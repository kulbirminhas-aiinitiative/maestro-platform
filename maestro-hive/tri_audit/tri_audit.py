"""
Tri-Modal Convergence Audit

Aggregates verdicts from DDE, BDV, and ACC streams to make deployment decisions.
Deploy to production ONLY when: DDE ✅ AND BDV ✅ AND ACC ✅

This is the convergence layer that ensures comprehensive validation with
non-overlapping blind spots across all three validation dimensions.
"""

from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum
from typing import Dict, Any, List, Optional
import json
from pathlib import Path


class TriModalVerdict(Enum):
    """Tri-modal audit verdict"""
    ALL_PASS = "all_pass"  # All three audits passed - safe to deploy
    DESIGN_GAP = "design_gap"  # DDE + ACC pass, BDV fails - wrong thing built
    ARCHITECTURAL_EROSION = "architectural_erosion"  # DDE + BDV pass, ACC fails - technical debt
    PROCESS_ISSUE = "process_issue"  # BDV + ACC pass, DDE fails - pipeline issue
    SYSTEMIC_FAILURE = "systemic_failure"  # All three fail - halt everything
    MIXED_FAILURE = "mixed_failure"  # Other combinations


@dataclass
class DDEAuditResult:
    """Results from DDE (Dependency-Driven Execution) audit"""
    iteration_id: str
    passed: bool
    score: float  # 0.0 to 1.0
    all_nodes_complete: bool
    blocking_gates_passed: bool
    artifacts_stamped: bool
    lineage_intact: bool
    contracts_locked: bool
    details: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class BDVAuditResult:
    """Results from BDV (Behavior-Driven Validation) audit"""
    iteration_id: str
    passed: bool
    total_scenarios: int
    passed_scenarios: int
    failed_scenarios: int
    flake_rate: float  # 0.0 to 1.0
    contract_mismatches: List[str]
    critical_journeys_covered: bool
    details: Dict[str, Any]

    @property
    def all_scenarios_passed(self) -> bool:
        return self.failed_scenarios == 0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ACCAuditResult:
    """Results from ACC (Architectural Conformance Checking) audit"""
    iteration_id: str
    passed: bool
    blocking_violations: int
    warning_violations: int
    cycles: List[List[str]]
    coupling_scores: Dict[str, Dict[str, float]]
    suppressions_have_adrs: bool
    coupling_within_limits: bool
    no_new_cycles: bool
    details: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        result = asdict(self)
        # Convert enum values if needed
        return result


@dataclass
class TriAuditResult:
    """Aggregated result from tri-modal audit"""
    iteration_id: str
    verdict: TriModalVerdict
    timestamp: str
    dde_passed: bool
    bdv_passed: bool
    acc_passed: bool
    can_deploy: bool
    diagnosis: str
    recommendations: List[str]
    dde_details: Dict[str, Any]
    bdv_details: Dict[str, Any]
    acc_details: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        result = asdict(self)
        result['verdict'] = self.verdict.value
        return result


def tri_modal_audit(
    iteration_id: str,
    dde_result: Optional[DDEAuditResult] = None,
    bdv_result: Optional[BDVAuditResult] = None,
    acc_result: Optional[ACCAuditResult] = None
) -> TriAuditResult:
    """
    Run tri-modal convergence audit.

    Aggregates verdicts from DDE, BDV, and ACC.
    Deploy ONLY if all three pass.

    Args:
        iteration_id: Iteration identifier
        dde_result: DDE audit result (optional - will be loaded if not provided)
        bdv_result: BDV audit result (optional - will be loaded if not provided)
        acc_result: ACC audit result (optional - will be loaded if not provided)

    Returns:
        TriAuditResult with aggregated verdict
    """
    # Load results if not provided
    if dde_result is None:
        dde_result = load_dde_audit(iteration_id)
    if bdv_result is None:
        bdv_result = load_bdv_audit(iteration_id)
    if acc_result is None:
        acc_result = load_acc_audit(iteration_id)

    # Extract pass/fail
    dde_pass = dde_result.passed if dde_result else False
    bdv_pass = bdv_result.passed if bdv_result else False
    acc_pass = acc_result.passed if acc_result else False

    # Determine verdict
    verdict = determine_verdict(dde_pass, bdv_pass, acc_pass)

    # Generate diagnosis
    diagnosis = diagnose_failure(verdict, dde_pass, bdv_pass, acc_pass)

    # Generate recommendations
    recommendations = generate_recommendations(
        verdict,
        dde_result,
        bdv_result,
        acc_result
    )

    # Create result
    result = TriAuditResult(
        iteration_id=iteration_id,
        verdict=verdict,
        timestamp=datetime.utcnow().isoformat() + "Z",
        dde_passed=dde_pass,
        bdv_passed=bdv_pass,
        acc_passed=acc_pass,
        can_deploy=verdict == TriModalVerdict.ALL_PASS,
        diagnosis=diagnosis,
        recommendations=recommendations,
        dde_details=dde_result.to_dict() if dde_result else {},
        bdv_details=bdv_result.to_dict() if bdv_result else {},
        acc_details=acc_result.to_dict() if acc_result else {}
    )

    # Save result
    save_tri_audit_result(result)

    return result


