"""
Pattern Analyzer Module
========================

AI-powered cross-system pattern analysis for quality data.
Identifies patterns across NCs, CAPAs, audits, and complaints.
"""

import logging
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple


class DataSource(Enum):
    """Quality data sources for pattern analysis."""
    NON_CONFORMANCE = "non_conformance"
    CAPA = "capa"
    AUDIT = "audit"
    COMPLAINT = "complaint"
    DEVIATION = "deviation"
    CHANGE_CONTROL = "change_control"


class PatternType(Enum):
    """Types of quality patterns."""
    RECURRING = "recurring"           # Same issue recurring
    TRENDING = "trending"             # Increasing/decreasing trend
    SEASONAL = "seasonal"             # Time-based patterns
    CORRELATED = "correlated"         # Cross-system correlations
    CLUSTERED = "clustered"           # Grouped by attribute
    ANOMALY = "anomaly"               # Unusual deviations


class TrendDirection(Enum):
    """Trend direction indicators."""
    INCREASING = "increasing"
    DECREASING = "decreasing"
    STABLE = "stable"
    VOLATILE = "volatile"


@dataclass
class QualityEvent:
    """Generic quality event for pattern analysis."""
    id: str
    source: DataSource
    category: str
    severity: str
    created_at: datetime
    description: str
    attributes: Dict[str, Any] = field(default_factory=dict)
    tags: Set[str] = field(default_factory=set)


@dataclass
class Pattern:
    """Identified quality pattern."""
    id: str
    pattern_type: PatternType
    sources: List[DataSource]
    description: str
    confidence: float
    impact_score: float  # 1-10 scale
    frequency: int       # How often pattern occurs
    affected_areas: List[str]
    evidence: List[str]  # Event IDs supporting this pattern
    first_occurrence: datetime
    last_occurrence: datetime
    trend: Optional[TrendDirection] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def priority_score(self) -> float:
        """Calculate priority based on impact, confidence, and frequency."""
        return (self.impact_score * self.confidence * min(self.frequency, 10)) / 10

    @property
    def is_critical(self) -> bool:
        """Check if pattern requires immediate attention."""
        return self.impact_score >= 8 and self.confidence >= 0.8


@dataclass
class TrendAnalysis:
    """Result of trend analysis."""
    direction: TrendDirection
    slope: float
    r_squared: float  # Fit quality
    forecast_next_30_days: float
    confidence: float


class PatternMatcher:
    """Identifies recurring patterns in quality events."""

    def __init__(self, similarity_threshold: float = 0.7):
        self.similarity_threshold = similarity_threshold
        self.pattern_signatures: Dict[str, List[str]] = {}

    def find_similar_events(
        self,
        events: List[QualityEvent]
    ) -> Dict[str, List[QualityEvent]]:
        """Group similar events together."""
        groups = defaultdict(list)

        for event in events:
            # Create signature from key attributes
            signature = self._create_signature(event)
            groups[signature].append(event)

        # Filter to groups with multiple events (recurring)
        return {k: v for k, v in groups.items() if len(v) >= 2}

    def _create_signature(self, event: QualityEvent) -> str:
        """Create a matching signature for an event."""
        # Combine source, category, and key words
        key_words = self._extract_key_words(event.description)
        return f"{event.source.value}:{event.category}:{':'.join(sorted(key_words)[:5])}"

    def _extract_key_words(self, text: str) -> Set[str]:
        """Extract key words from text for matching."""
        # Simple keyword extraction (stop words removed)
        stop_words = {'the', 'a', 'an', 'is', 'was', 'were', 'been', 'being',
                      'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would',
                      'could', 'should', 'may', 'might', 'must', 'shall', 'of',
                      'in', 'to', 'for', 'with', 'on', 'at', 'by', 'from', 'as'}
        
        words = text.lower().split()
        return {w for w in words if len(w) > 3 and w not in stop_words}


