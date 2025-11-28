-- ============================================================================
-- Seed Data: Sample data for testing and development
-- Description: Populate database with test data
-- Author: Database Specialist
-- Created: 2025-10-12
-- ============================================================================

-- NOTE: This is for DEVELOPMENT/TESTING only
-- DO NOT run in production environment

BEGIN;

-- ============================================================================
-- SAMPLE USERS
-- ============================================================================

-- Admin user (password: Admin123!)
INSERT INTO users (id, username, email, password_hash, first_name, last_name, is_active, is_verified)
VALUES
    ('550e8400-e29b-41d4-a716-446655440001',
     'admin',
     'admin@example.com',
     '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYqVr/YPZxK', -- Admin123!
     'Admin',
     'User',
     TRUE,
     TRUE),

    ('550e8400-e29b-41d4-a716-446655440002',
     'johndoe',
     'john.doe@example.com',
     '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYqVr/YPZxK', -- User123!
     'John',
     'Doe',
     TRUE,
     TRUE),

    ('550e8400-e29b-41d4-a716-446655440003',
     'janesmith',
     'jane.smith@example.com',
     '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYqVr/YPZxK', -- User123!
     'Jane',
     'Smith',
     TRUE,
     TRUE),

    ('550e8400-e29b-41d4-a716-446655440004',
     'bobmoderator',
     'bob.moderator@example.com',
     '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYqVr/YPZxK', -- Mod123!
     'Bob',
     'Moderator',
     TRUE,
     TRUE),

    ('550e8400-e29b-41d4-a716-446655440005',
     'alice_guest',
     'alice.guest@example.com',
     '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYqVr/YPZxK', -- Guest123!
     'Alice',
     'Guest',
     TRUE,
     FALSE), -- Not verified

    ('550e8400-e29b-41d4-a716-446655440006',
     'inactive_user',
     'inactive@example.com',
     '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYqVr/YPZxK',
     'Inactive',
     'User',
     FALSE, -- Inactive account
     TRUE)
ON CONFLICT (id) DO NOTHING;

-- ============================================================================
-- USER PROFILES
-- ============================================================================

INSERT INTO user_profiles (user_id, bio, phone_number, date_of_birth, timezone, locale)
VALUES
    ('550e8400-e29b-41d4-a716-446655440001',
     'System administrator with full access',
     '+1-555-0001',
     '1985-01-15',
     'America/New_York',
     'en_US'),

    ('550e8400-e29b-41d4-a716-446655440002',
     'Software engineer passionate about clean code',
     '+1-555-0002',
     '1990-05-20',
     'America/Los_Angeles',
     'en_US'),

    ('550e8400-e29b-41d4-a716-446655440003',
     'Product manager focused on user experience',
     '+1-555-0003',
     '1988-08-10',
     'Europe/London',
     'en_GB'),

    ('550e8400-e29b-41d4-a716-446655440004',
     'Community moderator helping keep things civil',
     '+1-555-0004',
     '1992-03-25',
     'America/Chicago',
     'en_US'),

    ('550e8400-e29b-41d4-a716-446655440005',
     'New user exploring the platform',
     '+1-555-0005',
     '1995-12-01',
     'Asia/Tokyo',
     'ja_JP')
ON CONFLICT (user_id) DO NOTHING;

-- ============================================================================
-- ROLE ASSIGNMENTS
-- ============================================================================

-- Get role IDs
DO $$
DECLARE
    admin_role_id UUID;
    user_role_id UUID;
    moderator_role_id UUID;
    guest_role_id UUID;
