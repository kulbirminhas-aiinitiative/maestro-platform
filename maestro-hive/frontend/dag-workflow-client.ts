/**
 * DAG Workflow Client Library
 * Complete TypeScript client for DAG Workflow API
 *
 * @version 1.0.0
 * @author Maestro Platform Team
 */

// ============================================================================
// Type Definitions
// ============================================================================

export interface WorkflowResponse {
  workflow_id: string;
  name: string;
  type: 'linear' | 'parallel';
  nodes: number;
  edges: number;
  created_at: string;
}

export interface WorkflowNode {
  id: string;
  type: 'phase';
  position: { x: number; y: number };
  data: {
    phase: string;
    label: string;
    status: NodeStatus;
    node_type: string;
  };
}

export interface WorkflowEdge {
  id: string;
  source: string;
  target: string;
  type: 'smoothstep';
}

export interface WorkflowDetails {
  workflow_id: string;
  name: string;
  type: string;
  nodes: WorkflowNode[];
  edges: WorkflowEdge[];
}

export type NodeStatus = 'pending' | 'running' | 'completed' | 'failed';
export type ExecutionStatus = 'pending' | 'running' | 'completed' | 'failed' | 'cancelled';

export interface NodeStateResponse {
  node_id: string;
  status: NodeStatus;
  attempt_count: number;
  started_at?: string;
  completed_at?: string;
  duration?: number;
  outputs?: Record<string, any>;
  artifacts?: string[];
  error?: string;
}

export interface ExecutionStatusResponse {
  execution_id: string;
  workflow_id: string;
  status: ExecutionStatus;
  completed_nodes: number;
  total_nodes: number;
  progress_percent: number;
  node_states: NodeStateResponse[];
  started_at?: string;
  completed_at?: string;
}

export interface ExecutionResponse {
  execution_id: string;
  workflow_id: string;
  status: 'running';
  started_at: string;
}

export interface ExecuteRequest {
  requirement: string;
  initial_context?: {
    timeout_seconds?: number;
    [key: string]: any;
  };
}

export interface HealthResponse {
  status: 'healthy' | 'degraded' | 'unhealthy';
  timestamp: string;
  database: {
    connected: boolean;
    type: 'SQLite' | 'PostgreSQL';
    error?: string;
  };
  cache: {
    workflows: number;
    websockets: number;
  };
  tasks: {
    background: number;
    active: number;
  };
}

export type WebSocketEventType =
  | 'workflow_started'
  | 'node_started'
  | 'node_completed'
  | 'node_failed'
  | 'workflow_completed'
  | 'workflow_failed'
  | 'pong';

export interface WebSocketEvent {
  type: WebSocketEventType;
  timestamp: string;
  workflow_id?: string;
  execution_id?: string;
  node_id?: string;
  data?: any;
}

// ============================================================================
// Configuration
// ============================================================================

export interface DAGClientConfig {
  /**
   * Base URL of the DAG API server
   * @default 'http://localhost:8003'
   */
  baseUrl: string;

  /**
   * Request timeout in milliseconds
   * @default 30000
   */
  timeout?: number;

  /**
   * Custom headers to include in all requests
   */
  headers?: Record<string, string>;

  /**
   * Retry configuration
   */
  retry?: {
    maxAttempts: number;
    delayMs: number;
  };
}

// ============================================================================
// Error Handling
// ============================================================================

export class DAGWorkflowError extends Error {
  constructor(
    message: string,
    public code: string,
    public statusCode?: number,
    public details?: any
  ) {
    super(message);
    this.name = 'DAGWorkflowError';
  }
}

// ============================================================================
// Main Client Class
// ============================================================================

export class DAGWorkflowClient {
  private baseUrl: string;
  private timeout: number;
  private headers: Record<string, string>;
  private retryConfig?: { maxAttempts: number; delayMs: number };

  constructor(config: DAGClientConfig) {
    this.baseUrl = config.baseUrl.replace(/\/$/, ''); // Remove trailing slash
    this.timeout = config.timeout || 30000;
    this.headers = {
      'Content-Type': 'application/json',
      ...config.headers,
    };
    this.retryConfig = config.retry;
  }

  // --------------------------------------------------------------------------
  // Private Helper Methods
  // --------------------------------------------------------------------------

