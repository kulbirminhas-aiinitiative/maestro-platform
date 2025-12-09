"""
Automated Rollback Triggers.

Monitors conditions and triggers automatic rollbacks.
"""

import asyncio
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Optional

from .strategy import RollbackStrategy, Deployment, RollbackType
from .health_check import HealthChecker, HealthStatus


class ConditionType(str, Enum):
    """Types of rollback conditions."""
    ERROR_RATE = "error_rate"
    LATENCY = "latency"
    HEALTH_CHECK = "health_check"
    METRIC_THRESHOLD = "metric_threshold"
    CUSTOM = "custom"


class ComparisonOperator(str, Enum):
    """Comparison operators for conditions."""
    GREATER_THAN = "gt"
    LESS_THAN = "lt"
    EQUALS = "eq"
    NOT_EQUALS = "ne"
    GREATER_THAN_OR_EQUAL = "gte"
    LESS_THAN_OR_EQUAL = "lte"


@dataclass
class RollbackCondition:
    """Condition that triggers rollback."""
    name: str
    condition_type: ConditionType
    metric: str
    operator: ComparisonOperator
    threshold: float
    duration_seconds: int = 60
    enabled: bool = True
    description: str = ""

    def evaluate(self, value: float) -> bool:
        """Evaluate condition against value."""
        if self.operator == ComparisonOperator.GREATER_THAN:
            return value > self.threshold
        elif self.operator == ComparisonOperator.LESS_THAN:
            return value < self.threshold
        elif self.operator == ComparisonOperator.EQUALS:
            return value == self.threshold
        elif self.operator == ComparisonOperator.NOT_EQUALS:
            return value != self.threshold
        elif self.operator == ComparisonOperator.GREATER_THAN_OR_EQUAL:
            return value >= self.threshold
        elif self.operator == ComparisonOperator.LESS_THAN_OR_EQUAL:
            return value <= self.threshold
        return False

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "type": self.condition_type.value,
            "metric": self.metric,
            "operator": self.operator.value,
            "threshold": self.threshold,
            "duration_seconds": self.duration_seconds,
            "enabled": self.enabled,
            "description": self.description
        }


@dataclass
class AutoRollbackTrigger:
    """Trigger for automatic rollback."""
    id: str
    environment: str
    conditions: list[RollbackCondition]
    strategy: RollbackType = RollbackType.IMMEDIATE
    cooldown_seconds: int = 300
    max_rollbacks: int = 3
    notification_channels: list[str] = field(default_factory=list)
    enabled: bool = True

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "environment": self.environment,
            "conditions": [c.to_dict() for c in self.conditions],
            "strategy": self.strategy.value,
            "cooldown_seconds": self.cooldown_seconds,
            "max_rollbacks": self.max_rollbacks,
            "notification_channels": self.notification_channels,
            "enabled": self.enabled
        }


@dataclass
class RollbackEvent:
    """Record of a rollback event."""
    trigger_id: str
    deployment_id: str
    condition_name: str
    triggered_at: datetime
    metric_value: float
    threshold: float
    rollback_executed: bool
    error: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "trigger_id": self.trigger_id,
            "deployment_id": self.deployment_id,
            "condition_name": self.condition_name,
            "triggered_at": self.triggered_at.isoformat(),
            "metric_value": self.metric_value,
            "threshold": self.threshold,
            "rollback_executed": self.rollback_executed,
            "error": self.error
        }


