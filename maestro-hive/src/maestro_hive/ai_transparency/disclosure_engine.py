"""
Disclosure Engine Module - MD-2792

Generates and manages AI content disclosures for EU AI Act compliance.
Handles multiple output formats and disclosure tracking.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union
import hashlib
import json
import logging
import re
import uuid

from .config import TransparencyConfig, TransparencyLevel, DisclosureFormat
from .agent_registry import AgentConfig, AgentRegistry, get_registry

logger = logging.getLogger(__name__)


class ContentType(Enum):
    """Types of AI-generated content."""
    TEXT = "text"
    CODE = "code"
    DOCUMENT = "document"
    API_RESPONSE = "api_response"
    CHAT_MESSAGE = "chat_message"
    EMAIL = "email"
    REPORT = "report"


@dataclass
class DisclosureResult:
    """
    Result of a disclosure operation.

    Contains the disclosed content and metadata for audit tracking.
    """
    # Unique identifiers
    disclosure_id: str
    content_hash: str

    # Content
    original_content: str
    disclosed_content: str
    disclosure_text: str

    # Context
    agent_id: Optional[str] = None
    agent_name: Optional[str] = None
    model_name: Optional[str] = None
    content_type: ContentType = ContentType.TEXT

    # Settings used
    disclosure_format: DisclosureFormat = DisclosureFormat.INLINE
    disclosure_level: TransparencyLevel = TransparencyLevel.STANDARD

    # Metadata
    timestamp: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary for storage/audit."""
        return {
            "disclosure_id": self.disclosure_id,
            "content_hash": self.content_hash,
            "disclosed_content_length": len(self.disclosed_content),
            "disclosure_text": self.disclosure_text,
            "agent_id": self.agent_id,
            "agent_name": self.agent_name,
            "model_name": self.model_name,
            "content_type": self.content_type.value,
            "disclosure_format": self.disclosure_format.value,
            "disclosure_level": self.disclosure_level.value,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
        }

    def to_audit_log(self) -> Dict[str, Any]:
        """Generate audit log entry (excludes content for privacy)."""
        return {
            "disclosure_id": self.disclosure_id,
            "content_hash": self.content_hash,
            "agent_id": self.agent_id,
            "content_type": self.content_type.value,
            "disclosure_format": self.disclosure_format.value,
            "timestamp": self.timestamp.isoformat(),
        }


