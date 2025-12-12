/**
 * ExecutionFlowDashboard - Real-time mission execution monitoring dashboard
 *
 * Displays:
 * - Execution status and progress
 * - Task completion tracking
 * - Real-time updates via WebSocket
 * - Verification results
 */

import React, { useState, useEffect, useCallback, useMemo } from 'react';

// Types
interface ExecutionStatus {
  state: 'pending' | 'running' | 'paused' | 'completed' | 'failed' | 'cancelled';
  progress: number;
  currentTask: string | null;
  elapsedTime: number;
  remainingTasks: number;
  checkpointId: string | null;
}

interface ProgressReport {
  totalTasks: number;
  completed: number;
  pending: number;
  inProgress: number;
  failed: number;
  percentage: number;
  estimatedRemaining: number | null;
  currentTasks: string[];
}

interface VerificationResult {
  success: boolean;
  status: 'pending' | 'passed' | 'failed' | 'warning';
  completionTime: string;
  issues: string[];
  warnings: string[];
  passedRules: string[];
  failedRules: string[];
}

interface TaskUpdate {
  taskId: string;
  status: 'pending' | 'in_progress' | 'completed' | 'failed';
  progress: number;
  message?: string;
  timestamp: string;
}

interface ExecutionFlowDashboardProps {
  executionId: string;
  missionId: string;
  onPause?: () => void;
  onResume?: () => void;
  onCancel?: () => void;
  websocketUrl?: string;
}

// Status badge component
const StatusBadge: React.FC<{ status: string }> = ({ status }) => {
  const colorMap: Record<string, string> = {
    pending: 'bg-gray-200 text-gray-800',
    running: 'bg-blue-200 text-blue-800',
    paused: 'bg-yellow-200 text-yellow-800',
    completed: 'bg-green-200 text-green-800',
    failed: 'bg-red-200 text-red-800',
    cancelled: 'bg-gray-400 text-gray-900',
    in_progress: 'bg-blue-200 text-blue-800',
    passed: 'bg-green-200 text-green-800',
    warning: 'bg-yellow-200 text-yellow-800',
  };

  return (
    <span className={`px-2 py-1 rounded-full text-sm font-medium ${colorMap[status] || 'bg-gray-200'}`}>
      {status.replace('_', ' ').toUpperCase()}
    </span>
  );
};

// Progress bar component
const ProgressBar: React.FC<{ percentage: number; showLabel?: boolean }> = ({
  percentage,
  showLabel = true,
}) => {
  const clampedPercentage = Math.min(100, Math.max(0, percentage));

  return (
    <div className="w-full">
      <div className="w-full bg-gray-200 rounded-full h-4">
        <div
          className="bg-blue-600 h-4 rounded-full transition-all duration-300"
          style={{ width: `${clampedPercentage}%` }}
        />
      </div>
      {showLabel && (
        <span className="text-sm text-gray-600 mt-1">{clampedPercentage.toFixed(1)}%</span>
      )}
    </div>
  );
};

// Format time helper
const formatTime = (seconds: number): string => {
  const hrs = Math.floor(seconds / 3600);
  const mins = Math.floor((seconds % 3600) / 60);
  const secs = Math.floor(seconds % 60);

  if (hrs > 0) {
    return `${hrs}h ${mins}m ${secs}s`;
  } else if (mins > 0) {
    return `${mins}m ${secs}s`;
  }
  return `${secs}s`;
};

