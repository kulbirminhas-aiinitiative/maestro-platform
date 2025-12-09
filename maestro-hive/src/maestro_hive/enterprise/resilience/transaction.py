"""
Transaction Semantics for Distributed Operations.

Provides transaction context and coordination.
"""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Callable, Any, Dict, List, Awaitable
from enum import Enum
import uuid
import contextvars


# Context variable for current transaction
_current_transaction: contextvars.ContextVar[Optional["TransactionContext"]] = contextvars.ContextVar(
    "current_transaction", default=None
)


class TransactionStatus(Enum):
    """Transaction status."""
    PENDING = "pending"
    ACTIVE = "active"
    COMMITTED = "committed"
    COMPENSATING = "compensating"
    COMPENSATED = "compensated"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


class TransactionIsolation(Enum):
    """Transaction isolation levels."""
    READ_UNCOMMITTED = "read_uncommitted"
    READ_COMMITTED = "read_committed"
    REPEATABLE_READ = "repeatable_read"
    SERIALIZABLE = "serializable"


@dataclass
class TransactionStep:
    """Step within a transaction."""
    id: str
    name: str
    status: TransactionStatus = TransactionStatus.PENDING
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error: Optional[str] = None
    result: Any = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TransactionLog:
    """Transaction log entry."""
    transaction_id: str
    step_name: str
    action: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    data: Dict[str, Any] = field(default_factory=dict)


class TransactionContext:
    """
    Transaction context for coordinating operations.

    Provides a context for executing multiple operations
    as a logical transaction with rollback capability.
    """

    def __init__(
        self,
        name: str,
        isolation: TransactionIsolation = TransactionIsolation.READ_COMMITTED,
        timeout_seconds: int = 300,
    ):
        """
        Initialize transaction context.

        Args:
            name: Transaction name
            isolation: Isolation level
            timeout_seconds: Transaction timeout
        """
        self.id = str(uuid.uuid4())
        self.name = name
        self.isolation = isolation
        self.timeout_seconds = timeout_seconds
        self.status = TransactionStatus.PENDING
        self._steps: List[TransactionStep] = []
        self._log: List[TransactionLog] = []
        self._compensation_stack: List[Callable] = []
        self._data: Dict[str, Any] = {}
        self._started_at: Optional[datetime] = None
        self._completed_at: Optional[datetime] = None
        self._token: Optional[contextvars.Token] = None
        self._lock = asyncio.Lock()

    @property
    def is_active(self) -> bool:
        """Check if transaction is active."""
        return self.status == TransactionStatus.ACTIVE

    @property
    def duration_ms(self) -> int:
        """Get transaction duration in milliseconds."""
        if not self._started_at:
            return 0
        end = self._completed_at or datetime.utcnow()
        return int((end - self._started_at).total_seconds() * 1000)

    def set(self, key: str, value: Any) -> None:
        """Set transaction data."""
        self._data[key] = value

    def get(self, key: str, default: Any = None) -> Any:
        """Get transaction data."""
        return self._data.get(key, default)

    def _log_action(self, step_name: str, action: str, data: Dict = None) -> None:
        """Log transaction action."""
        entry = TransactionLog(
            transaction_id=self.id,
            step_name=step_name,
            action=action,
            data=data or {},
        )
        self._log.append(entry)

    async def begin(self) -> "TransactionContext":
        """
        Begin transaction.

        Returns:
            Self for context manager usage
        """
        async with self._lock:
            if self.status != TransactionStatus.PENDING:
                raise RuntimeError("Transaction already started")

            self.status = TransactionStatus.ACTIVE
            self._started_at = datetime.utcnow()
            self._token = _current_transaction.set(self)
            self._log_action("__transaction__", "begin")

        return self

    async def step(
        self,
        name: str,
        action: Callable[[], Awaitable[Any]],
        compensation: Optional[Callable[[], Awaitable[Any]]] = None,
    ) -> Any:
        """
        Execute transaction step.

        Args:
            name: Step name
            action: Step action
            compensation: Compensation action for rollback

        Returns:
            Step result
        """
        if not self.is_active:
            raise RuntimeError("Transaction is not active")

        step = TransactionStep(
            id=str(uuid.uuid4()),
            name=name,
        )
        self._steps.append(step)

        step.status = TransactionStatus.ACTIVE
        step.started_at = datetime.utcnow()
        self._log_action(name, "start")

        try:
            result = await action()
            step.result = result
            step.status = TransactionStatus.COMMITTED
            step.completed_at = datetime.utcnow()
            self._log_action(name, "complete", {"result_type": type(result).__name__})

            # Register compensation if provided
            if compensation:
                self._compensation_stack.append(compensation)

            return result

        except Exception as e:
            step.status = TransactionStatus.FAILED
            step.error = str(e)
            step.completed_at = datetime.utcnow()
            self._log_action(name, "fail", {"error": str(e)})
            raise

    async def commit(self) -> None:
        """Commit transaction."""
        async with self._lock:
            if self.status != TransactionStatus.ACTIVE:
                raise RuntimeError("Cannot commit - transaction not active")

            self.status = TransactionStatus.COMMITTED
            self._completed_at = datetime.utcnow()
            self._compensation_stack.clear()
            self._log_action("__transaction__", "commit")

    async def rollback(self) -> Dict[str, Any]:
        """
        Rollback transaction by executing compensations.

        Returns:
            Rollback result
        """
        async with self._lock:
            if self.status == TransactionStatus.COMMITTED:
                raise RuntimeError("Cannot rollback committed transaction")

            self.status = TransactionStatus.COMPENSATING
            self._log_action("__transaction__", "rollback_start")

        errors = []
        executed = 0

        # Execute compensations in reverse order
        while self._compensation_stack:
            compensation = self._compensation_stack.pop()
            try:
                await compensation()
                executed += 1
            except Exception as e:
                errors.append(str(e))

        async with self._lock:
            self.status = (
                TransactionStatus.COMPENSATED if not errors
                else TransactionStatus.ROLLED_BACK
            )
            self._completed_at = datetime.utcnow()
            self._log_action("__transaction__", "rollback_complete", {
                "executed": executed,
                "errors": len(errors),
            })

        return {
            "success": len(errors) == 0,
            "compensations_executed": executed,
            "errors": errors,
        }

    async def __aenter__(self) -> "TransactionContext":
        """Async context manager entry."""
        return await self.begin()

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        if self._token:
            _current_transaction.reset(self._token)

        if exc_type is not None:
            # Exception occurred - rollback
            await self.rollback()
        elif self.status == TransactionStatus.ACTIVE:
            # No exception, auto-commit
            await self.commit()

    def get_steps(self) -> List[TransactionStep]:
        """Get transaction steps."""
        return list(self._steps)

    def get_log(self) -> List[TransactionLog]:
        """Get transaction log."""
        return list(self._log)

    def get_status(self) -> Dict[str, Any]:
        """Get transaction status."""
        return {
            "id": self.id,
            "name": self.name,
            "status": self.status.value,
            "isolation": self.isolation.value,
            "started_at": self._started_at.isoformat() if self._started_at else None,
            "completed_at": self._completed_at.isoformat() if self._completed_at else None,
            "duration_ms": self.duration_ms,
            "steps": [
                {
                    "name": s.name,
                    "status": s.status.value,
                    "error": s.error,
                }
                for s in self._steps
            ],
        }


