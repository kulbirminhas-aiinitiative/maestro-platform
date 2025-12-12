"""
Tests for Persona University Module (MD-3127)

Tests all 10 Acceptance Criteria:
- AC-1: Curriculum YAML loading
- AC-2: Credential-gated hiring
- AC-3: Exam in simulator
- AC-4: Grading metrics
- AC-5: VC issuance on pass
- AC-6: Ed25519 signature
- AC-7: Reputation update
- AC-8: Violation = failure
- AC-9: Credential persistence
- AC-10: Frontend data (exam history)
"""

import pytest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch
import tempfile
import yaml

# Import modules under test
from maestro_hive.university.credential_store import (
    CredentialStore,
    CredentialStatus,
    VerifiableCredential,
)
from maestro_hive.university.user_simulator import (
    UserSimulatorAgent,
    ExamScenario,
    ScenarioStep,
)
from maestro_hive.university.exam_simulator import (
    ExamSimulator,
    ExamResult,
    ExamGrade,
    ExamMetrics,
)
from maestro_hive.university.persona_university_service import (
    PersonaUniversityService,
    Curriculum,
    CurriculumModule,
)


# ============================================================
# AC-1: Curriculum YAML Loading
# ============================================================

class TestAC1CurriculumLoading:
    """AC-1: A curriculum can be defined in YAML and loaded."""

    def test_curriculum_from_yaml(self, tmp_path):
        """Test loading curriculum from YAML file."""
        yaml_content = """
curriculum:
  id: test_curriculum
  name: "Test Curriculum"
  type: "major"
  prerequisites: []
  modules:
    - id: module_1
      name: "Module 1"
      skills:
        - skill_a
        - skill_b
      exam:
        type: code_completion
        time_limit_minutes: 30
        pass_threshold: 0.8
  certification:
    name: "Test_Credential"
    validity_days: 365
    revocable: true
"""
        yaml_path = tmp_path / "test_curriculum.yaml"
        yaml_path.write_text(yaml_content)

        curriculum = Curriculum.from_yaml(str(yaml_path))

        assert curriculum.curriculum_id == "test_curriculum"
        assert curriculum.name == "Test Curriculum"
        assert curriculum.curriculum_type == "major"
        assert len(curriculum.modules) == 1
        assert curriculum.modules[0].skills == ["skill_a", "skill_b"]
        assert curriculum.certification_name == "Test_Credential"

    def test_curriculum_to_dict(self):
        """Test curriculum serialization."""
        curriculum = Curriculum(
            curriculum_id="test",
            name="Test",
            curriculum_type="core",
            prerequisites=["prereq_1"],
            modules=[
                CurriculumModule(
                    module_id="m1",
                    name="Module 1",
                    skills=["s1"],
                    exam_type="bug_fix",
                    time_limit_minutes=45,
                    pass_threshold=0.85,
                )
            ],
            certification_name="Test_Cert",
            validity_days=180,
        )

        data = curriculum.to_dict()
        assert data["id"] == "test"
        assert data["prerequisites"] == ["prereq_1"]
        assert len(data["modules"]) == 1
        assert data["modules"][0]["exam"]["pass_threshold"] == 0.85

    def test_service_loads_curricula_from_directory(self, tmp_path):
        """Test that service loads all curricula from directory."""
        # Create two curriculum files
        for i in range(2):
            yaml_content = f"""
curriculum:
  id: curriculum_{i}
  name: "Curriculum {i}"
  type: major
  prerequisites: []
  modules: []
  certification:
    name: "Cert_{i}"
"""
            (tmp_path / f"curriculum_{i}.yaml").write_text(yaml_content)

        service = PersonaUniversityService(curriculum_dir=str(tmp_path))

        curricula = service.list_curricula()
        assert len(curricula) == 2


# ============================================================
# AC-2: Credential-Gated Hiring
# ============================================================

