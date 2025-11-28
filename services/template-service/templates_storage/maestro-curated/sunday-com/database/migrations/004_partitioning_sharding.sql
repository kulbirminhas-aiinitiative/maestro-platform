-- Migration: 004_partitioning_sharding.sql
-- Description: Advanced partitioning and sharding strategy implementation
-- Version: 004
-- Created: 2024-12-01

BEGIN;

-- ============================================================================
-- PARTITIONING STRATEGY IMPLEMENTATION
-- ============================================================================

-- Create function to generate monthly partitions automatically
CREATE OR REPLACE FUNCTION create_monthly_partition(
    parent_table text,
    start_date date
) RETURNS text AS $$
DECLARE
    partition_name text;
    end_date date;
    partition_sql text;
BEGIN
    -- Generate partition name
    partition_name := parent_table || '_y' || to_char(start_date, 'YYYY') || 'm' || to_char(start_date, 'MM');
    end_date := start_date + interval '1 month';

    -- Check if partition already exists
    IF EXISTS (
        SELECT 1 FROM pg_tables
        WHERE schemaname = 'public'
        AND tablename = partition_name
    ) THEN
        RETURN partition_name;
    END IF;

    -- Create the partition
    partition_sql := format(
        'CREATE TABLE %I PARTITION OF %I FOR VALUES FROM (%L) TO (%L)',
        partition_name, parent_table, start_date, end_date
    );

    EXECUTE partition_sql;

    -- Create indexes on the new partition
    CASE parent_table
        WHEN 'activity_log' THEN
            EXECUTE format('CREATE INDEX %I ON %I (organization_id, created_at DESC)',
                          'idx_' || partition_name || '_org_created', partition_name);
            EXECUTE format('CREATE INDEX %I ON %I (user_id, created_at DESC)',
                          'idx_' || partition_name || '_user_created', partition_name);
            EXECUTE format('CREATE INDEX %I ON %I (entity_type, entity_id, created_at DESC)',
                          'idx_' || partition_name || '_entity', partition_name);

        WHEN 'automation_executions' THEN
            EXECUTE format('CREATE INDEX %I ON %I (rule_id, executed_at DESC)',
                          'idx_' || partition_name || '_rule', partition_name);
            EXECUTE format('CREATE INDEX %I ON %I (execution_status, executed_at DESC)',
                          'idx_' || partition_name || '_status', partition_name);
    END CASE;

    RETURN partition_name;
END;
$$ LANGUAGE plpgsql;

-- Create function to automatically manage partition creation
CREATE OR REPLACE FUNCTION ensure_partition_exists(
    parent_table text,
    partition_date date
) RETURNS text AS $$
DECLARE
    partition_month date;
    partition_name text;
BEGIN
    -- Round down to first day of month
    partition_month := date_trunc('month', partition_date)::date;

    -- Create partition for the month
    partition_name := create_monthly_partition(parent_table, partition_month);

    -- Also create next month's partition proactively
    PERFORM create_monthly_partition(parent_table, partition_month + interval '1 month');

    RETURN partition_name;
END;
$$ LANGUAGE plpgsql;

-- Create automated partition maintenance function
CREATE OR REPLACE FUNCTION maintain_partitions() RETURNS void AS $$
DECLARE
    current_month date;
    table_name text;
BEGIN
    current_month := date_trunc('month', CURRENT_DATE)::date;

    -- Ensure partitions exist for current and next 3 months
    FOR table_name IN VALUES ('activity_log'), ('automation_executions')
    LOOP
        FOR i IN 0..3 LOOP
            PERFORM create_monthly_partition(
                table_name,
                current_month + (i || ' months')::interval
            );
        END LOOP;
    END LOOP;

    -- Drop old partitions (older than 2 years for activity_log, 1 year for automation_executions)
    FOR table_name IN VALUES ('activity_log'), ('automation_executions')
    LOOP
        DECLARE
            retention_months int;
            cutoff_date date;
            partition_name text;
        BEGIN
            retention_months := CASE table_name
                WHEN 'activity_log' THEN 24
                WHEN 'automation_executions' THEN 12
                ELSE 12
            END;

            cutoff_date := current_month - (retention_months || ' months')::interval;

            -- Find and drop old partitions
            FOR partition_name IN
                SELECT tablename
                FROM pg_tables
                WHERE schemaname = 'public'
                AND tablename LIKE table_name || '_y%m%'
                AND substring(tablename from '\d{4}_\d{2}')::text < to_char(cutoff_date, 'YYYY_MM')
            LOOP
                EXECUTE format('DROP TABLE IF EXISTS %I', partition_name);
                RAISE NOTICE 'Dropped old partition: %', partition_name;
            END LOOP;
        END;
    END LOOP;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- LARGE TABLE PARTITIONING
-- ============================================================================