BEGIN
    SELECT id INTO admin_role_id FROM roles WHERE name = 'admin';
    SELECT id INTO user_role_id FROM roles WHERE name = 'user';
    SELECT id INTO moderator_role_id FROM roles WHERE name = 'moderator';
    SELECT id INTO guest_role_id FROM roles WHERE name = 'guest';

    -- Admin user: admin + user roles
    INSERT INTO user_roles (user_id, role_id, assigned_by)
    VALUES
        ('550e8400-e29b-41d4-a716-446655440001', admin_role_id, NULL),
        ('550e8400-e29b-41d4-a716-446655440001', user_role_id, NULL)
    ON CONFLICT DO NOTHING;

    -- John Doe: user role
    INSERT INTO user_roles (user_id, role_id, assigned_by)
    VALUES
        ('550e8400-e29b-41d4-a716-446655440002', user_role_id, '550e8400-e29b-41d4-a716-446655440001')
    ON CONFLICT DO NOTHING;

    -- Jane Smith: user role
    INSERT INTO user_roles (user_id, role_id, assigned_by)
    VALUES
        ('550e8400-e29b-41d4-a716-446655440003', user_role_id, '550e8400-e29b-41d4-a716-446655440001')
    ON CONFLICT DO NOTHING;

    -- Bob Moderator: moderator + user roles
    INSERT INTO user_roles (user_id, role_id, assigned_by)
    VALUES
        ('550e8400-e29b-41d4-a716-446655440004', moderator_role_id, '550e8400-e29b-41d4-a716-446655440001'),
        ('550e8400-e29b-41d4-a716-446655440004', user_role_id, '550e8400-e29b-41d4-a716-446655440001')
    ON CONFLICT DO NOTHING;

    -- Alice Guest: guest role
    INSERT INTO user_roles (user_id, role_id, assigned_by)
    VALUES
        ('550e8400-e29b-41d4-a716-446655440005', guest_role_id, '550e8400-e29b-41d4-a716-446655440001')
    ON CONFLICT DO NOTHING;

    -- Inactive user: user role (but account is inactive)
    INSERT INTO user_roles (user_id, role_id, assigned_by)
    VALUES
        ('550e8400-e29b-41d4-a716-446655440006', user_role_id, '550e8400-e29b-41d4-a716-446655440001')
    ON CONFLICT DO NOTHING;
END $$;

-- ============================================================================
-- SAMPLE AUDIT LOG ENTRIES
-- ============================================================================

INSERT INTO user_audit_log (user_id, action, entity_type, entity_id, new_values, ip_address, performed_by)
VALUES
    ('550e8400-e29b-41d4-a716-446655440001',
     'CREATE',
     'user',
     '550e8400-e29b-41d4-a716-446655440001',
     '{"username": "admin", "email": "admin@example.com"}',
     '192.168.1.1',
     NULL),

    ('550e8400-e29b-41d4-a716-446655440002',
     'CREATE',
     'user',
     '550e8400-e29b-41d4-a716-446655440002',
     '{"username": "johndoe", "email": "john.doe@example.com"}',
     '192.168.1.100',
     '550e8400-e29b-41d4-a716-446655440001'),

    ('550e8400-e29b-41d4-a716-446655440002',
     'UPDATE',
     'user_profile',
     '550e8400-e29b-41d4-a716-446655440002',
     '{"bio": "Software engineer passionate about clean code"}',
     '192.168.1.100',
     '550e8400-e29b-41d4-a716-446655440002');

-- ============================================================================
-- SAMPLE EMAIL VERIFICATION TOKEN (for unverified user)
-- ============================================================================

INSERT INTO email_verification_tokens (user_id, token, expires_at)
VALUES
    ('550e8400-e29b-41d4-a716-446655440005',
     'verify_token_' || encode(gen_random_bytes(32), 'hex'),
     CURRENT_TIMESTAMP + INTERVAL '24 hours');

-- ============================================================================
-- VERIFICATION
-- ============================================================================

DO $$
DECLARE
    user_count INTEGER;
    profile_count INTEGER;
    role_assignment_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO user_count FROM users WHERE deleted_at IS NULL;
    SELECT COUNT(*) INTO profile_count FROM user_profiles;
    SELECT COUNT(*) INTO role_assignment_count FROM user_roles;

    RAISE NOTICE 'Seed data loaded:';
    RAISE NOTICE '  Users: %', user_count;
    RAISE NOTICE '  Profiles: %', profile_count;
    RAISE NOTICE '  Role assignments: %', role_assignment_count;

    IF user_count < 5 THEN
        RAISE EXCEPTION 'Seed data verification failed: Expected at least 5 users';
    END IF;
END $$;

COMMIT;

-- ============================================================================
-- TEST CREDENTIALS
-- ============================================================================

-- Password for all test users: User123! (or variations)
-- Hash algorithm: bcrypt with cost factor 12
--
-- Test Users:
-- 1. admin@example.com / Admin123! - Full admin access
-- 2. john.doe@example.com / User123! - Regular user
-- 3. jane.smith@example.com / User123! - Regular user
-- 4. bob.moderator@example.com / Mod123! - Moderator
-- 5. alice.guest@example.com / Guest123! - Guest (unverified)
-- 6. inactive@example.com - Inactive account

-- ============================================================================
-- QUERY EXAMPLES FOR TESTING
-- ============================================================================

-- View all users with roles
-- SELECT * FROM v_users_complete;

-- View active users only
-- SELECT * FROM v_active_users_summary;

-- View audit trail
-- SELECT * FROM user_audit_log ORDER BY created_at DESC;

-- Test soft delete
-- SELECT soft_delete_user('550e8400-e29b-41d4-a716-446655440006');
