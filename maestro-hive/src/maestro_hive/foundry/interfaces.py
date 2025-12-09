"""
AI Persona Foundry - Core Interfaces
Defines the abstract interfaces for all 8 platform components.
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, AsyncIterator
from .types import (
    Persona,
    PersonaConfig,
    Document,
    Tool,
    Feedback,
    DomainConfig,
    DomainType,
    DomainStats,
    ExecutionContext,
    ExecutionResult,
    ToolInvocation,
    Pattern,
)


class PersonaEngine(ABC):
    """
    Component 1: Persona Engine
    Manages persona lifecycle - creation, versioning, evolution.
    """
    
    @abstractmethod
    async def create_persona(self, config: PersonaConfig, created_by: str) -> Persona:
        """Create a new persona with the given configuration."""
        pass
    
    @abstractmethod
    async def get_persona(self, persona_id: str, version: str = "latest") -> Optional[Persona]:
        """Retrieve a persona by ID and optional version."""
        pass
    
    @abstractmethod
    async def update_persona(self, persona_id: str, config: PersonaConfig) -> Persona:
        """Update persona configuration, creating a new version."""
        pass
    
    @abstractmethod
    async def evolve_persona(self, persona_id: str, feedback: List[Feedback]) -> Persona:
        """Evolve persona based on accumulated feedback."""
        pass
    
    @abstractmethod
    async def list_personas(
        self, 
        domain: Optional[DomainType] = None,
        status: Optional[str] = None
    ) -> List[Persona]:
        """List personas with optional filters."""
        pass
    
    @abstractmethod
    async def deprecate_persona(self, persona_id: str) -> Persona:
        """Mark a persona as deprecated."""
        pass
    
    @abstractmethod
    async def get_persona_versions(self, persona_id: str) -> List[str]:
        """Get all available versions of a persona."""
        pass


class KnowledgeStore(ABC):
    """
    Component 2: Knowledge Store
    Universal RAG system for multi-domain knowledge management.
    """
    
    @abstractmethod
    async def store(self, document: Document) -> str:
        """Store a document and return its ID."""
        pass
    
    @abstractmethod
    async def store_batch(self, documents: List[Document]) -> List[str]:
        """Store multiple documents efficiently."""
        pass
    
    @abstractmethod
    async def retrieve(
        self, 
        query: str, 
        domain: DomainType,
        top_k: int = 10,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Document]:
        """Retrieve relevant documents using RAG."""
        pass
    
    @abstractmethod
    async def delete(self, document_id: str) -> bool:
        """Delete a document from the store."""
        pass
    
    @abstractmethod
    async def update_embeddings(self, domain: DomainType) -> int:
        """Refresh embeddings for a domain. Returns count updated."""
        pass
    
    @abstractmethod
    async def get_domain_stats(self, domain: DomainType) -> DomainStats:
        """Get statistics for a domain."""
        pass
    
    @abstractmethod
    async def search(
        self,
        query: str,
        domains: Optional[List[DomainType]] = None
    ) -> List[Document]:
        """Full-text search across domains."""
        pass


class AgentRuntime(ABC):
    """
    Component 3: Agent Runtime
    Executes personas with full context and tool access.
    """
    
    @abstractmethod
    async def execute(
        self, 
        context: ExecutionContext,
        stream: bool = False
    ) -> ExecutionResult:
        """Execute a persona with the given context."""
        pass
    
    @abstractmethod
    async def execute_stream(
        self, 
        context: ExecutionContext
    ) -> AsyncIterator[str]:
        """Stream execution output."""
        pass
    
    @abstractmethod
    async def get_execution(self, execution_id: str) -> Optional[ExecutionResult]:
        """Get execution result by ID."""
        pass
    
    @abstractmethod
    async def cancel_execution(self, execution_id: str) -> bool:
        """Cancel a running execution."""
        pass
    
    @abstractmethod
    async def list_executions(
        self,
        persona_id: Optional[str] = None,
        limit: int = 100
    ) -> List[ExecutionResult]:
        """List recent executions."""
        pass
    
    @abstractmethod
    def build_context(
        self,
        persona: Persona,
        task: str,
        knowledge: List[Document],
        tools: List[Tool]
    ) -> ExecutionContext:
        """Build execution context from components."""
        pass


class ToolFramework(ABC):
    """
    Component 4: Tool Framework
    Domain-agnostic tool registration and invocation.
    """
    
    @abstractmethod
    async def register_tool(self, tool: Tool) -> str:
        """Register a new tool and return its ID."""
        pass
    
    @abstractmethod
    async def get_tool(self, tool_id: str) -> Optional[Tool]:
        """Get tool by ID."""
        pass
    
    @abstractmethod
    async def invoke_tool(
        self,
        tool_id: str,
        parameters: Dict[str, Any],
        persona_id: str
    ) -> ToolInvocation:
        """Invoke a tool with parameters."""
        pass
    
    @abstractmethod
    async def list_tools(
        self,
        domain: Optional[DomainType] = None,
        enabled_only: bool = True
    ) -> List[Tool]:
        """List available tools."""
        pass
    
    @abstractmethod
    async def validate_tool_access(
        self,
        tool_id: str,
        persona: Persona
    ) -> bool:
        """Check if persona can access tool."""
        pass
    
    @abstractmethod
    async def disable_tool(self, tool_id: str) -> bool:
        """Disable a tool."""
        pass


class LearningEngine(ABC):
    """
    Component 5: Learning Engine
    Continuous improvement from execution outcomes.
    """
    
    @abstractmethod
    async def record_feedback(self, feedback: Feedback) -> str:
        """Record feedback for an execution."""
        pass
    
    @abstractmethod
    async def get_feedback(
        self,
        persona_id: str,
        limit: int = 100
    ) -> List[Feedback]:
        """Get feedback history for a persona."""
        pass
    
    @abstractmethod
    async def compute_improvements(
        self,
        persona_id: str
    ) -> Dict[str, Any]:
        """Compute suggested improvements from feedback."""
        pass
    
    @abstractmethod
    async def get_performance_metrics(
        self,
        persona_id: str
    ) -> Dict[str, float]:
        """Get performance metrics for a persona."""
        pass
    
    @abstractmethod
    async def trigger_evolution(
        self,
        persona_id: str,
        threshold: float = 0.8
    ) -> bool:
        """Trigger persona evolution if performance threshold met."""
        pass


class InnovationEngine(ABC):
    """
    Component 6: Innovation Engine
    Pattern discovery and improvement proposals.
    """
    
    @abstractmethod
    async def discover_patterns(
        self,
        domain: DomainType,
        min_frequency: int = 5
    ) -> List[Pattern]:
        """Discover patterns in execution data."""
        pass
    
    @abstractmethod
    async def get_pattern(self, pattern_id: str) -> Optional[Pattern]:
        """Get pattern by ID."""
        pass
    
    @abstractmethod
    async def suggest_improvements(
        self,
        persona_id: str
    ) -> List[str]:
        """Generate improvement suggestions for a persona."""
        pass
    
    @abstractmethod
    async def analyze_domain_trends(
        self,
        domain: DomainType
    ) -> Dict[str, Any]:
        """Analyze trends in a domain."""
        pass
    
    @abstractmethod
    async def propose_new_capability(
        self,
        domain: DomainType,
        based_on_patterns: List[str]
    ) -> Optional[Dict[str, Any]]:
        """Propose a new capability based on patterns."""
        pass


class CollaborationProtocol(ABC):
    """
    Component 7: Collaboration Protocol
    Multi-agent coordination and communication.
    """
    
    @abstractmethod
    async def create_session(
        self,
        personas: List[Persona],
        task: str
    ) -> str:
        """Create a collaboration session. Returns session ID."""
        pass
    
    @abstractmethod
    async def send_message(
        self,
        session_id: str,
        from_persona: str,
        to_persona: Optional[str],
        message: str
    ) -> str:
        """Send message in session. Returns message ID."""
        pass
    
    @abstractmethod
    async def get_messages(
        self,
        session_id: str,
        since: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get messages in session."""
        pass
    
    @abstractmethod
    async def delegate_task(
        self,
        session_id: str,
        from_persona: str,
        to_persona: str,
        task: str
    ) -> str:
        """Delegate a subtask to another persona."""
        pass
    
    @abstractmethod
    async def close_session(
        self,
        session_id: str,
        result: Any
    ) -> bool:
        """Close a collaboration session."""
        pass


class DomainOnboarding(ABC):
    """
    Component 8: Domain Onboarding
    Framework for adding new domain verticals.
    """
    
    @abstractmethod
    async def register_domain(
        self,
        config: DomainConfig
    ) -> bool:
        """Register a new domain vertical."""
        pass
    
    @abstractmethod
    async def get_domain_config(
        self,
        domain: DomainType
    ) -> Optional[DomainConfig]:
        """Get configuration for a domain."""
        pass
    
    @abstractmethod
    async def update_domain_config(
        self,
        domain: DomainType,
        config: DomainConfig
    ) -> bool:
        """Update domain configuration."""
        pass
    
    @abstractmethod
    async def list_domains(self) -> List[DomainConfig]:
        """List all registered domains."""
        pass
    
    @abstractmethod
    async def seed_domain(
        self,
        domain: DomainType,
        personas: List[PersonaConfig],
        documents: List[Document],
        tools: List[Tool]
    ) -> Dict[str, int]:
        """Seed a domain with initial data. Returns counts."""
        pass
    
    @abstractmethod
    async def validate_domain(
        self,
        domain: DomainType
    ) -> Dict[str, Any]:
        """Validate domain setup is complete."""
        pass
