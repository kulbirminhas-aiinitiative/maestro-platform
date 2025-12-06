"""
BlueprintScorer: 4-Dimensional Scoring for Blueprint-Requirement Matching

This module implements a weighted scoring system to calculate how well a blueprint
matches a requirement classification. It replaces hardcoded match_score values
(0.85, 0.6) with a dynamic calculation based on:

1. Parallelizability Match (30%): How well execution patterns align
2. Expertise Coverage (30%): How well required skills are covered
3. Complexity Alignment (20%): How well complexity levels match
4. Historical Success Rate (20%): Past performance of the blueprint

JIRA: MD-2534
"""
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple, Protocol
from enum import Enum
import logging
import os


logger = logging.getLogger(__name__)


# Default scoring weights
DEFAULT_WEIGHTS = {
    "parallelizability": 0.30,
    "expertise_coverage": 0.30,
    "complexity_alignment": 0.20,
    "historical_success": 0.20,
}


class ParallelizabilityLevel(Enum):
    """Parallelizability levels for requirements"""
    FULLY_PARALLEL = "fully_parallel"
    PARTIALLY_PARALLEL = "partially_parallel"
    SEQUENTIAL = "sequential"


class RequirementComplexity(Enum):
    """Complexity levels for requirements"""
    SIMPLE = "simple"
    MODERATE = "moderate"
    COMPLEX = "complex"
    VERY_COMPLEX = "very_complex"


@dataclass
class ScoringWeights:
    """Configuration for scoring dimension weights"""
    parallelizability: float = 0.30
    expertise_coverage: float = 0.30
    complexity_alignment: float = 0.20
    historical_success: float = 0.20

    def __post_init__(self):
        total = (
            self.parallelizability +
            self.expertise_coverage +
            self.complexity_alignment +
            self.historical_success
        )
        if abs(total - 1.0) > 0.001:
            logger.warning(f"Weights sum to {total}, not 1.0. Normalizing...")
            self.parallelizability /= total
            self.expertise_coverage /= total
            self.complexity_alignment /= total
            self.historical_success /= total

    def to_dict(self) -> Dict[str, float]:
        return {
            "parallelizability": self.parallelizability,
            "expertise_coverage": self.expertise_coverage,
            "complexity_alignment": self.complexity_alignment,
            "historical_success": self.historical_success,
        }


class HistoryStore(Protocol):
    """Protocol for history storage backends"""
    def get_success_rate(self, blueprint_id: str) -> Optional[float]:
        """Get success rate for a blueprint (0.0-1.0)"""
        ...


@dataclass
class DefaultHistoryStore:
    """Default in-memory history store with baseline rates"""
    _rates: Dict[str, float] = field(default_factory=dict)
    default_rate: float = 0.7

    def get_success_rate(self, blueprint_id: str) -> Optional[float]:
        return self._rates.get(blueprint_id, self.default_rate)

    def record_execution(self, blueprint_id: str, success: bool):
        """Record an execution result"""
        current = self._rates.get(blueprint_id, self.default_rate)
        # Simple exponential moving average
        alpha = 0.3
        new_value = 1.0 if success else 0.0
        self._rates[blueprint_id] = alpha * new_value + (1 - alpha) * current


@dataclass
class ScoreBreakdown:
    """Breakdown of individual dimension scores"""
    overall: float
    parallelizability: float
    expertise_coverage: float
    complexity_alignment: float
    historical_success: float

    def to_dict(self) -> Dict[str, float]:
        return {
            "overall": self.overall,
            "parallelizability": self.parallelizability,
            "expertise_coverage": self.expertise_coverage,
            "complexity_alignment": self.complexity_alignment,
            "historical_success": self.historical_success,
        }


