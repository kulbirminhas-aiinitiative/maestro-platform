"""
Unit Tests for SDLC Integration
Version: 1.0.0

Comprehensive tests for multi-agent workflow orchestration.
"""

import pytest
from datetime import datetime, timedelta

from contracts.sdlc import (
    AgentRole, AgentCapability, Agent, AgentTeam,
    SDLCPhase, WorkflowStepStatus, WorkflowStep, SDLCWorkflow,
    OrchestrationEvent, ContractOrchestrator
)
from contracts.models import UniversalContract, ContractLifecycle, AcceptanceCriterion
from contracts.handoff.models import HandoffSpec, HandoffStatus, HandoffTask


# ============================================================================
# Test AgentRole Enum
# ============================================================================

class TestAgentRole:
    """Tests for AgentRole enum"""

    def test_agent_role_values(self):
        """Test AgentRole enum values"""
        assert AgentRole.BACKEND_DEVELOPER == "backend_developer"
        assert AgentRole.FRONTEND_DEVELOPER == "frontend_developer"
        assert AgentRole.QA_ENGINEER == "qa_engineer"
        assert AgentRole.DEVOPS_ENGINEER == "devops_engineer"

    def test_agent_role_membership(self):
        """Test AgentRole membership checks"""
        roles = [role.value for role in AgentRole]
        assert "backend_developer" in roles
        assert "product_owner" in roles
        assert "invalid_role" not in roles


# ============================================================================
# Test AgentCapability
# ============================================================================

class TestAgentCapability:
    """Tests for AgentCapability"""

    def test_capability_creation(self):
        """Test creating AgentCapability"""
        cap = AgentCapability(
            capability_id="cap-001",
            name="Python Development",
            description="Expert in Python",
            proficiency="expert",
            tags=["python", "backend"]
        )

        assert cap.capability_id == "cap-001"
        assert cap.name == "Python Development"
        assert cap.proficiency == "expert"
        assert len(cap.tags) == 2


# ============================================================================
# Test Agent
# ============================================================================

class TestAgent:
    """Tests for Agent class"""

    def test_agent_creation_minimal(self):
        """Test creating Agent with minimal fields"""
        agent = Agent(
            agent_id="agent-001",
            name="Backend Developer",
            roles=[AgentRole.BACKEND_DEVELOPER]
        )

        assert agent.agent_id == "agent-001"
        assert agent.name == "Backend Developer"
        assert len(agent.roles) == 1
        assert agent.available is True
        assert agent.max_concurrent_tasks == 3

    def test_agent_creation_full(self):
        """Test creating Agent with all fields"""
        capabilities = [
            AgentCapability(
                capability_id="cap-1",
                name="Python",
                description="Python programming",
                proficiency="expert"
            )
        ]

        agent = Agent(
            agent_id="agent-002",
            name="Full Stack Developer",
            roles=[AgentRole.BACKEND_DEVELOPER, AgentRole.FRONTEND_DEVELOPER],
            capabilities=capabilities,
            available=True,
            max_concurrent_tasks=5,
            completed_tasks=10,
            success_rate=0.95
        )

        assert len(agent.roles) == 2
        assert len(agent.capabilities) == 1
        assert agent.completed_tasks == 10
        assert agent.success_rate == 0.95

    def test_agent_can_perform_role(self):
        """Test agent role checking"""
        agent = Agent(
            agent_id="agent-003",
            name="Backend Dev",
            roles=[AgentRole.BACKEND_DEVELOPER, AgentRole.DEVOPS_ENGINEER]
        )

        assert agent.can_perform_role(AgentRole.BACKEND_DEVELOPER) is True
        assert agent.can_perform_role(AgentRole.DEVOPS_ENGINEER) is True
        assert agent.can_perform_role(AgentRole.FRONTEND_DEVELOPER) is False

    def test_agent_has_capability(self):
        """Test agent capability checking"""
        cap1 = AgentCapability("c1", "Python", "Python dev")
        cap2 = AgentCapability("c2", "Docker", "Containerization")

        agent = Agent(
            agent_id="agent-004",
            name="DevOps Engineer",
            roles=[AgentRole.DEVOPS_ENGINEER],
            capabilities=[cap1, cap2]
        )

        assert agent.has_capability("Python") is True
        assert agent.has_capability("Docker") is True
        assert agent.has_capability("Kubernetes") is False

    def test_agent_to_dict(self):
        """Test Agent serialization"""
        agent = Agent(
            agent_id="agent-005",
            name="QA Engineer",
            roles=[AgentRole.QA_ENGINEER],
            completed_tasks=5,
            success_rate=1.0
        )

        data = agent.to_dict()

        assert data["agent_id"] == "agent-005"
        assert data["name"] == "QA Engineer"
        assert data["roles"] == ["qa_engineer"]
        assert data["completed_tasks"] == 5
        assert data["success_rate"] == 1.0


