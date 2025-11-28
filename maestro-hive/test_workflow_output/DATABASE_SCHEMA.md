# Database Schema Documentation

## User Management System
### Version: 1.0.0
### Design Phase

---

## Table of Contents
1. [Overview](#overview)
2. [Database Selection](#database-selection)
3. [Schema Design](#schema-design)
4. [Tables](#tables)
5. [Indexes](#indexes)
6. [Relationships](#relationships)
7. [Constraints](#constraints)
8. [Data Types](#data-types)
9. [Migration Strategy](#migration-strategy)
10. [Performance Considerations](#performance-considerations)

---

## Overview

This document describes the database schema design for the User Management REST API system. The schema is designed to support efficient CRUD operations, data integrity, and scalability.

### Design Principles
- **Normalization:** Schema follows 3NF (Third Normal Form) to reduce redundancy
- **Integrity:** Comprehensive constraints and foreign keys ensure data validity
- **Performance:** Strategic indexes optimize common query patterns
- **Scalability:** Design supports horizontal scaling and sharding
- **Auditability:** Timestamp fields track creation and modification

---

## Database Selection

### Recommended: PostgreSQL 14+

**Rationale:**
- ACID compliance for data integrity
- Excellent support for UUID primary keys
- Advanced indexing capabilities (B-tree, Hash, GiST, GIN)
- JSON/JSONB support for flexible data storage
- Strong community and ecosystem
- Proven scalability for user management systems

**Alternative Options:**
- **MySQL 8.0+:** Good alternative with similar features
- **MongoDB:** For document-based, schema-less requirements
- **Amazon Aurora:** For cloud-native deployments

---

## Schema Design

### Entity-Relationship Diagram

```
┌─────────────────────────────────────┐
│             users                    │
├─────────────────────────────────────┤
│ id (PK)                    UUID     │
│ username                   VARCHAR   │
│ email                      VARCHAR   │
│ password_hash              VARCHAR   │
│ first_name                 VARCHAR   │
│ last_name                  VARCHAR   │
│ phone                      VARCHAR   │
│ role                       VARCHAR   │
│ is_active                  BOOLEAN   │
│ email_verified             BOOLEAN   │
│ created_at                 TIMESTAMP │
│ updated_at                 TIMESTAMP │
│ last_login_at              TIMESTAMP │
│ deleted_at                 TIMESTAMP │
└─────────────────────────────────────┘
         │
         │ 1:N
         ▼
┌─────────────────────────────────────┐
│         user_sessions                │
├─────────────────────────────────────┤
│ id (PK)                    UUID     │
│ user_id (FK)               UUID     │
│ token_hash                 VARCHAR   │
│ ip_address                 VARCHAR   │
│ user_agent                 TEXT     │
│ expires_at                 TIMESTAMP │
│ created_at                 TIMESTAMP │
└─────────────────────────────────────┘
         ▲
         │
┌─────────────────────────────────────┐
│       audit_logs                     │
├─────────────────────────────────────┤
│ id (PK)                    UUID     │
│ user_id (FK)               UUID     │
│ action                     VARCHAR   │
│ entity_type                VARCHAR   │
│ entity_id                  UUID     │
│ old_values                 JSONB    │
│ new_values                 JSONB    │
│ ip_address                 VARCHAR   │
│ created_at                 TIMESTAMP │
└─────────────────────────────────────┘
```

---

## Tables

### 1. users

Primary table for storing user information.

**Table Definition:**

```sql
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username VARCHAR(50) NOT NULL UNIQUE,
    email VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    phone VARCHAR(20),
    role VARCHAR(20) NOT NULL DEFAULT 'user',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    email_verified BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_login_at TIMESTAMP WITH TIME ZONE,
    deleted_at TIMESTAMP WITH TIME ZONE,

    CONSTRAINT check_username_format CHECK (username ~ '^[a-zA-Z0-9_]{3,50}$'),
    CONSTRAINT check_email_format CHECK (email ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$'),
    CONSTRAINT check_role_values CHECK (role IN ('user', 'admin', 'moderator')),
    CONSTRAINT check_phone_format CHECK (phone IS NULL OR phone ~ '^\+?[0-9\-\(\) ]{7,20}$')
);
```

**Column Descriptions:**

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| id | UUID | No | gen_random_uuid() | Unique user identifier |
| username | VARCHAR(50) | No | - | Unique username (3-50 alphanumeric + underscore) |
| email | VARCHAR(255) | No | - | Unique email address |
| password_hash | VARCHAR(255) | No | - | Bcrypt hashed password |
| first_name | VARCHAR(100) | No | - | User's first name |
| last_name | VARCHAR(100) | No | - | User's last name |
| phone | VARCHAR(20) | Yes | NULL | Contact phone number |
| role | VARCHAR(20) | No | 'user' | User role (user/admin/moderator) |
| is_active | BOOLEAN | No | TRUE | Account active status |
| email_verified | BOOLEAN | No | FALSE | Email verification status |
| created_at | TIMESTAMP | No | CURRENT_TIMESTAMP | Record creation timestamp |
| updated_at | TIMESTAMP | No | CURRENT_TIMESTAMP | Last update timestamp |
| last_login_at | TIMESTAMP | Yes | NULL | Last successful login |
| deleted_at | TIMESTAMP | Yes | NULL | Soft delete timestamp |

**Business Rules:**
- Username must be unique and follow format constraints
- Email must be unique and valid format
- Password must be hashed using bcrypt with cost factor 12
- Soft deletes preserve data integrity (deleted_at)
- Role values are restricted to predefined set

---

### 2. user_sessions

Stores active user sessions for authentication and tracking.

**Table Definition:**

```sql
CREATE TABLE user_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    token_hash VARCHAR(255) NOT NULL UNIQUE,
    ip_address VARCHAR(45),
    user_agent TEXT,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_user_sessions_user_id
        FOREIGN KEY (user_id)
        REFERENCES users(id)
        ON DELETE CASCADE,

    CONSTRAINT check_expires_future
        CHECK (expires_at > created_at)
);
```

**Column Descriptions:**

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| id | UUID | No | gen_random_uuid() | Unique session identifier |
| user_id | UUID | No | - | Reference to users table |
| token_hash | VARCHAR(255) | No | - | Hashed authentication token |
| ip_address | VARCHAR(45) | Yes | NULL | Client IP address (IPv4/IPv6) |
| user_agent | TEXT | Yes | NULL | Client user agent string |
| expires_at | TIMESTAMP | No | - | Session expiration timestamp |
| created_at | TIMESTAMP | No | CURRENT_TIMESTAMP | Session creation timestamp |

**Business Rules:**
- Sessions are tied to users via foreign key
- Token hash must be unique
- Expired sessions should be cleaned up periodically
- CASCADE delete when user is deleted

---

### 3. audit_logs

Tracks all changes to user data for compliance and debugging.

**Table Definition:**

```sql
CREATE TABLE audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID,
    action VARCHAR(50) NOT NULL,
    entity_type VARCHAR(50) NOT NULL,
    entity_id UUID,
    old_values JSONB,
    new_values JSONB,
    ip_address VARCHAR(45),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_audit_logs_user_id
        FOREIGN KEY (user_id)
        REFERENCES users(id)
        ON DELETE SET NULL,

    CONSTRAINT check_action_values
        CHECK (action IN ('CREATE', 'UPDATE', 'DELETE', 'LOGIN', 'LOGOUT', 'PASSWORD_CHANGE'))
);
```

**Column Descriptions:**

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| id | UUID | No | gen_random_uuid() | Unique audit log identifier |
| user_id | UUID | Yes | NULL | User who performed the action |
| action | VARCHAR(50) | No | - | Type of action performed |
| entity_type | VARCHAR(50) | No | - | Type of entity modified |
| entity_id | UUID | Yes | NULL | ID of the modified entity |
| old_values | JSONB | Yes | NULL | Previous values (JSON) |
| new_values | JSONB | Yes | NULL | New values (JSON) |
| ip_address | VARCHAR(45) | Yes | NULL | Client IP address |
| created_at | TIMESTAMP | No | CURRENT_TIMESTAMP | Audit log creation timestamp |

**Business Rules:**
- All user modifications should generate audit logs
- Old/new values stored as JSON for flexibility
- SET NULL on user deletion to preserve audit trail
- Immutable records (no updates or deletes)

---

## Indexes

### Primary Indexes

All primary keys automatically create unique B-tree indexes.

### Secondary Indexes

```sql
-- Users table indexes
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_username ON users(username);
CREATE INDEX idx_users_role ON users(role);
CREATE INDEX idx_users_is_active ON users(is_active) WHERE is_active = TRUE;
CREATE INDEX idx_users_created_at ON users(created_at DESC);
CREATE INDEX idx_users_deleted_at ON users(deleted_at) WHERE deleted_at IS NULL;

-- Composite index for common queries
CREATE INDEX idx_users_active_role ON users(is_active, role)
    WHERE deleted_at IS NULL;

-- User sessions indexes
CREATE INDEX idx_user_sessions_user_id ON user_sessions(user_id);
CREATE INDEX idx_user_sessions_token_hash ON user_sessions(token_hash);
CREATE INDEX idx_user_sessions_expires_at ON user_sessions(expires_at);
CREATE INDEX idx_user_sessions_active ON user_sessions(user_id, expires_at)
    WHERE expires_at > CURRENT_TIMESTAMP;

-- Audit logs indexes
CREATE INDEX idx_audit_logs_user_id ON audit_logs(user_id);
CREATE INDEX idx_audit_logs_entity ON audit_logs(entity_type, entity_id);
CREATE INDEX idx_audit_logs_action ON audit_logs(action);
CREATE INDEX idx_audit_logs_created_at ON audit_logs(created_at DESC);

-- GIN index for JSONB fields
CREATE INDEX idx_audit_logs_new_values ON audit_logs USING GIN (new_values);
CREATE INDEX idx_audit_logs_old_values ON audit_logs USING GIN (old_values);
```

### Index Strategy
- **B-tree indexes:** For equality and range queries
- **Partial indexes:** Optimize queries with WHERE clauses
- **Composite indexes:** Support multi-column queries
- **GIN indexes:** Enable efficient JSONB queries

---

## Relationships

### Foreign Key Relationships

```
users (1) ──────< (N) user_sessions
  │
  │ (0..1)
  │
  └──────< (N) audit_logs
```

**Relationship Details:**

1. **users → user_sessions** (One-to-Many)
   - One user can have multiple active sessions
   - Cascade delete: Remove sessions when user is deleted

2. **users → audit_logs** (One-to-Many)
   - One user can have multiple audit log entries
   - Set null on delete: Preserve audit trail

---

## Constraints

### Check Constraints

```sql
-- Username format: alphanumeric and underscore, 3-50 chars
CONSTRAINT check_username_format
    CHECK (username ~ '^[a-zA-Z0-9_]{3,50}$')

-- Email format validation
CONSTRAINT check_email_format
    CHECK (email ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$')

-- Role enumeration
CONSTRAINT check_role_values
    CHECK (role IN ('user', 'admin', 'moderator'))

-- Phone format: optional international format
CONSTRAINT check_phone_format
    CHECK (phone IS NULL OR phone ~ '^\+?[0-9\-\(\) ]{7,20}$')

-- Session expiration must be in future
CONSTRAINT check_expires_future
    CHECK (expires_at > created_at)

-- Audit log action enumeration
CONSTRAINT check_action_values
    CHECK (action IN ('CREATE', 'UPDATE', 'DELETE', 'LOGIN', 'LOGOUT', 'PASSWORD_CHANGE'))
```

### Unique Constraints

```sql
-- Unique username
ALTER TABLE users ADD CONSTRAINT unique_username UNIQUE (username);

-- Unique email
ALTER TABLE users ADD CONSTRAINT unique_email UNIQUE (email);

-- Unique session token
ALTER TABLE user_sessions ADD CONSTRAINT unique_token_hash UNIQUE (token_hash);
```

---

## Data Types

### UUID vs Integer for Primary Keys

**Choice: UUID**

**Advantages:**
- Globally unique across distributed systems
- No sequential enumeration (security)
- Enables offline ID generation
- Simplifies data merging and replication

**Disadvantages:**
- Larger storage (16 bytes vs 4-8 bytes)
- Slightly slower joins
- Less human-readable

### Timestamp Storage

**Choice: TIMESTAMP WITH TIME ZONE**

**Rationale:**
- Stores absolute point in time
- Automatic timezone conversion
- Prevents timezone-related bugs
- Essential for global applications

### Password Storage

**Choice: Bcrypt with cost factor 12**

**Security Considerations:**
- One-way hashing (irreversible)
- Built-in salt
- Adaptive cost factor
- Industry standard

---

## Migration Strategy

### Initial Migration

```sql
-- Migration: 001_create_users_table.sql
CREATE TABLE users (
    -- Table definition here
);

-- Migration: 002_create_user_sessions_table.sql
CREATE TABLE user_sessions (
    -- Table definition here
);

-- Migration: 003_create_audit_logs_table.sql
CREATE TABLE audit_logs (
    -- Table definition here
);

-- Migration: 004_create_indexes.sql
-- All index definitions here
```

### Migration Tools

**Recommended:** Alembic (Python) or Flyway (Java)

**Migration Best Practices:**
- Versioned migrations with timestamps
- Rollback scripts for each migration
- Test migrations on staging before production
- Incremental migrations (small, focused changes)
- Document breaking changes

---

## Performance Considerations

### Query Optimization

1. **Use appropriate indexes** for common query patterns
2. **Avoid SELECT *** - specify needed columns
3. **Use EXPLAIN ANALYZE** to profile queries
4. **Implement connection pooling** (recommended: 20-30 connections)

### Scalability Strategies

1. **Read Replicas**
   - Route read queries to replicas
   - Reduces load on primary database
   - Improves read performance

2. **Partitioning**
   - Partition audit_logs by created_at (monthly)
   - Improves query performance on large tables
   - Simplifies data archival

3. **Caching**
   - Cache frequently accessed user data (Redis)
   - Cache-aside pattern for reads
   - Write-through for updates

4. **Archival Strategy**
   - Archive audit_logs older than 2 years
   - Archive soft-deleted users after 1 year
   - Maintain separate archive database

### Monitoring Metrics

- **Query performance:** Average query time, slow query log
- **Connection pool:** Active connections, wait time
- **Table size:** Monitor growth, plan capacity
- **Index usage:** Identify unused indexes
- **Lock contention:** Monitor deadlocks and timeouts

---

## Maintenance Tasks

### Regular Maintenance

```sql
-- Clean up expired sessions (daily)
DELETE FROM user_sessions
WHERE expires_at < CURRENT_TIMESTAMP - INTERVAL '7 days';

-- Update statistics (weekly)
ANALYZE users;
ANALYZE user_sessions;
ANALYZE audit_logs;

-- Vacuum tables (weekly)
VACUUM ANALYZE users;
VACUUM ANALYZE user_sessions;

-- Archive old audit logs (monthly)
INSERT INTO audit_logs_archive
SELECT * FROM audit_logs
WHERE created_at < CURRENT_TIMESTAMP - INTERVAL '2 years';

DELETE FROM audit_logs
WHERE created_at < CURRENT_TIMESTAMP - INTERVAL '2 years';
```

---

## Backup and Recovery

### Backup Strategy

1. **Full Backup:** Daily at 2:00 AM UTC
2. **Incremental Backup:** Every 6 hours
3. **Point-in-Time Recovery:** Enabled with WAL archiving
4. **Retention:** 30 days online, 1 year archived

### Recovery Testing

- Monthly recovery drills
- Document recovery procedures
- Maintain recovery time objective (RTO): < 1 hour
- Maintain recovery point objective (RPO): < 15 minutes

---

## Security Considerations

### Database Security

1. **Access Control**
   - Principle of least privilege
   - Separate read-only and read-write roles
   - Application-specific database user

2. **Encryption**
   - Encryption at rest (full disk encryption)
   - Encryption in transit (SSL/TLS required)
   - Column-level encryption for sensitive data

3. **Audit Logging**
   - Log all schema changes
   - Log authentication attempts
   - Log privilege escalations

4. **SQL Injection Prevention**
   - Use parameterized queries only
   - Never concatenate user input into SQL
   - Input validation at application layer

---

## Appendix

### Sample Data

```sql
-- Insert sample users
INSERT INTO users (username, email, password_hash, first_name, last_name, role)
VALUES
    ('admin', 'admin@example.com', '$2b$12$...', 'Admin', 'User', 'admin'),
    ('john_doe', 'john@example.com', '$2b$12$...', 'John', 'Doe', 'user'),
    ('jane_smith', 'jane@example.com', '$2b$12$...', 'Jane', 'Smith', 'user');
```

### Useful Queries

```sql
-- Count active users by role
SELECT role, COUNT(*)
FROM users
WHERE is_active = TRUE AND deleted_at IS NULL
GROUP BY role;

-- Find users with active sessions
SELECT u.username, u.email, COUNT(s.id) as active_sessions
FROM users u
JOIN user_sessions s ON u.id = s.user_id
WHERE s.expires_at > CURRENT_TIMESTAMP
GROUP BY u.id, u.username, u.email;

-- Audit trail for specific user
SELECT action, entity_type, created_at
FROM audit_logs
WHERE user_id = 'user-uuid-here'
ORDER BY created_at DESC
LIMIT 50;
```

---

**Document Version:** 1.0.0
**Last Updated:** 2025-10-12
**Phase:** Design
**Database:** PostgreSQL 14+
**Status:** Draft
