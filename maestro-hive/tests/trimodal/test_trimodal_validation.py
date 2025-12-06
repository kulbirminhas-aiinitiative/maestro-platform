"""
Trimodal Validation Integration Tests (MD-2026)

Tests for the DDE, BDV, and ACC validation system integration.
Verifies that all three components work together correctly.

Author: Claude Code Implementation
Date: 2025-12-01
"""

import pytest
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from bdv.integration_service import BDVIntegrationService
from acc.integration_service import ACCIntegrationService
from dde.verdict_aggregator import VerdictAggregator


class TestBDVIntegration:
    """Tests for BDV (Behavior-Driven Validation) component"""

    def test_bdv_validates_contracts_with_acceptance_criteria(self):
        """BDV should generate and run scenarios from contracts with acceptance criteria"""
        contracts = [
            {
                'id': 'test_contract_bdv_1',
                'name': 'Test Contract',
                'description': 'Test contract for validation',
                'acceptance_criteria': [
                    'User can authenticate',
                    'System validates input'
                ],
                'deliverables': ['auth.py']
            }
        ]

        bdv_service = BDVIntegrationService()
        result = bdv_service.validate_contracts(
            execution_id='test_bdv_001',
            contracts=contracts
        )

        assert result.total_contracts == 1
        # Should generate scenarios from acceptance criteria and deliverables
        assert result.total_scenarios > 0
        assert result.overall_pass_rate >= 0.0

    def test_bdv_handles_string_deliverables(self):
        """BDV should handle deliverables as simple strings (filenames)"""
        contracts = [
            {
                'id': 'test_contract_bdv_2',
                'name': 'String Deliverables Test',
                'description': 'Test with string deliverables',
                'acceptance_criteria': ['Feature works'],
                'deliverables': ['file1.py', 'file2.py', 'file3.py']
            }
        ]

        bdv_service = BDVIntegrationService()
        result = bdv_service.validate_contracts(
            execution_id='test_bdv_002',
            contracts=contracts
        )

        # Should not error on string deliverables
        assert result.total_contracts == 1
        assert result.scenarios_failed == 0  # No errors

    def test_bdv_handles_dict_deliverables(self):
        """BDV should handle deliverables as dictionaries with name and type"""
        contracts = [
            {
                'id': 'test_contract_bdv_3',
                'name': 'Dict Deliverables Test',
                'description': 'Test with dict deliverables',
                'acceptance_criteria': ['Feature works'],
                'deliverables': [
                    {'name': 'auth_module', 'type': 'module'},
                    {'name': 'config.json', 'type': 'config'}
                ]
            }
        ]

        bdv_service = BDVIntegrationService()
        result = bdv_service.validate_contracts(
            execution_id='test_bdv_003',
            contracts=contracts
        )

        assert result.total_contracts == 1
        assert result.scenarios_failed == 0  # No errors

    def test_bdv_empty_contracts_list(self):
        """BDV should handle empty contracts list gracefully"""
        bdv_service = BDVIntegrationService()
        result = bdv_service.validate_contracts(
            execution_id='test_bdv_004',
            contracts=[]
        )

        assert result.total_contracts == 0
        assert result.total_scenarios == 0


class TestACCIntegration:
    """Tests for ACC (Architectural Conformance Checking) component"""

    def test_acc_validates_python_codebase(self):
        """ACC should analyze Python codebase and return conformance score"""
        acc_service = ACCIntegrationService()

        # Use the bdv directory as a simple test codebase
        result = acc_service.validate_architecture(
            execution_id='test_acc_001',
            project_path=str(Path(__file__).parent.parent.parent / 'bdv')
        )

        assert result.is_compliant is not None
        assert 0.0 <= result.conformance_score <= 1.0
        assert result.rules_evaluated > 0

    def test_acc_handles_nonexistent_path(self):
        """ACC should handle non-existent paths gracefully"""
        acc_service = ACCIntegrationService()

        result = acc_service.validate_architecture(
            execution_id='test_acc_002',
            project_path='/nonexistent/path/to/project'
        )

        # Should return a result even for non-existent path
        assert result is not None

    def test_acc_returns_violation_summary(self):
        """ACC should return a violation summary object"""
        acc_service = ACCIntegrationService()

        result = acc_service.validate_architecture(
            execution_id='test_acc_003',
            project_path=str(Path(__file__).parent.parent.parent / 'acc')
        )

        assert hasattr(result.violations, 'total')
        assert hasattr(result.violations, 'blocking')
        assert result.violations.total >= 0


