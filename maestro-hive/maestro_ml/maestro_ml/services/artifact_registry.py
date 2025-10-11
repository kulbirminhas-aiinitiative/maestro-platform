#!/usr/bin/env python3
"""
Artifact Registry Service - The "Music Library"

Manages reusable ML artifacts (feature pipelines, model templates, schemas, notebooks).
Tracks usage and calculates impact scores to identify valuable components.
"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func, Text
from typing import List, Optional, Dict, Any
from datetime import datetime
import hashlib

from maestro_ml.models.database import Artifact, ArtifactUsage, ArtifactCreate, ArtifactResponse


class ArtifactRegistry:
    """Artifact registry service for managing reusable ML components"""

    async def create_artifact(
        self,
        session: AsyncSession,
        artifact_data: ArtifactCreate
    ) -> Artifact:
        """Register a new artifact in the library"""

        # Calculate content hash
        content_hash = self._calculate_hash(artifact_data.storage_path)

        artifact = Artifact(
            name=artifact_data.name,
            type=artifact_data.type,
            version=artifact_data.version,
            created_by=artifact_data.created_by,
            tags=artifact_data.tags,
            content_hash=content_hash,
            storage_path=artifact_data.storage_path,
            meta=artifact_data.metadata
        )

        session.add(artifact)
        await session.commit()
        await session.refresh(artifact)

        return artifact

    async def search_artifacts(
        self,
        session: AsyncSession,
        query: Optional[str] = None,
        artifact_type: Optional[str] = None,
        tags: Optional[List[str]] = None,
        min_impact_score: Optional[float] = None,
        limit: int = 20
    ) -> List[Artifact]:
        """
        Search artifacts by query, type, tags, and impact score

        Returns top matching artifacts sorted by impact score
        """
        stmt = select(Artifact).where(Artifact.is_active == True)

        # Filter by type
        if artifact_type:
            stmt = stmt.where(Artifact.type == artifact_type)

        # Filter by tags (any match) - works for both PostgreSQL ARRAY and SQLite JSON
        if tags:
            # For SQLite with JSONEncodedList, we need to use LIKE for pattern matching
            tag_conditions = []
            for tag in tags:
                # Use LIKE to search for the tag in the JSON string
                tag_conditions.append(Artifact.tags.cast(Text).like(f'%"{tag}"%'))
            if tag_conditions:
                stmt = stmt.where(or_(*tag_conditions))

        # Filter by minimum impact score
        if min_impact_score:
            stmt = stmt.where(Artifact.avg_impact_score >= min_impact_score)

        # Text search in name (metadata search requires jsonb support)
        if query:
            stmt = stmt.where(Artifact.name.ilike(f"%{query}%"))

        # Order by impact score (most valuable first)
        stmt = stmt.order_by(Artifact.avg_impact_score.desc()).limit(limit)

        result = await session.execute(stmt)
        return result.scalars().all()

    async def log_usage(
        self,
        session: AsyncSession,
        artifact_id: str,
        project_id: str,
        impact_score: Optional[float] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> ArtifactUsage:
        """
        Log artifact usage in a project

        This is called whenever an artifact is used. Impact score can be provided
        now or calculated later after project completion.
        """
        import uuid as uuid_lib

        # Convert string IDs to UUIDs
        artifact_uuid = uuid_lib.UUID(artifact_id) if isinstance(artifact_id, str) else artifact_id
        project_uuid = uuid_lib.UUID(project_id) if isinstance(project_id, str) else project_id

        usage = ArtifactUsage(
            artifact_id=artifact_uuid,
            project_id=project_uuid,
            impact_score=impact_score,
            context=context or {}
        )

        session.add(usage)

        # Increment usage count
        stmt = select(Artifact).where(Artifact.id == artifact_uuid)
        result = await session.execute(stmt)
        artifact = result.scalar_one()
        artifact.usage_count += 1

        await session.commit()
        await session.refresh(usage)

        return usage

    async def update_impact_score(
        self,
        session: AsyncSession,
        artifact_id: str
    ) -> float:
        """
        Calculate and update average impact score for an artifact

        Impact score = average of all usage impact scores
        Called after projects complete to update artifact value
        """
        stmt = select(func.avg(ArtifactUsage.impact_score)).where(
            and_(
                ArtifactUsage.artifact_id == artifact_id,
                ArtifactUsage.impact_score.isnot(None)
            )
        )

        result = await session.execute(stmt)
        avg_score = result.scalar() or 0.0

        # Update artifact
        stmt = select(Artifact).where(Artifact.id == artifact_id)
        result = await session.execute(stmt)
        artifact = result.scalar_one()
        artifact.avg_impact_score = avg_score

        await session.commit()

        return avg_score

    async def get_top_artifacts(
        self,
        session: AsyncSession,
        artifact_type: Optional[str] = None,
        limit: int = 10
    ) -> List[Artifact]:
        """Get top artifacts by impact score"""
        stmt = select(Artifact).where(Artifact.is_active == True)

        if artifact_type:
            stmt = stmt.where(Artifact.type == artifact_type)

        stmt = stmt.order_by(
            Artifact.avg_impact_score.desc(),
            Artifact.usage_count.desc()
        ).limit(limit)

        result = await session.execute(stmt)
        return result.scalars().all()

    async def get_artifact_analytics(
        self,
        session: AsyncSession,
        artifact_id: str
    ) -> Dict[str, Any]:
        """Get analytics for a specific artifact"""
        # Get artifact
        stmt = select(Artifact).where(Artifact.id == artifact_id)
        result = await session.execute(stmt)
        artifact = result.scalar_one()

        # Get usage statistics
        usage_stmt = select(ArtifactUsage).where(ArtifactUsage.artifact_id == artifact_id)
        usage_result = await session.execute(usage_stmt)
        usages = usage_result.scalars().all()

        # Calculate stats
        impact_scores = [u.impact_score for u in usages if u.impact_score is not None]

        return {
            "artifact_id": str(artifact_id),
            "name": artifact.name,
            "type": artifact.type,
            "version": artifact.version,
            "usage_count": artifact.usage_count,
            "avg_impact_score": artifact.avg_impact_score,
            "total_projects": len(usages),
            "impact_scores": impact_scores,
            "created_at": artifact.created_at,
            "created_by": artifact.created_by
        }

    @staticmethod
    def _calculate_hash(content: str) -> str:
        """Calculate SHA-256 hash of content"""
        return hashlib.sha256(content.encode()).hexdigest()
