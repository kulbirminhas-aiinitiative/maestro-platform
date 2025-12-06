"""AI Explainability Dashboard Data Provider"""
from typing import Dict, Any, List
from datetime import datetime, timedelta
from collections import defaultdict

class ExplainabilityDashboard:
    """Provides data for AI explainability dashboard."""

    def __init__(self):
        self.decisions: List[Dict[str, Any]] = []
        self.explanations: List[Dict[str, Any]] = []

    def record_decision(self, decision_type: str, input_summary: str,
                       output_summary: str, reasoning: str, confidence: float):
        """Record an AI decision for the dashboard."""
        self.decisions.append({
            "timestamp": datetime.utcnow().isoformat(),
            "type": decision_type,
            "input": input_summary,
            "output": output_summary,
            "reasoning": reasoning,
            "confidence": confidence
        })

    def get_decision_summary(self, hours: int = 24) -> Dict[str, Any]:
        """Get summary of decisions in the last N hours."""
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        recent = [d for d in self.decisions
                  if datetime.fromisoformat(d["timestamp"]) > cutoff]

        by_type = defaultdict(int)
        total_confidence = 0

        for d in recent:
            by_type[d["type"]] += 1
            total_confidence += d["confidence"]

        return {
            "period_hours": hours,
            "total_decisions": len(recent),
            "by_type": dict(by_type),
            "average_confidence": total_confidence / len(recent) if recent else 0,
            "generated_at": datetime.utcnow().isoformat()
        }

    def get_algorithm_explanations(self) -> List[Dict[str, str]]:
        """Get explanations of scoring algorithms."""
        return [
            {
                "name": "Task Assignment",
                "description": "Matches tasks to agents based on capability scores",
                "factors": ["skill_match", "availability", "historical_performance"],
                "weight_distribution": "skill_match: 40%, availability: 30%, performance: 30%"
            },
            {
                "name": "Quality Scoring",
                "description": "Evaluates output quality using multiple dimensions",
                "factors": ["correctness", "completeness", "style_compliance"],
                "weight_distribution": "correctness: 50%, completeness: 30%, style: 20%"
            },
            {
                "name": "Priority Ranking",
                "description": "Ranks tasks by urgency and business impact",
                "factors": ["deadline_proximity", "business_value", "dependencies"],
                "weight_distribution": "deadline: 40%, value: 35%, dependencies: 25%"
            }
        ]
