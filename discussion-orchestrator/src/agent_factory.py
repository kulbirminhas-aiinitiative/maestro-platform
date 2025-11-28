"""
Agent factory for creating AutoGen agents with execution-platform integration.

Creates AutoGen AssistantAgent instances configured to use execution-platform's
PersonaRouter for LLM interactions across different providers.
"""
from __future__ import annotations
from typing import Dict, List, Optional, Any
import logging

try:
    from autogen import AssistantAgent, UserProxyAgent
except ImportError:
    # Define stub classes if autogen not installed
    class AssistantAgent:
        def __init__(self, *args, **kwargs):
            raise ImportError("pyautogen is not installed. Install with: pip install pyautogen")

    class UserProxyAgent:
        def __init__(self, *args, **kwargs):
            raise ImportError("pyautogen is not installed. Install with: pip install pyautogen")

from .autogen_adapter import ExecutionPlatformLLM, AutoGenModelClient
from .models import AgentConfig

logger = logging.getLogger(__name__)


class AgentFactory:
    """
    Factory for creating AutoGen agents backed by execution-platform.

    This factory creates AutoGen AssistantAgent instances that use the
    execution-platform's LLM routing capabilities, allowing seamless integration
    with multiple LLM providers (Claude, GPT-4, Gemini, etc.).
    """

    def __init__(self):
        """Initialize the AgentFactory."""
        self._agents: Dict[str, AssistantAgent] = {}
        logger.info("AgentFactory initialized")

    def create_agent(
        self,
        agent_config: AgentConfig,
        system_message: Optional[str] = None,
        human_input_mode: str = "NEVER",
        max_consecutive_auto_reply: Optional[int] = None,
        **kwargs
    ) -> AssistantAgent:
        """
        Create an AutoGen AssistantAgent with execution-platform backend.

        Args:
            agent_config: Agent configuration from models
            system_message: Optional system message override
            human_input_mode: AutoGen human input mode (NEVER, TERMINATE, ALWAYS)
            max_consecutive_auto_reply: Max consecutive auto-replies
            **kwargs: Additional AutoGen configuration

        Returns:
            Configured AssistantAgent instance
        """
        try:
            # Create execution-platform LLM wrapper
            llm = ExecutionPlatformLLM(
                provider=agent_config.provider,
                temperature=agent_config.temperature,
                max_tokens=agent_config.max_tokens or 2048,
            )

            # Create model client wrapper for AutoGen
            model_client = AutoGenModelClient(llm)

            # Prepare system message
            final_system_message = system_message or agent_config.system_prompt
            if not final_system_message:
                final_system_message = (
                    f"You are {agent_config.persona}. "
                    "Provide thoughtful, well-reasoned responses to the discussion."
                )

            # Create AutoGen agent configuration
            llm_config = {
                "model": agent_config.model,
                "temperature": agent_config.temperature,
                "max_tokens": agent_config.max_tokens or 2048,
                "model_client": model_client,
            }

            # Merge with additional config
            llm_config.update(kwargs.get("llm_config", {}))

            # Create the agent
            agent = AssistantAgent(
                name=agent_config.agent_id,
                system_message=final_system_message,
                llm_config=llm_config,
                human_input_mode=human_input_mode,
                max_consecutive_auto_reply=max_consecutive_auto_reply or 10,
                **{k: v for k, v in kwargs.items() if k != "llm_config"}
            )

            # Cache the agent
            self._agents[agent_config.agent_id] = agent

            logger.info(
                f"Created agent '{agent_config.agent_id}' with provider "
                f"'{agent_config.provider}' and persona '{agent_config.persona}'"
            )

            return agent

        except Exception as e:
            logger.error(f"Failed to create agent: {e}", exc_info=True)
            raise

    def create_user_proxy(
        self,
        name: str = "User",
        human_input_mode: str = "ALWAYS",
        max_consecutive_auto_reply: int = 0,
        **kwargs
    ) -> UserProxyAgent:
        """
        Create a UserProxyAgent for human participation.

        Args:
            name: Agent name
            human_input_mode: How to handle human input
            max_consecutive_auto_reply: Max auto-replies
            **kwargs: Additional configuration

        Returns:
            Configured UserProxyAgent instance
        """
        try:
            agent = UserProxyAgent(
                name=name,
                human_input_mode=human_input_mode,
                max_consecutive_auto_reply=max_consecutive_auto_reply,
                code_execution_config=False,  # Disable code execution by default
                **kwargs
            )

            self._agents[name] = agent
            logger.info(f"Created user proxy agent '{name}'")

            return agent

        except Exception as e:
            logger.error(f"Failed to create user proxy: {e}", exc_info=True)
            raise

    def create_multiple_agents(
        self,
        agent_configs: List[AgentConfig],
        **kwargs
    ) -> List[AssistantAgent]:
        """
        Create multiple agents from a list of configurations.

        Args:
            agent_configs: List of agent configurations
            **kwargs: Common configuration for all agents

        Returns:
            List of created AssistantAgent instances
        """
        agents = []
        for config in agent_configs:
            try:
                agent = self.create_agent(config, **kwargs)
                agents.append(agent)
            except Exception as e:
                logger.error(f"Failed to create agent from config {config}: {e}")
                # Continue creating other agents even if one fails
                continue

        logger.info(f"Created {len(agents)} agents from {len(agent_configs)} configs")
        return agents

    def get_agent(self, agent_id: str) -> Optional[AssistantAgent]:
        """
        Get a cached agent by ID.

        Args:
            agent_id: Agent identifier

        Returns:
            AssistantAgent instance or None if not found
        """
        return self._agents.get(agent_id)

    def get_all_agents(self) -> Dict[str, AssistantAgent]:
        """
        Get all cached agents.

        Returns:
            Dictionary of agent_id -> AssistantAgent
        """
        return self._agents.copy()

    def clear_cache(self) -> None:
        """Clear the agent cache."""
        self._agents.clear()
        logger.info("Agent cache cleared")

    def remove_agent(self, agent_id: str) -> bool:
        """
        Remove an agent from the cache.

        Args:
            agent_id: Agent identifier

        Returns:
            True if removed, False if not found
        """
        if agent_id in self._agents:
            del self._agents[agent_id]
            logger.info(f"Removed agent '{agent_id}' from cache")
            return True
        return False


