# Maestro Platform - Quick Start Guide

Get the Maestro Platform up and running in minutes.

## Prerequisites Check

```bash
# Check Docker
docker --version
docker-compose --version

# Check ports are free
lsof -i :5000 || echo "Port 5000 is available"
lsof -i :8000 || echo "Port 8000 is available"
lsof -i :6379 || echo "Port 6379 is available"
```

## One-Command Setup

```bash
cd /home/ec2-user/projects/maestro-platform

# 1. Copy and configure environment
cp .env.example .env
# Edit .env and add your API keys (OPENAI_API_KEY, ANTHROPIC_API_KEY)

# 2. Start all services
docker-compose up -d

# 3. Check status
docker-compose ps

# 4. View logs
docker-compose logs -f
```

## Service Access

Once running, access these URLs:

- **Discussion Orchestrator**: http://localhost:5000
  - API Docs: http://localhost:5000/docs
  - Health: http://localhost:5000/health

- **Execution Platform**: http://localhost:8000
  - API Docs: http://localhost:8000/docs
  - Health: http://localhost:8000/health

- **Redis**: localhost:6379

## Common Commands

### Start Services

```bash
# All services
docker-compose up -d

# Specific service
docker-compose up -d discussion-orchestrator

# Development mode with live reload
docker-compose -f docker-compose.yml -f discussion-orchestrator/docker-compose.dev.yml up
```

### View Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f discussion-orchestrator

# Last 100 lines
docker-compose logs --tail=100 discussion-orchestrator
```

### Stop Services

```bash
# Stop all
docker-compose down

# Stop but keep data
docker-compose stop

# Stop and remove volumes (clean slate)
docker-compose down -v
```

### Restart Services

```bash
# Restart all
docker-compose restart

# Restart specific service
docker-compose restart discussion-orchestrator

# Rebuild after code changes
docker-compose up -d --build discussion-orchestrator
```

## Development Workflow

### Local Development (Without Docker)

```bash
# Terminal 1: Start Redis
docker-compose up redis -d

# Terminal 2: Start Execution Platform
cd execution-platform
./scripts/start.sh

# Terminal 3: Start Discussion Orchestrator
cd discussion-orchestrator
./scripts/start.sh
```

### Run Tests

```bash
cd discussion-orchestrator
./scripts/test.sh
```

### Build Docker Image

```bash
cd discussion-orchestrator
./scripts/docker-build.sh v1.0.0
```

## Configuration

### Required Environment Variables

Edit `.env` file:

```bash
# Required: At least one LLM provider API key
OPENAI_API_KEY=sk-...
# OR
ANTHROPIC_API_KEY=sk-ant-...

# Required: Security
SECRET_KEY=your-random-secret-key-here
EXECUTION_PLATFORM_API_KEY=your-secure-api-key

# Optional: Customize services
LOG_LEVEL=INFO
AUTOGEN_MAX_ROUNDS=20
CORS_ORIGINS=http://localhost:3000,http://localhost:4300
```

## Verify Installation

```bash
# Check all services are healthy
curl http://localhost:5000/health
curl http://localhost:8000/health
docker-compose exec redis redis-cli ping

# Check API documentation
open http://localhost:5000/docs
open http://localhost:8000/docs
```

## Troubleshooting

### Services won't start

```bash
# Check logs
docker-compose logs

# Check if ports are in use
lsof -i :5000
lsof -i :8000
lsof -i :6379

# Recreate everything
docker-compose down -v
docker-compose up -d
```

### Redis connection errors

```bash
# Check Redis is running
docker-compose ps redis

# Test connection
docker-compose exec redis redis-cli ping

# Restart Redis
docker-compose restart redis
```

### Build errors

```bash
# Clean rebuild
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

## Next Steps

1. Read the full [DEPLOYMENT.md](DEPLOYMENT.md) for detailed deployment options
2. Check service-specific READMEs:
   - [Discussion Orchestrator README](discussion-orchestrator/README.md)
   - [Execution Platform README](execution-platform/README.md)
3. Explore the API documentation at `/docs` endpoints
4. Review the architecture documentation

## Support

- Check logs: `docker-compose logs -f`
- Health checks: `curl http://localhost:5000/health`
- Documentation: See DEPLOYMENT.md
- Issues: Create a GitHub issue

---

**Need Help?** Check DEPLOYMENT.md for comprehensive documentation.
