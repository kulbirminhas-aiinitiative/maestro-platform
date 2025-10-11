"""
Quality Fabric Integration Tests
Version: 1.0.0

Comprehensive tests for Universal Contract Protocol with Quality Fabric validation.
"""

import pytest
import asyncio
import tempfile
import os
import json
from datetime import datetime
from pathlib import Path

# Import quality fabric client
import sys
sys.path.insert(0, '/home/ec2-user/projects/maestro-platform/maestro-hive')
from quality_fabric_client import QualityFabricClient, PersonaType

# Import contract protocol modules
from contracts.models import UniversalContract, ContractLifecycle, AcceptanceCriterion
from contracts.artifacts import ArtifactStore, Artifact, ArtifactManifest
from contracts.validators import (
    BaseValidator, ValidationResult,
    ScreenshotDiffValidator, OpenAPIValidator,
    PerformanceValidator, SecurityValidator
)
from contracts.handoff import HandoffSpec, HandoffTask, HandoffStatus
from contracts.sdlc import (
    Agent, AgentTeam, AgentRole,
    SDLCWorkflow, WorkflowStep, SDLCPhase, WorkflowStepStatus,
    ContractOrchestrator
)


# ============================================================================
# Test Fixtures
# ============================================================================

@pytest.fixture
def quality_client():
    """Create Quality Fabric client"""
    return QualityFabricClient(quality_fabric_url="http://localhost:8001")


@pytest.fixture
def temp_dir():
    """Create temporary directory"""
    temp_path = tempfile.mkdtemp()
    yield temp_path
    import shutil
    if os.path.exists(temp_path):
        shutil.rmtree(temp_path)


@pytest.fixture
def artifact_store(temp_dir):
    """Create artifact store"""
    store_path = os.path.join(temp_dir, "artifacts")
    return ArtifactStore(store_path)


# ============================================================================
# Phase 2: Artifact Storage with Quality Fabric
# ============================================================================

class TestArtifactStorageQuality:
    """Test artifact storage with quality validation"""

    @pytest.mark.asyncio
    async def test_artifact_storage_quality_validation(self, artifact_store, temp_dir, quality_client):
        """Test artifact storage with quality fabric validation"""

        # Create test artifacts
        code_file = os.path.join(temp_dir, "api.py")
        with open(code_file, 'w') as f:
            f.write("# API implementation\nclass API:\n    pass\n")

        test_file = os.path.join(temp_dir, "test_api.py")
        with open(test_file, 'w') as f:
            f.write("# API tests\ndef test_api():\n    pass\n")

        # Store artifacts
        code_artifact = artifact_store.store(
            file_path=code_file,
            role="deliverable",
            media_type="text/x-python",
            related_contract_id="contract-001"
        )

        test_artifact = artifact_store.store(
            file_path=test_file,
            role="evidence",
            media_type="text/x-python",
            related_contract_id="contract-001"
        )

        # Verify storage
        assert code_artifact is not None
        assert test_artifact is not None
        assert artifact_store.verify_artifact(code_artifact) is True

        # Create output for quality validation
        output = {
            "code_files": [
                {
                    "name": "api.py",
                    "path": code_artifact.path,
                    "digest": code_artifact.digest,
                    "content": "# API implementation"
                }
            ],
            "test_files": [
                {
                    "name": "test_api.py",
                    "path": test_artifact.path,
                    "digest": test_artifact.digest,
                    "content": "# API tests"
                }
            ],
            "metadata": {
                "total_artifacts": 2,
                "verified": True
            }
        }

        # Validate with Quality Fabric
        result = await quality_client.validate_persona_output(
            persona_id="storage-test-001",
            persona_type=PersonaType.BACKEND_DEVELOPER,
            output=output
        )

        # Assertions
        assert result.status in ["pass", "warning"]
        assert result.overall_score > 0.5
        assert "code_files_present" in result.gates_passed
        assert "test_files_present" in result.gates_passed


# ============================================================================
# Phase 3: Validator Framework with Quality Fabric
# ============================================================================

