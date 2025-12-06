"""
Export Service for Execution History Store

EPIC: MD-2500
AC-4: Export capability for analysis

This module provides export functionality for execution history records
in various formats (JSON, CSV, Parquet) for external analysis.
"""

import csv
import io
import json
import logging
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from uuid import UUID

from .models import ExecutionRecord, ExecutionStatus

logger = logging.getLogger(__name__)


class ExportFormat(str, Enum):
    """Supported export formats."""
    JSON = "json"
    JSONL = "jsonl"  # JSON Lines for streaming
    CSV = "csv"
    PARQUET = "parquet"


@dataclass
class ExportOptions:
    """Options for export operations."""
    format: ExportFormat = ExportFormat.JSON
    include_embeddings: bool = False  # Embeddings can be large
    include_metadata: bool = True
    include_artifacts: bool = True
    include_quality_scores: bool = True
    pretty_print: bool = False
    compress: bool = False
    date_format: str = "iso"  # "iso" or "timestamp"

    # Filtering options
    status_filter: Optional[List[ExecutionStatus]] = None
    epic_filter: Optional[List[str]] = None
    since: Optional[datetime] = None
    until: Optional[datetime] = None
    limit: Optional[int] = None


@dataclass
class ExportResult:
    """Result of an export operation."""
    records_exported: int = 0
    file_path: Optional[str] = None
    file_size_bytes: int = 0
    format: ExportFormat = ExportFormat.JSON
    duration_seconds: float = 0.0
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "records_exported": self.records_exported,
            "file_path": self.file_path,
            "file_size_bytes": self.file_size_bytes,
            "format": self.format.value,
            "duration_seconds": self.duration_seconds,
            "error": self.error,
        }


