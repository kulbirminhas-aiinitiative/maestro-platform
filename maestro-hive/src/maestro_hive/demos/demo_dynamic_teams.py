#!/usr/bin/env python3
"""
Dynamic Team Management Demo

Demonstrates all 8 real-world scenarios for dynamic team management:
1. Progressive team scaling (2→4 members)
2. Phase-based rotation
3. Performance-based removal
4. Emergency escalation
5. Skill-based dynamic composition
6. Workload-based auto-scaling
7. Cost optimization during idle
8. Cross-project resource sharing

Run this to see the complete dynamic team management system in action.
"""

import asyncio
import sys
from pathlib import Path
import uuid

# Add parent directories to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
sys.path.insert(0, str(Path(__file__).parent))

from dynamic_team_manager import DynamicTeamManager
from team_scenarios import TeamScenarioHandler
from team_composition_policies import ProjectType
from persistence import init_database, StateManager, DatabaseConfig
from persistence.redis_manager import RedisManager


async def run_all_scenarios():
    """Run all 8 scenarios sequentially"""

    print("\n" + "=" * 80)
    print("DYNAMIC TEAM MANAGEMENT - COMPREHENSIVE DEMO")
    print("=" * 80)
    print("\nThis demo shows all 8 real-world team management scenarios.")
    print("Each scenario demonstrates different aspects of dynamic team management.\n")

    # Initialize infrastructure
    print("Initializing infrastructure (SQLite + Redis)...")
    db_config = DatabaseConfig.for_testing()
    db = await init_database(db_config)
    redis = RedisManager()
    await redis.initialize()
    state_manager = StateManager(db, redis)

    print("✓ Infrastructure ready\n")

    # Main menu
    scenarios = {
        "1": ("Progressive Team Scaling (2→4 members)", run_scenario_1),
        "2": ("Phase-Based Rotation", run_scenario_2),
        "3": ("Performance-Based Removal", run_scenario_3),
        "4": ("Emergency Escalation", run_scenario_4),
        "5": ("Skill-Based Dynamic Composition", run_scenario_5),
        "6": ("Workload-Based Auto-Scaling", run_scenario_6),
        "7": ("Cost Optimization During Idle", run_scenario_7),
        "8": ("Cross-Project Resource Sharing", run_scenario_8),
        "all": ("Run All Scenarios", None)
    }

    print("Available scenarios:")
    for key, (name, _) in scenarios.items():
        print(f"  {key}. {name}")

    choice = input("\nSelect scenario (1-8, 'all', or 'q' to quit): ").strip().lower()

    if choice == 'q':
        print("Exiting...")
        await cleanup(db, redis)
        return

    if choice == 'all':
        # Run all scenarios
        for i in range(1, 9):
            team_id = f"demo_team_{i}_{uuid.uuid4().hex[:4]}"
            manager = DynamicTeamManager(
                team_id=team_id,
                state_manager=state_manager,
                project_type=ProjectType.MEDIUM_FEATURE
            )
            handler = TeamScenarioHandler(manager)

            scenario_func = scenarios[str(i)][1]
            await scenario_func(handler)

            input("\nPress Enter to continue to next scenario...")
    elif choice in scenarios:
        # Run selected scenario
        team_id = f"demo_team_{choice}_{uuid.uuid4().hex[:4]}"
        manager = DynamicTeamManager(
            team_id=team_id,
            state_manager=state_manager,
            project_type=ProjectType.MEDIUM_FEATURE
        )
        handler = TeamScenarioHandler(manager)

        scenario_func = scenarios[choice][1]
        await scenario_func(handler)
    else:
        print("Invalid choice")

    print("\n" + "=" * 80)
    print("DEMO COMPLETE")
    print("=" * 80)

    # Cleanup
    await cleanup(db, redis)


async def run_scenario_1(handler: TeamScenarioHandler):
    """Scenario 1: Progressive Team Scaling"""
    result = await handler.scenario_progressive_scaling()
    print(f"\n📊 Result: Scaled from 2 to {result['total_members']} members")


async def run_scenario_2(handler: TeamScenarioHandler):
    """Scenario 2: Phase-Based Rotation"""
    result = await handler.scenario_phase_based_rotation()
    print(f"\n📊 Result: Executed {result['phases_executed']} phases")


async def run_scenario_3(handler: TeamScenarioHandler):
    """Scenario 3: Performance-Based Removal"""
    result = await handler.scenario_performance_based_removal()
    print(f"\n📊 Result: {len(result['actions_taken'])} actions taken")


async def run_scenario_4(handler: TeamScenarioHandler):
    """Scenario 4: Emergency Escalation"""
    result = await handler.scenario_emergency_escalation()
    print(f"\n📊 Result: Emergency team assembled, {result['total_members']} members")


