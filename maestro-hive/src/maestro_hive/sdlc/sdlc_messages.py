#!/usr/bin/env python3
"""
SDLC Message Types - Inspired by AutoGen's Message Architecture

Provides rich, structured messages for team communication instead of simple strings.
Each message is traceable, serializable, and preserves full context.

Based on: Microsoft AutoGen's BaseChatMessage pattern
"""

from typing import Dict, List, Any, Optional
from datetime import datetime
from pydantic import BaseModel, Field
import uuid


class SDLCMessage(BaseModel):
    """
    Base message for SDLC team communication
    
    Inspired by AutoGen's BaseChatMessage:
    - Unique ID for traceability
    - Source tracking (which persona)
    - Timestamps for temporal ordering
    - Metadata for arbitrary context
    - Serialization support
    """
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    """Unique message identifier"""
    
    source: str
    """Persona that created this message (persona_id)"""
    
    created_at: datetime = Field(default_factory=datetime.now)
    """When message was created"""
    
    phase: str
    """SDLC phase (requirements, design, implementation, testing, deployment)"""
    
    metadata: Dict[str, Any] = Field(default_factory=dict)
    """Additional metadata (duration, quality_score, deliverables, etc.)"""
    
    def to_text(self) -> str:
        """Convert to human-readable text representation"""
        raise NotImplementedError("Subclasses must implement to_text()")
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary for JSON storage"""
        return self.model_dump(mode="json")
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SDLCMessage':
        """Deserialize from dictionary"""
        return cls.model_validate(data)
    
    class Config:
        """Pydantic config"""
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class PersonaWorkMessage(SDLCMessage):
    """
    Message containing persona's work output
    
    Replaces simple "created N files" with rich structured output:
    - Summary of work done
    - Key decisions with rationale
    - Trade-offs considered
    - Questions for other personas
    - Assumptions made
    - Dependencies on/from others
    """
    
    summary: str
    """Brief summary of work done (1-2 sentences)"""
    
    decisions: List[Dict[str, Any]] = Field(default_factory=list)
    """
    Key decisions made during work:
    [
        {
            "decision": "What was decided",
            "rationale": "Why this decision",
            "alternatives_considered": ["Option A", "Option B"],
            "trade_offs": "What was traded off"
        }
    ]
    """
    
    files_created: List[str] = Field(default_factory=list)
    """List of files created by this persona"""
    
    deliverables: Dict[str, List[str]] = Field(default_factory=dict)
    """
    Deliverables mapped to files:
    {
        "api_implementation": ["server.ts", "routes/api.ts"],
        "database_schema": ["prisma/schema.prisma"]
    }
    """
    
    questions: List[Dict[str, str]] = Field(default_factory=list)
    """
    Questions for other team members:
    [
        {
            "for": "frontend_developer",
            "question": "What response format do you prefer?"
        }
    ]
    """
    
    assumptions: List[str] = Field(default_factory=list)
    """
    Assumptions made during work:
    - "Frontend will handle JWT storage"
    - "CORS will be configured by DevOps"
    """
    
    dependencies: Dict[str, List[str]] = Field(default_factory=dict)
    """
    Dependencies on/from other personas:
    {
        "depends_on": ["solution_architect"],
        "provides_for": ["frontend_developer", "qa_engineer"]
    }
    """
    
    concerns: List[str] = Field(default_factory=list)
    """Any concerns or risks identified"""
    
    def to_text(self) -> str:
        """Format as readable markdown text"""
        text = f"## {self.source.replace('_', ' ').title()} ({self.phase})\n\n"
        text += f"**Summary:** {self.summary}\n\n"
        
        if self.decisions:
            text += "### Key Decisions\n\n"
            for i, decision in enumerate(self.decisions, 1):
                text += f"{i}. **{decision.get('decision', 'N/A')}**\n"
                text += f"   - Rationale: {decision.get('rationale', 'N/A')}\n"
                if decision.get('alternatives_considered'):
                    text += f"   - Alternatives: {', '.join(decision['alternatives_considered'])}\n"
                if decision.get('trade_offs'):
                    text += f"   - Trade-offs: {decision['trade_offs']}\n"
                text += "\n"
        
        if self.questions:
            text += "### Questions for Team\n\n"
            for q in self.questions:
                text += f"- **For {q.get('for', 'team')}:** {q.get('question', 'N/A')}\n"
            text += "\n"
        
        if self.assumptions:
            text += "### Assumptions\n\n"
            for assumption in self.assumptions:
                text += f"- {assumption}\n"
            text += "\n"
        
        if self.concerns:
            text += "### Concerns/Risks\n\n"
            for concern in self.concerns:
                text += f"- ⚠️ {concern}\n"
            text += "\n"
        
        if self.dependencies:
            if self.dependencies.get('depends_on'):
                text += f"**Depends on:** {', '.join(self.dependencies['depends_on'])}\n"
            if self.dependencies.get('provides_for'):
                text += f"**Provides for:** {', '.join(self.dependencies['provides_for'])}\n"
            text += "\n"
        
        text += f"**Files:** {len(self.files_created)} created\n"
        if len(self.files_created) <= 10:
            for f in self.files_created:
                text += f"  - {f}\n"
        else:
            for f in self.files_created[:8]:
                text += f"  - {f}\n"
            text += f"  ... and {len(self.files_created) - 8} more\n"
        
        return text


class ConversationMessage(SDLCMessage):
    """
    Message for group discussion/chat
    
    Used in group chat pattern for collaborative design:
    - Discussion comments
    - Questions to specific personas
    - Answers to questions
    - Concerns raised
    - Proposals made
    """
    
    content: str
    """The actual message content"""
    
    reply_to: Optional[str] = None
    """ID of message this is replying to"""
    
    message_type: str = "discussion"
    """
    Type of message:
    - discussion: General discussion
    - question: Asking a question
    - answer: Answering a question
    - concern: Raising a concern
    - proposal: Proposing a solution
    """
    
    def to_text(self) -> str:
        """Format with emoji prefix based on type"""
        prefix = {
            "question": "❓",
            "answer": "💡",
            "concern": "⚠️",
            "proposal": "📋",
            "discussion": "💬"
        }.get(self.message_type, "💬")
        
        text = f"{prefix} **{self.source.replace('_', ' ').title()}:** {self.content}"
        
        if self.reply_to:
            text = f"  ↳ {text} (replying to {self.reply_to[:8]}...)"
        
        return text


class SystemMessage(SDLCMessage):
    """
    System/orchestrator message
    
    Used for:
    - Phase transitions
    - Quality gate results
    - Orchestration decisions
    - Error/warning messages
    """
    
    content: str
    """System message content"""
    
    level: str = "info"
    """Message level: info, warning, error, success"""
    
    def to_text(self) -> str:
        """Format with icon based on level"""
        icon = {
            "info": "ℹ️",
            "warning": "⚠️",
            "error": "❌",
            "success": "✅"
        }[self.level]
        
        return f"{icon} **SYSTEM:** {self.content}"


class QualityGateMessage(SDLCMessage):
    """
    Message for quality gate results
    
    Captures quality validation results:
    - Whether gate passed
    - Quality metrics
    - Issues found
    - Recommendations
    """
    
    persona_evaluated: str
    """Which persona's work was evaluated"""
    
    passed: bool
    """Whether quality gate passed"""
    
    quality_score: float
    """Overall quality score (0-1)"""
    
    completeness_percentage: float
    """Completeness percentage (0-100)"""
    
    metrics: Dict[str, Any] = Field(default_factory=dict)
    """
    Detailed quality metrics:
    {
        "pylint_score": 8.5,
        "test_coverage": 85.0,
        "security_issues": 0
    }
    """
    
    issues: List[Dict[str, str]] = Field(default_factory=list)
    """
    Issues found:
    [
        {"severity": "high", "description": "Missing error handling"}
    ]
    """
    
    recommendations: List[str] = Field(default_factory=list)
    """Recommendations for improvement"""
    
    def to_text(self) -> str:
        """Format quality gate result"""
        status = "✅ PASSED" if self.passed else "❌ FAILED"
        
        text = f"## Quality Gate: {self.persona_evaluated.replace('_', ' ').title()}\n\n"
        text += f"**Status:** {status}\n"
        text += f"**Quality Score:** {self.quality_score:.2f}\n"
        text += f"**Completeness:** {self.completeness_percentage:.1f}%\n\n"
        
        if self.metrics:
            text += "### Metrics\n\n"
            for key, value in self.metrics.items():
                text += f"- {key.replace('_', ' ').title()}: {value}\n"
            text += "\n"
        
        if self.issues:
            text += "### Issues Found\n\n"
            critical = [i for i in self.issues if i.get('severity') == 'critical']
            high = [i for i in self.issues if i.get('severity') == 'high']
            
            if critical:
                text += f"❌ **Critical:** {len(critical)}\n"
            if high:
                text += f"⚠️ **High:** {len(high)}\n"
            text += f"Total: {len(self.issues)}\n\n"
        
        if self.recommendations and not self.passed:
            text += "### Recommendations\n\n"
            for rec in self.recommendations[:5]:
                text += f"- {rec}\n"
            if len(self.recommendations) > 5:
                text += f"... and {len(self.recommendations) - 5} more\n"
        
        return text


