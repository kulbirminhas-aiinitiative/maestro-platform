"""
CAPA Effectiveness Predictor Module
====================================

AI-powered prediction of CAPA effectiveness based on historical data.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class EffectivenessRating(Enum):
    """CAPA effectiveness rating."""
    EXCELLENT = "excellent"    # >90% success rate
    GOOD = "good"              # 75-90% success rate
    ADEQUATE = "adequate"      # 60-75% success rate
    POOR = "poor"              # <60% success rate
    UNKNOWN = "unknown"


@dataclass
class HistoricalCAPAData:
    """Historical CAPA data for ML training."""
    capa_id: str
    root_cause_category: str
    action_types: List[str]
    time_to_implement: int  # days
    recurrence_within_year: bool
    effectiveness_verified: bool
    success: bool  # Did it prevent recurrence?
    features: Dict[str, Any] = field(default_factory=dict)


@dataclass
class EffectivenessPrediction:
    """CAPA effectiveness prediction result."""
    predicted_success_rate: float
    confidence: float
    rating: EffectivenessRating
    risk_factors: List[str]
    recommendations: List[str]
    similar_capas: List[Dict[str, Any]]
    predicted_at: datetime


class EffectivenessFeatureExtractor:
    """Extracts features from CAPA data for prediction."""
    
    # Features that correlate with CAPA success
    SUCCESS_INDICATORS = {
        "root_cause_verified": 0.25,
        "multiple_actions": 0.15,
        "timeline_reasonable": 0.15,
        "cross_functional_team": 0.20,
        "systemic_fix": 0.15,
        "training_included": 0.10,
    }
    
    # Risk factors that reduce success probability
    RISK_FACTORS = {
        "no_root_cause": ("Root cause not properly identified", -0.30),
        "quick_fix": ("Appears to be quick fix rather than systemic", -0.20),
        "no_verification": ("No verification plan defined", -0.15),
        "overdue_history": ("Similar CAPAs have history of overdue", -0.10),
        "single_action": ("Only single corrective action defined", -0.10),
        "no_preventive": ("No preventive measures included", -0.15),
    }
    
    def extract_features(self, capa_data: Dict[str, Any]) -> Dict[str, float]:
        """
        Extract predictive features from CAPA data.
        
        Args:
            capa_data: CAPA record data
            
        Returns:
            Dictionary of feature scores
        """
        features = {}
        
        # Root cause analysis quality
        root_cause = capa_data.get("root_cause", "")
        rca_data = capa_data.get("root_cause_analysis", {})
        
        features["root_cause_verified"] = 1.0 if (
            root_cause and len(root_cause) > 50 and rca_data
        ) else 0.0
        
        # Action plan quality
        actions = capa_data.get("actions", [])
        features["multiple_actions"] = 1.0 if len(actions) >= 3 else 0.5 if len(actions) >= 2 else 0.0
        
        # Timeline assessment
        due_days = capa_data.get("due_days", 90)
        num_actions = len(actions)
        reasonable_timeline = (due_days / max(num_actions, 1)) >= 14
        features["timeline_reasonable"] = 1.0 if reasonable_timeline else 0.5
        
        # Team involvement
        owners = set(a.get("responsible_party", "") for a in actions)
        features["cross_functional_team"] = 1.0 if len(owners) >= 2 else 0.0
        
        # Systemic vs quick fix assessment
        action_text = " ".join(a.get("description", "").lower() for a in actions)
        systemic_keywords = ["process", "procedure", "training", "system", "automation", "design"]
        quick_fix_keywords = ["remind", "retrain", "warning", "memo"]
        
        systemic_score = sum(1 for kw in systemic_keywords if kw in action_text)
        quick_fix_score = sum(1 for kw in quick_fix_keywords if kw in action_text)
        
        features["systemic_fix"] = min(1.0, systemic_score * 0.2) if systemic_score > quick_fix_score else 0.0
        
        # Training included
        features["training_included"] = 1.0 if "training" in action_text or "train" in action_text else 0.0
        
        return features
    
    def identify_risk_factors(self, capa_data: Dict[str, Any]) -> List[Tuple[str, str, float]]:
        """
        Identify risk factors that may reduce effectiveness.
        
        Returns:
            List of (risk_id, description, impact) tuples
        """
        risks = []
        
        root_cause = capa_data.get("root_cause", "")
        if not root_cause or len(root_cause) < 20:
            risks.append(self.RISK_FACTORS["no_root_cause"] + ("no_root_cause",))
        
        actions = capa_data.get("actions", [])
        if len(actions) == 1:
            risks.append(self.RISK_FACTORS["single_action"] + ("single_action",))
        
        action_text = " ".join(a.get("description", "").lower() for a in actions)
        if not any(kw in action_text for kw in ["prevent", "systemic", "process"]):
            risks.append(self.RISK_FACTORS["no_preventive"] + ("no_preventive",))
        
        return [(r[2], r[0], r[1]) for r in risks]


class SimilarCAPAFinder:
    """
    Finds similar historical CAPAs for reference and learning.
    
    Uses text similarity and categorical matching to identify
    relevant historical CAPAs.
    """
    
    def __init__(self):
        self.historical_capas: List[Dict[str, Any]] = []
        self.logger = logging.getLogger("qms-capa-finder")
    
    def add_historical_capa(self, capa_data: Dict[str, Any]) -> None:
        """Add a CAPA to the historical database."""
        self.historical_capas.append(capa_data)
    
    def find_similar(
        self,
        capa_data: Dict[str, Any],
        max_results: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Find similar historical CAPAs.
        
        Args:
            capa_data: Current CAPA data
            max_results: Maximum number of results
            
        Returns:
            List of similar CAPAs with similarity scores
        """
        if not self.historical_capas:
            return []
        
        # Calculate similarity scores
        scored_capas = []
        for historical in self.historical_capas:
            score = self._calculate_similarity(capa_data, historical)
            if score > 0.3:  # Minimum threshold
                scored_capas.append({
                    "capa": historical,
                    "similarity_score": score,
                    "matching_factors": self._get_matching_factors(capa_data, historical)
                })
        
        # Sort by similarity score descending
        scored_capas.sort(key=lambda x: x["similarity_score"], reverse=True)
        
        return scored_capas[:max_results]
    
    def _calculate_similarity(
        self,
        capa1: Dict[str, Any],
        capa2: Dict[str, Any]
    ) -> float:
        """Calculate similarity score between two CAPAs."""
        score = 0.0
        
        # Category match (weight: 0.3)
        if capa1.get("category") == capa2.get("category"):
            score += 0.3
        
        # Root cause category match (weight: 0.25)
        if capa1.get("root_cause_category") == capa2.get("root_cause_category"):
            score += 0.25
        
        # Keyword overlap in description (weight: 0.25)
        desc1_words = set(capa1.get("description", "").lower().split())
        desc2_words = set(capa2.get("description", "").lower().split())
        if desc1_words and desc2_words:
            overlap = len(desc1_words & desc2_words) / max(len(desc1_words), len(desc2_words))
            score += overlap * 0.25
        
        # Same source (weight: 0.1)
        if capa1.get("source_nc_category") == capa2.get("source_nc_category"):
            score += 0.1
        
        # Similar priority (weight: 0.1)
        if capa1.get("priority") == capa2.get("priority"):
            score += 0.1
        
        return min(score, 1.0)
    
    def _get_matching_factors(
        self,
        capa1: Dict[str, Any],
        capa2: Dict[str, Any]
    ) -> List[str]:
        """Get list of matching factors between CAPAs."""
        factors = []
        
        if capa1.get("category") == capa2.get("category"):
            factors.append(f"Same category: {capa1.get('category')}")
        
        if capa1.get("root_cause_category") == capa2.get("root_cause_category"):
            factors.append(f"Same root cause category: {capa1.get('root_cause_category')}")
        
        if capa1.get("priority") == capa2.get("priority"):
            factors.append(f"Same priority: {capa1.get('priority')}")
        
        return factors


