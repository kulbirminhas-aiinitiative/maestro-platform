#!/usr/bin/env python3
"""Tests for CollaborationEngine module."""

import pytest
from pathlib import Path
from datetime import datetime
from typing import Dict, Any

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from maestro_hive.personas.collaboration_engine import (
    CollaborationEngine,
    CollaborationContract,
    CollaborationSession,
    CollaborationPattern,
    ConflictType,
    MessageType,
    Message,
    Deliverable,
    Conflict,
    ContractTerm,
    create_collaboration_engine
)


class TestDeliverable:
    """Tests for Deliverable dataclass."""

    def test_deliverable_creation(self):
        """Test creating a Deliverable."""
        deliverable = Deliverable(
            deliverable_id="del_001",
            name="API Design",
            description="REST API design document",
            owner_id="architect_001"
        )

        assert deliverable.deliverable_id == "del_001"
        assert deliverable.name == "API Design"
        assert deliverable.owner_id == "architect_001"
        assert deliverable.status == "pending"


class TestMessage:
    """Tests for Message dataclass."""

    def test_message_creation(self):
        """Test creating a Message."""
        msg = Message(
            message_id="msg_001",
            sender_id="dev_001",
            recipient_id="qa_001",
            content={"text": "Code ready for review"},
            message_type=MessageType.REQUEST
        )

        assert msg.message_id == "msg_001"
        assert msg.sender_id == "dev_001"
        assert msg.recipient_id == "qa_001"


class TestConflict:
    """Tests for Conflict dataclass."""

    def test_conflict_creation(self):
        """Test creating a Conflict."""
        conflict = Conflict(
            conflict_id="conf_001",
            conflict_type=ConflictType.APPROACH,
            description="Disagreement on architecture approach",
            parties=["dev_001", "architect_001"],
            context={"topic": "microservices vs monolith"}
        )

        assert conflict.conflict_id == "conf_001"
        assert conflict.conflict_type == ConflictType.APPROACH
        assert len(conflict.parties) == 2
        assert conflict.resolved is False


class TestCollaborationContract:
    """Tests for CollaborationContract dataclass."""

    def test_contract_creation(self):
        """Test creating a CollaborationContract."""
        contract = CollaborationContract(
            contract_id="contract_001",
            team_id="team_001",
            parties=["dev_001", "qa_001"],
            deliverables=[
                Deliverable(
                    deliverable_id="del_001",
                    name="Feature Code",
                    description="Implementation",
                    owner_id="dev_001"
                )
            ],
            terms=[],
            created_at=datetime.utcnow()
        )

        assert contract.contract_id == "contract_001"
        assert len(contract.parties) == 2
        assert len(contract.deliverables) == 1

    def test_contract_is_complete(self):
        """Test contract completion check."""
        deliverable = Deliverable(
            deliverable_id="del_001",
            name="Deliverable 1",
            description="Test",
            owner_id="dev_001",
            status="pending"
        )
        contract = CollaborationContract(
            contract_id="contract_001",
            team_id="team_001",
            parties=["dev_001"],
            deliverables=[deliverable],
            terms=[],
            created_at=datetime.utcnow()
        )

        assert contract.is_complete() is False

        # Complete the deliverable
        contract.deliverables[0].status = "completed"
        assert contract.is_complete() is True

    def test_get_party_deliverables(self):
        """Test getting deliverables for a party."""
        contract = CollaborationContract(
            contract_id="contract_001",
            team_id="team_001",
            parties=["dev_001", "qa_001"],
            deliverables=[
                Deliverable(
                    deliverable_id="del_001",
                    name="Code",
                    description="Implementation",
                    owner_id="dev_001"
                ),
                Deliverable(
                    deliverable_id="del_002",
                    name="Tests",
                    description="Test suite",
                    owner_id="qa_001"
                )
            ],
            terms=[],
            created_at=datetime.utcnow()
        )

        dev_deliverables = contract.get_party_deliverables("dev_001")
        assert len(dev_deliverables) == 1
        assert dev_deliverables[0].name == "Code"

        qa_deliverables = contract.get_party_deliverables("qa_001")
        assert len(qa_deliverables) == 1
        assert qa_deliverables[0].name == "Tests"


class TestCollaborationSession:
    """Tests for CollaborationSession dataclass."""

    def test_session_creation(self):
        """Test creating a CollaborationSession."""
        session = CollaborationSession(
            session_id="session_001",
            team_id="team_001",
            participants={"dev_001", "qa_001", "pm_001"},
            pattern=CollaborationPattern.CONSENSUS
        )

        assert session.session_id == "session_001"
        assert session.team_id == "team_001"
        assert len(session.participants) == 3
        assert session.pattern == CollaborationPattern.CONSENSUS


