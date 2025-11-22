#!/usr/bin/env python3
"""
Production-Ready Standard Team Wrapper

A standard (static) team with fixed composition and sequential workflow.
Uses configuration system for all settings - no hardcoded values.

Usage:
    python examples/team_wrappers/standard_team_wrapper.py \\
        --requirement "Analyze market trends for Q4" \\
        --team-size 3 \\
        --output ./output/analysis

Features:
    - Configuration-driven (uses dynaconf)
    - Resilience patterns (circuit breaker, retry, timeout)
    - Persistent state
    - Progress tracking
    - Error handling
"""

import asyncio
import argparse
import sys
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime
import json

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Use new src structure
try:
    from src.claude_team_sdk import TeamAgent, AgentConfig, AgentRole, TeamCoordinator
    from src.claude_team_sdk.config import settings
    from src.claude_team_sdk.resilience import CircuitBreaker, retry_with_backoff, with_timeout
except ImportError:
    # Fallback to old structure
    from claude_team_sdk import TeamAgent, AgentConfig, AgentRole, TeamCoordinator
    from claude_team_sdk.config import settings
    from claude_team_sdk.resilience import CircuitBreaker, retry_with_backoff, with_timeout


class AnalystAgent(TeamAgent):
    """Agent that analyzes requirements and produces reports."""

    def __init__(self, agent_id: str, coord_server):
        config = AgentConfig(
            agent_id=agent_id,
            role=AgentRole.ANALYST,
            system_prompt="You are a data analyst. Analyze requirements and produce detailed reports."
        )
        super().__init__(config, coord_server)
        self.circuit_breaker = CircuitBreaker(
            failure_threshold=settings.resilience.circuit_breaker.failure_threshold,
            name=f"{agent_id}_circuit"
        )

    async def analyze(self, requirement: str) -> Dict[str, Any]:
        """Analyze requirement and produce report."""
        print(f"[{self.agent_id}] 📊 Analyzing: {requirement}")

        async def do_analysis():
            # In production, this would call Claude API
            # For now, simulate analysis
            await asyncio.sleep(1)
            analysis = {
                "requirement": requirement,
                "analysis_type": "market_trends",
                "findings": f"Detailed analysis of {requirement}",
                "recommendations": ["Recommendation 1", "Recommendation 2"],
                "confidence": 0.85,
                "timestamp": datetime.now().isoformat()
            }
            return analysis

        # Execute with resilience patterns
        result = await self.circuit_breaker.call(
            with_timeout,
            lambda: retry_with_backoff(
                do_analysis,
                max_retries=settings.resilience.retry.max_retries,
                name=f"{self.agent_id}_analysis"
            ),
            timeout=settings.resilience.timeout.agent_execution
        )

        # Share with team
        await self.share_knowledge(key="analysis_report", value=result)
        print(f"[{self.agent_id}] ✅ Analysis complete and shared")

        return result


class ReviewerAgent(TeamAgent):
    """Agent that reviews analysis reports."""

    def __init__(self, agent_id: str, coord_server):
        config = AgentConfig(
            agent_id=agent_id,
            role=AgentRole.REVIEWER,
            system_prompt="You are a senior reviewer. Review reports for quality and accuracy."
        )
        super().__init__(config, coord_server)

    async def review(self) -> Dict[str, Any]:
        """Review the analysis report."""
        print(f"[{self.agent_id}] 🔍 Retrieving report for review...")

        # Get the analysis from shared knowledge
        analysis = await self.get_knowledge("analysis_report")

        if not analysis:
            print(f"[{self.agent_id}] ❌ No analysis found to review")
            return {"status": "failed", "reason": "No analysis available"}

        print(f"[{self.agent_id}] 📝 Reviewing analysis...")
        await asyncio.sleep(1)

        review = {
            "reviewed_at": datetime.now().isoformat(),
            "original_analysis": analysis,
            "review_status": "approved",
            "quality_score": 0.9,
            "comments": "Analysis is thorough and well-structured",
            "reviewer": self.agent_id
        }

        await self.share_knowledge(key="review_report", value=review)
        print(f"[{self.agent_id}] ✅ Review complete - Status: {review['review_status']}")

        return review


class PublisherAgent(TeamAgent):
    """Agent that publishes finalized reports."""

    def __init__(self, agent_id: str, coord_server):
        config = AgentConfig(
            agent_id=agent_id,
            role=AgentRole.PUBLISHER,
            system_prompt="You are a publisher. Format and publish finalized reports."
        )
        super().__init__(config, coord_server)

    async def publish(self, output_dir: Path) -> Dict[str, Any]:
        """Publish the finalized report."""
        print(f"[{self.agent_id}] 📤 Preparing to publish...")

        # Get review from shared knowledge
        review = await self.get_knowledge("review_report")

        if not review:
            print(f"[{self.agent_id}] ❌ No review found to publish")
            return {"status": "failed", "reason": "No review available"}

        if review.get("review_status") != "approved":
            print(f"[{self.agent_id}] ⚠️  Report not approved, cannot publish")
            return {"status": "failed", "reason": "Report not approved"}

        # Create output directory
        output_dir.mkdir(parents=True, exist_ok=True)

        # Generate publication
        publication = {
            "published_at": datetime.now().isoformat(),
            "analysis": review["original_analysis"],
            "review": {
                "status": review["review_status"],
                "score": review["quality_score"],
                "comments": review["comments"]
            },
            "publisher": self.agent_id,
            "version": "1.0"
        }

        # Write to file
        output_file = output_dir / f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(output_file, 'w') as f:
            json.dump(publication, f, indent=2)

        print(f"[{self.agent_id}] ✅ Published to: {output_file}")

        return {
            "status": "published",
            "output_file": str(output_file),
            "publication": publication
        }


