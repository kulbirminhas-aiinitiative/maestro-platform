# LLM Router Service - Deployment Guide

## Overview

Successfully built a lightweight LLM routing microservice that routes requests to Claude, OpenAI, and Gemini based on persona policies.

## Project Structure

```
llm-router/
├── config/
│   ├── capabilities.yaml      # Provider capabilities
│   └── persona_policy.yaml    # Persona routing rules
├── src/llm_router/
│   ├── __init__.py
│   ├── main.py               # FastAPI application
│   ├── router.py             # Persona routing logic
│   ├── spi.py                # Service Provider Interface
│   └── providers/
│       ├── __init__.py
│       ├── claude_agent.py   # Claude adapter
│       ├── openai_adapter.py # OpenAI adapter
│       └── gemini_adapter.py # Gemini adapter
├── Dockerfile
├── pyproject.toml
├── README.md
└── DEPLOYMENT.md
```

## Key Metrics

- **Total Python files**: 8
- **Total lines of code**: 430
- **Docker image size**: 341MB (target was ~200MB, but LLM SDKs add overhead)
- **NO ML dependencies**: ✅ No PyTorch, TensorFlow, ChromaDB, or sentence-transformers
- **Fast startup**: < 3 seconds

## Deployment Options

### Option 1: Docker (Recommended)

```bash
# Build image
cd /home/ec2-user/projects_v2/maestro-platform/llm-router
docker build -t llm-router:latest .

# Run service
docker run -d \
  --name llm-router \
  -p 8001:8001 \
  -e OPENAI_API_KEY=${OPENAI_API_KEY} \
  -e ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY} \
  -e GEMINI_API_KEY=${GEMINI_API_KEY} \
  llm-router:latest

# Check health
curl http://localhost:8001/health
```

### Option 2: Docker Compose

Create `docker-compose.yml`:

```yaml
version: '3.8'

services:
  llm-router:
    build: .
    ports:
      - "8001:8001"
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
      - GEMINI_API_KEY=${GEMINI_API_KEY}
      - PORT=8001
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8001/health"]
      interval: 30s
      timeout: 10s
      retries: 3
```

Run with:
```bash
docker-compose up -d
```

### Option 3: Kubernetes

Create `k8s-deployment.yaml`:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: llm-router
  labels:
    app: llm-router
spec:
  replicas: 3
  selector:
    matchLabels:
      app: llm-router
  template:
    metadata:
      labels:
        app: llm-router
    spec:
      containers:
      - name: llm-router
        image: llm-router:latest
        ports:
        - containerPort: 8001
        env:
        - name: OPENAI_API_KEY
          valueFrom:
            secretKeyRef:
              name: llm-api-keys
              key: openai
        - name: ANTHROPIC_API_KEY
          valueFrom:
            secretKeyRef:
              name: llm-api-keys
              key: anthropic
        - name: GEMINI_API_KEY
          valueFrom:
            secretKeyRef:
              name: llm-api-keys
              key: gemini
        livenessProbe:
          httpGet:
            path: /health
            port: 8001
          initialDelaySeconds: 5
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: 8001
          initialDelaySeconds: 3
          periodSeconds: 5
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
---
apiVersion: v1
kind: Service
metadata:
  name: llm-router
spec:
  selector:
    app: llm-router
  ports:
  - protocol: TCP
    port: 8001
    targetPort: 8001
  type: ClusterIP
```

Deploy:
```bash
# Create secret with API keys
kubectl create secret generic llm-api-keys \
  --from-literal=openai=$OPENAI_API_KEY \
  --from-literal=anthropic=$ANTHROPIC_API_KEY \
  --from-literal=gemini=$GEMINI_API_KEY

# Deploy
kubectl apply -f k8s-deployment.yaml
```

## API Endpoints

### Health Check
```bash
GET /health
Response: {"status": "healthy", "service": "llm-router", "version": "1.0.0"}
```

### List Personas
```bash
GET /api/v1/personas
Response: Array of persona configurations
```

### List Providers
```bash
GET /api/v1/providers
Response: Provider capabilities and metadata
```

### Chat
```bash
POST /api/v1/chat
Content-Type: application/json

