"""
Enterprise Features Module for Maestro SDLC Phase 3.

This module provides enterprise-grade capabilities:
- Authentication (OAuth2, MFA, API Keys)
- Multi-tenancy isolation (RLS, Feature Flags)
- JIRA bidirectional sync
- Resilience patterns (Circuit Breaker, Compensation)
"""

from .auth import (
    OAuth2Provider,
    TokenManager,
    MFAProvider,
    APIKeyManager,
    PasswordHasher,
)
from .tenancy import (
    TenantRLS,
    TenantFeatureFlags,
    TenantContext,
)
from .jira_sync import (
    JIRASyncEngine,
    ConflictResolver,
    FieldMapper,
)
from .resilience import (
    CircuitBreaker,
    CompensationManager,
    TransactionContext,
)

__all__ = [
    # Auth
    "OAuth2Provider",
    "TokenManager",
    "MFAProvider",
    "APIKeyManager",
    "PasswordHasher",
    # Tenancy
    "TenantRLS",
    "TenantFeatureFlags",
    "TenantContext",
    # JIRA Sync
    "JIRASyncEngine",
    "ConflictResolver",
    "FieldMapper",
    # Resilience
    "CircuitBreaker",
    "CompensationManager",
    "TransactionContext",
]

__version__ = "1.0.0"