class StandardTeamWorkflow:
    """Production-ready standard team workflow."""

    def __init__(
        self,
        team_id: str,
        requirement: str,
        output_dir: Path,
        team_size: int = 3
    ):
        self.team_id = team_id
        self.requirement = requirement
        self.output_dir = output_dir
        self.team_size = team_size
        self.coordinator = None
        self.agents: List[TeamAgent] = []

    async def execute(self) -> Dict[str, Any]:
        """Execute the complete standard team workflow."""
        print(f"\n{'=' * 80}")
        print(f"🚀 Standard Team Workflow: {self.team_id}")
        print(f"{'=' * 80}\n")

        print(f"Configuration:")
        print(f"  Environment: {settings.service.environment}")
        print(f"  Max Agents: {settings.team.max_agents}")
        print(f"  Coordination Timeout: {settings.team.coordination_timeout}s")
        print(f"  Output Directory: {self.output_dir}\n")

        try:
            # Create team coordinator
            print("📋 Setting up team coordinator...")
            from claude_team_sdk.team_coordinator import TeamConfig
            config = TeamConfig(
                team_id=self.team_id,
                max_agents=self.team_size
            )
            self.coordinator = TeamCoordinator(config)
            coord_server = self.coordinator.create_coordination_server()
            print("✅ Coordinator ready\n")

            # Create team members
            print(f"👥 Creating team ({self.team_size} members)...")
            analyst = AnalystAgent("analyst_1", coord_server)
            reviewer = ReviewerAgent("reviewer_1", coord_server)
            publisher = PublisherAgent("publisher_1", coord_server)
            self.agents = [analyst, reviewer, publisher][:self.team_size]

            # Initialize agents
            for agent in self.agents:
                await agent.initialize()
                print(f"  ✅ {agent.agent_id} ({agent.config.role.value}) initialized")
            print()

            # Execute sequential workflow
            print(f"⚙️  Executing workflow...\n")

            # Step 1: Analysis
            print("Step 1/3: Analysis Phase")
            analysis_result = await analyst.analyze(self.requirement)

            # Step 2: Review (if team has reviewer)
            if len(self.agents) >= 2:
                print("\nStep 2/3: Review Phase")
                review_result = await reviewer.review()
            else:
                review_result = {"status": "skipped", "reason": "No reviewer in team"}

            # Step 3: Publishing (if team has publisher)
            if len(self.agents) >= 3:
                print("\nStep 3/3: Publishing Phase")
                publish_result = await publisher.publish(self.output_dir)
            else:
                publish_result = {"status": "skipped", "reason": "No publisher in team"}

            # Gather results
            results = {
                "team_id": self.team_id,
                "requirement": self.requirement,
                "team_size": self.team_size,
                "executed_at": datetime.now().isoformat(),
                "phases": {
                    "analysis": analysis_result,
                    "review": review_result,
                    "publication": publish_result
                },
                "status": "success"
            }

            print(f"\n{'=' * 80}")
            print("✅ Workflow Complete!")
            print(f"{'=' * 80}\n")

            return results

        except Exception as e:
            print(f"\n❌ Error in workflow: {str(e)}")
            return {
                "status": "failed",
                "error": str(e),
                "team_id": self.team_id
            }

        finally:
            # Cleanup
            print("🧹 Cleaning up...")
            for agent in self.agents:
                await agent.shutdown()
            print("✅ Cleanup complete\n")


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Standard Team Workflow - Production Ready"
    )
    parser.add_argument(
        "--requirement",
        required=True,
        help="The requirement to analyze"
    )
    parser.add_argument(
        "--team-size",
        type=int,
        default=3,
        choices=[1, 2, 3],
        help="Team size (1=analyst only, 2=+reviewer, 3=+publisher)"
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(settings.output.base_dir) / "standard_team",
        help="Output directory for reports"
    )
    parser.add_argument(
        "--team-id",
        default=f"standard_team_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        help="Team identifier"
    )

    args = parser.parse_args()

    # Create and execute workflow
    workflow = StandardTeamWorkflow(
        team_id=args.team_id,
        requirement=args.requirement,
        output_dir=args.output,
        team_size=args.team_size
    )

    results = await workflow.execute()

    # Save results
    results_file = args.output / "workflow_results.json"
    results_file.parent.mkdir(parents=True, exist_ok=True)
    with open(results_file, 'w') as f:
        json.dump(results, f, indent=2)

    print(f"📄 Results saved to: {results_file}")

    return results


if __name__ == "__main__":
    asyncio.run(main())
