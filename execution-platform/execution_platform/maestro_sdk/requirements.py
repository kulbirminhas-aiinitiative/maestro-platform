from __future__ import annotations
from typing import Optional, Dict
from .capabilities import CAPABILITIES

class RequirementError(Exception):
    pass

def ensure_requirements(provider: str, requires: Optional[Dict[str, str]] = None):
    if not requires:
        return
    caps = CAPABILITIES.get(provider, {})
    for k, v in requires.items():
        if k == 'tool_calling':
            wanted = v
            have = caps.get('tool_calling')
            ok = (wanted == 'native' and have == 'native') or (wanted in ('limited','simulated') and have in ('native','limited','simulated'))
            if not ok:
                raise RequirementError(f"Provider {provider} lacks required tool_calling={wanted} (have {have})")
        elif k == 'json_mode':
            if bool(v) and not caps.get('json_mode'):
                raise RequirementError(f"Provider {provider} lacks json_mode")
        elif k == 'streaming':
            if bool(v) and not caps.get('streaming'):
                raise RequirementError(f"Provider {provider} lacks streaming")
