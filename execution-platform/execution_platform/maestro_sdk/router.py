from __future__ import annotations
from typing import Literal
from execution_platform.adapters.mock_adapter import MockAdapter
from execution_platform.adapters.anthropic_adapter import AnthropicAdapter
from execution_platform.adapters.openai_adapter import OpenAIAdapter
from execution_platform.adapters.gemini_adapter import GeminiAdapter
from execution_platform.adapters.claude_agent_adapter import ClaudeAgentAdapter
from execution_platform.maestro_sdk.interfaces import LLMClient
from execution_platform.config import settings

def get_adapter(provider: Literal["mock","anthropic","openai","gemini","claude_agent","auto"]) -> LLMClient:
    if provider == "auto":
        if settings.openai_api_key:
            return OpenAIAdapter()
        if settings.anthropic_api_key:
            return AnthropicAdapter()
        if getattr(settings, 'gemini_api_key', None):
            return GeminiAdapter()
        # Last-resort fallback to local Claude Agent SDK wrapper
        return ClaudeAgentAdapter()
    if provider == "anthropic":
        return AnthropicAdapter()
    if provider == "openai":
        return OpenAIAdapter()
    if provider == "gemini":
        return GeminiAdapter()
    if provider == "claude_agent":
        return ClaudeAgentAdapter()
    return MockAdapter()
