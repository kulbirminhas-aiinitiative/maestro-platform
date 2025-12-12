"""
Tests for TokenTracker - Per-Persona Token Usage Tracking.

EPIC: MD-3094 - Token Efficiency & Cleanup
Covers: AC-1 (token tracking per persona), AC-2 (configurable max_attempts)
"""

import pytest
from datetime import datetime

from maestro_hive.cost.token_tracker import (
    TokenTracker,
    TokenUsage,
    TokenBudgetExceeded,
    MaxAttemptsExceeded,
    PersonaUsageReport,
    TOKEN_TRACKER_CONFIG,
    get_token_tracker,
    reset_global_tracker,
)


class TestTokenUsage:
    """Tests for TokenUsage dataclass."""

    def test_default_values(self):
        """Test default token usage values."""
        usage = TokenUsage(persona_id="test_persona")
        assert usage.persona_id == "test_persona"
        assert usage.tokens_used == 0
        assert usage.budget == 100000
        assert usage.attempts == 0
        assert usage.max_attempts == 3

    def test_budget_remaining(self):
        """Test budget_remaining property."""
        usage = TokenUsage(persona_id="test", tokens_used=30000, budget=100000)
        assert usage.budget_remaining == 70000

    def test_budget_remaining_over_budget(self):
        """Test budget_remaining when over budget returns 0."""
        usage = TokenUsage(persona_id="test", tokens_used=120000, budget=100000)
        assert usage.budget_remaining == 0

    def test_budget_used_percent(self):
        """Test budget_used_percent calculation."""
        usage = TokenUsage(persona_id="test", tokens_used=50000, budget=100000)
        assert usage.budget_used_percent == 50.0

    def test_attempts_remaining(self):
        """Test attempts_remaining property."""
        usage = TokenUsage(persona_id="test", attempts=1, max_attempts=3)
        assert usage.attempts_remaining == 2

    def test_is_over_budget(self):
        """Test is_over_budget property."""
        usage = TokenUsage(persona_id="test", tokens_used=100000, budget=100000)
        assert usage.is_over_budget is True

        usage2 = TokenUsage(persona_id="test", tokens_used=99999, budget=100000)
        assert usage2.is_over_budget is False

    def test_is_max_attempts_reached(self):
        """Test is_max_attempts_reached property."""
        usage = TokenUsage(persona_id="test", attempts=3, max_attempts=3)
        assert usage.is_max_attempts_reached is True

        usage2 = TokenUsage(persona_id="test", attempts=2, max_attempts=3)
        assert usage2.is_max_attempts_reached is False

    def test_to_dict(self):
        """Test serialization to dictionary."""
        usage = TokenUsage(
            persona_id="backend_developer",
            tokens_used=5000,
            budget=100000,
            attempts=1,
            max_attempts=3,
            last_updated=datetime(2025, 12, 11, 10, 0, 0)
        )
        d = usage.to_dict()
        assert d["persona_id"] == "backend_developer"
        assert d["tokens_used"] == 5000
        assert d["budget"] == 100000
        assert d["budget_remaining"] == 95000
        assert d["budget_used_percent"] == 5.0
        assert d["attempts"] == 1
        assert d["attempts_remaining"] == 2
        assert d["is_over_budget"] is False
        assert d["is_max_attempts_reached"] is False


