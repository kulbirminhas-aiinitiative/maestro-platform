"""
Compliance Checker for Verification & Validation.

EPIC: MD-2521 - [SDLC-Phase7] Verification & Validation
AC-2: Compliance Checker - Automated compliance validation against regulatory standards

This module provides:
- Rule-based validation engine
- Standard templates (SOC2, GDPR, HIPAA patterns)
- Evidence collection and linking
- Remediation guidance generation
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set

logger = logging.getLogger(__name__)


class ComplianceStandard(Enum):
    """Supported compliance standards."""
    SOC2 = "SOC2"
    GDPR = "GDPR"
    HIPAA = "HIPAA"
    PCI_DSS = "PCI-DSS"
    ISO27001 = "ISO27001"
    CUSTOM = "CUSTOM"


class RuleSeverity(Enum):
    """Severity level of compliance rules."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class RuleStatus(Enum):
    """Status of a compliance rule check."""
    COMPLIANT = "compliant"
    NON_COMPLIANT = "non_compliant"
    PARTIALLY_COMPLIANT = "partially_compliant"
    NOT_APPLICABLE = "not_applicable"
    ERROR = "error"


@dataclass
class Evidence:
    """Evidence supporting compliance."""
    evidence_id: str
    evidence_type: str  # document, log, config, screenshot, etc.
    description: str
    location: str  # file path, URL, etc.
    collected_at: datetime = field(default_factory=datetime.utcnow)
    hash: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "evidence_id": self.evidence_id,
            "evidence_type": self.evidence_type,
            "description": self.description,
            "location": self.location,
            "collected_at": self.collected_at.isoformat(),
            "hash": self.hash,
            "metadata": self.metadata
        }


@dataclass
class RemediationGuidance:
    """Guidance for remediation of non-compliance."""
    guidance_id: str
    title: str
    description: str
    steps: List[str]
    priority: int  # 1 = highest priority
    estimated_effort: str  # e.g., "1 day", "1 week"
    resources: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "guidance_id": self.guidance_id,
            "title": self.title,
            "description": self.description,
            "steps": self.steps,
            "priority": self.priority,
            "estimated_effort": self.estimated_effort,
            "resources": self.resources
        }


@dataclass
class ComplianceRule:
    """
    Definition of a compliance rule.

    Each rule represents a specific compliance requirement
    from a standard.
    """
    rule_id: str
    standard: ComplianceStandard
    requirement_id: str  # e.g., "SOC2-CC6.1"
    title: str
    description: str
    severity: RuleSeverity
    validator: Optional[Callable[[Any], bool]] = None
    evidence_required: List[str] = field(default_factory=list)
    remediation: Optional[RemediationGuidance] = None
    enabled: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)

    def validate(self, context: Any) -> RuleStatus:
        """
        Validate this rule against context.

        Args:
            context: The context to validate

        Returns:
            RuleStatus indicating compliance level
        """
        if not self.enabled:
            return RuleStatus.NOT_APPLICABLE

        if self.validator is None:
            logger.warning(f"Rule {self.rule_id} has no validator")
            return RuleStatus.NOT_APPLICABLE

        try:
            result = self.validator(context)
            return RuleStatus.COMPLIANT if result else RuleStatus.NON_COMPLIANT
        except Exception as e:
            logger.error(f"Rule validation error for {self.rule_id}: {e}")
            return RuleStatus.ERROR


@dataclass
class RuleResult:
    """Result of a compliance rule check."""
    rule: ComplianceRule
    status: RuleStatus
    evidence: List[Evidence] = field(default_factory=list)
    findings: List[str] = field(default_factory=list)
    checked_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "rule_id": self.rule.rule_id,
            "requirement_id": self.rule.requirement_id,
            "title": self.rule.title,
            "standard": self.rule.standard.value,
            "severity": self.rule.severity.value,
            "status": self.status.value,
            "evidence": [e.to_dict() for e in self.evidence],
            "findings": self.findings,
            "remediation": self.rule.remediation.to_dict() if self.rule.remediation else None,
            "checked_at": self.checked_at.isoformat()
        }


