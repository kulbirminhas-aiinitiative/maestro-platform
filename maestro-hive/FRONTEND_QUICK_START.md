# Frontend Integration Quick Start Guide

**Get started with DAG Workflow API in 5 minutes**

---

## 1. Install Dependencies

### React
```bash
npm install --save-dev @types/node

# Or with Yarn
yarn add -D @types/node
```

### Vue.js
```bash
npm install vue@next

# Or with Yarn
yarn add vue@next
```

### Angular
```bash
npm install @angular/common@latest @angular/core@latest
```

---

## 2. Copy the Client Library

Copy the TypeScript client library to your project:

```bash
# From maestro-hive directory
cp frontend/dag-workflow-client.ts your-project/src/lib/
```

---

## 3. Quick Examples

### React - Execute Workflow

```typescript
import React, { useState } from 'react';
import { dagClient } from './lib/dag-workflow-client';

export function QuickWorkflowExecutor() {
  const [executionId, setExecutionId] = useState<string | null>(null);
  const [progress, setProgress] = useState(0);

  const handleExecute = async () => {
    // Start execution
    const execution = await dagClient.executeWorkflow(
      'sdlc_parallel',
      'Build a REST API for user authentication'
    );

    setExecutionId(execution.execution_id);

    // Poll for updates
    await dagClient.pollExecution(execution.execution_id, (status) => {
      setProgress(status.progress_percent);
    });
  };

  return (
    <div>
      <button onClick={handleExecute}>Execute Workflow</button>
      {executionId && <p>Progress: {progress.toFixed(1)}%</p>}
    </div>
  );
}
```

### Vue.js - Execute Workflow

```vue
<template>
  <div>
    <button @click="handleExecute">Execute Workflow</button>
    <p v-if="executionId">Progress: {{ progress.toFixed(1) }}%</p>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import { dagClient } from './lib/dag-workflow-client';

const executionId = ref<string | null>(null);
const progress = ref(0);

const handleExecute = async () => {
  // Start execution
  const execution = await dagClient.executeWorkflow(
    'sdlc_parallel',
    'Build a REST API for user authentication'
  );

  executionId.value = execution.execution_id;

  // Poll for updates
  await dagClient.pollExecution(execution.execution_id, (status) => {
    progress.value = status.progress_percent;
  });
};
</script>
```

### Angular - Execute Workflow

```typescript
import { Component } from '@angular/core';
import { dagClient } from './lib/dag-workflow-client';

@Component({
  selector: 'app-quick-executor',
  template: `
    <button (click)="handleExecute()">Execute Workflow</button>
    <p *ngIf="executionId">Progress: {{ progress }}%</p>
  `
})
export class QuickExecutorComponent {
  executionId: string | null = null;
  progress = 0;

  async handleExecute() {
    // Start execution
    const execution = await dagClient.executeWorkflow(
      'sdlc_parallel',
      'Build a REST API for user authentication'
    );

    this.executionId = execution.execution_id;

    // Poll for updates
    await dagClient.pollExecution(execution.execution_id, (status) => {
      this.progress = Math.round(status.progress_percent);
    });
  }
}
```

---

## 4. Real-Time Updates with WebSocket

### React

```typescript
import { useEffect, useState } from 'react';
import { dagClient, type WebSocketEvent } from './lib/dag-workflow-client';

export function RealtimeWorkflow() {
  const [events, setEvents] = useState<WebSocketEvent[]>([]);

  useEffect(() => {
    const ws = dagClient.connectWebSocket('sdlc_parallel', {
      onMessage: (event) => {
        setEvents(prev => [...prev, event]);
        console.log('Event:', event.type, event.node_id);
      }
    });

    return () => ws.close();
  }, []);

  return (
    <div>
      <h3>Real-Time Events</h3>
      {events.map((event, idx) => (
        <div key={idx}>{event.type}: {event.node_id}</div>
      ))}
    </div>
  );
}
```

### Vue.js

