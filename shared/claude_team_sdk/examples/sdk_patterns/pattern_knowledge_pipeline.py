#!/usr/bin/env python3
"""
SDK Pattern: Knowledge Pipeline

Sequential stages where each agent builds on previous knowledge and artifacts.
Knowledge and value accumulate through the pipeline.

Usage:
    python examples/sdk_patterns/pattern_knowledge_pipeline.py \
        --requirement "Build payment processing API" \
        --stages research design implement test \
        --output ./output/pipeline

How it works:
1. Stage 1 (Research): Creates research artifacts
2. Stage 2 (Design): Builds on research, creates design artifacts
3. Stage 3 (Implement): Uses design, creates code artifacts
4. Stage 4 (Test): Tests implementation, creates test artifacts
5. Each stage shares knowledge for next stage

SDK Features Used:
- share_knowledge (knowledge accumulation)
- store_artifact (artifact pipeline)
- get_knowledge / get_artifacts (building on previous work)
- Sequential coordination with context
"""

import asyncio
import argparse
import sys
from pathlib import Path
from typing import List
from datetime import datetime
import json
import logging

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.claude_team_sdk import TeamAgent, AgentConfig, AgentRole, AgentStatus, TeamCoordinator
from src.claude_team_sdk.coordination.team_coordinator import TeamConfig
from src.claude_team_sdk.config import settings

logger = logging.getLogger(__name__)


class PipelineStageAgent(TeamAgent):
    """Agent representing one stage in knowledge pipeline"""

    def __init__(self, agent_id: str, coordination_server, stage: str, role: AgentRole):
        self.stage = stage

        stage_prompts = {
            "research": """You are the Research stage.

INPUTS: Original requirement
TASK: Research and analyze the requirement
OUTPUTS:
- research_findings.md: Comprehensive research
- technical_requirements.md: Detailed technical requirements
- technology_recommendations.md: Recommended tech stack

KNOWLEDGE TO SHARE:
- key_requirements: Critical requirements identified
- tech_stack: Recommended technologies
- constraints: Technical constraints discovered

Use Write tool for files, share_knowledge for key findings.""",

            "design": """You are the Design stage.

INPUTS: Research findings and requirements (use get_knowledge and get_artifacts)
TASK: Create architectural design based on research
OUTPUTS:
- architecture_design.md: System architecture
- api_specification.md: API design
- data_models.md: Data models

KNOWLEDGE TO SHARE:
- architecture_decisions: Key architectural choices
- api_design: API structure
- data_schema: Data model decisions

Build on research stage's knowledge. Reference their findings.""",

            "implement": """You are the Implementation stage.

INPUTS: Design artifacts and decisions (use get_knowledge, get_artifacts)
TASK: Implement based on design
OUTPUTS:
- Source code files (actual implementation)
- configuration files
- IMPLEMENTATION_NOTES.md: Implementation details

KNOWLEDGE TO SHARE:
- implementation_approach: How you implemented it
- code_structure: Code organization
- dependencies: Required dependencies

Follow the design. Reference design decisions.""",

            "test": """You are the Testing stage.

INPUTS: Implementation artifacts (use get_knowledge, get_artifacts)
TASK: Create comprehensive test suite
OUTPUTS:
- Test files (unit, integration)
- test_plan.md: Testing strategy
- TEST_RESULTS.md: Test execution template

KNOWLEDGE TO SHARE:
- test_coverage: Coverage achieved
- test_strategy: Testing approach
- issues_found: Any issues discovered

Test the implementation. Reference code structure."""
        }

        config = AgentConfig(
            agent_id=agent_id,
            role=role,
            auto_claim_tasks=False,
            system_prompt=f"""You are {agent_id}, the {stage.upper()} stage agent.

{stage_prompts.get(stage, 'Process this stage')}

CRITICAL:
1. ALWAYS check previous stages (use get_knowledge and get_artifacts)
2. BUILD ON their work, don't duplicate
3. REFERENCE their decisions in your output
4. SHARE your key decisions via share_knowledge
5. CREATE actual files with Write tool

This is a pipeline - each stage adds value to previous stages' work."""
        )
        super().__init__(config, coordination_server)

    async def execute_stage(self, requirement: str, coordinator: TeamCoordinator):
        """Execute this pipeline stage"""
        await self._update_status(AgentStatus.WORKING, f"Executing {self.stage}")

        logger.info(f"[{self.agent_id}] ⚙️  Executing {self.stage} stage...")

        # Get context from previous stages
        knowledge = coordinator.shared_workspace["knowledge"]
        artifacts = coordinator.shared_workspace["artifacts"]

        context = f"Original requirement: {requirement}\n\n"

        if knowledge:
            context += "KNOWLEDGE FROM PREVIOUS STAGES:\n"
            for key, item in knowledge.items():
                context += f"- {key}: {item['value'][:200]}...\n"

        if artifacts:
            context += "\nARTIFACTS FROM PREVIOUS STAGES:\n"
            for aid, artifact in artifacts.items():
                context += f"- {artifact['name']} ({artifact['type']})\n"

        await self.client.query(
            f"""Execute {self.stage.upper()} stage:

{context}

YOUR TASK:
1. Review all previous work (use get_knowledge and get_artifacts)
2. Build upon previous stages' outputs
3. Create your stage's deliverables (use Write tool)
4. Share key decisions (use share_knowledge)
5. Post message to next stage with handoff notes

Be thorough and reference previous work."""
        )

        files_created = []
        async for msg in self.client.receive_response():
            if hasattr(msg, 'message_type') and msg.message_type == 'tool_use':
                if hasattr(msg, 'name') and msg.name == 'Write':
                    file_path = msg.input.get('file_path') if hasattr(msg, 'input') else None
                    if file_path:
                        files_created.append(file_path)
                        logger.info(f"  [{self.agent_id}] 📄 Created: {Path(file_path).name}")

        await self._update_status(AgentStatus.IDLE, f"{self.stage} complete")
        logger.info(f"[{self.agent_id}] ✅ {self.stage} stage complete")

        return files_created

    async def execute_task(self, task_description: str):
        return {"success": True}

    async def execute_role_specific_work(self):
        pass


