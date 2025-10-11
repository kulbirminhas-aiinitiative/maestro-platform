#!/usr/bin/env python3
"""
Demo: Team Execution V2 - Complete Workflow

This demonstrates the complete V2 workflow:
1. AI analyzes requirement
2. Blueprint selected from catalog
3. Contracts designed
4. Team executes in parallel
5. Contract validation
6. Quality assessment

Run this to see the full system in action!
"""

import asyncio
import sys
import json
import logging
from pathlib import Path
from datetime import datetime

# Add paths
sys.path.insert(0, str(Path(__file__).parent))

# Import our V2 system
from team_execution_v2 import TeamExecutionEngineV2

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s"
)

logger = logging.getLogger(__name__)


async def demo_scenario_1_parallel():
    """
    Scenario 1: Full-Stack Web Application (Parallel Execution)
    
    This should trigger:
    - AI analysis: feature_development, partially_parallel
    - Blueprint: parallel-contract-first
    - Contracts: Backend API + Frontend UI
    - Execution: Backend and Frontend work in parallel with mock API
    """
    print("\n" + "="*80)
    print("🎬 SCENARIO 1: Full-Stack Web Application (Parallel)")
    print("="*80)
    
    requirement = """
    Build a task management web application with:
    - Backend REST API with Node.js/Express
    - PostgreSQL database
    - Frontend React application
    - User authentication
    - CRUD operations for tasks
    - Real-time updates
    
    The backend should provide a REST API that the frontend consumes.
    """
    
    engine = TeamExecutionEngineV2(
        output_dir="./demo_v2_parallel"
    )
    
    result = await engine.execute(
        requirement=requirement,
        constraints={
            "prefer_parallel": True,
            "quality_threshold": 0.80
        }
    )
    
    print("\n" + "="*80)
    print("📊 SCENARIO 1 RESULT")
    print("="*80)
    print(json.dumps(result, indent=2, default=str))
    print("="*80)
    
    return result


async def demo_scenario_2_sequential():
    """
    Scenario 2: Algorithm Optimization (Sequential Execution)
    
    This should trigger:
    - AI analysis: performance_optimization, fully_sequential
    - Blueprint: sequential-basic
    - Contracts: Sequential deliverables
    - Execution: One persona after another
    """
    print("\n" + "="*80)
    print("🎬 SCENARIO 2: Algorithm Optimization (Sequential)")
    print("="*80)
    
    requirement = """
    Optimize the sorting algorithm in our data processing pipeline.
    The current implementation is O(n²) and needs to be O(n log n).
    Must maintain backward compatibility.
    """
    
    engine = TeamExecutionEngineV2(
        output_dir="./demo_v2_sequential"
    )
    
    result = await engine.execute(
        requirement=requirement
    )
    
    print("\n" + "="*80)
    print("📊 SCENARIO 2 RESULT")
    print("="*80)
    print(json.dumps(result, indent=2, default=str))
    print("="*80)
    
    return result


async def demo_scenario_3_complex():
    """
    Scenario 3: Microservices Architecture (Complex, Parallel)
    
    This should trigger:
    - AI analysis: feature_development, complex, fully_parallel
    - Blueprint: parallel-elastic
    - Contracts: Multiple API contracts
    - Execution: Multiple services in parallel
    """
    print("\n" + "="*80)
    print("🎬 SCENARIO 3: Microservices Architecture (Complex)")
    print("="*80)
    
    requirement = """
    Build a microservices-based e-commerce platform with:
    
    Services:
    - User Service (authentication, profiles)
    - Product Service (catalog, inventory)
    - Order Service (cart, checkout)
    - Payment Service (payment processing)
    - Notification Service (email, SMS)
    
    Requirements:
    - Each service has its own database
    - Services communicate via REST APIs
    - API Gateway for routing
    - Message queue for async operations
    - Kubernetes deployment configs
    """
    
    engine = TeamExecutionEngineV2(
        output_dir="./demo_v2_complex"
    )
    
    result = await engine.execute(
        requirement=requirement,
        constraints={
            "prefer_parallel": True,
            "quality_threshold": 0.85
        }
    )
    
    print("\n" + "="*80)
    print("📊 SCENARIO 3 RESULT")
    print("="*80)
    print(json.dumps(result, indent=2, default=str))
    print("="*80)
    
    return result


