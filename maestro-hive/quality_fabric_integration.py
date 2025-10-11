"""
Quality Fabric Integration for SDLC Workflow
Provides enterprise-grade validation via microservices API
"""
import aiohttp
import asyncio
from typing import Dict, Any, List, Optional
from pathlib import Path
import logging
import json

logger = logging.getLogger(__name__)

class QualityFabricClient:
    """Client for Quality Fabric microservices API"""
    
    def __init__(
        self,
        base_url: str = "http://localhost:9800",
        api_key: Optional[str] = None,
        timeout: int = 30
    ):
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key or "default-dev-key"
        self.timeout = aiohttp.ClientTimeout(total=timeout)
        self.session = None
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession(
            headers={
                "X-API-Key": self.api_key,
                "Content-Type": "application/json"
            },
            timeout=self.timeout
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def health_check(self) -> bool:
        """Check if Quality Fabric API is available"""
        try:
            async with self.session.get(f"{self.base_url}/health") as resp:
                return resp.status == 200
        except Exception as e:
            logger.debug(f"Quality Fabric health check failed: {e}")
            return False
    
    async def validate_project(
        self,
        project_dir: Path,
        phase: str,
        validation_type: str = "comprehensive"
    ) -> Dict[str, Any]:
        """
        Validate project artifacts using Quality Fabric
        
        Args:
            project_dir: Path to project directory
            phase: SDLC phase (requirements, design, development, etc.)
            validation_type: Type of validation (quick, standard, comprehensive)
        
        Returns:
            {
                "overall_score": 0.85,
                "phase_scores": {...},
                "issues_found": [...],
                "recommendations": [...],
                "ai_insights": {...}
            }
        """
        try:
            # Check if API is available
            if not await self.health_check():
                logger.warning("Quality Fabric API unavailable, using fallback")
                return self._fallback_validation(project_dir, phase)
            
            # Prepare validation request
            validation_request = {
                "project_path": str(project_dir),
                "phase": phase,
                "validation_type": validation_type,
                "include_ai_insights": True,
                "scan_depth": "comprehensive"
            }
            
            # Call automation service for validation
            async with self.session.post(
                f"{self.base_url}/api/v1/automation/validate",
                json=validation_request
            ) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    logger.info(f"✅ Quality Fabric validation: {result.get('overall_score', 0):.2%}")
                    return result
                else:
                    error_text = await resp.text()
                    logger.error(f"❌ Quality Fabric validation failed: {error_text}")
                    return self._fallback_validation(project_dir, phase)
        
        except asyncio.TimeoutError:
            logger.warning("⚠️  Quality Fabric request timeout, using fallback")
            return self._fallback_validation(project_dir, phase)
        except Exception as e:
            logger.warning(f"⚠️  Quality Fabric error: {e}, using fallback")
            return self._fallback_validation(project_dir, phase)
    
    async def get_remediation_recommendations(
        self,
        validation_results: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Get AI-powered remediation recommendations
        
        Returns:
            [
                {
                    "issue": "Missing API documentation",
                    "severity": "high",
                    "persona": "tech_writer",
                    "recommended_action": "Generate OpenAPI spec",
                    "confidence": 0.92
                }
            ]
        """
        try:
            if not await self.health_check():
                return self._generate_fallback_recommendations(validation_results)
            
            async with self.session.post(
                f"{self.base_url}/api/v1/ai/remediation-recommendations",
                json={"validation_results": validation_results}
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    recommendations = data.get("recommendations", [])
                    logger.info(f"🤖 Received {len(recommendations)} AI recommendations")
                    return recommendations
                return self._generate_fallback_recommendations(validation_results)
        except Exception as e:
            logger.warning(f"⚠️  AI recommendations unavailable: {e}")
            return self._generate_fallback_recommendations(validation_results)
    
    async def track_quality_metrics(
        self,
        project_id: str,
        metrics: Dict[str, float]
    ) -> bool:
        """Track quality metrics over time"""
        try:
            if not await self.health_check():
                return False
            
            async with self.session.post(
                f"{self.base_url}/api/v1/core/metrics",
                json={
                    "project_id": project_id,
                    "metrics": metrics,
                    "timestamp": "auto"
                }
            ) as resp:
                if resp.status == 200:
                    logger.info("📊 Metrics tracked successfully")
                    return True
                return False
        except Exception as e:
            logger.debug(f"Metrics tracking failed: {e}")
            return False
    
    def _fallback_validation(
        self,
        project_dir: Path,
        phase: str
    ) -> Dict[str, Any]:
        """Fallback to file-based validation if Quality Fabric unavailable"""
        try:
            from validation_utils import validate_project_comprehensive
            logger.info("📁 Using fallback file-based validation")
            return validate_project_comprehensive(project_dir)
        except ImportError:
            logger.error("❌ Fallback validation not available")
            return {
                "overall_score": 0.0,
                "phase_scores": {},
                "issues_found": [],
                "recommendations": [],
                "validation_method": "unavailable"
            }
    
    def _generate_fallback_recommendations(
        self,
        validation_results: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Generate basic recommendations without AI"""
        recommendations = []
        issues = validation_results.get("issues_found", [])
        
        # Map issue types to personas
        persona_mapping = {
            "missing_tests": "qa_engineer",
            "incomplete_docs": "tech_writer",
            "api_issues": "backend_developer",
            "ui_issues": "frontend_developer",
            "deployment_issues": "devops_engineer"
        }
        
        for issue in issues[:10]:  # Limit to top 10
            issue_type = issue.get("type", "unknown")
            persona = persona_mapping.get(issue_type, "backend_developer")
            
            recommendations.append({
                "issue": issue.get("description", f"Fix {issue_type}"),
                "severity": issue.get("severity", "medium"),
                "persona": persona,
                "recommended_action": f"Address {issue_type} in {issue.get('file', 'project')}",
                "confidence": 0.70
            })
        
        return recommendations


# ============================================================================
# Integration Helper Functions
# ============================================================================

async def validate_with_quality_fabric(
    project_dir: Path,
    phase: str = "all",
    enable_ai_insights: bool = True
) -> Dict[str, Any]:
    """
    Convenience function for quality fabric validation
    
    Usage:
        results = await validate_with_quality_fabric(
            Path("./my_project"),
            "development"
        )
    """
    async with QualityFabricClient() as client:
        validation_results = await client.validate_project(
            project_dir,
            phase,
            validation_type="comprehensive"
        )
        
        if enable_ai_insights and validation_results.get("overall_score", 0) < 0.8:
            recommendations = await client.get_remediation_recommendations(
                validation_results
            )
            validation_results["ai_recommendations"] = recommendations
        
        return validation_results


async def get_quality_fabric_status() -> Dict[str, Any]:
    """Check Quality Fabric service status"""
    try:
        async with QualityFabricClient() as client:
            is_available = await client.health_check()
            return {
                "available": is_available,
                "service": "Quality Fabric",
                "base_url": client.base_url
            }
    except Exception as e:
        return {
            "available": False,
            "service": "Quality Fabric",
            "error": str(e)
        }


# ============================================================================
# CLI Interface for Testing
# ============================================================================

async def main():
    """Test Quality Fabric integration"""
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python quality_fabric_integration.py <project_dir> [phase]")
        print("Example: python quality_fabric_integration.py ./sunday_com development")
        sys.exit(1)
    
    project_dir = Path(sys.argv[1])
    phase = sys.argv[2] if len(sys.argv) > 2 else "all"
    
    print(f"\n🔍 Validating {project_dir} (phase: {phase})\n")
    
    # Check service status
    status = await get_quality_fabric_status()
    print(f"Quality Fabric Status: {'✅ Available' if status['available'] else '❌ Unavailable'}")
    print(f"Base URL: {status.get('base_url', 'N/A')}\n")
    
    # Run validation
    results = await validate_with_quality_fabric(project_dir, phase)
    
    print(f"Overall Score: {results.get('overall_score', 0):.2%}")
    print(f"Issues Found: {len(results.get('issues_found', []))}")
    print(f"Recommendations: {len(results.get('ai_recommendations', []))}")
    
    if results.get("ai_recommendations"):
        print("\n🤖 Top Recommendations:")
        for i, rec in enumerate(results["ai_recommendations"][:5], 1):
            print(f"  {i}. [{rec['severity']}] {rec['issue']}")
            print(f"     Persona: {rec['persona']}")
            print(f"     Action: {rec['recommended_action']}\n")


if __name__ == "__main__":
    asyncio.run(main())
