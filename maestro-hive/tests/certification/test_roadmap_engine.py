"""
Tests for Roadmap Engine module.

This test suite validates:
- AC-2: Compliance Roadmap Engine functionality
- Gap analysis generation
- Roadmap milestone creation
- Effort estimation
- Resource planning
"""

import pytest
from datetime import datetime, timedelta
from typing import Dict, List

from maestro_hive.certification import (
    StandardsRegistry,
    CertificationStandard,
    ControlRequirement,
    ControlCategory,
    Priority,
)
from maestro_hive.certification.roadmap_engine import (
    RoadmapEngine,
    ComplianceRoadmap,
    Milestone,
    GapAnalysisReport,
    ComplianceGap,
    EffortEstimate,
    ResourcePlan,
    ComplianceState,
    MilestoneStatus,
    GapSeverity,
)


class TestMilestoneStatus:
    """Test MilestoneStatus enum."""

    def test_all_statuses_exist(self):
        """Test all expected milestone statuses exist."""
        expected = ["NOT_STARTED", "IN_PROGRESS", "COMPLETED", "BLOCKED", "DEFERRED"]

        for status_name in expected:
            assert hasattr(MilestoneStatus, status_name)

    def test_status_values(self):
        """Test status string values."""
        assert MilestoneStatus.NOT_STARTED.value == "not_started"
        assert MilestoneStatus.IN_PROGRESS.value == "in_progress"
        assert MilestoneStatus.COMPLETED.value == "completed"


class TestGapSeverity:
    """Test GapSeverity enum."""

    def test_all_severities_exist(self):
        """Test all expected gap severities exist."""
        expected = ["CRITICAL", "HIGH", "MEDIUM", "LOW"]

        for severity_name in expected:
            assert hasattr(GapSeverity, severity_name)

    def test_severity_values(self):
        """Test severity string values."""
        assert GapSeverity.CRITICAL.value == "critical"
        assert GapSeverity.HIGH.value == "high"


class TestComplianceState:
    """Test ComplianceState dataclass."""

    def test_create_compliance_state(self):
        """Test creating a compliance state."""
        state = ComplianceState(
            implemented_controls={"ISO_27001": ["A.5.1.1", "A.5.1.2"]},
            evidence_inventory={"A.5.1.1": ["EV-001", "EV-002"]},
            last_assessment_date=datetime.utcnow(),
            overall_score=75.0,
        )

        assert state.overall_score == 75.0
        assert "ISO_27001" in state.implemented_controls

    def test_get_implemented_count(self):
        """Test counting implemented controls."""
        state = ComplianceState(
            implemented_controls={
                "ISO_27001": ["A.5.1.1", "A.5.1.2", "A.6.1.1"],
                "SOC2": ["CC1.1"],
            },
            evidence_inventory={},
        )

        assert state.get_implemented_count("ISO_27001") == 3
        assert state.get_implemented_count("SOC2") == 1
        assert state.get_implemented_count("UNKNOWN") == 0

    def test_is_control_implemented(self):
        """Test checking if control is implemented."""
        state = ComplianceState(
            implemented_controls={"ISO_27001": ["A.5.1.1", "A.5.1.2"]},
            evidence_inventory={},
        )

        assert state.is_control_implemented("ISO_27001", "A.5.1.1") is True
        assert state.is_control_implemented("ISO_27001", "A.9.9.9") is False
        assert state.is_control_implemented("UNKNOWN", "A.5.1.1") is False


class TestComplianceGap:
    """Test ComplianceGap dataclass."""

    def test_create_gap(self):
        """Test creating a compliance gap."""
        control = ControlRequirement(
            control_id="A.9.1.1",
            name="Access Control Policy",
            description="Establish access control policy",
            category=ControlCategory.ACCESS_CONTROL,
            implementation_guidance="Define policies",
            evidence_requirements=["Policy document"],
            priority=Priority.HIGH,
        )

        gap = ComplianceGap(
            control=control,
            standard_id="ISO_27001",
            severity=GapSeverity.HIGH,
            finding="No formal access control policy documented",
            remediation_guidance="Draft and implement access control policy",
            estimated_effort_hours=40,
            dependencies=["A.5.1.1"],
        )

        assert gap.control.control_id == "A.9.1.1"
        assert gap.severity == GapSeverity.HIGH
        assert gap.estimated_effort_hours == 40

    def test_gap_to_dict(self):
        """Test gap serialization."""
        control = ControlRequirement(
            control_id="TEST-001",
            name="Test Control",
            description="Test",
            category=ControlCategory.COMPLIANCE,
            implementation_guidance="Test",
            evidence_requirements=["Test"],
            priority=Priority.MEDIUM,
        )

        gap = ComplianceGap(
            control=control,
            standard_id="TEST",
            severity=GapSeverity.MEDIUM,
            finding="Test finding",
            remediation_guidance="Test guidance",
            estimated_effort_hours=8,
        )

        data = gap.to_dict()

        assert data["control_id"] == "TEST-001"
        assert data["severity"] == "medium"
        assert data["estimated_effort_hours"] == 8


