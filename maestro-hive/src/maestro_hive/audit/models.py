"""
Data models for the Audit & Record Keeping module.

EU AI Act Article 12 Compliance:
- Automatic logging of events during system operation
- Traceability of AI system functioning
- Recording of relevant data for post-market monitoring
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4


class DecisionType(str, Enum):
    """Types of AI decisions that are logged."""
    AGENT_SELECTION = "agent_selection"
    TASK_ASSIGNMENT = "task_assignment"
    QUALITY_ASSESSMENT = "quality_assessment"
    RESOURCE_ALLOCATION = "resource_allocation"
    WORKFLOW_ROUTING = "workflow_routing"
    ESCALATION = "escalation"
    AUTO_REMEDIATION = "auto_remediation"


class ContributorType(str, Enum):
    """Types of contributors for IP attribution."""
    AI_GENERATED = "ai_generated"
    HUMAN_AUTHORED = "human_authored"
    AI_ASSISTED = "ai_assisted"
    HYBRID = "hybrid"
    EXTERNAL_SERVICE = "external_service"


class RetentionTier(str, Enum):
    """Retention tiers for data lifecycle management."""
    HOT = "hot"           # Immediately accessible, 30 days
    WARM = "warm"         # Quick access, 90 days
    COLD = "cold"         # Archived, 1 year
    GLACIER = "glacier"   # Long-term compliance, 7 years
    DELETED = "deleted"   # Marked for deletion


class PIIMaskingLevel(str, Enum):
    """Levels of PII masking for audit logs."""
    NONE = "none"
    PARTIAL = "partial"
    FULL = "full"
    REDACTED = "redacted"


class AuditEventType(str, Enum):
    """Types of audit events."""
    DECISION = "decision"
    LLM_CALL = "llm_call"
    TEMPLATE_USAGE = "template_usage"
    IP_ATTRIBUTION = "ip_attribution"
    DATA_ACCESS = "data_access"
    CONFIGURATION_CHANGE = "configuration_change"
    SECURITY_EVENT = "security_event"
    COMPLIANCE_CHECK = "compliance_check"


@dataclass
class DecisionCandidate:
    """A candidate considered during decision-making."""
    candidate_id: str
    candidate_type: str
    score: float
    ranking: int
    factors: Dict[str, float] = field(default_factory=dict)
    disqualification_reason: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "candidate_type": self.candidate_type,
            "score": self.score,
            "ranking": self.ranking,
            "factors": self.factors,
            "disqualification_reason": self.disqualification_reason
        }


@dataclass
class DecisionRecord:
    """
    Record of an AI decision for audit purposes.

    Captures why a particular choice was made, what alternatives
    were considered, and the reasoning behind the selection.
    """
    id: UUID = field(default_factory=uuid4)
    decision_type: DecisionType = DecisionType.AGENT_SELECTION
    timestamp: datetime = field(default_factory=datetime.utcnow)

    # Decision context
    context_id: str = ""  # e.g., task_id, workflow_id
    context_type: str = ""  # e.g., "task", "workflow"

    # The selected option
    selected_id: str = ""
    selected_type: str = ""
    selected_score: float = 0.0

    # Alternatives considered
    candidates: List[DecisionCandidate] = field(default_factory=list)

    # Reasoning
    decision_factors: Dict[str, float] = field(default_factory=dict)
    reasoning_summary: str = ""
    confidence_score: float = 0.0

    # Metadata
    algorithm_version: str = "1.0"
    requesting_user: Optional[str] = None
    session_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": str(self.id),
            "decision_type": self.decision_type.value,
            "timestamp": self.timestamp.isoformat(),
            "context_id": self.context_id,
            "context_type": self.context_type,
            "selected_id": self.selected_id,
            "selected_type": self.selected_type,
            "selected_score": self.selected_score,
            "candidates": [c.to_dict() for c in self.candidates],
            "decision_factors": self.decision_factors,
            "reasoning_summary": self.reasoning_summary,
            "confidence_score": self.confidence_score,
            "algorithm_version": self.algorithm_version,
            "requesting_user": self.requesting_user,
            "session_id": self.session_id
        }


@dataclass
class LLMCallRecord:
    """
    Record of an LLM API call with PII masking.

    Captures inputs and outputs while protecting sensitive data.
    """
    id: UUID = field(default_factory=uuid4)
    timestamp: datetime = field(default_factory=datetime.utcnow)

    # LLM details
    provider: str = ""  # e.g., "openai", "anthropic"
    model: str = ""     # e.g., "gpt-4", "claude-3"

    # Input/Output (with PII masking applied)
    input_prompt: str = ""
    input_tokens: int = 0
    output_response: str = ""
    output_tokens: int = 0

    # PII masking info
    masking_level: PIIMaskingLevel = PIIMaskingLevel.FULL
    pii_detected: List[str] = field(default_factory=list)
    pii_patterns_masked: int = 0

    # Performance
    latency_ms: int = 0
    success: bool = True
    error_message: Optional[str] = None

    # Context
    context_id: str = ""
    context_type: str = ""
    purpose: str = ""

    # Cost tracking
    estimated_cost_usd: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": str(self.id),
            "timestamp": self.timestamp.isoformat(),
            "provider": self.provider,
            "model": self.model,
            "input_prompt": self.input_prompt,
            "input_tokens": self.input_tokens,
            "output_response": self.output_response,
            "output_tokens": self.output_tokens,
            "masking_level": self.masking_level.value,
            "pii_detected": self.pii_detected,
            "pii_patterns_masked": self.pii_patterns_masked,
            "latency_ms": self.latency_ms,
            "success": self.success,
            "error_message": self.error_message,
            "context_id": self.context_id,
            "context_type": self.context_type,
            "purpose": self.purpose,
            "estimated_cost_usd": self.estimated_cost_usd
        }


@dataclass
class TemplateUsageRecord:
    """
    Record of template usage for audit trail.

    Tracks which templates are used, when, and by whom.
    """
    id: UUID = field(default_factory=uuid4)
    timestamp: datetime = field(default_factory=datetime.utcnow)

    # Template details
    template_id: str = ""
    template_name: str = ""
    template_version: str = ""
    template_category: str = ""

    # Usage context
    used_by: str = ""  # user or agent ID
    used_by_type: str = ""  # "user" or "agent"
    context_id: str = ""
    context_type: str = ""

    # Template application
    input_variables: Dict[str, Any] = field(default_factory=dict)
    output_generated: bool = True
    output_size_bytes: int = 0

    # Customization tracking
    customizations_applied: List[str] = field(default_factory=list)
    original_template_hash: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": str(self.id),
            "timestamp": self.timestamp.isoformat(),
            "template_id": self.template_id,
            "template_name": self.template_name,
            "template_version": self.template_version,
            "template_category": self.template_category,
            "used_by": self.used_by,
            "used_by_type": self.used_by_type,
            "context_id": self.context_id,
            "context_type": self.context_type,
            "input_variables": self.input_variables,
            "output_generated": self.output_generated,
            "output_size_bytes": self.output_size_bytes,
            "customizations_applied": self.customizations_applied,
            "original_template_hash": self.original_template_hash
        }


@dataclass
class IPAttributionRecord:
    """
    Record of intellectual property attribution.

    Tracks AI vs human contributions for IP clarity.
    """
    id: UUID = field(default_factory=uuid4)
    timestamp: datetime = field(default_factory=datetime.utcnow)

    # Artifact details
    artifact_id: str = ""
    artifact_type: str = ""  # e.g., "code", "document", "design"
    artifact_name: str = ""

    # Attribution
    contributor_type: ContributorType = ContributorType.HYBRID
    ai_contribution_percent: float = 0.0
    human_contribution_percent: float = 0.0

    # Detailed breakdown
    contributions: List[Dict[str, Any]] = field(default_factory=list)

    # AI model details (if applicable)
    ai_models_used: List[str] = field(default_factory=list)
    ai_prompts_count: int = 0

    # Human details (if applicable)
    human_contributors: List[str] = field(default_factory=list)
    human_review_performed: bool = False
    human_modifications_count: int = 0

    # Context
    project_id: str = ""
    workflow_id: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": str(self.id),
            "timestamp": self.timestamp.isoformat(),
            "artifact_id": self.artifact_id,
            "artifact_type": self.artifact_type,
            "artifact_name": self.artifact_name,
            "contributor_type": self.contributor_type.value,
            "ai_contribution_percent": self.ai_contribution_percent,
            "human_contribution_percent": self.human_contribution_percent,
            "contributions": self.contributions,
            "ai_models_used": self.ai_models_used,
            "ai_prompts_count": self.ai_prompts_count,
            "human_contributors": self.human_contributors,
            "human_review_performed": self.human_review_performed,
            "human_modifications_count": self.human_modifications_count,
            "project_id": self.project_id,
            "workflow_id": self.workflow_id
        }


@dataclass
class RetentionPolicy:
    """
    Configuration for data retention policies.
    """
    id: UUID = field(default_factory=uuid4)
    name: str = ""
    description: str = ""

    # Tier durations
    hot_duration_days: int = 30
    warm_duration_days: int = 90
    cold_duration_days: int = 365
    glacier_duration_days: int = 2555  # ~7 years

    # Applicable data types
    applies_to: List[AuditEventType] = field(default_factory=list)

    # Archival settings
    archive_destination: str = "local"  # "local", "s3", "azure_blob"
    compress_on_archive: bool = True
    encrypt_on_archive: bool = True

    # Compliance requirements
    compliance_frameworks: List[str] = field(default_factory=list)  # e.g., ["EU_AI_ACT", "GDPR"]
    legal_hold_enabled: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": str(self.id),
            "name": self.name,
            "description": self.description,
            "hot_duration_days": self.hot_duration_days,
            "warm_duration_days": self.warm_duration_days,
            "cold_duration_days": self.cold_duration_days,
            "glacier_duration_days": self.glacier_duration_days,
            "applies_to": [t.value for t in self.applies_to],
            "archive_destination": self.archive_destination,
            "compress_on_archive": self.compress_on_archive,
            "encrypt_on_archive": self.encrypt_on_archive,
            "compliance_frameworks": self.compliance_frameworks,
            "legal_hold_enabled": self.legal_hold_enabled
        }

    def get_tier_for_age(self, age_days: int) -> RetentionTier:
        """Determine the retention tier based on record age."""
        if age_days <= self.hot_duration_days:
            return RetentionTier.HOT
        elif age_days <= self.hot_duration_days + self.warm_duration_days:
            return RetentionTier.WARM
        elif age_days <= self.hot_duration_days + self.warm_duration_days + self.cold_duration_days:
            return RetentionTier.COLD
        elif age_days <= self.hot_duration_days + self.warm_duration_days + self.cold_duration_days + self.glacier_duration_days:
            return RetentionTier.GLACIER
        else:
            return RetentionTier.DELETED


@dataclass
class AuditQueryResult:
    """Result of an audit query."""
    records: List[Dict[str, Any]] = field(default_factory=list)
    total_count: int = 0
    page: int = 1
    page_size: int = 100
    query_time_ms: int = 0
    filters_applied: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "records": self.records,
            "total_count": self.total_count,
            "page": self.page,
            "page_size": self.page_size,
            "query_time_ms": self.query_time_ms,
            "filters_applied": self.filters_applied
        }


@dataclass
class ComplianceReport:
    """
    Compliance audit report for regulators.
    """
    id: UUID = field(default_factory=uuid4)
    generated_at: datetime = field(default_factory=datetime.utcnow)

    # Report scope
    report_type: str = "standard"  # "standard", "detailed", "executive"
    date_range_start: datetime = field(default_factory=datetime.utcnow)
    date_range_end: datetime = field(default_factory=datetime.utcnow)

    # Statistics
    total_decisions: int = 0
    total_llm_calls: int = 0
    total_template_usages: int = 0
    total_ip_attributions: int = 0

    # Compliance metrics
    pii_masking_compliance: float = 100.0
    retention_compliance: float = 100.0
    logging_completeness: float = 100.0

    # Findings
    issues_found: List[Dict[str, Any]] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)

    # Export info
    export_format: str = "json"
    export_hash: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": str(self.id),
            "generated_at": self.generated_at.isoformat(),
            "report_type": self.report_type,
            "date_range_start": self.date_range_start.isoformat(),
            "date_range_end": self.date_range_end.isoformat(),
            "total_decisions": self.total_decisions,
            "total_llm_calls": self.total_llm_calls,
            "total_template_usages": self.total_template_usages,
            "total_ip_attributions": self.total_ip_attributions,
            "pii_masking_compliance": self.pii_masking_compliance,
            "retention_compliance": self.retention_compliance,
            "logging_completeness": self.logging_completeness,
            "issues_found": self.issues_found,
            "recommendations": self.recommendations,
            "export_format": self.export_format,
            "export_hash": self.export_hash
        }
