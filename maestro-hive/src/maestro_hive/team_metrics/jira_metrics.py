#!/usr/bin/env python3
"""
Jira Metrics Provider: Fetches real-time metrics from Jira.

Implements AC-2 and AC-7:
- AC-2: Real-time Velocity calculation from Jira
- AC-7: Jira integration via jira_tool.py for task metrics
"""

import json
import logging
import os
from dataclasses import dataclass, asdict, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
import requests
from requests.auth import HTTPBasicAuth

logger = logging.getLogger(__name__)


@dataclass
class JiraConfig:
    """Jira connection configuration."""
    base_url: str
    email: str
    api_token: str
    project_key: Optional[str] = None

    @classmethod
    def from_env(cls) -> 'JiraConfig':
        """Load configuration from environment variables."""
        return cls(
            base_url=os.getenv('JIRA_BASE_URL', 'https://your-domain.atlassian.net'),
            email=os.getenv('JIRA_EMAIL', ''),
            api_token=os.getenv('JIRA_API_TOKEN', ''),
            project_key=os.getenv('JIRA_PROJECT_KEY')
        )


@dataclass
class SprintData:
    """Sprint information from Jira."""
    id: int
    name: str
    state: str  # active, closed, future
    start_date: Optional[str]
    end_date: Optional[str]
    goal: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class VelocityData:
    """Velocity calculation result."""
    team_id: str
    sprint_id: str
    sprint_name: str
    committed_points: float
    completed_points: float
    velocity: float
    completion_rate: float
    stories_completed: int
    stories_total: int
    average_velocity: float  # Rolling average

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class JiraMetricsProvider:
    """
    Fetches real-time metrics from Jira.

    Integrates with Jira REST API to retrieve:
    - Sprint data
    - Story points
    - Velocity calculations
    - Issue statistics
    """

    def __init__(self, config: Optional[JiraConfig] = None):
        self.config = config or JiraConfig.from_env()
        self._auth = HTTPBasicAuth(self.config.email, self.config.api_token)
        self._headers = {'Accept': 'application/json'}

    def get_active_sprint(self, board_id: int) -> Optional[SprintData]:
        """Get the currently active sprint for a board."""
        try:
            url = f"{self.config.base_url}/rest/agile/1.0/board/{board_id}/sprint"
            params = {'state': 'active'}

            response = requests.get(
                url,
                auth=self._auth,
                headers=self._headers,
                params=params,
                timeout=30
            )
            response.raise_for_status()

            data = response.json()
            sprints = data.get('values', [])

            if sprints:
                sprint = sprints[0]
                return SprintData(
                    id=sprint['id'],
                    name=sprint['name'],
                    state=sprint['state'],
                    start_date=sprint.get('startDate'),
                    end_date=sprint.get('endDate'),
                    goal=sprint.get('goal')
                )

            return None

        except Exception as e:
            logger.error(f"Error fetching active sprint: {e}")
            return None

    def get_sprint_velocity(
        self,
        team_id: str,
        board_id: int,
        sprint_id: Optional[int] = None
    ) -> Optional[VelocityData]:
        """
        Calculate velocity for a sprint.

        AC-2: Real-time Velocity calculation from Jira
        """
        try:
            # Get sprint if not provided
            if sprint_id is None:
                active_sprint = self.get_active_sprint(board_id)
                if not active_sprint:
                    logger.warning(f"No active sprint found for board {board_id}")
                    return None
                sprint_id = active_sprint.id
                sprint_name = active_sprint.name
            else:
                # Fetch sprint details
                sprint_url = f"{self.config.base_url}/rest/agile/1.0/sprint/{sprint_id}"
                sprint_response = requests.get(
                    sprint_url,
                    auth=self._auth,
                    headers=self._headers,
                    timeout=30
                )
                sprint_response.raise_for_status()
                sprint_data = sprint_response.json()
                sprint_name = sprint_data['name']

            # Get issues in sprint
            jql = f"sprint = {sprint_id}"
            issues_url = f"{self.config.base_url}/rest/api/3/search"
            params = {
                'jql': jql,
                'fields': 'status,customfield_10016',  # story points field
                'maxResults': 100
            }

            response = requests.get(
                issues_url,
                auth=self._auth,
                headers=self._headers,
                params=params,
                timeout=30
            )
            response.raise_for_status()

            issues = response.json().get('issues', [])

            # Calculate metrics
            total_points = 0.0
            completed_points = 0.0
            total_stories = 0
            completed_stories = 0

            for issue in issues:
                fields = issue.get('fields', {})
                points = fields.get('customfield_10016') or 0
                status = fields.get('status', {}).get('statusCategory', {}).get('key', '')

                total_points += float(points)
                total_stories += 1

                if status == 'done':
                    completed_points += float(points)
                    completed_stories += 1

            # Calculate completion rate
            completion_rate = (completed_points / total_points * 100) if total_points > 0 else 0

            # Get rolling average (last 5 sprints)
            average_velocity = self._get_average_velocity(board_id, 5)

            return VelocityData(
                team_id=team_id,
                sprint_id=str(sprint_id),
                sprint_name=sprint_name,
                committed_points=total_points,
                completed_points=completed_points,
                velocity=completed_points,
                completion_rate=completion_rate,
                stories_completed=completed_stories,
                stories_total=total_stories,
                average_velocity=average_velocity
            )

        except Exception as e:
            logger.error(f"Error calculating velocity: {e}")
            return None

    def _get_average_velocity(self, board_id: int, num_sprints: int = 5) -> float:
        """Calculate rolling average velocity from recent sprints."""
        try:
            url = f"{self.config.base_url}/rest/agile/1.0/board/{board_id}/sprint"
            params = {'state': 'closed', 'maxResults': num_sprints}

            response = requests.get(
                url,
                auth=self._auth,
                headers=self._headers,
                params=params,
                timeout=30
            )
            response.raise_for_status()

            sprints = response.json().get('values', [])
            if not sprints:
                return 0.0

            total_velocity = 0.0
            count = 0

            for sprint in sprints:
                # Get completed points for each sprint
                jql = f"sprint = {sprint['id']} AND status = Done"
                issues_url = f"{self.config.base_url}/rest/api/3/search"
                params = {
                    'jql': jql,
                    'fields': 'customfield_10016',
                    'maxResults': 100
                }

                issues_response = requests.get(
                    issues_url,
                    auth=self._auth,
                    headers=self._headers,
                    params=params,
                    timeout=30
                )
                issues_response.raise_for_status()

                sprint_points = sum(
                    float(issue.get('fields', {}).get('customfield_10016') or 0)
                    for issue in issues_response.json().get('issues', [])
                )

                total_velocity += sprint_points
                count += 1

            return total_velocity / count if count > 0 else 0.0

        except Exception as e:
            logger.error(f"Error calculating average velocity: {e}")
            return 0.0

    def get_team_task_metrics(
        self,
        project_key: str,
        days: int = 30
    ) -> Dict[str, Any]:
        """
        Get comprehensive task metrics for a team.

        AC-7: Jira integration for task metrics.
        """
        try:
            since_date = (datetime.utcnow() - timedelta(days=days)).strftime('%Y-%m-%d')

            metrics = {
                'project_key': project_key,
                'period_days': days,
                'issues_created': 0,
                'issues_resolved': 0,
                'issues_in_progress': 0,
                'bugs_created': 0,
                'bugs_resolved': 0,
                'average_resolution_time_hours': 0,
                'story_points_completed': 0,
                'by_priority': {},
                'by_type': {}
            }

            # Issues created in period
            jql_created = f"project = {project_key} AND created >= {since_date}"
            created_response = self._execute_search(jql_created)
            metrics['issues_created'] = created_response.get('total', 0)

            # Issues resolved in period
            jql_resolved = f"project = {project_key} AND resolved >= {since_date}"
            resolved_response = self._execute_search(jql_resolved)
            metrics['issues_resolved'] = resolved_response.get('total', 0)

            # Issues in progress
            jql_in_progress = f"project = {project_key} AND status = 'In Progress'"
            in_progress_response = self._execute_search(jql_in_progress)
            metrics['issues_in_progress'] = in_progress_response.get('total', 0)

            # Bugs
            jql_bugs_created = f"project = {project_key} AND issuetype = Bug AND created >= {since_date}"
            bugs_created = self._execute_search(jql_bugs_created)
            metrics['bugs_created'] = bugs_created.get('total', 0)

            jql_bugs_resolved = f"project = {project_key} AND issuetype = Bug AND resolved >= {since_date}"
            bugs_resolved = self._execute_search(jql_bugs_resolved)
            metrics['bugs_resolved'] = bugs_resolved.get('total', 0)

            return metrics

        except Exception as e:
            logger.error(f"Error fetching task metrics: {e}")
            return {}

    def _execute_search(self, jql: str, max_results: int = 100) -> Dict[str, Any]:
        """Execute a JQL search."""
        try:
            url = f"{self.config.base_url}/rest/api/3/search"
            params = {'jql': jql, 'maxResults': max_results}

            response = requests.get(
                url,
                auth=self._auth,
                headers=self._headers,
                params=params,
                timeout=30
            )
            response.raise_for_status()
            return response.json()

        except Exception as e:
            logger.error(f"JQL search error: {e}")
            return {'total': 0, 'issues': []}


def get_jira_metrics_provider(**kwargs) -> JiraMetricsProvider:
    """Get Jira metrics provider instance."""
    config = JiraConfig(**kwargs) if kwargs else None
    return JiraMetricsProvider(config=config)
