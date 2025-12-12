/**
 * ApprovalDashboard.tsx
 *
 * Human-in-the-Loop Approval Dashboard Component
 * Provides UI for reviewing, approving, and managing approval requests.
 *
 * Related EPIC: MD-3023 - Human-in-the-Loop Approval System
 * EU AI Act Compliance: Article 14 (Human Oversight)
 */

import React, { useState, useEffect, useCallback } from 'react';

// Types matching backend API
export type ApprovalType = 'decision' | 'override' | 'critical' | 'compliance';
export type ApprovalStatus = 'pending' | 'approved' | 'rejected' | 'escalated' | 'cancelled' | 'expired';
export type Priority = 'LOW' | 'NORMAL' | 'HIGH' | 'CRITICAL';
export type ApprovalDecision = 'approved' | 'rejected';

export interface ApprovalRequest {
  id: string;
  workflow_id: string;
  request_type: ApprovalType;
  context: Record<string, unknown>;
  requester: string;
  assigned_to: string[];
  priority: number;
  timeout_seconds: number;
  created_at: string;
  status: ApprovalStatus;
  decision: ApprovalDecision | null;
  decided_by: string | null;
  decided_at: string | null;
  comments: string | null;
  escalation_level: number;
}

export interface QueueStats {
  total_pending: number;
  by_priority: Record<string, number>;
  by_type: Record<string, number>;
  overdue_count: number;
  average_wait_seconds: number;
  oldest_request_age_seconds: number;
  timestamp: string;
}

export interface ApprovalResult {
  request_id: string;
  success: boolean;
  decision: ApprovalDecision;
  workflow_resumed: boolean;
  message: string;
  timestamp: string;
}

interface ApprovalDashboardProps {
  approverId: string;
  apiBaseUrl?: string;
  onApprovalComplete?: (result: ApprovalResult) => void;
  refreshInterval?: number;
}

const PRIORITY_LABELS: Record<number, string> = {
  1: 'LOW',
  2: 'NORMAL',
  3: 'HIGH',
  4: 'CRITICAL'
};

const PRIORITY_COLORS: Record<number, string> = {
  1: '#6b7280',
  2: '#3b82f6',
  3: '#f59e0b',
  4: '#ef4444'
};

const TYPE_LABELS: Record<ApprovalType, string> = {
  decision: 'Decision',
  override: 'Override',
  critical: 'Critical',
  compliance: 'Compliance'
};

const STATUS_COLORS: Record<ApprovalStatus, string> = {
  pending: '#f59e0b',
  approved: '#10b981',
  rejected: '#ef4444',
  escalated: '#8b5cf6',
  cancelled: '#6b7280',
  expired: '#9ca3af'
};

