-- Migration: 003_data_integrity.sql
-- Description: Comprehensive data integrity constraints and validation triggers
-- Version: 003
-- Created: 2024-12-01

BEGIN;

-- ============================================================================
-- DATA VALIDATION FUNCTIONS
-- ============================================================================

-- Validate email format
CREATE OR REPLACE FUNCTION validate_email(email_address TEXT)
RETURNS BOOLEAN AS $$
BEGIN
    RETURN email_address ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$';
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- Validate URL format
CREATE OR REPLACE FUNCTION validate_url(url_text TEXT)
RETURNS BOOLEAN AS $$
BEGIN
    RETURN url_text ~* '^https?://[^\s/$.?#].[^\s]*$';
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- Validate JSON structure
CREATE OR REPLACE FUNCTION validate_json_keys(json_data JSONB, required_keys TEXT[])
RETURNS BOOLEAN AS $$
DECLARE
    key TEXT;
BEGIN
    FOREACH key IN ARRAY required_keys
    LOOP
        IF NOT json_data ? key THEN
            RETURN FALSE;
        END IF;
    END LOOP;
    RETURN TRUE;
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- Validate item data based on column type
CREATE OR REPLACE FUNCTION validate_item_data(board_id_param UUID, item_data_param JSONB)
RETURNS BOOLEAN AS $$
DECLARE
    column_record RECORD;
    column_value TEXT;
    validation_rules JSONB;
BEGIN
    -- Check each column's data against its validation rules
    FOR column_record IN
        SELECT name, column_type, validation_rules
        FROM board_columns
        WHERE board_id = board_id_param AND is_required = true
    LOOP
        -- Check if required field is present
        IF NOT item_data_param ? column_record.name THEN
            RETURN FALSE;
        END IF;

        column_value := item_data_param ->> column_record.name;
        validation_rules := column_record.validation_rules;

        -- Type-specific validation
        CASE column_record.column_type
            WHEN 'number' THEN
                IF NOT (column_value ~ '^-?\d+\.?\d*$') THEN
                    RETURN FALSE;
                END IF;
            WHEN 'date' THEN
                IF NOT (column_value ~ '^\d{4}-\d{2}-\d{2}$') THEN
                    RETURN FALSE;
                END IF;
            WHEN 'email' THEN
                IF NOT validate_email(column_value) THEN
                    RETURN FALSE;
                END IF;
            WHEN 'url' THEN
                IF NOT validate_url(column_value) THEN
                    RETURN FALSE;
                END IF;
            ELSE
                -- Text and other types - just check not empty if required
                IF column_value IS NULL OR trim(column_value) = '' THEN
                    RETURN FALSE;
                END IF;
        END CASE;

        -- Apply custom validation rules
        IF validation_rules IS NOT NULL THEN
            -- Min length validation
            IF validation_rules ? 'min_length' THEN
                IF length(column_value) < (validation_rules->>'min_length')::int THEN
                    RETURN FALSE;
                END IF;
            END IF;

            -- Max length validation
            IF validation_rules ? 'max_length' THEN
                IF length(column_value) > (validation_rules->>'max_length')::int THEN
                    RETURN FALSE;
                END IF;
            END IF;

            -- Pattern validation
            IF validation_rules ? 'pattern' THEN
                IF NOT (column_value ~ (validation_rules->>'pattern')) THEN
                    RETURN FALSE;
                END IF;
            END IF;

            -- Allowed values validation
            IF validation_rules ? 'allowed_values' THEN
                IF NOT (column_value = ANY(
                    SELECT jsonb_array_elements_text(validation_rules->'allowed_values')
                )) THEN
                    RETURN FALSE;
                END IF;
            END IF;
        END IF;
    END LOOP;

    RETURN TRUE;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- AUDIT LOGGING FUNCTIONS
-- ============================================================================

