#!/usr/bin/env python3
"""
Fraud Alert Dashboard - Parallel Execution Demo

Demonstrates "Speculative Execution and Convergent Design" strategy.
Timeline: T+0 → T+240 (4 hours)
Result: 4 days → 4 hours (24x speedup)
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from persistence import init_database, StateManager, DatabaseConfig
from persistence.redis_manager import RedisManager
from parallel_workflow_engine import ParallelWorkflowEngine


async def print_timeline(time: str, title: str):
    print(f"\n{'=' * 80}\n⏱️  {time}: {title}\n{'=' * 80}\n")


async def demo_fraud_alert_parallel():
    """Fraud Alert Dashboard parallel execution demo"""

    print("\n🚀 FRAUD ALERT DASHBOARD - PARALLEL EXECUTION DEMO")
    print("=" * 80 + "\n")

    db_config = DatabaseConfig.for_testing()
    db = await init_database(db_config)
    redis = RedisManager()
    await redis.initialize()
    state = StateManager(db, redis)

    team_id = "fraud_alert_team"
    engine = ParallelWorkflowEngine(team_id, state)

    # T+0: Requirement arrives
    await print_timeline("T+0 Minutes", "REQUIREMENT ARRIVES")

    mvd = {
        "id": "req_fraud_dashboard",
        "title": "Real-Time Fraud Alert Dashboard",
        "description": "Dashboard showing suspicious transactions in real-time"
    }
    print(f"📋 Requirement: {mvd['title']}\n✓ AI notifies ALL roles simultaneously")

    # T+15: All roles start work
    await print_timeline("T+15 Minutes", "PARALLEL EXECUTION STARTS")

    work_streams = [
        {"role": "BA", "agent_id": "ba_001", "stream_type": "Analysis", "initial_task": "Define criteria"},
        {"role": "Architect", "agent_id": "sa_001", "stream_type": "Architecture", "initial_task": "Design system"},
        {"role": "Backend Dev", "agent_id": "be_001", "stream_type": "Backend", "initial_task": "Build API"},
        {"role": "Frontend Dev", "agent_id": "fe_001", "stream_type": "Frontend", "initial_task": "Build UI"}
    ]

    await engine.start_parallel_work_streams(mvd, work_streams)

    # Architect creates contract v0.1
    contract_v01 = await engine.contracts.create_contract(
        team_id=team_id,
        contract_name="FraudAlertsAPI",
        version="v0.1",
        contract_type="REST_API",
        specification={
            "endpoint": "/api/v1/fraud-alerts",
            "response": {"id": "string", "timestamp": "string", "amount": "number", "reason": "string"}
        },
        owner_role="Architect",
        owner_agent="sa_001",
        consumers=["be_001", "fe_001"]
    )
    await engine.contracts.activate_contract(contract_v01['id'], "sa_001")

    # Track assumption
    assumption = await engine.assumptions.track_assumption(
        team_id=team_id,
        made_by_agent="sa_001",
        made_by_role="Architect",
        assumption_text="Fields (id, timestamp, amount, reason) are sufficient",
        assumption_category="data_structure",
        related_artifact_type="contract",
        related_artifact_id=contract_v01['id']
    )

    print("\n✅ Backend & Frontend ALREADY WORKING in parallel using contract v0.1!")

    # T+60: BA updates requirement
    await print_timeline("T+60 Minutes", "REQUIREMENT EVOLUTION")

    print("📋 BA adds NEW REQUIREMENTS:")
    print("   - Must include IP address")
    print("   - Must include Device ID")
    print("\n   ⚠️  These fields are missing from contract v0.1!")

    # T+61: AI detects conflict
    await print_timeline("T+61 Minutes", "AI CONFLICT DETECTION")

    await engine.assumptions.invalidate_assumption(
        assumption_id=assumption['id'],
        invalidated_by="ai_orchestrator",
        validation_notes="New fields (ip_address, device_id) required but missing from contract"
    )

    conflict = await engine.create_conflict(
        conflict_type="contract_breach",
        severity="high",
        description="Contract missing required fields: ip_address, device_id",
        artifacts_involved=[{"type": "contract", "id": contract_v01['id']}],
        affected_agents=["sa_001", "be_001", "fe_001"],
        estimated_rework_hours=3
    )

    print("🚨 CONTRACT BREACH detected!")
    print(f"   Conflict ID: {conflict['id']}")
    print("   Affected: Architect, Backend Dev, Frontend Dev")

    # T+70: Convergence
    await print_timeline("T+70 Minutes", "TEAM CONVERGENCE")

    convergence = await engine.trigger_convergence(
        trigger_type="conflict_detected",
        trigger_description="Contract needs new fields for fraud correlation",
        conflict_ids=[conflict['id']],
        participants=["sa_001", "be_001", "fe_001"]
    )

    # Evolve contract to v0.2
    contract_v02 = await engine.contracts.evolve_contract(
        team_id=team_id,
        contract_name="FraudAlertsAPI",
        new_version="v0.2",
        new_specification={
            "endpoint": "/api/v1/fraud-alerts",
            "response": {
                "id": "string", "timestamp": "string", "amount": "number",
                "reason": "string", "ip_address": "string", "device_id": "string"
            }
        },
        changes_from_previous={"added_fields": ["ip_address", "device_id"]},
        breaking_changes=False,
        owner_agent="sa_001"
    )
    await engine.contracts.activate_contract(contract_v02['id'], "sa_001")

    print("\n✓ Backend Dev: Updated Kafka consumer (1 hour)")
    print("✓ Frontend Dev: Added 2 columns to UI (1 hour)")

    await engine.complete_convergence(
        convergence_id=convergence['id'],
        decisions_made=[{"decision": "Add ip_address & device_id", "made_by": "sa_001"}],
        artifacts_updated=[{"type": "contract", "id": contract_v02['id']}],
        rework_performed=[
            {"agent": "be_001", "task": "Update API", "hours": 1},
            {"agent": "fe_001", "task": "Update UI", "hours": 1}
        ]
    )

    print("\n✅ Convergence complete! Rework: 2 hours (localized)")

    # T+240: Complete
    await print_timeline("T+240 Minutes (4 Hours)", "FEATURE COMPLETE")

    print("✅ Real-Time Fraud Alert Dashboard COMPLETE!")
    print("\n📊 Comparison:")
    print("   Traditional: 4 DAYS (sequential)")
    print("   Parallel:    4 HOURS (concurrent)")
    print("\n   🚀 24x SPEEDUP!\n")

    await engine.print_execution_status()
    await state.cleanup()
    print("\n✅ Demo complete!\n")


if __name__ == "__main__":
    asyncio.run(demo_fraud_alert_parallel())