class TestGapAnalysisReport:
    """Test GapAnalysisReport dataclass."""

    def test_create_report(self):
        """Test creating a gap analysis report."""
        control = ControlRequirement(
            control_id="A.9.1.1",
            name="Access Control",
            description="Access control",
            category=ControlCategory.ACCESS_CONTROL,
            implementation_guidance="Implement",
            evidence_requirements=["Evidence"],
            priority=Priority.HIGH,
        )

        gap = ComplianceGap(
            control=control,
            standard_id="ISO_27001",
            severity=GapSeverity.HIGH,
            finding="Gap",
            remediation_guidance="Fix",
            estimated_effort_hours=40,
        )

        report = GapAnalysisReport(
            standard_id="ISO_27001",
            analysis_date=datetime.utcnow(),
            total_controls=100,
            implemented_controls=75,
            gaps=[gap],
            overall_compliance_percentage=75.0,
            critical_gaps_count=0,
            high_gaps_count=1,
        )

        assert report.standard_id == "ISO_27001"
        assert report.overall_compliance_percentage == 75.0
        assert len(report.gaps) == 1

    def test_report_gap_count(self):
        """Test report gap count property."""
        report = GapAnalysisReport(
            standard_id="TEST",
            analysis_date=datetime.utcnow(),
            total_controls=50,
            implemented_controls=40,
            gaps=[],  # Empty gaps for simplicity
            overall_compliance_percentage=80.0,
            critical_gaps_count=2,
            high_gaps_count=5,
        )

        assert report.gap_count == 0  # Based on gaps list length


class TestEffortEstimate:
    """Test EffortEstimate dataclass."""

    def test_create_estimate(self):
        """Test creating an effort estimate."""
        estimate = EffortEstimate(
            total_hours=800,
            by_category={"access_control": 200, "compliance": 600},
            by_priority={"critical": 100, "high": 300, "medium": 400},
            confidence_level=0.85,
        )

        assert estimate.total_hours == 800
        assert estimate.confidence_level == 0.85
        assert "access_control" in estimate.by_category


class TestResourcePlan:
    """Test ResourcePlan dataclass."""

    def test_create_resource_plan(self):
        """Test creating a resource plan."""
        plan = ResourcePlan(
            total_effort_hours=800,
            recommended_team_size=3,
            skill_requirements=["Security Analyst", "Compliance Officer", "IT Admin"],
            tool_requirements=["GRC Platform", "SIEM", "Vulnerability Scanner"],
            budget_estimate_usd=150000,
        )

        assert len(plan.skill_requirements) == 3
        assert plan.budget_estimate_usd == 150000


class TestMilestone:
    """Test Milestone dataclass."""

    def test_create_milestone(self):
        """Test creating a milestone."""
        control = ControlRequirement(
            control_id="A.5.1.1",
            name="Policies",
            description="Policy development",
            category=ControlCategory.INFORMATION_SECURITY,
            implementation_guidance="Create policies",
            evidence_requirements=["Policy documents"],
            priority=Priority.HIGH,
        )

        milestone = Milestone(
            id="MS-001",
            name="Phase 1: Policy Development",
            description="Develop core security policies",
            controls=[control],
            target_date=datetime.utcnow() + timedelta(days=30),
            status=MilestoneStatus.NOT_STARTED,
            dependencies=[],
            deliverables=["Policy documents", "Approval records"],
        )

        assert milestone.id == "MS-001"
        assert len(milestone.controls) == 1
        assert milestone.status == MilestoneStatus.NOT_STARTED

    def test_milestone_with_dependencies(self):
        """Test milestone with dependencies."""
        control = ControlRequirement(
            control_id="A.9.1.1",
            name="Access Control",
            description="Access control",
            category=ControlCategory.ACCESS_CONTROL,
            implementation_guidance="Implement",
            evidence_requirements=["Evidence"],
            priority=Priority.HIGH,
        )

        milestone = Milestone(
            id="MS-002",
            name="Phase 2: Implementation",
            description="Implement security controls",
            controls=[control],
            target_date=datetime.utcnow() + timedelta(days=60),
            status=MilestoneStatus.NOT_STARTED,
            dependencies=["MS-001"],
            deliverables=["Implemented controls"],
        )

        assert "MS-001" in milestone.dependencies


