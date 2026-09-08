"""Edge-case and bounds-clamping tests for Project 19 contracts.

These tests cover paths not exercised by the primary test suite:
non-string normalisation input, limit clamping in retrieval, minimum
CPU stress bounds, and multi-reason privacy classification.
"""

import pytest

from src.ingest import SyntheticDocument, split_documents, tag_documents
from src.offline_cpu import run_cpu_stress_check
from src.privacy import restricted_path_reasons
from src.tools import drug_interaction_lookup, normalize_drug_name, retrieve_cited


# ---------------------------------------------------------------------------
# normalize_drug_name: non-string input
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("non_string", [None, 42, 3.14, [], {}])
def test_normalize_drug_name_returns_empty_string_for_non_string_input(non_string):
    result = normalize_drug_name(non_string)
    assert result == ""
    assert isinstance(result, str)


def test_normalize_drug_name_returns_empty_for_punctuation_only_string():
    result = normalize_drug_name("---/\\---")
    assert result == ""
    assert isinstance(result, str)


# ---------------------------------------------------------------------------
# drug_interaction_lookup: punctuation-only names fall through to empty check
# ---------------------------------------------------------------------------


def test_drug_interaction_lookup_treats_punctuation_only_as_empty():
    result = drug_interaction_lookup("---", "warfarin")
    assert isinstance(result, str)
    assert "two non-empty" in result.lower()


# ---------------------------------------------------------------------------
# retrieve_cited: limit clamping at zero and negative
# ---------------------------------------------------------------------------


def _three_tagged_docs():
    base = [
        SyntheticDocument("alpha beta gamma", {"page": 1}),
        SyntheticDocument("alpha beta", {"page": 2}),
        SyntheticDocument("alpha", {"page": 3}),
    ]
    return [
        tagged
        for doc, gid in zip(base, ("NG28", "CG127", "NG17"))
        for tagged in tag_documents([doc], gid)
    ]


def test_retrieve_cited_with_limit_zero_returns_no_match_message():
    result = retrieve_cited("alpha", _three_tagged_docs(), limit=0)
    assert isinstance(result, str)
    assert "no matching" in result.lower()


def test_retrieve_cited_with_negative_limit_clamps_to_zero():
    result = retrieve_cited("alpha", _three_tagged_docs(), limit=-5)
    assert isinstance(result, str)
    assert "no matching" in result.lower()


def test_retrieve_cited_always_returns_string():
    result = retrieve_cited("alpha", _three_tagged_docs())
    assert isinstance(result, str)


# ---------------------------------------------------------------------------
# split_documents: short content that fits within one chunk
# ---------------------------------------------------------------------------


def test_split_documents_produces_one_chunk_when_content_fits():
    short = SyntheticDocument(
        page_content="short",
        metadata={"guideline_id": "NG28", "page": 1},
    )
    chunks = split_documents([short], chunk_size=100, chunk_overlap=10)
    assert len(chunks) == 1
    assert chunks[0].page_content == "short"
    assert chunks[0].metadata["chunk_index"] == 0
    assert chunks[0].metadata["guideline_id"] == "NG28"


def test_split_documents_handles_content_exactly_chunk_size():
    exact = SyntheticDocument(
        page_content="0123456789",
        metadata={"guideline_id": "CG127", "page": 2},
    )
    chunks = split_documents([exact], chunk_size=10, chunk_overlap=2)
    assert len(chunks) == 1
    assert chunks[0].page_content == "0123456789"


# ---------------------------------------------------------------------------
# run_cpu_stress_check: minimum valid document count
# ---------------------------------------------------------------------------


def test_cpu_stress_check_runs_at_minimum_document_count():
    # With only 5 documents (1 per guideline) the lexical retriever has insufficient
    # signal to guarantee all top-3 results are same-guideline, so all_citations_valid
    # may be False — that is correct behaviour. We only assert the run completes and
    # returns valid-typed fields.
    report = run_cpu_stress_check(document_count=5, query_repeats=1)
    assert report.document_count == 5
    assert report.chunk_count >= 5
    assert report.queries_checked == 5
    assert isinstance(report.all_citations_valid, bool)
    assert report.max_passages <= 3


# ---------------------------------------------------------------------------
# restricted_path_reasons: multiple reasons on one path
# ---------------------------------------------------------------------------


def test_restricted_path_reasons_returns_multiple_reasons_for_nested_pdf():
    reasons = restricted_path_reasons("data/pdfs/NG28.pdf")
    assert len(reasons) >= 2
    reason_text = " ".join(reasons)
    assert "pdfs" in reason_text
    assert ".pdf" in reason_text


def test_restricted_path_reasons_returns_empty_tuple_for_plain_source_file():
    reasons = restricted_path_reasons("src/protocol.py")
    assert reasons == ()
