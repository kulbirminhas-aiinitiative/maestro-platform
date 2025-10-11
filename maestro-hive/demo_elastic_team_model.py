#!/usr/bin/env python3
"""
Elastic Team Model Demo - Showcasing Enhanced Features

This demo showcases the 3 critical enhancements for the Elastic Team Model:
1. Role-Based Routing: Tasks assigned to roles, not individuals
2. AI-Powered Onboarding Briefings: Contextual "State of the Union" for new members
3. Knowledge Handoff Protocol: Digital Handshake to prevent knowledge loss

Scenario:
- Start with 2-person team (architect + backend dev)
- Scale to 4 members with role-based assignment
- Demonstrate seamless role reassignment
- Retire member with knowledge handoff
- Show onboarding briefing for replacement
"""

import asyncio
import sys
from pathlib import Path

# Add parent directories to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from persistence import init_database, StateManager, DatabaseConfig
from persistence.redis_manager import RedisManager
from persistence.models import MembershipState
from dynamic_team_manager import DynamicTeamManager
from team_composition_policies import ProjectType
import team_organization

SDLCPhase = team_organization.SDLCPhase


async def print_section(title: str):
    """Print formatted section header"""
    print(f"\n{'=' * 80}")
    print(f"{title}")
    print(f"{'=' * 80}\n")


