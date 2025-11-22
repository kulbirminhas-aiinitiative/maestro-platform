#!/usr/bin/env python3
"""
SDK-Based Standard Team - Sequential Workflow with Real Team Coordination

Properly uses claude_team_sdk components:
- TeamCoordinator for team management
- Specialized agents (ArchitectAgent, ReviewerAgent, etc.)
- MCP coordination server for inter-agent communication
- Knowledge sharing and artifact management

Usage:
    python examples/team_wrappers/sdk_standard_team.py \
        --requirement "Build a user authentication system with JWT" \
        --output ./output/standard

Features:
    - Real Claude API calls via SDK agents
    - Inter-agent communication via MCP
    - Knowledge sharing across team
    - Artifact management
    - Sequential workflow (Analyst → Reviewer → Publisher)
"""

import asyncio
import argparse
import sys
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime
import json
import logging

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Import SDK components
try:
    from src.claude_team_sdk import TeamAgent, AgentConfig, AgentRole, AgentStatus, TeamCoordinator
    from src.claude_team_sdk.coordination.team_coordinator import TeamConfig
    from src.claude_team_sdk.config import settings
except ImportError:
    from claude_team_sdk import TeamAgent, AgentConfig, AgentRole, AgentStatus, TeamCoordinator
    from claude_team_sdk.team_coordinator import TeamConfig
    from claude_team_sdk.config import settings

logger = logging.getLogger(__name__)


class AnalystAgent(TeamAgent):
    """Analyst agent - analyzes requirements using SDK infrastructure"""

    def __init__(self, agent_id: str, coordination_server):
        config = AgentConfig(
            agent_id=agent_id,
            role=AgentRole.ANALYST,
            system_prompt=f"""You are {agent_id}, the Requirements Analyst.

RESPONSIBILITIES:
- Analyze user requirements thoroughly
- Create detailed requirement specifications
- Identify functional and non-functional requirements
- Create user stories and acceptance criteria
- Share findings with the team

WORKFLOW:
1. Analyze the requirement using Claude Code tools (Write, Read, etc.)
2. Create comprehensive documentation files:
   - requirements_analysis.md (functional/non-functional requirements, risks)
   - user_stories.md (user stories with acceptance criteria)
   - technical_scope.md (components, technologies, data models)
3. Share key findings with team via share_knowledge
4. Store documents as artifacts
5. Post completion message to team

Use the coordination tools to collaborate with your team members."""
        )
        super().__init__(config, coordination_server)

    async def analyze_requirement(self, requirement: str) -> Dict[str, Any]:
        """Analyze requirement and create deliverables"""
        await self._update_status(AgentStatus.WORKING, "Analyzing requirements")

        logger.info(f"[{self.agent_id}] 🔍 Starting requirement analysis...")

        try:
            # Execute analysis task with Claude
            await self.client.query(
                f"""Analyze this requirement and create comprehensive documentation:

Requirement: {requirement}

Create these deliverables using the Write tool:

1. **requirements_analysis.md**: Include:
   - Functional requirements (numbered list)
   - Non-functional requirements (performance, security, scalability)
   - Assumptions and constraints
   - Risk assessment

2. **user_stories.md**: Include:
   - User stories in format: "As a [user], I want [goal] so that [benefit]"
   - Acceptance criteria for each story

3. **technical_scope.md**: Include:
   - Key components needed
   - Technologies required
   - Integration points
   - Data models

After creating files:
- Use share_knowledge to share key findings with the team
- Use store_artifact to register important documents
- Use post_message to notify the team that analysis is complete"""
            )

            files_created = []
            async for msg in self.client.receive_response():
                # Track file creation
                if hasattr(msg, 'message_type') and msg.message_type == 'tool_use':
                    if hasattr(msg, 'name') and msg.name == 'Write':
                        file_path = msg.input.get('file_path') if hasattr(msg, 'input') else None
                        if file_path:
                            files_created.append(file_path)
                            logger.info(f"  [{self.agent_id}] 📄 Created: {Path(file_path).name}")

            await self._update_status(AgentStatus.IDLE, "Analysis complete")
            logger.info(f"[{self.agent_id}] ✅ Analysis complete: {len(files_created)} files created")

            return {
                "success": True,
                "agent_id": self.agent_id,
                "files_created": files_created
            }

        except Exception as e:
            logger.exception(f"[{self.agent_id}] ❌ Error during analysis")
            await self._update_status(AgentStatus.BLOCKED, f"Error: {str(e)}")
            return {
                "success": False,
                "agent_id": self.agent_id,
                "error": str(e)
            }

    async def execute_role_specific_work(self):
        """Analyst-specific work - not used in this workflow"""
        pass

    async def execute_task(self, task_description: str) -> Dict[str, Any]:
        """Execute task - required by TeamAgent interface"""
        return await self.analyze_requirement(task_description)