-- Generic audit logging function
CREATE OR REPLACE FUNCTION log_activity(
    org_id UUID,
    workspace_id_param UUID DEFAULT NULL,
    board_id_param UUID DEFAULT NULL,
    item_id_param UUID DEFAULT NULL,
    user_id_param UUID,
    action_param TEXT,
    entity_type_param TEXT,
    entity_id_param UUID,
    old_values_param JSONB DEFAULT NULL,
    new_values_param JSONB DEFAULT NULL,
    metadata_param JSONB DEFAULT '{}'::JSONB
)
RETURNS VOID AS $$
BEGIN
    INSERT INTO activity_log (
        organization_id,
        workspace_id,
        board_id,
        item_id,
        user_id,
        action,
        entity_type,
        entity_id,
        old_values,
        new_values,
        metadata
    ) VALUES (
        org_id,
        workspace_id_param,
        board_id_param,
        item_id_param,
        user_id_param,
        action_param,
        entity_type_param,
        entity_id_param,
        old_values_param,
        new_values_param,
        metadata_param
    );
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- TRIGGER FUNCTIONS
-- ============================================================================

-- Update timestamps trigger
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Soft delete cascade trigger for boards
CREATE OR REPLACE FUNCTION soft_delete_board_items()
RETURNS TRIGGER AS $$
BEGIN
    -- When a board is soft deleted, soft delete all its items
    IF NEW.deleted_at IS NOT NULL AND (OLD.deleted_at IS NULL OR OLD.deleted_at != NEW.deleted_at) THEN
        UPDATE items
        SET deleted_at = NEW.deleted_at,
            updated_at = NOW()
        WHERE board_id = NEW.id AND deleted_at IS NULL;

        -- Log the cascade delete
        PERFORM log_activity(
            (SELECT organization_id FROM workspaces WHERE id = NEW.workspace_id),
            NEW.workspace_id,
            NEW.id,
            NULL,
            NEW.created_by,
            'board_items_soft_deleted',
            'board',
            NEW.id,
            NULL,
            jsonb_build_object('cascaded_items', (
                SELECT count(*) FROM items WHERE board_id = NEW.id AND deleted_at = NEW.deleted_at
            ))
        );
    END IF;

    -- When a board is restored, restore all its items
    IF OLD.deleted_at IS NOT NULL AND NEW.deleted_at IS NULL THEN
        UPDATE items
        SET deleted_at = NULL,
            updated_at = NOW()
        WHERE board_id = NEW.id AND deleted_at = OLD.deleted_at;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Item hierarchy validation trigger
CREATE OR REPLACE FUNCTION validate_item_hierarchy()
RETURNS TRIGGER AS $$
DECLARE
    current_parent_id UUID;
    depth_counter INT := 0;
    max_depth INT := 10; -- Prevent infinite recursion
BEGIN
    -- Prevent self-referencing
    IF NEW.parent_id = NEW.id THEN
        RAISE EXCEPTION 'Item cannot be its own parent';
    END IF;

    -- Check for circular references
    IF NEW.parent_id IS NOT NULL THEN
        current_parent_id := NEW.parent_id;

        WHILE current_parent_id IS NOT NULL AND depth_counter < max_depth LOOP
            IF current_parent_id = NEW.id THEN
                RAISE EXCEPTION 'Circular reference detected in item hierarchy';
            END IF;

            SELECT parent_id INTO current_parent_id
            FROM items
            WHERE id = current_parent_id AND deleted_at IS NULL;

            depth_counter := depth_counter + 1;
        END LOOP;

        IF depth_counter >= max_depth THEN
            RAISE EXCEPTION 'Item hierarchy too deep (max: %)', max_depth;
        END IF;

        -- Ensure parent exists and is in the same board
        IF NOT EXISTS (
            SELECT 1 FROM items
            WHERE id = NEW.parent_id
            AND board_id = NEW.board_id
            AND deleted_at IS NULL
        ) THEN
            RAISE EXCEPTION 'Parent item must exist in the same board';
        END IF;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Item data validation trigger
CREATE OR REPLACE FUNCTION validate_item_data_trigger()
RETURNS TRIGGER AS $$
BEGIN
    -- Validate item data against board column rules
    IF NOT validate_item_data(NEW.board_id, NEW.item_data) THEN
        RAISE EXCEPTION 'Item data validation failed for board %', NEW.board_id;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- User email validation trigger
