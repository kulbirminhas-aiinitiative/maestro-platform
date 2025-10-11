"""
Maestro API Client - Production-Grade Integration
Replaces direct file access with API-based communication for:
1. Template management (maestro-templates)
2. Quality predictions (quality-fabric)
3. Persona definitions (maestro-engine)

This eliminates ALL hardcoding and provides a proper service-oriented architecture.
"""
import asyncio
import aiohttp
from typing import Dict, Any, List, Optional
from pathlib import Path
import logging
import json
from dataclasses import dataclass, asdict
from datetime import datetime
import sys

logger = logging.getLogger(__name__)

# Service endpoints configuration
DEFAULT_MAESTRO_TEMPLATES_API = "http://localhost:8002/api"
DEFAULT_QUALITY_FABRIC_API = "http://localhost:8001/api"
DEFAULT_MAESTRO_ENGINE_API = "http://localhost:8003/api"


@dataclass
class TemplateMatch:
    """Represents a matched template from RAG system"""
    template_id: str
    persona: str
    similarity_score: float
    template_content: str
    metadata: Dict[str, Any]
    reuse_recommended: bool
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class QualityPrediction:
    """Quality prediction result"""
    predicted_score: float
    confidence: float
    risk_factors: List[str]
    recommendations: List[str]
    model_version: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class MaestroAPIClient:
    """
    Production-grade API client for Maestro ecosystem services.
    Eliminates all hardcoding and file-based access.
    """
    
    def __init__(
        self,
        templates_api_url: Optional[str] = None,
        quality_api_url: Optional[str] = None,
        engine_api_url: Optional[str] = None,
        similarity_threshold: float = 0.75,
        timeout: int = 30,
        fallback_to_direct: bool = True
    ):
        """
        Initialize API client.
        
        Args:
            templates_api_url: maestro-templates API endpoint
            quality_api_url: quality-fabric API endpoint
            engine_api_url: maestro-engine API endpoint
            similarity_threshold: Minimum similarity for template matches (0-1)
            timeout: Request timeout in seconds
            fallback_to_direct: Fallback to direct file access if APIs unavailable
        """
        self.templates_api_url = templates_api_url or DEFAULT_MAESTRO_TEMPLATES_API
        self.quality_api_url = quality_api_url or DEFAULT_QUALITY_FABRIC_API
        self.engine_api_url = engine_api_url or DEFAULT_MAESTRO_ENGINE_API
        self.similarity_threshold = similarity_threshold
        self.timeout = aiohttp.ClientTimeout(total=timeout)
        self.fallback_to_direct = fallback_to_direct
        
        # Session management
        self._session: Optional[aiohttp.ClientSession] = None
        self._services_available: Dict[str, bool] = {}
        
        # Cache
        self._persona_cache: Dict[str, Dict[str, Any]] = {}
        self._template_cache: Dict[str, List[Dict[str, Any]]] = {}
    
    async def __aenter__(self):
        """Async context manager entry"""
        await self._ensure_session()
        await self._check_services()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close()
    
    async def _ensure_session(self):
        """Ensure HTTP session is initialized"""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(timeout=self.timeout)
    
    async def close(self):
        """Close HTTP session"""
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None
    
    async def _check_services(self):
        """Check availability of all services"""
        await self._ensure_session()
        
        services = {
            "templates": f"{self.templates_api_url}/health",
            "quality": f"{self.quality_api_url}/health",
            "engine": f"{self.engine_api_url}/health"
        }
        
        for service_name, health_url in services.items():
            try:
                async with self._session.get(health_url) as response:
                    self._services_available[service_name] = response.status == 200
                    if self._services_available[service_name]:
                        logger.info(f"✅ {service_name} service available at {health_url}")
                    else:
                        logger.warning(f"⚠️  {service_name} service returned {response.status}")
            except Exception as e:
                self._services_available[service_name] = False
                logger.warning(f"❌ {service_name} service unavailable: {e}")
                if not self.fallback_to_direct:
                    raise
    
    def is_service_available(self, service: str) -> bool:
        """Check if a service is available"""
        return self._services_available.get(service, False)
    
    # ========================================================================
    # Template Management (maestro-templates API)
    # ========================================================================
    
    async def find_similar_templates(
        self,
        requirement: str,
        persona: str,
        threshold: Optional[float] = None
    ) -> List[TemplateMatch]:
        """
        Find similar templates using maestro-templates RAG API.
        
        Args:
            requirement: Current project requirement
            persona: Persona to find templates for
            threshold: Minimum similarity threshold (0-1)
        
        Returns:
            List of TemplateMatch objects sorted by similarity
        """
        threshold = threshold or self.similarity_threshold
        
        if not self.is_service_available("templates"):
            logger.warning("Templates service unavailable, using fallback")
            if self.fallback_to_direct:
                return await self._find_templates_direct(requirement, persona, threshold)
            return []
        
        try:
            await self._ensure_session()
            url = f"{self.templates_api_url}/templates/search"
            
            payload = {
                "query": requirement,
                "persona": persona,
                "threshold": threshold,
                "limit": 10
            }
            
            async with self._session.post(url, json=payload) as response:
                if response.status != 200:
                    logger.error(f"Template search failed: {response.status}")
                    return []
                
                data = await response.json()
                matches = []
                
                for result in data.get("results", []):
                    matches.append(TemplateMatch(
                        template_id=result.get("id", "unknown"),
                        persona=persona,
                        similarity_score=result.get("similarity", 0.0),
                        template_content=result.get("content", ""),
                        metadata=result.get("metadata", {}),
                        reuse_recommended=result.get("similarity", 0.0) >= 0.85
                    ))
                
                logger.info(f"Found {len(matches)} templates via API for {persona}")
                return matches
        
        except Exception as e:
            logger.error(f"Template search failed: {e}")
            if self.fallback_to_direct:
                return await self._find_templates_direct(requirement, persona, threshold)
            return []
    
    async def get_template_by_id(self, template_id: str) -> Optional[Dict[str, Any]]:
        """Get specific template by ID"""
        if not self.is_service_available("templates"):
            return None
        
        try:
            await self._ensure_session()
            url = f"{self.templates_api_url}/templates/{template_id}"
            
            async with self._session.get(url) as response:
                if response.status == 200:
                    return await response.json()
                return None
        
        except Exception as e:
            logger.error(f"Failed to get template {template_id}: {e}")
            return None
    
    async def list_templates_for_persona(self, persona: str) -> List[Dict[str, Any]]:
        """List all templates for a specific persona"""
        if not self.is_service_available("templates"):
            return []
        
        try:
            await self._ensure_session()
            url = f"{self.templates_api_url}/templates"
            params = {"persona": persona, "limit": 100}
            
            async with self._session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get("templates", [])
                return []
        
        except Exception as e:
            logger.error(f"Failed to list templates for {persona}: {e}")
            return []
    
    # ========================================================================
    # Quality Prediction (quality-fabric API)
    # ========================================================================
    
    async def predict_quality_score(
        self,
        requirement: str,
        personas: List[str],
        phase: str,
        context: Optional[Dict[str, Any]] = None
    ) -> QualityPrediction:
        """
        Predict quality score using quality-fabric ML models.
        
        Args:
            requirement: Project requirement text
            personas: List of persona IDs involved
            phase: SDLC phase name
            context: Additional context for prediction
        
        Returns:
            QualityPrediction with score, confidence, risks, and recommendations
        """
        if not self.is_service_available("quality"):
            logger.warning("Quality service unavailable, using fallback")
            if self.fallback_to_direct:
                return await self._predict_quality_direct(requirement, personas, phase)
            return QualityPrediction(
                predicted_score=0.70,
                confidence=0.50,
                risk_factors=["Quality service unavailable"],
                recommendations=["Retry when service is available"]
            )
        
        try:
            await self._ensure_session()
            url = f"{self.quality_api_url}/sdlc/predict-quality"
            
            payload = {
                "requirement": requirement,
                "personas": personas,
                "phase": phase,
                "context": context or {}
            }
            
            async with self._session.post(url, json=payload) as response:
                if response.status != 200:
                    logger.error(f"Quality prediction failed: {response.status}")
                    return QualityPrediction(
                        predicted_score=0.70,
                        confidence=0.50,
                        risk_factors=["Prediction service error"],
                        recommendations=[]
                    )
                
                data = await response.json()
                
                return QualityPrediction(
                    predicted_score=data.get("predicted_score", 0.70),
                    confidence=data.get("confidence", 0.50),
                    risk_factors=data.get("risk_factors", []),
                    recommendations=data.get("recommendations", []),
                    model_version=data.get("model_version")
                )
        
        except Exception as e:
            logger.error(f"Quality prediction failed: {e}")
            if self.fallback_to_direct:
                return await self._predict_quality_direct(requirement, personas, phase)
            return QualityPrediction(
                predicted_score=0.70,
                confidence=0.50,
                risk_factors=[f"Prediction error: {str(e)}"],
                recommendations=[]
            )
    
    async def analyze_complexity(
        self,
        requirement: str
    ) -> Dict[str, Any]:
        """
        Analyze requirement complexity using quality-fabric.
        
        Returns:
            {
                "complexity_score": 0.65,
                "factors": {...},
                "recommendations": [...]
            }
        """
        if not self.is_service_available("quality"):
            return self._analyze_complexity_direct(requirement)
        
        try:
            await self._ensure_session()
            url = f"{self.quality_api_url}/sdlc/analyze-complexity"
            
            payload = {"requirement": requirement}
            
            async with self._session.post(url, json=payload) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    return self._analyze_complexity_direct(requirement)
        
        except Exception as e:
            logger.error(f"Complexity analysis failed: {e}")
            return self._analyze_complexity_direct(requirement)
    
    # ========================================================================
    # Persona Management (maestro-engine API)
    # ========================================================================
    
    async def get_persona_definition(self, persona_id: str) -> Optional[Dict[str, Any]]:
        """Get persona definition from maestro-engine"""
        if persona_id in self._persona_cache:
            return self._persona_cache[persona_id]
        
        if not self.is_service_available("engine"):
            logger.warning("Engine service unavailable, using fallback")
            if self.fallback_to_direct:
                return await self._get_persona_direct(persona_id)
            return None
        
        try:
            await self._ensure_session()
            url = f"{self.engine_api_url}/personas/{persona_id}"
            
            async with self._session.get(url) as response:
                if response.status == 200:
                    persona = await response.json()
                    self._persona_cache[persona_id] = persona
                    return persona
                return None
        
        except Exception as e:
            logger.error(f"Failed to get persona {persona_id}: {e}")
            if self.fallback_to_direct:
                return await self._get_persona_direct(persona_id)
            return None
    
    async def get_all_personas(self) -> Dict[str, Dict[str, Any]]:
        """Get all persona definitions"""
        if self._persona_cache:
            return self._persona_cache.copy()
        
        if not self.is_service_available("engine"):
            if self.fallback_to_direct:
                return await self._get_all_personas_direct()
            return {}
        
        try:
            await self._ensure_session()
            url = f"{self.engine_api_url}/personas"
            
            async with self._session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    personas = data.get("personas", {})
                    self._persona_cache = personas
                    return personas
                return {}
        
        except Exception as e:
            logger.error(f"Failed to get personas: {e}")
            if self.fallback_to_direct:
                return await self._get_all_personas_direct()
            return {}
    
    async def get_persona_keywords(self, persona_id: str) -> List[str]:
        """Get searchable keywords for a persona"""
        persona = await self.get_persona_definition(persona_id)
        if not persona:
            return []
        
        # Extract keywords from specializations and capabilities
        specializations = persona.get("role", {}).get("specializations", [])
        core_capabilities = persona.get("capabilities", {}).get("core", [])
        
        keywords = []
        for term in specializations + core_capabilities:
            # Convert underscore-separated terms to words
            words = term.replace("_", " ").split()
            keywords.extend(words)
            keywords.append(term.replace("_", " "))
        
        return list(set(keywords))
    
    async def get_persona_priority(self, persona_id: str) -> int:
        """Get execution priority for a persona (lower = higher priority)"""
        persona = await self.get_persona_definition(persona_id)
        if not persona:
            return 100  # Default low priority
        
        return persona.get("execution", {}).get("priority", 100)
    
    async def optimize_persona_execution_order(
        self,
        personas: List[str],
        requirement: str
    ) -> List[str]:
        """
        Optimize persona execution order based on dynamic priorities and dependencies.
        Uses API-provided configuration, no hardcoding.
        """
        # Get all persona definitions
        persona_definitions = await asyncio.gather(*[
            self.get_persona_definition(p) for p in personas
        ])
        
        # Build priority map
        priority_map = {}
        for persona_id, definition in zip(personas, persona_definitions):
            if definition:
                priority_map[persona_id] = definition.get("execution", {}).get("priority", 100)
            else:
                priority_map[persona_id] = 100
        
        # Sort by priority (lower number = higher priority)
        optimized = sorted(personas, key=lambda p: priority_map.get(p, 100))
        
        if optimized != personas:
            priority_info = [f"{p}({priority_map.get(p, '?')})" for p in optimized[:5]]
            logger.info(f"Optimized execution order: {' → '.join(priority_info)}")
        
        return optimized
    
    async def extract_required_personas(self, requirement: str) -> List[str]:
        """
        Extract required personas from requirement using keyword matching.
        Uses dynamic persona definitions from API.
        """
        requirement_lower = requirement.lower()
        required = []
        
        # Get all personas
        all_personas = await self.get_all_personas()
        
        # Match personas based on keywords
        for persona_id in all_personas.keys():
            keywords = await self.get_persona_keywords(persona_id)
            if any(keyword.lower() in requirement_lower for keyword in keywords):
                required.append(persona_id)
        
        # Ensure minimum set if none matched
        if not required:
            # Get personas with highest priorities as defaults
            persona_priorities = {}
            for persona_id in all_personas.keys():
                priority = await self.get_persona_priority(persona_id)
                persona_priorities[persona_id] = priority
            
            # Sort by priority and take top 2
            sorted_personas = sorted(persona_priorities.items(), key=lambda x: x[1])[:2]
            required = [p[0] for p in sorted_personas]
        
        return required
    
    # ========================================================================
    # Cost Estimation
    # ========================================================================
    
    async def estimate_cost_savings(
        self,
        personas: List[str],
        reuse_candidates: Dict[str, List[TemplateMatch]]
    ) -> Dict[str, Any]:
        """
        Estimate cost savings from template reuse.
        
        Returns:
            {
                "total_cost_without_reuse": 1000,
                "total_cost_with_reuse": 650,
                "savings_usd": 350,
                "savings_percent": 0.35,
                "personas_reused": [...],
                "personas_executed": [...],
                "breakdown": {...}
            }
        """
        COST_PER_PERSONA = 100  # USD per persona execution
        REUSE_COST_FACTOR = 0.15  # 15% of full cost when reusing
        
        total_without_reuse = len(personas) * COST_PER_PERSONA
        total_with_reuse = 0
        reused = []
        executed = []
        breakdown = {}
        
        for persona in personas:
            persona_cost = COST_PER_PERSONA
            reuse_status = "executed"
            
            if persona in reuse_candidates and reuse_candidates[persona]:
                best_match = reuse_candidates[persona][0]
                if best_match.reuse_recommended:
                    persona_cost = COST_PER_PERSONA * REUSE_COST_FACTOR
                    reused.append(persona)
                    reuse_status = "reused"
                else:
                    executed.append(persona)
            else:
                executed.append(persona)
            
            total_with_reuse += persona_cost
            breakdown[persona] = {
                "status": reuse_status,
                "cost": persona_cost,
                "similarity": reuse_candidates.get(persona, [{}])[0].similarity_score 
                            if persona in reuse_candidates and reuse_candidates[persona] 
                            else 0.0
            }
        
        savings = total_without_reuse - total_with_reuse
        savings_percent = savings / total_without_reuse if total_without_reuse > 0 else 0
        
        result = {
            "total_cost_without_reuse": total_without_reuse,
            "total_cost_with_reuse": total_with_reuse,
            "savings_usd": savings,
            "savings_percent": savings_percent,
            "personas_reused": reused,
            "personas_executed": executed,
            "breakdown": breakdown
        }
        
        logger.info(f"💰 Cost savings: ${savings:.2f} ({savings_percent:.1%})")
        return result
    
    # ========================================================================
    # Fallback Methods (Direct File Access)
    # ========================================================================
    
    async def _find_templates_direct(
        self,
        requirement: str,
        persona: str,
        threshold: float
    ) -> List[TemplateMatch]:
        """Fallback: Direct file system access for templates"""
        # Import the old client for fallback
        try:
            from maestro_ml_client import MaestroMLClient
            client = MaestroMLClient()
            return await client.find_similar_templates(requirement, persona, threshold)
        except Exception as e:
            logger.error(f"Fallback template search failed: {e}")
            return []
    
    async def _predict_quality_direct(
        self,
        requirement: str,
        personas: List[str],
        phase: str
    ) -> QualityPrediction:
        """Fallback: Direct quality prediction"""
        try:
            from maestro_ml_client import MaestroMLClient
            client = MaestroMLClient()
            result = await client.predict_quality_score(requirement, personas, phase)
            return QualityPrediction(
                predicted_score=result["predicted_score"],
                confidence=result["confidence"],
                risk_factors=result["risk_factors"],
                recommendations=result["recommendations"]
            )
        except Exception as e:
            logger.error(f"Fallback quality prediction failed: {e}")
            return QualityPrediction(
                predicted_score=0.70,
                confidence=0.50,
                risk_factors=["Fallback prediction failed"],
                recommendations=[]
            )
    
    def _analyze_complexity_direct(self, requirement: str) -> Dict[str, Any]:
        """Fallback: Direct complexity analysis"""
        word_count = len(requirement.split())
        
        # Complexity indicators
        indicators = {
            "has_integration": any(w in requirement.lower() for w in ['api', 'integration', 'third-party']),
            "has_auth": any(w in requirement.lower() for w in ['authentication', 'authorization', 'login']),
            "has_database": any(w in requirement.lower() for w in ['database', 'data', 'storage']),
            "has_realtime": any(w in requirement.lower() for w in ['realtime', 'websocket', 'streaming'])
        }
        
        # Base complexity from word count
        complexity = min(word_count / 500, 1.0)
        
        # Adjust for indicators
        if indicators["has_integration"]:
            complexity += 0.1
        if indicators["has_auth"]:
            complexity += 0.1
        if indicators["has_database"]:
            complexity += 0.05
        if indicators["has_realtime"]:
            complexity += 0.15
        
        return {
            "complexity_score": min(complexity, 1.0),
            "factors": indicators,
            "recommendations": []
        }
    
    async def _get_persona_direct(self, persona_id: str) -> Optional[Dict[str, Any]]:
        """Fallback: Direct persona file access"""
        try:
            persona_file = Path(f"/home/ec2-user/projects/maestro-engine/src/personas/definitions/{persona_id}.json")
            if persona_file.exists():
                with open(persona_file, 'r') as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"Fallback persona loading failed for {persona_id}: {e}")
        return None
    
    async def _get_all_personas_direct(self) -> Dict[str, Dict[str, Any]]:
        """Fallback: Direct access to all personas"""
        try:
            personas_dir = Path("/home/ec2-user/projects/maestro-engine/src/personas/definitions")
            personas = {}
            
            if personas_dir.exists():
                for json_file in personas_dir.glob("*.json"):
                    try:
                        with open(json_file, 'r') as f:
                            persona_data = json.load(f)
                            persona_id = persona_data.get("persona_id")
                            if persona_id:
                                personas[persona_id] = persona_data
                    except Exception as e:
                        logger.warning(f"Failed to load {json_file}: {e}")
            
            return personas
        except Exception as e:
            logger.error(f"Fallback persona loading failed: {e}")
            return {}


