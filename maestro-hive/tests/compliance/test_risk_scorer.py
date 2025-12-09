#!/usr/bin/env python3
"""Tests for risk_scorer module."""

import pytest
import tempfile
from datetime import datetime

from maestro_hive.compliance.risk_scorer import (
    RiskScorer,
    RiskLevel,
    RiskCategory,
    RiskAssessment,
    RiskFactor,
    get_risk_scorer
)


class TestRiskScorer:
    """Tests for RiskScorer class."""

    def test_scorer_initialization(self):
        """Test scorer initializes correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            scorer = RiskScorer(storage_dir=tmpdir)
            assert scorer.storage_dir.exists()

    def test_assess_low_risk(self):
        """Test assessing low risk scenario."""
        with tempfile.TemporaryDirectory() as tmpdir:
            scorer = RiskScorer(storage_dir=tmpdir)

            assessment = scorer.assess(
                resource='simple-script.py',
                category=RiskCategory.OPERATIONAL,
                factors=[
                    RiskFactor(
                        name='complexity',
                        value=2,
                        weight=1.0,
                        description='Low complexity script'
                    )
                ]
            )

            assert assessment.resource == 'simple-script.py'
            assert assessment.category == RiskCategory.OPERATIONAL
            assert assessment.risk_level == RiskLevel.LOW
            assert assessment.score < 4.0

    def test_assess_high_risk(self):
        """Test assessing high risk scenario."""
        with tempfile.TemporaryDirectory() as tmpdir:
            scorer = RiskScorer(storage_dir=tmpdir)

            assessment = scorer.assess(
                resource='payment-processor',
                category=RiskCategory.FINANCIAL,
                factors=[
                    RiskFactor(name='data_sensitivity', value=10, weight=2.0, description='PII/Financial'),
                    RiskFactor(name='regulatory_impact', value=9, weight=1.5, description='GDPR/PCI'),
                    RiskFactor(name='availability_requirement', value=10, weight=1.0, description='24/7')
                ]
            )

            assert assessment.risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL]
            assert assessment.score > 6.0

    def test_assess_critical_risk(self):
        """Test assessing critical risk scenario."""
        with tempfile.TemporaryDirectory() as tmpdir:
            scorer = RiskScorer(storage_dir=tmpdir)

            assessment = scorer.assess(
                resource='ai-autonomous-system',
                category=RiskCategory.EU_AI_ACT,
                factors=[
                    RiskFactor(name='autonomy_level', value=10, weight=2.0, description='Fully autonomous'),
                    RiskFactor(name='human_impact', value=10, weight=2.0, description='Critical decisions'),
                    RiskFactor(name='reversibility', value=10, weight=1.5, description='Irreversible actions')
                ]
            )

            assert assessment.risk_level == RiskLevel.CRITICAL
            assert assessment.score >= 9.0

    def test_risk_categories(self):
        """Test all risk categories can be assessed."""
        with tempfile.TemporaryDirectory() as tmpdir:
            scorer = RiskScorer(storage_dir=tmpdir)

            categories = [
                RiskCategory.OPERATIONAL,
                RiskCategory.SECURITY,
                RiskCategory.COMPLIANCE,
                RiskCategory.FINANCIAL,
                RiskCategory.REPUTATIONAL,
                RiskCategory.EU_AI_ACT
            ]

            for category in categories:
                assessment = scorer.assess(
                    resource=f'test-{category.value}',
                    category=category,
                    factors=[RiskFactor(name='test', value=5, weight=1.0, description='Test')]
                )
                assert assessment.category == category

    def test_score_boundaries(self):
        """Test risk level boundaries."""
        with tempfile.TemporaryDirectory() as tmpdir:
            scorer = RiskScorer(storage_dir=tmpdir)

            # Low: 0-3.9
            low = scorer.assess(
                resource='r1',
                category=RiskCategory.OPERATIONAL,
                factors=[RiskFactor(name='f', value=2, weight=1.0, description='')]
            )
            assert low.risk_level == RiskLevel.LOW

            # Medium: 4.0-6.9
            medium = scorer.assess(
                resource='r2',
                category=RiskCategory.OPERATIONAL,
                factors=[RiskFactor(name='f', value=5, weight=1.0, description='')]
            )
            assert medium.risk_level == RiskLevel.MEDIUM

            # High: 7.0-8.9
            high = scorer.assess(
                resource='r3',
                category=RiskCategory.OPERATIONAL,
                factors=[RiskFactor(name='f', value=8, weight=1.0, description='')]
            )
            assert high.risk_level == RiskLevel.HIGH

            # Critical: 9.0-10.0
            critical = scorer.assess(
                resource='r4',
                category=RiskCategory.OPERATIONAL,
                factors=[RiskFactor(name='f', value=10, weight=1.0, description='')]
            )
            assert critical.risk_level == RiskLevel.CRITICAL

    def test_query_assessments(self):
        """Test querying assessments."""
        with tempfile.TemporaryDirectory() as tmpdir:
            scorer = RiskScorer(storage_dir=tmpdir)

            # Create assessments
            scorer.assess(
                resource='resource-1',
                category=RiskCategory.SECURITY,
                factors=[RiskFactor(name='f', value=8, weight=1.0, description='')]
            )
            scorer.assess(
                resource='resource-2',
                category=RiskCategory.FINANCIAL,
                factors=[RiskFactor(name='f', value=5, weight=1.0, description='')]
            )
            scorer.assess(
                resource='resource-3',
                category=RiskCategory.SECURITY,
                factors=[RiskFactor(name='f', value=3, weight=1.0, description='')]
            )

            # Query by category
            security_risks = scorer.query(category=RiskCategory.SECURITY)
            assert len(security_risks) == 2

            # Query by level
            high_risks = scorer.query(risk_level=RiskLevel.HIGH)
            assert len(high_risks) == 1

    def test_get_risk_summary(self):
        """Test getting risk summary."""
        with tempfile.TemporaryDirectory() as tmpdir:
            scorer = RiskScorer(storage_dir=tmpdir)

            scorer.assess(
                resource='r1',
                category=RiskCategory.OPERATIONAL,
                factors=[RiskFactor(name='f', value=3, weight=1.0, description='')]
            )
            scorer.assess(
                resource='r2',
                category=RiskCategory.SECURITY,
                factors=[RiskFactor(name='f', value=8, weight=1.0, description='')]
            )

            summary = scorer.get_summary()
            assert 'total_assessments' in summary
            assert 'by_level' in summary
            assert 'by_category' in summary
            assert summary['total_assessments'] == 2

    def test_get_risk_scorer_factory(self):
        """Test factory function."""
        scorer = get_risk_scorer()
        assert isinstance(scorer, RiskScorer)


class TestRiskFactor:
    """Tests for RiskFactor dataclass."""

    def test_risk_factor_creation(self):
        """Test risk factor creation."""
        factor = RiskFactor(
            name='data_sensitivity',
            value=8,
            weight=1.5,
            description='Contains PII data'
        )
        assert factor.name == 'data_sensitivity'
        assert factor.value == 8
        assert factor.weight == 1.5

    def test_risk_factor_to_dict(self):
        """Test risk factor serialization."""
        factor = RiskFactor(
            name='complexity',
            value=7,
            weight=1.0,
            description='High cyclomatic complexity'
        )
        data = factor.to_dict()
        assert data['name'] == 'complexity'
        assert data['value'] == 7

    def test_risk_factor_value_bounds(self):
        """Test risk factor value is within bounds."""
        # Values should be 0-10
        factor = RiskFactor(name='test', value=5, weight=1.0, description='')
        assert 0 <= factor.value <= 10


class TestRiskAssessment:
    """Tests for RiskAssessment dataclass."""

    def test_assessment_creation(self):
        """Test assessment creation."""
        assessment = RiskAssessment(
            id='RISK-001',
            resource='payment-api',
            category=RiskCategory.FINANCIAL,
            factors=[],
            score=7.5,
            risk_level=RiskLevel.HIGH,
            timestamp='2024-01-01T00:00:00'
        )
        assert assessment.id == 'RISK-001'
        assert assessment.risk_level == RiskLevel.HIGH

    def test_assessment_to_dict(self):
        """Test assessment serialization."""
        assessment = RiskAssessment(
            id='RISK-002',
            resource='auth-service',
            category=RiskCategory.SECURITY,
            factors=[
                RiskFactor(name='vulnerability', value=6, weight=1.0, description='')
            ],
            score=6.0,
            risk_level=RiskLevel.MEDIUM,
            timestamp='2024-01-01T00:00:00'
        )
        data = assessment.to_dict()
        assert data['id'] == 'RISK-002'
        assert data['resource'] == 'auth-service'
        assert len(data['factors']) == 1
