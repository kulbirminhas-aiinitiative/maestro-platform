-- Real-Time Analytics Database Schema

-- Raw events table
CREATE TABLE IF NOT EXISTS raw_events (
    id BIGSERIAL PRIMARY KEY,
    event_id VARCHAR(255) UNIQUE NOT NULL,
    event_type VARCHAR(100) NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    data JSONB,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Index for faster queries
CREATE INDEX idx_raw_events_event_type ON raw_events(event_type);
CREATE INDEX idx_raw_events_timestamp ON raw_events(timestamp DESC);
CREATE INDEX idx_raw_events_event_type_timestamp ON raw_events(event_type, timestamp DESC);

-- Aggregations table
CREATE TABLE IF NOT EXISTS aggregations (
    id BIGSERIAL PRIMARY KEY,
    event_type VARCHAR(100) NOT NULL,
    window_start TIMESTAMP NOT NULL,
    count INTEGER NOT NULL,
    metrics JSONB,
    computed_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Index for aggregations
CREATE INDEX idx_aggregations_event_type ON aggregations(event_type);
CREATE INDEX idx_aggregations_window_start ON aggregations(window_start DESC);
CREATE INDEX idx_aggregations_event_type_window ON aggregations(event_type, window_start DESC);

-- Anomalies table
CREATE TABLE IF NOT EXISTS anomalies (
    id BIGSERIAL PRIMARY KEY,
    event_type VARCHAR(100) NOT NULL,
    detected_at TIMESTAMP NOT NULL,
    details JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Index for anomalies
CREATE INDEX idx_anomalies_event_type ON anomalies(event_type);
CREATE INDEX idx_anomalies_detected_at ON anomalies(detected_at DESC);

-- System metrics table for monitoring
CREATE TABLE IF NOT EXISTS system_metrics (
    id BIGSERIAL PRIMARY KEY,
    metric_name VARCHAR(255) NOT NULL,
    metric_value NUMERIC,
    tags JSONB,
    timestamp TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Index for system metrics
CREATE INDEX idx_system_metrics_name ON system_metrics(metric_name);
CREATE INDEX idx_system_metrics_timestamp ON system_metrics(timestamp DESC);

-- Partitioning for raw_events (by month)
-- Note: This is a simplified example. In production, use proper partitioning strategy
CREATE TABLE IF NOT EXISTS raw_events_archive (
    LIKE raw_events INCLUDING ALL
);

-- Create a function to archive old data
CREATE OR REPLACE FUNCTION archive_old_events()
RETURNS void AS $$
BEGIN
    INSERT INTO raw_events_archive
    SELECT * FROM raw_events
    WHERE timestamp < NOW() - INTERVAL '30 days';

    DELETE FROM raw_events
    WHERE timestamp < NOW() - INTERVAL '30 days';
END;
$$ LANGUAGE plpgsql;

-- Grant permissions
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO analytics_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO analytics_user;