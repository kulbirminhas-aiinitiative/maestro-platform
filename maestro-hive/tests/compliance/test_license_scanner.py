#!/usr/bin/env python3
"""Tests for license_scanner module."""

import pytest
import tempfile
import os
from pathlib import Path

from maestro_hive.compliance.license_scanner import (
    LicenseScanner,
    LicensePolicy,
    LicenseRisk,
    LicenseInfo,
    ScanResult,
    get_license_scanner
)


class TestLicenseScanner:
    """Tests for LicenseScanner class."""

    def test_scanner_initialization(self):
        """Test scanner initializes with default policy."""
        scanner = LicenseScanner()
        assert scanner.policy is not None

    def test_scanner_with_custom_policy(self):
        """Test scanner with custom policy."""
        policy = LicensePolicy(
            allowed_risks=[LicenseRisk.LOW, LicenseRisk.MEDIUM],
            denied_licenses=['GPL-3.0'],
            require_attribution=True
        )
        scanner = LicenseScanner(policy=policy)
        assert scanner.policy == policy
        assert LicenseRisk.LOW in scanner.policy.allowed_risks

    def test_scan_empty_directory(self):
        """Test scanning empty directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            scanner = LicenseScanner()
            result = scanner.scan(tmpdir)
            assert result.project_path == tmpdir
            assert len(result.licenses) == 0
            assert result.compliant is True

    def test_scan_with_requirements_txt(self):
        """Test scanning project with requirements.txt."""
        with tempfile.TemporaryDirectory() as tmpdir:
            req_file = Path(tmpdir) / "requirements.txt"
            req_file.write_text("requests==2.28.0\nflask>=2.0\n")

            scanner = LicenseScanner()
            result = scanner.scan(tmpdir)
            assert result.project_path == tmpdir

    def test_scan_with_package_json(self):
        """Test scanning project with package.json."""
        with tempfile.TemporaryDirectory() as tmpdir:
            pkg_file = Path(tmpdir) / "package.json"
            pkg_file.write_text('{"dependencies": {"lodash": "^4.17.21"}}')

            scanner = LicenseScanner()
            result = scanner.scan(tmpdir)
            assert result.project_path == tmpdir

    def test_license_risk_classification(self):
        """Test license risk classification."""
        scanner = LicenseScanner()

        # MIT should be low risk
        assert scanner._classify_risk('MIT') == LicenseRisk.LOW
        assert scanner._classify_risk('Apache-2.0') == LicenseRisk.LOW

        # GPL should be higher risk
        assert scanner._classify_risk('GPL-3.0') in [LicenseRisk.MEDIUM, LicenseRisk.HIGH]

    def test_get_license_scanner_factory(self):
        """Test factory function."""
        scanner = get_license_scanner()
        assert isinstance(scanner, LicenseScanner)


class TestLicensePolicy:
    """Tests for LicensePolicy dataclass."""

    def test_default_policy(self):
        """Test default policy creation."""
        policy = LicensePolicy()
        assert policy.allowed_risks == []
        assert policy.denied_licenses == []
        assert policy.require_attribution is False

    def test_policy_with_risks(self):
        """Test policy with allowed risks."""
        policy = LicensePolicy(
            allowed_risks=[LicenseRisk.LOW, LicenseRisk.MEDIUM]
        )
        assert len(policy.allowed_risks) == 2

    def test_policy_to_dict(self):
        """Test policy serialization."""
        policy = LicensePolicy(
            allowed_risks=[LicenseRisk.LOW],
            denied_licenses=['GPL-3.0'],
            require_attribution=True
        )
        data = policy.to_dict()
        assert 'allowed_risks' in data
        assert 'denied_licenses' in data
        assert data['require_attribution'] is True


class TestLicenseInfo:
    """Tests for LicenseInfo dataclass."""

    def test_license_info_creation(self):
        """Test license info creation."""
        info = LicenseInfo(
            name='MIT License',
            spdx_id='MIT',
            risk=LicenseRisk.LOW,
            source='package.json'
        )
        assert info.name == 'MIT License'
        assert info.spdx_id == 'MIT'
        assert info.compliant is None  # Not yet checked

    def test_license_info_to_dict(self):
        """Test license info serialization."""
        info = LicenseInfo(
            name='Apache License 2.0',
            spdx_id='Apache-2.0',
            risk=LicenseRisk.LOW,
            source='requirements.txt',
            compliant=True
        )
        data = info.to_dict()
        assert data['name'] == 'Apache License 2.0'
        assert data['spdx_id'] == 'Apache-2.0'
        assert data['compliant'] is True
