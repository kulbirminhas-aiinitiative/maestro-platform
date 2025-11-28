from __future__ import annotations
import asyncio
import sys
import os
from typing import AsyncIterator
from execution_platform.spi import LLMClient, ChatRequest, ChatChunk, Usage

# Use REAL Claude SDK integration from maestro-hive
class ClaudeAgentClient(LLMClient):
    def __init__(self):
        # Add maestro-hive to path for claude_code_sdk
        self._setup_paths()
        self._sdk_available = self._check_sdk()

    def _setup_paths(self):
        """Add maestro-hive to sys.path for claude_code_sdk"""
        root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
        hive_path = os.path.join(root, "maestro-hive")
        if os.path.exists(hive_path) and hive_path not in sys.path:
            sys.path.insert(0, hive_path)

    def _check_sdk(self) -> bool:
        """Check if Claude SDK is available"""
        try:
            from claude_code_sdk import query, ClaudeCodeOptions
            return True
        except ImportError:
            return False

    async def chat(self, req: ChatRequest) -> AsyncIterator[ChatChunk]:
        """Execute chat using REAL Claude Code SDK"""
        if not self._sdk_available:
            # Fallback to stub if SDK not available
            text = "".join(m.content for m in req.messages if m.role in ("user", "system"))
            yield ChatChunk(delta_text=f"[claude_agent_sdk_unavailable] {text}", finish_reason="stop")
            return

        try:
            from claude_code_sdk import query, ClaudeCodeOptions
            
            # Build prompt from messages
            sys_prompt = ""
            user_messages = []
            
            for m in req.messages:
                if m.role == "system":
                    sys_prompt = m.content
                elif m.role == "user":
                    user_messages.append(m.content)
            
            # Combine into single prompt
            if sys_prompt:
                prompt = f"{sys_prompt}\n\n{' '.join(user_messages)}"
            else:
                prompt = " ".join(user_messages)
            
            # Configure Claude SDK options
            opts = ClaudeCodeOptions()
            opts.max_tokens = req.max_tokens or 4096
            opts.temperature = req.temperature or 0.7
            opts.permission_mode = "acceptEdits"
            
            # Stream results from REAL Claude SDK
            total_text = ""
            async for msg in query(prompt, opts):
                if msg.message_type == "text" and msg.content:
                    total_text += msg.content
                    yield ChatChunk(delta_text=msg.content)
                elif msg.message_type == "error":
                    yield ChatChunk(delta_text=f"[error] {msg.content}")
            
            # Send final chunk with usage
            yield ChatChunk(
                finish_reason="stop", 
                usage=Usage(
                    prompt_tokens=len(prompt.split()),
                    completion_tokens=len(total_text.split()),
                    total_tokens=len(prompt.split()) + len(total_text.split())
                )
            )
            
        except Exception as e:
            # Error fallback
            yield ChatChunk(delta_text=f"[claude_agent_error] {str(e)}", finish_reason="error")
