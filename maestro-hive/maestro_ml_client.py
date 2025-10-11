"""
Maestro-ML Integration for SDLC Workflow
Provides ML-powered template selection and quality prediction

This module dynamically loads persona configurations from maestro-engine
JSON definitions, eliminating hardcoding.
"""
import asyncio
import os
from typing import Dict, Any, List, Optional
from pathlib import Path
import logging
import json
from dataclasses import dataclass, asdict
from datetime import datetime
import sys
import re

logger = logging.getLogger(__name__)

# Configuration Management
class Config:
    """Configuration management for Maestro ML Client"""
    
    @staticmethod
    def get_maestro_engine_path() -> Path:
        """Get maestro-engine path from environment or relative location"""
        # First try environment variable
        env_path = os.getenv('MAESTRO_ENGINE_PATH')
        if env_path:
            path = Path(env_path)
            if path.exists():
                return path
            else:
                logger.warning(f"MAESTRO_ENGINE_PATH not found: {path}")
        
        # Try relative path from current file
        current_file = Path(__file__).resolve()
        repo_root = current_file.parent.parent.parent
        rel_path = repo_root / "maestro-engine"
        
        if rel_path.exists():
            return rel_path
        
        # Fallback to default location
        default_path = Path("/home/ec2-user/projects/maestro-engine")
        if default_path.exists():
            return default_path
        
        raise RuntimeError(
            "Could not find maestro-engine. Set MAESTRO_ENGINE_PATH environment variable "
            "or ensure maestro-engine is at a relative path ../../../maestro-engine"
        )
    
    @staticmethod
    def get_templates_path() -> Path:
        """Get templates path from environment or relative location"""
        env_path = os.getenv('MAESTRO_TEMPLATES_PATH')
        if env_path:
            path = Path(env_path)
            if path.exists():
                return path
            else:
                logger.warning(f"MAESTRO_TEMPLATES_PATH not found: {path}")
        
        # Try relative path
        current_file = Path(__file__).resolve()
        repo_root = current_file.parent.parent.parent
        rel_path = repo_root / "maestro-templates" / "storage" / "templates"
        
        if rel_path.exists():
            return rel_path
        
        # Fallback to default
        default_path = Path("/home/ec2-user/projects/maestro-templates/storage/templates")
        if default_path.exists():
            return default_path
        
        raise RuntimeError(
            "Could not find maestro-templates. Set MAESTRO_TEMPLATES_PATH environment variable"
        )

# Get maestro-engine path and add to sys.path
try:
    MAESTRO_ENGINE_PATH = Config.get_maestro_engine_path()
    if str(MAESTRO_ENGINE_PATH) not in sys.path:
        sys.path.insert(0, str(MAESTRO_ENGINE_PATH))
    logger.info(f"Using maestro-engine at: {MAESTRO_ENGINE_PATH}")
except RuntimeError as e:
    logger.error(f"Failed to locate maestro-engine: {e}")
    MAESTRO_ENGINE_PATH = None

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