# ============================================================================
# Test AgentTeam
# ============================================================================

class TestAgentTeam:
    """Tests for AgentTeam class"""

    def test_team_creation(self):
        """Test creating AgentTeam"""
        agents = [
            Agent("a1", "Backend Dev", [AgentRole.BACKEND_DEVELOPER]),
            Agent("a2", "Frontend Dev", [AgentRole.FRONTEND_DEVELOPER])
        ]

        team = AgentTeam(
            team_id="team-001",
            name="Development Team",
            agents=agents,
            description="Core development team"
        )

        assert team.team_id == "team-001"
        assert len(team.agents) == 2
        assert team.description == "Core development team"

    def test_get_agents_by_role(self):
        """Test getting agents by role"""
        agents = [
            Agent("a1", "Backend 1", [AgentRole.BACKEND_DEVELOPER]),
            Agent("a2", "Backend 2", [AgentRole.BACKEND_DEVELOPER]),
            Agent("a3", "Frontend", [AgentRole.FRONTEND_DEVELOPER])
        ]

        team = AgentTeam("team-002", "Team", agents)

        backend_devs = team.get_agents_by_role(AgentRole.BACKEND_DEVELOPER)
        assert len(backend_devs) == 2

        frontend_devs = team.get_agents_by_role(AgentRole.FRONTEND_DEVELOPER)
        assert len(frontend_devs) == 1

    def test_get_available_agents(self):
        """Test getting available agents"""
        agents = [
            Agent("a1", "Dev 1", [AgentRole.BACKEND_DEVELOPER], available=True),
            Agent("a2", "Dev 2", [AgentRole.BACKEND_DEVELOPER], available=False),
            Agent("a3", "Dev 3", [AgentRole.FRONTEND_DEVELOPER], available=True)
        ]

        team = AgentTeam("team-003", "Team", agents)

        available = team.get_available_agents()
        assert len(available) == 2
        assert all(a.available for a in available)

    def test_get_agent_by_id(self):
        """Test getting agent by ID"""
        agents = [
            Agent("a1", "Dev 1", [AgentRole.BACKEND_DEVELOPER]),
            Agent("a2", "Dev 2", [AgentRole.FRONTEND_DEVELOPER])
        ]

        team = AgentTeam("team-004", "Team", agents)

        agent = team.get_agent_by_id("a1")
        assert agent is not None
        assert agent.agent_id == "a1"

        missing = team.get_agent_by_id("a999")
        assert missing is None

    def test_assign_role(self):
        """Test assigning role to agent"""
        agent = Agent("a1", "Dev", [AgentRole.BACKEND_DEVELOPER])
        team = AgentTeam("team-005", "Team", [agent])

        # Assign new role
        success = team.assign_role("a1", AgentRole.DEVOPS_ENGINEER)
        assert success is True
        assert AgentRole.DEVOPS_ENGINEER in agent.roles

        # Try to assign existing role (should return False, role already exists)
        success = team.assign_role("a1", AgentRole.BACKEND_DEVELOPER)
        assert success is False  # Returns False when role already exists

    def test_team_has_role(self):
        """Test checking if team has a role"""
        agents = [
            Agent("a1", "Backend", [AgentRole.BACKEND_DEVELOPER]),
            Agent("a2", "Frontend", [AgentRole.FRONTEND_DEVELOPER])
        ]

        team = AgentTeam("team-006", "Team", agents)

        assert team.team_has_role(AgentRole.BACKEND_DEVELOPER) is True
        assert team.team_has_role(AgentRole.FRONTEND_DEVELOPER) is True
        assert team.team_has_role(AgentRole.DEVOPS_ENGINEER) is False

    def test_team_statistics(self):
        """Test team statistics generation"""
        agents = [
            Agent("a1", "Dev 1", [AgentRole.BACKEND_DEVELOPER], completed_tasks=10, success_rate=0.9),
            Agent("a2", "Dev 2", [AgentRole.FRONTEND_DEVELOPER], completed_tasks=5, success_rate=1.0)
        ]

        team = AgentTeam("team-007", "Team", agents)

        stats = team.team_statistics()

        assert stats["total_agents"] == 2
        assert stats["total_completed_tasks"] == 15
        assert stats["average_success_rate"] == 0.95

    def test_team_to_dict(self):
        """Test team serialization"""
        agents = [Agent("a1", "Dev", [AgentRole.BACKEND_DEVELOPER])]
        team = AgentTeam("team-008", "Dev Team", agents, description="Main team")

        data = team.to_dict()

        assert data["team_id"] == "team-008"
        assert data["name"] == "Dev Team"
        assert len(data["agents"]) == 1
        assert "statistics" in data


