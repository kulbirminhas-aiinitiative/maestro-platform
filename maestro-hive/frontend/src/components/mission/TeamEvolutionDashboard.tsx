/**
 * TeamEvolutionDashboard - MD-3020
 *
 * Interactive dashboard for monitoring and controlling team evolution
 * and optimization. Provides real-time visualization of evolution progress,
 * performance metrics, and recommendations.
 */

import React, { useState, useCallback, useEffect, useMemo } from 'react';

// Types
interface TeamRole {
  name: string;
  skills: string[];
  weight: number;
}

interface TeamConfiguration {
  configId: string;
  teamId: string;
  roles: TeamRole[];
  skillWeights: Record<string, number>;
  fitnessScore: number;
  generation: number;
  createdAt: string;
}

interface EvolutionMetrics {
  teamId: string;
  generation: number;
  bestFitness: number;
  averageFitness: number;
  populationDiversity: number;
  stagnationCount: number;
}

interface EvolutionResult {
  teamId: string;
  bestConfiguration: TeamConfiguration;
  bestFitness: number;
  generationsCompleted: number;
  evolutionHistory: EvolutionMetrics[];
  converged: boolean;
  totalDurationMs: number;
}

interface PerformanceSnapshot {
  teamId: string;
  timestamp: string;
  throughput: number;
  quality: number;
  efficiency: number;
}

interface Recommendation {
  id: string;
  teamId: string;
  title: string;
  description: string;
  priority: 'critical' | 'high' | 'medium' | 'low';
  estimatedImpact: number;
  actionType: string;
  confidence: number;
}

type EvolutionStrategy = 'genetic' | 'hill_climbing' | 'simulated_annealing' | 'memetic';
type OptimizationTarget = 'throughput' | 'quality' | 'efficiency' | 'balanced';

interface Team {
  id: string;
  name: string;
  members: string[];
  currentFitness: number;
  performance: PerformanceSnapshot;
}

// Mock data for demonstration
const mockTeams: Team[] = [
  {
    id: 'team-alpha',
    name: 'Alpha Team',
    members: ['backend_dev', 'frontend_dev', 'qa_engineer'],
    currentFitness: 0.72,
    performance: {
      teamId: 'team-alpha',
      timestamp: new Date().toISOString(),
      throughput: 0.75,
      quality: 0.82,
      efficiency: 0.68,
    },
  },
  {
    id: 'team-beta',
    name: 'Beta Team',
    members: ['backend_dev', 'devops', 'designer'],
    currentFitness: 0.65,
    performance: {
      teamId: 'team-beta',
      timestamp: new Date().toISOString(),
      throughput: 0.60,
      quality: 0.70,
      efficiency: 0.65,
    },
  },
];

const mockRecommendations: Recommendation[] = [
  {
    id: 'rec_1',
    teamId: 'team-alpha',
    title: 'Add QA capacity',
    description: 'Consider adding another QA engineer to improve quality metrics.',
    priority: 'medium',
    estimatedImpact: 0.15,
    actionType: 'add_role',
    confidence: 0.85,
  },
  {
    id: 'rec_2',
    teamId: 'team-beta',
    title: 'Improve throughput',
    description: 'Team velocity is below target. Review task allocation.',
    priority: 'high',
    estimatedImpact: 0.20,
    actionType: 'optimize_workflow',
    confidence: 0.78,
  },
];

// Utility components
const ProgressBar: React.FC<{ value: number; max?: number; color?: string }> = ({
  value,
  max = 1,
  color = 'blue',
}) => {
  const percentage = Math.min(100, (value / max) * 100);
  const colorClasses: Record<string, string> = {
    blue: 'bg-blue-500',
    green: 'bg-green-500',
    yellow: 'bg-yellow-500',
    red: 'bg-red-500',
  };

  return (
    <div className="w-full bg-gray-200 rounded-full h-2.5">
      <div
        className={`h-2.5 rounded-full ${colorClasses[color] || colorClasses.blue}`}
        style={{ width: `${percentage}%` }}
      />
    </div>
  );
};

const MetricCard: React.FC<{
  label: string;
  value: number;
  change?: number;
  format?: 'percent' | 'number';
}> = ({ label, value, change, format = 'percent' }) => {
  const formattedValue = format === 'percent' ? `${(value * 100).toFixed(1)}%` : value.toFixed(2);
  const changeColor = change && change > 0 ? 'text-green-600' : change && change < 0 ? 'text-red-600' : 'text-gray-500';

  return (
    <div className="bg-white rounded-lg shadow p-4">
      <div className="text-sm text-gray-500">{label}</div>
      <div className="text-2xl font-bold">{formattedValue}</div>
      {change !== undefined && (
        <div className={`text-sm ${changeColor}`}>
          {change > 0 ? '+' : ''}{(change * 100).toFixed(1)}%
        </div>
      )}
    </div>
  );
};

