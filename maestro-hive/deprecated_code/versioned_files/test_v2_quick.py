#!/usr/bin/env python3
"""
Quick Test: Team Execution V2 - Basic Workflow

This tests the basic workflow without requiring Claude SDK:
1. AI analyzes requirement (fallback mode)
2. Blueprint selected
3. Contracts designed
4. Team structure ready

Run this to verify the system is working.
"""

import asyncio
import sys
import json
import logging
from pathlib import Path

# Add paths
sys.path.insert(0, str(Path(__file__).parent))

# Import V2 system
from team_execution_v2 import TeamExecutionEngineV2, TeamComposerAgent, ContractDesignerAgent

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s"
)

logger = logging.getLogger(__name__)


async def test_requirement_analysis():
    """Test AI requirement analysis"""
    print("\n" + "="*70)
    print("TEST 1: Requirement Analysis")
    print("="*70)
    
    agent = TeamComposerAgent()
    
    requirement = "Build a REST API for managing tasks with Node.js and PostgreSQL"
    
    try:
        classification = await agent.analyze_requirement(requirement)
        
        print(f"✅ Analysis complete:")
        print(f"   Type: {classification.requirement_type}")
        print(f"   Complexity: {classification.complexity.value}")
        print(f"   Parallelizability: {classification.parallelizability.value}")
        print(f"   Effort: {classification.estimated_effort_hours}h")
        print(f"   Confidence: {classification.confidence_score:.0%}")
        print(f"   Required skills: {', '.join(classification.required_expertise)}")
        
        return True
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_blueprint_recommendation():
    """Test blueprint recommendation"""
    print("\n" + "="*70)
    print("TEST 2: Blueprint Recommendation")
    print("="*70)
    
    agent = TeamComposerAgent()
    
    # Create mock classification
    from team_execution_v2 import RequirementClassification, RequirementComplexity, ParallelizabilityLevel
    
    classification = RequirementClassification(
        requirement_type="feature_development",
        complexity=RequirementComplexity.MODERATE,
        parallelizability=ParallelizabilityLevel.FULLY_PARALLEL,
        required_expertise=["backend", "frontend"],
        estimated_effort_hours=8.0,
        dependencies=[],
        risks=[],
        rationale="Test classification",
        confidence_score=0.9
    )
    
    try:
        recommendation = await agent.recommend_blueprint(classification)
        
        print(f"✅ Blueprint recommended:")
        print(f"   ID: {recommendation.blueprint_id}")
        print(f"   Name: {recommendation.blueprint_name}")
        print(f"   Match score: {recommendation.match_score:.0%}")
        print(f"   Execution: {recommendation.execution_mode}")
        print(f"   Coordination: {recommendation.coordination_mode}")
        print(f"   Team: {', '.join(recommendation.personas)}")
        print(f"   Est. savings: {recommendation.estimated_time_savings:.0%}")
        
        return True
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_contract_design():
    """Test contract design"""
    print("\n" + "="*70)
    print("TEST 3: Contract Design")
    print("="*70)
    
    designer = ContractDesignerAgent()
    
    # Create mock inputs
    from team_execution_v2 import (
        RequirementClassification, RequirementComplexity, ParallelizabilityLevel,
        BlueprintRecommendation
    )
    
    classification = RequirementClassification(
        requirement_type="feature_development",
        complexity=RequirementComplexity.MODERATE,
        parallelizability=ParallelizabilityLevel.FULLY_PARALLEL,
        required_expertise=["backend", "frontend"],
        estimated_effort_hours=8.0,
        dependencies=[],
        risks=[],
        rationale="Test",
        confidence_score=0.9
    )
    
    blueprint = BlueprintRecommendation(
        blueprint_id="parallel-contract-first",
        blueprint_name="Parallel Contract-First",
        match_score=0.85,
        personas=["backend_developer", "frontend_developer", "qa_engineer"],
        rationale="Test",
        alternatives=[],
        execution_mode="parallel",
        coordination_mode="contract",
        scaling_strategy="static",
        estimated_time_savings=0.4
    )
    
    requirement = "Build a REST API for managing tasks"
    
    try:
        contracts = await designer.design_contracts(
            requirement,
            classification,
            blueprint
        )
        
        print(f"✅ Contracts designed: {len(contracts)}")
        for contract in contracts:
            print(f"   • {contract.name}")
            print(f"     Provider: {contract.provider_persona_id}")
            print(f"     Consumers: {', '.join(contract.consumer_persona_ids)}")
            print(f"     Type: {contract.contract_type}")
            print(f"     Mock available: {contract.mock_available}")
            print(f"     Deliverables: {len(contract.deliverables)}")
        
        return True
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_full_workflow():
    """Test complete workflow"""
    print("\n" + "="*70)
    print("TEST 4: Full Workflow (Analysis Only)")
    print("="*70)
    
    engine = TeamExecutionEngineV2(output_dir="./test_v2_output")
    
    requirement = """
    Build a simple task management API:
    - REST API with Node.js
    - CRUD operations for tasks
    - PostgreSQL database
    - Basic authentication
    """
    
    try:
        # Note: This will only do analysis, not full execution
        # because Claude SDK is not available
        print("⚠️  Note: Full execution requires Claude SDK")
        print("   This test will validate the analysis pipeline only")
        print("")
        
        result = await engine.execute(
            requirement=requirement,
            constraints={"prefer_parallel": True}
        )
        
        print(f"\n✅ Workflow complete!")
        print(f"   Success: {result['success']}")
        print(f"   Classification: {result['classification']['type']}")
        print(f"   Blueprint: {result['blueprint']['name']}")
        print(f"   Team size: {result['team']['size']}")
        print(f"   Contracts: {len(result['contracts'])}")
        
        return True
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run all tests"""
    print("""
╔══════════════════════════════════════════════════════════════════════╗
║                                                                      ║
║   🧪  TEAM EXECUTION ENGINE V2 - QUICK TEST  🧪                      ║
║                                                                      ║
║   Testing: Analysis • Blueprints • Contracts                        ║
║                                                                      ║
╚══════════════════════════════════════════════════════════════════════╝
""")
    
    tests = [
        ("Requirement Analysis", test_requirement_analysis),
        ("Blueprint Recommendation", test_blueprint_recommendation),
        ("Contract Design", test_contract_design),
        ("Full Workflow", test_full_workflow),
    ]
    
    results = []
    
    for name, test_func in tests:
        try:
            result = await test_func()
            results.append((name, result))
        except Exception as e:
            logger.error(f"Test '{name}' crashed: {e}")
            results.append((name, False))
    
    # Print summary
    print("\n" + "="*70)
    print("📊 TEST SUMMARY")
    print("="*70)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {name}")
    
    print("="*70)
    print(f"Results: {passed}/{total} tests passed ({passed/total:.0%})")
    print("="*70)
    
    if passed == total:
        print("\n🎉 All tests passed! System is ready.")
        print("\nNext steps:")
        print("1. Set up Claude SDK for full execution")
        print("2. Run demo: python demo_v2_execution.py")
        print("3. Try real project: python team_execution_v2.py --requirement '...'")
    else:
        print(f"\n⚠️  {total - passed} test(s) failed. Please check errors above.")
    
    return passed == total


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