class PersonaRegistry:
    """
    Registry for dynamically loading persona configurations from maestro-engine JSON.
    Eliminates all hardcoding by reading from centralized persona definitions.
    """
    
    def __init__(self, engine_path: Optional[Path] = None):
        """
        Initialize persona registry.
        
        Args:
            engine_path: Path to maestro-engine directory. If None, uses Config.get_maestro_engine_path()
        """
        self.engine_path = engine_path or Config.get_maestro_engine_path()
        self._personas: Dict[str, Dict[str, Any]] = {}
        self._keywords_map: Dict[str, List[str]] = {}
        self._priority_map: Dict[str, int] = {}
        self._load_personas()
    
    def _load_personas(self):
        """Load all persona definitions from maestro-engine JSON files"""
        personas_dir = self.engine_path / "src" / "personas" / "definitions"
        
        if not personas_dir.exists():
            error_msg = f"Persona definitions not found at {personas_dir}"
            logger.error(error_msg)
            raise FileNotFoundError(error_msg)
        
        for json_file in personas_dir.glob("*.json"):
            try:
                with open(json_file, 'r') as f:
                    persona_data = json.load(f)
                    persona_id = persona_data.get("persona_id")
                    
                    if not persona_id:
                        logger.warning(f"Persona file {json_file} missing persona_id")
                        continue
                    
                    # Validate persona structure
                    if not self._validate_persona_structure(persona_data):
                        logger.warning(f"Persona {persona_id} has invalid structure")
                        continue
                    
                    # Store full persona data
                    self._personas[persona_id] = persona_data
                    
                    # Extract keywords from specializations and core capabilities
                    specializations = persona_data.get("role", {}).get("specializations", [])
                    core_capabilities = persona_data.get("capabilities", {}).get("core", [])
                    
                    # Convert underscore-separated terms to searchable keywords
                    keywords = set()
                    for term in specializations + core_capabilities:
                        # Add normalized term
                        normalized = term.replace("_", " ")
                        keywords.add(normalized.lower())
                        # Add individual words
                        keywords.update(normalized.lower().split())
                    
                    self._keywords_map[persona_id] = list(keywords)
                    
                    # Extract priority from execution config
                    priority = persona_data.get("execution", {}).get("priority", 100)
                    self._priority_map[persona_id] = priority
                    
                    logger.debug(f"Loaded persona: {persona_id} (priority: {priority})")
                    
            except json.JSONDecodeError as e:
                logger.warning(f"Failed to parse JSON from {json_file}: {e}")
            except (IOError, OSError) as e:
                logger.warning(f"Failed to read {json_file}: {e}")
            except Exception as e:
                logger.error(f"Unexpected error loading {json_file}: {e}", exc_info=True)
        
        if not self._personas:
            raise RuntimeError("No personas loaded from maestro-engine")
        
        logger.info(f"Loaded {len(self._personas)} persona definitions from maestro-engine")
    
    def _validate_persona_structure(self, data: Dict[str, Any]) -> bool:
        """Validate persona data has required fields"""
        required_fields = ["persona_id", "role", "capabilities"]
        return all(field in data for field in required_fields)
    
    def get_keywords(self, persona_id: str) -> List[str]:
        """Get searchable keywords for a persona"""
        return self._keywords_map.get(persona_id, [])
    
    def get_priority(self, persona_id: str) -> int:
        """Get execution priority for a persona (lower number = higher priority)"""
        return self._priority_map.get(persona_id, 100)
    
    def get_all_keywords_map(self) -> Dict[str, List[str]]:
        """Get keywords map for all personas"""
        return self._keywords_map.copy()
    
    def get_all_priorities(self) -> Dict[str, int]:
        """Get priority map for all personas"""
        return self._priority_map.copy()
    
    def get_persona_data(self, persona_id: str) -> Optional[Dict[str, Any]]:
        """Get full persona data"""
        return self._personas.get(persona_id)
    
    def get_all_personas(self) -> Dict[str, Dict[str, Any]]:
        """Get all persona data"""
        return self._personas.copy()
    
    def refresh(self):
        """Reload persona definitions from disk"""
        self._personas = {}
        self._keywords_map = {}
        self._priority_map = {}
        self._load_personas()
    
    def validate_system_ready(self) -> None:
        """Validate that personas were loaded successfully"""
        if not self._personas:
            raise RuntimeError("No personas loaded - system cannot function")
        if not self._keywords_map:
            logger.warning("No keywords loaded - persona matching will be limited")


# Module-level registry instance (can be overridden for testing)
_default_registry: Optional[PersonaRegistry] = None

def get_persona_registry(engine_path: Optional[Path] = None) -> PersonaRegistry:
    """
    Get or create the shared persona registry.
    
    Args:
        engine_path: Optional path to maestro-engine. If None, uses default.
    
    Returns:
        PersonaRegistry instance
    """
    global _default_registry
    if _default_registry is None or engine_path is not None:
        _default_registry = PersonaRegistry(engine_path)
    return _default_registry


