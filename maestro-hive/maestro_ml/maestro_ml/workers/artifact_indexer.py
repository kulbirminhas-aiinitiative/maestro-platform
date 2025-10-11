#!/usr/bin/env python3
"""
Artifact Indexer Worker

Background worker that:
- Indexes artifacts for fast search
- Updates impact scores based on usage
- Cleanups old/unused artifacts
- Generates artifact recommendations

Runs on a configurable schedule (default: 1 hour).
"""

import asyncio
import logging
from datetime import datetime, timedelta

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from maestro_ml.config.settings import get_settings
from maestro_ml.core.database import AsyncSessionLocal
from maestro_ml.models.database import Artifact, ArtifactUsage
from maestro_ml.services.artifact_registry import ArtifactRegistry

settings = get_settings()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ArtifactIndexer:
    """Background worker for artifact indexing and maintenance"""

    def __init__(self):
        self.artifact_registry = ArtifactRegistry()
        self.indexing_interval = 3600  # 1 hour
        self.running = False

    async def update_artifact_scores(self, session: AsyncSession):
        """Update impact scores for all artifacts"""
        try:
            logger.info("Updating artifact impact scores...")

            # Get all artifacts
            stmt = select(Artifact).where(Artifact.is_active == True)
            result = await session.execute(stmt)
            artifacts = result.scalars().all()

            updated_count = 0
            for artifact in artifacts:
                try:
                    # Update impact score based on usage
                    new_score = await self.artifact_registry.update_impact_score(
                        session, str(artifact.id)
                    )
                    if new_score > 0:
                        updated_count += 1
                        logger.debug(f"Updated {artifact.name}: {new_score:.2f}")
                except Exception as e:
                    logger.error(f"Error updating score for {artifact.name}: {e}")

            logger.info(f"Updated impact scores for {updated_count} artifacts")

        except Exception as e:
            logger.error(f"Error updating artifact scores: {e}")

    async def cleanup_old_artifacts(self, session: AsyncSession):
        """Mark unused artifacts as inactive"""
        try:
            logger.info("Checking for unused artifacts...")

            # Find artifacts not used in 90 days
            cutoff_date = datetime.utcnow() - timedelta(days=90)

            stmt = select(Artifact).where(
                and_(
                    Artifact.is_active == True,
                    Artifact.usage_count == 0
                )
            )
            result = await session.execute(stmt)
            unused_artifacts = result.scalars().all()

            archived_count = 0
            for artifact in unused_artifacts:
                # Check if artifact was created more than 90 days ago
                if artifact.created_at < cutoff_date:
                    artifact.is_active = False
                    archived_count += 1
                    logger.info(f"Archived unused artifact: {artifact.name}")

            await session.commit()

            logger.info(f"Archived {archived_count} unused artifacts")

        except Exception as e:
            logger.error(f"Error cleaning up artifacts: {e}")

    async def generate_trending_artifacts(self, session: AsyncSession):
        """Identify trending artifacts (recently popular)"""
        try:
            logger.info("Identifying trending artifacts...")

            # Get usage from last 7 days
            cutoff_date = datetime.utcnow() - timedelta(days=7)

            stmt = select(
                ArtifactUsage.artifact_id,
                Artifact.name
            ).join(
                Artifact, ArtifactUsage.artifact_id == Artifact.id
            ).where(
                ArtifactUsage.used_at >= cutoff_date
            )

            result = await session.execute(stmt)
            recent_usage = result.all()

            # Count usage per artifact
            usage_counts = {}
            for artifact_id, name in recent_usage:
                usage_counts[artifact_id] = usage_counts.get(artifact_id, 0) + 1

            # Log top 10 trending
            trending = sorted(usage_counts.items(), key=lambda x: x[1], reverse=True)[:10]
            logger.info("Top 10 trending artifacts:")
            for artifact_id, count in trending:
                logger.info(f"  - {artifact_id}: {count} uses this week")

        except Exception as e:
            logger.error(f"Error generating trending artifacts: {e}")

    async def run_maintenance_cycle(self):
        """Run one complete maintenance cycle"""
        async with AsyncSessionLocal() as session:
            try:
                logger.info("Starting artifact maintenance cycle...")

                # Update impact scores
                await self.update_artifact_scores(session)

                # Cleanup old artifacts
                await self.cleanup_old_artifacts(session)

                # Generate trending list
                await self.generate_trending_artifacts(session)

                logger.info("Maintenance cycle completed successfully")

            except Exception as e:
                logger.error(f"Error in maintenance cycle: {e}")

    async def run(self):
        """Main worker loop"""
        self.running = True
        logger.info(f"Artifact indexer started (interval: {self.indexing_interval}s)")

        while self.running:
            try:
                start_time = datetime.now()
                logger.info("Starting indexing cycle...")

                await self.run_maintenance_cycle()

                # Calculate next run time
                elapsed = (datetime.now() - start_time).total_seconds()
                sleep_time = max(0, self.indexing_interval - elapsed)

                logger.info(f"Cycle completed in {elapsed:.2f}s. Next run in {sleep_time:.2f}s")
                await asyncio.sleep(sleep_time)

            except asyncio.CancelledError:
                logger.info("Worker cancelled, shutting down...")
                break
            except Exception as e:
                logger.error(f"Unexpected error in worker loop: {e}")
                await asyncio.sleep(300)  # Wait 5 minutes on error

        self.running = False
        logger.info("Artifact indexer stopped")

    def stop(self):
        """Stop the worker"""
        self.running = False


async def main():
    """Entry point for artifact indexer"""
    worker = ArtifactIndexer()

    try:
        await worker.run()
    except KeyboardInterrupt:
        logger.info("Received shutdown signal")
        worker.stop()


if __name__ == "__main__":
    asyncio.run(main())
