#!/usr/bin/env python3
"""
Fully Functional Standard Team - Real Claude API Integration

A sequential workflow team that uses Claude Code SDK to perform actual work:
- Analyst: Analyzes requirements and creates analysis documents
- Reviewer: Reviews the analysis and provides feedback
- Publisher: Creates final deliverables and documentation

Usage:
    python examples/team_wrappers/functional_standard_team.py \
        --requirement "Build a user authentication system with JWT" \
        --output ./output/standard

Features:
    - Real Claude API calls (no simulation)
    - Actual file generation
    - Sequential workflow with knowledge transfer
    - Configuration-driven
    - Production-ready output
"""

import asyncio
import argparse
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime
import json
import logging

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Configuration
try:
    from src.claude_team_sdk.config import settings
except ImportError:
    from claude_team_sdk.config import settings

# Claude Code SDK
try:
    from claude_code_sdk import query, ClaudeCodeOptions
    CLAUDE_SDK_AVAILABLE = True
except ImportError:
    CLAUDE_SDK_AVAILABLE = False
    logging.error("❌ claude_code_sdk not available - install with: pip install claude-code-sdk")

logger = logging.getLogger(__name__)


class AgentContext:
    """Context for a single agent's execution"""

    def __init__(self, agent_id: str, role: str, output_dir: Path):
        self.agent_id = agent_id
        self.role = role
        self.output_dir = output_dir
        self.files_created: List[str] = []
        self.start_time = datetime.now()
        self.end_time: Optional[datetime] = None
        self.success = False
        self.error: Optional[str] = None
        self.output_data: Dict[str, Any] = {}

    def mark_complete(self, success: bool = True, error: Optional[str] = None):
        self.end_time = datetime.now()
        self.success = success
        self.error = error

    def duration(self) -> float:
        if self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return 0

    def add_file(self, file_path: str):
        self.files_created.append(file_path)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "role": self.role,
            "success": self.success,
            "files_created": self.files_created,
            "duration": self.duration(),
            "error": self.error,
            "output_data": self.output_data
        }


class AnalystAgent:
    """Analyst agent - analyzes requirements and creates detailed specifications"""

    def __init__(self, agent_id: str, output_dir: Path):
        self.agent_id = agent_id
        self.output_dir = output_dir
        self.role = "analyst"

    async def analyze(self, requirement: str) -> AgentContext:
        """Analyze requirements and create analysis documents"""
        context = AgentContext(self.agent_id, self.role, self.output_dir)

        logger.info(f"\n[{self.agent_id}] 🔍 Starting requirement analysis...")

        try:
            system_prompt = """You are a Requirements Analyst.

Your responsibilities:
- Analyze user requirements thoroughly
- Identify functional and non-functional requirements
- Create detailed requirement specifications
- Identify potential risks and assumptions
- Create user stories and acceptance criteria

Create comprehensive analysis documents that will guide the development team."""

            prompt = f"""Analyze this requirement and create comprehensive documentation:

Requirement: {requirement}

Please create the following deliverables:

1. **requirements_analysis.md**: Detailed analysis including:
   - Functional requirements (numbered list)
   - Non-functional requirements (performance, security, scalability)
   - Assumptions and constraints
   - Risk assessment

2. **user_stories.md**: User stories in format:
   - As a [user type], I want [goal] so that [benefit]
   - Acceptance criteria for each story

3. **technical_scope.md**: Technical scope including:
   - Key components needed
   - Technologies required
   - Integration points
   - Data models

Use the Write tool to create these files in the output directory.
Be detailed and production-ready in your analysis."""

            options = ClaudeCodeOptions(
                system_prompt=system_prompt,
                model=settings.claude.model if hasattr(settings, 'claude') else "claude-sonnet-4-20250514",
                cwd=str(self.output_dir),
                permission_mode="auto"
            )

            # Execute with Claude
            async for message in query(prompt=prompt, options=options):
                # Track files created
                if hasattr(message, 'message_type') and message.message_type == 'tool_use':
                    if hasattr(message, 'name') and message.name == 'Write':
                        file_path = message.input.get('file_path') if hasattr(message, 'input') else None
                        if file_path:
                            context.add_file(file_path)
                            logger.info(f"  📄 Created: {file_path}")

            context.mark_complete(success=True)
            logger.info(f"[{self.agent_id}] ✅ Analysis complete: {len(context.files_created)} files created")

        except Exception as e:
            logger.exception(f"[{self.agent_id}] ❌ Error during analysis")
            context.mark_complete(success=False, error=str(e))

        return context


