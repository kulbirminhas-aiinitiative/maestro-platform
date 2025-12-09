#!/usr/bin/env python3
"""
Dashboard API: Provides a monitoring dashboard interface.

This module handles:
- Dashboard data aggregation
- Real-time metrics display
- Multi-modal visualization data
- Status overview and notifications
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional
import uuid

logger = logging.getLogger(__name__)


class WidgetType(Enum):
    """Types of dashboard widgets."""
    METRIC = "metric"
    CHART = "chart"
    TABLE = "table"
    STATUS = "status"
    ALERT = "alert"
    LOG = "log"
    PROGRESS = "progress"


class ChartType(Enum):
    """Types of charts."""
    LINE = "line"
    BAR = "bar"
    PIE = "pie"
    AREA = "area"
    GAUGE = "gauge"


class NotificationType(Enum):
    """Types of notifications."""
    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"


@dataclass
class Widget:
    """A dashboard widget configuration."""
    widget_id: str
    name: str
    widget_type: WidgetType
    config: Dict[str, Any]
    data_source: Optional[str] = None
    refresh_interval: int = 30  # seconds
    position: Dict[str, int] = field(default_factory=dict)  # x, y, w, h


@dataclass
class Dashboard:
    """A dashboard configuration."""
    dashboard_id: str
    name: str
    description: str
    widgets: List[Widget]
    layout: str = "grid"  # grid, free
    refresh_interval: int = 30
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class Notification:
    """A notification message."""
    notification_id: str
    notification_type: NotificationType
    title: str
    message: str
    read: bool = False
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class DashboardData:
    """Data for rendering a dashboard."""
    dashboard_id: str
    widgets_data: Dict[str, Any]
    timestamp: datetime
    notifications: List[Notification]


class DashboardService:
    """
    Provides dashboard functionality.

    Implements:
    - dashboard: Create and manage dashboards
    - progress_indication: Show operation progress
    - notifications: Manage user notifications
    - multi_modal: Support different visualization modes
    """

    def __init__(self):
        """Initialize the dashboard service."""
        self._dashboards: Dict[str, Dashboard] = {}
        self._notifications: List[Notification] = []
        self._data_sources: Dict[str, Callable] = {}
        self._metrics_cache: Dict[str, Any] = {}

        # Create default dashboard
        self._create_default_dashboard()

    def _create_default_dashboard(self) -> None:
        """Create the default dashboard."""
        widgets = [
            Widget(
                widget_id="system-health",
                name="System Health",
                widget_type=WidgetType.STATUS,
                config={"show_details": True},
                position={"x": 0, "y": 0, "w": 3, "h": 2}
            ),
            Widget(
                widget_id="gap-count",
                name="Gap Count",
                widget_type=WidgetType.METRIC,
                config={"format": "number", "threshold": 20},
                position={"x": 3, "y": 0, "w": 2, "h": 1}
            ),
            Widget(
                widget_id="test-results",
                name="Test Results",
                widget_type=WidgetType.CHART,
                config={"chart_type": ChartType.PIE.value},
                position={"x": 5, "y": 0, "w": 2, "h": 2}
            ),
            Widget(
                widget_id="recent-alerts",
                name="Recent Alerts",
                widget_type=WidgetType.ALERT,
                config={"limit": 5},
                position={"x": 0, "y": 2, "w": 4, "h": 2}
            ),
            Widget(
                widget_id="execution-progress",
                name="Execution Progress",
                widget_type=WidgetType.PROGRESS,
                config={"show_percentage": True},
                position={"x": 4, "y": 2, "w": 3, "h": 1}
            ),
            Widget(
                widget_id="activity-log",
                name="Activity Log",
                widget_type=WidgetType.LOG,
                config={"limit": 10},
                position={"x": 0, "y": 4, "w": 7, "h": 2}
            ),
        ]

        dashboard = Dashboard(
            dashboard_id="default",
            name="Maestro Overview",
            description="Main dashboard showing system status and metrics",
            widgets=widgets
        )

        self._dashboards[dashboard.dashboard_id] = dashboard

    def create_dashboard(
        self,
        name: str,
        description: str,
        widgets: List[Dict[str, Any]]
    ) -> Dashboard:
        """
        Create a new dashboard.

        Implements dashboard creation.
        """
        widget_objects = []
        for w in widgets:
            widget = Widget(
                widget_id=str(uuid.uuid4()),
                name=w['name'],
                widget_type=WidgetType(w['type']),
                config=w.get('config', {}),
                data_source=w.get('data_source'),
                position=w.get('position', {})
            )
            widget_objects.append(widget)

        dashboard = Dashboard(
            dashboard_id=str(uuid.uuid4()),
            name=name,
            description=description,
            widgets=widget_objects
        )

        self._dashboards[dashboard.dashboard_id] = dashboard
        logger.info(f"Dashboard created: {name}")

        return dashboard

    def get_dashboard(self, dashboard_id: str) -> Optional[Dashboard]:
        """Get a dashboard by ID."""
        return self._dashboards.get(dashboard_id)

    def get_dashboard_data(
        self,
        dashboard_id: str
    ) -> Optional[DashboardData]:
        """
        Get data for rendering a dashboard.

        Aggregates data from all widgets' data sources.
        """
        dashboard = self._dashboards.get(dashboard_id)
        if not dashboard:
            return None

        widgets_data = {}
        for widget in dashboard.widgets:
            data = self._get_widget_data(widget)
            widgets_data[widget.widget_id] = data

        return DashboardData(
            dashboard_id=dashboard_id,
            widgets_data=widgets_data,
            timestamp=datetime.utcnow(),
            notifications=self.get_unread_notifications()
        )

    def _get_widget_data(self, widget: Widget) -> Dict[str, Any]:
        """Get data for a specific widget."""
        # Check if there's a registered data source
        if widget.data_source and widget.data_source in self._data_sources:
            source_fn = self._data_sources[widget.data_source]
            try:
                return source_fn()
            except Exception as e:
                logger.error(f"Data source error: {e}")

        # Return mock data based on widget type
        return self._get_mock_widget_data(widget)

    def _get_mock_widget_data(self, widget: Widget) -> Dict[str, Any]:
        """Get mock data for widget demonstration."""
        if widget.widget_type == WidgetType.STATUS:
            return {
                "status": "healthy",
                "uptime": "99.9%",
                "components": {
                    "quality_fabric": "healthy",
                    "jira_api": "healthy",
                    "confluence": "healthy"
                }
            }

        elif widget.widget_type == WidgetType.METRIC:
            return {
                "value": 15,
                "trend": "down",
                "change": -5
            }

        elif widget.widget_type == WidgetType.CHART:
            return {
                "labels": ["Passed", "Failed", "Skipped"],
                "values": [45, 3, 2],
                "colors": ["#22c55e", "#ef4444", "#f59e0b"]
            }

        elif widget.widget_type == WidgetType.ALERT:
            return {
                "alerts": [
                    {"level": "warning", "message": "Coverage below 80%", "time": "5m ago"},
                    {"level": "info", "message": "Test suite completed", "time": "10m ago"}
                ]
            }

        elif widget.widget_type == WidgetType.PROGRESS:
            return {
                "current": 7,
                "total": 10,
                "percentage": 70,
                "label": "Phase 7 of 10"
            }

        elif widget.widget_type == WidgetType.LOG:
            return {
                "entries": [
                    {"time": "14:30:00", "level": "INFO", "message": "Test execution started"},
                    {"time": "14:30:15", "level": "INFO", "message": "Running unit tests"},
                    {"time": "14:30:45", "level": "INFO", "message": "45 tests passed"}
                ]
            }

        return {}

    def register_data_source(
        self,
        name: str,
        source_fn: Callable[[], Dict[str, Any]]
    ) -> None:
        """Register a data source function."""
        self._data_sources[name] = source_fn
        logger.info(f"Data source registered: {name}")

    def send_notification(
        self,
        title: str,
        message: str,
        notification_type: NotificationType = NotificationType.INFO
    ) -> Notification:
        """
        Send a notification.

        Implements notifications.
        """
        notification = Notification(
            notification_id=str(uuid.uuid4()),
            notification_type=notification_type,
            title=title,
            message=message
        )

        self._notifications.append(notification)

        # Keep only last 100 notifications
        if len(self._notifications) > 100:
            self._notifications = self._notifications[-100:]

        logger.info(f"Notification sent: {title}")
        return notification

    def get_notifications(self, limit: int = 20) -> List[Notification]:
        """Get recent notifications."""
        return list(reversed(self._notifications[-limit:]))

    def get_unread_notifications(self) -> List[Notification]:
        """Get unread notifications."""
        return [n for n in self._notifications if not n.read]

    def mark_notification_read(self, notification_id: str) -> bool:
        """Mark a notification as read."""
        for n in self._notifications:
            if n.notification_id == notification_id:
                n.read = True
                return True
        return False

    def mark_all_read(self) -> int:
        """Mark all notifications as read."""
        count = 0
        for n in self._notifications:
            if not n.read:
                n.read = True
                count += 1
        return count

    def update_progress(
        self,
        task_id: str,
        current: int,
        total: int,
        message: str = ""
    ) -> Dict[str, Any]:
        """
        Update progress for a task.

        Implements progress_indication.
        """
        progress = {
            "task_id": task_id,
            "current": current,
            "total": total,
            "percentage": (current / total * 100) if total > 0 else 0,
            "message": message,
            "timestamp": datetime.utcnow().isoformat()
        }

        self._metrics_cache[f"progress_{task_id}"] = progress
        return progress

    def get_progress(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get progress for a task."""
        return self._metrics_cache.get(f"progress_{task_id}")

    def get_visualization_data(
        self,
        data_type: str,
        chart_type: ChartType = ChartType.LINE,
        time_range_minutes: int = 60
    ) -> Dict[str, Any]:
        """
        Get data formatted for visualization.

        Implements multi_modal visualization support.
        """
        # Mock time series data
        now = datetime.utcnow()
        labels = []
        values = []

        for i in range(time_range_minutes, 0, -5):
            time_point = now - timedelta(minutes=i)
            labels.append(time_point.strftime("%H:%M"))
            values.append(50 + (i % 20))  # Mock value

        return {
            "type": chart_type.value,
            "labels": labels,
            "datasets": [{
                "label": data_type,
                "data": values
            }],
            "options": {
                "responsive": True,
                "animation": True
            }
        }

    def list_dashboards(self) -> List[Dashboard]:
        """List all dashboards."""
        return list(self._dashboards.values())

    def delete_dashboard(self, dashboard_id: str) -> bool:
        """Delete a dashboard."""
        if dashboard_id in self._dashboards:
            del self._dashboards[dashboard_id]
            return True
        return False


# Factory function
def create_dashboard_service() -> DashboardService:
    """Create a new DashboardService instance."""
    return DashboardService()
