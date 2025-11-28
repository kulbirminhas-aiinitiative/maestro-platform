# Frontend Integration with DAG Workflow System

**Comprehensive Guide for Frontend Developers**

**Version**: 1.0.0
**Last Updated**: 2025-10-11
**Status**: Production Ready ✅

---

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [API Reference](#api-reference)
4. [WebSocket Integration](#websocket-integration)
5. [Frontend Client Library](#frontend-client-library)
6. [React Integration](#react-integration)
7. [Vue.js Integration](#vuejs-integration)
8. [Angular Integration](#angular-integration)
9. [State Management](#state-management)
10. [Real-Time Updates](#real-time-updates)
11. [Error Handling](#error-handling)
12. [Best Practices](#best-practices)
13. [Example Applications](#example-applications)

---

## Overview

The DAG Workflow System provides a RESTful API and WebSocket interface for managing SDLC workflows from frontend applications. This guide covers complete frontend integration patterns.

### Key Features

- ✅ RESTful API for workflow management
- ✅ WebSocket for real-time updates
- ✅ Workflow visualization support
- ✅ Execution monitoring
- ✅ Node-level status tracking
- ✅ Artifact management
- ✅ Error handling and recovery

### Supported Frontend Frameworks

- ✅ React (with hooks)
- ✅ Vue.js 3 (with Composition API)
- ✅ Angular 15+
- ✅ Vanilla JavaScript
- ✅ TypeScript (full type definitions)

---

## Architecture

### System Overview

```
┌─────────────────┐
│   Frontend UI   │
│  (React/Vue/    │
│   Angular)      │
└────────┬────────┘
         │
         │ HTTP/REST
         ├──────────────┐
         │              │ WebSocket
         ↓              ↓
┌─────────────────────────────────┐
│   DAG Workflow API Server       │
│   (FastAPI - Port 8003)         │
│                                 │
│  Routes:                        │
│  - GET  /api/workflows          │
│  - GET  /api/workflows/{id}     │
│  - POST /api/workflows/{id}/    │
│         execute                 │
│  - GET  /api/executions/{id}    │
│  - WS   /ws/workflow/{id}       │
└─────────────────────────────────┘
         │
         ↓
┌─────────────────────────────────┐
│   DAG Executor & Team Engine    │
│   - Workflow execution          │
│   - Persona orchestration       │
│   - State persistence           │
└─────────────────────────────────┘
```

### Data Flow

1. **Workflow Creation**: Frontend → API → DAG Workflow Generator
2. **Execution Start**: Frontend → API → DAG Executor → Background Task
3. **Real-Time Updates**: DAG Executor → WebSocket → Frontend
4. **Status Polling**: Frontend → API → Database → Frontend

---

## API Reference

### Base URL

```
Production: http://localhost:8003
Development: http://localhost:8003
```

### Endpoints

#### 1. Get Workflows List

**GET** `/api/workflows`

Get list of all available workflow definitions.

**Response**:
```typescript
interface WorkflowResponse {
  workflow_id: string;
  name: string;
  type: 'linear' | 'parallel';
  nodes: number;
  edges: number;
  created_at: string;
}

// Response: WorkflowResponse[]
```

**Example**:
```javascript
const response = await fetch('http://localhost:8003/api/workflows');
const workflows = await response.json();

// [
//   {
//     workflow_id: "sdlc_parallel",
//     name: "SDLC Parallel Workflow",
//     type: "parallel",
//     nodes: 6,
//     edges: 7,
//     created_at: "2025-10-11T13:00:00"
//   }
// ]
```

---

#### 2. Get Workflow Details

**GET** `/api/workflows/{workflow_id}`

Get detailed workflow structure for visualization.

**Response**:
```typescript
interface WorkflowNode {
  id: string;
  type: 'phase';
  position: { x: number; y: number };
  data: {
    phase: string;
    label: string;
    status: 'pending' | 'running' | 'completed' | 'failed';
    node_type: string;
  };
}

interface WorkflowEdge {
  id: string;
  source: string;
  target: string;
  type: 'smoothstep';
}

interface WorkflowDetails {
  workflow_id: string;
  name: string;
  type: string;
  nodes: WorkflowNode[];
  edges: WorkflowEdge[];
}
```

**Example**:
```javascript
const response = await fetch('http://localhost:8003/api/workflows/sdlc_parallel');
const workflow = await response.json();

// {
//   workflow_id: "sdlc_parallel",
//   name: "SDLC Parallel Workflow",
//   type: "parallel",
//   nodes: [
//     {
//       id: "requirement_analysis",
//       type: "phase",
//       position: { x: 0, y: 0 },
//       data: {
//         phase: "requirement_analysis",
//         label: "Requirement Analysis",
//         status: "pending",
//         node_type: "phase"
//       }
//     },
//     // ... more nodes
//   ],
//   edges: [
//     {
//       id: "requirement_analysis-design",
//       source: "requirement_analysis",
//       target: "design",
//       type: "smoothstep"
//     },
//     // ... more edges
//   ]
// }
```

---

#### 3. Execute Workflow

**POST** `/api/workflows/{workflow_id}/execute`

Start workflow execution with a requirement.

**Request Body**:
```typescript
interface ExecuteRequest {
  requirement: string;
  initial_context?: {
    timeout_seconds?: number;
    [key: string]: any;
  };
}
```

**Response**:
```typescript
interface ExecutionResponse {
  execution_id: string;
  workflow_id: string;
  status: 'running';
  started_at: string;
}
```

**Example**:
```javascript
const response = await fetch('http://localhost:8003/api/workflows/sdlc_parallel/execute', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    requirement: 'Build a REST API for user authentication with JWT tokens',
    initial_context: {
      timeout_seconds: 3600  // 1 hour
    }
  })
});

const execution = await response.json();

// {
//   execution_id: "exec_20251011_130245",
//   workflow_id: "sdlc_parallel",
//   status: "running",
//   started_at: "2025-10-11T13:02:45"
// }
```

---

#### 4. Get Execution Status

**GET** `/api/executions/{execution_id}`

Get current execution status and progress.

**Response**:
```typescript
interface NodeStateResponse {
  node_id: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  attempt_count: number;
  started_at?: string;
  completed_at?: string;
  duration?: number;
  outputs?: Record<string, any>;
  artifacts?: string[];
  error?: string;
}

interface ExecutionStatusResponse {
  execution_id: string;
  workflow_id: string;
  status: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled';
  completed_nodes: number;
  total_nodes: number;
  progress_percent: number;
  node_states: NodeStateResponse[];
  started_at?: string;
  completed_at?: string;
}
```

**Example**:
```javascript
const response = await fetch('http://localhost:8003/api/executions/exec_20251011_130245');
const status = await response.json();

// {
//   execution_id: "exec_20251011_130245",
//   workflow_id: "sdlc_parallel",
//   status: "running",
//   completed_nodes: 2,
//   total_nodes: 6,
//   progress_percent: 33.33,
//   node_states: [
//     {
//       node_id: "requirement_analysis",
//       status: "completed",
//       attempt_count: 1,
//       started_at: "2025-10-11T13:02:46",
//       completed_at: "2025-10-11T13:03:10",
//       duration: 24.5,
//       outputs: { /* ... */ },
//       artifacts: ["requirements.md"]
//     },
//     {
//       node_id: "design",
//       status: "running",
//       attempt_count: 1,
//       started_at: "2025-10-11T13:03:11"
//     },
//     // ... more node states
//   ]
// }
```

---

#### 5. Health Check

**GET** `/health`

Check API server health and status.

**Response**:
```typescript
interface HealthResponse {
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
```

---

## WebSocket Integration

### Connection

Connect to WebSocket for real-time workflow updates.

**Endpoint**: `ws://localhost:8003/ws/workflow/{workflow_id}`

**Connection Limits**:
- Max 1000 total connections
- Max 100 connections per workflow

### Event Types

```typescript
type WebSocketEvent =
  | WorkflowStartedEvent
  | NodeStartedEvent
  | NodeCompletedEvent
  | NodeFailedEvent
  | WorkflowCompletedEvent
  | WorkflowFailedEvent
  | PongEvent;

interface WorkflowStartedEvent {
  type: 'workflow_started';
  timestamp: string;
  workflow_id: string;
  execution_id: string;
  data: {};
}

interface NodeStartedEvent {
  type: 'node_started';
  timestamp: string;
  workflow_id: string;
  execution_id: string;
  node_id: string;
  data: {
    phase: string;
  };
}

interface NodeCompletedEvent {
  type: 'node_completed';
  timestamp: string;
  workflow_id: string;
  execution_id: string;
  node_id: string;
  data: {
    phase: string;
    duration: number;
    outputs?: any;
  };
}

interface NodeFailedEvent {
  type: 'node_failed';
  timestamp: string;
  workflow_id: string;
  execution_id: string;
  node_id: string;
  data: {
    error: string;
    phase: string;
  };
}

interface WorkflowCompletedEvent {
  type: 'workflow_completed';
  timestamp: string;
  workflow_id: string;
  execution_id: string;
  data: {};
}

interface WorkflowFailedEvent {
  type: 'workflow_failed';
  timestamp: string;
  workflow_id: string;
  execution_id: string;
  data: {
    error: string;
  };
}

interface PongEvent {
  type: 'pong';
  timestamp: string;
}
```

### Example WebSocket Usage

```javascript
// Connect to WebSocket
const ws = new WebSocket('ws://localhost:8003/ws/workflow/sdlc_parallel');

ws.onopen = () => {
  console.log('Connected to workflow');

  // Send ping to keep connection alive
  setInterval(() => {
    ws.send('ping');
  }, 30000);
};

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);

  switch (data.type) {
    case 'workflow_started':
      console.log('Workflow started:', data.execution_id);
      break;

    case 'node_started':
      console.log('Node started:', data.node_id);
      updateNodeStatus(data.node_id, 'running');
      break;

    case 'node_completed':
      console.log('Node completed:', data.node_id);
      updateNodeStatus(data.node_id, 'completed');
      updateProgress(data);
      break;

    case 'node_failed':
      console.error('Node failed:', data.node_id, data.data.error);
      updateNodeStatus(data.node_id, 'failed');
      showError(data.data.error);
      break;

    case 'workflow_completed':
      console.log('Workflow completed!');
      showSuccess();
      break;

    case 'workflow_failed':
      console.error('Workflow failed:', data.data.error);
      showError(data.data.error);
      break;

    case 'pong':
      // Keep-alive response
      break;
  }
};

ws.onerror = (error) => {
  console.error('WebSocket error:', error);
};

ws.onclose = () => {
  console.log('Disconnected from workflow');
};
```

---

## Frontend Client Library

Complete TypeScript client library for DAG Workflow API.

```typescript
// dag-client.ts

export interface DAGClientConfig {
  baseUrl: string;
  timeout?: number;
}

export class DAGWorkflowClient {
  private baseUrl: string;
  private timeout: number;

  constructor(config: DAGClientConfig) {
    this.baseUrl = config.baseUrl;
    this.timeout = config.timeout || 30000;
  }

  /**
   * Get list of all workflows
   */
  async getWorkflows(): Promise<WorkflowResponse[]> {
    const response = await fetch(`${this.baseUrl}/api/workflows`);
    if (!response.ok) {
      throw new Error(`Failed to get workflows: ${response.statusText}`);
    }
    return response.json();
  }

  /**
   * Get workflow details for visualization
   */
  async getWorkflowDetails(workflowId: string): Promise<WorkflowDetails> {
    const response = await fetch(`${this.baseUrl}/api/workflows/${workflowId}`);
    if (!response.ok) {
      throw new Error(`Failed to get workflow: ${response.statusText}`);
    }
    return response.json();
  }

  /**
   * Execute a workflow
   */
  async executeWorkflow(
    workflowId: string,
    requirement: string,
    initialContext?: Record<string, any>
  ): Promise<ExecutionResponse> {
    const response = await fetch(`${this.baseUrl}/api/workflows/${workflowId}/execute`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        requirement,
        initial_context: initialContext,
      }),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.message || 'Failed to execute workflow');
    }

    return response.json();
  }

  /**
   * Get execution status
   */
  async getExecutionStatus(executionId: string): Promise<ExecutionStatusResponse> {
    const response = await fetch(`${this.baseUrl}/api/executions/${executionId}`);
    if (!response.ok) {
      throw new Error(`Failed to get execution status: ${response.statusText}`);
    }
    return response.json();
  }

  /**
   * Poll execution status until completion
   */
  async pollExecution(
    executionId: string,
    onUpdate: (status: ExecutionStatusResponse) => void,
    intervalMs: number = 2000
  ): Promise<ExecutionStatusResponse> {
    return new Promise((resolve, reject) => {
      const interval = setInterval(async () => {
        try {
          const status = await this.getExecutionStatus(executionId);
          onUpdate(status);

          if (status.status === 'completed' || status.status === 'failed' || status.status === 'cancelled') {
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
    const wsUrl = this.baseUrl.replace('http', 'ws');
    const ws = new WebSocket(`${wsUrl}/ws/workflow/${workflowId}`);

    ws.onopen = () => {
      handlers.onOpen?.();

      // Keep-alive ping
      const pingInterval = setInterval(() => {
        if (ws.readyState === WebSocket.OPEN) {
          ws.send('ping');
        } else {
          clearInterval(pingInterval);
        }
      }, 30000);
    };

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      handlers.onMessage?.(data);
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
   * Check API health
   */
  async healthCheck(): Promise<HealthResponse> {
    const response = await fetch(`${this.baseUrl}/health`);
    if (!response.ok) {
      throw new Error('API is unhealthy');
    }
    return response.json();
  }
}

// Export singleton instance
export const dagClient = new DAGWorkflowClient({
  baseUrl: 'http://localhost:8003'
});
```

---

## React Integration

### Custom Hooks

```typescript
// hooks/useDAGWorkflow.ts

import { useState, useEffect, useCallback } from 'react';
import { dagClient } from '../lib/dag-client';
import type { ExecutionStatusResponse, WebSocketEvent } from '../lib/dag-client';

export function useDAGWorkflow(workflowId: string) {
  const [workflows, setWorkflows] = useState<WorkflowResponse[]>([]);
  const [workflowDetails, setWorkflowDetails] = useState<WorkflowDetails | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Load workflows
  useEffect(() => {
    dagClient.getWorkflows()
      .then(setWorkflows)
      .catch(err => setError(err.message));
  }, []);

  // Load workflow details
  useEffect(() => {
    if (workflowId) {
      dagClient.getWorkflowDetails(workflowId)
        .then(setWorkflowDetails)
        .catch(err => setError(err.message));
    }
  }, [workflowId]);

  const executeWorkflow = useCallback(async (requirement: string) => {
    setLoading(true);
    setError(null);

    try {
      const execution = await dagClient.executeWorkflow(workflowId, requirement);
      return execution;
    } catch (err: any) {
      setError(err.message);
      throw err;
    } finally {
      setLoading(false);
    }
  }, [workflowId]);

  return {
    workflows,
    workflowDetails,
    loading,
    error,
    executeWorkflow,
  };
}

export function useExecutionStatus(executionId: string | null) {
  const [status, setStatus] = useState<ExecutionStatusResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!executionId) return;

    setLoading(true);

    const interval = setInterval(async () => {
      try {
        const newStatus = await dagClient.getExecutionStatus(executionId);
        setStatus(newStatus);

        if (newStatus.status === 'completed' || newStatus.status === 'failed') {
          clearInterval(interval);
          setLoading(false);
        }
      } catch (err: any) {
        setError(err.message);
        clearInterval(interval);
        setLoading(false);
      }
    }, 2000);

    return () => clearInterval(interval);
  }, [executionId]);

  return { status, loading, error };
}

export function useWorkflowWebSocket(workflowId: string | null) {
  const [events, setEvents] = useState<WebSocketEvent[]>([]);
  const [connected, setConnected] = useState(false);

  useEffect(() => {
    if (!workflowId) return;

    const ws = dagClient.connectWebSocket(workflowId, {
      onOpen: () => setConnected(true),
      onMessage: (event) => setEvents(prev => [...prev, event]),
      onClose: () => setConnected(false),
      onError: (error) => console.error('WebSocket error:', error),
    });

    return () => {
      ws.close();
    };
  }, [workflowId]);

  return { events, connected };
}
```

### React Components

```typescript
// components/WorkflowExecutor.tsx

import React, { useState } from 'react';
import { useDAGWorkflow, useExecutionStatus, useWorkflowWebSocket } from '../hooks/useDAGWorkflow';

export function WorkflowExecutor() {
  const [workflowId, setWorkflowId] = useState('sdlc_parallel');
  const [requirement, setRequirement] = useState('');
  const [executionId, setExecutionId] = useState<string | null>(null);

  const { workflows, workflowDetails, executeWorkflow, loading, error } = useDAGWorkflow(workflowId);
  const { status } = useExecutionStatus(executionId);
  const { events, connected } = useWorkflowWebSocket(workflowId);

  const handleExecute = async () => {
    try {
      const execution = await executeWorkflow(requirement);
      setExecutionId(execution.execution_id);
    } catch (err) {
      console.error('Execution failed:', err);
    }
  };

  return (
    <div className="workflow-executor">
      <h1>DAG Workflow Executor</h1>

      {/* Workflow Selection */}
      <div className="workflow-selector">
        <label>Select Workflow:</label>
        <select value={workflowId} onChange={(e) => setWorkflowId(e.target.value)}>
          {workflows.map(wf => (
            <key={wf.workflow_id} value={wf.workflow_id}>
              {wf.name} ({wf.type})
            </option>
          ))}
        </select>
      </div>

      {/* Requirement Input */}
      <div className="requirement-input">
        <label>Requirement:</label>
        <textarea
          value={requirement}
          onChange={(e) => setRequirement(e.target.value)}
          placeholder="Enter your project requirement..."
          rows={4}
        />
      </div>

      {/* Execute Button */}
      <button onClick={handleExecute} disabled={loading || !requirement}>
        {loading ? 'Executing...' : 'Execute Workflow'}
      </button>

      {/* Error Display */}
      {error && (
        <div className="error">
          Error: {error}
        </div>
      )}

      {/* Execution Status */}
      {status && (
        <div className="execution-status">
          <h2>Execution Status</h2>
          <div className="status-info">
            <p>Status: <strong>{status.status}</strong></p>
            <p>Progress: <strong>{status.progress_percent.toFixed(1)}%</strong></p>
            <p>Completed Nodes: <strong>{status.completed_nodes}/{status.total_nodes}</strong></p>
          </div>

          {/* Node States */}
          <div className="node-states">
            <h3>Node Status</h3>
            {status.node_states.map(node => (
              <div key={node.node_id} className={`node-state ${node.status}`}>
                <span className="node-id">{node.node_id}</span>
                <span className="node-status">{node.status}</span>
                {node.duration && (
                  <span className="node-duration">{node.duration.toFixed(1)}s</span>
                )}
                {node.error && (
                  <span className="node-error">{node.error}</span>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* WebSocket Connection Status */}
      <div className="websocket-status">
        <span className={`indicator ${connected ? 'connected' : 'disconnected'}`}></span>
        {connected ? 'Connected' : 'Disconnected'}
      </div>

      {/* Real-Time Events */}
      {events.length > 0 && (
        <div className="events-log">
          <h3>Real-Time Events</h3>
          <div className="events">
            {events.slice(-10).reverse().map((event, idx) => (
              <div key={idx} className="event">
                <span className="timestamp">{new Date(event.timestamp).toLocaleTimeString()}</span>
                <span className="type">{event.type}</span>
                {event.node_id && <span className="node">{event.node_id}</span>}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
```

---

## Vue.js Integration

### Vue Composables

```typescript
// composables/useDAGWorkflow.ts

import { ref, computed, onMounted, onUnmounted } from 'vue';
import { dagClient } from '../lib/dag-client';
import type { ExecutionStatusResponse, WebSocketEvent } from '../lib/dag-client';

export function useDAGWorkflow(workflowId: string) {
  const workflowDetails = ref<WorkflowDetails | null>(null);
  const loading = ref(false);
  const error = ref<string | null>(null);

  const loadWorkflow = async () => {
    loading.value = true;
    error.value = null;

    try {
      workflowDetails.value = await dagClient.getWorkflowDetails(workflowId);
    } catch (err: any) {
      error.value = err.message;
    } finally {
      loading.value = false;
    }
  };

  onMounted(loadWorkflow);

  const executeWorkflow = async (requirement: string) => {
    loading.value = true;
    error.value = null;

    try {
      return await dagClient.executeWorkflow(workflowId, requirement);
    } catch (err: any) {
      error.value = err.message;
      throw err;
    } finally {
      loading.value = false;
    }
  };

  return {
    workflowDetails,
    loading,
    error,
    executeWorkflow,
    reload: loadWorkflow,
  };
}

export function useExecutionStatus(executionId: Ref<string | null>) {
  const status = ref<ExecutionStatusResponse | null>(null);
  const loading = ref(false);
  const error = ref<string | null>(null);

  let pollInterval: ReturnType<typeof setInterval> | null = null;

  watch(executionId, async (newId) => {
    if (pollInterval) {
      clearInterval(pollInterval);
      pollInterval = null;
    }

    if (!newId) return;

    loading.value = true;

    pollInterval = setInterval(async () => {
      try {
        const newStatus = await dagClient.getExecutionStatus(newId);
        status.value = newStatus;

        if (newStatus.status === 'completed' || newStatus.status === 'failed') {
          if (pollInterval) clearInterval(pollInterval);
          loading.value = false;
        }
      } catch (err: any) {
        error.value = err.message;
        if (pollInterval) clearInterval(pollInterval);
        loading.value = false;
      }
    }, 2000);
  });

  onUnmounted(() => {
    if (pollInterval) clearInterval(pollInterval);
  });

  return {
    status: computed(() => status.value),
    loading: computed(() => loading.value),
    error: computed(() => error.value),
  };
}

export function useWorkflowWebSocket(workflowId: Ref<string | null>) {
  const events = ref<WebSocketEvent[]>([]);
  const connected = ref(false);
  let ws: WebSocket | null = null;

  watch(workflowId, (newId) => {
    if (ws) {
      ws.close();
      ws = null;
    }

    if (!newId) return;

    ws = dagClient.connectWebSocket(newId, {
      onOpen: () => { connected.value = true; },
      onMessage: (event) => { events.value.push(event); },
      onClose: () => { connected.value = false; },
      onError: (error) => console.error('WebSocket error:', error),
    });
  });

  onUnmounted(() => {
    if (ws) ws.close();
  });

  return {
    events: computed(() => events.value),
    connected: computed(() => connected.value),
  };
}
```

### Vue Component

```vue
<!-- components/WorkflowExecutor.vue -->

<template>
  <div class="workflow-executor">
    <h1>DAG Workflow Executor</h1>

    <!-- Workflow Selection -->
    <div class="workflow-selector">
      <label>Select Workflow:</label>
      <select v-model="selectedWorkflowId">
        <option v-for="wf in workflows" :key="wf.workflow_id" :value="wf.workflow_id">
          {{ wf.name }} ({{ wf.type }})
        </option>
      </select>
    </div>

    <!-- Requirement Input -->
    <div class="requirement-input">
      <label>Requirement:</label>
      <textarea
        v-model="requirement"
        placeholder="Enter your project requirement..."
        rows="4"
      />
    </div>

    <!-- Execute Button -->
    <button @click="handleExecute" :disabled="loading || !requirement">
      {{ loading ? 'Executing...' : 'Execute Workflow' }}
    </button>

    <!-- Error Display -->
    <div v-if="error" class="error">
      Error: {{ error }}
    </div>

    <!-- Execution Status -->
    <div v-if="status" class="execution-status">
      <h2>Execution Status</h2>
      <div class="status-info">
        <p>Status: <strong>{{ status.status }}</strong></p>
        <p>Progress: <strong>{{ status.progress_percent.toFixed(1) }}%</strong></p>
        <p>Completed Nodes: <strong>{{ status.completed_nodes }}/{{ status.total_nodes }}</strong></p>
      </div>

      <!-- Node States -->
      <div class="node-states">
        <h3>Node Status</h3>
        <div
          v-for="node in status.node_states"
          :key="node.node_id"
          :class="['node-state', node.status]"
        >
          <span class="node-id">{{ node.node_id }}</span>
          <span class="node-status">{{ node.status }}</span>
          <span v-if="node.duration" class="node-duration">{{ node.duration.toFixed(1) }}s</span>
          <span v-if="node.error" class="node-error">{{ node.error }}</span>
        </div>
      </div>
    </div>

    <!-- WebSocket Status -->
    <div class="websocket-status">
      <span :class="['indicator', { connected }]"></span>
      {{ connected ? 'Connected' : 'Disconnected' }}
    </div>

    <!-- Real-Time Events -->
    <div v-if="events.length > 0" class="events-log">
      <h3>Real-Time Events</h3>
      <div class="events">
        <div v-for="(event, idx) in recentEvents" :key="idx" class="event">
          <span class="timestamp">{{ formatTime(event.timestamp) }}</span>
          <span class="type">{{ event.type }}</span>
          <span v-if="event.node_id" class="node">{{ event.node_id }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue';
import { useDAGWorkflow, useExecutionStatus, useWorkflowWebSocket } from '../composables/useDAGWorkflow';

const selectedWorkflowId = ref('sdlc_parallel');
const requirement = ref('');
const executionId = ref<string | null>(null);

const { workflowDetails, executeWorkflow, loading, error } = useDAGWorkflow(selectedWorkflowId.value);
const { status } = useExecutionStatus(executionId);
const { events, connected } = useWorkflowWebSocket(selectedWorkflowId);

const recentEvents = computed(() => events.value.slice(-10).reverse());

const handleExecute = async () => {
  try {
    const execution = await executeWorkflow(requirement.value);
    executionId.value = execution.execution_id;
  } catch (err) {
    console.error('Execution failed:', err);
  }
};

const formatTime = (timestamp: string) => {
  return new Date(timestamp).toLocaleTimeString();
};
</script>

<style scoped>
.workflow-executor {
  padding: 20px;
  max-width: 1200px;
  margin: 0 auto;
}

.node-state {
  padding: 10px;
  margin: 5px 0;
  border-radius: 4px;
  display: flex;
  justify-content: space-between;
}

.node-state.completed {
  background: #d4edda;
  border: 1px solid #c3e6cb;
}

.node-state.running {
  background: #fff3cd;
  border: 1px solid #ffeeba;
}

.node-state.failed {
  background: #f8d7da;
  border: 1px solid #f5c6cb;
}

.websocket-status .indicator {
  display: inline-block;
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: #dc3545;
  margin-right: 8px;
}

.websocket-status .indicator.connected {
  background: #28a745;
}
</style>
```

---

## Angular Integration

### Angular Service

```typescript
// services/dag-workflow.service.ts

import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, interval, Subject } from 'rxjs';
import { switchMap, takeWhile, shareReplay } from 'rxjs/operators';
import {
  WorkflowResponse,
  WorkflowDetails,
  ExecutionResponse,
  ExecutionStatusResponse,
  WebSocketEvent
} from '../models/dag-workflow.models';

@Injectable({
  providedIn: 'root'
})
export class DAGWorkflowService {
  private baseUrl = 'http://localhost:8003';
  private wsConnections = new Map<string, WebSocket>();
  private wsEvents$ = new Map<string, Subject<WebSocketEvent>>();

  constructor(private http: HttpClient) {}

  /**
   * Get all workflows
   */
  getWorkflows(): Observable<WorkflowResponse[]> {
    return this.http.get<WorkflowResponse[]>(`${this.baseUrl}/api/workflows`);
  }

  /**
   * Get workflow details
   */
  getWorkflowDetails(workflowId: string): Observable<WorkflowDetails> {
    return this.http.get<WorkflowDetails>(`${this.baseUrl}/api/workflows/${workflowId}`);
  }

  /**
   * Execute workflow
   */
  executeWorkflow(
    workflowId: string,
    requirement: string,
    initialContext?: any
  ): Observable<ExecutionResponse> {
    return this.http.post<ExecutionResponse>(
      `${this.baseUrl}/api/workflows/${workflowId}/execute`,
      { requirement, initial_context: initialContext }
    );
  }

  /**
   * Get execution status
   */
  getExecutionStatus(executionId: string): Observable<ExecutionStatusResponse> {
    return this.http.get<ExecutionStatusResponse>(
      `${this.baseUrl}/api/executions/${executionId}`
    );
  }

  /**
   * Poll execution status until completion
   */
  pollExecutionStatus(executionId: string, intervalMs = 2000): Observable<ExecutionStatusResponse> {
    return interval(intervalMs).pipe(
      switchMap(() => this.getExecutionStatus(executionId)),
      takeWhile(status =>
        status.status !== 'completed' &&
        status.status !== 'failed' &&
        status.status !== 'cancelled',
        true // Include final value
      ),
      shareReplay(1)
    );
  }

  /**
   * Connect to WebSocket for real-time updates
   */
  connectWebSocket(workflowId: string): Observable<WebSocketEvent> {
    // Return existing connection if available
    if (this.wsEvents$.has(workflowId)) {
      return this.wsEvents$.get(workflowId)!.asObservable();
    }

    const subject = new Subject<WebSocketEvent>();
    this.wsEvents$.set(workflowId, subject);

    const wsUrl = this.baseUrl.replace('http', 'ws');
    const ws = new WebSocket(`${wsUrl}/ws/workflow/${workflowId}`);
    this.wsConnections.set(workflowId, ws);

    ws.onopen = () => {
      // Keep-alive ping
      setInterval(() => {
        if (ws.readyState === WebSocket.OPEN) {
          ws.send('ping');
        }
      }, 30000);
    };

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      subject.next(data);
    };

    ws.onerror = (error) => {
      subject.error(error);
    };

    ws.onclose = () => {
      subject.complete();
      this.wsConnections.delete(workflowId);
      this.wsEvents$.delete(workflowId);
    };

    return subject.asObservable();
  }

  /**
   * Disconnect WebSocket
   */
  disconnectWebSocket(workflowId: string): void {
    const ws = this.wsConnections.get(workflowId);
    if (ws) {
      ws.close();
      this.wsConnections.delete(workflowId);
      this.wsEvents$.delete(workflowId);
    }
  }

  /**
   * Health check
   */
  healthCheck(): Observable<any> {
    return this.http.get(`${this.baseUrl}/health`);
  }
}
```

### Angular Component

```typescript
// components/workflow-executor/workflow-executor.component.ts

import { Component, OnInit, OnDestroy } from '@angular/core';
import { DAGWorkflowService } from '../../services/dag-workflow.service';
import { Subject } from 'rxjs';
import { takeUntil } from 'rxjs/operators';
import {
  WorkflowResponse,
  ExecutionStatusResponse,
  WebSocketEvent
} from '../../models/dag-workflow.models';

@Component({
  selector: 'app-workflow-executor',
  templateUrl: './workflow-executor.component.html',
  styleUrls: ['./workflow-executor.component.scss']
})
export class WorkflowExecutorComponent implements OnInit, OnDestroy {
  workflows: WorkflowResponse[] = [];
  selectedWorkflowId = 'sdlc_parallel';
  requirement = '';
  executionId: string | null = null;
  executionStatus: ExecutionStatusResponse | null = null;
  loading = false;
  error: string | null = null;
  events: WebSocketEvent[] = [];
  wsConnected = false;

  private destroy$ = new Subject<void>();

  constructor(private dagService: DAGWorkflowService) {}

  ngOnInit() {
    this.loadWorkflows();
    this.connectWebSocket();
  }

  ngOnDestroy() {
    this.destroy$.next();
    this.destroy$.complete();
    this.dagService.disconnectWebSocket(this.selectedWorkflowId);
  }

  loadWorkflows() {
    this.dagService.getWorkflows()
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: (workflows) => this.workflows = workflows,
        error: (err) => this.error = err.message
      });
  }

  connectWebSocket() {
    this.dagService.connectWebSocket(this.selectedWorkflowId)
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: (event) => {
          this.events.push(event);
          this.wsConnected = true;
        },
        error: (err) => {
          console.error('WebSocket error:', err);
          this.wsConnected = false;
        },
        complete: () => {
          this.wsConnected = false;
        }
      });
  }

  executeWorkflow() {
    if (!this.requirement) return;

    this.loading = true;
    this.error = null;

    this.dagService.executeWorkflow(this.selectedWorkflowId, this.requirement)
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: (execution) => {
          this.executionId = execution.execution_id;
          this.pollExecutionStatus(execution.execution_id);
        },
        error: (err) => {
          this.error = err.message;
          this.loading = false;
        }
      });
  }

  pollExecutionStatus(executionId: string) {
    this.dagService.pollExecutionStatus(executionId)
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: (status) => {
          this.executionStatus = status;

          if (status.status === 'completed' || status.status === 'failed') {
            this.loading = false;
          }
        },
        error: (err) => {
          this.error = err.message;
          this.loading = false;
        }
      });
  }

  get recentEvents() {
    return this.events.slice(-10).reverse();
  }
}
```

---

## State Management

### Redux/NgRx Pattern

```typescript
// store/dag-workflow.slice.ts (Redux Toolkit)

import { createSlice, createAsyncThunk, PayloadAction } from '@reduxjs/toolkit';
import { dagClient } from '../lib/dag-client';
import type {
  WorkflowResponse,
  WorkflowDetails,
  ExecutionResponse,
  ExecutionStatusResponse
} from '../lib/dag-client';

interface DAGWorkflowState {
  workflows: WorkflowResponse[];
  currentWorkflow: WorkflowDetails | null;
  currentExecution: ExecutionResponse | null;
  executionStatus: ExecutionStatusResponse | null;
  loading: boolean;
  error: string | null;
}

const initialState: DAGWorkflowState = {
  workflows: [],
  currentWorkflow: null,
  currentExecution: null,
  executionStatus: null,
  loading: false,
  error: null,
};

// Async thunks
export const fetchWorkflows = createAsyncThunk(
  'dagWorkflow/fetchWorkflows',
  async () => {
    return await dagClient.getWorkflows();
  }
);

export const fetchWorkflowDetails = createAsyncThunk(
  'dagWorkflow/fetchWorkflowDetails',
  async (workflowId: string) => {
    return await dagClient.getWorkflowDetails(workflowId);
  }
);

export const executeWorkflow = createAsyncThunk(
  'dagWorkflow/executeWorkflow',
  async ({ workflowId, requirement }: { workflowId: string; requirement: string }) => {
    return await dagClient.executeWorkflow(workflowId, requirement);
  }
);

export const fetchExecutionStatus = createAsyncThunk(
  'dagWorkflow/fetchExecutionStatus',
  async (executionId: string) => {
    return await dagClient.getExecutionStatus(executionId);
  }
);

// Slice
const dagWorkflowSlice = createSlice({
  name: 'dagWorkflow',
  initialState,
  reducers: {
    clearError: (state) => {
      state.error = null;
    },
    updateExecutionStatus: (state, action: PayloadAction<ExecutionStatusResponse>) => {
      state.executionStatus = action.payload;
    },
  },
  extraReducers: (builder) => {
    builder
      // Fetch workflows
      .addCase(fetchWorkflows.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(fetchWorkflows.fulfilled, (state, action) => {
        state.loading = false;
        state.workflows = action.payload;
      })
      .addCase(fetchWorkflows.rejected, (state, action) => {
        state.loading = false;
        state.error = action.error.message || 'Failed to fetch workflows';
      })

      // Fetch workflow details
      .addCase(fetchWorkflowDetails.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(fetchWorkflowDetails.fulfilled, (state, action) => {
        state.loading = false;
        state.currentWorkflow = action.payload;
      })
      .addCase(fetchWorkflowDetails.rejected, (state, action) => {
        state.loading = false;
        state.error = action.error.message || 'Failed to fetch workflow details';
      })

      // Execute workflow
      .addCase(executeWorkflow.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(executeWorkflow.fulfilled, (state, action) => {
        state.loading = false;
        state.currentExecution = action.payload;
      })
      .addCase(executeWorkflow.rejected, (state, action) => {
        state.loading = false;
        state.error = action.error.message || 'Failed to execute workflow';
      })

      // Fetch execution status
      .addCase(fetchExecutionStatus.fulfilled, (state, action) => {
        state.executionStatus = action.payload;
      });
  },
});

export const { clearError, updateExecutionStatus } = dagWorkflowSlice.actions;
export default dagWorkflowSlice.reducer;
```

---

## Real-Time Updates

### Combining Polling and WebSocket

```typescript
// utils/workflow-monitor.ts

import { dagClient } from '../lib/dag-client';
import type { ExecutionStatusResponse, WebSocketEvent } from '../lib/dag-client';

export class WorkflowMonitor {
  private ws: WebSocket | null = null;
  private pollInterval: ReturnType<typeof setInterval> | null = null;
  private listeners: Map<string, Set<(data: any) => void>> = new Map();

  constructor(
    private workflowId: string,
    private executionId: string
  ) {}

  /**
   * Start monitoring with both WebSocket and polling fallback
   */
  start(onUpdate: (status: ExecutionStatusResponse) => void) {
    // Connect WebSocket for real-time updates
    this.ws = dagClient.connectWebSocket(this.workflowId, {
      onMessage: (event: WebSocketEvent) => {
        this.handleWebSocketEvent(event, onUpdate);
      },
      onError: () => {
        // Fallback to polling if WebSocket fails
        this.startPolling(onUpdate);
      },
      onClose: () => {
        // Restart polling if WebSocket closes
        this.startPolling(onUpdate);
      },
    });

    // Also poll as backup (less frequently)
    this.pollInterval = setInterval(async () => {
      try {
        const status = await dagClient.getExecutionStatus(this.executionId);
        onUpdate(status);

        if (status.status === 'completed' || status.status === 'failed') {
          this.stop();
        }
      } catch (err) {
        console.error('Polling error:', err);
      }
    }, 5000); // Poll every 5 seconds
  }

  /**
   * Stop monitoring
   */
  stop() {
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }

    if (this.pollInterval) {
      clearInterval(this.pollInterval);
      this.pollInterval = null;
    }
  }

  /**
   * Handle WebSocket events and trigger status update
   */
  private async handleWebSocketEvent(
    event: WebSocketEvent,
    onUpdate: (status: ExecutionStatusResponse) => void
  ) {
    // On any significant event, fetch latest status
    if (event.type !== 'pong') {
      try {
        const status = await dagClient.getExecutionStatus(this.executionId);
        onUpdate(status);

        if (status.status === 'completed' || status.status === 'failed') {
          this.stop();
        }
      } catch (err) {
        console.error('Failed to fetch status after WebSocket event:', err);
      }
    }
  }

  /**
   * Fallback to polling only
   */
  private startPolling(onUpdate: (status: ExecutionStatusResponse) => void) {
    if (this.pollInterval) return; // Already polling

    this.pollInterval = setInterval(async () => {
      try {
        const status = await dagClient.getExecutionStatus(this.executionId);
        onUpdate(status);

        if (status.status === 'completed' || status.status === 'failed') {
          this.stop();
        }
      } catch (err) {
        console.error('Polling error:', err);
      }
    }, 2000); // Poll every 2 seconds
  }
}

// Usage
const monitor = new WorkflowMonitor('sdlc_parallel', 'exec_123');

monitor.start((status) => {
  console.log('Status update:', status);
  // Update UI with new status
});

// Clean up when done
// monitor.stop();
```

---

## Error Handling

### Comprehensive Error Handling Pattern

```typescript
// utils/error-handler.ts

export class DAGWorkflowError extends Error {
  constructor(
    message: string,
    public code: string,
    public details?: any
  ) {
    super(message);
    this.name = 'DAGWorkflowError';
  }
}

export async function handleAPIError<T>(
  promise: Promise<T>,
  context: string
): Promise<T> {
  try {
    return await promise;
  } catch (error: any) {
    // Network error
    if (error instanceof TypeError && error.message.includes('fetch')) {
      throw new DAGWorkflowError(
        'Unable to connect to DAG API server. Please check if the server is running.',
        'NETWORK_ERROR',
        { context, originalError: error.message }
      );
    }

    // HTTP error
    if (error.response) {
      const status = error.response.status;
      const data = await error.response.json().catch(() => ({}));

      if (status === 400) {
        throw new DAGWorkflowError(
          data.message || 'Invalid request',
          'VALIDATION_ERROR',
          { context, details: data }
        );
      }

      if (status === 404) {
        throw new DAGWorkflowError(
          `Resource not found: ${context}`,
          'NOT_FOUND',
          { context }
        );
      }

      if (status === 500) {
        throw new DAGWorkflowError(
          'Internal server error. Please try again later.',
          'SERVER_ERROR',
          { context, details: data }
        );
      }
    }

    // Unknown error
    throw new DAGWorkflowError(
      `Unexpected error: ${error.message}`,
      'UNKNOWN_ERROR',
      { context, originalError: error }
    );
  }
}

// Usage
try {
  const workflows = await handleAPIError(
    dagClient.getWorkflows(),
    'fetching workflows'
  );
} catch (error) {
  if (error instanceof DAGWorkflowError) {
    console.error(`Error ${error.code}:`, error.message);
    // Show user-friendly error message
    showErrorNotification(error.message);
  }
}
```

---

## Best Practices

### 1. Connection Management

```typescript
// ✅ Good: Reuse connections
const ws = dagClient.connectWebSocket('sdlc_parallel', handlers);
// Use same connection throughout component lifecycle

// ❌ Bad: Create multiple connections
setInterval(() => {
  const ws = dagClient.connectWebSocket('sdlc_parallel', handlers); // Memory leak!
}, 1000);
```

### 2. Polling Strategy

```typescript
// ✅ Good: Stop polling when done
if (status.status === 'completed' || status.status === 'failed') {
  clearInterval(pollInterval);
}

// ❌ Bad: Never stop polling
setInterval(() => {
  fetchStatus(); // Runs forever!
}, 2000);
```

### 3. Error Boundaries

```typescript
// React Error Boundary for workflow errors
class WorkflowErrorBoundary extends React.Component {
  state = { hasError: false, error: null };

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    console.error('Workflow error:', error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return <ErrorDisplay error={this.state.error} />;
    }
    return this.props.children;
  }
}
```

### 4. Performance Optimization

```typescript
// ✅ Good: Debounce status updates
import { debounce } from 'lodash';

const updateStatus = debounce((status) => {
  setExecutionStatus(status);
}, 100);

// ✅ Good: Limit event history
const addEvent = (event) => {
  setEvents(prev => [...prev.slice(-100), event]); // Keep last 100
};

// ✅ Good: Virtualize long lists
import { FixedSizeList } from 'react-window';

<FixedSizeList
  height={400}
  itemCount={nodeStates.length}
  itemSize={50}
>
  {NodeStateRow}
</FixedSizeList>
```

### 5. TypeScript Types

```typescript
// Always use proper typing
const executeWorkflow = async (
  workflowId: string,
  requirement: string
): Promise<ExecutionResponse> => {
  return await dagClient.executeWorkflow(workflowId, requirement);
};

// Use type guards
function isCompletedStatus(
  status: ExecutionStatusResponse
): status is ExecutionStatusResponse & { status: 'completed' } {
  return status.status === 'completed';
}

if (isCompletedStatus(status)) {
  // TypeScript knows status is 'completed' here
  console.log('Workflow completed at:', status.completed_at);
}
```

---

## Example Applications

### Complete React Application

See `/examples/react-dag-workflow-ui/` for a complete React application with:
- Workflow selection and execution
- Real-time progress monitoring
- Node-level status visualization
- WebSocket integration
- Error handling
- TypeScript support

### Complete Vue Application

See `/examples/vue-dag-workflow-ui/` for a complete Vue 3 application with:
- Composition API
- Pinia state management
- Real-time updates
- TypeScript support

### Complete Angular Application

See `/examples/angular-dag-workflow-ui/` for a complete Angular application with:
- Services and dependency injection
- RxJS observables
- Real-time monitoring
- TypeScript support

---

## Appendix

### API Server Configuration

**Port**: 8003 (configurable in `dag_api_server_robust.py`)

**CORS**: Enabled for:
- http://localhost:3000
- http://localhost:4200
- http://localhost:4300

**Database**: SQLite (development) / PostgreSQL (production)

**Timeout**: 2 hours default for workflow execution

**Connection Limits**:
- Max 1000 total WebSocket connections
- Max 100 WebSocket connections per workflow

### TypeScript Definitions

Complete TypeScript type definitions are available in `/types/dag-workflow.d.ts`

### Testing

See `/tests/frontend-integration/` for:
- Unit tests for client library
- Integration tests for API
- E2E tests for complete workflows

---

**Document Version**: 1.0.0
**Last Updated**: 2025-10-11
**Maintainer**: Maestro Platform Team
**Status**: ✅ Production Ready
