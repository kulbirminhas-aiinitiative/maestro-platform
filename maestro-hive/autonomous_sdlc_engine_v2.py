#!/usr/bin/env python3
"""
Autonomous SDLC Engine V2 - Tool-Based Approach

Key improvements over V1:
1. Agents use Claude's built-in tools (Write, Edit, Read, Bash) directly
2. No hardcoded templates - pure tool-based execution
3. No fragile text parsing - tools create structured outputs
4. Dynamic workflow with state machine
5. Enhanced context with structured deliverables

This is TRUE autonomy - agents manipulate files and run commands directly.
"""

import asyncio
import os
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional
from enum import Enum
import json

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
sys.path.insert(0, str(Path(__file__).parent))

# Import personas and team organization
import personas
from team_organization import (
    get_deliverables_for_persona,
    get_agents_for_phase,
    get_workflow_transitions,
    SDLCPhase
)

# Import tool access mapping
from tool_access_mapping import ToolAccessMapping

# Import configuration
from config import CLAUDE_CONFIG, WORKFLOW_CONFIG, OUTPUT_CONFIG

# Import Claude Code SDK
try:
    from claude_code_sdk import query, ClaudeCodeOptions
    CLAUDE_SDK_AVAILABLE = True
except ImportError:
    CLAUDE_SDK_AVAILABLE = False
    print("⚠️  Claude Code SDK not available. Install: pip install claude-code-sdk")


class PhaseStatus(Enum):
    """Status of a phase execution"""
    SUCCESS = "success"
    NEEDS_REVISION = "needs_revision"
    BLOCKED = "blocked"
    FAILED = "failed"


class ProjectContext:
    """
    Enhanced context object that tracks project state

    Instead of a simple dict, this maintains:
    - Structured deliverables (tech stack, architecture, etc.)
    - File manifest with status
    - Phase execution history
    - Inter-agent communication
    """

    def __init__(self, requirement: str, output_dir: str):
        self.requirement = requirement
        self.output_dir = output_dir
        self.deliverables = {}  # Structured deliverables by type
        self.files = {}  # File manifest: {path: {status, created_by, ...}}
        self.phase_history = []  # List of completed phases
        self.agent_messages = []  # Inter-agent communication

    def add_deliverable(self, deliverable_type: str, content: Any, created_by: str):
        """Add a structured deliverable"""
        self.deliverables[deliverable_type] = {
            "content": content,
            "created_by": created_by,
            "timestamp": asyncio.get_event_loop().time()
        }

    def register_file(self, file_path: str, created_by: str, file_type: str):
        """Register a file in the manifest"""
        self.files[file_path] = {
            "created_by": created_by,
            "file_type": file_type,
            "status": "created"
        }

    def get_tech_stack(self) -> Optional[Dict]:
        """Query the tech stack (if defined by architect)"""
        return self.deliverables.get("tech_stack", {}).get("content")

    def get_architecture(self) -> Optional[Dict]:
        """Query the architecture (if defined by architect)"""
        return self.deliverables.get("architecture", {}).get("content")

    def add_phase(self, phase_name: str, agent_id: str, status: PhaseStatus):
        """Record phase execution"""
        self.phase_history.append({
            "phase": phase_name,
            "agent": agent_id,
            "status": status.value,
            "timestamp": asyncio.get_event_loop().time()
        })

    def to_dict(self) -> Dict:
        """Export context for agents"""
        return {
            "requirement": self.requirement,
            "deliverables": self.deliverables,
            "files": list(self.files.keys()),
            "phase_history": self.phase_history,
            "tech_stack": self.get_tech_stack(),
            "architecture": self.get_architecture()
        }


