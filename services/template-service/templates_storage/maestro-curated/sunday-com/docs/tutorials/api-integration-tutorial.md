# API Integration Tutorial

## 🎯 Overview

This tutorial demonstrates how to integrate with the Sunday.com API to build custom applications, automate workflows, and sync data with external systems. We'll cover REST API usage, webhook implementation, and real-time WebSocket connections.

## 📋 Prerequisites

- Basic knowledge of HTTP/REST APIs
- Familiarity with JavaScript/TypeScript or Python
- Sunday.com account with API access
- Development environment set up

## 🔑 Authentication Setup

### Getting API Credentials

1. **Log into** your Sunday.com account
2. **Navigate to** Settings > Integrations > API Keys
3. **Click** "Generate New API Key"
4. **Copy** your API key and store it securely
5. **Note** your organization ID for API calls

### Authentication Methods

Sunday.com supports multiple authentication methods:

#### Method 1: API Key (Recommended for server-side)
```bash
curl -H "Authorization: Bearer your_api_key" \
  https://api.sunday.com/v1/workspaces
```

#### Method 2: OAuth 2.0 (Recommended for user applications)
```javascript
// Step 1: Redirect user to authorization URL
const authUrl = `https://auth.sunday.com/oauth/authorize?` +
  `client_id=${CLIENT_ID}&` +
  `redirect_uri=${REDIRECT_URI}&` +
  `response_type=code&` +
  `scope=read:workspaces write:items`;

window.location.href = authUrl;

// Step 2: Exchange code for token
const tokenResponse = await fetch('https://auth.sunday.com/oauth/token', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    grant_type: 'authorization_code',
    client_id: CLIENT_ID,
    client_secret: CLIENT_SECRET,
    code: authorizationCode,
    redirect_uri: REDIRECT_URI,
  }),
});

const { access_token } = await tokenResponse.json();
```

## 🔧 Building Your First Integration

### Example 1: Task Sync Integration

Let's build an integration that syncs tasks between Sunday.com and an external system.

#### Setup the API Client

```javascript
class SundayAPIClient {
  constructor(apiKey) {
    this.apiKey = apiKey;
    this.baseURL = 'https://api.sunday.com/v1';
  }

  async request(method, endpoint, data = null) {
    const config = {
      method,
      headers: {
        'Authorization': `Bearer ${this.apiKey}`,
        'Content-Type': 'application/json',
      },
    };

    if (data) {
      config.body = JSON.stringify(data);
    }

    const response = await fetch(`${this.baseURL}${endpoint}`, config);

    if (!response.ok) {
      const error = await response.json();
      throw new Error(`API Error: ${error.error.message}`);
    }

    return response.json();
  }

  // Workspace methods
  async getWorkspaces() {
    return this.request('GET', '/workspaces');
  }

  // Board methods
  async getBoards(workspaceId) {
    return this.request('GET', `/workspaces/${workspaceId}/boards`);
  }

  async getBoard(boardId, include = []) {
    const params = include.length > 0 ? `?include=${include.join(',')}` : '';
    return this.request('GET', `/boards/${boardId}${params}`);
  }

  // Item methods
  async getItems(boardId, filters = {}) {
    const params = new URLSearchParams();

    Object.entries(filters).forEach(([key, value]) => {
      if (Array.isArray(value)) {
        value.forEach(v => params.append(`filter[${key}]`, v));
      } else {
        params.append(`filter[${key}]`, value);
      }
    });

    const queryString = params.toString();
    const url = `/boards/${boardId}/items${queryString ? `?${queryString}` : ''}`;

    return this.request('GET', url);
  }

  async createItem(boardId, itemData) {
    return this.request('POST', `/boards/${boardId}/items`, itemData);
  }

  async updateItem(itemId, itemData) {
    return this.request('PUT', `/items/${itemId}`, itemData);
  }

  async deleteItem(itemId) {
    return this.request('DELETE', `/items/${itemId}`);
  }

  // Comment methods
  async addComment(itemId, content, mentions = []) {
    return this.request('POST', `/items/${itemId}/comments`, {
      content,
      mentions,
    });
  }
}
```

#### Sync Tasks from External System

```javascript
class TaskSyncService {
  constructor(sundayClient, externalAPI) {
    this.sunday = sundayClient;
    this.external = externalAPI;
    this.boardId = 'your_board_id';
  }

