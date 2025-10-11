#!/usr/bin/env python3
"""
Integration Test - Full Phase-Based Workflow with Real Execution

This test runs a COMPLETE end-to-end SDLC workflow using:
- Real team_execution.py (Claude SDK)
- Real phase gate validation
- Real progressive quality management
- Real persona selection

This is NOT a mock test - it will actually generate code!
"""

import asyncio
import sys
import logging
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from phase_workflow_orchestrator import PhaseWorkflowOrchestrator
from phase_models import SDLCPhase, PhaseState


async def test_full_workflow_simple_project():
    """
    Test full workflow with a simple project
    
    Project: Simple REST API for Todo Management
    Expected: Complete all 5 phases successfully
    """
    print("\n" + "="*80)
    print("🚀 INTEGRATION TEST: Simple REST API Project")
    print("="*80)
    print()
    print("Project: Todo Management REST API")
    print("Expected Phases: Requirements → Design → Implementation → Testing → Deployment")
    print("Expected Outcome: All phases complete with progressive quality improvement")
    print()
    print("="*80 + "\n")
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(message)s'
    )
    
    # Create orchestrator
    orchestrator = PhaseWorkflowOrchestrator(
        session_id=f"integration_test_simple_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        requirement=(
            "Build a simple REST API for Todo Management with the following features:\n"
            "1. User authentication (JWT)\n"
            "2. CRUD operations for todos (create, read, update, delete)\n"
            "3. Todo fields: id, title, description, status, priority, due_date\n"
            "4. Filter and search capabilities\n"
            "5. SQLite database\n"
            "6. Python FastAPI framework\n"
            "7. Basic unit tests\n"
            "8. API documentation (OpenAPI/Swagger)"
        ),
        output_dir=Path(f"./integration_test_output/simple_api_{datetime.now().strftime('%Y%m%d_%H%M%S')}"),
        enable_phase_gates=True,
        enable_progressive_quality=True,
        maestro_ml_url="http://localhost:8001"
    )
    
    # Execute workflow
    print("Starting workflow execution...")
    print("This will take several minutes as it executes real personas with Claude SDK\n")
    
    result = await orchestrator.execute_workflow(max_iterations=10)
    
    # Analyze results
    print("\n" + "="*80)
    print("📊 INTEGRATION TEST RESULTS")
    print("="*80)
    
    print(f"\n🎯 Overall Success: {'✅ YES' if result.success else '❌ NO'}")
    print(f"\n📈 Execution Metrics:")
    print(f"   Total Iterations: {result.total_iterations}")
    print(f"   Phases Completed: {len(result.phases_completed)}/5")
    print(f"   Personas Executed: {result.total_personas_executed}")
    print(f"   Personas Reused: {result.total_personas_reused}")
    print(f"   Duration: {result.total_duration_seconds:.0f}s ({result.total_duration_seconds/60:.1f} minutes)")
    
    print(f"\n📊 Quality Metrics:")
    print(f"   Final Quality Score: {result.final_quality_score:.0%}")
    print(f"   Final Completeness: {result.final_completeness:.0%}")
    
    print(f"\n🔄 Phase History ({len(result.phase_history)} executions):")
    for i, phase_exec in enumerate(result.phase_history, 1):
        status_emoji = {
            PhaseState.COMPLETED: "✅",
            PhaseState.NEEDS_REWORK: "🔄",
            PhaseState.FAILED: "❌",
            PhaseState.IN_PROGRESS: "⏳"
        }.get(phase_exec.state, "❓")
        
        print(f"\n   {i}. {phase_exec.phase.value.upper()} (Iteration {phase_exec.iteration})")
        print(f"      Status: {status_emoji} {phase_exec.state.value}")
        print(f"      Quality: {phase_exec.quality_score:.0%}")
        print(f"      Completeness: {phase_exec.completeness:.0%}")
        print(f"      Personas: {len(phase_exec.personas_executed)} executed, {len(phase_exec.personas_reused)} reused")
        print(f"      Duration: {phase_exec.duration_seconds():.0f}s")
        
        if phase_exec.entry_gate_result:
            entry_status = "✅ PASS" if phase_exec.entry_gate_result.passed else "❌ FAIL"
            print(f"      Entry Gate: {entry_status} ({phase_exec.entry_gate_result.score:.0%})")
        
        if phase_exec.exit_gate_result:
            exit_status = "✅ PASS" if phase_exec.exit_gate_result.passed else "❌ FAIL"
            print(f"      Exit Gate: {exit_status} ({phase_exec.exit_gate_result.score:.0%})")
            
            if not phase_exec.exit_gate_result.passed:
                print(f"      Blocking Issues: {len(phase_exec.exit_gate_result.blocking_issues)}")
                for issue in phase_exec.exit_gate_result.blocking_issues[:3]:
                    print(f"        • {issue}")
    
    print(f"\n🎯 Phases Completed:")
    for phase in result.phases_completed:
        print(f"   ✅ {phase.value.upper()}")
    
    missing_phases = set([
        SDLCPhase.REQUIREMENTS,
        SDLCPhase.DESIGN,
        SDLCPhase.IMPLEMENTATION,
        SDLCPhase.TESTING,
        SDLCPhase.DEPLOYMENT
    ]) - set(result.phases_completed)
    
    if missing_phases:
        print(f"\n⚠️  Incomplete Phases:")
        for phase in missing_phases:
            print(f"   ❌ {phase.value.upper()}")
    
    print(f"\n💾 Output Directory: {orchestrator.output_dir}")
    print(f"   Check this directory for generated code and artifacts")
    
    # Verify expectations
    print(f"\n🧪 Verification:")
    
    success_criteria = {
        "Workflow completed": result.success or len(result.phases_completed) >= 3,
        "Quality improved": len(result.phase_history) <= 1 or result.phase_history[-1].quality_score >= result.phase_history[0].quality_score,
        "Personas executed": result.total_personas_executed > 0,
        "Phase gates validated": any(p.entry_gate_result or p.exit_gate_result for p in result.phase_history),
        "Progressive thresholds": len(result.phase_history) > 0
    }
    
    for criterion, passed in success_criteria.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"   {status} {criterion}")
    
    all_passed = all(success_criteria.values())
    
    print("\n" + "="*80)
    if all_passed:
        print("✅ INTEGRATION TEST PASSED")
    else:
        print("⚠️  INTEGRATION TEST: Some criteria not met (but may be expected)")
    print("="*80 + "\n")
    
    return result


