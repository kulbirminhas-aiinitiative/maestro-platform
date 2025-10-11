# Sunday.com Database Administration Guide

## Executive Summary

This comprehensive guide covers the complete database administration strategy for Sunday.com, a modern work management platform. The database infrastructure is designed to handle enterprise-scale workloads with high availability, performance, and security requirements.

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Migration Management](#migration-management)
3. [Performance Optimization](#performance-optimization)
4. [Data Integrity & Security](#data-integrity--security)
5. [Backup & Recovery](#backup--recovery)
6. [Partitioning & Sharding](#partitioning--sharding)
7. [Monitoring & Maintenance](#monitoring--maintenance)
8. [Troubleshooting](#troubleshooting)
9. [Operational Procedures](#operational-procedures)

---

## Architecture Overview

### Database Stack

- **Primary Database**: PostgreSQL 15+
- **Cache Layer**: Redis 7+
- **Analytics**: ClickHouse
- **Search**: Elasticsearch
- **Object Storage**: Amazon S3

### Core Design Principles

1. **Multi-tenancy**: Organization-based data isolation
2. **Horizontal Scalability**: Partitioning and sharding support
3. **High Availability**: Master-slave replication with failover
4. **Performance**: Advanced indexing and query optimization
5. **Security**: Row-level security and encryption
6. **Compliance**: GDPR, SOC2, and HIPAA ready

### Database Schema Highlights

- **42 core tables** with proper relationships
- **UUID primary keys** for distributed systems
- **JSONB columns** for flexible data storage
- **Soft deletes** for data recovery
- **Audit trails** with automatic logging
- **Partitioned tables** for time-series data

---

## Migration Management

### Migration System

The database uses a sophisticated migration system with versioning, rollback capabilities, and integrity checking.

#### Key Features

- **Atomic migrations** with transaction support
- **Checksum verification** for integrity
- **Rollback support** with down scripts
- **Dependency tracking** and validation
- **Automated execution** with scheduling

#### Running Migrations

```bash
# Apply all pending migrations
python database/migration_manager.py migrate

# Apply to specific version
python database/migration_manager.py migrate --target=003

# Check migration status
python database/migration_manager.py status

# Rollback to previous version
python database/migration_manager.py rollback --target=002

# Validate migration integrity
python database/migration_manager.py validate

# Create new migration
python database/migration_manager.py create "add_user_preferences"
```

#### Migration Files Structure

```
database/
├── migrations/
│   ├── 001_init_schema.sql           # Core schema
│   ├── 002_advanced_indexes.sql      # Performance indexes
│   ├── 003_data_integrity.sql        # Constraints & triggers
│   └── 004_partitioning_sharding.sql # Scaling features
├── migration_manager.py              # Migration tool
└── backup/
    └── backup_manager.py             # Backup system
```

### Migration Best Practices

1. **Always test** migrations in development first
2. **Create backups** before major migrations
3. **Use transactions** for atomic operations
4. **Include rollback scripts** for complex changes
5. **Monitor performance** during migration execution

---

## Performance Optimization

### Indexing Strategy

The database implements a comprehensive indexing strategy with 70+ carefully designed indexes.

#### Index Categories

1. **Primary Indexes**: Core business operations
2. **Composite Indexes**: Multi-column queries
3. **Partial Indexes**: Filtered conditions
4. **Full-text Indexes**: Search capabilities
5. **JSONB Indexes**: Dynamic data queries
6. **Covering Indexes**: Include additional columns

#### Critical Performance Indexes

```sql
-- Board item queries (most frequent)
CREATE INDEX CONCURRENTLY idx_items_board_position
ON items(board_id, position) WHERE deleted_at IS NULL;

-- User access patterns
CREATE INDEX CONCURRENTLY idx_org_members_user_active
ON organization_members(user_id, organization_id)
WHERE status = 'active';

-- Full-text search
CREATE INDEX CONCURRENTLY idx_items_search
ON items USING GIN (to_tsvector('english', name || ' ' || COALESCE(description, '')))
WHERE deleted_at IS NULL;
```

### Query Optimization

#### Performance Monitoring

```bash
# Generate performance report
python database/performance/query_optimizer.py report --output=performance_report.json

# Real-time monitoring
python database/performance/query_optimizer.py monitor --duration=300

# Optimize specific query
python database/performance/query_optimizer.py optimize "SELECT * FROM items WHERE board_id = ?"
```

#### Key Metrics to Monitor

- **Query response time**: <50ms for 95% of queries
- **Cache hit ratio**: >95% for indexes, >90% for heap
- **Connection pool utilization**: <80%
- **Lock contention**: Minimal blocking locks
- **Table statistics freshness**: Updated weekly

### Performance Targets

| Metric | Target | Critical Threshold |
|--------|--------|--------------------|
| Query Response Time | <50ms (95%ile) | >200ms |
| Cache Hit Ratio | >95% | <90% |
| Connection Pool | <80% utilized | >95% |
| Disk I/O Wait | <10% | >25% |
| Concurrent Users | 100,000+ | N/A |

---

## Data Integrity & Security

### Validation Framework

Comprehensive data validation with triggers and constraints:

#### Key Validation Features

1. **Email format validation** with regex patterns
2. **Hierarchical integrity** for item relationships
3. **Dynamic validation** based on board column types
4. **Cross-reference checks** for foreign keys
5. **Business rule enforcement** via triggers

#### Security Implementation

```sql
-- Row Level Security example
CREATE POLICY organization_access_policy ON organizations
FOR ALL TO PUBLIC
USING (
    id IN (
        SELECT organization_id FROM organization_members
        WHERE user_id = current_setting('app.current_user_id')::UUID
        AND status = 'active'
    )
);
```

### Data Quality Monitoring

```sql
-- Check data quality issues
SELECT * FROM data_quality_issues;

-- Find orphaned records
SELECT * FROM orphaned_records;

-- Validate referential integrity
SELECT validate_item_data(board_id, item_data) FROM items LIMIT 100;
```

### Compliance Features

- **Audit trails** for all data changes
- **Data retention** policies with automated cleanup
- **Encryption at rest** with field-level encryption options
- **Access logging** with detailed activity tracking
- **GDPR compliance** with data export/deletion tools

---

## Backup & Recovery

### Backup Strategy

Multi-layered backup approach with encryption and compression:

#### Backup Types

1. **Full Backups**: Complete database dump (weekly)
2. **Incremental Backups**: WAL files since last backup (daily)
3. **Differential Backups**: Changes since last full backup
4. **Point-in-time Recovery**: Any moment in time within retention

#### Running Backups

```bash
# Create full backup
python database/backup/backup_manager.py backup --type=full

# Create incremental backup
python database/backup/backup_manager.py backup --type=incremental --base=full_20241201_020000

# List available backups
python database/backup/backup_manager.py list

# Verify backup integrity
python database/backup/backup_manager.py verify full_20241201_020000

# Restore from backup
python database/backup/backup_manager.py restore full_20241201_020000

# Point-in-time recovery
python database/backup/backup_manager.py restore full_20241201_020000 --time="2024-12-01T15:30:00"
```

#### Automated Scheduling

```bash
# Start backup scheduler daemon
python database/backup/backup_manager.py scheduler --daemon
```

**Default Schedule:**
- **Full backups**: Sundays at 2:00 AM
- **Incremental backups**: Daily at 2:00 AM (except Sunday)
- **Cleanup**: Monthly retention management

### Disaster Recovery

#### Recovery Time Objectives (RTO)

- **Database restore**: <30 minutes
- **Application recovery**: <15 minutes
- **Full system recovery**: <1 hour

#### Recovery Point Objectives (RPO)

- **Maximum data loss**: <5 minutes
- **Backup frequency**: Every 24 hours
- **WAL archiving**: Real-time

#### DR Procedures

1. **Automated failover** to standby server
2. **Data replication** across multiple regions
3. **Application-level failover** with load balancer
4. **Regular DR testing** monthly
5. **Documentation updates** quarterly

---

## Partitioning & Sharding

### Partitioning Strategy

Time-based partitioning for large tables:

#### Partitioned Tables

1. **activity_log**: Monthly partitions (24-month retention)
2. **automation_executions**: Monthly partitions (12-month retention)
3. **webhook_deliveries**: Monthly partitions (6-month retention)

#### Partition Management

```sql
-- Create monthly partitions automatically
SELECT create_monthly_partition('activity_log', '2024-12-01'::date);

-- Maintain partitions (run daily)
SELECT maintain_partitions();

-- Check partition health
SELECT * FROM check_partition_health();

-- View partition distribution
SELECT * FROM partition_monitoring;
```

### Sharding Strategy

Organization-based sharding for horizontal scaling:

#### Sharding Functions

```sql
-- Determine shard for organization
SELECT get_organization_shard('org-uuid');

-- View shard distribution
SELECT * FROM shard_load_distribution;

-- Check for cross-shard operations
SELECT validate_cross_shard_operation(ARRAY['org1-uuid', 'org2-uuid']);
```

#### Shard Rebalancing

When shard imbalance is detected:

1. **Identify hot shards** with high load
2. **Plan migration** of organizations
3. **Execute gradual migration** during low-traffic periods
4. **Verify data consistency** post-migration
5. **Update routing configuration**

---

## Monitoring & Maintenance

### Health Monitoring

#### Key Metrics Dashboard

```bash
# Database health check
SELECT checkDatabaseHealth();

# Connection status
SELECT * FROM pg_stat_activity WHERE state = 'active';

# Lock monitoring
SELECT * FROM pg_stat_activity WHERE wait_event IS NOT NULL;

# Replication lag
SELECT * FROM pg_stat_replication;
```

#### Automated Monitoring

Set up alerts for:

- **Query response time** > 200ms
- **Cache hit ratio** < 90%
- **Connection count** > 80% of max
- **Disk space** > 85% full
- **Replication lag** > 10 seconds

### Maintenance Tasks

#### Daily Tasks

1. **Backup verification** - Check backup integrity
2. **Performance monitoring** - Review slow queries
3. **Connection monitoring** - Check active connections
4. **Error log review** - Investigate any errors

#### Weekly Tasks

1. **Statistics update** - `ANALYZE` all tables
2. **Index usage review** - Identify unused indexes
3. **Query plan analysis** - Review execution plans
4. **Capacity planning** - Monitor growth trends

#### Monthly Tasks

1. **Vacuum operations** - Reclaim storage space
2. **Partition maintenance** - Create/drop partitions
3. **Security audit** - Review access patterns
4. **DR testing** - Test backup/restore procedures

---

## Troubleshooting

### Common Issues

#### Slow Queries

1. **Identify slow queries**:
   ```sql
   SELECT query, mean_exec_time, calls
   FROM pg_stat_statements
   ORDER BY mean_exec_time DESC LIMIT 10;
   ```

2. **Analyze execution plan**:
   ```sql
   EXPLAIN (ANALYZE, BUFFERS) SELECT ...;
   ```

3. **Check for missing indexes**:
   ```bash
   python database/performance/query_optimizer.py report
   ```

#### High CPU Usage

1. **Check active queries**:
   ```sql
   SELECT pid, query, state, query_start
   FROM pg_stat_activity
   WHERE state = 'active';
   ```

2. **Identify blocking locks**:
   ```sql
   SELECT * FROM pg_locks WHERE NOT granted;
   ```

3. **Monitor connection counts**:
   ```sql
   SELECT count(*) FROM pg_stat_activity;
   ```

#### Storage Issues

1. **Check table sizes**:
   ```sql
   SELECT schemaname, tablename, pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename))
   FROM pg_tables WHERE schemaname = 'public'
   ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
   ```

2. **Identify bloated tables**:
   ```sql
   SELECT * FROM tables_needing_vacuum;
   ```

3. **Run maintenance**:
   ```sql
   VACUUM ANALYZE;
   ```

---

## Operational Procedures

### Production Deployment

#### Pre-deployment Checklist

- [ ] Test migrations in staging
- [ ] Create full backup
- [ ] Review performance impact
- [ ] Prepare rollback plan
- [ ] Schedule maintenance window

#### Deployment Steps

1. **Enable maintenance mode**
2. **Create backup checkpoint**
3. **Run database migrations**
4. **Verify data integrity**
5. **Test application functionality**
6. **Disable maintenance mode**
7. **Monitor system health**

#### Post-deployment Monitoring

- Monitor query performance for 24 hours
- Check error rates and response times
- Verify backup completion
- Review access logs for anomalies

### Emergency Procedures

#### Database Outage

1. **Assess severity** and impact
2. **Check server status** and connectivity
3. **Review recent changes** and logs
4. **Initiate failover** if necessary
5. **Communicate status** to stakeholders
6. **Document incident** and resolution

#### Data Corruption

1. **Stop write operations** immediately
2. **Assess corruption scope**
3. **Restore from last good backup**
4. **Apply incremental changes** if possible
5. **Verify data integrity**
6. **Resume normal operations**

#### Performance Degradation

1. **Identify root cause** using monitoring tools
2. **Check for slow queries** and blocking locks
3. **Review recent configuration changes**
4. **Apply immediate fixes** (query kills, index creation)
5. **Plan long-term solutions**

---

## Contact & Support

### Team Contacts

- **Database Administrator**: [Your Name] - [email]
- **Platform Team**: [Team Email]
- **On-call Engineer**: [Phone/Pager]

### Documentation Updates

This guide should be reviewed and updated:

- **Monthly**: Performance metrics and thresholds
- **Quarterly**: Procedures and contact information
- **Annually**: Overall strategy and architecture

### Resources

- **Internal Wiki**: [URL]
- **Monitoring Dashboard**: [URL]
- **Incident Management**: [Tool/URL]
- **Change Management**: [Process/URL]

---

*Last Updated: December 2024*
*Next Review: March 2025*
*Document Version: 1.0*