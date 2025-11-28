# Data Model Documentation
## User Management REST API

**Version:** 1.0.0
**Database:** PostgreSQL 14+
**Created:** 2025-10-12
**Author:** Database Specialist

---

## Table of Contents
1. [Overview](#overview)
2. [Entity Relationship Diagram](#entity-relationship-diagram)
3. [Data Entities](#data-entities)
4. [Relationships](#relationships)
5. [Data Types and Constraints](#data-types-and-constraints)
6. [Indexing Strategy](#indexing-strategy)
7. [Security Considerations](#security-considerations)

---

## Overview

This data model supports a comprehensive user management system with CRUD operations, role-based access control (RBAC), audit logging, and user verification workflows.

### Key Features
- **User Management**: Core user accounts with soft delete support
- **Profile Management**: Extended user information storage
- **Role-Based Access Control**: Flexible role assignment system
- **Audit Trail**: Complete history of user-related changes
- **Token Management**: Password reset and email verification flows
- **Soft Deletes**: Data retention for compliance and recovery

---

## Entity Relationship Diagram

```
┌─────────────────┐
│     USERS       │
│─────────────────│
│ PK: id (UUID)   │
│ UK: username    │
│ UK: email       │
│ password_hash   │
│ first_name      │
│ last_name       │
│ is_active       │
│ is_verified     │
│ created_at      │
│ updated_at      │
│ last_login_at   │
│ deleted_at      │
└────────┬────────┘
         │
         │ 1:1
         │
┌────────▼────────┐
│ USER_PROFILES   │
│─────────────────│
│PK,FK: user_id   │
│ bio             │
│ phone_number    │
│ date_of_birth   │
│ avatar_url      │
│ timezone        │
│ locale          │
│ created_at      │
│ updated_at      │
└─────────────────┘

         │
         │ M:N
         │
┌────────▼────────┐      ┌─────────────────┐
│   USER_ROLES    │──────│     ROLES       │
│─────────────────│  M:1 │─────────────────│
│PK,FK: user_id   │      │ PK: id (UUID)   │
│PK,FK: role_id   │      │ UK: name        │
│ assigned_at     │      │ description     │
│ assigned_by     │      │ created_at      │
└─────────────────┘      └─────────────────┘

┌─────────────────┐
│USER_AUDIT_LOG   │
│─────────────────│
│ PK: id (UUID)   │
│ FK: user_id     │
│ action          │
│ entity_type     │
│ entity_id       │
│ old_values      │
│ new_values      │
│ ip_address      │
│ user_agent      │
│ created_at      │
│ performed_by    │
└─────────────────┘

┌─────────────────────────┐
│PASSWORD_RESET_TOKENS    │
│─────────────────────────│
│ PK: id (UUID)           │
│ FK: user_id             │
│ UK: token               │
│ expires_at              │
│ used_at                 │
│ created_at              │
└─────────────────────────┘

┌─────────────────────────┐
│EMAIL_VERIFICATION_TOKENS│
│─────────────────────────│
│ PK: id (UUID)           │
│ FK: user_id             │
│ UK: token               │
│ expires_at              │
│ verified_at             │
│ created_at              │
└─────────────────────────┘
```

---

## Data Entities

### 1. Users (Core Entity)
**Purpose:** Store core user account information and authentication credentials.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PRIMARY KEY, DEFAULT uuid_generate_v4() | Unique user identifier |
| username | VARCHAR(50) | NOT NULL, UNIQUE, LENGTH >= 3 | User's unique username |
| email | VARCHAR(255) | NOT NULL, UNIQUE, Valid email format | User's email address |
| password_hash | VARCHAR(255) | NOT NULL | Hashed password (bcrypt/argon2) |
| first_name | VARCHAR(100) | NULL | User's first name |
| last_name | VARCHAR(100) | NULL | User's last name |
| is_active | BOOLEAN | DEFAULT TRUE | Account active status |
| is_verified | BOOLEAN | DEFAULT FALSE | Email verification status |
| created_at | TIMESTAMP WITH TIME ZONE | DEFAULT CURRENT_TIMESTAMP | Account creation timestamp |
| updated_at | TIMESTAMP WITH TIME ZONE | DEFAULT CURRENT_TIMESTAMP | Last update timestamp |
| last_login_at | TIMESTAMP WITH TIME ZONE | NULL | Last successful login |
| deleted_at | TIMESTAMP WITH TIME ZONE | NULL | Soft delete timestamp |

**Business Rules:**
- Username must be at least 3 characters
- Email must match standard email format
- Soft delete: deleted_at != NULL indicates deleted user
- Users cannot be hard deleted (compliance requirement)

### 2. User Profiles
**Purpose:** Store extended user information separate from core authentication data.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| user_id | UUID | PRIMARY KEY, FOREIGN KEY → users(id) | Reference to user |
| bio | TEXT | NULL | User biography/description |
| phone_number | VARCHAR(20) | NULL | Contact phone number |
| date_of_birth | DATE | NULL | User's date of birth |
| avatar_url | VARCHAR(500) | NULL | Profile picture URL |
| timezone | VARCHAR(50) | DEFAULT 'UTC' | User's timezone |
| locale | VARCHAR(10) | DEFAULT 'en_US' | User's locale preference |
| created_at | TIMESTAMP WITH TIME ZONE | DEFAULT CURRENT_TIMESTAMP | Profile creation timestamp |
| updated_at | TIMESTAMP WITH TIME ZONE | DEFAULT CURRENT_TIMESTAMP | Last update timestamp |

**Business Rules:**
- One-to-one relationship with users
- Cascade delete with parent user
- Profile is optional (can be created later)

### 3. Roles
**Purpose:** Define system roles for access control.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PRIMARY KEY, DEFAULT uuid_generate_v4() | Unique role identifier |
| name | VARCHAR(50) | NOT NULL, UNIQUE, LOWERCASE | Role name (lowercase) |
| description | TEXT | NULL | Role description |
| created_at | TIMESTAMP WITH TIME ZONE | DEFAULT CURRENT_TIMESTAMP | Role creation timestamp |

**Default Roles:**
- `admin`: Full system access
- `user`: Standard user permissions
- `moderator`: Content and user management
- `guest`: Read-only access

### 4. User Roles (Junction Table)
**Purpose:** Many-to-many relationship between users and roles.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| user_id | UUID | PRIMARY KEY, FOREIGN KEY → users(id) | Reference to user |
| role_id | UUID | PRIMARY KEY, FOREIGN KEY → roles(id) | Reference to role |
| assigned_at | TIMESTAMP WITH TIME ZONE | DEFAULT CURRENT_TIMESTAMP | Role assignment timestamp |
| assigned_by | UUID | FOREIGN KEY → users(id) | User who assigned the role |

**Business Rules:**
- Composite primary key (user_id, role_id)
- Users can have multiple roles
- Roles can be assigned to multiple users

### 5. User Audit Log
**Purpose:** Track all user-related changes for compliance and security.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PRIMARY KEY, DEFAULT uuid_generate_v4() | Unique audit entry ID |
| user_id | UUID | FOREIGN KEY → users(id) | Affected user |
| action | VARCHAR(50) | NOT NULL | Action performed (CREATE, UPDATE, DELETE) |
| entity_type | VARCHAR(50) | NOT NULL | Type of entity changed |
| entity_id | UUID | NULL | ID of affected entity |
| old_values | JSONB | NULL | Previous values (JSON) |
| new_values | JSONB | NULL | New values (JSON) |
| ip_address | INET | NULL | Client IP address |
| user_agent | TEXT | NULL | Client user agent |
| created_at | TIMESTAMP WITH TIME ZONE | DEFAULT CURRENT_TIMESTAMP | Audit entry timestamp |
| performed_by | UUID | FOREIGN KEY → users(id) | User who performed action |

**Business Rules:**
- Immutable records (no updates or deletes)
- Stores complete change history
- JSONB format for flexible value storage

### 6. Password Reset Tokens
**Purpose:** Manage password reset workflow securely.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PRIMARY KEY, DEFAULT uuid_generate_v4() | Unique token ID |
| user_id | UUID | NOT NULL, FOREIGN KEY → users(id) | User requesting reset |
| token | VARCHAR(255) | NOT NULL, UNIQUE | Secure reset token |
| expires_at | TIMESTAMP WITH TIME ZONE | NOT NULL | Token expiration time |
| used_at | TIMESTAMP WITH TIME ZONE | NULL | Token usage timestamp |
| created_at | TIMESTAMP WITH TIME ZONE | DEFAULT CURRENT_TIMESTAMP | Token creation timestamp |

**Business Rules:**
- Tokens expire after configured time (typically 1 hour)
- Single-use tokens (used_at marks as consumed)
- Automatic cleanup of expired tokens

### 7. Email Verification Tokens
**Purpose:** Manage email verification workflow.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PRIMARY KEY, DEFAULT uuid_generate_v4() | Unique token ID |
| user_id | UUID | NOT NULL, FOREIGN KEY → users(id) | User to verify |
| token | VARCHAR(255) | NOT NULL, UNIQUE | Verification token |
| expires_at | TIMESTAMP WITH TIME ZONE | NOT NULL | Token expiration time |
| verified_at | TIMESTAMP WITH TIME ZONE | NULL | Verification timestamp |
| created_at | TIMESTAMP WITH TIME ZONE | DEFAULT CURRENT_TIMESTAMP | Token creation timestamp |

**Business Rules:**
- Tokens expire after configured time (typically 24 hours)
- Single-use tokens
- Updates users.is_verified on successful verification

---

## Relationships

### One-to-One Relationships
1. **users ↔ user_profiles**
   - Each user has at most one profile
   - Profile is optional
   - CASCADE DELETE: Deleting user removes profile

### One-to-Many Relationships
1. **users → password_reset_tokens**
   - User can have multiple password reset tokens (historical)
   - CASCADE DELETE: Deleting user removes tokens

2. **users → email_verification_tokens**
   - User can have multiple verification tokens
   - CASCADE DELETE: Deleting user removes tokens

3. **users → user_audit_log**
   - User can have many audit log entries
   - SET NULL on delete: Preserve audit trail

### Many-to-Many Relationships
1. **users ↔ roles** (via user_roles)
   - Users can have multiple roles
   - Roles can be assigned to multiple users
   - CASCADE DELETE on user removal
   - CASCADE DELETE on role removal

---

## Data Types and Constraints

### UUID Usage
- **Primary Keys:** All tables use UUID for primary keys
- **Benefits:**
  - Globally unique identifiers
  - No collision risk in distributed systems
  - Better security (non-sequential)

### Timestamp Standards
- **Type:** `TIMESTAMP WITH TIME ZONE`
- **Benefits:** Timezone-aware storage for global applications
- **Default:** `CURRENT_TIMESTAMP` for automatic timestamps

### Soft Delete Pattern
- **Implementation:** `deleted_at` column (NULL = active)
- **Benefits:**
  - Data retention for compliance
  - Ability to restore accounts
  - Maintains referential integrity

### Email Validation
- **Constraint:** Regex pattern matching
- **Format:** `^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$`

### Password Security
- **Storage:** Hashed using bcrypt or argon2
- **Never** store plain text passwords
- **Column:** `password_hash` (255 characters for future-proofing)

---

## Indexing Strategy

### Performance Indexes
```sql
-- High-frequency query optimization
idx_users_email               -- Login by email
idx_users_username            -- Login by username
idx_users_is_active           -- Filter active users
idx_users_created_at          -- Sort by registration date

-- Relationship indexes
idx_user_roles_user_id        -- Find user's roles
idx_user_roles_role_id        -- Find users with role

-- Audit and security
idx_audit_log_user_id         -- User activity history
idx_audit_log_created_at      -- Recent activity
idx_audit_log_action          -- Filter by action type
```

### Partial Indexes
```sql
-- Index only non-deleted users (most common queries)
WHERE deleted_at IS NULL

-- Index only active tokens
WHERE used_at IS NULL
WHERE verified_at IS NULL
```

**Benefits:**
- Smaller index size
- Faster query performance
- Lower maintenance overhead

---

## Security Considerations

### Authentication Security
1. **Password Hashing:** Use bcrypt (cost factor 12) or argon2
2. **Token Security:** Cryptographically secure random tokens
3. **Token Expiration:** Short-lived tokens (1-24 hours)
4. **Rate Limiting:** Implement at application layer

### Data Privacy
1. **PII Protection:** Encrypt sensitive fields (consider pgcrypto)
2. **Audit Logging:** Track all data access and modifications
3. **Soft Deletes:** Enable data recovery and compliance
4. **Access Control:** Role-based permissions

### SQL Injection Prevention
1. **Parameterized Queries:** Always use prepared statements
2. **Input Validation:** Enforce at database and application layers
3. **Constraint Checks:** Database-level validation

### Compliance Considerations
1. **GDPR:** Right to erasure (soft delete + data export)
2. **Audit Trail:** Complete change history
3. **Data Retention:** Configurable retention policies
4. **User Consent:** Track via audit log

---

## Query Patterns

### Common Operations

#### 1. Create User
```sql
INSERT INTO users (username, email, password_hash, first_name, last_name)
VALUES ($1, $2, $3, $4, $5)
RETURNING id, username, email, created_at;
```

#### 2. Read User (with Profile and Roles)
```sql
SELECT * FROM v_users_complete WHERE id = $1;
```

#### 3. Update User
```sql
UPDATE users
SET first_name = $1, last_name = $2, updated_at = CURRENT_TIMESTAMP
WHERE id = $3 AND deleted_at IS NULL
RETURNING *;
```

#### 4. Soft Delete User
```sql
SELECT soft_delete_user($1);
```

#### 5. Assign Role
```sql
INSERT INTO user_roles (user_id, role_id, assigned_by)
VALUES ($1, $2, $3)
ON CONFLICT DO NOTHING;
```

---

## Performance Benchmarks

### Expected Query Performance
- **User lookup by email/username:** < 5ms (indexed)
- **User with profile and roles:** < 10ms (join 3 tables)
- **Audit log insertion:** < 3ms (minimal indexes)
- **Token validation:** < 5ms (indexed, partial)

### Scalability Considerations
- **Users:** Optimized for 1M+ users
- **Audit Log:** Partition by date for large datasets
- **Indexes:** Regularly VACUUM and ANALYZE
- **Connections:** Use connection pooling (PgBouncer)

---

## Migration Strategy

See `migration_scripts/` directory for:
- Initial schema creation
- Version upgrades
- Rollback procedures
- Data seeding scripts

---

## Maintenance Procedures

### Regular Maintenance
```sql
-- Clean expired tokens (run daily)
SELECT clean_expired_tokens();

-- Vacuum and analyze (run weekly)
VACUUM ANALYZE users;
VACUUM ANALYZE user_audit_log;

-- Reindex if needed (run monthly)
REINDEX TABLE users;
```

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2025-10-12 | Initial data model design |

---

## Contact

For questions or updates to this data model, contact the Database Specialist team.
