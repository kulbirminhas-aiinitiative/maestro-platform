#!/usr/bin/env python3
"""
Immutable Store: Hash-chain based immutable audit storage.

Provides tamper-evident storage for audit logs using SHA-256 chaining.
"""

import json
import hashlib
import logging
from dataclasses import dataclass, asdict, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class ImmutableRecord:
    """An immutable audit record with hash chain."""
    id: str
    sequence: int
    timestamp: str
    data: Dict[str, Any]
    previous_hash: str
    hash: str
    signature: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ImmutableRecord':
        return cls(**data)


class ImmutableStore:
    """
    Hash-chain based immutable storage.

    Each record includes the hash of the previous record,
    creating a tamper-evident chain.
    """

    GENESIS_HASH = "0" * 64

    def __init__(self, storage_dir: Optional[str] = None):
        self.storage_dir = Path(storage_dir) if storage_dir else \
            Path.home() / '.maestro' / 'immutable_audit'
        self.storage_dir.mkdir(parents=True, exist_ok=True)

        self._records: List[ImmutableRecord] = []
        self._sequence = 0
        self._last_hash = self.GENESIS_HASH

        self._load_records()

    def append(self, data: Dict[str, Any]) -> ImmutableRecord:
        """
        Append a new record to the immutable store.

        Args:
            data: Data to store

        Returns:
            ImmutableRecord with hash
        """
        self._sequence += 1
        timestamp = datetime.utcnow().isoformat()
        record_id = f"IMM-{timestamp.replace(':', '').replace('.', '')}-{self._sequence:08d}"

        # Create record content for hashing
        content = {
            'id': record_id,
            'sequence': self._sequence,
            'timestamp': timestamp,
            'data': data,
            'previous_hash': self._last_hash
        }

        # Calculate hash
        content_str = json.dumps(content, sort_keys=True)
        record_hash = hashlib.sha256(content_str.encode()).hexdigest()

        record = ImmutableRecord(
            id=record_id,
            sequence=self._sequence,
            timestamp=timestamp,
            data=data,
            previous_hash=self._last_hash,
            hash=record_hash
        )

        self._records.append(record)
        self._last_hash = record_hash
        self._persist_record(record)

        return record

    def verify_chain(self) -> tuple[bool, Optional[str]]:
        """
        Verify integrity of the entire chain.

        Returns:
            (is_valid, error_message)
        """
        if not self._records:
            return True, None

        previous_hash = self.GENESIS_HASH

        for record in self._records:
            # Verify previous hash link
            if record.previous_hash != previous_hash:
                return False, f"Chain broken at record {record.id}: previous_hash mismatch"

            # Recalculate hash
            content = {
                'id': record.id,
                'sequence': record.sequence,
                'timestamp': record.timestamp,
                'data': record.data,
                'previous_hash': record.previous_hash
            }
            content_str = json.dumps(content, sort_keys=True)
            calculated_hash = hashlib.sha256(content_str.encode()).hexdigest()

            if calculated_hash != record.hash:
                return False, f"Hash mismatch at record {record.id}: data may have been tampered"

            previous_hash = record.hash

        return True, None

    def get_record(self, record_id: str) -> Optional[ImmutableRecord]:
        """Get a record by ID."""
        for record in self._records:
            if record.id == record_id:
                return record
        return None

    def get_records(
        self,
        since: Optional[str] = None,
        limit: int = 100
    ) -> List[ImmutableRecord]:
        """Get records with optional filters."""
        records = self._records

        if since:
            records = [r for r in records if r.timestamp >= since]

        return records[-limit:]

    def get_chain_info(self) -> Dict[str, Any]:
        """Get information about the chain."""
        is_valid, error = self.verify_chain()

        return {
            'total_records': len(self._records),
            'last_sequence': self._sequence,
            'last_hash': self._last_hash,
            'chain_valid': is_valid,
            'validation_error': error,
            'genesis_hash': self.GENESIS_HASH
        }

    def export(self, format: str = 'json') -> bytes:
        """Export the complete chain."""
        data = {
            'chain_info': self.get_chain_info(),
            'records': [r.to_dict() for r in self._records]
        }

        if format == 'json':
            return json.dumps(data, indent=2).encode()
        else:
            raise ValueError(f"Unknown format: {format}")

    def _persist_record(self, record: ImmutableRecord):
        """Persist record to storage."""
        file_path = self.storage_dir / f"chain.jsonl"

        with open(file_path, 'a') as f:
            f.write(json.dumps(record.to_dict()) + '\n')

    def _load_records(self):
        """Load existing records from storage."""
        file_path = self.storage_dir / "chain.jsonl"

        if not file_path.exists():
            return

        try:
            with open(file_path, 'r') as f:
                for line in f:
                    data = json.loads(line.strip())
                    record = ImmutableRecord.from_dict(data)
                    self._records.append(record)
                    self._sequence = max(self._sequence, record.sequence)
                    self._last_hash = record.hash

            # Verify loaded chain
            is_valid, error = self.verify_chain()
            if not is_valid:
                logger.error(f"Chain integrity error: {error}")
            else:
                logger.info(f"Loaded {len(self._records)} records from immutable store")

        except Exception as e:
            logger.error(f"Error loading immutable store: {e}")


def get_immutable_store(**kwargs) -> ImmutableStore:
    """Get immutable store instance."""
    return ImmutableStore(**kwargs)
