"""Learning Engine - Enable AI agents to learn and improve from experience."""
from .models import LearningEvent, LearningPattern, FeedbackSignal
from .collector import ExperienceCollector
from .analyzer import PatternAnalyzer
from .reinforcer import BehaviorReinforcer

__version__ = "1.0.0"
__all__ = ["LearningEvent", "LearningPattern", "FeedbackSignal", 
           "ExperienceCollector", "PatternAnalyzer", "BehaviorReinforcer"]
