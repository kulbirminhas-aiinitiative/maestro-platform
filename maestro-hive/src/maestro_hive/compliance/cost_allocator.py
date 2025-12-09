#!/usr/bin/env python3
"""
Cost Allocator: Allocate costs to teams and projects.

Implements chargeback and showback for LLM usage costs.
"""

import json
import logging
from dataclasses import dataclass, asdict, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from .cost_tracker import CostTracker

logger = logging.getLogger(__name__)


@dataclass
class CostAllocation:
    """A cost allocation record."""
    id: str
    period: str
    entity_type: str  # team, project, user
    entity_id: str
    total_cost: float
    token_count: int
    request_count: int
    by_model: Dict[str, float]
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class CostAllocator:
    """Allocates costs to organizational entities."""

    def __init__(
        self,
        storage_dir: Optional[str] = None,
        tracker: Optional[CostTracker] = None
    ):
        self.storage_dir = Path(storage_dir) if storage_dir else \
            Path.home() / '.maestro' / 'cost_allocations'
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.tracker = tracker or CostTracker()
        self._allocation_rules: Dict[str, Dict] = {}

    def allocate_by_team(self, period: str = '30d') -> List[CostAllocation]:
        """Allocate costs to teams."""
        summary = self.tracker.get_summary(since=period)
        allocations = []

        for team_id, cost in summary.by_team.items():
            allocation = CostAllocation(
                id=f"ALLOC-TEAM-{team_id}-{datetime.utcnow().strftime('%Y%m%d')}",
                period=period,
                entity_type='team',
                entity_id=team_id,
                total_cost=cost,
                token_count=0,  # Would need more detailed tracking
                request_count=0,
                by_model={}
            )
            allocations.append(allocation)
            self._save_allocation(allocation)

        return allocations

    def allocate_by_project(self, period: str = '30d') -> List[CostAllocation]:
        """Allocate costs to projects."""
        summary = self.tracker.get_summary(since=period)
        allocations = []

        for project_id, cost in summary.by_project.items():
            allocation = CostAllocation(
                id=f"ALLOC-PROJ-{project_id}-{datetime.utcnow().strftime('%Y%m%d')}",
                period=period,
                entity_type='project',
                entity_id=project_id,
                total_cost=cost,
                token_count=0,
                request_count=0,
                by_model={}
            )
            allocations.append(allocation)
            self._save_allocation(allocation)

        return allocations

    def set_allocation_rule(
        self,
        rule_id: str,
        source_pattern: str,
        target_entity: str,
        percentage: float = 100.0
    ):
        """Set a cost allocation rule."""
        self._allocation_rules[rule_id] = {
            'source_pattern': source_pattern,
            'target_entity': target_entity,
            'percentage': percentage
        }

    def _save_allocation(self, allocation: CostAllocation):
        """Save allocation to storage."""
        file_path = self.storage_dir / f"{allocation.id}.json"
        with open(file_path, 'w') as f:
            json.dump(allocation.to_dict(), f, indent=2)


def get_cost_allocator(**kwargs) -> CostAllocator:
    """Get cost allocator instance."""
    return CostAllocator(**kwargs)
