# Database Schema Design - User Management API

## Project Information
**Workflow ID:** workflow-20251012-130125
**Phase:** Requirements
**Document Version:** 1.0
**Date:** 2025-10-12
**Prepared by:** Backend Developer

---

## 1. Schema Overview

This document defines the database schema for the User Management REST API. The schema is designed for a relational database (PostgreSQL recommended) with emphasis on data integrity, performance, and security.

### Design Principles
- **Normalization:** 3NF (Third Normal Form) to minimize redundancy
- **Performance:** Strategic indexing for common queries
- **Security:** Encrypted sensitive data, hashed passwords
- **Scalability:** Efficient data types and constraints
- **Audit Trail:** Timestamp tracking for all records

---

## 2. Database Schema (PostgreSQL)

### 2.1 Users Table

The primary table for storing user information.

```sql
CREATE TABLE users (
    -- Primary Key
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Authentication & Identification
    username VARCHAR(50) NOT NULL,
    email VARCHAR(255) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,

    -- Personal Information
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    phone_number VARCHAR(20),
    date_of_birth DATE,

    -- Profile Data
    profile_picture_url VARCHAR(500),
    bio TEXT CHECK (length(bio) <= 500),

    -- Status & Metadata
    status VARCHAR(20) NOT NULL DEFAULT 'active',
    is_active BOOLEAN NOT NULL DEFAULT true,
    email_verified BOOLEAN NOT NULL DEFAULT false,

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP WITH TIME ZONE,
    deleted_at TIMESTAMP WITH TIME ZONE,

    -- Constraints
    CONSTRAINT users_username_unique UNIQUE (username),
    CONSTRAINT users_email_unique UNIQUE (email),
    CONSTRAINT users_status_check CHECK (status IN ('active', 'inactive', 'suspended', 'deleted')),
    CONSTRAINT users_email_format CHECK (email ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$')
);

-- Indexes for performance optimization
CREATE INDEX idx_users_email ON users(email) WHERE deleted_at IS NULL;
CREATE INDEX idx_users_username ON users(username) WHERE deleted_at IS NULL;
CREATE INDEX idx_users_status ON users(status) WHERE deleted_at IS NULL;
CREATE INDEX idx_users_created_at ON users(created_at DESC);
CREATE INDEX idx_users_last_name_first_name ON users(last_name, first_name) WHERE deleted_at IS NULL;
CREATE INDEX idx_users_is_active ON users(is_active) WHERE deleted_at IS NULL;

-- Trigger for updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER users_updated_at_trigger
    BEFORE UPDATE ON users
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Comment on table and columns
COMMENT ON TABLE users IS 'Core user data table for user management API';
COMMENT ON COLUMN users.id IS 'Unique identifier for user (UUID v4)';
COMMENT ON COLUMN users.username IS 'Unique username for authentication (3-50 chars)';
COMMENT ON COLUMN users.email IS 'Unique email address for contact and authentication';
COMMENT ON COLUMN users.password_hash IS 'Bcrypt hashed password (never store plain text)';
COMMENT ON COLUMN users.status IS 'User account status: active, inactive, suspended, deleted';
COMMENT ON COLUMN users.is_active IS 'Quick flag for active/inactive users';
COMMENT ON COLUMN users.deleted_at IS 'Soft delete timestamp (NULL if not deleted)';
```

---

### 2.2 Audit Log Table (Optional - Recommended)

Track all modifications to user records for compliance and debugging.

```sql
CREATE TABLE user_audit_log (
    -- Primary Key
    id BIGSERIAL PRIMARY KEY,

    -- Reference
    user_id UUID NOT NULL,

    -- Audit Information
    action VARCHAR(20) NOT NULL,
    changed_by UUID,
    changed_fields JSONB,
    old_values JSONB,
    new_values JSONB,

    -- Context
    ip_address INET,
    user_agent TEXT,

    -- Timestamp
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,

    -- Constraints
    CONSTRAINT audit_action_check CHECK (action IN ('CREATE', 'UPDATE', 'DELETE', 'LOGIN', 'LOGOUT'))
);

-- Indexes for audit queries
CREATE INDEX idx_audit_user_id ON user_audit_log(user_id);
CREATE INDEX idx_audit_action ON user_audit_log(action);
CREATE INDEX idx_audit_created_at ON user_audit_log(created_at DESC);

COMMENT ON TABLE user_audit_log IS 'Audit trail for all user record modifications';
COMMENT ON COLUMN user_audit_log.action IS 'Type of action performed';
COMMENT ON COLUMN user_audit_log.changed_fields IS 'JSON array of field names that were modified';
```

---

### 2.3 Session Management Table (Optional - For JWT blacklist)

