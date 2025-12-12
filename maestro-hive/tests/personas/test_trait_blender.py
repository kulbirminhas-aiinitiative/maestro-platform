"""
Tests for Trait Blender - MD-3017

Comprehensive test suite for trait blending functionality.
"""

import pytest
import math
from datetime import datetime
from unittest.mock import Mock, patch

from maestro_hive.personas.trait_blender import (
    TraitBlender,
    BlendMode,
    ConflictResolution,
    TraitValue,
    BlendResult,
    BlenderConfig,
    blend,
    get_default_blender
)


class TestTraitValue:
    """Tests for TraitValue dataclass."""

    def test_valid_trait_value_creation(self):
        """Test creating a valid trait value."""
        tv = TraitValue(value=0.7, weight=1.5, source="persona_1")
        assert tv.value == 0.7
        assert tv.weight == 1.5
        assert tv.source == "persona_1"
        assert tv.confidence == 1.0  # default

    def test_trait_value_bounds(self):
        """Test trait value bounds validation."""
        with pytest.raises(ValueError, match="value must be between 0 and 1"):
            TraitValue(value=1.5)

        with pytest.raises(ValueError, match="value must be between 0 and 1"):
            TraitValue(value=-0.1)

    def test_trait_weight_bounds(self):
        """Test trait weight bounds validation."""
        with pytest.raises(ValueError, match="Weight must be non-negative"):
            TraitValue(value=0.5, weight=-1.0)

    def test_trait_confidence_bounds(self):
        """Test confidence bounds validation."""
        with pytest.raises(ValueError, match="Confidence must be between 0 and 1"):
            TraitValue(value=0.5, confidence=1.5)

    def test_trait_value_with_timestamp(self):
        """Test trait value with timestamp."""
        now = datetime.now()
        tv = TraitValue(value=0.5, timestamp=now)
        assert tv.timestamp == now


class TestBlendResult:
    """Tests for BlendResult dataclass."""

    def test_blend_result_creation(self):
        """Test creating a blend result."""
        result = BlendResult(
            trait_name="creativity",
            blended_value=0.75,
            source_count=3,
            blend_mode="weighted_sum",
            confidence=0.9,
            contributing_sources=["p1", "p2", "p3"]
        )
        assert result.trait_name == "creativity"
        assert result.blended_value == 0.75
        assert result.source_count == 3


class TestBlenderConfig:
    """Tests for BlenderConfig dataclass."""

    def test_default_config(self):
        """Test default configuration values."""
        config = BlenderConfig()
        assert config.default_mode == BlendMode.WEIGHTED_SUM
        assert config.conflict_resolution == ConflictResolution.AVERAGE
        assert config.normalize_weights is True

    def test_custom_config(self):
        """Test custom configuration."""
        config = BlenderConfig(
            default_mode=BlendMode.GEOMETRIC_MEAN,
            normalize_weights=False
        )
        assert config.default_mode == BlendMode.GEOMETRIC_MEAN
        assert config.normalize_weights is False