```vue
<template>
  <div>
    <h3>Real-Time Events</h3>
    <div v-for="(event, idx) in events" :key="idx">
      {{ event.type }}: {{ event.node_id }}
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue';
import { dagClient, type WebSocketEvent } from './lib/dag-workflow-client';

const events = ref<WebSocketEvent[]>([]);
let ws: WebSocket | null = null;

onMounted(() => {
  ws = dagClient.connectWebSocket('sdlc_parallel', {
    onMessage: (event) => {
      events.value.push(event);
      console.log('Event:', event.type, event.node_id);
    }
  });
});

onUnmounted(() => {
  ws?.close();
});
</script>
```

---

## 5. Error Handling

```typescript
import { dagClient, DAGWorkflowError } from './lib/dag-workflow-client';

async function executeWithErrorHandling() {
  try {
    const execution = await dagClient.executeWorkflow(
      'sdlc_parallel',
      'Build a REST API'
    );

    console.log('Started:', execution.execution_id);

    const finalStatus = await dagClient.pollExecution(execution.execution_id);

    if (finalStatus.status === 'completed') {
      console.log('Success!');
    } else {
      console.error('Failed:', finalStatus.status);
    }

  } catch (error) {
    if (error instanceof DAGWorkflowError) {
      switch (error.code) {
        case 'NETWORK_ERROR':
          console.error('Cannot connect to API server');
          break;
        case 'VALIDATION_ERROR':
          console.error('Invalid request:', error.message);
          break;
        case 'TIMEOUT_ERROR':
          console.error('Request timeout');
          break;
        default:
          console.error('Error:', error.message);
      }
    }
  }
}
```

---

## 6. Complete Example

```typescript
import React, { useState, useEffect } from 'react';
import {
  dagClient,
  DAGWorkflowError,
  type ExecutionStatusResponse
} from './lib/dag-workflow-client';

export function CompleteWorkflowExample() {
  const [requirement, setRequirement] = useState('');
  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState<ExecutionStatusResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleExecute = async () => {
    if (!requirement) return;

    setLoading(true);
    setError(null);

    try {
      // Start execution
      const execution = await dagClient.executeWorkflow(
        'sdlc_parallel',
        requirement
      );

      // Poll for status updates
      await dagClient.pollExecution(
        execution.execution_id,
        (newStatus) => {
          setStatus(newStatus);
        }
      );

      setLoading(false);

    } catch (err) {
      if (err instanceof DAGWorkflowError) {
        setError(err.message);
      } else {
        setError('An unexpected error occurred');
      }
      setLoading(false);
    }
  };

  return (
    <div className="workflow-executor">
      <h2>DAG Workflow Executor</h2>

      <textarea
        value={requirement}
        onChange={(e) => setRequirement(e.target.value)}
        placeholder="Enter your project requirement..."
        rows={4}
        style={{ width: '100%', padding: '10px' }}
      />

      <button
        onClick={handleExecute}
        disabled={loading || !requirement}
        style={{ marginTop: '10px', padding: '10px 20px' }}
      >
        {loading ? 'Executing...' : 'Execute Workflow'}
      </button>

      {error && (
        <div style={{ color: 'red', marginTop: '10px' }}>
          Error: {error}
        </div>
      )}

      {status && (
        <div style={{ marginTop: '20px' }}>
          <h3>Status: {status.status}</h3>
          <p>Progress: {status.progress_percent.toFixed(1)}%</p>
          <p>Completed: {status.completed_nodes}/{status.total_nodes} nodes</p>

          <div style={{ marginTop: '20px' }}>
            <h4>Node Status:</h4>
            {status.node_states.map(node => (
              <div
                key={node.node_id}
                style={{
                  padding: '10px',
                  margin: '5px 0',
                  backgroundColor:
                    node.status === 'completed' ? '#d4edda' :
                    node.status === 'running' ? '#fff3cd' :
                    node.status === 'failed' ? '#f8d7da' : '#e2e3e5',
                  borderRadius: '4px'
                }}
              >
                <strong>{node.node_id}</strong>: {node.status}
                {node.duration && ` (${node.duration.toFixed(1)}s)`}
                {node.error && <div style={{ color: 'red' }}>{node.error}</div>}
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

## 7. Configuration

### Environment Variables

Create a `.env` file:

```bash
# DAG API Server URL
REACT_APP_DAG_API_URL=http://localhost:8003

