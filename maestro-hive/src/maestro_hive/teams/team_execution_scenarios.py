#!/usr/bin/env python3
"""
Team Execution Scenarios - Comprehensive Scenario Matrix Generator

Generates all possible combinations of:
- Execution modes (single-go, phased, mixed, parallel-hybrid, dynamic)
- Blueprint strategies (static, dynamic-per-phase, adaptive, user-specified)
- Human intervention (none, after-each, critical-only, dynamic)
- Parallelism strategies (sequential, within-phase, cross-phase-pipeline, full-parallel)

Total possible scenarios: 5 × 4 × 4 × 4 = 320 combinations

This module provides:
- Complete scenario matrix generation
- Filtering to practical scenarios
- Scenario descriptions and recommendations
- Use case matching
"""

from enum import Enum
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
import json


# =============================================================================
# SCENARIO DIMENSIONS
# =============================================================================

class ExecutionMode(str, Enum):
    """Execution mode dimension"""
    SINGLE_GO = "single_go"                    # All phases continuous
    PHASED = "phased"                          # One phase at a time
    MIXED = "mixed"                            # Selective checkpoints
    PARALLEL_HYBRID = "parallel_hybrid"        # Parallel within phases
    DYNAMIC = "dynamic"                        # AI-decided mode


class BlueprintStrategy(str, Enum):
    """Blueprint selection strategy dimension"""
    STATIC = "static"                         # Same blueprint all phases
    DYNAMIC_PER_PHASE = "dynamic_per_phase"   # AI selects per phase
    ADAPTIVE = "adaptive"                      # Adapts based on quality
    USER_SPECIFIED = "user_specified"          # Manual selection


class HumanIntervention(str, Enum):
    """Human intervention pattern dimension"""
    NONE = "none"                              # Fully automated
    AFTER_EACH = "after_each"                  # Review every phase
    CRITICAL_ONLY = "critical_only"            # Review design + testing
    DYNAMIC = "dynamic"                        # AI decides when needed


class ParallelismStrategy(str, Enum):
    """Parallelism strategy dimension"""
    SEQUENTIAL_ONLY = "sequential_only"        # No parallel work
    WITHIN_PHASE = "within_phase"              # Parallel within phases
    CROSS_PHASE_PIPELINE = "cross_phase_pipeline"  # Pipeline parallelism
    FULL_PARALLEL = "full_parallel"            # Max parallelism


# =============================================================================
# SCENARIO DEFINITION
# =============================================================================

