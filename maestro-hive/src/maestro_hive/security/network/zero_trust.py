"""
Zero Trust Network Module - AC-3: Zero Trust network architecture with AuthorizationPolicy.

This module implements Zero Trust networking principles including:
- Istio AuthorizationPolicy management for fine-grained access control
- Default deny-all policies with explicit allow rules
- JWT validation for external requests
- Service-to-service authorization rules

Implements: MD-2782 AC-3
"""

import logging
import subprocess
import json
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

logger = logging.getLogger(__name__)


class AuthorizationAction(Enum):
    """Authorization policy actions."""
    ALLOW = "ALLOW"
    DENY = "DENY"
    CUSTOM = "CUSTOM"
    AUDIT = "AUDIT"


class Operation(Enum):
    """HTTP operation types for access rules."""
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    DELETE = "DELETE"
    PATCH = "PATCH"
    HEAD = "HEAD"
    OPTIONS = "OPTIONS"


@dataclass
class Source:
    """Source specification for authorization rules."""
    principals: list[str] = field(default_factory=list)
    namespaces: list[str] = field(default_factory=list)
    ip_blocks: list[str] = field(default_factory=list)
    request_principals: list[str] = field(default_factory=list)
    not_principals: list[str] = field(default_factory=list)
    not_namespaces: list[str] = field(default_factory=list)
    not_ip_blocks: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Convert to dictionary for manifest generation."""
        result = {}
        if self.principals:
            result["principals"] = self.principals
        if self.namespaces:
            result["namespaces"] = self.namespaces
        if self.ip_blocks:
            result["ipBlocks"] = self.ip_blocks
        if self.request_principals:
            result["requestPrincipals"] = self.request_principals
        if self.not_principals:
            result["notPrincipals"] = self.not_principals
        if self.not_namespaces:
            result["notNamespaces"] = self.not_namespaces
        if self.not_ip_blocks:
            result["notIpBlocks"] = self.not_ip_blocks
        return result


@dataclass
class OperationSpec:
    """Operation specification for authorization rules."""
    hosts: list[str] = field(default_factory=list)
    ports: list[str] = field(default_factory=list)
    methods: list[str] = field(default_factory=list)
    paths: list[str] = field(default_factory=list)
    not_hosts: list[str] = field(default_factory=list)
    not_ports: list[str] = field(default_factory=list)
    not_methods: list[str] = field(default_factory=list)
    not_paths: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Convert to dictionary for manifest generation."""
        result = {}
        if self.hosts:
            result["hosts"] = self.hosts
        if self.ports:
            result["ports"] = self.ports
        if self.methods:
            result["methods"] = self.methods
        if self.paths:
            result["paths"] = self.paths
        if self.not_hosts:
            result["notHosts"] = self.not_hosts
        if self.not_ports:
            result["notPorts"] = self.not_ports
        if self.not_methods:
            result["notMethods"] = self.not_methods
        if self.not_paths:
            result["notPaths"] = self.not_paths
        return result