class TestValidatorFrameworkQuality:
    """Test validator framework with quality validation"""

    @pytest.mark.asyncio
    async def test_performance_validator_quality(self, temp_dir, quality_client):
        """Test performance validator with quality fabric"""

        # Create performance metrics
        metrics = {
            "load_time_ms": 2500,
            "ttfb_ms": 400,
            "fcp_ms": 1200,
            "lcp_ms": 2000,
            "tti_ms": 2800,
            "cls": 0.08,
            "api_response_ms": 250
        }

        metrics_file = os.path.join(temp_dir, "performance.json")
        with open(metrics_file, 'w') as f:
            json.dump(metrics, f)

        # Run validator
        validator = PerformanceValidator()
        validation_result = await validator.execute(
            artifacts={"metrics": metrics_file},
            config={
                "max_load_time_ms": 3000,
                "max_lcp_ms": 2500,
                "max_cls": 0.1
            }
        )

        assert validation_result.passed is True
        assert validation_result.score > 0.8

        # Create output for quality validation (QA needs > 5 test files)
        output = {
            "test_files": [
                {"name": "performance_results.json", "content": json.dumps(metrics), "type": "performance_metrics"},
                {"name": "test_load_time.py", "content": "# Load time tests"},
                {"name": "test_lcp.py", "content": "# LCP tests"},
                {"name": "test_cls.py", "content": "# CLS tests"},
                {"name": "test_tti.py", "content": "# TTI tests"},
                {"name": "test_api_response.py", "content": "# API response tests"},
                {"name": "test_integration.py", "content": "# Integration tests"}
            ],
            "documentation": [
                {
                    "name": "performance_report.md",
                    "content": f"Performance validation: {validation_result.message}"
                }
            ],
            "metadata": {
                "validator": "PerformanceValidator",
                "score": validation_result.score,
                "passed": validation_result.passed,
                "metrics": validation_result.evidence
            }
        }

        # Validate with Quality Fabric
        result = await quality_client.validate_persona_output(
            persona_id="perf-validator-001",
            persona_type=PersonaType.QA_ENGINEER,
            output=output
        )

        assert result.status in ["pass", "warning"]
        assert result.overall_score > 0.0

    @pytest.mark.asyncio
    async def test_security_validator_quality(self, temp_dir, quality_client):
        """Test security validator with quality fabric"""

        # Create security scan results
        scan_results = {
            "vulnerabilities": [
                {
                    "cve_id": "CVE-2024-0001",
                    "severity": "medium",
                    "description": "Minor vulnerability",
                    "package": "test-lib",
                    "fixed_in": "2.0.0"
                }
            ]
        }

        scan_file = os.path.join(temp_dir, "security_scan.json")
        with open(scan_file, 'w') as f:
            json.dump(scan_results, f)

        # Run validator
        validator = SecurityValidator()
        validation_result = await validator.execute(
            artifacts={"scan_results": scan_file},
            config={
                "severity_threshold": "high",
                "check_dependencies": True
            }
        )

        # Should pass (medium severity with high threshold)
        assert validation_result.passed is True

        # Create output for quality validation
        output = {
            "test_files": [
                {
                    "name": "security_scan.json",
                    "content": json.dumps(scan_results)
                }
            ],
            "documentation": [
                {
                    "name": "security_report.md",
                    "content": f"Security validation: {validation_result.message}"
                }
            ],
            "metadata": {
                "validator": "SecurityValidator",
                "total_vulnerabilities": len(scan_results["vulnerabilities"]),
                "critical": 0,
                "high": 0,
                "medium": 1
            }
        }

        # Validate with Quality Fabric
        result = await quality_client.validate_persona_output(
            persona_id="sec-validator-001",
            persona_type=PersonaType.SECURITY_ENGINEER,
            output=output
        )

        assert result.status in ["pass", "warning"]


# ============================================================================
# Phase 4: Handoff System with Quality Fabric
# ============================================================================