class ReviewerAgent:
    """Reviewer agent - reviews analysis and provides feedback"""

    def __init__(self, agent_id: str, output_dir: Path):
        self.agent_id = agent_id
        self.output_dir = output_dir
        self.role = "reviewer"

    async def review(self, analysis_context: AgentContext) -> AgentContext:
        """Review analysis documents and provide feedback"""
        context = AgentContext(self.agent_id, self.role, self.output_dir)

        logger.info(f"\n[{self.agent_id}] 📋 Starting review process...")

        try:
            system_prompt = """You are a Technical Reviewer.

Your responsibilities:
- Review requirement analysis for completeness and accuracy
- Identify gaps or ambiguities
- Verify technical feasibility
- Ensure requirements are testable
- Provide constructive feedback
- Suggest improvements

Create detailed review reports that improve the quality of deliverables."""

            # Build context from analyst's work
            files_to_review = "\n".join(f"- {f}" for f in analysis_context.files_created)

            prompt = f"""Review the analysis documents created by the Analyst:

Files to review:
{files_to_review}

Please:
1. Read each file using the Read tool
2. Analyze for:
   - Completeness
   - Clarity and specificity
   - Technical feasibility
   - Missing requirements
   - Potential risks or issues

3. Create a **review_report.md** that includes:
   - Summary of review
   - Strengths identified
   - Issues found (categorized by severity: Critical, Major, Minor)
   - Recommendations for improvement
   - Approval status (Approved / Approved with conditions / Rejected)

4. If you find issues, create an **improvement_suggestions.md** with:
   - Specific suggestions for each issue
   - Additional requirements to consider
   - Best practices recommendations

Use the Read tool to review files and Write tool to create reports."""

            options = ClaudeCodeOptions(
                system_prompt=system_prompt,
                model=settings.claude.model if hasattr(settings, 'claude') else "claude-sonnet-4-20250514",
                cwd=str(self.output_dir),
                permission_mode="auto"
            )

            # Execute review
            async for message in query(prompt=prompt, options=options):
                if hasattr(message, 'message_type') and message.message_type == 'tool_use':
                    if hasattr(message, 'name') and message.name == 'Write':
                        file_path = message.input.get('file_path') if hasattr(message, 'input') else None
                        if file_path:
                            context.add_file(file_path)
                            logger.info(f"  📄 Created: {file_path}")

            context.mark_complete(success=True)
            logger.info(f"[{self.agent_id}] ✅ Review complete: {len(context.files_created)} files created")

        except Exception as e:
            logger.exception(f"[{self.agent_id}] ❌ Error during review")
            context.mark_complete(success=False, error=str(e))

        return context


class PublisherAgent:
    """Publisher agent - creates final deliverables and documentation"""

    def __init__(self, agent_id: str, output_dir: Path):
        self.agent_id = agent_id
        self.output_dir = output_dir
        self.role = "publisher"

    async def publish(self, analysis_context: AgentContext, review_context: AgentContext) -> AgentContext:
        """Create final deliverables and documentation"""
        context = AgentContext(self.agent_id, self.role, self.output_dir)

        logger.info(f"\n[{self.agent_id}] 📦 Creating final deliverables...")

        try:
            system_prompt = """You are a Technical Publisher.

Your responsibilities:
- Synthesize analysis and review feedback
- Create final, polished documentation
- Ensure consistency and clarity
- Create executive summaries
- Organize deliverables professionally
- Prepare handoff documentation

Create publication-ready deliverables that stakeholders can use immediately."""

            all_files = analysis_context.files_created + review_context.files_created
            files_context = "\n".join(f"- {f}" for f in all_files)

            prompt = f"""Create the final deliverables based on the analysis and review:

Available files:
{files_context}

Please create:

1. **EXECUTIVE_SUMMARY.md**: High-level summary including:
   - Project overview
   - Key requirements (top 5-7)
   - Success criteria
   - Timeline estimates
   - Resource requirements

2. **FINAL_REQUIREMENTS_SPEC.md**: Complete requirements specification:
   - Consolidated functional requirements
   - Non-functional requirements
   - Acceptance criteria
   - Technical constraints
   - Dependencies

3. **IMPLEMENTATION_GUIDE.md**: Guide for developers:
   - Architecture recommendations
   - Technology stack
   - Development phases
   - Testing strategy
   - Deployment considerations

4. **PROJECT_INDEX.md**: Index of all deliverables:
   - File listing with descriptions
   - Document hierarchy
   - Quick navigation guide

Read the existing files, synthesize the content, incorporate review feedback,
and create these polished final deliverables."""

            options = ClaudeCodeOptions(
                system_prompt=system_prompt,
                model=settings.claude.model if hasattr(settings, 'claude') else "claude-sonnet-4-20250514",
                cwd=str(self.output_dir),
                permission_mode="auto"
            )

            # Execute publishing
            async for message in query(prompt=prompt, options=options):
                if hasattr(message, 'message_type') and message.message_type == 'tool_use':
                    if hasattr(message, 'name') and message.name == 'Write':
                        file_path = message.input.get('file_path') if hasattr(message, 'input') else None
                        if file_path:
                            context.add_file(file_path)
                            logger.info(f"  📄 Created: {file_path}")

            context.mark_complete(success=True)
            logger.info(f"[{self.agent_id}] ✅ Publishing complete: {len(context.files_created)} files created")

        except Exception as e:
            logger.exception(f"[{self.agent_id}] ❌ Error during publishing")
            context.mark_complete(success=False, error=str(e))

        return context


