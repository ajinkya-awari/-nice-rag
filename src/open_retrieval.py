"""Deterministic lexical retrieval for the isolated PMC open-evidence corpus."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from datetime import datetime, timezone
import json
from pathlib import Path
import platform
import re

from src.open_ingest import (
    OPEN_EVIDENCE_CORPUS,
    OpenChunk,
    ValidatedOpenArticle,
    split_open_sections,
)
from src.open_registry import OPEN_EVIDENCE_SOURCES
from src.protocol import MAX_RETRIEVAL_PASSAGES


OPEN_VALIDATION_QUERIES: Mapping[str, str] = {
    "type_2_diabetes": "type diabetes glucose",
    "pregnancy_hypertension": "pre eclampsia hypertension",
    "neuropathic_pain": "neuropathic pain",
    "adult_sepsis": "sepsis recognition",
    "adult_safeguarding": "staff resident abuse",
}
_CITATION_PATTERN = re.compile(
    r"^\[PMCID: (PMC[0-9]+), section: ([^\]\r\n]+)\]"
)


def _tokens(value: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", value.casefold())


def _validate_chunk(chunk: OpenChunk) -> tuple[str, str]:
    metadata = chunk.metadata
    if metadata.get("corpus") != OPEN_EVIDENCE_CORPUS:
        raise ValueError("Each chunk must use the pmc_open_evidence corpus")
    if "guideline_id" in metadata:
        raise ValueError("NICE guideline metadata is forbidden in open-evidence chunks")
    pmcid = metadata.get("pmcid")
    if not isinstance(pmcid, str) or re.fullmatch(r"PMC[0-9]+", pmcid) is None:
        raise ValueError("Each chunk must include a canonical PMCID")
    section = metadata.get("section_title")
    if not isinstance(section, str) or not section.strip():
        raise ValueError("Each chunk must include a non-empty section title")
    normalized_section = " ".join(section.split()).replace("]", ")")
    return pmcid, normalized_section


def retrieve_open_cited(
    query: str,
    chunks: Iterable[OpenChunk],
    limit: int = MAX_RETRIEVAL_PASSAGES,
) -> str:
    """Return at most three deterministic, cited open-evidence passages."""
    if not query.strip():
        return "Please provide a non-empty open-evidence research query."

    query_tokens = _tokens(query)
    bounded_limit = max(0, min(limit, MAX_RETRIEVAL_PASSAGES))
    scored: list[tuple[int, int, OpenChunk, str, str]] = []
    for position, chunk in enumerate(chunks):
        pmcid, section = _validate_chunk(chunk)
        content_tokens = _tokens(chunk.text)
        score = sum(content_tokens.count(token) for token in query_tokens)
        if score:
            scored.append((-score, position, chunk, pmcid, section))

    scored.sort(key=lambda item: (item[0], item[1]))
    selected = scored[:bounded_limit]
    if not selected:
        return "No matching open-evidence passages found."
    return "\n".join(
        f"[PMCID: {pmcid}, section: {section}] {chunk.text.strip()}"
        for _, _, chunk, pmcid, section in selected
    )


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace(
        "+00:00", "Z"
    )


def _citation_prefixes(result: str) -> tuple[str, ...]:
    prefixes: list[str] = []
    for line in result.splitlines():
        match = _CITATION_PATTERN.match(line)
        if match is not None:
            prefixes.append(match.group(0))
    return tuple(prefixes)


def validate_open_queries(
    articles: Iterable[ValidatedOpenArticle],
    *,
    repeats: int = 2,
    generated_at_utc: str | None = None,
    source_revision: str = "unrecorded",
) -> dict[str, object]:
    """Run five fixed queries and return a metadata-only validation report."""
    article_values = tuple(articles)
    if len(article_values) != len(OPEN_EVIDENCE_SOURCES):
        raise ValueError("Open validation requires exactly five articles")
    if repeats <= 0:
        raise ValueError("repeats must be greater than zero")
    topic_keys = [article.source.topic_key for article in article_values]
    if len(set(topic_keys)) != len(topic_keys):
        raise ValueError("Open validation rejects duplicate topic sources")
    expected_topics = {source.topic_key for source in OPEN_EVIDENCE_SOURCES}
    if set(topic_keys) != expected_topics:
        raise ValueError("Open validation topic set differs from the fixed registry")

    all_chunks = tuple(
        chunk
        for article in article_values
        for chunk in split_open_sections(article.sections)
    )
    query_results: list[dict[str, object]] = []
    for source in OPEN_EVIDENCE_SOURCES:
        query = OPEN_VALIDATION_QUERIES[source.topic_key]
        replays = tuple(
            retrieve_open_cited(query, all_chunks) for _ in range(repeats)
        )
        prefixes = _citation_prefixes(replays[0])
        citation_pmcids = tuple(
            match.group(1)
            for prefix in prefixes
            if (match := _CITATION_PATTERN.match(prefix)) is not None
        )
        deterministic = len(set(replays)) == 1
        citation_valid = bool(prefixes) and all(
            pmcid == source.pmcid for pmcid in citation_pmcids
        )
        query_results.append(
            {
                "topic_key": source.topic_key,
                "expected_pmcid": source.pmcid,
                "citation_prefixes": list(prefixes),
                "passage_count": len(prefixes),
                "citations_valid": citation_valid,
                "deterministic_replay": deterministic,
            }
        )

    all_citations_valid = all(
        bool(item["citations_valid"]) for item in query_results
    )
    all_deterministic = all(
        bool(item["deterministic_replay"]) for item in query_results
    )
    maximum_passage_count = max(
        (int(item["passage_count"]) for item in query_results), default=0
    )
    return {
        "schema_version": 1,
        "status": (
            "OPEN-EVIDENCE-VERIFIED"
            if all_citations_valid
            and all_deterministic
            and maximum_passage_count <= MAX_RETRIEVAL_PASSAGES
            else "OPEN-EVIDENCE-VALIDATION-FAILED"
        ),
        "corpus": OPEN_EVIDENCE_CORPUS,
        "generated_at_utc": generated_at_utc or _utc_now(),
        "source_revision": source_revision,
        "command": "python run.py --validate-open-evidence",
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "device": "CPU",
        "gpu_used": False,
        "source_count": len(article_values),
        "scenario_count": len(query_results),
        "repeats": repeats,
        "maximum_passage_count": maximum_passage_count,
        "all_citations_valid": all_citations_valid,
        "all_deterministic": all_deterministic,
        "queries": query_results,
        "skipped_gates": [
            "NICE content acquisition",
            "embedding model download",
            "Chroma build",
            "Groq or other provider execution",
            "patient data",
            "deployment",
        ],
    }


def write_open_validation_report(
    report: Mapping[str, object], path: Path
) -> None:
    """Write a sanitized deterministic-validation report as JSON."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(dict(report), indent=2) + "\n", encoding="utf-8")
