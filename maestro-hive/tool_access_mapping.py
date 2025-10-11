"""
Tool Access Mapping for SDLC Personas

Maps Claude's built-in tools to specific personas based on their roles.
Implements RBAC (Role-Based Access Control) for tool usage.
"""

from typing import Dict, List
from enum import Enum


class Tool(Enum):
    """Available tools in Claude Code"""
    # File Operations
    READ = "Read"
    WRITE = "Write"
    EDIT = "Edit"
    GLOB = "Glob"
    GREP = "Grep"

    # System Operations
    BASH = "Bash"

    # Research Tools
    WEB_SEARCH = "WebSearch"
    WEB_FETCH = "WebFetch"

    # TODO Management
    TODO_WRITE = "TodoWrite"

    # Git Operations
    GIT = "Git"  # Through Bash

    # Notebook Operations
    NOTEBOOK_EDIT = "NotebookEdit"

    # Task Management
    TASK = "Task"  # For spawning sub-agents


class AccessLevel(Enum):
    """Access levels for tools"""
    NONE = 0
    READ_ONLY = 1
    WRITE = 2
    FULL = 3


class ToolAccessMapping:
    """
    Maps personas to tools with access levels

    Based on SDLC roles and responsibilities
    """

    @staticmethod
    def get_tool_access() -> Dict[str, Dict[str, AccessLevel]]:
        """
        Returns tool access mapping for each persona

        Format: {
            "persona_id": {
                "tool_name": AccessLevel.WRITE,
                ...
            }
        }
        """
        return {
            "requirement_analyst": {
                # Research tools for understanding requirements
                Tool.WEB_SEARCH.value: AccessLevel.FULL,
                Tool.WEB_FETCH.value: AccessLevel.FULL,

                # Read existing code/docs to understand context
                Tool.READ.value: AccessLevel.FULL,
                Tool.GLOB.value: AccessLevel.FULL,
                Tool.GREP.value: AccessLevel.FULL,

                # Write requirements documents
                Tool.WRITE.value: AccessLevel.FULL,
                Tool.EDIT.value: AccessLevel.FULL,

                # Task management
                Tool.TODO_WRITE.value: AccessLevel.FULL,
                Tool.TASK.value: AccessLevel.FULL,

                # Limited bash (only for analysis commands)
                Tool.BASH.value: AccessLevel.READ_ONLY,
            },

            "ui_ux_designer": {
                # Research design patterns and UI libraries
                Tool.WEB_SEARCH.value: AccessLevel.FULL,
                Tool.WEB_FETCH.value: AccessLevel.FULL,

                # Read existing UI code
                Tool.READ.value: AccessLevel.FULL,
                Tool.GLOB.value: AccessLevel.FULL,
                Tool.GREP.value: AccessLevel.FULL,

                # Create design documents and wireframes
                Tool.WRITE.value: AccessLevel.FULL,
                Tool.EDIT.value: AccessLevel.FULL,

                # Task management
                Tool.TODO_WRITE.value: AccessLevel.FULL,

                # No bash access needed
                Tool.BASH.value: AccessLevel.NONE,
            },

            "solution_architect": {
                # Research technologies and architectures
                Tool.WEB_SEARCH.value: AccessLevel.FULL,
                Tool.WEB_FETCH.value: AccessLevel.FULL,

                # Read entire codebase
                Tool.READ.value: AccessLevel.FULL,
                Tool.GLOB.value: AccessLevel.FULL,
                Tool.GREP.value: AccessLevel.FULL,

                # Write architecture documents
                Tool.WRITE.value: AccessLevel.FULL,
                Tool.EDIT.value: AccessLevel.FULL,

                # Analysis commands
                Tool.BASH.value: AccessLevel.READ_ONLY,

                # Task management and spawning sub-tasks
                Tool.TODO_WRITE.value: AccessLevel.FULL,
                Tool.TASK.value: AccessLevel.FULL,
            },

            "security_specialist": {
                # Research security vulnerabilities and best practices
                Tool.WEB_SEARCH.value: AccessLevel.FULL,
                Tool.WEB_FETCH.value: AccessLevel.FULL,

                # Read code for security review
                Tool.READ.value: AccessLevel.FULL,
                Tool.GLOB.value: AccessLevel.FULL,
                Tool.GREP.value: AccessLevel.FULL,

                # Write security reviews and recommendations
                Tool.WRITE.value: AccessLevel.FULL,
                Tool.EDIT.value: AccessLevel.FULL,

                # Run security scanning tools
                Tool.BASH.value: AccessLevel.FULL,

                # Task management
                Tool.TODO_WRITE.value: AccessLevel.FULL,
                Tool.TASK.value: AccessLevel.FULL,
            },

            "backend_developer": {
                # Research APIs and libraries
                Tool.WEB_SEARCH.value: AccessLevel.FULL,
                Tool.WEB_FETCH.value: AccessLevel.FULL,

                # Full code access
                Tool.READ.value: AccessLevel.FULL,
                Tool.GLOB.value: AccessLevel.FULL,
                Tool.GREP.value: AccessLevel.FULL,
                Tool.WRITE.value: AccessLevel.FULL,
                Tool.EDIT.value: AccessLevel.FULL,

                # Full bash access for testing, installing packages, etc.
                Tool.BASH.value: AccessLevel.FULL,

                # Git operations
                Tool.GIT.value: AccessLevel.FULL,

                # Task management
                Tool.TODO_WRITE.value: AccessLevel.FULL,
                Tool.TASK.value: AccessLevel.FULL,
            },

            "frontend_developer": {
                # Research UI libraries and frameworks
                Tool.WEB_SEARCH.value: AccessLevel.FULL,
                Tool.WEB_FETCH.value: AccessLevel.FULL,

                # Full code access
                Tool.READ.value: AccessLevel.FULL,
                Tool.GLOB.value: AccessLevel.FULL,
                Tool.GREP.value: AccessLevel.FULL,
                Tool.WRITE.value: AccessLevel.FULL,
                Tool.EDIT.value: AccessLevel.FULL,

                # Full bash access for npm/yarn commands
                Tool.BASH.value: AccessLevel.FULL,

                # Git operations
                Tool.GIT.value: AccessLevel.FULL,

                # Task management
                Tool.TODO_WRITE.value: AccessLevel.FULL,
                Tool.TASK.value: AccessLevel.FULL,
            },

            "devops_engineer": {
                # Research DevOps tools and practices
                Tool.WEB_SEARCH.value: AccessLevel.FULL,
                Tool.WEB_FETCH.value: AccessLevel.FULL,

                # Read all code and configs
                Tool.READ.value: AccessLevel.FULL,
                Tool.GLOB.value: AccessLevel.FULL,
                Tool.GREP.value: AccessLevel.FULL,

                # Write infrastructure configs
                Tool.WRITE.value: AccessLevel.FULL,
                Tool.EDIT.value: AccessLevel.FULL,

                # FULL bash access for deployment, docker, k8s, etc.
                Tool.BASH.value: AccessLevel.FULL,

                # Git operations
                Tool.GIT.value: AccessLevel.FULL,

                # Task management
                Tool.TODO_WRITE.value: AccessLevel.FULL,
                Tool.TASK.value: AccessLevel.FULL,
            },

            "qa_engineer": {
                # Research testing frameworks and best practices
                Tool.WEB_SEARCH.value: AccessLevel.FULL,
                Tool.WEB_FETCH.value: AccessLevel.FULL,

                # Read code for testing
                Tool.READ.value: AccessLevel.FULL,
                Tool.GLOB.value: AccessLevel.FULL,
                Tool.GREP.value: AccessLevel.FULL,

                # Write test code
                Tool.WRITE.value: AccessLevel.FULL,
                Tool.EDIT.value: AccessLevel.FULL,

                # Run tests
                Tool.BASH.value: AccessLevel.FULL,

                # Task management for tracking bugs
                Tool.TODO_WRITE.value: AccessLevel.FULL,
                Tool.TASK.value: AccessLevel.FULL,
            },

            "technical_writer": {
                # Research documentation best practices
                Tool.WEB_SEARCH.value: AccessLevel.FULL,
                Tool.WEB_FETCH.value: AccessLevel.FULL,

                # Read code to document it
                Tool.READ.value: AccessLevel.FULL,
                Tool.GLOB.value: AccessLevel.FULL,
                Tool.GREP.value: AccessLevel.FULL,

                # Write documentation
                Tool.WRITE.value: AccessLevel.FULL,
                Tool.EDIT.value: AccessLevel.FULL,

                # Limited bash for generating docs
                Tool.BASH.value: AccessLevel.READ_ONLY,

                # Notebook editing for tutorials
                Tool.NOTEBOOK_EDIT.value: AccessLevel.FULL,

                # Task management
                Tool.TODO_WRITE.value: AccessLevel.FULL,
            },

            "deployment_specialist": {
                # Research deployment strategies
                Tool.WEB_SEARCH.value: AccessLevel.FULL,
                Tool.WEB_FETCH.value: AccessLevel.FULL,

                # Read all code and configs
                Tool.READ.value: AccessLevel.FULL,
                Tool.GLOB.value: AccessLevel.FULL,
                Tool.GREP.value: AccessLevel.FULL,

                # Write deployment guides
                Tool.WRITE.value: AccessLevel.FULL,
                Tool.EDIT.value: AccessLevel.FULL,

                # Full bash for deployment operations
                Tool.BASH.value: AccessLevel.FULL,

                # Git operations for releases
                Tool.GIT.value: AccessLevel.FULL,

                # Task management
                Tool.TODO_WRITE.value: AccessLevel.FULL,
                Tool.TASK.value: AccessLevel.FULL,
            },
        }

    @staticmethod
    def get_allowed_tools(persona_id: str) -> List[str]:
        """
        Get list of tools a persona can use

        Returns only tools with WRITE or FULL access
        """
        access_map = ToolAccessMapping.get_tool_access()
        persona_access = access_map.get(persona_id, {})

        allowed = []
        for tool, level in persona_access.items():
            if level in [AccessLevel.WRITE, AccessLevel.FULL]:
                allowed.append(tool)

        return allowed

    @staticmethod
    def can_use_tool(persona_id: str, tool_name: str) -> bool:
        """Check if persona can use a specific tool"""
        access_map = ToolAccessMapping.get_tool_access()
        persona_access = access_map.get(persona_id, {})

        access_level = persona_access.get(tool_name, AccessLevel.NONE)
        return access_level != AccessLevel.NONE

    @staticmethod
    def get_access_level(persona_id: str, tool_name: str) -> AccessLevel:
        """Get access level for a persona-tool combination"""
        access_map = ToolAccessMapping.get_tool_access()
        persona_access = access_map.get(persona_id, {})

        return persona_access.get(tool_name, AccessLevel.NONE)

    @staticmethod
    def generate_tool_permissions_prompt(persona_id: str) -> str:
        """
        Generate a prompt section describing tool permissions

        This can be added to the agent's system prompt
        """
        allowed_tools = ToolAccessMapping.get_allowed_tools(persona_id)
        access_map = ToolAccessMapping.get_tool_access()
        persona_access = access_map.get(persona_id, {})

        prompt = f"""
YOUR TOOL PERMISSIONS:

You have access to the following tools:
"""
        for tool in allowed_tools:
            level = persona_access.get(tool, AccessLevel.NONE)

            if level == AccessLevel.FULL:
                prompt += f"\n✅ {tool} - FULL ACCESS"
            elif level == AccessLevel.WRITE:
                prompt += f"\n✅ {tool} - WRITE ACCESS"
            elif level == AccessLevel.READ_ONLY:
                prompt += f"\n📖 {tool} - READ ONLY"

        prompt += "\n\nUSE THESE TOOLS to accomplish your tasks."

        return prompt


# Example usage
if __name__ == "__main__":
    print("=" * 80)
    print("TOOL ACCESS MAPPING FOR SDLC PERSONAS")
    print("=" * 80)

    personas = [
        "requirement_analyst",
        "solution_architect",
        "backend_developer",
        "security_specialist",
        "devops_engineer"
    ]

    for persona in personas:
        print(f"\n{persona.upper()}")
        print("-" * 80)

        tools = ToolAccessMapping.get_allowed_tools(persona)
        print(f"Allowed tools: {', '.join(tools)}")

        # Show access levels
        access_map = ToolAccessMapping.get_tool_access()
        persona_access = access_map.get(persona, {})

        print("\nDetailed Access:")
        for tool, level in persona_access.items():
            if level != AccessLevel.NONE:
                print(f"  - {tool}: {level.name}")

        # Show generated prompt
        print("\nGenerated Prompt Section:")
        print(ToolAccessMapping.generate_tool_permissions_prompt(persona))