CREATE OR REPLACE FUNCTION validate_user_email_trigger()
RETURNS TRIGGER AS $$
BEGIN
    IF NOT validate_email(NEW.email) THEN
        RAISE EXCEPTION 'Invalid email format: %', NEW.email;
    END IF;

    -- Convert email to lowercase for consistency
    NEW.email := LOWER(NEW.email);

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Organization membership validation trigger
CREATE OR REPLACE FUNCTION validate_organization_membership()
RETURNS TRIGGER AS $$
BEGIN
    -- Ensure user exists
    IF NOT EXISTS (SELECT 1 FROM users WHERE id = NEW.user_id AND deleted_at IS NULL) THEN
        RAISE EXCEPTION 'User does not exist or is deleted';
    END IF;

    -- Ensure organization exists
    IF NOT EXISTS (SELECT 1 FROM organizations WHERE id = NEW.organization_id AND deleted_at IS NULL) THEN
        RAISE EXCEPTION 'Organization does not exist or is deleted';
    END IF;

    -- Set joined_at when status changes to active
    IF OLD.status != 'active' AND NEW.status = 'active' THEN
        NEW.joined_at := NOW();
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Workspace membership validation trigger
CREATE OR REPLACE FUNCTION validate_workspace_membership()
RETURNS TRIGGER AS $$
BEGIN
    -- Ensure user is a member of the organization
    IF NOT EXISTS (
        SELECT 1 FROM organization_members om
        JOIN workspaces w ON w.organization_id = om.organization_id
        WHERE om.user_id = NEW.user_id
        AND w.id = NEW.workspace_id
        AND om.status = 'active'
    ) THEN
        RAISE EXCEPTION 'User must be an active organization member to join workspace';
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- File size validation trigger
CREATE OR REPLACE FUNCTION validate_file_size()
RETURNS TRIGGER AS $$
DECLARE
    max_file_size BIGINT := 100 * 1024 * 1024; -- 100MB default
    org_settings JSONB;
BEGIN
    -- Get organization-specific file size limit
    SELECT settings INTO org_settings
    FROM organizations
    WHERE id = NEW.organization_id;

    IF org_settings ? 'max_file_size' THEN
        max_file_size := (org_settings->>'max_file_size')::BIGINT;
    END IF;

    IF NEW.file_size > max_file_size THEN
        RAISE EXCEPTION 'File size (%) exceeds maximum allowed size (%)',
            pg_size_pretty(NEW.file_size),
            pg_size_pretty(max_file_size);
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Automation rule validation trigger
CREATE OR REPLACE FUNCTION validate_automation_rule()
RETURNS TRIGGER AS $$
BEGIN
    -- Validate trigger configuration
    IF NOT (NEW.trigger_config ? 'event' AND NEW.trigger_config ? 'conditions') THEN
        RAISE EXCEPTION 'Automation rule must have event and conditions in trigger_config';
    END IF;

    -- Validate action configuration
    IF NOT (NEW.action_config ? 'type' AND NEW.action_config ? 'parameters') THEN
        RAISE EXCEPTION 'Automation rule must have type and parameters in action_config';
    END IF;

    -- Ensure rule has valid scope
    IF (NEW.board_id IS NULL AND NEW.workspace_id IS NULL AND NEW.organization_id IS NULL) THEN
        RAISE EXCEPTION 'Automation rule must have board, workspace, or organization scope';
    END IF;

    -- Prevent multiple scope assignments
    IF (
        (NEW.board_id IS NOT NULL AND NEW.workspace_id IS NOT NULL) OR
        (NEW.board_id IS NOT NULL AND NEW.organization_id IS NOT NULL) OR
        (NEW.workspace_id IS NOT NULL AND NEW.organization_id IS NOT NULL)
    ) THEN
        RAISE EXCEPTION 'Automation rule can only have one scope (board, workspace, or organization)';
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Activity log partition creation trigger
CREATE OR REPLACE FUNCTION create_activity_log_partition()
RETURNS TRIGGER AS $$
DECLARE
    partition_date TEXT;
    partition_name TEXT;
    start_date TEXT;
    end_date TEXT;