class TestVerdictAggregator:
    """Tests for Verdict Aggregator component"""

    def test_verdict_with_all_metrics(self):
        """Verdict aggregator should combine DDE, BDV, and ACC scores"""
        aggregator = VerdictAggregator()

        dde_metrics = {
            'avg_quality_score': 0.95,
            'contract_fulfillment_rate': 1.0,
            'error_rate': 0.0
        }
        bdv_metrics = {
            'total_contracts': 1,
            'contracts_fulfilled': 1,
            'overall_pass_rate': 1.0
        }
        acc_metrics = {
            'is_compliant': True,
            'conformance_score': 1.0,
            'total_violations': 0,
            'blocking_violations': 0
        }

        verdict = aggregator.generate_verdict(
            execution_id='test_verdict_001',
            dde_metrics=dde_metrics,
            bdv_metrics=bdv_metrics,
            acc_metrics=acc_metrics
        )

        assert verdict.grade is not None
        assert verdict.overall_score >= 0.0
        assert verdict.deployment_decision is not None

    def test_verdict_with_partial_metrics(self):
        """Verdict aggregator should handle partial metrics"""
        aggregator = VerdictAggregator()

        # Only DDE metrics
        verdict = aggregator.generate_verdict(
            execution_id='test_verdict_002',
            dde_metrics={'avg_quality_score': 0.8},
            bdv_metrics=None,
            acc_metrics=None
        )

        assert verdict.grade is not None

    def test_verdict_grades_correctly(self):
        """Verdict aggregator should assign grades correctly"""
        aggregator = VerdictAggregator()

        # Perfect scores
        perfect_verdict = aggregator.generate_verdict(
            execution_id='test_verdict_003',
            dde_metrics={'avg_quality_score': 1.0, 'contract_fulfillment_rate': 1.0, 'error_rate': 0.0}
        )

        # Low scores
        low_verdict = aggregator.generate_verdict(
            execution_id='test_verdict_004',
            dde_metrics={'avg_quality_score': 0.3, 'contract_fulfillment_rate': 0.2, 'error_rate': 0.5}
        )

        # Perfect should score higher than low
        assert perfect_verdict.overall_score > low_verdict.overall_score


class TestTrimodalEndToEnd:
    """End-to-end tests for the full Trimodal validation pipeline"""

    def test_full_trimodal_pipeline(self):
        """Test complete BDV -> ACC -> Verdict flow"""
        # 1. Run BDV validation
        bdv_service = BDVIntegrationService()
        bdv_result = bdv_service.validate_contracts(
            execution_id='test_e2e_001',
            contracts=[
                {
                    'id': 'e2e_contract',
                    'name': 'End-to-End Test Contract',
                    'description': 'Full pipeline test',
                    'acceptance_criteria': ['System initializes correctly'],
                    'deliverables': ['main.py']
                }
            ]
        )

        # 2. Run ACC validation
        acc_service = ACCIntegrationService()
        acc_result = acc_service.validate_architecture(
            execution_id='test_e2e_001',
            project_path=str(Path(__file__).parent.parent.parent / 'dde')
        )

        # 3. Generate verdict
        aggregator = VerdictAggregator()
        verdict = aggregator.generate_verdict(
            execution_id='test_e2e_001',
            dde_metrics={'avg_quality_score': 0.9, 'contract_fulfillment_rate': 1.0, 'error_rate': 0.0},
            bdv_metrics={
                'total_contracts': bdv_result.total_contracts,
                'contracts_fulfilled': bdv_result.contracts_fulfilled,
                'overall_pass_rate': bdv_result.overall_pass_rate
            },
            acc_metrics={
                'is_compliant': acc_result.is_compliant,
                'conformance_score': acc_result.conformance_score,
                'total_violations': acc_result.violations.total,
                'blocking_violations': acc_result.violations.blocking
            }
        )

        # Verify complete pipeline
        assert bdv_result.total_contracts == 1
        assert acc_result.conformance_score >= 0.0
        assert verdict.grade is not None
        assert verdict.deployment_decision is not None


