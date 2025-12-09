"""
Tests for Kubernetes NetworkPolicy module.

Tests AC-4: Kubernetes NetworkPolicy for pod-to-pod traffic control
EPIC: MD-2782
"""

import pytest
import json
from unittest.mock import Mock, patch

from maestro_hive.security.network.network_policy import (
    PolicyType,
    Protocol,
    PodSelector,
    NamespaceSelector,
    IPBlock,
    NetworkPolicyPort,
    IngressRule,
    EgressRule,
    NetworkPolicy,
    DefaultDenyPolicy,
    NamespaceIsolation,
    NetworkPolicyManager,
)


class TestPolicyType:
    """Tests for PolicyType enumeration."""

    def test_ingress_type(self):
        """Test ingress policy type."""
        assert PolicyType.INGRESS.value == "Ingress"

    def test_egress_type(self):
        """Test egress policy type."""
        assert PolicyType.EGRESS.value == "Egress"


class TestProtocol:
    """Tests for Protocol enumeration."""

    def test_all_protocols_exist(self):
        """Test all expected protocols exist."""
        protocols = [p.value for p in Protocol]
        assert "TCP" in protocols
        assert "UDP" in protocols
        assert "SCTP" in protocols


class TestPodSelector:
    """Tests for PodSelector configuration."""

    def test_empty_selector(self):
        """Test empty pod selector (selects all)."""
        selector = PodSelector()
        assert selector.to_dict() == {}

    def test_selector_with_labels(self):
        """Test pod selector with labels."""
        selector = PodSelector(
            match_labels={"app": "my-service", "version": "v1"}
        )
        result = selector.to_dict()
        assert "matchLabels" in result
        assert result["matchLabels"]["app"] == "my-service"

    def test_selector_with_expressions(self):
        """Test pod selector with expressions."""
        selector = PodSelector(
            match_expressions=[
                {"key": "app", "operator": "In", "values": ["web", "api"]}
            ]
        )
        result = selector.to_dict()
        assert "matchExpressions" in result


class TestIPBlock:
    """Tests for IPBlock configuration."""

    def test_basic_ip_block(self):
        """Test basic IP block."""
        block = IPBlock(cidr="10.0.0.0/8")
        result = block.to_dict()
        assert result["cidr"] == "10.0.0.0/8"

    def test_ip_block_with_exceptions(self):
        """Test IP block with CIDR exceptions."""
        block = IPBlock(
            cidr="10.0.0.0/8",
            except_cidrs=["10.1.0.0/16", "10.2.0.0/16"]
        )
        result = block.to_dict()
        assert "except" in result
        assert len(result["except"]) == 2


class TestNetworkPolicyPort:
    """Tests for NetworkPolicyPort configuration."""

    def test_default_port(self):
        """Test default port settings."""
        port = NetworkPolicyPort(port=80)
        result = port.to_dict()
        assert result["port"] == 80
        assert result["protocol"] == "TCP"

    def test_udp_port(self):
        """Test UDP port."""
        port = NetworkPolicyPort(port=53, protocol=Protocol.UDP)
        result = port.to_dict()
        assert result["protocol"] == "UDP"

    def test_port_range(self):
        """Test port range."""
        port = NetworkPolicyPort(port=8000, end_port=8100)
        result = port.to_dict()
        assert result["port"] == 8000
        assert result["endPort"] == 8100


class TestIngressRule:
    """Tests for IngressRule configuration."""

    def test_empty_ingress_rule(self):
        """Test empty ingress rule."""
        rule = IngressRule()
        assert rule.to_dict() == {}

    def test_ingress_from_namespace(self):
        """Test ingress from specific namespace."""
        rule = IngressRule(
            from_selectors=[{
                "namespaceSelector": {
                    "matchLabels": {"kubernetes.io/metadata.name": "frontend"}
                }
            }]
        )
        result = rule.to_dict()
        assert "from" in result

    def test_ingress_with_ports(self):
        """Test ingress with port restrictions."""
        rule = IngressRule(
            ports=[
                NetworkPolicyPort(port=80),
                NetworkPolicyPort(port=443),
            ]
        )
        result = rule.to_dict()
        assert "ports" in result
        assert len(result["ports"]) == 2


