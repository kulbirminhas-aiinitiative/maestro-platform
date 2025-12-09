/**
 * MD-2371: Mission Documents Panel
 * Implements AC-7: Frontend Real-time Reflection
 *
 * React component to display generated documents in real-time.
 */

import React, { useState, useEffect, useCallback } from 'react';

// Types
interface DocumentType {
  type: 'prd' | 'techDesign' | 'testPlan' | 'userStories' | 'adr' | 'runbook' | 'deploymentGuide';
  label: string;
  icon: string;
}

interface GeneratedDocument {
  id: string;
  documentType: DocumentType['type'];
  title: string;
  confluenceUrl?: string;
  personaName: string;
  aiSummary?: string;
  createdAt: Date;
  status: 'generating' | 'complete' | 'error';
  progress?: number;
  error?: string;
}

interface MissionDocumentsPanelProps {
  missionId: string;
  teamId: string;
  onDocumentClick?: (document: GeneratedDocument) => void;
  className?: string;
}

// Document type metadata
const DOCUMENT_TYPES: DocumentType[] = [
  { type: 'prd', label: 'Product Requirements', icon: '📋' },
  { type: 'techDesign', label: 'Technical Design', icon: '🏗️' },
  { type: 'testPlan', label: 'Test Plan', icon: '🧪' },
  { type: 'userStories', label: 'User Stories', icon: '📝' },
  { type: 'adr', label: 'Architecture Decision', icon: '🏛️' },
  { type: 'runbook', label: 'Operations Runbook', icon: '📖' },
  { type: 'deploymentGuide', label: 'Deployment Guide', icon: '🚀' },
];

/**
 * Mission Documents Panel Component
 * Displays real-time document generation progress and results
 */
