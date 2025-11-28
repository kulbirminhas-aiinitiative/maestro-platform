from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Literal, Optional

Role = Literal["system", "user", "assistant", "tool"]

@dataclass
class Message:
    role: Role
    content: str
    name: Optional[str] = None
    tool_call_id: Optional[str] = None

@dataclass
class ToolDefinition:
    name: str
    description: Optional[str] = None
    json_schema: Dict[str, Any] = field(default_factory=dict)

@dataclass
class ChatRequest:
    messages: List[Message]
    tools: Optional[List[ToolDefinition]] = None
    tool_choice: Optional[Literal["auto", "none"] | Dict[str, Any]] = None
    system: Optional[str] = None
    temperature: float = 0.7
    max_tokens: int = 1024
    stop: Optional[List[str]] = None
    response_format: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class Usage:
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    cost_usd: Optional[float] = None

@dataclass
class ToolCall:
    id: str
    name: str
    arguments: Dict[str, Any]

@dataclass
class ChatChunk:
    delta_text: Optional[str] = None
    tool_call_delta: Optional[ToolCall] = None
    finish_reason: Optional[str] = None
    usage: Optional[Usage] = None
    provider_events: Optional[Dict[str, Any]] = None
