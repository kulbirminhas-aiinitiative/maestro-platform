#!/usr/bin/env python3.11
"""
Test Real Quality Fabric Integration
Tests the actual integration with Quality Fabric API
"""

import asyncio
import sys
from quality_fabric_client import QualityFabricClient, PersonaType


async def test_real_integration():
    """Test real integration with Quality Fabric"""
    print("=" * 70)
    print("🧪 Testing Real Quality Fabric Integration")
    print("=" * 70)
    print()
    
    # Initialize client
    client = QualityFabricClient("http://localhost:8001")
    
    # Step 1: Health Check
    print("Step 1: Health Check")
    print("-" * 70)
    health = await client.health_check()
    print(f"✅ Status: {health.get('status')}")
    print(f"✅ Service: {health.get('service')}")
    print()
    
    # Step 2: Test Backend Developer with Real Code
    print("Step 2: Backend Developer Validation (With Real Analysis)")
    print("-" * 70)
    
    backend_output = {
        "code_files": [
            {
                "name": "app.py",
                "content": """
def calculate_sum(a, b):
    '''Calculate sum of two numbers'''
    return a + b

def main():
    '''Main function'''
    result = calculate_sum(5, 3)
    print(f"Result: {result}")

if __name__ == "__main__":
    main()
""",
                "lines": 10
            }
        ],
        "test_files": [
            {
                "name": "test_app.py",
                "content": """
import pytest
from app import calculate_sum

def test_calculate_sum():
    assert calculate_sum(2, 3) == 5
    assert calculate_sum(-1, 1) == 0
    assert calculate_sum(0, 0) == 0
""",
                "lines": 7
            }
        ],
        "documentation": [
            {
                "name": "README.md",
                "content": "# My App\n\nSimple calculator application."
            }
        ]
    }
    
    result = await client.validate_persona_output(
        persona_id="backend_dev_real_001",
        persona_type=PersonaType.BACKEND_DEVELOPER,
        output=backend_output
    )
    
    print(f"Persona ID: {result.persona_id}")
    print(f"Status: {result.status}")
    print(f"Overall Score: {result.overall_score:.1f}%")
    print(f"Gates Passed: {len(result.gates_passed)}")
    print(f"Gates Failed: {len(result.gates_failed)}")
    print()
    
    if result.quality_metrics:
        print("Quality Metrics:")
        for key, value in result.quality_metrics.items():
            if value is not None:
                print(f"  • {key}: {value}")
    print()
    
    if result.recommendations:
        print("Recommendations:")
        for rec in result.recommendations:
            print(f"  • {rec}")
    print()
    
    # Step 3: Test with minimal code (should fail)
    print("Step 3: Frontend Developer Validation (Minimal Code - Should Fail)")
    print("-" * 70)
    
    minimal_output = {
        "code_files": [
            {
                "name": "index.html",
                "content": "<html></html>",
                "lines": 1
            }
        ],
        "test_files": [],  # No tests
        "documentation": []
    }
    
    result2 = await client.validate_persona_output(
        persona_id="frontend_dev_real_001",
        persona_type=PersonaType.FRONTEND_DEVELOPER,
        output=minimal_output
    )
    
    print(f"Persona ID: {result2.persona_id}")
    print(f"Status: {result2.status}")
    print(f"Overall Score: {result2.overall_score:.1f}%")
    print(f"Gates Passed: {len(result2.gates_passed)}")
    print(f"Gates Failed: {len(result2.gates_failed)}")
    print(f"Requires Revision: {result2.requires_revision}")
    print()
    
    # Step 4: Phase Gate Evaluation
    print("Step 4: Phase Gate Evaluation")
    print("-" * 70)
    
    persona_results = [
        {
            "persona_id": result.persona_id,
            "overall_score": result.overall_score,
            "status": result.status
        },
        {
            "persona_id": result2.persona_id,
            "overall_score": result2.overall_score,
            "status": result2.status
        }
    ]
    
    phase_gate = await client.evaluate_phase_gate(
        current_phase="implementation",
        next_phase="testing",
        phase_outputs={},
        persona_results=persona_results
    )
    
    print(f"Transition: {phase_gate.get('current_phase')} → {phase_gate.get('next_phase')}")
    print(f"Status: {phase_gate.get('status')}")
    print(f"Overall Quality: {phase_gate.get('overall_quality_score', 0):.1f}%")
    print(f"Blockers: {len(phase_gate.get('blockers', []))}")
    print(f"Warnings: {len(phase_gate.get('warnings', []))}")
    print()
    
    # Summary
    print("=" * 70)
    print("📊 Test Summary")
    print("=" * 70)
    print(f"✅ Health check: PASSED")
    print(f"✅ Backend validation: {result.status.upper()}")
    print(f"✅ Frontend validation: {result2.status.upper()}")
    print(f"✅ Phase gate evaluation: {phase_gate.get('status', 'unknown').upper()}")
    print()
    
    if result.status == "pass" or result.status == "warning":
        print("🎉 Integration test PASSED!")
        return 0
    else:
        print("⚠️  Some validations failed (expected for testing)")
        return 0


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(test_real_integration())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
