"""
AI Persona Foundry - Core Types
Defines the fundamental data structures for the platform.
"""
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from enum import Enum
from datetime import datetime


class DomainType(Enum):
    """Supported domain verticals"""
    SDLC = "sdlc"
    ENGINEERING = "engineering"
    BUSINESS = "business"
    CREATIVE = "creative"


class PersonaStatus(Enum):
    """Persona lifecycle status"""
    DRAFT = "draft"
    ACTIVE = "active"
    DEPRECATED = "deprecated"
    ARCHIVED = "archived"


@dataclass
class PersonaCapability:
    """A capability that a persona can perform"""
    name: str
    description: str
    tools: List[str] = field(default_factory=list)
    knowledge_sources: List[str] = field(default_factory=list)


@dataclass
class PersonaConfig:
    """Configuration for creating/updating a persona"""
    name: str
    domain: DomainType
    description: str
    capabilities: List[PersonaCapability] = field(default_factory=list)
    system_prompt: str = ""
    temperature: float = 0.7
    max_tokens: int = 4096
    tools: List[str] = field(default_factory=list)
    knowledge_sources: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Persona:
    """An AI persona with specialized capabilities"""
    id: str
    name: str
    domain: DomainType
    description: str
    version: str
    status: PersonaStatus
    config: PersonaConfig
    created_at: datetime
    updated_at: datetime
    created_by: str
    performance_score: float = 0.0
    execution_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Document:
    """A document in the knowledge store"""
    id: str
    content: str
    domain: DomainType
    source: str
    embedding: Optional[List[float]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class Tool:
    """A tool that can be invoked by agents"""
    id: str
    name: str
    description: str
    domain: DomainType
    parameters: Dict[str, Any] = field(default_factory=dict)
    required_permissions: List[str] = field(default_factory=list)
    enabled: bool = True


@dataclass
class ToolInvocation:
    """Record of a tool being invoked"""
    tool_id: str
    persona_id: str
    parameters: Dict[str, Any]
    result: Any
    success: bool
    duration_ms: int
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class Feedback:
    """Feedback on persona execution for learning"""
    execution_id: str
    persona_id: str
    rating: float  # 0.0 to 1.0
    feedback_type: str  # "positive", "negative", "neutral"
    comment: Optional[str] = None
    corrections: Optional[Dict[str, Any]] = None
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class DomainConfig:
    """Configuration for a domain vertical"""
    domain: DomainType
    embedding_model: str = "text-embedding-ada-002"
    retrieval_top_k: int = 10
    tool_whitelist: List[str] = field(default_factory=list)
    knowledge_sources: List[str] = field(default_factory=list)
    default_persona_config: Optional[PersonaConfig] = None


@dataclass
class ExecutionContext:
    """Context for agent execution"""
    execution_id: str
    persona: Persona
    task: str
    domain: DomainType
    knowledge_context: List[Document] = field(default_factory=list)
    available_tools: List[Tool] = field(default_factory=list)
    parent_execution_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ExecutionResult:
    """Result of agent execution"""
    execution_id: str
    persona_id: str
    success: bool
    output: Any
    tool_invocations: List[ToolInvocation] = field(default_factory=list)
    duration_ms: int = 0
    tokens_used: int = 0
    error: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class Pattern:
    """A discovered pattern from the innovation engine"""
    id: str
    name: str
    description: str
    domain: DomainType
    frequency: int
    confidence: float
    suggested_improvements: List[str] = field(default_factory=list)
    discovered_at: datetime = field(default_factory=datetime.now)


@dataclass
class DomainStats:
    """Statistics for a domain"""
    domain: DomainType
    document_count: int
    persona_count: int
    tool_count: int
    total_executions: int
    avg_success_rate: float
    avg_response_time_ms: float
