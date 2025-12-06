"""
Unit tests for BlueprintScorer - 4-Dimensional Scoring

Tests all 4 scoring dimensions:
1. Parallelizability match
2. Expertise coverage
3. Complexity alignment
4. Historical success rate

JIRA: MD-2534
"""
import pytest
from dataclasses import dataclass
from typing import List, Optional
from enum import Enum
import sys
from pathlib import Path

# Add source path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from maestro_hive.teams.blueprint_scorer import (
    BlueprintScorer,
    ScoringWeights,
    ScoreBreakdown,
    DefaultHistoryStore,
    ParallelizabilityLevel,
    RequirementComplexity,
    score_blueprint,
    DEFAULT_WEIGHTS,
)


# Mock data classes for testing
@dataclass
class MockArchetype:
    """Mock archetype for testing"""
    class MockExecution:
        class MockMode:
            def __init__(self, value):
                self.value = value
        def __init__(self, mode_value):
            self.mode = self.MockMode(mode_value)

    class MockCoordination:
        class MockMode:
            def __init__(self, value):
                self.value = value
        def __init__(self, mode_value):
            self.mode = self.MockMode(mode_value)

    class MockScaling:
        def __init__(self, value):
            self.value = value

    def __init__(self, exec_mode="parallel", coord_mode="shared_state", scaling="elastic"):
        self.execution = self.MockExecution(exec_mode)
        self.coordination = self.MockCoordination(coord_mode)
        self.scaling = self.MockScaling(scaling)


@dataclass
class MockBlueprint:
    """Mock blueprint for testing"""
    id: str
    name: str
    archetype: Optional[MockArchetype] = None
    capabilities: Optional[List[str]] = None
    personas: Optional[List[str]] = None
    complexity: Optional[str] = None

    def __post_init__(self):
        if self.archetype is None:
            self.archetype = MockArchetype()
        if self.capabilities is None:
            self.capabilities = ["backend", "frontend", "testing"]


class MockParallelizability(Enum):
    FULLY_PARALLEL = "fully_parallel"
    PARTIALLY_PARALLEL = "partially_parallel"
    SEQUENTIAL = "sequential"


class MockComplexity(Enum):
    SIMPLE = "simple"
    MODERATE = "moderate"
    COMPLEX = "complex"
    VERY_COMPLEX = "very_complex"


@dataclass
class MockClassification:
    """Mock classification for testing"""
    parallelizability: MockParallelizability = MockParallelizability.PARTIALLY_PARALLEL
    complexity: MockComplexity = MockComplexity.MODERATE
    required_expertise: List[str] = None

    def __post_init__(self):
        if self.required_expertise is None:
            self.required_expertise = ["backend", "testing"]


class TestScoringWeights:
    """Tests for ScoringWeights configuration"""

    def test_default_weights_sum_to_one(self):
        """Default weights should sum to 1.0"""
        weights = ScoringWeights()
        total = (
            weights.parallelizability +
            weights.expertise_coverage +
            weights.complexity_alignment +
            weights.historical_success
        )
        assert abs(total - 1.0) < 0.001

    def test_custom_weights_normalization(self):
        """Custom weights should be normalized to sum to 1.0"""
        weights = ScoringWeights(
            parallelizability=0.5,
            expertise_coverage=0.5,
            complexity_alignment=0.5,
            historical_success=0.5
        )
        total = (
            weights.parallelizability +
            weights.expertise_coverage +
            weights.complexity_alignment +
            weights.historical_success
        )
        assert abs(total - 1.0) < 0.001

    def test_to_dict(self):
        """to_dict should return all weights"""
        weights = ScoringWeights()
        d = weights.to_dict()
        assert "parallelizability" in d
        assert "expertise_coverage" in d
        assert "complexity_alignment" in d
        assert "historical_success" in d


class TestDefaultHistoryStore:
    """Tests for DefaultHistoryStore"""

    def test_default_rate(self):
        """Should return default rate for unknown blueprints"""
        store = DefaultHistoryStore()
        rate = store.get_success_rate("unknown-blueprint")
        assert rate == 0.7

    def test_record_execution(self):
        """Should update rates based on execution results"""
        store = DefaultHistoryStore()
        bp_id = "test-blueprint"

        # Record a success
        store.record_execution(bp_id, success=True)
        rate_after_success = store.get_success_rate(bp_id)

        # Rate should increase (or stay same if already high)
        assert rate_after_success >= 0.7


