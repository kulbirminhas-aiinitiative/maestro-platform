-- ============================================================================
-- Rollback Migration: 001_initial_schema
-- Description: Rollback initial database schema
-- Author: Database Specialist
-- Created: 2025-10-12
-- ============================================================================

-- WARNING: This will DELETE all data and DROP all tables
-- Use with extreme caution in production environments

BEGIN;

-- ============================================================================
-- DROP VIEWS
-- ============================================================================

DROP VIEW IF EXISTS v_active_users_summary CASCADE;
DROP VIEW IF EXISTS v_users_complete CASCADE;

-- ============================================================================
-- DROP TRIGGERS
-- ============================================================================

DROP TRIGGER IF EXISTS update_user_profiles_updated_at ON user_profiles;
DROP TRIGGER IF EXISTS update_users_updated_at ON users;

-- ============================================================================
-- DROP FUNCTIONS
-- ============================================================================

DROP FUNCTION IF EXISTS clean_expired_tokens() CASCADE;
DROP FUNCTION IF EXISTS soft_delete_user(UUID) CASCADE;
DROP FUNCTION IF EXISTS update_updated_at_column() CASCADE;

-- ============================================================================
-- DROP TABLES (in reverse dependency order)
-- ============================================================================

DROP TABLE IF EXISTS email_verification_tokens CASCADE;
DROP TABLE IF EXISTS password_reset_tokens CASCADE;
DROP TABLE IF EXISTS user_audit_log CASCADE;
DROP TABLE IF EXISTS user_roles CASCADE;
DROP TABLE IF EXISTS roles CASCADE;
DROP TABLE IF EXISTS user_profiles CASCADE;
DROP TABLE IF EXISTS users CASCADE;

-- ============================================================================
-- REMOVE MIGRATION RECORD
-- ============================================================================

DELETE FROM schema_migrations WHERE version = '001';

-- If this is the only migration, drop the migrations table too
DROP TABLE IF EXISTS schema_migrations CASCADE;

-- ============================================================================
-- DROP EXTENSIONS (Optional - only if no other schemas use them)
-- ============================================================================

-- Uncomment if you want to remove extensions (be careful in shared databases)
-- DROP EXTENSION IF EXISTS "pgcrypto";
-- DROP EXTENSION IF EXISTS "uuid-ossp";

COMMIT;

-- ============================================================================
-- VERIFICATION
-- ============================================================================

DO $$
DECLARE
    table_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO table_count
    FROM information_schema.tables
    WHERE table_schema = 'public'
    AND table_name IN ('users', 'user_profiles', 'roles', 'user_roles',
                       'user_audit_log', 'password_reset_tokens',
                       'email_verification_tokens');

    IF table_count <> 0 THEN
        RAISE EXCEPTION 'Rollback verification failed: Found % remaining tables', table_count;
    END IF;

    RAISE NOTICE 'Rollback of migration 001 completed successfully';
END $$;
