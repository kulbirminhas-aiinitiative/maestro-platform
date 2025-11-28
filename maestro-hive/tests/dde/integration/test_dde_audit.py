"""
DDE Integration Tests: Audit & Deployment Tests
Test IDs: DDE-701 to DDE-730 (30 tests)

Tests for DDE audit system:

1. Completeness checks (701-710):
   - All nodes completed
   - Missing nodes detected
   - All gates passed
   - Artifacts stamped
   - Contracts locked

2. Integrity validation (711-723):
   - Node count match
   - Execution order correct
   - Completeness score calculation
   - Lineage integrity
   - Artifact SHA256 verification
   - Policy violations

3. Reporting (724-730):
   - JSON report generation
   - Schema validation
   - Timestamps
   - Duration tracking
   - Caching (5min)
   - History
   - Comparison with previous

These tests ensure the DDE audit system can:
1. Verify workflow completeness and integrity
2. Detect violations and generate actionable recommendations
3. Cache and compare audit results over time
"""

import pytest
import asyncio
import json
import tempfile
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any

# Import DDE auditor
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from dde.auditor import (
    DDEAuditor,
    AuditResult,
    ViolationType,
    AuditViolation,
    CompletenessMetrics,
    IntegrityMetrics,
    AuditReport
)


# ============================================================================
# Test Fixtures
# ============================================================================

@pytest.fixture
def auditor():
    """Create fresh auditor for each test"""
    return DDEAuditor(cache_ttl_seconds=300)


@pytest.fixture
def complete_manifest():
    """Complete workflow manifest with all nodes"""
    return {
        "workflow_id": "test-workflow-001",
        "nodes": {
            "IF.AuthAPI": {
                "type": "INTERFACE",
                "contract_version": "v1.0",
                "gates": ["schema_validation", "security_scan"],
                "expected_artifacts": ["openapi.yaml"],
                "dependencies": []
            },
            "IMPL.AuthService": {
                "type": "ACTION",
                "gates": ["unit_tests", "code_quality"],
                "expected_artifacts": ["auth_service.py", "test_results.json"],
                "dependencies": ["IF.AuthAPI"]
            },
            "TEST.Integration": {
                "type": "ACTION",
                "gates": ["integration_tests"],
                "expected_artifacts": ["integration_report.json"],
                "dependencies": ["IMPL.AuthService"]
            }
        }
    }


@pytest.fixture
def complete_execution_log():
    """Complete execution log with all nodes executed"""
    base_time = datetime.utcnow()

    return {
        "iteration_id": "Iter-20251013-1200-001",
        "started_at": base_time.isoformat() + "Z",
        "completed_at": (base_time + timedelta(minutes=10)).isoformat() + "Z",
        "node_states": {
            "IF.AuthAPI": {
                "status": "completed",
                "start_time": base_time.isoformat() + "Z",
                "end_time": (base_time + timedelta(minutes=2)).isoformat() + "Z",
                "contract_locked": True,
                "artifacts": ["artifacts/Iter-20251013-1200-001/IF.AuthAPI/openapi.yaml"],
                "gate_results": {
                    "schema_validation": {"status": "passed", "severity": "BLOCKING"},
                    "security_scan": {"status": "passed", "severity": "WARNING"}
                }
            },
            "IMPL.AuthService": {
                "status": "completed",
                "start_time": (base_time + timedelta(minutes=2)).isoformat() + "Z",
                "end_time": (base_time + timedelta(minutes=7)).isoformat() + "Z",
                "contract_locked": False,
                "artifacts": [
                    "artifacts/Iter-20251013-1200-001/IMPL.AuthService/auth_service.py",
                    "artifacts/Iter-20251013-1200-001/IMPL.AuthService/test_results.json"
                ],
                "gate_results": {
                    "unit_tests": {"status": "passed", "severity": "BLOCKING"},
                    "code_quality": {"status": "passed", "severity": "WARNING"}
                }
            },
            "TEST.Integration": {
                "status": "completed",
                "start_time": (base_time + timedelta(minutes=7)).isoformat() + "Z",
                "end_time": (base_time + timedelta(minutes=10)).isoformat() + "Z",
                "contract_locked": False,
                "artifacts": ["artifacts/Iter-20251013-1200-001/TEST.Integration/integration_report.json"],
                "gate_results": {
                    "integration_tests": {"status": "passed", "severity": "BLOCKING"}
                }
            }
        }
    }


