"""
Tests for Service Mesh configuration module.

Tests AC-1: Istio Service Mesh installation and configuration
EPIC: MD-2782
"""

import pytest
import json
from unittest.mock import Mock, patch, MagicMock

from maestro_hive.security.network.service_mesh import (
    IstioProfile,
    TrafficPolicy,
    IstioConfig,
    VirtualService,
    DestinationRule,
    IstioInstaller,
    SidecarInjector,
    IstioConfigManager,
    ServiceMeshConfig,
)


class TestIstioConfig:
    """Tests for IstioConfig dataclass."""

    def test_default_config(self):
        """Test default IstioConfig values."""
        config = IstioConfig()
        assert config.profile == IstioProfile.PRODUCTION
        assert config.namespace == "istio-system"
        assert config.enable_tracing is True
        assert config.pilot_replicas == 2

    def test_custom_config(self):
        """Test custom IstioConfig values."""
        config = IstioConfig(
            profile=IstioProfile.DEMO,
            namespace="custom-istio",
            proxy_cpu_request="200m",
            pilot_replicas=3,
        )
        assert config.profile == IstioProfile.DEMO
        assert config.namespace == "custom-istio"
        assert config.proxy_cpu_request == "200m"
        assert config.pilot_replicas == 3

    def test_to_yaml_generation(self):
        """Test YAML generation from config."""
        config = IstioConfig(profile=IstioProfile.PRODUCTION)
        yaml_output = config.to_yaml()

        assert "apiVersion: install.istio.io/v1alpha1" in yaml_output
        assert "kind: IstioOperator" in yaml_output
        assert "profile: production" in yaml_output
        assert "namespace: istio-system" in yaml_output


class TestVirtualService:
    """Tests for VirtualService configuration."""

    def test_virtual_service_creation(self):
        """Test VirtualService creation."""
        vs = VirtualService(
            name="test-vs",
            namespace="default",
            hosts=["test-service"],
            gateways=["mesh"],
        )
        assert vs.name == "test-vs"
        assert vs.hosts == ["test-service"]

    def test_virtual_service_manifest(self):
        """Test VirtualService manifest generation."""
        vs = VirtualService(
            name="test-vs",
            namespace="default",
            hosts=["test-service.default.svc.cluster.local"],
            http_routes=[{
                "route": [{"destination": {"host": "test-service", "port": {"number": 80}}}]
            }],
        )
        manifest = vs.to_manifest()

        assert manifest["apiVersion"] == "networking.istio.io/v1beta1"
        assert manifest["kind"] == "VirtualService"
        assert manifest["metadata"]["name"] == "test-vs"
        assert "test-service.default.svc.cluster.local" in manifest["spec"]["hosts"]


class TestDestinationRule:
    """Tests for DestinationRule configuration."""

    def test_destination_rule_creation(self):
        """Test DestinationRule creation."""
        dr = DestinationRule(
            name="test-dr",
            namespace="default",
            host="test-service",
            traffic_policy=TrafficPolicy.LEAST_CONN,
        )
        assert dr.name == "test-dr"
        assert dr.traffic_policy == TrafficPolicy.LEAST_CONN

    def test_destination_rule_manifest(self):
        """Test DestinationRule manifest generation."""
        dr = DestinationRule(
            name="test-dr",
            namespace="default",
            host="test-service",
            traffic_policy=TrafficPolicy.ROUND_ROBIN,
            subsets=[{"name": "v1", "labels": {"version": "v1"}}],
        )
        manifest = dr.to_manifest()

        assert manifest["apiVersion"] == "networking.istio.io/v1beta1"
        assert manifest["kind"] == "DestinationRule"
        assert manifest["spec"]["host"] == "test-service"
        assert manifest["spec"]["trafficPolicy"]["loadBalancer"]["simple"] == "ROUND_ROBIN"


class TestIstioInstaller:
    """Tests for IstioInstaller."""

    def test_installer_initialization(self):
        """Test installer initialization."""
        installer = IstioInstaller()
        assert installer.kubeconfig is None

    def test_installer_with_kubeconfig(self):
        """Test installer with custom kubeconfig."""
        installer = IstioInstaller(kubeconfig="/path/to/kubeconfig")
        assert installer.kubeconfig == "/path/to/kubeconfig"

    @patch("subprocess.run")
    def test_check_prerequisites(self, mock_run):
        """Test prerequisite checking."""
        mock_run.return_value = Mock(returncode=0, stdout="yes", stderr="")

        installer = IstioInstaller()
        checks = installer.check_prerequisites()

        assert "istioctl_available" in checks
        assert "kubernetes_accessible" in checks
        assert "sufficient_permissions" in checks


