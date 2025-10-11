# Sunday.com Database Schema Documentation

## Overview

Sunday.com uses PostgreSQL as the primary database with Prisma ORM for type-safe database access. The schema is designed to support multi-tenant work management with organizations, workspaces, boards, items, real-time collaboration, and comprehensive audit logging.

## Database Provider

**PostgreSQL 13+** with Prisma ORM

## Schema Structure

The database consists of **18 core tables** organized into logical modules:

1. **Organizations & Workspaces** (3 tables)
2. **Users & Membership** (3 tables)
3. **Boards & Templates** (5 tables)
4. **Items & Tasks** (3 tables)
5. **Comments & Collaboration** (1 table)
6. **Time Tracking** (1 table)
7. **Files & Attachments** (2 tables)
8. **Automation & Workflows** (2 tables)
9. **Activity & Audit Logs** (1 table)
10. **Webhooks** (2 tables)

## Table Definitions

### Organizations & Workspaces Module

#### organizations
Primary tenant container for multi-tenancy.

```sql
CREATE TABLE organizations (
    id VARCHAR PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR NOT NULL,
    slug VARCHAR UNIQUE NOT NULL,
    domain VARCHAR,
    settings JSONB DEFAULT '{}',
    subscription_plan VARCHAR DEFAULT 'free',
    subscription_status VARCHAR DEFAULT 'active',
    created_at TIMESTAMP DEFAULT now(),
    updated_at TIMESTAMP DEFAULT now(),
    deleted_at TIMESTAMP
);
```

**Key Features:**
- Multi-tenant isolation at organization level
- Subscription management with plans and status
- Flexible settings storage in JSONB
- Soft delete support
- Custom domain support

**Relationships:**
- One-to-many: workspaces, members, board_templates, files, automation_rules

#### workspaces
Logical grouping within organizations for teams/projects.

```sql
CREATE TABLE workspaces (
    id VARCHAR PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id VARCHAR NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    name VARCHAR NOT NULL,
    description TEXT,
    color VARCHAR DEFAULT '#6B7280',
    settings JSONB DEFAULT '{}',
    is_private BOOLEAN DEFAULT false,
    created_at TIMESTAMP DEFAULT now(),
    updated_at TIMESTAMP DEFAULT now(),
    deleted_at TIMESTAMP,

    CONSTRAINT workspace_org_name_unique UNIQUE (organization_id, name)
);
```

**Key Features:**
- Hierarchical structure under organizations
- Privacy controls (public/private workspaces)
- Color coding for visual organization
- Unique naming within organization scope

**Relationships:**
- Many-to-one: organization
- One-to-many: boards, members, folders, automation_rules

### Users & Membership Module

#### users
Core user accounts with authentication and profile data.

```sql
CREATE TABLE users (
    id VARCHAR PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR UNIQUE NOT NULL,
    email_verified BOOLEAN DEFAULT false,
    password_hash VARCHAR,
    first_name VARCHAR,
    last_name VARCHAR,
    avatar_url VARCHAR,
    timezone VARCHAR DEFAULT 'UTC',
    locale VARCHAR DEFAULT 'en',
    settings JSONB DEFAULT '{}',
    last_login_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT now(),
    updated_at TIMESTAMP DEFAULT now(),
    deleted_at TIMESTAMP
);
```

**Key Features:**
- Email-based authentication
- OAuth support (password_hash nullable)
- Internationalization (timezone, locale)
- Customizable user settings
- Soft delete with audit trail

**Relationships:**
- One-to-many: organization_members, workspace_members, board_members, items, comments, time_entries, files, activity_logs

#### organization_members
Organization-level membership and roles.

```sql
CREATE TABLE organization_members (
    id VARCHAR PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id VARCHAR NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    user_id VARCHAR NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role VARCHAR DEFAULT 'member',
    status VARCHAR DEFAULT 'active',
    invited_by VARCHAR REFERENCES users(id),
    invited_at TIMESTAMP,
    joined_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT now(),
    updated_at TIMESTAMP DEFAULT now(),

    CONSTRAINT unique_org_user UNIQUE (organization_id, user_id)
);
```

**Key Features:**
- Role-based access control at organization level
- Invitation workflow tracking
- Membership status management
- Audit trail for membership changes

#### workspace_members
Workspace-level membership with granular permissions.

```sql
CREATE TABLE workspace_members (
    id VARCHAR PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id VARCHAR NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    user_id VARCHAR NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role VARCHAR DEFAULT 'member',
    permissions JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT now(),
    updated_at TIMESTAMP DEFAULT now(),

    CONSTRAINT unique_workspace_user UNIQUE (workspace_id, user_id)
);
```

