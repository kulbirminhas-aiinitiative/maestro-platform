#!/usr/bin/env python3.11
"""
Quality Fabric Client
Simple client for SDLC integration with Quality Fabric
"""

import httpx
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict
from enum import Enum
import json


class PersonaType(str, Enum):
    """SDLC Persona types"""
    SYSTEM_ARCHITECT = "system_architect"
    BACKEND_DEVELOPER = "backend_developer"
    FRONTEND_DEVELOPER = "frontend_developer"
    DATABASE_ENGINEER = "database_engineer"
    DEVOPS_ENGINEER = "devops_engineer"
    QA_ENGINEER = "qa_engineer"
    SECURITY_ENGINEER = "security_engineer"
    TECHNICAL_WRITER = "technical_writer"
    PROJECT_MANAGER = "project_manager"
    PRODUCT_MANAGER = "product_manager"
    UX_DESIGNER = "ux_designer"


@dataclass
class PersonaValidationResult:
    """Result of persona output validation"""
    persona_id: str
    persona_type: str
    status: str  # "pass", "fail", "warning"
    overall_score: float
    gates_passed: List[str]
    gates_failed: List[str]
    quality_metrics: Dict[str, Any]
    recommendations: List[str]
    requires_revision: bool


class QualityFabricClient:
    """
    Client for integrating SDLC Team with Quality Fabric
    """
    
    def __init__(
        self,
        quality_fabric_url: str = "http://localhost:8000",
        timeout: float = 60.0
    ):
        self.base_url = quality_fabric_url.rstrip('/')
        self.timeout = timeout
        
    async def health_check(self) -> Dict[str, Any]:
        """Check if Quality Fabric is healthy"""
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"{self.base_url}/health",
                    timeout=5.0
                )
                return response.json()
            except Exception as e:
                return {"status": "error", "error": str(e)}
    
    async def validate_persona_output(
        self,
        persona_id: str,
        persona_type: PersonaType,
        output: Dict[str, Any],
        custom_gates: Optional[Dict[str, Any]] = None
    ) -> PersonaValidationResult:
        """
        Validate persona output against quality gates
        
        Args:
            persona_id: Unique persona identifier
            persona_type: Type of persona
            output: Persona output artifacts
            custom_gates: Optional custom quality gates
        
        Returns:
            Validation result
        """
        # Try to use real API first, fallback to mock if unavailable
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                # Prepare request payload
                payload = {
                    "persona_id": persona_id,
                    "persona_type": persona_type.value,
                    "artifacts": {
                        "code_files": output.get("code_files", []),
                        "test_files": output.get("test_files", []),
                        "documentation": output.get("documentation", []),
                        "config_files": output.get("config_files", []),
                        "metadata": output.get("metadata", {})
                    },
                    "custom_gates": custom_gates,
                    "project_context": output.get("project_context", {})
                }
                
                # Call Quality Fabric API
                response = await client.post(
                    f"{self.base_url}/api/v1/sdlc/validate-persona",
                    json=payload,
                    timeout=self.timeout
                )
                
                if response.status_code == 200:
                    data = response.json()
                    return PersonaValidationResult(
                        persona_id=data["persona_id"],
                        persona_type=data["persona_type"],
                        status=data["status"],
                        overall_score=data["overall_score"],
                        gates_passed=data["gates_passed"],
                        gates_failed=data["gates_failed"],
                        quality_metrics=data["quality_metrics"],
                        recommendations=data["recommendations"],
                        requires_revision=data["requires_revision"]
                    )
                else:
                    # Fallback to mock if API returns error
                    print(f"⚠️  API returned {response.status_code}, using mock validation")
                    return self._mock_validate(persona_id, persona_type, output)
        
        except Exception as e:
            # Fallback to mock if API is unavailable
            print(f"⚠️  API unavailable ({str(e)}), using mock validation")
            return self._mock_validate(persona_id, persona_type, output)
    
    def _mock_validate(
        self,
        persona_id: str,
        persona_type: PersonaType,
        output: Dict[str, Any]
    ) -> PersonaValidationResult:
        """Mock validation for testing without Quality Fabric"""
        gates_passed = []
        gates_failed = []
        recommendations = []
        quality_metrics = {}
        
        # Extract artifacts
        code_files = output.get("code_files", [])
        test_files = output.get("test_files", [])
        documentation = output.get("documentation", [])
        
        # Mock validation logic based on persona type
        if persona_type in [PersonaType.BACKEND_DEVELOPER, PersonaType.FRONTEND_DEVELOPER]:
            # Check if code files exist
            if len(code_files) > 0:
                gates_passed.append("code_files_present")
                quality_metrics["code_files_count"] = len(code_files)
            else:
                gates_failed.append("code_files_missing")
                recommendations.append("Generate code files for implementation")
            
            # Check if test files exist
            if len(test_files) > 0:
                gates_passed.append("test_files_present")
                quality_metrics["test_files_count"] = len(test_files)
            else:
                gates_failed.append("test_files_missing")
                recommendations.append("Add test coverage for code")
            
            # Mock coverage score
            coverage = (len(test_files) / max(len(code_files), 1)) * 100
            quality_metrics["estimated_coverage"] = min(coverage, 100.0)
            
            if coverage >= 70:
                gates_passed.append("coverage_acceptable")
            else:
                gates_failed.append("coverage_low")
                recommendations.append(f"Increase test coverage (current: {coverage:.0f}%)")
        
        elif persona_type == PersonaType.QA_ENGINEER:
            # QA persona needs comprehensive test suite
            if len(test_files) > 5:
                gates_passed.append("comprehensive_tests")
            else:
                gates_failed.append("insufficient_tests")
                recommendations.append("Add more test cases for comprehensive coverage")
        
        elif persona_type == PersonaType.SECURITY_ENGINEER:
            # Security persona needs security documentation
            if len(documentation) > 0:
                gates_passed.append("security_documentation")
            else:
                gates_failed.append("missing_security_docs")
                recommendations.append("Document security considerations")
        
        # Calculate overall score
        total_gates = len(gates_passed) + len(gates_failed)
        overall_score = len(gates_passed) / total_gates if total_gates > 0 else 0.5
        
        # Determine status
        if len(gates_failed) == 0:
            status = "pass"
        elif overall_score >= 0.7:
            status = "warning"
        else:
            status = "fail"
        
        return PersonaValidationResult(
            persona_id=persona_id,
            persona_type=persona_type.value,
            status=status,
            overall_score=overall_score,
            gates_passed=gates_passed,
            gates_failed=gates_failed,
            quality_metrics=quality_metrics,
            recommendations=recommendations,
            requires_revision=(status == "fail")
        )
    
    async def evaluate_phase_gate(
        self,
        current_phase: str,
        next_phase: str,
        phase_outputs: Dict[str, Any],
        persona_results: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Evaluate phase gate for transition
        
        Args:
            current_phase: Current SDLC phase
            next_phase: Target SDLC phase
            phase_outputs: Aggregated phase outputs
            persona_results: List of persona validation results
        
        Returns:
            Phase gate evaluation result
        """
        # Try to use real API first, fallback to mock if unavailable
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                payload = {
                    "current_phase": current_phase,
                    "next_phase": next_phase,
                    "phase_outputs": phase_outputs,
                    "persona_results": persona_results
                }
                
                response = await client.post(
                    f"{self.base_url}/api/v1/sdlc/evaluate-phase-gate",
                    json=payload,
                    timeout=self.timeout
                )
                
                if response.status_code == 200:
                    return response.json()
                else:
                    print(f"⚠️  Phase gate API returned {response.status_code}, using mock")
                    return self._mock_evaluate_phase_gate(persona_results)
        
        except Exception as e:
            print(f"⚠️  Phase gate API unavailable ({str(e)}), using mock")
            return self._mock_evaluate_phase_gate(persona_results)
    
    def _mock_evaluate_phase_gate(
        self, 
        persona_results: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Mock phase gate evaluation"""
        persona_scores = [r.get("overall_score", 0.0) for r in persona_results]
        avg_score = sum(persona_scores) / len(persona_scores) if persona_scores else 0.0
        
        # Determine phase from persona results
        current_phase = "development"  # Default
        next_phase = "testing"  # Default
        
        # Simple gate logic
        gates_passed = []
        gates_failed = []
        
        if avg_score >= 0.8:
            gates_passed.append("overall_quality")
            status = "pass"
        elif avg_score >= 0.6:
            gates_passed.append("overall_quality_acceptable")
            status = "warning"
        else:
            gates_failed.append("overall_quality")
            status = "fail"
        
        return {
            "phase": current_phase,
            "next_phase": next_phase,
            "status": status,
            "overall_quality_score": avg_score,
            "overall_score": avg_score,  # Alias for convenience
            "gates_passed": gates_passed,
            "gates_failed": gates_failed,
            "blockers": [] if status != "fail" else ["Quality score below threshold"],
            "warnings": [] if status == "pass" else ["Quality score below optimal"],
            "recommendations": [] if status == "pass" else ["Improve persona output quality"],
            "bypass_available": status != "fail",
            "human_approval_required": next_phase == "deployment"
        }
    
    def validate_persona_output_sync(
        self,
        persona_id: str,
        persona_type: PersonaType,
        output: Dict[str, Any]
    ) -> PersonaValidationResult:
        """Synchronous version of validate_persona_output"""
        import asyncio
        
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        return loop.run_until_complete(
            self.validate_persona_output(persona_id, persona_type, output)
        )


# Quick test function
async def test_quality_fabric_client():
    """Test the Quality Fabric client"""
    print("🧪 Testing Quality Fabric Client\n")
    
    client = QualityFabricClient()
    
    # Test 1: Health check
    print("1️⃣ Health Check...")
    health = await client.health_check()
    print(f"   Status: {health.get('status')}")
    print()
    
    # Test 2: Validate backend developer output
    print("2️⃣ Validate Backend Developer Output...")
    backend_output = {
        "code_files": [
            {"name": "api.py", "content": "# API code"},
            {"name": "models.py", "content": "# Models"}
        ],
        "test_files": [
            {"name": "test_api.py", "content": "# Tests"}
        ],
        "documentation": [
            {"name": "README.md", "content": "# API Documentation"}
        ]
    }
    
    result = await client.validate_persona_output(
        persona_id="backend_dev_001",
        persona_type=PersonaType.BACKEND_DEVELOPER,
        output=backend_output
    )
    
    print(f"   Status: {result.status}")
    print(f"   Score: {result.overall_score:.1%}")
    print(f"   Gates Passed: {', '.join(result.gates_passed)}")
    if result.gates_failed:
        print(f"   Gates Failed: {', '.join(result.gates_failed)}")
    if result.recommendations:
        print(f"   Recommendations:")
        for rec in result.recommendations:
            print(f"     • {rec}")
    print()
    
    # Test 3: Validate QA engineer output
    print("3️⃣ Validate QA Engineer Output...")
    qa_output = {
        "test_files": [
            {"name": f"test_{i}.py", "content": "# Test"} for i in range(8)
        ]
    }
    
    qa_result = await client.validate_persona_output(
        persona_id="qa_eng_001",
        persona_type=PersonaType.QA_ENGINEER,
        output=qa_output
    )
    
    print(f"   Status: {qa_result.status}")
    print(f"   Score: {qa_result.overall_score:.1%}")
    print(f"   Gates Passed: {', '.join(qa_result.gates_passed)}")
    print()
    
    # Test 4: Phase gate evaluation
    print("4️⃣ Evaluate Phase Gate...")
    phase_result = await client.evaluate_phase_gate(
        current_phase="implementation",
        next_phase="testing",
        phase_outputs={},
        persona_results=[asdict(result), asdict(qa_result)]
    )
    
    print(f"   Transition: {phase_result['phase']} → {phase_result['next_phase']}")
    print(f"   Status: {phase_result['status']}")
    print(f"   Quality Score: {phase_result['overall_quality_score']:.1%}")
    print()
    
    print("✅ Quality Fabric Client Test Complete!")


if __name__ == "__main__":
    import asyncio
    asyncio.run(test_quality_fabric_client())
