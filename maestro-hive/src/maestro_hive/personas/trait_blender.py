"""
Trait Blender Module - MD-3017

Provides weighted trait combination functionality for persona fusion.
Supports multiple blending strategies and conflict resolution.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Callable
import logging
import math

logger = logging.getLogger(__name__)


class BlendMode(Enum):
    """Available blending modes for traits."""
    WEIGHTED_SUM = "weighted_sum"
    GEOMETRIC_MEAN = "geometric_mean"
    HARMONIC_MEAN = "harmonic_mean"
    QUADRATIC_MEAN = "quadratic_mean"
    DOMINANT = "dominant"
    RECESSIVE = "recessive"


class ConflictResolution(Enum):
    """Strategies for resolving trait conflicts."""
    AVERAGE = "average"
    HIGHEST = "highest"
    LOWEST = "lowest"
    LATEST_WINS = "latest_wins"
    FIRST_WINS = "first_wins"
    WEIGHTED_PRIORITY = "weighted_priority"


@dataclass
class TraitValue:
    """Represents a single trait value with metadata."""
    value: float
    weight: float = 1.0
    source: Optional[str] = None
    timestamp: Optional[datetime] = None
    confidence: float = 1.0

    def __post_init__(self):
        if not 0 <= self.value <= 1:
            raise ValueError(f"Trait value must be between 0 and 1, got {self.value}")
        if self.weight < 0:
            raise ValueError(f"Weight must be non-negative, got {self.weight}")
        if not 0 <= self.confidence <= 1:
            raise ValueError(f"Confidence must be between 0 and 1, got {self.confidence}")


@dataclass
class BlendResult:
    """Result of a trait blending operation."""
    trait_name: str
    blended_value: float
    source_count: int
    blend_mode: str
    confidence: float
    contributing_sources: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class BlenderConfig:
    """Configuration for the TraitBlender."""
    default_mode: BlendMode = BlendMode.WEIGHTED_SUM
    conflict_resolution: ConflictResolution = ConflictResolution.AVERAGE
    normalize_weights: bool = True
    weight_bounds: Tuple[float, float] = (0.1, 2.0)
    min_confidence_threshold: float = 0.0
    apply_confidence_weighting: bool = True


class TraitBlender:
    """
    Blends traits from multiple sources using configurable strategies.

    Supports various blending modes and conflict resolution strategies
    for combining persona traits in the fusion process.
    """

    def __init__(self, config: Optional[BlenderConfig] = None):
        self.config = config or BlenderConfig()
        self._blend_functions: Dict[BlendMode, Callable] = {
            BlendMode.WEIGHTED_SUM: self._weighted_sum,
            BlendMode.GEOMETRIC_MEAN: self._geometric_mean,
            BlendMode.HARMONIC_MEAN: self._harmonic_mean,
            BlendMode.QUADRATIC_MEAN: self._quadratic_mean,
            BlendMode.DOMINANT: self._dominant,
            BlendMode.RECESSIVE: self._recessive,
        }
        logger.info(f"TraitBlender initialized with mode: {self.config.default_mode.value}")

    def blend_trait(
        self,
        trait_name: str,
        values: List[TraitValue],
        mode: Optional[BlendMode] = None
    ) -> BlendResult:
        """
        Blend multiple trait values into a single result.

        Args:
            trait_name: Name of the trait being blended
            values: List of TraitValue objects to blend
            mode: Blending mode to use (defaults to config default)

        Returns:
            BlendResult with the blended value and metadata
        """
        if not values:
            raise ValueError("At least one trait value required for blending")

        mode = mode or self.config.default_mode

        # Filter by confidence threshold
        filtered_values = [
            v for v in values
            if v.confidence >= self.config.min_confidence_threshold
        ]

        if not filtered_values:
            logger.warning(f"All values for trait '{trait_name}' below confidence threshold")
            filtered_values = values  # Fall back to all values

        # Normalize weights if configured
        if self.config.normalize_weights:
            filtered_values = self._normalize_weights(filtered_values)

        # Apply confidence weighting if enabled
        if self.config.apply_confidence_weighting:
            filtered_values = self._apply_confidence_weights(filtered_values)

        # Get the blend function and calculate result
        blend_func = self._blend_functions.get(mode, self._weighted_sum)
        blended_value = blend_func(filtered_values)

        # Calculate aggregate confidence
        total_confidence = sum(v.confidence * v.weight for v in filtered_values)
        total_weight = sum(v.weight for v in filtered_values)
        avg_confidence = total_confidence / total_weight if total_weight > 0 else 0.0

        # Collect contributing sources
        sources = [v.source for v in filtered_values if v.source]

        return BlendResult(
            trait_name=trait_name,
            blended_value=min(1.0, max(0.0, blended_value)),  # Clamp to [0, 1]
            source_count=len(filtered_values),
            blend_mode=mode.value,
            confidence=avg_confidence,
            contributing_sources=sources,
            metadata={
                "original_count": len(values),
                "filtered_count": len(filtered_values),
                "normalization_applied": self.config.normalize_weights
            }
        )

    def blend_multiple_traits(
        self,
        traits: Dict[str, List[TraitValue]],
        mode: Optional[BlendMode] = None
    ) -> Dict[str, BlendResult]:
        """
        Blend multiple traits at once.

        Args:
            traits: Dictionary mapping trait names to lists of values
            mode: Blending mode to use for all traits

        Returns:
            Dictionary mapping trait names to BlendResults
        """
        results = {}
        for trait_name, values in traits.items():
            try:
                results[trait_name] = self.blend_trait(trait_name, values, mode)
            except Exception as e:
                logger.error(f"Failed to blend trait '{trait_name}': {e}")
                raise
        return results

    def resolve_conflict(
        self,
        values: List[TraitValue],
        resolution: Optional[ConflictResolution] = None
    ) -> TraitValue:
        """
        Resolve a conflict between multiple trait values.

        Args:
            values: Conflicting trait values
            resolution: Resolution strategy to use

        Returns:
            Single resolved TraitValue
        """
        if not values:
            raise ValueError("No values to resolve")

        if len(values) == 1:
            return values[0]

        resolution = resolution or self.config.conflict_resolution

        if resolution == ConflictResolution.AVERAGE:
            avg_value = sum(v.value for v in values) / len(values)
            return TraitValue(
                value=avg_value,
                weight=sum(v.weight for v in values) / len(values),
                source="conflict_resolution:average",
                confidence=sum(v.confidence for v in values) / len(values)
            )

        elif resolution == ConflictResolution.HIGHEST:
            return max(values, key=lambda v: v.value)

        elif resolution == ConflictResolution.LOWEST:
            return min(values, key=lambda v: v.value)

        elif resolution == ConflictResolution.LATEST_WINS:
            values_with_time = [v for v in values if v.timestamp]
            if values_with_time:
                return max(values_with_time, key=lambda v: v.timestamp)
            return values[-1]  # Fall back to last in list

        elif resolution == ConflictResolution.FIRST_WINS:
            values_with_time = [v for v in values if v.timestamp]
            if values_with_time:
                return min(values_with_time, key=lambda v: v.timestamp)
            return values[0]

        elif resolution == ConflictResolution.WEIGHTED_PRIORITY:
            return max(values, key=lambda v: v.value * v.weight * v.confidence)

        else:
            return values[0]

    def _normalize_weights(self, values: List[TraitValue]) -> List[TraitValue]:
        """Normalize weights to sum to 1."""
        total_weight = sum(v.weight for v in values)
        if total_weight == 0:
            return values

        return [
            TraitValue(
                value=v.value,
                weight=v.weight / total_weight,
                source=v.source,
                timestamp=v.timestamp,
                confidence=v.confidence
            )
            for v in values
        ]

    def _apply_confidence_weights(self, values: List[TraitValue]) -> List[TraitValue]:
        """Adjust weights based on confidence scores."""
        return [
            TraitValue(
                value=v.value,
                weight=v.weight * v.confidence,
                source=v.source,
                timestamp=v.timestamp,
                confidence=v.confidence
            )
            for v in values
        ]

    def _weighted_sum(self, values: List[TraitValue]) -> float:
        """Calculate weighted sum (normalized)."""
        total_weight = sum(v.weight for v in values)
        if total_weight == 0:
            return sum(v.value for v in values) / len(values)
        return sum(v.value * v.weight for v in values) / total_weight

    def _geometric_mean(self, values: List[TraitValue]) -> float:
        """Calculate weighted geometric mean."""
        if any(v.value == 0 for v in values):
            return 0.0

        total_weight = sum(v.weight for v in values)
        if total_weight == 0:
            total_weight = len(values)
            weights = [1.0] * len(values)
        else:
            weights = [v.weight for v in values]

        log_sum = sum(w * math.log(v.value) for v, w in zip(values, weights) if v.value > 0)
        return math.exp(log_sum / total_weight)

    def _harmonic_mean(self, values: List[TraitValue]) -> float:
        """Calculate weighted harmonic mean."""
        if any(v.value == 0 for v in values):
            return 0.0

        total_weight = sum(v.weight for v in values)
        if total_weight == 0:
            return len(values) / sum(1 / v.value for v in values)

        weighted_reciprocal_sum = sum(v.weight / v.value for v in values)
        return total_weight / weighted_reciprocal_sum

    def _quadratic_mean(self, values: List[TraitValue]) -> float:
        """Calculate weighted quadratic mean (RMS)."""
        total_weight = sum(v.weight for v in values)
        if total_weight == 0:
            return math.sqrt(sum(v.value ** 2 for v in values) / len(values))

        weighted_square_sum = sum(v.weight * v.value ** 2 for v in values)
        return math.sqrt(weighted_square_sum / total_weight)

    def _dominant(self, values: List[TraitValue]) -> float:
        """Return the value with highest weight * confidence."""
        if not values:
            return 0.0
        dominant = max(values, key=lambda v: v.weight * v.confidence)
        return dominant.value

    def _recessive(self, values: List[TraitValue]) -> float:
        """Return the value with lowest weight * confidence."""
        if not values:
            return 0.0
        recessive = min(values, key=lambda v: v.weight * v.confidence)
        return recessive.value

    def get_available_modes(self) -> List[str]:
        """Return list of available blending modes."""
        return [m.value for m in BlendMode]

    def get_available_resolutions(self) -> List[str]:
        """Return list of available conflict resolution strategies."""
        return [r.value for r in ConflictResolution]

    def calculate_trait_variance(self, values: List[TraitValue]) -> float:
        """Calculate variance among trait values."""
        if len(values) < 2:
            return 0.0

        trait_values = [v.value for v in values]
        mean = sum(trait_values) / len(trait_values)
        return sum((v - mean) ** 2 for v in trait_values) / len(trait_values)

    def detect_conflicts(
        self,
        values: List[TraitValue],
        variance_threshold: float = 0.25
    ) -> bool:
        """
        Detect if there are significant conflicts among trait values.

        Args:
            values: List of trait values to check
            variance_threshold: Variance above which conflicts are detected

        Returns:
            True if conflicts detected, False otherwise
        """
        return self.calculate_trait_variance(values) > variance_threshold


# Module-level convenience functions
_default_blender: Optional[TraitBlender] = None


def get_default_blender() -> TraitBlender:
    """Get or create the default trait blender instance."""
    global _default_blender
    if _default_blender is None:
        _default_blender = TraitBlender()
    return _default_blender


def blend(
    trait_name: str,
    values: List[Dict[str, Any]],
    mode: str = "weighted_sum"
) -> Dict[str, Any]:
    """
    Convenience function for quick trait blending.

    Args:
        trait_name: Name of the trait
        values: List of dicts with 'value', 'weight', 'source' keys
        mode: Blending mode string

    Returns:
        Dictionary with blended result
    """
    blender = get_default_blender()
    trait_values = [
        TraitValue(
            value=v.get("value", 0.0),
            weight=v.get("weight", 1.0),
            source=v.get("source"),
            confidence=v.get("confidence", 1.0)
        )
        for v in values
    ]

    blend_mode = BlendMode(mode)
    result = blender.blend_trait(trait_name, trait_values, blend_mode)

    return {
        "trait_name": result.trait_name,
        "blended_value": result.blended_value,
        "source_count": result.source_count,
        "blend_mode": result.blend_mode,
        "confidence": result.confidence,
        "contributing_sources": result.contributing_sources
    }
