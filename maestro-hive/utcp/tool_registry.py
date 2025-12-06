"""
UTCP Tool Registry - Catalog of Available Tools

This module implements the Tool Registry for MD-2563, providing:
- Tool schema definition (inputs, outputs, side effects)
- Tool categorization by domain and capability
- Version tracking for tool evolution
- Health check and availability status
- Registration of existing UTCP tools

Part of: MD-2545 (FOUNDRY-CORE Tool Integration Framework)
Story: MD-2563 (Tool Registry - Catalog of Available Tools)
"""

import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Type, Union
import inspect
import hashlib
import json

from .base import UTCPTool, ToolConfig, ToolCapability, ToolResult


class ToolDomain(str, Enum):
    """Domain categorization for tools."""
    PROJECT_MANAGEMENT = "project_management"
    DOCUMENTATION = "documentation"
    VERSION_CONTROL = "version_control"
    COMMUNICATION = "communication"
    CLOUD_INFRASTRUCTURE = "cloud_infrastructure"
    MONITORING = "monitoring"
    INCIDENT_MANAGEMENT = "incident_management"
    IDENTITY = "identity"
    CRM = "crm"
    PRODUCTIVITY = "productivity"
    CUSTOM = "custom"


class SideEffectType(str, Enum):
    """Types of side effects a tool operation can have."""
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    NOTIFY = "notify"
    TRIGGER_WORKFLOW = "trigger_workflow"
    EXTERNAL_API_CALL = "external_api_call"
    STATE_CHANGE = "state_change"
    NONE = "none"


class HealthStatus(str, Enum):
    """Health status of a tool."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class ParameterSchema:
    """Schema for a tool parameter (input or output)."""
    name: str
    type: str  # e.g., "string", "integer", "object", "array"
    description: str
    required: bool = True
    default: Any = None
    enum: Optional[List[Any]] = None
    properties: Optional[Dict[str, "ParameterSchema"]] = None  # For nested objects
    items: Optional["ParameterSchema"] = None  # For arrays

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format."""
        result = {
            "name": self.name,
            "type": self.type,
            "description": self.description,
            "required": self.required,
        }
        if self.default is not None:
            result["default"] = self.default
        if self.enum:
            result["enum"] = self.enum
        if self.properties:
            result["properties"] = {k: v.to_dict() for k, v in self.properties.items()}
        if self.items:
            result["items"] = self.items.to_dict()
        return result


@dataclass
class SideEffect:
    """Definition of a side effect from a tool operation."""
    type: SideEffectType
    description: str
    target: Optional[str] = None  # e.g., "jira_issue", "slack_channel"
    reversible: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.type.value,
            "description": self.description,
            "target": self.target,
            "reversible": self.reversible,
        }


@dataclass
class OperationSchema:
    """Schema for a tool operation (method)."""
    name: str
    description: str
    inputs: Dict[str, ParameterSchema]
    outputs: Dict[str, ParameterSchema]
    side_effects: List[SideEffect] = field(default_factory=list)
    rate_limit: Optional[int] = None  # Operations per minute
    timeout: int = 30  # Seconds
    idempotent: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "inputs": {k: v.to_dict() for k, v in self.inputs.items()},
            "outputs": {k: v.to_dict() for k, v in self.outputs.items()},
            "side_effects": [se.to_dict() for se in self.side_effects],
            "rate_limit": self.rate_limit,
            "timeout": self.timeout,
            "idempotent": self.idempotent,
        }


@dataclass
class ToolSchema:
    """Complete schema for a registered tool."""
    name: str
    version: str
    domain: ToolDomain
    description: str
    capabilities: List[ToolCapability]
    operations: Dict[str, OperationSchema]
    required_credentials: List[str]
    optional_credentials: List[str] = field(default_factory=list)
    tags: Set[str] = field(default_factory=set)
    deprecated: bool = False
    deprecation_message: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "version": self.version,
            "domain": self.domain.value,
            "description": self.description,
            "capabilities": [c.value for c in self.capabilities],
            "operations": {k: v.to_dict() for k, v in self.operations.items()},
            "required_credentials": self.required_credentials,
            "optional_credentials": self.optional_credentials,
            "tags": list(self.tags),
            "deprecated": self.deprecated,
            "deprecation_message": self.deprecation_message,
        }

    def schema_hash(self) -> str:
        """Generate a hash of the schema for version tracking."""
        schema_str = json.dumps(self.to_dict(), sort_keys=True)
        return hashlib.sha256(schema_str.encode()).hexdigest()[:16]


