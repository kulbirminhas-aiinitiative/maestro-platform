from __future__ import annotations
import os
import yaml
from typing import Optional
from .spi import LLMClient
from .providers.claude_agent import ClaudeAgentClient
from .providers.openai_adapter import OpenAIClient
from .providers.gemini_adapter import GeminiClient

CAP_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "config", "capabilities.yaml")
POLICY_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "config", "persona_policy.yaml")

_PROVIDER_MAP = {
    "claude_agent": lambda: ClaudeAgentClient(),
    "openai": lambda: OpenAIClient(),
    "gemini": lambda: GeminiClient(),
}

def load_yaml(path: str):
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

class PersonaRouter:
    def __init__(self, capabilities: Optional[dict] = None, policy: Optional[dict] = None):
        self.capabilities = capabilities or load_yaml(CAP_PATH)
        self.policy = policy or load_yaml(POLICY_PATH)

    def select_provider(self, persona: str) -> str:
        prefs = self.policy.get("personas", {}).get(persona, {}).get("provider_preferences", [])
        reqs = set(self.policy.get("personas", {}).get(persona, {}).get("requires", []))
        caps = self.capabilities.get("providers", {})
        for p in prefs:
            pc = caps.get(p, {}).get("capabilities", [])
            if reqs.issubset(set(pc)):
                return p
        raise ValueError(f"No provider satisfies requirements for persona={persona}")

    def get_client(self, persona: str) -> LLMClient:
        pid = self.select_provider(persona)
        factory = _PROVIDER_MAP.get(pid)
        if not factory:
            raise ValueError(f"Unknown provider: {pid}")
        return factory()
