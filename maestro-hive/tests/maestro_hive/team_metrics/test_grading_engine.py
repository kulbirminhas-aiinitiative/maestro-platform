#!/usr/bin/env python3
"""
Tests for grading engine.

Tests AC-5: Team Ranking/Grading with weighted scoring algorithm.
"""

import pytest

from maestro_hive.team_metrics.models import TeamMetrics, TeamGrade
from maestro_hive.team_metrics.grading_engine import (
    GradingEngine, GradingWeights, NormalizationConfig, get_grading_engine
)


class TestGradingWeights:
    """Tests for GradingWeights configuration."""

    def test_default_weights(self):
        """Test default weight configuration."""
        weights = GradingWeights()

        assert weights.velocity == 0.25
        assert weights.quality_score == 0.30
        assert weights.artifact_count == 0.15
        assert weights.commit_frequency == 0.15
        assert weights.test_coverage == 0.15

    def test_weights_validation_valid(self):
        """Test valid weights sum to 1.0."""
        weights = GradingWeights()
        assert weights.validate() is True

    def test_weights_validation_invalid(self):
        """Test invalid weights detection."""
        weights = GradingWeights(
            velocity=0.50,
            quality_score=0.30,
            artifact_count=0.15,
            commit_frequency=0.15,
            test_coverage=0.15
        )
        assert weights.validate() is False

    def test_weights_to_dict(self):
        """Test weights serialization."""
        weights = GradingWeights()
        data = weights.to_dict()

        assert 'velocity' in data
        assert data['velocity'] == 0.25


class TestNormalizationConfig:
    """Tests for NormalizationConfig."""

    def test_default_normalization(self):
        """Test default normalization values."""
        config = NormalizationConfig()

        assert config.velocity_max == 50.0
        assert config.artifact_max == 100
        assert config.commit_max == 10.0


