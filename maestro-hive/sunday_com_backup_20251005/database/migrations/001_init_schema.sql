-- Migration: 001_init_schema.sql
-- Description: Initialize Sunday.com database schema with core tables
-- Version: 1.0.0
-- Created: 2024-12-01
-- Requires: PostgreSQL 14+, Extensions: uuid-ossp, pg_trgm, btree_gin

BEGIN;

-- ============================================================================
-- SCHEMA VERSIONING SYSTEM
-- ============================================================================

-- Create schema migrations table if not exists
CREATE TABLE IF NOT EXISTS schema_migrations (
    version VARCHAR(20) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    applied_at TIMESTAMPTZ DEFAULT NOW(),
    applied_by VARCHAR(100) DEFAULT current_user,
    checksum VARCHAR(64),
    execution_time_ms INTEGER
);

-- ============================================================================
-- CORE EXTENSIONS
-- ============================================================================

-- Required PostgreSQL extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";
CREATE EXTENSION IF NOT EXISTS "btree_gin";
CREATE EXTENSION IF NOT EXISTS "pg_stat_statements";

-- ============================================================================
-- ORGANIZATIONS & WORKSPACES
-- ============================================================================

CREATE TABLE organizations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(100) UNIQUE NOT NULL,
    domain VARCHAR(255),
    settings JSONB DEFAULT '{}',
    subscription_plan VARCHAR(50) DEFAULT 'free',
    subscription_status VARCHAR(20) DEFAULT 'active',
    billing_email VARCHAR(320),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    deleted_at TIMESTAMPTZ,

    CONSTRAINT organizations_name_length CHECK (length(name) >= 2),
    CONSTRAINT organizations_slug_format CHECK (slug ~ '^[a-z0-9-]+$'),
    CONSTRAINT organizations_subscription_plan_valid
        CHECK (subscription_plan IN ('free', 'basic', 'standard', 'enterprise')),
    CONSTRAINT organizations_subscription_status_valid
        CHECK (subscription_status IN ('active', 'suspended', 'cancelled', 'trial'))
);

CREATE TABLE workspaces (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    color VARCHAR(7) DEFAULT '#6B7280',
    settings JSONB DEFAULT '{}',
    is_private BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    deleted_at TIMESTAMPTZ,

    CONSTRAINT workspaces_name_length CHECK (length(name) >= 1),
    CONSTRAINT workspaces_color_format CHECK (color ~ '^#[0-9A-Fa-f]{6}$'),
    CONSTRAINT workspaces_organization_name_unique
        UNIQUE (organization_id, name) DEFERRABLE INITIALLY DEFERRED
);

-- ============================================================================
-- USERS & AUTHENTICATION
-- ============================================================================

CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(320) UNIQUE NOT NULL,
    email_verified BOOLEAN DEFAULT FALSE,
    password_hash VARCHAR(255), -- NULL for SSO users
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    avatar_url TEXT,
    timezone VARCHAR(50) DEFAULT 'UTC',
    locale VARCHAR(10) DEFAULT 'en',
    settings JSONB DEFAULT '{}',
    last_login_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    deleted_at TIMESTAMPTZ,

    CONSTRAINT users_email_format CHECK (email ~ '^[^@]+@[^@]+\.[^@]+$'),
    CONSTRAINT users_timezone_valid CHECK (timezone IS NULL OR length(timezone) <= 50),
    CONSTRAINT users_locale_valid CHECK (locale ~ '^[a-z]{2}(_[A-Z]{2})?$')
);

CREATE TABLE organization_members (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role VARCHAR(50) NOT NULL DEFAULT 'member',
    status VARCHAR(20) DEFAULT 'active',
    invited_by UUID REFERENCES users(id),
    invited_at TIMESTAMPTZ,
    joined_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    CONSTRAINT org_members_role_valid CHECK (role IN ('owner', 'admin', 'member', 'viewer')),
    CONSTRAINT org_members_status_valid CHECK (status IN ('active', 'invited', 'suspended')),
    CONSTRAINT org_members_unique UNIQUE (organization_id, user_id)
);

