# Execution Platform - Quick Reference Card

**Version 1.0** | **Production Ready** ✅

---

## 🚀 Quick Start (30 seconds)

```python
from execution_platform.router import PersonaRouter
from execution_platform.spi import Message, ChatRequest

# 1. Initialize
router = PersonaRouter()

# 2. Get client
client = router.get_client("architect")

# 3. Execute
request = ChatRequest(
    messages=[Message(role="user", content="Your prompt here")],
    max_tokens=1000
)

# 4. Stream response
async for chunk in client.chat(request):
    if chunk.delta_text:
        print(chunk.delta_text, end="")
```

---

## 📊 Available Personas

| Persona | Provider | Speed | Use Case |
|---------|----------|-------|----------|
| `architect` | Claude | ⚡⚡⚡ | System design |
| `code_writer` | Claude | ⚡⚡⚡ | Code generation |
| `reviewer` | Claude | ⚡⚡⚡ | Code review |
| `qa_engineer` | OpenAI | ⚡⚡ | Testing strategy |
| `architect_openai` | OpenAI | ⚡⚡ | Architecture (quality) |
| `code_writer_openai` | OpenAI | ⚡⚡ | Code (quality) |
| `reviewer_openai` | OpenAI | ⚡⚡ | Review (quality) |

---

## 🎯 Common Patterns

### Pattern 1: Simple Request
```python
async def ask(prompt: str) -> str:
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

### Pattern 2: Multi-Turn Context
```python
messages = []
messages.append(Message(role="user", content="Question 1"))
# ... get response1
messages.append(Message(role="assistant", content=response1))
messages.append(Message(role="user", content="Question 2"))
# ... get response2 (has context from Question 1)
```

### Pattern 3: Provider Switching
```python
# Phase 1: Fast with Claude
claude_client = router.get_client("architect")
result1 = await execute(claude_client, prompt1)

# Phase 2: Quality with OpenAI  
openai_client = router.get_client("architect_openai")
result2 = await execute(openai_client, prompt2, context=result1)
```

### Pattern 4: Parallel Execution
```python
import asyncio

results = await asyncio.gather(
    execute_task(task1),
    execute_task(task2),
    execute_task(task3)
)
```

---

## ⚙️ Configuration

### Environment Variables
```bash
EP_OPENAI_API_KEY=sk-your-key
EP_ANTHROPIC_API_KEY=sk-ant-your-key  # Optional
EP_GEMINI_API_KEY=your-key            # Optional
```

### Persona Policy (`docs/persona_policy.yaml`)
```yaml
personas:
  my_persona:
    requires: [system_prompts]
    provider_preferences: [claude_agent, openai]
```

---

## 🔧 Request Options

```python
request = ChatRequest(
    messages=messages,          # Required
    max_tokens=1000,           # Optional (default: model default)
    temperature=0.7,           # Optional (0-2, default: 1.0)
    top_p=1.0,                 # Optional (0-1)
    stop=["END"],              # Optional stop sequences
    model="gpt-4",             # Optional model override
    system="You are...",       # Optional system prompt
    tools=[tool_def]           # Optional tool definitions
)
```

---

## 🎭 Provider Performance

| Config | Duration | Use When |
|--------|----------|----------|
| Full Claude | 12s | Fast iteration, development |
| Mixed (Claude+OpenAI) | 51s | Balanced quality/speed |
| Full OpenAI | 136s | Maximum quality, production |

**Recommendation**: Use Mixed for optimal balance (60% faster than full OpenAI)

---

## ❌ Error Handling

```python
from execution_platform.exceptions import (
    RouterError,
    ProviderError,
    TimeoutError
)

try:
    result = await execute(client, request)
except RouterError:
    # Invalid persona
    pass
except ProviderError:
    # Provider unavailable
    pass
except TimeoutError:
    # Request timeout
    pass
```

---

## 📝 Message Roles

| Role | Description | Example |
|------|-------------|---------|
| `system` | System instructions | "You are an expert..." |
| `user` | User input | "Write a function..." |
| `assistant` | AI response | "Here's the code..." |

---

## 🧪 Testing with Quality Fabric

```python
from tests.quality_fabric_client import QualityFabricClient

qf = QualityFabricClient(project="your-service")
await qf.submit_test_suite(test_suite)
gates = await qf.check_quality_gates(suite_id)
```

---

## 📊 Metrics

### Test Results (21 comprehensive tests)
```
✅ Provider Routing: 4/4 (100%)
✅ Context Passing: 3/3 (100%)
✅ Error Handling: 3/3 (100%)
✅ Performance: 3/3 (100%)
✅ Provider Switching: 3/3 (100%)
✅ Streaming: 3/3 (100%)
✅ Tool Calling: 1/1 (100%)
✅ Multi-Persona: 1/1 (100%)

Total: 21/21 (100%) ✅
```

---

## 🔍 Troubleshooting

| Issue | Solution |
|-------|----------|
| "No provider for persona" | Add to `persona_policy.yaml` |
| "Module 'openai' not found" | Run `poetry install` |
| Claude not responding | Install: `npm install -g @anthropic-ai/claude-code` |
| Context not preserved | Include previous messages in request |
| Slow responses | Use Claude for faster results |

---

## 📚 Documentation

- **Full Integration Guide**: `INTEGRATION_GUIDE.md`
- **Test Results**: `COMPREHENSIVE_TEST_RESULTS.md`
- **Workflow Analysis**: `COMPLETE_WORKFLOW_ANALYSIS.md`
- **API Reference**: See Integration Guide

---

## 🎯 Best Practices

1. **Provider Selection**: Claude for speed, OpenAI for quality
2. **Context**: Always include previous messages
3. **Tokens**: Set reasonable `max_tokens` limits
4. **Errors**: Handle specific exception types
5. **Performance**: Use `asyncio.gather()` for parallel tasks

---

## 📞 Support

- **Issues**: GitHub Issues
- **Docs**: `/docs/` directory
- **Examples**: `/examples/` directory
- **Tests**: `/tests/` directory

---

**Status**: ✅ Production Ready | **Version**: 1.0 | **Tests**: 21/21 Passed