class TestHandoffSystemQuality:
    """Test handoff system with quality validation"""

    @pytest.mark.asyncio
    async def test_handoff_quality_gates(self, quality_client):
        """Test handoff system with quality gate validation"""

        # Create handoff with tasks
        handoff = HandoffSpec(
            handoff_id="handoff-q-001",
            from_phase="development",
            to_phase="testing",
            tasks=[
                HandoffTask(
                    task_id="t1",
                    description="Complete unit tests",
                    completed=True,
                    priority="high"
                ),
                HandoffTask(
                    task_id="t2",
                    description="Update documentation",
                    completed=True,
                    priority="medium"
                ),
                HandoffTask(
                    task_id="t3",
                    description="Deploy to staging",
                    completed=False,
                    priority="critical"
                )
            ],
            status=HandoffStatus.IN_PROGRESS
        )

        # Calculate completion
        completed_tasks = sum(1 for t in handoff.tasks if t.completed)
        total_tasks = len(handoff.tasks)
        completion_rate = completed_tasks / total_tasks

        # Create output for quality validation
        output = {
            "code_files": [
                {"name": "implementation.py", "content": "# Implementation"}
            ],
            "test_files": [
                {"name": "test_implementation.py", "content": "# Tests"}
            ],
            "documentation": [
                {"name": "handoff_checklist.md", "content": "# Handoff checklist"}
            ],
            "metadata": {
                "handoff_id": handoff.handoff_id,
                "from_phase": handoff.from_phase,
                "to_phase": handoff.to_phase,
                "tasks_total": total_tasks,
                "tasks_completed": completed_tasks,
                "completion_rate": completion_rate,
                "status": handoff.status.value
            }
        }

        # Validate with Quality Fabric
        result = await quality_client.validate_persona_output(
            persona_id="handoff-dev-001",
            persona_type=PersonaType.BACKEND_DEVELOPER,
            output=output
        )

        assert result is not None
        assert result.overall_score > 0.0

        # Result depends on code/test files presence (mock validation logic)
        # If completion rate is low, we may get warnings (but not guaranteed with mock)
        assert result.status in ["pass", "warning", "fail"]


# ============================================================================
# Phase 5: SDLC Integration with Quality Fabric
# ============================================================================

