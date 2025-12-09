"""
Operations Module - SDLC Phase 6: Deployment & Operations.

Provides comprehensive deployment and operations infrastructure including:
- CI/CD Pipeline orchestration
- Environment management
- Deployment rollback
- Operations monitoring

EPIC: MD-2520
"""

from .cicd import (
    PipelineOrchestrator,
    PipelineStage,
    PipelineConfig,
    PipelineTrigger,
    PipelineResult,
    QualityGate,
    GateRule,
    GateResult,
    ArtifactManager,
)
from .environments import (
    EnvironmentManager,
    EnvironmentConfig,
    Environment,
    PromotionResult,
    SecretManager,
)
from .rollback import (
    RollbackStrategy,
    RollbackResult,
    HealthChecker,
    HealthEndpoint,
    HealthStatus,
    AutoRollbackTrigger,
)
from .monitoring import (
    MetricsCollector,
    MetricsBackend,
    Metric,
    MetricQuery,
    MetricResult,
    AlertManager,
    AlertRule,
    Alert,
    NotificationChannel,
    IncidentManager,
    Incident,
)

__all__ = [
    # CI/CD
    "PipelineOrchestrator",
    "PipelineStage",
    "PipelineConfig",
    "PipelineTrigger",
    "PipelineResult",
    "QualityGate",
    "GateRule",
    "GateResult",
    "ArtifactManager",
    # Environments
    "EnvironmentManager",
    "EnvironmentConfig",
    "Environment",
    "PromotionResult",
    "SecretManager",
    # Rollback
    "RollbackStrategy",
    "RollbackResult",
    "HealthChecker",
    "HealthEndpoint",
    "HealthStatus",
    "AutoRollbackTrigger",
    # Monitoring
    "MetricsCollector",
    "MetricsBackend",
    "Metric",
    "MetricQuery",
    "MetricResult",
    "AlertManager",
    "AlertRule",
    "Alert",
    "NotificationChannel",
    "IncidentManager",
    "Incident",
]

__version__ = "1.0.0"
__epic__ = "MD-2520"
