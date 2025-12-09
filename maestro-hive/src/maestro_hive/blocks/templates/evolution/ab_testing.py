#!/usr/bin/env python3
"""
A/B Testing Engine: Manages A/B tests for template evolution.

This module handles:
- Test variant management
- Traffic splitting
- Metric collection and analysis
- Statistical significance testing
"""

import logging
import math
import random
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple
import uuid

logger = logging.getLogger(__name__)


class VariantStatus(Enum):
    """Status of a test variant."""
    ACTIVE = "active"
    PAUSED = "paused"
    WINNER = "winner"
    LOSER = "loser"


class TestStatus(Enum):
    """Status of an A/B test."""
    DRAFT = "draft"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


@dataclass
class Variant:
    """A variant in an A/B test."""
    variant_id: str
    name: str
    description: str
    config: Dict[str, Any]
    traffic_weight: float = 0.5  # 0.0 to 1.0
    status: VariantStatus = VariantStatus.ACTIVE
    impressions: int = 0
    conversions: int = 0
    custom_metrics: Dict[str, float] = field(default_factory=dict)

    def conversion_rate(self) -> float:
        """Calculate conversion rate."""
        if self.impressions == 0:
            return 0.0
        return self.conversions / self.impressions


@dataclass
class ABTest:
    """An A/B test configuration."""
    test_id: str
    name: str
    description: str
    variants: List[Variant]
    status: TestStatus = TestStatus.DRAFT
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    min_sample_size: int = 100
    confidence_level: float = 0.95
    primary_metric: str = "conversion_rate"
    created_at: datetime = field(default_factory=datetime.utcnow)
    winner_variant_id: Optional[str] = None

    def total_impressions(self) -> int:
        """Get total impressions across all variants."""
        return sum(v.impressions for v in self.variants)

    def is_ready_for_analysis(self) -> bool:
        """Check if test has enough data for analysis."""
        return all(v.impressions >= self.min_sample_size for v in self.variants)


@dataclass
class TestResult:
    """Result of A/B test analysis."""
    test_id: str
    winner: Optional[str]
    confidence: float
    variants_data: List[Dict[str, Any]]
    is_significant: bool
    recommendation: str
    analyzed_at: datetime = field(default_factory=datetime.utcnow)


