"""
Tests for mTLS Manager module.

Tests AC-2: mTLS implementation for service-to-service communication
EPIC: MD-2782
"""

import pytest
import json
from unittest.mock import Mock, patch
from datetime import datetime, timedelta

from maestro_hive.security.network.mtls_manager import (
    TLSMode,
    PortLevelMTLS,
    PeerAuthenticationPolicy,
    DestinationRuleTLS,
    CertificateInfo,
    MTLSManager,
    CertificateRotator,
    SPIFFEValidator,
)


class TestTLSMode:
    """Tests for TLSMode enumeration."""

    def test_all_modes_exist(self):
        """Test all expected TLS modes exist."""
        modes = [m.value for m in TLSMode]
        assert "STRICT" in modes
        assert "PERMISSIVE" in modes
        assert "DISABLE" in modes
        assert "UNSET" in modes

    def test_strict_mode_value(self):
        """Test STRICT mode value."""
        assert TLSMode.STRICT.value == "STRICT"


class TestPeerAuthenticationPolicy:
    """Tests for PeerAuthenticationPolicy configuration."""

    def test_default_policy(self):
        """Test default PeerAuthentication policy."""
        policy = PeerAuthenticationPolicy(
            name="default",
            namespace="maestro",
        )
        assert policy.mtls_mode == TLSMode.STRICT
        assert policy.selector is None

    def test_policy_with_selector(self):
        """Test policy with workload selector."""
        policy = PeerAuthenticationPolicy(
            name="app-policy",
            namespace="maestro",
            mtls_mode=TLSMode.STRICT,
            selector={"app": "my-service"},
        )
        assert policy.selector == {"app": "my-service"}

    def test_policy_manifest_generation(self):
        """Test manifest generation."""
        policy = PeerAuthenticationPolicy(
            name="strict-mtls",
            namespace="default",
            mtls_mode=TLSMode.STRICT,
        )
        manifest = policy.to_manifest()

        assert manifest["apiVersion"] == "security.istio.io/v1beta1"
        assert manifest["kind"] == "PeerAuthentication"
        assert manifest["metadata"]["name"] == "strict-mtls"
        assert manifest["spec"]["mtls"]["mode"] == "STRICT"

    def test_port_level_mtls(self):
        """Test port-level mTLS configuration."""
        policy = PeerAuthenticationPolicy(
            name="port-specific",
            namespace="default",
            mtls_mode=TLSMode.STRICT,
            port_level_mtls={
                8080: PortLevelMTLS.PERMISSIVE,
                9090: PortLevelMTLS.DISABLE,
            },
        )
        manifest = policy.to_manifest()

        assert "portLevelMtls" in manifest["spec"]
        assert manifest["spec"]["portLevelMtls"]["8080"]["mode"] == "PERMISSIVE"
        assert manifest["spec"]["portLevelMtls"]["9090"]["mode"] == "DISABLE"


class TestDestinationRuleTLS:
    """Tests for DestinationRule TLS settings."""

    def test_default_tls_settings(self):
        """Test default TLS settings."""
        dr_tls = DestinationRuleTLS(
            name="test-dr",
            namespace="default",
            host="test-service",
        )
        assert dr_tls.tls_mode == "ISTIO_MUTUAL"

    def test_tls_manifest_generation(self):
        """Test TLS manifest generation."""
        dr_tls = DestinationRuleTLS(
            name="test-dr",
            namespace="default",
            host="test-service.default.svc.cluster.local",
            tls_mode="ISTIO_MUTUAL",
        )
        manifest = dr_tls.to_manifest()

        assert manifest["spec"]["trafficPolicy"]["tls"]["mode"] == "ISTIO_MUTUAL"
        assert manifest["spec"]["host"] == "test-service.default.svc.cluster.local"


class TestCertificateInfo:
    """Tests for CertificateInfo."""

    def test_valid_certificate(self):
        """Test valid certificate check."""
        now = datetime.utcnow()
        cert = CertificateInfo(
            subject="CN=test",
            issuer="CN=CA",
            serial_number="123456",
            not_before=now - timedelta(days=1),
            not_after=now + timedelta(days=30),
        )
        assert cert.is_valid is True
        assert cert.days_until_expiry >= 29  # Allow for timing edge case

    def test_expired_certificate(self):
        """Test expired certificate detection."""
        now = datetime.utcnow()
        cert = CertificateInfo(
            subject="CN=test",
            issuer="CN=CA",
            serial_number="123456",
            not_before=now - timedelta(days=60),
            not_after=now - timedelta(days=1),
        )
        assert cert.is_valid is False

    def test_not_yet_valid_certificate(self):
        """Test not-yet-valid certificate detection."""
        now = datetime.utcnow()
        cert = CertificateInfo(
            subject="CN=test",
            issuer="CN=CA",
            serial_number="123456",
            not_before=now + timedelta(days=1),
            not_after=now + timedelta(days=30),
        )
        assert cert.is_valid is False


