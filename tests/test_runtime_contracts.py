import ast
import inspect
import sys

from src import ingest


def test_ingest_exposes_lazy_runtime_function_contracts():
    expected = {
        "load_guideline_documents",
        "tag_loaded_documents",
        "split_loaded_documents",
        "build_chroma_store",
        "load_chroma_store",
    }

    assert expected.issubset(set(dir(ingest)))


def test_optional_runtime_imports_are_not_top_level():
    tree = ast.parse(inspect.getsource(ingest))
    top_level_imports = []
    for node in tree.body:
        if isinstance(node, ast.Import):
            top_level_imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            top_level_imports.append(node.module)

    assert not any(
        name.startswith(("chromadb", "langchain", "sentence_transformers"))
        for name in top_level_imports
    )
    assert "chromadb" not in sys.modules
    assert "langchain_community" not in sys.modules


def test_ingest_contract_preserves_metadata_order_and_persistent_paths():
    split_source = inspect.getsource(ingest.split_loaded_documents)
    assert split_source.index("tag_loaded_documents") < split_source.index(
        "RecursiveCharacterTextSplitter"
    )
    assert "langchain_text_splitters" in split_source
    assert "guideline_id" in split_source

    load_source = inspect.getsource(ingest.load_guideline_documents)
    assert "langchain_community.document_loaders" in load_source
    assert "PyPDFLoader" in load_source

    build_source = inspect.getsource(ingest.build_chroma_store)
    load_store_source = inspect.getsource(ingest.load_chroma_store)
    for source in (build_source, load_store_source):
        assert "langchain_community" in source
        assert "HuggingFaceEmbeddings" in source
        assert 'persist_directory="data/chroma_db"' in source