# ============================================================================
# Test SDLCPhase
# ============================================================================

class TestSDLCPhase:
    """Tests for SDLCPhase enum"""

    def test_sdlc_phase_values(self):
        """Test SDLCPhase enum values"""
        assert SDLCPhase.REQUIREMENTS == "requirements"
        assert SDLCPhase.DESIGN == "design"
        assert SDLCPhase.DEVELOPMENT == "development"
        assert SDLCPhase.TESTING == "testing"
        assert SDLCPhase.DEPLOYMENT == "deployment"


# ============================================================================
# Test WorkflowStep
# ============================================================================

class TestWorkflowStep:
    """Tests for WorkflowStep class"""

    def test_workflow_step_creation_minimal(self):
        """Test creating WorkflowStep with minimal fields"""
        step = WorkflowStep(
            step_id="step-001",
            name="Design UI",
            phase=SDLCPhase.DESIGN
        )

        assert step.step_id == "step-001"
        assert step.name == "Design UI"
        assert step.phase == SDLCPhase.DESIGN
        assert step.status == WorkflowStepStatus.PENDING
        assert step.depends_on == []

    def test_workflow_step_creation_full(self):
        """Test creating WorkflowStep with all fields"""
        step = WorkflowStep(
            step_id="step-002",
            name="Implement API",
            phase=SDLCPhase.DEVELOPMENT,
            description="Implement REST API",
            status=WorkflowStepStatus.IN_PROGRESS,
            assigned_to="agent-001",
            contracts=["contract-1", "contract-2"],
            depends_on=["step-001"],
            estimated_duration_hours=8.0
        )

        assert step.phase == SDLCPhase.DEVELOPMENT
        assert step.status == WorkflowStepStatus.IN_PROGRESS
        assert step.assigned_to == "agent-001"
        assert len(step.contracts) == 2
        assert len(step.depends_on) == 1

    def test_workflow_step_actual_duration(self):
        """Test calculating actual step duration"""
        started = datetime(2024, 1, 1, 10, 0, 0)
        completed = datetime(2024, 1, 1, 14, 30, 0)

        step = WorkflowStep(
            step_id="step-003",
            name="Code Review",
            phase=SDLCPhase.DEVELOPMENT,
            started_at=started,
            completed_at=completed
        )

        duration = step.actual_duration_hours()
        assert duration == 4.5

    def test_workflow_step_status_checks(self):
        """Test step status checking methods"""
        step = WorkflowStep("s1", "Test", SDLCPhase.TESTING)

        # Ready check
        assert step.is_ready() is True
        step.status = WorkflowStepStatus.IN_PROGRESS
        assert step.is_ready() is False

        # Complete check
        assert step.is_complete() is False
        step.status = WorkflowStepStatus.COMPLETED
        assert step.is_complete() is True

        # Failed check
        assert step.is_failed() is False
        step.status = WorkflowStepStatus.FAILED
        assert step.is_failed() is True

    def test_workflow_step_to_dict(self):
        """Test WorkflowStep serialization"""
        step = WorkflowStep(
            step_id="step-004",
            name="Deploy",
            phase=SDLCPhase.DEPLOYMENT,
            status=WorkflowStepStatus.COMPLETED,
            estimated_duration_hours=2.0
        )

        data = step.to_dict()

        assert data["step_id"] == "step-004"
        assert data["phase"] == "deployment"
        assert data["status"] == "COMPLETED"
        assert data["estimated_duration_hours"] == 2.0


