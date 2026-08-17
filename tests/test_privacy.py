import ast
from pathlib import Path

from src.protocol import NICE_OGL_ATTRIBUTION, RESEARCH_DISCLAIMER
from src.privacy import is_restricted_path, restricted_path_reasons


def test_restricted_path_detection_covers_sources_caches_credentials_and_traces():
    restricted = [
        Path("data/pdfs/NG28.pdf"),
        Path("data/chroma_db/index.bin"),
        Path(".env"),
        Path("credentials.json"),
        Path("results/scenario_01.jsonl"),
    ]
    allowed = [Path("src/protocol.py"), Path("README.md"), Path("results/.gitkeep")]

    assert all(is_restricted_path(path) for path in restricted)
    assert all(not is_restricted_path(path) for path in allowed)
    assert all(restricted_path_reasons(path) for path in restricted)


def test_release_text_preserves_disclaimer_and_attribution_contracts():
    assert "research" in RESEARCH_DISCLAIMER.lower()
    assert "not for clinical use" in RESEARCH_DISCLAIMER.lower()
    assert "NICE" in NICE_OGL_ATTRIBUTION
    assert "OGL" in NICE_OGL_ATTRIBUTION


def test_runtime_source_has_no_network_transfer_imports():
    root = Path(__file__).parents[1]
    forbidden_roots = {
        "boto3",
        "googleapiclient",
        "huggingface_hub",
        "httpx",
        "requests",
        "urllib",
    }
    for source_path in (root / "src").glob("*.py"):
        tree = ast.parse(source_path.read_text(encoding="utf-8"))
        imported_roots = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported_roots.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported_roots.add(node.module.split(".")[0])
        assert not imported_roots.intersection(forbidden_roots), source_path


def test_current_tree_has_no_restricted_artifact_files():
    root = Path(__file__).parents[1]
    restricted = []
    for path in root.rglob("*"):
        if not path.is_file() or ".git" in path.parts:
            continue
        if path.name in {".gitignore", "CACHEDIR.TAG"}:
            continue
        if is_restricted_path(path.relative_to(root)):
            restricted.append(path)

    assert restricted == []
