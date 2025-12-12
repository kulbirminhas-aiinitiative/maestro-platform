#!/usr/bin/env python3.11
"""
Test Quality Fabric Integration with SDLC Team
Day 1 Integration Test
"""

import asyncio
import sys
from pathlib import Path

# Add to path
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent / "src"))

from maestro_hive.quality.quality_fabric_client import QualityFabricClient, PersonaType
from dataclasses import asdict


async def test_complete_workflow():
    """
    Test complete SDLC workflow with Quality Fabric integration
    """
    print("=" * 70)
    print("🚀 SDLC Team + Quality Fabric Integration Test")
    print("=" * 70)
    print()
    
    client = QualityFabricClient()
    
    # Step 1: Verify Quality Fabric is running
    print("Step 1: Verify Quality Fabric Health")
    print("-" * 70)
    health = await client.health_check()
    
    if health.get("status") == "healthy":
        print("✅ Quality Fabric is healthy")
        print(f"   Service: {health.get('service', 'quality-fabric')}")
        print(f"   Version: {health.get('version', '1.0.0')}")
    else:
        print("⚠️  Quality Fabric health check:")
        print(f"   {health}")
        print("\n💡 Tip: Start Quality Fabric with:")
        print("   cd ~/projects/quality-fabric && docker-compose up -d")
    print()
    
    # Step 2: Simulate persona execution with validation
    print("Step 2: Execute Personas with Quality Validation")
    print("-" * 70)
    
    personas_to_test = [
        {
            "persona_id": "backend_dev_001",
            "persona_type": PersonaType.BACKEND_DEVELOPER,
            "output": {
                "code_files": [
                    {"name": "main.py", "lines": 150, "content": "# FastAPI application"},
                    {"name": "models.py", "lines": 80, "content": "# Pydantic models"},
                    {"name": "database.py", "lines": 60, "content": "# DB connection"}
                ],
                "test_files": [
                    {"name": "test_main.py", "lines": 120, "content": "# API tests"},
                    {"name": "test_models.py", "lines": 80, "content": "# Model tests"}
                ],
                "documentation": [
                    {"name": "API.md", "content": "# API Documentation"}
                ],
                "metadata": {
                    "execution_time": 45.2,
                    "files_created": 6
                }
            }
        },
        {
            "persona_id": "frontend_dev_001",
            "persona_type": PersonaType.FRONTEND_DEVELOPER,
            "output": {
                "code_files": [
                    {"name": "App.tsx", "lines": 200, "content": "# React app"},
                    {"name": "components/Header.tsx", "lines": 50},
                    {"name": "pages/Dashboard.tsx", "lines": 150}
                ],
                "test_files": [
                    {"name": "App.test.tsx", "lines": 100, "content": "# React tests"}
                ],
                "documentation": [
                    {"name": "COMPONENTS.md", "content": "# Component docs"}
                ],
                "metadata": {
                    "execution_time": 38.5,
                    "files_created": 5
                }
            }
        },
        {
            "persona_id": "qa_eng_001",
            "persona_type": PersonaType.QA_ENGINEER,
            "output": {
                "test_files": [
                    {"name": "test_integration.py", "lines": 200},
                    {"name": "test_e2e.py", "lines": 180},
                    {"name": "test_api.py", "lines": 150},
                    {"name": "test_auth.py", "lines": 120},
                    {"name": "test_database.py", "lines": 100},
                    {"name": "test_performance.py", "lines": 80}
                ],
                "documentation": [
                    {"name": "TEST_PLAN.md", "content": "# Test plan"},
                    {"name": "TEST_RESULTS.md", "content": "# Results"}
                ],
                "metadata": {
                    "execution_time": 52.3,
                    "files_created": 8,
                    "test_coverage": 85.5
                }
            }
        }
    ]
    
    persona_results = []
    
    for persona_data in personas_to_test:
        persona_id = persona_data["persona_id"]
        persona_type = persona_data["persona_type"]
        output = persona_data["output"]
        
        print(f"\n{persona_type.value.replace('_', ' ').title()}")
        print(f"  ID: {persona_id}")
        
        # Validate output
        result = await client.validate_persona_output(
            persona_id=persona_id,
            persona_type=persona_type,
            output=output
        )
        
        persona_results.append(asdict(result))
        
        # Display results
        status_icon = {"pass": "✅", "warning": "⚠️", "fail": "❌"}[result.status]
        print(f"  Status: {status_icon} {result.status.upper()}")
        print(f"  Quality Score: {result.overall_score:.1%}")
        print(f"  Gates Passed: {len(result.gates_passed)}/{len(result.gates_passed) + len(result.gates_failed)}")
        
        if result.gates_passed:
            print(f"  ✓ {', '.join(result.gates_passed)}")
        
        if result.gates_failed:
            print(f"  ✗ {', '.join(result.gates_failed)}")
        
        if result.recommendations:
            print(f"  💡 Recommendations:")
            for rec in result.recommendations:
                print(f"     • {rec}")
        
        # Simulate reflection if needed
        if result.requires_revision:
            print(f"  🔄 Triggering reflection loop...")
            print(f"     (Would refine output based on recommendations)")
    
    print()
    
    # Step 3: Evaluate phase gate
    print("Step 3: Evaluate Phase Gate Transition")
    print("-" * 70)
    
    phase_result = await client.evaluate_phase_gate(
        current_phase="implementation",
        next_phase="testing",
        phase_outputs={
            "total_code_files": sum(len(p["output"].get("code_files", [])) for p in personas_to_test),
            "total_test_files": sum(len(p["output"].get("test_files", [])) for p in personas_to_test),
        },
        persona_results=persona_results
    )
    
    print(f"\nPhase Transition: {phase_result.get('phase', 'unknown')} → {phase_result.get('next_phase', 'unknown')}")
    
    status_icon = {"pass": "✅", "warning": "⚠️", "fail": "❌"}[phase_result['status']]
    print(f"Status: {status_icon} {phase_result['status'].upper()}")
    print(f"Overall Quality: {phase_result['overall_quality_score']:.1%}")
    
    if phase_result['gates_passed']:
        print(f"Gates Passed: {', '.join(phase_result['gates_passed'])}")
    
    if phase_result['gates_failed']:
        print(f"Gates Failed: {', '.join(phase_result['gates_failed'])}")
    
    if phase_result['recommendations']:
        print(f"Recommendations:")
        for rec in phase_result['recommendations']:
            print(f"  • {rec}")
    
    print()
    
    # Step 4: Summary
    print("=" * 70)
    print("📊 Test Summary")
    print("=" * 70)
    
    total_personas = len(persona_results)
    passed_personas = sum(1 for r in persona_results if r["status"] == "pass")
    avg_quality = sum(r["overall_score"] for r in persona_results) / total_personas
    
    print(f"\nPersonas Tested: {total_personas}")
    print(f"Personas Passed: {passed_personas}/{total_personas}")
    print(f"Average Quality: {avg_quality:.1%}")
    print(f"Phase Gate: {phase_result['status'].upper()}")
    
    if phase_result['status'] == "pass":
        print("\n✅ All quality checks passed - ready to proceed!")
    elif phase_result['status'] == "warning":
        print("\n⚠️  Quality checks passed with warnings - review recommended")
    else:
        print("\n❌ Quality checks failed - improvements required")
    
    print("\n" + "=" * 70)
    print("🎉 Integration Test Complete!")
    print("=" * 70)
    print()
    
    return phase_result['status'] == "pass"