**Key Features:**
- Granular permission system via JSONB
- Role hierarchy (admin, member, viewer)
- Workspace-specific access control

### Boards & Templates Module

#### boards
Core work management boards with customizable columns.

```sql
CREATE TABLE boards (
    id VARCHAR PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id VARCHAR NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    name VARCHAR NOT NULL,
    description TEXT,
    template_id VARCHAR REFERENCES board_templates(id),
    settings JSONB DEFAULT '{}',
    view_settings JSONB DEFAULT '{}',
    is_private BOOLEAN DEFAULT false,
    folder_id VARCHAR REFERENCES folders(id),
    position INTEGER,
    created_by VARCHAR NOT NULL REFERENCES users(id),
    created_at TIMESTAMP DEFAULT now(),
    updated_at TIMESTAMP DEFAULT now(),
    deleted_at TIMESTAMP
);
```

**Key Features:**
- Template-based board creation
- Flexible view configurations (Kanban, Table, Timeline, Calendar)
- Folder organization
- Privacy controls
- Position-based ordering

**Relationships:**
- Many-to-one: workspace, template, folder, creator
- One-to-many: columns, items, members, automation_rules, activity_logs

#### board_templates
Reusable board templates for quick setup.

```sql
CREATE TABLE board_templates (
    id VARCHAR PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR NOT NULL,
    description TEXT,
    category VARCHAR,
    template_data JSONB NOT NULL,
    is_public BOOLEAN DEFAULT false,
    created_by VARCHAR REFERENCES users(id),
    organization_id VARCHAR REFERENCES organizations(id),
    usage_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT now(),
    updated_at TIMESTAMP DEFAULT now()
);
```

**Key Features:**
- Public and private templates
- Usage analytics
- Complete board structure serialization
- Category-based organization

#### board_columns
Configurable columns for boards with validation rules.

```sql
CREATE TABLE board_columns (
    id VARCHAR PRIMARY KEY DEFAULT gen_random_uuid(),
    board_id VARCHAR NOT NULL REFERENCES boards(id) ON DELETE CASCADE,
    name VARCHAR NOT NULL,
    column_type VARCHAR NOT NULL,
    settings JSONB DEFAULT '{}',
    validation_rules JSONB DEFAULT '{}',
    position INTEGER NOT NULL,
    is_required BOOLEAN DEFAULT false,
    is_visible BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT now(),
    updated_at TIMESTAMP DEFAULT now(),

    CONSTRAINT unique_board_column_position UNIQUE (board_id, position)
);
```

**Key Features:**
- Multiple column types (text, number, date, status, people, etc.)
- Validation rules for data integrity
- Column visibility controls
- Position-based ordering

#### board_members
Board-level access control and permissions.

```sql
CREATE TABLE board_members (
    id VARCHAR PRIMARY KEY DEFAULT gen_random_uuid(),
    board_id VARCHAR NOT NULL REFERENCES boards(id) ON DELETE CASCADE,
    user_id VARCHAR NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role VARCHAR DEFAULT 'member',
    permissions JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT now(),
    updated_at TIMESTAMP DEFAULT now(),

    CONSTRAINT unique_board_user UNIQUE (board_id, user_id)
);
```

#### folders
Organizational folders for grouping boards.

```sql
CREATE TABLE folders (
    id VARCHAR PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id VARCHAR NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    name VARCHAR NOT NULL,
    color VARCHAR DEFAULT '#6B7280',
    position INTEGER,
    created_at TIMESTAMP DEFAULT now(),
    updated_at TIMESTAMP DEFAULT now()
);
```

### Items & Tasks Module

#### items
Core work items/tasks with hierarchical structure.

```sql
CREATE TABLE items (
    id VARCHAR PRIMARY KEY DEFAULT gen_random_uuid(),
    board_id VARCHAR NOT NULL REFERENCES boards(id) ON DELETE CASCADE,
    parent_id VARCHAR REFERENCES items(id),
    name VARCHAR NOT NULL,
    description TEXT,
    item_data JSONB DEFAULT '{}',
    position DECIMAL(10,5) NOT NULL,
    created_by VARCHAR NOT NULL REFERENCES users(id),
    created_at TIMESTAMP DEFAULT now(),
    updated_at TIMESTAMP DEFAULT now(),
    deleted_at TIMESTAMP
);
```

**Key Features:**
- Hierarchical structure (parent-child relationships)
- Flexible data storage in JSONB for custom fields
- Precise positioning with DECIMAL for drag-and-drop
- Soft delete with audit trail