async def run_pipeline_pattern(requirement: str, stages: List[str], output_dir: Path):
    """Execute knowledge pipeline pattern"""

    print("=" * 80)
    print("🔄 KNOWLEDGE PIPELINE PATTERN")
    print("=" * 80)
    print(f"Requirement: {requirement}")
    print(f"Pipeline Stages: {' → '.join(stages)}")
    print(f"Output: {output_dir}")
    print("=" * 80)
    print()

    start_time = datetime.now()
    output_dir.mkdir(parents=True, exist_ok=True)

    # Create coordinator
    team_config = TeamConfig(
        team_id=f"pipeline_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        workspace_path=output_dir,
        max_agents=len(stages)
    )
    coordinator = TeamCoordinator(team_config)
    coord_server = coordinator.create_coordination_server()

    # Map stages to roles
    stage_roles = {
        "research": AgentRole.ANALYST,
        "design": AgentRole.ARCHITECT,
        "implement": AgentRole.DEVELOPER,
        "test": AgentRole.TESTER
    }

    pipeline_results = {}

    # Execute pipeline sequentially
    for i, stage in enumerate(stages, 1):
        print(f"\n{'=' * 60}")
        print(f"STAGE {i}/{len(stages)}: {stage.upper()}")
        print(f"{'=' * 60}")

        role = stage_roles.get(stage, AgentRole.DEVELOPER)
        agent = PipelineStageAgent(f"{stage}_agent", coord_server, stage, role)
        await agent.initialize()

        files = await agent.execute_stage(requirement, coordinator)

        state = await coordinator.get_workspace_state()
        print(f"  ✅ Files created: {len(files)}")
        print(f"  📚 Knowledge items: {state['knowledge_items']}")
        print(f"  📦 Artifacts: {state['artifacts']}")

        pipeline_results[stage] = {
            "files_created": files,
            "knowledge_items": state['knowledge_items'],
            "artifacts": state['artifacts']
        }

        await agent.shutdown()

    # Final results
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    final_state = await coordinator.get_workspace_state()

    all_files = []
    for stage_result in pipeline_results.values():
        all_files.extend(stage_result['files_created'])

    result = {
        "pattern": "knowledge_pipeline",
        "requirement": requirement,
        "stages": stages,
        "duration_seconds": duration,
        "total_files": len(all_files),
        "final_knowledge_items": final_state['knowledge_items'],
        "final_artifacts": final_state['artifacts'],
        "pipeline_results": pipeline_results,
        "output_dir": str(output_dir)
    }

    with open(output_dir / "pipeline_results.json", 'w') as f:
        json.dump(result, f, indent=2, default=str)

    print()
    print("=" * 80)
    print("✅ KNOWLEDGE PIPELINE COMPLETE")
    print("=" * 80)
    print(f"Duration: {duration:.2f}s")
    print(f"Stages: {len(stages)}")
    print(f"Files Created: {len(all_files)}")
    print(f"Knowledge Accumulated: {result['final_knowledge_items']} items")
    print(f"Artifacts Created: {result['final_artifacts']}")
    print(f"Output: {output_dir}")
    print("=" * 80)

    return result


async def main():
    parser = argparse.ArgumentParser(description="Knowledge Pipeline Pattern")
    parser.add_argument("--requirement", required=True, help="Project requirement")
    parser.add_argument("--stages", nargs="+",
                       choices=["research", "design", "implement", "test"],
                       default=["research", "design", "implement", "test"],
                       help="Pipeline stages in order")
    parser.add_argument("--output", type=Path,
                       default=Path(settings.output.base_dir if hasattr(settings, 'output') else "./output") / "pipeline",
                       help="Output directory")

    args = parser.parse_args()

    result = await run_pipeline_pattern(args.requirement, args.stages, args.output)

    if result['total_files'] > 0:
        print(f"\n✅ Success! Check {result['output_dir']} for pipeline output")
    else:
        print(f"\n❌ No files created")
        sys.exit(1)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(message)s')
    asyncio.run(main())
