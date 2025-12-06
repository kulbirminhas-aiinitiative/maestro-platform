#!/usr/bin/env python3.11
"""
Reflection Loop with Real Quality Analysis
Demonstrates automatic quality improvement through iterative refinement
"""

import asyncio
import sys
from typing import Dict, Any
from quality_fabric_client import QualityFabricClient, PersonaType


class QualityReflectionLoop:
    """
    Implements reflection loop for quality improvement
    """
    
    def __init__(self, client: QualityFabricClient, max_iterations: int = 3):
        self.client = client
        self.max_iterations = max_iterations
    
    async def execute_with_reflection(
        self,
        persona_id: str,
        persona_type: PersonaType,
        initial_output: Dict[str, Any],
        quality_threshold: float = 80.0
    ) -> Dict[str, Any]:
        """
        Execute persona with automatic quality improvement
        
        Args:
            persona_id: Persona identifier
            persona_type: Type of persona
            initial_output: Initial persona output
            quality_threshold: Minimum quality score to accept
        
        Returns:
            Final output with quality validation
        """
        print(f"🔄 Starting Reflection Loop for {persona_type.value}")
        print(f"   Threshold: {quality_threshold}%")
        print(f"   Max Iterations: {self.max_iterations}")
        print()
        
        current_output = initial_output.copy()
        iteration_history = []
        
        for iteration in range(1, self.max_iterations + 1):
            print(f"Iteration {iteration}/{self.max_iterations}")
            print("-" * 50)
            
            # Validate current output
            validation = await self.client.validate_persona_output(
                persona_id=f"{persona_id}_iter_{iteration}",
                persona_type=persona_type,
                output=current_output
            )
            
            # Record history
            iteration_history.append({
                "iteration": iteration,
                "score": validation.overall_score,
                "status": validation.status,
                "gates_passed": len(validation.gates_passed),
                "gates_failed": len(validation.gates_failed)
            })
            
            # Display results
            print(f"Status: {validation.status.upper()}")
            print(f"Score: {validation.overall_score:.1f}%")
            print(f"Gates: {len(validation.gates_passed)} passed, {len(validation.gates_failed)} failed")
            
            if validation.quality_metrics:
                print("Metrics:")
                for key, value in validation.quality_metrics.items():
                    if value is not None and key in ['pylint_score', 'test_coverage', 'security_issues']:
                        print(f"  • {key}: {value}")
            
            # Check if quality threshold is met
            if validation.overall_score >= quality_threshold:
                print(f"\n✅ Quality threshold met ({validation.overall_score:.1f}% >= {quality_threshold}%)")
                print(f"🎉 Converged in {iteration} iteration(s)")
                return {
                    "output": current_output,
                    "validation": validation,
                    "iterations": iteration,
                    "history": iteration_history,
                    "converged": True
                }
            
            # If not last iteration, apply improvements
            if iteration < self.max_iterations:
                print(f"\n⚠️  Quality below threshold ({validation.overall_score:.1f}% < {quality_threshold}%)")
                print("📝 Recommendations:")
                for rec in validation.recommendations[:3]:  # Show top 3
                    print(f"  • {rec}")
                
                # Simulate improvement (in real scenario, would regenerate with feedback)
                current_output = self._apply_improvements(
                    current_output, 
                    validation
                )
                print(f"\n🔧 Applied improvements, retrying...\n")
            else:
                print(f"\n⚠️  Max iterations reached without convergence")
        
        # Max iterations reached without convergence
        return {
            "output": current_output,
            "validation": validation,
            "iterations": self.max_iterations,
            "history": iteration_history,
            "converged": False
        }
    
    def _apply_improvements(
        self, 
        output: Dict[str, Any], 
        validation
    ) -> Dict[str, Any]:
        """
        Apply improvements based on validation feedback
        In real implementation, would use LLM to regenerate with feedback
        """
        improved = output.copy()
        
        # Simulate improvements
        # In reality, this would call the persona again with feedback
        
        # Add more tests if coverage is low
        if validation.quality_metrics.get('test_coverage', 100) < 70:
            improved['test_files'] = improved.get('test_files', []) + [
                {
                    "name": f"test_additional_{len(improved.get('test_files', []))}.py",
                    "content": "def test_additional(): assert True",
                    "lines": 1
                }
            ]
        
        # Add documentation if missing
        if validation.quality_metrics.get('documentation_completeness', 100) < 60:
            improved['documentation'] = improved.get('documentation', []) + [
                {
                    "name": "README.md",
                    "content": "# Project Documentation\n\nDetailed documentation here."
                }
            ]
        
        # Improve code quality (simulate)
        if validation.quality_metrics.get('pylint_score', 10) < 7:
            # In reality, would regenerate code with better quality
            for code_file in improved.get('code_files', []):
                if 'content' in code_file:
                    # Add docstrings
                    content = code_file['content']
                    if '"""' not in content and "'''" not in content:
                        code_file['content'] = f'"""\nImproved module\n"""\n{content}'
        
        return improved