# Message factory for deserialization
MESSAGE_TYPE_MAP = {
    "PersonaWorkMessage": PersonaWorkMessage,
    "ConversationMessage": ConversationMessage,
    "SystemMessage": SystemMessage,
    "QualityGateMessage": QualityGateMessage,
}


def message_from_dict(data: Dict[str, Any]) -> SDLCMessage:
    """
    Create message from dictionary with automatic type detection
    
    Args:
        data: Message data dict (must have __type__ or detectable fields)
    
    Returns:
        Appropriate SDLCMessage subclass instance
    """
    # Check for explicit type
    if "__type__" in data:
        msg_type = MESSAGE_TYPE_MAP.get(data["__type__"])
        if msg_type:
            data_copy = data.copy()
            del data_copy["__type__"]
            return msg_type.from_dict(data_copy)
    
    # Auto-detect based on fields
    if "decisions" in data and "files_created" in data:
        return PersonaWorkMessage.from_dict(data)
    elif "content" in data and "message_type" in data:
        return ConversationMessage.from_dict(data)
    elif "quality_score" in data and "passed" in data:
        return QualityGateMessage.from_dict(data)
    elif "content" in data and "level" in data:
        return SystemMessage.from_dict(data)
    else:
        # Fallback to base message (though shouldn't happen)
        raise ValueError(f"Cannot determine message type from data: {data.keys()}")


def message_to_dict(message: SDLCMessage) -> Dict[str, Any]:
    """
    Convert message to dictionary with type information
    
    Args:
        message: SDLCMessage instance
    
    Returns:
        Dictionary with __type__ field for deserialization
    """
    data = message.to_dict()
    data["__type__"] = message.__class__.__name__
    return data
