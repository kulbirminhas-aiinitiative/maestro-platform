/**
 * Mission Handoff Status Component
 * EPIC: MD-3024 - Mission to Execution Handoff
 *
 * Displays the current status of mission handoff operations,
 * including progress, validation results, and execution state.
 */

import React, { useState, useEffect, useCallback } from 'react';

// Types
interface ValidationIssue {
  code: string;
  message: string;
  severity: 'error' | 'warning' | 'info';
  field?: string;
  suggestion?: string;
}

interface ValidationResult {
  is_valid: boolean;
  issues: ValidationIssue[];
  validated_at: string;
}

interface HandoffStatus {
  handoff_id: string;
  mission_id: string;
  state: HandoffState;
  progress_percent: number;
  current_step: string;
  error?: string;
  execution_id?: string;
  started_at?: string;
  completed_at?: string;
  updated_at: string;
}

type HandoffState =
  | 'pending'
  | 'validating'
  | 'packaging'
  | 'triggering'
  | 'executing'
  | 'completed'
  | 'failed'
  | 'cancelled';

interface HandoffStatusProps {
  /** ID of the handoff to display */
  handoffId: string;
  /** ID of the mission being handed off */
  missionId: string;
  /** Initial status data (optional) */
  initialStatus?: HandoffStatus;
  /** Callback when handoff completes */
  onComplete?: (status: HandoffStatus) => void;
  /** Callback when handoff fails */
  onError?: (error: string) => void;
  /** Enable real-time updates via polling */
  enablePolling?: boolean;
  /** Polling interval in ms */
  pollInterval?: number;
  /** Show validation details */
  showValidation?: boolean;
  /** Compact display mode */
  compact?: boolean;
  /** Custom class name */
  className?: string;
}

// State color mapping
const stateColors: Record<HandoffState, string> = {
  pending: '#6B7280',      // gray
  validating: '#3B82F6',   // blue
  packaging: '#8B5CF6',    // purple
  triggering: '#F59E0B',   // amber
  executing: '#10B981',    // green
  completed: '#059669',    // emerald
  failed: '#EF4444',       // red
  cancelled: '#9CA3AF',    // gray
};

// State labels
const stateLabels: Record<HandoffState, string> = {
  pending: 'Pending',
  validating: 'Validating',
  packaging: 'Packaging Context',
  triggering: 'Triggering Execution',
  executing: 'Executing',
  completed: 'Completed',
  failed: 'Failed',
  cancelled: 'Cancelled',
};

// Severity icons
const severityIcons: Record<string, string> = {
  error: '❌',
  warning: '⚠️',
  info: 'ℹ️',
};

// Progress bar component
const ProgressBar: React.FC<{ progress: number; color: string }> = ({
  progress,
  color,
}) => (
  <div className="progress-container">
    <div className="progress-bar-bg">
      <div
        className="progress-bar-fill"
        style={{
          width: `${Math.min(100, Math.max(0, progress))}%`,
          backgroundColor: color,
        }}
      />
    </div>
    <span className="progress-label">{progress.toFixed(0)}%</span>
    <style>{`
      .progress-container {
        display: flex;
        align-items: center;
        gap: 8px;
        width: 100%;
      }
      .progress-bar-bg {
        flex: 1;
        height: 8px;
        background-color: #E5E7EB;
        border-radius: 4px;
        overflow: hidden;
      }
      .progress-bar-fill {
        height: 100%;
        transition: width 0.3s ease;
        border-radius: 4px;
      }
      .progress-label {
        font-size: 12px;
        font-weight: 500;
        color: #6B7280;
        min-width: 36px;
        text-align: right;
      }
    `}</style>
  </div>
);

// State badge component
const StateBadge: React.FC<{ state: HandoffState }> = ({ state }) => {
  const color = stateColors[state];
  const label = stateLabels[state];
  const isTerminal = ['completed', 'failed', 'cancelled'].includes(state);

  return (
    <div className="state-badge" style={{ backgroundColor: color }}>
      {!isTerminal && <span className="pulse-dot" />}
      <span className="state-label">{label}</span>
      <style>{`
        .state-badge {
          display: inline-flex;
          align-items: center;
          gap: 6px;
          padding: 4px 10px;
          border-radius: 12px;
          font-size: 12px;
          font-weight: 500;
          color: white;
        }
        .pulse-dot {
          width: 6px;
          height: 6px;
          background-color: white;
          border-radius: 50%;
          animation: pulse 1.5s infinite;
        }
        @keyframes pulse {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.5; }
        }
      `}</style>
    </div>
  );
};

