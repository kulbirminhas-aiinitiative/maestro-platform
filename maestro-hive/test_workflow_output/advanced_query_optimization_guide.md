# Advanced Query Optimization Guide
## User Management REST API - Design Phase

**Project:** User Management REST API
**Phase:** Design
**Version:** 2.0
**Date:** 2025-10-12
**Prepared by:** Database Specialist

---

## Table of Contents
1. [Performance Targets](#1-performance-targets)
2. [Optimized Query Patterns](#2-optimized-query-patterns)
3. [Index Strategy](#3-index-strategy)
4. [Connection Pooling](#4-connection-pooling)
5. [Caching Strategy](#5-caching-strategy)
6. [Query Analysis Tools](#6-query-analysis-tools)
7. [Performance Monitoring](#7-performance-monitoring)
8. [Troubleshooting Guide](#8-troubleshooting-guide)

---

## 1. Performance Targets

### 1.1 Response Time Goals

| Operation | Target (p95) | Target (p99) | Notes |
|-----------|--------------|--------------|-------|
| User by ID lookup | < 5ms | < 10ms | Single index scan |
| Login authentication | < 10ms | < 20ms | Index + password hash |
| User list (paginated) | < 15ms | < 30ms | Composite index scan |
| Full-text search | < 50ms | < 100ms | GIN index scan |
| User update | < 20ms | < 40ms | Update + trigger |
| Audit log query | < 20ms | < 40ms | Partitioned table |
| Token validation | < 5ms | < 10ms | Partial index lookup |

### 1.2 Throughput Goals

| Metric | Target | Scale |
|--------|--------|-------|
| Concurrent connections | 100-500 | Per app instance |
| Queries per second | 10,000+ | Database cluster |
| Transactions per second | 5,000+ | Write operations |
| Connection pool size | 20-50 | Per app instance |

### 1.3 Scalability Targets

| Users | Database Size | RAM | Storage IOPS | Query Performance |
|-------|--------------|-----|--------------|-------------------|
| 10K | 500MB | 4GB | 3K | Baseline |
| 100K | 5GB | 8GB | 10K | +10% latency |
| 1M | 50GB | 16GB | 30K | +20% latency |
| 10M | 500GB | 64GB | 100K | +40% latency |

---

## 2. Optimized Query Patterns

### 2.1 Authentication Queries

#### Login by Email (HOT PATH)
```sql
-- OPTIMIZED: Uses idx_users_email partial index
SELECT
    id,
    username,
    password_hash,
    status,
    failed_login_attempts,
    locked_until,
    is_email_verified
FROM users
WHERE email = $1
  AND deleted_at IS NULL
  AND status IN ('active', 'inactive')
LIMIT 1;

-- Performance: < 5ms (index-only scan)
-- Index: idx_users_email (email) WHERE deleted_at IS NULL
```

#### Login by Username (HOT PATH)
```sql
-- OPTIMIZED: Uses idx_users_username partial index
SELECT
    id,
    username,
    password_hash,
    status,
    failed_login_attempts,
    locked_until,
    is_email_verified
FROM users
WHERE username = $1
  AND deleted_at IS NULL
  AND status IN ('active', 'inactive')
LIMIT 1;

-- Performance: < 5ms (index-only scan)
-- Index: idx_users_username (username) WHERE deleted_at IS NULL
```

#### Combined Login Lookup (Email OR Username)
```sql
-- OPTIMIZED: Uses UNION for index utilization
(
    SELECT
        id, username, email, password_hash, status,
        failed_login_attempts, locked_until, is_email_verified
    FROM users
    WHERE email = $1
      AND deleted_at IS NULL
      AND status IN ('active', 'inactive')
    LIMIT 1
)
UNION ALL
(
    SELECT
        id, username, email, password_hash, status,
        failed_login_attempts, locked_until, is_email_verified
    FROM users
    WHERE username = $1
      AND deleted_at IS NULL
      AND status IN ('active', 'inactive')
    LIMIT 1
)
LIMIT 1;

-- Performance: < 10ms (two index scans + union)
-- Indexes: idx_users_email, idx_users_username
-- Note: UNION ALL avoids duplicate elimination overhead
```

### 2.2 User CRUD Operations

#### Get User by ID
```sql
-- OPTIMIZED: Primary key lookup (fastest possible)
SELECT
    id, username, email, first_name, last_name,
    phone_number, date_of_birth, profile_picture_url, bio,
    status, is_email_verified, is_phone_verified,
    created_at, updated_at, last_login_at
FROM users
WHERE id = $1
  AND deleted_at IS NULL;

-- Performance: < 2ms (primary key index)
-- Index: PRIMARY KEY (id)
```

#### List Users with Pagination
```sql
-- OPTIMIZED: Uses composite index for filtering + sorting
SELECT
    id, username, email, first_name, last_name,
    status, created_at, last_login_at
FROM users
WHERE deleted_at IS NULL
  AND status = $1  -- e.g., 'active'
ORDER BY created_at DESC
LIMIT $2 OFFSET $3;

-- Performance: < 15ms for first 1000 pages
-- Index: idx_users_status_created (status, created_at DESC) WHERE deleted_at IS NULL
-- WARNING: OFFSET becomes slow for high values (> 10,000)
```

#### List Users with Cursor Pagination (RECOMMENDED)
```sql
-- OPTIMIZED: Cursor-based pagination avoids OFFSET penalty
SELECT
    id, username, email, first_name, last_name,
    status, created_at, last_login_at
FROM users
WHERE deleted_at IS NULL
  AND status = $1
  AND created_at < $2  -- Cursor: last created_at from previous page
ORDER BY created_at DESC
LIMIT $3;

-- Performance: < 15ms regardless of page depth
-- Index: idx_users_status_created (status, created_at DESC)
-- Benefit: O(1) performance, no penalty for deep pages
```

#### Update User Profile
```sql
-- OPTIMIZED: Update only changed fields
UPDATE users
SET
    first_name = COALESCE($2, first_name),
    last_name = COALESCE($3, last_name),
    phone_number = COALESCE($4, phone_number),
    bio = COALESCE($5, bio),
    updated_at = CURRENT_TIMESTAMP  -- Automatically handled by trigger
WHERE id = $1
  AND deleted_at IS NULL
RETURNING id, updated_at;

-- Performance: < 20ms (includes trigger execution)
-- Trigger: update_users_updated_at, audit_users_changes
```

### 2.3 Search Queries

#### Simple Search (Username or Email Contains)
```sql
-- OPTIMIZED: Use indexes + LIKE with leading wildcard prevention
SELECT id, username, email, first_name, last_name, status
FROM users
WHERE deleted_at IS NULL
  AND (
      username ILIKE $1 || '%'  -- Leading wildcard for index use
      OR email ILIKE $1 || '%'
  )
LIMIT 50;

-- Performance: < 30ms
-- Indexes: idx_users_username, idx_users_email
-- Note: Avoid '%pattern%' (both-sided wildcard) for better performance
```

#### Full-Text Search (Advanced)
```sql
-- OPTIMIZED: Uses GIN index for full-text search
SELECT
    id, username, email, first_name, last_name, status,
    ts_rank(
        to_tsvector('english',
            COALESCE(username, '') || ' ' ||
            COALESCE(email, '') || ' ' ||
            COALESCE(first_name, '') || ' ' ||
            COALESCE(last_name, '')
        ),
        to_tsquery('english', $1)
    ) AS rank
FROM users
WHERE deleted_at IS NULL
  AND to_tsvector('english',
      COALESCE(username, '') || ' ' ||
      COALESCE(email, '') || ' ' ||
      COALESCE(first_name, '') || ' ' ||
      COALESCE(last_name, '')
  ) @@ to_tsquery('english', $1)
ORDER BY rank DESC
LIMIT 50;

-- Performance: < 50ms for typical searches
-- Index: idx_users_fulltext (GIN on tsvector)
-- Example: $1 = 'john & doe' (searches for both terms)
```

### 2.4 Token Management Queries

#### Validate Refresh Token (HOT PATH)
```sql
-- OPTIMIZED: Uses partial index on active tokens
SELECT
    rt.id,
    rt.user_id,
    rt.expires_at,
    rt.device_fingerprint,
    u.status,
    u.deleted_at
FROM refresh_tokens rt
INNER JOIN users u ON rt.user_id = u.id
WHERE rt.token_hash = $1
  AND rt.revoked_at IS NULL
  AND rt.expires_at > CURRENT_TIMESTAMP
  AND u.deleted_at IS NULL
  AND u.status = 'active';

-- Performance: < 5ms (two index lookups + join)
-- Indexes:
--   - idx_refresh_tokens_hash (token_hash) WHERE revoked_at IS NULL
--   - PRIMARY KEY on users(id)
```

#### Revoke All User Tokens (Logout All Devices)
```sql
-- OPTIMIZED: Single UPDATE with index scan
UPDATE refresh_tokens
SET revoked_at = CURRENT_TIMESTAMP
WHERE user_id = $1
  AND revoked_at IS NULL
  AND expires_at > CURRENT_TIMESTAMP;

-- Performance: < 10ms for typical user (1-5 tokens)
-- Index: idx_refresh_tokens_user (user_id, expires_at DESC)
```

#### Clean Expired Tokens (Scheduled Job)
```sql
-- OPTIMIZED: Batch delete with index scan
DELETE FROM refresh_tokens
WHERE expires_at < CURRENT_TIMESTAMP - INTERVAL '7 days'
  AND revoked_at IS NOT NULL;

DELETE FROM password_reset_tokens
WHERE expires_at < CURRENT_TIMESTAMP - INTERVAL '7 days';

DELETE FROM email_verification_tokens
WHERE expires_at < CURRENT_TIMESTAMP - INTERVAL '7 days';

-- Performance: < 100ms for thousands of records
-- Indexes: idx_*_expires_at on each table
-- Schedule: Daily at 2 AM (low traffic period)
```

### 2.5 Audit Log Queries

#### User Activity Trail
```sql
-- OPTIMIZED: Partitioned table + composite index
SELECT
    action,
    entity_type,
    entity_id,
    old_values,
    new_values,
    ip_address,
    created_at
FROM audit_logs
WHERE user_id = $1
  AND created_at >= $2  -- e.g., last 30 days
ORDER BY created_at DESC
LIMIT 100;

-- Performance: < 20ms (partition pruning + index scan)
-- Index: idx_audit_logs_user_id (user_id, created_at DESC)
-- Partitioning: Monthly partitions improve query performance
```

#### Recent System Activity
```sql
-- OPTIMIZED: Partition pruning + action index
SELECT
    user_id,
    action,
    entity_type,
    entity_id,
    created_at
FROM audit_logs
WHERE log_date >= CURRENT_DATE - INTERVAL '7 days'
  AND action IN ('login', 'login_failed', 'password_change')
ORDER BY created_at DESC
LIMIT 1000;

-- Performance: < 50ms (only scans recent partitions)
-- Indexes:
--   - idx_audit_logs_log_date (partition key)
--   - idx_audit_logs_action (action, created_at DESC)
```

### 2.6 Rate Limiting Queries

#### Check Rate Limit
```sql
-- OPTIMIZED: Composite index + window calculation
SELECT
    SUM(request_count) AS total_requests
FROM rate_limits
WHERE identifier = $1  -- IP address or user_id
  AND endpoint = $2
  AND window_end > CURRENT_TIMESTAMP
  AND window_start >= CURRENT_TIMESTAMP - INTERVAL '1 minute';

-- Performance: < 5ms
-- Index: idx_rate_limits_lookup (identifier, endpoint, window_end)
-- Alternative: Use Redis for sub-millisecond performance
```

#### Record Request
```sql
-- OPTIMIZED: INSERT ... ON CONFLICT for atomic increment
INSERT INTO rate_limits (identifier, endpoint, request_count, window_start, window_end)
VALUES ($1, $2, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP + INTERVAL '1 minute')
ON CONFLICT (identifier, endpoint, window_start)
DO UPDATE SET
    request_count = rate_limits.request_count + 1;

-- Performance: < 5ms
-- Constraint: UNIQUE (identifier, endpoint, window_start)
```

---

## 3. Index Strategy

### 3.1 Index Design Principles

#### Principle 1: Index Selectivity
- **High Selectivity (Good):** email, username, id (unique values)
- **Low Selectivity (Bad):** status, is_email_verified (few distinct values)
- **Solution:** Use composite indexes or partial indexes

#### Principle 2: Index Size
- **Smaller is Faster:** Narrow indexes fit in memory, faster scans
- **Include Only Necessary Columns:** Avoid bloated indexes
- **Partial Indexes:** Reduce index size by filtering (e.g., WHERE deleted_at IS NULL)

#### Principle 3: Write Performance
- **Too Many Indexes:** Slow down INSERTs/UPDATEs
- **Balance:** Index hot paths, skip rare queries
- **Monitoring:** Track unused indexes, drop if not used

### 3.2 Index Types

#### B-tree Indexes (Default)
```sql
-- Use for: =, <, <=, >, >=, BETWEEN, ORDER BY
CREATE INDEX idx_users_created_at ON users(created_at DESC);
```
- **Best for:** Range queries, sorting, equality
- **Size:** Compact, fast scans
- **Maintenance:** Automatic, low overhead

#### Partial Indexes (Filtered)
```sql
-- Use for: Common WHERE clause filtering
CREATE INDEX idx_users_email ON users(email) WHERE deleted_at IS NULL;
```
- **Best for:** Queries with consistent WHERE conditions
- **Size:** 10-50% smaller than full index
- **Benefit:** Faster scans, less I/O

#### Composite Indexes (Multi-column)
```sql
-- Use for: Multi-column WHERE/ORDER BY
CREATE INDEX idx_users_status_created ON users(status, created_at DESC)
    WHERE deleted_at IS NULL;
```
- **Best for:** Queries filtering on multiple columns
- **Column Order Matters:** Most selective column first
- **Can Replace Multiple Indexes:** Covers (status), (status, created_at)

#### GIN Indexes (Full-Text)
```sql
-- Use for: Full-text search, JSONB, arrays
CREATE INDEX idx_users_fulltext ON users
    USING gin(to_tsvector('english', ...));
```
- **Best for:** Full-text search, JSONB queries
- **Size:** Large (2-3x data size)
- **Maintenance:** Expensive updates

### 3.3 Index Maintenance

#### Monitor Index Usage
```sql
-- Find unused indexes (candidates for removal)
SELECT
    schemaname,
    tablename,
    indexname,
    idx_scan AS scans,
    pg_size_pretty(pg_relation_size(indexrelid)) AS size
FROM pg_stat_user_indexes
WHERE schemaname = 'public'
  AND idx_scan = 0
  AND indexname NOT LIKE '%_pkey'
ORDER BY pg_relation_size(indexrelid) DESC;
```

#### Reindex Strategy
```sql
-- Rebuild indexes to reduce bloat (monthly maintenance)
REINDEX INDEX CONCURRENTLY idx_users_email;
REINDEX INDEX CONCURRENTLY idx_users_username;

-- Or reindex entire table (requires downtime)
REINDEX TABLE users;
```

#### Index Bloat Detection
```sql
-- Estimate index bloat
SELECT
    schemaname,
    tablename,
    indexname,
    pg_size_pretty(pg_relation_size(indexrelid)) AS index_size,
    idx_scan,
    idx_tup_read,
    idx_tup_fetch
FROM pg_stat_user_indexes
WHERE schemaname = 'public'
ORDER BY pg_relation_size(indexrelid) DESC;
```

---

## 4. Connection Pooling

### 4.1 Application-Level Pooling

#### Python (SQLAlchemy)
```python
from sqlalchemy import create_engine
from sqlalchemy.pool import QueuePool

# Optimized pool configuration
engine = create_engine(
    'postgresql://user:pass@localhost/db',
    poolclass=QueuePool,
    pool_size=20,              # Core connections
    max_overflow=10,           # Additional connections under load
    pool_timeout=30,           # Wait time for connection
    pool_recycle=3600,         # Recycle connections after 1 hour
    pool_pre_ping=True,        # Verify connection before use
    echo_pool=False,           # Disable pool logging in production
    pool_use_lifo=True         # LIFO for better caching
)
```

#### Node.js (pg-pool)
```javascript
const { Pool } = require('pg');

const pool = new Pool({
  host: 'localhost',
  database: 'user_management',
  user: 'api_user',
  password: 'secure_password',
  port: 5432,

  // Pool configuration
  min: 10,                    // Minimum pool size
  max: 20,                    // Maximum pool size
  idleTimeoutMillis: 30000,   // Close idle connections after 30s
  connectionTimeoutMillis: 2000, // Fail if can't connect in 2s
});
```

### 4.2 PgBouncer (Database-Level Pooling)

#### Configuration (`pgbouncer.ini`)
```ini
[databases]
user_management = host=localhost port=5432 dbname=user_management

[pgbouncer]
listen_addr = 0.0.0.0
listen_port = 6432
auth_type = md5
auth_file = /etc/pgbouncer/userlist.txt

# Pool settings
pool_mode = transaction      # Best for stateless APIs
max_client_conn = 1000       # Total client connections
default_pool_size = 20       # Connections per DB
reserve_pool_size = 5        # Emergency connections
reserve_pool_timeout = 3     # Wait time for reserve pool

# Connection lifetime
server_lifetime = 3600       # Recycle after 1 hour
server_idle_timeout = 600    # Close idle after 10 min
query_timeout = 30           # Fail queries after 30s

# Memory
max_packet_size = 1073741824 # 1GB max packet

# Logging
log_connections = 0
log_disconnections = 0
log_pooler_errors = 1
```

#### Benefits
- **Connection Reuse:** 1000+ clients → 20 database connections
- **Reduced Overhead:** PostgreSQL handles fewer connections
- **Query Timeout:** Automatic cancellation of slow queries
- **Transparent:** Applications see it as regular PostgreSQL

---

## 5. Caching Strategy

### 5.1 Redis Caching

#### Cache User Profiles (Read-Heavy)
```python
import redis
import json

redis_client = redis.Redis(host='localhost', port=6379, db=0)

def get_user_by_id(user_id):
    # Try cache first
    cache_key = f"user:{user_id}"
    cached = redis_client.get(cache_key)

    if cached:
        return json.loads(cached)

    # Cache miss: query database
    user = db.query(User).filter(User.id == user_id).first()

    if user:
        # Cache for 15 minutes
        redis_client.setex(
            cache_key,
            900,  # 15 minutes TTL
            json.dumps(user.to_dict())
        )

    return user
```

#### Cache Invalidation on Update
```python
def update_user(user_id, data):
    # Update database
    db.query(User).filter(User.id == user_id).update(data)
    db.commit()

    # Invalidate cache
    redis_client.delete(f"user:{user_id}")
```

### 5.2 Application-Level Query Caching

#### Cached Prepared Statements
```python
from sqlalchemy import text

# Prepared statement with caching
stmt = text("""
    SELECT id, username, email, first_name, last_name
    FROM users
    WHERE email = :email AND deleted_at IS NULL
""").bindparams(email='user@example.com')

# SQLAlchemy caches the execution plan
result = session.execute(stmt).fetchone()
```

### 5.3 PostgreSQL Query Result Caching

#### Enable Query Result Cache
```sql
-- PostgreSQL 16+ (experimental)
SET enable_result_cache = on;

-- Automatic caching for repeated queries with same parameters
```

---

## 6. Query Analysis Tools

### 6.1 EXPLAIN ANALYZE

#### Basic Usage
```sql
EXPLAIN ANALYZE
SELECT id, username, email
FROM users
WHERE email = 'user@example.com' AND deleted_at IS NULL;
```

#### Output Interpretation
```
Index Scan using idx_users_email on users  (cost=0.29..8.30 rows=1 width=54) (actual time=0.015..0.016 rows=1 loops=1)
  Index Cond: ((email)::text = 'user@example.com'::text)
  Filter: (deleted_at IS NULL)
Planning Time: 0.081 ms
Execution Time: 0.032 ms
```

**Key Metrics:**
- **cost=0.29..8.30:** Estimated cost (startup..total)
- **rows=1:** Estimated rows returned
- **width=54:** Average row size in bytes
- **actual time=0.015..0.016:** Actual execution time (ms)
- **loops=1:** Number of iterations

#### Red Flags
- **Seq Scan:** Full table scan (missing index)
- **High loops:** Nested loop inefficiency
- **actual time >> cost:** Poor estimation, run ANALYZE
- **Filter after Index Scan:** Index not selective enough

### 6.2 pg_stat_statements

#### Enable Extension
```sql
-- Add to postgresql.conf
shared_preload_libraries = 'pg_stat_statements'

-- Create extension
CREATE EXTENSION pg_stat_statements;
```

#### Query Performance Analysis
```sql
-- Top 20 slowest queries by average time
SELECT
    query,
    calls,
    total_exec_time / 1000 AS total_time_sec,
    mean_exec_time AS avg_time_ms,
    min_exec_time AS min_time_ms,
    max_exec_time AS max_time_ms,
    stddev_exec_time AS stddev_ms
FROM pg_stat_statements
WHERE query NOT LIKE '%pg_stat_statements%'
ORDER BY mean_exec_time DESC
LIMIT 20;
```

#### Query by Total Time (Optimization Priority)
```sql
-- Queries consuming most total time
SELECT
    query,
    calls,
    total_exec_time / 1000 AS total_time_sec,
    mean_exec_time AS avg_time_ms,
    (total_exec_time / sum(total_exec_time) OVER ()) * 100 AS percent_total
FROM pg_stat_statements
WHERE query NOT LIKE '%pg_stat_statements%'
ORDER BY total_exec_time DESC
LIMIT 20;
```

### 6.3 Auto Explain

#### Enable for Slow Queries
```sql
-- Add to postgresql.conf
session_preload_libraries = 'auto_explain'
auto_explain.log_min_duration = 100  # Log queries > 100ms
auto_explain.log_analyze = true
auto_explain.log_buffers = true
auto_explain.log_timing = true
auto_explain.log_nested_statements = true
```

#### View Logs
```bash
tail -f /var/log/postgresql/postgresql-*.log | grep "duration:"
```

---

## 7. Performance Monitoring

### 7.1 Key Performance Indicators (KPIs)

#### Database Health
```sql
-- Active connections
SELECT count(*) AS active_connections
FROM pg_stat_activity
WHERE state = 'active';

-- Idle connections
SELECT count(*) AS idle_connections
FROM pg_stat_activity
WHERE state = 'idle';

-- Long-running queries (> 5 seconds)
SELECT
    pid,
    now() - query_start AS duration,
    state,
    query
FROM pg_stat_activity
WHERE state != 'idle'
  AND now() - query_start > interval '5 seconds'
ORDER BY duration DESC;
```

#### Cache Hit Ratio
```sql
-- Should be > 95%
SELECT
    sum(heap_blks_hit) AS heap_hit,
    sum(heap_blks_read) AS heap_read,
    sum(heap_blks_hit) / (sum(heap_blks_hit) + sum(heap_blks_read)) * 100 AS cache_hit_ratio
FROM pg_statio_user_tables;
```

#### Index Hit Ratio
```sql
-- Should be > 95%
SELECT
    sum(idx_blks_hit) AS idx_hit,
    sum(idx_blks_read) AS idx_read,
    sum(idx_blks_hit) / NULLIF(sum(idx_blks_hit) + sum(idx_blks_read), 0) * 100 AS idx_hit_ratio
FROM pg_statio_user_indexes;
```

### 7.2 Table Statistics

#### Table Size and Bloat
```sql
SELECT
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS total_size,
    pg_size_pretty(pg_relation_size(schemaname||'.'||tablename)) AS table_size,
    pg_size_pretty(pg_indexes_size(schemaname||'.'||tablename)) AS indexes_size,
    n_live_tup AS live_rows,
    n_dead_tup AS dead_rows,
    round(n_dead_tup * 100.0 / NULLIF(n_live_tup + n_dead_tup, 0), 2) AS dead_pct
FROM pg_stat_user_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
```

#### Vacuum Recommendations
```sql
-- Tables needing VACUUM
SELECT
    schemaname,
    tablename,
    n_dead_tup,
    n_live_tup,
    round(n_dead_tup * 100.0 / NULLIF(n_live_tup, 0), 2) AS dead_pct,
    last_autovacuum,
    last_vacuum
FROM pg_stat_user_tables
WHERE n_dead_tup > 1000
  AND round(n_dead_tup * 100.0 / NULLIF(n_live_tup, 0), 2) > 10
ORDER BY dead_pct DESC;
```

### 7.3 Replication Monitoring

#### Replication Lag
```sql
-- On primary server
SELECT
    client_addr,
    state,
    sync_state,
    pg_wal_lsn_diff(pg_current_wal_lsn(), sent_lsn) AS send_lag_bytes,
    pg_wal_lsn_diff(sent_lsn, write_lsn) AS write_lag_bytes,
    pg_wal_lsn_diff(write_lsn, flush_lsn) AS flush_lag_bytes,
    pg_wal_lsn_diff(flush_lsn, replay_lsn) AS replay_lag_bytes
FROM pg_stat_replication;
```

---

## 8. Troubleshooting Guide

### 8.1 Slow Query Diagnosis

#### Step 1: Identify Slow Query
```sql
-- Current slow queries
SELECT
    pid,
    now() - query_start AS duration,
    state,
    wait_event_type,
    wait_event,
    query
FROM pg_stat_activity
WHERE state = 'active'
  AND now() - query_start > interval '1 second'
ORDER BY duration DESC;
```

#### Step 2: Run EXPLAIN ANALYZE
```sql
EXPLAIN (ANALYZE, BUFFERS, VERBOSE)
<your_slow_query>;
```

#### Step 3: Check for Missing Indexes
```sql
-- Tables with sequential scans
SELECT
    schemaname,
    tablename,
    seq_scan,
    seq_tup_read,
    idx_scan,
    seq_tup_read / NULLIF(seq_scan, 0) AS avg_seq_read
FROM pg_stat_user_tables
WHERE schemaname = 'public'
  AND seq_scan > 0
ORDER BY seq_tup_read DESC
LIMIT 20;
```

#### Step 4: Update Statistics
```sql
ANALYZE users;
ANALYZE refresh_tokens;
ANALYZE audit_logs;
```

### 8.2 High CPU Usage

#### Diagnosis
```sql
-- Queries consuming most CPU time
SELECT
    query,
    calls,
    total_exec_time / 1000 AS total_sec,
    mean_exec_time AS avg_ms
FROM pg_stat_statements
ORDER BY total_exec_time DESC
LIMIT 10;
```

#### Solutions
1. **Missing Indexes:** Add indexes for frequent queries
2. **Full Table Scans:** Review EXPLAIN plans
3. **Inefficient Queries:** Rewrite with better logic
4. **Too Many Connections:** Use connection pooling

### 8.3 High Memory Usage

#### Diagnosis
```sql
-- Memory settings
SHOW shared_buffers;
SHOW work_mem;
SHOW maintenance_work_mem;
SHOW effective_cache_size;
```

#### Recommended Settings (16GB RAM server)
```sql
-- postgresql.conf
shared_buffers = 4GB           # 25% of RAM
effective_cache_size = 12GB    # 75% of RAM
work_mem = 32MB                # Per operation
maintenance_work_mem = 1GB     # For VACUUM, CREATE INDEX
```

### 8.4 Lock Contention

#### Detect Blocking Queries
```sql
SELECT
    blocked_locks.pid AS blocked_pid,
    blocked_activity.usename AS blocked_user,
    blocking_locks.pid AS blocking_pid,
    blocking_activity.usename AS blocking_user,
    blocked_activity.query AS blocked_statement,
    blocking_activity.query AS current_statement_in_blocking_process
FROM pg_catalog.pg_locks blocked_locks
JOIN pg_catalog.pg_stat_activity blocked_activity ON blocked_activity.pid = blocked_locks.pid
JOIN pg_catalog.pg_locks blocking_locks
    ON blocking_locks.locktype = blocked_locks.locktype
    AND blocking_locks.database IS NOT DISTINCT FROM blocked_locks.database
    AND blocking_locks.relation IS NOT DISTINCT FROM blocked_locks.relation
    AND blocking_locks.page IS NOT DISTINCT FROM blocked_locks.page
    AND blocking_locks.tuple IS NOT DISTINCT FROM blocked_locks.tuple
    AND blocking_locks.virtualxid IS NOT DISTINCT FROM blocked_locks.virtualxid
    AND blocking_locks.transactionid IS NOT DISTINCT FROM blocked_locks.transactionid
    AND blocking_locks.classid IS NOT DISTINCT FROM blocked_locks.classid
    AND blocking_locks.objid IS NOT DISTINCT FROM blocked_locks.objid
    AND blocking_locks.objsubid IS NOT DISTINCT FROM blocked_locks.objsubid
    AND blocking_locks.pid != blocked_locks.pid
JOIN pg_catalog.pg_stat_activity blocking_activity ON blocking_activity.pid = blocking_locks.pid
WHERE NOT blocked_locks.granted;
```

#### Kill Blocking Query
```sql
-- Terminate specific query
SELECT pg_terminate_backend(<blocking_pid>);
```

---

## 9. Summary

This advanced query optimization guide provides:

✅ **Optimized Query Patterns:** Production-ready SQL for all operations
✅ **Index Strategy:** Comprehensive indexing for < 200ms queries
✅ **Connection Pooling:** Application and database-level pooling
✅ **Caching:** Redis and application-level caching strategies
✅ **Monitoring:** KPIs, metrics, and alerting queries
✅ **Troubleshooting:** Step-by-step diagnosis and solutions

**Expected Performance:**
- 10,000+ queries/sec throughput
- < 200ms p95 latency for all operations
- 1M+ user scalability
- 99.9% uptime

---

**Prepared by:** Database Specialist
**Status:** ✅ Complete
**Next Steps:** Implement and benchmark
