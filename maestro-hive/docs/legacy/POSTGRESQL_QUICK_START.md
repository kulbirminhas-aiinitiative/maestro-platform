# PostgreSQL Integration - Quick Start

Get the PostgreSQL-backed DAG workflow system running in 5 minutes!

## 🚀 Quick Setup (Development - SQLite)

```bash
# 1. Run automated setup
./setup_database.sh sqlite

# 2. Start API server
USE_SQLITE=true python3 dag_api_server_postgres.py

# 3. Test the API
curl http://localhost:8000/health

# ✅ You're ready! API Docs: http://localhost:8000/docs
```

## 🐘 Quick Setup (Production - PostgreSQL)

```bash
# 1. Run automated setup (installs PostgreSQL if needed)
./setup_database.sh postgres

# 2. Source environment
source .env.database

# 3. Start API server
python3 dag_api_server_postgres.py

# 4. Test the API
curl http://localhost:8000/health

# ✅ You're ready! API Docs: http://localhost:8000/docs
```

## 📊 What's Included

### Database Package (`database/`)

```
database/
├── __init__.py          # Package exports
├── models.py           # SQLAlchemy ORM models
├── config.py           # Database engine & connections
├── repository.py       # Data access layer
└── workflow_store.py   # Context persistence (drop-in replacement)
```

### API Server

- **Original**: `dag_api_server.py` (in-memory)
- **New**: `dag_api_server_postgres.py` (PostgreSQL-backed)

### Setup & Migration

- `setup_database.sh` - Automated setup script
- `alembic/` - Database migrations
- `.env.database` - Environment configuration

### Documentation

- `POSTGRESQL_INTEGRATION_GUIDE.md` - Complete guide (18 pages)
- `POSTGRESQL_QUICK_START.md` - This file
- `database/README` - Package overview

## 🧪 Test It Out

### 1. Execute a Workflow

```bash
# Create and execute dog marketplace workflow
curl -X POST http://localhost:8000/api/workflows/sdlc_parallel/execute \
  -H 'Content-Type: application/json' \
  -d '{
    "requirement": "Build a marketplace for dog products, sellers and buyers can interact"
  }'

# Response:
{
  "execution_id": "exec_sdlc_parallel_20251011_120000_abc123",
  "workflow_id": "sdlc_parallel",
  "status": "running",
  "started_at": "2025-10-11T12:00:00"
}
```

### 2. Check Execution Status

```bash
# Get execution status (replace with your execution_id)
curl http://localhost:8000/api/executions/exec_sdlc_parallel_20251011_120000_abc123

# Response:
{
  "execution_id": "exec_...",
  "workflow_id": "sdlc_parallel",
  "status": "running",
  "progress_percent": 33.3,
  "completed_nodes": 2,
  "total_nodes": 6,
  "node_states": [
    {
      "node_id": "requirements",
      "status": "completed",
      "duration": 532.5,
      "outputs": {"artifacts": 6, "quality": 0.85}
    },
    {
      "node_id": "design",
      "status": "running",
      "attempt_count": 1
    }
  ]
}
```

### 3. List All Workflows

```bash
curl http://localhost:8000/api/workflows

# Response:
[
  {
    "workflow_id": "sdlc_parallel",
    "name": "SDLC Parallel Workflow",
    "type": "parallel",
    "nodes": 6,
    "edges": 7,
    "created_at": "2025-10-11T12:00:00"
  }
]
```

### 4. WebSocket Real-time Updates

```bash
# Install wscat
npm install -g wscat

# Connect to WebSocket
wscat -c ws://localhost:8000/ws/workflow/sdlc_parallel

# You'll receive real-time events:
{
  "type": "node_started",
  "execution_id": "exec_...",
  "node_id": "requirements",
  "timestamp": "2025-10-11T12:00:00"
}

{
  "type": "node_completed",
  "execution_id": "exec_...",
  "node_id": "requirements",
  "timestamp": "2025-10-11T12:09:00",
  "data": {"artifacts": 6, "quality": 0.85}
}
```

## 🗄️ Query the Database

### SQLite (Development)

```bash
# Connect to SQLite
sqlite3 maestro_workflows.db

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
```

### PostgreSQL (Production)

```bash
# Connect to PostgreSQL
psql -h localhost -U maestro -d maestro_workflows

# Same queries as above work in PostgreSQL
```

## 📈 Key Features

### 1. Persistence
- ✅ All workflow data persisted to database
- ✅ No data loss on server restart
- ✅ Full execution history

### 2. Recovery
- ✅ Resume failed workflows
- ✅ Workflow state recovery
- ✅ Retry logic with state preservation

