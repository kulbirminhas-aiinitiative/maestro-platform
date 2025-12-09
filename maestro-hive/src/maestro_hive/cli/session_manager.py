"""
Session Manager
===============

Manages session persistence and resume capability.

Implements: AC-3 (Resume capability for long-running executions)
"""

import json
import os
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional, Any


class SessionStatus(Enum):
    """Status of a session."""
    CREATED = "created"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    RESUMED = "resumed"


@dataclass
class Session:
    """
    Session data structure.

    Stores all information needed to resume a long-running execution.
    """
    session_id: str
    status: SessionStatus = SessionStatus.CREATED
    current_step: int = 0
    total_steps: int = 10
    started_at: datetime = field(default_factory=datetime.now)
    last_updated: datetime = field(default_factory=datetime.now)
    input_data: str = ""
    command_type_str: str = ""
    checkpoint_data: Optional[dict] = None
    error: Optional[str] = None

    def to_dict(self) -> dict:
        """Convert session to dictionary for serialization."""
        return {
            "session_id": self.session_id,
            "status": self.status.value,
            "current_step": self.current_step,
            "total_steps": self.total_steps,
            "started_at": self.started_at.isoformat(),
            "last_updated": self.last_updated.isoformat(),
            "input_data": self.input_data,
            "command_type_str": self.command_type_str,
            "checkpoint_data": self.checkpoint_data,
            "error": self.error,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Session":
        """Create session from dictionary."""
        return cls(
            session_id=data["session_id"],
            status=SessionStatus(data["status"]),
            current_step=data["current_step"],
            total_steps=data["total_steps"],
            started_at=datetime.fromisoformat(data["started_at"]),
            last_updated=datetime.fromisoformat(data["last_updated"]),
            input_data=data.get("input_data", ""),
            command_type_str=data.get("command_type_str", ""),
            checkpoint_data=data.get("checkpoint_data"),
            error=data.get("error"),
        )


class SessionManager:
    """
    Manages session lifecycle and persistence.

    Provides:
    - Session creation with unique IDs
    - Checkpoint saving for resume capability
    - Session loading for continuation
    - Session listing and cleanup

    Implements AC-3: Resume capability for long-running executions
    """

    def __init__(self, session_dir: Optional[str] = None):
        """
        Initialize the session manager.

        Args:
            session_dir: Directory for session storage
                        (defaults to ~/.maestro/sessions)
        """
        if session_dir:
            self.session_dir = Path(session_dir)
        else:
            self.session_dir = Path.home() / ".maestro" / "sessions"

        # Ensure directory exists
        self.session_dir.mkdir(parents=True, exist_ok=True)

    def create_session(self) -> Session:
        """
        Create a new session.

        Returns:
            New Session instance with unique ID
        """
        session_id = self._generate_session_id()
        session = Session(
            session_id=session_id,
            status=SessionStatus.CREATED,
            started_at=datetime.now(),
            last_updated=datetime.now(),
        )

        # Save initial state
        self._save_session(session)

        return session

    def save_checkpoint(self, session: Session, checkpoint_data: Optional[dict] = None) -> None:
        """
        Save session checkpoint.

        Args:
            session: The session to checkpoint
            checkpoint_data: Optional additional checkpoint data
        """
        session.last_updated = datetime.now()
        if checkpoint_data:
            session.checkpoint_data = checkpoint_data

        self._save_session(session)

    def load_session(self, session_id: str) -> Session:
        """
        Load a session by ID.

        Args:
            session_id: The session ID to load

        Returns:
            The loaded Session

        Raises:
            FileNotFoundError: If session doesn't exist
        """
        session_file = self.session_dir / f"{session_id}.json"

        if not session_file.exists():
            raise FileNotFoundError(f"Session {session_id} not found")

        with open(session_file, 'r') as f:
            data = json.load(f)

        return Session.from_dict(data)

    def list_sessions(
        self,
        status: Optional[SessionStatus] = None,
        limit: int = 100
    ) -> list[Session]:
        """
        List all sessions, optionally filtered by status.

        Args:
            status: Optional status filter
            limit: Maximum number of sessions to return

        Returns:
            List of Session objects
        """
        sessions = []

        for session_file in sorted(
            self.session_dir.glob("*.json"),
            key=lambda f: f.stat().st_mtime,
            reverse=True
        )[:limit]:
            try:
                with open(session_file, 'r') as f:
                    data = json.load(f)
                session = Session.from_dict(data)

                if status is None or session.status == status:
                    sessions.append(session)

            except (json.JSONDecodeError, KeyError):
                # Skip invalid session files
                continue

        return sessions

    def delete_session(self, session_id: str) -> bool:
        """
        Delete a session.

        Args:
            session_id: The session ID to delete

        Returns:
            True if deleted, False if not found
        """
        session_file = self.session_dir / f"{session_id}.json"

        if session_file.exists():
            session_file.unlink()
            return True

        return False

    def update_status(self, session: Session, status: SessionStatus) -> None:
        """
        Update session status.

        Args:
            session: The session to update
            status: New status
        """
        session.status = status
        session.last_updated = datetime.now()
        self._save_session(session)

    def mark_completed(self, session: Session) -> None:
        """Mark session as completed."""
        self.update_status(session, SessionStatus.COMPLETED)

    def mark_failed(self, session: Session, error: str) -> None:
        """
        Mark session as failed.

        Args:
            session: The session to mark
            error: Error message
        """
        session.status = SessionStatus.FAILED
        session.error = error
        session.last_updated = datetime.now()
        self._save_session(session)

    def get_resumable_sessions(self) -> list[Session]:
        """
        Get sessions that can be resumed.

        Returns:
            List of sessions with status PAUSED or RUNNING
        """
        resumable = []
        for session in self.list_sessions():
            if session.status in (SessionStatus.PAUSED, SessionStatus.RUNNING):
                resumable.append(session)
        return resumable

    def cleanup_old_sessions(self, days: int = 30) -> int:
        """
        Delete sessions older than specified days.

        Args:
            days: Age threshold in days

        Returns:
            Number of sessions deleted
        """
        cutoff = datetime.now().timestamp() - (days * 24 * 60 * 60)
        deleted = 0

        for session_file in self.session_dir.glob("*.json"):
            if session_file.stat().st_mtime < cutoff:
                session_file.unlink()
                deleted += 1

        return deleted

    def _generate_session_id(self) -> str:
        """Generate a unique session ID."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        unique = uuid.uuid4().hex[:8]
        return f"session_{timestamp}_{unique}"

    def _save_session(self, session: Session) -> None:
        """Save session to file."""
        session_file = self.session_dir / f"{session.session_id}.json"

        with open(session_file, 'w') as f:
            json.dump(session.to_dict(), f, indent=2)

    def get_session_file_path(self, session_id: str) -> Path:
        """Get the file path for a session."""
        return self.session_dir / f"{session_id}.json"

    def session_exists(self, session_id: str) -> bool:
        """Check if a session exists."""
        return self.get_session_file_path(session_id).exists()
