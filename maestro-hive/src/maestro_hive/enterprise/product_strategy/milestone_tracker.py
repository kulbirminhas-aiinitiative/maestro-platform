"""
Milestone Tracker - Key milestone management with dependency tracking

Provides capabilities for:
- Defining and tracking key milestones with target dates
- Managing dependencies between milestones
- Health status monitoring and risk assessment
- Dependency graph visualization

Implements AC-3: Key milestones documented with target dates
Implements AC-6: Dependencies and risks documented
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Set, Tuple
from uuid import uuid4
import logging

logger = logging.getLogger(__name__)


class MilestoneStatus(Enum):
    """Status of a milestone."""
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    AT_RISK = "at_risk"
    BLOCKED = "blocked"
    COMPLETED = "completed"
    MISSED = "missed"
    DEFERRED = "deferred"


class HealthStatus(Enum):
    """Health status for tracking."""
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


class RiskLevel(Enum):
    """Risk level for milestones."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class Risk:
    """Represents a risk associated with a milestone."""
    risk_id: str
    description: str
    level: RiskLevel
    mitigation: str
    owner: Optional[str] = None
    identified_date: datetime = field(default_factory=datetime.utcnow)
    is_mitigated: bool = False

    def to_dict(self) -> Dict:
        """Convert risk to dictionary representation."""
        return {
            "risk_id": self.risk_id,
            "description": self.description,
            "level": self.level.value,
            "mitigation": self.mitigation,
            "owner": self.owner,
            "identified_date": self.identified_date.isoformat(),
            "is_mitigated": self.is_mitigated,
        }