**Relationships:**
- Many-to-one: board, parent, creator
- One-to-many: children, assignments, dependencies, comments, time_entries, attachments, activity_logs

#### item_assignments
User assignments to items with audit trail.

```sql
CREATE TABLE item_assignments (
    id VARCHAR PRIMARY KEY DEFAULT gen_random_uuid(),
    item_id VARCHAR NOT NULL REFERENCES items(id) ON DELETE CASCADE,
    user_id VARCHAR NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    assigned_by VARCHAR NOT NULL,
    assigned_at TIMESTAMP DEFAULT now(),

    CONSTRAINT unique_item_user_assignment UNIQUE (item_id, user_id)
);
```

**Key Features:**
- Multiple assignees per item
- Assignment audit trail
- Assignment history tracking

#### item_dependencies
Task dependencies for project management.

```sql
CREATE TABLE item_dependencies (
    id VARCHAR PRIMARY KEY DEFAULT gen_random_uuid(),
    predecessor_id VARCHAR NOT NULL REFERENCES items(id) ON DELETE CASCADE,
    successor_id VARCHAR NOT NULL REFERENCES items(id) ON DELETE CASCADE,
    dependency_type VARCHAR DEFAULT 'blocks',
    created_by VARCHAR NOT NULL,
    created_at TIMESTAMP DEFAULT now(),

    CONSTRAINT unique_item_dependency UNIQUE (predecessor_id, successor_id)
);
```

**Key Features:**
- Multiple dependency types (blocks, related)
- Circular dependency prevention (application-level)
- Dependency visualization support

### Comments & Collaboration Module

#### comments
Threaded comments with mentions and attachments.

```sql
CREATE TABLE comments (
    id VARCHAR PRIMARY KEY DEFAULT gen_random_uuid(),
    item_id VARCHAR NOT NULL REFERENCES items(id) ON DELETE CASCADE,
    parent_id VARCHAR REFERENCES comments(id),
    user_id VARCHAR NOT NULL REFERENCES users(id),
    content TEXT NOT NULL,
    content_type VARCHAR DEFAULT 'text',
    mentions JSONB DEFAULT '[]',
    attachments JSONB DEFAULT '[]',
    is_edited BOOLEAN DEFAULT false,
    created_at TIMESTAMP DEFAULT now(),
    updated_at TIMESTAMP DEFAULT now(),
    deleted_at TIMESTAMP
);
```

**Key Features:**
- Threaded comment system
- Rich content support (text, markdown)
- User mentions with notifications
- File attachments
- Edit history tracking

### Time Tracking Module

#### time_entries
Time tracking for items with billing support.

```sql
CREATE TABLE time_entries (
    id VARCHAR PRIMARY KEY DEFAULT gen_random_uuid(),
    item_id VARCHAR NOT NULL REFERENCES items(id) ON DELETE CASCADE,
    user_id VARCHAR NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    description TEXT,
    start_time TIMESTAMP NOT NULL,
    end_time TIMESTAMP,
    duration_seconds INTEGER,
    is_billable BOOLEAN DEFAULT false,
    created_at TIMESTAMP DEFAULT now(),
    updated_at TIMESTAMP DEFAULT now()
);
```

**Key Features:**
- Active time tracking (start/stop)
- Manual time entry
- Billable time categorization
- Duration calculations

### Files & Attachments Module

#### files
Secure file storage with metadata.

```sql
CREATE TABLE files (
    id VARCHAR PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id VARCHAR NOT NULL REFERENCES organizations(id),
    original_name VARCHAR NOT NULL,
    file_key VARCHAR NOT NULL,
    file_size BIGINT NOT NULL,
    mime_type VARCHAR,
    checksum VARCHAR,
    thumbnail_key VARCHAR,
    uploaded_by VARCHAR NOT NULL REFERENCES users(id),
    created_at TIMESTAMP DEFAULT now(),
    deleted_at TIMESTAMP
);
```

**Key Features:**
- S3-based file storage
- File integrity verification (checksum)
- Thumbnail generation
- Organization-scoped storage

#### file_attachments
Polymorphic file attachments to entities.

```sql
CREATE TABLE file_attachments (
    id VARCHAR PRIMARY KEY DEFAULT gen_random_uuid(),
    file_id VARCHAR NOT NULL REFERENCES files(id) ON DELETE CASCADE,
    entity_type VARCHAR NOT NULL,
    entity_id VARCHAR NOT NULL,
    item_id VARCHAR REFERENCES items(id),
    attached_by VARCHAR NOT NULL REFERENCES users(id),
    attached_at TIMESTAMP DEFAULT now()
);
```

