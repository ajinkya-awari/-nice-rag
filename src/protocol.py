"""Stable Project 19 contracts used by the future NICE-RAG runtime.

This module intentionally uses only the Python standard library. Importing it
must not download data, load models, initialize a vector store, or call an API.
"""

from pathlib import Path
from types import MappingProxyType


GUIDELINE_IDS = ("NG28", "CG127", "NG17", "NG185", "CG191")

PDF_DIRECTORY = Path("data/pdfs")
CHROMA_DIRECTORY = Path("data/chroma_db")
RESULTS_DIRECTORY = Path("results")

CITATION_FORMAT = "[GUIDELINE_ID, p.PAGE]"
MAX_RETRIEVAL_PASSAGES = 3
REACT_VARIABLES = frozenset(
    {"tools", "tool_names", "agent_scratchpad", "input"}
)

EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
GROQ_MODEL = "llama-3.1-8b-instant"

RESEARCH_DISCLAIMER = (
    "Research information only; this demonstration is not for clinical use "
    "and is not a substitute for qualified professional advice."
)
NICE_OGL_ATTRIBUTION = (
    "NICE guideline-derived material requires attribution under the NICE Open "
    "Government Licence (OGL) before approved public release."
)

PACKAGE_PINS = MappingProxyType(
    {
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
)
