"""
Unit tests for the 8-case Tri-Modal truth table.

Tests all combinations of DDE, BDV, ACC pass/fail to ensure
correct verdict determination.

MD-2083: Write unit tests for 8 truth table cases
"""

import pytest
from tri_audit.tri_audit import (
    determine_verdict,
    tri_modal_audit,
    TriModalVerdict,
    DDEAuditResult,
    BDVAuditResult,
    ACCAuditResult,
)


class TestDetermineVerdict:
    """Test the determine_verdict() function with all 8 truth table cases."""

    def test_case_1_all_pass(self):
        """
        Case 1: DDE=T, BDV=T, ACC=T -> ALL_PASS (can_deploy=YES)
        All audits passed - safe to deploy.
        """
        verdict = determine_verdict(dde=True, bdv=True, acc=True)
        assert verdict == TriModalVerdict.ALL_PASS

    def test_case_2_design_gap(self):
        """
        Case 2: DDE=T, BDV=F, ACC=T -> DESIGN_GAP (can_deploy=NO)
        Built right, architecturally sound, but wrong thing (BDV fails).
        """
        verdict = determine_verdict(dde=True, bdv=False, acc=True)
        assert verdict == TriModalVerdict.DESIGN_GAP

    def test_case_3_architectural_erosion(self):
        """
        Case 3: DDE=T, BDV=T, ACC=F -> ARCHITECTURAL_EROSION (can_deploy=NO)
        Built right, does what users want, but architectural violations.
        """
        verdict = determine_verdict(dde=True, bdv=True, acc=False)
        assert verdict == TriModalVerdict.ARCHITECTURAL_EROSION

    def test_case_4_process_issue(self):
        """
        Case 4: DDE=F, BDV=T, ACC=T -> PROCESS_ISSUE (can_deploy=NO)
        Does what users want, architecturally sound, but process issues.
        """
        verdict = determine_verdict(dde=False, bdv=True, acc=True)
        assert verdict == TriModalVerdict.PROCESS_ISSUE

    def test_case_5_systemic_failure(self):
        """
        Case 5: DDE=F, BDV=F, ACC=F -> SYSTEMIC_FAILURE (can_deploy=NO)
        All three audits failed - systemic issues.
        """
        verdict = determine_verdict(dde=False, bdv=False, acc=False)
        assert verdict == TriModalVerdict.SYSTEMIC_FAILURE

    def test_case_6_mixed_failure_dde_pass_only(self):
        """
        Case 6: DDE=T, BDV=F, ACC=F -> MIXED_FAILURE (can_deploy=NO)
        Only DDE passes - mixed failure.
        """
        verdict = determine_verdict(dde=True, bdv=False, acc=False)
        assert verdict == TriModalVerdict.MIXED_FAILURE

    def test_case_7_mixed_failure_bdv_pass_only(self):
        """
        Case 7: DDE=F, BDV=T, ACC=F -> MIXED_FAILURE (can_deploy=NO)
        Only BDV passes - mixed failure.
        """
        verdict = determine_verdict(dde=False, bdv=True, acc=False)
        assert verdict == TriModalVerdict.MIXED_FAILURE

    def test_case_8_mixed_failure_acc_pass_only(self):
        """
        Case 8: DDE=F, BDV=F, ACC=T -> MIXED_FAILURE (can_deploy=NO)
        Only ACC passes - mixed failure.
        """
        verdict = determine_verdict(dde=False, bdv=False, acc=True)
        assert verdict == TriModalVerdict.MIXED_FAILURE