class TrendDetector:
    """Detects trends in quality metrics over time."""

    def analyze_trend(
        self,
        events: List[QualityEvent],
        period_days: int = 30
    ) -> TrendAnalysis:
        """
        Analyze trend direction and strength.

        Args:
            events: Quality events to analyze
            period_days: Period for trend calculation

        Returns:
            TrendAnalysis with direction and metrics
        """
        if len(events) < 3:
            return TrendAnalysis(
                direction=TrendDirection.STABLE,
                slope=0.0,
                r_squared=0.0,
                forecast_next_30_days=len(events),
                confidence=0.0
            )

        # Group events by period
        periods = self._group_by_period(events, period_days)
        counts = [len(events) for events in periods.values()]

        if len(counts) < 2:
            return TrendAnalysis(
                direction=TrendDirection.STABLE,
                slope=0.0,
                r_squared=0.0,
                forecast_next_30_days=counts[0] if counts else 0,
                confidence=0.0
            )

        # Calculate trend using linear regression
        n = len(counts)
        x_mean = (n - 1) / 2
        y_mean = sum(counts) / n

        numerator = sum((i - x_mean) * (counts[i] - y_mean) for i in range(n))
        denominator = sum((i - x_mean) ** 2 for i in range(n))

        slope = numerator / denominator if denominator > 0 else 0

        # Calculate R-squared
        ss_tot = sum((y - y_mean) ** 2 for y in counts)
        ss_res = sum((counts[i] - (y_mean + slope * (i - x_mean))) ** 2 for i in range(n))
        r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0

        # Determine direction
        if abs(slope) < 0.1:
            direction = TrendDirection.STABLE
        elif slope > 0:
            direction = TrendDirection.INCREASING
        else:
            direction = TrendDirection.DECREASING

        # Check for volatility
        if n >= 3:
            changes = [counts[i] - counts[i-1] for i in range(1, n)]
            if any(c > 0 for c in changes) and any(c < 0 for c in changes):
                if max(abs(c) for c in changes) > y_mean * 0.5:
                    direction = TrendDirection.VOLATILE

        # Forecast
        forecast = max(0, y_mean + slope * (n + 1 - x_mean))

        return TrendAnalysis(
            direction=direction,
            slope=slope,
            r_squared=max(0, r_squared),
            forecast_next_30_days=forecast,
            confidence=max(0, min(1, abs(r_squared)))
        )

    def _group_by_period(
        self,
        events: List[QualityEvent],
        period_days: int
    ) -> Dict[int, List[QualityEvent]]:
        """Group events by time period."""
        if not events:
            return {}

        sorted_events = sorted(events, key=lambda e: e.created_at)
        start_date = sorted_events[0].created_at

        periods = defaultdict(list)
        for event in sorted_events:
            period_num = (event.created_at - start_date).days // period_days
            periods[period_num].append(event)

        return periods


class CorrelationAnalyzer:
    """Analyzes correlations between different quality data sources."""

    def find_correlations(
        self,
        events: List[QualityEvent],
        time_window_days: int = 7
    ) -> List[Tuple[DataSource, DataSource, float]]:
        """
        Find correlations between different event sources.

        Returns:
            List of (source1, source2, correlation_strength) tuples
        """
        # Group by source
        by_source = defaultdict(list)
        for event in events:
            by_source[event.source].append(event)

        correlations = []
        sources = list(by_source.keys())

        for i, src1 in enumerate(sources):
            for src2 in sources[i+1:]:
                correlation = self._calculate_temporal_correlation(
                    by_source[src1],
                    by_source[src2],
                    time_window_days
                )
                if correlation > 0.3:  # Minimum threshold
                    correlations.append((src1, src2, correlation))

        return sorted(correlations, key=lambda x: x[2], reverse=True)

    def _calculate_temporal_correlation(
        self,
        events1: List[QualityEvent],
        events2: List[QualityEvent],
        window_days: int
    ) -> float:
        """Calculate temporal correlation between two event sets."""
        if not events1 or not events2:
            return 0.0

        # Count events in events2 within window after events1
        correlated_count = 0
        total_count = len(events1)

        for e1 in events1:
            window_end = e1.created_at + timedelta(days=window_days)
            for e2 in events2:
                if e1.created_at <= e2.created_at <= window_end:
                    correlated_count += 1
                    break

        return correlated_count / total_count if total_count > 0 else 0.0


