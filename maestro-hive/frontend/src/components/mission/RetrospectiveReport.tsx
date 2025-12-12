/**
 * RetrospectiveReport Component
 *
 * Displays automated team retrospective results including:
 * - Overall performance score with radar chart
 * - Category breakdowns
 * - Improvement recommendations
 * - Action item tracking
 *
 * EPIC: MD-3015 - Autonomous Team Retrospective & Evaluation
 */

import React, { useState, useEffect } from 'react';

// Configuration
export const REPORT_CONFIG = {
  chartType: 'radar' as const,
  showTrends: true,
  maxActionItems: 10,
  refreshInterval: 30000,
};

// Types
interface CategoryScore {
  category: string;
  score: number;
  trend?: number;
}

interface Improvement {
  id: string;
  title: string;
  description: string;
  category: string;
  impact_score: number;
  effort_score: number;
  priority: number;
}

interface ActionItem {
  id: string;
  title: string;
  description: string;
  status: 'open' | 'in_progress' | 'completed' | 'deferred';
  due_date?: string;
  assignee?: string;
}

interface RetrospectiveData {
  id: string;
  team_id: string;
  sprint_id: string;
  overall_score: number;
  category_scores: CategoryScore[];
  strengths: string[];
  areas_for_improvement: string[];
  improvements: Improvement[];
  action_items: ActionItem[];
  generated_at: string;
}

interface RetrospectiveReportProps {
  teamId: string;
  sprintId?: string;
  onActionItemUpdate?: (item: ActionItem) => void;
}

// Score level helper
const getScoreLevel = (score: number): { label: string; color: string } => {
  if (score >= 0.9) return { label: 'Exceptional', color: '#10B981' };
  if (score >= 0.75) return { label: 'Strong', color: '#34D399' };
  if (score >= 0.6) return { label: 'Meeting Expectations', color: '#FBBF24' };
  if (score >= 0.4) return { label: 'Needs Improvement', color: '#F97316' };
  return { label: 'Critical', color: '#EF4444' };
};

// Priority quadrant helper
const getPriorityLabel = (impact: number, effort: number): string => {
  if (impact >= 0.6 && effort <= 0.5) return 'Quick Win';
  if (impact >= 0.6 && effort > 0.5) return 'Strategic';
  if (impact < 0.6 && effort <= 0.5) return 'Fill-in';
  return 'Low Priority';
};

// Score Badge Component
const ScoreBadge: React.FC<{ score: number }> = ({ score }) => {
  const { label, color } = getScoreLevel(score);
  return (
    <span
      style={{
        backgroundColor: color,
        color: 'white',
        padding: '4px 12px',
        borderRadius: '16px',
        fontSize: '14px',
        fontWeight: 500,
      }}
    >
      {label} ({Math.round(score * 100)}%)
    </span>
  );
};

// Trend Indicator Component
const TrendIndicator: React.FC<{ trend?: number }> = ({ trend }) => {
  if (!trend) return null;
  const isPositive = trend > 0;
  return (
    <span
      style={{
        color: isPositive ? '#10B981' : '#EF4444',
        marginLeft: '8px',
        fontSize: '12px',
      }}
    >
      {isPositive ? '↑' : '↓'} {Math.abs(trend)}%
    </span>
  );
};