class TestTrimodalScenarios:
    """MD-2026: End-to-end scenario tests for Trimodal validation"""

    def test_happy_path_all_pass_verdict_approved(self):
        """
        MD-2026 Test Case 1: Happy path with all validators passing
        Expected: APPROVED verdict with high score
        """
        aggregator = VerdictAggregator()

        # All validators pass with excellent scores
        verdict = aggregator.generate_verdict(
            execution_id='happy_path_001',
            dde_metrics={
                'avg_quality_score': 0.95,
                'contract_fulfillment_rate': 1.0,
                'error_rate': 0.02
            },
            bdv_metrics={
                'total_contracts': 5,
                'contracts_fulfilled': 5,
                'overall_pass_rate': 0.98,
                'bdv_pass_rate': 0.98,
                'scenarios_passed': 49,
                'scenarios_failed': 1
            },
            acc_metrics={
                'is_compliant': True,
                'acc_conformance_score': 0.95,
                'conformance_score': 0.95,
                'total_violations': 2,
                'blocking_violations': 0,
                'warning_violations': 2
            }
        )

        assert verdict.deployment_decision.value == 'approved'
        assert verdict.overall_score >= 0.80
        assert verdict.grade.value in ['A+', 'A']

    def test_bdv_failure_verdict_conditional(self):
        """
        MD-2026 Test Case 2: BDV scenarios fail, verdict CONDITIONAL
        Expected: CONDITIONAL or lower due to test failures
        """
        aggregator = VerdictAggregator()

        verdict = aggregator.generate_verdict(
            execution_id='bdv_fail_001',
            dde_metrics={
                'avg_quality_score': 0.85,
                'contract_fulfillment_rate': 0.80,
                'error_rate': 0.05
            },
            bdv_metrics={
                'total_contracts': 5,
                'contracts_fulfilled': 2,
                'overall_pass_rate': 0.50,
                'bdv_pass_rate': 0.50,
                'scenarios_passed': 10,
                'scenarios_failed': 10
            },
            acc_metrics={
                'is_compliant': True,
                'acc_conformance_score': 0.90,
                'conformance_score': 0.90,
                'total_violations': 1,
                'blocking_violations': 0,
                'warning_violations': 1
            }
        )

        # With 50% BDV pass rate, should not be approved
        assert verdict.deployment_decision.value in ['conditional', 'blocked']
        assert verdict.overall_score < 0.80

    def test_acc_failure_verdict_blocked(self):
        """
        MD-2026 Test Case 3: ACC violations detected, verdict BLOCKED
        Expected: BLOCKED due to architectural violations
        """
        aggregator = VerdictAggregator()

        verdict = aggregator.generate_verdict(
            execution_id='acc_fail_001',
            dde_metrics={
                'avg_quality_score': 0.95,
                'contract_fulfillment_rate': 1.0,
                'error_rate': 0.01
            },
            bdv_metrics={
                'total_contracts': 5,
                'contracts_fulfilled': 5,
                'overall_pass_rate': 0.95,
                'bdv_pass_rate': 0.95,
                'scenarios_passed': 19,
                'scenarios_failed': 1
            },
            acc_metrics={
                'is_compliant': False,
                'acc_conformance_score': 0.50,
                'conformance_score': 0.50,
                'total_violations': 5,
                'blocking_violations': 3,
                'warning_violations': 2
            }
        )

        # Blocking violations should result in BLOCKED
        assert verdict.deployment_decision.value == 'blocked'

    def test_dde_failure_verdict_adjusted(self):
        """
        MD-2026 Test Case 4: DDE low quality, verdict adjusted
        Expected: Lower grade due to poor DDE performance
        """
        aggregator = VerdictAggregator()

        verdict = aggregator.generate_verdict(
            execution_id='dde_fail_001',
            dde_metrics={
                'avg_quality_score': 0.40,
                'contract_fulfillment_rate': 0.30,
                'error_rate': 0.40
            },
            bdv_metrics={
                'total_contracts': 5,
                'contracts_fulfilled': 5,
                'overall_pass_rate': 0.90,
                'bdv_pass_rate': 0.90,
                'scenarios_passed': 18,
                'scenarios_failed': 2
            },
            acc_metrics={
                'is_compliant': True,
                'acc_conformance_score': 0.85,
                'conformance_score': 0.85,
                'total_violations': 2,
                'blocking_violations': 0,
                'warning_violations': 2
            }
        )

        # Low DDE score should pull overall score down
        assert verdict.overall_score < 0.80
        assert verdict.grade.value in ['B', 'C', 'D', 'F']

    def test_mixed_failures_multiple_issues(self):
        """
        MD-2026 Test Case 5: Multiple validators have issues
        Expected: BLOCKED with low score
        """
        aggregator = VerdictAggregator()

        verdict = aggregator.generate_verdict(
            execution_id='mixed_fail_001',
            dde_metrics={
                'avg_quality_score': 0.50,
                'contract_fulfillment_rate': 0.40,
                'error_rate': 0.30
            },
            bdv_metrics={
                'total_contracts': 5,
                'contracts_fulfilled': 1,
                'overall_pass_rate': 0.30,
                'bdv_pass_rate': 0.30,
                'scenarios_passed': 6,
                'scenarios_failed': 14
            },
            acc_metrics={
                'is_compliant': False,
                'acc_conformance_score': 0.40,
                'conformance_score': 0.40,
                'total_violations': 8,
                'blocking_violations': 2,
                'warning_violations': 6
            }
        )

        # Multiple failures should result in BLOCKED
        assert verdict.deployment_decision.value == 'blocked'
        assert verdict.overall_score < 0.60
        assert verdict.grade.value in ['D', 'F']


