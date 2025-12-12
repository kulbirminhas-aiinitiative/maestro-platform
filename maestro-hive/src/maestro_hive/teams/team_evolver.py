"""
Team Evolver Module - MD-3020

Implements adaptive team composition using evolutionary algorithms.
Supports genetic algorithms, hill climbing, and simulated annealing strategies.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple
import hashlib
import logging
import random
import uuid

logger = logging.getLogger(__name__)


class EvolutionStrategy(Enum):
    """Available evolution strategies."""
    GENETIC = "genetic"
    HILL_CLIMBING = "hill_climbing"
    SIMULATED_ANNEALING = "simulated_annealing"
    MEMETIC = "memetic"


@dataclass
class TeamRole:
    """Represents a role in a team."""
    name: str
    skills: List[str] = field(default_factory=list)
    weight: float = 1.0
    required: bool = False


@dataclass
class TeamConfiguration:
    """Represents a team configuration in the population."""
    config_id: str
    team_id: str
    roles: List[TeamRole]
    skill_weights: Dict[str, float]
    fitness_score: float = 0.0
    generation: int = 0
    created_at: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "config_id": self.config_id,
            "team_id": self.team_id,
            "roles": [{"name": r.name, "skills": r.skills, "weight": r.weight} for r in self.roles],
            "skill_weights": self.skill_weights,
            "fitness_score": self.fitness_score,
            "generation": self.generation,
            "created_at": self.created_at.isoformat(),
            "metadata": self.metadata
        }


@dataclass
class EvolutionMetrics:
    """Metrics for tracking evolution progress."""
    team_id: str
    generation: int
    best_fitness: float
    average_fitness: float
    population_diversity: float
    stagnation_count: int = 0
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class EvolutionResult:
    """Result of an evolution run."""
    team_id: str
    best_configuration: TeamConfiguration
    best_fitness: float
    generations_completed: int
    evolution_history: List[EvolutionMetrics]
    converged: bool
    total_duration_ms: int
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class EvolverConfig:
    """Configuration for the evolution process."""
    population_size: int = 20
    mutation_rate: float = 0.1
    crossover_rate: float = 0.7
    elitism_count: int = 2
    strategy: EvolutionStrategy = EvolutionStrategy.GENETIC
    fitness_threshold: float = 0.95
    max_stagnation: int = 5
    max_generations: int = 100


class TeamEvolver:
    """
    Manages adaptive team composition using evolutionary algorithms.

    Supports multiple evolution strategies for optimizing team configurations
    based on fitness functions.
    """

    def __init__(
        self,
        config: Optional[EvolverConfig] = None,
        fitness_function: Optional[Callable[[TeamConfiguration], float]] = None
    ):
        self.config = config or EvolverConfig()
        self._fitness_function = fitness_function or self._default_fitness
        self._teams: Dict[str, Dict[str, Any]] = {}
        self._populations: Dict[str, List[TeamConfiguration]] = {}
        self._evolution_history: Dict[str, List[EvolutionMetrics]] = {}
        self._available_roles: List[str] = [
            "backend_developer", "frontend_developer", "qa_engineer",
            "devops_engineer", "designer", "product_manager"
        ]
        logger.info(f"TeamEvolver initialized with strategy: {self.config.strategy.value}")

    def register_team(
        self,
        team_id: str,
        members: List[str],
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Register a team for evolution."""
        self._teams[team_id] = {
            "members": members,
            "metadata": metadata or {},
            "registered_at": datetime.now()
        }
        self._populations[team_id] = []
        self._evolution_history[team_id] = []
        logger.debug(f"Registered team: {team_id} with {len(members)} members")

    def get_team(self, team_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a registered team."""
        return self._teams.get(team_id)

    def set_available_roles(self, roles: List[str]) -> None:
        """Set the available roles for team composition."""
        self._available_roles = roles

    def evolve(
        self,
        team_id: str,
        generations: int = 10
    ) -> EvolutionResult:
        """
        Execute evolution cycles on a team.

        Args:
            team_id: ID of the team to evolve
            generations: Number of generations to run

        Returns:
            EvolutionResult with best configuration and metrics

        Raises:
            ValueError: If team not registered
        """
        if team_id not in self._teams:
            raise ValueError(f"Team '{team_id}' not registered")

        start_time = datetime.now()
        generations = min(generations, self.config.max_generations)

        # Initialize population if empty
        if not self._populations[team_id]:
            self._initialize_population(team_id)

        best_config = None
        best_fitness = 0.0
        stagnation_count = 0
        prev_best_fitness = 0.0

        for gen in range(generations):
            # Evaluate fitness
            self._evaluate_population(team_id)

            # Get best configuration
            population = self._populations[team_id]
            population.sort(key=lambda c: c.fitness_score, reverse=True)
            current_best = population[0]

            if current_best.fitness_score > best_fitness:
                best_fitness = current_best.fitness_score
                best_config = current_best
                stagnation_count = 0
            else:
                stagnation_count += 1

            # Record metrics
            avg_fitness = sum(c.fitness_score for c in population) / len(population)
            diversity = self._calculate_diversity(population)

            metrics = EvolutionMetrics(
                team_id=team_id,
                generation=gen,
                best_fitness=best_fitness,
                average_fitness=avg_fitness,
                population_diversity=diversity,
                stagnation_count=stagnation_count
            )
            self._evolution_history[team_id].append(metrics)

            # Check convergence
            if best_fitness >= self.config.fitness_threshold:
                logger.info(f"Team {team_id} converged at generation {gen}")
                break

            if stagnation_count >= self.config.max_stagnation:
                logger.info(f"Team {team_id} stagnated after {gen} generations")
                break

            # Evolve to next generation
            self._evolve_population(team_id, gen + 1)

        duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)

        return EvolutionResult(
            team_id=team_id,
            best_configuration=best_config,
            best_fitness=best_fitness,
            generations_completed=len(self._evolution_history[team_id]),
            evolution_history=self._evolution_history[team_id],
            converged=best_fitness >= self.config.fitness_threshold,
            total_duration_ms=duration_ms
        )

    def get_fitness(self, team_id: str) -> float:
        """Get current best fitness score for a team."""
        if team_id not in self._populations or not self._populations[team_id]:
            return 0.0
        return max(c.fitness_score for c in self._populations[team_id])

    def get_best_configuration(self, team_id: str) -> Optional[TeamConfiguration]:
        """Get the best configuration for a team."""
        if team_id not in self._populations or not self._populations[team_id]:
            return None
        return max(self._populations[team_id], key=lambda c: c.fitness_score)

    def get_evolution_history(self, team_id: str) -> List[EvolutionMetrics]:
        """Get evolution history for a team."""
        return self._evolution_history.get(team_id, [])

    def _initialize_population(self, team_id: str) -> None:
        """Initialize random population for a team."""
        team = self._teams[team_id]
        population = []

        for i in range(self.config.population_size):
            # Create random configuration
            num_roles = random.randint(2, min(5, len(self._available_roles)))
            selected_roles = random.sample(self._available_roles, num_roles)

            roles = [
                TeamRole(
                    name=role,
                    skills=self._get_role_skills(role),
                    weight=random.uniform(0.5, 1.5)
                )
                for role in selected_roles
            ]

            # Random skill weights
            skill_weights = {
                skill: random.uniform(0.0, 1.0)
                for role in roles
                for skill in role.skills
            }

            config = TeamConfiguration(
                config_id=str(uuid.uuid4())[:8],
                team_id=team_id,
                roles=roles,
                skill_weights=skill_weights,
                generation=0
            )
            population.append(config)

        self._populations[team_id] = population
        logger.debug(f"Initialized population of {len(population)} for team {team_id}")

    def _evaluate_population(self, team_id: str) -> None:
        """Evaluate fitness of all configurations in population."""
        for config in self._populations[team_id]:
            config.fitness_score = self._fitness_function(config)

    def _evolve_population(self, team_id: str, generation: int) -> None:
        """Evolve population to next generation."""
        if self.config.strategy == EvolutionStrategy.GENETIC:
            self._genetic_evolution(team_id, generation)
        elif self.config.strategy == EvolutionStrategy.HILL_CLIMBING:
            self._hill_climbing_evolution(team_id, generation)
        elif self.config.strategy == EvolutionStrategy.SIMULATED_ANNEALING:
            self._simulated_annealing_evolution(team_id, generation)
        elif self.config.strategy == EvolutionStrategy.MEMETIC:
            self._memetic_evolution(team_id, generation)

    def _genetic_evolution(self, team_id: str, generation: int) -> None:
        """Standard genetic algorithm evolution."""
        population = self._populations[team_id]
        population.sort(key=lambda c: c.fitness_score, reverse=True)

        new_population = []

        # Elitism: preserve best configurations
        for i in range(self.config.elitism_count):
            elite = TeamConfiguration(
                config_id=str(uuid.uuid4())[:8],
                team_id=team_id,
                roles=population[i].roles.copy(),
                skill_weights=population[i].skill_weights.copy(),
                generation=generation
            )
            new_population.append(elite)

        # Generate rest through crossover and mutation
        while len(new_population) < self.config.population_size:
            # Tournament selection
            parent1 = self._tournament_select(population)
            parent2 = self._tournament_select(population)

            # Crossover
            if random.random() < self.config.crossover_rate:
                child = self._crossover(parent1, parent2, team_id, generation)
            else:
                child = TeamConfiguration(
                    config_id=str(uuid.uuid4())[:8],
                    team_id=team_id,
                    roles=parent1.roles.copy(),
                    skill_weights=parent1.skill_weights.copy(),
                    generation=generation
                )

            # Mutation
            if random.random() < self.config.mutation_rate:
                self._mutate(child)

            new_population.append(child)

        self._populations[team_id] = new_population

    def _hill_climbing_evolution(self, team_id: str, generation: int) -> None:
        """Hill climbing optimization."""
        population = self._populations[team_id]
        new_population = []

        for config in population:
            # Try small mutations and keep if better
            mutated = TeamConfiguration(
                config_id=str(uuid.uuid4())[:8],
                team_id=team_id,
                roles=config.roles.copy(),
                skill_weights=config.skill_weights.copy(),
                generation=generation
            )
            self._mutate(mutated)
            mutated.fitness_score = self._fitness_function(mutated)

            if mutated.fitness_score > config.fitness_score:
                new_population.append(mutated)
            else:
                config.generation = generation
                new_population.append(config)

        self._populations[team_id] = new_population

    def _simulated_annealing_evolution(self, team_id: str, generation: int) -> None:
        """Simulated annealing optimization."""
        population = self._populations[team_id]
        temperature = 1.0 / (1 + generation * 0.1)  # Decrease temperature over time
        new_population = []

        for config in population:
            mutated = TeamConfiguration(
                config_id=str(uuid.uuid4())[:8],
                team_id=team_id,
                roles=config.roles.copy(),
                skill_weights=config.skill_weights.copy(),
                generation=generation
            )
            self._mutate(mutated)
            mutated.fitness_score = self._fitness_function(mutated)

            delta = mutated.fitness_score - config.fitness_score
            if delta > 0 or random.random() < pow(2.71828, delta / temperature):
                new_population.append(mutated)
            else:
                config.generation = generation
                new_population.append(config)

        self._populations[team_id] = new_population

    def _memetic_evolution(self, team_id: str, generation: int) -> None:
        """Memetic algorithm: genetic + local search."""
        # First do genetic evolution
        self._genetic_evolution(team_id, generation)

        # Then apply local search to best solutions
        population = self._populations[team_id]
        population.sort(key=lambda c: c.fitness_score, reverse=True)

        for config in population[:self.config.elitism_count]:
            # Local search: try small improvements
            for _ in range(3):
                mutated = TeamConfiguration(
                    config_id=str(uuid.uuid4())[:8],
                    team_id=team_id,
                    roles=config.roles.copy(),
                    skill_weights=config.skill_weights.copy(),
                    generation=generation
                )
                self._small_mutate(mutated)
                mutated.fitness_score = self._fitness_function(mutated)
                if mutated.fitness_score > config.fitness_score:
                    config.roles = mutated.roles
                    config.skill_weights = mutated.skill_weights
                    config.fitness_score = mutated.fitness_score

    def _tournament_select(self, population: List[TeamConfiguration], k: int = 3) -> TeamConfiguration:
        """Tournament selection."""
        tournament = random.sample(population, min(k, len(population)))
        return max(tournament, key=lambda c: c.fitness_score)

    def _crossover(
        self,
        parent1: TeamConfiguration,
        parent2: TeamConfiguration,
        team_id: str,
        generation: int
    ) -> TeamConfiguration:
        """Single-point crossover between two configurations."""
        # Combine roles from both parents
        all_roles = parent1.roles + parent2.roles
        unique_roles = list({r.name: r for r in all_roles}.values())

        # Select subset of roles
        num_roles = random.randint(2, min(5, len(unique_roles)))
        selected_roles = random.sample(unique_roles, num_roles)

        # Combine skill weights
        combined_weights = {**parent1.skill_weights, **parent2.skill_weights}

        return TeamConfiguration(
            config_id=str(uuid.uuid4())[:8],
            team_id=team_id,
            roles=selected_roles,
            skill_weights=combined_weights,
            generation=generation
        )

    def _mutate(self, config: TeamConfiguration) -> None:
        """Apply mutation to a configuration."""
        mutation_type = random.choice(["role", "weight", "add", "remove"])

        if mutation_type == "role" and config.roles:
            # Replace a role
            idx = random.randint(0, len(config.roles) - 1)
            new_role = random.choice(self._available_roles)
            config.roles[idx] = TeamRole(
                name=new_role,
                skills=self._get_role_skills(new_role),
                weight=random.uniform(0.5, 1.5)
            )

        elif mutation_type == "weight" and config.skill_weights:
            # Modify a weight
            key = random.choice(list(config.skill_weights.keys()))
            config.skill_weights[key] = max(0.0, min(1.0,
                config.skill_weights[key] + random.uniform(-0.2, 0.2)
            ))

        elif mutation_type == "add" and len(config.roles) < 5:
            # Add a role
            new_role = random.choice(self._available_roles)
            config.roles.append(TeamRole(
                name=new_role,
                skills=self._get_role_skills(new_role),
                weight=random.uniform(0.5, 1.5)
            ))

        elif mutation_type == "remove" and len(config.roles) > 2:
            # Remove a role
            idx = random.randint(0, len(config.roles) - 1)
            config.roles.pop(idx)

    def _small_mutate(self, config: TeamConfiguration) -> None:
        """Apply small mutation for local search."""
        if config.skill_weights:
            key = random.choice(list(config.skill_weights.keys()))
            config.skill_weights[key] = max(0.0, min(1.0,
                config.skill_weights[key] + random.uniform(-0.05, 0.05)
            ))

    def _calculate_diversity(self, population: List[TeamConfiguration]) -> float:
        """Calculate population diversity."""
        if len(population) < 2:
            return 0.0

        fitness_values = [c.fitness_score for c in population]
        mean = sum(fitness_values) / len(fitness_values)
        variance = sum((f - mean) ** 2 for f in fitness_values) / len(fitness_values)
        return variance ** 0.5

    def _get_role_skills(self, role: str) -> List[str]:
        """Get default skills for a role."""
        skills_map = {
            "backend_developer": ["python", "api", "database", "testing"],
            "frontend_developer": ["javascript", "react", "css", "typescript"],
            "qa_engineer": ["testing", "automation", "quality"],
            "devops_engineer": ["docker", "kubernetes", "ci_cd", "cloud"],
            "designer": ["ui", "ux", "figma", "prototyping"],
            "product_manager": ["requirements", "planning", "communication"]
        }
        return skills_map.get(role, ["general"])

    def _default_fitness(self, config: TeamConfiguration) -> float:
        """Default fitness function based on configuration balance."""
        # Score based on:
        # 1. Role diversity (more diverse = better)
        # 2. Skill coverage
        # 3. Weight balance

        role_diversity = len(set(r.name for r in config.roles)) / max(1, len(config.roles))

        all_skills = set()
        for role in config.roles:
            all_skills.update(role.skills)
        skill_coverage = min(1.0, len(all_skills) / 10)  # Normalized to max 10 skills

        weights = list(config.skill_weights.values()) if config.skill_weights else [0.5]
        weight_balance = 1.0 - (max(weights) - min(weights)) if weights else 0.5

        fitness = (role_diversity * 0.4 + skill_coverage * 0.4 + weight_balance * 0.2)
        return max(0.0, min(1.0, fitness))

    def get_available_strategies(self) -> List[str]:
        """Return list of available evolution strategies."""
        return [s.value for s in EvolutionStrategy]


# Module-level convenience functions
_default_evolver: Optional[TeamEvolver] = None


def get_default_evolver() -> TeamEvolver:
    """Get or create the default team evolver instance."""
    global _default_evolver
    if _default_evolver is None:
        _default_evolver = TeamEvolver()
    return _default_evolver


def evolve_team(team_id: str, generations: int = 10) -> EvolutionResult:
    """Convenience function for quick team evolution."""
    evolver = get_default_evolver()
    return evolver.evolve(team_id, generations)
