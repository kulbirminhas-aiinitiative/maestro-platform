# Sunday.com API Documentation

## 📖 Overview

The Sunday.com API provides programmatic access to all platform features, enabling developers to build custom integrations, automate workflows, and extend the platform's capabilities. Our API follows REST conventions, supports GraphQL for complex queries, and provides real-time updates via WebSocket connections.

## 🚀 Quick Start

### Authentication

All API requests require authentication using JWT tokens. Obtain tokens through the authentication endpoints or via OAuth 2.0.

```bash
# Example: Get an access token
curl -X POST https://api.sunday.com/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "password123"
  }'
```

Response:
```json
{
  "data": {
    "user": {
      "id": "usr_abc123",
      "email": "user@example.com",
      "firstName": "John",
      "lastName": "Doe"
    },
    "tokens": {
      "accessToken": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
      "refreshToken": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
      "expiresIn": 3600
    }
  }
}
```

### Making API Calls

Include the access token in the Authorization header:

```bash
curl -H "Authorization: Bearer your_access_token" \
  https://api.sunday.com/v1/workspaces
```

## 🔗 Base URLs

| Environment | Base URL |
|-------------|----------|
| Production | `https://api.sunday.com/v1` |
| Staging | `https://api-staging.sunday.com/v1` |
| Development | `http://localhost:3000/api/v1` |

## 📊 Rate Limits

API requests are rate-limited based on your subscription plan:

| Plan | Requests/Minute | Burst Limit |
|------|-----------------|-------------|
| Free | 100 | 200 |
| Pro | 1,000 | 2,000 |
| Enterprise | 10,000 | 20,000 |

Rate limit headers are included in every response:
```
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 999
X-RateLimit-Reset: 1640995200
```

## 🏢 Core Resources

### Organizations

Organizations are the top-level containers for all Sunday.com resources.

#### List Organizations

```bash
GET /organizations
```

**Example Request:**
```bash
curl -H "Authorization: Bearer token" \
  https://api.sunday.com/v1/organizations
```

**Example Response:**
```json
{
  "data": [
    {
      "id": "org_abc123",
      "name": "Acme Corporation",
      "slug": "acme-corp",
      "domain": "acme.com",
      "subscriptionPlan": "enterprise",
      "settings": {
        "allowGuestAccess": true,
        "defaultWorkspaceVisibility": "private"
      },
      "createdAt": "2024-01-15T10:00:00Z",
      "updatedAt": "2024-12-01T15:30:00Z"
    }
  ],
  "meta": {
    "pagination": {
      "page": 1,
      "limit": 20,
      "total": 1,
      "totalPages": 1,
      "hasNext": false,
      "hasPrev": false
    }
  }
}
```

#### Create Organization

```bash
POST /organizations
```

**Request Body:**
```json
{
  "name": "My Company",
  "slug": "my-company",
  "domain": "mycompany.com"
}
```

**Example Request:**
```bash
curl -X POST https://api.sunday.com/v1/organizations \
  -H "Authorization: Bearer token" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "My Company",
    "slug": "my-company",
    "domain": "mycompany.com"
  }'
```

### Workspaces

Workspaces organize related projects and boards within an organization.

#### List Workspaces

```bash
GET /organizations/{org_id}/workspaces
```

**Query Parameters:**
- `include` - Additional data to include (members, boards, stats)
- `filter[name]` - Filter by workspace name
- `filter[visibility]` - Filter by visibility (public, private)

**Example Request:**
```bash
curl -H "Authorization: Bearer token" \
  "https://api.sunday.com/v1/organizations/org_abc123/workspaces?include=members,stats"
```

**Example Response:**
```json
{
  "data": [
    {
      "id": "ws_xyz789",
      "organizationId": "org_abc123",
      "name": "Product Development",
      "description": "Main product development workspace",
      "color": "#3B82F6",
      "isPrivate": false,
      "members": [
        {
          "id": "usr_def456",
          "role": "admin",
          "user": {
            "id": "usr_def456",
            "firstName": "Jane",
            "lastName": "Smith",
            "email": "jane@acme.com"
          }
        }
      ],
      "stats": {
        "boardCount": 5,
        "memberCount": 12,
        "activeItemCount": 89
      },
      "settings": {
        "allowGuests": false,
        "defaultBoardVisibility": "workspace"
      },
      "createdAt": "2024-01-20T14:00:00Z",
      "updatedAt": "2024-12-01T16:00:00Z"
    }
  ]
}
```

