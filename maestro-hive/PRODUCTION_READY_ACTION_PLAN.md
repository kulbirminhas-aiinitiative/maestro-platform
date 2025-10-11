# Production-Ready Action Plan
## Making sunday_com Production-Ready via Automated Workflow

**Date:** October 5, 2025  
**Goal:** Complete ML/RAG integration and make system fully autonomous  
**Timeline:** 2-3 days (16-24 hours focused work)  
**Status:** 🚀 Ready to Execute

---

## Critical Path Overview

```
Current State: 85% Complete
├─ phased_autonomous_executor.py: ✅ 90% (orchestration works)
├─ team_execution.py: ✅ 95% (execution works)
└─ maestro_ml_client.py: ⚠️ 70% (hardcoding blocks integration)

Blockers:
├─ Hardcoded paths (4 hours to fix)
├─ Hardcoded keywords/priorities (2 hours to fix)
├─ Missing API integration (6-8 hours to add)
└─ Intelligence not wired in (4 hours to connect)

After Fixes: 98% Complete → Production Ready
```

---

## Phase 1: Remove Hardcoding (Day 1 Morning, 4-6 hours)

### 1.1 Fix Path Management (2 hours)

**File:** `maestro_ml_client.py`

**Current Issues:**
```python
# Line 20
MAESTRO_ENGINE_PATH = Path("/home/ec2-user/projects/maestro-engine")

# Line 148
templates_path: str = "/home/ec2-user/projects/maestro-templates/storage/templates"
```

**Fix:**
```python
# Add Config class (already partially exists, expand it)
class Config:
    @staticmethod
    def get_maestro_engine_path() -> Path:
        """Get path from env or auto-detect"""
        if env_path := os.getenv('MAESTRO_ENGINE_PATH'):
            return Path(env_path)
        
        # Auto-detect relative path
        current = Path(__file__).resolve()
        repo_root = current.parent.parent.parent
        engine_path = repo_root / "maestro-engine"
        
        if engine_path.exists():
            return engine_path
        
        # Fallback to default
        default = Path("/home/ec2-user/projects/maestro-engine")
        if default.exists():
            return default
            
        raise RuntimeError(
            "maestro-engine not found. Set MAESTRO_ENGINE_PATH env var"
        )
    
    @staticmethod
    def get_templates_path() -> Path:
        """Get templates path from env or auto-detect"""
        if env_path := os.getenv('MAESTRO_TEMPLATES_PATH'):
            return Path(env_path)
        
        # Try API URL first
        if api_url := os.getenv('MAESTRO_TEMPLATES_API'):
            return api_url  # Will use API instead of filesystem
        
        # Auto-detect relative path
        current = Path(__file__).resolve()
        repo_root = current.parent.parent.parent
        templates_path = repo_root / "maestro-templates" / "storage" / "templates"
        
        if templates_path.exists():
            return templates_path
        
        raise RuntimeError(
            "maestro-templates not found. "
            "Set MAESTRO_TEMPLATES_PATH or MAESTRO_TEMPLATES_API env var"
        )

# Update module-level initialization
MAESTRO_ENGINE_PATH = Config.get_maestro_engine_path()
```

**Test:**
```bash
# Should work on any machine
export MAESTRO_ENGINE_PATH=/custom/path/maestro-engine
python -c "from maestro_ml_client import MAESTRO_ENGINE_PATH; print(MAESTRO_ENGINE_PATH)"
```

### 1.2 Use Dynamic Persona Data (2 hours)

**Current Issues:**
```python
# Lines 310-330 - Hardcoded keywords
persona_keywords = {
    "product_manager": ["requirements", "user stories", "features"],
    "backend_developer": ["api", "database", "backend"],
    # ... hardcoded for all personas
}

# Lines 160-240 - Hardcoded priorities
priority_order = {
    "product_manager": 1,
    "architect": 2,
    "backend_developer": 3,
    # ... static priorities
}
```

