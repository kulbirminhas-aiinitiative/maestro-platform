"""
Tests for Product Strategy Module - MD-2870

Validates:
- AC-1: Product vision and mission statement defined
- AC-2: High-level product roadmap with quarterly phases
- AC-3: Key milestones documented with target dates
- AC-4: Strategic priorities and objectives identified
- AC-5: Capability maturity progression defined
- AC-6: Dependencies and risks documented
"""

import pytest
from datetime import datetime, timedelta
import sys
sys.path.insert(0, '/home/ec2-user/projects/maestro-platform/maestro-hive/src')

from maestro_hive.enterprise.product_strategy import (
    # Roadmap
    RoadmapManager,
    Roadmap,
    RoadmapPhase,
    Feature,
    PhaseStatus,
    ProgressReport,
    # Milestone
    MilestoneTracker,
    Milestone,
    MilestoneStatus,
    HealthStatus,
    DependencyGraph,
    # Strategy
    StrategyPlanner,
    Strategy,
    Vision,
    Objective,
    Priority,
    StrategicAlignment,
    # Capability
    CapabilityMatrix,
    Capability,
    MaturityLevel,
    ProgressionPlan,
    Assessment,
)
from maestro_hive.enterprise.product_strategy.roadmap_manager import FeatureStatus, FeaturePriority
from maestro_hive.enterprise.product_strategy.milestone_tracker import RiskLevel
from maestro_hive.enterprise.product_strategy.strategy_planner import ObjectiveStatus, AlignmentScore
from maestro_hive.enterprise.product_strategy.capability_matrix import CapabilityCategory


# =============================================================================
# AC-1: Product vision and mission statement defined
# =============================================================================

class TestAC1VisionMission:
    """Tests for AC-1: Product vision and mission statement."""

    def test_create_strategy_with_vision(self):
        """Test creating a strategy with vision statement."""
        planner = StrategyPlanner()
        strategy = planner.create_strategy("Maestro 2025", strategic_themes=["AI-first", "Enterprise-ready"])

        vision = planner.set_vision(
            strategy_id=strategy.strategy_id,
            statement="To be the leading AI-powered development platform",
            description="Enable developers to build faster with AI assistance",
            target_audience="Enterprise development teams",
            value_proposition="10x developer productivity through AI",
            time_horizon="3 years",
            created_by="product_lead",
        )

        assert vision is not None
        assert vision.statement == "To be the leading AI-powered development platform"
        assert vision.target_audience == "Enterprise development teams"
        assert "VIS-" in vision.vision_id

    def test_create_strategy_with_mission(self):
        """Test creating a strategy with mission statement."""
        planner = StrategyPlanner()
        strategy = planner.create_strategy("Maestro Mission")

        mission = planner.set_mission(
            strategy_id=strategy.strategy_id,
            statement="Democratize AI-powered development",
            purpose="Make AI accessible to all developers",
            core_values=["Innovation", "Quality", "User-first"],
            key_stakeholders=["Developers", "Enterprises", "Partners"],
            created_by="ceo",
        )

        assert mission is not None
        assert mission.statement == "Democratize AI-powered development"
        assert len(mission.core_values) == 3
        assert "MIS-" in mission.mission_id

    def test_strategy_with_both_vision_and_mission(self):
        """Test strategy has both vision and mission."""
        planner = StrategyPlanner()
        strategy = planner.create_strategy("Complete Strategy")

        planner.set_vision(
            strategy_id=strategy.strategy_id,
            statement="Vision statement",
            description="Description",
            target_audience="Audience",
            value_proposition="Value",
            time_horizon="5 years",
            created_by="creator",
        )

        planner.set_mission(
            strategy_id=strategy.strategy_id,
            statement="Mission statement",
            purpose="Purpose",
            core_values=["Value1"],
            key_stakeholders=["Stakeholder1"],
            created_by="creator",
        )

        updated_strategy = planner.get_strategy(strategy.strategy_id)
        assert updated_strategy.vision is not None
        assert updated_strategy.mission is not None


