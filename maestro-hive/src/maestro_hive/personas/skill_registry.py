#!/usr/bin/env python3
"""
Skill Registry: Central registry for AI skills that can be injected into personas.

This module provides registration, discovery, and management of skills that
can dynamically enhance persona capabilities in the Maestro orchestration system.

Related EPIC: MD-3016 - AI Skill Injection Marketplace
"""

import json
import threading
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Callable
from dataclasses import dataclass, asdict, field
from enum import Enum
import logging
import hashlib

logger = logging.getLogger(__name__)


class SkillCategory(Enum):
    """Categories of skills available in the marketplace."""
    CODE_GENERATION = "code_generation"
    CODE_ANALYSIS = "code_analysis"
    DOCUMENTATION = "documentation"
    TESTING = "testing"
    SECURITY = "security"
    DATA_PROCESSING = "data_processing"
    INTEGRATION = "integration"
    DEVOPS = "devops"
    CUSTOM = "custom"


class SkillStatus(Enum):
    """Status of a registered skill."""
    AVAILABLE = "available"
    DEPRECATED = "deprecated"
    BETA = "beta"
    DISABLED = "disabled"


class SkillCompatibility(Enum):
    """Compatibility level for skill injection."""
    UNIVERSAL = "universal"  # Works with any persona
    SPECIALIZED = "specialized"  # Works with specific persona types
    RESTRICTED = "restricted"  # Requires explicit approval


@dataclass
class SkillRequirement:
    """Requirement for a skill to function properly."""
    type: str  # "capability", "model", "permission"
    value: str
    optional: bool = False


@dataclass
class SkillMetrics:
    """Metrics tracking for skill usage."""
    injection_count: int = 0
    success_count: int = 0
    failure_count: int = 0
    average_execution_time_ms: float = 0.0
    last_used: Optional[str] = None

    def record_usage(self, success: bool, execution_time_ms: float) -> None:
        """Record a skill usage event."""
        self.injection_count += 1
        if success:
            self.success_count += 1
        else:
            self.failure_count += 1

        # Update rolling average
        total_time = self.average_execution_time_ms * (self.injection_count - 1)
        self.average_execution_time_ms = (total_time + execution_time_ms) / self.injection_count
        self.last_used = datetime.utcnow().isoformat()


@dataclass
class SkillDefinition:
    """
    Definition of an injectable AI skill.

    A skill represents a specific capability that can be dynamically
    injected into personas to enhance their functionality.
    """
    id: str
    name: str
    description: str
    category: SkillCategory
    version: str
    prompt_template: str  # Template for skill execution
    input_schema: Dict[str, Any]  # JSON Schema for inputs
    output_schema: Dict[str, Any]  # JSON Schema for outputs
    requirements: List[SkillRequirement] = field(default_factory=list)
    compatibility: SkillCompatibility = SkillCompatibility.UNIVERSAL
    status: SkillStatus = SkillStatus.AVAILABLE
    tags: List[str] = field(default_factory=list)
    author: str = "system"
    license: str = "MIT"
    documentation_url: Optional[str] = None
    metrics: SkillMetrics = field(default_factory=SkillMetrics)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def compute_hash(self) -> str:
        """Compute a hash of the skill definition for integrity checking."""
        content = f"{self.id}:{self.version}:{self.prompt_template}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    def is_compatible_with(self, persona_capabilities: List[str]) -> bool:
        """Check if skill is compatible with given persona capabilities."""
        if self.compatibility == SkillCompatibility.UNIVERSAL:
            return True

        required_caps = [
            req.value for req in self.requirements
            if req.type == "capability" and not req.optional
        ]
        persona_caps_lower = {c.lower() for c in persona_capabilities}
        return all(cap.lower() in persona_caps_lower for cap in required_caps)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        data = asdict(self)
        data['category'] = self.category.value
        data['status'] = self.status.value
        data['compatibility'] = self.compatibility.value
        data['requirements'] = [asdict(r) for r in self.requirements]
        data['metrics'] = asdict(self.metrics)
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SkillDefinition':
        """Create SkillDefinition from dictionary."""
        data = dict(data)  # Copy to avoid mutation
        if isinstance(data.get('category'), str):
            data['category'] = SkillCategory(data['category'])
        if isinstance(data.get('status'), str):
            data['status'] = SkillStatus(data['status'])
        if isinstance(data.get('compatibility'), str):
            data['compatibility'] = SkillCompatibility(data['compatibility'])
        if data.get('requirements'):
            data['requirements'] = [
                SkillRequirement(**r) if isinstance(r, dict) else r
                for r in data['requirements']
            ]
        if data.get('metrics') and isinstance(data['metrics'], dict):
            data['metrics'] = SkillMetrics(**data['metrics'])
        return cls(**data)