-- Partition items table by organization (for very large deployments)
-- This is optional and should be used only when items table becomes very large

-- Create function to partition items by organization hash
CREATE OR REPLACE FUNCTION create_items_hash_partitions(num_partitions int DEFAULT 4)
RETURNS void AS $$
DECLARE
    i int;
    partition_name text;
BEGIN
    -- Only create if not already partitioned
    IF NOT EXISTS (
        SELECT 1 FROM pg_partitioned_table
        WHERE schemaname = 'public' AND tablename = 'items'
    ) THEN
        -- This would require recreating the items table as partitioned
        RAISE NOTICE 'Items table partitioning requires manual migration';
        RETURN;
    END IF;

    -- Create hash partitions
    FOR i IN 0..num_partitions-1 LOOP
        partition_name := 'items_part_' || i;

        IF NOT EXISTS (
            SELECT 1 FROM pg_tables
            WHERE schemaname = 'public' AND tablename = partition_name
        ) THEN
            EXECUTE format(
                'CREATE TABLE %I PARTITION OF items FOR VALUES WITH (MODULUS %s, REMAINDER %s)',
                partition_name, num_partitions, i
            );

            -- Create indexes on partition
            EXECUTE format('CREATE INDEX %I ON %I (board_id, position) WHERE deleted_at IS NULL',
                          'idx_' || partition_name || '_board_position', partition_name);
            EXECUTE format('CREATE INDEX %I ON %I (created_by, created_at DESC) WHERE deleted_at IS NULL',
                          'idx_' || partition_name || '_created', partition_name);
        END IF;
    END LOOP;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- SHARDING STRATEGY FUNCTIONS
-- ============================================================================

-- Function to determine shard for organization
CREATE OR REPLACE FUNCTION get_organization_shard(org_id uuid) RETURNS int AS $$
BEGIN
    -- Simple hash-based sharding
    -- In production, you might use consistent hashing
    RETURN (hashtext(org_id::text) % 4) + 1;
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- Function to validate cross-shard operations
CREATE OR REPLACE FUNCTION validate_cross_shard_operation(
    org_ids uuid[]
) RETURNS boolean AS $$
DECLARE
    shard_id int;
    first_shard int;
BEGIN
    IF array_length(org_ids, 1) = 0 THEN
        RETURN true;
    END IF;

    -- Get shard for first organization
    first_shard := get_organization_shard(org_ids[1]);

    -- Check if all organizations are on the same shard
    FOR i IN 1..array_length(org_ids, 1) LOOP
        shard_id := get_organization_shard(org_ids[i]);
        IF shard_id != first_shard THEN
            RETURN false;
        END IF;
    END LOOP;

    RETURN true;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- SHARD MANAGEMENT VIEWS
-- ============================================================================

-- View to show data distribution across organizations
CREATE OR REPLACE VIEW organization_data_distribution AS
SELECT
    o.id as organization_id,
    o.name as organization_name,
    get_organization_shard(o.id) as shard_id,
    (SELECT COUNT(*) FROM workspaces w WHERE w.organization_id = o.id) as workspace_count,
    (SELECT COUNT(*) FROM boards b
     JOIN workspaces w ON b.workspace_id = w.id
     WHERE w.organization_id = o.id AND b.deleted_at IS NULL) as board_count,
    (SELECT COUNT(*) FROM items i
     JOIN boards b ON i.board_id = b.id
     JOIN workspaces w ON b.workspace_id = w.id
     WHERE w.organization_id = o.id AND i.deleted_at IS NULL) as item_count,
    (SELECT COUNT(*) FROM organization_members om WHERE om.organization_id = o.id) as member_count,
    o.created_at
FROM organizations o
WHERE o.deleted_at IS NULL
ORDER BY shard_id, item_count DESC;

-- View to show shard load distribution
CREATE OR REPLACE VIEW shard_load_distribution AS
SELECT
    shard_id,
    COUNT(*) as organization_count,
    SUM(workspace_count) as total_workspaces,
    SUM(board_count) as total_boards,
    SUM(item_count) as total_items,
    SUM(member_count) as total_members,
    AVG(item_count) as avg_items_per_org,
    MAX(item_count) as max_items_per_org,
    MIN(item_count) as min_items_per_org
FROM organization_data_distribution
GROUP BY shard_id
ORDER BY shard_id;

-- ============================================================================
-- PARTITION MAINTENANCE SCHEDULING
-- ============================================================================