# =============================================================================
# AC-2: High-level product roadmap with quarterly phases
# =============================================================================

class TestAC2RoadmapQuarterlyPhases:
    """Tests for AC-2: Roadmap with quarterly phases."""

    def test_create_roadmap(self):
        """Test creating a product roadmap."""
        manager = RoadmapManager()
        roadmap = manager.create_roadmap(
            name="Maestro 2025 Roadmap",
            vision="AI-first development platform",
            description="Annual product roadmap",
            fiscal_year_start=1,
        )

        assert roadmap is not None
        assert roadmap.name == "Maestro 2025 Roadmap"
        assert "RM-" in roadmap.roadmap_id

    def test_add_quarterly_phases(self):
        """Test adding quarterly phases to roadmap."""
        manager = RoadmapManager()
        roadmap = manager.create_roadmap("2025 Roadmap", "Vision")

        q1_id = manager.add_phase(
            roadmap_id=roadmap.roadmap_id,
            name="Q1 Foundation",
            quarter="Q1",
            year=2025,
            objectives=["Core infrastructure", "Auth system"],
        )

        q2_id = manager.add_phase(
            roadmap_id=roadmap.roadmap_id,
            name="Q2 Features",
            quarter="Q2",
            year=2025,
            objectives=["Agent framework", "IDE integration"],
        )

        assert q1_id is not None
        assert q2_id is not None
        assert len(roadmap.phases) == 2
        assert roadmap.phases[0].quarter == "Q1 2025"
        assert roadmap.phases[1].quarter == "Q2 2025"

    def test_add_features_to_phase(self):
        """Test adding features to a phase."""
        manager = RoadmapManager()
        roadmap = manager.create_roadmap("Test Roadmap", "Vision")
        phase_id = manager.add_phase(
            roadmap_id=roadmap.roadmap_id,
            name="Q1",
            quarter="Q1",
            year=2025,
            objectives=["Objective 1"],
        )

        feature_id = manager.add_feature_to_phase(
            roadmap_id=roadmap.roadmap_id,
            phase_id=phase_id,
            name="AI Code Generation",
            description="Generate code from natural language",
            priority=FeaturePriority.HIGH,
            estimated_effort=40,
        )

        assert feature_id is not None
        assert "FT-" in feature_id
        phase = roadmap.phases[0]
        assert len(phase.features) == 1
        assert phase.features[0].name == "AI Code Generation"

    def test_phase_completion_calculation(self):
        """Test phase completion calculation."""
        manager = RoadmapManager()
        roadmap = manager.create_roadmap("Test", "Vision")
        phase_id = manager.add_phase(roadmap.roadmap_id, "Q1", "Q1", 2025, ["Obj"])

        # Add 4 features
        for i in range(4):
            manager.add_feature_to_phase(
                roadmap.roadmap_id, phase_id, f"Feature {i}", "Desc", FeaturePriority.MEDIUM
            )

        # Complete 2 features (50%)
        phase = roadmap.phases[0]
        manager.update_feature_status(
            roadmap.roadmap_id, phase_id, phase.features[0].feature_id, FeatureStatus.COMPLETED
        )
        manager.update_feature_status(
            roadmap.roadmap_id, phase_id, phase.features[1].feature_id, FeatureStatus.COMPLETED
        )

        assert phase.calculate_completion() == 50.0


# =============================================================================
# AC-3: Key milestones documented with target dates
# =============================================================================

