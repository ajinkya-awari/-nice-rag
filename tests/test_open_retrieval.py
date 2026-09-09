from dataclasses import replace
import json
from pathlib import Path

import pytest

from src.open_ingest import OpenChunk, OpenSection, ValidatedOpenArticle
from src.open_registry import OPEN_EVIDENCE_SOURCES
from src.open_retrieval import (
    OPEN_VALIDATION_QUERIES,
    retrieve_open_cited,
    validate_open_queries,
    write_open_validation_report,
)


def chunk(text: str, pmcid: str = "PMC5256065", section: str = "Methods") -> OpenChunk:
    return OpenChunk(
        text=text,
        metadata={
            "corpus": "pmc_open_evidence",
            "topic_key": "type_2_diabetes",
            "pmcid": pmcid,
            "doi": "10.3389/fendo.2017.00006",
            "article_title": "Fictional test article",
            "section_title": section,
            "section_index": 0,
            "canonical_url": f"https://pmc.ncbi.nlm.nih.gov/articles/{pmcid}/",
            "license_uri": "https://creativecommons.org/licenses/by/4.0/",
            "retrieved_at_utc": "2026-09-09T12:00:00Z",
            "source_sha256": "a" * 64,
            "chunk_index": 0,
        },
    )


def test_retrieval_ranks_occurrences_stably_and_formats_citations() -> None:
    chunks = (
        chunk("glucose context", section="Background"),
        chunk("glucose glucose methods", section="Methods"),
        chunk("glucose cohort", pmcid="PMC7886065", section="Results"),
    )

    result = retrieve_open_cited("glucose", chunks)

    lines = result.splitlines()
    assert lines[0] == "[PMCID: PMC5256065, section: Methods] glucose glucose methods"
    assert lines[1] == "[PMCID: PMC5256065, section: Background] glucose context"
    assert lines[2] == "[PMCID: PMC7886065, section: Results] glucose cohort"
    assert retrieve_open_cited("glucose", chunks) == result


def test_retrieval_enforces_empty_no_match_and_three_passage_boundaries() -> None:
    assert retrieve_open_cited(" ", (chunk("glucose"),)).startswith("Please provide")
    assert retrieve_open_cited("sepsis", (chunk("glucose"),)).startswith("No matching")
    result = retrieve_open_cited(
        "glucose", tuple(chunk(f"glucose item {index}") for index in range(5)), limit=20
    )
    assert len(result.splitlines()) == 3
    assert retrieve_open_cited("glucose", (chunk("glucose"),), limit=0).startswith(
        "No matching"
    )


@pytest.mark.parametrize(
    ("metadata_change", "message"),
    (
        ({"corpus": "nice"}, "corpus"),
        ({"guideline_id": "NG28"}, "NICE"),
        ({"pmcid": None}, "PMCID"),
        ({"section_title": None}, "section"),
    ),
)
def test_retrieval_rejects_namespace_and_provenance_leakage(
    metadata_change: dict[str, object], message: str
) -> None:
    original = chunk("glucose")
    invalid = replace(original, metadata={**original.metadata, **metadata_change})

    with pytest.raises(ValueError, match=message):
        retrieve_open_cited("glucose", (invalid,))


def article_for_topic(index: int) -> ValidatedOpenArticle:
    source = OPEN_EVIDENCE_SOURCES[index]
    query = OPEN_VALIDATION_QUERIES[source.topic_key]
    section = OpenSection(
        text=f"Fictional validation context {query}.",
        metadata={
            "corpus": "pmc_open_evidence",
            "topic_key": source.topic_key,
            "pmcid": source.pmcid,
            "doi": source.doi,
            "article_title": source.title,
            "section_title": "Fictional validation section",
            "section_index": 0,
            "canonical_url": source.canonical_url,
            "license_uri": source.expected_license_uri,
            "retrieved_at_utc": "2026-09-09T12:00:00Z",
            "source_sha256": str(index) * 64,
        },
    )
    return ValidatedOpenArticle(
        source=source,
        sections=(section,),
        source_sha256=str(index) * 64,
        retrieved_at_utc="2026-09-09T12:00:00Z",
        byte_count=100,
        license_uri=source.expected_license_uri,
        http_status=200,
        content_type="text/xml",
        retrieval_url="https://pmc.ncbi.nlm.nih.gov/api/oai/v1/mh/",
    )


def test_five_query_validation_is_sanitized_cited_and_deterministic() -> None:
    report = validate_open_queries(
        tuple(article_for_topic(index) for index in range(5)),
        repeats=2,
        generated_at_utc="2026-09-09T13:00:00Z",
    )

    assert report["status"] == "OPEN-EVIDENCE-VERIFIED"
    assert report["source_count"] == 5
    assert report["scenario_count"] == 5
    assert report["maximum_passage_count"] <= 3
    assert report["all_citations_valid"] is True
    assert report["all_deterministic"] is True
    assert len(report["queries"]) == 5
    assert all(item["citation_prefixes"] for item in report["queries"])
    assert "text" not in json.dumps(report).casefold()


def test_validation_rejects_partial_duplicate_or_invalid_repeats() -> None:
    articles = tuple(article_for_topic(index) for index in range(5))
    with pytest.raises(ValueError, match="exactly five"):
        validate_open_queries(articles[:4])
    with pytest.raises(ValueError, match="duplicate"):
        validate_open_queries((articles[0], articles[0], *articles[2:]))
    with pytest.raises(ValueError, match="repeats"):
        validate_open_queries(articles, repeats=0)


def test_validation_report_writer_emits_json_without_source_text(tmp_path: Path) -> None:
    report = validate_open_queries(
        tuple(article_for_topic(index) for index in range(5)),
        generated_at_utc="2026-09-09T13:00:00Z",
    )
    path = tmp_path / "validation.json"

    write_open_validation_report(report, path)

    loaded = json.loads(path.read_text(encoding="utf-8"))
    assert loaded == report
    assert "Fictional validation context" not in path.read_text(encoding="utf-8")