class SkillRegistry:
    """
    Central registry for AI skills.

    Provides registration, discovery, and lifecycle management for skills
    that can be injected into personas. Supports capability-based matching,
    versioning, and usage metrics tracking.
    """

    _instance: Optional['SkillRegistry'] = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        """Singleton pattern for global registry access."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, persistence_path: Optional[str] = None):
        """
        Initialize the skill registry.

        Args:
            persistence_path: Path to JSON file for persistence
        """
        if hasattr(self, '_initialized') and self._initialized:
            return

        self._skills: Dict[str, SkillDefinition] = {}
        self._registry_lock = threading.RLock()
        self._persistence_path = Path(persistence_path) if persistence_path else None
        self._category_index: Dict[SkillCategory, Set[str]] = {}
        self._tag_index: Dict[str, Set[str]] = {}
        self._event_handlers: Dict[str, List[Callable]] = {
            'skill_registered': [],
            'skill_updated': [],
            'skill_removed': [],
            'skill_injected': []
        }
        self._initialized = True

        # Load persisted skills
        if self._persistence_path and self._persistence_path.exists():
            self._load_from_file()

        # Register default skills
        self._register_defaults()

        logger.info("SkillRegistry initialized")

    def register(self, skill: SkillDefinition, overwrite: bool = False) -> bool:
        """
        Register a new skill.

        Args:
            skill: SkillDefinition to register
            overwrite: Allow overwriting existing skill

        Returns:
            True if registration successful
        """
        with self._registry_lock:
            if skill.id in self._skills and not overwrite:
                logger.warning(f"Skill already registered: {skill.id}")
                return False

            # Update timestamp if overwriting
            if skill.id in self._skills:
                skill.updated_at = datetime.utcnow().isoformat()
                self._emit_event('skill_updated', skill)
            else:
                self._emit_event('skill_registered', skill)

            self._skills[skill.id] = skill
            self._update_indices(skill)
            self._persist()

            logger.info(f"Skill registered: {skill.id} ({skill.name}) v{skill.version}")
            return True

    def unregister(self, skill_id: str) -> bool:
        """
        Remove a skill from the registry.

        Args:
            skill_id: ID of skill to remove

        Returns:
            True if skill was found and removed
        """
        with self._registry_lock:
            if skill_id not in self._skills:
                return False

            skill = self._skills.pop(skill_id)
            self._remove_from_indices(skill)
            self._emit_event('skill_removed', skill)
            self._persist()

            logger.info(f"Skill unregistered: {skill_id}")
            return True

    def get(self, skill_id: str) -> Optional[SkillDefinition]:
        """
        Get a skill by ID.

        Args:
            skill_id: ID of skill to retrieve

        Returns:
            SkillDefinition or None if not found
        """
        with self._registry_lock:
            return self._skills.get(skill_id)

    def get_version(self, skill_id: str, version: str) -> Optional[SkillDefinition]:
        """
        Get a specific version of a skill.

        Args:
            skill_id: ID of skill
            version: Version string

        Returns:
            SkillDefinition if matching version found
        """
        with self._registry_lock:
            skill = self._skills.get(skill_id)
            if skill and skill.version == version:
                return skill
            return None

    def list_all(
        self,
        status: Optional[SkillStatus] = None,
        category: Optional[SkillCategory] = None
    ) -> List[SkillDefinition]:
        """
        List all registered skills.

        Args:
            status: Filter by status (optional)
            category: Filter by category (optional)

        Returns:
            List of SkillDefinitions
        """
        with self._registry_lock:
            skills = list(self._skills.values())
            if status:
                skills = [s for s in skills if s.status == status]
            if category:
                skills = [s for s in skills if s.category == category]
            return skills

    def find_by_category(self, category: SkillCategory) -> List[SkillDefinition]:
        """
        Find skills by category.

        Args:
            category: Category to search for

        Returns:
            List of matching SkillDefinitions
        """
        with self._registry_lock:
            skill_ids = self._category_index.get(category, set())
            return [self._skills[sid] for sid in skill_ids if sid in self._skills]

    def find_by_tag(self, tag: str) -> List[SkillDefinition]:
        """
        Find skills by tag.

        Args:
            tag: Tag to search for

        Returns:
            List of matching SkillDefinitions
        """
        with self._registry_lock:
            tag_lower = tag.lower()
            skill_ids = self._tag_index.get(tag_lower, set())
            return [self._skills[sid] for sid in skill_ids if sid in self._skills]

    def find_compatible(
        self,
        persona_capabilities: List[str],
        category: Optional[SkillCategory] = None
    ) -> List[SkillDefinition]:
        """
        Find skills compatible with given persona capabilities.

        Args:
            persona_capabilities: List of persona capabilities
            category: Filter by category (optional)

        Returns:
            List of compatible SkillDefinitions
        """
        with self._registry_lock:
            skills = self.list_all(status=SkillStatus.AVAILABLE, category=category)
            return [s for s in skills if s.is_compatible_with(persona_capabilities)]

    def search(
        self,
        query: str,
        status: Optional[SkillStatus] = None
    ) -> List[SkillDefinition]:
        """
        Search skills by name or description.

        Args:
            query: Search query string
            status: Filter by status (optional)

        Returns:
            List of matching SkillDefinitions
        """
        with self._registry_lock:
            query_lower = query.lower()
            skills = self.list_all(status=status)
            return [
                s for s in skills
                if query_lower in s.name.lower() or query_lower in s.description.lower()
            ]

    def update_status(self, skill_id: str, status: SkillStatus) -> bool:
        """
        Update skill status.

        Args:
            skill_id: ID of skill to update
            status: New status

        Returns:
            True if update successful
        """
        with self._registry_lock:
            if skill_id not in self._skills:
                return False

            self._skills[skill_id].status = status
            self._skills[skill_id].updated_at = datetime.utcnow().isoformat()
            self._emit_event('skill_updated', self._skills[skill_id])
            self._persist()

            logger.info(f"Skill {skill_id} status updated to {status.value}")
            return True

    def record_injection(
        self,
        skill_id: str,
        success: bool,
        execution_time_ms: float
    ) -> None:
        """
        Record a skill injection event for metrics.

        Args:
            skill_id: ID of injected skill
            success: Whether injection was successful
            execution_time_ms: Execution time in milliseconds
        """
        with self._registry_lock:
            if skill_id in self._skills:
                self._skills[skill_id].metrics.record_usage(success, execution_time_ms)
                self._emit_event('skill_injected', self._skills[skill_id])
                self._persist()

    def get_marketplace_catalog(self) -> Dict[str, Any]:
        """
        Get catalog data for the skill marketplace.

        Returns:
            Dictionary with marketplace catalog data
        """
        with self._registry_lock:
            available_skills = self.list_all(status=SkillStatus.AVAILABLE)

            # Group by category
            by_category: Dict[str, List[Dict]] = {}
            for skill in available_skills:
                cat_name = skill.category.value
                if cat_name not in by_category:
                    by_category[cat_name] = []
                by_category[cat_name].append({
                    'id': skill.id,
                    'name': skill.name,
                    'description': skill.description,
                    'version': skill.version,
                    'tags': skill.tags,
                    'compatibility': skill.compatibility.value,
                    'metrics': {
                        'usage_count': skill.metrics.injection_count,
                        'success_rate': (
                            skill.metrics.success_count / skill.metrics.injection_count * 100
                            if skill.metrics.injection_count > 0 else 0
                        )
                    }
                })

            return {
                'total_skills': len(available_skills),
                'categories': by_category,
                'updated_at': datetime.utcnow().isoformat()
            }

    def on_event(self, event: str, handler: Callable) -> None:
        """
        Register an event handler.

        Args:
            event: Event name
            handler: Handler function
        """
        if event in self._event_handlers:
            self._event_handlers[event].append(handler)

    def _emit_event(self, event: str, skill: SkillDefinition) -> None:
        """Emit an event to all registered handlers."""
        for handler in self._event_handlers.get(event, []):
            try:
                handler(skill)
            except Exception as e:
                logger.error(f"Event handler error for {event}: {e}")

    def _update_indices(self, skill: SkillDefinition) -> None:
        """Update indices for a skill."""
        # Category index
        if skill.category not in self._category_index:
            self._category_index[skill.category] = set()
        self._category_index[skill.category].add(skill.id)

        # Tag index
        for tag in skill.tags:
            tag_lower = tag.lower()
            if tag_lower not in self._tag_index:
                self._tag_index[tag_lower] = set()
            self._tag_index[tag_lower].add(skill.id)

    def _remove_from_indices(self, skill: SkillDefinition) -> None:
        """Remove skill from indices."""
        # Category index
        if skill.category in self._category_index:
            self._category_index[skill.category].discard(skill.id)

        # Tag index
        for tag in skill.tags:
            tag_lower = tag.lower()
            if tag_lower in self._tag_index:
                self._tag_index[tag_lower].discard(skill.id)

    def _persist(self) -> None:
        """Persist registry to file."""
        if not self._persistence_path:
            return

        data = {
            'skills': [s.to_dict() for s in self._skills.values()],
            'updated_at': datetime.utcnow().isoformat()
        }

        self._persistence_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self._persistence_path, 'w') as f:
            json.dump(data, f, indent=2)

    def _load_from_file(self) -> None:
        """Load registry from file."""
        try:
            with open(self._persistence_path, 'r') as f:
                data = json.load(f)

            for skill_data in data.get('skills', []):
                skill = SkillDefinition.from_dict(skill_data)
                self._skills[skill.id] = skill
                self._update_indices(skill)

            logger.info(f"Loaded {len(self._skills)} skills from {self._persistence_path}")
        except Exception as e:
            logger.error(f"Failed to load skills: {e}")

    def _register_defaults(self) -> None:
        """Register default system skills."""
        defaults = [
            SkillDefinition(
                id="code_review",
                name="Code Review",
                description="Perform comprehensive code review with best practices analysis",
                category=SkillCategory.CODE_ANALYSIS,
                version="1.0.0",
                prompt_template="""Review the following code for:
