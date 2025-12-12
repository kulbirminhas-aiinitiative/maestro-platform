"""
Guild Definitions - Agent Capability Classifications

EPIC: MD-3107 - Agora Phase 2: Guilds & Registry
AC-1: Define Guild schemas (Coder, Reviewer, Architect, Tester, etc.)

Guilds represent categories of agent capabilities in the Agora.
Each Guild has:
- A set of skills/capabilities
- A typical cost range
- Quality standards expected

Reference: docs/roadmap/AGORA_PHASE2_DETAILED_BACKLOG.md (AGORA-105)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Set

logger = logging.getLogger(__name__)


class GuildType(Enum):
    """
    Guild types representing agent specializations.

    The Agora society organizes agents into Guilds based on their
    primary capabilities and roles in the development lifecycle.
    """

    # Code Production Guilds
    CODER = "coder"
    ARCHITECT = "architect"
    FRONTEND_DEVELOPER = "frontend_developer"
    BACKEND_DEVELOPER = "backend_developer"
    API_DEVELOPER = "api_developer"
    DATABASE_ENGINEER = "database_engineer"

    # Quality Assurance Guilds
    REVIEWER = "reviewer"
    TESTER = "tester"
    QA_ENGINEER = "qa_engineer"
    SECURITY_ANALYST = "security_analyst"

    # Documentation & Design Guilds
    TECHNICAL_WRITER = "technical_writer"
    UX_DESIGNER = "ux_designer"
    REQUIREMENTS_ANALYST = "requirements_analyst"

    # Operations Guilds
    DEVOPS_ENGINEER = "devops_engineer"
    SRE = "sre"

    # Coordination Guilds
    PROJECT_MANAGER = "project_manager"
    SCRUM_MASTER = "scrum_master"

    # Generalist
    GENERALIST = "generalist"


@dataclass
class GuildProfile:
    """
    Profile defining a Guild's characteristics.

    Attributes:
        guild_type: The type of guild
        name: Human-readable name
        description: What this guild does
        skills: Set of skills this guild provides
        cost_per_token_range: (min, max) token cost range
        quality_tier: Expected quality level (1-5)
        can_collaborate_with: List of compatible guilds
    """

    guild_type: GuildType
    name: str
    description: str
    skills: Set[str] = field(default_factory=set)
    cost_per_token_range: tuple[float, float] = (0.001, 0.01)
    quality_tier: int = 3
    can_collaborate_with: List[GuildType] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)

    def has_skill(self, skill: str) -> bool:
        """Check if guild has a specific skill."""
        return skill.lower() in {s.lower() for s in self.skills}

    def is_affordable(self, max_cost: float) -> bool:
        """Check if guild's minimum cost is within budget."""
        return self.cost_per_token_range[0] <= max_cost

    def to_dict(self) -> Dict[str, Any]:
        """Serialize guild profile to dictionary."""
        return {
            "guild_type": self.guild_type.value,
            "name": self.name,
            "description": self.description,
            "skills": list(self.skills),
            "cost_per_token_range": list(self.cost_per_token_range),
            "quality_tier": self.quality_tier,
            "can_collaborate_with": [g.value for g in self.can_collaborate_with],
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
        }


