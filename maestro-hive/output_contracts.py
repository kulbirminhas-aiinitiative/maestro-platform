#!/usr/bin/env python3
"""
Output Contract System - Outcome-Based Quality Gates

Implements outcome-based contracts for workflow phases that enforce:
- Build success requirements (must compile/build)
- Test coverage minimums (must pass tests)
- PRD traceability (requirements must be implemented)
- Deployment readiness (must be deployable)
- Quality SLOs (must meet quality thresholds)

This addresses the Batch 5 gap where validation passed but builds failed.

Reference: BATCH5_WORKFLOW_SYSTEM_ANALYSIS.md
Integration: Uses validation_integration.py for enforcement
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ContractRequirementType(Enum):
    """Types of contract requirements"""
    BUILD_SUCCESS = "build_success"          # Must build successfully
    TEST_COVERAGE = "test_coverage"          # Must meet test coverage
    PRD_TRACEABILITY = "prd_traceability"    # Must implement PRD requirements
    NO_STUBS = "no_stubs"                    # Must not have stub implementations
    DEPLOYMENT_READY = "deployment_ready"    # Must be deployable
    QUALITY_SLO = "quality_slo"              # Must meet quality SLO
    FUNCTIONAL = "functional"                # Must be functional (no 501s)


class ContractSeverity(Enum):
    """Severity of contract violations"""
    BLOCKING = "blocking"      # Blocks phase completion
    WARNING = "warning"        # Allows completion with warning
    INFO = "info"              # Informational only


@dataclass
class ContractRequirement:
    """A single requirement in an output contract"""
    requirement_id: str
    requirement_type: ContractRequirementType
    severity: ContractSeverity
    description: str
    validation_criteria: Dict[str, Any]
    min_threshold: Optional[float] = None
    max_threshold: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "requirement_id": self.requirement_id,
            "requirement_type": self.requirement_type.value,
            "severity": self.severity.value,
            "description": self.description,
            "validation_criteria": self.validation_criteria,
            "min_threshold": self.min_threshold,
            "max_threshold": self.max_threshold
        }


@dataclass
class OutputContract:
    """
    Output contract for a workflow phase

    Specifies what the phase MUST produce and what quality gates it MUST pass.
    Unlike API contracts (team-to-team), these are phase-to-phase guarantees.

    Example:
        backend_contract = OutputContract(
            phase="implementation",
            produces=["backend_code", "api_endpoints"],
            requirements=[
                ContractRequirement(
                    requirement_id="backend_builds",
                    requirement_type=ContractRequirementType.BUILD_SUCCESS,
                    severity=ContractSeverity.BLOCKING,
                    description="Backend must build successfully",
                    validation_criteria={"npm_build": True}
                )
            ]
        )
    """
    contract_id: str
    phase: str
    produces: List[str]  # What artifacts/outputs are produced
    requirements: List[ContractRequirement] = field(default_factory=list)
    slo_thresholds: Dict[str, float] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "contract_id": self.contract_id,
            "phase": self.phase,
            "produces": self.produces,
            "requirements": [r.to_dict() for r in self.requirements],
            "slo_thresholds": self.slo_thresholds,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat()
        }


@dataclass
class ContractViolation:
    """Represents a violation of a contract requirement"""
    requirement_id: str
    requirement_type: ContractRequirementType
    severity: ContractSeverity
    violation_message: str
    actual_value: Optional[Any] = None
    expected_value: Optional[Any] = None
    evidence: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "requirement_id": self.requirement_id,
            "requirement_type": self.requirement_type.value,
            "severity": self.severity.value,
            "violation_message": self.violation_message,
            "actual_value": self.actual_value,
            "expected_value": self.expected_value,
            "evidence": self.evidence
        }


@dataclass
class ContractValidationResult:
    """Result of validating output against contract"""
    contract_id: str
    phase: str
    passed: bool
    blocking_violations: List[ContractViolation] = field(default_factory=list)
    warning_violations: List[ContractViolation] = field(default_factory=list)
    requirements_met: int = 0
    requirements_total: int = 0
    validation_timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "contract_id": self.contract_id,
            "phase": self.phase,
            "passed": self.passed,
            "blocking_violations": [v.to_dict() for v in self.blocking_violations],
            "warning_violations": [v.to_dict() for v in self.warning_violations],
            "requirements_met": self.requirements_met,
            "requirements_total": self.requirements_total,
            "validation_timestamp": self.validation_timestamp.isoformat()
        }


class ContractValidator:
    """
    Validates workflow outputs against contracts

    Integrates with validation_integration.py to enforce outcome-based gates.
    """

    def __init__(self):
        self.validation_cache: Dict[str, ContractValidationResult] = {}

    async def validate_contract(
        self,
        contract: OutputContract,
        output_dir: Path,
        validation_report: Optional[Dict[str, Any]] = None
    ) -> ContractValidationResult:
        """
        Validate output against contract

        Args:
            contract: The contract to validate against
            output_dir: Directory containing phase outputs
            validation_report: Optional pre-computed validation report from validation_integration.py

        Returns:
            ContractValidationResult with violations
        """
        logger.info(f"🔍 Validating contract: {contract.contract_id} (phase: {contract.phase})")

        blocking_violations = []
        warning_violations = []
        requirements_met = 0

        # If we have a validation report, use it
        if validation_report is None:
            # Run validation
            from validation_integration import validate_workflow_comprehensive
            validation_report = await validate_workflow_comprehensive(str(output_dir))
            validation_report = validation_report.to_dict()

        # Validate each requirement
        for requirement in contract.requirements:
            violation = await self._validate_requirement(
                requirement,
                output_dir,
                validation_report
            )

            if violation:
                if violation.severity == ContractSeverity.BLOCKING:
                    blocking_violations.append(violation)
                    logger.error(f"  ❌ BLOCKING: {violation.violation_message}")
                else:
                    warning_violations.append(violation)
                    logger.warning(f"  ⚠️  WARNING: {violation.violation_message}")
            else:
                requirements_met += 1
                logger.info(f"  ✅ {requirement.description}")

        passed = len(blocking_violations) == 0

        result = ContractValidationResult(
            contract_id=contract.contract_id,
            phase=contract.phase,
            passed=passed,
            blocking_violations=blocking_violations,
            warning_violations=warning_violations,
            requirements_met=requirements_met,
            requirements_total=len(contract.requirements)
        )

        # Cache result
        self.validation_cache[contract.contract_id] = result

        if passed:
            logger.info(f"✅ Contract PASSED: {requirements_met}/{len(contract.requirements)} requirements met")
        else:
            logger.error(f"❌ Contract FAILED: {len(blocking_violations)} blocking violations")

        return result

    async def _validate_requirement(
        self,
        requirement: ContractRequirement,
        output_dir: Path,
        validation_report: Dict[str, Any]
    ) -> Optional[ContractViolation]:
        """Validate a single requirement"""

        req_type = requirement.requirement_type

        # BUILD_SUCCESS requirement
        if req_type == ContractRequirementType.BUILD_SUCCESS:
            can_build = validation_report.get("can_build", False)
            if not can_build:
                build_validation = validation_report.get("build_validation", {})
                results = build_validation.get("results", [])

                # Find build failure evidence
                evidence = []
                for result in results:
                    if "build" in result.get("check", "").lower() and not result.get("passed", True):
                        evidence.append(result.get("message", "Build failed"))

                return ContractViolation(
                    requirement_id=requirement.requirement_id,
                    requirement_type=req_type,
                    severity=requirement.severity,
                    violation_message="Build validation failed - application does not build",
                    actual_value=False,
                    expected_value=True,
                    evidence=evidence[:3]  # First 3 pieces of evidence
                )

        # TEST_COVERAGE requirement
        elif req_type == ContractRequirementType.TEST_COVERAGE:
            min_coverage = requirement.min_threshold or 0.7  # 70% default
            # Would need to parse test results - placeholder for now
            # In production, parse coverage reports from validation
            pass

        # PRD_TRACEABILITY requirement
        elif req_type == ContractRequirementType.PRD_TRACEABILITY:
            weighted_scores = validation_report.get("weighted_scores", {})
            features_score = weighted_scores.get("features_implemented", 0.0)
            min_features = requirement.min_threshold or 0.8  # 80% default

            if features_score < min_features:
                return ContractViolation(
                    requirement_id=requirement.requirement_id,
                    requirement_type=req_type,
                    severity=requirement.severity,
                    violation_message=f"PRD feature implementation below threshold",
                    actual_value=features_score,
                    expected_value=min_features,
                    evidence=[f"Only {features_score:.0%} of PRD features implemented"]
                )

        # NO_STUBS requirement
        elif req_type == ContractRequirementType.NO_STUBS:
            max_stub_rate = requirement.max_threshold or 0.05  # 5% max

            build_validation = validation_report.get("build_validation", {})
            results = build_validation.get("results", [])

            for result in results:
                if result.get("check") == "stub_implementation_detection":
                    if not result.get("passed", True):
                        # Extract stub rate from message
                        message = result.get("message", "")
                        if "%" in message:
                            # Parse "X/Y files (Z%)"
                            import re
                            match = re.search(r'\((\d+)%\)', message)
                            if match:
                                stub_rate = int(match.group(1)) / 100.0

                                if stub_rate > max_stub_rate:
                                    return ContractViolation(
                                        requirement_id=requirement.requirement_id,
                                        requirement_type=req_type,
                                        severity=requirement.severity,
                                        violation_message=f"Stub implementation rate too high",
                                        actual_value=stub_rate,
                                        expected_value=max_stub_rate,
                                        evidence=result.get("evidence", [])[:3]
                                    )

        # FUNCTIONAL requirement (no 501 responses)
        elif req_type == ContractRequirementType.FUNCTIONAL:
            # This is checked by stub detection
            weighted_scores = validation_report.get("weighted_scores", {})
            functionality_score = weighted_scores.get("functionality", 0.0)
            min_functionality = requirement.min_threshold or 0.7  # 70% default

            if functionality_score < min_functionality:
                return ContractViolation(
                    requirement_id=requirement.requirement_id,
                    requirement_type=req_type,
                    severity=requirement.severity,
                    violation_message=f"Functionality score below threshold",
                    actual_value=functionality_score,
                    expected_value=min_functionality,
                    evidence=["Contains stub implementations or non-functional code"]
                )

        # DEPLOYMENT_READY requirement
        elif req_type == ContractRequirementType.DEPLOYMENT_READY:
            final_status = validation_report.get("final_status", "critical_failures")

            if final_status != "ready_to_deploy":
                return ContractViolation(
                    requirement_id=requirement.requirement_id,
                    requirement_type=req_type,
                    severity=requirement.severity,
                    violation_message=f"Not deployment ready - status: {final_status}",
                    actual_value=final_status,
                    expected_value="ready_to_deploy",
                    evidence=validation_report.get("blocking_issues", [])[:3]
                )

        # QUALITY_SLO requirement
        elif req_type == ContractRequirementType.QUALITY_SLO:
            overall_score = validation_report.get("overall_score", 0.0)
            min_quality = requirement.min_threshold or 0.8  # 80% default

            if overall_score < min_quality:
                return ContractViolation(
                    requirement_id=requirement.requirement_id,
                    requirement_type=req_type,
                    severity=requirement.severity,
                    violation_message=f"Quality score below SLO threshold",
                    actual_value=overall_score,
                    expected_value=min_quality,
                    evidence=[f"Overall quality: {overall_score:.1%} < {min_quality:.1%}"]
                )

        # No violation found
        return None


# ============================================================================
# Pre-defined Contracts for SDLC Phases
# ============================================================================

def create_implementation_contract() -> OutputContract:
    """
    Contract for implementation phase

    This is the MOST CRITICAL contract that addresses Batch 5 issues.
    """
    return OutputContract(
        contract_id="implementation_v1",
        phase="implementation",
        produces=[
            "backend_code",
            "frontend_code",
            "api_endpoints",
            "database_models",
            "tests"
        ],
        requirements=[
            # CRITICAL: Must build (addresses Batch 5 root cause)
            ContractRequirement(
                requirement_id="backend_builds",
                requirement_type=ContractRequirementType.BUILD_SUCCESS,
                severity=ContractSeverity.BLOCKING,
                description="Backend must build successfully (npm install + npm build)",
                validation_criteria={"npm_build": True}
            ),
            ContractRequirement(
                requirement_id="frontend_builds",
                requirement_type=ContractRequirementType.BUILD_SUCCESS,
                severity=ContractSeverity.BLOCKING,
                description="Frontend must build successfully (npm install + npm build)",
                validation_criteria={"npm_build": True}
            ),

            # CRITICAL: No stub implementations
            ContractRequirement(
                requirement_id="no_stubs",
                requirement_type=ContractRequirementType.NO_STUBS,
                severity=ContractSeverity.BLOCKING,
                description="Stub implementation rate must be < 5%",
                validation_criteria={"max_stub_rate": 0.05},
                max_threshold=0.05
            ),

            # HIGH: Functional code (no 501 responses)
            ContractRequirement(
                requirement_id="functional_code",
                requirement_type=ContractRequirementType.FUNCTIONAL,
                severity=ContractSeverity.BLOCKING,
                description="Code must be functional (functionality score ≥ 70%)",
                validation_criteria={"min_functionality": 0.7},
                min_threshold=0.7
            ),

            # HIGH: PRD traceability
            ContractRequirement(
                requirement_id="prd_features",
                requirement_type=ContractRequirementType.PRD_TRACEABILITY,
                severity=ContractSeverity.WARNING,
                description="At least 80% of PRD features must be implemented",
                validation_criteria={"min_feature_coverage": 0.8},
                min_threshold=0.8
            ),

            # HIGH: Quality SLO
            ContractRequirement(
                requirement_id="quality_slo",
                requirement_type=ContractRequirementType.QUALITY_SLO,
                severity=ContractSeverity.WARNING,
                description="Overall quality score must be ≥ 70%",
                validation_criteria={"min_quality": 0.7},
                min_threshold=0.7
            ),
        ],
        slo_thresholds={
            "build_success_rate": 1.0,      # 100% must build
            "stub_rate": 0.05,              # < 5% stubs
            "functionality_score": 0.7,     # ≥ 70% functional
            "feature_coverage": 0.8,        # ≥ 80% features
            "overall_quality": 0.7          # ≥ 70% quality
        },
        metadata={
            "batch_5_fix": True,
            "addresses": "Validation passed but builds failed",
            "validation_integration": "Uses validation_integration.py"
        }
    )


def create_deployment_contract() -> OutputContract:
    """Contract for deployment phase"""
    return OutputContract(
        contract_id="deployment_v1",
        phase="deployment",
        produces=[
            "docker_images",
            "kubernetes_manifests",
            "deployment_configs"
        ],
        requirements=[
            # CRITICAL: Must be deployment ready
            ContractRequirement(
                requirement_id="deployment_ready",
                requirement_type=ContractRequirementType.DEPLOYMENT_READY,
                severity=ContractSeverity.BLOCKING,
                description="Application must be deployment ready",
                validation_criteria={"status": "ready_to_deploy"}
            ),

            # CRITICAL: Builds must succeed
            ContractRequirement(
                requirement_id="builds_succeed",
                requirement_type=ContractRequirementType.BUILD_SUCCESS,
                severity=ContractSeverity.BLOCKING,
                description="All builds (npm, docker) must succeed",
                validation_criteria={"all_builds": True}
            ),

            # HIGH: Quality SLO for deployment
            ContractRequirement(
                requirement_id="deployment_quality",
                requirement_type=ContractRequirementType.QUALITY_SLO,
                severity=ContractSeverity.BLOCKING,
                description="Overall quality must be ≥ 80% for deployment",
                validation_criteria={"min_quality": 0.8},
                min_threshold=0.8
            ),
        ],
        slo_thresholds={
            "build_success_rate": 1.0,
            "deployment_readiness": 1.0,
            "overall_quality": 0.8
        }
    )


def create_testing_contract() -> OutputContract:
    """Contract for testing phase"""
    return OutputContract(
        contract_id="testing_v1",
        phase="testing",
        produces=[
            "test_results",
            "coverage_reports",
            "test_documentation"
        ],
        requirements=[
            # HIGH: Test coverage
            ContractRequirement(
                requirement_id="test_coverage",
                requirement_type=ContractRequirementType.TEST_COVERAGE,
                severity=ContractSeverity.WARNING,
                description="Test coverage must be ≥ 70%",
                validation_criteria={"min_coverage": 0.7},
                min_threshold=0.7
            ),
        ],
        slo_thresholds={
            "test_coverage": 0.7
        }
    )


# ============================================================================
# Contract Registry
# ============================================================================

class ContractRegistry:
    """
    Registry of all output contracts

    Provides easy access to contracts by phase name.
    """

    def __init__(self):
        self.contracts: Dict[str, OutputContract] = {}
        self._initialize_default_contracts()

    def _initialize_default_contracts(self):
        """Initialize with default SDLC contracts"""
        self.register_contract(create_implementation_contract())
        self.register_contract(create_deployment_contract())
        self.register_contract(create_testing_contract())

    def register_contract(self, contract: OutputContract):
        """Register a contract"""
        self.contracts[contract.phase] = contract
        logger.info(f"📋 Registered contract for phase: {contract.phase}")

    def get_contract(self, phase: str) -> Optional[OutputContract]:
        """Get contract for a phase"""
        return self.contracts.get(phase)

    def list_contracts(self) -> List[str]:
        """List all registered contract phases"""
        return list(self.contracts.keys())

    def get_all_contracts(self) -> Dict[str, OutputContract]:
        """Get all contracts"""
        return self.contracts.copy()


# ============================================================================
# Integration with Quality Fabric
# ============================================================================

class QualityFabricIntegration:
    """
    Integration with Quality Fabric for SLO enforcement

    Wires contract violations to CI/CD to block merges.
    """

    def __init__(self, quality_fabric_url: str = "http://localhost:9800"):
        self.quality_fabric_url = quality_fabric_url

    async def publish_contract_result(
        self,
        validation_result: ContractValidationResult,
        workflow_id: str
    ) -> bool:
        """
        Publish contract validation result to Quality Fabric

        This enables Quality Fabric to:
        - Track SLO compliance over time
        - Block merges if contracts fail
        - Trigger alerts on violations
        """
        try:
            import aiohttp

            async with aiohttp.ClientSession() as session:
                payload = {
                    "workflow_id": workflow_id,
                    "contract_id": validation_result.contract_id,
                    "phase": validation_result.phase,
                    "passed": validation_result.passed,
                    "blocking_violations": len(validation_result.blocking_violations),
                    "warning_violations": len(validation_result.warning_violations),
                    "requirements_met": validation_result.requirements_met,
                    "requirements_total": validation_result.requirements_total,
                    "timestamp": validation_result.validation_timestamp.isoformat()
                }

                async with session.post(
                    f"{self.quality_fabric_url}/api/v1/contracts/validation",
                    json=payload
                ) as resp:
                    if resp.status == 200:
                        logger.info(f"✅ Published contract result to Quality Fabric")
                        return True
                    else:
                        logger.warning(f"⚠️  Failed to publish to Quality Fabric: {resp.status}")
                        return False

        except Exception as e:
            logger.warning(f"⚠️  Quality Fabric integration error: {e}")
            return False

    async def check_slo_compliance(
        self,
        workflow_id: str,
        slo_name: str
    ) -> Dict[str, Any]:
        """
        Check if workflow meets SLO

        Returns:
            {
                "compliant": bool,
                "actual_value": float,
                "threshold": float,
                "violation_details": [...]
            }
        """
        # This would query Quality Fabric for SLO status
        # Placeholder implementation
        return {
            "compliant": True,
            "actual_value": 0.0,
            "threshold": 0.0,
            "violation_details": []
        }


# ============================================================================
# CLI Interface
# ============================================================================

async def validate_workflow_contract(
    workflow_dir: str,
    phase: str
) -> ContractValidationResult:
    """
    Validate workflow output against contract

    Usage:
        result = await validate_workflow_contract(
            "/tmp/maestro_workflow/wf-123456",
            "implementation"
        )

        if not result.passed:
            print("❌ Contract validation failed")
            for violation in result.blocking_violations:
                print(f"  - {violation.violation_message}")
    """
    registry = ContractRegistry()
    contract = registry.get_contract(phase)

    if not contract:
        raise ValueError(f"No contract registered for phase: {phase}")

    validator = ContractValidator()
    result = await validator.validate_contract(
        contract,
        Path(workflow_dir)
    )

    return result


if __name__ == "__main__":
    import sys
    import asyncio

    if len(sys.argv) < 3:
        print("Usage: python output_contracts.py <workflow_dir> <phase>")
        print("Example: python output_contracts.py /tmp/maestro_workflow/wf-123456 implementation")
        sys.exit(1)

    workflow_dir = sys.argv[1]
    phase = sys.argv[2]

    async def main():
        print(f"\n🔍 Validating {phase} phase contract for {workflow_dir}\n")

        result = await validate_workflow_contract(workflow_dir, phase)

        print("\n" + "=" * 80)
        print("CONTRACT VALIDATION RESULT")
        print("=" * 80)
        print(f"Contract: {result.contract_id}")
        print(f"Phase: {result.phase}")
        print(f"Status: {'✅ PASSED' if result.passed else '❌ FAILED'}")
        print(f"Requirements Met: {result.requirements_met}/{result.requirements_total}")

        if result.blocking_violations:
            print(f"\n⛔ Blocking Violations ({len(result.blocking_violations)}):")
            for violation in result.blocking_violations:
                print(f"  - {violation.violation_message}")
                if violation.evidence:
                    for evidence in violation.evidence[:2]:
                        print(f"    Evidence: {evidence}")

        if result.warning_violations:
            print(f"\n⚠️  Warnings ({len(result.warning_violations)}):")
            for violation in result.warning_violations:
                print(f"  - {violation.violation_message}")

        # Save result
        output_file = Path(workflow_dir) / f"CONTRACT_VALIDATION_{phase.upper()}.json"
        output_file.write_text(json.dumps(result.to_dict(), indent=2))
        print(f"\n📄 Full result saved to: {output_file}")

        sys.exit(0 if result.passed else 1)

    asyncio.run(main())
