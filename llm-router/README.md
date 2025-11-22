# LLM Router Service

Lightweight microservice for routing LLM requests to different providers (Claude, OpenAI, Gemini) based on persona policies.

## Features

- **Persona-based routing**: Route requests based on predefined personas (code_assistant, chatbot, analyst, creative_writer)
- **Multi-provider support**: Claude, OpenAI, Gemini
- **Capability matching**: Automatically select provider based on required capabilities
- **Streaming support**: Real-time streaming responses
- **Minimal dependencies**: NO ML libraries, NO heavy frameworks
- **Fast startup**: Docker image ~200MB

## API Endpoints

### Health Check
```bash
GET /health
```

### List Personas
```bash
GET /api/v1/personas
```

### List Providers
```bash
GET /api/v1/providers
```

### Chat
```bash
POST /api/v1/chat
Content-Type: application/json

{
  "persona": "code_assistant",
  "messages": [
    {"role": "user", "content": "Hello!"}
  ],
  "stream": true,
  "temperature": 0.7,
  "max_tokens": 4096
}
```

## Quick Start

### Using Docker

```bash
# Build image
docker build -t llm-router:latest .

# Run service
docker run -p 8001:8001 \
  -e OPENAI_API_KEY=your_key \
  -e ANTHROPIC_API_KEY=your_key \
  -e GEMINI_API_KEY=your_key \
  llm-router:latest
```

### Local Development

```bash
# Install dependencies
poetry install

# Run service
poetry run python -m llm_router.main
```

## Configuration

### Personas
Defined in `config/persona_policy.yaml`:
- `code_assistant`: AI coding assistant
- `chatbot`: General conversational AI
- `analyst`: Data/business analyst
- `creative_writer`: Creative content generation

### Capabilities
Defined in `config/capabilities.yaml`:
- Provider capabilities (streaming, tool_calling, etc.)
- Context window sizes
- Cost tiers

## Environment Variables

- `PORT`: Service port (default: 8001)
- `OPENAI_API_KEY`: OpenAI API key
- `ANTHROPIC_API_KEY`: Anthropic API key
- `GEMINI_API_KEY`: Google Gemini API key

## Architecture

```
llm-router/
├── src/llm_router/
│   ├── main.py              # FastAPI application
│   ├── router.py            # Persona routing logic
│   ├── spi.py               # Service Provider Interface
│   └── providers/
│       ├── claude_agent.py  # Claude adapter
│       ├── openai_adapter.py # OpenAI adapter
│       └── gemini_adapter.py # Gemini adapter
├── config/
│   ├── capabilities.yaml    # Provider capabilities
│   └── persona_policy.yaml  # Persona routing rules
└── Dockerfile
```

## License

MIT