  async syncTasksToSunday() {
    try {
      // Get external tasks
      const externalTasks = await this.external.getTasks();

      // Get existing Sunday items
      const sundayResponse = await this.sunday.getItems(this.boardId);
      const sundayItems = sundayResponse.data;

      // Create a map of external IDs to Sunday items
      const existingItems = new Map();
      sundayItems.forEach(item => {
        const externalId = item.data.externalId;
        if (externalId) {
          existingItems.set(externalId, item);
        }
      });

      // Process each external task
      for (const task of externalTasks) {
        const existingItem = existingItems.get(task.id);

        if (existingItem) {
          // Update existing item if changed
          if (this.hasChanges(task, existingItem)) {
            await this.updateSundayItem(existingItem.id, task);
            console.log(`Updated item: ${task.title}`);
          }
        } else {
          // Create new item
          await this.createSundayItem(task);
          console.log(`Created item: ${task.title}`);
        }
      }

      console.log('Sync completed successfully');
    } catch (error) {
      console.error('Sync failed:', error);
      throw error;
    }
  }

  hasChanges(externalTask, sundayItem) {
    return (
      externalTask.title !== sundayItem.name ||
      externalTask.status !== sundayItem.data.status ||
      externalTask.assignee !== sundayItem.data.assignee ||
      new Date(externalTask.updatedAt) > new Date(sundayItem.updatedAt)
    );
  }

  async createSundayItem(task) {
    const itemData = {
      name: task.title,
      description: task.description,
      data: {
        status: this.mapStatus(task.status),
        priority: task.priority,
        externalId: task.id,
        assignee: task.assignee,
        dueDate: task.dueDate,
      },
    };

    return this.sunday.createItem(this.boardId, itemData);
  }

  async updateSundayItem(itemId, task) {
    const itemData = {
      name: task.title,
      description: task.description,
      data: {
        status: this.mapStatus(task.status),
        priority: task.priority,
        assignee: task.assignee,
        dueDate: task.dueDate,
      },
    };

    return this.sunday.updateItem(itemId, itemData);
  }

  mapStatus(externalStatus) {
    const statusMap = {
      'open': 'Not Started',
      'in_progress': 'In Progress',
      'review': 'Review',
      'done': 'Done',
    };

    return statusMap[externalStatus] || 'Not Started';
  }
}

// Usage
const sundayClient = new SundayAPIClient('your_api_key');
const syncService = new TaskSyncService(sundayClient, externalAPI);

// Run sync
await syncService.syncTasksToSunday();
```

### Example 2: Automated Reporting

Create automated reports from Sunday.com data:

```javascript
class ReportingService {
  constructor(sundayClient) {
    this.sunday = sundayClient;
  }

  async generateProductivityReport(workspaceId, dateRange) {
    const boards = await this.sunday.getBoards(workspaceId);
    const report = {
      workspace: workspaceId,
      period: dateRange,
      boards: [],
      summary: {
        totalItems: 0,
        completedItems: 0,
        inProgressItems: 0,
        overdueTasks: 0,
      },
    };

    for (const board of boards.data) {
      const boardReport = await this.generateBoardReport(board, dateRange);
      report.boards.push(boardReport);

      // Update summary
      report.summary.totalItems += boardReport.totalItems;
      report.summary.completedItems += boardReport.completedItems;
      report.summary.inProgressItems += boardReport.inProgressItems;
      report.summary.overdueTasks += boardReport.overdueTasks;
    }

    // Calculate completion rate
    report.summary.completionRate =
      (report.summary.completedItems / report.summary.totalItems * 100).toFixed(1);

    return report;
  }

  async generateBoardReport(board, dateRange) {
    const items = await this.sunday.getItems(board.id, {
      created_at: {
        gte: dateRange.start,
        lte: dateRange.end,
      },
    });

    const boardReport = {
      boardId: board.id,
      boardName: board.name,
      totalItems: items.data.length,
      completedItems: 0,
      inProgressItems: 0,
      overdueTasks: 0,
      teamPerformance: {},
    };

    const now = new Date();

    items.data.forEach(item => {
      // Count by status
      if (item.data.status === 'Done') {
        boardReport.completedItems++;
      } else if (item.data.status === 'In Progress') {
        boardReport.inProgressItems++;
      }

      // Count overdue
      if (item.data.dueDate && new Date(item.data.dueDate) < now && item.data.status !== 'Done') {
        boardReport.overdueTasks++;
      }

      // Team performance
      item.assignees.forEach(assignee => {
        if (!boardReport.teamPerformance[assignee.id]) {
          boardReport.teamPerformance[assignee.id] = {
            name: assignee.fullName,
            assigned: 0,
            completed: 0,
          };
        }

        boardReport.teamPerformance[assignee.id].assigned++;
        if (item.data.status === 'Done') {
          boardReport.teamPerformance[assignee.id].completed++;
        }
      });
    });

    return boardReport;
  }

