"""Offline evaluation-plan enumeration without live model execution."""

from dataclasses import dataclass

from src.ingest import SyntheticDocument, tag_documents
from src.scenarios import CANONICAL_SCENARIOS
from src.tools import retrieve_cited


@dataclass(frozen=True)
class EvaluationPlanEntry:
    """Fixture metadata for a scenario whose live run remains gated."""

    scenario_id: str
    guideline_id: str
    query: str
    status: str


@dataclass(frozen=True)
class SyntheticSmokeResult:
    """One in-memory cited passage from a synthetic retrieval smoke test."""

    scenario_id: str
    guideline_id: str
    citation: str
    passage: str


def build_offline_evaluation_plan() -> tuple[EvaluationPlanEntry, ...]:
    """Return exactly the five fixture inputs with no generated result."""
    return tuple(
        EvaluationPlanEntry(
            scenario_id=scenario.scenario_id,
            guideline_id=scenario.guideline_id,
            query=scenario.query,
            status="gated_no_live_trace",
        )
        for scenario in CANONICAL_SCENARIOS
    )


def render_offline_evaluation_plan() -> str:
    """Render fixture metadata for inspection without running an agent."""
    return "\n".join(
        "\t".join(
            (entry.scenario_id, entry.guideline_id, entry.status, entry.query)
        )
        for entry in build_offline_evaluation_plan()
    )


def run_synthetic_retrieval_smoke() -> tuple[SyntheticSmokeResult, ...]:
    """Retrieve one synthetic page for each fixture without model execution."""
    results = []
    for page, scenario in enumerate(CANONICAL_SCENARIOS, start=1):
        document = tag_documents(
            [
                SyntheticDocument(
                    page_content=f"{scenario.query} Synthetic passage.",
                    metadata={"page": page},
                )
            ],
            scenario.guideline_id,
        )[0]
        citation = f"[{scenario.guideline_id}, p.{page}]"
        results.append(
            SyntheticSmokeResult(
                scenario_id=scenario.scenario_id,
                guideline_id=scenario.guideline_id,
                citation=citation,
                passage=retrieve_cited(scenario.query, [document]),
            )
        )
    return tuple(results)
