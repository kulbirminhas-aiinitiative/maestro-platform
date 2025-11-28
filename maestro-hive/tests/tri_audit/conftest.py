"""
Pytest fixtures for Tri-Modal Audit tests.

Provides sample audit results for testing verdict determination
and integration scenarios.
"""

import pytest
from typing import Dict, Any


@pytest.fixture
def sample_dde_audit_result() -> Dict[str, Any]:
    """Sample DDE audit result with all checks passing."""
    return {
        "iteration_id": "test-iter-001",
        "passed": True,
        "score": 0.95,
        "all_nodes_complete": True,
        "blocking_gates_passed": True,
        "artifacts_stamped": True,
        "lineage_intact": True,
        "contracts_locked": True,
        "details": {
            "total_nodes": 10,
            "completed_nodes": 10,
            "failed_nodes": 0,
            "execution_time_seconds": 120
        }
    }


@pytest.fixture
def sample_bdv_audit_result() -> Dict[str, Any]:
    """Sample BDV audit result with all scenarios passing."""
    return {
        "iteration_id": "test-iter-001",
        "passed": True,
        "total_scenarios": 25,
        "passed_scenarios": 25,
        "failed_scenarios": 0,
        "flake_rate": 0.04,
        "contract_mismatches": [],
        "critical_journeys_covered": True,
        "details": {
            "features_tested": 8,
            "coverage_percentage": 92.5,
            "execution_time_seconds": 180
        }
    }


@pytest.fixture
def sample_acc_audit_result() -> Dict[str, Any]:
    """Sample ACC audit result with no blocking violations."""
    return {
        "iteration_id": "test-iter-001",
        "passed": True,
        "blocking_violations": 0,
        "warning_violations": 2,
        "cycles": [],
        "coupling_scores": {
            "auth_service": {"billing_service": 0.15},
            "billing_service": {"notification_service": 0.20}
        },
        "suppressions_have_adrs": True,
        "coupling_within_limits": True,
        "no_new_cycles": True,
        "details": {
            "components_analyzed": 15,
            "total_dependencies": 42,
            "instability_score": 0.35
        }
    }


@pytest.fixture
def failing_dde_audit_result() -> Dict[str, Any]:
    """Sample DDE audit result with failures."""
    return {
        "iteration_id": "test-iter-002",
        "passed": False,
        "score": 0.65,
        "all_nodes_complete": False,
        "blocking_gates_passed": False,
        "artifacts_stamped": True,
        "lineage_intact": True,
        "contracts_locked": False,
        "details": {
            "total_nodes": 10,
            "completed_nodes": 7,
            "failed_nodes": 3,
            "execution_time_seconds": 85
        }
    }


@pytest.fixture
def failing_bdv_audit_result() -> Dict[str, Any]:
    """Sample BDV audit result with failing scenarios."""
    return {
        "iteration_id": "test-iter-002",
        "passed": False,
        "total_scenarios": 25,
        "passed_scenarios": 20,
        "failed_scenarios": 5,
        "flake_rate": 0.12,
        "contract_mismatches": ["AuthAPI.v1.2", "PaymentAPI.v2.0"],
        "critical_journeys_covered": False,
        "details": {
            "features_tested": 8,
            "coverage_percentage": 78.3,
            "execution_time_seconds": 210
        }
    }


@pytest.fixture
def failing_acc_audit_result() -> Dict[str, Any]:
    """Sample ACC audit result with blocking violations."""
    return {
        "iteration_id": "test-iter-002",
        "passed": False,
        "blocking_violations": 3,
        "warning_violations": 8,
        "cycles": [
            ["ModuleA", "ModuleB", "ModuleA"],
            ["ServiceX", "ServiceY", "ServiceZ", "ServiceX"]
        ],
        "coupling_scores": {
            "auth_service": {"billing_service": 0.85},  # Too high
            "billing_service": {"notification_service": 0.45}
        },
        "suppressions_have_adrs": False,
        "coupling_within_limits": False,
        "no_new_cycles": False,
        "details": {
            "components_analyzed": 15,
            "total_dependencies": 58,
            "instability_score": 0.72
        }
    }


@pytest.fixture
def systemic_failure_results(
    failing_dde_audit_result,
    failing_bdv_audit_result,
    failing_acc_audit_result
) -> Dict[str, Dict[str, Any]]:
    """Sample audit results where all three streams fail."""
    return {
        "dde": failing_dde_audit_result,
        "bdv": failing_bdv_audit_result,
        "acc": failing_acc_audit_result
    }


@pytest.fixture
def all_pass_results(
    sample_dde_audit_result,
    sample_bdv_audit_result,
    sample_acc_audit_result
) -> Dict[str, Dict[str, Any]]:
    """Sample audit results where all three streams pass."""
    return {
        "dde": sample_dde_audit_result,
        "bdv": sample_bdv_audit_result,
        "acc": sample_acc_audit_result
    }


@pytest.fixture
def design_gap_results(
    sample_dde_audit_result,
    failing_bdv_audit_result,
    sample_acc_audit_result
) -> Dict[str, Dict[str, Any]]:
    """Sample audit results indicating design gap (BDV fails)."""
    return {
        "dde": sample_dde_audit_result,
        "bdv": failing_bdv_audit_result,
        "acc": sample_acc_audit_result
    }


@pytest.fixture
def arch_erosion_results(
    sample_dde_audit_result,
    sample_bdv_audit_result,
    failing_acc_audit_result
) -> Dict[str, Dict[str, Any]]:
    """Sample audit results indicating architectural erosion (ACC fails)."""
    return {
        "dde": sample_dde_audit_result,
        "bdv": sample_bdv_audit_result,
        "acc": failing_acc_audit_result
    }


@pytest.fixture
def process_issue_results(
    failing_dde_audit_result,
    sample_bdv_audit_result,
    sample_acc_audit_result
) -> Dict[str, Dict[str, Any]]:
    """Sample audit results indicating process issue (DDE fails)."""
    return {
        "dde": failing_dde_audit_result,
        "bdv": sample_bdv_audit_result,
        "acc": sample_acc_audit_result
    }
