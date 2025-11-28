# Discussion Orchestrator Service

A FastAPI-based service for orchestrating multi-agent discussions with human participants. This service manages shared context, agent coordination, and real-time communication using Redis for state management and WebSockets for live updates.

## Overview

The Discussion Orchestrator enables collaborative discussions between AI agents and human participants. It provides:

- **Multi-Agent Support**: Coordinate multiple AI agents with different personas and capabilities
- **Human Participation**: Include human participants in discussions with configurable roles and permissions
- **Real-Time Updates**: WebSocket streaming for live discussion events
- **Shared Context**: Redis-backed state management for distributed discussion state
- **Flexible Protocols**: Support for various discussion protocols (round-robin, free-form, moderated, consensus)
- **Integration Ready**: Designed to integrate with the Execution Platform for agent execution

## Architecture

```
┌─────────────────────────────────────────────────┐
│         Discussion Orchestrator Service          │
├─────────────────────────────────────────────────┤
│  FastAPI Application                            │
│  ├─ REST API Endpoints                          │
│  ├─ WebSocket Streaming                         │
│  └─ CORS Middleware                             │
├─────────────────────────────────────────────────┤
│  Core Components                                │
│  ├─ SharedContext (Redis State Management)     │
│  ├─ ConnectionManager (WebSocket Connections)  │
│  └─ Pydantic Models (Data Validation)          │
├─────────────────────────────────────────────────┤
│  External Dependencies                          │
│  ├─ Redis (State & Message Storage)            │
│  └─ Execution Platform (Agent Execution)       │
└─────────────────────────────────────────────────┘
```

## Installation

### Prerequisites

- Python 3.9 or higher
- Redis 5.0 or higher
- pip package manager

### Setup

1. **Clone and navigate to the directory:**

```bash
cd /home/ec2-user/projects/maestro-platform/discussion-orchestrator
```

2. **Create and activate a virtual environment:**

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies:**

```bash
pip install -r requirements.txt
```

4. **Configure environment variables:**

```bash
cp .env.example .env
# Edit .env with your configuration
```

### Environment Configuration

Edit `.env` file with your settings:

```env
# Redis Configuration
REDIS_URL=redis://localhost:6379
REDIS_DB=0
REDIS_MAX_CONNECTIONS=10

# Service Configuration
SERVICE_PORT=5000
LOG_LEVEL=INFO

# CORS Configuration
CORS_ORIGINS=http://localhost:4300,http://localhost:3000

# Integration
EXECUTION_PLATFORM_URL=http://localhost:8000
```

## Running the Service

### Development Mode

```bash
# With hot reload
python -m uvicorn src.main:app --reload --host 0.0.0.0 --port 5000

# Or using the main module directly
python -m src.main
```

### Production Mode

```bash
uvicorn src.main:app --host 0.0.0.0 --port 5000 --workers 4
```

### Using Docker (Future)

```bash
docker build -t discussion-orchestrator .
docker run -p 5000:5000 --env-file .env discussion-orchestrator
```

## API Documentation

Once the service is running, access the interactive API documentation:

- **Swagger UI**: http://localhost:5000/docs
- **ReDoc**: http://localhost:5000/redoc

### Core Endpoints

#### Health Check

```http
GET /health
```

Returns service health status and dependency information.

#### Create Discussion

```http
POST /v1/discussions
Content-Type: application/json

{
  "topic": "Design API for user authentication",
  "agents": [
    {
      "persona": "Security Expert",
      "provider": "openai",
      "model": "gpt-4",
      "system_prompt": "You are an expert in security best practices..."
    },
    {
      "persona": "Backend Developer",
      "provider": "openai",
      "model": "gpt-4"
    }
  ],
  "humans": [
    {
      "user_id": "user_123",
      "name": "John Doe",
      "role": "Product Manager",
      "permissions": ["read", "write", "moderate"]
    }
  ],
  "protocol": "moderated",
  "max_rounds": 10
}
```

Returns the created discussion session with ID and participant details.

#### Get Discussion Details

```http
GET /v1/discussions/{discussion_id}
```

