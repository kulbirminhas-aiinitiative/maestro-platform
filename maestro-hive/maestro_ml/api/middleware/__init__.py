"""
API Middleware (rate limiting, metrics, logging, etc.)
"""

from .rate_limiter import RateLimitMiddleware, RateLimiter
from .metrics import (
    PrometheusMetricsMiddleware,
    record_model_operation,
    record_model_size,
    update_model_count,
    record_experiment,
    record_training_duration,
    record_feature_discovery,
    record_model_card_generation,
    update_tenant_quota_usage,
    update_tenant_active_users,
    record_rate_limit_exceeded,
    set_app_info
)

__all__ = [
    "RateLimitMiddleware",
    "RateLimiter",
    "PrometheusMetricsMiddleware",
    "record_model_operation",
    "record_model_size",
    "update_model_count",
    "record_experiment",
    "record_training_duration",
    "record_feature_discovery",
    "record_model_card_generation",
    "update_tenant_quota_usage",
    "update_tenant_active_users",
    "record_rate_limit_exceeded",
    "set_app_info"
]
