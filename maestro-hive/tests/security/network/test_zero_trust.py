"""
Tests for Zero Trust network module.

Tests AC-3: Zero Trust network architecture with AuthorizationPolicy
EPIC: MD-2782
"""

import pytest
import json
from unittest.mock import Mock, patch

from maestro_hive.security.network.zero_trust import (
    AuthorizationAction,
    Operation,
    Source,
    OperationSpec,
    AccessRule,
    AuthorizationPolicy,
    JWTRule,
    RequestAuthentication,
    ZeroTrustPolicy,
    AuthorizationPolicyManager,
    JWTValidator,
)


class TestAuthorizationAction:
    """Tests for AuthorizationAction enumeration."""

    def test_all_actions_exist(self):
        """Test all expected actions exist."""
        actions = [a.value for a in AuthorizationAction]
        assert "ALLOW" in actions
        assert "DENY" in actions
        assert "CUSTOM" in actions
        assert "AUDIT" in actions


class TestSource:
    """Tests for Source specification."""

    def test_empty_source(self):
        """Test empty source."""
        source = Source()
        assert source.to_dict() == {}

    def test_source_with_principals(self):
        """Test source with principals."""
        source = Source(
            principals=["cluster.local/ns/default/sa/my-service"]
        )
        result = source.to_dict()
        assert "principals" in result
        assert len(result["principals"]) == 1

    def test_source_with_namespaces(self):
        """Test source with namespace restriction."""
        source = Source(
            namespaces=["production", "staging"]
        )
        result = source.to_dict()
        assert "namespaces" in result
        assert len(result["namespaces"]) == 2

    def test_source_with_ip_blocks(self):
        """Test source with IP blocks."""
        source = Source(
            ip_blocks=["10.0.0.0/8", "192.168.0.0/16"]
        )
        result = source.to_dict()
        assert "ipBlocks" in result

    def test_source_with_not_principals(self):
        """Test source with negative principals."""
        source = Source(
            not_principals=["cluster.local/ns/default/sa/blocked-service"]
        )
        result = source.to_dict()
        assert "notPrincipals" in result


class TestOperationSpec:
    """Tests for OperationSpec specification."""

    def test_empty_operation(self):
        """Test empty operation."""
        op = OperationSpec()
        assert op.to_dict() == {}

    def test_operation_with_methods(self):
        """Test operation with HTTP methods."""
        op = OperationSpec(
            methods=["GET", "POST"]
        )
        result = op.to_dict()
        assert "methods" in result
        assert "GET" in result["methods"]

    def test_operation_with_paths(self):
        """Test operation with path restrictions."""
        op = OperationSpec(
            paths=["/api/*", "/health"]
        )
        result = op.to_dict()
        assert "paths" in result

    def test_operation_with_hosts(self):
        """Test operation with host restrictions."""
        op = OperationSpec(
            hosts=["api.example.com"]
        )
        result = op.to_dict()
        assert "hosts" in result


class TestAccessRule:
    """Tests for AccessRule."""

    def test_empty_rule(self):
        """Test empty access rule."""
        rule = AccessRule()
        assert rule.to_dict() == {}

    def test_rule_with_source_and_operation(self):
        """Test complete access rule."""
        source = Source(namespaces=["trusted-ns"])
        operation = OperationSpec(methods=["GET"], paths=["/api/*"])

        rule = AccessRule(
            from_sources=[source],
            to_operations=[operation]
        )
        result = rule.to_dict()

        assert "from" in result
        assert "to" in result

    def test_rule_with_conditions(self):
        """Test rule with when conditions."""
        rule = AccessRule(
            when_conditions=[
                {"key": "request.headers[x-token]", "values": ["valid-token"]}
            ]
        )
        result = rule.to_dict()
        assert "when" in result


class TestAuthorizationPolicy:
    """Tests for AuthorizationPolicy configuration."""

    def test_deny_all_policy(self):
        """Test deny-all policy creation."""
        policy = AuthorizationPolicy(
            name="deny-all",
            namespace="maestro",
            action=AuthorizationAction.DENY,
        )
        manifest = policy.to_manifest()

        assert manifest["metadata"]["name"] == "deny-all"
        assert manifest["spec"]["action"] == "DENY"

    def test_allow_policy_with_rules(self):
        """Test allow policy with rules."""
        source = Source(namespaces=["frontend"])
        rule = AccessRule(from_sources=[source])

        policy = AuthorizationPolicy(
            name="allow-frontend",
            namespace="backend",
            action=AuthorizationAction.ALLOW,
            rules=[rule],
        )
        manifest = policy.to_manifest()

        assert manifest["metadata"]["name"] == "allow-frontend"
        assert "rules" in manifest["spec"]

    def test_policy_with_selector(self):
        """Test policy with workload selector."""
        policy = AuthorizationPolicy(
            name="api-policy",
            namespace="default",
            selector={"app": "api-gateway"},
        )
        manifest = policy.to_manifest()

        assert "selector" in manifest["spec"]
        assert manifest["spec"]["selector"]["matchLabels"]["app"] == "api-gateway"


