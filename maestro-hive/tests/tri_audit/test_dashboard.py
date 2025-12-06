"""
Tests for tri_audit/dashboard.py (MD-2082)

Tests dashboard data provider:
- Health status calculation
- Trend calculation
- Dashboard status generation
- Verdict breakdown
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

from tri_audit.dashboard import (
    TrendDirection,
    StreamHealthStatus,
    DashboardStatus,
    TrendDataPoint,
    TrendData,
    VerdictBreakdown,
    StreamDetail,
    RecentAudit,
    calculate_health_status,
    calculate_trend,
    get_daily_stats,
    get_verdict_counts,
    get_top_failure_reasons,
    get_dashboard_status,
    get_trend_data,
    get_verdict_breakdown,
    get_stream_details,
    get_recent_audits,
    get_full_dashboard_data
)

from tri_audit.storage import AuditHistoryEntry


class TestCalculateHealthStatus:
    """Tests for health status calculation."""

    def test_healthy_high_rate(self):
        """High pass rate should be healthy."""
        assert calculate_health_status(0.95) == StreamHealthStatus.HEALTHY
        assert calculate_health_status(0.90) == StreamHealthStatus.HEALTHY

    def test_degraded_medium_rate(self):
        """Medium pass rate should be degraded."""
        assert calculate_health_status(0.85) == StreamHealthStatus.DEGRADED
        assert calculate_health_status(0.70) == StreamHealthStatus.DEGRADED

    def test_critical_low_rate(self):
        """Low pass rate should be critical."""
        assert calculate_health_status(0.65) == StreamHealthStatus.CRITICAL
        assert calculate_health_status(0.0) == StreamHealthStatus.CRITICAL

    def test_unknown_negative_rate(self):
        """Negative rate should be unknown."""
        assert calculate_health_status(-0.1) == StreamHealthStatus.UNKNOWN


class TestCalculateTrend:
    """Tests for trend direction calculation."""

    def test_improving_trend(self):
        """Significant increase should be improving."""
        assert calculate_trend(0.9, 0.8) == TrendDirection.IMPROVING

    def test_declining_trend(self):
        """Significant decrease should be declining."""
        assert calculate_trend(0.7, 0.9) == TrendDirection.DECLINING

    def test_stable_trend(self):
        """Small change should be stable."""
        assert calculate_trend(0.85, 0.84) == TrendDirection.STABLE
        assert calculate_trend(0.85, 0.86) == TrendDirection.STABLE

    def test_unknown_zero_previous(self):
        """Zero previous should be unknown."""
        assert calculate_trend(0.5, 0) == TrendDirection.UNKNOWN


class TestGetDailyStats:
    """Tests for daily statistics calculation."""

    def test_empty_history(self):
        """Empty history should return zeros."""
        stats = get_daily_stats([], 0)
        assert stats["total"] == 0
        assert stats["pass_rate"] == 0.0

    def test_calculates_rates(self):
        """Should calculate correct rates."""
        now = datetime.utcnow()
        history = [
            AuditHistoryEntry(
                iteration_id=f"iter-{i}",
                timestamp=now.isoformat() + "Z",
                verdict="all_pass" if i % 2 == 0 else "design_gap",
                can_deploy=(i % 2 == 0),
                dde_passed=True,
                bdv_passed=(i % 2 == 0),
                acc_passed=True
            )
            for i in range(4)
        ]

        stats = get_daily_stats(history, 0)
        assert stats["total"] == 4
        assert stats["pass_rate"] == 0.5  # 2 out of 4
        assert stats["dde_rate"] == 1.0  # All pass
        assert stats["bdv_rate"] == 0.5  # 2 out of 4


class TestGetVerdictCounts:
    """Tests for verdict counting."""

    def test_empty_history(self):
        """Empty history should have zero counts."""
        counts = get_verdict_counts([])
        assert counts["all_pass"] == 0
        assert counts["systemic_failure"] == 0

    def test_counts_verdicts(self):
        """Should count each verdict type."""
        history = [
            AuditHistoryEntry(
                iteration_id=f"iter-{i}",
                timestamp=datetime.utcnow().isoformat() + "Z",
                verdict="all_pass",
                can_deploy=True,
                dde_passed=True,
                bdv_passed=True,
                acc_passed=True
            )
            for i in range(3)
        ] + [
            AuditHistoryEntry(
                iteration_id="iter-failure",
                timestamp=datetime.utcnow().isoformat() + "Z",
                verdict="systemic_failure",
                can_deploy=False,
                dde_passed=False,
                bdv_passed=False,
                acc_passed=False
            )
        ]

        counts = get_verdict_counts(history)
        assert counts["all_pass"] == 3
        assert counts["systemic_failure"] == 1


class TestGetTopFailureReasons:
    """Tests for failure reason extraction."""

    def test_no_failures_empty_reasons(self):
        """No failures should return empty reasons."""
        history = [
            AuditHistoryEntry(
                iteration_id="iter-1",
                timestamp=datetime.utcnow().isoformat() + "Z",
                verdict="all_pass",
                can_deploy=True,
                dde_passed=True,
                bdv_passed=True,
                acc_passed=True
            )
        ]

        reasons = get_top_failure_reasons(history, "dde")
        assert len(reasons) == 0

    def test_dde_failures(self):
        """DDE failures should return execution reasons."""
        history = [
            AuditHistoryEntry(
                iteration_id="iter-1",
                timestamp=datetime.utcnow().isoformat() + "Z",
                verdict="process_issue",
                can_deploy=False,
                dde_passed=False,
                bdv_passed=True,
                acc_passed=True
            )
        ]

        reasons = get_top_failure_reasons(history, "dde")
        assert len(reasons) > 0
        assert "Execution" in reasons[0] or "process" in reasons[0]


class TestDashboardStatus:
    """Tests for DashboardStatus model."""

    def test_model_creation(self):
        """Test model can be created."""
        status = DashboardStatus(
            timestamp=datetime.utcnow().isoformat() + "Z",
            overall_health=StreamHealthStatus.HEALTHY,
            deployment_readiness=True,
            overall_pass_rate=0.95,
            dde_pass_rate=0.98,
            bdv_pass_rate=0.92,
            acc_pass_rate=0.95,
            dde_health=StreamHealthStatus.HEALTHY,
            bdv_health=StreamHealthStatus.HEALTHY,
            acc_health=StreamHealthStatus.HEALTHY,
            pass_rate_trend=TrendDirection.STABLE,
            dde_trend=TrendDirection.STABLE,
            bdv_trend=TrendDirection.STABLE,
            acc_trend=TrendDirection.STABLE,
            total_audits_today=10,
            approved_today=9,
            blocked_today=1,
            active_blocks=1,
            systemic_failures=0
        )

        assert status.overall_health == StreamHealthStatus.HEALTHY
        assert status.deployment_readiness is True


class TestTrendData:
    """Tests for TrendData model."""

    def test_model_creation(self):
        """Test model can be created."""
        trend = TrendData(
            period_days=7,
            data_points=[
                TrendDataPoint(
                    timestamp=datetime.utcnow().isoformat() + "Z",
                    date=datetime.utcnow().date().isoformat(),
                    pass_rate=0.9,
                    dde_rate=0.95,
                    bdv_rate=0.88,
                    acc_rate=0.92,
                    total_audits=10
                )
            ],
            overall_trend=TrendDirection.IMPROVING
        )

        assert trend.period_days == 7
        assert len(trend.data_points) == 1


class TestVerdictBreakdown:
    """Tests for VerdictBreakdown model."""

    def test_model_creation(self):
        """Test model can be created."""
        breakdown = VerdictBreakdown(
            all_pass=80,
            design_gap=5,
            architectural_erosion=8,
            process_issue=4,
            systemic_failure=1,
            mixed_failure=2,
            total=100
        )

        assert breakdown.total == 100
        assert breakdown.all_pass == 80


class TestIntegration:
    """Integration tests with mocked dependencies."""

    @patch('tri_audit.dashboard.get_audit_statistics')
    @patch('tri_audit.dashboard.get_audit_history')
    def test_get_dashboard_status_with_data(self, mock_history, mock_stats):
        """Test dashboard status generation."""
        mock_stats.return_value = {
            "total_audits": 100,
            "deployable": 90,
            "blocked": 10,
            "pass_rate": 0.9,
            "stream_pass_rates": {
                "dde": 0.95,
                "bdv": 0.88,
                "acc": 0.92
            }
        }
        mock_history.return_value = []

        status = get_dashboard_status(days=7)

        assert status.overall_pass_rate == 0.9
        assert status.dde_pass_rate == 0.95
        assert status.overall_health == StreamHealthStatus.HEALTHY

    @patch('tri_audit.dashboard.get_audit_history')
    def test_get_trend_data_with_data(self, mock_history):
        """Test trend data generation."""
        now = datetime.utcnow()
        mock_history.return_value = [
            AuditHistoryEntry(
                iteration_id=f"iter-{i}",
                timestamp=(now - timedelta(days=i)).isoformat() + "Z",
                verdict="all_pass",
                can_deploy=True,
                dde_passed=True,
                bdv_passed=True,
                acc_passed=True
            )
            for i in range(7)
        ]

        trend = get_trend_data(days=7)

        assert trend.period_days == 7
        assert len(trend.data_points) == 7

    @patch('tri_audit.dashboard.get_audit_history')
    def test_get_verdict_breakdown_with_data(self, mock_history):
        """Test verdict breakdown generation."""
        mock_history.return_value = [
            AuditHistoryEntry(
                iteration_id="iter-1",
                timestamp=datetime.utcnow().isoformat() + "Z",
                verdict="all_pass",
                can_deploy=True,
                dde_passed=True,
                bdv_passed=True,
                acc_passed=True
            ),
            AuditHistoryEntry(
                iteration_id="iter-2",
                timestamp=datetime.utcnow().isoformat() + "Z",
                verdict="design_gap",
                can_deploy=False,
                dde_passed=True,
                bdv_passed=False,
                acc_passed=True
            )
        ]

        breakdown = get_verdict_breakdown(days=7)

        assert breakdown.all_pass == 1
        assert breakdown.design_gap == 1
        assert breakdown.total == 2

    @patch('tri_audit.dashboard.get_audit_history')
    def test_get_recent_audits(self, mock_history):
        """Test recent audits retrieval."""
        mock_history.return_value = [
            AuditHistoryEntry(
                iteration_id=f"iter-{i}",
                timestamp=datetime.utcnow().isoformat() + "Z",
                verdict="all_pass",
                can_deploy=True,
                dde_passed=True,
                bdv_passed=True,
                acc_passed=True
            )
            for i in range(5)
        ]

        recent = get_recent_audits(limit=5)

        assert len(recent) == 5
        assert recent[0].iteration_id == "iter-0"


class TestEnums:
    """Tests for enum values."""

    def test_trend_directions(self):
        """All trend directions should exist."""
        assert TrendDirection.IMPROVING.value == "improving"
        assert TrendDirection.DECLINING.value == "declining"
        assert TrendDirection.STABLE.value == "stable"
        assert TrendDirection.UNKNOWN.value == "unknown"

    def test_health_statuses(self):
        """All health statuses should exist."""
        assert StreamHealthStatus.HEALTHY.value == "healthy"
        assert StreamHealthStatus.DEGRADED.value == "degraded"
        assert StreamHealthStatus.CRITICAL.value == "critical"
        assert StreamHealthStatus.UNKNOWN.value == "unknown"
