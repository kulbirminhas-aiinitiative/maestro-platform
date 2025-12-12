/**
 * Project Scanner Page - External Project Gap Analysis UI
 *
 * EPIC: MD-3022
 * Child Task: MD-2923
 */

import React, { useState, useCallback } from 'react';

// Types
interface HealthScore {
  overall: number;
  code_quality: number;
  architecture: number;
  testing: number;
  documentation: number;
  security: number;
  maintainability: number;
  grade: string;
}

interface Recommendation {
  id: string;
  title: string;
  description: string;
  priority: 'critical' | 'high' | 'medium' | 'low' | 'informational';
  category: string;
  effort_estimate: string;
  impact_estimate: string;
  affected_files: string[];
  action_items: string[];
}

interface Gap {
  id: string;
  title: string;
  description: string;
  severity: 'critical' | 'high' | 'medium' | 'low';
  category: string;
  affected_files: string[];
}

interface Pattern {
  pattern: string;
  confidence: number;
  locations: string[];
}

interface ScanResult {
  project_url: string;
  project_path: string;
  status: string;
  duration_seconds: number;
  files_analyzed: number;
  gaps_found: number;
  health_score: HealthScore | null;
  recommendations: Recommendation[];
  summary: string;
  patterns?: Pattern[];
  gaps?: Gap[];
}

interface ScanFormData {
  projectUrl: string;
  branch: string;
  enableVisionAnalysis: boolean;
  enableGapAnalysis: boolean;
}

