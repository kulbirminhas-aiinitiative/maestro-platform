"""
ACC PostgreSQL Suppression Store (MD-2087)

Provides persistent storage for suppressions with audit trail.

Database Schema:
CREATE TABLE acc_suppressions (
    id VARCHAR(64) PRIMARY KEY,
    pattern TEXT NOT NULL,
    level VARCHAR(32) NOT NULL,
    pattern_type VARCHAR(32) DEFAULT 'glob',
    rule_type VARCHAR(32),
    threshold INTEGER,
    expires_at TIMESTAMP,
    author VARCHAR(128) NOT NULL,
    justification TEXT NOT NULL,
    adr_reference VARCHAR(32) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_used_at TIMESTAMP,
    use_count INTEGER DEFAULT 0,
    is_permanent BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN DEFAULT TRUE,
    metadata JSONB DEFAULT '{}'
);
"""

import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import asdict

logger = logging.getLogger(__name__)

# Try to import asyncpg for async PostgreSQL
try:
    import asyncpg
    HAS_ASYNCPG = True
except ImportError:
    HAS_ASYNCPG = False
    logger.warning("asyncpg not available, using sync psycopg2")

# Try to import psycopg2 for sync PostgreSQL
try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
    HAS_PSYCOPG2 = True
except ImportError:
    HAS_PSYCOPG2 = False


