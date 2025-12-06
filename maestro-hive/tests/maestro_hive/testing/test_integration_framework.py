"""
Tests for Integration Testing Framework

EPIC: MD-2509
[BLOCK-ARCH] Sub-EPIC 4: Integration Testing Framework

Tests all acceptance criteria:
- AC-1: Skip unit tests for TRUSTED blocks
- AC-2: Contract tests verify interfaces
- AC-3: Integration tests for composition
- AC-4: 90% fewer tests for composed systems
"""

import asyncio
import pytest
from datetime import datetime
from unittest.mock import MagicMock, patch
from uuid import UUID

# Import integration testing components
from maestro_hive.testing.integration import (
    TrustStatus,
    BlockTestScope,
    TestRequirements,
    TrustEvidence,
    ContractSpec,
    ContractResult,
    IntegrationResult,
    BlockTrustManager,
    ContractTester,
    IntegrationRunner,
    TestScopeDecider,
)


# =============================================================================
# Test Fixtures
# =============================================================================

@pytest.fixture
def trust_manager():
    """Create a fresh trust manager for each test."""
    return BlockTrustManager(auto_load=False)


@pytest.fixture
def contract_tester():
    """Create a fresh contract tester for each test."""
    return ContractTester()


@pytest.fixture
def integration_runner(trust_manager):
    """Create an integration runner with trust manager."""
    return IntegrationRunner(trust_manager=trust_manager)


@pytest.fixture
def scope_decider(trust_manager):
    """Create a test scope decider."""
    return TestScopeDecider(trust_manager=trust_manager)


class SampleBlock:
    """Sample block for testing."""
    name = "sample_block"

    def process(self, data: dict) -> dict:
        return {"processed": True, **data}

    def validate(self, input_data: str) -> bool:
        return len(input_data) > 0


class AuthBlock:
    """Sample auth block implementing required interface."""

    def authenticate(self, credentials: dict) -> dict:
        return {"authenticated": True, "user_id": "123"}

    def validate_token(self, token: str) -> bool:
        return len(token) > 0


# =============================================================================
# AC-1: Skip unit tests for TRUSTED blocks
# =============================================================================

class TestTrustStatus:
    """Tests for AC-1: Skip unit tests for TRUSTED blocks."""

    def test_trust_status_enum_values(self):
        """Test TrustStatus enum has correct values."""
        assert TrustStatus.TRUSTED.value == "trusted"
        assert TrustStatus.CATALOGUED.value == "catalogued"
        assert TrustStatus.NEW.value == "new"

    def test_new_block_defaults_to_new_status(self, trust_manager):
        """Test unregistered blocks have NEW status (AC-1)."""
        status = trust_manager.get_trust_status("unknown_block")
        assert status == TrustStatus.NEW

    def test_register_trusted_block(self, trust_manager):
        """Test registering a trusted block (AC-1)."""
        evidence = TrustEvidence(
            block_name="auth_service",
            verified_by="security_team",
            evidence_type="manual_review",
        )
        trust_manager.register_trusted_block("auth_service", evidence)

        status = trust_manager.get_trust_status("auth_service")
        assert status == TrustStatus.TRUSTED

    def test_register_catalogued_block(self, trust_manager):
        """Test registering a catalogued block."""
        trust_manager.register_catalogued_block("api_gateway")

        status = trust_manager.get_trust_status("api_gateway")
        assert status == TrustStatus.CATALOGUED

    def test_trusted_block_skips_unit_tests(self, trust_manager):
        """Test TRUSTED blocks skip unit tests (AC-1)."""
        evidence = TrustEvidence(block_name="db_client", verified_by="team")
        trust_manager.register_trusted_block("db_client", evidence)

        scope = trust_manager.get_test_scope("db_client")

        assert scope.run_unit_tests is False
        assert scope.run_contract_tests is True
        assert scope.run_e2e_tests is True

    def test_catalogued_block_skips_unit_tests(self, trust_manager):
        """Test CATALOGUED blocks skip unit tests (AC-1)."""
        trust_manager.register_catalogued_block("cache_service")

        scope = trust_manager.get_test_scope("cache_service")

        assert scope.run_unit_tests is False
        assert scope.run_contract_tests is True
        assert scope.run_integration_tests is True

    def test_new_block_runs_all_tests(self, trust_manager):
        """Test NEW blocks run all tests."""
        scope = trust_manager.get_test_scope("brand_new_block")

        assert scope.run_unit_tests is True
        assert scope.run_contract_tests is True
        assert scope.run_integration_tests is True
        assert scope.run_e2e_tests is True

    def test_demote_block(self, trust_manager):
        """Test demoting block trust status."""
        evidence = TrustEvidence(block_name="test_block", verified_by="team")
        trust_manager.register_trusted_block("test_block", evidence)

        # Demote: TRUSTED -> CATALOGUED
        new_status = trust_manager.demote_block("test_block")
        assert new_status == TrustStatus.CATALOGUED

        # Demote: CATALOGUED -> NEW
        new_status = trust_manager.demote_block("test_block")
        assert new_status == TrustStatus.NEW

    def test_trust_manager_stats(self, trust_manager):
        """Test trust manager statistics."""
        trust_manager.get_trust_status("block1")
        trust_manager.get_trust_status("block2")

        evidence = TrustEvidence(block_name="block3", verified_by="team")
        trust_manager.register_trusted_block("block3", evidence)
        trust_manager.get_trust_status("block3")

        stats = trust_manager.get_stats()
        assert stats["lookups"] == 3
        assert stats["trusted_hits"] == 1
        assert stats["new_hits"] == 2


