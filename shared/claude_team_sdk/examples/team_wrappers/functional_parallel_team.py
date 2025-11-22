#!/usr/bin/env python3
"""
Fully Functional Parallel Team - Real Claude API Integration

Multiple agents working concurrently on independent tasks using real Claude API.
Each agent performs actual work and produces real deliverables.

Usage:
    python examples/team_wrappers/functional_parallel_team.py \
        --tasks "Research authentication best practices" \
                "Research database options for user data" \
                "Research API security patterns" \
        --agents 3 \
        --output ./output/parallel

Features:
    - Real concurrent Claude API execution
    - Actual research and file generation
    - Load balancing across agents
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
    from src.claude_team_sdk.resilience import Bulkhead
except ImportError:
    from claude_team_sdk.config import settings
    from claude_team_sdk.resilience import Bulkhead

# Claude Code SDK
try:
    from claude_code_sdk import query, ClaudeCodeOptions
    CLAUDE_SDK_AVAILABLE = True
except ImportError:
    CLAUDE_SDK_AVAILABLE = False
    logging.error("❌ claude_code_sdk not available")

logger = logging.getLogger(__name__)


class TaskContext:
    """Context for a single task execution"""

    def __init__(self, task_id: int, task: str, agent_id: str, output_dir: Path):
        self.task_id = task_id
        self.task = task
        self.agent_id = agent_id
        self.output_dir = output_dir
        self.files_created: List[str] = []
        self.start_time = datetime.now()
        self.end_time: Optional[datetime] = None
        self.success = False
        self.error: Optional[str] = None

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
            "task_id": self.task_id,
            "task": self.task,
            "agent_id": self.agent_id,
            "success": self.success,
            "files_created": self.files_created,
            "duration": self.duration(),
            "error": self.error
        }


class ResearchAgent:
    """Agent that performs actual research using Claude API"""

    def __init__(self, agent_id: str, output_dir: Path):
        self.agent_id = agent_id
        self.output_dir = output_dir
        self.tasks_completed = 0

    async def research(self, task: str, task_id: int) -> TaskContext:
        """Perform actual research on a task using Claude"""
        context = TaskContext(task_id, task, self.agent_id, self.output_dir)

        logger.info(f"[{self.agent_id}] 🔍 Starting research on: {task[:50]}...")

        try:
            system_prompt = """You are a Research Agent specializing in technical research.

Your responsibilities:
- Conduct thorough research on assigned topics
- Analyze current best practices and industry standards
- Identify pros and cons of different approaches
- Provide actionable recommendations
- Create comprehensive research reports

Your research should be detailed, accurate, and production-ready."""

            prompt = f"""Conduct comprehensive research on this topic:

Topic: {task}

Please create a detailed research report with the following structure:

**File**: `task_{task_id}_research_report.md`

Content:
1. **Executive Summary**: Brief overview of findings
2. **Key Findings**: Main discoveries (3-5 points)
3. **Detailed Analysis**: In-depth analysis of the topic
4. **Best Practices**: Industry standards and recommendations
5. **Pros and Cons**: Advantages and disadvantages of different approaches
6. **Recommendations**: Actionable recommendations
7. **References**: Sources and further reading

