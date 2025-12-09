"""
Service Mesh Configuration Module - AC-1: Istio Service Mesh installation and configuration.

This module provides comprehensive Istio Service Mesh management capabilities including:
- Istio installation with configurable profiles
- Sidecar injection management
- Traffic management via VirtualServices and DestinationRules
- Gateway configuration for ingress/egress

Implements: MD-2782 AC-1
"""

import logging
import subprocess
import json
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class IstioProfile(Enum):
    """Istio installation profiles."""
    DEFAULT = "default"
    DEMO = "demo"
    MINIMAL = "minimal"
    PRODUCTION = "production"
    EMPTY = "empty"


class TrafficPolicy(Enum):
    """Traffic management policies."""
    ROUND_ROBIN = "ROUND_ROBIN"
    LEAST_CONN = "LEAST_CONN"
    RANDOM = "RANDOM"
    PASSTHROUGH = "PASSTHROUGH"


@dataclass
class IstioConfig:
    """Configuration for Istio installation."""
    profile: IstioProfile = IstioProfile.PRODUCTION
    namespace: str = "istio-system"
    enable_tracing: bool = True
    enable_access_logging: bool = True
    proxy_cpu_request: str = "100m"
    proxy_memory_request: str = "128Mi"
    proxy_cpu_limit: str = "2000m"
    proxy_memory_limit: str = "1024Mi"
    pilot_replicas: int = 2
    ingress_enabled: bool = True
    egress_enabled: bool = True

    def to_yaml(self) -> str:
        """Generate IstioOperator YAML configuration."""
        return f"""apiVersion: install.istio.io/v1alpha1
kind: IstioOperator
metadata:
  namespace: {self.namespace}
spec:
  profile: {self.profile.value}
  meshConfig:
    accessLogFile: /dev/stdout
    enableTracing: {str(self.enable_tracing).lower()}
  components:
    pilot:
      k8s:
        replicaCount: {self.pilot_replicas}
    ingressGateways:
    - name: istio-ingressgateway
      enabled: {str(self.ingress_enabled).lower()}
    egressGateways:
    - name: istio-egressgateway
      enabled: {str(self.egress_enabled).lower()}
  values:
    global:
      proxy:
        resources:
          requests:
            cpu: {self.proxy_cpu_request}
            memory: {self.proxy_memory_request}
          limits:
            cpu: {self.proxy_cpu_limit}
            memory: {self.proxy_memory_limit}
"""


@dataclass
class VirtualService:
    """Istio VirtualService configuration."""
    name: str
    namespace: str
    hosts: list[str]
    http_routes: list[dict] = field(default_factory=list)
    gateways: list[str] = field(default_factory=list)

    def to_manifest(self) -> dict:
        """Generate VirtualService manifest."""
        manifest = {
            "apiVersion": "networking.istio.io/v1beta1",
            "kind": "VirtualService",
            "metadata": {
                "name": self.name,
                "namespace": self.namespace,
            },
            "spec": {
                "hosts": self.hosts,
            }
        }
        if self.gateways:
            manifest["spec"]["gateways"] = self.gateways
        if self.http_routes:
            manifest["spec"]["http"] = self.http_routes
        return manifest


@dataclass
class DestinationRule:
    """Istio DestinationRule configuration."""
    name: str
    namespace: str
    host: str
    traffic_policy: TrafficPolicy = TrafficPolicy.ROUND_ROBIN
    subsets: list[dict] = field(default_factory=list)

    def to_manifest(self) -> dict:
        """Generate DestinationRule manifest."""
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
                    "loadBalancer": {
                        "simple": self.traffic_policy.value
                    }
                },
                "subsets": self.subsets if self.subsets else []
            }
        }


