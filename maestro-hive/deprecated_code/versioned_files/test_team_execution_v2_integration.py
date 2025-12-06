#!/usr/bin/env python3
"""
Integration Test for Team Execution V2 System
Tests the AI-driven workflow with contracts and personas
"""

import sys
import os
import asyncio
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "synth"))

def test_simple_feature_development():
    """Test simple feature development with parallel team"""
    print("\n" + "="*80)
    print("🧪 TEST 1: Simple Feature Development (Parallel Team)")
    print("="*80)
    
    # Import after path setup
    from team_execution_v2 import TeamExecutionEngineV2
    
    requirement = """
    Build a simple user registration API with the following:
    - POST /api/register endpoint
    - Accept: username, email, password
    - Return: user_id and success message
    - Include basic input validation
    """
    
    print(f"\n📋 Requirement:\n{requirement}")
    print("\n🚀 Starting execution...\n")
    
    async def run_test():
        # Create engine
        engine = TeamExecutionEngineV2(
            output_dir="./test_v2_integration_output/test1_simple_api"
        )
        
        # Execute with prefer_parallel
        constraints = {
            "prefer_parallel": True,
            "quality_threshold": 0.80
        }
        
        result = await engine.execute(
            requirement=requirement,
            constraints=constraints
        )
        
        return result
    
    try:
        # Run synchronously for testing
        result = asyncio.run(run_test())
        
        print("\n" + "="*80)
        print("✅ TEST 1 COMPLETED")
        print("="*80)
        print(f"\n📊 Results:")
        print(f"  - Classification: {result.get('classification', {}).get('requirement_type', 'unknown')}")
        print(f"  - Complexity: {result.get('classification', {}).get('complexity', 'unknown')}")
        print(f"  - Blueprint: {result.get('blueprint', {}).get('name', 'unknown')}")
        print(f"  - Execution Mode: {result.get('blueprint', {}).get('execution_mode', 'unknown')}")
        print(f"  - Team Size: {result.get('execution', {}).get('personas_executed', 0)} personas")
        print(f"  - Time Savings: {result.get('execution', {}).get('time_savings_percent', 0)*100:.0f}%")
        print(f"  - Quality Score: {result.get('quality', {}).get('overall_quality_score', 0)*100:.0f}%")
        
        if result.get('deliverables'):
            print(f"\n📦 Deliverables: {len(result['deliverables'])} personas delivered")
        
        return True
        
    except Exception as e:
        print(f"\n❌ TEST 1 FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_collaborative_feature():
    """Test collaborative team for complex feature"""
    print("\n" + "="*80)
    print("🧪 TEST 2: Collaborative Feature (Consensus Team)")
    print("="*80)
    
    from team_execution_v2 import TeamExecutionEngineV2
    
    requirement = """
    Design a payment processing system architecture with:
    - Multiple payment providers (Stripe, PayPal)
    - Retry logic and error handling
    - Transaction logging
    - Security considerations
    
    This requires collaborative design and consensus.
    """
    
    print(f"\n📋 Requirement:\n{requirement}")
    print("\n🚀 Starting execution...\n")
    
    async def run_test():
        engine = TeamExecutionEngineV2(
            output_dir="./test_v2_integration_output/test2_payment_system"
        )
        
        constraints = {
            "prefer_parallel": False,  # Complex design may need consensus
            "quality_threshold": 0.85
        }
        
        result = await engine.execute(
            requirement=requirement,
            constraints=constraints
        )
        
        return result
    
    try:
        result = asyncio.run(run_test())
        
        print("\n" + "="*80)
        print("✅ TEST 2 COMPLETED")
        print("="*80)
        print(f"\n📊 Results:")
        print(f"  - Classification: {result.get('classification', {}).get('requirement_type', 'unknown')}")
        print(f"  - Blueprint: {result.get('blueprint', {}).get('name', 'unknown')}")
        print(f"  - Coordination: {result.get('blueprint', {}).get('coordination_mode', 'unknown')}")
        print(f"  - Quality Score: {result.get('quality', {}).get('overall_quality_score', 0)*100:.0f}%")
        
        return True
        
    except Exception as e:
        print(f"\n❌ TEST 2 FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_bug_fix_workflow():
    """Test bug fix with sequential handoff"""
    print("\n" + "="*80)
    print("🧪 TEST 3: Bug Fix Workflow (Sequential Team)")
    print("="*80)
    
    from team_execution_v2 import TeamExecutionEngineV2
    
    requirement = """
    Fix a bug in user authentication:
    - Users can't login after password reset
    - Error: "Invalid session token"
    - Appears to be a token expiry issue
    
    Investigate, fix, and verify.
    """
    
    print(f"\n📋 Requirement:\n{requirement}")
    print("\n🚀 Starting execution...\n")
    
    async def run_test():
        engine = TeamExecutionEngineV2(
            output_dir="./test_v2_integration_output/test3_bug_fix"
        )
        
        constraints = {
            "prefer_parallel": False,  # Bug fixes are sequential
            "quality_threshold": 0.90  # Higher quality for fixes
        }
        
        result = await engine.execute(
            requirement=requirement,
            constraints=constraints
        )
        
        return result
    
    try:
        result = asyncio.run(run_test())
        
        print("\n" + "="*80)
        print("✅ TEST 3 COMPLETED")
        print("="*80)
        print(f"\n📊 Results:")
        print(f"  - Classification: {result.get('classification', {}).get('requirement_type', 'unknown')}")
        print(f"  - Specialization: {result.get('classification', {}).get('specialization', 'unknown')}")
        print(f"  - Blueprint: {result.get('blueprint', {}).get('name', 'unknown')}")
        print(f"  - Quality Score: {result.get('quality', {}).get('overall_quality_score', 0)*100:.0f}%")
        
        return True
        
    except Exception as e:
        print(f"\n❌ TEST 3 FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all integration tests"""
    print("\n" + "="*80)
    print("🎯 TEAM EXECUTION V2 - INTEGRATION TEST SUITE")
    print("="*80)
    print("\nThis will test:")
    print("  1. ✅ Simple feature development (Parallel)")
    print("  2. ✅ Collaborative design (Consensus)")
    print("  3. ✅ Bug fix workflow (Sequential)")
    print("\n" + "="*80 + "\n")
    
    results = []
    
    # Test 1: Simple feature (should work with minimal dependencies)
    try:
        result1 = test_simple_feature_development()
        results.append(("Simple Feature Development", result1))
    except Exception as e:
        print(f"Test 1 crashed: {e}")
        results.append(("Simple Feature Development", False))
    
    # Test 2: Collaborative feature
    try:
        result2 = test_collaborative_feature()
        results.append(("Collaborative Feature", result2))
    except Exception as e:
        print(f"Test 2 crashed: {e}")
        results.append(("Collaborative Feature", False))
    
    # Test 3: Bug fix
    try:
        result3 = test_bug_fix_workflow()
        results.append(("Bug Fix Workflow", result3))
    except Exception as e:
        print(f"Test 3 crashed: {e}")
        results.append(("Bug Fix Workflow", False))
    
    # Summary
    print("\n" + "="*80)
    print("📊 TEST SUMMARY")
    print("="*80)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {status} - {name}")
    
    print(f"\n  Total: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n  🎉 All tests passed!")
        return 0
    else:
        print(f"\n  ⚠️  {total - passed} test(s) failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
