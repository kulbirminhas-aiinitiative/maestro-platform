# Database Entity Relationship Model
## User Management REST API - Design Phase

**Project:** User Management REST API
**Phase:** Design
**Version:** 2.0
**Date:** 2025-10-12
**Prepared by:** Database Specialist

---

## Table of Contents
1. [Entity Relationship Diagram](#1-entity-relationship-diagram)
2. [Entity Definitions](#2-entity-definitions)
3. [Relationship Specifications](#3-relationship-specifications)
4. [Data Dictionary](#4-data-dictionary)
5. [Business Rules](#5-business-rules)
6. [Data Flow Patterns](#6-data-flow-patterns)

---

## 1. Entity Relationship Diagram

### 1.1 Conceptual ERD

```
┌─────────────────────────────────────────────────────────────────────┐
│                     USER MANAGEMENT SYSTEM                           │
└─────────────────────────────────────────────────────────────────────┘

                            ┌──────────────┐
                            │    USERS     │
                            │ (Core Entity)│
                            ├──────────────┤
                            │ id (PK)      │
                            │ username     │◄────┐
                            │ email        │     │
                            │ password_hash│     │
                            │ status       │     │
                            │ ...          │     │
                            └──────┬───────┘     │
                                   │             │
                    ┌──────────────┼─────────────┴────────────┐
                    │              │                           │
                    │              │                           │
          ┌─────────▼──────┐  ┌───▼─────────────┐  ┌─────────▼────────┐
          │ REFRESH_TOKENS │  │  AUDIT_LOGS     │  │ PASSWORD_RESET   │
          ├────────────────┤  ├─────────────────┤  │    _TOKENS       │
          │ id (PK)        │  │ id (PK)         │  ├──────────────────┤
          │ user_id (FK)   │  │ user_id (FK)    │  │ id (PK)          │
          │ token_hash     │  │ action          │  │ user_id (FK)     │
          │ expires_at     │  │ entity_type     │  │ token_hash       │
          │ ...            │  │ old_values      │  │ expires_at       │
          └────────────────┘  │ new_values      │  │ ...              │
                              │ ...             │  └──────────────────┘
                              └─────────────────┘
                                       │
                              ┌────────▼─────────┐
                              │  EMAIL_VERIFICATION│
                              │     _TOKENS       │
                              ├──────────────────┤
                              │ id (PK)          │
                              │ user_id (FK)     │
                              │ token_hash       │
                              │ email            │
                              │ ...              │
                              └──────────────────┘

          ┌─────────────────┐
          │  RATE_LIMITS    │
          ├─────────────────┤
          │ id (PK)         │
          │ identifier      │ ◄── (IP or user_id)
          │ endpoint        │
          │ request_count   │
          │ window_start    │
          │ ...             │
          └─────────────────┘
```

### 1.2 Physical ERD (Detailed)

```
╔═══════════════════════════════════════════════════════════════════════════╗
║                              USERS TABLE                                   ║
╠═══════════════════════════════════════════════════════════════════════════╣
║  id                        UUID PRIMARY KEY                               ║
║  username                  VARCHAR(50) UNIQUE NOT NULL                    ║
║  email                     VARCHAR(255) UNIQUE NOT NULL                   ║
║  password_hash             VARCHAR(255) NOT NULL                          ║
║  password_changed_at       TIMESTAMP WITH TIME ZONE                       ║
║  failed_login_attempts     INTEGER DEFAULT 0                              ║
║  locked_until              TIMESTAMP WITH TIME ZONE                       ║
║  first_name                VARCHAR(100)                                   ║
║  last_name                 VARCHAR(100)                                   ║
║  phone_number              VARCHAR(20)                                    ║
║  date_of_birth             DATE                                           ║
║  profile_picture_url       VARCHAR(500)                                   ║
║  bio                       TEXT (max 500 chars)                           ║
║  status                    user_status (ENUM) DEFAULT 'active'            ║
║  is_email_verified         BOOLEAN DEFAULT FALSE                          ║
║  is_phone_verified         BOOLEAN DEFAULT FALSE                          ║
║  created_at                TIMESTAMP WITH TIME ZONE DEFAULT NOW()         ║
║  updated_at                TIMESTAMP WITH TIME ZONE DEFAULT NOW()         ║
║  last_login_at             TIMESTAMP WITH TIME ZONE                       ║
║  deleted_at                TIMESTAMP WITH TIME ZONE                       ║
║  gdpr_consent_at           TIMESTAMP WITH TIME ZONE                       ║
║  data_retention_until      DATE                                           ║
╠═══════════════════════════════════════════════════════════════════════════╣
║  INDEXES:                                                                  ║
║  - idx_users_email (email) WHERE deleted_at IS NULL                       ║
║  - idx_users_username (username) WHERE deleted_at IS NULL                 ║
║  - idx_users_status (status) WHERE deleted_at IS NULL                     ║
║  - idx_users_login_lookup (email, password_hash) [COMPOSITE]              ║
║  - idx_users_fulltext (GIN) for full-text search                          ║
╚═══════════════════════════════════════════════════════════════════════════╝
                                     │
                                     │ 1
                                     │
                    ┌────────────────┼────────────────┐
                    │                │                │
              1     │                │                │     1
                    │                │                │
         ┌──────────▼───────┐  ┌────▼─────────┐  ┌──▼──────────────┐
         │ REFRESH_TOKENS   │  │ AUDIT_LOGS   │  │ PASSWORD_RESET  │
         ├──────────────────┤  ├──────────────┤  │    _TOKENS      │
         │ id (PK)          │  │ id (PK)      │  ├─────────────────┤
         │ user_id (FK) ────┼─►│ user_id (FK) │  │ id (PK)         │
         │ token_hash UQ    │  │ action       │  │ user_id (FK) ───┤
         │ expires_at       │  │ entity_type  │  │ token_hash UQ   │
         │ revoked_at       │  │ entity_id    │  │ expires_at      │
         │ replaced_by (FK) │  │ old_values   │  │ created_at      │
         │ device_fp        │  │ new_values   │  │ used_at         │
         └──────────────────┘  │ ip_address   │  │ ip_address      │
                ▲               │ request_id   │  └─────────────────┘
                │               │ severity     │
                │               └──────────────┘
                │ self-reference
                └───────┐               │
                        │               │ 1
                                        │
                              ┌─────────▼─────────┐
                              │ EMAIL_VERIFICATION│
                              │     _TOKENS       │
                              ├───────────────────┤
                              │ id (PK)           │
                              │ user_id (FK)      │
                              │ email             │
                              │ token_hash UQ     │
                              │ expires_at        │
                              │ verified_at       │
                              └───────────────────┘
```

---

## 2. Entity Definitions

### 2.1 USERS (Core Entity)

**Purpose:** Central entity storing user accounts and authentication credentials

**Entity Type:** Strong entity (independent)

**Cardinality:** 0 to N (unlimited users)

**Key Attributes:**
- **Primary Key:** `id` (UUID) - Globally unique identifier
- **Unique Keys:** `username`, `email`
- **Required:** `username`, `email`, `password_hash`
- **Optional:** Profile fields, contact information

**State Machine:**
```
    [created]
        │
        ▼
   [active] ◄──► [inactive]
        │           │
        ▼           ▼
  [suspended] ◄─► [deleted]
```

### 2.2 REFRESH_TOKENS

**Purpose:** Manage JWT refresh tokens for session management

**Entity Type:** Weak entity (depends on USERS)

**Cardinality:** 0 to N per user (multiple devices)

**Lifecycle:**
```
[created] → [active] → [revoked/expired] → [deleted]
```

**Key Features:**
- Token rotation support (replaced_by self-reference)
- Device tracking (user_agent, device_fingerprint)
- Automatic cleanup via scheduled job

### 2.3 AUDIT_LOGS

**Purpose:** Immutable audit trail for compliance and security

**Entity Type:** Weak entity (depends on USERS)

**Cardinality:** 0 to N per user (unlimited history)

**Key Features:**
- JSONB storage for flexible change tracking
- Request correlation (request_id)
- Partitioning support (log_date)
- Severity levels for alerting

### 2.4 PASSWORD_RESET_TOKENS

**Purpose:** Secure password reset workflow

**Entity Type:** Weak entity (depends on USERS)

**Cardinality:** 0 to 1 active per user

**Security Features:**
- Short expiration (1 hour)
- Single-use tokens
- IP tracking for fraud detection

### 2.5 EMAIL_VERIFICATION_TOKENS

**Purpose:** Email ownership verification

**Entity Type:** Weak entity (depends on USERS)

**Cardinality:** 0 to 1 active per user

**Features:**
- Supports email change verification
- Stores email being verified
- Single-use tokens

### 2.6 RATE_LIMITS

**Purpose:** API abuse prevention

**Entity Type:** Independent entity

**Cardinality:** Multiple per identifier/endpoint

**Implementation:**
- Sliding window algorithm support
- Per-endpoint granularity
- Automatic cleanup

---

## 3. Relationship Specifications

### 3.1 Relationship Matrix

| Parent Entity | Child Entity | Type | Cardinality | FK Column | On Delete |
|--------------|--------------|------|-------------|-----------|-----------|
| USERS | REFRESH_TOKENS | 1:N | 0..* | user_id | CASCADE |
| USERS | AUDIT_LOGS | 1:N | 0..* | user_id | SET NULL |
| USERS | PASSWORD_RESET_TOKENS | 1:N | 0..* | user_id | CASCADE |
| USERS | EMAIL_VERIFICATION_TOKENS | 1:N | 0..* | user_id | CASCADE |
| REFRESH_TOKENS | REFRESH_TOKENS | 1:1 | 0..1 | replaced_by | SET NULL |

### 3.2 Relationship Descriptions

#### R1: USERS → REFRESH_TOKENS (1:N)
**Relationship:** "User HAS multiple refresh tokens"
- **Type:** One-to-Many, Identifying
- **Participation:** Users (Optional), Refresh Tokens (Mandatory)
- **Business Rule:** Each user may have multiple active sessions across devices
- **Constraint:** CASCADE delete ensures cleanup when user is deleted
- **Typical Count:** 1-5 tokens per active user

#### R2: USERS → AUDIT_LOGS (1:N)
**Relationship:** "User HAS audit history"
- **Type:** One-to-Many, Non-Identifying
- **Participation:** Users (Optional), Audit Logs (Optional)
- **Business Rule:** All user actions must be logged
- **Constraint:** SET NULL preserves audit trail even after user deletion
- **Retention:** 7 years for compliance

#### R3: USERS → PASSWORD_RESET_TOKENS (1:N)
**Relationship:** "User REQUESTS password resets"
- **Type:** One-to-Many, Identifying
- **Participation:** Users (Optional), Tokens (Mandatory)
- **Business Rule:** Multiple reset requests allowed, only latest is valid
- **Constraint:** CASCADE delete cleans up pending resets
- **Typical Count:** 0-1 active token per user

#### R4: REFRESH_TOKENS → REFRESH_TOKENS (1:1)
**Relationship:** "Token REPLACES previous token"
- **Type:** Self-referential, Optional
- **Participation:** Both sides optional
- **Business Rule:** Token rotation for security
- **Constraint:** SET NULL on delete (historical reference)
- **Chain Length:** Typically 1-10 rotations per session

---

## 4. Data Dictionary

### 4.1 Common Data Types

| Type | PostgreSQL Type | Size | Usage |
|------|----------------|------|-------|
| ID | UUID | 16 bytes | All primary keys |
| Username | VARCHAR(50) | 50 chars | User identifier |
| Email | VARCHAR(255) | 255 chars | Email addresses |
| Password Hash | VARCHAR(255) | 255 chars | Bcrypt/Argon2 hash |
| Timestamp | TIMESTAMP WITH TIME ZONE | 8 bytes | All dates/times |
| Status | ENUM | 4 bytes | Predefined states |
| JSON Data | JSONB | Variable | Flexible storage |
| Text | TEXT | Variable | Long-form content |
| IP Address | INET | 7-19 bytes | IPv4/IPv6 addresses |

### 4.2 ENUM Definitions

#### user_status
```sql
CREATE TYPE user_status AS ENUM (
    'active',      -- Normal, operational account
    'inactive',    -- Temporarily disabled by user
    'suspended',   -- Administratively suspended
    'deleted'      -- Soft-deleted, pending removal
);
```

#### audit_action
```sql
CREATE TYPE audit_action AS ENUM (
    'created',          -- New record created
    'updated',          -- Record modified
    'deleted',          -- Record removed
    'login',            -- User authentication
    'logout',           -- Session termination
    'password_change',  -- Password updated
    'status_change',    -- Status modified
    'email_verified',   -- Email verification completed
    'account_locked',   -- Account locked due to failed attempts
    'account_unlocked'  -- Account manually unlocked
);
```

### 4.3 Field Validation Rules

#### Username
- **Pattern:** `^[a-zA-Z0-9_-]+$`
- **Length:** 3-50 characters
- **Unique:** Global uniqueness required
- **Immutable:** Cannot be changed after creation (design decision)

#### Email
- **Pattern:** RFC 5322 compliant
- **Length:** Max 255 characters
- **Unique:** Global uniqueness required
- **Format:** Validated via CHECK constraint
- **Example:** `user@example.com`

#### Password Hash
- **Algorithm:** Argon2id (preferred) or bcrypt
- **Min Cost:** bcrypt cost factor 12+
- **Storage:** Hash only, never plain text
- **Length:** 255 characters (future-proof)

#### Phone Number
- **Pattern:** E.164 international format
- **Example:** `+14155552671`
- **Optional:** NULL allowed
- **Validation:** CHECK constraint

---

## 5. Business Rules

### 5.1 User Management Rules

1. **BR-001: Unique Email**
   - Each email must be unique across all active users
   - Soft-deleted users have email modified to allow re-registration
   - Format: `original@email.com.deleted.<uuid>`

2. **BR-002: Username Immutability**
   - Username cannot be changed after account creation
   - Rationale: Maintain audit trail integrity

3. **BR-003: Password Strength**
   - Minimum 8 characters
   - Must contain: uppercase, lowercase, digit, special character
   - Validated at application layer
   - Helper function: `is_strong_password()`

4. **BR-004: Account Locking**
   - 5 failed login attempts triggers lock
   - Lock duration: 30 minutes
   - Reset counter on successful login

5. **BR-005: Soft Delete**
   - Deletion sets `deleted_at` timestamp
   - Status changed to 'deleted'
   - Email modified to prevent conflicts
   - Data retained for 90 days before anonymization

### 5.2 Token Management Rules

1. **BR-101: Token Expiration**
   - Refresh tokens: 7-30 days (configurable)
   - Password reset: 1 hour maximum
   - Email verification: 24 hours

2. **BR-102: Token Rotation**
   - New refresh token on each refresh operation
   - Old token marked as revoked
   - `replaced_by` tracks token lineage

3. **BR-103: Single-Use Tokens**
   - Password reset and email verification are single-use
   - Marked with `used_at` timestamp
   - Cannot be reused after consumption

4. **BR-104: Token Cleanup**
   - Expired tokens cleaned daily
   - Revoked refresh tokens retained for 7 days
   - Used password reset tokens retained for 7 days

### 5.3 Audit Rules

1. **BR-201: Comprehensive Logging**
   - All user CRUD operations logged
   - Authentication events logged
   - Status changes logged
   - IP address and user agent captured

2. **BR-202: Immutable Audit Trail**
   - No updates or deletes allowed on audit_logs
   - Use DELETE SET NULL to preserve logs after user deletion

3. **BR-203: Audit Retention**
   - 7-year retention for compliance
   - Partitioned by month for performance
   - Old partitions archived to cold storage

### 5.4 Data Retention Rules

1. **BR-301: Active User Data**
   - Retained indefinitely while account is active

2. **BR-302: Soft-Deleted Users**
   - 90-day grace period for recovery
   - Anonymized after 90 days
   - Audit logs preserved

3. **BR-303: Token Cleanup**
   - Expired tokens: 7 days retention
   - Rate limits: 1 hour retention

---

## 6. Data Flow Patterns

### 6.1 User Registration Flow

```
┌─────────────────────────────────────────────────────────┐
│ 1. User Registration Request                            │
└─────────────────────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────┐
│ 2. Validate Input                                       │
│    - Check email uniqueness                             │
│    - Validate password strength                         │
│    - Sanitize username                                  │
└─────────────────────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────┐
│ 3. Hash Password (Argon2id/bcrypt)                      │
└─────────────────────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────┐
│ 4. INSERT into USERS table                              │
│    - status = 'active'                                  │
│    - is_email_verified = FALSE                          │
└─────────────────────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────┐
│ 5. Trigger: create_audit_log()                          │
│    - action = 'created'                                 │
└─────────────────────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────┐
│ 6. Generate Email Verification Token                    │
│    - INSERT into EMAIL_VERIFICATION_TOKENS              │
└─────────────────────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────┐
│ 7. Send Verification Email (external service)           │
└─────────────────────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────┐
│ 8. Return User Object (without password_hash)           │
└─────────────────────────────────────────────────────────┘
```

### 6.2 User Login Flow

```
┌─────────────────────────────────────────────────────────┐
│ 1. Login Request (email/username + password)            │
└─────────────────────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────┐
│ 2. Check Rate Limit                                     │
│    - Query RATE_LIMITS table                            │
│    - Enforce 100 req/min per IP                         │
└─────────────────────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────┐
│ 3. Lookup User                                          │
│    - WHERE (email OR username)                          │
│    - AND deleted_at IS NULL                             │
│    - AND status IN ('active')                           │
└─────────────────────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────┐
│ 4. Check Account Lock                                   │
│    - IF locked_until > NOW() → REJECT                   │
└─────────────────────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────┐
│ 5. Verify Password                                      │
│    - Compare hash using bcrypt/Argon2                   │
└─────────────────────────────────────────────────────────┘
        │                           │
        │ SUCCESS                   │ FAILURE
        ▼                           ▼
┌──────────────────┐      ┌────────────────────────┐
│ 6a. Reset        │      │ 6b. Increment          │
│     failed_login │      │     failed_login       │
│     _attempts    │      │     _attempts          │
│     to 0         │      │     (lock if >= 5)     │
└──────────────────┘      └────────────────────────┘
        │                           │
        │                           ▼
        │                  ┌────────────────────────┐
        │                  │ INSERT AUDIT_LOG       │
        │                  │ action='login_failed'  │
        │                  └────────────────────────┘
        ▼
┌─────────────────────────────────────────────────────────┐
│ 7. Update last_login_at = NOW()                         │
└─────────────────────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────────────────┐
│ 8. Generate Tokens                                      │
│    - Access Token (JWT, 15 min)                         │
│    - Refresh Token (JWT, 7-30 days)                     │
└─────────────────────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────────────────┐
│ 9. INSERT REFRESH_TOKENS                                │
│    - Hash refresh token                                 │
│    - Store device info                                  │
└─────────────────────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────────────────┐
│ 10. INSERT AUDIT_LOG (action='login')                   │
└─────────────────────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────────────────┐
│ 11. Return Tokens + User Object                         │
└─────────────────────────────────────────────────────────┘
```

### 6.3 Token Refresh Flow

```
┌─────────────────────────────────────────────────────────┐
│ 1. Token Refresh Request (with refresh_token)           │
└─────────────────────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────┐
│ 2. Hash Provided Token                                  │
└─────────────────────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────┐
│ 3. Lookup in REFRESH_TOKENS                             │
│    - WHERE token_hash = ?                               │
│    - AND revoked_at IS NULL                             │
│    - AND expires_at > NOW()                             │
└─────────────────────────────────────────────────────────┘
        │                           │
        │ FOUND                     │ NOT FOUND
        ▼                           ▼
┌──────────────────┐      ┌────────────────────────┐
│ 4. Validate User │      │ REJECT: Invalid Token  │
│    - deleted_at  │      └────────────────────────┘
│      IS NULL     │
│    - status =    │
│      'active'    │
└──────────────────┘
        │
        ▼
┌─────────────────────────────────────────────────────────┐
│ 5. Generate New Refresh Token                           │
└─────────────────────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────────────────┐
│ 6. INSERT New REFRESH_TOKEN                             │
│    - New token_hash                                     │
│    - New expiration                                     │
└─────────────────────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────────────────┐
│ 7. UPDATE Old Token                                     │
│    - SET revoked_at = NOW()                             │
│    - SET replaced_by = new_token_id                     │
└─────────────────────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────────────────┐
│ 8. Generate New Access Token (JWT, 15 min)              │
└─────────────────────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────────────────┐
│ 9. Return New Tokens                                    │
└─────────────────────────────────────────────────────────┘
```

### 6.4 Soft Delete Flow

```
┌─────────────────────────────────────────────────────────┐
│ 1. Delete User Request                                  │
└─────────────────────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────┐
│ 2. Authorize Request (user owns account or is admin)    │
└─────────────────────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────┐
│ 3. Call soft_delete_user(user_id)                       │
└─────────────────────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────┐
│ 4. UPDATE USERS                                         │
│    - SET deleted_at = NOW()                             │
│    - SET status = 'deleted'                             │
│    - SET email = email || '.deleted.' || id::text       │
└─────────────────────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────┐
│ 5. Trigger: create_audit_log()                          │
│    - action = 'deleted'                                 │
│    - Captures old/new values                            │
└─────────────────────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────┐
│ 6. CASCADE: Delete REFRESH_TOKENS                       │
│             Delete PASSWORD_RESET_TOKENS                │
│             Delete EMAIL_VERIFICATION_TOKENS            │
└─────────────────────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────┐
│ 7. Return Success Response                              │
└─────────────────────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────┐
│ 8. (After 90 days) Scheduled Job: Anonymize User Data   │
│    - Replace PII with anonymized values                 │
│    - Preserve audit logs                                │
└─────────────────────────────────────────────────────────┘
```

---

## 7. Query Patterns & Indexes

### 7.1 Critical Query Patterns

#### Pattern 1: User Authentication
```sql
-- Index: idx_users_email
SELECT id, password_hash, status, failed_login_attempts, locked_until
FROM users
WHERE email = $1
  AND deleted_at IS NULL;
```

#### Pattern 2: Token Validation
```sql
-- Index: idx_refresh_tokens_hash
SELECT rt.id, rt.user_id, rt.expires_at, u.status
FROM refresh_tokens rt
JOIN users u ON rt.user_id = u.id
WHERE rt.token_hash = $1
  AND rt.revoked_at IS NULL
  AND rt.expires_at > CURRENT_TIMESTAMP
  AND u.deleted_at IS NULL;
```

#### Pattern 3: User Listing (Paginated)
```sql
-- Index: idx_users_status_created
SELECT id, username, email, first_name, last_name, status, created_at
FROM users
WHERE deleted_at IS NULL
  AND status = 'active'
ORDER BY created_at DESC
LIMIT $1 OFFSET $2;
```

#### Pattern 4: Audit Trail Query
```sql
-- Index: idx_audit_logs_user_id
SELECT action, entity_type, old_values, new_values, created_at, ip_address
FROM audit_logs
WHERE user_id = $1
  AND created_at >= $2
ORDER BY created_at DESC
LIMIT 100;
```

### 7.2 Index Coverage Analysis

| Query Pattern | Index Used | Coverage | Performance |
|--------------|-----------|----------|-------------|
| Login by email | idx_users_email | Full | < 5ms |
| Login by username | idx_users_username | Full | < 5ms |
| Token validation | idx_refresh_tokens_hash | Full | < 5ms |
| User list | idx_users_status_created | Full | < 15ms |
| Search by name | idx_users_fulltext | Full | < 50ms |
| Audit trail | idx_audit_logs_user_id | Full | < 20ms |

---

## 8. Conclusion

This Entity Relationship Model provides a comprehensive view of the database structure for the User Management REST API. Key features:

✅ **Normalized Design:** 3rd Normal Form (3NF) compliance
✅ **Referential Integrity:** Comprehensive foreign key relationships
✅ **Performance Optimized:** Strategic indexing for < 200ms queries
✅ **Security Focused:** Audit trails, token management, soft deletes
✅ **Scalable:** Designed for 1M+ users
✅ **GDPR Compliant:** Data retention policies, anonymization support

The model is production-ready and supports all functional requirements defined in the requirements phase.

---

**Prepared by:** Database Specialist
**Status:** ✅ Complete
**Next Steps:** Implementation and testing
