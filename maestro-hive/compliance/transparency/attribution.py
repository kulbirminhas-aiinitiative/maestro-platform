"""AI Attribution System - Track AI vs Human contributions"""
from typing import Dict, Any, Optional, List
from datetime import datetime
from enum import Enum
import hashlib
import json

class ContentSource(Enum):
    AI_GENERATED = "ai_generated"
    HUMAN_WRITTEN = "human_written"
    AI_ASSISTED = "ai_assisted"  # Human edited AI content
    MIXED = "mixed"

class AIAttribution:
    """Tracks and marks AI-generated content for IP attribution."""

    MARKER_PREFIX = "<!-- AI-ATTR:"
    MARKER_SUFFIX = ":AI-ATTR -->"

    def __init__(self, provider: str, model: str):
        self.provider = provider
        self.model = model

    def create_marker(self, content_hash: str) -> str:
        """Create invisible attribution marker."""
        attr_data = {
            "v": "1.0",
            "src": ContentSource.AI_GENERATED.value,
            "p": self.provider,
            "m": self.model,
            "t": datetime.utcnow().isoformat(),
            "h": content_hash[:16]
        }
        return f"{self.MARKER_PREFIX}{json.dumps(attr_data)}{self.MARKER_SUFFIX}"

    def mark_code(self, code: str, language: str = "python") -> str:
        """Add attribution marker to code."""
        content_hash = hashlib.sha256(code.encode()).hexdigest()
        marker = self.create_marker(content_hash)

        comment_styles = {
            "python": f"# {marker}",
            "javascript": f"// {marker}",
            "java": f"// {marker}",
            "html": marker,
            "css": f"/* {marker} */",
        }

        comment = comment_styles.get(language, f"# {marker}")
        return f"{comment}\n{code}"

    def mark_document(self, content: str) -> str:
        """Add attribution marker to document."""
        content_hash = hashlib.sha256(content.encode()).hexdigest()
        marker = self.create_marker(content_hash)
        return f"{content}\n\n{marker}"

    @staticmethod
    def extract_attribution(content: str) -> Optional[Dict[str, Any]]:
        """Extract attribution data from marked content."""
        import re
        pattern = r'<!-- AI-ATTR:(.*?):AI-ATTR -->'
        match = re.search(pattern, content)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                return None
        return None

    @staticmethod
    def is_ai_generated(content: str) -> bool:
        """Check if content has AI attribution marker."""
        return "AI-ATTR:" in content


def create_git_commit_message(description: str, ai_contribution_pct: float) -> str:
    """Create git commit message with AI attribution."""
    ai_note = ""
    if ai_contribution_pct > 0:
        ai_note = f"\n\n🤖 AI Contribution: {ai_contribution_pct:.0f}%"
        ai_note += "\nGenerated with AI assistance per EU AI Act Article 52"

    return f"{description}{ai_note}"
