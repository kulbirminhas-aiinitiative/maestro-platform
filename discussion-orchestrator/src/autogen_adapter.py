"""
AutoGen adapter for execution-platform integration.

Wraps execution-platform's PersonaRouter and LLMClient to work with AutoGen's
agent framework. Converts between AutoGen message format and execution-platform
ChatRequest format.
"""
from __future__ import annotations
import sys
import os
from typing import Any, Dict, List, Optional, AsyncIterator, Union
import asyncio
import logging

# Add execution-platform to sys.path
execution_platform_path = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "../../../execution-platform")
)
if execution_platform_path not in sys.path:
    sys.path.insert(0, execution_platform_path)

from execution_platform.maestro_sdk.types import ChatRequest, ChatChunk, Message, Role
from execution_platform.maestro_sdk.interfaces import LLMClient
from execution_platform.maestro_sdk.router import get_adapter

logger = logging.getLogger(__name__)


class ExecutionPlatformLLM:
    """
    Wrapper for execution-platform LLMClient to be used with AutoGen agents.

    This class bridges the execution-platform's streaming chat interface with
    AutoGen's expected LLM client interface. It handles message format conversion
    and streaming response aggregation.
    """

    def __init__(
        self,
        provider: str = "anthropic",
        temperature: float = 0.7,
        max_tokens: int = 2048,
        **kwargs
    ):
        """
        Initialize ExecutionPlatformLLM.

        Args:
            provider: LLM provider (anthropic, openai, gemini, claude_agent)
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            **kwargs: Additional configuration options
        """
        self.provider = provider
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.config = kwargs

        # Get the appropriate adapter from execution-platform
        self.client: LLMClient = get_adapter(provider)
        logger.info(f"Initialized ExecutionPlatformLLM with provider: {provider}")

    async def create_completion(
        self,
        messages: List[Dict[str, str]],
        **kwargs
    ) -> Dict[str, Any]:
        """
        Create a chat completion using execution-platform.

        This method is called by AutoGen agents to generate responses.
        It converts AutoGen's message format to execution-platform's format,
        streams the response, and returns it in AutoGen's expected format.

        Args:
            messages: List of message dicts with 'role' and 'content'
            **kwargs: Additional parameters for the request

        Returns:
            Dict with 'choices' containing the generated response
        """
        try:
            # Convert AutoGen messages to execution-platform format
            chat_request = self._convert_to_chat_request(messages, **kwargs)

            # Stream response from execution-platform
            full_response = await self._stream_response(chat_request)

            # Return in AutoGen's expected format
            return {
                "choices": [
                    {
                        "message": {
                            "role": "assistant",
                            "content": full_response["content"]
                        },
                        "finish_reason": full_response.get("finish_reason", "stop")
                    }
                ],
                "usage": full_response.get("usage", {}),
                "model": self.provider,
            }

        except Exception as e:
            logger.error(f"Error in create_completion: {e}", exc_info=True)
            raise

    async def stream_completion(
        self,
        messages: List[Dict[str, str]],
        **kwargs
    ) -> AsyncIterator[Dict[str, Any]]:
        """
        Stream a chat completion from execution-platform.

        Yields:
            Streaming chunks in AutoGen's expected format
        """
        try:
            chat_request = self._convert_to_chat_request(messages, **kwargs)

            async for chunk in self.client.chat(chat_request):
                if chunk.delta_text:
                    yield {
                        "choices": [
                            {
                                "delta": {
                                    "role": "assistant",
                                    "content": chunk.delta_text
                                },
                                "finish_reason": None
                            }
                        ]
                    }

                if chunk.finish_reason:
                    yield {
                        "choices": [
                            {
                                "delta": {},
                                "finish_reason": chunk.finish_reason
                            }
                        ],
                        "usage": self._convert_usage(chunk.usage) if chunk.usage else {}
                    }

        except Exception as e:
            logger.error(f"Error in stream_completion: {e}", exc_info=True)
            raise

    def _convert_to_chat_request(
        self,
        messages: List[Dict[str, str]],
        **kwargs
    ) -> ChatRequest:
        """
        Convert AutoGen message format to execution-platform ChatRequest.

        Args:
            messages: AutoGen format messages
            **kwargs: Additional parameters

        Returns:
            ChatRequest object for execution-platform
        """
        # Extract system message if present
        system_prompt = None
        converted_messages = []

        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")

            if role == "system":
                system_prompt = content
            else:
                # Map roles to execution-platform's Role type
                ep_role: Role = self._map_role(role)
                converted_messages.append(
                    Message(
                        role=ep_role,
                        content=content,
                        name=msg.get("name")
                    )
                )

        # Merge kwargs with instance config
        temperature = kwargs.get("temperature", self.temperature)
        max_tokens = kwargs.get("max_tokens", self.max_tokens)

        return ChatRequest(
            messages=converted_messages,
            system=system_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
            tools=kwargs.get("tools"),
            tool_choice=kwargs.get("tool_choice"),
        )

    def _map_role(self, autogen_role: str) -> Role:
        """
        Map AutoGen role to execution-platform Role.

        Args:
            autogen_role: Role from AutoGen message

        Returns:
            Corresponding execution-platform Role
        """
        role_mapping = {
            "user": "user",
            "assistant": "assistant",
            "system": "system",
            "function": "tool",
            "tool": "tool",
        }
        return role_mapping.get(autogen_role.lower(), "user")

    async def _stream_response(self, chat_request: ChatRequest) -> Dict[str, Any]:
        """
        Stream response from execution-platform and aggregate it.

        Args:
            chat_request: ChatRequest for execution-platform

        Returns:
            Dict with aggregated response content and metadata
        """
        content_parts = []
        finish_reason = None
        usage = None

        try:
            async for chunk in self.client.chat(chat_request):
                if chunk.delta_text:
                    content_parts.append(chunk.delta_text)

                if chunk.finish_reason:
                    finish_reason = chunk.finish_reason

                if chunk.usage:
                    usage = chunk.usage

            return {
                "content": "".join(content_parts),
                "finish_reason": finish_reason,
                "usage": self._convert_usage(usage) if usage else {}
            }

        except Exception as e:
            logger.error(f"Error streaming response: {e}", exc_info=True)
            raise

    def _convert_usage(self, usage: Any) -> Dict[str, Any]:
        """
        Convert execution-platform Usage to AutoGen format.

        Args:
            usage: Usage object from execution-platform

        Returns:
            Dict with usage information
        """
        if not usage:
            return {}

        return {
            "prompt_tokens": getattr(usage, "input_tokens", 0) or 0,
            "completion_tokens": getattr(usage, "output_tokens", 0) or 0,
            "total_tokens": (
                (getattr(usage, "input_tokens", 0) or 0) +
                (getattr(usage, "output_tokens", 0) or 0)
            ),
            "cost_usd": getattr(usage, "cost_usd", None)
        }

    def get_client(self) -> LLMClient:
        """
        Get the underlying execution-platform LLMClient.

        Returns:
            LLMClient instance
        """
        return self.client


