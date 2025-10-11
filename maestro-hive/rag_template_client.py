#!/usr/bin/env python3
"""
RAG Template Client - Retrieval-Augmented Generation for Template Library

This module provides a client for accessing the maestro-templates registry
and performing intelligent template retrieval for team execution workflows.

Features:
- Search templates by persona, language, framework, category
- Calculate relevance scores (metadata matching + semantic similarity)
- Get recommended template packages from recommendation engine
- Local caching for performance
- Graceful degradation when API unavailable

Architecture:
    TeamExecutionEngine
          ↓
    TemplateRAGClient (this module)
          ↓
    Template Registry API (:9600)
          ↓
    Template Library (maestro-templates)

Usage:
    client = TemplateRAGClient()

    # Project-level: Get recommended package
    package = await client.get_recommended_package(requirement)

    # Persona-level: Get relevant templates
    templates = await client.search_templates_for_persona(
        persona_id="backend_developer",
        requirement="Build REST API",
        context={}
    )
"""

import asyncio
import aiohttp
import json
import logging
import os
from pathlib import Path
from typing import List, Dict, Any, Optional, Set
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
import hashlib
from urllib.parse import urlencode

# Import configuration
try:
    from config import RAG_CONFIG
    CONFIG_AVAILABLE = True
except ImportError:
    # Default configuration if config.py not available
    RAG_CONFIG = {
        "registry_base_url": "http://localhost:9600",
        "templates_base_path": "/home/ec2-user/projects/maestro-platform/maestro-templates/storage/templates",
        "enable_cache": True,
        "cache_ttl_hours": 24,
        "cache_dir": "/tmp/maestro_rag_cache",
        "high_relevance_threshold": 0.80,
        "medium_relevance_threshold": 0.60,
        "max_templates_to_show": 5,
        "max_templates_to_search": 20,
        "keyword_weight": 0.30,
        "tag_weight": 0.20,
        "quality_weight": 0.20,
        "tech_stack_weight": 0.20,
        "usage_stats_weight": 0.10,
    }
    CONFIG_AVAILABLE = False
    logging.warning("config.py not found, using default RAG configuration")

logger = logging.getLogger(__name__)


# =============================================================================
# DATA MODELS
# =============================================================================

@dataclass
class TemplateMetadata:
    """Template metadata from registry"""
    id: str
    name: str
    description: str
    category: str
    language: str
    framework: str
    version: str
    tags: List[str]
    persona: str

    # Quality scores
    quality_score: float
    security_score: float
    performance_score: float
    maintainability_score: float
    test_coverage: float

    # Usage stats
    usage_count: int = 0
    success_rate: float = 0.0

    # Status
    status: str = "approved"
    is_pinned: bool = False
    quality_tier: Optional[str] = None

    # Timestamps
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


@dataclass
class TemplateContent:
    """Template with full content"""
    metadata: TemplateMetadata
    content: str  # Source code
    variables: Dict[str, Any]
    dependencies: List[str]
    workflow_context: Dict[str, Any]

    # RAG-specific
    relevance_score: float = 0.0  # Calculated relevance to requirement
    selection_reasoning: str = ""  # Why this template was selected


@dataclass
class TemplateRecommendation:
    """Single template recommendation"""
    template_id: str
    template_name: str
    persona: str
    reason: str
    priority: str  # "required", "recommended", "optional"
    quality_score: float
    is_substitute: bool = False
    original_template_id: Optional[str] = None


@dataclass
class PackageRecommendation:
    """Complete package recommendation from recommendation engine"""
    requirement_text: str
    recommendation_type: str  # "exact_match", "near_match_with_substitution", "partial_match", "custom"
    confidence: float
    best_match_package_id: Optional[str]
    best_match_package_name: Optional[str]
    recommended_templates: List[TemplateRecommendation]
    explanation: str
    warnings: List[str]
    estimated_setup_time_hours: str


# =============================================================================
# RAG TEMPLATE CLIENT
# =============================================================================