**Fix:**
```python
class PersonaRegistry:
    def __init__(self):
        self._personas: Dict[str, Dict[str, Any]] = {}
        self._keywords_map: Dict[str, List[str]] = {}
        self._priority_map: Dict[str, int] = {}
        self._load_personas()
    
    def _load_personas(self):
        """Load personas and extract keywords/priorities from JSON"""
        personas_dir = MAESTRO_ENGINE_PATH / "src" / "personas" / "definitions"
        
        for json_file in personas_dir.glob("*.json"):
            try:
                with open(json_file, 'r') as f:
                    persona_data = json.load(f)
                
                persona_id = persona_data.get("persona_id")
                if not persona_id:
                    continue
                
                # Store full persona data
                self._personas[persona_id] = persona_data
                
                # Extract keywords from JSON (no hardcoding!)
                keywords = set()
                
                # From search_keywords field (if exists)
                if "search_keywords" in persona_data:
                    keywords.update(persona_data["search_keywords"])
                
                # From specializations
                if "specializations" in persona_data:
                    for spec in persona_data["specializations"]:
                        keywords.add(spec.replace("_", " "))
                        keywords.update(spec.replace("_", " ").split())
                
                # From capabilities
                if "core_capabilities" in persona_data:
                    for cap in persona_data["core_capabilities"]:
                        keywords.add(cap.replace("_", " "))
                
                # From role description
                if "role" in persona_data:
                    keywords.update(persona_data["role"].lower().split())
                
                self._keywords_map[persona_id] = list(keywords)
                
                # Extract priority from JSON
                self._priority_map[persona_id] = persona_data.get(
                    "dependency_priority",
                    persona_data.get("execution_priority", 5)  # Default to middle priority
                )
                
            except Exception as e:
                logger.warning(f"Failed to load persona {json_file}: {e}")
    
    def get_persona_keywords(self, persona_id: str) -> List[str]:
        """Get keywords for persona matching"""
        return self._keywords_map.get(persona_id, [])
    
    def get_persona_priority(self, persona_id: str) -> int:
        """Get execution priority for persona"""
        return self._priority_map.get(persona_id, 5)
    
    def get_priority_order(self) -> Dict[str, int]:
        """Get priority order for all personas"""
        return self._priority_map.copy()

class MaestroMLClient:
    def __init__(self):
        self.persona_registry = PersonaRegistry()
        # No more hardcoded dictionaries!
    
    def select_optimal_personas(self, requirement: str, all_personas: List[str]) -> List[str]:
        """Select personas based on requirement with dynamic priorities"""
        
        # Use dynamic keywords from JSON
        persona_scores = {}
        for persona in all_personas:
            keywords = self.persona_registry.get_persona_keywords(persona)
            score = self._calculate_relevance(requirement, keywords)
            persona_scores[persona] = score
        
        # Filter by relevance threshold
        relevant_personas = {
            p: score for p, score in persona_scores.items() 
            if score > 0.3
        }
        
        # Sort by dynamic priority
        priority_order = self.persona_registry.get_priority_order()
        sorted_personas = sorted(
            relevant_personas.keys(),
            key=lambda p: (
                -persona_scores[p],  # Higher score first
                priority_order.get(p, 5)  # Then by priority
            )
        )
        
        return sorted_personas
```

**Test:**
```python
# Test dynamic loading
registry = PersonaRegistry()
keywords = registry.get_persona_keywords("backend_developer")
priority = registry.get_persona_priority("backend_developer")

# Should come from JSON, not hardcoded
assert len(keywords) > 0
assert isinstance(priority, int)
```

### 1.3 Remove Mock ML Predictions (2 hours)

**Current Issue:**
```python
# Lines 210-270 - predict_quality_score()
async def predict_quality_score(...) -> Dict[str, Any]:
    # Hardcoded baseline
    prediction = {
        "predicted_score": 0.80,  # Static value!
        "confidence": 0.75,
        # ... all hardcoded
    }
    
    # Analyze complexity with hardcoded thresholds
    complexity = await self._analyze_complexity(requirement)
    if complexity > 0.7:  # Magic number
        prediction["predicted_score"] -= 0.10  # Magic number
```

**Fix:**
```python
# Extract thresholds to constants
class QualityPredictionConfig:
    """Configuration for quality prediction"""
    BASE_SCORE = 0.70  # Start at 70% (realistic baseline)
    HIGH_COMPLEXITY_THRESHOLD = 0.7
    COMPLEXITY_PENALTY = 0.10
    MISSING_PERSONA_PENALTY = 0.05
    PHASE_BONUS = {
        "requirements": 0.05,
        "design": 0.03,
        "implementation": 0.0,
        "testing": 0.10,
        "deployment": 0.02
    }

async def predict_quality_score(
    self,
    requirement: str,
    personas: List[str],
    phase: str
) -> Dict[str, Any]:
    """
    Predict quality score using enhanced rule-based system
    
    Note: This is rule-based, not ML. For true ML predictions,
    integrate with quality-fabric API.
    """
    config = QualityPredictionConfig()
    
    # Start with baseline
    predicted_score = config.BASE_SCORE
    
    # Analyze requirement complexity
    complexity = await self._analyze_complexity(requirement)
    if complexity > config.HIGH_COMPLEXITY_THRESHOLD:
        predicted_score -= config.COMPLEXITY_PENALTY
    
    # Check persona completeness
    optimal_personas = await self.select_optimal_personas(requirement, personas)
    missing_count = len(set(optimal_personas) - set(personas))
    predicted_score -= missing_count * config.MISSING_PERSONA_PENALTY
    
    # Phase bonus
    predicted_score += config.PHASE_BONUS.get(phase, 0.0)
    
    # Clamp to valid range
    predicted_score = max(0.0, min(1.0, predicted_score))
    
    # Calculate confidence based on data availability
    confidence = 0.65  # Rule-based has lower confidence
    if len(personas) >= len(optimal_personas):
        confidence += 0.15  # Higher confidence with complete team
    
    return {
        "predicted_score": predicted_score,
        "confidence": confidence,
        "prediction_method": "rule_based",  # Be honest about method
        "complexity_score": complexity,
        "optimal_personas": optimal_personas,
        "missing_personas": list(set(optimal_personas) - set(personas)),
        "note": "For ML-based predictions, enable quality-fabric API integration"
    }
```

