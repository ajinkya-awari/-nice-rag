import ast
import json
from pathlib import Path


NOTEBOOK_PATH = (
    Path(__file__).parents[1] / "notebooks" / "kaggle_nice_rag.ipynb"
)


def _notebook() -> dict:
    return json.loads(NOTEBOOK_PATH.read_text(encoding="utf-8"))


def _code_sources() -> list[str]:
    return [
        "".join(cell.get("source", []))
        for cell in _notebook()["cells"]
        if cell.get("cell_type") == "code"
    ]


def test_kaggle_notebook_fetches_the_active_approved_repository_by_revision() -> None:
    source = "\n".join(_code_sources())

    assert "REPOSITORY = 'https://github.com/ajinkya-awari/-nice-rag.git'" in source
    assert "'remote', 'add', 'origin', REPOSITORY" in source
    assert "'fetch', '--depth', '1', 'origin', EXPECTED_REVISION" in source


def test_kaggle_notebook_pins_revision_and_avoids_unused_stack_install() -> None:
    source = "\n".join(_code_sources())

    assert "EXPECTED_REVISION = " in source
    assert "source revision does not match EXPECTED_REVISION" in source
    assert "'fetch', '--depth', '1', 'origin', EXPECTED_REVISION" in source
    assert "'checkout', '--detach', 'FETCH_HEAD'" in source
    assert "'clone', '--depth', '2'" not in source
    assert "'pip', 'install'" not in source
    assert "requirements.txt" not in source


def test_kaggle_notebook_fails_closed_and_writes_sanitized_evidence() -> None:
    source = "\n".join(_code_sources())

    assert "def run_checked" in source
    assert "raise RuntimeError" in source
    assert "EVIDENCE_PATH = ROOT / 'nice_rag_synthetic_evidence.json'" in source
    assert "'kernel': 'ajinkya1225/nice-rag-synthetic-validation'" in source
    assert "json.dump" in source
    for field in (
        "python_version",
        "platform",
        "dependency_versions",
        "gpu_visible",
        "source_revision",
        "pytest_exit_code",
        "pytest_passed",
        "compileall_exit_code",
        "cpu_smoke",
        "citation_validity",
        "scenario_count",
        "restricted_artifacts",
        "skipped_gates",
    ):
        assert repr(field) in source or f'"{field}"' in source


def test_kaggle_notebook_runs_only_provider_free_bounded_stages() -> None:
    source = "\n".join(_code_sources())

    assert "--documents', '1000'" in source or '"--documents", "1000"' in source
    assert "--repeats', '1'" in source or '"--repeats", "1"' in source
    assert "--list-scenarios" in source
    assert "GROQ_API_KEY" not in source
    assert "data/pdfs" not in source
    assert "build_chroma_store(" not in source


def test_kaggle_notebook_tolerates_missing_nvidia_smi_on_cpu_image() -> None:
    source = "\n".join(_code_sources())

    assert "shutil.which('nvidia-smi')" in source
    assert "if nvidia_smi" in source


def test_kaggle_notebook_metadata_is_cpu_private_and_internet_enabled() -> None:
    notebook = _notebook()

    assert notebook["nbformat"] == 4
    assert notebook["metadata"]["kernelspec"]["name"] == "python3"
    cell_ids = [cell.get("id") for cell in notebook["cells"]]
    assert all(isinstance(cell_id, str) and cell_id for cell_id in cell_ids)
    assert len(cell_ids) == len(set(cell_ids))
    assert all(cell.get("outputs", []) == [] for cell in notebook["cells"])
