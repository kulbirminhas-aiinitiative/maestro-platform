"""
Bias Detection & Mitigation - Data Models (MD-2157)

EU AI Act Compliance - Article 10

Defines data structures for bias detection and mitigation.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from enum import Enum
import uuid


class BiasSeverity(str, Enum):
    """Severity levels for bias vectors."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class BiasVectorType(str, Enum):
    """Types of bias vectors identified in the system."""
    HISTORICAL_PERFORMANCE = "historical_performance"
    TIME_BASED = "time_based"
    DEFAULT_STRATEGY = "default_strategy"
    INITIAL_CAPABILITY = "initial_capability"
    HARD_THRESHOLD = "hard_threshold"
    QUANTITY_OVER_QUALITY = "quantity_over_quality"
    IP_ATTRIBUTION = "ip_attribution"
    TEMPLATE_LOCKIN = "template_lockin"
    ROLE_RIGIDITY = "role_rigidity"
    NO_ESCALATION = "no_escalation"


class AuditEventType(str, Enum):
    """Types of audit events."""
    TASK_ASSIGNMENT = "task_assignment"
    AGENT_EVALUATION = "agent_evaluation"
    QUALITY_SCORING = "quality_scoring"
    THRESHOLD_DECISION = "threshold_decision"
    FAIRNESS_ADJUSTMENT = "fairness_adjustment"
    COOLING_OFF_APPLIED = "cooling_off_applied"
    INCIDENT_REPORTED = "incident_reported"
    AUDIT_COMPLETED = "audit_completed"


class IncidentStatus(str, Enum):
    """Status of a bias incident."""
    REPORTED = "reported"
    INVESTIGATING = "investigating"
    CONFIRMED = "confirmed"
    MITIGATED = "mitigated"
    RESOLVED = "resolved"
    FALSE_POSITIVE = "false_positive"


@dataclass
class BiasVector:
    """
    Represents an identified bias vector in the system.

    Each vector corresponds to a potential source of unfair treatment
    in the AI decision-making process.
    """
    vector_id: str
    vector_type: BiasVectorType
    name: str
    description: str
    severity: BiasSeverity
    source_file: str
    source_component: str
    mitigation_strategy: str
    detection_patterns: List[str] = field(default_factory=list)
    is_active: bool = True
    last_detected: Optional[datetime] = None
    detection_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            'vector_id': self.vector_id,
            'vector_type': self.vector_type.value,
            'name': self.name,
            'description': self.description,
            'severity': self.severity.value,
            'source_file': self.source_file,
            'source_component': self.source_component,
            'mitigation_strategy': self.mitigation_strategy,
            'detection_patterns': self.detection_patterns,
            'is_active': self.is_active,
            'last_detected': self.last_detected.isoformat() if self.last_detected else None,
            'detection_count': self.detection_count
        }


@dataclass
class AuditRecord:
    """
    Audit record for tracking decisions made by the system.

    Enables post-hoc analysis of fairness in task assignment,
    agent evaluation, and quality scoring decisions.
    """
    record_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    event_type: AuditEventType = AuditEventType.TASK_ASSIGNMENT
    timestamp: datetime = field(default_factory=datetime.now)

    # Decision context
    agent_id: Optional[str] = None
    task_id: Optional[str] = None
    task_type: Optional[str] = None

    # Decision details
    decision: str = ""
    decision_factors: Dict[str, float] = field(default_factory=dict)
    alternatives_considered: List[str] = field(default_factory=list)

    # Fairness metrics
    fairness_score: float = 1.0
    fairness_adjustments: Dict[str, float] = field(default_factory=dict)
    bias_indicators: List[str] = field(default_factory=list)

    # Context
    context: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'record_id': self.record_id,
            'event_type': self.event_type.value,
            'timestamp': self.timestamp.isoformat(),
            'agent_id': self.agent_id,
            'task_id': self.task_id,
            'task_type': self.task_type,
            'decision': self.decision,
            'decision_factors': self.decision_factors,
            'alternatives_considered': self.alternatives_considered,
            'fairness_score': self.fairness_score,
            'fairness_adjustments': self.fairness_adjustments,
            'bias_indicators': self.bias_indicators,
            'context': self.context
        }


