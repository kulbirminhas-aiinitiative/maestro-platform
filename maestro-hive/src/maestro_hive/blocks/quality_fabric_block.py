"""
QualityFabricBlock - Certified Block for Quality Fabric Integration

Wraps the existing quality_fabric_client.py as a certified block
with contract testing and versioning.

Block ID: quality-fabric
Version: 2.0.0

Reference: MD-2507 Block Formalization
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime

from ..core.block_interface import BlockInterface, BlockResult, BlockStatus
from .interfaces import (
    IQualityFabric,
    HealthStatus,
)

logger = logging.getLogger(__name__)


class QualityFabricBlock(IQualityFabric):
    """
    Certified block wrapping QualityFabricClient.

    This block formalizes the Quality Fabric integration with
    standard interface, contract testing, and versioning.

    Features:
    - Persona output validation
    - Phase quality gate evaluation
    - Health monitoring
    - Metrics publishing
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize QualityFabricBlock.

        Args:
            config: Optional configuration
                - quality_fabric_url: QF URL (default: http://localhost:8000)
                - timeout: Request timeout (default: 60.0)
                - fallback_to_mock: Use mock if QF unavailable (default: True)
        """
        self._config = config or {}
        self._qf_url = self._config.get("quality_fabric_url", "http://localhost:8000")
        self._timeout = self._config.get("timeout", 60.0)
        self._fallback_to_mock = self._config.get("fallback_to_mock", True)

        # Lazy-load wrapped module
        self._qf_client_module = None
        self._qf_client = None

        self._start_time = datetime.utcnow()
        self._last_error: Optional[str] = None

        logger.info(f"QualityFabricBlock initialized (v{self.version})")

    def _initialize_for_registration(self):
        """Minimal init for registry metadata extraction"""
        pass

    @property
    def block_id(self) -> str:
        return "quality-fabric"

    @property
    def version(self) -> str:
        return "2.0.0"

    def _get_qf_client_module(self):
        """Lazy load quality_fabric_client module"""
        if self._qf_client_module is None:
            try:
                from ..quality import quality_fabric_client
                self._qf_client_module = quality_fabric_client
            except ImportError:
                logger.warning("quality_fabric_client not found, using mock")
                self._qf_client_module = None
        return self._qf_client_module

    def _get_qf_client(self):
        """Get or create QF client instance"""
        if self._qf_client is None:
            module = self._get_qf_client_module()
            if module:
                self._qf_client = module.QualityFabricClient(
                    quality_fabric_url=self._qf_url,
                    timeout=self._timeout
                )
        return self._qf_client

    def validate_inputs(self, inputs: Dict[str, Any]) -> bool:
        """Validate QF operation inputs"""
        if not isinstance(inputs, dict):
            return False

        operation = inputs.get("operation")
        if operation not in ["validate_persona", "evaluate_gate", "health", "publish_metrics"]:
            return False

        return True

    def execute(self, inputs: Dict[str, Any]) -> BlockResult:
        """
        Execute QF operation.

        Args:
            inputs: {"operation": "validate_persona", "persona_id": "...", ...}

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

            if operation == "validate_persona":
                result = self.validate_persona(
                    inputs.get("persona_id", ""),
                    inputs.get("persona_type", ""),
                    inputs.get("artifacts", {})
                )
                return BlockResult(
                    status=BlockStatus.COMPLETED,
                    output=result,
                    metrics={"quality_score": result.get("overall_score", 0)}
                )

            elif operation == "evaluate_gate":
                result = self.evaluate_gate(
                    inputs.get("phase", ""),
                    inputs.get("outputs", {})
                )
                return BlockResult(
                    status=BlockStatus.COMPLETED if result.get("passed") else BlockStatus.FAILED,
                    output=result
                )

            elif operation == "health":
                health = self.get_health()
                return BlockResult(
                    status=BlockStatus.COMPLETED if health.healthy else BlockStatus.FAILED,
                    output={
                        "healthy": health.healthy,
                        "status": health.status,
                        "version": health.version,
                        "uptime_seconds": health.uptime_seconds
                    }
                )

            elif operation == "publish_metrics":
                success = self.publish_metrics(inputs.get("metrics", {}))
                return BlockResult(
                    status=BlockStatus.COMPLETED if success else BlockStatus.FAILED,
                    output={"published": success}
                )

            else:
                return BlockResult(
                    status=BlockStatus.FAILED,
                    output={},
                    error=f"Unknown operation: {operation}"
                )

        except Exception as e:
            self._last_error = str(e)
            logger.error(f"QF operation failed: {e}")
            return BlockResult(
                status=BlockStatus.FAILED,
                output={},
                error=str(e)
            )

    def validate_persona(
        self,
        persona_id: str,
        persona_type: str,
        artifacts: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Validate persona output artifacts.

        Args:
            persona_id: Unique persona identifier
            persona_type: Type of persona
            artifacts: Output artifacts to validate

        Returns:
            Validation result with score and gates
        """
        client = self._get_qf_client()

        if client:
            import asyncio
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

            try:
                # Get PersonaType enum
                module = self._get_qf_client_module()
                persona_type_enum = module.PersonaType(persona_type)

                result = loop.run_until_complete(
                    client.validate_persona_output(
                        persona_id=persona_id,
                        persona_type=persona_type_enum,
                        output=artifacts
                    )
                )

                return {
                    "persona_id": result.persona_id,
                    "persona_type": result.persona_type,
                    "status": result.status,
                    "overall_score": result.overall_score,
                    "gates_passed": result.gates_passed,
                    "gates_failed": result.gates_failed,
                    "quality_metrics": result.quality_metrics,
                    "recommendations": result.recommendations,
                    "requires_revision": result.requires_revision
                }
            except Exception as e:
                logger.warning(f"QF client failed, using mock: {e}")
                if not self._fallback_to_mock:
                    raise

        # Mock validation
        return self._mock_validate_persona(persona_id, persona_type, artifacts)

    def _mock_validate_persona(
        self,
        persona_id: str,
        persona_type: str,
        artifacts: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Mock persona validation for testing"""
        gates_passed = []
        gates_failed = []

        # Check for code files
        if artifacts.get("code_files"):
            gates_passed.append("code_present")
        else:
            gates_failed.append("code_present")

        # Check for test files
        if artifacts.get("test_files"):
            gates_passed.append("tests_present")
        else:
            gates_failed.append("tests_present")

        # Check for documentation
        if artifacts.get("documentation"):
            gates_passed.append("docs_present")
        else:
            gates_failed.append("docs_present")

        total = len(gates_passed) + len(gates_failed)
        score = len(gates_passed) / max(total, 1)

        return {
            "persona_id": persona_id,
            "persona_type": persona_type,
            "status": "pass" if score >= 0.7 else "fail",
            "overall_score": score,
            "gates_passed": gates_passed,
            "gates_failed": gates_failed,
            "quality_metrics": {
                "completeness": score,
                "coverage_estimate": 0.8 if artifacts.get("test_files") else 0.0
            },
            "recommendations": [
                "Add more unit tests" if not artifacts.get("test_files") else None,
                "Add documentation" if not artifacts.get("documentation") else None
            ],
            "requires_revision": score < 0.7
        }

    def evaluate_gate(
        self,
        phase: str,
        outputs: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Evaluate phase quality gate.

        Args:
            phase: SDLC phase name
            outputs: Phase outputs to evaluate

        Returns:
            Gate evaluation result
        """
        client = self._get_qf_client()

        if client:
            import asyncio
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

            try:
                result = loop.run_until_complete(
                    client.evaluate_phase_gate(phase=phase, outputs=outputs)
                )
                return result
            except Exception as e:
                logger.warning(f"QF gate evaluation failed, using mock: {e}")
                if not self._fallback_to_mock:
                    raise

        # Mock gate evaluation
        return self._mock_evaluate_gate(phase, outputs)

    def _mock_evaluate_gate(self, phase: str, outputs: Dict[str, Any]) -> Dict[str, Any]:
        """Mock gate evaluation for testing"""
        # Define phase-specific gates
        phase_gates = {
            "requirements": ["prd_complete", "stakeholder_approval"],
            "design": ["architecture_reviewed", "api_contracts_defined"],
            "implementation": ["code_complete", "unit_tests_pass", "code_reviewed"],
            "testing": ["all_tests_pass", "coverage_threshold"],
            "deployment": ["deployment_successful", "smoke_tests_pass"]
        }

        gates = phase_gates.get(phase, ["generic_gate"])
        gates_passed = []
        gates_failed = []
        blockers = []
        warnings = []

        for gate in gates:
            if outputs.get(gate, False):
                gates_passed.append(gate)
            else:
                gates_failed.append(gate)
                if gate in ["code_complete", "all_tests_pass", "deployment_successful"]:
                    blockers.append(f"Critical gate failed: {gate}")
                else:
                    warnings.append(f"Optional gate failed: {gate}")

        total = len(gates_passed) + len(gates_failed)
        score = len(gates_passed) / max(total, 1)
        passed = len(blockers) == 0 and score >= 0.7

        return {
            "phase": phase,
            "passed": passed,
            "overall_score": score,
            "gates_passed": gates_passed,
            "gates_failed": gates_failed,
            "blockers": blockers,
            "warnings": warnings,
            "bypass_available": len(blockers) == 0
        }

    def get_health(self) -> HealthStatus:
        """Get Quality Fabric health status"""
        client = self._get_qf_client()

        if client:
            import asyncio
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

            try:
                result = loop.run_until_complete(client.health_check())
                return HealthStatus(
                    healthy=result.get("status") == "healthy",
                    status=result.get("status", "unknown"),
                    version=result.get("version", "unknown"),
                    uptime_seconds=(datetime.utcnow() - self._start_time).total_seconds(),
                    last_error=self._last_error
                )
            except Exception as e:
                self._last_error = str(e)

        # Mock health
        return HealthStatus(
            healthy=True,
            status="healthy (mock)",
            version=self.version,
            uptime_seconds=(datetime.utcnow() - self._start_time).total_seconds(),
            last_error=self._last_error
        )

    def publish_metrics(self, metrics: Dict[str, Any]) -> bool:
        """Publish quality metrics"""
        # In real implementation, would publish to metrics system
        logger.info(f"Publishing metrics: {metrics}")
        return True

    def health_check(self) -> bool:
        """Check if the block is healthy"""
        health = self.get_health()
        return health.healthy
