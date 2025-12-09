"""
Per-Tenant Feature Flags.

Implements feature flag management with tenant-level overrides
and A/B testing support.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict, Any, Union
from enum import Enum
import hashlib
import json


class FlagStatus(Enum):
    """Feature flag status."""
    ENABLED = "enabled"
    DISABLED = "disabled"
    PERCENTAGE = "percentage"  # Percentage rollout
    VARIANT = "variant"  # A/B testing


@dataclass
class FlagVariant:
    """A/B test variant configuration."""
    name: str
    weight: int  # Weight for distribution (0-100)
    payload: Optional[Dict[str, Any]] = None


@dataclass
class FeatureFlag:
    """Feature flag definition."""
    name: str
    description: str = ""
    default_status: FlagStatus = FlagStatus.DISABLED
    percentage: int = 0  # For percentage rollouts
    variants: List[FlagVariant] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class TenantFlagOverride:
    """Tenant-specific flag override."""
    tenant_id: str
    flag_name: str
    status: FlagStatus
    percentage: Optional[int] = None
    forced_variant: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class FlagEvaluationResult:
    """Result of flag evaluation."""
    flag_name: str
    is_enabled: bool
    variant: Optional[str] = None
    variant_payload: Optional[Dict[str, Any]] = None
    reason: str = ""  # Why this value was returned


class TenantFeatureFlags:
    """
    Per-tenant feature flag management.

    Supports:
    - Global flags with tenant overrides
    - Percentage-based rollouts
    - A/B testing with variants
    - Sticky assignments for consistency
    """

    def __init__(self, storage=None):
        """
        Initialize feature flags manager.

        Args:
            storage: Optional storage backend
        """
        self._flags: Dict[str, FeatureFlag] = {}
        self._tenant_overrides: Dict[str, Dict[str, TenantFlagOverride]] = {}
        self._user_assignments: Dict[str, Dict[str, str]] = {}  # user_id -> flag -> variant
        self.storage = storage

    def create_flag(
        self,
        name: str,
        description: str = "",
        default_enabled: bool = False,
        variants: Optional[List[FlagVariant]] = None,
    ) -> FeatureFlag:
        """
        Create new feature flag.

        Args:
            name: Unique flag name
            description: Flag description
            default_enabled: Default enabled state
            variants: A/B test variants

        Returns:
            Created FeatureFlag
        """
        flag = FeatureFlag(
            name=name,
            description=description,
            default_status=FlagStatus.ENABLED if default_enabled else FlagStatus.DISABLED,
            variants=variants or [],
        )

        self._flags[name] = flag
        return flag

    def set_flag_percentage(
        self,
        flag_name: str,
        percentage: int,
    ) -> None:
        """
        Set percentage rollout for flag.

        Args:
            flag_name: Flag name
            percentage: Rollout percentage (0-100)
        """
        if flag_name not in self._flags:
            raise ValueError(f"Flag not found: {flag_name}")

        flag = self._flags[flag_name]
        flag.default_status = FlagStatus.PERCENTAGE
        flag.percentage = max(0, min(100, percentage))
        flag.updated_at = datetime.utcnow()

    def set_tenant_override(
        self,
        tenant_id: str,
        flag_name: str,
        enabled: bool,
        percentage: Optional[int] = None,
        forced_variant: Optional[str] = None,
    ) -> TenantFlagOverride:
        """
        Set tenant-specific flag override.

        Args:
            tenant_id: Tenant ID
            flag_name: Flag name
            enabled: Override enabled state
            percentage: Tenant-specific percentage
            forced_variant: Force specific variant

        Returns:
            Created override
        """
        if tenant_id not in self._tenant_overrides:
            self._tenant_overrides[tenant_id] = {}

        status = FlagStatus.ENABLED if enabled else FlagStatus.DISABLED
        if percentage is not None:
            status = FlagStatus.PERCENTAGE

        override = TenantFlagOverride(
            tenant_id=tenant_id,
            flag_name=flag_name,
            status=status,
            percentage=percentage,
            forced_variant=forced_variant,
        )

        self._tenant_overrides[tenant_id][flag_name] = override
        return override

    def remove_tenant_override(
        self,
        tenant_id: str,
        flag_name: str,
    ) -> bool:
        """
        Remove tenant override, reverting to global flag value.

        Args:
            tenant_id: Tenant ID
            flag_name: Flag name

        Returns:
            True if override was removed
        """
        if tenant_id in self._tenant_overrides:
            if flag_name in self._tenant_overrides[tenant_id]:
                del self._tenant_overrides[tenant_id][flag_name]
                return True
        return False

    def _compute_hash_bucket(
        self,
        identifier: str,
        flag_name: str,
    ) -> int:
        """
        Compute consistent hash bucket for percentage/variant assignment.

        Args:
            identifier: User or tenant ID
            flag_name: Flag name

        Returns:
            Bucket number 0-99
        """
        hash_input = f"{identifier}:{flag_name}"
        hash_value = hashlib.md5(hash_input.encode()).hexdigest()
        return int(hash_value[:8], 16) % 100

    def _select_variant(
        self,
        flag: FeatureFlag,
        identifier: str,
    ) -> Optional[FlagVariant]:
        """
        Select variant based on weights.

        Args:
            flag: Feature flag
            identifier: User/tenant ID for consistent assignment

        Returns:
            Selected variant or None
        """
        if not flag.variants:
            return None

        # Check for sticky assignment
        if identifier in self._user_assignments:
            assigned = self._user_assignments[identifier].get(flag.name)
            if assigned:
                for variant in flag.variants:
                    if variant.name == assigned:
                        return variant

        # Compute new assignment
        bucket = self._compute_hash_bucket(identifier, flag.name)

        cumulative = 0
        for variant in flag.variants:
            cumulative += variant.weight
            if bucket < cumulative:
                # Store sticky assignment
                if identifier not in self._user_assignments:
                    self._user_assignments[identifier] = {}
                self._user_assignments[identifier][flag.name] = variant.name
                return variant

        return flag.variants[-1] if flag.variants else None

    def is_enabled(
        self,
        flag_name: str,
        tenant_id: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> bool:
        """
        Check if flag is enabled.

        Args:
            flag_name: Flag name
            tenant_id: Tenant ID for overrides
            user_id: User ID for percentage rollouts

        Returns:
            True if flag is enabled
        """
        result = self.evaluate(flag_name, tenant_id, user_id)
        return result.is_enabled

    def evaluate(
        self,
        flag_name: str,
        tenant_id: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> FlagEvaluationResult:
        """
        Evaluate flag with full context.

        Args:
            flag_name: Flag name
            tenant_id: Tenant ID
            user_id: User ID

        Returns:
            FlagEvaluationResult with evaluation details
        """
        # Check if flag exists
        flag = self._flags.get(flag_name)
        if not flag:
            return FlagEvaluationResult(
                flag_name=flag_name,
                is_enabled=False,
                reason="flag_not_found",
            )

        # Check for tenant override
        if tenant_id:
            override = self._tenant_overrides.get(tenant_id, {}).get(flag_name)
            if override:
                if override.forced_variant:
                    for variant in flag.variants:
                        if variant.name == override.forced_variant:
                            return FlagEvaluationResult(
                                flag_name=flag_name,
                                is_enabled=True,
                                variant=variant.name,
                                variant_payload=variant.payload,
                                reason="tenant_override_variant",
                            )

                if override.status == FlagStatus.ENABLED:
                    return FlagEvaluationResult(
                        flag_name=flag_name,
                        is_enabled=True,
                        reason="tenant_override_enabled",
                    )
                elif override.status == FlagStatus.DISABLED:
                    return FlagEvaluationResult(
                        flag_name=flag_name,
                        is_enabled=False,
                        reason="tenant_override_disabled",
                    )
                elif override.status == FlagStatus.PERCENTAGE:
                    identifier = user_id or tenant_id
                    bucket = self._compute_hash_bucket(identifier, flag_name)
                    enabled = bucket < override.percentage
                    return FlagEvaluationResult(
                        flag_name=flag_name,
                        is_enabled=enabled,
                        reason=f"tenant_override_percentage_{override.percentage}",
                    )

        # Evaluate global flag
        if flag.default_status == FlagStatus.ENABLED:
            # Check for variants
            if flag.variants:
                identifier = user_id or tenant_id or "default"
                variant = self._select_variant(flag, identifier)
                if variant:
                    return FlagEvaluationResult(
                        flag_name=flag_name,
                        is_enabled=True,
                        variant=variant.name,
                        variant_payload=variant.payload,
                        reason="global_variant",
                    )
            return FlagEvaluationResult(
                flag_name=flag_name,
                is_enabled=True,
                reason="global_enabled",
            )

        elif flag.default_status == FlagStatus.DISABLED:
            return FlagEvaluationResult(
                flag_name=flag_name,
                is_enabled=False,
                reason="global_disabled",
            )

        elif flag.default_status == FlagStatus.PERCENTAGE:
            identifier = user_id or tenant_id or "default"
            bucket = self._compute_hash_bucket(identifier, flag_name)
            enabled = bucket < flag.percentage
            return FlagEvaluationResult(
                flag_name=flag_name,
                is_enabled=enabled,
                reason=f"global_percentage_{flag.percentage}",
            )

        return FlagEvaluationResult(
            flag_name=flag_name,
            is_enabled=False,
            reason="unknown_status",
        )

    def get_all_flags(
        self,
        tenant_id: Optional[str] = None,
    ) -> Dict[str, FlagEvaluationResult]:
        """
        Get all flags with evaluations.

        Args:
            tenant_id: Tenant ID for overrides

        Returns:
            Dictionary of flag name to evaluation result
        """
        results = {}
        for flag_name in self._flags:
            results[flag_name] = self.evaluate(flag_name, tenant_id)
        return results

    def get_tenant_overrides(
        self,
        tenant_id: str,
    ) -> List[TenantFlagOverride]:
        """
        Get all overrides for a tenant.

        Args:
            tenant_id: Tenant ID

        Returns:
            List of tenant overrides
        """
        overrides = self._tenant_overrides.get(tenant_id, {})
        return list(overrides.values())
