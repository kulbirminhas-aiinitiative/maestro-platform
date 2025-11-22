#!/usr/bin/env python3
"""
Educational Team Example - Collaborative Learning Project

Team Composition (7 members):
- 1 Lead Teacher (Project coordinator)
- 1 Subject Teacher (Math specialist)
- 3 Students (Team members with different strengths)
- 1 Teaching Assistant (Support)
- 1 Academic Counselor (Guidance)

Scenario: Group project on climate change with collaborative research and presentation
"""

import asyncio
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from claude_team_sdk import TeamAgent, AgentConfig, AgentRole, TeamCoordinator, TeamConfig


class TeacherAgent(TeamAgent):
    """Lead teacher coordinating the project"""

    def __init__(self, agent_id: str, subject: str, coordination_server):
        self.subject = subject
        config = AgentConfig(
            agent_id=agent_id,
            role=AgentRole.COORDINATOR,
            auto_claim_tasks=False,
            system_prompt=f"""You are {agent_id}, a {subject} Teacher coordinating a group project.

RESPONSIBILITIES:
- Guide students through the project
- Provide learning resources and feedback
- Coordinate team activities
- Ensure all students participate
- Assess progress and learning outcomes

TEACHING STYLE:
- Encourage collaboration and peer learning
- Ask guiding questions rather than giving answers
- Celebrate student achievements
- Provide constructive feedback
- Foster critical thinking

WORKFLOW:
1. Introduce project objectives
2. Help students divide tasks
3. Monitor progress and provide guidance
4. Facilitate peer collaboration
5. Assess learning and provide feedback

Create a supportive, engaging learning environment."""
        )
        super().__init__(config, coordination_server)


class StudentAgent(TeamAgent):
    """Student participating in group project"""

    def __init__(self, agent_id: str, strength: str, coordination_server):
        self.strength = strength
        config = AgentConfig(
            agent_id=agent_id,
            role=AgentRole.DEVELOPER,
            system_prompt=f"""You are {agent_id}, a student working on a group project.

YOUR STRENGTH: {strength}
RESPONSIBILITIES:
- Contribute to group project
- Collaborate with teammates
- Research assigned topics
- Ask questions when stuck
- Share findings with team
- Help other students

LEARNING APPROACH:
- Ask questions when confused
- Share what you learn with others
- Build on teammates' ideas
- Be respectful and supportive
- Take initiative in your strength area

WORKFLOW:
1. Understand project goals
2. Claim tasks matching your strength
3. Research and learn
4. Share findings with team
5. Help teammates when possible
6. Contribute to final deliverable

You're here to learn and grow together with your team."""
        )
        super().__init__(config, coordination_server)


class TeachingAssistantAgent(TeamAgent):
    """TA supporting students and teacher"""

    def __init__(self, agent_id: str, coordination_server):
        config = AgentConfig(
            agent_id=agent_id,
            role=AgentRole.REVIEWER,
            system_prompt=f"""You are {agent_id}, a Teaching Assistant supporting the class.

RESPONSIBILITIES:
- Help students with questions
- Review student work
- Provide encouragement
- Alert teacher to student struggles
- Facilitate group discussions

SUPPORT STYLE:
- Patient and approachable
- Scaffold learning (break down complex tasks)
- Encourage student independence
- Provide hints, not answers
- Celebrate effort and growth

WORKFLOW:
1. Monitor student questions and progress
2. Provide targeted support
3. Review student work and give feedback
4. Report concerns to lead teacher
5. Foster positive team dynamics

You help students succeed while building their confidence."""
        )
        super().__init__(config, coordination_server)


class CounselorAgent(TeamAgent):
    """Academic counselor providing guidance"""

    def __init__(self, agent_id: str, coordination_server):
        config = AgentConfig(
            agent_id=agent_id,
            role=AgentRole.ANALYST,
            system_prompt=f"""You are {agent_id}, an Academic Counselor supporting student success.

RESPONSIBILITIES:
- Monitor student wellbeing
- Provide study strategies
- Help with time management
- Support collaboration skills
- Address learning barriers

COUNSELING APPROACH:
- Empathetic and supportive
- Focus on strengths-based learning
- Teach metacognitive skills
- Promote growth mindset
- Encourage self-advocacy

WORKFLOW:
1. Check in with students about workload
2. Provide study and collaboration strategies
3. Help students overcome challenges
4. Share resources for learning
5. Support team dynamics

You help students thrive academically and personally."""
        )
        super().__init__(config, coordination_server)


