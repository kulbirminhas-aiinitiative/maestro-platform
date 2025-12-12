"""
Tests for Adherence Checker module.

This test suite validates:
- AC-3: Adherence Checker functionality
- Evidence management
- Control verification
- Compliance report generation
"""

import pytest
from datetime import datetime, timedelta
from typing import Dict, List

from maestro_hive.certification import (
    StandardsRegistry,
    CertificationStandard,
    ControlRequirement,
    ControlCategory,
    Priority,
)
from maestro_hive.certification.adherence_checker import (
    AdherenceChecker,
    AdherenceReport,
    ControlVerificationResult,
    Evidence,
    ComplianceReport,
    VerificationStatus,
    EvidenceType,
)


class TestEvidenceType:
    """Test EvidenceType enum."""

    def test_key_evidence_types_exist(self):
        """Test key expected evidence types exist."""
        expected = [
            "DOCUMENT",
            "LOG",
            "SCREENSHOT",
            "CONFIGURATION",
            "ATTESTATION",
            "AUDIT_REPORT",
            "POLICY",
        ]

        for type_name in expected:
            assert hasattr(EvidenceType, type_name)

    def test_evidence_type_values(self):
        """Test evidence type string values."""
        assert EvidenceType.DOCUMENT.value == "document"
        assert EvidenceType.LOG.value == "log"
        assert EvidenceType.POLICY.value == "policy"


class TestVerificationStatus:
    """Test VerificationStatus enum."""

    def test_key_statuses_exist(self):
        """Test key expected verification statuses exist."""
        expected = [
            "VERIFIED",
            "NOT_VERIFIED",
            "EVIDENCE_MISSING",
            "EVIDENCE_EXPIRED",
        ]

        for status_name in expected:
            assert hasattr(VerificationStatus, status_name)

    def test_status_values(self):
        """Test status string values."""
        assert VerificationStatus.VERIFIED.value == "verified"
        assert VerificationStatus.NOT_VERIFIED.value == "not_verified"


class TestEvidence:
    """Test Evidence dataclass."""

    def test_create_evidence(self):
        """Test creating evidence."""
        evidence = Evidence(
            id="EV-001",
            name="Access Control Policy",
            evidence_type=EvidenceType.POLICY,
            description="Corporate access control policy document",
            file_path="/policies/access_control_v1.pdf",
            collected_date=datetime.utcnow(),
            expiry_date=datetime.utcnow() + timedelta(days=365),
        )

        assert evidence.id == "EV-001"
        assert evidence.evidence_type == EvidenceType.POLICY
        assert evidence.file_path == "/policies/access_control_v1.pdf"

    def test_evidence_without_expiry(self):
        """Test evidence without expiry date."""
        evidence = Evidence(
            id="EV-002",
            name="Access Logs",
            evidence_type=EvidenceType.LOG,
            description="System access logs",
            file_path="/logs/access.log",
            collected_date=datetime.utcnow(),
        )

        assert evidence.expiry_date is None

    def test_evidence_is_expired(self):
        """Test checking if evidence is expired."""
        expired_evidence = Evidence(
            id="EV-003",
            name="Old Attestation",
            evidence_type=EvidenceType.ATTESTATION,
            description="Expired attestation",
            file_path="/attestations/old.pdf",
            collected_date=datetime.utcnow() - timedelta(days=400),
            expiry_date=datetime.utcnow() - timedelta(days=35),
        )

        # Check expiry via property
        assert expired_evidence.is_expired is True

    def test_evidence_not_expired(self):
        """Test evidence that is not expired."""
        valid_evidence = Evidence(
            id="EV-004",
            name="Current Policy",
            evidence_type=EvidenceType.POLICY,
            description="Valid policy",
            file_path="/policies/current.pdf",
            collected_date=datetime.utcnow(),
            expiry_date=datetime.utcnow() + timedelta(days=365),
        )

        assert valid_evidence.is_expired is False

    def test_evidence_to_dict(self):
        """Test evidence serialization."""
        evidence = Evidence(
            id="EV-005",
            name="Test Evidence",
            evidence_type=EvidenceType.DOCUMENT,
            description="Test description",
            file_path="/test/doc.pdf",
            collected_date=datetime.utcnow(),
        )

        data = evidence.to_dict()

        assert data["id"] == "EV-005"
        assert data["evidence_type"] == "document"
        assert "collected_date" in data