// Components
const HealthScoreCard: React.FC<{ score: HealthScore }> = ({ score }) => {
  const gradeColors: Record<string, string> = {
    A: 'bg-green-500',
    B: 'bg-green-400',
    C: 'bg-yellow-500',
    D: 'bg-orange-500',
    F: 'bg-red-500',
  };

  const getScoreColor = (value: number): string => {
    if (value >= 80) return 'text-green-600';
    if (value >= 60) return 'text-yellow-600';
    return 'text-red-600';
  };

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <h3 className="text-lg font-semibold mb-4">Health Score</h3>
      <div className="flex items-center justify-center mb-6">
        <div
          className={`w-24 h-24 rounded-full ${gradeColors[score.grade]} flex items-center justify-center`}
        >
          <span className="text-4xl font-bold text-white">{score.grade}</span>
        </div>
        <div className="ml-4">
          <div className="text-3xl font-bold">{score.overall}</div>
          <div className="text-gray-500">/ 100</div>
        </div>
      </div>
      <div className="space-y-3">
        {[
          { label: 'Code Quality', value: score.code_quality },
          { label: 'Architecture', value: score.architecture },
          { label: 'Testing', value: score.testing },
          { label: 'Documentation', value: score.documentation },
          { label: 'Security', value: score.security },
          { label: 'Maintainability', value: score.maintainability },
        ].map(({ label, value }) => (
          <div key={label} className="flex items-center">
            <span className="w-32 text-sm text-gray-600">{label}</span>
            <div className="flex-1 bg-gray-200 rounded-full h-2 mx-2">
              <div
                className="bg-blue-500 h-2 rounded-full"
                style={{ width: `${value}%` }}
              />
            </div>
            <span className={`w-10 text-sm font-medium ${getScoreColor(value)}`}>
              {value}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
};

const RecommendationCard: React.FC<{ recommendation: Recommendation }> = ({
  recommendation,
}) => {
  const [expanded, setExpanded] = useState(false);

  const priorityColors: Record<string, string> = {
    critical: 'bg-red-100 text-red-800 border-red-300',
    high: 'bg-orange-100 text-orange-800 border-orange-300',
    medium: 'bg-yellow-100 text-yellow-800 border-yellow-300',
    low: 'bg-blue-100 text-blue-800 border-blue-300',
    informational: 'bg-gray-100 text-gray-800 border-gray-300',
  };

  return (
    <div className="border rounded-lg p-4 mb-3">
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <div className="flex items-center gap-2 mb-2">
            <span
              className={`px-2 py-1 text-xs font-medium rounded border ${priorityColors[recommendation.priority]}`}
            >
              {recommendation.priority.toUpperCase()}
            </span>
            <span className="text-xs text-gray-500">{recommendation.category}</span>
          </div>
          <h4 className="font-medium">{recommendation.title}</h4>
          <p className="text-sm text-gray-600 mt-1">{recommendation.description}</p>
        </div>
        <button
          onClick={() => setExpanded(!expanded)}
          className="text-blue-500 text-sm hover:underline"
        >
          {expanded ? 'Less' : 'More'}
        </button>
      </div>
      {expanded && (
        <div className="mt-4 pt-4 border-t">
          <div className="grid grid-cols-2 gap-4 mb-4">
            <div>
              <span className="text-xs text-gray-500">Effort</span>
              <div className="font-medium capitalize">{recommendation.effort_estimate}</div>
            </div>
            <div>
              <span className="text-xs text-gray-500">Impact</span>
              <div className="font-medium capitalize">{recommendation.impact_estimate}</div>
            </div>
          </div>
          {recommendation.action_items.length > 0 && (
            <div>
              <span className="text-xs text-gray-500">Action Items</span>
              <ul className="mt-1 list-disc list-inside text-sm">
                {recommendation.action_items.map((item, idx) => (
                  <li key={idx}>{item}</li>
                ))}
              </ul>
            </div>
          )}
          {recommendation.affected_files.length > 0 && (
            <div className="mt-3">
              <span className="text-xs text-gray-500">Affected Files</span>
              <div className="mt-1 text-sm font-mono text-gray-700">
                {recommendation.affected_files.map((file, idx) => (
                  <div key={idx}>{file}</div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

const PatternCard: React.FC<{ pattern: Pattern }> = ({ pattern }) => (
  <div className="bg-gray-50 rounded p-3 mb-2">
    <div className="flex items-center justify-between">
      <span className="font-medium capitalize">{pattern.pattern.replace('_', ' ')}</span>
      <span className="text-sm text-gray-500">
        {Math.round(pattern.confidence * 100)}% confidence
      </span>
    </div>
    {pattern.locations.length > 0 && (
      <div className="text-xs text-gray-500 mt-1">
        Found in: {pattern.locations.slice(0, 3).join(', ')}
      </div>
    )}
  </div>
);

const ScanForm: React.FC<{
  onSubmit: (data: ScanFormData) => void;
  loading: boolean;
}> = ({ onSubmit, loading }) => {
  const [formData, setFormData] = useState<ScanFormData>({
    projectUrl: '',
    branch: 'main',
    enableVisionAnalysis: true,
    enableGapAnalysis: true,
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSubmit(formData);
  };

  return (
    <form onSubmit={handleSubmit} className="bg-white rounded-lg shadow p-6">
      <h2 className="text-xl font-semibold mb-4">Scan External Project</h2>
      <div className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Repository URL or Local Path
          </label>
          <input
            type="text"
            value={formData.projectUrl}
            onChange={(e) =>
              setFormData({ ...formData, projectUrl: e.target.value })
            }
            placeholder="https://github.com/user/repo or /path/to/project"
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            required
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Branch
          </label>
          <input
            type="text"
            value={formData.branch}
            onChange={(e) => setFormData({ ...formData, branch: e.target.value })}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
        <div className="flex items-center gap-6">
          <label className="flex items-center">
            <input
              type="checkbox"
              checked={formData.enableVisionAnalysis}
              onChange={(e) =>
                setFormData({ ...formData, enableVisionAnalysis: e.target.checked })
              }
              className="mr-2"
            />
            <span className="text-sm">Vision Analysis</span>
          </label>
          <label className="flex items-center">
            <input
              type="checkbox"
              checked={formData.enableGapAnalysis}
              onChange={(e) =>
                setFormData({ ...formData, enableGapAnalysis: e.target.checked })
              }
              className="mr-2"
            />
            <span className="text-sm">Gap Analysis</span>
          </label>
        </div>
        <button
          type="submit"
          disabled={loading || !formData.projectUrl}
          className="w-full bg-blue-600 text-white py-2 px-4 rounded-md hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed"
        >
          {loading ? 'Scanning...' : 'Start Scan'}
        </button>
      </div>
    </form>
  );
};

const ScanProgress: React.FC<{ status: string }> = ({ status }) => {
  const stages = ['cloning', 'scanning', 'analyzing', 'complete'];
  const currentIndex = stages.indexOf(status.toLowerCase());

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <h3 className="text-lg font-semibold mb-4">Scan Progress</h3>
      <div className="flex items-center justify-between">
        {stages.map((stage, idx) => (
          <React.Fragment key={stage}>
            <div className="flex flex-col items-center">
              <div
                className={`w-8 h-8 rounded-full flex items-center justify-center ${
                  idx <= currentIndex
                    ? 'bg-blue-500 text-white'
                    : 'bg-gray-200 text-gray-500'
                }`}
              >
                {idx < currentIndex ? '✓' : idx + 1}
              </div>
              <span className="text-xs mt-1 capitalize">{stage}</span>
            </div>
            {idx < stages.length - 1 && (
              <div
                className={`flex-1 h-1 mx-2 ${
                  idx < currentIndex ? 'bg-blue-500' : 'bg-gray-200'
                }`}
              />
            )}
          </React.Fragment>
        ))}
      </div>
    </div>
  );
};

const ResultsSummary: React.FC<{ result: ScanResult }> = ({ result }) => (
  <div className="bg-white rounded-lg shadow p-6">
    <h3 className="text-lg font-semibold mb-4">Summary</h3>
    <p className="text-gray-700 mb-4">{result.summary}</p>
    <div className="grid grid-cols-3 gap-4 text-center">
      <div className="bg-gray-50 rounded p-3">
        <div className="text-2xl font-bold text-blue-600">
          {result.files_analyzed}
        </div>
        <div className="text-sm text-gray-500">Files Analyzed</div>
      </div>
      <div className="bg-gray-50 rounded p-3">
        <div className="text-2xl font-bold text-orange-600">
          {result.gaps_found}
        </div>
        <div className="text-sm text-gray-500">Gaps Found</div>
      </div>
      <div className="bg-gray-50 rounded p-3">
        <div className="text-2xl font-bold text-green-600">
          {result.duration_seconds.toFixed(1)}s
        </div>
        <div className="text-sm text-gray-500">Scan Time</div>
      </div>
    </div>
  </div>
);

// Main Component
const ProjectScannerPage: React.FC = () => {
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<ScanResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [scanStatus, setScanStatus] = useState<string>('idle');

  const handleScan = useCallback(async (formData: ScanFormData) => {
    setLoading(true);
    setError(null);
    setResult(null);
    setScanStatus('cloning');

    try {
      // API call to backend
      const response = await fetch('/api/v1/gap-analysis/scan', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          project_url: formData.projectUrl,
          branch: formData.branch,
          enable_vision_analysis: formData.enableVisionAnalysis,
          enable_gap_analysis: formData.enableGapAnalysis,
        }),
      });

      if (!response.ok) {
        throw new Error(`Scan failed: ${response.statusText}`);
      }

      const data = await response.json();
      setScanStatus(data.status);
      setResult(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
      setScanStatus('error');
    } finally {
      setLoading(false);
    }
  }, []);

  return (
    <div className="min-h-screen bg-gray-100 py-8">
      <div className="max-w-6xl mx-auto px-4">
        <header className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900">
            External Project Scanner
          </h1>
          <p className="text-gray-600 mt-2">
            Analyze external codebases to identify gaps and improvement opportunities
          </p>
        </header>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Left Column - Form and Progress */}
          <div className="lg:col-span-1 space-y-6">
            <ScanForm onSubmit={handleScan} loading={loading} />
            {loading && <ScanProgress status={scanStatus} />}
            {error && (
              <div className="bg-red-50 border border-red-200 rounded-lg p-4">
                <h4 className="font-medium text-red-800">Error</h4>
                <p className="text-sm text-red-600">{error}</p>
              </div>
            )}
          </div>

          {/* Right Column - Results */}
          <div className="lg:col-span-2 space-y-6">
            {result && (
              <>
                <ResultsSummary result={result} />

                {result.health_score && (
                  <HealthScoreCard score={result.health_score} />
                )}

                {result.patterns && result.patterns.length > 0 && (
                  <div className="bg-white rounded-lg shadow p-6">
                    <h3 className="text-lg font-semibold mb-4">
                      Detected Patterns
                    </h3>
                    {result.patterns.map((pattern, idx) => (
                      <PatternCard key={idx} pattern={pattern} />
                    ))}
                  </div>
                )}

                {result.recommendations.length > 0 && (
                  <div className="bg-white rounded-lg shadow p-6">
                    <h3 className="text-lg font-semibold mb-4">
                      Recommendations ({result.recommendations.length})
                    </h3>
                    <div className="max-h-96 overflow-y-auto">
                      {result.recommendations.map((rec) => (
                        <RecommendationCard key={rec.id} recommendation={rec} />
                      ))}
                    </div>
                  </div>
                )}
              </>
            )}

            {!result && !loading && (
              <div className="bg-white rounded-lg shadow p-12 text-center">
                <div className="text-gray-400 text-6xl mb-4">🔍</div>
                <h3 className="text-lg font-medium text-gray-700">
                  No scan results yet
                </h3>
                <p className="text-gray-500 mt-2">
                  Enter a repository URL or local path to start scanning
                </p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default ProjectScannerPage;
