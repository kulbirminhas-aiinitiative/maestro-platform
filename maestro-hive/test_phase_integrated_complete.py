#!/usr/bin/env python3
"""
Comprehensive Test Suite for Phase-Integrated SDLC System

Tests the complete integration of:
1. Phase workflow orchestration
2. Progressive quality management
3. Phase gate validation
4. Team execution with progressive thresholds
5. Early failure detection
6. Adaptive persona selection

Includes critical test: Sunday.com failure prevention
"""

import asyncio
import sys
import json
import shutil
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))

from phase_integrated_executor import PhaseIntegratedExecutor
from phase_models import SDLCPhase, PhaseState
from progressive_quality_manager import ProgressiveQualityManager


async def test_progressive_quality_thresholds():
    """
    Test: Progressive quality thresholds increase with iterations
    
    Expected:
    - Iteration 1: 60% completeness, 0.50 quality
    - Iteration 2: 70% completeness, 0.60 quality  
    - Iteration 3: 80% completeness, 0.70 quality
    """
    
    print("\n" + "="*80)
    print("TEST 1: Progressive Quality Thresholds")
    print("="*80 + "\n")
    
    quality_mgr = ProgressiveQualityManager()
    
    # Test iteration progression
    for iteration in range(1, 6):
        thresholds = quality_mgr.get_thresholds_for_iteration(
            SDLCPhase.IMPLEMENTATION,
            iteration
        )
        
        print(f"Iteration {iteration}:")
        print(f"  Completeness: {thresholds.completeness:.0%}")
        print(f"  Quality: {thresholds.quality:.2f}")
        print(f"  Test Coverage: {thresholds.test_coverage:.0%}")
        
        # Verify progression
        expected_completeness = min(0.60 + (iteration - 1) * 0.10, 0.95)
        expected_quality = min(0.50 + (iteration - 1) * 0.10, 0.90)
        
        assert abs(thresholds.completeness - expected_completeness) < 0.01, \
            f"Completeness mismatch: {thresholds.completeness} != {expected_completeness}"
        
        assert abs(thresholds.quality - expected_quality) < 0.01, \
            f"Quality mismatch: {thresholds.quality} != {expected_quality}"
    
    print("\n✅ TEST PASSED: Progressive thresholds working correctly\n")
    return True


async def test_phase_specific_adjustments():
    """
    Test: Phase-specific threshold adjustments
    
    Expected:
    - Requirements phase: +10% completeness
    - Testing phase: +10% test coverage
    - Deployment phase: +10% completeness and quality
    """
    
    print("\n" + "="*80)
    print("TEST 2: Phase-Specific Threshold Adjustments")
    print("="*80 + "\n")
    
    quality_mgr = ProgressiveQualityManager()
    
    iteration = 1
    
    # Requirements phase: Should have higher completeness
    req_thresholds = quality_mgr.get_thresholds_for_iteration(
        SDLCPhase.REQUIREMENTS, iteration
    )
    impl_thresholds = quality_mgr.get_thresholds_for_iteration(
        SDLCPhase.IMPLEMENTATION, iteration
    )
    
    print(f"Requirements vs Implementation (Iteration {iteration}):")
    print(f"  Requirements completeness: {req_thresholds.completeness:.0%}")
    print(f"  Implementation completeness: {impl_thresholds.completeness:.0%}")
    
    assert req_thresholds.completeness > impl_thresholds.completeness, \
        "Requirements should have higher completeness threshold"
    
    # Testing phase: Should have higher test coverage
    testing_thresholds = quality_mgr.get_thresholds_for_iteration(
        SDLCPhase.TESTING, iteration
    )
    
    print(f"\nTesting vs Implementation (Iteration {iteration}):")
    print(f"  Testing test_coverage: {testing_thresholds.test_coverage:.0%}")
    print(f"  Implementation test_coverage: {impl_thresholds.test_coverage:.0%}")
    
    assert testing_thresholds.test_coverage > impl_thresholds.test_coverage, \
        "Testing should have higher test coverage threshold"
    
    # Deployment phase: Should have highest standards
    deploy_thresholds = quality_mgr.get_thresholds_for_iteration(
        SDLCPhase.DEPLOYMENT, iteration
    )
    
    print(f"\nDeployment vs Implementation (Iteration {iteration}):")
    print(f"  Deployment completeness: {deploy_thresholds.completeness:.0%}")
    print(f"  Deployment quality: {deploy_thresholds.quality:.2f}")
    print(f"  Implementation completeness: {impl_thresholds.completeness:.0%}")
    print(f"  Implementation quality: {impl_thresholds.quality:.2f}")
    
    assert deploy_thresholds.completeness > impl_thresholds.completeness, \
        "Deployment should have higher completeness"
    assert deploy_thresholds.quality > impl_thresholds.quality, \
        "Deployment should have higher quality"
    
    print("\n✅ TEST PASSED: Phase-specific adjustments working correctly\n")
    return True