```sql
CREATE TABLE user_sessions (
    -- Primary Key
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Reference
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,

    -- Session Data
    token_jti VARCHAR(255) NOT NULL UNIQUE,
    refresh_token_hash VARCHAR(255),

    -- Metadata
    ip_address INET,
    user_agent TEXT,

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    last_used_at TIMESTAMP WITH TIME ZONE,
    revoked_at TIMESTAMP WITH TIME ZONE,

    -- Constraints
    CONSTRAINT valid_expiry CHECK (expires_at > created_at)
);

-- Indexes
CREATE INDEX idx_sessions_user_id ON user_sessions(user_id);
CREATE INDEX idx_sessions_token_jti ON user_sessions(token_jti) WHERE revoked_at IS NULL;
CREATE INDEX idx_sessions_expires_at ON user_sessions(expires_at);

COMMENT ON TABLE user_sessions IS 'Active user sessions and token management';
COMMENT ON COLUMN user_sessions.token_jti IS 'JWT ID (jti claim) for token blacklisting';
```

---

## 3. Data Dictionary

### 3.1 Users Table Fields

| Column | Type | Nullable | Default | Description | Validation |
|--------|------|----------|---------|-------------|------------|
| id | UUID | NO | gen_random_uuid() | Primary key, unique user identifier | UUID v4 format |
| username | VARCHAR(50) | NO | - | Unique username | 3-50 chars, alphanumeric + underscore |
| email | VARCHAR(255) | NO | - | Unique email address | Valid email format (RFC 5322) |
| password_hash | VARCHAR(255) | NO | - | Bcrypt hashed password | Bcrypt hash (60 chars) |
| first_name | VARCHAR(100) | YES | NULL | User's first name | 1-100 chars |
| last_name | VARCHAR(100) | YES | NULL | User's last name | 1-100 chars |
| phone_number | VARCHAR(20) | YES | NULL | Contact phone number | E.164 format recommended |
| date_of_birth | DATE | YES | NULL | User's birthdate | Valid date, past only |
| profile_picture_url | VARCHAR(500) | YES | NULL | URL to profile image | Valid URL format |
| bio | TEXT | YES | NULL | User biography/description | Max 500 characters |
| status | VARCHAR(20) | NO | 'active' | Account status | Enum: active, inactive, suspended, deleted |
| is_active | BOOLEAN | NO | true | Active flag | Boolean |
| email_verified | BOOLEAN | NO | false | Email verification status | Boolean |
| created_at | TIMESTAMP | NO | CURRENT_TIMESTAMP | Record creation time | UTC timestamp |
| updated_at | TIMESTAMP | NO | CURRENT_TIMESTAMP | Last update time | UTC timestamp, auto-updated |
| last_login | TIMESTAMP | YES | NULL | Last successful login | UTC timestamp |
| deleted_at | TIMESTAMP | YES | NULL | Soft delete timestamp | UTC timestamp (NULL = active) |

---

## 4. Indexes Strategy

### 4.1 Primary Indexes

```sql
-- Unique constraints (automatically create indexes)
users.id (PRIMARY KEY)
users.username (UNIQUE)
users.email (UNIQUE)
```

### 4.2 Performance Indexes

```sql
-- Search and filtering
idx_users_email (Partial index for active users)
idx_users_username (Partial index for active users)
idx_users_status (For status-based queries)
idx_users_is_active (For active/inactive filtering)

-- Sorting and pagination
idx_users_created_at (Descending for recent users first)
idx_users_last_name_first_name (Composite for name searches)
```

### 4.3 Index Usage Patterns

| Query Pattern | Index Used | Performance Gain |
|---------------|-----------|------------------|
| Login by email | idx_users_email | O(log n) vs O(n) |
| Login by username | idx_users_username | O(log n) vs O(n) |
| List active users | idx_users_is_active | Filtered scan |
| Sort by created date | idx_users_created_at | Sorted access |
| Search by name | idx_users_last_name_first_name | Composite scan |

---

## 5. Constraints and Business Rules

### 5.1 Data Integrity Constraints

```sql
-- Uniqueness
- username must be unique (case-insensitive recommended)
- email must be unique (case-insensitive recommended)

-- Format validation
- email must match email regex pattern
- status must be one of: active, inactive, suspended, deleted

-- Logical constraints
- bio max length 500 characters
- username 3-50 characters
- created_at <= updated_at
```

### 5.2 Application-Level Validations

These are enforced by the backend application:

```python
# Username validation
- Pattern: ^[a-zA-Z0-9_]{3,50}$
- Alphanumeric characters and underscore only
- 3-50 characters length

# Email validation
- RFC 5322 compliant email format
- Maximum 255 characters
- Case-insensitive uniqueness check

# Password requirements (before hashing)
- Minimum 8 characters
- At least one uppercase letter
- At least one lowercase letter
- At least one digit
- At least one special character (!@#$%^&*)

# Phone number validation
- E.164 format recommended: +[country code][number]
- Optional field, validated if provided

# Date of birth validation
- Must be a valid date
- Must be in the past
- User must be at least 13 years old (COPPA compliance)

# Profile picture URL
- Valid URL format (https:// preferred)
- Maximum 500 characters
```