1. Code quality and best practices
2. Potential bugs or issues
3. Security vulnerabilities
4. Performance considerations
5. Maintainability

Code to review:
{code}

Provide detailed feedback with specific line references.""",
                input_schema={
                    "type": "object",
                    "properties": {
                        "code": {"type": "string"},
                        "language": {"type": "string"}
                    },
                    "required": ["code"]
                },
                output_schema={
                    "type": "object",
                    "properties": {
                        "issues": {"type": "array"},
                        "suggestions": {"type": "array"},
                        "score": {"type": "number"}
                    }
                },
                tags=["code", "review", "quality"]
            ),
            SkillDefinition(
                id="test_generation",
                name="Test Generation",
                description="Generate unit tests for given code",
                category=SkillCategory.TESTING,
                version="1.0.0",
                prompt_template="""Generate comprehensive unit tests for the following code:

{code}

Include tests for:
- Normal operation
- Edge cases
- Error conditions
- Boundary values

Use {test_framework} as the testing framework.""",
                input_schema={
                    "type": "object",
                    "properties": {
                        "code": {"type": "string"},
                        "test_framework": {"type": "string", "default": "pytest"}
                    },
                    "required": ["code"]
                },
                output_schema={
                    "type": "object",
                    "properties": {
                        "test_code": {"type": "string"},
                        "coverage_estimate": {"type": "number"}
                    }
                },
                tags=["testing", "unit-tests", "automation"]
            ),
            SkillDefinition(
                id="documentation_writer",
                name="Documentation Writer",
                description="Generate technical documentation from code",
                category=SkillCategory.DOCUMENTATION,
                version="1.0.0",
                prompt_template="""Generate {doc_type} documentation for:

