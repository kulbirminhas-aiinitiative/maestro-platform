"""
Field Mapper for Maestro-JIRA Synchronization.

Handles bidirectional field mapping and transformation.
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any, Callable, List
from enum import Enum


class MappingDirection(Enum):
    """Mapping direction."""
    TO_JIRA = "to_jira"
    FROM_JIRA = "from_jira"
    BIDIRECTIONAL = "bidirectional"


@dataclass
class FieldMapping:
    """Field mapping configuration."""
    maestro_field: str
    jira_field: str
    direction: MappingDirection = MappingDirection.BIDIRECTIONAL
    transformer_to_jira: Optional[Callable[[Any], Any]] = None
    transformer_from_jira: Optional[Callable[[Any], Any]] = None
    required: bool = False
    default_value: Any = None


class FieldMapper:
    """
    Field mapper for Maestro-JIRA synchronization.

    Handles:
    - Field name mapping
    - Value transformation
    - Type conversion
    - Nested field access
    """

    # Default field mappings
    DEFAULT_MAPPINGS = [
        FieldMapping("summary", "summary"),
        FieldMapping("description", "description"),
        FieldMapping("status", "status.name"),
        FieldMapping("assignee", "assignee.emailAddress"),
        FieldMapping("priority", "priority.name"),
        FieldMapping("labels", "labels"),
        FieldMapping("due_date", "duedate"),
        FieldMapping("created_at", "created"),
        FieldMapping("updated_at", "updated"),
    ]

    def __init__(
        self,
        custom_mappings: Optional[List[FieldMapping]] = None,
        use_defaults: bool = True,
    ):
        """
        Initialize field mapper.

        Args:
            custom_mappings: Custom field mappings
            use_defaults: Include default mappings
        """
        self._mappings: Dict[str, FieldMapping] = {}

        if use_defaults:
            for mapping in self.DEFAULT_MAPPINGS:
                self._mappings[mapping.maestro_field] = mapping

        if custom_mappings:
            for mapping in custom_mappings:
                self._mappings[mapping.maestro_field] = mapping

    def add_mapping(self, mapping: FieldMapping) -> None:
        """Add field mapping."""
        self._mappings[mapping.maestro_field] = mapping

    def remove_mapping(self, maestro_field: str) -> None:
        """Remove field mapping."""
        self._mappings.pop(maestro_field, None)

    def _get_nested_value(self, data: Dict, path: str) -> Any:
        """
        Get value from nested dictionary using dot notation.

        Args:
            data: Dictionary to search
            path: Dot-separated path (e.g., "status.name")

        Returns:
            Value at path or None
        """
        parts = path.split(".")
        current = data

        for part in parts:
            if isinstance(current, dict):
                current = current.get(part)
            else:
                return None

            if current is None:
                return None

        return current

    def _set_nested_value(self, data: Dict, path: str, value: Any) -> None:
        """
        Set value in nested dictionary using dot notation.

        Args:
            data: Dictionary to modify
            path: Dot-separated path
            value: Value to set
        """
        parts = path.split(".")
        current = data

        for part in parts[:-1]:
            if part not in current:
                current[part] = {}
            current = current[part]

        current[parts[-1]] = value

    def to_jira(self, maestro_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Map Maestro data to JIRA format.

        Args:
            maestro_data: Maestro workflow data

        Returns:
            JIRA-formatted data
        """
        jira_data = {}

        for maestro_field, mapping in self._mappings.items():
            if mapping.direction == MappingDirection.FROM_JIRA:
                continue

            value = maestro_data.get(maestro_field)

            if value is None:
                if mapping.required and mapping.default_value is not None:
                    value = mapping.default_value
                else:
                    continue

            # Apply transformer if defined
            if mapping.transformer_to_jira:
                value = mapping.transformer_to_jira(value)

            # Handle nested JIRA fields
            if "." in mapping.jira_field:
                # For update operations, use the top-level field
                # JIRA expects {"status": {"name": "Done"}} for updates
                self._set_nested_value(jira_data, mapping.jira_field, value)
            else:
                jira_data[mapping.jira_field] = value

        return jira_data

    def from_jira(self, jira_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Map JIRA data to Maestro format.

        Args:
            jira_data: JIRA issue data

        Returns:
            Maestro-formatted data
        """
        # JIRA data comes wrapped in "fields" object
        fields = jira_data.get("fields", jira_data)
        maestro_data = {}

        for maestro_field, mapping in self._mappings.items():
            if mapping.direction == MappingDirection.TO_JIRA:
                continue

            # Get value from nested path
            value = self._get_nested_value(fields, mapping.jira_field)

            if value is None:
                if mapping.required and mapping.default_value is not None:
                    value = mapping.default_value
                else:
                    continue

            # Apply transformer if defined
            if mapping.transformer_from_jira:
                value = mapping.transformer_from_jira(value)

            maestro_data[maestro_field] = value

        # Include issue key if available
        if "key" in jira_data:
            maestro_data["jira_key"] = jira_data["key"]

        return maestro_data

    def get_mapping(self, maestro_field: str) -> Optional[FieldMapping]:
        """Get mapping for Maestro field."""
        return self._mappings.get(maestro_field)

    def list_mappings(self) -> List[FieldMapping]:
        """Get all field mappings."""
        return list(self._mappings.values())


# Common transformers
def status_to_jira(maestro_status: str) -> str:
    """Transform Maestro status to JIRA status."""
    status_map = {
        "pending": "To Do",
        "in_progress": "In Progress",
        "review": "In Review",
        "done": "Done",
        "blocked": "Blocked",
    }
    return status_map.get(maestro_status, maestro_status)


def status_from_jira(jira_status: str) -> str:
    """Transform JIRA status to Maestro status."""
    status_map = {
        "To Do": "pending",
        "Open": "pending",
        "In Progress": "in_progress",
        "In Review": "review",
        "Done": "done",
        "Closed": "done",
        "Blocked": "blocked",
    }
    return status_map.get(jira_status, jira_status.lower().replace(" ", "_"))


def priority_to_jira(maestro_priority: str) -> str:
    """Transform Maestro priority to JIRA priority."""
    priority_map = {
        "critical": "Highest",
        "high": "High",
        "medium": "Medium",
        "low": "Low",
        "trivial": "Lowest",
    }
    return priority_map.get(maestro_priority, "Medium")


def priority_from_jira(jira_priority: str) -> str:
    """Transform JIRA priority to Maestro priority."""
    priority_map = {
        "Highest": "critical",
        "High": "high",
        "Medium": "medium",
        "Low": "low",
        "Lowest": "trivial",
    }
    return priority_map.get(jira_priority, "medium")


# Pre-configured mapper with transformers
def create_default_mapper() -> FieldMapper:
    """Create field mapper with default transformers."""
    mappings = [
        FieldMapping("summary", "summary", required=True),
        FieldMapping("description", "description"),
        FieldMapping(
            "status",
            "status.name",
            transformer_to_jira=status_to_jira,
            transformer_from_jira=status_from_jira,
        ),
        FieldMapping(
            "priority",
            "priority.name",
            transformer_to_jira=priority_to_jira,
            transformer_from_jira=priority_from_jira,
        ),
        FieldMapping("assignee", "assignee.emailAddress"),
        FieldMapping("labels", "labels"),
    ]

    return FieldMapper(custom_mappings=mappings, use_defaults=False)
