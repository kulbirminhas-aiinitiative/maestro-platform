-- Initial database schema for event sourcing multi-tenant SaaS

-- Tenants table
CREATE TABLE IF NOT EXISTS tenants (
    tenant_id UUID PRIMARY KEY,
    tenant_name VARCHAR(255) NOT NULL,
    subscription_tier VARCHAR(50) NOT NULL DEFAULT 'standard',
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    settings JSONB DEFAULT '{}'::jsonb,
    CONSTRAINT tenants_name_unique UNIQUE (tenant_name)
);

-- Index for tenant lookups
CREATE INDEX idx_tenants_active ON tenants(is_active);
CREATE INDEX idx_tenants_subscription ON tenants(subscription_tier);

-- Events table (event store)
CREATE TABLE IF NOT EXISTS events (
    position BIGSERIAL PRIMARY KEY,
    event_id UUID NOT NULL UNIQUE,
    event_type VARCHAR(255) NOT NULL,
    aggregate_id UUID NOT NULL,
    aggregate_type VARCHAR(255) NOT NULL,
    tenant_id UUID NOT NULL REFERENCES tenants(tenant_id),
    occurred_at TIMESTAMP NOT NULL DEFAULT NOW(),
    version INTEGER NOT NULL,
    user_id UUID,
    data JSONB NOT NULL,
    metadata JSONB DEFAULT '{}'::jsonb,
    CONSTRAINT events_aggregate_version_unique UNIQUE (aggregate_id, tenant_id, version)
);

-- Indexes for event queries
CREATE INDEX idx_events_aggregate ON events(aggregate_id, tenant_id, version);
CREATE INDEX idx_events_tenant ON events(tenant_id, position);
CREATE INDEX idx_events_type ON events(event_type, tenant_id);
CREATE INDEX idx_events_occurred ON events(occurred_at);

-- Snapshots table for aggregate state caching
CREATE TABLE IF NOT EXISTS snapshots (
    snapshot_id UUID PRIMARY KEY,
    aggregate_id UUID NOT NULL,
    aggregate_type VARCHAR(255) NOT NULL,
    tenant_id UUID NOT NULL REFERENCES tenants(tenant_id),
    version INTEGER NOT NULL,
    state JSONB NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    CONSTRAINT snapshots_aggregate_unique UNIQUE (aggregate_id, tenant_id, version)
);

-- Index for snapshot lookups
CREATE INDEX idx_snapshots_aggregate ON snapshots(aggregate_id, tenant_id, version DESC);

-- Read model tables (example for a generic entity)
CREATE TABLE IF NOT EXISTS read_model_entities (
    entity_id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL REFERENCES tenants(tenant_id),
    entity_type VARCHAR(255) NOT NULL,
    data JSONB NOT NULL,
    version INTEGER NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Index for read model queries
CREATE INDEX idx_read_entities_tenant ON read_model_entities(tenant_id);
CREATE INDEX idx_read_entities_type ON read_model_entities(entity_type, tenant_id);

-- Projection checkpoints for tracking projection progress
CREATE TABLE IF NOT EXISTS projection_checkpoints (
    projection_name VARCHAR(255) PRIMARY KEY,
    tenant_id UUID NOT NULL REFERENCES tenants(tenant_id),
    last_position BIGINT NOT NULL DEFAULT 0,
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    CONSTRAINT projection_checkpoints_unique UNIQUE (projection_name, tenant_id)
);

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Triggers for updated_at
CREATE TRIGGER update_tenants_updated_at BEFORE UPDATE ON tenants
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_read_entities_updated_at BEFORE UPDATE ON read_model_entities
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();