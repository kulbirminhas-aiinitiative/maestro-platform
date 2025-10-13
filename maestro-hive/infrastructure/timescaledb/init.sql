-- TimescaleDB Initialization for Tri-Modal Mission Control
-- Sprint 1: Metrics Storage

-- Enable TimescaleDB extension
CREATE EXTENSION IF NOT EXISTS timescaledb;

-- ============================================================================
-- Event Metrics Tables
-- ============================================================================

-- DDE Event Metrics
CREATE TABLE dde_event_metrics (
    time TIMESTAMPTZ NOT NULL,
    event_id UUID NOT NULL,
    iteration_id VARCHAR(255) NOT NULL,
    workflow_id VARCHAR(255) NOT NULL,
    event_type VARCHAR(50) NOT NULL,
    node_id VARCHAR(255),
    node_type VARCHAR(50),
    node_status VARCHAR(50),
    retry_count INTEGER DEFAULT 0,
    duration_ms BIGINT,
    trace_id VARCHAR(32) NOT NULL,
    span_id VARCHAR(16) NOT NULL,
    PRIMARY KEY (time, event_id)
);

-- Convert to hypertable (time-series optimization)
SELECT create_hypertable('dde_event_metrics', 'time', if_not_exists => TRUE);

-- Create indexes for common queries
CREATE INDEX idx_dde_iteration ON dde_event_metrics (iteration_id, time DESC);
CREATE INDEX idx_dde_workflow ON dde_event_metrics (workflow_id, time DESC);
CREATE INDEX idx_dde_trace ON dde_event_metrics (trace_id);
CREATE INDEX idx_dde_node ON dde_event_metrics (node_id, time DESC);

-- BDV Event Metrics
CREATE TABLE bdv_event_metrics (
    time TIMESTAMPTZ NOT NULL,
    event_id UUID NOT NULL,
    iteration_id VARCHAR(255) NOT NULL,
    event_type VARCHAR(50) NOT NULL,
    feature_path VARCHAR(512),
    scenario_id VARCHAR(255),
    scenario_status VARCHAR(20),
    duration_ms BIGINT,
    flake_rate DOUBLE PRECISION,
    trace_id VARCHAR(32) NOT NULL,
    span_id VARCHAR(16) NOT NULL,
    PRIMARY KEY (time, event_id)
);

SELECT create_hypertable('bdv_event_metrics', 'time', if_not_exists => TRUE);

CREATE INDEX idx_bdv_iteration ON bdv_event_metrics (iteration_id, time DESC);
CREATE INDEX idx_bdv_scenario ON bdv_event_metrics (scenario_id, time DESC);
CREATE INDEX idx_bdv_trace ON bdv_event_metrics (trace_id);

-- ACC Event Metrics
CREATE TABLE acc_event_metrics (
    time TIMESTAMPTZ NOT NULL,
    event_id UUID NOT NULL,
    iteration_id VARCHAR(255) NOT NULL,
    manifest_name VARCHAR(255) NOT NULL,
    event_type VARCHAR(50) NOT NULL,
    module_path VARCHAR(512),
    violation_type VARCHAR(50),
    violation_severity VARCHAR(20),
    coupling_score DOUBLE PRECISION,
    total_violations INTEGER,
    blocking_violations INTEGER,
    trace_id VARCHAR(32) NOT NULL,
    span_id VARCHAR(16) NOT NULL,
    PRIMARY KEY (time, event_id)
);

SELECT create_hypertable('acc_event_metrics', 'time', if_not_exists => TRUE);

CREATE INDEX idx_acc_iteration ON acc_event_metrics (iteration_id, time DESC);
CREATE INDEX idx_acc_manifest ON acc_event_metrics (manifest_name, time DESC);
CREATE INDEX idx_acc_trace ON acc_event_metrics (trace_id);
CREATE INDEX idx_acc_violations ON acc_event_metrics (violation_severity, time DESC);

-- ============================================================================
-- Aggregated Metrics (Continuous Aggregates)
-- ============================================================================

