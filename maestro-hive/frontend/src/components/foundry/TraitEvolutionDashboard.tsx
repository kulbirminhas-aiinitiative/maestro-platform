/**
 * TraitEvolutionDashboard - MD-3018
 *
 * Interactive dashboard for persona trait evolution and guidance.
 * Displays trait progress, decay warnings, recommendations, and career goals.
 *
 * Related EPIC: MD-3018 - Persona Trait Evolution & Guidance
 */

import React, { useState, useEffect, useCallback } from 'react';

// Types
interface TraitMetrics {
  practiceCount: number;
  successCount: number;
  failureCount: number;
  totalPracticeTimeHours: number;
  lastPractice: string | null;
  successRate: number;
}

interface Trait {
  id: string;
  name: string;
  description: string;
  category: string;
  level: number;
  minLevel: number;
  maxLevel: number;
  status: 'active' | 'inactive' | 'evolving' | 'decaying' | 'mastered';
  personaId: string | null;
  tags: string[];
  metrics: TraitMetrics;
  createdAt: string;
  updatedAt: string;
}

interface DecayResult {
  traitId: string;
  originalLevel: number;
  decayedLevel: number;
  decayAmount: number;
  decayRate: number;
  daysSincePractice: number;
  alertGenerated: boolean;
}

interface LearningResource {
  resourceId: string;
  title: string;
  resourceType: string;
  url?: string;
  estimatedHours: number;
  difficultyLevel: string;
}

interface Recommendation {
  recommendationId: string;
  traitId: string;
  traitName: string;
  recommendationType: string;
  priority: 'urgent' | 'high' | 'medium' | 'low' | 'exploratory';
  title: string;
  description: string;
  expectedLevelGain: number;
  estimatedHours: number;
  resources: LearningResource[];
  rationale: string;
  confidenceScore: number;
  accepted: boolean;
  completed: boolean;
}

interface CareerGoal {
  goalId: string;
  personaId: string;
  title: string;
  description: string;
  targetRole: string;
  targetTraits: Record<string, number>;
  deadline: string | null;
  progress: number;
}

interface EvolutionPlan {
  planId: string;
  personaId: string;
  title: string;
  recommendations: Recommendation[];
  totalEstimatedHours: number;
  expectedCompletionDate: string | null;
  careerGoal: CareerGoal | null;
}

interface TraitEvolutionDashboardProps {
  personaId: string;
  personaName?: string;
  apiEndpoint?: string;
  onTraitUpdated?: (trait: Trait) => void;
  onRecommendationAccepted?: (recommendation: Recommendation) => void;
}

// Priority colors
const PRIORITY_COLORS: Record<string, string> = {
  urgent: '#dc2626',
  high: '#ea580c',
  medium: '#2563eb',
  low: '#059669',
  exploratory: '#7c3aed',
};

const STATUS_COLORS: Record<string, string> = {
  active: '#059669',
  inactive: '#6b7280',
  evolving: '#2563eb',
  decaying: '#dc2626',
  mastered: '#7c3aed',
};

// Components
const TraitLevelBar: React.FC<{
  level: number;
  status: string;
  showPercentage?: boolean;
}> = ({ level, status, showPercentage = true }) => (
  <div className="trait-level-bar">
    <div className="level-track">
      <div
        className="level-fill"
        style={{
          width: `${level * 100}%`,
          backgroundColor: STATUS_COLORS[status] || '#3b82f6',
        }}
      />
    </div>
    {showPercentage && (
      <span className="level-text">{(level * 100).toFixed(0)}%</span>
    )}
  </div>
);

const TraitCard: React.FC<{
  trait: Trait;
  decayInfo?: DecayResult;
  onPractice: () => void;
}> = ({ trait, decayInfo, onPractice }) => (
  <div className={`trait-card status-${trait.status}`}>
    <div className="trait-header">
      <h4 className="trait-name">{trait.name}</h4>
      <span className={`status-badge ${trait.status}`}>
        {trait.status}
      </span>
    </div>

    <p className="trait-description">{trait.description}</p>

    <div className="trait-progress">
      <TraitLevelBar level={trait.level} status={trait.status} />
    </div>

    {decayInfo && decayInfo.alertGenerated && (
      <div className="decay-warning">
        <span className="warning-icon">⚠️</span>
        <span>
          Declining! -{(decayInfo.decayAmount * 100).toFixed(1)}% over{' '}
          {decayInfo.daysSincePractice} days
        </span>
      </div>
    )}

    <div className="trait-metrics">
      <div className="metric">
        <span className="metric-label">Practice</span>
        <span className="metric-value">{trait.metrics.practiceCount}x</span>
      </div>
      <div className="metric">
        <span className="metric-label">Success</span>
        <span className="metric-value">
          {(trait.metrics.successRate * 100).toFixed(0)}%
        </span>
      </div>
      <div className="metric">
        <span className="metric-label">Hours</span>
        <span className="metric-value">
          {trait.metrics.totalPracticeTimeHours.toFixed(1)}h
        </span>
      </div>
    </div>

    <div className="trait-tags">
      <span className="category-tag">{trait.category}</span>
      {trait.tags.slice(0, 2).map((tag) => (
        <span key={tag} className="tag">{tag}</span>
      ))}
    </div>

    <button className="practice-btn" onClick={onPractice}>
      Record Practice
    </button>
  </div>
);