class ReviewerAgent(TeamAgent):
    """Reviewer agent - reviews analysis using SDK infrastructure"""

    def __init__(self, agent_id: str, coordination_server):
        config = AgentConfig(
            agent_id=agent_id,
            role=AgentRole.REVIEWER,
            system_prompt=f"""You are {agent_id}, the Technical Reviewer.

RESPONSIBILITIES:
- Review requirement analysis for completeness and accuracy
- Check messages from analyst about completed work
- Retrieve knowledge shared by analyst
- Provide constructive feedback
- Create review reports

WORKFLOW:
1. Check messages from the analyst (use get_messages)
2. Review shared knowledge (use get_knowledge to find key findings)
3. Read the analysis files created by analyst (use Read tool)
4. Create review documents:
   - review_report.md (summary, strengths, issues, recommendations, approval)
   - improvement_suggestions.md (if issues found)
5. Share review findings via share_knowledge
6. Post message to team about review completion

Use coordination tools to collaborate effectively."""
        )
        super().__init__(config, coordination_server)

    async def review_analysis(self) -> Dict[str, Any]:
        """Review the analyst's work"""
        await self._update_status(AgentStatus.WORKING, "Reviewing analysis")

        logger.info(f"[{self.agent_id}] 📋 Starting review process...")

        try:
            await self.client.query(
                """Review the analysis completed by the analyst:

1. First, check messages to see what the analyst completed (use get_messages)
2. Retrieve shared knowledge from the analyst (use get_knowledge)
3. Read the analysis files (use Read tool to review requirements_analysis.md, user_stories.md, technical_scope.md)
4. Analyze for:
   - Completeness
   - Clarity and specificity
   - Technical feasibility
   - Missing requirements
   - Potential risks

5. Create **review_report.md** with:
   - Summary of review
   - Strengths identified
   - Issues found (categorized: Critical, Major, Minor)
   - Recommendations for improvement
   - Approval status (Approved / Approved with conditions / Rejected)

6. If issues found, create **improvement_suggestions.md** with specific suggestions

7. Share review results via share_knowledge
8. Post message to team that review is complete"""
            )

            files_created = []
            async for msg in self.client.receive_response():
                if hasattr(msg, 'message_type') and msg.message_type == 'tool_use':
                    if hasattr(msg, 'name') and msg.name == 'Write':
                        file_path = msg.input.get('file_path') if hasattr(msg, 'input') else None
                        if file_path:
                            files_created.append(file_path)
                            logger.info(f"  [{self.agent_id}] 📄 Created: {Path(file_path).name}")

            await self._update_status(AgentStatus.IDLE, "Review complete")
            logger.info(f"[{self.agent_id}] ✅ Review complete: {len(files_created)} files created")

            return {
                "success": True,
                "agent_id": self.agent_id,
                "files_created": files_created
            }

        except Exception as e:
            logger.exception(f"[{self.agent_id}] ❌ Error during review")
            await self._update_status(AgentStatus.BLOCKED, f"Error: {str(e)}")
            return {
                "success": False,
                "agent_id": self.agent_id,
                "error": str(e)
            }

    async def execute_role_specific_work(self):
        """Reviewer-specific work - not used in this workflow"""
        pass

    async def execute_task(self, task_description: str) -> Dict[str, Any]:
        """Execute task - required by TeamAgent interface"""
        return await self.review_analysis()