@dataclass
class ComplianceReport:
    """Overall compliance report."""
    report_id: str
    standards: List[ComplianceStandard]
    results: List[RuleResult]
    generated_at: datetime = field(default_factory=datetime.utcnow)

    @property
    def total_rules(self) -> int:
        """Total number of rules checked."""
        return len(self.results)

    @property
    def compliant_count(self) -> int:
        """Number of compliant rules."""
        return sum(1 for r in self.results if r.status == RuleStatus.COMPLIANT)

    @property
    def non_compliant_count(self) -> int:
        """Number of non-compliant rules."""
        return sum(1 for r in self.results if r.status == RuleStatus.NON_COMPLIANT)

    @property
    def compliance_rate(self) -> float:
        """Overall compliance rate (0.0 to 1.0)."""
        applicable = [r for r in self.results if r.status != RuleStatus.NOT_APPLICABLE]
        if not applicable:
            return 1.0
        compliant = sum(1 for r in applicable if r.status == RuleStatus.COMPLIANT)
        return compliant / len(applicable)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "report_id": self.report_id,
            "standards": [s.value for s in self.standards],
            "total_rules": self.total_rules,
            "compliant": self.compliant_count,
            "non_compliant": self.non_compliant_count,
            "compliance_rate": self.compliance_rate,
            "results": [r.to_dict() for r in self.results],
            "generated_at": self.generated_at.isoformat()
        }


class ComplianceChecker:
    """
    Engine for checking compliance against standards.

    Manages rules, collects evidence, and generates reports.
    """

    def __init__(self):
        """Initialize the compliance checker."""
        self._rules: Dict[str, ComplianceRule] = {}
        self._standards_rules: Dict[ComplianceStandard, List[str]] = {}
        self._evidence_store: Dict[str, Evidence] = {}
        logger.info("ComplianceChecker initialized")

    def register_rule(self, rule: ComplianceRule) -> None:
        """
        Register a compliance rule.

        Args:
            rule: The rule to register
        """
        self._rules[rule.rule_id] = rule

        if rule.standard not in self._standards_rules:
            self._standards_rules[rule.standard] = []
        self._standards_rules[rule.standard].append(rule.rule_id)

        logger.debug(f"Registered rule: {rule.rule_id}")

    def register_evidence(self, evidence: Evidence) -> None:
        """
        Register collected evidence.

        Args:
            evidence: The evidence to register
        """
        self._evidence_store[evidence.evidence_id] = evidence
        logger.debug(f"Registered evidence: {evidence.evidence_id}")

    def check_rule(self, rule_id: str, context: Any) -> RuleResult:
        """
        Check a single compliance rule.

        Args:
            rule_id: ID of the rule to check
            context: Context to validate against

        Returns:
            RuleResult with check outcome
        """
        rule = self._rules.get(rule_id)
        if rule is None:
            # Create a dummy rule for error reporting
            dummy_rule = ComplianceRule(
                rule_id=rule_id,
                standard=ComplianceStandard.CUSTOM,
                requirement_id="UNKNOWN",
                title="Unknown Rule",
                description="Rule not found",
                severity=RuleSeverity.INFO
            )
            return RuleResult(
                rule=dummy_rule,
                status=RuleStatus.ERROR,
                findings=[f"Rule '{rule_id}' not found"]
            )

        status = rule.validate(context)

        # Collect associated evidence
        evidence = []
        for evidence_id in rule.evidence_required:
            if evidence_id in self._evidence_store:
                evidence.append(self._evidence_store[evidence_id])

        findings = []
        if status == RuleStatus.NON_COMPLIANT:
            findings.append(f"Non-compliant with {rule.requirement_id}: {rule.title}")

        return RuleResult(
            rule=rule,
            status=status,
            evidence=evidence,
            findings=findings
        )

    def check_standard(self, standard: ComplianceStandard, context: Any) -> ComplianceReport:
        """
        Check all rules for a compliance standard.

        Args:
            standard: The standard to check
            context: Context to validate against

        Returns:
            ComplianceReport with all rule results
        """
        rule_ids = self._standards_rules.get(standard, [])
        results = []

        for rule_id in rule_ids:
            result = self.check_rule(rule_id, context)
            results.append(result)

        return ComplianceReport(
            report_id=f"{standard.value}-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
            standards=[standard],
            results=results
        )

    def check_all(self, context: Any) -> ComplianceReport:
        """
        Check all registered rules.

        Args:
            context: Context to validate against

        Returns:
            ComplianceReport with all results
        """
        results = []
        standards: Set[ComplianceStandard] = set()

        for rule_id, rule in self._rules.items():
            result = self.check_rule(rule_id, context)
            results.append(result)
            standards.add(rule.standard)

        return ComplianceReport(
            report_id=f"full-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
            standards=list(standards),
            results=results
        )

    def get_non_compliant(self, report: ComplianceReport) -> List[RuleResult]:
        """Get all non-compliant results from a report."""
        return [r for r in report.results if r.status == RuleStatus.NON_COMPLIANT]

    def get_remediation_plan(self, report: ComplianceReport) -> List[Dict[str, Any]]:
        """
        Generate a remediation plan from non-compliant results.

        Args:
            report: The compliance report

        Returns:
            List of remediation items sorted by priority
        """
        plan = []
        for result in self.get_non_compliant(report):
            if result.rule.remediation:
                plan.append({
                    "rule_id": result.rule.rule_id,
                    "requirement": result.rule.requirement_id,
                    "severity": result.rule.severity.value,
                    "remediation": result.rule.remediation.to_dict()
                })

        # Sort by severity then priority
        severity_order = {
            RuleSeverity.CRITICAL.value: 0,
            RuleSeverity.HIGH.value: 1,
            RuleSeverity.MEDIUM.value: 2,
            RuleSeverity.LOW.value: 3,
            RuleSeverity.INFO.value: 4
        }

        plan.sort(key=lambda x: (
            severity_order.get(x["severity"], 5),
            x["remediation"]["priority"]
        ))

        return plan