class AutoGenModelClient:
    """
    Model client wrapper for AutoGen compatibility.

    This provides a synchronous interface that AutoGen expects while
    internally using async execution-platform calls.
    """

    def __init__(self, llm: ExecutionPlatformLLM):
        """
        Initialize with ExecutionPlatformLLM instance.

        Args:
            llm: ExecutionPlatformLLM instance to wrap
        """
        self.llm = llm
        self._loop = None

    def _get_event_loop(self):
        """Get or create event loop for async operations."""
        if self._loop is None or self._loop.is_closed():
            try:
                self._loop = asyncio.get_event_loop()
            except RuntimeError:
                self._loop = asyncio.new_event_loop()
                asyncio.set_event_loop(self._loop)
        return self._loop

    def create(
        self,
        messages: List[Dict[str, str]],
        **kwargs
    ) -> Dict[str, Any]:
        """
        Synchronous wrapper for create_completion.

        Args:
            messages: List of message dicts
            **kwargs: Additional parameters

        Returns:
            Response dict in AutoGen format
        """
        loop = self._get_event_loop()
        return loop.run_until_complete(
            self.llm.create_completion(messages, **kwargs)
        )

    def message_retrieval(self, response: Dict[str, Any]) -> str:
        """
        Extract message content from response.

        Args:
            response: Response dict from create()

        Returns:
            Message content string
        """
        try:
            return response["choices"][0]["message"]["content"]
        except (KeyError, IndexError) as e:
            logger.error(f"Error retrieving message: {e}")
            return ""

    def cost(self, response: Dict[str, Any]) -> float:
        """
        Calculate cost from response.

        Args:
            response: Response dict from create()

        Returns:
            Cost in USD
        """
        try:
            return response.get("usage", {}).get("cost_usd", 0.0) or 0.0
        except Exception as e:
            logger.error(f"Error calculating cost: {e}")
            return 0.0