{code}

Include:
- Purpose and overview
- Parameters/arguments
- Return values
- Usage examples
- Notes and caveats""",
                input_schema={
                    "type": "object",
                    "properties": {
                        "code": {"type": "string"},
                        "doc_type": {"type": "string", "enum": ["api", "readme", "inline"]}
                    },
                    "required": ["code"]
                },
                output_schema={
                    "type": "object",
                    "properties": {
                        "documentation": {"type": "string"},
                        "format": {"type": "string"}
                    }
                },
                tags=["documentation", "technical-writing"]
            ),
            SkillDefinition(
                id="security_scan",
                name="Security Scanner",
                description="Scan code for security vulnerabilities",
                category=SkillCategory.SECURITY,
                version="1.0.0",
                prompt_template="""Perform a security analysis on the following code:

{code}

Check for:
- OWASP Top 10 vulnerabilities
- Injection flaws
- Authentication issues
- Data exposure risks
- Configuration security

Provide severity ratings and remediation suggestions.""",
                input_schema={
                    "type": "object",
                    "properties": {
                        "code": {"type": "string"},
                        "language": {"type": "string"}
                    },
                    "required": ["code"]
                },
                output_schema={
                    "type": "object",
                    "properties": {
                        "vulnerabilities": {"type": "array"},
                        "risk_score": {"type": "number"},
                        "recommendations": {"type": "array"}
                    }
                },
                requirements=[
                    SkillRequirement(type="capability", value="security")
                ],
                compatibility=SkillCompatibility.SPECIALIZED,
                tags=["security", "vulnerability", "owasp"]
            )
        ]

        for skill in defaults:
            if skill.id not in self._skills:
                self._skills[skill.id] = skill
                self._update_indices(skill)


# Convenience function to get singleton instance
def get_skill_registry(**kwargs) -> SkillRegistry:
    """Get the singleton SkillRegistry instance."""
    return SkillRegistry(**kwargs)