class PublisherAgent(TeamAgent):
    """Publisher agent - creates final deliverables using SDK infrastructure"""

    def __init__(self, agent_id: str, coordination_server):
        config = AgentConfig(
            agent_id=agent_id,
            role=AgentRole.ANALYST,  # Using ANALYST as closest match
            system_prompt=f"""You are {agent_id}, the Technical Publisher.

RESPONSIBILITIES:
- Synthesize analysis and review feedback
- Create final, polished documentation
- Ensure consistency and clarity
- Create executive summaries
- Prepare handoff documentation

WORKFLOW:
1. Check messages from analyst and reviewer
2. Retrieve all shared knowledge
3. Read all documents created by the team
4. Create final deliverables:
   - EXECUTIVE_SUMMARY.md (high-level overview, key requirements, success criteria)
   - FINAL_REQUIREMENTS_SPEC.md (consolidated requirements, acceptance criteria)
   - IMPLEMENTATION_GUIDE.md (architecture recommendations, development phases)
   - PROJECT_INDEX.md (document index and navigation)
5. Share final deliverables info via share_knowledge
6. Post completion message to team

Use coordination tools to gather team's work."""
        )
        super().__init__(config, coordination_server)

    async def publish_deliverables(self) -> Dict[str, Any]:
        """Create final deliverables"""
        await self._update_status(AgentStatus.WORKING, "Creating final deliverables")

        logger.info(f"[{self.agent_id}] 📦 Creating final deliverables...")

        try:
            await self.client.query(
                """Create final deliverables based on all team work:

1. Check all messages (use get_messages) to understand what was created
2. Retrieve all shared knowledge (use get_knowledge)
3. Read all documents created by analyst and reviewer

4. Create these polished final deliverables:

   **EXECUTIVE_SUMMARY.md**:
   - Project overview
   - Key requirements (top 5-7)
   - Success criteria
   - Timeline estimates
   - Resource requirements

   **FINAL_REQUIREMENTS_SPEC.md**:
   - Consolidated functional requirements
   - Non-functional requirements
   - Acceptance criteria
   - Technical constraints
   - Dependencies

   **IMPLEMENTATION_GUIDE.md**:
   - Architecture recommendations
   - Technology stack
   - Development phases
   - Testing strategy
   - Deployment considerations

   **PROJECT_INDEX.md**:
   - File listing with descriptions
   - Document hierarchy
   - Quick navigation guide

5. Share final deliverables summary via share_knowledge
6. Post message that publishing is complete"""
            )

            files_created = []
            async for msg in self.client.receive_response():
                if hasattr(msg, 'message_type') and msg.message_type == 'tool_use':
                    if hasattr(msg, 'name') and msg.name == 'Write':
                        file_path = msg.input.get('file_path') if hasattr(msg, 'input') else None
                        if file_path:
                            files_created.append(file_path)
                            logger.info(f"  [{self.agent_id}] 📄 Created: {Path(file_path).name}")

            await self._update_status(AgentStatus.IDLE, "Publishing complete")
            logger.info(f"[{self.agent_id}] ✅ Publishing complete: {len(files_created)} files created")

            return {
                "success": True,
                "agent_id": self.agent_id,
                "files_created": files_created
            }

        except Exception as e:
            logger.exception(f"[{self.agent_id}] ❌ Error during publishing")
            await self._update_status(AgentStatus.BLOCKED, f"Error: {str(e)}")
            return {
                "success": False,
                "agent_id": self.agent_id,
                "error": str(e)
            }

    async def execute_role_specific_work(self):
        """Publisher-specific work - not used in this workflow"""
        pass

    async def execute_task(self, task_description: str) -> Dict[str, Any]:
        """Execute task - required by TeamAgent interface"""
        return await self.publish_deliverables()


