# PostgreSQL Integration Guide

## 🎯 Overview

This guide covers the PostgreSQL integration for the Maestro DAG Workflow system, providing production-grade persistence for workflows, executions, node states, events, and artifacts.

**What's New:**
- ✅ PostgreSQL-backed workflow storage (replaces in-memory storage)
- ✅ SQLAlchemy ORM with complete schema
- ✅ Database migrations with Alembic
- ✅ Production-ready API server (`dag_api_server_postgres.py`)
- ✅ Workflow recovery and resume capabilities
- ✅ Event tracking and audit logs
- ✅ Multi-instance support (horizontal scaling ready)

---

## 📊 Architecture

### Database Schema

```
┌─────────────────────────┐
│ workflow_definitions    │  Workflow DAG structures
│  - id (PK)             │
│  - name                │
│  - nodes (JSON)        │
│  - edges (JSON)        │
│  - metadata (JSON)     │
└────────┬────────────────┘
         │
         │ 1:N
         ↓
┌─────────────────────────┐
│ workflow_executions     │  Execution instances
│  - id (PK)             │
│  - workflow_id (FK)    │
│  - status              │
│  - progress_percent    │
│  - global_context      │
└────────┬────────────────┘
         │
         ├── 1:N ──→ ┌──────────────────┐
         │           │ node_states      │  Node execution states
         │           │  - execution_id  │
         │           │  - node_id       │
         │           │  - status        │
         │           │  - outputs       │
         │           └──────────────────┘
         │
         ├── 1:N ──→ ┌──────────────────┐
         │           │ execution_events │  Event logs
         │           │  - execution_id  │
         │           │  - event_type    │
         │           │  - node_id       │
         │           │  - data (JSON)   │
         │           └──────────────────┘
         │
         └── 1:N ──→ ┌──────────────────┐
                     │ artifacts        │  Generated files
                     │  - execution_id  │
                     │  - node_id       │
                     │  - file_path     │
                     └──────────────────┘
```

### Component Stack

```
FastAPI Application (dag_api_server_postgres.py)
    ↓
Database Package (database/)
    ├── models.py          → SQLAlchemy models
    ├── config.py          → Database engine & connections
    ├── repository.py      → Data access layer
    └── workflow_store.py  → Context persistence
    ↓
PostgreSQL Database
    └── maestro_workflows (database)
        ├── workflow_definitions
        ├── workflow_executions
        ├── node_states
        ├── execution_events
        └── artifacts
```

---

## 🚀 Quick Start

### Option 1: Automated Setup (Recommended)

```bash
# Run setup script
./setup_database.sh sqlite     # For development (SQLite)
./setup_database.sh postgres   # For production (PostgreSQL)

# The script will:
# 1. Install dependencies (SQLAlchemy, psycopg2, Alembic)
# 2. Setup database (PostgreSQL) or create SQLite file
# 3. Initialize schema
# 4. Verify connection
```

### Option 2: Manual Setup

**1. Install Dependencies**

```bash
# Using Poetry
poetry add sqlalchemy psycopg2-binary alembic

# Or using pip
pip3 install sqlalchemy psycopg2-binary alembic
```

**2. Setup PostgreSQL**

```bash
# Install PostgreSQL (Amazon Linux 2)
sudo yum install -y postgresql15 postgresql15-server
sudo postgresql-setup --initdb
sudo systemctl enable postgresql
sudo systemctl start postgresql

# Create database and user
sudo -u postgres psql << EOF
CREATE USER maestro WITH PASSWORD 'maestro_dev';
CREATE DATABASE maestro_workflows OWNER maestro;
GRANT ALL PRIVILEGES ON DATABASE maestro_workflows TO maestro;
EOF
```

**3. Configure Environment**

```bash
# Create .env.database
cat > .env.database << EOF
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=maestro_workflows
POSTGRES_USER=maestro
POSTGRES_PASSWORD=maestro_dev
USE_SQLITE=false
EOF

# Source environment
source .env.database
```

**4. Initialize Database**

```bash
# Initialize schema
python3 -c "from database import initialize_database; initialize_database()"

# Or run migrations (alternative)
alembic upgrade head
```

**5. Start API Server**

```bash
python3 dag_api_server_postgres.py

# API available at:
# - REST: http://localhost:8000/api
# - Docs: http://localhost:8000/docs
# - WebSocket: ws://localhost:8000/ws/workflow/{id}
```

