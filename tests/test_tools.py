import pytest

from src.ingest import SyntheticDocument, tag_documents
from src.tools import (
    drug_interaction_lookup,
    normalize_drug_name,
    retrieve_cited,
)


def _tagged_documents():
    documents = [
        SyntheticDocument("alpha passage one", {"page": 1}),
        SyntheticDocument("alpha alpha passage two", {"page": 2}),
        SyntheticDocument("alpha passage three", {"page": 3}),
        SyntheticDocument("alpha passage four", {"page": 4}),
    ]
    return [
        tagged
        for document, guideline_id in zip(
            documents, ("NG28", "CG127", "NG17", "NG185")
        )
        for tagged in tag_documents([document], guideline_id)
    ]


def test_retrieve_cited_caps_results_and_formats_guideline_page_citations():
    result = retrieve_cited("alpha", _tagged_documents(), limit=10)

    lines = [line for line in result.splitlines() if line]
    assert len(lines) == 3
    assert all(line.startswith("[") and "] " in line for line in lines)
    assert "[CG127, p.2]" in result
    assert "[NG28, p.1]" in result
    assert "[NG17, p.3]" in result
    assert "[NG185, p.4]" not in result


def test_retrieve_cited_handles_empty_query_and_no_matches():
    documents = _tagged_documents()

    assert "query" in retrieve_cited("   ", documents).lower()
    assert "no matching" in retrieve_cited("missing", documents).lower()


def test_retrieve_cited_rejects_documents_without_provenance():
    malformed = [SyntheticDocument("alpha", {"page": 1})]

    with pytest.raises(ValueError, match="guideline_id"):
        retrieve_cited("alpha", malformed)


def test_normalize_drug_name_is_case_and_punctuation_insensitive():
    assert normalize_drug_name("  Aspirin/Warfarin ") == "aspirin warfarin"


def test_drug_interaction_lookup_is_deterministic_and_returns_strings():
    first = drug_interaction_lookup("  Aspirin ", "WARFARIN")
    second = drug_interaction_lookup("warfarin", "aspirin")

    assert isinstance(first, str)
    assert first == second
    assert "synthetic" in first.lower()


def test_drug_interaction_lookup_handles_unknown_and_blank_inputs():
    unknown = drug_interaction_lookup("vitamin c", "water")
    blank = drug_interaction_lookup("", "water")

    assert isinstance(unknown, str)
    assert "no synthetic interaction" in unknown.lower()
    assert isinstance(blank, str)
    assert "two non-empty" in blank.lower()