# Built-in compliance rules for common standards

def _access_control_validator(context: Dict[str, Any]) -> bool:
    """Validate access control requirements."""
    return context.get("rbac_enabled", False) and context.get("mfa_enabled", False)


def _encryption_validator(context: Dict[str, Any]) -> bool:
    """Validate encryption requirements."""
    return (
        context.get("data_encrypted_at_rest", False) and
        context.get("data_encrypted_in_transit", False)
    )


def _audit_logging_validator(context: Dict[str, Any]) -> bool:
    """Validate audit logging requirements."""
    return (
        context.get("audit_logging_enabled", False) and
        context.get("log_retention_days", 0) >= 90
    )


def _data_retention_validator(context: Dict[str, Any]) -> bool:
    """Validate data retention policy."""
    return context.get("retention_policy_defined", False)


SOC2_RULES = [
    ComplianceRule(
        rule_id="soc2-cc6.1",
        standard=ComplianceStandard.SOC2,
        requirement_id="CC6.1",
        title="Logical Access Security",
        description="Access to systems and data is restricted using logical access controls",
        severity=RuleSeverity.CRITICAL,
        validator=_access_control_validator,
        evidence_required=["access_control_policy", "rbac_config"],
        remediation=RemediationGuidance(
            guidance_id="rem-cc6.1",
            title="Implement Access Controls",
            description="Set up role-based access control and multi-factor authentication",
            steps=[
                "Enable RBAC in authentication system",
                "Configure MFA for all users",
                "Document access control policies"
            ],
            priority=1,
            estimated_effort="1 week"
        )
    ),
    ComplianceRule(
        rule_id="soc2-cc6.7",
        standard=ComplianceStandard.SOC2,
        requirement_id="CC6.7",
        title="Data Encryption",
        description="Data is encrypted at rest and in transit",
        severity=RuleSeverity.CRITICAL,
        validator=_encryption_validator,
        evidence_required=["encryption_config", "tls_certificates"],
        remediation=RemediationGuidance(
            guidance_id="rem-cc6.7",
            title="Implement Encryption",
            description="Enable encryption for data at rest and in transit",
            steps=[
                "Enable TLS 1.3 for all connections",
                "Configure database encryption",
                "Encrypt file storage"
            ],
            priority=1,
            estimated_effort="3 days"
        )
    ),
    ComplianceRule(
        rule_id="soc2-cc7.2",
        standard=ComplianceStandard.SOC2,
        requirement_id="CC7.2",
        title="Audit Logging",
        description="System activities are logged and monitored",
        severity=RuleSeverity.HIGH,
        validator=_audit_logging_validator,
        evidence_required=["audit_logs", "monitoring_config"],
        remediation=RemediationGuidance(
            guidance_id="rem-cc7.2",
            title="Enable Audit Logging",
            description="Set up comprehensive audit logging with retention",
            steps=[
                "Enable audit logging in all services",
                "Configure 90-day log retention",
                "Set up log aggregation"
            ],
            priority=2,
            estimated_effort="2 days"
        )
    )
]


GDPR_RULES = [
    ComplianceRule(
        rule_id="gdpr-art5.1e",
        standard=ComplianceStandard.GDPR,
        requirement_id="Article 5(1)(e)",
        title="Storage Limitation",
        description="Personal data kept no longer than necessary",
        severity=RuleSeverity.HIGH,
        validator=_data_retention_validator,
        evidence_required=["retention_policy"],
        remediation=RemediationGuidance(
            guidance_id="rem-gdpr5.1e",
            title="Define Data Retention",
            description="Create and implement data retention policies",
            steps=[
                "Document retention periods for each data type",
                "Implement automated data deletion",
                "Configure retention monitoring"
            ],
            priority=2,
            estimated_effort="1 week"
        )
    )
]


def create_compliance_checker_with_defaults() -> ComplianceChecker:
    """Create a compliance checker with built-in rules."""
    checker = ComplianceChecker()

    for rule in SOC2_RULES:
        checker.register_rule(rule)

    for rule in GDPR_RULES:
        checker.register_rule(rule)

    return checker