  async sendReportEmail(report, recipients) {
    // Generate HTML report
    const html = this.generateReportHTML(report);

    // Send via email service (example with SendGrid)
    const msg = {
      to: recipients,
      from: 'reports@sunday.com',
      subject: `Weekly Productivity Report - ${report.period.start} to ${report.period.end}`,
      html: html,
    };

    await sgMail.send(msg);
  }

  generateReportHTML(report) {
    return `
      <html>
        <body>
          <h1>Productivity Report</h1>
          <h2>Summary</h2>
          <ul>
            <li>Total Items: ${report.summary.totalItems}</li>
            <li>Completed: ${report.summary.completedItems}</li>
            <li>Completion Rate: ${report.summary.completionRate}%</li>
            <li>Overdue Tasks: ${report.summary.overdueTasks}</li>
          </ul>

          <h2>Board Breakdown</h2>
          ${report.boards.map(board => `
            <h3>${board.boardName}</h3>
            <p>Completed: ${board.completedItems}/${board.totalItems}</p>
            <p>Overdue: ${board.overdueTasks}</p>
          `).join('')}
        </body>
      </html>
    `;
  }
}

// Schedule weekly reports
const reportingService = new ReportingService(sundayClient);

async function weeklyReport() {
  const lastWeek = {
    start: new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString(),
    end: new Date().toISOString(),
  };

  const report = await reportingService.generateProductivityReport('ws_123', lastWeek);
  await reportingService.sendReportEmail(report, ['manager@company.com']);
}

// Run every Monday at 9 AM
const cron = require('node-cron');
cron.schedule('0 9 * * MON', weeklyReport);
```

## 🔗 Webhook Integration

### Setting Up Webhooks

Webhooks allow you to receive real-time notifications when events occur in Sunday.com.

#### Create Webhook Endpoint

```javascript
const express = require('express');
const crypto = require('crypto');
const app = express();

// Middleware to capture raw body for signature verification
app.use('/webhooks', express.raw({ type: 'application/json' }));

function verifyWebhookSignature(payload, signature, secret) {
  const expectedSignature = crypto
    .createHmac('sha256', secret)
    .update(payload)
    .digest('hex');

  return crypto.timingSafeEqual(
    Buffer.from(signature),
    Buffer.from(`sha256=${expectedSignature}`)
  );
}

app.post('/webhooks/sunday', (req, res) => {
  const signature = req.headers['x-sunday-signature'];
  const payload = req.body;
  const secret = process.env.WEBHOOK_SECRET;

  // Verify signature
  if (!verifyWebhookSignature(payload, signature, secret)) {
    console.error('Invalid webhook signature');
    return res.status(401).send('Unauthorized');
  }

  try {
    const event = JSON.parse(payload.toString());
    handleWebhookEvent(event);
    res.status(200).send('OK');
  } catch (error) {
    console.error('Webhook processing error:', error);
    res.status(400).send('Bad Request');
  }
});

function handleWebhookEvent(event) {
  console.log(`Received event: ${event.event}`);

  switch (event.event) {
    case 'item.created':
      handleItemCreated(event.data);
      break;
    case 'item.updated':
      handleItemUpdated(event.data);
      break;
    case 'item.deleted':
      handleItemDeleted(event.data);
      break;
    case 'comment.added':
      handleCommentAdded(event.data);
      break;
    default:
      console.log(`Unhandled event type: ${event.event}`);
  }
}

async function handleItemCreated(data) {
  const { item, board, user } = data;

  console.log(`New item created: ${item.name} by ${user.name}`);

  // Example: Send Slack notification
  await sendSlackNotification({
    text: `📝 New task created: *${item.name}*`,
    attachments: [{
      color: 'good',
      fields: [
        { title: 'Board', value: board.name, short: true },
        { title: 'Created by', value: user.name, short: true },
        { title: 'Status', value: item.data.status, short: true },
      ],
    }],
  });
}