CREATE TABLE workspace_members (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role VARCHAR(50) NOT NULL DEFAULT 'member',
    permissions JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    CONSTRAINT workspace_members_role_valid CHECK (role IN ('admin', 'member', 'viewer')),
    CONSTRAINT workspace_members_unique UNIQUE (workspace_id, user_id)
);

-- ============================================================================
-- FOLDERS
-- ============================================================================

CREATE TABLE folders (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    color VARCHAR(7) DEFAULT '#6B7280',
    position INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    CONSTRAINT folders_name_length CHECK (length(name) >= 1),
    CONSTRAINT folders_color_format CHECK (color ~ '^#[0-9A-Fa-f]{6}$')
);

-- ============================================================================
-- BOARD TEMPLATES
-- ============================================================================

CREATE TABLE board_templates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    category VARCHAR(100),
    template_data JSONB NOT NULL,
    is_public BOOLEAN DEFAULT FALSE,
    created_by UUID REFERENCES users(id),
    organization_id UUID REFERENCES organizations(id),
    usage_count INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    CONSTRAINT board_templates_name_length CHECK (length(name) >= 1),
    CONSTRAINT board_templates_usage_count_positive CHECK (usage_count >= 0)
);

-- ============================================================================
-- BOARDS & PROJECTS
-- ============================================================================

CREATE TABLE boards (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    template_id UUID REFERENCES board_templates(id),
    settings JSONB DEFAULT '{}',
    view_settings JSONB DEFAULT '{}',
    is_private BOOLEAN DEFAULT FALSE,
    folder_id UUID REFERENCES folders(id),
    position INTEGER,
    created_by UUID NOT NULL REFERENCES users(id),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    deleted_at TIMESTAMPTZ,

    CONSTRAINT boards_name_length CHECK (length(name) >= 1)
);

CREATE TABLE board_columns (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    board_id UUID NOT NULL REFERENCES boards(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    column_type VARCHAR(50) NOT NULL,
    settings JSONB DEFAULT '{}',
    validation_rules JSONB DEFAULT '{}',
    position INTEGER NOT NULL,
    is_required BOOLEAN DEFAULT FALSE,
    is_visible BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    CONSTRAINT board_columns_name_length CHECK (length(name) >= 1),
    CONSTRAINT board_columns_type_valid CHECK (
        column_type IN ('text', 'number', 'status', 'date', 'people', 'dropdown',
                       'checkbox', 'rating', 'progress', 'timeline', 'file', 'link')
    ),
    CONSTRAINT board_columns_position_unique UNIQUE (board_id, position)
);

CREATE TABLE board_members (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    board_id UUID NOT NULL REFERENCES boards(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role VARCHAR(50) NOT NULL DEFAULT 'member',
    permissions JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    CONSTRAINT board_members_role_valid CHECK (role IN ('owner', 'admin', 'member', 'viewer')),
    CONSTRAINT board_members_unique UNIQUE (board_id, user_id)
);

-- ============================================================================
-- ITEMS & TASKS
-- ============================================================================

CREATE TABLE items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    board_id UUID NOT NULL REFERENCES boards(id) ON DELETE CASCADE,
    parent_id UUID REFERENCES items(id),
    name VARCHAR(500) NOT NULL,
    description TEXT,
    item_data JSONB DEFAULT '{}',
    position DECIMAL(20,10) DEFAULT 1.0,
    created_by UUID NOT NULL REFERENCES users(id),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    deleted_at TIMESTAMPTZ,

    CONSTRAINT items_name_length CHECK (length(name) >= 1),
    CONSTRAINT items_no_self_parent CHECK (id != parent_id)
);

CREATE TABLE item_assignments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    item_id UUID NOT NULL REFERENCES items(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    assigned_by UUID NOT NULL REFERENCES users(id),
    assigned_at TIMESTAMPTZ DEFAULT NOW(),

    CONSTRAINT item_assignments_unique UNIQUE (item_id, user_id)
);

CREATE TABLE item_dependencies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    predecessor_id UUID NOT NULL REFERENCES items(id) ON DELETE CASCADE,
    successor_id UUID NOT NULL REFERENCES items(id) ON DELETE CASCADE,
    dependency_type VARCHAR(20) DEFAULT 'blocks',
    created_by UUID NOT NULL REFERENCES users(id),
    created_at TIMESTAMPTZ DEFAULT NOW(),

    CONSTRAINT item_deps_type_valid CHECK (dependency_type IN ('blocks', 'related')),
    CONSTRAINT item_deps_unique UNIQUE (predecessor_id, successor_id),
    CONSTRAINT item_deps_no_self CHECK (predecessor_id != successor_id)
);

