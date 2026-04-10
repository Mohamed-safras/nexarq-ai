"""
Base integration adapter for agentic AI frameworks (SRS 3.13).

Nexarq supports four frameworks as optional enhancement layers:
  - LangChain  – chain-based orchestration
  - LangGraph  – stateful graph-based workflows
  - AutoGen    – multi-agent conversation framework
  - CrewAI     – role-based agent crews

Each adapter wraps the native Nexarq agent system so that framework-specific
tooling (tracing, memory, structured I/O) can be layered on top without
changing core review logic.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from nexarq_cli.agents.base import AgentResult
from nexarq_cli.agents.registry import AgentRegistry, REGISTRY
from nexarq_cli.config.schema import NexarqConfig
from nexarq_cli.llm.factory import LLMFactory


class FrameworkAdapter(ABC):
    """
    Abstract adapter that bridges a Nexarq agent pipeline to a specific
    agentic AI framework.
    """

    framework_name: str = "base"

    def __init__(
        self,
        config: NexarqConfig,
        factory: LLMFactory,
        registry: AgentRegistry = REGISTRY,
    ) -> None:
        self._config = config
        self._factory = factory
        self._registry = registry

    @abstractmethod
    def run(
        self,
        diff: str,
        language: str,
        agent_names: list[str] | None = None,
        context: dict | None = None,
        diff_result=None,
    ) -> list[AgentResult]:
        """Execute the review pipeline using the framework."""

    def stream(
        self,
        diff: str,
        language: str,
        agent_names: list[str] | None = None,
        context: dict | None = None,
        diff_result=None,
    ):
        """Stream results as each agent completes. Default: wraps run()."""
        yield from self.run(diff, language, agent_names, context, diff_result)

    def is_available(self) -> bool:
        """Return True if the framework package is installed."""
        try:
            self._check_import()
            return True
        except ImportError:
            return False

    @abstractmethod
    def _check_import(self) -> None:
        """Attempt to import the framework package (raises ImportError if missing)."""