# ============================================================================
# Test SDLCWorkflow
# ============================================================================

class TestSDLCWorkflow:
    """Tests for SDLCWorkflow class"""

    def test_workflow_creation(self):
        """Test creating SDLCWorkflow"""
        workflow = SDLCWorkflow(
            workflow_id="wf-001",
            name="E-commerce Development",
            description="Build e-commerce platform",
            project_id="project-001"
        )

        assert workflow.workflow_id == "wf-001"
        assert workflow.name == "E-commerce Development"
        assert workflow.status == "draft"
        assert workflow.steps == []

    def test_get_steps_by_phase(self):
        """Test getting steps by phase"""
        steps = [
            WorkflowStep("s1", "Design", SDLCPhase.DESIGN),
            WorkflowStep("s2", "Develop", SDLCPhase.DEVELOPMENT),
            WorkflowStep("s3", "Test", SDLCPhase.TESTING),
            WorkflowStep("s4", "More Dev", SDLCPhase.DEVELOPMENT)
        ]

        workflow = SDLCWorkflow("wf-002", "Project", "Desc", "p1", steps=steps)

        dev_steps = workflow.get_steps_by_phase(SDLCPhase.DEVELOPMENT)
        assert len(dev_steps) == 2

        design_steps = workflow.get_steps_by_phase(SDLCPhase.DESIGN)
        assert len(design_steps) == 1

    def test_get_step_by_id(self):
        """Test getting step by ID"""
        steps = [
            WorkflowStep("s1", "Step 1", SDLCPhase.DESIGN),
            WorkflowStep("s2", "Step 2", SDLCPhase.DEVELOPMENT)
        ]

        workflow = SDLCWorkflow("wf-003", "Project", "Desc", "p1", steps=steps)

        step = workflow.get_step_by_id("s1")
        assert step is not None
        assert step.step_id == "s1"

        missing = workflow.get_step_by_id("s999")
        assert missing is None

    def test_get_ready_steps(self):
        """Test getting ready steps"""
        steps = [
            WorkflowStep("s1", "Ready", SDLCPhase.DESIGN, status=WorkflowStepStatus.READY),
            WorkflowStep("s2", "In Progress", SDLCPhase.DESIGN, status=WorkflowStepStatus.IN_PROGRESS),
            WorkflowStep("s3", "Pending", SDLCPhase.DEVELOPMENT, status=WorkflowStepStatus.PENDING),
            WorkflowStep("s4", "Completed", SDLCPhase.DEVELOPMENT, status=WorkflowStepStatus.COMPLETED)
        ]

        workflow = SDLCWorkflow("wf-004", "Project", "Desc", "p1", steps=steps)

        ready = workflow.get_ready_steps()
        assert len(ready) == 2  # READY and PENDING (no deps)

    def test_get_ready_steps_with_dependencies(self):
        """Test getting ready steps respects dependencies"""
        steps = [
            WorkflowStep("s1", "First", SDLCPhase.DESIGN, status=WorkflowStepStatus.COMPLETED),
            WorkflowStep("s2", "Second", SDLCPhase.DEVELOPMENT, depends_on=["s1"]),
            WorkflowStep("s3", "Third", SDLCPhase.TESTING, depends_on=["s2"])
        ]

        workflow = SDLCWorkflow("wf-005", "Project", "Desc", "p1", steps=steps)

        ready = workflow.get_ready_steps()
        assert len(ready) == 1  # Only s2 is ready (s1 is complete)
        assert ready[0].step_id == "s2"

    def test_calculate_progress(self):
        """Test workflow progress calculation"""
        steps = [
            WorkflowStep("s1", "S1", SDLCPhase.DESIGN, status=WorkflowStepStatus.COMPLETED),
            WorkflowStep("s2", "S2", SDLCPhase.DESIGN, status=WorkflowStepStatus.COMPLETED),
            WorkflowStep("s3", "S3", SDLCPhase.DEVELOPMENT, status=WorkflowStepStatus.IN_PROGRESS),
            WorkflowStep("s4", "S4", SDLCPhase.TESTING, status=WorkflowStepStatus.PENDING)
        ]

        workflow = SDLCWorkflow("wf-006", "Project", "Desc", "p1", steps=steps)

        progress = workflow.calculate_progress()
        assert progress == 50.0  # 2 out of 4 completed

    def test_estimated_total_duration(self):
        """Test total estimated duration calculation"""
        steps = [
            WorkflowStep("s1", "S1", SDLCPhase.DESIGN, estimated_duration_hours=4.0),
            WorkflowStep("s2", "S2", SDLCPhase.DEVELOPMENT, estimated_duration_hours=8.0),
            WorkflowStep("s3", "S3", SDLCPhase.TESTING, estimated_duration_hours=6.0)
        ]

        workflow = SDLCWorkflow("wf-007", "Project", "Desc", "p1", steps=steps)

        total = workflow.estimated_total_duration_hours()
        assert total == 18.0

    def test_critical_path(self):
        """Test critical path calculation"""
        steps = [
            WorkflowStep("s1", "Setup", SDLCPhase.DESIGN, estimated_duration_hours=2.0),
            WorkflowStep("s2", "Backend", SDLCPhase.DEVELOPMENT, estimated_duration_hours=8.0, depends_on=["s1"]),
            WorkflowStep("s3", "Frontend", SDLCPhase.DEVELOPMENT, estimated_duration_hours=6.0, depends_on=["s1"]),
            WorkflowStep("s4", "Integration", SDLCPhase.TESTING, estimated_duration_hours=4.0, depends_on=["s2", "s3"])
        ]

        workflow = SDLCWorkflow("wf-008", "Project", "Desc", "p1", steps=steps)

        critical_path = workflow.get_critical_path()

        # Critical path should be: s1 -> s2 -> s4 (2 + 8 + 4 = 14 hours)
        assert len(critical_path) == 3
        assert critical_path[0].step_id == "s1"
        assert critical_path[1].step_id == "s2"
        assert critical_path[2].step_id == "s4"

    def test_workflow_statistics(self):
        """Test workflow statistics"""
        steps = [
            WorkflowStep("s1", "Design", SDLCPhase.DESIGN, status=WorkflowStepStatus.COMPLETED),
            WorkflowStep("s2", "Develop", SDLCPhase.DEVELOPMENT, status=WorkflowStepStatus.IN_PROGRESS),
            WorkflowStep("s3", "Test", SDLCPhase.TESTING, status=WorkflowStepStatus.PENDING)
        ]

        workflow = SDLCWorkflow("wf-009", "Project", "Desc", "p1", steps=steps)

        stats = workflow.workflow_statistics()

        assert stats["total_steps"] == 3
        assert stats["completed"] == 1
        assert stats["in_progress"] == 1
        assert stats["pending"] == 1
        assert stats["progress_percentage"] == pytest.approx(33.33, 0.1)

    def test_workflow_to_dict(self):
        """Test workflow serialization"""
        workflow = SDLCWorkflow(
            workflow_id="wf-010",
            name="Test Workflow",
            description="Test description",
            project_id="p1"
        )

        data = workflow.to_dict()

        assert data["workflow_id"] == "wf-010"
        assert data["name"] == "Test Workflow"
        assert data["status"] == "draft"
        assert "statistics" in data


