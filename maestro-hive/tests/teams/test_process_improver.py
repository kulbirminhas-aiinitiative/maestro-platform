#!/usr/bin/env python3
"""
E2E Tests for ProcessImprover - REAL MODULE IMPORTS
EPIC: MD-3075 - Remediation for MD-3036
Story: MD-3077 - Create real test files for untested modules

CRITICAL: This file imports from the REAL maestro_hive.teams.process_improver
module, NOT mock implementations.
"""
import pytest
import sys
import os
from datetime import datetime

# Add maestro-hive to path for real imports
sys.path.insert(0, '/home/ec2-user/projects/maestro-platform/maestro-hive/src')

# REAL IMPORTS - NOT MOCKS
from maestro_hive.teams.process_improver import (
    ProcessImprover,
    ImprovementCategory,
    ImpactLevel,
    EffortLevel,
    PriorityQuadrant,
    Bottleneck,
    WorkflowData,
    WorkflowAnalysis,
    PrioritizedAction,
    ImproverConfig,
    create_process_improver,
)
from maestro_hive.teams.retrospective_engine import (
    MetricCategory,
    MetricValue,
    TeamMetrics,
    Timeframe,
)


class TestProcessImproverRealModule:
    """
    E2E tests for ProcessImprover using REAL module imports.

    AC-1: Test file imports from maestro_hive.teams
    """

    def test_process_improver_import_is_real(self):
        """Verify we're testing the real ProcessImprover, not a mock."""
        assert 'maestro_hive.teams.process_improver' in sys.modules
        assert hasattr(ProcessImprover, 'analyze_workflow')
        assert hasattr(ProcessImprover, 'detect_bottlenecks')
        assert hasattr(ProcessImprover, 'suggest_improvements')
        assert hasattr(ProcessImprover, 'prioritize_actions')

    def test_improvement_category_enum_values(self):
        """Test ImprovementCategory enum has expected values."""
        assert ImprovementCategory.PROCESS_EFFICIENCY.value == "process_efficiency"
        assert ImprovementCategory.CODE_QUALITY.value == "code_quality"
        assert ImprovementCategory.TEAM_COMMUNICATION.value == "team_communication"
        assert ImprovementCategory.TECHNICAL_DEBT.value == "technical_debt"
        assert ImprovementCategory.TESTING_PRACTICES.value == "testing_practices"
        assert ImprovementCategory.DOCUMENTATION.value == "documentation"

    def test_impact_level_enum_values(self):
        """Test ImpactLevel enum has expected values."""
        assert ImpactLevel.HIGH.value == "high"
        assert ImpactLevel.MEDIUM.value == "medium"
        assert ImpactLevel.LOW.value == "low"

    def test_effort_level_enum_values(self):
        """Test EffortLevel enum has expected values."""
        assert EffortLevel.HIGH.value == "high"
        assert EffortLevel.MEDIUM.value == "medium"
        assert EffortLevel.LOW.value == "low"

    def test_priority_quadrant_enum_values(self):
        """Test PriorityQuadrant enum has expected values."""
        assert PriorityQuadrant.QUICK_WINS.value == "quick_wins"
        assert PriorityQuadrant.STRATEGIC.value == "strategic"
        assert PriorityQuadrant.FILL_INS.value == "fill_ins"
        assert PriorityQuadrant.AVOID.value == "avoid"

    def test_bottleneck_creation(self):
        """Test Bottleneck dataclass creation."""
        bottleneck = Bottleneck(
            name="Code Review Delay",
            description="Reviews taking too long",
            severity=0.75,
            location="Code Review",
        )

        assert bottleneck.name == "Code Review Delay"
        assert bottleneck.description == "Reviews taking too long"
        assert bottleneck.severity == 0.75
        assert bottleneck.location == "Code Review"
        assert bottleneck.id is not None
        assert isinstance(bottleneck.detected_at, datetime)
        assert bottleneck.metrics_evidence == []

    def test_bottleneck_to_dict(self):
        """Test Bottleneck.to_dict method."""
        bottleneck = Bottleneck(
            name="Test Bottleneck",
            description="Description",
            severity=0.5,
            location="Testing",
            metrics_evidence=["metric_1", "metric_2"],
        )

        result = bottleneck.to_dict()

        assert result["name"] == "Test Bottleneck"
        assert result["severity"] == 0.5
        assert result["metrics_evidence"] == ["metric_1", "metric_2"]
        assert "id" in result
        assert "detected_at" in result

    def test_workflow_data_creation(self):
        """Test WorkflowData dataclass creation."""
        data = WorkflowData(
            team_id="team-001",
            stages=["planning", "development", "review", "testing"],
            avg_cycle_time=72.0,
            stage_times={"planning": 4.0, "development": 40.0},
            handoff_count=3,
            rework_rate=0.15,
        )

        assert data.team_id == "team-001"
        assert len(data.stages) == 4
        assert data.avg_cycle_time == 72.0
        assert data.handoff_count == 3
        assert data.rework_rate == 0.15

    def test_workflow_data_defaults(self):
        """Test WorkflowData default values."""
        data = WorkflowData(team_id="team-002")

        assert data.stages == []
        assert data.avg_cycle_time == 0.0
        assert data.stage_times == {}
        assert data.handoff_count == 0
        assert data.rework_rate == 0.0

    def test_workflow_analysis_creation(self):
        """Test WorkflowAnalysis dataclass creation."""
        analysis = WorkflowAnalysis(
            team_id="team-003",
            efficiency_score=0.8,
            cycle_time=48.0,
        )

        assert analysis.team_id == "team-003"
        assert analysis.efficiency_score == 0.8
        assert analysis.cycle_time == 48.0
        assert analysis.bottlenecks == []
        assert analysis.recommendations == []
        assert analysis.focus_areas == []
        assert isinstance(analysis.analyzed_at, datetime)

    def test_workflow_analysis_to_dict(self):
        """Test WorkflowAnalysis.to_dict method."""
        bottleneck = Bottleneck(
            name="Test",
            description="Desc",
            severity=0.5,
            location="Loc",
        )

        analysis = WorkflowAnalysis(
            team_id="team-004",
            bottlenecks=[bottleneck],
            efficiency_score=0.75,
            focus_areas=[ImprovementCategory.CODE_QUALITY],
            recommendations=["Fix issues"],
        )

        result = analysis.to_dict()

        assert result["team_id"] == "team-004"
        assert result["efficiency_score"] == 0.75
        assert len(result["bottlenecks"]) == 1
        assert result["focus_areas"] == ["code_quality"]
        assert result["recommendations"] == ["Fix issues"]

    def test_prioritized_action_creation(self):
        """Test PrioritizedAction dataclass creation."""
        action = PrioritizedAction(
            improvement_id="imp-001",
            title="Improve Reviews",
            description="Speed up code reviews",
            category=ImprovementCategory.TEAM_COMMUNICATION,
            impact_score=0.8,
            impact_level=ImpactLevel.HIGH,
            effort_score=0.3,
            effort_level=EffortLevel.LOW,
            priority_quadrant=PriorityQuadrant.QUICK_WINS,
            priority_rank=1,
            confidence=0.85,
        )

        assert action.improvement_id == "imp-001"
        assert action.title == "Improve Reviews"
        assert action.category == ImprovementCategory.TEAM_COMMUNICATION
        assert action.impact_level == ImpactLevel.HIGH
        assert action.effort_level == EffortLevel.LOW
        assert action.priority_quadrant == PriorityQuadrant.QUICK_WINS
        assert action.priority_rank == 1

    def test_prioritized_action_to_dict(self):
        """Test PrioritizedAction.to_dict method."""
        action = PrioritizedAction(
            improvement_id="imp-002",
            title="Test Action",
            description="Description",
            category=ImprovementCategory.CODE_QUALITY,
            impact_score=0.7,
            impact_level=ImpactLevel.MEDIUM,
            effort_score=0.6,
            effort_level=EffortLevel.MEDIUM,
            priority_quadrant=PriorityQuadrant.STRATEGIC,
            priority_rank=2,
            confidence=0.8,
            expected_benefit="Better code",
            implementation_steps=["Step 1", "Step 2"],
        )

        result = action.to_dict()

        assert result["improvement_id"] == "imp-002"
        assert result["category"] == "code_quality"
        assert result["impact_level"] == "medium"
        assert result["priority_quadrant"] == "strategic"
        assert result["implementation_steps"] == ["Step 1", "Step 2"]

    def test_improver_config_defaults(self):
        """Test ImproverConfig default values."""
        config = ImproverConfig()

        assert config.max_suggestions == 5
        assert config.min_confidence == 0.7
        assert config.max_high_priority == 3
        assert len(config.focus_areas) == 4

    def test_improver_config_custom_values(self):
        """Test ImproverConfig with custom values."""
        config = ImproverConfig(
            max_suggestions=10,
            min_confidence=0.8,
            max_high_priority=5,
            focus_areas=[ImprovementCategory.CODE_QUALITY],
        )

        assert config.max_suggestions == 10
        assert config.min_confidence == 0.8
        assert config.max_high_priority == 5
        assert len(config.focus_areas) == 1