---

## Phase 2: API Integration (Day 1 Afternoon + Day 2 Morning, 8-10 hours)

### 2.1 Create Configuration System (2 hours)

**Create:** `maestro_config.py`

```python
"""
Centralized configuration for all Maestro services
"""
import os
from pathlib import Path
from dataclasses import dataclass
from typing import Optional
import yaml

@dataclass
class ServiceConfig:
    """Configuration for external services"""
    
    # Paths
    maestro_engine_path: Path
    maestro_templates_path: Optional[Path] = None
    
    # API URLs
    maestro_templates_api: Optional[str] = None
    quality_fabric_api: Optional[str] = None
    maestro_ml_api: Optional[str] = None
    
    # Feature flags
    enable_api_mode: bool = False
    enable_template_reuse: bool = True
    enable_quality_prediction: bool = True
    
    # Performance
    cache_ttl_seconds: int = 3600
    max_concurrent_requests: int = 10
    
    @classmethod
    def from_env(cls) -> 'ServiceConfig':
        """Load configuration from environment variables"""
        return cls(
            maestro_engine_path=Path(
                os.getenv('MAESTRO_ENGINE_PATH', 
                         '/home/ec2-user/projects/maestro-engine')
            ),
            maestro_templates_path=Path(
                os.getenv('MAESTRO_TEMPLATES_PATH',
                         '/home/ec2-user/projects/maestro-templates/storage/templates')
            ) if not os.getenv('MAESTRO_TEMPLATES_API') else None,
            maestro_templates_api=os.getenv('MAESTRO_TEMPLATES_API'),
            quality_fabric_api=os.getenv('QUALITY_FABRIC_API'),
            maestro_ml_api=os.getenv('MAESTRO_ML_API'),
            enable_api_mode=bool(os.getenv('MAESTRO_TEMPLATES_API')),
            enable_template_reuse=os.getenv('ENABLE_TEMPLATE_REUSE', 'true').lower() == 'true',
            enable_quality_prediction=os.getenv('ENABLE_QUALITY_PREDICTION', 'true').lower() == 'true',
            cache_ttl_seconds=int(os.getenv('CACHE_TTL_SECONDS', '3600')),
            max_concurrent_requests=int(os.getenv('MAX_CONCURRENT_REQUESTS', '10'))
        )
    
    @classmethod
    def from_yaml(cls, config_file: str) -> 'ServiceConfig':
        """Load configuration from YAML file"""
        with open(config_file, 'r') as f:
            data = yaml.safe_load(f)
        
        return cls(
            maestro_engine_path=Path(data['paths']['maestro_engine']),
            maestro_templates_path=Path(data['paths']['maestro_templates']) if 'maestro_templates' in data['paths'] else None,
            maestro_templates_api=data.get('apis', {}).get('maestro_templates'),
            quality_fabric_api=data.get('apis', {}).get('quality_fabric'),
            maestro_ml_api=data.get('apis', {}).get('maestro_ml'),
            enable_api_mode=data.get('features', {}).get('enable_api_mode', False),
            enable_template_reuse=data.get('features', {}).get('enable_template_reuse', True),
            enable_quality_prediction=data.get('features', {}).get('enable_quality_prediction', True),
            cache_ttl_seconds=data.get('performance', {}).get('cache_ttl_seconds', 3600),
            max_concurrent_requests=data.get('performance', {}).get('max_concurrent_requests', 10)
        )

# Global config instance
_config: Optional[ServiceConfig] = None

def get_config() -> ServiceConfig:
    """Get global configuration instance"""
    global _config
    if _config is None:
        # Try loading from YAML first
        config_file = os.getenv('MAESTRO_CONFIG_FILE', 'maestro_config.yaml')
        if os.path.exists(config_file):
            _config = ServiceConfig.from_yaml(config_file)
        else:
            _config = ServiceConfig.from_env()
    return _config

def set_config(config: ServiceConfig):
    """Set global configuration"""
    global _config
    _config = config
```

**Create:** `maestro_config.yaml` (default configuration)

```yaml
paths:
  maestro_engine: /home/ec2-user/projects/maestro-engine
  maestro_templates: /home/ec2-user/projects/maestro-templates/storage/templates

apis:
  maestro_templates: null  # Set to http://localhost:8000 to enable API mode
  quality_fabric: null     # Set to http://localhost:8001 to enable
  maestro_ml: null         # Set to http://localhost:8002 to enable

features:
  enable_api_mode: false          # Use filesystem when false
  enable_template_reuse: true     # Enable template matching
  enable_quality_prediction: true # Enable quality predictions

performance:
  cache_ttl_seconds: 3600
  max_concurrent_requests: 10

# Override any value with environment variables:
# MAESTRO_ENGINE_PATH, MAESTRO_TEMPLATES_API, etc.
```