# ============================================================================
# Test ContractOrchestrator
# ============================================================================

class TestContractOrchestrator:
    """Tests for ContractOrchestrator class"""

    def test_orchestrator_creation(self):
        """Test creating ContractOrchestrator"""
        workflow = SDLCWorkflow("wf-1", "Workflow", "Test", "p1")
        team = AgentTeam("team-1", "Team", [])

        orch = ContractOrchestrator(
            orchestrator_id="orch-001",
            workflow=workflow,
            team=team
        )

        assert orch.orchestrator_id == "orch-001"
        assert orch.workflow == workflow
        assert orch.team == team
        assert len(orch.contracts) == 0
        assert len(orch.handoffs) == 0

    def test_add_contract(self):
        """Test adding contracts to orchestrator"""
        workflow = SDLCWorkflow("wf-1", "Workflow", "Test", "p1")
        team = AgentTeam("team-1", "Team", [])
        orch = ContractOrchestrator("orch-1", workflow, team)

        contract = UniversalContract(
            contract_id="c1",
            contract_type="API",
            name="API Contract",
            description="REST API",
            provider_agent="backend",
            consumer_agents=["frontend"],
            specification={},
            acceptance_criteria=[]
        )

        orch.add_contract(contract)

        assert len(orch.contracts) == 1
        assert orch.get_contract("c1") == contract

    def test_add_handoff(self):
        """Test adding handoffs to orchestrator"""
        workflow = SDLCWorkflow("wf-1", "Workflow", "Test", "p1")
        team = AgentTeam("team-1", "Team", [])
        orch = ContractOrchestrator("orch-1", workflow, team)

        handoff = HandoffSpec(
            handoff_id="h1",
            from_phase="design",
            to_phase="development"
        )

        orch.add_handoff(handoff)

        assert len(orch.handoffs) == 1
        assert orch.get_handoff("h1") == handoff

    def test_assign_agent_to_step(self):
        """Test assigning agent to step"""
        agent = Agent("a1", "Dev", [AgentRole.BACKEND_DEVELOPER])
        team = AgentTeam("team-1", "Team", [agent])

        step = WorkflowStep("s1", "Develop", SDLCPhase.DEVELOPMENT)
        workflow = SDLCWorkflow("wf-1", "Workflow", "Test", "p1", steps=[step])

        orch = ContractOrchestrator("orch-1", workflow, team)

        success = orch.assign_agent_to_step("s1", "a1")

        assert success is True
        assert step.assigned_to == "a1"

    def test_assign_agent_to_step_unavailable(self):
        """Test assigning unavailable agent fails"""
        agent = Agent("a1", "Dev", [AgentRole.BACKEND_DEVELOPER], available=False)
        team = AgentTeam("team-1", "Team", [agent])

        step = WorkflowStep("s1", "Develop", SDLCPhase.DEVELOPMENT)
        workflow = SDLCWorkflow("wf-1", "Workflow", "Test", "p1", steps=[step])

        orch = ContractOrchestrator("orch-1", workflow, team)

        success = orch.assign_agent_to_step("s1", "a1")

        assert success is False
        assert step.assigned_to is None

    def test_auto_assign_agents(self):
        """Test auto-assigning agents to ready steps"""
        agents = [
            Agent("a1", "Dev", [AgentRole.BACKEND_DEVELOPER]),
            Agent("a2", "QA", [AgentRole.QA_ENGINEER])
        ]
        team = AgentTeam("team-1", "Team", agents)

        steps = [
            WorkflowStep("s1", "Dev", SDLCPhase.DEVELOPMENT, status=WorkflowStepStatus.READY),
            WorkflowStep("s2", "Test", SDLCPhase.TESTING, status=WorkflowStepStatus.READY)
        ]
        workflow = SDLCWorkflow("wf-1", "Workflow", "Test", "p1", steps=steps)

        orch = ContractOrchestrator("orch-1", workflow, team)

        assignments = orch.auto_assign_agents()

        assert assignments == 2
        assert steps[0].assigned_to is not None
        assert steps[1].assigned_to is not None

    def test_start_step(self):
        """Test starting a workflow step"""
        agent = Agent("a1", "Dev", [AgentRole.BACKEND_DEVELOPER])
        team = AgentTeam("team-1", "Team", [agent])

        step = WorkflowStep("s1", "Develop", SDLCPhase.DEVELOPMENT, assigned_to="a1")
        workflow = SDLCWorkflow("wf-1", "Workflow", "Test", "p1", steps=[step])

        orch = ContractOrchestrator("orch-1", workflow, team)

        success = orch.start_step("s1")

        assert success is True
        assert step.status == WorkflowStepStatus.IN_PROGRESS
        assert step.started_at is not None
        assert orch.active_step_id == "s1"

    def test_start_step_with_dependencies(self):
        """Test starting step with incomplete dependencies fails"""
        agent = Agent("a1", "Dev", [AgentRole.BACKEND_DEVELOPER])
        team = AgentTeam("team-1", "Team", [agent])

        steps = [
            WorkflowStep("s1", "First", SDLCPhase.DESIGN),
            WorkflowStep("s2", "Second", SDLCPhase.DEVELOPMENT, depends_on=["s1"])
        ]
        workflow = SDLCWorkflow("wf-1", "Workflow", "Test", "p1", steps=steps)

        orch = ContractOrchestrator("orch-1", workflow, team)

        # Try to start s2 before s1 is complete
        success = orch.start_step("s2")

        assert success is False

    def test_complete_step(self):
        """Test completing a workflow step"""
        agent = Agent("a1", "Dev", [AgentRole.BACKEND_DEVELOPER])
        team = AgentTeam("team-1", "Team", [agent])

        step = WorkflowStep(
            "s1", "Develop", SDLCPhase.DEVELOPMENT,
            status=WorkflowStepStatus.IN_PROGRESS,
            assigned_to="a1",
            started_at=datetime.utcnow()
        )
        workflow = SDLCWorkflow("wf-1", "Workflow", "Test", "p1", steps=[step])

        orch = ContractOrchestrator("orch-1", workflow, team)
        orch.active_step_id = "s1"

        success = orch.complete_step("s1", success=True)

        assert success is True
        assert step.status == WorkflowStepStatus.COMPLETED
        assert step.completed_at is not None
        assert agent.completed_tasks == 1

    def test_complete_step_updates_agent_success_rate(self):
        """Test completing step updates agent performance"""
        agent = Agent("a1", "Dev", [AgentRole.BACKEND_DEVELOPER], completed_tasks=4, success_rate=1.0)
        team = AgentTeam("team-1", "Team", [agent])

        step = WorkflowStep(
            "s1", "Develop", SDLCPhase.DEVELOPMENT,
            status=WorkflowStepStatus.IN_PROGRESS,
            assigned_to="a1"
        )
        workflow = SDLCWorkflow("wf-1", "Workflow", "Test", "p1", steps=[step])

        orch = ContractOrchestrator("orch-1", workflow, team)

        # Complete with failure
        orch.complete_step("s1", success=False)

        assert agent.completed_tasks == 5
        assert agent.success_rate == 0.8  # 4/5

    def test_get_workflow_status(self):
        """Test getting comprehensive workflow status"""
        agent = Agent("a1", "Dev", [AgentRole.BACKEND_DEVELOPER])
        team = AgentTeam("team-1", "Team", [agent])

        step = WorkflowStep("s1", "Develop", SDLCPhase.DEVELOPMENT)
        workflow = SDLCWorkflow("wf-1", "Workflow", "Test", "p1", steps=[step])

        orch = ContractOrchestrator("orch-1", workflow, team)

        # Add a contract
        contract = UniversalContract(
            contract_id="c1",
            contract_type="API",
            name="API",
            description="API",
            provider_agent="a1",
            consumer_agents=[],
            specification={},
            acceptance_criteria=[]
        )
        orch.add_contract(contract)

        status = orch.get_workflow_status()

        assert status["orchestrator_id"] == "orch-1"
        assert status["contracts"]["total_contracts"] == 1
        assert status["team"]["total_agents"] == 1

    def test_orchestrator_to_dict(self):
        """Test orchestrator serialization"""
        agent = Agent("a1", "Dev", [AgentRole.BACKEND_DEVELOPER])
        team = AgentTeam("team-1", "Team", [agent])
        workflow = SDLCWorkflow("wf-1", "Workflow", "Test", "p1")

        orch = ContractOrchestrator("orch-1", workflow, team)

        data = orch.to_dict()

        assert data["orchestrator_id"] == "orch-1"
        assert "workflow" in data
        assert "team" in data
        assert "status" in data