// Main dashboard component
export const ExecutionFlowDashboard: React.FC<ExecutionFlowDashboardProps> = ({
  executionId,
  missionId,
  onPause,
  onResume,
  onCancel,
  websocketUrl,
}) => {
  const [status, setStatus] = useState<ExecutionStatus | null>(null);
  const [progress, setProgress] = useState<ProgressReport | null>(null);
  const [verification, setVerification] = useState<VerificationResult | null>(null);
  const [taskUpdates, setTaskUpdates] = useState<TaskUpdate[]>([]);
  const [connected, setConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // WebSocket connection
  useEffect(() => {
    if (!websocketUrl) return;

    const ws = new WebSocket(websocketUrl);

    ws.onopen = () => {
      setConnected(true);
      setError(null);
      // Subscribe to execution updates
      ws.send(JSON.stringify({ type: 'subscribe', executionId }));
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);

        switch (data.type) {
          case 'status_update':
            setStatus(data.payload);
            break;
          case 'progress_update':
            setProgress(data.payload);
            break;
          case 'task_update':
            setTaskUpdates((prev) => [data.payload, ...prev].slice(0, 50));
            break;
          case 'verification_result':
            setVerification(data.payload);
            break;
          default:
            console.log('Unknown message type:', data.type);
        }
      } catch (err) {
        console.error('Failed to parse WebSocket message:', err);
      }
    };

    ws.onerror = () => {
      setError('WebSocket connection error');
      setConnected(false);
    };

    ws.onclose = () => {
      setConnected(false);
    };

    return () => {
      ws.close();
    };
  }, [websocketUrl, executionId]);

  // Poll for status if no WebSocket
  useEffect(() => {
    if (websocketUrl) return;

    const pollStatus = async () => {
      try {
        const response = await fetch(`/api/executions/${executionId}/status`);
        if (response.ok) {
          const data = await response.json();
          setStatus(data.status);
          setProgress(data.progress);
        }
      } catch (err) {
        console.error('Failed to poll status:', err);
      }
    };

    pollStatus();
    const interval = setInterval(pollStatus, 2000);

    return () => clearInterval(interval);
  }, [executionId, websocketUrl]);

  // Control button handlers
  const handlePause = useCallback(() => {
    onPause?.();
  }, [onPause]);

  const handleResume = useCallback(() => {
    onResume?.();
  }, [onResume]);

  const handleCancel = useCallback(() => {
    if (window.confirm('Are you sure you want to cancel this execution?')) {
      onCancel?.();
    }
  }, [onCancel]);

  // Computed values
  const isRunning = status?.state === 'running';
  const isPaused = status?.state === 'paused';
  const isFinished = ['completed', 'failed', 'cancelled'].includes(status?.state || '');

  const taskStats = useMemo(() => {
    if (!progress) return null;
    return {
      total: progress.totalTasks,
      completed: progress.completed,
      failed: progress.failed,
      remaining: progress.pending + progress.inProgress,
    };
  }, [progress]);

  return (
    <div className="p-6 bg-white rounded-lg shadow-lg max-w-4xl mx-auto">
      {/* Header */}
      <div className="flex justify-between items-center mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Execution Dashboard</h1>
          <p className="text-gray-600">
            Mission: {missionId} | Execution: {executionId.slice(0, 8)}...
          </p>
        </div>
        <div className="flex items-center gap-2">
          {connected ? (
            <span className="text-green-600 text-sm flex items-center">
              <span className="w-2 h-2 bg-green-500 rounded-full mr-1 animate-pulse" />
              Live
            </span>
          ) : (
            <span className="text-gray-500 text-sm">Polling</span>
          )}
        </div>
      </div>

      {/* Error display */}
      {error && (
        <div className="mb-4 p-3 bg-red-100 text-red-700 rounded-md">{error}</div>
      )}

      {/* Status section */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
        <div className="p-4 bg-gray-50 rounded-lg">
          <h3 className="text-sm font-medium text-gray-500 mb-1">Status</h3>
          {status && <StatusBadge status={status.state} />}
        </div>
        <div className="p-4 bg-gray-50 rounded-lg">
          <h3 className="text-sm font-medium text-gray-500 mb-1">Elapsed Time</h3>
          <p className="text-xl font-semibold">
            {status ? formatTime(status.elapsedTime) : '--:--'}
          </p>
        </div>
        <div className="p-4 bg-gray-50 rounded-lg">
          <h3 className="text-sm font-medium text-gray-500 mb-1">Est. Remaining</h3>
          <p className="text-xl font-semibold">
            {progress?.estimatedRemaining
              ? formatTime(progress.estimatedRemaining)
              : '--:--'}
          </p>
        </div>
      </div>

      {/* Progress section */}
      <div className="mb-6">
        <h2 className="text-lg font-semibold mb-3">Progress</h2>
        <ProgressBar percentage={progress?.percentage || 0} />

        {taskStats && (
          <div className="grid grid-cols-4 gap-4 mt-4">
            <div className="text-center">
              <p className="text-2xl font-bold text-gray-900">{taskStats.total}</p>
              <p className="text-sm text-gray-500">Total</p>
            </div>
            <div className="text-center">
              <p className="text-2xl font-bold text-green-600">{taskStats.completed}</p>
              <p className="text-sm text-gray-500">Completed</p>
            </div>
            <div className="text-center">
              <p className="text-2xl font-bold text-blue-600">{taskStats.remaining}</p>
              <p className="text-sm text-gray-500">Remaining</p>
            </div>
            <div className="text-center">
              <p className="text-2xl font-bold text-red-600">{taskStats.failed}</p>
              <p className="text-sm text-gray-500">Failed</p>
            </div>
          </div>
        )}
      </div>

      {/* Current tasks */}
      {progress?.currentTasks && progress.currentTasks.length > 0 && (
        <div className="mb-6">
          <h2 className="text-lg font-semibold mb-3">Current Tasks</h2>
          <div className="space-y-2">
            {progress.currentTasks.map((taskId) => (
              <div
                key={taskId}
                className="p-2 bg-blue-50 rounded flex items-center"
              >
                <span className="w-2 h-2 bg-blue-500 rounded-full mr-2 animate-pulse" />
                <span className="text-sm">{taskId}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Recent updates */}
      <div className="mb-6">
        <h2 className="text-lg font-semibold mb-3">Recent Updates</h2>
        <div className="max-h-48 overflow-y-auto border rounded-lg">
          {taskUpdates.length > 0 ? (
            taskUpdates.map((update, index) => (
              <div
                key={`${update.taskId}-${index}`}
                className="p-2 border-b last:border-b-0 flex justify-between items-center"
              >
                <div>
                  <span className="font-medium">{update.taskId}</span>
                  {update.message && (
                    <span className="text-gray-500 ml-2">- {update.message}</span>
                  )}
                </div>
                <StatusBadge status={update.status} />
              </div>
            ))
          ) : (
            <p className="p-4 text-gray-500 text-center">No updates yet</p>
          )}
        </div>
      </div>

      {/* Verification results */}
      {verification && (
        <div className="mb-6">
          <h2 className="text-lg font-semibold mb-3">Verification</h2>
          <div className="p-4 bg-gray-50 rounded-lg">
            <div className="flex justify-between items-center mb-2">
              <span className="font-medium">Status</span>
              <StatusBadge status={verification.status} />
            </div>

            {verification.passedRules.length > 0 && (
              <div className="mb-2">
                <span className="text-sm text-green-600">
                  Passed: {verification.passedRules.join(', ')}
                </span>
              </div>
            )}

            {verification.failedRules.length > 0 && (
              <div className="mb-2">
                <span className="text-sm text-red-600">
                  Failed: {verification.failedRules.join(', ')}
                </span>
              </div>
            )}

            {verification.issues.length > 0 && (
              <div className="mt-2">
                <p className="text-sm font-medium text-red-600">Issues:</p>
                <ul className="list-disc list-inside text-sm text-red-600">
                  {verification.issues.map((issue, i) => (
                    <li key={i}>{issue}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Control buttons */}
      {!isFinished && (
        <div className="flex justify-end gap-3">
          {isRunning && (
            <button
              onClick={handlePause}
              className="px-4 py-2 bg-yellow-500 text-white rounded-md hover:bg-yellow-600 transition"
            >
              Pause
            </button>
          )}
          {isPaused && (
            <button
              onClick={handleResume}
              className="px-4 py-2 bg-green-500 text-white rounded-md hover:bg-green-600 transition"
            >
              Resume
            </button>
          )}
          <button
            onClick={handleCancel}
            className="px-4 py-2 bg-red-500 text-white rounded-md hover:bg-red-600 transition"
          >
            Cancel
          </button>
        </div>
      )}

      {/* Checkpoint info */}
      {status?.checkpointId && (
        <div className="mt-4 p-2 bg-gray-100 rounded text-sm text-gray-600">
          Checkpoint: {status.checkpointId.slice(0, 8)}...
        </div>
      )}
    </div>
  );
};

export default ExecutionFlowDashboard;
