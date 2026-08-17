import inspect
import re
import sys


def test_inline_react_prompt_has_exactly_the_four_required_variables():
    from src.prompts import PROMPT_VARIABLES, REACT_PROMPT_TEMPLATE

    extracted = frozenset(re.findall(r"{([a-z_]+)}", REACT_PROMPT_TEMPLATE))

    assert extracted == frozenset(
        {"tools", "tool_names", "agent_scratchpad", "input"}
    )
    assert PROMPT_VARIABLES == extracted
    assert "hub.pull" not in REACT_PROMPT_TEMPLATE


def test_agent_import_is_lazy_and_missing_key_is_graceful(monkeypatch):
    before = set(sys.modules)

    import src.agent as agent

    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    assert agent.build_agent_executor() is None
    assert "GROQ_API_KEY" in agent.missing_api_key_message()
    assert "not available" in agent.missing_api_key_message().lower()

    newly_loaded = set(sys.modules) - before
    forbidden_runtime_modules = {
        "chromadb",
        "langchain",
        "langchain_core",
        "langchain_groq",
        "langchain_community",
    }
    assert not newly_loaded.intersection(forbidden_runtime_modules)


def test_agent_configuration_preserves_project_safety_bounds():
    import src.agent as agent

    assert agent.AGENT_EXECUTOR_CONFIG == {
        "handle_parsing_errors": True,
        "max_iterations": 6,
        "return_intermediate_steps": True,
    }
    assert agent.MODEL_CONFIG == {
        "model_name": "llama-3.1-8b-instant",
        "temperature": 0.0,
        "max_tokens": 1024,
    }
    factory_source = inspect.getsource(agent.build_agent_executor)
    assert "ChatGroq(" in factory_source
    assert "GROQ_API_KEY" in factory_source
    assert "AgentExecutor(" in factory_source