class TestCorrelationService:
    """MD-2023: Tests for DDE-BDV Correlation Service"""

    def test_correlation_service_records_dde_results(self):
        """Correlation service should record DDE fulfillment results"""
        from dde.correlation_service import get_correlation_service

        service = get_correlation_service()
        execution_id = 'corr_test_001'

        service.record_dde_result(
            execution_id=execution_id,
            contract_id='contract-001',
            contract_name='Test Contract',
            fulfilled=True,
            quality_score=0.92,
            deliverables=['auth.py', 'tests.py']
        )

        dde_status = service.get_dde_fulfillment_status(execution_id)
        assert 'contract-001' in dde_status
        assert dde_status['contract-001'] is True

    def test_correlation_service_correlates_results(self):
        """Correlation service should correlate DDE and BDV results"""
        from dde.correlation_service import get_correlation_service, CorrelationStatus

        service = get_correlation_service()
        execution_id = 'corr_test_002'

        # Record DDE result
        service.record_dde_result(
            execution_id=execution_id,
            contract_id='contract-002',
            contract_name='API Contract',
            fulfilled=True,
            quality_score=0.95
        )

        # Record matching BDV result (agreement)
        service.record_bdv_result(
            execution_id=execution_id,
            contract_id='contract-002',
            contract_name='API Contract',
            fulfilled=True,
            pass_rate=0.90,
            scenarios_passed=9,
            scenarios_failed=1
        )

        # Correlate
        result = service.correlate_results(execution_id)

        assert result.total_contracts == 1
        assert result.contracts_in_agreement == 1
        assert result.contracts_in_disagreement == 0

    def test_correlation_detects_disagreement(self):
        """Correlation service should detect when DDE and BDV disagree"""
        from dde.correlation_service import get_correlation_service, CorrelationStatus

        service = get_correlation_service()
        execution_id = 'corr_test_003'

        # DDE says fulfilled
        service.record_dde_result(
            execution_id=execution_id,
            contract_id='contract-003',
            contract_name='Disputed Contract',
            fulfilled=True,
            quality_score=0.80
        )

        # BDV says NOT fulfilled
        service.record_bdv_result(
            execution_id=execution_id,
            contract_id='contract-003',
            contract_name='Disputed Contract',
            fulfilled=False,
            pass_rate=0.40,
            scenarios_passed=4,
            scenarios_failed=6
        )

        # Correlate
        result = service.correlate_results(execution_id)

        assert result.contracts_in_disagreement == 1
        assert result.correlation_confidence < 1.0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
