"""Offline evaluation-plan enumeration without live model execution."""

from dataclasses import dataclass

from src.scenarios import CANONICAL_SCENARIOS


@dataclass(frozen=True)
class EvaluationPlanEntry:
    """Fixture metadata for a scenario whose live run remains gated."""

    scenario_id: str
    guideline_id: str
    query: str
    status: str


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