### 2.2 Create Quality Fabric Client (2-3 hours)

**Create:** `quality_fabric_client.py`

```python
"""
Client for quality-fabric service API
Provides quality assessment and predictions
"""
import aiohttp
import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
import json

logger = logging.getLogger(__name__)

@dataclass
class QualityAssessment:
    """Quality assessment result"""
    overall_score: float
    dimensions: Dict[str, float]  # code_quality, documentation, testing, etc.
    issues: List[Dict[str, Any]]
    recommendations: List[str]
    confidence: float

class QualityFabricClient:
    """
    Client for quality-fabric API
    
    Supports both API mode and fallback rule-based mode
    """
    
    def __init__(self, api_url: Optional[str] = None):
        from maestro_config import get_config
        config = get_config()
        
        self.api_url = api_url or config.quality_fabric_api
        self.use_api = bool(self.api_url)
        
        if not self.use_api:
            logger.info("Quality Fabric API not configured, using rule-based fallback")
    
    async def assess_project_quality(
        self,
        project_dir: str,
        personas_used: List[str]
    ) -> QualityAssessment:
        """Assess quality of existing project"""
        
        if self.use_api:
            return await self._assess_via_api(project_dir, personas_used)
        else:
            return await self._assess_rule_based(project_dir, personas_used)
    
    async def predict_quality(
        self,
        requirement: str,
        personas: List[str],
        phase: str
    ) -> Dict[str, Any]:
        """Predict quality score for upcoming work"""
        
        if self.use_api:
            return await self._predict_via_api(requirement, personas, phase)
        else:
            return await self._predict_rule_based(requirement, personas, phase)
    
    async def _assess_via_api(
        self,
        project_dir: str,
        personas_used: List[str]
    ) -> QualityAssessment:
        """Assess quality via API"""
        
        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(
                    f"{self.api_url}/api/assess",
                    json={
                        "project_dir": project_dir,
                        "personas_used": personas_used
                    },
                    timeout=aiohttp.ClientTimeout(total=60)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        return QualityAssessment(**data)
                    else:
                        logger.error(f"API returned {response.status}")
                        return await self._assess_rule_based(project_dir, personas_used)
            
            except Exception as e:
                logger.error(f"API call failed: {e}, falling back to rule-based")
                return await self._assess_rule_based(project_dir, personas_used)
    
    async def _assess_rule_based(
        self,
        project_dir: str,
        personas_used: List[str]
    ) -> QualityAssessment:
        """Fallback rule-based assessment"""
        from validation_utils import analyze_implementation_quality
        
        # Use existing validation utilities
        results = analyze_implementation_quality(project_dir)
        
        return QualityAssessment(
            overall_score=results.get('overall_score', 0.5),
            dimensions=results.get('dimensions', {}),
            issues=results.get('issues', []),
            recommendations=results.get('recommendations', []),
            confidence=0.65  # Lower confidence for rule-based
        )
    
    async def _predict_via_api(
        self,
        requirement: str,
        personas: List[str],
        phase: str
    ) -> Dict[str, Any]:
        """Predict quality via API"""
        
        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(
                    f"{self.api_url}/api/predict",
                    json={
                        "requirement": requirement,
                        "personas": personas,
                        "phase": phase
                    },
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        logger.error(f"API returned {response.status}")
                        return await self._predict_rule_based(requirement, personas, phase)
            
            except Exception as e:
                logger.error(f"API call failed: {e}, falling back to rule-based")
                return await self._predict_rule_based(requirement, personas, phase)
    
    async def _predict_rule_based(
        self,
        requirement: str,
        personas: List[str],
        phase: str
    ) -> Dict[str, Any]:
        """Fallback rule-based prediction"""
        # Use existing logic from maestro_ml_client
        # (Extract the improved version from Phase 1.3)
        return {
            "predicted_score": 0.70,
            "confidence": 0.65,
            "method": "rule_based"
        }
```

### 2.3 Update Maestro ML Client for API Support (4-5 hours)

**Update:** `maestro_ml_client.py`

