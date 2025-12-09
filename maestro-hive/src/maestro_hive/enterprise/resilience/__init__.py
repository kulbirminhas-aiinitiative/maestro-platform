"""
Resilience Module for enterprise features.

Provides:
- Circuit breaker pattern
- Compensation/rollback logic
- Transaction semantics
- Rate limiting (AC-3: 1000 req/min per user)
- Auto-scaling (AC-4: 70% CPU trigger)
"""

from .circuit_breaker import (
    CircuitBreaker,
    CircuitState,
    CircuitBreakerConfig,
    CircuitBreakerError,
)
from .compensation import (
    CompensationManager,
    CompensationAction,
    CompensationResult,
    Saga,
)
from .transaction import (
    TransactionContext,
    TransactionStep,
    TransactionStatus,
    DistributedTransaction,
)
from .rate_limiter import (
    RateLimiter,
    RateLimiterConfig,
    RateLimitResult,
    RateLimitStrategy,
    RateLimitExceeded,
    rate_limited,
)
from .auto_scaler import (
    AutoScaler,
    AutoScaleConfig,
    ScaleAction,
    ScaleDirection,
    ScalingState,
    generate_hpa_manifest,
)

__all__ = [
    # Circuit Breaker
    "CircuitBreaker",
    "CircuitState",
    "CircuitBreakerConfig",
    "CircuitBreakerError",
    # Compensation
    "CompensationManager",
    "CompensationAction",
    "CompensationResult",
    "Saga",
    # Transaction
    "TransactionContext",
    "TransactionStep",
    "TransactionStatus",
    "DistributedTransaction",
    # Rate Limiter (AC-3)
    "RateLimiter",
    "RateLimiterConfig",
    "RateLimitResult",
    "RateLimitStrategy",
    "RateLimitExceeded",
    "rate_limited",
    # Auto-Scaler (AC-4)
    "AutoScaler",
    "AutoScaleConfig",
    "ScaleAction",
    "ScaleDirection",
    "ScalingState",
    "generate_hpa_manifest",
]
