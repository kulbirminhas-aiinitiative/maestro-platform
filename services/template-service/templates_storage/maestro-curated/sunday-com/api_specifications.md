# Sunday.com - API Specifications

## Executive Summary

This document provides comprehensive API specifications for Sunday.com, covering REST APIs, GraphQL APIs, WebSocket protocols, and webhook specifications. The APIs are designed to support web applications, mobile apps, and third-party integrations while maintaining security, performance, and developer experience standards.

## Table of Contents

1. [API Architecture Overview](#api-architecture-overview)
2. [Authentication & Authorization](#authentication--authorization)
3. [REST API Specifications](#rest-api-specifications)
4. [GraphQL API Specifications](#graphql-api-specifications)
5. [WebSocket API Specifications](#websocket-api-specifications)
6. [Webhook Specifications](#webhook-specifications)
7. [Rate Limiting & Throttling](#rate-limiting--throttling)
8. [Error Handling](#error-handling)
9. [API Versioning Strategy](#api-versioning-strategy)
10. [SDKs & Client Libraries](#sdks--client-libraries)

---

## API Architecture Overview

### API Design Principles

1. **API-First Design:** APIs designed before implementation
2. **RESTful Conventions:** Standard HTTP methods and status codes
3. **GraphQL for Flexibility:** Complex queries and real-time subscriptions
4. **WebSocket for Real-time:** Live collaboration and notifications
5. **Versioning:** Backward compatibility and smooth migrations
6. **Security:** Authentication, authorization, and data protection
7. **Performance:** Caching, pagination, and optimization
8. **Developer Experience:** Clear documentation and consistent patterns

### API Ecosystem Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        API Gateway                             │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │     Kong API Gateway / AWS Application Load Balancer       │ │
│  │  • Authentication   • Rate Limiting   • SSL Termination    │ │
│  │  • Request Routing  • Load Balancing  • API Analytics      │ │
│  └─────────────────────────────────────────────────────────────┘ │
├─────────────────────────────────────────────────────────────────┤
│                     API Endpoints                              │
│  ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐  │
│  │    REST API     │ │   GraphQL API   │ │  WebSocket API  │  │
│  │  (CRUD Ops)     │ │ (Complex Query) │ │  (Real-time)    │  │
│  │  /api/v1/*      │ │   /graphql      │ │    /ws          │  │
│  └─────────────────┘ └─────────────────┘ └─────────────────┘  │
├─────────────────────────────────────────────────────────────────┤
│                  Business Services                             │
│  ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐  │
│  │  User Service   │ │ Project Service │ │   AI Service    │  │
│  │  Auth Service   │ │  Board Service  │ │  File Service   │  │
│  └─────────────────┘ └─────────────────┘ └─────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

### API Consumer Types

| Consumer Type | Primary API | Use Cases | Authentication |
|---------------|-------------|-----------|----------------|
| **Web App** | GraphQL + WebSocket | Complex UI, real-time updates | JWT Bearer token |
| **Mobile App** | REST + WebSocket | Mobile-optimized, offline sync | JWT Bearer token |
| **Third-party** | REST + Webhooks | Integrations, automation | API Key + OAuth |
| **Internal Services** | gRPC | Service-to-service | Service account |

---

## Authentication & Authorization

### Authentication Methods

#### 1. JWT Bearer Tokens (Primary)
```http
Authorization: Bearer eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...

# Token Structure
{
  "sub": "user_uuid",
  "iss": "https://auth.sunday.com",
  "aud": "https://api.sunday.com",
  "exp": 1640995200,
  "iat": 1640908800,
  "scope": "read:projects write:projects",
  "org_id": "org_uuid",
  "permissions": ["workspace:read", "board:write"]
}
```

#### 2. API Keys (Third-party)
```http
X-API-Key: sk_live_abc123def456
Authorization: Bearer sk_live_abc123def456
```

#### 3. OAuth 2.0 (Third-party Apps)
```http
# Authorization Code Flow
GET /oauth/authorize?
  client_id=client_uuid&
  redirect_uri=https://app.example.com/callback&
  scope=read:projects%20write:tasks&
  response_type=code&
  state=random_string

# Token Exchange
POST /oauth/token
{
  "grant_type": "authorization_code",
  "code": "auth_code",
  "client_id": "client_uuid",
  "client_secret": "client_secret",
  "redirect_uri": "https://app.example.com/callback"
}
```

### Authorization Model

#### Role-Based Access Control (RBAC)
```typescript
interface UserPermissions {
  organization: {
    id: string;
    role: 'owner' | 'admin' | 'member';
    permissions: string[];
  };
  workspaces: Array<{
    id: string;
    role: 'admin' | 'member' | 'viewer';
    permissions: string[];
  }>;
  boards: Array<{
    id: string;
    permissions: string[];
  }>;
}

// Permission Examples
const permissions = [
  'org:read', 'org:write', 'org:admin',
  'workspace:read', 'workspace:write', 'workspace:admin',
  'board:read', 'board:write', 'board:admin',
  'item:read', 'item:write', 'item:delete',
  'comment:read', 'comment:write', 'comment:delete',
  'file:read', 'file:write', 'file:delete',
  'automation:read', 'automation:write',
  'analytics:read'
];
```

---

## REST API Specifications

### Base Configuration

```yaml
# OpenAPI 3.0 Specification
openapi: 3.0.3
info:
  title: Sunday.com API
  version: 1.0.0
  description: Work management platform API
  contact:
    name: API Support
    url: https://docs.sunday.com
    email: api-support@sunday.com

servers:
  - url: https://api.sunday.com/v1
    description: Production server
  - url: https://api-staging.sunday.com/v1
    description: Staging server

security:
  - BearerAuth: []
  - ApiKeyAuth: []
```

### Core Resource APIs

#### Organizations API

```yaml
/organizations:
  get:
    summary: List organizations
    parameters:
      - name: limit
        in: query
        schema:
          type: integer
          minimum: 1
          maximum: 100
          default: 20
      - name: cursor
        in: query
        schema:
          type: string
    responses:
      200:
        description: Success
        content:
          application/json:
            schema:
              type: object
              properties:
                data:
                  type: array
                  items:
                    $ref: '#/components/schemas/Organization'
                pagination:
                  $ref: '#/components/schemas/Pagination'

  post:
    summary: Create organization
    requestBody:
      required: true
      content:
        application/json:
          schema:
            type: object
            properties:
              name:
                type: string
                minLength: 1
                maxLength: 255
              slug:
                type: string
                pattern: '^[a-z0-9-]+$'
              domain:
                type: string
                format: hostname
            required: [name, slug]
    responses:
      201:
        description: Created
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/Organization'

/organizations/{org_id}:
  get:
    summary: Get organization
    parameters:
      - name: org_id
        in: path
        required: true
        schema:
          type: string
          format: uuid
    responses:
      200:
        description: Success
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/Organization'
      404:
        $ref: '#/components/responses/NotFound'

  put:
    summary: Update organization
    parameters:
      - name: org_id
        in: path
        required: true
        schema:
          type: string
          format: uuid
    requestBody:
      required: true
      content:
        application/json:
          schema:
            $ref: '#/components/schemas/OrganizationUpdate'
    responses:
      200:
        description: Updated
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/Organization'
```

#### Workspaces API

```yaml
/organizations/{org_id}/workspaces:
  get:
    summary: List workspaces
    parameters:
      - name: org_id
        in: path
        required: true
        schema:
          type: string
          format: uuid
    responses:
      200:
        description: Success
        content:
          application/json:
            schema:
              type: object
              properties:
                data:
                  type: array
                  items:
                    $ref: '#/components/schemas/Workspace'

  post:
    summary: Create workspace
    requestBody:
      content:
        application/json:
          schema:
            type: object
            properties:
              name:
                type: string
                minLength: 1
                maxLength: 255
              description:
                type: string
                maxLength: 1000
              color:
                type: string
                pattern: '^#[0-9A-Fa-f]{6}$'
              is_private:
                type: boolean
                default: false
            required: [name]
```

#### Boards API

```yaml
/workspaces/{workspace_id}/boards:
  get:
    summary: List boards
    parameters:
      - name: workspace_id
        in: path
        required: true
        schema:
          type: string
          format: uuid
      - name: include
        in: query
        schema:
          type: array
          items:
            type: string
            enum: [columns, items, members]
    responses:
      200:
        description: Success
        content:
          application/json:
            schema:
              type: object
              properties:
                data:
                  type: array
                  items:
                    $ref: '#/components/schemas/Board'

  post:
    summary: Create board
    requestBody:
      content:
        application/json:
          schema:
            type: object
            properties:
              name:
                type: string
                minLength: 1
                maxLength: 255
              description:
                type: string
                maxLength: 1000
              template_id:
                type: string
                format: uuid
              folder_id:
                type: string
                format: uuid
              settings:
                type: object
            required: [name]

/boards/{board_id}:
  get:
    summary: Get board with items
    parameters:
      - name: board_id
        in: path
        required: true
        schema:
          type: string
          format: uuid
      - name: include
        in: query
        schema:
          type: array
          items:
            type: string
            enum: [columns, items, members, activity]
    responses:
      200:
        description: Success
        content:
          application/json:
            schema:
              allOf:
                - $ref: '#/components/schemas/Board'
                - type: object
                  properties:
                    columns:
                      type: array
                      items:
                        $ref: '#/components/schemas/BoardColumn'
                    items:
                      type: array
                      items:
                        $ref: '#/components/schemas/Item'
```

#### Items API

```yaml
/boards/{board_id}/items:
  get:
    summary: List board items
    parameters:
      - name: board_id
        in: path
        required: true
        schema:
          type: string
          format: uuid
      - name: filter
        in: query
        style: deepObject
        explode: true
        schema:
          type: object
          properties:
            status:
              type: array
              items:
                type: string
            assignee:
              type: array
              items:
                type: string
                format: uuid
            due_date:
              type: object
              properties:
                from:
                  type: string
                  format: date
                to:
                  type: string
                  format: date
      - name: sort
        in: query
        schema:
          type: array
          items:
            type: string
            enum: [position, created_at, updated_at, due_date]
      - name: order
        in: query
        schema:
          type: string
          enum: [asc, desc]
          default: asc
    responses:
      200:
        description: Success
        content:
          application/json:
            schema:
              type: object
              properties:
                data:
                  type: array
                  items:
                    $ref: '#/components/schemas/Item'
                meta:
                  type: object
                  properties:
                    total_count:
                      type: integer
                    filter_count:
                      type: integer

  post:
    summary: Create item
    requestBody:
      content:
        application/json:
          schema:
            type: object
            properties:
              name:
                type: string
                minLength: 1
                maxLength: 500
              description:
                type: string
                maxLength: 10000
              parent_id:
                type: string
                format: uuid
              position:
                type: number
                format: decimal
              data:
                type: object
              assignees:
                type: array
                items:
                  type: string
                  format: uuid
            required: [name]

/items/{item_id}:
  get:
    summary: Get item details
    parameters:
      - name: item_id
        in: path
        required: true
        schema:
          type: string
          format: uuid
      - name: include
        in: query
        schema:
          type: array
          items:
            type: string
            enum: [comments, attachments, dependencies, time_entries]
    responses:
      200:
        description: Success
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/ItemDetailed'

  put:
    summary: Update item
    parameters:
      - name: item_id
        in: path
        required: true
        schema:
          type: string
          format: uuid
    requestBody:
      content:
        application/json:
          schema:
            $ref: '#/components/schemas/ItemUpdate'
    responses:
      200:
        description: Updated
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/Item'

  delete:
    summary: Delete item
    parameters:
      - name: item_id
        in: path
        required: true
        schema:
          type: string
          format: uuid
    responses:
      204:
        description: Deleted
```

#### Bulk Operations API

```yaml
/items/bulk:
  put:
    summary: Bulk update items
    requestBody:
      content:
        application/json:
          schema:
            type: object
            properties:
              item_ids:
                type: array
                items:
                  type: string
                  format: uuid
                maxItems: 100
              updates:
                type: object
                properties:
                  data:
                    type: object
                  assignees:
                    type: array
                    items:
                      type: string
                      format: uuid
            required: [item_ids, updates]
    responses:
      200:
        description: Updated
        content:
          application/json:
            schema:
              type: object
              properties:
                updated_count:
                  type: integer
                errors:
                  type: array
                  items:
                    type: object
                    properties:
                      item_id:
                        type: string
                        format: uuid
                      error:
                        type: string

  delete:
    summary: Bulk delete items
    requestBody:
      content:
        application/json:
          schema:
            type: object
            properties:
              item_ids:
                type: array
                items:
                  type: string
                  format: uuid
                maxItems: 100
            required: [item_ids]
    responses:
      200:
        description: Deleted
        content:
          application/json:
            schema:
              type: object
              properties:
                deleted_count:
                  type: integer
```

### Data Schemas

```yaml
components:
  schemas:
    Organization:
      type: object
      properties:
        id:
          type: string
          format: uuid
        name:
          type: string
        slug:
          type: string
        domain:
          type: string
        settings:
          type: object
        subscription_plan:
          type: string
          enum: [free, pro, enterprise]
        created_at:
          type: string
          format: date-time
        updated_at:
          type: string
          format: date-time

    Workspace:
      type: object
      properties:
        id:
          type: string
          format: uuid
        organization_id:
          type: string
          format: uuid
        name:
          type: string
        description:
          type: string
        color:
          type: string
        is_private:
          type: boolean
        settings:
          type: object
        created_at:
          type: string
          format: date-time

    Board:
      type: object
      properties:
        id:
          type: string
          format: uuid
        workspace_id:
          type: string
          format: uuid
        name:
          type: string
        description:
          type: string
        settings:
          type: object
        view_settings:
          type: object
        is_private:
          type: boolean
        created_by:
          $ref: '#/components/schemas/User'
        created_at:
          type: string
          format: date-time

    BoardColumn:
      type: object
      properties:
        id:
          type: string
          format: uuid
        board_id:
          type: string
          format: uuid
        name:
          type: string
        column_type:
          type: string
          enum: [text, number, status, date, people, timeline, files]
        settings:
          type: object
        validation_rules:
          type: object
        position:
          type: integer
        is_required:
          type: boolean
        is_visible:
          type: boolean

    Item:
      type: object
      properties:
        id:
          type: string
          format: uuid
        board_id:
          type: string
          format: uuid
        parent_id:
          type: string
          format: uuid
        name:
          type: string
        description:
          type: string
        data:
          type: object
        position:
          type: number
          format: decimal
        assignees:
          type: array
          items:
            $ref: '#/components/schemas/User'
        created_by:
          $ref: '#/components/schemas/User'
        created_at:
          type: string
          format: date-time
        updated_at:
          type: string
          format: date-time

    User:
      type: object
      properties:
        id:
          type: string
          format: uuid
        email:
          type: string
          format: email
        first_name:
          type: string
        last_name:
          type: string
        avatar_url:
          type: string
          format: uri

    Pagination:
      type: object
      properties:
        next_cursor:
          type: string
        has_more:
          type: boolean
        total_count:
          type: integer

    Error:
      type: object
      properties:
        error:
          type: object
          properties:
            type:
              type: string
            message:
              type: string
            details:
              type: object
```

---

## GraphQL API Specifications

### Schema Definition

```graphql
# User Types
type User {
  id: ID!
  email: String!
  firstName: String
  lastName: String
  fullName: String!
  avatarUrl: String
  timezone: String!
  locale: String!
  settings: JSON!
  lastLoginAt: DateTime
  createdAt: DateTime!
  updatedAt: DateTime!
}

# Organization Types
type Organization {
  id: ID!
  name: String!
  slug: String!
  domain: String
  settings: JSON!
  subscriptionPlan: SubscriptionPlan!
  subscriptionStatus: SubscriptionStatus!
  workspaces(first: Int, after: String): WorkspaceConnection!
  members(first: Int, after: String): OrganizationMemberConnection!
  createdAt: DateTime!
  updatedAt: DateTime!
}

type OrganizationMember {
  id: ID!
  organization: Organization!
  user: User!
  role: OrganizationRole!
  status: MembershipStatus!
  invitedBy: User
  invitedAt: DateTime
  joinedAt: DateTime
  createdAt: DateTime!
}

enum OrganizationRole {
  OWNER
  ADMIN
  MEMBER
}

enum SubscriptionPlan {
  FREE
  PRO
  ENTERPRISE
}

# Workspace Types
type Workspace {
  id: ID!
  organization: Organization!
  name: String!
  description: String
  color: String!
  isPrivate: Boolean!
  settings: JSON!
  boards(first: Int, after: String, filter: BoardFilter): BoardConnection!
  members(first: Int, after: String): WorkspaceMemberConnection!
  createdAt: DateTime!
  updatedAt: DateTime!
}

input BoardFilter {
  name: String
  isPrivate: Boolean
  folderId: ID
}

# Board Types
type Board {
  id: ID!
  workspace: Workspace!
  name: String!
  description: String
  settings: JSON!
  viewSettings: JSON!
  isPrivate: Boolean!
  folder: Folder
  position: Int
  columns: [BoardColumn!]!
  items(
    first: Int
    after: String
    filter: ItemFilter
    sort: [ItemSort!]
  ): ItemConnection!
  members: [BoardMember!]!
  createdBy: User!
  createdAt: DateTime!
  updatedAt: DateTime!
}

type BoardColumn {
  id: ID!
  board: Board!
  name: String!
  columnType: ColumnType!
  settings: JSON!
  validationRules: JSON!
  position: Int!
  isRequired: Boolean!
  isVisible: Boolean!
  createdAt: DateTime!
}

enum ColumnType {
  TEXT
  NUMBER
  STATUS
  DATE
  PEOPLE
  TIMELINE
  FILES
  CHECKBOX
  RATING
  EMAIL
  PHONE
  URL
}

# Item Types
type Item {
  id: ID!
  board: Board!
  parent: Item
  name: String!
  description: String
  data: JSON!
  position: Decimal!
  assignees: [User!]!
  dependencies: [ItemDependency!]!
  comments(first: Int, after: String): CommentConnection!
  attachments: [FileAttachment!]!
  timeEntries: [TimeEntry!]!
  subtasks: [Item!]!
  createdBy: User!
  createdAt: DateTime!
  updatedAt: DateTime!
}

input ItemFilter {
  parentId: ID
  assigneeIds: [ID!]
  status: [String!]
  dueDateFrom: DateTime
  dueDateTo: DateTime
  search: String
}

input ItemSort {
  field: ItemSortField!
  direction: SortDirection!
}

enum ItemSortField {
  POSITION
  CREATED_AT
  UPDATED_AT
  DUE_DATE
  NAME
}

enum SortDirection {
  ASC
  DESC
}

type ItemDependency {
  id: ID!
  predecessor: Item!
  successor: Item!
  dependencyType: DependencyType!
  createdBy: User!
  createdAt: DateTime!
}

enum DependencyType {
  BLOCKS
  RELATED
}

# Comment Types
type Comment {
  id: ID!
  item: Item!
  parent: Comment
  user: User!
  content: String!
  contentType: ContentType!
  mentions: [User!]!
  attachments: [FileAttachment!]!
  isEdited: Boolean!
  replies: [Comment!]!
  createdAt: DateTime!
  updatedAt: DateTime!
}

enum ContentType {
  TEXT
  MARKDOWN
}

# File Types
type File {
  id: ID!
  originalName: String!
  fileKey: String!
  fileSize: Int!
  mimeType: String
  thumbnailKey: String
  uploadedBy: User!
  createdAt: DateTime!
}

type FileAttachment {
  id: ID!
  file: File!
  entityType: String!
  entityId: ID!
  attachedBy: User!
  attachedAt: DateTime!
}

# Time Tracking Types
type TimeEntry {
  id: ID!
  item: Item!
  user: User!
  description: String
  startTime: DateTime!
  endTime: DateTime
  durationSeconds: Int
  isBillable: Boolean!
  createdAt: DateTime!
  updatedAt: DateTime!
}

# Analytics Types
type AnalyticsData {
  totalItems: Int!
  completedItems: Int!
  activeUsers: Int!
  averageCompletionTime: Float
  productivityScore: Float
  trends: [AnalyticsTrend!]!
}

type AnalyticsTrend {
  date: Date!
  value: Float!
  metric: String!
}

# Connection Types
type BoardConnection {
  edges: [BoardEdge!]!
  pageInfo: PageInfo!
  totalCount: Int!
}

type BoardEdge {
  node: Board!
  cursor: String!
}

type ItemConnection {
  edges: [ItemEdge!]!
  pageInfo: PageInfo!
  totalCount: Int!
}

type ItemEdge {
  node: Item!
  cursor: String!
}

type PageInfo {
  hasNextPage: Boolean!
  hasPreviousPage: Boolean!
  startCursor: String
  endCursor: String
}

# Custom Scalars
scalar DateTime
scalar Date
scalar JSON
scalar Decimal
```

### Query Examples

#### 1. Workspace Overview Query
```graphql
query WorkspaceOverview($workspaceId: ID!) {
  workspace(id: $workspaceId) {
    id
    name
    description
    boards(first: 20) {
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

#### 2. Board with Items Query
```graphql
query BoardWithItems(
  $boardId: ID!
  $itemsFirst: Int = 50
  $itemsFilter: ItemFilter
) {
  board(id: $boardId) {
    id
    name
    description
    settings
    columns {
      id
      name
      columnType
      settings
      position
      isRequired
    }
    items(first: $itemsFirst, filter: $itemsFilter) {
      edges {
        node {
          id
          name
          description
          data
          position
          assignees {
            id
            fullName
            avatarUrl
          }
          dependencies {
            id
            predecessor {
              id
              name
            }
            dependencyType
          }
          createdAt
          updatedAt
        }
      }
      pageInfo {
        hasNextPage
        endCursor
      }
      totalCount
    }
  }
}
```

### Mutation Examples

#### 1. Create Item Mutation
```graphql
mutation CreateItem($input: CreateItemInput!) {
  createItem(input: $input) {
    item {
      id
      name
      description
      data
      position
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

input CreateItemInput {
  boardId: ID!
  name: String!
  description: String
  parentId: ID
  data: JSON
  position: Decimal
  assigneeIds: [ID!]
}
```

#### 2. Update Item Mutation
```graphql
mutation UpdateItem($id: ID!, $input: UpdateItemInput!) {
  updateItem(id: $id, input: $input) {
    item {
      id
      name
      data
      updatedAt
    }
    errors {
      field
      message
    }
  }
}

input UpdateItemInput {
  name: String
  description: String
  data: JSON
  position: Decimal
  assigneeIds: [ID!]
}
```

#### 3. Bulk Update Items Mutation
```graphql
mutation BulkUpdateItems($input: BulkUpdateItemsInput!) {
  bulkUpdateItems(input: $input) {
    updatedCount
    errors {
      itemId
      message
    }
  }
}

input BulkUpdateItemsInput {
  itemIds: [ID!]!
  updates: ItemUpdates!
}

input ItemUpdates {
  data: JSON
  assigneeIds: [ID!]
  position: Decimal
}
```

### Subscription Examples

#### 1. Board Updates Subscription
```graphql
subscription BoardUpdates($boardId: ID!) {
  boardUpdates(boardId: $boardId) {
    type
    item {
      id
      name
      data
      position
      assignees {
        id
        fullName
      }
      updatedAt
    }
    user {
      id
      fullName
    }
  }
}
```

#### 2. User Presence Subscription
```graphql
subscription UserPresence($boardId: ID!) {
  userPresence(boardId: $boardId) {
    type # JOINED, LEFT, CURSOR_MOVED
    user {
      id
      fullName
      avatarUrl
    }
    cursor {
      x
      y
    }
    timestamp
  }
}
```

---

## WebSocket API Specifications

### Connection Protocol

#### 1. Connection Establishment
```typescript
// Client connection
const ws = new WebSocket('wss://api.sunday.com/ws');

// Authentication
ws.onopen = () => {
  ws.send(JSON.stringify({
    type: 'auth',
    token: 'jwt_token_here'
  }));
};

// Server response
{
  "type": "auth_success",
  "user_id": "user_uuid",
  "connection_id": "conn_uuid"
}
```

#### 2. Channel Subscription
```typescript
// Subscribe to board updates
ws.send(JSON.stringify({
  type: 'subscribe',
  channel: 'board:board_uuid',
  params: {
    include_presence: true
  }
}));

// Server confirmation
{
  "type": "subscribed",
  "channel": "board:board_uuid",
  "subscription_id": "sub_uuid"
}
```

### Message Types

#### 1. Item Updates
```typescript
// Item created
{
  "type": "item_created",
  "channel": "board:board_uuid",
  "data": {
    "item": {
      "id": "item_uuid",
      "name": "New task",
      "data": {...},
      "position": 1.5,
      "created_by": "user_uuid"
    },
    "user": {
      "id": "user_uuid",
      "name": "John Doe"
    }
  },
  "timestamp": "2024-12-01T10:00:00Z"
}

// Item updated
{
  "type": "item_updated",
  "channel": "board:board_uuid",
  "data": {
    "item_id": "item_uuid",
    "changes": {
      "name": {
        "old": "Old name",
        "new": "New name"
      },
      "data.status": {
        "old": "In Progress",
        "new": "Done"
      }
    },
    "updated_by": "user_uuid"
  },
  "timestamp": "2024-12-01T10:01:00Z"
}
```

#### 2. User Presence
```typescript
// User joined board
{
  "type": "user_joined",
  "channel": "board:board_uuid",
  "data": {
    "user": {
      "id": "user_uuid",
      "name": "Jane Smith",
      "avatar_url": "https://..."
    },
    "cursor": {
      "x": 100,
      "y": 200
    }
  }
}

// Cursor movement
{
  "type": "cursor_moved",
  "channel": "board:board_uuid",
  "data": {
    "user_id": "user_uuid",
    "cursor": {
      "x": 150,
      "y": 250
    }
  }
}

// User left board
{
  "type": "user_left",
  "channel": "board:board_uuid",
  "data": {
    "user_id": "user_uuid"
  }
}
```

#### 3. Comments & Collaboration
```typescript
// Comment added
{
  "type": "comment_added",
  "channel": "item:item_uuid",
  "data": {
    "comment": {
      "id": "comment_uuid",
      "content": "Great work!",
      "user": {
        "id": "user_uuid",
        "name": "Alice Johnson"
      },
      "mentions": ["user_uuid_2"],
      "created_at": "2024-12-01T10:02:00Z"
    }
  }
}

// Typing indicators
{
  "type": "user_typing",
  "channel": "item:item_uuid",
  "data": {
    "user_id": "user_uuid",
    "is_typing": true
  }
}
```

### Client Implementation Examples

#### JavaScript Client
```typescript
class SundayWebSocketClient {
  private ws: WebSocket;
  private subscriptions: Map<string, Set<Function>> = new Map();

  constructor(private token: string) {
    this.connect();
  }

  private connect() {
    this.ws = new WebSocket('wss://api.sunday.com/ws');

    this.ws.onopen = () => {
      this.authenticate();
    };

    this.ws.onmessage = (event) => {
      const message = JSON.parse(event.data);
      this.handleMessage(message);
    };

    this.ws.onclose = () => {
      setTimeout(() => this.connect(), 1000); // Reconnect
    };
  }

  private authenticate() {
    this.send({
      type: 'auth',
      token: this.token
    });
  }

  subscribe(channel: string, callback: Function) {
    if (!this.subscriptions.has(channel)) {
      this.subscriptions.set(channel, new Set());
      this.send({
        type: 'subscribe',
        channel
      });
    }
    this.subscriptions.get(channel)!.add(callback);
  }

  unsubscribe(channel: string, callback?: Function) {
    if (callback) {
      this.subscriptions.get(channel)?.delete(callback);
    } else {
      this.subscriptions.delete(channel);
      this.send({
        type: 'unsubscribe',
        channel
      });
    }
  }

  private handleMessage(message: any) {
    const { channel, type, data } = message;

    if (channel && this.subscriptions.has(channel)) {
      this.subscriptions.get(channel)!.forEach(callback => {
        callback({ type, data, channel });
      });
    }
  }

  private send(message: any) {
    if (this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(message));
    }
  }
}

// Usage
const client = new SundayWebSocketClient('jwt_token');

client.subscribe('board:board_uuid', ({ type, data }) => {
  switch (type) {
    case 'item_created':
      console.log('New item:', data.item);
      break;
    case 'item_updated':
      console.log('Item updated:', data.changes);
      break;
    case 'user_joined':
      console.log('User joined:', data.user);
      break;
  }
});
```

---

## Webhook Specifications

### Webhook Configuration

#### 1. Webhook Registration
```http
POST /api/v1/webhooks
Authorization: Bearer <token>
Content-Type: application/json

{
  "url": "https://myapp.com/webhooks/sunday",
  "events": [
    "item.created",
    "item.updated",
    "item.deleted",
    "comment.added"
  ],
  "secret": "webhook_secret_key",
  "active": true,
  "filters": {
    "board_ids": ["board_uuid_1", "board_uuid_2"],
    "workspace_ids": ["workspace_uuid"]
  }
}
```

#### 2. Webhook Delivery
```http
POST /webhooks/sunday HTTP/1.1
Host: myapp.com
Content-Type: application/json
X-Sunday-Event: item.created
X-Sunday-Signature: sha256=hash_value
X-Sunday-Delivery: delivery_uuid
User-Agent: Sunday-Hookshot/1.0

{
  "event": "item.created",
  "timestamp": "2024-12-01T10:00:00Z",
  "data": {
    "item": {
      "id": "item_uuid",
      "board_id": "board_uuid",
      "name": "New task",
      "data": {...},
      "created_by": "user_uuid"
    },
    "board": {
      "id": "board_uuid",
      "name": "Project Board",
      "workspace_id": "workspace_uuid"
    },
    "user": {
      "id": "user_uuid",
      "name": "John Doe",
      "email": "john@example.com"
    }
  }
}
```

### Webhook Events

#### Available Events
```typescript
interface WebhookEvents {
  // Item events
  'item.created': ItemCreatedPayload;
  'item.updated': ItemUpdatedPayload;
  'item.deleted': ItemDeletedPayload;
  'item.assigned': ItemAssignedPayload;
  'item.unassigned': ItemUnassignedPayload;

  // Comment events
  'comment.added': CommentAddedPayload;
  'comment.updated': CommentUpdatedPayload;
  'comment.deleted': CommentDeletedPayload;

  // Board events
  'board.created': BoardCreatedPayload;
  'board.updated': BoardUpdatedPayload;
  'board.deleted': BoardDeletedPayload;

  // User events
  'user.invited': UserInvitedPayload;
  'user.joined': UserJoinedPayload;
  'user.left': UserLeftPayload;

  // Automation events
  'automation.executed': AutomationExecutedPayload;
  'automation.failed': AutomationFailedPayload;
}
```

### Webhook Security

#### 1. Signature Verification
```typescript
// Verify webhook signature
function verifyWebhookSignature(
  payload: string,
  signature: string,
  secret: string
): boolean {
  const expectedSignature = crypto
    .createHmac('sha256', secret)
    .update(payload)
    .digest('hex');

  return signature === `sha256=${expectedSignature}`;
}

// Express middleware
app.use('/webhooks/sunday', express.raw({ type: 'application/json' }));

app.post('/webhooks/sunday', (req, res) => {
  const signature = req.headers['x-sunday-signature'] as string;
  const payload = req.body.toString();

  if (!verifyWebhookSignature(payload, signature, WEBHOOK_SECRET)) {
    return res.status(401).send('Invalid signature');
  }

  const event = JSON.parse(payload);
  handleWebhookEvent(event);

  res.status(200).send('OK');
});
```

#### 2. Retry Logic
```yaml
Retry Policy:
  - Initial delivery attempt
  - Retry after 1 minute (if failed)
  - Retry after 5 minutes
  - Retry after 15 minutes
  - Retry after 1 hour
  - Retry after 6 hours
  - Final retry after 24 hours

Failure Conditions:
  - HTTP status >= 400
  - Connection timeout (30 seconds)
  - DNS resolution failure

Success Conditions:
  - HTTP status 200-299
  - Response received within 30 seconds
```

---

## Rate Limiting & Throttling

### Rate Limit Tiers

| Plan | API Calls/minute | Burst Limit | WebSocket Connections |
|------|------------------|-------------|----------------------|
| **Free** | 100 | 200 | 5 |
| **Pro** | 1,000 | 2,000 | 50 |
| **Enterprise** | 10,000 | 20,000 | 500 |

### Implementation

```typescript
// Rate limiting headers
interface RateLimitHeaders {
  'X-RateLimit-Limit': number;
  'X-RateLimit-Remaining': number;
  'X-RateLimit-Reset': number;
  'X-RateLimit-Retry-After'?: number;
}

// Example response with rate limit headers
HTTP/1.1 200 OK
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 999
X-RateLimit-Reset: 1640995200
Content-Type: application/json

{
  "data": {...}
}

// Rate limit exceeded response
HTTP/1.1 429 Too Many Requests
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 0
X-RateLimit-Reset: 1640995200
X-RateLimit-Retry-After: 60
Content-Type: application/json

{
  "error": {
    "type": "rate_limit_exceeded",
    "message": "API rate limit exceeded. Retry after 60 seconds."
  }
}
```

---

## Error Handling

### Error Response Format

```typescript
interface APIError {
  error: {
    type: string;
    message: string;
    details?: Record<string, any>;
    request_id?: string;
  };
}

// Example error responses
{
  "error": {
    "type": "validation_error",
    "message": "Invalid input parameters",
    "details": {
      "name": ["Name is required"],
      "email": ["Invalid email format"]
    },
    "request_id": "req_123abc"
  }
}

{
  "error": {
    "type": "not_found",
    "message": "Board not found",
    "request_id": "req_456def"
  }
}

{
  "error": {
    "type": "permission_denied",
    "message": "Insufficient permissions to access this resource",
    "request_id": "req_789ghi"
  }
}
```

### HTTP Status Codes

| Status Code | Description | Usage |
|-------------|-------------|-------|
| **200** | OK | Successful GET, PUT requests |
| **201** | Created | Successful POST requests |
| **204** | No Content | Successful DELETE requests |
| **400** | Bad Request | Invalid request parameters |
| **401** | Unauthorized | Missing or invalid authentication |
| **403** | Forbidden | Insufficient permissions |
| **404** | Not Found | Resource does not exist |
| **409** | Conflict | Resource conflict (duplicate, dependency) |
| **422** | Unprocessable Entity | Validation errors |
| **429** | Too Many Requests | Rate limit exceeded |
| **500** | Internal Server Error | Server-side errors |
| **503** | Service Unavailable | Temporary service issues |

---

## API Versioning Strategy

### Versioning Approach

1. **URL Versioning** (Primary)
   ```
   https://api.sunday.com/v1/boards
   https://api.sunday.com/v2/boards
   ```

2. **Header Versioning** (Alternative)
   ```http
   Accept: application/vnd.sunday.v1+json
   Sunday-Version: 2024-12-01
   ```

### Version Lifecycle

```typescript
interface APIVersion {
  version: string;
  release_date: string;
  deprecation_date?: string;
  sunset_date?: string;
  status: 'active' | 'deprecated' | 'sunset';
}

const versions: APIVersion[] = [
  {
    version: 'v1',
    release_date: '2024-12-01',
    status: 'active'
  },
  {
    version: 'v2',
    release_date: '2025-06-01',
    status: 'active'
  }
];
```

### Breaking Changes Policy

- **Backward Compatibility:** Maintained for 18 months
- **Deprecation Notice:** 12 months before removal
- **Migration Guide:** Provided for all breaking changes
- **Sunset Headers:** Added to deprecated endpoints

```http
Sunset: Sat, 31 Dec 2025 23:59:59 GMT
Deprecation: Tue, 31 Dec 2024 23:59:59 GMT
Link: <https://docs.sunday.com/api/migration/v1-to-v2>; rel="sunset"
```

---

## SDKs & Client Libraries

### Official SDKs

#### JavaScript/TypeScript SDK
```typescript
import { SundayClient } from '@sunday/sdk';

const client = new SundayClient({
  apiKey: 'your_api_key',
  baseUrl: 'https://api.sunday.com/v1'
});

// Get workspaces
const workspaces = await client.workspaces.list({
  organizationId: 'org_uuid'
});

// Create board
const board = await client.boards.create({
  workspaceId: 'workspace_uuid',
  name: 'My Board',
  description: 'Project board'
});

// Real-time updates
client.realtime.subscribe('board:board_uuid', (event) => {
  console.log('Board update:', event);
});
```

#### Python SDK
```python
from sunday import SundayClient

client = SundayClient(api_key='your_api_key')

# Get workspaces
workspaces = client.workspaces.list(organization_id='org_uuid')

# Create item
item = client.items.create(
    board_id='board_uuid',
    name='New task',
    data={'status': 'To Do', 'priority': 'High'}
)

# Bulk operations
client.items.bulk_update(
    item_ids=['item1', 'item2'],
    updates={'data': {'status': 'Done'}}
)
```

#### React Hooks
```typescript
import { useSundayQuery, useSundayMutation } from '@sunday/react';

function BoardComponent({ boardId }: { boardId: string }) {
  // Query hook
  const { data: board, loading, error } = useSundayQuery({
    query: GET_BOARD_QUERY,
    variables: { boardId }
  });

  // Mutation hook
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

  return (
    <div>
      {loading ? (
        <div>Loading...</div>
      ) : (
        <div>
          <h1>{board.name}</h1>
          {/* Board content */}
        </div>
      )}
    </div>
  );
}
```

---

## Conclusion

This comprehensive API specification provides a robust, scalable, and developer-friendly interface for Sunday.com that supports web applications, mobile apps, and third-party integrations. The multi-protocol approach (REST, GraphQL, WebSocket) ensures optimal performance and flexibility for different use cases.

### Key API Features Summary

1. **RESTful Design:** Standard HTTP methods and status codes
2. **GraphQL Flexibility:** Complex queries and real-time subscriptions
3. **Real-time Communication:** WebSocket for live collaboration
4. **Webhook Integration:** Event-driven third-party integrations
5. **Enterprise Security:** JWT, OAuth 2.0, and API key authentication
6. **Performance Optimization:** Rate limiting, caching, and pagination
7. **Developer Experience:** Comprehensive SDKs and documentation

### Performance Targets

- **API Response Time:** <200ms for 95% of requests
- **GraphQL Query Time:** <500ms for complex queries
- **WebSocket Latency:** <100ms for real-time updates
- **Webhook Delivery:** <5 seconds for event notification
- **Rate Limits:** Tiered limits based on subscription plan

---

*Document Version: 1.0*
*Created: December 2024*
*Next Review: Q1 2025*
*Approval Required: CTO, API Architect, Developer Experience Team*