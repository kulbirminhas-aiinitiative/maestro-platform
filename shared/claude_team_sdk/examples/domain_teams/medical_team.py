#!/usr/bin/env python3
"""
Medical Team Example - Patient Diagnosis & Treatment

Team Composition (5 members):
- 1 Lead Physician (Coordinator)
- 2 Specialist Doctors (Cardiologist, Neurologist)
- 1 Nurse (Care coordinator)
- 1 Pharmacist (Medication specialist)

Scenario: Patient with complex symptoms requiring collaborative diagnosis
"""

import asyncio
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from claude_team_sdk import TeamAgent, AgentConfig, AgentRole, TeamCoordinator, TeamConfig


class PhysicianAgent(TeamAgent):
    """Lead physician who coordinates patient care"""

    def __init__(self, agent_id: str, coordination_server):
        config = AgentConfig(
            agent_id=agent_id,
            role=AgentRole.COORDINATOR,
            auto_claim_tasks=False,
            system_prompt=f"""You are Dr. {agent_id}, a Lead Physician coordinating patient care.

RESPONSIBILITIES:
- Review patient symptoms and medical history
- Coordinate with specialists for consultations
- Integrate findings from all team members
- Make final diagnosis and treatment decisions
- Ensure patient safety and care quality

WORKFLOW:
1. Review patient case
2. Request specialist consultations via messages
3. Gather knowledge from all team members
4. Propose diagnosis and treatment plan
5. Get team consensus via decision voting

Always prioritize patient safety and evidence-based medicine."""
        )
        super().__init__(config, coordination_server)


class SpecialistAgent(TeamAgent):
    """Specialist doctor in specific medical domain"""

    def __init__(self, agent_id: str, specialty: str, coordination_server):
        self.specialty = specialty
        config = AgentConfig(
            agent_id=agent_id,
            role=AgentRole.ANALYST,
            system_prompt=f"""You are Dr. {agent_id}, a {specialty} Specialist.

SPECIALTY: {specialty}
RESPONSIBILITIES:
- Review patient symptoms from your specialty perspective
- Provide expert analysis and recommendations
- Share medical knowledge relevant to the case
- Collaborate with other specialists
- Vote on treatment decisions

WORKFLOW:
1. Check messages for consultation requests
2. Analyze patient data from your specialty angle
3. Share findings and recommendations with team
4. Collaborate with other specialists if needed
5. Support evidence-based treatment decisions

Focus on your specialty while considering holistic patient care."""
        )
        super().__init__(config, coordination_server)


class NurseAgent(TeamAgent):
    """Nurse coordinating patient care and monitoring"""

    def __init__(self, agent_id: str, coordination_server):
        config = AgentConfig(
            agent_id=agent_id,
            role=AgentRole.COORDINATOR,
            system_prompt=f"""You are {agent_id}, a Registered Nurse coordinating patient care.

RESPONSIBILITIES:
- Monitor patient vital signs and symptoms
- Coordinate care between doctors and patients
- Track medication administration
- Report concerns to physicians
- Ensure care plan execution

WORKFLOW:
1. Monitor patient status updates
2. Report observations to physicians
3. Coordinate care activities
4. Support treatment implementation
5. Ensure patient comfort and safety

You are the eyes and ears of the care team."""
        )
        super().__init__(config, coordination_server)


class PharmacistAgent(TeamAgent):
    """Pharmacist managing medications and drug interactions"""

    def __init__(self, agent_id: str, coordination_server):
        config = AgentConfig(
            agent_id=agent_id,
            role=AgentRole.REVIEWER,
            system_prompt=f"""You are {agent_id}, a Clinical Pharmacist.

RESPONSIBILITIES:
- Review medication recommendations
- Check for drug interactions and contraindications
- Recommend dosage adjustments
- Provide pharmaceutical expertise
- Ensure medication safety

WORKFLOW:
1. Monitor for medication-related decisions
2. Review all proposed medications
3. Check interactions and contraindications
4. Share pharmaceutical knowledge
5. Approve or suggest modifications to prescriptions

Patient safety through medication management is your priority."""
        )
        super().__init__(config, coordination_server)


