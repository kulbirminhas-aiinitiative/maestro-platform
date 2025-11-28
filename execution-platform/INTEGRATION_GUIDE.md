# Execution Platform - Integration Guide

**Version**: 1.0  
**Date**: 2025-10-11  
**Status**: Production Ready

---

## 📋 Table of Contents

1. [Overview](#overview)
2. [Quick Start](#quick-start)
3. [API Reference](#api-reference)
4. [Integration Patterns](#integration-patterns)
5. [Provider Configuration](#provider-configuration)
6. [Error Handling](#error-handling)
7. [Best Practices](#best-practices)
8. [Examples](#examples)
9. [Troubleshooting](#troubleshooting)

---

## Overview

The Execution Platform provides a unified interface for multi-provider LLM integration with intelligent routing, context management, and enterprise-grade quality assurance.

### Key Features

- **Multi-Provider Support**: Claude (Agent SDK), OpenAI, Gemini
- **Intelligent Routing**: Persona-based provider selection
- **Context Preservation**: Seamless context across providers
- **Streaming Responses**: Real-time token streaming
- **Tool Calling**: Function/tool invocation support
- **Quality Fabric Integration**: Enterprise testing and monitoring

### Architecture

```
┌─────────────────┐
│  Your Service   │
└────────┬────────┘
         │
         ▼
┌─────────────────────────────────┐
│   Execution Platform Router     │
│  (PersonaRouter + SPI Layer)    │
└────────┬────────────────────────┘
         │
    ┌────┴─────┬──────────┬─────────┐
    ▼          ▼          ▼         ▼
┌────────┐ ┌────────┐ ┌────────┐ ┌──────┐
│ Claude │ │ OpenAI │ │ Gemini │ │ etc. │
└────────┘ └────────┘ └────────┘ └──────┘
```

---

## Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/yourorg/maestro-platform.git
cd maestro-platform/execution-platform

# Install dependencies
poetry install

# Set up environment variables
cp .env.example .env
# Edit .env with your API keys
```

### Environment Variables

```bash
# Required
EP_OPENAI_API_KEY=sk-your-openai-key
EP_ANTHROPIC_API_KEY=sk-ant-your-anthropic-key  # Optional if using Claude SDK
EP_GEMINI_API_KEY=your-gemini-key               # Optional

# Optional
EP_DEFAULT_PROVIDER=claude_agent
EP_TIMEOUT=300
```

### Basic Usage

```python
from execution_platform.router import PersonaRouter
from execution_platform.spi import Message, ChatRequest

# Initialize router
router = PersonaRouter()

# Get a client for specific persona
client = router.get_client("architect")

# Create a request
request = ChatRequest(
    messages=[
        Message(role="user", content="Design a REST API for user management")
    ],
    max_tokens=1000,
    temperature=0.7
)

# Execute and stream response
async for chunk in client.chat(request):
    if chunk.delta_text:
        print(chunk.delta_text, end="", flush=True)
    if chunk.usage:
        print(f"\nTokens used: {chunk.usage.total_tokens}")
```

---

## API Reference

### Core Classes

#### PersonaRouter

Main entry point for provider routing.

```python
class PersonaRouter:
    """Routes requests to appropriate LLM providers based on persona"""
    
    def select_provider(self, persona: str) -> str:
        """
        Select provider for given persona
        
        Args:
            persona: Persona name (e.g., "architect", "code_writer")
            
        Returns:
            Provider name (e.g., "claude_agent", "openai")
            
        Raises:
            ValueError: If persona not found
        """
    
    def get_client(self, persona: str) -> LLMClient:
        """
        Get LLM client for persona
        
        Args:
            persona: Persona name
            
        Returns:
            LLMClient instance for the persona's provider
        """
```

#### ChatRequest

Request object for chat completions.

```python
@dataclass
class ChatRequest:
    """Request for chat completion"""
    messages: List[Message]           # Conversation messages
    max_tokens: Optional[int] = None  # Max tokens to generate
    temperature: Optional[float] = None  # Sampling temperature (0-2)
    top_p: Optional[float] = None     # Nucleus sampling
    stop: Optional[List[str]] = None  # Stop sequences
    model: Optional[str] = None       # Override default model
    system: Optional[str] = None      # System prompt
    tools: Optional[List[ToolDefinition]] = None  # Available tools
```

#### Message

Individual conversation message.

```python
@dataclass
class Message:
    """Single message in conversation"""
    role: str        # "user", "assistant", or "system"
    content: str     # Message content
    name: Optional[str] = None  # Optional name
```

#### ChatChunk

Streaming response chunk.

```python
@dataclass
class ChatChunk:
    """Chunk of streaming response"""
    delta_text: Optional[str] = None      # Incremental text
    finish_reason: Optional[str] = None   # "stop", "length", etc.
    usage: Optional[Usage] = None         # Token usage stats
```

### Available Personas

| Persona | Default Provider | Use Case |
|---------|-----------------|----------|
| `architect` | claude_agent | System design, architecture |
| `code_writer` | claude_agent | Code generation, implementation |
| `reviewer` | claude_agent | Code review, quality checks |
| `qa_engineer` | openai | Testing, quality assurance |
| `architect_openai` | openai | OpenAI-specific architecture |
| `code_writer_openai` | openai | OpenAI-specific coding |
| `reviewer_openai` | openai | OpenAI-specific review |

### Configuring Custom Personas

Edit `docs/persona_policy.yaml`:

```yaml
personas:
  my_custom_persona:
    requires: [system_prompts]
    provider_preferences: [claude_agent, openai, gemini]
```

---

## Integration Patterns

### Pattern 1: Simple Single Request

For one-off requests without context.

```python
from execution_platform.router import PersonaRouter
from execution_platform.spi import Message, ChatRequest

async def simple_request(prompt: str) -> str:
    """Execute simple request"""
    router = PersonaRouter()
    client = router.get_client("code_writer")
    
    request = ChatRequest(
        messages=[Message(role="user", content=prompt)],
        max_tokens=500
    )
    
    response = ""
    async for chunk in client.chat(request):
        if chunk.delta_text:
            response += chunk.delta_text
    
    return response
```

### Pattern 2: Multi-Turn Conversation

For maintaining context across multiple turns.

```python
async def conversation(persona: str):
    """Multi-turn conversation with context"""
    router = PersonaRouter()
    client = router.get_client(persona)
    messages = []
    
    while True:
        user_input = input("You: ")
        if user_input.lower() == "exit":
            break
        
        # Add user message
        messages.append(Message(role="user", content=user_input))
        
        # Get response
        request = ChatRequest(messages=messages, max_tokens=500)
        response = ""
        
        async for chunk in client.chat(request):
            if chunk.delta_text:
                response += chunk.delta_text
                print(chunk.delta_text, end="", flush=True)
        
        print()  # New line
        
        # Add assistant response to context
        messages.append(Message(role="assistant", content=response))
```

### Pattern 3: Provider Switching Workflow

For multi-phase workflows with different providers.

```python
async def multi_provider_workflow(requirement: str) -> dict:
    """Execute workflow across multiple providers"""
    router = PersonaRouter()
    results = {}
    
    # Phase 1: Requirements (Claude - fast)
    phase1_client = router.get_client("architect")
    req1 = ChatRequest(
        messages=[Message(role="user", content=f"Analyze: {requirement}")],
        max_tokens=500
    )
    
    results["requirements"] = ""
    async for chunk in phase1_client.chat(req1):
        if chunk.delta_text:
            results["requirements"] += chunk.delta_text
    
    # Phase 2: Architecture (OpenAI - quality)
    phase2_client = router.get_client("architect_openai")
    req2 = ChatRequest(
        messages=[
            Message(role="user", content=f"Analyze: {requirement}"),
            Message(role="assistant", content=results["requirements"]),
            Message(role="user", content="Design the architecture")
        ],
        max_tokens=800
    )
    
    results["architecture"] = ""
    async for chunk in phase2_client.chat(req2):
        if chunk.delta_text:
            results["architecture"] += chunk.delta_text
    
    # Phase 3: Review (Claude - fast)
    phase3_client = router.get_client("reviewer")
    req3 = ChatRequest(
        messages=[
            Message(role="user", content="Review this architecture"),
            Message(role="assistant", content=results["architecture"])
        ],
        max_tokens=500
    )
    
    results["review"] = ""
    async for chunk in phase3_client.chat(req3):
        if chunk.delta_text:
            results["review"] += chunk.delta_text
    
    return results
```

### Pattern 4: Parallel Execution

For executing multiple requests concurrently.

```python
import asyncio

async def parallel_execution(tasks: List[dict]) -> List[str]:
    """Execute multiple requests in parallel"""
    router = PersonaRouter()
    
    async def execute_task(task: dict) -> str:
        client = router.get_client(task["persona"])
        request = ChatRequest(
            messages=[Message(role="user", content=task["prompt"])],
            max_tokens=task.get("max_tokens", 500)
        )
        
        response = ""
        async for chunk in client.chat(request):
            if chunk.delta_text:
                response += chunk.delta_text
        
        return response
    
    # Execute all tasks concurrently
    responses = await asyncio.gather(
        *[execute_task(task) for task in tasks]
    )
    
    return responses

# Usage
tasks = [
    {"persona": "architect", "prompt": "Design API"},
    {"persona": "code_writer", "prompt": "Write handler"},
    {"persona": "qa_engineer", "prompt": "Create tests"}
]

results = await parallel_execution(tasks)
```

### Pattern 5: Tool Calling

For function/tool invocation.

```python
from execution_platform.spi import ToolDefinition, ToolParameter

async def tool_calling_example():
    """Execute request with tool definitions"""
    router = PersonaRouter()
    client = router.get_client("code_writer")
    
    # Define available tools
    tools = [
        ToolDefinition(
            name="get_weather",
            description="Get weather for a location",
            parameters=[
                ToolParameter(name="location", type="string", required=True),
                ToolParameter(name="units", type="string", required=False)
            ]
        )
    ]
    
    request = ChatRequest(
        messages=[Message(role="user", content="What's the weather in Paris?")],
        tools=tools,
        max_tokens=200
    )
    
    async for chunk in client.chat(request):
        if chunk.tool_call:
            # Handle tool call
            print(f"Tool called: {chunk.tool_call.name}")
            print(f"Arguments: {chunk.tool_call.arguments}")
        if chunk.delta_text:
            print(chunk.delta_text, end="")
```

---

## Provider Configuration

### Claude Configuration

Claude uses the local Claude Code SDK.

```yaml
# docs/persona_policy.yaml
personas:
  architect:
    requires: [system_prompts]
    provider_preferences: [claude_agent, openai]

providers:
  claude_agent:
    capabilities: [system_prompts, streaming]
```

**No API key required** - uses local CLI.

### OpenAI Configuration

OpenAI uses the official Python SDK.

```yaml
personas:
  architect_openai:
    requires: [system_prompts]
    provider_preferences: [openai]

providers:
  openai:
    capabilities: [system_prompts, tool_calling, json_mode, vision, streaming]
```

**Requires**: `OPENAI_API_KEY` environment variable.

### Gemini Configuration

Gemini support is available for future integration.

```yaml
personas:
  architect_gemini:
    requires: [system_prompts]
    provider_preferences: [gemini]

providers:
  gemini:
    capabilities: [system_prompts, json_mode, vision, streaming]
```

**Requires**: `GEMINI_API_KEY` environment variable.

---

## Error Handling

### Exception Types

```python
from execution_platform.exceptions import (
    ExecutionPlatformError,
    ProviderError,
    RouterError,
    TimeoutError
)

try:
    client = router.get_client("architect")
    response = await client.chat(request)
except RouterError as e:
    # Handle routing errors (invalid persona, etc.)
    print(f"Routing error: {e}")
except ProviderError as e:
    # Handle provider-specific errors
    print(f"Provider error: {e}")
except TimeoutError as e:
    # Handle timeout
    print(f"Request timeout: {e}")
except ExecutionPlatformError as e:
    # Handle general errors
    print(f"Platform error: {e}")
```

### Retry Logic

```python
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=10)
)
async def execute_with_retry(client, request):
    """Execute request with automatic retry"""
    response = ""
    async for chunk in client.chat(request):
        if chunk.delta_text:
            response += chunk.delta_text
    return response
```

### Fallback Providers

```python
async def execute_with_fallback(persona: str, request: ChatRequest) -> str:
    """Execute with fallback to alternative provider"""
    router = PersonaRouter()
    
    # Primary provider
    try:
        client = router.get_client(persona)
        response = ""
        async for chunk in client.chat(request):
            if chunk.delta_text:
                response += chunk.delta_text
        return response
    except ProviderError:
        # Fallback to OpenAI
        fallback_persona = f"{persona}_openai"
        client = router.get_client(fallback_persona)
        response = ""
        async for chunk in client.chat(request):
            if chunk.delta_text:
                response += chunk.delta_text
        return response
```

---

## Best Practices

### 1. Provider Selection Strategy

**Use Claude for**:
- Fast iterations
- Simple code generation
- Quick reviews
- Cost-sensitive workloads

**Use OpenAI for**:
- Complex reasoning
- High-quality outputs
- Production artifacts
- Critical reviews

**Use Mixed for**:
- Optimal performance/quality balance
- Multi-phase workflows
- Cost optimization

### 2. Context Management

```python
# Good: Maintain conversation context
messages = []
for turn in conversation:
    messages.append(Message(role="user", content=turn.user_message))
    # ... get response
    messages.append(Message(role="assistant", content=response))

# Good: Clear context between unrelated requests
messages = []  # Start fresh
```

### 3. Token Management

```python
# Good: Set reasonable limits
request = ChatRequest(
    messages=messages,
    max_tokens=1000  # Appropriate limit
)

# Better: Adjust based on task
if task_type == "summary":
    max_tokens = 500
elif task_type == "implementation":
    max_tokens = 2000
```

### 4. Error Handling

```python
# Good: Specific error handling
try:
    result = await execute_request(client, request)
except TimeoutError:
    # Retry with longer timeout
    result = await execute_request(client, request, timeout=600)
except ProviderError as e:
    # Log and fallback
    logger.error(f"Provider error: {e}")
    result = await execute_with_fallback(persona, request)
```

### 5. Performance Optimization

```python
# Good: Use concurrent execution when possible
tasks = [task1, task2, task3]
results = await asyncio.gather(*[execute(t) for t in tasks])

# Good: Stream results for better UX
async for chunk in client.chat(request):
    if chunk.delta_text:
        yield chunk.delta_text  # Stream to user immediately
```

---

## Examples

### Example 1: REST API Generation Service

```python
class APIGenerationService:
    """Service for generating REST API specifications"""
    
    def __init__(self):
        self.router = PersonaRouter()
    
    async def generate_api(self, requirement: str) -> dict:
        """Generate complete API specification"""
        
        # Phase 1: Requirements analysis (Claude - fast)
        architect = self.router.get_client("architect")
        req_analysis = await self._execute_phase(
            architect,
            f"Analyze API requirements: {requirement}"
        )
        
        # Phase 2: API design (OpenAI - quality)
        designer = self.router.get_client("architect_openai")
        api_design = await self._execute_phase(
            designer,
            f"Design REST API based on: {req_analysis}",
            context=[req_analysis]
        )
        
        # Phase 3: Review (Claude - fast)
        reviewer = self.router.get_client("reviewer")
        review = await self._execute_phase(
            reviewer,
            f"Review API design: {api_design}"
        )
        
        return {
            "requirements": req_analysis,
            "design": api_design,
            "review": review
        }
    
    async def _execute_phase(
        self, 
        client, 
        prompt: str, 
        context: List[str] = None
    ) -> str:
        """Execute a single phase"""
        messages = []
        if context:
            for ctx in context:
                messages.append(Message(role="assistant", content=ctx))
        
        messages.append(Message(role="user", content=prompt))
        
        request = ChatRequest(messages=messages, max_tokens=1500)
        response = ""
        
        async for chunk in client.chat(request):
            if chunk.delta_text:
                response += chunk.delta_text
        
        return response
```

### Example 2: Code Review Service

```python
class CodeReviewService:
    """Automated code review service"""
    
    def __init__(self):
        self.router = PersonaRouter()
    
    async def review_code(
        self, 
        code: str, 
        language: str = "python"
    ) -> dict:
        """Perform comprehensive code review"""
        
        # Use OpenAI for thorough review
        reviewer = self.router.get_client("reviewer_openai")
        
        request = ChatRequest(
            messages=[
                Message(
                    role="system",
                    content=f"You are an expert {language} code reviewer."
                ),
                Message(
                    role="user",
                    content=f"Review this {language} code:\n\n{code}"
                )
            ],
            max_tokens=2000,
            temperature=0.3  # Lower temperature for consistency
        )
        
        review_text = ""
        async for chunk in reviewer.chat(request):
            if chunk.delta_text:
                review_text += chunk.delta_text
        
        return {
            "review": review_text,
            "language": language,
            "reviewer": "openai"
        }
```

### Example 3: Multi-Provider Orchestrator

```python
class MultiProviderOrchestrator:
    """Orchestrate work across multiple providers"""
    
    def __init__(self):
        self.router = PersonaRouter()
    
    async def execute_workflow(self, phases: List[dict]) -> List[dict]:
        """
        Execute multi-phase workflow
        
        Args:
            phases: List of phase definitions
                [
                    {"persona": "architect", "prompt": "...", "provider": "claude"},
                    {"persona": "code_writer", "prompt": "...", "provider": "openai"},
                    ...
                ]
        
        Returns:
            List of phase results
        """
        results = []
        context = []
        
        for phase in phases:
            # Get client for this phase
            client = self.router.get_client(phase["persona"])
            
            # Build messages with context
            messages = []
            for prev_result in context:
                messages.append(
                    Message(role="assistant", content=prev_result["output"])
                )
            
            messages.append(Message(role="user", content=phase["prompt"]))
            
            # Execute phase
            request = ChatRequest(
                messages=messages,
                max_tokens=phase.get("max_tokens", 1000)
            )
            
            output = ""
            start_time = time.time()
            provider_used = self.router.select_provider(phase["persona"])
            
            async for chunk in client.chat(request):
                if chunk.delta_text:
                    output += chunk.delta_text
            
            duration = time.time() - start_time
            
            # Store result
            result = {
                "phase": phase.get("name", f"Phase {len(results)+1}"),
                "persona": phase["persona"],
                "provider": provider_used,
                "output": output,
                "duration_ms": duration * 1000
            }
            
            results.append(result)
            context.append(result)
        
        return results
```

---

## Troubleshooting

### Common Issues

#### Issue: "No provider satisfies requirements for persona"

**Cause**: Persona not defined in `persona_policy.yaml`

**Solution**:
```yaml
# Add to docs/persona_policy.yaml
personas:
  your_persona:
    requires: [system_prompts]
    provider_preferences: [claude_agent, openai]
```

#### Issue: "Module 'openai' not found"

**Cause**: OpenAI dependency not installed

**Solution**:
```bash
poetry install
# or
pip install openai
```

#### Issue: Claude SDK not responding

**Cause**: Claude CLI not installed or not in PATH

**Solution**:
```bash
# Install Claude CLI
npm install -g @anthropic-ai/claude-code

# Verify installation
claude --version
```

#### Issue: Context not preserved across providers

**Cause**: Messages not properly passed

**Solution**:
```python
# Ensure all previous messages are included
messages = [
    Message(role="user", content="First message"),
    Message(role="assistant", content=first_response),
    Message(role="user", content="Second message")
]
```

### Performance Issues

#### Slow Response Times

1. Check provider latency:
```python
import time
start = time.time()
response = await client.chat(request)
print(f"Duration: {time.time() - start}s")
```

2. Use faster provider (Claude) for time-sensitive tasks

3. Implement caching for repeated requests

#### High Token Usage

1. Reduce `max_tokens`:
```python
request = ChatRequest(messages=messages, max_tokens=500)  # Lower limit
```

2. Use more concise prompts

3. Clear context periodically:
```python
# Keep only last N messages
messages = messages[-10:]
```

---

## Quality Fabric Integration

### Setup

```python
from tests.quality_fabric_client import QualityFabricClient, TestResult

# Initialize client
qf_client = QualityFabricClient(project="your-service")

# Submit test results
await qf_client.submit_test_suite(test_suite)

# Check quality gates
gates = await qf_client.check_quality_gates(suite_id)
```

### Custom Quality Gates

Configure in Quality Fabric service:

```yaml
quality_gates:
  success_rate:
    threshold: 99.0
    operator: ">="
  
  average_duration:
    threshold: 5000
    operator: "<="
  
  error_rate:
    threshold: 1.0
    operator: "<="
```

---

## Support and Resources

### Documentation
- API Reference: `/docs/api/`
- Provider Documentation: `/docs/providers/`
- Test Results: `/test-results/`

### Example Code
- `/examples/` - Integration examples
- `/tests/` - Test implementations

### Configuration Files
- `docs/persona_policy.yaml` - Persona configuration
- `docs/capabilities.yaml` - Provider capabilities
- `.env` - Environment variables

### Contact
- Issues: GitHub Issues
- Questions: team@yourorg.com

---

**Last Updated**: 2025-10-11  
**Version**: 1.0  
**Status**: Production Ready ✅
