"""
Teams Module - Autonomous Team Management and Retrospective Systems

This module provides:
- RetrospectiveEngine: Automated team retrospective analysis
- EvaluatorPersona: AI-powered performance evaluation
- ProcessImprover: Intelligent workflow optimization
- TeamSimulator: Scenario-based team simulation (MD-3019)
- BenchmarkRunner: Performance benchmarking for teams (MD-3019)

EPIC: MD-3015 - Autonomous Team Retrospective & Evaluation
EPIC: MD-3019 - Team Simulation & Benchmarking
"""

from .retrospective_engine import (
    RetrospectiveEngine,
    RetrospectiveResult,
    RetrospectiveReport,
    RetrospectiveConfig,
    RetrospectiveStatus,
    TeamMetrics,
    Timeframe,
    MetricValue,
    MetricCategory,
    PerformanceAssessment,
    Improvement,
    ActionItem,
    ActionItemStatus,
    create_retrospective_engine,
)

from .evaluator_persona import (
    EvaluatorPersona,
    EvaluatorConfig,
    EvaluationLevel,
    EvaluationCriteria,
    TeamScore,
    FeedbackReport,
    create_evaluator_persona,
)

from .process_improver import (
    ProcessImprover,
    ImproverConfig,
    ImprovementCategory,
    WorkflowAnalysis,
    Bottleneck,
    PriorityQuadrant,
    create_process_improver,
)

from .team_simulator import (
    TeamSimulator,
    SimulationResult,
    SimulationScenario,
    SimulationStatus,
    ScenarioType,
    run_simulation,
)

from .benchmark_runner import (
    BenchmarkRunner,
    BenchmarkResult,
    BenchmarkConfig,
    BenchmarkMetrics,
    MetricType,
    run_benchmark,
)

from .team_evolver import (
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

from .performance_optimizer import (
    PerformanceOptimizer,
    OptimizerConfig,
    OptimizationTarget,
    PerformanceMetric,
    PerformanceSnapshot,
    Recommendation,
    RecommendationPriority,
    AnalysisResult,
    OptimizationResult,
    get_default_optimizer,
    analyze_team,
    optimize_team,
)

__all__ = [
    # Engine
    "RetrospectiveEngine",
    "RetrospectiveResult",
    "RetrospectiveReport",
    "RetrospectiveConfig",
    "RetrospectiveStatus",
    "create_retrospective_engine",
    # Metrics
    "TeamMetrics",
    "Timeframe",
    "MetricValue",
    "MetricCategory",
    "PerformanceAssessment",
    "Improvement",
    "ActionItem",
    "ActionItemStatus",
    # Evaluator
    "EvaluatorPersona",
    "EvaluatorConfig",
    "EvaluationLevel",
    "EvaluationCriteria",
    "TeamScore",
    "FeedbackReport",
    "create_evaluator_persona",
    # Improver
    "ProcessImprover",
    "ImproverConfig",
    "ImprovementCategory",
    "WorkflowAnalysis",
    "Bottleneck",
    "PriorityQuadrant",
    "create_process_improver",
    # Simulator (MD-3019)
    "TeamSimulator",
    "SimulationResult",
    "SimulationScenario",
    "SimulationStatus",
    "ScenarioType",
    "run_simulation",
    # Benchmark (MD-3019)
    "BenchmarkRunner",
    "BenchmarkResult",
    "BenchmarkConfig",
    "BenchmarkMetrics",
    "MetricType",
    "run_benchmark",
    # Team Evolver (MD-3020)
    "TeamEvolver",
    "EvolverConfig",
    "EvolutionStrategy",
    "TeamConfiguration",
    "TeamRole",
    "EvolutionMetrics",
    "EvolutionResult",
    "get_default_evolver",
    "evolve_team",
    # Performance Optimizer (MD-3020)
    "PerformanceOptimizer",
    "OptimizerConfig",
    "OptimizationTarget",
    "PerformanceMetric",
    "PerformanceSnapshot",
    "Recommendation",
    "RecommendationPriority",
    "AnalysisResult",
    "OptimizationResult",
    "get_default_optimizer",
    "analyze_team",
    "optimize_team",
]