@dataclass
class ToolVersion:
    """Version information for a tool."""
    version: str
    schema_hash: str
    released_at: datetime
    changelog: Optional[str] = None
    breaking_changes: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "version": self.version,
            "schema_hash": self.schema_hash,
            "released_at": self.released_at.isoformat(),
            "changelog": self.changelog,
            "breaking_changes": self.breaking_changes,
        }


@dataclass
class ToolHealthInfo:
    """Health information for a registered tool."""
    status: HealthStatus
    last_check: Optional[datetime] = None
    last_success: Optional[datetime] = None
    consecutive_failures: int = 0
    latency_ms: Optional[float] = None
    error_message: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status.value,
            "last_check": self.last_check.isoformat() if self.last_check else None,
            "last_success": self.last_success.isoformat() if self.last_success else None,
            "consecutive_failures": self.consecutive_failures,
            "latency_ms": self.latency_ms,
            "error_message": self.error_message,
        }


@dataclass
class RegisteredTool:
    """A tool registered in the registry."""
    tool_class: Type[UTCPTool]
    schema: ToolSchema
    instance: Optional[UTCPTool] = None
    health: ToolHealthInfo = field(default_factory=lambda: ToolHealthInfo(status=HealthStatus.UNKNOWN))
    version_history: List[ToolVersion] = field(default_factory=list)
    registered_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema": self.schema.to_dict(),
            "health": self.health.to_dict(),
            "version_history": [v.to_dict() for v in self.version_history],
            "registered_at": self.registered_at.isoformat(),
        }