class TestAC2HiringEligibility:
    """AC-2: A Fresh agent cannot be hired for Senior role without credentials."""

    def test_fresh_agent_not_eligible_without_credentials(self):
        """Fresh agent should not be eligible for senior role."""
        service = PersonaUniversityService()

        result = service.check_hiring_eligibility(
            agent_id="fresh_agent",
            required_role="senior_developer",
            required_credentials=["Python_Expert", "Security_Certified"],
        )

        assert result["eligible"] is False
        assert "Python_Expert" in result["missing_credentials"]
        assert "Security_Certified" in result["missing_credentials"]

    def test_credential_store_check_hiring(self):
        """Test CredentialStore hiring check."""
        store = CredentialStore()

        # Issue a credential
        store.issue_credential(
            agent_id="agent_1",
            credential_type="Python_Novice",
        )

        # Check eligibility
        assert store.check_hiring_eligibility("agent_1", "Python_Novice") is True
        assert store.check_hiring_eligibility("agent_1", "Python_Expert") is False

    def test_agent_with_credentials_is_eligible(self):
        """Agent with required credentials should be eligible."""
        store = CredentialStore()

        # Issue required credentials
        store.issue_credential("agent_1", "Python_Expert")
        store.issue_credential("agent_1", "Security_Certified")

        # Check both credentials exist
        assert store.has_credential("agent_1", "Python_Expert") is True
        assert store.has_credential("agent_1", "Security_Certified") is True


# ============================================================
# AC-3: Exam in Simulator
# ============================================================

class TestAC3ExamSimulator:
    """AC-3: An agent can take a Python 101 exam in the simulator."""

    def test_user_simulator_basic_flow(self):
        """Test basic user simulator flow."""
        scenario_data = {
            "scenario": {
                "id": "test_exam",
                "name": "Test Exam",
                "description": "A test exam",
                "difficulty": "easy",
                "max_time_minutes": 30,
                "passing_score": 0.8,
                "steps": [
                    {
                        "user_input": "Complete this function",
                        "expected_behavior": "Write correct code",
                        "success_criteria": ["Compiles", "Handles edge cases"],
                    }
                ]
            }
        }

        simulator = UserSimulatorAgent(scenario_data=scenario_data)

        prompt = simulator.start_exam()
        assert prompt == "Complete this function"

        result = simulator.evaluate_response("def func(): return True", score=0.9)
        assert result["passed"] is True
        assert result["score"] == 0.9

    def test_exam_simulator_runs_exam(self):
        """Test full exam execution."""
        scenario = ExamScenario(
            scenario_id="python_test",
            name="Python Test",
            description="Basic Python test",
            difficulty="easy",
            max_total_time_minutes=30,
            passing_score=0.8,
            steps=[
                ScenarioStep(
                    step_id=0,
                    user_input="Write a hello world function",
                    expected_behavior="Print hello world",
                    success_criteria=["Function defined", "Prints output"],
                )
            ]
        )

        simulator = ExamSimulator()

        # Mock agent that always responds correctly
        def agent_callback(prompt: str) -> str:
            return "def hello(): print('hello world')"

        result = simulator.run_exam(
            agent_id="test_agent",
            scenario=scenario,
            agent_response_callback=agent_callback,
        )

        assert result.agent_id == "test_agent"
        assert result.scenario_id == "python_test"
        assert result.metrics is not None


# ============================================================
# AC-4: Grading Metrics
# ============================================================

class TestAC4GradingMetrics:
    """AC-4: Exam results include Accuracy, Efficiency, and Safety scores."""

    def test_exam_metrics_structure(self):
        """Test ExamMetrics has all required fields."""
        metrics = ExamMetrics(
            accuracy=0.95,
            efficiency=0.85,
            safety=1.0,
            creativity=0.7,
        )

        assert metrics.accuracy == 0.95
        assert metrics.efficiency == 0.85
        assert metrics.safety == 1.0
        assert metrics.creativity == 0.7

    def test_weighted_score_calculation(self):
        """Test weighted score calculation."""
        metrics = ExamMetrics(
            accuracy=1.0,
            efficiency=1.0,
            safety=1.0,
            creativity=1.0,
        )

        # Perfect scores should give approximately 1.0 (float precision)
        assert metrics.weighted_score() == pytest.approx(1.0)

    def test_grade_determination(self):
        """Test grade determination from scores."""
        simulator = ExamSimulator()

        assert simulator._determine_grade(0.99, 0) == ExamGrade.S_TIER
        assert simulator._determine_grade(0.95, 0) == ExamGrade.A_TIER
        assert simulator._determine_grade(0.85, 0) == ExamGrade.B_TIER
        assert simulator._determine_grade(0.70, 0) == ExamGrade.C_TIER
        assert simulator._determine_grade(0.50, 0) == ExamGrade.FAILED

    def test_violation_causes_failure(self):
        """Test that any violation causes automatic failure."""
        simulator = ExamSimulator()

        # Even with perfect score, violation = failure
        assert simulator._determine_grade(1.0, 1) == ExamGrade.FAILED