---

## 📚 Database Models

### WorkflowDefinition

Stores workflow DAG structure.

```python
from database.models import WorkflowDefinition

workflow = WorkflowDefinition(
    id="sdlc_parallel",
    name="SDLC Parallel Workflow",
    workflow_type="parallel",
    nodes={
        "requirements": {"name": "Requirements", "type": "phase"},
        "design": {"name": "Design", "type": "phase"},
        # ...
    },
    edges=[
        {"source": "requirements", "target": "design"},
        # ...
    ]
)
```

**Fields:**
- `id` - Unique workflow identifier
- `name` - Human-readable name
- `workflow_type` - Type (linear, parallel, custom)
- `nodes` - Node definitions (JSON)
- `edges` - Edge connections (JSON)
- `metadata` - Custom metadata (JSON)

### WorkflowExecution

Tracks workflow execution instances.

```python
from database.models import WorkflowExecution, WorkflowStatus

execution = WorkflowExecution(
    id="exec_sdlc_parallel_20251011_abc123",
    workflow_id="sdlc_parallel",
    status=WorkflowStatus.RUNNING,
    initial_context={"requirement": "Build todo app"},
    progress_percent=45.0,
    completed_nodes=3,
    total_nodes=6
)
```

**Fields:**
- `id` - Unique execution identifier
- `workflow_id` - Reference to workflow definition
- `status` - Execution status (pending, running, completed, failed)
- `initial_context` - Input parameters (JSON)
- `global_context` - Shared execution context (JSON)
- `progress_percent` - Progress (0-100)
- `started_at`, `completed_at` - Timestamps

### NodeState

Tracks individual node execution state.

```python
from database.models import NodeState, NodeStatus

node_state = NodeState(
    execution_id="exec_sdlc_parallel_20251011_abc123",
    node_id="requirements",
    node_name="Requirements Analysis",
    node_type="phase",
    status=NodeStatus.COMPLETED,
    attempt_count=1,
    outputs={"artifacts": 6, "quality": 0.85},
    duration_seconds=532.5
)
```

**Fields:**
- `execution_id` - Parent execution
- `node_id` - Node identifier
- `status` - Node status (pending, running, completed, failed)
- `attempt_count` - Retry attempts
- `inputs`, `outputs` - Node I/O (JSON)
- `started_at`, `completed_at` - Timestamps
- `quality_score` - Quality metrics

### ExecutionEvent

Logs all execution events.

```python
from database.models import ExecutionEvent, EventType

event = ExecutionEvent(
    execution_id="exec_sdlc_parallel_20251011_abc123",
    event_type=EventType.NODE_COMPLETED,
    node_id="requirements",
    message="Requirements phase completed successfully",
    data={"artifacts": 6, "duration": 532.5}
)
```

### Artifact

Stores generated files and outputs.

```python
from database.models import Artifact

artifact = Artifact(
    execution_id="exec_sdlc_parallel_20251011_abc123",
    node_id="requirements",
    artifact_type="file",
    name="user_stories.md",
    file_path="/path/to/user_stories.md",
    size_bytes=4096
)
```

---

## 🔧 Repository Layer

The repository layer provides high-level data access methods.

### WorkflowRepository

```python
from database import get_db, RepositoryFactory

with get_db() as session:
    repos = RepositoryFactory(session)

    # Create workflow
    workflow = repos.workflow.create(workflow_dag)

    # Get workflow
    workflow = repos.workflow.get("sdlc_parallel")

    # List workflows
    workflows = repos.workflow.list(limit=100)

    # Delete workflow
    repos.workflow.delete("sdlc_parallel")
```

### ExecutionRepository

```python
# Create execution
execution = repos.execution.create(
    workflow_id="sdlc_parallel",
    initial_context={"requirement": "Build todo app"}
)

# Get execution
execution = repos.execution.get(execution_id)

# Update status
repos.execution.update_status(
    execution_id=execution_id,
    status=WorkflowStatus.COMPLETED
)

# Update progress
repos.execution.update_progress(execution_id)

# List executions for workflow
executions = repos.execution.list_by_workflow("sdlc_parallel")

# List active executions
active = repos.execution.list_active()
```

### NodeStateRepository

