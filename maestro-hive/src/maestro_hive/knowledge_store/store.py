"""
Knowledge Store - Core storage and management for knowledge artifacts

Implements:
- AC-2543-1: Store knowledge artifacts
- AC-2543-3: Version control for updates
"""
import json
import logging
import threading
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set
from uuid import UUID

from .models import (
    KnowledgeArtifact,
    KnowledgeType,
    KnowledgeStatus,
    KnowledgeVersion,
    KnowledgeMetadata,
    KnowledgeContribution,
    ContributorType,
)


logger = logging.getLogger(__name__)


class KnowledgeStore:
    """
    Central storage for knowledge artifacts.
    
    Features:
    - Thread-safe storage operations
    - Version history tracking
    - Domain-based organization
    - Status management
    """
    
    def __init__(self, storage_path: Optional[Path] = None):
        """
        Initialize the knowledge store.
        
        Args:
            storage_path: Path for persistent storage
        """
        self.storage_path = storage_path or Path("/tmp/knowledge_store")
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        self._artifacts: Dict[UUID, KnowledgeArtifact] = {}
        self._versions: Dict[UUID, List[KnowledgeArtifact]] = {}
        self._domain_index: Dict[str, Set[UUID]] = {}
        self._type_index: Dict[KnowledgeType, Set[UUID]] = {}
        self._lock = threading.RLock()
        
        # Load existing artifacts
        self._load_from_storage()
        
        logger.info("KnowledgeStore initialized with %d artifacts", len(self._artifacts))
    
    def _load_from_storage(self) -> None:
        """Load artifacts from storage directory."""
        for file_path in self.storage_path.glob("*.json"):
            try:
                artifact = KnowledgeArtifact.from_json(file_path.read_text())
                self._artifacts[artifact.id] = artifact
                self._index_artifact(artifact)
            except Exception as e:
                logger.error("Failed to load artifact from %s: %s", file_path, e)
    
    def _save_artifact(self, artifact: KnowledgeArtifact) -> None:
        """Save artifact to storage."""
        file_path = self.storage_path / f"{artifact.id}.json"
        file_path.write_text(artifact.to_json())
    
    def _index_artifact(self, artifact: KnowledgeArtifact) -> None:
        """Add artifact to indexes."""
        # Domain index
        domain = artifact.metadata.domain
        if domain:
            if domain not in self._domain_index:
                self._domain_index[domain] = set()
            self._domain_index[domain].add(artifact.id)
        
        # Type index
        ktype = artifact.knowledge_type
        if ktype not in self._type_index:
            self._type_index[ktype] = set()
        self._type_index[ktype].add(artifact.id)
    
    def _unindex_artifact(self, artifact: KnowledgeArtifact) -> None:
        """Remove artifact from indexes."""
        domain = artifact.metadata.domain
        if domain and domain in self._domain_index:
            self._domain_index[domain].discard(artifact.id)
        
        ktype = artifact.knowledge_type
        if ktype in self._type_index:
            self._type_index[ktype].discard(artifact.id)
    
    def store(self, artifact: KnowledgeArtifact) -> UUID:
        """
        Store a new knowledge artifact.
        
        Args:
            artifact: Artifact to store
        
        Returns:
            UUID of stored artifact
        """
        with self._lock:
            if artifact.id in self._artifacts:
                raise ValueError(f"Artifact {artifact.id} already exists")
            
            # Extract keywords if not present
            if not artifact.keywords:
                artifact.keywords = artifact.extract_keywords()
            
            # Set checksum
            artifact.version.checksum = artifact.compute_checksum()
            
            self._artifacts[artifact.id] = artifact
            self._versions[artifact.id] = []
            self._index_artifact(artifact)
            self._save_artifact(artifact)
            
            logger.info("Stored artifact: %s (%s)", artifact.title, artifact.id)
            return artifact.id
    
    def get(self, artifact_id: UUID) -> Optional[KnowledgeArtifact]:
        """Get an artifact by ID."""
        with self._lock:
            return self._artifacts.get(artifact_id)
    
    def get_by_title(self, title: str) -> Optional[KnowledgeArtifact]:
        """Get an artifact by title (case-insensitive)."""
        with self._lock:
            title_lower = title.lower()
            for artifact in self._artifacts.values():
                if artifact.title.lower() == title_lower:
                    return artifact
            return None
    
    def update(
        self,
        artifact: KnowledgeArtifact,
        bump_version: str = "patch",
        contributor_id: str = "",
        contributor_type: ContributorType = ContributorType.HUMAN,
        changelog: str = "",
    ) -> KnowledgeArtifact:
        """
        Update an existing artifact with version bump.
        
        Args:
            artifact: Updated artifact
            bump_version: Version bump type ('major', 'minor', 'patch')
            contributor_id: ID of contributor making update
            contributor_type: Type of contributor
            changelog: Description of changes
        
        Returns:
            Updated artifact
        """
        with self._lock:
            if artifact.id not in self._artifacts:
                raise ValueError(f"Artifact {artifact.id} not found")
            
            # Unindex old artifact
            old_artifact = self._artifacts[artifact.id]
            self._unindex_artifact(old_artifact)
            
            # Save to version history
            if artifact.id not in self._versions:
                self._versions[artifact.id] = []
            self._versions[artifact.id].append(
                KnowledgeArtifact.from_dict(old_artifact.to_dict())
            )
            
            # Bump version
            old_version = artifact.version
            if bump_version == "major":
                artifact.version = old_version.bump_major(contributor_id, contributor_type)
            elif bump_version == "minor":
                artifact.version = old_version.bump_minor(contributor_id, contributor_type)
            else:
                artifact.version = old_version.bump_patch(contributor_id, contributor_type)
            
            artifact.version.changelog = changelog
            artifact.version.checksum = artifact.compute_checksum()
            artifact.version_history.append(KnowledgeVersion.from_dict(old_version.to_dict()))
            artifact.updated_at = datetime.utcnow()
            
            # Re-extract keywords
            artifact.keywords = artifact.extract_keywords()
            
            # Update storage
            self._artifacts[artifact.id] = artifact
            self._index_artifact(artifact)
            self._save_artifact(artifact)
            
            logger.info(
                "Updated artifact %s: v%s -> v%s",
                artifact.id,
                old_version,
                artifact.version,
            )
            return artifact
    
    def delete(self, artifact_id: UUID, hard_delete: bool = False) -> bool:
        """
        Delete an artifact.
        
        Args:
            artifact_id: ID of artifact to delete
            hard_delete: If True, permanently remove. If False, archive.
        
        Returns:
            True if successful
        """
        with self._lock:
            if artifact_id not in self._artifacts:
                return False
            
            artifact = self._artifacts[artifact_id]
            
            if hard_delete:
                self._unindex_artifact(artifact)
                del self._artifacts[artifact_id]
                if artifact_id in self._versions:
                    del self._versions[artifact_id]
                
                file_path = self.storage_path / f"{artifact_id}.json"
                if file_path.exists():
                    file_path.unlink()
                
                logger.info("Hard deleted artifact: %s", artifact_id)
            else:
                artifact.archive()
                self._save_artifact(artifact)
                logger.info("Archived artifact: %s", artifact_id)
            
            return True
    
    def get_version(
        self,
        artifact_id: UUID,
        version: str,
    ) -> Optional[KnowledgeArtifact]:
        """
        Get a specific version of an artifact.
        
        Args:
            artifact_id: Artifact ID
            version: Version string (e.g., '1.2.3')
        
        Returns:
            Artifact at specified version or None
        """
        with self._lock:
            if artifact_id not in self._versions:
                return None
            
            target = KnowledgeVersion.from_string(version)
            
            # Check history
            for artifact in self._versions[artifact_id]:
                v = artifact.version
                if v.major == target.major and v.minor == target.minor and v.patch == target.patch:
                    return artifact
            
            # Check current
            current = self._artifacts.get(artifact_id)
            if current:
                v = current.version
                if v.major == target.major and v.minor == target.minor and v.patch == target.patch:
                    return current
            
            return None
    
    def list_versions(self, artifact_id: UUID) -> List[str]:
        """List all versions of an artifact."""
        with self._lock:
            versions = []
            
            if artifact_id in self._versions:
                for artifact in self._versions[artifact_id]:
                    versions.append(str(artifact.version))
            
            current = self._artifacts.get(artifact_id)
            if current:
                versions.append(str(current.version))
            
            return versions
    
    def list_by_domain(
        self,
        domain: str,
        include_archived: bool = False,
    ) -> List[KnowledgeArtifact]:
        """List all artifacts in a domain."""
        with self._lock:
            if domain not in self._domain_index:
                return []
            
            results = []
            for aid in self._domain_index[domain]:
                artifact = self._artifacts.get(aid)
                if artifact:
                    if include_archived or artifact.status != KnowledgeStatus.ARCHIVED:
                        results.append(artifact)
            
            return results
    
    def list_by_type(
        self,
        knowledge_type: KnowledgeType,
        include_archived: bool = False,
    ) -> List[KnowledgeArtifact]:
        """List all artifacts of a specific type."""
        with self._lock:
            if knowledge_type not in self._type_index:
                return []
            
            results = []
            for aid in self._type_index[knowledge_type]:
                artifact = self._artifacts.get(aid)
                if artifact:
                    if include_archived or artifact.status != KnowledgeStatus.ARCHIVED:
                        results.append(artifact)
            
            return results
    
    def list_all(
        self,
        include_archived: bool = False,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        List all artifacts with summary info.
        
        Args:
            include_archived: Include archived artifacts
            limit: Maximum results
        
        Returns:
            List of artifact summaries
        """
        with self._lock:
            summaries = []
            for artifact in list(self._artifacts.values())[:limit]:
                if not include_archived and artifact.status == KnowledgeStatus.ARCHIVED:
                    continue
                
                summaries.append({
                    "id": str(artifact.id),
                    "title": artifact.title,
                    "knowledge_type": artifact.knowledge_type.value,
                    "status": artifact.status.value,
                    "domain": artifact.metadata.domain,
                    "version": str(artifact.version),
                    "usage_count": artifact.metadata.usage_count,
                    "created_at": artifact.created_at.isoformat(),
                    "updated_at": artifact.updated_at.isoformat(),
                })
            
            return summaries
    
    def get_stats(self) -> Dict[str, Any]:
        """Get store statistics."""
        with self._lock:
            type_counts = {}
            for ktype, ids in self._type_index.items():
                type_counts[ktype.value] = len(ids)
            
            status_counts = {}
            for artifact in self._artifacts.values():
                status = artifact.status.value
                status_counts[status] = status_counts.get(status, 0) + 1
            
            return {
                "total_artifacts": len(self._artifacts),
                "domains": len(self._domain_index),
                "type_counts": type_counts,
                "status_counts": status_counts,
                "total_versions": sum(len(v) for v in self._versions.values()),
            }
