"""
CrewAI adapter — Nexarq review as a multi-agent crew.

Organises the 31 review agents into specialised CREWS that work together
like a real engineering team:

  ┌─────────────────────────────────────────────────────────────────┐
  │  SECURITY CREW   security · secrets_detection · memory_safety   │
  │  BUG CREW        bugs · concurrency · error_handling            │
  │  QUALITY CREW    review · code_smells · maintainability · style  │
  │  ARCH CREW       architecture · api_design · database · dep      │
  │  DOC CREW        docstring · standards · logging · compliance     │
  │  SYNTHESIS CREW  risk_scoring · summary · next_steps             │
  └─────────────────────────────────────────────────────────────────┘

Each crew runs its agents sequentially, and all crews are kicked off
together (parallel) by CrewAI's process engine.

Install:  pip install 'nexarq-cli[crewai]'  or  pip install crewai
"""
from __future__ import annotations

from typing import Iterator

from nexarq_cli.agents.base import AgentResult, Severity
from nexarq_cli.frameworks.base import FrameworkAdapter

# ── Crew definitions ───────────────────────────────────────────────────────────
# Each crew: (crew_name, crew_goal, [agent_names])

_CREWS: list[tuple[str, str, list[str]]] = [
    (
        "Security Crew",
        "Detect every security vulnerability, secret exposure, and memory safety issue.",
        ["security", "secrets_detection", "memory_safety"],
    ),
    (
        "Bug Detection Crew",
        "Find all logical errors, race conditions, and unhandled failure paths.",
        ["bugs", "concurrency", "error_handling"],
    ),
    (
        "Code Quality Crew",
        "Assess readability, smell, maintainability, style, types, and performance.",
        ["review", "code_smells", "maintainability", "style", "type_safety",
         "performance", "resource_usage"],
    ),
    (
        "Architecture Crew",
        "Evaluate design patterns, API contracts, database queries, and dependencies.",
        ["architecture", "api_design", "database", "dependency"],
    ),
    (
        "Documentation & Compliance Crew",
        "Check docstrings, standards, logging, accessibility, compliance, and i18n.",
        ["docstring", "standards", "logging_agent", "accessibility",
         "compliance", "i18n", "devops"],
    ),
    (
        "Testing Crew",
        "Identify missing test coverage and edge cases.",
        ["test_coverage"],
    ),
    (
        "Synthesis Crew",
        "Score overall risk, write an executive summary, and produce the action plan.",
        ["risk_scoring", "summary", "next_steps"],
    ),
]


class CrewAIAdapter(FrameworkAdapter):
    """
    Run Nexarq review agents as a CrewAI multi-crew pipeline.

    Each specialised crew handles one dimension of the review.
    Crews run in parallel; agents within a crew run sequentially.
    """

    framework_name = "crewai"

    def _check_import(self) -> None:
        import crewai  # noqa: F401

    # ── Public API ─────────────────────────────────────────────────────────────

    def run(
        self,
        diff: str,
        language: str,
        agent_names: list[str] | None = None,
        context: dict | None = None,
        diff_result=None,
    ) -> list[AgentResult]:
        return list(self.stream(diff, language, agent_names, context, diff_result=diff_result))

    def stream(
        self,
        diff: str,
        language: str,
        agent_names: list[str] | None = None,
        context: dict | None = None,
        diff_result=None,
    ) -> Iterator[AgentResult]:
        try:
            from crewai import Agent, Task, Crew, Process
        except ImportError as e:
            raise ImportError(
                "CrewAI not installed.\n"
                "Run: pip install 'nexarq-cli[crewai]'  or  pip install crewai"
            ) from e

        ctx = context or {}
        requested = set(agent_names) if agent_names else None

        # Get the user's configured LLM for CrewAI agents.
        # Without this, CrewAI defaults to OpenAI which may not be configured.
        lc_llm = None
        try:
            from nexarq_cli.frameworks.lc_llm import get_lc_llm
            lc_llm = get_lc_llm(self._config)
        except Exception:
            pass  # CrewAI will use its own default if lc_llm is None

        # Build one CrewAI Crew per logical crew group
        all_crews: list[Crew] = []
        crew_to_nexarq: list[tuple[str, list[str]]] = []  # (crew_name, [agent_names])

        for crew_name, crew_goal, members in _CREWS:
            # Only include members that are registered + enabled + requested
            active = [
                m for m in members
                if m in self._registry.names()
                and (requested is None or m in requested)
                and self._is_enabled(m)
            ]
            if not active:
                continue

            crew_agents: list[Agent] = []
            tasks:       list[Task]  = []
            last_task: Task | None   = None

            for name in active:
                nexarq_agent = self._registry.get(name)

                # Build the prompt for this agent
                agent_prompt = nexarq_agent.build_prompt(diff, language, ctx)

                # CrewAI Agent — role-based persona, uses user's configured LLM
                agent_kwargs: dict = dict(
                    role=f"{name.replace('_', ' ').title()} Specialist",
                    goal=nexarq_agent.description,
                    backstory=(
                        f"You are an expert {name.replace('_', ' ')} reviewer. "
                        f"You analyse code diffs and report only real, actionable findings "
                        f"in your domain. Be specific — cite file paths and line numbers."
                    ),
                    verbose=False,
                    allow_delegation=False,
                )
                if lc_llm is not None:
                    agent_kwargs["llm"] = lc_llm

                ca = Agent(**agent_kwargs)
                crew_agents.append(ca)

                # Task for this agent — sequential within the crew
                task = Task(
                    description=agent_prompt,
                    agent=ca,
                    expected_output=(
                        f"Structured {name} findings with severity, file references, "
                        "and concrete recommendations. If no issues found, say so briefly."
                    ),
                    context=[last_task] if last_task else [],
                )
                tasks.append(task)
                last_task = task

            crew = Crew(
                agents=crew_agents,
                tasks=tasks,
                process=Process.sequential,  # agents pass context to each other
                verbose=False,
            )
            all_crews.append(crew)
            crew_to_nexarq.append((crew_name, active))

        if not all_crews:
            return

        # Kick off all crews (CrewAI runs them, we wrap outputs into AgentResults)
        for crew, (crew_name, active_names) in zip(all_crews, crew_to_nexarq):
            try:
                crew_output = crew.kickoff()

                # Map CrewAI task outputs back to AgentResult objects
                tasks_output = (
                    crew_output.tasks_output
                    if hasattr(crew_output, "tasks_output")
                    else []
                )

                for name, task_out in zip(active_names, tasks_output):
                    nexarq_agent = self._registry.get(name)
                    text = (
                        task_out.raw if hasattr(task_out, "raw")
                        else str(task_out)
                    )
                    yield AgentResult(
                        agent_name=name,
                        severity=nexarq_agent.severity,
                        output=text,
                    )

            except Exception as exc:
                # If a whole crew fails, yield error results for each member
                for name in active_names:
                    nexarq_agent = self._registry.get(name)
                    yield AgentResult(
                        agent_name=name,
                        severity=Severity.INFO,
                        output="",
                        error=f"CrewAI crew '{crew_name}' failed: {exc}",
                    )

    # ── Helpers ────────────────────────────────────────────────────────────────

    def is_available(self) -> bool:
        try:
            import crewai  # noqa: F401
            return True
        except ImportError:
            return False

    def _is_enabled(self, name: str) -> bool:
        try:
            return self._config.effective_agent_config(name).enabled
        except Exception:
            return True
