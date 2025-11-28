# Maestro Platform Deployment Guide

This guide provides comprehensive instructions for deploying and managing the Maestro Platform services, including the Discussion Orchestrator and Execution Platform.

## Table of Contents

- [Architecture Overview](#architecture-overview)
- [Prerequisites](#prerequisites)
- [Environment Configuration](#environment-configuration)
- [Service Deployment](#service-deployment)
- [Development Setup](#development-setup)
- [Port Mappings](#port-mappings)
- [Service Dependencies](#service-dependencies)
- [Monitoring and Health Checks](#monitoring-and-health-checks)
- [Troubleshooting](#troubleshooting)

## Architecture Overview

The Maestro Platform consists of the following services:

```
┌─────────────────────────────────────────────────────────┐
│                    Maestro Platform                      │
├─────────────────────────────────────────────────────────┤
│                                                           │
│  ┌──────────────────┐      ┌──────────────────┐        │
│  │   Discussion     │      │   Execution      │        │
│  │  Orchestrator    │◄────►│   Platform       │        │
│  │   (Port 5000)    │      │   (Port 8000)    │        │
│  └────────┬─────────┘      └────────┬─────────┘        │
│           │                         │                   │
│           │        ┌────────────────┘                   │
│           │        │                                    │
│           ▼        ▼                                    │
│      ┌─────────────────┐                               │
│      │     Redis       │                               │
│      │  (Port 6379)    │                               │
│      └─────────────────┘                               │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

### Services:

1. **Discussion Orchestrator**: Multi-agent discussion service using AutoGen
2. **Execution Platform**: Code execution and LLM integration service
3. **Redis**: Caching and message broker

## Prerequisites

- Docker (v20.10+)
- Docker Compose (v2.0+)
- Python 3.11+ (for local development)
- Git

## Environment Configuration

### Step 1: Copy Environment File

```bash
cd /home/ec2-user/projects/maestro-platform
cp .env.example .env
```

### Step 2: Configure Environment Variables

Edit `.env` and set the following required variables:

```bash
# LLM API Keys (at least one required)
OPENAI_API_KEY=sk-your-openai-api-key
ANTHROPIC_API_KEY=your-anthropic-api-key

# Execution Platform
EXECUTION_PLATFORM_API_KEY=your-secure-api-key

# Security
SECRET_KEY=your-random-secret-key-here

# Optional: Customize service URLs
DISCUSSION_ORCHESTRATOR_URL=http://discussion-orchestrator:5000
EXECUTION_PLATFORM_URL=http://execution-platform:8080
REDIS_URL=redis://redis:6379
```

### Step 3: Configure Service-Specific Environment

```bash
# Discussion Orchestrator
cd discussion-orchestrator
cp .env.example .env
# Edit .env with service-specific settings

# Execution Platform
cd ../execution-platform
cp .env.example .env
# Edit .env with service-specific settings
```

## Service Deployment

### Production Deployment

Start all services in production mode:

```bash
cd /home/ec2-user/projects/maestro-platform

# Build and start all services
docker-compose up -d

# View logs
docker-compose logs -f

# View specific service logs
docker-compose logs -f discussion-orchestrator
docker-compose logs -f execution-platform
```

### Verify Services

Check that all services are running:

```bash
# Check service status
docker-compose ps

# Check health endpoints
curl http://localhost:5000/health  # Discussion Orchestrator
curl http://localhost:8000/health  # Execution Platform

# Check API documentation
open http://localhost:5000/docs    # Discussion Orchestrator API docs
open http://localhost:8000/docs    # Execution Platform API docs
```

## Development Setup

### Option 1: Docker Development Mode

Run services with live code reloading:

```bash
# Start with development overrides
docker-compose -f docker-compose.yml -f discussion-orchestrator/docker-compose.dev.yml up

# Or start individual service in dev mode
docker-compose -f docker-compose.yml -f discussion-orchestrator/docker-compose.dev.yml up discussion-orchestrator
```

### Option 2: Local Development

Run services locally without Docker:

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

### Running Tests

```bash
# Discussion Orchestrator tests
cd discussion-orchestrator
./scripts/test.sh

# Or with Docker
docker-compose run --rm discussion-orchestrator pytest
```

## Port Mappings

| Service                | Internal Port | External Port | Description                          |
|------------------------|---------------|---------------|--------------------------------------|
| Discussion Orchestrator| 5000          | 5000          | FastAPI + WebSocket server           |
| Execution Platform     | 8080          | 8000          | Code execution gateway               |
| Redis                  | 6379          | 6379          | Cache and message broker             |
| Debug Port (Dev)       | 5678          | 5678          | Python debugger (development only)   |

## Service Dependencies

### Startup Order

The services start in the following order to respect dependencies:

1. **Redis** - Must be healthy before other services start
2. **Execution Platform** - Starts after Redis
3. **Discussion Orchestrator** - Starts after Redis and Execution Platform

### Dependency Graph

```
Redis (healthy)
  │
  ├─► Execution Platform
  │
  └─► Discussion Orchestrator ──► Execution Platform
```

## Monitoring and Health Checks

### Health Check Endpoints

Each service provides a health check endpoint:

```bash
# Discussion Orchestrator
curl http://localhost:5000/health

# Execution Platform
curl http://localhost:8000/health

# Redis
docker-compose exec redis redis-cli ping
```

### Docker Health Checks

Services are configured with automatic health checks:

- **Redis**: Every 10s, timeout 5s
- **Execution Platform**: Every 30s, timeout 10s
- **Discussion Orchestrator**: Every 30s, timeout 10s, start period 10s

View health status:

```bash
docker-compose ps
```

### Logs

Access service logs:

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f discussion-orchestrator

# Last 100 lines
docker-compose logs --tail=100 discussion-orchestrator

# Since specific time
docker-compose logs --since 30m discussion-orchestrator
```

## Common Operations

### Restart Services

```bash
# Restart all services
docker-compose restart

# Restart specific service
docker-compose restart discussion-orchestrator

# Rebuild and restart (after code changes)
docker-compose up -d --build discussion-orchestrator
```

### Scale Services

```bash
# Scale discussion orchestrator to 3 instances
docker-compose up -d --scale discussion-orchestrator=3
```

### Stop Services

```bash
# Stop all services
docker-compose down

# Stop and remove volumes
docker-compose down -v

# Stop specific service
docker-compose stop discussion-orchestrator
```

### Update Services

```bash
# Pull latest code
git pull

# Rebuild and restart
docker-compose up -d --build

# Or rebuild specific service
docker-compose up -d --build discussion-orchestrator
```

## Troubleshooting

### Service Won't Start

1. Check logs:
   ```bash
   docker-compose logs discussion-orchestrator
   ```

2. Verify environment variables:
   ```bash
   docker-compose config
   ```

3. Check port conflicts:
   ```bash
   lsof -i :5000
   lsof -i :8000
   ```

### Redis Connection Issues

1. Verify Redis is running:
   ```bash
   docker-compose ps redis
   ```

2. Test connection:
   ```bash
   docker-compose exec redis redis-cli ping
   ```

3. Check Redis logs:
   ```bash
   docker-compose logs redis
   ```

### Memory Issues

1. Check Docker resources:
   ```bash
   docker stats
   ```

2. Increase Docker memory limit in Docker Desktop settings

3. Reduce concurrent operations in configuration

### Network Issues

1. Verify network exists:
   ```bash
   docker network ls | grep maestro
   ```

2. Inspect network:
   ```bash
   docker network inspect maestro-network
   ```

3. Recreate network:
   ```bash
   docker-compose down
   docker network prune
   docker-compose up -d
   ```

## Development Workflow

### Making Code Changes

1. Edit code in `discussion-orchestrator/src/`
2. If using development mode, changes are auto-reloaded
3. If using production mode, rebuild:
   ```bash
   docker-compose up -d --build discussion-orchestrator
   ```

### Adding Dependencies

1. Update `requirements.txt`
2. Rebuild container:
   ```bash
   docker-compose build discussion-orchestrator
   docker-compose up -d discussion-orchestrator
   ```

### Running Tests Before Commit

```bash
cd discussion-orchestrator
./scripts/test.sh
```

## Production Considerations

### Environment Variables

- Never commit `.env` files
- Use secrets management in production (AWS Secrets Manager, HashiCorp Vault)
- Rotate API keys regularly

### Security

- Run containers as non-root user (already configured)
- Use network policies to restrict inter-service communication
- Enable TLS/SSL for external endpoints
- Implement rate limiting
- Use API authentication tokens

### Performance

- Monitor resource usage with `docker stats`
- Scale services horizontally as needed
- Use Redis persistence for production
- Implement caching strategies
- Configure appropriate timeouts

### Backup and Recovery

- Backup Redis data regularly
- Use volume snapshots for persistence
- Document restore procedures
- Test disaster recovery plans

## Quick Reference Commands

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Restart service
docker-compose restart discussion-orchestrator

# Rebuild and start
docker-compose up -d --build

# Stop all services
docker-compose down

# Development mode
docker-compose -f docker-compose.yml -f discussion-orchestrator/docker-compose.dev.yml up

# Run tests
cd discussion-orchestrator && ./scripts/test.sh

# Check health
curl http://localhost:5000/health
curl http://localhost:8000/health

# View API docs
open http://localhost:5000/docs
open http://localhost:8000/docs
```

## Support

For issues and questions:
- Check logs: `docker-compose logs -f`
- Review health checks: `docker-compose ps`
- Consult service documentation in respective README files
- Check GitHub issues: https://github.com/maestro-platform/maestro-platform/issues