class Guild:
    """
    Guild singleton registry for guild profiles.

    This class maintains the canonical definitions of all guilds
    and provides factory methods for creating guild profiles.
    """

    _profiles: Dict[GuildType, GuildProfile] = {}
    _initialized: bool = False

    @classmethod
    def initialize(cls) -> None:
        """Initialize all guild profiles."""
        if cls._initialized:
            return

        cls._profiles = {
            # Code Production Guilds
            GuildType.CODER: GuildProfile(
                guild_type=GuildType.CODER,
                name="Coder",
                description="Writes production-quality code across multiple languages",
                skills={"python", "typescript", "javascript", "code_generation", "debugging"},
                cost_per_token_range=(0.001, 0.01),
                quality_tier=4,
                can_collaborate_with=[GuildType.REVIEWER, GuildType.TESTER, GuildType.ARCHITECT],
            ),
            GuildType.ARCHITECT: GuildProfile(
                guild_type=GuildType.ARCHITECT,
                name="Solution Architect",
                description="Designs system architecture and technical solutions",
                skills={"system_design", "architecture", "api_design", "database_design", "patterns"},
                cost_per_token_range=(0.005, 0.02),
                quality_tier=5,
                can_collaborate_with=[GuildType.CODER, GuildType.BACKEND_DEVELOPER, GuildType.DEVOPS_ENGINEER],
            ),
            GuildType.FRONTEND_DEVELOPER: GuildProfile(
                guild_type=GuildType.FRONTEND_DEVELOPER,
                name="Frontend Developer",
                description="Builds user interfaces and client-side applications",
                skills={"react", "typescript", "css", "html", "accessibility", "responsive_design"},
                cost_per_token_range=(0.001, 0.008),
                quality_tier=4,
                can_collaborate_with=[GuildType.UX_DESIGNER, GuildType.BACKEND_DEVELOPER],
            ),
            GuildType.BACKEND_DEVELOPER: GuildProfile(
                guild_type=GuildType.BACKEND_DEVELOPER,
                name="Backend Developer",
                description="Builds server-side applications and APIs",
                skills={"python", "node", "database", "api", "microservices", "security"},
                cost_per_token_range=(0.001, 0.01),
                quality_tier=4,
                can_collaborate_with=[GuildType.FRONTEND_DEVELOPER, GuildType.DATABASE_ENGINEER, GuildType.API_DEVELOPER],
            ),
            GuildType.API_DEVELOPER: GuildProfile(
                guild_type=GuildType.API_DEVELOPER,
                name="API Developer",
                description="Designs and implements RESTful and GraphQL APIs",
                skills={"rest_api", "graphql", "openapi", "authentication", "rate_limiting"},
                cost_per_token_range=(0.001, 0.01),
                quality_tier=4,
                can_collaborate_with=[GuildType.BACKEND_DEVELOPER, GuildType.SECURITY_ANALYST],
            ),
            GuildType.DATABASE_ENGINEER: GuildProfile(
                guild_type=GuildType.DATABASE_ENGINEER,
                name="Database Engineer",
                description="Designs and optimizes database schemas and queries",
                skills={"sql", "postgresql", "mongodb", "redis", "optimization", "migration"},
                cost_per_token_range=(0.002, 0.012),
                quality_tier=4,
                can_collaborate_with=[GuildType.BACKEND_DEVELOPER, GuildType.ARCHITECT],
            ),

            # Quality Assurance Guilds
            GuildType.REVIEWER: GuildProfile(
                guild_type=GuildType.REVIEWER,
                name="Code Reviewer",
                description="Reviews code for quality, security, and best practices",
                skills={"code_review", "security_review", "best_practices", "mentoring"},
                cost_per_token_range=(0.002, 0.01),
                quality_tier=5,
                can_collaborate_with=[GuildType.CODER, GuildType.SECURITY_ANALYST],
            ),
            GuildType.TESTER: GuildProfile(
                guild_type=GuildType.TESTER,
                name="Tester",
                description="Writes and executes tests for software quality",
                skills={"unit_testing", "integration_testing", "e2e_testing", "pytest", "jest"},
                cost_per_token_range=(0.001, 0.008),
                quality_tier=4,
                can_collaborate_with=[GuildType.CODER, GuildType.QA_ENGINEER],
            ),
            GuildType.QA_ENGINEER: GuildProfile(
                guild_type=GuildType.QA_ENGINEER,
                name="QA Engineer",
                description="Comprehensive quality assurance and test automation",
                skills={"test_automation", "ci_cd", "performance_testing", "regression_testing"},
                cost_per_token_range=(0.002, 0.01),
                quality_tier=4,
                can_collaborate_with=[GuildType.TESTER, GuildType.DEVOPS_ENGINEER],
            ),
            GuildType.SECURITY_ANALYST: GuildProfile(
                guild_type=GuildType.SECURITY_ANALYST,
                name="Security Analyst",
                description="Identifies and mitigates security vulnerabilities",
                skills={"security_audit", "penetration_testing", "owasp", "vulnerability_assessment"},
                cost_per_token_range=(0.005, 0.02),
                quality_tier=5,
                can_collaborate_with=[GuildType.REVIEWER, GuildType.API_DEVELOPER, GuildType.BACKEND_DEVELOPER],
            ),

            # Documentation & Design Guilds
            GuildType.TECHNICAL_WRITER: GuildProfile(
                guild_type=GuildType.TECHNICAL_WRITER,
                name="Technical Writer",
                description="Creates technical documentation and guides",
                skills={"documentation", "api_docs", "user_guides", "markdown", "diagrams"},
                cost_per_token_range=(0.001, 0.006),
                quality_tier=4,
                can_collaborate_with=[GuildType.CODER, GuildType.ARCHITECT],
            ),
            GuildType.UX_DESIGNER: GuildProfile(
                guild_type=GuildType.UX_DESIGNER,
                name="UX Designer",
                description="Designs user experiences and interfaces",
                skills={"ux_design", "wireframing", "prototyping", "user_research", "accessibility"},
                cost_per_token_range=(0.002, 0.01),
                quality_tier=4,
                can_collaborate_with=[GuildType.FRONTEND_DEVELOPER, GuildType.REQUIREMENTS_ANALYST],
            ),
            GuildType.REQUIREMENTS_ANALYST: GuildProfile(
                guild_type=GuildType.REQUIREMENTS_ANALYST,
                name="Requirements Analyst",
                description="Analyzes and documents business requirements",
                skills={"requirements_gathering", "user_stories", "acceptance_criteria", "bdd"},
                cost_per_token_range=(0.002, 0.01),
                quality_tier=4,
                can_collaborate_with=[GuildType.ARCHITECT, GuildType.PROJECT_MANAGER],
            ),

            # Operations Guilds
            GuildType.DEVOPS_ENGINEER: GuildProfile(
                guild_type=GuildType.DEVOPS_ENGINEER,
                name="DevOps Engineer",
                description="Manages CI/CD, infrastructure, and deployments",
                skills={"docker", "kubernetes", "terraform", "ci_cd", "aws", "monitoring"},
                cost_per_token_range=(0.003, 0.015),
                quality_tier=4,
                can_collaborate_with=[GuildType.BACKEND_DEVELOPER, GuildType.SRE],
            ),
            GuildType.SRE: GuildProfile(
                guild_type=GuildType.SRE,
                name="Site Reliability Engineer",
                description="Ensures system reliability and performance",
                skills={"monitoring", "alerting", "incident_response", "performance", "scaling"},
                cost_per_token_range=(0.004, 0.018),
                quality_tier=5,
                can_collaborate_with=[GuildType.DEVOPS_ENGINEER, GuildType.BACKEND_DEVELOPER],
            ),

            # Coordination Guilds
            GuildType.PROJECT_MANAGER: GuildProfile(
                guild_type=GuildType.PROJECT_MANAGER,
                name="Project Manager",
                description="Coordinates project execution and team communication",
                skills={"project_management", "agile", "communication", "planning", "risk_management"},
                cost_per_token_range=(0.002, 0.01),
                quality_tier=4,
                can_collaborate_with=[GuildType.REQUIREMENTS_ANALYST, GuildType.SCRUM_MASTER],
            ),
            GuildType.SCRUM_MASTER: GuildProfile(
                guild_type=GuildType.SCRUM_MASTER,
                name="Scrum Master",
                description="Facilitates agile processes and removes blockers",
                skills={"scrum", "agile", "facilitation", "coaching", "retrospectives"},
                cost_per_token_range=(0.002, 0.008),
                quality_tier=3,
                can_collaborate_with=[GuildType.PROJECT_MANAGER],
            ),

            # Generalist
            GuildType.GENERALIST: GuildProfile(
                guild_type=GuildType.GENERALIST,
                name="Generalist",
                description="Versatile agent capable of multiple roles",
                skills={"python", "documentation", "testing", "debugging"},
                cost_per_token_range=(0.001, 0.005),
                quality_tier=3,
                can_collaborate_with=list(GuildType),
            ),
        }

        cls._initialized = True
        logger.info(f"Guild registry initialized with {len(cls._profiles)} guild profiles")

    @classmethod
    def get_profile(cls, guild_type: GuildType) -> GuildProfile:
        """Get the profile for a guild type."""
        cls.initialize()
        if guild_type not in cls._profiles:
            raise ValueError(f"Unknown guild type: {guild_type}")
        return cls._profiles[guild_type]

    @classmethod
    def get_all_profiles(cls) -> Dict[GuildType, GuildProfile]:
        """Get all guild profiles."""
        cls.initialize()
        return cls._profiles.copy()

    @classmethod
    def find_by_skill(cls, skill: str) -> List[GuildProfile]:
        """Find all guilds that have a specific skill."""
        cls.initialize()
        return [p for p in cls._profiles.values() if p.has_skill(skill)]

    @classmethod
    def find_affordable(cls, max_cost: float) -> List[GuildProfile]:
        """Find all guilds within a budget."""
        cls.initialize()
        return [p for p in cls._profiles.values() if p.is_affordable(max_cost)]