```python
# Create/update node state
node_state = repos.node_state.create_or_update(
    execution_id=execution_id,
    node_id="requirements",
    node_state=dag_node_state  # From DAG execution
)

# Get node states for execution
node_states = repos.node_state.get_by_execution(execution_id)

# Get specific node
node = repos.node_state.get_node(execution_id, "requirements")
```

### EventRepository

```python
# Create event
event = repos.event.create(
    execution_id=execution_id,
    event_type=EventType.NODE_STARTED,
    node_id="requirements",
    message="Starting requirements analysis"
)

# Get events for execution
events = repos.event.list_by_execution(execution_id)

# Get events for specific node
node_events = repos.event.list_by_node(execution_id, "requirements")
```

---

## 💾 DatabaseWorkflowContextStore

Drop-in replacement for in-memory `WorkflowContextStore` with PostgreSQL persistence.

### Usage

```python
from database.workflow_store import DatabaseWorkflowContextStore
from dag_executor import DAGExecutor

# Create store
context_store = DatabaseWorkflowContextStore()

# Create executor with database-backed store
executor = DAGExecutor(
    workflow=workflow_dag,
    context_store=context_store
)

# Execute workflow (context automatically persisted)
context = await executor.execute(initial_context={...})

# Load context for recovery
context = context_store.load_context(execution_id)

# Resume execution
context = await executor.resume(context)
```

### Methods

```python
# Save context
context_store.save_context(workflow_context)

# Load context
context = context_store.load_context(execution_id)

# List executions
execution_ids = context_store.list_executions(workflow_id="sdlc_parallel")

# Delete execution
context_store.delete_context(execution_id)

# Log event
context_store.log_event(
    execution_id=execution_id,
    event_type="node_completed",
    node_id="requirements",
    data={"duration": 532.5}
)

# Get events
events = context_store.get_events(execution_id)

# Register workflow
context_store.register_workflow(workflow_dag)

# Update execution status
context_store.update_execution_status(
    execution_id=execution_id,
    status="completed"
)
```

---

## 🔄 Database Migrations

Alembic is configured for database schema migrations.

### Create Migration

```bash
# Auto-generate migration from model changes
alembic revision --autogenerate -m "Add quality metrics to node_states"

# Create empty migration
alembic revision -m "Custom migration"
```

### Apply Migrations

```bash
# Upgrade to latest
alembic upgrade head

# Upgrade one version
alembic upgrade +1

# Downgrade one version
alembic downgrade -1

# Downgrade to specific version
alembic downgrade <revision_id>

# Downgrade to base (empty database)
alembic downgrade base
```

### Check Migration Status

```bash
# Show current version
alembic current

# Show migration history
alembic history

# Show pending migrations
alembic history --verbose
```

---

## 🌐 API Server with PostgreSQL

The `dag_api_server_postgres.py` server uses PostgreSQL for all persistence.

### Key Features

1. **Database-backed workflow storage**
   - All workflows persisted to PostgreSQL
   - No data loss on server restart

2. **Execution persistence**
   - Full execution history
   - Progress tracking
   - Event logs

3. **Recovery support**
   - Resume failed executions
   - Workflow state recovery
   - Audit trail

4. **Horizontal scaling ready**
   - Multiple API instances can share database
   - Ready for Redis pub/sub (future enhancement)

### API Endpoints

All endpoints use database backend:

```bash
# List workflows (from database)
GET /api/workflows

# Create workflow (persisted to database)
POST /api/workflows

# Get workflow details
GET /api/workflows/{workflow_id}

# Execute workflow (tracked in database)
POST /api/workflows/{workflow_id}/execute

# Get execution status (from database)
GET /api/executions/{execution_id}

# Health check (includes database status)
GET /health
```

### WebSocket with Event Logging

WebSocket events are logged to database:

```python
# Events broadcasted to WebSocket AND saved to database
{
    "type": "node_completed",
    "execution_id": "exec_...",
    "node_id": "requirements",
    "timestamp": "2025-10-11T12:00:00",
    "data": {"artifacts": 6, "quality": 0.85}
}
```

---

## 🧪 Testing

### Test Database Connection

```bash
# Run health check
python3 database/config.py health

# Or via API
curl http://localhost:8000/health
```

### Test Workflow Execution

