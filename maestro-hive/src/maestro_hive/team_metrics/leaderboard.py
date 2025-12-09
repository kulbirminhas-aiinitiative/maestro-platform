#!/usr/bin/env python3
"""
Leaderboard Service: Manages team rankings, badges, and gamification.

Implements AC-6: Gamification elements including:
- Leaderboard rankings
- Achievement badges
- A-F grades
- Performance streaks
"""

import json
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from .models import (
    TeamMetrics, TeamGrade, TeamRanking, Badge, BadgeType,
    SprintMetrics, QualityMetrics
)
from .grading_engine import GradingEngine

logger = logging.getLogger(__name__)


@dataclass
class LeaderboardConfig:
    """Configuration for leaderboard service."""
    storage_path: str = "/tmp/leaderboard_data.json"
    badge_cooldown_days: int = 7  # Days before same badge can be earned again
    streak_threshold_days: int = 5  # Days for streak tracking

    @classmethod
    def from_env(cls) -> 'LeaderboardConfig':
        return cls(
            storage_path=os.getenv('LEADERBOARD_STORAGE_PATH', '/tmp/leaderboard_data.json'),
            badge_cooldown_days=int(os.getenv('BADGE_COOLDOWN_DAYS', '7')),
            streak_threshold_days=int(os.getenv('STREAK_THRESHOLD_DAYS', '5'))
        )


