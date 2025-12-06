"""
Enterprise database migration management for MAESTRO.

Provides:
- MigrationConfig for migration settings
- MigrationManager for Alembic programmatic control
- Async migration execution support
"""

import asyncio
import os
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Callable

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from .exceptions import (
    MigrationException,
    MigrationVersionConflict,
    MigrationLockException,
    MigrationNotFoundException
)


def _get_logger():
    """Lazy logger initialization to avoid circular imports."""
    try:
        from maestro_core_logging import get_logger
        return get_logger(__name__)
    except ImportError:
        import logging
        return logging.getLogger(__name__)


logger = type("LazyLogger", (), {"__getattr__": lambda self, name: getattr(_get_logger(), name)})()


# =============================================================================
# Configuration
# =============================================================================

@dataclass
class MigrationConfig:
    """
    Configuration for database migrations.

    Attributes:
        migration_location: Path to migration files (alembic/versions)
        version_table: Table name for tracking migration versions
        version_table_schema: Schema for version table (optional)
        lock_timeout: Timeout for acquiring migration lock (seconds)
        dry_run: Preview migrations without applying
        transaction_per_migration: Use separate transaction per migration
    """

    migration_location: str = "migrations"
    version_table: str = "alembic_version"
    version_table_schema: Optional[str] = None
    lock_timeout: int = 60
    dry_run: bool = False
    transaction_per_migration: bool = True

    # Advanced settings
    compare_type: bool = True
    compare_server_default: bool = False
    include_schemas: bool = True
    include_object: Optional[Callable] = None

    def __post_init__(self):
        """Validate configuration."""
        if not self.migration_location:
            raise ValueError("migration_location is required")


@dataclass
class MigrationInfo:
    """Information about a single migration."""

    revision: str
    description: str
    created_date: Optional[datetime] = None
    is_applied: bool = False
    is_head: bool = False
    down_revision: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "revision": self.revision,
            "description": self.description,
            "created_date": self.created_date.isoformat() if self.created_date else None,
            "is_applied": self.is_applied,
            "is_head": self.is_head,
            "down_revision": self.down_revision,
        }


# =============================================================================
# Migration Manager
# =============================================================================

