"""Task Assignment Explainability - EU AI Act Article 13"""
from typing import Dict, Any, List, Optional
from datetime import datetime
from dataclasses import dataclass, asdict
import json

@dataclass
class AssignmentExplanation:
    """Explains why a specific agent was selected for a task."""
    task_id: str
    selected_agent: str
    selection_reason: str
    capability_scores: Dict[str, float]
    alternatives_considered: List[Dict[str, Any]]
    timestamp: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_human_readable(self) -> str:
        """Generate human-readable explanation."""
        lines = [
            f"Task Assignment Explanation for {self.task_id}",
            f"=" * 50,
            f"Selected Agent: {self.selected_agent}",
            f"Reason: {self.selection_reason}",
            "",
            "Capability Scores:",
        ]
        for cap, score in self.capability_scores.items():
            lines.append(f"  - {cap}: {score:.2f}")

        lines.append("")
        lines.append(f"Alternatives Considered: {len(self.alternatives_considered)}")
        for alt in self.alternatives_considered[:3]:
            lines.append(f"  - {alt.get('agent', 'Unknown')}: {alt.get('reason_not_selected', 'N/A')}")

        return "\n".join(lines)


class TaskAssignmentExplainer:
    """Generates explanations for AI task assignment decisions."""

    def __init__(self):
        self.explanations: List[AssignmentExplanation] = []

    def explain_assignment(
        self,
        task_id: str,
        selected_agent: str,
        capability_match: Dict[str, float],
        candidates: List[Dict[str, Any]],
        selection_criteria: str = "highest_capability_match"
    ) -> AssignmentExplanation:
        """
        Generate explanation for a task assignment decision.

        Args:
            task_id: The task being assigned
            selected_agent: The agent that was selected
            capability_match: Dict of capability scores for selected agent
            candidates: List of all candidate agents considered
            selection_criteria: The criteria used for selection
        """
        # Build alternatives list
        alternatives = []
        for candidate in candidates:
            if candidate.get('agent_id') != selected_agent:
                alternatives.append({
                    'agent': candidate.get('agent_id'),
                    'score': candidate.get('score', 0),
                    'reason_not_selected': self._determine_rejection_reason(
                        candidate, capability_match
                    )
                })

        explanation = AssignmentExplanation(
            task_id=task_id,
            selected_agent=selected_agent,
            selection_reason=f"Selected based on {selection_criteria} with score {max(capability_match.values()):.2f}",
            capability_scores=capability_match,
            alternatives_considered=alternatives,
            timestamp=datetime.utcnow().isoformat()
        )

        self.explanations.append(explanation)
        return explanation

    def _determine_rejection_reason(
        self,
        candidate: Dict[str, Any],
        winning_scores: Dict[str, float]
    ) -> str:
        """Determine why a candidate was not selected."""
        candidate_score = candidate.get('score', 0)
        max_winning = max(winning_scores.values()) if winning_scores else 0

        if candidate_score < max_winning * 0.5:
            return "Significantly lower capability match"
        elif candidate_score < max_winning:
            return "Lower overall score"
        elif not candidate.get('available', True):
            return "Agent not available"
        else:
            return "Tie-breaker: selected agent had priority"

    def get_explanation(self, task_id: str) -> Optional[AssignmentExplanation]:
        """Retrieve explanation for a specific task."""
        for exp in self.explanations:
            if exp.task_id == task_id:
                return exp
        return None


def get_agent_selection_reason(task_id: str, agent_id: str,
                                scores: Dict[str, float]) -> str:
    """
    Generate human-readable explanation for agent selection.

    This function provides the "why was this agent selected" explanation
    required by EU AI Act Article 13.
    """
    top_capability = max(scores.items(), key=lambda x: x[1])

    reasons = []
    reasons.append(f"Agent {agent_id} was selected for task {task_id}")
    reasons.append(f"Primary reason: Highest score in '{top_capability[0]}' ({top_capability[1]:.2f})")

    if scores.get('availability', 0) > 0.8:
        reasons.append("Agent was immediately available")

    if scores.get('historical_success', 0) > 0.7:
        reasons.append("Agent has strong track record with similar tasks")

    return "\n".join(reasons)
