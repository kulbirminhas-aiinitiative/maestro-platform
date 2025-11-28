# Maestro DevOps

Centralized deployment, monitoring, and operations scripts for the Maestro platform.

## Structure

```
maestro-devops/
├── scripts/           # Deployment and operational scripts
│   ├── deploy-service.sh        # Unified service deployment
│   ├── deploy-demo.sh           # Demo server deployment
│   ├── deploy-production.sh     # Production deployment
│   ├── health-monitor.sh        # Health monitoring with alerts
│   ├── notify-deployment.sh     # Deployment notifications
│   ├── rollback.sh              # Automated rollback
│   └── pre-deployment-checks.sh # Pre-deployment validation
├── configs/           # Configuration templates
└── README.md
```

## Quick Start

### Deploy a Service

```bash
# Deploy a specific service
./scripts/deploy-service.sh maestro-templates

# Deploy all services
./scripts/deploy-service.sh --all

# Check service status
./scripts/deploy-service.sh --status
```

### Environment Variables

Set these before running deployment scripts:

```bash
export DEMO_SERVER="18.134.157.225"
export SSH_KEY_PATH="/home/ec2-user/projects/genesis-dev.pem"
```

### Available Services

- `infrastructure` - Redis, PostgreSQL
- `maestro-engine` - Core workflow engine
- `maestro-templates` - Template service
- `quality-fabric` - Quality assurance service
- `gateway` - API gateway
- `frontend` - Frontend and BFF

## Scripts

### deploy-service.sh

Unified deployment script for all Maestro services. Validates existing services before deploying.

```bash
./scripts/deploy-service.sh <service-name>
./scripts/deploy-service.sh --all
./scripts/deploy-service.sh --status
```

### health-monitor.sh

Monitors all services and sends alerts via Slack, email, or JIRA.

```bash
# Run health check
./scripts/health-monitor.sh

# Add to cron for continuous monitoring
*/5 * * * * /path/to/health-monitor.sh
```

Environment variables:
- `SLACK_WEBHOOK_URL` - Slack webhook for alerts
- `ALERT_EMAIL` - Email for notifications
- `JIRA_EMAIL`, `JIRA_API_TOKEN` - JIRA credentials for issue creation

### notify-deployment.sh

Sends deployment notifications for events.

```bash
./scripts/notify-deployment.sh started
./scripts/notify-deployment.sh succeeded
./scripts/notify-deployment.sh failed "Error message"
./scripts/notify-deployment.sh rolled_back "Reason"
```

### rollback.sh

Automated rollback mechanism maintaining last 3 successful deployments.

```bash
# Interactive rollback selection
./scripts/rollback.sh

# Auto-rollback to previous version
./scripts/rollback.sh --auto

# Rollback to specific version
./scripts/rollback.sh --version backup-20251122-120000

# List available rollback points
./scripts/rollback.sh --list

# Deploy with automatic rollback on failure
./scripts/rollback.sh --deploy
```

## JIRA Integration

Related JIRA Epic: [MD-635](https://fifth9.atlassian.net/browse/MD-635)

## Migration Notes

These scripts were migrated from `maestro-frontend-production/scripts/` to this centralized location on 2025-11-22. The original scripts remain in place for backward compatibility but should be deprecated.
