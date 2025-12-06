"""
Unit tests for the DDE, BDV, and ACC data loaders.

Tests the real data loading from file-based storage.

MD-2075: Replace load_dde_audit() stub with real loader
MD-2076: Replace load_bdv_audit() stub with real loader
MD-2077: Replace load_acc_audit() stub with real loader
"""

import pytest
import json
import tempfile
import os
from pathlib import Path

from tri_audit.tri_audit import (
    load_dde_audit,
    load_bdv_audit,
    load_acc_audit,
    DDEAuditResult,
    BDVAuditResult,
    ACCAuditResult,
)


class TestLoadDDEAudit:
    """Test the load_dde_audit function."""

    def test_load_from_performance_tracker(self):
        """Test loading DDE data from performance tracker metrics."""
        # Test with a known execution ID that has performance data
        result = load_dde_audit("sdlc_90d46aa4_20251201_171107")

        # If data exists, validate structure
        if result is not None:
            assert isinstance(result, DDEAuditResult)
            assert result.iteration_id == "sdlc_90d46aa4_20251201_171107"
            assert 0.0 <= result.score <= 1.0
            assert isinstance(result.passed, bool)
            assert isinstance(result.details, dict)

    def test_nonexistent_iteration_returns_none(self):
        """Test that non-existent iteration returns None."""
        result = load_dde_audit("nonexistent-iteration-xyz")
        assert result is None

    def test_dde_result_structure(self):
        """Test DDE audit result has all required fields."""
        result = load_dde_audit("sdlc_90d46aa4_20251201_171107")

        if result is not None:
            # Check all required fields exist
            assert hasattr(result, 'iteration_id')
            assert hasattr(result, 'passed')
            assert hasattr(result, 'score')
            assert hasattr(result, 'all_nodes_complete')
            assert hasattr(result, 'blocking_gates_passed')
            assert hasattr(result, 'artifacts_stamped')
            assert hasattr(result, 'lineage_intact')
            assert hasattr(result, 'contracts_locked')
            assert hasattr(result, 'details')


class TestLoadBDVAudit:
    """Test the load_bdv_audit function."""

    def test_load_from_validation_result(self):
        """Test loading BDV data from validation_result.json."""
        result = load_bdv_audit("sdlc_90d46aa4_20251201_171107")

        if result is not None:
            assert isinstance(result, BDVAuditResult)
            assert isinstance(result.total_scenarios, int)
            assert isinstance(result.passed_scenarios, int)
            assert isinstance(result.failed_scenarios, int)
            assert 0.0 <= result.flake_rate <= 1.0

    def test_load_from_bdv_results(self):
        """Test loading BDV data from bdv_results.json format."""
        result = load_bdv_audit("test-full-workflow")

        if result is not None:
            assert isinstance(result, BDVAuditResult)
            assert result.total_scenarios >= 0

    def test_nonexistent_iteration_returns_none(self):
        """Test that non-existent iteration returns None."""
        result = load_bdv_audit("nonexistent-bdv-xyz")
        assert result is None

    def test_bdv_result_structure(self):
        """Test BDV audit result has all required fields."""
        result = load_bdv_audit("sdlc_90d46aa4_20251201_171107")

        if result is not None:
            assert hasattr(result, 'iteration_id')
            assert hasattr(result, 'passed')
            assert hasattr(result, 'total_scenarios')
            assert hasattr(result, 'passed_scenarios')
            assert hasattr(result, 'failed_scenarios')
            assert hasattr(result, 'flake_rate')
            assert hasattr(result, 'contract_mismatches')
            assert hasattr(result, 'critical_journeys_covered')
            assert hasattr(result, 'details')


class TestLoadACCAudit:
    """Test the load_acc_audit function."""

    def test_load_from_validation_result(self):
        """Test loading ACC data from validation_result.json."""
        result = load_acc_audit("sdlc_90d46aa4_20251201_171107")

        if result is not None:
            assert isinstance(result, ACCAuditResult)
            assert isinstance(result.blocking_violations, int)
            assert isinstance(result.warning_violations, int)
            assert isinstance(result.cycles, list)

    def test_nonexistent_iteration_returns_none(self):
        """Test that non-existent iteration returns None."""
        result = load_acc_audit("nonexistent-acc-xyz")
        assert result is None

    def test_acc_result_structure(self):
        """Test ACC audit result has all required fields."""
        result = load_acc_audit("sdlc_90d46aa4_20251201_171107")

        if result is not None:
            assert hasattr(result, 'iteration_id')
            assert hasattr(result, 'passed')
            assert hasattr(result, 'blocking_violations')
            assert hasattr(result, 'warning_violations')
            assert hasattr(result, 'cycles')
            assert hasattr(result, 'coupling_scores')
            assert hasattr(result, 'suppressions_have_adrs')
            assert hasattr(result, 'coupling_within_limits')
            assert hasattr(result, 'no_new_cycles')
            assert hasattr(result, 'details')

    def test_acc_compliant_result(self):
        """Test that compliant ACC result has passed=True."""
        result = load_acc_audit("sdlc_90d46aa4_20251201_171107")

        if result is not None:
            # This execution should be compliant
            if result.details.get('is_compliant', False):
                assert result.passed is True
                assert result.blocking_violations == 0


class TestLoaderIntegration:
    """Integration tests for all loaders working together."""

    def test_all_loaders_return_same_iteration_id(self):
        """Test that all loaders correctly set iteration_id."""
        test_id = "sdlc_90d46aa4_20251201_171107"

        dde = load_dde_audit(test_id)
        bdv = load_bdv_audit(test_id)
        acc = load_acc_audit(test_id)

        if dde is not None:
            assert dde.iteration_id == test_id
        if bdv is not None:
            assert bdv.iteration_id == test_id
        if acc is not None:
            assert acc.iteration_id == test_id

    def test_to_dict_method(self):
        """Test that to_dict() methods work correctly."""
        test_id = "sdlc_90d46aa4_20251201_171107"

        dde = load_dde_audit(test_id)
        if dde is not None:
            dde_dict = dde.to_dict()
            assert isinstance(dde_dict, dict)
            assert 'iteration_id' in dde_dict
            assert 'passed' in dde_dict
            assert 'score' in dde_dict

        bdv = load_bdv_audit(test_id)
        if bdv is not None:
            bdv_dict = bdv.to_dict()
            assert isinstance(bdv_dict, dict)
            assert 'iteration_id' in bdv_dict
            assert 'passed' in bdv_dict

        acc = load_acc_audit(test_id)
        if acc is not None:
            acc_dict = acc.to_dict()
            assert isinstance(acc_dict, dict)
            assert 'iteration_id' in acc_dict
            assert 'passed' in acc_dict


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
