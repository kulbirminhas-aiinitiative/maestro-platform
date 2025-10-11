#!/usr/bin/env python3
"""
Comprehensive Test Suite for Contract System (Week 3-4)

Tests all contract components:
- Contract requirements (7 types: BUILD_SUCCESS, TEST_COVERAGE, PRD_TRACEABILITY,
  NO_STUBS, DEPLOYMENT_READY, QUALITY_SLO, FUNCTIONAL)
- Contract validation and enforcement
- Contract registry
- Quality Fabric integration

Test Coverage Target: 85%+
"""

import pytest
import asyncio
import json
from pathlib import Path
from typing import Dict, Any
import tempfile
import shutil
from datetime import datetime

# Import modules under test
from output_contracts import (
    ContractRequirementType,
    ContractSeverity,
    ContractRequirement,
    OutputContract,
    ContractViolation,
    ContractValidationResult,
    ContractValidator,
    ContractRegistry,
    QualityFabricIntegration,
    create_implementation_contract,
    create_deployment_contract,
    create_testing_contract,
    validate_workflow_contract
)


# ===== TEST FIXTURES =====

@pytest.fixture
def temp_workflow_dir():
    """Create temporary workflow directory for testing"""
    temp_dir = Path(tempfile.mkdtemp())
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def sample_validation_report_passing():
    """Sample validation report that passes all checks"""
    return {
        "workflow_id": "test-workflow-001",
        "overall_score": 0.85,
        "can_build": True,
        "final_status": "ready_to_deploy",
        "weighted_scores": {
            "builds_successfully": 1.0,
            "functionality": 0.9,
            "features_implemented": 0.8,
            "structure": 0.8
        },
        "build_validation": {
            "results": [
                {
                    "check": "backend_build_success",
                    "passed": True,
                    "message": "Backend builds successfully"
                },
                {
                    "check": "frontend_build_success",
                    "passed": True,
                    "message": "Frontend builds successfully"
                },
                {
                    "check": "stub_implementation_detection",
                    "passed": True,
                    "message": "Low stub rate: 1/50 files (2%)",
                    "evidence": []
                }
            ]
        },
        "blocking_issues": []
    }


@pytest.fixture
def sample_validation_report_failing():
    """Sample validation report that fails critical checks"""
    return {
        "workflow_id": "test-workflow-002",
        "overall_score": 0.45,
        "can_build": False,
        "final_status": "critical_failures",
        "weighted_scores": {
            "builds_successfully": 0.0,
            "functionality": 0.4,
            "features_implemented": 0.3,
            "structure": 0.7
        },
        "build_validation": {
            "results": [
                {
                    "check": "backend_build_success",
                    "passed": False,
                    "message": "Backend build failed: TypeScript compilation errors",
                    "evidence": ["Error TS2304: Cannot find name 'Express'"]
                },
                {
                    "check": "frontend_build_success",
                    "passed": False,
                    "message": "Frontend build failed: Vite build errors",
                    "evidence": ["Error: Module not found: '@/components/App'"]
                },
                {
                    "check": "stub_implementation_detection",
                    "passed": False,
                    "message": "High stub rate: 25/50 files (50%)",
                    "evidence": [
                        "backend/src/routes/api.ts: 501 status code",
                        "backend/src/controllers/user.ts: Not implemented string"
                    ]
                }
            ]
        },
        "blocking_issues": [
            "Backend build failed",
            "Frontend build failed",
            "High stub implementation rate"
        ]
    }


# ===== CONTRACT REQUIREMENT TESTS =====

class TestContractRequirement:
    """Test contract requirement creation and validation"""

    def test_create_build_success_requirement(self):
        """Test creating BUILD_SUCCESS requirement"""
        req = ContractRequirement(
            requirement_id="test_build",
            requirement_type=ContractRequirementType.BUILD_SUCCESS,
            severity=ContractSeverity.BLOCKING,
            description="Must build successfully",
            validation_criteria={"npm_build": True}
        )

        assert req.requirement_id == "test_build"
        assert req.requirement_type == ContractRequirementType.BUILD_SUCCESS
        assert req.severity == ContractSeverity.BLOCKING
        assert req.validation_criteria["npm_build"] == True

    def test_requirement_serialization(self):
        """Test requirement can be serialized to dict"""
        req = ContractRequirement(
            requirement_id="test_req",
            requirement_type=ContractRequirementType.TEST_COVERAGE,
            severity=ContractSeverity.WARNING,
            description="Test coverage >= 70%",
            validation_criteria={"min_coverage": 0.7},
            min_threshold=0.7
        )

        req_dict = req.to_dict()

        assert req_dict["requirement_id"] == "test_req"
        assert req_dict["requirement_type"] == "test_coverage"
        assert req_dict["severity"] == "warning"
        assert req_dict["min_threshold"] == 0.7

    def test_all_requirement_types_exist(self):
        """Test all 7 requirement types are defined"""
        types = [
            ContractRequirementType.BUILD_SUCCESS,
            ContractRequirementType.TEST_COVERAGE,
            ContractRequirementType.PRD_TRACEABILITY,
            ContractRequirementType.NO_STUBS,
            ContractRequirementType.DEPLOYMENT_READY,
            ContractRequirementType.QUALITY_SLO,
            ContractRequirementType.FUNCTIONAL
        ]

        assert len(types) == 7
        # All should have unique values
        values = [t.value for t in types]
        assert len(set(values)) == 7


