from __future__ import annotations
from typing import AsyncIterator
from execution_platform.maestro_sdk.types import ChatRequest, ChatChunk, Usage, ToolCall
from execution_platform.maestro_sdk.interfaces import LLMClient
from execution_platform.config import settings
import json

try:
    import google.generativeai as genai  # type: ignore
    from google.generativeai.types import GenerationConfig  # type: ignore
except Exception:
    genai = None  # type: ignore
    GenerationConfig = None  # type: ignore

class GeminiAdapter(LLMClient):
    """
    Gemini adapter with true async streaming support.

    Features:
    - Async streaming via generate_content_async with stream=True
    - Tool/function calling support
    - Usage tracking
    - Consistent ChatChunk output format
    """

    async def chat(self, req: ChatRequest) -> AsyncIterator[ChatChunk]:
        if genai is None or not settings.gemini_api_key:
            last = next((m for m in reversed(req.messages) if m.role == "user"), None)
            text = last.content if last else "ok"
            yield ChatChunk(delta_text=f"[gemini-disabled] {text}")
            yield ChatChunk(finish_reason="stop", usage=Usage())
            return

        genai.configure(api_key=settings.gemini_api_key)

        # Get model name from settings
        model_name = getattr(settings, 'gemini_model', 'gemini-2.0-flash-exp')

        # Handle old model names - map to gemini-2.0-flash-exp
        if model_name in ('gemini-1.5-pro', 'gemini-1.5-pro-latest', 'gemini-1.5-flash'):
            model_name = 'gemini-2.0-flash-exp'

        # Remove models/ prefix if present to avoid duplication
        if model_name.startswith('models/'):
            model_name = model_name.replace('models/', '')

        # Build generation config
        generation_config = None
        if GenerationConfig:
            generation_config = GenerationConfig(
                temperature=req.temperature if req.temperature is not None else 0.7,
                max_output_tokens=req.max_tokens if req.max_tokens else 4096,
            )

        # Build tools for function calling
        tools = None
        if req.tools:
            tools = []
            for tool in req.tools:
                tool_def = {
                    "name": tool.name,
                    "description": tool.description or "",
                    "parameters": tool.json_schema or {"type": "object", "properties": {}}
                }
                tools.append({"function_declarations": [tool_def]})

        # Create model with optional tools
        model_kwargs = {"model_name": model_name}
        if tools:
            model_kwargs["tools"] = tools
        if generation_config:
            model_kwargs["generation_config"] = generation_config

        model = genai.GenerativeModel(**model_kwargs)

        # Build conversation history for chat
        # Gemini uses 'user' and 'model' roles
        contents = []
        system_instruction = None

        for msg in req.messages:
            if msg.role == "system":
                # Gemini handles system as system_instruction
                system_instruction = msg.content
            elif msg.role == "user":
                contents.append({"role": "user", "parts": [{"text": msg.content}]})
            elif msg.role == "assistant":
                contents.append({"role": "model", "parts": [{"text": msg.content}]})

        # If system instruction provided, recreate model with it
        if system_instruction:
            model_kwargs["system_instruction"] = system_instruction
            model = genai.GenerativeModel(**model_kwargs)

        # Track usage
        input_tokens = 0
        output_tokens = 0

        try:
            # Use async streaming
            response = await model.generate_content_async(
                contents,
                stream=True
            )

            # Stream chunks as they arrive
            async for chunk in response:
                # Check for text content
                if hasattr(chunk, 'text') and chunk.text:
                    yield ChatChunk(delta_text=chunk.text)

                # Check for function calls
                if hasattr(chunk, 'candidates') and chunk.candidates:
                    for candidate in chunk.candidates:
                        if hasattr(candidate, 'content') and candidate.content:
                            for part in candidate.content.parts:
                                # Handle function call
                                if hasattr(part, 'function_call') and part.function_call:
                                    fc = part.function_call
                                    # Convert args to dict
                                    args = {}
                                    if hasattr(fc, 'args') and fc.args:
                                        try:
                                            args = dict(fc.args)
                                        except Exception:
                                            args = {}

                                    yield ChatChunk(
                                        tool_call_delta=ToolCall(
                                            id=f"call_{fc.name}",
                                            name=fc.name,
                                            arguments=args
                                        )
                                    )

                # Track usage if available
                if hasattr(chunk, 'usage_metadata'):
                    um = chunk.usage_metadata
                    if hasattr(um, 'prompt_token_count'):
                        input_tokens = um.prompt_token_count
                    if hasattr(um, 'candidates_token_count'):
                        output_tokens = um.candidates_token_count

            # Final chunk with usage
            yield ChatChunk(
                finish_reason="stop",
                usage=Usage(
                    input_tokens=input_tokens if input_tokens else None,
                    output_tokens=output_tokens if output_tokens else None
                )
            )

        except Exception as e:
            # Yield error information
            yield ChatChunk(delta_text=f"[Gemini Error: {str(e)}]")
            yield ChatChunk(finish_reason="error", usage=Usage())
