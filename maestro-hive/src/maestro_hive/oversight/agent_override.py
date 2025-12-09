"""
Agent Override Service
AC-1: Implement agent override mechanism (kill-switch)
EU AI Act Article 14 - Human intervention capability
EPIC: MD-2158
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from .compliance_logger import ComplianceLogger, ComplianceContext


class AgentState(Enum):
    """Agent execution states."""
    RUNNING = "running"
    PAUSED = "paused"
    STOPPED = "stopped"
    TERMINATED = "terminated"


class OverrideSeverity(Enum):
    """Override severity levels."""
    SOFT = "soft"  # Graceful stop
    HARD = "hard"  # Immediate termination


@dataclass
class AgentOverrideRequest:
    """Request to override an agent."""
    agent_id: str
    reason: str
    operator_id: str
    severity: OverrideSeverity
    context: Optional[ComplianceContext] = None


@dataclass
class AgentOverrideResult:
    """Result of an agent override operation."""
    success: bool
    agent_id: str
    previous_state: AgentState
    new_state: AgentState
    override_id: str
    timestamp: datetime
    audit_log_id: str


@dataclass
class AgentRecord:
    """Agent record in the system."""
    id: str
    state: AgentState
    last_override_id: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)


class AgentOverrideService:
    """
    Agent Override Service
    Provides kill-switch capability for AI agents with full audit trail.
    EU AI Act Article 14 compliant human intervention mechanism.
    """

    def __init__(
        self,
        logger: ComplianceLogger,
        db_client: Optional[Any] = None,
        message_queue: Optional[Any] = None,
        timeout_ms: int = 5000
    ):
        """
        Initialize agent override service.

        Args:
            logger: Compliance logger for audit trail
            db_client: Optional database client
            message_queue: Optional message queue for agent control
            timeout_ms: Override timeout in milliseconds
        """
        self._logger = logger
        self._db = db_client
        self._mq = message_queue
        self._timeout_ms = timeout_ms
        self._agents: Dict[str, AgentRecord] = {}
        self._overrides: Dict[str, Dict[str, Any]] = {}

    def _generate_override_id(self) -> str:
        """Generate unique override ID."""
        return f"ovr_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:8]}"

    async def override_agent(self, request: AgentOverrideRequest) -> AgentOverrideResult:
        """
        Override (stop) an agent immediately.
        This is the kill-switch capability required by EU AI Act Article 14.

        Args:
            request: Override request details

        Returns:
            AgentOverrideResult with operation outcome

        Raises:
            ValueError: If agent not found
        """
        agent = self._agents.get(request.agent_id)
        if not agent:
            raise ValueError(f"Agent not found: {request.agent_id}")

        previous_state = agent.state

        # Determine new state based on severity
        new_state = AgentState.TERMINATED if request.severity == OverrideSeverity.HARD else AgentState.STOPPED

        # Generate override ID
        override_id = self._generate_override_id()

        # Update agent state
        agent.state = new_state
        agent.last_override_id = override_id
        agent.updated_at = datetime.utcnow()

        # Record override
        self._overrides[override_id] = {
            "agent_id": request.agent_id,
            "operator_id": request.operator_id,
            "reason": request.reason,
            "severity": request.severity.value,
            "previous_state": previous_state.value,
            "new_state": new_state.value,
            "created_at": datetime.utcnow().isoformat(),
        }

        # Send control signal via message queue if available
        if self._mq:
            await self._mq.publish("agent.control", {
                "type": "override",
                "agent_id": request.agent_id,
                "override_id": override_id,
                "severity": request.severity.value,
                "command": "TERMINATE" if request.severity == OverrideSeverity.HARD else "STOP",
                "timestamp": datetime.utcnow().isoformat(),
            })

        # Log to compliance audit
        audit_entry = await self._logger.log_override(
            request.operator_id,
            request.agent_id,
            request.reason,
            request.severity.value,
            True,
            request.context
        )

        return AgentOverrideResult(
            success=True,
            agent_id=request.agent_id,
            previous_state=previous_state,
            new_state=new_state,
            override_id=override_id,
            timestamp=datetime.utcnow(),
            audit_log_id=audit_entry.id,
        )

    async def resume_agent(
        self,
        agent_id: str,
        override_id: str,
        operator_id: str,
        review_notes: Optional[str] = None
    ) -> AgentOverrideResult:
        """
        Resume an agent after override review.

        Args:
            agent_id: Agent to resume
            override_id: Original override ID
            operator_id: Operator performing resume
            review_notes: Optional review notes

        Returns:
            AgentOverrideResult with operation outcome

        Raises:
            ValueError: If agent or override not found, or agent terminated
        """
        # Verify override exists
        override = self._overrides.get(override_id)
        if not override:
            raise ValueError(f"Override not found: {override_id}")

        if override["agent_id"] != agent_id:
            raise ValueError(f"Override {override_id} does not match agent {agent_id}")

        # Get agent
        agent = self._agents.get(agent_id)
        if not agent:
            raise ValueError(f"Agent not found: {agent_id}")

        # Cannot resume terminated agent
        if agent.state == AgentState.TERMINATED:
            raise ValueError(f"Cannot resume terminated agent {agent_id}. Create new instance instead.")

        previous_state = agent.state
        new_state = AgentState.RUNNING

        # Update agent
        agent.state = new_state
        agent.last_override_id = None
        agent.updated_at = datetime.utcnow()

        # Generate resume ID
        resume_id = self._generate_override_id()

        # Send resume signal
        if self._mq:
            await self._mq.publish("agent.control", {
                "type": "resume",
                "agent_id": agent_id,
                "resume_id": resume_id,
                "related_override_id": override_id,
                "command": "START",
                "timestamp": datetime.utcnow().isoformat(),
            })

        # Log to audit
        from .compliance_logger import OversightActionType
        audit_entry = await self._logger.log_action(
            OversightActionType.RESUME,
            operator_id,
            agent_id,
            {
                "override_id": override_id,
                "review_notes": review_notes,
                "action_type": "agent_resume",
            }
        )

        return AgentOverrideResult(
            success=True,
            agent_id=agent_id,
            previous_state=previous_state,
            new_state=new_state,
            override_id=resume_id,
            timestamp=datetime.utcnow(),
            audit_log_id=audit_entry.id,
        )

    def register_agent(self, agent_id: str) -> AgentRecord:
        """Register a new agent for oversight."""
        agent = AgentRecord(
            id=agent_id,
            state=AgentState.RUNNING,
        )
        self._agents[agent_id] = agent
        return agent

    def get_agent_status(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """Get current status of an agent."""
        agent = self._agents.get(agent_id)
        if not agent:
            return None
        return {
            "agent_id": agent.id,
            "state": agent.state.value,
            "last_override_id": agent.last_override_id,
            "updated_at": agent.updated_at.isoformat(),
        }

    def list_active_overrides(self) -> List[Dict[str, Any]]:
        """List all active overrides."""
        active = []
        for override_id, override in self._overrides.items():
            agent = self._agents.get(override["agent_id"])
            if agent and agent.state in [AgentState.STOPPED, AgentState.TERMINATED]:
                if agent.last_override_id == override_id:
                    active.append({
                        "override_id": override_id,
                        **override
                    })
        return active

    async def emergency_stop_all(self, operator_id: str, reason: str) -> int:
        """
        Emergency stop all running agents.

        Args:
            operator_id: Operator performing emergency stop
            reason: Reason for emergency stop

        Returns:
            Number of agents stopped
        """
        stopped_count = 0
        for agent_id, agent in self._agents.items():
            if agent.state == AgentState.RUNNING:
                try:
                    await self.override_agent(AgentOverrideRequest(
                        agent_id=agent_id,
                        reason=f"EMERGENCY STOP: {reason}",
                        operator_id=operator_id,
                        severity=OverrideSeverity.HARD,
                    ))
                    stopped_count += 1
                except Exception:
                    pass  # Continue with other agents
        return stopped_count