class TestTestRequirements:
    """Tests for TestRequirements based on trust status."""

    def test_requirements_for_trusted(self):
        """Test requirements for TRUSTED status (AC-1)."""
        reqs = TestRequirements.for_status(TrustStatus.TRUSTED)

        assert reqs.run_unit_tests is False
        assert reqs.run_contract_tests is True
        assert reqs.run_integration_tests is False
        assert reqs.run_e2e_tests is True

    def test_requirements_for_catalogued(self):
        """Test requirements for CATALOGUED status."""
        reqs = TestRequirements.for_status(TrustStatus.CATALOGUED)

        assert reqs.run_unit_tests is False
        assert reqs.run_contract_tests is True
        assert reqs.run_integration_tests is True
        assert reqs.run_e2e_tests is True

    def test_requirements_for_new(self):
        """Test requirements for NEW status."""
        reqs = TestRequirements.for_status(TrustStatus.NEW)

        assert reqs.run_unit_tests is True
        assert reqs.run_contract_tests is True
        assert reqs.run_integration_tests is True
        assert reqs.run_e2e_tests is True


# =============================================================================
# AC-2: Contract tests verify interfaces
# =============================================================================

class TestContractTester:
    """Tests for AC-2: Contract tests verify interfaces."""

    def test_contract_spec_creation(self):
        """Test ContractSpec creation."""
        contract = ContractSpec(
            name="AuthService",
            required_methods=["authenticate", "validate_token"],
            inputs={"authenticate": "credentials: dict"},
            outputs={"authenticate": "AuthResult"},
        )

        assert contract.name == "AuthService"
        assert len(contract.required_methods) == 2

    def test_verify_contract_success(self, contract_tester):
        """Test successful contract verification (AC-2)."""
        contract = ContractSpec(
            name="AuthContract",
            required_methods=["authenticate", "validate_token"],
        )

        block = AuthBlock()
        result = contract_tester.verify_contract(block, contract)

        assert result.passed is True
        assert result.contract_name == "AuthContract"
        assert result.failed_checks == 0

    def test_verify_contract_missing_method(self, contract_tester):
        """Test contract verification with missing method (AC-2)."""
        contract = ContractSpec(
            name="TestContract",
            required_methods=["process", "nonexistent_method"],
        )

        block = SampleBlock()
        result = contract_tester.verify_contract(block, contract)

        assert result.passed is False
        assert result.failed_checks > 0
        assert any("nonexistent_method" in str(f) for f in result.failures)

    def test_verify_interface_class(self, contract_tester):
        """Test interface verification using class (AC-2)."""
        class IAuthenticator:
            def authenticate(self, credentials: dict) -> dict:
                pass

            def validate_token(self, token: str) -> bool:
                pass

        block = AuthBlock()
        result = contract_tester.verify_interface(block, IAuthenticator)

        assert result.passed is True

    def test_contract_result_pass_rate(self):
        """Test ContractResult pass rate calculation."""
        result = ContractResult(
            total_checks=10,
            passed_checks=8,
            failed_checks=2,
            passed=False,
        )

        assert result.pass_rate == 0.8

    def test_register_and_run_contracts(self, contract_tester):
        """Test registering and running multiple contracts (AC-2)."""
        contract1 = ContractSpec(name="Contract1", required_methods=["process"])
        contract2 = ContractSpec(name="Contract2", required_methods=["validate"])

        contract_tester.register_contract(contract1)
        contract_tester.register_contract(contract2)

        block = SampleBlock()
        results = contract_tester.run_contract_tests(block)

        assert len(results) == 2

    def test_contract_tester_stats(self, contract_tester):
        """Test contract tester statistics."""
        contract = ContractSpec(name="Test", required_methods=["process"])

        block = SampleBlock()
        contract_tester.verify_contract(block, contract)
        contract_tester.verify_contract(block, contract)

        stats = contract_tester.get_stats()
        assert stats["verifications"] == 2
        assert stats["passes"] == 2