class DisclosureEngine:
    """
    Engine for generating AI content disclosures.

    Handles all disclosure generation with support for multiple formats
    and compliance requirements.
    """

    def __init__(
        self,
        config: Optional[TransparencyConfig] = None,
        registry: Optional[AgentRegistry] = None
    ):
        """
        Initialize the disclosure engine.

        Args:
            config: Transparency configuration
            registry: Agent registry for agent lookups
        """
        self.config = config or TransparencyConfig()
        self.registry = registry or get_registry()
        self._disclosure_history: List[DisclosureResult] = []

    def disclose(
        self,
        content: str,
        agent_id: Optional[str] = None,
        content_type: ContentType = ContentType.TEXT,
        metadata: Optional[Dict[str, Any]] = None,
        override_format: Optional[DisclosureFormat] = None,
        override_level: Optional[TransparencyLevel] = None,
    ) -> DisclosureResult:
        """
        Apply AI disclosure to content.

        Args:
            content: Original content to disclose
            agent_id: Optional agent ID for specific agent info
            content_type: Type of content being disclosed
            metadata: Additional metadata to include
            override_format: Override disclosure format
            override_level: Override disclosure level

        Returns:
            DisclosureResult with disclosed content
        """
        if not self.config.disclosure_enabled:
            return self._create_result(
                content, content, "", agent_id, content_type, metadata
            )

        # Get agent config if available
        agent_config = None
        if agent_id:
            agent_config = self.registry.get(agent_id)

        # Determine format and level
        disclosure_format = override_format or self.config.disclosure_format
        disclosure_level = override_level or self.config.disclosure_level

        # Generate disclosure text
        disclosure_text = self._generate_disclosure_text(
            agent_config, disclosure_level
        )

        # Apply disclosure to content
        disclosed_content = self._apply_disclosure(
            content, disclosure_text, disclosure_format, content_type
        )

        # Create result
        result = self._create_result(
            content,
            disclosed_content,
            disclosure_text,
            agent_id,
            content_type,
            metadata,
            agent_config,
            disclosure_format,
            disclosure_level
        )

        # Track for audit
        if self.config.disclosure_tracking_enabled:
            self._disclosure_history.append(result)
            if len(self._disclosure_history) > 1000:
                self._disclosure_history = self._disclosure_history[-500:]

        logger.debug(f"Disclosure applied: {result.disclosure_id}")
        return result

    def disclose_code(
        self,
        code: str,
        language: str = "python",
        agent_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> DisclosureResult:
        """
        Apply AI disclosure to code content.

        Args:
            code: Source code
            language: Programming language
            agent_id: Optional agent ID
            metadata: Additional metadata

        Returns:
            DisclosureResult with disclosed code
        """
        meta = metadata or {}
        meta["language"] = language

        return self.disclose(
            code,
            agent_id=agent_id,
            content_type=ContentType.CODE,
            metadata=meta,
            override_format=DisclosureFormat.HEADER  # Code uses header format
        )

    def disclose_document(
        self,
        document: str,
        doc_type: str = "markdown",
        agent_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> DisclosureResult:
        """
        Apply AI disclosure to document content.

        Args:
            document: Document content
            doc_type: Document type (markdown, html, plain)
            agent_id: Optional agent ID
            metadata: Additional metadata

        Returns:
            DisclosureResult with disclosed document
        """
        meta = metadata or {}
        meta["doc_type"] = doc_type

        # Choose format based on document type
        if doc_type == "html":
            format_override = DisclosureFormat.FOOTER
        elif doc_type == "markdown":
            format_override = DisclosureFormat.HEADER
        else:
            format_override = None

        return self.disclose(
            document,
            agent_id=agent_id,
            content_type=ContentType.DOCUMENT,
            metadata=meta,
            override_format=format_override
        )

    def disclose_api_response(
        self,
        response: Union[str, Dict[str, Any]],
        agent_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> DisclosureResult:
        """
        Apply AI disclosure to API response.

        Args:
            response: API response content
            agent_id: Optional agent ID
            metadata: Additional metadata

        Returns:
            DisclosureResult with disclosed response
        """
        if isinstance(response, dict):
            content = json.dumps(response, indent=2)
        else:
            content = response

        return self.disclose(
            content,
            agent_id=agent_id,
            content_type=ContentType.API_RESPONSE,
            metadata=metadata,
            override_format=DisclosureFormat.METADATA
        )

    def _generate_disclosure_text(
        self,
        agent_config: Optional[AgentConfig],
        level: TransparencyLevel
    ) -> str:
        """Generate disclosure text based on level and agent config."""
        parts = []

        # Base indicator
        if self.config.custom_disclosure_template:
            base = self.config.custom_disclosure_template
        else:
            base = self.config.ai_indicator_text

        parts.append(base)

        # Add details based on level
        if level in (TransparencyLevel.STANDARD, TransparencyLevel.DETAILED, TransparencyLevel.FULL):
            if agent_config and self.config.include_agent_name:
                parts.append(f"by {agent_config.display_name}")
            elif self.config.include_agent_name:
                parts.append("by AI Assistant")

        if level in (TransparencyLevel.DETAILED, TransparencyLevel.FULL):
            if agent_config and self.config.include_model_info:
                model_info = agent_config.model_name
                if agent_config.model_version:
                    model_info += f" v{agent_config.model_version}"
                parts.append(f"({model_info})")

            if self.config.include_provider_info and agent_config:
                parts.append(f"via {agent_config.provider}")

        if level == TransparencyLevel.FULL:
            if self.config.include_timestamp:
                parts.append(f"[{datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}]")

        return " ".join(parts)

    def _apply_disclosure(
        self,
        content: str,
        disclosure_text: str,
        format: DisclosureFormat,
        content_type: ContentType
    ) -> str:
        """Apply disclosure to content based on format."""
        if format == DisclosureFormat.HEADER:
            return self._format_header(content, disclosure_text, content_type)
        elif format == DisclosureFormat.FOOTER:
            return self._format_footer(content, disclosure_text, content_type)
        elif format == DisclosureFormat.INLINE:
            return self._format_inline(content, disclosure_text)
        elif format == DisclosureFormat.METADATA:
            return content  # Metadata-only, content unchanged
        elif format == DisclosureFormat.WATERMARK:
            return self._format_watermark(content, disclosure_text, content_type)
        else:
            return self._format_inline(content, disclosure_text)

    def _format_header(
        self,
        content: str,
        disclosure: str,
        content_type: ContentType
    ) -> str:
        """Format disclosure as header."""
        if content_type == ContentType.CODE:
            # Use comment format for code
            return f'"""\n{disclosure}\n"""\n\n{content}'
        elif content_type == ContentType.DOCUMENT:
            return f"> {disclosure}\n\n---\n\n{content}"
        else:
            return f"[{disclosure}]\n\n{content}"

    def _format_footer(
        self,
        content: str,
        disclosure: str,
        content_type: ContentType
    ) -> str:
        """Format disclosure as footer."""
        if content_type == ContentType.CODE:
            return f'{content}\n\n# {disclosure}'
        elif content_type == ContentType.DOCUMENT:
            return f"{content}\n\n---\n\n_{disclosure}_"
        else:
            return f"{content}\n\n[{disclosure}]"

    def _format_inline(self, content: str, disclosure: str) -> str:
        """Format disclosure inline with content."""
        return f"[{disclosure}] {content}"

    def _format_watermark(
        self,
        content: str,
        disclosure: str,
        content_type: ContentType
    ) -> str:
        """Format disclosure as watermark (visual marker)."""
        watermark = f"<!-- AI-DISCLOSURE: {disclosure} -->"
        if content_type == ContentType.DOCUMENT:
            return f"{watermark}\n{content}"
        else:
            return f"{content}\n{watermark}"

    def _create_result(
        self,
        original: str,
        disclosed: str,
        disclosure_text: str,
        agent_id: Optional[str],
        content_type: ContentType,
        metadata: Optional[Dict[str, Any]],
        agent_config: Optional[AgentConfig] = None,
        disclosure_format: Optional[DisclosureFormat] = None,
        disclosure_level: Optional[TransparencyLevel] = None,
    ) -> DisclosureResult:
        """Create a DisclosureResult."""
        return DisclosureResult(
            disclosure_id=f"disc_{uuid.uuid4().hex[:12]}",
            content_hash=hashlib.sha256(original.encode()).hexdigest()[:16],
            original_content=original,
            disclosed_content=disclosed,
            disclosure_text=disclosure_text,
            agent_id=agent_id,
            agent_name=agent_config.display_name if agent_config else None,
            model_name=agent_config.model_name if agent_config else None,
            content_type=content_type,
            disclosure_format=disclosure_format or self.config.disclosure_format,
            disclosure_level=disclosure_level or self.config.disclosure_level,
            metadata=metadata or {},
        )

    def get_disclosure_history(
        self,
        limit: int = 100,
        agent_id: Optional[str] = None
    ) -> List[DisclosureResult]:
        """
        Get disclosure history for audit.

        Args:
            limit: Maximum results to return
            agent_id: Filter by agent ID

        Returns:
            List of DisclosureResult objects
        """
        results = self._disclosure_history

        if agent_id:
            results = [r for r in results if r.agent_id == agent_id]

        return results[-limit:]

    def get_statistics(self) -> Dict[str, Any]:
        """Get disclosure statistics."""
        if not self._disclosure_history:
            return {
                "total_disclosures": 0,
                "by_type": {},
                "by_format": {},
                "by_level": {},
            }

        by_type = {}
        by_format = {}
        by_level = {}

        for result in self._disclosure_history:
            # By content type
            t = result.content_type.value
            by_type[t] = by_type.get(t, 0) + 1

            # By format
            f = result.disclosure_format.value
            by_format[f] = by_format.get(f, 0) + 1

            # By level
            l = result.disclosure_level.value
            by_level[l] = by_level.get(l, 0) + 1

        return {
            "total_disclosures": len(self._disclosure_history),
            "by_type": by_type,
            "by_format": by_format,
            "by_level": by_level,
            "unique_agents": len(set(
                r.agent_id for r in self._disclosure_history if r.agent_id
            )),
        }

    def clear_history(self) -> int:
        """
        Clear disclosure history.

        Returns:
            Number of records cleared
        """
        count = len(self._disclosure_history)
        self._disclosure_history.clear()
        return count


# Default engine instance
_default_engine: Optional[DisclosureEngine] = None


def get_engine() -> DisclosureEngine:
    """Get the default disclosure engine instance."""
    global _default_engine
    if _default_engine is None:
        _default_engine = DisclosureEngine()
    return _default_engine


def set_engine(engine: DisclosureEngine) -> None:
    """Set the default disclosure engine instance."""
    global _default_engine
    _default_engine = engine


def disclose(content: str, **kwargs) -> DisclosureResult:
    """Convenience function to apply disclosure using default engine."""
    return get_engine().disclose(content, **kwargs)
