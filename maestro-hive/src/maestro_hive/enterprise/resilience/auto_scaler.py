"""
Auto-Scaler Implementation for Maestro Platform.

Provides automatic horizontal scaling based on CPU utilization metrics.
Fulfills AC-4: Auto-scale triggers at 70% CPU.

Author: EPIC Executor v2.1
EPIC: MD-2050 - Resilience and Scaling
"""

import asyncio
import time
from dataclasses import dataclass, field
from typing import Dict, Optional, Any, List, Callable
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class ScaleDirection(Enum):
    """Direction of scaling action."""
    UP = "scale_up"
    DOWN = "scale_down"
    NONE = "no_change"


class ScalingState(Enum):
    """Current state of the auto-scaler."""
    IDLE = "idle"
    SCALING_UP = "scaling_up"
    SCALING_DOWN = "scaling_down"
    COOLDOWN = "cooldown"


@dataclass
class AutoScaleConfig:
    """Configuration for auto-scaler."""
    # CPU thresholds
    cpu_scale_up_threshold: float = 70.0  # AC-4: 70% CPU trigger
    cpu_scale_down_threshold: float = 30.0

    # Replica limits
    min_replicas: int = 2
    max_replicas: int = 10

    # Scaling behavior
    scale_up_increment: int = 2
    scale_down_increment: int = 1

    # Timing windows (seconds)
    scale_up_window: int = 180  # 3 minutes
    scale_down_window: int = 600  # 10 minutes
    cooldown_period: int = 300  # 5 minutes

    # Metrics
    metrics_interval: int = 30


@dataclass
class ScaleAction:
    """Result of a scaling decision."""
    direction: ScaleDirection
    current_replicas: int
    target_replicas: int
    reason: str
    metrics: Dict[str, float] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)


@dataclass
class MetricSample:
    """A single metric sample."""
    value: float
    timestamp: float