class EffectivenessPredictor:
    """
    AI-powered CAPA effectiveness predictor.
    
    Predicts the likelihood of CAPA success based on:
    - Historical data patterns
    - Root cause analysis quality
    - Action plan completeness
    - Similar CAPA outcomes
    """
    
    def __init__(self):
        self.feature_extractor = EffectivenessFeatureExtractor()
        self.similar_finder = SimilarCAPAFinder()
        self.logger = logging.getLogger("qms-effectiveness")
        self._configure_logger()
    
    def _configure_logger(self) -> None:
        """Configure logger."""
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)
    
    def predict(self, capa_data: Dict[str, Any]) -> EffectivenessPrediction:
        """
        Predict CAPA effectiveness.
        
        Args:
            capa_data: CAPA record data including root cause and actions
            
        Returns:
            EffectivenessPrediction with success probability and recommendations
        """
        # Extract features
        features = self.feature_extractor.extract_features(capa_data)
        
        # Calculate base score from features
        base_score = sum(
            features.get(feature, 0) * weight
            for feature, weight in self.feature_extractor.SUCCESS_INDICATORS.items()
        )
        
        # Identify and apply risk factors
        risks = self.feature_extractor.identify_risk_factors(capa_data)
        risk_penalty = sum(r[2] for r in risks)
        
        # Find similar CAPAs
        similar_capas = self.similar_finder.find_similar(capa_data)
        
        # Adjust based on similar CAPA outcomes
        if similar_capas:
            successful_similar = [s for s in similar_capas if s["capa"].get("success", False)]
            success_rate_adjustment = (len(successful_similar) / len(similar_capas) - 0.5) * 0.2
        else:
            success_rate_adjustment = 0
        
        # Calculate final prediction
        predicted_success_rate = min(1.0, max(0.0, 
            base_score + risk_penalty + success_rate_adjustment
        ))
        
        # Determine rating
        if predicted_success_rate >= 0.9:
            rating = EffectivenessRating.EXCELLENT
        elif predicted_success_rate >= 0.75:
            rating = EffectivenessRating.GOOD
        elif predicted_success_rate >= 0.6:
            rating = EffectivenessRating.ADEQUATE
        else:
            rating = EffectivenessRating.POOR
        
        # Generate recommendations
        recommendations = self._generate_recommendations(features, risks, similar_capas)
        
        # Calculate confidence based on data availability
        confidence = min(0.9, 0.5 + (len(similar_capas) * 0.08) + (sum(features.values()) / 10))
        
        prediction = EffectivenessPrediction(
            predicted_success_rate=predicted_success_rate,
            confidence=confidence,
            rating=rating,
            risk_factors=[r[1] for r in risks],
            recommendations=recommendations,
            similar_capas=similar_capas,
            predicted_at=datetime.utcnow()
        )
        
        self.logger.info(
            f"EFFECTIVENESS_PREDICTED | success_rate={predicted_success_rate:.2f} | "
            f"rating={rating.value} | confidence={confidence:.2f}"
        )
        
        return prediction
    
    def _generate_recommendations(
        self,
        features: Dict[str, float],
        risks: List[Tuple[str, str, float]],
        similar_capas: List[Dict[str, Any]]
    ) -> List[str]:
        """Generate recommendations to improve CAPA effectiveness."""
        recommendations = []
        
        # Address identified risks
        for risk_id, description, _ in risks:
            if risk_id == "no_root_cause":
                recommendations.append(
                    "Perform thorough root cause analysis using 5-Why or Fishbone methodology"
                )
            elif risk_id == "single_action":
                recommendations.append(
                    "Add additional corrective and preventive actions for comprehensive coverage"
                )
            elif risk_id == "no_preventive":
                recommendations.append(
                    "Include systemic/preventive measures to prevent recurrence"
                )
        
        # Feature-based recommendations
        if features.get("cross_functional_team", 0) < 1:
            recommendations.append(
                "Involve cross-functional team members for diverse perspectives"
            )
        
        if features.get("training_included", 0) < 1:
            recommendations.append(
                "Consider adding training component to reinforce corrective measures"
            )
        
        # Learn from similar CAPAs
        if similar_capas:
            successful = [s for s in similar_capas if s["capa"].get("success", False)]
            if successful:
                best_practice = successful[0]
                recommendations.append(
                    f"Review successful similar CAPA {best_practice['capa'].get('id', 'N/A')} "
                    "for best practices"
                )
        
        return recommendations
    
    def add_historical_outcome(
        self,
        capa_id: str,
        capa_data: Dict[str, Any],
        success: bool
    ) -> None:
        """
        Add historical CAPA outcome for future predictions.
        
        Args:
            capa_id: CAPA identifier
            capa_data: Full CAPA data
            success: Whether the CAPA was effective
        """
        capa_data["id"] = capa_id
        capa_data["success"] = success
        self.similar_finder.add_historical_capa(capa_data)
        
        self.logger.info(
            f"HISTORICAL_CAPA_ADDED | capa_id={capa_id} | success={success}"
        )
