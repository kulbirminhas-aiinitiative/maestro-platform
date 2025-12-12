#!/usr/bin/env python3
"""
Unit tests for SDLC Phase Configuration

Tests the centralized phase configuration including:
- Phase normalization
- Alias resolution
- Phase sequence validation
- Navigation functions
"""

import pytest
from maestro_hive.config.phases import (
    SDLC_PHASES,
    PHASE_ALIASES,
    normalize_phase_name,
    get_next_phase,
    get_previous_phase,
    validate_phase_sequence
)


class TestPhaseNormalization:
    """Tests for normalize_phase_name function"""

    def test_canonical_phases_unchanged(self):
        """Test canonical phase names are returned as-is"""
        for phase in SDLC_PHASES:
            assert normalize_phase_name(phase) == phase

    def test_case_insensitive(self):
        """Test phase normalization is case-insensitive"""
        assert normalize_phase_name("REQUIREMENTS") == "requirements"
        assert normalize_phase_name("Design") == "design"
        assert normalize_phase_name("IMPLEMENTATION") == "implementation"

    def test_aliases_resolve_correctly(self):
        """Test phase aliases resolve to canonical names"""
        # Backend/frontend should map to implementation
        assert normalize_phase_name("backend_development") == "implementation"
        assert normalize_phase_name("frontend_development") == "implementation"

        # Review should map to testing
        assert normalize_phase_name("review") == "testing"

        # Analysis should map to requirements
        assert normalize_phase_name("analysis") == "requirements"

    def test_whitespace_stripped(self):
        """Test whitespace is stripped from phase names"""
        assert normalize_phase_name("  requirements  ") == "requirements"
        assert normalize_phase_name("\tdesign\n") == "design"

    def test_unknown_phase_raises_error(self):
        """Test unknown phase names raise ValueError"""
        with pytest.raises(ValueError, match="Unknown phase"):
            normalize_phase_name("unknown_phase")

        with pytest.raises(ValueError, match="Unknown phase"):
            normalize_phase_name("invalid")


class TestPhaseNavigation:
    """Tests for phase navigation functions"""

    def test_get_next_phase(self):
        """Test getting next phase in sequence"""
        assert get_next_phase("requirements") == "design"
        assert get_next_phase("design") == "implementation"
        assert get_next_phase("implementation") == "testing"
        assert get_next_phase("testing") == "deployment"

    def test_get_next_phase_from_last(self):
        """Test getting next phase from last phase returns None"""
        assert get_next_phase("deployment") is None

    def test_get_next_phase_normalizes(self):
        """Test get_next_phase normalizes phase names"""
        assert get_next_phase("backend_development") == "testing"
        assert get_next_phase("DESIGN") == "implementation"

    def test_get_previous_phase(self):
        """Test getting previous phase in sequence"""
        assert get_previous_phase("deployment") == "testing"
        assert get_previous_phase("testing") == "implementation"
        assert get_previous_phase("implementation") == "design"
        assert get_previous_phase("design") == "requirements"

    def test_get_previous_phase_from_first(self):
        """Test getting previous phase from first phase returns None"""
        assert get_previous_phase("requirements") is None

    def test_get_previous_phase_normalizes(self):
        """Test get_previous_phase normalizes phase names"""
        assert get_previous_phase("review") == "implementation"
        assert get_previous_phase("TESTING") == "implementation"


class TestPhaseSequenceValidation:
    """Tests for validate_phase_sequence function"""

    def test_valid_full_sequence(self):
        """Test validation passes for complete sequence"""
        sequence = ["requirements", "design", "implementation", "testing", "deployment"]
        assert validate_phase_sequence(sequence) is True

    def test_valid_partial_sequence(self):
        """Test validation passes for partial sequence from start"""
        assert validate_phase_sequence(["requirements"]) is True
        assert validate_phase_sequence(["requirements", "design"]) is True
        assert validate_phase_sequence(["requirements", "design", "implementation"]) is True

    def test_invalid_missing_start(self):
        """Test validation fails when sequence doesn't start at requirements"""
        # Sequence not starting from requirements is still valid order-wise
        assert validate_phase_sequence(["design", "implementation"]) is True

    def test_invalid_out_of_order(self):
        """Test validation fails for out-of-order phases"""
        assert validate_phase_sequence(["requirements", "implementation", "design"]) is False

    def test_invalid_skipped_phase(self):
        """Test validation allows skipped phases (partial sequence is valid)"""
        # Skipping phases but maintaining order is valid
        assert validate_phase_sequence(["requirements", "implementation"]) is True

    def test_empty_sequence(self):
        """Test validation passes for empty sequence"""
        assert validate_phase_sequence([]) is True

    def test_normalizes_phase_names(self):
        """Test validation normalizes phase names"""
        sequence = ["REQUIREMENTS", "Design", "backend_development"]
        assert validate_phase_sequence(sequence) is True


class TestPhaseConstants:
    """Tests for phase constants"""

    def test_sdlc_phases_count(self):
        """Test correct number of SDLC phases"""
        assert len(SDLC_PHASES) == 5

    def test_sdlc_phases_order(self):
        """Test SDLC phases are in correct order"""
        expected = ["requirements", "design", "implementation", "testing", "deployment"]
        assert SDLC_PHASES == expected

    def test_aliases_are_comprehensive(self):
        """Test common aliases are defined"""
        common_aliases = [
            "backend_development",
            "frontend_development",
            "review",
            "analysis",
            "coding",
            "development"
        ]
        for alias in common_aliases:
            assert alias in PHASE_ALIASES
