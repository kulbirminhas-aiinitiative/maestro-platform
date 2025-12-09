#!/usr/bin/env python3
"""
Requirements Decomposition: Breaks down high-level requirements into actionable tasks.

This module handles:
- Decomposition of epics into stories and tasks
- Dependency mapping between tasks
- Complexity analysis for effort estimation
- Change management for requirement updates
"""

import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set
import uuid

logger = logging.getLogger(__name__)


class RequirementType(Enum):
    """Types of requirements."""
    EPIC = "epic"
    STORY = "story"
    TASK = "task"
    SUBTASK = "subtask"
    BUG = "bug"
    SPIKE = "spike"


class DecompositionStrategy(Enum):
    """Strategies for decomposing requirements."""
    FUNCTIONAL = "functional"      # By functionality
    COMPONENT = "component"        # By system component
    USER_JOURNEY = "user_journey"  # By user workflow
    TECHNICAL = "technical"        # By technical concern


class DependencyType(Enum):
    """Types of dependencies between tasks."""
    BLOCKS = "blocks"              # Must complete before
    DEPENDS_ON = "depends_on"      # Requires completion of
    RELATES_TO = "relates_to"      # Related but independent
    DUPLICATES = "duplicates"      # Same as another


@dataclass
class Requirement:
    """A requirement that can be decomposed."""
    req_id: str
    title: str
    description: str
    req_type: RequirementType
    acceptance_criteria: List[str] = field(default_factory=list)
    labels: List[str] = field(default_factory=list)
    priority: int = 5
    story_points: Optional[int] = None
    parent_id: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class Dependency:
    """A dependency between two requirements."""
    source_id: str
    target_id: str
    dependency_type: DependencyType
    description: Optional[str] = None


@dataclass
class DecompositionResult:
    """Result of decomposing a requirement."""
    original_id: str
    strategy_used: DecompositionStrategy
    children: List[Requirement]
    dependencies: List[Dependency]
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class ChangeRecord:
    """Record of a change to a requirement."""
    change_id: str
    req_id: str
    field_changed: str
    old_value: Any
    new_value: Any
    reason: str
    changed_by: str
    timestamp: datetime = field(default_factory=datetime.utcnow)