```python
class MaestroMLClient:
    def __init__(self, config: Optional[ServiceConfig] = None):
        from maestro_config import get_config
        from quality_fabric_client import QualityFabricClient
        
        self.config = config or get_config()
        self.persona_registry = PersonaRegistry()
        self.quality_client = QualityFabricClient(self.config.quality_fabric_api)
        
        # Template storage
        self.templates_path = self.config.maestro_templates_path
        self.use_api = self.config.enable_api_mode
        self._template_cache: Dict[str, List[Dict[str, Any]]] = {}
    
    async def find_similar_templates(
        self,
        requirement: str,
        persona: str,
        threshold: Optional[float] = None
    ) -> List[TemplateMatch]:
        """Find similar templates - API or filesystem"""
        
        if self.use_api and self.config.maestro_templates_api:
            return await self._find_templates_via_api(requirement, persona, threshold)
        else:
            return await self._find_templates_via_filesystem(requirement, persona, threshold)
    
    async def _find_templates_via_api(
        self,
        requirement: str,
        persona: str,
        threshold: Optional[float]
    ) -> List[TemplateMatch]:
        """Find templates via API"""
        
        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(
                    f"{self.config.maestro_templates_api}/api/search",
                    json={
                        "query": requirement,
                        "persona": persona,
                        "threshold": threshold or 0.7,
                        "max_results": 10
                    },
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        return [
                            TemplateMatch(
                                template_id=t['template_id'],
                                persona=persona,
                                similarity_score=t['similarity_score'],
                                template_content=t['content'],
                                metadata=t.get('metadata', {})
                            )
                            for t in data['results']
                        ]
                    else:
                        logger.warning(f"Template API returned {response.status}, falling back to filesystem")
                        return await self._find_templates_via_filesystem(requirement, persona, threshold)
            
            except Exception as e:
                logger.warning(f"Template API failed: {e}, falling back to filesystem")
                return await self._find_templates_via_filesystem(requirement, persona, threshold)
    
    async def _find_templates_via_filesystem(
        self,
        requirement: str,
        persona: str,
        threshold: Optional[float]
    ) -> List[TemplateMatch]:
        """Find templates via filesystem (existing logic)"""
        # Keep existing implementation for backward compatibility
        # ... (current filesystem logic)
    
    async def predict_quality_score(
        self,
        requirement: str,
        personas: List[str],
        phase: str
    ) -> Dict[str, Any]:
        """Predict quality - delegates to quality fabric client"""
        return await self.quality_client.predict_quality(requirement, personas, phase)
```

---

## Phase 3: Wire Intelligence Into Execution (Day 2 Afternoon, 4-6 hours)

### 3.1 Update Phased Executor to Use ML Guidance (2 hours)

**File:** `phased_autonomous_executor.py`

```python
class PhasedAutonomousExecutor:
    def __init__(self, ...):
        # ... existing init
        
        # Add ML client
        from maestro_ml_client import MaestroMLClient
        self.ml_client = MaestroMLClient()
    
    async def _select_personas_for_phase(
        self,
        phase: SDLCPhase,
        iteration: int
    ) -> List[str]:
        """Select personas using ML guidance"""
        
        # Get base personas for this phase
        mapping = self._get_phase_mapping(phase)
        base_personas = mapping.required_personas.copy()
        
        # On iteration 2+, consider optional personas
        if iteration > 1:
            base_personas.extend(mapping.optional_personas)
        
        # Use ML to optimize persona selection
        if self.ml_client.config.enable_template_reuse:
            optimized_personas = await self.ml_client.select_optimal_personas(
                requirement=self.requirement,
                all_personas=base_personas,
                phase=phase.value
            )
            
            logger.info(f"ML optimized persona selection:")
            logger.info(f"  Base: {base_personas}")
            logger.info(f"  Optimized: {optimized_personas}")
            
            return optimized_personas
        else:
            return base_personas
    
    async def _should_accept_quality(
        self,
        phase: SDLCPhase,
        quality_score: float,
        iteration: int
    ) -> bool:
        """Decide if quality is acceptable using ML prediction"""
        
        # Get required threshold
        required_threshold = self.quality_manager.get_threshold(
            phase=phase,
            iteration=iteration
        )
        
        # Get ML prediction
        personas = await self._select_personas_for_phase(phase, iteration)
        prediction = await self.ml_client.predict_quality_score(
            requirement=self.requirement,
            personas=personas,
            phase=phase.value
        )
        
        predicted_score = prediction['predicted_score']
        confidence = prediction['confidence']
        
        logger.info(f"Quality Decision:")
        logger.info(f"  Current Score: {quality_score:.2f}")
        logger.info(f"  Required: {required_threshold:.2f}")
        logger.info(f"  ML Predicted: {predicted_score:.2f} (confidence: {confidence:.2f})")
        
        # Accept if:
        # 1. Meets threshold, OR
        # 2. ML predicts we're close to optimal
        if quality_score >= required_threshold:
            return True
        
        if confidence > 0.7 and abs(quality_score - predicted_score) < 0.1:
            logger.info("  Accepting based on ML prediction (close to optimal)")
            return True
        
        return False
```

### 3.2 Update Team Execution to Accept ML Guidance (2 hours)

**File:** `team_execution.py`