async function handleItemUpdated(data) {
  const { item, changes, user } = data;

  // Check if status changed to "Done"
  if (changes.status && changes.status.new === 'Done') {
    console.log(`Task completed: ${item.name}`);

    // Update external system
    await updateExternalSystem(item.data.externalId, { status: 'completed' });

    // Send congratulations message
    await sundayClient.addComment(item.id,
      `🎉 Congratulations @${user.name} on completing this task!`
    );
  }
}

async function sendSlackNotification(message) {
  const response = await fetch(process.env.SLACK_WEBHOOK_URL, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(message),
  });

  if (!response.ok) {
    console.error('Failed to send Slack notification');
  }
}

app.listen(3000, () => {
  console.log('Webhook server running on port 3000');
});
```

#### Register Your Webhook

```javascript
async function registerWebhook() {
  const webhookConfig = {
    url: 'https://your-server.com/webhooks/sunday',
    events: [
      'item.created',
      'item.updated',
      'item.deleted',
      'comment.added',
    ],
    secret: process.env.WEBHOOK_SECRET,
    active: true,
    filters: {
      boardIds: ['board_123', 'board_456'],
    },
  };

  const response = await sundayClient.request('POST', '/webhooks', webhookConfig);
  console.log('Webhook registered:', response.data);
}
```

## ⚡ Real-time Integration with WebSockets

### WebSocket Client Implementation

```javascript
class SundayRealtimeClient {
  constructor(token) {
    this.token = token;
    this.socket = null;
    this.subscriptions = new Map();
  }

  connect() {
    return new Promise((resolve, reject) => {
      this.socket = io('wss://api.sunday.com', {
        auth: { token: this.token },
        transports: ['websocket'],
      });

      this.socket.on('connect', () => {
        console.log('Connected to Sunday.com real-time server');
        resolve();
      });

      this.socket.on('connect_error', (error) => {
        console.error('Connection failed:', error);
        reject(error);
      });

      this.socket.on('disconnect', () => {
        console.log('Disconnected from real-time server');
      });

      // Handle reconnection
      this.socket.on('reconnect', () => {
        console.log('Reconnected to real-time server');
        this.resubscribeAll();
      });

      this.setupEventHandlers();
    });
  }

  setupEventHandlers() {
    this.socket.on('item-updated', (data) => {
      this.handleItemUpdate(data);
    });

    this.socket.on('comment-added', (data) => {
      this.handleCommentAdded(data);
    });

    this.socket.on('user-presence', (data) => {
      this.handleUserPresence(data);
    });

    this.socket.on('typing-indicator', (data) => {
      this.handleTypingIndicator(data);
    });
  }

  subscribeToBoardUpdates(boardId, callback) {
    this.socket.emit('join-board', boardId);

    if (!this.subscriptions.has(boardId)) {
      this.subscriptions.set(boardId, new Set());
    }

    this.subscriptions.get(boardId).add(callback);
  }

  unsubscribeFromBoard(boardId, callback = null) {
    if (callback) {
      this.subscriptions.get(boardId)?.delete(callback);
    } else {
      this.subscriptions.delete(boardId);
      this.socket.emit('leave-board', boardId);
    }
  }

  handleItemUpdate(data) {
    const { boardId, item, changes, user } = data;
    const callbacks = this.subscriptions.get(boardId);

    if (callbacks) {
      callbacks.forEach(callback => {
        callback({
          type: 'item-updated',
          boardId,
          item,
          changes,
          user,
        });
      });
    }
  }

  handleCommentAdded(data) {
    const { boardId, comment, item } = data;
    const callbacks = this.subscriptions.get(boardId);

    if (callbacks) {
      callbacks.forEach(callback => {
        callback({
          type: 'comment-added',
          boardId,
          comment,
          item,
        });
      });
    }
  }

  sendCursorPosition(boardId, x, y) {
    this.socket.emit('cursor-move', { boardId, x, y });
  }

  sendTypingIndicator(itemId, isTyping) {
    this.socket.emit('typing', { itemId, isTyping });
  }

  resubscribeAll() {
    for (const boardId of this.subscriptions.keys()) {
      this.socket.emit('join-board', boardId);
    }
  }

  disconnect() {
    if (this.socket) {
      this.socket.disconnect();
    }
  }
}

// Usage example
const realtimeClient = new SundayRealtimeClient('your_token');

