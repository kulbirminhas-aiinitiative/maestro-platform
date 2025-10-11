#!/usr/bin/env python3
"""
Conversation History Manager - Inspired by AutoGen's Message History

Manages shared conversation history for SDLC team.
Replaces simple string context with rich message-based communication.

Key Principles from AutoGen:
1. All agents see the same conversation history
2. Messages are structured and traceable
3. Full context preservation (no information loss)
4. Serialization for persistence and debugging

Based on: Microsoft AutoGen's conversation history pattern
"""

from typing import List, Dict, Any, Optional, Union, Type
from pathlib import Path
import json
import logging

from sdlc_messages import (
    SDLCMessage,
    PersonaWorkMessage,
    ConversationMessage,
    SystemMessage,
    QualityGateMessage,
    message_from_dict,
    message_to_dict
)

logger = logging.getLogger(__name__)


class ConversationHistory:
    """
    Manages SDLC team conversation history
    
    AutoGen Pattern: Shared message history that all agents can access
    
    Features:
    - Rich message storage (not just strings)
    - Filtering by source, phase, type
    - Context extraction for specific personas
    - Serialization for persistence
    - Full traceability
    """
    
    def __init__(self, session_id: str):
        """
        Initialize conversation history
        
        Args:
            session_id: Unique session identifier
        """
        self.session_id = session_id
        self.messages: List[SDLCMessage] = []
        logger.info(f"📝 Initialized conversation history for session {session_id}")
    
    def add_message(self, message: SDLCMessage) -> SDLCMessage:
        """
        Add message to conversation
        
        Args:
            message: SDLCMessage instance
        
        Returns:
            The added message (for chaining)
        """
        self.messages.append(message)
        logger.debug(f"Added message {message.id[:8]} from {message.source}")
        return message
    
    def add_persona_work(
        self,
        persona_id: str,
        phase: str,
        summary: str,
        decisions: List[Dict[str, Any]] = None,
        files_created: List[str] = None,
        deliverables: Dict[str, List[str]] = None,
        questions: List[Dict[str, str]] = None,
        assumptions: List[str] = None,
        dependencies: Dict[str, List[str]] = None,
        concerns: List[str] = None,
        **metadata
    ) -> PersonaWorkMessage:
        """
        Add persona work message
        
        Args:
            persona_id: Persona identifier
            phase: SDLC phase
            summary: Brief summary of work
            decisions: Key decisions made
            files_created: List of files created
            deliverables: Deliverables map
            questions: Questions for team
            assumptions: Assumptions made
            dependencies: Dependencies on/from others
            concerns: Concerns or risks
            **metadata: Additional metadata
        
        Returns:
            Created PersonaWorkMessage
        """
        message = PersonaWorkMessage(
            source=persona_id,
            phase=phase,
            summary=summary,
            decisions=decisions or [],
            files_created=files_created or [],
            deliverables=deliverables or {},
            questions=questions or [],
            assumptions=assumptions or [],
            dependencies=dependencies or {},
            concerns=concerns or [],
            metadata=metadata
        )
        return self.add_message(message)
    
    def add_discussion(
        self,
        persona_id: str,
        content: str,
        phase: str,
        message_type: str = "discussion",
        reply_to: Optional[str] = None,
        **metadata
    ) -> ConversationMessage:
        """
        Add discussion message (for group chat)
        
        Args:
            persona_id: Persona identifier
            content: Message content
            phase: SDLC phase
            message_type: Type (discussion, question, answer, concern, proposal)
            reply_to: Message ID this is replying to
            **metadata: Additional metadata
        
        Returns:
            Created ConversationMessage
        """
        message = ConversationMessage(
            source=persona_id,
            phase=phase,
            content=content,
            message_type=message_type,
            reply_to=reply_to,
            metadata=metadata
        )
        return self.add_message(message)
    
    def add_system_message(
        self,
        content: str,
        phase: str,
        level: str = "info",
        **metadata
    ) -> SystemMessage:
        """
        Add system message
        
        Args:
            content: Message content
            phase: SDLC phase
            level: Message level (info, warning, error, success)
            **metadata: Additional metadata
        
        Returns:
            Created SystemMessage
        """
        message = SystemMessage(
            source="system",
            phase=phase,
            content=content,
            level=level,
            metadata=metadata
        )
        return self.add_message(message)
    
    def add_quality_gate(
        self,
        persona_id: str,
        phase: str,
        passed: bool,
        quality_score: float,
        completeness_percentage: float,
        metrics: Dict[str, Any] = None,
        issues: List[Dict[str, str]] = None,
        recommendations: List[str] = None,
        **metadata
    ) -> QualityGateMessage:
        """
        Add quality gate result message
        
        Args:
            persona_id: Persona evaluated
            phase: SDLC phase
            passed: Whether gate passed
            quality_score: Quality score (0-1)
            completeness_percentage: Completeness (0-100)
            metrics: Quality metrics
            issues: Issues found
            recommendations: Recommendations
            **metadata: Additional metadata
        
        Returns:
            Created QualityGateMessage
        """
        message = QualityGateMessage(
            source="quality_gate",
            phase=phase,
            persona_evaluated=persona_id,
            passed=passed,
            quality_score=quality_score,
            completeness_percentage=completeness_percentage,
            metrics=metrics or {},
            issues=issues or [],
            recommendations=recommendations or [],
            metadata=metadata
        )
        return self.add_message(message)
    
    def get_messages(
        self,
        source: Optional[str] = None,
        phase: Optional[str] = None,
        message_type: Optional[Type[SDLCMessage]] = None,
        limit: Optional[int] = None,
        skip_system: bool = False
    ) -> List[SDLCMessage]:
        """
        Filter and retrieve messages
        
        Args:
            source: Filter by source persona
            phase: Filter by SDLC phase
            message_type: Filter by message type class
            limit: Limit to last N messages
            skip_system: Skip system messages
        
        Returns:
            List of matching messages
        """
        filtered = self.messages
        
        if skip_system:
            filtered = [m for m in filtered if not isinstance(m, SystemMessage)]
        
        if source:
            filtered = [m for m in filtered if m.source == source]
        
        if phase:
            filtered = [m for m in filtered if m.phase == phase]
        
        if message_type:
            filtered = [m for m in filtered if isinstance(m, message_type)]
        
        if limit:
            filtered = filtered[-limit:]
        
        return filtered
    
    def get_conversation_text(
        self,
        include_system: bool = True,
        max_messages: Optional[int] = None,
        phase: Optional[str] = None
    ) -> str:
        """
        Get formatted conversation for prompt injection
        
        AutoGen Pattern: Format entire conversation history as text
        
        Args:
            include_system: Include system messages
            max_messages: Limit to recent N messages
            phase: Filter by phase
        
        Returns:
            Formatted conversation text
        """
        messages = self.messages
        
        if not include_system:
            messages = [m for m in messages if not isinstance(m, SystemMessage)]
        
        if phase:
            messages = [m for m in messages if m.phase == phase]
        
        if max_messages:
            messages = messages[-max_messages:]
        
        if not messages:
            return "No conversation history yet."
        
        return "\n\n".join([msg.to_text() for msg in messages])
    
    def get_persona_context(
        self,
        persona_id: str,
        phase: Optional[str] = None,
        max_messages: int = 50
    ) -> str:
        """
        Get context relevant to specific persona
        
        Includes:
        - Work from other personas (what they did and why)
        - Questions directed to this persona
        - Dependencies on this persona
        - Recent discussion
        
        Args:
            persona_id: Persona to get context for
            phase: Filter by phase (optional)
            max_messages: Maximum messages to include
        
        Returns:
            Formatted context string
        """
        # Get work from other personas
        other_work = self.get_messages(
            message_type=PersonaWorkMessage,
            phase=phase
        )
        other_work = [m for m in other_work if m.source != persona_id][-10:]  # Last 10
        
        # Get questions directed to this persona
        questions_for_me = []
        for msg in self.get_messages(message_type=PersonaWorkMessage):
            if isinstance(msg, PersonaWorkMessage):
                for q in msg.questions:
                    if q.get('for') == persona_id:
                        questions_for_me.append({
                            "from": msg.source,
                            "question": q['question'],
                            "message_id": msg.id
                        })
        
        # Get recent discussion
        discussions = self.get_messages(
            message_type=ConversationMessage,
            phase=phase,
            limit=20
        )
        
        # Build context
        context_parts = []
        
        # Section 1: Previous Work
        if other_work:
            context_parts.append("## Previous Team Work\n")
            for msg in other_work:
                context_parts.append(msg.to_text())
                context_parts.append("")  # Blank line
        
        # Section 2: Questions for You
        if questions_for_me:
            context_parts.append("## Questions Directed to You\n")
            for q in questions_for_me:
                context_parts.append(f"**From {q['from'].replace('_', ' ').title()}:** {q['question']}\n")
            context_parts.append("")
        
        # Section 3: Recent Discussion
        if discussions:
            context_parts.append("## Recent Team Discussion\n")
            for msg in discussions[-10:]:  # Last 10 discussion messages
                context_parts.append(msg.to_text())
                context_parts.append("")
        
        # Section 4: Dependencies
        depends_on_me = []
        for msg in self.get_messages(message_type=PersonaWorkMessage):
            if isinstance(msg, PersonaWorkMessage):
                if persona_id in msg.dependencies.get('depends_on', []):
                    depends_on_me.append(msg.source)
        
        if depends_on_me:
            context_parts.append(f"## Personas Depending on Your Work\n")
            context_parts.append(f"{', '.join([p.replace('_', ' ').title() for p in depends_on_me])}\n")
        
        if not context_parts:
            return "No previous team context available. You are the first to work on this project."
        
        return "\n".join(context_parts)
    
    def get_summary_statistics(self) -> Dict[str, Any]:
        """
        Get conversation statistics
        
        Returns:
            Dictionary with statistics
        """
        return {
            "total_messages": len(self.messages),
            "by_type": {
                "persona_work": len([m for m in self.messages if isinstance(m, PersonaWorkMessage)]),
                "discussions": len([m for m in self.messages if isinstance(m, ConversationMessage)]),
                "system": len([m for m in self.messages if isinstance(m, SystemMessage)]),
                "quality_gates": len([m for m in self.messages if isinstance(m, QualityGateMessage)])
            },
            "unique_sources": len(set(m.source for m in self.messages)),
            "phases": list(set(m.phase for m in self.messages)),
            "questions_asked": sum(
                len(m.questions)
                for m in self.messages
                if isinstance(m, PersonaWorkMessage)
            ),
            "decisions_made": sum(
                len(m.decisions)
                for m in self.messages
                if isinstance(m, PersonaWorkMessage)
            )
        }
    
    def save(self, filepath: Path) -> None:
        """
        Save conversation to disk
        
        AutoGen Pattern: Persist conversation for debugging/resuming
        
        Args:
            filepath: Path to save to
        """
        data = {
            "session_id": self.session_id,
            "message_count": len(self.messages),
            "messages": [message_to_dict(msg) for msg in self.messages]
        }
        
        filepath.parent.mkdir(parents=True, exist_ok=True)
        filepath.write_text(json.dumps(data, indent=2))
        logger.info(f"💾 Saved conversation ({len(self.messages)} messages) to {filepath}")
    
    @classmethod
    def load(cls, filepath: Path) -> 'ConversationHistory':
        """
        Load conversation from disk
        
        AutoGen Pattern: Resume from saved conversation
        
        Args:
            filepath: Path to load from
        
        Returns:
            ConversationHistory instance
        """
        data = json.loads(filepath.read_text())
        conv = cls(data["session_id"])
        
        # Reconstruct messages
        for msg_data in data["messages"]:
            try:
                msg = message_from_dict(msg_data)
                conv.messages.append(msg)
            except Exception as e:
                logger.warning(f"Failed to load message: {e}")
                # Continue loading other messages
        
        logger.info(f"📂 Loaded conversation ({len(conv.messages)} messages) from {filepath}")
        return conv
    
    def clear(self) -> None:
        """Clear all messages (for testing)"""
        self.messages.clear()
        logger.info(f"🗑️ Cleared conversation history")
    
    def __len__(self) -> int:
        """Number of messages in conversation"""
        return len(self.messages)
    
    def __repr__(self) -> str:
        """String representation"""
        return f"ConversationHistory(session={self.session_id}, messages={len(self.messages)})"
