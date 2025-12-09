"""
AI Persona Foundry - Exceptions
Custom exceptions for the platform.
"""


class FoundryError(Exception):
    """Base exception for all Foundry errors."""
    pass


class PersonaNotFoundError(FoundryError):
    """Raised when a persona cannot be found."""
    def __init__(self, persona_id: str, version: str = "latest"):
        self.persona_id = persona_id
        self.version = version
        super().__init__(f"Persona not found: {persona_id} (version: {version})")


class PersonaVersionError(FoundryError):
    """Raised when there's a version conflict."""
    def __init__(self, persona_id: str, message: str):
        self.persona_id = persona_id
        super().__init__(f"Version error for {persona_id}: {message}")


class DomainNotFoundError(FoundryError):
    """Raised when a domain is not registered."""
    def __init__(self, domain: str):
        self.domain = domain
        super().__init__(f"Domain not registered: {domain}")


class ToolNotFoundError(FoundryError):
    """Raised when a tool cannot be found."""
    def __init__(self, tool_id: str):
        self.tool_id = tool_id
        super().__init__(f"Tool not found: {tool_id}")


class ToolAccessDeniedError(FoundryError):
    """Raised when a persona cannot access a tool."""
    def __init__(self, persona_id: str, tool_id: str):
        self.persona_id = persona_id
        self.tool_id = tool_id
        super().__init__(f"Persona {persona_id} cannot access tool {tool_id}")


class ExecutionError(FoundryError):
    """Raised when execution fails."""
    def __init__(self, execution_id: str, message: str):
        self.execution_id = execution_id
        super().__init__(f"Execution {execution_id} failed: {message}")


class ExecutionCancelledError(FoundryError):
    """Raised when execution is cancelled."""
    def __init__(self, execution_id: str):
        self.execution_id = execution_id
        super().__init__(f"Execution cancelled: {execution_id}")


class KnowledgeStoreError(FoundryError):
    """Raised when knowledge store operations fail."""
    def __init__(self, operation: str, message: str):
        self.operation = operation
        super().__init__(f"Knowledge store {operation} failed: {message}")


class CollaborationError(FoundryError):
    """Raised when collaboration fails."""
    def __init__(self, session_id: str, message: str):
        self.session_id = session_id
        super().__init__(f"Collaboration session {session_id} error: {message}")


class ValidationError(FoundryError):
    """Raised when validation fails."""
    def __init__(self, entity: str, errors: list):
        self.entity = entity
        self.errors = errors
        super().__init__(f"Validation failed for {entity}: {', '.join(errors)}")


class ConfigurationError(FoundryError):
    """Raised when configuration is invalid."""
    def __init__(self, component: str, message: str):
        self.component = component
        super().__init__(f"Configuration error in {component}: {message}")