@dataclass
class AccessRule:
    """Access rule combining source and operation specifications."""
    from_sources: list[Source] = field(default_factory=list)
    to_operations: list[OperationSpec] = field(default_factory=list)
    when_conditions: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Convert to dictionary for manifest generation."""
        result = {}
        if self.from_sources:
            result["from"] = [{"source": s.to_dict()} for s in self.from_sources]
        if self.to_operations:
            result["to"] = [{"operation": o.to_dict()} for o in self.to_operations]
        if self.when_conditions:
            result["when"] = self.when_conditions
        return result


@dataclass
class AuthorizationPolicy:
    """Istio AuthorizationPolicy configuration."""
    name: str
    namespace: str
    action: AuthorizationAction = AuthorizationAction.ALLOW
    rules: list[AccessRule] = field(default_factory=list)
    selector: Optional[dict] = None
    provider: Optional[str] = None

    def to_manifest(self) -> dict:
        """Generate AuthorizationPolicy Kubernetes manifest."""
        manifest = {
            "apiVersion": "security.istio.io/v1beta1",
            "kind": "AuthorizationPolicy",
            "metadata": {
                "name": self.name,
                "namespace": self.namespace,
            },
            "spec": {}
        }

        # Add action
        if self.action != AuthorizationAction.ALLOW:
            manifest["spec"]["action"] = self.action.value

        # Add workload selector if specified
        if self.selector:
            manifest["spec"]["selector"] = {
                "matchLabels": self.selector
            }

        # Add rules
        if self.rules:
            manifest["spec"]["rules"] = [r.to_dict() for r in self.rules]

        # Add provider for CUSTOM action
        if self.action == AuthorizationAction.CUSTOM and self.provider:
            manifest["spec"]["provider"] = {"name": self.provider}

        return manifest


@dataclass
class JWTRule:
    """JWT validation rule for RequestAuthentication."""
    issuer: str
    audiences: list[str] = field(default_factory=list)
    jwks_uri: Optional[str] = None
    jwks: Optional[dict] = None
    from_headers: list[dict] = field(default_factory=list)
    from_params: list[str] = field(default_factory=list)
    forward_original_token: bool = False
    output_claim_to_headers: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Convert to dictionary for manifest generation."""
        result = {"issuer": self.issuer}
        if self.audiences:
            result["audiences"] = self.audiences
        if self.jwks_uri:
            result["jwksUri"] = self.jwks_uri
        if self.jwks:
            result["jwks"] = json.dumps(self.jwks)
        if self.from_headers:
            result["fromHeaders"] = self.from_headers
        if self.from_params:
            result["fromParams"] = self.from_params
        if self.forward_original_token:
            result["forwardOriginalToken"] = True
        if self.output_claim_to_headers:
            result["outputClaimToHeaders"] = self.output_claim_to_headers
        return result


@dataclass
class RequestAuthentication:
    """Istio RequestAuthentication for JWT validation."""
    name: str
    namespace: str
    jwt_rules: list[JWTRule] = field(default_factory=list)
    selector: Optional[dict] = None

    def to_manifest(self) -> dict:
        """Generate RequestAuthentication manifest."""
        manifest = {
            "apiVersion": "security.istio.io/v1beta1",
            "kind": "RequestAuthentication",
            "metadata": {
                "name": self.name,
                "namespace": self.namespace,
            },
            "spec": {}
        }

        if self.selector:
            manifest["spec"]["selector"] = {
                "matchLabels": self.selector
            }

        if self.jwt_rules:
            manifest["spec"]["jwtRules"] = [r.to_dict() for r in self.jwt_rules]

        return manifest


