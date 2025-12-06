"""
Block Contract Tests - AC-2: Contract Tests for Each Block

These tests validate that each certified block:
1. Implements the required interface methods
2. Returns correct types
3. Handles edge cases appropriately
4. Maintains behavioral contracts

Reference: MD-2507 Acceptance Criterion 2
"""

import pytest
from typing import Dict, Any

# Import blocks
import sys
sys.path.insert(0, '/home/ec2-user/projects/maestro-platform/maestro-hive/src')

from maestro_hive.blocks import (
    DAGExecutorBlock,
    PhaseOrchestratorBlock,
    ContractRegistryBlock,
    JiraAdapterBlock,
    QualityFabricBlock,
    BlockRegistry,
    get_block_registry,
)
from maestro_hive.blocks.interfaces import (
    IDAGExecutor,
    IPhaseOrchestrator,
    IContractRegistry,
    IJiraAdapter,
    IQualityFabric,
    ExecutionResult,
    ValidationResult,
    PhaseResult,
    ContractValidation,
    IssueData,
    HealthStatus,
)
from maestro_hive.core.block_interface import BlockResult, BlockStatus


class TestBlockInterface:
    """Test that all blocks implement BlockInterface correctly"""

    @pytest.fixture
    def blocks(self):
        """Create instances of all blocks"""
        return {
            "dag-executor": DAGExecutorBlock(),
            "phase-orchestrator": PhaseOrchestratorBlock(),
            "contract-registry": ContractRegistryBlock(),
            "jira-adapter": JiraAdapterBlock(),
            "quality-fabric": QualityFabricBlock(),
        }

    def test_all_blocks_have_block_id(self, blocks):
        """All blocks must have a block_id property"""
        for name, block in blocks.items():
            assert hasattr(block, 'block_id')
            assert isinstance(block.block_id, str)
            assert len(block.block_id) > 0
            assert block.block_id == name

    def test_all_blocks_have_version(self, blocks):
        """All blocks must have a semver version"""
        import re
        semver_pattern = r'^\d+\.\d+\.\d+$'

        for name, block in blocks.items():
            assert hasattr(block, 'version')
            assert isinstance(block.version, str)
            assert re.match(semver_pattern, block.version), f"{name} has invalid version: {block.version}"

    def test_all_blocks_have_validate_inputs(self, blocks):
        """All blocks must have validate_inputs method"""
        for name, block in blocks.items():
            assert hasattr(block, 'validate_inputs')
            assert callable(block.validate_inputs)

    def test_all_blocks_have_execute(self, blocks):
        """All blocks must have execute method"""
        for name, block in blocks.items():
            assert hasattr(block, 'execute')
            assert callable(block.execute)

    def test_all_blocks_have_health_check(self, blocks):
        """All blocks must have health_check method"""
        for name, block in blocks.items():
            assert hasattr(block, 'health_check')
            assert callable(block.health_check)
            # Health check should return bool
            result = block.health_check()
            assert isinstance(result, bool)


class TestDAGExecutorBlockContract:
    """Contract tests for DAGExecutorBlock"""

    @pytest.fixture
    def block(self):
        return DAGExecutorBlock()

    def test_implements_interface(self, block):
        """Must implement IDAGExecutor interface"""
        assert isinstance(block, IDAGExecutor)

    def test_block_id_is_dag_executor(self, block):
        """Block ID must be 'dag-executor'"""
        assert block.block_id == "dag-executor"

    def test_version_is_2_0_0(self, block):
        """Version must be 2.0.0"""
        assert block.version == "2.0.0"

    def test_validate_inputs_rejects_empty(self, block):
        """Must reject empty inputs"""
        assert block.validate_inputs({}) == False
        assert block.validate_inputs(None) == False

    def test_validate_inputs_requires_dag_definition(self, block):
        """Must require dag_definition"""
        assert block.validate_inputs({"dag_definition": {"nodes": []}}) == True
        assert block.validate_inputs({"other": "value"}) == False

    def test_execute_returns_block_result(self, block):
        """Execute must return BlockResult"""
        result = block.execute({"dag_definition": {"nodes": [{"id": "node1"}]}})
        assert isinstance(result, BlockResult)
        assert hasattr(result, 'status')
        assert hasattr(result, 'output')

    def test_execute_dag_returns_execution_result(self, block):
        """execute_dag must return ExecutionResult"""
        result = block.execute_dag({"nodes": [{"id": "test"}]})
        assert isinstance(result, ExecutionResult)
        assert hasattr(result, 'success')
        assert hasattr(result, 'execution_id')
        assert hasattr(result, 'status')

    def test_validate_dag_returns_validation_result(self, block):
        """validate_dag must return ValidationResult"""
        result = block.validate_dag({"nodes": [{"id": "test"}]})
        assert isinstance(result, ValidationResult)
        assert hasattr(result, 'valid')
        assert hasattr(result, 'errors')
        assert hasattr(result, 'warnings')

    def test_validate_dag_detects_missing_nodes(self, block):
        """Must detect DAG with no nodes"""
        result = block.validate_dag({"nodes": []})
        assert result.valid == False
        assert len(result.errors) > 0

    def test_validate_dag_detects_missing_dependencies(self, block):
        """Must detect references to non-existent nodes"""
        result = block.validate_dag({
            "nodes": [
                {"id": "node1", "dependencies": ["non_existent"]}
            ]
        })
        assert result.valid == False
        assert "non_existent" in str(result.errors)

    def test_get_execution_status(self, block):
        """Must track execution status"""
        exec_result = block.execute_dag({"nodes": [{"id": "test"}]})
        status = block.get_execution_status(exec_result.execution_id)
        assert isinstance(status, dict)
        assert "status" in status


