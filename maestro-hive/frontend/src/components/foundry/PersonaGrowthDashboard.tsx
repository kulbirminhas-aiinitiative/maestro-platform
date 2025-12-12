/**
 * PersonaGrowthDashboard Component
 *
 * Displays persona evolution and growth metrics with interactive visualizations.
 *
 * EPIC: MD-3021 - Persona Evolution & Learning
 * AC-3: Persona growth dashboard frontend component
 */

import React, { useState, useEffect, useCallback, useMemo } from 'react';

// Types
interface SkillLevel {
  skillId: string;
  skillName: string;
  level: number;
  previousLevel: number;
  trend: 'up' | 'down' | 'stable';
}

interface Milestone {
  id: string;
  type: string;
  skillId: string | null;
  achievedAt: string;
  description: string;
  previousValue: number;
  newValue: number;
}

interface GrowthMetrics {
  velocity: number;
  acceleration: number;
  skillsImproved: number;
  skillsDeclined: number;
  milestonesAchieved: number;
  dominantSkill: string | null;
  growthTrend: 'accelerating' | 'steady' | 'decelerating' | 'stagnant';
}

interface EvolutionSnapshot {
  id: string;
  timestamp: string;
  stage: string;
  overallLevel: number;
  skillLevels: Record<string, number>;
  growthVelocity: number;
  activeSkills: number;
  totalExperiences: number;
}

interface PersonaEvolutionData {
  personaId: string;
  personaName: string;
  stage: string;
  overallLevel: number;
  skillCount: number;
  skillLevels: SkillLevel[];
  totalMilestones: number;
  recentMilestones: Milestone[];
  growthMetrics: GrowthMetrics | null;
  experienceCount: number;
  snapshots: EvolutionSnapshot[];
}

interface PersonaGrowthDashboardProps {
  personaId: string;
  refreshInterval?: number;
  onMilestoneClick?: (milestone: Milestone) => void;
  onSkillClick?: (skill: SkillLevel) => void;
  className?: string;
}

// Stage configuration
const STAGE_CONFIG: Record<string, { label: string; color: string; icon: string }> = {
  nascent: { label: 'Nascent', color: '#9CA3AF', icon: '🌱' },
  developing: { label: 'Developing', color: '#60A5FA', icon: '🌿' },
  competent: { label: 'Competent', color: '#34D399', icon: '🌳' },
  proficient: { label: 'Proficient', color: '#FBBF24', icon: '⭐' },
  expert: { label: 'Expert', color: '#F97316', icon: '🏆' },
  master: { label: 'Master', color: '#8B5CF6', icon: '👑' },
};

// Trend icons
const TREND_ICONS: Record<string, string> = {
  up: '↑',
  down: '↓',
  stable: '→',
};

const GROWTH_TREND_CONFIG: Record<string, { label: string; color: string }> = {
  accelerating: { label: 'Accelerating', color: '#22C55E' },
  steady: { label: 'Steady', color: '#3B82F6' },
  decelerating: { label: 'Decelerating', color: '#F59E0B' },
  stagnant: { label: 'Stagnant', color: '#EF4444' },
};

/**
 * Progress bar component for skill levels
 */
const SkillProgressBar: React.FC<{
  skill: SkillLevel;
  onClick?: () => void;
}> = ({ skill, onClick }) => {
  const percentage = Math.round(skill.level * 100);
  const previousPercentage = Math.round(skill.previousLevel * 100);
  const change = percentage - previousPercentage;

  return (
    <div
      className="skill-progress-item"
      onClick={onClick}
      style={{ cursor: onClick ? 'pointer' : 'default' }}
    >
      <div className="skill-header">
        <span className="skill-name">{skill.skillName}</span>
        <span className="skill-level">
          {percentage}%
          {change !== 0 && (
            <span className={`skill-change ${change > 0 ? 'positive' : 'negative'}`}>
              {TREND_ICONS[skill.trend]} {change > 0 ? '+' : ''}{change}%
            </span>
          )}
        </span>
      </div>
      <div className="progress-bar-container">
        <div
          className="progress-bar-fill"
          style={{
            width: `${percentage}%`,
            backgroundColor: getSkillColor(skill.level),
          }}
        />
        {skill.previousLevel > 0 && skill.previousLevel !== skill.level && (
          <div
            className="progress-bar-previous"
            style={{ left: `${previousPercentage}%` }}
          />
        )}
      </div>
    </div>
  );
};

/**
 * Get color based on skill level
 */
