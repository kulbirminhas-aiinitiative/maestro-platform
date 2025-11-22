#!/usr/bin/env python3
"""
Quality Fabric - Test Result Aggregator
Collects, processes, and analyzes test results from multiple sources
"""

import asyncio
import json
import time
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, Union, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
from datetime import datetime, timedelta
import sqlite3
from collections import defaultdict
import hashlib

logger = logging.getLogger(__name__)

try:
    import pandas as pd
    import numpy as np
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False
    logger.warning("Pandas not available - some analytics features will be limited")
    # Create mock pandas/numpy
    class pd:
        pass
    class np:
        pass


class ResultStatus(str, Enum):
    """Test result status"""
    PASSED = "passed"
    FAILED = "failed"
    ERROR = "error"
    SKIPPED = "skipped"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"


class AggregationLevel(str, Enum):
    """Aggregation levels"""
    TEST_CASE = "test_case"
    TEST_SUITE = "test_suite"
    TEST_CATEGORY = "test_category"
    SERVICE = "service"
    ORCHESTRATION = "orchestration"


@dataclass
class TestResultMetadata:
    """Test result metadata"""
    test_id: str
    orchestration_id: str
    category: str
    service: str
    environment: str
    timestamp: float
    duration: float
    status: ResultStatus
    tags: List[str] = None
    custom_fields: Dict[str, Any] = None


@dataclass
class AggregatedTestMetrics:
    """Aggregated test metrics"""
    total_tests: int
    passed_tests: int
    failed_tests: int
    error_tests: int
    skipped_tests: int
    success_rate: float
    average_duration: float
    total_duration: float
    test_velocity: float  # tests per hour
    failure_rate_trend: List[float]
    performance_trend: List[float]


@dataclass
class QualityInsight:
    """Quality insight from test results"""
    insight_type: str
    severity: str
    title: str
    description: str
    affected_components: List[str]
    recommendation: str
    evidence: Dict[str, Any]


