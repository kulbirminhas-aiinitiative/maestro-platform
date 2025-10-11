-- Migration: 002_advanced_indexes.sql
-- Description: Advanced indexing strategy for optimal performance
-- Version: 002
-- Created: 2024-12-01

BEGIN;

-- ============================================================================
-- PERFORMANCE-CRITICAL INDEXES
-- ============================================================================

-- Organizations
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_organizations_slug
ON organizations(slug) WHERE deleted_at IS NULL;

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_organizations_domain
ON organizations(domain) WHERE domain IS NOT NULL AND deleted_at IS NULL;

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_organizations_subscription
ON organizations(subscription_plan, subscription_status)
WHERE deleted_at IS NULL;

-- Workspaces
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_workspaces_org_id
ON workspaces(organization_id) WHERE deleted_at IS NULL;

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_workspaces_org_name
ON workspaces(organization_id, name) WHERE deleted_at IS NULL;

-- Users
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_users_email_verified
ON users(email) WHERE email_verified = true AND deleted_at IS NULL;

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_users_last_login
ON users(last_login_at DESC) WHERE deleted_at IS NULL;

-- Organization Members
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_org_members_user_id
ON organization_members(user_id);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_org_members_org_role
ON organization_members(organization_id, role, status);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_org_members_status_invited
ON organization_members(status, invited_at) WHERE status = 'invited';

-- Workspace Members
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_workspace_members_user
ON workspace_members(user_id);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_workspace_members_workspace_role
ON workspace_members(workspace_id, role);

-- Boards
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_boards_workspace_id
ON boards(workspace_id) WHERE deleted_at IS NULL;

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_boards_workspace_position
ON boards(workspace_id, position) WHERE deleted_at IS NULL;

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_boards_folder_id
ON boards(folder_id) WHERE folder_id IS NOT NULL AND deleted_at IS NULL;

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_boards_created_by
ON boards(created_by, created_at DESC) WHERE deleted_at IS NULL;

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_boards_template_id
ON boards(template_id) WHERE template_id IS NOT NULL;

-- Board Columns
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_board_columns_board_position
ON board_columns(board_id, position);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_board_columns_type
ON board_columns(board_id, column_type);

-- Board Members
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_board_members_user
ON board_members(user_id);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_board_members_board_role
ON board_members(board_id, role);

-- Items (Most Critical)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_items_board_id
ON items(board_id) WHERE deleted_at IS NULL;

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_items_board_position
ON items(board_id, position) WHERE deleted_at IS NULL;

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_items_parent_id
ON items(parent_id) WHERE parent_id IS NOT NULL AND deleted_at IS NULL;

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_items_created_by
ON items(created_by, created_at DESC) WHERE deleted_at IS NULL;

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_items_updated_at
ON items(updated_at DESC) WHERE deleted_at IS NULL;

-- Item data JSONB indexes
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_items_status
ON items USING GIN ((item_data->'status'))
WHERE deleted_at IS NULL;

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_items_priority
ON items USING GIN ((item_data->'priority'))
WHERE deleted_at IS NULL;

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_items_due_date
ON items USING BTREE (CAST(item_data->>'due_date' AS TIMESTAMPTZ))
WHERE deleted_at IS NULL AND item_data->>'due_date' IS NOT NULL;

-- Item Assignments
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_item_assignments_user
ON item_assignments(user_id, assigned_at DESC);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_item_assignments_item
ON item_assignments(item_id);

-- Item Dependencies
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_item_dependencies_predecessor
ON item_dependencies(predecessor_id);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_item_dependencies_successor
ON item_dependencies(successor_id);

-- Comments
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_comments_item_id
ON comments(item_id, created_at DESC) WHERE deleted_at IS NULL;

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_comments_user_id
ON comments(user_id, created_at DESC) WHERE deleted_at IS NULL;

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_comments_parent_id
ON comments(parent_id) WHERE parent_id IS NOT NULL AND deleted_at IS NULL;

-- Time Entries
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_time_entries_item
ON time_entries(item_id, start_time DESC);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_time_entries_user
ON time_entries(user_id, start_time DESC);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_time_entries_billable
ON time_entries(is_billable, start_time DESC)
WHERE is_billable = true;

-- Files
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_files_org_id
ON files(organization_id, created_at DESC) WHERE deleted_at IS NULL;

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_files_uploaded_by
ON files(uploaded_by, created_at DESC) WHERE deleted_at IS NULL;

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_files_mime_type
ON files(mime_type) WHERE deleted_at IS NULL;

-- File Attachments
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_file_attachments_entity
ON file_attachments(entity_type, entity_id);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_file_attachments_file
ON file_attachments(file_id);