class TestComplianceRoadmap:
    """Test ComplianceRoadmap dataclass."""

    def test_create_roadmap(self):
        """Test creating a compliance roadmap."""
        registry = StandardsRegistry()
        standard = registry.get_standard("ISO_27001")

        control = ControlRequirement(
            control_id="CTRL-001",
            name="Test Control",
            description="Test",
            category=ControlCategory.COMPLIANCE,
            implementation_guidance="Test",
            evidence_requirements=["Test"],
            priority=Priority.MEDIUM,
        )

        current_state = ComplianceState(
            implemented_controls={},
            evidence_inventory={},
        )

        milestone = Milestone(
            id="MS-001",
            name="Phase 1",
            description="Initial phase",
            controls=[control],
            target_date=datetime.utcnow() + timedelta(days=30),
            status=MilestoneStatus.NOT_STARTED,
            dependencies=[],
            deliverables=["Deliverable 1"],
        )

        resource_plan = ResourcePlan(
            total_effort_hours=200,
            recommended_team_size=2,
            skill_requirements=["Security Analyst"],
            tool_requirements=["GRC Platform"],
            budget_estimate_usd=50000,
        )

        gap_report = GapAnalysisReport(
            standard_id="ISO_27001",
            analysis_date=datetime.utcnow(),
            total_controls=100,
            implemented_controls=0,
            gaps=[],
            overall_compliance_percentage=0.0,
            critical_gaps_count=0,
            high_gaps_count=0,
        )

        roadmap = ComplianceRoadmap(
            id="RM-001",
            target_standard=standard,
            current_state=current_state,
            milestones=[milestone],
            estimated_completion=datetime.utcnow() + timedelta(days=180),
            resource_requirements=resource_plan,
            gap_analysis=gap_report,
        )

        assert roadmap.id == "RM-001"
        assert len(roadmap.milestones) == 1


class TestRoadmapEngine:
    """Test RoadmapEngine class."""

    @pytest.fixture
    def engine(self):
        """Create a roadmap engine for each test."""
        registry = StandardsRegistry()
        return RoadmapEngine(registry)

    @pytest.fixture
    def sample_current_state(self) -> ComplianceState:
        """Sample current compliance state."""
        return ComplianceState(
            implemented_controls={
                "ISO_27001": ["A.5.1.1", "A.5.1.2"],
            },
            evidence_inventory={
                "A.5.1.1": ["EV-001"],
                "A.5.1.2": ["EV-002"],
            },
            last_assessment_date=datetime.utcnow(),
            overall_score=50.0,
        )

    def test_engine_initialization(self, engine):
        """Test engine initializes correctly."""
        assert engine is not None
        assert engine._registry is not None

    def test_analyze_gaps(self, engine, sample_current_state):
        """Test gap analysis generation."""
        report = engine.analyze_gaps("ISO_27001", sample_current_state)

        assert isinstance(report, GapAnalysisReport)
        assert report.standard_id == "ISO_27001"
        assert report.total_controls >= 0
        assert 0 <= report.overall_compliance_percentage <= 100

    def test_analyze_gaps_empty_state(self, engine):
        """Test gap analysis with empty current state."""
        empty_state = ComplianceState(
            implemented_controls={},
            evidence_inventory={},
        )

        report = engine.analyze_gaps("ISO_27001", empty_state)

        assert isinstance(report, GapAnalysisReport)
        # All controls should be gaps
        assert report.implemented_controls == 0 or report.total_controls == 0

    def test_generate_roadmap(self, engine, sample_current_state):
        """Test roadmap generation."""
        roadmap = engine.generate_roadmap(
            target_standard="ISO_27001",
            current_state=sample_current_state,
            timeline_months=12,
        )

        assert isinstance(roadmap, ComplianceRoadmap)
        assert roadmap.target_standard.id == "ISO_27001"

    def test_generate_roadmap_with_priority(self, engine, sample_current_state):
        """Test roadmap generation with priority order."""
        roadmap = engine.generate_roadmap(
            target_standard="ISO_27001",
            current_state=sample_current_state,
            timeline_months=12,
            priority_order=["CRITICAL", "HIGH", "MEDIUM", "LOW"],
        )

        assert isinstance(roadmap, ComplianceRoadmap)

    def test_estimate_effort(self, engine, sample_current_state):
        """Test effort estimation."""
        # First generate a roadmap
        roadmap = engine.generate_roadmap(
            target_standard="ISO_27001",
            current_state=sample_current_state,
            timeline_months=12,
        )

        # Then estimate effort from roadmap
        estimate = engine.estimate_effort(roadmap)

        assert isinstance(estimate, EffortEstimate)
        assert estimate.total_hours >= 0
        assert estimate.confidence_level >= 0
        assert estimate.confidence_level <= 1

    def test_estimate_effort_empty_state(self, engine):
        """Test effort estimation with empty state."""
        empty_state = ComplianceState(
            implemented_controls={},
            evidence_inventory={},
        )

        roadmap = engine.generate_roadmap(
            target_standard="ISO_27001",
            current_state=empty_state,
            timeline_months=12,
        )

        estimate = engine.estimate_effort(roadmap)

        assert isinstance(estimate, EffortEstimate)

    def test_roadmap_for_multiple_standards(self, engine):
        """Test generating roadmaps for multiple standards."""
        empty_state = ComplianceState(
            implemented_controls={},
            evidence_inventory={},
        )

        standards = ["ISO_27001", "SOC2_TYPE2", "GDPR"]

        for std_id in standards:
            roadmap = engine.generate_roadmap(
                target_standard=std_id,
                current_state=empty_state,
                timeline_months=12,
            )

            assert isinstance(roadmap, ComplianceRoadmap)
            assert roadmap.target_standard.id == std_id


