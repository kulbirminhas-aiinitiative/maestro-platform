-- ============================================================================
-- Migration: 001_initial_schema
-- Description: Initial database schema for User Management API
-- Author: Database Specialist
-- Created: 2025-10-12
-- ============================================================================

-- Migration metadata
-- Version: 001
-- Requires: PostgreSQL 14+
-- Estimated time: < 1 second (empty database)

BEGIN;

-- ============================================================================
-- EXTENSIONS
-- ============================================================================

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ============================================================================
-- SCHEMA VERSION TRACKING
-- ============================================================================

CREATE TABLE IF NOT EXISTS schema_migrations (
    version VARCHAR(20) PRIMARY KEY,
    description TEXT NOT NULL,
    applied_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    applied_by VARCHAR(100) DEFAULT CURRENT_USER,
    execution_time_ms INTEGER,
    checksum VARCHAR(64)
);

-- ============================================================================
-- CORE TABLES
-- ============================================================================

CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    username VARCHAR(50) NOT NULL UNIQUE,
    email VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    is_active BOOLEAN DEFAULT TRUE,
    is_verified BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_login_at TIMESTAMP WITH TIME ZONE,
    deleted_at TIMESTAMP WITH TIME ZONE,
    CONSTRAINT username_length CHECK (LENGTH(username) >= 3),
    CONSTRAINT email_format CHECK (email ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$')
);