async def run_scenario_5(handler: TeamScenarioHandler):
    """Scenario 5: Skill-Based Dynamic Composition"""
    result = await handler.scenario_skill_based_composition()
    print(f"\n📊 Result: Demonstrated {result['project_types_demonstrated']} project types")


async def run_scenario_6(handler: TeamScenarioHandler):
    """Scenario 6: Workload-Based Auto-Scaling"""
    result = await handler.scenario_workload_autoscaling()
    print(f"\n📊 Result: {len(result['actions_taken'])} scaling actions")


async def run_scenario_7(handler: TeamScenarioHandler):
    """Scenario 7: Cost Optimization"""
    result = await handler.scenario_cost_optimization_idle()
    print(f"\n📊 Result: {result['cost_savings_hours']} hours saved")


async def run_scenario_8(handler: TeamScenarioHandler):
    """Scenario 8: Cross-Project Resource Sharing"""
    result = await handler.scenario_cross_project_sharing()
    print(f"\n📊 Result: {result['projects']} projects sharing {result['shared_specialist']}")


async def cleanup(db, redis):
    """Clean up resources"""
    print("\nCleaning up...")
    await redis.close()
    await db.close()
    print("✓ Cleanup complete")


async def quick_demo():
    """Quick demo of most important scenarios"""
    print("\n" + "=" * 80)
    print("QUICK DEMO - DYNAMIC TEAM MANAGEMENT")
    print("=" * 80)
    print("\nShowing 3 key scenarios:\n")

    # Initialize
    db_config = DatabaseConfig.for_testing()
    db = await init_database(db_config)
    redis = RedisManager()
    await redis.initialize()
    state_manager = StateManager(db, redis)

    # Scenario 1: Progressive Scaling
    print("\n" + "─" * 80)
    team_id = f"quick_demo_{uuid.uuid4().hex[:4]}"
    manager = DynamicTeamManager(
        team_id=team_id,
        state_manager=state_manager,
        project_type=ProjectType.MEDIUM_FEATURE
    )
    handler = TeamScenarioHandler(manager)

    await handler.scenario_progressive_scaling()

    # Scenario 2: Phase-Based (just 2 phases)
    print("\n" + "─" * 80)
    team_id = f"quick_demo_{uuid.uuid4().hex[:4]}"
    manager = DynamicTeamManager(
        team_id=team_id,
        state_manager=state_manager,
        project_type=ProjectType.FULL_SDLC
    )
    handler = TeamScenarioHandler(manager)

    from team_organization import SDLCPhase
    await handler.scenario_phase_based_rotation(
        phases_to_execute=[SDLCPhase.REQUIREMENTS, SDLCPhase.DESIGN]
    )

    # Scenario 3: Emergency
    print("\n" + "─" * 80)
    team_id = f"quick_demo_{uuid.uuid4().hex[:4]}"
    manager = DynamicTeamManager(
        team_id=team_id,
        state_manager=state_manager,
        project_type=ProjectType.MEDIUM_FEATURE
    )
    handler = TeamScenarioHandler(manager)

    await handler.scenario_emergency_escalation()

    print("\n" + "=" * 80)
    print("QUICK DEMO COMPLETE")
    print("=" * 80)
    print("\nRun with 'all' option to see all 8 scenarios.\n")

    await cleanup(db, redis)


async def scenario_comparison_demo():
    """
    Compare team compositions for different project types
    """
    print("\n" + "=" * 80)
    print("TEAM COMPOSITION COMPARISON")
    print("=" * 80)
    print("\nShowing how team size varies by project type:\n")

    from team_composition_policies import TeamCompositionPolicy

    policy = TeamCompositionPolicy()

    project_types = [
        ProjectType.BUG_FIX,
        ProjectType.SIMPLE_FEATURE,
        ProjectType.MEDIUM_FEATURE,
        ProjectType.SECURITY_PATCH,
        ProjectType.FULL_SDLC
    ]

    print(f"{'Project Type':<25} {'Min':<6} {'Optimal':<8} {'Duration':<10} {'Scaling Policy'}")
    print("─" * 80)

    for proj_type in project_types:
        comp = policy.get_composition_for_project(proj_type)
        print(
            f"{proj_type.value:<25} "
            f"{comp.min_team_size:<6} "
            f"{comp.optimal_team_size:<8} "
            f"{comp.expected_duration_days} days{'':<4} "
            f"{comp.scaling_policy}"
        )

    print("\n" + "=" * 80 + "\n")


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        if sys.argv[1] == "quick":
            asyncio.run(quick_demo())
        elif sys.argv[1] == "compare":
            asyncio.run(scenario_comparison_demo())
        else:
            print("Usage:")
            print("  python demo_dynamic_teams.py         # Interactive menu")
            print("  python demo_dynamic_teams.py quick   # Quick demo (3 scenarios)")
            print("  python demo_dynamic_teams.py compare # Compare team compositions")
    else:
        asyncio.run(run_all_scenarios())