function getSkillColor(level: number): string {
  if (level >= 0.9) return '#8B5CF6'; // Purple - Master
  if (level >= 0.75) return '#F97316'; // Orange - Expert
  if (level >= 0.6) return '#FBBF24'; // Yellow - Proficient
  if (level >= 0.4) return '#34D399'; // Green - Competent
  if (level >= 0.2) return '#60A5FA'; // Blue - Developing
  return '#9CA3AF'; // Gray - Nascent
}

/**
 * Milestone card component
 */
const MilestoneCard: React.FC<{
  milestone: Milestone;
  onClick?: () => void;
}> = ({ milestone, onClick }) => {
  const formattedDate = new Date(milestone.achievedAt).toLocaleDateString();

  return (
    <div
      className="milestone-card"
      onClick={onClick}
      style={{ cursor: onClick ? 'pointer' : 'default' }}
    >
      <div className="milestone-icon">
        {getMilestoneIcon(milestone.type)}
      </div>
      <div className="milestone-content">
        <div className="milestone-description">{milestone.description}</div>
        <div className="milestone-date">{formattedDate}</div>
      </div>
    </div>
  );
};

/**
 * Get icon for milestone type
 */
function getMilestoneIcon(type: string): string {
  const icons: Record<string, string> = {
    skill_acquired: '✨',
    skill_mastery: '🏆',
    level_up: '⬆️',
    streak_achieved: '🔥',
    growth_spurt: '🚀',
    expertise_threshold: '⭐',
    specialization: '🎯',
    cross_skill_synergy: '🔗',
  };
  return icons[type] || '📌';
}

/**
 * Growth metrics summary component
 */
const GrowthMetricsSummary: React.FC<{
  metrics: GrowthMetrics;
}> = ({ metrics }) => {
  const trendConfig = GROWTH_TREND_CONFIG[metrics.growthTrend];

  return (
    <div className="growth-metrics-summary">
      <div className="metrics-header">
        <h3>Growth Metrics</h3>
        <span
          className="growth-trend-badge"
          style={{ backgroundColor: trendConfig.color }}
        >
          {trendConfig.label}
        </span>
      </div>
      <div className="metrics-grid">
        <div className="metric-item">
          <span className="metric-value">{(metrics.velocity * 100).toFixed(2)}%</span>
          <span className="metric-label">Velocity/Day</span>
        </div>
        <div className="metric-item">
          <span className="metric-value">{metrics.skillsImproved}</span>
          <span className="metric-label">Skills Improved</span>
        </div>
        <div className="metric-item">
          <span className="metric-value">{metrics.milestonesAchieved}</span>
          <span className="metric-label">Milestones</span>
        </div>
        {metrics.dominantSkill && (
          <div className="metric-item">
            <span className="metric-value">{metrics.dominantSkill}</span>
            <span className="metric-label">Dominant Skill</span>
          </div>
        )}
      </div>
    </div>
  );
};

/**
 * Evolution stage indicator component
 */
const StageIndicator: React.FC<{
  stage: string;
  overallLevel: number;
}> = ({ stage, overallLevel }) => {
  const stageConfig = STAGE_CONFIG[stage] || STAGE_CONFIG.nascent;
  const percentage = Math.round(overallLevel * 100);

  return (
    <div className="stage-indicator">
      <div className="stage-icon" style={{ backgroundColor: stageConfig.color }}>
        {stageConfig.icon}
      </div>
      <div className="stage-info">
        <span className="stage-label">{stageConfig.label}</span>
        <span className="stage-level">{percentage}% Overall</span>
      </div>
      <div className="stage-progress">
        <div className="stage-progress-bar">
          {Object.entries(STAGE_CONFIG).map(([key, config], index) => (
            <div
              key={key}
              className={`stage-segment ${key === stage ? 'active' : ''}`}
              style={{
                backgroundColor: key === stage ? config.color : '#E5E7EB',
                opacity: Object.keys(STAGE_CONFIG).indexOf(key) <= Object.keys(STAGE_CONFIG).indexOf(stage) ? 1 : 0.3,
              }}
            />
          ))}
        </div>
      </div>
    </div>
  );
};

/**
 * Mini chart for growth history
 */
