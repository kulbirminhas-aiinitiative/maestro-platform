#!/usr/bin/env python3
"""
Sunday.com Database Query Optimizer

Advanced query performance monitoring, analysis, and optimization system
for PostgreSQL databases. Provides real-time monitoring, slow query analysis,
index recommendations, and automated performance tuning.

Features:
- Real-time query performance monitoring
- Slow query analysis and optimization recommendations
- Index usage analysis and recommendations
- Table statistics and maintenance suggestions
- Query plan analysis and optimization hints
- Automated performance reporting
"""

import os
import sys
import time
import json
import logging
import argparse
import datetime
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict
from collections import defaultdict
import psycopg2
from psycopg2.extras import RealDictCursor
import matplotlib.pyplot as plt
import pandas as pd
from tabulate import tabulate

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('query_optimizer.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

@dataclass
class QueryMetrics:
    """Query performance metrics"""
    query_hash: str
    query_text: str
    calls: int
    total_time: float
    mean_time: float
    min_time: float
    max_time: float
    stddev_time: float
    rows: int
    shared_blks_hit: int
    shared_blks_read: int
    shared_blks_dirtied: int
    temp_blks_read: int
    temp_blks_written: int
    first_seen: datetime.datetime
    last_seen: datetime.datetime

@dataclass
class IndexMetrics:
    """Index usage metrics"""
    schema_name: str
    table_name: str
    index_name: str
    idx_scan: int
    idx_tup_read: int
    idx_tup_fetch: int
    size_bytes: int
    is_unique: bool
    is_primary: bool
    columns: List[str]

@dataclass
class TableMetrics:
    """Table statistics and metrics"""
    schema_name: str
    table_name: str
    n_tup_ins: int
    n_tup_upd: int
    n_tup_del: int
    n_live_tup: int
    n_dead_tup: int
    seq_scan: int
    seq_tup_read: int
    idx_scan: int
    idx_tup_fetch: int
    heap_blks_read: int
    heap_blks_hit: int
    size_bytes: int
    last_vacuum: Optional[datetime.datetime]
    last_autovacuum: Optional[datetime.datetime]
    last_analyze: Optional[datetime.datetime]
    last_autoanalyze: Optional[datetime.datetime]

class DatabaseConnection:
    """Database connection management"""

    def __init__(self, connection_string: str):
        self.connection_string = connection_string
        self.connection = None

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()

    def connect(self):
        """Establish database connection"""
        try:
            self.connection = psycopg2.connect(
                self.connection_string,
                cursor_factory=RealDictCursor
            )
            self.connection.autocommit = True
            logger.info("Connected to database successfully")
        except Exception as e:
            logger.error(f"Failed to connect to database: {e}")
            raise

    def disconnect(self):
        """Close database connection"""
        if self.connection:
            self.connection.close()
            logger.info("Database connection closed")

    def execute_query(self, query: str, params: tuple = None) -> List[Dict]:
        """Execute query and return results"""
        with self.connection.cursor() as cursor:
            cursor.execute(query, params)
            if cursor.description:
                return [dict(row) for row in cursor.fetchall()]
            return []

class QueryAnalyzer:
    """Query performance analyzer"""

    def __init__(self, db_connection: DatabaseConnection):
        self.db = db_connection

    def get_slow_queries(self, min_duration_ms: float = 100, limit: int = 50) -> List[QueryMetrics]:
        """Get slow queries from pg_stat_statements"""
        query = """
        SELECT
            queryid::text as query_hash,
            query as query_text,
            calls,
            total_exec_time as total_time,
            mean_exec_time as mean_time,
            min_exec_time as min_time,
            max_exec_time as max_time,
            stddev_exec_time as stddev_time,
            rows,
            shared_blks_hit,
            shared_blks_read,
            shared_blks_dirtied,
            temp_blks_read,
            temp_blks_written,
            stats_since as first_seen,
            stats_since as last_seen
        FROM pg_stat_statements
        WHERE mean_exec_time > %s
        ORDER BY mean_exec_time DESC
        LIMIT %s
        """

        results = self.db.execute_query(query, (min_duration_ms, limit))
        return [QueryMetrics(**row) for row in results]

    def get_query_plan(self, query: str) -> Dict:
        """Get execution plan for a query"""
        explain_query = f"EXPLAIN (FORMAT JSON, ANALYZE false, BUFFERS false) {query}"
        try:
            results = self.db.execute_query(explain_query)
            if results:
                return results[0]
        except Exception as e:
            logger.error(f"Failed to get query plan: {e}")
        return {}

    def analyze_query_performance(self, query: str) -> Dict:
        """Analyze query performance and provide recommendations"""
        plan = self.get_query_plan(query)
        recommendations = []

        if not plan:
            return {"recommendations": ["Unable to analyze query plan"]}

        # Extract plan from JSON
        if 'QUERY PLAN' in plan:
            plan_data = plan['QUERY PLAN'][0]['Plan']

            # Check for sequential scans
            if self._has_sequential_scan(plan_data):
                recommendations.append("Consider adding indexes to avoid sequential scans")

            # Check for expensive operations
            if self._has_expensive_operations(plan_data):
                recommendations.append("Query contains expensive operations (sorts, hash joins)")

            # Check for missing statistics
            if self._needs_statistics_update(plan_data):
                recommendations.append("Consider running ANALYZE on involved tables")

        return {
            "query_plan": plan,
            "recommendations": recommendations
        }

    def _has_sequential_scan(self, plan_node: Dict) -> bool:
        """Check if plan contains sequential scans"""
        if plan_node.get('Node Type') == 'Seq Scan':
            return True

        for child in plan_node.get('Plans', []):
            if self._has_sequential_scan(child):
                return True

        return False

    def _has_expensive_operations(self, plan_node: Dict) -> bool:
        """Check for expensive operations in plan"""
        expensive_ops = ['Sort', 'Hash Join', 'Merge Join', 'Nested Loop']
        if plan_node.get('Node Type') in expensive_ops:
            return True

        for child in plan_node.get('Plans', []):
            if self._has_expensive_operations(child):
                return True

        return False

    def _needs_statistics_update(self, plan_node: Dict) -> bool:
        """Check if statistics need updating based on row count estimates"""
        actual_rows = plan_node.get('Actual Rows', 0)
        planned_rows = plan_node.get('Plan Rows', 0)

        if planned_rows > 0 and actual_rows > 0:
            ratio = abs(actual_rows - planned_rows) / planned_rows
            if ratio > 0.5:  # 50% difference
                return True

        for child in plan_node.get('Plans', []):
            if self._needs_statistics_update(child):
                return True

        return False

class IndexAnalyzer:
    """Index usage analyzer"""

    def __init__(self, db_connection: DatabaseConnection):
        self.db = db_connection

    def get_index_usage(self) -> List[IndexMetrics]:
        """Get index usage statistics"""
        query = """
        SELECT
            schemaname as schema_name,
            tablename as table_name,
            indexname as index_name,
            idx_scan,
            idx_tup_read,
            idx_tup_fetch,
            pg_relation_size(indexrelid) as size_bytes,
            indisunique as is_unique,
            indisprimary as is_primary,
            array_agg(attname ORDER BY attnum) as columns
        FROM pg_stat_user_indexes psi
        JOIN pg_index pi ON psi.indexrelid = pi.indexrelid
        JOIN pg_attribute pa ON pi.indexrelid = pa.attrelid
        WHERE pa.attnum > 0
        GROUP BY
            schemaname, tablename, indexname, idx_scan, idx_tup_read,
            idx_tup_fetch, indexrelid, indisunique, indisprimary
        ORDER BY idx_scan DESC
        """

        results = self.db.execute_query(query)
        return [IndexMetrics(**row) for row in results]

    def find_unused_indexes(self, min_scans: int = 10) -> List[IndexMetrics]:
        """Find indexes with low usage"""
        all_indexes = self.get_index_usage()
        return [idx for idx in all_indexes
                if idx.idx_scan < min_scans and not idx.is_primary]

    def find_duplicate_indexes(self) -> List[Tuple[IndexMetrics, IndexMetrics]]:
        """Find potentially duplicate indexes"""
        indexes = self.get_index_usage()
        duplicates = []

        for i, idx1 in enumerate(indexes):
            for idx2 in indexes[i+1:]:
                if (idx1.table_name == idx2.table_name and
                    idx1.columns == idx2.columns and
                    not idx1.is_primary and not idx2.is_primary):
                    duplicates.append((idx1, idx2))

        return duplicates

    def suggest_missing_indexes(self) -> List[str]:
        """Suggest missing indexes based on query patterns"""
        # Get tables with high sequential scan ratios
        query = """
        SELECT
            schemaname,
            tablename,
            seq_scan,
            seq_tup_read,
            idx_scan,
            idx_tup_fetch,
            CASE
                WHEN seq_scan + idx_scan > 0
                THEN seq_scan::float / (seq_scan + idx_scan)
                ELSE 0
            END as seq_scan_ratio
        FROM pg_stat_user_tables
        WHERE seq_scan > 1000
        ORDER BY seq_scan_ratio DESC
        LIMIT 20
        """

        results = self.db.execute_query(query)
        suggestions = []

        for row in results:
            if row['seq_scan_ratio'] > 0.5:  # More than 50% sequential scans
                suggestions.append(
                    f"Consider adding indexes to {row['schemaname']}.{row['tablename']} "
                    f"(seq_scan_ratio: {row['seq_scan_ratio']:.2f})"
                )

        return suggestions

class TableAnalyzer:
    """Table statistics analyzer"""

    def __init__(self, db_connection: DatabaseConnection):
        self.db = db_connection

    def get_table_stats(self) -> List[TableMetrics]:
        """Get comprehensive table statistics"""
        query = """
        SELECT
            pst.schemaname as schema_name,
            pst.tablename as table_name,
            pst.n_tup_ins,
            pst.n_tup_upd,
            pst.n_tup_del,
            pst.n_live_tup,
            pst.n_dead_tup,
            pst.seq_scan,
            pst.seq_tup_read,
            pst.idx_scan,
            pst.idx_tup_fetch,
            pst.heap_blks_read,
            pst.heap_blks_hit,
            pg_total_relation_size(pst.relid) as size_bytes,
            pst.last_vacuum,
            pst.last_autovacuum,
            pst.last_analyze,
            pst.last_autoanalyze
        FROM pg_stat_user_tables pst
        ORDER BY pg_total_relation_size(pst.relid) DESC
        """

        results = self.db.execute_query(query)
        return [TableMetrics(**row) for row in results]

    def find_tables_needing_vacuum(self, dead_tuple_threshold: float = 0.1) -> List[TableMetrics]:
        """Find tables that need vacuuming"""
        tables = self.get_table_stats()
        needing_vacuum = []

        for table in tables:
            if table.n_live_tup > 0:
                dead_ratio = table.n_dead_tup / (table.n_live_tup + table.n_dead_tup)
                if dead_ratio > dead_tuple_threshold:
                    needing_vacuum.append(table)

        return needing_vacuum

    def find_tables_needing_analyze(self, days_threshold: int = 7) -> List[TableMetrics]:
        """Find tables that need statistics updates"""
        tables = self.get_table_stats()
        needing_analyze = []
        threshold_date = datetime.datetime.now() - datetime.timedelta(days=days_threshold)

        for table in tables:
            last_analyze = table.last_analyze or table.last_autoanalyze
            if not last_analyze or last_analyze < threshold_date:
                needing_analyze.append(table)

        return needing_analyze

    def get_cache_hit_ratio(self) -> Dict[str, float]:
        """Get buffer cache hit ratios"""
        query = """
        SELECT
            'heap_hit_ratio' as metric,
            CASE
                WHEN heap_blks_read + heap_blks_hit > 0
                THEN heap_blks_hit::float / (heap_blks_read + heap_blks_hit) * 100
                ELSE 0
            END as ratio
        FROM (
            SELECT sum(heap_blks_read) as heap_blks_read,
                   sum(heap_blks_hit) as heap_blks_hit
            FROM pg_statio_user_tables
        ) t
        UNION ALL
        SELECT
            'index_hit_ratio' as metric,
            CASE
                WHEN idx_blks_read + idx_blks_hit > 0
                THEN idx_blks_hit::float / (idx_blks_read + idx_blks_hit) * 100
                ELSE 0
            END as ratio
        FROM (
            SELECT sum(idx_blks_read) as idx_blks_read,
                   sum(idx_blks_hit) as idx_blks_hit
            FROM pg_statio_user_indexes
        ) t
        """

        results = self.db.execute_query(query)
        return {row['metric']: row['ratio'] for row in results}

class PerformanceMonitor:
    """Main performance monitoring coordinator"""

    def __init__(self, connection_string: str):
        self.connection_string = connection_string
        self.db = DatabaseConnection(connection_string)
        self.query_analyzer = QueryAnalyzer(self.db)
        self.index_analyzer = IndexAnalyzer(self.db)
        self.table_analyzer = TableAnalyzer(self.db)

    def generate_performance_report(self, output_file: str = None) -> Dict:
        """Generate comprehensive performance report"""
        logger.info("Generating performance report...")

        with self.db:
            # Collect metrics
            slow_queries = self.query_analyzer.get_slow_queries(min_duration_ms=50, limit=20)
            unused_indexes = self.index_analyzer.find_unused_indexes(min_scans=5)
            duplicate_indexes = self.index_analyzer.find_duplicate_indexes()
            missing_indexes = self.index_analyzer.suggest_missing_indexes()
            tables_need_vacuum = self.table_analyzer.find_tables_needing_vacuum()
            tables_need_analyze = self.table_analyzer.find_tables_needing_analyze()
            cache_ratios = self.table_analyzer.get_cache_hit_ratio()

            report = {
                "timestamp": datetime.datetime.now().isoformat(),
                "slow_queries": [asdict(q) for q in slow_queries[:10]],
                "unused_indexes": [asdict(idx) for idx in unused_indexes],
                "duplicate_indexes": len(duplicate_indexes),
                "missing_indexes": missing_indexes,
                "tables_needing_vacuum": len(tables_need_vacuum),
                "tables_needing_analyze": len(tables_need_analyze),
                "cache_hit_ratios": cache_ratios,
                "recommendations": self._generate_recommendations(
                    slow_queries, unused_indexes, duplicate_indexes,
                    missing_indexes, tables_need_vacuum, tables_need_analyze, cache_ratios
                )
            }

        if output_file:
            with open(output_file, 'w') as f:
                json.dump(report, f, indent=2, default=str)
            logger.info(f"Performance report saved to {output_file}")

        return report

    def _generate_recommendations(self, slow_queries, unused_indexes, duplicate_indexes,
                                 missing_indexes, tables_need_vacuum, tables_need_analyze,
                                 cache_ratios) -> List[str]:
        """Generate performance recommendations"""
        recommendations = []

        # Query performance
        if slow_queries:
            recommendations.append(f"Found {len(slow_queries)} slow queries that need optimization")

        # Index optimization
        if unused_indexes:
            recommendations.append(f"Found {len(unused_indexes)} unused indexes that could be dropped")

        if duplicate_indexes:
            recommendations.append(f"Found {len(duplicate_indexes)} duplicate index pairs")

        if missing_indexes:
            recommendations.extend(missing_indexes[:5])  # Top 5 suggestions

        # Maintenance
        if tables_need_vacuum:
            recommendations.append(f"{len(tables_need_vacuum)} tables need vacuuming")

        if tables_need_analyze:
            recommendations.append(f"{len(tables_need_analyze)} tables need statistics updates")

        # Cache performance
        heap_ratio = cache_ratios.get('heap_hit_ratio', 0)
        index_ratio = cache_ratios.get('index_hit_ratio', 0)

        if heap_ratio < 90:
            recommendations.append(f"Low heap cache hit ratio: {heap_ratio:.1f}% (should be >90%)")

        if index_ratio < 95:
            recommendations.append(f"Low index cache hit ratio: {index_ratio:.1f}% (should be >95%)")

        return recommendations

    def monitor_real_time(self, duration_seconds: int = 300, interval_seconds: int = 10):
        """Monitor performance in real-time"""
        logger.info(f"Starting real-time monitoring for {duration_seconds} seconds...")

        start_time = time.time()
        metrics_history = []

        while time.time() - start_time < duration_seconds:
            try:
                with self.db:
                    # Get current metrics snapshot
                    cache_ratios = self.table_analyzer.get_cache_hit_ratio()
                    slow_queries = self.query_analyzer.get_slow_queries(min_duration_ms=100, limit=5)

                    snapshot = {
                        "timestamp": datetime.datetime.now(),
                        "cache_hit_ratios": cache_ratios,
                        "slow_query_count": len(slow_queries),
                        "avg_slow_query_time": sum(q.mean_time for q in slow_queries) / len(slow_queries) if slow_queries else 0
                    }

                    metrics_history.append(snapshot)

                    # Print current status
                    print(f"\r[{snapshot['timestamp'].strftime('%H:%M:%S')}] "
                          f"Cache Hit: {cache_ratios.get('heap_hit_ratio', 0):.1f}% | "
                          f"Slow Queries: {snapshot['slow_query_count']} | "
                          f"Avg Time: {snapshot['avg_slow_query_time']:.2f}ms", end="")

                time.sleep(interval_seconds)

            except KeyboardInterrupt:
                print("\nMonitoring stopped by user")
                break
            except Exception as e:
                logger.error(f"Error during monitoring: {e}")
                break

        print()  # New line after monitoring
        return metrics_history

    def optimize_query(self, query: str) -> Dict:
        """Analyze and optimize a specific query"""
        logger.info("Analyzing query for optimization...")

        with self.db:
            analysis = self.query_analyzer.analyze_query_performance(query)

        return analysis

def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(description="Sunday.com Database Query Optimizer")
    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    # Report command
    report_parser = subparsers.add_parser('report', help='Generate performance report')
    report_parser.add_argument('--output', '-o', help='Output file for report')

    # Monitor command
    monitor_parser = subparsers.add_parser('monitor', help='Real-time performance monitoring')
    monitor_parser.add_argument('--duration', '-d', type=int, default=300,
                               help='Monitoring duration in seconds (default: 300)')
    monitor_parser.add_argument('--interval', '-i', type=int, default=10,
                               help='Monitoring interval in seconds (default: 10)')

    # Optimize command
    optimize_parser = subparsers.add_parser('optimize', help='Optimize specific query')
    optimize_parser.add_argument('query', help='SQL query to optimize')

    # Add database connection options
    for subparser in [report_parser, monitor_parser, optimize_parser]:
        subparser.add_argument('--host', default='localhost', help='Database host')
        subparser.add_argument('--port', type=int, default=5432, help='Database port')
        subparser.add_argument('--database', default='sunday_dev', help='Database name')
        subparser.add_argument('--user', default='sunday_dev', help='Database user')
        subparser.add_argument('--password', help='Database password')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    # Build connection string
    password = args.password or os.getenv('DB_PASSWORD', 'dev_password123')
    connection_string = (
        f"host={args.host} port={args.port} dbname={args.database} "
        f"user={args.user} password={password} sslmode=prefer"
    )

    try:
        monitor = PerformanceMonitor(connection_string)

        if args.command == 'report':
            report = monitor.generate_performance_report(args.output)

            # Print summary
            print("\n=== PERFORMANCE REPORT SUMMARY ===")
            print(f"Slow queries: {len(report['slow_queries'])}")
            print(f"Unused indexes: {len(report['unused_indexes'])}")
            print(f"Duplicate indexes: {report['duplicate_indexes']}")
            print(f"Tables needing vacuum: {report['tables_needing_vacuum']}")
            print(f"Tables needing analyze: {report['tables_needing_analyze']}")

            cache_ratios = report['cache_hit_ratios']
            print(f"Heap cache hit ratio: {cache_ratios.get('heap_hit_ratio', 0):.1f}%")
            print(f"Index cache hit ratio: {cache_ratios.get('index_hit_ratio', 0):.1f}%")

            print("\n=== RECOMMENDATIONS ===")
            for recommendation in report['recommendations']:
                print(f"• {recommendation}")

        elif args.command == 'monitor':
            metrics = monitor.monitor_real_time(args.duration, args.interval)
            print(f"\nCollected {len(metrics)} monitoring snapshots")

        elif args.command == 'optimize':
            analysis = monitor.optimize_query(args.query)
            print("\n=== QUERY OPTIMIZATION ANALYSIS ===")
            for recommendation in analysis.get('recommendations', []):
                print(f"• {recommendation}")

    except Exception as e:
        logger.error(f"Error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()