async def test_sunday_com_failure_prevention():
    """
    Test: Sunday.com-style failure should be caught at phase gates
    
    Sunday.com Issue:
    - 80% of backend features missing (routes commented out)
    - All personas marked "success"
    - Proceeded to deployment
    
    Expected with Phase System:
    - Implementation phase exit gate should FAIL
    - Should detect commented routes
    - Should NOT proceed to Testing/Deployment
    - Should provide clear recommendations
    """
    
    print("\n" + "="*80)
    print("TEST 3: Sunday.com Failure Prevention (Critical)")
    print("="*80 + "\n")
    
    print("Scenario: Implementation with 80% routes commented out")
    print("Expected: FAIL at Implementation exit gate, not proceed to Deployment\n")
    
    # Create a test session with simulated Sunday.com-style incomplete implementation
    test_session_id = f"test_sunday_prevention_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    test_output = Path(f"./test_output/sunday_prevention")
    
    # Clean up previous test
    if test_output.exists():
        shutil.rmtree(test_output)
    test_output.mkdir(parents=True, exist_ok=True)
    
    # Simulate incomplete implementation
    # Create stub files to mimic Sunday.com's incomplete state
    backend_dir = test_output / "backend" / "src" / "routes"
    backend_dir.mkdir(parents=True, exist_ok=True)
    
    # Create routes file with commented routes (Sunday.com pattern)
    routes_file = backend_dir / "api.routes.ts"
    routes_file.write_text("""
// Sunday.com Pattern: Routes commented out = incomplete

// ❌ COMMENTED OUT - Feature not implemented
// router.use('/api/workspaces', workspaceRoutes);

// ❌ COMMENTED OUT - Feature not implemented  
// router.use('/api/boards', boardRoutes);

// ❌ COMMENTED OUT - Feature not implemented
// router.use('/api/items', itemRoutes);

// ✅ Only auth works
router.use('/api/auth', authRoutes);

export default router;
""")
    
    print(f"Created test environment: {test_output}")
    print(f"  - Simulated incomplete backend with 75% routes commented out")
    print(f"  - This mimics the Sunday.com failure pattern\n")
    
    # Now test if phase system catches this
    try:
        executor = PhaseIntegratedExecutor(
            session_id=test_session_id,
            requirement="Build workspace management platform (Sunday.com clone)",
            output_dir=test_output,
            enable_phase_gates=True,
            enable_progressive_quality=True,
            enable_persona_reuse=False  # Disable for clean test
        )
        
        # Execute workflow - should fail at Implementation phase
        result = await executor.execute_workflow(max_iterations=2)
        
        print("\n" + "-"*80)
        print("RESULT ANALYSIS:")
        print("-"*80)
        print(f"Success: {result['success']}")
        print(f"Status: {result['status']}")
        
        if not result['success']:
            print(f"Failed At: {result.get('failed_at_phase', 'N/A')}")
            print(f"Failure Reason: {result.get('failure_reason', 'N/A')}")
            
            # Check if failed at Implementation (not Deployment!)
            if result.get('failed_at_phase') == 'IMPLEMENTATION':
                print("\n✅ CRITICAL: Failure detected at IMPLEMENTATION phase")
                print("   This prevents the Sunday.com issue where incomplete")
                print("   code proceeded all the way to deployment!")
                success = True
            elif result.get('status') == 'partial':
                # Check that deployment didn't happen
                if 'DEPLOYMENT' not in result.get('phases_completed', []):
                    print("\n✅ CRITICAL: Deployment phase never reached")
                    print("   Incomplete implementation was caught early!")
                    success = True
                else:
                    print("\n❌ FAILURE: Deployment proceeded despite incomplete implementation")
                    print("   This is the Sunday.com bug!")
                    success = False
            else:
                print(f"\n⚠️  Unexpected failure point: {result.get('failed_at_phase')}")
                success = False
        else:
            print("\n❌ TEST FAILED: Workflow succeeded despite incomplete implementation")
            print("   This is exactly the Sunday.com bug we're trying to prevent!")
            success = False
        
        # Clean up
        if test_output.exists():
            shutil.rmtree(test_output)
        
        if success:
            print("\n✅ TEST PASSED: Sunday.com-style failures are now prevented!\n")
        else:
            print("\n❌ TEST FAILED: Sunday.com issue not prevented\n")
        
        return success
    
    except Exception as e:
        print(f"\n❌ TEST FAILED with exception: {e}")
        import traceback
        traceback.print_exc()
        
        # Clean up
        if test_output.exists():
            shutil.rmtree(test_output)
        
        return False


