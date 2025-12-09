"""Concept Combiner - Combine concepts in creative ways."""
import logging
from typing import Dict, List, Optional, Tuple
from .models import InnovationSeed, Innovation, CombinationStrategy
from .generator import InnovationGenerator

logger = logging.getLogger(__name__)


class ConceptCombiner:
    """Combines concepts to create innovations."""
    
    def __init__(self, generator: InnovationGenerator):
        self.generator = generator
        self._combination_history: List[Tuple] = []
    
    def find_compatible_seeds(self, seed_id: str) -> List[InnovationSeed]:
        """Find seeds that could combine well with the given seed."""
        seeds = self.generator.get_seeds()
        target = next((s for s in seeds if str(s.id) == seed_id), None)
        if not target:
            return []
        
        # Simple compatibility: same domain or shared attributes
        compatible = []
        for seed in seeds:
            if seed.id == target.id:
                continue
            if seed.domain == target.domain:
                compatible.append(seed)
            elif set(seed.attributes.keys()) & set(target.attributes.keys()):
                compatible.append(seed)
        
        return compatible
    
    def auto_combine(self, strategy: CombinationStrategy = CombinationStrategy.MERGE) -> List[Innovation]:
        """Automatically combine compatible seeds."""
        seeds = self.generator.get_seeds()
        innovations = []
        
        for i, seed1 in enumerate(seeds):
            for seed2 in seeds[i+1:]:
                if seed1.domain == seed2.domain:
                    innovation = self.generator.generate_combination(
                        [seed1.id, seed2.id], strategy
                    )
                    if innovation:
                        innovations.append(innovation)
                        self._combination_history.append((seed1.id, seed2.id, strategy))
        
        logger.info("Auto-combined %d pairs", len(innovations))
        return innovations
    
    def suggest_combinations(self, seed_id: str) -> List[Dict]:
        """Suggest possible combinations for a seed."""
        compatible = self.find_compatible_seeds(seed_id)
        suggestions = []
        
        for comp in compatible[:5]:
            for strategy in CombinationStrategy:
                suggestions.append({
                    "partner_seed": comp.concept,
                    "strategy": strategy.value,
                    "potential": "high" if comp.domain == self.generator._seeds.get(seed_id, InnovationSeed()).domain else "medium"
                })
        
        return suggestions
    
    def get_combination_stats(self) -> Dict:
        return {
            "total_combinations": len(self._combination_history),
            "strategies_used": len(set(c[2] for c in self._combination_history))
        }
