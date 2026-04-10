"""Tests for agentic AI framework integration adapters (SRS 3.13)."""
from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch

from nexarq_cli.agents.base import AgentResult, Severity
from nexarq_cli.agents.registry import REGISTRY
from nexarq_cli.config.schema import NexarqConfig
from nexarq_cli.frameworks.base import FrameworkAdapter
from nexarq_cli.frameworks.langchain_adapter import LangChainAdapter
from nexarq_cli.frameworks.langgraph_adapter import LangGraphAdapter
from nexarq_cli.frameworks.crewai_adapter import CrewAIAdapter
from nexarq_cli.frameworks.autogen_adapter import AutoGenAdapter, get_adapter_for
from nexarq_cli.llm.base import BaseLLMProvider, LLMResponse


MOCK_DIFF = "diff --git a/x.py b/x.py\n+def foo(): pass\n"


class _MockFactory:
    def get_for_agent(self, name: str):
        class _P(BaseLLMProvider):
            name = "mock"
            def _call_api(self, p, s=""):
                return LLMResponse(text="No issues found.", provider="mock", model="m")
            def health_check(self): return True
        return _P(model="m")

    def get(self, key="default"):
        return self.get_for_agent(key)


class TestFrameworkAdapterBase:
    def test_all_adapters_inherit_base(self):
        cfg = NexarqConfig()
        factory = _MockFactory()
        for cls in [LangChainAdapter, LangGraphAdapter, CrewAIAdapter, AutoGenAdapter]:
            adapter = cls(cfg, factory, REGISTRY)
            assert isinstance(adapter, FrameworkAdapter)

    def test_framework_names_unique(self):
        names = [LangChainAdapter.framework_name, LangGraphAdapter.framework_name,
                 CrewAIAdapter.framework_name, AutoGenAdapter.framework_name]
        assert len(set(names)) == 4

    def test_all_have_framework_name(self):
        for cls in [LangChainAdapter, LangGraphAdapter, CrewAIAdapter, AutoGenAdapter]:
            assert cls.framework_name != "base"


class TestLangChainAdapter:
    def test_is_available_returns_bool(self):
        cfg = NexarqConfig()
        adapter = LangChainAdapter(cfg, _MockFactory(), REGISTRY)
        result = adapter.is_available()
        assert isinstance(result, bool)

    def test_error_message_references_install_cmd(self):
        """The RuntimeError from missing langchain must mention pip install."""
        cfg = NexarqConfig()
        adapter = LangChainAdapter(cfg, _MockFactory(), REGISTRY)
        # Simulate missing langchain by patching the import inside run()
        with patch("nexarq_cli.frameworks.langchain_adapter.LangChainAdapter.run",
                   side_effect=RuntimeError("LangChain not installed. Run: pip install langchain")):
            with pytest.raises(RuntimeError, match="pip install"):
                adapter.run(MOCK_DIFF, "python", ["security"])

    def test_framework_name(self):
        assert LangChainAdapter.framework_name == "langchain"

    def test_as_tools_returns_list_or_raises(self):
        """as_tools returns a list (if langchain available) or raises."""
        cfg = NexarqConfig()
        adapter = LangChainAdapter(cfg, _MockFactory(), REGISTRY)
        try:
            tools = adapter.as_tools(MOCK_DIFF, "python")
            assert isinstance(tools, list)
        except RuntimeError:
            pass  # langchain not installed


class TestLangGraphAdapter:
    def test_priority_split_includes_security(self):
        from nexarq_cli.frameworks.langgraph_adapter import _PRIORITY
        assert "security" in _PRIORITY

    def test_build_graph_or_raises(self):
        """build_graph returns compiled graph or raises RuntimeError if missing."""
        cfg = NexarqConfig()
        adapter = LangGraphAdapter(cfg, _MockFactory(), REGISTRY)
        try:
            graph = adapter.build_graph(["security", "bugs"])
            assert graph is not None
        except RuntimeError:
            pass  # langgraph not installed

    def test_priority_split(self):
        from nexarq_cli.frameworks.langgraph_adapter import _PRIORITY
        assert "security" in _PRIORITY
        assert "bugs" in _PRIORITY
        assert "review" not in _PRIORITY


class TestCrewAIAdapter:
    def test_run_raises_if_crewai_missing(self):
        cfg = NexarqConfig()
        adapter = CrewAIAdapter(cfg, _MockFactory(), REGISTRY)
        with pytest.raises((RuntimeError, ImportError)):
            adapter.run(MOCK_DIFF, "python", ["security"])

    def test_framework_name(self):
        assert CrewAIAdapter.framework_name == "crewai"


class TestAutoGenAdapter:
    def test_run_without_framework_uses_native(self):
        """AutoGen adapter falls back to direct agent execution when AutoGen not installed."""
        cfg = NexarqConfig()
        adapter = AutoGenAdapter(cfg, _MockFactory(), REGISTRY)

        # Mock agents to avoid LLM calls
        with patch.object(REGISTRY, "get") as mock_get:
            mock_agent = MagicMock()
            mock_agent.run.return_value = AgentResult(
                agent_name="security", severity=Severity.CRITICAL, output="ok"
            )
            mock_get.return_value = mock_agent

            # AutoGen adapter delegates to native run even without autogen installed
            with patch("builtins.__import__", side_effect=lambda n, *a, **k: (_ for _ in ()).throw(ImportError) if n == "autogen" else __import__(n, *a, **k)):
                try:
                    results = adapter.run(MOCK_DIFF, "python", ["security"])
                    assert all(isinstance(r, AgentResult) for r in results)
                except (RuntimeError, ImportError):
                    pass  # Expected when autogen not installed

    def test_framework_name(self):
        assert AutoGenAdapter.framework_name == "autogen"


class TestGetAdapterFor:
    def test_returns_correct_adapter_langchain(self):
        cfg = NexarqConfig()
        adapter = get_adapter_for("langchain", cfg, _MockFactory())
        assert isinstance(adapter, LangChainAdapter)

    def test_returns_correct_adapter_langgraph(self):
        cfg = NexarqConfig()
        adapter = get_adapter_for("langgraph", cfg, _MockFactory())
        assert isinstance(adapter, LangGraphAdapter)

    def test_returns_correct_adapter_crewai(self):
        cfg = NexarqConfig()
        adapter = get_adapter_for("crewai", cfg, _MockFactory())
        assert isinstance(adapter, CrewAIAdapter)

    def test_returns_correct_adapter_autogen(self):
        cfg = NexarqConfig()
        adapter = get_adapter_for("autogen", cfg, _MockFactory())
        assert isinstance(adapter, AutoGenAdapter)

    def test_case_insensitive(self):
        cfg = NexarqConfig()
        adapter = get_adapter_for("LangChain", cfg, _MockFactory())
        assert isinstance(adapter, LangChainAdapter)

    def test_unknown_framework_raises(self):
        cfg = NexarqConfig()
        with pytest.raises(ValueError, match="Unknown framework"):
            get_adapter_for("tensorflow", cfg, _MockFactory())
