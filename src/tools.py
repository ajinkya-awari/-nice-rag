"""Deterministic, synthetic retrieval and interaction tools for Project 19."""

import re
from collections.abc import Iterable

from src.ingest import SyntheticDocument
from src.protocol import GUIDELINE_IDS, MAX_RETRIEVAL_PASSAGES


def _tokens(value: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", value.casefold())


def retrieve_cited(
    query: str,
    documents: Iterable[SyntheticDocument],
    limit: int = MAX_RETRIEVAL_PASSAGES,
) -> str:
    """Return at most three lexically matching synthetic passages with citations."""
    if not query.strip():
        return "Please provide a non-empty research query."

    query_tokens = _tokens(query)
    bounded_limit = max(0, min(limit, MAX_RETRIEVAL_PASSAGES))
    scored = []
    for position, document in enumerate(documents):
        guideline_id = document.metadata.get("guideline_id")
        if guideline_id not in GUIDELINE_IDS:
            raise ValueError("Each document must include a supported guideline_id")
        if "page" not in document.metadata:
            raise ValueError("Each document must include page metadata")

        content_tokens = _tokens(document.page_content)
        score = sum(content_tokens.count(token) for token in query_tokens)
        if score:
            scored.append((-score, position, document))

    scored.sort(key=lambda item: (item[0], item[1]))
    selected = [item[2] for item in scored[:bounded_limit]]
    if not selected:
        return "No matching synthetic passages found."

    return "\n".join(
        f"[{document.metadata['guideline_id']}, p.{document.metadata['page']}] "
        f"{document.page_content.strip()}"
        for document in selected
    )


def normalize_drug_name(name: str) -> str:
    """Normalize a medicine label for deterministic fixture lookup."""
    if not isinstance(name, str):
        return ""
    return " ".join(_tokens(name))


INTERACTION_FIXTURES: dict[frozenset[str], str] = {
    frozenset({"aspirin", "warfarin"}): (
        "Synthetic interaction fixture found for aspirin and warfarin; "
        "consult qualified professionals."
    )
}


def drug_interaction_lookup(first: str, second: str) -> str:
    """Look up a normalized synthetic interaction pair and always return text."""
    first_normalized = normalize_drug_name(first)
    second_normalized = normalize_drug_name(second)
    if not first_normalized or not second_normalized:
        return "Please provide two non-empty medicine names."

    interaction = INTERACTION_FIXTURES.get(
        frozenset({first_normalized, second_normalized})
    )
    if interaction is None:
        return "No synthetic interaction fixture found for the supplied pair."
    return interaction


def build_langchain_tools(documents: Iterable[SyntheticDocument]) -> list[object]:
    """Create LangChain wrappers lazily around the deterministic string tools."""
    from langchain_core.tools import tool

    bound_documents = tuple(documents)

    @tool
    def retrieve_guideline(query: str) -> str:
        """Retrieve at most three cited passages from the bound document set."""
        return retrieve_cited(query, bound_documents)

    @tool
    def check_drug_interaction(first: str, second: str) -> str:
        """Return a deterministic interaction-fixture string."""
        return drug_interaction_lookup(first, second)

    return [retrieve_guideline, check_drug_interaction]
