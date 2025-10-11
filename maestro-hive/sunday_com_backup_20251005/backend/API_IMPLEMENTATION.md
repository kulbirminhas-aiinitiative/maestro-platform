# Sunday.com API Implementation Documentation

## Overview

Sunday.com provides a comprehensive REST API for work management and collaboration. This API implementation covers all core functionality including authentication, workspace management, boards, items, real-time collaboration, AI features, and automation.

## Base URL

```
https://api.sunday.com/api/v1
```

## Authentication

All API endpoints require authentication using JWT tokens.

### Headers
```
Authorization: Bearer <jwt_token>
Content-Type: application/json
X-Request-ID: <optional_request_id>
```

## API Structure

### Core Endpoints

| Module | Base Path | Description |
|--------|-----------|-------------|
| Authentication | `/auth` | User authentication and session management |
| Organizations | `/organizations` | Organization management |
| Workspaces | `/workspaces` | Workspace CRUD and member management |
| Boards | `/boards` | Board management and column operations |
| Items | `/items` | Task/item management and bulk operations |
| Comments | `/comments` | Communication and collaboration |
| Files | `/files` | File upload and attachment management |
| AI | `/ai` | AI-powered features and suggestions |
| Automation | `/automation` | Automation rules and execution |
| Analytics | `/analytics` | Reporting and insights |
| Time | `/time` | Time tracking functionality |
| Webhooks | `/webhooks` | External integrations |
| Collaboration | `/collaboration` | Real-time collaboration features |

## Authentication API

### POST /auth/login
Login user with email and password.

**Request:**
```json
{
  "email": "user@example.com",
  "password": "password123"
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "user": {
      "id": "user-uuid",
      "email": "user@example.com",
      "firstName": "John",
      "lastName": "Doe"
    },
    "tokens": {
      "accessToken": "jwt-access-token",
      "refreshToken": "jwt-refresh-token"
    }
  }
}
```

### POST /auth/register
Register new user account.

**Request:**
```json
{
  "email": "user@example.com",
  "password": "password123",
  "firstName": "John",
  "lastName": "Doe"
}
```

### POST /auth/refresh
Refresh access token using refresh token.

**Request:**
```json
{
  "refreshToken": "jwt-refresh-token"
}
```

### POST /auth/logout
Logout user and invalidate tokens.

## Workspace API

### GET /workspaces
List user's workspaces with pagination.

**Query Parameters:**
- `page` (integer): Page number (default: 1)
- `limit` (integer): Items per page (default: 20, max: 100)
- `search` (string): Search term for workspace names

**Response:**
```json
{
  "success": true,
  "data": [
    {
      "id": "workspace-uuid",
      "name": "My Workspace",
      "description": "Team workspace",
      "isPrivate": false,
      "createdAt": "2024-01-01T00:00:00Z",
      "updatedAt": "2024-01-01T00:00:00Z",
      "_count": {
        "boards": 5,
        "members": 10
      }
    }
  ],
  "meta": {
    "page": 1,
    "limit": 20,
    "total": 1,
    "totalPages": 1,
    "hasNext": false,
    "hasPrev": false
  }
}
```

### POST /workspaces
Create new workspace.

**Request:**
```json
{
  "name": "New Workspace",
  "description": "Workspace description",
  "isPrivate": false
}
```

### GET /workspaces/:workspaceId
Get workspace details by ID.

### PUT /workspaces/:workspaceId
Update workspace details.

### DELETE /workspaces/:workspaceId
Delete workspace (soft delete).

### POST /workspaces/:workspaceId/members
Add member to workspace.

**Request:**
```json
{
  "email": "member@example.com",
  "role": "member"
}
```

### DELETE /workspaces/:workspaceId/members/:userId
Remove member from workspace.

## Board API

### GET /boards
List boards in workspace.

**Query Parameters:**
- `workspaceId` (string, required): Workspace ID
- `page` (integer): Page number
- `limit` (integer): Items per page
- `folderId` (string): Filter by folder

### POST /boards
Create new board.

**Request:**
```json
{
  "workspaceId": "workspace-uuid",
  "name": "Project Board",
  "description": "Track project tasks",
  "isPrivate": false,
  "columns": [
    {
      "name": "To Do",
      "position": 0
    },
    {
      "name": "In Progress",
      "position": 1
    },
    {
      "name": "Done",
      "position": 2
    }
  ]
}
```

