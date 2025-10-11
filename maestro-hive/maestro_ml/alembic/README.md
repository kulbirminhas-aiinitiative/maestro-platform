# Database Migrations

Alembic database migrations for Maestro ML Platform.

## Setup

The database schema is defined in `maestro_ml/models/database.py`. Alembic tracks changes to this schema and generates migration scripts.

## Creating Migrations

### Auto-generate Migration

```bash
# Generate migration based on model changes
alembic revision --autogenerate -m "Add new table"
```

### Manual Migration

```bash
# Create empty migration script
alembic revision -m "Manual migration"

# Edit the generated file in alembic/versions/
```

## Running Migrations

### Upgrade to Latest

```bash
# Apply all pending migrations
alembic upgrade head
```

### Upgrade to Specific Revision

```bash
# Upgrade to specific revision
alembic upgrade <revision_id>

# Upgrade by +N versions
alembic upgrade +2
```

### Downgrade

```bash
# Downgrade by 1 version
alembic downgrade -1

# Downgrade to specific revision
alembic downgrade <revision_id>

# Downgrade all
alembic downgrade base
```

## Migration History

```bash
# Show current version
alembic current

# Show all revisions
alembic history

# Show verbose history
alembic history --verbose
```

## Initial Migration

For a fresh database:

```bash
# Create initial migration
alembic revision --autogenerate -m "Initial schema"

# Apply migration
alembic upgrade head
```

## Production Deployment

### Pre-deployment

```bash
# Check pending migrations
alembic current
alembic history

# Test migration in staging
alembic upgrade head --sql > migration.sql
# Review migration.sql
```

### Deployment

```bash
# Backup database first!
pg_dump -h <host> -U maestro maestro_ml > backup.sql

# Run migration
alembic upgrade head
```

### Rollback

```bash
# If something goes wrong
alembic downgrade -1

# Or restore from backup
psql -h <host> -U maestro maestro_ml < backup.sql
```

## Kubernetes Deployment

Run migrations as a Kubernetes Job before deploying the application:

```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: maestro-migrations
spec:
  template:
    spec:
      containers:
      - name: migrations
        image: maestro-ml/api:latest
        command: ["alembic", "upgrade", "head"]
        envFrom:
        - secretRef:
            name: maestro-secrets
      restartPolicy: OnFailure
```

## Troubleshooting

### Migration Conflicts

```bash
# If you have multiple heads (branches)
alembic merge <rev1> <rev2> -m "Merge migrations"
```

### Reset Migrations

```bash
# Drop alembic_version table
psql -h <host> -U maestro maestro_ml -c "DROP TABLE alembic_version;"

# Stamp current version without running migrations
alembic stamp head
```

### Check SQL Without Applying

```bash
# Generate SQL for migration
alembic upgrade head --sql
```
