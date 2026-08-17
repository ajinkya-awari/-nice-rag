"""Lazy, API-key-gated ReAct AgentExecutor factory for Project 19."""

from __future__ import annotations

import os
from collections.abc import Sequence
from types import MappingProxyType
from typing import Any

from src.prompts import REACT_PROMPT_TEMPLATE
from src.protocol import GROQ_MODEL


MISSING_API_KEY_MESSAGE = (
    "GROQ_API_KEY is not set; the NICE-RAG agent is not available. "
    "No external API was called."
)

MODEL_CONFIG = MappingProxyType(
    {
        "model_name": GROQ_MODEL,
        "temperature": 0.0,
        "max_tokens": 1024,
    }
)

AGENT_EXECUTOR_CONFIG = MappingProxyType(
    {
        "handle_parsing_errors": True,
        "max_iterations": 6,
        "return_intermediate_steps": True,
    }
)


def missing_api_key_message() -> str:
    """Return the safe user-facing state when Groq is not configured."""
    return MISSING_API_KEY_MESSAGE


def build_agent_executor(tools: Sequence[Any] = ()) -> Any | None:
    """Build the bounded executor only after the explicit API-key gate."""
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        return None

    try:
        from langchain.agents import AgentExecutor, create_react_agent
        from langchain_core.prompts import PromptTemplate
        from langchain_groq import ChatGroq
    except ImportError as exc:
        raise RuntimeError(
            "Optional agent dependencies are not installed; no external API call was made."
        ) from exc

    llm = ChatGroq(**dict(MODEL_CONFIG))
    prompt = PromptTemplate.from_template(REACT_PROMPT_TEMPLATE)
    bound_tools = list(tools)
    react_agent = create_react_agent(llm, bound_tools, prompt)
    return AgentExecutor(
        agent=react_agent,
        tools=bound_tools,
        **dict(AGENT_EXECUTOR_CONFIG),
    )
