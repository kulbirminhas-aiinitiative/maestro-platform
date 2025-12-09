#!/usr/bin/env python3
"""
Grading Engine: Calculates team scores and grades using weighted algorithms.

Implements AC-5: Team Ranking/Grading with weighted scoring algorithm.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from .models import TeamMetrics, TeamGrade, TeamRanking

logger = logging.getLogger(__name__)


@dataclass
class GradingWeights:
    """Configurable weights for scoring algorithm."""
    velocity: float = 0.25
    quality_score: float = 0.30
    artifact_count: float = 0.15
    commit_frequency: float = 0.15
    test_coverage: float = 0.15

    def to_dict(self) -> Dict[str, float]:
        return {
            'velocity': self.velocity,
            'quality_score': self.quality_score,
            'artifact_count': self.artifact_count,
            'commit_frequency': self.commit_frequency,
            'test_coverage': self.test_coverage
        }

    def validate(self) -> bool:
        """Validate that weights sum to 1.0."""
        total = sum(self.to_dict().values())
        return 0.99 <= total <= 1.01  # Allow small floating point variance


@dataclass
class NormalizationConfig:
    """Configuration for metric normalization."""
    velocity_max: float = 50.0  # Story points for 100%
    artifact_max: int = 100  # Artifacts for 100%
    commit_max: float = 10.0  # Commits/day for 100%

    def to_dict(self) -> Dict[str, Any]:
        return {
            'velocity_max': self.velocity_max,
            'artifact_max': self.artifact_max,
            'commit_max': self.commit_max
        }


class GradingEngine:
    """
    Calculates team scores and grades using weighted algorithms.

    Implements AC-5: Team Ranking/Grading with weighted scoring algorithm.

    The grading system uses:
    - Weighted scoring across multiple metrics
    - Normalization to 0-100 scale
    - A-F grade conversion
    - Historical trend analysis
    """

    def __init__(
        self,
        weights: Optional[GradingWeights] = None,
        normalization: Optional[NormalizationConfig] = None
    ):
        self.weights = weights or GradingWeights()
        self.normalization = normalization or NormalizationConfig()
        self._historical_scores: Dict[str, List[float]] = {}

    def calculate_score(self, metrics: TeamMetrics) -> float:
        """
        Calculate overall score for a team.

        AC-5: Weighted scoring algorithm implementation.

        Returns:
            Score on 0-100 scale
        """
        weights = self.weights.to_dict()

        # Normalize each metric to 0-100 scale
        velocity_score = self._normalize_velocity(metrics.velocity)
        quality_score = metrics.quality_score  # Already 0-100
        artifact_score = self._normalize_artifacts(metrics.artifact_count)
        commit_score = self._normalize_commits(metrics.commit_frequency)
        coverage_score = metrics.test_coverage * 100  # Convert 0-1 to 0-100

        # Apply weights
        score = (
            velocity_score * weights['velocity'] +
            quality_score * weights['quality_score'] +
            artifact_score * weights['artifact_count'] +
            commit_score * weights['commit_frequency'] +
            coverage_score * weights['test_coverage']
        )

        # Update metrics object
        metrics.overall_score = round(score, 2)
        metrics.grade = TeamGrade.from_score(score)

        # Store for historical tracking
        self._record_score(metrics.team_id, score)

        return score

    def calculate_grade(self, score: float) -> TeamGrade:
        """Convert numeric score to letter grade."""
        return TeamGrade.from_score(score)

    def grade_all_teams(
        self,
        teams: List[TeamMetrics]
    ) -> List[Tuple[TeamMetrics, float, TeamGrade]]:
        """
        Grade multiple teams and return sorted results.

        Returns:
            List of (TeamMetrics, score, grade) tuples sorted by score descending
        """
        results = []

        for team in teams:
            score = self.calculate_score(team)
            grade = team.grade or self.calculate_grade(score)
            results.append((team, score, grade))

        # Sort by score descending
        results.sort(key=lambda x: x[1], reverse=True)

        return results

    def create_rankings(
        self,
        teams: List[TeamMetrics],
        previous_rankings: Optional[Dict[str, int]] = None
    ) -> List[TeamRanking]:
        """
        Create ranked leaderboard from team metrics.

        Args:
            teams: List of team metrics
            previous_rankings: Dict mapping team_id to previous rank

        Returns:
            List of TeamRanking objects sorted by rank
        """
        graded_teams = self.grade_all_teams(teams)
        rankings = []

        for rank, (team, score, grade) in enumerate(graded_teams, start=1):
            previous_rank = None
            rank_change = 0

            if previous_rankings and team.team_id in previous_rankings:
                previous_rank = previous_rankings[team.team_id]
                rank_change = previous_rank - rank  # Positive = improved

            trend = self._calculate_trend(team.team_id)

            ranking = TeamRanking(
                rank=rank,
                team_id=team.team_id,
                team_name=team.team_name,
                score=score,
                grade=grade,
                previous_rank=previous_rank,
                rank_change=rank_change,
                badges=[],  # Badges assigned separately
                streak_days=0,  # Would track consistent performance
                trend=trend
            )

            rankings.append(ranking)

        return rankings

    def get_grade_distribution(
        self,
        teams: List[TeamMetrics]
    ) -> Dict[str, int]:
        """Get distribution of grades across teams."""
        distribution = {'A': 0, 'B': 0, 'C': 0, 'D': 0, 'F': 0}

        for team in teams:
            if team.grade:
                distribution[team.grade.value] += 1

        return distribution

    def get_percentile(
        self,
        score: float,
        all_scores: List[float]
    ) -> float:
        """Calculate percentile rank for a score."""
        if not all_scores:
            return 0.0

        below = sum(1 for s in all_scores if s < score)
        return (below / len(all_scores)) * 100

    def _normalize_velocity(self, velocity: float) -> float:
        """Normalize velocity to 0-100 scale."""
        if velocity <= 0:
            return 0.0
        return min(100, (velocity / self.normalization.velocity_max) * 100)

    def _normalize_artifacts(self, count: int) -> float:
        """Normalize artifact count to 0-100 scale."""
        if count <= 0:
            return 0.0
        return min(100, (count / self.normalization.artifact_max) * 100)

    def _normalize_commits(self, frequency: float) -> float:
        """Normalize commit frequency to 0-100 scale."""
        if frequency <= 0:
            return 0.0
        return min(100, (frequency / self.normalization.commit_max) * 100)

    def _record_score(self, team_id: str, score: float) -> None:
        """Record score for historical tracking."""
        if team_id not in self._historical_scores:
            self._historical_scores[team_id] = []

        self._historical_scores[team_id].append(score)

        # Keep only last 10 scores
        if len(self._historical_scores[team_id]) > 10:
            self._historical_scores[team_id] = self._historical_scores[team_id][-10:]

    def _calculate_trend(self, team_id: str) -> str:
        """Calculate performance trend from historical data."""
        history = self._historical_scores.get(team_id, [])

        if len(history) < 2:
            return "stable"

        # Compare recent average to older average
        midpoint = len(history) // 2
        older_avg = sum(history[:midpoint]) / midpoint
        recent_avg = sum(history[midpoint:]) / (len(history) - midpoint)

        diff = recent_avg - older_avg

        if diff > 5:
            return "improving"
        elif diff < -5:
            return "declining"
        else:
            return "stable"

    def get_improvement_recommendations(
        self,
        metrics: TeamMetrics
    ) -> List[Dict[str, Any]]:
        """
        Generate improvement recommendations based on metrics.

        Returns list of recommendations with:
        - area: The metric area to improve
        - current_value: Current metric value
        - target_value: Suggested target
        - impact: Estimated score impact
        """
        recommendations = []
        weights = self.weights.to_dict()

        # Check velocity
        velocity_score = self._normalize_velocity(metrics.velocity)
        if velocity_score < 70:
            recommendations.append({
                'area': 'velocity',
                'current_value': metrics.velocity,
                'target_value': self.normalization.velocity_max * 0.7,
                'impact': (70 - velocity_score) * weights['velocity'],
                'suggestion': 'Improve sprint planning and story point estimation'
            })

        # Check quality
        if metrics.quality_score < 70:
            recommendations.append({
                'area': 'quality_score',
                'current_value': metrics.quality_score,
                'target_value': 70,
                'impact': (70 - metrics.quality_score) * weights['quality_score'],
                'suggestion': 'Focus on code reviews and testing practices'
            })

        # Check test coverage
        coverage_score = metrics.test_coverage * 100
        if coverage_score < 70:
            recommendations.append({
                'area': 'test_coverage',
                'current_value': metrics.test_coverage,
                'target_value': 0.70,
                'impact': (70 - coverage_score) * weights['test_coverage'],
                'suggestion': 'Increase unit and integration test coverage'
            })

        # Check commit frequency
        commit_score = self._normalize_commits(metrics.commit_frequency)
        if commit_score < 50:
            recommendations.append({
                'area': 'commit_frequency',
                'current_value': metrics.commit_frequency,
                'target_value': self.normalization.commit_max * 0.5,
                'impact': (50 - commit_score) * weights['commit_frequency'],
                'suggestion': 'Encourage smaller, more frequent commits'
            })

        # Sort by impact
        recommendations.sort(key=lambda x: x['impact'], reverse=True)

        return recommendations


def get_grading_engine(**kwargs) -> GradingEngine:
    """Get a configured grading engine instance."""
    weights = None
    normalization = None

    if 'weights' in kwargs:
        weights = GradingWeights(**kwargs['weights'])
    if 'normalization' in kwargs:
        normalization = NormalizationConfig(**kwargs['normalization'])

    return GradingEngine(weights=weights, normalization=normalization)
