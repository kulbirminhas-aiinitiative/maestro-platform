-- Additional performance indexes

-- Composite indexes for common query patterns
CREATE INDEX IF NOT EXISTS idx_events_tenant_type_time
    ON events(tenant_id, event_type, occurred_at DESC);

CREATE INDEX IF NOT EXISTS idx_events_aggregate_tenant_version
    ON events(aggregate_id, tenant_id, version ASC);

-- GIN indexes for JSONB queries
CREATE INDEX IF NOT EXISTS idx_events_data_gin
    ON events USING GIN (data);

CREATE INDEX IF NOT EXISTS idx_read_entities_data_gin
    ON read_model_entities USING GIN (data);

-- Partial indexes for active records
CREATE INDEX IF NOT EXISTS idx_tenants_active_name
    ON tenants(tenant_name) WHERE is_active = true;

-- Index for user activity tracking
CREATE INDEX IF NOT EXISTS idx_events_user
    ON events(user_id, tenant_id) WHERE user_id IS NOT NULL;