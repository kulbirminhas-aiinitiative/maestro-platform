"""Innovation Evaluator - Evaluate innovation quality."""
import logging
from typing import Dict, List, Optional
from .models import Innovation

logger = logging.getLogger(__name__)


class InnovationEvaluator:
    """Evaluates innovations for quality and viability."""
    
    def __init__(self, novelty_weight: float = 0.4, feasibility_weight: float = 0.3, impact_weight: float = 0.3):
        self.weights = {"novelty": novelty_weight, "feasibility": feasibility_weight, "impact": impact_weight}
        self._evaluations: Dict[str, Dict] = {}
    
    def evaluate(self, innovation: Innovation, context: Optional[Dict] = None) -> Dict:
        """Evaluate an innovation."""
        evaluation = {
            "innovation_id": str(innovation.id),
            "scores": {
                "novelty": innovation.novelty_score,
                "feasibility": innovation.feasibility_score,
                "impact": innovation.impact_score,
                "overall": innovation.overall_score
            },
            "rating": self._get_rating(innovation.overall_score),
            "recommendations": self._get_recommendations(innovation)
        }
        
        self._evaluations[str(innovation.id)] = evaluation
        logger.debug("Evaluated innovation %s: %.2f", innovation.id, innovation.overall_score)
        return evaluation
    
    def _get_rating(self, score: float) -> str:
        if score >= 0.8:
            return "excellent"
        elif score >= 0.6:
            return "good"
        elif score >= 0.4:
            return "moderate"
        else:
            return "needs_improvement"
    
    def _get_recommendations(self, innovation: Innovation) -> List[str]:
        recs = []
        if innovation.novelty_score < 0.5:
            recs.append("Consider more creative combinations")
        if innovation.feasibility_score < 0.5:
            recs.append("Assess implementation challenges")
        if innovation.impact_score < 0.5:
            recs.append("Define clearer value proposition")
        return recs
    
    def compare(self, innovations: List[Innovation]) -> List[Dict]:
        """Compare multiple innovations."""
        ranked = sorted(innovations, key=lambda i: i.overall_score, reverse=True)
        return [{"rank": i+1, "title": inn.title, "score": inn.overall_score} 
                for i, inn in enumerate(ranked)]
    
    def get_top_innovations(self, innovations: List[Innovation], n: int = 5) -> List[Innovation]:
        """Get top N innovations by score."""
        return sorted(innovations, key=lambda i: i.overall_score, reverse=True)[:n]
