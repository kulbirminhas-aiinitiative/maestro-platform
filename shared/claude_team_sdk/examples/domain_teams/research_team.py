#!/usr/bin/env python3
"""
Research Team Example - Scientific Discovery

Team Composition (4 members - Small focused team):
- 1 Principal Investigator (Lead scientist)
- 1 Research Scientist (Experimental work)
- 1 Data Analyst (Statistical analysis)
- 1 Research Writer (Publications)

Scenario: Collaborative research on new drug compound
"""

import asyncio
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from claude_team_sdk import TeamAgent, AgentConfig, AgentRole, TeamCoordinator, TeamConfig


class PrincipalInvestigatorAgent(TeamAgent):
    """PI leading the research"""

    def __init__(self, agent_id: str, coordination_server):
        config = AgentConfig(
            agent_id=agent_id,
            role=AgentRole.COORDINATOR,
            auto_claim_tasks=False,
            system_prompt=f"""You are Dr. {agent_id}, a Principal Investigator leading research.

RESPONSIBILITIES:
- Define research hypotheses and methodology
- Coordinate team research activities
- Review and interpret findings
- Secure funding and resources
- Guide publication strategy

LEADERSHIP STYLE:
- Foster collaborative inquiry
- Encourage rigorous methodology
- Support junior researchers
- Promote open scientific discourse
- Ensure ethical research practices

Guide the team toward meaningful scientific discovery."""
        )
        super().__init__(config, coordination_server)


async def run_research_project():
    """Simulate a scientific research collaboration"""

    print("🔬 SCIENTIFIC RESEARCH TEAM COLLABORATION")
    print("=" * 70)
    print("\nResearch Project: Novel Antibiotic Compound XR-47")
    print("Team Size: 4 members (Small focused team)")
    print("Phase: Initial efficacy testing")
    print("\n" + "=" * 70 + "\n")

    config = TeamConfig(team_id="research_lab_001")
    coordinator = TeamCoordinator(config)
    coord_server = coordinator.create_coordination_server()

    # Create small research team
    from claude_team_sdk import ArchitectAgent, DeveloperAgent, ReviewerAgent

    pi = ArchitectAgent("dr_martinez", coord_server)  # Using architect as PI role
    scientist = DeveloperAgent("dr_chen", coord_server)  # Research scientist
    analyst = DeveloperAgent("dr_patel", coord_server)  # Data analyst
    writer = ReviewerAgent("dr_kim", coord_server)  # Research writer

    print("👥 RESEARCH TEAM:")
    print("   1. Dr. Martinez (Principal Investigator)")
    print("   2. Dr. Chen (Research Scientist - Lab work)")
    print("   3. Dr. Patel (Data Analyst - Statistics)")
    print("   4. Dr. Kim (Research Writer - Publications)")
    print("\n" + "=" * 70 + "\n")

    await pi.initialize()
    await scientist.initialize()
    await analyst.initialize()
    await writer.initialize()

    print("📋 RESEARCH WORKFLOW:\n")

    # Phase 1: PI sets hypothesis
    print("[PHASE 1] PI defines research hypothesis and methodology\n")

    await pi.send_message(
        "all",
        "Hypothesis: XR-47 shows >70% efficacy against multi-drug resistant bacteria. Begin efficacy testing with standardized protocol.",
        "info"
    )

    await pi.share_knowledge(
        "hypothesis",
        "XR-47 antibiotic compound tested against MDR bacteria. Expected: >70% kill rate. Control: Standard antibiotic (30-40% efficacy)",
        "research"
    )

    await asyncio.sleep(1)

    # Phase 2: Scientist conducts experiments
    print("[PHASE 2] Research scientist conducts experiments\n")

    await scientist.send_message(
        "all",
        "Lab work complete. XR-47 showed 78% bacterial kill rate vs 35% for control. Data ready for analysis.",
        "info"
    )

    await scientist.share_knowledge(
        "experimental_data",
        "Sample size: n=120, XR-47 efficacy: 78% ± 4%, Control: 35% ± 3%, p<0.001, No adverse cytotoxicity observed",
        "data"
    )

    await asyncio.sleep(1)

    # Phase 3: Analyst reviews data
    print("[PHASE 3] Data analyst performs statistical analysis\n")

    exp_data = await analyst.get_knowledge("experimental_data")

    await analyst.send_message(
        "all",
        "Statistical analysis confirms significance. 78% efficacy with strong confidence (p<0.001). Recommend proceeding to Phase II.",
        "info"
    )

    await analyst.share_knowledge(
        "statistical_analysis",
        "Results: Highly significant (p<0.001), Effect size: Large (Cohen's d=2.3), Power: 0.98, Confidence: 95% CI [74-82%]",
        "analysis"
    )

    await asyncio.sleep(1)

    # Phase 4: Writer prepares findings
    print("[PHASE 4] Research writer prepares manuscript\n")

    await writer.send_message(
        "dr_martinez",
        "Draft abstract ready. Key finding: XR-47 demonstrates superior efficacy against MDR bacteria. Ready for your review.",
        "info"
    )

    await asyncio.sleep(1)

    # Phase 5: Team discusses publication
    print("[PHASE 5] Team collaborates on publication strategy\n")

    await pi.send_message(
        "all",
        "Excellent work team! Let's target high-impact journal. Dr. Kim, highlight novelty. Dr. Patel, add supplementary statistical tables.",
        "info"
    )

    await asyncio.sleep(1)

    # Summary
    print("\n" + "=" * 70)
    print("\n📊 RESEARCH SUMMARY:")

    state = await coordinator.get_workspace_state()
    print(f"\nTeam Collaboration:")
    print(f"  - Messages exchanged: {state['messages']}")
    print(f"  - Knowledge shared: {state['knowledge_items']}")

    print(f"\n🔬 KEY FINDINGS:")
    print(f"  - XR-47 efficacy: 78% (vs 35% control)")
    print(f"  - Statistical significance: p<0.001")
    print(f"  - No cytotoxicity observed")
    print(f"  - Ready for Phase II clinical trials")

    print(f"\n📝 PUBLICATION STATUS:")
    print(f"  - Manuscript drafted")
    print(f"  - Statistical analysis complete")
    print(f"  - Target: High-impact medical journal")

    print("\n" + "=" * 70 + "\n")

    await pi.shutdown()
    await scientist.shutdown()
    await analyst.shutdown()
    await writer.shutdown()
    await coordinator.shutdown()

    print("✅ Research project completed!\n")


if __name__ == "__main__":
    asyncio.run(run_research_project())
