-- ============================================================================
-- Capability Registry Database Schema
-- JIRA: MD-2064 (part of MD-2042)
-- Description: Database schema for dynamic agent capability registration
-- ============================================================================

-- Enable UUID extension if not already enabled
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================================================
-- Agents Table
-- Stores agent profiles with availability and work limits
-- ============================================================================
CREATE TABLE IF NOT EXISTS capability_agents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    agent_id VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    persona_type VARCHAR(100),
    availability_status VARCHAR(20) DEFAULT 'offline'
        CHECK (availability_status IN ('available', 'busy', 'offline')),
    wip_limit INT DEFAULT 3 CHECK (wip_limit >= 0),
    current_wip INT DEFAULT 0 CHECK (current_wip >= 0),
    metadata JSONB DEFAULT '{}',
    last_active TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Index for quick agent lookups
CREATE INDEX IF NOT EXISTS idx_capability_agents_agent_id ON capability_agents(agent_id);
CREATE INDEX IF NOT EXISTS idx_capability_agents_persona_type ON capability_agents(persona_type);
CREATE INDEX IF NOT EXISTS idx_capability_agents_availability ON capability_agents(availability_status);

-- ============================================================================
-- Capabilities Table (Master List)
-- Stores the capability taxonomy with hierarchical structure
-- ============================================================================
CREATE TABLE IF NOT EXISTS capabilities (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    skill_id VARCHAR(255) UNIQUE NOT NULL,  -- e.g., "Backend:Python:FastAPI"
    parent_skill_id VARCHAR(255),            -- Hierarchy reference (e.g., "Backend:Python")
    category VARCHAR(100),                    -- Top-level category (e.g., "Backend")
    version VARCHAR(20) DEFAULT '1.0.0',
    description TEXT,
    deprecated BOOLEAN DEFAULT FALSE,
    successor_skill_id VARCHAR(255),         -- For deprecated skills, points to replacement
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Index for skill lookups and hierarchy navigation
CREATE INDEX IF NOT EXISTS idx_capabilities_skill_id ON capabilities(skill_id);
CREATE INDEX IF NOT EXISTS idx_capabilities_parent ON capabilities(parent_skill_id);
CREATE INDEX IF NOT EXISTS idx_capabilities_category ON capabilities(category);
CREATE INDEX IF NOT EXISTS idx_capabilities_deprecated ON capabilities(deprecated) WHERE deprecated = TRUE;

-- ============================================================================
-- Agent Capabilities Junction Table
-- Links agents to their capabilities with proficiency levels
-- ============================================================================
CREATE TABLE IF NOT EXISTS agent_capabilities (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    agent_id UUID NOT NULL REFERENCES capability_agents(id) ON DELETE CASCADE,
    capability_id UUID NOT NULL REFERENCES capabilities(id) ON DELETE CASCADE,
    proficiency INT NOT NULL CHECK (proficiency BETWEEN 1 AND 5),
    source VARCHAR(50) DEFAULT 'manual'
        CHECK (source IN ('manual', 'inferred', 'historical', 'assessment')),
    confidence FLOAT DEFAULT 1.0 CHECK (confidence BETWEEN 0.0 AND 1.0),
    last_used TIMESTAMP WITH TIME ZONE,
    execution_count INT DEFAULT 0 CHECK (execution_count >= 0),
    success_count INT DEFAULT 0 CHECK (success_count >= 0),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(agent_id, capability_id)
);

-- Indexes for capability lookups
CREATE INDEX IF NOT EXISTS idx_agent_capabilities_agent ON agent_capabilities(agent_id);
CREATE INDEX IF NOT EXISTS idx_agent_capabilities_capability ON agent_capabilities(capability_id);
CREATE INDEX IF NOT EXISTS idx_agent_capabilities_proficiency ON agent_capabilities(proficiency);

-- ============================================================================
-- Agent Quality History
-- Tracks quality scores for performance trending
-- ============================================================================
CREATE TABLE IF NOT EXISTS agent_quality_history (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    agent_id UUID NOT NULL REFERENCES capability_agents(id) ON DELETE CASCADE,
    task_id VARCHAR(255),
    quality_score FLOAT CHECK (quality_score BETWEEN 0.0 AND 1.0),
    execution_time_ms INT,
    skill_id VARCHAR(255),  -- Which capability was used
    recorded_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for quality history queries
CREATE INDEX IF NOT EXISTS idx_quality_history_agent ON agent_quality_history(agent_id);
CREATE INDEX IF NOT EXISTS idx_quality_history_recorded ON agent_quality_history(recorded_at);
CREATE INDEX IF NOT EXISTS idx_quality_history_agent_recent ON agent_quality_history(agent_id, recorded_at DESC);

-- ============================================================================
-- Capability Groups Table
-- Stores predefined capability groups (e.g., FullStackWeb)
-- ============================================================================
CREATE TABLE IF NOT EXISTS capability_groups (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    group_name VARCHAR(100) UNIQUE NOT NULL,
    description TEXT,
    skill_ids TEXT[] NOT NULL,  -- Array of skill_ids in this group
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_capability_groups_name ON capability_groups(group_name);

-- ============================================================================
-- Update Timestamp Trigger
-- Automatically updates updated_at on row changes
-- ============================================================================
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply trigger to capability_agents
DROP TRIGGER IF EXISTS update_capability_agents_updated_at ON capability_agents;
CREATE TRIGGER update_capability_agents_updated_at
    BEFORE UPDATE ON capability_agents
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Apply trigger to agent_capabilities
DROP TRIGGER IF EXISTS update_agent_capabilities_updated_at ON agent_capabilities;
CREATE TRIGGER update_agent_capabilities_updated_at
    BEFORE UPDATE ON agent_capabilities
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- Views for Common Queries
-- ============================================================================

-- View: Agent capabilities with skill details
CREATE OR REPLACE VIEW v_agent_capability_details AS
SELECT
    ca.id,
    a.agent_id,
    a.name AS agent_name,
    a.persona_type,
    a.availability_status,
    a.current_wip,
    a.wip_limit,
    c.skill_id,
    c.category,
    c.version AS skill_version,
    ac.proficiency,
    ac.source,
    ac.confidence,
    ac.execution_count,
    ac.success_count,
    ac.last_used
FROM capability_agents a
JOIN agent_capabilities ac ON a.id = ac.agent_id
JOIN capabilities c ON ac.capability_id = c.id;

-- View: Agent quality summary (rolling 20 scores)
CREATE OR REPLACE VIEW v_agent_quality_summary AS
SELECT
    agent_id,
    COUNT(*) AS total_executions,
    AVG(quality_score) AS avg_quality_score,
    MIN(quality_score) AS min_quality_score,
    MAX(quality_score) AS max_quality_score,
    AVG(execution_time_ms) AS avg_execution_time_ms,
    MAX(recorded_at) AS last_execution
FROM (
    SELECT
        agent_id,
        quality_score,
        execution_time_ms,
        recorded_at,
        ROW_NUMBER() OVER (PARTITION BY agent_id ORDER BY recorded_at DESC) AS rn
    FROM agent_quality_history
) ranked
WHERE rn <= 20  -- Rolling 20 most recent scores
GROUP BY agent_id;

-- ============================================================================
-- Seed Default Capability Groups
-- ============================================================================
INSERT INTO capability_groups (group_name, description, skill_ids) VALUES
    ('FullStackWeb', 'Full stack web development capabilities',
     ARRAY['Web:React', 'Backend:Node', 'Data:PostgreSQL', 'DevOps:Docker']),
    ('BackendAPI', 'Backend API development capabilities',
     ARRAY['Backend:Python:FastAPI', 'Data:SQL', 'Architecture:APIDesign', 'Testing:Integration']),
    ('FrontendExpert', 'Frontend development expertise',
     ARRAY['Web:React', 'Web:TypeScript', 'Testing:E2E', 'Testing:Unit']),
    ('DevOpsEngineer', 'DevOps and infrastructure capabilities',
     ARRAY['DevOps:Kubernetes', 'DevOps:CI/CD', 'DevOps:Terraform', 'DevOps:Monitoring']),
    ('SecuritySpecialist', 'Security and compliance capabilities',
     ARRAY['Security:OWASP', 'Security:SAST', 'Security:PenetrationTesting', 'Architecture:APIDesign']),
    ('DataEngineer', 'Data engineering capabilities',
     ARRAY['Data:DataEngineering', 'Backend:Python', 'Data:SQL', 'Data:NoSQL']),
    ('QAEngineer', 'Quality assurance capabilities',
     ARRAY['Testing:Unit', 'Testing:Integration', 'Testing:E2E', 'Testing:Performance'])
ON CONFLICT (group_name) DO NOTHING;

-- ============================================================================
-- Comments for Documentation
-- ============================================================================
COMMENT ON TABLE capability_agents IS 'Stores agent profiles for the capability registry';
COMMENT ON TABLE capabilities IS 'Master list of capabilities from the taxonomy';
COMMENT ON TABLE agent_capabilities IS 'Junction table linking agents to their capabilities with proficiency';
COMMENT ON TABLE agent_quality_history IS 'Historical quality scores for agents';
COMMENT ON TABLE capability_groups IS 'Predefined groups of related capabilities';

COMMENT ON COLUMN capability_agents.availability_status IS 'Current availability: available, busy, or offline';
COMMENT ON COLUMN capability_agents.wip_limit IS 'Maximum concurrent work items for this agent';
COMMENT ON COLUMN agent_capabilities.proficiency IS 'Skill level from 1 (beginner) to 5 (expert)';
COMMENT ON COLUMN agent_capabilities.source IS 'How proficiency was determined: manual, inferred, historical, assessment';
COMMENT ON COLUMN agent_capabilities.confidence IS 'Confidence score for inferred capabilities (0.0-1.0)';