class TestTraitBlender:
    """Tests for TraitBlender main class."""

    @pytest.fixture
    def blender(self):
        """Create a TraitBlender instance for testing."""
        return TraitBlender()

    @pytest.fixture
    def sample_values(self):
        """Create sample trait values for testing."""
        return [
            TraitValue(value=0.8, weight=1.0, source="p1"),
            TraitValue(value=0.4, weight=1.0, source="p2"),
            TraitValue(value=0.6, weight=1.0, source="p3"),
        ]

    def test_blender_initialization(self, blender):
        """Test blender initialization."""
        assert blender.config.default_mode == BlendMode.WEIGHTED_SUM

    def test_blend_trait_weighted_sum(self, blender, sample_values):
        """Test weighted sum blending."""
        result = blender.blend_trait("test", sample_values, BlendMode.WEIGHTED_SUM)

        # (0.8 + 0.4 + 0.6) / 3 = 0.6
        assert abs(result.blended_value - 0.6) < 0.01
        assert result.trait_name == "test"
        assert result.source_count == 3

    def test_blend_trait_weighted_sum_with_weights(self, blender):
        """Test weighted sum with different weights."""
        values = [
            TraitValue(value=0.8, weight=2.0),
            TraitValue(value=0.4, weight=1.0),
        ]
        result = blender.blend_trait("test", values, BlendMode.WEIGHTED_SUM)

        # (0.8 * 2 + 0.4 * 1) / 3 = 2.0 / 3 = 0.666...
        assert abs(result.blended_value - 0.666) < 0.01

    def test_blend_trait_geometric_mean(self, blender, sample_values):
        """Test geometric mean blending."""
        result = blender.blend_trait("test", sample_values, BlendMode.GEOMETRIC_MEAN)

        # geometric mean of [0.8, 0.4, 0.6] = (0.8 * 0.4 * 0.6)^(1/3)
        expected = math.pow(0.8 * 0.4 * 0.6, 1/3)
        assert abs(result.blended_value - expected) < 0.01

    def test_blend_trait_geometric_mean_with_zero(self, blender):
        """Test geometric mean with zero value."""
        values = [
            TraitValue(value=0.8),
            TraitValue(value=0.0),
        ]
        result = blender.blend_trait("test", values, BlendMode.GEOMETRIC_MEAN)
        assert result.blended_value == 0.0

    def test_blend_trait_harmonic_mean(self, blender, sample_values):
        """Test harmonic mean blending."""
        result = blender.blend_trait("test", sample_values, BlendMode.HARMONIC_MEAN)

        # harmonic mean = n / sum(1/x)
        expected = 3 / (1/0.8 + 1/0.4 + 1/0.6)
        assert abs(result.blended_value - expected) < 0.01

    def test_blend_trait_harmonic_mean_with_zero(self, blender):
        """Test harmonic mean with zero value."""
        values = [
            TraitValue(value=0.8),
            TraitValue(value=0.0),
        ]
        result = blender.blend_trait("test", values, BlendMode.HARMONIC_MEAN)
        assert result.blended_value == 0.0

    def test_blend_trait_quadratic_mean(self, blender, sample_values):
        """Test quadratic mean (RMS) blending."""
        result = blender.blend_trait("test", sample_values, BlendMode.QUADRATIC_MEAN)

        # RMS = sqrt(mean(x^2))
        expected = math.sqrt((0.8**2 + 0.4**2 + 0.6**2) / 3)
        assert abs(result.blended_value - expected) < 0.01

    def test_blend_trait_dominant(self, blender):
        """Test dominant blending (highest weight * confidence)."""
        values = [
            TraitValue(value=0.3, weight=1.0, confidence=0.5),
            TraitValue(value=0.9, weight=2.0, confidence=1.0),  # Highest weight * confidence
            TraitValue(value=0.6, weight=1.0, confidence=0.8),
        ]
        result = blender.blend_trait("test", values, BlendMode.DOMINANT)
        assert result.blended_value == 0.9

    def test_blend_trait_recessive(self, blender):
        """Test recessive blending (lowest weight * confidence)."""
        values = [
            TraitValue(value=0.3, weight=1.0, confidence=0.5),  # Lowest weight * confidence
            TraitValue(value=0.9, weight=2.0, confidence=1.0),
            TraitValue(value=0.6, weight=1.0, confidence=0.8),
        ]
        result = blender.blend_trait("test", values, BlendMode.RECESSIVE)
        assert result.blended_value == 0.3

    def test_blend_trait_empty_values(self, blender):
        """Test blending with empty values raises error."""
        with pytest.raises(ValueError, match="At least one trait value required"):
            blender.blend_trait("test", [])

    def test_blend_trait_value_clamping(self, blender):
        """Test that blended values are clamped to [0, 1]."""
        # This shouldn't happen normally but test the safety
        result = blender.blend_trait("test", [TraitValue(value=1.0)])
        assert 0 <= result.blended_value <= 1

    def test_blend_multiple_traits(self, blender):
        """Test blending multiple traits at once."""
        traits = {
            "creativity": [
                TraitValue(value=0.8, source="p1"),
                TraitValue(value=0.4, source="p2"),
            ],
            "technical": [
                TraitValue(value=0.9, source="p1"),
                TraitValue(value=0.7, source="p2"),
            ]
        }
        results = blender.blend_multiple_traits(traits)

        assert "creativity" in results
        assert "technical" in results
        assert abs(results["creativity"].blended_value - 0.6) < 0.01
        assert abs(results["technical"].blended_value - 0.8) < 0.01


