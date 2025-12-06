"""
Tri-Modal Audit Result Storage

Provides persistent storage for tri-modal audit results with:
- JSON file storage (default)
- Query capabilities (by iteration_id, verdict, time range)
- History tracking for trend analysis
- Database upgrade path (future)

Part of MD-2043: Trimodal Convergence Completion
Task: MD-2078 - Implement persistent audit result storage

Author: Claude Code Agent
Date: 2025-12-02
"""

import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import threading
import fcntl


# Import tri-audit types
try:
    from tri_audit.tri_audit import (
        TriAuditResult,
        TriModalVerdict,
        DDEAuditResult,
        BDVAuditResult,
        ACCAuditResult
    )
except ImportError:
    TriAuditResult = None
    TriModalVerdict = None
    DDEAuditResult = None
    BDVAuditResult = None
    ACCAuditResult = None


class StorageBackend(Enum):
    """Storage backend type."""
    JSON_FILE = "json_file"
    SQLITE = "sqlite"  # Future
    POSTGRES = "postgres"  # Future


@dataclass
class StorageConfig:
    """Configuration for audit storage."""
    backend: StorageBackend = StorageBackend.JSON_FILE
    base_dir: str = "data/tri_audit"
    results_file: str = "audit_results.json"
    history_file: str = "audit_history.json"
    max_history_entries: int = 1000
    auto_prune_days: int = 90


