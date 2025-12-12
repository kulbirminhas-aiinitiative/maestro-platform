#!/usr/bin/env python3
"""
E2E Tests for EvaluatorPersona - REAL MODULE IMPORTS
EPIC: MD-3075 - Remediation for MD-3036
Story: MD-3077 - Create real test files for untested modules

CRITICAL: This file imports from the REAL maestro_hive.teams.evaluator_persona
module, NOT mock implementations.
"""
import pytest
import sys
import os
from datetime import datetime

# Add maestro-hive to path for real imports
sys.path.insert(0, '/home/ec2-user/projects/maestro-platform/maestro-hive/src')

# REAL IMPORTS - NOT MOCKS
from maestro_hive.teams.evaluator_persona import (
    EvaluatorPersona,
    EvaluationLevel,
    EvaluationCriteria,
    CriterionScore,
    FeedbackItem,
    FeedbackReport,
    TeamScore,
    EvaluatorConfig,
    DEFAULT_WEIGHTS,
    create_evaluator_persona,
)
from maestro_hive.teams.retrospective_engine import (
    MetricCategory,
    MetricValue,
    TeamMetrics,
    Timeframe,
)


class TestEvaluatorPersonaRealModule:
    """
    E2E tests for EvaluatorPersona using REAL module imports.

    AC-1: Test file imports from maestro_hive.teams
    """

    def test_evaluator_persona_import_is_real(self):
        """Verify we're testing the real EvaluatorPersona, not a mock."""
        assert 'maestro_hive.teams.evaluator_persona' in sys.modules
        assert hasattr(EvaluatorPersona, 'evaluate_performance')
        assert hasattr(EvaluatorPersona, 'generate_feedback')
        assert hasattr(EvaluatorPersona, 'score_team')

    def test_evaluation_level_enum_values(self):
        """Test EvaluationLevel enum has expected values."""
        assert EvaluationLevel.EXCEPTIONAL.value == "exceptional"
        assert EvaluationLevel.STRONG.value == "strong"
        assert EvaluationLevel.MEETING_EXPECTATIONS.value == "meeting_expectations"
        assert EvaluationLevel.NEEDS_IMPROVEMENT.value == "needs_improvement"
        assert EvaluationLevel.CRITICAL.value == "critical"

    def test_evaluation_criteria_enum_values(self):
        """Test EvaluationCriteria enum has expected values."""
        assert EvaluationCriteria.VELOCITY_CONSISTENCY.value == "velocity_consistency"
        assert EvaluationCriteria.QUALITY_METRICS.value == "quality_metrics"
        assert EvaluationCriteria.COLLABORATION_SCORE.value == "collaboration_score"
        assert EvaluationCriteria.DELIVERY_RELIABILITY.value == "delivery_reliability"

    def test_default_weights_sum_to_one(self):
        """Test that default weights sum to 1.0."""
        total = sum(DEFAULT_WEIGHTS.values())
        assert total == pytest.approx(1.0)

    def test_criterion_score_creation(self):
        """Test CriterionScore dataclass creation."""
        score = CriterionScore(
            criterion=EvaluationCriteria.VELOCITY_CONSISTENCY,
            score=0.85,
            weight=0.25,
            weighted_score=0.2125,
            analysis="Good velocity",
        )

        assert score.criterion == EvaluationCriteria.VELOCITY_CONSISTENCY
        assert score.score == 0.85
        assert score.weight == 0.25
        assert score.weighted_score == 0.2125
        assert score.analysis == "Good velocity"
        assert score.data_points == []

    def test_feedback_item_creation(self):
        """Test FeedbackItem dataclass creation."""
        item = FeedbackItem(
            category="performance",
            feedback_type="strength",
            message="Excellent velocity consistency",
            priority=1,
            actionable=True,
        )

        assert item.category == "performance"
        assert item.feedback_type == "strength"
        assert item.message == "Excellent velocity consistency"
        assert item.priority == 1
        assert item.actionable is True

    def test_feedback_item_defaults(self):
        """Test FeedbackItem default values."""
        item = FeedbackItem(
            category="quality",
            feedback_type="improvement",
            message="Needs attention",
        )

        assert item.priority == 0
        assert item.actionable is True

    def test_feedback_report_creation(self):
        """Test FeedbackReport dataclass creation."""
        report = FeedbackReport(
            team_id="team-001",
            overall_feedback="Good performance",
        )

        assert report.team_id == "team-001"
        assert report.overall_feedback == "Good performance"
        assert report.strengths == []
        assert report.improvements == []
        assert report.recommendations == []
        assert isinstance(report.generated_at, datetime)

    def test_feedback_report_to_dict(self):
        """Test FeedbackReport.to_dict method."""
        strength = FeedbackItem(
            category="velocity",
            feedback_type="strength",
            message="Consistent delivery",
        )
        improvement = FeedbackItem(
            category="quality",
            feedback_type="improvement",
            message="Improve test coverage",
            priority=1,
        )

        report = FeedbackReport(
            team_id="team-002",
            overall_feedback="Summary here",
            strengths=[strength],
            improvements=[improvement],
            recommendations=["Focus on testing"],
        )

        result = report.to_dict()

        assert result["team_id"] == "team-002"
        assert result["overall_feedback"] == "Summary here"
        assert len(result["strengths"]) == 1
        assert len(result["improvements"]) == 1
        assert result["recommendations"] == ["Focus on testing"]

    def test_team_score_creation(self):
        """Test TeamScore dataclass creation."""
        score = TeamScore(
            team_id="team-003",
            overall=0.78,
            level=EvaluationLevel.STRONG,
        )

        assert score.team_id == "team-003"
        assert score.overall == 0.78
        assert score.level == EvaluationLevel.STRONG
        assert score.criterion_scores == []
        assert score.trend is None
        assert isinstance(score.evaluated_at, datetime)

    def test_team_score_to_dict(self):
        """Test TeamScore.to_dict method."""
        criterion_score = CriterionScore(
            criterion=EvaluationCriteria.QUALITY_METRICS,
            score=0.8,
            weight=0.3,
            weighted_score=0.24,
        )

        team_score = TeamScore(
            team_id="team-004",
            overall=0.82,
            level=EvaluationLevel.STRONG,
            criterion_scores=[criterion_score],
            trend=0.05,
        )

        result = team_score.to_dict()

        assert result["team_id"] == "team-004"
        assert result["overall"] == 0.82
        assert result["level"] == "strong"
        assert result["trend"] == 0.05
        assert len(result["criterion_scores"]) == 1

    def test_evaluator_config_defaults(self):
        """Test EvaluatorConfig default values."""
        config = EvaluatorConfig()

        assert config.persona_id == "team_evaluator"
        assert config.model_id == "claude-3-sonnet-20240229"
        assert config.temperature == 0.3
        assert config.max_tokens == 4096
        assert config.min_data_points == 3
        assert len(config.weights) == 4

    def test_evaluator_config_custom_values(self):
        """Test EvaluatorConfig with custom values."""
        custom_weights = {
            EvaluationCriteria.VELOCITY_CONSISTENCY: 0.5,
            EvaluationCriteria.QUALITY_METRICS: 0.5,
        }

        config = EvaluatorConfig(
            persona_id="custom_evaluator",
            temperature=0.5,
            weights=custom_weights,
        )

        assert config.persona_id == "custom_evaluator"
        assert config.temperature == 0.5
        assert config.weights == custom_weights


