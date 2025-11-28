-- Migration 003: Add Quality Validation Tracking
-- Purpose: Track Quality-Fabric validation results for templates
-- Phase: 4 (Quality-Fabric Integration)

-- Create table for validation history
CREATE TABLE IF NOT EXISTS template_validations (
    id SERIAL PRIMARY KEY,
    template_id UUID NOT NULL REFERENCES templates(id) ON DELETE CASCADE,

    -- Validation metadata
    validation_type VARCHAR(20) NOT NULL CHECK (validation_type IN ('quick', 'full', 'security', 'performance')),
    status VARCHAR(20) NOT NULL CHECK (status IN ('pending', 'running', 'completed', 'failed')),
    priority VARCHAR(20) DEFAULT 'normal' CHECK (priority IN ('low', 'normal', 'high', 'critical')),

    -- Scores (populated after validation)
    quality_score FLOAT CHECK (quality_score >= 0 AND quality_score <= 100),
    security_score FLOAT CHECK (security_score >= 0 AND security_score <= 100),
    performance_score FLOAT CHECK (performance_score >= 0 AND performance_score <= 100),
    maintainability_score FLOAT CHECK (maintainability_score >= 0 AND maintainability_score <= 100),

    -- Test results
    passed BOOLEAN,
    tests_run INTEGER DEFAULT 0,
    tests_passed INTEGER DEFAULT 0,
    tests_failed INTEGER DEFAULT 0,

    -- Issues and recommendations (JSON)
    issues JSONB DEFAULT '[]'::jsonb,
    recommendations TEXT[],

    -- Timing
    started_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP,

    -- Metadata
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_template_validations_template_id
    ON template_validations(template_id);

CREATE INDEX IF NOT EXISTS idx_template_validations_status
    ON template_validations(status);

CREATE INDEX IF NOT EXISTS idx_template_validations_started_at
    ON template_validations(started_at DESC);

-- Composite index for latest validation per template
CREATE INDEX IF NOT EXISTS idx_template_validations_latest
    ON template_validations(template_id, started_at DESC);

-- Add validation tracking to templates table
ALTER TABLE templates
ADD COLUMN IF NOT EXISTS last_validation_at TIMESTAMP,
ADD COLUMN IF NOT EXISTS last_validation_status VARCHAR(20),
ADD COLUMN IF NOT EXISTS last_validation_passed BOOLEAN,
ADD COLUMN IF NOT EXISTS validation_count INTEGER DEFAULT 0;

-- Create trigger to update template validation stats
CREATE OR REPLACE FUNCTION update_template_validation_stats()
RETURNS trigger AS $$
BEGIN
    -- Update templates table with latest validation
    IF NEW.status = 'completed' THEN
        UPDATE templates
        SET
            last_validation_at = NEW.completed_at,
            last_validation_status = NEW.status,
            last_validation_passed = NEW.passed,
            validation_count = validation_count + 1,
            updated_at = NOW()
        WHERE id = NEW.template_id;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS template_validation_stats_trigger ON template_validations;
CREATE TRIGGER template_validation_stats_trigger
    AFTER INSERT OR UPDATE OF status
    ON template_validations
    FOR EACH ROW
    WHEN (NEW.status = 'completed')
    EXECUTE FUNCTION update_template_validation_stats();

-- Create materialized view for validation statistics
CREATE MATERIALIZED VIEW IF NOT EXISTS validation_statistics AS
SELECT
    validation_type,
    status,
    COUNT(*) as count,
    AVG(quality_score) as avg_quality_score,
    AVG(security_score) as avg_security_score,
    AVG(performance_score) as avg_performance_score,
    AVG(maintainability_score) as avg_maintainability_score,
    AVG(EXTRACT(EPOCH FROM (completed_at - started_at))) as avg_duration_seconds,
    SUM(CASE WHEN passed THEN 1 ELSE 0 END) as passed_count,
    SUM(CASE WHEN passed THEN 0 ELSE 1 END) as failed_count
FROM template_validations
WHERE status = 'completed'
GROUP BY validation_type, status;

-- Create index on materialized view
CREATE INDEX IF NOT EXISTS idx_validation_statistics_type
    ON validation_statistics(validation_type);

-- Function to refresh validation statistics
CREATE OR REPLACE FUNCTION refresh_validation_statistics()
RETURNS void AS $$
BEGIN
    REFRESH MATERIALIZED VIEW validation_statistics;
END;
$$ LANGUAGE plpgsql;

-- Grant permissions
GRANT SELECT, INSERT, UPDATE ON template_validations TO maestro_registry_user;
GRANT USAGE, SELECT ON SEQUENCE template_validations_id_seq TO maestro_registry_user;
GRANT SELECT ON validation_statistics TO maestro_registry_user;

-- Add comments
COMMENT ON TABLE template_validations IS 'Tracks Quality-Fabric validation results for templates';
COMMENT ON COLUMN template_validations.validation_type IS 'Type of validation: quick, full, security, performance';
COMMENT ON COLUMN template_validations.status IS 'Current status: pending, running, completed, failed';
COMMENT ON COLUMN template_validations.issues IS 'JSON array of issues found during validation';
COMMENT ON COLUMN template_validations.recommendations IS 'Array of improvement recommendations';
COMMENT ON COLUMN templates.last_validation_at IS 'Timestamp of most recent validation';
COMMENT ON COLUMN templates.last_validation_passed IS 'Result of most recent validation';
COMMENT ON COLUMN templates.validation_count IS 'Total number of validations performed';
COMMENT ON MATERIALIZED VIEW validation_statistics IS 'Aggregated validation statistics by type and status';
