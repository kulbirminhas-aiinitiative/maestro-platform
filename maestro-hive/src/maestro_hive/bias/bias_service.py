"""
Bias Service (MD-2157)

EU AI Act Compliance - Article 10

Main orchestration service for bias detection and mitigation.
Integrates all bias components and provides a unified API.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

from .models import (
    BiasVector,
    BiasVectorType,
    BiasSeverity,
    AuditRecord,
    FairnessWeight,
    CoolingOffPeriod,
    BiasIncident,
    FairnessAuditResult
)
from .audit_logger import BiasAuditLogger, get_audit_logger
from .fairness_weights import FairnessWeightCalculator, get_fairness_calculator
from .adaptive_scorer import AdaptiveScorer, get_adaptive_scorer
from .cooling_off import CoolingOffManager, get_cooling_off_manager
from .incident_reporter import BiasIncidentReporter, get_incident_reporter
from .fairness_auditor import FairnessAuditor, get_fairness_auditor

logger = logging.getLogger(__name__)


# Pre-defined bias vectors from EPIC MD-2157
KNOWN_BIAS_VECTORS = [
    BiasVector(
        vector_id="BV-1",
        vector_type=BiasVectorType.HISTORICAL_PERFORMANCE,
        name="Historical Performance Bias",
        description="Task matching overly favors agents with recent high performance",
        severity=BiasSeverity.HIGH,
        source_file="dde/task_matcher.py",
        source_component="TaskMatcher._calculate_quality_score",
        mitigation_strategy="Apply fairness weights and cooling-off periods",
        detection_patterns=["quality_score", "recent_quality_score"]
    ),
    BiasVector(
        vector_id="BV-2",
        vector_type=BiasVectorType.TIME_BASED,
        name="Time-Based Discrimination",
        description="Evaluation may discriminate based on time of execution",
        severity=BiasSeverity.MEDIUM,
        source_file="dde/agent_evaluator.py",
        source_component="AgentEvaluator._evaluate_efficiency",
        mitigation_strategy="Normalize time-based metrics",
        detection_patterns=["duration", "time_efficiency"]
    ),
    BiasVector(
        vector_id="BV-3",
        vector_type=BiasVectorType.DEFAULT_STRATEGY,
        name="Default Strategy Bias",
        description="Routing defaults to strategies that may introduce bias",
        severity=BiasSeverity.MEDIUM,
        source_file="dde/routing_engine.py",
        source_component="RoutingEngine.route",
        mitigation_strategy="Implement bias-aware routing",
        detection_patterns=["default_strategy", "fallback"]
    ),
    BiasVector(
        vector_id="BV-4",
        vector_type=BiasVectorType.INITIAL_CAPABILITY,
        name="Initial Capability Assumptions",
        description="New agents start with hardcoded proficiency scores",
        severity=BiasSeverity.LOW,
        source_file="dde/agent_registry.py",
        source_component="AgentRegistry.register_agent",
        mitigation_strategy="Remove hardcoded proficiency scores",
        detection_patterns=["default_proficiency", "initial_score"]
    ),
    BiasVector(
        vector_id="BV-5",
        vector_type=BiasVectorType.HARD_THRESHOLD,
        name="Hard Threshold Bias",
        description="Hard thresholds for grades may unfairly penalize edge cases",
        severity=BiasSeverity.MEDIUM,
        source_file="dde/verdict_aggregator.py",
        source_component="VerdictAggregator._calculate_grade",
        mitigation_strategy="Replace with adaptive scoring",
        detection_patterns=["GRADE_THRESHOLDS", "threshold"]
    ),
    BiasVector(
        vector_id="BV-6",
        vector_type=BiasVectorType.QUANTITY_OVER_QUALITY,
        name="Quantity Over Quality",
        description="Metrics may favor quantity of output over quality",
        severity=BiasSeverity.MEDIUM,
        source_file="quality_fabric_client.py",
        source_component="QualityFabricClient.calculate_score",
        mitigation_strategy="Add quality-aware test validation",
        detection_patterns=["files_per_min", "output_count"]
    ),
    BiasVector(
        vector_id="BV-7",
        vector_type=BiasVectorType.IP_ATTRIBUTION,
        name="IP Attribution Gap",
        description="Lack of attribution tracking for code contributions",
        severity=BiasSeverity.HIGH,
        source_file="sdlc_code_generator.py",
        source_component="SDLCCodeGenerator.generate",
        mitigation_strategy="Implement contribution tracking",
        detection_patterns=["author", "attribution"]
    ),
    BiasVector(
        vector_id="BV-8",
        vector_type=BiasVectorType.TEMPLATE_LOCKIN,
        name="Template Lock-In",
        description="Template selection may lock in biased patterns",
        severity=BiasSeverity.LOW,
        source_file="template_intelligence.py",
        source_component="TemplateIntelligence.select",
        mitigation_strategy="Add template diversity scoring",
        detection_patterns=["template_id", "locked"]
    ),
    BiasVector(
        vector_id="BV-9",
        vector_type=BiasVectorType.ROLE_RIGIDITY,
        name="Role Rigidity",
        description="Roles are rigidly defined without flexibility",
        severity=BiasSeverity.LOW,
        source_file="services/governance_service.py",
        source_component="GovernanceService.check_permission",
        mitigation_strategy="Implement dynamic role expansion",
        detection_patterns=["role", "permission"]
    ),
    BiasVector(
        vector_id="BV-10",
        vector_type=BiasVectorType.NO_ESCALATION,
        name="No Escalation Path",
        description="No mechanism for agents to escalate bias concerns",
        severity=BiasSeverity.MEDIUM,
        source_file="persona_executor_v2.py",
        source_component="PersonaExecutor.execute",
        mitigation_strategy="Add bias incident reporting",
        detection_patterns=["escalate", "report"]
    )
]


class BiasService:
    """
    Main bias detection and mitigation service.

    Provides a unified API for all bias-related operations
    and coordinates between components.
    """

    def __init__(
        self,
        audit_logger: Optional[BiasAuditLogger] = None,
        fairness_calculator: Optional[FairnessWeightCalculator] = None,
        adaptive_scorer: Optional[AdaptiveScorer] = None,
        cooling_off_manager: Optional[CoolingOffManager] = None,
        incident_reporter: Optional[BiasIncidentReporter] = None,
        fairness_auditor: Optional[FairnessAuditor] = None
    ):
        """
        Initialize the bias service.

        Args:
            audit_logger: Optional audit logger
            fairness_calculator: Optional fairness calculator
            adaptive_scorer: Optional adaptive scorer
            cooling_off_manager: Optional cooling-off manager
            incident_reporter: Optional incident reporter
            fairness_auditor: Optional fairness auditor
        """
        self.audit_logger = audit_logger or get_audit_logger()
        self.fairness_calculator = fairness_calculator or get_fairness_calculator()
        self.adaptive_scorer = adaptive_scorer or get_adaptive_scorer()
        self.cooling_off_manager = cooling_off_manager or get_cooling_off_manager()
        self.incident_reporter = incident_reporter or get_incident_reporter()
        self.fairness_auditor = fairness_auditor or get_fairness_auditor()

        # Known bias vectors
        self._bias_vectors = {v.vector_id: v for v in KNOWN_BIAS_VECTORS}

        logger.info("BiasService initialized with all components")

    # ==================== Audit Logging ====================

    def log_task_assignment(
        self,
        agent_id: str,
        task_id: str,
        task_type: str,
        decision_factors: Dict[str, float],
        alternatives: List[str],
        context: Optional[Dict[str, Any]] = None
    ) -> AuditRecord:
        """Log a task assignment decision with bias awareness."""
        # Calculate fairness
        fairness_score = self.fairness_calculator.get_fairness_score()
        fairness_adjustments = self.fairness_calculator.get_adjusted_weights(
            agent_id,
            decision_factors
        )

        # Check for bias indicators
        bias_indicators = self._detect_bias_indicators(
            agent_id, task_id, decision_factors
        )

        # Log the assignment
        record = self.audit_logger.log_task_assignment(
            agent_id=agent_id,
            task_id=task_id,
            task_type=task_type,
            decision_factors=decision_factors,
            alternatives=alternatives,
            fairness_score=fairness_score,
            fairness_adjustments=fairness_adjustments,
            bias_indicators=bias_indicators,
            context=context
        )

        # Record assignment for cooling-off
        self.cooling_off_manager.record_assignment(agent_id)

        return record

    def _detect_bias_indicators(
        self,
        agent_id: str,
        task_id: str,
        decision_factors: Dict[str, float]
    ) -> List[str]:
        """Detect potential bias indicators in a decision."""
        indicators = []

        # Check if agent is in cooling-off but still assigned
        if self.cooling_off_manager.is_cooling_off(agent_id):
            indicators.append(f"Agent {agent_id} is in cooling-off period")

        # Check for extreme quality bias
        quality_score = decision_factors.get('quality', decision_factors.get('quality_score', 0))
        if quality_score > 0.95:
            indicators.append(f"Very high quality score ({quality_score:.2f}) may indicate historical bias")

        # Check assignment frequency
        recent_count = self.cooling_off_manager.get_recent_assignment_count(agent_id)
        if recent_count > 3:
            indicators.append(f"Agent {agent_id} has {recent_count} recent assignments")

        return indicators

    # ==================== Fairness Weights ====================

    def get_fairness_adjusted_weights(
        self,
        agent_id: str,
        weights: Dict[str, float]
    ) -> Dict[str, float]:
        """Get fairness-adjusted weights for scoring."""
        return self.fairness_calculator.get_adjusted_weights(agent_id, weights)

    def get_fairness_score(self) -> float:
        """Get current overall fairness score."""
        return self.fairness_calculator.get_fairness_score()

    # ==================== Adaptive Scoring ====================

    def get_adaptive_grade(
        self,
        score: float,
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """Get grade using adaptive thresholds."""
        return self.adaptive_scorer.get_grade(score, context)

    def get_adaptive_deployment_decision(
        self,
        score: float,
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """Get deployment decision using adaptive thresholds."""
        return self.adaptive_scorer.get_deployment_decision(score, context)

    def evaluate_with_adaptive_threshold(
        self,
        threshold_id: str,
        value: float,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Evaluate a value against an adaptive threshold."""
        return self.adaptive_scorer.evaluate_with_adaptive_threshold(
            threshold_id, value, context
        )

    # ==================== Cooling-Off ====================

    def is_agent_cooling_off(self, agent_id: str) -> bool:
        """Check if an agent is in cooling-off period."""
        return self.cooling_off_manager.is_cooling_off(agent_id)

    def get_available_agents(self, agent_ids: List[str]) -> List[str]:
        """Filter agents to only those not in cooling-off."""
        return self.cooling_off_manager.get_available_agents(agent_ids)

    def force_cooling_off(
        self,
        agent_id: str,
        duration_minutes: float,
        reason: str = "manual"
    ):
        """Force a cooling-off period on an agent."""
        self.cooling_off_manager.force_cooling_off(agent_id, duration_minutes, reason)

    # ==================== Incident Reporting ====================

    def report_bias_incident(
        self,
        vector_type: BiasVectorType,
        severity: BiasSeverity,
        title: str,
        description: str,
        affected_agents: Optional[List[str]] = None,
        affected_tasks: Optional[List[str]] = None,
        evidence: Optional[Dict[str, Any]] = None,
        reporter: str = "system"
    ) -> BiasIncident:
        """Report a bias incident."""
        # Log the incident reporting
        self.audit_logger.log_fairness_adjustment(
            agent_id=affected_agents[0] if affected_agents else "system",
            adjustment_type=vector_type,
            original_value=0.0,
            adjusted_value=0.0,
            reason=f"Incident reported: {title}",
            context={'severity': severity.value}
        )

        return self.incident_reporter.report_incident(
            vector_type=vector_type,
            severity=severity,
            title=title,
            description=description,
            affected_agents=affected_agents,
            affected_tasks=affected_tasks,
            evidence=evidence,
            reporter=reporter
        )

    def get_open_incidents(self) -> List[BiasIncident]:
        """Get all open bias incidents."""
        return self.incident_reporter.get_open_incidents()

    # ==================== Fairness Audits ====================

    def run_fairness_audit(
        self,
        time_window_days: int = 30,
        create_incidents: bool = True
    ) -> FairnessAuditResult:
        """Run a fairness audit."""
        return self.fairness_auditor.run_audit(
            time_window_days=time_window_days,
            create_incidents=create_incidents
        )

    def get_audit_history(self, limit: int = 10) -> List[FairnessAuditResult]:
        """Get recent audit history."""
        return self.fairness_auditor.get_audit_history(limit)

    # ==================== Bias Vectors ====================

    def get_bias_vectors(self) -> List[BiasVector]:
        """Get all known bias vectors."""
        return list(self._bias_vectors.values())

    def get_bias_vector(self, vector_id: str) -> Optional[BiasVector]:
        """Get a specific bias vector."""
        return self._bias_vectors.get(vector_id)

    def get_high_severity_vectors(self) -> List[BiasVector]:
        """Get high severity bias vectors."""
        return [
            v for v in self._bias_vectors.values()
            if v.severity in [BiasSeverity.HIGH, BiasSeverity.CRITICAL]
        ]

    # ==================== Statistics & Status ====================

    def get_status(self) -> Dict[str, Any]:
        """Get overall bias service status."""
        open_incidents = self.get_open_incidents()
        high_severity = [i for i in open_incidents if i.severity in [BiasSeverity.HIGH, BiasSeverity.CRITICAL]]

        return {
            'status': 'warning' if high_severity else 'healthy',
            'fairness_score': self.get_fairness_score(),
            'open_incidents': len(open_incidents),
            'high_severity_incidents': len(high_severity),
            'agents_in_cooling_off': len(self.cooling_off_manager.get_all_active_periods()),
            'audit_records': self.audit_logger.get_statistics()['total_records'],
            'known_bias_vectors': len(self._bias_vectors),
            'last_audit': self.fairness_auditor.get_statistics().get('last_audit')
        }

    def get_comprehensive_statistics(self) -> Dict[str, Any]:
        """Get comprehensive statistics from all components."""
        return {
            'service_status': self.get_status(),
            'audit_logger': self.audit_logger.get_statistics(),
            'fairness': {
                'score': self.get_fairness_score(),
                'distribution': self.fairness_calculator.get_assignment_distribution()
            },
            'adaptive_scorer': self.adaptive_scorer.get_adaptation_statistics(),
            'cooling_off': self.cooling_off_manager.get_statistics(),
            'incidents': self.incident_reporter.get_statistics(),
            'auditor': self.fairness_auditor.get_statistics()
        }

    def export_audit_data(
        self,
        output_dir: str,
        since: Optional[datetime] = None
    ) -> Dict[str, int]:
        """
        Export all audit data for compliance purposes.

        Args:
            output_dir: Directory to export to
            since: Export data since this time

        Returns:
            Dictionary with counts of exported items
        """
        from pathlib import Path
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        since = since or (datetime.now() - timedelta(days=30))

        # Export audit records
        records_count = self.audit_logger.export_records(
            str(output_path / "audit_records.json"),
            since=since
        )

        # Export incidents
        incidents_count = self.incident_reporter.export_incidents(
            str(output_path / "incidents.json"),
            since=since
        )

        return {
            'audit_records': records_count,
            'incidents': incidents_count
        }


# Global instance
_bias_service: Optional[BiasService] = None


def get_bias_service() -> BiasService:
    """Get or create global bias service instance."""
    global _bias_service
    if _bias_service is None:
        _bias_service = BiasService()
    return _bias_service
