# Sunday.com - API Architecture Specifications
## Comprehensive API Design for Missing Service Implementation

**Document Version:** 1.0 - Implementation Ready
**Date:** December 19, 2024
**Author:** Solution Architect
**Project Phase:** Iteration 2 - Core Feature Implementation
**Focus:** Missing Service API Specifications & Implementation Guidance

---

## Executive Summary

This document provides detailed API architecture specifications for the missing Sunday.com services identified in the gap analysis. It focuses on the critical 5,547+ lines of business logic implementation, covering the 7 core services with 105 methods requiring comprehensive API design and testing integration.

### API Implementation Priorities

**1. Core Business Logic APIs** - 7 services with 105 methods
**2. Real-time Collaboration APIs** - WebSocket and REST integration
**3. AI Integration APIs** - Bridge backend AI services to frontend
**4. Testing Infrastructure APIs** - Test harness and validation endpoints
**5. Performance Monitoring APIs** - Metrics and health check endpoints

---

## Table of Contents

1. [API Architecture Overview](#api-architecture-overview)
2. [Core Service API Specifications](#core-service-api-specifications)
3. [Real-time Collaboration APIs](#real-time-collaboration-apis)
4. [AI Integration API Design](#ai-integration-api-design)
5. [Testing Infrastructure APIs](#testing-infrastructure-apis)
6. [Performance & Monitoring APIs](#performance--monitoring-apis)
7. [Security & Authentication APIs](#security--authentication-apis)
8. [Implementation Guidelines](#implementation-guidelines)

---

## API Architecture Overview

### Complete API Ecosystem

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                           Sunday.com API Architecture                               │
│                               Complete Ecosystem                                    │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                     │
│  ┌─────────────────────────────────────────────────────────────────────────────┐   │
│  │                          External API Layer                                │   │
│  │                                                                             │   │
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐            │   │
│  │  │   REST API      │  │   GraphQL API   │  │  WebSocket API  │            │   │
│  │  │   (v1, v2)      │  │   (Flexible)    │  │  (Real-time)    │            │   │
│  │  │                 │  │                 │  │                 │            │   │
│  │  │ • Public        │  │ • Complex Queries│  │ • Live Updates  │            │   │
│  │  │ • Versioned     │  │ • Single Request │  │ • Presence      │            │   │
│  │  │ • Standards     │  │ • Type Safety   │  │ • Collaboration │            │   │
│  │  │ • Cacheable     │  │ • Real-time     │  │ • Low Latency   │            │   │
│  │  └─────────────────┘  └─────────────────┘  └─────────────────┘            │   │
│  └─────────────────────────────────────────────────────────────────────────────┘   │
│                                      │                                              │
│                                      ▼                                              │
│  ┌─────────────────────────────────────────────────────────────────────────────┐   │
│  │                          API Gateway Layer                                 │   │
│  │                                                                             │   │
│  │  ┌─────────────────────────────────────────────────────────────────────┐   │   │
│  │  │                      Kong API Gateway                              │   │   │
│  │  │                                                                     │   │   │
│  │  │  Features:                                                          │   │   │
│  │  │  • Authentication & Authorization                                   │   │   │
│  │  │  • Rate Limiting & Throttling                                       │   │   │
│  │  │  • Request/Response Transformation                                  │   │   │
│  │  │  • Caching & Performance Optimization                              │   │   │
│  │  │  • API Analytics & Monitoring                                       │   │   │
│  │  │  • Load Balancing & Health Checks                                  │   │   │
│  │  │  • SSL Termination & Security Headers                             │   │   │
│  │  └─────────────────────────────────────────────────────────────────────┘   │   │
│  └─────────────────────────────────────────────────────────────────────────────┘   │
│                                      │                                              │
│                                      ▼                                              │
│  ┌─────────────────────────────────────────────────────────────────────────────┐   │
│  │                        Service API Layer                                   │   │
│  │                         (Missing Implementation)                           │   │
│  │                                                                             │   │
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐            │   │
│  │  │  BoardService   │  │  ItemService    │  │AutomationService│            │   │
│  │  │   API (18)      │  │   API (15)      │  │   API (20)      │            │   │
│  │  │                 │  │                 │  │                 │            │   │
│  │  │ • 18 endpoints  │  │ • 15 endpoints  │  │ • 20 endpoints  │            │   │
│  │  │ • 780 LOC       │  │ • 852 LOC       │  │ • 1,067 LOC     │            │   │
│  │  │ • Critical      │  │ • Critical      │  │ • Complex       │            │   │
│  │  │ • Tested        │  │ • Tested        │  │ • High Priority │            │   │
│  │  └─────────────────┘  └─────────────────┘  └─────────────────┘            │   │
│  │                                                                             │   │
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐            │   │
│  │  │   AIService     │  │ WorkspaceService│  │  FileService    │            │   │
│  │  │   API (12)      │  │   API (14)      │  │   API (16)      │            │   │
│  │  │                 │  │                 │  │                 │            │   │
│  │  │ • 12 endpoints  │  │ • 14 endpoints  │  │ • 16 endpoints  │            │   │
│  │  │ • 957 LOC       │  │ • 824 LOC       │  │ • 936 LOC       │            │   │
│  │  │ • AI Bridge     │  │ • Multi-tenant  │  │ • Upload/Process│            │   │
│  │  │ • Integration   │  │ • Permissions   │  │ • Security      │            │   │
│  │  └─────────────────┘  └─────────────────┘  └─────────────────┘            │   │
│  │                                                                             │   │
│  │  ┌─────────────────┐                                                       │   │
│  │  │AnalyticsService │   TOTAL API IMPLEMENTATION:                          │   │
│  │  │   API (10)      │   • 105 endpoints across 7 services                  │   │
│  │  │                 │   • 5,547+ lines of business logic                    │   │
│  │  │ • 10 endpoints  │   • 0% current implementation                         │   │
│  │  │ • 600 LOC       │   • 85%+ test coverage required                       │   │
│  │  │ • Reporting     │   • Real-time integration needed                      │   │
│  │  │ • Dashboards    │                                                       │   │
│  │  └─────────────────┘                                                       │   │
│  └─────────────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

### API Design Principles

```yaml
API Design Principles:
  Consistency:
    - RESTful resource naming conventions
    - Standardized response formats
    - Common error handling patterns
    - Uniform authentication/authorization

  Performance:
    - Sub-200ms response times (95th percentile)
    - Efficient pagination and filtering
    - Smart caching strategies
    - Optimized database queries

  Reliability:
    - Idempotent operations where appropriate
    - Graceful error handling and recovery
    - Circuit breaker patterns
    - Comprehensive input validation

  Security:
    - JWT-based authentication
    - Role-based authorization
    - Input sanitization and validation
    - Rate limiting and abuse prevention

  Testability:
    - Comprehensive test coverage (85%+)
    - Test doubles and mocking support
    - Integration test capabilities
    - Performance test compatibility

  Observability:
    - Structured logging
    - Performance metrics collection
    - Health check endpoints
    - Request tracing and correlation
```

---

## Core Service API Specifications

### BoardService API Implementation

```yaml
# BoardService API Specification (18 endpoints, 780 LOC)

/api/v1/boards:
  post:
    summary: Create new board
    operationId: createBoard
    tags: [Boards]
    security:
      - BearerAuth: []
    requestBody:
      required: true
      content:
        application/json:
          schema:
            type: object
            properties:
              workspaceId:
                type: string
                format: uuid
                description: "Workspace where board will be created"
              name:
                type: string
                minLength: 1
                maxLength: 255
                description: "Board name (unique within workspace)"
              description:
                type: string
                maxLength: 1000
                description: "Optional board description"
              templateId:
                type: string
                format: uuid
                description: "Optional template to create board from"
              isPrivate:
                type: boolean
                default: false
                description: "Whether board is private"
              settings:
                type: object
                description: "Board configuration settings"
                properties:
                  defaultView:
                    type: string
                    enum: [kanban, table, timeline, calendar]
                    default: kanban
                  allowComments:
                    type: boolean
                    default: true
                  allowFileAttachments:
                    type: boolean
                    default: true
            required: [workspaceId, name]
          examples:
            simple_board:
              summary: Simple board creation
              value:
                workspaceId: "550e8400-e29b-41d4-a716-446655440000"
                name: "Product Development"
                description: "Track product development tasks"
            template_board:
              summary: Board from template
              value:
                workspaceId: "550e8400-e29b-41d4-a716-446655440000"
                name: "Sprint Planning"
                templateId: "template-uuid"
                isPrivate: true
    responses:
      201:
        description: Board created successfully
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
      400:
        $ref: '#/components/responses/ValidationError'
      403:
        $ref: '#/components/responses/PermissionDenied'
      409:
        description: Board name conflicts
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/Error'
            example:
              error:
                type: "conflict"
                message: "Board with name 'Product Development' already exists in workspace"

/api/v1/boards/{boardId}:
  get:
    summary: Get board with items
    operationId: getBoard
    parameters:
      - name: boardId
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
            enum: [items, columns, members, activity, statistics]
        style: form
        explode: false
        description: "Additional data to include in response"
      - name: itemLimit
        in: query
        schema:
          type: integer
          minimum: 1
          maximum: 1000
          default: 100
        description: "Maximum number of items to return"
      - name: itemCursor
        in: query
        schema:
          type: string
        description: "Cursor for item pagination"
    responses:
      200:
        description: Board retrieved successfully
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
                      type: object
                      properties:
                        data:
                          type: array
                          items:
                            $ref: '#/components/schemas/Item'
                        pagination:
                          $ref: '#/components/schemas/Pagination'
                    members:
                      type: array
                      items:
                        $ref: '#/components/schemas/BoardMember'
                    statistics:
                      type: object
                      properties:
                        totalItems:
                          type: integer
                        completedItems:
                          type: integer
                        activeMembers:
                          type: integer

  put:
    summary: Update board
    operationId: updateBoard
    parameters:
      - name: boardId
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
            type: object
            properties:
              name:
                type: string
                minLength: 1
                maxLength: 255
              description:
                type: string
                maxLength: 1000
              settings:
                type: object
              isPrivate:
                type: boolean
    responses:
      200:
        description: Board updated successfully
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/Board'

  delete:
    summary: Delete board
    operationId: deleteBoard
    parameters:
      - name: boardId
        in: path
        required: true
        schema:
          type: string
          format: uuid
    responses:
      204:
        description: Board deleted successfully
      400:
        description: Board cannot be deleted (has dependencies)
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/Error'

/api/v1/boards/{boardId}/share:
  post:
    summary: Share board with users
    operationId: shareBoardWithUsers
    parameters:
      - name: boardId
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
            type: object
            properties:
              userIds:
                type: array
                items:
                  type: string
                  format: uuid
                minItems: 1
                maxItems: 50
              permissions:
                type: array
                items:
                  type: string
                  enum: [read, write, admin]
                default: [read]
              message:
                type: string
                maxLength: 500
                description: "Optional message for invitation"
            required: [userIds]
    responses:
      200:
        description: Board shared successfully
        content:
          application/json:
            schema:
              type: object
              properties:
                sharedWithCount:
                  type: integer
                failedUsers:
                  type: array
                  items:
                    type: object
                    properties:
                      userId:
                        type: string
                        format: uuid
                      error:
                        type: string

/api/v1/boards/{boardId}/duplicate:
  post:
    summary: Duplicate board
    operationId: duplicateBoard
    parameters:
      - name: boardId
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
            type: object
            properties:
              name:
                type: string
                minLength: 1
                maxLength: 255
              workspaceId:
                type: string
                format: uuid
                description: "Target workspace (defaults to same as source)"
              includeItems:
                type: boolean
                default: true
              includeMembers:
                type: boolean
                default: false
            required: [name]
    responses:
      201:
        description: Board duplicated successfully
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/Board'

/api/v1/boards/{boardId}/columns:
  get:
    summary: Get board columns
    operationId: getBoardColumns
    parameters:
      - name: boardId
        in: path
        required: true
        schema:
          type: string
          format: uuid
    responses:
      200:
        description: Columns retrieved successfully
        content:
          application/json:
            schema:
              type: object
              properties:
                data:
                  type: array
                  items:
                    $ref: '#/components/schemas/BoardColumn'

  post:
    summary: Add column to board
    operationId: addBoardColumn
    parameters:
      - name: boardId
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
            $ref: '#/components/schemas/CreateBoardColumn'
    responses:
      201:
        description: Column added successfully
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/BoardColumn'

  put:
    summary: Update board columns (bulk operation)
    operationId: updateBoardColumns
    parameters:
      - name: boardId
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
            type: object
            properties:
              columns:
                type: array
                items:
                  allOf:
                    - $ref: '#/components/schemas/BoardColumn'
                    - type: object
                      properties:
                        _action:
                          type: string
                          enum: [create, update, delete]
                          description: "Action to perform on column"
    responses:
      200:
        description: Columns updated successfully
        content:
          application/json:
            schema:
              type: object
              properties:
                data:
                  type: array
                  items:
                    $ref: '#/components/schemas/BoardColumn'
                changes:
                  type: object
                  properties:
                    created:
                      type: integer
                    updated:
                      type: integer
                    deleted:
                      type: integer
```

### ItemService API Implementation

```yaml
# ItemService API Specification (15 endpoints, 852 LOC)

/api/v1/boards/{boardId}/items:
  get:
    summary: List board items with filtering
    operationId: listBoardItems
    parameters:
      - name: boardId
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
            assigneeIds:
              type: array
              items:
                type: string
                format: uuid
            parentId:
              type: string
              format: uuid
            dueDateFrom:
              type: string
              format: date
            dueDateTo:
              type: string
              format: date
            priority:
              type: array
              items:
                type: string
                enum: [low, medium, high, critical]
            tags:
              type: array
              items:
                type: string
            search:
              type: string
              minLength: 2
        description: "Filtering criteria for items"
      - name: sort
        in: query
        schema:
          type: array
          items:
            type: string
            enum: [position, created_at, updated_at, due_date, priority, name]
        description: "Sort fields"
      - name: order
        in: query
        schema:
          type: string
          enum: [asc, desc]
          default: asc
      - name: limit
        in: query
        schema:
          type: integer
          minimum: 1
          maximum: 1000
          default: 50
      - name: cursor
        in: query
        schema:
          type: string
        description: "Pagination cursor"
      - name: include
        in: query
        schema:
          type: array
          items:
            type: string
            enum: [assignees, comments, attachments, dependencies, subtasks]
        description: "Additional data to include"
    responses:
      200:
        description: Items retrieved successfully
        headers:
          X-Total-Count:
            schema:
              type: integer
            description: "Total number of items matching filter"
        content:
          application/json:
            schema:
              type: object
              properties:
                data:
                  type: array
                  items:
                    $ref: '#/components/schemas/Item'
                pagination:
                  $ref: '#/components/schemas/Pagination'
                aggregations:
                  type: object
                  properties:
                    statusCounts:
                      type: object
                      additionalProperties:
                        type: integer
                    priorityCounts:
                      type: object
                      additionalProperties:
                        type: integer

  post:
    summary: Create new item
    operationId: createItem
    parameters:
      - name: boardId
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
            type: object
            properties:
              name:
                type: string
                minLength: 1
                maxLength: 500
              description:
                type: string
                maxLength: 10000
              parentId:
                type: string
                format: uuid
                description: "Parent item for hierarchical structure"
              position:
                type: number
                format: decimal
                description: "Position for ordering (calculated if not provided)"
              data:
                type: object
                description: "Custom field data"
              assigneeIds:
                type: array
                items:
                  type: string
                  format: uuid
                maxItems: 10
              dependencies:
                type: array
                items:
                  type: string
                  format: uuid
                description: "Items this item depends on"
              attachments:
                type: array
                items:
                  type: string
                  format: uuid
                description: "File attachment IDs"
              tags:
                type: array
                items:
                  type: string
                maxItems: 20
            required: [name]
          examples:
            simple_item:
              summary: Simple task
              value:
                name: "Implement user authentication"
                description: "Add JWT-based authentication system"
                data:
                  status: "To Do"
                  priority: "High"
                  estimated_hours: 8
            complex_item:
              summary: Complex item with dependencies
              value:
                name: "Deploy to production"
                description: "Production deployment with monitoring"
                parentId: "parent-item-uuid"
                assigneeIds: ["user1-uuid", "user2-uuid"]
                dependencies: ["dependency1-uuid", "dependency2-uuid"]
                data:
                  status: "Blocked"
                  priority: "Critical"
                  due_date: "2024-12-31"
                tags: ["deployment", "critical"]
    responses:
      201:
        description: Item created successfully
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/Item'
      400:
        description: Validation error
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/ValidationError'

/api/v1/items/{itemId}:
  get:
    summary: Get item details
    operationId: getItem
    parameters:
      - name: itemId
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
            enum: [comments, attachments, dependencies, subtasks, activity, time_entries]
    responses:
      200:
        description: Item retrieved successfully
        content:
          application/json:
            schema:
              allOf:
                - $ref: '#/components/schemas/Item'
                - type: object
                  properties:
                    comments:
                      type: array
                      items:
                        $ref: '#/components/schemas/Comment'
                    attachments:
                      type: array
                      items:
                        $ref: '#/components/schemas/FileAttachment'
                    dependencies:
                      type: array
                      items:
                        $ref: '#/components/schemas/ItemDependency'
                    subtasks:
                      type: array
                      items:
                        $ref: '#/components/schemas/Item'

  put:
    summary: Update item
    operationId: updateItem
    parameters:
      - name: itemId
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
            type: object
            properties:
              name:
                type: string
                minLength: 1
                maxLength: 500
              description:
                type: string
                maxLength: 10000
              data:
                type: object
                description: "Partial update of custom field data"
              assigneeIds:
                type: array
                items:
                  type: string
                  format: uuid
              tags:
                type: array
                items:
                  type: string
    responses:
      200:
        description: Item updated successfully
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/Item'

  delete:
    summary: Delete item
    operationId: deleteItem
    parameters:
      - name: itemId
        in: path
        required: true
        schema:
          type: string
          format: uuid
      - name: deleteSubtasks
        in: query
        schema:
          type: boolean
          default: false
        description: "Whether to delete subtasks (otherwise they'll be moved up)"
    responses:
      204:
        description: Item deleted successfully
      400:
        description: Cannot delete item with dependencies
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/Error'

/api/v1/items/bulk:
  put:
    summary: Bulk update items
    operationId: bulkUpdateItems
    requestBody:
      required: true
      content:
        application/json:
          schema:
            type: object
            properties:
              itemIds:
                type: array
                items:
                  type: string
                  format: uuid
                minItems: 1
                maxItems: 100
              updates:
                type: object
                description: "Updates to apply to all items"
                properties:
                  data:
                    type: object
                  assigneeIds:
                    type: array
                    items:
                      type: string
                      format: uuid
                  tags:
                    type: array
                    items:
                      type: string
              operation:
                type: string
                enum: [replace, merge]
                default: merge
                description: "How to apply updates (replace overwrites, merge combines)"
            required: [itemIds, updates]
    responses:
      200:
        description: Bulk update completed
        content:
          application/json:
            schema:
              type: object
              properties:
                updatedCount:
                  type: integer
                errors:
                  type: array
                  items:
                    type: object
                    properties:
                      itemId:
                        type: string
                        format: uuid
                      error:
                        type: string
                totalProcessed:
                  type: integer

  delete:
    summary: Bulk delete items
    operationId: bulkDeleteItems
    requestBody:
      required: true
      content:
        application/json:
          schema:
            type: object
            properties:
              itemIds:
                type: array
                items:
                  type: string
                  format: uuid
                minItems: 1
                maxItems: 100
              deleteSubtasks:
                type: boolean
                default: false
            required: [itemIds]
    responses:
      200:
        description: Bulk delete completed
        content:
          application/json:
            schema:
              type: object
              properties:
                deletedCount:
                  type: integer
                errors:
                  type: array
                  items:
                    type: object
                    properties:
                      itemId:
                        type: string
                        format: uuid
                      error:
                        type: string

/api/v1/items/{itemId}/move:
  put:
    summary: Move item to new position/parent
    operationId: moveItem
    parameters:
      - name: itemId
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
            type: object
            properties:
              position:
                type: number
                format: decimal
                description: "New position value"
              parentId:
                type: string
                format: uuid
                description: "New parent item ID (null for root level)"
              boardId:
                type: string
                format: uuid
                description: "Move to different board (same workspace only)"
            required: [position]
    responses:
      200:
        description: Item moved successfully
        content:
          application/json:
            schema:
              allOf:
                - $ref: '#/components/schemas/Item'
                - type: object
                  properties:
                    affectedItems:
                      type: array
                      items:
                        type: object
                        properties:
                          itemId:
                            type: string
                            format: uuid
                          oldPosition:
                            type: number
                          newPosition:
                            type: number

/api/v1/items/{itemId}/dependencies:
  get:
    summary: Get item dependencies
    operationId: getItemDependencies
    parameters:
      - name: itemId
        in: path
        required: true
        schema:
          type: string
          format: uuid
    responses:
      200:
        description: Dependencies retrieved successfully
        content:
          application/json:
            schema:
              type: object
              properties:
                predecessors:
                  type: array
                  items:
                    $ref: '#/components/schemas/ItemDependency'
                successors:
                  type: array
                  items:
                    $ref: '#/components/schemas/ItemDependency'

  post:
    summary: Create item dependency
    operationId: createItemDependency
    parameters:
      - name: itemId
        in: path
        required: true
        schema:
          type: string
          format: uuid
        description: "Successor item (depends on predecessor)"
    requestBody:
      required: true
      content:
        application/json:
          schema:
            type: object
            properties:
              predecessorId:
                type: string
                format: uuid
                description: "Item that this item depends on"
              dependencyType:
                type: string
                enum: [blocks, related]
                default: blocks
                description: "Type of dependency relationship"
            required: [predecessorId]
    responses:
      201:
        description: Dependency created successfully
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/ItemDependency'
      400:
        description: Would create circular dependency
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/Error'
            example:
              error:
                type: "validation_error"
                message: "Creating this dependency would result in a circular reference"
                details:
                  cycle: ["item1", "item2", "item3", "item1"]

/api/v1/items/{itemId}/comments:
  get:
    summary: Get item comments
    operationId: getItemComments
    parameters:
      - name: itemId
        in: path
        required: true
        schema:
          type: string
          format: uuid
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
        description: Comments retrieved successfully
        content:
          application/json:
            schema:
              type: object
              properties:
                data:
                  type: array
                  items:
                    $ref: '#/components/schemas/Comment'
                pagination:
                  $ref: '#/components/schemas/Pagination'

  post:
    summary: Add comment to item
    operationId: addItemComment
    parameters:
      - name: itemId
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
            type: object
            properties:
              content:
                type: string
                minLength: 1
                maxLength: 5000
              parentId:
                type: string
                format: uuid
                description: "Parent comment for replies"
              mentions:
                type: array
                items:
                  type: string
                  format: uuid
                description: "User IDs mentioned in comment"
            required: [content]
    responses:
      201:
        description: Comment added successfully
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/Comment'
```

### AutomationService API Implementation

```yaml
# AutomationService API Specification (20 endpoints, 1,067 LOC)

/api/v1/automations/rules:
  get:
    summary: List automation rules
    operationId: listAutomationRules
    parameters:
      - name: workspaceId
        in: query
        required: true
        schema:
          type: string
          format: uuid
      - name: boardId
        in: query
        schema:
          type: string
          format: uuid
        description: "Filter by specific board"
      - name: status
        in: query
        schema:
          type: string
          enum: [active, paused, disabled]
        description: "Filter by rule status"
      - name: triggerType
        in: query
        schema:
          type: string
          enum: [item_created, item_updated, status_changed, date_reached, user_assigned]
    responses:
      200:
        description: Rules retrieved successfully
        content:
          application/json:
            schema:
              type: object
              properties:
                data:
                  type: array
                  items:
                    $ref: '#/components/schemas/AutomationRule'
                pagination:
                  $ref: '#/components/schemas/Pagination'

  post:
    summary: Create automation rule
    operationId: createAutomationRule
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
              description:
                type: string
                maxLength: 1000
              workspaceId:
                type: string
                format: uuid
              boardId:
                type: string
                format: uuid
                description: "Optional: limit rule to specific board"
              trigger:
                $ref: '#/components/schemas/AutomationTrigger'
              conditions:
                type: array
                items:
                  $ref: '#/components/schemas/AutomationCondition'
              actions:
                type: array
                items:
                  $ref: '#/components/schemas/AutomationAction'
                minItems: 1
              settings:
                type: object
                properties:
                  priority:
                    type: integer
                    minimum: 0
                    maximum: 100
                    default: 50
                  stopExecution:
                    type: boolean
                    default: false
                    description: "Stop executing other rules after this one"
                  retryAttempts:
                    type: integer
                    minimum: 0
                    maximum: 5
                    default: 3
                  isActive:
                    type: boolean
                    default: true
            required: [name, workspaceId, trigger, actions]
          examples:
            status_automation:
              summary: Auto-assign when status changes
              value:
                name: "Auto-assign urgent tasks"
                description: "Automatically assign urgent tasks to team lead"
                workspaceId: "workspace-uuid"
                trigger:
                  type: "status_changed"
                  parameters:
                    from: "To Do"
                    to: "In Progress"
                conditions:
                  - type: "field_equals"
                    field: "priority"
                    value: "High"
                actions:
                  - type: "assign_user"
                    parameters:
                      userId: "team-lead-uuid"
                  - type: "send_notification"
                    parameters:
                      message: "Urgent task assigned to you"
            due_date_automation:
              summary: Reminder before due date
              value:
                name: "Due date reminder"
                description: "Send reminder 1 day before due date"
                workspaceId: "workspace-uuid"
                trigger:
                  type: "date_reached"
                  parameters:
                    field: "due_date"
                    offset: "-1 day"
                actions:
                  - type: "send_notification"
                    parameters:
                      template: "due_date_reminder"
                      recipients: "assignees"
    responses:
      201:
        description: Rule created successfully
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/AutomationRule'
      400:
        description: Invalid rule configuration
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/ValidationError'

/api/v1/automations/rules/{ruleId}:
  get:
    summary: Get automation rule
    operationId: getAutomationRule
    parameters:
      - name: ruleId
        in: path
        required: true
        schema:
          type: string
          format: uuid
    responses:
      200:
        description: Rule retrieved successfully
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/AutomationRule'

  put:
    summary: Update automation rule
    operationId: updateAutomationRule
    parameters:
      - name: ruleId
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
            type: object
            properties:
              name:
                type: string
                minLength: 1
                maxLength: 255
              description:
                type: string
                maxLength: 1000
              trigger:
                $ref: '#/components/schemas/AutomationTrigger'
              conditions:
                type: array
                items:
                  $ref: '#/components/schemas/AutomationCondition'
              actions:
                type: array
                items:
                  $ref: '#/components/schemas/AutomationAction'
              settings:
                type: object
    responses:
      200:
        description: Rule updated successfully
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/AutomationRule'

  delete:
    summary: Delete automation rule
    operationId: deleteAutomationRule
    parameters:
      - name: ruleId
        in: path
        required: true
        schema:
          type: string
          format: uuid
    responses:
      204:
        description: Rule deleted successfully

/api/v1/automations/rules/{ruleId}/execute:
  post:
    summary: Manually execute automation rule
    operationId: executeAutomationRule
    parameters:
      - name: ruleId
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
            type: object
            properties:
              triggerData:
                type: object
                description: "Simulated trigger data for testing"
              dryRun:
                type: boolean
                default: false
                description: "Test execution without performing actions"
            required: [triggerData]
    responses:
      200:
        description: Rule executed successfully
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/AutomationExecutionResult'

/api/v1/automations/rules/{ruleId}/test:
  post:
    summary: Test automation rule
    operationId: testAutomationRule
    parameters:
      - name: ruleId
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
            type: object
            properties:
              testData:
                type: object
                description: "Test data to validate rule against"
            required: [testData]
    responses:
      200:
        description: Test completed successfully
        content:
          application/json:
            schema:
              type: object
              properties:
                conditionResults:
                  type: array
                  items:
                    type: object
                    properties:
                      conditionIndex:
                        type: integer
                      result:
                        type: boolean
                      details:
                        type: string
                wouldExecute:
                  type: boolean
                estimatedActions:
                  type: array
                  items:
                    type: object
                    properties:
                      actionType:
                        type: string
                      parameters:
                        type: object
                      estimatedResult:
                        type: string

/api/v1/automations/executions:
  get:
    summary: Get automation execution history
    operationId: getAutomationExecutions
    parameters:
      - name: ruleId
        in: query
        schema:
          type: string
          format: uuid
      - name: workspaceId
        in: query
        schema:
          type: string
          format: uuid
      - name: status
        in: query
        schema:
          type: string
          enum: [success, partial_success, failed]
      - name: fromDate
        in: query
        schema:
          type: string
          format: date-time
      - name: toDate
        in: query
        schema:
          type: string
          format: date-time
      - name: limit
        in: query
        schema:
          type: integer
          minimum: 1
          maximum: 100
          default: 50
    responses:
      200:
        description: Execution history retrieved successfully
        content:
          application/json:
            schema:
              type: object
              properties:
                data:
                  type: array
                  items:
                    $ref: '#/components/schemas/AutomationExecution'
                pagination:
                  $ref: '#/components/schemas/Pagination'
                aggregations:
                  type: object
                  properties:
                    totalExecutions:
                      type: integer
                    successRate:
                      type: number
                      format: float
                    averageExecutionTime:
                      type: number
                      format: float

/api/v1/automations/triggers:
  get:
    summary: Get available trigger types
    operationId: getAvailableTriggers
    responses:
      200:
        description: Available triggers retrieved successfully
        content:
          application/json:
            schema:
              type: object
              properties:
                data:
                  type: array
                  items:
                    $ref: '#/components/schemas/TriggerDefinition'

/api/v1/automations/actions:
  get:
    summary: Get available action types
    operationId: getAvailableActions
    responses:
      200:
        description: Available actions retrieved successfully
        content:
          application/json:
            schema:
              type: object
              properties:
                data:
                  type: array
                  items:
                    $ref: '#/components/schemas/ActionDefinition'

/api/v1/automations/rules/{ruleId}/pause:
  post:
    summary: Pause automation rule
    operationId: pauseAutomationRule
    parameters:
      - name: ruleId
        in: path
        required: true
        schema:
          type: string
          format: uuid
    responses:
      200:
        description: Rule paused successfully
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/AutomationRule'

/api/v1/automations/rules/{ruleId}/resume:
  post:
    summary: Resume automation rule
    operationId: resumeAutomationRule
    parameters:
      - name: ruleId
        in: path
        required: true
        schema:
          type: string
          format: uuid
    responses:
      200:
        description: Rule resumed successfully
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/AutomationRule'
```

---

## Real-time Collaboration APIs

### WebSocket API Specifications

```typescript
// WebSocket API Event Specifications

interface WebSocketAPI {
  // Connection Management
  'connection.authenticate': {
    request: {
      token: string;
      clientInfo?: {
        userAgent: string;
        deviceType: 'desktop' | 'mobile' | 'tablet';
        capabilities: string[];
      };
    };
    response: {
      success: boolean;
      userId: string;
      connectionId: string;
      serverCapabilities: string[];
    };
  };

  'connection.heartbeat': {
    request: {
      timestamp: number;
    };
    response: {
      timestamp: number;
      serverTime: number;
    };
  };

  // Room/Channel Management
  'room.join': {
    request: {
      roomType: 'board' | 'workspace' | 'organization';
      roomId: string;
      options?: {
        trackPresence?: boolean;
        trackCursor?: boolean;
        receiveUpdates?: boolean;
      };
    };
    response: {
      success: boolean;
      roomId: string;
      memberCount: number;
      currentMembers?: Array<{
        userId: string;
        joinedAt: number;
        presence?: PresenceData;
      }>;
    };
  };

  'room.leave': {
    request: {
      roomId: string;
    };
    response: {
      success: boolean;
    };
  };

  // Real-time Item Updates
  'item.update': {
    request: {
      itemId: string;
      updates: Record<string, any>;
      optimisticId?: string;
      clientTimestamp: number;
    };
    response: {
      success: boolean;
      itemId: string;
      optimisticId?: string;
      item?: Item;
      conflicts?: Conflict[];
      serverTimestamp: number;
    };
  };

  'item.updated': {
    broadcast: {
      itemId: string;
      item: Item;
      changes: Record<string, any>;
      updatedBy: string;
      timestamp: number;
      affectedUsers?: string[];
    };
  };

  'item.move': {
    request: {
      itemId: string;
      position: number;
      parentId?: string;
      boardId?: string;
      optimisticId?: string;
    };
    response: {
      success: boolean;
      itemId: string;
      optimisticId?: string;
      newPosition: number;
      affectedItems?: Array<{
        itemId: string;
        oldPosition: number;
        newPosition: number;
      }>;
    };
  };

  // Presence Management
  'presence.update': {
    request: {
      roomId: string;
      presence: {
        status: 'active' | 'idle' | 'away';
        activity?: {
          type: 'viewing' | 'editing' | 'commenting';
          target?: string;
        };
        metadata?: Record<string, any>;
      };
    };
    response: {
      success: boolean;
    };
  };

  'presence.changed': {
    broadcast: {
      roomId: string;
      userId: string;
      presence: PresenceData;
      timestamp: number;
    };
  };

  // Cursor Tracking
  'cursor.move': {
    request: {
      roomId: string;
      position: {
        x: number;
        y: number;
        target?: string;
        selection?: {
          start: number;
          end: number;
        };
      };
    };
    response: {
      // No response needed for cursor moves (fire and forget)
    };
  };

  'cursor.moved': {
    broadcast: {
      roomId: string;
      userId: string;
      position: CursorPosition;
      timestamp: number;
    };
  };

  // Collaboration Features
  'collaboration.lock': {
    request: {
      resourceType: 'item' | 'board' | 'field';
      resourceId: string;
      lockType: 'edit' | 'exclusive';
      timeout?: number; // milliseconds
    };
    response: {
      success: boolean;
      lockId?: string;
      lockedBy?: string;
      expiresAt?: number;
    };
  };

  'collaboration.unlock': {
    request: {
      lockId: string;
    };
    response: {
      success: boolean;
    };
  };

  'collaboration.conflict': {
    broadcast: {
      itemId: string;
      conflicts: Conflict[];
      involvedUsers: string[];
      timestamp: number;
    };
  };

  // Error Handling
  'error': {
    broadcast: {
      type: 'authentication' | 'permission' | 'validation' | 'rate_limit' | 'internal';
      message: string;
      code?: string;
      details?: Record<string, any>;
      timestamp: number;
    };
  };
}

// WebSocket Client Implementation Pattern
class SundayWebSocketClient {
  private ws: WebSocket;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectDelay = 1000;

  constructor(private config: {
    url: string;
    token: string;
    onConnect?: () => void;
    onDisconnect?: () => void;
    onError?: (error: Error) => void;
  }) {}

  async connect(): Promise<void> {
    return new Promise((resolve, reject) => {
      this.ws = new WebSocket(this.config.url);

      this.ws.onopen = () => {
        this.authenticate().then(() => {
          this.reconnectAttempts = 0;
          this.config.onConnect?.();
          resolve();
        }).catch(reject);
      };

      this.ws.onmessage = (event) => {
        this.handleMessage(JSON.parse(event.data));
      };

      this.ws.onclose = () => {
        this.handleDisconnection();
      };

      this.ws.onerror = (error) => {
        this.config.onError?.(new Error('WebSocket error'));
        reject(error);
      };
    });
  }

  private async authenticate(): Promise<void> {
    return this.send('connection.authenticate', {
      token: this.config.token,
      clientInfo: {
        userAgent: navigator.userAgent,
        deviceType: this.detectDeviceType(),
        capabilities: ['presence', 'cursor', 'collaboration']
      }
    });
  }

  private handleDisconnection(): void {
    this.config.onDisconnect?.();

    if (this.reconnectAttempts < this.maxReconnectAttempts) {
      setTimeout(() => {
        this.reconnectAttempts++;
        this.connect().catch(() => {
          // Will retry on next timeout
        });
      }, this.reconnectDelay * Math.pow(2, this.reconnectAttempts));
    }
  }

  async send<T extends keyof WebSocketAPI>(
    event: T,
    data: WebSocketAPI[T]['request']
  ): Promise<WebSocketAPI[T]['response']> {
    return new Promise((resolve, reject) => {
      const messageId = generateMessageId();
      const message = {
        id: messageId,
        event,
        data,
        timestamp: Date.now()
      };

      // Set up response handler
      const timeout = setTimeout(() => {
        this.removeResponseHandler(messageId);
        reject(new Error('WebSocket request timeout'));
      }, 10000); // 10 second timeout

      this.responseHandlers.set(messageId, (response) => {
        clearTimeout(timeout);
        if (response.error) {
          reject(new Error(response.error));
        } else {
          resolve(response.data);
        }
      });

      this.ws.send(JSON.stringify(message));
    });
  }

  // High-level collaboration methods
  async joinBoard(boardId: string): Promise<void> {
    await this.send('room.join', {
      roomType: 'board',
      roomId: boardId,
      options: {
        trackPresence: true,
        trackCursor: true,
        receiveUpdates: true
      }
    });
  }

  async updateItem(
    itemId: string,
    updates: Record<string, any>
  ): Promise<{ success: boolean; conflicts?: Conflict[] }> {
    const optimisticId = generateOptimisticId();

    try {
      const result = await this.send('item.update', {
        itemId,
        updates,
        optimisticId,
        clientTimestamp: Date.now()
      });

      return {
        success: result.success,
        conflicts: result.conflicts
      };
    } catch (error) {
      return { success: false };
    }
  }

  updatePresence(roomId: string, activity: string): void {
    // Fire and forget for presence updates
    this.send('presence.update', {
      roomId,
      presence: {
        status: 'active',
        activity: {
          type: 'editing',
          target: activity
        }
      }
    }).catch(() => {
      // Ignore presence update failures
    });
  }

  moveCursor(roomId: string, x: number, y: number, target?: string): void {
    // Throttled cursor updates
    if (this.shouldThrottleCursor()) return;

    this.send('cursor.move', {
      roomId,
      position: { x, y, target }
    }).catch(() => {
      // Ignore cursor move failures
    });
  }
}
```

---

## AI Integration API Design

### AI Service API Specifications

```yaml
# AI Integration API Specification (12 endpoints, 957 LOC bridge)

/api/v1/ai/suggestions/tasks:
  post:
    summary: Get AI task suggestions
    operationId: getTaskSuggestions
    tags: [AI]
    security:
      - BearerAuth: []
    requestBody:
      required: true
      content:
        application/json:
          schema:
            type: object
            properties:
              context:
                type: string
                minLength: 10
                maxLength: 2000
                description: "Description of what needs to be accomplished"
              boardId:
                type: string
                format: uuid
                description: "Board context for suggestions"
              boardType:
                type: string
                enum: [project, kanban, scrum, marketing, engineering]
                description: "Type of board for context"
              teamSize:
                type: integer
                minimum: 1
                maximum: 100
                description: "Team size for workload consideration"
              preferences:
                type: object
                properties:
                  complexity:
                    type: string
                    enum: [simple, moderate, complex]
                    default: moderate
                  timeframe:
                    type: string
                    enum: [urgent, short_term, medium_term, long_term]
                  skillLevel:
                    type: string
                    enum: [beginner, intermediate, advanced]
            required: [context, boardId]
          examples:
            product_feature:
              summary: Product feature development
              value:
                context: "We need to implement a user dashboard with analytics and reporting capabilities for our SaaS platform"
                boardId: "board-uuid"
                boardType: "engineering"
                teamSize: 5
                preferences:
                  complexity: "complex"
                  timeframe: "medium_term"
                  skillLevel: "advanced"
            marketing_campaign:
              summary: Marketing campaign planning
              value:
                context: "Launch a social media campaign for our new product release targeting millennials"
                boardId: "board-uuid"
                boardType: "marketing"
                teamSize: 3
                preferences:
                  complexity: "moderate"
                  timeframe: "short_term"
    responses:
      200:
        description: Task suggestions generated successfully
        content:
          application/json:
            schema:
              type: object
              properties:
                suggestions:
                  type: array
                  items:
                    type: object
                    properties:
                      title:
                        type: string
                        description: "Suggested task title"
                      description:
                        type: string
                        description: "Detailed task description"
                      suggestedFields:
                        type: object
                        properties:
                          priority:
                            type: string
                            enum: [Low, Medium, High, Critical]
                          estimatedHours:
                            type: number
                            minimum: 0.5
                            maximum: 120
                          tags:
                            type: array
                            items:
                              type: string
                          dueDate:
                            type: string
                            format: date
                          complexity:
                            type: string
                            enum: [Simple, Moderate, Complex]
                      confidence:
                        type: number
                        format: float
                        minimum: 0
                        maximum: 1
                        description: "AI confidence score for suggestion"
                      reasoning:
                        type: array
                        items:
                          type: string
                        description: "Why this task was suggested"
                      dependencies:
                        type: array
                        items:
                          type: string
                        description: "Suggested prerequisite tasks"
                metadata:
                  type: object
                  properties:
                    processingTime:
                      type: number
                      description: "Time taken to generate suggestions (ms)"
                    modelVersion:
                      type: string
                    contextAnalysis:
                      type: object
                      properties:
                        complexity:
                          type: string
                        domain:
                          type: string
                        estimatedEffort:
                          type: string
      400:
        description: Invalid request parameters
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/ValidationError'
      429:
        description: Rate limit exceeded
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/Error'
            example:
              error:
                type: "rate_limit_exceeded"
                message: "AI API rate limit exceeded. Try again in 60 seconds."
                retryAfter: 60

/api/v1/ai/auto-complete:
  post:
    summary: Get auto-complete suggestions
    operationId: getAutoCompleteSuggestions
    requestBody:
      required: true
      content:
        application/json:
          schema:
            type: object
            properties:
              type:
                type: string
                enum: [item_name, description, comment]
                description: "Type of content to auto-complete"
              partialText:
                type: string
                minLength: 2
                maxLength: 500
                description: "Partial text to complete"
              context:
                type: object
                properties:
                  boardId:
                    type: string
                    format: uuid
                  itemId:
                    type: string
                    format: uuid
                  fieldType:
                    type: string
                  relatedItems:
                    type: array
                    items:
                      type: string
                      format: uuid
              maxSuggestions:
                type: integer
                minimum: 1
                maximum: 10
                default: 5
            required: [type, partialText]
    responses:
      200:
        description: Auto-complete suggestions generated
        content:
          application/json:
            schema:
              type: object
              properties:
                suggestions:
                  type: array
                  items:
                    type: object
                    properties:
                      text:
                        type: string
                        description: "Suggested completion"
                      confidence:
                        type: number
                        format: float
                      type:
                        type: string
                        enum: [exact_match, contextual, creative]
                      metadata:
                        type: object

/api/v1/ai/smart-assign:
  post:
    summary: Get smart assignment suggestions
    operationId: getSmartAssignmentSuggestions
    requestBody:
      required: true
      content:
        application/json:
          schema:
            type: object
            properties:
              itemId:
                type: string
                format: uuid
                description: "Item to assign"
              itemDescription:
                type: string
                description: "Item description for analysis"
              requiredSkills:
                type: array
                items:
                  type: string
                description: "Required skills for the task"
              workloadConsideration:
                type: boolean
                default: true
                description: "Consider current workload in assignment"
              availabilityCheck:
                type: boolean
                default: true
                description: "Check user availability"
              teamOnly:
                type: boolean
                default: false
                description: "Only consider current board/workspace members"
            required: [itemId]
    responses:
      200:
        description: Smart assignment suggestions generated
        content:
          application/json:
            schema:
              type: object
              properties:
                recommendations:
                  type: array
                  items:
                    type: object
                    properties:
                      userId:
                        type: string
                        format: uuid
                      user:
                        $ref: '#/components/schemas/User'
                      confidence:
                        type: number
                        format: float
                        description: "Confidence score (0-1)"
                      reasoning:
                        type: array
                        items:
                          type: string
                        description: "Reasons for recommendation"
                      workloadImpact:
                        type: object
                        properties:
                          currentTasks:
                            type: integer
                          estimatedHours:
                            type: number
                          capacityUtilization:
                            type: number
                            format: float
                      skillMatch:
                        type: object
                        properties:
                          matchedSkills:
                            type: array
                            items:
                              type: string
                          skillLevel:
                            type: string
                            enum: [beginner, intermediate, expert]
                          relevantExperience:
                            type: array
                            items:
                              type: string
                      availability:
                        type: object
                        properties:
                          status:
                            type: string
                            enum: [available, busy, out_of_office]
                          nextAvailable:
                            type: string
                            format: date-time
                alternativeOptions:
                  type: object
                  properties:
                    reassignExisting:
                      type: array
                      items:
                        type: object
                        properties:
                          fromUserId:
                            type: string
                            format: uuid
                          toUserId:
                            type: string
                            format: uuid
                          itemId:
                            type: string
                            format: uuid
                          reason:
                            type: string
                    delayRecommendation:
                      type: object
                      properties:
                        suggestedDelay:
                          type: string
                        reason:
                          type: string

/api/v1/ai/analyze/workload:
  post:
    summary: Analyze workload and productivity
    operationId: analyzeWorkload
    requestBody:
      required: true
      content:
        application/json:
          schema:
            type: object
            properties:
              workspaceId:
                type: string
                format: uuid
              timeRange:
                type: object
                properties:
                  start:
                    type: string
                    format: date
                  end:
                    type: string
                    format: date
                required: [start, end]
              includeTeamMembers:
                type: boolean
                default: true
              metrics:
                type: array
                items:
                  type: string
                  enum: [productivity, burnout_risk, task_distribution, completion_rate, collaboration_score]
                default: [productivity, task_distribution, completion_rate]
            required: [workspaceId, timeRange]
    responses:
      200:
        description: Workload analysis completed
        content:
          application/json:
            schema:
              type: object
              properties:
                summary:
                  type: object
                  properties:
                    totalTasks:
                      type: integer
                    completedTasks:
                      type: integer
                    averageCompletionTime:
                      type: number
                      description: "Average completion time in hours"
                    productivityScore:
                      type: number
                      format: float
                      description: "Overall productivity score (0-100)"
                    teamUtilization:
                      type: number
                      format: float
                      description: "Team capacity utilization (0-1)"
                teamAnalysis:
                  type: array
                  items:
                    type: object
                    properties:
                      userId:
                        type: string
                        format: uuid
                      user:
                        $ref: '#/components/schemas/User'
                      metrics:
                        type: object
                        properties:
                          tasksCompleted:
                            type: integer
                          averageCompletionTime:
                            type: number
                          productivityScore:
                            type: number
                            format: float
                          burnoutRisk:
                            type: string
                            enum: [low, medium, high]
                          collaborationScore:
                            type: number
                            format: float
                          workloadBalance:
                            type: string
                            enum: [underutilized, optimal, overloaded]
                insights:
                  type: array
                  items:
                    type: object
                    properties:
                      type:
                        type: string
                        enum: [optimization, warning, recommendation]
                      title:
                        type: string
                      description:
                        type: string
                      actionable:
                        type: boolean
                      suggestedActions:
                        type: array
                        items:
                          type: string
                recommendations:
                  type: array
                  items:
                    type: object
                    properties:
                      type:
                        type: string
                        enum: [redistribute_tasks, schedule_break, increase_capacity, improve_process]
                      description:
                        type: string
                      priority:
                        type: string
                        enum: [low, medium, high]
                      impact:
                        type: string
                        enum: [low, medium, high]
                      effort:
                        type: string
                        enum: [low, medium, high]

/api/v1/ai/optimize/board:
  post:
    summary: Get board optimization suggestions
    operationId: optimizeBoard
    requestBody:
      required: true
      content:
        application/json:
          schema:
            type: object
            properties:
              boardId:
                type: string
                format: uuid
              analysisType:
                type: array
                items:
                  type: string
                  enum: [structure, workflow, performance, collaboration]
                default: [structure, workflow, performance]
              includeReorganization:
                type: boolean
                default: true
              includeAutomation:
                type: boolean
                default: true
            required: [boardId]
    responses:
      200:
        description: Board optimization suggestions generated
        content:
          application/json:
            schema:
              type: object
              properties:
                currentAnalysis:
                  type: object
                  properties:
                    structure:
                      type: object
                      properties:
                        columnCount:
                          type: integer
                        itemCount:
                          type: integer
                        depth:
                          type: integer
                        organizationScore:
                          type: number
                          format: float
                    workflow:
                      type: object
                      properties:
                        bottlenecks:
                          type: array
                          items:
                            type: object
                            properties:
                              location:
                                type: string
                              severity:
                                type: string
                                enum: [low, medium, high]
                              description:
                                type: string
                        flowEfficiency:
                          type: number
                          format: float
                optimizations:
                  type: array
                  items:
                    type: object
                    properties:
                      type:
                        type: string
                        enum: [restructure, automation, workflow, naming]
                      title:
                        type: string
                      description:
                        type: string
                      impact:
                        type: string
                        enum: [low, medium, high]
                      effort:
                        type: string
                        enum: [low, medium, high]
                      priority:
                        type: integer
                        minimum: 1
                        maximum: 5
                      implementation:
                        type: object
                        properties:
                          steps:
                            type: array
                            items:
                              type: string
                          estimatedTime:
                            type: string
                          risks:
                            type: array
                            items:
                              type: string
                suggestedAutomations:
                  type: array
                  items:
                    type: object
                    properties:
                      name:
                        type: string
                      description:
                        type: string
                      trigger:
                        type: string
                      actions:
                        type: array
                        items:
                          type: string
                      estimatedTimeSaving:
                        type: string
                      confidence:
                        type: number
                        format: float
```

---

## Implementation Guidelines

### API Implementation Checklist

<function_calls>
<invoke name="TodoWrite">
<parameter name="todos">[{"content": "Create comprehensive architecture design document", "status": "completed", "activeForm": "Creating comprehensive architecture design document"}, {"content": "Design technology stack with testing infrastructure focus", "status": "completed", "activeForm": "Designing technology stack with testing infrastructure focus"}, {"content": "Create detailed component architecture diagram", "status": "completed", "activeForm": "Creating detailed component architecture diagram"}, {"content": "Define integration patterns for real-time collaboration", "status": "completed", "activeForm": "Defining integration patterns for real-time collaboration"}, {"content": "Specify API architecture for missing services", "status": "completed", "activeForm": "Specifying API architecture for missing services"}]