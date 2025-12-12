import subprocess
import logging
import json
from pathlib import Path
from typing import Optional, List, Dict, Any

class ClaudeCLIClient:
    """
    Direct integration with Claude CLI command
    Uses subprocess to interact with installed Claude CLI
    
    FIXED VERSION (MD-3054): Handles stdin=DEVNULL for background execution.
    """

    def __init__(self, cwd: Optional[Path] = None):
        """
        Initialize Claude CLI client

        Args:
            cwd: Working directory (defaults to current directory)
        """
        self.cwd = cwd or Path.cwd()
        # Try to find claude CLI - check common locations
        self.claude_cmd = self._find_claude_cli()
        self.logger = logging.getLogger(self.__class__.__name__)

    def _find_claude_cli(self) -> str:
        """Find claude CLI executable, checking common installation paths."""
        import shutil
        import os

        # First try PATH
        claude_path = shutil.which("claude")
        if claude_path:
            return claude_path

        # Check common NVM installation paths
        home = os.path.expanduser("~")
        nvm_paths = [
            f"{home}/.nvm/versions/node/v22.19.0/bin/claude",
            f"{home}/.nvm/versions/node/v20.18.0/bin/claude",
            f"{home}/.nvm/versions/node/v18.20.0/bin/claude",
        ]

        for path in nvm_paths:
            if os.path.isfile(path) and os.access(path, os.X_OK):
                return path

        # Check global npm path
        global_npm = f"{home}/.local/bin/claude"
        if os.path.isfile(global_npm) and os.access(global_npm, os.X_OK):
            return global_npm

        # Fallback to just "claude" and hope it's in PATH at runtime
        return "claude"

    def query(
        self,
        prompt: str,
        output_format: str = "text",
        allowed_tools: Optional[List[str]] = None,
        disallowed_tools: Optional[List[str]] = None,
        skip_permissions: bool = False,
        timeout: int = 300
    ) -> Dict[str, Any]:
        """
        Send query to Claude CLI

        Args:
            prompt: The prompt to send
            output_format: 'text', 'json', or 'stream-json'
            allowed_tools: List of allowed tools (e.g. ["Edit", "Write", "Bash"])
            disallowed_tools: List of disallowed tools
            skip_permissions: Skip all permission prompts (use with caution)
            timeout: Timeout in seconds

        Returns:
            Response from Claude
        """
        cmd = [self.claude_cmd, "--print"]

        # Add options before prompt
        cmd.extend(["--output-format", output_format])

        if skip_permissions:
            cmd.append("--dangerously-skip-permissions")

        if allowed_tools:
            tools_str = ",".join(allowed_tools)
            cmd.extend(["--allowed-tools", tools_str])

        if disallowed_tools:
            tools_str = ",".join(disallowed_tools)
            cmd.extend(["--disallowed-tools", tools_str])

        # Prompt must be last
        cmd.append("--")  # End of options
        cmd.append(prompt)

        self.logger.info(f"Executing: {' '.join(cmd[:5])}... (prompt truncated)")

        try:
            # MD-3054 FIX: Explicitly set stdin to DEVNULL to prevent EBADF in background
            result = subprocess.run(
                cmd,
                cwd=self.cwd,
                capture_output=True,
                text=True,
                timeout=timeout,
                stdin=subprocess.DEVNULL 
            )

            if result.returncode != 0:
                self.logger.error(f"Claude CLI error: {result.stderr}")
                return {
                    "success": False,
                    "error": result.stderr,
                    "returncode": result.returncode
                }

            if output_format == "json":
                try:
                    data = json.loads(result.stdout)
                    return {
                        "success": True,
                        "output": data,
                        "format": "json"
                    }
                except json.JSONDecodeError as e:
                    self.logger.error(f"JSON decode error: {e}")
                    return {
                        "success": False,
                        "error": f"JSON decode error: {e}",
                        "raw_output": result.stdout
                    }

            return {
                "success": True,
                "output": result.stdout,
                "format": "text"
            }

        except subprocess.TimeoutExpired:
            self.logger.error(f"Claude CLI timeout after {timeout}s")
            return {
                "success": False,
                "error": f"Timeout after {timeout} seconds"
            }
        except Exception as e:
            self.logger.error(f"Claude CLI exception: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    def create_code(
        self,
        requirement: str,
        language: str = "python",
        framework: Optional[str] = None
    ) -> Dict[str, Any]:
        """Generate code based on requirement"""
        framework_text = f" using {framework}" if framework else ""

        prompt = f"Create {language} code{framework_text} for: {requirement}. Include docstrings, type hints, error handling, and follow best practices. Output only the code."
        response = self.query(
            prompt,
            output_format="text",
            skip_permissions=True,
            allowed_tools=["Write", "Edit"]
        )

        if response["success"]:
            return {
                "success": True,
                "code": response["output"],
                "language": language,
                "framework": framework
            }
        else:
            return response

    def analyze_code(
        self,
        code_or_file: str,
        analysis_type: str = "quality"
    ) -> Dict[str, Any]:
        """Analyze code quality, security, or performance"""
        # Check if it's a file path
        if Path(code_or_file).exists():
            prompt = f"""
            Analyze this file for {analysis_type}: {code_or_file}

            Provide:
            1. Score (0-100)
            2. Issues found
            3. Recommendations
            4. Best practices to follow

            Be specific and actionable.
            """
        else:
            prompt = f"""
            Analyze this code for {analysis_type}:

            ```
            {code_or_file}
            ```

            Provide:
            1. Score (0-100)
            2. Issues found
            3. Recommendations
            4. Best practices to follow

            Be specific and actionable.
            """

        response = self.query(
            prompt,
            output_format="text",
            allowed_tools=["Read"]
        )

        if response["success"]:
            return {
                "success": True,
                "analysis": response["output"],
                "analysis_type": analysis_type
            }
        else:
            return response

    def create_template(
        self,
        requirement: str,
        complexity: str = "intermediate"
    ) -> Dict[str, Any]:
        """Create a reusable template"""
        prompt = f"""
        Create a reusable {complexity} template for: {requirement}

        Include:
        1. Complete, working code
        2. Configuration examples
        3. Documentation
        4. Usage examples
        5. Error handling
        6. Type hints
        7. Tests (if applicable)

        Make it production-ready and well-documented.
        Output only the code and documentation.
        """

        response = self.query(
            prompt,
            output_format="text",
            skip_permissions=True,
            allowed_tools=["Write", "Edit"],
            timeout=600  # Longer timeout for templates
        )

        if response["success"]:
            return {
                "success": True,
                "template": response["output"],
                "complexity": complexity,
                "requirement": requirement
            }
        else:
            return response

    def improve_code(
        self,
        code_or_file: str,
        improvement_goals: List[str]
    ) -> Dict[str, Any]:
        """Improve existing code"""
        goals_text = ", ".join(improvement_goals)

        if Path(code_or_file).exists():
            prompt = f"""
            Improve this file focusing on: {goals_text}

            File: {code_or_file}

            Provide the improved version with:
            1. Clear improvements for each goal
            2. Comments explaining changes
            3. Maintained functionality
            4. Better practices applied
            """
        else:
            prompt = f"""
            Improve this code focusing on: {goals_text}

            ```
            {code_or_file}
            ```

            Provide the improved version with:
            1. Clear improvements for each goal
            2. Comments explaining changes
            3. Maintained functionality
            4. Better practices applied
            """

        response = self.query(
            prompt,
            output_format="text",
            skip_permissions=True,
            allowed_tools=["Edit", "Write", "Read"]
        )

        if response["success"]:
            return {
                "success": True,
                "improved_code": response["output"],
                "goals": improvement_goals
            }
        else:
            return response