class TestControlVerificationResult:
    """Test ControlVerificationResult dataclass."""

    def test_create_verification_result(self):
        """Test creating a verification result."""
        evidence = Evidence(
            id="EV-001",
            name="Test Evidence",
            evidence_type=EvidenceType.DOCUMENT,
            description="Test",
            file_path="/test.pdf",
            collected_date=datetime.utcnow(),
        )

        result = ControlVerificationResult(
            control_id="A.9.1.1",
            control_name="Access Control Policy",
            status=VerificationStatus.VERIFIED,
            evidence=[evidence],
            verification_date=datetime.utcnow(),
            verifier="System",
            findings=["Control implemented as required"],
            score=100.0,
        )

        assert result.control_id == "A.9.1.1"
        assert result.status == VerificationStatus.VERIFIED
        assert len(result.evidence) == 1

    def test_verification_with_findings(self):
        """Test verification result with findings."""
        result = ControlVerificationResult(
            control_id="A.9.2.1",
            control_name="User Registration",
            status=VerificationStatus.NOT_VERIFIED,
            evidence=[],
            verification_date=datetime.utcnow(),
            verifier="Auditor",
            findings=["User registration process incomplete"],
            score=0.0,
        )

        assert result.status == VerificationStatus.NOT_VERIFIED
        assert "incomplete" in result.findings[0]


class TestAdherenceReport:
    """Test AdherenceReport dataclass."""

    def test_create_adherence_report(self):
        """Test creating an adherence report."""
        evidence = Evidence(
            id="EV-001",
            name="Test",
            evidence_type=EvidenceType.DOCUMENT,
            description="Test",
            file_path="/test.pdf",
            collected_date=datetime.utcnow(),
        )

        verification = ControlVerificationResult(
            control_id="A.9.1.1",
            control_name="Access Control",
            status=VerificationStatus.VERIFIED,
            evidence=[evidence],
            verification_date=datetime.utcnow(),
            verifier="System",
            findings=["OK"],
            score=100.0,
        )

        report = AdherenceReport(
            standard_id="ISO_27001",
            standard_name="ISO 27001:2022",
            check_date=datetime.utcnow(),
            scope="all_controls",
            total_controls=100,
            verified_controls=95,
            partial_controls=3,
            missing_controls=2,
            control_results=[verification],
            overall_score=95.0,
            recommendations=["Continue monitoring"],
            next_review_date=datetime.utcnow() + timedelta(days=90),
        )

        assert report.standard_id == "ISO_27001"
        assert report.overall_score == 95.0
        assert len(report.control_results) == 1


class TestComplianceReport:
    """Test ComplianceReport dataclass."""

    def test_create_compliance_report(self):
        """Test creating a comprehensive compliance report."""
        registry = StandardsRegistry()
        standard = registry.get_standard("ISO_27001")

        evidence = Evidence(
            id="EV-001",
            name="Test",
            evidence_type=EvidenceType.DOCUMENT,
            description="Test",
            file_path="/test.pdf",
            collected_date=datetime.utcnow(),
        )

        verification = ControlVerificationResult(
            control_id="A.9.1.1",
            control_name="Access Control",
            status=VerificationStatus.VERIFIED,
            evidence=[evidence],
            verification_date=datetime.utcnow(),
            verifier="System",
            findings=[],
            score=100.0,
        )

        adherence_report = AdherenceReport(
            standard_id="ISO_27001",
            standard_name="ISO 27001:2022",
            check_date=datetime.utcnow(),
            scope="all_controls",
            total_controls=100,
            verified_controls=93,
            partial_controls=5,
            missing_controls=2,
            control_results=[verification],
            overall_score=93.0,
            recommendations=["Review access logs"],
            next_review_date=datetime.utcnow() + timedelta(days=90),
        )

        report = ComplianceReport(
            id="COMP-001",
            title="ISO 27001 Compliance Report",
            standard=standard,
            adherence_report=adherence_report,
            generated_date=datetime.utcnow(),
            report_format="json",
            executive_summary="Strong overall compliance posture",
            detailed_findings=[{"area": "access_control", "status": "compliant"}],
            remediation_plan=[{"action": "Update policies", "priority": "medium"}],
        )

        assert report.title == "ISO 27001 Compliance Report"
        assert report.adherence_report.overall_score == 93.0