-- ============================================================================
-- TIME TRACKING
-- ============================================================================

CREATE TABLE time_entries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    item_id UUID NOT NULL REFERENCES items(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    description TEXT,
    start_time TIMESTAMPTZ NOT NULL,
    end_time TIMESTAMPTZ,
    duration_seconds INTEGER,
    is_billable BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    CONSTRAINT time_entries_duration_positive CHECK (duration_seconds > 0),
    CONSTRAINT time_entries_time_order CHECK (end_time IS NULL OR end_time > start_time)
);

-- ============================================================================
-- COMMENTS & COLLABORATION
-- ============================================================================

CREATE TABLE comments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    item_id UUID NOT NULL REFERENCES items(id) ON DELETE CASCADE,
    parent_id UUID REFERENCES comments(id),
    user_id UUID NOT NULL REFERENCES users(id),
    content TEXT NOT NULL,
    content_type VARCHAR(20) DEFAULT 'text',
    mentions JSONB DEFAULT '[]',
    attachments JSONB DEFAULT '[]',
    is_edited BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    deleted_at TIMESTAMPTZ,

    CONSTRAINT comments_content_length CHECK (length(content) >= 1),
    CONSTRAINT comments_content_type_valid CHECK (content_type IN ('text', 'markdown'))
);

-- ============================================================================
-- FILES & ATTACHMENTS
-- ============================================================================

CREATE TABLE files (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id),
    original_name VARCHAR(255) NOT NULL,
    file_key VARCHAR(500) NOT NULL UNIQUE,
    file_size BIGINT NOT NULL,
    mime_type VARCHAR(100),
    checksum VARCHAR(64),
    thumbnail_key VARCHAR(500),
    uploaded_by UUID NOT NULL REFERENCES users(id),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    deleted_at TIMESTAMPTZ,

    CONSTRAINT files_size_positive CHECK (file_size > 0),
    CONSTRAINT files_name_length CHECK (length(original_name) >= 1)
);

CREATE TABLE file_attachments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    file_id UUID NOT NULL REFERENCES files(id) ON DELETE CASCADE,
    entity_type VARCHAR(50) NOT NULL,
    entity_id UUID NOT NULL,
    attached_by UUID NOT NULL REFERENCES users(id),
    attached_at TIMESTAMPTZ DEFAULT NOW(),

    CONSTRAINT file_attachments_entity_type_valid
        CHECK (entity_type IN ('item', 'comment', 'board'))
);

-- ============================================================================
-- AUTOMATION & WORKFLOWS
-- ============================================================================