class IstioInstaller:
    """Manages Istio installation and upgrades."""

    def __init__(self, kubeconfig: Optional[str] = None):
        """Initialize Istio installer.

        Args:
            kubeconfig: Path to kubeconfig file. Uses default if not specified.
        """
        self.kubeconfig = kubeconfig
        self._istioctl_path: Optional[str] = None

    @property
    def istioctl(self) -> str:
        """Get istioctl binary path."""
        if self._istioctl_path is None:
            self._istioctl_path = self._find_istioctl()
        return self._istioctl_path

    def _find_istioctl(self) -> str:
        """Find istioctl binary in PATH."""
        try:
            result = subprocess.run(
                ["which", "istioctl"],
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError:
            logger.warning("istioctl not found in PATH, using 'istioctl'")
            return "istioctl"

    def _run_istioctl(self, args: list[str]) -> subprocess.CompletedProcess:
        """Run istioctl command with arguments."""
        cmd = [self.istioctl] + args
        if self.kubeconfig:
            cmd.extend(["--kubeconfig", self.kubeconfig])
        logger.info(f"Running: {' '.join(cmd)}")
        return subprocess.run(cmd, capture_output=True, text=True)

    def check_prerequisites(self) -> dict[str, bool]:
        """Check if prerequisites for Istio installation are met."""
        checks = {
            "istioctl_available": False,
            "kubernetes_accessible": False,
            "sufficient_permissions": False,
        }

        # Check istioctl
        result = self._run_istioctl(["version", "--remote=false"])
        checks["istioctl_available"] = result.returncode == 0

        # Check Kubernetes access
        try:
            k8s_cmd = ["kubectl", "cluster-info"]
            if self.kubeconfig:
                k8s_cmd.extend(["--kubeconfig", self.kubeconfig])
            result = subprocess.run(k8s_cmd, capture_output=True, text=True)
            checks["kubernetes_accessible"] = result.returncode == 0
        except Exception as e:
            logger.error(f"Kubernetes check failed: {e}")

        # Check permissions
        try:
            perm_cmd = ["kubectl", "auth", "can-i", "create", "namespace"]
            if self.kubeconfig:
                perm_cmd.extend(["--kubeconfig", self.kubeconfig])
            result = subprocess.run(perm_cmd, capture_output=True, text=True)
            checks["sufficient_permissions"] = "yes" in result.stdout.lower()
        except Exception as e:
            logger.error(f"Permission check failed: {e}")

        return checks

    def install(self, config: IstioConfig) -> dict[str, Any]:
        """Install Istio with the given configuration.

        Args:
            config: IstioConfig object with installation settings.

        Returns:
            Installation result with status and details.
        """
        logger.info(f"Installing Istio with profile: {config.profile.value}")

        # Generate operator config
        operator_yaml = config.to_yaml()
        config_path = Path("/tmp/istio-operator.yaml")
        config_path.write_text(operator_yaml)

        # Run installation
        result = self._run_istioctl([
            "install",
            "-f", str(config_path),
            "-y"
        ])

        return {
            "success": result.returncode == 0,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "profile": config.profile.value,
            "namespace": config.namespace,
        }

    def verify_installation(self) -> dict[str, Any]:
        """Verify Istio installation status."""
        result = self._run_istioctl(["verify-install"])

        # Get component status
        analyze_result = self._run_istioctl(["analyze"])

        return {
            "verified": result.returncode == 0,
            "analysis": analyze_result.stdout,
            "issues": analyze_result.stderr if analyze_result.returncode != 0 else None,
        }

    def uninstall(self, purge: bool = False) -> dict[str, Any]:
        """Uninstall Istio from the cluster.

        Args:
            purge: If True, remove all Istio resources including CRDs.
        """
        args = ["uninstall", "-y"]
        if purge:
            args.append("--purge")

        result = self._run_istioctl(args)
        return {
            "success": result.returncode == 0,
            "purged": purge,
            "output": result.stdout,
        }


class SidecarInjector:
    """Manages Istio sidecar injection for namespaces and pods."""

    def __init__(self, kubeconfig: Optional[str] = None):
        """Initialize sidecar injector.

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

    def enable_namespace_injection(self, namespace: str) -> dict[str, Any]:
        """Enable automatic sidecar injection for a namespace.

        Args:
            namespace: Kubernetes namespace name.
        """
        result = self._run_kubectl([
            "label", "namespace", namespace,
            "istio-injection=enabled",
            "--overwrite"
        ])

        return {
            "success": result.returncode == 0,
            "namespace": namespace,
            "injection_enabled": result.returncode == 0,
            "output": result.stdout or result.stderr,
        }

    def disable_namespace_injection(self, namespace: str) -> dict[str, Any]:
        """Disable automatic sidecar injection for a namespace."""
        result = self._run_kubectl([
            "label", "namespace", namespace,
            "istio-injection-",
        ])

        return {
            "success": result.returncode == 0,
            "namespace": namespace,
            "injection_disabled": result.returncode == 0,
        }

    def get_injection_status(self, namespace: str) -> dict[str, Any]:
        """Get sidecar injection status for a namespace."""
        result = self._run_kubectl([
            "get", "namespace", namespace,
            "-o", "jsonpath={.metadata.labels.istio-injection}"
        ])

        status = result.stdout.strip()
        return {
            "namespace": namespace,
            "injection_enabled": status == "enabled",
            "label_value": status if status else None,
        }

    def list_injected_pods(self, namespace: str) -> list[dict]:
        """List pods with Istio sidecar in a namespace."""
        result = self._run_kubectl([
            "get", "pods", "-n", namespace,
            "-o", "json"
        ])

        if result.returncode != 0:
            return []

        try:
            pods_data = json.loads(result.stdout)
            injected_pods = []

            for pod in pods_data.get("items", []):
                containers = pod.get("spec", {}).get("containers", [])
                has_sidecar = any(c.get("name") == "istio-proxy" for c in containers)

                if has_sidecar:
                    injected_pods.append({
                        "name": pod["metadata"]["name"],
                        "namespace": namespace,
                        "status": pod.get("status", {}).get("phase"),
                    })

            return injected_pods
        except json.JSONDecodeError:
            logger.error("Failed to parse pods JSON")
            return []


class IstioConfigManager:
    """Manages Istio configuration resources."""

    def __init__(self, kubeconfig: Optional[str] = None):
        """Initialize config manager."""
        self.kubeconfig = kubeconfig

    def _run_kubectl(self, args: list[str], input_data: Optional[str] = None) -> subprocess.CompletedProcess:
        """Run kubectl command."""
        cmd = ["kubectl"] + args
        if self.kubeconfig:
            cmd.extend(["--kubeconfig", self.kubeconfig])
        return subprocess.run(cmd, capture_output=True, text=True, input=input_data)

    def apply_virtual_service(self, vs: VirtualService) -> dict[str, Any]:
        """Apply a VirtualService configuration.

        Args:
            vs: VirtualService configuration object.
        """
        manifest = json.dumps(vs.to_manifest())
        result = self._run_kubectl(
            ["apply", "-f", "-"],
            input_data=manifest
        )

        return {
            "success": result.returncode == 0,
            "name": vs.name,
            "namespace": vs.namespace,
            "output": result.stdout or result.stderr,
        }

    def apply_destination_rule(self, dr: DestinationRule) -> dict[str, Any]:
        """Apply a DestinationRule configuration.

        Args:
            dr: DestinationRule configuration object.
        """
        manifest = json.dumps(dr.to_manifest())
        result = self._run_kubectl(
            ["apply", "-f", "-"],
            input_data=manifest
        )

        return {
            "success": result.returncode == 0,
            "name": dr.name,
            "namespace": dr.namespace,
            "output": result.stdout or result.stderr,
        }

    def get_virtual_services(self, namespace: str = "default") -> list[dict]:
        """Get VirtualServices in a namespace."""
        result = self._run_kubectl([
            "get", "virtualservices", "-n", namespace,
            "-o", "json"
        ])

        if result.returncode != 0:
            return []

        try:
            data = json.loads(result.stdout)
            return [
                {
                    "name": item["metadata"]["name"],
                    "namespace": item["metadata"]["namespace"],
                    "hosts": item.get("spec", {}).get("hosts", []),
                }
                for item in data.get("items", [])
            ]
        except json.JSONDecodeError:
            return []

    def get_destination_rules(self, namespace: str = "default") -> list[dict]:
        """Get DestinationRules in a namespace."""
        result = self._run_kubectl([
            "get", "destinationrules", "-n", namespace,
            "-o", "json"
        ])

        if result.returncode != 0:
            return []

        try:
            data = json.loads(result.stdout)
            return [
                {
                    "name": item["metadata"]["name"],
                    "namespace": item["metadata"]["namespace"],
                    "host": item.get("spec", {}).get("host"),
                }
                for item in data.get("items", [])
            ]
        except json.JSONDecodeError:
            return []

    def delete_virtual_service(self, name: str, namespace: str) -> dict[str, Any]:
        """Delete a VirtualService."""
        result = self._run_kubectl([
            "delete", "virtualservice", name, "-n", namespace
        ])
        return {
            "success": result.returncode == 0,
            "name": name,
            "namespace": namespace,
        }

    def delete_destination_rule(self, name: str, namespace: str) -> dict[str, Any]:
        """Delete a DestinationRule."""
        result = self._run_kubectl([
            "delete", "destinationrule", name, "-n", namespace
        ])
        return {
            "success": result.returncode == 0,
            "name": name,
            "namespace": namespace,
        }


class ServiceMeshConfig:
    """High-level Service Mesh configuration manager.

    Provides a unified interface for managing all aspects of Istio Service Mesh:
    - Installation and upgrades
    - Sidecar injection
    - Traffic management
    """

    def __init__(self, kubeconfig: Optional[str] = None):
        """Initialize ServiceMeshConfig.

        Args:
            kubeconfig: Path to kubeconfig file.
        """
        self.kubeconfig = kubeconfig
        self.installer = IstioInstaller(kubeconfig)
        self.injector = SidecarInjector(kubeconfig)
        self.config_manager = IstioConfigManager(kubeconfig)

    def configure_namespace(
        self,
        namespace: str,
        enable_injection: bool = True,
        traffic_policy: Optional[TrafficPolicy] = None,
    ) -> dict[str, Any]:
        """Configure a namespace for service mesh.

        Args:
            namespace: Kubernetes namespace.
            enable_injection: Whether to enable sidecar injection.
            traffic_policy: Default traffic policy for the namespace.
        """
        results = {
            "namespace": namespace,
            "operations": [],
        }

        # Configure injection
        if enable_injection:
            inject_result = self.injector.enable_namespace_injection(namespace)
            results["operations"].append({
                "operation": "enable_injection",
                "success": inject_result["success"],
            })
        else:
            inject_result = self.injector.disable_namespace_injection(namespace)
            results["operations"].append({
                "operation": "disable_injection",
                "success": inject_result["success"],
            })

        # Apply default traffic policy if specified
        if traffic_policy:
            dr = DestinationRule(
                name=f"{namespace}-default",
                namespace=namespace,
                host=f"*.{namespace}.svc.cluster.local",
                traffic_policy=traffic_policy,
            )
            dr_result = self.config_manager.apply_destination_rule(dr)
            results["operations"].append({
                "operation": "apply_traffic_policy",
                "success": dr_result["success"],
            })

        results["success"] = all(op["success"] for op in results["operations"])
        return results

    def get_mesh_status(self) -> dict[str, Any]:
        """Get overall service mesh status."""
        verify_result = self.installer.verify_installation()

        return {
            "installed": verify_result["verified"],
            "analysis": verify_result.get("analysis"),
            "issues": verify_result.get("issues"),
        }
