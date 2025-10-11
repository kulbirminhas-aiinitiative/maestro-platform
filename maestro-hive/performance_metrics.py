#!/usr/bin/env python3
"""
Performance Metrics System for Dynamic Team Management

Provides advanced performance tracking, analysis, and decision-making for:
- Individual agent performance scoring
- Team-level metrics and health
- Underperformer detection
- Auto-scaling triggers
- Performance-based recommendations
"""

import sys
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass

# Add parent directories to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from persistence.state_manager import StateManager


@dataclass
class PerformanceThresholds:
    """Performance thresholds for decision making"""
    # Minimum acceptable scores
    min_performance_score: int = 60
    min_task_completion_rate: int = 50
    min_collaboration_score: int = 40

    # Maximum acceptable values
    max_avg_task_duration_multiplier: float = 2.0  # 2x team average
    max_task_failure_rate: int = 30  # 30% failure rate

    # Team health thresholds
    team_health_good: int = 75
    team_health_warning: int = 50

    # Auto-scaling triggers
    ready_tasks_threshold: int = 10
    avg_wait_time_hours: float = 4.0
    capacity_utilization_high: int = 90  # %
    capacity_utilization_low: int = 30   # %


@dataclass
class AgentPerformanceScore:
    """Detailed performance score breakdown for an agent"""
    agent_id: str
    persona_id: str
    overall_score: int  # 0-100

    # Component scores
    task_completion_score: int
    speed_score: int
    quality_score: int
    collaboration_score: int

    # Raw metrics
    total_tasks: int
    completed_tasks: int
    failed_tasks: int
    avg_task_duration_hours: Optional[float]

    # Status
    is_underperformer: bool
    recommendation: str  # "keep", "improve", "standby", "replace"
    issues: List[str]


@dataclass
class TeamHealthMetrics:
    """Overall team health metrics"""
    team_id: str
    overall_health_score: int  # 0-100

    # Team composition
    total_members: int
    active_members: int
    standby_members: int
    retired_members: int

    # Workload metrics
    total_ready_tasks: int
    total_running_tasks: int
    avg_wait_time_hours: float
    capacity_utilization: int  # 0-100%

    # Performance metrics
    avg_team_performance: int
    underperformers_count: int
    top_performers_count: int

    # Recommendations
    scaling_recommendation: str  # "scale_up", "scale_down", "maintain"
    recommended_actions: List[str]
    issues: List[str]