const PriorityBadge: React.FC<{ priority: string }> = ({ priority }) => {
  const colors: Record<string, string> = {
    critical: 'bg-red-100 text-red-800',
    high: 'bg-orange-100 text-orange-800',
    medium: 'bg-yellow-100 text-yellow-800',
    low: 'bg-green-100 text-green-800',
  };

  return (
    <span className={`px-2 py-1 rounded-full text-xs font-medium ${colors[priority] || colors.medium}`}>
      {priority.toUpperCase()}
    </span>
  );
};

// Main Dashboard Component
const TeamEvolutionDashboard: React.FC = () => {
  const [selectedTeam, setSelectedTeam] = useState<Team | null>(mockTeams[0]);
  const [teams, setTeams] = useState<Team[]>(mockTeams);
  const [recommendations, setRecommendations] = useState<Recommendation[]>(mockRecommendations);
  const [isEvolving, setIsEvolving] = useState(false);
  const [evolutionProgress, setEvolutionProgress] = useState(0);
  const [evolutionHistory, setEvolutionHistory] = useState<EvolutionMetrics[]>([]);
  const [strategy, setStrategy] = useState<EvolutionStrategy>('genetic');
  const [optimizationTarget, setOptimizationTarget] = useState<OptimizationTarget>('balanced');
  const [generations, setGenerations] = useState(10);

  // Simulated evolution function
  const startEvolution = useCallback(async () => {
    if (!selectedTeam || isEvolving) return;

    setIsEvolving(true);
    setEvolutionProgress(0);
    setEvolutionHistory([]);

    // Simulate evolution generations
    for (let gen = 0; gen < generations; gen++) {
      await new Promise((resolve) => setTimeout(resolve, 500));

      const progress = ((gen + 1) / generations) * 100;
      setEvolutionProgress(progress);

      // Simulate improving fitness
      const baselineFitness = selectedTeam.currentFitness;
      const improvement = Math.min(0.3, (gen + 1) * 0.03 * Math.random());

      const metrics: EvolutionMetrics = {
        teamId: selectedTeam.id,
        generation: gen + 1,
        bestFitness: Math.min(0.98, baselineFitness + improvement),
        averageFitness: baselineFitness + improvement * 0.7,
        populationDiversity: 0.3 - gen * 0.02,
        stagnationCount: 0,
      };

      setEvolutionHistory((prev) => [...prev, metrics]);
    }

    // Update team fitness
    setTeams((prev) =>
      prev.map((t) =>
        t.id === selectedTeam.id
          ? { ...t, currentFitness: Math.min(0.98, t.currentFitness + 0.15) }
          : t
      )
    );

    setIsEvolving(false);
  }, [selectedTeam, isEvolving, generations]);

  // Render evolution progress chart
  const renderEvolutionChart = useMemo(() => {
    if (evolutionHistory.length === 0) {
      return (
        <div className="h-48 flex items-center justify-center text-gray-400">
          No evolution data yet. Start evolution to see progress.
        </div>
      );
    }

    const maxFitness = Math.max(...evolutionHistory.map((h) => h.bestFitness));

    return (
      <div className="h-48 flex items-end space-x-1">
        {evolutionHistory.map((metrics, idx) => (
          <div
            key={idx}
            className="flex-1 bg-blue-500 rounded-t hover:bg-blue-600 transition-colors"
            style={{ height: `${(metrics.bestFitness / maxFitness) * 100}%` }}
            title={`Gen ${metrics.generation}: ${(metrics.bestFitness * 100).toFixed(1)}%`}
          />
        ))}
      </div>
    );
  }, [evolutionHistory]);

  return (
    <div className="min-h-screen bg-gray-100 p-6">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900">Team Evolution Dashboard</h1>
          <p className="text-gray-600">Monitor and optimize team composition using evolutionary algorithms</p>
        </div>

        {/* Team Selection and Overview */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
          <div className="md:col-span-1">
            <div className="bg-white rounded-lg shadow p-4">
              <h2 className="text-lg font-semibold mb-4">Teams</h2>
              <div className="space-y-2">
                {teams.map((team) => (
                  <button
                    key={team.id}
                    onClick={() => setSelectedTeam(team)}
                    className={`w-full p-3 rounded-lg text-left transition-colors ${
                      selectedTeam?.id === team.id
                        ? 'bg-blue-100 border-blue-500 border'
                        : 'bg-gray-50 hover:bg-gray-100'
                    }`}
                  >
                    <div className="font-medium">{team.name}</div>
                    <div className="text-sm text-gray-500">
                      Fitness: {(team.currentFitness * 100).toFixed(1)}%
                    </div>
                  </button>
                ))}
              </div>
            </div>
          </div>

          {/* Metrics Overview */}
          <div className="md:col-span-3">
            {selectedTeam && (
              <div className="grid grid-cols-4 gap-4">
                <MetricCard
                  label="Current Fitness"
                  value={selectedTeam.currentFitness}
                  change={0.05}
                />
                <MetricCard
                  label="Throughput"
                  value={selectedTeam.performance.throughput}
                />
                <MetricCard
                  label="Quality"
                  value={selectedTeam.performance.quality}
                />
                <MetricCard
                  label="Efficiency"
                  value={selectedTeam.performance.efficiency}
                />
              </div>
            )}
          </div>
        </div>

        {/* Evolution Controls and Progress */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
          {/* Evolution Controls */}
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-lg font-semibold mb-4">Evolution Controls</h2>

            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Strategy
                </label>
                <select
                  value={strategy}
                  onChange={(e) => setStrategy(e.target.value as EvolutionStrategy)}
                  className="w-full p-2 border rounded-lg"
                  disabled={isEvolving}
                >
                  <option value="genetic">Genetic Algorithm</option>
                  <option value="hill_climbing">Hill Climbing</option>
                  <option value="simulated_annealing">Simulated Annealing</option>
                  <option value="memetic">Memetic (Hybrid)</option>
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Generations: {generations}
                </label>
                <input
                  type="range"
                  min="5"
                  max="50"
                  value={generations}
                  onChange={(e) => setGenerations(parseInt(e.target.value))}
                  className="w-full"
                  disabled={isEvolving}
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Optimization Target
                </label>
                <select
                  value={optimizationTarget}
                  onChange={(e) => setOptimizationTarget(e.target.value as OptimizationTarget)}
                  className="w-full p-2 border rounded-lg"
                  disabled={isEvolving}
                >
                  <option value="balanced">Balanced</option>
                  <option value="throughput">Throughput</option>
                  <option value="quality">Quality</option>
                  <option value="efficiency">Efficiency</option>
                </select>
              </div>

              <button
                onClick={startEvolution}
                disabled={!selectedTeam || isEvolving}
                className={`w-full py-3 rounded-lg font-medium ${
                  isEvolving
                    ? 'bg-gray-300 cursor-not-allowed'
                    : 'bg-blue-600 text-white hover:bg-blue-700'
                }`}
              >
                {isEvolving ? 'Evolving...' : 'Start Evolution'}
              </button>

              {isEvolving && (
                <div>
                  <div className="flex justify-between text-sm text-gray-600 mb-1">
                    <span>Progress</span>
                    <span>{evolutionProgress.toFixed(0)}%</span>
                  </div>
                  <ProgressBar value={evolutionProgress} max={100} color="green" />
                </div>
              )}
            </div>
          </div>

          {/* Evolution Progress Chart */}
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-lg font-semibold mb-4">Evolution Progress</h2>
            {renderEvolutionChart}
            {evolutionHistory.length > 0 && (
              <div className="mt-4 text-sm text-gray-600">
                <div>Best Fitness: {(evolutionHistory[evolutionHistory.length - 1]?.bestFitness * 100).toFixed(1)}%</div>
                <div>Generations: {evolutionHistory.length}</div>
              </div>
            )}
          </div>
        </div>

        {/* Recommendations */}
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-lg font-semibold mb-4">Optimization Recommendations</h2>

          {recommendations.length === 0 ? (
            <div className="text-gray-500">No recommendations available.</div>
          ) : (
            <div className="space-y-4">
              {recommendations.map((rec) => (
                <div
                  key={rec.id}
                  className="border rounded-lg p-4 hover:bg-gray-50 transition-colors"
                >
                  <div className="flex items-start justify-between">
                    <div>
                      <div className="flex items-center gap-2 mb-1">
                        <span className="font-medium">{rec.title}</span>
                        <PriorityBadge priority={rec.priority} />
                      </div>
                      <p className="text-sm text-gray-600">{rec.description}</p>
                    </div>
                    <div className="text-right">
                      <div className="text-sm text-gray-500">
                        Impact: +{(rec.estimatedImpact * 100).toFixed(0)}%
                      </div>
                      <div className="text-sm text-gray-400">
                        Confidence: {(rec.confidence * 100).toFixed(0)}%
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default TeamEvolutionDashboard;