```bash
# Create and execute workflow
curl -X POST http://localhost:8000/api/workflows/sdlc_parallel/execute \
  -H 'Content-Type: application/json' \
  -d '{
    "requirement": "Build a simple todo application with user authentication"
  }'

# Response:
{
  "execution_id": "exec_sdlc_parallel_20251011_120000_abc123",
  "workflow_id": "sdlc_parallel",
  "status": "running",
  "started_at": "2025-10-11T12:00:00"
}

# Check execution status
curl http://localhost:8000/api/executions/exec_sdlc_parallel_20251011_120000_abc123

# Response:
{
  "execution_id": "exec_...",
  "workflow_id": "sdlc_parallel",
  "status": "running",
  "progress_percent": 33.3,
  "completed_nodes": 2,
  "total_nodes": 6,
  "node_states": [...]
}
```

### Query Database Directly

```bash
# Connect to PostgreSQL
psql -h localhost -U maestro -d maestro_workflows

# Query executions
SELECT id, workflow_id, status, progress_percent, started_at
FROM workflow_executions
ORDER BY started_at DESC
LIMIT 10;

# Query node states
SELECT execution_id, node_id, status, duration_seconds, quality_score
FROM node_states
WHERE execution_id = 'exec_...';

# Query events
SELECT event_type, node_id, timestamp, message
FROM execution_events
WHERE execution_id = 'exec_...'
ORDER BY timestamp;

# Query artifacts
SELECT node_id, name, file_path, size_bytes
FROM artifacts
WHERE execution_id = 'exec_...';
```

---

## 🔧 Configuration

### Environment Variables

```bash
# PostgreSQL (Production)
export POSTGRES_HOST=localhost
export POSTGRES_PORT=5432
export POSTGRES_DB=maestro_workflows
export POSTGRES_USER=maestro
export POSTGRES_PASSWORD=maestro_dev
export USE_SQLITE=false

# Connection Pool
export DB_POOL_SIZE=10
export DB_MAX_OVERFLOW=20
export DB_POOL_TIMEOUT=30
export DB_POOL_RECYCLE=3600

# SQLite (Development)
export USE_SQLITE=true
export SQLITE_PATH=maestro_workflows.db
```

### Database Configuration

```python
from database.config import DatabaseConfig

# Customize configuration
config = DatabaseConfig()
config.host = "db.example.com"
config.port = 5432
config.pool_size = 20

# Create engine with custom config
from database.config import DatabaseEngine
engine = DatabaseEngine(config)
engine.initialize()
```

---

## 🚀 Production Deployment

### PostgreSQL Setup

```bash
# 1. Install PostgreSQL
sudo yum install -y postgresql15 postgresql15-server

# 2. Initialize and start
sudo postgresql-setup --initdb
sudo systemctl enable postgresql
sudo systemctl start postgresql

# 3. Configure PostgreSQL for remote access (optional)
sudo vi /var/lib/pgsql/data/postgresql.conf
# Set: listen_addresses = '*'

sudo vi /var/lib/pgsql/data/pg_hba.conf
# Add: host all all 0.0.0.0/0 md5

# 4. Restart PostgreSQL
sudo systemctl restart postgresql

# 5. Create production database
sudo -u postgres psql << EOF
CREATE USER maestro_prod WITH PASSWORD 'STRONG_PASSWORD_HERE';
CREATE DATABASE maestro_workflows_prod OWNER maestro_prod;
GRANT ALL PRIVILEGES ON DATABASE maestro_workflows_prod TO maestro_prod;
EOF
```

### Production Configuration

```bash
# .env.production
POSTGRES_HOST=db.internal.company.com
POSTGRES_PORT=5432
POSTGRES_DB=maestro_workflows_prod
POSTGRES_USER=maestro_prod
POSTGRES_PASSWORD=<strong-password>
USE_SQLITE=false

# Connection pool for production
DB_POOL_SIZE=20
DB_MAX_OVERFLOW=40
DB_POOL_TIMEOUT=60
DB_POOL_RECYCLE=3600
```

### Deploy with Systemd

```bash
# Create systemd service
sudo vi /etc/systemd/system/maestro-dag-api.service

[Unit]
Description=Maestro DAG Workflow API Server
After=network.target postgresql.service

[Service]
Type=simple
User=maestro
WorkingDirectory=/opt/maestro-hive
EnvironmentFile=/opt/maestro-hive/.env.production
ExecStart=/usr/bin/python3 /opt/maestro-hive/dag_api_server_postgres.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target

# Enable and start
sudo systemctl enable maestro-dag-api
sudo systemctl start maestro-dag-api

# Check status
sudo systemctl status maestro-dag-api
```