class TestConflictResolution:
    """Tests for conflict resolution strategies."""

    @pytest.fixture
    def blender(self):
        return TraitBlender()

    def test_resolve_conflict_average(self, blender):
        """Test average conflict resolution."""
        values = [
            TraitValue(value=0.8, source="p1"),
            TraitValue(value=0.4, source="p2"),
        ]
        result = blender.resolve_conflict(values, ConflictResolution.AVERAGE)
        assert abs(result.value - 0.6) < 0.01

    def test_resolve_conflict_highest(self, blender):
        """Test highest value conflict resolution."""
        values = [
            TraitValue(value=0.8, source="p1"),
            TraitValue(value=0.4, source="p2"),
        ]
        result = blender.resolve_conflict(values, ConflictResolution.HIGHEST)
        assert result.value == 0.8

    def test_resolve_conflict_lowest(self, blender):
        """Test lowest value conflict resolution."""
        values = [
            TraitValue(value=0.8, source="p1"),
            TraitValue(value=0.4, source="p2"),
        ]
        result = blender.resolve_conflict(values, ConflictResolution.LOWEST)
        assert result.value == 0.4

    def test_resolve_conflict_latest_wins(self, blender):
        """Test latest wins conflict resolution."""
        now = datetime.now()
        values = [
            TraitValue(value=0.3, timestamp=datetime(2024, 1, 1)),
            TraitValue(value=0.9, timestamp=now),  # Latest
        ]
        result = blender.resolve_conflict(values, ConflictResolution.LATEST_WINS)
        assert result.value == 0.9

    def test_resolve_conflict_first_wins(self, blender):
        """Test first wins conflict resolution."""
        now = datetime.now()
        values = [
            TraitValue(value=0.3, timestamp=datetime(2024, 1, 1)),  # First
            TraitValue(value=0.9, timestamp=now),
        ]
        result = blender.resolve_conflict(values, ConflictResolution.FIRST_WINS)
        assert result.value == 0.3

    def test_resolve_conflict_weighted_priority(self, blender):
        """Test weighted priority conflict resolution."""
        values = [
            TraitValue(value=0.3, weight=1.0, confidence=1.0),  # 0.3 * 1 * 1 = 0.3
            TraitValue(value=0.9, weight=0.5, confidence=0.5),  # 0.9 * 0.5 * 0.5 = 0.225
        ]
        result = blender.resolve_conflict(values, ConflictResolution.WEIGHTED_PRIORITY)
        assert result.value == 0.3  # Higher weighted priority

    def test_resolve_conflict_single_value(self, blender):
        """Test conflict resolution with single value."""
        values = [TraitValue(value=0.5)]
        result = blender.resolve_conflict(values)
        assert result.value == 0.5

    def test_resolve_conflict_empty_raises(self, blender):
        """Test conflict resolution with no values raises error."""
        with pytest.raises(ValueError, match="No values to resolve"):
            blender.resolve_conflict([])


class TestVarianceAndConflictDetection:
    """Tests for variance calculation and conflict detection."""

    @pytest.fixture
    def blender(self):
        return TraitBlender()

    def test_calculate_trait_variance(self, blender):
        """Test variance calculation."""
        values = [
            TraitValue(value=0.8),
            TraitValue(value=0.4),
            TraitValue(value=0.6),
        ]
        variance = blender.calculate_trait_variance(values)

        # mean = 0.6, variance = ((0.8-0.6)^2 + (0.4-0.6)^2 + (0.6-0.6)^2) / 3
        expected = (0.04 + 0.04 + 0.0) / 3
        assert abs(variance - expected) < 0.001

    def test_calculate_trait_variance_single_value(self, blender):
        """Test variance with single value is zero."""
        values = [TraitValue(value=0.5)]
        assert blender.calculate_trait_variance(values) == 0.0

    def test_detect_conflicts_high_variance(self, blender):
        """Test conflict detection with high variance."""
        values = [
            TraitValue(value=0.1),
            TraitValue(value=0.9),
        ]
        assert blender.detect_conflicts(values, variance_threshold=0.1)

    def test_detect_conflicts_low_variance(self, blender):
        """Test conflict detection with low variance."""
        values = [
            TraitValue(value=0.5),
            TraitValue(value=0.6),
        ]
        assert not blender.detect_conflicts(values, variance_threshold=0.1)