export const MissionDocumentsPanel: React.FC<MissionDocumentsPanelProps> = ({
  missionId,
  teamId,
  onDocumentClick,
  className = '',
}) => {
  const [documents, setDocuments] = useState<GeneratedDocument[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedFilter, setSelectedFilter] = useState<DocumentType['type'] | 'all'>('all');

  // Fetch initial documents
  useEffect(() => {
    const fetchDocuments = async () => {
      try {
        setIsLoading(true);
        const response = await fetch(`/api/missions/${missionId}/documents`);

        if (!response.ok) {
          throw new Error('Failed to fetch documents');
        }

        const data = await response.json();
        setDocuments(data.documents || []);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'An error occurred');
      } finally {
        setIsLoading(false);
      }
    };

    fetchDocuments();
  }, [missionId]);

  // WebSocket subscription for real-time updates
  useEffect(() => {
    // In production, this would connect to the actual WebSocket server
    const mockWebSocket = {
      subscribe: (callback: (event: any) => void) => {
        // Simulate WebSocket events for demonstration
        return () => {}; // Cleanup function
      },
    };

    const handleEvent = (event: any) => {
      switch (event.type) {
        case 'document:generating':
          handleDocumentGenerating(event.payload);
          break;
        case 'document:progress':
          handleDocumentProgress(event.payload);
          break;
        case 'document:complete':
          handleDocumentComplete(event.payload);
          break;
        case 'document:error':
          handleDocumentError(event.payload);
          break;
      }
    };

    const unsubscribe = mockWebSocket.subscribe(handleEvent);

    return () => {
      unsubscribe();
    };
  }, [missionId]);

  const handleDocumentGenerating = useCallback((payload: any) => {
    setDocuments((prev) => [
      ...prev,
      {
        id: `temp_${payload.documentType}`,
        documentType: payload.documentType,
        title: `Generating ${getDocumentTypeLabel(payload.documentType)}...`,
        personaName: payload.persona,
        status: 'generating',
        progress: 0,
        createdAt: new Date(),
      },
    ]);
  }, []);

  const handleDocumentProgress = useCallback((payload: any) => {
    setDocuments((prev) =>
      prev.map((doc) =>
        doc.documentType === payload.documentType && doc.status === 'generating'
          ? { ...doc, progress: payload.progress }
          : doc
      )
    );
  }, []);

  const handleDocumentComplete = useCallback((payload: any) => {
    setDocuments((prev) =>
      prev.map((doc) =>
        doc.documentType === payload.documentType && doc.status === 'generating'
          ? {
              ...doc,
              id: payload.documentId,
              status: 'complete',
              confluenceUrl: payload.confluenceUrl,
              progress: 100,
            }
          : doc
      )
    );
  }, []);

  const handleDocumentError = useCallback((payload: any) => {
    setDocuments((prev) =>
      prev.map((doc) =>
        doc.documentType === payload.documentType && doc.status === 'generating'
          ? {
              ...doc,
              status: 'error',
              error: payload.error,
            }
          : doc
      )
    );
  }, []);

  const getDocumentTypeLabel = (type: DocumentType['type']): string => {
    return DOCUMENT_TYPES.find((dt) => dt.type === type)?.label || type;
  };

  const getDocumentTypeIcon = (type: DocumentType['type']): string => {
    return DOCUMENT_TYPES.find((dt) => dt.type === type)?.icon || '📄';
  };

  const filteredDocuments = documents.filter(
    (doc) => selectedFilter === 'all' || doc.documentType === selectedFilter
  );

  const stats = {
    total: documents.length,
    complete: documents.filter((d) => d.status === 'complete').length,
    generating: documents.filter((d) => d.status === 'generating').length,
    errors: documents.filter((d) => d.status === 'error').length,
  };

  if (isLoading) {
    return (
      <div className={`mission-documents-panel loading ${className}`}>
        <div className="loading-spinner">Loading documents...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className={`mission-documents-panel error ${className}`}>
        <div className="error-message">
          <span className="error-icon">⚠️</span>
          <span>{error}</span>
          <button onClick={() => window.location.reload()}>Retry</button>
        </div>
      </div>
    );
  }

  return (
    <div className={`mission-documents-panel ${className}`}>
      {/* Header */}
      <div className="panel-header">
        <h3>Generated Documents</h3>
        <div className="stats">
          <span className="stat complete">{stats.complete} Complete</span>
          {stats.generating > 0 && (
            <span className="stat generating">{stats.generating} Generating</span>
          )}
          {stats.errors > 0 && (
            <span className="stat error">{stats.errors} Failed</span>
          )}
        </div>
      </div>

      {/* Filter */}
      <div className="filter-bar">
        <button
          className={`filter-btn ${selectedFilter === 'all' ? 'active' : ''}`}
          onClick={() => setSelectedFilter('all')}
        >
          All
        </button>
        {DOCUMENT_TYPES.map((dt) => (
          <button
            key={dt.type}
            className={`filter-btn ${selectedFilter === dt.type ? 'active' : ''}`}
            onClick={() => setSelectedFilter(dt.type)}
          >
            {dt.icon} {dt.label}
          </button>
        ))}
      </div>

      {/* Document List */}
      <div className="document-list">
        {filteredDocuments.length === 0 ? (
          <div className="empty-state">
            <span className="empty-icon">📭</span>
            <p>No documents generated yet</p>
            <p className="hint">Documents will appear here as they are generated</p>
          </div>
        ) : (
          filteredDocuments.map((doc) => (
            <DocumentCard
              key={doc.id}
              document={doc}
              onClick={onDocumentClick}
            />
          ))
        )}
      </div>
    </div>
  );
};

/**
 * Document Card Component
 */
interface DocumentCardProps {
  document: GeneratedDocument;
  onClick?: (document: GeneratedDocument) => void;
}