-- Activity Log (Partitioned)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_activity_log_org_created
ON activity_log(organization_id, created_at DESC);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_activity_log_user_created
ON activity_log(user_id, created_at DESC);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_activity_log_entity
ON activity_log(entity_type, entity_id, created_at DESC);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_activity_log_board
ON activity_log(board_id, created_at DESC)
WHERE board_id IS NOT NULL;

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_activity_log_item
ON activity_log(item_id, created_at DESC)
WHERE item_id IS NOT NULL;

-- Automation Rules
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_automation_rules_board
ON automation_rules(board_id) WHERE board_id IS NOT NULL;

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_automation_rules_workspace
ON automation_rules(workspace_id) WHERE workspace_id IS NOT NULL;

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_automation_rules_enabled
ON automation_rules(is_enabled, last_executed_at)
WHERE is_enabled = true;

-- Automation Executions (Partitioned)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_automation_executions_rule
ON automation_executions(rule_id, executed_at DESC);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_automation_executions_status
ON automation_executions(execution_status, executed_at DESC);

-- Webhooks
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_webhooks_org_active
ON webhooks(organization_id, is_active);

-- Webhook Deliveries
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_webhook_deliveries_webhook
ON webhook_deliveries(webhook_id, created_at DESC);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_webhook_deliveries_status
ON webhook_deliveries(status, next_retry_at)
WHERE status IN ('pending', 'failed');

-- ============================================================================
-- FULL-TEXT SEARCH INDEXES
-- ============================================================================

-- Items full-text search
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_items_search
ON items USING GIN (
    to_tsvector('english',
        name || ' ' ||
        COALESCE(description, '') || ' ' ||
        COALESCE(item_data::text, '')
    )
) WHERE deleted_at IS NULL;

-- Trigram search for fuzzy matching
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_items_name_trgm
ON items USING GIN (name gin_trgm_ops)
WHERE deleted_at IS NULL;

-- Comments full-text search
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_comments_search
ON comments USING GIN (to_tsvector('english', content))
WHERE deleted_at IS NULL;

-- Organizations search
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_organizations_search
ON organizations USING GIN (
    to_tsvector('english', name || ' ' || COALESCE(domain, ''))
) WHERE deleted_at IS NULL;

-- Users search
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_users_search
ON users USING GIN (
    to_tsvector('english',
        COALESCE(first_name, '') || ' ' ||
        COALESCE(last_name, '') || ' ' ||
        email
    )
) WHERE deleted_at IS NULL;

-- ============================================================================
-- COMPOSITE INDEXES FOR COMPLEX QUERIES
-- ============================================================================

-- Board item queries with status filter
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_items_board_status_position
ON items(board_id, (item_data->>'status'), position)
WHERE deleted_at IS NULL;

-- User activity across organization
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_user_org_activity
ON activity_log(user_id, organization_id, created_at DESC);

-- Item assignment by board
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_item_assignments_board_user
ON item_assignments(user_id, assigned_at DESC)
INCLUDE (item_id);

-- Time tracking aggregation
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_time_entries_user_date_billable
ON time_entries(user_id, DATE(start_time), is_billable);

-- Board member permissions
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_board_members_user_board_role
ON board_members(user_id, board_id, role);

-- File attachments by entity with file info
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_file_attachments_entity_file
ON file_attachments(entity_type, entity_id, attached_at DESC)
INCLUDE (file_id);

-- ============================================================================
-- PARTIAL INDEXES FOR SPECIFIC CONDITIONS
-- ============================================================================

-- Active organizations only
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_organizations_active
ON organizations(name, created_at DESC)
WHERE deleted_at IS NULL AND subscription_status = 'active';

-- Public board templates
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_board_templates_public
ON board_templates(category, usage_count DESC)
WHERE is_public = true;

-- Pending webhook deliveries
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_webhook_deliveries_pending
ON webhook_deliveries(created_at, attempt)
WHERE status = 'pending';

-- Failed automation executions
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_automation_executions_failed
ON automation_executions(executed_at DESC, rule_id)
WHERE execution_status = 'failed';

-- Recent activity (last 30 days)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_activity_log_recent
ON activity_log(organization_id, action, created_at DESC)
WHERE created_at > NOW() - INTERVAL '30 days';

-- ============================================================================
-- EXPRESSION INDEXES
-- ============================================================================

-- Lowercase email for case-insensitive searches
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_users_email_lower
ON users(LOWER(email)) WHERE deleted_at IS NULL;

-- Organization slug lowercase
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_organizations_slug_lower
ON organizations(LOWER(slug)) WHERE deleted_at IS NULL;

-- Item name length for analytics
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_items_name_length
ON items(LENGTH(name)) WHERE deleted_at IS NULL;

