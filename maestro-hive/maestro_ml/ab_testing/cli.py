"""
A/B Testing CLI Tool
"""

import json
from typing import Optional

import click
from tabulate import tabulate

from .engines.experiment_engine import ExperimentEngine
from .engines.statistical_analyzer import StatisticalAnalyzer
from .models.experiment_models import (
    ExperimentMetric,
    ExperimentStatus,
    ExperimentVariant,
    MetricType,
    TrafficSplit,
)
from .routing.traffic_router import TrafficRouter

# Global engine (in production, use dependency injection)
engine = ExperimentEngine()
router = TrafficRouter()
analyzer = StatisticalAnalyzer()


@click.group()
def cli():
    """A/B Testing Framework CLI"""
    pass


@cli.command()
@click.option("--name", required=True, help="Experiment name")
@click.option("--description", required=True, help="Experiment description")
@click.option("--duration-days", type=int, help="Planned duration in days")
@click.option("--created-by", default="cli", help="Creator user ID")
def create(name: str, description: str, duration_days: Optional[int], created_by: str):
    """Create a new A/B test experiment"""
    click.echo(f"Creating experiment: {name}")
    click.echo("Enter variant configurations...")

    # Collect variants
    variants = []
    while True:
        variant_name = click.prompt("Variant name (or 'done' to finish)")
        if variant_name.lower() == "done":
            break

        variant_id = click.prompt(
            "Variant ID", default=variant_name.lower().replace(" ", "_")
        )
        model_name = click.prompt("Model name", default="")
        model_version = click.prompt("Model version", default="")
        traffic_pct = click.prompt("Traffic percentage", type=float)
        is_control = click.confirm(
            "Is this the control variant?", default=len(variants) == 0
        )

        variants.append(
            ExperimentVariant(
                variant_id=variant_id,
                name=variant_name,
                model_name=model_name if model_name else None,
                model_version=model_version if model_version else None,
                traffic_percentage=traffic_pct,
                is_control=is_control,
            )
        )

    if len(variants) < 2:
        click.echo("Error: Need at least 2 variants", err=True)
        return

    # Collect metrics
    click.echo("\nEnter metrics to track...")
    metrics = []
    while True:
        metric_name = click.prompt("Metric name (or 'done' to finish)")
        if metric_name.lower() == "done":
            break

        metric_type = click.prompt(
            "Metric type",
            type=click.Choice([t.value for t in MetricType]),
            default=MetricType.ACCURACY.value,
        )
        is_primary = click.confirm(
            "Is this the primary metric?", default=len(metrics) == 0
        )
        higher_is_better = click.confirm("Higher is better?", default=True)

        metrics.append(
            ExperimentMetric(
                metric_name=metric_name,
                metric_type=MetricType(metric_type),
                is_primary=is_primary,
                higher_is_better=higher_is_better,
            )
        )

    if len(metrics) == 0:
        click.echo("Error: Need at least 1 metric", err=True)
        return

    # Create traffic split
    variant_weights = {v.variant_id: v.traffic_percentage for v in variants}
    traffic_split = TrafficSplit(variant_weights=variant_weights)

    # Create experiment
    experiment = engine.create_experiment(
        name=name,
        description=description,
        variants=variants,
        metrics=metrics,
        traffic_split=traffic_split,
        duration_days=duration_days,
        created_by=created_by,
    )

    click.echo(f"\n✓ Created experiment: {experiment.experiment_id}")
    click.echo(f"  Name: {experiment.name}")
    click.echo(f"  Variants: {len(experiment.variants)}")
    click.echo(f"  Metrics: {len(experiment.metrics)}")
    click.echo(f"  Status: {experiment.status.value}")


@cli.command()
@click.argument("experiment_id")
def start(experiment_id: str):
    """Start an experiment"""
    try:
        experiment = engine.start_experiment(experiment_id)
        click.echo(f"✓ Started experiment: {experiment_id}")
        click.echo(f"  Status: {experiment.status.value}")
        click.echo(f"  Start time: {experiment.start_time}")
        if experiment.end_time:
            click.echo(f"  Planned end: {experiment.end_time}")
    except Exception as e:
        click.echo(f"Error: {e}", err=True)


