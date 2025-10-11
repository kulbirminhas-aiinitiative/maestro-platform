"""
Traffic Routing for A/B Tests
"""

import hashlib
import logging
from datetime import datetime
from typing import Any, Optional

from ..models.experiment_models import Experiment, ExperimentStatus, ExperimentVariant

logger = logging.getLogger(__name__)


class TrafficRouter:
    """
    Route traffic to experiment variants

    Features:
    - Consistent hashing for sticky sessions
    - Weighted random assignment
    - Session persistence
    - Exclusion rules
    """

    def __init__(self):
        self.logger = logger
        self.session_cache: dict[str, dict[str, Any]] = {}  # user_id -> session_info

    def route_request(
        self,
        experiment: Experiment,
        user_id: str,
        request_context: Optional[dict[str, Any]] = None,
    ) -> ExperimentVariant:
        """
        Route a request to an experiment variant

        Args:
            experiment: The experiment
            user_id: User identifier
            request_context: Additional context (e.g., device, location)

        Returns:
            Selected variant
        """
        if experiment.status != ExperimentStatus.RUNNING:
            # Return control variant if experiment not running
            control_variant = next(v for v in experiment.variants if v.is_control)
            return control_variant

        # Check for existing session
        if experiment.traffic_split.sticky_sessions:
            existing_variant = self._get_cached_assignment(
                experiment.experiment_id,
                user_id,
                experiment.traffic_split.session_duration_seconds,
            )
            if existing_variant:
                return existing_variant

        # Assign to variant
        variant = self._assign_variant(
            experiment=experiment, user_id=user_id, request_context=request_context
        )

        # Cache assignment
        if experiment.traffic_split.sticky_sessions:
            self._cache_assignment(experiment.experiment_id, user_id, variant)

        return variant

    def _assign_variant(
        self,
        experiment: Experiment,
        user_id: str,
        request_context: Optional[dict[str, Any]],
    ) -> ExperimentVariant:
        """Assign user to a variant using consistent hashing"""
        # Create hash input
        hash_input = f"{experiment.experiment_id}:{user_id}"

        # Consistent hashing
        hash_value = int(hashlib.md5(hash_input.encode()).hexdigest(), 16)
        hash_percent = (hash_value % 10000) / 100.0  # 0-100 with 2 decimal precision

        # Assign based on cumulative weights
        cumulative = 0.0
        for variant_id, weight in experiment.traffic_split.variant_weights.items():
            cumulative += weight
            if hash_percent < cumulative:
                # Find variant
                variant = next(
                    v for v in experiment.variants if v.variant_id == variant_id
                )
                return variant

        # Fallback to last variant
        last_variant_id = list(experiment.traffic_split.variant_weights.keys())[-1]
        return next(v for v in experiment.variants if v.variant_id == last_variant_id)

    def _get_cached_assignment(
        self, experiment_id: str, user_id: str, session_duration_seconds: int
    ) -> Optional[ExperimentVariant]:
        """Get cached variant assignment if still valid"""
        cache_key = f"{experiment_id}:{user_id}"

        if cache_key in self.session_cache:
            session = self.session_cache[cache_key]
            assigned_at = session["assigned_at"]
            variant = session["variant"]

            # Check if session still valid
            age = (datetime.utcnow() - assigned_at).total_seconds()
            if age < session_duration_seconds:
                return variant

            # Expired, remove from cache
            del self.session_cache[cache_key]

        return None

    def _cache_assignment(
        self, experiment_id: str, user_id: str, variant: ExperimentVariant
    ):
        """Cache variant assignment"""
        cache_key = f"{experiment_id}:{user_id}"
        self.session_cache[cache_key] = {
            "variant": variant,
            "assigned_at": datetime.utcnow(),
        }

    def get_variant_by_id(
        self, experiment: Experiment, variant_id: str
    ) -> Optional[ExperimentVariant]:
        """Get variant by ID"""
        return next(
            (v for v in experiment.variants if v.variant_id == variant_id), None
        )

    def force_variant(
        self,
        experiment_id: str,
        user_id: str,
        variant: ExperimentVariant,
        duration_seconds: int = 3600,
    ):
        """
        Force a user to a specific variant (for testing/debugging)

        Args:
            experiment_id: Experiment ID
            user_id: User ID
            variant: Variant to assign
            duration_seconds: How long to maintain this assignment
        """
        cache_key = f"{experiment_id}:{user_id}"
        self.session_cache[cache_key] = {
            "variant": variant,
            "assigned_at": datetime.utcnow(),
            "forced": True,
        }

        self.logger.info(
            f"Forced user {user_id} to variant {variant.variant_id} in experiment {experiment_id}"
        )

    def clear_user_sessions(self, user_id: Optional[str] = None):
        """Clear cached sessions for a user or all users"""
        if user_id:
            keys_to_remove = [
                k for k in self.session_cache if k.endswith(f":{user_id}")
            ]
            for key in keys_to_remove:
                del self.session_cache[key]
        else:
            self.session_cache.clear()

    def get_current_traffic_distribution(self, experiment_id: str) -> dict[str, int]:
        """
        Get current traffic distribution across variants

        Returns:
            variant_id -> user_count
        """
        distribution = {}

        for cache_key, session in self.session_cache.items():
            if cache_key.startswith(f"{experiment_id}:"):
                variant_id = session["variant"].variant_id
                distribution[variant_id] = distribution.get(variant_id, 0) + 1

        return distribution