class TestTokenTracker:
    """Tests for TokenTracker class - implements AC-1 and AC-2."""

    def setup_method(self):
        """Reset global tracker before each test."""
        reset_global_tracker()

    def test_initialization_defaults(self):
        """Test tracker initialization with defaults."""
        tracker = TokenTracker()
        assert tracker._default_budget == TOKEN_TRACKER_CONFIG["default_token_budget"]
        assert tracker._default_max_attempts == TOKEN_TRACKER_CONFIG["default_max_attempts"]

    def test_initialization_custom(self):
        """Test tracker initialization with custom values."""
        tracker = TokenTracker(max_tokens_per_persona=50000, max_attempts=5)
        assert tracker._default_budget == 50000
        assert tracker._default_max_attempts == 5

    def test_record_tokens(self):
        """AC-1: Test recording token usage for a persona."""
        tracker = TokenTracker()
        usage = tracker.record("backend_developer", tokens=5000)

        assert usage.persona_id == "backend_developer"
        assert usage.tokens_used == 5000
        assert usage.last_updated is not None

    def test_record_tokens_cumulative(self):
        """AC-1: Test cumulative token tracking."""
        tracker = TokenTracker()
        tracker.record("backend_developer", tokens=5000)
        usage = tracker.record("backend_developer", tokens=3000)

        assert usage.tokens_used == 8000

    def test_record_budget_exceeded_raises(self):
        """AC-1: Test TokenBudgetExceeded is raised when over budget."""
        tracker = TokenTracker(max_tokens_per_persona=10000)

        with pytest.raises(TokenBudgetExceeded) as exc_info:
            tracker.record("backend_developer", tokens=15000)

        assert exc_info.value.persona_id == "backend_developer"
        assert exc_info.value.tokens_used == 15000
        assert exc_info.value.budget == 10000

    def test_record_budget_exceeded_no_raise(self):
        """AC-1: Test recording without raising on budget exceeded."""
        tracker = TokenTracker(max_tokens_per_persona=10000)
        usage = tracker.record("backend_developer", tokens=15000, raise_on_exceeded=False)

        assert usage.tokens_used == 15000
        assert usage.is_over_budget is True

    def test_record_attempt(self):
        """AC-2: Test recording execution attempts."""
        tracker = TokenTracker()
        usage = tracker.record_attempt("backend_developer")

        assert usage.attempts == 1
        assert usage.attempts_remaining == 2

    def test_record_attempt_max_exceeded_raises(self):
        """AC-2: Test MaxAttemptsExceeded is raised when max attempts reached."""
        tracker = TokenTracker(max_attempts=3)

        tracker.record_attempt("backend_developer")  # 1
        tracker.record_attempt("backend_developer")  # 2

        with pytest.raises(MaxAttemptsExceeded) as exc_info:
            tracker.record_attempt("backend_developer")  # 3

        assert exc_info.value.persona_id == "backend_developer"
        assert exc_info.value.attempts == 3
        assert exc_info.value.max_attempts == 3

    def test_record_attempt_no_raise(self):
        """AC-2: Test recording attempts without raising."""
        tracker = TokenTracker(max_attempts=2)
        tracker.record_attempt("backend_developer", raise_on_exceeded=False)
        usage = tracker.record_attempt("backend_developer", raise_on_exceeded=False)

        assert usage.attempts == 2
        assert usage.is_max_attempts_reached is True

    def test_get_usage(self):
        """Test getting usage for a specific persona."""
        tracker = TokenTracker()
        tracker.record("backend_developer", tokens=5000)

        usage = tracker.get_usage("backend_developer")
        assert usage is not None
        assert usage.tokens_used == 5000

    def test_get_usage_none_for_unknown(self):
        """Test get_usage returns None for unknown persona."""
        tracker = TokenTracker()
        usage = tracker.get_usage("unknown_persona")
        assert usage is None

    def test_check_budget(self):
        """Test budget checking."""
        tracker = TokenTracker(max_tokens_per_persona=10000)
        tracker.record("backend_developer", tokens=5000)

        assert tracker.check_budget("backend_developer", required_tokens=4000) is True
        assert tracker.check_budget("backend_developer", required_tokens=6000) is False

    def test_check_attempts(self):
        """AC-2: Test attempts checking."""
        tracker = TokenTracker(max_attempts=3)
        tracker.record_attempt("backend_developer", raise_on_exceeded=False)
        tracker.record_attempt("backend_developer", raise_on_exceeded=False)

        assert tracker.check_attempts("backend_developer") is True

        tracker.record_attempt("backend_developer", raise_on_exceeded=False)
        assert tracker.check_attempts("backend_developer") is False

    def test_set_budget(self):
        """Test setting custom budget for a persona."""
        tracker = TokenTracker()
        usage = tracker.set_budget("backend_developer", budget=200000)

        assert usage.budget == 200000

    def test_set_max_attempts(self):
        """AC-2: Test setting custom max_attempts for a persona."""
        tracker = TokenTracker()
        usage = tracker.set_max_attempts("backend_developer", max_attempts=5)

        assert usage.max_attempts == 5

    def test_reset_single_persona(self):
        """Test resetting a single persona's usage."""
        tracker = TokenTracker()
        tracker.record("backend_developer", tokens=5000)
        tracker.record("frontend_developer", tokens=3000)

        tracker.reset("backend_developer")

        assert tracker.get_usage("backend_developer") is None
        assert tracker.get_usage("frontend_developer") is not None

    def test_reset_all(self):
        """Test resetting all usage data."""
        tracker = TokenTracker()
        tracker.record("backend_developer", tokens=5000)
        tracker.record("frontend_developer", tokens=3000)

        tracker.reset()

        assert tracker.get_usage("backend_developer") is None
        assert tracker.get_usage("frontend_developer") is None

    def test_get_report(self):
        """AC-1: Test comprehensive usage report generation."""
        tracker = TokenTracker(max_tokens_per_persona=10000)
        tracker.record("backend_developer", tokens=5000)
        tracker.record("frontend_developer", tokens=8500)  # 85% - triggers warning

        report = tracker.get_report()

        assert report.total_tokens_used == 13500
        assert report.total_budget == 20000
        assert len(report.personas) == 2
        assert len(report.warnings) >= 1  # Should have warning for frontend_developer

    def test_get_all_usage(self):
        """Test getting all persona usage records."""
        tracker = TokenTracker()
        tracker.record("backend_developer", tokens=5000)
        tracker.record("frontend_developer", tokens=3000)

        all_usage = tracker.get_all_usage()

        assert len(all_usage) == 2
        assert "backend_developer" in all_usage
        assert "frontend_developer" in all_usage


