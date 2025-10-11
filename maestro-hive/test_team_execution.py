#!/usr/bin/env python3
"""
Test script for team_execution.py

Simulates execution without requiring claude_code_sdk
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime
import json

# Add parent directories to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
sys.path.insert(0, str(Path(__file__).parent))

from personas import SDLCPersonas
from session_manager import SessionManager


async def test_team_execution_dry_run():
    """
    Dry-run test showing the V3.1 workflow without actual execution
    """

    print("="*80)
    print("🧪 TEAM EXECUTION V3.1 - DRY RUN TEST")
    print("="*80)

    # Test requirement
    requirement = "Create a simple TODO application with user authentication"

    print(f"\n📝 Requirement: {requirement}")
    print()

    # Initialize session manager
    session_manager = SessionManager()

    # Create test session
    output_dir = Path("./test_output")
    output_dir.mkdir(parents=True, exist_ok=True)

    session = session_manager.create_session(
        requirement=requirement,
        output_dir=output_dir,
        session_id="test_todo_app"
    )

    print(f"🆕 Created session: {session.session_id}")
    print(f"📁 Output directory: {output_dir}")
    print()

    # Get all personas (load asynchronously if needed)
    try:
        from src.personas import get_adapter
        adapter = get_adapter()
        await adapter.ensure_loaded()
    except:
        pass

    all_personas = SDLCPersonas.get_all_personas()

    # Select subset of personas for test
    selected_personas = [
        "requirement_analyst",
        "solution_architect",
        "backend_developer",
        "frontend_developer",
        "database_administrator"
    ]

    print("👥 Selected Personas:")
    for i, persona_id in enumerate(selected_personas, 1):
        persona = all_personas[persona_id]
        print(f"  {i}. {persona['name']} ({persona_id})")
    print()

    # Simulate V3.1 workflow
    print("="*80)
    print("🔍 STEP 1: PERSONA-LEVEL REUSE ANALYSIS (V3.1)")
    print("="*80)
    print()

    # Simulate similarity analysis
    print("Checking for similar projects...")
    print("Found similar project: 'Task Management System' (proj_12345)")
    print()

    # Simulated persona reuse map
    persona_reuse_map = {
        "overall_similarity": 0.58,  # 58% overall (too low for V4 project clone)
        "persona_decisions": {
            "requirement_analyst": {
                "similarity_score": 1.00,
                "should_reuse": False,  # Always runs first
                "rationale": "First persona - must run to create REQUIREMENTS.md"
            },
            "solution_architect": {
                "similarity_score": 0.92,
                "should_reuse": True,
                "rationale": "Architecture 92% similar: Both use microservices + REST API + PostgreSQL"
            },
            "backend_developer": {
                "similarity_score": 0.42,
                "should_reuse": False,
                "rationale": "Backend logic 42% similar: TODO features differ from task management"
            },
            "frontend_developer": {
                "similarity_score": 0.88,
                "should_reuse": True,
                "rationale": "Frontend 88% similar: Both use React + similar UI components (list, forms, auth)"
            },
            "database_administrator": {
                "similarity_score": 0.35,
                "should_reuse": False,
                "rationale": "Database 35% similar: TODO schema differs from task schema"
            }
        },
        "personas_to_reuse": ["solution_architect", "frontend_developer"],
        "personas_to_execute": ["requirement_analyst", "backend_developer", "database_administrator"]
    }

    print("📊 Persona-Level Analysis Results:")
    print(f"   Overall Similarity: {persona_reuse_map['overall_similarity']:.0%}")
    print(f"   Personas to REUSE: {len(persona_reuse_map['personas_to_reuse'])}")
    print(f"   Personas to EXECUTE: {len(persona_reuse_map['personas_to_execute'])}")
    print()

    for persona_id in selected_personas:
        decision = persona_reuse_map['persona_decisions'][persona_id]
        status = "⚡ REUSE" if decision['should_reuse'] else "🔨 EXECUTE"
        print(f"  {status} {persona_id}: {decision['similarity_score']:.0%}")
        print(f"        {decision['rationale']}")
    print()

    # Calculate savings
    total_personas = len(selected_personas)
    reused_count = len(persona_reuse_map['personas_to_reuse'])
    executed_count = len(persona_reuse_map['personas_to_execute'])
    time_savings_percent = (reused_count / total_personas) * 100
    cost_savings = reused_count * 22  # $22 per persona

    print("💰 Estimated Savings:")
    print(f"   Time saved: {time_savings_percent:.0f}%")
    print(f"   Cost saved: ${cost_savings}")
    print()

    # Simulate execution
    print("="*80)
    print("🚀 STEP 2: EXECUTION")
    print("="*80)
    print()

    start_time = datetime.now()

    for i, persona_id in enumerate(selected_personas, 1):
        decision = persona_reuse_map['persona_decisions'][persona_id]

        print(f"[{i}/{total_personas}] Processing: {persona_id}")

        if decision['should_reuse']:
            print(f"   ⚡ REUSING artifacts from proj_12345")
            print(f"   📥 Fetched: ARCHITECTURE.md, SYSTEM_DESIGN.md")
            print(f"   ✅ Complete (0 seconds, $0)")

            # Simulate adding files to session
            session.add_persona_execution(
                persona_id=persona_id,
                files_created=[f"{persona_id}_reused_artifact.md"],
                deliverables={},
                duration=0,
                success=True
            )

        else:
            print(f"   🔨 EXECUTING fresh")
            print(f"   📄 Creating deliverables...")
            print(f"   ✅ Complete (simulated - would take ~2.75 min, $22)")

            # Simulate adding files to session
            session.add_persona_execution(
                persona_id=persona_id,
                files_created=[f"{persona_id}_output.md"],
                deliverables={},
                duration=2.75 * 60,  # 2.75 minutes in seconds
                success=True
            )

        print()

    # Save session
    session_manager.save_session(session)

    end_time = datetime.now()
    total_duration = (end_time - start_time).total_seconds()

    # Build result
    print("="*80)
    print("📊 EXECUTION SUMMARY - V3.1")
    print("="*80)
    print()
    print(f"✅ Status: Success")
    print(f"🆔 Session: {session.session_id}")
    print(f"📁 Files created: {len(session.get_all_files())}")
    print(f"⏱️  Duration: {total_duration:.2f}s (dry-run)")
    print()

    print("🎯 V3.1 PERSONA-LEVEL REUSE:")
    print(f"   ⚡ Personas reused: {reused_count}")
    print(f"   🔨 Personas executed: {executed_count}")
    print(f"   💰 Cost saved: ${cost_savings}")
    print(f"   ⏱️  Time saved: {time_savings_percent:.0f}%")
    print()

    print(f"📂 Output: {output_dir}")
    print()

    # Show result JSON
    result = {
        "success": True,
        "session_id": session.session_id,
        "requirement": requirement,
        "executed_personas": selected_personas,
        "files": session.get_all_files(),
        "reuse_stats": {
            "personas_reused": reused_count,
            "personas_executed": executed_count,
            "cost_saved_dollars": cost_savings,
            "time_saved_percent": time_savings_percent
        },
        "persona_reuse_map": persona_reuse_map
    }

    print("="*80)
    print("📤 RESULT JSON")
    print("="*80)
    print(json.dumps(result, indent=2))
    print()

    print("="*80)
    print("✅ DRY-RUN TEST COMPLETE")
    print("="*80)
    print()
    print("💡 This demonstrates V3.1 persona-level reuse workflow:")
    print("   - Even with 58% overall similarity (V3 would run full SDLC)")
    print("   - V3.1 identified 2 personas with 88%+ matches and reused them")
    print("   - Result: 40% time savings, $44 cost savings")
    print()
    print("🔧 To run with actual Claude Code SDK:")
    print(f"   python team_execution.py {' '.join(selected_personas)} \\")
    print(f"       --requirement \"{requirement}\" \\")
    print(f"       --session-id test_todo_app")
    print()


if __name__ == "__main__":
    asyncio.run(test_team_execution_dry_run())
