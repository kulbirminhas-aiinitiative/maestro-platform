"""
Strategy Planner - Product vision and strategic planning

Provides capabilities for:
- Defining product vision and mission statements
- Setting strategic priorities and objectives
- Aligning features with strategic goals
- Tracking strategic alignment across the roadmap

Implements AC-1: Product vision and mission statement defined
Implements AC-4: Strategic priorities and objectives identified
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional
from uuid import uuid4
import logging

logger = logging.getLogger(__name__)


class Priority(Enum):
    """Priority level for strategic items."""
    P0_CRITICAL = "p0_critical"
    P1_HIGH = "p1_high"
    P2_MEDIUM = "p2_medium"
    P3_LOW = "p3_low"


class ObjectiveStatus(Enum):
    """Status of a strategic objective."""
    DRAFT = "draft"
    APPROVED = "approved"
    IN_PROGRESS = "in_progress"
    ACHIEVED = "achieved"
    DEFERRED = "deferred"
    CANCELLED = "cancelled"


class AlignmentScore(Enum):
    """Alignment score levels."""
    STRONG = "strong"
    MODERATE = "moderate"
    WEAK = "weak"
    MISALIGNED = "misaligned"


@dataclass
class Vision:
    """Represents the product vision."""
    vision_id: str
    statement: str
    description: str
    target_audience: str
    value_proposition: str
    time_horizon: str  # e.g., "3 years", "5 years"
    created_by: str
    approved_by: Optional[str] = None
    approved_date: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict:
        """Convert vision to dictionary representation."""
        return {
            "vision_id": self.vision_id,
            "statement": self.statement,
            "description": self.description,
            "target_audience": self.target_audience,
            "value_proposition": self.value_proposition,
            "time_horizon": self.time_horizon,
            "created_by": self.created_by,
            "approved_by": self.approved_by,
            "approved_date": self.approved_date.isoformat() if self.approved_date else None,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


@dataclass
class Mission:
    """Represents the product mission statement."""
    mission_id: str
    statement: str
    purpose: str
    core_values: List[str]
    key_stakeholders: List[str]
    created_by: str
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict:
        """Convert mission to dictionary representation."""
        return {
            "mission_id": self.mission_id,
            "statement": self.statement,
            "purpose": self.purpose,
            "core_values": self.core_values,
            "key_stakeholders": self.key_stakeholders,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


@dataclass
class KeyResult:
    """Represents a key result for an objective (OKR pattern)."""
    key_result_id: str
    description: str
    metric: str
    target_value: float
    current_value: float = 0.0
    unit: str = ""
    created_at: datetime = field(default_factory=datetime.utcnow)

    def get_progress(self) -> float:
        """Calculate progress percentage."""
        if self.target_value == 0:
            return 0.0
        return min(100.0, (self.current_value / self.target_value) * 100)

    def to_dict(self) -> Dict:
        """Convert key result to dictionary representation."""
        return {
            "key_result_id": self.key_result_id,
            "description": self.description,
            "metric": self.metric,
            "target_value": self.target_value,
            "current_value": self.current_value,
            "unit": self.unit,
            "progress": self.get_progress(),
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class Objective:
    """Represents a strategic objective."""
    objective_id: str
    name: str
    description: str
    priority: Priority
    owner: str
    status: ObjectiveStatus = ObjectiveStatus.DRAFT
    key_results: List[KeyResult] = field(default_factory=list)
    aligned_features: List[str] = field(default_factory=list)  # Feature IDs
    aligned_milestones: List[str] = field(default_factory=list)  # Milestone IDs
    target_quarter: Optional[str] = None  # e.g., "Q1 2025"
    success_criteria: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def calculate_progress(self) -> float:
        """Calculate overall objective progress from key results."""
        if not self.key_results:
            return 0.0
        total_progress = sum(kr.get_progress() for kr in self.key_results)
        return total_progress / len(self.key_results)

    def to_dict(self) -> Dict:
        """Convert objective to dictionary representation."""
        return {
            "objective_id": self.objective_id,
            "name": self.name,
            "description": self.description,
            "priority": self.priority.value,
            "owner": self.owner,
            "status": self.status.value,
            "key_results": [kr.to_dict() for kr in self.key_results],
            "aligned_features": self.aligned_features,
            "aligned_milestones": self.aligned_milestones,
            "target_quarter": self.target_quarter,
            "success_criteria": self.success_criteria,
            "progress": self.calculate_progress(),
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


@dataclass
class StrategicAlignment:
    """Represents alignment analysis between items and strategy."""
    alignment_id: str
    item_type: str  # "feature", "milestone", "initiative"
    item_id: str
    item_name: str
    objective_id: str
    objective_name: str
    score: AlignmentScore
    rationale: str
    recommendations: List[str] = field(default_factory=list)
    analyzed_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict:
        """Convert alignment to dictionary representation."""
        return {
            "alignment_id": self.alignment_id,
            "item_type": self.item_type,
            "item_id": self.item_id,
            "item_name": self.item_name,
            "objective_id": self.objective_id,
            "objective_name": self.objective_name,
            "score": self.score.value,
            "rationale": self.rationale,
            "recommendations": self.recommendations,
            "analyzed_at": self.analyzed_at.isoformat(),
        }


@dataclass
class Strategy:
    """Represents the overall product strategy."""
    strategy_id: str
    name: str
    vision: Optional[Vision] = None
    mission: Optional[Mission] = None
    objectives: List[Objective] = field(default_factory=list)
    strategic_themes: List[str] = field(default_factory=list)
    planning_horizon: str = "1 year"
    review_frequency: str = "quarterly"
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def get_objectives_by_priority(self, priority: Priority) -> List[Objective]:
        """Get objectives filtered by priority."""
        return [o for o in self.objectives if o.priority == priority]

    def get_active_objectives(self) -> List[Objective]:
        """Get objectives that are in progress."""
        return [o for o in self.objectives if o.status == ObjectiveStatus.IN_PROGRESS]

    def calculate_overall_progress(self) -> float:
        """Calculate overall strategy progress."""
        active = self.get_active_objectives()
        if not active:
            return 0.0
        return sum(o.calculate_progress() for o in active) / len(active)

    def to_dict(self) -> Dict:
        """Convert strategy to dictionary representation."""
        return {
            "strategy_id": self.strategy_id,
            "name": self.name,
            "vision": self.vision.to_dict() if self.vision else None,
            "mission": self.mission.to_dict() if self.mission else None,
            "objectives": [o.to_dict() for o in self.objectives],
            "strategic_themes": self.strategic_themes,
            "planning_horizon": self.planning_horizon,
            "review_frequency": self.review_frequency,
            "overall_progress": self.calculate_overall_progress(),
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


class StrategyPlanner:
    """
    Manages product strategy, vision, mission, and objectives.

    Provides CRUD operations for strategic elements and alignment analysis.
    """

    def __init__(self):
        """Initialize the strategy planner."""
        self._strategies: Dict[str, Strategy] = {}
        self._alignments: Dict[str, StrategicAlignment] = {}
        logger.info("StrategyPlanner initialized")

    def create_strategy(
        self,
        name: str,
        strategic_themes: Optional[List[str]] = None,
        planning_horizon: str = "1 year",
        review_frequency: str = "quarterly",
    ) -> Strategy:
        """
        Create a new strategy.

        Args:
            name: Strategy name
            strategic_themes: List of strategic themes
            planning_horizon: Planning time horizon
            review_frequency: How often to review

        Returns:
            The created Strategy instance
        """
        strategy_id = f"STR-{uuid4().hex[:8].upper()}"
        strategy = Strategy(
            strategy_id=strategy_id,
            name=name,
            strategic_themes=strategic_themes or [],
            planning_horizon=planning_horizon,
            review_frequency=review_frequency,
        )
        self._strategies[strategy_id] = strategy
        logger.info(f"Created strategy: {strategy_id} - {name}")
        return strategy

    def get_strategy(self, strategy_id: str) -> Optional[Strategy]:
        """Get a strategy by ID."""
        return self._strategies.get(strategy_id)

    def list_strategies(self) -> List[Strategy]:
        """List all strategies."""
        return list(self._strategies.values())

    def set_vision(
        self,
        strategy_id: str,
        statement: str,
        description: str,
        target_audience: str,
        value_proposition: str,
        time_horizon: str,
        created_by: str,
    ) -> Optional[Vision]:
        """
        Set the vision for a strategy.

        Args:
            strategy_id: ID of the strategy
            statement: Vision statement
            description: Detailed description
            target_audience: Target audience
            value_proposition: Value proposition
            time_horizon: Time horizon for the vision
            created_by: Creator

        Returns:
            The created Vision instance or None
        """
        strategy = self._strategies.get(strategy_id)
        if not strategy:
            return None

        vision_id = f"VIS-{uuid4().hex[:8].upper()}"
        vision = Vision(
            vision_id=vision_id,
            statement=statement,
            description=description,
            target_audience=target_audience,
            value_proposition=value_proposition,
            time_horizon=time_horizon,
            created_by=created_by,
        )
        strategy.vision = vision
        strategy.updated_at = datetime.utcnow()
        logger.info(f"Set vision for strategy {strategy_id}")
        return vision

    def set_mission(
        self,
        strategy_id: str,
        statement: str,
        purpose: str,
        core_values: List[str],
        key_stakeholders: List[str],
        created_by: str,
    ) -> Optional[Mission]:
        """
        Set the mission for a strategy.

        Args:
            strategy_id: ID of the strategy
            statement: Mission statement
            purpose: Purpose description
            core_values: List of core values
            key_stakeholders: List of key stakeholders
            created_by: Creator

        Returns:
            The created Mission instance or None
        """
        strategy = self._strategies.get(strategy_id)
        if not strategy:
            return None

        mission_id = f"MIS-{uuid4().hex[:8].upper()}"
        mission = Mission(
            mission_id=mission_id,
            statement=statement,
            purpose=purpose,
            core_values=core_values,
            key_stakeholders=key_stakeholders,
            created_by=created_by,
        )
        strategy.mission = mission
        strategy.updated_at = datetime.utcnow()
        logger.info(f"Set mission for strategy {strategy_id}")
        return mission

    def add_objective(
        self,
        strategy_id: str,
        name: str,
        description: str,
        priority: Priority,
        owner: str,
        target_quarter: Optional[str] = None,
        success_criteria: Optional[List[str]] = None,
    ) -> Optional[str]:
        """
        Add an objective to a strategy.

        Args:
            strategy_id: ID of the strategy
            name: Objective name
            description: Detailed description
            priority: Priority level
            owner: Objective owner
            target_quarter: Target quarter
            success_criteria: List of success criteria

        Returns:
            Objective ID if successful, None otherwise
        """
        strategy = self._strategies.get(strategy_id)
        if not strategy:
            return None

        objective_id = f"OBJ-{uuid4().hex[:8].upper()}"
        objective = Objective(
            objective_id=objective_id,
            name=name,
            description=description,
            priority=priority,
            owner=owner,
            target_quarter=target_quarter,
            success_criteria=success_criteria or [],
        )
        strategy.objectives.append(objective)
        strategy.updated_at = datetime.utcnow()
        logger.info(f"Added objective {objective_id} to strategy {strategy_id}")
        return objective_id

    def add_key_result(
        self,
        strategy_id: str,
        objective_id: str,
        description: str,
        metric: str,
        target_value: float,
        unit: str = "",
    ) -> Optional[str]:
        """
        Add a key result to an objective.

        Args:
            strategy_id: ID of the strategy
            objective_id: ID of the objective
            description: Key result description
            metric: Metric name
            target_value: Target value
            unit: Unit of measurement

        Returns:
            Key result ID if successful, None otherwise
        """
        strategy = self._strategies.get(strategy_id)
        if not strategy:
            return None

        objective = next(
            (o for o in strategy.objectives if o.objective_id == objective_id), None
        )
        if not objective:
            return None

        kr_id = f"KR-{uuid4().hex[:8].upper()}"
        key_result = KeyResult(
            key_result_id=kr_id,
            description=description,
            metric=metric,
            target_value=target_value,
            unit=unit,
        )
        objective.key_results.append(key_result)
        objective.updated_at = datetime.utcnow()
        strategy.updated_at = datetime.utcnow()
        logger.info(f"Added key result {kr_id} to objective {objective_id}")
        return kr_id

    def update_key_result_progress(
        self,
        strategy_id: str,
        objective_id: str,
        key_result_id: str,
        current_value: float,
    ) -> bool:
        """
        Update progress on a key result.

        Args:
            strategy_id: ID of the strategy
            objective_id: ID of the objective
            key_result_id: ID of the key result
            current_value: Current value

        Returns:
            True if successful, False otherwise
        """
        strategy = self._strategies.get(strategy_id)
        if not strategy:
            return False

        objective = next(
            (o for o in strategy.objectives if o.objective_id == objective_id), None
        )
        if not objective:
            return False

        key_result = next(
            (kr for kr in objective.key_results if kr.key_result_id == key_result_id),
            None,
        )
        if not key_result:
            return False

        key_result.current_value = current_value
        objective.updated_at = datetime.utcnow()
        strategy.updated_at = datetime.utcnow()
        logger.info(f"Updated key result {key_result_id} progress to {current_value}")
        return True

    def update_objective_status(
        self,
        strategy_id: str,
        objective_id: str,
        status: ObjectiveStatus,
    ) -> bool:
        """
        Update the status of an objective.

        Args:
            strategy_id: ID of the strategy
            objective_id: ID of the objective
            status: New status

        Returns:
            True if successful, False otherwise
        """
        strategy = self._strategies.get(strategy_id)
        if not strategy:
            return False

        objective = next(
            (o for o in strategy.objectives if o.objective_id == objective_id), None
        )
        if not objective:
            return False

        objective.status = status
        objective.updated_at = datetime.utcnow()
        strategy.updated_at = datetime.utcnow()
        logger.info(f"Updated objective {objective_id} status to {status.value}")
        return True

    def align_feature(
        self,
        strategy_id: str,
        objective_id: str,
        feature_id: str,
    ) -> bool:
        """
        Align a feature with an objective.

        Args:
            strategy_id: ID of the strategy
            objective_id: ID of the objective
            feature_id: ID of the feature

        Returns:
            True if successful, False otherwise
        """
        strategy = self._strategies.get(strategy_id)
        if not strategy:
            return False

        objective = next(
            (o for o in strategy.objectives if o.objective_id == objective_id), None
        )
        if not objective:
            return False

        if feature_id not in objective.aligned_features:
            objective.aligned_features.append(feature_id)
            objective.updated_at = datetime.utcnow()
            strategy.updated_at = datetime.utcnow()
            logger.info(f"Aligned feature {feature_id} with objective {objective_id}")
        return True

    def analyze_alignment(
        self,
        strategy_id: str,
        item_type: str,
        item_id: str,
        item_name: str,
        objective_id: str,
        score: AlignmentScore,
        rationale: str,
        recommendations: Optional[List[str]] = None,
    ) -> Optional[StrategicAlignment]:
        """
        Record alignment analysis for an item.

        Args:
            strategy_id: ID of the strategy
            item_type: Type of item
            item_id: ID of the item
            item_name: Name of the item
            objective_id: ID of the objective
            score: Alignment score
            rationale: Rationale for the score
            recommendations: List of recommendations

        Returns:
            The created StrategicAlignment or None
        """
        strategy = self._strategies.get(strategy_id)
        if not strategy:
            return None

        objective = next(
            (o for o in strategy.objectives if o.objective_id == objective_id), None
        )
        if not objective:
            return None

        alignment_id = f"ALN-{uuid4().hex[:8].upper()}"
        alignment = StrategicAlignment(
            alignment_id=alignment_id,
            item_type=item_type,
            item_id=item_id,
            item_name=item_name,
            objective_id=objective_id,
            objective_name=objective.name,
            score=score,
            rationale=rationale,
            recommendations=recommendations or [],
        )
        self._alignments[alignment_id] = alignment
        logger.info(f"Created alignment analysis {alignment_id}")
        return alignment

    def get_alignments_by_objective(self, objective_id: str) -> List[StrategicAlignment]:
        """Get all alignments for an objective."""
        return [a for a in self._alignments.values() if a.objective_id == objective_id]

    def get_strategic_summary(self, strategy_id: str) -> Optional[Dict]:
        """
        Get a summary of the strategy.

        Args:
            strategy_id: ID of the strategy

        Returns:
            Summary dictionary or None
        """
        strategy = self._strategies.get(strategy_id)
        if not strategy:
            return None

        objectives_by_status = {}
        for status in ObjectiveStatus:
            count = len([o for o in strategy.objectives if o.status == status])
            if count > 0:
                objectives_by_status[status.value] = count

        objectives_by_priority = {}
        for priority in Priority:
            count = len([o for o in strategy.objectives if o.priority == priority])
            if count > 0:
                objectives_by_priority[priority.value] = count

        return {
            "strategy_id": strategy_id,
            "name": strategy.name,
            "has_vision": strategy.vision is not None,
            "has_mission": strategy.mission is not None,
            "total_objectives": len(strategy.objectives),
            "objectives_by_status": objectives_by_status,
            "objectives_by_priority": objectives_by_priority,
            "overall_progress": strategy.calculate_overall_progress(),
            "strategic_themes": strategy.strategic_themes,
            "planning_horizon": strategy.planning_horizon,
        }
