"""
UTCP Base Classes

Defines the base interfaces for all UTCP tools.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from enum import Enum
from datetime import datetime


class ToolError(Exception):
    """Exception raised when a tool operation fails."""
    def __init__(self, message: str, code: str = "TOOL_ERROR", details: Optional[Dict] = None):
        self.message = message
        self.code = code
        self.details = details or {}
        super().__init__(message)


@dataclass
class ToolResult:
    """Standard result format for all tool operations."""
    success: bool
    data: Any = None
    error: Optional[str] = None
    error_code: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    @classmethod
    def ok(cls, data: Any, **metadata) -> 'ToolResult':
        return cls(success=True, data=data, metadata=metadata)

    @classmethod
    def fail(cls, error: str, code: str = "ERROR", **metadata) -> 'ToolResult':
        return cls(success=False, error=error, error_code=code, metadata=metadata)


class ToolCapability(str, Enum):
    """Capabilities that tools can provide."""
    READ = "read"
    WRITE = "write"
    DELETE = "delete"
    EXECUTE = "execute"
    SEARCH = "search"
    COMMENT = "comment"
    TRANSITION = "transition"
    ATTACH = "attach"


@dataclass
class ToolConfig:
    """Configuration for a tool instance."""
    name: str
    version: str
    capabilities: List[ToolCapability]
    required_credentials: List[str]
    optional_credentials: List[str] = field(default_factory=list)
    rate_limit: Optional[int] = None  # requests per minute
    timeout: int = 30  # seconds


class UTCPTool(ABC):
    """Base class for all UTCP tools."""

    def __init__(self, credentials: Dict[str, str]):
        self.credentials = credentials
        self._validate_credentials()

    @property
    @abstractmethod
    def config(self) -> ToolConfig:
        """Return tool configuration."""
        pass

    def _validate_credentials(self):
        """Validate that required credentials are provided."""
        missing = []
        for cred in self.config.required_credentials:
            if cred not in self.credentials or not self.credentials[cred]:
                missing.append(cred)

        if missing:
            raise ToolError(
                f"Missing required credentials: {', '.join(missing)}",
                code="MISSING_CREDENTIALS"
            )

    @abstractmethod
    async def health_check(self) -> ToolResult:
        """Check if the tool can connect to its service."""
        pass

    def has_capability(self, capability: ToolCapability) -> bool:
        """Check if tool has a specific capability."""
        return capability in self.config.capabilities