@cli.command()
@click.argument("experiment_id")
@click.option("--reason", default="Manual stop", help="Reason for stopping")
def stop(experiment_id: str, reason: str):
    """Stop an experiment"""
    try:
        experiment = engine.stop_experiment(experiment_id, reason)
        click.echo(f"✓ Stopped experiment: {experiment_id}")
        click.echo(f"  Status: {experiment.status.value}")
        click.echo(f"  Reason: {reason}")
    except Exception as e:
        click.echo(f"Error: {e}", err=True)


@cli.command()
@click.argument("experiment_id")
def pause(experiment_id: str):
    """Pause an experiment"""
    try:
        experiment = engine.pause_experiment(experiment_id)
        click.echo(f"✓ Paused experiment: {experiment_id}")
    except Exception as e:
        click.echo(f"Error: {e}", err=True)


@cli.command()
@click.argument("experiment_id")
def resume(experiment_id: str):
    """Resume a paused experiment"""
    try:
        experiment = engine.resume_experiment(experiment_id)
        click.echo(f"✓ Resumed experiment: {experiment_id}")
    except Exception as e:
        click.echo(f"Error: {e}", err=True)


@cli.command()
@click.option(
    "--status",
    type=click.Choice([s.value for s in ExperimentStatus]),
    help="Filter by status",
)
@click.option("--created-by", help="Filter by creator")
def list(status: Optional[str], created_by: Optional[str]):
    """List all experiments"""
    status_enum = ExperimentStatus(status) if status else None
    experiments = engine.list_experiments(status=status_enum, created_by=created_by)

    if not experiments:
        click.echo("No experiments found")
        return

    # Format as table
    table_data = []
    for exp in experiments:
        table_data.append(
            [
                exp.experiment_id[:12],
                exp.name,
                exp.status.value,
                len(exp.variants),
                len(exp.metrics),
                exp.created_at.strftime("%Y-%m-%d %H:%M"),
                exp.created_by,
            ]
        )

    click.echo(
        tabulate(
            table_data,
            headers=["ID", "Name", "Status", "Variants", "Metrics", "Created", "By"],
            tablefmt="grid",
        )
    )


@cli.command()
@click.argument("experiment_id")
def status(experiment_id: str):
    """Get experiment status"""
    try:
        status_info = engine.get_experiment_status(experiment_id)

        click.echo(f"\nExperiment: {status_info['name']}")
        click.echo(f"ID: {status_info['experiment_id']}")
        click.echo(f"Status: {status_info['status'].value}")
        click.echo(f"Total samples: {status_info['total_samples']}")
        click.echo("\nVariant samples:")
        for variant_id, count in status_info["variant_samples"].items():
            click.echo(f"  {variant_id}: {count}")
        click.echo(f"\nTracking metrics: {', '.join(status_info['metrics'])}")

    except Exception as e:
        click.echo(f"Error: {e}", err=True)


