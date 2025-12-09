"""
Transparency Manager Module - EU AI Act Article 13 Compliance

Provides clear information to users about AI system operation,
capabilities, and limitations.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
import json


class TransparencyLevel(Enum):
    """Levels of transparency information."""
    BASIC = "basic"  # Minimal required disclosure
    STANDARD = "standard"  # Standard user information
    DETAILED = "detailed"  # Technical details for experts
    FULL = "full"  # Complete transparency for auditors


class InformationType(Enum):
    """Types of transparency information."""
    SYSTEM_CAPABILITIES = "system_capabilities"
    SYSTEM_LIMITATIONS = "system_limitations"
    INTENDED_PURPOSE = "intended_purpose"
    DECISION_EXPLANATION = "decision_explanation"
    DATA_USAGE = "data_usage"
    RISK_INFORMATION = "risk_information"
    CONTACT_INFORMATION = "contact_information"
    TRAINING_DATA_INFO = "training_data_info"


@dataclass
class TransparencyItem:
    """Single transparency information item."""
    item_id: str
    info_type: InformationType
    title: str
    content: str
    level: TransparencyLevel
    audience: List[str]  # e.g., ["end_user", "deployer", "auditor"]
    version: str
    effective_date: datetime
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class DecisionExplanation:
    """Explanation for an AI decision."""
    decision_id: str
    decision_type: str
    input_summary: str
    output_summary: str
    confidence: float
    contributing_factors: List[Dict[str, Any]]
    limitations_applicable: List[str]
    explanation_text: str
    generated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class TransparencyReport:
    """Comprehensive transparency report."""
    report_id: str
    ai_system_id: str
    ai_system_name: str
    report_type: str
    transparency_level: TransparencyLevel
    items: List[TransparencyItem]
    generated_at: datetime = field(default_factory=datetime.utcnow)
    valid_until: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert report to dictionary."""
        return {
            "report_id": self.report_id,
            "ai_system_id": self.ai_system_id,
            "ai_system_name": self.ai_system_name,
            "report_type": self.report_type,
            "transparency_level": self.transparency_level.value,
            "items": [
                {
                    "item_id": item.item_id,
                    "type": item.info_type.value,
                    "title": item.title,
                    "content": item.content,
                    "level": item.level.value,
                    "audience": item.audience
                }
                for item in self.items
            ],
            "generated_at": self.generated_at.isoformat(),
            "valid_until": self.valid_until.isoformat() if self.valid_until else None
        }


