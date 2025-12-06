"""
Execution History Store - Persistent Storage for Learning Loop

EPIC: MD-2500 - Execution History Store (Sub-EPIC of MD-2493)

Stores execution history in PostgreSQL with pgvector for:
- Semantic similarity search
- Pattern extraction
- Session resume capability
- Metrics and analytics
"""

import logging
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Any, Dict, List, Optional
import json

logger = logging.getLogger(__name__)


@dataclass
class ExecutionRecord:
    """Record of a single execution."""
    execution_id: str
    epic_key: Optional[str]
    description: str
    mode: str  # "epic", "adhoc", "resume"
    status: str  # "running", "completed", "failed"
    started_at: datetime
    completed_at: Optional[datetime]
    phase_results: Dict[str, Any]
    patterns_used: List[str]
    success: bool
    compliance_score: float
    error: Optional[str]
    embedding: Optional[List[float]] = None  # pgvector embedding


class ExecutionHistoryStore:
    """
    Persistent storage for execution history.

    Uses PostgreSQL with pgvector extension for:
    - Full execution records
    - Semantic embeddings for similarity search
    - Session state for resume capability
    """

    def __init__(
        self,
        db_url: Optional[str] = None,
    ):
        """
        Initialize the history store.

        Args:
            db_url: PostgreSQL connection URL
        """
        self.db_url = db_url
        self._conn = None

        logger.info("Execution History Store initialized")

    async def initialize(self):
        """Initialize database schema."""
        logger.info("Creating execution_history table...")

        # TODO: Implement actual database initialization
        # Schema:
        # CREATE TABLE execution_history (
        #     execution_id UUID PRIMARY KEY,
        #     epic_key VARCHAR(20),
        #     description TEXT,
        #     mode VARCHAR(20),
        #     status VARCHAR(20),
        #     started_at TIMESTAMPTZ,
        #     completed_at TIMESTAMPTZ,
        #     phase_results JSONB,
        #     patterns_used TEXT[],
        #     success BOOLEAN,
        #     compliance_score FLOAT,
        #     error TEXT,
        #     embedding vector(1536)
        # );
        #
        # CREATE INDEX ON execution_history USING ivfflat (embedding vector_cosine_ops);

        logger.info("Database initialization pending (MD-2500)")

    async def store(self, record: ExecutionRecord) -> str:
        """
        Store an execution record.

        Args:
            record: The execution record to store

        Returns:
            The execution_id
        """
        logger.info(f"Storing execution record: {record.execution_id}")

        # TODO: Implement actual storage
        # For now, log to file
        log_path = f"/tmp/maestro/history/{record.execution_id}.json"

        try:
            import os
            os.makedirs("/tmp/maestro/history", exist_ok=True)

            record_dict = asdict(record)
            record_dict["started_at"] = record.started_at.isoformat()
            if record.completed_at:
                record_dict["completed_at"] = record.completed_at.isoformat()
            # Remove embedding for JSON serialization
            record_dict.pop("embedding", None)

            with open(log_path, "w") as f:
                json.dump(record_dict, f, indent=2)

            logger.info(f"Execution record stored to: {log_path}")
        except Exception as e:
            logger.error(f"Failed to store execution record: {e}")

        return record.execution_id

    async def get(self, execution_id: str) -> Optional[ExecutionRecord]:
        """
        Retrieve an execution record.

        Args:
            execution_id: The execution ID to retrieve

        Returns:
            ExecutionRecord or None if not found
        """
        logger.info(f"Retrieving execution record: {execution_id}")

        # TODO: Implement actual retrieval
        try:
            log_path = f"/tmp/maestro/history/{execution_id}.json"
            with open(log_path, "r") as f:
                data = json.load(f)

            return ExecutionRecord(
                execution_id=data["execution_id"],
                epic_key=data.get("epic_key"),
                description=data["description"],
                mode=data["mode"],
                status=data["status"],
                started_at=datetime.fromisoformat(data["started_at"]),
                completed_at=datetime.fromisoformat(data["completed_at"]) if data.get("completed_at") else None,
                phase_results=data["phase_results"],
                patterns_used=data["patterns_used"],
                success=data["success"],
                compliance_score=data["compliance_score"],
                error=data.get("error"),
            )
        except FileNotFoundError:
            return None
        except Exception as e:
            logger.error(f"Failed to retrieve execution record: {e}")
            return None

    async def search_similar(
        self,
        embedding: List[float],
        limit: int = 5,
    ) -> List[ExecutionRecord]:
        """
        Search for similar executions using vector similarity.

        Args:
            embedding: Query embedding vector
            limit: Maximum number of results

        Returns:
            List of similar ExecutionRecords
        """
        logger.info(f"Searching for {limit} similar executions...")

        # TODO: Implement actual vector search
        # SELECT * FROM execution_history
        # ORDER BY embedding <=> $1
        # LIMIT $2;

        return []

    async def get_patterns(
        self,
        success_only: bool = False,
        limit: int = 100,
    ) -> tuple[List[str], List[str]]:
        """
        Get patterns from execution history.

        Args:
            success_only: Only include patterns from successful executions
            limit: Maximum number of executions to analyze

        Returns:
            Tuple of (patterns_that_worked, patterns_that_failed)
        """
        # TODO: Implement actual pattern extraction
        return [], []

    async def get_session_state(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Get session state for resume capability.

        Args:
            session_id: The session ID to retrieve

        Returns:
            Session state dictionary or None
        """
        record = await self.get(session_id)
        if record:
            return {
                "execution_id": record.execution_id,
                "current_phase": record.phase_results.get("current_phase"),
                "artifacts": record.phase_results,
            }
        return None

    async def update_session_state(
        self,
        session_id: str,
        state: Dict[str, Any],
    ):
        """
        Update session state for resume capability.

        Args:
            session_id: The session ID to update
            state: New state dictionary
        """
        # TODO: Implement actual state update
        logger.info(f"Updating session state: {session_id}")
