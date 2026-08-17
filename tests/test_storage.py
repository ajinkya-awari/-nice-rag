import sys
from pathlib import Path

from src.storage import build_chroma_config, load_chroma_config


def test_build_and_load_use_the_same_persistent_local_configuration():
    expected = {
        "persist_directory": "data/chroma_db",
        "embedding_model": "sentence-transformers/all-MiniLM-L6-v2",
    }

    assert build_chroma_config() == expected
    assert load_chroma_config() == expected
    assert build_chroma_config() == load_chroma_config()


def test_configuration_helpers_have_no_chroma_import_or_filesystem_side_effect():
    root = Path(__file__).parents[1]
    store_path = root / "data" / "chroma_db"
    existed_before = store_path.exists()
    modules_before = set(sys.modules)

    build_chroma_config()
    load_chroma_config()

    assert store_path.exists() is existed_before
    assert "chromadb" not in (set(sys.modules) - modules_before)
