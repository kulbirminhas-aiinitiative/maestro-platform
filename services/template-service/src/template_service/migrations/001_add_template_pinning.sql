-- Migration: Add template pinning feature
-- Created: 2025-10-01
-- Description: Add pinning fields to templates table for "golden" template recommendations

-- Add new columns for template pinning
ALTER TABLE templates
ADD COLUMN IF NOT EXISTS is_pinned BOOLEAN DEFAULT false,
ADD COLUMN IF NOT EXISTS quality_tier VARCHAR(20) DEFAULT 'standard',
ADD COLUMN IF NOT EXISTS pin_reason TEXT,
ADD COLUMN IF NOT EXISTS pinned_at TIMESTAMP,
ADD COLUMN IF NOT EXISTS pinned_by VARCHAR(255);

-- Add check constraint for quality_tier
ALTER TABLE templates
ADD CONSTRAINT check_quality_tier
CHECK (quality_tier IN ('gold', 'silver', 'bronze', 'standard'));

-- Create index for pinned templates (for fast filtering)
CREATE INDEX IF NOT EXISTS idx_templates_pinned
ON templates(is_pinned)
WHERE is_pinned = true;

-- Create index for quality tier filtering
CREATE INDEX IF NOT EXISTS idx_templates_quality_tier
ON templates(quality_tier);

-- Add comment to document the feature
COMMENT ON COLUMN templates.is_pinned IS 'Whether this template is pinned as recommended';
COMMENT ON COLUMN templates.quality_tier IS 'Quality tier: gold (best), silver, bronze, standard';
COMMENT ON COLUMN templates.pin_reason IS 'Business reason for pinning this template';
COMMENT ON COLUMN templates.pinned_at IS 'Timestamp when template was pinned';
COMMENT ON COLUMN templates.pinned_by IS 'User who pinned the template';
