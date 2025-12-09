"""
Verbosity Dashboard API for Admin Interface.

Epic: MD-2491 - [VISIBILITY] Phase 5: Saturation Detection & Auto-Optimization

Provides API endpoints and data structures for the admin dashboard
to display saturation progress, trends, and manual override controls.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from enum import Enum
import json

try:
    from .saturation_detector import VerbosityLevel, VerbosityManager
except ImportError:
    from saturation_detector import VerbosityLevel, VerbosityManager


@dataclass
class TrendPoint:
    """Single point in a trend chart."""
    timestamp: datetime
    value: float
    label: str = ""


@dataclass
class DashboardAlert:
    """Alert for the dashboard."""
    id: str
    severity: str  # info, warning, error
    message: str
    timestamp: datetime
    acknowledged: bool = False


class VerbosityDashboard:
    """
    Dashboard interface for verbosity management.

    Provides all data needed for the admin dashboard including:
    - Current verbosity level indicator
    - Saturation progress bar
    - Novelty trend chart
    - Manual override buttons
    - Quality regression alerts
    """

    def __init__(self, manager: VerbosityManager):
        """
        Initialize dashboard with verbosity manager.

        Args:
            manager: The VerbosityManager to monitor
        """
        self.manager = manager
        self.alerts: List[DashboardAlert] = []
        self.novelty_history: List[TrendPoint] = []
        self._alert_counter = 0

    def get_current_level_indicator(self) -> Dict:
        """
        Get current verbosity level with visual indicator data.

        Returns:
            Dictionary with level info and styling
        """
        level = self.manager.get_current_level()
        level_config = {
            VerbosityLevel.LEARNING: {
                "label": "LEARNING",
                "color": "#FFA500",  # Orange
                "icon": "school",
                "description": "System is actively learning patterns"
            },
            VerbosityLevel.OPTIMIZED: {
                "label": "OPTIMIZED",
                "color": "#4CAF50",  # Green
                "icon": "speed",
                "description": "Learning stabilized, reduced verbosity"
            },
            VerbosityLevel.PRODUCTION: {
                "label": "PRODUCTION",
                "color": "#2196F3",  # Blue
                "icon": "verified",
                "description": "Fully optimized for production use"
            }
        }
        config = level_config[level]
        return {
            "level": level.value,
            **config
        }

    def get_saturation_progress(self) -> Dict:
        """
        Get saturation progress bar data.

        Returns:
            Dictionary with progress percentage and thresholds
        """
        stats = self.manager.saturation_detector.get_stats()
        progress = stats["saturation_progress"]

        return {
            "progress": progress,
            "threshold": self.manager.saturation_detector.threshold * 100,
            "is_saturated": stats["is_saturated"],
            "interaction_count": stats["interaction_count"],
            "min_interactions": self.manager.MIN_INTERACTIONS_FOR_TRANSITION,
            "color": self._get_progress_color(progress)
        }

    def _get_progress_color(self, progress: float) -> str:
        """Get color based on progress level."""
        if progress < 50:
            return "#FFA500"  # Orange - early stages
        elif progress < 80:
            return "#FFEB3B"  # Yellow - progressing
        elif progress < 95:
            return "#8BC34A"  # Light green - almost there
        else:
            return "#4CAF50"  # Green - saturated

    def record_novelty_snapshot(self) -> None:
        """Record current novelty for trend tracking."""
        stats = self.manager.saturation_detector.get_stats()
        self.novelty_history.append(TrendPoint(
            timestamp=datetime.utcnow(),
            value=stats["novelty_score"] * 100,
            label=f"{stats['interaction_count']} interactions"
        ))
        # Keep last 30 days of hourly snapshots
        cutoff = datetime.utcnow() - timedelta(days=30)
        self.novelty_history = [
            p for p in self.novelty_history
            if p.timestamp >= cutoff
        ]

    def get_novelty_trend_chart(self, days: int = 30) -> Dict:
        """
        Get novelty trend data for charting.

        Args:
            days: Number of days of history to return

        Returns:
            Dictionary with chart data
        """
        cutoff = datetime.utcnow() - timedelta(days=days)
        points = [
            p for p in self.novelty_history
            if p.timestamp >= cutoff
        ]

        return {
            "title": "Novelty Trend (Last {} Days)".format(days),
            "y_axis_label": "Novelty %",
            "x_axis_label": "Time",
            "data_points": [
                {
                    "x": p.timestamp.isoformat(),
                    "y": p.value,
                    "label": p.label
                }
                for p in points
            ],
            "threshold_line": (1 - self.manager.saturation_detector.threshold) * 100
        }

    def get_override_buttons(self) -> List[Dict]:
        """
        Get manual override button configurations.

        Returns:
            List of button configurations
        """
        current_level = self.manager.get_current_level()
        buttons = []

        for level in VerbosityLevel:
            enabled = level != current_level
            button = {
                "level": level.value,
                "label": f"Force {level.value.upper()}",
                "enabled": enabled,
                "requires_confirmation": True,
                "warning_message": self._get_override_warning(current_level, level)
            }
            buttons.append(button)

        return buttons

    def _get_override_warning(self, current: VerbosityLevel,
                               target: VerbosityLevel) -> str:
        """Get warning message for override action."""
        if target == VerbosityLevel.LEARNING:
            return "This will increase verbosity and restart pattern learning."
        elif target == VerbosityLevel.OPTIMIZED:
            if current == VerbosityLevel.LEARNING:
                return "Manual transition to OPTIMIZED may miss learning patterns."
            else:
                return "Reverting from PRODUCTION to OPTIMIZED."
        elif target == VerbosityLevel.PRODUCTION:
            return "PRODUCTION mode minimizes verbosity. Ensure system is stable."
        return ""

    def add_alert(self, severity: str, message: str) -> str:
        """
        Add an alert to the dashboard.

        Args:
            severity: Alert severity (info, warning, error)
            message: Alert message

        Returns:
            Alert ID
        """
        self._alert_counter += 1
        alert_id = f"alert_{self._alert_counter}"
        self.alerts.append(DashboardAlert(
            id=alert_id,
            severity=severity,
            message=message,
            timestamp=datetime.utcnow()
        ))
        return alert_id

    def acknowledge_alert(self, alert_id: str) -> bool:
        """
        Acknowledge an alert.

        Args:
            alert_id: ID of alert to acknowledge

        Returns:
            True if alert was found and acknowledged
        """
        for alert in self.alerts:
            if alert.id == alert_id:
                alert.acknowledged = True
                return True
        return False

    def get_alerts(self, include_acknowledged: bool = False) -> List[Dict]:
        """
        Get active alerts.

        Args:
            include_acknowledged: Include acknowledged alerts

        Returns:
            List of alert dictionaries
        """
        alerts = [
            a for a in self.alerts
            if include_acknowledged or not a.acknowledged
        ]
        return [
            {
                "id": a.id,
                "severity": a.severity,
                "message": a.message,
                "timestamp": a.timestamp.isoformat(),
                "acknowledged": a.acknowledged
            }
            for a in alerts
        ]

    def check_for_regression_alerts(self) -> None:
        """Check and create alerts for regression detection."""
        stats = self.manager.regression_detector.get_stats()
        if stats["regression_detected"]:
            self.add_alert(
                "error",
                f"Quality regression detected! {stats['failure_streak']} "
                f"consecutive workflows below baseline ({stats['current_baseline']:.2f})"
            )

    def get_full_dashboard_state(self) -> Dict:
        """
        Get complete dashboard state for rendering.

        Returns:
            Dictionary with all dashboard data
        """
        self.check_for_regression_alerts()

        return {
            "level_indicator": self.get_current_level_indicator(),
            "saturation_progress": self.get_saturation_progress(),
            "novelty_trend": self.get_novelty_trend_chart(),
            "override_buttons": self.get_override_buttons(),
            "alerts": self.get_alerts(),
            "manager_data": self.manager.get_dashboard_data(),
            "last_updated": datetime.utcnow().isoformat()
        }

    def perform_override(self, level_str: str, reason: str) -> Dict:
        """
        Perform a manual override.

        Args:
            level_str: Target level as string
            reason: Admin-provided reason

        Returns:
            Result dictionary
        """
        try:
            level = VerbosityLevel(level_str)
            old_level = self.manager.get_current_level()
            self.manager.force_override(level, reason)

            self.add_alert(
                "info",
                f"Admin override: {old_level.value} → {level.value}. Reason: {reason}"
            )

            return {
                "success": True,
                "previous_level": old_level.value,
                "new_level": level.value,
                "reason": reason
            }
        except ValueError as e:
            return {
                "success": False,
                "error": f"Invalid level: {level_str}"
            }


def create_dashboard(manager: Optional[VerbosityManager] = None) -> VerbosityDashboard:
    """
    Factory function to create a dashboard.

    Args:
        manager: VerbosityManager instance (creates new if None)

    Returns:
        Configured VerbosityDashboard
    """
    try:
        from .saturation_detector import create_learning_system
    except ImportError:
        from saturation_detector import create_learning_system

    if manager is None:
        manager = create_learning_system()
    return VerbosityDashboard(manager)