class BlueprintScorer:
    """
    4-Dimensional Blueprint Scorer

    Calculates match scores between requirements and blueprints based on:
    - Parallelizability match
    - Expertise coverage
    - Complexity alignment
    - Historical success rate

    Example:
        >>> scorer = BlueprintScorer()
        >>> score = scorer.score(classification, blueprint)
        >>> print(f"Match score: {score:.2f}")
    """

    def __init__(
        self,
        weights: Optional[Dict[str, float]] = None,
        history_store: Optional[HistoryStore] = None
    ):
        """
        Initialize the BlueprintScorer.

        Args:
            weights: Optional custom weights for scoring dimensions.
                     Keys: parallelizability, expertise_coverage,
                           complexity_alignment, historical_success
            history_store: Optional history provider for success rate calculations
        """
        # Load weights from environment if not provided
        if weights is None:
            env_weights = os.environ.get("BLUEPRINT_SCORER_WEIGHTS")
            if env_weights:
                try:
                    import json
                    weights = json.loads(env_weights)
                except Exception as e:
                    logger.warning(f"Failed to parse BLUEPRINT_SCORER_WEIGHTS: {e}")
                    weights = DEFAULT_WEIGHTS.copy()
            else:
                weights = DEFAULT_WEIGHTS.copy()

        self._weights = ScoringWeights(
            parallelizability=weights.get("parallelizability", 0.30),
            expertise_coverage=weights.get("expertise_coverage", 0.30),
            complexity_alignment=weights.get("complexity_alignment", 0.20),
            historical_success=weights.get("historical_success", 0.20),
        )

        self._history_store = history_store or DefaultHistoryStore()

        # Check if history is enabled
        self._history_enabled = os.environ.get(
            "BLUEPRINT_SCORER_HISTORY_ENABLED", "true"
        ).lower() == "true"

        logger.debug(
            f"BlueprintScorer initialized with weights: {self._weights.to_dict()}"
        )

    def score(
        self,
        classification: Any,
        blueprint: Any
    ) -> float:
        """
        Calculate overall match score between a requirement and blueprint.

        Args:
            classification: RequirementClassification with parallelizability,
                          complexity, and required_expertise
            blueprint: BlueprintMetadata with archetype and capabilities

        Returns:
            Float between 0.0 and 1.0 representing match quality
        """
        try:
            overall, _ = self.score_with_breakdown(classification, blueprint)
            return overall
        except Exception as e:
            logger.warning(f"BlueprintScorer.score failed: {e}, returning 0.5")
            return 0.5

    def score_with_breakdown(
        self,
        classification: Any,
        blueprint: Any
    ) -> Tuple[float, ScoreBreakdown]:
        """
        Calculate score with per-dimension breakdown.

        Args:
            classification: RequirementClassification
            blueprint: BlueprintMetadata

        Returns:
            Tuple of (overall_score, ScoreBreakdown)
        """
        # Calculate individual dimension scores
        para_score = self._score_parallelizability(classification, blueprint)
        expertise_score = self._score_expertise_coverage(classification, blueprint)
        complexity_score = self._score_complexity_alignment(classification, blueprint)
        history_score = self._score_historical_success(blueprint)

        # Calculate weighted overall score
        overall = (
            self._weights.parallelizability * para_score +
            self._weights.expertise_coverage * expertise_score +
            self._weights.complexity_alignment * complexity_score +
            self._weights.historical_success * history_score
        )

        breakdown = ScoreBreakdown(
            overall=overall,
            parallelizability=para_score,
            expertise_coverage=expertise_score,
            complexity_alignment=complexity_score,
            historical_success=history_score,
        )

        logger.debug(
            f"BlueprintScorer calculated score={overall:.2f} "
            f"breakdown={breakdown.to_dict()}"
        )

        return overall, breakdown

    def _score_parallelizability(
        self,
        classification: Any,
        blueprint: Any
    ) -> float:
        """
        Score how well requirement parallelizability matches blueprint execution mode.

        Scoring matrix:
        | Requirement          | Blueprint   | Score |
        |---------------------|-------------|-------|
        | FULLY_PARALLEL      | parallel    | 1.0   |
        | FULLY_PARALLEL      | sequential  | 0.3   |
        | PARTIALLY_PARALLEL  | parallel    | 0.8   |
        | PARTIALLY_PARALLEL  | sequential  | 0.6   |
        | SEQUENTIAL          | sequential  | 1.0   |
        | SEQUENTIAL          | parallel    | 0.7   |
        """
        try:
            # Get requirement parallelizability
            req_para = getattr(classification, 'parallelizability', None)
            if req_para is None:
                return 0.5  # Neutral if unknown

            # Get blueprint execution mode
            bp_mode = self._get_blueprint_execution_mode(blueprint)

            # Convert to string for comparison
            if hasattr(req_para, 'value'):
                req_para_str = req_para.value.lower()
            else:
                req_para_str = str(req_para).lower()

            bp_mode_str = bp_mode.lower() if bp_mode else "sequential"

            # Scoring matrix
            is_parallel_bp = "parallel" in bp_mode_str

            if "fully_parallel" in req_para_str:
                return 1.0 if is_parallel_bp else 0.3
            elif "partially_parallel" in req_para_str:
                return 0.8 if is_parallel_bp else 0.6
            else:  # sequential
                return 0.7 if is_parallel_bp else 1.0

        except Exception as e:
            logger.warning(f"Parallelizability scoring failed: {e}")
            return 0.5

    def _score_expertise_coverage(
        self,
        classification: Any,
        blueprint: Any
    ) -> float:
        """
        Score how well blueprint covers required expertise.

        Calculates overlap between required skills and blueprint capabilities.
        """
        try:
            # Get required expertise from classification
            required = getattr(classification, 'required_expertise', [])
            if not required:
                return 0.7  # Default score if no requirements

            # Get blueprint capabilities/personas
            bp_capabilities = self._get_blueprint_capabilities(blueprint)

            if not bp_capabilities:
                return 0.5  # Neutral if no capabilities defined

            # Calculate overlap
            required_lower = set(skill.lower() for skill in required)
            capabilities_lower = set(cap.lower() for cap in bp_capabilities)

            # Check for matches (including partial matches)
            matched = 0
            for req in required_lower:
                for cap in capabilities_lower:
                    if req in cap or cap in req:
                        matched += 1
                        break

            coverage = matched / len(required_lower)
            return min(coverage, 1.0)

        except Exception as e:
            logger.warning(f"Expertise coverage scoring failed: {e}")
            return 0.5

    def _score_complexity_alignment(
        self,
        classification: Any,
        blueprint: Any
    ) -> float:
        """
        Score how well requirement complexity aligns with blueprint's intended use.

        | Alignment        | Score |
        |-----------------|-------|
        | Exact match     | 1.0   |
        | One level off   | 0.7   |
        | Two levels off  | 0.4   |
        | Three+ levels   | 0.2   |
        """
        try:
            # Get requirement complexity
            req_complexity = getattr(classification, 'complexity', None)
            if req_complexity is None:
                return 0.6  # Neutral

            # Get blueprint target complexity
            bp_complexity = self._get_blueprint_complexity(blueprint)

            # Convert to numeric scale
            complexity_order = {
                "simple": 0,
                "moderate": 1,
                "complex": 2,
                "very_complex": 3,
            }

            if hasattr(req_complexity, 'value'):
                req_val = complexity_order.get(req_complexity.value.lower(), 1)
            else:
                req_val = complexity_order.get(str(req_complexity).lower(), 1)

            bp_val = complexity_order.get(bp_complexity.lower(), 1) if bp_complexity else 1

            # Score based on distance
            distance = abs(req_val - bp_val)
            scores = {0: 1.0, 1: 0.7, 2: 0.4, 3: 0.2}
            return scores.get(distance, 0.2)

        except Exception as e:
            logger.warning(f"Complexity alignment scoring failed: {e}")
            return 0.5

    def _score_historical_success(self, blueprint: Any) -> float:
        """
        Score based on historical success rate of the blueprint.
        """
        if not self._history_enabled:
            return 0.7  # Default neutral-positive score

        try:
            # Get blueprint ID
            bp_id = getattr(blueprint, 'id', None) or getattr(blueprint, 'blueprint_id', None)
            if not bp_id:
                bp_id = str(blueprint)

            success_rate = self._history_store.get_success_rate(bp_id)
            if success_rate is not None:
                return success_rate
            return 0.7  # Default

        except Exception as e:
            logger.warning(f"Historical success scoring failed: {e}")
            return 0.7

    def _get_blueprint_execution_mode(self, blueprint: Any) -> str:
        """Extract execution mode from blueprint."""
        try:
            # Try archetype.execution.mode
            if hasattr(blueprint, 'archetype'):
                arch = blueprint.archetype
                if hasattr(arch, 'execution'):
                    exec_cfg = arch.execution
                    if hasattr(exec_cfg, 'mode'):
                        mode = exec_cfg.mode
                        return mode.value if hasattr(mode, 'value') else str(mode)

            # Try direct execution_mode
            if hasattr(blueprint, 'execution_mode'):
                mode = blueprint.execution_mode
                return mode.value if hasattr(mode, 'value') else str(mode)

            # Try dict access
            if isinstance(blueprint, dict):
                return blueprint.get('execution_mode', 'sequential')

            return "sequential"
        except Exception:
            return "sequential"

    def _get_blueprint_capabilities(self, blueprint: Any) -> List[str]:
        """Extract capabilities/personas from blueprint."""
        try:
            # Try archetype.roles or personas
            if hasattr(blueprint, 'archetype'):
                arch = blueprint.archetype
                if hasattr(arch, 'roles'):
                    return [str(r) for r in arch.roles]

            # Try direct capabilities
            if hasattr(blueprint, 'capabilities'):
                return list(blueprint.capabilities)

            # Try personas
            if hasattr(blueprint, 'personas'):
                return list(blueprint.personas)

            # Try dict access
            if isinstance(blueprint, dict):
                return blueprint.get('capabilities', blueprint.get('personas', []))

            return []
        except Exception:
            return []

    def _get_blueprint_complexity(self, blueprint: Any) -> str:
        """Extract target complexity from blueprint."""
        try:
            # Try archetype.complexity
            if hasattr(blueprint, 'archetype'):
                arch = blueprint.archetype
                if hasattr(arch, 'complexity'):
                    return str(arch.complexity)

            # Try scaling strategy as proxy
            if hasattr(blueprint, 'archetype'):
                arch = blueprint.archetype
                if hasattr(arch, 'scaling'):
                    scaling = arch.scaling
                    scaling_str = scaling.value if hasattr(scaling, 'value') else str(scaling)
                    # Elastic scaling suggests complex use cases
                    if "elastic" in scaling_str.lower():
                        return "complex"

            # Try direct access
            if hasattr(blueprint, 'complexity'):
                return str(blueprint.complexity)

            return "moderate"  # Default
        except Exception:
            return "moderate"

    @property
    def weights(self) -> ScoringWeights:
        """Get current scoring weights."""
        return self._weights


# Convenience function for one-off scoring
def score_blueprint(
    classification: Any,
    blueprint: Any,
    weights: Optional[Dict[str, float]] = None
) -> float:
    """
    Convenience function to score a blueprint against a classification.

    Args:
        classification: RequirementClassification
        blueprint: BlueprintMetadata
        weights: Optional custom weights

    Returns:
        Match score (0.0-1.0)
    """
    scorer = BlueprintScorer(weights=weights)
    return scorer.score(classification, blueprint)
