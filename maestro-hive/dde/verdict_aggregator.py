"""
Tri-Modal Verdict Aggregator (MD-898)

Combines DDE, BDV, ACC results into unified quality verdict.
Foundation for quality gates and deployment decisions.

Features:
- Weight scores from each system
- Calculate overall quality grade
- Generate actionable recommendations
- Gate deployments based on thresholds

ML Integration Points:
- Quality prediction from multi-modal signals
- Optimal weight learning
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Any
from enum import Enum

logger = logging.getLogger(__name__)


class QualityGrade(str, Enum):
    """Quality grade levels"""
    A_PLUS = "A+"
    A = "A"
    B = "B"
    C = "C"
    D = "D"
    F = "F"


class DeploymentDecision(str, Enum):
    """Deployment gate decisions"""
    APPROVED = "approved"
    CONDITIONAL = "conditional"
    BLOCKED = "blocked"


@dataclass
class ModalScore:
    """Score from a single modal (DDE, BDV, or ACC)"""
    modal_name: str
    score: float
    weight: float
    weighted_score: float
    metrics: Dict[str, Any]
    is_available: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            'modal_name': self.modal_name,
            'score': round(self.score, 4),
            'weight': self.weight,
            'weighted_score': round(self.weighted_score, 4),
            'metrics': self.metrics,
            'is_available': self.is_available
        }


@dataclass
class QualityVerdict:
    """Unified quality verdict from tri-modal analysis"""
    execution_id: str
    overall_score: float
    grade: QualityGrade
    deployment_decision: DeploymentDecision
    modal_scores: List[ModalScore]
    strengths: List[str]
    weaknesses: List[str]
    recommendations: List[str]
    gate_results: Dict[str, bool]
    verdict_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'execution_id': self.execution_id,
            'overall_score': round(self.overall_score, 4),
            'grade': self.grade.value,
            'deployment_decision': self.deployment_decision.value,
            'modal_scores': [m.to_dict() for m in self.modal_scores],
            'strengths': self.strengths,
            'weaknesses': self.weaknesses,
            'recommendations': self.recommendations,
            'gate_results': self.gate_results,
            'verdict_at': self.verdict_at.isoformat()
        }


class VerdictAggregator:
    """
    Tri-Modal Verdict Aggregator

    Combines DDE, BDV, ACC results into unified quality assessment.
    """

    # Default weights (ML will optimize these)
    DEFAULT_WEIGHTS = {
        'dde': 0.35,  # Execution performance
        'bdv': 0.35,  # Behavioral validation
        'acc': 0.30   # Architectural conformance
    }

    # Grade thresholds
    GRADE_THRESHOLDS = {
        QualityGrade.A_PLUS: 0.95,
        QualityGrade.A: 0.90,
        QualityGrade.B: 0.80,
        QualityGrade.C: 0.70,
        QualityGrade.D: 0.60,
        QualityGrade.F: 0.0
    }

    # Deployment thresholds
    DEPLOYMENT_THRESHOLDS = {
        'approved': 0.80,      # Auto-approve above this
        'conditional': 0.60    # Conditional approval (manual review)
    }

    def __init__(self, weights: Optional[Dict[str, float]] = None):
        """
        Initialize verdict aggregator.

        Args:
            weights: Custom modal weights
        """
        self.weights = weights or self.DEFAULT_WEIGHTS.copy()

        # Normalize weights
        total = sum(self.weights.values())
        if total > 0:
            self.weights = {k: v / total for k, v in self.weights.items()}

        # Results storage
        self._verdicts: List[QualityVerdict] = []

        logger.info("✅ VerdictAggregator initialized")

    def generate_verdict(
        self,
        execution_id: str,
        dde_metrics: Optional[Dict[str, Any]] = None,
        bdv_metrics: Optional[Dict[str, Any]] = None,
        acc_metrics: Optional[Dict[str, Any]] = None
    ) -> QualityVerdict:
        """
        Generate unified quality verdict.

        Args:
            execution_id: Execution identifier
            dde_metrics: DDE performance metrics
            bdv_metrics: BDV validation metrics
            acc_metrics: ACC conformance metrics

        Returns:
            QualityVerdict with overall assessment
        """
        logger.info(f"🔍 Generating verdict for {execution_id}")

        # Calculate modal scores
        modal_scores = []

        # DDE Score
        dde_score = self._calculate_dde_score(dde_metrics)
        modal_scores.append(dde_score)

        # BDV Score
        bdv_score = self._calculate_bdv_score(bdv_metrics)
        modal_scores.append(bdv_score)

        # ACC Score
        acc_score = self._calculate_acc_score(acc_metrics)
        modal_scores.append(acc_score)

        # Calculate overall score
        overall_score = sum(m.weighted_score for m in modal_scores if m.is_available)

        # Normalize if not all modals available
        available_weight = sum(m.weight for m in modal_scores if m.is_available)
        if available_weight > 0 and available_weight < 1.0:
            overall_score = overall_score / available_weight

        # Determine grade
        grade = self._calculate_grade(overall_score)

        # Determine deployment decision
        deployment_decision = self._determine_deployment(
            overall_score,
            modal_scores,
            dde_metrics,
            bdv_metrics,
            acc_metrics
        )

        # Generate insights
        strengths = self._identify_strengths(modal_scores)
        weaknesses = self._identify_weaknesses(modal_scores)
        recommendations = self._generate_recommendations(
            modal_scores,
            dde_metrics,
            bdv_metrics,
            acc_metrics
        )

        # Check quality gates
        gate_results = self._check_quality_gates(
            modal_scores,
            dde_metrics,
            bdv_metrics,
            acc_metrics
        )

        verdict = QualityVerdict(
            execution_id=execution_id,
            overall_score=overall_score,
            grade=grade,
            deployment_decision=deployment_decision,
            modal_scores=modal_scores,
            strengths=strengths,
            weaknesses=weaknesses,
            recommendations=recommendations,
            gate_results=gate_results
        )

        # Store verdict
        self._verdicts.append(verdict)

        logger.info(f"✅ Verdict: {grade.value} (score: {overall_score:.2f}, "
                   f"decision: {deployment_decision.value})")

        return verdict

    def _calculate_dde_score(
        self,
        metrics: Optional[Dict[str, Any]]
    ) -> ModalScore:
        """Calculate DDE modal score."""
        if not metrics:
            return ModalScore(
                modal_name="DDE",
                score=0.0,
                weight=self.weights['dde'],
                weighted_score=0.0,
                metrics={},
                is_available=False
            )

        # Extract DDE metrics
        quality_score = metrics.get('avg_quality_score', 0.0)
        fulfillment_rate = metrics.get('contract_fulfillment_rate', 0.0)
        error_rate = metrics.get('error_rate', 0.0)

        # Calculate composite score
        score = (
            quality_score * 0.5 +
            fulfillment_rate * 0.3 +
            (1.0 - error_rate) * 0.2
        )

        return ModalScore(
            modal_name="DDE",
            score=score,
            weight=self.weights['dde'],
            weighted_score=score * self.weights['dde'],
            metrics=metrics
        )

    def _calculate_bdv_score(
        self,
        metrics: Optional[Dict[str, Any]]
    ) -> ModalScore:
        """Calculate BDV modal score."""
        if not metrics:
            return ModalScore(
                modal_name="BDV",
                score=0.0,
                weight=self.weights['bdv'],
                weighted_score=0.0,
                metrics={},
                is_available=False
            )

        # Extract BDV metrics
        pass_rate = metrics.get('bdv_pass_rate', 0.0)
        fulfillment_rate = metrics.get('fulfillment_rate', 0.0)

        # Calculate composite score
        score = (
            pass_rate * 0.6 +
            fulfillment_rate * 0.4
        )

        return ModalScore(
            modal_name="BDV",
            score=score,
            weight=self.weights['bdv'],
            weighted_score=score * self.weights['bdv'],
            metrics=metrics
        )

    def _calculate_acc_score(
        self,
        metrics: Optional[Dict[str, Any]]
    ) -> ModalScore:
        """Calculate ACC modal score."""
        if not metrics:
            return ModalScore(
                modal_name="ACC",
                score=0.0,
                weight=self.weights['acc'],
                weighted_score=0.0,
                metrics={},
                is_available=False
            )

        # Extract ACC metrics
        conformance_score = metrics.get('acc_conformance_score', 0.0)
        is_compliant = metrics.get('is_compliant', False)

        # Calculate composite score
        score = conformance_score
        if is_compliant:
            score = min(1.0, score + 0.05)  # Small bonus for compliance

        return ModalScore(
            modal_name="ACC",
            score=score,
            weight=self.weights['acc'],
            weighted_score=score * self.weights['acc'],
            metrics=metrics
        )

    def _calculate_grade(self, score: float) -> QualityGrade:
        """Calculate letter grade from score."""
        for grade, threshold in self.GRADE_THRESHOLDS.items():
            if score >= threshold:
                return grade
        return QualityGrade.F

    def _determine_deployment(
        self,
        overall_score: float,
        modal_scores: List[ModalScore],
        dde_metrics: Optional[Dict[str, Any]],
        bdv_metrics: Optional[Dict[str, Any]],
        acc_metrics: Optional[Dict[str, Any]]
    ) -> DeploymentDecision:
        """Determine deployment decision."""
        # Check for blocking conditions
        if acc_metrics:
            if acc_metrics.get('blocking_violations', 0) > 0:
                return DeploymentDecision.BLOCKED
            if not acc_metrics.get('is_compliant', True):
                return DeploymentDecision.BLOCKED

        if bdv_metrics:
            if bdv_metrics.get('scenarios_failed', 0) > 0:
                # Failed tests - conditional or blocked based on severity
                pass_rate = bdv_metrics.get('bdv_pass_rate', 0.0)
                if pass_rate < 0.5:
                    return DeploymentDecision.BLOCKED

        # Score-based decision
        if overall_score >= self.DEPLOYMENT_THRESHOLDS['approved']:
            return DeploymentDecision.APPROVED
        elif overall_score >= self.DEPLOYMENT_THRESHOLDS['conditional']:
            return DeploymentDecision.CONDITIONAL
        else:
            return DeploymentDecision.BLOCKED

    def _identify_strengths(self, modal_scores: List[ModalScore]) -> List[str]:
        """Identify strengths from modal scores."""
        strengths = []

        for modal in modal_scores:
            if not modal.is_available:
                continue

            if modal.score >= 0.90:
                strengths.append(f"Excellent {modal.modal_name} performance ({modal.score:.1%})")
            elif modal.score >= 0.80:
                strengths.append(f"Strong {modal.modal_name} results ({modal.score:.1%})")

        return strengths

    def _identify_weaknesses(self, modal_scores: List[ModalScore]) -> List[str]:
        """Identify weaknesses from modal scores."""
        weaknesses = []

        for modal in sorted(modal_scores, key=lambda x: x.score):
            if not modal.is_available:
                weaknesses.append(f"{modal.modal_name} validation not available")
                continue

            if modal.score < 0.60:
                weaknesses.append(f"Poor {modal.modal_name} performance ({modal.score:.1%})")
            elif modal.score < 0.70:
                weaknesses.append(f"Below average {modal.modal_name} ({modal.score:.1%})")

        return weaknesses[:3]  # Top 3 weaknesses

    def _generate_recommendations(
        self,
        modal_scores: List[ModalScore],
        dde_metrics: Optional[Dict[str, Any]],
        bdv_metrics: Optional[Dict[str, Any]],
        acc_metrics: Optional[Dict[str, Any]]
    ) -> List[str]:
        """Generate actionable recommendations."""
        recommendations = []

        # DDE recommendations
        dde_modal = next((m for m in modal_scores if m.modal_name == "DDE"), None)
        if dde_modal and dde_modal.is_available and dde_modal.score < 0.80:
            if dde_metrics:
                if dde_metrics.get('error_rate', 0) > 0.1:
                    recommendations.append("Reduce error rate by improving error handling")
                if dde_metrics.get('avg_quality_score', 1.0) < 0.85:
                    recommendations.append("Improve code quality through better prompts")

        # BDV recommendations
        bdv_modal = next((m for m in modal_scores if m.modal_name == "BDV"), None)
        if bdv_modal and bdv_modal.is_available and bdv_modal.score < 0.80:
            if bdv_metrics:
                if bdv_metrics.get('scenarios_failed', 0) > 0:
                    recommendations.append("Fix failing test scenarios")
                if bdv_metrics.get('fulfillment_rate', 1.0) < 0.90:
                    recommendations.append("Review contracts for completeness")

        # ACC recommendations
        acc_modal = next((m for m in modal_scores if m.modal_name == "ACC"), None)
        if acc_modal and acc_modal.is_available and acc_modal.score < 0.80:
            if acc_metrics:
                if acc_metrics.get('blocking_violations', 0) > 0:
                    recommendations.append("Resolve blocking architectural violations")
                if acc_metrics.get('cycles_detected', 0) > 0:
                    recommendations.append("Break cyclic dependencies")
                if acc_metrics.get('warning_violations', 0) > 3:
                    recommendations.append("Address architectural warnings")

        # General recommendations
        if not recommendations:
            if all(m.score >= 0.90 for m in modal_scores if m.is_available):
                recommendations.append("Excellent quality - consider this for best practices")
            else:
                recommendations.append("Continue monitoring quality metrics")

        return recommendations[:5]

    def _check_quality_gates(
        self,
        modal_scores: List[ModalScore],
        dde_metrics: Optional[Dict[str, Any]],
        bdv_metrics: Optional[Dict[str, Any]],
        acc_metrics: Optional[Dict[str, Any]]
    ) -> Dict[str, bool]:
        """Check quality gates."""
        gates = {}

        # Gate 1: Minimum overall score
        overall = sum(m.weighted_score for m in modal_scores if m.is_available)
        gates['min_overall_score'] = overall >= 0.60

        # Gate 2: No blocking violations
        gates['no_blocking_violations'] = True
        if acc_metrics:
            gates['no_blocking_violations'] = acc_metrics.get('blocking_violations', 0) == 0

        # Gate 3: Test pass rate
        gates['test_pass_rate'] = True
        if bdv_metrics:
            gates['test_pass_rate'] = bdv_metrics.get('bdv_pass_rate', 0.0) >= 0.70

        # Gate 4: Contract fulfillment
        gates['contract_fulfillment'] = True
        if dde_metrics:
            gates['contract_fulfillment'] = dde_metrics.get('contract_fulfillment_rate', 0.0) >= 0.80

        # Gate 5: Architectural compliance
        gates['architectural_compliance'] = True
        if acc_metrics:
            gates['architectural_compliance'] = acc_metrics.get('is_compliant', True)

        return gates

    def update_weights(self, new_weights: Dict[str, float]):
        """
        Update modal weights (for ML optimization).

        Args:
            new_weights: New weight values
        """
        for key in new_weights:
            if key in self.weights:
                self.weights[key] = new_weights[key]

        # Normalize
        total = sum(self.weights.values())
        if total > 0:
            self.weights = {k: v / total for k, v in self.weights.items()}

        logger.info(f"Updated weights: {self.weights}")

    def get_verdict_history(
        self,
        limit: int = 10
    ) -> List[QualityVerdict]:
        """Get recent verdicts."""
        return list(reversed(self._verdicts[-limit:]))

    def get_ml_training_data(self) -> List[Dict[str, Any]]:
        """
        Get verdict data formatted for ML training.

        Returns:
            List of feature dictionaries for ML
        """
        training_data = []

        for verdict in self._verdicts:
            record = {
                'execution_id': verdict.execution_id,
                'overall_score': verdict.overall_score,
                'grade': verdict.grade.value,
                'deployment_decision': verdict.deployment_decision.value,
                'timestamp': verdict.verdict_at.isoformat()
            }

            # Add modal scores
            for modal in verdict.modal_scores:
                record[f'{modal.modal_name.lower()}_score'] = modal.score
                record[f'{modal.modal_name.lower()}_available'] = 1 if modal.is_available else 0

            # Add gate results
            for gate, result in verdict.gate_results.items():
                record[f'gate_{gate}'] = 1 if result else 0

            training_data.append(record)

        return training_data


# Global instance
_aggregator: Optional[VerdictAggregator] = None


def get_verdict_aggregator() -> VerdictAggregator:
    """Get or create global verdict aggregator instance."""
    global _aggregator
    if _aggregator is None:
        _aggregator = VerdictAggregator()
    return _aggregator


# Example usage
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    # Initialize aggregator
    aggregator = get_verdict_aggregator()

    # Sample metrics
    dde_metrics = {
        'avg_quality_score': 0.92,
        'contract_fulfillment_rate': 0.95,
        'error_rate': 0.05
    }

    bdv_metrics = {
        'bdv_pass_rate': 0.88,
        'fulfillment_rate': 0.90,
        'scenarios_passed': 22,
        'scenarios_failed': 3
    }

    acc_metrics = {
        'acc_conformance_score': 0.85,
        'is_compliant': True,
        'blocking_violations': 0,
        'warning_violations': 2,
        'cycles_detected': 0
    }

    # Generate verdict
    verdict = aggregator.generate_verdict(
        execution_id="exec-001",
        dde_metrics=dde_metrics,
        bdv_metrics=bdv_metrics,
        acc_metrics=acc_metrics
    )

    print("\n=== Quality Verdict ===")
    print(f"Overall Score: {verdict.overall_score:.2f}")
    print(f"Grade: {verdict.grade.value}")
    print(f"Deployment: {verdict.deployment_decision.value}")

    print("\nModal Scores:")
    for modal in verdict.modal_scores:
        status = "✅" if modal.is_available else "❌"
        print(f"  {status} {modal.modal_name}: {modal.score:.2f} (weight: {modal.weight:.0%})")

    print(f"\nStrengths: {verdict.strengths}")
    print(f"Weaknesses: {verdict.weaknesses}")
    print(f"Recommendations: {verdict.recommendations}")

    print("\nQuality Gates:")
    for gate, passed in verdict.gate_results.items():
        status = "✅" if passed else "❌"
        print(f"  {status} {gate}")
