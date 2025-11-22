"""
Base Agent Classes for Team Collaboration
"""

import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Optional, Dict, Any, List
from datetime import datetime

from claude_code_sdk import (
    ClaudeSDKClient,
    ClaudeCodeOptions,
    AssistantMessage,
    TextBlock,
    ResultMessage,
    McpSdkServerConfig
)


class AgentRole(str, Enum):
    """Agent role types"""
    ARCHITECT = "architect"
    DEVELOPER = "developer"
    REVIEWER = "reviewer"
    TESTER = "tester"
    COORDINATOR = "coordinator"
    ANALYST = "analyst"
    DEPLOYER = "deployer"


class AgentStatus(str, Enum):
    """Agent status"""
    IDLE = "idle"
    WORKING = "working"
    WAITING = "waiting"
    BLOCKED = "blocked"
    COMPLETED = "completed"


@dataclass
class AgentConfig:
    """Agent configuration"""
    agent_id: str
    role: AgentRole
    system_prompt: str = ""
    max_turns: int = 20
    auto_claim_tasks: bool = True
    communication_enabled: bool = True


class TeamAgent(ABC):
    """
    Base class for team agents with shared MCP coordination.

    All agents share the same MCP coordination server for:
    - Inter-agent messaging
    - Task claiming and completion
    - Knowledge sharing
    - Status updates
    - Collaborative decision making
    """

    def __init__(self, config: AgentConfig, coordination_server: McpSdkServerConfig):
        self.config = config
        self.agent_id = config.agent_id
        self.role = config.role
        self.coordination_server = coordination_server

        self.status = AgentStatus.IDLE
        self.current_task: Optional[str] = None
        self.client: Optional[ClaudeSDKClient] = None

        # Build system prompt
        self.system_prompt = config.system_prompt or self._build_system_prompt()

    def _build_system_prompt(self) -> str:
        """Build default system prompt based on role"""
        return f"""You are {self.agent_id}, a {self.role.value} agent in a multi-agent development team.

Role: {self.role.value.upper()}
Agent ID: {self.agent_id}

CAPABILITIES:
- Communicate with other team members via post_message/get_messages
- Claim and complete tasks from the team queue
- Share and retrieve knowledge with the team
- Update your status for team visibility
- Store and retrieve work artifacts
- Participate in team decisions

WORKFLOW:
1. Update your status when starting work
2. Check for messages from other agents
3. Claim tasks that match your role
4. Share knowledge and artifacts with the team
5. Communicate progress and blockers
6. Complete tasks with detailed results

COLLABORATION:
- Always check messages before claiming tasks
- Share relevant findings with the team
- Ask for help when blocked
- Vote on team decisions
- Store artifacts for team use

Use the coordination tools actively to work effectively with your team.
"""

    async def initialize(self):
        """Initialize agent and connect to coordination server"""
        options = ClaudeCodeOptions(
            mcp_servers={"coord": self.coordination_server},
            allowed_tools=[
                "post_message",
                "get_messages",
                "claim_task",
                "complete_task",
                "share_knowledge",
                "get_knowledge",
                "update_status",
                "get_team_status",
                "store_artifact",
                "get_artifacts",
                "propose_decision",
                "vote_decision"
            ],
            system_prompt=self.system_prompt,
            max_turns=self.config.max_turns
        )

        self.client = ClaudeSDKClient(options)
        await self.client.connect()

        # Register with team
        await self._update_status(AgentStatus.IDLE, "Initialized")

    async def _update_status(self, status: AgentStatus, task: str = ""):
        """Update agent status in shared workspace"""
        self.status = status
        self.current_task = task

        if self.client:
            await self.client.query(
                f"Update my status to '{status.value}' with current task: {task or 'none'}"
            )

            # Consume response
            async for _ in self.client.receive_response():
                pass

    async def send_message(self, to_agent: str, message: str, message_type: str = "info"):
        """Send message to another agent or broadcast to all"""
        if self.client:
            await self.client.query(
                f"Post a message to {to_agent}: '{message}' (type: {message_type})"
            )

            async for _ in self.client.receive_response():
                pass

    async def check_messages(self, limit: int = 5) -> List[str]:
        """Check messages from other agents"""
        messages = []

        if self.client:
            await self.client.query(f"Get the last {limit} messages for me")

            async for msg in self.client.receive_response():
                if isinstance(msg, AssistantMessage):
                    for block in msg.content:
                        if isinstance(block, TextBlock):
                            messages.append(block.text)

        return messages

    async def share_knowledge(self, key: str, value: str, category: str = "general"):
        """Share knowledge with the team"""
        if self.client:
            await self.client.query(
                f"Share knowledge: key='{key}', value='{value}', category='{category}'"
            )

            async for _ in self.client.receive_response():
                pass

    async def get_knowledge(self, key: str) -> Optional[str]:
        """Retrieve knowledge from team"""
        if self.client:
            await self.client.query(f"Get knowledge for key '{key}'")

            async for msg in self.client.receive_response():
                if isinstance(msg, AssistantMessage):
                    for block in msg.content:
                        if isinstance(block, TextBlock):
                            return block.text

        return None

    @abstractmethod
    async def execute_task(self, task_description: str) -> Dict[str, Any]:
        """Execute a specific task - implemented by subclasses"""
        pass

    async def run(self):
        """Main agent execution loop"""
        await self.initialize()

        try:
            if self.config.auto_claim_tasks:
                await self._auto_task_loop()
            else:
                await self._manual_task_loop()

        finally:
            await self.shutdown()

    async def _auto_task_loop(self):
        """Automatically claim and execute tasks"""
        await self._update_status(AgentStatus.IDLE, "Waiting for tasks")

        while True:
            # Check messages
            if self.config.communication_enabled:
                await self.check_messages()

            # Try to claim a task
            await self.client.query(
                f"Claim a task for my role '{self.role.value}'. "
                f"If you find a task, execute it and complete it with the result."
            )

            task_found = False
            async for msg in self.client.receive_response():
                if isinstance(msg, AssistantMessage):
                    for block in msg.content:
                        if isinstance(block, TextBlock) and "Task claimed" in block.text:
                            task_found = True
                            await self._update_status(AgentStatus.WORKING, block.text)

            if not task_found:
                # No tasks available, wait
                await asyncio.sleep(2)
            else:
                # Task completed, back to idle
                await self._update_status(AgentStatus.IDLE, "Task completed")
                await asyncio.sleep(0.5)

    async def _manual_task_loop(self):
        """Manual task execution - subclass controlled"""
        await self.execute_role_specific_work()

    @abstractmethod
    async def execute_role_specific_work(self):
        """Role-specific work implementation"""
        pass

    async def shutdown(self):
        """Shutdown agent"""
        await self._update_status(AgentStatus.COMPLETED, "Shutting down")

        if self.client:
            await self.client.disconnect()