# ===== OUTPUT CONTRACT TESTS =====

class TestOutputContract:
    """Test output contract creation and structure"""

    def test_create_basic_contract(self):
        """Test creating a basic output contract"""
        contract = OutputContract(
            contract_id="test_contract",
            phase="testing",
            produces=["test_results", "coverage_reports"],
            requirements=[]
        )

        assert contract.contract_id == "test_contract"
        assert contract.phase == "testing"
        assert "test_results" in contract.produces
        assert len(contract.requirements) == 0

    def test_contract_with_requirements(self):
        """Test contract with multiple requirements"""
        req1 = ContractRequirement(
            requirement_id="req1",
            requirement_type=ContractRequirementType.BUILD_SUCCESS,
            severity=ContractSeverity.BLOCKING,
            description="Must build",
            validation_criteria={}
        )

        req2 = ContractRequirement(
            requirement_id="req2",
            requirement_type=ContractRequirementType.NO_STUBS,
            severity=ContractSeverity.WARNING,
            description="No stubs",
            validation_criteria={}
        )

        contract = OutputContract(
            contract_id="test",
            phase="implementation",
            produces=["code"],
            requirements=[req1, req2]
        )

        assert len(contract.requirements) == 2
        assert contract.requirements[0].requirement_id == "req1"
        assert contract.requirements[1].requirement_id == "req2"

    def test_contract_serialization(self):
        """Test contract can be serialized to dict"""
        contract = OutputContract(
            contract_id="test",
            phase="implementation",
            produces=["code"],
            slo_thresholds={"build_success": 1.0}
        )

        contract_dict = contract.to_dict()

        assert contract_dict["contract_id"] == "test"
        assert contract_dict["phase"] == "implementation"
        assert "created_at" in contract_dict
        assert contract_dict["slo_thresholds"]["build_success"] == 1.0


# ===== PREDEFINED CONTRACT TESTS =====

class TestPredefinedContracts:
    """Test pre-defined contracts (implementation, deployment, testing)"""

    def test_implementation_contract_structure(self):
        """Test implementation contract has all required elements"""
        contract = create_implementation_contract()

        assert contract.contract_id == "implementation_v1"
        assert contract.phase == "implementation"
        # Has 6 requirements (2 BUILD_SUCCESS for backend/frontend + 4 others)
        assert len(contract.requirements) >= 5

        # Check critical requirements
        req_types = [r.requirement_type for r in contract.requirements]
        assert ContractRequirementType.BUILD_SUCCESS in req_types
        assert ContractRequirementType.NO_STUBS in req_types
        assert ContractRequirementType.FUNCTIONAL in req_types

    def test_implementation_contract_addresses_batch5(self):
        """Test implementation contract addresses Batch 5 issues"""
        contract = create_implementation_contract()

        # Should have metadata about Batch 5 fix
        assert contract.metadata.get("batch_5_fix") == True
        assert "Validation passed but builds failed" in contract.metadata.get("addresses", "")

        # Should require build success (critical Batch 5 fix)
        build_reqs = [r for r in contract.requirements
                      if r.requirement_type == ContractRequirementType.BUILD_SUCCESS]
        assert len(build_reqs) >= 2  # Backend and frontend
        assert all(r.severity == ContractSeverity.BLOCKING for r in build_reqs)

    def test_deployment_contract_structure(self):
        """Test deployment contract has deployment-specific requirements"""
        contract = create_deployment_contract()

        assert contract.contract_id == "deployment_v1"
        assert contract.phase == "deployment"

        # Should have deployment ready requirement
        req_types = [r.requirement_type for r in contract.requirements]
        assert ContractRequirementType.DEPLOYMENT_READY in req_types

    def test_testing_contract_structure(self):
        """Test testing contract has test-specific requirements"""
        contract = create_testing_contract()

        assert contract.contract_id == "testing_v1"
        assert contract.phase == "testing"

        # Should have test coverage requirement
        req_types = [r.requirement_type for r in contract.requirements]
        assert ContractRequirementType.TEST_COVERAGE in req_types


