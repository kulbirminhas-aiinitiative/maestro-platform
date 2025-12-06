"""
Fairness Auditor (MD-2157)

EU AI Act Compliance - Article 10

Performs periodic fairness audits of the system to detect
and report potential biases.
"""

import logging
import statistics
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

from .models import (
    FairnessAuditResult,
    BiasVectorType,
    BiasSeverity
)
from .audit_logger import BiasAuditLogger, get_audit_logger
from .incident_reporter import BiasIncidentReporter, get_incident_reporter

logger = logging.getLogger(__name__)


class FairnessAuditor:
    """
    Fairness auditor for periodic system audits.

    Analyzes system behavior to detect potential biases
    and generates audit reports.
    """

    # Default thresholds for bias detection
    DEFAULT_THRESHOLDS = {
        'assignment_skew': 0.3,  # Max acceptable skew in assignment distribution
        'quality_variance': 0.15,  # Max acceptable quality variance
        'fairness_score_min': 0.7,  # Minimum acceptable fairness score
        'indicator_threshold': 5  # Max bias indicators before flagging
    }

    def __init__(
        self,
        audit_logger: Optional[BiasAuditLogger] = None,
        incident_reporter: Optional[BiasIncidentReporter] = None,
        thresholds: Optional[Dict[str, float]] = None
    ):
        """
        Initialize the fairness auditor.

        Args:
            audit_logger: Audit logger instance
            incident_reporter: Incident reporter instance
            thresholds: Custom thresholds for bias detection
        """
        self.audit_logger = audit_logger or get_audit_logger()
        self.incident_reporter = incident_reporter or get_incident_reporter()
        self.thresholds = {**self.DEFAULT_THRESHOLDS, **(thresholds or {})}

        # Audit history
        self._audit_history: List[FairnessAuditResult] = []

        logger.info("FairnessAuditor initialized")

    def run_audit(
        self,
        time_window_days: int = 30,
        agents_to_audit: Optional[List[str]] = None,
        create_incidents: bool = True
    ) -> FairnessAuditResult:
        """
        Run a fairness audit.

        Args:
            time_window_days: Days of data to analyze
            agents_to_audit: Specific agents to audit (or all)
            create_incidents: Whether to create incidents for findings

        Returns:
            FairnessAuditResult with findings
        """
        logger.info(f"Starting fairness audit (window: {time_window_days} days)")

        audit = FairnessAuditResult(
            time_window_days=time_window_days,
            agents_audited=agents_to_audit or []
        )

        since = datetime.now() - timedelta(days=time_window_days)

        # Get audit records
        records = self.audit_logger.get_records(since=since, limit=10000)
        audit.records_analyzed = len(records)

        # Analyze assignment distribution
        assignment_analysis = self._analyze_assignment_distribution(records)
        audit.assignment_distribution = assignment_analysis['distribution']

        # Analyze quality distribution
        quality_analysis = self._analyze_quality_distribution(records)
        audit.quality_distribution = quality_analysis['distribution']

        # Collect bias indicators
        bias_indicators = self._collect_bias_indicators(records, assignment_analysis, quality_analysis)
        audit.bias_indicators = bias_indicators

        # Calculate fairness score
        audit.overall_fairness_score = self._calculate_fairness_score(
            assignment_analysis,
            quality_analysis,
            bias_indicators
        )

        # Generate recommendations
        audit.recommendations = self._generate_recommendations(
            assignment_analysis,
            quality_analysis,
            bias_indicators
        )

        # Create incidents for significant findings
        if create_incidents:
            incidents = self._create_incidents_for_findings(audit, bias_indicators)
            audit.incidents_created = [i.incident_id for i in incidents]

        # Complete the audit
        audit.completed_at = datetime.now()

        # Store audit
        self._audit_history.append(audit)

        logger.info(f"Fairness audit complete: score={audit.overall_fairness_score:.2f}, "
                   f"indicators={len(bias_indicators)}, "
                   f"recommendations={len(audit.recommendations)}")

        return audit

    def _analyze_assignment_distribution(
        self,
        records
    ) -> Dict[str, Any]:
        """Analyze task assignment distribution across agents."""
        distribution = {}
        total = 0

        for record in records:
            if record.event_type.value == 'task_assignment' and record.agent_id:
                distribution[record.agent_id] = distribution.get(record.agent_id, 0) + 1
                total += 1

        # Calculate metrics
        if total > 0 and len(distribution) > 0:
            expected_share = 1.0 / len(distribution)
            shares = [count / total for count in distribution.values()]

            max_share = max(shares)
            min_share = min(shares)
            skew = max_share - min_share

            try:
                variance = statistics.variance(shares)
            except statistics.StatisticsError:
                variance = 0.0

            return {
                'distribution': distribution,
                'total': total,
                'expected_share': expected_share,
                'max_share': max_share,
                'min_share': min_share,
                'skew': skew,
                'variance': variance,
                'is_skewed': skew > self.thresholds['assignment_skew']
            }

        return {
            'distribution': {},
            'total': 0,
            'expected_share': 0,
            'max_share': 0,
            'min_share': 0,
            'skew': 0,
            'variance': 0,
            'is_skewed': False
        }

    def _analyze_quality_distribution(
        self,
        records
    ) -> Dict[str, Any]:
        """Analyze quality score distribution across agents."""
        quality_by_agent = {}

        for record in records:
            if record.agent_id and record.fairness_score > 0:
                if record.agent_id not in quality_by_agent:
                    quality_by_agent[record.agent_id] = []
                quality_by_agent[record.agent_id].append(record.fairness_score)

        # Calculate average quality per agent
        avg_quality = {}
        for agent_id, scores in quality_by_agent.items():
            avg_quality[agent_id] = sum(scores) / len(scores)

        # Calculate metrics
        if avg_quality:
            values = list(avg_quality.values())
            try:
                variance = statistics.variance(values)
            except statistics.StatisticsError:
                variance = 0.0

            return {
                'distribution': avg_quality,
                'variance': variance,
                'max_quality': max(values),
                'min_quality': min(values),
                'has_high_variance': variance > self.thresholds['quality_variance']
            }

        return {
            'distribution': {},
            'variance': 0,
            'max_quality': 0,
            'min_quality': 0,
            'has_high_variance': False
        }

    def _collect_bias_indicators(
        self,
        records,
        assignment_analysis: Dict[str, Any],
        quality_analysis: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Collect bias indicators from analysis."""
        indicators = []

        # Check assignment skew
        if assignment_analysis.get('is_skewed'):
            indicators.append({
                'type': BiasVectorType.HISTORICAL_PERFORMANCE.value,
                'severity': BiasSeverity.MEDIUM.value,
                'description': f"Assignment distribution is skewed (skew: {assignment_analysis['skew']:.2f})",
                'details': {
                    'max_share': assignment_analysis['max_share'],
                    'min_share': assignment_analysis['min_share'],
                    'threshold': self.thresholds['assignment_skew']
                }
            })

        # Check quality variance
        if quality_analysis.get('has_high_variance'):
            indicators.append({
                'type': BiasVectorType.HARD_THRESHOLD.value,
                'severity': BiasSeverity.LOW.value,
                'description': f"Quality scores have high variance ({quality_analysis['variance']:.3f})",
                'details': {
                    'variance': quality_analysis['variance'],
                    'threshold': self.thresholds['quality_variance']
                }
            })

        # Check for bias indicators in records
        bias_indicator_records = self.audit_logger.get_bias_indicators()
        if len(bias_indicator_records) > self.thresholds['indicator_threshold']:
            indicators.append({
                'type': BiasVectorType.DEFAULT_STRATEGY.value,
                'severity': BiasSeverity.MEDIUM.value,
                'description': f"High number of bias indicators detected ({len(bias_indicator_records)})",
                'details': {
                    'count': len(bias_indicator_records),
                    'threshold': self.thresholds['indicator_threshold']
                }
            })

        # Check for specific over-assigned agents
        distribution = assignment_analysis.get('distribution', {})
        total = assignment_analysis.get('total', 0)
        expected_share = assignment_analysis.get('expected_share', 0)

        for agent_id, count in distribution.items():
            if total > 0:
                share = count / total
                if share > expected_share * 2:  # More than 2x expected share
                    indicators.append({
                        'type': BiasVectorType.HISTORICAL_PERFORMANCE.value,
                        'severity': BiasSeverity.MEDIUM.value,
                        'description': f"Agent {agent_id} is over-assigned ({share:.1%} vs expected {expected_share:.1%})",
                        'details': {
                            'agent_id': agent_id,
                            'actual_share': share,
                            'expected_share': expected_share
                        }
                    })

        return indicators

    def _calculate_fairness_score(
        self,
        assignment_analysis: Dict[str, Any],
        quality_analysis: Dict[str, Any],
        bias_indicators: List[Dict[str, Any]]
    ) -> float:
        """Calculate overall fairness score."""
        score = 1.0

        # Penalize for assignment skew
        skew = assignment_analysis.get('skew', 0)
        if skew > 0:
            score -= min(0.3, skew)

        # Penalize for quality variance
        variance = quality_analysis.get('variance', 0)
        if variance > 0:
            score -= min(0.2, variance)

        # Penalize for bias indicators
        indicator_count = len(bias_indicators)
        if indicator_count > 0:
            score -= min(0.3, indicator_count * 0.05)

        return max(0.0, score)

    def _generate_recommendations(
        self,
        assignment_analysis: Dict[str, Any],
        quality_analysis: Dict[str, Any],
        bias_indicators: List[Dict[str, Any]]
    ) -> List[str]:
        """Generate recommendations based on findings."""
        recommendations = []

        if assignment_analysis.get('is_skewed'):
            recommendations.append(
                "Implement cooling-off periods for frequently assigned agents"
            )
            recommendations.append(
                "Review task matcher weights to improve fairness"
            )

        if quality_analysis.get('has_high_variance'):
            recommendations.append(
                "Consider adaptive thresholds for quality scoring"
            )

        # Recommendations based on indicator types
        indicator_types = set(i['type'] for i in bias_indicators)

        if BiasVectorType.HISTORICAL_PERFORMANCE.value in indicator_types:
            recommendations.append(
                "Apply fairness weights to historical performance scoring"
            )

        if BiasVectorType.HARD_THRESHOLD.value in indicator_types:
            recommendations.append(
                "Replace hard thresholds with adaptive thresholds"
            )

        if not recommendations:
            recommendations.append("Continue monitoring for potential biases")

        return recommendations[:5]

    def _create_incidents_for_findings(
        self,
        audit: FairnessAuditResult,
        bias_indicators: List[Dict[str, Any]]
    ) -> List:
        """Create incidents for significant findings."""
        incidents = []

        # Create incident for each high/critical indicator
        for indicator in bias_indicators:
            if indicator['severity'] in [BiasSeverity.HIGH.value, BiasSeverity.CRITICAL.value]:
                incident = self.incident_reporter.report_incident(
                    vector_type=BiasVectorType(indicator['type']),
                    severity=BiasSeverity(indicator['severity']),
                    title=f"Bias detected: {indicator['type']}",
                    description=indicator['description'],
                    evidence={'indicator': indicator, 'audit_id': audit.audit_id},
                    reporter="fairness_auditor"
                )
                incidents.append(incident)

        # Create summary incident if fairness score is low
        if audit.overall_fairness_score < self.thresholds['fairness_score_min']:
            incident = self.incident_reporter.report_incident(
                vector_type=BiasVectorType.DEFAULT_STRATEGY,
                severity=BiasSeverity.MEDIUM,
                title="Low fairness score detected",
                description=f"Overall fairness score ({audit.overall_fairness_score:.2f}) "
                           f"is below threshold ({self.thresholds['fairness_score_min']})",
                evidence={'audit_id': audit.audit_id, 'score': audit.overall_fairness_score},
                reporter="fairness_auditor"
            )
            incidents.append(incident)

        return incidents

    def get_audit_history(self, limit: int = 10) -> List[FairnessAuditResult]:
        """
        Get recent audit history.

        Args:
            limit: Maximum audits to return

        Returns:
            List of recent audits
        """
        return list(reversed(self._audit_history[-limit:]))

    def get_fairness_trend(self, days: int = 90) -> List[Dict[str, Any]]:
        """
        Get fairness score trend over time.

        Args:
            days: Number of days to analyze

        Returns:
            List of (date, score) tuples
        """
        cutoff = datetime.now() - timedelta(days=days)

        trend = []
        for audit in self._audit_history:
            if audit.completed_at and audit.completed_at >= cutoff:
                trend.append({
                    'date': audit.completed_at.isoformat(),
                    'score': audit.overall_fairness_score,
                    'indicators': len(audit.bias_indicators)
                })

        return sorted(trend, key=lambda x: x['date'])

    def get_statistics(self) -> Dict[str, Any]:
        """Get auditor statistics."""
        if not self._audit_history:
            return {
                'total_audits': 0,
                'avg_fairness_score': None,
                'total_indicators': 0,
                'total_incidents_created': 0
            }

        scores = [a.overall_fairness_score for a in self._audit_history]
        indicators = sum(len(a.bias_indicators) for a in self._audit_history)
        incidents = sum(len(a.incidents_created) for a in self._audit_history)

        return {
            'total_audits': len(self._audit_history),
            'avg_fairness_score': sum(scores) / len(scores),
            'min_fairness_score': min(scores),
            'max_fairness_score': max(scores),
            'total_indicators': indicators,
            'total_incidents_created': incidents,
            'last_audit': self._audit_history[-1].completed_at.isoformat() if self._audit_history[-1].completed_at else None
        }


# Global instance
_fairness_auditor: Optional[FairnessAuditor] = None


def get_fairness_auditor() -> FairnessAuditor:
    """Get or create global fairness auditor instance."""
    global _fairness_auditor
    if _fairness_auditor is None:
        _fairness_auditor = FairnessAuditor()
    return _fairness_auditor