class TestResultAggregator:
    """
    Comprehensive test result aggregator for Quality Fabric Testing Service
    """

    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.database_path = Path(self.config.get("database_path", "/tmp/quality_fabric_results.db"))
        self.results_cache = {}
        self.aggregation_cache = {}

        # Initialize database
        self._initialize_database()

    def _initialize_database(self):
        """Initialize SQLite database for test results"""
        try:
            self.database_path.parent.mkdir(parents=True, exist_ok=True)

            with sqlite3.connect(self.database_path) as conn:
                # Create tables
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS test_results (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        test_id TEXT NOT NULL,
                        orchestration_id TEXT NOT NULL,
                        category TEXT NOT NULL,
                        service TEXT NOT NULL,
                        environment TEXT NOT NULL,
                        timestamp REAL NOT NULL,
                        duration REAL NOT NULL,
                        status TEXT NOT NULL,
                        tags TEXT,
                        custom_fields TEXT,
                        result_data TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)

                conn.execute("""
                    CREATE TABLE IF NOT EXISTS aggregated_metrics (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        orchestration_id TEXT NOT NULL,
                        aggregation_level TEXT NOT NULL,
                        metrics_data TEXT NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)

                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_orchestration_id
                    ON test_results(orchestration_id)
                """)

                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_timestamp
                    ON test_results(timestamp)
                """)

                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_category
                    ON test_results(category)
                """)

                conn.commit()

            logger.info(f"Test results database initialized at {self.database_path}")

        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise

    async def store_test_results(
        self,
        orchestration_id: str,
        results: List[Dict[str, Any]]
    ) -> bool:
        """Store test results in the database"""
        try:
            with sqlite3.connect(self.database_path) as conn:
                for result in results:
                    # Extract metadata
                    metadata = self._extract_metadata(result, orchestration_id)

                    # Store in database
                    conn.execute("""
                        INSERT INTO test_results (
                            test_id, orchestration_id, category, service, environment,
                            timestamp, duration, status, tags, custom_fields, result_data
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        metadata.test_id,
                        metadata.orchestration_id,
                        metadata.category,
                        metadata.service,
                        metadata.environment,
                        metadata.timestamp,
                        metadata.duration,
                        metadata.status.value,
                        json.dumps(metadata.tags or []),
                        json.dumps(metadata.custom_fields or {}),
                        json.dumps(result)
                    ))

                conn.commit()

            # Clear cache to force refresh
            self._clear_cache(orchestration_id)

            logger.info(f"Stored {len(results)} test results for orchestration {orchestration_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to store test results: {e}")
            return False

    async def get_test_results(
        self,
        orchestration_id: str = None,
        category: str = None,
        time_range: Tuple[float, float] = None
    ) -> List[Dict[str, Any]]:
        """Retrieve test results from database"""
        try:
            with sqlite3.connect(self.database_path) as conn:
                conn.row_factory = sqlite3.Row

                # Build query
                query = "SELECT * FROM test_results WHERE 1=1"
                params = []

                if orchestration_id:
                    query += " AND orchestration_id = ?"
                    params.append(orchestration_id)

                if category:
                    query += " AND category = ?"
                    params.append(category)

                if time_range:
                    query += " AND timestamp BETWEEN ? AND ?"
                    params.extend(time_range)

                query += " ORDER BY timestamp DESC"

                cursor = conn.execute(query, params)
                rows = cursor.fetchall()

                # Convert to dictionaries
                results = []
                for row in rows:
                    result_dict = dict(row)
                    result_dict['tags'] = json.loads(result_dict['tags'] or '[]')
                    result_dict['custom_fields'] = json.loads(result_dict['custom_fields'] or '{}')
                    result_dict['result_data'] = json.loads(result_dict['result_data'] or '{}')
                    results.append(result_dict)

                return results

        except Exception as e:
            logger.error(f"Failed to retrieve test results: {e}")
            return []

    async def aggregate_results(
        self,
        aggregation_level: AggregationLevel,
        filters: Dict[str, Any] = None,
        time_range: Tuple[float, float] = None
    ) -> AggregatedTestMetrics:
        """Aggregate test results at specified level"""
        try:
            # Generate cache key
            cache_key = self._generate_cache_key(aggregation_level, filters, time_range)

            # Check cache first
            if cache_key in self.aggregation_cache:
                cached_result = self.aggregation_cache[cache_key]
                if time.time() - cached_result['timestamp'] < 300:  # 5 minutes cache
                    return cached_result['metrics']

            # Get results from database
            results = await self.get_test_results(
                orchestration_id=filters.get('orchestration_id') if filters else None,
                category=filters.get('category') if filters else None,
                time_range=time_range
            )

            if not results:
                return self._empty_metrics()

            # Aggregate based on level
            metrics = await self._perform_aggregation(results, aggregation_level)

            # Cache result
            self.aggregation_cache[cache_key] = {
                'metrics': metrics,
                'timestamp': time.time()
            }

            return metrics

        except Exception as e:
            logger.error(f"Failed to aggregate results: {e}")
            return self._empty_metrics()

    async def generate_quality_insights(
        self,
        time_range: Tuple[float, float] = None,
        min_severity: str = "low"
    ) -> List[QualityInsight]:
        """Generate AI-powered quality insights"""
        try:
            insights = []

            # Get recent test results
            results = await self.get_test_results(time_range=time_range)

            if not results:
                return insights

            # Analyze failure patterns
            failure_insights = await self._analyze_failure_patterns(results)
            insights.extend(failure_insights)

            # Analyze performance trends
            performance_insights = await self._analyze_performance_trends(results)
            insights.extend(performance_insights)

            # Analyze test coverage
            coverage_insights = await self._analyze_test_coverage(results)
            insights.extend(coverage_insights)

            # Filter by severity
            severity_order = {"low": 0, "medium": 1, "high": 2, "critical": 3}
            min_severity_level = severity_order.get(min_severity, 0)

            filtered_insights = [
                insight for insight in insights
                if severity_order.get(insight.severity, 0) >= min_severity_level
            ]

            return filtered_insights

        except Exception as e:
            logger.error(f"Failed to generate quality insights: {e}")
            return []

    async def generate_test_report(
        self,
        orchestration_id: str,
        report_format: str = "comprehensive"
    ) -> Dict[str, Any]:
        """Generate comprehensive test report"""
        try:
            # Get test results for orchestration
            results = await self.get_test_results(orchestration_id=orchestration_id)

            if not results:
                return {"error": "No results found for orchestration"}

            # Generate metrics
            metrics = await self.aggregate_results(
                AggregationLevel.ORCHESTRATION,
                {"orchestration_id": orchestration_id}
            )

            # Generate insights
            time_range = (
                min(r['timestamp'] for r in results),
                max(r['timestamp'] for r in results)
            )
            insights = await self.generate_quality_insights(time_range)

            # Build report
            report = {
                "orchestration_id": orchestration_id,
                "generated_at": datetime.utcnow().isoformat(),
                "report_format": report_format,
                "summary": {
                    "total_tests": metrics.total_tests,
                    "success_rate": metrics.success_rate,
                    "total_duration": metrics.total_duration,
                    "test_velocity": metrics.test_velocity
                },
                "detailed_metrics": asdict(metrics),
                "quality_insights": [asdict(insight) for insight in insights],
                "recommendations": await self._generate_report_recommendations(metrics, insights)
            }

            if report_format == "comprehensive":
                report["detailed_results"] = results
                report["category_breakdown"] = await self._generate_category_breakdown(results)

            return report

        except Exception as e:
            logger.error(f"Failed to generate test report: {e}")
            return {"error": str(e)}

    def _extract_metadata(self, result: Dict[str, Any], orchestration_id: str) -> TestResultMetadata:
        """Extract metadata from test result"""
        # Generate test ID if not present
        test_id = result.get('test_id') or result.get('execution_id') or f"test_{int(time.time())}"

        return TestResultMetadata(
            test_id=test_id,
            orchestration_id=orchestration_id,
            category=result.get('category', 'unknown'),
            service=result.get('service', 'quality_fabric'),
            environment=result.get('environment', 'test'),
            timestamp=result.get('timestamp', time.time()),
            duration=result.get('duration', 0),
            status=ResultStatus(result.get('status', 'unknown')),
            tags=result.get('tags', []),
            custom_fields=result.get('custom_fields', {})
        )

    async def _perform_aggregation(
        self,
        results: List[Dict[str, Any]],
        aggregation_level: AggregationLevel
    ) -> AggregatedTestMetrics:
        """Perform aggregation based on level"""
        total_tests = len(results)
        if total_tests == 0:
            return self._empty_metrics()

        # Count by status
        status_counts = defaultdict(int)
        for result in results:
            status_counts[result['status']] += 1

        passed_tests = status_counts['passed']
        failed_tests = status_counts['failed']
        error_tests = status_counts['error']
        skipped_tests = status_counts['skipped']

        success_rate = passed_tests / total_tests if total_tests > 0 else 0

        # Calculate durations
        durations = [r['duration'] for r in results if r['duration'] > 0]
        average_duration = sum(durations) / len(durations) if durations else 0
        total_duration = sum(durations)

        # Calculate test velocity (tests per hour)
        time_span = max(r['timestamp'] for r in results) - min(r['timestamp'] for r in results)
        test_velocity = (total_tests / (time_span / 3600)) if time_span > 0 else 0

        # Calculate trends (simplified)
        failure_rate_trend = await self._calculate_failure_trend(results)
        performance_trend = await self._calculate_performance_trend(results)

        return AggregatedTestMetrics(
            total_tests=total_tests,
            passed_tests=passed_tests,
            failed_tests=failed_tests,
            error_tests=error_tests,
            skipped_tests=skipped_tests,
            success_rate=success_rate,
            average_duration=average_duration,
            total_duration=total_duration,
            test_velocity=test_velocity,
            failure_rate_trend=failure_rate_trend,
            performance_trend=performance_trend
        )

    async def _analyze_failure_patterns(self, results: List[Dict[str, Any]]) -> List[QualityInsight]:
        """Analyze failure patterns in test results"""
        insights = []

        failed_results = [r for r in results if r['status'] in ['failed', 'error']]
        total_results = len(results)

        if not failed_results:
            return insights

        failure_rate = len(failed_results) / total_results

        if failure_rate > 0.2:  # More than 20% failure rate
            insights.append(QualityInsight(
                insight_type="high_failure_rate",
                severity="high" if failure_rate > 0.5 else "medium",
                title="High Test Failure Rate Detected",
                description=f"Test failure rate is {failure_rate:.1%}, which exceeds acceptable thresholds",
                affected_components=list(set(r['category'] for r in failed_results)),
                recommendation="Review failed tests and address underlying issues",
                evidence={
                    "failure_rate": failure_rate,
                    "failed_tests": len(failed_results),
                    "total_tests": total_results
                }
            ))

        # Analyze failure by category
        category_failures = defaultdict(int)
        category_totals = defaultdict(int)

        for result in results:
            category = result['category']
            category_totals[category] += 1
            if result['status'] in ['failed', 'error']:
                category_failures[category] += 1

        for category, failures in category_failures.items():
            if failures > 0:
                category_failure_rate = failures / category_totals[category]
                if category_failure_rate > 0.3:  # More than 30% failure in category
                    insights.append(QualityInsight(
                        insight_type="category_failure_pattern",
                        severity="medium",
                        title=f"High Failure Rate in {category.title()} Tests",
                        description=f"{category.title()} tests have a {category_failure_rate:.1%} failure rate",
                        affected_components=[category],
                        recommendation=f"Focus on improving {category} test stability",
                        evidence={
                            "category": category,
                            "failure_rate": category_failure_rate,
                            "failed_tests": failures,
                            "total_tests": category_totals[category]
                        }
                    ))

        return insights

    async def _analyze_performance_trends(self, results: List[Dict[str, Any]]) -> List[QualityInsight]:
        """Analyze performance trends"""
        insights = []

        # Get results with valid durations
        timed_results = [r for r in results if r['duration'] > 0]

        if len(timed_results) < 5:  # Not enough data
            return insights

        # Calculate average duration
        average_duration = sum(r['duration'] for r in timed_results) / len(timed_results)

        # Find slow tests
        slow_tests = [r for r in timed_results if r['duration'] > average_duration * 2]

        if slow_tests:
            insights.append(QualityInsight(
                insight_type="slow_tests_detected",
                severity="low",
                title="Slow Tests Detected",
                description=f"Found {len(slow_tests)} tests that are significantly slower than average",
                affected_components=list(set(r['category'] for r in slow_tests)),
                recommendation="Optimize slow tests to improve overall test execution time",
                evidence={
                    "slow_test_count": len(slow_tests),
                    "average_duration": average_duration,
                    "slowest_test_duration": max(r['duration'] for r in slow_tests)
                }
            ))

        return insights

    async def _analyze_test_coverage(self, results: List[Dict[str, Any]]) -> List[QualityInsight]:
        """Analyze test coverage"""
        insights = []

        # Analyze test distribution by category
        category_counts = defaultdict(int)
        for result in results:
            category_counts[result['category']] += 1

        total_tests = len(results)
        categories = list(category_counts.keys())

        # Check for missing common test categories
        expected_categories = ['unit', 'integration', 'frontend', 'performance']
        missing_categories = [cat for cat in expected_categories if cat not in categories]

        if missing_categories:
            insights.append(QualityInsight(
                insight_type="missing_test_categories",
                severity="medium",
                title="Missing Test Categories",
                description=f"Missing test coverage for: {', '.join(missing_categories)}",
                affected_components=missing_categories,
                recommendation="Add tests for missing categories to improve coverage",
                evidence={
                    "missing_categories": missing_categories,
                    "present_categories": categories,
                    "total_tests": total_tests
                }
            ))

        return insights

    async def _calculate_failure_trend(self, results: List[Dict[str, Any]]) -> List[float]:
        """Calculate failure rate trend over time"""
        if len(results) < 10:
            return [0.0] * 5

        # Sort by timestamp
        sorted_results = sorted(results, key=lambda x: x['timestamp'])

        # Split into 5 time buckets
        bucket_size = len(sorted_results) // 5
        trends = []

        for i in range(5):
            start_idx = i * bucket_size
            end_idx = start_idx + bucket_size if i < 4 else len(sorted_results)
            bucket_results = sorted_results[start_idx:end_idx]

            if bucket_results:
                failed_count = sum(1 for r in bucket_results if r['status'] in ['failed', 'error'])
                failure_rate = failed_count / len(bucket_results)
                trends.append(failure_rate)
            else:
                trends.append(0.0)

        return trends

    async def _calculate_performance_trend(self, results: List[Dict[str, Any]]) -> List[float]:
        """Calculate performance trend over time"""
        timed_results = [r for r in results if r['duration'] > 0]

        if len(timed_results) < 10:
            return [0.0] * 5

        # Sort by timestamp
        sorted_results = sorted(timed_results, key=lambda x: x['timestamp'])

        # Split into 5 time buckets
        bucket_size = len(sorted_results) // 5
        trends = []

        for i in range(5):
            start_idx = i * bucket_size
            end_idx = start_idx + bucket_size if i < 4 else len(sorted_results)
            bucket_results = sorted_results[start_idx:end_idx]

            if bucket_results:
                avg_duration = sum(r['duration'] for r in bucket_results) / len(bucket_results)
                trends.append(avg_duration)
            else:
                trends.append(0.0)

        return trends

    async def _generate_category_breakdown(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate breakdown by category"""
        breakdown = defaultdict(lambda: {
            'total': 0,
            'passed': 0,
            'failed': 0,
            'error': 0,
            'skipped': 0,
            'average_duration': 0
        })

        for result in results:
            category = result['category']
            breakdown[category]['total'] += 1
            breakdown[category][result['status']] += 1

            if result['duration'] > 0:
                current_avg = breakdown[category]['average_duration']
                current_count = breakdown[category]['total']
                new_avg = ((current_avg * (current_count - 1)) + result['duration']) / current_count
                breakdown[category]['average_duration'] = new_avg

        # Calculate success rates
        for category, stats in breakdown.items():
            if stats['total'] > 0:
                stats['success_rate'] = stats['passed'] / stats['total']
            else:
                stats['success_rate'] = 0

        return dict(breakdown)

    async def _generate_report_recommendations(
        self,
        metrics: AggregatedTestMetrics,
        insights: List[QualityInsight]
    ) -> List[str]:
        """Generate recommendations for test report"""
        recommendations = []

        if metrics.success_rate < 0.8:
            recommendations.append("Improve test success rate by addressing failing tests")

        if metrics.average_duration > 60:  # More than 1 minute average
            recommendations.append("Optimize test performance to reduce execution time")

        if insights:
            recommendations.append("Address quality insights to improve overall test quality")

        if not recommendations:
            recommendations.append("Test quality is good - maintain current practices")

        return recommendations

    def _empty_metrics(self) -> AggregatedTestMetrics:
        """Return empty metrics"""
        return AggregatedTestMetrics(
            total_tests=0,
            passed_tests=0,
            failed_tests=0,
            error_tests=0,
            skipped_tests=0,
            success_rate=0.0,
            average_duration=0.0,
            total_duration=0.0,
            test_velocity=0.0,
            failure_rate_trend=[],
            performance_trend=[]
        )

    def _generate_cache_key(
        self,
        aggregation_level: AggregationLevel,
        filters: Dict[str, Any],
        time_range: Tuple[float, float]
    ) -> str:
        """Generate cache key for aggregation"""
        key_data = {
            "level": aggregation_level.value,
            "filters": filters or {},
            "time_range": time_range
        }
        key_str = json.dumps(key_data, sort_keys=True)
        return hashlib.md5(key_str.encode()).hexdigest()

    def _clear_cache(self, orchestration_id: str = None):
        """Clear relevant caches"""
        if orchestration_id:
            # Clear specific caches
            keys_to_remove = [
                key for key in self.aggregation_cache.keys()
                if orchestration_id in str(self.aggregation_cache[key])
            ]
            for key in keys_to_remove:
                del self.aggregation_cache[key]
        else:
            # Clear all caches
            self.aggregation_cache.clear()
            self.results_cache.clear()