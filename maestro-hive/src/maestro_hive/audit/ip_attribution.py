"""
IP Attribution Tracker for AI vs Human contribution tracking.

EU AI Act Article 12 Compliance:
Tracks and attributes contributions to AI vs human sources
for intellectual property clarity and accountability.
"""

import hashlib
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import UUID

from .models import (
    IPAttributionRecord,
    ContributorType,
    AuditQueryResult
)


logger = logging.getLogger(__name__)


class Contribution:
    """Represents a single contribution to an artifact."""

    def __init__(
        self,
        contributor_id: str,
        contributor_type: ContributorType,
        contribution_type: str,
        description: str,
        size_bytes: int = 0,
        timestamp: Optional[datetime] = None
    ):
        """
        Initialize a contribution.

        Args:
            contributor_id: ID of contributor (model name or user ID)
            contributor_type: Type of contributor
            contribution_type: What was contributed (e.g., "code", "review")
            description: Description of contribution
            size_bytes: Size of contribution in bytes
            timestamp: When contribution was made
        """
        self.contributor_id = contributor_id
        self.contributor_type = contributor_type
        self.contribution_type = contribution_type
        self.description = description
        self.size_bytes = size_bytes
        self.timestamp = timestamp or datetime.utcnow()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "contributor_id": self.contributor_id,
            "contributor_type": self.contributor_type.value,
            "contribution_type": self.contribution_type,
            "description": self.description,
            "size_bytes": self.size_bytes,
            "timestamp": self.timestamp.isoformat()
        }


