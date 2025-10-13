"""
Tri-Modal Framework Demonstration

This script demonstrates the tri-modal convergence framework with all three streams:
- DDE (Dependency-Driven Execution)
- BDV (Behavior-Driven Validation)
- ACC (Architectural Conformance Checking)

Shows different failure scenarios and their diagnoses.
"""

from tri_audit import (
    tri_modal_audit,
    DDEAuditResult,
    BDVAuditResult,
    ACCAuditResult,
    TriModalVerdict
)


def demo_all_pass():
    """Demo: All three streams pass - safe to deploy"""
    print("\n" + "=" * 80)
    print("SCENARIO 1: ALL PASS - Safe to Deploy")
    print("=" * 80)

    iteration_id = "Demo-AllPass-001"

    dde = DDEAuditResult(
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

    bdv = BDVAuditResult(
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

    acc = ACCAuditResult(
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

    result = tri_modal_audit(iteration_id, dde, bdv, acc)
    print_result(result)


def demo_design_gap():
    """Demo: DDE + ACC pass, BDV fails - Built the wrong thing"""
    print("\n" + "=" * 80)
    print("SCENARIO 2: DESIGN GAP - Built the Wrong Thing")
    print("=" * 80)

    iteration_id = "Demo-DesignGap-001"

    dde = DDEAuditResult(
        iteration_id=iteration_id,
        passed=True,
        score=0.92,
        all_nodes_complete=True,
        blocking_gates_passed=True,
        artifacts_stamped=True,
        lineage_intact=True,
        contracts_locked=True,
        details={}
    )

    bdv = BDVAuditResult(
        iteration_id=iteration_id,
        passed=False,  # BDV FAILS
        total_scenarios=25,
        passed_scenarios=18,
        failed_scenarios=7,
        flake_rate=0.08,
        contract_mismatches=["AuthAPI:v1.2 -> v1.3"],
        critical_journeys_covered=False,
        details={"failing_scenarios": [
            "User login flow doesn't match new requirements",
            "Profile update missing validation rules",
            "Search results don't match expected behavior"
        ]}
    )

    acc = ACCAuditResult(
        iteration_id=iteration_id,
        passed=True,
        blocking_violations=0,
        warning_violations=3,
        cycles=[],
        coupling_scores={},
        suppressions_have_adrs=True,
        coupling_within_limits=True,
        no_new_cycles=True,
        details={}
    )

    result = tri_modal_audit(iteration_id, dde, bdv, acc)
    print_result(result)


def demo_architectural_erosion():
    """Demo: DDE + BDV pass, ACC fails - Technical debt accumulating"""
    print("\n" + "=" * 80)
    print("SCENARIO 3: ARCHITECTURAL EROSION - Technical Debt")
    print("=" * 80)

    iteration_id = "Demo-ArchErosion-001"

    dde = DDEAuditResult(
        iteration_id=iteration_id,
        passed=True,
        score=0.88,
        all_nodes_complete=True,
        blocking_gates_passed=True,
        artifacts_stamped=True,
        lineage_intact=True,
        contracts_locked=True,
        details={}
    )

    bdv = BDVAuditResult(
        iteration_id=iteration_id,
        passed=True,
        total_scenarios=25,
        passed_scenarios=25,
        failed_scenarios=0,
        flake_rate=0.06,
        contract_mismatches=[],
        critical_journeys_covered=True,
        details={}
    )

    acc = ACCAuditResult(
        iteration_id=iteration_id,
        passed=False,  # ACC FAILS
        blocking_violations=5,
        warning_violations=12,
        cycles=[
            ["services.user", "repositories.profile", "services.user"],
            ["domain.order", "domain.payment", "domain.order"]
        ],
        coupling_scores={
            "BusinessLogic": {"efferent": 15, "afferent": 3, "instability": 0.83}
        },
        suppressions_have_adrs=False,
        coupling_within_limits=False,
        no_new_cycles=False,
        details={"violations": [
            "Presentation layer calling DataAccess directly",
            "DataAccess calling BusinessLogic (reverse dependency)",
            "Cyclic dependencies between User and Profile services",
            "BusinessLogic coupling exceeds limit of 10 (current: 15)"
        ]}
    )

    result = tri_modal_audit(iteration_id, dde, bdv, acc)
    print_result(result)


def demo_process_issue():
    """Demo: BDV + ACC pass, DDE fails - Pipeline/gate issues"""
    print("\n" + "=" * 80)
    print("SCENARIO 4: PROCESS ISSUE - Pipeline Configuration")
    print("=" * 80)

    iteration_id = "Demo-ProcessIssue-001"

    dde = DDEAuditResult(
        iteration_id=iteration_id,
        passed=False,  # DDE FAILS
        score=0.65,
        all_nodes_complete=False,
        blocking_gates_passed=False,
        artifacts_stamped=True,
        lineage_intact=True,
        contracts_locked=False,
        details={"issues": [
            "3 nodes incomplete",
            "Coverage gate failed: 62% < 70% threshold",
            "SAST scan found 2 medium severity issues",
            "2 interface contracts not locked"
        ]}
    )

    bdv = BDVAuditResult(
        iteration_id=iteration_id,
        passed=True,
        total_scenarios=25,
        passed_scenarios=25,
        failed_scenarios=0,
        flake_rate=0.05,
        contract_mismatches=[],
        critical_journeys_covered=True,
        details={}
    )

    acc = ACCAuditResult(
        iteration_id=iteration_id,
        passed=True,
        blocking_violations=0,
        warning_violations=4,
        cycles=[],
        coupling_scores={},
        suppressions_have_adrs=True,
        coupling_within_limits=True,
        no_new_cycles=True,
        details={}
    )

    result = tri_modal_audit(iteration_id, dde, bdv, acc)
    print_result(result)


def demo_systemic_failure():
    """Demo: All three streams fail - HALT"""
    print("\n" + "=" * 80)
    print("SCENARIO 5: SYSTEMIC FAILURE - All Streams Failed")
    print("=" * 80)

    iteration_id = "Demo-SystemicFailure-001"

    dde = DDEAuditResult(
        iteration_id=iteration_id,
        passed=False,
        score=0.42,
        all_nodes_complete=False,
        blocking_gates_passed=False,
        artifacts_stamped=False,
        lineage_intact=False,
        contracts_locked=False,
        details={}
    )

    bdv = BDVAuditResult(
        iteration_id=iteration_id,
        passed=False,
        total_scenarios=25,
        passed_scenarios=8,
        failed_scenarios=17,
        flake_rate=0.24,
        contract_mismatches=["AuthAPI:v1.2", "ProfileAPI:v1.0"],
        critical_journeys_covered=False,
        details={}
    )

    acc = ACCAuditResult(
        iteration_id=iteration_id,
        passed=False,
        blocking_violations=15,
        warning_violations=28,
        cycles=[
            ["A", "B", "C", "A"],
            ["X", "Y", "X"],
            ["M", "N", "O", "M"]
        ],
        coupling_scores={},
        suppressions_have_adrs=False,
        coupling_within_limits=False,
        no_new_cycles=False,
        details={}
    )

    result = tri_modal_audit(iteration_id, dde, bdv, acc)
    print_result(result)


def print_result(result):
    """Pretty-print tri-audit result"""
    print(f"\nIteration: {result.iteration_id}")
    print(f"Verdict: {result.verdict.value.upper()}")
    print(f"Can Deploy: {'✅ YES' if result.can_deploy else '❌ NO'}")

    print(f"\nStream Results:")
    print(f"  DDE (Execution):    {'✅ PASS' if result.dde_passed else '❌ FAIL'}")
    print(f"  BDV (Behavior):     {'✅ PASS' if result.bdv_passed else '❌ FAIL'}")
    print(f"  ACC (Architecture): {'✅ PASS' if result.acc_passed else '❌ FAIL'}")

    print(f"\nDiagnosis:")
    print(result.diagnosis)

    print(f"\nRecommendations:")
    for i, rec in enumerate(result.recommendations, 1):
        print(f"  {i}. {rec}")


if __name__ == "__main__":
    print("\n" + "=" * 80)
    print("TRI-MODAL CONVERGENCE FRAMEWORK DEMONSTRATION")
    print("=" * 80)
    print("\nDemonstrating all failure patterns and their diagnoses...")

    # Run all scenarios
    demo_all_pass()
    demo_design_gap()
    demo_architectural_erosion()
    demo_process_issue()
    demo_systemic_failure()

    print("\n" + "=" * 80)
    print("DEMONSTRATION COMPLETE")
    print("=" * 80)
    print("\nKey Insight: Each failure pattern has non-overlapping blind spots.")
    print("Only when ALL THREE streams pass can we safely deploy to production.")
    print("\nDeploy ONLY when: DDE ✅ AND BDV ✅ AND ACC ✅")
    print("=" * 80 + "\n")