// Validation issues component
const ValidationIssues: React.FC<{ issues: ValidationIssue[] }> = ({
  issues,
}) => {
  if (!issues.length) return null;

  const errors = issues.filter((i) => i.severity === 'error');
  const warnings = issues.filter((i) => i.severity === 'warning');
  const infos = issues.filter((i) => i.severity === 'info');

  return (
    <div className="validation-issues">
      {errors.length > 0 && (
        <div className="issue-group error">
          <h4>{severityIcons.error} Errors ({errors.length})</h4>
          {errors.map((issue, idx) => (
            <div key={idx} className="issue-item">
              <strong>{issue.code}</strong>: {issue.message}
              {issue.suggestion && (
                <div className="issue-suggestion">💡 {issue.suggestion}</div>
              )}
            </div>
          ))}
        </div>
      )}
      {warnings.length > 0 && (
        <div className="issue-group warning">
          <h4>{severityIcons.warning} Warnings ({warnings.length})</h4>
          {warnings.map((issue, idx) => (
            <div key={idx} className="issue-item">
              <strong>{issue.code}</strong>: {issue.message}
              {issue.suggestion && (
                <div className="issue-suggestion">💡 {issue.suggestion}</div>
              )}
            </div>
          ))}
        </div>
      )}
      {infos.length > 0 && (
        <div className="issue-group info">
          <h4>{severityIcons.info} Info ({infos.length})</h4>
          {infos.map((issue, idx) => (
            <div key={idx} className="issue-item">
              {issue.message}
            </div>
          ))}
        </div>
      )}
      <style>{`
        .validation-issues {
          margin-top: 12px;
        }
        .issue-group {
          margin-bottom: 12px;
          padding: 12px;
          border-radius: 8px;
        }
        .issue-group.error {
          background-color: #FEF2F2;
          border: 1px solid #FECACA;
        }
        .issue-group.warning {
          background-color: #FFFBEB;
          border: 1px solid #FDE68A;
        }
        .issue-group.info {
          background-color: #EFF6FF;
          border: 1px solid #BFDBFE;
        }
        .issue-group h4 {
          margin: 0 0 8px 0;
          font-size: 14px;
        }
        .issue-item {
          font-size: 13px;
          margin-bottom: 6px;
          color: #374151;
        }
        .issue-suggestion {
          margin-top: 4px;
          font-size: 12px;
          color: #6B7280;
        }
      `}</style>
    </div>
  );
};

// Timeline component
const HandoffTimeline: React.FC<{ status: HandoffStatus }> = ({ status }) => {
  const steps: HandoffState[] = [
    'pending',
    'validating',
    'packaging',
    'triggering',
    'executing',
    'completed',
  ];

  const currentIndex = steps.indexOf(status.state);
  const isFailed = status.state === 'failed';
  const isCancelled = status.state === 'cancelled';

  return (
    <div className="timeline">
      {steps.map((step, idx) => {
        const isCompleted = !isFailed && !isCancelled && idx < currentIndex;
        const isCurrent = status.state === step;
        const isPending = idx > currentIndex;

        return (
          <div
            key={step}
            className={`timeline-step ${isCompleted ? 'completed' : ''} ${
              isCurrent ? 'current' : ''
            } ${isPending ? 'pending' : ''}`}
          >
            <div className="timeline-dot">
              {isCompleted && '✓'}
              {isCurrent && !isFailed && '●'}
              {isFailed && isCurrent && '✕'}
            </div>
            <div className="timeline-label">{stateLabels[step]}</div>
            {idx < steps.length - 1 && <div className="timeline-line" />}
          </div>
        );
      })}
      <style>{`
        .timeline {
          display: flex;
          align-items: flex-start;
          justify-content: space-between;
          position: relative;
          padding: 20px 0;
        }
        .timeline-step {
          display: flex;
          flex-direction: column;
          align-items: center;
          flex: 1;
          position: relative;
        }
        .timeline-dot {
          width: 24px;
          height: 24px;
          border-radius: 50%;
          background-color: #E5E7EB;
          display: flex;
          align-items: center;
          justify-content: center;
          font-size: 12px;
          font-weight: bold;
          color: white;
          z-index: 1;
        }
        .timeline-step.completed .timeline-dot {
          background-color: #059669;
        }
        .timeline-step.current .timeline-dot {
          background-color: #3B82F6;
          animation: pulse-ring 1.5s infinite;
        }
        .timeline-label {
          margin-top: 8px;
          font-size: 11px;
          color: #6B7280;
          text-align: center;
        }
        .timeline-step.completed .timeline-label,
        .timeline-step.current .timeline-label {
          color: #111827;
          font-weight: 500;
        }
        .timeline-line {
          position: absolute;
          top: 12px;
          left: 50%;
          width: 100%;
          height: 2px;
          background-color: #E5E7EB;
        }
        .timeline-step.completed .timeline-line {
          background-color: #059669;
        }
        @keyframes pulse-ring {
          0% { box-shadow: 0 0 0 0 rgba(59, 130, 246, 0.4); }
          70% { box-shadow: 0 0 0 6px rgba(59, 130, 246, 0); }
          100% { box-shadow: 0 0 0 0 rgba(59, 130, 246, 0); }
        }
      `}</style>
    </div>
  );
};