@cli.command()
@click.argument("experiment_id")
@click.option(
    "--format", "output_format", type=click.Choice(["table", "json"]), default="table"
)
def analyze(experiment_id: str, output_format: str):
    """Analyze experiment results"""
    try:
        result = engine.analyze_experiment(experiment_id)

        if output_format == "json":
            click.echo(json.dumps(result.model_dump(), indent=2, default=str))
            return

        # Table format
        click.echo(f"\n{'='*80}")
        click.echo(f"Experiment Analysis: {result.experiment_name}")
        click.echo(f"{'='*80}")

        click.echo(f"\nExperiment ID: {result.experiment_id}")
        click.echo(f"Status: {result.status.value}")
        click.echo(f"Duration: {result.experiment_duration_hours:.1f} hours")
        click.echo(f"Total samples: {result.total_sample_size}")
        click.echo(f"Data quality: {result.data_quality_score:.2%}")

        # Variant metrics
        click.echo(f"\n{'Variant Metrics':^80}")
        click.echo("-" * 80)
        for vm in result.variant_metrics:
            click.echo(f"\nVariant: {vm.variant_id}")
            click.echo(f"  Sample size: {vm.sample_size}")
            for metric_name, value in vm.metrics.items():
                ci = vm.confidence_intervals.get(metric_name, (0, 0))
                click.echo(
                    f"  {metric_name}: {value:.4f} (95% CI: [{ci[0]:.4f}, {ci[1]:.4f}])"
                )

        # Comparisons
        click.echo(f"\n{'Statistical Comparisons':^80}")
        click.echo("-" * 80)
        comp_table = []
        for comp in result.comparisons:
            comp_table.append(
                [
                    comp.metric_name,
                    comp.control_variant_id,
                    comp.treatment_variant_id,
                    f"{comp.absolute_difference:+.4f}",
                    f"{comp.relative_difference_percent:+.2f}%",
                    f"{comp.p_value:.4f}",
                    "✓" if comp.is_significant else "✗",
                    f"{comp.statistical_power:.2f}"
                    if comp.statistical_power
                    else "N/A",
                    comp.recommendation,
                ]
            )

        click.echo(
            tabulate(
                comp_table,
                headers=[
                    "Metric",
                    "Control",
                    "Treatment",
                    "Abs Diff",
                    "Rel Diff",
                    "p-value",
                    "Sig?",
                    "Power",
                    "Rec",
                ],
                tablefmt="grid",
            )
        )

        # Winner
        click.echo(f"\n{'Results':^80}")
        click.echo("-" * 80)
        if result.winning_variant_id:
            click.echo(f"Winner: {result.winning_variant_id}")
            click.echo(f"Confidence: {result.confidence_in_winner:.2%}")
        else:
            click.echo("No clear winner")

        click.echo(f"\nRecommendation: {result.recommendation}")
        click.echo(f"Reason: {result.reason}")
        click.echo(f"\n{'='*80}\n")

    except Exception as e:
        click.echo(f"Error: {e}", err=True)


@cli.command()
@click.argument("experiment_id")
def check_early_stop(experiment_id: str):
    """Check if experiment should be stopped early"""
    try:
        should_stop, reason = engine.check_early_stopping(experiment_id)

        if should_stop:
            click.echo("✓ Recommend stopping experiment")
            click.echo(f"  Reason: {reason}")
        else:
            click.echo("Continue experiment")
            click.echo(f"  Reason: {reason}")

    except Exception as e:
        click.echo(f"Error: {e}", err=True)


@cli.command()
@click.option(
    "--baseline-rate", required=True, type=float, help="Baseline conversion rate (0-1)"
)
@click.option(
    "--mde", required=True, type=float, help="Minimum detectable effect (0-1)"
)
@click.option("--alpha", default=0.05, type=float, help="Significance level")
@click.option("--power", default=0.8, type=float, help="Statistical power")
def sample_size(baseline_rate: float, mde: float, alpha: float, power: float):
    """Calculate required sample size"""
    required = analyzer.calculate_required_sample_size(
        baseline_conversion_rate=baseline_rate,
        minimum_detectable_effect=mde,
        alpha=alpha,
        power=power,
    )

    click.echo(f"\nRequired sample size per variant: {required:,}")
    click.echo(f"Total sample size (2 variants): {required * 2:,}")
    click.echo("\nParameters:")
    click.echo(f"  Baseline rate: {baseline_rate:.1%}")
    click.echo(f"  Minimum detectable effect: {mde:.1%}")
    click.echo(f"  Significance level (α): {alpha}")
    click.echo(f"  Statistical power: {power}")


@cli.command()
@click.argument("experiment_id")
@click.argument("variant_id")
@click.argument("metric_name")
@click.argument("value", type=float)
def record(experiment_id: str, variant_id: str, metric_name: str, value: float):
    """Record a metric value"""
    try:
        engine.record_metric(experiment_id, variant_id, metric_name, value)
        click.echo(f"✓ Recorded {metric_name}={value} for variant {variant_id}")
    except Exception as e:
        click.echo(f"Error: {e}", err=True)


if __name__ == "__main__":
    cli()
