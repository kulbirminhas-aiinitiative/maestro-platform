#!/usr/bin/env python3
"""
Cost Tracking CLI

Usage:
    python -m cost_tracking.cli estimate <resource_type> <hours> [--quantity N]
    python -m cost_tracking.cli report <model> [--days 30] [--budget 1000]
    python -m cost_tracking.cli budget set <model> <amount>
    python -m cost_tracking.cli budget alerts
"""

import click
from datetime import datetime, timedelta

from .services.training_cost_calculator import TrainingCostCalculator
from .services.inference_cost_tracker import InferenceCostTracker
from .services.cost_reporter import CostReporter
from .models.cost_models import ResourceType
from .models.pricing_models import PricingCatalog


# Global instances
pricing = PricingCatalog.default_aws_pricing()
training_calc = TrainingCostCalculator(pricing)
inference_tracker = InferenceCostTracker(pricing)
reporter = CostReporter(training_calc, inference_tracker)


@click.group()
def cli():
    """Cost Tracking CLI - Training and inference cost management"""
    pass


@cli.command()
@click.argument('resource_type', type=click.Choice([r.value for r in ResourceType if 'gpu' in r.value or 'cpu' in r.value]))
@click.argument('hours', type=float)
@click.option('--quantity', default=1, help='Number of resources')
@click.option('--epochs', type=int, help='Number of training epochs')
@click.option('--samples', type=int, help='Number of training samples')
def estimate(resource_type, hours, quantity, epochs, samples):
    """
    Estimate training cost

    Example:
        python -m cost_tracking.cli estimate gpu_v100 8.0 --epochs 10 --samples 100000
    """
    estimate_result = training_calc.estimate_training_cost(
        resource_type=ResourceType(resource_type),
        estimated_hours=hours,
        quantity=quantity,
        num_epochs=epochs,
        num_samples=samples
    )

    click.echo(f"\n💰 Cost Estimate: Training on {resource_type}")
    click.echo("=" * 70)
    click.echo(f"Resource:     {quantity}x {resource_type}")
    click.echo(f"Duration:     {hours:.1f} hours")

    if epochs:
        click.echo(f"Epochs:       {epochs}")
        hours_per_epoch = hours / epochs
        click.echo(f"Per Epoch:    {hours_per_epoch:.2f} hours")

    if samples:
        click.echo(f"Samples:      {samples:,}")

    click.echo(f"\n📊 Estimated Costs:")
    click.echo(f"  Compute:    ${estimate_result.estimated_compute_cost:.2f}")
    click.echo(f"  Storage:    ${estimate_result.estimated_storage_cost:.2f}")
    click.echo(f"  Network:    ${estimate_result.estimated_network_cost:.2f}")
    click.echo(f"  ----------")
    click.echo(f"  TOTAL:      ${estimate_result.estimated_total_cost:.2f}")

    if epochs:
        cost_per_epoch = estimate_result.estimated_total_cost / epochs
        click.echo(f"\n💡 Cost per epoch: ${cost_per_epoch:.2f}")

    if samples:
        cost_per_sample = estimate_result.estimated_total_cost / samples
        click.echo(f"💡 Cost per sample: ${cost_per_sample:.6f}")

    click.echo(f"\n🎯 Confidence: {estimate_result.confidence_level}")