class TestEgressRule:
    """Tests for EgressRule configuration."""

    def test_empty_egress_rule(self):
        """Test empty egress rule."""
        rule = EgressRule()
        assert rule.to_dict() == {}

    def test_egress_to_cidr(self):
        """Test egress to CIDR block."""
        rule = EgressRule(
            to_selectors=[{
                "ipBlock": {"cidr": "0.0.0.0/0"}
            }]
        )
        result = rule.to_dict()
        assert "to" in result

    def test_egress_with_dns_ports(self):
        """Test egress with DNS ports."""
        rule = EgressRule(
            ports=[
                NetworkPolicyPort(port=53, protocol=Protocol.UDP),
                NetworkPolicyPort(port=53, protocol=Protocol.TCP),
            ]
        )
        result = rule.to_dict()
        assert len(result["ports"]) == 2


class TestNetworkPolicy:
    """Tests for NetworkPolicy configuration."""

    def test_default_deny_ingress_manifest(self):
        """Test default deny ingress manifest generation."""
        policy = NetworkPolicy(
            name="default-deny-ingress",
            namespace="maestro",
            pod_selector=PodSelector(),
            policy_types=[PolicyType.INGRESS],
        )
        manifest = policy.to_manifest()

        assert manifest["apiVersion"] == "networking.k8s.io/v1"
        assert manifest["kind"] == "NetworkPolicy"
        assert manifest["spec"]["policyTypes"] == ["Ingress"]
        assert manifest["spec"]["ingress"] == []

    def test_default_deny_all_manifest(self):
        """Test default deny all traffic manifest."""
        policy = NetworkPolicy(
            name="default-deny-all",
            namespace="maestro",
            pod_selector=PodSelector(),
            policy_types=[PolicyType.INGRESS, PolicyType.EGRESS],
        )
        manifest = policy.to_manifest()

        assert "Ingress" in manifest["spec"]["policyTypes"]
        assert "Egress" in manifest["spec"]["policyTypes"]

    def test_policy_with_ingress_rules(self):
        """Test policy with ingress rules."""
        ingress_rule = IngressRule(
            from_selectors=[{
                "namespaceSelector": {
                    "matchLabels": {"kubernetes.io/metadata.name": "trusted"}
                }
            }],
            ports=[NetworkPolicyPort(port=8080)]
        )

        policy = NetworkPolicy(
            name="allow-trusted",
            namespace="backend",
            policy_types=[PolicyType.INGRESS],
            ingress_rules=[ingress_rule],
        )
        manifest = policy.to_manifest()

        assert len(manifest["spec"]["ingress"]) == 1

    def test_policy_with_labels(self):
        """Test policy with metadata labels."""
        policy = NetworkPolicy(
            name="labeled-policy",
            namespace="default",
            labels={"managed-by": "maestro"},
            annotations={"description": "Test policy"},
        )
        manifest = policy.to_manifest()

        assert manifest["metadata"]["labels"]["managed-by"] == "maestro"
        assert "description" in manifest["metadata"]["annotations"]


class TestDefaultDenyPolicy:
    """Tests for DefaultDenyPolicy factory."""

    def test_create_deny_all_ingress(self):
        """Test creating deny all ingress policy."""
        factory = DefaultDenyPolicy(namespace="maestro")
        policy = factory.create_deny_all_ingress()

        assert policy.name == "default-deny-ingress"
        assert PolicyType.INGRESS in policy.policy_types
        assert PolicyType.EGRESS not in policy.policy_types

    def test_create_deny_all_egress(self):
        """Test creating deny all egress policy."""
        factory = DefaultDenyPolicy(namespace="maestro")
        policy = factory.create_deny_all_egress()

        assert policy.name == "default-deny-egress"
        assert PolicyType.EGRESS in policy.policy_types

    def test_create_deny_all(self):
        """Test creating deny all traffic policy."""
        factory = DefaultDenyPolicy(namespace="maestro")
        policy = factory.create_deny_all()

        assert policy.name == "default-deny-all"
        assert PolicyType.INGRESS in policy.policy_types
        assert PolicyType.EGRESS in policy.policy_types


