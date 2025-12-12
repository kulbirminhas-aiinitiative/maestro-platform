/**
 * SimulationDashboard - Team Simulation & Benchmarking Dashboard
 *
 * MD-3019: Team Simulation & Benchmarking
 * Frontend component for monitoring and managing team simulations.
 */

import React, { useState, useEffect, useCallback } from 'react';

// Types
interface SimulationMetrics {
  overall_quality: number;
  total_phases: number;
  [key: string]: number;
}

interface Checkpoint {
  phase: string;
  timestamp: string;
  duration_seconds: number;
  outputs: Record<string, unknown>;
}

interface SimulationResult {
  simulation_id: string;
  scenario_name: string;
  status: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled';
  start_time: string;
  end_time: string | null;
  duration_seconds: number;
  outputs: Record<string, unknown>;
  metrics: SimulationMetrics;
  errors: string[];
  checkpoints: Checkpoint[];
}

interface BenchmarkMetrics {
  throughput: number;
  latency: {
    p50: number;
    p95: number;
    p99: number;
    mean: number;
    std: number;
  };
  quality: {
    mean: number;
    std: number;
  };
  error_rate: number;
  operations: {
    total: number;
    successful: number;
    failed: number;
  };
}

interface BenchmarkResult {
  benchmark_id: string;
  scenario_name: string;
  metrics: BenchmarkMetrics;
  start_time: string;
  end_time: string;
  duration_seconds: number;
}

interface ScenarioConfig {
  name: string;
  description: string;
  team_size: number;
  complexity: 'simple' | 'medium' | 'complex';
  timeout_seconds: number;
}

// Predefined scenarios
const PREDEFINED_SCENARIOS: Record<string, ScenarioConfig> = {
  simple_api: {
    name: 'Simple API Development',
    description: 'Build a REST API with basic CRUD operations',
    team_size: 3,
    complexity: 'simple',
    timeout_seconds: 120,
  },
  complex_ml: {
    name: 'ML Pipeline Development',
    description: 'Build ML training and prediction pipeline',
    team_size: 5,
    complexity: 'complex',
    timeout_seconds: 600,
  },
  microservices: {
    name: 'Microservices Architecture',
    description: 'Build distributed microservices platform',
    team_size: 7,
    complexity: 'complex',
    timeout_seconds: 900,
  },
  data_pipeline: {
    name: 'Data Pipeline Development',
    description: 'Build ETL data processing pipeline',
    team_size: 4,
    complexity: 'medium',
    timeout_seconds: 300,
  },
};

// Status badge component
const StatusBadge: React.FC<{ status: SimulationResult['status'] }> = ({ status }) => {
  const statusStyles: Record<string, string> = {
    pending: 'bg-gray-100 text-gray-800',
    running: 'bg-blue-100 text-blue-800',
    completed: 'bg-green-100 text-green-800',
    failed: 'bg-red-100 text-red-800',
    cancelled: 'bg-yellow-100 text-yellow-800',
  };

  return (
    <span className={`px-2 py-1 rounded-full text-xs font-medium ${statusStyles[status]}`}>
      {status.charAt(0).toUpperCase() + status.slice(1)}
    </span>
  );
};

// Progress bar component
const ProgressBar: React.FC<{ value: number; max: number; label?: string }> = ({
  value,
  max,
  label,
}) => {
  const percentage = max > 0 ? (value / max) * 100 : 0;

  return (
    <div className="w-full">
      {label && <div className="text-sm text-gray-600 mb-1">{label}</div>}
      <div className="w-full bg-gray-200 rounded-full h-2">
        <div
          className="bg-blue-600 h-2 rounded-full transition-all duration-300"
          style={{ width: `${percentage}%` }}
        />
      </div>
      <div className="text-xs text-gray-500 mt-1">{value} / {max}</div>
    </div>
  );
};

// Metric card component
const MetricCard: React.FC<{
  title: string;
  value: string | number;
  subtitle?: string;
  trend?: 'up' | 'down' | 'neutral';
}> = ({ title, value, subtitle, trend }) => {
  const trendColors = {
    up: 'text-green-600',
    down: 'text-red-600',
    neutral: 'text-gray-600',
  };

  return (
    <div className="bg-white rounded-lg shadow p-4">
      <div className="text-sm text-gray-500">{title}</div>
      <div className="text-2xl font-bold mt-1">{value}</div>
      {subtitle && (
        <div className={`text-xs mt-1 ${trend ? trendColors[trend] : 'text-gray-500'}`}>
          {subtitle}
        </div>
      )}
    </div>
  );
};