# ===== CONTRACT VALIDATOR TESTS =====

class TestContractValidator:
    """Test contract validation logic"""

    @pytest.mark.asyncio
    async def test_validate_passing_contract(
        self,
        temp_workflow_dir,
        sample_validation_report_passing
    ):
        """Test validation of contract that passes all requirements"""
        contract = create_implementation_contract()
        validator = ContractValidator()

        result = await validator.validate_contract(
            contract,
            temp_workflow_dir,
            sample_validation_report_passing
        )

        assert result.passed == True
        assert len(result.blocking_violations) == 0
        assert result.requirements_met == result.requirements_total

    @pytest.mark.asyncio
    async def test_validate_failing_contract(
        self,
        temp_workflow_dir,
        sample_validation_report_failing
    ):
        """Test validation of contract that fails requirements"""
        contract = create_implementation_contract()
        validator = ContractValidator()

        result = await validator.validate_contract(
            contract,
            temp_workflow_dir,
            sample_validation_report_failing
        )

        assert result.passed == False
        assert len(result.blocking_violations) > 0
        assert result.requirements_met < result.requirements_total

    @pytest.mark.asyncio
    async def test_build_success_violation(
        self,
        temp_workflow_dir,
        sample_validation_report_failing
    ):
        """Test BUILD_SUCCESS requirement violation"""
        req = ContractRequirement(
            requirement_id="test_build",
            requirement_type=ContractRequirementType.BUILD_SUCCESS,
            severity=ContractSeverity.BLOCKING,
            description="Must build",
            validation_criteria={}
        )

        contract = OutputContract(
            contract_id="test",
            phase="implementation",
            produces=[],
            requirements=[req]
        )

        validator = ContractValidator()
        result = await validator.validate_contract(
            contract,
            temp_workflow_dir,
            sample_validation_report_failing
        )

        assert not result.passed
        assert len(result.blocking_violations) == 1
        assert result.blocking_violations[0].requirement_type == ContractRequirementType.BUILD_SUCCESS

    @pytest.mark.asyncio
    async def test_no_stubs_violation(self, temp_workflow_dir):
        """Test NO_STUBS requirement violation"""
        req = ContractRequirement(
            requirement_id="no_stubs",
            requirement_type=ContractRequirementType.NO_STUBS,
            severity=ContractSeverity.BLOCKING,
            description="No stubs allowed",
            validation_criteria={},
            max_threshold=0.05
        )

        contract = OutputContract(
            contract_id="test",
            phase="implementation",
            produces=[],
            requirements=[req]
        )

        # Report with high stub rate
        report = {
            "workflow_id": "test",
            "can_build": True,
            "build_validation": {
                "results": [
                    {
                        "check": "stub_implementation_detection",
                        "passed": False,
                        "message": "High stub rate: 25/50 files (50%)",
                        "evidence": ["backend/routes/api.ts: 501 status code"]
                    }
                ]
            }
        }

        validator = ContractValidator()
        result = await validator.validate_contract(
            contract,
            temp_workflow_dir,
            report
        )

        assert not result.passed
        assert any(v.requirement_type == ContractRequirementType.NO_STUBS
                   for v in result.blocking_violations)

    @pytest.mark.asyncio
    async def test_quality_slo_violation(self, temp_workflow_dir):
        """Test QUALITY_SLO requirement violation"""
        req = ContractRequirement(
            requirement_id="quality",
            requirement_type=ContractRequirementType.QUALITY_SLO,
            severity=ContractSeverity.WARNING,
            description="Quality >= 80%",
            validation_criteria={},
            min_threshold=0.8
        )

        contract = OutputContract(
            contract_id="test",
            phase="implementation",
            produces=[],
            requirements=[req]
        )

        # Report with low quality score
        report = {
            "workflow_id": "test",
            "overall_score": 0.65,  # Below 0.8 threshold
            "can_build": True
        }

        validator = ContractValidator()
        result = await validator.validate_contract(
            contract,
            temp_workflow_dir,
            report
        )

        # Should have warning violation
        assert len(result.warning_violations) > 0
        assert result.warning_violations[0].requirement_type == ContractRequirementType.QUALITY_SLO

    @pytest.mark.asyncio
    async def test_prd_traceability_violation(self, temp_workflow_dir):
        """Test PRD_TRACEABILITY requirement violation"""
        req = ContractRequirement(
            requirement_id="prd",
            requirement_type=ContractRequirementType.PRD_TRACEABILITY,
            severity=ContractSeverity.WARNING,
            description="80% features implemented",
            validation_criteria={},
            min_threshold=0.8
        )

        contract = OutputContract(
            contract_id="test",
            phase="implementation",
            produces=[],
            requirements=[req]
        )

        # Report with low feature implementation
        report = {
            "workflow_id": "test",
            "can_build": True,
            "weighted_scores": {
                "features_implemented": 0.5  # Below 0.8 threshold
            }
        }

        validator = ContractValidator()
        result = await validator.validate_contract(
            contract,
            temp_workflow_dir,
            report
        )

        assert len(result.warning_violations) > 0
        assert result.warning_violations[0].requirement_type == ContractRequirementType.PRD_TRACEABILITY


