#!/usr/bin/env python3
"""
Database models for Maestro ML Platform - WITH MULTI-TENANCY

GAP FIX: Added tenant_id to all models (Task 2.1.1)
Addresses meta-review Gap 2.1: Multi-Tenancy Database Integration

Changes from original database.py:
1. Added Tenant model
2. Added tenant_id to all core models (Project, Artifact, etc.)
3. Added indexes for tenant_id fields
4. Added composite indexes for (tenant_id, created_at)
5. Updated Pydantic models to include tenant_id
"""

from sqlalchemy import (
    Column, String, Integer, Float, DateTime, Text, JSON, ForeignKey, Boolean, Index
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.types import TypeDecorator
import json
from datetime import datetime
import uuid

Base = declarative_base()


class JSONEncodedList(TypeDecorator):
    """Enables JSON storage for lists - works in both PostgreSQL and SQLite"""
    impl = Text
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return '[]'
        return json.dumps(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return []
        return json.loads(value)


class Tenant(Base):
    """
    Tenant model for multi-tenancy

    NEW: Added for multi-tenancy support
    Each organization/customer is a separate tenant.
    """
    __tablename__ = "tenants"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False, unique=True)
    slug = Column(String(100), nullable=False, unique=True)  # URL-friendly identifier
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

    # Subscription/limits
    max_users = Column(Integer, default=10)
    max_projects = Column(Integer, default=100)
    max_artifacts = Column(Integer, default=1000)

    # Metadata
    meta = Column(JSON)  # Flexible additional data (plan tier, features, etc.)

    # Relationships
    projects = relationship("Project", back_populates="tenant", cascade="all, delete-orphan")
    artifacts = relationship("Artifact", back_populates="tenant", cascade="all, delete-orphan")
    users = relationship("User", back_populates="tenant", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Tenant(name='{self.name}', slug='{self.slug}', active={self.is_active})>"


class User(Base):
    """
    User model for authentication and authorization
    
    NEW: Added for authentication support (Phase 3/4)
    Stores user credentials, profile, and permissions.
    """
    __tablename__ = "users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Multi-tenancy
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    
    # Authentication
    email = Column(String(255), nullable=False, unique=True, index=True)
    password_hash = Column(String(255), nullable=False)  # bcrypt hash
    
    # Profile
    name = Column(String(255), nullable=False)
    role = Column(String(50), nullable=False, default="viewer")  # admin, developer, viewer
    
    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)  # Email verified
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login_at = Column(DateTime)
    
    # Metadata
    meta = Column(JSON)  # Flexible additional data (preferences, settings, etc.)
    
    # Relationships
    tenant = relationship("Tenant", back_populates="users")
    
    # Indexes for common queries
    __table_args__ = (
        Index('ix_users_tenant_email', 'tenant_id', 'email'),
        Index('ix_users_tenant_role', 'tenant_id', 'role'),
        Index('ix_users_active', 'is_active'),
    )
    
    def __repr__(self):
        return f"<User(email='{self.email}', role='{self.role}', tenant_id={self.tenant_id})>"


class Project(Base):
    """
    ML Project tracking

    MODIFIED: Added tenant_id for multi-tenancy
    """
    __tablename__ = "projects"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # ADDED: Multi-tenancy field (nullable for backwards compatibility during migration)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=True, index=True)

    name = Column(String(255), nullable=False)
    problem_class = Column(String(50), nullable=False)  # classification, nlp, forecasting, etc.
    complexity_score = Column(Integer)  # 1-100
    team_size = Column(Integer)
    start_date = Column(DateTime, default=datetime.utcnow)
    completion_date = Column(DateTime)
    success_score = Column(Float)  # 0-100, weighted composite
    model_performance = Column(Float)  # Final model metric (accuracy, F1, etc.)
    compute_cost = Column(Float)  # Total compute cost
    business_impact = Column(Float)  # Business value delivered
    meta = Column(JSON)  # Flexible additional data

    # Relationships
    tenant = relationship("Tenant", back_populates="projects")
    artifacts_used = relationship("ArtifactUsage", back_populates="project")
    team_members = relationship("TeamMember", back_populates="project")
    metrics = relationship("ProcessMetric", back_populates="project")
    predictions = relationship("Prediction", back_populates="project")

    # ADDED: Indexes for multi-tenancy queries
    __table_args__ = (
        # Composite index for common queries
        Index('ix_projects_tenant_created', 'tenant_id', 'start_date'),
        Index('ix_projects_tenant_name', 'tenant_id', 'name'),
    )

    def __repr__(self):
        return f"<Project(name='{self.name}', tenant_id={self.tenant_id}, problem_class='{self.problem_class}')>"


class Artifact(Base):
    """
    Reusable ML artifacts (Music Library)

    MODIFIED: Added tenant_id for multi-tenancy
    """
    __tablename__ = "artifacts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # ADDED: Multi-tenancy field (nullable for backwards compatibility during migration)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=True, index=True)

    name = Column(String(255), nullable=False)
    type = Column(String(50), nullable=False)  # feature_pipeline, model_template, schema, notebook
    version = Column(String(50), nullable=False)
    created_by = Column(String(255))
    created_at = Column(DateTime, default=datetime.utcnow)
    usage_count = Column(Integer, default=0)
    avg_impact_score = Column(Float, default=0.0)  # Average contribution to project success
    tags = Column(JSONEncodedList)  # Works in both PostgreSQL and SQLite
    content_hash = Column(String(64))  # SHA-256 of content
    storage_path = Column(Text)  # S3/MinIO path
    meta = Column(JSON)
    is_active = Column(Boolean, default=True)

    # Relationships
    tenant = relationship("Tenant", back_populates="artifacts")
    usages = relationship("ArtifactUsage", back_populates="artifact")

    # ADDED: Indexes for multi-tenancy queries
    __table_args__ = (
        Index('ix_artifacts_tenant_created', 'tenant_id', 'created_at'),
        Index('ix_artifacts_tenant_type', 'tenant_id', 'type'),
        Index('ix_artifacts_tenant_active', 'tenant_id', 'is_active'),
    )

    def __repr__(self):
        return f"<Artifact(name='{self.name}', tenant_id={self.tenant_id}, type='{self.type}')>"


class ArtifactUsage(Base):
    """
    Track when artifacts are used in projects

    MODIFIED: Added tenant_id for multi-tenancy (inherited from project/artifact but explicit for queries)
    """
    __tablename__ = "artifact_usage"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # ADDED: Multi-tenancy field (denormalized for performance, nullable for backwards compatibility)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=True, index=True)

    artifact_id = Column(UUID(as_uuid=True), ForeignKey("artifacts.id"), nullable=False)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False)
    used_at = Column(DateTime, default=datetime.utcnow)
    impact_score = Column(Float)  # Contribution to project success (calculated post-project)
    context = Column(JSON)  # How it was used, modifications made, etc.

    # Relationships
    artifact = relationship("Artifact", back_populates="usages")
    project = relationship("Project", back_populates="artifacts_used")

    # ADDED: Indexes
    __table_args__ = (
        Index('ix_artifact_usage_tenant_used', 'tenant_id', 'used_at'),
    )

    def __repr__(self):
        return f"<ArtifactUsage(tenant_id={self.tenant_id}, artifact_id={self.artifact_id}, project_id={self.project_id})>"


