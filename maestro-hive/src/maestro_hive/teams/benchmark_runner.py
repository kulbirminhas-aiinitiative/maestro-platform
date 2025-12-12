#!/usr/bin/env python3
"""
Benchmark Runner - Performance Measurement for Team Simulations

MD-3019: Team Simulation & Benchmarking
Implements benchmarking capabilities for measuring team performance metrics.
"""

import asyncio
import json
import logging
import statistics
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from .team_simulator import TeamSimulator, ScenarioType, SimulationScenario

logger = logging.getLogger(__name__)


class MetricType(Enum):
    """Types of benchmark metrics."""

    THROUGHPUT = "throughput"  # Operations per second
    LATENCY = "latency"  # Response time in ms
    QUALITY = "quality"  # Quality score 0-1
    RESOURCE_USAGE = "resource_usage"  # CPU/Memory usage
    ERROR_RATE = "error_rate"  # Percentage of failures


@dataclass
class BenchmarkMetrics:
    """Collection of benchmark metrics."""

    throughput: float = 0.0
    latency_p50: float = 0.0
    latency_p95: float = 0.0
    latency_p99: float = 0.0
    latency_mean: float = 0.0
    latency_std: float = 0.0
    quality_mean: float = 0.0
    quality_std: float = 0.0
    error_rate: float = 0.0
    total_operations: int = 0
    successful_operations: int = 0
    failed_operations: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary."""
        return {
            "throughput": round(self.throughput, 3),
            "latency": {
                "p50": round(self.latency_p50, 3),
                "p95": round(self.latency_p95, 3),
                "p99": round(self.latency_p99, 3),
                "mean": round(self.latency_mean, 3),
                "std": round(self.latency_std, 3),
            },
            "quality": {
                "mean": round(self.quality_mean, 3),
                "std": round(self.quality_std, 3),
            },
            "error_rate": round(self.error_rate, 4),
            "operations": {
                "total": self.total_operations,
                "successful": self.successful_operations,
                "failed": self.failed_operations,
            },
        }


@dataclass
class BenchmarkConfig:
    """Configuration for benchmark runs."""

    iterations: int = 100
    warmup_iterations: int = 10
    parallel_runs: int = 1
    timeout_per_iteration: int = 300
    collect_detailed_metrics: bool = False
    output_format: str = "json"


@dataclass
class BenchmarkResult:
    """Result of a benchmark run."""

    benchmark_id: str
    scenario_name: str
    config: BenchmarkConfig
    metrics: BenchmarkMetrics
    start_time: datetime
    end_time: datetime
    duration_seconds: float
    raw_latencies: List[float] = field(default_factory=list)
    raw_qualities: List[float] = field(default_factory=list)
    iteration_results: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary."""
        return {
            "benchmark_id": self.benchmark_id,
            "scenario_name": self.scenario_name,
            "config": {
                "iterations": self.config.iterations,
                "warmup_iterations": self.config.warmup_iterations,
                "parallel_runs": self.config.parallel_runs,
            },
            "metrics": self.metrics.to_dict(),
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat(),
            "duration_seconds": round(self.duration_seconds, 2),
        }

    def to_json(self, include_raw: bool = False) -> str:
        """Convert result to JSON string."""
        data = self.to_dict()
        if include_raw:
            data["raw_latencies"] = self.raw_latencies
            data["raw_qualities"] = self.raw_qualities
        return json.dumps(data, indent=2)