BEGIN
    -- Calculate partition name based on month
    partition_date := to_char(NEW.created_at, 'YYYY_MM');
    partition_name := 'activity_log_' || partition_date;

    -- Check if partition exists
    IF NOT EXISTS (
        SELECT 1 FROM pg_tables
        WHERE schemaname = 'public'
        AND tablename = partition_name
    ) THEN
        -- Create partition for the month
        start_date := to_char(date_trunc('month', NEW.created_at), 'YYYY-MM-DD');
        end_date := to_char(date_trunc('month', NEW.created_at) + interval '1 month', 'YYYY-MM-DD');

        EXECUTE format(
            'CREATE TABLE %I PARTITION OF activity_log
             FOR VALUES FROM (%L) TO (%L)',
            partition_name, start_date, end_date
        );

        -- Create indexes on the new partition
        EXECUTE format('CREATE INDEX %I ON %I (organization_id, created_at DESC)',
                      'idx_' || partition_name || '_org_created', partition_name);
        EXECUTE format('CREATE INDEX %I ON %I (user_id, created_at DESC)',
                      'idx_' || partition_name || '_user_created', partition_name);
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- CONSTRAINT CHECKS
-- ============================================================================

-- Enhanced email constraint
ALTER TABLE users
DROP CONSTRAINT IF EXISTS users_email_format,
ADD CONSTRAINT users_email_format
CHECK (validate_email(email));

-- Enhanced webhook URL constraint
ALTER TABLE webhooks
DROP CONSTRAINT IF EXISTS webhooks_url_format,
ADD CONSTRAINT webhooks_url_format
CHECK (validate_url(url));

-- Board position constraints
ALTER TABLE boards
ADD CONSTRAINT boards_position_positive
CHECK (position IS NULL OR position >= 0);

-- Item position constraints
ALTER TABLE items
ADD CONSTRAINT items_position_positive
CHECK (position > 0);

-- Time entry constraints
ALTER TABLE time_entries
ADD CONSTRAINT time_entries_valid_duration
CHECK (
    (end_time IS NULL AND duration_seconds IS NULL) OR
    (end_time IS NOT NULL AND duration_seconds IS NOT NULL AND duration_seconds > 0)
);

-- Board column constraints
ALTER TABLE board_columns
ADD CONSTRAINT board_columns_position_positive
CHECK (position >= 0);

-- File constraints
ALTER TABLE files
ADD CONSTRAINT files_size_positive
CHECK (file_size > 0),
ADD CONSTRAINT files_checksum_format
CHECK (checksum IS NULL OR checksum ~ '^[a-f0-9]{64}$');

-- Automation execution constraints
ALTER TABLE automation_executions
ADD CONSTRAINT automation_executions_time_positive
CHECK (execution_time_ms IS NULL OR execution_time_ms >= 0);

-- Webhook delivery constraints
ALTER TABLE webhook_deliveries
ADD CONSTRAINT webhook_deliveries_attempt_positive
CHECK (attempt > 0),
ADD CONSTRAINT webhook_deliveries_attempt_max
CHECK (attempt <= 10);

-- ============================================================================
-- CREATE TRIGGERS
-- ============================================================================

-- Updated at triggers
CREATE TRIGGER trigger_organizations_updated_at
    BEFORE UPDATE ON organizations
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trigger_workspaces_updated_at
    BEFORE UPDATE ON workspaces
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trigger_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trigger_boards_updated_at
    BEFORE UPDATE ON boards
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trigger_items_updated_at
    BEFORE UPDATE ON items
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trigger_comments_updated_at
    BEFORE UPDATE ON comments
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Data validation triggers
CREATE TRIGGER trigger_validate_user_email
    BEFORE INSERT OR UPDATE ON users
    FOR EACH ROW
    EXECUTE FUNCTION validate_user_email_trigger();

CREATE TRIGGER trigger_validate_item_hierarchy
    BEFORE INSERT OR UPDATE ON items
    FOR EACH ROW
    EXECUTE FUNCTION validate_item_hierarchy();