// Radar Chart Component (simplified SVG implementation)
const RadarChart: React.FC<{ scores: CategoryScore[] }> = ({ scores }) => {
  const size = 200;
  const center = size / 2;
  const radius = 80;

  const points = scores.map((score, index) => {
    const angle = (Math.PI * 2 * index) / scores.length - Math.PI / 2;
    const r = radius * score.score;
    return {
      x: center + r * Math.cos(angle),
      y: center + r * Math.sin(angle),
      label: score.category,
      labelX: center + (radius + 20) * Math.cos(angle),
      labelY: center + (radius + 20) * Math.sin(angle),
    };
  });

  const pathData = points.map((p, i) => `${i === 0 ? 'M' : 'L'} ${p.x} ${p.y}`).join(' ') + ' Z';

  return (
    <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
      {/* Background grid */}
      {[0.25, 0.5, 0.75, 1].map((scale) => (
        <polygon
          key={scale}
          points={scores
            .map((_, i) => {
              const angle = (Math.PI * 2 * i) / scores.length - Math.PI / 2;
              const r = radius * scale;
              return `${center + r * Math.cos(angle)},${center + r * Math.sin(angle)}`;
            })
            .join(' ')}
          fill="none"
          stroke="#E5E7EB"
          strokeWidth="1"
        />
      ))}

      {/* Data polygon */}
      <polygon
        points={points.map((p) => `${p.x},${p.y}`).join(' ')}
        fill="rgba(59, 130, 246, 0.3)"
        stroke="#3B82F6"
        strokeWidth="2"
      />

      {/* Data points */}
      {points.map((p, i) => (
        <circle key={i} cx={p.x} cy={p.y} r="4" fill="#3B82F6" />
      ))}

      {/* Labels */}
      {points.map((p, i) => (
        <text
          key={i}
          x={p.labelX}
          y={p.labelY}
          textAnchor="middle"
          dominantBaseline="middle"
          fontSize="10"
          fill="#6B7280"
        >
          {p.label.replace(/_/g, ' ')}
        </text>
      ))}
    </svg>
  );
};

// Category Score Row Component
const CategoryScoreRow: React.FC<{ score: CategoryScore }> = ({ score }) => {
  const percentage = Math.round(score.score * 100);
  const { color } = getScoreLevel(score.score);

  return (
    <div style={{ marginBottom: '12px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
        <span style={{ fontSize: '14px', color: '#374151' }}>
          {score.category.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())}
        </span>
        <span style={{ fontSize: '14px', fontWeight: 500 }}>
          {percentage}%
          <TrendIndicator trend={score.trend} />
        </span>
      </div>
      <div
        style={{
          height: '8px',
          backgroundColor: '#E5E7EB',
          borderRadius: '4px',
          overflow: 'hidden',
        }}
      >
        <div
          style={{
            width: `${percentage}%`,
            height: '100%',
            backgroundColor: color,
            transition: 'width 0.3s ease',
          }}
        />
      </div>
    </div>
  );
};

// Improvement Card Component
const ImprovementCard: React.FC<{ improvement: Improvement }> = ({ improvement }) => {
  const priorityLabel = getPriorityLabel(improvement.impact_score, improvement.effort_score);
  const priorityColor =
    priorityLabel === 'Quick Win' ? '#10B981' : priorityLabel === 'Strategic' ? '#3B82F6' : '#9CA3AF';

  return (
    <div
      style={{
        border: '1px solid #E5E7EB',
        borderRadius: '8px',
        padding: '16px',
        marginBottom: '12px',
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <h4 style={{ margin: 0, fontSize: '16px', color: '#111827' }}>{improvement.title}</h4>
        <span
          style={{
            backgroundColor: priorityColor,
            color: 'white',
            padding: '2px 8px',
            borderRadius: '4px',
            fontSize: '12px',
          }}
        >
          {priorityLabel}
        </span>
      </div>
      <p style={{ margin: '8px 0', fontSize: '14px', color: '#6B7280' }}>{improvement.description}</p>
      <div style={{ display: 'flex', gap: '16px', fontSize: '12px', color: '#9CA3AF' }}>
        <span>Impact: {Math.round(improvement.impact_score * 100)}%</span>
        <span>Effort: {Math.round(improvement.effort_score * 100)}%</span>
        <span>Category: {improvement.category}</span>
      </div>
    </div>
  );
};

// Action Item Component
const ActionItemRow: React.FC<{
  item: ActionItem;
  onStatusChange?: (status: ActionItem['status']) => void;
}> = ({ item, onStatusChange }) => {
  const statusColors: Record<ActionItem['status'], string> = {
    open: '#3B82F6',
    in_progress: '#FBBF24',
    completed: '#10B981',
    deferred: '#9CA3AF',
  };

  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        padding: '12px',
        borderBottom: '1px solid #E5E7EB',
      }}
    >
      <input
        type="checkbox"
        checked={item.status === 'completed'}
        onChange={() => onStatusChange?.(item.status === 'completed' ? 'open' : 'completed')}
        style={{ marginRight: '12px' }}
      />
      <div style={{ flex: 1 }}>
        <div
          style={{
            fontSize: '14px',
            color: item.status === 'completed' ? '#9CA3AF' : '#111827',
            textDecoration: item.status === 'completed' ? 'line-through' : 'none',
          }}
        >
          {item.title}
        </div>
        {item.due_date && (
          <div style={{ fontSize: '12px', color: '#9CA3AF' }}>
            Due: {new Date(item.due_date).toLocaleDateString()}
          </div>
        )}
      </div>
      <span
        style={{
          backgroundColor: statusColors[item.status],
          color: 'white',
          padding: '2px 8px',
          borderRadius: '4px',
          fontSize: '12px',
        }}
      >
        {item.status.replace(/_/g, ' ')}
      </span>
    </div>
  );
};