class BenchmarkRunner:
    """
    Benchmark Runner for measuring team simulation performance.

    Provides capabilities for:
    - Running performance benchmarks on simulations
    - Collecting and analyzing metrics
    - Comparing configurations
    - Statistical analysis of results
    """

    def __init__(
        self,
        simulator: Optional[TeamSimulator] = None,
        output_dir: str = "./benchmark_output",
    ):
        """
        Initialize Benchmark Runner.

        Args:
            simulator: TeamSimulator instance (created if not provided)
            output_dir: Directory for benchmark output files
        """
        self.simulator = simulator or TeamSimulator()
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self._benchmark_history: List[BenchmarkResult] = []

    async def run_benchmark(
        self,
        scenario: SimulationScenario,
        config: Optional[BenchmarkConfig] = None,
        progress_callback: Optional[Callable[[int, int], None]] = None,
    ) -> BenchmarkResult:
        """
        Run a benchmark on a simulation scenario.

        Args:
            scenario: The scenario to benchmark
            config: Benchmark configuration (uses defaults if not provided)
            progress_callback: Optional callback for progress updates (iteration, total)

        Returns:
            BenchmarkResult with collected metrics
        """
        import uuid

        config = config or BenchmarkConfig()
        benchmark_id = str(uuid.uuid4())[:8]
        start_time = datetime.now()

        logger.info(
            f"Starting benchmark {benchmark_id}: {scenario.name}",
            extra={
                "benchmark_id": benchmark_id,
                "iterations": config.iterations,
            },
        )

        latencies: List[float] = []
        qualities: List[float] = []
        iteration_results: List[Dict[str, Any]] = []
        failed_count = 0

        total_iterations = config.warmup_iterations + config.iterations

        # Warmup phase
        logger.info(f"Running {config.warmup_iterations} warmup iterations")
        for i in range(config.warmup_iterations):
            try:
                await self.simulator.run_scenario(scenario)
            except Exception as e:
                logger.warning(f"Warmup iteration {i} failed: {e}")

        # Benchmark phase
        logger.info(f"Running {config.iterations} benchmark iterations")
        for i in range(config.iterations):
            iteration_start = time.time()

            try:
                if config.parallel_runs > 1:
                    # Run parallel simulations
                    tasks = [
                        self.simulator.run_scenario(scenario)
                        for _ in range(config.parallel_runs)
                    ]
                    results = await asyncio.gather(*tasks, return_exceptions=True)

                    for result in results:
                        if isinstance(result, Exception):
                            failed_count += 1
                        else:
                            latency = result.duration_seconds
                            quality = result.metrics.get("overall_quality", 0)
                            latencies.append(latency)
                            qualities.append(quality)
                else:
                    # Single simulation
                    result = await self.simulator.run_scenario(scenario)
                    latency = result.duration_seconds
                    quality = result.metrics.get("overall_quality", 0)
                    latencies.append(latency)
                    qualities.append(quality)

                    if config.collect_detailed_metrics:
                        iteration_results.append(
                            {
                                "iteration": i,
                                "latency": latency,
                                "quality": quality,
                                "metrics": result.metrics,
                            }
                        )

            except Exception as e:
                failed_count += 1
                logger.warning(f"Iteration {i} failed: {e}")

            # Progress callback
            if progress_callback:
                progress_callback(i + 1, config.iterations)

        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        # Calculate metrics
        metrics = self._calculate_metrics(
            latencies, qualities, failed_count, config.iterations, duration
        )

        result = BenchmarkResult(
            benchmark_id=benchmark_id,
            scenario_name=scenario.name,
            config=config,
            metrics=metrics,
            start_time=start_time,
            end_time=end_time,
            duration_seconds=duration,
            raw_latencies=latencies if config.collect_detailed_metrics else [],
            raw_qualities=qualities if config.collect_detailed_metrics else [],
            iteration_results=iteration_results,
        )

        self._benchmark_history.append(result)

        # Save results
        self._save_result(result)

        logger.info(
            f"Benchmark {benchmark_id} completed",
            extra={
                "throughput": metrics.throughput,
                "latency_p99": metrics.latency_p99,
                "error_rate": metrics.error_rate,
            },
        )

        return result

    def _calculate_metrics(
        self,
        latencies: List[float],
        qualities: List[float],
        failed_count: int,
        total_iterations: int,
        duration: float,
    ) -> BenchmarkMetrics:
        """Calculate benchmark metrics from raw data."""
        metrics = BenchmarkMetrics()

        if latencies:
            sorted_latencies = sorted(latencies)
            n = len(sorted_latencies)

            metrics.latency_mean = statistics.mean(sorted_latencies)
            metrics.latency_std = (
                statistics.stdev(sorted_latencies) if n > 1 else 0.0
            )
            metrics.latency_p50 = sorted_latencies[int(n * 0.50)]
            metrics.latency_p95 = sorted_latencies[int(n * 0.95)]
            metrics.latency_p99 = sorted_latencies[min(int(n * 0.99), n - 1)]

        if qualities:
            metrics.quality_mean = statistics.mean(qualities)
            metrics.quality_std = (
                statistics.stdev(qualities) if len(qualities) > 1 else 0.0
            )

        metrics.total_operations = total_iterations
        metrics.successful_operations = len(latencies)
        metrics.failed_operations = failed_count
        metrics.error_rate = failed_count / total_iterations if total_iterations > 0 else 0.0
        metrics.throughput = (
            len(latencies) / duration if duration > 0 else 0.0
        )

        return metrics

    def _save_result(self, result: BenchmarkResult):
        """Save benchmark result to file."""
        filename = f"benchmark_{result.benchmark_id}_{result.scenario_name.replace(' ', '_')}.json"
        filepath = self.output_dir / filename

        with open(filepath, "w") as f:
            f.write(result.to_json(include_raw=result.config.collect_detailed_metrics))

        logger.info(f"Benchmark results saved to {filepath}")

    async def run_predefined_benchmark(
        self,
        scenario_type: ScenarioType,
        config: Optional[BenchmarkConfig] = None,
    ) -> BenchmarkResult:
        """
        Run benchmark on a predefined scenario.

        Args:
            scenario_type: Type of predefined scenario
            config: Benchmark configuration

        Returns:
            BenchmarkResult
        """
        scenario = TeamSimulator.PREDEFINED_SCENARIOS.get(scenario_type)
        if not scenario:
            raise ValueError(f"Unknown scenario type: {scenario_type}")
        return await self.run_benchmark(scenario, config)

    async def compare_scenarios(
        self,
        scenarios: List[SimulationScenario],
        config: Optional[BenchmarkConfig] = None,
    ) -> Dict[str, BenchmarkResult]:
        """
        Run benchmarks on multiple scenarios for comparison.

        Args:
            scenarios: List of scenarios to compare
            config: Benchmark configuration (same for all)

        Returns:
            Dictionary mapping scenario names to results
        """
        results = {}
        for scenario in scenarios:
            result = await self.run_benchmark(scenario, config)
            results[scenario.name] = result
        return results

    async def compare_configurations(
        self,
        scenario: SimulationScenario,
        configs: List[BenchmarkConfig],
    ) -> List[BenchmarkResult]:
        """
        Compare different benchmark configurations on same scenario.

        Args:
            scenario: Scenario to benchmark
            configs: List of configurations to compare

        Returns:
            List of BenchmarkResults
        """
        results = []
        for config in configs:
            result = await self.run_benchmark(scenario, config)
            results.append(result)
        return results

    def get_benchmark_history(
        self, limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get history of benchmark runs."""
        return [result.to_dict() for result in self._benchmark_history[-limit:]]

    def generate_comparison_report(
        self, results: List[BenchmarkResult]
    ) -> Dict[str, Any]:
        """
        Generate a comparison report from multiple benchmark results.

        Args:
            results: List of benchmark results to compare

        Returns:
            Comparison report dictionary
        """
        if not results:
            return {"error": "No results to compare"}

        report = {
            "comparison_date": datetime.now().isoformat(),
            "scenarios_compared": len(results),
            "scenarios": [],
            "rankings": {},
        }

        # Collect data for each scenario
        for result in results:
            report["scenarios"].append(
                {
                    "name": result.scenario_name,
                    "benchmark_id": result.benchmark_id,
                    "throughput": result.metrics.throughput,
                    "latency_p99": result.metrics.latency_p99,
                    "quality_mean": result.metrics.quality_mean,
                    "error_rate": result.metrics.error_rate,
                }
            )

        # Calculate rankings
        sorted_by_throughput = sorted(
            results, key=lambda r: r.metrics.throughput, reverse=True
        )
        sorted_by_latency = sorted(
            results, key=lambda r: r.metrics.latency_p99
        )
        sorted_by_quality = sorted(
            results, key=lambda r: r.metrics.quality_mean, reverse=True
        )

        report["rankings"] = {
            "by_throughput": [r.scenario_name for r in sorted_by_throughput],
            "by_latency": [r.scenario_name for r in sorted_by_latency],
            "by_quality": [r.scenario_name for r in sorted_by_quality],
        }

        # Summary statistics
        throughputs = [r.metrics.throughput for r in results]
        latencies = [r.metrics.latency_p99 for r in results]
        qualities = [r.metrics.quality_mean for r in results]

        report["summary"] = {
            "throughput": {
                "min": min(throughputs),
                "max": max(throughputs),
                "mean": statistics.mean(throughputs),
            },
            "latency_p99": {
                "min": min(latencies),
                "max": max(latencies),
                "mean": statistics.mean(latencies),
            },
            "quality": {
                "min": min(qualities),
                "max": max(qualities),
                "mean": statistics.mean(qualities),
            },
        }

        return report


# Convenience function for running benchmarks
async def run_benchmark(
    scenario_type: ScenarioType = ScenarioType.SIMPLE_API,
    iterations: int = 10,
) -> BenchmarkResult:
    """
    Convenience function to run a benchmark.

    Args:
        scenario_type: Type of scenario to benchmark
        iterations: Number of benchmark iterations

    Returns:
        BenchmarkResult
    """
    runner = BenchmarkRunner()
    config = BenchmarkConfig(iterations=iterations, warmup_iterations=2)
    return await runner.run_predefined_benchmark(scenario_type, config)


if __name__ == "__main__":
    # Demo run
    async def demo():
        runner = BenchmarkRunner()

        print("Running benchmark on Simple API scenario...")
        config = BenchmarkConfig(
            iterations=5,
            warmup_iterations=1,
            collect_detailed_metrics=True,
        )

        result = await runner.run_predefined_benchmark(
            ScenarioType.SIMPLE_API, config
        )

        print(f"\nBenchmark ID: {result.benchmark_id}")
        print(f"Duration: {result.duration_seconds:.2f}s")
        print(f"Throughput: {result.metrics.throughput:.3f} ops/s")
        print(f"Latency P99: {result.metrics.latency_p99:.3f}s")
        print(f"Quality Mean: {result.metrics.quality_mean:.1%}")
        print(f"Error Rate: {result.metrics.error_rate:.1%}")

    asyncio.run(demo())
