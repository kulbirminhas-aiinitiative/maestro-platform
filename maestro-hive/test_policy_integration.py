#!/usr/bin/env python3
"""
Test Policy Integration
Verify that policy_loader and quality_fabric_client work together correctly.
"""

import sys
import json
import logging
from policy_loader import get_policy_loader
from quality_fabric_client import QualityFabricClient, PersonaType

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_policy_loader():
    """Test policy loader functionality"""
    print("\n" + "="*70)
    print("TEST 1: Policy Loader")
    print("="*70)

    loader = get_policy_loader()

    # Test 1: Load backend developer policy
    print("\n1. Backend Developer Policy:")
    backend_policy = loader.get_persona_policy("backend_developer")
    if backend_policy:
        print(f"   ✓ Description: {backend_policy.description}")
        print(f"   ✓ Quality Gates: {list(backend_policy.quality_gates.keys())}")
        print(f"   ✓ Required Artifacts: {backend_policy.required_artifacts}")

        # Check specific gate thresholds
        code_quality_gate = backend_policy.quality_gates.get("code_quality")
        if code_quality_gate:
            print(f"   ✓ Code Quality Threshold: {code_quality_gate.threshold}")
            print(f"   ✓ Code Quality Severity: {code_quality_gate.severity}")
    else:
        print("   ✗ Failed to load backend developer policy")
        return False

    # Test 2: Load implementation phase SLO
    print("\n2. Implementation Phase SLO:")
    impl_slo = loader.get_phase_slo("implementation")
    if impl_slo:
        print(f"   ✓ Phase: {impl_slo.phase_name}")
        print(f"   ✓ Success Criteria: {list(impl_slo.success_criteria.keys())}")
        print(f"   ✓ Exit Gates: {len(impl_slo.exit_gates)} gates")
        print(f"   ✓ Required Artifacts: {impl_slo.required_artifacts}")
    else:
        print("   ✗ Failed to load implementation phase SLO")
        return False

    # Test 3: Validate persona output
    print("\n3. Validate Backend Developer Output (Mock):")
    test_metrics = {
        "code_quality": 8.5,
        "test_coverage": 0.85,
        "security": 0,
        "complexity": 8,
        "documentation": 0.75
    }
    result = loader.validate_persona_output("backend_developer", test_metrics)
    print(f"   ✓ Validation Status: {result['status']}")
    print(f"   ✓ Gates Passed: {result['gates_passed']}")
    print(f"   ✓ Gates Failed: {len(result['gates_failed'])} gate(s)")
    if result['gates_failed']:
        for failed in result['gates_failed']:
            print(f"      - {failed['gate']}: {failed.get('actual', 'N/A')} vs {failed.get('threshold', 'N/A')}")

    # Test 4: Check bypass rules
    print("\n4. Bypass Rules:")
    can_bypass_complexity = loader.can_bypass_gate("complexity", "implementation")
    can_bypass_security = loader.can_bypass_gate("security", "implementation")
    print(f"   ✓ Can bypass 'complexity' gate: {can_bypass_complexity}")
    print(f"   ✓ Can bypass 'security' gate: {can_bypass_security}")

    return True


def test_quality_fabric_client():
    """Test Quality Fabric client with policy integration"""
    print("\n" + "="*70)
    print("TEST 2: Quality Fabric Client Integration")
    print("="*70)

    # Initialize client (will automatically load policy loader)
    client = QualityFabricClient()

    # Test 1: Get persona gates from policy
    print("\n1. Get Persona Gates from Policy:")
    backend_gates = client.get_persona_gates(PersonaType.BACKEND_DEVELOPER)
    if backend_gates:
        print(f"   ✓ Loaded {len(backend_gates)} gates for backend_developer")
        for gate_name, gate_info in backend_gates.items():
            print(f"      - {gate_name}: threshold={gate_info['threshold']}, severity={gate_info['severity']}")
    else:
        print("   ✗ No gates loaded (PolicyLoader may not be available)")

    # Test 2: Get phase gates
    print("\n2. Get Phase Gates from Policy:")
    impl_gates = client.get_phase_gates("implementation")
    if impl_gates:
        print(f"   ✓ Loaded {len(impl_gates)} exit gates for implementation phase")
        for gate in impl_gates[:3]:  # Show first 3
            print(f"      - {gate['gate']}: {gate['condition']} ({gate['severity']})")
    else:
        print("   ✗ No phase gates loaded (PolicyLoader may not be available)")

    # Test 3: Check service health
    print("\n3. Quality Fabric Service Health:")
    import asyncio
    try:
        health = asyncio.run(client.health_check())
        if health.get("status") == "error":
            print(f"   ⚠ Service not available: {health.get('error')}")
        else:
            print(f"   ✓ Service Status: {health.get('status', 'unknown')}")
    except Exception as e:
        print(f"   ⚠ Service check failed: {e}")

    return True


