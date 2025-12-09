#!/usr/bin/env python3
"""
Risk Scorer: Automated risk assessment and scoring engine.

Provides CVSS-like risk scoring for code, deployments, and system changes.
Supports EU AI Act risk categorization and ISO 27001 risk assessment.

EU AI Act Article 9: Risk management system.
ISO 27001 A.8: Asset management and risk assessment.
"""

import json
import math
import logging
from dataclasses import dataclass, asdict, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Callable
import hashlib

logger = logging.getLogger(__name__)


class RiskLevel(Enum):
    """Risk severity levels."""
    CRITICAL = "critical"  # 9.0-10.0
    HIGH = "high"          # 7.0-8.9
    MEDIUM = "medium"      # 4.0-6.9
    LOW = "low"            # 0.1-3.9
    NONE = "none"          # 0.0


class RiskCategory(Enum):
    """Risk categories aligned with EU AI Act."""
    UNACCEPTABLE = "unacceptable"  # Banned uses
    HIGH_RISK = "high_risk"         # Requires conformity assessment
    LIMITED_RISK = "limited_risk"   # Transparency obligations
    MINIMAL_RISK = "minimal_risk"   # No obligations


class RiskFactorType(Enum):
    """Types of risk factors."""
    SECURITY = "security"
    PRIVACY = "privacy"
    RELIABILITY = "reliability"
    COMPLIANCE = "compliance"
    OPERATIONAL = "operational"
    FINANCIAL = "financial"
    REPUTATIONAL = "reputational"


@dataclass
class RiskFactor:
    """A single risk factor in an assessment."""
    id: str
    name: str
    type: RiskFactorType
    description: str
    weight: float  # 0.0-1.0
    score: float   # 0.0-10.0
    evidence: Optional[str] = None
    mitigations: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def weighted_score(self) -> float:
        """Calculate weighted score."""
        return self.score * self.weight

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data['type'] = self.type.value
        data['weighted_score'] = self.weighted_score()
        return data


@dataclass
class RiskMitigation:
    """A risk mitigation action."""
    id: str
    risk_id: str
    action: str
    status: str  # proposed, in_progress, completed, rejected
    effectiveness: float  # 0.0-1.0 (expected risk reduction)
    owner: Optional[str] = None
    due_date: Optional[str] = None
    completed_at: Optional[str] = None
    notes: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class RiskAssessment:
    """Complete risk assessment for an entity."""
    id: str
    entity_type: str  # project, code, deployment, change
    entity_id: str
    entity_name: str
    timestamp: str
    overall_score: float
    risk_level: RiskLevel
    ai_risk_category: RiskCategory
    factors: List[RiskFactor]
    mitigations: List[RiskMitigation] = field(default_factory=list)
    residual_score: Optional[float] = None
    assessor: str = "automated"
    review_required: bool = False
    next_review: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data['risk_level'] = self.risk_level.value
        data['ai_risk_category'] = self.ai_risk_category.value
        data['factors'] = [f.to_dict() for f in self.factors]
        data['mitigations'] = [m.to_dict() for m in self.mitigations]
        return data


# Default risk factors configuration
DEFAULT_RISK_FACTORS = {
    "code_complexity": {
        "name": "Code Complexity",
        "type": RiskFactorType.RELIABILITY,
        "description": "High cyclomatic complexity increases bug risk",
        "weight": 0.15,
        "thresholds": {"low": 10, "medium": 20, "high": 40}
    },
    "security_vulnerabilities": {
        "name": "Security Vulnerabilities",
        "type": RiskFactorType.SECURITY,
        "description": "Known CVEs in dependencies",
        "weight": 0.25,
        "thresholds": {"low": 0, "medium": 3, "high": 10}
    },
    "data_sensitivity": {
        "name": "Data Sensitivity",
        "type": RiskFactorType.PRIVACY,
        "description": "PII/PHI data handling",
        "weight": 0.20,
        "thresholds": {"none": 0, "low": 1, "high": 3}
    },
    "test_coverage": {
        "name": "Test Coverage",
        "type": RiskFactorType.RELIABILITY,
        "description": "Code test coverage percentage",
        "weight": 0.10,
        "thresholds": {"high": 80, "medium": 50, "low": 20},
        "inverse": True  # Higher is better
    },
    "dependency_freshness": {
        "name": "Dependency Freshness",
        "type": RiskFactorType.SECURITY,
        "description": "Age of dependencies",
        "weight": 0.10,
        "thresholds": {"low": 90, "medium": 180, "high": 365}
    },
    "deployment_frequency": {
        "name": "Deployment Frequency",
        "type": RiskFactorType.OPERATIONAL,
        "description": "Changes per week",
        "weight": 0.10,
        "thresholds": {"low": 5, "medium": 15, "high": 30}
    },
    "ai_autonomy": {
        "name": "AI Autonomy Level",
        "type": RiskFactorType.COMPLIANCE,
        "description": "Level of autonomous AI decision-making",
        "weight": 0.10,
        "thresholds": {"low": 1, "medium": 3, "high": 5}
    }
}