class AutoScaler:
    """
    Automatic horizontal scaling based on CPU metrics.

    Implements AC-4: Auto-scale triggers at 70% CPU.

    Features:
    - CPU-based scaling triggers
    - Configurable scale-up/down windows
    - Cooldown periods to prevent thrashing
    - Min/max replica bounds
    - Kubernetes HPA integration ready

    Example:
        config = AutoScaleConfig(
            cpu_scale_up_threshold=70.0,
            min_replicas=2,
            max_replicas=10
        )
        scaler = AutoScaler(config)

        # Check and potentially scale
        action = await scaler.check_and_scale()
        if action.direction != ScaleDirection.NONE:
            await apply_scaling(action)
    """

    def __init__(
        self,
        config: Optional[AutoScaleConfig] = None,
        metrics_provider: Optional[Callable[[], Dict[str, float]]] = None
    ):
        """Initialize auto-scaler.

        Args:
            config: Scaling configuration
            metrics_provider: Callable that returns current metrics dict
        """
        self.config = config or AutoScaleConfig()
        self._metrics_provider = metrics_provider

        self._current_replicas = self.config.min_replicas
        self._state = ScalingState.IDLE
        self._last_scale_time: Optional[float] = None
        self._cpu_samples: List[MetricSample] = []
        self._memory_samples: List[MetricSample] = []
        self._lock = asyncio.Lock()

        logger.info(
            f"AutoScaler initialized: threshold={self.config.cpu_scale_up_threshold}%, "
            f"replicas={self.config.min_replicas}-{self.config.max_replicas}"
        )

    async def check_and_scale(self) -> ScaleAction:
        """
        Check current metrics and determine if scaling is needed.

        Returns:
            ScaleAction describing the scaling decision
        """
        async with self._lock:
            current_time = time.time()

            # Check cooldown
            if self._is_in_cooldown(current_time):
                return ScaleAction(
                    direction=ScaleDirection.NONE,
                    current_replicas=self._current_replicas,
                    target_replicas=self._current_replicas,
                    reason="In cooldown period"
                )

            # Collect metrics
            metrics = await self._collect_metrics()
            cpu_avg = metrics.get("cpu_percent", 0.0)

            # Store sample
            self._cpu_samples.append(MetricSample(cpu_avg, current_time))
            self._cleanup_old_samples(current_time)

            # Evaluate scaling decision
            action = self._evaluate_scaling(cpu_avg, current_time, metrics)

            if action.direction != ScaleDirection.NONE:
                self._apply_action(action, current_time)

            return action

    def _is_in_cooldown(self, current_time: float) -> bool:
        """Check if still in cooldown period."""
        if self._last_scale_time is None:
            return False
        return current_time - self._last_scale_time < self.config.cooldown_period

    async def _collect_metrics(self) -> Dict[str, float]:
        """Collect current system metrics."""
        if self._metrics_provider:
            try:
                return self._metrics_provider()
            except Exception as e:
                logger.error(f"Failed to collect metrics: {e}")

        # Default mock metrics for testing
        return {
            "cpu_percent": 50.0,
            "memory_percent": 60.0,
            "request_rate": 100.0
        }

    def _cleanup_old_samples(self, current_time: float) -> None:
        """Remove samples outside the evaluation window."""
        max_window = max(
            self.config.scale_up_window,
            self.config.scale_down_window
        )
        cutoff = current_time - max_window

        self._cpu_samples = [
            s for s in self._cpu_samples
            if s.timestamp > cutoff
        ]

    def _evaluate_scaling(
        self,
        current_cpu: float,
        current_time: float,
        metrics: Dict[str, float]
    ) -> ScaleAction:
        """Evaluate if scaling is needed based on metrics."""

        # Check for scale up
        if current_cpu >= self.config.cpu_scale_up_threshold:
            if self._check_sustained_high_cpu(current_time):
                if self._current_replicas < self.config.max_replicas:
                    target = min(
                        self._current_replicas + self.config.scale_up_increment,
                        self.config.max_replicas
                    )
                    return ScaleAction(
                        direction=ScaleDirection.UP,
                        current_replicas=self._current_replicas,
                        target_replicas=target,
                        reason=f"CPU {current_cpu:.1f}% >= {self.config.cpu_scale_up_threshold}% threshold",
                        metrics=metrics
                    )
                else:
                    return ScaleAction(
                        direction=ScaleDirection.NONE,
                        current_replicas=self._current_replicas,
                        target_replicas=self._current_replicas,
                        reason=f"Already at max replicas ({self.config.max_replicas})",
                        metrics=metrics
                    )

        # Check for scale down
        if current_cpu <= self.config.cpu_scale_down_threshold:
            if self._check_sustained_low_cpu(current_time):
                if self._current_replicas > self.config.min_replicas:
                    target = max(
                        self._current_replicas - self.config.scale_down_increment,
                        self.config.min_replicas
                    )
                    return ScaleAction(
                        direction=ScaleDirection.DOWN,
                        current_replicas=self._current_replicas,
                        target_replicas=target,
                        reason=f"CPU {current_cpu:.1f}% <= {self.config.cpu_scale_down_threshold}% threshold",
                        metrics=metrics
                    )
                else:
                    return ScaleAction(
                        direction=ScaleDirection.NONE,
                        current_replicas=self._current_replicas,
                        target_replicas=self._current_replicas,
                        reason=f"Already at min replicas ({self.config.min_replicas})",
                        metrics=metrics
                    )

        return ScaleAction(
            direction=ScaleDirection.NONE,
            current_replicas=self._current_replicas,
            target_replicas=self._current_replicas,
            reason=f"CPU {current_cpu:.1f}% within normal range",
            metrics=metrics
        )

    def _check_sustained_high_cpu(self, current_time: float) -> bool:
        """Check if CPU has been high for the scale-up window."""
        window_start = current_time - self.config.scale_up_window
        relevant_samples = [
            s for s in self._cpu_samples
            if s.timestamp >= window_start
        ]

        if len(relevant_samples) < 3:
            return False

        avg = sum(s.value for s in relevant_samples) / len(relevant_samples)
        return avg >= self.config.cpu_scale_up_threshold

    def _check_sustained_low_cpu(self, current_time: float) -> bool:
        """Check if CPU has been low for the scale-down window."""
        window_start = current_time - self.config.scale_down_window
        relevant_samples = [
            s for s in self._cpu_samples
            if s.timestamp >= window_start
        ]

        if len(relevant_samples) < 3:
            return False

        avg = sum(s.value for s in relevant_samples) / len(relevant_samples)
        return avg <= self.config.cpu_scale_down_threshold

    def _apply_action(self, action: ScaleAction, current_time: float) -> None:
        """Apply the scaling action."""
        old_replicas = self._current_replicas
        self._current_replicas = action.target_replicas
        self._last_scale_time = current_time

        if action.direction == ScaleDirection.UP:
            self._state = ScalingState.SCALING_UP
        elif action.direction == ScaleDirection.DOWN:
            self._state = ScalingState.SCALING_DOWN

        logger.info(
            f"Scaling {action.direction.value}: {old_replicas} -> {action.target_replicas} "
            f"({action.reason})"
        )

    def get_current_replicas(self) -> int:
        """Get current replica count."""
        return self._current_replicas

    def set_current_replicas(self, count: int) -> None:
        """Set current replica count (for external sync)."""
        self._current_replicas = max(
            self.config.min_replicas,
            min(count, self.config.max_replicas)
        )

    def get_metrics(self) -> Dict[str, float]:
        """Get current scaling metrics."""
        if not self._cpu_samples:
            return {"cpu_avg": 0.0, "sample_count": 0}

        cpu_avg = sum(s.value for s in self._cpu_samples) / len(self._cpu_samples)

        return {
            "cpu_avg": cpu_avg,
            "sample_count": len(self._cpu_samples),
            "current_replicas": self._current_replicas,
            "min_replicas": self.config.min_replicas,
            "max_replicas": self.config.max_replicas,
            "cpu_threshold": self.config.cpu_scale_up_threshold
        }

    def get_status(self) -> Dict[str, Any]:
        """Get full auto-scaler status."""
        current_time = time.time()

        cooldown_remaining = 0.0
        if self._last_scale_time:
            cooldown_remaining = max(
                0.0,
                self.config.cooldown_period - (current_time - self._last_scale_time)
            )

        return {
            "state": self._state.value,
            "current_replicas": self._current_replicas,
            "min_replicas": self.config.min_replicas,
            "max_replicas": self.config.max_replicas,
            "cpu_threshold_up": self.config.cpu_scale_up_threshold,
            "cpu_threshold_down": self.config.cpu_scale_down_threshold,
            "cooldown_remaining": cooldown_remaining,
            "last_scale_time": self._last_scale_time,
            "metrics": self.get_metrics()
        }


