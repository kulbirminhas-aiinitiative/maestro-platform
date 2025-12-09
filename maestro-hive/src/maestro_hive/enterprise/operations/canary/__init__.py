"""
Canary Deployment Module - AC-3 Implementation.

Implements canary deployment with traffic splitting and automatic rollback.
"""

from .deployer import (
    CanaryDeployer,
    CanaryConfig,
    CanaryDeployment,
    CanaryStatus,
    TrafficSplit,
)
from .analyzer import (
    CanaryAnalyzer,
    CanaryMetrics,
    AnalysisResult,
    HealthCriteria,
)
from .traffic import (
    TrafficRouter,
    TrafficRule,
    WeightedRoute,
)

__all__ = [
    "CanaryDeployer",
    "CanaryConfig",
    "CanaryDeployment",
    "CanaryStatus",
    "TrafficSplit",
    "CanaryAnalyzer",
    "CanaryMetrics",
    "AnalysisResult",
    "HealthCriteria",
    "TrafficRouter",
    "TrafficRule",
    "WeightedRoute",
]
