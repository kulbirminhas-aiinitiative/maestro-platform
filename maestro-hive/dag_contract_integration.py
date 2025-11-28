#!/usr/bin/env python3
"""
DAG Contract Integration

Integrates outcome-based contracts with the DAG workflow system.
Enables contract validation at phase gates to enforce quality requirements.

Key Features:
- Contract validation at phase exit gates
- Blocking on contract violations
- Integration with phase_gate_validator.py
- Quality Fabric SLO enforcement

Reference: BATCH5_WORKFLOW_SYSTEM_ANALYSIS.md, output_contracts.py
"""

import logging
from pathlib import Path
from typing import Dict, List, Any, Optional
import asyncio

from output_contracts import (
    OutputContract,
    ContractValidator,
    ContractRegistry,
    ContractValidationResult,
    QualityFabricIntegration
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DAGContractEnforcer:
    """
    Enforces contracts at DAG workflow phase gates

    Integrates with:
    - phase_gate_validator.py (for exit criteria)
    - dag_executor.py (for phase execution)
    - Quality Fabric (for SLO tracking)
    """

    def __init__(
        self,
        quality_fabric_url: str = "http://localhost:9800",
        enable_quality_fabric: bool = True
    ):
        self.contract_registry = ContractRegistry()
        self.contract_validator = ContractValidator()
        self.quality_fabric = QualityFabricIntegration(quality_fabric_url) if enable_quality_fabric else None

    async def validate_phase_output(
        self,
        phase: str,
        workflow_id: str,
        output_dir: Path
    ) -> ContractValidationResult:
        """
        Validate phase output against contract

        This is called at phase exit gates to enforce quality requirements.

        Args:
            phase: Phase name (e.g., "implementation", "deployment")
            workflow_id: Workflow ID
            output_dir: Directory containing phase outputs

        Returns:
            ContractValidationResult with pass/fail and violations
        """
        logger.info(f"🔒 Enforcing contract for phase: {phase} (workflow: {workflow_id})")

        # Get contract for phase
        contract = self.contract_registry.get_contract(phase)

        if not contract:
            logger.warning(f"⚠️  No contract registered for phase: {phase}, skipping validation")
            # Return a passing result if no contract
            return ContractValidationResult(
                contract_id="none",
                phase=phase,
                passed=True,
                requirements_met=0,
                requirements_total=0
            )

        # Validate contract
        result = await self.contract_validator.validate_contract(
            contract,
            output_dir
        )

        # Publish to Quality Fabric if enabled
        if self.quality_fabric:
            await self.quality_fabric.publish_contract_result(result, workflow_id)

        # Log result
        if result.passed:
            logger.info(f"✅ Contract validation PASSED for phase: {phase}")
        else:
            logger.error(f"❌ Contract validation FAILED for phase: {phase}")
            logger.error(f"   {len(result.blocking_violations)} blocking violation(s)")

            # Log violations
            for violation in result.blocking_violations:
                logger.error(f"   ⛔ {violation.violation_message}")

        return result

    def get_blocking_issues(self, result: ContractValidationResult) -> List[str]:
        """
        Extract blocking issues from contract validation result

        These are used by phase_gate_validator.py to block phase completion.
        """
        issues = []

        for violation in result.blocking_violations:
            issue = f"Contract violation: {violation.violation_message}"
            if violation.actual_value is not None and violation.expected_value is not None:
                issue += f" (actual: {violation.actual_value}, expected: {violation.expected_value})"
            issues.append(issue)

        return issues

    def get_recommendations(self, result: ContractValidationResult) -> List[str]:
        """Generate recommendations from contract violations"""
        recommendations = []

        if not result.passed:
            recommendations.append(
                f"❌ Contract validation failed for {result.phase} phase"
            )

            # Group by violation type
            build_violations = [v for v in result.blocking_violations if "build" in v.violation_message.lower()]
            stub_violations = [v for v in result.blocking_violations if "stub" in v.violation_message.lower()]
            functional_violations = [v for v in result.blocking_violations if "functional" in v.violation_message.lower()]

            if build_violations:
                recommendations.append("  → Fix build failures (npm install, npm build must succeed)")

            if stub_violations:
                recommendations.append("  → Replace stub implementations with working code")

            if functional_violations:
                recommendations.append("  → Implement functionality (remove 501 responses, add error handling)")

            # Add warning recommendations
            if result.warning_violations:
                recommendations.append(f"  ⚠️  {len(result.warning_violations)} warning(s) to address")

        return recommendations


# ============================================================================
# Integration Example for phase_gate_validator.py
# ============================================================================

class EnhancedPhaseGateValidator:
    """
    Example: Enhanced phase gate validator with contract enforcement

    This shows how to integrate contracts into the existing phase_gate_validator.py
    """

    def __init__(self):
        self.contract_enforcer = DAGContractEnforcer()

    async def validate_exit_criteria_with_contracts(
        self,
        phase: str,
        workflow_id: str,
        output_dir: Path,
        # ... other phase_gate_validator parameters
    ) -> Dict[str, Any]:
        """
        Enhanced exit criteria validation with contracts

        This augments the existing validate_exit_criteria() method.
        """

        # Step 1: Run existing validation
        # (from phase_gate_validator.py)
        existing_validation_passed = True  # Placeholder
        existing_blocking_issues = []

        # Step 2: Run contract validation (NEW)
        contract_result = await self.contract_enforcer.validate_phase_output(
            phase,
            workflow_id,
            output_dir
        )

        # Step 3: Combine results
        all_blocking_issues = existing_blocking_issues.copy()

        if not contract_result.passed:
            # Add contract violations as blocking issues
            contract_issues = self.contract_enforcer.get_blocking_issues(contract_result)
            all_blocking_issues.extend(contract_issues)

        # Step 4: Determine final status
        passed = len(all_blocking_issues) == 0

        return {
            "passed": passed,
            "blocking_issues": all_blocking_issues,
            "contract_result": contract_result.to_dict(),
            "recommendations": self.contract_enforcer.get_recommendations(contract_result)
        }


# ============================================================================
# Practical Integration Code
# ============================================================================

async def integrate_with_phase_gate_validator():
    """
    Shows how to add contract validation to existing phase_gate_validator.py

    Add this to phase_gate_validator.py:validate_exit_criteria()
    """

    code_example = '''
    # In phase_gate_validator.py, in validate_exit_criteria() method:

    async def validate_exit_criteria(
        self,
        phase: SDLCPhase,
        phase_exec: PhaseExecution,
        quality_thresholds: QualityThresholds,
        output_dir: Path
    ) -> PhaseGateResult:
        """Validate exit criteria for a phase"""

        # ... existing code ...

        # NEW: Add contract validation
        from dag_contract_integration import DAGContractEnforcer

        contract_enforcer = DAGContractEnforcer()
        contract_result = await contract_enforcer.validate_phase_output(
            phase.value,  # e.g., "implementation"
            str(output_dir),  # workflow directory
            output_dir
        )

        # NEW: Add contract violations as blocking issues
        if not contract_result.passed:
            contract_issues = contract_enforcer.get_blocking_issues(contract_result)
            blocking_issues.extend(contract_issues)

            # NEW: Add recommendations
            recommendations = contract_enforcer.get_recommendations(contract_result)
            for rec in recommendations:
                logger.warning(f"  💡 {rec}")

        # ... rest of existing code ...

        passed = len(blocking_issues) == 0

        return PhaseGateResult(
            passed=passed,
            # ... other fields ...
            blocking_issues=blocking_issues
        )
    '''

    print(code_example)


async def integrate_with_dag_executor():
    """
    Shows how to add contract validation to dag_executor.py

    Add this to dag_executor.py after node execution
    """

    code_example = '''
    # In dag_executor.py, after executing a phase node:

    async def _execute_single_node(self, dag, context, node_id):
        """Execute a single node"""

        # ... existing node execution code ...

        # NEW: If this is a phase node, validate contract
        if node.node_type == NodeType.PHASE:
            from dag_contract_integration import DAGContractEnforcer

            contract_enforcer = DAGContractEnforcer()

            # Get output directory from context
            output_dir = Path(f"/tmp/maestro_workflow/{context.workflow_id}")

            # Validate contract
            contract_result = await contract_enforcer.validate_phase_output(
                node_id,  # phase name
                context.workflow_id,
                output_dir
            )

            # If contract fails, mark node as failed
            if not contract_result.passed:
                logger.error(f"❌ Contract validation failed for {node_id}")
                logger.error(f"   {len(contract_result.blocking_violations)} blocking violations")

                # Set node state to FAILED
                node_state.status = NodeStatus.FAILED
                node_state.error_message = f"Contract validation failed: {len(contract_result.blocking_violations)} blocking violations"

                # Store contract result in node output
                result["contract_validation"] = contract_result.to_dict()

                return result  # Don't proceed with dependent nodes

        # ... rest of existing code ...
    '''

    print(code_example)


# ============================================================================
# CI/CD Integration
# ============================================================================

class CIContractEnforcer:
    """
    Enforces contracts in CI/CD pipeline

    Blocks merges if contracts fail (per agent's input)
    """

    def __init__(self):
        self.contract_enforcer = DAGContractEnforcer()

    async def check_pr_contracts(
        self,
        pr_id: str,
        workflow_dir: str
    ) -> Dict[str, Any]:
        """
        Check if PR meets contract requirements

        Returns:
            {
                "can_merge": bool,
                "failed_contracts": [...],
                "blocking_issues": [...]
            }
        """

        # Check all phase contracts
        phases_to_check = ["implementation", "testing", "deployment"]
        failed_contracts = []
        all_blocking_issues = []

        for phase in phases_to_check:
            result = await self.contract_enforcer.validate_phase_output(
                phase,
                pr_id,
                Path(workflow_dir)
            )

            if not result.passed:
                failed_contracts.append(phase)
                issues = self.contract_enforcer.get_blocking_issues(result)
                all_blocking_issues.extend(issues)

        can_merge = len(failed_contracts) == 0

        return {
            "can_merge": can_merge,
            "failed_contracts": failed_contracts,
            "blocking_issues": all_blocking_issues,
            "pr_id": pr_id
        }

    async def generate_pr_comment(
        self,
        pr_check_result: Dict[str, Any]
    ) -> str:
        """Generate PR comment with contract status"""

        if pr_check_result["can_merge"]:
            return f"""
## ✅ Contract Validation Passed

All phase contracts meet requirements. PR is ready to merge.

**Contracts Checked**: implementation, testing, deployment
**Status**: All passed
            """
        else:
            failed = pr_check_result["failed_contracts"]
            issues = pr_check_result["blocking_issues"]

            comment = f"""
## ❌ Contract Validation Failed

This PR cannot be merged due to contract violations.

**Failed Contracts**: {', '.join(failed)}

**Blocking Issues**:
"""
            for issue in issues[:5]:  # Show first 5
                comment += f"\n- {issue}"

            comment += f"""

**To Fix**:
1. Address blocking issues listed above
2. Re-run validation: `python output_contracts.py <workflow_dir> <phase>`
3. Push fixes and re-run CI
            """

            return comment


# ============================================================================
# Quality Fabric Integration
# ============================================================================

async def wire_quality_fabric_to_ci():
    """
    Wire Quality Fabric SLOs to CI to block merges (per agent's input)

    This shows how to integrate with CI/CD systems like GitHub Actions, GitLab CI, etc.
    """

    github_action_example = '''
    # .github/workflows/contract-validation.yml

    name: Contract Validation

    on:
      pull_request:
        branches: [main, develop]

    jobs:
      validate-contracts:
        runs-on: ubuntu-latest
        steps:
          - uses: actions/checkout@v2

          - name: Setup Python
            uses: actions/setup-python@v2
            with:
              python-version: '3.11'

          - name: Install dependencies
            run: |
              pip install -r requirements.txt

          - name: Validate Implementation Contract
            run: |
              python output_contracts.py ${{ github.workspace }} implementation
            continue-on-error: false  # Block on failure

          - name: Validate Deployment Contract
            run: |
              python output_contracts.py ${{ github.workspace }} deployment
            continue-on-error: false  # Block on failure

          - name: Post PR Comment
            if: failure()
            uses: actions/github-script@v6
            with:
              script: |
                github.rest.issues.createComment({
                  issue_number: context.issue.number,
                  owner: context.repo.owner,
                  repo: context.repo.repo,
                  body: '❌ Contract validation failed. See workflow logs for details.'
                })
    '''

    print(github_action_example)


# ============================================================================
# CLI Interface
# ============================================================================

if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("DAG Contract Integration")
        print("=" * 80)
        print("\nIntegration Examples:")
        print("  python dag_contract_integration.py phase_gate_validator")
        print("  python dag_contract_integration.py dag_executor")
        print("  python dag_contract_integration.py ci_cd")
        sys.exit(1)

    integration_type = sys.argv[1]

    async def main():
        if integration_type == "phase_gate_validator":
            print("\n" + "=" * 80)
            print("Integration with phase_gate_validator.py")
            print("=" * 80 + "\n")
            await integrate_with_phase_gate_validator()

        elif integration_type == "dag_executor":
            print("\n" + "=" * 80)
            print("Integration with dag_executor.py")
            print("=" * 80 + "\n")
            await integrate_with_dag_executor()

        elif integration_type == "ci_cd":
            print("\n" + "=" * 80)
            print("CI/CD Integration (Wire Quality Fabric to CI)")
            print("=" * 80 + "\n")
            await wire_quality_fabric_to_ci()

        else:
            print(f"Unknown integration type: {integration_type}")
            sys.exit(1)

    asyncio.run(main())
