"""Tool Sandbox - Execute tools in isolated environment."""
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Set
from .models import Tool, ToolResult

logger = logging.getLogger(__name__)


@dataclass
class SandboxPolicy:
    """Security policy for sandbox."""
    allowed_tools: Set[str] = field(default_factory=set)
    blocked_tools: Set[str] = field(default_factory=set)
    max_execution_time_ms: int = 60000
    max_memory_mb: int = 256
    allow_network: bool = True
    allow_file_write: bool = False
    allowed_paths: List[str] = field(default_factory=list)


class ToolSandbox:
    """Executes tools in a sandboxed environment."""
    
    def __init__(self, policy: SandboxPolicy = None):
        self.policy = policy or SandboxPolicy()
        self._execution_count = 0
    
    def can_execute(self, tool: Tool) -> tuple:
        """Check if tool can be executed under current policy."""
        if tool.name in self.policy.blocked_tools:
            return False, "Tool is blocked"
        
        if self.policy.allowed_tools and tool.name not in self.policy.allowed_tools:
            return False, "Tool not in allowed list"
        
        if tool.timeout_ms > self.policy.max_execution_time_ms:
            return False, "Tool timeout exceeds policy limit"
        
        return True, None
    
    def execute_in_sandbox(self, tool: Tool, params: Dict[str, Any]) -> ToolResult:
        """Execute tool within sandbox constraints."""
        can_exec, reason = self.can_execute(tool)
        if not can_exec:
            return ToolResult(tool_name=tool.name, success=False, error=reason)
        
        self._execution_count += 1
        
        try:
            if tool.handler:
                output = tool.handler(**params)
                return ToolResult(tool_name=tool.name, success=True, output=output)
            return ToolResult(tool_name=tool.name, success=True, output={"executed": True})
        except Exception as e:
            logger.error("Sandbox execution failed: %s", e)
            return ToolResult(tool_name=tool.name, success=False, error=str(e))
    
    def get_stats(self) -> Dict[str, Any]:
        return {"execution_count": self._execution_count, "policy": {
            "max_time_ms": self.policy.max_execution_time_ms,
            "max_memory_mb": self.policy.max_memory_mb,
            "allow_network": self.policy.allow_network,
        }}
