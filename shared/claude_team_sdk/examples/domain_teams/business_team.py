#!/usr/bin/env python3
"""
Business Team Example - Product Launch

Team Composition (8 members - Medium cross-functional team):
- 1 Product Manager (Strategy lead)
- 2 Designers (UI/UX)
- 2 Marketing Specialists (Brand, Digital)
- 1 Business Analyst (Market research)
- 1 Sales Lead (Go-to-market)
- 1 Operations Manager (Launch logistics)

Scenario: Launch new SaaS product in competitive market
"""

import asyncio
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from claude_team_sdk import TeamAgent, AgentConfig, AgentRole, TeamCoordinator, TeamConfig


async def run_product_launch():
    """Simulate a product launch team collaboration"""

    print("💼 BUSINESS TEAM - PRODUCT LAUNCH COLLABORATION")
    print("=" * 70)
    print("\nProduct: CloudSync Pro - Team Collaboration SaaS")
    print("Team Size: 8 members (Cross-functional)")
    print("Goal: Successful market launch in 30 days")
    print("\n" + "=" * 70 + "\n")

    config = TeamConfig(team_id="product_launch_team")
    coordinator = TeamCoordinator(config)
    coord_server = coordinator.create_coordination_server()

    # Create diverse business team using existing agents
    from claude_team_sdk import (CoordinatorAgent, DeveloperAgent, ReviewerAgent,
                                   ArchitectAgent, TesterAgent)

    pm = CoordinatorAgent("sarah_pm", coord_server)  # Product Manager
    designer1 = DeveloperAgent("alex_ux", coord_server)  # UX Designer
    designer2 = DeveloperAgent("maya_ui", coord_server)  # UI Designer
    marketer1 = DeveloperAgent("james_brand", coord_server)  # Brand Marketing
    marketer2 = DeveloperAgent("priya_digital", coord_server)  # Digital Marketing
    analyst = ArchitectAgent("david_analyst", coord_server)  # Business Analyst
    sales = ReviewerAgent("lisa_sales", coord_server)  # Sales Lead
    ops = TesterAgent("mike_ops", coord_server)  # Operations

    print("👥 LAUNCH TEAM:")
    print("   Strategy:")
    print("     1. Sarah (Product Manager)")
    print("     2. David (Business Analyst)")
    print("   Design:")
    print("     3. Alex (UX Designer)")
    print("     4. Maya (UI Designer)")
    print("   Marketing:")
    print("     5. James (Brand Marketing)")
    print("     6. Priya (Digital Marketing)")
    print("   Go-to-Market:")
    print("     7. Lisa (Sales Lead)")
    print("     8. Mike (Operations Manager)")
    print("\n" + "=" * 70 + "\n")

    # Initialize team
    for agent in [pm, designer1, designer2, marketer1, marketer2, analyst, sales, ops]:
        await agent.initialize()

    print("📋 LAUNCH WORKFLOW:\n")

    # Phase 1: PM kicks off
    print("[PHASE 1] Product Manager initiates launch planning\n")

    await pm.send_message(
        "all",
        "Team, we're launching CloudSync Pro in 30 days! Target: Small-medium businesses, 10K users in Q1. Let's align on strategy.",
        "broadcast"
    )

    await pm.share_knowledge(
        "launch_goals",
        "Q1 Target: 10K users, $500K ARR, 20% MOM growth. USP: Real-time collaboration + AI features. Pricing: $15/user/month",
        "strategy"
    )

    await asyncio.sleep(1)

    # Phase 2: Analyst provides market intel
    print("[PHASE 2] Business analyst shares market research\n")

    await analyst.send_message(
        "all",
        "Market analysis: 73% of SMBs need better collaboration. Top pain points: scattered tools (62%), poor mobile UX (54%). We address both!",
        "info"
    )

    await analyst.share_knowledge(
        "market_research",
        "TAM: $12B, Competitors: Slack ($8B), Teams ($5B). Our advantage: AI + mobile-first. Target: 0.5% market share (Y1)",
        "research"
    )

    await asyncio.sleep(1)

    # Phase 3: Designers collaborate
    print("[PHASE 3] Design team creates user experience\n")

    await designer1.send_message(
        "maya_ui",
        "Maya, let's align on design system. I'm focusing on mobile-first UX flows. Can you create component library?",
        "request"
    )

    await designer2.send_message(
        "alex_ux",
        "On it! I'll design UI components matching our brand: clean, modern, AI-powered feel. Blue/purple palette?",
        "response"
    )

    await designer1.share_knowledge(
        "ux_design",
        "Mobile-first approach: 3-tap max to any feature, offline mode, push notifications, AI suggestions in-context",
        "design"
    )

    await asyncio.sleep(1)

    # Phase 4: Marketing plans campaign
    print("[PHASE 4] Marketing team develops campaign strategy\n")

    await marketer1.send_message(
        "priya_digital",
        "Priya, I'm positioning us as 'collaboration + AI intelligence'. Can you run targeted LinkedIn/Google ads?",
        "request"
    )

    await marketer2.send_message(
        "james_brand",
        "Perfect! Targeting: SMB decision-makers, 100-500 employees. Budget: $50K/month. Expected CPA: $120",
        "response"
    )

    await marketer1.share_knowledge(
        "brand_strategy",
        "Messaging: 'Work Smarter Together'. Pillars: 1) AI-powered, 2) Mobile-first, 3) Enterprise security. Tone: Professional yet approachable",
        "marketing"
    )

    await asyncio.sleep(1)

    # Phase 5: Sales prepares go-to-market
    print("[PHASE 5] Sales lead develops GTM strategy\n")

    await sales.send_message(
        "sarah_pm",
        "GTM ready: 14-day free trial, demo videos, sales deck complete. Targeting 50 enterprise pilots. Need pricing approval.",
        "info"
    )

    await sales.share_knowledge(
        "sales_strategy",
        "Channel mix: 60% inbound (content/SEO), 30% outbound (cold email), 10% partnerships. Sales cycle: 30-45 days avg",
        "gtm"
    )

    await asyncio.sleep(1)

    # Phase 6: Operations coordinates launch
    print("[PHASE 6] Operations ensures launch readiness\n")

    await ops.send_message(
        "all",
        "Launch checklist: ✅ Servers scaled, ✅ Support team trained, ✅ Payment integration tested, ⏳ Final QA in progress",
        "info"
    )

    await ops.share_knowledge(
        "ops_readiness",
        "Infrastructure: 99.9% uptime SLA, auto-scaling to 100K users, 24/7 support (email/chat), monitoring dashboards live",
        "operations"
    )

    await asyncio.sleep(1)

    # Phase 7: Team alignment meeting
    print("[PHASE 7] Cross-functional alignment\n")

    await pm.send_message(
        "all",
        "Excellent progress! Let's sync: Design (95% done), Marketing (campaigns ready), Sales (50 pilots lined up), Ops (launch-ready). Launch date: CONFIRMED!",
        "broadcast"
    )

    await asyncio.sleep(2)

    # Summary
    print("\n" + "=" * 70)
    print("\n📊 LAUNCH READINESS SUMMARY:")

    state = await coordinator.get_workspace_state()
    print(f"\nTeam Collaboration:")
    print(f"  - Team members: {state['active_agents']}")
    print(f"  - Messages exchanged: {state['messages']}")
    print(f"  - Knowledge shared: {state['knowledge_items']}")

    print(f"\n🚀 LAUNCH STATUS:")
    print(f"  Product:")
    print(f"    - Name: CloudSync Pro")
    print(f"    - Positioning: AI-powered collaboration for SMBs")
    print(f"    - Pricing: $15/user/month with 14-day trial")

    print(f"\n  Design:")
    print(f"    - ✅ Mobile-first UX complete")
    print(f"    - ✅ UI component library ready")
    print(f"    - ✅ Brand guidelines established")

    print(f"\n  Marketing:")
    print(f"    - ✅ Campaign strategy defined")
    print(f"    - ✅ $50K/month ad budget allocated")
    print(f"    - ✅ Content marketing in progress")

    print(f"\n  Sales:")
    print(f"    - ✅ 50 enterprise pilots secured")
    print(f"    - ✅ Sales materials prepared")
    print(f"    - ✅ GTM strategy finalized")

    print(f"\n  Operations:")
    print(f"    - ✅ Infrastructure scaled")
    print(f"    - ✅ 99.9% uptime SLA")
    print(f"    - ✅ Support team ready")

    print(f"\n📈 TARGETS:")
    print(f"  - Q1 Users: 10,000")
    print(f"  - Q1 Revenue: $500K ARR")
    print(f"  - Growth: 20% MOM")

    print(f"\n✅ LAUNCH DATE: CONFIRMED - Ready to go live!")

    print("\n" + "=" * 70 + "\n")

    # Cleanup
    for agent in [pm, designer1, designer2, marketer1, marketer2, analyst, sales, ops]:
        await agent.shutdown()
    await coordinator.shutdown()

    print("✅ Product launch planning completed!\n")


if __name__ == "__main__":
    asyncio.run(run_product_launch())