class StandardTeamWorkflow:
    """Orchestrates the standard sequential team workflow"""

    def __init__(self, team_id: str, requirement: str, output_dir: Path):
        self.team_id = team_id
        self.requirement = requirement
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Create agents
        self.analyst = AnalystAgent("analyst_1", output_dir)
        self.reviewer = ReviewerAgent("reviewer_1", output_dir)
        self.publisher = PublisherAgent("publisher_1", output_dir)

    async def execute(self) -> Dict[str, Any]:
        """Execute the complete standard team workflow"""

        logger.info("=" * 80)
        logger.info("🚀 STANDARD TEAM WORKFLOW - SEQUENTIAL EXECUTION")
        logger.info("=" * 80)
        logger.info(f"📝 Requirement: {self.requirement}")
        logger.info(f"📁 Output: {self.output_dir}")
        logger.info("=" * 80)

        start_time = datetime.now()

        # Phase 1: Analysis
        logger.info("\n" + "=" * 80)
        logger.info("PHASE 1: REQUIREMENT ANALYSIS")
        logger.info("=" * 80)
        analysis_context = await self.analyst.analyze(self.requirement)

        if not analysis_context.success:
            return self._build_failure_result("Analysis phase failed", start_time)

        # Phase 2: Review
        logger.info("\n" + "=" * 80)
        logger.info("PHASE 2: REVIEW")
        logger.info("=" * 80)
        review_context = await self.reviewer.review(analysis_context)

        if not review_context.success:
            return self._build_failure_result("Review phase failed", start_time)

        # Phase 3: Publishing
        logger.info("\n" + "=" * 80)
        logger.info("PHASE 3: PUBLISHING")
        logger.info("=" * 80)
        publish_context = await self.publisher.publish(analysis_context, review_context)

        if not publish_context.success:
            return self._build_failure_result("Publishing phase failed", start_time)

        # Build final result
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        all_files = (
            analysis_context.files_created +
            review_context.files_created +
            publish_context.files_created
        )

        result = {
            "success": True,
            "team_id": self.team_id,
            "workflow_type": "standard_sequential",
            "requirement": self.requirement,
            "executed_at": start_time.isoformat(),
            "completed_at": end_time.isoformat(),
            "duration_seconds": duration,
            "files_created": all_files,
            "file_count": len(all_files),
            "output_dir": str(self.output_dir),
            "phases": {
                "analysis": analysis_context.to_dict(),
                "review": review_context.to_dict(),
                "publishing": publish_context.to_dict()
            }
        }

        # Save execution summary
        self._save_summary(result)

        logger.info("\n" + "=" * 80)
        logger.info("✅ STANDARD TEAM WORKFLOW COMPLETE!")
        logger.info(f"   Duration: {duration:.2f}s")
        logger.info(f"   Files created: {len(all_files)}")
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
    if not CLAUDE_SDK_AVAILABLE:
        print("❌ Error: claude_code_sdk is not available")
        print("Install with: pip install claude-code-sdk")
        return

    parser = argparse.ArgumentParser(
        description="Functional Standard Team - Sequential Workflow with Real Claude API"
    )
    parser.add_argument(
        "--requirement",
        required=True,
        help="User requirement to analyze and implement"
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(settings.output.base_dir if hasattr(settings, 'output') else "./output") / "standard_team",
        help="Output directory for deliverables"
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
        output_dir=args.output
    )

    result = await workflow.execute()

    if result["success"]:
        print(f"\n✅ Workflow completed successfully!")
        print(f"📁 {result['file_count']} files created")
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
