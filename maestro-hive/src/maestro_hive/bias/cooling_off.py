"""
Cooling-Off Manager (MD-2157)

EU AI Act Compliance - Article 10

Manages agent selection cooling-off periods to prevent
over-assignment of high-performing agents.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from collections import defaultdict

from .models import CoolingOffPeriod

logger = logging.getLogger(__name__)


class CoolingOffManager:
    """
    Manages cooling-off periods for agent selection.

    Prevents over-selection of high-performing agents by
    enforcing mandatory rest periods after frequent assignments.
    """

    # Default configuration
    DEFAULT_CONFIG = {
        'window_hours': 1,  # Time window for counting assignments
        'assignment_threshold': 5,  # Max assignments in window
        'cooling_off_minutes': 30,  # Cooling-off duration
        'min_cooling_off_minutes': 10,
        'max_cooling_off_minutes': 120,
        'scaling_factor': 1.5  # Scale cooling-off based on over-threshold
    }

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the cooling-off manager.

        Args:
            config: Optional configuration overrides
        """
        self.config = {**self.DEFAULT_CONFIG, **(config or {})}

        # Active cooling-off periods
        self._active_periods: Dict[str, CoolingOffPeriod] = {}

        # Assignment history by agent
        self._assignment_history: Dict[str, List[datetime]] = defaultdict(list)

        logger.info("CoolingOffManager initialized")

    def record_assignment(self, agent_id: str, timestamp: Optional[datetime] = None):
        """
        Record a task assignment to an agent.

        Args:
            agent_id: ID of the assigned agent
            timestamp: Assignment timestamp (default: now)
        """
        timestamp = timestamp or datetime.now()
        self._assignment_history[agent_id].append(timestamp)

        # Cleanup old history
        self._cleanup_old_history(agent_id)

        # Check if cooling-off is needed
        self._check_cooling_off_needed(agent_id)

    def _cleanup_old_history(self, agent_id: str):
        """Remove old assignment history outside the window."""
        cutoff = datetime.now() - timedelta(hours=self.config['window_hours'] * 2)
        self._assignment_history[agent_id] = [
            ts for ts in self._assignment_history[agent_id]
            if ts > cutoff
        ]

    def _check_cooling_off_needed(self, agent_id: str):
        """Check if agent needs cooling-off and apply if needed."""
        if self.is_cooling_off(agent_id):
            return  # Already in cooling-off

        recent_count = self.get_recent_assignment_count(agent_id)
        threshold = self.config['assignment_threshold']

        if recent_count >= threshold:
            # Calculate cooling-off duration
            over_threshold = recent_count - threshold + 1
            base_minutes = self.config['cooling_off_minutes']
            scaling = self.config['scaling_factor']

            duration_minutes = min(
                self.config['max_cooling_off_minutes'],
                max(
                    self.config['min_cooling_off_minutes'],
                    base_minutes * (scaling ** over_threshold)
                )
            )

            self._apply_cooling_off(
                agent_id=agent_id,
                duration_minutes=duration_minutes,
                reason=f"Exceeded assignment threshold ({recent_count}/{threshold})",
                recent_count=recent_count
            )

    def _apply_cooling_off(
        self,
        agent_id: str,
        duration_minutes: float,
        reason: str,
        recent_count: int
    ):
        """Apply a cooling-off period to an agent."""
        period = CoolingOffPeriod(
            agent_id=agent_id,
            reason=reason,
            duration=timedelta(minutes=duration_minutes),
            recent_assignment_count=recent_count,
            threshold_exceeded=True
        )

        self._active_periods[agent_id] = period

        logger.info(f"Cooling-off applied to {agent_id}: {duration_minutes:.0f}m ({reason})")

    def is_cooling_off(self, agent_id: str) -> bool:
        """
        Check if an agent is currently in cooling-off.

        Args:
            agent_id: ID of the agent

        Returns:
            True if agent is in cooling-off
        """
        period = self._active_periods.get(agent_id)
        if period and period.is_active:
            return True

        # Clean up expired periods
        if period and not period.is_active:
            del self._active_periods[agent_id]

        return False

    def get_cooling_off_period(self, agent_id: str) -> Optional[CoolingOffPeriod]:
        """
        Get the cooling-off period for an agent.

        Args:
            agent_id: ID of the agent

        Returns:
            CoolingOffPeriod or None
        """
        period = self._active_periods.get(agent_id)
        if period and period.is_active:
            return period

        # Clean up expired
        if period:
            del self._active_periods[agent_id]

        return None

    def get_remaining_seconds(self, agent_id: str) -> float:
        """
        Get remaining cooling-off seconds for an agent.

        Args:
            agent_id: ID of the agent

        Returns:
            Remaining seconds (0 if not cooling-off)
        """
        period = self.get_cooling_off_period(agent_id)
        return period.remaining_seconds if period else 0.0

    def get_recent_assignment_count(
        self,
        agent_id: str,
        window_hours: Optional[float] = None
    ) -> int:
        """
        Get the number of recent assignments for an agent.

        Args:
            agent_id: ID of the agent
            window_hours: Time window (default from config)

        Returns:
            Number of assignments in window
        """
        window_hours = window_hours or self.config['window_hours']
        cutoff = datetime.now() - timedelta(hours=window_hours)

        return sum(
            1 for ts in self._assignment_history.get(agent_id, [])
            if ts >= cutoff
        )

    def get_all_active_periods(self) -> List[CoolingOffPeriod]:
        """
        Get all active cooling-off periods.

        Returns:
            List of active CoolingOffPeriod objects
        """
        active = []
        to_remove = []

        for agent_id, period in self._active_periods.items():
            if period.is_active:
                active.append(period)
            else:
                to_remove.append(agent_id)

        # Cleanup expired
        for agent_id in to_remove:
            del self._active_periods[agent_id]

        return active

    def get_available_agents(
        self,
        agent_ids: List[str]
    ) -> List[str]:
        """
        Filter agent list to only those not in cooling-off.

        Args:
            agent_ids: List of agent IDs to check

        Returns:
            List of available agent IDs
        """
        return [
            agent_id for agent_id in agent_ids
            if not self.is_cooling_off(agent_id)
        ]

    def force_cooling_off(
        self,
        agent_id: str,
        duration_minutes: float,
        reason: str = "manual"
    ):
        """
        Force a cooling-off period on an agent.

        Args:
            agent_id: ID of the agent
            duration_minutes: Duration in minutes
            reason: Reason for the cooling-off
        """
        self._apply_cooling_off(
            agent_id=agent_id,
            duration_minutes=duration_minutes,
            reason=reason,
            recent_count=self.get_recent_assignment_count(agent_id)
        )

    def cancel_cooling_off(self, agent_id: str):
        """
        Cancel a cooling-off period.

        Args:
            agent_id: ID of the agent
        """
        if agent_id in self._active_periods:
            del self._active_periods[agent_id]
            logger.info(f"Cancelled cooling-off for {agent_id}")

    def get_assignment_distribution(self) -> Dict[str, int]:
        """
        Get assignment distribution across agents.

        Returns:
            Dictionary of agent_id -> assignment count
        """
        window_hours = self.config['window_hours']
        cutoff = datetime.now() - timedelta(hours=window_hours)

        distribution = {}
        for agent_id, history in self._assignment_history.items():
            count = sum(1 for ts in history if ts >= cutoff)
            if count > 0:
                distribution[agent_id] = count

        return distribution

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get cooling-off statistics.

        Returns:
            Statistics dictionary
        """
        active_periods = self.get_all_active_periods()
        distribution = self.get_assignment_distribution()

        return {
            'active_cooling_off_count': len(active_periods),
            'agents_in_cooling_off': [p.agent_id for p in active_periods],
            'total_tracked_agents': len(self._assignment_history),
            'assignment_distribution': distribution,
            'total_assignments_in_window': sum(distribution.values()),
            'config': {
                'window_hours': self.config['window_hours'],
                'assignment_threshold': self.config['assignment_threshold'],
                'cooling_off_minutes': self.config['cooling_off_minutes']
            }
        }

    def reset(self, agent_id: Optional[str] = None):
        """
        Reset cooling-off state.

        Args:
            agent_id: Reset only for this agent (or all if None)
        """
        if agent_id:
            self._active_periods.pop(agent_id, None)
            self._assignment_history.pop(agent_id, None)
        else:
            self._active_periods.clear()
            self._assignment_history.clear()

        logger.info(f"Reset cooling-off state for {agent_id or 'all agents'}")


# Global instance
_cooling_off_manager: Optional[CoolingOffManager] = None


def get_cooling_off_manager() -> CoolingOffManager:
    """Get or create global cooling-off manager instance."""
    global _cooling_off_manager
    if _cooling_off_manager is None:
        _cooling_off_manager = CoolingOffManager()
    return _cooling_off_manager
