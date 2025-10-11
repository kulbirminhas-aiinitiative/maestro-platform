# Sunday.com - Database Design & Schema

## Executive Summary

This document provides a comprehensive database design for Sunday.com, implementing a polyglot persistence strategy with PostgreSQL as the primary OLTP database, Redis for caching and real-time features, ClickHouse for analytics, and Elasticsearch for search capabilities. The design supports multi-tenancy, scalability, and enterprise-grade performance requirements.

## Table of Contents

1. [Database Architecture Overview](#database-architecture-overview)
2. [Primary Database Schema (PostgreSQL)](#primary-database-schema-postgresql)
3. [Caching Layer (Redis)](#caching-layer-redis)
4. [Analytics Database (ClickHouse)](#analytics-database-clickhouse)
5. [Search Engine (Elasticsearch)](#search-engine-elasticsearch)
6. [Data Relationships & Constraints](#data-relationships--constraints)
7. [Indexing Strategy](#indexing-strategy)
8. [Partitioning & Sharding](#partitioning--sharding)
9. [Data Migration Strategy](#data-migration-strategy)
10. [Performance Optimization](#performance-optimization)

---

## Database Architecture Overview

### Polyglot Persistence Strategy

```
┌─────────────────────────────────────────────────────────────────┐
│                    Database Architecture                       │
├─────────────────────────────────────────────────────────────────┤
│  Application Layer                                             │
│  ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐  │
│  │   Write Path    │ │   Read Path     │ │   Search Path   │  │
│  │   (Commands)    │ │   (Queries)     │ │   (Full-text)   │  │
│  └─────────────────┘ └─────────────────┘ └─────────────────┘  │
│       ↓                      ↓                      ↓         │
│  ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐  │
│  │   PostgreSQL    │ │     Redis       │ │ Elasticsearch   │  │
│  │   (Primary)     │ │   (Cache)       │ │   (Search)      │  │
│  └─────────────────┘ └─────────────────┘ └─────────────────┘  │
│       ↓                                                       │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │                Event Stream (Kafka)                        │ │
│  └─────────────────────────────────────────────────────────────┘ │
│       ↓                                                       │
│  ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐  │
│  │   ClickHouse    │ │     MongoDB     │ │   Vector DB     │  │
│  │  (Analytics)    │ │   (Flexible)    │ │     (AI)        │  │
│  └─────────────────┘ └─────────────────┘ └─────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

### Database Responsibilities

| Database | Purpose | Data Types | Access Pattern |
|----------|---------|------------|----------------|
| **PostgreSQL** | Primary OLTP | Core business data | CRUD operations |
| **Redis** | Cache & Real-time | Session, cache, pub/sub | High-frequency reads |
| **ClickHouse** | Analytics OLAP | Events, metrics, logs | Aggregation queries |
| **Elasticsearch** | Search | Full-text, faceted search | Text search queries |
| **MongoDB** | Flexible schema | Custom fields, configs | Document queries |
| **S3** | Object storage | Files, attachments | Binary data |

---

## Primary Database Schema (PostgreSQL)

### Core Tables

#### Organizations & Workspaces

```sql
-- Organizations table
CREATE TABLE organizations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(100) UNIQUE NOT NULL,
    domain VARCHAR(255),
    settings JSONB DEFAULT '{}',
    subscription_plan VARCHAR(50) DEFAULT 'free',
    subscription_status VARCHAR(20) DEFAULT 'active',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);

-- Workspaces table
CREATE TABLE workspaces (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    color VARCHAR(7) DEFAULT '#6B7280',
    settings JSONB DEFAULT '{}',
    is_private BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    deleted_at TIMESTAMPTZ,
    CONSTRAINT workspaces_organization_name_unique
        UNIQUE (organization_id, name) WHERE deleted_at IS NULL
);
```

#### Users & Authentication

```sql
-- Users table
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(320) UNIQUE NOT NULL,
    email_verified BOOLEAN DEFAULT FALSE,
    password_hash VARCHAR(255), -- NULL for SSO users
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    avatar_url TEXT,
    timezone VARCHAR(50) DEFAULT 'UTC',
    locale VARCHAR(10) DEFAULT 'en',
    settings JSONB DEFAULT '{}',
    last_login_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);

-- Organization memberships
CREATE TABLE organization_members (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role VARCHAR(50) NOT NULL DEFAULT 'member',
    status VARCHAR(20) DEFAULT 'active', -- active, invited, suspended
    invited_by UUID REFERENCES users(id),
    invited_at TIMESTAMPTZ,
    joined_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (organization_id, user_id)
);

-- Workspace memberships
CREATE TABLE workspace_members (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role VARCHAR(50) NOT NULL DEFAULT 'member',
    permissions JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (workspace_id, user_id)
);
```

#### Boards & Projects

```sql
-- Boards table
CREATE TABLE boards (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    template_id UUID REFERENCES board_templates(id),
    settings JSONB DEFAULT '{}',
    view_settings JSONB DEFAULT '{}',
    is_private BOOLEAN DEFAULT FALSE,
    folder_id UUID REFERENCES folders(id),
    position INTEGER,
    created_by UUID NOT NULL REFERENCES users(id),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);

-- Board columns (custom fields)
CREATE TABLE board_columns (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    board_id UUID NOT NULL REFERENCES boards(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    column_type VARCHAR(50) NOT NULL, -- text, number, status, date, people, etc.
    settings JSONB DEFAULT '{}',
    validation_rules JSONB DEFAULT '{}',
    position INTEGER NOT NULL,
    is_required BOOLEAN DEFAULT FALSE,
    is_visible BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (board_id, position)
);

-- Board templates
CREATE TABLE board_templates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    category VARCHAR(100),
    template_data JSONB NOT NULL,
    is_public BOOLEAN DEFAULT FALSE,
    created_by UUID REFERENCES users(id),
    organization_id UUID REFERENCES organizations(id),
    usage_count INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

#### Items & Tasks

```sql
-- Items (tasks/work items)
CREATE TABLE items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    board_id UUID NOT NULL REFERENCES boards(id) ON DELETE CASCADE,
    parent_id UUID REFERENCES items(id), -- for subtasks
    name VARCHAR(500) NOT NULL,
    description TEXT,
    item_data JSONB DEFAULT '{}', -- dynamic column values
    position DECIMAL(10,5), -- for ordering
    created_by UUID NOT NULL REFERENCES users(id),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);

-- Item assignments
CREATE TABLE item_assignments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    item_id UUID NOT NULL REFERENCES items(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    assigned_by UUID NOT NULL REFERENCES users(id),
    assigned_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (item_id, user_id)
);

-- Item dependencies
CREATE TABLE item_dependencies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    predecessor_id UUID NOT NULL REFERENCES items(id) ON DELETE CASCADE,
    successor_id UUID NOT NULL REFERENCES items(id) ON DELETE CASCADE,
    dependency_type VARCHAR(20) DEFAULT 'blocks', -- blocks, related
    created_by UUID NOT NULL REFERENCES users(id),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (predecessor_id, successor_id),
    CONSTRAINT no_self_dependency CHECK (predecessor_id != successor_id)
);

-- Item time tracking
CREATE TABLE time_entries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    item_id UUID NOT NULL REFERENCES items(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    description TEXT,
    start_time TIMESTAMPTZ NOT NULL,
    end_time TIMESTAMPTZ,
    duration_seconds INTEGER,
    is_billable BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

#### Comments & Collaboration

```sql
-- Comments
CREATE TABLE comments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    item_id UUID NOT NULL REFERENCES items(id) ON DELETE CASCADE,
    parent_id UUID REFERENCES comments(id), -- for threaded comments
    user_id UUID NOT NULL REFERENCES users(id),
    content TEXT NOT NULL,
    content_type VARCHAR(20) DEFAULT 'text', -- text, markdown
    mentions JSONB DEFAULT '[]', -- array of mentioned user IDs
    attachments JSONB DEFAULT '[]',
    is_edited BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);

-- Activity log
CREATE TABLE activity_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id),
    workspace_id UUID REFERENCES workspaces(id),
    board_id UUID REFERENCES boards(id),
    item_id UUID REFERENCES items(id),
    user_id UUID NOT NULL REFERENCES users(id),
    action VARCHAR(100) NOT NULL,
    entity_type VARCHAR(50) NOT NULL,
    entity_id UUID NOT NULL,
    old_values JSONB,
    new_values JSONB,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
) PARTITION BY RANGE (created_at);

-- Activity log partitions (monthly)
CREATE TABLE activity_log_y2024m12 PARTITION OF activity_log
    FOR VALUES FROM ('2024-12-01') TO ('2025-01-01');
```

#### Automation & Workflows

```sql
-- Automation rules
CREATE TABLE automation_rules (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    board_id UUID REFERENCES boards(id) ON DELETE CASCADE,
    workspace_id UUID REFERENCES workspaces(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    trigger_config JSONB NOT NULL,
    condition_config JSONB DEFAULT '{}',
    action_config JSONB NOT NULL,
    is_enabled BOOLEAN DEFAULT TRUE,
    execution_count INTEGER DEFAULT 0,
    last_executed_at TIMESTAMPTZ,
    created_by UUID NOT NULL REFERENCES users(id),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Automation execution log
CREATE TABLE automation_executions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    rule_id UUID NOT NULL REFERENCES automation_rules(id) ON DELETE CASCADE,
    item_id UUID REFERENCES items(id),
    trigger_data JSONB,
    execution_status VARCHAR(20) NOT NULL, -- success, failed, skipped
    error_message TEXT,
    execution_time_ms INTEGER,
    executed_at TIMESTAMPTZ DEFAULT NOW()
) PARTITION BY RANGE (executed_at);
```

#### Files & Attachments

```sql
-- Files
CREATE TABLE files (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id),
    original_name VARCHAR(255) NOT NULL,
    file_key VARCHAR(500) NOT NULL, -- S3 key
    file_size BIGINT NOT NULL,
    mime_type VARCHAR(100),
    checksum VARCHAR(64),
    thumbnail_key VARCHAR(500),
    uploaded_by UUID NOT NULL REFERENCES users(id),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);

-- File attachments
CREATE TABLE file_attachments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    file_id UUID NOT NULL REFERENCES files(id) ON DELETE CASCADE,
    entity_type VARCHAR(50) NOT NULL, -- item, comment, board
    entity_id UUID NOT NULL,
    attached_by UUID NOT NULL REFERENCES users(id),
    attached_at TIMESTAMPTZ DEFAULT NOW()
);
```

### Indexes & Constraints

```sql
-- Performance indexes
CREATE INDEX CONCURRENTLY idx_organizations_slug ON organizations(slug);
CREATE INDEX CONCURRENTLY idx_workspaces_org_id ON workspaces(organization_id);
CREATE INDEX CONCURRENTLY idx_boards_workspace_id ON boards(workspace_id);
CREATE INDEX CONCURRENTLY idx_items_board_id ON items(board_id);
CREATE INDEX CONCURRENTLY idx_items_parent_id ON items(parent_id) WHERE parent_id IS NOT NULL;
CREATE INDEX CONCURRENTLY idx_comments_item_id ON comments(item_id);
CREATE INDEX CONCURRENTLY idx_activity_log_org_created ON activity_log(organization_id, created_at);

-- Full-text search indexes
CREATE INDEX CONCURRENTLY idx_items_search
ON items USING GIN (to_tsvector('english', name || ' ' || COALESCE(description, '')));

CREATE INDEX CONCURRENTLY idx_comments_search
ON comments USING GIN (to_tsvector('english', content));

-- Partial indexes for soft deletes
CREATE INDEX CONCURRENTLY idx_items_active
ON items(board_id, position) WHERE deleted_at IS NULL;

CREATE INDEX CONCURRENTLY idx_boards_active
ON boards(workspace_id) WHERE deleted_at IS NULL;

-- Composite indexes for queries
CREATE INDEX CONCURRENTLY idx_org_members_user_role
ON organization_members(user_id, role, status);

CREATE INDEX CONCURRENTLY idx_workspace_members_user
ON workspace_members(user_id, workspace_id);
```

---

## Caching Layer (Redis)

### Cache Patterns

#### Application Cache Structure

```redis
# User session cache
user:session:{session_id} -> {
  "user_id": "uuid",
  "organization_id": "uuid",
  "permissions": ["read", "write"],
  "expires_at": "timestamp"
}
TTL: 24 hours

# User permissions cache
user:permissions:{user_id}:{org_id} -> {
  "workspaces": {
    "workspace_id": ["read", "write", "admin"]
  },
  "boards": {
    "board_id": ["read", "write"]
  }
}
TTL: 1 hour

# Board data cache
board:data:{board_id} -> {
  "id": "uuid",
  "name": "string",
  "columns": [...],
  "settings": {...}
}
TTL: 30 minutes

# Items cache (for frequently accessed boards)
board:items:{board_id} -> [
  {
    "id": "uuid",
    "name": "string",
    "data": {...},
    "position": 1.5
  }
]
TTL: 15 minutes

# Real-time presence
presence:board:{board_id} -> {
  "users": {
    "user_id": {
      "name": "John Doe",
      "cursor": {"x": 100, "y": 200},
      "last_seen": "timestamp"
    }
  }
}
TTL: 30 seconds
```

#### Real-time Communication

```redis
# WebSocket connection mapping
ws:connections:{user_id} -> set of connection_ids
TTL: Connection lifetime

# Board subscriptions
ws:board:{board_id} -> set of connection_ids
TTL: Connection lifetime

# Pub/Sub channels
PUBLISH board:{board_id}:item:created {
  "type": "item_created",
  "item": {...},
  "user": {...}
}

PUBLISH board:{board_id}:item:updated {
  "type": "item_updated",
  "item_id": "uuid",
  "changes": {...}
}

# Rate limiting
rate_limit:api:{user_id}:{endpoint} -> count
TTL: 1 hour

rate_limit:ip:{ip_address} -> count
TTL: 15 minutes
```

#### Cache Invalidation

```typescript
// Cache invalidation patterns
class CacheService {
  async invalidateBoard(boardId: string) {
    const keys = [
      `board:data:${boardId}`,
      `board:items:${boardId}`,
      `board:columns:${boardId}`,
    ];
    await redis.del(...keys);
  }

  async invalidateUserPermissions(userId: string, orgId: string) {
    const pattern = `user:permissions:${userId}:${orgId}`;
    await redis.del(pattern);
  }

  async publishUpdate(channel: string, data: any) {
    await redis.publish(channel, JSON.stringify(data));
  }
}
```

---

## Analytics Database (ClickHouse)

### Event Tracking Schema

```sql
-- Main events table
CREATE TABLE events (
    timestamp DateTime64(3) CODEC(Delta, ZSTD),
    event_id String CODEC(ZSTD),
    user_id String CODEC(ZSTD),
    organization_id String CODEC(ZSTD),
    workspace_id String CODEC(ZSTD),
    board_id String CODEC(ZSTD),
    item_id String CODEC(ZSTD),
    event_type String CODEC(ZSTD),
    event_category String CODEC(ZSTD),
    properties String CODEC(ZSTD), -- JSON string
    session_id String CODEC(ZSTD),
    ip_address String CODEC(ZSTD),
    user_agent String CODEC(ZSTD),
    created_date Date MATERIALIZED toDate(timestamp)
) ENGINE = MergeTree()
PARTITION BY toYYYYMM(timestamp)
ORDER BY (organization_id, created_date, timestamp)
SETTINGS index_granularity = 8192;

-- Page views tracking
CREATE TABLE page_views (
    timestamp DateTime64(3),
    user_id String,
    organization_id String,
    page_path String,
    referrer String,
    duration_seconds UInt32,
    session_id String
) ENGINE = MergeTree()
PARTITION BY toYYYYMM(timestamp)
ORDER BY (organization_id, toDate(timestamp), timestamp);

-- Performance metrics
CREATE TABLE performance_metrics (
    timestamp DateTime64(3),
    metric_name String,
    metric_value Float64,
    tags Map(String, String),
    organization_id String,
    service_name String
) ENGINE = MergeTree()
PARTITION BY toYYYYMM(timestamp)
ORDER BY (service_name, metric_name, timestamp);
```

### Materialized Views for Real-time Analytics

```sql
-- Daily active users
CREATE MATERIALIZED VIEW daily_active_users_mv
ENGINE = SummingMergeTree()
PARTITION BY toYYYYMM(date)
ORDER BY (organization_id, date)
AS SELECT
    toDate(timestamp) as date,
    organization_id,
    uniqState(user_id) as active_users
FROM events
WHERE event_type = 'user_activity'
GROUP BY date, organization_id;

-- Board activity summary
CREATE MATERIALIZED VIEW board_activity_mv
ENGINE = SummingMergeTree()
PARTITION BY toYYYYMM(date)
ORDER BY (organization_id, board_id, date)
AS SELECT
    toDate(timestamp) as date,
    organization_id,
    board_id,
    countState() as total_events,
    uniqState(user_id) as unique_users,
    sumState(if(event_type = 'item_created', 1, 0)) as items_created,
    sumState(if(event_type = 'item_updated', 1, 0)) as items_updated
FROM events
WHERE board_id != ''
GROUP BY date, organization_id, board_id;

-- User productivity metrics
CREATE MATERIALIZED VIEW user_productivity_mv
ENGINE = SummingMergeTree()
PARTITION BY toYYYYMM(date)
ORDER BY (organization_id, user_id, date)
AS SELECT
    toDate(timestamp) as date,
    organization_id,
    user_id,
    sumState(if(event_type = 'item_completed', 1, 0)) as tasks_completed,
    sumState(if(event_type = 'comment_added', 1, 0)) as comments_added,
    sumState(if(event_type = 'time_logged', toFloat64(JSONExtractFloat(properties, 'duration')), 0)) as time_logged
FROM events
WHERE user_id != ''
GROUP BY date, organization_id, user_id;
```

### Analytics Queries

```sql
-- Organization dashboard metrics
SELECT
    organization_id,
    uniq(user_id) as active_users,
    sum(if(event_type = 'item_created', 1, 0)) as items_created,
    sum(if(event_type = 'item_completed', 1, 0)) as items_completed,
    avg(if(event_type = 'page_load', toFloat64(JSONExtractFloat(properties, 'load_time')), NULL)) as avg_load_time
FROM events
WHERE timestamp >= now() - INTERVAL 30 DAY
GROUP BY organization_id;

-- Team productivity trends
SELECT
    toStartOfWeek(timestamp) as week,
    organization_id,
    uniq(user_id) as active_users,
    sum(if(event_type = 'item_completed', 1, 0)) / uniq(user_id) as avg_completion_rate
FROM events
WHERE timestamp >= now() - INTERVAL 12 WEEK
    AND organization_id = 'org_uuid'
GROUP BY week, organization_id
ORDER BY week;

-- Board performance analysis
SELECT
    board_id,
    count() as total_activity,
    uniq(user_id) as unique_contributors,
    sum(if(event_type = 'item_created', 1, 0)) as items_created,
    sum(if(event_type = 'item_completed', 1, 0)) as items_completed
FROM events
WHERE timestamp >= now() - INTERVAL 7 DAY
    AND organization_id = 'org_uuid'
    AND board_id != ''
GROUP BY board_id
ORDER BY total_activity DESC;
```

---

## Search Engine (Elasticsearch)

### Index Mappings

#### Items Index

```json
{
  "mappings": {
    "properties": {
      "id": { "type": "keyword" },
      "board_id": { "type": "keyword" },
      "workspace_id": { "type": "keyword" },
      "organization_id": { "type": "keyword" },
      "name": {
        "type": "text",
        "analyzer": "standard",
        "fields": {
          "keyword": { "type": "keyword" },
          "suggest": {
            "type": "completion",
            "analyzer": "simple"
          }
        }
      },
      "description": {
        "type": "text",
        "analyzer": "standard"
      },
      "tags": { "type": "keyword" },
      "status": { "type": "keyword" },
      "priority": { "type": "keyword" },
      "assignees": {
        "type": "nested",
        "properties": {
          "id": { "type": "keyword" },
          "name": { "type": "text" },
          "email": { "type": "keyword" }
        }
      },
      "custom_fields": {
        "type": "object",
        "dynamic": true
      },
      "created_by": { "type": "keyword" },
      "created_at": { "type": "date" },
      "updated_at": { "type": "date" },
      "due_date": { "type": "date" }
    }
  },
  "settings": {
    "number_of_shards": 3,
    "number_of_replicas": 1,
    "analysis": {
      "analyzer": {
        "custom_text_analyzer": {
          "type": "custom",
          "tokenizer": "standard",
          "filter": [
            "lowercase",
            "stop",
            "snowball"
          ]
        }
      }
    }
  }
}
```

#### Comments Index

```json
{
  "mappings": {
    "properties": {
      "id": { "type": "keyword" },
      "item_id": { "type": "keyword" },
      "board_id": { "type": "keyword" },
      "user_id": { "type": "keyword" },
      "content": {
        "type": "text",
        "analyzer": "standard",
        "highlight": {}
      },
      "mentions": { "type": "keyword" },
      "created_at": { "type": "date" },
      "updated_at": { "type": "date" }
    }
  }
}
```

### Search Queries

```typescript
// Multi-field search
const searchQuery = {
  index: 'items',
  body: {
    query: {
      bool: {
        must: [
          {
            multi_match: {
              query: searchTerm,
              fields: ['name^3', 'description^2', 'custom_fields.*'],
              fuzziness: 'AUTO'
            }
          }
        ],
        filter: [
          { term: { organization_id: orgId } },
          { terms: { board_id: accessibleBoardIds } }
        ]
      }
    },
    highlight: {
      fields: {
        name: {},
        description: {}
      }
    },
    aggregations: {
      boards: {
        terms: { field: 'board_id' }
      },
      statuses: {
        terms: { field: 'status' }
      },
      assignees: {
        nested: { path: 'assignees' },
        aggs: {
          users: {
            terms: { field: 'assignees.id' }
          }
        }
      }
    },
    sort: [
      { _score: { order: 'desc' } },
      { updated_at: { order: 'desc' } }
    ]
  }
};

// Autocomplete suggestions
const suggestQuery = {
  index: 'items',
  body: {
    suggest: {
      item_suggest: {
        prefix: searchTerm,
        completion: {
          field: 'name.suggest',
          size: 10,
          contexts: {
            organization_id: [orgId]
          }
        }
      }
    }
  }
};
```

---

## Data Relationships & Constraints

### Entity Relationship Diagram

```
Organizations (1) ──────── (*) Workspaces
     │                          │
     │                          │
     (*) Org_Members             (*) Workspace_Members
     │                          │
     │                          │
Users (1) ──────────────────────┴─── (*) Boards
     │                               │
     │                               │
     (*) Comments                     (*) Items
     │                               │
     │                               │
     └─── (*) Time_Entries ──────── (*)
     │
     (*) Activity_Log
```

### Key Relationships

#### 1. Multi-tenancy Hierarchy
```sql
Organization → Workspace → Board → Item
```

#### 2. User Permissions
```sql
User → Organization_Member → Workspace_Member → Board_Access
```

#### 3. Content Relationships
```sql
Item → Comments
Item → Time_Entries
Item → File_Attachments
Item → Item_Dependencies (self-referential)
```

### Referential Integrity

```sql
-- Cascade delete rules
ALTER TABLE workspaces
ADD CONSTRAINT fk_workspaces_organization
FOREIGN KEY (organization_id) REFERENCES organizations(id) ON DELETE CASCADE;

ALTER TABLE boards
ADD CONSTRAINT fk_boards_workspace
FOREIGN KEY (workspace_id) REFERENCES workspaces(id) ON DELETE CASCADE;

-- Soft delete implementation
CREATE OR REPLACE FUNCTION soft_delete_items()
RETURNS TRIGGER AS $$
BEGIN
    -- When a board is soft deleted, soft delete all items
    IF NEW.deleted_at IS NOT NULL AND OLD.deleted_at IS NULL THEN
        UPDATE items
        SET deleted_at = NEW.deleted_at
        WHERE board_id = NEW.id AND deleted_at IS NULL;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_soft_delete_items
    AFTER UPDATE ON boards
    FOR EACH ROW
    EXECUTE FUNCTION soft_delete_items();
```

---

## Indexing Strategy

### Primary Indexes

#### 1. Performance-Critical Indexes
```sql
-- Board item queries (most frequent)
CREATE INDEX CONCURRENTLY idx_items_board_position
ON items(board_id, position)
WHERE deleted_at IS NULL;

-- User access patterns
CREATE INDEX CONCURRENTLY idx_org_members_user_active
ON organization_members(user_id, organization_id)
WHERE status = 'active';

-- Activity queries
CREATE INDEX CONCURRENTLY idx_activity_log_entity_time
ON activity_log(entity_type, entity_id, created_at DESC);
```

#### 2. Search Optimization
```sql
-- Full-text search with GIN indexes
CREATE INDEX CONCURRENTLY idx_items_fulltext
ON items USING GIN (
    to_tsvector('english',
        name || ' ' ||
        COALESCE(description, '') || ' ' ||
        (item_data::text)
    )
);

-- Trigram similarity search
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE INDEX CONCURRENTLY idx_items_name_trgm
ON items USING GIN (name gin_trgm_ops);
```

#### 3. Analytics Indexes
```sql
-- Time-series data
CREATE INDEX CONCURRENTLY idx_activity_log_org_time
ON activity_log(organization_id, created_at)
WHERE action IN ('item_created', 'item_completed', 'item_updated');

-- Aggregation optimization
CREATE INDEX CONCURRENTLY idx_time_entries_user_date
ON time_entries(user_id, DATE(start_time), item_id);
```

### Composite Indexes

```sql
-- Complex query optimization
CREATE INDEX CONCURRENTLY idx_items_board_status_assignee
ON items(board_id, (item_data->>'status'))
WHERE deleted_at IS NULL;

-- Permission checking
CREATE INDEX CONCURRENTLY idx_workspace_members_user_perms
ON workspace_members(user_id, workspace_id, role);
```

---

## Partitioning & Sharding

### Table Partitioning

#### 1. Time-based Partitioning
```sql
-- Activity log partitioning (monthly)
CREATE TABLE activity_log (
    -- columns...
) PARTITION BY RANGE (created_at);

-- Create partitions
CREATE TABLE activity_log_y2024m12 PARTITION OF activity_log
    FOR VALUES FROM ('2024-12-01') TO ('2025-01-01');

CREATE TABLE activity_log_y2025m01 PARTITION OF activity_log
    FOR VALUES FROM ('2025-01-01') TO ('2025-02-01');

-- Automated partition management
CREATE OR REPLACE FUNCTION create_monthly_partition(table_name text, start_date date)
RETURNS void AS $$
DECLARE
    partition_name text;
    end_date date;
BEGIN
    partition_name := table_name || '_y' || to_char(start_date, 'YYYY') || 'm' || to_char(start_date, 'MM');
    end_date := start_date + interval '1 month';

    EXECUTE format('CREATE TABLE %I PARTITION OF %I FOR VALUES FROM (%L) TO (%L)',
                   partition_name, table_name, start_date, end_date);
END;
$$ LANGUAGE plpgsql;
```

#### 2. Organization-based Partitioning
```sql
-- Large tables partitioned by organization
CREATE TABLE items_partitioned (
    -- columns...
    organization_id UUID NOT NULL
) PARTITION BY HASH (organization_id);

-- Create hash partitions
CREATE TABLE items_part_0 PARTITION OF items_partitioned
    FOR VALUES WITH (MODULUS 4, REMAINDER 0);

CREATE TABLE items_part_1 PARTITION OF items_partitioned
    FOR VALUES WITH (MODULUS 4, REMAINDER 1);

CREATE TABLE items_part_2 PARTITION OF items_partitioned
    FOR VALUES WITH (MODULUS 4, REMAINDER 2);

CREATE TABLE items_part_3 PARTITION OF items_partitioned
    FOR VALUES WITH (MODULUS 4, REMAINDER 3);
```

### Horizontal Sharding Strategy

#### 1. Tenant-based Sharding
```typescript
// Shard routing logic
class ShardRouter {
  private shards = [
    { id: 'shard_1', connection: 'postgres://shard1.sunday.com' },
    { id: 'shard_2', connection: 'postgres://shard2.sunday.com' },
    { id: 'shard_3', connection: 'postgres://shard3.sunday.com' },
    { id: 'shard_4', connection: 'postgres://shard4.sunday.com' },
  ];

  getShardForOrganization(organizationId: string): string {
    const hash = this.hashFunction(organizationId);
    const shardIndex = hash % this.shards.length;
    return this.shards[shardIndex].id;
  }

  private hashFunction(key: string): number {
    // Consistent hashing implementation
    return crc32(key);
  }
}
```

#### 2. Cross-shard Queries
```typescript
// Federated query executor
class FederatedQueryExecutor {
  async queryAllShards(query: string, params: any[]): Promise<any[]> {
    const promises = this.shards.map(shard =>
      this.executeOnShard(shard, query, params)
    );

    const results = await Promise.all(promises);
    return this.mergeResults(results);
  }

  async querySpecificShard(organizationId: string, query: string, params: any[]): Promise<any> {
    const shard = this.shardRouter.getShardForOrganization(organizationId);
    return this.executeOnShard(shard, query, params);
  }
}
```

---

## Data Migration Strategy

### Schema Evolution

#### 1. Database Migrations
```sql
-- Migration versioning
CREATE TABLE schema_migrations (
    version VARCHAR(14) PRIMARY KEY,
    applied_at TIMESTAMPTZ DEFAULT NOW()
);

-- Example migration: Add new column
-- Migration: 20241201_001_add_item_priority.sql
BEGIN;

ALTER TABLE items
ADD COLUMN priority VARCHAR(20) DEFAULT 'medium';

CREATE INDEX CONCURRENTLY idx_items_priority
ON items(priority) WHERE deleted_at IS NULL;

INSERT INTO schema_migrations (version) VALUES ('20241201_001');

COMMIT;
```

#### 2. Data Backfill Strategy
```typescript
// Large table backfill
class DataMigration {
  async backfillItemPriority() {
    const batchSize = 1000;
    let offset = 0;

    while (true) {
      const items = await this.db.query(`
        SELECT id FROM items
        WHERE priority IS NULL
        ORDER BY id
        LIMIT $1 OFFSET $2
      `, [batchSize, offset]);

      if (items.length === 0) break;

      // Process batch
      await this.processBatch(items);
      offset += batchSize;

      // Rate limiting
      await this.sleep(100);
    }
  }

  private async processBatch(items: any[]) {
    const updates = items.map(item => ({
      id: item.id,
      priority: this.calculatePriority(item)
    }));

    await this.db.query(`
      UPDATE items
      SET priority = data.priority
      FROM (VALUES ${this.buildValuesClause(updates)}) AS data(id, priority)
      WHERE items.id = data.id::uuid
    `);
  }
}
```

### Data Synchronization

#### 1. Event-driven Sync
```typescript
// Kafka-based data sync
class DataSynchronizer {
  async syncToAnalytics(event: DomainEvent) {
    switch (event.type) {
      case 'ItemCreated':
        await this.syncItemToClickHouse(event.data);
        await this.syncItemToElasticsearch(event.data);
        break;

      case 'ItemUpdated':
        await this.updateItemInClickHouse(event.data);
        await this.updateItemInElasticsearch(event.data);
        break;

      case 'ItemDeleted':
        await this.removeItemFromElasticsearch(event.data.id);
        // ClickHouse keeps historical data
        break;
    }
  }
}
```

#### 2. Bulk Data Export/Import
```typescript
// Data export for analytics
class DataExporter {
  async exportToDataWarehouse() {
    const query = `
      SELECT
        i.id,
        i.name,
        i.created_at,
        b.name as board_name,
        w.name as workspace_name,
        o.name as organization_name
      FROM items i
      JOIN boards b ON i.board_id = b.id
      JOIN workspaces w ON b.workspace_id = w.id
      JOIN organizations o ON w.organization_id = o.id
      WHERE i.created_at >= $1
    `;

    const stream = this.db.stream(query, [this.lastExportDate]);

    // Stream to S3 in Parquet format
    await this.streamToS3(stream, 'data-warehouse/items/');
  }
}
```

---

## Performance Optimization

### Query Optimization

#### 1. Complex Query Examples
```sql
-- Optimized board loading with all related data
WITH board_data AS (
  SELECT
    b.id,
    b.name,
    b.settings,
    json_agg(
      json_build_object(
        'id', bc.id,
        'name', bc.name,
        'type', bc.column_type,
        'settings', bc.settings
      ) ORDER BY bc.position
    ) as columns
  FROM boards b
  LEFT JOIN board_columns bc ON b.id = bc.board_id
  WHERE b.id = $1 AND b.deleted_at IS NULL
  GROUP BY b.id, b.name, b.settings
),
item_data AS (
  SELECT
    i.board_id,
    json_agg(
      json_build_object(
        'id', i.id,
        'name', i.name,
        'data', i.item_data,
        'position', i.position,
        'assignees', COALESCE(assignee_data.assignees, '[]'::json)
      ) ORDER BY i.position
    ) as items
  FROM items i
  LEFT JOIN (
    SELECT
      ia.item_id,
      json_agg(
        json_build_object(
          'id', u.id,
          'name', u.first_name || ' ' || u.last_name,
          'avatar', u.avatar_url
        )
      ) as assignees
    FROM item_assignments ia
    JOIN users u ON ia.user_id = u.id
    GROUP BY ia.item_id
  ) assignee_data ON i.id = assignee_data.item_id
  WHERE i.board_id = $1 AND i.deleted_at IS NULL
  GROUP BY i.board_id
)
SELECT
  bd.*,
  COALESCE(id.items, '[]'::json) as items
FROM board_data bd
LEFT JOIN item_data id ON bd.id = id.board_id;
```

#### 2. Pagination Strategy
```sql
-- Cursor-based pagination for large datasets
SELECT
  id,
  name,
  created_at
FROM items
WHERE board_id = $1
  AND created_at < $2 -- cursor
  AND deleted_at IS NULL
ORDER BY created_at DESC
LIMIT $3;
```

### Connection Management

```typescript
// Connection pooling configuration
const poolConfig = {
  host: process.env.DB_HOST,
  port: 5432,
  database: process.env.DB_NAME,
  user: process.env.DB_USER,
  password: process.env.DB_PASSWORD,

  // Pool settings
  min: 5,
  max: 20,
  acquireTimeoutMillis: 30000,
  createTimeoutMillis: 30000,
  destroyTimeoutMillis: 5000,
  idleTimeoutMillis: 30000,

  // Connection validation
  testOnBorrow: true,

  // Performance optimization
  statement_timeout: 30000,
  query_timeout: 30000,
};
```

---

## Conclusion

This comprehensive database design provides a robust, scalable foundation for Sunday.com that can handle enterprise-grade workloads while maintaining high performance and data integrity. The polyglot persistence strategy ensures each data store is optimized for its specific use case, while the careful indexing and partitioning strategies enable the platform to scale to millions of users and billions of data points.

### Key Design Decisions Summary

1. **Multi-tenant Architecture:** Organization-based data isolation with efficient querying
2. **Polyglot Persistence:** Optimal database selection for each use case
3. **Event-Driven Sync:** Consistent data across all storage systems
4. **Performance-First Indexing:** Comprehensive indexing strategy for fast queries
5. **Horizontal Scalability:** Partitioning and sharding for unlimited growth
6. **Real-time Capabilities:** Redis-based caching and pub/sub for live features
7. **Analytics-Ready:** ClickHouse integration for advanced business intelligence

### Performance Targets

- **Query Response Time:** <50ms for 95% of queries
- **Real-time Updates:** <100ms latency for live collaboration
- **Search Performance:** <200ms for complex searches
- **Analytics Queries:** <2 seconds for dashboard loading
- **Concurrent Users:** 100,000+ simultaneous active users

---

*Document Version: 1.0*
*Created: December 2024*
*Next Review: Q1 2025*
*Approval Required: CTO, Database Architect, Performance Team*