class TestGradingEngine:
    """Tests for GradingEngine."""

    @pytest.fixture
    def engine(self):
        """Create a grading engine instance."""
        return GradingEngine()

    @pytest.fixture
    def sample_metrics(self):
        """Create sample team metrics."""
        return TeamMetrics(
            team_id='team-1',
            team_name='Alpha Team',
            velocity=35.0,
            quality_score=85.0,
            artifact_count=60,
            commit_frequency=7.0,
            code_review_turnaround=3.0,
            test_coverage=0.80
        )

    def test_calculate_score(self, engine, sample_metrics):
        """AC-5: Test score calculation."""
        score = engine.calculate_score(sample_metrics)

        assert 0 <= score <= 100
        assert sample_metrics.overall_score == score
        assert sample_metrics.grade is not None

    def test_calculate_score_perfect_metrics(self, engine):
        """AC-5: Test perfect score calculation."""
        perfect_metrics = TeamMetrics(
            team_id='team-1',
            team_name='Alpha Team',
            velocity=50.0,
            quality_score=100.0,
            artifact_count=100,
            commit_frequency=10.0,
            code_review_turnaround=1.0,
            test_coverage=1.0
        )

        score = engine.calculate_score(perfect_metrics)
        assert score == 100.0
        assert perfect_metrics.grade == TeamGrade.A

    def test_calculate_score_zero_metrics(self, engine):
        """AC-5: Test zero score calculation."""
        zero_metrics = TeamMetrics(
            team_id='team-1',
            team_name='Alpha Team',
            velocity=0.0,
            quality_score=0.0,
            artifact_count=0,
            commit_frequency=0.0,
            code_review_turnaround=0.0,
            test_coverage=0.0
        )

        score = engine.calculate_score(zero_metrics)
        assert score == 0.0
        assert zero_metrics.grade == TeamGrade.F

    def test_calculate_grade(self, engine):
        """AC-5: Test grade calculation."""
        assert engine.calculate_grade(95) == TeamGrade.A
        assert engine.calculate_grade(85) == TeamGrade.B
        assert engine.calculate_grade(75) == TeamGrade.C
        assert engine.calculate_grade(65) == TeamGrade.D
        assert engine.calculate_grade(50) == TeamGrade.F

    def test_grade_all_teams(self, engine):
        """AC-5: Test grading multiple teams."""
        teams = [
            TeamMetrics(
                team_id=f'team-{i}',
                team_name=f'Team {i}',
                velocity=20.0 + i * 10,
                quality_score=60.0 + i * 10,
                artifact_count=30 + i * 20,
                commit_frequency=3.0 + i,
                code_review_turnaround=4.0,
                test_coverage=0.50 + i * 0.1
            )
            for i in range(1, 4)
        ]

        results = engine.grade_all_teams(teams)

        assert len(results) == 3
        # Results should be sorted by score descending
        assert results[0][1] >= results[1][1] >= results[2][1]

    def test_create_rankings(self, engine):
        """AC-5: Test ranking creation."""
        teams = [
            TeamMetrics(
                team_id='team-1',
                team_name='Alpha',
                velocity=40.0,
                quality_score=90.0,
                artifact_count=80,
                commit_frequency=8.0,
                code_review_turnaround=2.0,
                test_coverage=0.85
            ),
            TeamMetrics(
                team_id='team-2',
                team_name='Beta',
                velocity=30.0,
                quality_score=75.0,
                artifact_count=50,
                commit_frequency=5.0,
                code_review_turnaround=4.0,
                test_coverage=0.70
            )
        ]

        rankings = engine.create_rankings(teams)

        assert len(rankings) == 2
        assert rankings[0].rank == 1
        assert rankings[1].rank == 2
        assert rankings[0].score > rankings[1].score

    def test_create_rankings_with_previous(self, engine):
        """AC-5: Test ranking with previous positions."""
        teams = [
            TeamMetrics(
                team_id='team-1',
                team_name='Alpha',
                velocity=40.0,
                quality_score=90.0,
                artifact_count=80,
                commit_frequency=8.0,
                code_review_turnaround=2.0,
                test_coverage=0.85
            )
        ]

        previous = {'team-1': 3}
        rankings = engine.create_rankings(teams, previous)

        assert rankings[0].previous_rank == 3
        assert rankings[0].rank_change == 2  # Improved from 3 to 1

    def test_get_grade_distribution(self, engine):
        """Test grade distribution calculation."""
        teams = [
            TeamMetrics(
                team_id='team-1',
                team_name='Team 1',
                velocity=50.0,
                quality_score=100.0,
                artifact_count=100,
                commit_frequency=10.0,
                code_review_turnaround=1.0,
                test_coverage=1.0
            ),
            TeamMetrics(
                team_id='team-2',
                team_name='Team 2',
                velocity=0.0,
                quality_score=0.0,
                artifact_count=0,
                commit_frequency=0.0,
                code_review_turnaround=10.0,
                test_coverage=0.0
            )
        ]

        for team in teams:
            engine.calculate_score(team)

        distribution = engine.get_grade_distribution(teams)

        assert distribution['A'] == 1
        assert distribution['F'] == 1

    def test_get_percentile(self, engine):
        """Test percentile calculation."""
        all_scores = [50, 60, 70, 80, 90]

        assert engine.get_percentile(90, all_scores) == 80.0  # Better than 80%
        assert engine.get_percentile(50, all_scores) == 0.0  # Better than 0%

    def test_get_improvement_recommendations(self, engine, sample_metrics):
        """Test improvement recommendations."""
        engine.calculate_score(sample_metrics)
        recommendations = engine.get_improvement_recommendations(sample_metrics)

        # Should have recommendations for metrics below 70
        assert isinstance(recommendations, list)
        for rec in recommendations:
            assert 'area' in rec
            assert 'impact' in rec
            assert 'suggestion' in rec


class TestGradingEngineFactory:
    """Tests for get_grading_engine factory function."""

    def test_get_engine_default(self):
        """Test factory with defaults."""
        engine = get_grading_engine()
        assert isinstance(engine, GradingEngine)

    def test_get_engine_custom_weights(self):
        """Test factory with custom weights."""
        engine = get_grading_engine(
            weights={
                'velocity': 0.40,
                'quality_score': 0.20,
                'artifact_count': 0.15,
                'commit_frequency': 0.15,
                'test_coverage': 0.10
            }
        )

        assert engine.weights.velocity == 0.40
        assert engine.weights.quality_score == 0.20
