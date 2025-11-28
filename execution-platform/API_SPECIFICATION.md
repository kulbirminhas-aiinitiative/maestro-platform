# Execution Platform - API Specification

**Version**: 1.0.0  
**Date**: 2025-10-11  
**Status**: Production

---

## API Overview

The Execution Platform provides a Python SDK for multi-provider LLM integration with intelligent routing and context management.

### Base Components

```
execution_platform/
├── router.py          # Main routing logic
├── spi.py            # Service Provider Interface
├── providers/        # Provider implementations
│   ├── claude_agent.py
│   ├── openai_adapter.py
│   └── gemini_adapter.py
└── exceptions.py     # Exception types
```

---

## Core API

### PersonaRouter

**Module**: `execution_platform.router`

#### Constructor

```python
PersonaRouter(policy_path: Optional[str] = None)
```

**Parameters:**
- `policy_path`: Path to persona policy YAML file (default: `docs/persona_policy.yaml`)

**Example:**
```python
from execution_platform.router import PersonaRouter

# Use default policy
router = PersonaRouter()

# Use custom policy
router = PersonaRouter(policy_path="/path/to/custom_policy.yaml")
```

#### Methods

##### select_provider()

```python
def select_provider(self, persona: str) -> str
```

**Description**: Select appropriate provider for given persona.

**Parameters:**
- `persona` (str): Persona name (e.g., "architect", "code_writer")

**Returns:**
- `str`: Provider name (e.g., "claude_agent", "openai")

**Raises:**
- `ValueError`: If persona not found in policy

**Example:**
```python
provider = router.select_provider("architect")
# Returns: "claude_agent"
```

##### get_client()

```python
def get_client(self, persona: str) -> LLMClient
```

**Description**: Get LLM client instance for persona.

**Parameters:**
- `persona` (str): Persona name

**Returns:**
- `LLMClient`: Client instance for provider

**Raises:**
- `ValueError`: If persona not found
- `ProviderError`: If provider initialization fails

**Example:**
```python
client = router.get_client("architect")
# Returns: ClaudeAgentClient instance
```

---

## Data Models

### Message

**Module**: `execution_platform.spi`

```python
@dataclass
class Message:
    role: str
    content: str
    name: Optional[str] = None
```

**Fields:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| role | str | Yes | Message role: "user", "assistant", or "system" |
| content | str | Yes | Message content text |
| name | str | No | Optional sender name |

**Example:**
```python
from execution_platform.spi import Message

msg = Message(
    role="user",
    content="Write a hello world function"
)
```

---

### ChatRequest

**Module**: `execution_platform.spi`

```python
@dataclass
class ChatRequest:
    messages: List[Message]
    max_tokens: Optional[int] = None
    temperature: Optional[float] = None
    top_p: Optional[float] = None
    stop: Optional[List[str]] = None
    model: Optional[str] = None
    system: Optional[str] = None
    tools: Optional[List[ToolDefinition]] = None
```

**Fields:**

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| messages | List[Message] | Yes | - | Conversation messages |
| max_tokens | int | No | Provider default | Maximum tokens to generate |
| temperature | float | No | 1.0 | Sampling temperature (0.0-2.0) |
| top_p | float | No | 1.0 | Nucleus sampling (0.0-1.0) |
| stop | List[str] | No | None | Stop sequences |
| model | str | No | Provider default | Model override |
| system | str | No | None | System prompt |
| tools | List[ToolDefinition] | No | None | Available tools |

**Example:**
```python
from execution_platform.spi import ChatRequest, Message

request = ChatRequest(
    messages=[
        Message(role="system", content="You are a helpful assistant"),
        Message(role="user", content="Hello")
    ],
    max_tokens=1000,
    temperature=0.7
)
```

---

### ChatChunk

**Module**: `execution_platform.spi`

```python
@dataclass
class ChatChunk:
    delta_text: Optional[str] = None
    finish_reason: Optional[str] = None
    usage: Optional[Usage] = None
    tool_call: Optional[ToolCall] = None
```

**Fields:**

| Field | Type | Description |
|-------|------|-------------|
| delta_text | str | Incremental text chunk |
| finish_reason | str | Completion reason: "stop", "length", "tool_calls", etc. |
| usage | Usage | Token usage statistics |
| tool_call | ToolCall | Tool invocation details |

**Example:**
```python
async for chunk in client.chat(request):
    if chunk.delta_text:
        print(chunk.delta_text, end="")
    if chunk.finish_reason:
        print(f"\nFinished: {chunk.finish_reason}")
    if chunk.usage:
        print(f"Tokens: {chunk.usage.total_tokens}")
```

---

### Usage

**Module**: `execution_platform.spi`

```python
@dataclass
class Usage:
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
```

**Fields:**

| Field | Type | Description |
|-------|------|-------------|
| prompt_tokens | int | Tokens in prompt |
| completion_tokens | int | Tokens in completion |
| total_tokens | int | Total tokens used |

---

### ToolDefinition

**Module**: `execution_platform.spi`