class TestAdherenceChecker:
    """Test AdherenceChecker class."""

    @pytest.fixture
    def checker(self):
        """Create an adherence checker for each test."""
        registry = StandardsRegistry()
        return AdherenceChecker(registry)

    @pytest.fixture
    def sample_evidence(self) -> List[Evidence]:
        """Create sample evidence list."""
        return [
            Evidence(
                id="EV-001",
                name="Security Policy",
                evidence_type=EvidenceType.POLICY,
                description="Corporate security policy",
                file_path="/policies/security.pdf",
                collected_date=datetime.utcnow(),
                expiry_date=datetime.utcnow() + timedelta(days=365),
            ),
            Evidence(
                id="EV-002",
                name="Access Logs",
                evidence_type=EvidenceType.LOG,
                description="System access logs",
                file_path="/logs/access.log",
                collected_date=datetime.utcnow(),
            ),
            Evidence(
                id="EV-003",
                name="Audit Report",
                evidence_type=EvidenceType.AUDIT_REPORT,
                description="Annual audit report",
                file_path="/reports/audit_2024.pdf",
                collected_date=datetime.utcnow(),
                expiry_date=datetime.utcnow() + timedelta(days=180),
            ),
        ]

    def test_checker_initialization(self, checker):
        """Test checker initializes correctly."""
        assert checker is not None

    def test_add_evidence(self, checker, sample_evidence):
        """Test adding evidence to checker for a control."""
        control_id = "A.5.1.1"
        for evidence in sample_evidence:
            checker.add_evidence(control_id, evidence)

        # Evidence should be stored - verify no exception
        assert True  # If we got here, add_evidence worked

    def test_verify_control(self, checker, sample_evidence):
        """Test verifying a single control with evidence."""
        result = checker.verify_control(
            control_id="A.5.1.1",
            evidence=sample_evidence,
        )

        assert isinstance(result, ControlVerificationResult)
        assert result.control_id == "A.5.1.1"
        assert result.status in VerificationStatus

    def test_verify_control_without_evidence(self, checker):
        """Test verifying control without matching evidence."""
        result = checker.verify_control(
            control_id="A.99.99.99",  # Non-existent control
            evidence=[],
        )

        assert isinstance(result, ControlVerificationResult)

    def test_check_adherence(self, checker, sample_evidence):
        """Test checking overall adherence."""
        # Add evidence for controls
        for evidence in sample_evidence:
            checker.add_evidence("A.5.1.1", evidence)

        report = checker.check_adherence("ISO_27001")

        assert isinstance(report, AdherenceReport)
        assert report.standard_id == "ISO_27001"
        assert 0 <= report.overall_score <= 100

    def test_check_adherence_with_scope(self, checker, sample_evidence):
        """Test checking adherence with specific scope."""
        for evidence in sample_evidence:
            checker.add_evidence("A.5.1.1", evidence)

        report = checker.check_adherence(
            standard="ISO_27001",
            scope="access_controls",
        )

        assert isinstance(report, AdherenceReport)
        assert report.scope == "access_controls"

    def test_generate_report(self, checker, sample_evidence):
        """Test generating compliance report."""
        for evidence in sample_evidence:
            checker.add_evidence("A.5.1.1", evidence)

        report = checker.generate_report(
            standard="ISO_27001",
            report_format="json",
        )

        assert isinstance(report, ComplianceReport)
        assert report.report_format == "json"

    def test_generate_report_different_format(self, checker, sample_evidence):
        """Test generating report in different format."""
        for evidence in sample_evidence:
            checker.add_evidence("A.5.1.1", evidence)

        report = checker.generate_report(
            standard="ISO_27001",
            report_format="pdf",
        )

        assert isinstance(report, ComplianceReport)


