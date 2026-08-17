from pathlib import Path

import pytest

from src.offline_cpu import run_cpu_stress_check


def test_cpu_stress_check_scales_synthetic_retrieval_without_files() -> None:
    report = run_cpu_stress_check(document_count=250, query_repeats=2)

    assert report.document_count == 250
    assert report.chunk_count >= report.document_count
    assert report.queries_checked == 10
    assert report.cited_results == report.queries_checked
    assert report.max_passages == 3
    assert report.all_citations_valid is True
    assert not Path("data/chroma_db").exists()


def test_cli_runs_cpu_stress_check_without_external_runtime(capsys) -> None:
    import run

    assert run.main(["--cpu-smoke", "--documents", "100", "--repeats", "1"]) == 0
    output = capsys.readouterr().out

    assert "CPU-only synthetic stress check" in output
    assert "all_citations_valid=True" in output


@pytest.mark.parametrize(
    ("document_count", "query_repeats"),
    [(0, 1), (4, 1), (10, 0)],
)
def test_cpu_stress_check_rejects_unsafe_bounds(
    document_count: int, query_repeats: int
) -> None:
    with pytest.raises(ValueError):
        run_cpu_stress_check(
            document_count=document_count,
            query_repeats=query_repeats,
        )