class PostgresSuppressionStore:
    """
    PostgreSQL storage for ACC suppressions.

    Provides persistent storage with audit trail and history.
    """

    TABLE_NAME = "acc_suppressions"
    AUDIT_TABLE = "acc_suppression_audit"

    # SQL for creating tables
    CREATE_TABLE_SQL = """
    CREATE TABLE IF NOT EXISTS acc_suppressions (
        id VARCHAR(64) PRIMARY KEY,
        pattern TEXT NOT NULL,
        level VARCHAR(32) NOT NULL,
        pattern_type VARCHAR(32) DEFAULT 'glob',
        rule_type VARCHAR(32),
        threshold INTEGER,
        expires_at TIMESTAMP,
        author VARCHAR(128) NOT NULL,
        justification TEXT NOT NULL,
        adr_reference VARCHAR(64) NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        last_used_at TIMESTAMP,
        use_count INTEGER DEFAULT 0,
        is_permanent BOOLEAN DEFAULT FALSE,
        is_active BOOLEAN DEFAULT TRUE,
        metadata JSONB DEFAULT '{}'
    );

    CREATE INDEX IF NOT EXISTS idx_suppressions_active
        ON acc_suppressions(is_active, expires_at);
    CREATE INDEX IF NOT EXISTS idx_suppressions_adr
        ON acc_suppressions(adr_reference);
    CREATE INDEX IF NOT EXISTS idx_suppressions_pattern
        ON acc_suppressions(pattern);
    """

    CREATE_AUDIT_SQL = """
    CREATE TABLE IF NOT EXISTS acc_suppression_audit (
        id SERIAL PRIMARY KEY,
        suppression_id VARCHAR(64) NOT NULL,
        action VARCHAR(32) NOT NULL,
        old_data JSONB,
        new_data JSONB,
        changed_by VARCHAR(128),
        changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE INDEX IF NOT EXISTS idx_audit_suppression
        ON acc_suppression_audit(suppression_id);
    """

    def __init__(
        self,
        connection_string: Optional[str] = None,
        host: str = "localhost",
        port: int = 5432,
        database: str = "maestro",
        user: str = "postgres",
        password: str = "postgres",
        auto_create_tables: bool = True
    ):
        """
        Initialize PostgreSQL store.

        Args:
            connection_string: Full connection string (overrides other params)
            host: Database host
            port: Database port
            database: Database name
            user: Database user
            password: Database password
            auto_create_tables: Create tables if they don't exist
        """
        if connection_string:
            self.connection_string = connection_string
        else:
            self.connection_string = (
                f"postgresql://{user}:{password}@{host}:{port}/{database}"
            )

        self._conn = None
        self.auto_create_tables = auto_create_tables

    def connect(self):
        """Establish database connection."""
        if not HAS_PSYCOPG2:
            raise RuntimeError("psycopg2 not installed. Install with: pip install psycopg2-binary")

        try:
            self._conn = psycopg2.connect(self.connection_string)
            self._conn.autocommit = False

            if self.auto_create_tables:
                self._create_tables()

            logger.info("Connected to PostgreSQL database")

        except Exception as e:
            logger.error(f"Failed to connect to PostgreSQL: {e}")
            raise

    def _create_tables(self):
        """Create tables if they don't exist."""
        with self._conn.cursor() as cur:
            cur.execute(self.CREATE_TABLE_SQL)
            cur.execute(self.CREATE_AUDIT_SQL)
            self._conn.commit()

    def disconnect(self):
        """Close database connection."""
        if self._conn:
            self._conn.close()
            self._conn = None

    def save_suppression(self, suppression: Dict[str, Any], changed_by: str = "system"):
        """
        Save suppression to database.

        Args:
            suppression: Suppression dictionary
            changed_by: User making the change
        """
        if not self._conn:
            self.connect()

        sql = """
        INSERT INTO acc_suppressions (
            id, pattern, level, pattern_type, rule_type, threshold,
            expires_at, author, justification, adr_reference,
            created_at, last_used_at, use_count, is_permanent,
            is_active, metadata
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
        )
        ON CONFLICT (id) DO UPDATE SET
            pattern = EXCLUDED.pattern,
            level = EXCLUDED.level,
            pattern_type = EXCLUDED.pattern_type,
            rule_type = EXCLUDED.rule_type,
            threshold = EXCLUDED.threshold,
            expires_at = EXCLUDED.expires_at,
            justification = EXCLUDED.justification,
            adr_reference = EXCLUDED.adr_reference,
            last_used_at = EXCLUDED.last_used_at,
            use_count = EXCLUDED.use_count,
            is_permanent = EXCLUDED.is_permanent,
            is_active = EXCLUDED.is_active,
            metadata = EXCLUDED.metadata
        """

        try:
            with self._conn.cursor() as cur:
                cur.execute(sql, (
                    suppression['id'],
                    suppression['pattern'],
                    suppression['level'],
                    suppression.get('pattern_type', 'glob'),
                    suppression.get('rule_type'),
                    suppression.get('threshold'),
                    suppression.get('expires'),
                    suppression['author'],
                    suppression['justification'],
                    suppression.get('adr_reference', ''),
                    suppression.get('created_at', datetime.now().isoformat()),
                    suppression.get('last_used'),
                    suppression.get('use_count', 0),
                    suppression.get('permanent', False),
                    True,  # is_active
                    json.dumps(suppression.get('metadata', {}))
                ))

                # Record audit
                self._record_audit(
                    cur,
                    suppression['id'],
                    'UPSERT',
                    None,
                    suppression,
                    changed_by
                )

                self._conn.commit()
                logger.debug(f"Saved suppression {suppression['id']}")

        except Exception as e:
            self._conn.rollback()
            logger.error(f"Failed to save suppression: {e}")
            raise

    def _record_audit(
        self,
        cursor,
        suppression_id: str,
        action: str,
        old_data: Optional[Dict],
        new_data: Optional[Dict],
        changed_by: str
    ):
        """Record audit trail entry."""
        sql = """
        INSERT INTO acc_suppression_audit
            (suppression_id, action, old_data, new_data, changed_by)
        VALUES (%s, %s, %s, %s, %s)
        """
        cursor.execute(sql, (
            suppression_id,
            action,
            json.dumps(old_data) if old_data else None,
            json.dumps(new_data) if new_data else None,
            changed_by
        ))

    def get_suppression(self, suppression_id: str) -> Optional[Dict[str, Any]]:
        """Get suppression by ID."""
        if not self._conn:
            self.connect()

        sql = "SELECT * FROM acc_suppressions WHERE id = %s AND is_active = TRUE"

        with self._conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(sql, (suppression_id,))
            row = cur.fetchone()
            return dict(row) if row else None

    def get_active_suppressions(self) -> List[Dict[str, Any]]:
        """Get all active (non-expired) suppressions."""
        if not self._conn:
            self.connect()

        sql = """
        SELECT * FROM acc_suppressions
        WHERE is_active = TRUE
        AND (expires_at IS NULL OR expires_at > NOW())
        ORDER BY created_at DESC
        """

        with self._conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(sql)
            return [dict(row) for row in cur.fetchall()]

    def delete_suppression(self, suppression_id: str, changed_by: str = "system"):
        """Soft-delete suppression (set is_active = FALSE)."""
        if not self._conn:
            self.connect()

        # Get current data for audit
        old_data = self.get_suppression(suppression_id)

        sql = "UPDATE acc_suppressions SET is_active = FALSE WHERE id = %s"

        try:
            with self._conn.cursor() as cur:
                cur.execute(sql, (suppression_id,))

                self._record_audit(
                    cur,
                    suppression_id,
                    'DELETE',
                    old_data,
                    None,
                    changed_by
                )

                self._conn.commit()
                logger.info(f"Deleted suppression {suppression_id}")

        except Exception as e:
            self._conn.rollback()
            logger.error(f"Failed to delete suppression: {e}")
            raise

    def update_use_count(self, suppression_id: str):
        """Update use count and last_used timestamp."""
        if not self._conn:
            self.connect()

        sql = """
        UPDATE acc_suppressions
        SET use_count = use_count + 1, last_used_at = NOW()
        WHERE id = %s
        """

        try:
            with self._conn.cursor() as cur:
                cur.execute(sql, (suppression_id,))
                self._conn.commit()

        except Exception as e:
            self._conn.rollback()
            logger.error(f"Failed to update use count: {e}")

    def get_by_adr(self, adr_reference: str) -> List[Dict[str, Any]]:
        """Get suppressions linked to an ADR."""
        if not self._conn:
            self.connect()

        sql = """
        SELECT * FROM acc_suppressions
        WHERE adr_reference = %s AND is_active = TRUE
        ORDER BY created_at DESC
        """

        with self._conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(sql, (adr_reference,))
            return [dict(row) for row in cur.fetchall()]

    def get_audit_trail(
        self,
        suppression_id: str,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get audit trail for a suppression."""
        if not self._conn:
            self.connect()

        sql = """
        SELECT * FROM acc_suppression_audit
        WHERE suppression_id = %s
        ORDER BY changed_at DESC
        LIMIT %s
        """

        with self._conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(sql, (suppression_id, limit))
            return [dict(row) for row in cur.fetchall()]

    def cleanup_expired(self) -> int:
        """Deactivate expired suppressions. Returns count of deactivated."""
        if not self._conn:
            self.connect()

        sql = """
        UPDATE acc_suppressions
        SET is_active = FALSE
        WHERE is_active = TRUE
        AND expires_at IS NOT NULL
        AND expires_at < NOW()
        AND is_permanent = FALSE
        """

        try:
            with self._conn.cursor() as cur:
                cur.execute(sql)
                count = cur.rowcount
                self._conn.commit()
                logger.info(f"Cleaned up {count} expired suppressions")
                return count

        except Exception as e:
            self._conn.rollback()
            logger.error(f"Failed to cleanup expired suppressions: {e}")
            return 0

    def export_to_yaml(self, output_path: str):
        """Export active suppressions to YAML file."""
        import yaml

        suppressions = self.get_active_suppressions()

        # Convert to YAML-friendly format
        yaml_data = {
            'version': '1.0',
            'exported_at': datetime.now().isoformat(),
            'suppressions': suppressions
        }

        with open(output_path, 'w') as f:
            yaml.dump(yaml_data, f, default_flow_style=False)

        logger.info(f"Exported {len(suppressions)} suppressions to {output_path}")


# Convenience function
def get_postgres_store(
    connection_string: Optional[str] = None
) -> PostgresSuppressionStore:
    """Get or create PostgreSQL store instance."""
    import os

    conn_string = connection_string or os.environ.get(
        'DATABASE_URL',
        'postgresql://postgres:postgres@localhost:5432/maestro'
    )

    store = PostgresSuppressionStore(connection_string=conn_string)
    store.connect()
    return store
