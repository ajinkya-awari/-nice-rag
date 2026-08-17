import inspect
import sys

from src import tools


def test_lazy_tool_factory_exists_without_importing_langchain():
    assert hasattr(tools, "build_langchain_tools")
    assert "langchain_core" not in sys.modules


def test_tool_factory_contract_delegates_string_returning_functions():
    source = inspect.getsource(tools.build_langchain_tools)

    assert "from langchain_core.tools import tool" in source
    assert "retrieve_cited" in source
    assert "drug_interaction_lookup" in source
    assert "-> str" in source