class PersonaTemplates:
    """
    Pre-defined persona templates for common agent roles.

    These templates provide starting points for system prompts based on
    common software development roles.
    """

    ARCHITECT = """You are a Software Architect with deep expertise in system design.
You focus on scalability, maintainability, and best practices. You think holistically
about system architecture and consider trade-offs between different approaches."""

    BACKEND_ENGINEER = """You are an experienced Backend Engineer specializing in
server-side development, APIs, and databases. You prioritize performance, reliability,
and security in your solutions."""

    FRONTEND_ENGINEER = """You are a Frontend Engineer with expertise in user interfaces
and user experience. You focus on creating intuitive, responsive, and accessible
applications using modern frontend technologies."""

    DEVOPS_ENGINEER = """You are a DevOps Engineer focused on infrastructure, CI/CD,
and automation. You optimize deployment pipelines, monitoring, and system reliability."""

    SECURITY_EXPERT = """You are a Security Expert specializing in application security,
threat modeling, and secure coding practices. You identify vulnerabilities and recommend
security best practices."""

    DATA_ENGINEER = """You are a Data Engineer with expertise in data pipelines,
ETL processes, and data warehousing. You design efficient data architectures and
optimize data processing."""

    QA_ENGINEER = """You are a Quality Assurance Engineer focused on testing strategies,
test automation, and ensuring software quality. You think critically about edge cases
and potential bugs."""

    PRODUCT_MANAGER = """You are a Product Manager who balances technical feasibility
with business value and user needs. You prioritize features based on impact and
help guide technical decisions with product context."""

    @classmethod
    def get_template(cls, role: str) -> Optional[str]:
        """
        Get system prompt template for a role.

        Args:
            role: Role name (case-insensitive)

        Returns:
            System prompt template or None if role not found
        """
        role_upper = role.upper().replace(" ", "_")
        return getattr(cls, role_upper, None)

    @classmethod
    def list_roles(cls) -> List[str]:
        """
        List all available role templates.

        Returns:
            List of role names
        """
        return [
            name.lower().replace("_", " ")
            for name in dir(cls)
            if name.isupper() and not name.startswith("_")
        ]