class TransparencyManager:
    """
    Transparency Manager for EU AI Act Article 13 compliance.

    Ensures users receive clear and appropriate information about
    the AI system's operation, capabilities, and limitations.
    """

    def __init__(
        self,
        ai_system_id: str,
        ai_system_name: str,
        provider_name: str,
        contact_email: str
    ):
        """
        Initialize transparency manager.

        Args:
            ai_system_id: Unique identifier for the AI system
            ai_system_name: Human-readable name
            provider_name: Name of the AI system provider
            contact_email: Contact email for inquiries
        """
        self.ai_system_id = ai_system_id
        self.ai_system_name = ai_system_name
        self.provider_name = provider_name
        self.contact_email = contact_email

        self._transparency_items: Dict[str, TransparencyItem] = {}
        self._decision_explanations: Dict[str, DecisionExplanation] = {}
        self._item_counter = 0

        # Initialize with mandatory information
        self._initialize_mandatory_items()

    def _generate_item_id(self) -> str:
        """Generate unique item ID."""
        self._item_counter += 1
        return f"TI-{self.ai_system_id[:8]}-{self._item_counter:04d}"

    def _initialize_mandatory_items(self) -> None:
        """Initialize mandatory transparency items."""
        # Contact information
        self.add_transparency_item(
            info_type=InformationType.CONTACT_INFORMATION,
            title="Provider Contact Information",
            content=f"Provider: {self.provider_name}\nContact: {self.contact_email}",
            level=TransparencyLevel.BASIC,
            audience=["end_user", "deployer", "auditor"]
        )

    def add_transparency_item(
        self,
        info_type: InformationType,
        title: str,
        content: str,
        level: TransparencyLevel = TransparencyLevel.STANDARD,
        audience: Optional[List[str]] = None,
        version: str = "1.0"
    ) -> TransparencyItem:
        """
        Add a transparency information item.

        Args:
            info_type: Type of information
            title: Item title
            content: Information content
            level: Transparency level
            audience: Target audience
            version: Version string

        Returns:
            Created TransparencyItem
        """
        item = TransparencyItem(
            item_id=self._generate_item_id(),
            info_type=info_type,
            title=title,
            content=content,
            level=level,
            audience=audience or ["end_user"],
            version=version,
            effective_date=datetime.utcnow()
        )

        self._transparency_items[item.item_id] = item
        return item

    def set_capabilities(
        self,
        capabilities: List[str],
        performance_metrics: Dict[str, float],
        level: TransparencyLevel = TransparencyLevel.STANDARD
    ) -> TransparencyItem:
        """
        Document system capabilities.

        Args:
            capabilities: List of system capabilities
            performance_metrics: Performance metrics
            level: Transparency level

        Returns:
            Created TransparencyItem
        """
        content = "System Capabilities:\n"
        for cap in capabilities:
            content += f"- {cap}\n"

        content += "\nPerformance Metrics:\n"
        for metric, value in performance_metrics.items():
            content += f"- {metric}: {value:.2%}\n"

        return self.add_transparency_item(
            info_type=InformationType.SYSTEM_CAPABILITIES,
            title="System Capabilities",
            content=content,
            level=level,
            audience=["end_user", "deployer"]
        )

    def set_limitations(
        self,
        limitations: List[str],
        known_failure_modes: List[str],
        level: TransparencyLevel = TransparencyLevel.STANDARD
    ) -> TransparencyItem:
        """
        Document system limitations.

        Args:
            limitations: List of known limitations
            known_failure_modes: Known failure scenarios
            level: Transparency level

        Returns:
            Created TransparencyItem
        """
        content = "System Limitations:\n"
        for lim in limitations:
            content += f"- {lim}\n"

        if known_failure_modes:
            content += "\nKnown Failure Modes:\n"
            for mode in known_failure_modes:
                content += f"- {mode}\n"

        return self.add_transparency_item(
            info_type=InformationType.SYSTEM_LIMITATIONS,
            title="System Limitations",
            content=content,
            level=level,
            audience=["end_user", "deployer"]
        )

    def set_intended_purpose(
        self,
        purpose: str,
        use_cases: List[str],
        prohibited_uses: List[str],
        level: TransparencyLevel = TransparencyLevel.STANDARD
    ) -> TransparencyItem:
        """
        Document intended purpose.

        Args:
            purpose: Primary intended purpose
            use_cases: Intended use cases
            prohibited_uses: Prohibited uses
            level: Transparency level

        Returns:
            Created TransparencyItem
        """
        content = f"Intended Purpose:\n{purpose}\n\n"

        content += "Intended Use Cases:\n"
        for use in use_cases:
            content += f"- {use}\n"

        if prohibited_uses:
            content += "\nProhibited Uses:\n"
            for prohibited in prohibited_uses:
                content += f"- {prohibited}\n"

        return self.add_transparency_item(
            info_type=InformationType.INTENDED_PURPOSE,
            title="Intended Purpose",
            content=content,
            level=level,
            audience=["end_user", "deployer", "auditor"]
        )

    def set_data_usage(
        self,
        data_types_collected: List[str],
        purposes: List[str],
        retention_period: str,
        sharing_parties: List[str],
        level: TransparencyLevel = TransparencyLevel.STANDARD
    ) -> TransparencyItem:
        """
        Document data usage practices.

        Args:
            data_types_collected: Types of data collected
            purposes: Purposes for data collection
            retention_period: Data retention period
            sharing_parties: Third parties data may be shared with
            level: Transparency level

        Returns:
            Created TransparencyItem
        """
        content = "Data Types Collected:\n"
        for dtype in data_types_collected:
            content += f"- {dtype}\n"

        content += "\nPurposes:\n"
        for purpose in purposes:
            content += f"- {purpose}\n"

        content += f"\nRetention Period: {retention_period}\n"

        if sharing_parties:
            content += "\nData may be shared with:\n"
            for party in sharing_parties:
                content += f"- {party}\n"

        return self.add_transparency_item(
            info_type=InformationType.DATA_USAGE,
            title="Data Usage Information",
            content=content,
            level=level,
            audience=["end_user"]
        )

    def set_risk_information(
        self,
        risk_level: str,
        potential_risks: List[str],
        mitigation_measures: List[str],
        level: TransparencyLevel = TransparencyLevel.STANDARD
    ) -> TransparencyItem:
        """
        Document risk information.

        Args:
            risk_level: Overall risk level classification
            potential_risks: List of potential risks
            mitigation_measures: Risk mitigation measures
            level: Transparency level

        Returns:
            Created TransparencyItem
        """
        content = f"Risk Classification: {risk_level}\n\n"

        content += "Potential Risks:\n"
        for risk in potential_risks:
            content += f"- {risk}\n"

        content += "\nMitigation Measures:\n"
        for measure in mitigation_measures:
            content += f"- {measure}\n"

        return self.add_transparency_item(
            info_type=InformationType.RISK_INFORMATION,
            title="Risk Information",
            content=content,
            level=level,
            audience=["end_user", "deployer", "auditor"]
        )

    def generate_decision_explanation(
        self,
        decision_id: str,
        decision_type: str,
        input_data: Any,
        output: Any,
        confidence: float,
        contributing_factors: List[Dict[str, Any]],
        limitations_applicable: Optional[List[str]] = None
    ) -> DecisionExplanation:
        """
        Generate explanation for an AI decision.

        Args:
            decision_id: Unique decision identifier
            decision_type: Type of decision
            input_data: Input that led to decision
            output: Decision output
            confidence: Confidence score
            contributing_factors: Factors that influenced decision
            limitations_applicable: Relevant limitations

        Returns:
            DecisionExplanation object
        """
        # Generate human-readable explanation
        explanation_parts = [
            f"Decision Type: {decision_type}",
            f"Confidence Level: {confidence:.1%}",
            "",
            "This decision was made based on the following factors:"
        ]

        for i, factor in enumerate(contributing_factors, 1):
            factor_name = factor.get("name", "Unknown factor")
            factor_weight = factor.get("weight", 0)
            explanation_parts.append(f"  {i}. {factor_name} (influence: {factor_weight:.1%})")

        if limitations_applicable:
            explanation_parts.append("")
            explanation_parts.append("Applicable Limitations:")
            for lim in limitations_applicable:
                explanation_parts.append(f"  - {lim}")

        explanation = DecisionExplanation(
            decision_id=decision_id,
            decision_type=decision_type,
            input_summary=str(input_data)[:200],
            output_summary=str(output)[:200],
            confidence=confidence,
            contributing_factors=contributing_factors,
            limitations_applicable=limitations_applicable or [],
            explanation_text="\n".join(explanation_parts)
        )

        self._decision_explanations[decision_id] = explanation
        return explanation

    def get_decision_explanation(
        self,
        decision_id: str
    ) -> Optional[DecisionExplanation]:
        """Get explanation for a specific decision."""
        return self._decision_explanations.get(decision_id)

    def generate_transparency_report(
        self,
        level: TransparencyLevel = TransparencyLevel.STANDARD,
        audience: Optional[str] = None,
        report_type: str = "standard"
    ) -> TransparencyReport:
        """
        Generate a transparency report.

        Args:
            level: Minimum transparency level to include
            audience: Filter by audience
            report_type: Type of report

        Returns:
            TransparencyReport
        """
        # Filter items by level and audience
        level_order = [
            TransparencyLevel.BASIC,
            TransparencyLevel.STANDARD,
            TransparencyLevel.DETAILED,
            TransparencyLevel.FULL
        ]
        level_index = level_order.index(level)

        filtered_items = []
        for item in self._transparency_items.values():
            item_level_index = level_order.index(item.level)
            if item_level_index <= level_index:
                if audience is None or audience in item.audience:
                    filtered_items.append(item)

        report = TransparencyReport(
            report_id=f"TR-{self.ai_system_id[:8]}-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
            ai_system_id=self.ai_system_id,
            ai_system_name=self.ai_system_name,
            report_type=report_type,
            transparency_level=level,
            items=filtered_items
        )

        return report

    def get_user_disclosure(self) -> Dict[str, Any]:
        """
        Get user-friendly disclosure information.

        Returns:
            Dictionary with user disclosure information
        """
        disclosure = {
            "system_name": self.ai_system_name,
            "provider": self.provider_name,
            "contact": self.contact_email,
            "disclosure_date": datetime.utcnow().isoformat(),
            "sections": {}
        }

        # Group items by type for user-friendly display
        for item in self._transparency_items.values():
            if "end_user" in item.audience:
                section = item.info_type.value
                if section not in disclosure["sections"]:
                    disclosure["sections"][section] = []
                disclosure["sections"][section].append({
                    "title": item.title,
                    "content": item.content
                })

        return disclosure

    def get_transparency_item(self, item_id: str) -> Optional[TransparencyItem]:
        """Get a specific transparency item."""
        return self._transparency_items.get(item_id)

    def get_items_by_type(
        self,
        info_type: InformationType
    ) -> List[TransparencyItem]:
        """Get all items of a specific type."""
        return [
            item for item in self._transparency_items.values()
            if item.info_type == info_type
        ]

    def export_transparency_data(self) -> Dict[str, Any]:
        """Export all transparency data."""
        return {
            "ai_system_id": self.ai_system_id,
            "ai_system_name": self.ai_system_name,
            "provider_name": self.provider_name,
            "contact_email": self.contact_email,
            "items": [
                {
                    "item_id": item.item_id,
                    "type": item.info_type.value,
                    "title": item.title,
                    "content": item.content,
                    "level": item.level.value,
                    "audience": item.audience,
                    "version": item.version,
                    "effective_date": item.effective_date.isoformat()
                }
                for item in self._transparency_items.values()
            ],
            "decision_explanations_count": len(self._decision_explanations),
            "export_date": datetime.utcnow().isoformat()
        }