CREATE TRIGGER trigger_validate_item_data
    BEFORE INSERT OR UPDATE ON items
    FOR EACH ROW
    EXECUTE FUNCTION validate_item_data_trigger();

CREATE TRIGGER trigger_validate_organization_membership
    BEFORE INSERT OR UPDATE ON organization_members
    FOR EACH ROW
    EXECUTE FUNCTION validate_organization_membership();

CREATE TRIGGER trigger_validate_workspace_membership
    BEFORE INSERT OR UPDATE ON workspace_members
    FOR EACH ROW
    EXECUTE FUNCTION validate_workspace_membership();

CREATE TRIGGER trigger_validate_file_size
    BEFORE INSERT OR UPDATE ON files
    FOR EACH ROW
    EXECUTE FUNCTION validate_file_size();

CREATE TRIGGER trigger_validate_automation_rule
    BEFORE INSERT OR UPDATE ON automation_rules
    FOR EACH ROW
    EXECUTE FUNCTION validate_automation_rule();

-- Cascade triggers
CREATE TRIGGER trigger_soft_delete_board_items
    AFTER UPDATE ON boards
    FOR EACH ROW
    EXECUTE FUNCTION soft_delete_board_items();

-- Partition management triggers
CREATE TRIGGER trigger_create_activity_log_partition
    BEFORE INSERT ON activity_log
    FOR EACH ROW
    EXECUTE FUNCTION create_activity_log_partition();

-- ============================================================================
-- ROW LEVEL SECURITY (RLS)
-- ============================================================================

-- Enable RLS on sensitive tables
ALTER TABLE organizations ENABLE ROW LEVEL SECURITY;
ALTER TABLE workspaces ENABLE ROW LEVEL SECURITY;
ALTER TABLE boards ENABLE ROW LEVEL SECURITY;
ALTER TABLE items ENABLE ROW LEVEL SECURITY;
ALTER TABLE comments ENABLE ROW LEVEL SECURITY;
ALTER TABLE files ENABLE ROW LEVEL SECURITY;
ALTER TABLE activity_log ENABLE ROW LEVEL SECURITY;

-- Organization access policy
CREATE POLICY organization_access_policy ON organizations
    FOR ALL
    TO PUBLIC
    USING (
        id IN (
            SELECT organization_id
            FROM organization_members
            WHERE user_id = current_setting('app.current_user_id')::UUID
            AND status = 'active'
        )
    );

-- Workspace access policy
CREATE POLICY workspace_access_policy ON workspaces
    FOR ALL
    TO PUBLIC
    USING (
        organization_id IN (
            SELECT organization_id
            FROM organization_members
            WHERE user_id = current_setting('app.current_user_id')::UUID
            AND status = 'active'
        )
        OR
        id IN (
            SELECT workspace_id
            FROM workspace_members
            WHERE user_id = current_setting('app.current_user_id')::UUID
        )
    );

-- Board access policy
CREATE POLICY board_access_policy ON boards
    FOR ALL
    TO PUBLIC
    USING (
        workspace_id IN (
            SELECT w.id
            FROM workspaces w
            JOIN organization_members om ON w.organization_id = om.organization_id
            WHERE om.user_id = current_setting('app.current_user_id')::UUID
            AND om.status = 'active'
        )
        OR
        id IN (
            SELECT board_id
            FROM board_members
            WHERE user_id = current_setting('app.current_user_id')::UUID
        )
    );

-- Item access policy
CREATE POLICY item_access_policy ON items
    FOR ALL
    TO PUBLIC
    USING (
        board_id IN (
            SELECT b.id
            FROM boards b
            JOIN workspaces w ON b.workspace_id = w.id
            JOIN organization_members om ON w.organization_id = om.organization_id
            WHERE om.user_id = current_setting('app.current_user_id')::UUID
            AND om.status = 'active'
        )
    );

-- Comment access policy
CREATE POLICY comment_access_policy ON comments
    FOR ALL
    TO PUBLIC
    USING (
        item_id IN (
            SELECT i.id
            FROM items i
            JOIN boards b ON i.board_id = b.id
            JOIN workspaces w ON b.workspace_id = w.id
            JOIN organization_members om ON w.organization_id = om.organization_id
            WHERE om.user_id = current_setting('app.current_user_id')::UUID
            AND om.status = 'active'
        )
    );