#### Create Workspace

```bash
POST /organizations/{org_id}/workspaces
```

**Request Body:**
```json
{
  "name": "Marketing Campaigns",
  "description": "Workspace for managing marketing campaigns",
  "color": "#EF4444",
  "isPrivate": false
}
```

### Boards

Boards are flexible containers for organizing work items with customizable columns and views.

#### List Boards

```bash
GET /workspaces/{workspace_id}/boards
```

**Query Parameters:**
- `include` - Include additional data (columns, items, members)
- `filter[folder_id]` - Filter by folder
- `sort` - Sort by field (name, created_at, updated_at)
- `order` - Sort order (asc, desc)

**Example Request:**
```bash
curl -H "Authorization: Bearer token" \
  "https://api.sunday.com/v1/workspaces/ws_xyz789/boards?include=columns&sort=name&order=asc"
```

**Example Response:**
```json
{
  "data": [
    {
      "id": "brd_123abc",
      "workspaceId": "ws_xyz789",
      "name": "Product Roadmap",
      "description": "Q1 2025 product roadmap planning",
      "isPrivate": false,
      "viewSettings": {
        "defaultView": "table",
        "availableViews": ["table", "kanban", "timeline", "calendar"]
      },
      "columns": [
        {
          "id": "col_name",
          "name": "Item",
          "columnType": "text",
          "position": 0,
          "isRequired": true,
          "settings": {
            "width": 200
          }
        },
        {
          "id": "col_status",
          "name": "Status",
          "columnType": "status",
          "position": 1,
          "settings": {
            "options": [
              {"label": "Not Started", "color": "#94A3B8"},
              {"label": "In Progress", "color": "#3B82F6"},
              {"label": "Done", "color": "#10B981"}
            ]
          }
        },
        {
          "id": "col_assignee",
          "name": "Assignee",
          "columnType": "people",
          "position": 2,
          "settings": {
            "allowMultiple": true
          }
        }
      ],
      "createdBy": {
        "id": "usr_def456",
        "firstName": "Jane",
        "lastName": "Smith"
      },
      "createdAt": "2024-02-01T09:00:00Z",
      "updatedAt": "2024-12-01T17:30:00Z"
    }
  ]
}
```

#### Create Board

```bash
POST /workspaces/{workspace_id}/boards
```

**Request Body:**
```json
{
  "name": "Sprint Planning",
  "description": "Board for managing sprint planning",
  "templateId": "tpl_agile_board",
  "folderId": "fld_sprints",
  "settings": {
    "enableTimeTracking": true,
    "allowGuests": false
  }
}
```

### Items

Items represent individual work units within boards (tasks, issues, features, etc.).

#### List Board Items

```bash
GET /boards/{board_id}/items
```

**Query Parameters:**
- `filter[status]` - Filter by status values
- `filter[assignee]` - Filter by assignee user IDs
- `filter[due_date][from]` - Filter by due date range start
- `filter[due_date][to]` - Filter by due date range end
- `sort` - Sort by field (position, created_at, updated_at, due_date)
- `order` - Sort order (asc, desc)
- `limit` - Number of items per page (max 100)
- `cursor` - Pagination cursor

**Example Request:**
```bash
curl -H "Authorization: Bearer token" \
  "https://api.sunday.com/v1/boards/brd_123abc/items?filter[status]=In%20Progress&filter[assignee]=usr_def456&limit=25"
```

**Example Response:**
```json
{
  "data": [
    {
      "id": "itm_456def",
      "boardId": "brd_123abc",
      "name": "Implement user authentication",
      "description": "Add JWT-based authentication to the API",
      "position": 1.5,
      "data": {
        "status": "In Progress",
        "priority": "High",
        "estimate": 8,
        "dueDate": "2024-12-15T23:59:59Z"
      },
      "assignees": [
        {
          "id": "usr_def456",
          "firstName": "Jane",
          "lastName": "Smith",
          "email": "jane@acme.com",
          "avatarUrl": "https://cdn.sunday.com/avatars/usr_def456.jpg"
        }
      ],
      "dependencies": [
        {
          "id": "dep_789ghi",
          "predecessorId": "itm_321fed",
          "dependencyType": "blocks"
        }
      ],
      "createdBy": {
        "id": "usr_abc123",
        "firstName": "John",
        "lastName": "Doe"
      },
      "createdAt": "2024-11-15T10:00:00Z",
      "updatedAt": "2024-12-01T14:30:00Z"
    }
  ],
  "meta": {
    "totalCount": 156,
    "filterCount": 12,
    "pagination": {
      "nextCursor": "cursor_next_page",
      "hasMore": true
    }
  }
}
```