class TestMTLSManager:
    """Tests for MTLSManager."""

    def test_manager_initialization(self):
        """Test manager initialization."""
        manager = MTLSManager()
        assert manager.kubeconfig is None

    @patch("subprocess.run")
    def test_enable_strict_mtls(self, mock_run):
        """Test enabling STRICT mTLS."""
        mock_run.return_value = Mock(returncode=0, stdout="created", stderr="")

        manager = MTLSManager()
        result = manager.enable_strict_mtls("test-namespace")

        assert result["success"] is True
        assert result["mtls_mode"] == "STRICT"
        assert result["namespace"] == "test-namespace"

    @patch("subprocess.run")
    def test_enable_permissive_mtls(self, mock_run):
        """Test enabling PERMISSIVE mTLS."""
        mock_run.return_value = Mock(returncode=0, stdout="created", stderr="")

        manager = MTLSManager()
        result = manager.enable_permissive_mtls("test-namespace")

        assert result["success"] is True
        assert result["mtls_mode"] == "PERMISSIVE"

    @patch("subprocess.run")
    def test_get_peer_authentications(self, mock_run):
        """Test getting PeerAuthentication policies."""
        mock_run.return_value = Mock(
            returncode=0,
            stdout=json.dumps({
                "items": [{
                    "metadata": {"name": "default", "namespace": "test"},
                    "spec": {"mtls": {"mode": "STRICT"}}
                }]
            }),
            stderr=""
        )

        manager = MTLSManager()
        policies = manager.get_peer_authentications("test")

        assert len(policies) == 1
        assert policies[0]["name"] == "default"
        assert policies[0]["mtls_mode"] == "STRICT"

    @patch("subprocess.run")
    def test_get_mesh_mtls_status(self, mock_run):
        """Test getting mesh mTLS status."""
        mock_run.return_value = Mock(
            returncode=0,
            stdout=json.dumps({
                "items": [{
                    "metadata": {"name": "default", "namespace": "istio-system"},
                    "spec": {"mtls": {"mode": "STRICT"}}
                }]
            }),
            stderr=""
        )

        manager = MTLSManager()
        status = manager.get_mesh_mtls_status()

        assert status["mesh_mtls_enabled"] is True
        assert status["mesh_mtls_mode"] == "STRICT"


class TestCertificateRotator:
    """Tests for CertificateRotator."""

    def test_rotator_initialization(self):
        """Test rotator initialization."""
        rotator = CertificateRotator()
        assert rotator.kubeconfig is None

    @patch("subprocess.run")
    def test_trigger_cert_rotation(self, mock_run):
        """Test triggering certificate rotation."""
        mock_run.return_value = Mock(returncode=0, stdout="restarted", stderr="")

        rotator = CertificateRotator()
        result = rotator.trigger_cert_rotation()

        assert result["success"] is True
        assert result["action"] == "cert_rotation_triggered"


class TestSPIFFEValidator:
    """Tests for SPIFFEValidator."""

    def test_validator_initialization(self):
        """Test validator initialization."""
        validator = SPIFFEValidator()
        assert validator.trust_domain == "cluster.local"

    def test_custom_trust_domain(self):
        """Test custom trust domain."""
        validator = SPIFFEValidator(trust_domain="example.com")
        assert validator.trust_domain == "example.com"

    def test_generate_spiffe_id(self):
        """Test SPIFFE ID generation."""
        validator = SPIFFEValidator()
        spiffe_id = validator.generate_spiffe_id("default", "my-service")

        assert spiffe_id == "spiffe://cluster.local/ns/default/sa/my-service"

    def test_validate_valid_spiffe_id(self):
        """Test validating a valid SPIFFE ID."""
        validator = SPIFFEValidator()
        result = validator.validate_spiffe_id(
            "spiffe://cluster.local/ns/default/sa/my-service"
        )

        assert result["valid"] is True
        assert result["trust_domain"] == "cluster.local"
        assert result["namespace"] == "default"
        assert result["service_account"] == "my-service"

    def test_validate_invalid_spiffe_id(self):
        """Test validating an invalid SPIFFE ID."""
        validator = SPIFFEValidator()
        result = validator.validate_spiffe_id("invalid-spiffe-id")

        assert result["valid"] is False
        assert "error" in result

    def test_parse_spiffe_id(self):
        """Test parsing SPIFFE ID."""
        validator = SPIFFEValidator()
        parsed = validator.parse_spiffe_id(
            "spiffe://cluster.local/ns/maestro/sa/api-gateway"
        )

        assert parsed is not None
        assert parsed["namespace"] == "maestro"
        assert parsed["service_account"] == "api-gateway"

    def test_parse_invalid_spiffe_id(self):
        """Test parsing invalid SPIFFE ID returns None."""
        validator = SPIFFEValidator()
        parsed = validator.parse_spiffe_id("not-a-spiffe-id")

        assert parsed is None