await realtimeClient.connect();

// Subscribe to board updates
realtimeClient.subscribeToBoardUpdates('board_123', (event) => {
  switch (event.type) {
    case 'item-updated':
      console.log(`Item ${event.item.name} updated by ${event.user.name}`);
      updateUI(event.item);
      break;
    case 'comment-added':
      console.log(`New comment on ${event.item.name}`);
      showNotification(`New comment from ${event.comment.user.name}`);
      break;
  }
});
```

## 🔧 Advanced Integration Patterns

### Batch Operations

```javascript
class BatchProcessor {
  constructor(sundayClient, batchSize = 50) {
    this.sunday = sundayClient;
    this.batchSize = batchSize;
  }

  async processBatchUpdates(items) {
    const batches = this.chunkArray(items, this.batchSize);
    const results = [];

    for (const batch of batches) {
      const batchResults = await this.processBatch(batch);
      results.push(...batchResults);

      // Add delay to respect rate limits
      await this.delay(1000);
    }

    return results;
  }

  async processBatch(batch) {
    const promises = batch.map(item =>
      this.sunday.updateItem(item.id, item.updates)
        .catch(error => ({ id: item.id, error: error.message }))
    );

    return Promise.all(promises);
  }

  chunkArray(array, size) {
    const chunks = [];
    for (let i = 0; i < array.length; i += size) {
      chunks.push(array.slice(i, i + size));
    }
    return chunks;
  }

  delay(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
  }
}

// Usage
const batchProcessor = new BatchProcessor(sundayClient);

const updates = [
  { id: 'item_1', updates: { data: { status: 'Done' } } },
  { id: 'item_2', updates: { data: { status: 'In Progress' } } },
  // ... more items
];

const results = await batchProcessor.processBatchUpdates(updates);
console.log(`Updated ${results.length} items`);
```

### Error Handling and Retry Logic

```javascript
class ResilientAPIClient {
  constructor(apiKey, maxRetries = 3) {
    this.client = new SundayAPIClient(apiKey);
    this.maxRetries = maxRetries;
  }

  async requestWithRetry(method, endpoint, data = null, retryCount = 0) {
    try {
      return await this.client.request(method, endpoint, data);
    } catch (error) {
      if (this.shouldRetry(error, retryCount)) {
        const delay = this.calculateBackoff(retryCount);
        console.log(`Request failed, retrying in ${delay}ms...`);

        await this.delay(delay);
        return this.requestWithRetry(method, endpoint, data, retryCount + 1);
      }

      throw error;
    }
  }

  shouldRetry(error, retryCount) {
    if (retryCount >= this.maxRetries) return false;

    // Retry on network errors or server errors (5xx)
    return (
      error.message.includes('ECONNRESET') ||
      error.message.includes('ETIMEDOUT') ||
      (error.status >= 500 && error.status < 600) ||
      error.status === 429 // Rate limit
    );
  }

  calculateBackoff(retryCount) {
    // Exponential backoff with jitter
    const baseDelay = 1000;
    const maxDelay = 30000;
    const delay = Math.min(baseDelay * Math.pow(2, retryCount), maxDelay);
    const jitter = Math.random() * 0.1 * delay;

    return delay + jitter;
  }

  delay(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
  }
}
```

## 📊 Performance Optimization

### Caching Strategies

```javascript
class CachedAPIClient {
  constructor(apiKey, cacheConfig = {}) {
    this.client = new SundayAPIClient(apiKey);
    this.cache = new Map();
    this.cacheTTL = cacheConfig.ttl || 300000; // 5 minutes
    this.maxCacheSize = cacheConfig.maxSize || 1000;
  }

  async getCached(key, fetchFunction) {
    const cached = this.cache.get(key);

    if (cached && Date.now() - cached.timestamp < this.cacheTTL) {
      return cached.data;
    }

    const data = await fetchFunction();
    this.setCache(key, data);

    return data;
  }

  setCache(key, data) {
    // Implement LRU eviction if cache is full
    if (this.cache.size >= this.maxCacheSize) {
      const firstKey = this.cache.keys().next().value;
      this.cache.delete(firstKey);
    }

    this.cache.set(key, {
      data,
      timestamp: Date.now(),
    });
  }

  async getWorkspaces() {
    return this.getCached('workspaces', () =>
      this.client.getWorkspaces()
    );
  }