class LeaderboardService:
    """
    Manages team leaderboard and gamification features.

    Implements AC-6: Gamification elements.

    Features:
    - Real-time leaderboard rankings
    - Achievement badge system
    - Performance streak tracking
    - Historical ranking data
    """

    def __init__(
        self,
        config: Optional[LeaderboardConfig] = None,
        grading_engine: Optional[GradingEngine] = None
    ):
        self.config = config or LeaderboardConfig.from_env()
        self.grading_engine = grading_engine or GradingEngine()
        self._leaderboard_data: Dict[str, Any] = {}
        self._load_data()

    def update_leaderboard(
        self,
        teams: List[TeamMetrics]
    ) -> List[TeamRanking]:
        """
        Update leaderboard with new team metrics.

        AC-6: Update rankings and assign badges.

        Returns:
            Updated list of TeamRanking objects
        """
        # Get previous rankings for comparison
        previous_rankings = self._get_previous_rankings()

        # Create new rankings
        rankings = self.grading_engine.create_rankings(teams, previous_rankings)

        # Assign badges based on performance
        for ranking in rankings:
            team_metrics = next(
                (t for t in teams if t.team_id == ranking.team_id),
                None
            )
            if team_metrics:
                badges = self._evaluate_badges(ranking, team_metrics)
                ranking.badges = badges

                # Update streak
                ranking.streak_days = self._calculate_streak(ranking.team_id)

        # Store updated leaderboard
        self._store_rankings(rankings)

        return rankings

    def get_leaderboard(
        self,
        limit: Optional[int] = None
    ) -> List[TeamRanking]:
        """
        Get current leaderboard.

        Args:
            limit: Optional limit on number of results

        Returns:
            List of TeamRanking objects sorted by rank
        """
        rankings_data = self._leaderboard_data.get('current_rankings', [])
        rankings = [TeamRanking.from_dict(r) for r in rankings_data]

        if limit:
            rankings = rankings[:limit]

        return rankings

    def get_team_ranking(self, team_id: str) -> Optional[TeamRanking]:
        """Get ranking for a specific team."""
        rankings = self.get_leaderboard()
        for ranking in rankings:
            if ranking.team_id == team_id:
                return ranking
        return None

    def get_team_badges(self, team_id: str) -> List[Badge]:
        """Get all badges earned by a team."""
        badges_data = self._leaderboard_data.get('badges', {}).get(team_id, [])
        return [Badge.from_dict(b) for b in badges_data]

    def get_grade_summary(self) -> Dict[str, Any]:
        """
        Get summary of grade distribution.

        AC-6: A-F grading visibility.
        """
        rankings = self.get_leaderboard()

        distribution = {'A': 0, 'B': 0, 'C': 0, 'D': 0, 'F': 0}
        total_score = 0

        for ranking in rankings:
            distribution[ranking.grade.value] += 1
            total_score += ranking.score

        avg_score = total_score / len(rankings) if rankings else 0

        return {
            'grade_distribution': distribution,
            'average_score': round(avg_score, 2),
            'average_grade': TeamGrade.from_score(avg_score).value,
            'total_teams': len(rankings),
            'top_performers': len([r for r in rankings if r.grade in [TeamGrade.A, TeamGrade.B]]),
            'needs_improvement': len([r for r in rankings if r.grade in [TeamGrade.D, TeamGrade.F]])
        }

    def get_movers(self, count: int = 5) -> Dict[str, List[TeamRanking]]:
        """
        Get biggest rank movers (up and down).

        Returns:
            Dict with 'risers' and 'fallers' lists
        """
        rankings = self.get_leaderboard()

        # Sort by rank change
        with_changes = [r for r in rankings if r.rank_change != 0]

        risers = sorted(
            [r for r in with_changes if r.rank_change > 0],
            key=lambda x: x.rank_change,
            reverse=True
        )[:count]

        fallers = sorted(
            [r for r in with_changes if r.rank_change < 0],
            key=lambda x: x.rank_change
        )[:count]

        return {
            'risers': risers,
            'fallers': fallers
        }

    def _evaluate_badges(
        self,
        ranking: TeamRanking,
        metrics: TeamMetrics
    ) -> List[Badge]:
        """
        Evaluate and assign badges based on performance.

        AC-6: Badge gamification system.
        """
        badges = []
        now = datetime.utcnow().isoformat()
        team_id = ranking.team_id

        # Check existing badges for cooldown
        existing_badges = self.get_team_badges(team_id)
        recent_badge_types = set()

        cutoff = datetime.utcnow() - timedelta(days=self.config.badge_cooldown_days)
        for badge in existing_badges:
            try:
                earned_at = datetime.fromisoformat(badge.earned_at.replace('Z', '+00:00'))
                if earned_at > cutoff:
                    recent_badge_types.add(badge.badge_type)
            except (ValueError, AttributeError):
                pass

        # Velocity Champion: Top velocity
        if ranking.rank == 1 and BadgeType.VELOCITY_CHAMPION not in recent_badge_types:
            badges.append(Badge(
                badge_type=BadgeType.VELOCITY_CHAMPION,
                earned_at=now,
                team_id=team_id,
                description="Highest velocity this sprint",
                icon="🏃"
            ))

        # Quality Leader: Quality score >= 90
        if metrics.quality_score >= 90 and BadgeType.QUALITY_LEADER not in recent_badge_types:
            badges.append(Badge(
                badge_type=BadgeType.QUALITY_LEADER,
                earned_at=now,
                team_id=team_id,
                description="Excellence in code quality",
                icon="⭐"
            ))

        # Artifact Master: High artifact generation
        if metrics.artifact_count >= 50 and BadgeType.ARTIFACT_MASTER not in recent_badge_types:
            badges.append(Badge(
                badge_type=BadgeType.ARTIFACT_MASTER,
                earned_at=now,
                team_id=team_id,
                description="Prolific artifact generation",
                icon="📦"
            ))

        # Consistency Star: Grade A or B for multiple periods
        if ranking.grade in [TeamGrade.A, TeamGrade.B]:
            streak = self._calculate_streak(team_id)
            if streak >= 3 and BadgeType.CONSISTENCY_STAR not in recent_badge_types:
                badges.append(Badge(
                    badge_type=BadgeType.CONSISTENCY_STAR,
                    earned_at=now,
                    team_id=team_id,
                    description=f"Consistent high performer ({streak} periods)",
                    icon="🌟"
                ))

        # Most Improved: Biggest positive rank change
        if ranking.rank_change >= 3 and BadgeType.MOST_IMPROVED not in recent_badge_types:
            badges.append(Badge(
                badge_type=BadgeType.MOST_IMPROVED,
                earned_at=now,
                team_id=team_id,
                description=f"Improved {ranking.rank_change} ranks",
                icon="📈"
            ))

        # Sprint Hero: 100% completion rate
        if hasattr(metrics, 'sprint_completion_rate'):
            if metrics.sprint_completion_rate >= 100 and BadgeType.SPRINT_HERO not in recent_badge_types:
                badges.append(Badge(
                    badge_type=BadgeType.SPRINT_HERO,
                    earned_at=now,
                    team_id=team_id,
                    description="Completed all sprint commitments",
                    icon="🦸"
                ))

        # Test Champion: Test coverage >= 90%
        if metrics.test_coverage >= 0.90 and BadgeType.TEST_CHAMPION not in recent_badge_types:
            badges.append(Badge(
                badge_type=BadgeType.TEST_CHAMPION,
                earned_at=now,
                team_id=team_id,
                description="Outstanding test coverage",
                icon="🧪"
            ))

        # Store new badges
        self._store_badges(team_id, badges)

        return badges

    def _calculate_streak(self, team_id: str) -> int:
        """Calculate consecutive high-performance periods."""
        history = self._leaderboard_data.get('history', {}).get(team_id, [])

        if not history:
            return 0

        streak = 0
        for entry in reversed(history):
            grade = entry.get('grade', 'F')
            if grade in ['A', 'B']:
                streak += 1
            else:
                break

        return streak

    def _get_previous_rankings(self) -> Dict[str, int]:
        """Get previous ranking positions."""
        rankings_data = self._leaderboard_data.get('current_rankings', [])
        return {r['team_id']: r['rank'] for r in rankings_data}

    def _store_rankings(self, rankings: List[TeamRanking]) -> None:
        """Store rankings to persistent storage."""
        # Update current rankings
        self._leaderboard_data['current_rankings'] = [r.to_dict() for r in rankings]
        self._leaderboard_data['updated_at'] = datetime.utcnow().isoformat()

        # Update history
        if 'history' not in self._leaderboard_data:
            self._leaderboard_data['history'] = {}

        for ranking in rankings:
            if ranking.team_id not in self._leaderboard_data['history']:
                self._leaderboard_data['history'][ranking.team_id] = []

            self._leaderboard_data['history'][ranking.team_id].append({
                'rank': ranking.rank,
                'score': ranking.score,
                'grade': ranking.grade.value,
                'timestamp': datetime.utcnow().isoformat()
            })

            # Keep only last 20 entries
            if len(self._leaderboard_data['history'][ranking.team_id]) > 20:
                self._leaderboard_data['history'][ranking.team_id] = \
                    self._leaderboard_data['history'][ranking.team_id][-20:]

        self._save_data()

    def _store_badges(self, team_id: str, badges: List[Badge]) -> None:
        """Store badges for a team."""
        if 'badges' not in self._leaderboard_data:
            self._leaderboard_data['badges'] = {}

        if team_id not in self._leaderboard_data['badges']:
            self._leaderboard_data['badges'][team_id] = []

        for badge in badges:
            self._leaderboard_data['badges'][team_id].append(badge.to_dict())

        self._save_data()

    def _load_data(self) -> None:
        """Load leaderboard data from storage."""
        try:
            if os.path.exists(self.config.storage_path):
                with open(self.config.storage_path, 'r') as f:
                    self._leaderboard_data = json.load(f)
            else:
                self._leaderboard_data = {}
        except Exception as e:
            logger.error(f"Error loading leaderboard data: {e}")
            self._leaderboard_data = {}

    def _save_data(self) -> None:
        """Save leaderboard data to storage."""
        try:
            with open(self.config.storage_path, 'w') as f:
                json.dump(self._leaderboard_data, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving leaderboard data: {e}")

    def get_historical_rankings(
        self,
        team_id: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get historical ranking data for a team."""
        history = self._leaderboard_data.get('history', {}).get(team_id, [])
        return history[-limit:] if history else []

    def get_badge_leaderboard(self) -> List[Dict[str, Any]]:
        """Get teams ranked by badge count."""
        badges_data = self._leaderboard_data.get('badges', {})

        badge_counts = [
            {
                'team_id': team_id,
                'badge_count': len(badges),
                'badge_types': list(set(b.get('badge_type', '') for b in badges))
            }
            for team_id, badges in badges_data.items()
        ]

        badge_counts.sort(key=lambda x: x['badge_count'], reverse=True)
        return badge_counts


def get_leaderboard_service(**kwargs) -> LeaderboardService:
    """Get a configured leaderboard service instance."""
    config = LeaderboardConfig(**kwargs) if kwargs else None
    return LeaderboardService(config=config)