class TeamMember(Base):
    """
    Team composition for each project

    MODIFIED: Added tenant_id for multi-tenancy
    """
    __tablename__ = "team_members"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # ADDED: Multi-tenancy field (nullable for backwards compatibility)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=True, index=True)

    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False)
    role = Column(String(50))  # data_engineer, ml_scientist, devops, etc.
    experience_level = Column(String(20))  # junior, mid, senior, principal
    contribution_hours = Column(Float)
    performance_score = Column(Float)  # 0-100

    # Relationships
    project = relationship("Project", back_populates="team_members")

    def __repr__(self):
        return f"<TeamMember(role='{self.role}', experience='{self.experience_level}', tenant_id={self.tenant_id})>"


class ProcessMetric(Base):
    """
    Process and development metrics

    MODIFIED: Added tenant_id for multi-tenancy
    """
    __tablename__ = "process_metrics"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # ADDED: Multi-tenancy field (nullable for backwards compatibility)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=True, index=True)

    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False)
    metric_type = Column(String(50), nullable=False)  # git_velocity, ci_runtime, experiment_count, etc.
    metric_value = Column(Float, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    meta = Column(JSON)

    # Relationships
    project = relationship("Project", back_populates="metrics")

    # ADDED: Indexes
    __table_args__ = (
        Index('ix_process_metrics_tenant_timestamp', 'tenant_id', 'timestamp'),
        Index('ix_process_metrics_tenant_type', 'tenant_id', 'metric_type'),
    )

    def __repr__(self):
        return f"<ProcessMetric(type='{self.metric_type}', value={self.metric_value}, tenant_id={self.tenant_id})>"


class Prediction(Base):
    """
    Meta-model predictions for new projects

    MODIFIED: Added tenant_id for multi-tenancy
    """
    __tablename__ = "predictions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # ADDED: Multi-tenancy field (nullable for backwards compatibility)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=True, index=True)

    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"))
    predicted_success_score = Column(Float)  # 0-100
    predicted_duration_days = Column(Integer)
    predicted_cost = Column(Float)
    confidence = Column(Float)  # 0-1
    recommendation = Column(Text)  # Human-readable recommendation
    created_at = Column(DateTime, default=datetime.utcnow)
    model_version = Column(String(50))  # Which meta-model version made this prediction

    # Relationships
    project = relationship("Project", back_populates="predictions")

    # ADDED: Indexes
    __table_args__ = (
        Index('ix_predictions_tenant_created', 'tenant_id', 'created_at'),
    )

    def __repr__(self):
        return f"<Prediction(success_score={self.predicted_success_score}, tenant_id={self.tenant_id})>"


# ============================================================================
# Pydantic models for API (validation and serialization) - WITH TENANT SUPPORT
# ============================================================================

from pydantic import BaseModel, Field, field_serializer
from typing import Optional, List, Dict, Any, Union
from datetime import datetime as dt
from uuid import UUID as PyUUID


class TenantCreate(BaseModel):
    """Schema for creating a new tenant"""
    name: str
    slug: str
    max_users: int = 10
    max_projects: int = 100
    max_artifacts: int = 1000
    metadata: Optional[Dict[str, Any]] = {}


class TenantResponse(BaseModel):
    """Schema for tenant responses"""
    id: Union[str, PyUUID]
    name: str
    slug: str
    created_at: dt
    is_active: bool
    max_users: int
    max_projects: int
    max_artifacts: int

    @field_serializer('id')
    def serialize_id(self, value: Union[str, PyUUID], _info) -> str:
        return str(value)


class ProjectCreate(BaseModel):
    """
    Schema for creating a new project

    MODIFIED: Made tenant_id optional for backwards compatibility
    """
    name: str
    problem_class: str
    complexity_score: Optional[int] = None
    team_size: int
    tenant_id: Optional[Union[str, PyUUID]] = None  # Optional for backwards compatibility
    metadata: Optional[Dict[str, Any]] = {}


class ProjectResponse(BaseModel):
    """
    Schema for project responses

    MODIFIED: Added tenant_id
    """
    id: Union[str, PyUUID]
    name: str
    problem_class: str
    complexity_score: Optional[int]
    team_size: int
    start_date: dt
    completion_date: Optional[dt]
    success_score: Optional[float]
    model_performance: Optional[float]
    compute_cost: Optional[float]
    business_impact: Optional[float]
    tenant_id: Optional[Union[str, PyUUID]] = None  # Optional for backwards compatibility

    @field_serializer('id', 'tenant_id')
    def serialize_uuid(self, value: Union[str, PyUUID, None], _info) -> Optional[str]:
        return str(value) if value is not None else None

    class Config:
        from_attributes = True


class ArtifactCreate(BaseModel):
    """
    Schema for creating artifacts

    MODIFIED: Made tenant_id optional for backwards compatibility
    """
    name: str
    type: str
    version: str
    created_by: Optional[str] = None
    tags: Optional[List[str]] = []
    storage_path: Optional[str] = None
    tenant_id: Optional[Union[str, PyUUID]] = None  # Optional for backwards compatibility
    metadata: Optional[Dict[str, Any]] = {}


class ArtifactResponse(BaseModel):
    """
    Schema for artifact responses

    MODIFIED: Added tenant_id
    """
    id: Union[str, PyUUID]
    name: str
    type: str
    version: str
    created_by: Optional[str]
    created_at: dt
    usage_count: int
    avg_impact_score: float
    tags: List[str]
    storage_path: str
    is_active: bool
    tenant_id: Optional[Union[str, PyUUID]] = None  # Optional for backwards compatibility

    @field_serializer('id', 'tenant_id')
    def serialize_uuid(self, value: Union[str, PyUUID, None], _info) -> Optional[str]:
        return str(value) if value is not None else None

    class Config:
        from_attributes = True


class ArtifactSearch(BaseModel):
    """Schema for artifact search"""
    query: Optional[str] = None
    type: Optional[str] = None
    tags: Optional[List[str]] = None
    min_impact_score: Optional[float] = None


class PredictionResponse(BaseModel):
    """Schema for prediction responses"""
    id: Union[str, PyUUID]
    predicted_success_score: float
    predicted_duration_days: int
    predicted_cost: float
    confidence: float
    recommendation: str
    created_at: dt

    @field_serializer('id')
    def serialize_id(self, value: Union[str, PyUUID], _info) -> str:
        return str(value)

    class Config:
        from_attributes = True


class MetricCreate(BaseModel):
    """Schema for creating a process metric"""
    project_id: str
    metric_type: str
    metric_value: float
    metadata: Optional[Dict[str, Any]] = {}


class ProjectSuccessUpdate(BaseModel):
    """Schema for updating project success metrics"""
    model_accuracy: Optional[float] = None
    business_impact_usd: Optional[float] = None
    deployment_days: Optional[int] = None
    compute_cost: Optional[float] = None


class ArtifactUsageCreate(BaseModel):
    """Schema for logging artifact usage"""
    project_id: str
    impact_score: Optional[float] = None
    context: Optional[Dict[str, Any]] = {}


class ArtifactUsageResponse(BaseModel):
    """Schema for artifact usage response"""
    id: Union[str, PyUUID]
    artifact_id: Union[str, PyUUID]
    project_id: Union[str, PyUUID]
    used_at: dt
    impact_score: Optional[float]

    @field_serializer('id', 'artifact_id', 'project_id')
    def serialize_ids(self, value: Union[str, PyUUID], _info) -> str:
        return str(value)

    class Config:
        from_attributes = True