-- Item data keys for dynamic column queries
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_items_data_keys
ON items USING GIN ((item_data ? 'status'), (item_data ? 'priority'))
WHERE deleted_at IS NULL;

-- ============================================================================
-- COVERING INDEXES (INCLUDE COLUMNS)
-- ============================================================================

-- Board queries with included columns
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_boards_workspace_covering
ON boards(workspace_id, position)
INCLUDE (name, description, settings, is_private)
WHERE deleted_at IS NULL;

-- Item queries with included data
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_items_board_covering
ON items(board_id, position)
INCLUDE (name, description, item_data, created_by, updated_at)
WHERE deleted_at IS NULL;

-- User organization membership covering
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_org_members_covering
ON organization_members(user_id, organization_id)
INCLUDE (role, status, joined_at);

-- ============================================================================
-- STATISTICS AND MAINTENANCE
-- ============================================================================

-- Update table statistics for better query planning
ANALYZE organizations;
ANALYZE workspaces;
ANALYZE users;
ANALYZE organization_members;
ANALYZE workspace_members;
ANALYZE boards;
ANALYZE board_columns;
ANALYZE items;
ANALYZE item_assignments;
ANALYZE comments;
ANALYZE time_entries;
ANALYZE files;
ANALYZE file_attachments;
ANALYZE automation_rules;
ANALYZE automation_executions;
ANALYZE activity_log;

-- Record migration
INSERT INTO schema_migrations (version, name, checksum)
VALUES ('002', 'advanced_indexes', 'advanced_indexes_checksum_placeholder');

COMMIT;

-- ============================================================================
-- DOWN MIGRATION
-- ============================================================================