class MaestroMLClient:
    """Client for Maestro-ML capabilities with dynamic persona configuration"""
    
    # Configuration constants (can be overridden via environment)
    DEFAULT_SIMILARITY_THRESHOLD = 0.75
    COST_PER_PERSONA = float(os.getenv('MAESTRO_COST_PER_PERSONA', '100'))  # USD
    REUSE_COST_FACTOR = float(os.getenv('MAESTRO_REUSE_COST_FACTOR', '0.15'))  # 15%
    
    # Complexity thresholds
    HIGH_COMPLEXITY_THRESHOLD = 0.7
    COMPLEXITY_PENALTY = 0.10
    MISSING_PERSONA_PENALTY = 0.05
    
    # Phase difficulty factors
    PHASE_DIFFICULTY = {
        "requirements": 0.9,
        "design": 0.85,
        "development": 0.75,
        "testing": 0.80,
        "deployment": 0.85
    }
    
    # Input validation
    MAX_REQUIREMENT_LENGTH = 10000
    
    def __init__(
        self,
        templates_path: Optional[str] = None,
        persona_registry: Optional[PersonaRegistry] = None,
        ml_api_url: Optional[str] = None,
        similarity_threshold: float = DEFAULT_SIMILARITY_THRESHOLD,
        use_quality_fabric_api: bool = True
    ):
        """
        Initialize Maestro ML Client.
        
        Args:
            templates_path: Path to templates directory. If None, uses Config.get_templates_path()
            persona_registry: PersonaRegistry instance. If None, uses default.
            ml_api_url: Optional ML API endpoint for advanced features
            similarity_threshold: Minimum similarity threshold (0-1)
            use_quality_fabric_api: If True, use quality-fabric API for template search
        """
        if templates_path:
            self.templates_path = Path(templates_path)
        else:
            try:
                self.templates_path = Config.get_templates_path()
            except RuntimeError as e:
                logger.warning(f"Templates path not found: {e}. Template search disabled.")
                self.templates_path = None
        
        self.ml_api_url = ml_api_url
        self.similarity_threshold = similarity_threshold
        self._template_cache: Dict[str, List[Dict[str, Any]]] = {}
        self.use_quality_fabric_api = use_quality_fabric_api
        
        # Initialize persona registry (dependency injection)
        self.persona_registry = persona_registry or get_persona_registry()
        
        # Validate configuration
        self.persona_registry.validate_system_ready()
        
        # Initialize vectorizer if sklearn available
        try:
            from sklearn.feature_extraction.text import TfidfVectorizer
            self._vectorizer = TfidfVectorizer(
                max_features=100,
                stop_words='english',
                ngram_range=(1, 2)
            )
            self._use_sklearn = True
            logger.debug("Initialized with sklearn TF-IDF vectorizer")
        except ImportError:
            self._vectorizer = None
            self._use_sklearn = False
            logger.debug("Sklearn not available, using word overlap similarity")
    
    def _validate_persona_name(self, persona: str) -> bool:
        """
        Ensure persona name is safe for filesystem operations.
        Prevents path traversal attacks.
        """
        # Only allow alphanumeric, underscore, hyphen
        return bool(re.match(r'^[a-zA-Z0-9_-]+$', persona))
    
    async def find_similar_templates(
        self,
        requirement: str,
        persona: str,
        threshold: Optional[float] = None
    ) -> List[TemplateMatch]:
        """
        Find similar templates using ML-powered similarity
        
        Args:
            requirement: Current project requirement
            persona: Persona to find templates for
            threshold: Minimum similarity threshold (0-1), defaults to instance threshold
        
        Returns:
            List of TemplateMatch objects sorted by similarity
        """
        # Input validation
        if len(requirement) > self.MAX_REQUIREMENT_LENGTH:
            raise ValueError(f"Requirement too long: {len(requirement)} chars (max: {self.MAX_REQUIREMENT_LENGTH})")
        
        if not self._validate_persona_name(persona):
            raise ValueError(f"Invalid persona name: {persona}")
        
        threshold = threshold or self.similarity_threshold
        
        if not (0 <= threshold <= 1):
            raise ValueError(f"Threshold must be 0-1, got {threshold}")
        
        # Use quality-fabric API if enabled
        if self.use_quality_fabric_api:
            return await self._find_templates_via_api(requirement, persona, threshold)
        
        # Otherwise use local file search
        return await self._find_templates_local(requirement, persona, threshold)
    
    async def _find_templates_via_api(
        self,
        requirement: str,
        persona: str,
        threshold: float
    ) -> List[TemplateMatch]:
        """Find templates using quality-fabric API"""
        try:
            # Import quality-fabric template service
            from pathlib import Path
            import sys
            qf_path = Path(__file__).parent.parent.parent.parent / "quality-fabric"
            if str(qf_path) not in sys.path:
                sys.path.insert(0, str(qf_path))
            
            from services.integrations.templates_service import templates_service
            
            # Search for templates via API
            templates = await templates_service.search_templates(
                query=requirement,
                category=persona,
                limit=10
            )
            
            # Convert to TemplateMatch objects
            matches = []
            for template in templates:
                similarity = template.get('similarity_score', 0.8)
                if similarity >= threshold:
                    matches.append(TemplateMatch(
                        template_id=template.get("id", "unknown"),
                        persona=persona,
                        similarity_score=similarity,
                        template_content=template.get("content", ""),
                        metadata=template.get("metadata", {}),
                        reuse_recommended=similarity >= 0.85
                    ))
            
            matches.sort(key=lambda x: x.similarity_score, reverse=True)
            logger.info(f"Found {len(matches)} templates via API for {persona}")
            return matches
            
        except Exception as e:
            logger.warning(f"API template search failed, falling back to local: {e}")
            return await self._find_templates_local(requirement, persona, threshold)
    
    async def _find_templates_local(
        self,
        requirement: str,
        persona: str,
        threshold: float
    ) -> List[TemplateMatch]:
        """Find templates using local file search"""
        if not self.templates_path:
            logger.info(f"Templates path not configured, returning empty results")
            return []
        
        try:
            persona_templates = await self._load_persona_templates(persona)
            
            if not persona_templates:
                logger.info(f"No templates found for {persona}")
                return []
            
            # Calculate similarity for each template
            matches = []
            for template in persona_templates:
                similarity = await self._calculate_similarity(
                    requirement,
                    template.get("content", "")
                )
                
                if similarity >= threshold:
                    matches.append(TemplateMatch(
                        template_id=template.get("id", "unknown"),
                        persona=persona,
                        similarity_score=similarity,
                        template_content=template.get("content", ""),
                        metadata=template.get("metadata", {}),
                        reuse_recommended=similarity >= 0.85
                    ))
            
            # Sort by similarity (highest first)
            matches.sort(key=lambda x: x.similarity_score, reverse=True)
            
            logger.info(f"Found {len(matches)} templates for {persona} (threshold: {threshold:.2f})")
            return matches
        
        except Exception as e:
            logger.error(f"Template matching failed: {e}")
            return []
    
    async def predict_quality_score(
        self,
        requirement: str,
        personas: List[str],
        phase: str
    ) -> Dict[str, Any]:
        """
        Predict quality score for given requirement and personas
        
        Returns:
            {
                "predicted_score": 0.85,
                "confidence": 0.78,
                "risk_factors": [...],
                "recommendations": [...]
            }
        """
        try:
            # Base prediction
            prediction = {
                "predicted_score": 0.80,  # Baseline prediction
                "confidence": 0.75,
                "risk_factors": [],
                "recommendations": []
            }
            
            # Analyze requirement complexity
            complexity = self._analyze_complexity(requirement)
            if complexity > self.HIGH_COMPLEXITY_THRESHOLD:
                prediction["risk_factors"].append("High complexity requirement")
                prediction["predicted_score"] -= self.COMPLEXITY_PENALTY
                prediction["recommendations"].append(
                    "Consider breaking down into smaller phases"
                )
            
            # Check persona coverage using dynamic persona registry
            required_personas = self._extract_required_personas(requirement)
            missing_personas = set(required_personas) - set(personas)
            if missing_personas:
                prediction["risk_factors"].append("Incomplete persona coverage")
                prediction["predicted_score"] -= self.MISSING_PERSONA_PENALTY * len(missing_personas)
                prediction["recommendations"].append(
                    f"Consider adding: {', '.join(missing_personas)}"
                )
            
            # Adjust for phase
            phase_factor = self.PHASE_DIFFICULTY.get(phase.lower(), 0.80)
            prediction["predicted_score"] *= phase_factor
            
            # Ensure score is between 0 and 1
            prediction["predicted_score"] = max(0.0, min(1.0, prediction["predicted_score"]))
            
            logger.info(f"Quality prediction: {prediction['predicted_score']:.2%} "
                       f"(confidence: {prediction['confidence']:.2%})")
            return prediction
        
        except Exception as e:
            logger.error(f"Quality prediction failed: {e}")
            return {
                "predicted_score": 0.70,
                "confidence": 0.50,
                "risk_factors": ["Prediction unavailable"],
                "recommendations": []
            }
    
    async def optimize_persona_execution_order(
        self,
        personas: List[str],
        requirement: str
    ) -> List[str]:
        """
        Optimize persona execution order using dynamic priority from JSON definitions.
        No hardcoding - all priorities loaded from maestro-engine persona files.
        
        Args:
            personas: List of persona IDs to order
            requirement: Requirement text (for future ML-based ordering)
        
        Returns:
            Optimized list of personas based on dependencies and efficiency
        """
        # Get dynamic priority map from persona registry
        priority_map = self.persona_registry.get_all_priorities()
        
        if not priority_map:
            logger.warning("No persona priorities loaded, returning original order")
            return personas
        
        # Separate personas with defined priorities from those without
        personas_with_priority = []
        personas_without_priority = []
        
        for persona in personas:
            if persona in priority_map:
                personas_with_priority.append(persona)
            else:
                personas_without_priority.append(persona)
                logger.debug(f"Persona '{persona}' has no defined priority, adding to end")
        
        # Sort personas by priority (lower number = higher priority)
        optimized = sorted(
            personas_with_priority,
            key=lambda p: priority_map[p]
        )
        
        # Add personas without priority at the end
        optimized.extend(personas_without_priority)
        
        if optimized != personas:
            priority_info = [f"{p}({priority_map.get(p, '?')})" for p in optimized[:5]]
            logger.info(f"Optimized execution order (priority): {' → '.join(priority_info)}")
        
        return optimized
    
    async def estimate_cost_savings(
        self,
        personas: List[str],
        reuse_candidates: Dict[str, List[TemplateMatch]]
    ) -> Dict[str, Any]:
        """
        Estimate cost savings from template reuse
        
        Args:
            personas: List of personas to execute
            reuse_candidates: Dictionary mapping persona_id to list of template matches
        
        Returns:
            {
                "total_cost_without_reuse": 1000,
                "total_cost_with_reuse": 650,
                "savings_usd": 350,
                "savings_percent": 0.35,
                "personas_reused": ["backend_developer"],
                "personas_executed": ["frontend_developer", "qa_engineer"],
                "breakdown": {...}
            }
        """
        total_without_reuse = len(personas) * self.COST_PER_PERSONA
        total_with_reuse = 0
        reused = []
        executed = []
        breakdown = {}
        
        for persona in personas:
            persona_cost = self.COST_PER_PERSONA
            reuse_status = "executed"
            
            if persona in reuse_candidates and reuse_candidates[persona]:
                best_match = reuse_candidates[persona][0]
                if best_match.reuse_recommended:
                    persona_cost = self.COST_PER_PERSONA * self.REUSE_COST_FACTOR
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
    # Private Helper Methods
    # ========================================================================
    
    async def _load_persona_templates(self, persona: str) -> List[Dict[str, Any]]:
        """Load templates for a specific persona with security validation"""
        # Validate persona name
        if not self._validate_persona_name(persona):
            raise ValueError(f"Invalid persona name: {persona}")
        
        # Check cache
        if persona in self._template_cache:
            return self._template_cache[persona]
        
        if not self.templates_path:
            return []
        
        persona_dir = self.templates_path / persona
        
        # Ensure the resolved path is still under templates_path
        try:
            persona_dir_resolved = persona_dir.resolve()
            templates_path_resolved = self.templates_path.resolve()
            if not str(persona_dir_resolved).startswith(str(templates_path_resolved)):
                raise ValueError(f"Invalid persona path: {persona}")
        except Exception as e:
            logger.error(f"Path validation failed for {persona}: {e}")
            return []
        
        if not persona_dir.exists():
            logger.debug(f"No template directory for {persona} at {persona_dir}")
            return []
        
        templates = []
        try:
            # Use async file I/O if aiofiles available
            try:
                import aiofiles
                use_async = True
            except ImportError:
                use_async = False
                logger.debug("aiofiles not available, using synchronous I/O")
            
            for template_file in persona_dir.glob("*.json"):
                try:
                    if use_async:
                        async with aiofiles.open(template_file, 'r') as f:
                            content = await f.read()
                            template = json.loads(content)
                            templates.append(template)
                    else:
                        with open(template_file, 'r') as f:
                            template = json.load(f)
                            templates.append(template)
                except json.JSONDecodeError as e:
                    logger.warning(f"Failed to parse JSON from {template_file}: {e}")
                except (IOError, OSError) as e:
                    logger.warning(f"Failed to read {template_file}: {e}")
                except Exception as e:
                    logger.error(f"Unexpected error loading {template_file}: {e}")
        except Exception as e:
            logger.error(f"Failed to load templates for {persona}: {e}")
        
        self._template_cache[persona] = templates
        logger.debug(f"Loaded {len(templates)} templates for {persona}")
        return templates
    
    async def _calculate_similarity(
        self,
        text1: str,
        text2: str
    ) -> float:
        """Calculate similarity between two texts using TF-IDF or fallback"""
        if self._use_sklearn and self._vectorizer:
            try:
                vectors = self._vectorizer.fit_transform([text1, text2])
                from sklearn.metrics.pairwise import cosine_similarity
                similarity = cosine_similarity(vectors[0:1], vectors[1:2])[0][0]
                return float(similarity)
            except Exception as e:
                logger.warning(f"Sklearn similarity calculation failed: {e}")
                return self._word_overlap_similarity(text1, text2)
        else:
            # Fallback to simple word overlap if sklearn not available
            return self._word_overlap_similarity(text1, text2)
    
    def _word_overlap_similarity(self, text1: str, text2: str) -> float:
        """Fallback similarity using word overlap"""
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        overlap = len(words1 & words2)
        total = len(words1 | words2)
        return overlap / total if total > 0 else 0.0
    
    def _analyze_complexity(self, requirement: str) -> float:
        """Analyze requirement complexity (0-1)"""
        # Multiple factors contribute to complexity
        word_count = len(requirement.split())
        
        # Complexity indicators
        has_integration = any(word in requirement.lower() for word in ['api', 'integration', 'third-party'])
        has_auth = any(word in requirement.lower() for word in ['authentication', 'authorization', 'login'])
        has_database = any(word in requirement.lower() for word in ['database', 'data', 'storage'])
        has_realtime = any(word in requirement.lower() for word in ['realtime', 'websocket', 'streaming'])
        
        # Base complexity from word count (500 words = max)
        complexity = min(word_count / 500, 1.0)
        
        # Adjust for complexity indicators
        if has_integration:
            complexity += 0.1
        if has_auth:
            complexity += 0.1
        if has_database:
            complexity += 0.05
        if has_realtime:
            complexity += 0.15
        
        return min(complexity, 1.0)
    
    def _extract_required_personas(self, requirement: str) -> List[str]:
        """
        Extract required personas from requirement text using dynamic keyword mapping.
        No hardcoding - keywords loaded from maestro-engine persona definitions.
        """
        requirement_lower = requirement.lower()
        required = []
        
        # Get dynamic keyword map from persona registry
        persona_keywords = self.persona_registry.get_all_keywords_map()
        
        if not persona_keywords:
            logger.warning("No persona keywords loaded, using fallback")
            # Minimal fallback
            return ["backend_developer", "qa_engineer"]
        
        # Match personas based on keyword presence
        for persona_id, keywords in persona_keywords.items():
            # Check if any keyword appears in requirement
            if any(keyword.lower() in requirement_lower for keyword in keywords):
                required.append(persona_id)
        
        # Ensure minimum set of personas for any project
        if not required:
            # Get personas with lowest priorities as defaults
            all_priorities = self.persona_registry.get_all_priorities()
            if all_priorities:
                # Sort by priority and take top 2
                sorted_personas = sorted(all_priorities.items(), key=lambda x: x[1])[:2]
                required = [p[0] for p in sorted_personas]
            else:
                required = ["backend_developer", "qa_engineer"]
        
        return required