-- Create a simple cron-like scheduler for partition maintenance
CREATE OR REPLACE FUNCTION schedule_partition_maintenance() RETURNS void AS $$
BEGIN
    -- This function should be called daily by an external scheduler
    -- like pg_cron, crontab, or application scheduler

    PERFORM maintain_partitions();

    -- Log maintenance
    INSERT INTO activity_log (
        organization_id,
        user_id,
        action,
        entity_type,
        entity_id,
        metadata,
        created_at
    ) VALUES (
        '00000000-0000-0000-0000-000000000000'::uuid, -- System UUID
        '00000000-0000-0000-0000-000000000000'::uuid, -- System UUID
        'partition_maintenance',
        'system',
        '00000000-0000-0000-0000-000000000000'::uuid,
        jsonb_build_object(
            'maintenance_type', 'partition_maintenance',
            'timestamp', NOW()
        ),
        NOW()
    );
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- MONITORING AND ALERTING
-- ============================================================================

-- Function to check partition health
CREATE OR REPLACE FUNCTION check_partition_health() RETURNS TABLE (
    table_name text,
    issue_type text,
    issue_description text,
    severity text
) AS $$
BEGIN
    -- Check for missing future partitions
    RETURN QUERY
    SELECT
        'activity_log'::text,
        'missing_partition'::text,
        'Missing partition for next month'::text,
        'warning'::text
    WHERE NOT EXISTS (
        SELECT 1 FROM pg_tables
        WHERE schemaname = 'public'
        AND tablename = 'activity_log_y' || to_char(date_trunc('month', CURRENT_DATE + interval '1 month'), 'YYYY') || 'm' || to_char(date_trunc('month', CURRENT_DATE + interval '1 month'), 'MM')
    );

    -- Check for very large partitions
    RETURN QUERY
    SELECT
        pt.tablename::text,
        'large_partition'::text,
        'Partition size exceeds 10GB'::text,
        'warning'::text
    FROM pg_tables pt
    WHERE pt.schemaname = 'public'
    AND pt.tablename LIKE 'activity_log_y%m%'
    AND pg_total_relation_size(pt.tablename::regclass) > 10 * 1024 * 1024 * 1024; -- 10GB

    -- Check for shard imbalance
    RETURN QUERY
    SELECT
        'shard_distribution'::text,
        'imbalanced_shards'::text,
        'Shard load imbalance detected'::text,
        'info'::text
    WHERE EXISTS (
        SELECT 1 FROM shard_load_distribution
        GROUP BY 1
        HAVING MAX(total_items) > MIN(total_items) * 2 -- 2x imbalance
    );
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- PARTITION PRUNING OPTIMIZATION
-- ============================================================================

-- Enable constraint exclusion for better partition pruning
SET constraint_exclusion = partition;

-- Update table statistics for better query planning on partitioned tables
CREATE OR REPLACE FUNCTION update_partition_statistics() RETURNS void AS $$
DECLARE
    partition_name text;
BEGIN
    -- Update statistics on all activity_log partitions
    FOR partition_name IN
        SELECT tablename
        FROM pg_tables
        WHERE schemaname = 'public'
        AND tablename LIKE 'activity_log_y%m%'
    LOOP
        EXECUTE format('ANALYZE %I', partition_name);
    END LOOP;

    -- Update statistics on automation_execution partitions
    FOR partition_name IN
        SELECT tablename
        FROM pg_tables
        WHERE schemaname = 'public'
        AND tablename LIKE 'automation_executions_y%m%'
    LOOP
        EXECUTE format('ANALYZE %I', partition_name);
    END LOOP;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- FOREIGN DATA WRAPPER SETUP (for potential sharding)
-- ============================================================================

-- Function to create foreign server connections for sharding
CREATE OR REPLACE FUNCTION setup_shard_connections() RETURNS void AS $$
BEGIN
    -- This is a template for setting up foreign data wrappers
    -- Enable postgres_fdw extension if not already enabled

    -- Example setup (commented out as it requires actual server details):
    /*
    CREATE EXTENSION IF NOT EXISTS postgres_fdw;

    -- Create foreign servers
    CREATE SERVER IF NOT EXISTS shard_1
        FOREIGN DATA WRAPPER postgres_fdw
        OPTIONS (host 'shard1.sunday.com', port '5432', dbname 'sunday_shard_1');

    CREATE SERVER IF NOT EXISTS shard_2
        FOREIGN DATA WRAPPER postgres_fdw
        OPTIONS (host 'shard2.sunday.com', port '5432', dbname 'sunday_shard_2');

    -- Create user mappings
    CREATE USER MAPPING IF NOT EXISTS FOR CURRENT_USER
        SERVER shard_1
        OPTIONS (user 'sunday_user', password 'password');

    CREATE USER MAPPING IF NOT EXISTS FOR CURRENT_USER
        SERVER shard_2
        OPTIONS (user 'sunday_user', password 'password');
    */

    RAISE NOTICE 'Shard connection setup is commented out. Configure based on actual shard servers.';
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- INITIAL PARTITION CREATION
-- ============================================================================

-- Create partitions for the next 6 months
SELECT create_monthly_partition('activity_log', date_trunc('month', CURRENT_DATE + (i || ' months')::interval)::date)
FROM generate_series(0, 5) i;