class TestNamespaceIsolation:
    """Tests for NamespaceIsolation."""

    def test_isolation_policy_creation(self):
        """Test namespace isolation policy creation."""
        isolation = NamespaceIsolation(namespace="backend")
        policy = isolation.create_isolation_policy()

        assert policy.name == "backend-isolation"
        assert len(policy.policy_types) == 2

    def test_allow_from_namespace(self):
        """Test creating ingress rule from namespace."""
        isolation = NamespaceIsolation(namespace="backend")
        rule = isolation.allow_from_namespace("frontend")

        result = rule.to_dict()
        assert "from" in result

    def test_allow_to_namespace(self):
        """Test creating egress rule to namespace."""
        isolation = NamespaceIsolation(namespace="backend")
        rule = isolation.allow_to_namespace("database")

        result = rule.to_dict()
        assert "to" in result


class TestNetworkPolicyManager:
    """Tests for NetworkPolicyManager."""

    def test_manager_initialization(self):
        """Test manager initialization."""
        manager = NetworkPolicyManager()
        assert manager.kubeconfig is None

    @patch("subprocess.run")
    def test_apply_policy(self, mock_run):
        """Test applying NetworkPolicy."""
        mock_run.return_value = Mock(returncode=0, stdout="created", stderr="")

        policy = NetworkPolicy(
            name="test-policy",
            namespace="default",
            policy_types=[PolicyType.INGRESS],
        )

        manager = NetworkPolicyManager()
        result = manager.apply_policy(policy)

        assert result["success"] is True
        assert result["name"] == "test-policy"

    @patch("subprocess.run")
    def test_get_policies(self, mock_run):
        """Test getting NetworkPolicies."""
        mock_run.return_value = Mock(
            returncode=0,
            stdout=json.dumps({
                "items": [{
                    "metadata": {"name": "deny-all", "namespace": "test"},
                    "spec": {
                        "policyTypes": ["Ingress"],
                        "ingress": [],
                        "egress": []
                    }
                }]
            }),
            stderr=""
        )

        manager = NetworkPolicyManager()
        policies = manager.get_policies("test")

        assert len(policies) == 1
        assert policies[0]["name"] == "deny-all"

    @patch("subprocess.run")
    def test_create_default_deny(self, mock_run):
        """Test creating default deny policy."""
        mock_run.return_value = Mock(returncode=0, stdout="created", stderr="")

        manager = NetworkPolicyManager()
        result = manager.create_default_deny("test-namespace")

        assert result["success"] is True

    @patch("subprocess.run")
    def test_allow_ingress(self, mock_run):
        """Test creating ingress allow policy."""
        mock_run.return_value = Mock(returncode=0, stdout="created", stderr="")

        manager = NetworkPolicyManager()
        result = manager.allow_ingress(
            name="allow-frontend",
            namespace="backend",
            from_namespace="frontend",
            ports=[8080, 8443],
        )

        assert result["success"] is True

    @patch("subprocess.run")
    def test_allow_egress(self, mock_run):
        """Test creating egress allow policy."""
        mock_run.return_value = Mock(returncode=0, stdout="created", stderr="")

        manager = NetworkPolicyManager()
        result = manager.allow_egress(
            name="allow-external",
            namespace="backend",
            to_cidr="0.0.0.0/0",
            ports=[443],
        )

        assert result["success"] is True

    @patch("subprocess.run")
    def test_setup_namespace_isolation(self, mock_run):
        """Test setting up namespace isolation."""
        mock_run.return_value = Mock(returncode=0, stdout="created", stderr="")

        manager = NetworkPolicyManager()
        result = manager.setup_namespace_isolation(
            namespace="backend",
            allowed_namespaces=["frontend", "monitoring"],
        )

        assert result["success"] is True
        assert result["namespace"] == "backend"

    @patch("subprocess.run")
    def test_validate_policies(self, mock_run):
        """Test validating namespace policies."""
        mock_run.return_value = Mock(
            returncode=0,
            stdout=json.dumps({
                "items": [{
                    "metadata": {"name": "default-deny-ingress", "namespace": "test"},
                    "spec": {
                        "policyTypes": ["Ingress"],
                        "ingress": []
                    }
                }]
            }),
            stderr=""
        )

        manager = NetworkPolicyManager()
        result = manager.validate_policies("test")

        assert result["has_default_deny"] is True
        assert result["valid"] is True