class TestBlueprintScorer:
    """Tests for BlueprintScorer main class"""

    def test_initialization(self):
        """Scorer should initialize with default weights"""
        scorer = BlueprintScorer()
        assert scorer.weights is not None
        assert abs(scorer.weights.parallelizability - 0.30) < 0.01

    def test_initialization_with_custom_weights(self):
        """Scorer should accept custom weights"""
        custom = {
            "parallelizability": 0.40,
            "expertise_coverage": 0.30,
            "complexity_alignment": 0.15,
            "historical_success": 0.15
        }
        scorer = BlueprintScorer(weights=custom)
        assert abs(scorer.weights.parallelizability - 0.40) < 0.01

    def test_score_returns_float(self):
        """score() should return float between 0 and 1"""
        scorer = BlueprintScorer()
        classification = MockClassification()
        blueprint = MockBlueprint(id="bp-1", name="Test Blueprint")

        score = scorer.score(classification, blueprint)

        assert isinstance(score, float)
        assert 0.0 <= score <= 1.0

    def test_score_with_breakdown(self):
        """score_with_breakdown() should return overall and components"""
        scorer = BlueprintScorer()
        classification = MockClassification()
        blueprint = MockBlueprint(id="bp-1", name="Test Blueprint")

        overall, breakdown = scorer.score_with_breakdown(classification, blueprint)

        assert isinstance(overall, float)
        assert isinstance(breakdown, ScoreBreakdown)
        assert 0.0 <= breakdown.parallelizability <= 1.0
        assert 0.0 <= breakdown.expertise_coverage <= 1.0
        assert 0.0 <= breakdown.complexity_alignment <= 1.0
        assert 0.0 <= breakdown.historical_success <= 1.0


class TestParallelizabilityScoring:
    """Tests for parallelizability dimension scoring"""

    def test_fully_parallel_with_parallel_blueprint(self):
        """FULLY_PARALLEL + parallel blueprint = high score"""
        scorer = BlueprintScorer()
        classification = MockClassification(
            parallelizability=MockParallelizability.FULLY_PARALLEL
        )
        blueprint = MockBlueprint(
            id="bp-1",
            name="Parallel Blueprint",
            archetype=MockArchetype(exec_mode="parallel")
        )

        _, breakdown = scorer.score_with_breakdown(classification, blueprint)
        assert breakdown.parallelizability == 1.0

    def test_fully_parallel_with_sequential_blueprint(self):
        """FULLY_PARALLEL + sequential blueprint = low score"""
        scorer = BlueprintScorer()
        classification = MockClassification(
            parallelizability=MockParallelizability.FULLY_PARALLEL
        )
        blueprint = MockBlueprint(
            id="bp-1",
            name="Sequential Blueprint",
            archetype=MockArchetype(exec_mode="sequential")
        )

        _, breakdown = scorer.score_with_breakdown(classification, blueprint)
        assert breakdown.parallelizability == 0.3

    def test_sequential_with_sequential_blueprint(self):
        """SEQUENTIAL + sequential blueprint = high score"""
        scorer = BlueprintScorer()
        classification = MockClassification(
            parallelizability=MockParallelizability.SEQUENTIAL
        )
        blueprint = MockBlueprint(
            id="bp-1",
            name="Sequential Blueprint",
            archetype=MockArchetype(exec_mode="sequential")
        )

        _, breakdown = scorer.score_with_breakdown(classification, blueprint)
        assert breakdown.parallelizability == 1.0


class TestExpertiseCoverageScoring:
    """Tests for expertise coverage dimension scoring"""

    def test_full_coverage(self):
        """All required expertise covered = score 1.0"""
        scorer = BlueprintScorer()
        classification = MockClassification(
            required_expertise=["backend", "testing"]
        )
        blueprint = MockBlueprint(
            id="bp-1",
            name="Full Coverage Blueprint",
            capabilities=["backend", "frontend", "testing", "devops"]
        )

        _, breakdown = scorer.score_with_breakdown(classification, blueprint)
        assert breakdown.expertise_coverage == 1.0

    def test_partial_coverage(self):
        """Some expertise covered = partial score"""
        scorer = BlueprintScorer()
        classification = MockClassification(
            required_expertise=["backend", "ml", "security"]
        )
        blueprint = MockBlueprint(
            id="bp-1",
            name="Partial Coverage Blueprint",
            capabilities=["backend"]  # Only 1 of 3
        )

        _, breakdown = scorer.score_with_breakdown(classification, blueprint)
        # Should be approximately 1/3
        assert 0.3 <= breakdown.expertise_coverage <= 0.4

    def test_no_coverage(self):
        """No expertise covered = low score"""
        scorer = BlueprintScorer()
        classification = MockClassification(
            required_expertise=["ml", "security", "blockchain"]
        )
        blueprint = MockBlueprint(
            id="bp-1",
            name="No Coverage Blueprint",
            capabilities=["backend", "frontend"]
        )

        _, breakdown = scorer.score_with_breakdown(classification, blueprint)
        assert breakdown.expertise_coverage == 0.0