class TestPhaseOrchestratorBlockContract:
    """Contract tests for PhaseOrchestratorBlock"""

    @pytest.fixture
    def block(self):
        return PhaseOrchestratorBlock()

    def test_implements_interface(self, block):
        """Must implement IPhaseOrchestrator interface"""
        assert isinstance(block, IPhaseOrchestrator)

    def test_block_id_is_phase_orchestrator(self, block):
        """Block ID must be 'phase-orchestrator'"""
        assert block.block_id == "phase-orchestrator"

    def test_version_is_1_5_0(self, block):
        """Version must be 1.5.0"""
        assert block.version == "1.5.0"

    def test_run_phase_returns_phase_result(self, block):
        """run_phase must return PhaseResult"""
        result = block.run_phase("requirements", {"quality_score": 0.8})
        assert isinstance(result, PhaseResult)
        assert hasattr(result, 'phase')
        assert hasattr(result, 'passed')
        assert hasattr(result, 'score')
        assert hasattr(result, 'gates_passed')
        assert hasattr(result, 'gates_failed')

    def test_run_phase_validates_phase_name(self, block):
        """Must reject invalid phase names"""
        result = block.run_phase("invalid_phase", {})
        assert result.passed == False
        assert "invalid_phase" in str(result.gates_failed) or "invalid" in str(result.output)

    def test_valid_phases(self, block):
        """Must accept all valid SDLC phases"""
        valid_phases = ["requirements", "design", "implementation", "testing", "deployment"]
        for phase in valid_phases:
            result = block.run_phase(phase, {"quality_score": 0.9})
            assert result.phase == phase

    def test_transition_validates_sequence(self, block):
        """Must validate phase transition sequence"""
        # Complete requirements first
        block.run_phase("requirements", {"quality_score": 0.9})
        block._phase_states["requirements"] = block._phase_states["requirements"].__class__("completed")

        # Valid transition
        assert block.transition("requirements", "design") == True

        # Invalid transition (can't skip phases)
        assert block.transition("requirements", "deployment") == False

    def test_validate_entry_criteria(self, block):
        """Must validate entry criteria"""
        result = block.validate_entry_criteria("design", {})
        assert isinstance(result, ValidationResult)
        assert hasattr(result, 'valid')

    def test_validate_exit_criteria(self, block):
        """Must validate exit criteria"""
        result = block.validate_exit_criteria("requirements", {})
        assert isinstance(result, ValidationResult)