async def demo_elastic_team_model():
    """Main demo showcasing Elastic Team Model enhancements"""

    # Initialize infrastructure
    await print_section("🚀 ELASTIC TEAM MODEL DEMO")

    print("Initializing infrastructure...")
    db_config = DatabaseConfig.for_testing()
    db = await init_database(db_config)
    redis = RedisManager()
    await redis.initialize()
    state = StateManager(db, redis)

    # Create team manager
    team_id = "elastic_demo_team_001"
    manager = DynamicTeamManager(
        team_id=team_id,
        state_manager=state,
        project_type=ProjectType.MEDIUM_FEATURE,
        project_name="E-Commerce Payment Gateway"
    )

    # =========================================================================
    # PART 1: Initialize Roles (Role Abstraction)
    # =========================================================================

    await print_section("🎭 PART 1: ROLE-BASED ASSIGNMENT INITIALIZATION")

    print("The Elastic Team Model uses role abstraction:")
    print("  • Tasks are assigned to ROLES (e.g., 'Backend Lead')")
    print("  • Roles are filled by AGENTS (e.g., 'backend_developer_001')")
    print("  • Agents can be swapped seamlessly without reassigning tasks\n")

    # Initialize all standard SDLC roles
    await manager.initialize_roles()

    # Show role summary
    await manager.print_role_summary()

    # =========================================================================
    # PART 2: Start with Minimal Team (2 members)
    # =========================================================================

    await print_section("👥 PART 2: MINIMAL TEAM (2 MEMBERS)")

    print("Starting with a minimal 2-person team...")
    print("  • Solution Architect → Tech Lead role")
    print("  • Backend Developer → Backend Lead role\n")

    # Add architect with briefing and role assignment
    result1 = await manager.add_member_with_briefing(
        persona_id="solution_architect",
        reason="Initial tech leadership for payment gateway",
        role_id="Tech Lead"
    )

    print(f"\n📄 Onboarding briefing for {result1['membership']['agent_id']}:")
    briefing1 = result1['briefing']
    print(f"   Executive Summary: {briefing1['executive_summary'][:100]}...")
    print(f"   Focus Areas: {', '.join(briefing1['your_focus_areas'][:3])}")

    # Add backend developer with briefing and role assignment
    result2 = await manager.add_member_with_briefing(
        persona_id="backend_developer",
        reason="Core backend implementation for payment API",
        role_id="Backend Lead"
    )

    print(f"\n📄 Onboarding briefing for {result2['membership']['agent_id']}:")
    briefing2 = result2['briefing']
    print(f"   Executive Summary: {briefing2['executive_summary'][:100]}...")
    print(f"   Immediate Tasks: {len(briefing2['immediate_tasks'])} tasks")

    await manager.print_team_status()

    # =========================================================================
    # PART 3: Scale to 4 Members (Security + DevOps)
    # =========================================================================

    await print_section("📈 PART 3: SCALING UP TO 4 MEMBERS")

    print("Workload increased! Adding Security Auditor and DevOps Engineer...")
    print("Both will receive comprehensive onboarding briefings.\n")

    # Add security specialist
    result3 = await manager.add_member_with_briefing(
        persona_id="security_specialist",
        reason="Security review for payment processing and PCI compliance",
        role_id="Security Auditor"
    )

    print(f"\n📄 Onboarding briefing for {result3['membership']['agent_id']}:")
    briefing3 = result3['briefing']
    print(f"   Key Decisions to know: {len(briefing3['key_decisions'])} decisions")
    print(f"   Key Contacts: {len(briefing3['key_contacts'])} contacts")

    # Add DevOps engineer
    result4 = await manager.add_member_with_briefing(
        persona_id="devops_engineer",
        reason="CI/CD pipeline and infrastructure setup",
        role_id="DevOps Engineer"
    )

    print(f"\n📄 Onboarding briefing for {result4['membership']['agent_id']}:")
    briefing4 = result4['briefing']
    print(f"   Resources to read: {len(briefing4['resources'])} resources")
    print(f"   Current Challenges: {', '.join(briefing4['current_challenges'][:2])}")

    await manager.print_team_status()
    await manager.print_role_summary()

    # =========================================================================
    # PART 4: Seamless Role Reassignment
    # =========================================================================

    await print_section("🔄 PART 4: SEAMLESS ROLE REASSIGNMENT")

    print("Demonstrating the power of role abstraction...")
    print("Scenario: Backend Lead needs to temporarily help with security review\n")

    # Get current backend lead
    backend_agent = result2['membership']['agent_id']
    security_agent = result3['membership']['agent_id']

    print(f"Before reassignment:")
    print(f"  • Backend Lead: {backend_agent}")
    print(f"  • Security Auditor: {security_agent}\n")

    # Add a second backend developer
    result5 = await manager.add_member_with_briefing(
        persona_id="backend_developer",
        reason="Taking over backend lead while original helps with security",
        role_id=None  # Don't assign role yet
    )

    new_backend = result5['membership']['agent_id']

    # Reassign Backend Lead role
    print(f"\n🔄 Reassigning 'Backend Lead' role...")
    await manager.reassign_role(
        role_id="Backend Lead",
        new_agent_id=new_backend,
        reason=f"Original backend lead temporarily helping with security review"
    )

    print(f"\nAfter reassignment:")
    print(f"  • Backend Lead: {new_backend} (NEW)")
    print(f"  • Security Auditor: {security_agent}")
    print(f"  • Former Backend Lead {backend_agent} now free for other work\n")

    print("✅ Key Benefit: All tasks assigned to 'Backend Lead' role")
    print("   now automatically route to the new agent without task reassignment!")

    await manager.print_role_summary()

    # =========================================================================
    # PART 5: Knowledge Handoff (Digital Handshake)
    # =========================================================================

    await print_section("🤝 PART 5: KNOWLEDGE HANDOFF (DIGITAL HANDSHAKE)")

    print("Scenario: Original backend developer is retiring")
    print("We need to capture their knowledge before they leave...\n")

    # Attempt to retire without completing handoff
    print(f"Attempting to retire {backend_agent}...\n")

    result_retire = await manager.retire_member_with_handoff(
        agent_id=backend_agent,
        reason="Project phase complete, moving to other projects",
        require_handoff=True,
        force_skip_handoff=False
    )

    if result_retire['status'] == 'handoff_pending':
        print("✋ Retirement blocked! Handoff checklist incomplete.\n")
        print("Handoff checklist:")
        checklist = result_retire['handoff']['checklist']
        print(f"  ☑️  Artifacts verified: {checklist['artifacts_verified']}")
        print(f"  ☑️  Documentation complete: {checklist['documentation_complete']}")
        print(f"  ☑️  Lessons learned captured: {checklist['lessons_learned_captured']}")

        print("\n📝 Completing handoff checklist...")

        # Complete the handoff
        handoff_complete = await manager.complete_pending_handoff(
            agent_id=backend_agent,
            lessons_learned=(
                "Payment gateway implementation lessons:\n"
                "1. Stripe API has rate limits - implement exponential backoff\n"
                "2. Always use idempotency keys for payment operations\n"
                "3. Store webhook signatures for audit trail\n"
                "4. Test refund flows thoroughly - they're complex"
            ),
            open_questions=[
                "Should we support cryptocurrency payments in v2?",
                "How to handle multi-currency conversion edge cases?"
            ],
            recommendations=[
                "Add comprehensive integration tests for all payment scenarios",
                "Create runbook for handling failed payments",
                "Consider implementing payment retry queue"
            ]
        )

        print("\n✅ Handoff checklist complete!")
        print(f"   Status: {handoff_complete['status']}")
        print(f"   Knowledge captured: {handoff_complete['knowledge_captured']}")

        # Now retry retirement
        print(f"\nRetrying retirement with completed handoff...\n")

        result_retire = await manager.retire_member_with_handoff(
            agent_id=backend_agent,
            reason="Project phase complete, moving to other projects",
            require_handoff=True,
            force_skip_handoff=False
        )

    if result_retire['status'] == 'retired':
        print(f"✅ {backend_agent} successfully retired with knowledge captured!")
        print(f"\nKnowledge preservation summary:")
        print(f"  • Lessons learned: ✓")
        print(f"  • Open questions: ✓")
        print(f"  • Recommendations: ✓")
        print(f"  • All stored in knowledge base for future reference")

    await manager.print_team_status()

    # =========================================================================
    # PART 6: Summary and Benefits
    # =========================================================================

    await print_section("✨ ELASTIC TEAM MODEL BENEFITS DEMONSTRATED")

    print("1. ROLE-BASED ROUTING:")
    print("   ✅ Tasks assigned to roles, not individuals")
    print("   ✅ Seamless agent swapping without task reassignment")
    print("   ✅ Clear separation of concerns (Role → Persona → Agent)\n")

    print("2. AI-POWERED ONBOARDING:")
    print("   ✅ New members receive complete context immediately")
    print("   ✅ Briefings include: decisions, tasks, contacts, resources")
    print("   ✅ Reduces onboarding time and confusion\n")

    print("3. KNOWLEDGE HANDOFF:")
    print("   ✅ Prevents knowledge loss when members leave")
    print("   ✅ Mandatory checklist ensures nothing is forgotten")
    print("   ✅ Lessons learned captured for future benefit\n")

    print("4. DYNAMIC SCALING:")
    print("   ✅ Started with 2 members, scaled to 5")
    print("   ✅ Each addition/removal handled gracefully")
    print("   ✅ Team composition adapts to project needs\n")

    # Final status
    await manager.print_team_status()
    await manager.print_role_summary()

    # Cleanup
    await state.cleanup()
    print("\n✅ Demo complete!\n")


async def main():
    """Run the demo"""
    try:
        await demo_elastic_team_model()
    except KeyboardInterrupt:
        print("\n\n⚠️  Demo interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    print("\n" + "=" * 80)
    print("ELASTIC TEAM MODEL - COMPREHENSIVE DEMO")
    print("=" * 80)
    print("\nThis demo showcases 3 critical enhancements:")
    print("  1. Role-Based Routing")
    print("  2. AI-Powered Onboarding Briefings")
    print("  3. Knowledge Handoff Protocol (Digital Handshake)")
    print("\nStarting demo in 3 seconds...")
    print("=" * 80 + "\n")

    import time
    time.sleep(3)

    asyncio.run(main())