# ============================================================
# AC-5: VC Issuance on Pass
# ============================================================

class TestAC5CredentialIssuance:
    """AC-5: Upon passing (>80%), the agent receives a VC."""

    def test_credential_issued_on_pass(self):
        """Test that credential is issued when agent passes."""
        store = CredentialStore()

        credential = store.issue_credential(
            agent_id="passing_agent",
            credential_type="Python_Novice",
            exam_id="exam_123",
            exam_score=0.85,
        )

        assert credential is not None
        assert credential.agent_id == "passing_agent"
        assert credential.credential_type == "Python_Novice"
        assert credential.exam_score == 0.85

    def test_credential_has_expiry(self):
        """Test that credentials have expiry date."""
        store = CredentialStore(default_validity_days=365)

        credential = store.issue_credential(
            agent_id="agent_1",
            credential_type="Test_Cert",
        )

        assert credential.expires_at is not None
        assert credential.expires_at > datetime.utcnow()

    def test_credential_is_valid_when_issued(self):
        """Test newly issued credential is valid."""
        store = CredentialStore()

        credential = store.issue_credential(
            agent_id="agent_1",
            credential_type="Test_Cert",
        )

        assert credential.is_valid() is True
        assert store.verify_credential(credential) is True


# ============================================================
# AC-6: Ed25519 Signature
# ============================================================

class TestAC6CryptographicSigning:
    """AC-6: Credentials are signed using IdentityManager Ed25519 keys."""

    def test_credential_has_signature(self):
        """Test that issued credentials have signatures."""
        store = CredentialStore()

        credential = store.issue_credential(
            agent_id="agent_1",
            credential_type="Test_Cert",
        )

        assert credential.signature != ""

    def test_credential_signed_with_identity_manager(self):
        """Test credential signing with mock IdentityManager."""
        mock_identity = MagicMock()
        mock_identity.sign_action.return_value = MagicMock(signature="mock_ed25519_sig")

        store = CredentialStore(identity_manager=mock_identity)

        credential = store.issue_credential(
            agent_id="agent_1",
            credential_type="Test_Cert",
        )

        mock_identity.sign_action.assert_called_once()
        assert credential.signature == "mock_ed25519_sig"


# ============================================================
# AC-7: Reputation Update
# ============================================================

class TestAC7ReputationUpdate:
    """AC-7: Exam pass/fail events update agent reputation (+10/-5)."""

    def test_exam_updates_reputation_on_pass(self):
        """Test reputation update on exam pass."""
        mock_reputation = MagicMock()

        simulator = ExamSimulator(reputation_engine=mock_reputation)

        # Create a passing result
        result = ExamResult(
            exam_id="test",
            agent_id="agent_1",
            scenario_id="test_scenario",
            started_at=datetime.utcnow(),
            completed_at=datetime.utcnow(),
            metrics=ExamMetrics(accuracy=0.9, efficiency=0.9, safety=1.0, creativity=0.5),
            final_score=0.9,
            grade=ExamGrade.A_TIER,
            passed=True,
        )

        simulator._update_reputation("agent_1", result)

        # Should call record_event for passing
        assert mock_reputation.record_event.called

    def test_exam_updates_reputation_on_fail(self):
        """Test reputation update on exam failure."""
        mock_reputation = MagicMock()

        simulator = ExamSimulator(reputation_engine=mock_reputation)

        # Create a failing result
        result = ExamResult(
            exam_id="test",
            agent_id="agent_1",
            scenario_id="test_scenario",
            started_at=datetime.utcnow(),
            completed_at=datetime.utcnow(),
            metrics=ExamMetrics(accuracy=0.5, efficiency=0.5, safety=1.0, creativity=0.5),
            final_score=0.5,
            grade=ExamGrade.FAILED,
            passed=False,
        )

        simulator._update_reputation("agent_1", result)

        # Should call record_event for failing
        assert mock_reputation.record_event.called