### GET /boards/:boardId
Get board details with items and columns.

**Query Parameters:**
- `include` (array): Additional data to include [items, columns, members, activity, statistics]
- `itemLimit` (integer): Maximum items to return
- `itemCursor` (string): Pagination cursor for items

### PUT /boards/:boardId
Update board details.

### DELETE /boards/:boardId
Delete board.

### POST /boards/:boardId/columns
Add column to board.

**Request:**
```json
{
  "name": "Review",
  "position": 1,
  "color": "#ff6b6b"
}
```

### PUT /boards/:boardId/columns
Bulk update board columns.

### POST /boards/:boardId/share
Share board with users.

**Request:**
```json
{
  "userIds": ["user1-uuid", "user2-uuid"],
  "permissions": ["read", "write"],
  "message": "Welcome to the project board!"
}
```

### POST /boards/:boardId/duplicate
Duplicate board.

**Request:**
```json
{
  "name": "Copy of Project Board",
  "workspaceId": "workspace-uuid",
  "includeItems": true,
  "includeMembers": false
}
```

## Item API

### GET /boards/:boardId/items
List board items with filtering and pagination.

**Query Parameters:**
- `filter[status]` (array): Filter by status values
- `filter[assigneeIds]` (array): Filter by assignee IDs
- `filter[parentId]` (string): Filter by parent item
- `filter[dueDateFrom]` (date): Filter items due after date
- `filter[dueDateTo]` (date): Filter items due before date
- `filter[priority]` (array): Filter by priority [low, medium, high, critical]
- `filter[tags]` (array): Filter by tags
- `filter[search]` (string): Search in item names and descriptions
- `sort` (array): Sort fields [position, created_at, updated_at, due_date, priority, name]
- `order` (string): Sort order [asc, desc]
- `limit` (integer): Items per page
- `cursor` (string): Pagination cursor
- `include` (array): Additional data [assignees, comments, attachments, dependencies, subtasks]

### POST /boards/:boardId/items
Create new item.

**Request:**
```json
{
  "name": "Implement user authentication",
  "description": "Add JWT-based authentication system",
  "parentId": null,
  "position": 1.0,
  "data": {
    "status": "To Do",
    "priority": "High",
    "estimated_hours": 8,
    "due_date": "2024-12-31"
  },
  "assigneeIds": ["user1-uuid", "user2-uuid"],
  "dependencies": ["dependency1-uuid"],
  "attachments": ["file1-uuid"],
  "tags": ["backend", "authentication"]
}
```

### GET /items/:itemId
Get item details.

**Query Parameters:**
- `include` (array): Additional data [comments, attachments, dependencies, subtasks, activity, time_entries]

### PUT /items/:itemId
Update item.

**Request:**
```json
{
  "name": "Updated item name",
  "description": "Updated description",
  "data": {
    "status": "In Progress",
    "priority": "Medium"
  },
  "assigneeIds": ["user1-uuid"],
  "tags": ["backend", "updated"]
}
```

### DELETE /items/:itemId
Delete item.

**Query Parameters:**
- `deleteSubtasks` (boolean): Whether to delete subtasks (default: false)

### PUT /items/bulk
Bulk update items.

**Request:**
```json
{
  "itemIds": ["item1-uuid", "item2-uuid"],
  "updates": {
    "data": {
      "status": "In Progress"
    },
    "assigneeIds": ["user1-uuid"]
  },
  "operation": "merge"
}
```

### DELETE /items/bulk
Bulk delete items.

**Request:**
```json
{
  "itemIds": ["item1-uuid", "item2-uuid"],
  "deleteSubtasks": false
}
```

### PUT /items/:itemId/move
Move item to new position or parent.

**Request:**
```json
{
  "position": 1.5,
  "parentId": "parent-uuid",
  "boardId": "new-board-uuid"
}
```

### GET /items/:itemId/dependencies
Get item dependencies.

### POST /items/:itemId/dependencies
Create item dependency.

**Request:**
```json
{
  "predecessorId": "predecessor-uuid",
  "dependencyType": "blocks"
}
```

### GET /items/:itemId/comments
Get item comments.

