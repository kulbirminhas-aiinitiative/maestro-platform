#!/usr/bin/env python3
"""
Role Management System - Role-Based Assignment Abstraction

Enables role abstraction where tasks are assigned to roles (e.g., "Security Auditor")
not specific agents. Agents can be dynamically assigned to fill roles, enabling
seamless handoffs and team flexibility.

Key Concepts:
- Role: Abstract position (e.g., "Security Auditor", "DBA Specialist")
- Persona: Skill set (e.g., "security_specialist", "backend_developer")
- Agent: Individual instance (e.g., "security_specialist_team_123")

Roles can be filled by different agents over time, and tasks remain assigned
to roles rather than individuals.
"""

import sys
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime
import uuid

# Add parent directories to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from persistence.state_manager import StateManager
from persistence.models import RoleAssignment
from sqlalchemy import select, update, and_


class RoleManager:
    """
    Manages role-based assignments for teams

    Provides:
    - Role definition and management
    - Agent-to-role assignment
    - Role reassignment (seamless handoffs)
    - Role-based task routing
    """

    def __init__(self, state_manager: StateManager):
        self.state = state_manager

    # =========================================================================
    # Role Definition and Management
    # =========================================================================

    async def create_role(
        self,
        team_id: str,
        role_id: str,
        role_description: str,
        is_required: bool = True,
        priority: int = 5,
        created_by: str = "system"
    ) -> Dict[str, Any]:
        """
        Create a new role for a team

        Args:
            team_id: Team identifier
            role_id: Role identifier (e.g., "Security Auditor", "DBA Specialist")
            role_description: Human-readable description
            is_required: Whether this role is required for the project
            priority: Role priority (higher = more critical)
            created_by: Who created the role

        Returns:
            Role info
        """
        role = RoleAssignment(
            team_id=team_id,
            role_id=role_id,
            role_description=role_description,
            is_required=is_required,
            is_active=True,
            priority=priority,
            extra_metadata={"created_by": created_by}
        )

        async with self.state.db.session() as session:
            session.add(role)
            await session.commit()
            await session.refresh(role)

        print(f"  ✓ Created role: {role_id}")

        return role.to_dict()

    async def get_role(
        self,
        team_id: str,
        role_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get role information"""
        async with self.state.db.session() as session:
            result = await session.execute(
                select(RoleAssignment).where(
                    and_(
                        RoleAssignment.team_id == team_id,
                        RoleAssignment.role_id == role_id
                    )
                )
            )
            role = result.scalar_one_or_none()

            return role.to_dict() if role else None

    async def get_all_roles(
        self,
        team_id: str,
        active_only: bool = True
    ) -> List[Dict[str, Any]]:
        """Get all roles for a team"""
        async with self.state.db.session() as session:
            query = select(RoleAssignment).where(RoleAssignment.team_id == team_id)

            if active_only:
                query = query.where(RoleAssignment.is_active == True)

            result = await session.execute(query)
            roles = result.scalars().all()

            return [role.to_dict() for role in roles]

    async def deactivate_role(
        self,
        team_id: str,
        role_id: str,
        reason: str = "Role no longer needed"
    ) -> Dict[str, Any]:
        """Deactivate a role (mark as inactive)"""
        async with self.state.db.session() as session:
            result = await session.execute(
                select(RoleAssignment).where(
                    and_(
                        RoleAssignment.team_id == team_id,
                        RoleAssignment.role_id == role_id
                    )
                )
            )
            role = result.scalar_one_or_none()

            if not role:
                raise ValueError(f"Role {role_id} not found in team {team_id}")

            role.is_active = False
            role.extra_metadata = role.extra_metadata or {}
            role.extra_metadata['deactivation_reason'] = reason
            role.extra_metadata['deactivated_at'] = datetime.utcnow().isoformat()

            await session.commit()
            await session.refresh(role)

            print(f"  ✓ Deactivated role: {role_id}")
            return role.to_dict()

    # =========================================================================
    # Agent-to-Role Assignment
    # =========================================================================

    async def assign_agent_to_role(
        self,
        team_id: str,
        role_id: str,
        agent_id: str,
        assigned_by: str,
        reason: str = None
    ) -> Dict[str, Any]:
        """
        Assign an agent to fill a role

        This is the key operation for role abstraction.
        Tasks assigned to this role will now route to this agent.

        Args:
            team_id: Team identifier
            role_id: Role to fill
            agent_id: Agent to assign
            assigned_by: Who made the assignment
            reason: Why this assignment was made

        Returns:
            Updated role info
        """
        async with self.state.db.session() as session:
            result = await session.execute(
                select(RoleAssignment).where(
                    and_(
                        RoleAssignment.team_id == team_id,
                        RoleAssignment.role_id == role_id
                    )
                )
            )
            role = result.scalar_one_or_none()

            if not role:
                raise ValueError(f"Role {role_id} not found in team {team_id}")

            # Use the model method to record assignment
            role.assign_agent(agent_id, assigned_by, reason)

            await session.commit()
            await session.refresh(role)

        # Publish event
        await self.state.redis.publish_event(
            f"team:{team_id}:events:role.assigned",
            "role.assigned",
            {
                "role_id": role_id,
                "agent_id": agent_id,
                "assigned_by": assigned_by
            }
        )

        print(f"  ✓ Assigned {agent_id} to role {role_id}")

        return role.to_dict()

    async def reassign_role(
        self,
        team_id: str,
        role_id: str,
        new_agent_id: str,
        assigned_by: str,
        reason: str = "Role reassignment"
    ) -> Dict[str, Any]:
        """
        Reassign a role to a different agent (seamless handoff)

        This is the key operation for dynamic team management.
        Tasks remain assigned to the role, but now route to the new agent.

        Args:
            team_id: Team identifier
            role_id: Role to reassign
            new_agent_id: New agent to fill the role
            assigned_by: Who made the reassignment
            reason: Why the reassignment was made

        Returns:
            Updated role info
        """
        # Get current assignment
        current_role = await self.get_role(team_id, role_id)

        if not current_role:
            raise ValueError(f"Role {role_id} not found")

        old_agent_id = current_role.get('current_agent_id')

        # Assign new agent
        result = await self.assign_agent_to_role(
            team_id=team_id,
            role_id=role_id,
            agent_id=new_agent_id,
            assigned_by=assigned_by,
            reason=reason
        )

        print(f"  🔄 Reassigned role {role_id}: {old_agent_id} → {new_agent_id}")

        return result

    async def unassign_role(
        self,
        team_id: str,
        role_id: str,
        reason: str = "Agent removed from role"
    ) -> Dict[str, Any]:
        """Remove agent from role (leave role unfilled)"""
        async with self.state.db.session() as session:
            result = await session.execute(
                select(RoleAssignment).where(
                    and_(
                        RoleAssignment.team_id == team_id,
                        RoleAssignment.role_id == role_id
                    )
                )
            )
            role = result.scalar_one_or_none()

            if not role:
                raise ValueError(f"Role {role_id} not found")

            old_agent = role.current_agent_id

            # Record in history
            if not isinstance(role.assignment_history, list):
                role.assignment_history = []

            role.assignment_history.append({
                "from_agent": old_agent,
                "to_agent": None,
                "assigned_by": "system",
                "reason": reason,
                "timestamp": datetime.utcnow().isoformat()
            })

            role.current_agent_id = None
            role.assigned_at = None

            await session.commit()
            await session.refresh(role)

        print(f"  ✓ Unassigned {old_agent} from role {role_id}")

        return role.to_dict()

    # =========================================================================
    # Role-Based Task Routing
    # =========================================================================

    async def get_agent_for_role(
        self,
        team_id: str,
        role_id: str
    ) -> Optional[str]:
        """
        Get the current agent filling a role

        This is used to route tasks assigned to roles to specific agents.

        Args:
            team_id: Team identifier
            role_id: Role identifier

        Returns:
            Agent ID if role is filled, None otherwise
        """
        role = await self.get_role(team_id, role_id)

        if not role:
            return None

        return role.get('current_agent_id')

    async def get_roles_for_agent(
        self,
        team_id: str,
        agent_id: str
    ) -> List[str]:
        """Get all roles filled by an agent"""
        async with self.state.db.session() as session:
            result = await session.execute(
                select(RoleAssignment).where(
                    and_(
                        RoleAssignment.team_id == team_id,
                        RoleAssignment.current_agent_id == agent_id,
                        RoleAssignment.is_active == True
                    )
                )
            )
            roles = result.scalars().all()

            return [role.role_id for role in roles]

    async def get_unfilled_roles(
        self,
        team_id: str,
        required_only: bool = True
    ) -> List[Dict[str, Any]]:
        """Get roles that don't have an agent assigned"""
        async with self.state.db.session() as session:
            query = select(RoleAssignment).where(
                and_(
                    RoleAssignment.team_id == team_id,
                    RoleAssignment.current_agent_id.is_(None),
                    RoleAssignment.is_active == True
                )
            )

            if required_only:
                query = query.where(RoleAssignment.is_required == True)

            result = await session.execute(query)
            roles = result.scalars().all()

            return [role.to_dict() for role in roles]

    # =========================================================================
    # Predefined SDLC Roles
    # =========================================================================

    @staticmethod
    def get_standard_sdlc_roles() -> List[Dict[str, Any]]:
        """
        Get standard SDLC role definitions

        These are the common roles used in software development teams.
        Each role can be filled by appropriate personas.
        """
        return [
            {
                "role_id": "Product Owner",
                "description": "Defines requirements and priorities",
                "suitable_personas": ["requirement_analyst"],
                "priority": 10,
                "is_required": True
            },
            {
                "role_id": "Tech Lead",
                "description": "Technical leadership and architecture decisions",
                "suitable_personas": ["solution_architect"],
                "priority": 10,
                "is_required": True
            },
            {
                "role_id": "Security Auditor",
                "description": "Security review and compliance",
                "suitable_personas": ["security_specialist"],
                "priority": 9,
                "is_required": True
            },
            {
                "role_id": "DBA Specialist",
                "description": "Database design and optimization",
                "suitable_personas": ["backend_developer", "solution_architect"],
                "priority": 7,
                "is_required": False
            },
            {
                "role_id": "Frontend Lead",
                "description": "Frontend architecture and implementation",
                "suitable_personas": ["frontend_developer"],
                "priority": 8,
                "is_required": True
            },
            {
                "role_id": "Backend Lead",
                "description": "Backend architecture and implementation",
                "suitable_personas": ["backend_developer"],
                "priority": 8,
                "is_required": True
            },
            {
                "role_id": "DevOps Engineer",
                "description": "Infrastructure and deployment",
                "suitable_personas": ["devops_engineer"],
                "priority": 8,
                "is_required": True
            },
            {
                "role_id": "QA Lead",
                "description": "Test strategy and quality assurance",
                "suitable_personas": ["qa_engineer"],
                "priority": 8,
                "is_required": True
            },
            {
                "role_id": "UX Designer",
                "description": "User experience and interface design",
                "suitable_personas": ["ui_ux_designer"],
                "priority": 7,
                "is_required": False
            },
            {
                "role_id": "Documentation Lead",
                "description": "Technical documentation and knowledge management",
                "suitable_personas": ["technical_writer"],
                "priority": 5,
                "is_required": False
            },
            {
                "role_id": "Deployment Specialist",
                "description": "Production deployment and release management",
                "suitable_personas": ["deployment_specialist"],
                "priority": 7,
                "is_required": True
            }
        ]

    async def initialize_standard_roles(
        self,
        team_id: str,
        created_by: str = "system"
    ) -> List[Dict[str, Any]]:
        """
        Initialize all standard SDLC roles for a team

        Creates the role definitions but doesn't assign agents.
        Agents can be assigned later as needed.
        """
        print(f"\n  Initializing standard SDLC roles for team {team_id}...")

        roles = self.get_standard_sdlc_roles()
        created_roles = []

        for role_def in roles:
            try:
                role = await self.create_role(
                    team_id=team_id,
                    role_id=role_def['role_id'],
                    role_description=role_def['description'],
                    is_required=role_def['is_required'],
                    priority=role_def['priority'],
                    created_by=created_by
                )
                created_roles.append(role)
            except Exception as e:
                print(f"  ⚠️  Failed to create role {role_def['role_id']}: {e}")

        print(f"  ✅ Created {len(created_roles)} standard roles\n")

        return created_roles

    # =========================================================================
    # Reporting and Analytics
    # =========================================================================

    async def get_role_assignment_summary(
        self,
        team_id: str
    ) -> Dict[str, Any]:
        """Get summary of role assignments for a team"""
        all_roles = await self.get_all_roles(team_id, active_only=True)
        unfilled = await self.get_unfilled_roles(team_id, required_only=True)

        filled_roles = [r for r in all_roles if r['current_agent_id']]
        unfilled_roles = [r for r in all_roles if not r['current_agent_id']]

        return {
            "team_id": team_id,
            "total_roles": len(all_roles),
            "filled_roles": len(filled_roles),
            "unfilled_roles": len(unfilled_roles),
            "required_unfilled": len(unfilled),
            "roles": all_roles
        }

    async def print_role_summary(self, team_id: str):
        """Print formatted role assignment summary"""
        summary = await self.get_role_assignment_summary(team_id)

        print(f"\n{'=' * 80}")
        print(f"ROLE ASSIGNMENT SUMMARY: {team_id}")
        print(f"{'=' * 80}\n")

        print(f"  Total roles: {summary['total_roles']}")
        print(f"  Filled: {summary['filled_roles']}")
        print(f"  Unfilled: {summary['unfilled_roles']}")

        if summary['required_unfilled'] > 0:
            print(f"  ⚠️  Required roles unfilled: {summary['required_unfilled']}")

        print(f"\n  Role Details:")
        for role in summary['roles']:
            status = "✓ Filled" if role['current_agent_id'] else "✗ Unfilled"
            agent = f"({role['current_agent_id']})" if role['current_agent_id'] else ""
            priority = f"Priority: {role['priority']}"
            required = "[REQUIRED]" if role['is_required'] else ""

            print(f"    {status} {role['role_id']} {agent} {priority} {required}")

        print(f"\n{'=' * 80}\n")


if __name__ == "__main__":
    print("Role Management System")
    print("=" * 80)
    print("\nEnables role-based assignment abstraction where:")
    print("- Tasks are assigned to roles (e.g., 'Security Auditor')")
    print("- Roles can be filled by different agents over time")
    print("- Seamless handoffs without reassigning tasks")
    print("\nStandard SDLC Roles:")
    for role in RoleManager.get_standard_sdlc_roles():
        print(f"  - {role['role_id']}: {role['description']}")
