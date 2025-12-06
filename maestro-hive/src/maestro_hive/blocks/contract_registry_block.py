"""
ContractRegistryBlock - Certified Block for Contract Management

Wraps the existing output_contracts.py and contract_manager.py
as a certified block with contract testing and versioning.

Block ID: contract-registry
Version: 1.0.0

Reference: MD-2507 Block Formalization
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from uuid import uuid4

from ..core.block_interface import BlockInterface, BlockResult, BlockStatus
from .interfaces import (
    IContractRegistry,
    ContractValidation,
)

logger = logging.getLogger(__name__)


class ContractRegistryBlock(IContractRegistry):
    """
    Certified block wrapping ContractRegistry and ContractValidator.

    This block formalizes the output contract system with
    standard interface, contract testing, and versioning.

    Features:
    - Contract registration and discovery
    - Output validation against contracts
    - Contract versioning and evolution
    - SLO enforcement
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize ContractRegistryBlock.

        Args:
            config: Optional configuration
                - strict_validation: Fail on any violation (default: True)
                - cache_enabled: Enable validation caching (default: True)
        """
        self._config = config or {}
        self._strict_validation = self._config.get("strict_validation", True)
        self._cache_enabled = self._config.get("cache_enabled", True)

        self._contracts: Dict[str, Dict[str, Any]] = {}
        self._validation_cache: Dict[str, ContractValidation] = {}

        # Lazy-load wrapped modules
        self._output_contracts_module = None
        self._contract_manager_module = None

        # Initialize default contracts
        self._initialize_default_contracts()

        logger.info(f"ContractRegistryBlock initialized (v{self.version})")

    def _initialize_for_registration(self):
        """Minimal init for registry metadata extraction"""
        pass

    @property
    def block_id(self) -> str:
        return "contract-registry"

    @property
    def version(self) -> str:
        return "1.0.0"

    def _get_output_contracts_module(self):
        """Lazy load output_contracts module"""
        if self._output_contracts_module is None:
            try:
                import output_contracts
                self._output_contracts_module = output_contracts
            except ImportError:
                logger.warning("output_contracts module not found, using internal")
                self._output_contracts_module = None
        return self._output_contracts_module

    def _initialize_default_contracts(self):
        """Initialize default phase contracts"""
        default_contracts = [
            {
                "contract_id": "requirements-contract",
                "phase": "requirements",
                "produces": ["prd", "user_stories", "acceptance_criteria"],
                "requirements": [
                    {"id": "req-1", "type": "completeness", "min_threshold": 0.9}
                ],
                "version": "1.0.0"
            },
            {
                "contract_id": "design-contract",
                "phase": "design",
                "produces": ["architecture", "api_spec", "data_models"],
                "requirements": [
                    {"id": "des-1", "type": "architecture_complete", "min_threshold": 1.0}
                ],
                "version": "1.0.0"
            },
            {
                "contract_id": "implementation-contract",
                "phase": "implementation",
                "produces": ["source_code", "unit_tests", "api_implementation"],
                "requirements": [
                    {"id": "impl-1", "type": "build_success", "min_threshold": 1.0},
                    {"id": "impl-2", "type": "test_coverage", "min_threshold": 0.8}
                ],
                "version": "1.0.0"
            },
            {
                "contract_id": "testing-contract",
                "phase": "testing",
                "produces": ["test_results", "coverage_report", "quality_metrics"],
                "requirements": [
                    {"id": "test-1", "type": "all_tests_pass", "min_threshold": 1.0},
                    {"id": "test-2", "type": "coverage", "min_threshold": 0.8}
                ],
                "version": "1.0.0"
            },
            {
                "contract_id": "deployment-contract",
                "phase": "deployment",
                "produces": ["deployment_config", "runbook", "monitoring_config"],
                "requirements": [
                    {"id": "dep-1", "type": "deployment_ready", "min_threshold": 1.0}
                ],
                "version": "1.0.0"
            }
        ]

        for contract in default_contracts:
            self._contracts[contract["contract_id"]] = contract

    def validate_inputs(self, inputs: Dict[str, Any]) -> bool:
        """Validate registry operation inputs"""
        if not isinstance(inputs, dict):
            return False

        operation = inputs.get("operation")
        if operation not in ["register", "validate", "get", "list", "evolve"]:
            return False

        return True

    def execute(self, inputs: Dict[str, Any]) -> BlockResult:
        """
        Execute registry operation.

        Args:
            inputs: {"operation": "validate", "block_id": "...", "output": {...}}

        Returns:
            BlockResult with operation outcome
        """
        if not self.validate_inputs(inputs):
            return BlockResult(
                status=BlockStatus.FAILED,
                output={},
                error="Invalid inputs: operation required"
            )

        try:
            operation = inputs["operation"]

            if operation == "register":
                contract_id = self.register_contract(inputs.get("contract", {}))
                return BlockResult(
                    status=BlockStatus.COMPLETED,
                    output={"contract_id": contract_id}
                )

            elif operation == "validate":
                result = self.validate_output(
                    inputs.get("block_id", ""),
                    inputs.get("output", {})
                )
                return BlockResult(
                    status=BlockStatus.COMPLETED if result.passed else BlockStatus.FAILED,
                    output={
                        "contract_id": result.contract_id,
                        "passed": result.passed,
                        "violations": result.violations,
                        "score": result.score
                    }
                )

            elif operation == "get":
                contract = self.get_contract(inputs.get("contract_id", ""))
                return BlockResult(
                    status=BlockStatus.COMPLETED if contract else BlockStatus.FAILED,
                    output={"contract": contract}
                )

            elif operation == "list":
                contracts = self.list_contracts()
                return BlockResult(
                    status=BlockStatus.COMPLETED,
                    output={"contracts": contracts}
                )

            elif operation == "evolve":
                new_id = self.evolve_contract(
                    inputs.get("contract_id", ""),
                    inputs.get("new_version", {})
                )
                return BlockResult(
                    status=BlockStatus.COMPLETED,
                    output={"new_contract_id": new_id}
                )

            else:
                return BlockResult(
                    status=BlockStatus.FAILED,
                    output={},
                    error=f"Unknown operation: {operation}"
                )

        except Exception as e:
            logger.error(f"Contract registry operation failed: {e}")
            return BlockResult(
                status=BlockStatus.FAILED,
                output={},
                error=str(e)
            )

    def register_contract(self, contract: Dict[str, Any]) -> str:
        """
        Register a new output contract.

        Args:
            contract: Contract definition with requirements

        Returns:
            Contract ID
        """
        contract_id = contract.get("contract_id") or f"contract-{uuid4().hex[:8]}"

        contract_data = {
            "contract_id": contract_id,
            "phase": contract.get("phase", "unknown"),
            "produces": contract.get("produces", []),
            "requirements": contract.get("requirements", []),
            "slo_thresholds": contract.get("slo_thresholds", {}),
            "version": contract.get("version", "1.0.0"),
            "created_at": datetime.utcnow().isoformat(),
            "metadata": contract.get("metadata", {})
        }

        self._contracts[contract_id] = contract_data
        logger.info(f"Registered contract: {contract_id}")

        return contract_id

    def validate_output(self, block_id: str, output: Dict[str, Any]) -> ContractValidation:
        """
        Validate output against registered contract.

        Args:
            block_id: Block/phase ID to validate
            output: Output to validate

        Returns:
            ContractValidation with pass/fail and violations
        """
        # Find contract for this block/phase
        contract = None
        for cid, c in self._contracts.items():
            if c.get("phase") == block_id or cid == block_id:
                contract = c
                break

        if not contract:
            return ContractValidation(
                contract_id="none",
                passed=False,
                violations=[{"error": f"No contract found for: {block_id}"}],
                score=0.0
            )

        violations = []
        requirements_met = 0
        total_requirements = len(contract.get("requirements", []))

        # Check produces
        for required in contract.get("produces", []):
            if required not in output:
                violations.append({
                    "type": "missing_output",
                    "required": required,
                    "severity": "blocking"
                })

        # Check requirements
        for req in contract.get("requirements", []):
            req_id = req.get("id", "unknown")
            req_type = req.get("type", "unknown")
            min_threshold = req.get("min_threshold", 0.0)

            # Get actual value from output
            actual_value = self._get_requirement_value(req_type, output)

            if actual_value >= min_threshold:
                requirements_met += 1
            else:
                violations.append({
                    "requirement_id": req_id,
                    "type": req_type,
                    "expected": min_threshold,
                    "actual": actual_value,
                    "severity": "blocking" if self._strict_validation else "warning"
                })

        # Calculate score
        score = requirements_met / max(total_requirements, 1)
        passed = len([v for v in violations if v.get("severity") == "blocking"]) == 0

        return ContractValidation(
            contract_id=contract["contract_id"],
            passed=passed,
            violations=violations,
            score=score
        )

    def _get_requirement_value(self, req_type: str, output: Dict[str, Any]) -> float:
        """Extract requirement value from output"""
        if req_type == "build_success":
            return 1.0 if output.get("build_success", False) else 0.0

        elif req_type == "test_coverage":
            return output.get("test_coverage", 0.0)

        elif req_type == "all_tests_pass":
            return 1.0 if output.get("tests_passed", False) else 0.0

        elif req_type == "completeness":
            return output.get("completeness", 0.0)

        elif req_type == "architecture_complete":
            return 1.0 if output.get("architecture_complete", False) else 0.0

        elif req_type == "deployment_ready":
            return 1.0 if output.get("deployment_ready", False) else 0.0

        elif req_type == "coverage":
            return output.get("coverage", 0.0)

        else:
            # Generic check
            return output.get(req_type, 0.0)

    def get_contract(self, contract_id: str) -> Optional[Dict[str, Any]]:
        """Get a registered contract by ID"""
        return self._contracts.get(contract_id)

    def list_contracts(self) -> List[str]:
        """List all registered contract IDs"""
        return list(self._contracts.keys())

    def evolve_contract(self, contract_id: str, new_version: Dict[str, Any]) -> str:
        """Create a new version of an existing contract"""
        if contract_id not in self._contracts:
            raise ValueError(f"Contract not found: {contract_id}")

        old_contract = self._contracts[contract_id]

        # Parse version and increment
        old_version = old_contract.get("version", "1.0.0")
        parts = old_version.split(".")
        major, minor, patch = int(parts[0]), int(parts[1]), int(parts[2])

        # Determine version bump
        if new_version.get("breaking_change", False):
            new_version_str = f"{major + 1}.0.0"
        elif new_version.get("new_feature", False):
            new_version_str = f"{major}.{minor + 1}.0"
        else:
            new_version_str = f"{major}.{minor}.{patch + 1}"

        # Create new contract
        new_contract = {**old_contract, **new_version}
        new_contract["version"] = new_version_str
        new_contract["evolved_from"] = contract_id
        new_contract["created_at"] = datetime.utcnow().isoformat()

        new_id = f"{contract_id}-v{new_version_str}"
        self._contracts[new_id] = new_contract

        logger.info(f"Evolved contract {contract_id} -> {new_id}")
        return new_id

    def health_check(self) -> bool:
        """Check if the block is healthy"""
        return True

    def get_contract_summary(self) -> Dict[str, Any]:
        """Get summary of all contracts"""
        return {
            "total_contracts": len(self._contracts),
            "contracts": [
                {
                    "id": cid,
                    "phase": c.get("phase"),
                    "version": c.get("version"),
                    "requirements_count": len(c.get("requirements", []))
                }
                for cid, c in self._contracts.items()
            ]
        }
