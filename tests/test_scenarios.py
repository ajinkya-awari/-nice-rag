from dataclasses import fields

from src.protocol import GUIDELINE_IDS
from src.scenarios import CANONICAL_SCENARIOS, SCENARIO_COUNT, Scenario


def test_canonical_scenarios_have_exactly_five_guideline_scoped_records():
    assert SCENARIO_COUNT == 5
    assert len(CANONICAL_SCENARIOS) == SCENARIO_COUNT
    assert [scenario.scenario_id for scenario in CANONICAL_SCENARIOS] == [
        "scenario_01",
        "scenario_02",
        "scenario_03",
        "scenario_04",
        "scenario_05",
    ]
    assert {scenario.guideline_id for scenario in CANONICAL_SCENARIOS} == set(
        GUIDELINE_IDS
    )


def test_scenarios_are_fixture_only_and_contain_no_result_or_patient_fields():
    assert {field.name for field in fields(Scenario)} == {
        "scenario_id",
        "guideline_id",
        "query",
        "purpose",
        "status",
    }

    forbidden_terms = {
        "patient",
        "answer",
        "citation",
        "trace",
        "accuracy",
        "precision",
        "validation",
    }
    for scenario in CANONICAL_SCENARIOS:
        assert scenario.query.strip()
        assert scenario.purpose.strip()
        assert scenario.status == "fixture_only"
        text = f"{scenario.query} {scenario.purpose}".casefold()
        assert not forbidden_terms.intersection(text.split())