```python
class AutonomousSDLCEngineV3_1_Resumable:
    def __init__(
        self,
        selected_personas: List[str],
        output_dir: str,
        session_manager: SessionManager,
        enable_persona_reuse: bool = True,
        force_rerun: bool = False,
        ml_client: Optional[MaestroMLClient] = None  # NEW
    ):
        # ... existing init
        
        # ML client for template reuse
        self.ml_client = ml_client
        if enable_persona_reuse and not ml_client:
            from maestro_ml_client import MaestroMLClient
            self.ml_client = MaestroMLClient()
    
    async def _execute_persona_with_reuse(
        self,
        persona_id: str,
        requirement: str
    ) -> Dict[str, Any]:
        """Execute persona with template reuse support"""
        
        if not self.ml_client:
            return await self._execute_persona_direct(persona_id, requirement)
        
        # Find similar templates
        templates = await self.ml_client.find_similar_templates(
            requirement=requirement,
            persona=persona_id,
            threshold=0.75
        )
        
        if templates:
            best_match = templates[0]
            logger.info(f"Found template match for {persona_id}:")
            logger.info(f"  Template: {best_match.template_id}")
            logger.info(f"  Similarity: {best_match.similarity_score:.2f}")
            
            # Use template as starting point
            result = await self._execute_persona_with_template(
                persona_id=persona_id,
                requirement=requirement,
                template=best_match
            )
            
            result['reused_template'] = True
            result['template_id'] = best_match.template_id
            result['similarity_score'] = best_match.similarity_score
            
            return result
        else:
            logger.info(f"No templates found for {persona_id}, executing from scratch")
            return await self._execute_persona_direct(persona_id, requirement)
    
    async def _execute_persona_with_template(
        self,
        persona_id: str,
        requirement: str,
        template: TemplateMatch
    ) -> Dict[str, Any]:
        """Execute persona using template as starting point"""
        
        # Add template context to persona prompt
        enhanced_requirement = f"""
{requirement}

TEMPLATE REFERENCE:
A similar implementation has been found with {template.similarity_score:.0%} similarity.
Use this as reference but adapt to current requirements:

{template.template_content}

END TEMPLATE REFERENCE

Please adapt the above template to meet the new requirements while maintaining quality.
"""
        
        return await self._execute_persona_direct(persona_id, enhanced_requirement)
```

### 3.3 Add Reuse Tracking and Reporting (2 hours)

**Update both files to track reuse statistics:**

```python
@dataclass
class ReuseStatistics:
    """Track template reuse and cost savings"""
    personas_executed: int
    personas_reused: int
    templates_found: int
    templates_used: int
    estimated_time_saved_hours: float
    estimated_cost_saved_usd: float

class PhasedAutonomousExecutor:
    async def execute(self, ...):
        # Track reuse stats
        self.reuse_stats = ReuseStatistics(
            personas_executed=0,
            personas_reused=0,
            templates_found=0,
            templates_used=0,
            estimated_time_saved_hours=0.0,
            estimated_cost_saved_usd=0.0
        )
        
        # ... execution logic
        
        # Report at end
        logger.info("\n" + "="*80)
        logger.info("REUSE STATISTICS")
        logger.info("="*80)
        logger.info(f"Personas Executed: {self.reuse_stats.personas_executed}")
        logger.info(f"Personas Reused: {self.reuse_stats.personas_reused}")
        logger.info(f"Templates Used: {self.reuse_stats.templates_used}/{self.reuse_stats.templates_found}")
        logger.info(f"Time Saved: {self.reuse_stats.estimated_time_saved_hours:.1f} hours")
        logger.info(f"Cost Saved: ${self.reuse_stats.estimated_cost_saved_usd:.2f}")
        logger.info("="*80)
```

---

## Phase 4: Contract Validation (Day 3, 4-6 hours)

### 4.1 Define Contract Schema in Persona JSON (1 hour)

**Update:** `maestro-engine/src/personas/definitions/backend_developer.json`

```json
{
  "persona_id": "backend_developer",
  "role": "Backend Developer",
  "deliverable_contract": {
    "required_files": [
      "src/api/**/*.py",
      "src/models/**/*.py",
      "tests/test_*.py"
    ],
    "required_directories": [
      "src/api",
      "tests"
    ],
    "required_documentation_sections": {
      "README.md": [
        "API Endpoints",
        "Database Schema",
        "Running the Application"
      ],
      "docs/API.md": [
        "Endpoints",
        "Request/Response Examples",
        "Error Handling"
      ]
    },
    "quality_thresholds": {
      "test_coverage": 0.70,
      "code_quality_score": 0.75,
      "documentation_completeness": 0.80
    },
    "validation_rules": [
      {
        "rule": "all_api_files_have_docstrings",
        "severity": "error"
      },
      {
        "rule": "all_endpoints_documented",
        "severity": "warning"
      }
    ]
  }
}
```

### 4.2 Implement Contract Validator (2 hours)

**Create:** `contract_validator.py`