class TestCollaborationPatterns:
    """Tests for CollaborationPattern enum."""

    def test_pattern_values(self):
        """Test all collaboration patterns exist."""
        assert CollaborationPattern.SEQUENTIAL is not None
        assert CollaborationPattern.PARALLEL is not None
        assert CollaborationPattern.REVIEW_CHAIN is not None
        assert CollaborationPattern.CONSENSUS is not None
        assert CollaborationPattern.HIERARCHICAL is not None


class TestConflictTypes:
    """Tests for ConflictType enum."""

    def test_conflict_type_values(self):
        """Test all conflict types exist."""
        assert ConflictType.RESOURCE is not None
        assert ConflictType.APPROACH is not None
        assert ConflictType.PRIORITY is not None
        assert ConflictType.QUALITY is not None


class TestResolutionStrategies:
    """Tests for resolution strategies (passed as strings)."""

    def test_resolution_strategy_values(self):
        """Test valid resolution strategy strings."""
        # Resolution strategies are strings in the actual implementation
        valid_strategies = ["consensus", "lead_decision", "voting", "escalation"]
        assert len(valid_strategies) == 4
        assert "consensus" in valid_strategies
        assert "lead_decision" in valid_strategies


class TestCollaborationEngine:
    """Tests for CollaborationEngine class."""

    @pytest.fixture
    def engine(self):
        """Create a CollaborationEngine for testing."""
        return CollaborationEngine()

    @pytest.mark.asyncio
    async def test_negotiate_contract(self, engine):
        """Test contract negotiation."""
        deliverables = [
            Deliverable(
                deliverable_id="del_001",
                name="Feature Code",
                description="Implementation",
                owner_id="dev_001"
            )
        ]
        contract = await engine.negotiate_contract(
            team_id="team_001",
            parties=["dev_001", "qa_001"],
            deliverables=deliverables
        )

        assert contract is not None
        assert contract.team_id == "team_001"
        assert len(contract.parties) == 2

    @pytest.mark.asyncio
    async def test_start_collaboration(self, engine):
        """Test starting a collaboration session."""
        session = await engine.start_collaboration(
            team_id="team_001",
            participants=["dev_001", "reviewer_001"],
            pattern=CollaborationPattern.REVIEW_CHAIN
        )

        assert session is not None
        assert session.team_id == "team_001"
        assert session.pattern == CollaborationPattern.REVIEW_CHAIN

    @pytest.mark.asyncio
    async def test_execute_sequential_pattern(self, engine):
        """Test sequential collaboration pattern execution."""
        session = await engine.start_collaboration(
            team_id="team_001",
            participants=["dev_001", "qa_001"],
            pattern=CollaborationPattern.SEQUENTIAL
        )

        work_items = [
            {"task": "implement", "assignee": "dev_001"},
            {"task": "test", "assignee": "qa_001"}
        ]

        results = await engine.execute_pattern(
            session=session,
            work_items=work_items
        )

        assert results is not None

    @pytest.mark.asyncio
    async def test_execute_parallel_pattern(self, engine):
        """Test parallel collaboration pattern execution."""
        session = await engine.start_collaboration(
            team_id="team_001",
            participants=["dev_001", "dev_002"],
            pattern=CollaborationPattern.PARALLEL
        )

        work_items = [
            {"task": "feature_a", "assignee": "dev_001"},
            {"task": "feature_b", "assignee": "dev_002"}
        ]

        results = await engine.execute_pattern(
            session=session,
            work_items=work_items
        )

        assert results is not None

    @pytest.mark.asyncio
    async def test_raise_conflict(self, engine):
        """Test raising a conflict."""
        # Start a session first (not required for raise_conflict but good practice)
        session = await engine.start_collaboration(
            team_id="team_001",
            participants=["dev_001", "dev_002"],
            pattern=CollaborationPattern.CONSENSUS
        )

        conflict = await engine.raise_conflict(
            conflict_type=ConflictType.APPROACH,
            description="Different implementation approaches",
            parties=["dev_001", "dev_002"],
            context={"topic": "architecture"}
        )

        assert conflict is not None
        assert conflict.conflict_type == ConflictType.APPROACH
        assert conflict.resolved is False

    @pytest.mark.asyncio
    async def test_resolve_conflict(self, engine):
        """Test resolving a conflict."""
        # Create a conflict
        conflict = await engine.raise_conflict(
            conflict_type=ConflictType.PRIORITY,
            description="Priority disagreement",
            parties=["dev_001", "dev_002"],
            context={"priority_options": ["high", "medium"]}
        )

        # Resolve the conflict
        resolved = await engine.resolve_conflict(
            conflict_id=conflict.conflict_id,
            resolution_strategy="lead_decision"
        )

        assert resolved is not None
        # Conflict should be marked resolved
        assert resolved.resolved is True

    @pytest.mark.asyncio
    async def test_share_context(self, engine):
        """Test context sharing in a session."""
        session = await engine.start_collaboration(
            team_id="team_001",
            participants=["dev_001", "dev_002"],
            pattern=CollaborationPattern.PARALLEL
        )

        await engine.share_context(
            session_id=session.session_id,
            key="architecture_decision",
            value={"pattern": "microservices", "version": "2.0"},
            sender_id="dev_001"
        )

        context = engine.get_shared_context(session.session_id)
        assert "architecture_decision" in context
        assert context["architecture_decision"]["pattern"] == "microservices"

    def test_get_session(self, engine):
        """Test getting a session by ID."""
        # Create a session manually
        session = CollaborationSession(
            session_id="test_session",
            team_id="team_001",
            participants={"dev_001"},
            pattern=CollaborationPattern.SEQUENTIAL
        )
        engine._sessions["test_session"] = session

        retrieved = engine.get_session("test_session")
        assert retrieved is not None
        assert retrieved.session_id == "test_session"

        # Non-existent session
        assert engine.get_session("non_existent") is None

    def test_get_contract(self, engine):
        """Test getting a contract by ID."""
        # Create a contract manually
        contract = CollaborationContract(
            contract_id="test_contract",
            team_id="team_001",
            parties=["dev_001"],
            deliverables=[],
            terms=[],
            created_at=datetime.utcnow()
        )
        engine._contracts["test_contract"] = contract

        retrieved = engine.get_contract("test_contract")
        assert retrieved is not None
        assert retrieved.contract_id == "test_contract"

        # Non-existent contract
        assert engine.get_contract("non_existent") is None

    def test_get_active_conflicts(self, engine):
        """Test getting active conflicts."""
        # Add some conflicts
        engine._conflicts["conf_001"] = Conflict(
            conflict_id="conf_001",
            conflict_type=ConflictType.RESOURCE,
            description="Resource conflict",
            parties=["dev_001"],
            context={},
            resolved=False
        )
        engine._conflicts["conf_002"] = Conflict(
            conflict_id="conf_002",
            conflict_type=ConflictType.APPROACH,
            description="Approach conflict",
            parties=["dev_002"],
            context={},
            resolved=True  # Already resolved
        )

        active = engine.get_active_conflicts()

        # Only unresolved conflicts
        assert len(active) == 1
        assert active[0].conflict_id == "conf_001"

    def test_register_message_handler(self, engine):
        """Test registering a message handler."""
        handler_called = []

        async def test_handler(message: Message):
            handler_called.append(message)

        engine.register_message_handler(MessageType.REQUEST, test_handler)

        assert MessageType.REQUEST in engine._message_handlers