### POST /items/:itemId/comments
Add comment to item.

**Request:**
```json
{
  "content": "Great progress on this task!",
  "parentId": null,
  "mentions": ["user1-uuid"]
}
```

## File API

### POST /files/upload
Upload file with presigned URL.

**Request (multipart/form-data):**
- `file`: File to upload
- `itemId` (optional): Item to attach file to
- `metadata` (optional): Additional file metadata

**Response:**
```json
{
  "success": true,
  "data": {
    "id": "file-uuid",
    "filename": "document.pdf",
    "mimeType": "application/pdf",
    "size": 1024000,
    "url": "https://s3.amazonaws.com/bucket/file-uuid",
    "thumbnail": "https://s3.amazonaws.com/bucket/file-uuid-thumb"
  }
}
```

### GET /files/:fileId
Get file details and download URL.

### DELETE /files/:fileId
Delete file.

### GET /files/:fileId/download
Download file (redirects to S3 URL).

## AI API

### POST /ai/suggestions/tasks
Get AI task suggestions.

**Request:**
```json
{
  "context": "We need to implement a user dashboard with analytics",
  "boardId": "board-uuid",
  "boardType": "engineering",
  "teamSize": 5,
  "preferences": {
    "complexity": "complex",
    "timeframe": "medium_term",
    "skillLevel": "advanced"
  }
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "suggestions": [
      {
        "title": "Design dashboard wireframes",
        "description": "Create wireframes for user dashboard layout",
        "suggestedFields": {
          "priority": "Medium",
          "estimatedHours": 4,
          "tags": ["design", "ui"],
          "complexity": "Simple"
        },
        "confidence": 0.8,
        "reasoning": ["UI design is crucial first step", "Helps align team vision"],
        "dependencies": []
      }
    ],
    "metadata": {
      "processingTime": 1500,
      "modelVersion": "gpt-4",
      "contextAnalysis": {
        "complexity": "complex",
        "domain": "engineering",
        "estimatedEffort": "medium"
      }
    }
  }
}
```

### POST /ai/auto-complete
Get auto-complete suggestions.

**Request:**
```json
{
  "type": "item_name",
  "partialText": "Implement user",
  "context": {
    "boardId": "board-uuid",
    "fieldType": "name"
  },
  "maxSuggestions": 5
}
```

### POST /ai/smart-assign
Get smart assignment suggestions.

**Request:**
```json
{
  "itemId": "item-uuid",
  "itemDescription": "Implement user authentication system",
  "requiredSkills": ["Node.js", "JWT", "Security"],
  "workloadConsideration": true,
  "availabilityCheck": true,
  "teamOnly": false
}
```

### POST /ai/analyze/workload
Analyze workload and productivity.

**Request:**
```json
{
  "workspaceId": "workspace-uuid",
  "timeRange": {
    "start": "2024-01-01",
    "end": "2024-01-31"
  },
  "includeTeamMembers": true,
  "metrics": ["productivity", "task_distribution", "completion_rate"]
}
```

### POST /ai/optimize/board
Get board optimization suggestions.

**Request:**
```json
{
  "boardId": "board-uuid",
  "analysisType": ["structure", "workflow", "performance"],
  "includeReorganization": true,
  "includeAutomation": true
}
```

## Automation API

### GET /automation/rules
List automation rules.

**Query Parameters:**
- `workspaceId` (string, required): Workspace ID
- `boardId` (string): Filter by board
- `status` (string): Filter by status [active, paused, disabled]
- `triggerType` (string): Filter by trigger type

### POST /automation/rules
Create automation rule.

**Request:**
```json
{
  "name": "Auto-assign urgent tasks",
  "description": "Automatically assign urgent tasks to team lead",
  "workspaceId": "workspace-uuid",
  "boardId": "board-uuid",
  "trigger": {
    "type": "status_changed",
    "parameters": {
      "from": "To Do",
      "to": "In Progress"
    }
  },
  "conditions": [
    {
      "type": "field_equals",
      "field": "priority",
      "value": "High"
    }
  ],
  "actions": [
    {
      "type": "assign_user",
      "parameters": {
        "userId": "team-lead-uuid"
      }
    },
    {
      "type": "send_notification",
      "parameters": {
        "message": "Urgent task assigned to you"
      }
    }
  ],
  "settings": {
    "priority": 50,
    "stopExecution": false,
    "retryAttempts": 3,
    "isActive": true
  }
}
```

