#!/usr/bin/env python3
"""
Template Lifecycle Management - Prevents Template Explosion

Controls:
1. Maximum template limits per persona/category
2. Template retirement based on fitness scores
3. Consolidation detection (merge similar templates)
4. Coverage saturation (stop when good enough)
5. Recommendation limits

Author: Claude Code
Date: 2025-10-10
"""

import asyncio
import logging
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict

logger = logging.getLogger(__name__)


# =============================================================================
# DATA MODELS
# =============================================================================

@dataclass
class TemplateLifecyclePolicy:
    """Policies to prevent template explosion"""

    # Maximum limits
    max_templates_per_persona: int = 25
    max_templates_per_category: int = 50
    max_recommendations_per_run: int = 20

    # Coverage thresholds (stop recommending when reached)
    target_coverage_percent: float = 80.0
    saturation_coverage_percent: float = 90.0  # Stop completely at this level

    # Retirement thresholds
    min_fitness_score: float = 40.0  # Retire templates below this
    days_unused_before_retirement: int = 90

    # Consolidation thresholds
    consolidation_similarity_threshold: float = 0.90  # Merge if 90%+ similar
    min_templates_for_consolidation: int = 5  # Only consolidate if >=5 exist


@dataclass
class RetirementRecommendation:
    """Recommendation to retire a template"""
    template_id: str
    template_name: str
    reason: str
    fitness_score: float
    last_used_days_ago: int
    confidence: float


@dataclass
class ConsolidationRecommendation:
    """Recommendation to merge similar templates"""
    consolidation_id: str
    template_ids: List[str]
    template_names: List[str]
    reason: str
    similarity_scores: List[float]
    suggested_merged_name: str
    confidence: float


@dataclass
class LifecycleReport:
    """Report on template lifecycle status"""
    total_templates: int
    templates_by_persona: Dict[str, int]
    templates_by_category: Dict[str, int]

    # Health metrics
    templates_above_fitness_threshold: int
    templates_below_fitness_threshold: int
    templates_unused_90days: int

    # Recommendations
    retirement_recommendations: List[RetirementRecommendation] = field(default_factory=list)
    consolidation_recommendations: List[ConsolidationRecommendation] = field(default_factory=list)

    # Limits status
    personas_at_max_limit: List[str] = field(default_factory=list)
    categories_at_max_limit: List[str] = field(default_factory=list)

    # Coverage status
    current_coverage: float = 0.0
    coverage_saturated: bool = False
    should_stop_recommending: bool = False


# =============================================================================
# TEMPLATE LIFECYCLE MANAGER
# =============================================================================

