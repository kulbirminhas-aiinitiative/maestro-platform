"""
Main Healing Service for Self-Healing Mechanism.

Orchestrates all healing components and provides the main API.
"""

import logging
from typing import Any, Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime
import uuid
import asyncio

from .models import (
    FailureType,
    ActionType,
    FailurePattern,
    HealingAction,
    HealingSession,
    UserFeedback,
)
from .pattern_analyzer import FailurePatternAnalyzer
from .auto_refactor import AutoRefactorEngine
from .rag_feedback import RAGFeedbackLoop, RAGContext
from .user_feedback import UserFeedbackIntegrator

logger = logging.getLogger(__name__)


@dataclass
class HealingConfig:
    """Configuration for the healing service."""
    enabled: bool = True
    min_confidence: float = 0.7
    max_concurrent_sessions: int = 5
    auto_apply: bool = False
    require_validation: bool = True
    vector_store_url: Optional[str] = None
    rag_endpoint: Optional[str] = None
    quality_fabric_url: str = "http://localhost:8000"


class HealingService:
    """
    Main service for the self-healing mechanism.

    Orchestrates:
    - Pattern analysis
    - Auto-refactoring
    - RAG feedback loop
    - User feedback integration
    - Quality Fabric validation
    """

    def __init__(self, config: Optional[HealingConfig] = None):
        """
        Initialize the healing service.

        Args:
            config: Optional configuration override
        """
        self.config = config or HealingConfig()

        # Initialize components
        self.pattern_analyzer = FailurePatternAnalyzer(
            confidence_threshold=self.config.min_confidence,
        )
        self.auto_refactor = AutoRefactorEngine(
            min_confidence=self.config.min_confidence,
        )
        self.rag_feedback = RAGFeedbackLoop(
            vector_store_url=self.config.vector_store_url,
            rag_endpoint=self.config.rag_endpoint,
        )
        self.user_feedback = UserFeedbackIntegrator()

        # Active sessions
        self._sessions: Dict[str, HealingSession] = {}
        self._session_history: List[HealingSession] = []

        logger.info("HealingService initialized")

    async def analyze_failure(
        self,
        execution_id: str,
        error_message: str,
        context: Dict[str, Any],
    ) -> HealingSession:
        """
        Analyze a failure and create a healing session.

        Args:
            execution_id: The execution that failed
            error_message: The error message
            context: Additional context (file, line, stack trace, etc.)

        Returns:
            A HealingSession with detected patterns and proposed actions
        """
        if not self.config.enabled:
            raise RuntimeError("Healing service is disabled")

        # Check concurrent session limit
        active_count = len([s for s in self._sessions.values() if s.status == "analyzing"])
        if active_count >= self.config.max_concurrent_sessions:
            raise RuntimeError(f"Maximum concurrent sessions ({self.config.max_concurrent_sessions}) reached")

        # Create session
        session = HealingSession(
            session_id=f"heal-{uuid.uuid4().hex[:8]}",
            execution_id=execution_id,
            failure_type=self._classify_failure(error_message),
            error_message=error_message,
            context=context,
        )
        self._sessions[session.session_id] = session

        logger.info(f"Created healing session {session.session_id} for execution {execution_id}")

        try:
            # Step 1: Analyze patterns
            patterns = self.pattern_analyzer.analyze_failure(
                error_message=error_message,
                context=context,
                execution_id=execution_id,
            )

            for pattern in patterns:
                session.add_pattern(pattern)
                logger.debug(f"Detected pattern: {pattern.pattern_id} (confidence: {pattern.confidence_score:.2f})")

            # Step 2: Generate fixes for each pattern
            source_code = context.get("source_code", "")
            target_file = context.get("file", "unknown.py")

            for pattern in patterns:
                result = self.auto_refactor.generate_fix(
                    pattern=pattern,
                    source_code=source_code,
                    error_context={"error_message": error_message, **context},
                )

                if result and result.success:
                    action = self.auto_refactor.create_healing_action(
                        pattern=pattern,
                        result=result,
                        target_file=target_file,
                    )
                    session.propose_action(action)
                    self.user_feedback.register_action(action)
                    logger.debug(f"Proposed action: {action.action_id} ({result.description})")

            # Step 3: Try RAG improvement if no good fixes found
            if not session.proposed_actions and source_code:
                rag_context = RAGContext(
                    failed_test=context.get("test_name", "unknown"),
                    error_message=error_message,
                    original_code=source_code,
                    test_file=context.get("test_file", ""),
                    code_file=target_file,
                    stack_trace=context.get("stack_trace"),
                )

                rag_result = await self.rag_feedback.process_failed_test(rag_context)

                if rag_result:
                    action = HealingAction(
                        action_id=f"rag-{uuid.uuid4().hex[:8]}",
                        pattern_id="rag-generated",
                        action_type=ActionType.REGENERATE,
                        code_diff=self._generate_diff(source_code, rag_result.improved_code),
                        target_file=target_file,
                        success_rate=rag_result.confidence,
                    )
                    session.propose_action(action)
                    logger.debug(f"RAG proposed action: {action.action_id}")

            session.status = "ready" if session.proposed_actions else "no_fix_found"

        except Exception as e:
            logger.error(f"Error during failure analysis: {e}")
            session.status = "error"
            session.context["error"] = str(e)

        return session

    def _classify_failure(self, error_message: str) -> FailureType:
        """Classify failure type from error message."""
        error_lower = error_message.lower()

        if any(kw in error_lower for kw in ["syntaxerror", "indentationerror"]):
            return FailureType.SYNTAX
        if any(kw in error_lower for kw in ["typeerror", "valueerror", "keyerror"]):
            return FailureType.RUNTIME
        if any(kw in error_lower for kw in ["assertionerror", "failed"]):
            return FailureType.LOGIC
        if any(kw in error_lower for kw in ["modulenotfound", "import"]):
            return FailureType.DEPENDENCY

        return FailureType.UNKNOWN

    def _generate_diff(self, original: str, fixed: str) -> str:
        """Generate a simple diff between original and fixed code."""
        import difflib
        diff = difflib.unified_diff(
            original.splitlines(keepends=True),
            fixed.splitlines(keepends=True),
            fromfile="original",
            tofile="fixed",
        )
        return "".join(diff)

    async def apply_healing(
        self,
        session_id: str,
        action_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Apply a healing action from a session.

        Args:
            session_id: The session ID
            action_id: Optional specific action to apply (defaults to best)

        Returns:
            Result of the healing action
        """
        if session_id not in self._sessions:
            raise ValueError(f"Session {session_id} not found")

        session = self._sessions[session_id]

        if session.status not in ["ready", "healing"]:
            raise RuntimeError(f"Session is not ready for healing (status: {session.status})")

        # Select action
        if action_id:
            action = next(
                (a for a in session.proposed_actions if a.action_id == action_id),
                None,
            )
            if not action:
                raise ValueError(f"Action {action_id} not found in session")
        else:
            # Select best action (highest success rate)
            if not session.proposed_actions:
                raise RuntimeError("No proposed actions available")
            action = max(session.proposed_actions, key=lambda a: a.success_rate)

        session.apply_action(action)

        # Apply the fix
        source_code = session.context.get("source_code", "")
        success, result = self.auto_refactor.apply_action(action, source_code)

        if success:
            # Validate with Quality Fabric if required
            if self.config.require_validation:
                validation_result = await self._validate_with_qf(
                    result,
                    session.context.get("file", "unknown.py"),
                )
                if not validation_result.get("passed", False):
                    action.mark_failure("Quality Fabric validation failed")
                    session.complete(success=False)
                    return {
                        "success": False,
                        "session_id": session_id,
                        "action_id": action.action_id,
                        "reason": "Validation failed",
                        "validation": validation_result,
                    }

            session.complete(success=True)
            self._update_pattern_confidence(action.pattern_id, success=True)

            return {
                "success": True,
                "session_id": session_id,
                "action_id": action.action_id,
                "fixed_code": result,
                "diff": action.code_diff,
            }
        else:
            session.complete(success=False)
            self._update_pattern_confidence(action.pattern_id, success=False)

            return {
                "success": False,
                "session_id": session_id,
                "action_id": action.action_id,
                "reason": result,
            }

    async def _validate_with_qf(
        self,
        code: str,
        file_path: str,
    ) -> Dict[str, Any]:
        """Validate fixed code with Quality Fabric."""
        # In production, this would call Quality Fabric API
        # For now, do basic validation
        try:
            import ast
            ast.parse(code)
            return {"passed": True, "syntax_valid": True}
        except SyntaxError as e:
            return {"passed": False, "syntax_valid": False, "error": str(e)}

    def _update_pattern_confidence(
        self,
        pattern_id: str,
        success: bool,
    ) -> None:
        """Update pattern confidence based on fix outcome."""
        self.pattern_analyzer.update_pattern_confidence(
            pattern_id=pattern_id,
            success=success,
        )

    def submit_feedback(
        self,
        action_id: str,
        helpful: bool,
        comment: Optional[str] = None,
        suggested_fix: Optional[str] = None,
    ) -> UserFeedback:
        """
        Submit user feedback for a healing action.

        Args:
            action_id: The action to rate
            helpful: Whether the action was helpful
            comment: Optional comment
            suggested_fix: Optional suggested improvement

        Returns:
            The created feedback
        """
        feedback = self.user_feedback.submit_feedback(
            action_id=action_id,
            helpful=helpful,
            comment=comment,
            suggested_fix=suggested_fix,
        )

        # Check for learning updates
        pending = self.user_feedback.get_pending_updates()
        for update in pending:
            self.pattern_analyzer.update_pattern_confidence(
                pattern_id=update.pattern_id,
                success=update.confidence_delta > 0,
                delta=abs(update.confidence_delta),
            )
            self.user_feedback.apply_update(update)

        return feedback

    def get_session(self, session_id: str) -> Optional[HealingSession]:
        """Get a healing session by ID."""
        return self._sessions.get(session_id)

    def get_active_sessions(self) -> List[HealingSession]:
        """Get all active healing sessions."""
        return [
            s for s in self._sessions.values()
            if s.status in ["analyzing", "ready", "healing"]
        ]

    def get_statistics(self) -> Dict[str, Any]:
        """Get healing service statistics."""
        total_sessions = len(self._sessions) + len(self._session_history)
        successful = len([
            s for s in list(self._sessions.values()) + self._session_history
            if s.status == "success"
        ])

        return {
            "enabled": self.config.enabled,
            "total_sessions": total_sessions,
            "active_sessions": len(self.get_active_sessions()),
            "success_rate": successful / total_sessions if total_sessions > 0 else 0.0,
            "patterns": self.pattern_analyzer.get_statistics(),
            "rag": self.rag_feedback.get_statistics(),
            "feedback": self.user_feedback.get_statistics(),
        }

    def cleanup_sessions(self, max_age_hours: int = 24) -> int:
        """
        Clean up old sessions.

        Args:
            max_age_hours: Maximum age of sessions to keep

        Returns:
            Number of sessions cleaned up
        """
        from datetime import timedelta
        cutoff = datetime.utcnow() - timedelta(hours=max_age_hours)
        removed = 0

        for session_id in list(self._sessions.keys()):
            session = self._sessions[session_id]
            if session.completed_at and session.completed_at < cutoff:
                self._session_history.append(session)
                del self._sessions[session_id]
                removed += 1

        # Also clean up old history
        self._session_history = [
            s for s in self._session_history
            if not s.completed_at or s.completed_at > cutoff
        ]

        return removed

    def export_state(self) -> Dict[str, Any]:
        """Export service state for persistence."""
        return {
            "patterns": self.pattern_analyzer.export_patterns(),
            "rag_patterns": self.rag_feedback.export_patterns(),
            "feedback": self.user_feedback.export_feedback(),
            "sessions": [s.to_dict() for s in self._session_history],
        }

    def import_state(self, state: Dict[str, Any]) -> None:
        """Import service state from persistence."""
        if "patterns" in state:
            self.pattern_analyzer.import_patterns(state["patterns"])

        if "rag_patterns" in state:
            self.rag_feedback.import_patterns(state["rag_patterns"])

        if "feedback" in state:
            self.user_feedback.import_feedback(state["feedback"])

        logger.info("Imported healing service state")