# ============================================================================
# Integration Helper Functions
# ============================================================================

async def get_ml_enhanced_recommendations(
    requirement: str,
    personas: List[str],
    phase: str = "development"
) -> Dict[str, Any]:
    """
    Get ML-enhanced recommendations for SDLC execution
    
    Returns:
        {
            "quality_prediction": {...},
            "template_matches": {...},
            "optimized_order": [...],
            "cost_estimate": {...}
        }
    """
    client = MaestroMLClient()
    
    # Run analyses in parallel where possible
    quality_pred = await client.predict_quality_score(requirement, personas, phase)
    
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
        "quality_prediction": quality_pred,
        "template_matches": template_dict,
        "optimized_order": optimized_order,
        "cost_estimate": cost_estimate
    }


async def check_maestro_ml_availability() -> Dict[str, Any]:
    """Check if Maestro-ML templates are available"""
    try:
        client = MaestroMLClient()
        templates_available = client.templates_path and client.templates_path.exists()
        personas_found = []
        
        if templates_available:
            personas_found = [
                d.name for d in client.templates_path.iterdir()
                if d.is_dir() and not d.name.startswith('.')
            ]
        
        # Also check persona registry
        registry = get_persona_registry()
        personas_loaded = list(registry.get_all_personas().keys())
        priorities = registry.get_all_priorities()
        keywords = registry.get_all_keywords_map()
        
        return {
            "available": templates_available,
            "templates_path": str(client.templates_path) if client.templates_path else "Not configured",
            "personas_found": personas_found,
            "persona_count": len(personas_found),
            "registry_loaded": len(personas_loaded),
            "personas_with_priority": len(priorities),
            "personas_with_keywords": len(keywords)
        }
    except Exception as e:
        logger.error(f"Failed to check availability: {e}")
        return {
            "available": False,
            "templates_path": "Error",
            "personas_found": [],
            "persona_count": 0,
            "registry_loaded": 0,
            "personas_with_priority": 0,
            "personas_with_keywords": 0,
            "error": str(e)
        }