SELECT create_monthly_partition('automation_executions', date_trunc('month', CURRENT_DATE + (i || ' months')::interval)::date)
FROM generate_series(0, 5) i;

-- ============================================================================
-- PERFORMANCE HINTS AND CONFIGURATION
-- ============================================================================

-- Set optimal work_mem for partition operations
-- This should be set at session level or in postgresql.conf
-- SET work_mem = '256MB';

-- Enable parallel query execution for partitioned tables
-- SET max_parallel_workers_per_gather = 4;
-- SET parallel_tuple_cost = 0.1;
-- SET parallel_setup_cost = 1000;

-- Configure partition-wise joins
-- SET enable_partitionwise_join = on;
-- SET enable_partitionwise_aggregate = on;

-- ============================================================================
-- MONITORING QUERIES
-- ============================================================================

-- Create view for partition monitoring
CREATE OR REPLACE VIEW partition_monitoring AS
SELECT
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size,
    pg_total_relation_size(schemaname||'.'||tablename) as size_bytes,
    (SELECT count(*) FROM information_schema.table_constraints
     WHERE table_schema = pt.schemaname AND table_name = pt.tablename
     AND constraint_type = 'CHECK') as check_constraints
FROM pg_tables pt
WHERE schemaname = 'public'
AND (tablename LIKE 'activity_log_y%m%' OR tablename LIKE 'automation_executions_y%m%')
ORDER BY size_bytes DESC;

-- ============================================================================
-- MIGRATION UTILITIES
-- ============================================================================

-- Function to migrate existing data to partitioned tables
CREATE OR REPLACE FUNCTION migrate_to_partitioned_table(
    source_table text,
    target_table text,
    partition_column text,
    batch_size int DEFAULT 10000
) RETURNS void AS $$
DECLARE
    min_date date;
    max_date date;
    current_date date;
    rows_migrated bigint := 0;
    total_rows bigint;
BEGIN
    -- Get data range
    EXECUTE format('SELECT MIN(%I), MAX(%I), COUNT(*) FROM %I',
                   partition_column, partition_column, source_table)
    INTO min_date, max_date, total_rows;

    RAISE NOTICE 'Migrating % rows from % to % (% to %)',
                 total_rows, source_table, target_table, min_date, max_date;

    -- Migrate data month by month
    current_date := date_trunc('month', min_date);

    WHILE current_date <= max_date LOOP
        -- Ensure partition exists
        PERFORM ensure_partition_exists(target_table, current_date);

        -- Migrate data for this month
        EXECUTE format(
            'INSERT INTO %I SELECT * FROM %I WHERE %I >= %L AND %I < %L',
            target_table, source_table, partition_column, current_date,
            partition_column, current_date + interval '1 month'
        );

        GET DIAGNOSTICS rows_migrated = ROW_COUNT;
        RAISE NOTICE 'Migrated % rows for month %', rows_migrated, current_date;

        current_date := current_date + interval '1 month';
    END LOOP;

    RAISE NOTICE 'Migration completed successfully';
END;
$$ LANGUAGE plpgsql;

-- Record migration
INSERT INTO schema_migrations (version, name, checksum)
VALUES ('004', 'partitioning_sharding', 'partitioning_sharding_checksum_placeholder');

COMMIT;

-- ============================================================================
-- DOWN MIGRATION
-- ============================================================================

-- BEGIN;
--
-- -- Drop monitoring views
-- DROP VIEW IF EXISTS partition_monitoring;
-- DROP VIEW IF EXISTS shard_load_distribution;
-- DROP VIEW IF EXISTS organization_data_distribution;
--
-- -- Drop functions
-- DROP FUNCTION IF EXISTS migrate_to_partitioned_table(text, text, text, int);
-- DROP FUNCTION IF EXISTS setup_shard_connections();
-- DROP FUNCTION IF EXISTS update_partition_statistics();
-- DROP FUNCTION IF EXISTS check_partition_health();
-- DROP FUNCTION IF EXISTS schedule_partition_maintenance();
-- DROP FUNCTION IF EXISTS create_items_hash_partitions(int);
-- DROP FUNCTION IF EXISTS validate_cross_shard_operation(uuid[]);
-- DROP FUNCTION IF EXISTS get_organization_shard(uuid);
-- DROP FUNCTION IF EXISTS maintain_partitions();
-- DROP FUNCTION IF EXISTS ensure_partition_exists(text, date);
-- DROP FUNCTION IF EXISTS create_monthly_partition(text, date);
--
-- -- Note: Actual partition tables would need to be manually merged
-- -- back to the parent table if rollback is needed
--
-- -- Remove migration record
-- DELETE FROM schema_migrations WHERE version = '004';
--
-- COMMIT;