@cli.command()
@click.argument('model_name')
@click.option('--days', default=30, help='Days to include in report')
@click.option('--budget', type=float, help='Budget allocated')
def report(model_name, days, budget):
    """
    Generate cost report for a model

    Example:
        python -m cost_tracking.cli report fraud_detector --days 30 --budget 1000
    """
    end_time = datetime.utcnow()
    start_time = end_time - timedelta(days=days)

    summary = reporter.generate_model_summary(
        model_name=model_name,
        start_time=start_time,
        end_time=end_time,
        budget_allocated=budget
    )

    click.echo(f"\n📊 Cost Report: {model_name}")
    click.echo("=" * 70)
    click.echo(f"Period: {days} days ({start_time.date()} to {end_time.date()})")

    click.echo(f"\n💰 Cost Breakdown:")
    click.echo(f"  Training:   ${summary.total_training_cost:.2f}")
    click.echo(f"  Inference:  ${summary.total_inference_cost:.2f}")
    click.echo(f"  ----------")
    click.echo(f"  TOTAL:      ${summary.breakdown.total_cost:.2f}")

    click.echo(f"\n📈 Usage Statistics:")
    click.echo(f"  Training Jobs:      {summary.total_training_jobs}")
    click.echo(f"  Training Hours:     {summary.total_training_hours:.1f}h")
    click.echo(f"  Inference Requests: {summary.total_inference_requests:,}")
    click.echo(f"  Inference Hours:    {summary.total_inference_hours:.1f}h")

    click.echo(f"\n💡 Efficiency Metrics:")
    click.echo(f"  Avg cost/day:       ${summary.avg_cost_per_day:.2f}")
    if summary.avg_cost_per_training_job:
        click.echo(f"  Avg cost/job:       ${summary.avg_cost_per_training_job:.2f}")
    if summary.avg_cost_per_1k_requests:
        click.echo(f"  Avg cost/1K req:    ${summary.avg_cost_per_1k_requests:.4f}")

    if budget:
        click.echo(f"\n💵 Budget Tracking:")
        click.echo(f"  Allocated:    ${summary.budget_allocated:.2f}")
        click.echo(f"  Used:         ${summary.budget_used:.2f}")
        click.echo(f"  Remaining:    ${summary.budget_remaining:.2f}")
        click.echo(f"  Utilization:  {summary.budget_utilization_pct:.1f}%")

        if summary.budget_utilization_pct >= 90:
            click.echo(f"\n  ⚠️ WARNING: Budget {summary.budget_utilization_pct:.1f}% utilized!")
        elif summary.budget_utilization_pct >= 80:
            click.echo(f"\n  📊 Budget {summary.budget_utilization_pct:.1f}% utilized")

    if summary.cost_trend:
        trend_icon = "📈" if summary.cost_trend == "increasing" else "📉" if summary.cost_trend == "decreasing" else "➡️"
        click.echo(f"\n{trend_icon} Cost Trend: {summary.cost_trend}")


@cli.group()
def budget():
    """Budget management commands"""
    pass


@budget.command('set')
@click.argument('model_name')
@click.argument('amount', type=float)
def set_budget(model_name, amount):
    """
    Set budget for a model

    Example:
        python -m cost_tracking.cli budget set fraud_detector 1000.0
    """
    reporter.set_budget(model_name, amount)
    click.echo(f"✅ Set budget for {model_name}: ${amount:.2f}")


@budget.command('alerts')
@click.option('--model', help='Filter by model')
@click.option('--severity', type=click.Choice(['warning', 'critical']), help='Filter by severity')
def budget_alerts(model, severity):
    """
    List budget alerts

    Example:
        python -m cost_tracking.cli budget alerts --severity critical
    """
    alerts = reporter.get_budget_alerts(model_name=model, severity=severity)

    if not alerts:
        click.echo("No budget alerts found")
        return

    click.echo(f"\n🚨 Budget Alerts ({len(alerts)})")
    click.echo("=" * 70)

    for alert in alerts:
        severity_icon = "🔴" if alert.severity == "critical" else "🟡"
        click.echo(f"\n{severity_icon} {alert.severity.upper()}: {alert.model_name}")
        click.echo(f"   Budget: ${alert.budget_allocated:.2f}")
        click.echo(f"   Used:   ${alert.budget_used:.2f} ({alert.utilization_pct:.1f}%)")
        click.echo(f"   Remain: ${alert.budget_remaining:.2f}")
        click.echo(f"   {alert.message}")


@cli.command()
@click.option('--provider', type=click.Choice(['aws', 'gcp']), default='aws')
def pricing(provider):
    """
    Show pricing information

    Example:
        python -m cost_tracking.cli pricing --provider aws
    """
    if provider == 'aws':
        catalog = PricingCatalog.default_aws_pricing()
    else:
        catalog = PricingCatalog.default_gcp_pricing()

    click.echo(f"\n💵 {provider.upper()} Pricing Catalog")
    click.echo("=" * 70)
    click.echo(f"Effective: {catalog.effective_date}")
    click.echo(f"Currency: {catalog.currency}")

    click.echo(f"\n🖥️ GPU Compute:")
    for name, price in catalog.compute_pricing.items():
        if 'gpu' in name:
            click.echo(f"  {name:20s} ${price.price_per_hour:.3f}/hour  ({price.gpu_memory_gb}GB VRAM)")

    click.echo(f"\n💻 CPU Compute:")
    for name, price in catalog.compute_pricing.items():
        if 'cpu' in name:
            click.echo(f"  {name:20s} ${price.price_per_hour:.3f}/hour  ({price.vcpu} vCPU, {price.memory_gb}GB RAM)")

    click.echo(f"\n💾 Storage:")
    for name, price in catalog.storage_pricing.items():
        click.echo(f"  {name:20s} ${price.price_per_gb_month:.4f}/GB/month")


if __name__ == '__main__':
    cli()
