"""
Trace Viewer - Execution Visualization Component
EPIC: MD-3013 - Resilient Execution & Observability Grid
AC-5: TraceViewer component for execution visualization

Provides Python-based visualization of distributed traces with
multiple export formats (JSON, HTML, PNG) for debugging and audit.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any, Callable
import json
import html
import time


class ExportFormat(Enum):
    """Supported export formats for trace visualization."""
    JSON = "json"
    HTML = "html"
    TEXT = "text"
    MARKDOWN = "markdown"


class SpanDisplayStatus(Enum):
    """Display status for spans in visualization."""
    SUCCESS = "success"
    ERROR = "error"
    WARNING = "warning"
    PENDING = "pending"


@dataclass
class SpanView:
    """Visualization-ready span representation."""
    span_id: str
    trace_id: str
    name: str
    service: str
    start_time: datetime
    end_time: Optional[datetime]
    duration_ms: float
    status: SpanDisplayStatus
    parent_id: Optional[str]
    children: List["SpanView"] = field(default_factory=list)
    attributes: Dict[str, Any] = field(default_factory=dict)
    events: List[Dict[str, Any]] = field(default_factory=list)
    depth: int = 0


@dataclass
class TraceViewConfig:
    """Configuration for trace visualization."""
    show_timestamps: bool = True
    show_durations: bool = True
    show_attributes: bool = True
    show_events: bool = False
    max_depth: int = 10
    time_format: str = "%H:%M:%S.%f"
    color_scheme: str = "default"
    collapse_depth: int = 3  # Auto-collapse spans deeper than this


@dataclass
class TraceStatistics:
    """Statistical summary of a trace."""
    total_spans: int
    root_spans: int
    max_depth: int
    total_duration_ms: float
    error_count: int
    warning_count: int
    services: List[str]
    slowest_span: Optional[str]
    slowest_duration_ms: float


class TraceViewer:
    """
    Visualization engine for distributed execution traces.

    Provides multiple export formats for trace data:
    - JSON: Machine-readable format for processing
    - HTML: Interactive browser-based visualization
    - TEXT: Terminal-friendly ASCII representation
    - MARKDOWN: Documentation-friendly format

    Usage:
        viewer = TraceViewer(config=TraceViewConfig())

        # Load trace data
        viewer.load_trace(trace_data)

        # Export to different formats
        html_output = viewer.export(ExportFormat.HTML)
        json_output = viewer.export(ExportFormat.JSON)

        # Get statistics
        stats = viewer.get_statistics()
    """

    def __init__(self, config: Optional[TraceViewConfig] = None):
        """
        Initialize trace viewer with configuration.

        Args:
            config: Visualization configuration (uses defaults if None)
        """
        self.config = config or TraceViewConfig()
        self._spans: Dict[str, SpanView] = {}
        self._root_spans: List[str] = []
        self._trace_id: Optional[str] = None
        self._loaded_at: Optional[datetime] = None

    def load_trace(self, trace_data: Dict[str, Any]) -> None:
        """
        Load trace data for visualization.

        Args:
            trace_data: Trace data containing spans and metadata

        Expected format:
            {
                "trace_id": "abc123",
                "spans": [
                    {
                        "span_id": "span1",
                        "name": "operation",
                        "start_time": "2024-01-01T00:00:00Z",
                        "end_time": "2024-01-01T00:00:01Z",
                        "status": "ok",
                        "parent_span_id": null,
                        "attributes": {},
                        "events": []
                    }
                ]
            }
        """
        self._spans.clear()
        self._root_spans.clear()

        self._trace_id = trace_data.get("trace_id")
        self._loaded_at = datetime.utcnow()

        # Parse spans
        for span_data in trace_data.get("spans", []):
            span_view = self._parse_span(span_data)
            self._spans[span_view.span_id] = span_view

            if span_view.parent_id is None:
                self._root_spans.append(span_view.span_id)

        # Build hierarchy
        self._build_hierarchy()

        # Calculate depths
        for root_id in self._root_spans:
            self._calculate_depth(root_id, 0)

    def _parse_span(self, span_data: Dict[str, Any]) -> SpanView:
        """Parse raw span data into SpanView."""
        start_time = self._parse_timestamp(span_data.get("start_time"))
        end_time = self._parse_timestamp(span_data.get("end_time"))

        duration_ms = 0.0
        if start_time and end_time:
            duration_ms = (end_time - start_time).total_seconds() * 1000

        status = self._map_status(span_data.get("status", "ok"))

        return SpanView(
            span_id=span_data.get("span_id", ""),
            trace_id=span_data.get("trace_id", self._trace_id or ""),
            name=span_data.get("name", "unknown"),
            service=span_data.get("service", span_data.get("attributes", {}).get("service.name", "unknown")),
            start_time=start_time or datetime.utcnow(),
            end_time=end_time,
            duration_ms=duration_ms,
            status=status,
            parent_id=span_data.get("parent_span_id"),
            attributes=span_data.get("attributes", {}),
            events=span_data.get("events", [])
        )

    def _parse_timestamp(self, ts: Any) -> Optional[datetime]:
        """Parse timestamp from various formats."""
        if ts is None:
            return None
        if isinstance(ts, datetime):
            return ts
        if isinstance(ts, (int, float)):
            return datetime.fromtimestamp(ts / 1000 if ts > 1e12 else ts)
        if isinstance(ts, str):
            try:
                return datetime.fromisoformat(ts.replace("Z", "+00:00"))
            except ValueError:
                return None
        return None

    def _map_status(self, status: str) -> SpanDisplayStatus:
        """Map span status to display status."""
        status_lower = str(status).lower()
        if status_lower in ("ok", "success", "completed"):
            return SpanDisplayStatus.SUCCESS
        if status_lower in ("error", "failed", "exception"):
            return SpanDisplayStatus.ERROR
        if status_lower in ("warning", "timeout"):
            return SpanDisplayStatus.WARNING
        return SpanDisplayStatus.PENDING

    def _build_hierarchy(self) -> None:
        """Build parent-child relationships between spans."""
        for span in self._spans.values():
            if span.parent_id and span.parent_id in self._spans:
                parent = self._spans[span.parent_id]
                parent.children.append(span)

    def _calculate_depth(self, span_id: str, depth: int) -> None:
        """Calculate depth for span and children recursively."""
        if span_id not in self._spans:
            return

        span = self._spans[span_id]
        span.depth = depth

        for child in span.children:
            self._calculate_depth(child.span_id, depth + 1)

    def export(self, format: ExportFormat = ExportFormat.HTML) -> str:
        """
        Export trace visualization in specified format.

        Args:
            format: Export format (JSON, HTML, TEXT, MARKDOWN)

        Returns:
            Formatted string representation of the trace
        """
        if format == ExportFormat.JSON:
            return self._export_json()
        elif format == ExportFormat.HTML:
            return self._export_html()
        elif format == ExportFormat.TEXT:
            return self._export_text()
        elif format == ExportFormat.MARKDOWN:
            return self._export_markdown()
        else:
            raise ValueError(f"Unsupported export format: {format}")

    def _export_json(self) -> str:
        """Export trace as JSON."""
        data = {
            "trace_id": self._trace_id,
            "loaded_at": self._loaded_at.isoformat() if self._loaded_at else None,
            "statistics": self._stats_to_dict(self.get_statistics()),
            "spans": [self._span_to_dict(self._spans[sid]) for sid in self._root_spans]
        }
        return json.dumps(data, indent=2, default=str)

    def _span_to_dict(self, span: SpanView) -> Dict[str, Any]:
        """Convert span to dictionary for JSON export."""
        return {
            "span_id": span.span_id,
            "name": span.name,
            "service": span.service,
            "duration_ms": span.duration_ms,
            "status": span.status.value,
            "depth": span.depth,
            "attributes": span.attributes,
            "events": span.events,
            "children": [self._span_to_dict(child) for child in span.children]
        }

    def _stats_to_dict(self, stats: "TraceStatistics") -> Dict[str, Any]:
        """Convert statistics to dictionary."""
        return {
            "total_spans": stats.total_spans,
            "root_spans": stats.root_spans,
            "max_depth": stats.max_depth,
            "total_duration_ms": stats.total_duration_ms,
            "error_count": stats.error_count,
            "warning_count": stats.warning_count,
            "services": stats.services,
            "slowest_span": stats.slowest_span,
            "slowest_duration_ms": stats.slowest_duration_ms
        }

    def _export_html(self) -> str:
        """Export trace as interactive HTML."""
        stats = self.get_statistics()

        html_content = f'''<!DOCTYPE html>
<html>
<head>
    <title>Trace View: {html.escape(self._trace_id or "Unknown")}</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; margin: 20px; background: #f5f5f5; }}
        .trace-container {{ background: white; border-radius: 8px; padding: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        .trace-header {{ border-bottom: 1px solid #eee; padding-bottom: 15px; margin-bottom: 20px; }}
        .trace-header h1 {{ margin: 0; font-size: 24px; color: #333; }}
        .trace-header .trace-id {{ color: #666; font-size: 14px; margin-top: 5px; }}
        .stats-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 15px; margin-bottom: 20px; }}
        .stat-box {{ background: #f8f9fa; padding: 15px; border-radius: 6px; text-align: center; }}
        .stat-box .value {{ font-size: 24px; font-weight: bold; color: #333; }}
        .stat-box .label {{ font-size: 12px; color: #666; margin-top: 5px; }}
        .span {{ margin: 5px 0; border-left: 3px solid #ddd; padding-left: 15px; }}
        .span.success {{ border-left-color: #28a745; }}
        .span.error {{ border-left-color: #dc3545; }}
        .span.warning {{ border-left-color: #ffc107; }}
        .span.pending {{ border-left-color: #6c757d; }}
        .span-header {{ display: flex; align-items: center; gap: 10px; padding: 8px 0; cursor: pointer; }}
        .span-name {{ font-weight: 500; color: #333; }}
        .span-service {{ font-size: 12px; color: #666; background: #eee; padding: 2px 8px; border-radius: 3px; }}
        .span-duration {{ font-size: 12px; color: #999; margin-left: auto; }}
        .span-children {{ margin-left: 20px; }}
        .collapsible {{ cursor: pointer; }}
        .collapsed .span-children {{ display: none; }}
    </style>
</head>
<body>
    <div class="trace-container">
        <div class="trace-header">
            <h1>Execution Trace</h1>
            <div class="trace-id">Trace ID: {html.escape(self._trace_id or "N/A")}</div>
        </div>
        <div class="stats-grid">
            <div class="stat-box">
                <div class="value">{stats.total_spans}</div>
                <div class="label">Total Spans</div>
            </div>
            <div class="stat-box">
                <div class="value">{stats.total_duration_ms:.1f}ms</div>
                <div class="label">Total Duration</div>
            </div>
            <div class="stat-box">
                <div class="value">{stats.error_count}</div>
                <div class="label">Errors</div>
            </div>
            <div class="stat-box">
                <div class="value">{len(stats.services)}</div>
                <div class="label">Services</div>
            </div>
        </div>
        <div class="spans-container">
            {"".join(self._render_span_html(self._spans[sid]) for sid in self._root_spans)}
        </div>
    </div>
    <script>
        document.querySelectorAll('.collapsible').forEach(el => {{
            el.addEventListener('click', () => el.classList.toggle('collapsed'));
        }});
    </script>
</body>
</html>'''
        return html_content

    def _render_span_html(self, span: SpanView) -> str:
        """Render single span as HTML."""
        status_class = span.status.value
        has_children = len(span.children) > 0
        collapsible_class = "collapsible" if has_children else ""

        children_html = ""
        if has_children:
            children_html = f'''<div class="span-children">
                {"".join(self._render_span_html(child) for child in span.children)}
            </div>'''

        return f'''<div class="span {status_class} {collapsible_class}">
            <div class="span-header">
                <span class="span-name">{html.escape(span.name)}</span>
                <span class="span-service">{html.escape(span.service)}</span>
                <span class="span-duration">{span.duration_ms:.2f}ms</span>
            </div>
            {children_html}
        </div>'''

    def _export_text(self) -> str:
        """Export trace as ASCII text."""
        lines = [
            f"═══════════════════════════════════════════════════════════════",
            f"  TRACE VIEWER - {self._trace_id or 'Unknown Trace'}",
            f"═══════════════════════════════════════════════════════════════",
            ""
        ]

        stats = self.get_statistics()
        lines.extend([
            f"  Total Spans: {stats.total_spans}  |  Duration: {stats.total_duration_ms:.1f}ms  |  Errors: {stats.error_count}",
            f"  Services: {', '.join(stats.services)}",
            "",
            "───────────────────────────────────────────────────────────────",
            ""
        ])

        for root_id in self._root_spans:
            lines.extend(self._render_span_text(self._spans[root_id]))

        lines.append("═══════════════════════════════════════════════════════════════")
        return "\n".join(lines)

    def _render_span_text(self, span: SpanView, prefix: str = "") -> List[str]:
        """Render span as text lines."""
        status_char = {"success": "✓", "error": "✗", "warning": "⚠", "pending": "○"}
        char = status_char.get(span.status.value, "○")

        lines = [f"{prefix}{char} {span.name} [{span.service}] {span.duration_ms:.2f}ms"]

        child_prefix = prefix + "  │ "
        for i, child in enumerate(span.children):
            is_last = i == len(span.children) - 1
            child_prefix = prefix + ("  └─" if is_last else "  ├─")
            next_prefix = prefix + ("    " if is_last else "  │ ")
            lines.append(f"{child_prefix} {child.name} [{child.service}] {child.duration_ms:.2f}ms")
            for grandchild in child.children:
                lines.extend(self._render_span_text(grandchild, next_prefix))

        return lines

    def _export_markdown(self) -> str:
        """Export trace as Markdown."""
        stats = self.get_statistics()

        lines = [
            f"# Trace: {self._trace_id or 'Unknown'}",
            "",
            "## Summary",
            "",
            f"| Metric | Value |",
            f"|--------|-------|",
            f"| Total Spans | {stats.total_spans} |",
            f"| Total Duration | {stats.total_duration_ms:.1f}ms |",
            f"| Errors | {stats.error_count} |",
            f"| Services | {', '.join(stats.services)} |",
            "",
            "## Span Hierarchy",
            ""
        ]

        for root_id in self._root_spans:
            lines.extend(self._render_span_markdown(self._spans[root_id]))

        return "\n".join(lines)

    def _render_span_markdown(self, span: SpanView, depth: int = 0) -> List[str]:
        """Render span as Markdown."""
        indent = "  " * depth
        status_emoji = {"success": "✅", "error": "❌", "warning": "⚠️", "pending": "⏳"}
        emoji = status_emoji.get(span.status.value, "⏳")

        lines = [f"{indent}- {emoji} **{span.name}** `{span.service}` _{span.duration_ms:.2f}ms_"]

        for child in span.children:
            lines.extend(self._render_span_markdown(child, depth + 1))

        return lines

    def get_statistics(self) -> TraceStatistics:
        """
        Calculate trace statistics.

        Returns:
            TraceStatistics with summary information
        """
        if not self._spans:
            return TraceStatistics(
                total_spans=0,
                root_spans=0,
                max_depth=0,
                total_duration_ms=0.0,
                error_count=0,
                warning_count=0,
                services=[],
                slowest_span=None,
                slowest_duration_ms=0.0
            )

        services = set()
        error_count = 0
        warning_count = 0
        max_depth = 0
        slowest_span = None
        slowest_duration = 0.0
        total_duration = 0.0

        for span in self._spans.values():
            services.add(span.service)
            max_depth = max(max_depth, span.depth)

            if span.status == SpanDisplayStatus.ERROR:
                error_count += 1
            elif span.status == SpanDisplayStatus.WARNING:
                warning_count += 1

            if span.duration_ms > slowest_duration:
                slowest_duration = span.duration_ms
                slowest_span = span.name

            # Sum root span durations for total
            if span.parent_id is None:
                total_duration += span.duration_ms

        return TraceStatistics(
            total_spans=len(self._spans),
            root_spans=len(self._root_spans),
            max_depth=max_depth,
            total_duration_ms=total_duration,
            error_count=error_count,
            warning_count=warning_count,
            services=sorted(services),
            slowest_span=slowest_span,
            slowest_duration_ms=slowest_duration
        )

    def find_slow_spans(self, threshold_ms: float = 1000.0) -> List[SpanView]:
        """
        Find spans exceeding duration threshold.

        Args:
            threshold_ms: Duration threshold in milliseconds

        Returns:
            List of spans exceeding threshold, sorted by duration
        """
        slow_spans = [
            span for span in self._spans.values()
            if span.duration_ms >= threshold_ms
        ]
        return sorted(slow_spans, key=lambda s: s.duration_ms, reverse=True)

    def find_errors(self) -> List[SpanView]:
        """
        Find all spans with error status.

        Returns:
            List of error spans
        """
        return [
            span for span in self._spans.values()
            if span.status == SpanDisplayStatus.ERROR
        ]

    def get_critical_path(self) -> List[SpanView]:
        """
        Identify critical path (longest execution path).

        Returns:
            List of spans on the critical path
        """
        if not self._root_spans:
            return []

        def find_longest_path(span_id: str) -> List[SpanView]:
            span = self._spans.get(span_id)
            if not span:
                return []

            if not span.children:
                return [span]

            longest_child_path = []
            for child in span.children:
                child_path = find_longest_path(child.span_id)
                if sum(s.duration_ms for s in child_path) > sum(s.duration_ms for s in longest_child_path):
                    longest_child_path = child_path

            return [span] + longest_child_path

        all_paths = [find_longest_path(root_id) for root_id in self._root_spans]
        return max(all_paths, key=lambda p: sum(s.duration_ms for s in p)) if all_paths else []


def create_viewer(trace_data: Dict[str, Any], config: Optional[TraceViewConfig] = None) -> TraceViewer:
    """
    Factory function to create and initialize a TraceViewer.

    Args:
        trace_data: Trace data to visualize
        config: Optional configuration

    Returns:
        Initialized TraceViewer instance
    """
    viewer = TraceViewer(config=config)
    viewer.load_trace(trace_data)
    return viewer


__all__ = [
    "TraceViewer",
    "TraceViewConfig",
    "TraceStatistics",
    "SpanView",
    "SpanDisplayStatus",
    "ExportFormat",
    "create_viewer"
]