# =============================================================================
# AC-3: Integration tests for composition
# =============================================================================

class TestIntegrationRunner:
    """Tests for AC-3: Integration tests for composition."""

    def test_add_block(self, integration_runner):
        """Test adding blocks for integration testing."""
        block = SampleBlock()
        integration_runner.add_block("sample", block)

        assert "sample" in integration_runner._blocks

    @pytest.mark.asyncio
    async def test_run_integration_tests_basic(self, integration_runner):
        """Test basic integration test execution (AC-3)."""
        block = SampleBlock()
        integration_runner.add_block("sample", block)

        result = await integration_runner.run_integration_tests(["sample"])

        assert isinstance(result, IntegrationResult)
        assert result.blocks_tested == ["sample"]

    @pytest.mark.asyncio
    async def test_run_integration_tests_with_test_func(self, integration_runner):
        """Test integration with custom test function (AC-3)."""
        block = SampleBlock()

        def test_block(b):
            assert b.process({"key": "value"})["processed"] is True

        integration_runner.add_block("sample", block, tests=[test_block])

        result = await integration_runner.run_integration_tests(["sample"])

        assert result.passed is True
        assert result.passed_tests >= 1

    @pytest.mark.asyncio
    async def test_composition_test(self, integration_runner):
        """Test block composition testing (AC-3)."""
        block1 = SampleBlock()
        block2 = AuthBlock()

        integration_runner.add_block("sample", block1)
        integration_runner.add_block("auth", block2)

        def composition_test(blocks):
            assert "sample" in blocks
            assert "auth" in blocks

        result = await integration_runner.test_composition(
            ["sample", "auth"],
            composition_test
        )

        assert result.passed is True

    @pytest.mark.asyncio
    async def test_skip_integration_for_trusted(self, integration_runner, trust_manager):
        """Test skipping integration tests for TRUSTED blocks (AC-3)."""
        evidence = TrustEvidence(block_name="trusted_block", verified_by="team")
        trust_manager.register_trusted_block("trusted_block", evidence)

        block = SampleBlock()
        def test_func(b):
            pass

        integration_runner.add_block("trusted_block", block, tests=[test_func])

        result = await integration_runner.run_integration_tests(["trusted_block"])

        # TRUSTED blocks skip integration tests
        assert result.skipped_tests > 0

    def test_integration_result_pass_rate(self):
        """Test IntegrationResult pass rate calculation."""
        result = IntegrationResult(
            total_tests=10,
            passed_tests=8,
            failed_tests=2,
            skipped_tests=0,
        )

        assert result.pass_rate == 0.8


