#!/usr/bin/env python3
"""
Data models for team metrics system.

Implements:
- TeamMetrics: Core metrics data structure
- TeamGrade: A-F grading enum
- TeamRanking: Leaderboard position
- Badge: Gamification achievement
"""

import json
import logging
from dataclasses import dataclass, asdict, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class TeamGrade(Enum):
    """Team performance grades (A-F scale)."""
    A = "A"  # 90-100: Exceptional
    B = "B"  # 80-89: Above Average
    C = "C"  # 70-79: Average
    D = "D"  # 60-69: Below Average
    F = "F"  # 0-59: Failing

    @classmethod
    def from_score(cls, score: float) -> 'TeamGrade':
        """Convert numeric score to grade."""
        if score >= 90:
            return cls.A
        elif score >= 80:
            return cls.B
        elif score >= 70:
            return cls.C
        elif score >= 60:
            return cls.D
        else:
            return cls.F

    def to_dict(self) -> Dict[str, Any]:
        return {
            'grade': self.value,
            'description': self.description
        }

    @property
    def description(self) -> str:
        descriptions = {
            'A': 'Exceptional Performance',
            'B': 'Above Average',
            'C': 'Average',
            'D': 'Below Average',
            'F': 'Needs Improvement'
        }
        return descriptions.get(self.value, 'Unknown')


class BadgeType(Enum):
    """Types of achievement badges."""
    VELOCITY_CHAMPION = "velocity_champion"
    QUALITY_LEADER = "quality_leader"
    ARTIFACT_MASTER = "artifact_master"
    CONSISTENCY_STAR = "consistency_star"
    MOST_IMPROVED = "most_improved"
    SPRINT_HERO = "sprint_hero"
    CODE_REVIEWER = "code_reviewer"
    TEST_CHAMPION = "test_champion"


@dataclass
class Badge:
    """Achievement badge for gamification."""
    badge_type: BadgeType
    earned_at: str
    team_id: str
    description: str
    icon: str = ""

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data['badge_type'] = self.badge_type.value
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Badge':
        data['badge_type'] = BadgeType(data['badge_type'])
        return cls(**data)


@dataclass
class TeamMetrics:
    """
    Core team performance metrics.

    Implements AC-1, AC-2, AC-3, AC-4:
    - velocity: Story points completed per sprint (from Jira)
    - quality_score: Aggregated quality from agent execution
    - artifact_count: Workflow outputs tracked
    - commit_frequency: Commits per day
    - code_review_turnaround: Hours to complete reviews
    - test_coverage: Percentage of code covered
    """
    team_id: str
    team_name: str
    velocity: float  # Story points per sprint (AC-2)
    quality_score: float  # 0-100 scale (AC-3)
    artifact_count: int  # Generated artifacts (AC-4)
    commit_frequency: float  # Commits per day
    code_review_turnaround: float  # Hours
    test_coverage: float  # 0.0-1.0
    updated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    sprint_id: Optional[str] = None
    period_start: Optional[str] = None
    period_end: Optional[str] = None

    # Derived metrics
    overall_score: Optional[float] = None
    grade: Optional[TeamGrade] = None
    rank: Optional[int] = None

    # Detailed breakdowns
    jira_metrics: Dict[str, Any] = field(default_factory=dict)
    git_metrics: Dict[str, Any] = field(default_factory=dict)
    dde_metrics: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        if self.grade:
            data['grade'] = self.grade.value
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TeamMetrics':
        if 'grade' in data and data['grade']:
            data['grade'] = TeamGrade(data['grade'])
        return cls(**data)

    def calculate_score(self, weights: Optional[Dict[str, float]] = None) -> float:
        """
        Calculate overall score using weighted algorithm.

        Implements AC-5: Weighted scoring algorithm.
        """
        if weights is None:
            weights = {
                'velocity': 0.25,
                'quality_score': 0.30,
                'artifact_count': 0.15,
                'commit_frequency': 0.15,
                'test_coverage': 0.15
            }

        # Normalize metrics to 0-100 scale
        velocity_score = min(100, (self.velocity / 50) * 100)  # 50 points = 100%
        quality_score = self.quality_score  # Already 0-100
        artifact_score = min(100, (self.artifact_count / 100) * 100)  # 100 artifacts = 100%
        commit_score = min(100, (self.commit_frequency / 10) * 100)  # 10 commits/day = 100%
        coverage_score = self.test_coverage * 100  # Convert to percentage

        self.overall_score = (
            velocity_score * weights['velocity'] +
            quality_score * weights['quality_score'] +
            artifact_score * weights['artifact_count'] +
            commit_score * weights['commit_frequency'] +
            coverage_score * weights['test_coverage']
        )

        self.grade = TeamGrade.from_score(self.overall_score)
        return self.overall_score


@dataclass
class TeamRanking:
    """
    Team ranking for leaderboard.

    Implements AC-6: Gamification elements.
    """
    rank: int
    team_id: str
    team_name: str
    score: float
    grade: TeamGrade
    previous_rank: Optional[int] = None
    rank_change: int = 0
    badges: List[Badge] = field(default_factory=list)
    streak_days: int = 0
    trend: str = "stable"  # improving, declining, stable

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data['grade'] = self.grade.value
        data['badges'] = [b.to_dict() for b in self.badges]
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TeamRanking':
        data['grade'] = TeamGrade(data['grade'])
        if 'badges' in data:
            data['badges'] = [Badge.from_dict(b) for b in data['badges']]
        return cls(**data)


@dataclass
class SprintMetrics:
    """Sprint-specific metrics for velocity tracking."""
    sprint_id: str
    sprint_name: str
    team_id: str
    start_date: str
    end_date: str
    story_points_committed: int
    story_points_completed: int
    stories_committed: int
    stories_completed: int
    bugs_resolved: int
    velocity: float
    completion_rate: float

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class QualityMetrics:
    """Quality-specific metrics from agent execution."""
    team_id: str
    timestamp: str
    code_quality_score: float
    test_pass_rate: float
    bug_density: float
    documentation_coverage: float
    security_score: float
    performance_score: float
    overall_quality: float

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def calculate_overall(self) -> float:
        """Calculate overall quality score."""
        self.overall_quality = (
            self.code_quality_score * 0.25 +
            self.test_pass_rate * 0.25 +
            (100 - self.bug_density) * 0.15 +
            self.documentation_coverage * 0.10 +
            self.security_score * 0.15 +
            self.performance_score * 0.10
        )
        return self.overall_quality


@dataclass
class ArtifactMetrics:
    """Artifact generation tracking."""
    team_id: str
    period: str
    artifacts_generated: int
    artifact_types: Dict[str, int] = field(default_factory=dict)
    workflow_completions: int = 0
    successful_deployments: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
