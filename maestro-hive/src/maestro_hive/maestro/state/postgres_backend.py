"""
PostgreSQL State Store - Database-backed state persistence

EPIC: MD-2528 - AC-1: Unified state store (PostgreSQL backend)

Production-grade state storage with PostgreSQL backend.
"""

import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from .store import StateEntry, StateStore

logger = logging.getLogger(__name__)


class PostgreSQLStateStore(StateStore):
    """
    PostgreSQL-backed state store.

    Uses PostgreSQL for production-grade state persistence with:
    - ACID transactions
    - Concurrent access support
    - Efficient version queries

    Table schema:
        CREATE TABLE state_entries (
            id SERIAL PRIMARY KEY,
            key VARCHAR(255) NOT NULL,
            value JSONB NOT NULL,
            version INTEGER NOT NULL,
            timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            component_id VARCHAR(255),
            metadata JSONB DEFAULT '{}',
            UNIQUE(key, version)
        );
        CREATE INDEX idx_state_key ON state_entries(key);
        CREATE INDEX idx_state_key_version ON state_entries(key, version DESC);
    """

    def __init__(
        self,
        connection_string: Optional[str] = None,
        pool_size: int = 5,
        table_name: str = "state_entries",
    ):
        """
        Initialize PostgreSQL state store.

        Args:
            connection_string: PostgreSQL connection URL
            pool_size: Connection pool size
            table_name: Name of state table
        """
        self.connection_string = connection_string
        self.pool_size = pool_size
        self.table_name = table_name
        self._pool = None

        # Try to import psycopg2
        try:
            import psycopg2
            from psycopg2 import pool
            self._psycopg2 = psycopg2
            self._pool_class = pool.ThreadedConnectionPool
            self._available = True
        except ImportError:
            self._available = False
            logger.warning(
                "psycopg2 not available - PostgreSQL backend disabled. "
                "Install with: pip install psycopg2-binary"
            )

        if self._available and connection_string:
            self._init_pool()

        logger.info(f"PostgreSQLStateStore initialized (available={self._available})")

    def _init_pool(self) -> None:
        """Initialize connection pool."""
        if not self._available or not self.connection_string:
            return

        try:
            self._pool = self._pool_class(
                minconn=1,
                maxconn=self.pool_size,
                dsn=self.connection_string,
            )
            self._ensure_schema()
            logger.info("PostgreSQL connection pool initialized")
        except Exception as e:
            logger.error(f"Failed to initialize PostgreSQL pool: {e}")
            self._pool = None

    def _ensure_schema(self) -> None:
        """Create table if not exists."""
        if not self._pool:
            return

        conn = self._pool.getconn()
        try:
            with conn.cursor() as cur:
                cur.execute(f"""
                    CREATE TABLE IF NOT EXISTS {self.table_name} (
                        id SERIAL PRIMARY KEY,
                        key VARCHAR(255) NOT NULL,
                        value JSONB NOT NULL,
                        version INTEGER NOT NULL,
                        timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                        component_id VARCHAR(255),
                        metadata JSONB DEFAULT '{{}}',
                        UNIQUE(key, version)
                    )
                """)
                cur.execute(f"""
                    CREATE INDEX IF NOT EXISTS idx_{self.table_name}_key
                    ON {self.table_name}(key)
                """)
                cur.execute(f"""
                    CREATE INDEX IF NOT EXISTS idx_{self.table_name}_key_version
                    ON {self.table_name}(key, version DESC)
                """)
            conn.commit()
        finally:
            self._pool.putconn(conn)

    def _check_available(self) -> bool:
        """Check if PostgreSQL is available."""
        if not self._available:
            logger.warning("PostgreSQL not available")
            return False
        if not self._pool:
            logger.warning("PostgreSQL pool not initialized")
            return False
        return True

    def save(
        self,
        key: str,
        value: Dict[str, Any],
        component_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> StateEntry:
        """Save state with auto-incrementing version."""
        if not self._check_available():
            raise RuntimeError("PostgreSQL backend not available")

        conn = self._pool.getconn()
        try:
            with conn.cursor() as cur:
                # Get next version
                cur.execute(
                    f"SELECT COALESCE(MAX(version), 0) + 1 FROM {self.table_name} WHERE key = %s",
                    (key,)
                )
                new_version = cur.fetchone()[0]

                timestamp = datetime.utcnow()

                # Insert new version
                cur.execute(
                    f"""
                    INSERT INTO {self.table_name}
                    (key, value, version, timestamp, component_id, metadata)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    RETURNING id
                    """,
                    (
                        key,
                        json.dumps(value),
                        new_version,
                        timestamp,
                        component_id,
                        json.dumps(metadata or {}),
                    )
                )

            conn.commit()

            entry = StateEntry(
                key=key,
                value=value,
                version=new_version,
                timestamp=timestamp,
                component_id=component_id,
                metadata=metadata or {},
            )

            logger.debug(f"Saved state {key} v{new_version}")
            return entry

        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to save state {key}: {e}")
            raise
        finally:
            self._pool.putconn(conn)

    def load(
        self,
        key: str,
        version: Optional[int] = None,
    ) -> Optional[StateEntry]:
        """Load state, optionally at specific version."""
        if not self._check_available():
            return None

        conn = self._pool.getconn()
        try:
            with conn.cursor() as cur:
                if version is not None:
                    cur.execute(
                        f"""
                        SELECT key, value, version, timestamp, component_id, metadata
                        FROM {self.table_name}
                        WHERE key = %s AND version = %s
                        """,
                        (key, version)
                    )
                else:
                    cur.execute(
                        f"""
                        SELECT key, value, version, timestamp, component_id, metadata
                        FROM {self.table_name}
                        WHERE key = %s
                        ORDER BY version DESC
                        LIMIT 1
                        """,
                        (key,)
                    )

                row = cur.fetchone()
                if not row:
                    return None

                return StateEntry(
                    key=row[0],
                    value=row[1] if isinstance(row[1], dict) else json.loads(row[1]),
                    version=row[2],
                    timestamp=row[3],
                    component_id=row[4],
                    metadata=row[5] if isinstance(row[5], dict) else json.loads(row[5] or "{}"),
                )

        finally:
            self._pool.putconn(conn)

    def delete(self, key: str) -> bool:
        """Delete all versions of state."""
        if not self._check_available():
            return False

        conn = self._pool.getconn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    f"DELETE FROM {self.table_name} WHERE key = %s",
                    (key,)
                )
                deleted = cur.rowcount > 0
            conn.commit()

            if deleted:
                logger.info(f"Deleted state {key}")
            return deleted

        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to delete state {key}: {e}")
            return False
        finally:
            self._pool.putconn(conn)

    def exists(self, key: str) -> bool:
        """Check if state exists."""
        if not self._check_available():
            return False

        conn = self._pool.getconn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    f"SELECT 1 FROM {self.table_name} WHERE key = %s LIMIT 1",
                    (key,)
                )
                return cur.fetchone() is not None
        finally:
            self._pool.putconn(conn)

    def list_keys(self, prefix: Optional[str] = None) -> List[str]:
        """List all state keys."""
        if not self._check_available():
            return []

        conn = self._pool.getconn()
        try:
            with conn.cursor() as cur:
                if prefix:
                    cur.execute(
                        f"""
                        SELECT DISTINCT key FROM {self.table_name}
                        WHERE key LIKE %s
                        ORDER BY key
                        """,
                        (f"{prefix}%",)
                    )
                else:
                    cur.execute(
                        f"SELECT DISTINCT key FROM {self.table_name} ORDER BY key"
                    )
                return [row[0] for row in cur.fetchall()]
        finally:
            self._pool.putconn(conn)

    def list_versions(self, key: str) -> List[StateEntry]:
        """Get version history for a key."""
        if not self._check_available():
            return []

        conn = self._pool.getconn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    f"""
                    SELECT key, value, version, timestamp, component_id, metadata
                    FROM {self.table_name}
                    WHERE key = %s
                    ORDER BY version ASC
                    """,
                    (key,)
                )

                entries = []
                for row in cur.fetchall():
                    entries.append(StateEntry(
                        key=row[0],
                        value=row[1] if isinstance(row[1], dict) else json.loads(row[1]),
                        version=row[2],
                        timestamp=row[3],
                        component_id=row[4],
                        metadata=row[5] if isinstance(row[5], dict) else json.loads(row[5] or "{}"),
                    ))
                return entries
        finally:
            self._pool.putconn(conn)

    def get_latest_version(self, key: str) -> int:
        """Get the latest version number."""
        if not self._check_available():
            return 0

        conn = self._pool.getconn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    f"SELECT COALESCE(MAX(version), 0) FROM {self.table_name} WHERE key = %s",
                    (key,)
                )
                return cur.fetchone()[0]
        finally:
            self._pool.putconn(conn)

    def prune_versions(
        self,
        key: str,
        keep_count: int = 10,
    ) -> int:
        """Remove old versions keeping only the most recent."""
        if not self._check_available():
            return 0

        conn = self._pool.getconn()
        try:
            with conn.cursor() as cur:
                # Get versions to delete
                cur.execute(
                    f"""
                    DELETE FROM {self.table_name}
                    WHERE key = %s AND version NOT IN (
                        SELECT version FROM {self.table_name}
                        WHERE key = %s
                        ORDER BY version DESC
                        LIMIT %s
                    )
                    """,
                    (key, key, keep_count)
                )
                pruned = cur.rowcount
            conn.commit()

            if pruned > 0:
                logger.info(f"Pruned {pruned} old versions of {key}")
            return pruned

        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to prune versions for {key}: {e}")
            return 0
        finally:
            self._pool.putconn(conn)

    def close(self) -> None:
        """Close connection pool."""
        if self._pool:
            self._pool.closeall()
            logger.info("PostgreSQL connection pool closed")

    def is_available(self) -> bool:
        """Check if PostgreSQL backend is available and connected."""
        return self._available and self._pool is not None
