from __future__ import annotations
from dataclasses import dataclass, field
from typing import Protocol, AsyncIterator, Optional, Literal, Any

Role = Literal["system", "user", "assistant", "tool"]

@dataclass
class Message:
    role: Role
    content: str
    tool_call_id: Optional[str] = None

@dataclass
class ToolParameter:
    name: str
    type: str
    required: bool = False
    description: Optional[str] = None

@dataclass
class ToolDefinition:
    name: str
    description: Optional[str] = None
    parameters: list[ToolParameter] = field(default_factory=list)

@dataclass
class ChatRequest:
    messages: list[Message]
    tools: Optional[list[ToolDefinition]] = None
    max_tokens: int = 4096
    temperature: float = 0.7
    stream: bool = True
    model: Optional[str] = None
    metadata: dict[str, Any] = field(default_factory=dict)

@dataclass
class Usage:
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0

@dataclass
class ToolCallDelta:
    id: Optional[str] = None
    name: Optional[str] = None
    arguments_json: Optional[str] = None

@dataclass
class ChatChunk:
    delta_text: Optional[str] = None
    tool_call_delta: Optional[ToolCallDelta] = None
    finish_reason: Optional[str] = None
    usage: Optional[Usage] = None

class LLMError(Exception):
    pass

class RateLimitError(LLMError):
    pass

class ToolCallError(LLMError):
    pass

class LLMClient(Protocol):
    async def chat(self, req: ChatRequest) -> AsyncIterator[ChatChunk]:
        ...