```python
@dataclass
class ToolDefinition:
    name: str
    description: str
    parameters: List[ToolParameter]
```

**Fields:**

| Field | Type | Description |
|-------|------|-------------|
| name | str | Tool name |
| description | str | Tool description |
| parameters | List[ToolParameter] | Tool parameters |

**Example:**
```python
from execution_platform.spi import ToolDefinition, ToolParameter

tool = ToolDefinition(
    name="get_weather",
    description="Get current weather for a location",
    parameters=[
        ToolParameter(
            name="location",
            type="string",
            description="City name",
            required=True
        ),
        ToolParameter(
            name="units",
            type="string",
            description="Temperature units",
            required=False,
            enum=["celsius", "fahrenheit"]
        )
    ]
)
```

---

### ToolParameter

**Module**: `execution_platform.spi`

```python
@dataclass
class ToolParameter:
    name: str
    type: str
    description: Optional[str] = None
    required: bool = False
    enum: Optional[List[str]] = None
```

**Fields:**

| Field | Type | Description |
|-------|------|-------------|
| name | str | Parameter name |
| type | str | Parameter type: "string", "number", "boolean", "object", "array" |
| description | str | Parameter description |
| required | bool | Whether parameter is required |
| enum | List[str] | Valid values (if applicable) |

---

## LLMClient Interface

**Module**: `execution_platform.spi`

```python
class LLMClient(ABC):
    @abstractmethod
    async def chat(self, req: ChatRequest) -> AsyncIterator[ChatChunk]:
        """Execute chat completion"""
        pass
```

### chat()

```python
async def chat(self, req: ChatRequest) -> AsyncIterator[ChatChunk]
```

**Description**: Execute chat completion with streaming.

**Parameters:**
- `req` (ChatRequest): Chat request configuration

**Returns:**
- `AsyncIterator[ChatChunk]`: Stream of response chunks

**Example:**
```python
request = ChatRequest(
    messages=[Message(role="user", content="Hello")],
    max_tokens=100
)

response = ""
async for chunk in client.chat(request):
    if chunk.delta_text:
        response += chunk.delta_text
```

---

## Exception Types

**Module**: `execution_platform.exceptions`

### ExecutionPlatformError

Base exception for all platform errors.

```python
class ExecutionPlatformError(Exception):
    """Base exception for execution platform"""
    pass
```

### RouterError

Errors related to routing logic.

```python
class RouterError(ExecutionPlatformError):
    """Router-related errors"""
    pass
```

**Common Cases:**
- Invalid persona
- Missing persona policy
- Configuration errors

### ProviderError

Errors from LLM providers.

```python
class ProviderError(ExecutionPlatformError):
    """Provider-related errors"""
    pass
```

**Common Cases:**
- Provider unavailable
- API key invalid
- Rate limit exceeded

### TimeoutError

Request timeout errors.

```python
class TimeoutError(ExecutionPlatformError):
    """Request timeout"""
    pass
```

**Common Cases:**
- Long-running requests
- Network issues

---

## Provider-Specific APIs

### ClaudeAgentClient

**Module**: `execution_platform.providers.claude_agent`

**Provider**: Claude Code SDK

**Configuration**: No API key required (uses local Claude CLI)

**Capabilities:**
- System prompts ✓
- Streaming ✓
- Tool calling ✗
- JSON mode ✗
- Vision ✗

**Example:**
```python
from execution_platform.providers.claude_agent import ClaudeAgentClient

client = ClaudeAgentClient()
request = ChatRequest(
    messages=[Message(role="user", content="Hello")],
    max_tokens=500
)

async for chunk in client.chat(request):
    if chunk.delta_text:
        print(chunk.delta_text, end="")
```

---

### OpenAIClient

**Module**: `execution_platform.providers.openai_adapter`

**Provider**: OpenAI API

**Configuration**: Requires `OPENAI_API_KEY` environment variable

**Capabilities:**
- System prompts ✓
- Streaming ✓
- Tool calling ✓
- JSON mode ✓
- Vision ✓
- Stop sequences ✓

**Example:**
```python
from execution_platform.providers.openai_adapter import OpenAIClient

client = OpenAIClient(model="gpt-4")
request = ChatRequest(
    messages=[Message(role="user", content="Hello")],
    max_tokens=500,
    temperature=0.7
)

async for chunk in client.chat(request):
    if chunk.delta_text:
        print(chunk.delta_text, end="")
```

---

### GeminiClient

**Module**: `execution_platform.providers.gemini_adapter`

**Provider**: Google Gemini API

**Configuration**: Requires `GEMINI_API_KEY` environment variable

**Capabilities:**
- System prompts ✓
- Streaming ✓
- Tool calling ✗
- JSON mode ✓
- Vision ✓

**Example:**
```python
from execution_platform.providers.gemini_adapter import GeminiClient

client = GeminiClient(model="gemini-pro")
request = ChatRequest(
    messages=[Message(role="user", content="Hello")],
    max_tokens=500
)

async for chunk in client.chat(request):
    if chunk.delta_text:
        print(chunk.delta_text, end="")
```

---