#### Create Item

```bash
POST /boards/{board_id}/items
```

**Request Body:**
```json
{
  "name": "Design new login flow",
  "description": "Create wireframes and mockups for the new login experience",
  "parentId": null,
  "position": 2.5,
  "data": {
    "status": "Not Started",
    "priority": "Medium",
    "estimate": 5,
    "dueDate": "2024-12-20T23:59:59Z"
  },
  "assignees": ["usr_def456", "usr_ghi789"]
}
```

#### Update Item

```bash
PUT /items/{item_id}
```

**Request Body:**
```json
{
  "name": "Updated task name",
  "data": {
    "status": "Done",
    "priority": "Low"
  },
  "assignees": ["usr_def456"]
}
```

#### Bulk Update Items

```bash
PUT /items/bulk
```

**Request Body:**
```json
{
  "itemIds": ["itm_456def", "itm_789ghi", "itm_012jkl"],
  "updates": {
    "data": {
      "status": "Done",
      "completedDate": "2024-12-01T18:00:00Z"
    }
  }
}
```

**Response:**
```json
{
  "data": {
    "updatedCount": 3,
    "errors": []
  }
}
```

### Comments

Comments enable team collaboration and discussion on work items.

#### List Comments

```bash
GET /items/{item_id}/comments
```

**Example Response:**
```json
{
  "data": [
    {
      "id": "cmt_789ghi",
      "itemId": "itm_456def",
      "userId": "usr_def456",
      "content": "I've completed the initial implementation. @usr_abc123 please review.",
      "contentType": "markdown",
      "mentions": ["usr_abc123"],
      "attachments": [
        {
          "id": "att_123abc",
          "fileName": "implementation.png",
          "fileSize": 125834,
          "mimeType": "image/png",
          "url": "https://cdn.sunday.com/files/att_123abc/implementation.png"
        }
      ],
      "isEdited": false,
      "user": {
        "id": "usr_def456",
        "firstName": "Jane",
        "lastName": "Smith",
        "avatarUrl": "https://cdn.sunday.com/avatars/usr_def456.jpg"
      },
      "createdAt": "2024-12-01T16:45:00Z",
      "updatedAt": "2024-12-01T16:45:00Z"
    }
  ]
}
```

#### Add Comment

```bash
POST /items/{item_id}/comments
```

**Request Body:**
```json
{
  "content": "Great work on this feature! Just a few minor suggestions...",
  "mentions": ["usr_def456"],
  "attachments": ["att_456def"]
}
```

## 🔍 GraphQL API

For complex data fetching and real-time subscriptions, use our GraphQL endpoint.

### Endpoint
```
POST https://api.sunday.com/graphql
```

### Authentication
Include the JWT token in the Authorization header:
```
Authorization: Bearer your_access_token
```

### Example Queries

#### Get Workspace Overview
```graphql
query WorkspaceOverview($workspaceId: ID!) {
  workspace(id: $workspaceId) {
    id
    name
    description
    boards(first: 10) {
      edges {
        node {
          id
          name
          items(first: 5, sort: [{ field: UPDATED_AT, direction: DESC }]) {
            totalCount
            edges {
              node {
                id
                name
                data
                assignees {
                  id
                  fullName
                  avatarUrl
                }
                updatedAt
              }
            }
          }
        }
      }
    }
  }
}
```

#### Create New Item
```graphql
mutation CreateItem($input: CreateItemInput!) {
  createItem(input: $input) {
    item {
      id
      name
      data
      assignees {
        id
        fullName
      }
      createdAt
    }
    errors {
      field
      message
    }
  }
}
```

**Variables:**
```json
{
  "input": {
    "boardId": "brd_123abc",
    "name": "New feature request",
    "description": "Implement dark mode support",
    "data": {
      "status": "Backlog",
      "priority": "Medium"
    },
    "assigneeIds": ["usr_def456"]
  }
}
```

