"""
Network Security Module for Maestro Platform.

This module provides infrastructure security capabilities including:
- Istio Service Mesh configuration and management
- mTLS (Mutual TLS) for service-to-service communication
- Zero Trust network architecture with AuthorizationPolicy
- Kubernetes NetworkPolicy management

Implements MD-2782: [Infrastructure] Service Mesh & Network Security
Parent: MD-1663
"""

from .service_mesh import (
    ServiceMeshConfig,
    IstioInstaller,
    IstioConfigManager,
    SidecarInjector,
)
from .mtls_manager import (
    MTLSManager,
    PeerAuthenticationPolicy,
    CertificateRotator,
    TLSMode,
)
from .zero_trust import (
    ZeroTrustPolicy,
    AuthorizationPolicyManager,
    JWTValidator,
    AccessRule,
)
from .network_policy import (
    NetworkPolicyManager,
    DefaultDenyPolicy,
    IngressRule,
    EgressRule,
    NamespaceIsolation,
)

__all__ = [
    # Service Mesh
    "ServiceMeshConfig",
    "IstioInstaller",
    "IstioConfigManager",
    "SidecarInjector",
    # mTLS
    "MTLSManager",
    "PeerAuthenticationPolicy",
    "CertificateRotator",
    "TLSMode",
    # Zero Trust
    "ZeroTrustPolicy",
    "AuthorizationPolicyManager",
    "JWTValidator",
    "AccessRule",
    # Network Policy
    "NetworkPolicyManager",
    "DefaultDenyPolicy",
    "IngressRule",
    "EgressRule",
    "NamespaceIsolation",
]

__version__ = "1.0.0"
__epic__ = "MD-2782"