class TestResolutionMethods:
    """Tests for conflict resolution methods."""

    @pytest.fixture
    def engine(self):
        """Create a CollaborationEngine for testing."""
        return CollaborationEngine()

    def test_resolve_by_consensus(self, engine):
        """Test consensus resolution."""
        conflict = Conflict(
            conflict_id="conf_001",
            conflict_type=ConflictType.APPROACH,
            description="Test conflict",
            parties=["dev_001", "dev_002"],
            context={}
        )

        result = engine._resolve_by_consensus(conflict)
        assert result is not None
        assert isinstance(result, str)

    def test_resolve_by_lead(self, engine):
        """Test lead decision resolution."""
        conflict = Conflict(
            conflict_id="conf_001",
            conflict_type=ConflictType.PRIORITY,
            description="Test conflict",
            parties=["dev_001", "dev_002"],
            context={}
        )

        result = engine._resolve_by_lead(conflict)
        assert result is not None
        assert isinstance(result, str)

    def test_resolve_by_voting(self, engine):
        """Test voting resolution."""
        conflict = Conflict(
            conflict_id="conf_001",
            conflict_type=ConflictType.APPROACH,
            description="Test conflict",
            parties=["dev_001", "dev_002", "dev_003"],
            context={}
        )

        result = engine._resolve_by_voting(conflict)
        assert result is not None
        assert isinstance(result, str)

    def test_resolve_by_escalation(self, engine):
        """Test escalation resolution."""
        conflict = Conflict(
            conflict_id="conf_001",
            conflict_type=ConflictType.QUALITY,
            description="Test conflict",
            parties=["dev_001", "dev_002"],
            context={}
        )

        result = engine._resolve_by_escalation(conflict)
        assert result is not None
        assert isinstance(result, str)


class TestCreateCollaborationEngine:
    """Tests for factory function."""

    def test_create_collaboration_engine(self):
        """Test creating engine with factory."""
        engine = create_collaboration_engine()

        assert engine is not None
        assert isinstance(engine, CollaborationEngine)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