CREATE TABLE automation_rules (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    board_id UUID REFERENCES boards(id) ON DELETE CASCADE,
    workspace_id UUID REFERENCES workspaces(id) ON DELETE CASCADE,
    organization_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    trigger_config JSONB NOT NULL,
    condition_config JSONB DEFAULT '{}',
    action_config JSONB NOT NULL,
    is_enabled BOOLEAN DEFAULT TRUE,
    execution_count INTEGER DEFAULT 0,
    last_executed_at TIMESTAMPTZ,
    created_by UUID NOT NULL REFERENCES users(id),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    CONSTRAINT automation_rules_name_length CHECK (length(name) >= 1),
    CONSTRAINT automation_rules_execution_count_positive CHECK (execution_count >= 0),
    CONSTRAINT automation_rules_scope_check CHECK (
        (board_id IS NOT NULL AND workspace_id IS NULL AND organization_id IS NULL) OR
        (board_id IS NULL AND workspace_id IS NOT NULL AND organization_id IS NULL) OR
        (board_id IS NULL AND workspace_id IS NULL AND organization_id IS NOT NULL)
    )
);

-- Create partitioned table for automation executions
CREATE TABLE automation_executions (
    id UUID DEFAULT gen_random_uuid(),
    rule_id UUID NOT NULL REFERENCES automation_rules(id) ON DELETE CASCADE,
    item_id UUID REFERENCES items(id),
    trigger_data JSONB,
    execution_status VARCHAR(20) NOT NULL,
    error_message TEXT,
    execution_time_ms INTEGER,
    executed_at TIMESTAMPTZ DEFAULT NOW(),

    CONSTRAINT automation_executions_status_valid
        CHECK (execution_status IN ('success', 'failed', 'skipped')),
    CONSTRAINT automation_executions_execution_time_positive
        CHECK (execution_time_ms > 0),
    PRIMARY KEY (id, executed_at)
) PARTITION BY RANGE (executed_at);

-- Create initial partition for automation executions
CREATE TABLE automation_executions_2024_12 PARTITION OF automation_executions
    FOR VALUES FROM ('2024-12-01') TO ('2025-01-01');

-- ============================================================================
-- ACTIVITY & AUDIT LOGS
-- ============================================================================

-- Create partitioned activity log table
CREATE TABLE activity_log (
    id UUID DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id),
    workspace_id UUID REFERENCES workspaces(id),
    board_id UUID REFERENCES boards(id),
    item_id UUID REFERENCES items(id),
    user_id UUID NOT NULL REFERENCES users(id),
    action VARCHAR(100) NOT NULL,
    entity_type VARCHAR(50) NOT NULL,
    entity_id UUID NOT NULL,
    old_values JSONB,
    new_values JSONB,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),

    PRIMARY KEY (id, created_at)
) PARTITION BY RANGE (created_at);

-- Create initial partition for activity log
CREATE TABLE activity_log_2024_12 PARTITION OF activity_log
    FOR VALUES FROM ('2024-12-01') TO ('2025-01-01');

-- ============================================================================
-- WEBHOOKS
-- ============================================================================

CREATE TABLE webhooks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    url TEXT NOT NULL,
    events TEXT[] NOT NULL,
    secret VARCHAR(255) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    filters JSONB DEFAULT '{}',
    created_by UUID NOT NULL REFERENCES users(id),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    CONSTRAINT webhooks_url_format CHECK (url ~ '^https?://'),
    CONSTRAINT webhooks_events_not_empty CHECK (array_length(events, 1) > 0)
);

CREATE TABLE webhook_deliveries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    webhook_id UUID NOT NULL REFERENCES webhooks(id) ON DELETE CASCADE,
    event VARCHAR(100) NOT NULL,
    payload JSONB NOT NULL,
    response JSONB,
    status VARCHAR(20) DEFAULT 'pending',
    attempt INTEGER DEFAULT 1,
    delivered_at TIMESTAMPTZ,
    next_retry_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),

    CONSTRAINT webhook_deliveries_status_valid
        CHECK (status IN ('pending', 'delivered', 'failed', 'abandoned')),
    CONSTRAINT webhook_deliveries_attempt_positive CHECK (attempt > 0)
);

-- ============================================================================
-- RECORD MIGRATION
-- ============================================================================

INSERT INTO schema_migrations (version, name, checksum)
VALUES ('001', 'init_schema', 'sha256_placeholder');

COMMIT;