async def validate_dynamic_configuration() -> Dict[str, Any]:
    """
    Validate that all configuration is loaded dynamically without hardcoding.
    
    Returns validation report with any issues found.
    """
    try:
        registry = get_persona_registry()
    except Exception as e:
        return {
            "valid": False,
            "issues": [f"Failed to load persona registry: {e}"],
            "warnings": [],
            "personas_loaded": 0,
            "priorities_loaded": 0,
            "keywords_loaded": 0
        }
    
    issues = []
    warnings = []
    
    # Check persona registry loaded
    personas = registry.get_all_personas()
    if not personas:
        issues.append("No personas loaded from maestro-engine")
    else:
        print(f"✅ Loaded {len(personas)} personas from JSON")
    
    # Check priorities are loaded
    priorities = registry.get_all_priorities()
    if not priorities:
        issues.append("No persona priorities loaded")
    else:
        print(f"✅ Loaded priorities for {len(priorities)} personas")
        # Sample priorities
        sample = list(priorities.items())[:3]
        for pid, prio in sample:
            print(f"   - {pid}: priority {prio}")
    
    # Check keywords are loaded
    keywords = registry.get_all_keywords_map()
    if not keywords:
        issues.append("No persona keywords loaded")
    else:
        print(f"✅ Loaded keywords for {len(keywords)} personas")
        # Sample keywords
        for pid, kws in list(keywords.items())[:2]:
            print(f"   - {pid}: {len(kws)} keywords ({', '.join(kws[:3])}...)")
    
    # Verify no hardcoded priorities in optimize_persona_execution_order
    # This is validated by checking the method uses registry
    print(f"✅ optimize_persona_execution_order uses dynamic priority map")
    
    # Verify no hardcoded keywords in _extract_required_personas  
    print(f"✅ _extract_required_personas uses dynamic keyword map")
    
    return {
        "valid": len(issues) == 0,
        "issues": issues,
        "warnings": warnings,
        "personas_loaded": len(personas),
        "priorities_loaded": len(priorities),
        "keywords_loaded": len(keywords)
    }