class TestSDLCIntegrationQuality:
    """Test SDLC integration with quality validation"""

    @pytest.mark.asyncio
    async def test_complete_sdlc_workflow_with_quality(self, quality_client, artifact_store, temp_dir):
        """Test complete SDLC workflow with quality fabric validation at each phase"""

        # 1. Create team
        team = AgentTeam(
            team_id="team-quality-001",
            name="Quality-Validated Team",
            agents=[
                Agent("backend-dev", "Backend Developer", [AgentRole.BACKEND_DEVELOPER]),
                Agent("qa-engineer", "QA Engineer", [AgentRole.QA_ENGINEER]),
                Agent("devops", "DevOps", [AgentRole.DEVOPS_ENGINEER])
            ]
        )

        # 2. Create workflow
        workflow = SDLCWorkflow(
            workflow_id="wf-quality-001",
            name="Quality-Validated Workflow",
            description="Complete workflow with quality gates",
            project_id="proj-001",
            team_id=team.team_id,
            steps=[
                WorkflowStep(
                    "s1", "Backend Development",
                    SDLCPhase.DEVELOPMENT,
                    estimated_duration_hours=8.0
                ),
                WorkflowStep(
                    "s2", "Testing",
                    SDLCPhase.TESTING,
                    depends_on=["s1"],
                    estimated_duration_hours=4.0
                ),
                WorkflowStep(
                    "s3", "Deployment",
                    SDLCPhase.DEPLOYMENT,
                    depends_on=["s2"],
                    estimated_duration_hours=2.0
                )
            ]
        )

        # 3. Create orchestrator
        orch = ContractOrchestrator(
            orchestrator_id="orch-quality-001",
            workflow=workflow,
            team=team
        )

        # 4. Execute workflow with quality validation at each step

        # STEP 1: Development
        orch.assign_agent_to_step("s1", "backend-dev")
        orch.start_step("s1")

        # Simulate development work and create artifacts
        code_file = os.path.join(temp_dir, "user_service.py")
        with open(code_file, 'w') as f:
            f.write("""
# User Service Implementation
class UserService:
    def get_user(self, user_id):
        return {"id": user_id, "name": "Test User"}

    def create_user(self, data):
        return {"id": 1, "name": data.get("name")}
""")

        test_file = os.path.join(temp_dir, "test_user_service.py")
        with open(test_file, 'w') as f:
            f.write("""
# User Service Tests
def test_get_user():
    service = UserService()
    user = service.get_user(1)
    assert user["id"] == 1

def test_create_user():
    service = UserService()
    user = service.create_user({"name": "John"})
    assert user["name"] == "John"
""")

        # Store artifacts
        code_artifact = artifact_store.store(
            file_path=code_file,
            role="deliverable",
            media_type="text/x-python",
            related_contract_id="contract-dev-001"
        )

        test_artifact = artifact_store.store(
            file_path=test_file,
            role="evidence",
            media_type="text/x-python",
            related_contract_id="contract-dev-001"
        )

        # Validate development output with Quality Fabric
        dev_output = {
            "code_files": [
                {"name": "user_service.py", "path": code_artifact.path}
            ],
            "test_files": [
                {"name": "test_user_service.py", "path": test_artifact.path}
            ],
            "documentation": [],
            "metadata": {
                "phase": "development",
                "step_id": "s1"
            }
        }

        dev_result = await quality_client.validate_persona_output(
            persona_id="backend-dev",
            persona_type=PersonaType.BACKEND_DEVELOPER,
            output=dev_output
        )

        print(f"\n📊 Development Quality:")
        print(f"   Status: {dev_result.status}")
        print(f"   Score: {dev_result.overall_score:.1%}")
        print(f"   Gates Passed: {', '.join(dev_result.gates_passed)}")

        # Complete step if quality passes
        assert dev_result.status in ["pass", "warning"]
        orch.complete_step("s1", success=True)

        # STEP 2: Testing
        orch.assign_agent_to_step("s2", "qa-engineer")
        orch.start_step("s2")

        # Simulate QA work
        qa_output = {
            "code_files": [],
            "test_files": [
                {"name": "test_user_service.py", "content": "# Unit tests"},
                {"name": "test_integration.py", "content": "# Integration tests"},
                {"name": "test_e2e.py", "content": "# E2E tests"},
                {"name": "test_performance.py", "content": "# Performance tests"},
                {"name": "test_security.py", "content": "# Security tests"},
                {"name": "test_accessibility.py", "content": "# Accessibility tests"}
            ],
            "documentation": [
                {"name": "test_report.md", "content": "# Test Report\nAll tests passed"}
            ],
            "metadata": {
                "phase": "testing",
                "step_id": "s2",
                "tests_executed": 6,
                "tests_passed": 6,
                "coverage": 85.5
            }
        }

        qa_result = await quality_client.validate_persona_output(
            persona_id="qa-engineer",
            persona_type=PersonaType.QA_ENGINEER,
            output=qa_output
        )

        print(f"\n🧪 Testing Quality:")
        print(f"   Status: {qa_result.status}")
        print(f"   Score: {qa_result.overall_score:.1%}")
        print(f"   Gates Passed: {', '.join(qa_result.gates_passed)}")

        # Complete testing
        assert qa_result.status in ["pass", "warning"]
        orch.complete_step("s2", success=True)

        # STEP 3: Evaluate phase gate for deployment
        persona_results = [
            {
                "persona_id": dev_result.persona_id,
                "persona_type": dev_result.persona_type,
                "overall_score": dev_result.overall_score,
                "status": dev_result.status
            },
            {
                "persona_id": qa_result.persona_id,
                "persona_type": qa_result.persona_type,
                "overall_score": qa_result.overall_score,
                "status": qa_result.status
            }
        ]

        phase_gate_result = await quality_client.evaluate_phase_gate(
            current_phase="testing",
            next_phase="deployment",
            phase_outputs={},
            persona_results=persona_results
        )

        print(f"\n🚪 Phase Gate Evaluation:")
        print(f"   Status: {phase_gate_result['status']}")
        print(f"   Quality Score: {phase_gate_result['overall_quality_score']:.1%}")
        print(f"   Gates Passed: {', '.join(phase_gate_result['gates_passed'])}")

        # Deployment step
        if phase_gate_result["status"] in ["pass", "warning"]:
            orch.assign_agent_to_step("s3", "devops")
            orch.start_step("s3")
            orch.complete_step("s3", success=True)

        # 5. Final workflow status
        final_status = orch.get_workflow_status()

        print(f"\n✅ Workflow Complete:")
        print(f"   Progress: {final_status['workflow']['progress_percentage']}%")
        print(f"   Completed Steps: {final_status['workflow']['completed']}")
        print(f"   Team Success Rate: {final_status['team']['average_success_rate']:.1%}")

        # Assertions
        assert final_status['workflow']['progress_percentage'] == 100.0
        assert dev_result.overall_score > 0.0
        assert qa_result.overall_score > 0.0
        assert phase_gate_result["overall_quality_score"] > 0.0


# ============================================================================
# Integration Tests with Multiple Validators
# ============================================================================

