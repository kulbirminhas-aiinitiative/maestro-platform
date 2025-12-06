"""LLM Provider Information Display - EU AI Act Transparency"""
from typing import Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime

@dataclass
class LLMProviderInfo:
    """Information about the LLM provider used."""
    provider_name: str
    model_id: str
    model_version: str
    capabilities: list
    data_location: str
    privacy_policy_url: str

    def to_display_dict(self) -> Dict[str, Any]:
        """Return user-friendly display information."""
        return {
            "provider": self.provider_name,
            "model": f"{self.model_id} (v{self.model_version})",
            "capabilities": self.capabilities,
            "data_processing_location": self.data_location,
            "privacy_policy": self.privacy_policy_url
        }

# Known provider configurations
KNOWN_PROVIDERS = {
    "anthropic": LLMProviderInfo(
        provider_name="Anthropic",
        model_id="claude-3",
        model_version="opus/sonnet/haiku",
        capabilities=["text-generation", "code-generation", "analysis"],
        data_location="USA (AWS)",
        privacy_policy_url="https://www.anthropic.com/privacy"
    ),
    "openai": LLMProviderInfo(
        provider_name="OpenAI",
        model_id="gpt-4",
        model_version="turbo",
        capabilities=["text-generation", "code-generation", "vision"],
        data_location="USA (Azure)",
        privacy_policy_url="https://openai.com/privacy"
    )
}

def get_provider_info(provider_key: str) -> Optional[LLMProviderInfo]:
    """Get provider information by key."""
    return KNOWN_PROVIDERS.get(provider_key.lower())

def format_provider_disclosure(provider_key: str, request_id: str) -> str:
    """Format provider information for user display."""
    info = get_provider_info(provider_key)
    if not info:
        return f"AI Provider: {provider_key} (details unavailable)"

    return f"""
AI Processing Information
========================
Provider: {info.provider_name}
Model: {info.model_id} ({info.model_version})
Data Location: {info.data_location}
Request ID: {request_id}
Timestamp: {datetime.utcnow().isoformat()}
Privacy Policy: {info.privacy_policy_url}
"""