class TestEvaluatorPersonaOperations:
    """Test actual EvaluatorPersona operations with real module."""

    def test_evaluator_persona_instantiation(self):
        """Test EvaluatorPersona can be instantiated."""
        evaluator = EvaluatorPersona()

        assert evaluator.persona_id == "team_evaluator"
        assert evaluator.criteria == list(EvaluationCriteria)
        assert evaluator.config is not None

    def test_evaluator_persona_custom_config(self):
        """Test EvaluatorPersona with custom configuration."""
        config = EvaluatorConfig(
            persona_id="custom",
            temperature=0.7,
        )

        evaluator = EvaluatorPersona(
            persona_id="custom_evaluator",
            config=config,
        )

        assert evaluator.persona_id == "custom_evaluator"
        assert evaluator.config.temperature == 0.7

    def test_evaluator_persona_with_subset_criteria(self):
        """Test EvaluatorPersona with subset of criteria."""
        criteria = [
            EvaluationCriteria.VELOCITY_CONSISTENCY,
            EvaluationCriteria.QUALITY_METRICS,
        ]

        evaluator = EvaluatorPersona(criteria=criteria)

        assert len(evaluator.criteria) == 2

    def test_create_evaluator_persona_factory(self):
        """Test create_evaluator_persona factory function."""
        evaluator = create_evaluator_persona()

        assert isinstance(evaluator, EvaluatorPersona)
        assert evaluator.persona_id == "team_evaluator"

    def test_create_evaluator_persona_with_config(self):
        """Test create_evaluator_persona with custom config."""
        config = EvaluatorConfig(persona_id="factory_test")

        evaluator = create_evaluator_persona(
            persona_id="factory_evaluator",
            config=config,
        )

        assert evaluator.persona_id == "factory_evaluator"

    def test_evaluate_performance_with_metrics(self):
        """Test evaluate_performance with real metrics."""
        evaluator = EvaluatorPersona()
        timeframe = Timeframe.last_sprint()

        metrics = TeamMetrics(
            team_id="test-team",
            timeframe=timeframe,
            metrics=[
                MetricValue(name="velocity", value=40, category=MetricCategory.VELOCITY, trend=5.0),
                MetricValue(name="bugs", value=0.1, category=MetricCategory.QUALITY),
                MetricValue(name="review_time", value=4, category=MetricCategory.COLLABORATION),
                MetricValue(name="completion", value=0.9, category=MetricCategory.DELIVERY),
            ],
        )

        assessment = evaluator.evaluate_performance(metrics)

        assert assessment.team_id == "test-team"
        assert 0.0 <= assessment.overall_score <= 1.0
        assert isinstance(assessment.summary, str)

    def test_determine_level_exceptional(self):
        """Test _determine_level for exceptional score."""
        evaluator = EvaluatorPersona()
        level = evaluator._determine_level(0.95)

        assert level == EvaluationLevel.EXCEPTIONAL

    def test_determine_level_strong(self):
        """Test _determine_level for strong score."""
        evaluator = EvaluatorPersona()
        level = evaluator._determine_level(0.80)

        assert level == EvaluationLevel.STRONG

    def test_determine_level_meeting_expectations(self):
        """Test _determine_level for meeting expectations score."""
        evaluator = EvaluatorPersona()
        level = evaluator._determine_level(0.65)

        assert level == EvaluationLevel.MEETING_EXPECTATIONS

    def test_determine_level_needs_improvement(self):
        """Test _determine_level for needs improvement score."""
        evaluator = EvaluatorPersona()
        level = evaluator._determine_level(0.50)

        assert level == EvaluationLevel.NEEDS_IMPROVEMENT

    def test_determine_level_critical(self):
        """Test _determine_level for critical score."""
        evaluator = EvaluatorPersona()
        level = evaluator._determine_level(0.30)

        assert level == EvaluationLevel.CRITICAL

    def test_get_evaluation_history(self):
        """Test get_evaluation_history method."""
        evaluator = EvaluatorPersona()

        # Initially empty
        history = evaluator.get_evaluation_history("test-team")
        assert history == []


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