-- DDE Task Success Rate (5-minute buckets)
CREATE MATERIALIZED VIEW dde_task_success_rate_5m
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('5 minutes', time) AS bucket,
    workflow_id,
    COUNT(*) FILTER (WHERE event_type = 'TASK_COMPLETED') AS completed_tasks,
    COUNT(*) FILTER (WHERE event_type = 'TASK_FAILED') AS failed_tasks,
    COUNT(*) AS total_tasks,
    AVG(duration_ms) AS avg_duration_ms,
    MAX(retry_count) AS max_retries
FROM dde_event_metrics
WHERE event_type IN ('TASK_COMPLETED', 'TASK_FAILED')
GROUP BY bucket, workflow_id
WITH NO DATA;

-- Refresh policy: update every 5 minutes, look back 1 hour
SELECT add_continuous_aggregate_policy('dde_task_success_rate_5m',
    start_offset => INTERVAL '1 hour',
    end_offset => INTERVAL '1 minute',
    schedule_interval => INTERVAL '5 minutes',
    if_not_exists => TRUE
);

-- BDV Scenario Pass Rate (5-minute buckets)
CREATE MATERIALIZED VIEW bdv_scenario_pass_rate_5m
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('5 minutes', time) AS bucket,
    iteration_id,
    COUNT(*) FILTER (WHERE scenario_status = 'PASSED') AS passed_scenarios,
    COUNT(*) FILTER (WHERE scenario_status = 'FAILED') AS failed_scenarios,
    COUNT(*) FILTER (WHERE scenario_status = 'FLAKY') AS flaky_scenarios,
    COUNT(*) AS total_scenarios,
    AVG(duration_ms) AS avg_duration_ms,
    AVG(flake_rate) AS avg_flake_rate
FROM bdv_event_metrics
WHERE event_type IN ('SCENARIO_PASSED', 'SCENARIO_FAILED', 'FLAKE_DETECTED')
GROUP BY bucket, iteration_id
WITH NO DATA;

SELECT add_continuous_aggregate_policy('bdv_scenario_pass_rate_5m',
    start_offset => INTERVAL '1 hour',
    end_offset => INTERVAL '1 minute',
    schedule_interval => INTERVAL '5 minutes',
    if_not_exists => TRUE
);

-- ACC Violation Counts (5-minute buckets)
CREATE MATERIALIZED VIEW acc_violation_counts_5m
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('5 minutes', time) AS bucket,
    manifest_name,
    COUNT(*) FILTER (WHERE violation_severity = 'BLOCKING') AS blocking_violations,
    COUNT(*) FILTER (WHERE violation_severity = 'WARNING') AS warning_violations,
    COUNT(*) FILTER (WHERE violation_severity = 'INFO') AS info_violations,
    COUNT(*) AS total_violations,
    AVG(coupling_score) AS avg_coupling_score
FROM acc_event_metrics
WHERE event_type = 'VIOLATION_DETECTED'
GROUP BY bucket, manifest_name
WITH NO DATA;

SELECT add_continuous_aggregate_policy('acc_violation_counts_5m',
    start_offset => INTERVAL '1 hour',
    end_offset => INTERVAL '1 minute',
    schedule_interval => INTERVAL '5 minutes',
    if_not_exists => TRUE
);

-- ============================================================================
-- SLO Tracking Tables
-- ============================================================================

-- End-to-End Latency Tracking
CREATE TABLE e2e_latency_metrics (
    time TIMESTAMPTZ NOT NULL,
    iteration_id VARCHAR(255) NOT NULL,
    stream VARCHAR(10) NOT NULL, -- 'DDE', 'BDV', 'ACC'
    event_ingestion_time TIMESTAMPTZ NOT NULL,
    neo4j_write_time TIMESTAMPTZ,
    graphql_query_time TIMESTAMPTZ,
    ui_render_time TIMESTAMPTZ,
    total_latency_ms BIGINT,
    ingestion_latency_ms BIGINT,
    query_latency_ms BIGINT,
    render_latency_ms BIGINT,
    trace_id VARCHAR(32) NOT NULL,
    PRIMARY KEY (time, iteration_id, stream)
);

