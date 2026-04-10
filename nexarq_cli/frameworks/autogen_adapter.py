"""
AutoGen adapter (SRS 3.13).

Uses AutoGen's multi-agent conversation framework to run Nexarq agents
as specialised AssistantAgents in a group chat.

Each Nexarq agent is an AutoGen AssistantAgent with a role-specific system
prompt. A UserProxyAgent (nexarq_coordinator) initiates the conversation
with the diff and collects findings from all agents in turn.

Install: pip install pyautogen
"""
from __future__ import annotations

from typing import Iterator

from nexarq_cli.agents.base import AgentResult, Severity
from nexarq_cli.frameworks.base import FrameworkAdapter


class AutoGenAdapter(FrameworkAdapter):
    """
    Runs Nexarq agents as AutoGen AssistantAgents in a group conversation.

    The diff is the initial message. Each agent analyses it in turn and
    the UserProxyAgent terminates when all agents have responded.
    """

    framework_name = "autogen"

    def _check_import(self) -> None:
        import autogen  # noqa: F401

    # ── Public API ─────────────────────────────────────────────────────────────

    def run(
        self,
        diff: str,
        language: str,
        agent_names: list[str] | None = None,
        context: dict | None = None,
        diff_result=None,
    ) -> list[AgentResult]:
        """Execute agents via AutoGen group chat and return all results."""
        return list(self.stream(diff, language, agent_names, context, diff_result))

    def stream(
        self,
        diff: str,
        language: str,
        agent_names: list[str] | None = None,
        context: dict | None = None,
        diff_result=None,
    ) -> Iterator[AgentResult]:
        """
        Stream results using AutoGen group chat.

        Falls back to direct Nexarq agent execution if AutoGen is not
        installed — so the orchestrator can always call this safely.
        """
        ctx = dict(context or {})
        names = self._resolve_names(agent_names, diff_result)

        # Inject codebase context (RAG)
        if "_codebase_context" not in ctx and diff_result is not None:
            try:
                from nexarq_cli.rag.retriever import ContextRetriever
                codebase_ctx = ContextRetriever().retrieve(diff_result)
                if codebase_ctx:
                    ctx["_codebase_context"] = codebase_ctx
            except Exception:
                pass

        try:
            import autogen
        except ImportError:
            # AutoGen not installed — fall back to direct execution
            yield from self._stream_direct(names, diff, language, ctx)
            return

        # Build the LLM config from Nexarq provider settings
        llm_config = self._build_llm_config()

        # Build AutoGen AssistantAgents — one per Nexarq agent
        assistant_agents: list[autogen.AssistantAgent] = []
        name_to_nexarq: dict[str, str] = {}  # autogen_name → nexarq_name

        for name in names:
            try:
                nexarq_agent = self._registry.get(name)
            except Exception:
                continue

            # Build the agent's prompt as its system message
            agent_prompt = nexarq_agent.build_prompt(diff, language, ctx)
            system_msg = nexarq_agent._build_system(ctx)

            autogen_name = f"nexarq_{name}"
            assistant = autogen.AssistantAgent(
                name=autogen_name,
                system_message=(
                    f"{system_msg}\n\n"
                    f"Your specific role: {nexarq_agent.description}\n\n"
                    f"Analyze the following diff and report your findings:\n\n"
                    f"{agent_prompt}"
                ),
                llm_config=llm_config,
                human_input_mode="NEVER",
                max_consecutive_auto_reply=1,
            )
            assistant_agents.append(assistant)
            name_to_nexarq[autogen_name] = name

        if not assistant_agents:
            return

        # UserProxy to initiate and collect results
        user_proxy = autogen.UserProxyAgent(
            name="nexarq_coordinator",
            human_input_mode="NEVER",
            max_consecutive_auto_reply=0,
            code_execution_config=False,  # never execute code (SEC-7/8)
        )

        # Run each agent individually to collect structured AgentResults
        # (GroupChat ordering is non-deterministic; sequential gives us control)
        for assistant in assistant_agents:
            nexarq_name = name_to_nexarq[assistant.name]
            try:
                nexarq_agent = self._registry.get(nexarq_name)

                # Check cloud consent
                pcfg = self._config.effective_provider(nexarq_name)
                pname = str(pcfg.name.value if hasattr(pcfg.name, "value") else pcfg.name)
                if pname != "ollama" and not self._config.privacy.cloud_consent:
                    yield AgentResult(
                        agent_name=nexarq_name,
                        severity=nexarq_agent.severity,
                        output="",
                        error="Cloud provider blocked — cloud_consent is False",
                    )
                    continue

                # Initiate a 2-agent chat: coordinator → specialist
                chat_result = user_proxy.initiate_chat(
                    recipient=assistant,
                    message=f"Please perform your {nexarq_name} analysis now.",
                    max_turns=2,
                    silent=True,
                )

                # Extract the last assistant message as the finding
                output = ""
                if hasattr(chat_result, "chat_history"):
                    for msg in reversed(chat_result.chat_history):
                        if msg.get("role") == "assistant" or msg.get("name") == assistant.name:
                            output = msg.get("content", "")
                            break
                elif isinstance(chat_result, str):
                    output = chat_result

                yield AgentResult(
                    agent_name=nexarq_name,
                    severity=nexarq_agent.severity,
                    output=output,
                )

            except Exception as exc:
                yield AgentResult(
                    agent_name=nexarq_name,
                    severity=Severity.INFO,
                    output="",
                    error=f"AutoGen agent '{nexarq_name}' failed: {exc}",
                )

    # ── Helpers ────────────────────────────────────────────────────────────────

    def _stream_direct(
        self,
        names: list[str],
        diff: str,
        language: str,
        context: dict,
    ) -> Iterator[AgentResult]:
        """Direct fallback execution when AutoGen is not installed."""
        for name in names:
            try:
                agent = self._registry.get(name)
                provider = self._factory.get_for_agent(name)
                yield agent.run(diff, language, provider, context)
            except Exception as exc:
                yield AgentResult(
                    agent_name=name,
                    severity=Severity.INFO,
                    output="",
                    error=str(exc),
                )

    def _build_llm_config(self) -> dict:
        """Build AutoGen llm_config from the Nexarq provider config."""
        try:
            default_cfg = self._config.providers.get("default") or next(
                iter(self._config.providers.values())
            )
            name = str(
                default_cfg.name.value if hasattr(default_cfg.name, "value")
                else default_cfg.name
            )
            model = default_cfg.model

            if name == "ollama":
                base_url = getattr(default_cfg, "base_url", None) or "http://localhost:11434/v1"
                return {
                    "config_list": [{"model": model, "base_url": base_url, "api_key": "ollama"}],
                    "temperature": getattr(default_cfg, "temperature", 0.2),
                }
            elif name == "openai":
                import os
                api_key = getattr(default_cfg, "api_key", None) or os.environ.get("OPENAI_API_KEY", "")
                return {
                    "config_list": [{"model": model, "api_key": api_key}],
                    "temperature": getattr(default_cfg, "temperature", 0.2),
                }
            elif name == "anthropic":
                import os
                api_key = getattr(default_cfg, "api_key", None) or os.environ.get("ANTHROPIC_API_KEY", "")
                return {
                    "config_list": [{"model": model, "api_key": api_key}],
                    "temperature": getattr(default_cfg, "temperature", 0.2),
                }
            elif name == "google":
                import os
                api_key = getattr(default_cfg, "api_key", None) or os.environ.get("GOOGLE_API_KEY", "")
                return {
                    "config_list": [{"model": model, "api_key": api_key}],
                    "temperature": getattr(default_cfg, "temperature", 0.2),
                }
        except Exception:
            pass

        # Safe default — will fail gracefully if no key is set
        return {"config_list": [{"model": "gpt-4o-mini", "api_key": ""}]}

    def _resolve_names(self, agent_names: list[str] | None, diff_result) -> list[str]:
        from nexarq_cli.agents.selector import AgentSelector
        selector = AgentSelector(self._registry, self._config)
        if agent_names:
            return selector._filter_enabled(agent_names)
        if diff_result is not None:
            priority, parallel = selector.select(diff_result, None)
            return priority + parallel
        defaults = self._config.default_agents or list(self._registry.names())
        return selector._filter_enabled(defaults)

    def build_group_chat(self, diff: str, language: str, agent_names: list[str] | None = None):
        """
        Build an AutoGen GroupChat where each Nexarq agent is an AssistantAgent.
        Returns (group_chat, manager) for custom orchestration.
        """
        try:
            from autogen import AssistantAgent, UserProxyAgent, GroupChat, GroupChatManager
        except ImportError as e:
            raise RuntimeError("AutoGen not installed. Run: pip install pyautogen") from e

        names = self._resolve_names(agent_names, None)
        llm_config = self._build_llm_config()
        autogen_agents = []

        for name in names:
            try:
                nexarq_agent = self._registry.get(name)
            except Exception:
                continue
            assistant = AssistantAgent(
                name=f"nexarq_{name}",
                system_message=(
                    f"You are the {name} review specialist. "
                    f"Your focus: {nexarq_agent.description}. "
                    "Analyse the provided code diff and report findings."
                ),
                llm_config=llm_config,
            )
            autogen_agents.append(assistant)

        user_proxy = UserProxyAgent(
            name="nexarq_coordinator",
            human_input_mode="NEVER",
            max_consecutive_auto_reply=len(names),
            code_execution_config=False,
        )

        group_chat = GroupChat(
            agents=[user_proxy] + autogen_agents,
            messages=[],
            max_round=len(names) + 1,
        )
        manager = GroupChatManager(groupchat=group_chat, llm_config=llm_config)
        return group_chat, manager


def get_adapter_for(framework: str, config, factory, registry=None) -> FrameworkAdapter:
    """
    Factory function – return the correct adapter for a framework name.

    framework: 'langchain' | 'langgraph' | 'crewai' | 'autogen'
    """
    from nexarq_cli.frameworks.langchain_adapter import LangChainAdapter
    from nexarq_cli.frameworks.langgraph_adapter import LangGraphAdapter
    from nexarq_cli.frameworks.crewai_adapter import CrewAIAdapter

    from nexarq_cli.agents.registry import REGISTRY as _DEFAULT_REGISTRY

    reg = registry or _DEFAULT_REGISTRY
    _map = {
        "langchain": LangChainAdapter,
        "langgraph": LangGraphAdapter,
        "crewai": CrewAIAdapter,
        "autogen": AutoGenAdapter,
    }
    cls = _map.get(framework.lower())
    if cls is None:
        raise ValueError(
            f"Unknown framework '{framework}'. "
            f"Supported: {', '.join(_map.keys())}"
        )
    return cls(config, factory, reg)
