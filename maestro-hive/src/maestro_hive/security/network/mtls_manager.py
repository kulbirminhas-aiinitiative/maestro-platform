"""
mTLS (Mutual TLS) Manager Module - AC-2: mTLS implementation for service-to-service communication.

This module provides comprehensive mTLS management capabilities including:
- PeerAuthentication policy management for namespace/workload mTLS
- Certificate rotation monitoring and management
- TLS mode configuration (STRICT, PERMISSIVE, DISABLE)
- SPIFFE identity verification

Implements: MD-2782 AC-2
"""

import logging
import subprocess
import json
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class TLSMode(Enum):
    """mTLS enforcement modes."""
    STRICT = "STRICT"          # Only mutual TLS traffic is allowed
    PERMISSIVE = "PERMISSIVE"  # Both plaintext and mutual TLS accepted
    DISABLE = "DISABLE"        # mTLS disabled for this scope
    UNSET = "UNSET"           # Inherit from parent


class PortLevelMTLS(Enum):
    """Port-specific mTLS settings."""
    STRICT = "STRICT"
    PERMISSIVE = "PERMISSIVE"
    DISABLE = "DISABLE"


@dataclass
class PeerAuthenticationPolicy:
    """Istio PeerAuthentication policy configuration."""
    name: str
    namespace: str
    mtls_mode: TLSMode = TLSMode.STRICT
    selector: Optional[dict] = None
    port_level_mtls: dict[int, PortLevelMTLS] = field(default_factory=dict)

    def to_manifest(self) -> dict:
        """Generate PeerAuthentication Kubernetes manifest."""
        manifest = {
            "apiVersion": "security.istio.io/v1beta1",
            "kind": "PeerAuthentication",
            "metadata": {
                "name": self.name,
                "namespace": self.namespace,
            },
            "spec": {
                "mtls": {
                    "mode": self.mtls_mode.value
                }
            }
        }

        # Add workload selector if specified
        if self.selector:
            manifest["spec"]["selector"] = {
                "matchLabels": self.selector
            }

        # Add port-level mTLS settings
        if self.port_level_mtls:
            manifest["spec"]["portLevelMtls"] = {
                str(port): {"mode": mode.value}
                for port, mode in self.port_level_mtls.items()
            }

        return manifest

    def to_yaml(self) -> str:
        """Generate PeerAuthentication YAML."""
        import yaml
        return yaml.dump(self.to_manifest(), default_flow_style=False)


@dataclass
class DestinationRuleTLS:
    """DestinationRule TLS settings for client-side mTLS."""
    name: str
    namespace: str
    host: str
    tls_mode: str = "ISTIO_MUTUAL"
    sni: Optional[str] = None
    client_certificate: Optional[str] = None
    private_key: Optional[str] = None
    ca_certificates: Optional[str] = None

    def to_manifest(self) -> dict:
        """Generate DestinationRule manifest with TLS settings."""
        tls_settings = {"mode": self.tls_mode}

        if self.sni:
            tls_settings["sni"] = self.sni
        if self.client_certificate:
            tls_settings["clientCertificate"] = self.client_certificate
        if self.private_key:
            tls_settings["privateKey"] = self.private_key
        if self.ca_certificates:
            tls_settings["caCertificates"] = self.ca_certificates

        return {
            "apiVersion": "networking.istio.io/v1beta1",
            "kind": "DestinationRule",
            "metadata": {
                "name": self.name,
                "namespace": self.namespace,
            },
            "spec": {
                "host": self.host,
                "trafficPolicy": {
                    "tls": tls_settings
                }
            }
        }


@dataclass
class CertificateInfo:
    """Certificate information for mTLS."""
    subject: str
    issuer: str
    serial_number: str
    not_before: datetime
    not_after: datetime
    spiffe_id: Optional[str] = None

    @property
    def is_valid(self) -> bool:
        """Check if certificate is currently valid."""
        now = datetime.utcnow()
        return self.not_before <= now <= self.not_after

    @property
    def days_until_expiry(self) -> int:
        """Get days until certificate expiry."""
        now = datetime.utcnow()
        delta = self.not_after - now
        return delta.days