# ============================================================
# AC-8: Governance Violations
# ============================================================

class TestAC8GovernanceViolations:
    """AC-8: Governance violations during exam result in instant failure."""

    def test_prohibited_pattern_causes_violation(self):
        """Test that prohibited patterns cause violations."""
        mock_enforcer = MagicMock()
        simulator = ExamSimulator(enforcer=mock_enforcer)
        simulator._exam_in_progress = True

        from maestro_hive.university.exam_simulator import SecurityError
        with pytest.raises(SecurityError):
            simulator._check_response_compliance("agent_1", "sudo rm -rf /")

        assert simulator._governance_violations > 0

    def test_violation_count_increases(self):
        """Test violation count tracking."""
        simulator = ExamSimulator()
        simulator._exam_in_progress = True

        simulator.record_violation("test_violation")
        assert simulator._governance_violations == 1

        simulator.record_violation("another_violation")
        assert simulator._governance_violations == 2

    def test_sql_injection_detected(self):
        """Test SQL injection patterns are detected."""
        mock_enforcer = MagicMock()
        simulator = ExamSimulator(enforcer=mock_enforcer)
        simulator._exam_in_progress = True

        from maestro_hive.university.exam_simulator import SecurityError
        with pytest.raises(SecurityError):
            simulator._check_response_compliance("agent_1", "DROP TABLE users;")

    def test_code_injection_detected(self):
        """Test code injection patterns are detected."""
        mock_enforcer = MagicMock()
        simulator = ExamSimulator(enforcer=mock_enforcer)
        simulator._exam_in_progress = True

        from maestro_hive.university.exam_simulator import SecurityError
        with pytest.raises(SecurityError):
            simulator._check_response_compliance("agent_1", "eval('malicious')")


# ============================================================
# AC-9: Credential Persistence
# ============================================================

class TestAC9Persistence:
    """AC-9: Credentials survive system restart (GovernancePersistence)."""

    def test_credential_saved_to_memory(self):
        """Test credentials are saved to memory store."""
        store = CredentialStore()

        credential = store.issue_credential(
            agent_id="agent_1",
            credential_type="Test_Cert",
        )

        # Should be retrievable
        retrieved = store.get_credential(credential.credential_id)
        assert retrieved is not None
        assert retrieved.credential_type == "Test_Cert"

    def test_credential_serialization(self):
        """Test credential can be serialized and deserialized."""
        original = VerifiableCredential(
            credential_id="vc_test123",
            agent_id="agent_1",
            credential_type="Python_Novice",
            exam_id="exam_456",
            exam_score=0.85,
        )

        # Serialize
        data = original.to_dict()

        # Deserialize
        restored = VerifiableCredential.from_dict(data)

        assert restored.credential_id == original.credential_id
        assert restored.agent_id == original.agent_id
        assert restored.credential_type == original.credential_type
        assert restored.exam_score == original.exam_score

    def test_revocation_registry_persists(self):
        """Test revocation registry is maintained."""
        store = CredentialStore()

        credential = store.issue_credential(
            agent_id="agent_1",
            credential_type="Test_Cert",
        )

        # Revoke
        store.revoke_credential(credential.credential_id, "testing")

        # Verify revoked
        assert credential.credential_id in store._revocation_registry
        assert store.verify_credential(credential) is False


# ============================================================
# AC-10: Frontend Data
# ============================================================