## Configuration

### Persona Policy Format

**File**: `docs/persona_policy.yaml`

```yaml
personas:
  persona_name:
    requires: [list_of_capabilities]
    provider_preferences: [ordered_list_of_providers]

providers:
  provider_name:
    capabilities: [list_of_capabilities]
```

**Example:**
```yaml
personas:
  architect:
    requires: [system_prompts]
    provider_preferences: [claude_agent, openai, gemini]
  
  code_writer_openai:
    requires: [system_prompts, tool_calling]
    provider_preferences: [openai]

providers:
  claude_agent:
    capabilities: [system_prompts, streaming]
  
  openai:
    capabilities: [system_prompts, tool_calling, json_mode, vision, streaming, stop_sequences, token_count]
  
  gemini:
    capabilities: [system_prompts, json_mode, vision, streaming]
```

---

## Usage Patterns

### Pattern 1: Simple Request

```python
from execution_platform.router import PersonaRouter
from execution_platform.spi import Message, ChatRequest

async def simple_request():
    router = PersonaRouter()
    client = router.get_client("code_writer")
    
    request = ChatRequest(
        messages=[Message(role="user", content="Write hello world")],
        max_tokens=500
    )
    
    response = ""
    async for chunk in client.chat(request):
        if chunk.delta_text:
            response += chunk.delta_text
    
    return response
```

### Pattern 2: Context Preservation

```python
async def conversation():
    router = PersonaRouter()
    client = router.get_client("architect")
    messages = []
    
    # Turn 1
    messages.append(Message(role="user", content="Design a REST API"))
    request = ChatRequest(messages=messages, max_tokens=500)
    
    response1 = ""
    async for chunk in client.chat(request):
        if chunk.delta_text:
            response1 += chunk.delta_text
    
    messages.append(Message(role="assistant", content=response1))
    
    # Turn 2 (with context)
    messages.append(Message(role="user", content="Add authentication"))
    request = ChatRequest(messages=messages, max_tokens=500)
    
    response2 = ""
    async for chunk in client.chat(request):
        if chunk.delta_text:
            response2 += chunk.delta_text
    
    return response2
```

### Pattern 3: Provider Switching

```python
async def multi_provider_workflow():
    router = PersonaRouter()
    
    # Phase 1: Claude (fast)
    claude_client = router.get_client("architect")
    req1 = ChatRequest(
        messages=[Message(role="user", content="Analyze requirements")],
        max_tokens=500
    )
    
    result1 = ""
    async for chunk in claude_client.chat(req1):
        if chunk.delta_text:
            result1 += chunk.delta_text
    
    # Phase 2: OpenAI (quality) with Claude's context
    openai_client = router.get_client("architect_openai")
    req2 = ChatRequest(
        messages=[
            Message(role="user", content="Analyze requirements"),
            Message(role="assistant", content=result1),
            Message(role="user", content="Design architecture")
        ],
        max_tokens=800
    )
    
    result2 = ""
    async for chunk in openai_client.chat(req2):
        if chunk.delta_text:
            result2 += chunk.delta_text
    
    return {"requirements": result1, "architecture": result2}
```

### Pattern 4: Error Handling

```python
from execution_platform.exceptions import (
    RouterError, ProviderError, TimeoutError
)

async def robust_request():
    router = PersonaRouter()
    
    try:
        client = router.get_client("architect")
        request = ChatRequest(
            messages=[Message(role="user", content="Hello")],
            max_tokens=500
        )
        
        response = ""
        async for chunk in client.chat(request):
            if chunk.delta_text:
                response += chunk.delta_text
        
        return response
    
    except RouterError as e:
        print(f"Routing error: {e}")
        return None
    
    except ProviderError as e:
        print(f"Provider error: {e}")
        # Try fallback
        client = router.get_client("code_writer_openai")
        # ... retry
    
    except TimeoutError as e:
        print(f"Timeout: {e}")
        # ... retry with longer timeout
```

---

## API Versioning

**Current Version**: 1.0.0

**Compatibility**: Semantic versioning (MAJOR.MINOR.PATCH)

- **MAJOR**: Breaking changes
- **MINOR**: New features (backward compatible)
- **PATCH**: Bug fixes

---

## Rate Limits

Provider-specific rate limits apply:

| Provider | Rate Limit | Notes |
|----------|------------|-------|
| Claude Agent | Unlimited | Local SDK |
| OpenAI | Per API key | See OpenAI docs |
| Gemini | Per API key | See Google docs |

---

## Testing

### Unit Tests

```bash
poetry run pytest tests/unit/
```

### Integration Tests

```bash
poetry run pytest tests/integration/
```

### Comprehensive Suite

```bash
poetry run python run_comprehensive_tests.py
```

---

## Support

- **Documentation**: `INTEGRATION_GUIDE.md`
- **Quick Reference**: `QUICK_REFERENCE.md`
- **API Spec**: This document
- **Examples**: `/examples/` directory

---

**Version**: 1.0.0  
**Last Updated**: 2025-10-11  
**Status**: ✅ Production Ready