class MTLSManager:
    """Manages mTLS configuration and policies."""

    def __init__(self, kubeconfig: Optional[str] = None):
        """Initialize mTLS manager.

        Args:
            kubeconfig: Path to kubeconfig file.
        """
        self.kubeconfig = kubeconfig
        self._istioctl_path: Optional[str] = None

    def _run_kubectl(self, args: list[str], input_data: Optional[str] = None) -> subprocess.CompletedProcess:
        """Run kubectl command."""
        cmd = ["kubectl"] + args
        if self.kubeconfig:
            cmd.extend(["--kubeconfig", self.kubeconfig])
        return subprocess.run(cmd, capture_output=True, text=True, input=input_data)

    def _run_istioctl(self, args: list[str]) -> subprocess.CompletedProcess:
        """Run istioctl command."""
        cmd = ["istioctl"] + args
        if self.kubeconfig:
            cmd.extend(["--kubeconfig", self.kubeconfig])
        return subprocess.run(cmd, capture_output=True, text=True)

    def enable_strict_mtls(self, namespace: str, name: str = "default") -> dict[str, Any]:
        """Enable STRICT mTLS for a namespace.

        Args:
            namespace: Target namespace.
            name: Policy name.

        Returns:
            Result of the operation.
        """
        policy = PeerAuthenticationPolicy(
            name=name,
            namespace=namespace,
            mtls_mode=TLSMode.STRICT,
        )

        result = self.apply_peer_authentication(policy)
        logger.info(f"Enabled STRICT mTLS for namespace: {namespace}")
        return result

    def enable_permissive_mtls(self, namespace: str, name: str = "default") -> dict[str, Any]:
        """Enable PERMISSIVE mTLS for a namespace (migration mode).

        Args:
            namespace: Target namespace.
            name: Policy name.
        """
        policy = PeerAuthenticationPolicy(
            name=name,
            namespace=namespace,
            mtls_mode=TLSMode.PERMISSIVE,
        )

        result = self.apply_peer_authentication(policy)
        logger.info(f"Enabled PERMISSIVE mTLS for namespace: {namespace}")
        return result

    def apply_peer_authentication(self, policy: PeerAuthenticationPolicy) -> dict[str, Any]:
        """Apply a PeerAuthentication policy.

        Args:
            policy: PeerAuthenticationPolicy configuration.
        """
        manifest = json.dumps(policy.to_manifest())
        result = self._run_kubectl(
            ["apply", "-f", "-"],
            input_data=manifest
        )

        return {
            "success": result.returncode == 0,
            "name": policy.name,
            "namespace": policy.namespace,
            "mtls_mode": policy.mtls_mode.value,
            "output": result.stdout or result.stderr,
        }

    def get_peer_authentications(self, namespace: str = "") -> list[dict]:
        """Get PeerAuthentication policies.

        Args:
            namespace: Namespace to query. Empty string for all namespaces.
        """
        args = ["get", "peerauthentication"]
        if namespace:
            args.extend(["-n", namespace])
        else:
            args.append("-A")
        args.extend(["-o", "json"])

        result = self._run_kubectl(args)

        if result.returncode != 0:
            logger.error(f"Failed to get PeerAuthentications: {result.stderr}")
            return []

        try:
            data = json.loads(result.stdout)
            return [
                {
                    "name": item["metadata"]["name"],
                    "namespace": item["metadata"]["namespace"],
                    "mtls_mode": item.get("spec", {}).get("mtls", {}).get("mode", "UNSET"),
                    "selector": item.get("spec", {}).get("selector"),
                }
                for item in data.get("items", [])
            ]
        except json.JSONDecodeError:
            logger.error("Failed to parse PeerAuthentication JSON")
            return []

    def delete_peer_authentication(self, name: str, namespace: str) -> dict[str, Any]:
        """Delete a PeerAuthentication policy.

        Args:
            name: Policy name.
            namespace: Policy namespace.
        """
        result = self._run_kubectl([
            "delete", "peerauthentication", name, "-n", namespace
        ])

        return {
            "success": result.returncode == 0,
            "name": name,
            "namespace": namespace,
            "output": result.stdout or result.stderr,
        }

    def check_tls_status(self, pod: str, namespace: str) -> dict[str, Any]:
        """Check mTLS status for a specific pod.

        Args:
            pod: Pod name.
            namespace: Pod namespace.
        """
        result = self._run_istioctl([
            "authn", "tls-check", f"{pod}.{namespace}"
        ])

        return {
            "pod": pod,
            "namespace": namespace,
            "tls_status": result.stdout if result.returncode == 0 else None,
            "error": result.stderr if result.returncode != 0 else None,
        }

    def get_mesh_mtls_status(self) -> dict[str, Any]:
        """Get overall mesh mTLS status."""
        # Get mesh-wide PeerAuthentication
        mesh_policies = self.get_peer_authentications("istio-system")

        # Check for default policy
        default_policy = next(
            (p for p in mesh_policies if p["name"] == "default"),
            None
        )

        return {
            "mesh_mtls_enabled": default_policy is not None,
            "mesh_mtls_mode": default_policy["mtls_mode"] if default_policy else "PERMISSIVE",
            "policies_count": len(mesh_policies),
            "policies": mesh_policies,
        }


