from __future__ import annotations
from typing import Callable, Dict, Any

class SimpleToolBridge:
    def __init__(self) -> None:
        self._registry: Dict[str, Callable[[dict, dict], dict]] = {}

    def register(self, name: str, fn: Callable[[dict, dict], dict]) -> None:
        self._registry[name] = fn

    async def invoke(self, name: str, args: dict, ctx: dict) -> dict:
        if name not in self._registry:
            raise KeyError(f"Tool not found: {name}")
        return self._registry[name](args, ctx)

# Global bridge instance for gateway usage (simple bootstrap)
tool_bridge = SimpleToolBridge()

# Default tool registration
def register_default_tools(workspace_root: str) -> None:
    from execution_platform.tools.fs_tools import WorkspaceSandbox
    ws = WorkspaceSandbox(workspace_root)
    tool_bridge.register("fs_write", ws.fs_write)
    tool_bridge.register("fs_read", ws.fs_read)
    tool_bridge.register("echo", lambda args, ctx: {"echo": args})