async def demo_reflection_loop():
    """Demonstrate reflection loop with real quality analysis"""
    print("=" * 70)
    print("🧪 Reflection Loop Demo - Real Quality Analysis")
    print("=" * 70)
    print()
    
    # Initialize
    client = QualityFabricClient("http://localhost:8001")
    reflection = QualityReflectionLoop(client, max_iterations=3)
    
    # Test Case 1: Low quality code that needs improvement
    print("Test Case 1: Low Quality Code (Should Improve Over Iterations)")
    print("=" * 70)
    print()
    
    low_quality_output = {
        "code_files": [
            {
                "name": "simple.py",
                "content": "def f(x,y): return x+y",  # Poor quality
                "lines": 1
            }
        ],
        "test_files": [],  # No tests
        "documentation": []  # No docs
    }
    
    result1 = await reflection.execute_with_reflection(
        persona_id="backend_low_quality",
        persona_type=PersonaType.BACKEND_DEVELOPER,
        initial_output=low_quality_output,
        quality_threshold=75.0
    )
    
    print("\n" + "=" * 70)
    print("📊 Reflection Loop Results")
    print("=" * 70)
    print(f"Converged: {result1['converged']}")
    print(f"Iterations: {result1['iterations']}")
    print(f"Final Score: {result1['validation'].overall_score:.1f}%")
    print()
    
    print("Iteration History:")
    for h in result1['history']:
        print(f"  {h['iteration']}: {h['score']:.1f}% ({h['status']}) - "
              f"{h['gates_passed']}/{h['gates_passed']+h['gates_failed']} gates")
    print()
    
    # Test Case 2: High quality code (should pass immediately)
    print("\n" + "=" * 70)
    print("Test Case 2: High Quality Code (Should Pass Immediately)")
    print("=" * 70)
    print()
    
    high_quality_output = {
        "code_files": [
            {
                "name": "calculator.py",
                "content": '''
"""
Calculator module for basic arithmetic operations
"""

def add(a: int, b: int) -> int:
    """Add two numbers together"""
    return a + b

def subtract(a: int, b: int) -> int:
    """Subtract b from a"""
    return a - b

def multiply(a: int, b: int) -> int:
    """Multiply two numbers"""
    return a * b

def divide(a: int, b: int) -> float:
    """Divide a by b"""
    if b == 0:
        raise ValueError("Cannot divide by zero")
    return a / b
''',
                "lines": 20
            }
        ],
        "test_files": [
            {
                "name": "test_calculator.py",
                "content": '''
"""Tests for calculator module"""
import pytest
from calculator import add, subtract, multiply, divide

def test_add():
    assert add(2, 3) == 5
    assert add(-1, 1) == 0

def test_subtract():
    assert subtract(5, 3) == 2
    assert subtract(0, 5) == -5

def test_multiply():
    assert multiply(3, 4) == 12
    assert multiply(-2, 3) == -6

def test_divide():
    assert divide(10, 2) == 5.0
    with pytest.raises(ValueError):
        divide(10, 0)
''',
                "lines": 20
            }
        ],
        "documentation": [
            {
                "name": "README.md",
                "content": "# Calculator\n\nA simple calculator with comprehensive tests."
            }
        ]
    }
    
    result2 = await reflection.execute_with_reflection(
        persona_id="backend_high_quality",
        persona_type=PersonaType.BACKEND_DEVELOPER,
        initial_output=high_quality_output,
        quality_threshold=85.0
    )
    
    print("\n" + "=" * 70)
    print("📊 Reflection Loop Results")
    print("=" * 70)
    print(f"Converged: {result2['converged']}")
    print(f"Iterations: {result2['iterations']}")
    print(f"Final Score: {result2['validation'].overall_score:.1f}%")
    print()
    
    # Summary
    print("\n" + "=" * 70)
    print("🎯 Summary")
    print("=" * 70)
    print(f"Test Case 1: {result1['iterations']} iterations, "
          f"{'✅ Converged' if result1['converged'] else '⚠️ Did not converge'}")
    print(f"Test Case 2: {result2['iterations']} iteration, "
          f"{'✅ Converged' if result2['converged'] else '⚠️ Did not converge'}")
    print()
    print("🎉 Reflection Loop Demo Complete!")
    

if __name__ == "__main__":
    try:
        asyncio.run(demo_reflection_loop())
        sys.exit(0)
    except KeyboardInterrupt:
        print("\n\n⚠️  Demo interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Demo failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
