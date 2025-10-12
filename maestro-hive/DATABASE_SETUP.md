# Database Setup Guide

Complete guide for setting up and configuring the database infrastructure for Maestro DAG Workflow Platform.

## Table of Contents

1. [Overview](#overview)
2. [PostgreSQL Setup](#postgresql-setup)
3. [Redis Setup](#redis-setup)
4. [Environment Configuration](#environment-configuration)
5. [Verification](#verification)
6. [Troubleshooting](#troubleshooting)
7. [Production Considerations](#production-considerations)

---

## Overview

The Maestro DAG Workflow Platform uses two databases:

- **PostgreSQL**: Primary database for workflow persistence, execution tracking, node states, and event logs
- **Redis**: In-memory database for state management, caching, and real-time coordination

### Default Credentials

| Component | Value |
|-----------|-------|
| **PostgreSQL Host** | `localhost` |
| **PostgreSQL Port** | `5432` |
| **Database Name** | `maestro_workflows` |
| **Database User** | `maestro` |
| **Database Password** | `maestro_dev` |
| **Redis Host** | `localhost` |
| **Redis Port** | `6379` |
| **Redis DB** | `0` |

> **⚠️ IMPORTANT**: These are development credentials. Use strong passwords for production!

---

## PostgreSQL Setup

### 1. Check if PostgreSQL is Installed

```bash
# Check PostgreSQL service
sudo systemctl status postgresql

# Check PostgreSQL version
psql --version
```

### 2. Install PostgreSQL (if needed)

**Amazon Linux 2023:**
```bash
sudo dnf install postgresql15-server postgresql15
sudo postgresql-setup --initdb
sudo systemctl start postgresql
sudo systemctl enable postgresql
```

**Ubuntu/Debian:**
```bash
sudo apt-get update
sudo apt-get install postgresql postgresql-contrib
sudo systemctl start postgresql
sudo systemctl enable postgresql
```

### 3. Create Database User

```bash
# Create maestro user with CREATEDB privilege
sudo -u postgres psql -c "CREATE USER maestro WITH PASSWORD 'maestro_dev' CREATEDB;"

# Verify user was created
sudo -u postgres psql -c "\du"
```

Expected output:
```
                                   List of roles
   Role name   |                         Attributes
---------------+------------------------------------------------------------
 maestro       | Create DB
 postgres      | Superuser, Create role, Create DB, Replication, Bypass RLS
```

### 4. Create Database

```bash
# Create maestro_workflows database owned by maestro
sudo -u postgres psql -c "CREATE DATABASE maestro_workflows OWNER maestro;"

# Grant all privileges
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE maestro_workflows TO maestro;"

# Verify database was created
sudo -u postgres psql -c "\l" | grep maestro
```

Expected output:
```
 maestro_workflows | postgres | UTF8     | libc | en_US.UTF-8 | en_US.UTF-8
```

### 5. Test Connection

```bash
# Test connection with psql
PGPASSWORD='maestro_dev' psql -h localhost -U maestro -d maestro_workflows -c "SELECT 1;"

# Or using Python
python3 -c "
import psycopg2
conn = psycopg2.connect(
    host='localhost',
    port=5432,
    database='maestro_workflows',
    user='maestro',
    password='maestro_dev'
)
print('✅ PostgreSQL connection successful!')
conn.close()
"
```

### 6. Configure PostgreSQL Authentication (Optional)

Edit PostgreSQL authentication file if needed:

```bash
# Edit pg_hba.conf
sudo vi /var/lib/pgsql/data/pg_hba.conf

# Add this line for local connections (if not present):
# host    maestro_workflows    maestro    127.0.0.1/32    md5

# Reload PostgreSQL
sudo systemctl reload postgresql
```

---

## Redis Setup

### 1. Check if Redis is Installed

```bash
# Check Redis service
sudo systemctl status redis

# Check Redis CLI
redis-cli --version
# or
redis6-cli --version
```

### 2. Install Redis (if needed)

**Amazon Linux 2023:**
```bash
sudo dnf install redis6
sudo systemctl start redis6
sudo systemctl enable redis6
```

**Ubuntu/Debian:**
```bash
sudo apt-get update
sudo apt-get install redis-server
sudo systemctl start redis-server
sudo systemctl enable redis-server
```

### 3. Test Redis Connection

```bash
# Test with redis-cli
redis-cli ping
# or
redis6-cli ping

# Expected output: PONG

# Check Redis info
redis-cli info | grep version
```

### 4. Configure Redis (Optional)

Edit Redis configuration if needed:

```bash
# Edit redis.conf
sudo vi /etc/redis.conf
# or
sudo vi /etc/redis6.conf

# Key settings to verify:
# bind 127.0.0.1            # Listen on localhost
# port 6379                 # Default port
# maxmemory 256mb          # Set memory limit
# maxmemory-policy allkeys-lru  # Eviction policy

# Restart Redis after changes
sudo systemctl restart redis6
```

---

## Environment Configuration

### 1. Copy Environment Template

```bash
cd /home/ec2-user/projects/maestro-platform/maestro-hive

# Copy template to .env
cp .env.example .env

# Edit with your credentials (if different from defaults)
vi .env
```

### 2. Configure Database Credentials

Edit `.env` file:

```bash
# PostgreSQL Configuration
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=maestro_workflows
POSTGRES_USER=maestro
POSTGRES_PASSWORD=maestro_dev

# Redis Configuration
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0

# DO NOT use SQLite fallback
USE_SQLITE=false
```

### 3. Set Environment Variables (Optional)

Instead of `.env` file, you can set environment variables directly:

```bash
# Add to ~/.bashrc or ~/.bash_profile
export POSTGRES_HOST=localhost
export POSTGRES_PORT=5432
export POSTGRES_DB=maestro_workflows
export POSTGRES_USER=maestro
export POSTGRES_PASSWORD=maestro_dev

export REDIS_HOST=localhost
export REDIS_PORT=6379
export REDIS_DB=0

# Reload shell
source ~/.bashrc
```

---

## Verification

### 1. Run Database Health Check

```bash
cd /home/ec2-user/projects/maestro-platform/maestro-hive

# Test PostgreSQL connection
python3 database/config.py health
```

Expected output:
```
✅ Database is healthy
```

### 2. Start DAG API Server

```bash
# Start server
python3 dag_api_server_robust.py

# Check logs
tail -f dag_server_postgres.log
```

Expected output:
```
======================================================================
🚀 Starting Maestro DAG Workflow API Server
======================================================================
✅ PostgreSQL database initialized successfully
📊 Database: PostgreSQL
📚 API Docs: http://localhost:5001/docs
🔌 WebSocket: ws://localhost:5001/ws/workflow/{id}
======================================================================
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:5001
```

### 3. Test API Endpoints

```bash
# Test root endpoint
curl http://localhost:5001/ | python3 -m json.tool

# Test health endpoint
curl http://localhost:5001/health | python3 -m json.tool
```

Expected health response:
```json
{
    "status": "healthy",
    "database": {
        "connected": true,
        "type": "PostgreSQL"
    },
    "cache": {
        "workflows": 0,
        "websockets": 0
    },
    "tasks": {
        "background": 0,
        "active": 0
    }
}
```

### 4. Verify Database Tables

```bash
# Connect to PostgreSQL
PGPASSWORD='maestro_dev' psql -h localhost -U maestro -d maestro_workflows

# List tables
\dt

# Expected tables:
# - workflow_definitions
# - workflow_executions
# - workflow_node_states
# - workflow_events
# - (plus contract management tables)

# Exit psql
\q
```

---

## Troubleshooting

### PostgreSQL Connection Errors

#### Error: "password authentication failed for user maestro"

**Solution:**
```bash
# Verify user exists
sudo -u postgres psql -c "\du" | grep maestro

# If user doesn't exist, create it
sudo -u postgres psql -c "CREATE USER maestro WITH PASSWORD 'maestro_dev' CREATEDB;"

# Reset password if needed
sudo -u postgres psql -c "ALTER USER maestro WITH PASSWORD 'maestro_dev';"
```

#### Error: "database maestro_workflows does not exist"

**Solution:**
```bash
# Create database
sudo -u postgres psql -c "CREATE DATABASE maestro_workflows OWNER maestro;"

# Grant privileges
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE maestro_workflows TO maestro;"
```

#### Error: "could not connect to server"

**Solution:**
```bash
# Check PostgreSQL is running
sudo systemctl status postgresql

# Start if not running
sudo systemctl start postgresql

# Check if PostgreSQL is listening
sudo netstat -tlnp | grep 5432
```

### Redis Connection Errors

#### Error: "Connection refused"

**Solution:**
```bash
# Check Redis is running
sudo systemctl status redis6

# Start if not running
sudo systemctl start redis6

# Test connection
redis6-cli ping
```

#### Error: "NOAUTH Authentication required"

**Solution:**
```bash
# Add Redis password to .env
REDIS_PASSWORD=your-redis-password

# Or disable authentication in redis.conf
# requirepass ""
```

### Environment Variable Issues

#### Error: "Environment variables not loaded"

**Solution:**
```bash
# Verify .env file exists
ls -la .env

# Check file permissions
chmod 600 .env

# Manually load environment
set -a
source .env
set +a

# Or use python-dotenv in your code
pip install python-dotenv
```

---

## Production Considerations

### 1. Security Best Practices

**Use Strong Passwords:**
```bash
# Generate secure password
openssl rand -base64 32

# Update PostgreSQL password
sudo -u postgres psql -c "ALTER USER maestro WITH PASSWORD 'new-secure-password';"

# Update .env file
POSTGRES_PASSWORD=new-secure-password
```

**Enable SSL/TLS for PostgreSQL:**
```bash
# Edit postgresql.conf
ssl = on
ssl_cert_file = '/path/to/server.crt'
ssl_key_file = '/path/to/server.key'

# Update connection string
DATABASE_URL=postgresql://maestro:password@localhost:5432/maestro_workflows?sslmode=require
```

**Enable Redis Authentication:**
```bash
# Edit redis.conf
requirepass your-strong-redis-password

# Update .env
REDIS_PASSWORD=your-strong-redis-password
```

### 2. Database Backup

**PostgreSQL Backup:**
```bash
# Create backup
pg_dump -h localhost -U maestro -d maestro_workflows -F c -f maestro_workflows_backup.dump

# Restore from backup
pg_restore -h localhost -U maestro -d maestro_workflows maestro_workflows_backup.dump

# Automated daily backup (crontab)
0 2 * * * pg_dump -h localhost -U maestro -d maestro_workflows -F c -f /backups/maestro_$(date +\%Y\%m\%d).dump
```

**Redis Backup:**
```bash
# Create Redis snapshot
redis-cli SAVE

# Copy RDB file
cp /var/lib/redis/dump.rdb /backups/redis_backup_$(date +%Y%m%d).rdb

# Automated backup (crontab)
0 2 * * * redis-cli SAVE && cp /var/lib/redis/dump.rdb /backups/redis_$(date +\%Y\%m\%d).rdb
```

### 3. Monitoring

**PostgreSQL Monitoring:**
```bash
# Check active connections
PGPASSWORD='maestro_dev' psql -h localhost -U maestro -d maestro_workflows -c "SELECT count(*) FROM pg_stat_activity;"

# Check database size
PGPASSWORD='maestro_dev' psql -h localhost -U maestro -d maestro_workflows -c "SELECT pg_size_pretty(pg_database_size('maestro_workflows'));"

# Check slow queries
PGPASSWORD='maestro_dev' psql -h localhost -U maestro -d maestro_workflows -c "SELECT * FROM pg_stat_statements ORDER BY total_time DESC LIMIT 10;"
```

**Redis Monitoring:**
```bash
# Check memory usage
redis-cli INFO memory

# Check connected clients
redis-cli INFO clients

# Monitor commands in real-time
redis-cli MONITOR
```

### 4. Performance Tuning

**PostgreSQL Tuning:**
```bash
# Edit postgresql.conf
shared_buffers = 256MB
effective_cache_size = 1GB
maintenance_work_mem = 64MB
checkpoint_completion_target = 0.9
wal_buffers = 16MB
default_statistics_target = 100
random_page_cost = 1.1
effective_io_concurrency = 200
work_mem = 4MB
min_wal_size = 1GB
max_wal_size = 4GB

# Restart PostgreSQL
sudo systemctl restart postgresql
```

**Redis Tuning:**
```bash
# Edit redis.conf
maxmemory 1gb
maxmemory-policy allkeys-lru
maxmemory-samples 5
tcp-backlog 511
timeout 0
tcp-keepalive 300

# Restart Redis
sudo systemctl restart redis6
```

---

## Quick Reference

### PostgreSQL Commands

```bash
# Create user
sudo -u postgres psql -c "CREATE USER maestro WITH PASSWORD 'maestro_dev' CREATEDB;"

# Create database
sudo -u postgres psql -c "CREATE DATABASE maestro_workflows OWNER maestro;"

# Grant privileges
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE maestro_workflows TO maestro;"

# Test connection
PGPASSWORD='maestro_dev' psql -h localhost -U maestro -d maestro_workflows -c "SELECT 1;"

# List users
sudo -u postgres psql -c "\du"

# List databases
sudo -u postgres psql -c "\l"

# Drop database (BE CAREFUL!)
sudo -u postgres psql -c "DROP DATABASE maestro_workflows;"

# Drop user (BE CAREFUL!)
sudo -u postgres psql -c "DROP USER maestro;"
```

### Redis Commands

```bash
# Start Redis
sudo systemctl start redis6

# Stop Redis
sudo systemctl stop redis6

# Test connection
redis6-cli ping

# Check info
redis6-cli INFO

# Flush all data (BE CAREFUL!)
redis6-cli FLUSHALL

# Get all keys
redis6-cli KEYS '*'
```

### Environment Variables

```bash
# PostgreSQL
export POSTGRES_HOST=localhost
export POSTGRES_PORT=5432
export POSTGRES_DB=maestro_workflows
export POSTGRES_USER=maestro
export POSTGRES_PASSWORD=maestro_dev

# Redis
export REDIS_HOST=localhost
export REDIS_PORT=6379
export REDIS_DB=0

# Disable SQLite fallback
export USE_SQLITE=false
```

---

## Support

For issues or questions:

1. Check this documentation first
2. Review application logs: `tail -f dag_server_postgres.log`
3. Check PostgreSQL logs: `sudo tail -f /var/lib/pgsql/data/log/postgresql-*.log`
4. Check Redis logs: `sudo tail -f /var/log/redis/redis.log`

---

**Last Updated**: 2025-10-12
**Platform**: Maestro DAG Workflow Platform
**Version**: 2.1.0
