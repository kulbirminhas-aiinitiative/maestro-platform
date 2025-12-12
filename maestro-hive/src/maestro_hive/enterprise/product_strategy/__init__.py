"""
Product Strategy Module - Product Roadmap & Strategy Management

This module provides comprehensive capability for defining, tracking, and managing
product evolution including roadmaps, milestones, strategic planning, and
capability maturity assessment.

Acceptance Criteria Coverage:
- AC-1: Product vision and mission statement defined
- AC-2: High-level product roadmap with quarterly phases
- AC-3: Key milestones documented with target dates
- AC-4: Strategic priorities and objectives identified
- AC-5: Capability maturity progression defined
- AC-6: Dependencies and risks documented
"""

from .roadmap_manager import (
    RoadmapManager,
    Roadmap,
    RoadmapPhase,
    Feature,
    PhaseStatus,
    ProgressReport,
)

from .milestone_tracker import (
    MilestoneTracker,
    Milestone,
    MilestoneStatus,
    HealthStatus,
    DependencyGraph,
)

from .strategy_planner import (
    StrategyPlanner,
    Strategy,
    Vision,
    Objective,
    Priority,
    StrategicAlignment,
)

from .capability_matrix import (
    CapabilityMatrix,
    Capability,
    MaturityLevel,
    ProgressionPlan,
    Assessment,
)

__all__ = [
    # Roadmap Management
    "RoadmapManager",
    "Roadmap",
    "RoadmapPhase",
    "Feature",
    "PhaseStatus",
    "ProgressReport",
    # Milestone Tracking
    "MilestoneTracker",
    "Milestone",
    "MilestoneStatus",
    "HealthStatus",
    "DependencyGraph",
    # Strategy Planning
    "StrategyPlanner",
    "Strategy",
    "Vision",
    "Objective",
    "Priority",
    "StrategicAlignment",
    # Capability Matrix
    "CapabilityMatrix",
    "Capability",
    "MaturityLevel",
    "ProgressionPlan",
    "Assessment",
]

__version__ = "1.0.0"
