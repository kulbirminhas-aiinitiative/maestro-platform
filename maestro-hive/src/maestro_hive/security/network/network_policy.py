"""
Kubernetes NetworkPolicy Manager - AC-4: Kubernetes NetworkPolicy for pod-to-pod traffic control.

This module provides comprehensive NetworkPolicy management including:
- Default deny ingress/egress policies
- Pod-to-pod communication rules
- Namespace isolation
- CIDR-based rules for external access

Implements: MD-2782 AC-4
"""

import logging
import subprocess
import json
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

logger = logging.getLogger(__name__)


class PolicyType(Enum):
    """NetworkPolicy types."""
    INGRESS = "Ingress"
    EGRESS = "Egress"


class Protocol(Enum):
    """Network protocols."""
    TCP = "TCP"
    UDP = "UDP"
    SCTP = "SCTP"


@dataclass
class PodSelector:
    """Pod selector for NetworkPolicy."""
    match_labels: dict[str, str] = field(default_factory=dict)
    match_expressions: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Convert to Kubernetes selector format."""
        result = {}
        if self.match_labels:
            result["matchLabels"] = self.match_labels
        if self.match_expressions:
            result["matchExpressions"] = self.match_expressions
        return result


@dataclass
class NamespaceSelector:
    """Namespace selector for NetworkPolicy."""
    match_labels: dict[str, str] = field(default_factory=dict)
    match_expressions: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Convert to Kubernetes selector format."""
        result = {}
        if self.match_labels:
            result["matchLabels"] = self.match_labels
        if self.match_expressions:
            result["matchExpressions"] = self.match_expressions
        return result


@dataclass
class IPBlock:
    """IP block specification for NetworkPolicy."""
    cidr: str
    except_cidrs: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Convert to Kubernetes IPBlock format."""
        result = {"cidr": self.cidr}
        if self.except_cidrs:
            result["except"] = self.except_cidrs
        return result


@dataclass
class NetworkPolicyPort:
    """Port specification for NetworkPolicy."""
    port: Optional[int] = None
    end_port: Optional[int] = None
    protocol: Protocol = Protocol.TCP

    def to_dict(self) -> dict:
        """Convert to Kubernetes port format."""
        result = {"protocol": self.protocol.value}
        if self.port is not None:
            result["port"] = self.port
        if self.end_port is not None:
            result["endPort"] = self.end_port
        return result


@dataclass
class IngressRule:
    """Ingress rule for NetworkPolicy."""
    from_selectors: list[dict] = field(default_factory=list)
    ports: list[NetworkPolicyPort] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Convert to Kubernetes ingress rule format."""
        result = {}
        if self.from_selectors:
            result["from"] = self.from_selectors
        if self.ports:
            result["ports"] = [p.to_dict() for p in self.ports]
        return result


