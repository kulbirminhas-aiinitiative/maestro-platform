"""
AI Persona Foundry - Component Registry
Central registry for component implementations.
"""
from typing import Dict, Type, Optional
from .interfaces import (
    PersonaEngine,
    KnowledgeStore,
    AgentRuntime,
    ToolFramework,
    LearningEngine,
    InnovationEngine,
    CollaborationProtocol,
    DomainOnboarding,
)


class ComponentRegistry:
    """
    Registry for AI Persona Foundry components.
    Allows registration and retrieval of component implementations.
    """
    
    _instance: Optional['ComponentRegistry'] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._components: Dict[str, object] = {}
            cls._instance._implementations: Dict[str, Type] = {}
        return cls._instance
    
    def register(self, name: str, implementation: Type) -> None:
        """Register a component implementation class."""
        self._implementations[name] = implementation
    
    def get_implementation(self, name: str) -> Optional[Type]:
        """Get a registered implementation class."""
        return self._implementations.get(name)
    
    def set_instance(self, name: str, instance: object) -> None:
        """Set a component instance."""
        self._components[name] = instance
    
    def get_instance(self, name: str) -> Optional[object]:
        """Get a component instance."""
        return self._components.get(name)
    
    @property
    def persona_engine(self) -> Optional[PersonaEngine]:
        """Get PersonaEngine instance."""
        return self._components.get("persona_engine")
    
    @persona_engine.setter
    def persona_engine(self, instance: PersonaEngine) -> None:
        self._components["persona_engine"] = instance
    
    @property
    def knowledge_store(self) -> Optional[KnowledgeStore]:
        """Get KnowledgeStore instance."""
        return self._components.get("knowledge_store")
    
    @knowledge_store.setter
    def knowledge_store(self, instance: KnowledgeStore) -> None:
        self._components["knowledge_store"] = instance
    
    @property
    def agent_runtime(self) -> Optional[AgentRuntime]:
        """Get AgentRuntime instance."""
        return self._components.get("agent_runtime")
    
    @agent_runtime.setter
    def agent_runtime(self, instance: AgentRuntime) -> None:
        self._components["agent_runtime"] = instance
    
    @property
    def tool_framework(self) -> Optional[ToolFramework]:
        """Get ToolFramework instance."""
        return self._components.get("tool_framework")
    
    @tool_framework.setter
    def tool_framework(self, instance: ToolFramework) -> None:
        self._components["tool_framework"] = instance
    
    @property
    def learning_engine(self) -> Optional[LearningEngine]:
        """Get LearningEngine instance."""
        return self._components.get("learning_engine")
    
    @learning_engine.setter
    def learning_engine(self, instance: LearningEngine) -> None:
        self._components["learning_engine"] = instance
    
    @property
    def innovation_engine(self) -> Optional[InnovationEngine]:
        """Get InnovationEngine instance."""
        return self._components.get("innovation_engine")
    
    @innovation_engine.setter
    def innovation_engine(self, instance: InnovationEngine) -> None:
        self._components["innovation_engine"] = instance
    
    @property
    def collaboration_protocol(self) -> Optional[CollaborationProtocol]:
        """Get CollaborationProtocol instance."""
        return self._components.get("collaboration_protocol")
    
    @collaboration_protocol.setter
    def collaboration_protocol(self, instance: CollaborationProtocol) -> None:
        self._components["collaboration_protocol"] = instance
    
    @property
    def domain_onboarding(self) -> Optional[DomainOnboarding]:
        """Get DomainOnboarding instance."""
        return self._components.get("domain_onboarding")
    
    @domain_onboarding.setter
    def domain_onboarding(self, instance: DomainOnboarding) -> None:
        self._components["domain_onboarding"] = instance
    
    def reset(self) -> None:
        """Reset all registered components (for testing)."""
        self._components.clear()
        self._implementations.clear()


# Global registry instance
registry = ComponentRegistry()


def get_registry() -> ComponentRegistry:
    """Get the global component registry."""
    return registry