class IPAttributionTracker:
    """
    Tracks intellectual property attribution for artifacts.

    Maintains clear records of AI vs human contributions
    for compliance and IP management.
    """

    def __init__(
        self,
        storage_path: Optional[Path] = None,
        max_records_in_memory: int = 10000,
        auto_persist: bool = True
    ):
        """
        Initialize the IP attribution tracker.

        Args:
            storage_path: Path for persistent storage
            max_records_in_memory: Maximum records in memory
            auto_persist: Whether to auto-persist
        """
        self.storage_path = storage_path or Path("./audit/ip_attribution")
        self.storage_path.mkdir(parents=True, exist_ok=True)

        self.max_records_in_memory = max_records_in_memory
        self.auto_persist = auto_persist

        self._records: List[IPAttributionRecord] = []
        self._records_by_artifact: Dict[str, IPAttributionRecord] = {}
        self._records_by_project: Dict[str, List[IPAttributionRecord]] = {}

        logger.info(
            f"IPAttributionTracker initialized with storage at {self.storage_path}"
        )

    def create_attribution(
        self,
        artifact_id: str,
        artifact_type: str,
        artifact_name: str,
        project_id: str = "",
        workflow_id: str = ""
    ) -> IPAttributionRecord:
        """
        Create a new attribution record for an artifact.

        Args:
            artifact_id: Unique artifact identifier
            artifact_type: Type of artifact
            artifact_name: Human-readable name
            project_id: Project identifier
            workflow_id: Workflow identifier

        Returns:
            New IPAttributionRecord
        """
        record = IPAttributionRecord(
            artifact_id=artifact_id,
            artifact_type=artifact_type,
            artifact_name=artifact_name,
            project_id=project_id,
            workflow_id=workflow_id,
            contributor_type=ContributorType.HYBRID,
            ai_contribution_percent=0.0,
            human_contribution_percent=0.0
        )

        self._records.append(record)
        self._records_by_artifact[artifact_id] = record

        if project_id:
            if project_id not in self._records_by_project:
                self._records_by_project[project_id] = []
            self._records_by_project[project_id].append(record)

        logger.debug(f"Created attribution record for artifact: {artifact_id}")

        return record

    def add_ai_contribution(
        self,
        artifact_id: str,
        model_name: str,
        contribution_type: str,
        description: str,
        size_bytes: int = 0,
        prompt_used: bool = True
    ) -> Optional[IPAttributionRecord]:
        """
        Add an AI contribution to an artifact.

        Args:
            artifact_id: Artifact identifier
            model_name: Name of AI model used
            contribution_type: Type of contribution
            description: Description of contribution
            size_bytes: Size of contribution
            prompt_used: Whether a prompt was used

        Returns:
            Updated IPAttributionRecord or None if not found
        """
        record = self._records_by_artifact.get(artifact_id)
        if not record:
            logger.warning(f"No attribution record found for: {artifact_id}")
            return None

        contribution = Contribution(
            contributor_id=model_name,
            contributor_type=ContributorType.AI_GENERATED,
            contribution_type=contribution_type,
            description=description,
            size_bytes=size_bytes
        )

        record.contributions.append(contribution.to_dict())

        if model_name not in record.ai_models_used:
            record.ai_models_used.append(model_name)

        if prompt_used:
            record.ai_prompts_count += 1

        # Recalculate percentages
        self._recalculate_percentages(record)

        logger.debug(
            f"Added AI contribution to {artifact_id}: "
            f"{contribution_type} by {model_name}"
        )

        return record

    def add_human_contribution(
        self,
        artifact_id: str,
        user_id: str,
        contribution_type: str,
        description: str,
        size_bytes: int = 0,
        is_review: bool = False,
        is_modification: bool = False
    ) -> Optional[IPAttributionRecord]:
        """
        Add a human contribution to an artifact.

        Args:
            artifact_id: Artifact identifier
            user_id: User identifier
            contribution_type: Type of contribution
            description: Description of contribution
            size_bytes: Size of contribution
            is_review: Whether this is a review action
            is_modification: Whether this modifies existing content

        Returns:
            Updated IPAttributionRecord or None if not found
        """
        record = self._records_by_artifact.get(artifact_id)
        if not record:
            logger.warning(f"No attribution record found for: {artifact_id}")
            return None

        contribution = Contribution(
            contributor_id=user_id,
            contributor_type=ContributorType.HUMAN_AUTHORED,
            contribution_type=contribution_type,
            description=description,
            size_bytes=size_bytes
        )

        record.contributions.append(contribution.to_dict())

        if user_id not in record.human_contributors:
            record.human_contributors.append(user_id)

        if is_review:
            record.human_review_performed = True

        if is_modification:
            record.human_modifications_count += 1

        # Recalculate percentages
        self._recalculate_percentages(record)

        logger.debug(
            f"Added human contribution to {artifact_id}: "
            f"{contribution_type} by {user_id}"
        )

        return record

    def _recalculate_percentages(self, record: IPAttributionRecord) -> None:
        """
        Recalculate AI vs human contribution percentages.

        Uses size-weighted calculation when available,
        falls back to count-based calculation.
        """
        total_size = sum(c.get("size_bytes", 0) for c in record.contributions)
        ai_size = sum(
            c.get("size_bytes", 0)
            for c in record.contributions
            if c.get("contributor_type") == ContributorType.AI_GENERATED.value
        )
        human_size = sum(
            c.get("size_bytes", 0)
            for c in record.contributions
            if c.get("contributor_type") == ContributorType.HUMAN_AUTHORED.value
        )

        if total_size > 0:
            # Size-weighted calculation
            record.ai_contribution_percent = round(ai_size / total_size * 100, 2)
            record.human_contribution_percent = round(human_size / total_size * 100, 2)
        else:
            # Count-based fallback
            total_count = len(record.contributions)
            if total_count > 0:
                ai_count = sum(
                    1 for c in record.contributions
                    if c.get("contributor_type") == ContributorType.AI_GENERATED.value
                )
                human_count = sum(
                    1 for c in record.contributions
                    if c.get("contributor_type") == ContributorType.HUMAN_AUTHORED.value
                )
                record.ai_contribution_percent = round(ai_count / total_count * 100, 2)
                record.human_contribution_percent = round(human_count / total_count * 100, 2)

        # Determine overall contributor type
        if record.ai_contribution_percent >= 90:
            record.contributor_type = ContributorType.AI_GENERATED
        elif record.human_contribution_percent >= 90:
            record.contributor_type = ContributorType.HUMAN_AUTHORED
        elif record.ai_contribution_percent > 50:
            record.contributor_type = ContributorType.AI_ASSISTED
        else:
            record.contributor_type = ContributorType.HYBRID

    def get_attribution(self, artifact_id: str) -> Optional[IPAttributionRecord]:
        """
        Get the attribution record for an artifact.

        Args:
            artifact_id: Artifact identifier

        Returns:
            IPAttributionRecord or None
        """
        return self._records_by_artifact.get(artifact_id)

    def get_attributions_for_project(
        self,
        project_id: str
    ) -> List[IPAttributionRecord]:
        """
        Get all attributions for a project.

        Args:
            project_id: Project identifier

        Returns:
            List of IPAttributionRecords
        """
        return self._records_by_project.get(project_id, [])

    def query_attributions(
        self,
        artifact_type: Optional[str] = None,
        contributor_type: Optional[ContributorType] = None,
        project_id: Optional[str] = None,
        min_ai_percent: Optional[float] = None,
        max_ai_percent: Optional[float] = None,
        has_human_review: Optional[bool] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        page: int = 1,
        page_size: int = 100
    ) -> AuditQueryResult:
        """
        Query attribution records with filters.

        Args:
            artifact_type: Filter by artifact type
            contributor_type: Filter by overall contributor type
            project_id: Filter by project
            min_ai_percent: Minimum AI contribution percentage
            max_ai_percent: Maximum AI contribution percentage
            has_human_review: Filter by human review status
            start_time: Start of time range
            end_time: End of time range
            page: Page number
            page_size: Records per page

        Returns:
            AuditQueryResult with matching records
        """
        import time
        start = time.time()

        filtered = self._records.copy()

        if artifact_type:
            filtered = [r for r in filtered if r.artifact_type == artifact_type]

        if contributor_type:
            filtered = [r for r in filtered if r.contributor_type == contributor_type]

        if project_id:
            filtered = [r for r in filtered if r.project_id == project_id]

        if min_ai_percent is not None:
            filtered = [
                r for r in filtered
                if r.ai_contribution_percent >= min_ai_percent
            ]

        if max_ai_percent is not None:
            filtered = [
                r for r in filtered
                if r.ai_contribution_percent <= max_ai_percent
            ]

        if has_human_review is not None:
            filtered = [
                r for r in filtered
                if r.human_review_performed == has_human_review
            ]

        if start_time:
            filtered = [r for r in filtered if r.timestamp >= start_time]

        if end_time:
            filtered = [r for r in filtered if r.timestamp <= end_time]

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
                "artifact_type": artifact_type,
                "contributor_type": contributor_type.value if contributor_type else None,
                "project_id": project_id,
                "min_ai_percent": min_ai_percent,
                "max_ai_percent": max_ai_percent,
                "has_human_review": has_human_review
            }
        )

    def get_statistics(
        self,
        project_id: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Get statistics about IP attribution.

        Args:
            project_id: Optional project filter
            start_time: Start of time range
            end_time: End of time range

        Returns:
            Dictionary of statistics
        """
        filtered = self._records.copy()

        if project_id:
            filtered = self._records_by_project.get(project_id, [])

        if start_time:
            filtered = [r for r in filtered if r.timestamp >= start_time]
        if end_time:
            filtered = [r for r in filtered if r.timestamp <= end_time]

        # Count by contributor type
        by_type = {}
        for record in filtered:
            type_key = record.contributor_type.value
            by_type[type_key] = by_type.get(type_key, 0) + 1

        # Average percentages
        avg_ai = (
            sum(r.ai_contribution_percent for r in filtered) / len(filtered)
            if filtered else 0
        )
        avg_human = (
            sum(r.human_contribution_percent for r in filtered) / len(filtered)
            if filtered else 0
        )

        # Review stats
        reviewed = sum(1 for r in filtered if r.human_review_performed)

        # Model usage
        all_models = []
        for record in filtered:
            all_models.extend(record.ai_models_used)
        model_counts = {}
        for model in all_models:
            model_counts[model] = model_counts.get(model, 0) + 1

        return {
            "total_artifacts": len(filtered),
            "by_contributor_type": by_type,
            "average_ai_contribution_percent": round(avg_ai, 2),
            "average_human_contribution_percent": round(avg_human, 2),
            "human_reviewed_count": reviewed,
            "human_review_rate": round(reviewed / len(filtered), 3) if filtered else 0,
            "ai_models_used": model_counts,
            "unique_human_contributors": len(
                set(c for r in filtered for c in r.human_contributors)
            ),
            "total_contributions": sum(len(r.contributions) for r in filtered)
        }

    def generate_ip_report(
        self,
        artifact_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Generate a detailed IP report for an artifact.

        Args:
            artifact_id: Artifact identifier

        Returns:
            Detailed IP report or None
        """
        record = self._records_by_artifact.get(artifact_id)
        if not record:
            return None

        return {
            "artifact_id": record.artifact_id,
            "artifact_name": record.artifact_name,
            "artifact_type": record.artifact_type,
            "generated_at": datetime.utcnow().isoformat(),
            "ip_classification": record.contributor_type.value,
            "contribution_breakdown": {
                "ai_percent": record.ai_contribution_percent,
                "human_percent": record.human_contribution_percent,
                "other_percent": max(
                    0,
                    100 - record.ai_contribution_percent - record.human_contribution_percent
                )
            },
            "ai_details": {
                "models_used": record.ai_models_used,
                "prompts_count": record.ai_prompts_count,
                "contributions": [
                    c for c in record.contributions
                    if c.get("contributor_type") == ContributorType.AI_GENERATED.value
                ]
            },
            "human_details": {
                "contributors": record.human_contributors,
                "review_performed": record.human_review_performed,
                "modifications_count": record.human_modifications_count,
                "contributions": [
                    c for c in record.contributions
                    if c.get("contributor_type") == ContributorType.HUMAN_AUTHORED.value
                ]
            },
            "compliance_notes": self._generate_compliance_notes(record)
        }

    def _generate_compliance_notes(
        self,
        record: IPAttributionRecord
    ) -> List[str]:
        """Generate compliance notes for an attribution record."""
        notes = []

        if record.ai_contribution_percent >= 90:
            notes.append(
                "Artifact is predominantly AI-generated. "
                "May have limited IP protection in some jurisdictions."
            )

        if record.ai_contribution_percent > 0 and not record.human_review_performed:
            notes.append(
                "AI contributions present but no human review recorded. "
                "Consider human review for quality assurance."
            )

        if record.contributor_type == ContributorType.HYBRID:
            notes.append(
                "Hybrid contribution. IP ownership may depend on "
                "significance of human creative contributions."
            )

        if not notes:
            notes.append("No compliance concerns identified.")

        return notes

    def _persist_to_storage(self) -> None:
        """Persist records to storage."""
        if not self._records:
            return

        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        filename = f"ip_attribution_{timestamp}.json"
        filepath = self.storage_path / filename

        records_data = [r.to_dict() for r in self._records]

        with open(filepath, "w") as f:
            json.dump(records_data, f, indent=2)

        logger.info(
            f"Persisted {len(self._records)} IP attribution records to {filepath}"
        )

    def export_for_audit(
        self,
        start_time: datetime,
        end_time: datetime,
        output_path: Path
    ) -> Dict[str, Any]:
        """
        Export IP attributions for external audit.

        Args:
            start_time: Start of export range
            end_time: End of export range
            output_path: Path for export file

        Returns:
            Export metadata
        """
        result = self.query_attributions(
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
        self._records_by_artifact = {}
        self._records_by_project = {}