const GrowthSparkline: React.FC<{
  snapshots: EvolutionSnapshot[];
  height?: number;
}> = ({ snapshots, height = 60 }) => {
  if (snapshots.length < 2) {
    return <div className="sparkline-empty">Insufficient data</div>;
  }

  const levels = snapshots.map(s => s.overallLevel);
  const min = Math.min(...levels);
  const max = Math.max(...levels);
  const range = max - min || 0.1;

  const points = levels.map((level, index) => {
    const x = (index / (levels.length - 1)) * 100;
    const y = height - ((level - min) / range) * (height - 10);
    return `${x},${y}`;
  }).join(' ');

  return (
    <div className="growth-sparkline">
      <svg width="100%" height={height} viewBox={`0 0 100 ${height}`} preserveAspectRatio="none">
        <polyline
          points={points}
          fill="none"
          stroke="#3B82F6"
          strokeWidth="2"
          vectorEffect="non-scaling-stroke"
        />
        {levels.map((level, index) => {
          const x = (index / (levels.length - 1)) * 100;
          const y = height - ((level - min) / range) * (height - 10);
          return (
            <circle
              key={index}
              cx={x}
              cy={y}
              r="3"
              fill="#3B82F6"
              vectorEffect="non-scaling-stroke"
            />
          );
        })}
      </svg>
    </div>
  );
};

/**
 * Main PersonaGrowthDashboard component
 */