  /**
   * Make HTTP request with error handling and retries
   */
  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const url = `${this.baseUrl}${endpoint}`;
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), this.timeout);

    const requestOptions: RequestInit = {
      ...options,
      headers: {
        ...this.headers,
        ...options.headers,
      },
      signal: controller.signal,
    };

    try {
      const response = await this.fetchWithRetry(url, requestOptions);

      clearTimeout(timeoutId);

      if (!response.ok) {
        await this.handleErrorResponse(response);
      }

      return await response.json();
    } catch (error: any) {
      clearTimeout(timeoutId);

      if (error.name === 'AbortError') {
        throw new DAGWorkflowError(
          'Request timeout',
          'TIMEOUT_ERROR',
          undefined,
          { timeout: this.timeout }
        );
      }

      if (error instanceof DAGWorkflowError) {
        throw error;
      }

      throw new DAGWorkflowError(
        `Network error: ${error.message}`,
        'NETWORK_ERROR',
        undefined,
        { originalError: error }
      );
    }
  }

  /**
   * Fetch with retry logic
   */
  private async fetchWithRetry(
    url: string,
    options: RequestInit,
    attempt = 1
  ): Promise<Response> {
    try {
      return await fetch(url, options);
    } catch (error) {
      if (this.retryConfig && attempt < this.retryConfig.maxAttempts) {
        await this.delay(this.retryConfig.delayMs * attempt);
        return this.fetchWithRetry(url, options, attempt + 1);
      }
      throw error;
    }
  }

  /**
   * Handle error responses
   */
  private async handleErrorResponse(response: Response): Promise<never> {
    let errorData: any = {};
    try {
      errorData = await response.json();
    } catch {
      // Response is not JSON
    }

    const message = errorData.message || errorData.error || response.statusText;

    switch (response.status) {
      case 400:
        throw new DAGWorkflowError(
          message || 'Invalid request',
          'VALIDATION_ERROR',
          400,
          errorData
        );

      case 404:
        throw new DAGWorkflowError(
          message || 'Resource not found',
          'NOT_FOUND',
          404,
          errorData
        );

      case 500:
        throw new DAGWorkflowError(
          message || 'Internal server error',
          'SERVER_ERROR',
          500,
          errorData
        );

      default:
        throw new DAGWorkflowError(
          message || 'Request failed',
          'REQUEST_ERROR',
          response.status,
          errorData
        );
    }
  }

  /**
   * Delay helper for retries
   */
  private delay(ms: number): Promise<void> {
    return new Promise(resolve => setTimeout(resolve, ms));
  }

  // --------------------------------------------------------------------------
  // Public API Methods
  // --------------------------------------------------------------------------

  /**
   * Get list of all available workflows
   *
   * @returns List of workflow definitions
   * @throws {DAGWorkflowError} If the request fails
   *
   * @example
   * ```typescript
   * const workflows = await client.getWorkflows();
   * console.log('Available workflows:', workflows.map(w => w.name));
   * ```
   */
  async getWorkflows(): Promise<WorkflowResponse[]> {
    return this.request<WorkflowResponse[]>('/api/workflows');
  }

  /**
   * Get detailed workflow structure for visualization
   *
   * @param workflowId - Workflow identifier (e.g., 'sdlc_parallel')
   * @returns Workflow details with nodes and edges
   * @throws {DAGWorkflowError} If the workflow is not found
   *
   * @example
   * ```typescript
   * const workflow = await client.getWorkflowDetails('sdlc_parallel');
   * console.log('Nodes:', workflow.nodes.length);
   * console.log('Edges:', workflow.edges.length);
   * ```
   */
  async getWorkflowDetails(workflowId: string): Promise<WorkflowDetails> {
    return this.request<WorkflowDetails>(`/api/workflows/${workflowId}`);
  }

  /**
   * Execute a workflow with a requirement
   *
   * @param workflowId - Workflow to execute
   * @param requirement - Project requirement description
   * @param initialContext - Optional execution context
   * @returns Execution details
   * @throws {DAGWorkflowError} If execution fails to start
   *
   * @example
   * ```typescript
   * const execution = await client.executeWorkflow(
   *   'sdlc_parallel',
   *   'Build a REST API for user authentication',
   *   { timeout_seconds: 3600 }
   * );
   * console.log('Execution started:', execution.execution_id);
   * ```
   */
  async executeWorkflow(
    workflowId: string,
    requirement: string,
    initialContext?: Record<string, any>
  ): Promise<ExecutionResponse> {
    const body: ExecuteRequest = {
      requirement,
      initial_context: initialContext,
    };

    return this.request<ExecutionResponse>(
      `/api/workflows/${workflowId}/execute`,
      {
        method: 'POST',
        body: JSON.stringify(body),
      }
    );
  }

  /**
   * Get current execution status and progress
   *
   * @param executionId - Execution identifier
   * @returns Current execution status
   * @throws {DAGWorkflowError} If execution is not found
   *
   * @example
   * ```typescript
   * const status = await client.getExecutionStatus('exec_123');
   * console.log('Progress:', status.progress_percent + '%');
   * console.log('Status:', status.status);
   * ```
   */
  async getExecutionStatus(executionId: string): Promise<ExecutionStatusResponse> {
    return this.request<ExecutionStatusResponse>(`/api/executions/${executionId}`);
  }

  /**
   * Poll execution status until completion
   *
   * @param executionId - Execution identifier
   * @param onUpdate - Callback for status updates
   * @param intervalMs - Polling interval (default: 2000ms)
   * @returns Final execution status
   * @throws {DAGWorkflowError} If execution fails
   *
   * @example
   * ```typescript
   * const finalStatus = await client.pollExecution(
   *   'exec_123',
   *   (status) => {
   *     console.log('Progress:', status.progress_percent + '%');
   *   },
   *   2000
   * );
   * console.log('Final status:', finalStatus.status);
   * ```
   */
  async pollExecution(
    executionId: string,
    onUpdate?: (status: ExecutionStatusResponse) => void,
    intervalMs: number = 2000
  ): Promise<ExecutionStatusResponse> {
    return new Promise((resolve, reject) => {
      const interval = setInterval(async () => {
        try {
          const status = await this.getExecutionStatus(executionId);

          onUpdate?.(status);

          if (
            status.status === 'completed' ||
            status.status === 'failed' ||
            status.status === 'cancelled'
          ) {
            clearInterval(interval);
            resolve(status);
          }
        } catch (error) {
          clearInterval(interval);
          reject(error);
        }
      }, intervalMs);
    });
  }

  /**
   * Connect to WebSocket for real-time updates
   *
   * @param workflowId - Workflow to monitor
   * @param handlers - Event handlers
   * @returns WebSocket connection
   *
   * @example
   * ```typescript
   * const ws = client.connectWebSocket('sdlc_parallel', {
   *   onOpen: () => console.log('Connected'),
   *   onMessage: (event) => console.log('Event:', event.type),
   *   onError: (error) => console.error('Error:', error),
   *   onClose: () => console.log('Disconnected')
   * });
   *
   * // Clean up
   * ws.close();
   * ```
   */
  connectWebSocket(
    workflowId: string,
    handlers: {
      onOpen?: () => void;
      onMessage?: (event: WebSocketEvent) => void;
      onError?: (error: Event) => void;
      onClose?: () => void;
    }
  ): WebSocket {
    const wsUrl = this.baseUrl.replace(/^http/, 'ws');
    const ws = new WebSocket(`${wsUrl}/ws/workflow/${workflowId}`);

    ws.onopen = () => {
      handlers.onOpen?.();

      // Keep-alive ping every 30 seconds
      const pingInterval = setInterval(() => {
        if (ws.readyState === WebSocket.OPEN) {
          ws.send('ping');
        } else {
          clearInterval(pingInterval);
        }
      }, 30000);
    };

    ws.onmessage = (event) => {
      try {
        const data: WebSocketEvent = JSON.parse(event.data);
        handlers.onMessage?.(data);
      } catch (error) {
        console.error('Failed to parse WebSocket message:', error);
      }
    };

    ws.onerror = (error) => {
      handlers.onError?.(error);
    };

    ws.onclose = () => {
      handlers.onClose?.();
    };

    return ws;
  }

  /**
   * Check API server health
   *
   * @returns Health status
   * @throws {DAGWorkflowError} If the server is unhealthy
   *
   * @example
   * ```typescript
   * const health = await client.healthCheck();
   * console.log('Status:', health.status);
   * console.log('Database:', health.database.type);
   * ```
   */
  async healthCheck(): Promise<HealthResponse> {
    return this.request<HealthResponse>('/health');
  }

  /**
   * Wait for specific execution status
   *
   * @param executionId - Execution identifier
   * @param targetStatus - Status to wait for
   * @param timeoutMs - Max time to wait (default: 2 hours)
   * @returns Execution status when target reached
   * @throws {DAGWorkflowError} If timeout is reached
   *
   * @example
   * ```typescript
   * try {
   *   const status = await client.waitForStatus('exec_123', 'completed', 60000);
   *   console.log('Workflow completed!');
   * } catch (error) {
   *   console.error('Timeout or failure');
   * }
   * ```
   */
  async waitForStatus(
    executionId: string,
    targetStatus: ExecutionStatus,
    timeoutMs: number = 7200000 // 2 hours
  ): Promise<ExecutionStatusResponse> {
    const startTime = Date.now();

    return new Promise((resolve, reject) => {
      const interval = setInterval(async () => {
        try {
          const status = await this.getExecutionStatus(executionId);

          if (status.status === targetStatus) {
            clearInterval(interval);
            resolve(status);
          } else if (
            status.status === 'failed' ||
            status.status === 'cancelled'
          ) {
            clearInterval(interval);
            reject(new DAGWorkflowError(
              `Execution ${status.status}`,
              'EXECUTION_FAILED',
              undefined,
              { status }
            ));
          } else if (Date.now() - startTime > timeoutMs) {
            clearInterval(interval);
            reject(new DAGWorkflowError(
              'Timeout waiting for execution status',
              'TIMEOUT',
              undefined,
              { executionId, targetStatus, timeoutMs }
            ));
          }
        } catch (error) {
          clearInterval(interval);
          reject(error);
        }
      }, 2000);
    });
  }
}

