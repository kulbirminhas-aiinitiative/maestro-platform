-- Migration 002: Add Full-Text Search Capabilities
-- Purpose: Enable advanced search with ranking for templates
-- Phase: 4 (Quick Wins - PostgreSQL Full-Text Search)

-- Create a text search configuration for templates
-- This combines name, description, tags, and category into a searchable document

-- Add tsvector column for full-text search
ALTER TABLE templates
ADD COLUMN IF NOT EXISTS search_vector tsvector;

-- Create function to update search vector
CREATE OR REPLACE FUNCTION templates_search_vector_update()
RETURNS trigger AS $$
BEGIN
    -- Combine relevant fields into search vector with different weights
    -- A = highest weight (1.0) for name
    -- B = high weight (0.4) for description and category
    -- C = medium weight (0.2) for tags
    -- D = low weight (0.1) for language and framework
    NEW.search_vector :=
        setweight(to_tsvector('english', coalesce(NEW.name, '')), 'A') ||
        setweight(to_tsvector('english', coalesce(NEW.description, '')), 'B') ||
        setweight(to_tsvector('english', coalesce(NEW.category, '')), 'B') ||
        setweight(to_tsvector('english', coalesce(array_to_string(NEW.tags, ' '), '')), 'C') ||
        setweight(to_tsvector('english', coalesce(NEW.language, '')), 'D') ||
        setweight(to_tsvector('english', coalesce(NEW.framework, '')), 'D');
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger to automatically update search vector
DROP TRIGGER IF EXISTS templates_search_vector_trigger ON templates;
CREATE TRIGGER templates_search_vector_trigger
    BEFORE INSERT OR UPDATE
    ON templates
    FOR EACH ROW
    EXECUTE FUNCTION templates_search_vector_update();

-- Create GIN index for fast full-text search
CREATE INDEX IF NOT EXISTS idx_templates_search_vector
    ON templates USING GIN(search_vector);

-- Update existing rows with search vectors
UPDATE templates
SET search_vector =
    setweight(to_tsvector('english', coalesce(name, '')), 'A') ||
    setweight(to_tsvector('english', coalesce(description, '')), 'B') ||
    setweight(to_tsvector('english', coalesce(category, '')), 'B') ||
    setweight(to_tsvector('english', coalesce(array_to_string(tags, ' '), '')), 'C') ||
    setweight(to_tsvector('english', coalesce(language, '')), 'D') ||
    setweight(to_tsvector('english', coalesce(framework, '')), 'D')
WHERE search_vector IS NULL;

-- Add search statistics columns
ALTER TABLE templates
ADD COLUMN IF NOT EXISTS search_rank FLOAT DEFAULT 0.0,
ADD COLUMN IF NOT EXISTS search_count INTEGER DEFAULT 0,
ADD COLUMN IF NOT EXISTS last_searched_at TIMESTAMP;

-- Create index for search statistics
CREATE INDEX IF NOT EXISTS idx_templates_search_rank
    ON templates(search_rank DESC);

CREATE INDEX IF NOT EXISTS idx_templates_search_count
    ON templates(search_count DESC);

-- Create materialized view for search popularity
CREATE MATERIALIZED VIEW IF NOT EXISTS template_search_stats AS
SELECT
    id,
    name,
    search_count,
    search_rank,
    last_searched_at,
    quality_score,
    usage_count,
    is_pinned,
    quality_tier
FROM templates
WHERE status = 'approved'
ORDER BY search_rank DESC, search_count DESC;

-- Create index on materialized view
CREATE INDEX IF NOT EXISTS idx_template_search_stats_rank
    ON template_search_stats(search_rank DESC);

-- Create function to refresh search stats
CREATE OR REPLACE FUNCTION refresh_template_search_stats()
RETURNS void AS $$
BEGIN
    REFRESH MATERIALIZED VIEW template_search_stats;
END;
$$ LANGUAGE plpgsql;

-- Grant permissions
GRANT SELECT ON template_search_stats TO maestro_registry_user;

COMMENT ON COLUMN templates.search_vector IS 'Full-text search vector combining name, description, tags, etc.';
COMMENT ON COLUMN templates.search_rank IS 'Search relevance rank (calculated during search)';
COMMENT ON COLUMN templates.search_count IS 'Number of times this template appeared in search results';
COMMENT ON COLUMN templates.last_searched_at IS 'Last time this template was found in a search';
COMMENT ON MATERIALIZED VIEW template_search_stats IS 'Cached search statistics for performance';