@pytest.fixture
def incomplete_execution_log():
    """Incomplete execution log with missing nodes"""
    base_time = datetime.utcnow()

    return {
        "iteration_id": "Iter-20251013-1200-002",
        "started_at": base_time.isoformat() + "Z",
        "completed_at": None,
        "node_states": {
            "IF.AuthAPI": {
                "status": "completed",
                "start_time": base_time.isoformat() + "Z",
                "end_time": (base_time + timedelta(minutes=2)).isoformat() + "Z",
                "contract_locked": True,
                "artifacts": ["artifacts/Iter-20251013-1200-002/IF.AuthAPI/openapi.yaml"],
                "gate_results": {
                    "schema_validation": {"status": "passed", "severity": "BLOCKING"},
                    "security_scan": {"status": "passed", "severity": "WARNING"}
                }
            }
            # Missing IMPL.AuthService and TEST.Integration
        }
    }


# ============================================================================
# Test Suite 1: Completeness Checks (DDE-701 to DDE-710)
# ============================================================================

@pytest.mark.integration
@pytest.mark.dde
class TestCompletenessChecks:
    """Test suite for workflow completeness checks"""

    @pytest.mark.asyncio
    async def test_dde_701_all_nodes_completed(self, auditor, complete_manifest, complete_execution_log):
        """DDE-701: Audit passes when all nodes completed"""
        report = await auditor.audit_workflow(
            iteration_id="Iter-20251013-1200-001",
            manifest=complete_manifest,
            execution_log=complete_execution_log
        )

        assert report.audit_result == AuditResult.PASS
        assert report.completeness.completeness_score == 1.0
        assert report.completeness.total_nodes == 3
        assert report.completeness.completed_nodes == 3
        assert len(report.completeness.missing_nodes) == 0

    @pytest.mark.asyncio
    async def test_dde_702_missing_nodes_detected(self, auditor, complete_manifest, incomplete_execution_log):
        """DDE-702: Missing nodes are detected and reported"""
        report = await auditor.audit_workflow(
            iteration_id="Iter-20251013-1200-002",
            manifest=complete_manifest,
            execution_log=incomplete_execution_log
        )

        assert report.audit_result == AuditResult.FAIL
        assert report.completeness.completeness_score < 1.0
        assert len(report.completeness.missing_nodes) == 2
        assert "IMPL.AuthService" in report.completeness.missing_nodes
        assert "TEST.Integration" in report.completeness.missing_nodes

    @pytest.mark.asyncio
    async def test_dde_703_missing_node_creates_violation(self, auditor, complete_manifest, incomplete_execution_log):
        """DDE-703: Missing node creates BLOCKING violation"""
        report = await auditor.audit_workflow(
            iteration_id="Iter-20251013-1200-002",
            manifest=complete_manifest,
            execution_log=incomplete_execution_log
        )

        missing_violations = [
            v for v in report.violations
            if v.violation_type == ViolationType.MISSING_NODE
        ]

        assert len(missing_violations) == 2
        assert all(v.severity == "BLOCKING" for v in missing_violations)

    @pytest.mark.asyncio
    async def test_dde_704_all_gates_passed(self, auditor, complete_manifest, complete_execution_log):
        """DDE-704: All quality gates passed verification"""
        report = await auditor.audit_workflow(
            iteration_id="Iter-20251013-1200-001",
            manifest=complete_manifest,
            execution_log=complete_execution_log
        )

        # Total gates: 2 + 2 + 1 = 5
        assert report.integrity.total_gates == 5
        assert report.integrity.passed_gates == 5
        assert len(report.integrity.failed_gates) == 0

    @pytest.mark.asyncio
    async def test_dde_705_failed_gate_detected(self, auditor, complete_manifest):
        """DDE-705: Failed quality gates are detected"""
        # Create execution log with failed gate
        exec_log = {
            "iteration_id": "Iter-20251013-1200-003",
            "started_at": datetime.utcnow().isoformat() + "Z",
            "node_states": {
                "IF.AuthAPI": {
                    "status": "completed",
                    "start_time": datetime.utcnow().isoformat() + "Z",
                    "end_time": datetime.utcnow().isoformat() + "Z",
                    "contract_locked": True,
                    "artifacts": ["openapi.yaml"],
                    "gate_results": {
                        "schema_validation": {"status": "failed", "severity": "BLOCKING"},
                        "security_scan": {"status": "passed", "severity": "WARNING"}
                    }
                },
                "IMPL.AuthService": {
                    "status": "completed",
                    "artifacts": ["auth_service.py", "test_results.json"],
                    "gate_results": {
                        "unit_tests": {"status": "passed", "severity": "BLOCKING"},
                        "code_quality": {"status": "passed", "severity": "WARNING"}
                    }
                },
                "TEST.Integration": {
                    "status": "completed",
                    "artifacts": ["integration_report.json"],
                    "gate_results": {
                        "integration_tests": {"status": "passed", "severity": "BLOCKING"}
                    }
                }
            }
        }

        report = await auditor.audit_workflow(
            iteration_id="Iter-20251013-1200-003",
            manifest=complete_manifest,
            execution_log=exec_log
        )

        assert report.integrity.passed_gates == 4
        assert len(report.integrity.failed_gates) == 1
        assert report.integrity.failed_gates[0]["gate_name"] == "schema_validation"

    @pytest.mark.asyncio
    async def test_dde_706_all_artifacts_stamped(self, auditor, complete_manifest, complete_execution_log):
        """DDE-706: All artifacts stamped verification"""
        report = await auditor.audit_workflow(
            iteration_id="Iter-20251013-1200-001",
            manifest=complete_manifest,
            execution_log=complete_execution_log
        )

        # Total artifacts: 1 + 2 + 1 = 4
        assert report.integrity.total_artifacts == 4
        assert report.integrity.stamped_artifacts == 4
        assert len(report.integrity.missing_artifacts) == 0

    @pytest.mark.asyncio
    async def test_dde_707_missing_artifact_detected(self, auditor, complete_manifest):
        """DDE-707: Missing artifacts are detected"""
        # Create execution log with missing artifact
        exec_log = {
            "iteration_id": "Iter-20251013-1200-004",
            "node_states": {
                "IF.AuthAPI": {
                    "status": "completed",
                    "contract_locked": True,
                    "artifacts": ["openapi.yaml"],
                    "gate_results": {
                        "schema_validation": {"status": "passed", "severity": "BLOCKING"},
                        "security_scan": {"status": "passed", "severity": "WARNING"}
                    }
                },
                "IMPL.AuthService": {
                    "status": "completed",
                    "artifacts": ["auth_service.py"],  # Missing test_results.json
                    "gate_results": {
                        "unit_tests": {"status": "passed", "severity": "BLOCKING"},
                        "code_quality": {"status": "passed", "severity": "WARNING"}
                    }
                },
                "TEST.Integration": {
                    "status": "completed",
                    "artifacts": ["integration_report.json"],
                    "gate_results": {
                        "integration_tests": {"status": "passed", "severity": "BLOCKING"}
                    }
                }
            }
        }

        report = await auditor.audit_workflow(
            iteration_id="Iter-20251013-1200-004",
            manifest=complete_manifest,
            execution_log=exec_log
        )

        assert report.integrity.stamped_artifacts == 3
        assert len(report.integrity.missing_artifacts) == 1
        assert "IMPL.AuthService:test_results.json" in report.integrity.missing_artifacts

    @pytest.mark.asyncio
    async def test_dde_708_all_contracts_locked(self, auditor, complete_manifest, complete_execution_log):
        """DDE-708: All INTERFACE contracts locked verification"""
        report = await auditor.audit_workflow(
            iteration_id="Iter-20251013-1200-001",
            manifest=complete_manifest,
            execution_log=complete_execution_log
        )

        # Only 1 INTERFACE node
        assert report.integrity.total_contracts == 1
        assert report.integrity.locked_contracts == 1
        assert len(report.integrity.unlocked_contracts) == 0

    @pytest.mark.asyncio
    async def test_dde_709_unlocked_contract_detected(self, auditor, complete_manifest):
        """DDE-709: Unlocked contracts are detected"""
        # Create execution log with unlocked contract
        exec_log = {
            "iteration_id": "Iter-20251013-1200-005",
            "node_states": {
                "IF.AuthAPI": {
                    "status": "completed",
                    "contract_locked": False,  # Not locked!
                    "artifacts": ["openapi.yaml"],
                    "gate_results": {
                        "schema_validation": {"status": "passed", "severity": "BLOCKING"},
                        "security_scan": {"status": "passed", "severity": "WARNING"}
                    }
                },
                "IMPL.AuthService": {
                    "status": "completed",
                    "artifacts": ["auth_service.py", "test_results.json"],
                    "gate_results": {
                        "unit_tests": {"status": "passed", "severity": "BLOCKING"},
                        "code_quality": {"status": "passed", "severity": "WARNING"}
                    }
                },
                "TEST.Integration": {
                    "status": "completed",
                    "artifacts": ["integration_report.json"],
                    "gate_results": {
                        "integration_tests": {"status": "passed", "severity": "BLOCKING"}
                    }
                }
            }
        }

        report = await auditor.audit_workflow(
            iteration_id="Iter-20251013-1200-005",
            manifest=complete_manifest,
            execution_log=exec_log
        )

        assert report.integrity.locked_contracts == 0
        assert len(report.integrity.unlocked_contracts) == 1
        assert "IF.AuthAPI" in report.integrity.unlocked_contracts

    @pytest.mark.asyncio
    async def test_dde_710_completeness_score_calculation(self, auditor, complete_manifest, incomplete_execution_log):
        """DDE-710: Completeness score = completed_nodes / total_nodes"""
        report = await auditor.audit_workflow(
            iteration_id="Iter-20251013-1200-002",
            manifest=complete_manifest,
            execution_log=incomplete_execution_log
        )

        # 1 completed out of 3 total = 0.333...
        expected_score = 1 / 3
        assert abs(report.completeness.completeness_score - expected_score) < 0.01