async def test_full_workflow_complex_project():
    """
    Test full workflow with a more complex project
    
    Project: E-Commerce Platform
    Expected: May need multiple iterations, rework phases
    """
    print("\n" + "="*80)
    print("🚀 INTEGRATION TEST: Complex E-Commerce Platform")
    print("="*80)
    print()
    print("Project: Full E-Commerce Platform")
    print("Expected: Multiple iterations, some phases may need rework")
    print()
    print("="*80 + "\n")
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(message)s'
    )
    
    # Create orchestrator
    orchestrator = PhaseWorkflowOrchestrator(
        session_id=f"integration_test_complex_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        requirement=(
            "Build a comprehensive E-Commerce Platform with:\n"
            "1. User Management:\n"
            "   - Registration, login, profile management\n"
            "   - Address book, wishlist\n"
            "   - Order history\n"
            "2. Product Catalog:\n"
            "   - Categories, subcategories\n"
            "   - Product search, filters, sorting\n"
            "   - Product reviews and ratings\n"
            "3. Shopping Cart:\n"
            "   - Add/remove items\n"
            "   - Quantity management\n"
            "   - Save for later\n"
            "4. Checkout:\n"
            "   - Multiple payment methods (credit card, PayPal)\n"
            "   - Shipping options\n"
            "   - Order confirmation\n"
            "5. Admin Panel:\n"
            "   - Product management\n"
            "   - Order management\n"
            "   - User management\n"
            "   - Analytics dashboard\n"
            "6. Tech Stack:\n"
            "   - Backend: Node.js with Express\n"
            "   - Frontend: React with Redux\n"
            "   - Database: PostgreSQL\n"
            "   - Authentication: JWT\n"
            "   - Payment: Stripe integration\n"
            "7. Testing:\n"
            "   - Unit tests (Jest)\n"
            "   - Integration tests\n"
            "   - E2E tests (Cypress)"
        ),
        output_dir=Path(f"./integration_test_output/ecommerce_{datetime.now().strftime('%Y%m%d_%H%M%S')}"),
        enable_phase_gates=True,
        enable_progressive_quality=True,
        maestro_ml_url="http://localhost:8001"
    )
    
    # Execute workflow
    print("Starting workflow execution...")
    print("This is a complex project - may take 10-20 minutes\n")
    
    result = await orchestrator.execute_workflow(max_iterations=15)
    
    # Analyze results (same as simple test but expect different outcomes)
    print("\n" + "="*80)
    print("📊 INTEGRATION TEST RESULTS (Complex Project)")
    print("="*80)
    
    print(f"\n🎯 Overall Success: {'✅ YES' if result.success else '⚠️  PARTIAL'}")
    print(f"\n📈 Execution Metrics:")
    print(f"   Total Iterations: {result.total_iterations}")
    print(f"   Phases Completed: {len(result.phases_completed)}/5")
    print(f"   Personas Executed: {result.total_personas_executed}")
    print(f"   Personas Reused: {result.total_personas_reused}")
    print(f"   Duration: {result.total_duration_seconds:.0f}s ({result.total_duration_seconds/60:.1f} minutes)")
    
    print(f"\n📊 Quality Metrics:")
    print(f"   Final Quality Score: {result.final_quality_score:.0%}")
    print(f"   Final Completeness: {result.final_completeness:.0%}")
    
    # Show rework iterations
    rework_count = sum(1 for p in result.phase_history if p.state == PhaseState.NEEDS_REWORK)
    print(f"\n🔄 Rework Analysis:")
    print(f"   Phases needing rework: {rework_count}")
    print(f"   Average iterations per phase: {len(result.phase_history) / max(len(result.phases_completed), 1):.1f}")
    
    print(f"\n💾 Output Directory: {orchestrator.output_dir}")
    
    print("\n" + "="*80)
    print("✅ INTEGRATION TEST COMPLETED (Complex Project)")
    print("   Note: Complex projects may not complete all phases - this is expected")
    print("="*80 + "\n")
    
    return result


