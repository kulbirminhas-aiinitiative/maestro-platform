#!/usr/bin/env python3
"""
Requirements Ingestion: Parse and ingest requirements from various formats.

This module provides parsers for multiple requirement formats including
Markdown user stories, JIRA tickets, BDD feature files, and natural language.
"""

import re
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict, field
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class RequirementType(Enum):
    """Type of requirement."""
    FUNCTIONAL = "functional"
    NON_FUNCTIONAL = "non_functional"
    USER_STORY = "user_story"
    ACCEPTANCE_CRITERIA = "acceptance_criteria"
    TECHNICAL = "technical"
    CONSTRAINT = "constraint"


class RequirementPriority(Enum):
    """Priority level of requirement."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class Requirement:
    """
    A parsed requirement.

    Represents a single requirement extracted from any source format.
    """
    id: str
    title: str
    description: str
    type: RequirementType
    priority: RequirementPriority = RequirementPriority.MEDIUM
    acceptance_criteria: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    source: str = ""
    source_location: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        data = asdict(self)
        data['type'] = self.type.value
        data['priority'] = self.priority.value
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Requirement':
        """Create from dictionary."""
        data = dict(data)
        if isinstance(data.get('type'), str):
            data['type'] = RequirementType(data['type'])
        if isinstance(data.get('priority'), str):
            data['priority'] = RequirementPriority(data['priority'])
        return cls(**data)


@dataclass
class IngestionResult:
    """Result of a requirements ingestion operation."""
    requirements: List[Requirement]
    source: str
    source_type: str
    parse_errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())


class RequirementsIngester:
    """
    Parse and ingest requirements from various formats.

    Supported formats:
    - Markdown user stories
    - JIRA ticket descriptions
    - BDD feature files (Gherkin)
    - Natural language requirements
    """

    def __init__(self, jira_client: Optional[Any] = None):
        """
        Initialize the ingester.

        Args:
            jira_client: Optional JIRA client for ticket ingestion
        """
        self._jira_client = jira_client
        self._requirement_counter = 0

    def ingest_markdown(self, content: str, source: str = "markdown") -> IngestionResult:
        """
        Ingest requirements from Markdown content.

        Parses user stories in format:
        ## User Story: [Title]
        As a [role], I want [goal] so that [benefit].

        ### Acceptance Criteria
        - [ ] Criterion 1
        - [ ] Criterion 2

        Args:
            content: Markdown content to parse
            source: Source identifier

        Returns:
            IngestionResult with parsed requirements
        """
        requirements: List[Requirement] = []
        errors: List[str] = []
        warnings: List[str] = []

        # Pattern for user stories
        story_pattern = r'##\s*(?:User Story:?\s*)?(.+?)\n(.*?)(?=\n##|\Z)'
        stories = re.findall(story_pattern, content, re.DOTALL | re.IGNORECASE)

        for title, body in stories:
            title = title.strip()
            body = body.strip()

            # Parse "As a... I want... so that..." pattern
            story_match = re.search(
                r'As\s+(?:a|an)\s+(.+?),?\s+I\s+want\s+(.+?)\s+so\s+that\s+(.+?)(?:\.|$)',
                body,
                re.IGNORECASE | re.DOTALL
            )

            if story_match:
                role, goal, benefit = story_match.groups()
                description = f"As a {role.strip()}, I want {goal.strip()} so that {benefit.strip()}."
            else:
                description = body.split('\n')[0] if body else title

            # Extract acceptance criteria
            ac_pattern = r'(?:###?\s*)?Acceptance Criteria:?\s*(.*?)(?=\n##|\Z)'
            ac_match = re.search(ac_pattern, body, re.DOTALL | re.IGNORECASE)

            acceptance_criteria = []
            if ac_match:
                ac_text = ac_match.group(1)
                # Parse checkbox items or bullet points
                ac_items = re.findall(r'[-*]\s*\[?\s*[xX ]?\s*\]?\s*(.+)', ac_text)
                acceptance_criteria = [item.strip() for item in ac_items if item.strip()]

            # Extract tags from hashtags
            tags = re.findall(r'#(\w+)', body)

            req_id = self._generate_id("MD")
            requirements.append(Requirement(
                id=req_id,
                title=title,
                description=description,
                type=RequirementType.USER_STORY,
                acceptance_criteria=acceptance_criteria,
                tags=tags,
                source=source,
                source_location="markdown"
            ))

        if not requirements:
            warnings.append("No user stories found in markdown content")

        return IngestionResult(
            requirements=requirements,
            source=source,
            source_type="markdown",
            parse_errors=errors,
            warnings=warnings,
            metadata={"stories_found": len(requirements)}
        )

    def ingest_jira(
        self,
        ticket_key: str,
        include_subtasks: bool = True
    ) -> IngestionResult:
        """
        Ingest requirements from a JIRA ticket.

        Args:
            ticket_key: JIRA ticket key (e.g., 'PROJ-123')
            include_subtasks: Whether to include subtasks as separate requirements

        Returns:
            IngestionResult with parsed requirements
        """
        requirements: List[Requirement] = []
        errors: List[str] = []
        warnings: List[str] = []

        if not self._jira_client:
            # Mock implementation for when JIRA client not available
            warnings.append("JIRA client not configured, returning mock requirement")
            requirements.append(Requirement(
                id=self._generate_id("JIRA"),
                title=f"Requirement from {ticket_key}",
                description=f"Requirement ingested from JIRA ticket {ticket_key}",
                type=RequirementType.USER_STORY,
                source=ticket_key,
                source_location="jira"
            ))
            return IngestionResult(
                requirements=requirements,
                source=ticket_key,
                source_type="jira",
                warnings=warnings
            )

        try:
            # Fetch ticket from JIRA
            issue = self._jira_client.get_issue(ticket_key)

            # Parse main ticket
            description = issue.get('description', '') or ''

            # Try to extract acceptance criteria from description
            ac_pattern = r'h\d\.\s*Acceptance Criteria\s*(.*?)(?=h\d\.|\Z)'
            ac_match = re.search(ac_pattern, description, re.DOTALL | re.IGNORECASE)

            acceptance_criteria = []
            if ac_match:
                ac_text = ac_match.group(1)
                ac_items = re.findall(r'\*\s*(.+)', ac_text)
                acceptance_criteria = [item.strip() for item in ac_items]

            # Map JIRA priority
            jira_priority = issue.get('priority', {}).get('name', 'Medium').lower()
            priority_map = {
                'highest': RequirementPriority.CRITICAL,
                'high': RequirementPriority.HIGH,
                'medium': RequirementPriority.MEDIUM,
                'low': RequirementPriority.LOW,
                'lowest': RequirementPriority.LOW
            }
            priority = priority_map.get(jira_priority, RequirementPriority.MEDIUM)

            requirements.append(Requirement(
                id=ticket_key,
                title=issue.get('summary', ticket_key),
                description=description,
                type=RequirementType.USER_STORY,
                priority=priority,
                acceptance_criteria=acceptance_criteria,
                tags=issue.get('labels', []),
                source=ticket_key,
                source_location="jira",
                metadata={
                    'issue_type': issue.get('issuetype', {}).get('name'),
                    'status': issue.get('status', {}).get('name')
                }
            ))

            # Include subtasks if requested
            if include_subtasks:
                subtasks = issue.get('subtasks', [])
                for subtask in subtasks:
                    sub_req = self.ingest_jira(subtask['key'], include_subtasks=False)
                    requirements.extend(sub_req.requirements)

        except Exception as e:
            errors.append(f"Failed to fetch JIRA ticket {ticket_key}: {str(e)}")
            logger.error(f"JIRA ingestion error: {e}")

        return IngestionResult(
            requirements=requirements,
            source=ticket_key,
            source_type="jira",
            parse_errors=errors,
            warnings=warnings,
            metadata={"ticket_key": ticket_key}
        )

    def ingest_bdd(self, feature_file: Path) -> IngestionResult:
        """
        Ingest requirements from a BDD feature file (Gherkin syntax).

        Args:
            feature_file: Path to .feature file

        Returns:
            IngestionResult with parsed requirements
        """
        requirements: List[Requirement] = []
        errors: List[str] = []
        warnings: List[str] = []

        try:
            content = feature_file.read_text()
        except Exception as e:
            errors.append(f"Failed to read feature file: {str(e)}")
            return IngestionResult(
                requirements=[],
                source=str(feature_file),
                source_type="bdd",
                parse_errors=errors
            )

        # Parse Feature
        feature_match = re.search(r'Feature:\s*(.+?)(?:\n|$)', content)
        feature_name = feature_match.group(1).strip() if feature_match else feature_file.stem

        # Parse Feature description
        feature_desc_match = re.search(
            r'Feature:.*?\n(.*?)(?=\n\s*(?:Background|Scenario|@))',
            content,
            re.DOTALL
        )
        feature_description = ""
        if feature_desc_match:
            feature_description = feature_desc_match.group(1).strip()

        # Parse Scenarios
        scenario_pattern = r'(@.+?\n\s*)?\s*Scenario(?:\s+Outline)?:\s*(.+?)\n(.*?)(?=\n\s*(?:@|Scenario)|$)'
        scenarios = re.findall(scenario_pattern, content, re.DOTALL)

        for tags_str, scenario_name, scenario_body in scenarios:
            # Parse tags
            tags = re.findall(r'@(\w+)', tags_str) if tags_str else []

            # Extract Given/When/Then as acceptance criteria
            steps = re.findall(r'(Given|When|Then|And|But)\s+(.+)', scenario_body)
            acceptance_criteria = [f"{step[0]} {step[1].strip()}" for step in steps]

            req_id = self._generate_id("BDD")
            requirements.append(Requirement(
                id=req_id,
                title=scenario_name.strip(),
                description=f"Feature: {feature_name}\n{feature_description}",
                type=RequirementType.ACCEPTANCE_CRITERIA,
                acceptance_criteria=acceptance_criteria,
                tags=tags,
                source=str(feature_file),
                source_location=f"bdd:{feature_file.name}",
                metadata={"feature": feature_name, "scenario": scenario_name.strip()}
            ))

        if not requirements:
            warnings.append(f"No scenarios found in {feature_file}")

        return IngestionResult(
            requirements=requirements,
            source=str(feature_file),
            source_type="bdd",
            parse_errors=errors,
            warnings=warnings,
            metadata={"feature": feature_name, "scenarios_found": len(requirements)}
        )

    def parse_natural_language(
        self,
        text: str,
        context: Optional[str] = None
    ) -> IngestionResult:
        """
        Parse requirements from natural language text.

        Uses heuristics to identify requirements statements.

        Args:
            text: Natural language text to parse
            context: Optional context about the requirements domain

        Returns:
            IngestionResult with parsed requirements
        """
        requirements: List[Requirement] = []
        errors: List[str] = []
        warnings: List[str] = []

        # Split into sentences
        sentences = re.split(r'[.!?]\s+', text)

        # Patterns indicating requirements
        requirement_patterns = [
            (r'(?:system|application|user)\s+(?:must|shall|should|will)\s+(.+)', RequirementType.FUNCTIONAL),
            (r'(?:the\s+)?(\w+)\s+(?:must|shall|should)\s+be\s+able\s+to\s+(.+)', RequirementType.FUNCTIONAL),
            (r'(?:performance|security|scalability|availability)\s+requirement[s]?:\s*(.+)', RequirementType.NON_FUNCTIONAL),
            (r'(?:constraint|limitation):\s*(.+)', RequirementType.CONSTRAINT),
            (r'As\s+(?:a|an)\s+.+,\s+I\s+want\s+.+', RequirementType.USER_STORY),
        ]

        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue

            for pattern, req_type in requirement_patterns:
                match = re.search(pattern, sentence, re.IGNORECASE)
                if match:
                    req_id = self._generate_id("NL")
                    title = match.group(0)[:100]  # Truncate for title

                    # Determine priority from keywords
                    priority = RequirementPriority.MEDIUM
                    if re.search(r'\b(critical|essential|required)\b', sentence, re.IGNORECASE):
                        priority = RequirementPriority.CRITICAL
                    elif re.search(r'\b(important|necessary)\b', sentence, re.IGNORECASE):
                        priority = RequirementPriority.HIGH
                    elif re.search(r'\b(nice.to.have|optional)\b', sentence, re.IGNORECASE):
                        priority = RequirementPriority.LOW

                    requirements.append(Requirement(
                        id=req_id,
                        title=title,
                        description=sentence,
                        type=req_type,
                        priority=priority,
                        source="natural_language",
                        source_location="text",
                        metadata={"context": context} if context else {}
                    ))
                    break

        if not requirements:
            warnings.append("No requirements patterns found in text")

        return IngestionResult(
            requirements=requirements,
            source="natural_language",
            source_type="natural_language",
            parse_errors=errors,
            warnings=warnings,
            metadata={"sentences_analyzed": len(sentences)}
        )

    def _generate_id(self, prefix: str) -> str:
        """Generate a unique requirement ID."""
        self._requirement_counter += 1
        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        return f"REQ-{prefix}-{timestamp}-{self._requirement_counter:04d}"


# Convenience function
def ingest_requirements(
    source: str,
    source_type: str = "auto",
    **kwargs
) -> IngestionResult:
    """
    Convenience function to ingest requirements.

    Args:
        source: Source content or path
        source_type: Type of source (markdown, jira, bdd, natural_language, auto)
        **kwargs: Additional arguments for specific ingesters

    Returns:
        IngestionResult with parsed requirements
    """
    ingester = RequirementsIngester(**kwargs)

    if source_type == "auto":
        # Auto-detect source type
        if source.endswith('.feature'):
            source_type = "bdd"
        elif source.startswith(('MD-', 'PROJ-', 'JIRA-')):
            source_type = "jira"
        elif '##' in source or '# ' in source:
            source_type = "markdown"
        else:
            source_type = "natural_language"

    if source_type == "markdown":
        return ingester.ingest_markdown(source)
    elif source_type == "jira":
        return ingester.ingest_jira(source)
    elif source_type == "bdd":
        return ingester.ingest_bdd(Path(source))
    elif source_type == "natural_language":
        return ingester.parse_natural_language(source)
    else:
        raise ValueError(f"Unknown source type: {source_type}")