class TestAC3Milestones:
    """Tests for AC-3: Milestones with target dates."""

    def test_create_milestone(self):
        """Test creating a milestone with target date."""
        tracker = MilestoneTracker()
        target = datetime.utcnow() + timedelta(days=30)

        milestone = tracker.create_milestone(
            name="MVP Launch",
            description="Launch minimum viable product",
            target_date=target,
            owner="product_manager",
            deliverables=["Feature A", "Feature B"],
        )

        assert milestone is not None
        assert milestone.name == "MVP Launch"
        assert "MS-" in milestone.milestone_id
        assert milestone.target_date == target

    def test_milestone_days_until_due(self):
        """Test calculating days until milestone due."""
        tracker = MilestoneTracker()
        target = datetime.utcnow() + timedelta(days=14)

        milestone = tracker.create_milestone(
            name="Test Milestone",
            description="Test",
            target_date=target,
            owner="owner",
        )

        assert milestone.days_until_due() >= 13  # Account for time during test

    def test_milestone_overdue_detection(self):
        """Test detecting overdue milestones."""
        tracker = MilestoneTracker()
        past_date = datetime.utcnow() - timedelta(days=7)

        milestone = tracker.create_milestone(
            name="Past Milestone",
            description="Overdue",
            target_date=past_date,
            owner="owner",
        )

        assert milestone.is_overdue() is True

    def test_upcoming_milestones(self):
        """Test getting upcoming milestones."""
        tracker = MilestoneTracker()

        # Create milestones at different dates
        tracker.create_milestone("Soon", "Desc", datetime.utcnow() + timedelta(days=10), "owner")
        tracker.create_milestone("Later", "Desc", datetime.utcnow() + timedelta(days=60), "owner")

        upcoming = tracker.get_upcoming_milestones(days=30)
        assert len(upcoming) == 1
        assert upcoming[0].name == "Soon"


# =============================================================================
# AC-4: Strategic priorities and objectives identified
# =============================================================================

class TestAC4StrategicPriorities:
    """Tests for AC-4: Strategic priorities and objectives."""

    def test_add_objective_with_priority(self):
        """Test adding objectives with priority levels."""
        planner = StrategyPlanner()
        strategy = planner.create_strategy("Test Strategy")

        obj_id = planner.add_objective(
            strategy_id=strategy.strategy_id,
            name="Increase Market Share",
            description="Grow market share by 20%",
            priority=Priority.P0_CRITICAL,
            owner="ceo",
            target_quarter="Q4 2025",
        )

        assert obj_id is not None
        assert "OBJ-" in obj_id
        assert len(strategy.objectives) == 1
        assert strategy.objectives[0].priority == Priority.P0_CRITICAL

    def test_add_key_results_to_objective(self):
        """Test adding key results (OKR pattern)."""
        planner = StrategyPlanner()
        strategy = planner.create_strategy("OKR Test")
        obj_id = planner.add_objective(
            strategy.strategy_id, "Revenue Growth", "Increase revenue", Priority.P1_HIGH, "cfo"
        )

        kr_id = planner.add_key_result(
            strategy_id=strategy.strategy_id,
            objective_id=obj_id,
            description="Reach $10M ARR",
            metric="ARR",
            target_value=10000000,
            unit="USD",
        )

        assert kr_id is not None
        assert "KR-" in kr_id

    def test_objective_progress_tracking(self):
        """Test tracking objective progress via key results."""
        planner = StrategyPlanner()
        strategy = planner.create_strategy("Progress Test")
        obj_id = planner.add_objective(
            strategy.strategy_id, "Customer Growth", "Grow customers", Priority.P1_HIGH, "cmo"
        )

        kr_id = planner.add_key_result(
            strategy.strategy_id, obj_id, "Reach 1000 customers", "customers", 1000
        )

        # Update progress to 50%
        planner.update_key_result_progress(strategy.strategy_id, obj_id, kr_id, 500)

        objective = strategy.objectives[0]
        assert objective.calculate_progress() == 50.0

    def test_objectives_by_priority(self):
        """Test filtering objectives by priority."""
        planner = StrategyPlanner()
        strategy = planner.create_strategy("Priority Filter")

        planner.add_objective(strategy.strategy_id, "Critical", "Critical obj", Priority.P0_CRITICAL, "a")
        planner.add_objective(strategy.strategy_id, "High", "High obj", Priority.P1_HIGH, "b")
        planner.add_objective(strategy.strategy_id, "Medium", "Med obj", Priority.P2_MEDIUM, "c")

        critical = strategy.get_objectives_by_priority(Priority.P0_CRITICAL)
        assert len(critical) == 1
        assert critical[0].name == "Critical"


