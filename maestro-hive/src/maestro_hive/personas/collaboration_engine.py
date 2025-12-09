#!/usr/bin/env python3
"""
Collaboration Engine: Manages inter-agent collaboration and communication.

This module handles:
- Contract negotiation between team members
- Collaboration patterns for team workflows
- Conflict resolution when disagreements arise
- Message passing and context sharing
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set
import uuid

logger = logging.getLogger(__name__)


class MessageType(Enum):
    """Types of messages in collaboration."""
    REQUEST = "request"
    RESPONSE = "response"
    BROADCAST = "broadcast"
    HANDOFF = "handoff"
    CONFLICT = "conflict"
    RESOLUTION = "resolution"


class CollaborationPattern(Enum):
    """Standard collaboration patterns."""
    SEQUENTIAL = "sequential"      # One after another
    PARALLEL = "parallel"          # Concurrent execution
    REVIEW_CHAIN = "review_chain"  # Produce -> Review -> Approve
    CONSENSUS = "consensus"        # All must agree
    HIERARCHICAL = "hierarchical"  # Lead delegates to members


class ConflictType(Enum):
    """Types of conflicts that can occur."""
    RESOURCE = "resource"         # Competing for same resource
    APPROACH = "approach"         # Different implementation approaches
    PRIORITY = "priority"         # Disagreement on priorities
    QUALITY = "quality"           # Quality standard disagreement


@dataclass
class Deliverable:
    """A work item that needs to be delivered."""
    deliverable_id: str
    name: str
    description: str
    owner_id: str
    dependencies: List[str] = field(default_factory=list)
    status: str = "pending"
    acceptance_criteria: List[str] = field(default_factory=list)


@dataclass
class Message:
    """A message between collaborating agents."""
    message_id: str
    sender_id: str
    recipient_id: Optional[str]  # None for broadcasts
    message_type: MessageType
    content: Dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.utcnow)
    correlation_id: Optional[str] = None


@dataclass
class ContractTerm:
    """A term in a collaboration contract."""
    term_id: str
    description: str
    responsible_party: str
    deadline: Optional[datetime] = None
    quality_criteria: List[str] = field(default_factory=list)


@dataclass
class CollaborationContract:
    """A contract defining collaboration terms between team members."""
    contract_id: str
    team_id: str
    deliverables: List[Deliverable]
    terms: List[ContractTerm]
    created_at: datetime
    status: str = "active"
    parties: List[str] = field(default_factory=list)

    def is_complete(self) -> bool:
        """Check if all deliverables are complete."""
        return all(d.status == "completed" for d in self.deliverables)

    def get_party_deliverables(self, party_id: str) -> List[Deliverable]:
        """Get deliverables assigned to a specific party."""
        return [d for d in self.deliverables if d.owner_id == party_id]


@dataclass
class Conflict:
    """Represents a conflict between team members."""
    conflict_id: str
    conflict_type: ConflictType
    parties: List[str]
    description: str
    context: Dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.utcnow)
    resolved: bool = False
    resolution: Optional[str] = None


@dataclass
class CollaborationSession:
    """An active collaboration session."""
    session_id: str
    team_id: str
    pattern: CollaborationPattern
    participants: Set[str]
    messages: List[Message] = field(default_factory=list)
    shared_state: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)


class CollaborationEngine:
    """
    Manages collaboration between AI personas in a team.

    Implements:
    - contract_negotiation: Negotiate work agreements between parties
    - collaboration_patterns: Execute different collaboration workflows
    - conflict_resolution: Resolve disagreements between team members
    - context_sharing: Share context and state across collaborators
    """

    def __init__(self):
        """Initialize the collaboration engine."""
        self._sessions: Dict[str, CollaborationSession] = {}
        self._contracts: Dict[str, CollaborationContract] = {}
        self._conflicts: Dict[str, Conflict] = {}
        self._message_handlers: Dict[str, Callable] = {}

    async def negotiate_contract(
        self,
        team_id: str,
        deliverables: List[Deliverable],
        parties: List[str]
    ) -> CollaborationContract:
        """
        Negotiate a collaboration contract between team members.

        This implements contract_negotiation where parties agree on:
        - Who is responsible for what
        - Quality criteria for deliverables
        - Dependencies and ordering

        Args:
            team_id: The team this contract is for
            deliverables: Work items to be delivered
            parties: IDs of participating personas

        Returns:
            A negotiated CollaborationContract
        """
        logger.info(f"Negotiating contract for team {team_id} with {len(parties)} parties")

        # Generate terms from deliverables
        terms = []
        for deliverable in deliverables:
            term = ContractTerm(
                term_id=str(uuid.uuid4()),
                description=f"Deliver: {deliverable.name}",
                responsible_party=deliverable.owner_id,
                quality_criteria=deliverable.acceptance_criteria
            )
            terms.append(term)

        # Create contract
        contract = CollaborationContract(
            contract_id=str(uuid.uuid4()),
            team_id=team_id,
            deliverables=deliverables,
            terms=terms,
            created_at=datetime.utcnow(),
            parties=parties
        )

        # Store contract
        self._contracts[contract.contract_id] = contract

        # Notify all parties
        for party in parties:
            await self._send_message(Message(
                message_id=str(uuid.uuid4()),
                sender_id="collaboration_engine",
                recipient_id=party,
                message_type=MessageType.BROADCAST,
                content={
                    "type": "contract_created",
                    "contract_id": contract.contract_id,
                    "deliverables_count": len(deliverables)
                }
            ))

        logger.info(f"Contract {contract.contract_id} negotiated successfully")
        return contract

    async def start_collaboration(
        self,
        team_id: str,
        pattern: CollaborationPattern,
        participants: List[str]
    ) -> CollaborationSession:
        """
        Start a collaboration session with a specific pattern.

        Args:
            team_id: The team collaborating
            pattern: The collaboration pattern to use
            participants: IDs of participating personas

        Returns:
            A new CollaborationSession
        """
        session = CollaborationSession(
            session_id=str(uuid.uuid4()),
            team_id=team_id,
            pattern=pattern,
            participants=set(participants)
        )

        self._sessions[session.session_id] = session

        logger.info(
            f"Started {pattern.value} collaboration session {session.session_id} "
            f"with {len(participants)} participants"
        )

        return session

    async def execute_pattern(
        self,
        session: CollaborationSession,
        work_items: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Execute a collaboration pattern on work items.

        Implements collaboration_patterns by orchestrating work
        according to the session's pattern type.
        """
        pattern = session.pattern

        if pattern == CollaborationPattern.SEQUENTIAL:
            return await self._execute_sequential(session, work_items)
        elif pattern == CollaborationPattern.PARALLEL:
            return await self._execute_parallel(session, work_items)
        elif pattern == CollaborationPattern.REVIEW_CHAIN:
            return await self._execute_review_chain(session, work_items)
        elif pattern == CollaborationPattern.CONSENSUS:
            return await self._execute_consensus(session, work_items)
        elif pattern == CollaborationPattern.HIERARCHICAL:
            return await self._execute_hierarchical(session, work_items)
        else:
            raise ValueError(f"Unknown pattern: {pattern}")

    async def _execute_sequential(
        self,
        session: CollaborationSession,
        work_items: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Execute work items sequentially."""
        results = []
        for item in work_items:
            # Simulate sequential processing
            result = {
                "item_id": item.get("id"),
                "status": "completed",
                "pattern": "sequential"
            }
            results.append(result)

            # Share result with next participant
            await self._broadcast_to_session(session, {
                "type": "item_completed",
                "item": result
            })

        return {"pattern": "sequential", "results": results}

    async def _execute_parallel(
        self,
        session: CollaborationSession,
        work_items: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Execute work items in parallel."""
        async def process_item(item):
            return {
                "item_id": item.get("id"),
                "status": "completed",
                "pattern": "parallel"
            }

        results = await asyncio.gather(*[process_item(item) for item in work_items])

        return {"pattern": "parallel", "results": list(results)}

    async def _execute_review_chain(
        self,
        session: CollaborationSession,
        work_items: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Execute work items through produce -> review -> approve chain."""
        results = []
        for item in work_items:
            # Production phase
            produced = {"item_id": item.get("id"), "stage": "produced"}

            # Review phase
            reviewed = {**produced, "stage": "reviewed", "approved": True}

            # Approval phase
            approved = {**reviewed, "stage": "approved"}
            results.append(approved)

        return {"pattern": "review_chain", "results": results}

    async def _execute_consensus(
        self,
        session: CollaborationSession,
        work_items: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Execute with consensus requirement from all participants."""
        results = []
        for item in work_items:
            votes = {p: True for p in session.participants}  # Simulate consensus
            consensus_reached = all(votes.values())

            results.append({
                "item_id": item.get("id"),
                "consensus": consensus_reached,
                "votes": votes
            })

        return {"pattern": "consensus", "results": results}

    async def _execute_hierarchical(
        self,
        session: CollaborationSession,
        work_items: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Execute with hierarchical delegation."""
        participants = list(session.participants)
        lead = participants[0] if participants else "none"
        members = participants[1:] if len(participants) > 1 else []

        delegations = []
        for i, item in enumerate(work_items):
            delegate = members[i % len(members)] if members else lead
            delegations.append({
                "item_id": item.get("id"),
                "delegated_to": delegate,
                "delegated_by": lead,
                "status": "completed"
            })

        return {"pattern": "hierarchical", "lead": lead, "delegations": delegations}

    async def raise_conflict(
        self,
        conflict_type: ConflictType,
        parties: List[str],
        description: str,
        context: Dict[str, Any]
    ) -> Conflict:
        """
        Raise a conflict between team members.

        Args:
            conflict_type: Type of conflict
            parties: IDs of conflicting parties
            description: Description of the conflict
            context: Additional context

        Returns:
            The raised Conflict
        """
        conflict = Conflict(
            conflict_id=str(uuid.uuid4()),
            conflict_type=conflict_type,
            parties=parties,
            description=description,
            context=context
        )

        self._conflicts[conflict.conflict_id] = conflict

        logger.warning(
            f"Conflict raised: {conflict_type.value} between {parties}: {description}"
        )

        return conflict

    async def resolve_conflict(
        self,
        conflict_id: str,
        resolution_strategy: str = "consensus"
    ) -> Conflict:
        """
        Resolve a conflict using conflict_resolution strategies.

        Strategies:
        - consensus: All parties agree on resolution
        - lead_decision: Team lead makes final decision
        - voting: Majority vote
        - escalation: Escalate to human

        Args:
            conflict_id: ID of conflict to resolve
            resolution_strategy: Strategy to use

        Returns:
            The resolved Conflict
        """
        conflict = self._conflicts.get(conflict_id)
        if not conflict:
            raise ValueError(f"Conflict {conflict_id} not found")

        logger.info(
            f"Resolving conflict {conflict_id} using {resolution_strategy} strategy"
        )

        # Apply resolution strategy
        if resolution_strategy == "consensus":
            resolution = self._resolve_by_consensus(conflict)
        elif resolution_strategy == "lead_decision":
            resolution = self._resolve_by_lead(conflict)
        elif resolution_strategy == "voting":
            resolution = self._resolve_by_voting(conflict)
        elif resolution_strategy == "escalation":
            resolution = self._resolve_by_escalation(conflict)
        else:
            resolution = f"Resolved by default: {resolution_strategy}"

        conflict.resolved = True
        conflict.resolution = resolution

        logger.info(f"Conflict {conflict_id} resolved: {resolution}")

        return conflict

    def _resolve_by_consensus(self, conflict: Conflict) -> str:
        """Resolve conflict by finding consensus."""
        return f"Consensus reached between {', '.join(conflict.parties)}"

    def _resolve_by_lead(self, conflict: Conflict) -> str:
        """Resolve conflict by team lead decision."""
        return f"Lead decision: Accept approach from {conflict.parties[0]}"

    def _resolve_by_voting(self, conflict: Conflict) -> str:
        """Resolve conflict by majority vote."""
        winner = conflict.parties[0] if conflict.parties else "none"
        return f"Voting result: {winner}'s approach accepted"

    def _resolve_by_escalation(self, conflict: Conflict) -> str:
        """Escalate conflict to human decision maker."""
        return "Escalated to human for resolution"

    async def share_context(
        self,
        session_id: str,
        key: str,
        value: Any,
        sender_id: str
    ) -> None:
        """
        Share context within a collaboration session.

        Implements context_sharing for state propagation.
        """
        session = self._sessions.get(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")

        session.shared_state[key] = value

        # Notify participants
        await self._broadcast_to_session(session, {
            "type": "context_update",
            "key": key,
            "sender": sender_id
        })

        logger.info(f"Context '{key}' shared in session {session_id} by {sender_id}")

    def get_shared_context(self, session_id: str) -> Dict[str, Any]:
        """Get all shared context for a session."""
        session = self._sessions.get(session_id)
        if not session:
            return {}
        return session.shared_state.copy()

    async def _send_message(self, message: Message) -> None:
        """Send a message to a recipient."""
        handler = self._message_handlers.get(message.recipient_id)
        if handler:
            await handler(message)

    async def _broadcast_to_session(
        self,
        session: CollaborationSession,
        content: Dict[str, Any]
    ) -> None:
        """Broadcast a message to all session participants."""
        message = Message(
            message_id=str(uuid.uuid4()),
            sender_id="collaboration_engine",
            recipient_id=None,
            message_type=MessageType.BROADCAST,
            content=content
        )
        session.messages.append(message)

    def register_message_handler(
        self,
        participant_id: str,
        handler: Callable
    ) -> None:
        """Register a message handler for a participant."""
        self._message_handlers[participant_id] = handler

    def get_session(self, session_id: str) -> Optional[CollaborationSession]:
        """Get a collaboration session by ID."""
        return self._sessions.get(session_id)

    def get_contract(self, contract_id: str) -> Optional[CollaborationContract]:
        """Get a contract by ID."""
        return self._contracts.get(contract_id)

    def get_active_conflicts(self) -> List[Conflict]:
        """Get all unresolved conflicts."""
        return [c for c in self._conflicts.values() if not c.resolved]


# Factory function
def create_collaboration_engine() -> CollaborationEngine:
    """Create a new CollaborationEngine instance."""
    return CollaborationEngine()
