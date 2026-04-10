"""Agent registry – maps names to agent classes (AG-1/4)."""
from __future__ import annotations

from nexarq_cli.agents.base import BaseAgent

from nexarq_cli.agents.builtin.security import SecurityAgent
from nexarq_cli.agents.builtin.bugs import BugsAgent
from nexarq_cli.agents.builtin.performance import PerformanceAgent
from nexarq_cli.agents.builtin.review import ReviewAgent
from nexarq_cli.agents.builtin.architecture import ArchitectureAgent
from nexarq_cli.agents.builtin.devops import DevOpsAgent
from nexarq_cli.agents.builtin.refactor import RefactorAgent
from nexarq_cli.agents.builtin.docstring import DocstringAgent
from nexarq_cli.agents.builtin.type_safety import TypeSafetyAgent
from nexarq_cli.agents.builtin.test_coverage import TestCoverageAgent
from nexarq_cli.agents.builtin.dependency import DependencyAgent
from nexarq_cli.agents.builtin.api_design import APIDesignAgent
from nexarq_cli.agents.builtin.database import DatabaseAgent
from nexarq_cli.agents.builtin.concurrency import ConcurrencyAgent
from nexarq_cli.agents.builtin.error_handling import ErrorHandlingAgent
from nexarq_cli.agents.builtin.logging_agent import LoggingAgent
from nexarq_cli.agents.builtin.maintainability import MaintainabilityAgent
from nexarq_cli.agents.builtin.accessibility import AccessibilityAgent
from nexarq_cli.agents.builtin.compliance import ComplianceAgent
from nexarq_cli.agents.builtin.explain import ExplainAgent
from nexarq_cli.agents.builtin.memory_safety import MemorySafetyAgent
from nexarq_cli.agents.builtin.standards import StandardsAgent
from nexarq_cli.agents.builtin.i18n import I18nAgent
from nexarq_cli.agents.builtin.risk_scoring import RiskScoringAgent
from nexarq_cli.agents.builtin.summary import SummaryAgent
from nexarq_cli.agents.builtin.code_smells import CodeSmellsAgent
from nexarq_cli.agents.builtin.secrets_detection import SecretsDetectionAgent
from nexarq_cli.agents.builtin.ai_fixes import AIFixesAgent
from nexarq_cli.agents.builtin.style import StyleAgent
from nexarq_cli.agents.builtin.resource_usage import ResourceUsageAgent
from nexarq_cli.agents.builtin.next_steps import NextStepsAgent


class AgentRegistry:
    """Singleton registry for all available agents."""

    def __init__(self) -> None:
        self._agents: dict[str, type[BaseAgent]] = {}

    def register(self, cls: type[BaseAgent]) -> None:
        self._agents[cls.name] = cls

    def get(self, name: str) -> BaseAgent:
        cls = self._agents.get(name)
        if cls is None:
            raise KeyError(
                f"Unknown agent '{name}'. Available: {', '.join(self.names())}"
            )
        return cls()

    def names(self) -> list[str]:
        return sorted(self._agents.keys())

    def all_instances(self) -> list[BaseAgent]:
        return [cls() for cls in self._agents.values()]

    def descriptions(self) -> dict[str, str]:
        return {name: cls.description for name, cls in self._agents.items()}


REGISTRY = AgentRegistry()

_ALL_AGENTS: list[type[BaseAgent]] = [
    SecurityAgent, SecretsDetectionAgent,
    BugsAgent, ConcurrencyAgent, MemorySafetyAgent, ResourceUsageAgent,
    PerformanceAgent, ReviewAgent, CodeSmellsAgent, StyleAgent,
    RefactorAgent, MaintainabilityAgent, TypeSafetyAgent,
    ArchitectureAgent, APIDesignAgent, DatabaseAgent, DependencyAgent, ErrorHandlingAgent,
    DocstringAgent, TestCoverageAgent, LoggingAgent,
    ComplianceAgent, AccessibilityAgent, I18nAgent, StandardsAgent,
    DevOpsAgent,
    AIFixesAgent, RiskScoringAgent, ExplainAgent, SummaryAgent,
    NextStepsAgent,
]

for _agent_cls in _ALL_AGENTS:
    REGISTRY.register(_agent_cls)