@dataclass
class FairnessWeight:
    """
    Fairness weight adjustment for scoring algorithms.

    Used to adjust weights in task matching and evaluation
    to counteract identified biases.
    """
    weight_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    agent_id: str = ""
    factor_name: str = ""
    original_weight: float = 0.0
    adjusted_weight: float = 0.0
    adjustment_reason: str = ""
    adjustment_source: BiasVectorType = BiasVectorType.HISTORICAL_PERFORMANCE
    effective_from: datetime = field(default_factory=datetime.now)
    effective_until: Optional[datetime] = None

    @property
    def adjustment_delta(self) -> float:
        """Calculate the adjustment delta."""
        return self.adjusted_weight - self.original_weight

    @property
    def is_active(self) -> bool:
        """Check if the adjustment is currently active."""
        now = datetime.now()
        if self.effective_until and now > self.effective_until:
            return False
        return now >= self.effective_from

    def to_dict(self) -> Dict[str, Any]:
        return {
            'weight_id': self.weight_id,
            'agent_id': self.agent_id,
            'factor_name': self.factor_name,
            'original_weight': self.original_weight,
            'adjusted_weight': self.adjusted_weight,
            'adjustment_delta': self.adjustment_delta,
            'adjustment_reason': self.adjustment_reason,
            'adjustment_source': self.adjustment_source.value,
            'effective_from': self.effective_from.isoformat(),
            'effective_until': self.effective_until.isoformat() if self.effective_until else None,
            'is_active': self.is_active
        }


@dataclass
class CoolingOffPeriod:
    """
    Cooling-off period for agent selection.

    Prevents over-selection of high-performing agents by
    enforcing mandatory rest periods after frequent assignments.
    """
    period_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    agent_id: str = ""
    reason: str = ""
    started_at: datetime = field(default_factory=datetime.now)
    duration: timedelta = field(default_factory=lambda: timedelta(hours=1))
    recent_assignment_count: int = 0
    threshold_exceeded: bool = False

    @property
    def ends_at(self) -> datetime:
        """Calculate when the cooling-off period ends."""
        return self.started_at + self.duration

    @property
    def is_active(self) -> bool:
        """Check if the cooling-off period is still active."""
        return datetime.now() < self.ends_at

    @property
    def remaining_seconds(self) -> float:
        """Get remaining seconds in the cooling-off period."""
        if not self.is_active:
            return 0.0
        return (self.ends_at - datetime.now()).total_seconds()

    def to_dict(self) -> Dict[str, Any]:
        return {
            'period_id': self.period_id,
            'agent_id': self.agent_id,
            'reason': self.reason,
            'started_at': self.started_at.isoformat(),
            'ends_at': self.ends_at.isoformat(),
            'duration_seconds': self.duration.total_seconds(),
            'remaining_seconds': self.remaining_seconds,
            'is_active': self.is_active,
            'recent_assignment_count': self.recent_assignment_count,
            'threshold_exceeded': self.threshold_exceeded
        }


@dataclass
class BiasIncident:
    """
    Bias incident report.

    Represents a reported or detected bias incident that
    requires investigation and potential mitigation.
    """
    incident_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    vector_type: BiasVectorType = BiasVectorType.HISTORICAL_PERFORMANCE
    severity: BiasSeverity = BiasSeverity.MEDIUM
    status: IncidentStatus = IncidentStatus.REPORTED

    # Incident details
    title: str = ""
    description: str = ""
    affected_agents: List[str] = field(default_factory=list)
    affected_tasks: List[str] = field(default_factory=list)

    # Evidence
    evidence: Dict[str, Any] = field(default_factory=dict)
    audit_records: List[str] = field(default_factory=list)  # Record IDs

    # Resolution
    mitigation_applied: Optional[str] = None
    resolution_notes: Optional[str] = None

    # Timestamps
    reported_at: datetime = field(default_factory=datetime.now)
    resolved_at: Optional[datetime] = None

    # Reporter
    reporter: str = "system"

    def to_dict(self) -> Dict[str, Any]:
        return {
            'incident_id': self.incident_id,
            'vector_type': self.vector_type.value,
            'severity': self.severity.value,
            'status': self.status.value,
            'title': self.title,
            'description': self.description,
            'affected_agents': self.affected_agents,
            'affected_tasks': self.affected_tasks,
            'evidence': self.evidence,
            'audit_records': self.audit_records,
            'mitigation_applied': self.mitigation_applied,
            'resolution_notes': self.resolution_notes,
            'reported_at': self.reported_at.isoformat(),
            'resolved_at': self.resolved_at.isoformat() if self.resolved_at else None,
            'reporter': self.reporter
        }


