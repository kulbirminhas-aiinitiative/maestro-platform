"""
Team Metrics Module: Real-time team performance metrics and grading system.

Implements MD-2385 acceptance criteria:
- AC-1: Real data from DDE performance tracker
- AC-2: Real-time Velocity calculation from Jira
- AC-3: Real-time Quality Score aggregation
- AC-4: Real-time Artifact Generation tracking
- AC-5: Team Ranking/Grading with weighted scoring
- AC-6: Gamification (leaderboard, badges, grades)
- AC-7: Jira integration for task metrics
- AC-8: Git integration for commit metrics
"""

from .models import TeamMetrics, TeamGrade, TeamRanking, Badge
from .collector import TeamMetricsCollector
from .grading_engine import GradingEngine
from .leaderboard import LeaderboardService
from .jira_metrics import JiraMetricsProvider
from .git_metrics import GitMetricsProvider

__all__ = [
    'TeamMetrics',
    'TeamGrade',
    'TeamRanking',
    'Badge',
    'TeamMetricsCollector',
    'GradingEngine',
    'LeaderboardService',
    'JiraMetricsProvider',
    'GitMetricsProvider',
]