# ===== CONTRACT VIOLATION TESTS =====

class TestContractViolation:
    """Test contract violation structure and serialization"""

    def test_create_violation(self):
        """Test creating a contract violation"""
        violation = ContractViolation(
            requirement_id="test_req",
            requirement_type=ContractRequirementType.BUILD_SUCCESS,
            severity=ContractSeverity.BLOCKING,
            violation_message="Build failed",
            actual_value=False,
            expected_value=True,
            evidence=["TypeScript compilation error"]
        )

        assert violation.requirement_id == "test_req"
        assert violation.severity == ContractSeverity.BLOCKING
        assert len(violation.evidence) == 1

    def test_violation_serialization(self):
        """Test violation can be serialized to dict"""
        violation = ContractViolation(
            requirement_id="test",
            requirement_type=ContractRequirementType.NO_STUBS,
            severity=ContractSeverity.WARNING,
            violation_message="Stub rate too high",
            actual_value=0.15,
            expected_value=0.05
        )

        violation_dict = violation.to_dict()

        assert violation_dict["requirement_id"] == "test"
        assert violation_dict["actual_value"] == 0.15
        assert violation_dict["expected_value"] == 0.05


# ===== CONTRACT VALIDATION RESULT TESTS =====

class TestContractValidationResult:
    """Test contract validation result structure"""

    def test_create_result(self):
        """Test creating validation result"""
        result = ContractValidationResult(
            contract_id="test",
            phase="implementation",
            passed=True,
            requirements_met=5,
            requirements_total=5
        )

        assert result.passed == True
        assert result.requirements_met == 5
        assert len(result.blocking_violations) == 0

    def test_result_with_violations(self):
        """Test result with violations"""
        violation = ContractViolation(
            requirement_id="build",
            requirement_type=ContractRequirementType.BUILD_SUCCESS,
            severity=ContractSeverity.BLOCKING,
            violation_message="Build failed"
        )

        result = ContractValidationResult(
            contract_id="test",
            phase="implementation",
            passed=False,
            blocking_violations=[violation],
            requirements_met=4,
            requirements_total=5
        )

        assert not result.passed
        assert len(result.blocking_violations) == 1
        assert result.requirements_met < result.requirements_total

    def test_result_serialization(self):
        """Test result can be serialized to dict"""
        result = ContractValidationResult(
            contract_id="test",
            phase="implementation",
            passed=True,
            requirements_met=5,
            requirements_total=5
        )

        result_dict = result.to_dict()

        assert result_dict["contract_id"] == "test"
        assert result_dict["passed"] == True
        assert "validation_timestamp" in result_dict


# ===== CONTRACT REGISTRY TESTS =====