class ZeroTrustPolicy:
    """High-level Zero Trust policy management."""

    def __init__(self, kubeconfig: Optional[str] = None):
        """Initialize Zero Trust policy manager.

        Args:
            kubeconfig: Path to kubeconfig file.
        """
        self.kubeconfig = kubeconfig
        self.authz_manager = AuthorizationPolicyManager(kubeconfig)
        self.jwt_validator = JWTValidator(kubeconfig)

    def apply_default_deny(self, namespace: str) -> dict[str, Any]:
        """Apply default deny-all policy to a namespace.

        This is the foundation of Zero Trust - deny all traffic by default.

        Args:
            namespace: Target namespace.
        """
        policy = AuthorizationPolicy(
            name="deny-all",
            namespace=namespace,
            action=AuthorizationAction.DENY,
            rules=[],  # Empty rules = deny all
        )

        return self.authz_manager.apply_policy(policy)

    def allow_service_to_service(
        self,
        name: str,
        namespace: str,
        from_service: str,
        from_namespace: str,
        to_paths: Optional[list[str]] = None,
        to_methods: Optional[list[str]] = None,
    ) -> dict[str, Any]:
        """Create an allow rule for service-to-service communication.

        Args:
            name: Policy name.
            namespace: Target namespace.
            from_service: Source service account name.
            from_namespace: Source namespace.
            to_paths: Allowed paths (optional).
            to_methods: Allowed HTTP methods (optional).
        """
        source = Source(
            principals=[
                f"cluster.local/ns/{from_namespace}/sa/{from_service}"
            ]
        )

        operation = OperationSpec()
        if to_paths:
            operation.paths = to_paths
        if to_methods:
            operation.methods = to_methods

        rule = AccessRule(
            from_sources=[source],
            to_operations=[operation] if to_paths or to_methods else [],
        )

        policy = AuthorizationPolicy(
            name=name,
            namespace=namespace,
            action=AuthorizationAction.ALLOW,
            rules=[rule],
        )

        return self.authz_manager.apply_policy(policy)

    def configure_jwt_auth(
        self,
        name: str,
        namespace: str,
        issuer: str,
        jwks_uri: str,
        audiences: Optional[list[str]] = None,
    ) -> dict[str, Any]:
        """Configure JWT authentication for a namespace.

        Args:
            name: Policy name.
            namespace: Target namespace.
            issuer: JWT issuer.
            jwks_uri: JWKS endpoint URL.
            audiences: Expected audiences.
        """
        jwt_rule = JWTRule(
            issuer=issuer,
            jwks_uri=jwks_uri,
            audiences=audiences or [],
        )

        return self.jwt_validator.create_request_authentication(
            name=name,
            namespace=namespace,
            jwt_rules=[jwt_rule],
        )

    def get_namespace_policies(self, namespace: str) -> dict[str, Any]:
        """Get all Zero Trust policies for a namespace.

        Args:
            namespace: Target namespace.
        """
        authz_policies = self.authz_manager.get_policies(namespace)
        request_auths = self.jwt_validator.get_request_authentications(namespace)

        return {
            "namespace": namespace,
            "authorization_policies": authz_policies,
            "request_authentications": request_auths,
            "zero_trust_enabled": any(
                p.get("name") == "deny-all" for p in authz_policies
            ),
        }


class AuthorizationPolicyManager:
    """Manages Istio AuthorizationPolicy resources."""

    def __init__(self, kubeconfig: Optional[str] = None):
        """Initialize AuthorizationPolicy manager."""
        self.kubeconfig = kubeconfig

    def _run_kubectl(self, args: list[str], input_data: Optional[str] = None) -> subprocess.CompletedProcess:
        """Run kubectl command."""
        cmd = ["kubectl"] + args
        if self.kubeconfig:
            cmd.extend(["--kubeconfig", self.kubeconfig])
        return subprocess.run(cmd, capture_output=True, text=True, input=input_data)

    def apply_policy(self, policy: AuthorizationPolicy) -> dict[str, Any]:
        """Apply an AuthorizationPolicy.

        Args:
            policy: AuthorizationPolicy configuration.
        """
        manifest = json.dumps(policy.to_manifest())
        result = self._run_kubectl(
            ["apply", "-f", "-"],
            input_data=manifest
        )

        logger.info(f"Applied AuthorizationPolicy: {policy.name} in {policy.namespace}")

        return {
            "success": result.returncode == 0,
            "name": policy.name,
            "namespace": policy.namespace,
            "action": policy.action.value,
            "output": result.stdout or result.stderr,
        }

    def get_policies(self, namespace: str = "") -> list[dict]:
        """Get AuthorizationPolicies.

        Args:
            namespace: Namespace to query. Empty for all namespaces.
        """
        args = ["get", "authorizationpolicy"]
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
                    "action": item.get("spec", {}).get("action", "ALLOW"),
                    "rules_count": len(item.get("spec", {}).get("rules", [])),
                }
                for item in data.get("items", [])
            ]
        except json.JSONDecodeError:
            return []

    def delete_policy(self, name: str, namespace: str) -> dict[str, Any]:
        """Delete an AuthorizationPolicy.

        Args:
            name: Policy name.
            namespace: Policy namespace.
        """
        result = self._run_kubectl([
            "delete", "authorizationpolicy", name, "-n", namespace
        ])

        return {
            "success": result.returncode == 0,
            "name": name,
            "namespace": namespace,
        }

    def create_deny_all(self, namespace: str) -> dict[str, Any]:
        """Create a deny-all policy for a namespace.

        Args:
            namespace: Target namespace.
        """
        policy = AuthorizationPolicy(
            name="deny-all",
            namespace=namespace,
            action=AuthorizationAction.DENY,
        )
        return self.apply_policy(policy)

    def create_allow_all(self, namespace: str) -> dict[str, Any]:
        """Create an allow-all policy for a namespace.

        Note: Use with caution, this disables Zero Trust for the namespace.

        Args:
            namespace: Target namespace.
        """
        policy = AuthorizationPolicy(
            name="allow-all",
            namespace=namespace,
            action=AuthorizationAction.ALLOW,
            rules=[AccessRule()],  # Empty rule = allow all
        )
        return self.apply_policy(policy)