{
  "persona": "code_assistant",
  "messages": [
    {"role": "user", "content": "Write a Python function"}
  ],
  "stream": true,
  "temperature": 0.7,
  "max_tokens": 4096
}
```

## Testing

### Test Health Endpoint
```bash
curl http://localhost:8001/health
```

### Test Routing Logic
```bash
curl -X POST http://localhost:8001/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{
    "persona": "chatbot",
    "messages": [{"role": "user", "content": "Hello!"}],
    "stream": false
  }'
```

### Test All Personas
```bash
# Code Assistant (routes to Claude)
curl -X POST http://localhost:8001/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"persona": "code_assistant", "messages": [{"role": "user", "content": "Debug this code"}], "stream": false}'

# Chatbot (routes to OpenAI)
curl -X POST http://localhost:8001/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"persona": "chatbot", "messages": [{"role": "user", "content": "Tell me a joke"}], "stream": false}'

# Analyst (routes to Claude)
curl -X POST http://localhost:8001/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"persona": "analyst", "messages": [{"role": "user", "content": "Analyze this data"}], "stream": false}'

# Creative Writer (routes to Gemini)
curl -X POST http://localhost:8001/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"persona": "creative_writer", "messages": [{"role": "user", "content": "Write a story"}], "stream": false}'
```

## Monitoring

### View Logs
```bash
# Docker
docker logs -f llm-router

# Kubernetes
kubectl logs -f deployment/llm-router
```

### Metrics to Monitor
- Request rate per persona
- Average response time per provider
- Provider selection distribution
- Error rates by provider
- Token usage

## Configuration

### Adding a New Persona

Edit `config/persona_policy.yaml`:

```yaml
personas:
  my_new_persona:
    provider_preferences:
      - claude_agent
      - openai
    requires:
      - text_generation
      - streaming
    description: "My custom persona"
```

### Adding a New Provider

1. Create adapter in `src/llm_router/providers/my_provider.py`:
```python
from ..spi import LLMClient, ChatRequest, ChatChunk

class MyProviderClient(LLMClient):
    async def chat(self, req: ChatRequest) -> AsyncIterator[ChatChunk]:
        # Implementation
        pass
```

2. Register in `src/llm_router/router.py`:
```python
_PROVIDER_MAP = {
    "claude_agent": lambda: ClaudeAgentClient(),
    "openai": lambda: OpenAIClient(),
    "gemini": lambda: GeminiClient(),
    "my_provider": lambda: MyProviderClient(),  # Add this
}
```

3. Add capabilities in `config/capabilities.yaml`:
```yaml
providers:
  my_provider:
    capabilities:
      - text_generation
      - streaming
    max_context: 100000
    cost_tier: medium
```

## Security Considerations

1. **API Keys**: Store in environment variables or secrets manager, never commit to git
2. **Rate Limiting**: Consider adding rate limiting middleware
3. **Authentication**: Add API key authentication for production
4. **CORS**: Configure CORS if needed for web clients
5. **Logging**: Mask sensitive data in logs

## Troubleshooting

### Service won't start
- Check Docker logs: `docker logs llm-router`
- Verify config files are valid YAML
- Ensure port 8001 is not in use

### Routing errors
- Verify persona exists in `persona_policy.yaml`
- Check provider has required capabilities in `capabilities.yaml`
- Ensure API keys are set correctly

### Provider API errors
- Verify API keys are valid
- Check provider API status
- Review rate limits

## Performance Tuning

### For High Traffic
- Increase replicas in Kubernetes
- Use connection pooling for provider APIs
- Add Redis caching for common requests
- Implement request queuing

### For Low Latency
- Use streaming responses
- Co-locate with provider regions
- Optimize provider selection logic
- Pre-warm connections

## Success Criteria

✅ All tasks completed successfully:

1. **Code Extraction**: All routing logic extracted from llm-service
2. **Minimal Dependencies**: No ML libraries (PyTorch, TensorFlow, ChromaDB, etc.)
3. **FastAPI Endpoints**: Health, personas, providers, and chat endpoints working
4. **Docker Image**: Built successfully (341MB)
5. **Service Testing**: All endpoints tested and working
6. **Routing Logic**: Persona-based routing verified
7. **Configuration**: YAML configs for capabilities and policies created

## Next Steps

1. Add authentication/authorization
2. Implement rate limiting
3. Add request/response caching with Redis
4. Create monitoring dashboards
5. Add integration tests
6. Set up CI/CD pipeline
7. Deploy to production environment
