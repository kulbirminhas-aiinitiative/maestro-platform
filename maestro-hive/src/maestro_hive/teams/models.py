from enum import Enum
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

class TeamRole(Enum):
    """Team member roles."""
    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"
    VIEWER = "viewer"
    AI_AGENT = "ai_agent"

class MemberType(Enum):
    """Types of team members."""
    HUMAN = "human"
    AI_AGENT = "ai_agent"
    HYBRID = "hybrid"  # Human with AI assistant

class TeamStatus(Enum):
    """Team status states."""
    DRAFT = "draft"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    ARCHIVED = "archived"

class CollaborationMode(Enum):
    """Human-AI collaboration modes."""
    HUMAN_ONLY = "human_only"
    AI_ASSISTED = "ai_assisted"
    AI_LED = "ai_led"
    AUTONOMOUS = "autonomous"


@dataclass
class TeamMember:
    """Represents a team member."""
    id: str
    name: str
    email: Optional[str]
    member_type: MemberType
    role: TeamRole
    skills: List[str] = field(default_factory=list)
    permissions: List[str] = field(default_factory=list)
    joined_at: Optional[str] = None
    ai_config: Optional[Dict[str, Any]] = None