class RequirementDecomposer:
    """
    Decomposes high-level requirements into smaller, actionable items.

    Implements:
    - decomposition: Break down epics/stories into tasks
    - dependency_mapping: Identify and track dependencies
    - complexity_analysis: Estimate effort and complexity
    - change_management: Track requirement changes
    """

    def __init__(self):
        """Initialize the decomposer."""
        self._requirements: Dict[str, Requirement] = {}
        self._dependencies: List[Dependency] = []
        self._change_history: List[ChangeRecord] = []

    def decompose(
        self,
        requirement: Requirement,
        strategy: DecompositionStrategy = DecompositionStrategy.FUNCTIONAL
    ) -> DecompositionResult:
        """
        Decompose a requirement into smaller items.

        Args:
            requirement: The requirement to decompose
            strategy: Strategy to use for decomposition

        Returns:
            DecompositionResult with children and dependencies
        """
        logger.info(
            f"Decomposing {requirement.req_id} using {strategy.value} strategy"
        )

        # Store original requirement
        self._requirements[requirement.req_id] = requirement

        # Apply decomposition strategy
        if strategy == DecompositionStrategy.FUNCTIONAL:
            children = self._decompose_by_function(requirement)
        elif strategy == DecompositionStrategy.COMPONENT:
            children = self._decompose_by_component(requirement)
        elif strategy == DecompositionStrategy.USER_JOURNEY:
            children = self._decompose_by_user_journey(requirement)
        elif strategy == DecompositionStrategy.TECHNICAL:
            children = self._decompose_by_technical(requirement)
        else:
            children = self._decompose_by_function(requirement)

        # Perform dependency_mapping
        dependencies = self._map_dependencies(children)
        self._dependencies.extend(dependencies)

        # Store children
        for child in children:
            self._requirements[child.req_id] = child

        # Calculate complexity
        complexity = self._analyze_complexity(requirement, children)

        result = DecompositionResult(
            original_id=requirement.req_id,
            strategy_used=strategy,
            children=children,
            dependencies=dependencies,
            metadata={
                "complexity_analysis": complexity,
                "original_type": requirement.req_type.value,
                "children_count": len(children)
            }
        )

        logger.info(
            f"Decomposed {requirement.req_id} into {len(children)} children "
            f"with {len(dependencies)} dependencies"
        )

        return result

    def _decompose_by_function(self, req: Requirement) -> List[Requirement]:
        """Decompose by functional areas."""
        children = []
        child_type = self._get_child_type(req.req_type)

        # Extract functional areas from description and acceptance criteria
        functional_areas = self._extract_functional_areas(req)

        for i, area in enumerate(functional_areas, 1):
            child = Requirement(
                req_id=f"{req.req_id}-{i}",
                title=f"{area['title']}",
                description=area['description'],
                req_type=child_type,
                acceptance_criteria=area.get('criteria', []),
                labels=req.labels + ['auto-decomposed'],
                priority=req.priority,
                parent_id=req.req_id
            )
            children.append(child)

        return children

    def _decompose_by_component(self, req: Requirement) -> List[Requirement]:
        """Decompose by system component."""
        children = []
        child_type = self._get_child_type(req.req_type)

        # Identify components from description
        components = self._identify_components(req.description)

        for i, component in enumerate(components, 1):
            child = Requirement(
                req_id=f"{req.req_id}-C{i}",
                title=f"[{component}] {req.title}",
                description=f"Implement {req.title} for {component} component",
                req_type=child_type,
                labels=req.labels + [component.lower(), 'auto-decomposed'],
                priority=req.priority,
                parent_id=req.req_id
            )
            children.append(child)

        return children

    def _decompose_by_user_journey(self, req: Requirement) -> List[Requirement]:
        """Decompose by user workflow steps."""
        children = []
        child_type = self._get_child_type(req.req_type)

        # Extract user journey steps
        steps = self._extract_user_journey_steps(req)

        for i, step in enumerate(steps, 1):
            child = Requirement(
                req_id=f"{req.req_id}-S{i}",
                title=f"Step {i}: {step['action']}",
                description=step['description'],
                req_type=child_type,
                acceptance_criteria=[f"User can {step['action'].lower()}"],
                labels=req.labels + ['user-journey', 'auto-decomposed'],
                priority=req.priority,
                parent_id=req.req_id
            )
            children.append(child)

        return children

    def _decompose_by_technical(self, req: Requirement) -> List[Requirement]:
        """Decompose by technical concerns."""
        children = []
        child_type = self._get_child_type(req.req_type)

        # Standard technical decomposition
        technical_areas = [
            ("Data Model", "Define data structures and schemas"),
            ("API Layer", "Implement API endpoints"),
            ("Business Logic", "Core logic implementation"),
            ("Testing", "Write tests for the feature"),
            ("Documentation", "Document the implementation")
        ]

        for i, (area, desc) in enumerate(technical_areas, 1):
            child = Requirement(
                req_id=f"{req.req_id}-T{i}",
                title=f"[{area}] {req.title}",
                description=f"{desc} for: {req.title}",
                req_type=child_type,
                labels=req.labels + [area.lower().replace(' ', '-'), 'auto-decomposed'],
                priority=req.priority,
                parent_id=req.req_id
            )
            children.append(child)

        return children

    def _get_child_type(self, parent_type: RequirementType) -> RequirementType:
        """Get appropriate child type based on parent type."""
        type_hierarchy = {
            RequirementType.EPIC: RequirementType.STORY,
            RequirementType.STORY: RequirementType.TASK,
            RequirementType.TASK: RequirementType.SUBTASK,
            RequirementType.SUBTASK: RequirementType.SUBTASK
        }
        return type_hierarchy.get(parent_type, RequirementType.TASK)

    def _extract_functional_areas(self, req: Requirement) -> List[Dict[str, Any]]:
        """Extract functional areas from requirement."""
        areas = []

        # Parse acceptance criteria
        for i, criterion in enumerate(req.acceptance_criteria, 1):
            areas.append({
                'title': f"AC-{i}: {criterion[:50]}...",
                'description': criterion,
                'criteria': [criterion]
            })

        # If no AC, create from description
        if not areas:
            # Split description into sentences
            sentences = re.split(r'[.!?]\s+', req.description)
            for i, sentence in enumerate(sentences[:5], 1):
                if sentence.strip():
                    areas.append({
                        'title': f"Feature {i}: {sentence[:40]}",
                        'description': sentence,
                        'criteria': []
                    })

        return areas[:10]  # Limit to 10 children

    def _identify_components(self, description: str) -> List[str]:
        """Identify system components from description."""
        # Common components
        component_keywords = {
            'api': 'API',
            'database': 'Database',
            'frontend': 'Frontend',
            'backend': 'Backend',
            'auth': 'Authentication',
            'ui': 'UI',
            'service': 'Service',
            'worker': 'Worker',
            'cache': 'Cache',
            'queue': 'Queue'
        }

        found = []
        desc_lower = description.lower()

        for keyword, component in component_keywords.items():
            if keyword in desc_lower:
                found.append(component)

        return found if found else ['Core', 'Integration']

    def _extract_user_journey_steps(self, req: Requirement) -> List[Dict[str, str]]:
        """Extract user journey steps from requirement."""
        steps = []

        # Look for action verbs in description
        action_patterns = [
            r'user\s+(can|should|will|must)\s+(\w+)',
            r'(click|navigate|enter|submit|view|select)\s+',
            r'when\s+.+?\s+(then|,)',
        ]

        for pattern in action_patterns:
            matches = re.findall(pattern, req.description.lower())
            for match in matches:
                action = match[-1] if isinstance(match, tuple) else match
                steps.append({
                    'action': action.capitalize(),
                    'description': f"User {action} interaction"
                })

        if not steps:
            # Default journey steps
            steps = [
                {'action': 'View', 'description': 'View the feature interface'},
                {'action': 'Interact', 'description': 'Interact with feature elements'},
                {'action': 'Submit', 'description': 'Submit or save changes'},
                {'action': 'Confirm', 'description': 'Confirm action completion'}
            ]

        return steps[:8]

    def _map_dependencies(self, children: List[Requirement]) -> List[Dependency]:
        """
        Map dependencies between child requirements.

        Implements dependency_mapping to identify relationships.
        """
        dependencies = []

        # Sequential dependencies based on order
        for i in range(len(children) - 1):
            # Later tasks depend on earlier ones
            dep = Dependency(
                source_id=children[i + 1].req_id,
                target_id=children[i].req_id,
                dependency_type=DependencyType.DEPENDS_ON,
                description="Sequential dependency"
            )
            dependencies.append(dep)

        # Keyword-based dependencies
        keyword_deps = {
            'test': ['implementation', 'logic', 'api'],
            'documentation': ['implementation', 'api'],
            'integration': ['api', 'service']
        }

        for child in children:
            title_lower = child.title.lower()
            for keyword, deps_on in keyword_deps.items():
                if keyword in title_lower:
                    for other in children:
                        if other.req_id != child.req_id:
                            if any(d in other.title.lower() for d in deps_on):
                                dep = Dependency(
                                    source_id=child.req_id,
                                    target_id=other.req_id,
                                    dependency_type=DependencyType.DEPENDS_ON,
                                    description=f"Keyword dependency: {keyword}"
                                )
                                dependencies.append(dep)

        return dependencies

    def _analyze_complexity(
        self,
        original: Requirement,
        children: List[Requirement]
    ) -> Dict[str, Any]:
        """
        Analyze complexity of the requirement.

        Implements complexity_analysis for effort estimation.
        """
        # Base complexity from children count
        base_complexity = len(children)

        # Acceptance criteria complexity
        ac_count = len(original.acceptance_criteria)

        # Description complexity (word count)
        word_count = len(original.description.split())

        # Calculate complexity score (1-10)
        complexity_score = min(10, (base_complexity * 0.3) + (ac_count * 0.4) + (word_count * 0.01))

        # Estimate story points
        if complexity_score <= 3:
            estimated_points = 2
            complexity_level = "low"
        elif complexity_score <= 5:
            estimated_points = 5
            complexity_level = "medium"
        elif complexity_score <= 7:
            estimated_points = 8
            complexity_level = "high"
        else:
            estimated_points = 13
            complexity_level = "critical"

        return {
            "complexity_score": round(complexity_score, 2),
            "complexity_level": complexity_level,
            "estimated_points": estimated_points,
            "factors": {
                "children_count": base_complexity,
                "acceptance_criteria_count": ac_count,
                "description_word_count": word_count
            }
        }

    def record_change(
        self,
        req_id: str,
        field_changed: str,
        old_value: Any,
        new_value: Any,
        reason: str,
        changed_by: str
    ) -> ChangeRecord:
        """
        Record a change to a requirement.

        Implements change_management for tracking requirement evolution.
        """
        record = ChangeRecord(
            change_id=str(uuid.uuid4()),
            req_id=req_id,
            field_changed=field_changed,
            old_value=old_value,
            new_value=new_value,
            reason=reason,
            changed_by=changed_by
        )

        self._change_history.append(record)

        # Update the requirement if it exists
        if req_id in self._requirements:
            req = self._requirements[req_id]
            if hasattr(req, field_changed):
                setattr(req, field_changed, new_value)

        logger.info(
            f"Change recorded for {req_id}: {field_changed} changed by {changed_by}"
        )

        return record

    def get_change_history(self, req_id: str) -> List[ChangeRecord]:
        """Get change history for a requirement."""
        return [r for r in self._change_history if r.req_id == req_id]

    def get_requirement(self, req_id: str) -> Optional[Requirement]:
        """Get a requirement by ID."""
        return self._requirements.get(req_id)

    def get_children(self, parent_id: str) -> List[Requirement]:
        """Get all children of a requirement."""
        return [r for r in self._requirements.values() if r.parent_id == parent_id]

    def get_dependencies(self, req_id: str) -> List[Dependency]:
        """Get all dependencies for a requirement."""
        return [d for d in self._dependencies if d.source_id == req_id or d.target_id == req_id]

    def traceability_matrix(self) -> Dict[str, List[str]]:
        """
        Generate a traceability matrix.

        Implements traceability by showing parent-child relationships.
        """
        matrix = {}
        for req_id, req in self._requirements.items():
            if req.parent_id is None:
                # Top-level requirement
                children = self.get_children(req_id)
                matrix[req_id] = [c.req_id for c in children]
        return matrix


# Factory function
def create_requirement_decomposer() -> RequirementDecomposer:
    """Create a new RequirementDecomposer instance."""
    return RequirementDecomposer()