export const PersonaGrowthDashboard: React.FC<PersonaGrowthDashboardProps> = ({
  personaId,
  refreshInterval = 30000,
  onMilestoneClick,
  onSkillClick,
  className = '',
}) => {
  const [data, setData] = useState<PersonaEvolutionData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedTab, setSelectedTab] = useState<'skills' | 'milestones' | 'history'>('skills');

  /**
   * Fetch evolution data from API
   */
  const fetchEvolutionData = useCallback(async () => {
    try {
      const response = await fetch(`/api/personas/${personaId}/evolution`);

      if (!response.ok) {
        throw new Error(`Failed to fetch evolution data: ${response.statusText}`);
      }

      const json = await response.json();

      // Transform API response to component data format
      const transformedData: PersonaEvolutionData = {
        personaId: json.persona_id,
        personaName: json.persona_name || personaId,
        stage: json.stage,
        overallLevel: json.overall_level,
        skillCount: json.skill_count,
        skillLevels: Object.entries(json.skill_levels || {}).map(([id, level]) => ({
          skillId: id,
          skillName: formatSkillName(id),
          level: level as number,
          previousLevel: getPreviousLevel(json.snapshots, id),
          trend: getTrend(level as number, getPreviousLevel(json.snapshots, id)),
        })),
        totalMilestones: json.total_milestones,
        recentMilestones: (json.recent_milestones || []).map((m: any) => ({
          id: m.id,
          type: m.milestone_type,
          skillId: m.skill_id,
          achievedAt: m.achieved_at,
          description: m.description,
          previousValue: m.previous_value,
          newValue: m.new_value,
        })),
        growthMetrics: json.growth_metrics ? {
          velocity: json.growth_metrics.velocity,
          acceleration: json.growth_metrics.acceleration,
          skillsImproved: json.growth_metrics.skills_improved,
          skillsDeclined: json.growth_metrics.skills_declined,
          milestonesAchieved: json.growth_metrics.milestones_achieved,
          dominantSkill: json.growth_metrics.dominant_skill,
          growthTrend: json.growth_metrics.growth_trend,
        } : null,
        experienceCount: json.experience_count,
        snapshots: (json.snapshots || []).slice(-20).map((s: any) => ({
          id: s.id,
          timestamp: s.timestamp,
          stage: s.stage,
          overallLevel: s.overall_level,
          skillLevels: s.skill_levels,
          growthVelocity: s.growth_velocity,
          activeSkills: s.active_skills,
          totalExperiences: s.total_experiences,
        })),
      };

      setData(transformedData);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error occurred');
    } finally {
      setLoading(false);
    }
  }, [personaId]);

  // Initial fetch and refresh interval
  useEffect(() => {
    fetchEvolutionData();

    const interval = setInterval(fetchEvolutionData, refreshInterval);
    return () => clearInterval(interval);
  }, [fetchEvolutionData, refreshInterval]);

  // Sort skills by level (descending)
  const sortedSkills = useMemo(() => {
    if (!data) return [];
    return [...data.skillLevels].sort((a, b) => b.level - a.level);
  }, [data]);

  if (loading) {
    return (
      <div className={`persona-growth-dashboard loading ${className}`}>
        <div className="loading-spinner" />
        <span>Loading evolution data...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className={`persona-growth-dashboard error ${className}`}>
        <div className="error-icon">⚠️</div>
        <span>{error}</span>
        <button onClick={fetchEvolutionData}>Retry</button>
      </div>
    );
  }

  if (!data) {
    return (
      <div className={`persona-growth-dashboard empty ${className}`}>
        <div className="empty-icon">📊</div>
        <span>No evolution data available</span>
      </div>
    );
  }

  return (
    <div className={`persona-growth-dashboard ${className}`}>
      {/* Header */}
      <div className="dashboard-header">
        <h2>{data.personaName}</h2>
        <StageIndicator stage={data.stage} overallLevel={data.overallLevel} />
      </div>

      {/* Stats Summary */}
      <div className="stats-summary">
        <div className="stat-item">
          <span className="stat-value">{data.skillCount}</span>
          <span className="stat-label">Skills</span>
        </div>
        <div className="stat-item">
          <span className="stat-value">{data.experienceCount}</span>
          <span className="stat-label">Experiences</span>
        </div>
        <div className="stat-item">
          <span className="stat-value">{data.totalMilestones}</span>
          <span className="stat-label">Milestones</span>
        </div>
      </div>

      {/* Growth Metrics */}
      {data.growthMetrics && (
        <GrowthMetricsSummary metrics={data.growthMetrics} />
      )}

      {/* Growth History Sparkline */}
      {data.snapshots.length >= 2 && (
        <div className="growth-history-section">
          <h3>Growth History</h3>
          <GrowthSparkline snapshots={data.snapshots} />
        </div>
      )}

      {/* Tab Navigation */}
      <div className="tab-navigation">
        <button
          className={`tab-button ${selectedTab === 'skills' ? 'active' : ''}`}
          onClick={() => setSelectedTab('skills')}
        >
          Skills ({data.skillCount})
        </button>
        <button
          className={`tab-button ${selectedTab === 'milestones' ? 'active' : ''}`}
          onClick={() => setSelectedTab('milestones')}
        >
          Milestones ({data.totalMilestones})
        </button>
        <button
          className={`tab-button ${selectedTab === 'history' ? 'active' : ''}`}
          onClick={() => setSelectedTab('history')}
        >
          History
        </button>
      </div>

      {/* Tab Content */}
      <div className="tab-content">
        {selectedTab === 'skills' && (
          <div className="skills-tab">
            {sortedSkills.length === 0 ? (
              <div className="empty-state">No skills recorded yet</div>
            ) : (
              <div className="skills-list">
                {sortedSkills.map(skill => (
                  <SkillProgressBar
                    key={skill.skillId}
                    skill={skill}
                    onClick={onSkillClick ? () => onSkillClick(skill) : undefined}
                  />
                ))}
              </div>
            )}
          </div>
        )}

        {selectedTab === 'milestones' && (
          <div className="milestones-tab">
            {data.recentMilestones.length === 0 ? (
              <div className="empty-state">No milestones achieved yet</div>
            ) : (
              <div className="milestones-list">
                {data.recentMilestones.map(milestone => (
                  <MilestoneCard
                    key={milestone.id}
                    milestone={milestone}
                    onClick={onMilestoneClick ? () => onMilestoneClick(milestone) : undefined}
                  />
                ))}
              </div>
            )}
          </div>
        )}

        {selectedTab === 'history' && (
          <div className="history-tab">
            {data.snapshots.length === 0 ? (
              <div className="empty-state">No history available</div>
            ) : (
              <div className="snapshots-list">
                {data.snapshots.slice().reverse().map(snapshot => (
                  <div key={snapshot.id} className="snapshot-item">
                    <div className="snapshot-time">
                      {new Date(snapshot.timestamp).toLocaleString()}
                    </div>
                    <div className="snapshot-details">
                      <span className="snapshot-stage">
                        {STAGE_CONFIG[snapshot.stage]?.icon} {STAGE_CONFIG[snapshot.stage]?.label}
                      </span>
                      <span className="snapshot-level">
                        {Math.round(snapshot.overallLevel * 100)}%
                      </span>
                      <span className="snapshot-skills">
                        {snapshot.activeSkills} skills
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

// Helper functions
function formatSkillName(skillId: string): string {
  return skillId
    .replace(/_/g, ' ')
    .replace(/\b\w/g, c => c.toUpperCase());
}

function getPreviousLevel(snapshots: any[], skillId: string): number {
  if (!snapshots || snapshots.length < 2) return 0;
  const previousSnapshot = snapshots[snapshots.length - 2];
  return previousSnapshot?.skill_levels?.[skillId] || 0;
}

function getTrend(current: number, previous: number): 'up' | 'down' | 'stable' {
  const diff = current - previous;
  if (diff > 0.01) return 'up';
  if (diff < -0.01) return 'down';
  return 'stable';
}

export default PersonaGrowthDashboard;
