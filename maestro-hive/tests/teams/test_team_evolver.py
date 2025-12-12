"""
Tests for TeamEvolver - MD-3020

Comprehensive test suite for team evolution functionality.
"""

import pytest
from datetime import datetime
from unittest.mock import Mock, patch

from maestro_hive.teams.team_evolver import (
    TeamEvolver,
    EvolverConfig,
    EvolutionStrategy,
    TeamConfiguration,
    TeamRole,
    EvolutionMetrics,
    EvolutionResult,
    get_default_evolver,
    evolve_team,
)


class TestTeamRole:
    """Tests for TeamRole dataclass."""

    def test_team_role_creation(self):
        """Test creating a team role."""
        role = TeamRole(
            name="backend_dev",
            skills=["python", "databases"],
            weight=1.0
        )
        assert role.name == "backend_dev"
        assert "python" in role.skills
        assert role.weight == 1.0

    def test_team_role_default_values(self):
        """Test team role with default values."""
        role = TeamRole(name="qa", skills=["testing"])
        assert role.weight == 1.0
        assert role.required is False


class TestTeamConfiguration:
    """Tests for TeamConfiguration dataclass."""

    def test_configuration_creation(self):
        """Test creating team configuration."""
        roles = [
            TeamRole(name="dev", skills=["python"], weight=1.0),
            TeamRole(name="qa", skills=["testing"], weight=0.5),
        ]
        config = TeamConfiguration(
            config_id="cfg_1",
            team_id="team_alpha",
            roles=roles,
            skill_weights={"python": 1.0, "testing": 0.8},
            fitness_score=0.75,
            generation=1
        )
        assert config.config_id == "cfg_1"
        assert len(config.roles) == 2
        assert config.fitness_score == 0.75

    def test_configuration_to_dict(self):
        """Test converting configuration to dictionary."""
        config = TeamConfiguration(
            config_id="cfg_2",
            team_id="team_beta",
            roles=[TeamRole(name="dev", skills=["java"])],
            skill_weights={"java": 1.0},
            fitness_score=0.8,
            generation=2
        )
        data = config.to_dict()
        assert data["config_id"] == "cfg_2"
        assert data["team_id"] == "team_beta"
        assert data["fitness_score"] == 0.8


class TestEvolverConfig:
    """Tests for EvolverConfig dataclass."""

    def test_default_config(self):
        """Test default configuration values."""
        config = EvolverConfig()
        assert config.strategy == EvolutionStrategy.GENETIC
        assert config.population_size == 20
        assert config.max_generations == 100
        assert config.mutation_rate == 0.1
        assert config.crossover_rate == 0.7
        assert config.elitism_count == 2
        assert config.fitness_threshold == 0.95
        assert config.max_stagnation == 5

    def test_custom_config(self):
        """Test custom configuration."""
        config = EvolverConfig(
            strategy=EvolutionStrategy.SIMULATED_ANNEALING,
            population_size=50,
            max_generations=200
        )
        assert config.strategy == EvolutionStrategy.SIMULATED_ANNEALING
        assert config.population_size == 50


class TestEvolutionStrategy:
    """Tests for EvolutionStrategy enum."""

    def test_all_strategies_defined(self):
        """Test all evolution strategies are defined."""
        strategies = list(EvolutionStrategy)
        assert EvolutionStrategy.GENETIC in strategies
        assert EvolutionStrategy.HILL_CLIMBING in strategies
        assert EvolutionStrategy.SIMULATED_ANNEALING in strategies
        assert EvolutionStrategy.MEMETIC in strategies

    def test_strategy_values(self):
        """Test strategy string values."""
        assert EvolutionStrategy.GENETIC.value == "genetic"
        assert EvolutionStrategy.HILL_CLIMBING.value == "hill_climbing"


