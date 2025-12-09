"""Innovation Engine - Generate novel solutions and creative combinations."""
from .models import Innovation, InnovationSeed, CombinationStrategy
from .generator import InnovationGenerator
from .evaluator import InnovationEvaluator
from .combiner import ConceptCombiner

__version__ = "1.0.0"
__all__ = ["Innovation", "InnovationSeed", "CombinationStrategy",
           "InnovationGenerator", "InnovationEvaluator", "ConceptCombiner"]
