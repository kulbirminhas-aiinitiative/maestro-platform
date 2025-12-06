#!/usr/bin/env python3
"""
SQLAlchemy models for Capability Registry.

JIRA: MD-2063 (part of MD-2042)
Description: ORM models for agent capability management including:
- Agent profiles
- Capabilities (taxonomy)
- Agent-capability junction with proficiency
- Quality history tracking
- Capability groups
"""

from sqlalchemy import (
    Column, String, Integer, Float, Boolean, Text, DateTime,
    ForeignKey, Enum as SQLEnum, Index, UniqueConstraint, CheckConstraint,
    ARRAY
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
from enum import Enum
import uuid

# Use the same Base from models.py for consistency
# If running standalone, create a new Base
try:
    from .models import Base
except ImportError:
    Base = declarative_base()


# =============================================================================
# Enums
# =============================================================================

class AvailabilityStatus(str, Enum):
    """Agent availability states"""
    AVAILABLE = "available"
    BUSY = "busy"
    OFFLINE = "offline"


class CapabilitySource(str, Enum):
    """How capability proficiency was determined"""
    MANUAL = "manual"
    INFERRED = "inferred"
    HISTORICAL = "historical"
    ASSESSMENT = "assessment"


# =============================================================================
# Models
# =============================================================================

class CapabilityAgent(Base):
    """
    Agent profile for capability registry.

    Stores agent information including availability, work limits,
    and links to capabilities and quality history.
    """
    __tablename__ = "capability_agents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_id = Column(String(255), unique=True, nullable=False)
    name = Column(String(255), nullable=False)
    persona_type = Column(String(100), nullable=True)
    availability_status = Column(
        String(20),
        default=AvailabilityStatus.OFFLINE.value,
        nullable=False
    )
    wip_limit = Column(Integer, default=3)
    current_wip = Column(Integer, default=0)
    agent_metadata = Column(JSONB, default=dict)  # Renamed from 'metadata' (reserved)
    last_active = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    capabilities = relationship(
        "AgentCapability",
        back_populates="agent",
        cascade="all, delete-orphan"
    )
    quality_history = relationship(
        "AgentQualityHistory",
        back_populates="agent",
        cascade="all, delete-orphan"
    )

    # Constraints and indexes
    __table_args__ = (
        CheckConstraint('wip_limit >= 0', name='check_wip_limit_positive'),
        CheckConstraint('current_wip >= 0', name='check_current_wip_positive'),
        CheckConstraint(
            "availability_status IN ('available', 'busy', 'offline')",
            name='check_valid_availability_status'
        ),
        Index('idx_capability_agents_agent_id', 'agent_id'),
        Index('idx_capability_agents_persona_type', 'persona_type'),
        Index('idx_capability_agents_availability', 'availability_status'),
    )

    def __repr__(self):
        return f"<CapabilityAgent(agent_id={self.agent_id}, name={self.name}, status={self.availability_status})>"

    def to_dict(self):
        return {
            "id": str(self.id),
            "agent_id": self.agent_id,
            "name": self.name,
            "persona_type": self.persona_type,
            "availability_status": self.availability_status,
            "wip_limit": self.wip_limit,
            "current_wip": self.current_wip,
            "metadata": self.agent_metadata or {},
            "last_active": self.last_active.isoformat() if self.last_active else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class Capability(Base):
    """
    Master list of capabilities from the taxonomy.

    Supports hierarchical structure via parent_skill_id and
    versioning for capability evolution.
    """
    __tablename__ = "capabilities"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    skill_id = Column(String(255), unique=True, nullable=False)  # e.g., "Backend:Python:FastAPI"
    parent_skill_id = Column(String(255), nullable=True)  # Hierarchy reference
    category = Column(String(100), nullable=True)  # Top-level category
    version = Column(String(20), default="1.0.0")
    description = Column(Text, nullable=True)
    deprecated = Column(Boolean, default=False)
    successor_skill_id = Column(String(255), nullable=True)  # For deprecated skills
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    # Relationships
    agent_capabilities = relationship(
        "AgentCapability",
        back_populates="capability",
        cascade="all, delete-orphan"
    )

    # Indexes
    __table_args__ = (
        Index('idx_capabilities_skill_id', 'skill_id'),
        Index('idx_capabilities_parent', 'parent_skill_id'),
        Index('idx_capabilities_category', 'category'),
    )

    def __repr__(self):
        return f"<Capability(skill_id={self.skill_id}, category={self.category})>"

    def to_dict(self):
        return {
            "id": str(self.id),
            "skill_id": self.skill_id,
            "parent_skill_id": self.parent_skill_id,
            "category": self.category,
            "version": self.version,
            "description": self.description,
            "deprecated": self.deprecated,
            "successor_skill_id": self.successor_skill_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class AgentCapability(Base):
    """
    Junction table linking agents to their capabilities.

    Tracks proficiency levels, confidence scores, and usage statistics.
    """
    __tablename__ = "agent_capabilities"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_id = Column(
        UUID(as_uuid=True),
        ForeignKey("capability_agents.id", ondelete="CASCADE"),
        nullable=False
    )
    capability_id = Column(
        UUID(as_uuid=True),
        ForeignKey("capabilities.id", ondelete="CASCADE"),
        nullable=False
    )
    proficiency = Column(Integer, nullable=False)  # 1-5 scale
    source = Column(String(50), default=CapabilitySource.MANUAL.value)
    confidence = Column(Float, default=1.0)  # 0.0-1.0
    last_used = Column(DateTime(timezone=True), nullable=True)
    execution_count = Column(Integer, default=0)
    success_count = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    agent = relationship("CapabilityAgent", back_populates="capabilities")
    capability = relationship("Capability", back_populates="agent_capabilities")

    # Constraints and indexes
    __table_args__ = (
        UniqueConstraint('agent_id', 'capability_id', name='uq_agent_capability'),
        CheckConstraint('proficiency BETWEEN 1 AND 5', name='check_proficiency_range'),
        CheckConstraint('confidence BETWEEN 0.0 AND 1.0', name='check_confidence_range'),
        CheckConstraint('execution_count >= 0', name='check_execution_count_positive'),
        CheckConstraint('success_count >= 0', name='check_success_count_positive'),
        CheckConstraint(
            "source IN ('manual', 'inferred', 'historical', 'assessment')",
            name='check_valid_source'
        ),
        Index('idx_agent_capabilities_agent', 'agent_id'),
        Index('idx_agent_capabilities_capability', 'capability_id'),
        Index('idx_agent_capabilities_proficiency', 'proficiency'),
    )

    def __repr__(self):
        return f"<AgentCapability(agent={self.agent_id}, capability={self.capability_id}, proficiency={self.proficiency})>"

    def to_dict(self):
        return {
            "id": str(self.id),
            "agent_id": str(self.agent_id),
            "capability_id": str(self.capability_id),
            "proficiency": self.proficiency,
            "source": self.source,
            "confidence": self.confidence,
            "last_used": self.last_used.isoformat() if self.last_used else None,
            "execution_count": self.execution_count,
            "success_count": self.success_count,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    @property
    def success_rate(self) -> float:
        """Calculate success rate from execution history."""
        if self.execution_count == 0:
            return 0.0
        return self.success_count / self.execution_count


class AgentQualityHistory(Base):
    """
    Historical quality scores for agent performance tracking.

    Records quality scores, execution times, and skills used
    for trending and proficiency adjustment.
    """
    __tablename__ = "agent_quality_history"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_id = Column(
        UUID(as_uuid=True),
        ForeignKey("capability_agents.id", ondelete="CASCADE"),
        nullable=False
    )
    task_id = Column(String(255), nullable=True)  # External task reference
    quality_score = Column(Float, nullable=True)  # 0.0-1.0
    execution_time_ms = Column(Integer, nullable=True)
    skill_id = Column(String(255), nullable=True)  # Which capability was used
    recorded_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    # Relationships
    agent = relationship("CapabilityAgent", back_populates="quality_history")

    # Constraints and indexes
    __table_args__ = (
        CheckConstraint('quality_score BETWEEN 0.0 AND 1.0', name='check_quality_score_range'),
        Index('idx_quality_history_agent', 'agent_id'),
        Index('idx_quality_history_recorded', 'recorded_at'),
        Index('idx_quality_history_agent_recent', 'agent_id', 'recorded_at'),
    )

    def __repr__(self):
        return f"<AgentQualityHistory(agent={self.agent_id}, score={self.quality_score}, task={self.task_id})>"

    def to_dict(self):
        return {
            "id": str(self.id),
            "agent_id": str(self.agent_id),
            "task_id": self.task_id,
            "quality_score": self.quality_score,
            "execution_time_ms": self.execution_time_ms,
            "skill_id": self.skill_id,
            "recorded_at": self.recorded_at.isoformat() if self.recorded_at else None,
        }


class CapabilityGroup(Base):
    """
    Predefined groups of related capabilities.

    Examples: FullStackWeb, BackendAPI, DevOpsEngineer
    """
    __tablename__ = "capability_groups"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    group_name = Column(String(100), unique=True, nullable=False)
    description = Column(Text, nullable=True)
    skill_ids = Column(ARRAY(Text), nullable=False)  # Array of skill_ids
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    # Indexes
    __table_args__ = (
        Index('idx_capability_groups_name', 'group_name'),
    )

    def __repr__(self):
        return f"<CapabilityGroup(name={self.group_name}, skills={len(self.skill_ids or [])})>"

    def to_dict(self):
        return {
            "id": str(self.id),
            "group_name": self.group_name,
            "description": self.description,
            "skill_ids": self.skill_ids or [],
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    'AvailabilityStatus',
    'CapabilitySource',
    'CapabilityAgent',
    'Capability',
    'AgentCapability',
    'AgentQualityHistory',
    'CapabilityGroup',
]
