"""
Claude-UTCP Orchestrator - AI-powered service orchestration using UTCP.

This module integrates Claude's AI capabilities with UTCP service discovery
to create an intelligent, self-organizing microservices orchestrator.
"""

import os
from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass

from anthropic import Anthropic, AsyncAnthropic
from anthropic.types import Message, MessageParam, TextBlock, ToolUseBlock

from maestro_core_logging import get_logger

from .utcp_registry import UTCPServiceRegistry

logger = get_logger(__name__)


@dataclass
class OrchestrationResult:
    """Result of an orchestration request."""

    success: bool
    response: str
    tool_calls: List[Dict[str, Any]]
    tool_results: List[Dict[str, Any]]
    tokens_used: Dict[str, int]
    model: str
    error: Optional[str] = None


class ClaudeUTCPOrchestrator:
    """
    Claude-powered orchestrator using UTCP for dynamic service discovery.

    This orchestrator allows Claude to:
    1. Discover available microservices via UTCP
    2. Select appropriate services based on user requirements
    3. Call services directly using UTCP protocol
    4. Orchestrate complex multi-service workflows
    5. Provide intelligent responses based on service results

    Example:
        >>> orchestrator = ClaudeUTCPOrchestrator(api_key="your-key")
        >>>
        >>> # Initialize with service discovery
        >>> await orchestrator.initialize([
        ...     "http://workflow-engine:8001",
        ...     "http://intelligence-service:8002"
        ... ])
        >>>
        >>> # Process user request
        >>> result = await orchestrator.process_request(
        ...     "Create a comprehensive testing workflow for an e-commerce site"
        ... )
        >>> print(result.response)
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "claude-sonnet-4-5-20250929",
        max_tokens: int = 4096,
        registry: Optional[UTCPServiceRegistry] = None
    ):
        """
        Initialize Claude-UTCP orchestrator.

        Args:
            api_key: Anthropic API key (uses ANTHROPIC_API_KEY env var if None)
            model: Claude model to use
            max_tokens: Maximum tokens for responses
            registry: UTCP service registry (creates new if None)
        """
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY must be provided or set in environment")

        self.model = model
        self.max_tokens = max_tokens

        # Initialize Claude clients
        self.client = Anthropic(api_key=self.api_key)
        self.async_client = AsyncAnthropic(api_key=self.api_key)

        # Initialize or use provided registry
        self.registry = registry or UTCPServiceRegistry()

        logger.info(
            "Claude-UTCP Orchestrator initialized",
            model=self.model,
            max_tokens=self.max_tokens
        )

    async def initialize(self, service_urls: List[str]) -> None:
        """
        Initialize orchestrator with service discovery.

        Args:
            service_urls: List of service base URLs to discover
        """
        logger.info("Initializing orchestrator with service discovery", url_count=len(service_urls))

        discovered = await self.registry.discover_services(service_urls)

        logger.info(
            "Service discovery completed",
            discovered_count=len(discovered),
            services=[s.name for s in discovered]
        )

    async def process_request(
        self,
        user_requirement: str,
        conversation_history: Optional[List[MessageParam]] = None,
        system_prompt: Optional[str] = None
    ) -> OrchestrationResult:
        """
        Process a user requirement using Claude and UTCP services.

        Claude will:
        1. Analyze the user requirement
        2. Select appropriate services from the UTCP registry
        3. Call services with proper parameters
        4. Synthesize results into a coherent response

        Args:
            user_requirement: User's request or requirement
            conversation_history: Optional conversation context
            system_prompt: Optional system prompt override

        Returns:
            OrchestrationResult with response and execution details
        """
        logger.info("Processing orchestration request", requirement_length=len(user_requirement))

        try:
            # Get available tools from registry
            available_tools = self._get_claude_tools()

            if not available_tools:
                logger.warning("No UTCP services available")
                return OrchestrationResult(
                    success=False,
                    response="No services available for orchestration",
                    tool_calls=[],
                    tool_results=[],
                    tokens_used={},
                    model=self.model,
                    error="No services registered"
                )

            # Build system prompt
            system = system_prompt or self._build_system_prompt()

            # Build messages
            messages: List[MessageParam] = conversation_history or []
            messages.append({
                "role": "user",
                "content": user_requirement
            })

            # Initial Claude call to select tools
            logger.debug("Calling Claude for tool selection", tool_count=len(available_tools))

            message = await self.async_client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                system=system,
                tools=available_tools,
                messages=messages
            )

            # Extract tool calls
            tool_calls = self._extract_tool_calls(message)

            if not tool_calls:
                # No tool calls needed - direct response
                response_text = self._extract_text_response(message)

                return OrchestrationResult(
                    success=True,
                    response=response_text,
                    tool_calls=[],
                    tool_results=[],
                    tokens_used={
                        "input": message.usage.input_tokens,
                        "output": message.usage.output_tokens
                    },
                    model=self.model
                )

            # Execute tool calls via UTCP
            tool_results = await self._execute_tool_calls(tool_calls)

            # Get final response from Claude with tool results
            messages.append({
                "role": "assistant",
                "content": message.content
            })

            messages.append({
                "role": "user",
                "content": self._format_tool_results(tool_calls, tool_results)
            })

            final_message = await self.async_client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                system=system,
                messages=messages
            )

            response_text = self._extract_text_response(final_message)

            total_input_tokens = message.usage.input_tokens + final_message.usage.input_tokens
            total_output_tokens = message.usage.output_tokens + final_message.usage.output_tokens

            result = OrchestrationResult(
                success=True,
                response=response_text,
                tool_calls=tool_calls,
                tool_results=tool_results,
                tokens_used={
                    "input": total_input_tokens,
                    "output": total_output_tokens,
                    "total": total_input_tokens + total_output_tokens
                },
                model=self.model
            )

            logger.info(
                "Orchestration completed successfully",
                tool_calls=len(tool_calls),
                tokens_used=result.tokens_used["total"]
            )

            return result

        except Exception as e:
            logger.error("Orchestration failed", error=str(e), exc_info=True)

            return OrchestrationResult(
                success=False,
                response=f"Orchestration failed: {str(e)}",
                tool_calls=[],
                tool_results=[],
                tokens_used={},
                model=self.model,
                error=str(e)
            )

    def _get_claude_tools(self) -> List[Dict[str, Any]]:
        """
        Get all available tools from UTCP registry in Claude's format.

        Converts UTCP tool definitions to Claude's tool calling format.
        """
        utcp_tools = self.registry.list_available_tools()

        claude_tools = []

        for tool in utcp_tools:
            claude_tool = {
                "name": tool["name"],
                "description": tool["description"],
                "input_schema": tool["input_schema"]
            }

            # Add service context to description
            service_info = tool.get("service", {})
            if service_info:
                claude_tool["description"] += f"\n[Service: {service_info.get('name', 'unknown')}]"

            claude_tools.append(claude_tool)

        return claude_tools

    def _build_system_prompt(self) -> str:
        """Build system prompt for Claude."""
        services = self.registry.list_services(healthy_only=True)
        service_names = [s.name for s in services]

        return f"""You are an intelligent orchestrator for the MAESTRO ecosystem.