class PatternAnalyzer:
    """
    Main pattern analysis engine.

    Coordinates pattern detection across quality data sources.
    """

    def __init__(self):
        self.pattern_matcher = PatternMatcher()
        self.trend_detector = TrendDetector()
        self.correlation_analyzer = CorrelationAnalyzer()
        self.patterns: Dict[str, Pattern] = {}
        self.events: List[QualityEvent] = []
        self.logger = logging.getLogger("qms-patterns")
        self._configure_logger()

    def _configure_logger(self) -> None:
        """Configure logger."""
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)

    def add_event(self, event: QualityEvent) -> None:
        """Add a quality event for analysis."""
        self.events.append(event)

    def add_events(self, events: List[QualityEvent]) -> None:
        """Add multiple quality events."""
        self.events.extend(events)

    def analyze(self) -> List[Pattern]:
        """
        Run comprehensive pattern analysis.

        Returns:
            List of identified patterns sorted by priority
        """
        import uuid

        patterns = []

        # 1. Find recurring patterns
        recurring = self._find_recurring_patterns()
        patterns.extend(recurring)

        # 2. Detect trends
        trending = self._find_trending_patterns()
        patterns.extend(trending)

        # 3. Find correlations
        correlated = self._find_correlated_patterns()
        patterns.extend(correlated)

        # 4. Cluster analysis
        clustered = self._find_clustered_patterns()
        patterns.extend(clustered)

        # Store patterns
        for pattern in patterns:
            self.patterns[pattern.id] = pattern

        # Sort by priority
        patterns.sort(key=lambda p: p.priority_score, reverse=True)

        self.logger.info(
            f"PATTERN_ANALYSIS_COMPLETE | patterns_found={len(patterns)} | "
            f"critical={sum(1 for p in patterns if p.is_critical)}"
        )

        return patterns

    def _find_recurring_patterns(self) -> List[Pattern]:
        """Find recurring patterns in events."""
        import uuid

        patterns = []
        similar_groups = self.pattern_matcher.find_similar_events(self.events)

        for signature, events in similar_groups.items():
            if len(events) < 2:
                continue

            # Calculate impact based on severity
            severity_weights = {'critical': 10, 'high': 7, 'major': 7, 'medium': 5, 'minor': 3, 'low': 2}
            avg_impact = sum(
                severity_weights.get(e.severity.lower(), 5) for e in events
            ) / len(events)

            pattern = Pattern(
                id=f"PAT-REC-{str(uuid.uuid4())[:8].upper()}",
                pattern_type=PatternType.RECURRING,
                sources=list(set(e.source for e in events)),
                description=f"Recurring issue: {events[0].category} - {len(events)} occurrences",
                confidence=min(0.9, 0.5 + (len(events) * 0.05)),
                impact_score=avg_impact,
                frequency=len(events),
                affected_areas=[events[0].category],
                evidence=[e.id for e in events],
                first_occurrence=min(e.created_at for e in events),
                last_occurrence=max(e.created_at for e in events),
                metadata={"signature": signature}
            )
            patterns.append(pattern)

        return patterns

    def _find_trending_patterns(self) -> List[Pattern]:
        """Find trending patterns by category."""
        import uuid

        patterns = []

        # Group by category
        by_category = defaultdict(list)
        for event in self.events:
            by_category[event.category].append(event)

        for category, events in by_category.items():
            if len(events) < 5:
                continue

            trend = self.trend_detector.analyze_trend(events)

            if trend.direction in [TrendDirection.INCREASING, TrendDirection.VOLATILE]:
                severity_weights = {'critical': 10, 'high': 7, 'major': 7, 'medium': 5, 'minor': 3, 'low': 2}
                avg_impact = sum(
                    severity_weights.get(e.severity.lower(), 5) for e in events
                ) / len(events)

                pattern = Pattern(
                    id=f"PAT-TRD-{str(uuid.uuid4())[:8].upper()}",
                    pattern_type=PatternType.TRENDING,
                    sources=list(set(e.source for e in events)),
                    description=f"{trend.direction.value.capitalize()} trend in {category}",
                    confidence=trend.confidence,
                    impact_score=avg_impact * (1.5 if trend.direction == TrendDirection.INCREASING else 1.2),
                    frequency=len(events),
                    affected_areas=[category],
                    evidence=[e.id for e in events[-10:]],  # Last 10 events
                    first_occurrence=min(e.created_at for e in events),
                    last_occurrence=max(e.created_at for e in events),
                    trend=trend.direction,
                    metadata={
                        "slope": trend.slope,
                        "r_squared": trend.r_squared,
                        "forecast": trend.forecast_next_30_days
                    }
                )
                patterns.append(pattern)

        return patterns

    def _find_correlated_patterns(self) -> List[Pattern]:
        """Find correlated patterns across sources."""
        import uuid

        patterns = []
        correlations = self.correlation_analyzer.find_correlations(self.events)

        for src1, src2, strength in correlations:
            pattern = Pattern(
                id=f"PAT-COR-{str(uuid.uuid4())[:8].upper()}",
                pattern_type=PatternType.CORRELATED,
                sources=[src1, src2],
                description=f"Correlation between {src1.value} and {src2.value} events",
                confidence=strength,
                impact_score=7.0,  # Correlations are generally important
                frequency=1,
                affected_areas=["cross-system"],
                evidence=[],
                first_occurrence=min(e.created_at for e in self.events if e.source in [src1, src2]),
                last_occurrence=max(e.created_at for e in self.events if e.source in [src1, src2]),
                metadata={"correlation_strength": strength}
            )
            patterns.append(pattern)

        return patterns

    def _find_clustered_patterns(self) -> List[Pattern]:
        """Find clustered patterns by attribute."""
        import uuid

        patterns = []

        # Cluster by common attributes
        attribute_clusters = defaultdict(lambda: defaultdict(list))
        for event in self.events:
            for key, value in event.attributes.items():
                if isinstance(value, str):
                    attribute_clusters[key][value].append(event)

        for attr_name, value_clusters in attribute_clusters.items():
            for value, events in value_clusters.items():
                if len(events) >= 3:
                    severity_weights = {'critical': 10, 'high': 7, 'major': 7, 'medium': 5, 'minor': 3, 'low': 2}
                    avg_impact = sum(
                        severity_weights.get(e.severity.lower(), 5) for e in events
                    ) / len(events)

                    pattern = Pattern(
                        id=f"PAT-CLU-{str(uuid.uuid4())[:8].upper()}",
                        pattern_type=PatternType.CLUSTERED,
                        sources=list(set(e.source for e in events)),
                        description=f"Cluster: {len(events)} events with {attr_name}={value}",
                        confidence=min(0.85, 0.4 + (len(events) * 0.05)),
                        impact_score=avg_impact,
                        frequency=len(events),
                        affected_areas=[value],
                        evidence=[e.id for e in events],
                        first_occurrence=min(e.created_at for e in events),
                        last_occurrence=max(e.created_at for e in events),
                        metadata={"cluster_attribute": attr_name, "cluster_value": value}
                    )
                    patterns.append(pattern)

        return patterns

    def get_critical_patterns(self) -> List[Pattern]:
        """Get patterns requiring immediate attention."""
        return [p for p in self.patterns.values() if p.is_critical]

    def get_patterns_by_type(self, pattern_type: PatternType) -> List[Pattern]:
        """Get patterns by type."""
        return [p for p in self.patterns.values() if p.pattern_type == pattern_type]

    def get_summary(self) -> Dict[str, Any]:
        """Get analysis summary."""
        return {
            "total_events_analyzed": len(self.events),
            "patterns_identified": len(self.patterns),
            "critical_patterns": len(self.get_critical_patterns()),
            "by_type": {
                pt.value: len(self.get_patterns_by_type(pt))
                for pt in PatternType
            },
            "top_patterns": [
                {"id": p.id, "description": p.description, "priority": p.priority_score}
                for p in sorted(self.patterns.values(), key=lambda x: x.priority_score, reverse=True)[:5]
            ]
        }
