#!/usr/bin/env python3
"""
Simple Test for Team Execution V2

Tests the team_execution_v2 engine with a simple requirement
to verify all components are working correctly.
"""

import asyncio
import sys
import logging
from pathlib import Path
import json
from datetime import datetime

# Setup paths
sys.path.insert(0, str(Path(__file__).parent))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s"
)

logger = logging.getLogger(__name__)


async def test_simple_calculator():
    """Test with a simple calculator requirement"""
    
    print("\n" + "="*80)
    print("🧪 SIMPLE TEST: Calculator Application")
    print("="*80)
    
    requirement = """
    Create a simple calculator web application with the following features:
    - Basic arithmetic operations (add, subtract, multiply, divide)
    - Clean, responsive UI with buttons for numbers and operations
    - Display for showing current input and results
    - Clear button to reset the calculator
    - Handle division by zero gracefully
    """
    
    try:
        # Import the engine
        from team_execution_v2 import TeamExecutionEngineV2
        
        # Create output directory
        output_dir = Path(__file__).parent / "test_simple_output"
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize engine
        logger.info("Initializing Team Execution Engine V2...")
        engine = TeamExecutionEngineV2(output_dir=str(output_dir))
        
        # Execute
        logger.info("Executing requirement...")
        result = await engine.execute(
            requirement=requirement,
            constraints={
                "prefer_parallel": True,
                "quality_threshold": 0.75
            }
        )
        
        # Display results
        print("\n" + "="*80)
        print("✅ TEST COMPLETED SUCCESSFULLY")
        print("="*80)
        
        print("\n📊 Results Summary:")
        print(f"   ✓ Success: {result['success']}")
        print(f"   ✓ Session ID: {result['session_id']}")
        print(f"   ✓ Duration: {result['duration_seconds']:.2f}s")
        
        print("\n📋 Classification:")
        cls = result['classification']
        print(f"   ✓ Type: {cls['type']}")
        print(f"   ✓ Complexity: {cls['complexity']}")
        print(f"   ✓ Parallelizability: {cls['parallelizability']}")
        print(f"   ✓ Estimated Effort: {cls['effort_hours']}h")
        print(f"   ✓ Confidence: {cls['confidence']:.0%}")
        
        print("\n🎯 Blueprint:")
        bp = result['blueprint']
        print(f"   ✓ ID: {bp['id']}")
        print(f"   ✓ Name: {bp['name']}")
        print(f"   ✓ Match Score: {bp['match_score']:.0%}")
        print(f"   ✓ Execution Mode: {bp['execution_mode']}")
        print(f"   ✓ Time Savings: {bp['estimated_time_savings']:.0%}")
        
        print("\n👥 Team:")
        team = result['team']
        print(f"   ✓ Size: {team['size']} personas")
        print(f"   ✓ Members: {', '.join(team['personas'])}")
        
        print("\n📝 Contracts:")
        print(f"   ✓ Total: {result['contracts']['total']}")
        print(f"   ✓ Fulfilled: {result['contracts']['fulfilled']}")
        print(f"   ✓ Fulfillment Rate: {result['contracts']['fulfillment_rate']:.0%}")
        
        print("\n⚡ Execution:")
        exe = result['execution']
        print(f"   ✓ Parallel Duration: {exe['parallel_duration']:.2f}s")
        print(f"   ✓ Sequential Duration: {exe['sequential_duration']:.2f}s")
        print(f"   ✓ Time Savings: {exe['time_savings']:.0%}")
        print(f"   ✓ Parallelization Achieved: {exe['parallelization_achieved']:.0%}")
        
        print("\n🎯 Quality:")
        qual = result['quality']
        print(f"   ✓ Overall Score: {qual['overall_quality_score']:.0%}")
        print(f"   ✓ Contracts Fulfilled: {qual['contracts_fulfilled']}/{qual['contracts_total']}")
        print(f"   ✓ Integration Issues: {qual['integration_issues']}")
        
        print("\n📁 Output:")
        print(f"   ✓ Project Directory: {result['project_dir']}")
        
        # Save full result
        result_file = output_dir / f"result_{result['session_id']}.json"
        with open(result_file, 'w') as f:
            json.dump(result, indent=2, fp=f)
        print(f"   ✓ Full result saved: {result_file}")
        
        print("\n" + "="*80)
        print("🎉 All checks passed!")
        print("="*80)
        
        return True
        
    except Exception as e:
        print("\n" + "="*80)
        print("❌ TEST FAILED")
        print("="*80)
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_todo_list():
    """Test with a simple to-do list requirement"""
    
    print("\n" + "="*80)
    print("🧪 SIMPLE TEST: To-Do List Application")
    print("="*80)
    
    requirement = """
    Create a simple to-do list web application:
    - Add new tasks with a text input
    - Display list of tasks
    - Mark tasks as complete/incomplete with checkboxes
    - Delete tasks with a delete button
    - Filter tasks: All, Active, Completed
    - Task count showing active tasks
    - Clean, modern UI
    """
    
    try:
        from team_execution_v2 import TeamExecutionEngineV2
        
        output_dir = Path(__file__).parent / "test_todo_output"
        output_dir.mkdir(parents=True, exist_ok=True)
        
        engine = TeamExecutionEngineV2(output_dir=str(output_dir))
        
        result = await engine.execute(
            requirement=requirement,
            constraints={"prefer_parallel": True, "quality_threshold": 0.75}
        )
        
        print("\n✅ To-Do List test completed successfully!")
        print(f"   Classification: {result['classification']['type']}")
        print(f"   Blueprint: {result['blueprint']['name']}")
        print(f"   Team: {', '.join(result['team']['personas'])}")
        print(f"   Quality: {result['quality']['overall_quality_score']:.0%}")
        print(f"   Duration: {result['duration_seconds']:.2f}s")
        
        return True
        
    except Exception as e:
        print(f"\n❌ To-Do List test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run all simple tests"""
    
    print("\n" + "="*80)
    print("🚀 TEAM EXECUTION V2 - SIMPLE TESTS")
    print("="*80)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80)
    
    results = []
    
    # Test 1: Calculator
    print("\n📝 Test 1: Calculator Application")
    result1 = await test_simple_calculator()
    results.append(("Calculator", result1))
    
    # Test 2: To-Do List
    print("\n📝 Test 2: To-Do List Application")
    result2 = await test_todo_list()
    results.append(("To-Do List", result2))
    
    # Summary
    print("\n" + "="*80)
    print("📊 TEST SUMMARY")
    print("="*80)
    
    for name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"   {status} - {name}")
    
    total = len(results)
    passed = sum(1 for _, p in results if p)
    
    print("\n" + "-"*80)
    print(f"   Total: {total} | Passed: {passed} | Failed: {total - passed}")
    print("="*80)
    
    if passed == total:
        print("🎉 ALL TESTS PASSED!")
    else:
        print("⚠️  SOME TESTS FAILED")
    
    print("="*80)
    print(f"Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80)
    
    return passed == total


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