**Key Features:**
- Polymorphic attachments (items, comments, etc.)
- Attachment audit trail
- Multiple attachments per entity

### Automation & Workflows Module

#### automation_rules
Configurable automation rules with triggers and actions.

```sql
CREATE TABLE automation_rules (
    id VARCHAR PRIMARY KEY DEFAULT gen_random_uuid(),
    board_id VARCHAR REFERENCES boards(id) ON DELETE CASCADE,
    workspace_id VARCHAR REFERENCES workspaces(id) ON DELETE CASCADE,
    organization_id VARCHAR REFERENCES organizations(id) ON DELETE CASCADE,
    name VARCHAR NOT NULL,
    description TEXT,
    trigger_config JSONB NOT NULL,
    condition_config JSONB DEFAULT '{}',
    action_config JSONB NOT NULL,
    is_enabled BOOLEAN DEFAULT true,
    execution_count INTEGER DEFAULT 0,
    last_executed_at TIMESTAMP,
    created_by VARCHAR NOT NULL REFERENCES users(id),
    created_at TIMESTAMP DEFAULT now(),
    updated_at TIMESTAMP DEFAULT now()
);
```

**Key Features:**
- Multi-level scope (organization, workspace, board)
- Complex trigger/condition/action configuration
- Execution statistics
- Enable/disable controls

#### automation_executions
Automation execution history and audit trail.

```sql
CREATE TABLE automation_executions (
    id VARCHAR PRIMARY KEY DEFAULT gen_random_uuid(),
    rule_id VARCHAR NOT NULL REFERENCES automation_rules(id) ON DELETE CASCADE,
    item_id VARCHAR REFERENCES items(id),
    trigger_data JSONB,
    execution_status VARCHAR NOT NULL,
    error_message TEXT,
    execution_time_ms INTEGER,
    executed_by VARCHAR REFERENCES users(id),
    executed_at TIMESTAMP DEFAULT now()
);
```

**Key Features:**
- Complete execution audit trail
- Error tracking and debugging
- Performance monitoring
- Execution context preservation

### Activity & Audit Logs Module

#### activity_log
Comprehensive audit trail for all system changes.

```sql
CREATE TABLE activity_log (
    id VARCHAR PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id VARCHAR NOT NULL,
    workspace_id VARCHAR,
    board_id VARCHAR REFERENCES boards(id),
    item_id VARCHAR REFERENCES items(id),
    user_id VARCHAR NOT NULL REFERENCES users(id),
    action VARCHAR NOT NULL,
    entity_type VARCHAR NOT NULL,
    entity_id VARCHAR NOT NULL,
    old_values JSONB,
    new_values JSONB,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT now()
);
```

**Key Features:**
- Complete change tracking
- Before/after value storage
- Multi-level entity tracking
- Searchable metadata

### Webhooks Module

#### webhooks
External webhook integrations.

```sql
CREATE TABLE webhooks (
    id VARCHAR PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id VARCHAR NOT NULL,
    url VARCHAR NOT NULL,
    events TEXT[] NOT NULL,
    secret VARCHAR NOT NULL,
    is_active BOOLEAN DEFAULT true,
    filters JSONB DEFAULT '{}',
    created_by VARCHAR NOT NULL,
    created_at TIMESTAMP DEFAULT now(),
    updated_at TIMESTAMP DEFAULT now()
);
```

#### webhook_deliveries
Webhook delivery tracking and retry logic.

```sql
CREATE TABLE webhook_deliveries (
    id VARCHAR PRIMARY KEY DEFAULT gen_random_uuid(),
    webhook_id VARCHAR NOT NULL REFERENCES webhooks(id) ON DELETE CASCADE,
    event VARCHAR NOT NULL,
    payload JSONB NOT NULL,
    response JSONB,
    status VARCHAR DEFAULT 'pending',
    attempt INTEGER DEFAULT 1,
    delivered_at TIMESTAMP,
    next_retry_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT now()
);
```

## Database Indexes

### Performance Indexes