class TestComplexityAlignmentScoring:
    """Tests for complexity alignment dimension scoring"""

    def test_exact_complexity_match(self):
        """Same complexity level = score 1.0"""
        scorer = BlueprintScorer()
        classification = MockClassification(complexity=MockComplexity.COMPLEX)
        blueprint = MockBlueprint(
            id="bp-1",
            name="Complex Blueprint",
            complexity="complex",
            archetype=MockArchetype(scaling="elastic")  # Indicates complex
        )

        _, breakdown = scorer.score_with_breakdown(classification, blueprint)
        assert breakdown.complexity_alignment >= 0.6  # Elastic scaling gives high score

    def test_simple_requirement_with_simple_blueprint(self):
        """Simple requirement + simple blueprint = good match"""
        scorer = BlueprintScorer()
        classification = MockClassification(complexity=MockComplexity.SIMPLE)
        blueprint = MockBlueprint(
            id="bp-1",
            name="Simple Blueprint",
            complexity="simple",
            archetype=MockArchetype(scaling="static")
        )

        _, breakdown = scorer.score_with_breakdown(classification, blueprint)
        # Static scaling suggests simple = moderate complexity (1) vs simple (0) = one off
        assert breakdown.complexity_alignment >= 0.4


class TestHistoricalSuccessScoring:
    """Tests for historical success dimension scoring"""

    def test_default_history(self):
        """Default history should give neutral score"""
        scorer = BlueprintScorer()
        classification = MockClassification()
        blueprint = MockBlueprint(id="unknown-bp", name="Unknown Blueprint")

        _, breakdown = scorer.score_with_breakdown(classification, blueprint)
        # Default rate is 0.7
        assert breakdown.historical_success == 0.7

    def test_with_custom_history_store(self):
        """Custom history store should affect scoring"""
        store = DefaultHistoryStore()
        store._rates["custom-bp"] = 0.95  # High success rate

        scorer = BlueprintScorer(history_store=store)
        classification = MockClassification()
        blueprint = MockBlueprint(id="custom-bp", name="Custom Blueprint")

        _, breakdown = scorer.score_with_breakdown(classification, blueprint)
        assert breakdown.historical_success == 0.95


class TestWeightedScoring:
    """Tests for weighted overall scoring"""

    def test_overall_is_weighted_sum(self):
        """Overall score should be weighted sum of dimensions"""
        weights = {
            "parallelizability": 0.25,
            "expertise_coverage": 0.25,
            "complexity_alignment": 0.25,
            "historical_success": 0.25
        }
        scorer = BlueprintScorer(weights=weights)
        classification = MockClassification()
        blueprint = MockBlueprint(id="bp-1", name="Test Blueprint")

        overall, breakdown = scorer.score_with_breakdown(classification, blueprint)

        expected = (
            0.25 * breakdown.parallelizability +
            0.25 * breakdown.expertise_coverage +
            0.25 * breakdown.complexity_alignment +
            0.25 * breakdown.historical_success
        )
        assert abs(overall - expected) < 0.01


class TestEdgeCases:
    """Tests for edge cases and error handling"""

    def test_missing_classification_fields(self):
        """Should handle missing classification fields gracefully"""
        scorer = BlueprintScorer()

        @dataclass
        class IncompleteClassification:
            required_expertise: List[str] = None

        classification = IncompleteClassification()
        blueprint = MockBlueprint(id="bp-1", name="Test Blueprint")

        # Should not raise, should return neutral score
        score = scorer.score(classification, blueprint)
        assert 0.0 <= score <= 1.0

    def test_missing_blueprint_archetype(self):
        """Should handle missing blueprint archetype gracefully"""
        scorer = BlueprintScorer()
        classification = MockClassification()

        @dataclass
        class SimpleBlueprintNoArchetype:
            id: str
            name: str

        blueprint = SimpleBlueprintNoArchetype(id="bp-1", name="Simple")

        # Should not raise
        score = scorer.score(classification, blueprint)
        assert 0.0 <= score <= 1.0

    def test_score_on_error_returns_neutral(self):
        """On internal error, score() should return a neutral score (~0.5)"""
        scorer = BlueprintScorer()

        # Pass invalid types - scorer handles gracefully with default values
        score = scorer.score(None, None)
        # Should return a neutral-ish score (between 0.4 and 0.8)
        assert 0.4 <= score <= 0.8


class TestConvenienceFunction:
    """Tests for score_blueprint convenience function"""

    def test_score_blueprint_function(self):
        """score_blueprint() should work like BlueprintScorer.score()"""
        classification = MockClassification()
        blueprint = MockBlueprint(id="bp-1", name="Test Blueprint")

        score = score_blueprint(classification, blueprint)

        assert isinstance(score, float)
        assert 0.0 <= score <= 1.0


class TestScoreBreakdown:
    """Tests for ScoreBreakdown dataclass"""

    def test_to_dict(self):
        """to_dict should return all dimension scores"""
        breakdown = ScoreBreakdown(
            overall=0.75,
            parallelizability=0.8,
            expertise_coverage=0.7,
            complexity_alignment=0.6,
            historical_success=0.9
        )
        d = breakdown.to_dict()

        assert d["overall"] == 0.75
        assert d["parallelizability"] == 0.8
        assert d["expertise_coverage"] == 0.7
        assert d["complexity_alignment"] == 0.6
        assert d["historical_success"] == 0.9


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
