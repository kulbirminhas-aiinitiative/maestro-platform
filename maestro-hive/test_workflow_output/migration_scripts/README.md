# Database Migration Scripts

## Overview

This directory contains database migration scripts for the User Management API. Migrations are versioned and should be applied sequentially to ensure database schema consistency.

## Migration Philosophy

- **Sequential Versioning**: Migrations are numbered sequentially (001, 002, 003, etc.)
- **Idempotent**: Each migration can be safely re-run
- **Transactional**: All migrations use transactions for atomicity
- **Rollback Support**: Each migration has a corresponding rollback script
- **Documentation**: Each migration includes clear comments and metadata

## Directory Structure

```
migration_scripts/
├── README.md                      # This file
├── 001_initial_schema.sql        # Initial schema creation
├── rollback_001.sql              # Rollback for migration 001
└── seed_data.sql                 # Optional: Sample data for testing
```

## Migration Tracking

Migrations are tracked in the `schema_migrations` table:

```sql
CREATE TABLE schema_migrations (
    version VARCHAR(20) PRIMARY KEY,
    description TEXT NOT NULL,
    applied_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    applied_by VARCHAR(100) DEFAULT CURRENT_USER,
    execution_time_ms INTEGER,
    checksum VARCHAR(64)
);
```

## How to Apply Migrations

### Using psql Command Line

```bash
# Apply migration
psql -U username -d database_name -f migration_scripts/001_initial_schema.sql

# Verify migration
psql -U username -d database_name -c "SELECT * FROM schema_migrations ORDER BY version;"
```

### Using Environment Variables

```bash
# Set connection details
export PGHOST=localhost
export PGPORT=5432
export PGDATABASE=user_management
export PGUSER=admin
export PGPASSWORD=secret

# Apply migration
psql -f migration_scripts/001_initial_schema.sql
```

### Using Docker

```bash
# If running PostgreSQL in Docker
docker exec -i postgres_container psql -U username -d database_name < migration_scripts/001_initial_schema.sql
```

### Automated Migration Script

```bash
#!/bin/bash
# migrate.sh - Apply all pending migrations

DB_USER="admin"
DB_NAME="user_management"
DB_HOST="localhost"

for migration in migration_scripts/[0-9]*.sql; do
    echo "Applying migration: $migration"
    psql -h $DB_HOST -U $DB_USER -d $DB_NAME -f "$migration"
    if [ $? -eq 0 ]; then
        echo "✓ Migration applied successfully"
    else
        echo "✗ Migration failed"
        exit 1
    fi
done
```

## How to Rollback Migrations

### Rollback Single Migration

```bash
# Rollback most recent migration
psql -U username -d database_name -f migration_scripts/rollback_001.sql
```

### Rollback with Confirmation

```bash
#!/bin/bash
# rollback.sh - Rollback with safety check

read -p "WARNING: This will rollback migration 001. Continue? (yes/no) " confirm
if [ "$confirm" == "yes" ]; then
    psql -U username -d database_name -f migration_scripts/rollback_001.sql
    echo "Rollback completed"
else
    echo "Rollback cancelled"
fi
```

## Migration Best Practices

### 1. Always Use Transactions

```sql
BEGIN;
-- Your migration code here
COMMIT;
```

### 2. Make Migrations Idempotent

```sql
-- Use IF NOT EXISTS
CREATE TABLE IF NOT EXISTS users (...);

-- Use IF EXISTS for drops
DROP TABLE IF EXISTS old_table;

-- Use ON CONFLICT for inserts
INSERT INTO roles (name) VALUES ('admin')
ON CONFLICT (name) DO NOTHING;
```

### 3. Add Verification Steps

```sql
-- Verify expected state after migration
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM users LIMIT 1) THEN
        RAISE EXCEPTION 'Migration verification failed';
    END IF;
END $$;
```

### 4. Include Rollback Scripts

Every forward migration should have a corresponding rollback script that:
- Reverses all changes
- Maintains data integrity
- Includes warnings for destructive operations

### 5. Test Migrations

```bash
# Test on development database
psql -d dev_db -f 001_initial_schema.sql

# Test rollback
psql -d dev_db -f rollback_001.sql

# Re-apply to ensure idempotency
psql -d dev_db -f 001_initial_schema.sql
```

## Migration Workflow

### Development Environment

1. **Create Migration**: Write new migration file with next version number
2. **Test Locally**: Apply migration to local database
3. **Test Rollback**: Verify rollback works correctly
4. **Test Re-apply**: Ensure migration is idempotent
5. **Code Review**: Have migrations reviewed before merging

### Staging Environment

1. **Backup Database**: Always backup before migrations
2. **Apply Migration**: Run migration during maintenance window
3. **Verify**: Check application functionality
4. **Monitor**: Watch for errors or performance issues

### Production Environment

1. **Schedule Maintenance**: Plan migration during low-traffic period
2. **Backup Database**: Full backup before any changes
3. **Test on Copy**: Apply to production copy first
4. **Apply Migration**: Run with careful monitoring
5. **Health Check**: Verify all systems operational
6. **Keep Rollback Ready**: Be prepared to rollback if issues arise

## Version History

| Version | Date | Description | Applied By |
|---------|------|-------------|------------|
| 001 | 2025-10-12 | Initial schema creation | Database Specialist |

## Troubleshooting

### Migration Fails Midway

If a migration fails:

1. **Check Error Message**: Review PostgreSQL error output
2. **Check Migration Status**: `SELECT * FROM schema_migrations;`
3. **Manual Cleanup**: May need to manually clean partial changes
4. **Rollback**: Apply rollback script if available
5. **Fix and Retry**: Correct migration and re-apply

### Rollback Fails

If rollback fails:

1. **Review Dependencies**: Check for foreign key constraints
2. **Manual Cleanup**: May need to manually drop objects
3. **Force Drop**: Use CASCADE carefully if needed

```sql
DROP TABLE users CASCADE; -- Use with extreme caution
```

### Schema Drift

If schema differs from migrations:

1. **Export Current Schema**: `pg_dump --schema-only`
2. **Compare with Migrations**: Use diff tools
3. **Create Correction Migration**: Bring schema in sync
4. **Document Drift**: Update migration history

## Connection String Examples

### PostgreSQL Connection String

```
postgresql://username:password@localhost:5432/user_management
```

### Environment Variables

```bash
DATABASE_URL="postgresql://username:password@localhost:5432/user_management"
```

### Python (psycopg2)

```python
import psycopg2

conn = psycopg2.connect(
    host="localhost",
    port=5432,
    database="user_management",
    user="admin",
    password="secret"
)
```

### Node.js (pg)

```javascript
const { Pool } = require('pg');

const pool = new Pool({
  host: 'localhost',
  port: 5432,
  database: 'user_management',
  user: 'admin',
  password: 'secret'
});
```

## Security Notes

1. **Credentials**: Never commit passwords to version control
2. **Use .env Files**: Store sensitive data in environment variables
3. **Restrict Access**: Limit migration permissions to DBA role
4. **Audit Trail**: Log all migration activities
5. **Backup**: Always backup before migrations

## Support

For questions or issues with migrations:
- Review migration comments and documentation
- Check PostgreSQL logs: `/var/log/postgresql/`
- Contact Database Specialist team

---

**Last Updated**: 2025-10-12
**Maintainer**: Database Specialist
