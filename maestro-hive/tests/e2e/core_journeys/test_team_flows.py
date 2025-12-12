"""
Team Management E2E Tests.

EPIC: MD-3034 - Core User Journey E2E Tests
Tests team lifecycle, blueprints, and human-AI collaboration.
"""

import pytest
import asyncio
import json
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass, field
from enum import Enum
from unittest.mock import AsyncMock, MagicMock, patch


from src.maestro_hive.teams.models import TeamRole, MemberType, TeamStatus, CollaborationMode, TeamMember



@dataclass
class TeamBlueprint:
    """Template for creating teams."""
    id: str
    name: str
    description: str
    default_roles: List[Dict[str, Any]]
    required_skills: List[str]
    collaboration_mode: CollaborationMode
    ai_agents: List[Dict[str, Any]] = field(default_factory=list)
    workflows: List[str] = field(default_factory=list)


class TeamSimulator:
    """Simulates team management operations for E2E testing."""

    def __init__(self):
        self.teams: Dict[str, Dict[str, Any]] = {}
        self.members: Dict[str, Dict[str, TeamMember]] = {}
        self.blueprints: Dict[str, TeamBlueprint] = {}
        self.invitations: Dict[str, Dict[str, Any]] = {}
        self._init_default_blueprints()

    def _init_default_blueprints(self):
        """Initialize default team blueprints."""
        self.blueprints = {
            "development_team": TeamBlueprint(
                id="development_team",
                name="Development Team",
                description="Standard software development team",
                default_roles=[
                    {"role": TeamRole.ADMIN.value, "count": 1, "title": "Tech Lead"},
                    {"role": TeamRole.MEMBER.value, "count": 4, "title": "Developer"},
                    {"role": TeamRole.AI_AGENT.value, "count": 2, "title": "AI Assistant"}
                ],
                required_skills=["coding", "testing", "code_review"],
                collaboration_mode=CollaborationMode.AI_ASSISTED,
                ai_agents=[
                    {"type": "code_reviewer", "name": "CodeReview AI"},
                    {"type": "test_generator", "name": "TestGen AI"}
                ]
            ),
            "research_team": TeamBlueprint(
                id="research_team",
                name="Research Team",
                description="AI-led research team",
                default_roles=[
                    {"role": TeamRole.ADMIN.value, "count": 1, "title": "Research Lead"},
                    {"role": TeamRole.MEMBER.value, "count": 2, "title": "Researcher"},
                    {"role": TeamRole.AI_AGENT.value, "count": 3, "title": "AI Researcher"}
                ],
                required_skills=["research", "analysis", "writing"],
                collaboration_mode=CollaborationMode.AI_LED,
                ai_agents=[
                    {"type": "literature_review", "name": "Literature AI"},
                    {"type": "data_analysis", "name": "Analysis AI"},
                    {"type": "writing_assistant", "name": "Writing AI"}
                ]
            ),
            "support_team": TeamBlueprint(
                id="support_team",
                name="Support Team",
                description="Customer support team with AI agents",
                default_roles=[
                    {"role": TeamRole.ADMIN.value, "count": 1, "title": "Support Manager"},
                    {"role": TeamRole.MEMBER.value, "count": 3, "title": "Support Agent"},
                    {"role": TeamRole.AI_AGENT.value, "count": 1, "title": "AI Support"}
                ],
                required_skills=["customer_service", "troubleshooting", "communication"],
                collaboration_mode=CollaborationMode.AI_ASSISTED,
                ai_agents=[
                    {"type": "customer_support", "name": "Support AI"}
                ]
            )
        }

    async def create_team(
        self,
        name: str,
        description: str = "",
        owner_id: str = None,
        blueprint_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create a new team."""
        team_id = f"team_{uuid.uuid4().hex[:12]}"

        team = {
            "id": team_id,
            "name": name,
            "description": description,
            "status": TeamStatus.DRAFT.value,
            "blueprint_id": blueprint_id,
            "collaboration_mode": CollaborationMode.HUMAN_ONLY.value,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
            "settings": {},
            "metrics": {
                "member_count": 0,
                "ai_agent_count": 0,
                "tasks_completed": 0
            }
        }

        self.teams[team_id] = team
        self.members[team_id] = {}

        # Add owner if provided
        if owner_id:
            owner = TeamMember(
                id=owner_id,
                name="Team Owner",
                email="owner@example.com",
                member_type=MemberType.HUMAN,
                role=TeamRole.OWNER,
                joined_at=datetime.utcnow().isoformat()
            )
            await self.add_member(team_id, owner)

        return team

    async def add_member(
        self,
        team_id: str,
        member: TeamMember
    ) -> Dict[str, Any]:
        """Add a member to the team."""
        if team_id not in self.teams:
            raise ValueError(f"Team {team_id} not found")

        member.joined_at = datetime.utcnow().isoformat()
        self.members[team_id][member.id] = member

        # Update team metrics
        team = self.teams[team_id]
        team["metrics"]["member_count"] = len(self.members[team_id])
        team["metrics"]["ai_agent_count"] = sum(
            1 for m in self.members[team_id].values()
            if m.member_type == MemberType.AI_AGENT
        )
        team["updated_at"] = datetime.utcnow().isoformat()

        return {
            "id": member.id,
            "name": member.name,
            "role": member.role.value,
            "member_type": member.member_type.value
        }

    async def remove_member(
        self,
        team_id: str,
        member_id: str
    ) -> bool:
        """Remove a member from the team."""
        if team_id not in self.teams:
            raise ValueError(f"Team {team_id} not found")

        if member_id not in self.members[team_id]:
            raise ValueError(f"Member {member_id} not found in team")

        member = self.members[team_id][member_id]
        if member.role == TeamRole.OWNER:
            raise ValueError("Cannot remove team owner")

        del self.members[team_id][member_id]

        # Update metrics
        team = self.teams[team_id]
        team["metrics"]["member_count"] = len(self.members[team_id])
        team["metrics"]["ai_agent_count"] = sum(
            1 for m in self.members[team_id].values()
            if m.member_type == MemberType.AI_AGENT
        )

        return True

    async def assign_role(
        self,
        team_id: str,
        member_id: str,
        new_role: TeamRole
    ) -> Dict[str, Any]:
        """Assign a new role to a team member."""
        if team_id not in self.teams:
            raise ValueError(f"Team {team_id} not found")

        if member_id not in self.members[team_id]:
            raise ValueError(f"Member {member_id} not found in team")

        member = self.members[team_id][member_id]

        # Cannot change owner role
        if member.role == TeamRole.OWNER:
            raise ValueError("Cannot change owner role")

        # Cannot promote to owner
        if new_role == TeamRole.OWNER:
            raise ValueError("Cannot promote to owner role")

        old_role = member.role
        member.role = new_role

        return {
            "member_id": member_id,
            "old_role": old_role.value,
            "new_role": new_role.value
        }

    async def get_team_members(
        self,
        team_id: str
    ) -> List[Dict[str, Any]]:
        """Get all team members."""
        if team_id not in self.teams:
            raise ValueError(f"Team {team_id} not found")

        return [
            {
                "id": m.id,
                "name": m.name,
                "email": m.email,
                "role": m.role.value,
                "member_type": m.member_type.value,
                "skills": m.skills,
                "joined_at": m.joined_at
            }
            for m in self.members[team_id].values()
        ]

    async def apply_blueprint(
        self,
        team_id: str,
        blueprint_id: str
    ) -> Dict[str, Any]:
        """Apply a blueprint to configure the team."""
        if team_id not in self.teams:
            raise ValueError(f"Team {team_id} not found")

        if blueprint_id not in self.blueprints:
            raise ValueError(f"Blueprint {blueprint_id} not found")

        blueprint = self.blueprints[blueprint_id]
        team = self.teams[team_id]

        # Update team configuration
        team["blueprint_id"] = blueprint_id
        team["collaboration_mode"] = blueprint.collaboration_mode.value
        team["settings"]["required_skills"] = blueprint.required_skills
        team["settings"]["workflows"] = blueprint.workflows

        # Add AI agents from blueprint
        for ai_config in blueprint.ai_agents:
            ai_member = TeamMember(
                id=f"ai_{uuid.uuid4().hex[:8]}",
                name=ai_config["name"],
                email=None,
                member_type=MemberType.AI_AGENT,
                role=TeamRole.AI_AGENT,
                skills=[ai_config["type"]],
                ai_config=ai_config
            )
            await self.add_member(team_id, ai_member)

        team["status"] = TeamStatus.ACTIVE.value
        team["updated_at"] = datetime.utcnow().isoformat()

        return {
            "team_id": team_id,
            "blueprint_applied": blueprint_id,
            "collaboration_mode": team["collaboration_mode"],
            "ai_agents_added": len(blueprint.ai_agents)
        }

    async def validate_blueprint(
        self,
        team_id: str
    ) -> Dict[str, Any]:
        """Validate team against its blueprint requirements."""
        if team_id not in self.teams:
            raise ValueError(f"Team {team_id} not found")

        team = self.teams[team_id]
        validation = {
            "valid": True,
            "errors": [],
            "warnings": [],
            "coverage": {}
        }

        if not team.get("blueprint_id"):
            validation["valid"] = False
            validation["errors"].append("No blueprint applied")
            return validation

        blueprint = self.blueprints.get(team["blueprint_id"])
        if not blueprint:
            validation["valid"] = False
            validation["errors"].append("Blueprint not found")
            return validation

        # Check required skills coverage
        team_skills: Set[str] = set()
        for member in self.members[team_id].values():
            team_skills.update(member.skills)

        missing_skills = set(blueprint.required_skills) - team_skills
        if missing_skills:
            validation["warnings"].append(f"Missing skills: {missing_skills}")

        validation["coverage"]["skills"] = len(team_skills & set(blueprint.required_skills)) / len(blueprint.required_skills) if blueprint.required_skills else 1.0

        # Check role requirements
        role_counts = {}
        for member in self.members[team_id].values():
            role_counts[member.role.value] = role_counts.get(member.role.value, 0) + 1

        for role_req in blueprint.default_roles:
            role = role_req["role"]
            expected = role_req["count"]
            actual = role_counts.get(role, 0)
            if actual < expected:
                validation["warnings"].append(
                    f"Insufficient {role}: {actual}/{expected}"
                )

        # Check AI agents
        expected_ai = len(blueprint.ai_agents)
        actual_ai = team["metrics"]["ai_agent_count"]
        if actual_ai < expected_ai:
            validation["warnings"].append(
                f"Missing AI agents: {actual_ai}/{expected_ai}"
            )

        validation["coverage"]["ai_agents"] = actual_ai / expected_ai if expected_ai else 1.0

        return validation

    async def activate_team(self, team_id: str) -> Dict[str, Any]:
        """Activate a team for operations."""
        if team_id not in self.teams:
            raise ValueError(f"Team {team_id} not found")

        team = self.teams[team_id]

        if len(self.members[team_id]) == 0:
            raise ValueError("Cannot activate team with no members")

        team["status"] = TeamStatus.ACTIVE.value
        team["updated_at"] = datetime.utcnow().isoformat()

        return team

    async def suspend_team(self, team_id: str, reason: str) -> Dict[str, Any]:
        """Suspend team operations."""
        if team_id not in self.teams:
            raise ValueError(f"Team {team_id} not found")

        team = self.teams[team_id]
        team["status"] = TeamStatus.SUSPENDED.value
        team["settings"]["suspension_reason"] = reason
        team["updated_at"] = datetime.utcnow().isoformat()

        return team

    async def archive_team(self, team_id: str) -> Dict[str, Any]:
        """Archive a team."""
        if team_id not in self.teams:
            raise ValueError(f"Team {team_id} not found")

        team = self.teams[team_id]
        team["status"] = TeamStatus.ARCHIVED.value
        team["updated_at"] = datetime.utcnow().isoformat()

        return team

    async def send_invitation(
        self,
        team_id: str,
        email: str,
        role: TeamRole
    ) -> Dict[str, Any]:
        """Send team invitation."""
        if team_id not in self.teams:
            raise ValueError(f"Team {team_id} not found")

        invitation_id = f"inv_{uuid.uuid4().hex[:12]}"

        invitation = {
            "id": invitation_id,
            "team_id": team_id,
            "email": email,
            "role": role.value,
            "status": "pending",
            "created_at": datetime.utcnow().isoformat(),
            "expires_at": (datetime.utcnow() + timedelta(days=7)).isoformat()
        }

        self.invitations[invitation_id] = invitation
        return invitation

    async def accept_invitation(
        self,
        invitation_id: str,
        user_name: str
    ) -> Dict[str, Any]:
        """Accept team invitation."""
        if invitation_id not in self.invitations:
            raise ValueError(f"Invitation {invitation_id} not found")

        invitation = self.invitations[invitation_id]

        if invitation["status"] != "pending":
            raise ValueError(f"Invitation already {invitation['status']}")

        # Check expiration
        expires_at = datetime.fromisoformat(invitation["expires_at"])
        if datetime.utcnow() > expires_at:
            invitation["status"] = "expired"
            raise ValueError("Invitation has expired")

        # Add member to team
        member = TeamMember(
            id=f"user_{uuid.uuid4().hex[:8]}",
            name=user_name,
            email=invitation["email"],
            member_type=MemberType.HUMAN,
            role=TeamRole(invitation["role"])
        )

        await self.add_member(invitation["team_id"], member)
        invitation["status"] = "accepted"

        return {
            "invitation_id": invitation_id,
            "team_id": invitation["team_id"],
            "member_id": member.id
        }


class CollaborationSimulator:
    """Simulates human-AI collaboration scenarios."""

    def __init__(self, team_sim: TeamSimulator):
        self.team_sim = team_sim
        self.tasks: Dict[str, Dict[str, Any]] = {}
        self.interactions: List[Dict[str, Any]] = []

    async def create_task(
        self,
        team_id: str,
        title: str,
        task_type: str,
        assigned_to: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create a collaborative task."""
        task_id = f"task_{uuid.uuid4().hex[:12]}"

        task = {
            "id": task_id,
            "team_id": team_id,
            "title": title,
            "type": task_type,
            "assigned_to": assigned_to,
            "status": "open",
            "ai_suggestions": [],
            "human_decisions": [],
            "created_at": datetime.utcnow().isoformat()
        }

        self.tasks[task_id] = task
        return task

    async def ai_suggest(
        self,
        task_id: str,
        ai_agent_id: str,
        suggestion: Dict[str, Any]
    ) -> Dict[str, Any]:
        """AI agent provides a suggestion."""
        if task_id not in self.tasks:
            raise ValueError(f"Task {task_id} not found")

        task = self.tasks[task_id]
        suggestion_record = {
            "id": f"sug_{uuid.uuid4().hex[:8]}",
            "agent_id": ai_agent_id,
            "content": suggestion,
            "status": "pending",
            "created_at": datetime.utcnow().isoformat()
        }

        task["ai_suggestions"].append(suggestion_record)

        self.interactions.append({
            "type": "ai_suggestion",
            "task_id": task_id,
            "agent_id": ai_agent_id,
            "timestamp": datetime.utcnow().isoformat()
        })

        return suggestion_record

    async def human_review(
        self,
        task_id: str,
        suggestion_id: str,
        user_id: str,
        decision: str,  # "approve", "reject", "modify"
        modifications: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Human reviews AI suggestion."""
        if task_id not in self.tasks:
            raise ValueError(f"Task {task_id} not found")

        task = self.tasks[task_id]

        # Find the suggestion
        suggestion = None
        for sug in task["ai_suggestions"]:
            if sug["id"] == suggestion_id:
                suggestion = sug
                break

        if not suggestion:
            raise ValueError(f"Suggestion {suggestion_id} not found")

        suggestion["status"] = decision
        if modifications:
            suggestion["modifications"] = modifications

        decision_record = {
            "id": f"dec_{uuid.uuid4().hex[:8]}",
            "user_id": user_id,
            "suggestion_id": suggestion_id,
            "decision": decision,
            "modifications": modifications,
            "timestamp": datetime.utcnow().isoformat()
        }

        task["human_decisions"].append(decision_record)

        self.interactions.append({
            "type": "human_review",
            "task_id": task_id,
            "user_id": user_id,
            "decision": decision,
            "timestamp": datetime.utcnow().isoformat()
        })

        return decision_record

    async def get_collaboration_metrics(
        self,
        team_id: str
    ) -> Dict[str, Any]:
        """Get collaboration metrics for a team."""
        team_tasks = [t for t in self.tasks.values() if t["team_id"] == team_id]

        total_suggestions = sum(len(t["ai_suggestions"]) for t in team_tasks)
        total_decisions = sum(len(t["human_decisions"]) for t in team_tasks)

        approved = sum(
            1 for t in team_tasks
            for sug in t["ai_suggestions"]
            if sug["status"] == "approve"
        )

        return {
            "total_tasks": len(team_tasks),
            "total_ai_suggestions": total_suggestions,
            "total_human_decisions": total_decisions,
            "approval_rate": approved / total_suggestions if total_suggestions else 0,
            "collaboration_index": (total_suggestions + total_decisions) / len(team_tasks) if team_tasks else 0
        }


class TestTeamLifecycle:
    """E2E tests for team create -> add members -> assign roles flow."""

    @pytest.fixture
    def team_sim(self):
        return TeamSimulator()

    @pytest.mark.asyncio
    async def test_complete_team_lifecycle(self, team_sim):
        """Test full team lifecycle: create -> add members -> assign roles."""
        # Step 1: Create team with owner
        team = await team_sim.create_team(
            name="Engineering Team",
            description="Core engineering team",
            owner_id="owner_123"
        )
        assert team["status"] == TeamStatus.DRAFT.value
        assert team["metrics"]["member_count"] == 1

        # Step 2: Add members
        dev1 = TeamMember(
            id="dev_1",
            name="Developer One",
            email="dev1@example.com",
            member_type=MemberType.HUMAN,
            role=TeamRole.MEMBER,
            skills=["python", "javascript"]
        )
        await team_sim.add_member(team["id"], dev1)

        dev2 = TeamMember(
            id="dev_2",
            name="Developer Two",
            email="dev2@example.com",
            member_type=MemberType.HUMAN,
            role=TeamRole.MEMBER,
            skills=["java", "kotlin"]
        )
        await team_sim.add_member(team["id"], dev2)

        assert team["metrics"]["member_count"] == 3

        # Step 3: Assign roles
        role_change = await team_sim.assign_role(
            team["id"],
            "dev_1",
            TeamRole.ADMIN
        )
        assert role_change["old_role"] == TeamRole.MEMBER.value
        assert role_change["new_role"] == TeamRole.ADMIN.value

        # Step 4: Activate team
        activated = await team_sim.activate_team(team["id"])
        assert activated["status"] == TeamStatus.ACTIVE.value

        # Verify final state
        members = await team_sim.get_team_members(team["id"])
        assert len(members) == 3

        admin_count = sum(1 for m in members if m["role"] == TeamRole.ADMIN.value)
        assert admin_count == 1

    @pytest.mark.asyncio
    async def test_add_ai_agent_to_team(self, team_sim):
        """Test adding AI agents to team."""
        team = await team_sim.create_team(
            name="AI-Assisted Team",
            owner_id="owner_1"
        )

        # Add AI agent
        ai_agent = TeamMember(
            id="ai_1",
            name="Code Review AI",
            email=None,
            member_type=MemberType.AI_AGENT,
            role=TeamRole.AI_AGENT,
            skills=["code_review", "static_analysis"],
            ai_config={"model": "gpt-4", "temperature": 0.3}
        )
        await team_sim.add_member(team["id"], ai_agent)

        assert team["metrics"]["ai_agent_count"] == 1

        members = await team_sim.get_team_members(team["id"])
        ai_members = [m for m in members if m["member_type"] == MemberType.AI_AGENT.value]
        assert len(ai_members) == 1

    @pytest.mark.asyncio
    async def test_remove_member(self, team_sim):
        """Test removing a member from team."""
        team = await team_sim.create_team(
            name="Test Team",
            owner_id="owner_1"
        )

        member = TeamMember(
            id="member_1",
            name="Removable Member",
            email="member@example.com",
            member_type=MemberType.HUMAN,
            role=TeamRole.MEMBER
        )
        await team_sim.add_member(team["id"], member)
        assert team["metrics"]["member_count"] == 2

        result = await team_sim.remove_member(team["id"], "member_1")
        assert result is True
        assert team["metrics"]["member_count"] == 1

    @pytest.mark.asyncio
    async def test_cannot_remove_owner(self, team_sim):
        """Test that owner cannot be removed."""
        team = await team_sim.create_team(
            name="Test Team",
            owner_id="owner_1"
        )

        with pytest.raises(ValueError, match="Cannot remove team owner"):
            await team_sim.remove_member(team["id"], "owner_1")

    @pytest.mark.asyncio
    async def test_cannot_change_owner_role(self, team_sim):
        """Test that owner role cannot be changed."""
        team = await team_sim.create_team(
            name="Test Team",
            owner_id="owner_1"
        )

        with pytest.raises(ValueError, match="Cannot change owner role"):
            await team_sim.assign_role(team["id"], "owner_1", TeamRole.ADMIN)

    @pytest.mark.asyncio
    async def test_team_invitation_flow(self, team_sim):
        """Test team invitation workflow."""
        team = await team_sim.create_team(
            name="Invite Test Team",
            owner_id="owner_1"
        )

        # Send invitation
        invitation = await team_sim.send_invitation(
            team["id"],
            "newmember@example.com",
            TeamRole.MEMBER
        )
        assert invitation["status"] == "pending"
        assert invitation["role"] == TeamRole.MEMBER.value

        # Accept invitation
        result = await team_sim.accept_invitation(
            invitation["id"],
            "New Member"
        )
        assert result["team_id"] == team["id"]

        members = await team_sim.get_team_members(team["id"])
        assert len(members) == 2

    @pytest.mark.asyncio
    async def test_team_suspend_and_archive(self, team_sim):
        """Test team suspension and archival."""
        team = await team_sim.create_team(
            name="Lifecycle Team",
            owner_id="owner_1"
        )

        await team_sim.activate_team(team["id"])
        assert team["status"] == TeamStatus.ACTIVE.value

        # Suspend
        suspended = await team_sim.suspend_team(
            team["id"],
            "Budget constraints"
        )
        assert suspended["status"] == TeamStatus.SUSPENDED.value
        assert suspended["settings"]["suspension_reason"] == "Budget constraints"

        # Archive
        archived = await team_sim.archive_team(team["id"])
        assert archived["status"] == TeamStatus.ARCHIVED.value


class TestBlueprintApplication:
    """E2E tests for blueprint apply and validation."""

    @pytest.fixture
    def team_sim(self):
        return TeamSimulator()

    @pytest.mark.asyncio
    async def test_apply_development_blueprint(self, team_sim):
        """Test applying development team blueprint."""
        team = await team_sim.create_team(
            name="Dev Team",
            owner_id="owner_1"
        )

        result = await team_sim.apply_blueprint(team["id"], "development_team")

        assert result["blueprint_applied"] == "development_team"
        assert result["ai_agents_added"] == 2
        assert team["collaboration_mode"] == CollaborationMode.AI_ASSISTED.value
        assert team["status"] == TeamStatus.ACTIVE.value

    @pytest.mark.asyncio
    async def test_apply_research_blueprint(self, team_sim):
        """Test applying research team blueprint."""
        team = await team_sim.create_team(
            name="Research Team",
            owner_id="owner_1"
        )

        result = await team_sim.apply_blueprint(team["id"], "research_team")

        assert result["ai_agents_added"] == 3
        assert team["collaboration_mode"] == CollaborationMode.AI_LED.value

    @pytest.mark.asyncio
    async def test_validate_blueprint_compliance(self, team_sim):
        """Test validating team against blueprint requirements."""
        team = await team_sim.create_team(
            name="Validation Team",
            owner_id="owner_1"
        )

        await team_sim.apply_blueprint(team["id"], "development_team")

        # Add member with required skills
        dev = TeamMember(
            id="dev_1",
            name="Developer",
            email="dev@example.com",
            member_type=MemberType.HUMAN,
            role=TeamRole.MEMBER,
            skills=["coding", "testing", "code_review"]
        )
        await team_sim.add_member(team["id"], dev)

        validation = await team_sim.validate_blueprint(team["id"])

        assert validation["valid"] is True
        assert validation["coverage"]["skills"] == 1.0

    @pytest.mark.asyncio
    async def test_validate_incomplete_team(self, team_sim):
        """Test validation shows gaps for incomplete team."""
        team = await team_sim.create_team(
            name="Incomplete Team",
            owner_id="owner_1"
        )

        # Apply blueprint but don't add required members
        await team_sim.apply_blueprint(team["id"], "development_team")

        validation = await team_sim.validate_blueprint(team["id"])

        # Should have warnings about missing roles/skills
        assert len(validation["warnings"]) > 0

    @pytest.mark.asyncio
    async def test_blueprint_not_found(self, team_sim):
        """Test applying non-existent blueprint fails."""
        team = await team_sim.create_team(
            name="Test Team",
            owner_id="owner_1"
        )

        with pytest.raises(ValueError, match="Blueprint.*not found"):
            await team_sim.apply_blueprint(team["id"], "nonexistent_blueprint")

    @pytest.mark.asyncio
    async def test_validate_team_without_blueprint(self, team_sim):
        """Test validation fails for team without blueprint."""
        team = await team_sim.create_team(
            name="No Blueprint Team",
            owner_id="owner_1"
        )

        validation = await team_sim.validate_blueprint(team["id"])

        assert validation["valid"] is False
        assert any("No blueprint" in err for err in validation["errors"])


class TestHumanAICollaboration:
    """E2E tests for human-AI collaboration scenarios."""

    @pytest.fixture
    def team_sim(self):
        return TeamSimulator()

    @pytest.fixture
    def collab_sim(self, team_sim):
        return CollaborationSimulator(team_sim)

    @pytest.mark.asyncio
    async def test_ai_suggestion_approval_flow(self, team_sim, collab_sim):
        """Test AI suggestion and human approval flow."""
        team = await team_sim.create_team(
            name="Collab Team",
            owner_id="owner_1"
        )

        # Add AI agent and human
        ai_agent = TeamMember(
            id="ai_1",
            name="Suggestion AI",
            email=None,
            member_type=MemberType.AI_AGENT,
            role=TeamRole.AI_AGENT
        )
        await team_sim.add_member(team["id"], ai_agent)

        human = TeamMember(
            id="human_1",
            name="Reviewer",
            email="reviewer@example.com",
            member_type=MemberType.HUMAN,
            role=TeamRole.MEMBER
        )
        await team_sim.add_member(team["id"], human)

        # Create task
        task = await collab_sim.create_task(
            team["id"],
            "Code Review Task",
            "code_review"
        )

        # AI makes suggestion
        suggestion = await collab_sim.ai_suggest(
            task["id"],
            "ai_1",
            {"action": "refactor", "target": "function_x", "reason": "complexity"}
        )
        assert suggestion["status"] == "pending"

        # Human approves
        decision = await collab_sim.human_review(
            task["id"],
            suggestion["id"],
            "human_1",
            "approve"
        )
        assert decision["decision"] == "approve"

    @pytest.mark.asyncio
    async def test_ai_suggestion_rejection(self, team_sim, collab_sim):
        """Test AI suggestion rejection by human."""
        team = await team_sim.create_team(
            name="Reject Test Team",
            owner_id="owner_1"
        )

        task = await collab_sim.create_task(
            team["id"],
            "Test Task",
            "analysis"
        )

        suggestion = await collab_sim.ai_suggest(
            task["id"],
            "ai_1",
            {"recommendation": "delete_file", "file": "important.py"}
        )

        decision = await collab_sim.human_review(
            task["id"],
            suggestion["id"],
            "human_1",
            "reject"
        )

        assert decision["decision"] == "reject"

        # Verify in task
        task_data = collab_sim.tasks[task["id"]]
        assert task_data["ai_suggestions"][0]["status"] == "reject"

    @pytest.mark.asyncio
    async def test_ai_suggestion_modification(self, team_sim, collab_sim):
        """Test human modifying AI suggestion."""
        team = await team_sim.create_team(
            name="Modify Test Team",
            owner_id="owner_1"
        )

        task = await collab_sim.create_task(
            team["id"],
            "Design Task",
            "design"
        )

        suggestion = await collab_sim.ai_suggest(
            task["id"],
            "ai_1",
            {"component": "Button", "style": "primary", "size": "large"}
        )

        decision = await collab_sim.human_review(
            task["id"],
            suggestion["id"],
            "human_1",
            "modify",
            modifications={"size": "medium", "color": "blue"}
        )

        assert decision["decision"] == "modify"
        assert decision["modifications"]["size"] == "medium"

    @pytest.mark.asyncio
    async def test_collaboration_metrics(self, team_sim, collab_sim):
        """Test collaboration metrics calculation."""
        team = await team_sim.create_team(
            name="Metrics Team",
            owner_id="owner_1"
        )

        # Create multiple tasks with suggestions
        for i in range(3):
            task = await collab_sim.create_task(
                team["id"],
                f"Task {i}",
                "review"
            )

            # AI suggestions
            for j in range(2):
                suggestion = await collab_sim.ai_suggest(
                    task["id"],
                    f"ai_{j}",
                    {"action": f"action_{j}"}
                )

                # Human reviews (approve half)
                decision = "approve" if j == 0 else "reject"
                await collab_sim.human_review(
                    task["id"],
                    suggestion["id"],
                    "human_1",
                    decision
                )

        metrics = await collab_sim.get_collaboration_metrics(team["id"])

        assert metrics["total_tasks"] == 3
        assert metrics["total_ai_suggestions"] == 6
        assert metrics["total_human_decisions"] == 6
        assert metrics["approval_rate"] == 0.5

    @pytest.mark.asyncio
    async def test_multiple_ai_agents_collaboration(self, team_sim, collab_sim):
        """Test multiple AI agents working together."""
        team = await team_sim.create_team(
            name="Multi-AI Team",
            owner_id="owner_1"
        )

        # Add multiple AI agents
        for i in range(3):
            ai_agent = TeamMember(
                id=f"ai_{i}",
                name=f"AI Agent {i}",
                email=None,
                member_type=MemberType.AI_AGENT,
                role=TeamRole.AI_AGENT,
                skills=[["analysis", "synthesis", "evaluation"][i]]
            )
            await team_sim.add_member(team["id"], ai_agent)

        task = await collab_sim.create_task(
            team["id"],
            "Complex Analysis",
            "analysis"
        )

        # Each AI provides suggestion
        for i in range(3):
            await collab_sim.ai_suggest(
                task["id"],
                f"ai_{i}",
                {"phase": ["analyze", "synthesize", "evaluate"][i], "result": f"output_{i}"}
            )

        task_data = collab_sim.tasks[task["id"]]
        assert len(task_data["ai_suggestions"]) == 3

    @pytest.mark.asyncio
    async def test_hybrid_member_workflow(self, team_sim, collab_sim):
        """Test workflow with hybrid (human + AI assistant) member."""
        team = await team_sim.create_team(
            name="Hybrid Team",
            owner_id="owner_1"
        )

        # Add hybrid member
        hybrid_member = TeamMember(
            id="hybrid_1",
            name="Augmented Developer",
            email="hybrid@example.com",
            member_type=MemberType.HYBRID,
            role=TeamRole.MEMBER,
            ai_config={"assistant": "copilot_v2"}
        )
        await team_sim.add_member(team["id"], hybrid_member)

        members = await team_sim.get_team_members(team["id"])
        hybrid_members = [m for m in members if m["member_type"] == MemberType.HYBRID.value]
        assert len(hybrid_members) == 1


class TestTeamErrorHandling:
    """E2E tests for team management error scenarios."""

    @pytest.fixture
    def team_sim(self):
        return TeamSimulator()

    @pytest.mark.asyncio
    async def test_team_not_found(self, team_sim):
        """Test operations on non-existent team."""
        with pytest.raises(ValueError, match="Team.*not found"):
            await team_sim.add_member(
                "nonexistent_team",
                TeamMember(
                    id="m1",
                    name="Test",
                    email=None,
                    member_type=MemberType.HUMAN,
                    role=TeamRole.MEMBER
                )
            )

    @pytest.mark.asyncio
    async def test_member_not_found(self, team_sim):
        """Test operations on non-existent member."""
        team = await team_sim.create_team(
            name="Test Team",
            owner_id="owner_1"
        )

        with pytest.raises(ValueError, match="Member.*not found"):
            await team_sim.assign_role(
                team["id"],
                "nonexistent_member",
                TeamRole.ADMIN
            )

    @pytest.mark.asyncio
    async def test_cannot_activate_empty_team(self, team_sim):
        """Test that empty team cannot be activated."""
        team = await team_sim.create_team(
            name="Empty Team"
            # No owner_id, so no members
        )

        with pytest.raises(ValueError, match="no members"):
            await team_sim.activate_team(team["id"])

    @pytest.mark.asyncio
    async def test_expired_invitation(self, team_sim):
        """Test handling expired invitation."""
        team = await team_sim.create_team(
            name="Invite Team",
            owner_id="owner_1"
        )

        invitation = await team_sim.send_invitation(
            team["id"],
            "test@example.com",
            TeamRole.MEMBER
        )

        # Manually expire the invitation
        team_sim.invitations[invitation["id"]]["expires_at"] = (
            datetime.utcnow() - timedelta(days=1)
        ).isoformat()

        with pytest.raises(ValueError, match="expired"):
            await team_sim.accept_invitation(invitation["id"], "Test User")

    @pytest.mark.asyncio
    async def test_cannot_promote_to_owner(self, team_sim):
        """Test that members cannot be promoted to owner."""
        team = await team_sim.create_team(
            name="Test Team",
            owner_id="owner_1"
        )

        member = TeamMember(
            id="member_1",
            name="Member",
            email="m@example.com",
            member_type=MemberType.HUMAN,
            role=TeamRole.MEMBER
        )
        await team_sim.add_member(team["id"], member)

        with pytest.raises(ValueError, match="Cannot promote to owner"):
            await team_sim.assign_role(team["id"], "member_1", TeamRole.OWNER)