def test_end_to_end_validation():
    """Test end-to-end validation flow"""
    print("\n" + "="*70)
    print("TEST 3: End-to-End Validation Flow")
    print("="*70)

    loader = get_policy_loader()

    # Scenario: Backend developer with good code quality
    print("\n1. Scenario: High Quality Backend Code")
    metrics_good = {
        "code_quality": 8.5,
        "test_coverage": 0.85,
        "security": 0,
        "complexity": 7,
        "documentation": 0.80
    }
    result_good = loader.validate_persona_output("backend_developer", metrics_good)
    print(f"   Status: {result_good['status']}")
    print(f"   Blocking Failures: {result_good['blocking_failures']}")
    print(f"   Overall: {'✓ PASS' if result_good['status'] != 'fail' else '✗ FAIL'}")

    # Scenario: Backend developer with poor quality
    print("\n2. Scenario: Low Quality Backend Code")
    metrics_poor = {
        "code_quality": 6.0,  # Below threshold of 8.0
        "test_coverage": 0.50,  # Below threshold of 0.80
        "security": 2,  # Security issues present (threshold is 0)
        "complexity": 15,  # High complexity
        "documentation": 0.40  # Low documentation
    }
    result_poor = loader.validate_persona_output("backend_developer", metrics_poor)
    print(f"   Status: {result_poor['status']}")
    print(f"   Blocking Failures: {result_poor['blocking_failures']}")
    print(f"   Failed Gates: {len(result_poor['gates_failed'])}")
    for failed in result_poor['gates_failed']:
        if failed['severity'] == 'BLOCKING':
            print(f"      ✗ BLOCKING: {failed['gate']} ({failed.get('actual', 'N/A')} vs {failed.get('threshold', 'N/A')})")
    print(f"   Overall: {'✓ PASS' if result_poor['status'] != 'fail' else '✗ FAIL (as expected)'}")

    # Scenario: Phase transition validation
    print("\n3. Scenario: Implementation Phase Transition")
    phase_metrics = {
        "build_success_rate": 0.96,
        "code_quality_score": 8.2,
        "test_coverage": 0.82,
        "stub_rate": 0.03,
        "security_vulnerabilities": 0,
        "code_review_completion": 1.0,
        "documentation_coverage": 0.72
    }
    phase_result = loader.validate_phase_transition("implementation", phase_metrics)
    print(f"   Status: {phase_result['status']}")
    print(f"   Gates Passed: {len(phase_result['gates_passed'])}")
    print(f"   Blocking Failures: {phase_result['blocking_failures']}")
    print(f"   Can Proceed: {'✓ YES' if phase_result['status'] != 'fail' else '✗ NO'}")

    return True


def main():
    """Run all tests"""
    print("\n" + "="*70)
    print("QUALITY FABRIC POLICY INTEGRATION TEST SUITE")
    print("="*70)

    results = {
        "policy_loader": False,
        "quality_fabric_client": False,
        "end_to_end": False
    }

    try:
        results["policy_loader"] = test_policy_loader()
    except Exception as e:
        logger.error(f"Policy Loader test failed: {e}", exc_info=True)

    try:
        results["quality_fabric_client"] = test_quality_fabric_client()
    except Exception as e:
        logger.error(f"Quality Fabric Client test failed: {e}", exc_info=True)

    try:
        results["end_to_end"] = test_end_to_end_validation()
    except Exception as e:
        logger.error(f"End-to-End test failed: {e}", exc_info=True)

    # Summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    for test_name, passed in results.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{test_name:30s} {status}")

    all_passed = all(results.values())
    print("="*70)
    if all_passed:
        print("✓ ALL TESTS PASSED")
        return 0
    else:
        print("✗ SOME TESTS FAILED")
        return 1


if __name__ == "__main__":
    sys.exit(main())