class ToolRegistry:
    """
    Central registry for UTCP tools.

    Provides:
    - Tool schema definition (inputs, outputs, side effects)
    - Tool categorization by domain and capability
    - Version tracking for tool evolution
    - Health check and availability status
    - Registration of existing UTCP tools

    Example:
        >>> registry = ToolRegistry()
        >>> registry.register_tool(JiraTool, domain=ToolDomain.PROJECT_MANAGEMENT)
        >>> tools = registry.list_tools()
        >>> pm_tools = registry.get_tools_by_domain(ToolDomain.PROJECT_MANAGEMENT)
        >>> health = await registry.health_check_all()
    """

    def __init__(
        self,
        health_check_interval: int = 60,
        unhealthy_threshold: int = 3,
        auto_health_check: bool = True
    ):
        """
        Initialize the tool registry.

        Args:
            health_check_interval: Seconds between automatic health checks
            unhealthy_threshold: Consecutive failures before marking unhealthy
            auto_health_check: Enable automatic health monitoring
        """
        self._tools: Dict[str, RegisteredTool] = {}
        self._health_check_interval = health_check_interval
        self._unhealthy_threshold = unhealthy_threshold
        self._auto_health_check = auto_health_check
        self._health_check_task: Optional[asyncio.Task] = None
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize the registry and start health monitoring if enabled."""
        if self._initialized:
            return

        # Auto-register built-in tools
        await self._register_builtin_tools()

        if self._auto_health_check:
            await self.start_health_monitoring()

        self._initialized = True

    async def _register_builtin_tools(self) -> None:
        """Register all built-in UTCP tools."""
        from .tools import (
            JiraTool, ConfluenceTool, GitTool, SlackTool, TeamsTool,
            AWSTool, LinearTool, NotionTool, SalesforceTool, DatadogTool,
            PagerDutyTool, OktaTool, GoogleWorkspaceTool
        )

        # Define tool-to-domain mappings
        tool_domains = {
            JiraTool: ToolDomain.PROJECT_MANAGEMENT,
            ConfluenceTool: ToolDomain.DOCUMENTATION,
            GitTool: ToolDomain.VERSION_CONTROL,
            SlackTool: ToolDomain.COMMUNICATION,
            TeamsTool: ToolDomain.COMMUNICATION,
            AWSTool: ToolDomain.CLOUD_INFRASTRUCTURE,
            LinearTool: ToolDomain.PROJECT_MANAGEMENT,
            NotionTool: ToolDomain.DOCUMENTATION,
            SalesforceTool: ToolDomain.CRM,
            DatadogTool: ToolDomain.MONITORING,
            PagerDutyTool: ToolDomain.INCIDENT_MANAGEMENT,
            OktaTool: ToolDomain.IDENTITY,
            GoogleWorkspaceTool: ToolDomain.PRODUCTIVITY,
        }

        for tool_class, domain in tool_domains.items():
            try:
                self.register_tool(tool_class, domain=domain)
            except Exception:
                # Tool registration may fail if credentials are not provided
                # This is expected during initialization
                pass

    def register_tool(
        self,
        tool_class: Type[UTCPTool],
        domain: ToolDomain = ToolDomain.CUSTOM,
        tags: Optional[Set[str]] = None,
        credentials: Optional[Dict[str, str]] = None
    ) -> RegisteredTool:
        """
        Register a tool in the registry.

        Args:
            tool_class: The UTCPTool class to register
            domain: Domain categorization for the tool
            tags: Optional tags for additional categorization
            credentials: Optional credentials to instantiate the tool

        Returns:
            The registered tool entry

        Raises:
            ValueError: If tool is already registered with same version
        """
        # Get tool config from class (instantiate temporarily if needed)
        temp_instance = None
        if credentials:
            temp_instance = tool_class(credentials)
            config = temp_instance.config
        else:
            # Try to get config without credentials for schema
            try:
                # Create dummy credentials to read config
                dummy_creds = {k: "dummy" for k in ["base_url", "email", "api_token", "token"]}
                temp_instance = tool_class(dummy_creds)
                config = temp_instance.config
            except Exception:
                # If we can't instantiate, create minimal config from class name
                config = ToolConfig(
                    name=tool_class.__name__.lower().replace("tool", ""),
                    version="1.0.0",
                    capabilities=[],
                    required_credentials=[],
                )

        # Build operation schemas from class methods
        operations = self._extract_operations(tool_class)

        # Create full schema
        schema = ToolSchema(
            name=config.name,
            version=config.version,
            domain=domain,
            description=tool_class.__doc__ or f"{config.name} tool",
            capabilities=config.capabilities,
            operations=operations,
            required_credentials=config.required_credentials,
            optional_credentials=config.optional_credentials,
            tags=tags or set(),
        )

        # Check for duplicate registration
        if config.name in self._tools:
            existing = self._tools[config.name]
            if existing.schema.version == schema.version:
                raise ValueError(f"Tool '{config.name}' version {schema.version} already registered")

        # Create version entry
        version_entry = ToolVersion(
            version=config.version,
            schema_hash=schema.schema_hash(),
            released_at=datetime.utcnow(),
        )

        # Create registered tool
        registered = RegisteredTool(
            tool_class=tool_class,
            schema=schema,
            instance=temp_instance if credentials else None,
            version_history=[version_entry],
        )

        self._tools[config.name] = registered
        return registered

    def _extract_operations(self, tool_class: Type[UTCPTool]) -> Dict[str, OperationSchema]:
        """Extract operation schemas from tool class methods."""
        operations = {}

        # Get all public async methods (excluding health_check and private methods)
        for name, method in inspect.getmembers(tool_class, predicate=inspect.isfunction):
            if name.startswith("_") or name == "health_check":
                continue

            # Check if method is async
            if asyncio.iscoroutinefunction(method):
                # Parse docstring for description
                doc = method.__doc__ or f"Execute {name} operation"

                # Extract parameters from signature
                sig = inspect.signature(method)
                inputs = {}
                for param_name, param in sig.parameters.items():
                    if param_name == "self":
                        continue

                    # Determine type from annotation
                    param_type = "any"
                    if param.annotation != inspect.Parameter.empty:
                        param_type = self._python_type_to_schema_type(param.annotation)

                    required = param.default == inspect.Parameter.empty
                    default = None if required else param.default

                    inputs[param_name] = ParameterSchema(
                        name=param_name,
                        type=param_type,
                        description=f"Parameter: {param_name}",
                        required=required,
                        default=default,
                    )

                # Infer side effects from method name
                side_effects = self._infer_side_effects(name)

                operations[name] = OperationSchema(
                    name=name,
                    description=doc.strip().split("\n")[0] if doc else f"{name} operation",
                    inputs=inputs,
                    outputs={"result": ParameterSchema(
                        name="result",
                        type="object",
                        description="Operation result",
                    )},
                    side_effects=side_effects,
                    idempotent=name.startswith("get_") or name.startswith("list_"),
                )

        return operations

    def _python_type_to_schema_type(self, python_type: Any) -> str:
        """Convert Python type annotation to schema type string."""
        type_str = str(python_type)
        if "str" in type_str:
            return "string"
        elif "int" in type_str:
            return "integer"
        elif "float" in type_str:
            return "number"
        elif "bool" in type_str:
            return "boolean"
        elif "List" in type_str or "list" in type_str:
            return "array"
        elif "Dict" in type_str or "dict" in type_str:
            return "object"
        return "any"

    def _infer_side_effects(self, method_name: str) -> List[SideEffect]:
        """Infer side effects from method name patterns."""
        side_effects = []

        name_lower = method_name.lower()

        if name_lower.startswith("create_") or name_lower.startswith("add_"):
            side_effects.append(SideEffect(
                type=SideEffectType.CREATE,
                description=f"Creates a new resource via {method_name}",
                reversible=True,
            ))
        elif name_lower.startswith("update_") or name_lower.startswith("set_"):
            side_effects.append(SideEffect(
                type=SideEffectType.UPDATE,
                description=f"Updates an existing resource via {method_name}",
                reversible=True,
            ))
        elif name_lower.startswith("delete_") or name_lower.startswith("remove_"):
            side_effects.append(SideEffect(
                type=SideEffectType.DELETE,
                description=f"Deletes a resource via {method_name}",
                reversible=False,
            ))
        elif name_lower.startswith("send_") or name_lower.startswith("notify_"):
            side_effects.append(SideEffect(
                type=SideEffectType.NOTIFY,
                description=f"Sends notification via {method_name}",
                reversible=False,
            ))
        elif name_lower.startswith("transition_"):
            side_effects.append(SideEffect(
                type=SideEffectType.STATE_CHANGE,
                description=f"Changes state via {method_name}",
                reversible=True,
            ))
        elif name_lower.startswith("get_") or name_lower.startswith("list_") or name_lower.startswith("search_"):
            side_effects.append(SideEffect(
                type=SideEffectType.NONE,
                description=f"Read-only operation: {method_name}",
            ))
        else:
            side_effects.append(SideEffect(
                type=SideEffectType.EXTERNAL_API_CALL,
                description=f"External API call via {method_name}",
            ))

        return side_effects

    def unregister_tool(self, name: str) -> bool:
        """
        Unregister a tool from the registry.

        Args:
            name: Tool name to unregister

        Returns:
            True if tool was unregistered, False if not found
        """
        if name in self._tools:
            del self._tools[name]
            return True
        return False

    def get_tool(self, name: str) -> Optional[RegisteredTool]:
        """Get a registered tool by name."""
        return self._tools.get(name)

    def get_tool_schema(self, name: str) -> Optional[ToolSchema]:
        """Get the schema for a tool by name."""
        tool = self._tools.get(name)
        return tool.schema if tool else None

    def list_tools(
        self,
        healthy_only: bool = False,
        include_deprecated: bool = False
    ) -> List[RegisteredTool]:
        """
        List all registered tools.

        Args:
            healthy_only: Only return tools with healthy status
            include_deprecated: Include deprecated tools

        Returns:
            List of registered tools
        """
        tools = list(self._tools.values())

        if healthy_only:
            tools = [t for t in tools if t.health.status == HealthStatus.HEALTHY]

        if not include_deprecated:
            tools = [t for t in tools if not t.schema.deprecated]

        return tools

    def get_tools_by_domain(
        self,
        domain: ToolDomain,
        healthy_only: bool = False
    ) -> List[RegisteredTool]:
        """
        Get tools filtered by domain.

        Args:
            domain: The domain to filter by
            healthy_only: Only return healthy tools

        Returns:
            List of tools in the specified domain
        """
        tools = [t for t in self._tools.values() if t.schema.domain == domain]

        if healthy_only:
            tools = [t for t in tools if t.health.status == HealthStatus.HEALTHY]

        return tools

    def get_tools_by_capability(
        self,
        capability: ToolCapability,
        healthy_only: bool = False
    ) -> List[RegisteredTool]:
        """
        Get tools that have a specific capability.

        Args:
            capability: The capability to filter by
            healthy_only: Only return healthy tools

        Returns:
            List of tools with the specified capability
        """
        tools = [
            t for t in self._tools.values()
            if capability in t.schema.capabilities
        ]

        if healthy_only:
            tools = [t for t in tools if t.health.status == HealthStatus.HEALTHY]

        return tools

    def get_tools_by_tags(
        self,
        tags: Set[str],
        match_all: bool = False
    ) -> List[RegisteredTool]:
        """
        Get tools by tags.

        Args:
            tags: Tags to filter by
            match_all: If True, tool must have all tags; if False, any tag

        Returns:
            List of tools matching the tag filter
        """
        if match_all:
            return [t for t in self._tools.values() if tags.issubset(t.schema.tags)]
        else:
            return [t for t in self._tools.values() if tags.intersection(t.schema.tags)]

    async def health_check(self, name: str) -> ToolHealthInfo:
        """
        Perform health check on a specific tool.

        Args:
            name: Tool name to check

        Returns:
            Health information for the tool

        Raises:
            KeyError: If tool not found
        """
        if name not in self._tools:
            raise KeyError(f"Tool '{name}' not found in registry")

        tool = self._tools[name]

        if not tool.instance:
            # Cannot health check without an instance
            tool.health = ToolHealthInfo(
                status=HealthStatus.UNKNOWN,
                last_check=datetime.utcnow(),
                error_message="No instance available for health check",
            )
            return tool.health

        start_time = datetime.utcnow()

        try:
            result = await tool.instance.health_check()
            latency = (datetime.utcnow() - start_time).total_seconds() * 1000

            if result.success:
                tool.health = ToolHealthInfo(
                    status=HealthStatus.HEALTHY,
                    last_check=datetime.utcnow(),
                    last_success=datetime.utcnow(),
                    consecutive_failures=0,
                    latency_ms=latency,
                )
            else:
                consecutive = tool.health.consecutive_failures + 1
                status = (
                    HealthStatus.UNHEALTHY
                    if consecutive >= self._unhealthy_threshold
                    else HealthStatus.DEGRADED
                )
                tool.health = ToolHealthInfo(
                    status=status,
                    last_check=datetime.utcnow(),
                    last_success=tool.health.last_success,
                    consecutive_failures=consecutive,
                    latency_ms=latency,
                    error_message=result.error,
                )
        except Exception as e:
            consecutive = tool.health.consecutive_failures + 1
            status = (
                HealthStatus.UNHEALTHY
                if consecutive >= self._unhealthy_threshold
                else HealthStatus.DEGRADED
            )
            tool.health = ToolHealthInfo(
                status=status,
                last_check=datetime.utcnow(),
                last_success=tool.health.last_success,
                consecutive_failures=consecutive,
                error_message=str(e),
            )

        return tool.health

    async def health_check_all(self) -> Dict[str, ToolHealthInfo]:
        """
        Perform health check on all registered tools.

        Returns:
            Dictionary mapping tool names to their health status
        """
        results = {}

        # Run health checks concurrently
        tasks = []
        tool_names = []

        for name, tool in self._tools.items():
            if tool.instance:
                tasks.append(self.health_check(name))
                tool_names.append(name)

        if tasks:
            health_results = await asyncio.gather(*tasks, return_exceptions=True)

            for name, result in zip(tool_names, health_results):
                if isinstance(result, Exception):
                    results[name] = ToolHealthInfo(
                        status=HealthStatus.UNHEALTHY,
                        last_check=datetime.utcnow(),
                        error_message=str(result),
                    )
                else:
                    results[name] = result

        # Add tools without instances
        for name, tool in self._tools.items():
            if name not in results:
                results[name] = tool.health

        return results

    async def start_health_monitoring(self) -> None:
        """Start automatic health monitoring."""
        if self._health_check_task is not None:
            return

        async def monitor():
            while True:
                try:
                    await self.health_check_all()
                    await asyncio.sleep(self._health_check_interval)
                except asyncio.CancelledError:
                    break
                except Exception:
                    await asyncio.sleep(self._health_check_interval)

        self._health_check_task = asyncio.create_task(monitor())

    async def stop_health_monitoring(self) -> None:
        """Stop automatic health monitoring."""
        if self._health_check_task is not None:
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass
            self._health_check_task = None

    def get_version_history(self, name: str) -> List[ToolVersion]:
        """
        Get version history for a tool.

        Args:
            name: Tool name

        Returns:
            List of version entries, newest first
        """
        tool = self._tools.get(name)
        if not tool:
            return []
        return sorted(tool.version_history, key=lambda v: v.released_at, reverse=True)

    def update_tool_version(
        self,
        name: str,
        new_version: str,
        changelog: Optional[str] = None,
        breaking_changes: bool = False
    ) -> Optional[ToolVersion]:
        """
        Update version information for a registered tool.

        Args:
            name: Tool name
            new_version: New version string
            changelog: Optional changelog description
            breaking_changes: Whether this version has breaking changes

        Returns:
            The new version entry, or None if tool not found
        """
        tool = self._tools.get(name)
        if not tool:
            return None

        # Update schema version
        tool.schema.version = new_version

        # Create new version entry
        version_entry = ToolVersion(
            version=new_version,
            schema_hash=tool.schema.schema_hash(),
            released_at=datetime.utcnow(),
            changelog=changelog,
            breaking_changes=breaking_changes,
        )

        tool.version_history.append(version_entry)
        return version_entry

    def deprecate_tool(self, name: str, message: str) -> bool:
        """
        Mark a tool as deprecated.

        Args:
            name: Tool name to deprecate
            message: Deprecation message

        Returns:
            True if tool was deprecated, False if not found
        """
        tool = self._tools.get(name)
        if not tool:
            return False

        tool.schema.deprecated = True
        tool.schema.deprecation_message = message
        return True

    def to_catalog(self) -> Dict[str, Any]:
        """
        Export the entire registry as a catalog dictionary.

        Returns:
            Complete catalog of all registered tools
        """
        return {
            "tools": {name: tool.to_dict() for name, tool in self._tools.items()},
            "domains": [d.value for d in ToolDomain],
            "capabilities": [c.value for c in ToolCapability],
            "total_tools": len(self._tools),
            "healthy_tools": len([
                t for t in self._tools.values()
                if t.health.status == HealthStatus.HEALTHY
            ]),
            "generated_at": datetime.utcnow().isoformat(),
        }

    async def cleanup(self) -> None:
        """Cleanup registry resources."""
        await self.stop_health_monitoring()
        self._tools.clear()
        self._initialized = False


# Global registry instance
_default_registry: Optional[ToolRegistry] = None


def get_registry() -> ToolRegistry:
    """Get the default global registry instance."""
    global _default_registry
    if _default_registry is None:
        _default_registry = ToolRegistry()
    return _default_registry


async def initialize_registry() -> ToolRegistry:
    """Initialize and return the default registry."""
    registry = get_registry()
    await registry.initialize()
    return registry