async def test_reflection_pattern():
    """
    Test reflection pattern for quality improvement
    """
    print("\n" + "=" * 70)
    print("🔄 Testing Reflection Pattern for Quality Improvement")
    print("=" * 70)
    print()
    
    client = QualityFabricClient()
    
    # Simulate low-quality output
    print("Iteration 1: Initial Output (Low Quality)")
    print("-" * 70)
    
    initial_output = {
        "code_files": [
            {"name": "main.py", "content": "# Minimal code"}
        ],
        "test_files": [],  # No tests
        "documentation": []
    }
    
    result_1 = await client.validate_persona_output(
        persona_id="backend_dev_reflection",
        persona_type=PersonaType.BACKEND_DEVELOPER,
        output=initial_output
    )
    
    print(f"Status: {result_1.status}")
    print(f"Score: {result_1.overall_score:.1%}")
    print(f"Issues: {', '.join(result_1.gates_failed)}")
    print()
    
    if result_1.requires_revision:
        # Simulate improvement based on recommendations
        print("Iteration 2: After Reflection (Improved)")
        print("-" * 70)
        
        improved_output = {
            "code_files": [
                {"name": "main.py", "content": "# Full implementation"},
                {"name": "models.py", "content": "# Data models"}
            ],
            "test_files": [
                {"name": "test_main.py", "content": "# Comprehensive tests"}
            ],
            "documentation": [
                {"name": "README.md", "content": "# Documentation"}
            ]
        }
        
        result_2 = await client.validate_persona_output(
            persona_id="backend_dev_reflection",
            persona_type=PersonaType.BACKEND_DEVELOPER,
            output=improved_output
        )
        
        print(f"Status: {result_2.status}")
        print(f"Score: {result_2.overall_score:.1%}")
        print(f"Improvement: +{(result_2.overall_score - result_1.overall_score):.1%}")
        print()
        
        if result_2.status == "pass":
            print("✅ Quality improved through reflection!")
        else:
            print("⚠️  May need another iteration")
    
    print()


if __name__ == "__main__":
    async def main():
        # Run main workflow test
        success = await test_complete_workflow()
        
        # Run reflection pattern test
        await test_reflection_pattern()
        
        # Exit code
        sys.exit(0 if success else 1)
    
    asyncio.run(main())