class ExportService:
    """
    Export service for execution history data.

    Supports:
    - JSON export (single file or streaming JSONL)
    - CSV export for spreadsheet analysis
    - Parquet export for big data tools

    Usage:
        service = ExportService(store)

        # Export to file
        result = await service.export_to_file(
            "/path/to/export.json",
            ExportOptions(format=ExportFormat.JSON)
        )

        # Export to memory
        data = await service.export_to_memory(options)
    """

    def __init__(self, store: Any):
        """
        Initialize the export service.

        Args:
            store: ExecutionHistoryStore instance
        """
        self.store = store
        logger.info("ExportService initialized")

    async def export_to_file(
        self,
        file_path: Union[str, Path],
        options: Optional[ExportOptions] = None,
    ) -> ExportResult:
        """
        Export records to a file.

        Args:
            file_path: Path to output file
            options: Export options

        Returns:
            ExportResult with statistics
        """
        options = options or ExportOptions()
        start_time = datetime.utcnow()
        result = ExportResult(format=options.format)

        try:
            file_path = Path(file_path)
            file_path.parent.mkdir(parents=True, exist_ok=True)

            records = await self._fetch_records(options)

            if options.format == ExportFormat.JSON:
                await self._export_json(file_path, records, options)
            elif options.format == ExportFormat.JSONL:
                await self._export_jsonl(file_path, records, options)
            elif options.format == ExportFormat.CSV:
                await self._export_csv(file_path, records, options)
            elif options.format == ExportFormat.PARQUET:
                await self._export_parquet(file_path, records, options)

            result.records_exported = len(records)
            result.file_path = str(file_path)
            result.file_size_bytes = file_path.stat().st_size

        except Exception as e:
            result.error = str(e)
            logger.error(f"Export error: {e}")

        result.duration_seconds = (datetime.utcnow() - start_time).total_seconds()
        return result

    async def export_to_memory(
        self,
        options: Optional[ExportOptions] = None,
    ) -> Union[str, bytes, List[Dict]]:
        """
        Export records to memory.

        Args:
            options: Export options

        Returns:
            Exported data (format depends on options)
        """
        options = options or ExportOptions()
        records = await self._fetch_records(options)

        if options.format in (ExportFormat.JSON, ExportFormat.JSONL):
            return self._records_to_json(records, options)
        elif options.format == ExportFormat.CSV:
            return self._records_to_csv(records, options)
        else:
            # Default to JSON for memory export
            return self._records_to_json(records, options)

    async def _fetch_records(self, options: ExportOptions) -> List[ExecutionRecord]:
        """Fetch records based on filter options."""
        records = []

        if self.store.use_memory:
            for record in self.store._records.values():
                if self._matches_filter(record, options):
                    records.append(record)
        else:
            # Build query for PostgreSQL
            records = await self._pg_fetch_records(options)

        # Sort by created_at
        records.sort(key=lambda r: r.created_at, reverse=True)

        # Apply limit
        if options.limit:
            records = records[:options.limit]

        return records

    def _matches_filter(self, record: ExecutionRecord, options: ExportOptions) -> bool:
        """Check if a record matches filter options."""
        if options.status_filter and record.status not in options.status_filter:
            return False
        if options.epic_filter and record.epic_key not in options.epic_filter:
            return False
        if options.since and record.created_at < options.since:
            return False
        if options.until and record.created_at > options.until:
            return False
        return True

    async def _pg_fetch_records(self, options: ExportOptions) -> List[ExecutionRecord]:
        """Fetch records from PostgreSQL with filters."""
        where_clauses = []
        params = []

        if options.status_filter:
            placeholders = ", ".join(f"${i + 1}" for i in range(len(options.status_filter)))
            where_clauses.append(f"status IN ({placeholders})")
            params.extend(s.value for s in options.status_filter)

        if options.epic_filter:
            start_idx = len(params) + 1
            placeholders = ", ".join(f"${i + start_idx}" for i in range(len(options.epic_filter)))
            where_clauses.append(f"epic_key IN ({placeholders})")
            params.extend(options.epic_filter)

        if options.since:
            params.append(options.since)
            where_clauses.append(f"created_at >= ${len(params)}")

        if options.until:
            params.append(options.until)
            where_clauses.append(f"created_at <= ${len(params)}")

        where_clause = " AND ".join(where_clauses) if where_clauses else "TRUE"
        limit_clause = f"LIMIT {options.limit}" if options.limit else ""

        async with self.store._db_pool.acquire() as conn:
            rows = await conn.fetch(f"""
                SELECT * FROM execution_history
                WHERE {where_clause}
                ORDER BY created_at DESC
                {limit_clause}
            """, *params)

            return [self.store._row_to_record(row) for row in rows]

    def _record_to_dict(
        self,
        record: ExecutionRecord,
        options: ExportOptions,
    ) -> Dict[str, Any]:
        """Convert a record to dictionary for export."""
        data = {
            "id": str(record.id),
            "epic_key": record.epic_key,
            "status": record.status.value,
            "input_text": record.input_text,
            "output_summary": record.output_summary,
            "failure_reason": record.failure_reason,
            "executor_version": record.executor_version,
            "retry_count": record.retry_count,
        }

        # Format dates
        if options.date_format == "iso":
            data["created_at"] = record.created_at.isoformat()
            data["updated_at"] = record.updated_at.isoformat()
            data["completed_at"] = record.completed_at.isoformat() if record.completed_at else None
        else:
            data["created_at"] = record.created_at.timestamp()
            data["updated_at"] = record.updated_at.timestamp()
            data["completed_at"] = record.completed_at.timestamp() if record.completed_at else None

        # Optional fields
        if options.include_embeddings and record.input_embedding:
            data["input_embedding"] = record.input_embedding

        if options.include_metadata:
            data["input_metadata"] = record.input_metadata
            data["error_details"] = record.error_details

        if options.include_artifacts:
            data["output_artifacts"] = [
                {
                    "name": a.name,
                    "artifact_type": a.artifact_type,
                    "file_path": a.file_path,
                    "content_hash": a.content_hash,
                    "metadata": a.metadata if options.include_metadata else {},
                }
                for a in record.output_artifacts
            ]

        if options.include_quality_scores and record.quality_scores:
            data["quality_scores"] = record.quality_scores.to_dict()

        if record.parent_execution_id:
            data["parent_execution_id"] = str(record.parent_execution_id)

        return data

    def _records_to_json(
        self,
        records: List[ExecutionRecord],
        options: ExportOptions,
    ) -> str:
        """Convert records to JSON string."""
        data = [self._record_to_dict(r, options) for r in records]

        if options.format == ExportFormat.JSONL:
            return "\n".join(json.dumps(d) for d in data)

        indent = 2 if options.pretty_print else None
        return json.dumps(data, indent=indent)

    def _records_to_csv(
        self,
        records: List[ExecutionRecord],
        options: ExportOptions,
    ) -> str:
        """Convert records to CSV string."""
        if not records:
            return ""

        output = io.StringIO()

        # Define CSV columns (flatten structure)
        columns = [
            "id", "epic_key", "status", "created_at", "updated_at", "completed_at",
            "input_text", "output_summary", "failure_reason",
            "executor_version", "retry_count",
        ]

        if options.include_quality_scores:
            columns.extend([
                "overall_score", "documentation_score", "implementation_score",
                "test_coverage_score", "correctness_score", "build_score", "evidence_score",
            ])

        writer = csv.DictWriter(output, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()

        for record in records:
            row = self._record_to_dict(record, options)

            # Flatten quality scores
            if options.include_quality_scores and record.quality_scores:
                row.update(record.quality_scores.to_dict())

            # Truncate long text fields for CSV
            if len(row.get("input_text", "")) > 1000:
                row["input_text"] = row["input_text"][:1000] + "..."
            if len(row.get("output_summary", "")) > 1000:
                row["output_summary"] = row["output_summary"][:1000] + "..."

            writer.writerow(row)

        return output.getvalue()

    async def _export_json(
        self,
        file_path: Path,
        records: List[ExecutionRecord],
        options: ExportOptions,
    ) -> None:
        """Export records to JSON file."""
        content = self._records_to_json(records, options)

        if options.compress:
            import gzip
            with gzip.open(str(file_path) + ".gz", "wt", encoding="utf-8") as f:
                f.write(content)
        else:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)

    async def _export_jsonl(
        self,
        file_path: Path,
        records: List[ExecutionRecord],
        options: ExportOptions,
    ) -> None:
        """Export records to JSON Lines file."""
        if options.compress:
            import gzip
            with gzip.open(str(file_path) + ".gz", "wt", encoding="utf-8") as f:
                for record in records:
                    data = self._record_to_dict(record, options)
                    f.write(json.dumps(data) + "\n")
        else:
            with open(file_path, "w", encoding="utf-8") as f:
                for record in records:
                    data = self._record_to_dict(record, options)
                    f.write(json.dumps(data) + "\n")

    async def _export_csv(
        self,
        file_path: Path,
        records: List[ExecutionRecord],
        options: ExportOptions,
    ) -> None:
        """Export records to CSV file."""
        content = self._records_to_csv(records, options)

        if options.compress:
            import gzip
            with gzip.open(str(file_path) + ".gz", "wt", encoding="utf-8") as f:
                f.write(content)
        else:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)

    async def _export_parquet(
        self,
        file_path: Path,
        records: List[ExecutionRecord],
        options: ExportOptions,
    ) -> None:
        """Export records to Parquet file."""
        try:
            import pyarrow as pa
            import pyarrow.parquet as pq

            # Convert records to columnar format
            data = {
                "id": [str(r.id) for r in records],
                "epic_key": [r.epic_key for r in records],
                "status": [r.status.value for r in records],
                "created_at": [r.created_at for r in records],
                "updated_at": [r.updated_at for r in records],
                "completed_at": [r.completed_at for r in records],
                "input_text": [r.input_text for r in records],
                "output_summary": [r.output_summary for r in records],
                "failure_reason": [r.failure_reason for r in records],
                "executor_version": [r.executor_version for r in records],
                "retry_count": [r.retry_count for r in records],
            }

            if options.include_quality_scores:
                data["overall_score"] = [
                    r.quality_scores.overall_score if r.quality_scores else None
                    for r in records
                ]
                data["documentation_score"] = [
                    r.quality_scores.documentation_score if r.quality_scores else None
                    for r in records
                ]
                data["implementation_score"] = [
                    r.quality_scores.implementation_score if r.quality_scores else None
                    for r in records
                ]

            table = pa.Table.from_pydict(data)
            pq.write_table(table, str(file_path), compression="snappy" if options.compress else None)

        except ImportError:
            # Fallback to JSON if PyArrow not available
            logger.warning("PyArrow not available, falling back to JSON")
            options.format = ExportFormat.JSON
            await self._export_json(file_path.with_suffix(".json"), records, options)

    async def get_export_stats(self) -> Dict[str, Any]:
        """Get statistics about exportable data."""
        stats = {
            "total_records": 0,
            "by_status": {},
            "by_epic": {},
            "date_range": {
                "oldest": None,
                "newest": None,
            },
            "estimated_size": {
                "json_mb": 0,
                "csv_mb": 0,
            },
        }

        if self.store.use_memory:
            records = list(self.store._records.values())
            stats["total_records"] = len(records)

            for record in records:
                status = record.status.value
                stats["by_status"][status] = stats["by_status"].get(status, 0) + 1
                stats["by_epic"][record.epic_key] = stats["by_epic"].get(record.epic_key, 0) + 1

                if stats["date_range"]["oldest"] is None or record.created_at < datetime.fromisoformat(stats["date_range"]["oldest"]):
                    stats["date_range"]["oldest"] = record.created_at.isoformat()
                if stats["date_range"]["newest"] is None or record.created_at > datetime.fromisoformat(stats["date_range"]["newest"]):
                    stats["date_range"]["newest"] = record.created_at.isoformat()

            # Estimate sizes (rough calculation)
            avg_record_size = 2000  # bytes
            stats["estimated_size"]["json_mb"] = round(len(records) * avg_record_size / (1024 * 1024), 2)
            stats["estimated_size"]["csv_mb"] = round(len(records) * 500 / (1024 * 1024), 2)
        else:
            async with self.store._db_pool.acquire() as conn:
                stats["total_records"] = await conn.fetchval(
                    "SELECT COUNT(*) FROM execution_history"
                )

                rows = await conn.fetch("""
                    SELECT status, COUNT(*) as cnt
                    FROM execution_history
                    GROUP BY status
                """)
                stats["by_status"] = {row["status"]: row["cnt"] for row in rows}

                rows = await conn.fetch("""
                    SELECT epic_key, COUNT(*) as cnt
                    FROM execution_history
                    GROUP BY epic_key
                    ORDER BY cnt DESC
                    LIMIT 20
                """)
                stats["by_epic"] = {row["epic_key"]: row["cnt"] for row in rows}

                oldest = await conn.fetchval("SELECT MIN(created_at) FROM execution_history")
                newest = await conn.fetchval("SELECT MAX(created_at) FROM execution_history")
                stats["date_range"]["oldest"] = oldest.isoformat() if oldest else None
                stats["date_range"]["newest"] = newest.isoformat() if newest else None

                # Estimate size from table stats
                size = await conn.fetchval("""
                    SELECT pg_total_relation_size('execution_history')
                """)
                stats["estimated_size"]["json_mb"] = round(size / (1024 * 1024) * 1.5, 2) if size else 0
                stats["estimated_size"]["csv_mb"] = round(size / (1024 * 1024) * 0.8, 2) if size else 0

        return stats