-- File access policy
CREATE POLICY file_access_policy ON files
    FOR ALL
    TO PUBLIC
    USING (
        organization_id IN (
            SELECT organization_id
            FROM organization_members
            WHERE user_id = current_setting('app.current_user_id')::UUID
            AND status = 'active'
        )
    );

-- Activity log access policy
CREATE POLICY activity_log_access_policy ON activity_log
    FOR SELECT
    TO PUBLIC
    USING (
        organization_id IN (
            SELECT organization_id
            FROM organization_members
            WHERE user_id = current_setting('app.current_user_id')::UUID
            AND status = 'active'
        )
    );

-- ============================================================================
-- DATA INTEGRITY VIEWS
-- ============================================================================

-- View for orphaned records
CREATE OR REPLACE VIEW orphaned_records AS
SELECT
    'items' as table_name,
    id,
    'board_id' as foreign_key,
    board_id::text as foreign_value
FROM items
WHERE board_id NOT IN (SELECT id FROM boards WHERE deleted_at IS NULL)
AND deleted_at IS NULL

UNION ALL

SELECT
    'comments' as table_name,
    id,
    'item_id' as foreign_key,
    item_id::text as foreign_value
FROM comments
WHERE item_id NOT IN (SELECT id FROM items WHERE deleted_at IS NULL)
AND deleted_at IS NULL

UNION ALL

SELECT
    'file_attachments' as table_name,
    id,
    'entity_id' as foreign_key,
    entity_id::text as foreign_value
FROM file_attachments
WHERE entity_type = 'item'
AND entity_id NOT IN (SELECT id FROM items WHERE deleted_at IS NULL);

-- View for data quality issues
CREATE OR REPLACE VIEW data_quality_issues AS
SELECT
    'users_invalid_email' as issue_type,
    COUNT(*) as count
FROM users
WHERE NOT validate_email(email) AND deleted_at IS NULL

UNION ALL

SELECT
    'items_invalid_hierarchy' as issue_type,
    COUNT(*) as count
FROM items i1
WHERE parent_id IS NOT NULL
AND parent_id NOT IN (
    SELECT id FROM items i2
    WHERE i2.board_id = i1.board_id
    AND i2.deleted_at IS NULL
)
AND deleted_at IS NULL

UNION ALL

SELECT
    'boards_no_columns' as issue_type,
    COUNT(*) as count
FROM boards
WHERE id NOT IN (SELECT DISTINCT board_id FROM board_columns)
AND deleted_at IS NULL;

-- Record migration
INSERT INTO schema_migrations (version, name, checksum)
VALUES ('003', 'data_integrity', 'data_integrity_checksum_placeholder');

COMMIT;

-- ============================================================================
-- DOWN MIGRATION
-- ============================================================================

