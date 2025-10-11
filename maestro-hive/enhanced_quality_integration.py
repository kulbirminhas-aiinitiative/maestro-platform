#!/usr/bin/env python3.11
"""
Enhanced Quality Fabric Integration
Real-time validation with feedback loops during SDLC execution

This module provides:
1. Real-time artifact validation as they're created
2. Quality Fabric API integration with graceful fallback
3. Feedback loops for immediate rework
4. Validation caching for phase gates
5. Comprehensive artifact scanning

Usage:
    orchestrator = EnhancedQualityOrchestrator()
    
    # Validate during execution
    result = await orchestrator.validate_during_execution(
        persona_id="backend_dev_001",
        persona_type="backend_developer",
        output_dir=Path("project/output"),
        iteration=1
    )
    
    # Evaluate phase transition
    can_proceed = await orchestrator.evaluate_phase_transition(
        current_phase="implementation",
        next_phase="testing",
        persona_results=[...]
    )
"""

from quality_fabric_client import QualityFabricClient, PersonaType
from typing import Dict, Any, List, Optional
from pathlib import Path
from datetime import datetime
import asyncio
import logging
import json

logger = logging.getLogger(__name__)


class EnhancedQualityOrchestrator:
    """
    Orchestrates real-time quality validation during SDLC execution
    """
    
    def __init__(
        self,
        quality_fabric_url: str = "http://localhost:8001",
        enable_real_time: bool = True,
        cache_results: bool = True
    ):
        """
        Initialize quality orchestrator
        
        Args:
            quality_fabric_url: Quality Fabric service URL
            enable_real_time: Enable real-time validation
            cache_results: Cache validation results for phase gates
        """
        self.client = QualityFabricClient(quality_fabric_url)
        self.enable_real_time = enable_real_time
        self.cache_results = cache_results
        self.validation_cache = {}
        self.artifact_timestamps = {}
        
    async def validate_during_execution(
        self,
        persona_id: str,
        persona_type: str,
        output_dir: Path,
        iteration: int,
        phase: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Validate persona output in real-time as artifacts are created
        
        Args:
            persona_id: Unique persona identifier
            persona_type: Type of persona (e.g., 'backend_developer')
            output_dir: Directory containing persona outputs
            iteration: Current iteration number
            phase: Optional SDLC phase
            
        Returns:
            Validation result with status, score, and recommendations
        """
        logger.info(f"🔍 Validating {persona_id} output in {output_dir}")
        
        # Scan for artifacts
        artifacts = self._scan_artifacts(output_dir, persona_id)
        
        logger.info(f"   Found {len(artifacts['code_files'])} code files")
        logger.info(f"   Found {len(artifacts['test_files'])} test files")
        logger.info(f"   Found {len(artifacts['documentation'])} docs")
        
        # Call Quality Fabric API
        try:
            result = await self.client.validate_persona_output(
                persona_id=persona_id,
                persona_type=PersonaType(persona_type),
                output=artifacts
            )
            
            # Cache result for phase gate
            if self.cache_results:
                self.validation_cache[persona_id] = {
                    "iteration": iteration,
                    "phase": phase,
                    "result": result,
                    "timestamp": datetime.now(),
                    "artifacts": artifacts
                }
            
            # Log results
            logger.info(f"   ✅ Validation complete: {result.status}")
            logger.info(f"   📊 Score: {result.overall_score:.1%}")
            
            if result.gates_failed:
                logger.warning(f"   ⚠️  Failed gates: {', '.join(result.gates_failed)}")
            
            if result.recommendations:
                logger.info("   💡 Recommendations:")
                for rec in result.recommendations[:3]:  # Top 3
                    logger.info(f"      • {rec}")
            
            # Return structured result
            return {
                "status": result.status,
                "score": result.overall_score,
                "gates_passed": result.gates_passed,
                "gates_failed": result.gates_failed,
                "recommendations": result.recommendations,
                "requires_rework": result.requires_revision,
                "quality_metrics": {
                    "code_coverage": len(artifacts['test_files']) / max(len(artifacts['code_files']), 1) * 100,
                    "file_counts": {
                        "code": len(artifacts['code_files']),
                        "tests": len(artifacts['test_files']),
                        "docs": len(artifacts['documentation'])
                    }
                }
            }
            
        except Exception as e:
            logger.error(f"❌ Validation failed: {e}")
            return {
                "status": "error",
                "score": 0.0,
                "gates_passed": [],
                "gates_failed": ["validation_error"],
                "recommendations": ["Fix validation errors"],
                "requires_rework": True,
                "error": str(e)
            }
    
    async def evaluate_phase_transition(
        self,
        current_phase: str,
        next_phase: str,
        persona_results: List[Dict[str, Any]],
        phase_outputs: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Use Quality Fabric to evaluate phase gate
        
        Args:
            current_phase: Current SDLC phase
            next_phase: Target SDLC phase
            persona_results: List of persona validation results
            phase_outputs: Optional aggregated phase outputs
            
        Returns:
            Phase gate evaluation result
        """
        logger.info(f"🚪 Evaluating phase gate: {current_phase} → {next_phase}")
        
        try:
            result = await self.client.evaluate_phase_gate(
                current_phase=current_phase,
                next_phase=next_phase,
                phase_outputs=phase_outputs or {},
                persona_results=persona_results
            )
            
            # Log results
            status = result["status"]
            score = result["overall_quality_score"]
            
            if status == "pass":
                logger.info(f"   ✅ Phase gate PASSED ({score:.1%})")
            elif status == "warning":
                logger.warning(f"   ⚠️  Phase gate WARNING ({score:.1%})")
            else:
                logger.error(f"   ❌ Phase gate FAILED ({score:.1%})")
            
            if result["blockers"]:
                logger.error("   🚫 Blockers:")
                for blocker in result["blockers"]:
                    logger.error(f"      • {blocker}")
            
            if result["warnings"]:
                logger.warning("   ⚠️  Warnings:")
                for warning in result["warnings"]:
                    logger.warning(f"      • {warning}")
            
            return {
                "can_proceed": status in ["pass", "warning"],
                "status": status,
                "quality_score": score,
                "gates_passed": result["gates_passed"],
                "gates_failed": result["gates_failed"],
                "blockers": result["blockers"],
                "warnings": result["warnings"],
                "recommendations": result["recommendations"],
                "bypass_available": result["bypass_available"],
                "human_approval_required": result.get("human_approval_required", False)
            }
            
        except Exception as e:
            logger.error(f"❌ Phase gate evaluation failed: {e}")
            return {
                "can_proceed": False,
                "status": "error",
                "quality_score": 0.0,
                "gates_passed": [],
                "gates_failed": ["evaluation_error"],
                "blockers": [f"Phase gate evaluation failed: {str(e)}"],
                "warnings": [],
                "recommendations": ["Fix evaluation errors"],
                "bypass_available": False,
                "human_approval_required": True,
                "error": str(e)
            }
    
    def _scan_artifacts(
        self, 
        output_dir: Path, 
        persona_id: str
    ) -> Dict[str, Any]:
        """
        Scan directory for persona artifacts
        
        Args:
            output_dir: Directory to scan
            persona_id: Persona identifier (for filtering)
            
        Returns:
            Dictionary of categorized artifacts
        """
        artifacts = {
            "code_files": [],
            "test_files": [],
            "documentation": [],
            "config_files": [],
            "metadata": {
                "persona_id": persona_id,
                "scan_time": datetime.now().isoformat(),
                "output_dir": str(output_dir)
            }
        }
        
        if not output_dir.exists():
            logger.warning(f"⚠️  Output directory does not exist: {output_dir}")
            return artifacts
        
        # Define file patterns
        code_extensions = {".py", ".js", ".ts", ".jsx", ".tsx", ".java", ".go", ".rs", ".cpp", ".c", ".h"}
        test_patterns = {"test_", "_test", ".test.", ".spec.", "test/", "tests/", "__tests__/"}
        doc_extensions = {".md", ".rst", ".txt", ".adoc"}
        config_files = {
            "package.json", "requirements.txt", "Dockerfile", 
            "docker-compose.yml", "pyproject.toml", "setup.py",
            "tsconfig.json", "jest.config.js", "pytest.ini"
        }
        
        # Scan all files
        for file_path in output_dir.rglob("*"):
            if not file_path.is_file():
                continue
            
            # Skip hidden files and common excludes
            if any(part.startswith('.') for part in file_path.parts):
                continue
            
            if any(x in file_path.parts for x in ['node_modules', '__pycache__', '.git', 'venv', '.venv']):
                continue
            
            relative_path = file_path.relative_to(output_dir)
            file_ext = file_path.suffix.lower()
            file_name = file_path.name.lower()
            path_str = str(relative_path).lower()
            
            # Categorize file
            file_info = {
                "name": file_path.name,
                "path": str(relative_path),
                "size": file_path.stat().st_size,
                "modified": file_path.stat().st_mtime
            }
            
            # Check if it's a test file
            is_test = any(pattern in path_str for pattern in test_patterns)
            
            if is_test:
                artifacts["test_files"].append(file_info)
            elif file_ext in code_extensions:
                artifacts["code_files"].append(file_info)
            elif file_ext in doc_extensions:
                artifacts["documentation"].append(file_info)
            elif file_name in config_files:
                artifacts["config_files"].append(file_info)
        
        return artifacts
    
    def get_cached_validation(self, persona_id: str) -> Optional[Dict[str, Any]]:
        """
        Get cached validation result for persona
        
        Args:
            persona_id: Persona identifier
            
        Returns:
            Cached validation result or None
        """
        return self.validation_cache.get(persona_id)
    
    def clear_cache(self):
        """Clear validation cache"""
        self.validation_cache.clear()
        self.artifact_timestamps.clear()
        logger.info("🗑️  Validation cache cleared")
    
    async def batch_validate_personas(
        self,
        personas: List[Dict[str, str]],
        output_dir: Path,
        iteration: int,
        phase: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Validate multiple personas in parallel
        
        Args:
            personas: List of persona configs with id and type
            output_dir: Base output directory
            iteration: Current iteration
            phase: Optional SDLC phase
            
        Returns:
            List of validation results
        """
        tasks = []
        for persona in personas:
            task = self.validate_during_execution(
                persona_id=persona['id'],
                persona_type=persona['type'],
                output_dir=output_dir / persona['id'],
                iteration=iteration,
                phase=phase
            )
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Handle exceptions
        processed_results = []
        for idx, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"❌ Validation failed for {personas[idx]['id']}: {result}")
                processed_results.append({
                    "status": "error",
                    "score": 0.0,
                    "error": str(result)
                })
            else:
                processed_results.append(result)
        
        return processed_results


# Convenience functions

async def validate_persona_output(
    persona_id: str,
    persona_type: str,
    output_dir: Path,
    quality_fabric_url: str = "http://localhost:8001"
) -> Dict[str, Any]:
    """
    Convenience function to validate persona output
    
    Args:
        persona_id: Persona identifier
        persona_type: Type of persona
        output_dir: Output directory to scan
        quality_fabric_url: Quality Fabric service URL
        
    Returns:
        Validation result
    """
    orchestrator = EnhancedQualityOrchestrator(quality_fabric_url)
    return await orchestrator.validate_during_execution(
        persona_id=persona_id,
        persona_type=persona_type,
        output_dir=output_dir,
        iteration=1
    )


async def evaluate_phase_gate(
    current_phase: str,
    next_phase: str,
    persona_results: List[Dict[str, Any]],
    quality_fabric_url: str = "http://localhost:8001"
) -> Dict[str, Any]:
    """
    Convenience function to evaluate phase gate
    
    Args:
        current_phase: Current phase
        next_phase: Target phase
        persona_results: Persona validation results
        quality_fabric_url: Quality Fabric service URL
        
    Returns:
        Phase gate evaluation
    """
    orchestrator = EnhancedQualityOrchestrator(quality_fabric_url)
    return await orchestrator.evaluate_phase_transition(
        current_phase=current_phase,
        next_phase=next_phase,
        persona_results=persona_results
    )


# Test function

async def test_enhanced_quality():
    """Test enhanced quality orchestrator"""
    print("🧪 Testing Enhanced Quality Orchestrator\n")
    
    orchestrator = EnhancedQualityOrchestrator()
    
    # Test 1: Scan artifacts
    print("1️⃣ Testing artifact scanning...")
    test_dir = Path(__file__).parent / "test_output"
    test_dir.mkdir(exist_ok=True)
    
    # Create some test files
    (test_dir / "main.py").write_text("# Main code")
    (test_dir / "test_main.py").write_text("# Test code")
    (test_dir / "README.md").write_text("# Documentation")
    
    result = await orchestrator.validate_during_execution(
        persona_id="test_persona",
        persona_type="backend_developer",
        output_dir=test_dir,
        iteration=1
    )
    
    print(f"   Status: {result['status']}")
    print(f"   Score: {result['score']:.1%}")
    print(f"   Artifacts: {result['quality_metrics']['file_counts']}")
    print()
    
    # Test 2: Phase gate evaluation
    print("2️⃣ Testing phase gate evaluation...")
    gate_result = await orchestrator.evaluate_phase_transition(
        current_phase="implementation",
        next_phase="testing",
        persona_results=[result]
    )
    
    print(f"   Can proceed: {gate_result['can_proceed']}")
    print(f"   Status: {gate_result['status']}")
    print(f"   Quality: {gate_result['quality_score']:.1%}")
    print()
    
    # Cleanup
    import shutil
    shutil.rmtree(test_dir, ignore_errors=True)
    
    print("✅ Enhanced Quality Orchestrator Test Complete!")


if __name__ == "__main__":
    import asyncio
    asyncio.run(test_enhanced_quality())