@dataclass
class AdaptiveThreshold:
    """
    Adaptive threshold configuration.

    Replaces hard thresholds with adaptive thresholds that
    adjust based on context and historical data.
    """
    threshold_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""

    # Threshold values
    base_value: float = 0.0
    min_value: float = 0.0
    max_value: float = 1.0
    current_value: float = 0.0

    # Adaptation parameters
    adaptation_rate: float = 0.1
    sample_window: int = 100
    sensitivity: float = 0.5

    # Context factors
    context_weights: Dict[str, float] = field(default_factory=dict)

    # History
    adjustment_history: List[Dict[str, Any]] = field(default_factory=list)
    last_adjusted: Optional[datetime] = None

    def adapt(self, performance_delta: float, context: Dict[str, Any] = None) -> float:
        """
        Adapt the threshold based on performance and context.

        Args:
            performance_delta: Difference from expected performance
            context: Optional context factors

        Returns:
            New threshold value
        """
        # Calculate context adjustment
        context_adjustment = 0.0
        if context and self.context_weights:
            for key, weight in self.context_weights.items():
                if key in context:
                    context_adjustment += context[key] * weight

        # Calculate new value
        adjustment = performance_delta * self.adaptation_rate * self.sensitivity
        adjustment += context_adjustment * self.adaptation_rate

        new_value = self.current_value + adjustment
        new_value = max(self.min_value, min(self.max_value, new_value))

        # Record adjustment
        self.adjustment_history.append({
            'timestamp': datetime.now().isoformat(),
            'old_value': self.current_value,
            'new_value': new_value,
            'performance_delta': performance_delta,
            'context_adjustment': context_adjustment
        })

        # Keep only recent history
        if len(self.adjustment_history) > self.sample_window:
            self.adjustment_history = self.adjustment_history[-self.sample_window:]

        self.current_value = new_value
        self.last_adjusted = datetime.now()

        return new_value

    def to_dict(self) -> Dict[str, Any]:
        return {
            'threshold_id': self.threshold_id,
            'name': self.name,
            'description': self.description,
            'base_value': self.base_value,
            'min_value': self.min_value,
            'max_value': self.max_value,
            'current_value': self.current_value,
            'adaptation_rate': self.adaptation_rate,
            'sample_window': self.sample_window,
            'sensitivity': self.sensitivity,
            'context_weights': self.context_weights,
            'recent_adjustments': len(self.adjustment_history),
            'last_adjusted': self.last_adjusted.isoformat() if self.last_adjusted else None
        }


@dataclass
class FairnessAuditResult:
    """
    Result of a fairness audit.

    Contains metrics and findings from a periodic
    fairness audit of the system.
    """
    audit_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    audit_type: str = "periodic"
    started_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None

    # Scope
    agents_audited: List[str] = field(default_factory=list)
    time_window_days: int = 30
    records_analyzed: int = 0

    # Fairness metrics
    overall_fairness_score: float = 1.0
    assignment_distribution: Dict[str, int] = field(default_factory=dict)
    quality_distribution: Dict[str, float] = field(default_factory=dict)

    # Findings
    bias_indicators: List[Dict[str, Any]] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)

    # Actions taken
    adjustments_made: List[str] = field(default_factory=list)
    incidents_created: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'audit_id': self.audit_id,
            'audit_type': self.audit_type,
            'started_at': self.started_at.isoformat(),
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'agents_audited': self.agents_audited,
            'time_window_days': self.time_window_days,
            'records_analyzed': self.records_analyzed,
            'overall_fairness_score': self.overall_fairness_score,
            'assignment_distribution': self.assignment_distribution,
            'quality_distribution': self.quality_distribution,
            'bias_indicators': self.bias_indicators,
            'recommendations': self.recommendations,
            'adjustments_made': self.adjustments_made,
            'incidents_created': self.incidents_created
        }