-- BEGIN;
--
-- -- Drop RLS policies
-- DROP POLICY IF EXISTS organization_access_policy ON organizations;
-- DROP POLICY IF EXISTS workspace_access_policy ON workspaces;
-- DROP POLICY IF EXISTS board_access_policy ON boards;
-- DROP POLICY IF EXISTS item_access_policy ON items;
-- DROP POLICY IF EXISTS comment_access_policy ON comments;
-- DROP POLICY IF EXISTS file_access_policy ON files;
-- DROP POLICY IF EXISTS activity_log_access_policy ON activity_log;
--
-- -- Disable RLS
-- ALTER TABLE organizations DISABLE ROW LEVEL SECURITY;
-- ALTER TABLE workspaces DISABLE ROW LEVEL SECURITY;
-- ALTER TABLE boards DISABLE ROW LEVEL SECURITY;
-- ALTER TABLE items DISABLE ROW LEVEL SECURITY;
-- ALTER TABLE comments DISABLE ROW LEVEL SECURITY;
-- ALTER TABLE files DISABLE ROW LEVEL SECURITY;
-- ALTER TABLE activity_log DISABLE ROW LEVEL SECURITY;
--
-- -- Drop triggers
-- DROP TRIGGER IF EXISTS trigger_organizations_updated_at ON organizations;
-- DROP TRIGGER IF EXISTS trigger_workspaces_updated_at ON workspaces;
-- DROP TRIGGER IF EXISTS trigger_users_updated_at ON users;
-- DROP TRIGGER IF EXISTS trigger_boards_updated_at ON boards;
-- DROP TRIGGER IF EXISTS trigger_items_updated_at ON items;
-- DROP TRIGGER IF EXISTS trigger_comments_updated_at ON comments;
-- DROP TRIGGER IF EXISTS trigger_validate_user_email ON users;
-- DROP TRIGGER IF EXISTS trigger_validate_item_hierarchy ON items;
-- DROP TRIGGER IF EXISTS trigger_validate_item_data ON items;
-- DROP TRIGGER IF EXISTS trigger_validate_organization_membership ON organization_members;
-- DROP TRIGGER IF EXISTS trigger_validate_workspace_membership ON workspace_members;
-- DROP TRIGGER IF EXISTS trigger_validate_file_size ON files;
-- DROP TRIGGER IF EXISTS trigger_validate_automation_rule ON automation_rules;
-- DROP TRIGGER IF EXISTS trigger_soft_delete_board_items ON boards;
-- DROP TRIGGER IF EXISTS trigger_create_activity_log_partition ON activity_log;
--
-- -- Drop constraints
-- ALTER TABLE users DROP CONSTRAINT IF EXISTS users_email_format;
-- ALTER TABLE webhooks DROP CONSTRAINT IF EXISTS webhooks_url_format;
-- ALTER TABLE boards DROP CONSTRAINT IF EXISTS boards_position_positive;
-- ALTER TABLE items DROP CONSTRAINT IF EXISTS items_position_positive;
-- ALTER TABLE time_entries DROP CONSTRAINT IF EXISTS time_entries_valid_duration;
-- ALTER TABLE board_columns DROP CONSTRAINT IF EXISTS board_columns_position_positive;
-- ALTER TABLE files DROP CONSTRAINT IF EXISTS files_size_positive;
-- ALTER TABLE files DROP CONSTRAINT IF EXISTS files_checksum_format;
-- ALTER TABLE automation_executions DROP CONSTRAINT IF EXISTS automation_executions_time_positive;
-- ALTER TABLE webhook_deliveries DROP CONSTRAINT IF EXISTS webhook_deliveries_attempt_positive;
-- ALTER TABLE webhook_deliveries DROP CONSTRAINT IF EXISTS webhook_deliveries_attempt_max;
--
-- -- Drop views
-- DROP VIEW IF EXISTS orphaned_records;
-- DROP VIEW IF EXISTS data_quality_issues;
--
-- -- Drop functions
-- DROP FUNCTION IF EXISTS validate_email(TEXT);
-- DROP FUNCTION IF EXISTS validate_url(TEXT);
-- DROP FUNCTION IF EXISTS validate_json_keys(JSONB, TEXT[]);
-- DROP FUNCTION IF EXISTS validate_item_data(UUID, JSONB);
-- DROP FUNCTION IF EXISTS log_activity(UUID, UUID, UUID, UUID, UUID, TEXT, TEXT, UUID, JSONB, JSONB, JSONB);
-- DROP FUNCTION IF EXISTS update_updated_at_column();
-- DROP FUNCTION IF EXISTS soft_delete_board_items();
-- DROP FUNCTION IF EXISTS validate_item_hierarchy();
-- DROP FUNCTION IF EXISTS validate_item_data_trigger();
-- DROP FUNCTION IF EXISTS validate_user_email_trigger();
-- DROP FUNCTION IF EXISTS validate_organization_membership();
-- DROP FUNCTION IF EXISTS validate_workspace_membership();
-- DROP FUNCTION IF EXISTS validate_file_size();
-- DROP FUNCTION IF EXISTS validate_automation_rule();
-- DROP FUNCTION IF EXISTS create_activity_log_partition();
--
-- -- Remove migration record
-- DELETE FROM schema_migrations WHERE version = '003';
--
-- COMMIT;