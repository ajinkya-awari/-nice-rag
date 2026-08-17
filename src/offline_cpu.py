"""Download-free CPU stress checks over synthetic in-memory documents."""

from dataclasses import dataclass

from src.ingest import SyntheticDocument, split_documents, tag_documents
from src.scenarios import CANONICAL_SCENARIOS
from src.tools import retrieve_cited


MAX_SYNTHETIC_DOCUMENTS = 50_000
MAX_QUERY_REPEATS = 100


@dataclass(frozen=True)
class CpuStressReport:
    """Deterministic counters from the local synthetic CPU check."""

    document_count: int
    chunk_count: int
    queries_checked: int
    cited_results: int
    max_passages: int
    all_citations_valid: bool


def _build_synthetic_documents(document_count: int) -> list[SyntheticDocument]:
    documents: list[SyntheticDocument] = []
    for index in range(document_count):
        scenario = CANONICAL_SCENARIOS[index % len(CANONICAL_SCENARIOS)]
        document = SyntheticDocument(
            page_content=(
                f"{scenario.query} Synthetic CPU fixture passage {index}. "
                f"This repeated local text exercises tokenization and chunking. "
            )
            * 3,
            metadata={"page": (index % 50) + 1},
        )
        documents.extend(tag_documents([document], scenario.guideline_id))
    return documents


def run_cpu_stress_check(
    document_count: int = 1_000,
    query_repeats: int = 1,
) -> CpuStressReport:
    """Exercise synthetic ingestion and capped retrieval entirely in memory.

    This check deliberately avoids files, optional dependencies, embeddings,
    network access, model execution, and clinical/source-derived content.
    """
    if not isinstance(document_count, int) or not 5 <= document_count <= MAX_SYNTHETIC_DOCUMENTS:
        raise ValueError(
            f"document_count must be between 5 and {MAX_SYNTHETIC_DOCUMENTS}"
        )
    if not isinstance(query_repeats, int) or not 1 <= query_repeats <= MAX_QUERY_REPEATS:
        raise ValueError(f"query_repeats must be between 1 and {MAX_QUERY_REPEATS}")

    documents = _build_synthetic_documents(document_count)
    chunks = split_documents(documents, chunk_size=240, chunk_overlap=40)
    cited_results = 0
    max_passages = 0
    all_citations_valid = True

    for scenario in CANONICAL_SCENARIOS:
        for _ in range(query_repeats):
            result = retrieve_cited(scenario.query, chunks)
            lines = [line for line in result.splitlines() if line]
            passages = len(lines)
            max_passages = max(max_passages, passages)
            expected_prefix = f"[{scenario.guideline_id}, p."
            if lines and all(line.startswith("[") for line in lines):
                cited_results += 1
            else:
                all_citations_valid = False
            if not lines or not all(line.startswith(expected_prefix) for line in lines):
                all_citations_valid = False

    queries_checked = len(CANONICAL_SCENARIOS) * query_repeats
    return CpuStressReport(
        document_count=document_count,
        chunk_count=len(chunks),
        queries_checked=queries_checked,
        cited_results=cited_results,
        max_passages=max_passages,
        all_citations_valid=all_citations_valid,
    )


def render_cpu_stress_report(report: CpuStressReport) -> str:
    """Render a compact CLI report without writing result files."""
    return "\n".join(
        (
            "CPU-only synthetic stress check",
            f"documents={report.document_count}",
            f"chunks={report.chunk_count}",
            f"queries_checked={report.queries_checked}",
            f"cited_results={report.cited_results}",
            f"max_passages={report.max_passages}",
            f"all_citations_valid={report.all_citations_valid}",
        )
    )
