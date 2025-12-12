/**
 * RAG Configuration Dashboard
 *
 * Comprehensive dashboard for configuring and monitoring RAG (Retrieval-Augmented
 * Generation) integration for personas. Provides controls for knowledge index
 * management, connector configuration, and context enhancement settings.
 *
 * Related EPIC: MD-3026 - RAG Persona Integration
 */

import React, { useState, useEffect, useCallback, useMemo } from 'react';

// Types for RAG configuration
interface RAGProviderConfig {
  providerType: 'pinecone' | 'weaviate' | 'qdrant' | 'chroma' | 'faiss' | 'elasticsearch' | 'milvus' | 'custom';
  apiKey?: string;
  apiEndpoint?: string;
  indexName: string;
  namespace: string;
  embeddingModel: string;
  embeddingDimension: number;
  similarityMetric: 'cosine' | 'euclidean' | 'dot_product';
}

interface QueryConfig {
  strategy: 'semantic' | 'keyword' | 'hybrid' | 'mmr' | 'reranked';
  defaultTopK: number;
  maxTopK: number;
  minSimilarityThreshold: number;
  timeoutSeconds: number;
  retryAttempts: number;
  cacheEnabled: boolean;
  cacheTTLSeconds: number;
}

interface ChunkingConfig {
  strategy: 'fixed_size' | 'sentence' | 'paragraph' | 'semantic' | 'recursive' | 'code_aware' | 'hybrid';
  chunkSize: number;
  chunkOverlap: number;
  minChunkSize: number;
  maxChunkSize: number;
}

interface EnhancementConfig {
  strategy: 'prepend' | 'append' | 'inline' | 'structured' | 'summarize' | 'selective';
  contextFormat: 'plain' | 'markdown' | 'json' | 'bulleted';
  maxContextTokens: number;
  maxResultsToInclude: number;
  minRelevanceScore: number;
  includeSources: boolean;
  includeConfidence: boolean;
  deduplicate: boolean;
}

interface IndexStats {
  indexName: string;
  totalVectors: number;
  dimension: number;
  namespaces: string[];
  indexFullness: number;
  lastUpdated?: string;
}

interface IndexedDocument {
  documentId: string;
  title?: string;
  source?: string;
  chunkCount: number;
  indexedAt: string;
  status: string;
}

interface IndexHealth {
  status: 'active' | 'building' | 'updating' | 'stale' | 'error' | 'archived';
  totalDocuments: number;
  totalChunks: number;
  indexSizeMB: number;
  lastUpdated?: string;
  staleDocuments: number;
  errorCount: number;
  recommendations: string[];
}

interface ConnectorMetrics {
  status: 'disconnected' | 'connecting' | 'connected' | 'error' | 'degraded';
  queryCount: number;
  averageLatencyMs: number;
  cacheHitRate?: number;
  lastError?: string;
}

interface RAGConfigDashboardProps {
  personaId?: string;
  onConfigChange?: (config: Partial<RAGProviderConfig & QueryConfig & EnhancementConfig>) => void;
  onIndexDocument?: (file: File) => Promise<void>;
  onRemoveDocument?: (documentId: string) => Promise<void>;
  readOnly?: boolean;
}

// Provider options
const PROVIDER_OPTIONS = [
  { value: 'chroma', label: 'Chroma', description: 'Open-source embedding database' },
  { value: 'pinecone', label: 'Pinecone', description: 'Managed vector database' },
  { value: 'weaviate', label: 'Weaviate', description: 'Open-source vector search engine' },
  { value: 'qdrant', label: 'Qdrant', description: 'Vector similarity search engine' },
  { value: 'faiss', label: 'FAISS', description: 'Facebook AI Similarity Search' },
  { value: 'elasticsearch', label: 'Elasticsearch', description: 'Distributed search engine' },
  { value: 'milvus', label: 'Milvus', description: 'Open-source vector database' },
  { value: 'custom', label: 'Custom', description: 'Custom implementation' },
] as const;

const EMBEDDING_MODELS = [
  { value: 'text-embedding-3-small', label: 'OpenAI text-embedding-3-small', dimension: 1536 },
  { value: 'text-embedding-3-large', label: 'OpenAI text-embedding-3-large', dimension: 3072 },
  { value: 'text-embedding-ada-002', label: 'OpenAI ada-002', dimension: 1536 },
  { value: 'sentence-transformers/all-MiniLM-L6-v2', label: 'MiniLM-L6-v2', dimension: 384 },
  { value: 'sentence-transformers/all-mpnet-base-v2', label: 'MPNet Base v2', dimension: 768 },
  { value: 'custom', label: 'Custom Model', dimension: 0 },
] as const;

const QUERY_STRATEGIES = [
  { value: 'semantic', label: 'Semantic', description: 'Pure semantic similarity search' },
  { value: 'hybrid', label: 'Hybrid', description: 'Combined semantic + keyword matching' },
  { value: 'mmr', label: 'MMR', description: 'Maximum Marginal Relevance for diversity' },
  { value: 'keyword', label: 'Keyword', description: 'Keyword-based matching' },
  { value: 'reranked', label: 'Reranked', description: 'Initial retrieval with reranking' },
] as const;