### GET /automation/rules/:ruleId
Get automation rule.

### PUT /automation/rules/:ruleId
Update automation rule.

### DELETE /automation/rules/:ruleId
Delete automation rule.

### POST /automation/rules/:ruleId/execute
Manually execute automation rule.

**Request:**
```json
{
  "triggerData": {
    "itemId": "item-uuid",
    "changes": {
      "status": {
        "from": "To Do",
        "to": "In Progress"
      }
    }
  },
  "dryRun": false
}
```

### POST /automation/rules/:ruleId/test
Test automation rule.

**Request:**
```json
{
  "testData": {
    "itemId": "item-uuid",
    "itemData": {
      "status": "In Progress",
      "priority": "High"
    }
  }
}
```

### GET /automation/executions
Get automation execution history.

**Query Parameters:**
- `ruleId` (string): Filter by rule
- `workspaceId` (string): Filter by workspace
- `status` (string): Filter by status [success, partial_success, failed]
- `fromDate` (datetime): Filter from date
- `toDate` (datetime): Filter to date
- `limit` (integer): Items per page

### POST /automation/rules/:ruleId/pause
Pause automation rule.

### POST /automation/rules/:ruleId/resume
Resume automation rule.

### GET /automation/triggers
Get available trigger types.

### GET /automation/actions
Get available action types.

## Analytics API

### GET /analytics/dashboard
Get dashboard analytics.

**Query Parameters:**
- `workspaceId` (string, required): Workspace ID
- `timeRange` (string): Time range [7d, 30d, 90d, 1y]
- `metrics` (array): Metrics to include

### GET /analytics/boards/:boardId
Get board analytics.

### GET /analytics/users/:userId
Get user analytics.

### GET /analytics/reports
Get available reports.

### POST /analytics/reports
Generate custom report.

### GET /analytics/exports/:exportId
Download analytics export.

## Time Tracking API

### POST /time/start
Start time tracking.

**Request:**
```json
{
  "itemId": "item-uuid",
  "description": "Working on authentication"
}
```

### POST /time/stop
Stop time tracking.

**Request:**
```json
{
  "entryId": "entry-uuid"
}
```

### GET /time/entries
Get time entries.

**Query Parameters:**
- `userId` (string): Filter by user
- `itemId` (string): Filter by item
- `fromDate` (date): Filter from date
- `toDate` (date): Filter to date

### POST /time/entries
Create time entry.

**Request:**
```json
{
  "itemId": "item-uuid",
  "startTime": "2024-01-01T09:00:00Z",
  "endTime": "2024-01-01T17:00:00Z",
  "description": "Development work",
  "billable": true
}
```

### PUT /time/entries/:entryId
Update time entry.

### DELETE /time/entries/:entryId
Delete time entry.

## WebSocket API

### Connection
Connect to WebSocket server for real-time updates.

```javascript
const socket = io('wss://api.sunday.com', {
  auth: {
    token: 'jwt-access-token'
  }
});
```

### Events

#### Join Room
```javascript
socket.emit('join_room', {
  roomType: 'board',
  roomId: 'board-uuid'
});
```

#### Item Updates
```javascript
// Listen for item updates
socket.on('item_updated', (data) => {
  console.log('Item updated:', data);
});

// Send item update
socket.emit('item_update', {
  itemId: 'item-uuid',
  updates: {
    name: 'Updated name'
  }
});
```

#### Presence Updates
```javascript
// Update presence
socket.emit('presence_update', {
  roomId: 'board-uuid',
  presence: {
    status: 'active',
    activity: {
      type: 'editing',
      target: 'item-uuid'
    }
  }
});

// Listen for presence changes
socket.on('presence_changed', (data) => {
  console.log('User presence:', data);
});
```

## Error Handling

All API endpoints return standardized error responses:

```json
{
  "success": false,
  "error": {
    "type": "validation_error",
    "message": "Invalid input data",
    "details": {
      "field": "email",
      "code": "invalid_format"
    },
    "requestId": "req_123456789"
  }
}
```