export const ApprovalDashboard: React.FC<ApprovalDashboardProps> = ({
  approverId,
  apiBaseUrl = '/api/approvals',
  onApprovalComplete,
  refreshInterval = 30000
}) => {
  const [requests, setRequests] = useState<ApprovalRequest[]>([]);
  const [stats, setStats] = useState<QueueStats | null>(null);
  const [selectedRequest, setSelectedRequest] = useState<ApprovalRequest | null>(null);
  const [comments, setComments] = useState('');
  const [isLoading, setIsLoading] = useState(true);
  const [isProcessing, setIsProcessing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState<{
    priority: number | null;
    type: ApprovalType | null;
    showOverdueOnly: boolean;
  }>({
    priority: null,
    type: null,
    showOverdueOnly: false
  });

  const fetchRequests = useCallback(async () => {
    try {
      const params = new URLSearchParams({ approver_id: approverId });
      if (filter.priority) params.append('priority', filter.priority.toString());
      if (filter.type) params.append('type', filter.type);
      if (filter.showOverdueOnly) params.append('overdue', 'true');

      const response = await fetch(`${apiBaseUrl}/pending?${params}`);
      if (!response.ok) throw new Error('Failed to fetch requests');

      const data = await response.json();
      setRequests(data.requests || []);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load requests');
    }
  }, [apiBaseUrl, approverId, filter]);

  const fetchStats = useCallback(async () => {
    try {
      const response = await fetch(`${apiBaseUrl}/stats`);
      if (!response.ok) throw new Error('Failed to fetch stats');

      const data = await response.json();
      setStats(data);
    } catch (err) {
      console.error('Failed to fetch stats:', err);
    }
  }, [apiBaseUrl]);

  useEffect(() => {
    const loadData = async () => {
      setIsLoading(true);
      await Promise.all([fetchRequests(), fetchStats()]);
      setIsLoading(false);
    };

    loadData();

    const interval = setInterval(() => {
      fetchRequests();
      fetchStats();
    }, refreshInterval);

    return () => clearInterval(interval);
  }, [fetchRequests, fetchStats, refreshInterval]);

  const handleApproval = async (decision: ApprovalDecision) => {
    if (!selectedRequest) return;

    setIsProcessing(true);
    try {
      const response = await fetch(`${apiBaseUrl}/process`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          request_id: selectedRequest.id,
          decision,
          approver_id: approverId,
          comments: comments || undefined
        })
      });

      if (!response.ok) throw new Error('Failed to process approval');

      const result: ApprovalResult = await response.json();

      if (result.success) {
        setSelectedRequest(null);
        setComments('');
        await fetchRequests();
        await fetchStats();
        onApprovalComplete?.(result);
      } else {
        setError(result.message);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to process approval');
    } finally {
      setIsProcessing(false);
    }
  };

  const handleEscalate = async () => {
    if (!selectedRequest) return;

    setIsProcessing(true);
    try {
      const response = await fetch(`${apiBaseUrl}/escalate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          request_id: selectedRequest.id,
          reason: 'manual',
          triggered_by: approverId
        })
      });

      if (!response.ok) throw new Error('Failed to escalate request');

      setSelectedRequest(null);
      await fetchRequests();
      await fetchStats();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to escalate');
    } finally {
      setIsProcessing(false);
    }
  };

  const formatTimeRemaining = (request: ApprovalRequest): string => {
    const created = new Date(request.created_at);
    const deadline = new Date(created.getTime() + request.timeout_seconds * 1000);
    const remaining = deadline.getTime() - Date.now();

    if (remaining <= 0) return 'Overdue';

    const hours = Math.floor(remaining / (1000 * 60 * 60));
    const minutes = Math.floor((remaining % (1000 * 60 * 60)) / (1000 * 60));

    if (hours > 0) return `${hours}h ${minutes}m remaining`;
    return `${minutes}m remaining`;
  };

  const isOverdue = (request: ApprovalRequest): boolean => {
    const created = new Date(request.created_at);
    const deadline = new Date(created.getTime() + request.timeout_seconds * 1000);
    return Date.now() > deadline.getTime();
  };

  if (isLoading) {
    return (
      <div className="approval-dashboard loading">
        <div className="loading-spinner" />
        <p>Loading approval requests...</p>
      </div>
    );
  }

  return (
    <div className="approval-dashboard">
      <header className="dashboard-header">
        <h1>Human-in-the-Loop Approval Dashboard</h1>
        <p className="subtitle">EU AI Act Article 14 Compliance</p>
      </header>

      {error && (
        <div className="error-banner" role="alert">
          <span>{error}</span>
          <button onClick={() => setError(null)} aria-label="Dismiss error">
            &times;
          </button>
        </div>
      )}

      {stats && (
        <section className="stats-panel" aria-label="Queue Statistics">
          <div className="stat-card">
            <span className="stat-value">{stats.total_pending}</span>
            <span className="stat-label">Pending</span>
          </div>
          <div className="stat-card warning">
            <span className="stat-value">{stats.overdue_count}</span>
            <span className="stat-label">Overdue</span>
          </div>
          <div className="stat-card">
            <span className="stat-value">
              {Math.round(stats.average_wait_seconds / 60)}m
            </span>
            <span className="stat-label">Avg Wait</span>
          </div>
          <div className="stat-card">
            <span className="stat-value">
              {Math.round(stats.oldest_request_age_seconds / 3600)}h
            </span>
            <span className="stat-label">Oldest</span>
          </div>
        </section>
      )}

      <section className="filters-panel" aria-label="Filters">
        <div className="filter-group">
          <label htmlFor="priority-filter">Priority:</label>
          <select
            id="priority-filter"
            value={filter.priority || ''}
            onChange={(e) => setFilter(f => ({
              ...f,
              priority: e.target.value ? parseInt(e.target.value) : null
            }))}
          >
            <option value="">All</option>
            <option value="4">Critical</option>
            <option value="3">High</option>
            <option value="2">Normal</option>
            <option value="1">Low</option>
          </select>
        </div>

        <div className="filter-group">
          <label htmlFor="type-filter">Type:</label>
          <select
            id="type-filter"
            value={filter.type || ''}
            onChange={(e) => setFilter(f => ({
              ...f,
              type: (e.target.value as ApprovalType) || null
            }))}
          >
            <option value="">All</option>
            <option value="critical">Critical</option>
            <option value="compliance">Compliance</option>
            <option value="decision">Decision</option>
            <option value="override">Override</option>
          </select>
        </div>

        <div className="filter-group">
          <label>
            <input
              type="checkbox"
              checked={filter.showOverdueOnly}
              onChange={(e) => setFilter(f => ({
                ...f,
                showOverdueOnly: e.target.checked
              }))}
            />
            Overdue only
          </label>
        </div>

        <button
          className="refresh-btn"
          onClick={() => { fetchRequests(); fetchStats(); }}
          aria-label="Refresh data"
        >
          Refresh
        </button>
      </section>

      <main className="dashboard-content">
        <section className="requests-list" aria-label="Approval Requests">
          <h2>Pending Requests ({requests.length})</h2>

          {requests.length === 0 ? (
            <div className="empty-state">
              <p>No pending approval requests</p>
            </div>
          ) : (
            <ul className="request-cards">
              {requests.map(request => (
                <li
                  key={request.id}
                  className={`request-card ${selectedRequest?.id === request.id ? 'selected' : ''} ${isOverdue(request) ? 'overdue' : ''}`}
                  onClick={() => setSelectedRequest(request)}
                  role="button"
                  tabIndex={0}
                  onKeyDown={(e) => e.key === 'Enter' && setSelectedRequest(request)}
                  aria-selected={selectedRequest?.id === request.id}
                >
                  <div className="card-header">
                    <span
                      className="priority-badge"
                      style={{ backgroundColor: PRIORITY_COLORS[request.priority] }}
                    >
                      {PRIORITY_LABELS[request.priority]}
                    </span>
                    <span className="type-badge">
                      {TYPE_LABELS[request.request_type]}
                    </span>
                    {request.escalation_level > 0 && (
                      <span className="escalation-badge">
                        L{request.escalation_level}
                      </span>
                    )}
                  </div>

                  <div className="card-body">
                    <p className="request-id">{request.id}</p>
                    <p className="requester">From: {request.requester}</p>
                    <p className={`time-remaining ${isOverdue(request) ? 'overdue' : ''}`}>
                      {formatTimeRemaining(request)}
                    </p>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </section>

        {selectedRequest && (
          <section className="request-detail" aria-label="Request Details">
            <h2>Request Details</h2>

            <div className="detail-header">
              <h3>{selectedRequest.id}</h3>
              <span
                className="status-badge"
                style={{ backgroundColor: STATUS_COLORS[selectedRequest.status] }}
              >
                {selectedRequest.status}
              </span>
            </div>

            <div className="detail-grid">
              <div className="detail-item">
                <label>Type</label>
                <span>{TYPE_LABELS[selectedRequest.request_type]}</span>
              </div>
              <div className="detail-item">
                <label>Priority</label>
                <span style={{ color: PRIORITY_COLORS[selectedRequest.priority] }}>
                  {PRIORITY_LABELS[selectedRequest.priority]}
                </span>
              </div>
              <div className="detail-item">
                <label>Requester</label>
                <span>{selectedRequest.requester}</span>
              </div>
              <div className="detail-item">
                <label>Workflow</label>
                <span>{selectedRequest.workflow_id}</span>
              </div>
              <div className="detail-item">
                <label>Created</label>
                <span>{new Date(selectedRequest.created_at).toLocaleString()}</span>
              </div>
              <div className="detail-item">
                <label>Escalation Level</label>
                <span>{selectedRequest.escalation_level}</span>
              </div>
            </div>

            <div className="context-section">
              <h4>Decision Context</h4>
              <pre className="context-json">
                {JSON.stringify(selectedRequest.context, null, 2)}
              </pre>
            </div>

            <div className="assigned-section">
              <h4>Assigned Approvers</h4>
              <ul className="approver-list">
                {selectedRequest.assigned_to.map((approver, idx) => (
                  <li key={idx} className={approver === approverId ? 'current' : ''}>
                    {approver}
                    {approver === approverId && ' (You)'}
                  </li>
                ))}
              </ul>
            </div>

            <div className="comments-section">
              <label htmlFor="approval-comments">Comments (optional)</label>
              <textarea
                id="approval-comments"
                value={comments}
                onChange={(e) => setComments(e.target.value)}
                placeholder="Add rationale for your decision..."
                rows={3}
              />
            </div>

            <div className="action-buttons">
              <button
                className="approve-btn"
                onClick={() => handleApproval('approved')}
                disabled={isProcessing}
              >
                {isProcessing ? 'Processing...' : 'Approve'}
              </button>
              <button
                className="reject-btn"
                onClick={() => handleApproval('rejected')}
                disabled={isProcessing}
              >
                {isProcessing ? 'Processing...' : 'Reject'}
              </button>
              <button
                className="escalate-btn"
                onClick={handleEscalate}
                disabled={isProcessing}
              >
                Escalate
              </button>
              <button
                className="cancel-btn"
                onClick={() => {
                  setSelectedRequest(null);
                  setComments('');
                }}
                disabled={isProcessing}
              >
                Cancel
              </button>
            </div>
          </section>
        )}
      </main>

      <style>{`
        .approval-dashboard {
          font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
          max-width: 1400px;
          margin: 0 auto;
          padding: 20px;
          background: #f9fafb;
          min-height: 100vh;
        }

        .approval-dashboard.loading {
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          min-height: 400px;
        }

        .loading-spinner {
          width: 40px;
          height: 40px;
          border: 3px solid #e5e7eb;
          border-top-color: #3b82f6;
          border-radius: 50%;
          animation: spin 1s linear infinite;
        }

        @keyframes spin {
          to { transform: rotate(360deg); }
        }

        .dashboard-header {
          text-align: center;
          margin-bottom: 24px;
        }

        .dashboard-header h1 {
          margin: 0;
          color: #111827;
          font-size: 28px;
        }

        .dashboard-header .subtitle {
          margin: 8px 0 0;
          color: #6b7280;
          font-size: 14px;
        }

        .error-banner {
          background: #fef2f2;
          border: 1px solid #fecaca;
          color: #dc2626;
          padding: 12px 16px;
          border-radius: 8px;
          margin-bottom: 16px;
          display: flex;
          justify-content: space-between;
          align-items: center;
        }

        .error-banner button {
          background: none;
          border: none;
          font-size: 20px;
          cursor: pointer;
          color: #dc2626;
        }

        .stats-panel {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
          gap: 16px;
          margin-bottom: 24px;
        }

        .stat-card {
          background: white;
          border-radius: 12px;
          padding: 20px;
          text-align: center;
          box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
        }

        .stat-card.warning .stat-value {
          color: #f59e0b;
        }

        .stat-value {
          display: block;
          font-size: 32px;
          font-weight: 700;
          color: #111827;
        }

        .stat-label {
          display: block;
          font-size: 14px;
          color: #6b7280;
          margin-top: 4px;
        }

        .filters-panel {
          display: flex;
          gap: 16px;
          align-items: center;
          flex-wrap: wrap;
          background: white;
          padding: 16px;
          border-radius: 12px;
          margin-bottom: 24px;
          box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
        }

        .filter-group {
          display: flex;
          align-items: center;
          gap: 8px;
        }

        .filter-group label {
          font-size: 14px;
          color: #374151;
        }

        .filter-group select {
          padding: 8px 12px;
          border: 1px solid #d1d5db;
          border-radius: 6px;
          font-size: 14px;
        }

        .refresh-btn {
          margin-left: auto;
          padding: 8px 16px;
          background: #3b82f6;
          color: white;
          border: none;
          border-radius: 6px;
          cursor: pointer;
          font-size: 14px;
        }

        .refresh-btn:hover {
          background: #2563eb;
        }

        .dashboard-content {
          display: grid;
          grid-template-columns: 1fr 1fr;
          gap: 24px;
        }

        @media (max-width: 1024px) {
          .dashboard-content {
            grid-template-columns: 1fr;
          }
        }

        .requests-list {
          background: white;
          border-radius: 12px;
          padding: 20px;
          box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
        }

        .requests-list h2 {
          margin: 0 0 16px;
          font-size: 18px;
          color: #111827;
        }

        .empty-state {
          text-align: center;
          padding: 40px;
          color: #6b7280;
        }

        .request-cards {
          list-style: none;
          padding: 0;
          margin: 0;
          display: flex;
          flex-direction: column;
          gap: 12px;
          max-height: 600px;
          overflow-y: auto;
        }

        .request-card {
          border: 2px solid #e5e7eb;
          border-radius: 8px;
          padding: 16px;
          cursor: pointer;
          transition: all 0.2s;
        }

        .request-card:hover {
          border-color: #3b82f6;
          background: #f8fafc;
        }

        .request-card.selected {
          border-color: #3b82f6;
          background: #eff6ff;
        }

        .request-card.overdue {
          border-color: #fecaca;
          background: #fef2f2;
        }

        .card-header {
          display: flex;
          gap: 8px;
          margin-bottom: 12px;
        }

        .priority-badge,
        .type-badge,
        .escalation-badge,
        .status-badge {
          padding: 4px 8px;
          border-radius: 4px;
          font-size: 12px;
          font-weight: 600;
          color: white;
        }

        .type-badge {
          background: #6366f1;
        }

        .escalation-badge {
          background: #8b5cf6;
        }

        .card-body .request-id {
          font-family: monospace;
          font-size: 13px;
          color: #374151;
          margin: 0 0 4px;
        }

        .card-body .requester {
          font-size: 13px;
          color: #6b7280;
          margin: 0 0 4px;
        }

        .card-body .time-remaining {
          font-size: 13px;
          color: #059669;
          margin: 0;
        }

        .card-body .time-remaining.overdue {
          color: #dc2626;
          font-weight: 600;
        }

        .request-detail {
          background: white;
          border-radius: 12px;
          padding: 20px;
          box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
        }

        .request-detail h2 {
          margin: 0 0 16px;
          font-size: 18px;
          color: #111827;
        }

        .detail-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 20px;
        }

        .detail-header h3 {
          margin: 0;
          font-family: monospace;
          font-size: 16px;
        }

        .detail-grid {
          display: grid;
          grid-template-columns: repeat(2, 1fr);
          gap: 16px;
          margin-bottom: 20px;
        }

        .detail-item label {
          display: block;
          font-size: 12px;
          color: #6b7280;
          margin-bottom: 4px;
        }

        .detail-item span {
          font-size: 14px;
          color: #111827;
        }

        .context-section,
        .assigned-section,
        .comments-section {
          margin-bottom: 20px;
        }

        .context-section h4,
        .assigned-section h4 {
          font-size: 14px;
          color: #374151;
          margin: 0 0 8px;
        }

        .context-json {
          background: #f3f4f6;
          padding: 12px;
          border-radius: 6px;
          font-size: 12px;
          overflow-x: auto;
          max-height: 200px;
        }

        .approver-list {
          list-style: none;
          padding: 0;
          margin: 0;
        }

        .approver-list li {
          padding: 8px 12px;
          background: #f3f4f6;
          border-radius: 4px;
          margin-bottom: 4px;
          font-size: 14px;
        }

        .approver-list li.current {
          background: #dbeafe;
          color: #1d4ed8;
          font-weight: 500;
        }

        .comments-section label {
          display: block;
          font-size: 14px;
          color: #374151;
          margin-bottom: 8px;
        }

        .comments-section textarea {
          width: 100%;
          padding: 12px;
          border: 1px solid #d1d5db;
          border-radius: 6px;
          font-size: 14px;
          resize: vertical;
        }

        .action-buttons {
          display: flex;
          gap: 12px;
          flex-wrap: wrap;
        }

        .action-buttons button {
          padding: 12px 24px;
          border: none;
          border-radius: 6px;
          font-size: 14px;
          font-weight: 600;
          cursor: pointer;
          transition: opacity 0.2s;
        }

        .action-buttons button:disabled {
          opacity: 0.6;
          cursor: not-allowed;
        }

        .approve-btn {
          background: #10b981;
          color: white;
        }

        .approve-btn:hover:not(:disabled) {
          background: #059669;
        }

        .reject-btn {
          background: #ef4444;
          color: white;
        }

        .reject-btn:hover:not(:disabled) {
          background: #dc2626;
        }

        .escalate-btn {
          background: #8b5cf6;
          color: white;
        }

        .escalate-btn:hover:not(:disabled) {
          background: #7c3aed;
        }

        .cancel-btn {
          background: #e5e7eb;
          color: #374151;
        }

        .cancel-btn:hover:not(:disabled) {
          background: #d1d5db;
        }
      `}</style>
    </div>
  );
};

export default ApprovalDashboard;