@dataclass
class ScenarioDefinition:
    """
    Complete scenario definition.

    Combines all four dimensions plus metadata.
    """
    id: str
    name: str

    # Four dimensions
    execution_mode: ExecutionMode
    blueprint_strategy: BlueprintStrategy
    human_intervention: HumanIntervention
    parallelism_strategy: ParallelismStrategy

    # Metadata
    description: str = ""
    use_cases: List[str] = field(default_factory=list)
    characteristics: Dict[str, int] = field(default_factory=dict)  # 1-5 ratings
    estimated_time_multiplier: float = 1.0  # vs baseline
    complexity: int = 3  # 1-5
    recommended: bool = False  # Is this a recommended scenario?

    # Configuration hints
    checkpoint_phases: Optional[List[str]] = None
    blueprint_map: Optional[Dict[str, str]] = None
    quality_thresholds: Optional[Dict[str, float]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "id": self.id,
            "name": self.name,
            "execution_mode": self.execution_mode.value,
            "blueprint_strategy": self.blueprint_strategy.value,
            "human_intervention": self.human_intervention.value,
            "parallelism_strategy": self.parallelism_strategy.value,
            "description": self.description,
            "use_cases": self.use_cases,
            "characteristics": self.characteristics,
            "estimated_time_multiplier": self.estimated_time_multiplier,
            "complexity": self.complexity,
            "recommended": self.recommended,
            "checkpoint_phases": self.checkpoint_phases,
            "blueprint_map": self.blueprint_map,
            "quality_thresholds": self.quality_thresholds
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ScenarioDefinition':
        """Create from dictionary"""
        return cls(
            id=data["id"],
            name=data["name"],
            execution_mode=ExecutionMode(data["execution_mode"]),
            blueprint_strategy=BlueprintStrategy(data["blueprint_strategy"]),
            human_intervention=HumanIntervention(data["human_intervention"]),
            parallelism_strategy=ParallelismStrategy(data["parallelism_strategy"]),
            description=data.get("description", ""),
            use_cases=data.get("use_cases", []),
            characteristics=data.get("characteristics", {}),
            estimated_time_multiplier=data.get("estimated_time_multiplier", 1.0),
            complexity=data.get("complexity", 3),
            recommended=data.get("recommended", False),
            checkpoint_phases=data.get("checkpoint_phases"),
            blueprint_map=data.get("blueprint_map"),
            quality_thresholds=data.get("quality_thresholds")
        )


# =============================================================================
# SCENARIO MATRIX GENERATOR
# =============================================================================

class ScenarioMatrixGenerator:
    """
    Generate comprehensive scenario matrix.

    Creates all possible combinations and filters to practical scenarios.
    """

    @staticmethod
    def generate_all_combinations() -> List[ScenarioDefinition]:
        """
        Generate all possible scenario combinations.

        Returns:
            List of 320 scenario definitions
        """
        scenarios = []
        scenario_id = 1

        for execution in ExecutionMode:
            for blueprint in BlueprintStrategy:
                for human in HumanIntervention:
                    for parallel in ParallelismStrategy:
                        # Create scenario
                        scenario = ScenarioDefinition(
                            id=f"S{scenario_id:03d}",
                            name=ScenarioMatrixGenerator._generate_name(
                                execution, blueprint, human, parallel
                            ),
                            execution_mode=execution,
                            blueprint_strategy=blueprint,
                            human_intervention=human,
                            parallelism_strategy=parallel
                        )

                        # Add metadata
                        ScenarioMatrixGenerator._add_metadata(scenario)

                        scenarios.append(scenario)
                        scenario_id += 1

        return scenarios

    @staticmethod
    def generate_practical_scenarios() -> List[ScenarioDefinition]:
        """
        Generate practical scenarios (filtered for real-world use).

        Returns:
            List of ~50 practical scenarios
        """
        all_scenarios = ScenarioMatrixGenerator.generate_all_combinations()

        # Filter to practical scenarios
        practical = []

        for scenario in all_scenarios:
            if ScenarioMatrixGenerator._is_practical(scenario):
                practical.append(scenario)

        return practical

    @staticmethod
    def generate_recommended_scenarios() -> List[ScenarioDefinition]:
        """
        Generate recommended scenarios for common use cases.

        Returns:
            List of 8-10 recommended scenarios
        """
        practical = ScenarioMatrixGenerator.generate_practical_scenarios()

        # Mark recommended scenarios
        recommended_ids = {
            "S001",  # Single-go + Static + None + Sequential
            "S005",  # Single-go + Static + None + Full-Parallel
            "S026",  # Phased + Dynamic-Per-Phase + After-Each + Within-Phase
            "S043",  # Mixed + Dynamic-Per-Phase + Critical-Only + Within-Phase
            "S085",  # Parallel-Hybrid + Dynamic-Per-Phase + None + Full-Parallel
            "S106",  # Dynamic + Adaptive + Dynamic + Full-Parallel
            "S021",  # Phased + Static + After-Each + Sequential
            "S087",  # Parallel-Hybrid + Adaptive + Critical-Only + Full-Parallel
        }

        recommended = []
        for scenario in practical:
            if scenario.id in recommended_ids:
                scenario.recommended = True
                recommended.append(scenario)

        return recommended

    @staticmethod
    def _generate_name(
        execution: ExecutionMode,
        blueprint: BlueprintStrategy,
        human: HumanIntervention,
        parallel: ParallelismStrategy
    ) -> str:
        """Generate human-readable scenario name"""
        parts = []

        # Execution mode
        if execution == ExecutionMode.SINGLE_GO:
            parts.append("Batch")
        elif execution == ExecutionMode.PHASED:
            parts.append("Phased")
        elif execution == ExecutionMode.MIXED:
            parts.append("Mixed")
        elif execution == ExecutionMode.PARALLEL_HYBRID:
            parts.append("Parallel-Hybrid")
        elif execution == ExecutionMode.DYNAMIC:
            parts.append("Dynamic")

        # Blueprint strategy
        if blueprint == BlueprintStrategy.DYNAMIC_PER_PHASE:
            parts.append("Smart-Blueprints")
        elif blueprint == BlueprintStrategy.ADAPTIVE:
            parts.append("Adaptive-Blueprints")

        # Human intervention
        if human == HumanIntervention.AFTER_EACH:
            parts.append("Full-Review")
        elif human == HumanIntervention.CRITICAL_ONLY:
            parts.append("Key-Reviews")

        # Parallelism
        if parallel == ParallelismStrategy.FULL_PARALLEL:
            parts.append("Max-Parallel")
        elif parallel == ParallelismStrategy.WITHIN_PHASE:
            parts.append("Phase-Parallel")

        return " ".join(parts) if parts else "Basic"

    @staticmethod
    def _add_metadata(scenario: ScenarioDefinition):
        """Add metadata to scenario"""
        # Generate description
        scenario.description = ScenarioMatrixGenerator._generate_description(scenario)

        # Add use cases
        scenario.use_cases = ScenarioMatrixGenerator._generate_use_cases(scenario)

        # Add characteristics (1-5 ratings)
        scenario.characteristics = {
            "speed": ScenarioMatrixGenerator._rate_speed(scenario),
            "control": ScenarioMatrixGenerator._rate_control(scenario),
            "recovery": ScenarioMatrixGenerator._rate_recovery(scenario),
            "quality": ScenarioMatrixGenerator._rate_quality(scenario),
            "automation": ScenarioMatrixGenerator._rate_automation(scenario)
        }

        # Estimate time multiplier
        scenario.estimated_time_multiplier = ScenarioMatrixGenerator._estimate_time(scenario)

        # Complexity
        scenario.complexity = ScenarioMatrixGenerator._rate_complexity(scenario)

        # Configuration hints
        scenario.checkpoint_phases = ScenarioMatrixGenerator._suggest_checkpoints(scenario)
        scenario.blueprint_map = ScenarioMatrixGenerator._suggest_blueprints(scenario)
        scenario.quality_thresholds = ScenarioMatrixGenerator._suggest_quality_thresholds(scenario)

    @staticmethod
    def _generate_description(scenario: ScenarioDefinition) -> str:
        """Generate scenario description"""
        parts = []

        # Execution
        if scenario.execution_mode == ExecutionMode.SINGLE_GO:
            parts.append("All SDLC phases execute continuously in one batch")
        elif scenario.execution_mode == ExecutionMode.PHASED:
            parts.append("Each SDLC phase executes independently with checkpoints")
        elif scenario.execution_mode == ExecutionMode.MIXED:
            parts.append("Selective checkpoints at critical phases")
        elif scenario.execution_mode == ExecutionMode.PARALLEL_HYBRID:
            parts.append("Sequential phases with parallel work within each")
        elif scenario.execution_mode == ExecutionMode.DYNAMIC:
            parts.append("AI decides execution strategy per phase")

        # Human intervention
        if scenario.human_intervention == HumanIntervention.AFTER_EACH:
            parts.append("with human review after every phase")
        elif scenario.human_intervention == HumanIntervention.CRITICAL_ONLY:
            parts.append("with human review at design and testing")

        # Parallelism
        if scenario.parallelism_strategy == ParallelismStrategy.FULL_PARALLEL:
            parts.append("Maximum parallelism enabled")

        return ". ".join(parts) + "."

    @staticmethod
    def _generate_use_cases(scenario: ScenarioDefinition) -> List[str]:
        """Generate use cases for scenario"""
        use_cases = []

        # Based on execution + human intervention
        if scenario.execution_mode == ExecutionMode.SINGLE_GO and scenario.human_intervention == HumanIntervention.NONE:
            use_cases.append("CI/CD pipelines")
            use_cases.append("Small automated projects (< 4 hours)")
            use_cases.append("Rapid prototyping")

        if scenario.execution_mode == ExecutionMode.PHASED and scenario.human_intervention == HumanIntervention.AFTER_EACH:
            use_cases.append("Large enterprise projects")
            use_cases.append("Learning/teaching scenarios")
            use_cases.append("High-stakes production systems")

        if scenario.execution_mode == ExecutionMode.MIXED and scenario.human_intervention == HumanIntervention.CRITICAL_ONLY:
            use_cases.append("Balanced speed + control projects")
            use_cases.append("Production workflows")
            use_cases.append("Medium-sized projects (4-8 hours)")

        if scenario.parallelism_strategy == ParallelismStrategy.FULL_PARALLEL:
            use_cases.append("Time-critical projects")
            use_cases.append("Complex full-stack applications")

        if scenario.blueprint_strategy == BlueprintStrategy.DYNAMIC_PER_PHASE:
            use_cases.append("Projects with varying complexity per phase")
            use_cases.append("AI-optimized workflows")

        return use_cases[:3]  # Limit to top 3

    @staticmethod
    def _rate_speed(scenario: ScenarioDefinition) -> int:
        """Rate speed (1-5, higher = faster)"""
        score = 3

        # Execution mode impact
        if scenario.execution_mode == ExecutionMode.SINGLE_GO:
            score += 2
        elif scenario.execution_mode == ExecutionMode.PHASED:
            score -= 1

        # Human intervention impact
        if scenario.human_intervention == HumanIntervention.NONE:
            score += 1
        elif scenario.human_intervention == HumanIntervention.AFTER_EACH:
            score -= 2

        # Parallelism impact
        if scenario.parallelism_strategy == ParallelismStrategy.FULL_PARALLEL:
            score += 1
        elif scenario.parallelism_strategy == ParallelismStrategy.SEQUENTIAL_ONLY:
            score -= 1

        return max(1, min(5, score))

    @staticmethod
    def _rate_control(scenario: ScenarioDefinition) -> int:
        """Rate human control (1-5, higher = more control)"""
        score = 3

        # Human intervention impact
        if scenario.human_intervention == HumanIntervention.AFTER_EACH:
            score += 2
        elif scenario.human_intervention == HumanIntervention.NONE:
            score -= 2

        # Execution mode impact
        if scenario.execution_mode == ExecutionMode.PHASED:
            score += 1

        return max(1, min(5, score))

    @staticmethod
    def _rate_recovery(scenario: ScenarioDefinition) -> int:
        """Rate recovery capability (1-5, higher = better recovery)"""
        score = 3

        # Execution mode impact
        if scenario.execution_mode == ExecutionMode.PHASED:
            score += 2
        elif scenario.execution_mode == ExecutionMode.SINGLE_GO:
            score -= 2

        return max(1, min(5, score))

    @staticmethod
    def _rate_quality(scenario: ScenarioDefinition) -> int:
        """Rate quality assurance (1-5, higher = better quality)"""
        score = 3

        # Human intervention impact
        if scenario.human_intervention == HumanIntervention.AFTER_EACH:
            score += 2
        elif scenario.human_intervention == HumanIntervention.NONE:
            score -= 1

        # Blueprint strategy impact
        if scenario.blueprint_strategy == BlueprintStrategy.ADAPTIVE:
            score += 1

        return max(1, min(5, score))

    @staticmethod
    def _rate_automation(scenario: ScenarioDefinition) -> int:
        """Rate automation level (1-5, higher = more automated)"""
        score = 3

        # Human intervention impact
        if scenario.human_intervention == HumanIntervention.NONE:
            score += 2
        elif scenario.human_intervention == HumanIntervention.AFTER_EACH:
            score -= 2

        # Execution mode impact
        if scenario.execution_mode == ExecutionMode.DYNAMIC:
            score += 1

        return max(1, min(5, score))

    @staticmethod
    def _estimate_time(scenario: ScenarioDefinition) -> float:
        """Estimate time multiplier vs baseline (1.0 = baseline)"""
        multiplier = 1.0

        # Execution mode impact
        if scenario.execution_mode == ExecutionMode.SINGLE_GO:
            multiplier *= 0.9
        elif scenario.execution_mode == ExecutionMode.PHASED:
            multiplier *= 1.1

        # Human intervention impact (assumes 30 min review per phase)
        if scenario.human_intervention == HumanIntervention.AFTER_EACH:
            multiplier *= 1.3
        elif scenario.human_intervention == HumanIntervention.CRITICAL_ONLY:
            multiplier *= 1.1

        # Parallelism impact
        if scenario.parallelism_strategy == ParallelismStrategy.FULL_PARALLEL:
            multiplier *= 0.7
        elif scenario.parallelism_strategy == ParallelismStrategy.SEQUENTIAL_ONLY:
            multiplier *= 1.2

        return round(multiplier, 2)

    @staticmethod
    def _rate_complexity(scenario: ScenarioDefinition) -> int:
        """Rate scenario complexity (1-5, higher = more complex)"""
        score = 3

        # Execution mode impact
        if scenario.execution_mode == ExecutionMode.DYNAMIC:
            score += 1

        # Blueprint strategy impact
        if scenario.blueprint_strategy == BlueprintStrategy.ADAPTIVE:
            score += 1

        # Parallelism impact
        if scenario.parallelism_strategy == ParallelismStrategy.CROSS_PHASE_PIPELINE:
            score += 1

        return max(1, min(5, score))

    @staticmethod
    def _suggest_checkpoints(scenario: ScenarioDefinition) -> Optional[List[str]]:
        """Suggest checkpoint phases"""
        if scenario.execution_mode == ExecutionMode.SINGLE_GO:
            return None

        if scenario.human_intervention == HumanIntervention.AFTER_EACH:
            return ["requirements", "design", "implementation", "testing"]

        if scenario.human_intervention == HumanIntervention.CRITICAL_ONLY:
            return ["design", "testing"]

        if scenario.execution_mode == ExecutionMode.MIXED:
            return ["design", "testing"]

        return ["testing"]  # Default

    @staticmethod
    def _suggest_blueprints(scenario: ScenarioDefinition) -> Optional[Dict[str, str]]:
        """Suggest blueprint map per phase"""
        if scenario.blueprint_strategy == BlueprintStrategy.STATIC:
            return None  # Use single blueprint for all

        if scenario.blueprint_strategy == BlueprintStrategy.USER_SPECIFIED:
            return {
                "requirements": "sequential-basic",
                "design": "collaborative-consensus",
                "implementation": "parallel-contract-first",
                "testing": "parallel-specialized",
                "deployment": "sequential-basic"
            }

        # For dynamic/adaptive, return hints
        return {
            "requirements": "sequential",
            "design": "collaborative",
            "implementation": "parallel",
            "testing": "parallel",
            "deployment": "sequential"
        }

    @staticmethod
    def _suggest_quality_thresholds(scenario: ScenarioDefinition) -> Dict[str, float]:
        """Suggest quality thresholds per phase"""
        if scenario.human_intervention == HumanIntervention.AFTER_EACH:
            # Higher thresholds with human review
            return {
                "requirements": 0.80,
                "design": 0.85,
                "implementation": 0.75,
                "testing": 0.90,
                "deployment": 0.95
            }
        else:
            # Standard thresholds
            return {
                "requirements": 0.75,
                "design": 0.80,
                "implementation": 0.70,
                "testing": 0.85,
                "deployment": 0.90
            }

    @staticmethod
    def _is_practical(scenario: ScenarioDefinition) -> bool:
        """Check if scenario is practical for real-world use"""
        # Filter out impractical combinations

        # Impractical: Dynamic execution with static blueprints
        if scenario.execution_mode == ExecutionMode.DYNAMIC and scenario.blueprint_strategy == BlueprintStrategy.STATIC:
            return False

        # Impractical: Single-go with after-each human review
        if scenario.execution_mode == ExecutionMode.SINGLE_GO and scenario.human_intervention == HumanIntervention.AFTER_EACH:
            return False

        # Impractical: Cross-phase pipeline without hybrid execution
        if scenario.parallelism_strategy == ParallelismStrategy.CROSS_PHASE_PIPELINE and scenario.execution_mode != ExecutionMode.PARALLEL_HYBRID:
            return False

        return True


# =============================================================================
# SCENARIO FILTERS AND SEARCH
# =============================================================================

class ScenarioFilter:
    """Filter scenarios based on criteria"""

    @staticmethod
    def by_use_case(scenarios: List[ScenarioDefinition], use_case: str) -> List[ScenarioDefinition]:
        """Filter scenarios by use case"""
        return [s for s in scenarios if use_case.lower() in " ".join(s.use_cases).lower()]

    @staticmethod
    def by_characteristics(
        scenarios: List[ScenarioDefinition],
        min_speed: Optional[int] = None,
        min_control: Optional[int] = None,
        min_quality: Optional[int] = None
    ) -> List[ScenarioDefinition]:
        """Filter by characteristic thresholds"""
        filtered = scenarios

        if min_speed is not None:
            filtered = [s for s in filtered if s.characteristics.get("speed", 0) >= min_speed]

        if min_control is not None:
            filtered = [s for s in filtered if s.characteristics.get("control", 0) >= min_control]

        if min_quality is not None:
            filtered = [s for s in filtered if s.characteristics.get("quality", 0) >= min_quality]

        return filtered

    @staticmethod
    def by_complexity(
        scenarios: List[ScenarioDefinition],
        max_complexity: int = 3
    ) -> List[ScenarioDefinition]:
        """Filter by maximum complexity"""
        return [s for s in scenarios if s.complexity <= max_complexity]


# =============================================================================
# SCENARIO EXPORTER
# =============================================================================

class ScenarioExporter:
    """Export scenarios to various formats"""

    @staticmethod
    def to_json(scenarios: List[ScenarioDefinition], filepath: str):
        """Export to JSON file"""
        data = [s.to_dict() for s in scenarios]
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)

    @staticmethod
    def to_markdown(scenarios: List[ScenarioDefinition], filepath: str):
        """Export to Markdown table"""
        with open(filepath, 'w') as f:
            f.write("# Team Execution Scenarios\n\n")
            f.write(f"Total scenarios: {len(scenarios)}\n\n")

            f.write("## Scenario Matrix\n\n")
            f.write("| ID | Name | Execution | Blueprint | Human | Parallel | Speed | Control | Complexity |\n")
            f.write("|----|----|---------|----------|-------|----------|-------|---------|------------|\n")

            for s in scenarios:
                f.write(f"| {s.id} | {s.name} | {s.execution_mode.value} | {s.blueprint_strategy.value} | {s.human_intervention.value} | {s.parallelism_strategy.value} | ")
                f.write(f"{'⚡' * s.characteristics.get('speed', 0)} | {'⭐' * s.characteristics.get('control', 0)} | {s.complexity}/5 |\n")

            # Add recommended scenarios section
            recommended = [s for s in scenarios if s.recommended]
            if recommended:
                f.write("\n## Recommended Scenarios\n\n")
                for s in recommended:
                    f.write(f"### {s.id}: {s.name}\n\n")
                    f.write(f"{s.description}\n\n")
                    f.write(f"**Use Cases:** {', '.join(s.use_cases)}\n\n")
                    f.write(f"**Characteristics:**\n")
                    for key, value in s.characteristics.items():
                        f.write(f"- {key.title()}: {'⭐' * value}\n")
                    f.write("\n")