const RecommendationCard: React.FC<{
  recommendation: Recommendation;
  onAccept: () => void;
  onComplete: () => void;
}> = ({ recommendation, onAccept, onComplete }) => (
  <div className={`recommendation-card priority-${recommendation.priority}`}>
    <div className="rec-header">
      <span
        className="priority-badge"
        style={{ backgroundColor: PRIORITY_COLORS[recommendation.priority] }}
      >
        {recommendation.priority.toUpperCase()}
      </span>
      <span className="rec-type">{recommendation.recommendationType}</span>
    </div>

    <h4 className="rec-title">{recommendation.title}</h4>
    <p className="rec-description">{recommendation.description}</p>

    <div className="rec-metrics">
      <div className="rec-metric">
        <span className="rec-metric-label">Expected Gain</span>
        <span className="rec-metric-value">
          +{(recommendation.expectedLevelGain * 100).toFixed(0)}%
        </span>
      </div>
      <div className="rec-metric">
        <span className="rec-metric-label">Est. Time</span>
        <span className="rec-metric-value">
          {recommendation.estimatedHours}h
        </span>
      </div>
      <div className="rec-metric">
        <span className="rec-metric-label">Confidence</span>
        <span className="rec-metric-value">
          {(recommendation.confidenceScore * 100).toFixed(0)}%
        </span>
      </div>
    </div>

    {recommendation.rationale && (
      <p className="rec-rationale">{recommendation.rationale}</p>
    )}

    {recommendation.resources.length > 0 && (
      <div className="rec-resources">
        <h5>Resources</h5>
        <ul>
          {recommendation.resources.map((resource) => (
            <li key={resource.resourceId}>
              <span className="resource-type">{resource.resourceType}</span>
              <span className="resource-title">{resource.title}</span>
              <span className="resource-time">{resource.estimatedHours}h</span>
            </li>
          ))}
        </ul>
      </div>
    )}

    <div className="rec-actions">
      {!recommendation.accepted && (
        <button className="accept-btn" onClick={onAccept}>
          Accept
        </button>
      )}
      {recommendation.accepted && !recommendation.completed && (
        <button className="complete-btn" onClick={onComplete}>
          Mark Complete
        </button>
      )}
      {recommendation.completed && (
        <span className="completed-badge">✓ Completed</span>
      )}
    </div>
  </div>
);