### Subscriptions

Subscribe to real-time updates using GraphQL subscriptions:

```graphql
subscription BoardUpdates($boardId: ID!) {
  boardUpdates(boardId: $boardId) {
    type
    item {
      id
      name
      data
      updatedAt
    }
    user {
      id
      fullName
    }
  }
}
```

## ⚡ WebSocket API

For real-time collaboration features, connect to our WebSocket server.

### Connection
```javascript
const socket = io('wss://api.sunday.com', {
  auth: {
    token: 'your_jwt_token'
  }
});
```

### Events

#### Subscribe to Board Updates
```javascript
// Join a board room
socket.emit('join-board', 'brd_123abc');

// Listen for item updates
socket.on('item-updated', (data) => {
  console.log('Item updated:', data);
  // {
  //   itemId: 'itm_456def',
  //   changes: { status: { old: 'In Progress', new: 'Done' } },
  //   updatedBy: 'usr_def456',
  //   timestamp: '2024-12-01T18:30:00Z'
  // }
});

// Listen for new comments
socket.on('comment-added', (data) => {
  console.log('New comment:', data);
});

// Listen for user presence
socket.on('user-joined', (data) => {
  console.log('User joined:', data.user);
});

socket.on('user-left', (data) => {
  console.log('User left:', data.userId);
});
```

#### Send Updates
```javascript
// Update item position (drag & drop)
socket.emit('item-move', {
  itemId: 'itm_456def',
  newPosition: 3.5
});

// Send typing indicator
socket.emit('typing-start', {
  itemId: 'itm_456def',
  field: 'description'
});

socket.emit('typing-stop', {
  itemId: 'itm_456def'
});
```

## 🔗 Webhooks

Configure webhooks to receive notifications when events occur in your workspace.

### Setup Webhook

```bash
POST /webhooks
```

**Request Body:**
```json
{
  "url": "https://myapp.com/webhooks/sunday",
  "events": [
    "item.created",
    "item.updated",
    "item.deleted",
    "comment.added"
  ],
  "secret": "your_webhook_secret",
  "active": true,
  "filters": {
    "boardIds": ["brd_123abc"],
    "workspaceIds": ["ws_xyz789"]
  }
}
```

### Webhook Payload

When an event occurs, we'll send a POST request to your webhook URL:

```json
{
  "event": "item.created",
  "timestamp": "2024-12-01T18:00:00Z",
  "data": {
    "item": {
      "id": "itm_456def",
      "boardId": "brd_123abc",
      "name": "New task",
      "data": {...},
      "createdBy": "usr_def456"
    },
    "board": {
      "id": "brd_123abc",
      "name": "Product Roadmap",
      "workspaceId": "ws_xyz789"
    },
    "user": {
      "id": "usr_def456",
      "name": "Jane Smith",
      "email": "jane@acme.com"
    }
  }
}
```

### Verify Webhook Signature

```javascript
const crypto = require('crypto');

function verifyWebhookSignature(payload, signature, secret) {
  const expectedSignature = crypto
    .createHmac('sha256', secret)
    .update(payload)
    .digest('hex');

  return signature === `sha256=${expectedSignature}`;
}

// Express middleware
app.post('/webhooks/sunday', express.raw({type: 'application/json'}), (req, res) => {
  const signature = req.headers['x-sunday-signature'];
  const payload = req.body.toString();

  if (!verifyWebhookSignature(payload, signature, WEBHOOK_SECRET)) {
    return res.status(401).send('Invalid signature');
  }

  const event = JSON.parse(payload);
  handleWebhookEvent(event);

  res.status(200).send('OK');
});
```

## 📚 SDK Examples

### JavaScript/Node.js

Install the SDK:
```bash
npm install @sunday/sdk
```

Basic usage:
```javascript
import { SundayClient } from '@sunday/sdk';

const client = new SundayClient({
  apiKey: 'your_api_key',
  baseUrl: 'https://api.sunday.com/v1'
});

// Get workspaces
const workspaces = await client.workspaces.list({
  organizationId: 'org_abc123'
});

// Create a new item
const item = await client.items.create({
  boardId: 'brd_123abc',
  name: 'New task',
  data: {
    status: 'Not Started',
    priority: 'High'
  }
});

// Real-time updates
client.realtime.subscribe('board:brd_123abc', (event) => {
  console.log('Board update:', event);
});
```

