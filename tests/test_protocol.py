from pathlib import Path


from src import protocol


EXPECTED_PINS = {
    "langchain": "0.2.17",
    "langchain-community": "0.2.17",
    "langchain-core": "0.2.43",
    "langchain-text-splitters": "0.2.4",
    "langchain-groq": "0.1.9",
    "langchain-huggingface": "0.0.3",
    "chromadb": "0.5.3",
    "sentence-transformers": "3.1.0",
    "pypdf": "4.3.1",
    "gradio": "4.44.0",
    "pyyaml": "6.0.2",
    "pytest": ">=8.0",
}


def test_protocol_limits_corpus_to_the_five_approved_guidelines():
    assert protocol.GUIDELINE_IDS == ("NG28", "CG127", "NG17", "NG185", "CG191")


def test_protocol_preserves_paths_and_citation_contract():
    assert protocol.PDF_DIRECTORY == Path("data/pdfs")
    assert protocol.CHROMA_DIRECTORY == Path("data/chroma_db")
    assert protocol.RESULTS_DIRECTORY == Path("results")
    assert protocol.CITATION_FORMAT == "[GUIDELINE_ID, p.PAGE]"
    assert protocol.MAX_RETRIEVAL_PASSAGES == 3


def test_protocol_declares_exact_react_variables_and_planned_models():
    assert protocol.REACT_VARIABLES == frozenset(
        {"tools", "tool_names", "agent_scratchpad", "input"}
    )
    assert protocol.EMBEDDING_MODEL == "sentence-transformers/all-MiniLM-L6-v2"
    assert protocol.GROQ_MODEL == "llama-3.1-8b-instant"


def test_protocol_includes_safety_and_attribution_text():
    assert "research" in protocol.RESEARCH_DISCLAIMER.lower()
    assert "not for clinical use" in protocol.RESEARCH_DISCLAIMER.lower()
    assert "NICE" in protocol.NICE_OGL_ATTRIBUTION
    assert "OGL" in protocol.NICE_OGL_ATTRIBUTION


def test_requirements_manifest_contains_only_approved_planning_pins():
    manifest = Path(__file__).parents[1] / "requirements.txt"
    actual = {}
    for raw_line in manifest.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "==" in line:
            name, version = line.split("==", maxsplit=1)
            actual[name] = version
        elif ">=" in line:
            name, version = line.split(">=", maxsplit=1)
            actual[name] = f">={version}"
        else:
            raise AssertionError(f"Unpinned dependency entry: {line}")

    assert actual == EXPECTED_PINS
    assert protocol.PACKAGE_PINS == EXPECTED_PINS