```python
"""
Contract validation for persona deliverables
Ensures all required files, docs, and quality thresholds are met
"""
import re
from pathlib import Path
from typing import Dict, Any, List
from dataclasses import dataclass
import glob

@dataclass
class ContractViolation:
    """Represents a contract violation"""
    persona: str
    rule: str
    severity: str  # error, warning, info
    description: str
    expected: Any
    actual: Any

class ContractValidator:
    """Validates persona deliverables against contracts"""
    
    def __init__(self, persona_registry):
        self.persona_registry = persona_registry
    
    def validate_persona_deliverables(
        self,
        persona_id: str,
        project_dir: Path
    ) -> List[ContractViolation]:
        """Validate all deliverables for a persona"""
        
        violations = []
        persona_data = self.persona_registry.get_persona_data(persona_id)
        
        if not persona_data or 'deliverable_contract' not in persona_data:
            return violations  # No contract defined
        
        contract = persona_data['deliverable_contract']
        
        # Validate files
        violations.extend(
            self._validate_files(persona_id, project_dir, contract)
        )
        
        # Validate directories
        violations.extend(
            self._validate_directories(persona_id, project_dir, contract)
        )
        
        # Validate documentation
        violations.extend(
            self._validate_documentation(persona_id, project_dir, contract)
        )
        
        # Validate quality thresholds
        violations.extend(
            self._validate_quality(persona_id, project_dir, contract)
        )
        
        return violations
    
    def _validate_files(
        self,
        persona_id: str,
        project_dir: Path,
        contract: Dict[str, Any]
    ) -> List[ContractViolation]:
        """Validate required files exist"""
        violations = []
        
        for pattern in contract.get('required_files', []):
            matches = list(project_dir.glob(pattern))
            
            if not matches:
                violations.append(ContractViolation(
                    persona=persona_id,
                    rule='required_files',
                    severity='error',
                    description=f"Required files missing: {pattern}",
                    expected=pattern,
                    actual=None
                ))
        
        return violations
    
    def _validate_documentation(
        self,
        persona_id: str,
        project_dir: Path,
        contract: Dict[str, Any]
    ) -> List[ContractViolation]:
        """Validate documentation sections exist"""
        violations = []
        
        doc_requirements = contract.get('required_documentation_sections', {})
        
        for doc_file, required_sections in doc_requirements.items():
            doc_path = project_dir / doc_file
            
            if not doc_path.exists():
                violations.append(ContractViolation(
                    persona=persona_id,
                    rule='required_documentation',
                    severity='error',
                    description=f"Documentation file missing: {doc_file}",
                    expected=doc_file,
                    actual=None
                ))
                continue
            
            # Check for required sections
            content = doc_path.read_text()
            for section in required_sections:
                if section.lower() not in content.lower():
                    violations.append(ContractViolation(
                        persona=persona_id,
                        rule='documentation_completeness',
                        severity='warning',
                        description=f"Missing section '{section}' in {doc_file}",
                        expected=section,
                        actual=None
                    ))
        
        return violations
```

### 4.3 Integrate Contracts into Phase Gates (1-2 hours)

**Update:** `phase_gate_validator.py`

```python
from contract_validator import ContractValidator, ContractViolation

class PhaseGateValidator:
    def __init__(self):
        # ... existing init
        from maestro_ml_client import PersonaRegistry
        self.persona_registry = PersonaRegistry()
        self.contract_validator = ContractValidator(self.persona_registry)
    
    async def validate_exit_gate(
        self,
        phase: SDLCPhase,
        output_dir: Path,
        personas_executed: List[str],
        quality_score: float,
        threshold: QualityThresholds
    ) -> PhaseGateResult:
        """Validate exit gate including contracts"""
        
        # Existing validation
        result = await self._validate_deliverables(phase, output_dir)
        
        # Add contract validation
        contract_violations = []
        for persona in personas_executed:
            violations = self.contract_validator.validate_persona_deliverables(
                persona_id=persona,
                project_dir=output_dir
            )
            contract_violations.extend(violations)
        
        # Convert violations to gate issues
        for violation in contract_violations:
            if violation.severity == 'error':
                result.blocking_issues.append(
                    f"{violation.persona}: {violation.description}"
                )
            elif violation.severity == 'warning':
                result.warnings.append(
                    f"{violation.persona}: {violation.description}"
                )
        
        # Update pass status
        if contract_violations:
            error_count = len([v for v in contract_violations if v.severity == 'error'])
            if error_count > 0:
                result.passed = False
                result.score *= 0.8  # Penalty for contract violations
        
        return result
```

---

## Testing & Validation

### Integration Test

**Create:** `test_production_ready.py`

```python
"""
Integration test for production-ready workflow
Tests sunday_com remediation end-to-end
"""
import pytest
import asyncio
from pathlib import Path
from phased_autonomous_executor import PhasedAutonomousExecutor

@pytest.mark.asyncio
async def test_sunday_com_production_ready():
    """Test full production-ready workflow"""
    
    # Create executor
    executor = PhasedAutonomousExecutor(
        session_id="sunday_com_production_test",
        requirement="E-commerce platform with product management",
        output_dir=Path("test_output/sunday_com_remediated")
    )
    
    # Run validation and remediation
    result = await executor.validate_and_remediate(
        project_dir=Path("sunday_com/sunday_com")
    )
    
    # Assert success
    assert result['status'] == 'success'
    assert result['final_score'] > 0.80  # Production quality threshold
    assert result['improvement'] > 0.50  # Significant improvement
    
    # Verify ML integration worked
    assert 'reuse_stats' in result
    assert result['reuse_stats']['templates_used'] > 0  # Used templates
    
    # Verify contract validation
    assert 'contract_validation' in result
    assert len(result['contract_validation']['errors']) == 0  # No contract errors
    
    print(f"\n✅ Production Ready Test PASSED")
    print(f"   Initial Score: {result['initial_score']:.2%}")
    print(f"   Final Score: {result['final_score']:.2%}")
    print(f"   Improvement: {result['improvement']:.2%}")
    print(f"   Templates Used: {result['reuse_stats']['templates_used']}")
    print(f"   Time Saved: {result['reuse_stats']['estimated_time_saved_hours']:.1f} hours")

if __name__ == '__main__':
    asyncio.run(test_sunday_com_production_ready())
```