// Main component
export const HandoffStatus: React.FC<HandoffStatusProps> = ({
  handoffId,
  missionId,
  initialStatus,
  onComplete,
  onError,
  enablePolling = true,
  pollInterval = 2000,
  showValidation = true,
  compact = false,
  className = '',
}) => {
  const [status, setStatus] = useState<HandoffStatus | null>(
    initialStatus || null
  );
  const [loading, setLoading] = useState(!initialStatus);
  const [error, setError] = useState<string | null>(null);
  const [validationResult, setValidationResult] =
    useState<ValidationResult | null>(null);

  // Fetch status
  const fetchStatus = useCallback(async () => {
    try {
      const response = await fetch(
        `/api/v1/mission/handoff/${handoffId}/status`
      );
      if (!response.ok) {
        throw new Error(`Failed to fetch status: ${response.statusText}`);
      }
      const data: HandoffStatus = await response.json();
      setStatus(data);
      setError(null);

      // Check for completion
      if (data.state === 'completed' && onComplete) {
        onComplete(data);
      }

      // Check for failure
      if (data.state === 'failed' && data.error && onError) {
        onError(data.error);
      }

      return data;
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Unknown error';
      setError(message);
      return null;
    } finally {
      setLoading(false);
    }
  }, [handoffId, onComplete, onError]);

  // Initial fetch
  useEffect(() => {
    if (!initialStatus) {
      fetchStatus();
    }
  }, [initialStatus, fetchStatus]);

  // Polling
  useEffect(() => {
    if (!enablePolling) return;

    const isTerminal =
      status?.state &&
      ['completed', 'failed', 'cancelled'].includes(status.state);
    if (isTerminal) return;

    const interval = setInterval(fetchStatus, pollInterval);
    return () => clearInterval(interval);
  }, [enablePolling, pollInterval, status?.state, fetchStatus]);

  // Format timestamp
  const formatTime = (timestamp?: string): string => {
    if (!timestamp) return '-';
    const date = new Date(timestamp);
    return date.toLocaleTimeString();
  };

  // Calculate duration
  const getDuration = (): string => {
    if (!status?.started_at) return '-';
    const start = new Date(status.started_at);
    const end = status.completed_at ? new Date(status.completed_at) : new Date();
    const seconds = Math.floor((end.getTime() - start.getTime()) / 1000);
    if (seconds < 60) return `${seconds}s`;
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = seconds % 60;
    return `${minutes}m ${remainingSeconds}s`;
  };

  // Loading state
  if (loading) {
    return (
      <div className={`handoff-status loading ${className}`}>
        <div className="loading-spinner" />
        <span>Loading handoff status...</span>
        <style>{`
          .handoff-status.loading {
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 12px;
            padding: 24px;
            color: #6B7280;
          }
          .loading-spinner {
            width: 20px;
            height: 20px;
            border: 2px solid #E5E7EB;
            border-top-color: #3B82F6;
            border-radius: 50%;
            animation: spin 1s linear infinite;
          }
          @keyframes spin {
            to { transform: rotate(360deg); }
          }
        `}</style>
      </div>
    );
  }

  // Error state
  if (error && !status) {
    return (
      <div className={`handoff-status error-state ${className}`}>
        <div className="error-icon">❌</div>
        <div className="error-message">{error}</div>
        <button onClick={fetchStatus} className="retry-button">
          Retry
        </button>
        <style>{`
          .handoff-status.error-state {
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 12px;
            padding: 24px;
            background-color: #FEF2F2;
            border-radius: 8px;
          }
          .error-icon {
            font-size: 32px;
          }
          .error-message {
            color: #DC2626;
            text-align: center;
          }
          .retry-button {
            padding: 8px 16px;
            background-color: #3B82F6;
            color: white;
            border: none;
            border-radius: 6px;
            cursor: pointer;
          }
          .retry-button:hover {
            background-color: #2563EB;
          }
        `}</style>
      </div>
    );
  }

  if (!status) return null;

  // Compact view
  if (compact) {
    return (
      <div className={`handoff-status compact ${className}`}>
        <StateBadge state={status.state} />
        <ProgressBar
          progress={status.progress_percent}
          color={stateColors[status.state]}
        />
        <span className="current-step">{status.current_step}</span>
        <style>{`
          .handoff-status.compact {
            display: flex;
            align-items: center;
            gap: 12px;
            padding: 12px;
            background-color: #F9FAFB;
            border-radius: 8px;
          }
          .current-step {
            font-size: 13px;
            color: #6B7280;
          }
        `}</style>
      </div>
    );
  }

  // Full view
  return (
    <div className={`handoff-status ${className}`}>
      <div className="status-header">
        <div className="status-title">
          <h3>Mission Handoff</h3>
          <StateBadge state={status.state} />
        </div>
        <div className="status-ids">
          <span>Handoff: {handoffId.slice(0, 8)}...</span>
          <span>Mission: {missionId}</span>
        </div>
      </div>

      <HandoffTimeline status={status} />

      <div className="progress-section">
        <div className="progress-header">
          <span className="current-step">{status.current_step}</span>
          <span className="duration">Duration: {getDuration()}</span>
        </div>
        <ProgressBar
          progress={status.progress_percent}
          color={stateColors[status.state]}
        />
      </div>

      {status.state === 'failed' && status.error && (
        <div className="error-section">
          <h4>Error Details</h4>
          <div className="error-content">{status.error}</div>
        </div>
      )}

      {showValidation && validationResult && (
        <ValidationIssues issues={validationResult.issues} />
      )}

      <div className="status-footer">
        <div className="timestamp">
          Started: {formatTime(status.started_at)}
          {status.completed_at && ` | Completed: ${formatTime(status.completed_at)}`}
        </div>
        {status.execution_id && (
          <div className="execution-link">
            Execution ID: <code>{status.execution_id}</code>
          </div>
        )}
      </div>

      <style>{`
        .handoff-status {
          background-color: white;
          border: 1px solid #E5E7EB;
          border-radius: 12px;
          padding: 20px;
        }
        .status-header {
          display: flex;
          justify-content: space-between;
          align-items: flex-start;
          margin-bottom: 16px;
        }
        .status-title {
          display: flex;
          align-items: center;
          gap: 12px;
        }
        .status-title h3 {
          margin: 0;
          font-size: 18px;
          font-weight: 600;
        }
        .status-ids {
          display: flex;
          flex-direction: column;
          align-items: flex-end;
          gap: 4px;
          font-size: 12px;
          color: #6B7280;
        }
        .progress-section {
          margin: 16px 0;
        }
        .progress-header {
          display: flex;
          justify-content: space-between;
          margin-bottom: 8px;
        }
        .current-step {
          font-weight: 500;
          color: #374151;
        }
        .duration {
          font-size: 13px;
          color: #6B7280;
        }
        .error-section {
          margin: 16px 0;
          padding: 12px;
          background-color: #FEF2F2;
          border: 1px solid #FECACA;
          border-radius: 8px;
        }
        .error-section h4 {
          margin: 0 0 8px 0;
          color: #DC2626;
          font-size: 14px;
        }
        .error-content {
          font-size: 13px;
          color: #991B1B;
          font-family: monospace;
        }
        .status-footer {
          margin-top: 16px;
          padding-top: 16px;
          border-top: 1px solid #E5E7EB;
          display: flex;
          justify-content: space-between;
          align-items: center;
        }
        .timestamp {
          font-size: 12px;
          color: #6B7280;
        }
        .execution-link {
          font-size: 12px;
          color: #6B7280;
        }
        .execution-link code {
          background-color: #F3F4F6;
          padding: 2px 6px;
          border-radius: 4px;
          font-family: monospace;
        }
      `}</style>
    </div>
  );
};

export default HandoffStatus;
