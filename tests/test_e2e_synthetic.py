from dataclasses import fields

from src.evaluation import run_synthetic_retrieval_smoke


def test_all_five_fixture_queries_retrieve_synthetic_cited_strings():
    results = run_synthetic_retrieval_smoke()

    assert len(results) == 5
    assert {field.name for field in fields(results[0])} == {
        "scenario_id",
        "guideline_id",
        "citation",
        "passage",
    }
    for index, result in enumerate(results, start=1):
        assert result.scenario_id == f"scenario_{index:02d}"
        assert result.citation == f"[{result.guideline_id}, p.{index}]"
        assert isinstance(result.passage, str)
        assert result.citation in result.passage
