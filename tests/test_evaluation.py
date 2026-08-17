from src.evaluation import (
    build_offline_evaluation_plan,
    render_offline_evaluation_plan,
)
import subprocess
import sys


def test_offline_evaluation_plan_has_exactly_five_gated_entries():
    plan = build_offline_evaluation_plan()

    assert len(plan) == 5
    assert [entry.scenario_id for entry in plan] == [
        "scenario_01",
        "scenario_02",
        "scenario_03",
        "scenario_04",
        "scenario_05",
    ]
    assert all(entry.query.strip() for entry in plan)
    assert all(entry.status == "gated_no_live_trace" for entry in plan)


def test_rendered_offline_plan_contains_metadata_only():
    rendered = render_offline_evaluation_plan()
    lines = [line for line in rendered.splitlines() if line]

    assert len(lines) == 5
    assert all("gated_no_live_trace" in line for line in lines)
    assert "answer:" not in rendered.casefold()
    assert "citation:" not in rendered.casefold()
    assert "model output" not in rendered.casefold()


def test_cli_lists_scenarios_without_live_execution(capsys):
    import run

    assert run.main(["--list-scenarios"]) == 0
    output = capsys.readouterr().out

    assert output.count("gated_no_live_trace") == 5


def test_script_entrypoint_forwards_command_line_arguments():
    completed = subprocess.run(
        [sys.executable, "run.py", "--list-scenarios"],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0
    assert completed.stdout.count("gated_no_live_trace") == 5