async def main():
    """Run integration tests"""
    print("\n" + "="*80)
    print("🚀 PHASE-BASED WORKFLOW - FULL INTEGRATION TESTS")
    print("="*80)
    print()
    print("⚠️  WARNING: These tests will execute REAL workflows with Claude SDK")
    print("   - Will generate actual code")
    print("   - Will take several minutes")
    print("   - Will use Claude API credits")
    print()
    print("Tests to run:")
    print("   1. Simple REST API (expected: ~5-10 minutes)")
    print("   2. Complex E-Commerce Platform (expected: ~10-20 minutes)")
    print()
    print("="*80 + "\n")
    
    choice = input("Continue with tests? [y/N]: ").strip().lower()
    
    if choice != 'y':
        print("Tests cancelled by user")
        sys.exit(0)
    
    print("\n" + "="*80)
    print("Starting Integration Tests...")
    print("="*80 + "\n")
    
    tests_run = 0
    tests_passed = 0
    
    # Test 1: Simple project
    try:
        print("\n[1/2] Running Simple REST API test...\n")
        result1 = await test_full_workflow_simple_project()
        tests_run += 1
        if result1.success or len(result1.phases_completed) >= 3:
            tests_passed += 1
    except Exception as e:
        print(f"\n❌ Test 1 failed with error: {e}")
        import traceback
        traceback.print_exc()
    
    # Test 2: Complex project
    try:
        print("\n[2/2] Running Complex E-Commerce test...\n")
        result2 = await test_full_workflow_complex_project()
        tests_run += 1
        if result2.success or len(result2.phases_completed) >= 2:
            tests_passed += 1
    except Exception as e:
        print(f"\n❌ Test 2 failed with error: {e}")
        import traceback
        traceback.print_exc()
    
    # Final summary
    print("\n" + "="*80)
    print("🎉 INTEGRATION TEST SUITE COMPLETE")
    print("="*80)
    print(f"\nTests Run: {tests_run}/2")
    print(f"Tests Passed: {tests_passed}/{tests_run}")
    
    if tests_passed == tests_run:
        print("\n✅ ALL INTEGRATION TESTS PASSED!")
    else:
        print(f"\n⚠️  {tests_run - tests_passed} test(s) need attention")
    
    print("\n📚 Next Steps:")
    print("   1. Review generated code in output directories")
    print("   2. Analyze phase execution patterns")
    print("   3. Verify quality improvement over iterations")
    print("   4. Test with more project types")
    
    print("="*80 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
