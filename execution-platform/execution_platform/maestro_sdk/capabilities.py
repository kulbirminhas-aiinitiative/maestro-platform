from __future__ import annotations
from typing import Dict, Any

CAPABILITIES: Dict[str, Dict[str, Any]] = {
    "mock": {
        "streaming": True,
        "tool_calling": "simulated",
        "json_mode": False,
        "vision": False,
    },
    "anthropic": {
        "streaming": True,
        "tool_calling": "native",
        "json_mode": True,
        "vision": True,
    },
    "openai": {
        "streaming": True,
        "tool_calling": "native",
        "json_mode": True,
        "vision": True,
    },
    "gemini": {
        "streaming": False,
        "tool_calling": "limited",
        "json_mode": True,
        "vision": True,
    },
}
