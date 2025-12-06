"""
Convergence Dashboard Data Provider

Provides data for the tri-modal convergence dashboard:
- Real-time status overview
- Historical trend data
- Stream-level breakdown
- Deployment readiness indicators

Part of MD-2043: Trimodal Convergence Completion
Task: MD-2082 - Create convergence dashboard data provider

Author: Claude Code Agent
Date: 2025-12-02
"""

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field, asdict
from enum import Enum

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

# Import tri-audit components
try:
    from tri_audit.tri_audit import (
        TriModalVerdict,
        TriAuditResult,
        load_dde_audit,
        load_bdv_audit,
        load_acc_audit
    )
except ImportError:
    TriModalVerdict = None
    TriAuditResult = None

# Import storage
try:
    from tri_audit.storage import (
        get_storage,
        get_audit_statistics,
        get_audit_history,
        AuditHistoryEntry
    )
except ImportError:
    get_storage = None
    get_audit_statistics = None
    get_audit_history = None


class TrendDirection(str, Enum):
    """Trend direction for metrics."""
    IMPROVING = "improving"
    DECLINING = "declining"
    STABLE = "stable"
    UNKNOWN = "unknown"


class StreamHealthStatus(str, Enum):
    """Health status for individual streams."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


class DashboardStatus(BaseModel):
    """Overall dashboard status response."""
    timestamp: str
    overall_health: StreamHealthStatus
    deployment_readiness: bool

    # Current pass rates
    overall_pass_rate: float
    dde_pass_rate: float
    bdv_pass_rate: float
    acc_pass_rate: float

    # Stream health
    dde_health: StreamHealthStatus
    bdv_health: StreamHealthStatus
    acc_health: StreamHealthStatus

    # Trend indicators
    pass_rate_trend: TrendDirection
    dde_trend: TrendDirection
    bdv_trend: TrendDirection
    acc_trend: TrendDirection

    # Summary counts
    total_audits_today: int
    approved_today: int
    blocked_today: int

    # Active issues
    active_blocks: int
    systemic_failures: int


class TrendDataPoint(BaseModel):
    """Single data point for trend chart."""
    timestamp: str
    date: str
    pass_rate: float
    dde_rate: float
    bdv_rate: float
    acc_rate: float
    total_audits: int


class TrendData(BaseModel):
    """Trend data for charts."""
    period_days: int
    data_points: List[TrendDataPoint]
    overall_trend: TrendDirection


class VerdictBreakdown(BaseModel):
    """Breakdown of verdict types."""
    all_pass: int
    design_gap: int
    architectural_erosion: int
    process_issue: int
    systemic_failure: int
    mixed_failure: int
    total: int


class StreamDetail(BaseModel):
    """Detailed status for a single stream."""
    name: str
    pass_rate: float
    health: StreamHealthStatus
    trend: TrendDirection

    # Recent stats
    recent_passes: int
    recent_failures: int

    # Common failure reasons (if any)
    top_failure_reasons: List[str]


class RecentAudit(BaseModel):
    """Recent audit entry for list display."""
    iteration_id: str
    timestamp: str
    verdict: str
    can_deploy: bool
    dde_passed: bool
    bdv_passed: bool
    acc_passed: bool


class DashboardData(BaseModel):
    """Complete dashboard data response."""
    status: DashboardStatus
    trend_data: TrendData
    verdict_breakdown: VerdictBreakdown
    stream_details: Dict[str, StreamDetail]
    recent_audits: List[RecentAudit]


# ============================================================================
# Data Calculation Functions
# ============================================================================

def calculate_health_status(pass_rate: float) -> StreamHealthStatus:
    """
    Calculate health status from pass rate.

    Args:
        pass_rate: Pass rate (0.0 to 1.0)

    Returns:
        StreamHealthStatus enum
    """
    if pass_rate >= 0.9:
        return StreamHealthStatus.HEALTHY
    elif pass_rate >= 0.7:
        return StreamHealthStatus.DEGRADED
    elif pass_rate >= 0:
        return StreamHealthStatus.CRITICAL
    else:
        return StreamHealthStatus.UNKNOWN


def calculate_trend(current: float, previous: float, threshold: float = 0.05) -> TrendDirection:
    """
    Calculate trend direction from current and previous values.

    Args:
        current: Current value
        previous: Previous period value
        threshold: Change threshold to consider significant

    Returns:
        TrendDirection enum
    """
    if previous == 0:
        return TrendDirection.UNKNOWN

    change = (current - previous) / previous

    if change > threshold:
        return TrendDirection.IMPROVING
    elif change < -threshold:
        return TrendDirection.DECLINING
    else:
        return TrendDirection.STABLE


def get_daily_stats(history: List[AuditHistoryEntry], days_ago: int) -> Dict[str, Any]:
    """
    Get statistics for a specific day.

    Args:
        history: List of history entries
        days_ago: Days in the past (0 = today)

    Returns:
        Dict with day statistics
    """
    target_date = datetime.utcnow().date() - timedelta(days=days_ago)

    day_entries = []
    for entry in history:
        try:
            entry_date = datetime.fromisoformat(
                entry.timestamp.replace("Z", "+00:00").replace("+00:00", "")
            ).date()
            if entry_date == target_date:
                day_entries.append(entry)
        except Exception:
            continue

    total = len(day_entries)
    if total == 0:
        return {
            "date": target_date.isoformat(),
            "total": 0,
            "pass_rate": 0.0,
            "dde_rate": 0.0,
            "bdv_rate": 0.0,
            "acc_rate": 0.0
        }

    deployable = sum(1 for e in day_entries if e.can_deploy)
    dde_passed = sum(1 for e in day_entries if e.dde_passed)
    bdv_passed = sum(1 for e in day_entries if e.bdv_passed)
    acc_passed = sum(1 for e in day_entries if e.acc_passed)

    return {
        "date": target_date.isoformat(),
        "total": total,
        "pass_rate": deployable / total,
        "dde_rate": dde_passed / total,
        "bdv_rate": bdv_passed / total,
        "acc_rate": acc_passed / total
    }


def get_verdict_counts(history: List[AuditHistoryEntry]) -> Dict[str, int]:
    """
    Count verdicts from history.

    Args:
        history: List of history entries

    Returns:
        Dict mapping verdict to count
    """
    counts = {
        "all_pass": 0,
        "design_gap": 0,
        "architectural_erosion": 0,
        "process_issue": 0,
        "systemic_failure": 0,
        "mixed_failure": 0
    }

    for entry in history:
        verdict = entry.verdict
        if verdict in counts:
            counts[verdict] += 1
        else:
            counts["mixed_failure"] += 1

    return counts


def get_top_failure_reasons(history: List[AuditHistoryEntry], stream: str) -> List[str]:
    """
    Get top failure reasons for a stream.

    Args:
        history: List of history entries
        stream: Stream name ("dde", "bdv", "acc")

    Returns:
        List of failure reason strings
    """
    reasons = []

    stream_field = f"{stream}_passed"
    failed_entries = [
        e for e in history
        if not getattr(e, stream_field, True)
    ]

    if not failed_entries:
        return []

    # Analyze patterns
    total_failures = len(failed_entries)

    # Check for correlated failures
    if stream == "dde":
        reasons.append(f"Execution/process issues ({total_failures} failures)")
    elif stream == "bdv":
        reasons.append(f"Behavior validation failures ({total_failures} failures)")
    elif stream == "acc":
        reasons.append(f"Architectural violations ({total_failures} failures)")

    return reasons[:3]  # Top 3


# ============================================================================
# Dashboard Data Provider
# ============================================================================

def get_dashboard_status(days: int = 7) -> DashboardStatus:
    """
    Get current dashboard status.

    Args:
        days: Days to analyze for trends

    Returns:
        DashboardStatus with current metrics
    """
    timestamp = datetime.utcnow().isoformat() + "Z"

    # Get statistics
    if get_audit_statistics:
        current_stats = get_audit_statistics(days=days)
        previous_stats = get_audit_statistics(days=days * 2)
    else:
        current_stats = {
            "total_audits": 0,
            "deployable": 0,
            "blocked": 0,
            "pass_rate": 0.0,
            "stream_pass_rates": {"dde": 0.0, "bdv": 0.0, "acc": 0.0}
        }
        previous_stats = current_stats

    # Get today's stats
    if get_audit_history:
        history = get_audit_history(limit=1000)
        today_stats = get_daily_stats(history, 0)
    else:
        history = []
        today_stats = {"total": 0, "pass_rate": 0.0}

    # Calculate metrics
    overall_rate = current_stats.get("pass_rate", 0.0)
    dde_rate = current_stats.get("stream_pass_rates", {}).get("dde", 0.0)
    bdv_rate = current_stats.get("stream_pass_rates", {}).get("bdv", 0.0)
    acc_rate = current_stats.get("stream_pass_rates", {}).get("acc", 0.0)

    # Calculate health
    overall_health = calculate_health_status(overall_rate)
    dde_health = calculate_health_status(dde_rate)
    bdv_health = calculate_health_status(bdv_rate)
    acc_health = calculate_health_status(acc_rate)

    # Calculate trends
    prev_rate = previous_stats.get("pass_rate", 0.0)
    prev_dde = previous_stats.get("stream_pass_rates", {}).get("dde", 0.0)
    prev_bdv = previous_stats.get("stream_pass_rates", {}).get("bdv", 0.0)
    prev_acc = previous_stats.get("stream_pass_rates", {}).get("acc", 0.0)

    pass_rate_trend = calculate_trend(overall_rate, prev_rate)
    dde_trend = calculate_trend(dde_rate, prev_dde)
    bdv_trend = calculate_trend(bdv_rate, prev_bdv)
    acc_trend = calculate_trend(acc_rate, prev_acc)

    # Count systemic failures
    verdict_counts = get_verdict_counts(history)
    systemic_failures = verdict_counts.get("systemic_failure", 0)

    return DashboardStatus(
        timestamp=timestamp,
        overall_health=overall_health,
        deployment_readiness=(overall_health == StreamHealthStatus.HEALTHY),
        overall_pass_rate=overall_rate,
        dde_pass_rate=dde_rate,
        bdv_pass_rate=bdv_rate,
        acc_pass_rate=acc_rate,
        dde_health=dde_health,
        bdv_health=bdv_health,
        acc_health=acc_health,
        pass_rate_trend=pass_rate_trend,
        dde_trend=dde_trend,
        bdv_trend=bdv_trend,
        acc_trend=acc_trend,
        total_audits_today=today_stats.get("total", 0),
        approved_today=int(today_stats.get("total", 0) * today_stats.get("pass_rate", 0)),
        blocked_today=today_stats.get("total", 0) - int(today_stats.get("total", 0) * today_stats.get("pass_rate", 0)),
        active_blocks=current_stats.get("blocked", 0),
        systemic_failures=systemic_failures
    )


def get_trend_data(days: int = 14) -> TrendData:
    """
    Get trend data for charts.

    Args:
        days: Number of days of data

    Returns:
        TrendData with daily data points
    """
    if not get_audit_history:
        return TrendData(
            period_days=days,
            data_points=[],
            overall_trend=TrendDirection.UNKNOWN
        )

    history = get_audit_history(limit=5000)
    data_points = []

    for i in range(days - 1, -1, -1):
        stats = get_daily_stats(history, i)
        target_date = datetime.utcnow().date() - timedelta(days=i)

        data_points.append(TrendDataPoint(
            timestamp=datetime.combine(target_date, datetime.min.time()).isoformat() + "Z",
            date=stats["date"],
            pass_rate=stats["pass_rate"],
            dde_rate=stats["dde_rate"],
            bdv_rate=stats["bdv_rate"],
            acc_rate=stats["acc_rate"],
            total_audits=stats["total"]
        ))

    # Calculate overall trend
    if len(data_points) >= 2:
        first_half = data_points[:len(data_points)//2]
        second_half = data_points[len(data_points)//2:]

        first_avg = sum(p.pass_rate for p in first_half) / len(first_half) if first_half else 0
        second_avg = sum(p.pass_rate for p in second_half) / len(second_half) if second_half else 0

        overall_trend = calculate_trend(second_avg, first_avg)
    else:
        overall_trend = TrendDirection.UNKNOWN

    return TrendData(
        period_days=days,
        data_points=data_points,
        overall_trend=overall_trend
    )


def get_verdict_breakdown(days: int = 7) -> VerdictBreakdown:
    """
    Get verdict type breakdown.

    Args:
        days: Days to analyze

    Returns:
        VerdictBreakdown with counts
    """
    if not get_audit_history:
        return VerdictBreakdown(
            all_pass=0,
            design_gap=0,
            architectural_erosion=0,
            process_issue=0,
            systemic_failure=0,
            mixed_failure=0,
            total=0
        )

    history = get_audit_history(limit=1000)

    # Filter to time range
    cutoff = datetime.utcnow() - timedelta(days=days)
    recent_history = []
    for entry in history:
        try:
            entry_time = datetime.fromisoformat(
                entry.timestamp.replace("Z", "+00:00").replace("+00:00", "")
            )
            if entry_time >= cutoff:
                recent_history.append(entry)
        except Exception:
            continue

    counts = get_verdict_counts(recent_history)
    total = sum(counts.values())

    return VerdictBreakdown(
        all_pass=counts.get("all_pass", 0),
        design_gap=counts.get("design_gap", 0),
        architectural_erosion=counts.get("architectural_erosion", 0),
        process_issue=counts.get("process_issue", 0),
        systemic_failure=counts.get("systemic_failure", 0),
        mixed_failure=counts.get("mixed_failure", 0),
        total=total
    )


def get_stream_details(days: int = 7) -> Dict[str, StreamDetail]:
    """
    Get detailed status for each stream.

    Args:
        days: Days to analyze

    Returns:
        Dict mapping stream name to StreamDetail
    """
    if not get_audit_history or not get_audit_statistics:
        return {}

    stats = get_audit_statistics(days=days)
    history = get_audit_history(limit=1000)

    # Filter recent history
    cutoff = datetime.utcnow() - timedelta(days=days)
    recent_history = []
    for entry in history:
        try:
            entry_time = datetime.fromisoformat(
                entry.timestamp.replace("Z", "+00:00").replace("+00:00", "")
            )
            if entry_time >= cutoff:
                recent_history.append(entry)
        except Exception:
            continue

    streams = {}
    for stream in ["dde", "bdv", "acc"]:
        rate = stats.get("stream_pass_rates", {}).get(stream, 0.0)
        health = calculate_health_status(rate)

        # Get previous period for trend
        prev_stats = get_audit_statistics(days=days * 2)
        prev_rate = prev_stats.get("stream_pass_rates", {}).get(stream, 0.0)
        trend = calculate_trend(rate, prev_rate)

        # Count recent passes/failures
        stream_field = f"{stream}_passed"
        passes = sum(1 for e in recent_history if getattr(e, stream_field, False))
        failures = len(recent_history) - passes

        streams[stream] = StreamDetail(
            name=stream.upper(),
            pass_rate=rate,
            health=health,
            trend=trend,
            recent_passes=passes,
            recent_failures=failures,
            top_failure_reasons=get_top_failure_reasons(recent_history, stream)
        )

    return streams


def get_recent_audits(limit: int = 10) -> List[RecentAudit]:
    """
    Get recent audit entries for display.

    Args:
        limit: Maximum entries to return

    Returns:
        List of RecentAudit entries
    """
    if not get_audit_history:
        return []

    history = get_audit_history(limit=limit)

    return [
        RecentAudit(
            iteration_id=e.iteration_id,
            timestamp=e.timestamp,
            verdict=e.verdict,
            can_deploy=e.can_deploy,
            dde_passed=e.dde_passed,
            bdv_passed=e.bdv_passed,
            acc_passed=e.acc_passed
        )
        for e in history
    ]


def get_full_dashboard_data(days: int = 7, trend_days: int = 14) -> DashboardData:
    """
    Get complete dashboard data.

    Args:
        days: Days for statistics
        trend_days: Days for trend data

    Returns:
        Complete DashboardData
    """
    return DashboardData(
        status=get_dashboard_status(days),
        trend_data=get_trend_data(trend_days),
        verdict_breakdown=get_verdict_breakdown(days),
        stream_details=get_stream_details(days),
        recent_audits=get_recent_audits(10)
    )


# ============================================================================
# API Router
# ============================================================================

router = APIRouter(prefix="/api/v1/dashboard", tags=["dashboard"])


@router.get("/status", response_model=DashboardStatus)
async def get_status(
    days: int = Query(7, description="Days to analyze for trends")
) -> DashboardStatus:
    """
    Get current dashboard status.

    Returns high-level metrics and health indicators.
    """
    return get_dashboard_status(days)


@router.get("/trends", response_model=TrendData)
async def get_trends(
    days: int = Query(14, description="Days of trend data")
) -> TrendData:
    """
    Get trend data for charts.

    Returns daily data points for visualization.
    """
    return get_trend_data(days)


@router.get("/verdicts", response_model=VerdictBreakdown)
async def get_verdicts(
    days: int = Query(7, description="Days to analyze")
) -> VerdictBreakdown:
    """
    Get verdict type breakdown.

    Returns counts of each verdict type.
    """
    return get_verdict_breakdown(days)


@router.get("/streams")
async def get_streams(
    days: int = Query(7, description="Days to analyze")
) -> Dict[str, StreamDetail]:
    """
    Get detailed status for each stream.

    Returns DDE, BDV, and ACC individual metrics.
    """
    return get_stream_details(days)


@router.get("/recent", response_model=List[RecentAudit])
async def get_recent(
    limit: int = Query(10, description="Maximum entries")
) -> List[RecentAudit]:
    """
    Get recent audit entries.

    For activity feed display.
    """
    return get_recent_audits(limit)


@router.get("/full", response_model=DashboardData)
async def get_full_dashboard(
    days: int = Query(7, description="Days for statistics"),
    trend_days: int = Query(14, description="Days for trend data")
) -> DashboardData:
    """
    Get complete dashboard data in one request.

    Returns all dashboard components for initial load.
    """
    return get_full_dashboard_data(days, trend_days)


@router.get("/health")
async def health_check() -> Dict[str, Any]:
    """
    Health check endpoint for monitoring.
    """
    status = get_dashboard_status(days=1)

    return {
        "healthy": status.overall_health in [StreamHealthStatus.HEALTHY, StreamHealthStatus.DEGRADED],
        "overall_health": status.overall_health.value,
        "pass_rate": status.overall_pass_rate,
        "timestamp": status.timestamp
    }
