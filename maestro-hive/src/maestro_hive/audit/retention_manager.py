"""
Retention Policy Manager for data lifecycle management.

EU AI Act Article 12 Compliance:
Implements configurable retention policies with automatic
archival to meet compliance requirements.
"""

import gzip
import hashlib
import json
import logging
import os
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID, uuid4

from .models import (
    RetentionPolicy,
    RetentionTier,
    AuditEventType
)


logger = logging.getLogger(__name__)


class RetentionManager:
    """
    Manages data retention policies and automatic archival.

    Ensures compliance with data retention requirements
    while optimizing storage costs.
    """

    def __init__(
        self,
        hot_storage_path: Optional[Path] = None,
        warm_storage_path: Optional[Path] = None,
        cold_storage_path: Optional[Path] = None,
        glacier_storage_path: Optional[Path] = None
    ):
        """
        Initialize the retention manager.

        Args:
            hot_storage_path: Path for hot (immediate access) storage
            warm_storage_path: Path for warm (quick access) storage
            cold_storage_path: Path for cold (archived) storage
            glacier_storage_path: Path for glacier (long-term) storage
        """
        base_path = Path("./audit/storage")

        self.storage_paths = {
            RetentionTier.HOT: hot_storage_path or base_path / "hot",
            RetentionTier.WARM: warm_storage_path or base_path / "warm",
            RetentionTier.COLD: cold_storage_path or base_path / "cold",
            RetentionTier.GLACIER: glacier_storage_path or base_path / "glacier"
        }

        # Create directories
        for tier, path in self.storage_paths.items():
            path.mkdir(parents=True, exist_ok=True)

        self._policies: Dict[str, RetentionPolicy] = {}
        self._default_policy: Optional[RetentionPolicy] = None
        self._file_metadata: Dict[str, Dict[str, Any]] = {}

        # Initialize default policy
        self._create_default_policy()

        logger.info("RetentionManager initialized with storage tiers")

    def _create_default_policy(self) -> None:
        """Create the default retention policy."""
        self._default_policy = RetentionPolicy(
            name="default",
            description="Default retention policy for audit data",
            hot_duration_days=30,
            warm_duration_days=60,
            cold_duration_days=275,
            glacier_duration_days=2190,  # 6 years
            applies_to=[
                AuditEventType.DECISION,
                AuditEventType.LLM_CALL,
                AuditEventType.TEMPLATE_USAGE,
                AuditEventType.IP_ATTRIBUTION
            ],
            archive_destination="local",
            compress_on_archive=True,
            encrypt_on_archive=True,
            compliance_frameworks=["EU_AI_ACT"],
            legal_hold_enabled=False
        )
        self._policies["default"] = self._default_policy

    def create_policy(
        self,
        name: str,
        description: str,
        hot_duration_days: int = 30,
        warm_duration_days: int = 90,
        cold_duration_days: int = 365,
        glacier_duration_days: int = 2555,
        applies_to: Optional[List[AuditEventType]] = None,
        archive_destination: str = "local",
        compress_on_archive: bool = True,
        encrypt_on_archive: bool = True,
        compliance_frameworks: Optional[List[str]] = None,
        legal_hold_enabled: bool = False
    ) -> RetentionPolicy:
        """
        Create a new retention policy.

        Args:
            name: Policy name
            description: Policy description
            hot_duration_days: Days in hot storage
            warm_duration_days: Days in warm storage
            cold_duration_days: Days in cold storage
            glacier_duration_days: Days in glacier storage
            applies_to: Event types this policy applies to
            archive_destination: Where to archive
            compress_on_archive: Compress during archival
            encrypt_on_archive: Encrypt during archival
            compliance_frameworks: Compliance frameworks
            legal_hold_enabled: Whether legal hold is enabled

        Returns:
            Created RetentionPolicy
        """
        policy = RetentionPolicy(
            name=name,
            description=description,
            hot_duration_days=hot_duration_days,
            warm_duration_days=warm_duration_days,
            cold_duration_days=cold_duration_days,
            glacier_duration_days=glacier_duration_days,
            applies_to=applies_to or [],
            archive_destination=archive_destination,
            compress_on_archive=compress_on_archive,
            encrypt_on_archive=encrypt_on_archive,
            compliance_frameworks=compliance_frameworks or [],
            legal_hold_enabled=legal_hold_enabled
        )

        self._policies[name] = policy
        logger.info(f"Created retention policy: {name}")

        return policy

    def get_policy(self, name: str) -> Optional[RetentionPolicy]:
        """Get a policy by name."""
        return self._policies.get(name)

    def get_default_policy(self) -> RetentionPolicy:
        """Get the default retention policy."""
        return self._default_policy

    def list_policies(self) -> List[RetentionPolicy]:
        """List all retention policies."""
        return list(self._policies.values())

    def store_file(
        self,
        file_path: Path,
        event_type: AuditEventType,
        policy_name: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Store a file according to retention policy.

        Args:
            file_path: Path to file to store
            event_type: Type of audit event
            policy_name: Policy to use (or default)
            metadata: Additional metadata

        Returns:
            Storage result with location info
        """
        policy = self._policies.get(policy_name) or self._default_policy

        # Initial storage is always HOT
        tier = RetentionTier.HOT
        dest_dir = self.storage_paths[tier]

        # Generate unique filename
        file_id = str(uuid4())[:8]
        original_name = file_path.name
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        stored_name = f"{timestamp}_{file_id}_{original_name}"

        dest_path = dest_dir / stored_name

        # Copy file
        shutil.copy2(file_path, dest_path)

        # Store metadata
        self._file_metadata[stored_name] = {
            "original_name": original_name,
            "stored_at": datetime.utcnow().isoformat(),
            "event_type": event_type.value,
            "policy_name": policy.name,
            "current_tier": tier.value,
            "tier_transitions": [{
                "tier": tier.value,
                "timestamp": datetime.utcnow().isoformat()
            }],
            "file_hash": self._calculate_hash(dest_path),
            "file_size": dest_path.stat().st_size,
            "metadata": metadata or {}
        }

        logger.info(f"Stored file {original_name} as {stored_name} in {tier.value}")

        return {
            "file_id": stored_name,
            "storage_path": str(dest_path),
            "tier": tier.value,
            "policy": policy.name
        }

    def _calculate_hash(self, file_path: Path) -> str:
        """Calculate SHA-256 hash of a file."""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                sha256_hash.update(chunk)
        return sha256_hash.hexdigest()

    def process_tier_transitions(self) -> Dict[str, Any]:
        """
        Process tier transitions for all managed files.

        Moves files between storage tiers based on age
        and applicable retention policies.

        Returns:
            Summary of transitions performed
        """
        now = datetime.utcnow()
        transitions = {
            "hot_to_warm": [],
            "warm_to_cold": [],
            "cold_to_glacier": [],
            "glacier_to_deleted": [],
            "skipped_legal_hold": []
        }

        for file_id, meta in list(self._file_metadata.items()):
            stored_at = datetime.fromisoformat(meta["stored_at"])
            age_days = (now - stored_at).days

            policy_name = meta.get("policy_name", "default")
            policy = self._policies.get(policy_name, self._default_policy)

            # Check legal hold
            if policy.legal_hold_enabled:
                transitions["skipped_legal_hold"].append(file_id)
                continue

            current_tier = RetentionTier(meta["current_tier"])
            target_tier = policy.get_tier_for_age(age_days)

            if target_tier != current_tier:
                success = self._transition_file(
                    file_id, current_tier, target_tier, policy
                )
                if success:
                    transition_key = f"{current_tier.value}_to_{target_tier.value}"
                    if transition_key in transitions:
                        transitions[transition_key].append(file_id)

        total_transitions = sum(
            len(v) for k, v in transitions.items()
            if k != "skipped_legal_hold"
        )
        logger.info(f"Processed {total_transitions} tier transitions")

        return {
            "timestamp": now.isoformat(),
            "transitions": transitions,
            "total_transitions": total_transitions
        }

    def _transition_file(
        self,
        file_id: str,
        from_tier: RetentionTier,
        to_tier: RetentionTier,
        policy: RetentionPolicy
    ) -> bool:
        """
        Transition a file from one tier to another.

        Args:
            file_id: File identifier
            from_tier: Current tier
            to_tier: Target tier
            policy: Applicable policy

        Returns:
            True if transition successful
        """
        if to_tier == RetentionTier.DELETED:
            return self._delete_file(file_id, from_tier)

        source_path = self.storage_paths[from_tier] / file_id
        if not source_path.exists():
            logger.warning(f"Source file not found: {source_path}")
            return False

        dest_dir = self.storage_paths[to_tier]
        dest_name = file_id

        # Compress for cold/glacier storage
        if to_tier in (RetentionTier.COLD, RetentionTier.GLACIER):
            if policy.compress_on_archive and not file_id.endswith(".gz"):
                dest_name = f"{file_id}.gz"
                dest_path = dest_dir / dest_name

                with open(source_path, "rb") as f_in:
                    with gzip.open(dest_path, "wb") as f_out:
                        shutil.copyfileobj(f_in, f_out)
            else:
                dest_path = dest_dir / dest_name
                shutil.copy2(source_path, dest_path)
        else:
            dest_path = dest_dir / dest_name
            shutil.copy2(source_path, dest_path)

        # Remove from source tier
        source_path.unlink()

        # Update metadata
        meta = self._file_metadata.get(file_id)
        if meta:
            meta["current_tier"] = to_tier.value
            meta["tier_transitions"].append({
                "tier": to_tier.value,
                "timestamp": datetime.utcnow().isoformat()
            })
            # Update file_id if compressed
            if dest_name != file_id:
                self._file_metadata[dest_name] = meta
                del self._file_metadata[file_id]

        logger.info(f"Transitioned {file_id} from {from_tier.value} to {to_tier.value}")
        return True

    def _delete_file(self, file_id: str, from_tier: RetentionTier) -> bool:
        """Delete a file that has exceeded retention."""
        source_path = self.storage_paths[from_tier] / file_id
        if source_path.exists():
            source_path.unlink()

        if file_id in self._file_metadata:
            del self._file_metadata[file_id]

        logger.info(f"Deleted file {file_id} after retention period")
        return True

    def retrieve_file(
        self,
        file_id: str
    ) -> Tuple[Optional[Path], Optional[Dict[str, Any]]]:
        """
        Retrieve a file from storage.

        Args:
            file_id: File identifier

        Returns:
            Tuple of (file_path, metadata) or (None, None)
        """
        meta = self._file_metadata.get(file_id)
        if not meta:
            # Try with .gz extension
            gz_id = f"{file_id}.gz"
            meta = self._file_metadata.get(gz_id)
            if meta:
                file_id = gz_id

        if not meta:
            logger.warning(f"File not found in metadata: {file_id}")
            return None, None

        tier = RetentionTier(meta["current_tier"])
        file_path = self.storage_paths[tier] / file_id

        if not file_path.exists():
            logger.warning(f"File not found in storage: {file_path}")
            return None, None

        return file_path, meta

    def set_legal_hold(
        self,
        policy_name: str,
        enabled: bool
    ) -> bool:
        """
        Set legal hold on a policy.

        Args:
            policy_name: Policy name
            enabled: Whether to enable legal hold

        Returns:
            True if successful
        """
        policy = self._policies.get(policy_name)
        if not policy:
            logger.warning(f"Policy not found: {policy_name}")
            return False

        policy.legal_hold_enabled = enabled
        logger.info(
            f"Legal hold {'enabled' if enabled else 'disabled'} "
            f"for policy: {policy_name}"
        )
        return True

    def get_storage_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about storage usage.

        Returns:
            Dictionary of storage statistics
        """
        stats = {
            "by_tier": {},
            "by_event_type": {},
            "total_files": len(self._file_metadata),
            "total_size_bytes": 0
        }

        for file_id, meta in self._file_metadata.items():
            tier = meta["current_tier"]
            event_type = meta.get("event_type", "unknown")
            size = meta.get("file_size", 0)

            # By tier
            if tier not in stats["by_tier"]:
                stats["by_tier"][tier] = {"count": 0, "size_bytes": 0}
            stats["by_tier"][tier]["count"] += 1
            stats["by_tier"][tier]["size_bytes"] += size

            # By event type
            if event_type not in stats["by_event_type"]:
                stats["by_event_type"][event_type] = {"count": 0, "size_bytes": 0}
            stats["by_event_type"][event_type]["count"] += 1
            stats["by_event_type"][event_type]["size_bytes"] += size

            stats["total_size_bytes"] += size

        # Add disk usage for each tier
        for tier, path in self.storage_paths.items():
            tier_key = tier.value
            if tier_key not in stats["by_tier"]:
                stats["by_tier"][tier_key] = {"count": 0, "size_bytes": 0}

            try:
                disk_usage = sum(
                    f.stat().st_size
                    for f in path.iterdir()
                    if f.is_file()
                )
                stats["by_tier"][tier_key]["disk_usage_bytes"] = disk_usage
            except Exception:
                stats["by_tier"][tier_key]["disk_usage_bytes"] = 0

        return stats

    def get_retention_schedule(
        self,
        file_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get the retention schedule for a file.

        Args:
            file_id: File identifier

        Returns:
            Retention schedule or None
        """
        meta = self._file_metadata.get(file_id)
        if not meta:
            return None

        policy_name = meta.get("policy_name", "default")
        policy = self._policies.get(policy_name, self._default_policy)

        stored_at = datetime.fromisoformat(meta["stored_at"])

        schedule = {
            "file_id": file_id,
            "stored_at": stored_at.isoformat(),
            "policy": policy.name,
            "current_tier": meta["current_tier"],
            "transitions": []
        }

        # Calculate future transitions
        cumulative_days = 0
        tiers = [
            (RetentionTier.HOT, policy.hot_duration_days),
            (RetentionTier.WARM, policy.warm_duration_days),
            (RetentionTier.COLD, policy.cold_duration_days),
            (RetentionTier.GLACIER, policy.glacier_duration_days)
        ]

        for tier, duration in tiers:
            transition_date = stored_at + timedelta(days=cumulative_days)
            schedule["transitions"].append({
                "tier": tier.value,
                "starts": transition_date.isoformat(),
                "duration_days": duration
            })
            cumulative_days += duration

        # Deletion date
        deletion_date = stored_at + timedelta(days=cumulative_days)
        schedule["deletion_scheduled"] = deletion_date.isoformat()
        schedule["legal_hold_active"] = policy.legal_hold_enabled

        return schedule

    def export_metadata(self, output_path: Path) -> Dict[str, Any]:
        """
        Export all file metadata for backup.

        Args:
            output_path: Path for export file

        Returns:
            Export metadata
        """
        export_data = {
            "export_timestamp": datetime.utcnow().isoformat(),
            "policies": {
                name: policy.to_dict()
                for name, policy in self._policies.items()
            },
            "files": self._file_metadata
        }

        with open(output_path, "w") as f:
            json.dump(export_data, f, indent=2)

        return {
            "export_path": str(output_path),
            "policy_count": len(self._policies),
            "file_count": len(self._file_metadata),
            "exported_at": datetime.utcnow().isoformat()
        }