class StandardTeamWorkflow:
    """Orchestrates standard sequential team workflow using SDK"""

    def __init__(self, team_id: str, requirement: str, output_dir: Path):
        self.team_id = team_id
        self.requirement = requirement
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

    async def execute(self) -> Dict[str, Any]:
        """Execute the complete standard team workflow"""

        logger.info("=" * 80)
        logger.info("🚀 SDK-BASED STANDARD TEAM - SEQUENTIAL WORKFLOW")
        logger.info("=" * 80)
        logger.info(f"📝 Requirement: {self.requirement}")
        logger.info(f"📁 Output: {self.output_dir}")
        logger.info("=" * 80)

        start_time = datetime.now()

        # Create team coordinator
        team_config = TeamConfig(
            team_id=self.team_id,
            workspace_path=self.output_dir,
            max_agents=3
        )
        coordinator = TeamCoordinator(team_config)

        # Create coordination server for team communication
        coord_server = coordinator.create_coordination_server()

        logger.info("✅ Team coordinator initialized with MCP server\n")

        # Create agents using SDK
        analyst = AnalystAgent("analyst_1", coord_server)
        reviewer = ReviewerAgent("reviewer_1", coord_server)
        publisher = PublisherAgent("publisher_1", coord_server)

        # Initialize agents
        await analyst.initialize()
        await reviewer.initialize()
        await publisher.initialize()

        logger.info("✅ All agents initialized and connected to MCP server\n")

        # Phase 1: Analysis
        logger.info("=" * 80)
        logger.info("PHASE 1: REQUIREMENT ANALYSIS")
        logger.info("=" * 80)
        analysis_result = await analyst.analyze_requirement(self.requirement)

        if not analysis_result["success"]:
            return self._build_failure_result("Analysis failed", start_time)

        # Phase 2: Review
        logger.info("\n" + "=" * 80)
        logger.info("PHASE 2: REVIEW")
        logger.info("=" * 80)
        review_result = await reviewer.review_analysis()

        if not review_result["success"]:
            return self._build_failure_result("Review failed", start_time)

        # Phase 3: Publishing
        logger.info("\n" + "=" * 80)
        logger.info("PHASE 3: PUBLISHING")
        logger.info("=" * 80)
        publish_result = await publisher.publish_deliverables()

        if not publish_result["success"]:
            return self._build_failure_result("Publishing failed", start_time)

        # Shutdown agents
        await analyst.shutdown()
        await reviewer.shutdown()
        await publisher.shutdown()

        # Build final result
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        all_files = (
            analysis_result.get("files_created", []) +
            review_result.get("files_created", []) +
            publish_result.get("files_created", [])
        )

        result = {
            "success": True,
            "team_id": self.team_id,
            "workflow_type": "sdk_standard_sequential",
            "requirement": self.requirement,
            "executed_at": start_time.isoformat(),
            "completed_at": end_time.isoformat(),
            "duration_seconds": duration,
            "files_created": all_files,
            "file_count": len(all_files),
            "output_dir": str(self.output_dir),
            "coordination_used": "MCP Server",
            "phases": {
                "analysis": analysis_result,
                "review": review_result,
                "publishing": publish_result
            },
            "team_state": {
                "messages": len(coordinator.shared_workspace["messages"]),
                "knowledge_items": len(coordinator.shared_workspace["knowledge"]),
                "artifacts": len(coordinator.shared_workspace["artifacts"])
            }
        }

        # Save execution summary
        self._save_summary(result)

        logger.info("\n" + "=" * 80)
        logger.info("✅ SDK-BASED STANDARD TEAM WORKFLOW COMPLETE!")
        logger.info(f"   Duration: {duration:.2f}s")
        logger.info(f"   Files created: {len(all_files)}")
        logger.info(f"   Team messages: {result['team_state']['messages']}")
        logger.info(f"   Knowledge shared: {result['team_state']['knowledge_items']}")
        logger.info(f"   Output: {self.output_dir}")
        logger.info("=" * 80)

        return result

    def _build_failure_result(self, error: str, start_time: datetime) -> Dict[str, Any]:
        """Build result for failed execution"""
        return {
            "success": False,
            "team_id": self.team_id,
            "error": error,
            "executed_at": start_time.isoformat(),
            "completed_at": datetime.now().isoformat()
        }

    def _save_summary(self, result: Dict[str, Any]):
        """Save execution summary"""
        summary_file = self.output_dir / "workflow_summary.json"
        try:
            with open(summary_file, 'w') as f:
                json.dump(result, f, indent=2, default=str)
            logger.info(f"\n📄 Summary saved: {summary_file}")
        except Exception as e:
            logger.warning(f"⚠️ Failed to save summary: {e}")


async def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="SDK-Based Standard Team - Sequential Workflow with Team Coordination"
    )
    parser.add_argument(
        "--requirement",
        required=True,
        help="User requirement to analyze"
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(settings.output.base_dir if hasattr(settings, 'output') else "./output") / "sdk_standard_team",
        help="Output directory for deliverables"
    )
    parser.add_argument(
        "--team-id",
        default=f"sdk_standard_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        help="Team identifier"
    )

    args = parser.parse_args()

    # Create and execute workflow
    workflow = StandardTeamWorkflow(
        team_id=args.team_id,
        requirement=args.requirement,
        output_dir=args.output
    )

    result = await workflow.execute()

    if result["success"]:
        print(f"\n✅ Workflow completed successfully!")
        print(f"📁 {result['file_count']} files created")
        print(f"💬 {result['team_state']['messages']} team messages exchanged")
        print(f"🧠 {result['team_state']['knowledge_items']} knowledge items shared")
        print(f"📂 Output: {result['output_dir']}")
    else:
        print(f"\n❌ Workflow failed: {result.get('error', 'Unknown error')}")
        sys.exit(1)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    asyncio.run(main())
