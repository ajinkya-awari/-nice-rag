"""Canonical synthetic scenario fixtures for Project 19.

These records define test inputs only. They contain no model output, source
citation, clinical recommendation, or evaluation trace.
"""

from dataclasses import dataclass

from src.protocol import GUIDELINE_IDS


@dataclass(frozen=True)
class Scenario:
    """One synthetic research query awaiting an explicitly gated run."""

    scenario_id: str
    guideline_id: str
    query: str
    purpose: str
    status: str


SCENARIO_COUNT = 5

CANONICAL_SCENARIOS = (
    Scenario(
        scenario_id="scenario_01",
        guideline_id=GUIDELINE_IDS[0],
        query=(
            "Synthetic research query: retrieve NG28 guidance about reviewing "
            "glucose-lowering therapy in adults with type 2 diabetes."
        ),
        purpose="Check bounded retrieval for the NG28 synthetic fixture.",
        status="fixture_only",
    ),
    Scenario(
        scenario_id="scenario_02",
        guideline_id=GUIDELINE_IDS[1],
        query=(
            "Synthetic research query: retrieve CG127 guidance about blood-pressure "
            "assessment in pregnancy."
        ),
        purpose="Check bounded retrieval for the CG127 synthetic fixture.",
        status="fixture_only",
    ),
    Scenario(
        scenario_id="scenario_03",
        guideline_id=GUIDELINE_IDS[2],
        query=(
            "Synthetic research query: retrieve NG17 guidance about neuropathic "
            "pain management options."
        ),
        purpose="Check bounded retrieval for the NG17 synthetic fixture.",
        status="fixture_only",
    ),
    Scenario(
        scenario_id="scenario_04",
        guideline_id=GUIDELINE_IDS[3],
        query=(
            "Synthetic research query: retrieve NG185 guidance about recognising "
            "possible sepsis and escalation pathways."
        ),
        purpose="Check bounded retrieval for the NG185 synthetic fixture.",
        status="fixture_only",
    ),
    Scenario(
        scenario_id="scenario_05",
        guideline_id=GUIDELINE_IDS[4],
        query=(
            "Synthetic research query: retrieve CG191 guidance about safeguarding "
            "adults concerns and escalation pathways."
        ),
        purpose="Check bounded retrieval for the CG191 synthetic fixture.",
        status="fixture_only",
    ),
)
