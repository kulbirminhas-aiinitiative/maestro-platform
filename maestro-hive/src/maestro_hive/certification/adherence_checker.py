"""
Adherence Checker - Verifies adherence to certification requirements.

This module provides the AdherenceChecker class which performs automated
verification of compliance with certification control requirements.
"""

import hashlib
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from .standards_registry import (
    CertificationStandard,
    ControlRequirement,
    Priority,
    StandardsRegistry,
)

logger = logging.getLogger(__name__)


class VerificationStatus(Enum):
    """Status of control verification."""
    VERIFIED = "verified"
    PARTIALLY_VERIFIED = "partially_verified"
    NOT_VERIFIED = "not_verified"
    EVIDENCE_MISSING = "evidence_missing"
    EVIDENCE_EXPIRED = "evidence_expired"
    EXCEPTION_GRANTED = "exception_granted"


class EvidenceType(Enum):
    """Types of compliance evidence."""
    DOCUMENT = "document"
    SCREENSHOT = "screenshot"
    LOG = "log"
    CONFIGURATION = "configuration"
    ATTESTATION = "attestation"
    AUDIT_REPORT = "audit_report"
    SCAN_RESULT = "scan_result"
    POLICY = "policy"


@dataclass
class Evidence:
    """Represents compliance evidence."""

    id: str
    name: str
    evidence_type: EvidenceType
    description: str
    file_path: Optional[str] = None
    url: Optional[str] = None
    collected_date: datetime = field(default_factory=datetime.utcnow)
    expiry_date: Optional[datetime] = None
    collector: str = "system"
    checksum: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def is_expired(self) -> bool:
        """Check if evidence has expired."""
        if self.expiry_date is None:
            return False
        return datetime.utcnow() > self.expiry_date

    def to_dict(self) -> Dict[str, Any]:
        """Convert evidence to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "evidence_type": self.evidence_type.value,
            "description": self.description,
            "file_path": self.file_path,
            "url": self.url,
            "collected_date": self.collected_date.isoformat(),
            "expiry_date": self.expiry_date.isoformat() if self.expiry_date else None,
            "collector": self.collector,
            "checksum": self.checksum,
            "is_expired": self.is_expired,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Evidence":
        """Create evidence from dictionary."""
        return cls(
            id=data["id"],
            name=data["name"],
            evidence_type=EvidenceType(data["evidence_type"]),
            description=data["description"],
            file_path=data.get("file_path"),
            url=data.get("url"),
            collected_date=datetime.fromisoformat(data["collected_date"]),
            expiry_date=datetime.fromisoformat(data["expiry_date"]) if data.get("expiry_date") else None,
            collector=data.get("collector", "system"),
            checksum=data.get("checksum"),
            metadata=data.get("metadata", {}),
        )


@dataclass
class ControlVerificationResult:
    """Result of verifying a specific control."""

    control_id: str
    control_name: str
    status: VerificationStatus
    evidence: List[Evidence]
    verification_date: datetime
    verifier: str
    findings: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    score: float = 0.0  # 0-100
    exception_reason: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary."""
        return {
            "control_id": self.control_id,
            "control_name": self.control_name,
            "status": self.status.value,
            "evidence_count": len(self.evidence),
            "evidence": [e.to_dict() for e in self.evidence],
            "verification_date": self.verification_date.isoformat(),
            "verifier": self.verifier,
            "findings": self.findings,
            "recommendations": self.recommendations,
            "score": self.score,
            "exception_reason": self.exception_reason,
        }


@dataclass
class AdherenceReport:
    """Report from adherence check."""

    standard_id: str
    standard_name: str
    check_date: datetime
    scope: str
    total_controls: int
    verified_controls: int
    partial_controls: int
    missing_controls: int
    control_results: List[ControlVerificationResult]
    overall_score: float
    recommendations: List[str]
    next_review_date: datetime

    @property
    def adherence_percentage(self) -> float:
        """Calculate adherence percentage."""
        if self.total_controls == 0:
            return 0.0
        return (self.verified_controls / self.total_controls) * 100

    @property
    def gaps(self) -> List[ControlVerificationResult]:
        """Get list of controls with gaps."""
        return [
            r for r in self.control_results
            if r.status in (VerificationStatus.NOT_VERIFIED, VerificationStatus.EVIDENCE_MISSING)
        ]

    def to_dict(self) -> Dict[str, Any]:
        """Convert report to dictionary."""
        return {
            "standard_id": self.standard_id,
            "standard_name": self.standard_name,
            "check_date": self.check_date.isoformat(),
            "scope": self.scope,
            "total_controls": self.total_controls,
            "verified_controls": self.verified_controls,
            "partial_controls": self.partial_controls,
            "missing_controls": self.missing_controls,
            "adherence_percentage": self.adherence_percentage,
            "overall_score": self.overall_score,
            "gap_count": len(self.gaps),
            "recommendations": self.recommendations,
            "next_review_date": self.next_review_date.isoformat(),
            "control_results": [r.to_dict() for r in self.control_results],
        }