class TestSidecarInjector:
    """Tests for SidecarInjector."""

    def test_injector_initialization(self):
        """Test sidecar injector initialization."""
        injector = SidecarInjector()
        assert injector.kubeconfig is None

    @patch("subprocess.run")
    def test_enable_namespace_injection(self, mock_run):
        """Test enabling namespace injection."""
        mock_run.return_value = Mock(returncode=0, stdout="namespace/test labeled", stderr="")

        injector = SidecarInjector()
        result = injector.enable_namespace_injection("test")

        assert result["success"] is True
        assert result["namespace"] == "test"
        assert result["injection_enabled"] is True

    @patch("subprocess.run")
    def test_get_injection_status(self, mock_run):
        """Test getting injection status."""
        mock_run.return_value = Mock(returncode=0, stdout="enabled", stderr="")

        injector = SidecarInjector()
        result = injector.get_injection_status("test")

        assert result["namespace"] == "test"
        assert result["injection_enabled"] is True


class TestIstioConfigManager:
    """Tests for IstioConfigManager."""

    def test_config_manager_initialization(self):
        """Test config manager initialization."""
        manager = IstioConfigManager()
        assert manager.kubeconfig is None

    @patch("subprocess.run")
    def test_apply_virtual_service(self, mock_run):
        """Test applying VirtualService."""
        mock_run.return_value = Mock(returncode=0, stdout="virtualservice created", stderr="")

        vs = VirtualService(
            name="test-vs",
            namespace="default",
            hosts=["test-service"],
        )

        manager = IstioConfigManager()
        result = manager.apply_virtual_service(vs)

        assert result["success"] is True
        assert result["name"] == "test-vs"

    @patch("subprocess.run")
    def test_get_virtual_services(self, mock_run):
        """Test getting VirtualServices."""
        mock_run.return_value = Mock(
            returncode=0,
            stdout=json.dumps({
                "items": [{
                    "metadata": {"name": "test-vs", "namespace": "default"},
                    "spec": {"hosts": ["test-service"]}
                }]
            }),
            stderr=""
        )

        manager = IstioConfigManager()
        services = manager.get_virtual_services("default")

        assert len(services) == 1
        assert services[0]["name"] == "test-vs"


class TestServiceMeshConfig:
    """Tests for ServiceMeshConfig high-level interface."""

    def test_service_mesh_config_initialization(self):
        """Test ServiceMeshConfig initialization."""
        config = ServiceMeshConfig()
        assert config.kubeconfig is None
        assert config.installer is not None
        assert config.injector is not None
        assert config.config_manager is not None

    @patch("subprocess.run")
    def test_configure_namespace(self, mock_run):
        """Test namespace configuration."""
        mock_run.return_value = Mock(returncode=0, stdout="configured", stderr="")

        config = ServiceMeshConfig()
        result = config.configure_namespace(
            namespace="test",
            enable_injection=True,
            traffic_policy=TrafficPolicy.ROUND_ROBIN,
        )

        assert result["namespace"] == "test"
        assert "operations" in result


class TestIstioProfiles:
    """Tests for Istio profile enumeration."""

    def test_all_profiles_exist(self):
        """Test all expected profiles exist."""
        profiles = [p.value for p in IstioProfile]
        assert "default" in profiles
        assert "demo" in profiles
        assert "minimal" in profiles
        assert "production" in profiles
        assert "empty" in profiles

    def test_profile_values(self):
        """Test profile values are correct."""
        assert IstioProfile.PRODUCTION.value == "production"
        assert IstioProfile.DEMO.value == "demo"


class TestTrafficPolicies:
    """Tests for traffic policy enumeration."""

    def test_all_policies_exist(self):
        """Test all expected traffic policies exist."""
        policies = [p.value for p in TrafficPolicy]
        assert "ROUND_ROBIN" in policies
        assert "LEAST_CONN" in policies
        assert "RANDOM" in policies
        assert "PASSTHROUGH" in policies