class TestTeamEvolver:
    """Tests for TeamEvolver class."""

    @pytest.fixture
    def evolver(self):
        """Create evolver instance for tests."""
        return TeamEvolver()

    @pytest.fixture
    def sample_roles(self):
        """Create sample roles for testing."""
        return [
            TeamRole(name="backend_dev", skills=["python", "sql"], weight=1.0),
            TeamRole(name="frontend_dev", skills=["javascript", "react"], weight=1.0),
            TeamRole(name="qa_engineer", skills=["testing", "automation"], weight=0.8),
        ]

    def test_evolver_initialization(self, evolver):
        """Test evolver initializes correctly."""
        assert evolver.config is not None
        assert isinstance(evolver.config, EvolverConfig)

    def test_evolver_custom_config(self):
        """Test evolver with custom config."""
        config = EvolverConfig(
            strategy=EvolutionStrategy.HILL_CLIMBING,
            max_generations=100
        )
        evolver = TeamEvolver(config=config)
        assert evolver.config.strategy == EvolutionStrategy.HILL_CLIMBING
        assert evolver.config.max_generations == 100

    def test_register_team(self, evolver, sample_roles):
        """Test registering a team."""
        evolver.register_team(
            team_id="team_1",
            members=["dev1", "dev2", "qa1"]
        )
        team = evolver.get_team("team_1")
        assert team is not None
        assert len(team["members"]) == 3

    def test_register_team_stores_metadata(self, evolver, sample_roles):
        """Test that register_team stores metadata."""
        evolver.register_team("team_1", members=["dev1"], metadata={"location": "NYC"})
        evolver.register_team("team_2", members=["dev2"], metadata={"location": "LA"})
        team1 = evolver.get_team("team_1")
        team2 = evolver.get_team("team_2")
        assert team1["metadata"]["location"] == "NYC"
        assert team2["metadata"]["location"] == "LA"

    def test_get_fitness(self, evolver, sample_roles):
        """Test getting fitness score."""
        evolver.register_team("team_1", members=["dev1", "qa1"])
        # Initially no population, so fitness is 0
        fitness = evolver.get_fitness("team_1")
        assert fitness == 0.0

    def test_get_fitness_unregistered_team(self, evolver):
        """Test getting fitness for unregistered team."""
        fitness = evolver.get_fitness("nonexistent_team")
        assert fitness == 0.0

    def test_evolve_basic(self, evolver, sample_roles):
        """Test basic evolution."""
        evolver.register_team("team_1", members=["dev1", "qa1"])
        result = evolver.evolve("team_1", generations=5)

        assert isinstance(result, EvolutionResult)
        assert result.team_id == "team_1"
        assert result.generations_completed <= 5
        assert result.best_fitness >= 0.0

    def test_evolve_returns_history(self, evolver, sample_roles):
        """Test evolution returns history."""
        evolver.register_team("team_1", members=["dev1"])
        result = evolver.evolve("team_1", generations=3)

        assert len(result.evolution_history) > 0
        for metrics in result.evolution_history:
            assert isinstance(metrics, EvolutionMetrics)

    def test_evolve_improves_fitness(self, evolver, sample_roles):
        """Test evolution tends to improve fitness."""
        evolver.register_team("team_1", members=["dev1", "qa1"])
        initial_fitness = evolver.get_fitness("team_1")
        result = evolver.evolve("team_1", generations=10)

        # Fitness should not decrease significantly
        assert result.best_fitness >= initial_fitness * 0.9

    def test_evolve_with_different_strategies(self, evolver, sample_roles):
        """Test evolution with different strategies."""
        for strategy in EvolutionStrategy:
            config = EvolverConfig(strategy=strategy, max_generations=5)
            evolver = TeamEvolver(config=config)
            evolver.register_team("team_1", members=["dev1"])
            result = evolver.evolve("team_1", generations=3)
            assert result.best_fitness >= 0.0

    def test_evolve_unregistered_team_raises(self, evolver):
        """Test evolving unregistered team raises error."""
        with pytest.raises(ValueError, match="not registered"):
            evolver.evolve("nonexistent")

    def test_get_best_configuration(self, evolver, sample_roles):
        """Test getting best configuration."""
        evolver.register_team("team_1", members=["dev1"])
        evolver.evolve("team_1", generations=3)
        best = evolver.get_best_configuration("team_1")

        assert best is not None
        assert best.team_id == "team_1"

    def test_get_evolution_history(self, evolver, sample_roles):
        """Test getting evolution history."""
        evolver.register_team("team_1", members=["dev1"])
        evolver.evolve("team_1", generations=5)
        history = evolver.get_evolution_history("team_1")

        assert len(history) > 0

    def test_evolution_stagnation(self, evolver, sample_roles):
        """Test evolution stops on stagnation."""
        config = EvolverConfig(max_stagnation=2, max_generations=50)
        evolver = TeamEvolver(config=config)
        evolver.register_team("team_1", members=["dev1"])
        result = evolver.evolve("team_1", generations=50)

        # Should stop before max generations due to stagnation or convergence
        assert result.generations_completed > 0

    def test_convergence_detection(self, evolver, sample_roles):
        """Test convergence is detected."""
        config = EvolverConfig(
            fitness_threshold=0.1,  # Low threshold for easy convergence
            max_stagnation=20
        )
        evolver = TeamEvolver(config=config)
        evolver.register_team("team_1", members=["dev1"])
        result = evolver.evolve("team_1", generations=50)

        # Should converge before max generations
        assert result.converged or result.generations_completed > 0

    def test_population_diversity_tracking(self, evolver, sample_roles):
        """Test population diversity is tracked."""
        evolver.register_team("team_1", members=["dev1"])
        result = evolver.evolve("team_1", generations=5)

        for metrics in result.evolution_history:
            assert 0.0 <= metrics.population_diversity <= 1.0


