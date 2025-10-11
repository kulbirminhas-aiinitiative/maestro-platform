#!/usr/bin/env python3
"""
SDLC Team Example Scenarios

Demonstrates different use cases for the SDLC team:
1. New Feature Development
2. Critical Bug Fix
3. Security Vulnerability Patch
4. Sprint Planning and Execution
5. System Architecture Redesign

Each scenario shows how the 11 personas collaborate to deliver solutions.
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from sdlc_coordinator import create_sdlc_team
from team_organization import SDLCPhase


async def scenario_1_feature_development():
    """
    Scenario 1: New Feature Development

    Team builds a new "Real-time Notifications" feature from requirements to deployment
    """
    print("\n" + "=" * 80)
    print("SCENARIO 1: NEW FEATURE DEVELOPMENT")
    print("Feature: Real-time Notifications System")
    print("=" * 80)

    # Create SDLC team
    coordinator = await create_sdlc_team(
        project_name="Real-time Notifications System",
        use_sqlite=True
    )

    # Create feature workflow
    await coordinator.create_project_workflow(
        workflow_type="feature",
        feature_name="Real-time Notifications",
        complexity="complex",  # Complex feature
        include_security_review=True,
        include_performance_testing=True
    )

    # Execute through all phases
    phases = [
        SDLCPhase.REQUIREMENTS,
        SDLCPhase.DESIGN,
        SDLCPhase.IMPLEMENTATION,
        SDLCPhase.TESTING,
        SDLCPhase.DEPLOYMENT
    ]

    for phase in phases:
        await coordinator.start_phase(phase)

        # Simulate phase work (in production, agents would autonomously work)
        print(f"\n  🔄 Simulating {phase.value} phase work...")
        await asyncio.sleep(1)  # Simulate work time

        # Check phase completion and transition
        completion = await coordinator.check_phase_completion(phase)
        print(f"  📊 Phase completion: {completion['completion_percentage']:.1f}%")

    # Final status
    await coordinator.print_status()

    # Cleanup
    await coordinator.state.redis.close()
    await coordinator.state.db.close()

    print("\n✅ Scenario 1 Complete: Feature successfully deployed!\n")


async def scenario_2_critical_bugfix():
    """
    Scenario 2: Critical Bug Fix

    Emergency fix for a critical bug affecting production users
    """
    print("\n" + "=" * 80)
    print("SCENARIO 2: CRITICAL BUG FIX")
    print("Bug: Payment processing fails for international transactions")
    print("=" * 80)

    # Create SDLC team
    coordinator = await create_sdlc_team(
        project_name="Critical Payment Bug Fix",
        use_sqlite=True
    )

    # Create bug fix workflow
    await coordinator.create_project_workflow(
        workflow_type="bugfix",
        bug_id="BUG-CRIT-789",
        severity="critical",
        affected_component="backend"
    )

    # Execute bug fix workflow
    print("\n🚨 CRITICAL BUG FIX WORKFLOW:")
    print("  1. Backend Developer: Investigate and fix")
    print("  2. Security Specialist: Security review (critical path)")
    print("  3. QA Engineer: Regression testing")
    print("  4. Deployment Specialist: Emergency deployment")
    print("  5. Integration Tester: Production validation")

    # Run simulation
    await coordinator.run_simulation(max_iterations=20)

    # Cleanup
    await coordinator.state.redis.close()
    await coordinator.state.db.close()

    print("\n✅ Scenario 2 Complete: Bug fixed and deployed!\n")


async def scenario_3_security_patch():
    """
    Scenario 3: Security Vulnerability Patch

    Emergency security patch for a discovered vulnerability
    """
    print("\n" + "=" * 80)
    print("SCENARIO 3: SECURITY VULNERABILITY PATCH")
    print("CVE-2024-12345: SQL Injection in User Search")
    print("=" * 80)

    # Create SDLC team
    coordinator = await create_sdlc_team(
        project_name="Security Patch CVE-2024-12345",
        use_sqlite=True
    )

    # Create security patch workflow
    await coordinator.create_project_workflow(
        workflow_type="security_patch",
        vulnerability_id="VULN-2024-001",
        cve_id="CVE-2024-12345"
    )

    # Execute security patch workflow
    print("\n🔒 SECURITY PATCH WORKFLOW:")
    print("  1. Security Specialist: Assess vulnerability")
    print("  2. Backend Developer: Implement patch")
    print("  3. Security Specialist: Security code review")
    print("  4. Security Specialist: Security testing")
    print("  5. QA Engineer: Regression testing")
    print("  6. Deployment Specialist: Emergency deployment")
    print("  7. Security Specialist: Production validation")

    # Run simulation
    await coordinator.run_simulation(max_iterations=20)

    # Cleanup
    await coordinator.state.redis.close()
    await coordinator.state.db.close()

    print("\n✅ Scenario 3 Complete: Security vulnerability patched!\n")


async def scenario_4_sprint_execution():
    """
    Scenario 4: Sprint Planning and Execution

    2-week sprint with multiple user stories
    """
    print("\n" + "=" * 80)
    print("SCENARIO 4: SPRINT EXECUTION")
    print("Sprint 15: User Profile Enhancement")
    print("=" * 80)

    # Create SDLC team
    coordinator = await create_sdlc_team(
        project_name="Sprint 15 - User Profile Enhancement",
        use_sqlite=True
    )

    # Create sprint workflow
    user_stories = [
        {
            "id": "US-201",
            "title": "User can upload profile picture",
            "points": 5,
            "priority": 8
        },
        {
            "id": "US-202",
            "title": "User can add bio and social links",
            "points": 3,
            "priority": 6
        },
        {
            "id": "US-203",
            "title": "User can customize profile theme",
            "points": 8,
            "priority": 7
        },
        {
            "id": "US-204",
            "title": "Privacy settings for profile visibility",
            "points": 5,
            "priority": 9
        }
    ]

    await coordinator.create_project_workflow(
        workflow_type="sprint",
        sprint_number=15,
        user_stories=user_stories,
        sprint_duration_weeks=2
    )

    # Execute sprint workflow
    print(f"\n🏃 SPRINT 15 WORKFLOW:")
    print(f"  Total Story Points: {sum(s['points'] for s in user_stories)}")
    print(f"  Duration: 2 weeks")
    print(f"\n  User Stories:")
    for story in user_stories:
        print(f"    [{story['points']}pts] {story['id']}: {story['title']}")

    # Run simulation
    await coordinator.run_simulation(max_iterations=50)

    # Cleanup
    await coordinator.state.redis.close()
    await coordinator.state.db.close()

    print("\n✅ Scenario 4 Complete: Sprint successfully delivered!\n")


async def scenario_5_architecture_redesign():
    """
    Scenario 5: System Architecture Redesign

    Major architectural change - migrate from monolith to microservices
    """
    print("\n" + "=" * 80)
    print("SCENARIO 5: ARCHITECTURE REDESIGN")
    print("Migration: Monolith → Microservices Architecture")
    print("=" * 80)

    # Create SDLC team
    coordinator = await create_sdlc_team(
        project_name="Microservices Migration",
        use_sqlite=True
    )

    # Create feature workflow with high complexity
    await coordinator.create_project_workflow(
        workflow_type="feature",
        feature_name="Microservices Architecture Migration",
        complexity="complex",
        include_security_review=True,
        include_performance_testing=True
    )

    # This is a multi-phase project
    print("\n🏗️  ARCHITECTURE REDESIGN PHASES:")
    print("\n  Phase 1: REQUIREMENTS")
    print("    - Requirement Analyst: Business requirements")
    print("    - Solution Architect: Technical requirements")
    print("    - Security Specialist: Security requirements")

    print("\n  Phase 2: DESIGN")
    print("    - Solution Architect: Microservices design")
    print("    - DevOps Engineer: Container orchestration (Kubernetes)")
    print("    - Security Specialist: Security architecture")
    print("    - Backend Developer: API gateway design")

    print("\n  Phase 3: IMPLEMENTATION")
    print("    - Backend Developer: Service decomposition")
    print("    - Backend Developer: API gateway implementation")
    print("    - Frontend Developer: Update frontend integrations")
    print("    - DevOps Engineer: CI/CD pipeline updates")

    print("\n  Phase 4: TESTING")
    print("    - QA Engineer: Integration testing")
    print("    - QA Engineer: Performance testing")
    print("    - Security Specialist: Security testing")
    print("    - QA Engineer: End-to-end testing")

    print("\n  Phase 5: DEPLOYMENT")
    print("    - DevOps Engineer: Kubernetes cluster setup")
    print("    - Deployment Specialist: Phased migration plan")
    print("    - Deployment Specialist: Blue-green deployment")
    print("    - Integration Tester: Production validation")

    # Start requirements phase
    await coordinator.start_phase(SDLCPhase.REQUIREMENTS)

    # Run simulation
    print("\n🔄 Running architecture redesign simulation...")
    await coordinator.run_simulation(max_iterations=100)

    # Final status
    await coordinator.print_status()

    # Cleanup
    await coordinator.state.redis.close()
    await coordinator.state.db.close()

    print("\n✅ Scenario 5 Complete: Architecture successfully redesigned!\n")


async def scenario_6_collaborative_decision():
    """
    Scenario 6: Collaborative Decision Making

    Team discusses and decides on technology stack for new project
    """
    print("\n" + "=" * 80)
    print("SCENARIO 6: COLLABORATIVE DECISION MAKING")
    print("Decision: Choose technology stack for new project")
    print("=" * 80)

    # Create SDLC team
    coordinator = await create_sdlc_team(
        project_name="Technology Stack Decision",
        use_sqlite=True
    )

    print("\n🗳️  DECISION-MAKING PROCESS:")
    print("\n  Participants:")
    print("    - Solution Architect (Proposer)")
    print("    - Backend Developer (Technical Input)")
    print("    - Frontend Developer (Technical Input)")
    print("    - DevOps Engineer (Operational Input)")
    print("    - Security Specialist (Security Review)")
    print("    - Requirement Analyst (Business Alignment)")

    # Simulate collaborative discussion
    print("\n  💬 Discussion:")

    # Architect proposes
    await coordinator.state.propose_decision(
        team_id=coordinator.team_id,
        decision="Adopt React + Node.js + PostgreSQL + Kubernetes stack",
        rationale="Mature ecosystem, strong community support, scalable architecture",
        proposed_by=coordinator.team_members['solution_architect']['agent_id'],
        metadata={
            "technology_stack": {
                "frontend": "React 18",
                "backend": "Node.js 20 + Express",
                "database": "PostgreSQL 15",
                "container_orchestration": "Kubernetes",
                "caching": "Redis",
                "message_queue": "RabbitMQ"
            }
        }
    )

    print("    ✓ Solution Architect proposed technology stack")

    # Team members vote and provide input
    decisions = await coordinator.state.get_decisions(coordinator.team_id)
    if decisions:
        decision_id = decisions[0]['id']

        # Backend developer approves
        await coordinator.state.vote_on_decision(
            decision_id=decision_id,
            agent_id=coordinator.team_members['backend_developer']['agent_id'],
            vote="approve",
            comment="Node.js provides excellent performance and npm ecosystem"
        )
        print("    ✓ Backend Developer: Approved")

        # Frontend developer approves
        await coordinator.state.vote_on_decision(
            decision_id=decision_id,
            agent_id=coordinator.team_members['frontend_developer']['agent_id'],
            vote="approve",
            comment="React is industry standard with excellent tooling"
        )
        print("    ✓ Frontend Developer: Approved")

        # DevOps engineer approves
        await coordinator.state.vote_on_decision(
            decision_id=decision_id,
            agent_id=coordinator.team_members['devops_engineer']['agent_id'],
            vote="approve",
            comment="Kubernetes provides excellent orchestration and scaling"
        )
        print("    ✓ DevOps Engineer: Approved")

        # Security specialist approves with conditions
        await coordinator.state.vote_on_decision(
            decision_id=decision_id,
            agent_id=coordinator.team_members['security_specialist']['agent_id'],
            vote="approve",
            comment="Approved with requirement for security hardening and regular updates"
        )
        print("    ✓ Security Specialist: Approved (with security requirements)")

        # Requirement analyst approves
        await coordinator.state.vote_on_decision(
            decision_id=decision_id,
            agent_id=coordinator.team_members['requirement_analyst']['agent_id'],
            vote="approve",
            comment="Stack aligns with business requirements and hiring market"
        )
        print("    ✓ Requirement Analyst: Approved")

    print("\n  ✅ Decision Result: APPROVED (5/5 votes)")
    print("  📋 Action Items:")
    print("     - Security Specialist: Create security hardening checklist")
    print("     - DevOps Engineer: Setup Kubernetes development cluster")
    print("     - Backend Developer: Initialize Node.js project structure")
    print("     - Frontend Developer: Setup React project with TypeScript")

    # Show final workspace state
    workspace_state = await coordinator.state.get_workspace_state(coordinator.team_id)
    print(f"\n  📊 Workspace Activity:")
    print(f"     - Decisions Proposed: {workspace_state['decisions']}")
    print(f"     - Total Votes: 5")
    print(f"     - Consensus Achieved: Yes")

    # Cleanup
    await coordinator.state.redis.close()
    await coordinator.state.db.close()

    print("\n✅ Scenario 6 Complete: Technology stack decided!\n")


async def main():
    """
    Run all example scenarios
    """
    print("\n" + "=" * 80)
    print("🎯 SDLC TEAM EXAMPLE SCENARIOS")
    print("=" * 80)
    print("\nDemonstrating 6 real-world scenarios:\n")
    print("  1. New Feature Development (Complex)")
    print("  2. Critical Bug Fix (Emergency)")
    print("  3. Security Vulnerability Patch (Critical)")
    print("  4. Sprint Execution (Agile)")
    print("  5. Architecture Redesign (Major)")
    print("  6. Collaborative Decision Making (Governance)")
    print("\n" + "=" * 80)

    scenarios = [
        ("Feature Development", scenario_1_feature_development),
        ("Critical Bug Fix", scenario_2_critical_bugfix),
        ("Security Patch", scenario_3_security_patch),
        ("Sprint Execution", scenario_4_sprint_execution),
        ("Architecture Redesign", scenario_5_architecture_redesign),
        ("Collaborative Decision", scenario_6_collaborative_decision)
    ]

    for i, (name, scenario_func) in enumerate(scenarios, 1):
        print(f"\n\n{'#' * 80}")
        print(f"Running Scenario {i}: {name}")
        print(f"{'#' * 80}\n")

        try:
            await scenario_func()
        except Exception as e:
            print(f"\n❌ Scenario {i} failed: {e}")
            import traceback
            traceback.print_exc()

        if i < len(scenarios):
            print(f"\n⏸️  Waiting 2 seconds before next scenario...")
            await asyncio.sleep(2)

    print("\n\n" + "=" * 80)
    print("🎉 ALL SCENARIOS COMPLETE!")
    print("=" * 80)
    print("\nKey Achievements:")
    print("  ✅ Demonstrated 11 SDLC personas working together")
    print("  ✅ Showed phase-based workflow execution")
    print("  ✅ Illustrated RBAC enforcement")
    print("  ✅ Demonstrated persistent state management")
    print("  ✅ Showed collaborative decision making")
    print("  ✅ Illustrated different workflow types (feature, bug, security, sprint)")
    print("\n" + "=" * 80 + "\n")


if __name__ == "__main__":
    # Run individual scenario or all
    import sys

    if len(sys.argv) > 1:
        scenario_num = sys.argv[1]
        scenarios = {
            "1": scenario_1_feature_development,
            "2": scenario_2_critical_bugfix,
            "3": scenario_3_security_patch,
            "4": scenario_4_sprint_execution,
            "5": scenario_5_architecture_redesign,
            "6": scenario_6_collaborative_decision
        }

        if scenario_num in scenarios:
            asyncio.run(scenarios[scenario_num]())
        else:
            print(f"Unknown scenario: {scenario_num}")
            print("Valid scenarios: 1, 2, 3, 4, 5, 6")
    else:
        # Run all scenarios
        asyncio.run(main())
