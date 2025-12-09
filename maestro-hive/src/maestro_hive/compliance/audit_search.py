#!/usr/bin/env python3
"""
Audit Search: Searchable interface for audit logs.

Provides full-text and structured search across audit logs.
"""

import json
import re
import logging
from dataclasses import dataclass, asdict, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from .audit_logger import AuditLogger, AuditEvent, AuditEventType

logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    """A search result."""
    event: AuditEvent
    score: float
    highlights: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            'event': self.event.to_dict(),
            'score': self.score,
            'highlights': self.highlights
        }


@dataclass
class SearchQuery:
    """A search query."""
    text: Optional[str] = None
    event_types: Optional[List[AuditEventType]] = None
    actors: Optional[List[str]] = None
    resources: Optional[List[str]] = None
    since: Optional[str] = None
    until: Optional[str] = None
    limit: int = 100
    offset: int = 0


class AuditSearcher:
    """Search interface for audit logs."""

    def __init__(self, audit_logger: Optional[AuditLogger] = None):
        self.audit_logger = audit_logger or AuditLogger()
        self._index: Dict[str, List[str]] = {}  # Simple inverted index

    def search(self, query: SearchQuery) -> List[SearchResult]:
        """
        Search audit logs.

        Args:
            query: Search query parameters

        Returns:
            List of SearchResults
        """
        # Get base events from audit logger
        events = self.audit_logger.query(
            since=query.since,
            until=query.until,
            limit=query.limit * 10  # Get extra for filtering
        )

        results = []

        for event in events:
            # Apply filters
            if query.event_types and event.event_type not in query.event_types:
                continue
            if query.actors and event.actor not in query.actors:
                continue
            if query.resources:
                if not any(r in (event.resource or '') for r in query.resources):
                    continue

            # Text search
            score = 1.0
            highlights = []

            if query.text:
                text_lower = query.text.lower()
                searchable = f"{event.message} {event.actor} {event.resource}"
                searchable_lower = searchable.lower()

                if text_lower not in searchable_lower:
                    continue

                # Calculate score based on match quality
                score = self._calculate_score(text_lower, event)
                highlights = self._find_highlights(query.text, event)

            results.append(SearchResult(
                event=event,
                score=score,
                highlights=highlights
            ))

        # Sort by score
        results.sort(key=lambda r: r.score, reverse=True)

        # Apply pagination
        return results[query.offset:query.offset + query.limit]

    def aggregate(
        self,
        field: str,
        since: Optional[str] = None,
        until: Optional[str] = None
    ) -> Dict[str, int]:
        """
        Aggregate events by field.

        Args:
            field: Field to aggregate by (event_type, actor, resource)
            since: Start time
            until: End time

        Returns:
            Counts by field value
        """
        events = self.audit_logger.query(since=since, until=until, limit=10000)

        counts: Dict[str, int] = {}

        for event in events:
            if field == 'event_type':
                key = event.event_type.value
            elif field == 'actor':
                key = event.actor or 'unknown'
            elif field == 'resource':
                key = event.resource or 'none'
            elif field == 'outcome':
                key = event.outcome
            else:
                continue

            counts[key] = counts.get(key, 0) + 1

        return dict(sorted(counts.items(), key=lambda x: x[1], reverse=True))

    def timeline(
        self,
        since: str,
        until: Optional[str] = None,
        interval: str = 'hour'
    ) -> List[Dict[str, Any]]:
        """
        Get event timeline.

        Args:
            since: Start time
            until: End time
            interval: Aggregation interval (hour, day, week)

        Returns:
            Timeline data points
        """
        events = self.audit_logger.query(since=since, until=until, limit=10000)

        buckets: Dict[str, int] = {}

        for event in events:
            # Parse timestamp
            ts = datetime.fromisoformat(event.timestamp.replace('Z', '+00:00').replace('+00:00', ''))

            # Create bucket key based on interval
            if interval == 'hour':
                key = ts.strftime('%Y-%m-%d %H:00')
            elif interval == 'day':
                key = ts.strftime('%Y-%m-%d')
            elif interval == 'week':
                key = ts.strftime('%Y-W%W')
            else:
                key = ts.strftime('%Y-%m-%d')

            buckets[key] = buckets.get(key, 0) + 1

        return [
            {'timestamp': k, 'count': v}
            for k, v in sorted(buckets.items())
        ]

    def suggest(self, prefix: str, field: str, limit: int = 10) -> List[str]:
        """
        Suggest completions for a search term.

        Args:
            prefix: Prefix to complete
            field: Field to suggest from
            limit: Maximum suggestions

        Returns:
            List of suggestions
        """
        events = self.audit_logger.query(limit=1000)

        values = set()

        for event in events:
            if field == 'actor' and event.actor:
                values.add(event.actor)
            elif field == 'resource' and event.resource:
                values.add(event.resource)

        prefix_lower = prefix.lower()
        suggestions = [v for v in values if v.lower().startswith(prefix_lower)]

        return sorted(suggestions)[:limit]

    def _calculate_score(self, query: str, event: AuditEvent) -> float:
        """Calculate relevance score."""
        score = 0.0

        # Exact match in message
        if query in event.message.lower():
            score += 2.0

        # Match in actor
        if event.actor and query in event.actor.lower():
            score += 1.5

        # Match in resource
        if event.resource and query in event.resource.lower():
            score += 1.0

        return score

    def _find_highlights(self, query: str, event: AuditEvent) -> List[str]:
        """Find highlight snippets."""
        highlights = []
        pattern = re.compile(f'(.{{0,30}}{re.escape(query)}.{{0,30}})', re.IGNORECASE)

        for text in [event.message, event.actor or '', event.resource or '']:
            matches = pattern.findall(text)
            highlights.extend(matches)

        return highlights[:3]


def get_audit_searcher(**kwargs) -> AuditSearcher:
    """Get audit searcher instance."""
    return AuditSearcher(**kwargs)