### Python

Install the SDK:
```bash
pip install sunday-sdk
```

Basic usage:
```python
from sunday import SundayClient

client = SundayClient(api_key='your_api_key')

# Get workspaces
workspaces = client.workspaces.list(organization_id='org_abc123')

# Create item
item = client.items.create(
    board_id='brd_123abc',
    name='New task',
    data={'status': 'Not Started', 'priority': 'High'}
)

# Bulk operations
client.items.bulk_update(
    item_ids=['item1', 'item2'],
    updates={'data': {'status': 'Done'}}
)
```

### React Hooks

Install the React SDK:
```bash
npm install @sunday/react
```

Use in your React components:
```jsx
import { useSundayQuery, useSundayMutation } from '@sunday/react';

function BoardComponent({ boardId }) {
  // Query data
  const { data: board, loading, error } = useSundayQuery({
    query: GET_BOARD_QUERY,
    variables: { boardId }
  });

  // Mutations
  const [createItem, { loading: creating }] = useSundayMutation({
    mutation: CREATE_ITEM_MUTATION,
    onCompleted: (data) => {
      console.log('Item created:', data.createItem.item);
    }
  });

  // Real-time subscription
  useSundaySubscription({
    subscription: BOARD_UPDATES_SUBSCRIPTION,
    variables: { boardId },
    onData: ({ data }) => {
      console.log('Board update:', data);
    }
  });

  if (loading) return <div>Loading...</div>;
  if (error) return <div>Error: {error.message}</div>;

  return (
    <div>
      <h1>{board.name}</h1>
      <button
        onClick={() => createItem({ variables: { boardId, name: 'New task' } })}
        disabled={creating}
      >
        {creating ? 'Creating...' : 'Add Task'}
      </button>
    </div>
  );
}
```

## ⚠️ Error Handling

### Error Response Format

All errors follow a consistent format:

```json
{
  "error": {
    "type": "validation_error",
    "message": "Invalid input parameters",
    "details": {
      "name": ["Name is required"],
      "email": ["Invalid email format"]
    },
    "requestId": "req_123abc456"
  }
}
```

### Common Error Types

| Error Type | HTTP Status | Description |
|------------|-------------|-------------|
| `validation_error` | 422 | Request validation failed |
| `authentication_error` | 401 | Authentication required |
| `authorization_error` | 403 | Insufficient permissions |
| `not_found` | 404 | Resource not found |
| `rate_limit_exceeded` | 429 | Rate limit exceeded |
| `server_error` | 500 | Internal server error |

### Error Handling Examples

```javascript
// Handle API errors
try {
  const item = await client.items.create(itemData);
} catch (error) {
  if (error.type === 'validation_error') {
    console.log('Validation errors:', error.details);
  } else if (error.type === 'rate_limit_exceeded') {
    console.log('Rate limited. Retry after:', error.retryAfter);
  } else {
    console.log('Unexpected error:', error.message);
  }
}

// Handle webhook errors
app.post('/webhooks/sunday', (req, res) => {
  try {
    const event = verifyAndParseWebhook(req);
    handleWebhookEvent(event);
    res.status(200).send('OK');
  } catch (error) {
    console.error('Webhook error:', error);
    res.status(400).send('Bad Request');
  }
});
```

## 🔧 Advanced Features

### Batch Operations

Perform multiple operations in a single request:

```bash
POST /batch
```

**Request Body:**
```json
{
  "operations": [
    {
      "method": "POST",
      "path": "/items",
      "body": {
        "boardId": "brd_123abc",
        "name": "Task 1"
      }
    },
    {
      "method": "PUT",
      "path": "/items/itm_456def",
      "body": {
        "data": { "status": "Done" }
      }
    }
  ]
}
```

### Filtering and Searching

Advanced filtering options:

```bash
# Complex filtering
GET /items?filter[board_id]=brd_123abc&filter[assignee][in]=usr_1,usr_2&filter[due_date][gte]=2024-12-01&filter[status][not]=Done

# Full-text search
GET /search?q=authentication&type=items&workspace_id=ws_xyz789

# Search with filters
GET /search?q=urgent&filter[board_id]=brd_123abc&filter[assignee]=usr_def456
```

### Field Selection

Only return specific fields to optimize performance:

