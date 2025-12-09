#!/usr/bin/env python3
"""Tests for immutable_store module."""

import pytest
import tempfile
import json

from maestro_hive.compliance.immutable_store import (
    ImmutableStore,
    ImmutableRecord,
    get_immutable_store
)


class TestImmutableStore:
    """Tests for ImmutableStore class."""

    def test_store_initialization(self):
        """Test store initializes correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = ImmutableStore(storage_dir=tmpdir)
            assert store.storage_dir.exists()
            assert store._last_hash == ImmutableStore.GENESIS_HASH

    def test_append_record(self):
        """Test appending a record."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = ImmutableStore(storage_dir=tmpdir)

            record = store.append({'event': 'test', 'value': 123})

            assert record.sequence == 1
            assert record.data == {'event': 'test', 'value': 123}
            assert record.previous_hash == ImmutableStore.GENESIS_HASH
            assert len(record.hash) == 64  # SHA-256 hex

    def test_hash_chain_integrity(self):
        """Test hash chain links records."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = ImmutableStore(storage_dir=tmpdir)

            record1 = store.append({'event': 'first'})
            record2 = store.append({'event': 'second'})
            record3 = store.append({'event': 'third'})

            # Each record should link to previous
            assert record1.previous_hash == ImmutableStore.GENESIS_HASH
            assert record2.previous_hash == record1.hash
            assert record3.previous_hash == record2.hash

    def test_verify_chain_valid(self):
        """Test chain verification - valid chain."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = ImmutableStore(storage_dir=tmpdir)

            store.append({'event': 'e1'})
            store.append({'event': 'e2'})
            store.append({'event': 'e3'})

            is_valid, error = store.verify_chain()
            assert is_valid is True
            assert error is None

    def test_verify_chain_empty(self):
        """Test chain verification - empty chain is valid."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = ImmutableStore(storage_dir=tmpdir)

            is_valid, error = store.verify_chain()
            assert is_valid is True

    def test_verify_chain_tampered_data(self):
        """Test chain verification detects tampered data."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = ImmutableStore(storage_dir=tmpdir)

            store.append({'event': 'original'})
            store.append({'event': 'second'})

            # Tamper with data
            store._records[0].data['event'] = 'tampered'

            is_valid, error = store.verify_chain()
            assert is_valid is False
            assert 'tampered' in error.lower() or 'mismatch' in error.lower()

    def test_verify_chain_broken_link(self):
        """Test chain verification detects broken links."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = ImmutableStore(storage_dir=tmpdir)

            store.append({'event': 'e1'})
            store.append({'event': 'e2'})

            # Break the chain link
            store._records[1].previous_hash = 'invalid_hash'

            is_valid, error = store.verify_chain()
            assert is_valid is False
            assert 'chain broken' in error.lower() or 'mismatch' in error.lower()

    def test_get_record_by_id(self):
        """Test retrieving record by ID."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = ImmutableStore(storage_dir=tmpdir)

            record = store.append({'event': 'test'})
            retrieved = store.get_record(record.id)

            assert retrieved is not None
            assert retrieved.id == record.id
            assert retrieved.data == {'event': 'test'}

    def test_get_record_not_found(self):
        """Test retrieving non-existent record."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = ImmutableStore(storage_dir=tmpdir)

            result = store.get_record('non-existent-id')
            assert result is None

    def test_get_records_with_limit(self):
        """Test retrieving records with limit."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = ImmutableStore(storage_dir=tmpdir)

            for i in range(10):
                store.append({'event': f'event-{i}'})

            records = store.get_records(limit=5)
            assert len(records) == 5

    def test_get_chain_info(self):
        """Test getting chain information."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = ImmutableStore(storage_dir=tmpdir)

            store.append({'event': 'e1'})
            store.append({'event': 'e2'})

            info = store.get_chain_info()

            assert info['total_records'] == 2
            assert info['last_sequence'] == 2
            assert info['chain_valid'] is True
            assert info['genesis_hash'] == ImmutableStore.GENESIS_HASH

    def test_export_json(self):
        """Test exporting chain as JSON."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = ImmutableStore(storage_dir=tmpdir)

            store.append({'event': 'e1', 'data': 'test'})
            store.append({'event': 'e2', 'data': 'test2'})

            export = store.export(format='json')
            data = json.loads(export.decode())

            assert 'chain_info' in data
            assert 'records' in data
            assert len(data['records']) == 2

    def test_persistence_and_reload(self):
        """Test records persist and reload correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create store and add records
            store1 = ImmutableStore(storage_dir=tmpdir)
            store1.append({'event': 'persist1'})
            store1.append({'event': 'persist2'})

            # Create new store instance (simulates restart)
            store2 = ImmutableStore(storage_dir=tmpdir)

            # Should load existing records
            assert len(store2._records) == 2
            assert store2._records[0].data['event'] == 'persist1'
            assert store2._records[1].data['event'] == 'persist2'

            # Chain should still be valid
            is_valid, _ = store2.verify_chain()
            assert is_valid is True

    def test_get_immutable_store_factory(self):
        """Test factory function."""
        store = get_immutable_store()
        assert isinstance(store, ImmutableStore)


class TestImmutableRecord:
    """Tests for ImmutableRecord dataclass."""

    def test_record_creation(self):
        """Test record creation."""
        record = ImmutableRecord(
            id='IMM-001',
            sequence=1,
            timestamp='2024-01-01T00:00:00',
            data={'key': 'value'},
            previous_hash='0' * 64,
            hash='abc123'
        )
        assert record.id == 'IMM-001'
        assert record.sequence == 1
        assert record.data == {'key': 'value'}

    def test_record_to_dict(self):
        """Test record serialization."""
        record = ImmutableRecord(
            id='IMM-002',
            sequence=2,
            timestamp='2024-01-01T00:00:00',
            data={'event': 'test'},
            previous_hash='prev_hash',
            hash='curr_hash'
        )
        data = record.to_dict()
        assert data['id'] == 'IMM-002'
        assert data['sequence'] == 2
        assert data['data'] == {'event': 'test'}

    def test_record_from_dict(self):
        """Test record deserialization."""
        data = {
            'id': 'IMM-003',
            'sequence': 3,
            'timestamp': '2024-01-01T00:00:00',
            'data': {'event': 'loaded'},
            'previous_hash': 'prev',
            'hash': 'curr',
            'signature': None
        }
        record = ImmutableRecord.from_dict(data)
        assert record.id == 'IMM-003'
        assert record.data == {'event': 'loaded'}