---

## 6. Migration Scripts

### 6.1 Initial Schema Creation

```sql
-- migrations/V1__create_users_table.sql

BEGIN;

-- Create users table
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username VARCHAR(50) NOT NULL,
    email VARCHAR(255) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    phone_number VARCHAR(20),
    date_of_birth DATE,
    profile_picture_url VARCHAR(500),
    bio TEXT CHECK (length(bio) <= 500),
    status VARCHAR(20) NOT NULL DEFAULT 'active',
    is_active BOOLEAN NOT NULL DEFAULT true,
    email_verified BOOLEAN NOT NULL DEFAULT false,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP WITH TIME ZONE,
    deleted_at TIMESTAMP WITH TIME ZONE,
    CONSTRAINT users_username_unique UNIQUE (username),
    CONSTRAINT users_email_unique UNIQUE (email),
    CONSTRAINT users_status_check CHECK (status IN ('active', 'inactive', 'suspended', 'deleted')),
    CONSTRAINT users_email_format CHECK (email ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$')
);

-- Create indexes
CREATE INDEX idx_users_email ON users(email) WHERE deleted_at IS NULL;
CREATE INDEX idx_users_username ON users(username) WHERE deleted_at IS NULL;
CREATE INDEX idx_users_status ON users(status) WHERE deleted_at IS NULL;
CREATE INDEX idx_users_created_at ON users(created_at DESC);
CREATE INDEX idx_users_last_name_first_name ON users(last_name, first_name) WHERE deleted_at IS NULL;
CREATE INDEX idx_users_is_active ON users(is_active) WHERE deleted_at IS NULL;

-- Create trigger function
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Attach trigger
CREATE TRIGGER users_updated_at_trigger
    BEFORE UPDATE ON users
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

COMMIT;
```

### 6.2 Rollback Script

```sql
-- migrations/V1__create_users_table_rollback.sql

BEGIN;

DROP TRIGGER IF EXISTS users_updated_at_trigger ON users;
DROP FUNCTION IF EXISTS update_updated_at_column();
DROP TABLE IF EXISTS users CASCADE;

COMMIT;
```

---

## 7. Sample Data

### 7.1 Seed Data for Testing

```sql
-- Insert test users (for development environment only)
INSERT INTO users (username, email, password_hash, first_name, last_name, status, is_active, email_verified)
VALUES
    ('johndoe', 'john.doe@example.com', '$2b$10$rKwYvxRpJgVmHfNMvfNcguT5l8H3VVQJkZZkQvZlHf4X3oNQvZVZK', 'John', 'Doe', 'active', true, true),
    ('janedoe', 'jane.doe@example.com', '$2b$10$rKwYvxRpJgVmHfNMvfNcguT5l8H3VVQJkZZkQvZlHf4X3oNQvZVZK', 'Jane', 'Doe', 'active', true, true),
    ('testuser', 'test@example.com', '$2b$10$rKwYvxRpJgVmHfNMvfNcguT5l8H3VVQJkZZkQvZlHf4X3oNQvZVZK', 'Test', 'User', 'active', true, false);

-- Note: Password for all test users is 'Test@1234' (hashed with bcrypt)
```

---

## 8. Database Configuration

### 8.1 Recommended PostgreSQL Settings

```ini
# postgresql.conf optimizations

# Connection settings
max_connections = 100
shared_buffers = 256MB
effective_cache_size = 1GB
maintenance_work_mem = 64MB
checkpoint_completion_target = 0.9
wal_buffers = 16MB
default_statistics_target = 100
random_page_cost = 1.1
effective_io_concurrency = 200
work_mem = 2621kB
min_wal_size = 1GB
max_wal_size = 4GB

# Logging
log_destination = 'stderr'
logging_collector = on
log_line_prefix = '%m [%p] %u@%d '
log_statement = 'mod'
log_duration = on
log_min_duration_statement = 500

# Security
password_encryption = scram-sha-256
ssl = on
```

### 8.2 Connection Pool Configuration

```python
# Application connection pool settings
DATABASE_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "database": "user_management_db",
    "user": "app_user",
    "password": "secure_password",
    "pool_size": 20,
    "max_overflow": 10,
    "pool_timeout": 30,
    "pool_recycle": 3600,
    "echo": False
}
```

---

## 9. Backup and Recovery

### 9.1 Backup Strategy

