-- Rollback Migration: Remove template pinning feature
-- Created: 2025-10-01
-- Description: Rollback changes from 001_add_template_pinning.sql

-- Drop indexes
DROP INDEX IF EXISTS idx_templates_quality_tier;
DROP INDEX IF EXISTS idx_templates_pinned;

-- Drop check constraint
ALTER TABLE templates
DROP CONSTRAINT IF EXISTS check_quality_tier;

-- Drop columns
ALTER TABLE templates
DROP COLUMN IF EXISTS pinned_by,
DROP COLUMN IF EXISTS pinned_at,
DROP COLUMN IF EXISTS pin_reason,
DROP COLUMN IF EXISTS quality_tier,
DROP COLUMN IF EXISTS is_pinned;
