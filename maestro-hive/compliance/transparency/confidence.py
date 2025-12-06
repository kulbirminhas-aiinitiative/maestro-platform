"""AI Confidence Indicators - Show certainty levels"""
from typing import Dict, Any, Tuple
from enum import Enum

class ConfidenceLevel(Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    UNCERTAIN = "uncertain"

def calculate_confidence(score: float) -> Tuple[ConfidenceLevel, str]:
    """
    Calculate confidence level from a score.

    Args:
        score: Float between 0 and 1

    Returns:
        Tuple of (ConfidenceLevel, color_code)
    """
    if score >= 0.8:
        return ConfidenceLevel.HIGH, "#22c55e"  # green
    elif score >= 0.6:
        return ConfidenceLevel.MEDIUM, "#eab308"  # yellow
    elif score >= 0.4:
        return ConfidenceLevel.LOW, "#f97316"  # orange
    else:
        return ConfidenceLevel.UNCERTAIN, "#ef4444"  # red

def format_confidence_indicator(score: float, format: str = "text") -> str:
    """Format confidence for display."""
    level, color = calculate_confidence(score)
    percentage = int(score * 100)

    if format == "html":
        return f'<span class="confidence-indicator" style="color: {color}">Confidence: {percentage}% ({level.value})</span>'
    elif format == "emoji":
        emojis = {
            ConfidenceLevel.HIGH: "🟢",
            ConfidenceLevel.MEDIUM: "🟡",
            ConfidenceLevel.LOW: "🟠",
            ConfidenceLevel.UNCERTAIN: "🔴"
        }
        return f"{emojis[level]} {percentage}% confidence"
    else:
        return f"Confidence: {percentage}% ({level.value})"

class ConfidenceTracker:
    """Track confidence scores across AI decisions."""

    def __init__(self, threshold: float = 0.6):
        self.threshold = threshold
        self.scores: list = []

    def add_score(self, score: float, context: str = "") -> bool:
        """Add a confidence score. Returns True if above threshold."""
        self.scores.append({"score": score, "context": context})
        return score >= self.threshold

    def should_alert(self) -> bool:
        """Check if recent scores warrant an alert."""
        if len(self.scores) < 3:
            return False
        recent = [s["score"] for s in self.scores[-3:]]
        return sum(recent) / len(recent) < self.threshold

    def get_summary(self) -> Dict[str, Any]:
        """Get confidence summary."""
        if not self.scores:
            return {"count": 0, "average": 0, "below_threshold": 0}

        scores = [s["score"] for s in self.scores]
        return {
            "count": len(scores),
            "average": sum(scores) / len(scores),
            "below_threshold": sum(1 for s in scores if s < self.threshold),
            "min": min(scores),
            "max": max(scores)
        }