class PerformanceMetricsAnalyzer:
    """
    Analyzes performance metrics and provides recommendations

    Features:
    - Individual agent scoring (0-100)
    - Team health analysis
    - Underperformer detection
    - Auto-scaling recommendations
    - Performance-based action recommendations
    """

    def __init__(
        self,
        state_manager: StateManager,
        thresholds: Optional[PerformanceThresholds] = None
    ):
        self.state = state_manager
        self.thresholds = thresholds or PerformanceThresholds()

    async def analyze_agent_performance(
        self,
        team_id: str,
        agent_id: str
    ) -> AgentPerformanceScore:
        """
        Comprehensive agent performance analysis

        Scoring criteria:
        - Task completion rate: 40%
        - Speed (task duration): 30%
        - Quality (failure rate): 20%
        - Collaboration: 10%
        """
        # Get performance data
        perf = await self.state.get_member_performance(team_id, agent_id)

        if not perf:
            raise ValueError(f"No performance data for agent {agent_id}")

        # Get team average for comparison
        team_avg = await self._get_team_averages(team_id)

        # Calculate component scores
        completion_score = self._calculate_completion_score(
            perf['task_completion_rate']
        )

        speed_score = self._calculate_speed_score(
            perf['average_task_duration_hours'],
            team_avg['avg_duration']
        )

        quality_score = self._calculate_quality_score(
            perf['completed_tasks'],
            perf['failed_tasks']
        )

        collaboration_score = perf['collaboration_score']

        # Overall score (weighted average)
        overall_score = int(
            completion_score * 0.4 +
            speed_score * 0.3 +
            quality_score * 0.2 +
            collaboration_score * 0.1
        )

        # Determine if underperformer
        is_underperformer, issues = self._check_underperformer(
            overall_score,
            completion_score,
            quality_score,
            collaboration_score,
            perf['average_task_duration_hours'],
            team_avg['avg_duration']
        )

        # Recommendation
        recommendation = self._get_recommendation(
            overall_score,
            is_underperformer,
            issues
        )

        return AgentPerformanceScore(
            agent_id=agent_id,
            persona_id=perf['persona_id'],
            overall_score=overall_score,
            task_completion_score=completion_score,
            speed_score=speed_score,
            quality_score=quality_score,
            collaboration_score=collaboration_score,
            total_tasks=perf['total_tasks'],
            completed_tasks=perf['completed_tasks'],
            failed_tasks=perf['failed_tasks'],
            avg_task_duration_hours=perf['average_task_duration_hours'],
            is_underperformer=is_underperformer,
            recommendation=recommendation,
            issues=issues
        )

    async def analyze_team_health(
        self,
        team_id: str
    ) -> TeamHealthMetrics:
        """
        Comprehensive team health analysis

        Analyzes:
        - Team composition
        - Workload distribution
        - Performance levels
        - Scaling needs
        """
        from persistence.models import MembershipState

        # Get team members by state
        all_members = await self.state.get_team_members(team_id)
        active_members = await self.state.get_team_members(team_id, state=MembershipState.ACTIVE)
        standby_members = await self.state.get_team_members(team_id, state=MembershipState.ON_STANDBY)
        retired_members = await self.state.get_team_members(team_id, state=MembershipState.RETIRED)

        # Get workload metrics
        ready_tasks = await self.state.get_ready_tasks(team_id, limit=1000)

        # Get workspace state
        workspace = await self.state.get_workspace_state(team_id)
        running_tasks = workspace['tasks'].get('running', 0)

        # Calculate capacity utilization
        active_count = len(active_members)
        capacity_utilization = min(100, int((running_tasks / active_count) * 100)) if active_count > 0 else 0

        # Analyze individual performances
        performances = []
        for member in active_members:
            try:
                perf = await self.analyze_agent_performance(team_id, member['agent_id'])
                performances.append(perf)
            except:
                continue

        avg_team_perf = int(sum(p.overall_score for p in performances) / len(performances)) if performances else 0
        underperformers = [p for p in performances if p.is_underperformer]
        top_performers = [p for p in performances if p.overall_score >= 85]

        # Overall health score
        health_score = self._calculate_team_health_score(
            avg_team_perf,
            len(underperformers),
            len(active_members),
            capacity_utilization,
            len(ready_tasks)
        )

        # Scaling recommendation
        scaling_rec, actions, issues = self._get_scaling_recommendation(
            len(ready_tasks),
            running_tasks,
            active_count,
            capacity_utilization,
            len(underperformers)
        )

        return TeamHealthMetrics(
            team_id=team_id,
            overall_health_score=health_score,
            total_members=len(all_members),
            active_members=len(active_members),
            standby_members=len(standby_members),
            retired_members=len(retired_members),
            total_ready_tasks=len(ready_tasks),
            total_running_tasks=running_tasks,
            avg_wait_time_hours=0.0,  # Would need task timestamps
            capacity_utilization=capacity_utilization,
            avg_team_performance=avg_team_perf,
            underperformers_count=len(underperformers),
            top_performers_count=len(top_performers),
            scaling_recommendation=scaling_rec,
            recommended_actions=actions,
            issues=issues
        )

    async def get_underperformers(
        self,
        team_id: str
    ) -> List[AgentPerformanceScore]:
        """Get list of underperforming agents"""
        from persistence.models import MembershipState

        active_members = await self.state.get_team_members(team_id, state=MembershipState.ACTIVE)

        underperformers = []
        for member in active_members:
            try:
                perf = await self.analyze_agent_performance(team_id, member['agent_id'])
                if perf.is_underperformer:
                    underperformers.append(perf)
            except:
                continue

        return sorted(underperformers, key=lambda p: p.overall_score)

    async def get_replacement_candidates(
        self,
        team_id: str
    ) -> List[Tuple[str, str]]:
        """
        Get list of agents recommended for replacement

        Returns:
            List of (agent_id, reason) tuples
        """
        underperformers = await self.get_underperformers(team_id)

        candidates = []
        for perf in underperformers:
            if perf.recommendation == "replace":
                reason = f"Low performance (score: {perf.overall_score}/100). Issues: {', '.join(perf.issues)}"
                candidates.append((perf.agent_id, reason))

        return candidates

    # =========================================================================
    # Private Helper Methods
    # =========================================================================

    def _calculate_completion_score(self, completion_rate: int) -> int:
        """Score based on task completion rate (0-100)"""
        return min(100, completion_rate)

    def _calculate_speed_score(
        self,
        agent_duration: Optional[float],
        team_avg_duration: Optional[float]
    ) -> int:
        """Score based on task completion speed relative to team average"""
        if agent_duration is None or team_avg_duration is None or team_avg_duration == 0:
            return 70  # Neutral score if no data

        # Lower duration = higher score
        ratio = agent_duration / team_avg_duration

        if ratio <= 0.7:  # 30% faster than average
            return 100
        elif ratio <= 1.0:  # At or better than average
            return int(100 - (ratio - 0.7) * 100)
        elif ratio <= 1.5:  # Up to 50% slower
            return int(70 - (ratio - 1.0) * 100)
        else:  # More than 50% slower
            return max(0, int(40 - (ratio - 1.5) * 50))

    def _calculate_quality_score(
        self,
        completed_tasks: int,
        failed_tasks: int
    ) -> int:
        """Score based on task failure rate"""
        total = completed_tasks + failed_tasks
        if total == 0:
            return 100  # No failures yet

        failure_rate = (failed_tasks / total) * 100

        if failure_rate <= 5:
            return 100
        elif failure_rate <= 10:
            return 90
        elif failure_rate <= 20:
            return 70
        elif failure_rate <= 30:
            return 50
        else:
            return max(0, int(50 - (failure_rate - 30) * 2))

    def _check_underperformer(
        self,
        overall_score: int,
        completion_score: int,
        quality_score: int,
        collaboration_score: int,
        agent_duration: Optional[float],
        team_avg_duration: Optional[float]
    ) -> Tuple[bool, List[str]]:
        """Check if agent is underperforming and identify issues"""
        issues = []

        if overall_score < self.thresholds.min_performance_score:
            issues.append(f"Overall score too low ({overall_score}/100)")

        if completion_score < self.thresholds.min_task_completion_rate:
            issues.append(f"Low task completion rate ({completion_score}%)")

        if quality_score < 50:
            issues.append(f"High task failure rate (quality score: {quality_score}/100)")

        if collaboration_score < self.thresholds.min_collaboration_score:
            issues.append(f"Low collaboration ({collaboration_score}/100)")

        if agent_duration and team_avg_duration:
            if agent_duration > team_avg_duration * self.thresholds.max_avg_task_duration_multiplier:
                issues.append(f"Tasks taking too long ({agent_duration:.1f}h vs team avg {team_avg_duration:.1f}h)")

        is_underperformer = len(issues) > 0

        return is_underperformer, issues

    def _get_recommendation(
        self,
        overall_score: int,
        is_underperformer: bool,
        issues: List[str]
    ) -> str:
        """Get recommendation based on performance"""
        if not is_underperformer:
            if overall_score >= 85:
                return "keep"  # Top performer
            else:
                return "keep"  # Acceptable performance

        # Underperformer
        if overall_score >= 50:
            return "improve"  # Give chance to improve
        elif overall_score >= 30:
            return "standby"  # Move to standby
        else:
            return "replace"  # Too low, replace

    async def _get_team_averages(self, team_id: str) -> Dict[str, Any]:
        """Calculate team-wide averages for comparison"""
        from persistence.models import MembershipState

        active_members = await self.state.get_team_members(team_id, state=MembershipState.ACTIVE)

        durations = []
        for member in active_members:
            perf = await self.state.get_member_performance(team_id, member['agent_id'])
            if perf and perf['average_task_duration_hours']:
                durations.append(perf['average_task_duration_hours'])

        avg_duration = sum(durations) / len(durations) if durations else None

        return {
            "avg_duration": avg_duration
        }

    def _calculate_team_health_score(
        self,
        avg_team_perf: int,
        underperformers_count: int,
        active_count: int,
        capacity_utilization: int,
        ready_tasks_count: int
    ) -> int:
        """Calculate overall team health score (0-100)"""
        # Base score from average performance
        health = avg_team_perf

        # Penalty for underperformers
        if active_count > 0:
            underperformer_ratio = underperformers_count / active_count
            health -= int(underperformer_ratio * 30)

        # Penalty for poor capacity utilization
        if capacity_utilization > 95:
            health -= 20  # Overloaded
        elif capacity_utilization < 20:
            health -= 10  # Underutilized

        # Penalty for task backlog
        if ready_tasks_count > 20:
            health -= 15
        elif ready_tasks_count > 10:
            health -= 5

        return max(0, min(100, health))

    def _get_scaling_recommendation(
        self,
        ready_tasks: int,
        running_tasks: int,
        active_members: int,
        capacity_utilization: int,
        underperformers: int
    ) -> Tuple[str, List[str], List[str]]:
        """Get scaling recommendation and actions"""
        actions = []
        issues = []

        # Check for scale up triggers
        should_scale_up = False
        if ready_tasks > self.thresholds.ready_tasks_threshold:
            should_scale_up = True
            issues.append(f"High task backlog ({ready_tasks} ready tasks)")

        if capacity_utilization > self.thresholds.capacity_utilization_high:
            should_scale_up = True
            issues.append(f"Team overloaded ({capacity_utilization}% capacity)")

        # Check for scale down triggers
        should_scale_down = False
        if capacity_utilization < self.thresholds.capacity_utilization_low and ready_tasks < 3:
            should_scale_down = True
            issues.append(f"Team underutilized ({capacity_utilization}% capacity)")

        # Determine recommendation
        if should_scale_up:
            recommendation = "scale_up"
            actions.append(f"Add {max(2, ready_tasks // 5)} more team members")
            if underperformers > 0:
                actions.append(f"Consider replacing {underperformers} underperformers first")
        elif should_scale_down:
            recommendation = "scale_down"
            actions.append(f"Move {max(1, active_members // 3)} members to standby")
            actions.append("Retire members who are no longer needed")
        else:
            recommendation = "maintain"
            if underperformers > 0:
                actions.append(f"Address {underperformers} underperformers")
            else:
                actions.append("Team is performing well, maintain current composition")

        return recommendation, actions, issues


# Helper function for quick performance check
async def quick_performance_check(
    state_manager: StateManager,
    team_id: str
) -> Dict[str, Any]:
    """Quick performance check for a team"""
    analyzer = PerformanceMetricsAnalyzer(state_manager)

    health = await analyzer.analyze_team_health(team_id)
    underperformers = await analyzer.get_underperformers(team_id)

    return {
        "health_score": health.overall_health_score,
        "health_status": (
            "good" if health.overall_health_score >= 75
            else "warning" if health.overall_health_score >= 50
            else "critical"
        ),
        "active_members": health.active_members,
        "underperformers": len(underperformers),
        "scaling_recommendation": health.scaling_recommendation,
        "recommended_actions": health.recommended_actions,
        "issues": health.issues
    }


if __name__ == "__main__":
    print("Performance Metrics System")
    print("=" * 80)
    print("\nThis module provides:")
    print("- Individual agent performance scoring")
    print("- Team health analysis")
    print("- Underperformer detection")
    print("- Auto-scaling recommendations")
    print("\nUse via DynamicTeamManager for full functionality.")