def determine_verdict(dde: bool, bdv: bool, acc: bool) -> TriModalVerdict:
    """
    Determine tri-modal verdict from individual results.

    Args:
        dde: DDE audit passed
        bdv: BDV audit passed
        acc: ACC audit passed

    Returns:
        TriModalVerdict enum value
    """
    if dde and bdv and acc:
        return TriModalVerdict.ALL_PASS

    elif dde and not bdv and acc:
        # Built right, architecturally sound, but wrong thing
        return TriModalVerdict.DESIGN_GAP

    elif dde and bdv and not acc:
        # Built right, does what users want, but architectural violations
        return TriModalVerdict.ARCHITECTURAL_EROSION

    elif not dde and bdv and acc:
        # Does what users want, architecturally sound, but process issues
        return TriModalVerdict.PROCESS_ISSUE

    elif not dde and not bdv and not acc:
        # Everything failed - systemic issues
        return TriModalVerdict.SYSTEMIC_FAILURE

    else:
        # Other combinations
        return TriModalVerdict.MIXED_FAILURE


def diagnose_failure(
    verdict: TriModalVerdict,
    dde: bool,
    bdv: bool,
    acc: bool
) -> str:
    """
    Generate human-readable diagnosis based on verdict.

    Args:
        verdict: TriModalVerdict
        dde: DDE passed
        bdv: BDV passed
        acc: ACC passed

    Returns:
        Diagnosis string
    """
    diagnoses = {
        TriModalVerdict.ALL_PASS: (
            "✅ All audits passed. Safe to deploy.\n\n"
            "All three validation streams have given approval:\n"
            "- DDE: Execution process compliant\n"
            "- BDV: User behavior validated\n"
            "- ACC: Architecture conformant"
        ),

        TriModalVerdict.DESIGN_GAP: (
            "⚠️ DESIGN GAP DETECTED\n\n"
            "DDE and ACC passed, but BDV failed.\n\n"
            "This indicates a gap between implementation and business intent. "
            "The system is technically correct and architecturally sound, "
            "but doesn't meet user needs or acceptance criteria.\n\n"
            "Action: Revisit requirements and contracts. Re-align implementation "
            "with business goals. The technical quality is good, but you've "
            "built the wrong thing."
        ),

        TriModalVerdict.ARCHITECTURAL_EROSION: (
            "⚠️ ARCHITECTURAL EROSION DETECTED\n\n"
            "DDE and BDV passed, but ACC failed.\n\n"
            "This indicates architectural violations despite functional correctness. "
            "The system works as users expect and the process is compliant, "
            "but the codebase has structural issues.\n\n"
            "Action: Refactor to fix architectural violations before deploy. "
            "Do not accept technical debt. Long-term maintainability is at risk."
        ),

        TriModalVerdict.PROCESS_ISSUE: (
            "⚠️ PROCESS ISSUE DETECTED\n\n"
            "BDV and ACC passed, but DDE failed.\n\n"
            "This indicates process or pipeline issues. The implementation "
            "meets user needs and is architecturally sound, but quality gates "
            "or execution compliance checks are failing.\n\n"
            "Action: Tune quality gates, fix pipeline configuration, or address "
            "missing artifacts/contracts."
        ),

        TriModalVerdict.SYSTEMIC_FAILURE: (
            "❌ SYSTEMIC FAILURE\n\n"
            "All three audits failed.\n\n"
            "This indicates systemic issues across execution, behavior, and architecture. "
            "The scope may be too large, requirements unclear, or the team needs support.\n\n"
            "Action: HALT. Conduct retrospective. Reduce scope. Get help."
        ),

        TriModalVerdict.MIXED_FAILURE: (
            f"⚠️ MIXED FAILURE\n\n"
            f"Multiple failures detected: DDE={dde}, BDV={bdv}, ACC={acc}\n\n"
            f"Review each audit report for specific issues."
        )
    }

    return diagnoses.get(verdict, "Unknown verdict")


