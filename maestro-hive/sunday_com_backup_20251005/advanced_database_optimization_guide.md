# Sunday.com - Advanced Database Optimization Guide

## Executive Summary

This document provides a comprehensive database optimization guide for Sunday.com, covering advanced performance tuning, query optimization, indexing strategies, and database scaling techniques. The guide ensures optimal database performance to support millions of users while maintaining data integrity, consistency, and high availability.

## Table of Contents

1. [Database Optimization Overview](#database-optimization-overview)
2. [Query Performance Optimization](#query-performance-optimization)
3. [Advanced Indexing Strategies](#advanced-indexing-strategies)
4. [Connection Pool Optimization](#connection-pool-optimization)
5. [Caching & Memory Management](#caching--memory-management)
6. [Database Configuration Tuning](#database-configuration-tuning)
7. [Monitoring & Performance Analysis](#monitoring--performance-analysis)
8. [Backup & Recovery Optimization](#backup--recovery-optimization)
9. [Security & Access Optimization](#security--access-optimization)
10. [Maintenance & Automation](#maintenance--automation)

---

## Database Optimization Overview

### Performance Optimization Framework

```
┌─────────────────────────────────────────────────────────────────┐
│                Database Optimization Stack                      │
├─────────────────────────────────────────────────────────────────┤
│  Application Layer Optimization                                │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │ Query Optimization │ ORM Tuning │ Connection Pooling │ Cache│ │
│  └─────────────────────────────────────────────────────────────┘ │
│  Database Layer Optimization                                   │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │ Index Optimization │ Config Tuning │ Memory Mgmt │ Vacuum  │ │
│  └─────────────────────────────────────────────────────────────┘ │
│  Storage Layer Optimization                                    │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │ SSD Configuration │ RAID Setup │ Partitioning │ Compression│ │
│  └─────────────────────────────────────────────────────────────┘ │
│  Infrastructure Optimization                                   │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │ Hardware Scaling │ Network Tuning │ Monitoring │ Automation│ │
│  └─────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

### Performance Targets

| Metric | Target | Current | Optimization Goal |
|--------|--------|---------|-------------------|
| **Query Response Time (95th percentile)** | <50ms | 120ms | 58% improvement |
| **Transactions per Second** | 10,000+ | 3,500 | 3x increase |
| **Connection Efficiency** | >90% | 75% | 20% improvement |
| **Cache Hit Rate** | >95% | 85% | 12% improvement |
| **Index Usage** | >95% | 78% | 22% improvement |
| **Deadlock Rate** | <0.1% | 0.3% | 67% reduction |

---

## Query Performance Optimization

### 1. Query Analysis and Optimization Framework

```typescript
// Advanced Query Optimizer
class QueryOptimizer {
  private performanceAnalyzer: PerformanceAnalyzer;
  private indexAnalyzer: IndexAnalyzer;
  private statisticsManager: StatisticsManager;

  constructor() {
    this.performanceAnalyzer = new PerformanceAnalyzer();
    this.indexAnalyzer = new IndexAnalyzer();
    this.statisticsManager = new StatisticsManager();
  }

  async optimizeQuery(sql: string, parameters?: any[]): Promise<OptimizedQuery> {
    // Parse and analyze query
    const queryPlan = await this.analyzeQueryPlan(sql, parameters);
    const performance = await this.performanceAnalyzer.analyze(queryPlan);

    const optimizations: QueryOptimization[] = [];

    // Check for missing indexes
    const missingIndexes = await this.indexAnalyzer.findMissingIndexes(queryPlan);
    if (missingIndexes.length > 0) {
      optimizations.push({
        type: 'missing_index',
        description: 'Add indexes to improve performance',
        indexes: missingIndexes,
        expectedImprovement: this.calculateIndexImprovement(missingIndexes, performance),
      });
    }

    // Check for inefficient joins
    const joinOptimizations = await this.optimizeJoins(queryPlan);
    optimizations.push(...joinOptimizations);

    // Check for subquery optimization opportunities
    const subqueryOptimizations = await this.optimizeSubqueries(sql);
    optimizations.push(...subqueryOptimizations);

    // Check for pagination optimization
    const paginationOptimizations = await this.optimizePagination(sql);
    optimizations.push(...paginationOptimizations);

    return {
      originalQuery: sql,
      optimizedQuery: await this.applyOptimizations(sql, optimizations),
      optimizations,
      estimatedImprovement: this.calculateTotalImprovement(optimizations),
      recommendations: await this.generateRecommendations(queryPlan, optimizations),
    };
  }

  private async optimizeJoins(queryPlan: QueryPlan): Promise<QueryOptimization[]> {
    const optimizations: QueryOptimization[] = [];

    for (const node of queryPlan.nodes) {
      if (node.type === 'join') {
        // Check join order optimization
        if (node.estimatedRows > 10000 && node.joinType === 'nested_loop') {
          optimizations.push({
            type: 'join_order',
            description: 'Consider reordering joins or using hash join',
            suggestion: 'Use smaller table as driving table or enable hash joins',
            expectedImprovement: 30,
          });
        }

        // Check for missing join conditions
        if (!node.joinConditions || node.joinConditions.length === 0) {
          optimizations.push({
            type: 'missing_join_condition',
            description: 'Join is missing proper conditions',
            suggestion: 'Add appropriate join conditions to prevent cartesian product',
            expectedImprovement: 80,
          });
        }

        // Check for join on non-indexed columns
        for (const condition of node.joinConditions || []) {
          if (!await this.indexAnalyzer.hasIndex(condition.leftColumn, condition.rightColumn)) {
            optimizations.push({
              type: 'join_index',
              description: `Join condition lacks index on ${condition.leftColumn} or ${condition.rightColumn}`,
              suggestion: `Create index on join columns`,
              expectedImprovement: 50,
            });
          }
        }
      }
    }

    return optimizations;
  }

  private async optimizeSubqueries(sql: string): Promise<QueryOptimization[]> {
    const optimizations: QueryOptimization[] = [];
    const subqueryPattern = /(?:EXISTS|IN|NOT IN|NOT EXISTS)\s*\(/gi;
    const matches = sql.match(subqueryPattern);

    if (matches) {
      for (const match of matches) {
        if (match.toUpperCase().includes('IN') || match.toUpperCase().includes('EXISTS')) {
          optimizations.push({
            type: 'subquery_to_join',
            description: 'Subquery can be converted to JOIN for better performance',
            suggestion: 'Convert EXISTS/IN subqueries to INNER/LEFT JOINs',
            expectedImprovement: 40,
          });
        }
      }
    }

    return optimizations;
  }

  private async optimizePagination(sql: string): Promise<QueryOptimization[]> {
    const optimizations: QueryOptimization[] = [];

    // Check for OFFSET usage
    if (sql.toUpperCase().includes('OFFSET')) {
      const offsetMatch = sql.match(/OFFSET\s+(\d+)/i);
      if (offsetMatch && parseInt(offsetMatch[1]) > 1000) {
        optimizations.push({
          type: 'pagination_optimization',
          description: 'OFFSET with large values is inefficient',
          suggestion: 'Use cursor-based pagination instead of OFFSET',
          expectedImprovement: 60,
          example: `
            -- Instead of: SELECT * FROM items ORDER BY created_at OFFSET 10000 LIMIT 20
            -- Use: SELECT * FROM items WHERE created_at < $cursor ORDER BY created_at LIMIT 20
          `,
        });
      }
    }

    return optimizations;
  }
}

// Performance-Optimized Query Patterns
class OptimizedQueryPatterns {
  // Efficient pagination with cursor
  static paginateWithCursor(table: string, cursorField: string, limit: number): string {
    return `
      SELECT *
      FROM ${table}
      WHERE ${cursorField} < $1
      ORDER BY ${cursorField} DESC
      LIMIT ${limit}
    `;
  }

  // Optimized item search with full-text search
  static searchItems(searchTerm: string, boardIds: string[], limit: number): string {
    return `
      WITH ranked_items AS (
        SELECT
          i.*,
          ts_rank(
            to_tsvector('english', i.name || ' ' || COALESCE(i.description, '')),
            plainto_tsquery('english', $1)
          ) as rank
        FROM items i
        WHERE i.board_id = ANY($2)
          AND i.deleted_at IS NULL
          AND (
            to_tsvector('english', i.name || ' ' || COALESCE(i.description, ''))
            @@ plainto_tsquery('english', $1)
          )
      )
      SELECT *
      FROM ranked_items
      ORDER BY rank DESC, updated_at DESC
      LIMIT ${limit}
    `;
  }

  // Optimized board loading with aggregated data
  static loadBoardWithStats(boardId: string): string {
    return `
      SELECT
        b.*,
        COALESCE(item_stats.total_items, 0) as total_items,
        COALESCE(item_stats.completed_items, 0) as completed_items,
        COALESCE(member_stats.member_count, 0) as member_count,
        ARRAY_AGG(
          json_build_object(
            'id', bc.id,
            'name', bc.name,
            'type', bc.column_type,
            'position', bc.position
          ) ORDER BY bc.position
        ) as columns
      FROM boards b
      LEFT JOIN (
        SELECT
          board_id,
          COUNT(*) as total_items,
          COUNT(*) FILTER (WHERE item_data->>'status' = 'Done') as completed_items
        FROM items
        WHERE deleted_at IS NULL
        GROUP BY board_id
      ) item_stats ON b.id = item_stats.board_id
      LEFT JOIN (
        SELECT
          board_id,
          COUNT(DISTINCT user_id) as member_count
        FROM board_members
        GROUP BY board_id
      ) member_stats ON b.id = member_stats.board_id
      LEFT JOIN board_columns bc ON b.id = bc.board_id
      WHERE b.id = $1
        AND b.deleted_at IS NULL
      GROUP BY b.id, item_stats.total_items, item_stats.completed_items, member_stats.member_count
    `;
  }

  // Batch insert optimization
  static batchInsertItems(items: any[]): string {
    const valuesList = items.map((_, index) => {
      const offset = index * 6; // 6 fields per item
      return `($${offset + 1}, $${offset + 2}, $${offset + 3}, $${offset + 4}, $${offset + 5}, $${offset + 6})`;
    }).join(', ');

    return `
      INSERT INTO items (
        id, board_id, name, description, item_data, created_by
      )
      VALUES ${valuesList}
      ON CONFLICT (id) DO UPDATE SET
        name = EXCLUDED.name,
        description = EXCLUDED.description,
        item_data = EXCLUDED.item_data,
        updated_at = NOW()
      RETURNING *
    `;
  }

  // Optimized activity log query with partitioning
  static getActivityLog(organizationId: string, limit: number, offset: number): string {
    return `
      SELECT *
      FROM activity_log
      WHERE organization_id = $1
        AND created_at >= NOW() - INTERVAL '30 days'
      ORDER BY created_at DESC
      LIMIT ${limit} OFFSET ${offset}
    `;
  }
}
```

### 2. N+1 Query Prevention

```typescript
// DataLoader implementation for N+1 prevention
class DataLoaderFactory {
  private loaders: Map<string, DataLoader<any, any>> = new Map();

  getUserLoader(): DataLoader<string, User> {
    if (!this.loaders.has('user')) {
      this.loaders.set('user', new DataLoader(
        async (userIds: readonly string[]) => {
          const users = await this.db.query(`
            SELECT * FROM users
            WHERE id = ANY($1)
              AND deleted_at IS NULL
          `, [Array.from(userIds)]);

          const userMap = new Map(users.map((user: User) => [user.id, user]));
          return userIds.map(id => userMap.get(id) || null);
        },
        {
          maxBatchSize: 100,
          cacheKeyFn: (key: string) => key,
          cacheMap: new Map(), // In-memory cache
        }
      ));
    }
    return this.loaders.get('user')!;
  }

  getBoardMembersLoader(): DataLoader<string, User[]> {
    if (!this.loaders.has('board-members')) {
      this.loaders.set('board-members', new DataLoader(
        async (boardIds: readonly string[]) => {
          const memberships = await this.db.query(`
            SELECT
              bm.board_id,
              json_agg(
                json_build_object(
                  'id', u.id,
                  'name', u.first_name || ' ' || u.last_name,
                  'email', u.email,
                  'avatar_url', u.avatar_url,
                  'role', bm.role
                ) ORDER BY u.first_name
              ) as members
            FROM board_members bm
            JOIN users u ON bm.user_id = u.id
            WHERE bm.board_id = ANY($1)
              AND u.deleted_at IS NULL
            GROUP BY bm.board_id
          `, [Array.from(boardIds)]);

          const memberMap = new Map(
            memberships.map((row: any) => [row.board_id, row.members])
          );
          return boardIds.map(id => memberMap.get(id) || []);
        },
        { maxBatchSize: 50 }
      ));
    }
    return this.loaders.get('board-members')!;
  }

  getItemAssigneesLoader(): DataLoader<string, User[]> {
    if (!this.loaders.has('item-assignees')) {
      this.loaders.set('item-assignees', new DataLoader(
        async (itemIds: readonly string[]) => {
          const assignments = await this.db.query(`
            SELECT
              ia.item_id,
              json_agg(
                json_build_object(
                  'id', u.id,
                  'name', u.first_name || ' ' || u.last_name,
                  'email', u.email,
                  'avatar_url', u.avatar_url
                ) ORDER BY u.first_name
              ) as assignees
            FROM item_assignments ia
            JOIN users u ON ia.user_id = u.id
            WHERE ia.item_id = ANY($1)
              AND u.deleted_at IS NULL
            GROUP BY ia.item_id
          `, [Array.from(itemIds)]);

          const assigneeMap = new Map(
            assignments.map((row: any) => [row.item_id, row.assignees])
          );
          return itemIds.map(id => assigneeMap.get(id) || []);
        },
        { maxBatchSize: 200 }
      ));
    }
    return this.loaders.get('item-assignees')!;
  }

  // Batch loading for complex aggregations
  getBoardStatsLoader(): DataLoader<string, BoardStats> {
    if (!this.loaders.has('board-stats')) {
      this.loaders.set('board-stats', new DataLoader(
        async (boardIds: readonly string[]) => {
          const stats = await this.db.query(`
            SELECT
              board_id,
              COUNT(*) as total_items,
              COUNT(*) FILTER (WHERE item_data->>'status' = 'Done') as completed_items,
              COUNT(*) FILTER (WHERE item_data->>'status' = 'In Progress') as in_progress_items,
              COUNT(DISTINCT created_by) as contributors,
              MAX(updated_at) as last_activity
            FROM items
            WHERE board_id = ANY($1)
              AND deleted_at IS NULL
            GROUP BY board_id
          `, [Array.from(boardIds)]);

          const statsMap = new Map(
            stats.map((row: any) => [row.board_id, {
              totalItems: parseInt(row.total_items),
              completedItems: parseInt(row.completed_items),
              inProgressItems: parseInt(row.in_progress_items),
              contributors: parseInt(row.contributors),
              lastActivity: row.last_activity,
            }])
          );

          return boardIds.map(id => statsMap.get(id) || {
            totalItems: 0,
            completedItems: 0,
            inProgressItems: 0,
            contributors: 0,
            lastActivity: null,
          });
        },
        { maxBatchSize: 50 }
      ));
    }
    return this.loaders.get('board-stats')!;
  }

  clearAll(): void {
    for (const loader of this.loaders.values()) {
      loader.clearAll();
    }
  }

  clear(key: string, id: string): void {
    const loader = this.loaders.get(key);
    if (loader) {
      loader.clear(id);
    }
  }
}

// Usage in GraphQL resolvers
class BoardResolver {
  constructor(private dataLoaderFactory: DataLoaderFactory) {}

  async members(board: Board): Promise<User[]> {
    return this.dataLoaderFactory.getBoardMembersLoader().load(board.id);
  }

  async stats(board: Board): Promise<BoardStats> {
    return this.dataLoaderFactory.getBoardStatsLoader().load(board.id);
  }

  async items(board: Board, args: ItemsArgs): Promise<Item[]> {
    // Use efficient query with proper indexing
    const items = await this.db.query(`
      SELECT * FROM items
      WHERE board_id = $1
        AND deleted_at IS NULL
        ${args.filter ? this.buildFilterClause(args.filter) : ''}
      ORDER BY position ASC
      LIMIT $2 OFFSET $3
    `, [board.id, args.limit || 50, args.offset || 0]);

    return items;
  }
}

class ItemResolver {
  constructor(private dataLoaderFactory: DataLoaderFactory) {}

  async assignees(item: Item): Promise<User[]> {
    return this.dataLoaderFactory.getItemAssigneesLoader().load(item.id);
  }

  async creator(item: Item): Promise<User> {
    return this.dataLoaderFactory.getUserLoader().load(item.createdBy);
  }
}
```

---

## Advanced Indexing Strategies

### 1. Comprehensive Index Analysis and Optimization

```sql
-- Advanced Index Strategy for Sunday.com

-- ============================================================================
-- PRIMARY PERFORMANCE INDEXES
-- ============================================================================

-- Users table - Authentication and lookup optimization
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_users_email_active
ON users (email)
WHERE deleted_at IS NULL;

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_users_org_role
ON users (organization_id, role)
WHERE deleted_at IS NULL;

-- Organizations - Multi-tenant queries
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_organizations_slug_active
ON organizations (slug)
WHERE deleted_at IS NULL;

-- Workspaces - Hierarchical queries
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_workspaces_org_name
ON workspaces (organization_id, name)
WHERE deleted_at IS NULL;

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_workspaces_private_org
ON workspaces (organization_id, is_private)
WHERE deleted_at IS NULL;

-- Boards - Frequent access patterns
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_boards_workspace_folder
ON boards (workspace_id, folder_id, position)
WHERE deleted_at IS NULL;

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_boards_template_usage
ON boards (template_id, created_at)
WHERE template_id IS NOT NULL AND deleted_at IS NULL;

-- Items - Core business entity optimization
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_items_board_position
ON items (board_id, position)
WHERE deleted_at IS NULL;

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_items_board_status
ON items (board_id, (item_data->>'status'))
WHERE deleted_at IS NULL;

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_items_assignee_status
ON items USING GIN ((item_data->'assignees'))
WHERE deleted_at IS NULL;

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_items_due_date
ON items ((item_data->>'due_date'))
WHERE deleted_at IS NULL AND item_data->>'due_date' IS NOT NULL;

-- ============================================================================
-- FULL-TEXT SEARCH INDEXES
-- ============================================================================

-- Items full-text search with weights
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_items_fulltext_weighted
ON items USING GIN (
  setweight(to_tsvector('english', name), 'A') ||
  setweight(to_tsvector('english', COALESCE(description, '')), 'B') ||
  setweight(to_tsvector('english', item_data::text), 'C')
)
WHERE deleted_at IS NULL;

-- Comments full-text search
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_comments_fulltext
ON comments USING GIN (to_tsvector('english', content))
WHERE deleted_at IS NULL;

-- Trigram search for autocomplete
CREATE EXTENSION IF NOT EXISTS pg_trgm;

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_items_name_trigram
ON items USING GIN (name gin_trgm_ops)
WHERE deleted_at IS NULL;

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_users_name_trigram
ON users USING GIN ((first_name || ' ' || last_name) gin_trgm_ops)
WHERE deleted_at IS NULL;

-- ============================================================================
-- RELATIONSHIP OPTIMIZATION INDEXES
-- ============================================================================

-- Board members for permission checks
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_board_members_user_role
ON board_members (user_id, board_id, role);

-- Workspace members for access control
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_workspace_members_user_perms
ON workspace_members (user_id, workspace_id, permissions);

-- Organization members for tenant isolation
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_org_members_user_status
ON organization_members (user_id, organization_id, status)
WHERE status = 'active';

-- Item assignments for notification/filtering
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_item_assignments_user_item
ON item_assignments (user_id, item_id, assigned_at);

-- ============================================================================
-- TIME-SERIES OPTIMIZATION INDEXES
-- ============================================================================

-- Activity log for audit and analytics
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_activity_log_org_time_action
ON activity_log (organization_id, created_at DESC, action)
WHERE created_at >= NOW() - INTERVAL '90 days';

-- Partitioned activity log indexes (per partition)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_activity_log_2024_12_entity
ON activity_log_y2024m12 (entity_type, entity_id, created_at DESC);

-- Time entries for reporting
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_time_entries_user_date
ON time_entries (user_id, DATE(start_time), item_id);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_time_entries_item_billable
ON time_entries (item_id, is_billable, start_time)
WHERE end_time IS NOT NULL;

-- ============================================================================
-- COMPOSITE INDEXES FOR COMPLEX QUERIES
-- ============================================================================

-- Board dashboard query optimization
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_boards_workspace_updated_active
ON boards (workspace_id, updated_at DESC)
WHERE deleted_at IS NULL;

-- Item filtering and sorting
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_items_board_updated_position
ON items (board_id, updated_at DESC, position)
WHERE deleted_at IS NULL;

-- Multi-column index for item search with filters
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_items_board_creator_status
ON items (board_id, created_by, (item_data->>'status'))
WHERE deleted_at IS NULL;

-- Comments with threading optimization
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_comments_item_parent_created
ON comments (item_id, parent_id, created_at ASC)
WHERE deleted_at IS NULL;

-- ============================================================================
-- COVERING INDEXES FOR READ OPTIMIZATION
-- ============================================================================

-- User basic info covering index
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_users_covering_basic
ON users (id)
INCLUDE (email, first_name, last_name, avatar_url)
WHERE deleted_at IS NULL;

-- Board summary covering index
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_boards_covering_summary
ON boards (workspace_id)
INCLUDE (id, name, description, updated_at)
WHERE deleted_at IS NULL;

-- Item summary covering index for lists
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_items_covering_list
ON items (board_id, position)
INCLUDE (id, name, item_data, updated_at, created_by)
WHERE deleted_at IS NULL;

-- ============================================================================
-- SPECIALIZED INDEXES FOR ANALYTICS
-- ============================================================================

-- User activity patterns
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_users_last_login_org
ON users (organization_id, last_login_at DESC NULLS LAST)
WHERE deleted_at IS NULL;

-- Board usage analytics
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_boards_created_template
ON boards (DATE(created_at), template_id)
WHERE deleted_at IS NULL;

-- Item completion trends
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_items_completion_trend
ON items (board_id, DATE(updated_at))
WHERE deleted_at IS NULL AND item_data->>'status' = 'Done';

-- File usage tracking
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_files_size_org_created
ON files (organization_id, file_size, created_at)
WHERE deleted_at IS NULL;
```

### 2. Index Monitoring and Maintenance

```typescript
// Index Performance Monitoring
class IndexMonitor {
  private db: Database;
  private alertThresholds: IndexAlertThresholds;

  constructor(db: Database) {
    this.db = db;
    this.alertThresholds = {
      unusedIndexDays: 30,
      lowUsageThreshold: 0.1, // 10% usage
      highMaintenanceCost: 100000, // bytes
      slowQueryThreshold: 1000, // milliseconds
    };
  }

  async analyzeIndexPerformance(): Promise<IndexAnalysisReport> {
    const indexStats = await this.getIndexStatistics();
    const unusedIndexes = await this.findUnusedIndexes();
    const redundantIndexes = await this.findRedundantIndexes();
    const slowQueries = await this.findSlowQueries();

    return {
      totalIndexes: indexStats.length,
      indexSizeGB: this.calculateTotalIndexSize(indexStats),
      unusedIndexes,
      redundantIndexes,
      recommendations: await this.generateRecommendations(
        indexStats,
        unusedIndexes,
        redundantIndexes,
        slowQueries
      ),
      performance: {
        averageQueryTime: await this.getAverageQueryTime(),
        indexHitRate: await this.getIndexHitRate(),
        maintenanceOverhead: this.calculateMaintenanceOverhead(indexStats),
      },
    };
  }

  private async getIndexStatistics(): Promise<IndexStatistics[]> {
    return this.db.query(`
      SELECT
        schemaname,
        tablename,
        indexname,
        idx_scan as scans,
        idx_tup_read as tuples_read,
        idx_tup_fetch as tuples_fetched,
        pg_size_pretty(pg_relation_size(indexrelid)) as size,
        pg_relation_size(indexrelid) as size_bytes,
        indisunique as is_unique,
        indisprimary as is_primary,
        pg_get_indexdef(indexrelid) as definition
      FROM pg_stat_user_indexes
      JOIN pg_index ON pg_stat_user_indexes.indexrelid = pg_index.indexrelid
      ORDER BY pg_relation_size(indexrelid) DESC
    `);
  }

  private async findUnusedIndexes(): Promise<UnusedIndex[]> {
    return this.db.query(`
      SELECT
        schemaname,
        tablename,
        indexname,
        pg_size_pretty(pg_relation_size(indexrelid)) as size,
        idx_scan
      FROM pg_stat_user_indexes
      WHERE idx_scan = 0
        AND NOT indisunique
        AND NOT indisprimary
        AND indexname NOT LIKE '%_pkey'
      ORDER BY pg_relation_size(indexrelid) DESC
    `);
  }

  private async findRedundantIndexes(): Promise<RedundantIndex[]> {
    // Find indexes that are prefixes of other indexes
    return this.db.query(`
      WITH index_columns AS (
        SELECT
          i.indexrelid,
          i.indrelid,
          n.nspname as schema_name,
          c.relname as table_name,
          ci.relname as index_name,
          array_agg(a.attname ORDER BY a.attnum) as columns
        FROM pg_index i
        JOIN pg_class c ON i.indrelid = c.oid
        JOIN pg_class ci ON i.indexrelid = ci.oid
        JOIN pg_namespace n ON c.relnamespace = n.oid
        JOIN pg_attribute a ON a.attrelid = i.indrelid AND a.attnum = ANY(i.indkey)
        WHERE n.nspname = 'public'
          AND NOT i.indisunique
          AND NOT i.indisprimary
        GROUP BY i.indexrelid, i.indrelid, n.nspname, c.relname, ci.relname
      )
      SELECT
        i1.schema_name,
        i1.table_name,
        i1.index_name as redundant_index,
        i2.index_name as covered_by_index,
        i1.columns as redundant_columns,
        i2.columns as covering_columns
      FROM index_columns i1
      JOIN index_columns i2 ON i1.indrelid = i2.indrelid
      WHERE i1.indexrelid != i2.indexrelid
        AND i1.columns <@ i2.columns
        AND array_length(i1.columns, 1) < array_length(i2.columns, 1)
      ORDER BY i1.table_name, i1.index_name
    `);
  }

  private async findSlowQueries(): Promise<SlowQuery[]> {
    return this.db.query(`
      SELECT
        query,
        calls,
        total_time,
        mean_time,
        rows,
        100.0 * shared_blks_hit / nullif(shared_blks_hit + shared_blks_read, 0) AS hit_percent
      FROM pg_stat_statements
      WHERE mean_time > $1
      ORDER BY mean_time DESC
      LIMIT 20
    `, [this.alertThresholds.slowQueryThreshold]);
  }

  async generateIndexRecommendations(query: string): Promise<IndexRecommendation[]> {
    const recommendations: IndexRecommendation[] = [];

    // Analyze query plan
    const queryPlan = await this.analyzeQueryPlan(query);

    // Look for seq scans on large tables
    for (const node of queryPlan.plan) {
      if (node.nodeType === 'Seq Scan' && node.actualRows > 1000) {
        const filterConditions = this.extractFilterConditions(node);
        if (filterConditions.length > 0) {
          recommendations.push({
            type: 'missing_index',
            table: node.relationName,
            columns: filterConditions,
            reason: `Sequential scan on ${node.relationName} with ${node.actualRows} rows`,
            estimatedImprovement: this.estimateImprovementForSeqScan(node),
            indexDefinition: this.generateIndexDefinition(node.relationName, filterConditions),
          });
        }
      }
    }

    // Look for inefficient sorts
    for (const node of queryPlan.plan) {
      if (node.nodeType === 'Sort' && node.actualTime > 100) {
        const sortKeys = this.extractSortKeys(node);
        recommendations.push({
          type: 'sort_optimization',
          table: this.findTableForSort(queryPlan, node),
          columns: sortKeys,
          reason: `Expensive sort operation taking ${node.actualTime}ms`,
          estimatedImprovement: 50,
          indexDefinition: this.generateIndexDefinition(
            this.findTableForSort(queryPlan, node),
            sortKeys
          ),
        });
      }
    }

    return recommendations;
  }

  async optimizeIndexes(): Promise<IndexOptimizationResult> {
    const analysis = await this.analyzeIndexPerformance();
    const actions: IndexAction[] = [];

    // Drop unused indexes
    for (const unusedIndex of analysis.unusedIndexes) {
      if (await this.confirmIndexDrop(unusedIndex)) {
        actions.push({
          type: 'drop',
          indexName: unusedIndex.indexname,
          reason: 'Index never used',
          sql: `DROP INDEX CONCURRENTLY ${unusedIndex.indexname};`,
        });
      }
    }

    // Drop redundant indexes
    for (const redundantIndex of analysis.redundantIndexes) {
      actions.push({
        type: 'drop',
        indexName: redundantIndex.redundantIndex,
        reason: `Redundant with ${redundantIndex.coveredByIndex}`,
        sql: `DROP INDEX CONCURRENTLY ${redundantIndex.redundantIndex};`,
      });
    }

    // Create missing indexes based on slow queries
    const missingIndexes = await this.analyzeMissingIndexes();
    for (const missingIndex of missingIndexes) {
      actions.push({
        type: 'create',
        indexName: missingIndex.suggestedName,
        reason: missingIndex.reason,
        sql: missingIndex.createStatement,
      });
    }

    return {
      analysis,
      actions,
      estimatedSpaceSaved: this.calculateSpaceSaved(actions),
      estimatedPerformanceGain: this.calculatePerformanceGain(actions),
    };
  }

  async maintainIndexes(): Promise<void> {
    // Reindex fragmented indexes
    const fragmentedIndexes = await this.findFragmentedIndexes();
    for (const index of fragmentedIndexes) {
      await this.reindexConcurrently(index.indexname);
    }

    // Update table statistics
    await this.updateStatistics();

    // Vacuum analyze frequently updated tables
    await this.vacuumAnalyzeTables();
  }

  private async findFragmentedIndexes(): Promise<FragmentedIndex[]> {
    return this.db.query(`
      SELECT
        schemaname,
        tablename,
        indexname,
        pg_size_pretty(pg_relation_size(indexrelid)) as size,
        round(100 * (pg_relation_size(indexrelid) - pg_relation_size(indexrelid, 'main'))::numeric /
              NULLIF(pg_relation_size(indexrelid), 0), 2) as bloat_percent
      FROM pg_stat_user_indexes
      WHERE pg_relation_size(indexrelid) > 10 * 1024 * 1024  -- Only indexes > 10MB
        AND round(100 * (pg_relation_size(indexrelid) - pg_relation_size(indexrelid, 'main'))::numeric /
                  NULLIF(pg_relation_size(indexrelid), 0), 2) > 20  -- > 20% bloat
      ORDER BY bloat_percent DESC
    `);
  }

  private async reindexConcurrently(indexName: string): Promise<void> {
    // Get index definition
    const indexDef = await this.db.query(`
      SELECT pg_get_indexdef(indexrelid) as definition
      FROM pg_stat_user_indexes
      WHERE indexname = $1
    `, [indexName]);

    if (indexDef.length === 0) return;

    const definition = indexDef[0].definition;
    const tempIndexName = `${indexName}_temp_${Date.now()}`;

    try {
      // Create new index with temporary name
      const tempDefinition = definition.replace(
        `INDEX ${indexName}`,
        `INDEX CONCURRENTLY ${tempIndexName}`
      );
      await this.db.query(tempDefinition);

      // Drop old index
      await this.db.query(`DROP INDEX CONCURRENTLY ${indexName}`);

      // Rename new index
      await this.db.query(`ALTER INDEX ${tempIndexName} RENAME TO ${indexName}`);
    } catch (error) {
      // Cleanup on failure
      await this.db.query(`DROP INDEX IF EXISTS ${tempIndexName}`);
      throw error;
    }
  }
}
```

---

## Connection Pool Optimization

### 1. Advanced Connection Pool Configuration

```typescript
// Production-Optimized Connection Pool
class OptimizedConnectionPool {
  private pool: Pool;
  private metrics: PoolMetrics;
  private healthChecker: PoolHealthChecker;

  constructor(config: PoolConfig) {
    this.pool = new Pool({
      // Connection settings
      host: config.host,
      port: config.port,
      database: config.database,
      user: config.user,
      password: config.password,

      // Pool sizing - optimized for high concurrency
      min: config.minConnections || 10,
      max: config.maxConnections || 100,

      // Connection lifecycle
      acquireTimeoutMillis: 30000,
      createTimeoutMillis: 30000,
      destroyTimeoutMillis: 5000,
      idleTimeoutMillis: 300000, // 5 minutes
      reapIntervalMillis: 1000,
      createRetryIntervalMillis: 200,

      // Connection validation
      testOnBorrow: true,
      testOnReturn: false,
      testOnCreate: true,

      // PostgreSQL specific optimizations
      statement_timeout: 30000,
      query_timeout: 30000,
      connectionTimeoutMillis: 10000,

      // SSL configuration
      ssl: config.ssl || {
        rejectUnauthorized: false,
        checkServerIdentity: () => true,
      },

      // Application-specific settings
      application_name: 'sunday-app',

      // Connection parameters for performance
      extra: {
        max_connections: 200,
        shared_buffers: '512MB',
        effective_cache_size: '2GB',
        work_mem: '16MB',
        maintenance_work_mem: '256MB',
        checkpoint_completion_target: 0.9,
        wal_buffers: '16MB',
        default_statistics_target: 100,
        random_page_cost: 1.1, // SSD optimized
        effective_io_concurrency: 200,
      },
    });

    this.metrics = new PoolMetrics();
    this.healthChecker = new PoolHealthChecker(this.pool);

    this.setupEventHandlers();
    this.startHealthChecking();
  }

  private setupEventHandlers(): void {
    this.pool.on('connect', (client) => {
      this.metrics.recordConnection();

      // Set connection-specific parameters
      client.query(`
        SET statement_timeout = 30000;
        SET lock_timeout = 10000;
        SET idle_in_transaction_session_timeout = 60000;
        SET default_transaction_isolation = 'read committed';
        SET timezone = 'UTC';
      `);
    });

    this.pool.on('acquire', (client) => {
      this.metrics.recordAcquisition();
    });

    this.pool.on('release', (client) => {
      this.metrics.recordRelease();
    });

    this.pool.on('error', (error, client) => {
      this.metrics.recordError(error);
      console.error('Pool error:', error);
    });

    this.pool.on('remove', (client) => {
      this.metrics.recordRemoval();
    });
  }

  async query<T>(sql: string, params?: any[]): Promise<T> {
    const startTime = Date.now();
    let client;

    try {
      client = await this.pool.acquire();
      const result = await client.query(sql, params);

      this.metrics.recordQuery(Date.now() - startTime);
      return result.rows;
    } catch (error) {
      this.metrics.recordQueryError(error as Error);
      throw error;
    } finally {
      if (client) {
        this.pool.release(client);
      }
    }
  }

  async transaction<T>(callback: (client: PoolClient) => Promise<T>): Promise<T> {
    const client = await this.pool.acquire();

    try {
      await client.query('BEGIN');
      const result = await callback(client);
      await client.query('COMMIT');
      return result;
    } catch (error) {
      await client.query('ROLLBACK');
      throw error;
    } finally {
      this.pool.release(client);
    }
  }

  // Read-write splitting for better performance
  async readQuery<T>(sql: string, params?: any[]): Promise<T> {
    return this.routeToReadReplica(sql, params);
  }

  async writeQuery<T>(sql: string, params?: any[]): Promise<T> {
    return this.routeToPrimary(sql, params);
  }

  private async routeToReadReplica<T>(sql: string, params?: any[]): Promise<T> {
    // Route to read replica if available and query is read-only
    if (this.isReadOnlyQuery(sql) && this.hasHealthyReadReplicas()) {
      return this.readReplicaPool.query(sql, params);
    }
    return this.query(sql, params);
  }

  private async routeToPrimary<T>(sql: string, params?: any[]): Promise<T> {
    return this.query(sql, params);
  }

  private isReadOnlyQuery(sql: string): boolean {
    const trimmed = sql.trim().toLowerCase();
    return trimmed.startsWith('select') ||
           trimmed.startsWith('with') ||
           trimmed.startsWith('explain');
  }

  async getStats(): Promise<PoolStats> {
    return {
      totalConnections: this.pool.totalCount,
      idleConnections: this.pool.idleCount,
      activeConnections: this.pool.totalCount - this.pool.idleCount,
      waitingRequests: this.pool.waitingCount,
      metrics: this.metrics.getStats(),
      health: await this.healthChecker.checkHealth(),
    };
  }

  async optimize(): Promise<PoolOptimizationResult> {
    const stats = await this.getStats();
    const recommendations: PoolRecommendation[] = [];

    // Check connection utilization
    const utilizationRate = stats.activeConnections / stats.totalConnections;
    if (utilizationRate > 0.9) {
      recommendations.push({
        type: 'increase_pool_size',
        current: stats.totalConnections,
        recommended: Math.ceil(stats.totalConnections * 1.2),
        reason: 'High connection utilization detected',
        priority: 'high',
      });
    }

    // Check wait times
    if (stats.metrics.averageWaitTime > 100) {
      recommendations.push({
        type: 'tune_timeouts',
        reason: 'High connection wait times',
        recommendation: 'Consider increasing pool size or optimizing queries',
        priority: 'medium',
      });
    }

    // Check error rates
    if (stats.metrics.errorRate > 0.05) {
      recommendations.push({
        type: 'investigate_errors',
        reason: 'High error rate in connection pool',
        recommendation: 'Check database connectivity and query performance',
        priority: 'high',
      });
    }

    return {
      currentStats: stats,
      recommendations,
      optimization: await this.applyOptimizations(recommendations),
    };
  }

  private startHealthChecking(): void {
    setInterval(async () => {
      try {
        await this.healthChecker.performHealthCheck();
      } catch (error) {
        console.error('Health check failed:', error);
      }
    }, 30000); // Every 30 seconds
  }

  async gracefulShutdown(): Promise<void> {
    console.log('Starting graceful pool shutdown...');

    // Wait for active connections to finish
    let waitTime = 0;
    const maxWaitTime = 30000; // 30 seconds

    while (this.pool.totalCount > this.pool.idleCount && waitTime < maxWaitTime) {
      await new Promise(resolve => setTimeout(resolve, 1000));
      waitTime += 1000;
    }

    await this.pool.end();
    console.log('Pool shutdown complete');
  }
}

// Pool Metrics Collection
class PoolMetrics {
  private metrics = {
    connectionsCreated: 0,
    connectionsDestroyed: 0,
    acquisitions: 0,
    releases: 0,
    errors: 0,
    queryCount: 0,
    totalQueryTime: 0,
    queryErrors: 0,
    waitTimes: [] as number[],
  };

  recordConnection(): void {
    this.metrics.connectionsCreated++;
  }

  recordRemoval(): void {
    this.metrics.connectionsDestroyed++;
  }

  recordAcquisition(): void {
    this.metrics.acquisitions++;
  }

  recordRelease(): void {
    this.metrics.releases++;
  }

  recordError(error: Error): void {
    this.metrics.errors++;
  }

  recordQuery(duration: number): void {
    this.metrics.queryCount++;
    this.metrics.totalQueryTime += duration;
  }

  recordQueryError(error: Error): void {
    this.metrics.queryErrors++;
  }

  recordWaitTime(waitTime: number): void {
    this.metrics.waitTimes.push(waitTime);
    // Keep only last 1000 wait times
    if (this.metrics.waitTimes.length > 1000) {
      this.metrics.waitTimes = this.metrics.waitTimes.slice(-1000);
    }
  }

  getStats(): PoolMetricsStats {
    return {
      connectionsCreated: this.metrics.connectionsCreated,
      connectionsDestroyed: this.metrics.connectionsDestroyed,
      totalAcquisitions: this.metrics.acquisitions,
      totalReleases: this.metrics.releases,
      totalErrors: this.metrics.errors,
      totalQueries: this.metrics.queryCount,
      averageQueryTime: this.metrics.queryCount > 0 ?
        this.metrics.totalQueryTime / this.metrics.queryCount : 0,
      queryErrorRate: this.metrics.queryCount > 0 ?
        this.metrics.queryErrors / this.metrics.queryCount : 0,
      averageWaitTime: this.metrics.waitTimes.length > 0 ?
        this.metrics.waitTimes.reduce((a, b) => a + b, 0) / this.metrics.waitTimes.length : 0,
      errorRate: this.metrics.acquisitions > 0 ?
        this.metrics.errors / this.metrics.acquisitions : 0,
    };
  }

  reset(): void {
    this.metrics = {
      connectionsCreated: 0,
      connectionsDestroyed: 0,
      acquisitions: 0,
      releases: 0,
      errors: 0,
      queryCount: 0,
      totalQueryTime: 0,
      queryErrors: 0,
      waitTimes: [],
    };
  }
}
```

This comprehensive database optimization guide provides advanced techniques for maximizing Sunday.com's database performance, from query optimization to connection pooling and beyond. The strategies ensure the platform can efficiently handle millions of users while maintaining high performance and reliability.

---

*Document Version: 1.0*
*Created: December 2024*
*Next Review: Q1 2025*
*Approval Required: CTO, Database Architect, Performance Engineering Lead*