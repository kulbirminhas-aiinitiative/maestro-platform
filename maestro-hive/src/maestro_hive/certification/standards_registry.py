"""
Standards Registry - Central repository for certification standards.

This module provides the StandardsRegistry class which manages certification
standards and their control requirements for ISO 27001, SOC2, GDPR, HIPAA,
and PCI-DSS certifications.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class Priority(Enum):
    """Priority level for control requirements."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class ControlCategory(Enum):
    """Categories of control requirements."""
    ACCESS_CONTROL = "access_control"
    ASSET_MANAGEMENT = "asset_management"
    BUSINESS_CONTINUITY = "business_continuity"
    COMMUNICATIONS_SECURITY = "communications_security"
    COMPLIANCE = "compliance"
    CRYPTOGRAPHY = "cryptography"
    HUMAN_RESOURCES = "human_resources"
    INCIDENT_MANAGEMENT = "incident_management"
    INFORMATION_SECURITY = "information_security"
    OPERATIONS_SECURITY = "operations_security"
    ORGANIZATION = "organization"
    PHYSICAL_SECURITY = "physical_security"
    PRIVACY = "privacy"
    SUPPLIER_RELATIONSHIPS = "supplier_relationships"
    SYSTEM_ACQUISITION = "system_acquisition"


@dataclass
class ControlRequirement:
    """Individual control requirement within a certification standard."""

    control_id: str
    name: str
    description: str
    category: ControlCategory
    implementation_guidance: str
    evidence_requirements: List[str]
    priority: Priority
    is_mandatory: bool = True
    related_controls: List[str] = field(default_factory=list)
    audit_frequency_days: int = 365

    def to_dict(self) -> Dict[str, Any]:
        """Convert control requirement to dictionary."""
        return {
            "control_id": self.control_id,
            "name": self.name,
            "description": self.description,
            "category": self.category.value,
            "implementation_guidance": self.implementation_guidance,
            "evidence_requirements": self.evidence_requirements,
            "priority": self.priority.value,
            "is_mandatory": self.is_mandatory,
            "related_controls": self.related_controls,
            "audit_frequency_days": self.audit_frequency_days,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ControlRequirement":
        """Create control requirement from dictionary."""
        return cls(
            control_id=data["control_id"],
            name=data["name"],
            description=data["description"],
            category=ControlCategory(data["category"]),
            implementation_guidance=data["implementation_guidance"],
            evidence_requirements=data["evidence_requirements"],
            priority=Priority(data["priority"]),
            is_mandatory=data.get("is_mandatory", True),
            related_controls=data.get("related_controls", []),
            audit_frequency_days=data.get("audit_frequency_days", 365),
        )


@dataclass
class CertificationStandard:
    """Represents a certification standard with its control requirements."""

    id: str
    name: str
    version: str
    description: str
    controls: List[ControlRequirement]
    effective_date: datetime
    renewal_period_months: int
    issuing_body: str
    regions: List[str] = field(default_factory=list)

    @property
    def total_controls(self) -> int:
        """Get total number of controls."""
        return len(self.controls)

    @property
    def mandatory_controls(self) -> List[ControlRequirement]:
        """Get list of mandatory controls."""
        return [c for c in self.controls if c.is_mandatory]

    @property
    def critical_controls(self) -> List[ControlRequirement]:
        """Get list of critical priority controls."""
        return [c for c in self.controls if c.priority == Priority.CRITICAL]

    def get_controls_by_category(
        self, category: ControlCategory
    ) -> List[ControlRequirement]:
        """Get controls filtered by category."""
        return [c for c in self.controls if c.category == category]

    def get_control(self, control_id: str) -> Optional[ControlRequirement]:
        """Get a specific control by ID."""
        for control in self.controls:
            if control.control_id == control_id:
                return control
        return None

    def to_dict(self) -> Dict[str, Any]:
        """Convert standard to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "controls": [c.to_dict() for c in self.controls],
            "effective_date": self.effective_date.isoformat(),
            "renewal_period_months": self.renewal_period_months,
            "issuing_body": self.issuing_body,
            "regions": self.regions,
        }


@dataclass
class ControlMapping:
    """Mapping between controls of different standards."""

    source_standard: str
    source_control_id: str
    target_standard: str
    target_control_ids: List[str]
    mapping_type: str  # "equivalent", "partial", "related"
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert mapping to dictionary."""
        return {
            "source_standard": self.source_standard,
            "source_control_id": self.source_control_id,
            "target_standard": self.target_standard,
            "target_control_ids": self.target_control_ids,
            "mapping_type": self.mapping_type,
            "notes": self.notes,
        }


class StandardsRegistry:
    """
    Central repository for certification standards.

    Manages certification standards, their control requirements,
    and mappings between different standards.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the standards registry.

        Args:
            config: Optional configuration dictionary
        """
        self._config = config or {}
        self._standards: Dict[str, CertificationStandard] = {}
        self._mappings: List[ControlMapping] = []
        self._load_default_standards()
        logger.info("StandardsRegistry initialized with %d standards", len(self._standards))

    def _load_default_standards(self) -> None:
        """Load default certification standards."""
        self._standards["ISO_27001"] = self._create_iso_27001()
        self._standards["SOC2_TYPE2"] = self._create_soc2_type2()
        self._standards["GDPR"] = self._create_gdpr()
        self._standards["HIPAA"] = self._create_hipaa()
        self._standards["PCI_DSS"] = self._create_pci_dss()
        self._load_default_mappings()

    def _create_iso_27001(self) -> CertificationStandard:
        """Create ISO 27001:2022 standard definition."""
        controls = [
            ControlRequirement(
                control_id="A.5.1",
                name="Policies for information security",
                description="Information security policy and topic-specific policies shall be defined and approved by management",
                category=ControlCategory.ORGANIZATION,
                implementation_guidance="Document and communicate security policies",
                evidence_requirements=["Policy documents", "Approval records", "Communication records"],
                priority=Priority.HIGH,
            ),
            ControlRequirement(
                control_id="A.5.2",
                name="Information security roles and responsibilities",
                description="Information security roles and responsibilities shall be defined and allocated",
                category=ControlCategory.ORGANIZATION,
                implementation_guidance="Define RACI matrix for security responsibilities",
                evidence_requirements=["Org chart", "Job descriptions", "RACI matrix"],
                priority=Priority.HIGH,
            ),
            ControlRequirement(
                control_id="A.6.1",
                name="Screening",
                description="Background verification checks shall be carried out on candidates for employment",
                category=ControlCategory.HUMAN_RESOURCES,
                implementation_guidance="Implement background check process",
                evidence_requirements=["Background check policy", "Check records"],
                priority=Priority.MEDIUM,
            ),
            ControlRequirement(
                control_id="A.6.2",
                name="Terms and conditions of employment",
                description="Employment agreements shall state security responsibilities",
                category=ControlCategory.HUMAN_RESOURCES,
                implementation_guidance="Include security clauses in employment contracts",
                evidence_requirements=["Employment contract templates", "Signed agreements"],
                priority=Priority.MEDIUM,
            ),
            ControlRequirement(
                control_id="A.7.1",
                name="Physical security perimeters",
                description="Security perimeters shall be defined and used to protect areas containing sensitive information",
                category=ControlCategory.PHYSICAL_SECURITY,
                implementation_guidance="Define and implement physical security zones",
                evidence_requirements=["Security zone maps", "Access logs", "Physical audit reports"],
                priority=Priority.HIGH,
            ),
            ControlRequirement(
                control_id="A.8.1",
                name="User endpoint devices",
                description="Information stored on, processed by or accessible via user endpoint devices shall be protected",
                category=ControlCategory.ASSET_MANAGEMENT,
                implementation_guidance="Implement endpoint security controls",
                evidence_requirements=["Endpoint security policy", "MDM configuration", "Audit logs"],
                priority=Priority.CRITICAL,
            ),
            ControlRequirement(
                control_id="A.8.2",
                name="Privileged access rights",
                description="Allocation and use of privileged access rights shall be restricted and managed",
                category=ControlCategory.ACCESS_CONTROL,
                implementation_guidance="Implement PAM solution and review process",
                evidence_requirements=["PAM policy", "Access review records", "Privileged account inventory"],
                priority=Priority.CRITICAL,
            ),
            ControlRequirement(
                control_id="A.8.3",
                name="Information access restriction",
                description="Access to information and application system functions shall be restricted",
                category=ControlCategory.ACCESS_CONTROL,
                implementation_guidance="Implement RBAC and access controls",
                evidence_requirements=["Access control matrix", "RBAC configuration", "Access logs"],
                priority=Priority.CRITICAL,
            ),
            ControlRequirement(
                control_id="A.8.4",
                name="Access to source code",
                description="Read and write access to source code shall be appropriately managed",
                category=ControlCategory.ACCESS_CONTROL,
                implementation_guidance="Implement source code access controls",
                evidence_requirements=["SCM access policy", "Repository permissions", "Access logs"],
                priority=Priority.HIGH,
            ),
            ControlRequirement(
                control_id="A.8.5",
                name="Secure authentication",
                description="Secure authentication technologies and procedures shall be implemented",
                category=ControlCategory.ACCESS_CONTROL,
                implementation_guidance="Implement MFA and strong authentication",
                evidence_requirements=["Authentication policy", "MFA configuration", "Login audit logs"],
                priority=Priority.CRITICAL,
            ),
        ]

        return CertificationStandard(
            id="ISO_27001",
            name="ISO/IEC 27001",
            version="2022",
            description="Information security management systems - Requirements",
            controls=controls,
            effective_date=datetime(2022, 10, 25),
            renewal_period_months=36,
            issuing_body="ISO/IEC",
            regions=["Global"],
        )

    def _create_soc2_type2(self) -> CertificationStandard:
        """Create SOC2 Type II standard definition."""
        controls = [
            ControlRequirement(
                control_id="CC1.1",
                name="COSO Principle 1",
                description="The entity demonstrates a commitment to integrity and ethical values",
                category=ControlCategory.ORGANIZATION,
                implementation_guidance="Establish code of conduct and ethics program",
                evidence_requirements=["Code of conduct", "Ethics training records", "Compliance attestations"],
                priority=Priority.HIGH,
            ),
            ControlRequirement(
                control_id="CC2.1",
                name="COSO Principle 6",
                description="Internal and external communication are used to support internal control",
                category=ControlCategory.ORGANIZATION,
                implementation_guidance="Implement communication policies and channels",
                evidence_requirements=["Communication policy", "Meeting minutes", "Announcements"],
                priority=Priority.MEDIUM,
            ),
            ControlRequirement(
                control_id="CC3.1",
                name="COSO Principle 7",
                description="The entity identifies and assesses risks to the achievement of objectives",
                category=ControlCategory.INFORMATION_SECURITY,
                implementation_guidance="Implement risk assessment program",
                evidence_requirements=["Risk assessment methodology", "Risk register", "Risk treatment plans"],
                priority=Priority.CRITICAL,
            ),
            ControlRequirement(
                control_id="CC4.1",
                name="COSO Principle 10",
                description="The entity selects, develops and performs ongoing evaluations",
                category=ControlCategory.COMPLIANCE,
                implementation_guidance="Implement control monitoring program",
                evidence_requirements=["Monitoring procedures", "Control testing results", "Remediation records"],
                priority=Priority.HIGH,
            ),
            ControlRequirement(
                control_id="CC5.1",
                name="COSO Principle 11",
                description="The entity selects, develops, and deploys control activities",
                category=ControlCategory.OPERATIONS_SECURITY,
                implementation_guidance="Design and implement control activities",
                evidence_requirements=["Control documentation", "Implementation evidence", "Testing results"],
                priority=Priority.HIGH,
            ),
            ControlRequirement(
                control_id="CC6.1",
                name="Logical and physical access controls",
                description="The entity implements logical access security software",
                category=ControlCategory.ACCESS_CONTROL,
                implementation_guidance="Implement identity and access management",
                evidence_requirements=["IAM policy", "Access configurations", "Access reviews"],
                priority=Priority.CRITICAL,
            ),
            ControlRequirement(
                control_id="CC7.1",
                name="System operations",
                description="The entity uses detection and monitoring procedures",
                category=ControlCategory.OPERATIONS_SECURITY,
                implementation_guidance="Implement security monitoring and detection",
                evidence_requirements=["Monitoring tools configuration", "Alert procedures", "Incident logs"],
                priority=Priority.CRITICAL,
            ),
            ControlRequirement(
                control_id="CC8.1",
                name="Change management",
                description="The entity authorizes, designs, develops, configures, and tests changes",
                category=ControlCategory.SYSTEM_ACQUISITION,
                implementation_guidance="Implement change management process",
                evidence_requirements=["Change policy", "Change requests", "Testing records", "Approvals"],
                priority=Priority.HIGH,
            ),
        ]

        return CertificationStandard(
            id="SOC2_TYPE2",
            name="SOC 2 Type II",
            version="2017",
            description="Service Organization Control 2 Type II - Trust Services Criteria",
            controls=controls,
            effective_date=datetime(2017, 1, 1),
            renewal_period_months=12,
            issuing_body="AICPA",
            regions=["Global"],
        )

    def _create_gdpr(self) -> CertificationStandard:
        """Create GDPR standard definition."""
        controls = [
            ControlRequirement(
                control_id="GDPR-5",
                name="Principles of processing",
                description="Personal data shall be processed lawfully, fairly and transparently",
                category=ControlCategory.PRIVACY,
                implementation_guidance="Document lawful basis for processing",
                evidence_requirements=["Privacy policy", "Processing records", "Consent records"],
                priority=Priority.CRITICAL,
            ),
            ControlRequirement(
                control_id="GDPR-6",
                name="Lawfulness of processing",
                description="Processing shall be lawful only if certain conditions apply",
                category=ControlCategory.PRIVACY,
                implementation_guidance="Establish legal basis for each processing activity",
                evidence_requirements=["Legal basis documentation", "Data processing inventory"],
                priority=Priority.CRITICAL,
            ),
            ControlRequirement(
                control_id="GDPR-7",
                name="Conditions for consent",
                description="Consent must be freely given, specific, informed and unambiguous",
                category=ControlCategory.PRIVACY,
                implementation_guidance="Implement compliant consent mechanisms",
                evidence_requirements=["Consent forms", "Consent records", "Withdrawal mechanisms"],
                priority=Priority.HIGH,
            ),
            ControlRequirement(
                control_id="GDPR-12",
                name="Transparent information",
                description="The controller shall take appropriate measures to provide information",
                category=ControlCategory.PRIVACY,
                implementation_guidance="Create clear and accessible privacy notices",
                evidence_requirements=["Privacy notices", "Communication records"],
                priority=Priority.HIGH,
            ),
            ControlRequirement(
                control_id="GDPR-25",
                name="Data protection by design",
                description="Implement data protection principles by design and default",
                category=ControlCategory.PRIVACY,
                implementation_guidance="Integrate privacy into system design",
                evidence_requirements=["Privacy impact assessments", "Design documentation"],
                priority=Priority.HIGH,
            ),
            ControlRequirement(
                control_id="GDPR-32",
                name="Security of processing",
                description="Implement appropriate technical and organizational measures",
                category=ControlCategory.INFORMATION_SECURITY,
                implementation_guidance="Implement security controls for personal data",
                evidence_requirements=["Security policies", "Technical controls evidence", "Risk assessments"],
                priority=Priority.CRITICAL,
            ),
            ControlRequirement(
                control_id="GDPR-33",
                name="Notification of breach",
                description="Notify supervisory authority of personal data breach within 72 hours",
                category=ControlCategory.INCIDENT_MANAGEMENT,
                implementation_guidance="Implement breach notification procedures",
                evidence_requirements=["Incident response plan", "Notification templates", "Breach records"],
                priority=Priority.CRITICAL,
            ),
            ControlRequirement(
                control_id="GDPR-35",
                name="Data protection impact assessment",
                description="Carry out DPIA for high-risk processing activities",
                category=ControlCategory.PRIVACY,
                implementation_guidance="Establish DPIA process",
                evidence_requirements=["DPIA methodology", "Completed DPIAs", "Risk mitigations"],
                priority=Priority.HIGH,
            ),
        ]

        return CertificationStandard(
            id="GDPR",
            name="General Data Protection Regulation",
            version="2016/679",
            description="EU regulation on data protection and privacy",
            controls=controls,
            effective_date=datetime(2018, 5, 25),
            renewal_period_months=12,  # Ongoing compliance
            issuing_body="European Union",
            regions=["EU", "EEA"],
        )

    def _create_hipaa(self) -> CertificationStandard:
        """Create HIPAA standard definition."""
        controls = [
            ControlRequirement(
                control_id="164.308(a)(1)",
                name="Security Management Process",
                description="Implement policies and procedures to prevent security violations",
                category=ControlCategory.ORGANIZATION,
                implementation_guidance="Establish security management program",
                evidence_requirements=["Risk analysis", "Risk management plan", "Security policies"],
                priority=Priority.CRITICAL,
            ),
            ControlRequirement(
                control_id="164.308(a)(3)",
                name="Workforce Security",
                description="Implement policies and procedures for workforce access",
                category=ControlCategory.HUMAN_RESOURCES,
                implementation_guidance="Implement workforce security procedures",
                evidence_requirements=["Access procedures", "Termination procedures", "Training records"],
                priority=Priority.HIGH,
            ),
            ControlRequirement(
                control_id="164.308(a)(4)",
                name="Information Access Management",
                description="Implement policies for authorizing access to ePHI",
                category=ControlCategory.ACCESS_CONTROL,
                implementation_guidance="Implement access authorization process",
                evidence_requirements=["Access authorization policy", "Access reviews", "Role definitions"],
                priority=Priority.CRITICAL,
            ),
            ControlRequirement(
                control_id="164.308(a)(5)",
                name="Security Awareness and Training",
                description="Implement security awareness and training program",
                category=ControlCategory.HUMAN_RESOURCES,
                implementation_guidance="Develop and deliver security training",
                evidence_requirements=["Training materials", "Completion records", "Assessment results"],
                priority=Priority.HIGH,
            ),
            ControlRequirement(
                control_id="164.308(a)(6)",
                name="Security Incident Procedures",
                description="Implement policies and procedures for responding to security incidents",
                category=ControlCategory.INCIDENT_MANAGEMENT,
                implementation_guidance="Establish incident response procedures",
                evidence_requirements=["Incident response plan", "Incident logs", "Post-incident reviews"],
                priority=Priority.CRITICAL,
            ),
            ControlRequirement(
                control_id="164.310(a)(1)",
                name="Facility Access Controls",
                description="Implement policies for limiting physical access",
                category=ControlCategory.PHYSICAL_SECURITY,
                implementation_guidance="Implement facility access controls",
                evidence_requirements=["Access control policy", "Access logs", "Visitor logs"],
                priority=Priority.HIGH,
            ),
            ControlRequirement(
                control_id="164.312(a)(1)",
                name="Access Control",
                description="Implement technical policies for electronic access",
                category=ControlCategory.ACCESS_CONTROL,
                implementation_guidance="Implement technical access controls",
                evidence_requirements=["Access control configurations", "User provisioning records", "Audit logs"],
                priority=Priority.CRITICAL,
            ),
            ControlRequirement(
                control_id="164.312(b)",
                name="Audit Controls",
                description="Implement mechanisms to record and examine activity",
                category=ControlCategory.COMPLIANCE,
                implementation_guidance="Implement audit logging and monitoring",
                evidence_requirements=["Audit configurations", "Audit logs", "Review procedures"],
                priority=Priority.HIGH,
            ),
        ]

        return CertificationStandard(
            id="HIPAA",
            name="Health Insurance Portability and Accountability Act",
            version="2013",
            description="US law for protecting health information",
            controls=controls,
            effective_date=datetime(2013, 3, 26),
            renewal_period_months=12,
            issuing_body="US HHS",
            regions=["United States"],
        )

    def _create_pci_dss(self) -> CertificationStandard:
        """Create PCI-DSS standard definition."""
        controls = [
            ControlRequirement(
                control_id="PCI-1.1",
                name="Install and maintain network security controls",
                description="Establish and implement firewall and router configurations",
                category=ControlCategory.COMMUNICATIONS_SECURITY,
                implementation_guidance="Configure firewalls to protect cardholder data",
                evidence_requirements=["Firewall rules", "Network diagrams", "Configuration standards"],
                priority=Priority.CRITICAL,
            ),
            ControlRequirement(
                control_id="PCI-2.1",
                name="Apply secure configurations",
                description="Change vendor-supplied defaults and remove unnecessary features",
                category=ControlCategory.SYSTEM_ACQUISITION,
                implementation_guidance="Implement secure configuration baselines",
                evidence_requirements=["Configuration baselines", "Hardening guides", "Scan results"],
                priority=Priority.CRITICAL,
            ),
            ControlRequirement(
                control_id="PCI-3.1",
                name="Protect stored account data",
                description="Keep cardholder data storage to a minimum",
                category=ControlCategory.CRYPTOGRAPHY,
                implementation_guidance="Implement data retention and protection controls",
                evidence_requirements=["Data retention policy", "Encryption configurations", "Data inventory"],
                priority=Priority.CRITICAL,
            ),
            ControlRequirement(
                control_id="PCI-4.1",
                name="Protect cardholder data in transit",
                description="Use strong cryptography for transmission of cardholder data",
                category=ControlCategory.CRYPTOGRAPHY,
                implementation_guidance="Implement TLS for all transmissions",
                evidence_requirements=["TLS configurations", "Certificate inventory", "Scan results"],
                priority=Priority.CRITICAL,
            ),
            ControlRequirement(
                control_id="PCI-5.1",
                name="Protect systems from malware",
                description="Deploy anti-malware solutions on all systems",
                category=ControlCategory.OPERATIONS_SECURITY,
                implementation_guidance="Implement anti-malware controls",
                evidence_requirements=["Anti-malware configurations", "Scan logs", "Update records"],
                priority=Priority.HIGH,
            ),
            ControlRequirement(
                control_id="PCI-6.1",
                name="Develop secure systems and applications",
                description="Establish secure development lifecycle",
                category=ControlCategory.SYSTEM_ACQUISITION,
                implementation_guidance="Implement SDLC with security controls",
                evidence_requirements=["SDLC documentation", "Code review records", "Security testing results"],
                priority=Priority.HIGH,
            ),
            ControlRequirement(
                control_id="PCI-7.1",
                name="Restrict access to cardholder data",
                description="Limit access to system components by business need",
                category=ControlCategory.ACCESS_CONTROL,
                implementation_guidance="Implement role-based access control",
                evidence_requirements=["Access control policy", "Access matrices", "Review records"],
                priority=Priority.CRITICAL,
            ),
            ControlRequirement(
                control_id="PCI-8.1",
                name="Identify users and authenticate access",
                description="Establish unique user identification for all users",
                category=ControlCategory.ACCESS_CONTROL,
                implementation_guidance="Implement unique user IDs and strong authentication",
                evidence_requirements=["Authentication policy", "MFA configuration", "User inventory"],
                priority=Priority.CRITICAL,
            ),
        ]

        return CertificationStandard(
            id="PCI_DSS",
            name="Payment Card Industry Data Security Standard",
            version="4.0",
            description="Standard for organizations handling cardholder data",
            controls=controls,
            effective_date=datetime(2022, 3, 31),
            renewal_period_months=12,
            issuing_body="PCI SSC",
            regions=["Global"],
        )

    def _load_default_mappings(self) -> None:
        """Load default control mappings between standards."""
        # ISO 27001 to SOC2 mappings
        self._mappings.extend([
            ControlMapping(
                source_standard="ISO_27001",
                source_control_id="A.5.1",
                target_standard="SOC2_TYPE2",
                target_control_ids=["CC1.1", "CC2.1"],
                mapping_type="partial",
                notes="ISO policies map to SOC2 integrity and communication",
            ),
            ControlMapping(
                source_standard="ISO_27001",
                source_control_id="A.8.2",
                target_standard="SOC2_TYPE2",
                target_control_ids=["CC6.1"],
                mapping_type="equivalent",
                notes="Privileged access controls are equivalent",
            ),
            ControlMapping(
                source_standard="ISO_27001",
                source_control_id="A.8.5",
                target_standard="SOC2_TYPE2",
                target_control_ids=["CC6.1"],
                mapping_type="equivalent",
                notes="Authentication controls are equivalent",
            ),
        ])

    def get_standard(self, standard_id: str) -> CertificationStandard:
        """
        Retrieve a certification standard by ID.

        Args:
            standard_id: The unique identifier of the standard

        Returns:
            The certification standard

        Raises:
            KeyError: If standard not found
        """
        if standard_id not in self._standards:
            raise KeyError(f"Standard '{standard_id}' not found in registry")
        return self._standards[standard_id]

    def list_standards(self) -> List[CertificationStandard]:
        """
        List all available certification standards.

        Returns:
            List of all certification standards
        """
        return list(self._standards.values())

    def get_controls(self, standard_id: str) -> List[ControlRequirement]:
        """
        Get control requirements for a standard.

        Args:
            standard_id: The standard identifier

        Returns:
            List of control requirements
        """
        standard = self.get_standard(standard_id)
        return standard.controls

    def search_controls(
        self,
        query: str,
        standard_id: Optional[str] = None,
        category: Optional[ControlCategory] = None,
    ) -> List[ControlRequirement]:
        """
        Search across all controls.

        Args:
            query: Search query string
            standard_id: Optional standard to filter by
            category: Optional category to filter by

        Returns:
            List of matching control requirements
        """
        results = []
        query_lower = query.lower()

        standards = [self.get_standard(standard_id)] if standard_id else self.list_standards()

        for standard in standards:
            for control in standard.controls:
                if category and control.category != category:
                    continue

                if (
                    query_lower in control.name.lower()
                    or query_lower in control.description.lower()
                    or query_lower in control.control_id.lower()
                ):
                    results.append(control)

        return results

    def get_control_mapping(
        self,
        source: str,
        target: str,
    ) -> List[ControlMapping]:
        """
        Get mapping between two standards' controls.

        Args:
            source: Source standard ID
            target: Target standard ID

        Returns:
            List of control mappings
        """
        return [
            m for m in self._mappings
            if m.source_standard == source and m.target_standard == target
        ]

    def add_standard(self, standard: CertificationStandard) -> None:
        """
        Add a new certification standard to the registry.

        Args:
            standard: The certification standard to add
        """
        self._standards[standard.id] = standard
        logger.info("Added standard '%s' to registry", standard.id)

    def add_mapping(self, mapping: ControlMapping) -> None:
        """
        Add a new control mapping.

        Args:
            mapping: The control mapping to add
        """
        self._mappings.append(mapping)
        logger.info(
            "Added mapping from %s:%s to %s",
            mapping.source_standard,
            mapping.source_control_id,
            mapping.target_standard,
        )

    def health_check(self) -> Dict[str, Any]:
        """
        Perform health check on the registry.

        Returns:
            Health check results
        """
        return {
            "status": "healthy",
            "standards_count": len(self._standards),
            "total_controls": sum(s.total_controls for s in self._standards.values()),
            "mappings_count": len(self._mappings),
        }