class TestJWTRule:
    """Tests for JWT validation rules."""

    def test_basic_jwt_rule(self):
        """Test basic JWT rule."""
        rule = JWTRule(
            issuer="https://auth.example.com",
            jwks_uri="https://auth.example.com/.well-known/jwks.json",
        )
        result = rule.to_dict()

        assert result["issuer"] == "https://auth.example.com"
        assert "jwksUri" in result

    def test_jwt_rule_with_audiences(self):
        """Test JWT rule with audience validation."""
        rule = JWTRule(
            issuer="https://auth.example.com",
            jwks_uri="https://auth.example.com/.well-known/jwks.json",
            audiences=["api-service", "web-app"],
        )
        result = rule.to_dict()

        assert "audiences" in result
        assert len(result["audiences"]) == 2

    def test_jwt_rule_with_custom_headers(self):
        """Test JWT rule with custom header extraction."""
        rule = JWTRule(
            issuer="https://auth.example.com",
            jwks_uri="https://auth.example.com/.well-known/jwks.json",
            from_headers=[
                {"name": "x-jwt-token", "prefix": "Bearer "}
            ],
        )
        result = rule.to_dict()

        assert "fromHeaders" in result


class TestRequestAuthentication:
    """Tests for RequestAuthentication configuration."""

    def test_basic_request_authentication(self):
        """Test basic RequestAuthentication."""
        jwt_rule = JWTRule(
            issuer="https://auth.example.com",
            jwks_uri="https://auth.example.com/.well-known/jwks.json",
        )
        request_auth = RequestAuthentication(
            name="jwt-auth",
            namespace="default",
            jwt_rules=[jwt_rule],
        )
        manifest = request_auth.to_manifest()

        assert manifest["kind"] == "RequestAuthentication"
        assert "jwtRules" in manifest["spec"]

    def test_request_authentication_with_selector(self):
        """Test RequestAuthentication with selector."""
        request_auth = RequestAuthentication(
            name="gateway-jwt",
            namespace="istio-system",
            selector={"app": "istio-ingressgateway"},
        )
        manifest = request_auth.to_manifest()

        assert "selector" in manifest["spec"]


class TestZeroTrustPolicy:
    """Tests for ZeroTrustPolicy high-level interface."""

    def test_policy_initialization(self):
        """Test ZeroTrustPolicy initialization."""
        policy = ZeroTrustPolicy()
        assert policy.kubeconfig is None
        assert policy.authz_manager is not None
        assert policy.jwt_validator is not None

    @patch("subprocess.run")
    def test_apply_default_deny(self, mock_run):
        """Test applying default deny policy."""
        mock_run.return_value = Mock(returncode=0, stdout="created", stderr="")

        policy = ZeroTrustPolicy()
        result = policy.apply_default_deny("test-namespace")

        assert result["success"] is True
        assert result["action"] == "DENY"

    @patch("subprocess.run")
    def test_allow_service_to_service(self, mock_run):
        """Test creating service-to-service allow rule."""
        mock_run.return_value = Mock(returncode=0, stdout="created", stderr="")

        policy = ZeroTrustPolicy()
        result = policy.allow_service_to_service(
            name="allow-frontend-to-backend",
            namespace="backend",
            from_service="frontend",
            from_namespace="frontend-ns",
            to_paths=["/api/*"],
            to_methods=["GET", "POST"],
        )

        assert result["success"] is True


class TestAuthorizationPolicyManager:
    """Tests for AuthorizationPolicyManager."""

    @patch("subprocess.run")
    def test_create_deny_all(self, mock_run):
        """Test creating deny-all policy."""
        mock_run.return_value = Mock(returncode=0, stdout="created", stderr="")

        manager = AuthorizationPolicyManager()
        result = manager.create_deny_all("test-namespace")

        assert result["success"] is True

    @patch("subprocess.run")
    def test_create_allow_all(self, mock_run):
        """Test creating allow-all policy."""
        mock_run.return_value = Mock(returncode=0, stdout="created", stderr="")

        manager = AuthorizationPolicyManager()
        result = manager.create_allow_all("test-namespace")

        assert result["success"] is True

    @patch("subprocess.run")
    def test_get_policies(self, mock_run):
        """Test getting authorization policies."""
        mock_run.return_value = Mock(
            returncode=0,
            stdout=json.dumps({
                "items": [{
                    "metadata": {"name": "deny-all", "namespace": "test"},
                    "spec": {"action": "DENY", "rules": []}
                }]
            }),
            stderr=""
        )

        manager = AuthorizationPolicyManager()
        policies = manager.get_policies("test")

        assert len(policies) == 1
        assert policies[0]["name"] == "deny-all"


class TestJWTValidator:
    """Tests for JWTValidator."""

    @patch("subprocess.run")
    def test_create_request_authentication(self, mock_run):
        """Test creating RequestAuthentication."""
        mock_run.return_value = Mock(returncode=0, stdout="created", stderr="")

        jwt_rule = JWTRule(
            issuer="https://auth.example.com",
            jwks_uri="https://auth.example.com/.well-known/jwks.json",
        )

        validator = JWTValidator()
        result = validator.create_request_authentication(
            name="jwt-auth",
            namespace="default",
            jwt_rules=[jwt_rule],
        )

        assert result["success"] is True
        assert result["jwt_rules_count"] == 1

    @patch("subprocess.run")
    def test_require_jwt_for_ingress(self, mock_run):
        """Test requiring JWT for ingress gateway."""
        mock_run.return_value = Mock(returncode=0, stdout="created", stderr="")

        validator = JWTValidator()
        result = validator.require_jwt_for_ingress(
            namespace="maestro",
            issuer="https://auth.example.com",
            jwks_uri="https://auth.example.com/.well-known/jwks.json",
        )

        assert result["request_auth_created"] is True
