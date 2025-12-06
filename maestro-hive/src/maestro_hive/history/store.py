"""
Execution History Store - Main Store Implementation

EPIC: MD-2500
AC-1: pgvector for embeddings storage
AC-2: Efficient similarity queries

This module provides the main ExecutionHistoryStore class that handles
storage and retrieval of execution records with vector similarity search.
"""

import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

from .models import ExecutionRecord, ExecutionStatus, QualityScores

logger = logging.getLogger(__name__)


class ExecutionHistoryStore:
    """
    Main store for execution history with vector similarity search.

    Supports:
    - PostgreSQL with pgvector extension
    - SQLite fallback for development
    - In-memory storage for testing

    Usage:
        store = ExecutionHistoryStore(database_url="postgresql://...")
        await store.initialize()

        # Store execution
        record = ExecutionRecord(epic_key="MD-2500", input_text="...")
        await store.store_execution(record)

        # Find similar
        similar = await store.find_similar(embedding, limit=5)
    """

    def __init__(
        self,
        database_url: Optional[str] = None,
        embedding_dimension: int = 1536,
        use_memory: bool = False,
    ):
        """
        Initialize the store.

        Args:
            database_url: PostgreSQL connection string. If None, uses SQLite.
            embedding_dimension: Dimension of embedding vectors (default: 1536 for OpenAI)
            use_memory: If True, use in-memory storage (for testing)
        """
        self.database_url = database_url
        self.embedding_dimension = embedding_dimension
        self.use_memory = use_memory

        # In-memory storage
        self._records: Dict[UUID, ExecutionRecord] = {}
        self._db_pool = None
        self._initialized = False

        logger.info(f"ExecutionHistoryStore created (memory={use_memory}, dim={embedding_dimension})")

    async def initialize(self) -> None:
        """Initialize the store (create tables, indexes)."""
        if self._initialized:
            return

        if self.use_memory:
            logger.info("Using in-memory storage")
            self._initialized = True
            return

        if self.database_url and self.database_url.startswith("postgresql"):
            await self._init_postgres()
        else:
            await self._init_sqlite()

        self._initialized = True

    async def _init_postgres(self) -> None:
        """Initialize PostgreSQL with pgvector."""
        try:
            import asyncpg

            self._db_pool = await asyncpg.create_pool(self.database_url)

            async with self._db_pool.acquire() as conn:
                # Enable pgvector extension
                await conn.execute("CREATE EXTENSION IF NOT EXISTS vector")

                # Create execution history table
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS execution_history (
                        id UUID PRIMARY KEY,
                        epic_key VARCHAR(50) NOT NULL,
                        created_at TIMESTAMP NOT NULL DEFAULT NOW(),
                        updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
                        completed_at TIMESTAMP,
                        status VARCHAR(20) NOT NULL DEFAULT 'pending',
                        input_text TEXT,
                        input_embedding vector(%s),
                        input_metadata JSONB,
                        output_artifacts JSONB,
                        output_summary TEXT,
                        quality_scores JSONB,
                        failure_reason TEXT,
                        error_details JSONB,
                        executor_version VARCHAR(50),
                        parent_execution_id UUID,
                        retry_count INTEGER DEFAULT 0
                    )
                """ % self.embedding_dimension)

                # Create indexes for efficient queries (AC-2)
                await conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_execution_history_epic_key
                    ON execution_history (epic_key)
                """)
                await conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_execution_history_status
                    ON execution_history (status)
                """)
                await conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_execution_history_created_at
                    ON execution_history (created_at)
                """)

                # Create vector index for similarity search (AC-2)
                # Using IVFFlat for good balance of speed and accuracy
                await conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_execution_history_embedding
                    ON execution_history
                    USING ivfflat (input_embedding vector_cosine_ops)
                    WITH (lists = 100)
                """)

            logger.info("PostgreSQL initialized with pgvector")

        except ImportError:
            logger.warning("asyncpg not installed, falling back to in-memory")
            self.use_memory = True
        except Exception as e:
            logger.error(f"PostgreSQL init failed: {e}, falling back to in-memory")
            self.use_memory = True

    async def _init_sqlite(self) -> None:
        """Initialize SQLite fallback (no vector support)."""
        logger.info("Using SQLite fallback (no vector similarity)")
        # For development without PostgreSQL
        self.use_memory = True

    async def store_execution(self, record: ExecutionRecord) -> ExecutionRecord:
        """
        Store an execution record.

        Args:
            record: The ExecutionRecord to store

        Returns:
            The stored record with any updates
        """
        if not self._initialized:
            await self.initialize()

        record.updated_at = datetime.utcnow()

        if self.use_memory:
            self._records[record.id] = record
            logger.info(f"Stored execution {record.id} in memory")
            return record

        # PostgreSQL storage
        async with self._db_pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO execution_history (
                    id, epic_key, created_at, updated_at, completed_at,
                    status, input_text, input_embedding, input_metadata,
                    output_artifacts, output_summary, quality_scores,
                    failure_reason, error_details, executor_version,
                    parent_execution_id, retry_count
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17)
                ON CONFLICT (id) DO UPDATE SET
                    updated_at = $4,
                    completed_at = $5,
                    status = $6,
                    output_artifacts = $10,
                    output_summary = $11,
                    quality_scores = $12,
                    failure_reason = $13,
                    error_details = $14,
                    retry_count = $17
            """,
                record.id,
                record.epic_key,
                record.created_at,
                record.updated_at,
                record.completed_at,
                record.status.value,
                record.input_text,
                record.input_embedding,
                json.dumps(record.input_metadata),
                json.dumps([a.__dict__ for a in record.output_artifacts]),
                record.output_summary,
                json.dumps(record.quality_scores.to_dict()) if record.quality_scores else None,
                record.failure_reason,
                json.dumps(record.error_details) if record.error_details else None,
                record.executor_version,
                record.parent_execution_id,
                record.retry_count,
            )

        logger.info(f"Stored execution {record.id} in PostgreSQL")
        return record

    async def get_execution(self, execution_id: UUID) -> Optional[ExecutionRecord]:
        """Get an execution by ID."""
        if not self._initialized:
            await self.initialize()

        if self.use_memory:
            return self._records.get(execution_id)

        async with self._db_pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM execution_history WHERE id = $1",
                execution_id
            )
            if row:
                return self._row_to_record(row)
            return None

    async def get_by_epic(
        self,
        epic_key: str,
        status: Optional[ExecutionStatus] = None,
        limit: int = 100,
    ) -> List[ExecutionRecord]:
        """
        Get all executions for an EPIC.

        Args:
            epic_key: The EPIC key to search for
            status: Optional status filter
            limit: Maximum number of results

        Returns:
            List of matching ExecutionRecords
        """
        if not self._initialized:
            await self.initialize()

        if self.use_memory:
            records = [
                r for r in self._records.values()
                if r.epic_key == epic_key
                and (status is None or r.status == status)
            ]
            return sorted(records, key=lambda r: r.created_at, reverse=True)[:limit]

        async with self._db_pool.acquire() as conn:
            if status:
                rows = await conn.fetch("""
                    SELECT * FROM execution_history
                    WHERE epic_key = $1 AND status = $2
                    ORDER BY created_at DESC
                    LIMIT $3
                """, epic_key, status.value, limit)
            else:
                rows = await conn.fetch("""
                    SELECT * FROM execution_history
                    WHERE epic_key = $1
                    ORDER BY created_at DESC
                    LIMIT $2
                """, epic_key, limit)

            return [self._row_to_record(row) for row in rows]

    async def find_similar(
        self,
        embedding: List[float],
        limit: int = 5,
        min_score: float = 0.7,
        status_filter: Optional[List[ExecutionStatus]] = None,
    ) -> List[Tuple[ExecutionRecord, float]]:
        """
        Find similar executions by embedding (AC-2).

        Uses cosine similarity for vector comparison.

        Args:
            embedding: The query embedding vector
            limit: Maximum number of results
            min_score: Minimum similarity score (0-1)
            status_filter: Optional list of statuses to include

        Returns:
            List of (ExecutionRecord, similarity_score) tuples
        """
        if not self._initialized:
            await self.initialize()

        if self.use_memory:
            # Simple cosine similarity for in-memory
            results = []
            for record in self._records.values():
                if record.input_embedding:
                    if status_filter and record.status not in status_filter:
                        continue
                    score = self._cosine_similarity(embedding, record.input_embedding)
                    if score >= min_score:
                        results.append((record, score))
            results.sort(key=lambda x: x[1], reverse=True)
            return results[:limit]

        # PostgreSQL with pgvector
        async with self._db_pool.acquire() as conn:
            # Build status filter clause
            status_clause = ""
            if status_filter:
                statuses = ",".join(f"'{s.value}'" for s in status_filter)
                status_clause = f"AND status IN ({statuses})"

            # Use cosine distance (1 - similarity), then convert back
            rows = await conn.fetch(f"""
                SELECT *,
                       1 - (input_embedding <=> $1::vector) as similarity
                FROM execution_history
                WHERE input_embedding IS NOT NULL
                  AND 1 - (input_embedding <=> $1::vector) >= $2
                  {status_clause}
                ORDER BY input_embedding <=> $1::vector
                LIMIT $3
            """, embedding, min_score, limit)

            return [(self._row_to_record(row), row["similarity"]) for row in rows]

    def _cosine_similarity(self, a: List[float], b: List[float]) -> float:
        """Calculate cosine similarity between two vectors."""
        if len(a) != len(b):
            return 0.0

        dot_product = sum(x * y for x, y in zip(a, b))
        norm_a = sum(x * x for x in a) ** 0.5
        norm_b = sum(x * x for x in b) ** 0.5

        if norm_a == 0 or norm_b == 0:
            return 0.0

        return dot_product / (norm_a * norm_b)

    def _row_to_record(self, row: Any) -> ExecutionRecord:
        """Convert a database row to ExecutionRecord."""
        data = dict(row)
        data["id"] = str(data["id"])
        data["created_at"] = data["created_at"].isoformat() if data.get("created_at") else None
        data["updated_at"] = data["updated_at"].isoformat() if data.get("updated_at") else None
        data["completed_at"] = data["completed_at"].isoformat() if data.get("completed_at") else None
        data["parent_execution_id"] = str(data["parent_execution_id"]) if data.get("parent_execution_id") else None

        # Parse JSON fields
        if data.get("input_metadata") and isinstance(data["input_metadata"], str):
            data["input_metadata"] = json.loads(data["input_metadata"])
        if data.get("output_artifacts") and isinstance(data["output_artifacts"], str):
            data["output_artifacts"] = json.loads(data["output_artifacts"])
        if data.get("quality_scores") and isinstance(data["quality_scores"], str):
            data["quality_scores"] = json.loads(data["quality_scores"])
        if data.get("error_details") and isinstance(data["error_details"], str):
            data["error_details"] = json.loads(data["error_details"])

        return ExecutionRecord.from_dict(data)

    async def delete_execution(self, execution_id: UUID) -> bool:
        """Delete an execution record."""
        if not self._initialized:
            await self.initialize()

        if self.use_memory:
            if execution_id in self._records:
                del self._records[execution_id]
                return True
            return False

        async with self._db_pool.acquire() as conn:
            result = await conn.execute(
                "DELETE FROM execution_history WHERE id = $1",
                execution_id
            )
            return result == "DELETE 1"

    async def count(
        self,
        status: Optional[ExecutionStatus] = None,
        since: Optional[datetime] = None,
    ) -> int:
        """Count execution records."""
        if not self._initialized:
            await self.initialize()

        if self.use_memory:
            count = 0
            for record in self._records.values():
                if status and record.status != status:
                    continue
                if since and record.created_at < since:
                    continue
                count += 1
            return count

        async with self._db_pool.acquire() as conn:
            where_clauses = []
            params = []

            if status:
                where_clauses.append(f"status = ${len(params) + 1}")
                params.append(status.value)

            if since:
                where_clauses.append(f"created_at >= ${len(params) + 1}")
                params.append(since)

            where_clause = "WHERE " + " AND ".join(where_clauses) if where_clauses else ""

            result = await conn.fetchval(
                f"SELECT COUNT(*) FROM execution_history {where_clause}",
                *params
            )
            return result or 0

    async def close(self) -> None:
        """Close database connections."""
        if self._db_pool:
            await self._db_pool.close()
        self._initialized = False
        logger.info("ExecutionHistoryStore closed")