# =============================================================================
# AC-5: Capability maturity progression defined
# =============================================================================

class TestAC5CapabilityMaturity:
    """Tests for AC-5: Capability maturity progression."""

    def test_create_capability_with_maturity_level(self):
        """Test creating capability with maturity levels."""
        matrix = CapabilityMatrix()

        capability = matrix.create_capability(
            name="CI/CD Pipeline",
            description="Continuous integration and deployment",
            category=CapabilityCategory.TOOLS,
            target_level=MaturityLevel.LEVEL_4_MEASURED,
        )

        assert capability is not None
        assert capability.current_level == MaturityLevel.LEVEL_1_INITIAL
        assert capability.target_level == MaturityLevel.LEVEL_4_MEASURED
        assert capability.get_gap() == 3

    def test_maturity_level_descriptions(self):
        """Test maturity level descriptions."""
        assert MaturityLevel.LEVEL_1_INITIAL.name_display == "Initial"
        assert MaturityLevel.LEVEL_3_DEFINED.name_display == "Defined"
        assert MaturityLevel.LEVEL_5_OPTIMIZING.name_display == "Optimizing"

    def test_add_maturity_criteria(self):
        """Test adding maturity criteria."""
        matrix = CapabilityMatrix()
        capability = matrix.create_capability(
            "Test Capability", "Description", CapabilityCategory.PROCESS
        )

        criteria_id = matrix.add_maturity_criteria(
            capability_id=capability.capability_id,
            level=MaturityLevel.LEVEL_2_MANAGED,
            description="Processes are documented",
            evidence_required=["Process documentation", "Training records"],
        )

        assert criteria_id is not None
        assert "CRT-" in criteria_id
        assert len(capability.criteria) == 1

    def test_capability_assessment(self):
        """Test conducting capability assessment."""
        matrix = CapabilityMatrix()
        capability = matrix.create_capability(
            "Testing Maturity", "Test capability", CapabilityCategory.PROCESS
        )

        assessment = matrix.conduct_assessment(
            capability_id=capability.capability_id,
            assessed_level=MaturityLevel.LEVEL_2_MANAGED,
            assessor="assessor@company.com",
            evidence=["Document A", "Metrics B"],
            findings=["Good documentation", "Need more automation"],
            recommendations=["Implement CI/CD"],
        )

        assert assessment is not None
        assert "ASM-" in assessment.assessment_id
        assert capability.current_level == MaturityLevel.LEVEL_2_MANAGED

    def test_progression_plan(self):
        """Test creating progression plan."""
        matrix = CapabilityMatrix()
        capability = matrix.create_capability(
            "DevOps", "DevOps capability", CapabilityCategory.TECHNICAL
        )

        plan = matrix.create_progression_plan(
            capability_id=capability.capability_id,
            name="DevOps Maturity Improvement",
            target_level=MaturityLevel.LEVEL_4_MEASURED,
        )

        step_id = matrix.add_progression_step(
            plan_id=plan.plan_id,
            from_level=MaturityLevel.LEVEL_1_INITIAL,
            to_level=MaturityLevel.LEVEL_2_MANAGED,
            actions=["Document processes", "Create runbooks"],
            resources_needed=["Technical writer"],
            estimated_duration="2 weeks",
        )

        assert plan is not None
        assert step_id is not None
        assert len(plan.steps) == 1


# =============================================================================
# AC-6: Dependencies and risks documented
# =============================================================================

