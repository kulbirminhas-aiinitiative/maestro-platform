/**
 * Workflow Optimization Dashboard - AC-5 Implementation
 *
 * React component for monitoring and optimizing workflows.
 * Provides real-time visibility into workflow performance, best practices
 * compliance, and error prevention recommendations.
 *
 * Part of EPIC MD-2961: Workflow Optimization & Standardization
 */

import React, { useState, useEffect, useCallback, useMemo } from 'react';

// Types
interface WorkflowMetrics {
  totalWorkflows: number;
  activeWorkflows: number;
  completedToday: number;
  failedToday: number;
  averageExecutionTime: number;
  successRate: number;
}

interface ValidationResult {
  ruleId: string;
  ruleName: string;
  severity: 'error' | 'warning' | 'info';
  passed: boolean;
  message: string;
  recommendation?: string;
}

interface BestPracticeScore {
  category: string;
  score: number;
  maxScore: number;
  violations: number;
  recommendations: string[];
}

interface ErrorPrevention {
  patternId: string;
  patternName: string;
  severity: 'critical' | 'high' | 'medium' | 'low';
  confidence: number;
  indicators: string[];
  preventionStrategies: string[];
}

interface WorkflowPattern {
  id: string;
  name: string;
  category: string;
  usageCount: number;
  successRate: number;
  averageExecutionTime: number;
}

interface DashboardData {
  metrics: WorkflowMetrics;
  validationResults: ValidationResult[];
  bestPracticeScores: BestPracticeScore[];
  errorPreventions: ErrorPrevention[];
  topPatterns: WorkflowPattern[];
  lastUpdated: string;
}

// Severity badge component
const SeverityBadge: React.FC<{ severity: string }> = ({ severity }) => {
  const colors: Record<string, string> = {
    critical: 'bg-red-600 text-white',
    error: 'bg-red-500 text-white',
    high: 'bg-orange-500 text-white',
    warning: 'bg-yellow-500 text-black',
    medium: 'bg-yellow-400 text-black',
    info: 'bg-blue-500 text-white',
    low: 'bg-gray-400 text-white'
  };

  return (
    <span className={`px-2 py-1 rounded text-xs font-medium ${colors[severity] || 'bg-gray-300'}`}>
      {severity.toUpperCase()}
    </span>
  );
};

// Progress bar component
const ProgressBar: React.FC<{ value: number; max: number; color?: string }> = ({
  value,
  max,
  color = 'bg-blue-500'
}) => {
  const percentage = max > 0 ? (value / max) * 100 : 0;

  return (
    <div className="w-full bg-gray-200 rounded-full h-2.5">
      <div
        className={`h-2.5 rounded-full ${color}`}
        style={{ width: `${Math.min(percentage, 100)}%` }}
      />
    </div>
  );
};

// Metric card component
const MetricCard: React.FC<{
  title: string;
  value: string | number;
  subtitle?: string;
  trend?: 'up' | 'down' | 'neutral';
  trendValue?: string;
}> = ({ title, value, subtitle, trend, trendValue }) => {
  const trendColors = {
    up: 'text-green-500',
    down: 'text-red-500',
    neutral: 'text-gray-500'
  };

  const trendIcons = {
    up: '↑',
    down: '↓',
    neutral: '→'
  };

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <h3 className="text-sm font-medium text-gray-500">{title}</h3>
      <div className="mt-2 flex items-baseline">
        <p className="text-3xl font-semibold text-gray-900">{value}</p>
        {trend && trendValue && (
          <span className={`ml-2 text-sm ${trendColors[trend]}`}>
            {trendIcons[trend]} {trendValue}
          </span>
        )}
      </div>
      {subtitle && <p className="mt-1 text-sm text-gray-500">{subtitle}</p>}
    </div>
  );
};