  async getBoard(boardId) {
    return this.getCached(`board:${boardId}`, () =>
      this.client.getBoard(boardId, ['columns', 'members'])
    );
  }

  invalidateCache(pattern) {
    for (const key of this.cache.keys()) {
      if (key.includes(pattern)) {
        this.cache.delete(key);
      }
    }
  }
}
```

## 🚀 Deployment and Monitoring

### Environment Configuration

```javascript
// config.js
const config = {
  development: {
    apiUrl: 'http://localhost:3000/api/v1',
    wsUrl: 'ws://localhost:3000',
    logLevel: 'debug',
    rateLimitRPM: 100,
  },
  staging: {
    apiUrl: 'https://api-staging.sunday.com/v1',
    wsUrl: 'wss://api-staging.sunday.com',
    logLevel: 'info',
    rateLimitRPM: 500,
  },
  production: {
    apiUrl: 'https://api.sunday.com/v1',
    wsUrl: 'wss://api.sunday.com',
    logLevel: 'warn',
    rateLimitRPM: 1000,
  },
};

module.exports = config[process.env.NODE_ENV || 'development'];
```

### Monitoring and Logging

```javascript
class APIMetrics {
  constructor() {
    this.metrics = {
      requests: 0,
      errors: 0,
      responseTime: [],
    };
  }

  recordRequest(duration, error = null) {
    this.metrics.requests++;
    this.metrics.responseTime.push(duration);

    if (error) {
      this.metrics.errors++;
      console.error('API Error:', error);
    }

    // Keep only last 1000 response times
    if (this.metrics.responseTime.length > 1000) {
      this.metrics.responseTime = this.metrics.responseTime.slice(-1000);
    }
  }

  getStats() {
    const responseTimes = this.metrics.responseTime;
    const avgResponseTime = responseTimes.reduce((a, b) => a + b, 0) / responseTimes.length;

    return {
      totalRequests: this.metrics.requests,
      totalErrors: this.metrics.errors,
      errorRate: (this.metrics.errors / this.metrics.requests * 100).toFixed(2),
      avgResponseTime: avgResponseTime.toFixed(2),
    };
  }
}

// Wrap API client with metrics
class MonitoredAPIClient {
  constructor(apiKey) {
    this.client = new SundayAPIClient(apiKey);
    this.metrics = new APIMetrics();
  }

  async request(method, endpoint, data = null) {
    const startTime = Date.now();

    try {
      const result = await this.client.request(method, endpoint, data);
      const duration = Date.now() - startTime;
      this.metrics.recordRequest(duration);

      return result;
    } catch (error) {
      const duration = Date.now() - startTime;
      this.metrics.recordRequest(duration, error);
      throw error;
    }
  }

  getMetrics() {
    return this.metrics.getStats();
  }
}
```

## 📚 Next Steps

### Advanced Topics to Explore

1. **GraphQL Integration**: Use GraphQL for complex queries
2. **Bulk Data Processing**: Handle large datasets efficiently
3. **Custom Authentication**: Implement custom auth flows
4. **Plugin Development**: Build Sunday.com plugins
5. **Mobile Integration**: Integrate with mobile apps

### Resources

- **API Reference**: Complete endpoint documentation
- **SDK Libraries**: Official SDKs for popular languages
- **Example Projects**: Sample integrations and use cases
- **Community Forum**: Get help from other developers

## 🆘 Troubleshooting

### Common Issues

**Rate Limiting**
```javascript
// Handle rate limits gracefully
if (error.status === 429) {
  const retryAfter = error.headers['retry-after'];
  await delay(retryAfter * 1000);
  // Retry request
}
```

**Authentication Errors**
```javascript
// Check token expiration
if (error.status === 401) {
  // Refresh token or re-authenticate
  await refreshAccessToken();
  // Retry request
}
```

**Network Issues**
```javascript
// Implement connection health checks
async function healthCheck() {
  try {
    await apiClient.request('GET', '/health');
    return true;
  } catch (error) {
    return false;
  }
}
```

### Getting Help

- **Documentation**: [docs.sunday.com/api](https://docs.sunday.com/api)
- **Support**: api-support@sunday.com
- **Community**: [developers.sunday.com](https://developers.sunday.com)
- **GitHub**: Report issues and contribute

---

You're now ready to build powerful integrations with Sunday.com! Start with simple use cases and gradually add more complexity as you become familiar with the API patterns and best practices.