CREATE TABLE user_profiles (
    user_id UUID PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    bio TEXT,
    phone_number VARCHAR(20),
    date_of_birth DATE,
    avatar_url VARCHAR(500),
    timezone VARCHAR(50) DEFAULT 'UTC',
    locale VARCHAR(10) DEFAULT 'en_US',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE roles (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(50) NOT NULL UNIQUE,
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT role_name_lowercase CHECK (name = LOWER(name))
);

CREATE TABLE user_roles (
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    role_id UUID REFERENCES roles(id) ON DELETE CASCADE,
    assigned_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    assigned_by UUID REFERENCES users(id) ON DELETE SET NULL,
    PRIMARY KEY (user_id, role_id)
);

CREATE TABLE user_audit_log (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    action VARCHAR(50) NOT NULL,
    entity_type VARCHAR(50) NOT NULL,
    entity_id UUID,
    old_values JSONB,
    new_values JSONB,
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    performed_by UUID REFERENCES users(id) ON DELETE SET NULL
);

CREATE TABLE password_reset_tokens (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token VARCHAR(255) NOT NULL UNIQUE,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    used_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT token_not_expired CHECK (used_at IS NULL OR used_at < expires_at)
);

CREATE TABLE email_verification_tokens (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token VARCHAR(255) NOT NULL UNIQUE,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    verified_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- INDEXES
-- ============================================================================

-- Users indexes
CREATE INDEX idx_users_email ON users(email) WHERE deleted_at IS NULL;
CREATE INDEX idx_users_username ON users(username) WHERE deleted_at IS NULL;
CREATE INDEX idx_users_is_active ON users(is_active) WHERE deleted_at IS NULL;
CREATE INDEX idx_users_created_at ON users(created_at DESC);
CREATE INDEX idx_users_deleted_at ON users(deleted_at) WHERE deleted_at IS NOT NULL;

-- User profiles indexes
CREATE INDEX idx_user_profiles_phone ON user_profiles(phone_number);

-- User roles indexes
CREATE INDEX idx_user_roles_user_id ON user_roles(user_id);
CREATE INDEX idx_user_roles_role_id ON user_roles(role_id);

-- Audit log indexes
CREATE INDEX idx_audit_log_user_id ON user_audit_log(user_id);
CREATE INDEX idx_audit_log_created_at ON user_audit_log(created_at DESC);
CREATE INDEX idx_audit_log_action ON user_audit_log(action);
CREATE INDEX idx_audit_log_entity ON user_audit_log(entity_type, entity_id);

-- Token indexes
CREATE INDEX idx_password_reset_tokens_user_id ON password_reset_tokens(user_id);
CREATE INDEX idx_password_reset_tokens_token ON password_reset_tokens(token) WHERE used_at IS NULL;
CREATE INDEX idx_password_reset_tokens_expires ON password_reset_tokens(expires_at) WHERE used_at IS NULL;
CREATE INDEX idx_email_verification_tokens_user_id ON email_verification_tokens(user_id);
CREATE INDEX idx_email_verification_tokens_token ON email_verification_tokens(token) WHERE verified_at IS NULL;

-- ============================================================================
-- FUNCTIONS
-- ============================================================================

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION soft_delete_user(user_id_param UUID)
RETURNS BOOLEAN AS $$
BEGIN
    UPDATE users
    SET deleted_at = CURRENT_TIMESTAMP,
        is_active = FALSE
    WHERE id = user_id_param
    AND deleted_at IS NULL;
    RETURN FOUND;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION clean_expired_tokens()
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM password_reset_tokens
    WHERE expires_at < CURRENT_TIMESTAMP
    AND used_at IS NULL;
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    DELETE FROM email_verification_tokens
    WHERE expires_at < CURRENT_TIMESTAMP
    AND verified_at IS NULL;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- TRIGGERS
-- ============================================================================

CREATE TRIGGER update_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_user_profiles_updated_at
    BEFORE UPDATE ON user_profiles
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- VIEWS
-- ============================================================================

CREATE OR REPLACE VIEW v_users_complete AS
SELECT
    u.id,
    u.username,
    u.email,
    u.first_name,
    u.last_name,
    u.is_active,
    u.is_verified,
    u.created_at,
    u.updated_at,
    u.last_login_at,
    p.bio,
    p.phone_number,
    p.date_of_birth,
    p.avatar_url,
    p.timezone,
    p.locale,
    ARRAY_AGG(DISTINCT r.name) FILTER (WHERE r.name IS NOT NULL) AS roles
FROM users u
LEFT JOIN user_profiles p ON u.id = p.user_id
LEFT JOIN user_roles ur ON u.id = ur.user_id
LEFT JOIN roles r ON ur.role_id = r.id
WHERE u.deleted_at IS NULL
GROUP BY u.id, p.user_id, p.bio, p.phone_number, p.date_of_birth,
         p.avatar_url, p.timezone, p.locale;

CREATE OR REPLACE VIEW v_active_users_summary AS
SELECT
    u.id,
    u.username,
    u.email,
    u.first_name,
    u.last_name,
    u.is_verified,
    u.last_login_at,
    COUNT(DISTINCT ur.role_id) AS role_count
FROM users u
LEFT JOIN user_roles ur ON u.id = ur.user_id
WHERE u.is_active = TRUE
AND u.deleted_at IS NULL
GROUP BY u.id;

-- ============================================================================
-- SEED DATA
-- ============================================================================

INSERT INTO roles (name, description) VALUES
    ('admin', 'Full system access with all permissions'),
    ('user', 'Standard user with basic permissions'),
    ('moderator', 'Can moderate content and manage users'),
    ('guest', 'Read-only access')
ON CONFLICT (name) DO NOTHING;

-- ============================================================================
-- COMMENTS
-- ============================================================================

COMMENT ON TABLE users IS 'Core user accounts with authentication credentials';
COMMENT ON TABLE user_profiles IS 'Extended user profile information';
COMMENT ON TABLE roles IS 'System roles for access control';
COMMENT ON TABLE user_roles IS 'User-role assignments (many-to-many)';
COMMENT ON TABLE user_audit_log IS 'Audit trail for all user-related changes';
COMMENT ON COLUMN users.password_hash IS 'Hashed password using bcrypt or argon2';
COMMENT ON COLUMN users.deleted_at IS 'Soft delete timestamp (NULL = active)';

-- ============================================================================
-- RECORD MIGRATION
-- ============================================================================

INSERT INTO schema_migrations (version, description, execution_time_ms)
VALUES ('001', 'Initial schema creation', NULL);

COMMIT;

-- ============================================================================
-- VERIFICATION
-- ============================================================================

-- Verify tables created
DO $$
DECLARE
    table_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO table_count
    FROM information_schema.tables
    WHERE table_schema = 'public'
    AND table_name IN ('users', 'user_profiles', 'roles', 'user_roles',
                       'user_audit_log', 'password_reset_tokens',
                       'email_verification_tokens', 'schema_migrations');

    IF table_count <> 8 THEN
        RAISE EXCEPTION 'Migration verification failed: Expected 8 tables, found %', table_count;
    END IF;

    RAISE NOTICE 'Migration 001 completed successfully. Tables created: %', table_count;
END $$;