const CHUNKING_STRATEGIES = [
  { value: 'recursive', label: 'Recursive', description: 'Hierarchical splitting with separators' },
  { value: 'sentence', label: 'Sentence', description: 'Sentence-based splitting' },
  { value: 'paragraph', label: 'Paragraph', description: 'Paragraph-based splitting' },
  { value: 'fixed_size', label: 'Fixed Size', description: 'Fixed character count' },
  { value: 'code_aware', label: 'Code-Aware', description: 'Preserves code structure' },
  { value: 'semantic', label: 'Semantic', description: 'Semantic similarity-based' },
] as const;

const ENHANCEMENT_STRATEGIES = [
  { value: 'structured', label: 'Structured', description: 'Organized format with sections' },
  { value: 'prepend', label: 'Prepend', description: 'Add context before prompt' },
  { value: 'append', label: 'Append', description: 'Add context after prompt' },
  { value: 'inline', label: 'Inline', description: 'Inject at marked positions' },
  { value: 'summarize', label: 'Summarize', description: 'Summarize before injection' },
  { value: 'selective', label: 'Selective', description: 'Only most relevant pieces' },
] as const;

// Status Badge Component
const StatusBadge: React.FC<{ status: string; size?: 'sm' | 'md' | 'lg' }> = ({
  status,
  size = 'md',
}) => {
  const statusColors: Record<string, { bg: string; text: string; dot: string }> = {
    connected: { bg: 'bg-green-100', text: 'text-green-800', dot: 'bg-green-500' },
    active: { bg: 'bg-green-100', text: 'text-green-800', dot: 'bg-green-500' },
    disconnected: { bg: 'bg-gray-100', text: 'text-gray-800', dot: 'bg-gray-500' },
    connecting: { bg: 'bg-yellow-100', text: 'text-yellow-800', dot: 'bg-yellow-500' },
    building: { bg: 'bg-blue-100', text: 'text-blue-800', dot: 'bg-blue-500' },
    updating: { bg: 'bg-blue-100', text: 'text-blue-800', dot: 'bg-blue-500' },
    error: { bg: 'bg-red-100', text: 'text-red-800', dot: 'bg-red-500' },
    degraded: { bg: 'bg-orange-100', text: 'text-orange-800', dot: 'bg-orange-500' },
    stale: { bg: 'bg-yellow-100', text: 'text-yellow-800', dot: 'bg-yellow-500' },
    archived: { bg: 'bg-gray-100', text: 'text-gray-600', dot: 'bg-gray-400' },
  };

  const colors = statusColors[status.toLowerCase()] || statusColors.disconnected;
  const sizeClasses = {
    sm: 'px-2 py-0.5 text-xs',
    md: 'px-2.5 py-1 text-sm',
    lg: 'px-3 py-1.5 text-base',
  };

  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full font-medium ${colors.bg} ${colors.text} ${sizeClasses[size]}`}
    >
      <span className={`w-2 h-2 rounded-full ${colors.dot} animate-pulse`} />
      {status.charAt(0).toUpperCase() + status.slice(1)}
    </span>
  );
};

// Metric Card Component
const MetricCard: React.FC<{
  title: string;
  value: string | number;
  subtitle?: string;
  trend?: 'up' | 'down' | 'neutral';
  icon?: React.ReactNode;
}> = ({ title, value, subtitle, trend, icon }) => {
  const trendColors = {
    up: 'text-green-600',
    down: 'text-red-600',
    neutral: 'text-gray-500',
  };

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-4 shadow-sm hover:shadow-md transition-shadow">
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <p className="text-sm font-medium text-gray-600">{title}</p>
          <p className="mt-1 text-2xl font-semibold text-gray-900">{value}</p>
          {subtitle && (
            <p className={`mt-1 text-sm ${trend ? trendColors[trend] : 'text-gray-500'}`}>
              {subtitle}
            </p>
          )}
        </div>
        {icon && <div className="text-gray-400">{icon}</div>}
      </div>
    </div>
  );
};

// Configuration Section Component
const ConfigSection: React.FC<{
  title: string;
  description?: string;
  children: React.ReactNode;
  collapsible?: boolean;
  defaultOpen?: boolean;
}> = ({ title, description, children, collapsible = false, defaultOpen = true }) => {
  const [isOpen, setIsOpen] = useState(defaultOpen);

  return (
    <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
      <div
        className={`px-4 py-3 bg-gray-50 border-b border-gray-200 ${
          collapsible ? 'cursor-pointer hover:bg-gray-100' : ''
        }`}
        onClick={() => collapsible && setIsOpen(!isOpen)}
      >
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-base font-semibold text-gray-900">{title}</h3>
            {description && <p className="mt-0.5 text-sm text-gray-600">{description}</p>}
          </div>
          {collapsible && (
            <svg
              className={`w-5 h-5 text-gray-500 transition-transform ${isOpen ? 'rotate-180' : ''}`}
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
            </svg>
          )}
        </div>
      </div>
      {(!collapsible || isOpen) && <div className="p-4">{children}</div>}
    </div>
  );
};

// Form Input Components
const FormField: React.FC<{
  label: string;
  htmlFor: string;
  description?: string;
  required?: boolean;
  error?: string;
  children: React.ReactNode;
}> = ({ label, htmlFor, description, required, error, children }) => (
  <div className="space-y-1">
    <label htmlFor={htmlFor} className="block text-sm font-medium text-gray-700">
      {label}
      {required && <span className="text-red-500 ml-1">*</span>}
    </label>
    {children}
    {description && !error && <p className="text-xs text-gray-500">{description}</p>}
    {error && <p className="text-xs text-red-600">{error}</p>}
  </div>
);

const SelectField: React.FC<{
  value: string;
  onChange: (value: string) => void;
  options: readonly { value: string; label: string; description?: string }[];
  disabled?: boolean;
  id?: string;
}> = ({ value, onChange, options, disabled, id }) => (
  <select
    id={id}
    value={value}
    onChange={(e) => onChange(e.target.value)}
    disabled={disabled}
    className="block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 text-sm disabled:bg-gray-100 disabled:cursor-not-allowed"
  >
    {options.map((opt) => (
      <option key={opt.value} value={opt.value}>
        {opt.label}
      </option>
    ))}
  </select>
);

const NumberInput: React.FC<{
  value: number;
  onChange: (value: number) => void;
  min?: number;
  max?: number;
  step?: number;
  disabled?: boolean;
  id?: string;
}> = ({ value, onChange, min, max, step = 1, disabled, id }) => (
  <input
    type="number"
    id={id}
    value={value}
    onChange={(e) => onChange(Number(e.target.value))}
    min={min}
    max={max}
    step={step}
    disabled={disabled}
    className="block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 text-sm disabled:bg-gray-100 disabled:cursor-not-allowed"
  />
);

const TextInput: React.FC<{
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  type?: 'text' | 'password';
  disabled?: boolean;
  id?: string;
}> = ({ value, onChange, placeholder, type = 'text', disabled, id }) => (
  <input
    type={type}
    id={id}
    value={value}
    onChange={(e) => onChange(e.target.value)}
    placeholder={placeholder}
    disabled={disabled}
    className="block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 text-sm disabled:bg-gray-100 disabled:cursor-not-allowed"
  />
);

const Toggle: React.FC<{
  checked: boolean;
  onChange: (checked: boolean) => void;
  disabled?: boolean;
  id?: string;
}> = ({ checked, onChange, disabled, id }) => (
  <button
    type="button"
    id={id}
    role="switch"
    aria-checked={checked}
    onClick={() => !disabled && onChange(!checked)}
    disabled={disabled}
    className={`relative inline-flex h-6 w-11 flex-shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 ${
      checked ? 'bg-blue-600' : 'bg-gray-200'
    } ${disabled ? 'opacity-50 cursor-not-allowed' : ''}`}
  >
    <span
      className={`pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out ${
        checked ? 'translate-x-5' : 'translate-x-0'
      }`}
    />
  </button>
);

const Slider: React.FC<{
  value: number;
  onChange: (value: number) => void;
  min: number;
  max: number;
  step?: number;
  disabled?: boolean;
  showValue?: boolean;
  id?: string;
}> = ({ value, onChange, min, max, step = 1, disabled, showValue = true, id }) => (
  <div className="flex items-center gap-3">
    <input
      type="range"
      id={id}
      value={value}
      onChange={(e) => onChange(Number(e.target.value))}
      min={min}
      max={max}
      step={step}
      disabled={disabled}
      className="flex-1 h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-blue-600 disabled:opacity-50 disabled:cursor-not-allowed"
    />
    {showValue && (
      <span className="text-sm font-medium text-gray-700 min-w-[3rem] text-right">{value}</span>
    )}
  </div>
);

// Document List Component
const DocumentList: React.FC<{
  documents: IndexedDocument[];
  onRemove?: (documentId: string) => void;
  loading?: boolean;
}> = ({ documents, onRemove, loading }) => {
  if (loading) {
    return (
      <div className="flex items-center justify-center py-8">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" />
      </div>
    );
  }

  if (documents.length === 0) {
    return (
      <div className="text-center py-8">
        <svg
          className="mx-auto h-12 w-12 text-gray-400"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={1.5}
            d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
          />
        </svg>
        <p className="mt-2 text-sm text-gray-600">No documents indexed yet</p>
        <p className="text-xs text-gray-500">Upload documents to get started</p>
      </div>
    );
  }

  return (
    <div className="divide-y divide-gray-200 max-h-96 overflow-y-auto">
      {documents.map((doc) => (
        <div
          key={doc.documentId}
          className="flex items-center justify-between py-3 px-2 hover:bg-gray-50"
        >
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium text-gray-900 truncate">
              {doc.title || doc.documentId}
            </p>
            <div className="flex items-center gap-2 mt-1">
              {doc.source && <span className="text-xs text-gray-500">{doc.source}</span>}
              <span className="text-xs text-gray-400">|</span>
              <span className="text-xs text-gray-500">{doc.chunkCount} chunks</span>
              <span className="text-xs text-gray-400">|</span>
              <span className="text-xs text-gray-500">
                {new Date(doc.indexedAt).toLocaleDateString()}
              </span>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <StatusBadge status={doc.status} size="sm" />
            {onRemove && (
              <button
                onClick={() => onRemove(doc.documentId)}
                className="p-1 text-gray-400 hover:text-red-600 transition-colors"
                title="Remove document"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
                  />
                </svg>
              </button>
            )}
          </div>
        </div>
      ))}
    </div>
  );
};

// File Upload Component
const FileUpload: React.FC<{
  onUpload: (file: File) => void;
  accept?: string;
  disabled?: boolean;
}> = ({ onUpload, accept = '.txt,.md,.json,.pdf,.docx', disabled }) => {
  const [isDragging, setIsDragging] = useState(false);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setIsDragging(false);
      if (disabled) return;

      const file = e.dataTransfer.files[0];
      if (file) onUpload(file);
    },
    [onUpload, disabled]
  );

  const handleFileSelect = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      if (file) onUpload(file);
    },
    [onUpload]
  );

  return (
    <div
      onDragOver={(e) => {
        e.preventDefault();
        if (!disabled) setIsDragging(true);
      }}
      onDragLeave={() => setIsDragging(false)}
      onDrop={handleDrop}
      className={`border-2 border-dashed rounded-lg p-6 text-center transition-colors ${
        isDragging
          ? 'border-blue-500 bg-blue-50'
          : 'border-gray-300 hover:border-gray-400'
      } ${disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}`}
    >
      <input
        type="file"
        accept={accept}
        onChange={handleFileSelect}
        disabled={disabled}
        className="hidden"
        id="file-upload"
      />
      <label htmlFor="file-upload" className={disabled ? 'cursor-not-allowed' : 'cursor-pointer'}>
        <svg
          className="mx-auto h-10 w-10 text-gray-400"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={1.5}
            d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"
          />
        </svg>
        <p className="mt-2 text-sm text-gray-600">
          <span className="font-medium text-blue-600">Click to upload</span> or drag and drop
        </p>
        <p className="mt-1 text-xs text-gray-500">TXT, MD, JSON, PDF, DOCX</p>
      </label>
    </div>
  );
};

// Main Dashboard Component
export const RAGConfigDashboard: React.FC<RAGConfigDashboardProps> = ({
  personaId,
  onConfigChange,
  onIndexDocument,
  onRemoveDocument,
  readOnly = false,
}) => {
  // State for configurations
  const [providerConfig, setProviderConfig] = useState<RAGProviderConfig>({
    providerType: 'chroma',
    indexName: 'maestro_personas',
    namespace: personaId || 'default',
    embeddingModel: 'text-embedding-3-small',
    embeddingDimension: 1536,
    similarityMetric: 'cosine',
  });

  const [queryConfig, setQueryConfig] = useState<QueryConfig>({
    strategy: 'hybrid',
    defaultTopK: 10,
    maxTopK: 100,
    minSimilarityThreshold: 0.7,
    timeoutSeconds: 30,
    retryAttempts: 3,
    cacheEnabled: true,
    cacheTTLSeconds: 3600,
  });

  const [chunkingConfig, setChunkingConfig] = useState<ChunkingConfig>({
    strategy: 'recursive',
    chunkSize: 500,
    chunkOverlap: 50,
    minChunkSize: 100,
    maxChunkSize: 2000,
  });

  const [enhancementConfig, setEnhancementConfig] = useState<EnhancementConfig>({
    strategy: 'structured',
    contextFormat: 'markdown',
    maxContextTokens: 2000,
    maxResultsToInclude: 5,
    minRelevanceScore: 0.7,
    includeSources: true,
    includeConfidence: true,
    deduplicate: true,
  });

  // State for metrics and documents
  const [indexStats, setIndexStats] = useState<IndexStats | null>(null);
  const [indexHealth, setIndexHealth] = useState<IndexHealth | null>(null);
  const [connectorMetrics, setConnectorMetrics] = useState<ConnectorMetrics | null>(null);
  const [documents, setDocuments] = useState<IndexedDocument[]>([]);
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState<'overview' | 'provider' | 'query' | 'chunking' | 'enhancement' | 'documents'>('overview');

  // Simulated data loading
  useEffect(() => {
    // In a real implementation, this would fetch from API
    const loadData = async () => {
      setLoading(true);
      try {
        // Simulate API delay
        await new Promise((resolve) => setTimeout(resolve, 500));

        setIndexStats({
          indexName: providerConfig.indexName,
          totalVectors: 15420,
          dimension: providerConfig.embeddingDimension,
          namespaces: ['default', personaId || 'persona_1'].filter(Boolean),
          indexFullness: 0.32,
          lastUpdated: new Date().toISOString(),
        });

        setIndexHealth({
          status: 'active',
          totalDocuments: 127,
          totalChunks: 15420,
          indexSizeMB: 45.2,
          lastUpdated: new Date().toISOString(),
          staleDocuments: 3,
          errorCount: 0,
          recommendations: [],
        });

        setConnectorMetrics({
          status: 'connected',
          queryCount: 1542,
          averageLatencyMs: 45.3,
          cacheHitRate: 0.78,
        });

        setDocuments([
          {
            documentId: 'doc_001',
            title: 'Product Documentation',
            source: 'confluence',
            chunkCount: 156,
            indexedAt: new Date(Date.now() - 86400000).toISOString(),
            status: 'active',
          },
          {
            documentId: 'doc_002',
            title: 'API Reference Guide',
            source: 'github',
            chunkCount: 89,
            indexedAt: new Date(Date.now() - 172800000).toISOString(),
            status: 'active',
          },
          {
            documentId: 'doc_003',
            title: 'Best Practices Manual',
            source: 'upload',
            chunkCount: 234,
            indexedAt: new Date(Date.now() - 259200000).toISOString(),
            status: 'active',
          },
        ]);
      } finally {
        setLoading(false);
      }
    };

    loadData();
  }, [personaId, providerConfig.indexName, providerConfig.embeddingDimension]);

  // Handle config changes
  const handleConfigUpdate = useCallback(() => {
    if (onConfigChange) {
      onConfigChange({
        ...providerConfig,
        ...queryConfig,
        ...enhancementConfig,
      });
    }
  }, [providerConfig, queryConfig, enhancementConfig, onConfigChange]);

  // Handle document upload
  const handleDocumentUpload = useCallback(
    async (file: File) => {
      if (onIndexDocument) {
        await onIndexDocument(file);
      }
    },
    [onIndexDocument]
  );

  // Handle document removal
  const handleDocumentRemove = useCallback(
    async (documentId: string) => {
      if (onRemoveDocument) {
        await onRemoveDocument(documentId);
        setDocuments((prev) => prev.filter((d) => d.documentId !== documentId));
      }
    },
    [onRemoveDocument]
  );

  // Tab navigation
  const tabs = [
    { id: 'overview', label: 'Overview' },
    { id: 'provider', label: 'Provider' },
    { id: 'query', label: 'Query' },
    { id: 'chunking', label: 'Chunking' },
    { id: 'enhancement', label: 'Enhancement' },
    { id: 'documents', label: 'Documents' },
  ] as const;

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-7xl mx-auto space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">RAG Configuration</h1>
            <p className="mt-1 text-sm text-gray-600">
              Configure knowledge retrieval and context enhancement for
              {personaId ? ` persona ${personaId}` : ' all personas'}
            </p>
          </div>
          <div className="flex items-center gap-3">
            {connectorMetrics && <StatusBadge status={connectorMetrics.status} />}
            {!readOnly && (
              <button
                onClick={handleConfigUpdate}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors font-medium text-sm"
              >
                Save Changes
              </button>
            )}
          </div>
        </div>

        {/* Tab Navigation */}
        <div className="border-b border-gray-200">
          <nav className="flex -mb-px space-x-8">
            {tabs.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`py-3 px-1 border-b-2 font-medium text-sm transition-colors ${
                  activeTab === tab.id
                    ? 'border-blue-500 text-blue-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }`}
              >
                {tab.label}
              </button>
            ))}
          </nav>
        </div>

        {/* Tab Content */}
        <div className="space-y-6">
          {/* Overview Tab */}
          {activeTab === 'overview' && (
            <>
              {/* Metrics Grid */}
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                <MetricCard
                  title="Total Documents"
                  value={indexHealth?.totalDocuments || 0}
                  subtitle={`${indexHealth?.staleDocuments || 0} stale`}
                />
                <MetricCard
                  title="Total Chunks"
                  value={indexStats?.totalVectors?.toLocaleString() || 0}
                  subtitle={`${indexStats?.dimension || 0}d vectors`}
                />
                <MetricCard
                  title="Avg Query Latency"
                  value={`${connectorMetrics?.averageLatencyMs?.toFixed(1) || 0}ms`}
                  subtitle={`${connectorMetrics?.queryCount?.toLocaleString() || 0} queries`}
                  trend={connectorMetrics?.averageLatencyMs && connectorMetrics.averageLatencyMs < 100 ? 'up' : 'down'}
                />
                <MetricCard
                  title="Cache Hit Rate"
                  value={`${((connectorMetrics?.cacheHitRate || 0) * 100).toFixed(0)}%`}
                  subtitle={queryConfig.cacheEnabled ? 'Enabled' : 'Disabled'}
                />
              </div>

              {/* Quick Status */}
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                <ConfigSection title="Index Health">
                  <div className="space-y-4">
                    <div className="flex items-center justify-between">
                      <span className="text-sm text-gray-600">Status</span>
                      {indexHealth && <StatusBadge status={indexHealth.status} />}
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-sm text-gray-600">Index Size</span>
                      <span className="text-sm font-medium text-gray-900">
                        {indexHealth?.indexSizeMB?.toFixed(1) || 0} MB
                      </span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-sm text-gray-600">Last Updated</span>
                      <span className="text-sm text-gray-900">
                        {indexHealth?.lastUpdated
                          ? new Date(indexHealth.lastUpdated).toLocaleString()
                          : 'Never'}
                      </span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-sm text-gray-600">Namespaces</span>
                      <span className="text-sm font-medium text-gray-900">
                        {indexStats?.namespaces?.length || 0}
                      </span>
                    </div>
                    {indexHealth?.recommendations && indexHealth.recommendations.length > 0 && (
                      <div className="mt-4 p-3 bg-yellow-50 rounded-lg border border-yellow-100">
                        <p className="text-sm font-medium text-yellow-800">Recommendations</p>
                        <ul className="mt-2 space-y-1">
                          {indexHealth.recommendations.map((rec, idx) => (
                            <li key={idx} className="text-sm text-yellow-700">
                              {rec}
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>
                </ConfigSection>

                <ConfigSection title="Current Configuration">
                  <div className="space-y-3">
                    <div className="flex items-center justify-between">
                      <span className="text-sm text-gray-600">Provider</span>
                      <span className="text-sm font-medium text-gray-900 capitalize">
                        {providerConfig.providerType}
                      </span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-sm text-gray-600">Embedding Model</span>
                      <span className="text-sm font-medium text-gray-900">
                        {providerConfig.embeddingModel}
                      </span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-sm text-gray-600">Query Strategy</span>
                      <span className="text-sm font-medium text-gray-900 capitalize">
                        {queryConfig.strategy}
                      </span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-sm text-gray-600">Chunking Strategy</span>
                      <span className="text-sm font-medium text-gray-900 capitalize">
                        {chunkingConfig.strategy.replace('_', ' ')}
                      </span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-sm text-gray-600">Enhancement Strategy</span>
                      <span className="text-sm font-medium text-gray-900 capitalize">
                        {enhancementConfig.strategy}
                      </span>
                    </div>
                  </div>
                </ConfigSection>
              </div>
            </>
          )}

          {/* Provider Configuration Tab */}
          {activeTab === 'provider' && (
            <ConfigSection
              title="Vector Store Provider"
              description="Configure the vector database for storing embeddings"
            >
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <FormField label="Provider Type" htmlFor="provider-type" required>
                  <SelectField
                    id="provider-type"
                    value={providerConfig.providerType}
                    onChange={(v) =>
                      setProviderConfig((prev) => ({
                        ...prev,
                        providerType: v as RAGProviderConfig['providerType'],
                      }))
                    }
                    options={PROVIDER_OPTIONS}
                    disabled={readOnly}
                  />
                </FormField>

                <FormField label="Index Name" htmlFor="index-name" required>
                  <TextInput
                    id="index-name"
                    value={providerConfig.indexName}
                    onChange={(v) => setProviderConfig((prev) => ({ ...prev, indexName: v }))}
                    placeholder="maestro_personas"
                    disabled={readOnly}
                  />
                </FormField>

                <FormField label="Namespace" htmlFor="namespace">
                  <TextInput
                    id="namespace"
                    value={providerConfig.namespace}
                    onChange={(v) => setProviderConfig((prev) => ({ ...prev, namespace: v }))}
                    placeholder="default"
                    disabled={readOnly}
                  />
                </FormField>

                <FormField label="Embedding Model" htmlFor="embedding-model" required>
                  <SelectField
                    id="embedding-model"
                    value={providerConfig.embeddingModel}
                    onChange={(v) => {
                      const model = EMBEDDING_MODELS.find((m) => m.value === v);
                      setProviderConfig((prev) => ({
                        ...prev,
                        embeddingModel: v,
                        embeddingDimension: model?.dimension || prev.embeddingDimension,
                      }));
                    }}
                    options={EMBEDDING_MODELS}
                    disabled={readOnly}
                  />
                </FormField>

                <FormField label="Embedding Dimension" htmlFor="embedding-dimension">
                  <NumberInput
                    id="embedding-dimension"
                    value={providerConfig.embeddingDimension}
                    onChange={(v) =>
                      setProviderConfig((prev) => ({ ...prev, embeddingDimension: v }))
                    }
                    min={64}
                    max={4096}
                    disabled={readOnly}
                  />
                </FormField>

                <FormField label="Similarity Metric" htmlFor="similarity-metric">
                  <SelectField
                    id="similarity-metric"
                    value={providerConfig.similarityMetric}
                    onChange={(v) =>
                      setProviderConfig((prev) => ({
                        ...prev,
                        similarityMetric: v as RAGProviderConfig['similarityMetric'],
                      }))
                    }
                    options={[
                      { value: 'cosine', label: 'Cosine Similarity' },
                      { value: 'euclidean', label: 'Euclidean Distance' },
                      { value: 'dot_product', label: 'Dot Product' },
                    ]}
                    disabled={readOnly}
                  />
                </FormField>

                {providerConfig.providerType !== 'chroma' &&
                  providerConfig.providerType !== 'faiss' && (
                    <>
                      <FormField label="API Endpoint" htmlFor="api-endpoint">
                        <TextInput
                          id="api-endpoint"
                          value={providerConfig.apiEndpoint || ''}
                          onChange={(v) =>
                            setProviderConfig((prev) => ({ ...prev, apiEndpoint: v }))
                          }
                          placeholder="https://api.example.com"
                          disabled={readOnly}
                        />
                      </FormField>

                      <FormField label="API Key" htmlFor="api-key">
                        <TextInput
                          id="api-key"
                          value={providerConfig.apiKey || ''}
                          onChange={(v) => setProviderConfig((prev) => ({ ...prev, apiKey: v }))}
                          type="password"
                          placeholder="Enter API key"
                          disabled={readOnly}
                        />
                      </FormField>
                    </>
                  )}
              </div>
            </ConfigSection>
          )}

          {/* Query Configuration Tab */}
          {activeTab === 'query' && (
            <ConfigSection
              title="Query Settings"
              description="Configure how knowledge is retrieved from the index"
            >
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <FormField
                  label="Query Strategy"
                  htmlFor="query-strategy"
                  description="Method for retrieving relevant context"
                >
                  <SelectField
                    id="query-strategy"
                    value={queryConfig.strategy}
                    onChange={(v) =>
                      setQueryConfig((prev) => ({
                        ...prev,
                        strategy: v as QueryConfig['strategy'],
                      }))
                    }
                    options={QUERY_STRATEGIES}
                    disabled={readOnly}
                  />
                </FormField>

                <FormField
                  label="Default Top-K"
                  htmlFor="default-topk"
                  description="Number of results to return by default"
                >
                  <NumberInput
                    id="default-topk"
                    value={queryConfig.defaultTopK}
                    onChange={(v) => setQueryConfig((prev) => ({ ...prev, defaultTopK: v }))}
                    min={1}
                    max={queryConfig.maxTopK}
                    disabled={readOnly}
                  />
                </FormField>

                <FormField
                  label="Max Top-K"
                  htmlFor="max-topk"
                  description="Maximum allowed results per query"
                >
                  <NumberInput
                    id="max-topk"
                    value={queryConfig.maxTopK}
                    onChange={(v) => setQueryConfig((prev) => ({ ...prev, maxTopK: v }))}
                    min={10}
                    max={1000}
                    disabled={readOnly}
                  />
                </FormField>

                <FormField
                  label="Minimum Similarity Threshold"
                  htmlFor="min-similarity"
                  description="Minimum relevance score for results"
                >
                  <Slider
                    id="min-similarity"
                    value={queryConfig.minSimilarityThreshold}
                    onChange={(v) =>
                      setQueryConfig((prev) => ({ ...prev, minSimilarityThreshold: v }))
                    }
                    min={0}
                    max={1}
                    step={0.05}
                    disabled={readOnly}
                  />
                </FormField>

                <FormField
                  label="Timeout (seconds)"
                  htmlFor="timeout"
                  description="Query timeout in seconds"
                >
                  <NumberInput
                    id="timeout"
                    value={queryConfig.timeoutSeconds}
                    onChange={(v) => setQueryConfig((prev) => ({ ...prev, timeoutSeconds: v }))}
                    min={1}
                    max={120}
                    disabled={readOnly}
                  />
                </FormField>

                <FormField
                  label="Retry Attempts"
                  htmlFor="retry-attempts"
                  description="Number of retry attempts on failure"
                >
                  <NumberInput
                    id="retry-attempts"
                    value={queryConfig.retryAttempts}
                    onChange={(v) => setQueryConfig((prev) => ({ ...prev, retryAttempts: v }))}
                    min={0}
                    max={10}
                    disabled={readOnly}
                  />
                </FormField>

                <div className="md:col-span-2 border-t pt-4">
                  <h4 className="text-sm font-medium text-gray-900 mb-4">Cache Settings</h4>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <FormField
                      label="Enable Query Cache"
                      htmlFor="cache-enabled"
                      description="Cache query results for faster repeated queries"
                    >
                      <Toggle
                        id="cache-enabled"
                        checked={queryConfig.cacheEnabled}
                        onChange={(v) => setQueryConfig((prev) => ({ ...prev, cacheEnabled: v }))}
                        disabled={readOnly}
                      />
                    </FormField>

                    <FormField
                      label="Cache TTL (seconds)"
                      htmlFor="cache-ttl"
                      description="How long to cache query results"
                    >
                      <NumberInput
                        id="cache-ttl"
                        value={queryConfig.cacheTTLSeconds}
                        onChange={(v) =>
                          setQueryConfig((prev) => ({ ...prev, cacheTTLSeconds: v }))
                        }
                        min={60}
                        max={86400}
                        disabled={readOnly || !queryConfig.cacheEnabled}
                      />
                    </FormField>
                  </div>
                </div>
              </div>
            </ConfigSection>
          )}

          {/* Chunking Configuration Tab */}
          {activeTab === 'chunking' && (
            <ConfigSection
              title="Document Chunking"
              description="Configure how documents are split for indexing"
            >
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <FormField
                  label="Chunking Strategy"
                  htmlFor="chunking-strategy"
                  description="Method for splitting documents"
                >
                  <SelectField
                    id="chunking-strategy"
                    value={chunkingConfig.strategy}
                    onChange={(v) =>
                      setChunkingConfig((prev) => ({
                        ...prev,
                        strategy: v as ChunkingConfig['strategy'],
                      }))
                    }
                    options={CHUNKING_STRATEGIES}
                    disabled={readOnly}
                  />
                </FormField>

                <FormField
                  label="Target Chunk Size"
                  htmlFor="chunk-size"
                  description="Target characters per chunk"
                >
                  <NumberInput
                    id="chunk-size"
                    value={chunkingConfig.chunkSize}
                    onChange={(v) => setChunkingConfig((prev) => ({ ...prev, chunkSize: v }))}
                    min={100}
                    max={4000}
                    disabled={readOnly}
                  />
                </FormField>

                <FormField
                  label="Chunk Overlap"
                  htmlFor="chunk-overlap"
                  description="Characters to overlap between chunks"
                >
                  <NumberInput
                    id="chunk-overlap"
                    value={chunkingConfig.chunkOverlap}
                    onChange={(v) => setChunkingConfig((prev) => ({ ...prev, chunkOverlap: v }))}
                    min={0}
                    max={500}
                    disabled={readOnly}
                  />
                </FormField>

                <FormField
                  label="Minimum Chunk Size"
                  htmlFor="min-chunk-size"
                  description="Discard chunks smaller than this"
                >
                  <NumberInput
                    id="min-chunk-size"
                    value={chunkingConfig.minChunkSize}
                    onChange={(v) => setChunkingConfig((prev) => ({ ...prev, minChunkSize: v }))}
                    min={10}
                    max={500}
                    disabled={readOnly}
                  />
                </FormField>

                <FormField
                  label="Maximum Chunk Size"
                  htmlFor="max-chunk-size"
                  description="Split chunks larger than this"
                >
                  <NumberInput
                    id="max-chunk-size"
                    value={chunkingConfig.maxChunkSize}
                    onChange={(v) => setChunkingConfig((prev) => ({ ...prev, maxChunkSize: v }))}
                    min={500}
                    max={10000}
                    disabled={readOnly}
                  />
                </FormField>
              </div>
            </ConfigSection>
          )}

          {/* Enhancement Configuration Tab */}
          {activeTab === 'enhancement' && (
            <ConfigSection
              title="Context Enhancement"
              description="Configure how retrieved context is injected into prompts"
            >
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <FormField
                  label="Enhancement Strategy"
                  htmlFor="enhancement-strategy"
                  description="How to inject context into prompts"
                >
                  <SelectField
                    id="enhancement-strategy"
                    value={enhancementConfig.strategy}
                    onChange={(v) =>
                      setEnhancementConfig((prev) => ({
                        ...prev,
                        strategy: v as EnhancementConfig['strategy'],
                      }))
                    }
                    options={ENHANCEMENT_STRATEGIES}
                    disabled={readOnly}
                  />
                </FormField>

                <FormField
                  label="Context Format"
                  htmlFor="context-format"
                  description="Format for presenting context"
                >
                  <SelectField
                    id="context-format"
                    value={enhancementConfig.contextFormat}
                    onChange={(v) =>
                      setEnhancementConfig((prev) => ({
                        ...prev,
                        contextFormat: v as EnhancementConfig['contextFormat'],
                      }))
                    }
                    options={[
                      { value: 'markdown', label: 'Markdown' },
                      { value: 'plain', label: 'Plain Text' },
                      { value: 'json', label: 'JSON' },
                      { value: 'bulleted', label: 'Bulleted List' },
                    ]}
                    disabled={readOnly}
                  />
                </FormField>

                <FormField
                  label="Max Context Tokens"
                  htmlFor="max-context-tokens"
                  description="Maximum tokens for injected context"
                >
                  <NumberInput
                    id="max-context-tokens"
                    value={enhancementConfig.maxContextTokens}
                    onChange={(v) =>
                      setEnhancementConfig((prev) => ({ ...prev, maxContextTokens: v }))
                    }
                    min={100}
                    max={10000}
                    disabled={readOnly}
                  />
                </FormField>

                <FormField
                  label="Max Results to Include"
                  htmlFor="max-results"
                  description="Maximum context chunks to include"
                >
                  <NumberInput
                    id="max-results"
                    value={enhancementConfig.maxResultsToInclude}
                    onChange={(v) =>
                      setEnhancementConfig((prev) => ({ ...prev, maxResultsToInclude: v }))
                    }
                    min={1}
                    max={20}
                    disabled={readOnly}
                  />
                </FormField>

                <FormField
                  label="Min Relevance Score"
                  htmlFor="min-relevance"
                  description="Minimum score for context inclusion"
                >
                  <Slider
                    id="min-relevance"
                    value={enhancementConfig.minRelevanceScore}
                    onChange={(v) =>
                      setEnhancementConfig((prev) => ({ ...prev, minRelevanceScore: v }))
                    }
                    min={0}
                    max={1}
                    step={0.05}
                    disabled={readOnly}
                  />
                </FormField>

                <div className="space-y-4">
                  <FormField label="Include Sources" htmlFor="include-sources">
                    <Toggle
                      id="include-sources"
                      checked={enhancementConfig.includeSources}
                      onChange={(v) =>
                        setEnhancementConfig((prev) => ({ ...prev, includeSources: v }))
                      }
                      disabled={readOnly}
                    />
                  </FormField>

                  <FormField label="Include Confidence Scores" htmlFor="include-confidence">
                    <Toggle
                      id="include-confidence"
                      checked={enhancementConfig.includeConfidence}
                      onChange={(v) =>
                        setEnhancementConfig((prev) => ({ ...prev, includeConfidence: v }))
                      }
                      disabled={readOnly}
                    />
                  </FormField>

                  <FormField label="Deduplicate Content" htmlFor="deduplicate">
                    <Toggle
                      id="deduplicate"
                      checked={enhancementConfig.deduplicate}
                      onChange={(v) =>
                        setEnhancementConfig((prev) => ({ ...prev, deduplicate: v }))
                      }
                      disabled={readOnly}
                    />
                  </FormField>
                </div>
              </div>
            </ConfigSection>
          )}

          {/* Documents Tab */}
          {activeTab === 'documents' && (
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              <div className="lg:col-span-2">
                <ConfigSection title="Indexed Documents">
                  <DocumentList
                    documents={documents}
                    onRemove={readOnly ? undefined : handleDocumentRemove}
                    loading={loading}
                  />
                </ConfigSection>
              </div>

              <div>
                <ConfigSection title="Upload Document">
                  <FileUpload onUpload={handleDocumentUpload} disabled={readOnly} />
                </ConfigSection>

                <div className="mt-6">
                  <ConfigSection title="Quick Actions">
                    <div className="space-y-3">
                      <button
                        disabled={readOnly}
                        className="w-full px-4 py-2 text-sm font-medium text-blue-600 bg-blue-50 rounded-lg hover:bg-blue-100 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                      >
                        Refresh All Documents
                      </button>
                      <button
                        disabled={readOnly}
                        className="w-full px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                      >
                        Export Index Metadata
                      </button>
                      <button
                        disabled={readOnly}
                        className="w-full px-4 py-2 text-sm font-medium text-red-600 bg-red-50 rounded-lg hover:bg-red-100 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                      >
                        Clear Stale Documents
                      </button>
                    </div>
                  </ConfigSection>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default RAGConfigDashboard;