const DocumentCard: React.FC<DocumentCardProps> = ({ document, onClick }) => {
  const getStatusColor = (status: GeneratedDocument['status']): string => {
    switch (status) {
      case 'complete':
        return 'green';
      case 'generating':
        return 'blue';
      case 'error':
        return 'red';
      default:
        return 'gray';
    }
  };

  const getStatusIcon = (status: GeneratedDocument['status']): string => {
    switch (status) {
      case 'complete':
        return '✅';
      case 'generating':
        return '⏳';
      case 'error':
        return '❌';
      default:
        return '⚪';
    }
  };

  const getDocumentIcon = (type: DocumentType['type']): string => {
    const iconMap: Record<DocumentType['type'], string> = {
      prd: '📋',
      techDesign: '🏗️',
      testPlan: '🧪',
      userStories: '📝',
      adr: '🏛️',
      runbook: '📖',
      deploymentGuide: '🚀',
    };
    return iconMap[type] || '📄';
  };

  return (
    <div
      className={`document-card ${document.status}`}
      onClick={() => onClick?.(document)}
      role="button"
      tabIndex={0}
    >
      <div className="card-header">
        <span className="document-icon">{getDocumentIcon(document.documentType)}</span>
        <span className="document-title">{document.title}</span>
        <span className={`status-badge ${document.status}`}>
          {getStatusIcon(document.status)}
        </span>
      </div>

      {document.status === 'generating' && document.progress !== undefined && (
        <div className="progress-bar">
          <div
            className="progress-fill"
            style={{ width: `${document.progress}%` }}
          />
          <span className="progress-text">{document.progress}%</span>
        </div>
      )}

      <div className="card-meta">
        <span className="persona">By: {document.personaName}</span>
        <span className="timestamp">
          {document.createdAt.toLocaleString()}
        </span>
      </div>

      {document.aiSummary && (
        <div className="ai-summary">
          <span className="summary-label">AI Summary:</span>
          <p>{document.aiSummary}</p>
        </div>
      )}

      {document.confluenceUrl && (
        <a
          href={document.confluenceUrl}
          target="_blank"
          rel="noopener noreferrer"
          className="confluence-link"
          onClick={(e) => e.stopPropagation()}
        >
          View in Confluence →
        </a>
      )}

      {document.error && (
        <div className="error-details">
          <span className="error-icon">⚠️</span>
          <span>{document.error}</span>
        </div>
      )}
    </div>
  );
};

/**
 * CSS Styles (would typically be in a separate .css or .scss file)
 */
export const styles = `
.mission-documents-panel {
  background: #ffffff;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
  padding: 16px;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.panel-header h3 {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
}

.stats {
  display: flex;
  gap: 12px;
}

.stat {
  font-size: 12px;
  padding: 4px 8px;
  border-radius: 4px;
}

.stat.complete { background: #e6f7e6; color: #2e7d32; }
.stat.generating { background: #e3f2fd; color: #1565c0; }
.stat.error { background: #ffebee; color: #c62828; }

.filter-bar {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 16px;
  padding-bottom: 16px;
  border-bottom: 1px solid #e0e0e0;
}

.filter-btn {
  padding: 6px 12px;
  border: 1px solid #e0e0e0;
  border-radius: 16px;
  background: #ffffff;
  cursor: pointer;
  font-size: 12px;
  transition: all 0.2s;
}

.filter-btn:hover { background: #f5f5f5; }
.filter-btn.active { background: #1976d2; color: #ffffff; border-color: #1976d2; }

.document-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.document-card {
  padding: 16px;
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
}

.document-card:hover { box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1); }
.document-card.generating { border-left: 3px solid #1976d2; }
.document-card.complete { border-left: 3px solid #2e7d32; }
.document-card.error { border-left: 3px solid #c62828; }

.card-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.document-icon { font-size: 20px; }
.document-title { flex: 1; font-weight: 500; }

.progress-bar {
  height: 8px;
  background: #e0e0e0;
  border-radius: 4px;
  overflow: hidden;
  margin-bottom: 8px;
  position: relative;
}

.progress-fill {
  height: 100%;
  background: #1976d2;
  transition: width 0.3s;
}

.card-meta {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
  color: #666;
}

.ai-summary {
  margin-top: 8px;
  padding: 8px;
  background: #f5f5f5;
  border-radius: 4px;
  font-size: 12px;
}

.confluence-link {
  display: inline-block;
  margin-top: 8px;
  color: #1976d2;
  text-decoration: none;
  font-size: 12px;
}

.confluence-link:hover { text-decoration: underline; }

.error-details {
  margin-top: 8px;
  padding: 8px;
  background: #ffebee;
  border-radius: 4px;
  color: #c62828;
  font-size: 12px;
}

.empty-state {
  text-align: center;
  padding: 40px;
  color: #666;
}

.empty-icon { font-size: 48px; }
.hint { font-size: 12px; color: #999; }

.loading-spinner {
  text-align: center;
  padding: 40px;
  color: #666;
}
`;

export default MissionDocumentsPanel;