def generate_recommendations(
    verdict: TriModalVerdict,
    dde_result: Optional[DDEAuditResult],
    bdv_result: Optional[BDVAuditResult],
    acc_result: Optional[ACCAuditResult]
) -> List[str]:
    """
    Generate actionable recommendations based on failures.

    Args:
        verdict: TriModalVerdict
        dde_result: DDE audit result
        bdv_result: BDV audit result
        acc_result: ACC audit result

    Returns:
        List of recommendation strings
    """
    recommendations = []

    # DDE recommendations
    if dde_result and not dde_result.passed:
        if not dde_result.all_nodes_complete:
            recommendations.append(
                "Complete all DDE nodes in the execution manifest"
            )
        if not dde_result.blocking_gates_passed:
            recommendations.append(
                "Fix failed quality gates (coverage, lint, security scans)"
            )
        if not dde_result.artifacts_stamped:
            recommendations.append(
                "Ensure all artifacts are properly stamped with metadata"
            )
        if not dde_result.contracts_locked:
            recommendations.append(
                "Lock all interface contracts before dependent work begins"
            )

    # BDV recommendations
    if bdv_result and not bdv_result.passed:
        if bdv_result.failed_scenarios > 0:
            recommendations.append(
                f"Fix {bdv_result.failed_scenarios} failing BDV scenarios"
            )
        if bdv_result.flake_rate > 0.10:
            recommendations.append(
                f"Reduce flake rate from {bdv_result.flake_rate:.2%} to <10%"
            )
        if bdv_result.contract_mismatches:
            recommendations.append(
                f"Update scenarios to match deployed contract versions: {', '.join(bdv_result.contract_mismatches)}"
            )
        if not bdv_result.critical_journeys_covered:
            recommendations.append(
                "Add scenarios for critical user journeys"
            )

    # ACC recommendations
    if acc_result and not acc_result.passed:
        if acc_result.blocking_violations > 0:
            recommendations.append(
                f"Fix {acc_result.blocking_violations} blocking architectural violations"
            )
        if acc_result.cycles:
            recommendations.append(
                f"Break {len(acc_result.cycles)} cyclic dependencies"
            )
        if not acc_result.coupling_within_limits:
            recommendations.append(
                "Reduce coupling to meet architectural limits"
            )
        if not acc_result.suppressions_have_adrs:
            recommendations.append(
                "Document all architectural suppressions with ADRs"
            )

    # No recommendations if everything passed
    if not recommendations:
        recommendations.append("No action required - ready to deploy!")

    return recommendations


def can_deploy_to_production(iteration_id: str) -> bool:
    """
    FINAL DEPLOYMENT GATE.

    Deploy to production ONLY if all three audits pass.

    Args:
        iteration_id: Iteration identifier

    Returns:
        True if safe to deploy, False otherwise
    """
    result = tri_modal_audit(iteration_id)
    return result.can_deploy


# Storage functions (simplified - would use database in production)

def save_tri_audit_result(result: TriAuditResult):
    """Save tri-audit result to file"""
    output_dir = Path(f"reports/tri-modal/{result.iteration_id}")
    output_dir.mkdir(parents=True, exist_ok=True)

    output_file = output_dir / "tri_audit_result.json"
    with open(output_file, "w") as f:
        json.dump(result.to_dict(), f, indent=2)


def load_tri_audit_result(iteration_id: str) -> Optional[TriAuditResult]:
    """Load tri-audit result from file"""
    result_file = Path(f"reports/tri-modal/{iteration_id}/tri_audit_result.json")

    if not result_file.exists():
        return None

    with open(result_file) as f:
        data = json.load(f)

    data['verdict'] = TriModalVerdict(data['verdict'])

    return TriAuditResult(**data)


def load_dde_audit(iteration_id: str) -> Optional[DDEAuditResult]:
    """Load DDE audit result (stub - would load from database/file)"""
    # Stub implementation - return example result
    return DDEAuditResult(
        iteration_id=iteration_id,
        passed=True,
        score=0.95,
        all_nodes_complete=True,
        blocking_gates_passed=True,
        artifacts_stamped=True,
        lineage_intact=True,
        contracts_locked=True,
        details={}
    )


def load_bdv_audit(iteration_id: str) -> Optional[BDVAuditResult]:
    """Load BDV audit result (stub - would load from database/file)"""
    # Stub implementation - return example result
    return BDVAuditResult(
        iteration_id=iteration_id,
        passed=True,
        total_scenarios=25,
        passed_scenarios=25,
        failed_scenarios=0,
        flake_rate=0.04,
        contract_mismatches=[],
        critical_journeys_covered=True,
        details={}
    )


def load_acc_audit(iteration_id: str) -> Optional[ACCAuditResult]:
    """Load ACC audit result (stub - would load from database/file)"""
    # Stub implementation - return example result
    return ACCAuditResult(
        iteration_id=iteration_id,
        passed=True,
        blocking_violations=0,
        warning_violations=2,
        cycles=[],
        coupling_scores={},
        suppressions_have_adrs=True,
        coupling_within_limits=True,
        no_new_cycles=True,
        details={}
    )


# Example usage
if __name__ == "__main__":
    # Run tri-modal audit
    iteration_id = "Iter-20251012-1430-001"

    result = tri_modal_audit(iteration_id)

    print("=" * 80)
    print("TRI-MODAL AUDIT RESULT")
    print("=" * 80)
    print(f"\nIteration: {result.iteration_id}")
    print(f"Verdict: {result.verdict.value.upper()}")
    print(f"Can Deploy: {'✅ YES' if result.can_deploy else '❌ NO'}")
    print(f"\nStream Results:")
    print(f"  DDE (Execution): {'✅ PASS' if result.dde_passed else '❌ FAIL'}")
    print(f"  BDV (Behavior):  {'✅ PASS' if result.bdv_passed else '❌ FAIL'}")
    print(f"  ACC (Architecture): {'✅ PASS' if result.acc_passed else '❌ FAIL'}")
    print(f"\nDiagnosis:")
    print(result.diagnosis)
    print(f"\nRecommendations:")
    for i, rec in enumerate(result.recommendations, 1):
        print(f"  {i}. {rec}")
    print("\n" + "=" * 80)
