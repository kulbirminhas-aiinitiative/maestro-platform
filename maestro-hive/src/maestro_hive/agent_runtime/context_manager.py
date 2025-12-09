"""Context Manager - Preserve agent context across sessions (AC-2544-5)."""
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional
from uuid import UUID

from .models import AgentContext

logger = logging.getLogger(__name__)


class ContextManager:
    """Manages agent context persistence (AC-2544-5)."""
    
    def __init__(self, storage_path: Optional[Path] = None):
        self.storage_path = storage_path or Path("/tmp/agent_contexts")
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self._cache: Dict[UUID, AgentContext] = {}
        logger.info("ContextManager initialized")
    
    def save_context(self, context: AgentContext) -> bool:
        """Save context to storage."""
        try:
            file_path = self.storage_path / f"{context.id}.json"
            file_path.write_text(json.dumps(context.to_dict(), indent=2, default=str))
            self._cache[context.id] = context
            logger.debug("Saved context %s", context.id)
            return True
        except Exception as e:
            logger.error("Failed to save context: %s", e)
            return False
    
    def load_context(self, context_id: UUID) -> Optional[AgentContext]:
        """Load context from storage."""
        if context_id in self._cache:
            return self._cache[context_id]
        
        try:
            file_path = self.storage_path / f"{context_id}.json"
            if file_path.exists():
                data = json.loads(file_path.read_text())
                context = AgentContext.from_dict(data)
                self._cache[context_id] = context
                return context
        except Exception as e:
            logger.error("Failed to load context: %s", e)
        return None
    
    def delete_context(self, context_id: UUID) -> bool:
        """Delete context from storage."""
        try:
            file_path = self.storage_path / f"{context_id}.json"
            if file_path.exists():
                file_path.unlink()
            if context_id in self._cache:
                del self._cache[context_id]
            return True
        except Exception as e:
            logger.error("Failed to delete context: %s", e)
            return False
    
    def list_contexts(self) -> list:
        """List all stored contexts."""
        contexts = []
        for file_path in self.storage_path.glob("*.json"):
            try:
                data = json.loads(file_path.read_text())
                contexts.append({
                    "id": data.get("id"),
                    "persona_id": data.get("persona_id"),
                    "message_count": len(data.get("conversation_history", [])),
                    "updated_at": data.get("updated_at"),
                })
            except Exception:
                pass
        return contexts
