"""
AI Disclosure Module - EU AI Act Article 52 Compliance

Implements transparency requirements for AI systems interacting
with humans, including disclosure of AI nature.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
import hashlib


class DisclosureType(Enum):
    """Types of AI disclosure."""
    AI_INTERACTION = "ai_interaction"  # User interacting with AI
    AI_GENERATED_CONTENT = "ai_generated_content"  # AI-generated content
    EMOTION_RECOGNITION = "emotion_recognition"  # Emotion recognition system
    BIOMETRIC_CATEGORIZATION = "biometric_categorization"  # Biometric AI
    DEEP_FAKE = "deep_fake"  # Deep fake or synthetic media
    CHATBOT = "chatbot"  # Chatbot interaction
    RECOMMENDATION = "recommendation"  # AI-powered recommendations


class DisclosureFormat(Enum):
    """Formats for disclosure."""
    TEXT = "text"
    BANNER = "banner"
    AUDIO = "audio"
    VISUAL = "visual"
    METADATA = "metadata"
    WATERMARK = "watermark"


class AcknowledgmentStatus(Enum):
    """Status of user acknowledgment."""
    PENDING = "pending"
    ACKNOWLEDGED = "acknowledged"
    DECLINED = "declined"
    NOT_REQUIRED = "not_required"


@dataclass
class DisclosureTemplate:
    """Template for AI disclosure."""
    template_id: str
    disclosure_type: DisclosureType
    format: DisclosureFormat
    content: str
    language: str
    version: str
    active: bool = True
    created_at: datetime = field(default_factory=datetime.utcnow)

    def render(self, context: Optional[Dict[str, Any]] = None) -> str:
        """Render template with context."""
        if not context:
            return self.content

        result = self.content
        for key, value in context.items():
            result = result.replace(f"{{{key}}}", str(value))
        return result


@dataclass
class DisclosureRecord:
    """Record of a disclosure event."""
    record_id: str
    disclosure_type: DisclosureType
    template_id: str
    rendered_content: str
    format: DisclosureFormat
    user_id: Optional[str]
    session_id: Optional[str]
    context: Dict[str, Any]
    acknowledgment_status: AcknowledgmentStatus = AcknowledgmentStatus.PENDING
    acknowledged_at: Optional[datetime] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)
    ai_system_id: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "record_id": self.record_id,
            "disclosure_type": self.disclosure_type.value,
            "template_id": self.template_id,
            "rendered_content": self.rendered_content,
            "format": self.format.value,
            "user_id": self.user_id,
            "session_id": self.session_id,
            "acknowledgment_status": self.acknowledgment_status.value,
            "acknowledged_at": self.acknowledged_at.isoformat() if self.acknowledged_at else None,
            "timestamp": self.timestamp.isoformat()
        }


@dataclass
class ContentLabel:
    """Label for AI-generated content."""
    label_id: str
    content_hash: str
    disclosure_type: DisclosureType
    label_text: str
    metadata: Dict[str, Any]
    created_at: datetime = field(default_factory=datetime.utcnow)


class AIDisclosure:
    """
    AI Disclosure manager for EU AI Act Article 52 compliance.

    Ensures appropriate disclosure when users interact with AI
    systems or when content is AI-generated.
    """

    def __init__(
        self,
        ai_system_id: str,
        ai_system_name: str,
        provider_name: str,
        default_language: str = "en"
    ):
        """
        Initialize AI disclosure manager.

        Args:
            ai_system_id: Unique identifier for the AI system
            ai_system_name: Human-readable AI system name
            provider_name: Name of the provider
            default_language: Default language for disclosures
        """
        self.ai_system_id = ai_system_id
        self.ai_system_name = ai_system_name
        self.provider_name = provider_name
        self.default_language = default_language

        self._templates: Dict[str, DisclosureTemplate] = {}
        self._records: Dict[str, DisclosureRecord] = {}
        self._content_labels: Dict[str, ContentLabel] = {}
        self._record_counter = 0

        # Initialize default templates
        self._initialize_default_templates()

    def _generate_record_id(self) -> str:
        """Generate unique record ID."""
        self._record_counter += 1
        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        return f"DR-{timestamp}-{self._record_counter:06d}"

    def _hash_content(self, content: Any) -> str:
        """Generate hash for content."""
        content_str = str(content)
        return hashlib.sha256(content_str.encode()).hexdigest()[:16]

    def _initialize_default_templates(self) -> None:
        """Initialize default disclosure templates."""
        templates = [
            {
                "type": DisclosureType.AI_INTERACTION,
                "format": DisclosureFormat.TEXT,
                "content": f"You are interacting with {self.ai_system_name}, an AI system provided by {self.provider_name}.",
                "language": "en"
            },
            {
                "type": DisclosureType.AI_INTERACTION,
                "format": DisclosureFormat.BANNER,
                "content": f"AI Assistant: {self.ai_system_name}",
                "language": "en"
            },
            {
                "type": DisclosureType.CHATBOT,
                "format": DisclosureFormat.TEXT,
                "content": f"This is an automated AI chatbot ({self.ai_system_name}). You are not speaking with a human.",
                "language": "en"
            },
            {
                "type": DisclosureType.AI_GENERATED_CONTENT,
                "format": DisclosureFormat.TEXT,
                "content": f"This content was generated by AI ({self.ai_system_name}) and may not reflect human views.",
                "language": "en"
            },
            {
                "type": DisclosureType.AI_GENERATED_CONTENT,
                "format": DisclosureFormat.METADATA,
                "content": "ai_generated=true",
                "language": "en"
            },
            {
                "type": DisclosureType.RECOMMENDATION,
                "format": DisclosureFormat.TEXT,
                "content": "These recommendations are generated by an AI system and may be based on your previous interactions.",
                "language": "en"
            },
            {
                "type": DisclosureType.EMOTION_RECOGNITION,
                "format": DisclosureFormat.TEXT,
                "content": "This system uses AI to analyze emotions. Your facial expressions or voice may be processed.",
                "language": "en"
            },
            {
                "type": DisclosureType.DEEP_FAKE,
                "format": DisclosureFormat.VISUAL,
                "content": "AI-MANIPULATED CONTENT - This image/video has been artificially generated or modified.",
                "language": "en"
            }
        ]

        for i, t in enumerate(templates):
            template = DisclosureTemplate(
                template_id=f"TPL-{i+1:04d}",
                disclosure_type=t["type"],
                format=t["format"],
                content=t["content"],
                language=t["language"],
                version="1.0"
            )
            self._templates[template.template_id] = template

    def add_template(
        self,
        disclosure_type: DisclosureType,
        format: DisclosureFormat,
        content: str,
        language: str = "en",
        version: str = "1.0"
    ) -> DisclosureTemplate:
        """
        Add a custom disclosure template.

        Args:
            disclosure_type: Type of disclosure
            format: Format of disclosure
            content: Template content (use {key} for variables)
            language: Language code
            version: Version string

        Returns:
            Created DisclosureTemplate
        """
        template_id = f"TPL-{len(self._templates) + 1:04d}"
        template = DisclosureTemplate(
            template_id=template_id,
            disclosure_type=disclosure_type,
            format=format,
            content=content,
            language=language,
            version=version
        )
        self._templates[template_id] = template
        return template

    def disclose(
        self,
        disclosure_type: DisclosureType,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        format: Optional[DisclosureFormat] = None,
        language: Optional[str] = None,
        require_acknowledgment: bool = False
    ) -> DisclosureRecord:
        """
        Create a disclosure for a user interaction.

        Args:
            disclosure_type: Type of disclosure
            user_id: User identifier
            session_id: Session identifier
            context: Context for template rendering
            format: Preferred format (if None, use default)
            language: Language (if None, use default)
            require_acknowledgment: Whether acknowledgment is required

        Returns:
            DisclosureRecord
        """
        lang = language or self.default_language
        fmt = format or DisclosureFormat.TEXT

        # Find matching template
        template = self._find_template(disclosure_type, fmt, lang)
        if not template:
            # Fall back to any template of this type
            template = self._find_template(disclosure_type, None, None)

        if not template:
            # Create ad-hoc template if none found
            template = DisclosureTemplate(
                template_id="TPL-ADHOC",
                disclosure_type=disclosure_type,
                format=fmt,
                content=f"You are interacting with an AI system: {self.ai_system_name}",
                language=lang,
                version="1.0"
            )

        # Render content
        rendered = template.render(context)

        # Create record
        record = DisclosureRecord(
            record_id=self._generate_record_id(),
            disclosure_type=disclosure_type,
            template_id=template.template_id,
            rendered_content=rendered,
            format=template.format,
            user_id=user_id,
            session_id=session_id,
            context=context or {},
            acknowledgment_status=(
                AcknowledgmentStatus.PENDING if require_acknowledgment
                else AcknowledgmentStatus.NOT_REQUIRED
            ),
            ai_system_id=self.ai_system_id
        )

        self._records[record.record_id] = record
        return record

    def _find_template(
        self,
        disclosure_type: DisclosureType,
        format: Optional[DisclosureFormat],
        language: Optional[str]
    ) -> Optional[DisclosureTemplate]:
        """Find matching template."""
        for template in self._templates.values():
            if not template.active:
                continue
            if template.disclosure_type != disclosure_type:
                continue
            if format and template.format != format:
                continue
            if language and template.language != language:
                continue
            return template
        return None

    def acknowledge_disclosure(
        self,
        record_id: str,
        acknowledged: bool = True
    ) -> bool:
        """
        Record user acknowledgment of disclosure.

        Args:
            record_id: Disclosure record ID
            acknowledged: Whether user acknowledged

        Returns:
            True if acknowledgment recorded
        """
        if record_id not in self._records:
            return False

        record = self._records[record_id]
        if record.acknowledgment_status == AcknowledgmentStatus.NOT_REQUIRED:
            return True

        record.acknowledgment_status = (
            AcknowledgmentStatus.ACKNOWLEDGED if acknowledged
            else AcknowledgmentStatus.DECLINED
        )
        record.acknowledged_at = datetime.utcnow()
        return True

    def label_content(
        self,
        content: Any,
        disclosure_type: DisclosureType = DisclosureType.AI_GENERATED_CONTENT,
        additional_metadata: Optional[Dict[str, Any]] = None
    ) -> ContentLabel:
        """
        Label AI-generated content for transparency.

        Args:
            content: The content to label
            disclosure_type: Type of disclosure
            additional_metadata: Additional metadata to include

        Returns:
            ContentLabel
        """
        content_hash = self._hash_content(content)

        # Determine label text based on disclosure type
        label_texts = {
            DisclosureType.AI_GENERATED_CONTENT: "AI Generated",
            DisclosureType.DEEP_FAKE: "AI Manipulated Media",
            DisclosureType.RECOMMENDATION: "AI Recommended",
        }
        label_text = label_texts.get(disclosure_type, "AI Content")

        metadata = {
            "ai_system_id": self.ai_system_id,
            "ai_system_name": self.ai_system_name,
            "provider": self.provider_name,
            "generated_at": datetime.utcnow().isoformat(),
            "content_hash": content_hash
        }
        if additional_metadata:
            metadata.update(additional_metadata)

        label = ContentLabel(
            label_id=f"LBL-{content_hash}",
            content_hash=content_hash,
            disclosure_type=disclosure_type,
            label_text=label_text,
            metadata=metadata
        )

        self._content_labels[label.label_id] = label
        return label

    def get_content_label(self, content: Any) -> Optional[ContentLabel]:
        """Get label for content if it exists."""
        content_hash = self._hash_content(content)
        label_id = f"LBL-{content_hash}"
        return self._content_labels.get(label_id)

    def verify_content_labeled(self, content: Any) -> bool:
        """Check if content has been properly labeled."""
        return self.get_content_label(content) is not None

    def disclose_chatbot(
        self,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        chatbot_name: Optional[str] = None
    ) -> DisclosureRecord:
        """
        Create disclosure for chatbot interaction.

        Args:
            user_id: User identifier
            session_id: Session identifier
            chatbot_name: Optional custom chatbot name

        Returns:
            DisclosureRecord
        """
        context = {"chatbot_name": chatbot_name or self.ai_system_name}
        return self.disclose(
            disclosure_type=DisclosureType.CHATBOT,
            user_id=user_id,
            session_id=session_id,
            context=context,
            require_acknowledgment=True
        )

    def disclose_emotion_recognition(
        self,
        user_id: str,
        data_types: List[str],
        purposes: List[str],
        session_id: Optional[str] = None
    ) -> DisclosureRecord:
        """
        Create disclosure for emotion recognition system.

        Args:
            user_id: User identifier
            data_types: Types of data being processed
            purposes: Purposes of processing
            session_id: Session identifier

        Returns:
            DisclosureRecord
        """
        context = {
            "data_types": ", ".join(data_types),
            "purposes": ", ".join(purposes)
        }
        return self.disclose(
            disclosure_type=DisclosureType.EMOTION_RECOGNITION,
            user_id=user_id,
            session_id=session_id,
            context=context,
            require_acknowledgment=True
        )

    def get_disclosure_record(self, record_id: str) -> Optional[DisclosureRecord]:
        """Get a specific disclosure record."""
        return self._records.get(record_id)

    def get_records_by_user(self, user_id: str) -> List[DisclosureRecord]:
        """Get all disclosure records for a user."""
        return [
            r for r in self._records.values()
            if r.user_id == user_id
        ]

    def get_records_by_session(self, session_id: str) -> List[DisclosureRecord]:
        """Get all disclosure records for a session."""
        return [
            r for r in self._records.values()
            if r.session_id == session_id
        ]

    def get_pending_acknowledgments(
        self,
        user_id: Optional[str] = None
    ) -> List[DisclosureRecord]:
        """Get disclosures pending acknowledgment."""
        records = [
            r for r in self._records.values()
            if r.acknowledgment_status == AcknowledgmentStatus.PENDING
        ]
        if user_id:
            records = [r for r in records if r.user_id == user_id]
        return records

    def get_statistics(self) -> Dict[str, Any]:
        """Get disclosure statistics."""
        type_counts = {}
        ack_counts = {}

        for record in self._records.values():
            dtype = record.disclosure_type.value
            type_counts[dtype] = type_counts.get(dtype, 0) + 1

            status = record.acknowledgment_status.value
            ack_counts[status] = ack_counts.get(status, 0) + 1

        return {
            "ai_system_id": self.ai_system_id,
            "total_disclosures": len(self._records),
            "disclosures_by_type": type_counts,
            "acknowledgment_status": ack_counts,
            "total_content_labels": len(self._content_labels),
            "total_templates": len(self._templates),
            "active_templates": sum(1 for t in self._templates.values() if t.active),
            "statistics_timestamp": datetime.utcnow().isoformat()
        }

    def export_disclosure_data(self) -> Dict[str, Any]:
        """Export all disclosure data."""
        return {
            "ai_system_id": self.ai_system_id,
            "ai_system_name": self.ai_system_name,
            "provider_name": self.provider_name,
            "records": [r.to_dict() for r in self._records.values()],
            "content_labels": [
                {
                    "label_id": l.label_id,
                    "content_hash": l.content_hash,
                    "type": l.disclosure_type.value,
                    "label_text": l.label_text,
                    "created_at": l.created_at.isoformat()
                }
                for l in self._content_labels.values()
            ],
            "templates": [
                {
                    "template_id": t.template_id,
                    "type": t.disclosure_type.value,
                    "format": t.format.value,
                    "language": t.language,
                    "active": t.active
                }
                for t in self._templates.values()
            ],
            "export_date": datetime.utcnow().isoformat()
        }