Returns full discussion session including participants and metadata.

#### Get Message History

```http
GET /v1/discussions/{discussion_id}/messages?limit=50&offset=0
```

Returns paginated message history for the discussion.

#### Send Message

```http
POST /v1/discussions/{discussion_id}/messages
Content-Type: application/json

{
  "participant_id": "agent_abc123",
  "content": "I recommend using JWT tokens with refresh token rotation...",
  "message_type": "text"
}
```

Sends a message to the discussion and broadcasts it to WebSocket clients.

#### WebSocket Stream

```
WebSocket: ws://localhost:5000/v1/discussions/{discussion_id}/stream
```

Connect to receive real-time discussion updates:

```javascript
const ws = new WebSocket('ws://localhost:5000/v1/discussions/disc_abc123/stream');

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);

  if (data.type === 'init') {
    // Initial state with session and message history
    console.log('Session:', data.data.session);
    console.log('Messages:', data.data.messages);
  } else if (data.type === 'message') {
    // New message received
    console.log('New message:', data.data);
  }
};

// Send ping to keep connection alive
setInterval(() => {
  ws.send(JSON.stringify({ type: 'ping' }));
}, 30000);
```

#### List Active Discussions

```http
GET /v1/discussions
```

Returns array of active discussion IDs.

#### Delete Discussion

```http
DELETE /v1/discussions/{discussion_id}
```

Deletes the discussion session and all associated data.

## Data Models

### Discussion Session

```python
{
  "id": "disc_abc123",
  "topic": "Design API for user authentication",
  "protocol": "moderated",
  "status": "active",
  "participants": [...],
  "messages": [...],
  "current_round": 3,
  "max_rounds": 10,
  "created_at": "2025-01-15T10:00:00Z",
  "updated_at": "2025-01-15T10:15:00Z"
}
```

### Message

```python
{
  "message_id": "msg_xyz789",
  "participant_id": "agent_abc123",
  "participant_name": "Security Expert",
  "participant_type": "agent",
  "content": "Message content here...",
  "timestamp": "2025-01-15T10:15:00Z",
  "message_type": "text",
  "metadata": {}
}
```

### Agent Configuration

```python
{
  "agent_id": "agent_abc123",
  "persona": "Security Expert",
  "provider": "openai",
  "model": "gpt-4",
  "system_prompt": "Custom system prompt...",
  "temperature": 0.7
}
```

## Integration with Execution Platform

The Discussion Orchestrator is designed to work with the Execution Platform service for agent execution:

1. **Agent Creation**: Agent configurations are passed to the Execution Platform to create agent instances
2. **Message Routing**: Messages are routed through the Execution Platform for agent processing
3. **State Synchronization**: Discussion state is synchronized between services via Redis

### Integration Example

```python
import httpx

# Send agent configuration to Execution Platform
async with httpx.AsyncClient() as client:
    response = await client.post(
        f"{EXECUTION_PLATFORM_URL}/agents",
        json=agent_config
    )
    agent_instance = response.json()
```

## Redis Key Structure

The service uses the following Redis key patterns:

```
discussion:{id}:session         # Session metadata (JSON)
discussion:{id}:messages        # Message list (List of JSON)
discussion:{id}:participants    # Participant hash (Hash)
discussion:{id}:state          # Discussion state (Hash)
discussion:{id}:lock           # Coordination lock (String)
discussions:active             # Set of active discussion IDs
user:{user_id}:discussions     # User's discussion list
```

## Development

### Project Structure

```
discussion-orchestrator/
├── src/
│   ├── __init__.py           # Package initialization
│   ├── main.py               # FastAPI application & endpoints
│   ├── config.py             # Configuration management
│   ├── models.py             # Pydantic data models
│   └── context.py            # Redis context management
├── requirements.txt          # Python dependencies
├── .env.example             # Environment template
└── README.md                # This file
```

### Key Components

- **main.py**: FastAPI application with REST and WebSocket endpoints
- **config.py**: Configuration loading and Redis key patterns
- **models.py**: Pydantic models for data validation
- **context.py**: SharedContext class for Redis state management