@dataclass
class EgressRule:
    """Egress rule for NetworkPolicy."""
    to_selectors: list[dict] = field(default_factory=list)
    ports: list[NetworkPolicyPort] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Convert to Kubernetes egress rule format."""
        result = {}
        if self.to_selectors:
            result["to"] = self.to_selectors
        if self.ports:
            result["ports"] = [p.to_dict() for p in self.ports]
        return result


@dataclass
class NetworkPolicy:
    """Kubernetes NetworkPolicy configuration."""
    name: str
    namespace: str
    pod_selector: PodSelector = field(default_factory=PodSelector)
    policy_types: list[PolicyType] = field(default_factory=list)
    ingress_rules: list[IngressRule] = field(default_factory=list)
    egress_rules: list[EgressRule] = field(default_factory=list)
    labels: dict[str, str] = field(default_factory=dict)
    annotations: dict[str, str] = field(default_factory=dict)

    def to_manifest(self) -> dict:
        """Generate Kubernetes NetworkPolicy manifest."""
        manifest = {
            "apiVersion": "networking.k8s.io/v1",
            "kind": "NetworkPolicy",
            "metadata": {
                "name": self.name,
                "namespace": self.namespace,
            },
            "spec": {
                "podSelector": self.pod_selector.to_dict(),
            }
        }

        # Add labels and annotations
        if self.labels:
            manifest["metadata"]["labels"] = self.labels
        if self.annotations:
            manifest["metadata"]["annotations"] = self.annotations

        # Add policy types
        if self.policy_types:
            manifest["spec"]["policyTypes"] = [pt.value for pt in self.policy_types]

        # Add ingress rules
        if self.ingress_rules:
            manifest["spec"]["ingress"] = [r.to_dict() for r in self.ingress_rules]
        elif PolicyType.INGRESS in self.policy_types:
            # Empty ingress with Ingress policy type = deny all ingress
            manifest["spec"]["ingress"] = []

        # Add egress rules
        if self.egress_rules:
            manifest["spec"]["egress"] = [r.to_dict() for r in self.egress_rules]
        elif PolicyType.EGRESS in self.policy_types:
            # Empty egress with Egress policy type = deny all egress
            manifest["spec"]["egress"] = []

        return manifest


@dataclass
class DefaultDenyPolicy:
    """Factory for creating default deny NetworkPolicies."""
    namespace: str

    def create_deny_all_ingress(self) -> NetworkPolicy:
        """Create a default deny all ingress policy."""
        return NetworkPolicy(
            name="default-deny-ingress",
            namespace=self.namespace,
            pod_selector=PodSelector(),  # Empty = all pods
            policy_types=[PolicyType.INGRESS],
            labels={"policy-type": "default-deny"},
            annotations={"description": "Default deny all ingress traffic"},
        )

    def create_deny_all_egress(self) -> NetworkPolicy:
        """Create a default deny all egress policy."""
        return NetworkPolicy(
            name="default-deny-egress",
            namespace=self.namespace,
            pod_selector=PodSelector(),
            policy_types=[PolicyType.EGRESS],
            labels={"policy-type": "default-deny"},
            annotations={"description": "Default deny all egress traffic"},
        )

    def create_deny_all(self) -> NetworkPolicy:
        """Create a default deny all traffic policy."""
        return NetworkPolicy(
            name="default-deny-all",
            namespace=self.namespace,
            pod_selector=PodSelector(),
            policy_types=[PolicyType.INGRESS, PolicyType.EGRESS],
            labels={"policy-type": "default-deny"},
            annotations={"description": "Default deny all ingress and egress traffic"},
        )


class NamespaceIsolation:
    """Manages namespace-level isolation policies."""

    def __init__(self, namespace: str):
        """Initialize namespace isolation.

        Args:
            namespace: Target namespace.
        """
        self.namespace = namespace

    def create_isolation_policy(
        self,
        allow_same_namespace: bool = True,
        allow_kube_system_dns: bool = True,
    ) -> NetworkPolicy:
        """Create a namespace isolation policy.

        Args:
            allow_same_namespace: Allow traffic from same namespace.
            allow_kube_system_dns: Allow DNS traffic to kube-system.
        """
        ingress_rules = []
        egress_rules = []

        # Allow traffic from same namespace
        if allow_same_namespace:
            ingress_rules.append(IngressRule(
                from_selectors=[{
                    "namespaceSelector": {
                        "matchLabels": {"kubernetes.io/metadata.name": self.namespace}
                    }
                }]
            ))

        # Allow DNS egress to kube-system
        if allow_kube_system_dns:
            egress_rules.append(EgressRule(
                to_selectors=[{
                    "namespaceSelector": {
                        "matchLabels": {"kubernetes.io/metadata.name": "kube-system"}
                    }
                }],
                ports=[
                    NetworkPolicyPort(port=53, protocol=Protocol.UDP),
                    NetworkPolicyPort(port=53, protocol=Protocol.TCP),
                ]
            ))

            # Also allow egress to same namespace
            egress_rules.append(EgressRule(
                to_selectors=[{
                    "namespaceSelector": {
                        "matchLabels": {"kubernetes.io/metadata.name": self.namespace}
                    }
                }]
            ))

        return NetworkPolicy(
            name=f"{self.namespace}-isolation",
            namespace=self.namespace,
            pod_selector=PodSelector(),
            policy_types=[PolicyType.INGRESS, PolicyType.EGRESS],
            ingress_rules=ingress_rules,
            egress_rules=egress_rules,
            labels={"policy-type": "namespace-isolation"},
        )

    def allow_from_namespace(self, source_namespace: str) -> IngressRule:
        """Create an ingress rule allowing traffic from another namespace.

        Args:
            source_namespace: Source namespace name.
        """
        return IngressRule(
            from_selectors=[{
                "namespaceSelector": {
                    "matchLabels": {"kubernetes.io/metadata.name": source_namespace}
                }
            }]
        )

    def allow_to_namespace(self, target_namespace: str) -> EgressRule:
        """Create an egress rule allowing traffic to another namespace.

        Args:
            target_namespace: Target namespace name.
        """
        return EgressRule(
            to_selectors=[{
                "namespaceSelector": {
                    "matchLabels": {"kubernetes.io/metadata.name": target_namespace}
                }
            }]
        )


class NetworkPolicyManager:
    """Manages Kubernetes NetworkPolicy resources."""

    def __init__(self, kubeconfig: Optional[str] = None):
        """Initialize NetworkPolicy manager.

        Args:
            kubeconfig: Path to kubeconfig file.
        """
        self.kubeconfig = kubeconfig

    def _run_kubectl(self, args: list[str], input_data: Optional[str] = None) -> subprocess.CompletedProcess:
        """Run kubectl command."""
        cmd = ["kubectl"] + args
        if self.kubeconfig:
            cmd.extend(["--kubeconfig", self.kubeconfig])
        return subprocess.run(cmd, capture_output=True, text=True, input=input_data)

    def apply_policy(self, policy: NetworkPolicy) -> dict[str, Any]:
        """Apply a NetworkPolicy.

        Args:
            policy: NetworkPolicy configuration.
        """
        manifest = json.dumps(policy.to_manifest())
        result = self._run_kubectl(
            ["apply", "-f", "-"],
            input_data=manifest
        )

        logger.info(f"Applied NetworkPolicy: {policy.name} in {policy.namespace}")

        return {
            "success": result.returncode == 0,
            "name": policy.name,
            "namespace": policy.namespace,
            "policy_types": [pt.value for pt in policy.policy_types],
            "output": result.stdout or result.stderr,
        }

    def get_policies(self, namespace: str = "") -> list[dict]:
        """Get NetworkPolicies.

        Args:
            namespace: Namespace to query. Empty for all namespaces.
        """
        args = ["get", "networkpolicy"]
        if namespace:
            args.extend(["-n", namespace])
        else:
            args.append("-A")
        args.extend(["-o", "json"])

        result = self._run_kubectl(args)

        if result.returncode != 0:
            return []

        try:
            data = json.loads(result.stdout)
            return [
                {
                    "name": item["metadata"]["name"],
                    "namespace": item["metadata"]["namespace"],
                    "policy_types": item.get("spec", {}).get("policyTypes", []),
                    "ingress_rules": len(item.get("spec", {}).get("ingress", [])),
                    "egress_rules": len(item.get("spec", {}).get("egress", [])),
                }
                for item in data.get("items", [])
            ]
        except json.JSONDecodeError:
            return []

    def delete_policy(self, name: str, namespace: str) -> dict[str, Any]:
        """Delete a NetworkPolicy.

        Args:
            name: Policy name.
            namespace: Policy namespace.
        """
        result = self._run_kubectl([
            "delete", "networkpolicy", name, "-n", namespace
        ])

        return {
            "success": result.returncode == 0,
            "name": name,
            "namespace": namespace,
        }

    def create_default_deny(self, namespace: str) -> dict[str, Any]:
        """Create default deny policies for a namespace.

        Args:
            namespace: Target namespace.
        """
        factory = DefaultDenyPolicy(namespace)
        policy = factory.create_deny_all()
        return self.apply_policy(policy)

    def allow_ingress(
        self,
        name: str,
        namespace: str,
        from_namespace: Optional[str] = None,
        from_pod_labels: Optional[dict] = None,
        to_pod_labels: Optional[dict] = None,
        ports: Optional[list[int]] = None,
    ) -> dict[str, Any]:
        """Create an ingress allow policy.

        Args:
            name: Policy name.
            namespace: Target namespace.
            from_namespace: Source namespace (optional).
            from_pod_labels: Source pod selector labels (optional).
            to_pod_labels: Target pod selector labels (optional).
            ports: Allowed ports (optional).
        """
        from_selectors = []

        if from_namespace:
            selector = {
                "namespaceSelector": {
                    "matchLabels": {"kubernetes.io/metadata.name": from_namespace}
                }
            }
            if from_pod_labels:
                selector["podSelector"] = {"matchLabels": from_pod_labels}
            from_selectors.append(selector)
        elif from_pod_labels:
            from_selectors.append({
                "podSelector": {"matchLabels": from_pod_labels}
            })

        rule_ports = []
        if ports:
            rule_ports = [NetworkPolicyPort(port=p) for p in ports]

        ingress_rule = IngressRule(
            from_selectors=from_selectors,
            ports=rule_ports,
        )

        policy = NetworkPolicy(
            name=name,
            namespace=namespace,
            pod_selector=PodSelector(match_labels=to_pod_labels or {}),
            policy_types=[PolicyType.INGRESS],
            ingress_rules=[ingress_rule],
        )

        return self.apply_policy(policy)

    def allow_egress(
        self,
        name: str,
        namespace: str,
        to_namespace: Optional[str] = None,
        to_cidr: Optional[str] = None,
        from_pod_labels: Optional[dict] = None,
        ports: Optional[list[int]] = None,
    ) -> dict[str, Any]:
        """Create an egress allow policy.

        Args:
            name: Policy name.
            namespace: Target namespace.
            to_namespace: Target namespace (optional).
            to_cidr: Target CIDR block (optional).
            from_pod_labels: Source pod selector labels (optional).
            ports: Allowed ports (optional).
        """
        to_selectors = []

        if to_namespace:
            to_selectors.append({
                "namespaceSelector": {
                    "matchLabels": {"kubernetes.io/metadata.name": to_namespace}
                }
            })
        elif to_cidr:
            to_selectors.append({
                "ipBlock": {"cidr": to_cidr}
            })

        rule_ports = []
        if ports:
            rule_ports = [NetworkPolicyPort(port=p) for p in ports]

        egress_rule = EgressRule(
            to_selectors=to_selectors,
            ports=rule_ports,
        )

        policy = NetworkPolicy(
            name=name,
            namespace=namespace,
            pod_selector=PodSelector(match_labels=from_pod_labels or {}),
            policy_types=[PolicyType.EGRESS],
            egress_rules=[egress_rule],
        )

        return self.apply_policy(policy)

    def setup_namespace_isolation(
        self,
        namespace: str,
        allowed_namespaces: Optional[list[str]] = None,
    ) -> dict[str, Any]:
        """Setup complete namespace isolation.

        Args:
            namespace: Target namespace.
            allowed_namespaces: List of namespaces to allow communication with.
        """
        results = []

        # Create default deny
        deny_result = self.create_default_deny(namespace)
        results.append({"operation": "default_deny", **deny_result})

        # Create isolation policy
        isolation = NamespaceIsolation(namespace)
        isolation_policy = isolation.create_isolation_policy()
        isolation_result = self.apply_policy(isolation_policy)
        results.append({"operation": "isolation_policy", **isolation_result})

        # Allow specified namespaces
        if allowed_namespaces:
            for allowed_ns in allowed_namespaces:
                ingress_rule = isolation.allow_from_namespace(allowed_ns)
                egress_rule = isolation.allow_to_namespace(allowed_ns)

                allow_policy = NetworkPolicy(
                    name=f"allow-{allowed_ns}",
                    namespace=namespace,
                    pod_selector=PodSelector(),
                    policy_types=[PolicyType.INGRESS, PolicyType.EGRESS],
                    ingress_rules=[ingress_rule],
                    egress_rules=[egress_rule],
                )
                allow_result = self.apply_policy(allow_policy)
                results.append({"operation": f"allow_{allowed_ns}", **allow_result})

        return {
            "namespace": namespace,
            "operations": results,
            "success": all(r.get("success", False) for r in results),
        }

    def validate_policies(self, namespace: str) -> dict[str, Any]:
        """Validate NetworkPolicies in a namespace.

        Args:
            namespace: Target namespace.
        """
        policies = self.get_policies(namespace)

        has_default_deny = any(
            "deny" in p["name"].lower() and
            p["ingress_rules"] == 0 and
            "Ingress" in p.get("policy_types", [])
            for p in policies
        )

        issues = []
        if not has_default_deny:
            issues.append("No default deny ingress policy found")

        if not policies:
            issues.append("No NetworkPolicies defined")

        return {
            "namespace": namespace,
            "policies_count": len(policies),
            "has_default_deny": has_default_deny,
            "valid": len(issues) == 0,
            "issues": issues,
            "policies": policies,
        }