const CareerGoalPanel: React.FC<{
  goal: CareerGoal | null;
  traits: Trait[];
  onSetGoal: (goal: Partial<CareerGoal>) => void;
}> = ({ goal, traits, onSetGoal }) => {
  const [isEditing, setIsEditing] = useState(false);
  const [formData, setFormData] = useState({
    title: goal?.title || '',
    description: goal?.description || '',
    targetRole: goal?.targetRole || '',
  });

  const handleSubmit = () => {
    onSetGoal({
      ...formData,
      targetTraits: goal?.targetTraits || {},
    });
    setIsEditing(false);
  };

  if (isEditing) {
    return (
      <div className="career-goal-panel editing">
        <h3>Set Career Goal</h3>
        <div className="goal-form">
          <label>
            Goal Title
            <input
              type="text"
              value={formData.title}
              onChange={(e) =>
                setFormData({ ...formData, title: e.target.value })
              }
              placeholder="e.g., Become a Senior Architect"
            />
          </label>
          <label>
            Target Role
            <input
              type="text"
              value={formData.targetRole}
              onChange={(e) =>
                setFormData({ ...formData, targetRole: e.target.value })
              }
              placeholder="e.g., Senior Software Architect"
            />
          </label>
          <label>
            Description
            <textarea
              value={formData.description}
              onChange={(e) =>
                setFormData({ ...formData, description: e.target.value })
              }
              placeholder="Describe your career goal..."
            />
          </label>
          <div className="form-actions">
            <button className="cancel-btn" onClick={() => setIsEditing(false)}>
              Cancel
            </button>
            <button className="save-btn" onClick={handleSubmit}>
              Save Goal
            </button>
          </div>
        </div>
      </div>
    );
  }

  if (!goal) {
    return (
      <div className="career-goal-panel empty">
        <h3>Career Goal</h3>
        <p>Set a career goal to get personalized recommendations</p>
        <button className="set-goal-btn" onClick={() => setIsEditing(true)}>
          Set Career Goal
        </button>
      </div>
    );
  }

  return (
    <div className="career-goal-panel">
      <div className="goal-header">
        <h3>{goal.title}</h3>
        <button className="edit-btn" onClick={() => setIsEditing(true)}>
          Edit
        </button>
      </div>
      <p className="goal-role">Target Role: {goal.targetRole}</p>
      <p className="goal-description">{goal.description}</p>

      <div className="goal-progress">
        <div className="progress-label">
          <span>Progress</span>
          <span>{(goal.progress * 100).toFixed(0)}%</span>
        </div>
        <div className="progress-track">
          <div
            className="progress-fill"
            style={{ width: `${goal.progress * 100}%` }}
          />
        </div>
      </div>

      {Object.keys(goal.targetTraits).length > 0 && (
        <div className="target-traits">
          <h5>Target Traits</h5>
          {Object.entries(goal.targetTraits).map(([name, target]) => {
            const current = traits.find(
              (t) => t.name.toLowerCase() === name.toLowerCase()
            );
            return (
              <div key={name} className="target-trait">
                <span className="target-name">{name}</span>
                <div className="target-progress">
                  <div className="current-level">
                    {current ? (current.level * 100).toFixed(0) : 0}%
                  </div>
                  <div className="target-bar">
                    <div
                      className="current-fill"
                      style={{
                        width: `${(current?.level || 0) * 100}%`,
                      }}
                    />
                    <div
                      className="target-marker"
                      style={{ left: `${target * 100}%` }}
                    />
                  </div>
                  <div className="target-level">{(target * 100).toFixed(0)}%</div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};

const EvolutionPlanSummary: React.FC<{
  plan: EvolutionPlan | null;
}> = ({ plan }) => {
  if (!plan) return null;

  const completedCount = plan.recommendations.filter((r) => r.completed).length;
  const progressPercent = (completedCount / plan.recommendations.length) * 100;

  return (
    <div className="evolution-plan-summary">
      <h4>{plan.title}</h4>
      <div className="plan-stats">
        <div className="stat">
          <span className="stat-value">{plan.recommendations.length}</span>
          <span className="stat-label">Tasks</span>
        </div>
        <div className="stat">
          <span className="stat-value">{plan.totalEstimatedHours}h</span>
          <span className="stat-label">Est. Time</span>
        </div>
        <div className="stat">
          <span className="stat-value">{completedCount}</span>
          <span className="stat-label">Done</span>
        </div>
      </div>
      <div className="plan-progress">
        <div className="progress-track">
          <div
            className="progress-fill"
            style={{ width: `${progressPercent}%` }}
          />
        </div>
        <span className="progress-text">{progressPercent.toFixed(0)}% complete</span>
      </div>
    </div>
  );
};

// Main Component
export const TraitEvolutionDashboard: React.FC<TraitEvolutionDashboardProps> = ({
  personaId,
  personaName = 'Persona',
  apiEndpoint = '/api/evolution',
  onTraitUpdated,
  onRecommendationAccepted,
}) => {
  const [traits, setTraits] = useState<Trait[]>([]);
  const [decayResults, setDecayResults] = useState<Record<string, DecayResult>>({});
  const [recommendations, setRecommendations] = useState<Recommendation[]>([]);
  const [careerGoal, setCareerGoal] = useState<CareerGoal | null>(null);
  const [plan, setPlan] = useState<EvolutionPlan | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<'traits' | 'recommendations' | 'plan'>(
    'traits'
  );
  const [filter, setFilter] = useState<string>('all');
  const [error, setError] = useState<string | null>(null);

  // Fetch all data
  const fetchData = useCallback(async () => {
    setIsLoading(true);
    try {
      // Fetch traits
      const traitsRes = await fetch(`${apiEndpoint}/traits/${personaId}`);
      if (traitsRes.ok) {
        const traitsData = await traitsRes.json();
        setTraits(traitsData.traits || []);
        setDecayResults(traitsData.decayResults || {});
      }

      // Fetch recommendations
      const recsRes = await fetch(`${apiEndpoint}/recommendations/${personaId}`);
      if (recsRes.ok) {
        const recsData = await recsRes.json();
        setRecommendations(recsData.recommendations || []);
      }

      // Fetch career goal
      const goalRes = await fetch(`${apiEndpoint}/career-goal/${personaId}`);
      if (goalRes.ok) {
        const goalData = await goalRes.json();
        setCareerGoal(goalData.goal || null);
      }

      // Fetch plan
      const planRes = await fetch(`${apiEndpoint}/plan/${personaId}`);
      if (planRes.ok) {
        const planData = await planRes.json();
        setPlan(planData.plan || null);
      }
    } catch (err) {
      // Use mock data for development/demo
      setTraits(generateMockTraits(personaId));
      setRecommendations(generateMockRecommendations());
    } finally {
      setIsLoading(false);
    }
  }, [personaId, apiEndpoint]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  // Mock data generators for development
  const generateMockTraits = (pid: string): Trait[] => [
    {
      id: 'trait_1',
      name: 'Python',
      description: 'Python programming proficiency',
      category: 'technical',
      level: 0.85,
      minLevel: 0,
      maxLevel: 1,
      status: 'active',
      personaId: pid,
      tags: ['backend', 'scripting'],
      metrics: {
        practiceCount: 45,
        successCount: 40,
        failureCount: 5,
        totalPracticeTimeHours: 120,
        lastPractice: new Date().toISOString(),
        successRate: 0.89,
      },
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
    },
    {
      id: 'trait_2',
      name: 'System Design',
      description: 'Architecture and system design skills',
      category: 'technical',
      level: 0.65,
      minLevel: 0,
      maxLevel: 1,
      status: 'evolving',
      personaId: pid,
      tags: ['architecture', 'design'],
      metrics: {
        practiceCount: 20,
        successCount: 16,
        failureCount: 4,
        totalPracticeTimeHours: 50,
        lastPractice: new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString(),
        successRate: 0.8,
      },
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
    },
    {
      id: 'trait_3',
      name: 'Communication',
      description: 'Technical communication and documentation',
      category: 'soft_skill',
      level: 0.45,
      minLevel: 0,
      maxLevel: 1,
      status: 'decaying',
      personaId: pid,
      tags: ['writing', 'presentation'],
      metrics: {
        practiceCount: 10,
        successCount: 7,
        failureCount: 3,
        totalPracticeTimeHours: 25,
        lastPractice: new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString(),
        successRate: 0.7,
      },
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
    },
  ];

  const generateMockRecommendations = (): Recommendation[] => [
    {
      recommendationId: 'rec_1',
      traitId: 'trait_3',
      traitName: 'Communication',
      recommendationType: 'reinforce',
      priority: 'urgent',
      title: 'Reinforce: Communication',
      description: 'Your Communication skill is declining. Practice to maintain proficiency.',
      expectedLevelGain: 0.15,
      estimatedHours: 5,
      resources: [
        {
          resourceId: 'res_1',
          title: 'Technical Writing Workshop',
          resourceType: 'course',
          estimatedHours: 3,
          difficultyLevel: 'intermediate',
        },
      ],
      rationale: 'Skill has decayed by 8% over 30 days',
      confidenceScore: 0.9,
      accepted: false,
      completed: false,
    },
    {
      recommendationId: 'rec_2',
      traitId: 'trait_1',
      traitName: 'Python',
      recommendationType: 'advance',
      priority: 'medium',
      title: 'Advance: Python',
      description: "You're ready to advance your Python skill to expert level.",
      expectedLevelGain: 0.1,
      estimatedHours: 15,
      resources: [
        {
          resourceId: 'res_2',
          title: 'Advanced Python Patterns',
          resourceType: 'course',
          estimatedHours: 10,
          difficultyLevel: 'advanced',
        },
      ],
      rationale: 'Strong foundation in place, ready for advanced concepts',
      confidenceScore: 0.85,
      accepted: true,
      completed: false,
    },
  ];

  // Handlers
  const handlePractice = async (traitId: string) => {
    try {
      const response = await fetch(`${apiEndpoint}/practice`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          traitId,
          personaId,
          success: true,
          durationHours: 1,
        }),
      });

      if (response.ok) {
        const updatedTrait = await response.json();
        setTraits((prev) =>
          prev.map((t) => (t.id === traitId ? { ...t, ...updatedTrait } : t))
        );
        onTraitUpdated?.(updatedTrait);
      }
    } catch (err) {
      // Update locally for demo
      setTraits((prev) =>
        prev.map((t) =>
          t.id === traitId
            ? {
                ...t,
                level: Math.min(1, t.level + 0.02),
                metrics: {
                  ...t.metrics,
                  practiceCount: t.metrics.practiceCount + 1,
                  lastPractice: new Date().toISOString(),
                },
              }
            : t
        )
      );
    }
  };

  const handleAcceptRecommendation = async (recId: string) => {
    try {
      await fetch(`${apiEndpoint}/recommendations/${recId}/accept`, {
        method: 'POST',
      });
    } catch {
      // Continue with local update
    }
    setRecommendations((prev) =>
      prev.map((r) => (r.recommendationId === recId ? { ...r, accepted: true } : r))
    );
    const rec = recommendations.find((r) => r.recommendationId === recId);
    if (rec) onRecommendationAccepted?.(rec);
  };

  const handleCompleteRecommendation = async (recId: string) => {
    try {
      await fetch(`${apiEndpoint}/recommendations/${recId}/complete`, {
        method: 'POST',
      });
    } catch {
      // Continue with local update
    }
    setRecommendations((prev) =>
      prev.map((r) =>
        r.recommendationId === recId ? { ...r, completed: true } : r
      )
    );
  };

  const handleSetCareerGoal = async (goalData: Partial<CareerGoal>) => {
    try {
      const response = await fetch(`${apiEndpoint}/career-goal`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ...goalData, personaId }),
      });

      if (response.ok) {
        const newGoal = await response.json();
        setCareerGoal(newGoal);
      }
    } catch {
      // Set locally for demo
      setCareerGoal({
        goalId: `goal_${Date.now()}`,
        personaId,
        title: goalData.title || 'Career Goal',
        description: goalData.description || '',
        targetRole: goalData.targetRole || '',
        targetTraits: goalData.targetTraits || {},
        deadline: null,
        progress: 0,
      });
    }
  };

  // Filter traits
  const filteredTraits =
    filter === 'all'
      ? traits
      : traits.filter((t) => t.status === filter || t.category === filter);

  // Get decay warnings
  const decayWarnings = Object.values(decayResults).filter(
    (d) => d.alertGenerated
  );

  if (isLoading) {
    return (
      <div className="evolution-dashboard loading">
        <div className="loading-spinner" />
        <p>Loading evolution data...</p>
      </div>
    );
  }

  return (
    <div className="evolution-dashboard">
      <header className="dashboard-header">
        <div className="header-content">
          <h2>Trait Evolution Dashboard</h2>
          <p>Track and evolve {personaName}'s capabilities</p>
        </div>

        {decayWarnings.length > 0 && (
          <div className="decay-alerts">
            <span className="alert-icon">⚠️</span>
            <span>{decayWarnings.length} skill(s) declining</span>
          </div>
        )}
      </header>

      <div className="dashboard-content">
        <aside className="sidebar">
          <CareerGoalPanel
            goal={careerGoal}
            traits={traits}
            onSetGoal={handleSetCareerGoal}
          />

          <EvolutionPlanSummary plan={plan} />

          <div className="quick-stats">
            <h4>Overview</h4>
            <div className="stats-grid">
              <div className="stat-item">
                <span className="stat-number">{traits.length}</span>
                <span className="stat-label">Total Traits</span>
              </div>
              <div className="stat-item">
                <span className="stat-number">
                  {traits.filter((t) => t.status === 'mastered').length}
                </span>
                <span className="stat-label">Mastered</span>
              </div>
              <div className="stat-item">
                <span className="stat-number">
                  {traits.filter((t) => t.status === 'evolving').length}
                </span>
                <span className="stat-label">Evolving</span>
              </div>
              <div className="stat-item">
                <span className="stat-number">
                  {traits.filter((t) => t.status === 'decaying').length}
                </span>
                <span className="stat-label">Decaying</span>
              </div>
            </div>
          </div>
        </aside>

        <main className="main-content">
          <nav className="tab-nav">
            <button
              className={activeTab === 'traits' ? 'active' : ''}
              onClick={() => setActiveTab('traits')}
            >
              Traits ({traits.length})
            </button>
            <button
              className={activeTab === 'recommendations' ? 'active' : ''}
              onClick={() => setActiveTab('recommendations')}
            >
              Recommendations ({recommendations.filter((r) => !r.completed).length})
            </button>
            <button
              className={activeTab === 'plan' ? 'active' : ''}
              onClick={() => setActiveTab('plan')}
            >
              Evolution Plan
            </button>
          </nav>

          {activeTab === 'traits' && (
            <div className="traits-section">
              <div className="filter-bar">
                <select
                  value={filter}
                  onChange={(e) => setFilter(e.target.value)}
                >
                  <option value="all">All Traits</option>
                  <option value="active">Active</option>
                  <option value="evolving">Evolving</option>
                  <option value="decaying">Decaying</option>
                  <option value="mastered">Mastered</option>
                  <option value="technical">Technical</option>
                  <option value="soft_skill">Soft Skills</option>
                </select>
              </div>

              <div className="traits-grid">
                {filteredTraits.map((trait) => (
                  <TraitCard
                    key={trait.id}
                    trait={trait}
                    decayInfo={decayResults[trait.id]}
                    onPractice={() => handlePractice(trait.id)}
                  />
                ))}
              </div>

              {filteredTraits.length === 0 && (
                <div className="empty-state">
                  <p>No traits match the current filter</p>
                </div>
              )}
            </div>
          )}

          {activeTab === 'recommendations' && (
            <div className="recommendations-section">
              <div className="recommendations-list">
                {recommendations
                  .filter((r) => !r.completed)
                  .sort((a, b) => {
                    const priorityOrder = ['urgent', 'high', 'medium', 'low', 'exploratory'];
                    return (
                      priorityOrder.indexOf(a.priority) -
                      priorityOrder.indexOf(b.priority)
                    );
                  })
                  .map((rec) => (
                    <RecommendationCard
                      key={rec.recommendationId}
                      recommendation={rec}
                      onAccept={() => handleAcceptRecommendation(rec.recommendationId)}
                      onComplete={() =>
                        handleCompleteRecommendation(rec.recommendationId)
                      }
                    />
                  ))}
              </div>

              {recommendations.filter((r) => !r.completed).length === 0 && (
                <div className="empty-state">
                  <p>All recommendations completed! Great work!</p>
                </div>
              )}
            </div>
          )}

          {activeTab === 'plan' && (
            <div className="plan-section">
              {plan ? (
                <div className="plan-details">
                  <h3>{plan.title}</h3>
                  <div className="plan-overview">
                    <p>
                      {plan.recommendations.filter((r) => r.completed).length} of{' '}
                      {plan.recommendations.length} tasks completed
                    </p>
                    <p>
                      Estimated completion:{' '}
                      {plan.expectedCompletionDate
                        ? new Date(plan.expectedCompletionDate).toLocaleDateString()
                        : 'TBD'}
                    </p>
                  </div>

                  <div className="plan-tasks">
                    {plan.recommendations.map((rec, idx) => (
                      <div
                        key={rec.recommendationId}
                        className={`plan-task ${rec.completed ? 'completed' : ''}`}
                      >
                        <span className="task-number">{idx + 1}</span>
                        <div className="task-content">
                          <h5>{rec.title}</h5>
                          <p>{rec.description}</p>
                          <span className="task-time">{rec.estimatedHours}h</span>
                        </div>
                        {rec.completed && <span className="check-mark">✓</span>}
                      </div>
                    ))}
                  </div>
                </div>
              ) : (
                <div className="empty-state">
                  <p>No evolution plan created yet</p>
                  <button className="create-plan-btn">Create Plan</button>
                </div>
              )}
            </div>
          )}
        </main>
      </div>

      {error && <div className="error-toast">{error}</div>}

      <style>{`
        .evolution-dashboard {
          font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
          max-width: 1400px;
          margin: 0 auto;
          padding: 24px;
          background: #f9fafb;
          min-height: 100vh;
        }

        .evolution-dashboard.loading {
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          min-height: 400px;
        }

        .loading-spinner {
          width: 40px;
          height: 40px;
          border: 4px solid #e5e7eb;
          border-top-color: #3b82f6;
          border-radius: 50%;
          animation: spin 1s linear infinite;
        }

        @keyframes spin {
          to { transform: rotate(360deg); }
        }

        .dashboard-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 24px;
        }

        .header-content h2 {
          font-size: 28px;
          font-weight: 600;
          color: #1f2937;
          margin: 0 0 4px 0;
        }

        .header-content p {
          color: #6b7280;
          margin: 0;
        }

        .decay-alerts {
          display: flex;
          align-items: center;
          gap: 8px;
          padding: 10px 16px;
          background: #fef2f2;
          color: #dc2626;
          border-radius: 8px;
          font-weight: 500;
        }

        .dashboard-content {
          display: grid;
          grid-template-columns: 320px 1fr;
          gap: 24px;
        }

        .sidebar {
          display: flex;
          flex-direction: column;
          gap: 20px;
        }

        .career-goal-panel {
          background: white;
          border-radius: 12px;
          padding: 20px;
          box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }

        .career-goal-panel h3 {
          font-size: 16px;
          font-weight: 600;
          color: #1f2937;
          margin: 0 0 12px 0;
        }

        .career-goal-panel.empty {
          text-align: center;
        }

        .career-goal-panel.empty p {
          color: #6b7280;
          margin-bottom: 16px;
        }

        .set-goal-btn, .create-plan-btn {
          padding: 10px 20px;
          background: #3b82f6;
          color: white;
          border: none;
          border-radius: 6px;
          font-weight: 500;
          cursor: pointer;
        }

        .set-goal-btn:hover, .create-plan-btn:hover {
          background: #2563eb;
        }

        .goal-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 8px;
        }

        .goal-header h3 {
          margin: 0;
        }

        .edit-btn {
          padding: 4px 12px;
          background: #f3f4f6;
          border: none;
          border-radius: 4px;
          font-size: 13px;
          cursor: pointer;
        }

        .goal-role {
          font-size: 14px;
          color: #6b7280;
          margin: 0 0 8px 0;
        }

        .goal-description {
          font-size: 14px;
          color: #4b5563;
          margin: 0 0 16px 0;
        }

        .goal-progress, .plan-progress {
          margin-bottom: 16px;
        }

        .progress-label {
          display: flex;
          justify-content: space-between;
          font-size: 13px;
          color: #6b7280;
          margin-bottom: 6px;
        }

        .progress-track {
          height: 8px;
          background: #e5e7eb;
          border-radius: 4px;
          overflow: hidden;
        }

        .progress-fill {
          height: 100%;
          background: #3b82f6;
          border-radius: 4px;
          transition: width 0.3s ease;
        }

        .progress-text {
          font-size: 13px;
          color: #6b7280;
          margin-top: 4px;
          display: block;
        }

        .goal-form label {
          display: block;
          margin-bottom: 12px;
          font-size: 14px;
          color: #374151;
        }

        .goal-form input, .goal-form textarea {
          width: 100%;
          margin-top: 6px;
          padding: 10px;
          border: 1px solid #e5e7eb;
          border-radius: 6px;
          font-size: 14px;
          box-sizing: border-box;
        }

        .goal-form textarea {
          min-height: 80px;
          resize: vertical;
        }

        .form-actions {
          display: flex;
          gap: 8px;
          margin-top: 16px;
        }

        .cancel-btn {
          flex: 1;
          padding: 10px;
          background: #f3f4f6;
          border: none;
          border-radius: 6px;
          cursor: pointer;
        }

        .save-btn {
          flex: 1;
          padding: 10px;
          background: #3b82f6;
          color: white;
          border: none;
          border-radius: 6px;
          cursor: pointer;
        }

        .target-traits h5 {
          font-size: 13px;
          font-weight: 600;
          color: #374151;
          margin: 0 0 10px 0;
        }

        .target-trait {
          margin-bottom: 8px;
        }

        .target-name {
          font-size: 13px;
          color: #4b5563;
          display: block;
          margin-bottom: 4px;
        }

        .target-progress {
          display: flex;
          align-items: center;
          gap: 8px;
        }

        .current-level, .target-level {
          font-size: 12px;
          color: #6b7280;
          width: 32px;
        }

        .target-bar {
          flex: 1;
          height: 6px;
          background: #e5e7eb;
          border-radius: 3px;
          position: relative;
        }

        .current-fill {
          position: absolute;
          height: 100%;
          background: #3b82f6;
          border-radius: 3px;
        }

        .target-marker {
          position: absolute;
          width: 2px;
          height: 12px;
          background: #059669;
          top: -3px;
        }

        .evolution-plan-summary {
          background: white;
          border-radius: 12px;
          padding: 16px;
          box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }

        .evolution-plan-summary h4 {
          font-size: 14px;
          font-weight: 600;
          color: #1f2937;
          margin: 0 0 12px 0;
        }

        .plan-stats {
          display: flex;
          gap: 12px;
          margin-bottom: 12px;
        }

        .plan-stats .stat {
          text-align: center;
        }

        .plan-stats .stat-value {
          font-size: 18px;
          font-weight: 600;
          color: #1f2937;
          display: block;
        }

        .plan-stats .stat-label {
          font-size: 11px;
          color: #6b7280;
        }

        .quick-stats {
          background: white;
          border-radius: 12px;
          padding: 16px;
          box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }

        .quick-stats h4 {
          font-size: 14px;
          font-weight: 600;
          color: #1f2937;
          margin: 0 0 12px 0;
        }

        .stats-grid {
          display: grid;
          grid-template-columns: 1fr 1fr;
          gap: 12px;
        }

        .stat-item {
          text-align: center;
          padding: 12px;
          background: #f9fafb;
          border-radius: 8px;
        }

        .stat-number {
          font-size: 24px;
          font-weight: 600;
          color: #1f2937;
          display: block;
        }

        .stat-label {
          font-size: 12px;
          color: #6b7280;
        }

        .main-content {
          min-width: 0;
        }

        .tab-nav {
          display: flex;
          gap: 4px;
          background: white;
          padding: 4px;
          border-radius: 10px;
          margin-bottom: 20px;
          box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }

        .tab-nav button {
          flex: 1;
          padding: 12px 16px;
          background: transparent;
          border: none;
          border-radius: 8px;
          font-size: 14px;
          font-weight: 500;
          color: #6b7280;
          cursor: pointer;
          transition: all 0.2s;
        }

        .tab-nav button:hover {
          background: #f3f4f6;
        }

        .tab-nav button.active {
          background: #3b82f6;
          color: white;
        }

        .filter-bar {
          margin-bottom: 16px;
        }

        .filter-bar select {
          padding: 10px 16px;
          border: 1px solid #e5e7eb;
          border-radius: 8px;
          font-size: 14px;
          background: white;
          cursor: pointer;
        }

        .traits-grid {
          display: grid;
          grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
          gap: 16px;
        }

        .trait-card {
          background: white;
          border-radius: 12px;
          padding: 20px;
          box-shadow: 0 1px 3px rgba(0,0,0,0.1);
          border-left: 4px solid #e5e7eb;
        }

        .trait-card.status-active { border-left-color: #059669; }
        .trait-card.status-evolving { border-left-color: #2563eb; }
        .trait-card.status-decaying { border-left-color: #dc2626; }
        .trait-card.status-mastered { border-left-color: #7c3aed; }

        .trait-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 8px;
        }

        .trait-name {
          font-size: 16px;
          font-weight: 600;
          color: #1f2937;
          margin: 0;
        }

        .status-badge {
          font-size: 11px;
          padding: 4px 8px;
          border-radius: 4px;
          font-weight: 500;
          text-transform: uppercase;
        }

        .status-badge.active { background: #ecfdf5; color: #059669; }
        .status-badge.evolving { background: #eff6ff; color: #2563eb; }
        .status-badge.decaying { background: #fef2f2; color: #dc2626; }
        .status-badge.mastered { background: #f5f3ff; color: #7c3aed; }
        .status-badge.inactive { background: #f3f4f6; color: #6b7280; }

        .trait-description {
          font-size: 13px;
          color: #6b7280;
          margin: 0 0 12px 0;
        }

        .trait-progress {
          margin-bottom: 12px;
        }

        .trait-level-bar {
          display: flex;
          align-items: center;
          gap: 12px;
        }

        .level-track {
          flex: 1;
          height: 8px;
          background: #e5e7eb;
          border-radius: 4px;
          overflow: hidden;
        }

        .level-fill {
          height: 100%;
          border-radius: 4px;
          transition: width 0.3s ease;
        }

        .level-text {
          font-size: 14px;
          font-weight: 600;
          color: #1f2937;
          min-width: 40px;
        }

        .decay-warning {
          display: flex;
          align-items: center;
          gap: 8px;
          padding: 8px 12px;
          background: #fef2f2;
          border-radius: 6px;
          font-size: 13px;
          color: #dc2626;
          margin-bottom: 12px;
        }

        .trait-metrics {
          display: flex;
          gap: 16px;
          margin-bottom: 12px;
        }

        .metric {
          text-align: center;
        }

        .metric-label {
          font-size: 11px;
          color: #6b7280;
          display: block;
        }

        .metric-value {
          font-size: 14px;
          font-weight: 600;
          color: #1f2937;
        }

        .trait-tags {
          display: flex;
          flex-wrap: wrap;
          gap: 6px;
          margin-bottom: 12px;
        }

        .category-tag {
          font-size: 11px;
          padding: 4px 8px;
          background: #dbeafe;
          color: #1d4ed8;
          border-radius: 4px;
        }

        .tag {
          font-size: 11px;
          padding: 4px 8px;
          background: #f3f4f6;
          color: #6b7280;
          border-radius: 4px;
        }

        .practice-btn {
          width: 100%;
          padding: 10px;
          background: #f3f4f6;
          border: none;
          border-radius: 6px;
          font-size: 13px;
          font-weight: 500;
          color: #374151;
          cursor: pointer;
          transition: background 0.2s;
        }

        .practice-btn:hover {
          background: #e5e7eb;
        }

        .recommendations-list {
          display: flex;
          flex-direction: column;
          gap: 16px;
        }

        .recommendation-card {
          background: white;
          border-radius: 12px;
          padding: 20px;
          box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }

        .rec-header {
          display: flex;
          align-items: center;
          gap: 8px;
          margin-bottom: 12px;
        }

        .priority-badge {
          font-size: 10px;
          padding: 4px 8px;
          color: white;
          border-radius: 4px;
          font-weight: 600;
        }

        .rec-type {
          font-size: 12px;
          color: #6b7280;
          text-transform: capitalize;
        }

        .rec-title {
          font-size: 16px;
          font-weight: 600;
          color: #1f2937;
          margin: 0 0 8px 0;
        }

        .rec-description {
          font-size: 14px;
          color: #4b5563;
          margin: 0 0 16px 0;
        }

        .rec-metrics {
          display: flex;
          gap: 20px;
          margin-bottom: 12px;
          padding: 12px;
          background: #f9fafb;
          border-radius: 8px;
        }

        .rec-metric {
          text-align: center;
        }

        .rec-metric-label {
          font-size: 11px;
          color: #6b7280;
          display: block;
        }

        .rec-metric-value {
          font-size: 16px;
          font-weight: 600;
          color: #1f2937;
        }

        .rec-rationale {
          font-size: 13px;
          color: #6b7280;
          font-style: italic;
          margin: 0 0 12px 0;
        }

        .rec-resources {
          margin-bottom: 16px;
        }

        .rec-resources h5 {
          font-size: 13px;
          font-weight: 600;
          color: #374151;
          margin: 0 0 8px 0;
        }

        .rec-resources ul {
          list-style: none;
          padding: 0;
          margin: 0;
        }

        .rec-resources li {
          display: flex;
          align-items: center;
          gap: 8px;
          padding: 8px;
          background: #f9fafb;
          border-radius: 6px;
          margin-bottom: 4px;
        }

        .resource-type {
          font-size: 11px;
          padding: 2px 6px;
          background: #e5e7eb;
          border-radius: 3px;
          color: #4b5563;
        }

        .resource-title {
          flex: 1;
          font-size: 13px;
          color: #1f2937;
        }

        .resource-time {
          font-size: 12px;
          color: #6b7280;
        }

        .rec-actions {
          display: flex;
          gap: 8px;
        }

        .accept-btn {
          flex: 1;
          padding: 10px;
          background: #3b82f6;
          color: white;
          border: none;
          border-radius: 6px;
          font-weight: 500;
          cursor: pointer;
        }

        .accept-btn:hover {
          background: #2563eb;
        }

        .complete-btn {
          flex: 1;
          padding: 10px;
          background: #059669;
          color: white;
          border: none;
          border-radius: 6px;
          font-weight: 500;
          cursor: pointer;
        }

        .complete-btn:hover {
          background: #047857;
        }

        .completed-badge {
          color: #059669;
          font-weight: 500;
        }

        .plan-section {
          background: white;
          border-radius: 12px;
          padding: 24px;
          box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }

        .plan-details h3 {
          font-size: 20px;
          font-weight: 600;
          color: #1f2937;
          margin: 0 0 16px 0;
        }

        .plan-overview {
          margin-bottom: 24px;
          padding: 16px;
          background: #f9fafb;
          border-radius: 8px;
        }

        .plan-overview p {
          margin: 0 0 8px 0;
          font-size: 14px;
          color: #4b5563;
        }

        .plan-tasks {
          display: flex;
          flex-direction: column;
          gap: 12px;
        }

        .plan-task {
          display: flex;
          align-items: flex-start;
          gap: 12px;
          padding: 16px;
          background: #f9fafb;
          border-radius: 8px;
          transition: all 0.2s;
        }

        .plan-task.completed {
          background: #ecfdf5;
        }

        .task-number {
          width: 28px;
          height: 28px;
          background: #e5e7eb;
          border-radius: 50%;
          display: flex;
          align-items: center;
          justify-content: center;
          font-size: 13px;
          font-weight: 600;
          color: #4b5563;
          flex-shrink: 0;
        }

        .plan-task.completed .task-number {
          background: #059669;
          color: white;
        }

        .task-content {
          flex: 1;
        }

        .task-content h5 {
          font-size: 14px;
          font-weight: 600;
          color: #1f2937;
          margin: 0 0 4px 0;
        }

        .task-content p {
          font-size: 13px;
          color: #6b7280;
          margin: 0;
        }

        .task-time {
          font-size: 12px;
          color: #6b7280;
          margin-top: 4px;
          display: block;
        }

        .check-mark {
          font-size: 18px;
          color: #059669;
        }

        .empty-state {
          text-align: center;
          padding: 48px;
          color: #6b7280;
        }

        .error-toast {
          position: fixed;
          bottom: 24px;
          right: 24px;
          padding: 16px 24px;
          background: #dc2626;
          color: white;
          border-radius: 8px;
          box-shadow: 0 4px 12px rgba(0,0,0,0.2);
        }

        @media (max-width: 1024px) {
          .dashboard-content {
            grid-template-columns: 1fr;
          }

          .sidebar {
            order: 2;
          }

          .main-content {
            order: 1;
          }
        }

        @media (max-width: 640px) {
          .traits-grid {
            grid-template-columns: 1fr;
          }

          .tab-nav {
            flex-direction: column;
          }
        }
      `}</style>
    </div>
  );
};

export default TraitEvolutionDashboard;