# =============================================================================
# AC-4: 90% fewer tests for composed systems
# =============================================================================

class TestTestReduction:
    """Tests for AC-4: 90% fewer tests for composed systems."""

    def test_calculate_test_reduction_all_trusted(self, integration_runner, trust_manager):
        """Test 90% test reduction with all trusted blocks (AC-4)."""
        # Register multiple trusted blocks
        for i in range(5):
            evidence = TrustEvidence(block_name=f"block_{i}", verified_by="team")
            trust_manager.register_trusted_block(f"block_{i}", evidence)
            integration_runner.add_block(f"block_{i}", SampleBlock(), tests=[lambda b: None] * 10)

        reduction = integration_runner.calculate_test_reduction(
            [f"block_{i}" for i in range(5)]
        )

        assert reduction["reduction_percent"] >= 90
        assert reduction["target_met"] is True

    def test_calculate_test_reduction_mixed(self, integration_runner, trust_manager):
        """Test test reduction with mixed trust status (AC-4)."""
        # 3 trusted, 2 new
        for i in range(3):
            evidence = TrustEvidence(block_name=f"trusted_{i}", verified_by="team")
            trust_manager.register_trusted_block(f"trusted_{i}", evidence)
            integration_runner.add_block(f"trusted_{i}", SampleBlock(), tests=[lambda b: None] * 10)

        for i in range(2):
            integration_runner.add_block(f"new_{i}", SampleBlock(), tests=[lambda b: None] * 10)

        all_blocks = [f"trusted_{i}" for i in range(3)] + [f"new_{i}" for i in range(2)]
        reduction = integration_runner.calculate_test_reduction(all_blocks)

        # 30/50 tests skipped = 60% reduction
        assert reduction["reduction_percent"] >= 50

    def test_scope_decider_estimate_reduction(self, scope_decider, trust_manager):
        """Test TestScopeDecider estimation of test reduction (AC-4)."""
        # Register some trusted blocks
        for i in range(8):
            evidence = TrustEvidence(block_name=f"block_{i}", verified_by="team")
            trust_manager.register_trusted_block(f"block_{i}", evidence)

        # Add 2 new blocks
        blocks = [f"block_{i}" for i in range(8)] + ["new_1", "new_2"]

        estimate = scope_decider.estimate_test_reduction(blocks, tests_per_block=10)

        # 8/10 blocks are trusted -> high reduction
        assert estimate["reduction_percent"] >= 60

    def test_filter_for_unit_tests(self, scope_decider, trust_manager):
        """Test filtering blocks that need unit testing (AC-4)."""
        evidence = TrustEvidence(block_name="trusted", verified_by="team")
        trust_manager.register_trusted_block("trusted", evidence)
        trust_manager.register_catalogued_block("catalogued")

        blocks = ["trusted", "catalogued", "new"]
        need_unit_tests = scope_decider.filter_for_unit_tests(blocks)

        # Only NEW blocks need unit tests
        assert need_unit_tests == ["new"]

    def test_test_matrix_calculation(self, scope_decider, trust_manager):
        """Test calculating full test matrix (AC-4)."""
        evidence = TrustEvidence(block_name="trusted", verified_by="team")
        trust_manager.register_trusted_block("trusted", evidence)
        trust_manager.register_catalogued_block("catalogued")

        matrix = scope_decider.calculate_test_matrix(["trusted", "catalogued", "new"])

        assert matrix["summary"]["trusted"] == 1
        assert matrix["summary"]["catalogued"] == 1
        assert matrix["summary"]["new"] == 1
        assert matrix["summary"]["unit_tests_to_run"] == 1  # Only NEW


