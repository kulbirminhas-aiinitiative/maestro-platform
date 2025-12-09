"""
Decision JIRA Service

Creates and manages JIRA subtasks for AI agent decisions with
verbosity-aware filtering and status synchronization.
"""

import os
import asyncio
import logging
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class JiraStatus(Enum):
    """JIRA status mappings."""
    TO_DO = "To Do"
    IN_PROGRESS = "In Progress"
    DONE = "Done"
    BLOCKED = "Blocked"


@dataclass
class DecisionEvent:
    """Decision event from the event bus."""
    id: str
    event_type: str
    decision_type: str
    task_id: str
    persona_id: Optional[str]
    inputs: Dict[str, Any]
    outputs: Dict[str, Any]
    reasoning: Optional[str]
    timestamp: datetime
    verbosity_level: str
    confidence: float = 0.0


@dataclass
class JiraSubtask:
    """Represents a JIRA subtask."""
    key: str
    summary: str
    status: JiraStatus
    description: str
    created: datetime


class ADFBuilder:
    """Atlassian Document Format builder for rich JIRA content."""
    
    def __init__(self):
        self.content = []
    
    def heading(self, text: str, level: int = 2) -> 'ADFBuilder':
        """Add a heading."""
        self.content.append({
            "type": "heading",
            "attrs": {"level": level},
            "content": [{"type": "text", "text": text}]
        })
        return self
    
    def paragraph(self, text: str) -> 'ADFBuilder':
        """Add a paragraph."""
        self.content.append({
            "type": "paragraph",
            "content": [{"type": "text", "text": text}]
        })
        return self
    
    def code_block(self, code: str, language: str = "python") -> 'ADFBuilder':
        """Add a code block."""
        self.content.append({
            "type": "codeBlock",
            "attrs": {"language": language},
            "content": [{"type": "text", "text": code}]
        })
        return self
    
    def bullet_list(self, items: List[str]) -> 'ADFBuilder':
        """Add a bullet list."""
        list_items = []
        for item in items:
            list_items.append({
                "type": "listItem",
                "content": [{
                    "type": "paragraph",
                    "content": [{"type": "text", "text": item}]
                }]
            })
        self.content.append({
            "type": "bulletList",
            "content": list_items
        })
        return self
    
    def table(self, headers: List[str], rows: List[List[str]]) -> 'ADFBuilder':
        """Add a table."""
        table_rows = []
        
        # Header row
        header_cells = []
        for header in headers:
            header_cells.append({
                "type": "tableHeader",
                "content": [{"type": "paragraph", "content": [{"type": "text", "text": header}]}]
            })
        table_rows.append({"type": "tableRow", "content": header_cells})
        
        # Data rows
        for row in rows:
            data_cells = []
            for cell in row:
                data_cells.append({
                    "type": "tableCell",
                    "content": [{"type": "paragraph", "content": [{"type": "text", "text": str(cell)}]}]
                })
            table_rows.append({"type": "tableRow", "content": data_cells})
        
        self.content.append({
            "type": "table",
            "attrs": {"isNumberColumnEnabled": False, "layout": "default"},
            "content": table_rows
        })
        return self
    
    def build(self) -> Dict[str, Any]:
        """Build the ADF document."""
        return {
            "type": "doc",
            "version": 1,
            "content": self.content
        }