# Or for Vue
VITE_DAG_API_URL=http://localhost:8003

# Or for Angular
NG_DAG_API_URL=http://localhost:8003
```

### Custom Configuration

```typescript
import { DAGWorkflowClient } from './lib/dag-workflow-client';

const customClient = new DAGWorkflowClient({
  baseUrl: process.env.REACT_APP_DAG_API_URL || 'http://localhost:8003',
  timeout: 60000, // 60 seconds
  retry: {
    maxAttempts: 3,
    delayMs: 1000
  },
  headers: {
    'X-Custom-Header': 'value'
  }
});

export { customClient as dagClient };
```

---

## 8. API Server Setup

### Start the DAG API Server

```bash
cd /home/ec2-user/projects/maestro-platform/maestro-hive

# Start the server
USE_SQLITE=true python3 dag_api_server_robust.py

# Server will start on http://localhost:8003
```

### Verify Server is Running

```bash
curl http://localhost:8003/health

# Should return:
# {
#   "status": "healthy",
#   "database": { "connected": true, "type": "SQLite" },
#   ...
# }
```

---

## 9. Testing

### Test API Connection

```typescript
import { dagClient } from './lib/dag-workflow-client';

async function testConnection() {
  try {
    const health = await dagClient.healthCheck();
    console.log('API is healthy:', health.status);

    const workflows = await dagClient.getWorkflows();
    console.log('Available workflows:', workflows.length);

    return true;
  } catch (error) {
    console.error('Connection test failed:', error);
    return false;
  }
}

testConnection();
```

---

## 10. Common Patterns

### Pattern 1: Execute and Wait

```typescript
const execution = await dagClient.executeWorkflow('sdlc_parallel', requirement);
const finalStatus = await dagClient.waitForStatus(execution.execution_id, 'completed');
console.log('Workflow completed!');
```

### Pattern 2: Real-Time Progress

```typescript
const execution = await dagClient.executeWorkflow('sdlc_parallel', requirement);

dagClient.pollExecution(execution.execution_id, (status) => {
  console.log(`Progress: ${status.progress_percent}%`);
  updateProgressBar(status.progress_percent);
});
```

### Pattern 3: Combined Polling + WebSocket

```typescript
// WebSocket for instant updates
const ws = dagClient.connectWebSocket('sdlc_parallel', {
  onMessage: (event) => {
    if (event.type === 'node_completed') {
      showNotification(`${event.node_id} completed!`);
    }
  }
});

// Polling as backup
const execution = await dagClient.executeWorkflow('sdlc_parallel', requirement);
await dagClient.pollExecution(execution.execution_id, updateUI);

ws.close();
```

---

## Next Steps

1. **Read Full Documentation**: See `FRONTEND_DAG_INTEGRATION_GUIDE.md` for complete details
2. **Explore Examples**: Check the `/examples` directory for complete applications
3. **Customize**: Modify the client library to fit your needs
4. **Deploy**: Configure for production with proper error handling

---

## Troubleshooting

### Issue: Cannot connect to API

**Solution**: Make sure the DAG API server is running on port 8003

```bash
lsof -i :8003
# Should show python3 process
```

### Issue: CORS errors

**Solution**: The API server allows these origins:
- http://localhost:3000 (React)
- http://localhost:4200 (Angular)

Add your origin in `dag_api_server_robust.py` if different.

### Issue: WebSocket not connecting

**Solution**: Check WebSocket URL format:
- HTTP: `http://localhost:8003`
- WebSocket: `ws://localhost:8003`

The client library handles this automatically.

---

## Support

- **Documentation**: `FRONTEND_DAG_INTEGRATION_GUIDE.md`
- **API Reference**: See client library comments
- **Examples**: `/examples` directory
- **Issues**: Check server logs for errors

---

**Happy Coding! 🚀**
