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


def test_canonical_scenario_identifiers_match_their_research_topics():
    expected = [
        ("scenario_01", "NG28", "type 2 diabetes"),
        ("scenario_02", "NG133", "pregnancy"),
        ("scenario_03", "CG173", "neuropathic pain"),
        ("scenario_04", "NG253", "sepsis"),
        ("scenario_05", "NG189", "safeguarding"),
    ]

    actual = [
        (scenario.scenario_id, scenario.guideline_id, scenario.query.casefold())
        for scenario in CANONICAL_SCENARIOS
    ]
    assert [(scenario_id, guideline_id) for scenario_id, guideline_id, _ in actual] == [
        (scenario_id, guideline_id) for scenario_id, guideline_id, _ in expected
    ]
    for (_, _, query), (_, _, topic_phrase) in zip(actual, expected, strict=True):
        assert topic_phrase in query


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