Use the Write tool to create this research report.
Be thorough and provide production-ready insights."""

            options = ClaudeCodeOptions(
                system_prompt=system_prompt,
                model=settings.claude.model if hasattr(settings, 'claude') else "claude-sonnet-4-20250514",
                cwd=str(self.output_dir),
                permission_mode="auto"
            )

            # Execute research
            async for message in query(prompt=prompt, options=options):
                if hasattr(message, 'message_type') and message.message_type == 'tool_use':
                    if hasattr(message, 'name') and message.name == 'Write':
                        file_path = message.input.get('file_path') if hasattr(message, 'input') else None
                        if file_path:
                            context.add_file(file_path)
                            logger.info(f"  [{self.agent_id}] 📄 Created: {Path(file_path).name}")

            context.mark_complete(success=True)
            self.tasks_completed += 1
            logger.info(f"[{self.agent_id}] ✅ Research complete: {len(context.files_created)} files")

        except Exception as e:
            logger.exception(f"[{self.agent_id}] ❌ Error during research")
            context.mark_complete(success=False, error=str(e))

        return context


class ParallelTeamWorkflow:
    """Orchestrates parallel team execution with real Claude API calls"""

    def __init__(self, team_id: str, tasks: List[str], num_agents: int, output_dir: Path):
        self.team_id = team_id
        self.tasks = tasks
        self.num_agents = num_agents
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Create research agents
        self.agents = [
            ResearchAgent(f"researcher_{i+1}", output_dir)
            for i in range(num_agents)
        ]

        # Bulkhead for concurrency control
        max_concurrent = settings.resilience.bulkhead.max_concurrent_agents if hasattr(settings, 'resilience') else 4
        self.bulkhead = Bulkhead(max_concurrent=max_concurrent, name="parallel_team")

    async def execute(self) -> Dict[str, Any]:
        """Execute parallel team workflow with concurrent task execution"""

        logger.info("=" * 80)
        logger.info("🚀 PARALLEL TEAM WORKFLOW - CONCURRENT EXECUTION")
        logger.info("=" * 80)
        logger.info(f"📋 Total Tasks: {len(self.tasks)}")
        logger.info(f"👥 Agents: {self.num_agents}")
        logger.info(f"📁 Output: {self.output_dir}")
        logger.info("=" * 80)

        start_time = datetime.now()

        # Distribute tasks to agents (round-robin)
        task_assignments = []
        for task_id, task in enumerate(self.tasks):
            agent_idx = task_id % self.num_agents
            agent = self.agents[agent_idx]
            task_assignments.append({
                "task_id": task_id,
                "task": task,
                "agent": agent
            })
            logger.info(f"  Task {task_id}: '{task[:50]}...' → {agent.agent_id}")

        logger.info("\n⚙️  Executing tasks in parallel...\n")

        # Execute all tasks concurrently with bulkhead protection
        async def execute_with_bulkhead(assignment):
            return await self.bulkhead.call(
                assignment["agent"].research,
                assignment["task"],
                assignment["task_id"]
            )

        results = await asyncio.gather(
            *[execute_with_bulkhead(a) for a in task_assignments],
            return_exceptions=True
        )

        # Process results
        successful_tasks = []
        failed_tasks = []

        for i, result in enumerate(results):
            if isinstance(result, Exception):
                failed_tasks.append({
                    "task_id": i,
                    "task": self.tasks[i],
                    "error": str(result),
                    "status": "failed"
                })
                logger.error(f"  ❌ Task {i} failed: {str(result)}")
            elif isinstance(result, TaskContext):
                if result.success:
                    successful_tasks.append(result.to_dict())
                else:
                    failed_tasks.append(result.to_dict())

        # Compile final result
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        all_files = []
        for task_result in successful_tasks:
            all_files.extend(task_result.get("files_created", []))

        result = {
            "success": len(successful_tasks) > 0,
            "team_id": self.team_id,
            "workflow_type": "parallel_concurrent",
            "num_agents": self.num_agents,
            "num_tasks": len(self.tasks),
            "executed_at": start_time.isoformat(),
            "completed_at": end_time.isoformat(),
            "duration_seconds": duration,
            "tasks_per_second": len(self.tasks) / duration if duration > 0 else 0,
            "files_created": all_files,
            "file_count": len(all_files),
            "output_dir": str(self.output_dir),
            "successful_tasks": len(successful_tasks),
            "failed_tasks": len(failed_tasks),
            "success_rate": len(successful_tasks) / len(self.tasks) if self.tasks else 0,
            "tasks": {
                "successful": successful_tasks,
                "failed": failed_tasks
            }
        }

        # Save execution summary
        self._save_summary(result)

        # Create index file
        await self._create_index(successful_tasks)

        logger.info("\n" + "=" * 80)
        logger.info("✅ PARALLEL TEAM WORKFLOW COMPLETE!")
        logger.info(f"   Duration: {duration:.2f}s")
        logger.info(f"   Tasks completed: {len(successful_tasks)}/{len(self.tasks)}")
        logger.info(f"   Success rate: {result['success_rate']*100:.1f}%")
        logger.info(f"   Files created: {len(all_files)}")
        logger.info(f"   Throughput: {result['tasks_per_second']:.2f} tasks/second")
        logger.info(f"   Output: {self.output_dir}")
        logger.info("=" * 80)

        return result

    async def _create_index(self, successful_tasks: List[Dict[str, Any]]):
        """Create an index of all research reports"""
        try:
            index_content = "# Research Reports Index\n\n"
            index_content += f"Generated: {datetime.now().isoformat()}\n\n"
            index_content += "## Completed Research Tasks\n\n"

            for task in successful_tasks:
                index_content += f"### Task {task['task_id']}: {task['task']}\n"
                index_content += f"- Agent: {task['agent_id']}\n"
                index_content += f"- Duration: {task['duration']:.2f}s\n"
                index_content += f"- Files:\n"
                for file in task.get('files_created', []):
                    index_content += f"  - [{Path(file).name}]({file})\n"
                index_content += "\n"

            index_file = self.output_dir / "RESEARCH_INDEX.md"
            with open(index_file, 'w') as f:
                f.write(index_content)

            logger.info(f"\n📄 Research index created: {index_file}")

        except Exception as e:
            logger.warning(f"⚠️ Failed to create index: {e}")

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
        description="Functional Parallel Team - Concurrent Workflow with Real Claude API"
    )
    parser.add_argument(
        "--tasks",
        nargs="+",
        required=True,
        help="List of research tasks to execute in parallel"
    )
    parser.add_argument(
        "--agents",
        type=int,
        default=3,
        help="Number of research agents to create"
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(settings.output.base_dir if hasattr(settings, 'output') else "./output") / "parallel_team",
        help="Output directory for results"
    )
    parser.add_argument(
        "--team-id",
        default=f"parallel_team_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        help="Team identifier"
    )

    args = parser.parse_args()

    # Validate
    max_agents = settings.team.max_agents if hasattr(settings, 'team') else 10
    if args.agents > max_agents:
        logger.warning(f"⚠️ Requested {args.agents} agents but max is {max_agents}")
        args.agents = max_agents

    # Create and execute workflow
    workflow = ParallelTeamWorkflow(
        team_id=args.team_id,
        tasks=args.tasks,
        num_agents=args.agents,
        output_dir=args.output
    )

    result = await workflow.execute()

    if result["success"]:
        print(f"\n✅ Workflow completed!")
        print(f"📁 {result['file_count']} files created")
        print(f"📊 {result['successful_tasks']}/{result['num_tasks']} tasks completed")
        print(f"📂 Output: {result['output_dir']}")
    else:
        print(f"\n❌ Workflow failed - no tasks completed")
        sys.exit(1)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    asyncio.run(main())