def get_current_transaction() -> Optional[TransactionContext]:
    """Get current transaction context."""
    return _current_transaction.get()


class DistributedTransaction:
    """
    Coordinator for distributed transactions.

    Manages transactions across multiple services/resources.
    """

    def __init__(self, name: str):
        """Initialize distributed transaction."""
        self.id = str(uuid.uuid4())
        self.name = name
        self._participants: List[TransactionContext] = []
        self._status = TransactionStatus.PENDING

    def add_participant(self, transaction: TransactionContext) -> None:
        """Add participant transaction."""
        self._participants.append(transaction)

    async def prepare(self) -> bool:
        """
        Prepare phase (2PC).

        Returns:
            True if all participants are ready
        """
        self._status = TransactionStatus.ACTIVE
        ready = True

        for participant in self._participants:
            if participant.status != TransactionStatus.ACTIVE:
                ready = False
                break

        return ready

    async def commit_all(self) -> Dict[str, Any]:
        """
        Commit all participants.

        Returns:
            Commit result
        """
        results = []
        for participant in self._participants:
            try:
                await participant.commit()
                results.append({"id": participant.id, "status": "committed"})
            except Exception as e:
                results.append({"id": participant.id, "status": "failed", "error": str(e)})

        self._status = TransactionStatus.COMMITTED
        return {"participants": results}

    async def rollback_all(self) -> Dict[str, Any]:
        """
        Rollback all participants.

        Returns:
            Rollback result
        """
        results = []
        for participant in self._participants:
            try:
                result = await participant.rollback()
                results.append({"id": participant.id, "status": "rolled_back", "result": result})
            except Exception as e:
                results.append({"id": participant.id, "status": "failed", "error": str(e)})

        self._status = TransactionStatus.ROLLED_BACK
        return {"participants": results}
