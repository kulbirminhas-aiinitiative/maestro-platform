#!/usr/bin/env python3
"""Tests for audit_search module."""

import pytest
import tempfile
from datetime import datetime, timedelta

from maestro_hive.compliance.audit_search import (
    AuditSearcher,
    SearchQuery,
    SearchResult,
    get_audit_searcher
)
from maestro_hive.compliance.audit_logger import AuditLogger, AuditEventType


class TestAuditSearcher:
    """Tests for AuditSearcher class."""

    def test_searcher_initialization(self):
        """Test searcher initializes correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = AuditLogger(storage_dir=tmpdir)
            searcher = AuditSearcher(audit_logger=logger)
            assert searcher.audit_logger is not None

    def test_search_by_text(self):
        """Test searching by text."""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = AuditLogger(storage_dir=tmpdir)
            searcher = AuditSearcher(audit_logger=logger)

            # Create audit events
            logger.log(
                event_type=AuditEventType.DATA_ACCESS,
                message='User accessed sensitive document',
                actor='user-1',
                resource='doc-123'
            )
            logger.log(
                event_type=AuditEventType.DATA_ACCESS,
                message='User viewed public file',
                actor='user-2',
                resource='file-456'
            )

            # Search for 'sensitive'
            query = SearchQuery(text='sensitive')
            results = searcher.search(query)

            assert len(results) == 1
            assert 'sensitive' in results[0].event.message.lower()

    def test_search_by_event_type(self):
        """Test filtering by event type."""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = AuditLogger(storage_dir=tmpdir)
            searcher = AuditSearcher(audit_logger=logger)

            logger.log(AuditEventType.AUTHENTICATION, 'Login', actor='user-1')
            logger.log(AuditEventType.DATA_ACCESS, 'Read', actor='user-1')
            logger.log(AuditEventType.AUTHENTICATION, 'Logout', actor='user-1')

            query = SearchQuery(event_types=[AuditEventType.AUTHENTICATION])
            results = searcher.search(query)

            assert len(results) == 2
            for result in results:
                assert result.event.event_type == AuditEventType.AUTHENTICATION

    def test_search_by_actor(self):
        """Test filtering by actor."""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = AuditLogger(storage_dir=tmpdir)
            searcher = AuditSearcher(audit_logger=logger)

            logger.log(AuditEventType.DATA_ACCESS, 'Read', actor='admin')
            logger.log(AuditEventType.DATA_ACCESS, 'Write', actor='user')
            logger.log(AuditEventType.DATA_ACCESS, 'Delete', actor='admin')

            query = SearchQuery(actors=['admin'])
            results = searcher.search(query)

            assert len(results) == 2
            for result in results:
                assert result.event.actor == 'admin'

    def test_search_by_resource(self):
        """Test filtering by resource."""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = AuditLogger(storage_dir=tmpdir)
            searcher = AuditSearcher(audit_logger=logger)

            logger.log(AuditEventType.DATA_ACCESS, 'Access', actor='u1', resource='documents/report.pdf')
            logger.log(AuditEventType.DATA_ACCESS, 'Access', actor='u2', resource='images/photo.jpg')
            logger.log(AuditEventType.DATA_ACCESS, 'Access', actor='u3', resource='documents/memo.doc')

            query = SearchQuery(resources=['documents'])
            results = searcher.search(query)

            assert len(results) == 2
            for result in results:
                assert 'documents' in result.event.resource

    def test_search_with_pagination(self):
        """Test search pagination."""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = AuditLogger(storage_dir=tmpdir)
            searcher = AuditSearcher(audit_logger=logger)

            # Create 20 events
            for i in range(20):
                logger.log(AuditEventType.DATA_ACCESS, f'Event {i}', actor='user')

            # Get first page
            query1 = SearchQuery(limit=5, offset=0)
            results1 = searcher.search(query1)
            assert len(results1) == 5

            # Get second page
            query2 = SearchQuery(limit=5, offset=5)
            results2 = searcher.search(query2)
            assert len(results2) == 5

            # Results should be different
            ids1 = {r.event.id for r in results1}
            ids2 = {r.event.id for r in results2}
            assert ids1.isdisjoint(ids2)

    def test_search_score_ranking(self):
        """Test results are ranked by relevance score."""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = AuditLogger(storage_dir=tmpdir)
            searcher = AuditSearcher(audit_logger=logger)

            # Create events with varying relevance
            logger.log(AuditEventType.DATA_ACCESS, 'security check', actor='user', resource='other')
            logger.log(AuditEventType.DATA_ACCESS, 'normal access', actor='security-admin', resource='docs')
            logger.log(AuditEventType.DATA_ACCESS, 'security audit of security system', actor='security', resource='security')

            query = SearchQuery(text='security')
            results = searcher.search(query)

            # Results should be sorted by score (descending)
            scores = [r.score for r in results]
            assert scores == sorted(scores, reverse=True)

    def test_search_highlights(self):
        """Test search highlights matching text."""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = AuditLogger(storage_dir=tmpdir)
            searcher = AuditSearcher(audit_logger=logger)

            logger.log(
                AuditEventType.DATA_ACCESS,
                'User performed unauthorized access to restricted area',
                actor='hacker',
                resource='restricted-zone'
            )

            query = SearchQuery(text='unauthorized')
            results = searcher.search(query)

            assert len(results) == 1
            assert len(results[0].highlights) > 0
            assert any('unauthorized' in h.lower() for h in results[0].highlights)

    def test_aggregate_by_event_type(self):
        """Test aggregation by event type."""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = AuditLogger(storage_dir=tmpdir)
            searcher = AuditSearcher(audit_logger=logger)

            logger.log(AuditEventType.AUTHENTICATION, 'Login', actor='u1')
            logger.log(AuditEventType.AUTHENTICATION, 'Login', actor='u2')
            logger.log(AuditEventType.DATA_ACCESS, 'Read', actor='u1')

            counts = searcher.aggregate(field='event_type')

            assert AuditEventType.AUTHENTICATION.value in counts
            assert counts[AuditEventType.AUTHENTICATION.value] == 2
            assert counts[AuditEventType.DATA_ACCESS.value] == 1

    def test_aggregate_by_actor(self):
        """Test aggregation by actor."""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = AuditLogger(storage_dir=tmpdir)
            searcher = AuditSearcher(audit_logger=logger)

            logger.log(AuditEventType.DATA_ACCESS, 'Action', actor='alice')
            logger.log(AuditEventType.DATA_ACCESS, 'Action', actor='alice')
            logger.log(AuditEventType.DATA_ACCESS, 'Action', actor='bob')

            counts = searcher.aggregate(field='actor')

            assert counts['alice'] == 2
            assert counts['bob'] == 1

    def test_timeline(self):
        """Test timeline generation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = AuditLogger(storage_dir=tmpdir)
            searcher = AuditSearcher(audit_logger=logger)

            # Create events
            for i in range(5):
                logger.log(AuditEventType.DATA_ACCESS, f'Event {i}', actor='user')

            timeline = searcher.timeline(
                since='2024-01-01',
                interval='hour'
            )

            assert isinstance(timeline, list)
            # Each bucket should have timestamp and count
            for bucket in timeline:
                assert 'timestamp' in bucket
                assert 'count' in bucket

    def test_suggest_actors(self):
        """Test suggestion for actors."""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = AuditLogger(storage_dir=tmpdir)
            searcher = AuditSearcher(audit_logger=logger)

            logger.log(AuditEventType.DATA_ACCESS, 'Action', actor='admin-alice')
            logger.log(AuditEventType.DATA_ACCESS, 'Action', actor='admin-bob')
            logger.log(AuditEventType.DATA_ACCESS, 'Action', actor='user-carol')

            suggestions = searcher.suggest(prefix='admin', field='actor')

            assert 'admin-alice' in suggestions
            assert 'admin-bob' in suggestions
            assert 'user-carol' not in suggestions

    def test_get_audit_searcher_factory(self):
        """Test factory function."""
        searcher = get_audit_searcher()
        assert isinstance(searcher, AuditSearcher)