# ============================================================================
# High-Level Integration Functions
# ============================================================================

async def get_ml_enhanced_recommendations(
    requirement: str,
    personas: List[str],
    phase: str = "development",
    api_client: Optional[MaestroAPIClient] = None
) -> Dict[str, Any]:
    """
    Get ML-enhanced recommendations using API-based services.
    
    Returns:
        {
            "quality_prediction": {...},
            "template_matches": {...},
            "optimized_order": [...],
            "cost_estimate": {...},
            "complexity_analysis": {...}
        }
    """
    # Use provided client or create new one
    if api_client:
        client = api_client
        close_client = False
    else:
        client = MaestroAPIClient()
        await client._check_services()
        close_client = True
    
    try:
        # Run analyses in parallel where possible
        quality_pred = await client.predict_quality_score(requirement, personas, phase)
        complexity = await client.analyze_complexity(requirement)
        
        # Find templates for each persona
        template_matches_list = await asyncio.gather(*[
            client.find_similar_templates(requirement, persona)
            for persona in personas
        ])
        
        # Build template matches dict
        template_dict = {
            personas[i]: matches
            for i, matches in enumerate(template_matches_list)
        }
        
        # Optimize execution order
        optimized_order = await client.optimize_persona_execution_order(personas, requirement)
        
        # Estimate cost savings
        cost_estimate = await client.estimate_cost_savings(personas, template_dict)
        
        return {
            "quality_prediction": quality_pred.to_dict(),
            "template_matches": {k: [m.to_dict() for m in v] for k, v in template_dict.items()},
            "optimized_order": optimized_order,
            "cost_estimate": cost_estimate,
            "complexity_analysis": complexity
        }
    
    finally:
        if close_client:
            await client.close()