class TestContractRegistry:
    """Test contract registry functionality"""

    def test_registry_initialization(self):
        """Test registry initializes with default contracts"""
        registry = ContractRegistry()

        contracts = registry.list_contracts()

        assert "implementation" in contracts
        assert "deployment" in contracts
        assert "testing" in contracts
        assert len(contracts) == 3

    def test_get_contract(self):
        """Test getting contract by phase"""
        registry = ContractRegistry()

        impl_contract = registry.get_contract("implementation")

        assert impl_contract is not None
        assert impl_contract.phase == "implementation"
        assert impl_contract.contract_id == "implementation_v1"

    def test_register_new_contract(self):
        """Test registering a new contract"""
        registry = ContractRegistry()

        new_contract = OutputContract(
            contract_id="custom_v1",
            phase="custom_phase",
            produces=["custom_output"]
        )

        registry.register_contract(new_contract)

        retrieved = registry.get_contract("custom_phase")
        assert retrieved is not None
        assert retrieved.contract_id == "custom_v1"

    def test_get_all_contracts(self):
        """Test getting all contracts"""
        registry = ContractRegistry()

        all_contracts = registry.get_all_contracts()

        assert len(all_contracts) == 3
        assert "implementation" in all_contracts
        assert isinstance(all_contracts["implementation"], OutputContract)


# ===== QUALITY FABRIC INTEGRATION TESTS =====

class TestQualityFabricIntegration:
    """Test Quality Fabric integration"""

    @pytest.mark.asyncio
    async def test_publish_contract_result_structure(self):
        """Test contract result publishing structure"""
        integration = QualityFabricIntegration(quality_fabric_url="http://mock:9800")

        result = ContractValidationResult(
            contract_id="test",
            phase="implementation",
            passed=True,
            requirements_met=5,
            requirements_total=5
        )

        # This will fail to connect but tests the structure
        # In real implementation, would mock HTTP client
        success = await integration.publish_contract_result(result, "test-workflow")

        # Should handle failure gracefully
        assert success == False

    @pytest.mark.asyncio
    async def test_check_slo_compliance(self):
        """Test SLO compliance checking"""
        integration = QualityFabricIntegration()

        slo_result = await integration.check_slo_compliance(
            "test-workflow",
            "build_success_rate"
        )

        # Should return dict with compliance status
        assert "compliant" in slo_result
        assert "actual_value" in slo_result
        assert "threshold" in slo_result


# ===== INTEGRATION TESTS =====

class TestContractIntegration:
    """Test end-to-end contract validation scenarios"""

    @pytest.mark.asyncio
    async def test_full_validation_workflow_passing(
        self,
        temp_workflow_dir,
        sample_validation_report_passing
    ):
        """Test full contract validation for passing workflow"""
        # Get implementation contract
        contract = create_implementation_contract()

        # Validate
        validator = ContractValidator()
        result = await validator.validate_contract(
            contract,
            temp_workflow_dir,
            sample_validation_report_passing
        )

        # Should pass all checks
        assert result.passed
        assert len(result.blocking_violations) == 0
        assert result.requirements_met == result.requirements_total

    @pytest.mark.asyncio
    async def test_full_validation_workflow_failing(
        self,
        temp_workflow_dir,
        sample_validation_report_failing
    ):
        """Test full contract validation for failing workflow"""
        contract = create_implementation_contract()
        validator = ContractValidator()

        result = await validator.validate_contract(
            contract,
            temp_workflow_dir,
            sample_validation_report_failing
        )

        # Should fail with blocking violations
        assert not result.passed
        assert len(result.blocking_violations) > 0

        # Should have build failure violations
        build_violations = [v for v in result.blocking_violations
                            if v.requirement_type == ContractRequirementType.BUILD_SUCCESS]
        assert len(build_violations) > 0

    @pytest.mark.asyncio
    async def test_severity_levels(self, temp_workflow_dir):
        """Test that severity levels are enforced correctly"""
        # Create contract with BLOCKING and WARNING requirements
        blocking_req = ContractRequirement(
            requirement_id="blocking",
            requirement_type=ContractRequirementType.BUILD_SUCCESS,
            severity=ContractSeverity.BLOCKING,
            description="Must build",
            validation_criteria={}
        )

        warning_req = ContractRequirement(
            requirement_id="warning",
            requirement_type=ContractRequirementType.QUALITY_SLO,
            severity=ContractSeverity.WARNING,
            description="Quality should be high",
            validation_criteria={},
            min_threshold=0.9
        )

        contract = OutputContract(
            contract_id="test",
            phase="test",
            produces=[],
            requirements=[blocking_req, warning_req]
        )

        # Report that passes blocking but fails warning
        report = {
            "workflow_id": "test",
            "can_build": True,
            "overall_score": 0.75,  # Below 0.9
            "build_validation": {"results": []}
        }

        validator = ContractValidator()
        result = await validator.validate_contract(contract, temp_workflow_dir, report)

        # Should pass (no blocking violations)
        assert result.passed == True
        # But should have warning
        assert len(result.warning_violations) > 0


# ===== PYTEST CONFIGURATION =====

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