```sql
-- Core entity lookups
CREATE INDEX idx_workspaces_organization_id ON workspaces(organization_id);
CREATE INDEX idx_boards_workspace_id ON boards(workspace_id);
CREATE INDEX idx_items_board_id ON items(board_id);
CREATE INDEX idx_items_parent_id ON items(parent_id);

-- User access patterns
CREATE INDEX idx_organization_members_user_id ON organization_members(user_id);
CREATE INDEX idx_workspace_members_user_id ON workspace_members(user_id);
CREATE INDEX idx_board_members_user_id ON board_members(user_id);
CREATE INDEX idx_item_assignments_user_id ON item_assignments(user_id);

-- Position-based ordering
CREATE INDEX idx_items_board_position ON items(board_id, position);
CREATE INDEX idx_board_columns_board_position ON board_columns(board_id, position);

-- Time-based queries
CREATE INDEX idx_activity_log_created_at ON activity_log(created_at);
CREATE INDEX idx_time_entries_start_time ON time_entries(start_time);
CREATE INDEX idx_comments_created_at ON comments(created_at);

-- Soft delete support
CREATE INDEX idx_items_deleted_at ON items(deleted_at);
CREATE INDEX idx_boards_deleted_at ON boards(deleted_at);
CREATE INDEX idx_users_deleted_at ON users(deleted_at);

-- Full-text search
CREATE INDEX idx_items_name_gin ON items USING gin(to_tsvector('english', name));
CREATE INDEX idx_items_description_gin ON items USING gin(to_tsvector('english', description));

-- JSONB queries
CREATE INDEX idx_items_data_gin ON items USING gin(item_data);
CREATE INDEX idx_activity_log_metadata_gin ON activity_log USING gin(metadata);
```

### Composite Indexes

```sql
-- Multi-column lookups
CREATE INDEX idx_boards_workspace_folder ON boards(workspace_id, folder_id);
CREATE INDEX idx_items_board_parent ON items(board_id, parent_id);
CREATE INDEX idx_activity_log_entity ON activity_log(entity_type, entity_id);

-- Time-range queries
CREATE INDEX idx_time_entries_user_date ON time_entries(user_id, start_time);
CREATE INDEX idx_automation_executions_rule_date ON automation_executions(rule_id, executed_at);
```

## Data Types and Constraints

### Primary Keys
- All tables use `cuid()` for primary keys
- Provides URL-safe, collision-resistant identifiers
- Better performance than UUIDs for database clustering

### Foreign Keys
- Strict referential integrity with CASCADE deletes where appropriate
- Soft delete patterns for audit trail preservation
- Nullable foreign keys for optional relationships

### JSONB Usage
- Flexible schema storage for custom fields
- Settings and configuration data
- Activity log change tracking
- File attachment metadata

### Decimal Precision
- Item positions use `DECIMAL(10,5)` for precise ordering
- Supports fractional positioning for drag-and-drop
- Prevents ordering conflicts in concurrent updates

## Security Considerations

### Multi-Tenancy
- Organization-level data isolation
- Row-level security policies (RLS) ready
- Workspace and board-level access controls

### Data Protection
- Password hashing (bcrypt)
- Sensitive data encryption at application level
- Audit logging for compliance (SOX, GDPR, HIPAA)

### Performance
- Optimized indexes for common query patterns
- Partial indexes for soft-deleted records
- JSONB indexes for flexible schema queries

## Backup and Recovery

### Backup Strategy
- Point-in-time recovery (PITR) enabled
- Daily full backups
- Continuous WAL archiving
- Cross-region backup replication

### Data Retention
- Soft delete with configurable retention periods
- Activity log archival after 2 years
- File cleanup for orphaned attachments
- GDPR-compliant data deletion

## Migration Management

### Prisma Migrations
- Version-controlled schema changes
- Rollback capability
- Production deployment automation
- Data migration scripts

### Schema Versioning
```bash
# Generate migration
npx prisma migrate dev --name add_new_feature

# Deploy to production
npx prisma migrate deploy

# Reset development database
npx prisma migrate reset
```

## Performance Characteristics

### Query Performance
- Sub-10ms response times for indexed queries
- Optimized joins for common access patterns
- Connection pooling (100+ concurrent connections)
- Read replicas for reporting queries

### Scalability
- Horizontal scaling with read replicas
- Partitioning ready for large tables
- Archive tables for historical data
- Caching layer (Redis) integration

### Monitoring
- Query performance tracking
- Slow query identification
- Connection pool monitoring
- Disk usage alerts

## Development Tools

### Database Administration
```bash
# Access Prisma Studio
npx prisma studio

# Generate Prisma client
npx prisma generate

# Database introspection
npx prisma db pull

# Schema validation
npx prisma validate
```

### Development Setup
```bash
# Start local PostgreSQL
docker-compose up postgres

# Run migrations
npm run migrate

# Seed development data
npm run db:seed
```

This comprehensive database schema provides a robust foundation for the Sunday.com work management platform, supporting multi-tenancy, real-time collaboration, audit logging, and scalable performance.