// Simulation card component
const SimulationCard: React.FC<{
  simulation: SimulationResult;
  onCancel?: (id: string) => void;
}> = ({ simulation, onCancel }) => {
  const formatDuration = (seconds: number): string => {
    if (seconds < 60) return `${seconds.toFixed(1)}s`;
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = seconds % 60;
    return `${minutes}m ${remainingSeconds.toFixed(0)}s`;
  };

  return (
    <div className="bg-white rounded-lg shadow p-4 mb-4">
      <div className="flex justify-between items-start">
        <div>
          <h3 className="font-semibold text-lg">{simulation.scenario_name}</h3>
          <div className="text-sm text-gray-500">ID: {simulation.simulation_id}</div>
        </div>
        <StatusBadge status={simulation.status} />
      </div>

      <div className="mt-4 grid grid-cols-3 gap-4">
        <div>
          <div className="text-xs text-gray-500">Duration</div>
          <div className="font-medium">{formatDuration(simulation.duration_seconds)}</div>
        </div>
        <div>
          <div className="text-xs text-gray-500">Quality</div>
          <div className="font-medium">
            {((simulation.metrics.overall_quality || 0) * 100).toFixed(1)}%
          </div>
        </div>
        <div>
          <div className="text-xs text-gray-500">Phases</div>
          <div className="font-medium">{simulation.checkpoints.length}</div>
        </div>
      </div>

      {simulation.status === 'running' && (
        <div className="mt-4">
          <ProgressBar
            value={simulation.checkpoints.length}
            max={5}
            label="Progress"
          />
        </div>
      )}

      {simulation.errors.length > 0 && (
        <div className="mt-4 bg-red-50 rounded p-2">
          <div className="text-sm text-red-800 font-medium">Errors:</div>
          {simulation.errors.map((error, idx) => (
            <div key={idx} className="text-sm text-red-600">{error}</div>
          ))}
        </div>
      )}

      {simulation.status === 'running' && onCancel && (
        <div className="mt-4">
          <button
            onClick={() => onCancel(simulation.simulation_id)}
            className="px-3 py-1 text-sm bg-red-100 text-red-800 rounded hover:bg-red-200"
          >
            Cancel
          </button>
        </div>
      )}
    </div>
  );
};

// Benchmark result component
const BenchmarkCard: React.FC<{ benchmark: BenchmarkResult }> = ({ benchmark }) => {
  return (
    <div className="bg-white rounded-lg shadow p-4 mb-4">
      <div className="flex justify-between items-start">
        <div>
          <h3 className="font-semibold text-lg">{benchmark.scenario_name}</h3>
          <div className="text-sm text-gray-500">ID: {benchmark.benchmark_id}</div>
        </div>
      </div>

      <div className="mt-4 grid grid-cols-4 gap-4">
        <div>
          <div className="text-xs text-gray-500">Throughput</div>
          <div className="font-medium">{benchmark.metrics.throughput.toFixed(3)} ops/s</div>
        </div>
        <div>
          <div className="text-xs text-gray-500">Latency P99</div>
          <div className="font-medium">{benchmark.metrics.latency.p99.toFixed(3)}s</div>
        </div>
        <div>
          <div className="text-xs text-gray-500">Quality</div>
          <div className="font-medium">{(benchmark.metrics.quality.mean * 100).toFixed(1)}%</div>
        </div>
        <div>
          <div className="text-xs text-gray-500">Error Rate</div>
          <div className="font-medium">{(benchmark.metrics.error_rate * 100).toFixed(2)}%</div>
        </div>
      </div>

      <div className="mt-4 grid grid-cols-3 gap-2 text-sm">
        <div className="bg-gray-50 rounded p-2">
          <div className="text-gray-500">Total Ops</div>
          <div className="font-medium">{benchmark.metrics.operations.total}</div>
        </div>
        <div className="bg-green-50 rounded p-2">
          <div className="text-gray-500">Successful</div>
          <div className="font-medium text-green-700">
            {benchmark.metrics.operations.successful}
          </div>
        </div>
        <div className="bg-red-50 rounded p-2">
          <div className="text-gray-500">Failed</div>
          <div className="font-medium text-red-700">{benchmark.metrics.operations.failed}</div>
        </div>
      </div>
    </div>
  );
};

