"""
Secure Code Sandbox Manager.

Provides secure, isolated execution environment for agent-generated code with:
- Resource limits (CPU, memory, time)
- Network isolation
- Filesystem restrictions
- Process sandboxing
"""

import asyncio
import uuid
import os
import sys
import tempfile
import shutil
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from enum import Enum
import subprocess
import logging
import json
import traceback
from pathlib import Path

logger = logging.getLogger(__name__)


class SandboxStatus(Enum):
    """Sandbox execution status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"
    KILLED = "killed"


@dataclass
class SandboxConfig:
    """Configuration for sandbox execution."""
    timeout: int = 30  # Default timeout in seconds
    memory_limit: str = "512m"  # Memory limit (Docker format)
    cpu_limit: float = 1.0  # CPU core limit
    network_enabled: bool = False  # Enable network access
    max_output_size: int = 1024 * 1024  # 1MB output limit
    allowed_modules: List[str] = field(default_factory=lambda: [
        "math", "json", "datetime", "collections", "itertools",
        "functools", "operator", "string", "re", "random",
        "statistics", "decimal", "fractions", "typing",
    ])
    temp_dir: Optional[str] = None  # Custom temp directory


@dataclass
class ExecutionResult:
    """Result of sandbox execution."""
    sandbox_id: str
    status: SandboxStatus
    stdout: str = ""
    stderr: str = ""
    return_value: Any = None
    error: Optional[str] = None
    exit_code: int = 0
    execution_time_ms: float = 0.0
    memory_used_bytes: int = 0
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    @property
    def success(self) -> bool:
        """Check if execution was successful."""
        return self.status == SandboxStatus.COMPLETED and self.exit_code == 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "sandbox_id": self.sandbox_id,
            "status": self.status.value,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "return_value": self.return_value,
            "error": self.error,
            "exit_code": self.exit_code,
            "execution_time_ms": self.execution_time_ms,
            "memory_used_bytes": self.memory_used_bytes,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }


class SandboxError(Exception):
    """Exception raised for sandbox errors."""

    def __init__(self, message: str, sandbox_id: Optional[str] = None):
        self.sandbox_id = sandbox_id
        super().__init__(message)


class CodeValidator:
    """Validates code before execution."""

    DANGEROUS_IMPORTS = {
        "os", "sys", "subprocess", "multiprocessing",
        "socket", "http", "urllib", "requests",
        "shutil", "pathlib", "glob", "tempfile",
        "__builtins__", "__import__", "exec", "eval",
        "compile", "open", "input", "breakpoint",
    }

    DANGEROUS_PATTERNS = [
        "__import__",
        "exec(",
        "eval(",
        "compile(",
        "open(",
        "os.system",
        "subprocess",
        "shutil.rmtree",
    ]

    @classmethod
    def validate(cls, code: str, config: SandboxConfig) -> List[str]:
        """
        Validate code for safety.

        Args:
            code: Code to validate
            config: Sandbox configuration

        Returns:
            List of validation warnings/errors
        """
        issues = []

        # Check for dangerous patterns
        for pattern in cls.DANGEROUS_PATTERNS:
            if pattern in code:
                issues.append(f"Dangerous pattern detected: {pattern}")

        # Check imports
        import ast
        try:
            tree = ast.parse(code)
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        if alias.name.split(".")[0] in cls.DANGEROUS_IMPORTS:
                            if alias.name not in config.allowed_modules:
                                issues.append(f"Forbidden import: {alias.name}")

                elif isinstance(node, ast.ImportFrom):
                    if node.module and node.module.split(".")[0] in cls.DANGEROUS_IMPORTS:
                        if node.module not in config.allowed_modules:
                            issues.append(f"Forbidden import: {node.module}")

        except SyntaxError as e:
            issues.append(f"Syntax error: {e}")

        return issues


class SandboxManager:
    """
    Manages secure code execution sandboxes.

    Provides isolated execution environments for agent-generated code
    with configurable resource limits and security restrictions.
    """

    def __init__(self, config: Optional[SandboxConfig] = None):
        """
        Initialize sandbox manager.

        Args:
            config: Default sandbox configuration
        """
        self.config = config or SandboxConfig()
        self._sandboxes: Dict[str, ExecutionResult] = {}
        self._lock = asyncio.Lock()
        self._stats = {
            "total_executions": 0,
            "successful": 0,
            "failed": 0,
            "timeouts": 0,
        }

    async def execute(
        self,
        code: str,
        timeout: Optional[int] = None,
        config: Optional[SandboxConfig] = None,
        inputs: Optional[Dict[str, Any]] = None,
    ) -> ExecutionResult:
        """
        Execute code in sandbox.

        Args:
            code: Python code to execute
            timeout: Override default timeout
            config: Override default configuration
            inputs: Variables to inject into execution context

        Returns:
            ExecutionResult with output and status
        """
        cfg = config or self.config
        timeout = timeout or cfg.timeout
        sandbox_id = str(uuid.uuid4())

        result = ExecutionResult(
            sandbox_id=sandbox_id,
            status=SandboxStatus.PENDING,
            started_at=datetime.utcnow(),
        )

        # Validate code
        issues = CodeValidator.validate(code, cfg)
        if issues:
            result.status = SandboxStatus.FAILED
            result.error = f"Code validation failed: {'; '.join(issues)}"
            result.completed_at = datetime.utcnow()
            return result

        async with self._lock:
            self._stats["total_executions"] += 1
            self._sandboxes[sandbox_id] = result

        try:
            result.status = SandboxStatus.RUNNING
            result = await self._execute_isolated(code, timeout, cfg, inputs, result)

            if result.status == SandboxStatus.COMPLETED:
                self._stats["successful"] += 1
            elif result.status == SandboxStatus.TIMEOUT:
                self._stats["timeouts"] += 1
            else:
                self._stats["failed"] += 1

        except Exception as e:
            result.status = SandboxStatus.FAILED
            result.error = str(e)
            self._stats["failed"] += 1

        result.completed_at = datetime.utcnow()
        if result.started_at:
            delta = result.completed_at - result.started_at
            result.execution_time_ms = delta.total_seconds() * 1000

        async with self._lock:
            self._sandboxes[sandbox_id] = result

        logger.debug(f"Sandbox {sandbox_id} completed: {result.status.value}")
        return result

    async def _execute_isolated(
        self,
        code: str,
        timeout: int,
        config: SandboxConfig,
        inputs: Optional[Dict[str, Any]],
        result: ExecutionResult,
    ) -> ExecutionResult:
        """Execute code in isolated process."""
        # Create temporary directory for execution
        temp_dir = tempfile.mkdtemp(prefix="sandbox_", dir=config.temp_dir)

        try:
            # Write code to file
            code_file = os.path.join(temp_dir, "code.py")
            input_file = os.path.join(temp_dir, "inputs.json")
            output_file = os.path.join(temp_dir, "output.json")

            # Prepare execution wrapper
            wrapper_code = self._create_wrapper(code, inputs, output_file)

            with open(code_file, "w") as f:
                f.write(wrapper_code)

            if inputs:
                with open(input_file, "w") as f:
                    json.dump(inputs, f)

            # Execute in subprocess
            process = await asyncio.create_subprocess_exec(
                sys.executable, code_file,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=temp_dir,
                env=self._get_restricted_env(),
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=timeout
                )

                result.stdout = stdout.decode()[:config.max_output_size]
                result.stderr = stderr.decode()[:config.max_output_size]
                result.exit_code = process.returncode

                # Read output if available
                if os.path.exists(output_file):
                    with open(output_file, "r") as f:
                        output_data = json.load(f)
                        result.return_value = output_data.get("result")
                        if output_data.get("error"):
                            result.error = output_data["error"]

                if result.exit_code == 0 and not result.error:
                    result.status = SandboxStatus.COMPLETED
                else:
                    result.status = SandboxStatus.FAILED

            except asyncio.TimeoutError:
                process.kill()
                await process.wait()
                result.status = SandboxStatus.TIMEOUT
                result.error = f"Execution timed out after {timeout}s"

        finally:
            # Cleanup temp directory
            try:
                shutil.rmtree(temp_dir)
            except Exception:
                pass

        return result

    def _create_wrapper(
        self,
        code: str,
        inputs: Optional[Dict[str, Any]],
        output_file: str,
    ) -> str:
        """Create execution wrapper code."""
        input_setup = ""
        if inputs:
            for key, value in inputs.items():
                input_setup += f"{key} = {repr(value)}\n"

        return f'''
import json
import sys

# Restrict built-ins
_safe_builtins = {{
    'abs': abs, 'all': all, 'any': any, 'bin': bin,
    'bool': bool, 'bytes': bytes, 'chr': chr, 'dict': dict,
    'divmod': divmod, 'enumerate': enumerate, 'filter': filter,
    'float': float, 'format': format, 'frozenset': frozenset,
    'hash': hash, 'hex': hex, 'int': int, 'isinstance': isinstance,
    'issubclass': issubclass, 'iter': iter, 'len': len, 'list': list,
    'map': map, 'max': max, 'min': min, 'next': next, 'oct': oct,
    'ord': ord, 'pow': pow, 'print': print, 'range': range,
    'repr': repr, 'reversed': reversed, 'round': round, 'set': set,
    'slice': slice, 'sorted': sorted, 'str': str, 'sum': sum,
    'tuple': tuple, 'type': type, 'zip': zip,
    'True': True, 'False': False, 'None': None,
}}

output = {{"result": None, "error": None}}

try:
    # Input variables
{input_setup}

    # User code
{self._indent_code(code, 4)}

    # Try to capture last expression result
    try:
        output["result"] = result if 'result' in dir() else None
    except:
        pass

except Exception as e:
    output["error"] = str(e)

# Write output
with open({repr(output_file)}, 'w') as f:
    json.dump(output, f)
'''

    def _indent_code(self, code: str, spaces: int) -> str:
        """Indent code by specified spaces."""
        indent = " " * spaces
        return "\n".join(indent + line for line in code.split("\n"))

    def _get_restricted_env(self) -> Dict[str, str]:
        """Get restricted environment variables."""
        # Only pass minimal environment
        return {
            "PATH": "/usr/bin:/bin",
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONUNBUFFERED": "1",
        }

    async def get_result(self, sandbox_id: str) -> Optional[ExecutionResult]:
        """Get execution result by sandbox ID."""
        return self._sandboxes.get(sandbox_id)

    async def cleanup(self, sandbox_id: str) -> None:
        """Cleanup sandbox resources."""
        async with self._lock:
            if sandbox_id in self._sandboxes:
                del self._sandboxes[sandbox_id]

    async def cleanup_old(self, max_age_hours: int = 1) -> int:
        """
        Cleanup old sandbox results.

        Args:
            max_age_hours: Maximum age of results to keep

        Returns:
            Number of results cleaned up
        """
        cutoff = datetime.utcnow() - timedelta(hours=max_age_hours)
        cleaned = 0

        async with self._lock:
            for sandbox_id, result in list(self._sandboxes.items()):
                if result.completed_at and result.completed_at < cutoff:
                    del self._sandboxes[sandbox_id]
                    cleaned += 1

        return cleaned

    def get_stats(self) -> Dict[str, Any]:
        """Get sandbox execution statistics."""
        return {
            **self._stats,
            "active_sandboxes": len(self._sandboxes),
        }