class ToolBasedSDLCAgent:
    """
    Tool-based autonomous SDLC agent

    This agent doesn't generate text that we parse. Instead:
    - It uses Claude's built-in tools (Write, Edit, Read, Bash)
    - It directly creates files and executes commands
    - It produces structured deliverables

    NO HARDCODING. TRUE AUTONOMY.
    """

    def __init__(
        self,
        persona_id: str,
        persona_config: Dict[str, Any],
        output_dir: str
    ):
        self.persona_id = persona_id
        self.persona_config = persona_config
        self.output_dir = output_dir

    async def execute_phase(
        self,
        context: ProjectContext,
        deliverables_needed: List[str]
    ) -> PhaseStatus:
        """
        Execute phase using tools

        Returns:
            PhaseStatus indicating success or need for revision
        """

        print(f"\n{'='*80}")
        print(f"🤖 {self.persona_config['name']} ({self.persona_id})")
        print(f"{'='*80}")

        if not CLAUDE_SDK_AVAILABLE:
            print("⚠️  Claude SDK not available - cannot execute autonomously")
            return PhaseStatus.BLOCKED

        # Build tool-based prompt
        prompt = self._build_tool_prompt(context, deliverables_needed)

        # Configure options with persona's system prompt (NO HARDCODING)
        options = ClaudeCodeOptions(
            system_prompt=self.persona_config['system_prompt'],
            model=CLAUDE_CONFIG["model"],
            cwd=self.output_dir,
            permission_mode=CLAUDE_CONFIG["permission_mode"]
        )

        print(f"💭 {self.persona_config['name']} executing with tools...")

        try:
            # Execute with Claude - agent will use tools
            files_created = []
            structured_outputs = {}

            async for message in query(prompt=prompt, options=options):
                # Monitor tool usage
                if hasattr(message, 'type'):
                    if message.type == 'tool_use':
                        tool_name = getattr(message, 'name', 'unknown')
                        print(f"   🔧 Using tool: {tool_name}")

                        # Track file operations
                        if tool_name == 'Write':
                            file_path = getattr(message, 'input', {}).get('file_path', '')
                            if file_path:
                                files_created.append(file_path)
                                context.register_file(file_path, self.persona_id, "created")

                    elif message.type == 'text':
                        # Extract structured deliverables from text
                        content = str(getattr(message, 'content', ''))
                        self._extract_structured_outputs(content, structured_outputs)

            # Register deliverables in context
            for deliverable_type, content in structured_outputs.items():
                context.add_deliverable(deliverable_type, content, self.persona_id)

            print(f"   ✅ Completed: {len(files_created)} files, {len(structured_outputs)} deliverables")

            return PhaseStatus.SUCCESS

        except Exception as e:
            print(f"   ❌ Error: {e}")
            return PhaseStatus.FAILED

    def _build_tool_prompt(
        self,
        context: ProjectContext,
        deliverables_needed: List[str]
    ) -> str:
        """
        Build a prompt that instructs the agent to USE TOOLS

        This is the key difference from V1 - we don't ask for text,
        we ask the agent to perform actions using tools.
        """

        context_dict = context.to_dict()

        # Get tool permissions for this persona
        tool_permissions = ToolAccessMapping.generate_tool_permissions_prompt(self.persona_id)

        prompt = f"""You are a {self.persona_config['name']} working on a software project.

ORIGINAL REQUIREMENT:
{context.requirement}

CONTEXT FROM PREVIOUS PHASES:
{json.dumps(context_dict, indent=2)}

YOUR RESPONSIBILITIES:
{json.dumps(self.persona_config['responsibilities'], indent=2)}

YOUR DELIVERABLES FOR THIS PHASE:
{json.dumps(deliverables_needed, indent=2)}

{tool_permissions}

CRITICAL INSTRUCTIONS:

1. **USE YOUR ALLOWED TOOLS** - Don't just describe what to do, actually do it:
   - Use the Write tool to create new files
   - Use the Edit tool to modify existing files
   - Use the Read tool to inspect existing work
   - Use WebSearch/WebFetch to research best practices and technologies
   - Use the Bash tool to run commands (if you have access)

2. **Work incrementally**:
   - Read the context to understand what previous agents have done
   - Build on their work
   - Create files that integrate with the existing architecture

3. **Produce structured outputs**:
   - When making technical decisions (e.g., choosing a tech stack), format them as JSON
   - Example: {{
       "tech_stack": {{
           "backend": "Node.js + Express",
           "frontend": "Next.js 14",
           "database": "PostgreSQL"
       }}
   }}

4. **Be thorough**:
   - Create complete, working files
   - Add proper error handling
   - Follow best practices for your role

OUTPUT DIRECTORY: {self.output_dir}

Now execute your responsibilities using the tools. Start working!
"""
        return prompt

    def _extract_structured_outputs(self, text: str, outputs: Dict):
        """
        Extract structured deliverables from agent's text output

        Looks for JSON blocks that represent decisions/designs
        """
        try:
            # Try to find JSON blocks
            import re
            json_pattern = r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}'
            matches = re.findall(json_pattern, text)

            for match in matches:
                try:
                    data = json.loads(match)
                    # Identify the type of deliverable
                    for key in ['tech_stack', 'architecture', 'database_design', 'api_endpoints']:
                        if key in data:
                            outputs[key] = data[key]
                except json.JSONDecodeError:
                    continue
        except Exception:
            pass


