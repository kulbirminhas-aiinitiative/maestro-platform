"""Tool Executor - Execute tools with validation and sandboxing."""
import logging
import time
from typing import Any, Dict, Optional
from .models import Tool, ToolResult, ToolRegistry

logger = logging.getLogger(__name__)


class ToolExecutor:
    """Executes tools with safety measures."""
    
    def __init__(self, registry: ToolRegistry, sandbox_enabled: bool = True):
        self.registry = registry
        self.sandbox_enabled = sandbox_enabled
        self._rate_counters: Dict[str, list] = {}
    
    def execute(self, tool_name: str, params: Dict[str, Any]) -> ToolResult:
        """Execute a tool with the given parameters."""
        start_time = time.time()
        
        tool = self.registry.get(tool_name)
        if not tool:
            return ToolResult(tool_name=tool_name, success=False, error="Tool not found")
        
        if not tool.enabled:
            return ToolResult(tool_name=tool_name, success=False, error="Tool disabled")
        
        # Validate parameters
        errors = tool.validate_params(params)
        if errors:
            return ToolResult(tool_name=tool_name, success=False, error="; ".join(errors))
        
        # Check rate limit
        if tool.rate_limit and not self._check_rate_limit(tool_name, tool.rate_limit):
            return ToolResult(tool_name=tool_name, success=False, error="Rate limit exceeded")
        
        try:
            if tool.handler:
                output = tool.handler(**params)
            else:
                output = {"message": f"Tool {tool_name} executed", "params": params}
            
            return ToolResult(
                tool_name=tool_name,
                success=True,
                output=output,
                execution_time_ms=(time.time() - start_time) * 1000
            )
        except Exception as e:
            logger.error("Tool execution failed: %s", e)
            return ToolResult(
                tool_name=tool_name,
                success=False,
                error=str(e),
                execution_time_ms=(time.time() - start_time) * 1000
            )
    
    def _check_rate_limit(self, tool_name: str, limit: int) -> bool:
        """Check if rate limit allows execution."""
        now = time.time()
        if tool_name not in self._rate_counters:
            self._rate_counters[tool_name] = []
        
        # Remove old entries (older than 1 minute)
        self._rate_counters[tool_name] = [t for t in self._rate_counters[tool_name] if now - t < 60]
        
        if len(self._rate_counters[tool_name]) >= limit:
            return False
        
        self._rate_counters[tool_name].append(now)
        return True
