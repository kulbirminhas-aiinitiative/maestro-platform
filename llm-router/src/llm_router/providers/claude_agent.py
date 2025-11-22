from __future__ import annotations
import os
from typing import AsyncIterator
from ..spi import LLMClient, ChatRequest, ChatChunk, Usage

class ClaudeAgentClient(LLMClient):
    """
    Claude client using REAL claude-agent-sdk (same as existing v1 services)

    This integrates the working claude-agent-sdk that's used successfully
    in maestro-hive and execution-platform services.
    """

    def __init__(self):
        self.api_key = os.getenv("ANTHROPIC_API_KEY")
        self._check_sdk_availability()

    def _check_sdk_availability(self) -> bool:
        """Check if claude-agent-sdk is available"""
        try:
            # Try importing the REAL claude-agent-sdk (with yoga.wasm fix)
            from .claude_agent_sdk_fixed import query, ClaudeAgentOptions
            self.sdk_available = True
            self.query = query
            self.ClaudeAgentOptions = ClaudeAgentOptions
            return True
        except ImportError:
            self.sdk_available = False
            return False

    async def chat(self, req: ChatRequest) -> AsyncIterator[ChatChunk]:
        """
        Execute chat using claude-agent-sdk

        Priority:
        1. Use claude-agent-sdk if available (matches v1 services)
        2. Fallback to direct Anthropic API if SDK unavailable
        """

        # APPROACH 1: Try claude-agent-sdk (REAL SDK used by v1 services)
        if self.sdk_available:
            try:
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

                # Configure Claude Agent SDK options
                opts = self.ClaudeAgentOptions()
                opts.max_tokens = req.max_tokens or 4096
                opts.temperature = req.temperature or 0.7
                opts.model = req.model or "claude-3-haiku-20240307"

                # Stream results from REAL Claude Agent SDK
                total_text = ""
                async for msg in self.query(prompt=prompt, options=opts):
                    if hasattr(msg, 'content') and msg.content:
                        # Extract text from the message
                        if hasattr(msg.content, 'text'):
                            text = msg.content.text
                        elif isinstance(msg.content, str):
                            text = msg.content
                        elif isinstance(msg.content, list):
                            # Handle list of content blocks
                            text = ""
                            for block in msg.content:
                                if hasattr(block, 'text'):
                                    text += block.text
                                elif isinstance(block, str):
                                    text += block
                        else:
                            continue

                        if text:
                            total_text += text
                            yield ChatChunk(delta_text=text)

                # Send final chunk with usage
                yield ChatChunk(
                    finish_reason="stop",
                    usage=Usage(
                        prompt_tokens=len(prompt.split()),
                        completion_tokens=len(total_text.split()),
                        total_tokens=len(prompt.split()) + len(total_text.split())
                    )
                )
                return

            except Exception as e:
                # SDK failed, log and fall through to API approach
                pass

        # APPROACH 2: Direct Anthropic API (fallback)
        if not self.api_key:
            yield ChatChunk(delta_text="[error] ANTHROPIC_API_KEY not set and claude-agent-sdk unavailable", finish_reason="error")
            return

        try:
            import anthropic

            client = anthropic.AsyncAnthropic(api_key=self.api_key)

            # Convert messages to Anthropic format
            messages = []
            system_prompt = None

            for m in req.messages:
                if m.role == "system":
                    system_prompt = m.content
                else:
                    messages.append({
                        "role": m.role,
                        "content": m.content
                    })

            # Try multiple model names (only haiku is available with this API key)
            model_names = [
                req.model if req.model else None,
                "claude-3-haiku-20240307",
            ]

            model_names = [m for m in model_names if m]

            for model_name in model_names:
                try:
                    params = {
                        "model": model_name,
                        "messages": messages,
                        "max_tokens": req.max_tokens or 4096,
                        "temperature": req.temperature or 0.7,
                    }

                    if system_prompt:
                        params["system"] = system_prompt

                    total_text = ""
                    prompt_tokens = 0
                    completion_tokens = 0

                    message = await client.messages.create(**params)
                    for block in message.content:
                        if hasattr(block, 'text'):
                            total_text += block.text
                            yield ChatChunk(delta_text=block.text)

                    prompt_tokens = message.usage.input_tokens
                    completion_tokens = message.usage.output_tokens

                    yield ChatChunk(
                        finish_reason="stop",
                        usage=Usage(
                            prompt_tokens=prompt_tokens,
                            completion_tokens=completion_tokens,
                            total_tokens=prompt_tokens + completion_tokens
                        )
                    )
                    return

                except Exception as model_error:
                    if "404" in str(model_error) or "not_found" in str(model_error):
                        continue
                    else:
                        raise

            yield ChatChunk(
                delta_text=f"[error] All Claude models failed. Tried: {', '.join(model_names)}",
                finish_reason="error"
            )

        except Exception as e:
            yield ChatChunk(delta_text=f"[claude_error] {str(e)}", finish_reason="error")