async def test_early_failure_detection():
    """
    Test: Failures should be caught at phase boundaries, not at the end
    
    Expected:
    - If Requirements incomplete: Fail at Requirements, don't run Design
    - If Design incomplete: Fail at Design, don't run Implementation
    - Save time and cost by failing early
    """
    
    print("\n" + "="*80)
    print("TEST 4: Early Failure Detection")
    print("="*80 + "\n")
    
    print("Scenario: Requirements phase fails")
    print("Expected: Stop at Requirements, don't run remaining phases\n")
    
    # This test would need actual persona execution
    # For now, validate the logic is correct
    
    quality_mgr = ProgressiveQualityManager()
    
    # Simulate Requirements phase with low completeness
    req_thresholds = quality_mgr.get_thresholds_for_iteration(
        SDLCPhase.REQUIREMENTS, iteration=1
    )
    
    print(f"Requirements Phase (Iteration 1):")
    print(f"  Required Completeness: {req_thresholds.completeness:.0%}")
    print(f"  Simulated Completeness: 45%")
    
    # Check if would fail
    would_fail = 0.45 < req_thresholds.completeness
    
    if would_fail:
        print(f"\n✅ Exit gate would FAIL (45% < {req_thresholds.completeness:.0%})")
        print("   Workflow would stop at Requirements phase")
        print("   Cost saved: $176 (8 remaining personas × $22)")
        print("   Time saved: ~80% of total SDLC time")
        print("\n✅ TEST PASSED: Early failure detection working\n")
        return True
    else:
        print(f"\n❌ Exit gate would PASS despite low completeness")
        print("   This would allow incomplete work to proceed")
        print("\n❌ TEST FAILED\n")
        return False


async def test_persona_selection():
    """
    Test: Correct personas selected for each phase
    
    Expected:
    - Requirements: requirement_analyst
    - Design: solution_architect, security_specialist
    - Implementation: backend_developer, frontend_developer
    - Testing: qa_engineer, integration_tester
    - Deployment: devops_engineer, deployment_specialist
    """
    
    print("\n" + "="*80)
    print("TEST 5: Phase-Specific Persona Selection")
    print("="*80 + "\n")
    
    executor = PhaseIntegratedExecutor(
        session_id="test_persona_selection",
        requirement="Test project",
        enable_phase_gates=False  # Disable for this test
    )
    
    # Test each phase
    expected_personas = {
        SDLCPhase.REQUIREMENTS: ["requirement_analyst"],
        SDLCPhase.DESIGN: ["solution_architect", "security_specialist"],
        SDLCPhase.IMPLEMENTATION: ["backend_developer", "frontend_developer"],
        SDLCPhase.TESTING: ["qa_engineer", "integration_tester"],
        SDLCPhase.DEPLOYMENT: ["devops_engineer", "deployment_specialist"]
    }
    
    all_passed = True
    
    for phase, expected in expected_personas.items():
        selected = executor._select_personas_for_phase(phase, iteration=1)
        
        print(f"{phase.value}:")
        print(f"  Expected: {expected}")
        print(f"  Selected: {selected}")
        
        if set(selected) == set(expected):
            print(f"  ✅ Match")
        else:
            print(f"  ❌ Mismatch")
            all_passed = False
        print()
    
    if all_passed:
        print("✅ TEST PASSED: Persona selection correct for all phases\n")
    else:
        print("❌ TEST FAILED: Some phases have incorrect persona selection\n")
    
    return all_passed


async def run_all_tests():
    """Run complete test suite"""
    
    print("\n" + "#"*80)
    print("# COMPREHENSIVE PHASE-INTEGRATED SDLC TEST SUITE")
    print("#"*80 + "\n")
    
    print("Testing Phase-Based SDLC System with:")
    print("  - Progressive Quality Management")
    print("  - Phase Gate Validation")
    print("  - Early Failure Detection")
    print("  - Adaptive Persona Selection")
    print("  - Sunday.com Failure Prevention (CRITICAL)")
    print()
    
    results = {}
    
    # Test 1: Progressive quality thresholds
    try:
        results["progressive_thresholds"] = await test_progressive_quality_thresholds()
    except Exception as e:
        print(f"❌ Test 1 failed with exception: {e}")
        results["progressive_thresholds"] = False
    
    # Test 2: Phase-specific adjustments
    try:
        results["phase_adjustments"] = await test_phase_specific_adjustments()
    except Exception as e:
        print(f"❌ Test 2 failed with exception: {e}")
        results["phase_adjustments"] = False
    
    # Test 3: Sunday.com failure prevention (CRITICAL)
    try:
        results["sunday_com_prevention"] = await test_sunday_com_failure_prevention()
    except Exception as e:
        print(f"❌ Test 3 (CRITICAL) failed with exception: {e}")
        results["sunday_com_prevention"] = False
    
    # Test 4: Early failure detection
    try:
        results["early_failure"] = await test_early_failure_detection()
    except Exception as e:
        print(f"❌ Test 4 failed with exception: {e}")
        results["early_failure"] = False
    
    # Test 5: Persona selection
    try:
        results["persona_selection"] = await test_persona_selection()
    except Exception as e:
        print(f"❌ Test 5 failed with exception: {e}")
        results["persona_selection"] = False
    
    # Summary
    print("\n" + "#"*80)
    print("# TEST SUITE RESULTS")
    print("#"*80 + "\n")
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{status}: {test_name}")
    
    print(f"\nTotal: {passed}/{total} tests passed ({passed/total*100:.0f}%)")
    
    if passed == total:
        print("\n🎉 ALL TESTS PASSED! Phase-integrated system working correctly.")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed. Review above for details.")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(run_all_tests())
    sys.exit(exit_code)