SELECT create_hypertable('e2e_latency_metrics', 'time', if_not_exists => TRUE);

CREATE INDEX idx_e2e_stream ON e2e_latency_metrics (stream, time DESC);
CREATE INDEX idx_e2e_trace ON e2e_latency_metrics (trace_id);

-- Event Throughput Tracking
CREATE TABLE event_throughput_metrics (
    time TIMESTAMPTZ NOT NULL,
    stream VARCHAR(10) NOT NULL,
    events_received INTEGER NOT NULL,
    events_processed INTEGER NOT NULL,
    events_failed INTEGER NOT NULL,
    processing_rate DOUBLE PRECISION,
    PRIMARY KEY (time, stream)
);

SELECT create_hypertable('event_throughput_metrics', 'time', if_not_exists => TRUE);

-- ============================================================================
-- Data Retention Policies
-- ============================================================================

-- Keep raw events for 30 days
SELECT add_retention_policy('dde_event_metrics', INTERVAL '30 days', if_not_exists => TRUE);
SELECT add_retention_policy('bdv_event_metrics', INTERVAL '30 days', if_not_exists => TRUE);
SELECT add_retention_policy('acc_event_metrics', INTERVAL '30 days', if_not_exists => TRUE);

-- Keep aggregates for 90 days
SELECT add_retention_policy('dde_task_success_rate_5m', INTERVAL '90 days', if_not_exists => TRUE);
SELECT add_retention_policy('bdv_scenario_pass_rate_5m', INTERVAL '90 days', if_not_exists => TRUE);
SELECT add_retention_policy('acc_violation_counts_5m', INTERVAL '90 days', if_not_exists => TRUE);

-- Keep SLO metrics for 90 days
SELECT add_retention_policy('e2e_latency_metrics', INTERVAL '90 days', if_not_exists => TRUE);
SELECT add_retention_policy('event_throughput_metrics', INTERVAL '90 days', if_not_exists => TRUE);

-- ============================================================================
-- Helper Functions
-- ============================================================================

-- Calculate P95 latency
CREATE OR REPLACE FUNCTION calculate_p95_latency(
    stream_name VARCHAR,
    time_range INTERVAL
)
RETURNS BIGINT AS $$
DECLARE
    p95_latency BIGINT;
BEGIN
    SELECT percentile_cont(0.95) WITHIN GROUP (ORDER BY total_latency_ms)
    INTO p95_latency
    FROM e2e_latency_metrics
    WHERE stream = stream_name
      AND time >= NOW() - time_range;

    RETURN p95_latency;
END;
$$ LANGUAGE plpgsql;

-- Calculate event throughput rate
CREATE OR REPLACE FUNCTION calculate_throughput_rate(
    stream_name VARCHAR,
    time_range INTERVAL
)
RETURNS DOUBLE PRECISION AS $$
DECLARE
    throughput_rate DOUBLE PRECISION;
BEGIN
    SELECT AVG(processing_rate)
    INTO throughput_rate
    FROM event_throughput_metrics
    WHERE stream = stream_name
      AND time >= NOW() - time_range;

    RETURN throughput_rate;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- Initial Data / Test Data
-- ============================================================================

-- Grant permissions
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO maestro;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO maestro;

-- Create application user for ICS
CREATE USER ics_user WITH PASSWORD 'ics_dev';
GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA public TO ics_user;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO ics_user;

-- Success message
DO $$
BEGIN
    RAISE NOTICE 'TimescaleDB initialization complete!';
    RAISE NOTICE 'Created hypertables: dde_event_metrics, bdv_event_metrics, acc_event_metrics';
    RAISE NOTICE 'Created continuous aggregates: *_5m views';
    RAISE NOTICE 'Configured retention policies: 30 days (raw), 90 days (aggregates)';
END$$;