async def demo_comparison():
    """
    Run comparison between scenarios to show time savings
    """
    print("\n" + "="*80)
    print("📊 COMPARATIVE ANALYSIS")
    print("="*80)
    
    scenarios = {
        "Scenario 1 (Parallel)": demo_scenario_1_parallel,
        "Scenario 2 (Sequential)": demo_scenario_2_sequential,
        "Scenario 3 (Complex)": demo_scenario_3_complex
    }
    
    results = {}
    
    for name, func in scenarios.items():
        try:
            result = await func()
            results[name] = result
        except Exception as e:
            logger.error(f"❌ {name} failed: {e}")
            import traceback
            traceback.print_exc()
    
    # Print comparison table
    print("\n" + "="*80)
    print("📊 COMPARISON SUMMARY")
    print("="*80)
    print(f"{'Scenario':<30} {'Duration':<15} {'Savings':<15} {'Quality':<10}")
    print("-"*80)
    
    for name, result in results.items():
        if result.get("execution"):
            duration = result["execution"]["total_duration"]
            savings = result["execution"]["time_savings_percent"]
            quality = result["quality"]["overall_quality_score"]
            
            print(f"{name:<30} {duration:>8.1f}s {savings:>12.0%} {quality:>8.0%}")
    
    print("="*80)
    
    # Summary insights
    print("\n🔍 KEY INSIGHTS:")
    print("")
    
    for name, result in results.items():
        if result.get("execution"):
            print(f"{name}:")
            print(f"  • Classification: {result['classification']['type']}")
            print(f"  • Parallelizability: {result['classification']['parallelizability']}")
            print(f"  • Blueprint: {result['blueprint']['name']}")
            print(f"  • Time savings: {result['execution']['time_savings_percent']:.0%}")
            print(f"  • Parallelization: {result['execution']['parallelization_achieved']:.0%}")
            print(f"  • Quality: {result['quality']['overall_quality_score']:.0%}")
            print("")


async def main():
    """Main entry point"""
    print("""
╔══════════════════════════════════════════════════════════════════════╗
║                                                                      ║
║   🚀  TEAM EXECUTION ENGINE V2 - DEMONSTRATION  🚀                   ║
║                                                                      ║
║   AI-Driven • Blueprint-Based • Contract-First • Parallel           ║
║                                                                      ║
╚══════════════════════════════════════════════════════════════════════╝
""")
    
    print("This demo shows the complete V2 workflow:")
    print("1. ✅ AI analyzes requirements (no hardcoded keywords)")
    print("2. ✅ Blueprint selected from catalog (12+ patterns)")
    print("3. ✅ Contracts designed (clear interfaces)")
    print("4. ✅ Team executes in parallel (with mocks)")
    print("5. ✅ Contract validation (fulfillment check)")
    print("6. ✅ Quality assessment (comprehensive scoring)")
    print("")
    
    # Choose which demos to run
    print("Select demo to run:")
    print("1. Scenario 1: Full-Stack Web App (Parallel)")
    print("2. Scenario 2: Algorithm Optimization (Sequential)")
    print("3. Scenario 3: Microservices (Complex, Parallel)")
    print("4. ALL: Run all scenarios + comparison")
    print("")
    
    choice = input("Enter choice (1-4) [default: 1]: ").strip() or "1"
    
    if choice == "1":
        await demo_scenario_1_parallel()
    elif choice == "2":
        await demo_scenario_2_sequential()
    elif choice == "3":
        await demo_scenario_3_complex()
    elif choice == "4":
        await demo_comparison()
    else:
        print(f"Invalid choice: {choice}")
        return
    
    print("\n" + "="*80)
    print("✅ DEMO COMPLETE")
    print("="*80)
    print("")
    print("Check output directories:")
    print("  • ./demo_v2_parallel/")
    print("  • ./demo_v2_sequential/")
    print("  • ./demo_v2_complex/")
    print("")
    print("Each contains:")
    print("  • Generated code and deliverables")
    print("  • Contract specifications")
    print("  • Mock implementations")
    print("  • Validation reports")
    print("")


if __name__ == "__main__":
    asyncio.run(main())