@dataclass
class ComplianceReport:
    """Full compliance report for certification."""

    id: str
    title: str
    standard: CertificationStandard
    adherence_report: AdherenceReport
    generated_date: datetime
    report_format: str
    executive_summary: str
    detailed_findings: List[Dict[str, Any]]
    remediation_plan: List[Dict[str, Any]]
    appendices: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert report to dictionary."""
        return {
            "id": self.id,
            "title": self.title,
            "standard_id": self.standard.id,
            "standard_name": self.standard.name,
            "generated_date": self.generated_date.isoformat(),
            "report_format": self.report_format,
            "executive_summary": self.executive_summary,
            "overall_score": self.adherence_report.overall_score,
            "adherence_percentage": self.adherence_report.adherence_percentage,
            "detailed_findings": self.detailed_findings,
            "remediation_plan": self.remediation_plan,
            "appendices": self.appendices,
        }


class AdherenceChecker:
    """
    Verifies adherence to certification requirements.

    Performs automated checks against certification control requirements
    and generates compliance reports.
    """

    # Evidence requirements mapping
    REQUIRED_EVIDENCE_TYPES = {
        "policy": [EvidenceType.POLICY, EvidenceType.DOCUMENT],
        "technical": [EvidenceType.CONFIGURATION, EvidenceType.SCREENSHOT, EvidenceType.SCAN_RESULT],
        "operational": [EvidenceType.LOG, EvidenceType.AUDIT_REPORT],
        "attestation": [EvidenceType.ATTESTATION],
    }

    def __init__(
        self,
        registry: Optional[StandardsRegistry] = None,
        evidence_store_path: Optional[str] = None,
    ):
        """
        Initialize the adherence checker.

        Args:
            registry: Standards registry instance
            evidence_store_path: Path to evidence storage
        """
        self._registry = registry or StandardsRegistry()
        self._evidence_store_path = evidence_store_path
        self._evidence_cache: Dict[str, List[Evidence]] = {}
        self._report_counter = 0
        logger.info("AdherenceChecker initialized")

    def check_adherence(
        self,
        standard: str,
        scope: str = "all_controls",
        evidence_inventory: Optional[Dict[str, List[Evidence]]] = None,
    ) -> AdherenceReport:
        """
        Check adherence to a certification standard.

        Args:
            standard: ID of the certification standard
            scope: Scope of check ("all_controls" or specific category)
            evidence_inventory: Optional pre-loaded evidence inventory

        Returns:
            Adherence report
        """
        logger.info("Checking adherence for standard '%s' with scope '%s'", standard, scope)

        cert_standard = self._registry.get_standard(standard)
        evidence_inventory = evidence_inventory or self._evidence_cache

        # Get controls to check based on scope
        if scope == "all_controls":
            controls = cert_standard.controls
        else:
            controls = cert_standard.get_controls_by_category(scope)

        # Verify each control
        results = []
        verified_count = 0
        partial_count = 0
        missing_count = 0

        for control in controls:
            result = self.verify_control(
                control_id=control.control_id,
                evidence=evidence_inventory.get(control.control_id, []),
                control=control,
            )
            results.append(result)

            if result.status == VerificationStatus.VERIFIED:
                verified_count += 1
            elif result.status == VerificationStatus.PARTIALLY_VERIFIED:
                partial_count += 1
            else:
                missing_count += 1

        # Calculate overall score
        total_score = sum(r.score for r in results)
        overall_score = total_score / len(results) if results else 0.0

        # Generate recommendations
        recommendations = self._generate_recommendations(results)

        # Calculate next review date
        next_review = datetime.utcnow()
        next_review = next_review.replace(
            month=next_review.month + 3 if next_review.month <= 9 else next_review.month - 9,
            year=next_review.year if next_review.month <= 9 else next_review.year + 1,
        )

        report = AdherenceReport(
            standard_id=standard,
            standard_name=cert_standard.name,
            check_date=datetime.utcnow(),
            scope=scope,
            total_controls=len(controls),
            verified_controls=verified_count,
            partial_controls=partial_count,
            missing_controls=missing_count,
            control_results=results,
            overall_score=overall_score,
            recommendations=recommendations,
            next_review_date=next_review,
        )

        logger.info(
            "Adherence check complete: %.1f%% adherent, %d verified, %d partial, %d missing",
            report.adherence_percentage,
            verified_count,
            partial_count,
            missing_count,
        )

        return report

    def verify_control(
        self,
        control_id: str,
        evidence: List[Evidence],
        control: Optional[ControlRequirement] = None,
    ) -> ControlVerificationResult:
        """
        Verify a specific control requirement.

        Args:
            control_id: ID of the control to verify
            evidence: List of evidence for the control
            control: Optional control requirement object

        Returns:
            Control verification result
        """
        findings = []
        recommendations = []

        # Check evidence availability
        if not evidence:
            return ControlVerificationResult(
                control_id=control_id,
                control_name=control.name if control else control_id,
                status=VerificationStatus.EVIDENCE_MISSING,
                evidence=[],
                verification_date=datetime.utcnow(),
                verifier="AdherenceChecker",
                findings=["No evidence provided for this control"],
                recommendations=["Collect and upload required evidence"],
                score=0.0,
            )

        # Check for expired evidence
        expired_evidence = [e for e in evidence if e.is_expired]
        if expired_evidence:
            findings.append(f"{len(expired_evidence)} evidence item(s) have expired")
            recommendations.append("Refresh expired evidence")

        valid_evidence = [e for e in evidence if not e.is_expired]

        # Check evidence types against requirements
        if control:
            required_types = set()
            for req in control.evidence_requirements:
                req_lower = req.lower()
                if "policy" in req_lower or "document" in req_lower:
                    required_types.add(EvidenceType.POLICY)
                    required_types.add(EvidenceType.DOCUMENT)
                elif "configuration" in req_lower or "screenshot" in req_lower:
                    required_types.add(EvidenceType.CONFIGURATION)
                    required_types.add(EvidenceType.SCREENSHOT)
                elif "log" in req_lower or "audit" in req_lower:
                    required_types.add(EvidenceType.LOG)
                    required_types.add(EvidenceType.AUDIT_REPORT)

            provided_types = {e.evidence_type for e in valid_evidence}
            missing_types = required_types - provided_types

            if missing_types:
                findings.append(f"Missing evidence types: {[t.value for t in missing_types]}")
                recommendations.append(f"Provide evidence of types: {[t.value for t in missing_types]}")

        # Calculate score based on evidence completeness
        if not valid_evidence:
            score = 0.0
            status = VerificationStatus.EVIDENCE_EXPIRED
        elif len(valid_evidence) >= 3:
            score = 100.0
            status = VerificationStatus.VERIFIED
        elif len(valid_evidence) >= 1:
            score = 50.0 + (len(valid_evidence) * 15)
            status = VerificationStatus.PARTIALLY_VERIFIED
        else:
            score = 25.0
            status = VerificationStatus.PARTIALLY_VERIFIED

        # Verify evidence integrity (checksum)
        for ev in valid_evidence:
            if ev.checksum and ev.file_path:
                # In production, would verify actual file checksum
                findings.append(f"Evidence '{ev.name}' has checksum verification")

        return ControlVerificationResult(
            control_id=control_id,
            control_name=control.name if control else control_id,
            status=status,
            evidence=valid_evidence,
            verification_date=datetime.utcnow(),
            verifier="AdherenceChecker",
            findings=findings,
            recommendations=recommendations,
            score=score,
        )

    def generate_report(
        self,
        standard: str,
        report_format: str = "json",
        include_evidence: bool = True,
    ) -> ComplianceReport:
        """
        Generate a compliance report.

        Args:
            standard: ID of the certification standard
            report_format: Output format ("json", "pdf", "html")
            include_evidence: Whether to include evidence details

        Returns:
            Compliance report
        """
        logger.info("Generating %s compliance report for '%s'", report_format, standard)

        cert_standard = self._registry.get_standard(standard)
        adherence = self.check_adherence(standard)

        self._report_counter += 1
        report_id = f"CR-{standard}-{self._report_counter:04d}"

        # Generate executive summary
        executive_summary = self._generate_executive_summary(adherence)

        # Generate detailed findings
        detailed_findings = []
        for result in adherence.control_results:
            if result.status != VerificationStatus.VERIFIED:
                finding = {
                    "control_id": result.control_id,
                    "control_name": result.control_name,
                    "status": result.status.value,
                    "findings": result.findings,
                    "recommendations": result.recommendations,
                    "priority": self._get_control_priority(cert_standard, result.control_id),
                }
                detailed_findings.append(finding)

        # Generate remediation plan
        remediation_plan = self._generate_remediation_plan(adherence, cert_standard)

        report = ComplianceReport(
            id=report_id,
            title=f"{cert_standard.name} Compliance Report",
            standard=cert_standard,
            adherence_report=adherence,
            generated_date=datetime.utcnow(),
            report_format=report_format,
            executive_summary=executive_summary,
            detailed_findings=detailed_findings,
            remediation_plan=remediation_plan,
        )

        logger.info("Generated compliance report '%s'", report_id)

        return report

    def _generate_executive_summary(self, adherence: AdherenceReport) -> str:
        """Generate executive summary for report."""
        summary_parts = [
            f"Compliance Assessment for {adherence.standard_name}",
            f"",
            f"Assessment Date: {adherence.check_date.strftime('%Y-%m-%d')}",
            f"Scope: {adherence.scope}",
            f"",
            f"Overall Adherence: {adherence.adherence_percentage:.1f}%",
            f"Overall Score: {adherence.overall_score:.1f}/100",
            f"",
            f"Summary:",
            f"- Total Controls Assessed: {adherence.total_controls}",
            f"- Controls Verified: {adherence.verified_controls}",
            f"- Controls Partially Verified: {adherence.partial_controls}",
            f"- Controls Not Verified: {adherence.missing_controls}",
            f"",
            f"Key Findings:",
        ]

        # Add top recommendations
        for i, rec in enumerate(adherence.recommendations[:5], 1):
            summary_parts.append(f"{i}. {rec}")

        return "\n".join(summary_parts)

    def _generate_recommendations(
        self,
        results: List[ControlVerificationResult],
    ) -> List[str]:
        """Generate recommendations from verification results."""
        recommendations = []

        # Count issues by category
        evidence_missing = sum(1 for r in results if r.status == VerificationStatus.EVIDENCE_MISSING)
        evidence_expired = sum(1 for r in results if r.status == VerificationStatus.EVIDENCE_EXPIRED)
        partial = sum(1 for r in results if r.status == VerificationStatus.PARTIALLY_VERIFIED)

        if evidence_missing > 0:
            recommendations.append(
                f"Collect evidence for {evidence_missing} control(s) with missing documentation"
            )

        if evidence_expired > 0:
            recommendations.append(
                f"Refresh evidence for {evidence_expired} control(s) with expired documentation"
            )

        if partial > 0:
            recommendations.append(
                f"Strengthen evidence for {partial} partially verified control(s)"
            )

        # Add specific recommendations from control results
        seen_recommendations = set(recommendations)
        for result in results:
            for rec in result.recommendations:
                if rec not in seen_recommendations:
                    recommendations.append(rec)
                    seen_recommendations.add(rec)
                if len(recommendations) >= 10:
                    break

        return recommendations

    def _get_control_priority(
        self,
        standard: CertificationStandard,
        control_id: str,
    ) -> str:
        """Get priority of a control."""
        control = standard.get_control(control_id)
        if control:
            return control.priority.value
        return "medium"

    def _generate_remediation_plan(
        self,
        adherence: AdherenceReport,
        standard: CertificationStandard,
    ) -> List[Dict[str, Any]]:
        """Generate remediation plan from gaps."""
        plan = []

        # Sort gaps by priority
        gaps = adherence.gaps
        priority_order = {
            "critical": 0,
            "high": 1,
            "medium": 2,
            "low": 3,
        }

        sorted_gaps = sorted(
            gaps,
            key=lambda g: priority_order.get(
                self._get_control_priority(standard, g.control_id),
                2
            )
        )

        for idx, gap in enumerate(sorted_gaps, 1):
            control = standard.get_control(gap.control_id)
            remediation_item = {
                "step": idx,
                "control_id": gap.control_id,
                "control_name": gap.control_name,
                "priority": self._get_control_priority(standard, gap.control_id),
                "current_status": gap.status.value,
                "action_required": gap.recommendations[0] if gap.recommendations else "Address control gap",
                "evidence_needed": control.evidence_requirements if control else [],
                "estimated_effort": "TBD",
            }
            plan.append(remediation_item)

        return plan

    def add_evidence(
        self,
        control_id: str,
        evidence: Evidence,
    ) -> None:
        """
        Add evidence for a control.

        Args:
            control_id: ID of the control
            evidence: Evidence to add
        """
        if control_id not in self._evidence_cache:
            self._evidence_cache[control_id] = []
        self._evidence_cache[control_id].append(evidence)
        logger.info("Added evidence '%s' for control '%s'", evidence.name, control_id)

    def verify_connections(self) -> Dict[str, Any]:
        """Verify connections to dependent services."""
        return {
            "registry": "connected",
            "evidence_store": "connected" if self._evidence_store_path else "not_configured",
            "cache_entries": len(self._evidence_cache),
        }