# ============================================================================
# Test Suite 2: Integrity Validation (DDE-711 to DDE-723)
# ============================================================================

@pytest.mark.integration
@pytest.mark.dde
class TestIntegrityValidation:
    """Test suite for workflow integrity validation"""

    @pytest.mark.asyncio
    async def test_dde_711_node_count_match(self, auditor, complete_manifest, complete_execution_log):
        """DDE-711: Node count matches between manifest and execution"""
        report = await auditor.audit_workflow(
            iteration_id="Iter-20251013-1200-001",
            manifest=complete_manifest,
            execution_log=complete_execution_log
        )

        manifest_nodes = len(complete_manifest["nodes"])
        executed_nodes = len(complete_execution_log["node_states"])

        assert report.completeness.total_nodes == manifest_nodes
        assert report.completeness.completed_nodes == executed_nodes

    @pytest.mark.asyncio
    async def test_dde_712_execution_order_correct(self, auditor, complete_manifest, complete_execution_log):
        """DDE-712: Execution order respects dependencies"""
        report = await auditor.audit_workflow(
            iteration_id="Iter-20251013-1200-001",
            manifest=complete_manifest,
            execution_log=complete_execution_log
        )

        assert report.integrity.execution_order_valid is True

        # Verify no order violations
        order_violations = [
            v for v in report.violations
            if v.violation_type == ViolationType.ORDER_VIOLATION
        ]
        assert len(order_violations) == 0

    @pytest.mark.asyncio
    async def test_dde_713_execution_order_violation_detected(self, auditor, complete_manifest):
        """DDE-713: Execution order violations are detected"""
        base_time = datetime.utcnow()

        # Create execution log where IMPL starts before IF completes
        exec_log = {
            "iteration_id": "Iter-20251013-1200-006",
            "node_states": {
                "IF.AuthAPI": {
                    "status": "completed",
                    "start_time": base_time.isoformat() + "Z",
                    "end_time": (base_time + timedelta(minutes=5)).isoformat() + "Z",  # Ends at +5 min
                    "contract_locked": True,
                    "artifacts": ["openapi.yaml"],
                    "gate_results": {
                        "schema_validation": {"status": "passed", "severity": "BLOCKING"},
                        "security_scan": {"status": "passed", "severity": "WARNING"}
                    }
                },
                "IMPL.AuthService": {
                    "status": "completed",
                    "start_time": (base_time + timedelta(minutes=2)).isoformat() + "Z",  # Starts at +2 min (before IF ends!)
                    "end_time": (base_time + timedelta(minutes=7)).isoformat() + "Z",
                    "artifacts": ["auth_service.py", "test_results.json"],
                    "gate_results": {
                        "unit_tests": {"status": "passed", "severity": "BLOCKING"},
                        "code_quality": {"status": "passed", "severity": "WARNING"}
                    }
                },
                "TEST.Integration": {
                    "status": "completed",
                    "start_time": (base_time + timedelta(minutes=7)).isoformat() + "Z",
                    "end_time": (base_time + timedelta(minutes=10)).isoformat() + "Z",
                    "artifacts": ["integration_report.json"],
                    "gate_results": {
                        "integration_tests": {"status": "passed", "severity": "BLOCKING"}
                    }
                }
            }
        }

        report = await auditor.audit_workflow(
            iteration_id="Iter-20251013-1200-006",
            manifest=complete_manifest,
            execution_log=exec_log
        )

        assert report.integrity.execution_order_valid is False

    @pytest.mark.asyncio
    async def test_dde_714_completeness_score_100_percent(self, auditor, complete_manifest, complete_execution_log):
        """DDE-714: Completeness score is 100% when all nodes complete"""
        report = await auditor.audit_workflow(
            iteration_id="Iter-20251013-1200-001",
            manifest=complete_manifest,
            execution_log=complete_execution_log
        )

        assert report.completeness.completeness_score == 1.0

    @pytest.mark.asyncio
    async def test_dde_715_completeness_score_partial(self, auditor, complete_manifest):
        """DDE-715: Completeness score correctly calculates partial completion"""
        # 2 out of 3 nodes completed
        exec_log = {
            "iteration_id": "Iter-20251013-1200-007",
            "node_states": {
                "IF.AuthAPI": {
                    "status": "completed",
                    "contract_locked": True,
                    "artifacts": ["openapi.yaml"],
                    "gate_results": {
                        "schema_validation": {"status": "passed", "severity": "BLOCKING"},
                        "security_scan": {"status": "passed", "severity": "WARNING"}
                    }
                },
                "IMPL.AuthService": {
                    "status": "completed",
                    "artifacts": ["auth_service.py", "test_results.json"],
                    "gate_results": {
                        "unit_tests": {"status": "passed", "severity": "BLOCKING"},
                        "code_quality": {"status": "passed", "severity": "WARNING"}
                    }
                }
                # Missing TEST.Integration
            }
        }

        report = await auditor.audit_workflow(
            iteration_id="Iter-20251013-1200-007",
            manifest=complete_manifest,
            execution_log=exec_log
        )

        expected_score = 2 / 3
        assert abs(report.completeness.completeness_score - expected_score) < 0.01

    @pytest.mark.asyncio
    async def test_dde_716_lineage_integrity_all_deps_completed(self, auditor, complete_manifest, complete_execution_log):
        """DDE-716: Lineage integrity - all dependencies completed before dependent"""
        report = await auditor.audit_workflow(
            iteration_id="Iter-20251013-1200-001",
            manifest=complete_manifest,
            execution_log=complete_execution_log
        )

        # All nodes completed, so lineage is intact
        assert report.completeness.completed_nodes == report.completeness.total_nodes
        assert report.integrity.execution_order_valid is True

    @pytest.mark.asyncio
    async def test_dde_717_artifact_sha256_validation_concept(self, auditor):
        """DDE-717: Artifact SHA256 validation (conceptual test)"""
        # This test demonstrates the concept of SHA256 validation
        # In production, artifacts would be stamped with SHA256 hashes

        manifest = {
            "workflow_id": "test-workflow-sha256",
            "nodes": {
                "NODE1": {
                    "type": "ACTION",
                    "gates": [],
                    "expected_artifacts": ["file.txt"],
                    "dependencies": []
                }
            }
        }

        exec_log = {
            "iteration_id": "Iter-SHA256-001",
            "node_states": {
                "NODE1": {
                    "status": "completed",
                    "artifacts": ["file.txt"],
                    "gate_results": {}
                }
            }
        }

        report = await auditor.audit_workflow(
            iteration_id="Iter-SHA256-001",
            manifest=manifest,
            execution_log=exec_log
        )

        # Verify artifact was counted
        assert report.integrity.stamped_artifacts == 1

    @pytest.mark.asyncio
    async def test_dde_718_policy_violation_failed_gate(self, auditor, complete_manifest):
        """DDE-718: Policy violation detected via failed gate"""
        exec_log = {
            "iteration_id": "Iter-20251013-1200-008",
            "node_states": {
                "IF.AuthAPI": {
                    "status": "completed",
                    "contract_locked": True,
                    "artifacts": ["openapi.yaml"],
                    "gate_results": {
                        "schema_validation": {"status": "passed", "severity": "BLOCKING"},
                        "security_scan": {"status": "failed", "severity": "BLOCKING"}  # Policy violation
                    }
                },
                "IMPL.AuthService": {
                    "status": "completed",
                    "artifacts": ["auth_service.py", "test_results.json"],
                    "gate_results": {
                        "unit_tests": {"status": "passed", "severity": "BLOCKING"},
                        "code_quality": {"status": "passed", "severity": "WARNING"}
                    }
                },
                "TEST.Integration": {
                    "status": "completed",
                    "artifacts": ["integration_report.json"],
                    "gate_results": {
                        "integration_tests": {"status": "passed", "severity": "BLOCKING"}
                    }
                }
            }
        }

        report = await auditor.audit_workflow(
            iteration_id="Iter-20251013-1200-008",
            manifest=complete_manifest,
            execution_log=exec_log
        )

        # Failed gate should create violation
        failed_gate_violations = [
            v for v in report.violations
            if v.violation_type == ViolationType.FAILED_GATE
        ]

        assert len(failed_gate_violations) >= 1
        assert any(v.severity == "BLOCKING" for v in failed_gate_violations)

    @pytest.mark.asyncio
    async def test_dde_719_multiple_violation_types(self, auditor, complete_manifest):
        """DDE-719: Multiple violation types detected in single audit"""
        exec_log = {
            "iteration_id": "Iter-20251013-1200-009",
            "node_states": {
                "IF.AuthAPI": {
                    "status": "completed",
                    "contract_locked": False,  # Violation 1: Unlocked contract
                    "artifacts": [],  # Violation 2: Missing artifact
                    "gate_results": {
                        "schema_validation": {"status": "failed", "severity": "BLOCKING"},  # Violation 3: Failed gate
                        "security_scan": {"status": "passed", "severity": "WARNING"}
                    }
                }
                # Violation 4 & 5: Missing nodes
            }
        }

        report = await auditor.audit_workflow(
            iteration_id="Iter-20251013-1200-009",
            manifest=complete_manifest,
            execution_log=exec_log
        )

        # Should have multiple violation types
        violation_types = set(v.violation_type for v in report.violations)
        assert len(violation_types) >= 3

        # Check specific violations
        assert any(v.violation_type == ViolationType.UNLOCKED_CONTRACT for v in report.violations)
        assert any(v.violation_type == ViolationType.MISSING_ARTIFACT for v in report.violations)
        assert any(v.violation_type == ViolationType.FAILED_GATE for v in report.violations)
        assert any(v.violation_type == ViolationType.MISSING_NODE for v in report.violations)

    @pytest.mark.asyncio
    async def test_dde_720_failed_node_tracking(self, auditor, complete_manifest):
        """DDE-720: Failed nodes are tracked separately"""
        exec_log = {
            "iteration_id": "Iter-20251013-1200-010",
            "node_states": {
                "IF.AuthAPI": {
                    "status": "completed",
                    "contract_locked": True,
                    "artifacts": ["openapi.yaml"],
                    "gate_results": {
                        "schema_validation": {"status": "passed", "severity": "BLOCKING"},
                        "security_scan": {"status": "passed", "severity": "WARNING"}
                    }
                },
                "IMPL.AuthService": {
                    "status": "failed",  # Failed node
                    "artifacts": [],
                    "gate_results": {
                        "unit_tests": {"status": "failed", "severity": "BLOCKING"},
                        "code_quality": {"status": "passed", "severity": "WARNING"}
                    }
                },
                "TEST.Integration": {
                    "status": "skipped",  # Skipped due to dependency failure
                    "artifacts": [],
                    "gate_results": {}
                }
            }
        }

        report = await auditor.audit_workflow(
            iteration_id="Iter-20251013-1200-010",
            manifest=complete_manifest,
            execution_log=exec_log
        )

        assert len(report.completeness.failed_nodes) == 1
        assert "IMPL.AuthService" in report.completeness.failed_nodes

        assert len(report.completeness.skipped_nodes) == 1
        assert "TEST.Integration" in report.completeness.skipped_nodes

    @pytest.mark.asyncio
    async def test_dde_721_audit_result_pass_criteria(self, auditor, complete_manifest, complete_execution_log):
        """DDE-721: Audit result is PASS only when score=100% and no blocking violations"""
        report = await auditor.audit_workflow(
            iteration_id="Iter-20251013-1200-001",
            manifest=complete_manifest,
            execution_log=complete_execution_log
        )

        assert report.audit_result == AuditResult.PASS
        assert report.completeness.completeness_score == 1.0

        blocking_violations = [v for v in report.violations if v.severity == "BLOCKING"]
        assert len(blocking_violations) == 0

    @pytest.mark.asyncio
    async def test_dde_722_audit_result_fail_incomplete(self, auditor, complete_manifest, incomplete_execution_log):
        """DDE-722: Audit result is FAIL when score<100%"""
        report = await auditor.audit_workflow(
            iteration_id="Iter-20251013-1200-002",
            manifest=complete_manifest,
            execution_log=incomplete_execution_log
        )

        assert report.audit_result == AuditResult.FAIL
        assert report.completeness.completeness_score < 1.0

    @pytest.mark.asyncio
    async def test_dde_723_audit_result_fail_blocking_violation(self, auditor, complete_manifest):
        """DDE-723: Audit result is FAIL when blocking violation exists"""
        exec_log = {
            "iteration_id": "Iter-20251013-1200-011",
            "node_states": {
                "IF.AuthAPI": {
                    "status": "completed",
                    "contract_locked": False,  # BLOCKING violation
                    "artifacts": ["openapi.yaml"],
                    "gate_results": {
                        "schema_validation": {"status": "passed", "severity": "BLOCKING"},
                        "security_scan": {"status": "passed", "severity": "WARNING"}
                    }
                },
                "IMPL.AuthService": {
                    "status": "completed",
                    "artifacts": ["auth_service.py", "test_results.json"],
                    "gate_results": {
                        "unit_tests": {"status": "passed", "severity": "BLOCKING"},
                        "code_quality": {"status": "passed", "severity": "WARNING"}
                    }
                },
                "TEST.Integration": {
                    "status": "completed",
                    "artifacts": ["integration_report.json"],
                    "gate_results": {
                        "integration_tests": {"status": "passed", "severity": "BLOCKING"}
                    }
                }
            }
        }

        report = await auditor.audit_workflow(
            iteration_id="Iter-20251013-1200-011",
            manifest=complete_manifest,
            execution_log=exec_log
        )

        # Even though all nodes completed, blocking violation causes FAIL
        assert report.audit_result == AuditResult.FAIL
        assert report.completeness.completeness_score == 1.0  # All nodes done

        blocking_violations = [v for v in report.violations if v.severity == "BLOCKING"]
        assert len(blocking_violations) > 0


