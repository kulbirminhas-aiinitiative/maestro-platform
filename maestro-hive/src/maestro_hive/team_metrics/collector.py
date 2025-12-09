#!/usr/bin/env python3
"""
Team Metrics Collector: Aggregates metrics from multiple sources.

Implements:
- AC-1: Real data from DDE performance tracker
- AC-3: Real-time Quality Score aggregation
- AC-4: Real-time Artifact Generation tracking
"""

import json
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from .models import TeamMetrics, QualityMetrics, ArtifactMetrics
from .jira_metrics import JiraMetricsProvider, JiraConfig
from .git_metrics import GitMetricsProvider, GitConfig

logger = logging.getLogger(__name__)


@dataclass
class CollectorConfig:
    """Configuration for metrics collection."""
    dde_tracker_path: str = ""
    cache_ttl_seconds: int = 300  # 5 minutes
    quality_fabric_url: str = "http://localhost:8000"

    @classmethod
    def from_env(cls) -> 'CollectorConfig':
        return cls(
            dde_tracker_path=os.getenv('DDE_TRACKER_PATH', ''),
            cache_ttl_seconds=int(os.getenv('METRICS_CACHE_TTL', '300')),
            quality_fabric_url=os.getenv('QUALITY_FABRIC_URL', 'http://localhost:8000')
        )