// ============================================================================
// Singleton Instance
// ============================================================================

/**
 * Default singleton instance
 * Configure with environment variables or override
 */
export const dagClient = new DAGWorkflowClient({
  baseUrl: typeof process !== 'undefined' && process.env?.DAG_API_URL
    ? process.env.DAG_API_URL
    : 'http://localhost:8003',
  timeout: 30000,
  retry: {
    maxAttempts: 3,
    delayMs: 1000,
  },
});

// ============================================================================
// Utility Functions
// ============================================================================

/**
 * Calculate workflow progress percentage
 */
export function calculateProgress(status: ExecutionStatusResponse): number {
  return (status.completed_nodes / status.total_nodes) * 100;
}

/**
 * Check if execution is complete
 */
export function isExecutionComplete(status: ExecutionStatusResponse): boolean {
  return status.status === 'completed' || status.status === 'failed' || status.status === 'cancelled';
}

/**
 * Get human-readable duration
 */
export function formatDuration(seconds: number): string {
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  const secs = Math.floor(seconds % 60);

  if (hours > 0) {
    return `${hours}h ${minutes}m ${secs}s`;
  } else if (minutes > 0) {
    return `${minutes}m ${secs}s`;
  } else {
    return `${secs}s`;
  }
}

/**
 * Get status color for UI
 */
export function getStatusColor(status: NodeStatus | ExecutionStatus): string {
  switch (status) {
    case 'completed':
      return '#28a745'; // Green
    case 'running':
      return '#ffc107'; // Yellow
    case 'failed':
      return '#dc3545'; // Red
    case 'pending':
      return '#6c757d'; // Gray
    case 'cancelled':
      return '#6c757d'; // Gray
    default:
      return '#6c757d';
  }
}

/**
 * Get status icon for UI
 */
export function getStatusIcon(status: NodeStatus | ExecutionStatus): string {
  switch (status) {
    case 'completed':
      return '✓';
    case 'running':
      return '⟳';
    case 'failed':
      return '✗';
    case 'pending':
      return '○';
    case 'cancelled':
      return '⊗';
    default:
      return '?';
  }
}

// ============================================================================
// Export All
// ============================================================================

export default DAGWorkflowClient;