class TemplateLifecycleManager:
    """
    Manages template lifecycle to prevent explosion

    Responsibilities:
    1. Enforce maximum template limits
    2. Identify templates for retirement
    3. Detect consolidation opportunities
    4. Monitor coverage saturation
    5. Control recommendation flow
    """

    def __init__(self, policy: Optional[TemplateLifecyclePolicy] = None):
        self.policy = policy or TemplateLifecyclePolicy()
        self.templates_cache: List[Dict] = []
        self.usage_stats: Dict[str, Dict] = {}

    async def initialize(self, templates: List[Dict]):
        """Initialize with template data"""
        self.templates_cache = templates
        logger.info(f"📊 Template Lifecycle Manager initialized with {len(templates)} templates")

    async def analyze_lifecycle(
        self,
        current_coverage: float,
        similarity_analyzer=None
    ) -> LifecycleReport:
        """
        Analyze template lifecycle and generate recommendations

        Returns:
            Report with retirement and consolidation recommendations
        """
        logger.info("🔍 Analyzing template lifecycle...")

        # Count templates by persona/category
        templates_by_persona = defaultdict(int)
        templates_by_category = defaultdict(int)

        for template in self.templates_cache:
            persona = template.get("persona", "unknown")
            category = template.get("category", "unknown")
            templates_by_persona[persona] += 1
            templates_by_category[category] += 1

        report = LifecycleReport(
            total_templates=len(self.templates_cache),
            templates_by_persona=dict(templates_by_persona),
            templates_by_category=dict(templates_by_category),
            templates_above_fitness_threshold=0,
            templates_below_fitness_threshold=0,
            templates_unused_90days=0,
            current_coverage=current_coverage
        )

        # Check coverage saturation
        if current_coverage >= self.policy.saturation_coverage_percent:
            report.coverage_saturated = True
            report.should_stop_recommending = True
            logger.info(f"   ✅ Coverage saturated at {current_coverage:.1f}% (target: {self.policy.saturation_coverage_percent}%)")
        elif current_coverage >= self.policy.target_coverage_percent:
            report.should_stop_recommending = False
            logger.info(f"   📊 Coverage at target {current_coverage:.1f}% (continuing monitoring)")

        # Check for personas/categories at max limit
        for persona, count in templates_by_persona.items():
            if count >= self.policy.max_templates_per_persona:
                report.personas_at_max_limit.append(persona)
                logger.warning(f"   ⚠️  Persona '{persona}' at max limit ({count}/{self.policy.max_templates_per_persona})")

        for category, count in templates_by_category.items():
            if count >= self.policy.max_templates_per_category:
                report.categories_at_max_limit.append(category)
                logger.warning(f"   ⚠️  Category '{category}' at max limit ({count}/{self.policy.max_templates_per_category})")

        # Identify retirement candidates (would need real fitness scores)
        # For now, this is a placeholder
        report.retirement_recommendations = await self._identify_retirement_candidates()

        # Identify consolidation opportunities
        if similarity_analyzer and len(self.templates_cache) >= self.policy.min_templates_for_consolidation:
            report.consolidation_recommendations = await self._identify_consolidation_opportunities(similarity_analyzer)

        logger.info(f"   ✅ Lifecycle analysis complete:")
        logger.info(f"      Retirement candidates: {len(report.retirement_recommendations)}")
        logger.info(f"      Consolidation opportunities: {len(report.consolidation_recommendations)}")
        logger.info(f"      Personas at max: {len(report.personas_at_max_limit)}")
        logger.info(f"      Categories at max: {len(report.categories_at_max_limit)}")

        return report

    async def _identify_retirement_candidates(self) -> List[RetirementRecommendation]:
        """Identify templates that should be retired"""
        recommendations = []

        # TODO: Implement with real fitness scores and usage tracking
        # For now, return empty list
        # In production, this would:
        # 1. Check fitness scores from TemplateFitnessScorer
        # 2. Check last_used_date from usage tracking
        # 3. Generate retirement recommendations

        return recommendations

    async def _identify_consolidation_opportunities(
        self,
        similarity_analyzer
    ) -> List[ConsolidationRecommendation]:
        """Identify templates that could be merged"""
        recommendations = []
        checked_pairs = set()

        # Compare templates pairwise
        for i, template1 in enumerate(self.templates_cache):
            for j, template2 in enumerate(self.templates_cache[i+1:], start=i+1):
                pair_key = tuple(sorted([template1.get('id'), template2.get('id')]))

                if pair_key in checked_pairs:
                    continue
                checked_pairs.add(pair_key)

                # Check if same persona
                if template1.get('persona') != template2.get('persona'):
                    continue

                # Calculate similarity
                text1 = f"{template1.get('name', '')} {template1.get('description', '')}"
                text2 = f"{template2.get('name', '')} {template2.get('description', '')}"

                # Would need actual similarity calculation here
                # For now, skip implementation

        return recommendations

    def should_recommend_for_persona(self, persona: str) -> Tuple[bool, str]:
        """
        Check if we should recommend more templates for this persona

        Returns:
            (should_recommend, reason)
        """
        count = sum(1 for t in self.templates_cache if t.get('persona') == persona)

        if count >= self.policy.max_templates_per_persona:
            return False, f"Persona '{persona}' at maximum limit ({count}/{self.policy.max_templates_per_persona})"

        return True, ""

    def should_recommend_for_category(self, category: str) -> Tuple[bool, str]:
        """
        Check if we should recommend more templates for this category

        Returns:
            (should_recommend, reason)
        """
        count = sum(1 for t in self.templates_cache if t.get('category') == category)

        if count >= self.policy.max_templates_per_category:
            return False, f"Category '{category}' at maximum limit ({count}/{self.policy.max_templates_per_category})"

        return True, ""

    def filter_recommendations(
        self,
        recommendations: List,
        lifecycle_report: LifecycleReport
    ) -> List:
        """
        Filter recommendations based on lifecycle policies

        Removes recommendations for:
        - Personas at max limit
        - Categories at max limit
        - When coverage is saturated
        """
        if lifecycle_report.should_stop_recommending:
            logger.info("   🛑 Coverage saturated - stopping all recommendations")
            return []

        filtered = []
        removed_count = 0

        for rec in recommendations:
            persona = rec.persona if hasattr(rec, 'persona') else None
            category = rec.category if hasattr(rec, 'category') else None

            # Check persona limit
            if persona and persona in lifecycle_report.personas_at_max_limit:
                removed_count += 1
                continue

            # Check category limit
            if category and category in lifecycle_report.categories_at_max_limit:
                removed_count += 1
                continue

            filtered.append(rec)

        if removed_count > 0:
            logger.info(f"   🗑️  Filtered out {removed_count} recommendations (max limits reached)")

        # Apply max recommendations per run
        if len(filtered) > self.policy.max_recommendations_per_run:
            logger.info(f"   ✂️  Truncating to {self.policy.max_recommendations_per_run} recommendations (policy limit)")
            filtered = filtered[:self.policy.max_recommendations_per_run]

        return filtered


# =============================================================================
# EXAMPLE USAGE
# =============================================================================

async def main():
    """Example usage"""

    # Create policy
    policy = TemplateLifecyclePolicy(
        max_templates_per_persona=25,
        max_templates_per_category=50,
        max_recommendations_per_run=20,
        target_coverage_percent=80.0,
        saturation_coverage_percent=90.0
    )

    # Create manager
    manager = TemplateLifecycleManager(policy)

    # Initialize with templates (example)
    templates = [
        {"id": "1", "name": "Test 1", "persona": "backend_developer", "category": "backend"},
        {"id": "2", "name": "Test 2", "persona": "backend_developer", "category": "backend"},
    ]
    await manager.initialize(templates)

    # Analyze lifecycle
    report = await manager.analyze_lifecycle(current_coverage=32.0)

    print(f"Total templates: {report.total_templates}")
    print(f"Should stop recommending: {report.should_stop_recommending}")
    print(f"Personas at max: {report.personas_at_max_limit}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
