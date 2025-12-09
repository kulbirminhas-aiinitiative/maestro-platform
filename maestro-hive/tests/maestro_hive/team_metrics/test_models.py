#!/usr/bin/env python3
"""
Tests for team_metrics models.

Tests AC-5: Weighted scoring algorithm.
Tests AC-6: A-F grading system.
"""

import pytest
from datetime import datetime

from maestro_hive.team_metrics.models import (
    TeamMetrics, TeamGrade, TeamRanking, Badge, BadgeType,
    SprintMetrics, QualityMetrics, ArtifactMetrics
)


class TestTeamGrade:
    """Tests for TeamGrade enum and scoring."""

    def test_grade_from_score_a(self):
        """AC-6: Grade A for scores 90-100."""
        assert TeamGrade.from_score(100) == TeamGrade.A
        assert TeamGrade.from_score(95) == TeamGrade.A
        assert TeamGrade.from_score(90) == TeamGrade.A

    def test_grade_from_score_b(self):
        """AC-6: Grade B for scores 80-89."""
        assert TeamGrade.from_score(89) == TeamGrade.B
        assert TeamGrade.from_score(85) == TeamGrade.B
        assert TeamGrade.from_score(80) == TeamGrade.B

    def test_grade_from_score_c(self):
        """AC-6: Grade C for scores 70-79."""
        assert TeamGrade.from_score(79) == TeamGrade.C
        assert TeamGrade.from_score(75) == TeamGrade.C
        assert TeamGrade.from_score(70) == TeamGrade.C

    def test_grade_from_score_d(self):
        """AC-6: Grade D for scores 60-69."""
        assert TeamGrade.from_score(69) == TeamGrade.D
        assert TeamGrade.from_score(65) == TeamGrade.D
        assert TeamGrade.from_score(60) == TeamGrade.D

    def test_grade_from_score_f(self):
        """AC-6: Grade F for scores 0-59."""
        assert TeamGrade.from_score(59) == TeamGrade.F
        assert TeamGrade.from_score(30) == TeamGrade.F
        assert TeamGrade.from_score(0) == TeamGrade.F

    def test_grade_description(self):
        """Test grade descriptions."""
        assert TeamGrade.A.description == 'Exceptional Performance'
        assert TeamGrade.F.description == 'Needs Improvement'

    def test_grade_to_dict(self):
        """Test grade serialization."""
        data = TeamGrade.A.to_dict()
        assert data['grade'] == 'A'
        assert 'description' in data


class TestTeamMetrics:
    """Tests for TeamMetrics model."""

    def test_team_metrics_creation(self):
        """Test basic TeamMetrics creation."""
        metrics = TeamMetrics(
            team_id='team-1',
            team_name='Alpha Team',
            velocity=35.0,
            quality_score=85.0,
            artifact_count=50,
            commit_frequency=5.0,
            code_review_turnaround=4.0,
            test_coverage=0.80
        )

        assert metrics.team_id == 'team-1'
        assert metrics.team_name == 'Alpha Team'
        assert metrics.velocity == 35.0
        assert metrics.quality_score == 85.0

    def test_calculate_score_default_weights(self):
        """AC-5: Test weighted scoring with default weights."""
        metrics = TeamMetrics(
            team_id='team-1',
            team_name='Alpha Team',
            velocity=50.0,  # 100% normalized
            quality_score=100.0,  # 100%
            artifact_count=100,  # 100% normalized
            commit_frequency=10.0,  # 100% normalized
            code_review_turnaround=2.0,
            test_coverage=1.0  # 100%
        )

        score = metrics.calculate_score()

        # With all metrics at 100%, score should be 100
        assert score == 100.0
        assert metrics.grade == TeamGrade.A

    def test_calculate_score_partial_metrics(self):
        """AC-5: Test weighted scoring with partial metrics."""
        metrics = TeamMetrics(
            team_id='team-1',
            team_name='Alpha Team',
            velocity=25.0,  # 50% normalized
            quality_score=80.0,  # 80%
            artifact_count=50,  # 50% normalized
            commit_frequency=5.0,  # 50% normalized
            code_review_turnaround=4.0,
            test_coverage=0.70  # 70%
        )

        score = metrics.calculate_score()

        # Expected: 50*0.25 + 80*0.30 + 50*0.15 + 50*0.15 + 70*0.15 = 63
        expected = 12.5 + 24.0 + 7.5 + 7.5 + 10.5
        assert abs(score - expected) < 0.1
        assert metrics.grade == TeamGrade.D

    def test_calculate_score_custom_weights(self):
        """AC-5: Test weighted scoring with custom weights."""
        metrics = TeamMetrics(
            team_id='team-1',
            team_name='Alpha Team',
            velocity=40.0,
            quality_score=90.0,
            artifact_count=80,
            commit_frequency=8.0,
            code_review_turnaround=3.0,
            test_coverage=0.85
        )

        custom_weights = {
            'velocity': 0.40,
            'quality_score': 0.20,
            'artifact_count': 0.15,
            'commit_frequency': 0.15,
            'test_coverage': 0.10
        }

        score = metrics.calculate_score(custom_weights)
        assert score > 0
        assert metrics.overall_score == score

    def test_to_dict(self):
        """Test TeamMetrics serialization."""
        metrics = TeamMetrics(
            team_id='team-1',
            team_name='Alpha Team',
            velocity=35.0,
            quality_score=85.0,
            artifact_count=50,
            commit_frequency=5.0,
            code_review_turnaround=4.0,
            test_coverage=0.80
        )
        metrics.calculate_score()

        data = metrics.to_dict()

        assert data['team_id'] == 'team-1'
        assert data['velocity'] == 35.0
        assert data['grade'] == 'B' or data['grade'] == 'C'  # Depends on calculated score

    def test_from_dict(self):
        """Test TeamMetrics deserialization."""
        data = {
            'team_id': 'team-1',
            'team_name': 'Alpha Team',
            'velocity': 35.0,
            'quality_score': 85.0,
            'artifact_count': 50,
            'commit_frequency': 5.0,
            'code_review_turnaround': 4.0,
            'test_coverage': 0.80,
            'grade': 'B',
            'jira_metrics': {},
            'git_metrics': {},
            'dde_metrics': {}
        }

        metrics = TeamMetrics.from_dict(data)
        assert metrics.team_id == 'team-1'
        assert metrics.grade == TeamGrade.B


