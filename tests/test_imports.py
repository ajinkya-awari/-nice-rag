import importlib
import sys


def test_protocol_and_cli_are_importable_without_external_runtime_initialization():
    before = set(sys.modules)

    protocol = importlib.import_module("src.protocol")
    cli = importlib.import_module("run")

    assert protocol.GUIDELINE_IDS
    assert cli.main([]) == 0

    newly_loaded = set(sys.modules) - before
    forbidden_runtime_modules = {
        "chromadb",
        "gradio",
        "langchain",
        "langchain_community",
        "langchain_groq",
        "sentence_transformers",
    }
    assert not newly_loaded.intersection(forbidden_runtime_modules)