class TestConfigurationOptions:
    """Tests for blender configuration options."""

    def test_confidence_threshold_filtering(self):
        """Test that low confidence values can be filtered."""
        config = BlenderConfig(min_confidence_threshold=0.5)
        blender = TraitBlender(config)

        values = [
            TraitValue(value=0.9, confidence=0.8),  # Kept (0.8 >= 0.5)
            TraitValue(value=0.1, confidence=0.2),  # Filtered (0.2 < 0.5)
        ]

        result = blender.blend_trait("test", values)
        # Only the first value passes the threshold
        assert result.source_count == 1
        assert result.blended_value == 0.9

    def test_weight_normalization_enabled(self):
        """Test weight normalization when enabled."""
        config = BlenderConfig(normalize_weights=True)
        blender = TraitBlender(config)

        values = [
            TraitValue(value=1.0, weight=3.0),
            TraitValue(value=0.0, weight=1.0),
        ]

        result = blender.blend_trait("test", values)
        # With normalization: (1.0 * 0.75 + 0.0 * 0.25) = 0.75
        assert abs(result.blended_value - 0.75) < 0.01

    def test_confidence_weighting_applied(self):
        """Test confidence weighting effect."""
        config = BlenderConfig(apply_confidence_weighting=True)
        blender = TraitBlender(config)

        values = [
            TraitValue(value=0.9, weight=1.0, confidence=1.0),  # Full weight
            TraitValue(value=0.1, weight=1.0, confidence=0.1),  # Very low effective weight
        ]

        result = blender.blend_trait("test", values)
        # Should be closer to 0.9 due to confidence weighting
        assert result.blended_value > 0.7


class TestConvenienceFunctions:
    """Tests for module-level convenience functions."""

    def test_get_default_blender(self):
        """Test getting the default blender."""
        blender = get_default_blender()
        assert isinstance(blender, TraitBlender)

        # Should return same instance
        blender2 = get_default_blender()
        assert blender is blender2

    def test_blend_function(self):
        """Test the convenience blend function."""
        result = blend(
            "creativity",
            [
                {"value": 0.8, "weight": 1.0, "source": "p1"},
                {"value": 0.4, "weight": 1.0, "source": "p2"},
            ],
            mode="weighted_sum"
        )

        assert result["trait_name"] == "creativity"
        assert abs(result["blended_value"] - 0.6) < 0.01
        assert result["source_count"] == 2


class TestAvailableModes:
    """Tests for listing available modes and resolutions."""

    def test_get_available_modes(self):
        """Test getting available blending modes."""
        blender = TraitBlender()
        modes = blender.get_available_modes()

        assert "weighted_sum" in modes
        assert "geometric_mean" in modes
        assert "harmonic_mean" in modes
        assert "quadratic_mean" in modes
        assert "dominant" in modes
        assert "recessive" in modes

    def test_get_available_resolutions(self):
        """Test getting available conflict resolutions."""
        blender = TraitBlender()
        resolutions = blender.get_available_resolutions()

        assert "average" in resolutions
        assert "highest" in resolutions
        assert "lowest" in resolutions
        assert "latest_wins" in resolutions
        assert "first_wins" in resolutions
        assert "weighted_priority" in resolutions


class TestBlenderIntegration:
    """Integration tests for blender workflows."""

    def test_full_blending_workflow(self):
        """Test complete blending workflow."""
        # Initialize with custom config
        config = BlenderConfig(
            default_mode=BlendMode.WEIGHTED_SUM,
            conflict_resolution=ConflictResolution.WEIGHTED_PRIORITY,
            normalize_weights=True
        )
        blender = TraitBlender(config)

        # Create trait values from multiple personas
        creativity_values = [
            TraitValue(value=0.9, weight=2.0, source="designer", confidence=0.95),
            TraitValue(value=0.4, weight=1.0, source="engineer", confidence=0.9),
            TraitValue(value=0.7, weight=1.5, source="manager", confidence=0.85),
        ]

        technical_values = [
            TraitValue(value=0.3, weight=1.0, source="designer", confidence=0.7),
            TraitValue(value=0.95, weight=2.5, source="engineer", confidence=0.98),
            TraitValue(value=0.5, weight=1.0, source="manager", confidence=0.8),
        ]

        # Check for conflicts
        has_creativity_conflict = blender.detect_conflicts(creativity_values)
        has_technical_conflict = blender.detect_conflicts(technical_values)

        # Blend traits
        results = blender.blend_multiple_traits({
            "creativity": creativity_values,
            "technical": technical_values,
        })

        # Verify results
        assert "creativity" in results
        assert "technical" in results
        assert 0 <= results["creativity"].blended_value <= 1
        assert 0 <= results["technical"].blended_value <= 1
        assert results["creativity"].source_count == 3
        assert results["technical"].source_count == 3