-- BEGIN;
--
-- -- Drop all indexes created in this migration
-- DROP INDEX CONCURRENTLY IF EXISTS idx_organizations_slug;
-- DROP INDEX CONCURRENTLY IF EXISTS idx_organizations_domain;
-- DROP INDEX CONCURRENTLY IF EXISTS idx_organizations_subscription;
-- DROP INDEX CONCURRENTLY IF EXISTS idx_workspaces_org_id;
-- DROP INDEX CONCURRENTLY IF EXISTS idx_workspaces_org_name;
-- DROP INDEX CONCURRENTLY IF EXISTS idx_users_email_verified;
-- DROP INDEX CONCURRENTLY IF EXISTS idx_users_last_login;
-- DROP INDEX CONCURRENTLY IF EXISTS idx_org_members_user_id;
-- DROP INDEX CONCURRENTLY IF EXISTS idx_org_members_org_role;
-- DROP INDEX CONCURRENTLY IF EXISTS idx_org_members_status_invited;
-- DROP INDEX CONCURRENTLY IF EXISTS idx_workspace_members_user;
-- DROP INDEX CONCURRENTLY IF EXISTS idx_workspace_members_workspace_role;
-- DROP INDEX CONCURRENTLY IF EXISTS idx_boards_workspace_id;
-- DROP INDEX CONCURRENTLY IF EXISTS idx_boards_workspace_position;
-- DROP INDEX CONCURRENTLY IF EXISTS idx_boards_folder_id;
-- DROP INDEX CONCURRENTLY IF EXISTS idx_boards_created_by;
-- DROP INDEX CONCURRENTLY IF EXISTS idx_boards_template_id;
-- DROP INDEX CONCURRENTLY IF EXISTS idx_board_columns_board_position;
-- DROP INDEX CONCURRENTLY IF EXISTS idx_board_columns_type;
-- DROP INDEX CONCURRENTLY IF EXISTS idx_board_members_user;
-- DROP INDEX CONCURRENTLY IF EXISTS idx_board_members_board_role;
-- DROP INDEX CONCURRENTLY IF EXISTS idx_items_board_id;
-- DROP INDEX CONCURRENTLY IF EXISTS idx_items_board_position;
-- DROP INDEX CONCURRENTLY IF EXISTS idx_items_parent_id;
-- DROP INDEX CONCURRENTLY IF EXISTS idx_items_created_by;
-- DROP INDEX CONCURRENTLY IF EXISTS idx_items_updated_at;
-- DROP INDEX CONCURRENTLY IF EXISTS idx_items_status;
-- DROP INDEX CONCURRENTLY IF EXISTS idx_items_priority;
-- DROP INDEX CONCURRENTLY IF EXISTS idx_items_due_date;
-- DROP INDEX CONCURRENTLY IF EXISTS idx_item_assignments_user;
-- DROP INDEX CONCURRENTLY IF EXISTS idx_item_assignments_item;
-- DROP INDEX CONCURRENTLY IF EXISTS idx_item_dependencies_predecessor;
-- DROP INDEX CONCURRENTLY IF EXISTS idx_item_dependencies_successor;
-- DROP INDEX CONCURRENTLY IF EXISTS idx_comments_item_id;
-- DROP INDEX CONCURRENTLY IF EXISTS idx_comments_user_id;
-- DROP INDEX CONCURRENTLY IF EXISTS idx_comments_parent_id;
-- DROP INDEX CONCURRENTLY IF EXISTS idx_time_entries_item;
-- DROP INDEX CONCURRENTLY IF EXISTS idx_time_entries_user;
-- DROP INDEX CONCURRENTLY IF EXISTS idx_time_entries_billable;
-- DROP INDEX CONCURRENTLY IF EXISTS idx_files_org_id;
-- DROP INDEX CONCURRENTLY IF EXISTS idx_files_uploaded_by;
-- DROP INDEX CONCURRENTLY IF EXISTS idx_files_mime_type;
-- DROP INDEX CONCURRENTLY IF EXISTS idx_file_attachments_entity;
-- DROP INDEX CONCURRENTLY IF EXISTS idx_file_attachments_file;
-- DROP INDEX CONCURRENTLY IF EXISTS idx_activity_log_org_created;
-- DROP INDEX CONCURRENTLY IF EXISTS idx_activity_log_user_created;
-- DROP INDEX CONCURRENTLY IF EXISTS idx_activity_log_entity;
-- DROP INDEX CONCURRENTLY IF EXISTS idx_activity_log_board;
-- DROP INDEX CONCURRENTLY IF EXISTS idx_activity_log_item;
-- DROP INDEX CONCURRENTLY IF EXISTS idx_automation_rules_board;
-- DROP INDEX CONCURRENTLY IF EXISTS idx_automation_rules_workspace;
-- DROP INDEX CONCURRENTLY IF EXISTS idx_automation_rules_enabled;
-- DROP INDEX CONCURRENTLY IF EXISTS idx_automation_executions_rule;
-- DROP INDEX CONCURRENTLY IF EXISTS idx_automation_executions_status;
-- DROP INDEX CONCURRENTLY IF EXISTS idx_webhooks_org_active;
-- DROP INDEX CONCURRENTLY IF EXISTS idx_webhook_deliveries_webhook;
-- DROP INDEX CONCURRENTLY IF EXISTS idx_webhook_deliveries_status;
-- DROP INDEX CONCURRENTLY IF EXISTS idx_items_search;
-- DROP INDEX CONCURRENTLY IF EXISTS idx_items_name_trgm;
-- DROP INDEX CONCURRENTLY IF EXISTS idx_comments_search;
-- DROP INDEX CONCURRENTLY IF EXISTS idx_organizations_search;
-- DROP INDEX CONCURRENTLY IF EXISTS idx_users_search;
-- DROP INDEX CONCURRENTLY IF EXISTS idx_items_board_status_position;
-- DROP INDEX CONCURRENTLY IF EXISTS idx_user_org_activity;
-- DROP INDEX CONCURRENTLY IF EXISTS idx_item_assignments_board_user;
-- DROP INDEX CONCURRENTLY IF EXISTS idx_time_entries_user_date_billable;
-- DROP INDEX CONCURRENTLY IF EXISTS idx_board_members_user_board_role;
-- DROP INDEX CONCURRENTLY IF EXISTS idx_file_attachments_entity_file;
-- DROP INDEX CONCURRENTLY IF EXISTS idx_organizations_active;
-- DROP INDEX CONCURRENTLY IF EXISTS idx_board_templates_public;
-- DROP INDEX CONCURRENTLY IF EXISTS idx_webhook_deliveries_pending;
-- DROP INDEX CONCURRENTLY IF EXISTS idx_automation_executions_failed;
-- DROP INDEX CONCURRENTLY IF EXISTS idx_activity_log_recent;
-- DROP INDEX CONCURRENTLY IF EXISTS idx_users_email_lower;
-- DROP INDEX CONCURRENTLY IF EXISTS idx_organizations_slug_lower;
-- DROP INDEX CONCURRENTLY IF EXISTS idx_items_name_length;
-- DROP INDEX CONCURRENTLY IF EXISTS idx_items_data_keys;
-- DROP INDEX CONCURRENTLY IF EXISTS idx_boards_workspace_covering;
-- DROP INDEX CONCURRENTLY IF EXISTS idx_items_board_covering;
-- DROP INDEX CONCURRENTLY IF EXISTS idx_org_members_covering;
--
-- -- Remove migration record
-- DELETE FROM schema_migrations WHERE version = '002';
--
-- COMMIT;