# =============================================================================
# Data Model Tests
# =============================================================================

class TestDataModels:
    """Tests for data model classes."""

    def test_trust_evidence_to_dict(self):
        """Test TrustEvidence serialization."""
        evidence = TrustEvidence(
            block_name="test_block",
            verified_by="team",
            evidence_type="manual_review",
        )
        data = evidence.to_dict()

        assert data["block_name"] == "test_block"
        assert data["verified_by"] == "team"
        assert "id" in data

    def test_block_test_scope_to_dict(self):
        """Test BlockTestScope serialization."""
        scope = BlockTestScope(
            block_name="test",
            trust_status=TrustStatus.TRUSTED,
            requirements=TestRequirements.for_status(TrustStatus.TRUSTED),
        )
        data = scope.to_dict()

        assert data["block_name"] == "test"
        assert data["trust_status"] == "trusted"
        assert data["run_unit_tests"] is False

    def test_contract_result_to_dict(self):
        """Test ContractResult serialization."""
        result = ContractResult(
            contract_name="TestContract",
            block_name="TestBlock",
            passed=True,
            total_checks=5,
            passed_checks=5,
        )
        data = result.to_dict()

        assert data["contract_name"] == "TestContract"
        assert data["passed"] is True
        assert data["pass_rate"] == 1.0

    def test_integration_result_to_dict(self):
        """Test IntegrationResult serialization."""
        result = IntegrationResult(
            blocks_tested=["a", "b"],
            passed=True,
            total_tests=10,
            passed_tests=9,
            failed_tests=1,
            test_reduction_percent=75.0,
        )
        data = result.to_dict()

        assert data["blocks_tested"] == ["a", "b"]
        assert data["test_reduction_percent"] == 75.0


# =============================================================================
# Integration Tests
# =============================================================================

class TestFullWorkflow:
    """Integration tests for full testing workflow."""

    @pytest.mark.asyncio
    async def test_full_trust_based_testing_workflow(self, trust_manager):
        """Test complete trust-based testing workflow."""
        # 1. Register blocks with different trust statuses
        evidence = TrustEvidence(block_name="auth", verified_by="security")
        trust_manager.register_trusted_block("auth", evidence)
        trust_manager.register_catalogued_block("api")
        # "user" is NEW by default

        # 2. Create components
        contract_tester = ContractTester()
        runner = IntegrationRunner(trust_manager=trust_manager)
        decider = TestScopeDecider(trust_manager=trust_manager)

        # 3. Register contracts
        auth_contract = ContractSpec(
            name="AuthContract",
            required_methods=["authenticate", "validate_token"],
        )
        contract_tester.register_contract(auth_contract)

        # 4. Add blocks to runner with tests
        runner.add_block("auth", AuthBlock(), tests=[lambda b: None] * 10)
        runner.add_block("api", SampleBlock(), tests=[lambda b: None] * 10)
        runner.add_block("user", SampleBlock(), tests=[lambda b: None] * 10)

        # 5. Decide test scope
        matrix = decider.calculate_test_matrix(["auth", "api", "user"])

        assert matrix["blocks"]["auth"]["unit_tests"] is False
        assert matrix["blocks"]["user"]["unit_tests"] is True

        # 6. Run contract tests (AC-2)
        contract_result = contract_tester.verify_contract(AuthBlock(), auth_contract)
        assert contract_result.passed is True

        # 7. Run integration tests (AC-3)
        int_result = await runner.run_integration_tests()
        assert isinstance(int_result, IntegrationResult)

        # 8. Verify test reduction (AC-4)
        reduction = runner.calculate_test_reduction(["auth", "api", "user"])
        assert reduction["would_skip"] > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