class DynamicWorkflowEngine:
    """
    Dynamic workflow engine with state machine

    NO HARDCODING - All configuration pulled from team_organization.py

    Replaces the static linear workflow with:
    - State-based transitions
    - Iteration support (e.g., QA finds bug → back to dev)
    - Conditional branching
    """

    def __init__(self):
        # Load workflow transitions from central config (NO HARDCODING)
        self.states = get_workflow_transitions()

        # Build state→agents mapping from phase structure (NO HARDCODING)
        self.state_agents = {}
        for phase in SDLCPhase:
            # Skip cross-cutting phases that don't map directly to states
            if phase in [SDLCPhase.SECURITY, SDLCPhase.DOCUMENTATION]:
                continue

            state_name = phase.value
            self.state_agents[state_name] = get_agents_for_phase(phase)

        # Add special states that aren't in SDLCPhase enum
        self.state_agents["security_review"] = get_agents_for_phase(SDLCPhase.SECURITY)
        self.state_agents["documentation"] = get_agents_for_phase(SDLCPhase.DOCUMENTATION)

    def get_next_state(
        self,
        current_state: str,
        status: PhaseStatus
    ) -> Optional[str]:
        """
        Determine next state based on current state and status

        Implements the state machine logic
        """
        state_config = self.states.get(current_state)
        if not state_config:
            return None

        if status == PhaseStatus.SUCCESS:
            # Move forward
            next_states = state_config["next"]
            return next_states[0] if next_states else None

        elif status == PhaseStatus.NEEDS_REVISION:
            # Loop back
            loop_targets = state_config["can_loop_to"]
            return loop_targets[-1] if loop_targets else None

        else:
            # Blocked or failed - stay in current state
            return current_state

    def get_agents_for_state(self, state: str) -> List[str]:
        """Get list of agents that work in this state"""
        return self.state_agents.get(state, [])


