#!/usr/bin/env python3
"""Tests for cost_tracker module."""

import pytest
import tempfile
from decimal import Decimal
from datetime import datetime, timedelta

from maestro_hive.compliance.cost_tracker import (
    CostTracker,
    UsageRecord,
    get_cost_tracker,
    MODEL_PRICING
)


class TestCostTracker:
    """Tests for CostTracker class."""

    def test_tracker_initialization(self):
        """Test tracker initializes correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tracker = CostTracker(storage_dir=tmpdir)
            assert tracker.storage_dir.exists()
            assert tracker._records == []

    def test_track_usage_gpt4(self):
        """Test tracking GPT-4 usage."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tracker = CostTracker(storage_dir=tmpdir)
            record = tracker.track(
                model='gpt-4-turbo',
                input_tokens=1000,
                output_tokens=500,
                user_id='test-user',
                project_id='test-project'
            )

            assert record.model == 'gpt-4-turbo'
            assert record.input_tokens == 1000
            assert record.output_tokens == 500
            assert record.total_cost > Decimal('0')
            assert record.user_id == 'test-user'

    def test_track_usage_claude(self):
        """Test tracking Claude usage."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tracker = CostTracker(storage_dir=tmpdir)
            record = tracker.track(
                model='claude-3.5-sonnet',
                input_tokens=2000,
                output_tokens=1000,
                user_id='test-user'
            )

            assert record.model == 'claude-3.5-sonnet'
            assert record.provider == 'anthropic'
            assert record.total_cost > Decimal('0')

    def test_cost_calculation_accuracy(self):
        """Test cost calculation is accurate."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tracker = CostTracker(storage_dir=tmpdir)

            # GPT-4-turbo: $10/M input, $30/M output
            record = tracker.track(
                model='gpt-4-turbo',
                input_tokens=1_000_000,  # 1M tokens
                output_tokens=1_000_000,  # 1M tokens
                user_id='test-user'
            )

            # Expected: $10 + $30 = $40
            assert record.input_cost == Decimal('10.00')
            assert record.output_cost == Decimal('30.00')
            assert record.total_cost == Decimal('40.00')

    def test_query_by_user(self):
        """Test querying records by user."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tracker = CostTracker(storage_dir=tmpdir)

            # Create records for different users
            tracker.track(model='gpt-4o', input_tokens=100, output_tokens=50, user_id='user-1')
            tracker.track(model='gpt-4o', input_tokens=200, output_tokens=100, user_id='user-2')
            tracker.track(model='gpt-4o', input_tokens=300, output_tokens=150, user_id='user-1')

            user1_records = tracker.query(user_id='user-1')
            assert len(user1_records) == 2

            user2_records = tracker.query(user_id='user-2')
            assert len(user2_records) == 1

    def test_query_by_model(self):
        """Test querying records by model."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tracker = CostTracker(storage_dir=tmpdir)

            tracker.track(model='gpt-4-turbo', input_tokens=100, output_tokens=50, user_id='user')
            tracker.track(model='claude-3.5-sonnet', input_tokens=100, output_tokens=50, user_id='user')
            tracker.track(model='gpt-4-turbo', input_tokens=100, output_tokens=50, user_id='user')

            gpt4_records = tracker.query(model='gpt-4-turbo')
            assert len(gpt4_records) == 2

            claude_records = tracker.query(model='claude-3.5-sonnet')
            assert len(claude_records) == 1

    def test_get_total_cost(self):
        """Test getting total cost."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tracker = CostTracker(storage_dir=tmpdir)

            tracker.track(model='gpt-4o', input_tokens=1000, output_tokens=500, user_id='user')
            tracker.track(model='gpt-4o', input_tokens=2000, output_tokens=1000, user_id='user')

            total = tracker.get_total_cost()
            assert total > Decimal('0')

    def test_get_cost_by_model(self):
        """Test getting cost breakdown by model."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tracker = CostTracker(storage_dir=tmpdir)

            tracker.track(model='gpt-4-turbo', input_tokens=1000, output_tokens=500, user_id='user')
            tracker.track(model='claude-3.5-sonnet', input_tokens=1000, output_tokens=500, user_id='user')

            by_model = tracker.get_cost_by_model()
            assert 'gpt-4-turbo' in by_model
            assert 'claude-3.5-sonnet' in by_model

    def test_unknown_model_uses_default(self):
        """Test unknown model uses default pricing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tracker = CostTracker(storage_dir=tmpdir)

            record = tracker.track(
                model='unknown-model-xyz',
                input_tokens=1000,
                output_tokens=500,
                user_id='user'
            )

            # Should still calculate a cost using default
            assert record.total_cost >= Decimal('0')

    def test_model_pricing_constants(self):
        """Test model pricing constants are defined."""
        assert 'gpt-4-turbo' in MODEL_PRICING
        assert 'gpt-4o' in MODEL_PRICING
        assert 'claude-3.5-sonnet' in MODEL_PRICING

        for model, pricing in MODEL_PRICING.items():
            assert 'input' in pricing
            assert 'output' in pricing
            assert 'provider' in pricing

    def test_get_cost_tracker_factory(self):
        """Test factory function."""
        tracker = get_cost_tracker()
        assert isinstance(tracker, CostTracker)


class TestUsageRecord:
    """Tests for UsageRecord dataclass."""

    def test_usage_record_creation(self):
        """Test usage record creation."""
        record = UsageRecord(
            id='REC-001',
            timestamp='2024-01-01T00:00:00',
            model='gpt-4-turbo',
            provider='openai',
            input_tokens=1000,
            output_tokens=500,
            input_cost=Decimal('0.01'),
            output_cost=Decimal('0.015'),
            total_cost=Decimal('0.025'),
            user_id='test-user'
        )
        assert record.id == 'REC-001'
        assert record.model == 'gpt-4-turbo'
        assert record.total_cost == Decimal('0.025')

    def test_usage_record_to_dict(self):
        """Test usage record serialization."""
        record = UsageRecord(
            id='REC-002',
            timestamp='2024-01-01T00:00:00',
            model='claude-3.5-sonnet',
            provider='anthropic',
            input_tokens=2000,
            output_tokens=1000,
            input_cost=Decimal('0.006'),
            output_cost=Decimal('0.015'),
            total_cost=Decimal('0.021'),
            user_id='test-user',
            project_id='test-project'
        )
        data = record.to_dict()
        assert data['id'] == 'REC-002'
        assert data['model'] == 'claude-3.5-sonnet'
        assert data['project_id'] == 'test-project'