class DecisionJiraService:
    """
    Service for creating and managing JIRA subtasks for AI decisions.
    
    Integrates with VerbosityController to filter decisions based on
    current verbosity level, and uses ADFBuilder for rich formatting.
    """
    
    # Event types that should always create subtasks
    CRITICAL_EVENTS = {
        "error_recovered",
        "quality_gate_failed",
        "security_issue",
        "critical_failure",
    }
    
    # Event types for major decisions (OPTIMIZED level)
    MAJOR_EVENTS = {
        "blueprint_selected",
        "persona_completed",
        "quality_gate_evaluated",
        "artifact_generated",
    }
    
    def __init__(
        self,
        jira_url: Optional[str] = None,
        jira_email: Optional[str] = None,
        jira_token: Optional[str] = None,
        parent_epic_key: Optional[str] = None,
        verbosity_level: str = "learning",
    ):
        """
        Initialize the Decision JIRA Service.
        
        Args:
            jira_url: JIRA instance URL
            jira_email: JIRA authentication email
            jira_token: JIRA API token
            parent_epic_key: Parent EPIC for subtasks
            verbosity_level: Current verbosity level
        """
        self.jira_url = jira_url or os.getenv("JIRA_URL", "https://your-instance.atlassian.net")
        self.jira_email = jira_email or os.getenv("JIRA_EMAIL")
        self.jira_token = jira_token or os.getenv("JIRA_API_TOKEN")
        self.parent_epic_key = parent_epic_key
        self._verbosity_level = verbosity_level
        self._subtask_cache: Dict[str, JiraSubtask] = {}
        
        logger.info(f"DecisionJiraService initialized with verbosity: {verbosity_level}")
    
    @property
    def verbosity_level(self) -> str:
        """Get current verbosity level."""
        return self._verbosity_level
    
    @verbosity_level.setter
    def verbosity_level(self, level: str):
        """Set verbosity level."""
        old_level = self._verbosity_level
        self._verbosity_level = level
        logger.info(f"Verbosity level changed: {old_level} -> {level}")
    
    def should_create_subtask(self, decision: DecisionEvent) -> bool:
        """
        Determine if a subtask should be created based on verbosity level.
        
        Args:
            decision: The decision event to evaluate
            
        Returns:
            True if subtask should be created
        """
        event_type = decision.event_type
        level = self._verbosity_level
        
        # Critical events always create subtasks
        if event_type in self.CRITICAL_EVENTS:
            return True
        
        # Production: only critical events
        if level == "production":
            return False
        
        # Optimized: major events
        if level == "optimized":
            return event_type in self.MAJOR_EVENTS
        
        # Learning: all events
        return True
    
    def _build_subtask_description(self, decision: DecisionEvent) -> Dict[str, Any]:
        """Build rich ADF description for the subtask."""
        builder = ADFBuilder()
        
        builder.heading("Decision Details", 2)
        builder.paragraph(f"Event Type: {decision.event_type}")
        builder.paragraph(f"Decision Type: {decision.decision_type}")
        builder.paragraph(f"Task ID: {decision.task_id}")
        
        if decision.persona_id:
            builder.paragraph(f"Persona: {decision.persona_id}")
        
        if decision.reasoning:
            builder.heading("Reasoning", 3)
            builder.paragraph(decision.reasoning)
        
        builder.heading("Inputs", 3)
        if decision.inputs:
            items = [f"{k}: {v}" for k, v in decision.inputs.items()]
            builder.bullet_list(items[:10])  # Limit to first 10
        
        builder.heading("Outputs", 3)
        if decision.outputs:
            items = [f"{k}: {v}" for k, v in decision.outputs.items()]
            builder.bullet_list(items[:10])
        
        builder.heading("Metadata", 3)
        builder.table(
            ["Property", "Value"],
            [
                ["Confidence", f"{decision.confidence:.2%}"],
                ["Verbosity Level", decision.verbosity_level],
                ["Timestamp", decision.timestamp.isoformat()],
            ]
        )
        
        return builder.build()
    
    async def create_decision_subtask(
        self,
        decision: DecisionEvent,
        parent_key: Optional[str] = None
    ) -> Optional[str]:
        """
        Create a JIRA subtask for a decision event.
        
        Args:
            decision: The decision event
            parent_key: Parent issue key (overrides default)
            
        Returns:
            The created subtask key, or None if filtered out
        """
        if not self.should_create_subtask(decision):
            logger.debug(f"Skipping subtask for {decision.event_type} (verbosity: {self._verbosity_level})")
            return None
        
        parent = parent_key or self.parent_epic_key
        if not parent:
            logger.warning("No parent key specified for subtask creation")
            return None
        
        summary = f"[{decision.event_type.upper()}] {decision.decision_type}"
        if decision.persona_id:
            summary += f" ({decision.persona_id})"
        
        description = self._build_subtask_description(decision)
        
        # In a real implementation, this would call the JIRA API
        # For now, we simulate the creation
        subtask_key = f"{parent.split('-')[0]}-{hash(decision.id) % 10000}"
        
        subtask = JiraSubtask(
            key=subtask_key,
            summary=summary,
            status=JiraStatus.TO_DO,
            description=str(description),
            created=datetime.now()
        )
        
        self._subtask_cache[subtask_key] = subtask
        logger.info(f"Created subtask {subtask_key} for decision {decision.id}")
        
        return subtask_key
    
    async def update_subtask_status(
        self,
        subtask_key: str,
        status: JiraStatus
    ) -> bool:
        """
        Update the status of a subtask.
        
        Args:
            subtask_key: The subtask key
            status: New status
            
        Returns:
            True if successful
        """
        if subtask_key in self._subtask_cache:
            self._subtask_cache[subtask_key].status = status
            logger.info(f"Updated {subtask_key} status to {status.value}")
            return True
        
        logger.warning(f"Subtask {subtask_key} not found in cache")
        return False
    
    async def get_subtask(self, subtask_key: str) -> Optional[JiraSubtask]:
        """Get a subtask by key."""
        return self._subtask_cache.get(subtask_key)
    
    async def list_decision_subtasks(
        self,
        parent_key: Optional[str] = None,
        status: Optional[JiraStatus] = None
    ) -> List[JiraSubtask]:
        """List subtasks, optionally filtered by parent or status."""
        subtasks = list(self._subtask_cache.values())
        
        if status:
            subtasks = [s for s in subtasks if s.status == status]
        
        return subtasks
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get statistics about created subtasks."""
        subtasks = list(self._subtask_cache.values())
        
        by_status = {}
        for subtask in subtasks:
            status = subtask.status.value
            by_status[status] = by_status.get(status, 0) + 1
        
        return {
            "total_subtasks": len(subtasks),
            "by_status": by_status,
            "verbosity_level": self._verbosity_level,
        }