class TemplateRAGClient:
    """
    Client for accessing template library with RAG capabilities.

    Provides:
    - Template search and retrieval
    - Relevance scoring
    - Package recommendations
    - Local caching
    - Fallback strategies
    """

    def __init__(
        self,
        registry_url: Optional[str] = None,
        api_key: Optional[str] = None,
        cache_dir: Optional[str] = None,
        cache_ttl_hours: Optional[int] = None,
        enable_cache: Optional[bool] = None,
        max_templates_per_persona: Optional[int] = None,
        relevance_threshold_use: Optional[float] = None,
        relevance_threshold_custom: Optional[float] = None,
        templates_base_path: Optional[str] = None
    ):
        # Use config values as defaults
        self.registry_url = (registry_url or f"{RAG_CONFIG['registry_base_url']}/api/v1/templates").rstrip('/')
        self.api_key = api_key or os.getenv("TEMPLATE_REGISTRY_API_KEY", "")
        self.templates_base_path = Path(templates_base_path or RAG_CONFIG['templates_base_path'])

        # Caching
        self.enable_cache = enable_cache if enable_cache is not None else RAG_CONFIG['enable_cache']
        self.cache_ttl = timedelta(hours=cache_ttl_hours or RAG_CONFIG['cache_ttl_hours'])
        self.cache_dir = Path(cache_dir or RAG_CONFIG['cache_dir'])
        if self.enable_cache:
            self.cache_dir.mkdir(parents=True, exist_ok=True)

        # Configuration from RAG_CONFIG
        self.max_templates_per_persona = max_templates_per_persona or RAG_CONFIG['max_templates_to_show']
        self.relevance_threshold_use = relevance_threshold_use or RAG_CONFIG['high_relevance_threshold']
        self.relevance_threshold_custom = relevance_threshold_custom or RAG_CONFIG['medium_relevance_threshold']

        # Scoring weights from config
        self.keyword_weight = RAG_CONFIG['keyword_weight']
        self.tag_weight = RAG_CONFIG['tag_weight']
        self.quality_weight = RAG_CONFIG['quality_weight']
        self.tech_stack_weight = RAG_CONFIG['tech_stack_weight']
        self.usage_stats_weight = RAG_CONFIG['usage_stats_weight']

        # State
        self.session: Optional[aiohttp.ClientSession] = None
        self._template_cache: Dict[str, TemplateContent] = {}

        logger.info("✅ TemplateRAGClient initialized")
        logger.info(f"   Registry: {self.registry_url}")
        logger.info(f"   Templates: {self.templates_base_path}")
        logger.info(f"   Cache: {'enabled' if self.enable_cache else 'disabled'} ({self.cache_dir})")
        logger.info(f"   Thresholds: use={self.relevance_threshold_use:.0%}, custom={self.relevance_threshold_custom:.0%}")

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create HTTP session"""
        if self.session is None or self.session.closed:
            headers = {}
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"
            self.session = aiohttp.ClientSession(headers=headers)
        return self.session

    async def close(self):
        """Close HTTP session"""
        if self.session and not self.session.closed:
            await self.session.close()

    # =========================================================================
    # PERSONA-LEVEL RAG
    # =========================================================================

    async def search_templates_for_persona(
        self,
        persona_id: str,
        requirement: str,
        context: Optional[Dict[str, Any]] = None,
        language: Optional[str] = None,
        framework: Optional[str] = None
    ) -> List[TemplateContent]:
        """
        Search for relevant templates for a specific persona.

        Args:
            persona_id: Persona identifier (e.g., "backend_developer")
            requirement: Natural language requirement
            context: Additional context (tech stack, constraints, etc.)
            language: Filter by language
            framework: Filter by framework

        Returns:
            List of templates sorted by relevance (highest first)
        """
        logger.info(f"🔍 Searching templates for persona: {persona_id}")

        context = context or {}

        # Extract filters from context
        if not language and context.get("language"):
            language = context["language"]
        if not framework and context.get("framework"):
            framework = context["framework"]

        try:
            # Search registry API
            params = {
                "page": 1,
                "page_size": 20,  # Get more for better relevance filtering
            }

            # Filter by persona if template registry supports it
            # Note: Current API doesn't have persona filter, so we filter post-fetch

            if language:
                params["language"] = language
            if framework:
                params["framework"] = framework

            # Fetch templates from registry
            templates_list = await self._fetch_templates(params)

            # Filter by persona
            persona_templates = [
                t for t in templates_list
                if t.metadata.persona == persona_id
            ]

            logger.info(f"   Found {len(persona_templates)} templates for {persona_id}")

            # Calculate relevance scores
            scored_templates = []
            for template in persona_templates:
                relevance = self._calculate_relevance_score(
                    template, requirement, context
                )
                template.relevance_score = relevance
                template.selection_reasoning = self._generate_selection_reasoning(
                    template, relevance, requirement
                )
                scored_templates.append(template)

            # Sort by relevance (highest first)
            scored_templates.sort(key=lambda t: t.relevance_score, reverse=True)

            # Return top N
            result = scored_templates[:self.max_templates_per_persona]

            if result:
                logger.info(f"   ✅ Top template: {result[0].metadata.name} (relevance: {result[0].relevance_score:.0%})")
            else:
                logger.warning(f"   ⚠️  No templates found for {persona_id}")

            return result

        except Exception as e:
            logger.error(f"   ❌ Template search failed: {e}")
            return []

    async def _fetch_templates(self, params: Dict[str, Any]) -> List[TemplateContent]:
        """Fetch templates from registry API"""
        # Check cache first
        cache_key = self._get_cache_key("templates", params)
        cached = self._get_from_cache(cache_key)
        if cached:
            logger.debug(f"   📦 Cache hit: {cache_key}")
            return cached

        # Fetch from API
        session = await self._get_session()
        query_string = urlencode(params)
        url = f"{self.registry_url}?{query_string}"

        try:
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    templates_data = data.get("templates", [])

                    # Convert to TemplateContent objects
                    templates = []
                    for t_data in templates_data:
                        # Get full template content
                        full_template = await self._fetch_template_by_id(
                            t_data["id"],
                            file_path=t_data.get("file_path")
                        )
                        if full_template:
                            templates.append(full_template)

                    # Cache results
                    self._save_to_cache(cache_key, templates)

                    return templates
                else:
                    logger.warning(f"   API returned status {response.status}")
                    return []

        except Exception as e:
            logger.error(f"   API request failed: {e}")
            return []

    async def _fetch_template_by_id(self, template_id: str, file_path: Optional[str] = None) -> Optional[TemplateContent]:
        """Fetch single template with full content"""
        # Check in-memory cache
        if template_id in self._template_cache:
            return self._template_cache[template_id]

        # Check file cache
        cache_key = f"template_{template_id}"
        cached = self._get_from_cache(cache_key)
        if cached:
            self._template_cache[template_id] = cached
            return cached

        # Fetch from template storage (JSON files)
        # Use file_path from API if available, otherwise search for it
        if file_path:
            template_path = Path(file_path)
        else:
            template_path = self._find_template_file(template_id)

        if template_path and template_path.exists():
            try:
                with open(template_path) as f:
                    data = json.load(f)

                # Parse into TemplateContent
                template = self._parse_template_data(data)

                # Cache
                self._template_cache[template_id] = template
                self._save_to_cache(cache_key, template)

                return template

            except Exception as e:
                logger.error(f"   Failed to load template {template_id}: {e}")
                return None

        logger.warning(f"   Template not found: {template_id}")
        return None

    def _find_template_file(self, template_id: str) -> Optional[Path]:
        """Find template JSON file in storage"""
        # Templates are stored in {templates_base_path}/{persona}/
        templates_root = self.templates_base_path

        if not templates_root.exists():
            return None

        # Search all persona directories
        for persona_dir in templates_root.iterdir():
            if persona_dir.is_dir():
                # Try exact match first (UUID or name-based)
                template_file = persona_dir / f"{template_id}.json"
                if template_file.exists():
                    return template_file

                # Try finding by matching template name in JSON files
                for json_file in persona_dir.glob("*.json"):
                    try:
                        with open(json_file) as f:
                            data = json.load(f)
                            if data.get("metadata", {}).get("id") == template_id:
                                return json_file
                    except:
                        continue

        return None

    def _parse_template_data(self, data: Dict[str, Any]) -> TemplateContent:
        """Parse template JSON data into TemplateContent"""
        metadata_data = data.get("metadata", {})

        metadata = TemplateMetadata(
            id=metadata_data.get("id", "unknown"),
            name=metadata_data.get("name", "Unknown Template"),
            description=metadata_data.get("description", ""),
            category=metadata_data.get("category", "unknown"),
            language=metadata_data.get("language", ""),
            framework=metadata_data.get("framework", ""),
            version=metadata_data.get("version", "1.0"),
            tags=metadata_data.get("tags", []),
            persona=metadata_data.get("persona", "unknown"),
            quality_score=metadata_data.get("quality_score", 80.0),
            security_score=metadata_data.get("security_score", 80.0),
            performance_score=metadata_data.get("performance_score", 80.0),
            maintainability_score=metadata_data.get("maintainability_score", 80.0),
            test_coverage=metadata_data.get("test_coverage", 0.0),
            usage_count=metadata_data.get("usage_count", 0),
            success_rate=metadata_data.get("success_rate", 0.0),
            status=metadata_data.get("status", "approved"),
            is_pinned=metadata_data.get("is_pinned", False),
            quality_tier=metadata_data.get("quality_tier"),
            created_at=metadata_data.get("created_at"),
            updated_at=metadata_data.get("updated_at")
        )

        return TemplateContent(
            metadata=metadata,
            content=data.get("content", ""),
            variables=data.get("variables", {}),
            dependencies=data.get("dependencies", []),
            workflow_context=data.get("workflow_context", {})
        )

    def _calculate_relevance_score(
        self,
        template: TemplateContent,
        requirement: str,
        context: Dict[str, Any]
    ) -> float:
        """
        Calculate relevance score between template and requirement.

        Scoring components (weights from config):
        - Keyword matching (keyword_weight)
        - Category/tag alignment (tag_weight)
        - Quality scores (quality_weight)
        - Technology stack match (tech_stack_weight)
        - Usage statistics (usage_stats_weight)
        """
        scores = []

        # 1. Keyword matching
        req_lower = requirement.lower()
        template_text = f"{template.metadata.name} {template.metadata.description}".lower()
        template_tags = " ".join(template.metadata.tags).lower()

        # Simple keyword overlap
        req_words = set(req_lower.split())
        template_words = set(template_text.split()) | set(template_tags.split())
        overlap = len(req_words & template_words)
        keyword_score = min(overlap / max(len(req_words), 1), 1.0)
        scores.append(keyword_score * self.keyword_weight)

        # 2. Category/tag alignment
        # Check if requirement keywords match tags
        tag_matches = sum(1 for tag in template.metadata.tags if tag.lower() in req_lower)
        tag_score = min(tag_matches / max(len(template.metadata.tags), 1), 1.0)
        scores.append(tag_score * self.tag_weight)

        # 3. Quality scores
        quality_avg = (
            template.metadata.quality_score +
            template.metadata.security_score +
            template.metadata.performance_score +
            template.metadata.maintainability_score
        ) / 400.0  # Normalize to 0-1
        scores.append(quality_avg * self.quality_weight)

        # 4. Technology stack match
        tech_match = 1.0
        if context.get("language"):
            if template.metadata.language.lower() != context["language"].lower():
                tech_match *= 0.5
        if context.get("framework"):
            if template.metadata.framework.lower() != context["framework"].lower():
                tech_match *= 0.5
        scores.append(tech_match * self.tech_stack_weight)

        # 5. Usage statistics
        usage_score = min(template.metadata.usage_count / 100, 1.0) * 0.5  # Usage count
        usage_score += template.metadata.success_rate * 0.5  # Success rate
        scores.append(usage_score * self.usage_stats_weight)

        total_score = sum(scores)
        return round(total_score, 3)

    def _generate_selection_reasoning(
        self,
        template: TemplateContent,
        relevance: float,
        requirement: str
    ) -> str:
        """Generate human-readable reasoning for template selection"""
        if relevance >= self.relevance_threshold_use:
            return (
                f"High relevance ({relevance:.0%}) - Recommended for direct use. "
                f"Template '{template.metadata.name}' closely matches requirement with "
                f"quality score {template.metadata.quality_score}/100."
            )
        elif relevance >= self.relevance_threshold_custom:
            return (
                f"Medium relevance ({relevance:.0%}) - Use as inspiration/starting point. "
                f"Template provides useful patterns but may need customization."
            )
        else:
            return (
                f"Low relevance ({relevance:.0%}) - Consider building custom solution. "
                f"Template available for reference but significant customization needed."
            )

    # =========================================================================
    # PROJECT-LEVEL RAG
    # =========================================================================

    async def get_recommended_package(
        self,
        requirement: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Optional[PackageRecommendation]:
        """
        Get recommended template package for overall requirement.

        Uses the recommendation engine from maestro-templates to find
        the best matching template package.

        Args:
            requirement: Natural language requirement
            context: Additional context

        Returns:
            PackageRecommendation or None if no good match
        """
        logger.info("🎯 Getting recommended template package...")

        try:
            # Import recommendation engine from maestro-templates
            import sys
            templates_src = Path("/home/ec2-user/projects/maestro-platform/maestro-templates/src")
            if str(templates_src) not in sys.path:
                sys.path.insert(0, str(templates_src))

            from recommendation_engine import RecommendationEngine

            # Create recommendation engine
            engine = RecommendationEngine()

            # Get recommendation
            result = engine.recommend(requirement)

            # Convert to our PackageRecommendation format
            template_recommendations = [
                TemplateRecommendation(
                    template_id=t.template_id,
                    template_name=t.template_name,
                    persona=t.persona,
                    reason=t.reason,
                    priority=t.priority,
                    quality_score=t.quality_score,
                    is_substitute=t.is_substitute,
                    original_template_id=t.original_template_id
                )
                for t in result.recommended_templates
            ]

            package_rec = PackageRecommendation(
                requirement_text=result.requirement_text,
                recommendation_type=result.recommendation_type,
                confidence=result.confidence,
                best_match_package_id=result.best_match_package_id,
                best_match_package_name=result.best_match_package_name,
                recommended_templates=template_recommendations,
                explanation=result.explanation,
                warnings=result.warnings,
                estimated_setup_time_hours=result.estimated_setup_time_hours
            )

            logger.info(f"   ✅ Package: {package_rec.best_match_package_name or 'Custom'}")
            logger.info(f"   Type: {package_rec.recommendation_type}")
            logger.info(f"   Confidence: {package_rec.confidence:.0%}")
            logger.info(f"   Templates: {len(package_rec.recommended_templates)}")

            return package_rec

        except Exception as e:
            logger.error(f"   ❌ Package recommendation failed: {e}")
            return None

    # =========================================================================
    # CACHING
    # =========================================================================

    def _get_cache_key(self, prefix: str, params: Dict[str, Any]) -> str:
        """Generate cache key from parameters"""
        param_str = json.dumps(params, sort_keys=True)
        hash_val = hashlib.md5(param_str.encode()).hexdigest()[:12]
        return f"{prefix}_{hash_val}"

    def _get_from_cache(self, cache_key: str) -> Optional[Any]:
        """Get data from cache if not expired"""
        if not self.enable_cache:
            return None

        cache_file = self.cache_dir / f"{cache_key}.json"
        if not cache_file.exists():
            return None

        try:
            # Check if expired
            mtime = datetime.fromtimestamp(cache_file.stat().st_mtime)
            if datetime.now() - mtime > self.cache_ttl:
                cache_file.unlink()  # Delete expired cache
                return None

            # Load from cache
            with open(cache_file) as f:
                data = json.load(f)

            # Deserialize
            if isinstance(data, list):
                # List of templates
                return [self._deserialize_template(t) for t in data]
            else:
                # Single template
                return self._deserialize_template(data)

        except Exception as e:
            logger.debug(f"Cache read failed: {e}")
            return None

    def _save_to_cache(self, cache_key: str, data: Any):
        """Save data to cache"""
        if not self.enable_cache:
            return

        try:
            cache_file = self.cache_dir / f"{cache_key}.json"

            # Serialize
            if isinstance(data, list):
                serialized = [self._serialize_template(t) for t in data]
            else:
                serialized = self._serialize_template(data)

            # Save
            with open(cache_file, "w") as f:
                json.dump(serialized, f, indent=2)

        except Exception as e:
            logger.debug(f"Cache write failed: {e}")

    def _serialize_template(self, template: TemplateContent) -> Dict[str, Any]:
        """Serialize template for caching"""
        return {
            "metadata": asdict(template.metadata),
            "content": template.content,
            "variables": template.variables,
            "dependencies": template.dependencies,
            "workflow_context": template.workflow_context,
            "relevance_score": template.relevance_score,
            "selection_reasoning": template.selection_reasoning
        }

    def _deserialize_template(self, data: Dict[str, Any]) -> TemplateContent:
        """Deserialize template from cache"""
        metadata = TemplateMetadata(**data["metadata"])
        return TemplateContent(
            metadata=metadata,
            content=data["content"],
            variables=data["variables"],
            dependencies=data["dependencies"],
            workflow_context=data["workflow_context"],
            relevance_score=data.get("relevance_score", 0.0),
            selection_reasoning=data.get("selection_reasoning", "")
        )


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

async def test_rag_client():
    """Test RAG client functionality"""
    print("="*80)
    print("RAG Template Client - Test")
    print("="*80)

    client = TemplateRAGClient()

    # Test 1: Search templates for backend developer
    print("\n📋 Test 1: Search templates for backend_developer")
    requirement = "Build a REST API with authentication and CRUD operations"
    templates = await client.search_templates_for_persona(
        persona_id="backend_developer",
        requirement=requirement,
        context={"language": "python", "framework": "fastapi"}
    )

    print(f"\nFound {len(templates)} templates:")
    for i, template in enumerate(templates[:3], 1):
        print(f"\n{i}. {template.metadata.name}")
        print(f"   Relevance: {template.relevance_score:.0%}")
        print(f"   Quality: {template.metadata.quality_score}/100")
        print(f"   Framework: {template.metadata.framework}")
        print(f"   Reasoning: {template.selection_reasoning}")

    # Test 2: Get recommended package
    print("\n\n📋 Test 2: Get recommended template package")
    package = await client.get_recommended_package(
        requirement="Build an e-commerce platform with user authentication, product catalog, and payment processing"
    )

    if package:
        print(f"\nPackage: {package.best_match_package_name or 'Custom'}")
        print(f"Type: {package.recommendation_type}")
        print(f"Confidence: {package.confidence:.0%}")
        print(f"Explanation: {package.explanation}")
        print(f"\nTemplates ({len(package.recommended_templates)}):")
        for t in package.recommended_templates[:5]:
            print(f"  - {t.template_name} ({t.persona})")

    await client.close()

    print("\n" + "="*80)
    print("✅ Test complete")
    print("="*80)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s"
    )
    asyncio.run(test_rag_client())
