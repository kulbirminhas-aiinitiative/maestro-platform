# MAESTRO Platform - Frontend Integration Guide

**Last Updated:** 2025-10-28
**Environments:** Development Server (localhost) + Demo Server (18.134.157.225)
**Gateway Port:** 8080

---

## Table of Contents

1. [Environment Overview](#environment-overview)
2. [Service Architecture Overview](#service-architecture-overview)
3. [Base URLs](#base-urls)
4. [API v1 Routes (Gateway Proxied)](#api-v1-routes-gateway-proxied)
5. [API v2 Routes (New Microservices)](#api-v2-routes-new-microservices)
6. [Direct Service Access](#direct-service-access)
7. [WebSocket Endpoints](#websocket-endpoints)
8. [Authentication](#authentication)
9. [Rate Limits](#rate-limits)
10. [CORS Configuration](#cors-configuration)
11. [Service Health Checks](#service-health-checks)
12. [Example Requests](#example-requests)

---

## Environment Overview

The MAESTRO platform runs in two environments with different port configurations:

| Environment | Purpose | Base URL | Microservices Ports |
|-------------|---------|----------|-------------------|
| **Development** | Local testing and development | `localhost` | 8401-8404 range |
| **Demo** | Shared demo server | `18.134.157.225` | 8100, 8301-8303 range |

**Port Ranges:**
- **Dev:** ChromaDB (8401), LLM Router (8402), RAG (8403), Multi-Agent (8404), Redis (6381)
- **Demo:** ChromaDB (8100), LLM Router (8301), RAG (8302), Multi-Agent (8303), Redis (6380)

---

## Service Architecture Overview

```
Frontend (Port 4200)
        │
        ▼
┌─────────────────────────────────┐
│  API Gateway (Port 8080)        │
│  - Rate Limiting                │
│  - CORS                         │
│  - Request Routing              │
└─────────────────────────────────┘
        │
        ├──── V1 API (Legacy Services)
        │     ├── Templates (9600)
        │     ├── Quality Fabric (8000)
        │     ├── LLM Service (8001) [LEGACY]
        │     ├── Accelerator BFF (4001)
        │     └── Guardian Engine (5000)
        │
        └──── V2 API (Microservices)
              ├── LLM Router (8301) [NEW]
              ├── RAG Service (8302) [NEW]
              └── Multi-Agent (8303) [NEW]
```

---

## Base URLs

### Development Environment

```
API Gateway:    http://localhost:8080
Frontend:       http://localhost:4200

Microservices (Direct Access - Internal Only):
  LLM Router:   http://localhost:8402
  RAG Service:  http://localhost:8403
  Multi-Agent:  http://localhost:8404
  ChromaDB:     http://localhost:8401
  Redis:        localhost:6381
```

### Demo Server Environment

```
API Gateway:    http://18.134.157.225:8080
Frontend:       http://18.134.157.225:4200

Microservices (Direct Access - Internal Only):
  LLM Router:   http://18.134.157.225:8301
  RAG Service:  http://18.134.157.225:8302
  Multi-Agent:  http://18.134.157.225:8303
  ChromaDB:     http://18.134.157.225:8100
  Redis:        18.134.157.225:6380
```

**IMPORTANT:** All frontend API calls should go through the Gateway (port 8080). Direct service access is for internal service-to-service communication only.

---

## API v1 Routes (Gateway Proxied)

All v1 routes are proxied through the gateway with rate limiting and CORS enabled.

### Template Service

| Endpoint | Method | Backend | Rate Limit | Cache TTL |
|----------|--------|---------|------------|-----------|
| `/api/v1/templates/*` | ALL | Template Service (9600) | 200/min | 5 min |

**Example:**
```bash
GET http://18.134.157.225:8080/api/v1/templates/list
GET http://18.134.157.225:8080/api/v1/templates/{template_id}
POST http://18.134.157.225:8080/api/v1/templates/create
```

### Quality Fabric Service

| Endpoint | Method | Backend | Rate Limit | Cache TTL |
|----------|--------|---------|------------|-----------|
| `/api/v1/quality/*` | ALL | Quality Fabric (8000) | 50/min | None |

**Example:**
```bash
POST http://18.134.157.225:8080/api/v1/quality/test
GET http://18.134.157.225:8080/api/v1/quality/results/{test_id}
```

### RAG Service (Knowledge Retrieval)

| Endpoint | Method | Backend | Rate Limit | Cache TTL |
|----------|--------|---------|------------|-----------|
| `/api/v1/rag/*` | ALL | RAG Service (9803) | 100/min | 1 min |

**Note:** Currently configured to port 9803 in gateway, but RAG microservice runs on 8302. Needs gateway update.

### Accelerator Mode (BFF)

| Endpoint | Method | Backend | Rate Limit | Cache TTL |
|----------|--------|---------|------------|-----------|
| `/api/v1/accelerator/*` | ALL | BFF Service (4001) | 100/min | None |
| `/api/deployment/*` | ALL | BFF Service (4001) | 100/min | None |
| `/api/sdlc/*` | ALL | BFF Service (4001) | 100/min | None |

**Example:**
```bash
POST http://18.134.157.225:8080/api/v1/accelerator/session/create
GET http://18.134.157.225:8080/api/sdlc/documents
```

### Guardian Mode (Full SDLC)

| Endpoint | Method | Backend | Rate Limit | Cache TTL |
|----------|--------|---------|------------|-----------|
| `/api/v1/guardian/*` | ALL | Guardian Engine (5000) | 20/min | None |

**Example:**
```bash
POST http://18.134.157.225:8080/api/v1/guardian/workflow/start
GET http://18.134.157.225:8080/api/v1/guardian/workflow/{workflow_id}/status
```

### DAG Workflow API

| Endpoint | Method | Backend | Rate Limit | Cache TTL |
|----------|--------|---------|------------|-----------|
| `/api/workflow/*` | ALL | Workflow Service (5001) | 50/min | None |

**Example:**
```bash
POST http://18.134.157.225:8080/api/workflow/execute
GET http://18.134.157.225:8080/api/workflow/{workflow_id}/status
```

---

## API v2 Routes (New Microservices)

**STATUS:** These routes need to be added to the gateway configuration. Services are deployed and running.

### LLM Router Service (NEW)

**Direct Port:** 8301
**Gateway Route:** `/api/v2/llm/*` → `http://maestro-llm-router:8301`

| Endpoint | Method | Description | Request Body | Response |
|----------|--------|-------------|--------------|----------|
| `/api/v1/chat` | POST | Send chat message | `{persona, messages, model, stream}` | JSON or Stream |
| `/api/v1/personas` | GET | List available personas | None | `[{name, description, provider}]` |
| `/api/v1/providers` | GET | List LLM providers | None | `{providers: [...]}` |
| `/health` | GET | Health check | None | `{status, service, version}` |

**Example:**
```bash
# Through Gateway (when configured)
POST http://18.134.157.225:8080/api/v2/llm/chat

# Direct Access (internal only)
POST http://18.134.157.225:8301/api/v1/chat
```

**Chat Request Example:**
```json
{
  "persona": "solution_architect",
  "messages": [
    {"role": "user", "content": "Design a microservices architecture"}
  ],
  "model": "claude-3-haiku-20240307",
  "stream": false
}
```

**Note:** Only `claude-3-haiku-20240307` is currently available with the configured API key. Sonnet and Opus models require API key upgrade.

### RAG Service (NEW)

**Direct Port:** 8302
**Gateway Route:** `/api/v2/rag/*` → `http://maestro-rag-service:8302`

| Endpoint | Method | Description | Request Body | Response |
|----------|--------|-------------|--------------|----------|
| `/api/v1/ingest` | POST | Ingest documents | `{collection, documents}` | `{status, document_ids}` |
| `/api/v1/search` | POST | Semantic search | `{collection, query, top_k}` | `{results: [...]}` |
| `/api/v1/collections` | GET | List collections | None | `{collections: [...]}` |
| `/api/v1/collections/{name}` | DELETE | Delete collection | None | `{status}` |
| `/api/v1/context/{persona}/{session_id}` | GET | Get conversation context | None | `{conversation_history, team_context}` |
| `/api/v1/interactions/store` | POST | Store interaction | `{persona, session_id, content}` | `{status, session_id}` |
| `/api/v1/personas/{persona}/query` | POST | Query persona knowledge | `{query, top_k}` | `{results: [...]}` |
| `/health` | GET | Health check | None | `{status, chromadb_connected}` |

**Example:**
```bash
# Through Gateway (when configured)
POST http://18.134.157.225:8080/api/v2/rag/ingest

# Direct Access (internal only)
POST http://18.134.157.225:8302/api/v1/ingest
```

**Ingest Request Example:**
```json
{
  "collection_name": "requirements",
  "document_id": "doc1",
  "content": "The system shall support 1000 concurrent users",
  "metadata": {"type": "functional", "priority": "high"}
}
```

**Note:** RAG Service accepts single document per request, not arrays.

**Search Request Example:**
```json
{
  "collection_name": "requirements",
  "query": "What are the performance requirements?",
  "top_k": 5
}
```

### Multi-Agent Service (NEW)

**Direct Port:** 8303
**Gateway Route:** `/api/v2/teams/*` → `http://maestro-multi-agent:8303`

| Endpoint | Method | Description | Status |
|----------|--------|-------------|--------|
| `/api/v2/teams` | POST | Create agent team | ✅ Implemented |
| `/api/v2/teams` | GET | List all teams | ✅ Implemented |
| `/api/v2/teams/{id}` | GET | Get team details | ✅ Implemented |
| `/api/v2/teams/{id}` | DELETE | Delete team | ✅ Implemented |
| `/api/v2/teams/{id}/members` | GET | Get team members | ✅ Implemented |
| `/api/v2/chat/teams/{id}/sessions` | POST | Create chat session | ✅ Implemented |
| `/api/v2/chat/sessions/{id}` | GET | Get session details | ✅ Implemented |
| `/api/v2/chat/sessions/{id}/message` | POST | Send message to team | ✅ Implemented |
| `/api/v2/chat/sessions/{id}/messages` | GET | Get all messages | ✅ Implemented |
| `/api/v2/chat/sessions/{id}` | DELETE | Delete session | ✅ Implemented |
| `/health` | GET | Health check | ✅ Implemented |

**Available Personas:** `code_assistant`, `chatbot`, `analyst`, `creative_writer`, `solution_architect`, `code_writer`, `requirement_analyst`, `architect`

---

## Direct Service Access

**IMPORTANT:** These are internal ports. Frontend should NOT call these directly. Use Gateway (port 8080) instead.

### Port Mapping by Environment

| Service | Internal Port | Dev External Port | Demo External Port | Container Name | Status |
|---------|---------------|-------------------|-------------------|----------------|--------|
| Gateway | 8080 | 8080 | 8080 | maestro-gateway-* | Running |
| Templates | 9600 | 9600 | 9600 | maestro-template-service-* | Running |
| Quality Fabric | 8000 | 8000 | 8000 | maestro-quality-fabric-* | Running |
| LLM Service (Legacy) | 8001 | 8001 | 8001 | maestro-llm-service-* | Running |
| **LLM Router (NEW)** | 8001 | **8402** | **8301** | maestro-llm-router | Running |
| **RAG Service (NEW)** | 8002 | **8403** | **8302** | maestro-rag-service | Running |
| **Multi-Agent (NEW)** | 8003 | **8404** | **8303** | maestro-multi-agent | Running |
| ChromaDB | 8000 | **8401** | 8100 | maestro-chromadb | Running |
| Redis | 6379 | **6381** | 6380 | maestro-redis-* | Running |

**Note:** Microservices use different external ports in dev (8401-8404) to avoid conflicts with legacy services.

---

## WebSocket Endpoints

WebSocket connections are proxied through the gateway for real-time updates.

### Guardian Mode WebSocket

```
ws://18.134.157.225:8080/ws/guardian/{session_id}
```

**Rate Limit:** 10/minute
**Auth Required:** No
**Use Case:** Real-time workflow updates

### Accelerator Mode WebSocket

```
ws://18.134.157.225:8080/ws/accelerator/{session_id}
```

**Rate Limit:** 10/minute
**Auth Required:** No
**Use Case:** Real-time prototyping feedback

### Workflow WebSocket

```
ws://18.134.157.225:8080/ws/workflow/{workflow_id}
```

**Rate Limit:** 10/minute
**Auth Required:** **YES** (JWT required)
**Use Case:** Real-time workflow execution updates

---

## Authentication

### Current Configuration

- **Mode:** Permissive (authentication optional)
- **JWT Secret:** Configured via `JWT_SECRET` environment variable
- **Protected Paths:** Workflow WebSocket (`/ws/workflow/*`)

### JWT Token Format

```javascript
{
  "Authorization": "Bearer <jwt_token>"
}
```

### Future Protected Endpoints

Currently being rolled out gradually. Most endpoints are publicly accessible for development.

---

## Rate Limits

| Route Pattern | Rate Limit | Notes |
|---------------|------------|-------|
| `/api/v1/templates/*` | 200/minute | High limit for read-heavy operations |
| `/api/v1/accelerator/*` | 100/minute | Interactive sessions |
| `/api/v1/rag/*` | 100/minute | Knowledge retrieval |
| `/api/v1/quality/*` | 50/minute | Testing operations |
| `/api/v1/guardian/*` | 20/minute | Long-running workflows |
| `/api/workflow/*` | 50/minute | Workflow orchestration |
| `/ws/*` | 10/minute | WebSocket connections |
| **Default** | 60/minute | Applied to routes without explicit limit |

**Rate Limit Headers:**
```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1698765432
```

---

## CORS Configuration

### Allowed Origins

- `http://localhost:4200` (Frontend dev server)
- `http://localhost:3000` (Alternative frontend port)
- Any host on port 4200: `https?://.*:4200`
- Configurable via `FRONTEND_URL` environment variable

### Allowed Methods

```
GET, POST, PUT, DELETE, PATCH, OPTIONS, HEAD
```

### Allowed Headers

```
All headers (*) are allowed
```

### Credentials

```
allow_credentials: true
```

---

## Service Health Checks

All services expose health check endpoints. Use these to verify service availability.

### Health Check URLs - Development

```bash
# Gateway
GET http://localhost:8080/health

# LLM Router (NEW)
GET http://localhost:8402/health

# RAG Service (NEW)
GET http://localhost:8403/health

# Multi-Agent (NEW)
GET http://localhost:8404/health

# ChromaDB
GET http://localhost:8401/api/v2/heartbeat

# Templates
GET http://localhost:9600/health

# Quality Fabric
GET http://localhost:8000/health

# LLM Service (Legacy)
GET http://localhost:8001/health
```

### Health Check URLs - Demo Server

```bash
# Gateway
GET http://18.134.157.225:8080/health

# LLM Router (NEW)
GET http://18.134.157.225:8301/health

# RAG Service (NEW)
GET http://18.134.157.225:8302/health

# Multi-Agent (NEW)
GET http://18.134.157.225:8303/health

# ChromaDB
GET http://18.134.157.225:8100/api/v2/heartbeat

# Templates
GET http://18.134.157.225:9600/health

# Quality Fabric
GET http://18.134.157.225:8000/health

# LLM Service (Legacy)
GET http://18.134.157.225:8001/health
```

### Health Response Format

```json
{
  "status": "healthy",
  "service": "llm-router",
  "version": "1.0.0",
  "timestamp": "2025-10-27T20:25:33Z"
}
```

**RAG Service includes ChromaDB status:**
```json
{
  "status": "healthy",
  "service": "rag-service",
  "version": "1.0.0",
  "chromadb_connected": true,
  "timestamp": "2025-10-27T20:25:33Z"
}
```

---

## Example Requests

**Note:** Examples below show Demo server URLs. For Development, replace `18.134.157.225:8301` with `localhost:8402`, `8302` with `8403`, and `8303` with `8404`.

### 1. List Available Personas (LLM Router)

**Development:**
```bash
curl http://localhost:8402/api/v1/personas
```

**Demo Server:**
```bash
curl http://18.134.157.225:8301/api/v1/personas
```

**Response:**
```json
[
  {
    "name": "code_assistant",
    "description": "AI coding assistant with code understanding",
    "provider_preferences": ["claude_agent", "openai", "gemini"]
  },
  {
    "name": "chatbot",
    "description": "General purpose conversational AI",
    "provider_preferences": ["openai", "gemini", "claude_agent"]
  },
  {
    "name": "analyst",
    "description": "Data and business analyst persona",
    "provider_preferences": ["claude_agent", "openai"]
  },
  {
    "name": "creative_writer",
    "description": "Creative content generation",
    "provider_preferences": ["gemini", "claude_agent", "openai"]
  },
  {
    "name": "solution_architect",
    "description": "Solution architecture design and technical planning",
    "provider_preferences": ["claude_agent", "openai", "gemini"]
  },
  {
    "name": "code_writer",
    "description": "Code generation and implementation specialist",
    "provider_preferences": ["claude_agent", "openai", "gemini"]
  },
  {
    "name": "requirement_analyst",
    "description": "Requirements gathering and analysis expert",
    "provider_preferences": ["claude_agent", "openai"]
  },
  {
    "name": "architect",
    "description": "System and solution architect for technical design",
    "provider_preferences": ["claude_agent", "openai", "gemini"]
  }
]
```

### 2. Send Chat Message (LLM Router)

**Development:**
```bash
curl -X POST http://localhost:8402/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{
    "persona": "requirement_analyst",
    "messages": [
      {"role": "user", "content": "Write user story for login feature"}
    ],
    "model": "claude-3-haiku-20240307",
    "stream": false
  }'
```

**Demo Server:**
```bash
curl -X POST http://18.134.157.225:8301/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{
    "persona": "requirement_analyst",
    "messages": [
      {"role": "user", "content": "Write user story for login feature"}
    ],
    "model": "claude-3-haiku-20240307",
    "stream": false
  }'
```

**Response:**
```json
{
  "content": "As a user, I want to log in to the system...",
  "response": "As a user, I want to log in to the system...",
  "model": "claude-3-haiku-20240307",
  "usage": {
    "input_tokens": 45,
    "output_tokens": 120
  }
}
```

**Note:** Response includes both `content` and `response` fields for backward compatibility.

### 3. Ingest Document (RAG Service)

**Development:**
```bash
curl -X POST http://localhost:8403/api/v1/ingest \
  -H "Content-Type: application/json" \
  -d '{
    "collection_name": "requirements",
    "document_id": "req-001",
    "content": "The system shall support OAuth 2.0 authentication",
    "metadata": {"type": "security", "priority": "high"}
  }'
```

**Demo Server:**
```bash
curl -X POST http://18.134.157.225:8302/api/v1/ingest \
  -H "Content-Type: application/json" \
  -d '{
    "collection_name": "requirements",
    "document_id": "req-001",
    "content": "The system shall support OAuth 2.0 authentication",
    "metadata": {"type": "security", "priority": "high"}
  }'
```

**Response:**
```json
{
  "document_id": "req-001",
  "collection_name": "requirements",
  "status": "indexed",
  "indexed_at": "2025-10-28T12:00:00Z"
}
```

### 4. Search Documents (RAG Service)

```bash
curl -X POST http://18.134.157.225:8302/api/v1/search \
  -H "Content-Type: application/json" \
  -d '{
    "collection_name": "requirements",
    "query": "authentication requirements",
    "top_k": 3
  }'
```

**Response:**
```json
{
  "results": [
    {
      "id": "req-001",
      "content": "The system shall support OAuth 2.0 authentication",
      "metadata": {"type": "security", "priority": "high"},
      "score": 0.92
    }
  ],
  "query": "authentication requirements",
  "count": 1
}
```

### 5. List Templates (Via Gateway)

```bash
curl http://18.134.157.225:8080/api/v1/templates/list
```

### 6. Create Workflow (Guardian Mode)

```bash
curl -X POST http://18.134.157.225:8080/api/v1/guardian/workflow/start \
  -H "Content-Type: application/json" \
  -d '{
    "project_name": "ecommerce-platform",
    "sdlc_phases": ["requirements", "design", "implementation"]
  }'
```

---

## Migration Notes

### From Monolithic LLM Service to Microservices

**Old (Legacy):**
```
POST http://18.134.157.225:8001/api/v1/chat
```

**New (Microservices):**
```
POST http://18.134.157.225:8301/api/v1/chat
```

**Migration Timeline:**
1. **Phase 1** (Current): Both services running (ports 8001 and 8301)
2. **Phase 2** (Upcoming): Gateway routes updated to proxy to microservices
3. **Phase 3** (Future): Legacy service deprecated

---

## Gateway Configuration Updates Needed

To enable v2 API access through the gateway, add these routes to `/home/ec2-user/projects_v2/maestro-platform/gateway-service/config/gateway_routes.yaml`:

```yaml
# LLM Router Service (Microservices)
- path: /api/v2/llm/*
  backend: ${LLM_ROUTER_URL:http://maestro-llm-router:8301}
  rate_limit: 100/minute
  requires_auth: false
  cache_ttl: 0

# RAG Service (Microservices) - Update existing route
- path: /api/v1/rag/*
  backend: ${RAG_SERVICE_URL:http://maestro-rag-service:8302}
  rate_limit: 100/minute
  requires_auth: false
  cache_ttl: 60

# Multi-Agent Service (Microservices)
- path: /api/v2/teams/*
  backend: ${MULTI_AGENT_URL:http://maestro-multi-agent:8303}
  rate_limit: 50/minute
  requires_auth: false
  cache_ttl: 0

- path: /api/v2/chat/*
  backend: ${MULTI_AGENT_URL:http://maestro-multi-agent:8303}
  rate_limit: 50/minute
  requires_auth: false
  cache_ttl: 0

- path: /api/v2/personas
  backend: ${MULTI_AGENT_URL:http://maestro-multi-agent:8303}
  rate_limit: 100/minute
  requires_auth: false
  cache_ttl: 300
```

---

## API Key Configuration

### Setting Up API Keys for Development

The LLM Router service requires API keys to make calls to LLM providers (OpenAI, Anthropic, Google).

1. **Create .env file** from the template:
   ```bash
   cd ~/projects_v2/maestro-platform
   cp .env.example .env
   ```

2. **Edit .env file** and add your actual API keys:
   ```bash
   nano .env
   ```

3. **Restart services** to pick up the new API keys:
   ```bash
   cd ~/projects_v2/maestro-platform
   docker-compose -f docker-compose.microservices.yml down
   docker-compose -f docker-compose.microservices.yml up -d
   ```

4. **Verify services are running** with API keys:
   ```bash
   docker logs maestro-llm-router | grep -i "api_key"
   ```

**Note:** API keys are optional for testing infrastructure (health checks, service discovery), but required for actual LLM chat completions.

### Demo Server API Keys

Demo server API keys are managed separately. Contact the platform administrator to update demo server API keys.

---

## Support & Contact

For questions about this integration guide:
- Check service health endpoints
- Review gateway logs: `docker logs maestro-gateway-demo`
- Review service logs: `docker logs <service-container-name>`

**Service Status Dashboard:**
```bash
docker ps --filter 'name=maestro-' --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'
```

---

*Generated: 2025-10-28*
*Version: 2.0.0*
*Environments: Development + Demo Server*