class TestTeamRanking:
    """Tests for TeamRanking model."""

    def test_ranking_creation(self):
        """Test TeamRanking creation."""
        ranking = TeamRanking(
            rank=1,
            team_id='team-1',
            team_name='Alpha Team',
            score=95.0,
            grade=TeamGrade.A,
            previous_rank=3,
            rank_change=2,
            trend='improving'
        )

        assert ranking.rank == 1
        assert ranking.rank_change == 2
        assert ranking.trend == 'improving'

    def test_ranking_to_dict(self):
        """Test TeamRanking serialization."""
        ranking = TeamRanking(
            rank=1,
            team_id='team-1',
            team_name='Alpha Team',
            score=95.0,
            grade=TeamGrade.A
        )

        data = ranking.to_dict()
        assert data['rank'] == 1
        assert data['grade'] == 'A'
        assert data['badges'] == []


class TestBadge:
    """Tests for Badge model."""

    def test_badge_creation(self):
        """AC-6: Test badge creation."""
        badge = Badge(
            badge_type=BadgeType.VELOCITY_CHAMPION,
            earned_at='2024-01-01T00:00:00Z',
            team_id='team-1',
            description='Highest velocity this sprint',
            icon='🏃'
        )

        assert badge.badge_type == BadgeType.VELOCITY_CHAMPION
        assert badge.icon == '🏃'

    def test_badge_to_dict(self):
        """Test badge serialization."""
        badge = Badge(
            badge_type=BadgeType.QUALITY_LEADER,
            earned_at='2024-01-01T00:00:00Z',
            team_id='team-1',
            description='Excellence in code quality'
        )

        data = badge.to_dict()
        assert data['badge_type'] == 'quality_leader'

    def test_badge_from_dict(self):
        """Test badge deserialization."""
        data = {
            'badge_type': 'sprint_hero',
            'earned_at': '2024-01-01T00:00:00Z',
            'team_id': 'team-1',
            'description': 'Completed all sprint commitments',
            'icon': '🦸'
        }

        badge = Badge.from_dict(data)
        assert badge.badge_type == BadgeType.SPRINT_HERO


class TestQualityMetrics:
    """Tests for QualityMetrics model."""

    def test_quality_metrics_creation(self):
        """AC-3: Test quality metrics creation."""
        metrics = QualityMetrics(
            team_id='team-1',
            timestamp='2024-01-01T00:00:00Z',
            code_quality_score=90.0,
            test_pass_rate=95.0,
            bug_density=5.0,
            documentation_coverage=80.0,
            security_score=85.0,
            performance_score=88.0,
            overall_quality=0.0
        )

        assert metrics.code_quality_score == 90.0
        assert metrics.test_pass_rate == 95.0

    def test_calculate_overall(self):
        """AC-3: Test overall quality calculation."""
        metrics = QualityMetrics(
            team_id='team-1',
            timestamp='2024-01-01T00:00:00Z',
            code_quality_score=80.0,
            test_pass_rate=90.0,
            bug_density=10.0,
            documentation_coverage=70.0,
            security_score=85.0,
            performance_score=80.0,
            overall_quality=0.0
        )

        overall = metrics.calculate_overall()

        # Expected: 80*0.25 + 90*0.25 + (100-10)*0.15 + 70*0.10 + 85*0.15 + 80*0.10
        expected = 20 + 22.5 + 13.5 + 7 + 12.75 + 8
        assert abs(overall - expected) < 0.1


class TestSprintMetrics:
    """Tests for SprintMetrics model."""

    def test_sprint_metrics_creation(self):
        """AC-2: Test sprint metrics creation."""
        metrics = SprintMetrics(
            sprint_id='sprint-1',
            sprint_name='Sprint 23',
            team_id='team-1',
            start_date='2024-01-01',
            end_date='2024-01-14',
            story_points_committed=40,
            story_points_completed=35,
            stories_committed=10,
            stories_completed=8,
            bugs_resolved=5,
            velocity=35.0,
            completion_rate=87.5
        )

        assert metrics.velocity == 35.0
        assert metrics.completion_rate == 87.5

    def test_sprint_metrics_to_dict(self):
        """Test sprint metrics serialization."""
        metrics = SprintMetrics(
            sprint_id='sprint-1',
            sprint_name='Sprint 23',
            team_id='team-1',
            start_date='2024-01-01',
            end_date='2024-01-14',
            story_points_committed=40,
            story_points_completed=35,
            stories_committed=10,
            stories_completed=8,
            bugs_resolved=5,
            velocity=35.0,
            completion_rate=87.5
        )

        data = metrics.to_dict()
        assert data['sprint_id'] == 'sprint-1'
        assert data['velocity'] == 35.0