class AutonomousSDLCEngineV2:
    """
    Autonomous SDLC Engine V2

    Key improvements:
    1. Tool-based execution (no hardcoding)
    2. Dynamic workflow (state machine)
    3. Enhanced context (structured deliverables)
    """

    def __init__(self, output_dir: str = None):
        # Use configured default if not specified (NO HARDCODING)
        self.output_dir = output_dir or OUTPUT_CONFIG["default_output_dir"]
        os.makedirs(self.output_dir, exist_ok=True)

        # Initialize tool-based agents
        self.agents = self._initialize_agents()

        # Initialize workflow engine
        self.workflow = DynamicWorkflowEngine()

    def _initialize_agents(self) -> Dict[str, ToolBasedSDLCAgent]:
        """
        Initialize all SDLC agents - NO HARDCODING

        Uses personas.SDLCPersonas.get_all_personas() to dynamically
        discover all available personas
        """
        agents = {}

        # Get all persona definitions from central source (NO HARDCODING)
        all_personas = personas.SDLCPersonas.get_all_personas()

        for persona_id, persona_config in all_personas.items():
            agent = ToolBasedSDLCAgent(
                persona_id=persona_config['id'],
                persona_config=persona_config,
                output_dir=self.output_dir
            )
            agents[persona_config['id']] = agent

        return agents

    async def execute(self, requirement: str) -> Dict[str, Any]:
        """
        Execute autonomous SDLC with dynamic workflow

        Args:
            requirement: User's requirement (any complexity)

        Returns:
            Execution summary with all artifacts
        """

        print("="*80)
        print("🚀 AUTONOMOUS SDLC ENGINE V2 - TOOL-BASED EXECUTION")
        print("="*80)
        print(f"\n📝 Requirement: {requirement}")
        print(f"📁 Output: {self.output_dir}\n")

        # Initialize enhanced context
        context = ProjectContext(requirement, self.output_dir)

        # Start workflow
        current_state = "requirements"
        iteration = 0
        max_iterations = WORKFLOW_CONFIG["max_iterations"]  # NO HARDCODING

        while current_state != "complete" and iteration < max_iterations:
            iteration += 1

            print(f"\n{'='*80}")
            print(f"STATE: {current_state.upper()} (Iteration {iteration})")
            print(f"{'='*80}")

            # Get agents for this state
            agent_ids = self.workflow.get_agents_for_state(current_state)

            # Execute all agents in this state
            state_status = PhaseStatus.SUCCESS
            for agent_id in agent_ids:
                agent = self.agents.get(agent_id)
                if not agent:
                    continue

                # Define deliverables based on agent role
                deliverables = self._get_deliverables_for_agent(agent_id)

                # Execute agent
                status = await agent.execute_phase(context, deliverables)

                # Record in context
                context.add_phase(current_state, agent_id, status)

                # If any agent fails, mark state as failed
                if status in [PhaseStatus.FAILED, PhaseStatus.NEEDS_REVISION]:
                    state_status = status

            # Determine next state
            next_state = self.workflow.get_next_state(current_state, state_status)

            if next_state == current_state:
                print(f"\n⚠️  Workflow stuck in state: {current_state}")
                break

            current_state = next_state

        print(f"\n{'='*80}")
        print("✅ AUTONOMOUS SDLC COMPLETE!")
        print(f"{'='*80}")
        print(f"📦 Files created: {len(context.files)}")
        print(f"📋 Deliverables: {len(context.deliverables)}")
        print(f"🔄 Iterations: {iteration}")
        print(f"📁 Location: {self.output_dir}\n")

        return {
            "success": True,
            "project_dir": self.output_dir,
            "files": list(context.files.keys()),
            "deliverables": context.deliverables,
            "iterations": iteration
        }

    def _get_deliverables_for_agent(self, agent_id: str) -> List[str]:
        """
        Get deliverables for an agent from centralized team organization

        No hardcoding - uses team_organization.get_deliverables_for_persona()
        """
        return get_deliverables_for_persona(agent_id)


async def main():
    """
    Example: Run V2 engine with tool-based execution
    """

    if not CLAUDE_SDK_AVAILABLE:
        print("❌ Claude SDK required for V2 engine")
        print("   Install: pip install claude-code-sdk")
        return

    # Create V2 engine
    engine = AutonomousSDLCEngineV2(output_dir="./generated_project_v2")

    # Execute with ANY requirement
    requirement = """
    Create an improved website like mannam.co.uk, with advanced SEO optimization
    and AI Chatbot (OpenAI) - key to be shared later
    """

    result = await engine.execute(requirement)

    if result["success"]:
        print("\n🎉 SUCCESS! Project generated by tool-based autonomous agents.")
        print(f"\nFiles created: {len(result['files'])}")
        print(f"Location: {result['project_dir']}")


if __name__ == "__main__":
    asyncio.run(main())