# ============================================================================
# Integration Tests
# ============================================================================

class TestSDLCIntegration:
    """Integration tests for complete SDLC workflows"""

    def test_complete_workflow_execution(self):
        """Test executing a complete SDLC workflow"""
        # Create team
        agents = [
            Agent("designer", "UX Designer", [AgentRole.UX_DESIGNER]),
            Agent("backend-dev", "Backend Dev", [AgentRole.BACKEND_DEVELOPER]),
            Agent("qa", "QA Engineer", [AgentRole.QA_ENGINEER])
        ]
        team = AgentTeam("team-1", "Dev Team", agents)

        # Create workflow
        steps = [
            WorkflowStep("s1", "Design UI", SDLCPhase.DESIGN, estimated_duration_hours=4.0),
            WorkflowStep("s2", "Develop API", SDLCPhase.DEVELOPMENT, depends_on=["s1"], estimated_duration_hours=8.0),
            WorkflowStep("s3", "Test", SDLCPhase.TESTING, depends_on=["s2"], estimated_duration_hours=4.0)
        ]
        workflow = SDLCWorkflow("wf-1", "E-commerce", "Build shop", "p1", steps=steps)

        # Create orchestrator
        orch = ContractOrchestrator("orch-1", workflow, team)

        # Execute workflow
        # Step 1: Design
        orch.assign_agent_to_step("s1", "designer")
        orch.start_step("s1")
        assert steps[0].status == WorkflowStepStatus.IN_PROGRESS

        orch.complete_step("s1", success=True)
        assert steps[0].status == WorkflowStepStatus.COMPLETED

        # Step 2: Development
        ready = workflow.get_ready_steps()
        assert len(ready) == 1
        assert ready[0].step_id == "s2"

        orch.assign_agent_to_step("s2", "backend-dev")
        orch.start_step("s2")
        orch.complete_step("s2", success=True)

        # Step 3: Testing
        orch.assign_agent_to_step("s3", "qa")
        orch.start_step("s3")
        orch.complete_step("s3", success=True)

        # Check completion
        assert workflow.calculate_progress() == 100.0

    def test_workflow_with_handoffs(self):
        """Test workflow with handoffs between phases"""
        team = AgentTeam("team-1", "Team", [
            Agent("dev", "Developer", [AgentRole.BACKEND_DEVELOPER])
        ])

        # Create handoff
        handoff = HandoffSpec(
            handoff_id="h1",
            from_phase="design",
            to_phase="development",
            status=HandoffStatus.READY
        )

        # Create workflow with handoff
        step = WorkflowStep(
            "s1", "Develop",
            SDLCPhase.DEVELOPMENT,
            input_handoff_id="h1"
        )
        workflow = SDLCWorkflow("wf-1", "Project", "Test", "p1", steps=[step])

        # Create orchestrator
        orch = ContractOrchestrator("orch-1", workflow, team)
        orch.add_handoff(handoff)

        # Start step with handoff
        orch.assign_agent_to_step("s1", "dev")
        orch.start_step("s1")

        # Handoff should be in progress
        assert handoff.status == HandoffStatus.IN_PROGRESS

        # Complete step
        orch.complete_step("s1", success=True)

        # Handoff should be completed
        assert handoff.status == HandoffStatus.COMPLETED

    def test_multi_agent_parallel_execution(self):
        """Test multiple agents working in parallel"""
        agents = [
            Agent("dev1", "Dev 1", [AgentRole.BACKEND_DEVELOPER]),
            Agent("dev2", "Dev 2", [AgentRole.FRONTEND_DEVELOPER]),
            Agent("qa", "QA", [AgentRole.QA_ENGINEER])
        ]
        team = AgentTeam("team-1", "Team", agents)

        # Create parallel steps
        steps = [
            WorkflowStep("s1", "Setup", SDLCPhase.DESIGN, estimated_duration_hours=1.0),
            WorkflowStep("s2", "Backend", SDLCPhase.DEVELOPMENT, depends_on=["s1"]),
            WorkflowStep("s3", "Frontend", SDLCPhase.DEVELOPMENT, depends_on=["s1"]),
            WorkflowStep("s4", "Integration", SDLCPhase.TESTING, depends_on=["s2", "s3"])
        ]
        workflow = SDLCWorkflow("wf-1", "Project", "Test", "p1", steps=steps)

        orch = ContractOrchestrator("orch-1", workflow, team)

        # Complete setup
        orch.assign_agent_to_step("s1", "dev1")
        orch.start_step("s1")
        orch.complete_step("s1", success=True)

        # Both backend and frontend should be ready
        ready = workflow.get_ready_steps()
        assert len(ready) == 2

        # Assign and execute in parallel
        orch.assign_agent_to_step("s2", "dev1")
        orch.assign_agent_to_step("s3", "dev2")

        orch.start_step("s2")
        orch.start_step("s3")

        # Both should be in progress
        in_progress = workflow.get_in_progress_steps()
        assert len(in_progress) == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