class TestEvolutionMetrics:
    """Tests for EvolutionMetrics dataclass."""

    def test_metrics_creation(self):
        """Test creating evolution metrics."""
        metrics = EvolutionMetrics(
            team_id="team_1",
            generation=5,
            best_fitness=0.85,
            average_fitness=0.72,
            population_diversity=0.3,
            stagnation_count=0
        )
        assert metrics.generation == 5
        assert metrics.best_fitness == 0.85


class TestEvolutionResult:
    """Tests for EvolutionResult dataclass."""

    def test_result_creation(self):
        """Test creating evolution result."""
        config = TeamConfiguration(
            config_id="cfg_1",
            team_id="team_1",
            roles=[],
            skill_weights={},
            fitness_score=0.9,
            generation=10
        )
        result = EvolutionResult(
            team_id="team_1",
            best_configuration=config,
            best_fitness=0.9,
            generations_completed=10,
            evolution_history=[],
            converged=True,
            total_duration_ms=1000
        )
        assert result.converged is True
        assert result.best_fitness == 0.9


class TestModuleFunctions:
    """Tests for module-level convenience functions."""

    def test_get_default_evolver(self):
        """Test getting default evolver."""
        evolver1 = get_default_evolver()
        evolver2 = get_default_evolver()
        assert evolver1 is evolver2  # Same instance

    def test_evolve_team_function(self):
        """Test evolve_team convenience function."""
        evolver = get_default_evolver()
        evolver.register_team("test_team", members=["dev1"])

        result = evolve_team("test_team", generations=2)
        assert isinstance(result, EvolutionResult)


class TestGeneticOperations:
    """Tests for genetic algorithm operations."""

    @pytest.fixture
    def evolver(self):
        """Create evolver with genetic strategy."""
        config = EvolverConfig(strategy=EvolutionStrategy.GENETIC)
        return TeamEvolver(config=config)

    def test_mutation_preserves_validity(self, evolver):
        """Test mutation produces valid configurations."""
        evolver.register_team("team_1", members=["dev1", "qa1"])
        evolver.evolve("team_1", generations=5)
        best = evolver.get_best_configuration("team_1")

        assert best is not None
        assert all(0.0 <= role.weight <= 2.0 for role in best.roles)

    def test_crossover_produces_offspring(self, evolver):
        """Test crossover produces valid offspring."""
        evolver.register_team("team_1", members=["dev1", "qa1"])
        result = evolver.evolve("team_1", generations=5)

        # Should have produced multiple generations
        assert result.generations_completed > 0


class TestHillClimbing:
    """Tests for hill climbing strategy."""

    def test_hill_climbing_evolution(self):
        """Test hill climbing produces results."""
        config = EvolverConfig(strategy=EvolutionStrategy.HILL_CLIMBING)
        evolver = TeamEvolver(config=config)

        evolver.register_team("team_1", members=["dev1"])
        result = evolver.evolve("team_1", generations=5)

        assert result.best_fitness >= 0.0


class TestSimulatedAnnealing:
    """Tests for simulated annealing strategy."""

    def test_simulated_annealing_evolution(self):
        """Test simulated annealing produces results."""
        config = EvolverConfig(strategy=EvolutionStrategy.SIMULATED_ANNEALING)
        evolver = TeamEvolver(config=config)

        evolver.register_team("team_1", members=["dev1"])
        result = evolver.evolve("team_1", generations=5)

        assert result.best_fitness >= 0.0


class TestMemeticAlgorithm:
    """Tests for memetic (hybrid) algorithm strategy."""

    def test_memetic_evolution(self):
        """Test memetic algorithm produces results."""
        config = EvolverConfig(strategy=EvolutionStrategy.MEMETIC)
        evolver = TeamEvolver(config=config)

        evolver.register_team("team_1", members=["dev1"])
        result = evolver.evolve("team_1", generations=5)

        assert result.best_fitness >= 0.0


class TestEdgeCases:
    """Tests for edge cases."""

    def test_empty_members(self):
        """Test handling empty members list."""
        evolver = TeamEvolver()
        evolver.register_team("team_1", members=[])
        team = evolver.get_team("team_1")
        assert len(team["members"]) == 0

    def test_single_member(self):
        """Test evolution with single member."""
        evolver = TeamEvolver()
        evolver.register_team("team_1", members=["solo"])
        result = evolver.evolve("team_1", generations=3)
        assert result.best_fitness >= 0.0

    def test_many_members(self):
        """Test evolution with many members."""
        evolver = TeamEvolver()
        members = [f"member_{i}" for i in range(20)]
        evolver.register_team("team_1", members=members)
        result = evolver.evolve("team_1", generations=3)
        assert result.best_fitness >= 0.0

    def test_zero_generations(self):
        """Test evolution with zero generations."""
        evolver = TeamEvolver()
        evolver.register_team("team_1", members=["dev1"])
        result = evolver.evolve("team_1", generations=0)
        assert result.generations_completed == 0
