"""
Template Usage Tracker for audit trail.

EU AI Act Article 12 Compliance:
Tracks template usage with full audit trail for traceability.
"""

import hashlib
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import UUID

from .models import (
    TemplateUsageRecord,
    AuditQueryResult
)


logger = logging.getLogger(__name__)


class TemplateTracker:
    """
    Tracks template usage with complete audit trail.

    Records which templates are used, when, by whom, and how
    they're customized for compliance auditing.
    """

    def __init__(
        self,
        storage_path: Optional[Path] = None,
        max_records_in_memory: int = 10000,
        auto_persist: bool = True
    ):
        """
        Initialize the template tracker.

        Args:
            storage_path: Path for persistent storage
            max_records_in_memory: Maximum records in memory
            auto_persist: Whether to auto-persist
        """
        self.storage_path = storage_path or Path("./audit/template_usage")
        self.storage_path.mkdir(parents=True, exist_ok=True)

        self.max_records_in_memory = max_records_in_memory
        self.auto_persist = auto_persist

        self._records: List[TemplateUsageRecord] = []
        self._records_by_template: Dict[str, List[TemplateUsageRecord]] = {}
        self._records_by_user: Dict[str, List[TemplateUsageRecord]] = {}

        # Template registry for hash tracking
        self._template_registry: Dict[str, str] = {}  # template_id -> hash

        logger.info(
            f"TemplateTracker initialized with storage at {self.storage_path}"
        )

    def register_template(
        self,
        template_id: str,
        template_content: str
    ) -> str:
        """
        Register a template and get its content hash.

        Args:
            template_id: Unique template identifier
            template_content: The template content

        Returns:
            Content hash of the template
        """
        content_hash = hashlib.sha256(template_content.encode()).hexdigest()[:16]
        self._template_registry[template_id] = content_hash
        return content_hash

    def track_usage(
        self,
        template_id: str,
        template_name: str,
        template_version: str,
        template_category: str,
        used_by: str,
        used_by_type: str,
        context_id: str = "",
        context_type: str = "",
        input_variables: Optional[Dict[str, Any]] = None,
        output_size_bytes: int = 0,
        customizations_applied: Optional[List[str]] = None
    ) -> TemplateUsageRecord:
        """
        Track a template usage event.

        Args:
            template_id: Template identifier
            template_name: Human-readable template name
            template_version: Version of the template
            template_category: Category (e.g., "code", "document")
            used_by: User or agent ID
            used_by_type: "user" or "agent"
            context_id: Context identifier
            context_type: Type of context
            input_variables: Variables passed to template
            output_size_bytes: Size of generated output
            customizations_applied: List of customizations

        Returns:
            The created TemplateUsageRecord
        """
        # Sanitize input variables (remove sensitive data)
        safe_variables = self._sanitize_variables(input_variables or {})

        record = TemplateUsageRecord(
            template_id=template_id,
            template_name=template_name,
            template_version=template_version,
            template_category=template_category,
            used_by=used_by,
            used_by_type=used_by_type,
            context_id=context_id,
            context_type=context_type,
            input_variables=safe_variables,
            output_generated=output_size_bytes > 0,
            output_size_bytes=output_size_bytes,
            customizations_applied=customizations_applied or [],
            original_template_hash=self._template_registry.get(template_id, "")
        )

        self._records.append(record)

        # Index by template
        if template_id not in self._records_by_template:
            self._records_by_template[template_id] = []
        self._records_by_template[template_id].append(record)

        # Index by user
        if used_by not in self._records_by_user:
            self._records_by_user[used_by] = []
        self._records_by_user[used_by].append(record)

        logger.debug(
            f"Tracked template usage: {template_name} v{template_version} "
            f"by {used_by_type} {used_by}"
        )

        # Auto-persist if threshold reached
        if self.auto_persist and len(self._records) >= self.max_records_in_memory:
            self._persist_to_storage()

        return record

    def _sanitize_variables(
        self,
        variables: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Sanitize template variables by removing sensitive data.

        Args:
            variables: Raw input variables

        Returns:
            Sanitized variables safe for logging
        """
        sensitive_keys = {
            "password", "secret", "token", "api_key", "credential",
            "private_key", "ssn", "credit_card"
        }

        sanitized = {}
        for key, value in variables.items():
            # Check if key contains sensitive terms
            is_sensitive = any(s in key.lower() for s in sensitive_keys)

            if is_sensitive:
                sanitized[key] = "[REDACTED]"
            elif isinstance(value, str) and len(value) > 1000:
                # Truncate large values
                sanitized[key] = f"[{len(value)} chars]"
            elif isinstance(value, (list, dict)) and len(str(value)) > 1000:
                sanitized[key] = f"[{type(value).__name__} with {len(value)} items]"
            else:
                sanitized[key] = value

        return sanitized

    def get_usage_for_template(
        self,
        template_id: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> List[TemplateUsageRecord]:
        """
        Get all usage records for a specific template.

        Args:
            template_id: The template ID
            start_time: Optional start filter
            end_time: Optional end filter

        Returns:
            List of usage records
        """
        records = self._records_by_template.get(template_id, [])

        if start_time:
            records = [r for r in records if r.timestamp >= start_time]
        if end_time:
            records = [r for r in records if r.timestamp <= end_time]

        return records

    def get_usage_by_user(
        self,
        user_id: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> List[TemplateUsageRecord]:
        """
        Get all template usage by a specific user/agent.

        Args:
            user_id: The user or agent ID
            start_time: Optional start filter
            end_time: Optional end filter

        Returns:
            List of usage records
        """
        records = self._records_by_user.get(user_id, [])

        if start_time:
            records = [r for r in records if r.timestamp >= start_time]
        if end_time:
            records = [r for r in records if r.timestamp <= end_time]

        return records

    def query_usage(
        self,
        template_id: Optional[str] = None,
        template_category: Optional[str] = None,
        used_by: Optional[str] = None,
        used_by_type: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        context_type: Optional[str] = None,
        has_customizations: Optional[bool] = None,
        page: int = 1,
        page_size: int = 100
    ) -> AuditQueryResult:
        """
        Query template usage records with filters.

        Args:
            template_id: Filter by template
            template_category: Filter by category
            used_by: Filter by user/agent
            used_by_type: Filter by user type
            start_time: Start of time range
            end_time: End of time range
            context_type: Filter by context type
            has_customizations: Filter by customization
            page: Page number
            page_size: Records per page

        Returns:
            AuditQueryResult with matching records
        """
        import time
        start = time.time()

        filtered = self._records.copy()

        if template_id:
            filtered = [r for r in filtered if r.template_id == template_id]

        if template_category:
            filtered = [r for r in filtered if r.template_category == template_category]

        if used_by:
            filtered = [r for r in filtered if r.used_by == used_by]

        if used_by_type:
            filtered = [r for r in filtered if r.used_by_type == used_by_type]

        if start_time:
            filtered = [r for r in filtered if r.timestamp >= start_time]

        if end_time:
            filtered = [r for r in filtered if r.timestamp <= end_time]

        if context_type:
            filtered = [r for r in filtered if r.context_type == context_type]

        if has_customizations is not None:
            if has_customizations:
                filtered = [r for r in filtered if r.customizations_applied]
            else:
                filtered = [r for r in filtered if not r.customizations_applied]

        # Pagination
        total_count = len(filtered)
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        page_records = filtered[start_idx:end_idx]

        query_time_ms = int((time.time() - start) * 1000)

        return AuditQueryResult(
            records=[r.to_dict() for r in page_records],
            total_count=total_count,
            page=page,
            page_size=page_size,
            query_time_ms=query_time_ms,
            filters_applied={
                "template_id": template_id,
                "template_category": template_category,
                "used_by": used_by,
                "used_by_type": used_by_type,
                "start_time": start_time.isoformat() if start_time else None,
                "end_time": end_time.isoformat() if end_time else None,
                "context_type": context_type,
                "has_customizations": has_customizations
            }
        )

    def get_statistics(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Get statistics about template usage.

        Args:
            start_time: Start of time range
            end_time: End of time range

        Returns:
            Dictionary of statistics
        """
        filtered = self._records.copy()

        if start_time:
            filtered = [r for r in filtered if r.timestamp >= start_time]
        if end_time:
            filtered = [r for r in filtered if r.timestamp <= end_time]

        # Usage by template
        by_template = {}
        for record in filtered:
            by_template[record.template_id] = by_template.get(record.template_id, 0) + 1

        # Usage by category
        by_category = {}
        for record in filtered:
            by_category[record.template_category] = (
                by_category.get(record.template_category, 0) + 1
            )

        # Usage by user type
        by_user_type = {}
        for record in filtered:
            by_user_type[record.used_by_type] = (
                by_user_type.get(record.used_by_type, 0) + 1
            )

        # Customization stats
        with_customizations = sum(
            1 for r in filtered if r.customizations_applied
        )

        # Top templates
        top_templates = sorted(
            by_template.items(),
            key=lambda x: x[1],
            reverse=True
        )[:10]

        return {
            "total_usages": len(filtered),
            "unique_templates_used": len(by_template),
            "usage_by_template": by_template,
            "usage_by_category": by_category,
            "usage_by_user_type": by_user_type,
            "customization_rate": (
                round(with_customizations / len(filtered), 3) if filtered else 0
            ),
            "top_templates": [
                {"template_id": tid, "usage_count": count}
                for tid, count in top_templates
            ],
            "total_output_bytes": sum(r.output_size_bytes for r in filtered),
            "unique_users": len(set(r.used_by for r in filtered))
        }

    def get_template_popularity(
        self,
        top_n: int = 10,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """
        Get the most popular templates.

        Args:
            top_n: Number of templates to return
            start_time: Start of time range
            end_time: End of time range

        Returns:
            List of template popularity data
        """
        filtered = self._records.copy()

        if start_time:
            filtered = [r for r in filtered if r.timestamp >= start_time]
        if end_time:
            filtered = [r for r in filtered if r.timestamp <= end_time]

        # Count by template
        template_stats = {}
        for record in filtered:
            tid = record.template_id
            if tid not in template_stats:
                template_stats[tid] = {
                    "template_id": tid,
                    "template_name": record.template_name,
                    "template_category": record.template_category,
                    "usage_count": 0,
                    "unique_users": set(),
                    "total_output_bytes": 0
                }

            template_stats[tid]["usage_count"] += 1
            template_stats[tid]["unique_users"].add(record.used_by)
            template_stats[tid]["total_output_bytes"] += record.output_size_bytes

        # Convert sets to counts and sort
        result = []
        for stats in template_stats.values():
            stats["unique_users"] = len(stats["unique_users"])
            result.append(stats)

        result.sort(key=lambda x: x["usage_count"], reverse=True)
        return result[:top_n]

    def _persist_to_storage(self) -> None:
        """Persist records to storage."""
        if not self._records:
            return

        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        filename = f"template_usage_{timestamp}.json"
        filepath = self.storage_path / filename

        records_data = [r.to_dict() for r in self._records]

        with open(filepath, "w") as f:
            json.dump(records_data, f, indent=2)

        logger.info(
            f"Persisted {len(self._records)} template usage records to {filepath}"
        )

        self._records = []
        self._records_by_template = {}
        self._records_by_user = {}

    def export_for_audit(
        self,
        start_time: datetime,
        end_time: datetime,
        output_path: Path
    ) -> Dict[str, Any]:
        """
        Export template usage for external audit.

        Args:
            start_time: Start of export range
            end_time: End of export range
            output_path: Path for export file

        Returns:
            Export metadata
        """
        result = self.query_usage(
            start_time=start_time,
            end_time=end_time,
            page_size=100000
        )

        export_data = {
            "export_timestamp": datetime.utcnow().isoformat(),
            "date_range": {
                "start": start_time.isoformat(),
                "end": end_time.isoformat()
            },
            "total_records": result.total_count,
            "registered_templates": len(self._template_registry),
            "records": result.records
        }

        with open(output_path, "w") as f:
            json.dump(export_data, f, indent=2)

        with open(output_path, "rb") as f:
            file_hash = hashlib.sha256(f.read()).hexdigest()

        return {
            "export_path": str(output_path),
            "record_count": result.total_count,
            "file_hash": file_hash,
            "exported_at": datetime.utcnow().isoformat()
        }

    def clear(self) -> None:
        """Clear all in-memory records."""
        self._records = []
        self._records_by_template = {}
        self._records_by_user = {}