class TestAC6DependenciesRisks:
    """Tests for AC-6: Dependencies and risks documented."""

    def test_add_milestone_dependency(self):
        """Test adding dependencies between milestones."""
        tracker = MilestoneTracker()

        ms1 = tracker.create_milestone("Foundation", "Core work", datetime.utcnow() + timedelta(days=30), "owner")
        ms2 = tracker.create_milestone("Build", "Build on foundation", datetime.utcnow() + timedelta(days=60), "owner")

        dep_id = tracker.add_dependency(
            milestone_id=ms2.milestone_id,
            depends_on_id=ms1.milestone_id,
            dependency_type="blocks",
            description="Build requires Foundation complete",
        )

        assert dep_id is not None
        assert "DEP-" in dep_id
        assert ms1.milestone_id in ms2.dependencies

    def test_dependency_cycle_prevention(self):
        """Test that circular dependencies are prevented."""
        tracker = MilestoneTracker()

        ms1 = tracker.create_milestone("A", "Desc", datetime.utcnow() + timedelta(days=30), "owner")
        ms2 = tracker.create_milestone("B", "Desc", datetime.utcnow() + timedelta(days=60), "owner")

        # A depends on B
        tracker.add_dependency(ms1.milestone_id, ms2.milestone_id)

        # B depends on A should fail (would create cycle)
        result = tracker.add_dependency(ms2.milestone_id, ms1.milestone_id)
        assert result is None

    def test_add_risk_to_milestone(self):
        """Test adding risks to milestones."""
        tracker = MilestoneTracker()
        milestone = tracker.create_milestone(
            "Risky Milestone", "Has risks", datetime.utcnow() + timedelta(days=30), "owner"
        )

        risk_id = tracker.add_risk(
            milestone_id=milestone.milestone_id,
            description="Resource availability uncertain",
            level=RiskLevel.HIGH,
            mitigation="Hire contractors as backup",
            owner="project_manager",
        )

        assert risk_id is not None
        assert "RSK-" in risk_id
        assert len(milestone.risks) == 1
        assert milestone.risks[0].level == RiskLevel.HIGH

    def test_blocked_milestones_detection(self):
        """Test detecting blocked milestones."""
        tracker = MilestoneTracker()

        ms1 = tracker.create_milestone("Blocker", "Desc", datetime.utcnow() + timedelta(days=30), "owner")
        ms2 = tracker.create_milestone("Blocked", "Desc", datetime.utcnow() + timedelta(days=60), "owner")

        tracker.add_dependency(ms2.milestone_id, ms1.milestone_id)

        blocked = tracker.get_blocked_milestones()
        assert len(blocked) == 1
        assert blocked[0].milestone_id == ms2.milestone_id

    def test_dependency_graph_topological_sort(self):
        """Test dependency graph topological ordering."""
        graph = DependencyGraph()

        # A -> B -> C (C depends on B, B depends on A)
        graph.add_dependency("C", "B")
        graph.add_dependency("B", "A")

        order = graph.topological_sort()
        assert order.index("A") < order.index("B")
        assert order.index("B") < order.index("C")


# =============================================================================
# Integration Tests
# =============================================================================