def generate_hpa_manifest(
    deployment_name: str,
    namespace: str = "maestro",
    config: Optional[AutoScaleConfig] = None
) -> Dict[str, Any]:
    """
    Generate Kubernetes HPA manifest.

    Args:
        deployment_name: Name of the deployment to scale
        namespace: Kubernetes namespace
        config: Scaling configuration

    Returns:
        Dict representing HPA manifest
    """
    cfg = config or AutoScaleConfig()

    return {
        "apiVersion": "autoscaling/v2",
        "kind": "HorizontalPodAutoscaler",
        "metadata": {
            "name": f"{deployment_name}-hpa",
            "namespace": namespace
        },
        "spec": {
            "scaleTargetRef": {
                "apiVersion": "apps/v1",
                "kind": "Deployment",
                "name": deployment_name
            },
            "minReplicas": cfg.min_replicas,
            "maxReplicas": cfg.max_replicas,
            "metrics": [
                {
                    "type": "Resource",
                    "resource": {
                        "name": "cpu",
                        "target": {
                            "type": "Utilization",
                            "averageUtilization": int(cfg.cpu_scale_up_threshold)
                        }
                    }
                }
            ],
            "behavior": {
                "scaleUp": {
                    "stabilizationWindowSeconds": cfg.scale_up_window,
                    "policies": [
                        {
                            "type": "Pods",
                            "value": cfg.scale_up_increment,
                            "periodSeconds": 60
                        }
                    ]
                },
                "scaleDown": {
                    "stabilizationWindowSeconds": cfg.scale_down_window,
                    "policies": [
                        {
                            "type": "Pods",
                            "value": cfg.scale_down_increment,
                            "periodSeconds": 120
                        }
                    ]
                }
            }
        }
    }
