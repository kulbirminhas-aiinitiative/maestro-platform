"""
Traffic Router Implementation.

Manages traffic splitting between stable and canary versions.
"""

import uuid
from datetime import datetime
from dataclasses import dataclass, field
from typing import Any, Optional
from enum import Enum


class RouteType(str, Enum):
    """Traffic route type."""
    WEIGHTED = "weighted"
    HEADER = "header"
    COOKIE = "cookie"
    QUERY_PARAM = "query_param"


@dataclass
class WeightedRoute:
    """Weighted traffic route."""
    version: str
    weight: int
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "weight": self.weight,
            "metadata": self.metadata,
        }


@dataclass
class TrafficRule:
    """Traffic routing rule."""
    id: str
    service: str
    route_type: RouteType
    routes: list[WeightedRoute]
    priority: int = 0
    enabled: bool = True
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "service": self.service,
            "route_type": self.route_type.value,
            "routes": [r.to_dict() for r in self.routes],
            "priority": self.priority,
            "enabled": self.enabled,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "metadata": self.metadata,
        }

    def get_weight(self, version: str) -> int:
        """Get weight for a version."""
        for route in self.routes:
            if route.version == version:
                return route.weight
        return 0

    def set_weight(self, version: str, weight: int) -> None:
        """Set weight for a version."""
        for route in self.routes:
            if route.version == version:
                route.weight = weight
                self.updated_at = datetime.utcnow()
                return

        # Add new route
        self.routes.append(WeightedRoute(version=version, weight=weight))
        self.updated_at = datetime.utcnow()


class TrafficRouter:
    """Manages traffic routing between versions."""

    def __init__(self):
        self._rules: dict[str, TrafficRule] = {}
        self._rules_by_service: dict[str, list[str]] = {}

    def create_rule(
        self,
        service: str,
        stable_version: str,
        canary_version: str,
        canary_weight: int = 5,
        route_type: RouteType = RouteType.WEIGHTED,
    ) -> TrafficRule:
        """Create a traffic routing rule."""
        if canary_weight < 0 or canary_weight > 100:
            raise ValueError("Weight must be between 0 and 100")

        rule = TrafficRule(
            id=str(uuid.uuid4()),
            service=service,
            route_type=route_type,
            routes=[
                WeightedRoute(version=stable_version, weight=100 - canary_weight),
                WeightedRoute(version=canary_version, weight=canary_weight),
            ],
        )

        self._rules[rule.id] = rule

        if service not in self._rules_by_service:
            self._rules_by_service[service] = []
        self._rules_by_service[service].append(rule.id)

        return rule

    def get_rule(self, rule_id: str) -> Optional[TrafficRule]:
        """Get rule by ID."""
        return self._rules.get(rule_id)

    def get_rules_for_service(self, service: str) -> list[TrafficRule]:
        """Get all rules for a service."""
        rule_ids = self._rules_by_service.get(service, [])
        return [self._rules[rid] for rid in rule_ids if rid in self._rules]

    def update_weights(
        self,
        rule_id: str,
        stable_weight: int,
        canary_weight: int,
    ) -> TrafficRule:
        """Update traffic weights."""
        if stable_weight + canary_weight != 100:
            raise ValueError("Weights must sum to 100")

        rule = self._rules.get(rule_id)
        if not rule:
            raise ValueError(f"Rule not found: {rule_id}")

        # Update weights
        for route in rule.routes:
            if route.weight == max(r.weight for r in rule.routes):
                route.weight = stable_weight
            else:
                route.weight = canary_weight

        rule.updated_at = datetime.utcnow()
        return rule

    def shift_traffic(
        self,
        rule_id: str,
        to_version: str,
        increment: int = 10,
    ) -> TrafficRule:
        """Shift traffic towards a version."""
        rule = self._rules.get(rule_id)
        if not rule:
            raise ValueError(f"Rule not found: {rule_id}")

        target_route = None
        other_routes = []

        for route in rule.routes:
            if route.version == to_version:
                target_route = route
            else:
                other_routes.append(route)

        if not target_route:
            raise ValueError(f"Version not found in rule: {to_version}")

        # Calculate new weight
        new_weight = min(target_route.weight + increment, 100)
        remaining = 100 - new_weight

        # Distribute remaining weight
        if other_routes:
            per_route = remaining // len(other_routes)
            for route in other_routes:
                route.weight = per_route

            # Handle remainder
            other_routes[0].weight += remaining - (per_route * len(other_routes))

        target_route.weight = new_weight
        rule.updated_at = datetime.utcnow()

        return rule

    def promote_version(self, rule_id: str, version: str) -> TrafficRule:
        """Promote a version to 100% traffic."""
        rule = self._rules.get(rule_id)
        if not rule:
            raise ValueError(f"Rule not found: {rule_id}")

        for route in rule.routes:
            route.weight = 100 if route.version == version else 0

        rule.updated_at = datetime.utcnow()
        return rule

    def rollback_to_stable(self, rule_id: str) -> TrafficRule:
        """Rollback all traffic to stable."""
        rule = self._rules.get(rule_id)
        if not rule:
            raise ValueError(f"Rule not found: {rule_id}")

        # Assume first route is stable
        for i, route in enumerate(rule.routes):
            route.weight = 100 if i == 0 else 0

        rule.updated_at = datetime.utcnow()
        return rule

    def delete_rule(self, rule_id: str) -> bool:
        """Delete a traffic rule."""
        rule = self._rules.get(rule_id)
        if not rule:
            return False

        del self._rules[rule_id]

        if rule.service in self._rules_by_service:
            self._rules_by_service[rule.service] = [
                rid for rid in self._rules_by_service[rule.service]
                if rid != rule_id
            ]

        return True

    def enable_rule(self, rule_id: str) -> TrafficRule:
        """Enable a traffic rule."""
        rule = self._rules.get(rule_id)
        if not rule:
            raise ValueError(f"Rule not found: {rule_id}")

        rule.enabled = True
        rule.updated_at = datetime.utcnow()
        return rule

    def disable_rule(self, rule_id: str) -> TrafficRule:
        """Disable a traffic rule."""
        rule = self._rules.get(rule_id)
        if not rule:
            raise ValueError(f"Rule not found: {rule_id}")

        rule.enabled = False
        rule.updated_at = datetime.utcnow()
        return rule

    def get_routing_decision(self, service: str) -> dict[str, Any]:
        """Get current routing decision for a service."""
        rules = self.get_rules_for_service(service)
        enabled_rules = [r for r in rules if r.enabled]

        if not enabled_rules:
            return {"service": service, "routing": "default", "rules": []}

        # Sort by priority
        enabled_rules.sort(key=lambda r: r.priority, reverse=True)

        return {
            "service": service,
            "routing": "weighted",
            "rules": [r.to_dict() for r in enabled_rules],
            "active_rule": enabled_rules[0].to_dict() if enabled_rules else None,
        }

    def list_all_rules(self) -> list[TrafficRule]:
        """List all traffic rules."""
        return list(self._rules.values())

    def get_stats(self) -> dict[str, Any]:
        """Get traffic router statistics."""
        total_rules = len(self._rules)
        enabled_rules = sum(1 for r in self._rules.values() if r.enabled)
        services_count = len(self._rules_by_service)

        return {
            "total_rules": total_rules,
            "enabled_rules": enabled_rules,
            "disabled_rules": total_rules - enabled_rules,
            "services_count": services_count,
            "services": list(self._rules_by_service.keys()),
        }