### Adding New Features

1. **New Endpoint**: Add route handler in `main.py`
2. **New Model**: Add Pydantic model in `models.py`
3. **New State Logic**: Extend `SharedContext` in `context.py`
4. **New Configuration**: Add setting to `Settings` in `config.py`

## Testing

### Manual Testing with curl

```bash
# Health check
curl http://localhost:5000/health

# Create discussion
curl -X POST http://localhost:5000/v1/discussions \
  -H "Content-Type: application/json" \
  -d '{
    "topic": "Test discussion",
    "agents": [{"persona": "Test Agent"}],
    "protocol": "free_form"
  }'

# Get discussion
curl http://localhost:5000/v1/discussions/{discussion_id}

# Send message
curl -X POST http://localhost:5000/v1/discussions/{discussion_id}/messages \
  -H "Content-Type: application/json" \
  -d '{
    "participant_id": "agent_xyz",
    "content": "Test message"
  }'
```

### Testing WebSocket

Use a WebSocket client or browser console:

```javascript
const ws = new WebSocket('ws://localhost:5000/v1/discussions/disc_test/stream');
ws.onopen = () => console.log('Connected');
ws.onmessage = (e) => console.log('Message:', JSON.parse(e.data));
ws.onerror = (e) => console.error('Error:', e);
```

## Production Considerations

### Performance

- **Connection Pooling**: Redis connection pool configured for concurrent requests
- **Async Operations**: All I/O operations use async/await for non-blocking execution
- **Message Broadcasting**: Efficient WebSocket fan-out with dead connection cleanup

### Reliability

- **Error Handling**: Comprehensive try-catch blocks with proper HTTP status codes
- **Logging**: Structured logging at appropriate levels (INFO, WARNING, ERROR)
- **Health Checks**: Redis connectivity verified in health endpoint

### Scalability

- **Stateless Design**: Application state stored in Redis, enabling horizontal scaling
- **Redis Pub/Sub**: Can be extended to use Redis pub/sub for cross-instance messaging
- **Load Balancing**: Multiple instances can run behind a load balancer

### Security

- **CORS**: Configured with explicit allowed origins
- **Input Validation**: All inputs validated with Pydantic models
- **Error Messages**: Generic error messages to avoid information leakage

## Monitoring

### Logs

Logs are written to stdout in a structured format:

```
2025-01-15 10:00:00 - src.main - INFO - Created discussion session: disc_abc123
2025-01-15 10:00:01 - src.context - INFO - Connected to Redis successfully
```

### Metrics (Future Enhancement)

Consider adding:
- Prometheus metrics endpoint
- Request/response time tracking
- Active discussion count
- Message throughput

## Troubleshooting

### Redis Connection Failed

```
Error: Failed to connect to Redis
```

**Solution**: Verify Redis is running and URL is correct in `.env`

```bash
redis-cli ping  # Should return "PONG"
```

### WebSocket Connection Refused

```
Error: WebSocket connection refused
```

**Solution**: Check CORS origins include your frontend domain

### Import Errors

```
ModuleNotFoundError: No module named 'fastapi'
```

**Solution**: Install dependencies and activate virtual environment

```bash
pip install -r requirements.txt
source venv/bin/activate
```

## Roadmap

- [ ] Implement AutoGen integration for agent execution
- [ ] Add discussion protocol implementations (round-robin, consensus)
- [ ] Implement turn management and moderation
- [ ] Add authentication and authorization
- [ ] Implement rate limiting
- [ ] Add comprehensive test suite
- [ ] Create Docker deployment configuration
- [ ] Add Prometheus metrics
- [ ] Implement discussion analytics
- [ ] Add support for file attachments

## Contributing

1. Follow PEP 8 style guidelines
2. Add docstrings to all functions and classes
3. Use type hints for function parameters and returns
4. Write tests for new features
5. Update documentation as needed

## License

[Add your license information here]

## Support

For issues and questions:
- Create an issue in the repository
- Contact the Maestro Platform team
- Check the API documentation at `/docs`

---

**Version**: 0.1.0
**Last Updated**: 2025-01-15