class JWTValidator:
    """Manages JWT validation for Zero Trust external access."""

    def __init__(self, kubeconfig: Optional[str] = None):
        """Initialize JWT validator."""
        self.kubeconfig = kubeconfig

    def _run_kubectl(self, args: list[str], input_data: Optional[str] = None) -> subprocess.CompletedProcess:
        """Run kubectl command."""
        cmd = ["kubectl"] + args
        if self.kubeconfig:
            cmd.extend(["--kubeconfig", self.kubeconfig])
        return subprocess.run(cmd, capture_output=True, text=True, input=input_data)

    def create_request_authentication(
        self,
        name: str,
        namespace: str,
        jwt_rules: list[JWTRule],
        selector: Optional[dict] = None,
    ) -> dict[str, Any]:
        """Create a RequestAuthentication resource.

        Args:
            name: Resource name.
            namespace: Target namespace.
            jwt_rules: JWT validation rules.
            selector: Workload selector.
        """
        request_auth = RequestAuthentication(
            name=name,
            namespace=namespace,
            jwt_rules=jwt_rules,
            selector=selector,
        )

        manifest = json.dumps(request_auth.to_manifest())
        result = self._run_kubectl(
            ["apply", "-f", "-"],
            input_data=manifest
        )

        return {
            "success": result.returncode == 0,
            "name": name,
            "namespace": namespace,
            "jwt_rules_count": len(jwt_rules),
            "output": result.stdout or result.stderr,
        }

    def get_request_authentications(self, namespace: str = "") -> list[dict]:
        """Get RequestAuthentication resources.

        Args:
            namespace: Namespace to query.
        """
        args = ["get", "requestauthentication"]
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
                    "jwt_rules": len(item.get("spec", {}).get("jwtRules", [])),
                }
                for item in data.get("items", [])
            ]
        except json.JSONDecodeError:
            return []

    def delete_request_authentication(self, name: str, namespace: str) -> dict[str, Any]:
        """Delete a RequestAuthentication resource.

        Args:
            name: Resource name.
            namespace: Resource namespace.
        """
        result = self._run_kubectl([
            "delete", "requestauthentication", name, "-n", namespace
        ])

        return {
            "success": result.returncode == 0,
            "name": name,
            "namespace": namespace,
        }

    def require_jwt_for_ingress(
        self,
        namespace: str,
        issuer: str,
        jwks_uri: str,
        gateway_name: str = "istio-ingressgateway",
    ) -> dict[str, Any]:
        """Require JWT authentication for ingress traffic.

        Args:
            namespace: Target namespace.
            issuer: JWT issuer URL.
            jwks_uri: JWKS endpoint URL.
            gateway_name: Ingress gateway name.
        """
        # Create RequestAuthentication for the gateway
        jwt_rule = JWTRule(
            issuer=issuer,
            jwks_uri=jwks_uri,
        )

        auth_result = self.create_request_authentication(
            name=f"{gateway_name}-jwt",
            namespace="istio-system",
            jwt_rules=[jwt_rule],
            selector={"app": gateway_name},
        )

        return {
            "request_auth_created": auth_result["success"],
            "issuer": issuer,
            "gateway": gateway_name,
        }