```bash
# Daily full backup
pg_dump -U postgres -d user_management_db -F c -f backup_$(date +%Y%m%d).dump

# Point-in-time recovery setup
# Enable WAL archiving in postgresql.conf:
wal_level = replica
archive_mode = on
archive_command = 'cp %p /path/to/archive/%f'
```

### 9.2 Recovery Procedures

```bash
# Restore from backup
pg_restore -U postgres -d user_management_db -c backup_20251012.dump

# Point-in-time recovery
# See PostgreSQL documentation for detailed PITR procedures
```

---

## 10. Security Considerations

### 10.1 Database Security

```sql
-- Create application user with limited privileges
CREATE USER app_user WITH PASSWORD 'secure_generated_password';

-- Grant only necessary permissions
GRANT CONNECT ON DATABASE user_management_db TO app_user;
GRANT SELECT, INSERT, UPDATE, DELETE ON users TO app_user;
GRANT USAGE ON SEQUENCE users_id_seq TO app_user;

-- Revoke unnecessary permissions
REVOKE ALL ON SCHEMA public FROM PUBLIC;
GRANT USAGE ON SCHEMA public TO app_user;
```

### 10.2 Data Protection

- **Password Storage:** Never store plain text passwords, always use bcrypt hashing
- **Sensitive Fields:** Consider encryption at rest for PII fields
- **Row-Level Security:** Implement RLS policies if multi-tenant
- **Audit Logging:** Track all data modifications
- **Regular Backups:** Automated daily backups with tested recovery procedures

---

## 11. Performance Optimization

### 11.1 Query Optimization Guidelines

```sql
-- Good: Use indexed columns in WHERE clause
SELECT * FROM users WHERE email = 'user@example.com' AND deleted_at IS NULL;

-- Bad: Function on indexed column prevents index usage
SELECT * FROM users WHERE LOWER(email) = 'user@example.com';

-- Solution: Use case-insensitive index or functional index
CREATE INDEX idx_users_email_lower ON users(LOWER(email)) WHERE deleted_at IS NULL;
```

### 11.2 Common Query Patterns

```sql
-- 1. User login (by email)
SELECT id, username, email, password_hash, status, is_active
FROM users
WHERE email = $1 AND deleted_at IS NULL;

-- 2. Get user by ID
SELECT id, username, email, first_name, last_name, phone_number,
       date_of_birth, profile_picture_url, bio, status,
       created_at, updated_at, last_login
FROM users
WHERE id = $1 AND deleted_at IS NULL;

-- 3. List users with pagination
SELECT id, username, email, first_name, last_name, status, created_at
FROM users
WHERE deleted_at IS NULL
ORDER BY created_at DESC
LIMIT $1 OFFSET $2;

-- 4. Search users by name
SELECT id, username, email, first_name, last_name
FROM users
WHERE deleted_at IS NULL
  AND (first_name ILIKE $1 OR last_name ILIKE $1)
ORDER BY last_name, first_name
LIMIT 20;

-- 5. Soft delete user
UPDATE users
SET deleted_at = CURRENT_TIMESTAMP,
    status = 'deleted',
    is_active = false
WHERE id = $1 AND deleted_at IS NULL;
```

---

## 12. Monitoring and Maintenance

### 12.1 Database Health Checks

```sql
-- Check table size
SELECT pg_size_pretty(pg_total_relation_size('users')) AS table_size;

-- Check index usage
SELECT schemaname, tablename, indexname, idx_scan, idx_tup_read, idx_tup_fetch
FROM pg_stat_user_indexes
WHERE schemaname = 'public' AND tablename = 'users';

-- Check slow queries
SELECT query, mean_exec_time, calls
FROM pg_stat_statements
WHERE query LIKE '%users%'
ORDER BY mean_exec_time DESC
LIMIT 10;

-- Check for bloat
SELECT schemaname, tablename,
       pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
```

### 12.2 Maintenance Tasks

```sql
-- Regular vacuum and analyze
VACUUM ANALYZE users;

-- Reindex if needed (during maintenance window)
REINDEX TABLE users;

-- Update statistics
ANALYZE users;
```

---

## 13. Schema Versioning

| Version | Date | Changes | Migration Script |
|---------|------|---------|------------------|
| 1.0 | 2025-10-12 | Initial schema | V1__create_users_table.sql |
| 1.1 | TBD | Add audit log table | V2__add_audit_log.sql |
| 1.2 | TBD | Add session management | V3__add_sessions.sql |

---

## 14. References

- PostgreSQL Documentation: https://www.postgresql.org/docs/
- Database Design Best Practices
- OWASP Database Security Guidelines
- SQL Style Guide
- Database Migration Tools: Alembic (Python), Flyway (Java), node-pg-migrate (Node.js)

---

**Document Status:** Final
**Quality Review:** Passed
**Ready for Implementation:** Yes