### Run the Test

```bash
# Set up environment
export MAESTRO_ENGINE_PATH=/home/ec2-user/projects/maestro-engine
export MAESTRO_TEMPLATES_PATH=/home/ec2-user/projects/maestro-templates/storage/templates
export ENABLE_TEMPLATE_REUSE=true
export ENABLE_QUALITY_PREDICTION=true

# Run test
python test_production_ready.py
```

---

## Deployment Checklist

### Before Starting

- [ ] Backup current code
- [ ] Create feature branch: `git checkout -b feature/production-ready-ml-integration`
- [ ] Review this action plan
- [ ] Ensure quality-fabric and maestro-templates are accessible

### Phase 1 (Day 1 Morning)

- [ ] Fix path management in maestro_ml_client.py
- [ ] Update PersonaRegistry to use dynamic persona data
- [ ] Remove hardcoded keywords and priorities
- [ ] Fix mock ML predictions
- [ ] Test with: `python -m pytest test_maestro_ml_client.py`

### Phase 2 (Day 1 Afternoon - Day 2 Morning)

- [ ] Create maestro_config.py
- [ ] Create maestro_config.yaml
- [ ] Create quality_fabric_client.py
- [ ] Update maestro_ml_client.py for API support
- [ ] Test with: `python test_api_integration.py`

### Phase 3 (Day 2 Afternoon)

- [ ] Update phased_autonomous_executor.py
- [ ] Update team_execution.py
- [ ] Add reuse tracking
- [ ] Test with: `python test_ml_integration.py`

### Phase 4 (Day 3)

- [ ] Add contract schema to persona JSON files
- [ ] Create contract_validator.py
- [ ] Integrate into phase_gate_validator.py
- [ ] Test with: `python test_contract_validation.py`

### Final Validation

- [ ] Run full integration test: `python test_production_ready.py`
- [ ] Test sunday_com remediation: `./test_sunday_com.sh`
- [ ] Verify reuse statistics are reported
- [ ] Verify contract validation works
- [ ] Check logs for any errors/warnings
- [ ] Run existing tests: `python -m pytest tests/`

### Deployment

- [ ] Merge feature branch to main
- [ ] Update documentation
- [ ] Deploy to staging environment
- [ ] Test in staging
- [ ] Deploy to production

---

## Success Criteria

### System Must:

1. ✅ Load persona data dynamically from JSON (no hardcoding)
2. ✅ Work on any machine with proper env vars (portable)
3. ✅ Support both API and filesystem modes (flexible)
4. ✅ Find and reuse templates from maestro-templates
5. ✅ Predict quality using quality-fabric (or fallback)
6. ✅ Validate deliverable contracts
7. ✅ Track and report reuse statistics
8. ✅ Improve sunday_com from 2% to 80%+ quality score

### Performance Targets:

- Template matching: < 2 seconds per persona
- Quality prediction: < 1 second
- Contract validation: < 5 seconds
- Full remediation: < 30 minutes for sunday_com

### Quality Targets:

- Test coverage: > 70%
- No hardcoded paths
- No hardcoded persona attributes
- All contracts validated
- Production quality score: > 80%

---

## Risk Mitigation

### Risk: API services not available

**Mitigation:** Graceful fallback to filesystem/rule-based modes

### Risk: Breaking existing functionality

**Mitigation:** 
- Feature flags for all new functionality
- Backward compatibility maintained
- Comprehensive tests before deployment

### Risk: Performance degradation

**Mitigation:**
- Caching at multiple levels
- Async operations throughout
- Monitoring and profiling

### Risk: Timeline slippage

**Mitigation:**
- Phased approach allows partial deployment
- Each phase delivers value independently
- Can skip Phase 4 (contracts) if needed

---

## Next Steps

**Immediate Action:** Choose one of the following:

### Option A: Start Implementation Now ⭐ RECOMMENDED
- Begin with Phase 1.1 (fix path management)
- I'll make the changes and commit incrementally
- Test after each phase
- Complete in 2-3 days

### Option B: Review & Approve First
- Review this action plan in detail
- Ask questions or request changes
- Approve before I start implementation

### Option C: Pilot with Small Change
- Implement just Phase 1.1 (4 hours)
- Verify it works and is an improvement
- Then proceed with rest of phases

---

**Ready to proceed when you are!**

**Status:** 🚀 Action Plan Complete  
**Estimated Effort:** 16-24 hours over 2-3 days  
**Confidence Level:** Very High (95%)  
**Risk Level:** Low (backward compatible, phased approach)

**Last Updated:** October 5, 2025