```bash
# REST API
GET /items?fields=id,name,status,assignees.id,assignees.name

# GraphQL (natural field selection)
query {
  items {
    id
    name
    data { status }
    assignees { id name }
  }
}
```

## 📊 Analytics and Reporting

### Analytics Endpoints

```bash
# Workspace analytics
GET /workspaces/{workspace_id}/analytics

# Board performance
GET /boards/{board_id}/analytics

# User productivity
GET /users/{user_id}/analytics
```

### Custom Reports

Create custom reports using the reporting API:

```bash
POST /reports
```

**Request Body:**
```json
{
  "name": "Sprint Report",
  "type": "items",
  "filters": {
    "boardId": "brd_123abc",
    "dateRange": {
      "from": "2024-11-01",
      "to": "2024-11-30"
    }
  },
  "groupBy": ["status", "assignee"],
  "metrics": ["count", "averageCompletionTime"],
  "schedule": {
    "frequency": "weekly",
    "recipients": ["jane@acme.com"]
  }
}
```

## 🔐 Security Best Practices

### API Key Management

- **Rotate keys regularly** - Set up automatic key rotation
- **Use environment variables** - Never hardcode API keys
- **Scope permissions** - Use the minimum required permissions
- **Monitor usage** - Track API key usage and set alerts

### Rate Limiting

Implement client-side rate limiting:

```javascript
// Simple rate limiter
class RateLimiter {
  constructor(requestsPerMinute = 60) {
    this.requests = [];
    this.limit = requestsPerMinute;
  }

  async checkLimit() {
    const now = Date.now();
    this.requests = this.requests.filter(time => now - time < 60000);

    if (this.requests.length >= this.limit) {
      const waitTime = 60000 - (now - this.requests[0]);
      await new Promise(resolve => setTimeout(resolve, waitTime));
    }

    this.requests.push(now);
  }
}
```

### Webhook Security

Always verify webhook signatures:

```javascript
const crypto = require('crypto');

function verifyWebhook(payload, signature, secret) {
  const expectedSignature = crypto
    .createHmac('sha256', secret)
    .update(payload, 'utf8')
    .digest('hex');

  return crypto.timingSafeEqual(
    Buffer.from(signature),
    Buffer.from(`sha256=${expectedSignature}`)
  );
}
```

## 🚀 Performance Optimization

### Caching Strategies

- **Cache frequently accessed data** - User profiles, workspace settings
- **Use ETags** - Implement conditional requests
- **Cache GraphQL queries** - Use query result caching
- **Implement pagination** - Always paginate large result sets

### Efficient Queries

```javascript
// Good: Fetch only needed data
const items = await client.items.list({
  boardId: 'brd_123abc',
  fields: 'id,name,status',
  limit: 50
});

// Bad: Fetch all data
const items = await client.items.list({
  boardId: 'brd_123abc'
});
```

### Batch Requests

```javascript
// Good: Batch multiple operations
const results = await client.batch([
  { method: 'GET', path: '/workspaces/ws_1' },
  { method: 'GET', path: '/workspaces/ws_2' },
  { method: 'GET', path: '/workspaces/ws_3' }
]);

// Bad: Multiple individual requests
const ws1 = await client.workspaces.get('ws_1');
const ws2 = await client.workspaces.get('ws_2');
const ws3 = await client.workspaces.get('ws_3');
```

## 🆘 Support and Resources

### Getting Help

- **📖 Documentation**: [docs.sunday.com](https://docs.sunday.com)
- **💬 Developer Forum**: [developers.sunday.com](https://developers.sunday.com)
- **📧 Support Email**: api-support@sunday.com
- **🐛 Bug Reports**: [GitHub Issues](https://github.com/sunday-com/api/issues)

### Additional Resources

- **📋 API Changelog**: Track API updates and changes
- **🔧 Postman Collection**: Ready-to-use API collection
- **📊 Status Page**: Real-time API status and uptime
- **🔔 Developer Newsletter**: Latest API news and updates

### Community

- **🐦 Twitter**: [@SundayAPI](https://twitter.com/SundayAPI)
- **💬 Discord**: [Sunday Developer Community](https://discord.gg/sunday-dev)
- **📺 YouTube**: API tutorials and walkthroughs
- **📝 Blog**: Technical articles and best practices

---

*Last updated: December 2024*
*API Version: v1.0.0*