// Main Component
export const RetrospectiveReport: React.FC<RetrospectiveReportProps> = ({
  teamId,
  sprintId,
  onActionItemUpdate,
}) => {
  const [data, setData] = useState<RetrospectiveData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        // In production, this would fetch from the API
        // const response = await fetch(`/api/v1/retrospectives/${teamId}/${sprintId}`);
        // const result = await response.json();
        // setData(result);

        // Mock data for demonstration
        setData({
          id: 'retro-001',
          team_id: teamId,
          sprint_id: sprintId || 'current',
          overall_score: 0.78,
          category_scores: [
            { category: 'velocity_consistency', score: 0.82, trend: 5 },
            { category: 'quality_metrics', score: 0.75, trend: -2 },
            { category: 'collaboration_score', score: 0.85, trend: 10 },
            { category: 'delivery_reliability', score: 0.72, trend: 3 },
          ],
          strengths: [
            'Strong collaboration score: 85%',
            'Improving velocity consistency',
            'Good code review practices',
          ],
          areas_for_improvement: [
            'Quality metrics need attention',
            'Delivery reliability below target',
          ],
          improvements: [
            {
              id: 'imp-1',
              title: 'Implement Automated Testing',
              description: 'Add unit and integration tests to improve quality metrics',
              category: 'quality',
              impact_score: 0.85,
              effort_score: 0.6,
              priority: 1,
            },
            {
              id: 'imp-2',
              title: 'Reduce Code Review Turnaround',
              description: 'Implement review SLAs and pair programming',
              category: 'collaboration',
              impact_score: 0.75,
              effort_score: 0.3,
              priority: 2,
            },
          ],
          action_items: [
            {
              id: 'action-1',
              title: 'Set up CI/CD pipeline with test gates',
              description: 'Configure automated testing in pipeline',
              status: 'in_progress',
              due_date: '2025-12-23',
            },
            {
              id: 'action-2',
              title: 'Document code review guidelines',
              description: 'Create team guidelines for code reviews',
              status: 'open',
              due_date: '2025-12-20',
            },
          ],
          generated_at: new Date().toISOString(),
        });
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load retrospective');
      } finally {
        setLoading(false);
      }
    };

    fetchData();

    // Set up auto-refresh if configured
    if (REPORT_CONFIG.refreshInterval > 0) {
      const interval = setInterval(fetchData, REPORT_CONFIG.refreshInterval);
      return () => clearInterval(interval);
    }
  }, [teamId, sprintId]);

  if (loading) {
    return (
      <div style={{ padding: '40px', textAlign: 'center' }}>
        <div style={{ color: '#6B7280' }}>Loading retrospective data...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div
        style={{
          padding: '40px',
          textAlign: 'center',
          color: '#EF4444',
        }}
      >
        Error: {error}
      </div>
    );
  }

  if (!data) {
    return (
      <div style={{ padding: '40px', textAlign: 'center', color: '#6B7280' }}>
        No retrospective data available
      </div>
    );
  }

  return (
    <div style={{ maxWidth: '1200px', margin: '0 auto', padding: '24px' }}>
      {/* Header */}
      <div style={{ marginBottom: '32px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <h1 style={{ margin: 0, fontSize: '24px', color: '#111827' }}>Team Retrospective Report</h1>
          <ScoreBadge score={data.overall_score} />
        </div>
        <p style={{ margin: '8px 0 0', color: '#6B7280', fontSize: '14px' }}>
          Team: {data.team_id} | Sprint: {data.sprint_id} | Generated:{' '}
          {new Date(data.generated_at).toLocaleString()}
        </p>
      </div>

      {/* Main Grid */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))',
          gap: '24px',
        }}
      >
        {/* Performance Overview */}
        <div
          style={{
            backgroundColor: 'white',
            borderRadius: '12px',
            padding: '24px',
            boxShadow: '0 1px 3px rgba(0,0,0,0.1)',
          }}
        >
          <h2 style={{ margin: '0 0 16px', fontSize: '18px', color: '#111827' }}>
            Performance Overview
          </h2>
          <div style={{ display: 'flex', justifyContent: 'center', marginBottom: '24px' }}>
            <RadarChart scores={data.category_scores} />
          </div>
          <div>
            {data.category_scores.map((score) => (
              <CategoryScoreRow key={score.category} score={score} />
            ))}
          </div>
        </div>

        {/* Strengths & Improvements */}
        <div
          style={{
            backgroundColor: 'white',
            borderRadius: '12px',
            padding: '24px',
            boxShadow: '0 1px 3px rgba(0,0,0,0.1)',
          }}
        >
          <h2 style={{ margin: '0 0 16px', fontSize: '18px', color: '#111827' }}>Key Insights</h2>

          <h3 style={{ margin: '0 0 8px', fontSize: '14px', color: '#10B981' }}>Strengths</h3>
          <ul style={{ margin: '0 0 24px', paddingLeft: '20px' }}>
            {data.strengths.map((strength, i) => (
              <li key={i} style={{ fontSize: '14px', color: '#374151', marginBottom: '4px' }}>
                {strength}
              </li>
            ))}
          </ul>

          <h3 style={{ margin: '0 0 8px', fontSize: '14px', color: '#F97316' }}>Areas for Improvement</h3>
          <ul style={{ margin: 0, paddingLeft: '20px' }}>
            {data.areas_for_improvement.map((area, i) => (
              <li key={i} style={{ fontSize: '14px', color: '#374151', marginBottom: '4px' }}>
                {area}
              </li>
            ))}
          </ul>
        </div>
      </div>

      {/* Recommendations */}
      <div
        style={{
          backgroundColor: 'white',
          borderRadius: '12px',
          padding: '24px',
          marginTop: '24px',
          boxShadow: '0 1px 3px rgba(0,0,0,0.1)',
        }}
      >
        <h2 style={{ margin: '0 0 16px', fontSize: '18px', color: '#111827' }}>
          Recommended Improvements
        </h2>
        {data.improvements.map((improvement) => (
          <ImprovementCard key={improvement.id} improvement={improvement} />
        ))}
      </div>

      {/* Action Items */}
      <div
        style={{
          backgroundColor: 'white',
          borderRadius: '12px',
          padding: '24px',
          marginTop: '24px',
          boxShadow: '0 1px 3px rgba(0,0,0,0.1)',
        }}
      >
        <h2 style={{ margin: '0 0 16px', fontSize: '18px', color: '#111827' }}>Action Items</h2>
        {data.action_items.slice(0, REPORT_CONFIG.maxActionItems).map((item) => (
          <ActionItemRow
            key={item.id}
            item={item}
            onStatusChange={(status) => {
              const updatedItem = { ...item, status };
              onActionItemUpdate?.(updatedItem);
            }}
          />
        ))}
      </div>
    </div>
  );
};

export default RetrospectiveReport;