class TestProcessImproverOperations:
    """Test actual ProcessImprover operations with real module."""

    def test_process_improver_instantiation(self):
        """Test ProcessImprover can be instantiated."""
        improver = ProcessImprover()

        assert improver.config is not None
        assert improver.config.max_suggestions == 5

    def test_process_improver_custom_config(self):
        """Test ProcessImprover with custom configuration."""
        config = ImproverConfig(
            max_suggestions=10,
            min_confidence=0.6,
        )

        improver = ProcessImprover(config=config)

        assert improver.config.max_suggestions == 10
        assert improver.config.min_confidence == 0.6

    def test_create_process_improver_factory(self):
        """Test create_process_improver factory function."""
        improver = create_process_improver()

        assert isinstance(improver, ProcessImprover)

    def test_create_process_improver_with_config(self):
        """Test create_process_improver with custom config."""
        config = ImproverConfig(max_suggestions=8)

        improver = create_process_improver(config=config)

        assert improver.config.max_suggestions == 8

    def test_detect_bottlenecks_with_metrics(self):
        """Test detect_bottlenecks with real metrics."""
        improver = ProcessImprover()
        timeframe = Timeframe.last_sprint()

        metrics = TeamMetrics(
            team_id="bottleneck-test",
            timeframe=timeframe,
            metrics=[
                MetricValue(name="review_time", value=12, category=MetricCategory.COLLABORATION),
                MetricValue(name="bug_rate", value=0.3, category=MetricCategory.QUALITY),
                MetricValue(name="completion_rate", value=0.7, category=MetricCategory.DELIVERY),
            ],
        )

        bottlenecks = improver.detect_bottlenecks(metrics)

        assert isinstance(bottlenecks, list)
        # Should detect at least one bottleneck with these metrics
        assert len(bottlenecks) >= 1

    def test_detect_bottlenecks_no_issues(self):
        """Test detect_bottlenecks with good metrics."""
        improver = ProcessImprover()
        timeframe = Timeframe.last_sprint()

        metrics = TeamMetrics(
            team_id="good-team",
            timeframe=timeframe,
            metrics=[
                MetricValue(name="review_time", value=2, category=MetricCategory.COLLABORATION),
                MetricValue(name="bug_rate", value=0.05, category=MetricCategory.QUALITY),
                MetricValue(name="completion_rate", value=0.95, category=MetricCategory.DELIVERY),
            ],
        )

        bottlenecks = improver.detect_bottlenecks(metrics)

        # Good metrics should have few or no bottlenecks
        assert isinstance(bottlenecks, list)

    def test_analyze_workflow(self):
        """Test analyze_workflow method."""
        improver = ProcessImprover()
        timeframe = Timeframe.last_sprint()

        metrics = TeamMetrics(
            team_id="workflow-test",
            timeframe=timeframe,
            metrics=[
                MetricValue(name="review_time", value=10, category=MetricCategory.COLLABORATION),
                MetricValue(name="velocity", value=35, category=MetricCategory.VELOCITY),
            ],
        )

        analysis = improver.analyze_workflow(metrics)

        assert isinstance(analysis, WorkflowAnalysis)
        assert analysis.team_id == "workflow-test"
        assert 0.0 <= analysis.efficiency_score <= 1.0

    def test_determine_quadrant_quick_wins(self):
        """Test _determine_quadrant for quick wins."""
        improver = ProcessImprover()
        quadrant = improver._determine_quadrant(impact=0.8, effort=0.3)

        assert quadrant == PriorityQuadrant.QUICK_WINS

    def test_determine_quadrant_strategic(self):
        """Test _determine_quadrant for strategic."""
        improver = ProcessImprover()
        quadrant = improver._determine_quadrant(impact=0.8, effort=0.7)

        assert quadrant == PriorityQuadrant.STRATEGIC

    def test_determine_quadrant_fill_ins(self):
        """Test _determine_quadrant for fill-ins."""
        improver = ProcessImprover()
        quadrant = improver._determine_quadrant(impact=0.3, effort=0.3)

        assert quadrant == PriorityQuadrant.FILL_INS

    def test_determine_quadrant_avoid(self):
        """Test _determine_quadrant for avoid."""
        improver = ProcessImprover()
        quadrant = improver._determine_quadrant(impact=0.3, effort=0.8)

        assert quadrant == PriorityQuadrant.AVOID

    def test_calculate_efficiency_no_bottlenecks(self):
        """Test _calculate_efficiency with no bottlenecks."""
        improver = ProcessImprover()
        metrics = TeamMetrics(
            team_id="test",
            timeframe=Timeframe.last_sprint(),
            metrics=[],
        )

        efficiency = improver._calculate_efficiency(metrics, [])

        assert efficiency == 1.0

    def test_calculate_efficiency_with_bottlenecks(self):
        """Test _calculate_efficiency with bottlenecks."""
        improver = ProcessImprover()
        metrics = TeamMetrics(
            team_id="test",
            timeframe=Timeframe.last_sprint(),
            metrics=[],
        )

        bottlenecks = [
            Bottleneck(name="B1", description="", severity=0.5, location=""),
            Bottleneck(name="B2", description="", severity=0.8, location=""),
        ]

        efficiency = improver._calculate_efficiency(metrics, bottlenecks)

        # Each bottleneck reduces efficiency by severity * 0.2
        # 1.0 - (0.5 * 0.2) - (0.8 * 0.2) = 1.0 - 0.1 - 0.16 = 0.74
        assert efficiency == pytest.approx(0.74)

    def test_identify_focus_areas(self):
        """Test _identify_focus_areas method."""
        improver = ProcessImprover()
        metrics = TeamMetrics(
            team_id="test",
            timeframe=Timeframe.last_sprint(),
            metrics=[],
        )

        bottlenecks = [
            Bottleneck(name="Code Review Delay", description="", severity=0.8, location=""),
            Bottleneck(name="Quality Issues", description="", severity=0.6, location=""),
        ]

        focus_areas = improver._identify_focus_areas(metrics, bottlenecks)

        assert isinstance(focus_areas, list)
        assert len(focus_areas) <= 2
        assert ImprovementCategory.TEAM_COMMUNICATION in focus_areas
        assert ImprovementCategory.CODE_QUALITY in focus_areas


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
