"""Innovation Generator - Generate novel solutions."""
import logging
import random
from typing import Dict, List, Optional
from uuid import UUID
from .models import Innovation, InnovationSeed, InnovationType, CombinationStrategy

logger = logging.getLogger(__name__)


class InnovationGenerator:
    """Generates innovations from seeds and combinations."""
    
    def __init__(self):
        self._seeds: Dict[UUID, InnovationSeed] = {}
        self._generated: List[Innovation] = []
    
    def add_seed(self, concept: str, domain: str, attributes: Optional[Dict] = None) -> InnovationSeed:
        """Add a seed concept."""
        seed = InnovationSeed(concept=concept, domain=domain, attributes=attributes or {})
        self._seeds[seed.id] = seed
        logger.debug("Added seed: %s", concept)
        return seed
    
    def generate_incremental(self, seed_id: UUID, enhancement: str) -> Optional[Innovation]:
        """Generate incremental innovation from a seed."""
        seed = self._seeds.get(seed_id)
        if not seed:
            return None
        
        innovation = Innovation(
            innovation_type=InnovationType.INCREMENTAL,
            title=f"Enhanced {seed.concept}",
            description=f"{seed.concept} with {enhancement}",
            source_seeds=[seed_id],
            novelty_score=0.3,
            feasibility_score=0.8,
            impact_score=0.5
        )
        self._generated.append(innovation)
        return innovation
    
    def generate_combination(self, seed_ids: List[UUID], strategy: CombinationStrategy) -> Optional[Innovation]:
        """Generate innovation by combining seeds."""
        seeds = [self._seeds.get(sid) for sid in seed_ids if sid in self._seeds]
        if len(seeds) < 2:
            return None
        
        concepts = [s.concept for s in seeds]
        
        if strategy == CombinationStrategy.MERGE:
            title = " + ".join(concepts)
            description = f"Merged {', '.join(concepts)} into unified solution"
        elif strategy == CombinationStrategy.BLEND:
            title = f"Blended {concepts[0]}-{concepts[1]}"
            description = f"Seamless blend of {' and '.join(concepts)}"
        elif strategy == CombinationStrategy.CHAIN:
            title = f"{concepts[0]} -> {concepts[1]} Pipeline"
            description = f"Sequential combination: {' -> '.join(concepts)}"
        else:
            title = f"{concepts[0]} with {concepts[1]} substitution"
            description = f"Substituted elements between {' and '.join(concepts)}"
        
        innovation = Innovation(
            innovation_type=InnovationType.COMBINATION,
            title=title,
            description=description,
            source_seeds=seed_ids,
            strategy_used=strategy,
            novelty_score=0.6,
            feasibility_score=0.6,
            impact_score=0.7
        )
        self._generated.append(innovation)
        return innovation
    
    def generate_novel(self, domain: str, constraints: Optional[List[str]] = None) -> Innovation:
        """Generate completely novel innovation."""
        innovation = Innovation(
            innovation_type=InnovationType.NOVEL,
            title=f"Novel {domain} Solution",
            description=f"A novel approach to {domain}" + 
                        (f" considering: {', '.join(constraints)}" if constraints else ""),
            novelty_score=0.9,
            feasibility_score=0.4,
            impact_score=0.8
        )
        self._generated.append(innovation)
        return innovation
    
    def get_innovations(self, innovation_type: Optional[InnovationType] = None) -> List[Innovation]:
        """Get generated innovations."""
        if innovation_type:
            return [i for i in self._generated if i.innovation_type == innovation_type]
        return list(self._generated)
    
    def get_seeds(self) -> List[InnovationSeed]:
        return list(self._seeds.values())
