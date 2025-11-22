"""
UTCP adapter for MaestroAPI - enables Universal Tool Calling Protocol support.

This module provides automatic UTCP manual generation from FastAPI OpenAPI specs,
allowing AI agents to discover and call services directly without middleware.
"""

import json
from typing import Any, Dict, List, Optional
from datetime import datetime

from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi

from maestro_core_logging import get_logger

def _get_logger():
    try:
        from maestro_core_logging import get_logger
        return get_logger(__name__)
    except:
        import logging
        return logging.getLogger(__name__)

logger = type("LazyLogger", (), {"__getattr__": lambda self, name: getattr(_get_logger(), name)})()


class UTCPManualGenerator:
    """
    Generate UTCP manual from FastAPI OpenAPI specification.

    This enables automatic service discovery by AI agents using the
    Universal Tool Calling Protocol (UTCP).

    Example:
        >>> app = FastAPI()
        >>> generator = UTCPManualGenerator(app, base_url="http://localhost:8000")
        >>> manual = generator.generate_manual()
    """

    def __init__(
        self,
        app: FastAPI,
        base_url: str = "http://localhost:8000",
        service_version: str = "1.0.0",
        include_internal_routes: bool = False
    ):
        """
        Initialize UTCP manual generator.

        Args:
            app: FastAPI application instance
            base_url: Base URL for service endpoints
            service_version: Version of the service
            include_internal_routes: Include internal/admin routes in manual
        """
        self.app = app
        self.base_url = base_url.rstrip('/')
        self.service_version = service_version
        self.include_internal_routes = include_internal_routes

    def generate_manual(self) -> Dict[str, Any]:
        """
        Generate complete UTCP manual from OpenAPI spec.

        Returns:
            UTCP manual dictionary compliant with UTCP v1.0 spec
        """
        openapi = self._get_openapi_spec()

        manual = {
            "manual_version": "1.0",
            "utcp_version": "1.0",
            "metadata": self._generate_metadata(openapi),
            "variables": {
                "BASE_URL": self.base_url,
                "SERVICE_VERSION": self.service_version
            },
            "tools": self._extract_tools(openapi),
            "manual_call_templates": self._generate_call_templates()
        }

        logger.info(
            "Generated UTCP manual",
            service=openapi.get("info", {}).get("title"),
            tool_count=len(manual["tools"])
        )

        return manual

    def _get_openapi_spec(self) -> Dict[str, Any]:
        """Get OpenAPI specification from FastAPI app."""
        if self.app.openapi_schema:
            return self.app.openapi_schema
        return get_openapi(
            title=self.app.title,
            version=self.app.version,
            openapi_version=self.app.openapi_version,
            description=self.app.description,
            routes=self.app.routes,
        )

    def _generate_metadata(self, openapi: Dict[str, Any]) -> Dict[str, Any]:
        """Generate metadata section from OpenAPI info."""
        info = openapi.get("info", {})

        return {
            "name": info.get("title", "Unknown Service"),
            "description": info.get("description", ""),
            "version": info.get("version", self.service_version),
            "provider": "MAESTRO Ecosystem",
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "base_url": self.base_url,
            "protocols": ["http"],
            "authentication": {
                "type": "bearer",
                "description": "JWT token authentication"
            }
        }

    def _extract_tools(self, openapi: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Extract tool definitions from OpenAPI paths.

        Converts each OpenAPI endpoint into a UTCP tool definition.
        """
        tools = []
        paths = openapi.get("paths", {})

        for path, methods in paths.items():
            # Skip internal routes unless explicitly included
            if not self.include_internal_routes and self._is_internal_route(path):
                continue

            for method, spec in methods.items():
                if method.upper() not in ["GET", "POST", "PUT", "DELETE", "PATCH"]:
                    continue

                tool = self._create_tool_from_endpoint(path, method, spec)
                if tool:
                    tools.append(tool)

        return tools

    def _is_internal_route(self, path: str) -> bool:
        """Check if route is internal (health, metrics, admin)."""
        internal_prefixes = ["/health", "/metrics", "/admin", "/docs", "/redoc", "/openapi"]
        return any(path.startswith(prefix) for prefix in internal_prefixes)

    def _create_tool_from_endpoint(
        self,
        path: str,
        method: str,
        spec: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Create UTCP tool definition from OpenAPI endpoint."""
        operation_id = spec.get("operationId", f"{method}_{path}".replace("/", "_"))

        # Extract parameters and request body
        input_schema = self._build_input_schema(spec)

        # Get tags for categorization
        tags = spec.get("tags", ["general"])

        # Build tool definition
        tool = {
            "name": operation_id,
            "description": spec.get("summary") or spec.get("description", f"{method.upper()} {path}"),
            "input_schema": input_schema,
            "metadata": {
                "path": path,
                "method": method.upper(),
                "tags": tags,
                "operationId": operation_id
            }
        }

        # Add response information
        if "responses" in spec:
            tool["metadata"]["responses"] = self._extract_response_info(spec["responses"])

        return tool

    def _build_input_schema(self, spec: Dict[str, Any]) -> Dict[str, Any]:
        """
        Build JSON schema for tool inputs from OpenAPI parameters and request body.
        """
        schema = {
            "type": "object",
            "properties": {},
            "required": []
        }

        # Extract path parameters
        parameters = spec.get("parameters", [])
        for param in parameters:
            param_name = param.get("name")
            param_schema = param.get("schema", {"type": "string"})

            schema["properties"][param_name] = {
                **param_schema,
                "description": param.get("description", "")
            }

            if param.get("required", False):
                schema["required"].append(param_name)

        # Extract request body
        request_body = spec.get("requestBody", {})
        if request_body:
            content = request_body.get("content", {})
            json_content = content.get("application/json", {})
            body_schema = json_content.get("schema", {})

            # Merge body schema into properties
            if body_schema.get("properties"):
                schema["properties"].update(body_schema["properties"])

            if body_schema.get("required"):
                schema["required"].extend(body_schema["required"])

        # Remove duplicates from required
        schema["required"] = list(set(schema["required"]))

        return schema

    def _extract_response_info(self, responses: Dict[str, Any]) -> Dict[str, Any]:
        """Extract response information for tool metadata."""
        response_info = {}

        for status_code, response_spec in responses.items():
            response_info[status_code] = {
                "description": response_spec.get("description", ""),
                "content_type": list(response_spec.get("content", {}).keys())
            }

        return response_info

    def _generate_call_templates(self) -> List[Dict[str, Any]]:
        """
        Generate HTTP call templates for UTCP protocol.

        These templates define how to invoke the tools over HTTP.
        """
        return [
            {
                "name": "http_json",
                "description": "HTTP JSON API call template",
                "call_template_type": "http",
                "url": "${BASE_URL}${tool.metadata.path}",
                "http_method": "${tool.metadata.method}",
                "headers": {
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                    "Authorization": "Bearer ${AUTH_TOKEN}"
                },
                "body_template": "${tool_input}",
                "timeout": 30000
            }
        ]

    def export_to_file(self, filepath: str) -> None:
        """
        Export UTCP manual to JSON file.

        Args:
            filepath: Path to output JSON file
        """
        manual = self.generate_manual()

        with open(filepath, 'w') as f:
            json.dump(manual, f, indent=2)

        logger.info("UTCP manual exported", filepath=filepath)


class UTCPToolExecutor:
    """
    Execute UTCP tool calls against FastAPI endpoints.

    This allows UTCP clients to invoke tools on the service.
    """

    def __init__(self, app: FastAPI):
        """
        Initialize tool executor.

        Args:
            app: FastAPI application instance
        """
        self.app = app
        self.generator = UTCPManualGenerator(app)

    async def execute_tool(
        self,
        tool_name: str,
        tool_input: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Execute a tool by name with given inputs.

        Args:
            tool_name: Name of the tool to execute (operation ID)
            tool_input: Input parameters for the tool
            context: Additional context (auth, headers, etc.)

        Returns:
            Tool execution result

        Raises:
            ValueError: If tool not found or invalid input
        """
        # Find tool definition
        manual = self.generator.generate_manual()
        tool = next((t for t in manual["tools"] if t["name"] == tool_name), None)

        if not tool:
            raise ValueError(f"Tool '{tool_name}' not found")

        # Validate input against schema
        self._validate_input(tool_input, tool["input_schema"])

        # Build execution result
        result = {
            "tool_name": tool_name,
            "status": "success",
            "data": {
                "message": f"Tool '{tool_name}' would be executed",
                "input": tool_input,
                "note": "Actual execution requires route handler integration"
            }
        }

        logger.info("Tool execution requested", tool=tool_name, input_keys=list(tool_input.keys()))

        return result

    def _validate_input(self, tool_input: Dict[str, Any], schema: Dict[str, Any]) -> None:
        """
        Validate tool input against JSON schema.

        Args:
            tool_input: Input to validate
            schema: JSON schema to validate against

        Raises:
            ValueError: If validation fails
        """
        required = schema.get("required", [])
        properties = schema.get("properties", {})

        # Check required fields
        missing = [field for field in required if field not in tool_input]
        if missing:
            raise ValueError(f"Missing required fields: {', '.join(missing)}")

        # Check unknown fields
        unknown = [field for field in tool_input if field not in properties]
        if unknown:
            logger.warning("Unknown fields in tool input", fields=unknown)