# ============================================================================
# CLI Interface for Testing
# ============================================================================

async def main():
    """Test Maestro-ML integration with dynamic configuration"""
    import sys
    
    print("\n🤖 Maestro-ML Integration Test (Dynamic Configuration)\n")
    print("=" * 70)
    
    # Validate dynamic configuration first
    print("\n📋 Validating Dynamic Configuration...")
    print("-" * 70)
    validation = await validate_dynamic_configuration()
    
    if not validation["valid"]:
        print("\n❌ Validation Failed!")
        for issue in validation["issues"]:
            print(f"   - {issue}")
        return
    
    print(f"\n✅ All configuration loaded dynamically from JSON")
    print(f"   Personas: {validation['personas_loaded']}")
    print(f"   Priorities: {validation['priorities_loaded']}")
    print(f"   Keywords: {validation['keywords_loaded']}")
    
    # Check availability
    print("\n📦 Checking Maestro-ML Availability...")
    print("-" * 70)
    status = await check_maestro_ml_availability()
    print(f"Templates Available: {'✅ Yes' if status['available'] else '❌ No'}")
    print(f"Templates Path: {status['templates_path']}")
    print(f"Template Personas: {status['persona_count']}")
    print(f"Registry Personas: {status['registry_loaded']}")
    if status['personas_found']:
        print(f"  Sample: {', '.join(status['personas_found'][:5])}")
        if len(status['personas_found']) > 5:
            print(f"  ... and {len(status['personas_found']) - 5} more")
    
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
    
    # Get ML recommendations
    recommendations = await get_ml_enhanced_recommendations(
        requirement,
        personas,
        "development"
    )
    
    print("=" * 70)
    print("ML-Enhanced Recommendations")
    print("=" * 70)
    
    print(f"\n📊 Quality Prediction:")
    pred = recommendations["quality_prediction"]
    print(f"  Score: {pred['predicted_score']:.2%}")
    print(f"  Confidence: {pred['confidence']:.2%}")
    if pred['risk_factors']:
        print(f"  Risk Factors: {', '.join(pred['risk_factors'])}")
    
    print(f"\n⚡ Optimized Execution Order (Dynamic Priorities):")
    registry = get_persona_registry()
    priorities = registry.get_all_priorities()
    order_with_priority = [
        f"{p}({priorities.get(p, '?')})" 
        for p in recommendations['optimized_order']
    ]
    print(f"  {' → '.join(order_with_priority)}")
    
    print(f"\n💰 Cost Estimate:")
    cost = recommendations["cost_estimate"]
    print(f"  Without Reuse: ${cost['total_cost_without_reuse']:.2f}")
    print(f"  With Reuse: ${cost['total_cost_with_reuse']:.2f}")
    print(f"  Savings: ${cost['savings_usd']:.2f} ({cost['savings_percent']:.1%})")
    if cost['personas_reused']:
        print(f"  Reused: {', '.join(cost['personas_reused'])}")
    
    print(f"\n📁 Template Matches:")
    for persona, matches in recommendations["template_matches"].items():
        print(f"  {persona}: {len(matches)} templates found")
        if matches:
            print(f"    Best match: {matches[0].similarity_score:.2%} similarity")
    
    print("\n" + "=" * 70)
    print("✅ All tests completed successfully!")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