### Error Types
- `validation_error`: Input validation failed
- `authentication_error`: Authentication required or failed
- `authorization_error`: Insufficient permissions
- `not_found_error`: Resource not found
- `conflict_error`: Resource conflict (e.g., duplicate name)
- `rate_limit_error`: Rate limit exceeded
- `internal_error`: Server error

## Rate Limiting

API endpoints are rate limited to prevent abuse:

- Authentication endpoints: 5 requests per minute
- General API endpoints: 100 requests per minute
- File upload endpoints: 10 requests per minute
- AI endpoints: 20 requests per minute

Rate limit headers:
```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1640995200
```

## Pagination

List endpoints use cursor-based pagination:

```json
{
  "data": [...],
  "meta": {
    "page": 1,
    "limit": 20,
    "total": 100,
    "totalPages": 5,
    "hasNext": true,
    "hasPrev": false,
    "nextCursor": "cursor_string",
    "prevCursor": null
  }
}
```

## Webhooks

### POST /webhooks
Create webhook.

**Request:**
```json
{
  "url": "https://example.com/webhook",
  "events": ["item.created", "item.updated", "board.created"],
  "secret": "webhook_secret",
  "isActive": true
}
```

### Webhook Events
- `item.created`
- `item.updated`
- `item.deleted`
- `board.created`
- `board.updated`
- `board.deleted`
- `comment.created`
- `user.assigned`
- `automation.executed`

### Webhook Payload
```json
{
  "event": "item.created",
  "data": {
    "item": {...},
    "user": {...},
    "workspace": {...}
  },
  "timestamp": "2024-01-01T00:00:00Z",
  "webhookId": "webhook-uuid"
}
```

## SDK Examples

### JavaScript/Node.js
```javascript
const SundayAPI = require('@sunday.com/api-client');

const client = new SundayAPI({
  apiKey: 'your-api-key',
  baseURL: 'https://api.sunday.com/api/v1'
});

// Get workspaces
const workspaces = await client.workspaces.list();

// Create board
const board = await client.boards.create({
  workspaceId: 'workspace-uuid',
  name: 'Project Board'
});

// Create item
const item = await client.items.create({
  boardId: board.id,
  name: 'New Task',
  data: {
    status: 'To Do',
    priority: 'High'
  }
});
```

### Python
```python
from sunday_api import SundayClient

client = SundayClient(
    api_key='your-api-key',
    base_url='https://api.sunday.com/api/v1'
)

# Get workspaces
workspaces = client.workspaces.list()

# Create board
board = client.boards.create(
    workspace_id='workspace-uuid',
    name='Project Board'
)

# Create item
item = client.items.create(
    board_id=board['id'],
    name='New Task',
    data={
        'status': 'To Do',
        'priority': 'High'
    }
)
```

## Security

### HTTPS
All API communication must use HTTPS in production.

### Authentication
- JWT tokens with RS256 signing
- Refresh token rotation
- Token expiration: 1 hour (access), 30 days (refresh)

### Authorization
- Role-based access control (RBAC)
- Resource-level permissions
- Workspace and board-level isolation

### Input Validation
- All inputs validated with Joi schemas
- SQL injection prevention with Prisma ORM
- XSS protection with input sanitization

### File Upload Security
- File type validation
- Size limits (10MB per file)
- Virus scanning ready
- Secure S3 presigned URLs

## Testing

All API endpoints include comprehensive test coverage:

- Unit tests for business logic
- Integration tests for API endpoints
- End-to-end tests for complete workflows
- Performance tests for high-load scenarios

### Test Environment
```
Base URL: https://api.test.sunday.com/api/v1
Test Database: Isolated test database
Test Authentication: Test user accounts
```

## Support

### Documentation
- Interactive API documentation: https://docs.sunday.com/api
- OpenAPI specification: https://api.sunday.com/openapi.json
- SDKs and code examples: https://github.com/sunday-com/api-sdks

### Rate Limits and Quotas
- Free tier: 1,000 API calls per month
- Pro tier: 10,000 API calls per month
- Enterprise: Custom quotas

### Support Channels
- API support: api-support@sunday.com
- Documentation issues: docs@sunday.com
- Community forum: https://community.sunday.com

This API implementation provides a robust, scalable foundation for the Sunday.com work management platform with comprehensive authentication, real-time collaboration, AI features, and extensive customization capabilities.