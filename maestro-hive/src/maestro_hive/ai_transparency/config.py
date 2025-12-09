"""
Transparency Configuration Module - MD-2792

Provides configuration dataclasses for AI transparency settings
compliant with EU AI Act Article 52 requirements.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
import os
import json


class TransparencyLevel(Enum):
    """Levels of transparency disclosure detail."""
    MINIMAL = "minimal"      # Basic AI indicator only
    STANDARD = "standard"    # AI indicator with system name
    DETAILED = "detailed"    # Full disclosure with model info
    FULL = "full"            # Complete audit-level transparency


class DisclosureFormat(Enum):
    """Formats for displaying AI transparency disclosures."""
    INLINE = "inline"        # Disclosure appended to content
    FOOTER = "footer"        # Disclosure at end of document
    HEADER = "header"        # Disclosure at start of content
    METADATA = "metadata"    # Disclosure in response metadata only
    WATERMARK = "watermark"  # Visual watermark overlay


@dataclass
class TransparencyConfig:
    """
    Configuration for AI transparency settings.

    Manages disclosure behavior, format preferences, and compliance settings
    for EU AI Act Article 52 transparency requirements.
    """
    # Core settings
    disclosure_enabled: bool = True
    disclosure_format: DisclosureFormat = DisclosureFormat.INLINE
    disclosure_level: TransparencyLevel = TransparencyLevel.STANDARD

    # Disclosure text settings
    ai_indicator_text: str = "AI-generated content"
    custom_disclosure_template: Optional[str] = None

    # Content settings
    include_model_info: bool = False
    include_timestamp: bool = True
    include_agent_name: bool = True
    include_provider_info: bool = False

    # Compliance settings
    eu_ai_act_compliance: bool = True
    audit_logging_enabled: bool = True
    disclosure_tracking_enabled: bool = True

    # Agent image settings
    agent_images_enabled: bool = True
    default_agent_image: str = "/images/default-agent.png"
    agent_image_cdn_url: Optional[str] = None

    # Cache settings
    cache_ttl_seconds: int = 3600

    # Metadata
    config_version: str = "1.0.0"
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    @classmethod
    def from_env(cls) -> "TransparencyConfig":
        """
        Create configuration from environment variables.

        Environment variables:
            AI_TRANSPARENCY_ENABLED: Enable/disable transparency (default: true)
            AI_DISCLOSURE_LEVEL: Disclosure level (default: standard)
            AI_DISCLOSURE_FORMAT: Disclosure format (default: inline)
            AI_INDICATOR_TEXT: Custom indicator text
            AGENT_REGISTRY_PATH: Path to agent registry file
            AGENT_IMAGE_CDN_URL: CDN URL for agent images

        Returns:
            TransparencyConfig instance
        """
        return cls(
            disclosure_enabled=os.getenv("AI_TRANSPARENCY_ENABLED", "true").lower() == "true",
            disclosure_level=TransparencyLevel(
                os.getenv("AI_DISCLOSURE_LEVEL", "standard")
            ),
            disclosure_format=DisclosureFormat(
                os.getenv("AI_DISCLOSURE_FORMAT", "inline")
            ),
            ai_indicator_text=os.getenv("AI_INDICATOR_TEXT", "AI-generated content"),
            include_model_info=os.getenv("AI_INCLUDE_MODEL_INFO", "false").lower() == "true",
            include_timestamp=os.getenv("AI_INCLUDE_TIMESTAMP", "true").lower() == "true",
            agent_image_cdn_url=os.getenv("AGENT_IMAGE_CDN_URL"),
            eu_ai_act_compliance=os.getenv("EU_AI_ACT_COMPLIANCE", "true").lower() == "true",
            audit_logging_enabled=os.getenv("AUDIT_LOGGING_ENABLED", "true").lower() == "true",
        )

    @classmethod
    def from_file(cls, path: str) -> "TransparencyConfig":
        """
        Load configuration from a YAML or JSON file.

        Args:
            path: Path to configuration file

        Returns:
            TransparencyConfig instance
        """
        with open(path, "r") as f:
            if path.endswith(".json"):
                data = json.load(f)
            else:
                # Simple YAML parsing for basic configs
                import yaml
                data = yaml.safe_load(f)

        transparency_data = data.get("transparency", data)

        return cls(
            disclosure_enabled=transparency_data.get("enabled", True),
            disclosure_level=TransparencyLevel(
                transparency_data.get("disclosure", {}).get("level", "standard")
            ),
            disclosure_format=DisclosureFormat(
                transparency_data.get("disclosure", {}).get("format", "inline")
            ),
            ai_indicator_text=transparency_data.get("disclosure", {}).get("text", "AI-generated content"),
            include_model_info=transparency_data.get("disclosure", {}).get("include_model", False),
            include_timestamp=transparency_data.get("disclosure", {}).get("include_timestamp", True),
            agent_image_cdn_url=transparency_data.get("agents", {}).get("image_cdn"),
            eu_ai_act_compliance=transparency_data.get("compliance", {}).get("eu_ai_act", True),
            audit_logging_enabled=transparency_data.get("compliance", {}).get("audit_logging", True),
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return {
            "disclosure_enabled": self.disclosure_enabled,
            "disclosure_format": self.disclosure_format.value,
            "disclosure_level": self.disclosure_level.value,
            "ai_indicator_text": self.ai_indicator_text,
            "custom_disclosure_template": self.custom_disclosure_template,
            "include_model_info": self.include_model_info,
            "include_timestamp": self.include_timestamp,
            "include_agent_name": self.include_agent_name,
            "include_provider_info": self.include_provider_info,
            "eu_ai_act_compliance": self.eu_ai_act_compliance,
            "audit_logging_enabled": self.audit_logging_enabled,
            "disclosure_tracking_enabled": self.disclosure_tracking_enabled,
            "agent_images_enabled": self.agent_images_enabled,
            "default_agent_image": self.default_agent_image,
            "agent_image_cdn_url": self.agent_image_cdn_url,
            "config_version": self.config_version,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    def validate(self) -> List[str]:
        """
        Validate configuration settings.

        Returns:
            List of validation errors (empty if valid)
        """
        errors = []

        if self.eu_ai_act_compliance and not self.disclosure_enabled:
            errors.append("EU AI Act compliance requires disclosure_enabled=True")

        if self.disclosure_tracking_enabled and not self.audit_logging_enabled:
            errors.append("Disclosure tracking requires audit logging to be enabled")

        if self.agent_images_enabled and not self.default_agent_image:
            errors.append("Agent images enabled but no default image specified")

        if self.cache_ttl_seconds < 0:
            errors.append("Cache TTL must be non-negative")

        return errors

    def is_valid(self) -> bool:
        """Check if configuration is valid."""
        return len(self.validate()) == 0

    def update(self, **kwargs: Any) -> "TransparencyConfig":
        """
        Create updated configuration with new values.

        Args:
            **kwargs: Configuration values to update

        Returns:
            New TransparencyConfig with updated values
        """
        current = self.to_dict()

        # Handle enum conversions
        if "disclosure_format" in kwargs and isinstance(kwargs["disclosure_format"], str):
            kwargs["disclosure_format"] = DisclosureFormat(kwargs["disclosure_format"])
        if "disclosure_level" in kwargs and isinstance(kwargs["disclosure_level"], str):
            kwargs["disclosure_level"] = TransparencyLevel(kwargs["disclosure_level"])

        # Remove datetime fields that shouldn't be copied
        current.pop("created_at", None)
        current.pop("updated_at", None)

        # Apply updates
        for key, value in kwargs.items():
            if key in current or hasattr(self, key):
                current[key] = value

        # Convert string enums back
        if isinstance(current.get("disclosure_format"), str):
            current["disclosure_format"] = DisclosureFormat(current["disclosure_format"])
        if isinstance(current.get("disclosure_level"), str):
            current["disclosure_level"] = TransparencyLevel(current["disclosure_level"])

        new_config = TransparencyConfig(
            disclosure_enabled=current.get("disclosure_enabled", True),
            disclosure_format=current.get("disclosure_format", DisclosureFormat.INLINE),
            disclosure_level=current.get("disclosure_level", TransparencyLevel.STANDARD),
            ai_indicator_text=current.get("ai_indicator_text", "AI-generated content"),
            include_model_info=current.get("include_model_info", False),
            include_timestamp=current.get("include_timestamp", True),
            include_agent_name=current.get("include_agent_name", True),
            include_provider_info=current.get("include_provider_info", False),
            eu_ai_act_compliance=current.get("eu_ai_act_compliance", True),
            audit_logging_enabled=current.get("audit_logging_enabled", True),
            disclosure_tracking_enabled=current.get("disclosure_tracking_enabled", True),
            agent_images_enabled=current.get("agent_images_enabled", True),
            default_agent_image=current.get("default_agent_image", "/images/default-agent.png"),
            agent_image_cdn_url=current.get("agent_image_cdn_url"),
            cache_ttl_seconds=current.get("cache_ttl_seconds", 3600),
            created_at=self.created_at,
            updated_at=datetime.utcnow(),
        )

        return new_config


def enable_transparency(config: Optional[TransparencyConfig] = None) -> TransparencyConfig:
    """
    Enable transparency with the given configuration.

    Args:
        config: Optional configuration to use (default: from environment)

    Returns:
        Active TransparencyConfig
    """
    if config is None:
        config = TransparencyConfig.from_env()

    config = config.update(disclosure_enabled=True)
    return config


def disable_transparency(config: TransparencyConfig) -> TransparencyConfig:
    """
    Disable transparency (for emergency use only).

    Args:
        config: Current configuration

    Returns:
        Updated TransparencyConfig with disclosure disabled
    """
    return config.update(disclosure_enabled=False)