@dataclass
class Dependency:
    """Represents a dependency between milestones."""
    dependency_id: str
    source_milestone_id: str
    target_milestone_id: str
    dependency_type: str  # "blocks", "requires", "related"
    description: str = ""
    is_resolved: bool = False
    created_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict:
        """Convert dependency to dictionary representation."""
        return {
            "dependency_id": self.dependency_id,
            "source_milestone_id": self.source_milestone_id,
            "target_milestone_id": self.target_milestone_id,
            "dependency_type": self.dependency_type,
            "description": self.description,
            "is_resolved": self.is_resolved,
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class Milestone:
    """Represents a key milestone with target date."""
    milestone_id: str
    name: str
    description: str
    target_date: datetime
    owner: str
    status: MilestoneStatus = MilestoneStatus.NOT_STARTED
    completion_percentage: float = 0.0
    actual_completion_date: Optional[datetime] = None
    dependencies: List[str] = field(default_factory=list)  # IDs of blocking milestones
    risks: List[Risk] = field(default_factory=list)
    deliverables: List[str] = field(default_factory=list)
    epic_keys: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def days_until_due(self) -> int:
        """Calculate days until target date."""
        delta = self.target_date - datetime.utcnow()
        return delta.days

    def is_overdue(self) -> bool:
        """Check if milestone is overdue."""
        return datetime.utcnow() > self.target_date and self.status != MilestoneStatus.COMPLETED

    def get_health(self) -> HealthStatus:
        """Determine health status based on progress and timeline."""
        if self.status == MilestoneStatus.COMPLETED:
            return HealthStatus.HEALTHY
        if self.status in [MilestoneStatus.BLOCKED, MilestoneStatus.MISSED]:
            return HealthStatus.CRITICAL

        days_remaining = self.days_until_due()
        if days_remaining < 0:
            return HealthStatus.CRITICAL
        if days_remaining < 7 and self.completion_percentage < 80:
            return HealthStatus.CRITICAL
        if days_remaining < 14 and self.completion_percentage < 50:
            return HealthStatus.WARNING
        return HealthStatus.HEALTHY

    def to_dict(self) -> Dict:
        """Convert milestone to dictionary representation."""
        return {
            "milestone_id": self.milestone_id,
            "name": self.name,
            "description": self.description,
            "target_date": self.target_date.isoformat(),
            "owner": self.owner,
            "status": self.status.value,
            "completion_percentage": self.completion_percentage,
            "actual_completion_date": self.actual_completion_date.isoformat() if self.actual_completion_date else None,
            "dependencies": self.dependencies,
            "risks": [r.to_dict() for r in self.risks],
            "deliverables": self.deliverables,
            "epic_keys": self.epic_keys,
            "health": self.get_health().value,
            "days_until_due": self.days_until_due(),
            "is_overdue": self.is_overdue(),
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


class DependencyGraph:
    """
    Manages dependencies between milestones.

    Provides topological sorting, cycle detection, and critical path analysis.
    """

    def __init__(self):
        """Initialize the dependency graph."""
        self._edges: Dict[str, Set[str]] = {}  # milestone_id -> set of dependencies
        self._reverse_edges: Dict[str, Set[str]] = {}  # milestone_id -> set of dependents

    def add_dependency(self, milestone_id: str, depends_on: str) -> bool:
        """
        Add a dependency relationship.

        Args:
            milestone_id: ID of the milestone that has the dependency
            depends_on: ID of the milestone it depends on

        Returns:
            True if added successfully, False if would create a cycle
        """
        # Check for self-dependency
        if milestone_id == depends_on:
            return False

        # Initialize sets if needed
        if milestone_id not in self._edges:
            self._edges[milestone_id] = set()
        if depends_on not in self._reverse_edges:
            self._reverse_edges[depends_on] = set()

        # Check if adding this would create a cycle
        if self._would_create_cycle(milestone_id, depends_on):
            return False

        self._edges[milestone_id].add(depends_on)
        self._reverse_edges[depends_on].add(milestone_id)
        return True

    def remove_dependency(self, milestone_id: str, depends_on: str) -> bool:
        """Remove a dependency relationship."""
        if milestone_id in self._edges and depends_on in self._edges[milestone_id]:
            self._edges[milestone_id].discard(depends_on)
            self._reverse_edges[depends_on].discard(milestone_id)
            return True
        return False

    def get_dependencies(self, milestone_id: str) -> Set[str]:
        """Get all milestones that a milestone depends on."""
        return self._edges.get(milestone_id, set()).copy()

    def get_dependents(self, milestone_id: str) -> Set[str]:
        """Get all milestones that depend on a milestone."""
        return self._reverse_edges.get(milestone_id, set()).copy()

    def _would_create_cycle(self, milestone_id: str, depends_on: str) -> bool:
        """Check if adding a dependency would create a cycle."""
        visited = set()
        stack = [depends_on]

        while stack:
            current = stack.pop()
            if current == milestone_id:
                return True
            if current in visited:
                continue
            visited.add(current)
            stack.extend(self._edges.get(current, set()))

        return False

    def topological_sort(self) -> List[str]:
        """
        Return milestones in topological order (dependencies first).

        Returns:
            List of milestone IDs in execution order
        """
        in_degree = {node: 0 for node in self._edges}
        for deps in self._edges.values():
            for dep in deps:
                if dep not in in_degree:
                    in_degree[dep] = 0

        for deps in self._edges.values():
            for dep in deps:
                pass  # Count handled by reverse edges

        # Calculate in-degrees
        for node in self._edges:
            in_degree[node] = len(self._edges.get(node, set()))

        # Find nodes with no dependencies
        queue = [node for node, degree in in_degree.items() if degree == 0]
        result = []

        while queue:
            node = queue.pop(0)
            result.append(node)

            for dependent in self._reverse_edges.get(node, set()):
                in_degree[dependent] -= 1
                if in_degree[dependent] == 0:
                    queue.append(dependent)

        return result

    def get_critical_path(self, milestones: Dict[str, Milestone]) -> List[str]:
        """
        Calculate the critical path through milestones.

        Args:
            milestones: Dictionary of milestone_id -> Milestone

        Returns:
            List of milestone IDs on the critical path
        """
        if not milestones:
            return []

        # Find milestones with no dependents (end nodes)
        end_nodes = set(milestones.keys())
        for deps in self._edges.values():
            end_nodes -= deps

        if not end_nodes:
            return list(milestones.keys())

        # Find longest path to each end node
        critical_path = []
        max_duration = 0

        for end_node in end_nodes:
            path, duration = self._find_longest_path(end_node, milestones)
            if duration > max_duration:
                max_duration = duration
                critical_path = path

        return critical_path

    def _find_longest_path(
        self, node: str, milestones: Dict[str, Milestone]
    ) -> Tuple[List[str], int]:
        """Find the longest path ending at a node."""
        if node not in self._edges or not self._edges[node]:
            return [node], 0

        max_path = []
        max_duration = 0

        for dep in self._edges.get(node, set()):
            if dep in milestones:
                path, duration = self._find_longest_path(dep, milestones)
                # Add duration based on days until milestone
                milestone = milestones.get(dep)
                if milestone:
                    duration += max(0, milestone.days_until_due())
                if duration > max_duration:
                    max_duration = duration
                    max_path = path

        return max_path + [node], max_duration

    def to_dict(self) -> Dict:
        """Convert graph to dictionary representation."""
        return {
            "edges": {k: list(v) for k, v in self._edges.items()},
            "reverse_edges": {k: list(v) for k, v in self._reverse_edges.items()},
        }


class MilestoneTracker:
    """
    Tracks key milestones with target dates and dependencies.

    Provides CRUD operations, health monitoring, and risk tracking.
    """

    def __init__(self):
        """Initialize the milestone tracker."""
        self._milestones: Dict[str, Milestone] = {}
        self._dependency_graph = DependencyGraph()
        self._dependencies: Dict[str, Dependency] = {}
        logger.info("MilestoneTracker initialized")

    def create_milestone(
        self,
        name: str,
        description: str,
        target_date: datetime,
        owner: str,
        deliverables: Optional[List[str]] = None,
        epic_keys: Optional[List[str]] = None,
    ) -> Milestone:
        """
        Create a new milestone.

        Args:
            name: Milestone name
            description: Detailed description
            target_date: Target completion date
            owner: Person responsible
            deliverables: List of deliverables
            epic_keys: Associated JIRA epic keys

        Returns:
            The created Milestone instance
        """
        milestone_id = f"MS-{uuid4().hex[:8].upper()}"
        milestone = Milestone(
            milestone_id=milestone_id,
            name=name,
            description=description,
            target_date=target_date,
            owner=owner,
            deliverables=deliverables or [],
            epic_keys=epic_keys or [],
        )
        self._milestones[milestone_id] = milestone
        logger.info(f"Created milestone: {milestone_id} - {name}")
        return milestone

    def get_milestone(self, milestone_id: str) -> Optional[Milestone]:
        """Get a milestone by ID."""
        return self._milestones.get(milestone_id)

    def list_milestones(self) -> List[Milestone]:
        """List all milestones."""
        return list(self._milestones.values())

    def update_milestone(
        self,
        milestone_id: str,
        status: Optional[MilestoneStatus] = None,
        completion_percentage: Optional[float] = None,
        target_date: Optional[datetime] = None,
    ) -> bool:
        """
        Update a milestone's properties.

        Args:
            milestone_id: ID of the milestone
            status: New status
            completion_percentage: New completion percentage
            target_date: New target date

        Returns:
            True if successful, False otherwise
        """
        milestone = self._milestones.get(milestone_id)
        if not milestone:
            return False

        if status is not None:
            milestone.status = status
            if status == MilestoneStatus.COMPLETED:
                milestone.actual_completion_date = datetime.utcnow()
                milestone.completion_percentage = 100.0

        if completion_percentage is not None:
            milestone.completion_percentage = min(100.0, max(0.0, completion_percentage))

        if target_date is not None:
            milestone.target_date = target_date

        milestone.updated_at = datetime.utcnow()
        logger.info(f"Updated milestone: {milestone_id}")
        return True

    def add_dependency(
        self,
        milestone_id: str,
        depends_on_id: str,
        dependency_type: str = "blocks",
        description: str = "",
    ) -> Optional[str]:
        """
        Add a dependency between milestones.

        Args:
            milestone_id: ID of the dependent milestone
            depends_on_id: ID of the milestone it depends on
            dependency_type: Type of dependency
            description: Description of the dependency

        Returns:
            Dependency ID if successful, None if would create cycle
        """
        if milestone_id not in self._milestones or depends_on_id not in self._milestones:
            logger.error("One or both milestones not found")
            return None

        if not self._dependency_graph.add_dependency(milestone_id, depends_on_id):
            logger.error("Dependency would create a cycle")
            return None

        dep_id = f"DEP-{uuid4().hex[:8].upper()}"
        dependency = Dependency(
            dependency_id=dep_id,
            source_milestone_id=milestone_id,
            target_milestone_id=depends_on_id,
            dependency_type=dependency_type,
            description=description,
        )
        self._dependencies[dep_id] = dependency

        milestone = self._milestones[milestone_id]
        milestone.dependencies.append(depends_on_id)
        milestone.updated_at = datetime.utcnow()

        logger.info(f"Added dependency: {milestone_id} -> {depends_on_id}")
        return dep_id

    def add_risk(
        self,
        milestone_id: str,
        description: str,
        level: RiskLevel,
        mitigation: str,
        owner: Optional[str] = None,
    ) -> Optional[str]:
        """
        Add a risk to a milestone.

        Args:
            milestone_id: ID of the milestone
            description: Risk description
            level: Risk level
            mitigation: Mitigation strategy
            owner: Risk owner

        Returns:
            Risk ID if successful, None otherwise
        """
        milestone = self._milestones.get(milestone_id)
        if not milestone:
            return None

        risk_id = f"RSK-{uuid4().hex[:8].upper()}"
        risk = Risk(
            risk_id=risk_id,
            description=description,
            level=level,
            mitigation=mitigation,
            owner=owner,
        )
        milestone.risks.append(risk)
        milestone.updated_at = datetime.utcnow()

        logger.info(f"Added risk {risk_id} to milestone {milestone_id}")
        return risk_id

    def get_milestones_by_status(self, status: MilestoneStatus) -> List[Milestone]:
        """Get milestones filtered by status."""
        return [m for m in self._milestones.values() if m.status == status]

    def get_upcoming_milestones(self, days: int = 30) -> List[Milestone]:
        """Get milestones due within specified days."""
        cutoff = datetime.utcnow() + timedelta(days=days)
        return [
            m for m in self._milestones.values()
            if m.target_date <= cutoff and m.status not in [
                MilestoneStatus.COMPLETED, MilestoneStatus.DEFERRED
            ]
        ]

    def get_at_risk_milestones(self) -> List[Milestone]:
        """Get milestones that are at risk or critical health."""
        return [
            m for m in self._milestones.values()
            if m.get_health() in [HealthStatus.WARNING, HealthStatus.CRITICAL]
        ]

    def get_blocked_milestones(self) -> List[Milestone]:
        """Get milestones blocked by incomplete dependencies."""
        blocked = []
        for milestone in self._milestones.values():
            for dep_id in milestone.dependencies:
                dep_milestone = self._milestones.get(dep_id)
                if dep_milestone and dep_milestone.status != MilestoneStatus.COMPLETED:
                    blocked.append(milestone)
                    break
        return blocked

    def get_critical_path(self) -> List[Milestone]:
        """Get milestones on the critical path."""
        path_ids = self._dependency_graph.get_critical_path(self._milestones)
        return [self._milestones[mid] for mid in path_ids if mid in self._milestones]

    def get_execution_order(self) -> List[Milestone]:
        """Get milestones in recommended execution order."""
        order = self._dependency_graph.topological_sort()
        return [self._milestones[mid] for mid in order if mid in self._milestones]

    def get_health_summary(self) -> Dict:
        """Get overall health summary of all milestones."""
        total = len(self._milestones)
        if total == 0:
            return {"status": "no_milestones", "counts": {}}

        counts = {
            HealthStatus.HEALTHY.value: 0,
            HealthStatus.WARNING.value: 0,
            HealthStatus.CRITICAL.value: 0,
        }

        for milestone in self._milestones.values():
            health = milestone.get_health()
            if health.value in counts:
                counts[health.value] += 1

        overall = HealthStatus.HEALTHY
        if counts[HealthStatus.CRITICAL.value] > 0:
            overall = HealthStatus.CRITICAL
        elif counts[HealthStatus.WARNING.value] > 0:
            overall = HealthStatus.WARNING

        return {
            "status": overall.value,
            "total": total,
            "counts": counts,
            "at_risk_count": counts[HealthStatus.WARNING.value] + counts[HealthStatus.CRITICAL.value],
        }

    def get_dependency_graph(self) -> DependencyGraph:
        """Get the dependency graph."""
        return self._dependency_graph

    def to_dict(self) -> Dict:
        """Convert tracker state to dictionary."""
        return {
            "milestones": {mid: m.to_dict() for mid, m in self._milestones.items()},
            "dependencies": {did: d.to_dict() for did, d in self._dependencies.items()},
            "dependency_graph": self._dependency_graph.to_dict(),
            "health_summary": self.get_health_summary(),
        }
