#!/usr/bin/env python3
"""
Simple Test for Team Execution V2
Tests the new AI-driven, blueprint-based, contract-first architecture.
"""

import asyncio
import sys
import os
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

# Check environment
def check_environment():
    """Check that required dependencies are available"""
    issues = []
    
    # Check for ANTHROPIC_API_KEY
    if not os.getenv("ANTHROPIC_API_KEY"):
        issues.append("❌ ANTHROPIC_API_KEY not set in environment")
    else:
        logger.info("✅ ANTHROPIC_API_KEY is set")
    
    # Check for anthropic package
    try:
        import anthropic
        logger.info("✅ anthropic package is installed")
    except ImportError:
        issues.append("❌ anthropic package not installed (pip install anthropic)")
    
    # Check for claude_code_sdk
    try:
        import claude_code_sdk
        logger.info("✅ claude_code_sdk module is available")
    except ImportError:
        issues.append("❌ claude_code_sdk module not found")
    
    # Check for team_execution_v2
    try:
        import team_execution_v2
        logger.info("✅ team_execution_v2 module is available")
    except ImportError as e:
        issues.append(f"❌ team_execution_v2 module not found: {e}")
    
    return issues


async def test_simple_requirement():
    """Test with a simple requirement"""
    logger.info("\n" + "="*70)
    logger.info("TEST: Simple Feature Request")
    logger.info("="*70 + "\n")
    
    try:
        from team_execution_v2 import TeamExecutionEngineV2
        
        # Create engine
        engine = TeamExecutionEngineV2()
        logger.info("✅ Created TeamExecutionEngineV2")
        
        # Simple requirement (just a string, not a complex object)
        requirement = "Create a simple REST API endpoint that returns 'Hello, World!' in JSON format using Python and FastAPI"
        
        logger.info(f"📋 Requirement: {requirement}")
        
        # Execute
        logger.info("\n🚀 Executing requirement...")
        result = await engine.execute(
            requirement=requirement,
            constraints={"prefer_parallel": False, "quality_threshold": 0.80}
        )
        
        # Display results
        logger.info("\n" + "="*70)
        logger.info("RESULTS")
        logger.info("="*70)
        
        # result is a dictionary
        if isinstance(result, dict):
            logger.info(f"\n✅ Classification: {result.get('classification', {}).get('requirement_type', 'N/A')}")
            logger.info(f"⏱️  Duration: {result.get('duration_seconds', 0):.2f}s")
            
            blueprint = result.get('blueprint', {})
            if blueprint:
                logger.info(f"🎨 Blueprint: {blueprint.get('name', 'N/A')}")
                logger.info(f"   Personas: {', '.join(blueprint.get('personas', []))}")
                logger.info(f"   Execution Mode: {blueprint.get('execution_mode', 'N/A')}")
            
            contracts = result.get('contracts', [])
            if contracts:
                logger.info(f"\n📜 Contracts: {len(contracts)}")
                for i, contract in enumerate(contracts, 1):
                    logger.info(f"   {i}. {contract.get('name', 'N/A')}")
                    logger.info(f"      Provider: {contract.get('provider_persona_id', 'N/A')}")
                    logger.info(f"      Consumers: {', '.join(contract.get('consumer_persona_ids', []))}")
            
            execution = result.get('execution', {})
            if execution:
                logger.info(f"\n⚡ Execution:")
                logger.info(f"   Time Savings: {execution.get('time_savings_percent', 0):.0%}")
                logger.info(f"   Parallelization: {execution.get('parallelization_achieved', 0):.0%}")
                logger.info(f"   Personas: {execution.get('personas_executed', 0)}")
            
            quality = result.get('quality', {})
            if quality:
                logger.info(f"\n📊 Quality:")
                logger.info(f"   Overall Score: {quality.get('overall_quality_score', 0):.0%}")
                logger.info(f"   Contracts Fulfilled: {quality.get('contracts_fulfilled', 0)}/{quality.get('contracts_total', 0)}")
        else:
            logger.info(f"\nResult: {result}")
        
        logger.info("\n" + "="*70)
        
        # Check if execution was successful
        success = isinstance(result, dict) and result.get('duration_seconds', 0) > 0
        return result, success
        
    except Exception as e:
        logger.error(f"❌ Test failed with error: {e}", exc_info=True)
        return None, False