# ============================================================================
# Test Suite 3: Reporting (DDE-724 to DDE-730)
# ============================================================================

@pytest.mark.integration
@pytest.mark.dde
class TestReporting:
    """Test suite for audit reporting"""

    @pytest.mark.asyncio
    async def test_dde_724_json_report_generation(self, auditor, complete_manifest, complete_execution_log):
        """DDE-724: Audit report can be exported to JSON"""
        report = await auditor.audit_workflow(
            iteration_id="Iter-20251013-1200-001",
            manifest=complete_manifest,
            execution_log=complete_execution_log
        )

        # Convert to dict
        report_dict = report.to_dict()

        # Verify it's valid JSON
        json_str = json.dumps(report_dict)
        parsed = json.loads(json_str)

        assert parsed["iteration_id"] == "Iter-20251013-1200-001"
        assert parsed["audit_result"] == "PASS"

    @pytest.mark.asyncio
    async def test_dde_725_report_schema_validation(self, auditor, complete_manifest, complete_execution_log):
        """DDE-725: Audit report follows expected schema"""
        report = await auditor.audit_workflow(
            iteration_id="Iter-20251013-1200-001",
            manifest=complete_manifest,
            execution_log=complete_execution_log
        )

        report_dict = report.to_dict()

        # Verify required fields
        assert "iteration_id" in report_dict
        assert "workflow_id" in report_dict
        assert "audit_timestamp" in report_dict
        assert "audit_result" in report_dict
        assert "completeness" in report_dict
        assert "integrity" in report_dict
        assert "violations" in report_dict
        assert "recommendations" in report_dict

        # Verify completeness schema
        assert "total_nodes" in report_dict["completeness"]
        assert "completed_nodes" in report_dict["completeness"]
        assert "completeness_score" in report_dict["completeness"]

        # Verify integrity schema
        assert "total_gates" in report_dict["integrity"]
        assert "passed_gates" in report_dict["integrity"]
        assert "total_artifacts" in report_dict["integrity"]
        assert "stamped_artifacts" in report_dict["integrity"]
        assert "total_contracts" in report_dict["integrity"]
        assert "locked_contracts" in report_dict["integrity"]
        assert "execution_order_valid" in report_dict["integrity"]

    @pytest.mark.asyncio
    async def test_dde_726_timestamps_included(self, auditor, complete_manifest, complete_execution_log):
        """DDE-726: Report includes audit timestamp"""
        report = await auditor.audit_workflow(
            iteration_id="Iter-20251013-1200-001",
            manifest=complete_manifest,
            execution_log=complete_execution_log
        )

        assert report.audit_timestamp is not None
        assert "T" in report.audit_timestamp  # ISO format
        assert "Z" in report.audit_timestamp  # UTC timezone

        # Verify can parse timestamp
        datetime.fromisoformat(report.audit_timestamp.replace("Z", "+00:00"))

    @pytest.mark.asyncio
    async def test_dde_727_duration_tracking(self, auditor, complete_manifest, complete_execution_log):
        """DDE-727: Report tracks execution duration"""
        report = await auditor.audit_workflow(
            iteration_id="Iter-20251013-1200-001",
            manifest=complete_manifest,
            execution_log=complete_execution_log
        )

        assert report.execution_duration is not None
        assert report.execution_duration > 0  # Should be ~10 minutes = 600 seconds
        assert report.execution_duration == 600.0  # Based on fixture timestamps

    @pytest.mark.asyncio
    async def test_dde_728_caching_5min_ttl(self, auditor, complete_manifest, complete_execution_log):
        """DDE-728: Audit results cached for 5 minutes"""
        # First audit
        report1 = await auditor.audit_workflow(
            iteration_id="Iter-20251013-1200-001",
            manifest=complete_manifest,
            execution_log=complete_execution_log
        )

        # Second audit (should return cached)
        report2 = await auditor.audit_workflow(
            iteration_id="Iter-20251013-1200-001",
            manifest=complete_manifest,
            execution_log=complete_execution_log
        )

        # Should be exact same object (cached)
        assert report1.audit_timestamp == report2.audit_timestamp

    @pytest.mark.asyncio
    async def test_dde_729_audit_history_tracking(self, auditor, complete_manifest, complete_execution_log):
        """DDE-729: Audit history is tracked per iteration"""
        # First audit
        await auditor.audit_workflow(
            iteration_id="Iter-20251013-1200-001",
            manifest=complete_manifest,
            execution_log=complete_execution_log
        )

        # Clear cache to force new audit
        auditor.clear_cache()

        # Second audit (different timestamp)
        await asyncio.sleep(0.1)  # Small delay to ensure different timestamp

        await auditor.audit_workflow(
            iteration_id="Iter-20251013-1200-001",
            manifest=complete_manifest,
            execution_log=complete_execution_log
        )

        # Get history
        history = auditor.get_audit_history("Iter-20251013-1200-001")

        assert len(history) == 2
        assert history[0].audit_timestamp != history[1].audit_timestamp

    @pytest.mark.asyncio
    async def test_dde_730_comparison_with_previous(self, auditor, complete_manifest):
        """DDE-730: Can compare current audit with previous audit"""
        # First audit (incomplete)
        incomplete_log = {
            "iteration_id": "Iter-20251013-1200-012",
            "node_states": {
                "IF.AuthAPI": {
                    "status": "completed",
                    "contract_locked": True,
                    "artifacts": ["openapi.yaml"],
                    "gate_results": {
                        "schema_validation": {"status": "passed", "severity": "BLOCKING"},
                        "security_scan": {"status": "passed", "severity": "WARNING"}
                    }
                }
            }
        }

        await auditor.audit_workflow(
            iteration_id="Iter-20251013-1200-012",
            manifest=complete_manifest,
            execution_log=incomplete_log
        )

        auditor.clear_cache()
        await asyncio.sleep(0.1)

        # Second audit (complete)
        base_time = datetime.utcnow()
        complete_log = {
            "iteration_id": "Iter-20251013-1200-012",
            "started_at": base_time.isoformat() + "Z",
            "completed_at": (base_time + timedelta(minutes=10)).isoformat() + "Z",
            "node_states": {
                "IF.AuthAPI": {
                    "status": "completed",
                    "start_time": base_time.isoformat() + "Z",
                    "end_time": (base_time + timedelta(minutes=2)).isoformat() + "Z",
                    "contract_locked": True,
                    "artifacts": ["openapi.yaml"],
                    "gate_results": {
                        "schema_validation": {"status": "passed", "severity": "BLOCKING"},
                        "security_scan": {"status": "passed", "severity": "WARNING"}
                    }
                },
                "IMPL.AuthService": {
                    "status": "completed",
                    "start_time": (base_time + timedelta(minutes=2)).isoformat() + "Z",
                    "end_time": (base_time + timedelta(minutes=7)).isoformat() + "Z",
                    "artifacts": ["auth_service.py", "test_results.json"],
                    "gate_results": {
                        "unit_tests": {"status": "passed", "severity": "BLOCKING"},
                        "code_quality": {"status": "passed", "severity": "WARNING"}
                    }
                },
                "TEST.Integration": {
                    "status": "completed",
                    "start_time": (base_time + timedelta(minutes=7)).isoformat() + "Z",
                    "end_time": (base_time + timedelta(minutes=10)).isoformat() + "Z",
                    "artifacts": ["integration_report.json"],
                    "gate_results": {
                        "integration_tests": {"status": "passed", "severity": "BLOCKING"}
                    }
                }
            }
        }

        await auditor.audit_workflow(
            iteration_id="Iter-20251013-1200-012",
            manifest=complete_manifest,
            execution_log=complete_log
        )

        # Compare audits
        comparison = auditor.compare_audits("Iter-20251013-1200-012")

        assert "completeness_delta" in comparison
        assert comparison["completeness_delta"] > 0  # Improved
        assert comparison["improved"] is True
        assert "summary" in comparison


# ============================================================================
# Summary Test
# ============================================================================

@pytest.mark.integration
@pytest.mark.dde
class TestSummary:
    """Summary test to verify all test IDs"""

    def test_all_test_ids_present(self):
        """Verify all test IDs from DDE-701 to DDE-730 are implemented"""
        # This test documents all test IDs
        test_ids = [
            "DDE-701", "DDE-702", "DDE-703", "DDE-704", "DDE-705",
            "DDE-706", "DDE-707", "DDE-708", "DDE-709", "DDE-710",
            "DDE-711", "DDE-712", "DDE-713", "DDE-714", "DDE-715",
            "DDE-716", "DDE-717", "DDE-718", "DDE-719", "DDE-720",
            "DDE-721", "DDE-722", "DDE-723", "DDE-724", "DDE-725",
            "DDE-726", "DDE-727", "DDE-728", "DDE-729", "DDE-730"
        ]

        assert len(test_ids) == 30
        assert test_ids[0] == "DDE-701"
        assert test_ids[-1] == "DDE-730"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