# =============================================================================
# CLI AND EXAMPLE USAGE
# =============================================================================

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Team Execution Scenario Generator")
    parser.add_argument("--mode", choices=["all", "practical", "recommended"], default="recommended")
    parser.add_argument("--output", default="scenarios.json", help="Output file")
    parser.add_argument("--format", choices=["json", "markdown"], default="json")
    parser.add_argument("--filter-use-case", help="Filter by use case")

    args = parser.parse_args()

    # Generate scenarios
    if args.mode == "all":
        scenarios = ScenarioMatrixGenerator.generate_all_combinations()
    elif args.mode == "practical":
        scenarios = ScenarioMatrixGenerator.generate_practical_scenarios()
    else:
        scenarios = ScenarioMatrixGenerator.generate_recommended_scenarios()

    # Apply filters
    if args.filter_use_case:
        scenarios = ScenarioFilter.by_use_case(scenarios, args.filter_use_case)

    # Export
    if args.format == "json":
        ScenarioExporter.to_json(scenarios, args.output)
    else:
        ScenarioExporter.to_markdown(scenarios, args.output)

    print(f"✅ Generated {len(scenarios)} scenarios")
    print(f"   Output: {args.output}")

    # Print summary
    print(f"\n📊 Scenario Summary:")
    print(f"   Recommended: {sum(1 for s in scenarios if s.recommended)}")
    print(f"   Avg Complexity: {sum(s.complexity for s in scenarios) / len(scenarios):.1f}/5")
    print(f"   Avg Speed Rating: {sum(s.characteristics.get('speed', 0) for s in scenarios) / len(scenarios):.1f}/5")

    # Print top 3
    print(f"\n🌟 Top 3 Recommended Scenarios:")
    for s in [s for s in scenarios if s.recommended][:3]:
        print(f"\n   {s.id}: {s.name}")
        print(f"   {s.description}")
        print(f"   Use cases: {', '.join(s.use_cases[:2])}")