class TestIntegration:
    """Integration tests for the complete module."""

    def test_roadmap_progress_report(self):
        """Test generating roadmap progress report."""
        manager = RoadmapManager()
        roadmap = manager.create_roadmap("Integration Test", "Vision")
        phase_id = manager.add_phase(roadmap.roadmap_id, "Q1", "Q1", 2025, ["Obj"])

        for i in range(3):
            manager.add_feature_to_phase(
                roadmap.roadmap_id, phase_id, f"Feature {i}", "Desc", FeaturePriority.HIGH
            )

        report = manager.get_roadmap_progress(roadmap.roadmap_id)

        assert report is not None
        assert isinstance(report, ProgressReport)
        assert len(report.phases_summary) == 1

    def test_milestone_health_summary(self):
        """Test milestone health summary."""
        tracker = MilestoneTracker()

        # Healthy milestone (far out)
        tracker.create_milestone("Healthy", "Desc", datetime.utcnow() + timedelta(days=60), "owner")

        # At-risk milestone (close, low progress)
        ms = tracker.create_milestone("At Risk", "Desc", datetime.utcnow() + timedelta(days=5), "owner")
        tracker.update_milestone(ms.milestone_id, completion_percentage=20)

        summary = tracker.get_health_summary()

        assert summary["total"] == 2
        assert summary["at_risk_count"] >= 1

    def test_strategy_summary(self):
        """Test strategy summary generation."""
        planner = StrategyPlanner()
        strategy = planner.create_strategy("Summary Test", strategic_themes=["Theme1"])

        planner.set_vision(
            strategy.strategy_id, "Vision", "Desc", "Audience", "Value", "3y", "creator"
        )
        planner.add_objective(strategy.strategy_id, "Obj1", "Desc", Priority.P0_CRITICAL, "owner")
        planner.add_objective(strategy.strategy_id, "Obj2", "Desc", Priority.P1_HIGH, "owner")

        summary = planner.get_strategic_summary(strategy.strategy_id)

        assert summary is not None
        assert summary["has_vision"] is True
        assert summary["total_objectives"] == 2

    def test_capability_matrix_summary(self):
        """Test capability matrix summary."""
        matrix = CapabilityMatrix()

        matrix.create_capability("Cap1", "Desc", CapabilityCategory.TECHNICAL, MaturityLevel.LEVEL_3_DEFINED)
        matrix.create_capability("Cap2", "Desc", CapabilityCategory.PROCESS, MaturityLevel.LEVEL_4_MEASURED)

        summary = matrix.get_capability_matrix_summary()

        assert summary["total"] == 2
        assert "Initial" in summary["by_level"]

    def test_full_workflow(self):
        """Test complete workflow across all components."""
        # 1. Create strategy with vision
        planner = StrategyPlanner()
        strategy = planner.create_strategy("2025 Strategy")
        planner.set_vision(
            strategy.strategy_id,
            "Be #1 AI platform",
            "Leading AI development platform",
            "Developers",
            "10x productivity",
            "3 years",
            "CEO",
        )

        # 2. Add strategic objectives
        obj_id = planner.add_objective(
            strategy.strategy_id,
            "Launch AI Features",
            "Ship core AI capabilities",
            Priority.P0_CRITICAL,
            "VP Engineering",
            "Q2 2025",
        )

        # 3. Create roadmap
        rm = RoadmapManager()
        roadmap = rm.create_roadmap("AI Features Roadmap", "AI-first")
        phase_id = rm.add_phase(roadmap.roadmap_id, "Q1 AI Foundation", "Q1", 2025, ["Core AI"])
        feature_id = rm.add_feature_to_phase(
            roadmap.roadmap_id, phase_id, "Code Gen", "AI code generation", FeaturePriority.CRITICAL
        )

        # 4. Create milestones
        mt = MilestoneTracker()
        milestone = mt.create_milestone(
            "AI Alpha Release",
            "First AI feature release",
            datetime.utcnow() + timedelta(days=45),
            "AI Team Lead",
        )

        # 5. Set up capabilities
        cap = CapabilityMatrix()
        capability = cap.create_capability(
            "AI/ML Infrastructure",
            "ML pipeline and inference",
            CapabilityCategory.TECHNICAL,
            MaturityLevel.LEVEL_4_MEASURED,
        )

        # 6. Link objective to feature
        planner.align_feature(strategy.strategy_id, obj_id, feature_id)

        # Verify everything is connected
        assert strategy.objectives[0].aligned_features == [feature_id]
        assert milestone is not None
        assert capability.get_gap() == 3


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
