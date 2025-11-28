# Query Optimization Guide
## User Management REST API

**Version:** 1.0.0
**Author:** Database Specialist
**Last Updated:** 2025-10-12

---

## Table of Contents
1. [Overview](#overview)
2. [Indexing Strategy](#indexing-strategy)
3. [Common Query Patterns](#common-query-patterns)
4. [Performance Optimization Techniques](#performance-optimization-techniques)
5. [Query Examples](#query-examples)
6. [Monitoring and Maintenance](#monitoring-and-maintenance)
7. [Troubleshooting](#troubleshooting)

---

## Overview

This document provides comprehensive guidance on optimizing database queries for the User Management API. Following these practices will ensure optimal performance, scalability, and maintainability.

### Performance Goals
- **Single record lookup**: < 5ms
- **Complex joins (3+ tables)**: < 10ms
- **List queries (paginated)**: < 15ms
- **Audit log queries**: < 20ms

---

## Indexing Strategy

### Primary Indexes (Already Created)

#### 1. Users Table
```sql
-- Email lookup (most common login method)
CREATE INDEX idx_users_email ON users(email) WHERE deleted_at IS NULL;

-- Username lookup (alternate login method)
CREATE INDEX idx_users_username ON users(username) WHERE deleted_at IS NULL;

-- Active user filtering
CREATE INDEX idx_users_is_active ON users(is_active) WHERE deleted_at IS NULL;

-- Sorting by registration date
CREATE INDEX idx_users_created_at ON users(created_at DESC);

-- Finding deleted users (soft delete queries)
CREATE INDEX idx_users_deleted_at ON users(deleted_at) WHERE deleted_at IS NOT NULL;
```

**Rationale:**
- **Partial indexes** (WHERE clause): Smaller index size, faster queries
- **DESC ordering**: Optimized for "newest first" queries
- **Compound conditions**: Index on both `is_active` and `deleted_at`

#### 2. User Roles Tables
```sql
-- Find all roles for a user
CREATE INDEX idx_user_roles_user_id ON user_roles(user_id);

-- Find all users with a specific role
CREATE INDEX idx_user_roles_role_id ON user_roles(role_id);
```

#### 3. Audit Log
```sql
-- User activity history
CREATE INDEX idx_audit_log_user_id ON user_audit_log(user_id);

-- Recent activity (time-series queries)
CREATE INDEX idx_audit_log_created_at ON user_audit_log(created_at DESC);

-- Filter by action type
CREATE INDEX idx_audit_log_action ON user_audit_log(action);

-- Entity-specific queries
CREATE INDEX idx_audit_log_entity ON user_audit_log(entity_type, entity_id);
```

#### 4. Token Tables
```sql
-- Active password reset tokens only
CREATE INDEX idx_password_reset_tokens_token
ON password_reset_tokens(token) WHERE used_at IS NULL;

-- Find tokens by user
CREATE INDEX idx_password_reset_tokens_user_id
ON password_reset_tokens(user_id);

-- Email verification tokens
CREATE INDEX idx_email_verification_tokens_token
ON email_verification_tokens(token) WHERE verified_at IS NULL;
```

### When to Add Additional Indexes

Consider adding indexes when:
1. **Query runs frequently** (> 100 times per hour)
2. **Query performance is slow** (> 50ms)
3. **Table scan detected** in EXPLAIN output
4. **Filter on specific columns** in WHERE clause

**Warning**: Too many indexes can slow down INSERT/UPDATE operations. Balance read vs write performance.

---

## Common Query Patterns

### 1. User Authentication (Login)

#### By Email (Most Common)
```sql
-- Optimized query using email index
SELECT
    id,
    username,
    email,
    password_hash,
    is_active,
    is_verified
FROM users
WHERE email = $1
  AND deleted_at IS NULL
  AND is_active = TRUE;
```

**Performance:** < 5ms (using `idx_users_email`)

#### By Username
```sql
SELECT
    id,
    username,
    email,
    password_hash,
    is_active,
    is_verified
FROM users
WHERE username = $1
  AND deleted_at IS NULL
  AND is_active = TRUE;
```

**Performance:** < 5ms (using `idx_users_username`)

### 2. Get User with Profile and Roles

#### Using Pre-built View (Recommended)
```sql
-- Optimized view with efficient joins
SELECT *
FROM v_users_complete
WHERE id = $1;
```

**Performance:** < 10ms (3 table joins optimized)

#### Manual Join (If Custom Fields Needed)
```sql
SELECT
    u.id,
    u.username,
    u.email,
    u.first_name,
    u.last_name,
    u.is_active,
    u.is_verified,
    p.bio,
    p.phone_number,
    p.timezone,
    ARRAY_AGG(r.name) AS roles
FROM users u
LEFT JOIN user_profiles p ON u.id = p.user_id
LEFT JOIN user_roles ur ON u.id = ur.user_id
LEFT JOIN roles r ON ur.role_id = r.id
WHERE u.id = $1
  AND u.deleted_at IS NULL
GROUP BY u.id, p.user_id, p.bio, p.phone_number, p.timezone;
```

**Tips:**
- Use LEFT JOIN for optional relationships
- GROUP BY required when using ARRAY_AGG
- Filter on u.deleted_at early for performance

### 3. List Users (Paginated)

#### Basic Pagination
```sql
SELECT
    id,
    username,
    email,
    first_name,
    last_name,
    created_at
FROM users
WHERE deleted_at IS NULL
ORDER BY created_at DESC
LIMIT $1 OFFSET $2;
```

**Performance:** < 15ms with proper indexes

#### Cursor-Based Pagination (Better for Large Datasets)
```sql
-- First page
SELECT id, username, email, created_at
FROM users
WHERE deleted_at IS NULL
ORDER BY created_at DESC, id DESC
LIMIT 20;

-- Next page (using last created_at and id from previous page)
SELECT id, username, email, created_at
FROM users
WHERE deleted_at IS NULL
  AND (created_at, id) < ($1, $2)  -- Last record from previous page
ORDER BY created_at DESC, id DESC
LIMIT 20;
```

**Benefits:**
- Consistent performance regardless of page number
- No OFFSET computation overhead
- Better for real-time data

### 4. Search Users

#### Simple Search (Single Field)
```sql
-- Case-insensitive username search
SELECT id, username, email, first_name, last_name
FROM users
WHERE username ILIKE $1 || '%'
  AND deleted_at IS NULL
LIMIT 20;
```

#### Full-Text Search (Multiple Fields)
```sql
-- Create text search configuration
ALTER TABLE users ADD COLUMN search_vector tsvector;

CREATE INDEX idx_users_search ON users USING GIN(search_vector);

-- Update trigger to maintain search vector
CREATE FUNCTION users_search_trigger() RETURNS trigger AS $$
BEGIN
    NEW.search_vector :=
        setweight(to_tsvector('english', COALESCE(NEW.username, '')), 'A') ||
        setweight(to_tsvector('english', COALESCE(NEW.email, '')), 'B') ||
        setweight(to_tsvector('english', COALESCE(NEW.first_name, '')), 'C') ||
        setweight(to_tsvector('english', COALESCE(NEW.last_name, '')), 'C');
    RETURN NEW;
END $$ LANGUAGE plpgsql;

CREATE TRIGGER users_search_update
    BEFORE INSERT OR UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION users_search_trigger();

-- Search query
SELECT id, username, email, first_name, last_name,
       ts_rank(search_vector, query) AS rank
FROM users, to_tsquery('english', $1) AS query
WHERE search_vector @@ query
  AND deleted_at IS NULL
ORDER BY rank DESC
LIMIT 20;
```

### 5. Filter Users by Role

```sql
-- Find all admins
SELECT u.id, u.username, u.email
FROM users u
INNER JOIN user_roles ur ON u.id = ur.user_id
INNER JOIN roles r ON ur.role_id = r.id
WHERE r.name = 'admin'
  AND u.deleted_at IS NULL
  AND u.is_active = TRUE;
```

**Performance:** < 10ms (using role indexes)

### 6. User Activity Audit Trail

```sql
-- Get recent activity for a user
SELECT
    action,
    entity_type,
    entity_id,
    old_values,
    new_values,
    ip_address,
    created_at
FROM user_audit_log
WHERE user_id = $1
ORDER BY created_at DESC
LIMIT 50;
```

**Performance:** < 20ms (using `idx_audit_log_user_id` and `idx_audit_log_created_at`)

---

## Performance Optimization Techniques

### 1. Use EXPLAIN ANALYZE

Always analyze query performance:

```sql
EXPLAIN ANALYZE
SELECT * FROM users WHERE email = 'test@example.com';
```

**Look for:**
- **Index Scan** (good) vs **Seq Scan** (bad for large tables)
- **Actual time**: Milliseconds spent
- **Rows**: Estimated vs actual
- **Buffers**: Shared hits vs reads

### 2. Avoid SELECT *

```sql
-- BAD: Fetches all columns (slower, more data transfer)
SELECT * FROM users WHERE id = $1;

-- GOOD: Only fetch needed columns
SELECT id, username, email FROM users WHERE id = $1;
```

**Benefits:**
- Reduced network transfer
- Less memory usage
- Better index-only scans

### 3. Use EXISTS Instead of COUNT

```sql
-- BAD: Counts all matching rows
SELECT COUNT(*) FROM users WHERE email = $1;

-- GOOD: Returns immediately after finding first match
SELECT EXISTS(SELECT 1 FROM users WHERE email = $1);
```

**Performance Gain:** Up to 100x faster for existence checks

### 4. Optimize JOIN Order

```sql
-- Optimize by filtering early
SELECT u.username, r.name
FROM users u
INNER JOIN user_roles ur ON u.id = ur.user_id
INNER JOIN roles r ON ur.role_id = r.id
WHERE u.is_active = TRUE  -- Filter first
  AND u.deleted_at IS NULL
  AND r.name = 'admin';
```

### 5. Use Prepared Statements

```python
# Python example with psycopg2
cursor.execute(
    "SELECT * FROM users WHERE email = %s",
    (email,)
)
```

**Benefits:**
- SQL injection prevention
- Query plan caching
- Better performance

### 6. Batch Operations

```sql
-- BAD: Multiple single inserts
INSERT INTO users (username, email) VALUES ('user1', 'email1');
INSERT INTO users (username, email) VALUES ('user2', 'email2');

-- GOOD: Single batch insert
INSERT INTO users (username, email) VALUES
    ('user1', 'email1'),
    ('user2', 'email2'),
    ('user3', 'email3');
```

**Performance Gain:** 10-100x faster depending on batch size

### 7. Connection Pooling

Use connection pooling to avoid connection overhead:

```python
# Python example with psycopg2 pool
from psycopg2 import pool

connection_pool = pool.SimpleConnectionPool(
    minconn=1,
    maxconn=20,
    host='localhost',
    database='user_management',
    user='admin'
)
```

### 8. Materialized Views for Heavy Queries

```sql
-- Create materialized view for expensive aggregations
CREATE MATERIALIZED VIEW user_statistics AS
SELECT
    DATE_TRUNC('day', created_at) AS date,
    COUNT(*) AS new_users,
    COUNT(*) FILTER (WHERE is_verified) AS verified_users
FROM users
WHERE deleted_at IS NULL
GROUP BY DATE_TRUNC('day', created_at);

CREATE INDEX idx_user_stats_date ON user_statistics(date);

-- Refresh periodically (e.g., nightly)
REFRESH MATERIALIZED VIEW CONCURRENTLY user_statistics;
```

---

## Query Examples

### Create Operations

#### Create User with Profile
```sql
-- Use transaction for atomicity
BEGIN;

INSERT INTO users (username, email, password_hash, first_name, last_name)
VALUES ($1, $2, $3, $4, $5)
RETURNING id;

INSERT INTO user_profiles (user_id, bio, timezone)
VALUES ($6, $7, $8);

COMMIT;
```

### Read Operations

#### Get User by ID (Complete)
```sql
SELECT * FROM v_users_complete WHERE id = $1;
```

#### List Active Users
```sql
SELECT * FROM v_active_users_summary
ORDER BY last_login_at DESC NULLS LAST
LIMIT 50;
```

#### Check Email Availability
```sql
SELECT EXISTS(
    SELECT 1 FROM users
    WHERE email = $1 AND deleted_at IS NULL
) AS email_taken;
```

### Update Operations

#### Update User Profile
```sql
UPDATE user_profiles
SET
    bio = $1,
    phone_number = $2,
    timezone = $3,
    updated_at = CURRENT_TIMESTAMP
WHERE user_id = $4
RETURNING *;
```

#### Update Last Login
```sql
UPDATE users
SET last_login_at = CURRENT_TIMESTAMP
WHERE id = $1
RETURNING last_login_at;
```

### Delete Operations

#### Soft Delete User
```sql
-- Use provided function
SELECT soft_delete_user($1);

-- Or manual update
UPDATE users
SET
    deleted_at = CURRENT_TIMESTAMP,
    is_active = FALSE
WHERE id = $1
RETURNING deleted_at;
```

#### Hard Delete (Rare - Compliance Only)
```sql
-- WARNING: Permanent deletion
DELETE FROM users WHERE id = $1;
-- Cascades to profiles, roles, tokens
```

---

## Monitoring and Maintenance

### Performance Monitoring Queries

#### 1. Slow Queries
```sql
-- Enable logging in postgresql.conf
-- log_min_duration_statement = 100  # Log queries > 100ms

-- View slow queries
SELECT
    query,
    mean_exec_time,
    calls,
    total_exec_time
FROM pg_stat_statements
ORDER BY mean_exec_time DESC
LIMIT 10;
```

#### 2. Index Usage Statistics
```sql
SELECT
    schemaname,
    tablename,
    indexname,
    idx_scan AS index_scans,
    idx_tup_read AS tuples_read,
    idx_tup_fetch AS tuples_fetched
FROM pg_stat_user_indexes
WHERE schemaname = 'public'
ORDER BY idx_scan ASC;
```

#### 3. Table Bloat
```sql
SELECT
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
```

### Regular Maintenance Tasks

#### Daily Tasks
```bash
#!/bin/bash
# Clean expired tokens
psql -d user_management -c "SELECT clean_expired_tokens();"
```

#### Weekly Tasks
```bash
#!/bin/bash
# Vacuum and analyze
psql -d user_management -c "VACUUM ANALYZE users;"
psql -d user_management -c "VACUUM ANALYZE user_audit_log;"
psql -d user_management -c "VACUUM ANALYZE user_profiles;"
```

#### Monthly Tasks
```bash
#!/bin/bash
# Full vacuum and reindex
psql -d user_management -c "VACUUM FULL ANALYZE users;"
psql -d user_management -c "REINDEX TABLE users;"
```

---

## Troubleshooting

### Problem: Slow Query Performance

**Diagnosis:**
```sql
EXPLAIN ANALYZE <your_query>;
```

**Solutions:**
1. Check if indexes are being used
2. Ensure statistics are up-to-date: `ANALYZE users;`
3. Consider adding missing indexes
4. Rewrite query to use indexes

### Problem: High Connection Count

**Diagnosis:**
```sql
SELECT COUNT(*) FROM pg_stat_activity;
```

**Solutions:**
1. Implement connection pooling (PgBouncer)
2. Reduce max_connections in postgresql.conf
3. Fix connection leaks in application code

### Problem: Table Bloat

**Diagnosis:**
```sql
SELECT
    pg_size_pretty(pg_total_relation_size('users')) AS total_size,
    pg_size_pretty(pg_relation_size('users')) AS table_size,
    pg_size_pretty(pg_total_relation_size('users') - pg_relation_size('users')) AS indexes_size;
```

**Solutions:**
1. Run VACUUM FULL during maintenance window
2. Enable autovacuum in postgresql.conf
3. Adjust autovacuum parameters

### Problem: Lock Contention

**Diagnosis:**
```sql
SELECT * FROM pg_locks WHERE NOT granted;
```

**Solutions:**
1. Use shorter transactions
2. Avoid long-running queries during peak times
3. Consider READ COMMITTED isolation level

---

## Best Practices Summary

1. **Always use indexes** for WHERE, JOIN, and ORDER BY columns
2. **Use partial indexes** to reduce index size
3. **Prefer EXISTS** over COUNT for existence checks
4. **Use prepared statements** for security and performance
5. **Batch operations** when inserting multiple rows
6. **Monitor query performance** regularly
7. **Keep statistics updated** with ANALYZE
8. **Use connection pooling** in production
9. **Paginate large result sets**
10. **Regular maintenance** (VACUUM, ANALYZE, REINDEX)

---

## Performance Benchmarks

### Expected Performance (Sample Dataset: 100K users)

| Operation | Expected Time | Index Used |
|-----------|--------------|------------|
| Login by email | < 5ms | idx_users_email |
| Get user + profile | < 10ms | PK joins |
| List users (page 1) | < 15ms | idx_users_created_at |
| Search users | < 20ms | Full-text search |
| Create user | < 10ms | None |
| Update user | < 8ms | PK |
| Soft delete | < 5ms | PK |
| Audit log query | < 20ms | idx_audit_log_user_id |

### Scalability Targets

- **100K users**: All operations < 20ms
- **1M users**: All operations < 50ms
- **10M users**: Consider partitioning audit log table

---

**Last Updated:** 2025-10-12
**Maintained By:** Database Specialist Team