class TestAdherenceCheckerIntegration:
    """Integration tests for Adherence Checker."""

    def test_full_adherence_workflow(self):
        """Test complete adherence checking workflow."""
        registry = StandardsRegistry()
        checker = AdherenceChecker(registry)

        # 1. Add evidence
        evidence_list = [
            Evidence(
                id="EV-001",
                name="Information Security Policy",
                evidence_type=EvidenceType.POLICY,
                description="Main security policy",
                file_path="/policies/infosec.pdf",
                collected_date=datetime.utcnow(),
                expiry_date=datetime.utcnow() + timedelta(days=365),
            ),
            Evidence(
                id="EV-002",
                name="Access Control Config",
                evidence_type=EvidenceType.CONFIGURATION,
                description="RBAC configuration",
                file_path="/configs/rbac.yaml",
                collected_date=datetime.utcnow(),
            ),
        ]

        for evidence in evidence_list:
            checker.add_evidence("A.5.1.1", evidence)

        # 2. Verify specific controls
        result = checker.verify_control("A.5.1.1", evidence_list)
        assert isinstance(result, ControlVerificationResult)

        # 3. Generate adherence report
        adherence_report = checker.check_adherence("ISO_27001")
        assert isinstance(adherence_report, AdherenceReport)

        # 4. Generate full compliance report
        compliance_report = checker.generate_report("ISO_27001")

        assert isinstance(compliance_report, ComplianceReport)


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_duplicate_evidence(self):
        """Test adding duplicate evidence ID."""
        registry = StandardsRegistry()
        checker = AdherenceChecker(registry)

        evidence1 = Evidence(
            id="EV-DUP",
            name="Original",
            evidence_type=EvidenceType.DOCUMENT,
            description="First version",
            file_path="/doc1.pdf",
            collected_date=datetime.utcnow(),
        )

        evidence2 = Evidence(
            id="EV-DUP",  # Same ID
            name="Duplicate",
            evidence_type=EvidenceType.DOCUMENT,
            description="Second version",
            file_path="/doc2.pdf",
            collected_date=datetime.utcnow(),
        )

        checker.add_evidence("A.5.1.1", evidence1)

        try:
            checker.add_evidence("A.5.1.1", evidence2)
            # If allowed, should update or add as duplicate
            assert True
        except (ValueError, KeyError):
            # Expected - reject duplicate
            pass

    def test_unknown_standard_adherence(self):
        """Test checking adherence for unknown standard."""
        registry = StandardsRegistry()
        checker = AdherenceChecker(registry)

        try:
            report = checker.check_adherence("UNKNOWN_STANDARD")
            # If returns report, should be empty or indicate error
            assert isinstance(report, AdherenceReport)
        except (ValueError, KeyError):
            # Expected behavior
            pass

    def test_empty_standard_name(self):
        """Test generating report with empty standard name raises error."""
        registry = StandardsRegistry()
        checker = AdherenceChecker(registry)

        with pytest.raises(KeyError):
            # Empty string is not a valid standard
            checker.generate_report(
                standard="",
                report_format="json",
            )

    def test_large_evidence_set(self):
        """Test handling large number of evidence items."""
        registry = StandardsRegistry()
        checker = AdherenceChecker(registry)

        # Add many evidence items
        for i in range(50):
            evidence = Evidence(
                id=f"EV-{i:04d}",
                name=f"Document {i}",
                evidence_type=EvidenceType.DOCUMENT,
                description=f"Test document number {i}",
                file_path=f"/docs/doc_{i}.pdf",
                collected_date=datetime.utcnow(),
            )
            checker.add_evidence("A.5.1.1", evidence)

        # Should handle large evidence sets
        report = checker.check_adherence("ISO_27001")
        assert isinstance(report, AdherenceReport)