class RiskScorer:
    """
    Automated risk scoring engine.

    Features:
    - Multi-factor risk assessment
    - CVSS-compatible scoring (0.0-10.0)
    - EU AI Act risk categorization
    - Mitigation tracking
    - Historical trend analysis
    """

    def __init__(
        self,
        storage_dir: Optional[str] = None,
        risk_factors: Optional[Dict[str, Dict]] = None,
        custom_scorers: Optional[Dict[str, Callable]] = None
    ):
        """
        Initialize risk scorer.

        Args:
            storage_dir: Directory for storing assessments
            risk_factors: Custom risk factor definitions
            custom_scorers: Custom scoring functions
        """
        self.storage_dir = Path(storage_dir) if storage_dir else \
            Path.home() / '.maestro' / 'risk_assessments'
        self.storage_dir.mkdir(parents=True, exist_ok=True)

        self.risk_factors = risk_factors or DEFAULT_RISK_FACTORS
        self.custom_scorers = custom_scorers or {}
        self._assessment_counter = 0

        logger.info(f"RiskScorer initialized: {self.storage_dir}")

    def assess(
        self,
        entity_type: str,
        entity_id: str,
        entity_name: str,
        factor_values: Dict[str, Any],
        ai_use_case: Optional[str] = None,
        **metadata
    ) -> RiskAssessment:
        """
        Perform risk assessment for an entity.

        Args:
            entity_type: Type of entity (project, code, deployment)
            entity_id: Unique identifier
            entity_name: Human-readable name
            factor_values: Values for each risk factor
            ai_use_case: AI use case for EU AI Act categorization
            **metadata: Additional metadata

        Returns:
            RiskAssessment with scores and recommendations
        """
        self._assessment_counter += 1
        assessment_id = f"RISK-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}-{self._assessment_counter:04d}"

        factors = []
        total_weight = 0.0
        weighted_sum = 0.0

        # Score each factor
        for factor_id, factor_config in self.risk_factors.items():
            if factor_id not in factor_values:
                continue

            value = factor_values[factor_id]
            score = self._score_factor(factor_id, value, factor_config)

            factor = RiskFactor(
                id=factor_id,
                name=factor_config['name'],
                type=factor_config['type'],
                description=factor_config['description'],
                weight=factor_config['weight'],
                score=score,
                evidence=f"Value: {value}",
                mitigations=self._suggest_mitigations(factor_id, score, factor_config)
            )

            factors.append(factor)
            weighted_sum += factor.weighted_score()
            total_weight += factor_config['weight']

        # Calculate overall score (normalized to 0-10)
        if total_weight > 0:
            overall_score = min(10.0, (weighted_sum / total_weight))
        else:
            overall_score = 0.0

        # Determine risk level
        risk_level = self._get_risk_level(overall_score)

        # Determine AI risk category
        ai_category = self._categorize_ai_risk(ai_use_case, overall_score, factor_values)

        # Check if review required
        review_required = (
            risk_level in (RiskLevel.CRITICAL, RiskLevel.HIGH) or
            ai_category in (RiskCategory.UNACCEPTABLE, RiskCategory.HIGH_RISK)
        )

        assessment = RiskAssessment(
            id=assessment_id,
            entity_type=entity_type,
            entity_id=entity_id,
            entity_name=entity_name,
            timestamp=datetime.utcnow().isoformat(),
            overall_score=round(overall_score, 2),
            risk_level=risk_level,
            ai_risk_category=ai_category,
            factors=factors,
            review_required=review_required,
            metadata=metadata
        )

        # Persist assessment
        self._save_assessment(assessment)

        logger.info(
            f"Risk assessment {assessment_id}: {entity_name} - "
            f"Score: {overall_score:.2f} ({risk_level.value})"
        )

        return assessment

    def _score_factor(
        self,
        factor_id: str,
        value: Any,
        config: Dict[str, Any]
    ) -> float:
        """Score a single risk factor."""
        # Check for custom scorer
        if factor_id in self.custom_scorers:
            return self.custom_scorers[factor_id](value, config)

        thresholds = config.get('thresholds', {})
        inverse = config.get('inverse', False)

        if isinstance(value, bool):
            return 0.0 if value == inverse else 10.0

        if isinstance(value, (int, float)):
            # Sort thresholds
            sorted_thresholds = sorted(
                [(name, thresh) for name, thresh in thresholds.items()],
                key=lambda x: x[1]
            )

            if inverse:
                # Higher value = lower risk
                if value >= sorted_thresholds[-1][1]:
                    return 0.0  # Best
                elif value <= sorted_thresholds[0][1]:
                    return 10.0  # Worst
                else:
                    # Interpolate
                    for i, (name, thresh) in enumerate(sorted_thresholds[:-1]):
                        next_thresh = sorted_thresholds[i + 1][1]
                        if thresh <= value < next_thresh:
                            progress = (value - thresh) / (next_thresh - thresh)
                            max_score = 10.0 - (i * 3.3)
                            min_score = 10.0 - ((i + 1) * 3.3)
                            return max_score - progress * (max_score - min_score)
            else:
                # Higher value = higher risk
                if value <= sorted_thresholds[0][1]:
                    return 0.0  # Best
                elif value >= sorted_thresholds[-1][1]:
                    return 10.0  # Worst
                else:
                    # Interpolate
                    for i, (name, thresh) in enumerate(sorted_thresholds[:-1]):
                        next_thresh = sorted_thresholds[i + 1][1]
                        if thresh < value <= next_thresh:
                            progress = (value - thresh) / (next_thresh - thresh)
                            min_score = i * 3.3
                            max_score = (i + 1) * 3.3
                            return min_score + progress * (max_score - min_score)

        return 5.0  # Default medium score

    def _get_risk_level(self, score: float) -> RiskLevel:
        """Determine risk level from score."""
        if score >= 9.0:
            return RiskLevel.CRITICAL
        elif score >= 7.0:
            return RiskLevel.HIGH
        elif score >= 4.0:
            return RiskLevel.MEDIUM
        elif score > 0.0:
            return RiskLevel.LOW
        else:
            return RiskLevel.NONE

    def _categorize_ai_risk(
        self,
        use_case: Optional[str],
        score: float,
        factors: Dict[str, Any]
    ) -> RiskCategory:
        """
        Categorize AI risk per EU AI Act.

        Unacceptable: Social scoring, real-time biometric identification
        High-Risk: Critical infrastructure, education, employment, law enforcement
        Limited Risk: Chatbots, emotion recognition
        Minimal Risk: Spam filters, content recommendations
        """
        # Check for unacceptable uses
        unacceptable_uses = [
            'social_scoring', 'real_time_biometric', 'subliminal_manipulation',
            'vulnerability_exploitation'
        ]
        if use_case and any(u in use_case.lower() for u in unacceptable_uses):
            return RiskCategory.UNACCEPTABLE

        # Check AI autonomy factor
        ai_autonomy = factors.get('ai_autonomy', 0)

        # High-risk uses
        high_risk_uses = [
            'critical_infrastructure', 'education', 'employment',
            'law_enforcement', 'border_control', 'justice',
            'democratic_process', 'biometric'
        ]
        if use_case and any(u in use_case.lower() for u in high_risk_uses):
            return RiskCategory.HIGH_RISK

        # Score-based categorization
        if score >= 8.0 or ai_autonomy >= 4:
            return RiskCategory.HIGH_RISK
        elif score >= 5.0 or ai_autonomy >= 2:
            return RiskCategory.LIMITED_RISK
        else:
            return RiskCategory.MINIMAL_RISK

    def _suggest_mitigations(
        self,
        factor_id: str,
        score: float,
        config: Dict[str, Any]
    ) -> List[str]:
        """Suggest mitigations based on factor score."""
        mitigations = []

        if score < 4.0:
            return mitigations  # Low risk, no mitigations needed

        if factor_id == 'code_complexity':
            mitigations.extend([
                "Refactor complex methods into smaller functions",
                "Add comprehensive unit tests for complex logic",
                "Consider code review for high-complexity modules"
            ])

        elif factor_id == 'security_vulnerabilities':
            mitigations.extend([
                "Update vulnerable dependencies immediately",
                "Run security scan and remediate findings",
                "Implement dependency auto-update policy"
            ])

        elif factor_id == 'data_sensitivity':
            mitigations.extend([
                "Implement data encryption at rest and in transit",
                "Add access controls and audit logging",
                "Review data retention policies"
            ])

        elif factor_id == 'test_coverage':
            mitigations.extend([
                "Increase unit test coverage to 80%+",
                "Add integration tests for critical paths",
                "Implement mutation testing"
            ])

        elif factor_id == 'ai_autonomy':
            mitigations.extend([
                "Add human-in-the-loop checkpoints",
                "Implement decision explanation logging",
                "Create override mechanisms"
            ])

        return mitigations[:3]  # Limit to top 3

    def add_mitigation(
        self,
        assessment_id: str,
        action: str,
        owner: Optional[str] = None,
        due_date: Optional[str] = None,
        effectiveness: float = 0.5
    ) -> Optional[RiskMitigation]:
        """Add a mitigation to an assessment."""
        assessment = self.get_assessment(assessment_id)
        if not assessment:
            return None

        mitigation_id = f"MIT-{hashlib.md5(action.encode()).hexdigest()[:8]}"

        mitigation = RiskMitigation(
            id=mitigation_id,
            risk_id=assessment_id,
            action=action,
            status="proposed",
            effectiveness=effectiveness,
            owner=owner,
            due_date=due_date
        )

        assessment.mitigations.append(mitigation)

        # Recalculate residual score
        total_reduction = sum(
            m.effectiveness for m in assessment.mitigations
            if m.status == 'completed'
        )
        assessment.residual_score = max(0, assessment.overall_score * (1 - total_reduction))

        self._save_assessment(assessment)

        return mitigation

    def get_assessment(self, assessment_id: str) -> Optional[RiskAssessment]:
        """Retrieve an assessment by ID."""
        file_path = self.storage_dir / f"{assessment_id}.json"
        if file_path.exists():
            with open(file_path, 'r') as f:
                data = json.load(f)
                return self._dict_to_assessment(data)
        return None

    def get_assessments(
        self,
        entity_type: Optional[str] = None,
        risk_level: Optional[RiskLevel] = None,
        limit: int = 100
    ) -> List[RiskAssessment]:
        """Get assessments with filters."""
        assessments = []

        for file_path in sorted(self.storage_dir.glob("RISK-*.json"), reverse=True):
            if len(assessments) >= limit:
                break

            try:
                with open(file_path, 'r') as f:
                    data = json.load(f)
                    assessment = self._dict_to_assessment(data)

                    if entity_type and assessment.entity_type != entity_type:
                        continue
                    if risk_level and assessment.risk_level != risk_level:
                        continue

                    assessments.append(assessment)
            except Exception as e:
                logger.error(f"Error loading {file_path}: {e}")

        return assessments

    def _save_assessment(self, assessment: RiskAssessment) -> None:
        """Save assessment to storage."""
        file_path = self.storage_dir / f"{assessment.id}.json"
        with open(file_path, 'w') as f:
            json.dump(assessment.to_dict(), f, indent=2)

    def _dict_to_assessment(self, data: Dict[str, Any]) -> RiskAssessment:
        """Convert dictionary to RiskAssessment."""
        data = dict(data)
        data['risk_level'] = RiskLevel(data['risk_level'])
        data['ai_risk_category'] = RiskCategory(data['ai_risk_category'])

        # Convert factors
        factors = []
        for f in data.get('factors', []):
            f['type'] = RiskFactorType(f['type'])
            factors.append(RiskFactor(**{k: v for k, v in f.items() if k != 'weighted_score'}))
        data['factors'] = factors

        # Convert mitigations
        mitigations = [RiskMitigation(**m) for m in data.get('mitigations', [])]
        data['mitigations'] = mitigations

        return RiskAssessment(**data)


def get_risk_scorer(**kwargs) -> RiskScorer:
    """Get risk scorer instance."""
    return RiskScorer(**kwargs)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    scorer = RiskScorer()

    # Example assessment
    assessment = scorer.assess(
        entity_type="project",
        entity_id="maestro-hive",
        entity_name="Maestro Hive Platform",
        factor_values={
            'code_complexity': 25,
            'security_vulnerabilities': 2,
            'data_sensitivity': 2,
            'test_coverage': 75,
            'ai_autonomy': 3
        },
        ai_use_case="code_generation"
    )

    print(json.dumps(assessment.to_dict(), indent=2))