class MigrationManager:
    """
    Programmatic Alembic migration manager.

    Provides async-compatible migration operations for:
    - Running migrations (upgrade/downgrade)
    - Creating new migrations
    - Checking migration status
    - Migration history

    Example:
        ```python
        manager = MigrationManager(
            engine=async_engine,
            migration_location="alembic/versions"
        )

        # Check current version
        current = await manager.current_revision()
        print(f"Current revision: {current}")

        # Run all pending migrations
        await manager.run_migrations()

        # Downgrade to specific revision
        await manager.downgrade("abc123")
        ```
    """

    def __init__(
        self,
        engine: AsyncEngine,
        config: Optional[MigrationConfig] = None,
        migration_location: Optional[str] = None
    ):
        """
        Initialize migration manager.

        Args:
            engine: Async SQLAlchemy engine
            config: Migration configuration
            migration_location: Override migration location from config
        """
        self._engine = engine
        self._config = config or MigrationConfig()

        if migration_location:
            self._config.migration_location = migration_location

        self._alembic_config = None
        self._initialized = False

    def _get_alembic_config(self):
        """Get or create Alembic configuration."""
        if self._alembic_config is not None:
            return self._alembic_config

        try:
            from alembic.config import Config
            from alembic.script import ScriptDirectory

            # Create minimal Alembic config
            config = Config()
            config.set_main_option("script_location", self._config.migration_location)
            config.set_main_option("version_table", self._config.version_table)

            if self._config.version_table_schema:
                config.set_main_option(
                    "version_table_schema",
                    self._config.version_table_schema
                )

            self._alembic_config = config
            return config

        except ImportError:
            raise MigrationException(
                message="Alembic is not installed. Install with: pip install alembic"
            )

    def _get_script_directory(self):
        """Get Alembic script directory."""
        from alembic.script import ScriptDirectory
        config = self._get_alembic_config()
        return ScriptDirectory.from_config(config)

    async def _run_in_thread(self, func, *args, **kwargs):
        """Run blocking function in thread pool."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, lambda: func(*args, **kwargs))

    async def initialize(self) -> None:
        """Initialize migration system and verify configuration."""
        if self._initialized:
            return

        logger.info(
            "Initializing migration manager",
            location=self._config.migration_location
        )

        # Verify migration directory exists
        migration_path = Path(self._config.migration_location)
        if not migration_path.exists():
            logger.warning(
                "Migration directory does not exist",
                path=str(migration_path)
            )

        # Verify Alembic is configured
        self._get_alembic_config()

        # Create version table if needed
        await self._ensure_version_table()

        self._initialized = True
        logger.info("Migration manager initialized")

    async def _ensure_version_table(self) -> None:
        """Ensure the version tracking table exists."""
        schema_prefix = f"{self._config.version_table_schema}." if self._config.version_table_schema else ""
        table_name = f"{schema_prefix}{self._config.version_table}"

        create_sql = f"""
        CREATE TABLE IF NOT EXISTS {table_name} (
            version_num VARCHAR(32) NOT NULL,
            CONSTRAINT {self._config.version_table}_pkc PRIMARY KEY (version_num)
        )
        """

        async with self._engine.begin() as conn:
            await conn.execute(text(create_sql))

    async def current_revision(self) -> Optional[str]:
        """
        Get the current database revision.

        Returns:
            Current revision string or None if no migrations applied
        """
        schema_prefix = f"{self._config.version_table_schema}." if self._config.version_table_schema else ""
        table_name = f"{schema_prefix}{self._config.version_table}"

        try:
            async with self._engine.begin() as conn:
                result = await conn.execute(
                    text(f"SELECT version_num FROM {table_name} ORDER BY version_num DESC LIMIT 1")
                )
                row = result.fetchone()
                return row[0] if row else None
        except Exception as e:
            logger.warning("Could not get current revision", error=str(e))
            return None

    async def head_revision(self) -> Optional[str]:
        """
        Get the latest revision in migration scripts.

        Returns:
            Head revision string or None
        """
        try:
            script = self._get_script_directory()
            heads = script.get_heads()
            return heads[0] if heads else None
        except Exception as e:
            logger.warning("Could not get head revision", error=str(e))
            return None

    async def pending_migrations(self) -> List[MigrationInfo]:
        """
        Get list of pending migrations.

        Returns:
            List of MigrationInfo for unapplied migrations
        """
        current = await self.current_revision()
        pending = []

        try:
            script = self._get_script_directory()

            for revision in script.walk_revisions():
                # Check if revision is after current
                if current is None or (
                    revision.revision != current and
                    not self._is_revision_applied(script, revision.revision, current)
                ):
                    pending.append(MigrationInfo(
                        revision=revision.revision,
                        description=revision.doc or "",
                        down_revision=revision.down_revision,
                        is_head=revision.revision in script.get_heads()
                    ))

            # Return in order (oldest first)
            pending.reverse()
            return pending

        except Exception as e:
            logger.error("Failed to get pending migrations", error=str(e))
            return []

    def _is_revision_applied(self, script, revision: str, current: str) -> bool:
        """Check if a revision has been applied (is before or equal to current)."""
        try:
            # Walk from current back to see if revision is in history
            for rev in script.iterate_revisions(current, "base"):
                if rev.revision == revision:
                    return True
            return False
        except Exception:
            return False

    async def get_history(self, limit: int = 50) -> List[MigrationInfo]:
        """
        Get migration history.

        Args:
            limit: Maximum number of migrations to return

        Returns:
            List of MigrationInfo ordered by application time (newest first)
        """
        current = await self.current_revision()
        history = []

        try:
            script = self._get_script_directory()

            for revision in script.walk_revisions():
                is_applied = current and self._is_revision_applied(
                    script, revision.revision, current
                )

                history.append(MigrationInfo(
                    revision=revision.revision,
                    description=revision.doc or "",
                    is_applied=is_applied,
                    is_head=revision.revision in script.get_heads(),
                    down_revision=revision.down_revision
                ))

                if len(history) >= limit:
                    break

            return history

        except Exception as e:
            logger.error("Failed to get migration history", error=str(e))
            return []

    async def run_migrations(self, target: str = "head") -> List[str]:
        """
        Run migrations to target revision.

        Args:
            target: Target revision ("head" for latest, or specific revision)

        Returns:
            List of applied revision IDs

        Raises:
            MigrationException: If migration fails
            MigrationLockException: If cannot acquire lock
        """
        if not self._initialized:
            await self.initialize()

        logger.info("Running migrations", target=target)

        # Acquire migration lock
        if not await self._acquire_lock():
            raise MigrationLockException(
                message="Could not acquire migration lock"
            )

        try:
            applied = await self._run_upgrade(target)

            if applied:
                logger.info(
                    "Migrations applied successfully",
                    count=len(applied),
                    revisions=applied
                )
            else:
                logger.info("No pending migrations")

            return applied

        finally:
            await self._release_lock()

    async def _run_upgrade(self, target: str) -> List[str]:
        """Run upgrade migrations."""
        try:
            from alembic import command
            from alembic.runtime.environment import EnvironmentContext
            from alembic.runtime.migration import MigrationContext

            applied = []
            config = self._get_alembic_config()
            script = self._get_script_directory()

            def do_upgrade(revision, context):
                """Migration callback."""
                return script._upgrade_revs(target, revision)

            # Run migrations synchronously (Alembic doesn't support async)
            def run_sync():
                sync_url = str(self._engine.url).replace("+asyncpg", "").replace("+aiosqlite", "")

                from sqlalchemy import create_engine
                sync_engine = create_engine(sync_url)

                with sync_engine.begin() as conn:
                    context = MigrationContext.configure(
                        conn,
                        opts={
                            "target_metadata": None,
                            "version_table": self._config.version_table,
                        }
                    )

                    with EnvironmentContext(
                        config,
                        script,
                        fn=do_upgrade,
                        as_sql=self._config.dry_run,
                        starting_rev=None,
                        destination_rev=target,
                    ) as env:
                        env.configure(
                            connection=conn,
                            target_metadata=None,
                            version_table=self._config.version_table
                        )
                        with env.begin_transaction():
                            env.run_migrations()

                sync_engine.dispose()

            await self._run_in_thread(run_sync)

            # Get list of applied revisions
            current = await self.current_revision()
            if current:
                applied.append(current)

            return applied

        except Exception as e:
            logger.error("Migration upgrade failed", error=str(e))
            raise MigrationException(
                message=f"Migration failed: {e}",
                cause=e
            )

    async def downgrade(self, target: str) -> List[str]:
        """
        Downgrade to target revision.

        Args:
            target: Target revision ("base" for none, or specific revision)

        Returns:
            List of rolled back revision IDs
        """
        if not self._initialized:
            await self.initialize()

        logger.info("Running downgrade", target=target)

        if not await self._acquire_lock():
            raise MigrationLockException(
                message="Could not acquire migration lock"
            )

        try:
            reverted = await self._run_downgrade(target)

            if reverted:
                logger.info(
                    "Downgrade completed",
                    count=len(reverted),
                    revisions=reverted
                )

            return reverted

        finally:
            await self._release_lock()

    async def _run_downgrade(self, target: str) -> List[str]:
        """Run downgrade migrations."""
        try:
            from alembic.runtime.migration import MigrationContext

            current = await self.current_revision()
            if not current:
                return []

            config = self._get_alembic_config()
            script = self._get_script_directory()

            reverted = []

            def run_sync():
                sync_url = str(self._engine.url).replace("+asyncpg", "").replace("+aiosqlite", "")

                from sqlalchemy import create_engine
                sync_engine = create_engine(sync_url)

                with sync_engine.begin() as conn:
                    context = MigrationContext.configure(
                        conn,
                        opts={"version_table": self._config.version_table}
                    )

                    # Get downgrade path
                    for rev in script.iterate_revisions(current, target):
                        if rev.revision != target:
                            reverted.append(rev.revision)
                            if not self._config.dry_run:
                                if rev.module.downgrade:
                                    rev.module.downgrade()

                    # Update version
                    if not self._config.dry_run:
                        context._update_current_rev(current, target)

                sync_engine.dispose()

            await self._run_in_thread(run_sync)
            return reverted

        except Exception as e:
            logger.error("Migration downgrade failed", error=str(e))
            raise MigrationException(
                message=f"Downgrade failed: {e}",
                cause=e
            )

    async def _acquire_lock(self) -> bool:
        """Acquire advisory lock for migrations."""
        lock_id = hash("maestro_migration_lock") % (2**31)

        try:
            async with self._engine.begin() as conn:
                result = await conn.execute(
                    text(f"SELECT pg_try_advisory_lock({lock_id})")
                )
                row = result.fetchone()
                return row[0] if row else False
        except Exception as e:
            logger.warning("Could not acquire migration lock", error=str(e))
            return True  # Proceed anyway for non-PostgreSQL

    async def _release_lock(self) -> None:
        """Release advisory lock."""
        lock_id = hash("maestro_migration_lock") % (2**31)

        try:
            async with self._engine.begin() as conn:
                await conn.execute(text(f"SELECT pg_advisory_unlock({lock_id})"))
        except Exception:
            pass

    async def stamp(self, revision: str) -> None:
        """
        Stamp database with revision without running migrations.

        Useful for marking a database as already migrated.

        Args:
            revision: Revision to stamp
        """
        schema_prefix = f"{self._config.version_table_schema}." if self._config.version_table_schema else ""
        table_name = f"{schema_prefix}{self._config.version_table}"

        async with self._engine.begin() as conn:
            # Clear existing version
            await conn.execute(text(f"DELETE FROM {table_name}"))
            # Insert new version
            await conn.execute(
                text(f"INSERT INTO {table_name} (version_num) VALUES (:rev)"),
                {"rev": revision}
            )

        logger.info("Database stamped", revision=revision)

    async def get_status(self) -> Dict[str, Any]:
        """
        Get comprehensive migration status.

        Returns:
            Status dictionary with current, head, pending info
        """
        current = await self.current_revision()
        head = await self.head_revision()
        pending = await self.pending_migrations()

        return {
            "current_revision": current,
            "head_revision": head,
            "is_up_to_date": current == head,
            "pending_count": len(pending),
            "pending_migrations": [m.to_dict() for m in pending],
        }


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    # Configuration
    "MigrationConfig",
    "MigrationInfo",

    # Manager
    "MigrationManager",
]