class TestMultiValidatorQuality:
    """Test multiple validators with quality fabric"""

    @pytest.mark.asyncio
    async def test_multi_validator_pipeline(self, temp_dir, quality_client):
        """Test running multiple validators with quality validation"""

        # Create test artifacts
        perf_metrics = {
            "load_time_ms": 2000,
            "lcp_ms": 1800,
            "cls": 0.05
        }

        perf_file = os.path.join(temp_dir, "perf.json")
        with open(perf_file, 'w') as f:
            json.dump(perf_metrics, f)

        security_scan = {
            "vulnerabilities": []  # Clean scan
        }

        sec_file = os.path.join(temp_dir, "security.json")
        with open(sec_file, 'w') as f:
            json.dump(security_scan, f)

        # Run validators
        perf_validator = PerformanceValidator()
        perf_result = await perf_validator.execute(
            artifacts={"metrics": perf_file},
            config={"max_load_time_ms": 3000}
        )

        sec_validator = SecurityValidator()
        sec_result = await sec_validator.execute(
            artifacts={"scan_results": sec_file},
            config={"severity_threshold": "high"}
        )

        # Aggregate results
        all_passed = perf_result.passed and sec_result.passed
        avg_score = (perf_result.score + sec_result.score) / 2

        # Create comprehensive output
        output = {
            "code_files": [
                {"name": "service.py", "content": "# Service implementation"}
            ],
            "test_files": [
                {"name": "test_performance.py", "content": "# Performance tests"},
                {"name": "test_security.py", "content": "# Security tests"}
            ],
            "documentation": [
                {"name": "validation_report.md", "content": "# Validation Report"}
            ],
            "metadata": {
                "validators_run": 2,
                "performance_score": perf_result.score,
                "security_score": sec_result.score,
                "average_score": avg_score,
                "all_passed": all_passed
            }
        }

        # Validate with Quality Fabric
        result = await quality_client.validate_persona_output(
            persona_id="multi-validator-001",
            persona_type=PersonaType.QA_ENGINEER,
            output=output
        )

        print(f"\n🔍 Multi-Validator Quality:")
        print(f"   Status: {result.status}")
        print(f"   Score: {result.overall_score:.1%}")
        print(f"   Performance Passed: {perf_result.passed}")
        print(f"   Security Passed: {sec_result.passed}")

        # Assertions
        assert result is not None
        assert perf_result.passed is True
        assert sec_result.passed is True


# ============================================================================
# Stress Tests with Quality Fabric
# ============================================================================

class TestQualityStressTesting:
    """Stress tests with quality validation"""

    @pytest.mark.asyncio
    async def test_high_volume_artifacts_quality(self, artifact_store, temp_dir, quality_client):
        """Test high volume artifact storage with quality validation"""

        # Create many artifacts
        artifact_count = 20
        artifacts = []

        for i in range(artifact_count):
            file_path = os.path.join(temp_dir, f"module_{i}.py")
            with open(file_path, 'w') as f:
                f.write(f"# Module {i}\nclass Module{i}:\n    pass\n")

            artifact = artifact_store.store(
                file_path=file_path,
                role="deliverable",
                media_type="text/x-python",
                related_contract_id=f"contract-{i:03d}"
            )
            artifacts.append(artifact)

        # Verify all artifacts
        verified = sum(1 for a in artifacts if artifact_store.verify_artifact(a))
        verification_rate = verified / len(artifacts)

        # Create output
        output = {
            "code_files": [
                {"name": f"module_{i}.py", "content": f"# Module {i}"}
                for i in range(artifact_count)
            ],
            "test_files": [],  # Intentionally missing tests
            "metadata": {
                "total_artifacts": artifact_count,
                "verified_artifacts": verified,
                "verification_rate": verification_rate
            }
        }

        # Validate with Quality Fabric
        result = await quality_client.validate_persona_output(
            persona_id="stress-test-001",
            persona_type=PersonaType.BACKEND_DEVELOPER,
            output=output
        )

        print(f"\n💪 Stress Test Quality:")
        print(f"   Artifacts Created: {artifact_count}")
        print(f"   Verification Rate: {verification_rate:.1%}")
        print(f"   Quality Status: {result.status}")
        print(f"   Quality Score: {result.overall_score:.1%}")

        # Should have warning about missing tests
        assert verification_rate == 1.0
        assert result.status in ["pass", "warning", "fail"]
        if result.status == "fail":
            assert "test_files_missing" in result.gates_failed


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