class RollbackAutomation:
    """Manages automated rollback triggers and execution."""

    def __init__(
        self,
        rollback_strategy: Optional[RollbackStrategy] = None,
        health_checker: Optional[HealthChecker] = None
    ):
        self.rollback_strategy = rollback_strategy or RollbackStrategy()
        self.health_checker = health_checker or HealthChecker()
        self._triggers: dict[str, AutoRollbackTrigger] = {}
        self._events: list[RollbackEvent] = []
        self._cooldowns: dict[str, datetime] = {}
        self._rollback_counts: dict[str, int] = {}
        self._metric_providers: dict[str, Callable] = {}
        self._running = False

    def register_trigger(self, trigger: AutoRollbackTrigger) -> None:
        """Register auto-rollback trigger."""
        self._triggers[trigger.id] = trigger
        self._rollback_counts[trigger.id] = 0

    def unregister_trigger(self, trigger_id: str) -> bool:
        """Unregister trigger."""
        if trigger_id in self._triggers:
            del self._triggers[trigger_id]
            return True
        return False

    def register_metric_provider(self, metric: str, provider: Callable) -> None:
        """Register function to provide metric values."""
        self._metric_providers[metric] = provider

    async def check_triggers(self, deployment: Deployment) -> Optional[RollbackEvent]:
        """Check all triggers for deployment."""
        for trigger in self._triggers.values():
            if not trigger.enabled:
                continue

            if trigger.environment != deployment.environment:
                continue

            # Check cooldown
            if self._in_cooldown(trigger.id):
                continue

            # Check max rollbacks
            if self._rollback_counts.get(trigger.id, 0) >= trigger.max_rollbacks:
                continue

            # Evaluate conditions
            for condition in trigger.conditions:
                if not condition.enabled:
                    continue

                value = await self._get_metric_value(condition.metric)
                if condition.evaluate(value):
                    event = await self._execute_rollback(
                        trigger, deployment, condition, value
                    )
                    return event

        return None

    async def _get_metric_value(self, metric: str) -> float:
        """Get current value for metric."""
        if metric == "error_rate":
            return 0.0  # Simulated
        elif metric == "latency_p99":
            return 50.0  # Simulated
        elif metric == "health_check_failures":
            health = await self.health_checker.check_all()
            return float(health.unhealthy_count)

        provider = self._metric_providers.get(metric)
        if provider:
            return await provider()

        return 0.0

    async def _execute_rollback(
        self,
        trigger: AutoRollbackTrigger,
        deployment: Deployment,
        condition: RollbackCondition,
        metric_value: float
    ) -> RollbackEvent:
        """Execute automatic rollback."""
        event = RollbackEvent(
            trigger_id=trigger.id,
            deployment_id=deployment.id,
            condition_name=condition.name,
            triggered_at=datetime.utcnow(),
            metric_value=metric_value,
            threshold=condition.threshold,
            rollback_executed=False
        )

        try:
            self.rollback_strategy.strategy_type = trigger.strategy
            result = await self.rollback_strategy.execute(deployment)

            if result.status == "completed":
                event.rollback_executed = True
                self._rollback_counts[trigger.id] = \
                    self._rollback_counts.get(trigger.id, 0) + 1
                self._cooldowns[trigger.id] = datetime.utcnow()
            else:
                event.error = result.error

        except Exception as e:
            event.error = str(e)

        self._events.append(event)
        return event

    def _in_cooldown(self, trigger_id: str) -> bool:
        """Check if trigger is in cooldown period."""
        if trigger_id not in self._cooldowns:
            return False

        trigger = self._triggers.get(trigger_id)
        if not trigger:
            return False

        elapsed = (datetime.utcnow() - self._cooldowns[trigger_id]).total_seconds()
        return elapsed < trigger.cooldown_seconds

    async def start_monitoring(self, deployment: Deployment) -> None:
        """Start continuous monitoring for deployment."""
        self._running = True
        while self._running:
            await self.check_triggers(deployment)
            await asyncio.sleep(10)  # Check every 10 seconds

    def stop_monitoring(self) -> None:
        """Stop monitoring."""
        self._running = False

    def get_events(self, trigger_id: Optional[str] = None) -> list[RollbackEvent]:
        """Get rollback events."""
        if trigger_id:
            return [e for e in self._events if e.trigger_id == trigger_id]
        return self._events

    def reset_cooldown(self, trigger_id: str) -> None:
        """Reset cooldown for trigger."""
        self._cooldowns.pop(trigger_id, None)

    def reset_rollback_count(self, trigger_id: str) -> None:
        """Reset rollback count for trigger."""
        self._rollback_counts[trigger_id] = 0
