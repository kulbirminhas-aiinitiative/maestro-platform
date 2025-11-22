#!/usr/bin/env python3
"""
Emergency Response Team Example - Crisis Management

Team Composition (6 members - Rapid response team):
- 1 Incident Commander (Leader)
- 1 Fire Chief (Fire operations)
- 1 Medical Lead (EMS coordination)
- 1 Police Coordinator (Law enforcement)
- 1 Communications Officer (Public info)
- 1 Logistics Coordinator (Resources)

Scenario: Multi-vehicle accident with hazmat spill requiring coordinated response
"""

import asyncio
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from claude_team_sdk import TeamAgent, AgentConfig, AgentRole, TeamCoordinator, TeamConfig


async def run_emergency_response():
    """Simulate emergency response team coordination"""

    print("🚨 EMERGENCY RESPONSE TEAM - CRISIS COORDINATION")
    print("=" * 70)
    print("\nIncident: Multi-vehicle accident + Hazmat spill")
    print("Location: Highway 101, Mile Marker 47")
    print("Team Size: 6 members (Rapid response)")
    print("Severity: Level 3 - Major incident")
    print("\n" + "=" * 70 + "\n")

    config = TeamConfig(team_id="emergency_response_001")
    coordinator = TeamCoordinator(config)
    coord_server = coordinator.create_coordination_server()

    # Create emergency response team
    from claude_team_sdk import CoordinatorAgent, DeveloperAgent, ReviewerAgent

    incident_cmd = CoordinatorAgent("cmd_rodriguez", coord_server)
    fire_chief = DeveloperAgent("chief_martinez", coord_server)
    medical_lead = DeveloperAgent("medic_chen", coord_server)
    police_coord = DeveloperAgent("sgt_williams", coord_server)
    comms_officer = ReviewerAgent("pio_jackson", coord_server)
    logistics = DeveloperAgent("log_patel", coord_server)

    print("👥 EMERGENCY RESPONSE TEAM:")
    print("   Command:")
    print("     1. Commander Rodriguez (Incident Commander)")
    print("   Operations:")
    print("     2. Chief Martinez (Fire Operations)")
    print("     3. Medic Chen (EMS Coordinator)")
    print("     4. Sgt. Williams (Police Coordinator)")
    print("   Support:")
    print("     5. PIO Jackson (Communications)")
    print("     6. Log. Patel (Logistics)")
    print("\n" + "=" * 70 + "\n")

    # Initialize team
    for agent in [incident_cmd, fire_chief, medical_lead, police_coord, comms_officer, logistics]:
        await agent.initialize()

    print("📋 INCIDENT RESPONSE TIMELINE:\n")

    # T+0: Initial alert
    print("[T+0 MIN] Incident Commander establishes command\n")

    await incident_cmd.send_message(
        "all",
        "ALERT: Major incident - Highway 101 MM47. Multi-vehicle crash + chemical spill. Establishing unified command. All units report status.",
        "alert"
    )

    await incident_cmd.share_knowledge(
        "incident_details",
        "Type: MVC + Hazmat, Location: Hwy 101 MM47, Initial report: 5 vehicles, unknown injuries, tanker truck leaking chemical",
        "situation"
    )

    await asyncio.sleep(1)

    # T+2: Units report in
    print("[T+2 MIN] Response units report status\n")

    await fire_chief.send_message(
        "cmd_rodriguez",
        "Fire: Engine 5 on scene. Confirming chemical is diesel fuel, not hazmat. Setting up containment. No fire hazard.",
        "info"
    )

    await medical_lead.send_message(
        "cmd_rodriguez",
        "EMS: 3 ambulances en route, ETA 4 min. Triage area being established. Initial report: 2 critical, 3 moderate injuries.",
        "info"
    )

    await police_coord.send_message(
        "cmd_rodriguez",
        "Police: Traffic control in place. Highway closed both directions. Diverting to alternate routes. Scene secured.",
        "info"
    )

    await asyncio.sleep(1)

    # T+4: Situation assessment
    print("[T+4 MIN] Incident Commander assesses situation\n")

    await incident_cmd.send_message(
        "all",
        "SITREP: 5 vehicles, 5 patients (2 critical, 3 moderate). Diesel spill contained. Priority: medical evacuation, then cleanup.",
        "info"
    )

    await incident_cmd.share_knowledge(
        "priorities",
        "1) Medical - evacuate critical patients, 2) Scene safety - complete containment, 3) Traffic - maintain diversions, 4) Cleanup - coordinate hazmat removal",
        "strategy"
    )

    await asyncio.sleep(1)

    # T+6: Medical operations
    print("[T+6 MIN] EMS coordinates patient care\n")

    await medical_lead.send_message(
        "all",
        "Medical update: Critical patients being airlifted to trauma center. Moderate patients to local hospitals. Triage complete.",
        "info"
    )

    await medical_lead.share_knowledge(
        "medical_status",
        "Patient 1: Airlifted (head trauma), Patient 2: Airlifted (internal injuries), Patients 3-5: Transported by ambulance (stable)",
        "medical"
    )

    await asyncio.sleep(1)

    # T+10: Fire operations
    print("[T+10 MIN] Fire completes hazmat containment\n")

    await fire_chief.send_message(
        "cmd_rodriguez",
        "Fire: Diesel spill contained with absorbent booms. Estimated 50 gallons leaked. No environmental spread. Cleanup crew requested.",
        "info"
    )

    await fire_chief.share_knowledge(
        "fire_ops",
        "Containment: Complete, Volume: ~50 gal diesel, Spread: Contained to roadway, Risk: Minimal (no ignition source), Cleanup: Required",
        "operations"
    )

    await asyncio.sleep(1)

    # T+12: Logistics coordinates resources
    print("[T+12 MIN] Logistics coordinates cleanup resources\n")

    await logistics.send_message(
        "all",
        "Logistics: Hazmat cleanup contractor ETA 20 min. Tow trucks (5) en route for vehicle removal. Additional barricades being delivered.",
        "info"
    )

    await logistics.share_knowledge(
        "resources",
        "Cleanup crew: ETA 20min, Tow trucks: 5 units ETA 15min, Barricades: Additional 12 units ETA 10min, Estimated reopening: 90 min",
        "logistics"
    )

    await asyncio.sleep(1)

    # T+15: Public information
    print("[T+15 MIN] Communications updates public\n")

    await comms_officer.send_message(
        "all",
        "Public info released: Hwy 101 closed, use alternate routes. 5 injuries (all transported), diesel spill being cleaned. Reopening est. 2 hours.",
        "info"
    )

    await comms_officer.share_knowledge(
        "public_messaging",
        "Media release: Major incident, 5 injured (transported), no fatalities, highway closed temporarily, public safety maintained, avoid area",
        "communications"
    )

    await asyncio.sleep(1)

    # T+45: Transition to recovery
    print("[T+45 MIN] Incident Commander transitions to recovery phase\n")

    await incident_cmd.send_message(
        "all",
        "TRANSITION: Moving to recovery phase. Medical complete, containment complete. Focus: cleanup and reopening. Excellent coordination, team!",
        "info"
    )

    await asyncio.sleep(2)

    # Summary
    print("\n" + "=" * 70)
    print("\n📊 INCIDENT SUMMARY:")

    state = await coordinator.get_workspace_state()
    print(f"\nTeam Coordination:")
    print(f"  - Response time: 45 minutes to recovery phase")
    print(f"  - Messages exchanged: {state['messages']}")
    print(f"  - Knowledge shared: {state['knowledge_items']}")

    print(f"\n🚨 INCIDENT OUTCOME:")
    print(f"  Medical:")
    print(f"    - 5 patients treated and transported")
    print(f"    - 2 critical (airlifted to trauma center)")
    print(f"    - 3 moderate (transported to local hospitals)")
    print(f"    - 0 fatalities")

    print(f"\n  Hazmat:")
    print(f"    - ~50 gallons diesel fuel")
    print(f"    - Contained within roadway")
    print(f"    - No environmental damage")
    print(f"    - Cleanup in progress")

    print(f"\n  Traffic:")
    print(f"    - Highway closed both directions")
    print(f"    - Traffic successfully diverted")
    print(f"    - Estimated reopening: 90 minutes")

    print(f"\n✅ RESPONSE EFFECTIVENESS:")
    print(f"  - Rapid unified command established")
    print(f"  - Excellent inter-agency coordination")
    print(f"  - Priorities executed efficiently")
    print(f"  - Public safety maintained")
    print(f"  - Clear communication throughout")

    print("\n" + "=" * 70 + "\n")

    # Cleanup
    for agent in [incident_cmd, fire_chief, medical_lead, police_coord, comms_officer, logistics]:
        await agent.shutdown()
    await coordinator.shutdown()

    print("✅ Emergency response completed successfully!\n")


if __name__ == "__main__":
    asyncio.run(run_emergency_response())
