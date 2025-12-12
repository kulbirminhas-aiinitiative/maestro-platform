"""
Persona Fusion Engine - MD-3017

Enables fusion of multiple personas into hybrid agents with blended traits
and capabilities. Part of the Persona Fusion & Hybridization system.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set
import hashlib
import logging
import uuid

logger = logging.getLogger(__name__)


class FusionStrategy(Enum):
    """Available strategies for persona fusion."""
    WEIGHTED_AVERAGE = "weighted_average"
    MAX_POOLING = "max_pooling"
    HIERARCHICAL = "hierarchical"
    MIN_POOLING = "min_pooling"
    CONSENSUS = "consensus"


@dataclass
class PersonaTrait:
    """Represents a single persona trait with value and weight."""
    name: str
    value: float
    weight: float = 1.0
    source_persona: Optional[str] = None

    def __post_init__(self):
        if not 0 <= self.value <= 1:
            raise ValueError(f"Trait value must be between 0 and 1, got {self.value}")
        if self.weight < 0:
            raise ValueError(f"Trait weight must be non-negative, got {self.weight}")


@dataclass
class FusionValidationResult:
    """Result of persona fusion validation."""
    is_valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    compatibility_score: float = 0.0
    conflicting_traits: List[str] = field(default_factory=list)


@dataclass
class FusionPreview:
    """Preview of fusion result without persisting."""
    preview_id: str
    source_personas: List[str]
    estimated_traits: Dict[str, float]
    strategy: str
    compatibility_score: float
    warnings: List[str] = field(default_factory=list)


@dataclass
class FusedPersona:
    """Represents a fused/hybrid persona combining multiple sources."""
    id: str
    name: str
    source_personas: List[str]
    blended_traits: Dict[str, float]
    fusion_strategy: str
    created_at: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "id": self.id,
            "name": self.name,
            "source_personas": self.source_personas,
            "blended_traits": self.blended_traits,
            "fusion_strategy": self.fusion_strategy,
            "created_at": self.created_at.isoformat(),
            "metadata": self.metadata
        }


@dataclass
class FusionConfig:
    """Configuration for the fusion engine."""
    cache_enabled: bool = True
    cache_ttl: int = 3600
    max_personas: int = 5
    normalize_weights: bool = True
    default_strategy: FusionStrategy = FusionStrategy.WEIGHTED_AVERAGE
    conflict_resolution: str = "average"


class FusionCache:
    """Simple in-memory cache for fusion results."""

    def __init__(self, ttl: int = 3600):
        self._cache: Dict[str, tuple] = {}
        self._ttl = ttl

    def _generate_key(self, persona_ids: List[str], strategy: str) -> str:
        """Generate cache key from persona IDs and strategy."""
        sorted_ids = sorted(persona_ids)
        key_str = f"{','.join(sorted_ids)}:{strategy}"
        return hashlib.md5(key_str.encode()).hexdigest()

    def get(self, persona_ids: List[str], strategy: str) -> Optional[FusedPersona]:
        """Retrieve cached fusion result."""
        key = self._generate_key(persona_ids, strategy)
        if key in self._cache:
            result, timestamp = self._cache[key]
            if (datetime.now() - timestamp).seconds < self._ttl:
                logger.debug(f"Cache hit for fusion key: {key}")
                return result
            del self._cache[key]
        return None

    def set(self, persona_ids: List[str], strategy: str, result: FusedPersona) -> None:
        """Store fusion result in cache."""
        key = self._generate_key(persona_ids, strategy)
        self._cache[key] = (result, datetime.now())
        logger.debug(f"Cached fusion result with key: {key}")

    def clear(self) -> None:
        """Clear all cached results."""
        self._cache.clear()
        logger.info("Fusion cache cleared")


class FusionEngine:
    """
    Main engine for combining multiple personas into hybrid agents.

    Supports multiple fusion strategies and provides validation,
    preview, and caching capabilities.
    """

    def __init__(
        self,
        config: Optional[FusionConfig] = None,
        cache_enabled: bool = True
    ):
        self.config = config or FusionConfig()
        self._cache = FusionCache(self.config.cache_ttl) if cache_enabled else None
        self._persona_registry: Dict[str, Dict[str, Any]] = {}
        logger.info(f"FusionEngine initialized with strategy: {self.config.default_strategy.value}")

    def register_persona(self, persona_id: str, traits: Dict[str, float], metadata: Optional[Dict] = None) -> None:
        """Register a persona for fusion operations."""
        self._persona_registry[persona_id] = {
            "traits": traits,
            "metadata": metadata or {}
        }
        logger.debug(f"Registered persona: {persona_id}")

    def get_persona(self, persona_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a registered persona."""
        return self._persona_registry.get(persona_id)

    def validate_fusion(
        self,
        persona_ids: List[str]
    ) -> FusionValidationResult:
        """
        Validate compatibility of personas for fusion.

        Args:
            persona_ids: List of persona IDs to validate

        Returns:
            FusionValidationResult with validation status and details
        """
        errors = []
        warnings = []
        conflicting_traits = []

        # Check persona count
        if len(persona_ids) < 2:
            errors.append("At least 2 personas are required for fusion")

        if len(persona_ids) > self.config.max_personas:
            errors.append(f"Maximum {self.config.max_personas} personas allowed, got {len(persona_ids)}")

        # Check for duplicates
        if len(persona_ids) != len(set(persona_ids)):
            errors.append("Duplicate persona IDs detected")

        # Check personas exist
        missing = [pid for pid in persona_ids if pid not in self._persona_registry]
        if missing:
            errors.append(f"Personas not found: {missing}")

        # Check for trait conflicts
        if not missing:
            all_traits: Dict[str, List[float]] = {}
            for pid in persona_ids:
                persona = self._persona_registry[pid]
                for trait, value in persona["traits"].items():
                    if trait not in all_traits:
                        all_traits[trait] = []
                    all_traits[trait].append(value)

            # Identify conflicting traits (high variance)
            for trait, values in all_traits.items():
                if len(values) > 1:
                    variance = sum((v - sum(values)/len(values))**2 for v in values) / len(values)
                    if variance > 0.25:  # High variance threshold
                        conflicting_traits.append(trait)
                        warnings.append(f"High variance in trait '{trait}': consider using hierarchical strategy")

        # Calculate compatibility score
        compatibility = 1.0
        if conflicting_traits:
            compatibility -= 0.1 * len(conflicting_traits)
        compatibility = max(0.0, compatibility)

        return FusionValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            compatibility_score=compatibility,
            conflicting_traits=conflicting_traits
        )

    def get_fusion_preview(
        self,
        persona_ids: List[str],
        strategy: Optional[FusionStrategy] = None
    ) -> FusionPreview:
        """
        Get a preview of fusion result without persisting.

        Args:
            persona_ids: List of persona IDs to preview fusion
            strategy: Fusion strategy to use (defaults to config default)

        Returns:
            FusionPreview with estimated traits and compatibility
        """
        strategy = strategy or self.config.default_strategy

        validation = self.validate_fusion(persona_ids)

        # Collect all traits
        all_traits: Dict[str, List[tuple]] = {}
        for pid in persona_ids:
            if pid in self._persona_registry:
                persona = self._persona_registry[pid]
                for trait, value in persona["traits"].items():
                    if trait not in all_traits:
                        all_traits[trait] = []
                    all_traits[trait].append((value, 1.0, pid))

        # Estimate blended traits
        estimated = self._blend_traits(all_traits, strategy)

        return FusionPreview(
            preview_id=str(uuid.uuid4())[:8],
            source_personas=persona_ids,
            estimated_traits=estimated,
            strategy=strategy.value,
            compatibility_score=validation.compatibility_score,
            warnings=validation.warnings
        )

    def fuse_personas(
        self,
        persona_ids: List[str],
        strategy: Optional[FusionStrategy] = None,
        name: Optional[str] = None
    ) -> FusedPersona:
        """
        Combine multiple personas into a single hybrid persona.

        Args:
            persona_ids: List of persona IDs to fuse
            strategy: Fusion strategy to use
            name: Optional name for the fused persona

        Returns:
            FusedPersona representing the hybrid

        Raises:
            ValueError: If validation fails
        """
        strategy = strategy or self.config.default_strategy

        # Check cache first
        if self._cache:
            cached = self._cache.get(persona_ids, strategy.value)
            if cached:
                logger.info(f"Returning cached fusion for {persona_ids}")
                return cached

        # Validate
        validation = self.validate_fusion(persona_ids)
        if not validation.is_valid:
            raise ValueError(f"Fusion validation failed: {validation.errors}")

        # Collect all traits
        all_traits: Dict[str, List[tuple]] = {}
        for pid in persona_ids:
            persona = self._persona_registry[pid]
            for trait, value in persona["traits"].items():
                if trait not in all_traits:
                    all_traits[trait] = []
                all_traits[trait].append((value, 1.0, pid))

        # Blend traits
        blended = self._blend_traits(all_traits, strategy)

        # Create fused persona
        fused_id = f"fused_{hashlib.md5('_'.join(sorted(persona_ids)).encode()).hexdigest()[:12]}"
        fused_name = name or f"Hybrid ({'+'.join(persona_ids)})"

        result = FusedPersona(
            id=fused_id,
            name=fused_name,
            source_personas=persona_ids,
            blended_traits=blended,
            fusion_strategy=strategy.value,
            created_at=datetime.now(),
            metadata={
                "compatibility_score": validation.compatibility_score,
                "warnings": validation.warnings
            }
        )

        # Cache result
        if self._cache:
            self._cache.set(persona_ids, strategy.value, result)

        logger.info(f"Created fused persona: {fused_id} from {persona_ids}")
        return result

    def _blend_traits(
        self,
        traits: Dict[str, List[tuple]],
        strategy: FusionStrategy
    ) -> Dict[str, float]:
        """Apply blending strategy to traits."""
        blended = {}

        for trait_name, values in traits.items():
            if strategy == FusionStrategy.WEIGHTED_AVERAGE:
                total_weight = sum(w for _, w, _ in values)
                if total_weight > 0:
                    blended[trait_name] = sum(v * w for v, w, _ in values) / total_weight
                else:
                    blended[trait_name] = sum(v for v, _, _ in values) / len(values)

            elif strategy == FusionStrategy.MAX_POOLING:
                blended[trait_name] = max(v for v, _, _ in values)

            elif strategy == FusionStrategy.MIN_POOLING:
                blended[trait_name] = min(v for v, _, _ in values)

            elif strategy == FusionStrategy.HIERARCHICAL:
                # First persona takes priority
                blended[trait_name] = values[0][0]

            elif strategy == FusionStrategy.CONSENSUS:
                # Use median
                sorted_vals = sorted(v for v, _, _ in values)
                mid = len(sorted_vals) // 2
                if len(sorted_vals) % 2 == 0:
                    blended[trait_name] = (sorted_vals[mid-1] + sorted_vals[mid]) / 2
                else:
                    blended[trait_name] = sorted_vals[mid]
            else:
                # Default to average
                blended[trait_name] = sum(v for v, _, _ in values) / len(values)

        return blended

    def clear_cache(self) -> None:
        """Clear the fusion result cache."""
        if self._cache:
            self._cache.clear()
            logger.info("Fusion cache cleared")

    def get_available_strategies(self) -> List[str]:
        """Return list of available fusion strategies."""
        return [s.value for s in FusionStrategy]

    def unfuse(self, fused_persona_id: str) -> List[str]:
        """
        Get the source persona IDs from a fused persona ID.

        Note: This is a reverse lookup and may not work for all fused personas
        if the original registry state has changed.
        """
        # Look through registry for matching fusion
        for pid, data in self._persona_registry.items():
            if pid == fused_persona_id and "source_personas" in data.get("metadata", {}):
                return data["metadata"]["source_personas"]
        return []


# Module-level convenience functions
_default_engine: Optional[FusionEngine] = None

def get_default_engine() -> FusionEngine:
    """Get or create the default fusion engine instance."""
    global _default_engine
    if _default_engine is None:
        _default_engine = FusionEngine()
    return _default_engine

def fuse(persona_ids: List[str], strategy: str = "weighted_average") -> FusedPersona:
    """Convenience function for quick persona fusion."""
    engine = get_default_engine()
    strat = FusionStrategy(strategy)
    return engine.fuse_personas(persona_ids, strat)