class TestGlobalTracker:
    """Tests for global singleton tracker."""

    def setup_method(self):
        """Reset global tracker before each test."""
        reset_global_tracker()

    def test_get_token_tracker_singleton(self):
        """Test global tracker is a singleton."""
        tracker1 = get_token_tracker()
        tracker2 = get_token_tracker()

        assert tracker1 is tracker2

    def test_reset_global_tracker(self):
        """Test resetting global tracker."""
        tracker1 = get_token_tracker()
        tracker1.record("test", tokens=1000)

        reset_global_tracker()

        tracker2 = get_token_tracker()
        assert tracker2 is not tracker1
        assert tracker2.get_usage("test") is None


class TestExceptions:
    """Tests for custom exceptions."""

    def test_token_budget_exceeded_message(self):
        """Test TokenBudgetExceeded exception message."""
        exc = TokenBudgetExceeded("test_persona", 15000, 10000)
        assert "test_persona" in str(exc)
        assert "15000" in str(exc)
        assert "10000" in str(exc)

    def test_token_budget_exceeded_to_dict(self):
        """Test TokenBudgetExceeded serialization."""
        exc = TokenBudgetExceeded("test_persona", 15000, 10000)
        d = exc.to_dict()

        assert d["error"] == "TokenBudgetExceeded"
        assert d["persona_id"] == "test_persona"
        assert d["tokens_used"] == 15000
        assert d["budget"] == 10000
        assert d["overage"] == 5000

    def test_max_attempts_exceeded_message(self):
        """Test MaxAttemptsExceeded exception message."""
        exc = MaxAttemptsExceeded("test_persona", 3, 3)
        assert "test_persona" in str(exc)
        assert "3/3" in str(exc)

    def test_max_attempts_exceeded_to_dict(self):
        """Test MaxAttemptsExceeded serialization."""
        exc = MaxAttemptsExceeded("test_persona", 3, 3)
        d = exc.to_dict()

        assert d["error"] == "MaxAttemptsExceeded"
        assert d["persona_id"] == "test_persona"
        assert d["attempts"] == 3
        assert d["max_attempts"] == 3


class TestPersonaUsageReport:
    """Tests for PersonaUsageReport dataclass."""

    def test_total_budget_used_percent(self):
        """Test total budget percentage calculation."""
        report = PersonaUsageReport(
            total_tokens_used=50000,
            total_budget=100000,
            personas={},
            generated_at=datetime.now()
        )
        assert report.total_budget_used_percent == 50.0

    def test_to_dict(self):
        """Test report serialization."""
        usage = TokenUsage(persona_id="test", tokens_used=5000)
        report = PersonaUsageReport(
            total_tokens_used=5000,
            total_budget=100000,
            personas={"test": usage},
            generated_at=datetime.now(),
            warnings=["Test warning"]
        )

        d = report.to_dict()
        assert d["total_tokens_used"] == 5000
        assert d["total_budget"] == 100000
        assert "test" in d["personas"]
        assert d["warnings"] == ["Test warning"]
