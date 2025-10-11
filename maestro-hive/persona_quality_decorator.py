"""
Persona Quality Decorator
Wraps persona execution with automatic quality validation
"""

from functools import wraps
from typing import Any, Dict, Optional
import asyncio
import logging

from quality_fabric_client import QualityFabricClient, PersonaType

logger = logging.getLogger(__name__)


class PersonaQualityEnforcer:
    """Enforces quality gates on persona execution"""
    
    def __init__(self, quality_fabric_url: str = "http://localhost:8001"):
        self.client = QualityFabricClient(quality_fabric_url)
        self.enabled = True
        self.max_iterations = 3
    
    def with_quality_validation(self, persona_type: PersonaType, max_iterations: int = 3):
        """
        Decorator to add quality validation to persona execution.
        
        Usage:
            enforcer = PersonaQualityEnforcer()
            
            @enforcer.with_quality_validation(PersonaType.BACKEND_DEVELOPER)
            async def execute_backend_developer(persona_id: str, context: dict):
                # ... generate code ...
                return output
        """
        def decorator(func):
            @wraps(func)
            async def wrapper(persona_id: str, context: Dict[str, Any], *args, **kwargs):
                if not self.enabled:
                    # Quality checking disabled, just run
                    return await func(persona_id, context, *args, **kwargs)
                
                iteration = 0
                best_output = None
                best_score = 0.0
                
                while iteration < max_iterations:
                    logger.info(f"[{persona_id}] Quality iteration {iteration + 1}/{max_iterations}")
                    
                    # Execute persona
                    output = await func(persona_id, context, *args, **kwargs)
                    
                    # Validate output
                    validation = await self.client.validate_persona_output(
                        persona_id=persona_id,
                        persona_type=persona_type,
                        output=output
                    )
                    
                    logger.info(f"[{persona_id}] Quality: {validation.status} ({validation.overall_score:.1f}%)")
                    
                    # Track best output
                    if validation.overall_score > best_score:
                        best_output = output
                        best_score = validation.overall_score
                    
                    # If passed, return
                    if validation.status == "pass":
                        logger.info(f"[{persona_id}] ✅ Quality gate passed!")
                        return {
                            "output": output,
                            "validation": validation,
                            "iterations": iteration + 1
                        }
                    
                    # If needs revision, add feedback to context
                    if validation.requires_revision and iteration < max_iterations - 1:
                        logger.warning(f"[{persona_id}] 🔄 Refining based on quality feedback...")
                        context["quality_feedback"] = {
                            "recommendations": validation.recommendations,
                            "gates_failed": validation.gates_failed,
                            "iteration": iteration + 1
                        }
                        iteration += 1
                    else:
                        break
                
                # Max iterations reached or no revision needed
                logger.warning(f"[{persona_id}] ⚠️ Quality validation incomplete after {iteration + 1} iterations")
                return {
                    "output": best_output or output,
                    "validation": validation,
                    "iterations": iteration + 1,
                    "max_iterations_reached": True
                }
            
            return wrapper
        return decorator
    
    async def validate_phase_gate(
        self,
        current_phase: str,
        next_phase: str,
        persona_results: list
    ) -> Dict[str, Any]:
        """Validate phase gate transition"""
        
        if not self.enabled:
            return {
                "status": "pass",
                "message": "Quality checking disabled",
                "overall_score": 100.0,
                "blockers": [],
                "warnings": [],
                "recommendations": [],
                "bypass_available": True,
                "human_approval_required": False
            }
        
        result = await self.client.evaluate_phase_gate(
            current_phase=current_phase,
            next_phase=next_phase,
            phase_outputs={},
            persona_results=persona_results
        )
        
        # result is already a dict from the mock implementation
        logger.info(f"Phase gate {current_phase} → {next_phase}: {result['status']}")
        
        return result


# Global enforcer instance
quality_enforcer = PersonaQualityEnforcer()


# Convenience decorators for each persona type
def backend_developer_quality(func):
    """Quality validation for backend developer persona"""
    return quality_enforcer.with_quality_validation(PersonaType.BACKEND_DEVELOPER)(func)


def frontend_developer_quality(func):
    """Quality validation for frontend developer persona"""
    return quality_enforcer.with_quality_validation(PersonaType.FRONTEND_DEVELOPER)(func)


def qa_engineer_quality(func):
    """Quality validation for QA engineer persona"""
    return quality_enforcer.with_quality_validation(PersonaType.QA_ENGINEER)(func)


def devops_engineer_quality(func):
    """Quality validation for DevOps engineer persona"""
    return quality_enforcer.with_quality_validation(PersonaType.DEVOPS_ENGINEER)(func)


def security_engineer_quality(func):
    """Quality validation for security engineer persona"""
    return quality_enforcer.with_quality_validation(PersonaType.SECURITY_ENGINEER)(func)


# Example usage
if __name__ == "__main__":
    async def example():
        """Example of using the quality decorator"""
        
        @backend_developer_quality
        async def execute_backend_dev(persona_id: str, context: dict):
            """Mock backend developer execution"""
            print(f"[{persona_id}] Generating backend code...")
            
            # Simulate code generation
            await asyncio.sleep(0.1)
            
            # Check if we have feedback
            feedback = context.get("quality_feedback", {})
            iteration = feedback.get("iteration", 0)
            
            # Simulate improvement based on feedback
            code_quality = 60 + (iteration * 15)  # Improves each iteration
            
            return {
                "code_files": [
                    {"name": "main.py", "lines": 100},
                    {"name": "models.py", "lines": 50}
                ],
                "test_files": [
                    {"name": "test_main.py", "lines": 80}
                ] if code_quality >= 70 else [],
                "documentation": [
                    {"name": "README.md", "lines": 20}
                ],
                "metadata": {
                    "quality_target": code_quality
                }
            }
        
        # Execute with quality validation
        result = await execute_backend_dev(
            persona_id="backend_001",
            context={"project_name": "test_project"}
        )
        
        print(f"\n✅ Execution complete!")
        print(f"   Iterations: {result['iterations']}")
        print(f"   Status: {result['validation'].status}")
        print(f"   Score: {result['validation'].overall_score:.1f}%")
        print(f"   Gates passed: {len(result['validation'].gates_passed)}")
    
    # Run example
    asyncio.run(example())