// Main Dashboard Component
export const SimulationDashboard: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'simulations' | 'benchmarks' | 'configure'>('simulations');
  const [simulations, setSimulations] = useState<SimulationResult[]>([]);
  const [benchmarks, setBenchmarks] = useState<BenchmarkResult[]>([]);
  const [selectedScenario, setSelectedScenario] = useState<string>('simple_api');
  const [isRunning, setIsRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // API base URL - would come from environment in production
  const API_BASE = '/api/simulation';

  // Fetch simulations
  const fetchSimulations = useCallback(async () => {
    try {
      const response = await fetch(`${API_BASE}/simulations`);
      if (response.ok) {
        const data = await response.json();
        setSimulations(data);
      }
    } catch (err) {
      console.error('Failed to fetch simulations:', err);
    }
  }, []);

  // Fetch benchmarks
  const fetchBenchmarks = useCallback(async () => {
    try {
      const response = await fetch(`${API_BASE}/benchmarks`);
      if (response.ok) {
        const data = await response.json();
        setBenchmarks(data);
      }
    } catch (err) {
      console.error('Failed to fetch benchmarks:', err);
    }
  }, []);

  // Poll for updates
  useEffect(() => {
    fetchSimulations();
    fetchBenchmarks();

    const interval = setInterval(() => {
      fetchSimulations();
      fetchBenchmarks();
    }, 5000);

    return () => clearInterval(interval);
  }, [fetchSimulations, fetchBenchmarks]);

  // Run simulation
  const runSimulation = async () => {
    setIsRunning(true);
    setError(null);

    try {
      const response = await fetch(`${API_BASE}/run`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ scenario_type: selectedScenario }),
      });

      if (!response.ok) {
        throw new Error('Failed to start simulation');
      }

      await fetchSimulations();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setIsRunning(false);
    }
  };

  // Run benchmark
  const runBenchmark = async () => {
    setIsRunning(true);
    setError(null);

    try {
      const response = await fetch(`${API_BASE}/benchmark`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          scenario_type: selectedScenario,
          iterations: 10,
        }),
      });

      if (!response.ok) {
        throw new Error('Failed to start benchmark');
      }

      await fetchBenchmarks();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setIsRunning(false);
    }
  };

  // Cancel simulation
  const cancelSimulation = async (simulationId: string) => {
    try {
      const response = await fetch(`${API_BASE}/simulations/${simulationId}/cancel`, {
        method: 'POST',
      });

      if (response.ok) {
        await fetchSimulations();
      }
    } catch (err) {
      console.error('Failed to cancel simulation:', err);
    }
  };

  // Calculate summary metrics
  const completedSimulations = simulations.filter((s) => s.status === 'completed');
  const runningSimulations = simulations.filter((s) => s.status === 'running');
  const averageQuality =
    completedSimulations.length > 0
      ? completedSimulations.reduce((acc, s) => acc + (s.metrics.overall_quality || 0), 0) /
        completedSimulations.length
      : 0;

  return (
    <div className="min-h-screen bg-gray-100">
      {/* Header */}
      <header className="bg-white shadow">
        <div className="max-w-7xl mx-auto px-4 py-6">
          <h1 className="text-3xl font-bold text-gray-900">
            Team Simulation Dashboard
          </h1>
          <p className="mt-1 text-sm text-gray-500">
            Monitor and manage team simulations and benchmarks
          </p>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 py-6">
        {/* Summary Metrics */}
        <div className="grid grid-cols-4 gap-4 mb-6">
          <MetricCard
            title="Total Simulations"
            value={simulations.length}
            subtitle={`${runningSimulations.length} running`}
          />
          <MetricCard
            title="Completed"
            value={completedSimulations.length}
            trend="up"
          />
          <MetricCard
            title="Average Quality"
            value={`${(averageQuality * 100).toFixed(1)}%`}
          />
          <MetricCard
            title="Benchmarks Run"
            value={benchmarks.length}
          />
        </div>

        {/* Tabs */}
        <div className="border-b border-gray-200 mb-6">
          <nav className="-mb-px flex space-x-8">
            {(['simulations', 'benchmarks', 'configure'] as const).map((tab) => (
              <button
                key={tab}
                onClick={() => setActiveTab(tab)}
                className={`py-4 px-1 border-b-2 font-medium text-sm ${
                  activeTab === tab
                    ? 'border-blue-500 text-blue-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }`}
              >
                {tab.charAt(0).toUpperCase() + tab.slice(1)}
              </button>
            ))}
          </nav>
        </div>

        {/* Error Display */}
        {error && (
          <div className="mb-6 bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded">
            {error}
          </div>
        )}

        {/* Tab Content */}
        {activeTab === 'simulations' && (
          <div>
            <div className="flex justify-between items-center mb-4">
              <h2 className="text-xl font-semibold">Simulations</h2>
              <button
                onClick={runSimulation}
                disabled={isRunning}
                className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50"
              >
                {isRunning ? 'Starting...' : 'Run Simulation'}
              </button>
            </div>

            {simulations.length === 0 ? (
              <div className="text-center py-12 text-gray-500">
                No simulations yet. Click "Run Simulation" to start one.
              </div>
            ) : (
              <div className="space-y-4">
                {simulations.map((simulation) => (
                  <SimulationCard
                    key={simulation.simulation_id}
                    simulation={simulation}
                    onCancel={cancelSimulation}
                  />
                ))}
              </div>
            )}
          </div>
        )}

        {activeTab === 'benchmarks' && (
          <div>
            <div className="flex justify-between items-center mb-4">
              <h2 className="text-xl font-semibold">Benchmarks</h2>
              <button
                onClick={runBenchmark}
                disabled={isRunning}
                className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50"
              >
                {isRunning ? 'Starting...' : 'Run Benchmark'}
              </button>
            </div>

            {benchmarks.length === 0 ? (
              <div className="text-center py-12 text-gray-500">
                No benchmarks yet. Click "Run Benchmark" to start one.
              </div>
            ) : (
              <div className="space-y-4">
                {benchmarks.map((benchmark) => (
                  <BenchmarkCard key={benchmark.benchmark_id} benchmark={benchmark} />
                ))}
              </div>
            )}
          </div>
        )}

        {activeTab === 'configure' && (
          <div>
            <h2 className="text-xl font-semibold mb-4">Configure Simulation</h2>

            <div className="bg-white rounded-lg shadow p-6">
              <div className="mb-6">
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Select Scenario
                </label>
                <select
                  value={selectedScenario}
                  onChange={(e) => setSelectedScenario(e.target.value)}
                  className="w-full border border-gray-300 rounded-md px-3 py-2"
                >
                  {Object.entries(PREDEFINED_SCENARIOS).map(([key, scenario]) => (
                    <option key={key} value={key}>
                      {scenario.name}
                    </option>
                  ))}
                </select>
              </div>

              {selectedScenario && PREDEFINED_SCENARIOS[selectedScenario] && (
                <div className="bg-gray-50 rounded-lg p-4">
                  <h3 className="font-medium mb-2">
                    {PREDEFINED_SCENARIOS[selectedScenario].name}
                  </h3>
                  <p className="text-sm text-gray-600 mb-4">
                    {PREDEFINED_SCENARIOS[selectedScenario].description}
                  </p>

                  <div className="grid grid-cols-3 gap-4 text-sm">
                    <div>
                      <div className="text-gray-500">Team Size</div>
                      <div className="font-medium">
                        {PREDEFINED_SCENARIOS[selectedScenario].team_size} members
                      </div>
                    </div>
                    <div>
                      <div className="text-gray-500">Complexity</div>
                      <div className="font-medium capitalize">
                        {PREDEFINED_SCENARIOS[selectedScenario].complexity}
                      </div>
                    </div>
                    <div>
                      <div className="text-gray-500">Timeout</div>
                      <div className="font-medium">
                        {PREDEFINED_SCENARIOS[selectedScenario].timeout_seconds}s
                      </div>
                    </div>
                  </div>
                </div>
              )}

              <div className="mt-6 flex space-x-4">
                <button
                  onClick={runSimulation}
                  disabled={isRunning}
                  className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50"
                >
                  Run Simulation
                </button>
                <button
                  onClick={runBenchmark}
                  disabled={isRunning}
                  className="px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700 disabled:opacity-50"
                >
                  Run Benchmark
                </button>
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
};

export default SimulationDashboard;