class TestContractRegistryBlockContract:
    """Contract tests for ContractRegistryBlock"""

    @pytest.fixture
    def block(self):
        return ContractRegistryBlock()

    def test_implements_interface(self, block):
        """Must implement IContractRegistry interface"""
        assert isinstance(block, IContractRegistry)

    def test_block_id_is_contract_registry(self, block):
        """Block ID must be 'contract-registry'"""
        assert block.block_id == "contract-registry"

    def test_version_is_1_0_0(self, block):
        """Version must be 1.0.0"""
        assert block.version == "1.0.0"

    def test_register_contract_returns_id(self, block):
        """register_contract must return contract ID"""
        contract_id = block.register_contract({
            "phase": "test",
            "produces": ["output1"],
            "requirements": []
        })
        assert isinstance(contract_id, str)
        assert len(contract_id) > 0

    def test_get_contract_returns_registered(self, block):
        """get_contract must return registered contract"""
        contract_id = block.register_contract({
            "contract_id": "test-contract",
            "phase": "test"
        })
        contract = block.get_contract(contract_id)
        assert contract is not None
        assert contract["contract_id"] == contract_id

    def test_list_contracts(self, block):
        """list_contracts must return all IDs"""
        contracts = block.list_contracts()
        assert isinstance(contracts, list)
        # Should have default contracts
        assert len(contracts) > 0

    def test_validate_output_returns_validation(self, block):
        """validate_output must return ContractValidation"""
        result = block.validate_output("implementation", {"build_success": True})
        assert isinstance(result, ContractValidation)
        assert hasattr(result, 'passed')
        assert hasattr(result, 'violations')
        assert hasattr(result, 'score')

    def test_evolve_contract(self, block):
        """evolve_contract must create new version"""
        original_id = block.register_contract({
            "contract_id": "evolve-test",
            "phase": "test",
            "version": "1.0.0"
        })

        new_id = block.evolve_contract(original_id, {"new_feature": True})
        assert new_id != original_id
        assert "1.1.0" in new_id or "1.0.1" in new_id


class TestJiraAdapterBlockContract:
    """Contract tests for JiraAdapterBlock"""

    @pytest.fixture
    def block(self):
        return JiraAdapterBlock({"project_key": "TEST"})

    def test_implements_interface(self, block):
        """Must implement IJiraAdapter interface"""
        assert isinstance(block, IJiraAdapter)

    def test_block_id_is_jira_adapter(self, block):
        """Block ID must be 'jira-adapter'"""
        assert block.block_id == "jira-adapter"

    def test_version_is_3_1_0(self, block):
        """Version must be 3.1.0"""
        assert block.version == "3.1.0"

    def test_create_issue_returns_issue_data(self, block):
        """create_issue must return IssueData"""
        result = block.create_issue({
            "summary": "Test Issue",
            "description": "Test description"
        })
        assert isinstance(result, IssueData)
        assert hasattr(result, 'key')
        assert hasattr(result, 'summary')
        assert result.summary == "Test Issue"

    def test_get_issue_returns_created(self, block):
        """get_issue must return previously created issue"""
        created = block.create_issue({"summary": "Get Test"})
        retrieved = block.get_issue(created.key)
        assert retrieved is not None
        assert retrieved.key == created.key

    def test_update_issue(self, block):
        """update_issue must modify issue"""
        created = block.create_issue({"summary": "Original"})
        updated = block.update_issue(created.key, {"status": "In Progress"})
        assert updated.status == "In Progress"

    def test_add_comment_returns_dict(self, block):
        """add_comment must return comment data"""
        issue = block.create_issue({"summary": "Comment Test"})
        result = block.add_comment(issue.key, "Test comment")
        assert isinstance(result, dict)
        assert "body" in result or "id" in result

    def test_transition_issue(self, block):
        """transition_issue must change status"""
        issue = block.create_issue({"summary": "Transition Test"})
        success = block.transition_issue(issue.key, "Done")
        assert success == True

        updated = block.get_issue(issue.key)
        assert updated.status == "Done"

    def test_search_issues_returns_list(self, block):
        """search_issues must return list of IssueData"""
        block.create_issue({"summary": "Search Test"})
        results = block.search_issues("project = TEST")
        assert isinstance(results, list)
        assert all(isinstance(r, IssueData) for r in results)


class TestQualityFabricBlockContract:
    """Contract tests for QualityFabricBlock"""

    @pytest.fixture
    def block(self):
        return QualityFabricBlock()

    def test_implements_interface(self, block):
        """Must implement IQualityFabric interface"""
        assert isinstance(block, IQualityFabric)

    def test_block_id_is_quality_fabric(self, block):
        """Block ID must be 'quality-fabric'"""
        assert block.block_id == "quality-fabric"

    def test_version_is_2_0_0(self, block):
        """Version must be 2.0.0"""
        assert block.version == "2.0.0"

    def test_validate_persona_returns_dict(self, block):
        """validate_persona must return validation dict"""
        result = block.validate_persona(
            "persona-1",
            "backend_developer",
            {"code_files": ["main.py"], "test_files": ["test_main.py"]}
        )
        assert isinstance(result, dict)
        assert "overall_score" in result
        assert "gates_passed" in result
        assert "gates_failed" in result

    def test_evaluate_gate_returns_dict(self, block):
        """evaluate_gate must return gate evaluation"""
        result = block.evaluate_gate("implementation", {"code_complete": True})
        assert isinstance(result, dict)
        assert "passed" in result
        assert "overall_score" in result

    def test_get_health_returns_health_status(self, block):
        """get_health must return HealthStatus"""
        result = block.get_health()
        assert isinstance(result, HealthStatus)
        assert hasattr(result, 'healthy')
        assert hasattr(result, 'status')
        assert hasattr(result, 'version')

    def test_publish_metrics(self, block):
        """publish_metrics must accept metrics dict"""
        result = block.publish_metrics({"quality_score": 0.85})
        assert isinstance(result, bool)


