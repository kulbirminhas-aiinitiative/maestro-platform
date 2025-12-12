#!/usr/bin/env python3
"""
Tests for Benchmark Runner

MD-3019: Team Simulation & Benchmarking
"""

import asyncio
import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from maestro_hive.teams.benchmark_runner import (
    BenchmarkRunner,
    BenchmarkResult,
    BenchmarkConfig,
    BenchmarkMetrics,
    MetricType,
    run_benchmark,
)
from maestro_hive.teams.team_simulator import (
    TeamSimulator,
    ScenarioType,
    SimulationScenario,
)


class TestBenchmarkConfig:
    """Tests for BenchmarkConfig dataclass."""

    def test_default_config(self):
        """Test default configuration values."""
        config = BenchmarkConfig()

        assert config.iterations == 100
        assert config.warmup_iterations == 10
        assert config.parallel_runs == 1
        assert config.timeout_per_iteration == 300
        assert config.collect_detailed_metrics is False
        assert config.output_format == "json"

    def test_custom_config(self):
        """Test custom configuration."""
        config = BenchmarkConfig(
            iterations=50,
            warmup_iterations=5,
            parallel_runs=4,
            collect_detailed_metrics=True,
        )

        assert config.iterations == 50
        assert config.warmup_iterations == 5
        assert config.parallel_runs == 4
        assert config.collect_detailed_metrics is True


class TestBenchmarkMetrics:
    """Tests for BenchmarkMetrics dataclass."""

    def test_metrics_to_dict(self):
        """Test converting metrics to dictionary."""
        metrics = BenchmarkMetrics(
            throughput=10.5,
            latency_p50=0.1,
            latency_p95=0.2,
            latency_p99=0.3,
            latency_mean=0.15,
            latency_std=0.05,
            quality_mean=0.85,
            quality_std=0.02,
            error_rate=0.01,
            total_operations=100,
            successful_operations=99,
            failed_operations=1,
        )

        data = metrics.to_dict()

        assert data["throughput"] == 10.5
        assert data["latency"]["p99"] == 0.3
        assert data["quality"]["mean"] == 0.85
        assert data["error_rate"] == 0.01
        assert data["operations"]["total"] == 100


class TestBenchmarkResult:
    """Tests for BenchmarkResult dataclass."""

    def test_result_to_dict(self):
        """Test converting result to dictionary."""
        config = BenchmarkConfig(iterations=10)
        metrics = BenchmarkMetrics(
            throughput=5.0,
            latency_p50=0.1,
            latency_p95=0.2,
            latency_p99=0.3,
            latency_mean=0.15,
            latency_std=0.05,
            quality_mean=0.9,
            quality_std=0.01,
            total_operations=10,
            successful_operations=10,
            failed_operations=0,
        )

        result = BenchmarkResult(
            benchmark_id="bench123",
            scenario_name="Test Scenario",
            config=config,
            metrics=metrics,
            start_time=datetime(2024, 1, 1, 10, 0, 0),
            end_time=datetime(2024, 1, 1, 10, 1, 0),
            duration_seconds=60.0,
        )

        data = result.to_dict()

        assert data["benchmark_id"] == "bench123"
        assert data["scenario_name"] == "Test Scenario"
        assert data["duration_seconds"] == 60.0
        assert "metrics" in data

    def test_result_to_json(self):
        """Test converting result to JSON."""
        config = BenchmarkConfig(iterations=10)
        metrics = BenchmarkMetrics()

        result = BenchmarkResult(
            benchmark_id="bench123",
            scenario_name="Test Scenario",
            config=config,
            metrics=metrics,
            start_time=datetime(2024, 1, 1, 10, 0, 0),
            end_time=datetime(2024, 1, 1, 10, 1, 0),
            duration_seconds=60.0,
        )

        json_str = result.to_json()

        assert '"benchmark_id": "bench123"' in json_str
        assert '"scenario_name": "Test Scenario"' in json_str