async def run_educational_project():
    """Simulate a collaborative learning project"""

    print("🎓 COLLABORATIVE LEARNING PROJECT SIMULATION")
    print("=" * 70)
    print("\nProject: Climate Change Impact & Solutions")
    print("Duration: 2-week group project")
    print("Deliverable: Research presentation + action plan")
    print("\n" + "=" * 70 + "\n")

    # Setup
    config = TeamConfig(
        team_id="edu_team_climate",
        workspace_path=Path("./education_workspace")
    )
    coordinator = TeamCoordinator(config)
    coord_server = coordinator.create_coordination_server()

    # Create educational team
    lead_teacher = TeacherAgent("ms_rodriguez", "Science", coord_server)
    math_teacher = TeacherAgent("mr_kim", "Mathematics", coord_server)
    student_emma = StudentAgent("emma", "Research & Writing", coord_server)
    student_raj = StudentAgent("raj", "Data Analysis", coord_server)
    student_sofia = StudentAgent("sofia", "Visual Design", coord_server)
    ta = TeachingAssistantAgent("ta_james", coord_server)
    counselor = CounselorAgent("counselor_lee", coord_server)

    print("👥 LEARNING TEAM:")
    print("   Teachers:")
    print("     1. Ms. Rodriguez (Lead - Science)")
    print("     2. Mr. Kim (Math - Data support)")
    print("   Students:")
    print("     3. Emma (Research & Writing)")
    print("     4. Raj (Data Analysis)")
    print("     5. Sofia (Visual Design)")
    print("   Support:")
    print("     6. TA James (Teaching Assistant)")
    print("     7. Counselor Lee (Academic Counselor)")
    print("\n" + "=" * 70 + "\n")

    # Initialize team
    await lead_teacher.initialize()
    await math_teacher.initialize()
    await student_emma.initialize()
    await student_raj.initialize()
    await student_sofia.initialize()
    await ta.initialize()
    await counselor.initialize()

    print("📚 PROJECT WORKFLOW:\n")

    # Phase 1: Project Introduction
    print("[PHASE 1] Teacher introduces project\n")

    await lead_teacher.send_message(
        "all",
        "Welcome! Our project: Climate Change Impact & Solutions. You'll work together to research, analyze data, and create a presentation. Let's divide tasks based on your strengths!",
        "info"
    )

    await lead_teacher.share_knowledge(
        "project_goals",
        "1) Research climate change impacts, 2) Analyze temperature/sea level data, 3) Propose solutions, 4) Create visual presentation",
        "objectives"
    )

    # Add tasks to queue
    await coordinator.add_task(
        "Research climate change impacts on ecosystems and communities",
        required_role="developer",  # Student role
        priority=10
    )

    await coordinator.add_task(
        "Analyze historical temperature and CO2 data",
        required_role="developer",
        priority=9
    )

    await coordinator.add_task(
        "Design infographics showing key findings",
        required_role="developer",
        priority=7
    )

    await asyncio.sleep(1)

    # Phase 2: Students claim tasks
    print("[PHASE 2] Students claim tasks based on strengths\n")

    await student_emma.send_message(
        "all",
        "I'll take the research task! I love reading scientific articles.",
        "info"
    )

    await student_raj.send_message(
        "all",
        "I'll handle the data analysis - I'm good with numbers and graphs!",
        "info"
    )

    await student_sofia.send_message(
        "all",
        "I'll create the visual design and infographics!",
        "info"
    )

    await asyncio.sleep(1)

    # Phase 3: Counselor checks in
    print("[PHASE 3] Counselor supports team dynamics\n")

    await counselor.send_message(
        "all",
        "Great teamwork! Remember to check in with each other regularly. If anyone feels overwhelmed, reach out. You've got this! 💪",
        "info"
    )

    await counselor.share_knowledge(
        "collaboration_tips",
        "Schedule daily check-ins, use shared documents, ask for help early, celebrate small wins, respect different working styles",
        "guidance"
    )

    await asyncio.sleep(1)

    # Phase 4: Student collaboration
    print("[PHASE 4] Students collaborate and share findings\n")

    # Emma shares research
    await student_emma.send_message(
        "raj",
        "Hey Raj! I found data showing sea levels rose 8-9 inches since 1880. Can you visualize this trend?",
        "request"
    )

    await student_emma.share_knowledge(
        "research_findings",
        "Key impacts: Sea level rise (8-9in since 1880), Arctic ice loss (13% per decade), Extreme weather increase (5x since 1950s)",
        "research"
    )

    await asyncio.sleep(1)

    # Raj responds and shares analysis
    await student_raj.send_message(
        "emma",
        "Thanks Emma! I'll create a trend line graph. Also found global temp increased 1.1°C since pre-industrial times.",
        "response"
    )

    await student_raj.send_message(
        "sofia",
        "Sofia, I'm preparing data visualizations. Can you make them look professional for our presentation?",
        "request"
    )

    await student_raj.share_knowledge(
        "data_analysis",
        "Temperature trend: +1.1°C (1850-2020), CO2 levels: 280ppm → 420ppm, Correlation: 0.89 (very strong)",
        "analysis"
    )

    await asyncio.sleep(1)

    # Sofia responds
    await student_sofia.send_message(
        "raj",
        "Absolutely! Send me the data and I'll create compelling infographics. What color scheme - blues for ocean themes?",
        "response"
    )

    await asyncio.sleep(1)

    # Phase 5: TA provides support
    print("[PHASE 5] TA reviews work and provides feedback\n")

    await ta.send_message(
        "emma",
        "Emma, great research! Try to also include solutions - renewable energy, policy changes. That will strengthen your findings.",
        "info"
    )

    await ta.send_message(
        "raj",
        "Raj, your correlation analysis is excellent! Consider adding error bars to show data confidence.",
        "info"
    )

    await asyncio.sleep(1)

    # Phase 6: Math teacher supports data work
    print("[PHASE 6] Math teacher helps with statistical analysis\n")

    await math_teacher.send_message(
        "raj",
        "Raj, for your correlation analysis, also calculate R-squared value and explain what it means. This shows causation strength.",
        "info"
    )

    await math_teacher.share_knowledge(
        "statistics_help",
        "R-squared: Measure of correlation strength. 0.89 correlation means R² = 0.79, so 79% of temp variation explained by CO2",
        "math_support"
    )

    await asyncio.sleep(1)

    # Phase 7: Student asks for help
    print("[PHASE 7] Student asks question, receives peer support\n")

    await student_emma.send_message(
        "all",
        "I'm having trouble finding credible sources for renewable energy solutions. Any suggestions?",
        "question"
    )

    await ta.send_message(
        "emma",
        "Try NOAA, NASA Climate, and IPCC reports. They're peer-reviewed and authoritative. I can help you evaluate sources if needed.",
        "response"
    )

    await student_raj.send_message(
        "emma",
        "I used EIA (Energy Information Administration) for renewable energy data. Very reliable!",
        "response"
    )

    await asyncio.sleep(1)

    # Phase 8: Team synthesizes work
    print("[PHASE 8] Team shares progress and integrates work\n")

    # Get shared knowledge
    research = await student_sofia.get_knowledge("research_findings")
    analysis = await student_sofia.get_knowledge("data_analysis")

    await student_sofia.send_message(
        "all",
        f"I've created infographics combining Emma's research and Raj's data. Ready for review!",
        "info"
    )

    await student_sofia.share_knowledge(
        "design_mockup",
        "Presentation design: Blue/green theme, 3 main sections: 1) Impacts (Emma's research), 2) Data trends (Raj's graphs), 3) Solutions",
        "deliverable"
    )

    await asyncio.sleep(1)

    # Phase 9: Teacher provides feedback
    print("[PHASE 9] Teacher reviews and provides feedback\n")

    await lead_teacher.send_message(
        "all",
        "Excellent teamwork! Your collaboration is impressive. Emma's research is thorough, Raj's analysis is rigorous, Sofia's design is engaging. Let's finalize!",
        "info"
    )

    await lead_teacher.share_knowledge(
        "teacher_feedback",
        "Strengths: Strong collaboration, evidence-based research, clear data visualization. Improvement: Add more solution details, include action steps",
        "assessment"
    )

    await asyncio.sleep(1)

    # Phase 10: Final team reflection
    print("[PHASE 10] Team reflects on collaboration\n")

    await student_emma.send_message(
        "all",
        "This was great! I learned so much from Raj about data and from Sofia about visual communication.",
        "info"
    )

    await student_raj.send_message(
        "all",
        "Same! Emma taught me to write more clearly, and Sofia showed me how design makes data more impactful.",
        "info"
    )

    await student_sofia.send_message(
        "all",
        "I loved seeing how all our skills came together. We make a great team!",
        "info"
    )

    await asyncio.sleep(2)

    # Summary
    print("\n" + "=" * 70)
    print("\n📊 PROJECT SUMMARY:")

    state = await coordinator.get_workspace_state()
    print(f"\nTeam Collaboration:")
    print(f"  - Messages exchanged: {state['messages']}")
    print(f"  - Knowledge shared: {state['knowledge_items']}")
    print(f"  - Active participants: {state['active_agents']}")

    print(f"\n📚 LEARNING OUTCOMES:")
    print(f"  Students:")
    print(f"    - Emma: Research skills, scientific writing, peer collaboration")
    print(f"    - Raj: Statistical analysis, data visualization, math application")
    print(f"    - Sofia: Design thinking, visual communication, synthesis")
    print(f"\n  Collaboration Skills:")
    print(f"    - Task division based on strengths")
    print(f"    - Peer-to-peer learning and support")
    print(f"    - Effective communication")
    print(f"    - Integration of diverse contributions")

    print(f"\n✅ PROJECT DELIVERABLE:")
    print(f"  - Comprehensive climate change presentation")
    print(f"  - Data-driven analysis with visualizations")
    print(f"  - Evidence-based solutions")
    print(f"  - Professional design and layout")

    print(f"\n🌟 TEACHER ASSESSMENT:")
    print(f"  - Excellent teamwork and collaboration")
    print(f"  - Students leveraged individual strengths")
    print(f"  - High-quality, integrated final product")
    print(f"  - Demonstrated 21st-century learning skills")

    print("\n" + "=" * 70 + "\n")

    # Cleanup
    await lead_teacher.shutdown()
    await math_teacher.shutdown()
    await student_emma.shutdown()
    await student_raj.shutdown()
    await student_sofia.shutdown()
    await ta.shutdown()
    await counselor.shutdown()
    await coordinator.shutdown()

    print("✅ Educational project completed successfully!\n")


if __name__ == "__main__":
    asyncio.run(run_educational_project())