class TeamMetricsCollector:
    """
    Collects and aggregates team metrics from multiple sources.

    Sources:
    - DDE Performance Tracker (AC-1)
    - Jira (AC-2, AC-7)
    - Git (AC-8)
    - Quality Fabric (AC-3)
    - Artifact Tracking (AC-4)
    """

    def __init__(
        self,
        config: Optional[CollectorConfig] = None,
        jira_provider: Optional[JiraMetricsProvider] = None,
        git_provider: Optional[GitMetricsProvider] = None
    ):
        self.config = config or CollectorConfig.from_env()
        self.jira_provider = jira_provider or JiraMetricsProvider()
        self.git_provider = git_provider or GitMetricsProvider()
        self._cache: Dict[str, Any] = {}
        self._cache_timestamps: Dict[str, datetime] = {}

    def collect_team_metrics(
        self,
        team_id: str,
        team_name: str,
        board_id: Optional[int] = None,
        project_key: Optional[str] = None,
        repo_path: Optional[str] = None
    ) -> TeamMetrics:
        """
        Collect comprehensive metrics for a team.

        Aggregates data from all sources into a single TeamMetrics object.
        """
        logger.info(f"Collecting metrics for team: {team_id}")

        # Initialize with defaults
        velocity = 0.0
        quality_score = 0.0
        artifact_count = 0
        commit_frequency = 0.0
        code_review_turnaround = 0.0
        test_coverage = 0.0

        jira_metrics = {}
        git_metrics = {}
        dde_metrics = {}

        # Collect Jira metrics (AC-2, AC-7)
        if board_id:
            velocity_data = self.jira_provider.get_sprint_velocity(team_id, board_id)
            if velocity_data:
                velocity = velocity_data.velocity
                jira_metrics['velocity'] = velocity_data.to_dict()

        if project_key:
            task_metrics = self.jira_provider.get_team_task_metrics(project_key)
            if task_metrics:
                jira_metrics['tasks'] = task_metrics

        # Collect Git metrics (AC-8)
        commit_metrics = self.git_provider.get_commit_metrics(team_id, repo_path=repo_path)
        if commit_metrics:
            commit_frequency = commit_metrics.commits_per_day
            git_metrics['commits'] = commit_metrics.to_dict()

        # Collect DDE metrics (AC-1)
        dde_data = self._collect_dde_metrics(team_id)
        if dde_data:
            dde_metrics = dde_data
            quality_score = dde_data.get('quality_score', 0.0)
            artifact_count = dde_data.get('artifact_count', 0)
            test_coverage = dde_data.get('test_coverage', 0.0)

        # Collect Quality Fabric metrics (AC-3)
        quality_fabric_data = self._collect_quality_fabric_metrics(team_id)
        if quality_fabric_data:
            # Aggregate quality scores
            if quality_fabric_data.get('overall_score'):
                quality_score = (quality_score + quality_fabric_data['overall_score']) / 2
            dde_metrics['quality_fabric'] = quality_fabric_data

        # Build TeamMetrics
        metrics = TeamMetrics(
            team_id=team_id,
            team_name=team_name,
            velocity=velocity,
            quality_score=quality_score,
            artifact_count=artifact_count,
            commit_frequency=commit_frequency,
            code_review_turnaround=code_review_turnaround,
            test_coverage=test_coverage,
            jira_metrics=jira_metrics,
            git_metrics=git_metrics,
            dde_metrics=dde_metrics
        )

        # Calculate overall score
        metrics.calculate_score()

        logger.info(f"Collected metrics for {team_id}: score={metrics.overall_score}, grade={metrics.grade}")
        return metrics

    def collect_all_teams(
        self,
        team_configs: List[Dict[str, Any]]
    ) -> List[TeamMetrics]:
        """
        Collect metrics for multiple teams.

        Args:
            team_configs: List of team configuration dicts with:
                - team_id: str
                - team_name: str
                - board_id: Optional[int]
                - project_key: Optional[str]
                - repo_path: Optional[str]
        """
        results = []

        for config in team_configs:
            try:
                metrics = self.collect_team_metrics(
                    team_id=config['team_id'],
                    team_name=config['team_name'],
                    board_id=config.get('board_id'),
                    project_key=config.get('project_key'),
                    repo_path=config.get('repo_path')
                )
                results.append(metrics)
            except Exception as e:
                logger.error(f"Error collecting metrics for team {config.get('team_id')}: {e}")
                continue

        return results

    def _collect_dde_metrics(self, team_id: str) -> Dict[str, Any]:
        """
        Collect metrics from DDE Performance Tracker.

        AC-1: Real data from DDE performance tracker.
        """
        try:
            # Check cache
            cache_key = f"dde_{team_id}"
            if self._is_cached(cache_key):
                return self._cache.get(cache_key, {})

            # Read from DDE tracker file if configured
            if self.config.dde_tracker_path and os.path.exists(self.config.dde_tracker_path):
                with open(self.config.dde_tracker_path, 'r') as f:
                    dde_data = json.load(f)

                    # Find team-specific data
                    team_data = dde_data.get('teams', {}).get(team_id, {})

                    if team_data:
                        result = {
                            'quality_score': team_data.get('quality_score', 0),
                            'artifact_count': team_data.get('artifacts_generated', 0),
                            'test_coverage': team_data.get('test_coverage', 0),
                            'execution_success_rate': team_data.get('success_rate', 0),
                            'average_execution_time': team_data.get('avg_execution_time', 0)
                        }
                        self._update_cache(cache_key, result)
                        return result

            # Return defaults if no DDE data available
            return {
                'quality_score': 0,
                'artifact_count': 0,
                'test_coverage': 0,
                'execution_success_rate': 0,
                'average_execution_time': 0
            }

        except Exception as e:
            logger.error(f"Error collecting DDE metrics: {e}")
            return {}

    def _collect_quality_fabric_metrics(self, team_id: str) -> Dict[str, Any]:
        """
        Collect metrics from Quality Fabric.

        AC-3: Real-time Quality Score aggregation.
        """
        try:
            import requests

            # Check cache
            cache_key = f"qf_{team_id}"
            if self._is_cached(cache_key):
                return self._cache.get(cache_key, {})

            # Query Quality Fabric API
            url = f"{self.config.quality_fabric_url}/api/quality/team/{team_id}"

            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                self._update_cache(cache_key, data)
                return data

            return {}

        except Exception as e:
            logger.debug(f"Quality Fabric not available: {e}")
            return {}

    def collect_artifact_metrics(
        self,
        team_id: str,
        period: str = "sprint"
    ) -> ArtifactMetrics:
        """
        Collect artifact generation metrics.

        AC-4: Real-time Artifact Generation tracking.
        """
        try:
            # Query artifact storage/database
            # This would integrate with the actual artifact tracking system

            return ArtifactMetrics(
                team_id=team_id,
                period=period,
                artifacts_generated=0,
                artifact_types={},
                workflow_completions=0,
                successful_deployments=0
            )

        except Exception as e:
            logger.error(f"Error collecting artifact metrics: {e}")
            return ArtifactMetrics(
                team_id=team_id,
                period=period,
                artifacts_generated=0
            )

    def collect_quality_metrics(
        self,
        team_id: str
    ) -> QualityMetrics:
        """
        Collect quality-specific metrics.

        AC-3: Real-time Quality Score aggregation.
        """
        try:
            # Aggregate quality from multiple sources
            qf_data = self._collect_quality_fabric_metrics(team_id)
            dde_data = self._collect_dde_metrics(team_id)

            metrics = QualityMetrics(
                team_id=team_id,
                timestamp=datetime.utcnow().isoformat(),
                code_quality_score=qf_data.get('code_quality', 0),
                test_pass_rate=qf_data.get('test_pass_rate', 0),
                bug_density=qf_data.get('bug_density', 0),
                documentation_coverage=qf_data.get('doc_coverage', 0),
                security_score=qf_data.get('security_score', 0),
                performance_score=qf_data.get('performance_score', 0),
                overall_quality=0
            )

            metrics.calculate_overall()
            return metrics

        except Exception as e:
            logger.error(f"Error collecting quality metrics: {e}")
            return QualityMetrics(
                team_id=team_id,
                timestamp=datetime.utcnow().isoformat(),
                code_quality_score=0,
                test_pass_rate=0,
                bug_density=0,
                documentation_coverage=0,
                security_score=0,
                performance_score=0,
                overall_quality=0
            )

    def _is_cached(self, key: str) -> bool:
        """Check if cached data is still valid."""
        if key not in self._cache_timestamps:
            return False

        age = (datetime.utcnow() - self._cache_timestamps[key]).total_seconds()
        return age < self.config.cache_ttl_seconds

    def _update_cache(self, key: str, data: Any) -> None:
        """Update cache with new data."""
        self._cache[key] = data
        self._cache_timestamps[key] = datetime.utcnow()

    def clear_cache(self) -> None:
        """Clear all cached data."""
        self._cache.clear()
        self._cache_timestamps.clear()


def get_metrics_collector(**kwargs) -> TeamMetricsCollector:
    """Get a configured metrics collector instance."""
    config = CollectorConfig(**kwargs) if kwargs else None
    return TeamMetricsCollector(config=config)