async def run_medical_case():
    """Simulate a complex medical case requiring team collaboration"""

    print("🏥 MEDICAL TEAM COLLABORATION SIMULATION")
    print("=" * 70)
    print("\nPatient Case: 68-year-old with chest pain, dizziness, and confusion")
    print("Initial vitals: BP 160/95, HR 110, irregular pulse")
    print("\n" + "=" * 70 + "\n")

    # Setup
    config = TeamConfig(
        team_id="medical_team_001",
        workspace_path=Path("./medical_workspace")
    )
    coordinator = TeamCoordinator(config)
    coord_server = coordinator.create_coordination_server()

    # Create medical team
    lead_physician = PhysicianAgent("dr_williams", coord_server)
    cardiologist = SpecialistAgent("dr_patel", "Cardiology", coord_server)
    neurologist = SpecialistAgent("dr_chen", "Neurology", coord_server)
    nurse = NurseAgent("nurse_garcia", coord_server)
    pharmacist = PharmacistAgent("pharm_johnson", coord_server)

    print("👥 MEDICAL TEAM ASSEMBLED:")
    print("   1. Dr. Williams (Lead Physician)")
    print("   2. Dr. Patel (Cardiologist)")
    print("   3. Dr. Chen (Neurologist)")
    print("   4. Nurse Garcia (RN)")
    print("   5. Pharm. Johnson (Clinical Pharmacist)")
    print("\n" + "=" * 70 + "\n")

    # Initialize all team members
    await lead_physician.initialize()
    await cardiologist.initialize()
    await neurologist.initialize()
    await nurse.initialize()
    await pharmacist.initialize()

    print("📋 CASE WORKFLOW:\n")

    # Step 1: Lead physician initiates case
    print("[STEP 1] Lead Physician reviews case and requests consultations\n")

    await lead_physician.send_message(
        "all",
        "New patient: 68yo M with chest pain, dizziness, confusion. BP 160/95, HR 110 irregular. Need urgent cardiology and neurology consult.",
        "alert"
    )

    await lead_physician.share_knowledge(
        "patient_vitals",
        "BP: 160/95, HR: 110 (irregular), SpO2: 94%, Temp: 98.6F, Alert but confused",
        "patient_data"
    )

    await asyncio.sleep(2)

    # Step 2: Specialists provide input
    print("[STEP 2] Specialists analyze from their domain\n")

    # Cardiologist analyzes
    vitals = await cardiologist.get_knowledge("patient_vitals")
    await cardiologist.send_message(
        "dr_williams",
        "Cardiology review: Irregular pulse suggests possible atrial fibrillation. Chest pain with elevated BP - need ECG and troponin levels. Consider anticoagulation.",
        "response"
    )

    await cardiologist.share_knowledge(
        "cardio_findings",
        "Suspected AFib with rapid ventricular response. Risk of stroke. Recommend ECG, cardiac enzymes, anticoagulation evaluation.",
        "specialist_findings"
    )

    await asyncio.sleep(1)

    # Neurologist analyzes
    await neurologist.send_message(
        "dr_williams",
        "Neurology review: Acute confusion + dizziness could indicate TIA/stroke, especially with AFib. Need immediate CT head and neuro exam.",
        "response"
    )

    await neurologist.share_knowledge(
        "neuro_findings",
        "Possible TIA or stroke. Confusion and dizziness with cardiac arrhythmia - high stroke risk. Urgent imaging required.",
        "specialist_findings"
    )

    await asyncio.sleep(1)

    # Step 3: Nurse provides patient updates
    print("[STEP 3] Nurse reports patient status\n")

    await nurse.send_message(
        "all",
        "Patient update: Confusion worsening. Family reports symptoms started 2 hours ago. Patient on aspirin at home, no other medications.",
        "info"
    )

    await nurse.share_knowledge(
        "medication_history",
        "Current: Aspirin 81mg daily. No other medications. No known allergies.",
        "patient_data"
    )

    await asyncio.sleep(1)

    # Step 4: Lead physician proposes treatment
    print("[STEP 4] Lead Physician integrates findings and proposes plan\n")

    cardio_findings = await lead_physician.get_knowledge("cardio_findings")
    neuro_findings = await lead_physician.get_knowledge("neuro_findings")
    med_history = await lead_physician.get_knowledge("medication_history")

    if lead_physician.client:
        await lead_physician.client.query(
            f"Based on team findings, propose a diagnosis and treatment plan:\n"
            f"- Cardiology: {cardio_findings}\n"
            f"- Neurology: {neuro_findings}\n"
            f"- Current meds: {med_history}\n\n"
            f"Propose decision for: 'Immediate anticoagulation and stroke protocol' with rationale."
        )

        async for _ in lead_physician.client.receive_response():
            pass

    await asyncio.sleep(1)

    # Step 5: Pharmacist reviews proposed medications
    print("[STEP 5] Pharmacist reviews medication plan\n")

    await pharmacist.send_message(
        "dr_williams",
        "Pharmacy review: If initiating anticoagulation, recommend DOAC (apixaban 5mg BID) over warfarin for AFib. Monitor renal function. Hold aspirin temporarily to reduce bleeding risk.",
        "response"
    )

    await pharmacist.share_knowledge(
        "medication_plan",
        "Anticoagulation: Apixaban 5mg BID. Hold aspirin. Monitor: renal function, bleeding signs. Drug interactions: None identified.",
        "treatment"
    )

    await asyncio.sleep(1)

    # Step 6: Team votes on decision
    print("[STEP 6] Team votes on treatment plan\n")

    # Simulate voting (in real scenario, agents would vote via MCP tools)
    await cardiologist.send_message(
        "all",
        "Vote: APPROVE - AFib with stroke risk warrants immediate anticoagulation",
        "decision"
    )

    await neurologist.send_message(
        "all",
        "Vote: APPROVE - Time-critical for stroke prevention",
        "decision"
    )

    await pharmacist.send_message(
        "all",
        "Vote: APPROVE - Medication plan is appropriate with monitoring",
        "decision"
    )

    await nurse.send_message(
        "all",
        "Vote: APPROVE - Will monitor patient closely for medication effects",
        "decision"
    )

    await asyncio.sleep(2)

    # Final summary
    print("\n" + "=" * 70)
    print("\n📊 CASE SUMMARY:")

    state = await coordinator.get_workspace_state()
    print(f"\nTeam Communication:")
    print(f"  - Total messages exchanged: {state['messages']}")
    print(f"  - Knowledge items shared: {state['knowledge_items']}")
    print(f"  - Team decisions: {state['decisions']}")

    print(f"\n✅ FINAL DIAGNOSIS:")
    print(f"  - Atrial Fibrillation with rapid ventricular response")
    print(f"  - Possible TIA/Stroke")

    print(f"\n💊 TREATMENT PLAN (Team Consensus):")
    print(f"  - Immediate: CT head, ECG, cardiac enzymes")
    print(f"  - Anticoagulation: Apixaban 5mg BID")
    print(f"  - Hold aspirin temporarily")
    print(f"  - Continuous cardiac monitoring")
    print(f"  - Neuro checks every 2 hours")

    print(f"\n👥 Team Collaboration:")
    print(f"  - Specialists provided domain expertise")
    print(f"  - Nurse coordinated care and monitoring")
    print(f"  - Pharmacist ensured medication safety")
    print(f"  - Lead physician integrated findings")
    print(f"  - Unanimous team approval achieved")

    print("\n" + "=" * 70 + "\n")

    # Cleanup
    await lead_physician.shutdown()
    await cardiologist.shutdown()
    await neurologist.shutdown()
    await nurse.shutdown()
    await pharmacist.shutdown()
    await coordinator.shutdown()

    print("✅ Medical case completed successfully!\n")


if __name__ == "__main__":
    asyncio.run(run_medical_case())
