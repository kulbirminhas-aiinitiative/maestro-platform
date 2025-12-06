# Maestro Status Dashboard

> MD-2033: Web-Based Service Status Dashboard
> Part of EPIC MD-1979: Service Resilience & Operational Hardening

## Overview

A lightweight web dashboard for viewing service status across environments without requiring SSH access.

## Features

- **Real-time Status**: View PM2 process status and health endpoint status
- **Multi-Environment**: Compare Dev, Sandbox, and Demo environments side-by-side
- **Auto-Refresh**: Updates every 30 seconds
- **Health History**: Visual timeline of health check history (last 24h)
- **Incident Timeline**: Track status changes and degradations
- **Mobile-Friendly**: Responsive design works on all devices
- **Authentication**: Simple username/password authentication

## Quick Start

### Option 1: Direct Python

```bash
./run.sh
```

### Option 2: Docker

```bash
docker-compose up -d
```

## Access

| URL | Description |
|-----|-------------|
| http://localhost:8080 | Dashboard |
| http://localhost:8080/health | Health check |

**Default Credentials:**
- Username: `admin`
- Password: `maestro_status_2024`

## Configuration

Environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| PORT | 8080 | Server port |
| DEBUG | false | Enable debug mode |
| SECRET_KEY | (generated) | Flask secret key |
| ADMIN_USERNAME | admin | Dashboard username |
| ADMIN_PASSWORD | maestro_status_2024 | Dashboard password |

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/status` | All environments status |
| GET | `/api/status/<env>` | Single environment status |
| GET | `/api/history/<env>` | Health check history |
| GET | `/api/incidents` | Recent incidents |
| POST | `/api/actions/restart/<service>` | Restart a PM2 service |

## Environments Monitored

- **Development** (localhost:4100)
- **Sandbox** (localhost:14100)
- **Demo** (localhost:4100)

## Architecture

```
status-dashboard/
├── app.py              # Flask application
├── requirements.txt    # Python dependencies
├── run.sh              # Startup script
├── Dockerfile          # Docker image
├── docker-compose.yml  # Docker deployment
├── templates/
│   ├── index.html      # Main dashboard
│   └── login.html      # Login page
└── static/
    └── style.css       # Styles
```

## Screenshots

Dashboard shows:
- Environment cards with status badges
- Service list with memory, uptime, restarts
- Health endpoint status with response time
- History timeline visualization
- Recent incidents list

## SSH Tunnel Access

For remote access:

```bash
ssh -L 8080:localhost:8080 user@server
# Then access http://localhost:8080
```