class TestRoadmapEngineIntegration:
    """Integration tests for Roadmap Engine."""

    def test_full_gap_to_roadmap_flow(self):
        """Test complete flow from gap analysis to roadmap."""
        registry = StandardsRegistry()
        engine = RoadmapEngine(registry)

        # Initial state - mostly non-compliant
        current_state = ComplianceState(
            implemented_controls={"ISO_27001": []},
            evidence_inventory={},
        )

        # Analyze gaps
        gap_report = engine.analyze_gaps("ISO_27001", current_state)

        # Generate roadmap based on gaps
        roadmap = engine.generate_roadmap(
            target_standard="ISO_27001",
            current_state=current_state,
            timeline_months=12,
        )

        # Estimate effort from roadmap
        effort = engine.estimate_effort(roadmap)

        # Validate consistency
        assert gap_report.standard_id == roadmap.target_standard.id
        assert effort.total_hours >= 0
        assert isinstance(roadmap.resource_requirements, ResourcePlan)

    def test_incremental_compliance_improvement(self):
        """Test tracking compliance improvement over time."""
        registry = StandardsRegistry()
        engine = RoadmapEngine(registry)

        # Initial state - no controls
        state_t0 = ComplianceState(
            implemented_controls={"ISO_27001": []},
            evidence_inventory={},
        )
        report_t0 = engine.analyze_gaps("ISO_27001", state_t0)

        # After some work - some controls implemented
        state_t1 = ComplianceState(
            implemented_controls={"ISO_27001": ["A.5.1.1", "A.5.1.2"]},
            evidence_inventory={"A.5.1.1": ["EV-001"]},
        )
        report_t1 = engine.analyze_gaps("ISO_27001", state_t1)

        # Compliance should improve
        assert report_t1.implemented_controls >= report_t0.implemented_controls


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_unknown_standard(self):
        """Test handling unknown standard ID."""
        registry = StandardsRegistry()
        engine = RoadmapEngine(registry)

        empty_state = ComplianceState(
            implemented_controls={},
            evidence_inventory={},
        )

        # Should handle gracefully
        try:
            report = engine.analyze_gaps("UNKNOWN_STANDARD", empty_state)
            # If it returns a report, it should indicate error or empty
            assert isinstance(report, GapAnalysisReport)
        except (ValueError, KeyError):
            # Expected behavior - reject unknown standard
            pass

    def test_short_timeline(self):
        """Test roadmap with short timeline."""
        registry = StandardsRegistry()
        engine = RoadmapEngine(registry)

        empty_state = ComplianceState(
            implemented_controls={},
            evidence_inventory={},
        )

        roadmap = engine.generate_roadmap(
            target_standard="ISO_27001",
            current_state=empty_state,
            timeline_months=1,  # Very short timeline
        )

        # Should still generate roadmap
        assert isinstance(roadmap, ComplianceRoadmap)

    def test_long_timeline(self):
        """Test roadmap with long timeline."""
        registry = StandardsRegistry()
        engine = RoadmapEngine(registry)

        empty_state = ComplianceState(
            implemented_controls={},
            evidence_inventory={},
        )

        roadmap = engine.generate_roadmap(
            target_standard="ISO_27001",
            current_state=empty_state,
            timeline_months=36,  # 3 years
        )

        assert isinstance(roadmap, ComplianceRoadmap)