### Database Backup

```bash
# Backup database
pg_dump -h localhost -U maestro_prod maestro_workflows_prod > backup.sql

# Restore database
psql -h localhost -U maestro_prod maestro_workflows_prod < backup.sql

# Automated daily backups
cat > /etc/cron.daily/maestro-db-backup << 'EOF'
#!/bin/bash
BACKUP_DIR=/var/backups/maestro
DATE=$(date +%Y%m%d_%H%M%S)
pg_dump -h localhost -U maestro_prod maestro_workflows_prod | gzip > $BACKUP_DIR/maestro_workflows_$DATE.sql.gz
find $BACKUP_DIR -name "*.sql.gz" -mtime +30 -delete
EOF

chmod +x /etc/cron.daily/maestro-db-backup
```

---

## 📈 Monitoring

### Database Metrics

```sql
-- Active executions
SELECT status, COUNT(*)
FROM workflow_executions
GROUP BY status;

-- Execution success rate
SELECT
    COUNT(CASE WHEN status = 'completed' THEN 1 END)::float / COUNT(*) * 100 AS success_rate
FROM workflow_executions;

-- Average execution duration
SELECT
    AVG(EXTRACT(EPOCH FROM (completed_at - started_at))) AS avg_duration_seconds
FROM workflow_executions
WHERE status = 'completed';

-- Node failure rate
SELECT
    node_id,
    COUNT(CASE WHEN status = 'failed' THEN 1 END)::float / COUNT(*) * 100 AS failure_rate
FROM node_states
GROUP BY node_id;
```

### Performance Tuning

```sql
-- Add indexes for common queries
CREATE INDEX idx_execution_workflow_status ON workflow_executions(workflow_id, status);
CREATE INDEX idx_node_state_execution_status ON node_states(execution_id, status);
CREATE INDEX idx_event_execution_timestamp ON execution_events(execution_id, timestamp);

-- Vacuum and analyze
VACUUM ANALYZE workflow_executions;
VACUUM ANALYZE node_states;
VACUUM ANALYZE execution_events;
```

---

## 🐛 Troubleshooting

### Connection Issues

```bash
# Check PostgreSQL is running
sudo systemctl status postgresql

# Test connection
psql -h localhost -U maestro -d maestro_workflows -c "SELECT 1"

# Check logs
sudo tail -f /var/lib/pgsql/data/log/postgresql-*.log
```

### Migration Issues

```bash
# Check current version
alembic current

# Show migration history
alembic history

# Force stamp version (if out of sync)
alembic stamp head

# Reset and recreate (development only!)
python3 database/config.py reset
```

### Performance Issues

```sql
-- Check slow queries
SELECT query, mean_exec_time, calls
FROM pg_stat_statements
ORDER BY mean_exec_time DESC
LIMIT 10;

-- Check table sizes
SELECT
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;

-- Check connection pool
SELECT count(*) FROM pg_stat_activity;
```

---

## 📝 Summary

**What We Built:**

1. ✅ **Database Schema** - Complete PostgreSQL schema for workflows
2. ✅ **SQLAlchemy Models** - Type-safe ORM models
3. ✅ **Repository Layer** - Clean data access abstractions
4. ✅ **Database-backed Store** - Drop-in replacement for in-memory storage
5. ✅ **Migrations** - Alembic setup for schema evolution
6. ✅ **API Server** - Production-ready server with PostgreSQL
7. ✅ **Setup Scripts** - Automated database initialization
8. ✅ **Documentation** - Comprehensive guide (this document)

**Benefits:**

- 💾 **Persistence** - No data loss on restart
- 🔄 **Recovery** - Resume failed workflows
- 📊 **Analytics** - Query execution history
- 🔍 **Audit** - Complete event logs
- 📈 **Scaling** - Multi-instance support
- 🛡️ **Production** - Enterprise-ready storage

**Next Steps:**

1. Test PostgreSQL integration with dog marketplace workflow
2. Add Redis pub/sub for WebSocket scaling
3. Implement workflow builder UI
4. Add Prometheus metrics
5. Setup monitoring dashboards

---

**Ready for Production! 🚀**