class TestTriModalAuditWithMocks:
    """Test tri_modal_audit with mocked audit results."""

    def _create_dde_result(self, passed: bool) -> DDEAuditResult:
        """Create a mock DDE audit result."""
        return DDEAuditResult(
            iteration_id="test-iter",
            passed=passed,
            score=0.95 if passed else 0.45,
            all_nodes_complete=passed,
            blocking_gates_passed=passed,
            artifacts_stamped=passed,
            lineage_intact=passed,
            contracts_locked=passed,
            details={"mocked": True}
        )

    def _create_bdv_result(self, passed: bool) -> BDVAuditResult:
        """Create a mock BDV audit result."""
        return BDVAuditResult(
            iteration_id="test-iter",
            passed=passed,
            total_scenarios=10,
            passed_scenarios=10 if passed else 3,
            failed_scenarios=0 if passed else 7,
            flake_rate=0.02 if passed else 0.3,
            contract_mismatches=[] if passed else ["Contract A"],
            critical_journeys_covered=passed,
            details={"mocked": True}
        )

    def _create_acc_result(self, passed: bool) -> ACCAuditResult:
        """Create a mock ACC audit result."""
        return ACCAuditResult(
            iteration_id="test-iter",
            passed=passed,
            blocking_violations=0 if passed else 5,
            warning_violations=2,
            cycles=[] if passed else [["A", "B", "A"]],
            coupling_scores={},
            suppressions_have_adrs=True,
            coupling_within_limits=passed,
            no_new_cycles=passed,
            details={"mocked": True}
        )

    def test_all_pass_can_deploy(self):
        """Test that ALL_PASS verdict allows deployment."""
        result = tri_modal_audit(
            iteration_id="test-all-pass",
            dde_result=self._create_dde_result(True),
            bdv_result=self._create_bdv_result(True),
            acc_result=self._create_acc_result(True)
        )
        assert result.verdict == TriModalVerdict.ALL_PASS
        assert result.can_deploy is True
        assert result.dde_passed is True
        assert result.bdv_passed is True
        assert result.acc_passed is True

    def test_design_gap_blocks_deploy(self):
        """Test that DESIGN_GAP verdict blocks deployment."""
        result = tri_modal_audit(
            iteration_id="test-design-gap",
            dde_result=self._create_dde_result(True),
            bdv_result=self._create_bdv_result(False),
            acc_result=self._create_acc_result(True)
        )
        assert result.verdict == TriModalVerdict.DESIGN_GAP
        assert result.can_deploy is False
        assert "DESIGN GAP" in result.diagnosis

    def test_architectural_erosion_blocks_deploy(self):
        """Test that ARCHITECTURAL_EROSION verdict blocks deployment."""
        result = tri_modal_audit(
            iteration_id="test-arch-erosion",
            dde_result=self._create_dde_result(True),
            bdv_result=self._create_bdv_result(True),
            acc_result=self._create_acc_result(False)
        )
        assert result.verdict == TriModalVerdict.ARCHITECTURAL_EROSION
        assert result.can_deploy is False
        assert "ARCHITECTURAL EROSION" in result.diagnosis

    def test_process_issue_blocks_deploy(self):
        """Test that PROCESS_ISSUE verdict blocks deployment."""
        result = tri_modal_audit(
            iteration_id="test-process-issue",
            dde_result=self._create_dde_result(False),
            bdv_result=self._create_bdv_result(True),
            acc_result=self._create_acc_result(True)
        )
        assert result.verdict == TriModalVerdict.PROCESS_ISSUE
        assert result.can_deploy is False
        assert "PROCESS ISSUE" in result.diagnosis

    def test_systemic_failure_blocks_deploy(self):
        """Test that SYSTEMIC_FAILURE verdict blocks deployment."""
        result = tri_modal_audit(
            iteration_id="test-systemic-failure",
            dde_result=self._create_dde_result(False),
            bdv_result=self._create_bdv_result(False),
            acc_result=self._create_acc_result(False)
        )
        assert result.verdict == TriModalVerdict.SYSTEMIC_FAILURE
        assert result.can_deploy is False
        assert "SYSTEMIC FAILURE" in result.diagnosis


class TestRecommendations:
    """Test that recommendations are generated correctly."""

    def test_dde_failure_recommendations(self):
        """Test DDE failure generates relevant recommendations."""
        dde_result = DDEAuditResult(
            iteration_id="test",
            passed=False,
            score=0.5,
            all_nodes_complete=False,
            blocking_gates_passed=False,
            artifacts_stamped=True,
            lineage_intact=True,
            contracts_locked=False,
            details={}
        )
        bdv_result = BDVAuditResult(
            iteration_id="test",
            passed=True,
            total_scenarios=10,
            passed_scenarios=10,
            failed_scenarios=0,
            flake_rate=0.02,
            contract_mismatches=[],
            critical_journeys_covered=True,
            details={}
        )
        acc_result = ACCAuditResult(
            iteration_id="test",
            passed=True,
            blocking_violations=0,
            warning_violations=0,
            cycles=[],
            coupling_scores={},
            suppressions_have_adrs=True,
            coupling_within_limits=True,
            no_new_cycles=True,
            details={}
        )

        result = tri_modal_audit(
            iteration_id="test-dde-recs",
            dde_result=dde_result,
            bdv_result=bdv_result,
            acc_result=acc_result
        )

        # Should have DDE-related recommendations
        recs = " ".join(result.recommendations)
        assert "DDE" in recs or "nodes" in recs or "gates" in recs

    def test_all_pass_no_action_required(self):
        """Test that ALL_PASS generates 'no action required' recommendation."""
        dde = DDEAuditResult(
            iteration_id="test",
            passed=True,
            score=0.95,
            all_nodes_complete=True,
            blocking_gates_passed=True,
            artifacts_stamped=True,
            lineage_intact=True,
            contracts_locked=True,
            details={}
        )
        bdv = BDVAuditResult(
            iteration_id="test",
            passed=True,
            total_scenarios=10,
            passed_scenarios=10,
            failed_scenarios=0,
            flake_rate=0.02,
            contract_mismatches=[],
            critical_journeys_covered=True,
            details={}
        )
        acc = ACCAuditResult(
            iteration_id="test",
            passed=True,
            blocking_violations=0,
            warning_violations=0,
            cycles=[],
            coupling_scores={},
            suppressions_have_adrs=True,
            coupling_within_limits=True,
            no_new_cycles=True,
            details={}
        )

        result = tri_modal_audit(
            iteration_id="test-no-action",
            dde_result=dde,
            bdv_result=bdv,
            acc_result=acc
        )

        assert "No action required" in result.recommendations[0]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