class ABTestingEngine:
    """
    Manages A/B testing for template evolution.

    Implements:
    - ab_testing_integration: Create and manage A/B tests
    - usage_analytics: Track variant usage
    - evolutionary_learning: Learn from test results
    """

    def __init__(self, random_seed: Optional[int] = None):
        """Initialize the A/B testing engine."""
        self._tests: Dict[str, ABTest] = {}
        self._user_assignments: Dict[str, Dict[str, str]] = {}  # user_id -> {test_id: variant_id}
        self._results: Dict[str, TestResult] = {}

        if random_seed is not None:
            random.seed(random_seed)

    def create_test(
        self,
        name: str,
        description: str,
        variants: List[Dict[str, Any]],
        min_sample_size: int = 100,
        confidence_level: float = 0.95,
        primary_metric: str = "conversion_rate"
    ) -> ABTest:
        """
        Create a new A/B test.

        Implements ab_testing_integration.
        """
        # Create variant objects
        variant_objects = []
        total_weight = sum(v.get('weight', 1.0) for v in variants)

        for v in variants:
            variant = Variant(
                variant_id=str(uuid.uuid4()),
                name=v['name'],
                description=v.get('description', ''),
                config=v.get('config', {}),
                traffic_weight=v.get('weight', 1.0) / total_weight
            )
            variant_objects.append(variant)

        test = ABTest(
            test_id=str(uuid.uuid4()),
            name=name,
            description=description,
            variants=variant_objects,
            min_sample_size=min_sample_size,
            confidence_level=confidence_level,
            primary_metric=primary_metric
        )

        self._tests[test.test_id] = test
        logger.info(f"Created A/B test: {name} with {len(variant_objects)} variants")

        return test

    def start_test(self, test_id: str) -> bool:
        """Start an A/B test."""
        test = self._tests.get(test_id)
        if not test:
            return False

        if test.status == TestStatus.RUNNING:
            return True

        test.status = TestStatus.RUNNING
        test.start_date = datetime.utcnow()
        logger.info(f"Started A/B test: {test.name}")
        return True

    def stop_test(self, test_id: str) -> bool:
        """Stop an A/B test."""
        test = self._tests.get(test_id)
        if not test:
            return False

        test.status = TestStatus.COMPLETED
        test.end_date = datetime.utcnow()
        logger.info(f"Stopped A/B test: {test.name}")
        return True

    def get_variant(
        self,
        test_id: str,
        user_id: str
    ) -> Optional[Variant]:
        """
        Get the variant for a user in a test.

        Uses consistent assignment so user always sees same variant.
        """
        test = self._tests.get(test_id)
        if not test or test.status != TestStatus.RUNNING:
            return None

        # Check existing assignment
        if user_id in self._user_assignments:
            if test_id in self._user_assignments[user_id]:
                variant_id = self._user_assignments[user_id][test_id]
                for v in test.variants:
                    if v.variant_id == variant_id:
                        return v

        # Assign based on traffic weights
        rand = random.random()
        cumulative = 0.0

        for variant in test.variants:
            if variant.status != VariantStatus.ACTIVE:
                continue
            cumulative += variant.traffic_weight
            if rand <= cumulative:
                # Store assignment
                if user_id not in self._user_assignments:
                    self._user_assignments[user_id] = {}
                self._user_assignments[user_id][test_id] = variant.variant_id
                return variant

        return test.variants[0] if test.variants else None

    def record_impression(
        self,
        test_id: str,
        variant_id: str,
        user_id: str
    ) -> bool:
        """
        Record an impression for a variant.

        Implements usage_analytics.
        """
        test = self._tests.get(test_id)
        if not test:
            return False

        for variant in test.variants:
            if variant.variant_id == variant_id:
                variant.impressions += 1
                logger.debug(f"Impression recorded for variant {variant.name}")
                return True

        return False

    def record_conversion(
        self,
        test_id: str,
        variant_id: str,
        user_id: str,
        value: float = 1.0
    ) -> bool:
        """Record a conversion for a variant."""
        test = self._tests.get(test_id)
        if not test:
            return False

        for variant in test.variants:
            if variant.variant_id == variant_id:
                variant.conversions += 1
                logger.debug(f"Conversion recorded for variant {variant.name}")
                return True

        return False

    def record_custom_metric(
        self,
        test_id: str,
        variant_id: str,
        metric_name: str,
        value: float
    ) -> bool:
        """Record a custom metric for a variant."""
        test = self._tests.get(test_id)
        if not test:
            return False

        for variant in test.variants:
            if variant.variant_id == variant_id:
                if metric_name not in variant.custom_metrics:
                    variant.custom_metrics[metric_name] = 0.0
                variant.custom_metrics[metric_name] += value
                return True

        return False

    def analyze_test(self, test_id: str) -> Optional[TestResult]:
        """
        Analyze test results for statistical significance.

        Implements evolutionary_learning by determining winners.
        """
        test = self._tests.get(test_id)
        if not test:
            return None

        if len(test.variants) < 2:
            return None

        # Collect variant data
        variants_data = []
        for v in test.variants:
            variants_data.append({
                'variant_id': v.variant_id,
                'name': v.name,
                'impressions': v.impressions,
                'conversions': v.conversions,
                'conversion_rate': v.conversion_rate(),
                'custom_metrics': v.custom_metrics.copy()
            })

        # Calculate statistical significance using Z-test
        control = test.variants[0]
        treatment = test.variants[1]

        confidence, is_significant = self._calculate_significance(
            control.impressions, control.conversions,
            treatment.impressions, treatment.conversions,
            test.confidence_level
        )

        # Determine winner
        winner = None
        recommendation = "Test needs more data"

        if is_significant:
            if treatment.conversion_rate() > control.conversion_rate():
                winner = treatment.variant_id
                recommendation = f"Variant '{treatment.name}' is the winner. Consider promoting it."
            else:
                winner = control.variant_id
                recommendation = f"Control '{control.name}' performs better. Keep it."
        elif test.is_ready_for_analysis():
            recommendation = "No significant difference detected. Consider extending the test or declaring a tie."

        result = TestResult(
            test_id=test_id,
            winner=winner,
            confidence=confidence,
            variants_data=variants_data,
            is_significant=is_significant,
            recommendation=recommendation
        )

        self._results[test_id] = result

        # Update test winner
        if winner:
            test.winner_variant_id = winner
            for v in test.variants:
                if v.variant_id == winner:
                    v.status = VariantStatus.WINNER
                else:
                    v.status = VariantStatus.LOSER

        logger.info(f"Test analysis complete: significant={is_significant}, winner={winner}")
        return result

    def _calculate_significance(
        self,
        n1: int, c1: int,
        n2: int, c2: int,
        confidence_level: float
    ) -> Tuple[float, bool]:
        """Calculate statistical significance using Z-test."""
        if n1 == 0 or n2 == 0:
            return 0.0, False

        p1 = c1 / n1
        p2 = c2 / n2

        # Pooled proportion
        p_pooled = (c1 + c2) / (n1 + n2)

        # Standard error
        se = math.sqrt(p_pooled * (1 - p_pooled) * (1/n1 + 1/n2))

        if se == 0:
            return 0.0, False

        # Z-score
        z = abs(p1 - p2) / se

        # P-value approximation (two-tailed)
        # Using standard normal CDF approximation
        p_value = 2 * (1 - self._standard_normal_cdf(z))

        confidence = 1 - p_value
        is_significant = confidence >= confidence_level

        return confidence, is_significant

    def _standard_normal_cdf(self, x: float) -> float:
        """Approximate standard normal CDF."""
        return (1.0 + math.erf(x / math.sqrt(2.0))) / 2.0

    def get_test(self, test_id: str) -> Optional[ABTest]:
        """Get a test by ID."""
        return self._tests.get(test_id)

    def get_result(self, test_id: str) -> Optional[TestResult]:
        """Get analysis result for a test."""
        return self._results.get(test_id)

    def list_tests(
        self,
        status: Optional[TestStatus] = None
    ) -> List[ABTest]:
        """List all tests, optionally filtered by status."""
        tests = list(self._tests.values())
        if status:
            tests = [t for t in tests if t.status == status]
        return tests

    def get_analytics_summary(self, test_id: str) -> Dict[str, Any]:
        """
        Get analytics summary for a test.

        Implements usage_analytics reporting.
        """
        test = self._tests.get(test_id)
        if not test:
            return {}

        return {
            'test_id': test_id,
            'test_name': test.name,
            'status': test.status.value,
            'total_impressions': test.total_impressions(),
            'ready_for_analysis': test.is_ready_for_analysis(),
            'variants': [
                {
                    'name': v.name,
                    'impressions': v.impressions,
                    'conversions': v.conversions,
                    'conversion_rate': f"{v.conversion_rate() * 100:.2f}%",
                    'status': v.status.value
                }
                for v in test.variants
            ],
            'start_date': test.start_date.isoformat() if test.start_date else None,
            'winner': test.winner_variant_id
        }


# Factory function
def create_ab_testing_engine(random_seed: Optional[int] = None) -> ABTestingEngine:
    """Create a new ABTestingEngine instance."""
    return ABTestingEngine(random_seed=random_seed)