class TestSearchQuery:
    """Tests for SearchQuery dataclass."""

    def test_query_defaults(self):
        """Test query default values."""
        query = SearchQuery()
        assert query.text is None
        assert query.event_types is None
        assert query.limit == 100
        assert query.offset == 0

    def test_query_with_all_filters(self):
        """Test query with all filters set."""
        query = SearchQuery(
            text='security',
            event_types=[AuditEventType.AUTHENTICATION],
            actors=['admin'],
            resources=['secure'],
            since='2024-01-01',
            until='2024-12-31',
            limit=50,
            offset=10
        )
        assert query.text == 'security'
        assert len(query.event_types) == 1
        assert query.limit == 50


class TestSearchResult:
    """Tests for SearchResult dataclass."""

    def test_result_to_dict(self):
        """Test result serialization."""
        from maestro_hive.compliance.audit_logger import AuditEvent

        event = AuditEvent(
            id='EVT-001',
            event_type=AuditEventType.DATA_ACCESS,
            message='Test event',
            actor='user',
            timestamp='2024-01-01T00:00:00',
            outcome='success'
        )

        result = SearchResult(
            event=event,
            score=2.5,
            highlights=['matched text']
        )

        data = result.to_dict()
        assert data['score'] == 2.5
        assert 'matched text' in data['highlights']
        assert data['event']['id'] == 'EVT-001'