class TestBlockRegistry:
    """Contract tests for BlockRegistry"""

    @pytest.fixture
    def registry(self):
        reg = BlockRegistry()
        reg.clear()  # Clear for clean test
        return reg

    def test_singleton_pattern(self):
        """Registry must be singleton"""
        reg1 = BlockRegistry()
        reg2 = BlockRegistry()
        assert reg1 is reg2

    def test_get_block_registry_returns_singleton(self):
        """get_block_registry must return singleton"""
        reg1 = get_block_registry()
        reg2 = get_block_registry()
        assert reg1 is reg2

    def test_register_block(self, registry):
        """Must be able to register blocks"""
        key = registry.register(DAGExecutorBlock, description="DAG executor")
        assert "dag-executor" in key
        assert "2.0.0" in key

    def test_get_block_by_id(self, registry):
        """Must be able to get block by ID"""
        registry.register(DAGExecutorBlock)
        block = registry.get("dag-executor")
        assert block is not None
        assert isinstance(block, DAGExecutorBlock)

    def test_get_block_by_version(self, registry):
        """Must be able to get specific version"""
        registry.register(DAGExecutorBlock)
        block = registry.get("dag-executor", "2.0.0")
        assert block is not None
        assert block.version == "2.0.0"

    def test_list_blocks(self, registry):
        """Must list all registered blocks"""
        registry.register(DAGExecutorBlock)
        registry.register(PhaseOrchestratorBlock)

        blocks = registry.list_blocks()
        assert "dag-executor" in blocks
        assert "phase-orchestrator" in blocks

    def test_get_metadata(self, registry):
        """Must return block metadata"""
        registry.register(DAGExecutorBlock, description="Test description")

        metadata = registry.get_metadata("dag-executor")
        assert metadata is not None
        assert metadata.block_id == "dag-executor"
        assert metadata.version == "2.0.0"
        assert metadata.description == "Test description"

    def test_deprecate_block(self, registry):
        """Must be able to deprecate block versions"""
        registry.register(DAGExecutorBlock)
        success = registry.deprecate("dag-executor", "2.0.0", "Use 3.0.0 instead")
        assert success == True

        metadata = registry.get_metadata("dag-executor", "2.0.0")
        assert metadata.deprecated == True

    def test_get_registry_stats(self, registry):
        """Must return registry statistics"""
        registry.register(DAGExecutorBlock)
        registry.register(PhaseOrchestratorBlock)

        stats = registry.get_registry_stats()
        assert "total_blocks" in stats
        assert stats["total_blocks"] >= 2


class TestBlockVersioning:
    """Test semver versioning compliance (AC-4)"""

    def test_dag_executor_version_semver(self):
        """DAGExecutorBlock must use semver"""
        block = DAGExecutorBlock()
        parts = block.version.split(".")
        assert len(parts) == 3
        assert all(p.isdigit() for p in parts)

    def test_phase_orchestrator_version_semver(self):
        """PhaseOrchestratorBlock must use semver"""
        block = PhaseOrchestratorBlock()
        parts = block.version.split(".")
        assert len(parts) == 3
        assert all(p.isdigit() for p in parts)

    def test_contract_registry_version_semver(self):
        """ContractRegistryBlock must use semver"""
        block = ContractRegistryBlock()
        parts = block.version.split(".")
        assert len(parts) == 3
        assert all(p.isdigit() for p in parts)

    def test_jira_adapter_version_semver(self):
        """JiraAdapterBlock must use semver"""
        block = JiraAdapterBlock()
        parts = block.version.split(".")
        assert len(parts) == 3
        assert all(p.isdigit() for p in parts)

    def test_quality_fabric_version_semver(self):
        """QualityFabricBlock must use semver"""
        block = QualityFabricBlock()
        parts = block.version.split(".")
        assert len(parts) == 3
        assert all(p.isdigit() for p in parts)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