async def test_ai_analysis_only():
    """Test just the AI analysis components without full execution"""
    logger.info("\n" + "="*70)
    logger.info("TEST: AI Analysis Only")
    logger.info("="*70 + "\n")
    
    try:
        from team_execution_v2 import TeamComposerAgent, RequirementComplexity
        
        # Create agent
        agent = TeamComposerAgent()
        logger.info("✅ Created TeamComposerAgent")
        
        # Simple requirement
        requirement = "Build a simple calculator API with add, subtract, multiply, divide operations"
        
        logger.info(f"📋 Requirement: {requirement}")
        
        # Analyze
        logger.info("\n🤖 Running AI analysis...")
        classification = await agent.analyze_requirement(requirement)
        
        # Display results
        logger.info(f"\n✅ Classification Complete:")
        
        # Handle both dict and object responses
        if isinstance(classification, dict):
            logger.info(f"   Type: {classification.get('requirement_type', 'N/A')}")
            logger.info(f"   Complexity: {classification.get('complexity', 'N/A')}")
            logger.info(f"   Parallelizability: {classification.get('parallelizability', 'N/A')}")
            logger.info(f"   Required Expertise: {', '.join(classification.get('required_expertise', []))}")
            logger.info(f"   Estimated Effort: {classification.get('estimated_effort_hours', 0):.1f} hours")
            logger.info(f"   Confidence: {classification.get('confidence_score', 0):.0%}")
            rationale = classification.get('rationale', '')
        else:
            # It's a RequirementClassification object
            logger.info(f"   Type: {classification.requirement_type}")
            logger.info(f"   Complexity: {classification.complexity.value}")
            logger.info(f"   Parallelizability: {classification.parallelizability.value}")
            logger.info(f"   Required Expertise: {', '.join(classification.required_expertise)}")
            logger.info(f"   Estimated Effort: {classification.estimated_effort_hours:.1f} hours")
            logger.info(f"   Confidence: {classification.confidence_score:.0%}")
            rationale = classification.rationale
        
        if rationale:
            logger.info(f"\n💡 Rationale: {rationale[:200]}...")
        
        logger.info("\n✅ AI analysis test completed")
        
        return classification, True
        
    except Exception as e:
        logger.error(f"❌ AI analysis test failed: {e}", exc_info=True)
        return None, False


async def main():
    """Run all tests"""
    logger.info("\n" + "="*80)
    logger.info(" 🧪 TEAM EXECUTION V2 - SIMPLE TEST SUITE")
    logger.info("="*80 + "\n")
    
    # Check environment
    logger.info("📋 Checking environment...")
    issues = check_environment()
    
    if issues:
        logger.warning("\n⚠️  Environment Issues Detected:")
        for issue in issues:
            logger.warning(f"   {issue}")
        logger.warning("\nSome tests may be skipped...\n")
    else:
        logger.info("\n✅ Environment check passed\n")
    
    # Run tests
    test_results = []
    
    # Test 1: AI Analysis only (lightweight, works without API key in fallback mode)
    logger.info("\n" + "-"*80)
    result1, passed1 = await test_ai_analysis_only()
    test_results.append(("AI Analysis", passed1))
    
    # Test 2: Full execution (requires API key and dependencies)
    if os.getenv("ANTHROPIC_API_KEY"):
        logger.info("\n" + "-"*80)
        result2, passed2 = await test_simple_requirement()
        test_results.append(("Full Execution", passed2))
    else:
        logger.info("\n⏭️  Skipping full execution test (no API key)")
        test_results.append(("Full Execution", None))  # Skipped
    
    # Summary
    logger.info("\n" + "="*80)
    logger.info(" 📊 TEST SUMMARY")
    logger.info("="*80 + "\n")
    
    for test_name, passed in test_results:
        if passed is None:
            logger.info(f"   ⏭️  {test_name}: SKIPPED")
        elif passed:
            logger.info(f"   ✅ {test_name}: PASSED")
        else:
            logger.info(f"   ❌ {test_name}: FAILED")
    
    # Overall result
    passed_count = sum(1 for _, p in test_results if p is True)
    failed_count = sum(1 for _, p in test_results if p is False)
    skipped_count = sum(1 for _, p in test_results if p is None)
    
    logger.info(f"\n   Total: {passed_count} passed, {failed_count} failed, {skipped_count} skipped")
    
    if failed_count == 0:
        logger.info("\n✅ All tests passed!")
    else:
        logger.info("\n❌ Some tests failed")
    
    logger.info("\n" + "="*80 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