### 3. Audit & Analytics
- ✅ Complete event logs
- ✅ Execution metrics
- ✅ Performance tracking
- ✅ Quality metrics

### 4. Scaling
- ✅ Multi-instance support (shared database)
- ✅ Horizontal scaling ready
- ✅ Connection pooling

## 🔧 Configuration Options

### SQLite (Development)

```bash
export USE_SQLITE=true
export SQLITE_PATH=maestro_workflows.db
```

### PostgreSQL (Production)

```bash
export POSTGRES_HOST=localhost
export POSTGRES_PORT=5432
export POSTGRES_DB=maestro_workflows
export POSTGRES_USER=maestro
export POSTGRES_PASSWORD=maestro_dev
export USE_SQLITE=false

# Connection pool
export DB_POOL_SIZE=10
export DB_MAX_OVERFLOW=20
export DB_POOL_TIMEOUT=30
export DB_POOL_RECYCLE=3600
```

## 🎯 Usage Patterns

### Pattern 1: Execute & Monitor

```bash
# 1. Execute workflow
EXEC_ID=$(curl -s -X POST http://localhost:8000/api/workflows/sdlc_parallel/execute \
  -H 'Content-Type: application/json' \
  -d '{"requirement": "Build todo app"}' | jq -r '.execution_id')

# 2. Monitor progress (every 5 seconds)
watch -n 5 "curl -s http://localhost:8000/api/executions/$EXEC_ID | jq '.progress_percent'"

# 3. Get final results
curl http://localhost:8000/api/executions/$EXEC_ID | jq
```

### Pattern 2: List & Resume

```python
from database import DatabaseWorkflowContextStore

store = DatabaseWorkflowContextStore()

# List all executions for a workflow
executions = store.list_executions(workflow_id="sdlc_parallel")

# Load execution context
context = store.load_context(executions[0])

# Resume from where it left off
from dag_executor import DAGExecutor
executor = DAGExecutor(workflow, context_store=store)
result = await executor.resume(context)
```

### Pattern 3: Query Analytics

```python
from database import get_db, RepositoryFactory

with get_db() as session:
    repos = RepositoryFactory(session)

    # Get all executions
    executions = repos.execution.list_by_workflow("sdlc_parallel")

    # Calculate success rate
    total = len(executions)
    completed = len([e for e in executions if e.status.value == "completed"])
    success_rate = (completed / total * 100) if total > 0 else 0

    print(f"Success rate: {success_rate:.1f}%")

    # Get average duration
    import statistics
    from datetime import datetime

    durations = [
        (e.completed_at - e.started_at).total_seconds()
        for e in executions
        if e.completed_at and e.started_at
    ]

    if durations:
        avg_duration = statistics.mean(durations)
        print(f"Average duration: {avg_duration:.1f}s")
```

## 📚 Next Steps

1. **Read Full Guide**: `POSTGRESQL_INTEGRATION_GUIDE.md`
2. **Frontend Integration**: `QUICK_START_FRONTEND_INTEGRATION.md`
3. **Production Deployment**: See guide section on production deployment
4. **Add Redis**: For WebSocket scaling (future enhancement)
5. **Monitoring**: Setup Prometheus metrics (future enhancement)

## 🐛 Troubleshooting

### Database connection failed

```bash
# Check if PostgreSQL is running
sudo systemctl status postgresql

# Check if SQLite file exists (development)
ls -lh maestro_workflows.db

# Test connection manually
python3 database/config.py health
```

### API server won't start

```bash
# Check if port 8000 is available
lsof -ti:8000

# Kill existing process if needed
kill $(lsof -ti:8000)

# Check logs for errors
python3 dag_api_server_postgres.py 2>&1 | tee api.log
```

### Workflow execution stuck

```bash
# Check execution status
curl http://localhost:8000/api/executions/<execution_id>

# Query database directly
sqlite3 maestro_workflows.db "SELECT * FROM workflow_executions WHERE id = '<execution_id>'"

# Check event logs
sqlite3 maestro_workflows.db "SELECT * FROM execution_events WHERE execution_id = '<execution_id>' ORDER BY timestamp DESC LIMIT 20"
```

## ✅ Verification Checklist

- [ ] Database initialized successfully
- [ ] API server starts without errors
- [ ] Health check returns "healthy"
- [ ] Can create workflow via API
- [ ] Can execute workflow
- [ ] Can query execution status
- [ ] WebSocket connection works
- [ ] Events are logged to database
- [ ] Can query database directly

## 📞 Support

- **Full Documentation**: `POSTGRESQL_INTEGRATION_GUIDE.md`
- **API Docs**: http://localhost:8000/docs
- **Database Schema**: `database/models.py`
- **Repository Layer**: `database/repository.py`

---

**Ready to scale! 🚀**