// Validation results table
const ValidationResultsTable: React.FC<{ results: ValidationResult[] }> = ({ results }) => {
  const [filter, setFilter] = useState<'all' | 'failed' | 'passed'>('all');

  const filteredResults = useMemo(() => {
    if (filter === 'all') return results;
    if (filter === 'failed') return results.filter(r => !r.passed);
    return results.filter(r => r.passed);
  }, [results, filter]);

  return (
    <div className="bg-white rounded-lg shadow">
      <div className="px-6 py-4 border-b flex justify-between items-center">
        <h2 className="text-lg font-semibold">Validation Results</h2>
        <div className="flex gap-2">
          {(['all', 'failed', 'passed'] as const).map(f => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              className={`px-3 py-1 rounded text-sm ${
                filter === f
                  ? 'bg-blue-500 text-white'
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
              }`}
            >
              {f.charAt(0).toUpperCase() + f.slice(1)}
            </button>
          ))}
        </div>
      </div>
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Rule</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Severity</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Message</th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {filteredResults.map((result, index) => (
              <tr key={index} className={!result.passed ? 'bg-red-50' : ''}>
                <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                  {result.ruleName}
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <SeverityBadge severity={result.severity} />
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <span className={`px-2 py-1 rounded text-xs font-medium ${
                    result.passed
                      ? 'bg-green-100 text-green-800'
                      : 'bg-red-100 text-red-800'
                  }`}>
                    {result.passed ? 'PASSED' : 'FAILED'}
                  </span>
                </td>
                <td className="px-6 py-4 text-sm text-gray-500">
                  {result.message}
                  {result.recommendation && (
                    <p className="mt-1 text-xs text-blue-600">{result.recommendation}</p>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

// Best practices score card
const BestPracticesCard: React.FC<{ scores: BestPracticeScore[] }> = ({ scores }) => {
  const overallScore = useMemo(() => {
    const total = scores.reduce((acc, s) => acc + s.score, 0);
    const max = scores.reduce((acc, s) => acc + s.maxScore, 0);
    return max > 0 ? Math.round((total / max) * 100) : 0;
  }, [scores]);

  const getScoreColor = (percentage: number) => {
    if (percentage >= 90) return 'text-green-500';
    if (percentage >= 70) return 'text-yellow-500';
    return 'text-red-500';
  };

  return (
    <div className="bg-white rounded-lg shadow">
      <div className="px-6 py-4 border-b">
        <h2 className="text-lg font-semibold">Best Practices Compliance</h2>
      </div>
      <div className="p-6">
        <div className="text-center mb-6">
          <span className={`text-5xl font-bold ${getScoreColor(overallScore)}`}>
            {overallScore}%
          </span>
          <p className="text-gray-500 mt-1">Overall Compliance Score</p>
        </div>
        <div className="space-y-4">
          {scores.map((score, index) => (
            <div key={index}>
              <div className="flex justify-between mb-1">
                <span className="text-sm font-medium text-gray-700">{score.category}</span>
                <span className="text-sm text-gray-500">
                  {score.score}/{score.maxScore}
                </span>
              </div>
              <ProgressBar
                value={score.score}
                max={score.maxScore}
                color={score.score / score.maxScore >= 0.7 ? 'bg-green-500' : 'bg-yellow-500'}
              />
              {score.violations > 0 && (
                <p className="text-xs text-red-500 mt-1">
                  {score.violations} violation{score.violations > 1 ? 's' : ''}
                </p>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

// Error prevention alerts
const ErrorPreventionAlerts: React.FC<{ preventions: ErrorPrevention[] }> = ({ preventions }) => {
  const [expanded, setExpanded] = useState<string | null>(null);

  const sortedPreventions = useMemo(() => {
    const severityOrder = { critical: 0, high: 1, medium: 2, low: 3 };
    return [...preventions].sort((a, b) =>
      severityOrder[a.severity] - severityOrder[b.severity] ||
      b.confidence - a.confidence
    );
  }, [preventions]);

  return (
    <div className="bg-white rounded-lg shadow">
      <div className="px-6 py-4 border-b">
        <h2 className="text-lg font-semibold">Error Prevention Alerts</h2>
        <p className="text-sm text-gray-500 mt-1">
          RAG-based error detection and prevention recommendations
        </p>
      </div>
      <div className="divide-y divide-gray-200">
        {sortedPreventions.length === 0 ? (
          <div className="p-6 text-center text-gray-500">
            No potential errors detected
          </div>
        ) : (
          sortedPreventions.map((prevention) => (
            <div key={prevention.patternId} className="p-4">
              <div
                className="flex items-center justify-between cursor-pointer"
                onClick={() => setExpanded(
                  expanded === prevention.patternId ? null : prevention.patternId
                )}
              >
                <div className="flex items-center gap-3">
                  <SeverityBadge severity={prevention.severity} />
                  <span className="font-medium">{prevention.patternName}</span>
                </div>
                <div className="flex items-center gap-4">
                  <span className="text-sm text-gray-500">
                    Confidence: {Math.round(prevention.confidence * 100)}%
                  </span>
                  <span className="text-gray-400">
                    {expanded === prevention.patternId ? '▼' : '▶'}
                  </span>
                </div>
              </div>
              {expanded === prevention.patternId && (
                <div className="mt-4 pl-4 border-l-2 border-gray-200">
                  <div className="mb-3">
                    <h4 className="text-sm font-medium text-gray-700">Indicators</h4>
                    <ul className="mt-1 text-sm text-gray-600 list-disc list-inside">
                      {prevention.indicators.map((indicator, i) => (
                        <li key={i}>{indicator}</li>
                      ))}
                    </ul>
                  </div>
                  <div>
                    <h4 className="text-sm font-medium text-gray-700">Prevention Strategies</h4>
                    <ul className="mt-1 text-sm text-blue-600 list-disc list-inside">
                      {prevention.preventionStrategies.map((strategy, i) => (
                        <li key={i}>{strategy}</li>
                      ))}
                    </ul>
                  </div>
                </div>
              )}
            </div>
          ))
        )}
      </div>
    </div>
  );
};

// Top patterns chart
const TopPatternsChart: React.FC<{ patterns: WorkflowPattern[] }> = ({ patterns }) => {
  const maxUsage = useMemo(() =>
    Math.max(...patterns.map(p => p.usageCount), 1),
    [patterns]
  );

  return (
    <div className="bg-white rounded-lg shadow">
      <div className="px-6 py-4 border-b">
        <h2 className="text-lg font-semibold">Top Workflow Patterns</h2>
      </div>
      <div className="p-6">
        <div className="space-y-4">
          {patterns.map((pattern) => (
            <div key={pattern.id} className="flex items-center gap-4">
              <div className="w-32 truncate text-sm font-medium" title={pattern.name}>
                {pattern.name}
              </div>
              <div className="flex-1">
                <ProgressBar
                  value={pattern.usageCount}
                  max={maxUsage}
                  color={pattern.successRate >= 0.95 ? 'bg-green-500' : 'bg-blue-500'}
                />
              </div>
              <div className="w-20 text-right text-sm text-gray-500">
                {pattern.usageCount} uses
              </div>
              <div className="w-16 text-right">
                <span className={`text-sm font-medium ${
                  pattern.successRate >= 0.95 ? 'text-green-500' :
                  pattern.successRate >= 0.8 ? 'text-yellow-500' : 'text-red-500'
                }`}>
                  {Math.round(pattern.successRate * 100)}%
                </span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

// Main Dashboard Component
export const OptimizationDashboard: React.FC<{
  apiEndpoint?: string;
  refreshInterval?: number;
}> = ({
  apiEndpoint = '/api/workflow/dashboard',
  refreshInterval = 30000
}) => {
  const [data, setData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastRefresh, setLastRefresh] = useState<Date>(new Date());

  const fetchData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      // In production, this would be an actual API call
      // const response = await fetch(apiEndpoint);
      // const data = await response.json();

      // Mock data for demonstration
      const mockData: DashboardData = {
        metrics: {
          totalWorkflows: 1247,
          activeWorkflows: 23,
          completedToday: 156,
          failedToday: 3,
          averageExecutionTime: 2340,
          successRate: 0.981
        },
        validationResults: [
          {
            ruleId: 'timeout-required',
            ruleName: 'Timeout Required',
            severity: 'error',
            passed: true,
            message: 'All workflows have timeout configured'
          },
          {
            ruleId: 'retry-config',
            ruleName: 'Retry Configuration',
            severity: 'warning',
            passed: false,
            message: '3 workflows missing retry configuration',
            recommendation: 'Add retry configuration with exponential backoff'
          },
          {
            ruleId: 'error-handling',
            ruleName: 'Error Handling',
            severity: 'error',
            passed: true,
            message: 'All workflows have proper error handling'
          },
          {
            ruleId: 'logging',
            ruleName: 'Logging Standards',
            severity: 'info',
            passed: true,
            message: 'All workflows follow logging standards'
          },
          {
            ruleId: 'circuit-breaker',
            ruleName: 'Circuit Breaker',
            severity: 'warning',
            passed: false,
            message: '5 workflows with external calls missing circuit breaker',
            recommendation: 'Implement circuit breaker pattern for external service calls'
          }
        ],
        bestPracticeScores: [
          { category: 'Error Handling', score: 18, maxScore: 20, violations: 2, recommendations: [] },
          { category: 'Resilience', score: 15, maxScore: 20, violations: 5, recommendations: [] },
          { category: 'Performance', score: 17, maxScore: 20, violations: 3, recommendations: [] },
          { category: 'Security', score: 20, maxScore: 20, violations: 0, recommendations: [] },
          { category: 'Observability', score: 16, maxScore: 20, violations: 4, recommendations: [] }
        ],
        errorPreventions: [
          {
            patternId: 'timeout-cascade',
            patternName: 'Timeout Cascade Failure',
            severity: 'high',
            confidence: 0.75,
            indicators: ['Multiple services with same timeout values', 'No timeout budget allocation'],
            preventionStrategies: ['Implement timeout budgets', 'Use circuit breakers', 'Add bulkhead isolation']
          },
          {
            patternId: 'retry-storm',
            patternName: 'Retry Storm Risk',
            severity: 'medium',
            confidence: 0.62,
            indicators: ['Synchronized retry timing', 'Missing jitter in backoff'],
            preventionStrategies: ['Add jitter to retry delays', 'Implement exponential backoff', 'Limit total retry attempts']
          }
        ],
        topPatterns: [
          { id: 'retry-exp-backoff', name: 'Retry w/ Exp Backoff', category: 'Resilience', usageCount: 342, successRate: 0.98, averageExecutionTime: 1200 },
          { id: 'circuit-breaker', name: 'Circuit Breaker', category: 'Resilience', usageCount: 287, successRate: 0.99, averageExecutionTime: 850 },
          { id: 'timeout-wrapper', name: 'Timeout Wrapper', category: 'Resilience', usageCount: 256, successRate: 0.97, averageExecutionTime: 1500 },
          { id: 'rate-limiter', name: 'Rate Limiter', category: 'Performance', usageCount: 198, successRate: 0.995, averageExecutionTime: 50 },
          { id: 'bulkhead', name: 'Bulkhead', category: 'Resilience', usageCount: 145, successRate: 0.96, averageExecutionTime: 2100 }
        ],
        lastUpdated: new Date().toISOString()
      };

      setData(mockData);
      setLastRefresh(new Date());
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch dashboard data');
    } finally {
      setLoading(false);
    }
  }, [apiEndpoint]);

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, refreshInterval);
    return () => clearInterval(interval);
  }, [fetchData, refreshInterval]);

  if (loading && !data) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-4">
        <h3 className="text-red-800 font-medium">Error loading dashboard</h3>
        <p className="text-red-600 mt-1">{error}</p>
        <button
          onClick={fetchData}
          className="mt-3 px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700"
        >
          Retry
        </button>
      </div>
    );
  }

  if (!data) return null;

  return (
    <div className="space-y-6 p-6 bg-gray-100 min-h-screen">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">
            Workflow Optimization Dashboard
          </h1>
          <p className="text-gray-500 mt-1">
            Monitor and optimize workflow performance and compliance
          </p>
        </div>
        <div className="flex items-center gap-4">
          <span className="text-sm text-gray-500">
            Last updated: {lastRefresh.toLocaleTimeString()}
          </span>
          <button
            onClick={fetchData}
            disabled={loading}
            className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600 disabled:opacity-50"
          >
            {loading ? 'Refreshing...' : 'Refresh'}
          </button>
        </div>
      </div>

      {/* Metrics Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard
          title="Total Workflows"
          value={data.metrics.totalWorkflows.toLocaleString()}
          subtitle={`${data.metrics.activeWorkflows} currently active`}
        />
        <MetricCard
          title="Success Rate"
          value={`${(data.metrics.successRate * 100).toFixed(1)}%`}
          subtitle="Last 24 hours"
          trend={data.metrics.successRate >= 0.95 ? 'up' : 'down'}
          trendValue={data.metrics.successRate >= 0.95 ? 'On target' : 'Below target'}
        />
        <MetricCard
          title="Completed Today"
          value={data.metrics.completedToday}
          subtitle={`${data.metrics.failedToday} failed`}
          trend={data.metrics.failedToday === 0 ? 'up' : 'neutral'}
        />
        <MetricCard
          title="Avg Execution Time"
          value={`${(data.metrics.averageExecutionTime / 1000).toFixed(1)}s`}
          subtitle="Across all workflows"
        />
      </div>

      {/* Main Content Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column - Validation Results */}
        <div className="lg:col-span-2">
          <ValidationResultsTable results={data.validationResults} />
        </div>

        {/* Right Column - Best Practices */}
        <div>
          <BestPracticesCard scores={data.bestPracticeScores} />
        </div>
      </div>

      {/* Error Prevention and Patterns */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <ErrorPreventionAlerts preventions={data.errorPreventions} />
        <TopPatternsChart patterns={data.topPatterns} />
      </div>

      {/* Footer */}
      <div className="text-center text-sm text-gray-500 pt-4 border-t">
        <p>
          Workflow Optimization Dashboard v1.0 |
          EPIC MD-2961: Workflow Optimization &amp; Standardization
        </p>
      </div>
    </div>
  );
};

export default OptimizationDashboard;