class TestAC10FrontendData:
    """AC-10: Frontend displays agent credentials and exam history."""

    def test_exam_history_retrieval(self):
        """Test exam history retrieval for frontend."""
        store = CredentialStore()

        # Issue multiple credentials
        store.issue_credential(
            agent_id="agent_1",
            credential_type="Python_Novice",
            exam_id="exam_1",
            exam_score=0.85,
        )
        store.issue_credential(
            agent_id="agent_1",
            credential_type="Security_Basics",
            exam_id="exam_2",
            exam_score=0.90,
        )

        # Get all credentials for agent
        credentials = store.get_agent_credentials("agent_1")

        assert len(credentials) == 2

    def test_service_exam_history(self):
        """Test PersonaUniversityService exam history endpoint."""
        service = PersonaUniversityService()

        # Issue credential through store
        service._credential_store.issue_credential(
            agent_id="agent_1",
            credential_type="Test_Cert",
            exam_id="exam_123",
            exam_score=0.88,
        )

        history = service.get_exam_history("agent_1")

        assert len(history) == 1
        assert history[0]["credential_type"] == "Test_Cert"
        assert history[0]["exam_score"] == 0.88
        assert "issued_at" in history[0]
        assert history[0]["is_valid"] is True


# ============================================================
# Integration Tests
# ============================================================

class TestIntegration:
    """Integration tests combining multiple ACs."""

    def test_full_exam_workflow(self):
        """Test complete exam workflow from scheduling to credential."""
        # Create service
        service = PersonaUniversityService()

        # Create a simple scenario
        scenario = ExamScenario(
            scenario_id="integration_test",
            name="Integration Test",
            description="Full workflow test",
            difficulty="easy",
            max_total_time_minutes=5,
            passing_score=0.6,
            steps=[
                ScenarioStep(
                    step_id=0,
                    user_input="Write hello world",
                    expected_behavior="Print hello",
                    success_criteria=["Function works"],
                )
            ]
        )

        # Run exam
        result = service.run_exam(
            agent_id="test_agent",
            scenario=scenario,
            agent_response_callback=lambda p: "def hello(): print('hello world')",
        )

        assert result.agent_id == "test_agent"
        assert result.scenario_id == "integration_test"

    def test_credential_gated_exam(self):
        """Test that prerequisites are checked before exam."""
        service = PersonaUniversityService()

        # Create curriculum with prerequisites
        curriculum = Curriculum(
            curriculum_id="advanced",
            name="Advanced Course",
            curriculum_type="major",
            prerequisites=["Basic_Cert"],
            modules=[
                CurriculumModule(
                    module_id="adv_1",
                    name="Advanced Module",
                    skills=["advanced_skill"],
                    exam_type="code_completion",
                )
            ],
            certification_name="Advanced_Cert",
        )
        service._curricula["advanced"] = curriculum

        # Try to schedule without prerequisite
        scenario = service.schedule_exam(
            agent_id="new_agent",
            curriculum_id="advanced",
        )

        # Should fail due to missing prerequisite
        assert scenario is None


# ============================================================
# Edge Cases
# ============================================================

class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_empty_scenario_steps(self):
        """Test handling of empty scenario."""
        scenario_data = {
            "scenario": {
                "id": "empty",
                "name": "Empty",
                "description": "",
                "difficulty": "easy",
                "max_time_minutes": 1,
                "steps": []
            }
        }

        simulator = UserSimulatorAgent(scenario_data=scenario_data)
        prompt = simulator.start_exam()

        assert prompt == "[EXAM COMPLETE]"

    def test_expired_credential_not_valid(self):
        """Test that expired credentials are not valid."""
        store = CredentialStore()

        # Create credential with past expiry
        credential = VerifiableCredential(
            credential_id="old_cred",
            agent_id="agent_1",
            credential_type="Expired_Cert",
            expires_at=datetime.utcnow() - timedelta(days=1),
        )
        store._memory_store[credential.credential_id] = credential

        assert store.verify_credential(credential) is False

    def test_revoked_credential_not_valid(self):
        """Test that revoked credentials are not valid."""
        store = CredentialStore()

        credential = store.issue_credential(
            agent_id="agent_1",
            credential_type="Test_Cert",
        )

        # Revoke it
        store.revoke_credential(credential.credential_id, "testing")

        # Should no longer be valid
        assert store.verify_credential(store.get_credential(credential.credential_id)) is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