@dataclass
class AuditHistoryEntry:
    """Entry in audit history for trend tracking."""
    iteration_id: str
    timestamp: str
    verdict: str
    can_deploy: bool
    dde_passed: bool
    bdv_passed: bool
    acc_passed: bool

    def to_dict(self) -> Dict[str, Any]:
        return {
            "iteration_id": self.iteration_id,
            "timestamp": self.timestamp,
            "verdict": self.verdict,
            "can_deploy": self.can_deploy,
            "dde_passed": self.dde_passed,
            "bdv_passed": self.bdv_passed,
            "acc_passed": self.acc_passed
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AuditHistoryEntry":
        return cls(
            iteration_id=data["iteration_id"],
            timestamp=data["timestamp"],
            verdict=data["verdict"],
            can_deploy=data["can_deploy"],
            dde_passed=data["dde_passed"],
            bdv_passed=data["bdv_passed"],
            acc_passed=data["acc_passed"]
        )


class TriAuditStorage:
    """
    Persistent storage for tri-modal audit results.

    Features:
    - Store and retrieve audit results by iteration_id
    - Query by verdict type
    - Query by time range
    - Track history for trend analysis
    - Thread-safe file operations

    Usage:
        storage = TriAuditStorage()

        # Save result
        storage.save(audit_result)

        # Get result
        result = storage.get("iter-123")

        # Query by verdict
        failures = storage.query_by_verdict(TriModalVerdict.SYSTEMIC_FAILURE)

        # Get history
        history = storage.get_history(limit=100)
    """

    def __init__(self, config: Optional[StorageConfig] = None):
        """Initialize storage with configuration."""
        self.config = config or StorageConfig()
        self._lock = threading.RLock()
        self._ensure_storage_dirs()

    def _ensure_storage_dirs(self):
        """Create storage directories if they don't exist."""
        base_path = Path(self.config.base_dir)
        base_path.mkdir(parents=True, exist_ok=True)

        # Ensure results file exists
        results_path = base_path / self.config.results_file
        if not results_path.exists():
            self._write_json(results_path, {"results": {}, "metadata": {
                "created": datetime.utcnow().isoformat() + "Z",
                "version": "1.0.0"
            }})

        # Ensure history file exists
        history_path = base_path / self.config.history_file
        if not history_path.exists():
            self._write_json(history_path, {"entries": [], "metadata": {
                "created": datetime.utcnow().isoformat() + "Z",
                "version": "1.0.0"
            }})

    def _get_results_path(self) -> Path:
        """Get path to results file."""
        return Path(self.config.base_dir) / self.config.results_file

    def _get_history_path(self) -> Path:
        """Get path to history file."""
        return Path(self.config.base_dir) / self.config.history_file

    def _read_json(self, path: Path) -> Dict[str, Any]:
        """Read JSON file with file locking."""
        with self._lock:
            try:
                with open(path, 'r') as f:
                    fcntl.flock(f.fileno(), fcntl.LOCK_SH)
                    try:
                        return json.load(f)
                    finally:
                        fcntl.flock(f.fileno(), fcntl.LOCK_UN)
            except FileNotFoundError:
                return {}
            except json.JSONDecodeError:
                return {}

    def _write_json(self, path: Path, data: Dict[str, Any]):
        """Write JSON file with file locking."""
        with self._lock:
            # Write to temp file first, then rename for atomicity
            temp_path = path.with_suffix('.tmp')
            with open(temp_path, 'w') as f:
                fcntl.flock(f.fileno(), fcntl.LOCK_EX)
                try:
                    json.dump(data, f, indent=2, default=str)
                finally:
                    fcntl.flock(f.fileno(), fcntl.LOCK_UN)
            temp_path.rename(path)

    def save(self, result: "TriAuditResult") -> bool:
        """
        Save tri-audit result to storage.

        Args:
            result: TriAuditResult to save

        Returns:
            True if saved successfully
        """
        if result is None:
            return False

        try:
            # Save to results store
            results_data = self._read_json(self._get_results_path())

            result_dict = result.to_dict() if hasattr(result, 'to_dict') else self._result_to_dict(result)
            results_data["results"][result.iteration_id] = result_dict
            results_data["metadata"]["last_updated"] = datetime.utcnow().isoformat() + "Z"

            self._write_json(self._get_results_path(), results_data)

            # Add to history
            self._add_to_history(result)

            # Also save to individual file for backward compatibility
            self._save_individual_file(result)

            return True

        except Exception as e:
            print(f"Error saving audit result: {e}")
            return False

    def _result_to_dict(self, result: "TriAuditResult") -> Dict[str, Any]:
        """Convert TriAuditResult to dict if to_dict not available."""
        verdict_value = result.verdict.value if hasattr(result.verdict, 'value') else str(result.verdict)
        return {
            "iteration_id": result.iteration_id,
            "verdict": verdict_value,
            "timestamp": result.timestamp,
            "dde_passed": result.dde_passed,
            "bdv_passed": result.bdv_passed,
            "acc_passed": result.acc_passed,
            "can_deploy": result.can_deploy,
            "diagnosis": result.diagnosis,
            "recommendations": result.recommendations,
            "dde_details": result.dde_details,
            "bdv_details": result.bdv_details,
            "acc_details": result.acc_details
        }

    def _save_individual_file(self, result: "TriAuditResult"):
        """Save result to individual file (backward compatibility)."""
        output_dir = Path(f"reports/tri-modal/{result.iteration_id}")
        output_dir.mkdir(parents=True, exist_ok=True)

        result_dict = result.to_dict() if hasattr(result, 'to_dict') else self._result_to_dict(result)
        output_file = output_dir / "tri_audit_result.json"

        with open(output_file, 'w') as f:
            json.dump(result_dict, f, indent=2)

    def _add_to_history(self, result: "TriAuditResult"):
        """Add entry to history for trend tracking."""
        history_data = self._read_json(self._get_history_path())

        verdict_value = result.verdict.value if hasattr(result.verdict, 'value') else str(result.verdict)

        entry = AuditHistoryEntry(
            iteration_id=result.iteration_id,
            timestamp=result.timestamp,
            verdict=verdict_value,
            can_deploy=result.can_deploy,
            dde_passed=result.dde_passed,
            bdv_passed=result.bdv_passed,
            acc_passed=result.acc_passed
        )

        history_data["entries"].append(entry.to_dict())

        # Prune old entries if exceeding max
        if len(history_data["entries"]) > self.config.max_history_entries:
            history_data["entries"] = history_data["entries"][-self.config.max_history_entries:]

        history_data["metadata"]["last_updated"] = datetime.utcnow().isoformat() + "Z"
        self._write_json(self._get_history_path(), history_data)

    def get(self, iteration_id: str) -> Optional["TriAuditResult"]:
        """
        Get tri-audit result by iteration_id.

        Args:
            iteration_id: Iteration identifier

        Returns:
            TriAuditResult if found, None otherwise
        """
        # Try storage file first
        results_data = self._read_json(self._get_results_path())
        result_dict = results_data.get("results", {}).get(iteration_id)

        if result_dict:
            return self._dict_to_result(result_dict)

        # Fall back to individual file
        result_file = Path(f"reports/tri-modal/{iteration_id}/tri_audit_result.json")
        if result_file.exists():
            try:
                with open(result_file) as f:
                    result_dict = json.load(f)
                return self._dict_to_result(result_dict)
            except Exception:
                pass

        return None

    def _dict_to_result(self, data: Dict[str, Any]) -> Optional["TriAuditResult"]:
        """Convert dict to TriAuditResult."""
        if TriAuditResult is None or TriModalVerdict is None:
            return None

        try:
            verdict = TriModalVerdict(data['verdict'])
            return TriAuditResult(
                iteration_id=data['iteration_id'],
                verdict=verdict,
                timestamp=data['timestamp'],
                dde_passed=data['dde_passed'],
                bdv_passed=data['bdv_passed'],
                acc_passed=data['acc_passed'],
                can_deploy=data['can_deploy'],
                diagnosis=data['diagnosis'],
                recommendations=data.get('recommendations', []),
                dde_details=data.get('dde_details', {}),
                bdv_details=data.get('bdv_details', {}),
                acc_details=data.get('acc_details', {})
            )
        except Exception as e:
            print(f"Error converting dict to TriAuditResult: {e}")
            return None

    def query_by_verdict(
        self,
        verdict: "TriModalVerdict",
        limit: int = 100
    ) -> List["TriAuditResult"]:
        """
        Query results by verdict type.

        Args:
            verdict: TriModalVerdict to filter by
            limit: Maximum results to return

        Returns:
            List of matching TriAuditResults
        """
        results_data = self._read_json(self._get_results_path())
        verdict_value = verdict.value if hasattr(verdict, 'value') else str(verdict)

        matching = []
        for result_dict in results_data.get("results", {}).values():
            if result_dict.get("verdict") == verdict_value:
                result = self._dict_to_result(result_dict)
                if result:
                    matching.append(result)
                if len(matching) >= limit:
                    break

        return matching

    def query_by_time_range(
        self,
        start_time: datetime,
        end_time: Optional[datetime] = None,
        limit: int = 100
    ) -> List["TriAuditResult"]:
        """
        Query results by time range.

        Args:
            start_time: Start of time range
            end_time: End of time range (defaults to now)
            limit: Maximum results to return

        Returns:
            List of matching TriAuditResults
        """
        end_time = end_time or datetime.utcnow()
        results_data = self._read_json(self._get_results_path())

        matching = []
        for result_dict in results_data.get("results", {}).values():
            try:
                timestamp_str = result_dict.get("timestamp", "")
                timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00").replace("+00:00", ""))

                if start_time <= timestamp <= end_time:
                    result = self._dict_to_result(result_dict)
                    if result:
                        matching.append(result)
                    if len(matching) >= limit:
                        break
            except Exception:
                continue

        # Sort by timestamp descending
        matching.sort(key=lambda r: r.timestamp, reverse=True)
        return matching[:limit]

    def query_failures(
        self,
        days: int = 7,
        limit: int = 100
    ) -> List["TriAuditResult"]:
        """
        Query recent failures (non-deployable results).

        Args:
            days: Number of days to look back
            limit: Maximum results to return

        Returns:
            List of failed TriAuditResults
        """
        start_time = datetime.utcnow() - timedelta(days=days)
        recent = self.query_by_time_range(start_time, limit=limit * 2)

        return [r for r in recent if not r.can_deploy][:limit]

    def get_history(
        self,
        limit: int = 100,
        offset: int = 0
    ) -> List[AuditHistoryEntry]:
        """
        Get audit history entries.

        Args:
            limit: Maximum entries to return
            offset: Number of entries to skip

        Returns:
            List of AuditHistoryEntry
        """
        history_data = self._read_json(self._get_history_path())
        entries = history_data.get("entries", [])

        # Return in reverse chronological order
        entries = entries[::-1]

        return [
            AuditHistoryEntry.from_dict(e)
            for e in entries[offset:offset + limit]
        ]

    def get_statistics(
        self,
        days: int = 30
    ) -> Dict[str, Any]:
        """
        Get statistics for trend analysis.

        Args:
            days: Number of days to analyze

        Returns:
            Statistics dictionary with pass rates, failure types, etc.
        """
        start_time = datetime.utcnow() - timedelta(days=days)
        history_data = self._read_json(self._get_history_path())
        entries = history_data.get("entries", [])

        # Filter to time range
        recent_entries = []
        for entry in entries:
            try:
                timestamp_str = entry.get("timestamp", "")
                timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00").replace("+00:00", ""))
                if timestamp >= start_time:
                    recent_entries.append(entry)
            except Exception:
                continue

        total = len(recent_entries)
        if total == 0:
            return {
                "period_days": days,
                "total_audits": 0,
                "deployable": 0,
                "blocked": 0,
                "pass_rate": 0.0,
                "verdict_breakdown": {},
                "stream_pass_rates": {
                    "dde": 0.0,
                    "bdv": 0.0,
                    "acc": 0.0
                }
            }

        deployable = sum(1 for e in recent_entries if e.get("can_deploy", False))
        dde_passed = sum(1 for e in recent_entries if e.get("dde_passed", False))
        bdv_passed = sum(1 for e in recent_entries if e.get("bdv_passed", False))
        acc_passed = sum(1 for e in recent_entries if e.get("acc_passed", False))

        # Verdict breakdown
        verdict_counts = {}
        for entry in recent_entries:
            verdict = entry.get("verdict", "unknown")
            verdict_counts[verdict] = verdict_counts.get(verdict, 0) + 1

        return {
            "period_days": days,
            "total_audits": total,
            "deployable": deployable,
            "blocked": total - deployable,
            "pass_rate": deployable / total if total > 0 else 0.0,
            "verdict_breakdown": verdict_counts,
            "stream_pass_rates": {
                "dde": dde_passed / total if total > 0 else 0.0,
                "bdv": bdv_passed / total if total > 0 else 0.0,
                "acc": acc_passed / total if total > 0 else 0.0
            }
        }

    def prune_old_entries(self, days: Optional[int] = None):
        """
        Remove entries older than specified days.

        Args:
            days: Number of days to keep (defaults to config.auto_prune_days)
        """
        days = days or self.config.auto_prune_days
        cutoff = datetime.utcnow() - timedelta(days=days)

        # Prune history
        history_data = self._read_json(self._get_history_path())
        entries = history_data.get("entries", [])

        new_entries = []
        for entry in entries:
            try:
                timestamp_str = entry.get("timestamp", "")
                timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00").replace("+00:00", ""))
                if timestamp >= cutoff:
                    new_entries.append(entry)
            except Exception:
                continue

        history_data["entries"] = new_entries
        history_data["metadata"]["last_pruned"] = datetime.utcnow().isoformat() + "Z"
        self._write_json(self._get_history_path(), history_data)

        # Prune results
        results_data = self._read_json(self._get_results_path())
        results = results_data.get("results", {})

        new_results = {}
        for iteration_id, result_dict in results.items():
            try:
                timestamp_str = result_dict.get("timestamp", "")
                timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00").replace("+00:00", ""))
                if timestamp >= cutoff:
                    new_results[iteration_id] = result_dict
            except Exception:
                continue

        results_data["results"] = new_results
        results_data["metadata"]["last_pruned"] = datetime.utcnow().isoformat() + "Z"
        self._write_json(self._get_results_path(), results_data)

    def list_all(self, limit: int = 100) -> List[str]:
        """
        List all stored iteration IDs.

        Args:
            limit: Maximum IDs to return

        Returns:
            List of iteration IDs
        """
        results_data = self._read_json(self._get_results_path())
        return list(results_data.get("results", {}).keys())[:limit]

    def delete(self, iteration_id: str) -> bool:
        """
        Delete audit result.

        Args:
            iteration_id: Iteration identifier

        Returns:
            True if deleted successfully
        """
        try:
            deleted = False
            results_data = self._read_json(self._get_results_path())
            if iteration_id in results_data.get("results", {}):
                del results_data["results"][iteration_id]
                results_data["metadata"]["last_updated"] = datetime.utcnow().isoformat() + "Z"
                self._write_json(self._get_results_path(), results_data)
                deleted = True

            # Also delete individual file for consistency
            individual_file = Path(f"reports/tri-modal/{iteration_id}/tri_audit_result.json")
            if individual_file.exists():
                individual_file.unlink()
                # Try to remove parent dir if empty
                try:
                    individual_file.parent.rmdir()
                except OSError:
                    pass  # Directory not empty, that's fine
                deleted = True

            return deleted
        except Exception as e:
            print(f"Error deleting audit result: {e}")
            return False


# Global storage instance
_storage: Optional[TriAuditStorage] = None


def get_storage(config: Optional[StorageConfig] = None) -> TriAuditStorage:
    """Get or create global storage instance."""
    global _storage
    if _storage is None:
        _storage = TriAuditStorage(config)
    return _storage


# Convenience functions for direct use

def save_audit_result(result: "TriAuditResult") -> bool:
    """Save audit result using global storage."""
    return get_storage().save(result)


def get_audit_result(iteration_id: str) -> Optional["TriAuditResult"]:
    """Get audit result using global storage."""
    return get_storage().get(iteration_id)


def query_failures(days: int = 7, limit: int = 100) -> List["TriAuditResult"]:
    """Query recent failures using global storage."""
    return get_storage().query_failures(days=days, limit=limit)


def get_audit_statistics(days: int = 30) -> Dict[str, Any]:
    """Get audit statistics using global storage."""
    return get_storage().get_statistics(days=days)


def get_audit_history(limit: int = 100) -> List[AuditHistoryEntry]:
    """Get audit history using global storage."""
    return get_storage().get_history(limit=limit)
