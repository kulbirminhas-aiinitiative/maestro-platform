"""
UTCP extensions for MaestroAPI - adds UTCP endpoints and functionality.

This module provides easy integration of UTCP protocol into existing MaestroAPI applications.
"""

from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from maestro_core_logging import get_logger

from .app import MaestroAPI
from .utcp_adapter import UTCPManualGenerator, UTCPToolExecutor

logger = get_logger(__name__)


class UTCPToolRequest(BaseModel):
    """Request model for UTCP tool execution."""

    tool_name: str = Field(..., description="Name of the tool to execute")
    tool_input: Dict[str, Any] = Field(..., description="Input parameters for the tool")
    context: Optional[Dict[str, Any]] = Field(None, description="Additional execution context")


class UTCPToolResponse(BaseModel):
    """Response model for UTCP tool execution."""

    success: bool
    tool_name: str
    result: Any
    error: Optional[str] = None


def add_utcp_support(
    api: MaestroAPI,
    base_url: Optional[str] = None,
    enable_execution: bool = True,
    custom_executor: Optional[UTCPToolExecutor] = None
) -> APIRouter:
    """
    Add UTCP protocol support to a MaestroAPI application.

    This adds the following endpoints:
    - GET /utcp-manual.json - Service discovery endpoint
    - POST /utcp/execute - Tool execution endpoint (if enabled)
    - GET /utcp/tools - List available tools

    Args:
        api: MaestroAPI instance to enhance
        base_url: Base URL for the service (auto-detected if None)
        enable_execution: Enable POST /utcp/execute endpoint
        custom_executor: Custom tool executor (uses default if None)

    Returns:
        APIRouter with UTCP endpoints

    Example:
        >>> from maestro_core_api import MaestroAPI, APIConfig
        >>> from maestro_core_api.utcp_extensions import add_utcp_support
        >>>
        >>> config = APIConfig(title="My Service", service_name="my-service")
        >>> api = MaestroAPI(config)
        >>>
        >>> # Add UTCP support
        >>> utcp_router = add_utcp_support(api, base_url="http://localhost:8000")
        >>>
        >>> # Your service is now UTCP-enabled!
        >>> # AI agents can discover it at /utcp-manual.json
    """
    router = APIRouter()

    # Determine base URL
    if base_url is None:
        base_url = f"http://{api.config.host}:{api.config.port}"

    # Create generator and executor
    generator = UTCPManualGenerator(
        app=api.app,
        base_url=base_url,
        service_version=api.config.version
    )

    executor = custom_executor or UTCPToolExecutor(api.app)

    @router.get(
        "/utcp-manual.json",
        tags=["UTCP"],
        summary="Get UTCP service manual",
        description="Returns the UTCP manual for service discovery by AI agents"
    )
    async def get_utcp_manual():
        """
        Expose UTCP manual for service discovery.

        This endpoint allows AI agents to discover what tools this service provides
        and how to call them using the Universal Tool Calling Protocol.
        """
        try:
            manual = generator.generate_manual()
            logger.info("UTCP manual requested", tool_count=len(manual.get("tools", [])))
            return manual
        except Exception as e:
            logger.error("Failed to generate UTCP manual", error=str(e))
            raise HTTPException(status_code=500, detail="Failed to generate UTCP manual")

    @router.get(
        "/utcp/tools",
        tags=["UTCP"],
        summary="List available tools",
        description="Returns a list of all tools available through this service"
    )
    async def list_tools():
        """
        List all available UTCP tools.

        Returns simplified tool list for browsing and discovery.
        """
        try:
            manual = generator.generate_manual()
            tools = manual.get("tools", [])

            # Simplify tool list
            tool_list = [
                {
                    "name": tool["name"],
                    "description": tool["description"],
                    "tags": tool.get("metadata", {}).get("tags", [])
                }
                for tool in tools
            ]

            return {
                "service": manual["metadata"]["name"],
                "tool_count": len(tool_list),
                "tools": tool_list
            }
        except Exception as e:
            logger.error("Failed to list tools", error=str(e))
            raise HTTPException(status_code=500, detail="Failed to list tools")

    if enable_execution:
        @router.post(
            "/utcp/execute",
            response_model=UTCPToolResponse,
            tags=["UTCP"],
            summary="Execute a tool",
            description="Execute a UTCP tool with given inputs"
        )
        async def execute_tool(request: UTCPToolRequest):
            """
            Execute a UTCP tool.

            This endpoint allows direct tool invocation via UTCP protocol.
            Note: This is a simplified executor for demonstration.
            Production use should integrate with actual route handlers.
            """
            try:
                logger.info(
                    "UTCP tool execution requested",
                    tool=request.tool_name,
                    input_keys=list(request.tool_input.keys())
                )

                result = await executor.execute_tool(
                    tool_name=request.tool_name,
                    tool_input=request.tool_input,
                    context=request.context
                )

                return UTCPToolResponse(
                    success=True,
                    tool_name=request.tool_name,
                    result=result
                )

            except ValueError as e:
                logger.warning("Tool execution validation error", error=str(e))
                return UTCPToolResponse(
                    success=False,
                    tool_name=request.tool_name,
                    result=None,
                    error=str(e)
                )

            except Exception as e:
                logger.error("Tool execution failed", error=str(e), exc_info=True)
                return UTCPToolResponse(
                    success=False,
                    tool_name=request.tool_name,
                    result=None,
                    error=f"Internal error: {str(e)}"
                )

    # Include router in the API
    api.include_router(router, prefix="", tags=["UTCP"])

    logger.info(
        "UTCP support added to MaestroAPI",
        base_url=base_url,
        execution_enabled=enable_execution
    )

    return router


class UTCPEnabledAPI(MaestroAPI):
    """
    Extended MaestroAPI with built-in UTCP support.

    This is a convenience class that automatically adds UTCP endpoints
    during initialization.

    Example:
        >>> from maestro_core_api.utcp_extensions import UTCPEnabledAPI
        >>> from maestro_core_api import APIConfig
        >>>
        >>> config = APIConfig(title="My Service", service_name="my-service")
        >>> api = UTCPEnabledAPI(config, base_url="http://localhost:8000")
        >>>
        >>> # UTCP endpoints are automatically available!
        >>> @api.get("/custom-endpoint")
        >>> async def my_endpoint():
        >>>     return {"status": "ok"}
    """

    def __init__(
        self,
        config,
        base_url: Optional[str] = None,
        enable_utcp_execution: bool = True
    ):
        """
        Initialize UTCP-enabled API.

        Args:
            config: APIConfig instance
            base_url: Base URL for UTCP manual (auto-detected if None)
            enable_utcp_execution: Enable tool execution endpoint
        """
        super().__init__(config)

        # Add UTCP support
        self._utcp_router = add_utcp_support(
            api=self,
            base_url=base_url,
            enable_execution=enable_utcp_execution
        )

        logger.info("UTCPEnabledAPI initialized with UTCP support")

    @property
    def utcp_router(self) -> APIRouter:
        """Get the UTCP router."""
        return self._utcp_router