# Database Credentials Quick Reference

## Current Setup (Development)

### PostgreSQL
```
Host:     localhost
Port:     5432
Database: maestro_workflows
User:     maestro
Password: maestro_dev
```

**Connection String:**
```
postgresql://maestro:maestro_dev@localhost:5432/maestro_workflows
```

**Test Connection:**
```bash
PGPASSWORD='maestro_dev' psql -h localhost -U maestro -d maestro_workflows -c "SELECT 1;"
```

---

### Redis
```
Host: localhost
Port: 6379
DB:   0
```

**Test Connection:**
```bash
redis6-cli ping
```

---

## Environment Variables

Copy these to your `.env` file:

```bash
# PostgreSQL
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=maestro_workflows
POSTGRES_USER=maestro
POSTGRES_PASSWORD=maestro_dev

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0

# DO NOT use SQLite fallback
USE_SQLITE=false
USE_MOCK_REDIS=false
```

---

## Setup Commands

### Create PostgreSQL User & Database
```bash
# Create user
sudo -u postgres psql -c "CREATE USER maestro WITH PASSWORD 'maestro_dev' CREATEDB;"

# Create database
sudo -u postgres psql -c "CREATE DATABASE maestro_workflows OWNER maestro;"

# Grant privileges
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE maestro_workflows TO maestro;"
```

### Verify Setup
```bash
# Check PostgreSQL
PGPASSWORD='maestro_dev' psql -h localhost -U maestro -d maestro_workflows -c "SELECT 1;"

# Check Redis
redis6-cli ping

# Check API Server
curl http://localhost:5001/health | python3 -m json.tool
```

---

## Production Setup (TODO)

**⚠️ WARNING**: Do NOT use these default credentials in production!

For production:
1. Generate strong passwords: `openssl rand -base64 32`
2. Use environment-specific `.env` files
3. Enable SSL/TLS for database connections
4. Set up proper authentication for Redis
5. Use secrets management (AWS Secrets Manager, HashiCorp Vault, etc.)

---

**Created**: 2025-10-12  
**Purpose**: Quick reference to avoid credential lookup struggles
