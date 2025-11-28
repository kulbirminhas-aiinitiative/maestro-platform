# Quick Start Guide

Get the Discussion Orchestrator service running in 5 minutes.

## Prerequisites

- Python 3.9+
- Redis server running
- pip installed

## Steps

### 1. Install Dependencies

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install packages
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
# Copy example environment file
cp .env.example .env

# Edit .env if needed (defaults should work for local development)
nano .env
```

### 3. Start Redis (if not running)

```bash
# Check if Redis is running
redis-cli ping

# If not running, start it:
# On systemd-based systems:
sudo systemctl start redis

# Or run directly:
redis-server
```

### 4. Start the Service

```bash
# Option 1: Use the run script
./run.sh

# Option 2: Run directly
python -m uvicorn src.main:app --reload --host 0.0.0.0 --port 5000
```

### 5. Verify It's Working

Open your browser to:
- API Docs: http://localhost:5000/docs
- Health Check: http://localhost:5000/health

## Quick Test

### Using curl

```bash
# Health check
curl http://localhost:5000/health

# Create a discussion
curl -X POST http://localhost:5000/v1/discussions \
  -H "Content-Type: application/json" \
  -d '{
    "topic": "Test Discussion",
    "agents": [
      {
        "persona": "Backend Developer",
        "provider": "openai",
        "model": "gpt-4"
      }
    ],
    "protocol": "free_form"
  }'
```

### Using Python

```python
import requests

# Create discussion
response = requests.post(
    "http://localhost:5000/v1/discussions",
    json={
        "topic": "Design a REST API",
        "agents": [
            {
                "persona": "Backend Developer",
                "provider": "openai",
                "model": "gpt-4"
            }
        ],
        "protocol": "free_form"
    }
)

session = response.json()
discussion_id = session["session"]["id"]
print(f"Created discussion: {discussion_id}")

# Get discussion details
response = requests.get(f"http://localhost:5000/v1/discussions/{discussion_id}")
print(response.json())
```

### Using WebSocket (JavaScript)

```javascript
// Connect to discussion stream
const ws = new WebSocket('ws://localhost:5000/v1/discussions/YOUR_DISCUSSION_ID/stream');

ws.onopen = () => {
  console.log('Connected to discussion stream');
};

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('Received:', data);
};

// Keep connection alive
setInterval(() => {
  ws.send(JSON.stringify({ type: 'ping' }));
}, 30000);
```

## Common Issues

### "Redis connection failed"

Make sure Redis is running:
```bash
redis-cli ping  # Should return "PONG"
```

### "Port 5000 already in use"

Change the port in `.env`:
```env
SERVICE_PORT=5001
```

### Import errors

Make sure you're in the virtual environment:
```bash
source venv/bin/activate
pip install -r requirements.txt
```

## Next Steps

1. Read the full [README.md](README.md) for detailed documentation
2. Explore the API at http://localhost:5000/docs
3. Integrate with the Execution Platform
4. Build your first multi-agent discussion
5. Add custom discussion protocols

## Architecture Overview

```
Client Request
     ↓
FastAPI Endpoints
     ↓
SharedContext (Redis)
     ↓
WebSocket Broadcast
     ↓
Connected Clients
```

## Project Structure

```
discussion-orchestrator/
├── src/
│   ├── main.py          # FastAPI app & endpoints
│   ├── models.py        # Data models
│   ├── config.py        # Configuration
│   └── context.py       # Redis state management
├── requirements.txt     # Dependencies
├── .env.example        # Config template
├── run.sh              # Startup script
└── README.md           # Full documentation
```

## Support

- API Docs: http://localhost:5000/docs
- Health Check: http://localhost:5000/health
- Full README: [README.md](README.md)

Happy orchestrating!