You have access to the following microservices:
{', '.join(service_names)}

Your role is to:
1. Analyze user requirements and break them down into actionable tasks
2. Select the most appropriate service(s) to handle each task
3. Call services with proper parameters using the tools available
4. Synthesize results into clear, actionable responses

Guidelines:
- Use parallel tool calls when tasks are independent
- Provide detailed, structured responses
- If a service fails, try alternative approaches
- Always explain what services you're using and why

Focus on delivering value through intelligent service orchestration."""

    def _extract_tool_calls(self, message: Message) -> List[Dict[str, Any]]:
        """Extract tool use blocks from Claude's response."""
        tool_calls = []

        for block in message.content:
            if isinstance(block, ToolUseBlock):
                tool_calls.append({
                    "id": block.id,
                    "name": block.name,
                    "input": block.input
                })

        return tool_calls

    def _extract_text_response(self, message: Message) -> str:
        """Extract text content from Claude's response."""
        text_blocks = [
            block.text for block in message.content
            if isinstance(block, TextBlock)
        ]

        return "\n\n".join(text_blocks)

    async def _execute_tool_calls(
        self,
        tool_calls: List[Dict[str, Any]],
        max_concurrent: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Execute tool calls via UTCP registry with parallel execution.

        Independent tool calls are executed in parallel for better performance.

        Args:
            tool_calls: List of tool calls to execute
            max_concurrent: Maximum concurrent executions (default: 5)

        Returns:
            List of execution results
        """
        if not tool_calls:
            return []

        # Single tool call - execute directly
        if len(tool_calls) == 1:
            return [await self._execute_single_tool(tool_calls[0])]

        # Multiple tool calls - execute in parallel with semaphore limit
        logger.info(f"Executing {len(tool_calls)} tool calls in parallel (max {max_concurrent} concurrent)")

        semaphore = asyncio.Semaphore(max_concurrent)

        async def execute_with_limit(tool_call):
            async with semaphore:
                return await self._execute_single_tool(tool_call)

        # Execute all tool calls in parallel
        results = await asyncio.gather(
            *[execute_with_limit(call) for call in tool_calls],
            return_exceptions=True
        )

        # Convert exceptions to error results
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(
                    "Tool execution failed",
                    tool=tool_calls[i]["name"],
                    error=str(result)
                )
                processed_results.append({
                    "id": tool_calls[i]["id"],
                    "success": False,
                    "error": str(result)
                })
            else:
                processed_results.append(result)

        logger.info(f"Completed {len(processed_results)} tool executions ({len([r for r in processed_results if r['success']])} successful)")
        return processed_results

    async def _execute_single_tool(self, tool_call: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a single tool call.

        Args:
            tool_call: Tool call dictionary with id, name, and input

        Returns:
            Execution result dictionary
        """
        try:
            logger.debug("Executing tool via UTCP", tool=tool_call["name"])

            result = await self.registry.call_tool(
                tool_name=tool_call["name"],
                tool_args=tool_call["input"]
            )

            return {
                "id": tool_call["id"],
                "success": True,
                "result": result
            }

        except Exception as e:
            logger.error(
                "Tool execution failed",
                tool=tool_call["name"],
                error=str(e)
            )

            return {
                "id": tool_call["id"],
                "success": False,
                "error": str(e)
            }

    def _format_tool_results(
        self,
        tool_calls: List[Dict[str, Any]],
        tool_results: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Format tool results for Claude's next message."""
        formatted = []

        for call, result in zip(tool_calls, tool_results):
            if result["success"]:
                formatted.append({
                    "type": "tool_result",
                    "tool_use_id": result["id"],
                    "content": str(result["result"])
                })
            else:
                formatted.append({
                    "type": "tool_result",
                    "tool_use_id": result["id"],
                    "content": f"Error: {result['error']}",
                    "is_error": True
                })

        return formatted

    async def health_check(self) -> Dict[str, Any]:
        """
        Check orchestrator health and service status.

        Returns:
            Health status dictionary
        """
        service_health = await self.registry.health_check()

        return {
            "orchestrator": "healthy",
            "model": self.model,
            "services": service_health,
            "healthy_services": sum(1 for h in service_health.values() if h),
            "total_services": len(service_health)
        }

    async def cleanup(self) -> None:
        """Cleanup resources."""
        await self.registry.cleanup()
        logger.info("Orchestrator cleanup completed")