class CertificateRotator:
    """Manages certificate rotation for mTLS."""

    def __init__(self, kubeconfig: Optional[str] = None):
        """Initialize certificate rotator.

        Args:
            kubeconfig: Path to kubeconfig file.
        """
        self.kubeconfig = kubeconfig

    def _run_kubectl(self, args: list[str]) -> subprocess.CompletedProcess:
        """Run kubectl command."""
        cmd = ["kubectl"] + args
        if self.kubeconfig:
            cmd.extend(["--kubeconfig", self.kubeconfig])
        return subprocess.run(cmd, capture_output=True, text=True)

    def get_root_cert_expiry(self) -> Optional[datetime]:
        """Get the expiry date of the Istio root certificate."""
        result = self._run_kubectl([
            "get", "secret", "istio-ca-secret",
            "-n", "istio-system",
            "-o", "jsonpath={.data.ca-cert\\.pem}"
        ])

        if result.returncode != 0:
            logger.error("Failed to get root certificate")
            return None

        # Note: In production, decode and parse the certificate
        # This is a simplified implementation
        logger.info("Root certificate retrieved successfully")
        return None

    def check_workload_certs(self, namespace: str) -> list[dict]:
        """Check workload certificate status in a namespace.

        Args:
            namespace: Namespace to check.
        """
        # Get pods with istio-proxy
        result = self._run_kubectl([
            "get", "pods", "-n", namespace,
            "-l", "security.istio.io/tlsMode=istio",
            "-o", "json"
        ])

        if result.returncode != 0:
            return []

        try:
            pods_data = json.loads(result.stdout)
            cert_status = []

            for pod in pods_data.get("items", []):
                pod_name = pod["metadata"]["name"]
                cert_status.append({
                    "pod": pod_name,
                    "namespace": namespace,
                    "mtls_enabled": True,  # Has the label
                    "status": pod.get("status", {}).get("phase"),
                })

            return cert_status
        except json.JSONDecodeError:
            return []

    def trigger_cert_rotation(self, namespace: str = "istio-system") -> dict[str, Any]:
        """Trigger certificate rotation by restarting Istiod.

        Note: In production, use Istio's automatic rotation or external CA.

        Args:
            namespace: Istio system namespace.
        """
        result = self._run_kubectl([
            "rollout", "restart", "deployment/istiod",
            "-n", namespace
        ])

        return {
            "success": result.returncode == 0,
            "action": "cert_rotation_triggered",
            "output": result.stdout or result.stderr,
        }

    def get_cert_chain_info(self, pod: str, namespace: str) -> dict[str, Any]:
        """Get certificate chain information for a pod.

        Args:
            pod: Pod name.
            namespace: Pod namespace.
        """
        # Use istioctl to get proxy config
        cmd = ["istioctl"] + [
            "proxy-config", "secret", f"{pod}.{namespace}",
            "-o", "json"
        ]
        if self.kubeconfig:
            cmd.extend(["--kubeconfig", self.kubeconfig])

        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            return {
                "pod": pod,
                "namespace": namespace,
                "error": result.stderr,
            }

        try:
            data = json.loads(result.stdout)
            return {
                "pod": pod,
                "namespace": namespace,
                "secrets": data,
            }
        except json.JSONDecodeError:
            return {
                "pod": pod,
                "namespace": namespace,
                "raw_output": result.stdout,
            }


class SPIFFEValidator:
    """Validates SPIFFE identities for mTLS."""

    SPIFFE_ID_PREFIX = "spiffe://cluster.local/ns/"

    def __init__(self, trust_domain: str = "cluster.local"):
        """Initialize SPIFFE validator.

        Args:
            trust_domain: SPIFFE trust domain.
        """
        self.trust_domain = trust_domain

    def generate_spiffe_id(self, namespace: str, service_account: str) -> str:
        """Generate expected SPIFFE ID for a workload.

        Args:
            namespace: Kubernetes namespace.
            service_account: Service account name.
        """
        return f"spiffe://{self.trust_domain}/ns/{namespace}/sa/{service_account}"

    def validate_spiffe_id(self, spiffe_id: str) -> dict[str, Any]:
        """Validate a SPIFFE ID format.

        Args:
            spiffe_id: SPIFFE ID to validate.
        """
        if not spiffe_id.startswith("spiffe://"):
            return {
                "valid": False,
                "error": "Invalid SPIFFE ID prefix",
            }

        parts = spiffe_id.replace("spiffe://", "").split("/")

        if len(parts) < 4 or parts[1] != "ns" or parts[3] != "sa":
            return {
                "valid": False,
                "error": "Invalid SPIFFE ID format",
            }

        return {
            "valid": True,
            "trust_domain": parts[0],
            "namespace": parts[2],
            "service_account": parts[4] if len(parts) > 4 else None,
        }

    def parse_spiffe_id(self, spiffe_id: str) -> Optional[dict]:
        """Parse SPIFFE ID into components.

        Args:
            spiffe_id: SPIFFE ID to parse.
        """
        validation = self.validate_spiffe_id(spiffe_id)
        if not validation["valid"]:
            return None

        return {
            "trust_domain": validation["trust_domain"],
            "namespace": validation["namespace"],
            "service_account": validation["service_account"],
        }
