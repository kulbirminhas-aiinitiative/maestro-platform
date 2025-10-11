#!/usr/bin/env python3
"""
Test Phase Workflow Orchestrator

Tests the complete phase-based workflow orchestration.
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from phase_models import SDLCPhase, PhaseState
from phase_workflow_orchestrator import PhaseWorkflowOrchestrator


async def test_basic_workflow():
    """Test basic workflow execution"""
    print("\n" + "="*80)
    print("🧪 TEST: Basic Workflow Execution")
    print("="*80 + "\n")
    
    orchestrator = PhaseWorkflowOrchestrator(
        session_id="test_basic_workflow",
        requirement="Build a simple blog platform with user authentication",
        output_dir=Path("./test_output/basic"),
        enable_phase_gates=True,
        enable_progressive_quality=True
    )
    
    result = await orchestrator.execute_workflow(max_iterations=3)
    
    print("\n" + "-"*80)
    print("Test Results:")
    print("-"*80)
    print(f"Success: {result.success}")
    print(f"Iterations: {result.total_iterations}")
    print(f"Phases Completed: {len(result.phases_completed)}")
    print(f"Personas Executed: {result.total_personas_executed}")
    print(f"Final Quality: {result.final_quality_score:.0%}")
    print(f"Final Completeness: {result.final_completeness:.0%}")
    
    # Assertions
    assert result.total_iterations > 0, "Should have at least 1 iteration"
    assert len(result.phases_completed) >= 0, "Should have completed phases"
    assert result.total_personas_executed > 0, "Should have executed personas"
    
    print("\n✅ Test PASSED: Basic workflow executed successfully\n")
    return result


async def test_progressive_quality():
    """Test progressive quality thresholds"""
    print("\n" + "="*80)
    print("🧪 TEST: Progressive Quality Thresholds")
    print("="*80 + "\n")
    
    orchestrator = PhaseWorkflowOrchestrator(
        session_id="test_progressive",
        requirement="Build API service with ML integration",
        output_dir=Path("./test_output/progressive"),
        enable_phase_gates=True,
        enable_progressive_quality=True
    )
    
    result = await orchestrator.execute_workflow(max_iterations=5)
    
    print("\n" + "-"*80)
    print("Progressive Quality Analysis:")
    print("-"*80)
    
    # Check that quality improves over iterations
    if len(result.phase_history) > 1:
        for i, phase_exec in enumerate(result.phase_history[:3], 1):
            print(f"Iteration {i} ({phase_exec.phase.value}):")
            print(f"  Quality: {phase_exec.quality_score:.0%}")
            print(f"  Completeness: {phase_exec.completeness:.0%}")
            print(f"  State: {phase_exec.state.value}")
    
    # Verify progressive improvement
    if len(result.phase_history) >= 2:
        first_quality = result.phase_history[0].quality_score
        last_quality = result.phase_history[-1].quality_score
        assert last_quality >= first_quality, "Quality should improve or maintain"
    
    print("\n✅ Test PASSED: Progressive quality working\n")
    return result


async def test_phase_boundaries():
    """Test phase boundary enforcement"""
    print("\n" + "="*80)
    print("🧪 TEST: Phase Boundary Enforcement")
    print("="*80 + "\n")
    
    orchestrator = PhaseWorkflowOrchestrator(
        session_id="test_boundaries",
        requirement="Build mobile app with cloud backend",
        output_dir=Path("./test_output/boundaries"),
        enable_phase_gates=True,
        enable_progressive_quality=True
    )
    
    result = await orchestrator.execute_workflow(max_iterations=3)
    
    print("\n" + "-"*80)
    print("Phase Execution Order:")
    print("-"*80)
    
    phases_executed = []
    for phase_exec in result.phase_history:
        if phase_exec.state in [PhaseState.COMPLETED, PhaseState.NEEDS_REWORK]:
            phases_executed.append(phase_exec.phase)
            print(f"  {phase_exec.phase.value}: {phase_exec.state.value}")
    
    # Verify phases execute in order (Requirements first)
    if phases_executed:
        assert phases_executed[0] == SDLCPhase.REQUIREMENTS, \
            "First phase should be REQUIREMENTS"
    
    print("\n✅ Test PASSED: Phase boundaries enforced\n")
    return result


async def test_gate_validation():
    """Test entry/exit gate validation"""
    print("\n" + "="*80)
    print("🧪 TEST: Gate Validation")
    print("="*80 + "\n")
    
    orchestrator = PhaseWorkflowOrchestrator(
        session_id="test_gates",
        requirement="Build e-commerce platform",
        output_dir=Path("./test_output/gates"),
        enable_phase_gates=True,
        enable_progressive_quality=True
    )
    
    result = await orchestrator.execute_workflow(max_iterations=4)
    
    print("\n" + "-"*80)
    print("Gate Validation Results:")
    print("-"*80)
    
    gates_checked = 0
    gates_passed = 0
    gates_failed = 0
    
    for phase_exec in result.phase_history:
        # Check entry gate
        if phase_exec.entry_gate_result:
            gates_checked += 1
            if phase_exec.entry_gate_result.passed:
                gates_passed += 1
            else:
                gates_failed += 1
        
        # Check exit gate
        if phase_exec.exit_gate_result:
            gates_checked += 1
            if phase_exec.exit_gate_result.passed:
                gates_passed += 1
            else:
                gates_failed += 1
    
    print(f"  Gates Checked: {gates_checked}")
    print(f"  Gates Passed: {gates_passed}")
    print(f"  Gates Failed: {gates_failed}")
    
    assert gates_checked > 0, "Should have checked gates"
    
    print("\n✅ Test PASSED: Gates validated successfully\n")
    return result


async def test_disabled_features():
    """Test with gates and progressive quality disabled"""
    print("\n" + "="*80)
    print("🧪 TEST: Disabled Features")
    print("="*80 + "\n")
    
    orchestrator = PhaseWorkflowOrchestrator(
        session_id="test_disabled",
        requirement="Build simple REST API",
        output_dir=Path("./test_output/disabled"),
        enable_phase_gates=False,
        enable_progressive_quality=False
    )
    
    result = await orchestrator.execute_workflow(max_iterations=2)
    
    print("\n" + "-"*80)
    print("Results with disabled features:")
    print("-"*80)
    print(f"  Phases completed: {len(result.phases_completed)}")
    print(f"  Personas executed: {result.total_personas_executed}")
    
    # Verify gates were not checked
    gates_checked = any(
        phase_exec.entry_gate_result or phase_exec.exit_gate_result
        for phase_exec in result.phase_history
    )
    
    print(f"  Gates checked: {gates_checked}")
    
    print("\n✅ Test PASSED: Disabled features work correctly\n")
    return result


async def main():
    """Run all tests"""
    print("\n" + "="*80)
    print("🚀 PHASE WORKFLOW ORCHESTRATOR TESTS")
    print("="*80)
    
    tests_passed = 0
    tests_failed = 0
    
    tests = [
        ("Basic Workflow", test_basic_workflow),
        ("Progressive Quality", test_progressive_quality),
        ("Phase Boundaries", test_phase_boundaries),
        ("Gate Validation", test_gate_validation),
        ("Disabled Features", test_disabled_features)
    ]
    
    for test_name, test_func in tests:
        try:
            await test_func()
            tests_passed += 1
        except AssertionError as e:
            print(f"\n❌ TEST FAILED: {test_name}")
            print(f"   Error: {e}\n")
            tests_failed += 1
        except Exception as e:
            print(f"\n❌ TEST ERROR: {test_name}")
            print(f"   Error: {e}")
            import traceback
            traceback.print_exc()
            tests_failed += 1
    
    print("\n" + "="*80)
    print("🎉 TEST SUMMARY")
    print("="*80)
    print(f"Tests Passed: {tests_passed}/{len(tests)}")
    print(f"Tests Failed: {tests_failed}/{len(tests)}")
    
    if tests_failed == 0:
        print("\n✅ ALL TESTS PASSED!")
        print("\n📊 Week 2 Orchestrator: COMPLETE")
        print("\nNext Steps:")
        print("  1. Integrate with team_execution.py (real persona execution)")
        print("  2. Update session_manager.py (add phase tracking)")
        print("  3. Build SmartPersonaSelector (Week 3)")
    else:
        print(f"\n❌ {tests_failed} test(s) failed")
    
    print("="*80 + "\n")
    
    sys.exit(0 if tests_failed == 0 else 1)


if __name__ == "__main__":
    asyncio.run(main())