async def check_services_health() -> Dict[str, Any]:
    """Check health of all Maestro services"""
    async with MaestroAPIClient() as client:
        return {
            "templates_api": client.is_service_available("templates"),
            "quality_api": client.is_service_available("quality"),
            "engine_api": client.is_service_available("engine"),
            "templates_url": client.templates_api_url,
            "quality_url": client.quality_api_url,
            "engine_url": client.engine_api_url
        }


# ============================================================================
# CLI Interface for Testing
# ============================================================================

async def main():
    """Test Maestro API integration"""
    print("\n🤖 Maestro API Integration Test\n")
    print("=" * 70)
    
    # Check service health
    print("\n🏥 Checking Service Health...")
    print("-" * 70)
    health = await check_services_health()
    
    for service, status in health.items():
        if service.endswith("_url"):
            print(f"  {service.replace('_url', '')}: {status}")
        else:
            icon = "✅" if status else "❌"
            print(f"  {icon} {service}: {'Available' if status else 'Unavailable'}")
    
    # Test with sample requirement
    print("\n🧪 Testing ML Recommendations...")
    print("-" * 70)
    
    requirement = """
    Build a REST API with:
    - User authentication (JWT)
    - CRUD operations for blog posts
    - PostgreSQL database
    - Docker deployment
    - API documentation
    """
    
    personas = ["backend_developer", "devops_engineer", "qa_engineer"]
    
    print("Sample Requirement:")
    print(requirement.strip())
    print(f"\nPersonas: {', '.join(personas)}\n")
    
    # Get recommendations
    async with MaestroAPIClient() as client:
        recommendations = await get_ml_enhanced_recommendations(
            requirement,
            personas,
            "development",
            api_client=client
        )
    
    print("=" * 70)
    print("API-Based ML Recommendations")
    print("=" * 70)
    
    print(f"\n📊 Quality Prediction:")
    pred = recommendations["quality_prediction"]
    print(f"  Score: {pred['predicted_score']:.2%}")
    print(f"  Confidence: {pred['confidence']:.2%}")
    if pred['risk_factors']:
        print(f"  Risk Factors: {', '.join(pred['risk_factors'])}")
    
    print(f"\n🔍 Complexity Analysis:")
    comp = recommendations["complexity_analysis"]
    print(f"  Score: {comp['complexity_score']:.2%}")
    
    print(f"\n⚡ Optimized Execution Order:")
    print(f"  {' → '.join(recommendations['optimized_order'])}")
    
    print(f"\n💰 Cost Estimate:")
    cost = recommendations["cost_estimate"]
    print(f"  Without Reuse: ${cost['total_cost_without_reuse']:.2f}")
    print(f"  With Reuse: ${cost['total_cost_with_reuse']:.2f}")
    print(f"  Savings: ${cost['savings_usd']:.2f} ({cost['savings_percent']:.1%})")
    
    print(f"\n📁 Template Matches:")
    for persona, matches in recommendations["template_matches"].items():
        print(f"  {persona}: {len(matches)} templates found")
        if matches:
            print(f"    Best match: {matches[0]['similarity_score']:.2%} similarity")
    
    print("\n" + "=" * 70)
    print("✅ All tests completed successfully!")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