class TestBenchmarkRunner:
    """Tests for BenchmarkRunner class."""

    @pytest.fixture
    def runner(self, tmp_path):
        """Create a BenchmarkRunner instance."""
        return BenchmarkRunner(output_dir=str(tmp_path / "output"))

    def test_runner_initialization(self, runner):
        """Test runner initializes correctly."""
        assert runner.simulator is not None
        assert runner.output_dir.exists()
        assert len(runner._benchmark_history) == 0

    @pytest.mark.asyncio
    async def test_run_benchmark_simple(self, runner):
        """Test running a simple benchmark."""
        config = BenchmarkConfig(
            iterations=3,
            warmup_iterations=1,
        )

        result = await runner.run_predefined_benchmark(
            ScenarioType.SIMPLE_API, config
        )

        assert result.benchmark_id is not None
        assert result.scenario_name == "Simple API Development"
        assert result.duration_seconds > 0
        assert result.metrics.throughput > 0
        assert result.metrics.total_operations == 3

    @pytest.mark.asyncio
    async def test_run_benchmark_with_progress(self, runner):
        """Test benchmark with progress callback."""
        progress_updates = []

        def progress_callback(iteration, total):
            progress_updates.append((iteration, total))

        config = BenchmarkConfig(iterations=3, warmup_iterations=1)

        result = await runner.run_benchmark(
            TeamSimulator.PREDEFINED_SCENARIOS[ScenarioType.SIMPLE_API],
            config,
            progress_callback=progress_callback,
        )

        assert len(progress_updates) == 3
        assert progress_updates[-1] == (3, 3)

    @pytest.mark.asyncio
    async def test_run_benchmark_with_detailed_metrics(self, runner):
        """Test benchmark with detailed metrics collection."""
        config = BenchmarkConfig(
            iterations=3,
            warmup_iterations=1,
            collect_detailed_metrics=True,
        )

        result = await runner.run_predefined_benchmark(
            ScenarioType.SIMPLE_API, config
        )

        assert len(result.raw_latencies) == 3
        assert len(result.raw_qualities) == 3
        assert len(result.iteration_results) == 3

    @pytest.mark.asyncio
    async def test_benchmark_metrics_calculation(self, runner):
        """Test that metrics are calculated correctly."""
        config = BenchmarkConfig(iterations=5, warmup_iterations=1)

        result = await runner.run_predefined_benchmark(
            ScenarioType.SIMPLE_API, config
        )

        # Check latency metrics
        assert result.metrics.latency_p50 >= 0
        assert result.metrics.latency_p95 >= result.metrics.latency_p50
        assert result.metrics.latency_p99 >= result.metrics.latency_p95

        # Check quality metrics
        assert 0 <= result.metrics.quality_mean <= 1

        # Check operation counts
        assert result.metrics.successful_operations <= result.metrics.total_operations

    @pytest.mark.asyncio
    async def test_get_benchmark_history(self, runner):
        """Test getting benchmark history."""
        config = BenchmarkConfig(iterations=2, warmup_iterations=1)

        await runner.run_predefined_benchmark(ScenarioType.SIMPLE_API, config)
        await runner.run_predefined_benchmark(ScenarioType.SIMPLE_API, config)

        history = runner.get_benchmark_history()

        assert len(history) == 2
        assert all("benchmark_id" in h for h in history)

    @pytest.mark.asyncio
    async def test_compare_scenarios(self, runner):
        """Test comparing multiple scenarios."""
        config = BenchmarkConfig(iterations=2, warmup_iterations=1)

        scenarios = [
            TeamSimulator.PREDEFINED_SCENARIOS[ScenarioType.SIMPLE_API],
            TeamSimulator.PREDEFINED_SCENARIOS[ScenarioType.DATA_PIPELINE],
        ]

        results = await runner.compare_scenarios(scenarios, config)

        assert len(results) == 2
        assert "Simple API Development" in results
        assert "Data Pipeline Development" in results

    @pytest.mark.asyncio
    async def test_compare_configurations(self, runner):
        """Test comparing different configurations."""
        scenario = TeamSimulator.PREDEFINED_SCENARIOS[ScenarioType.SIMPLE_API]

        configs = [
            BenchmarkConfig(iterations=2, warmup_iterations=1),
            BenchmarkConfig(iterations=3, warmup_iterations=1),
        ]

        results = await runner.compare_configurations(scenario, configs)

        assert len(results) == 2
        assert results[0].metrics.total_operations == 2
        assert results[1].metrics.total_operations == 3

    @pytest.mark.asyncio
    async def test_generate_comparison_report(self, runner):
        """Test generating comparison report."""
        config = BenchmarkConfig(iterations=2, warmup_iterations=1)

        results = [
            await runner.run_predefined_benchmark(ScenarioType.SIMPLE_API, config),
            await runner.run_predefined_benchmark(ScenarioType.SIMPLE_API, config),
        ]

        report = runner.generate_comparison_report(results)

        assert "scenarios_compared" in report
        assert report["scenarios_compared"] == 2
        assert "rankings" in report
        assert "summary" in report

    def test_generate_comparison_report_empty(self, runner):
        """Test comparison report with no results."""
        report = runner.generate_comparison_report([])

        assert "error" in report

    @pytest.mark.asyncio
    async def test_benchmark_saves_results(self, runner, tmp_path):
        """Test that benchmark results are saved to file."""
        config = BenchmarkConfig(iterations=2, warmup_iterations=1)

        result = await runner.run_predefined_benchmark(
            ScenarioType.SIMPLE_API, config
        )

        # Check file was created
        files = list(runner.output_dir.glob("benchmark_*.json"))
        assert len(files) == 1


class TestMetricType:
    """Tests for MetricType enum."""

    def test_metric_types(self):
        """Test all metric types exist."""
        assert MetricType.THROUGHPUT.value == "throughput"
        assert MetricType.LATENCY.value == "latency"
        assert MetricType.QUALITY.value == "quality"
        assert MetricType.RESOURCE_USAGE.value == "resource_usage"
        assert MetricType.ERROR_RATE.value == "error_rate"


class TestConvenienceFunction:
    """Tests for run_benchmark convenience function."""

    @pytest.mark.asyncio
    async def test_run_benchmark_default(self):
        """Test run_benchmark with defaults."""
        result = await run_benchmark(iterations=2)

        assert result.benchmark_id is not None
        assert result.scenario_name == "Simple API Development"
        assert result.metrics.total_operations == 2

    @pytest.mark.asyncio
    async def test_run_benchmark_with_type(self):
        """Test run_benchmark with specific type."""
        result = await run_benchmark(
            scenario_type=ScenarioType.DATA_PIPELINE,
            iterations=2,
        )

        assert result.scenario_name == "Data Pipeline Development"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
