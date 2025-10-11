#!/usr/bin/env python3
"""
Model Performance Monitoring CLI

Usage:
    python -m monitoring.cli metrics record <model> <version> <metric_type> <value>
    python -m monitoring.cli metrics history <model> <version> --metric <type>
    python -m monitoring.cli alerts list
    python -m monitoring.cli alerts create-rule <model> <metric> --threshold <value>
    python -m monitoring.cli monitor <model> <version>
"""

import click
from datetime import datetime
from typing import Optional

from .services.metrics_collector import MetricsCollector
from .services.degradation_detector import DegradationDetector
from .services.alert_service import AlertService
from .models.metrics_models import MetricType
from .models.alert_models import AlertSeverity, AlertStatus


# Global instances (in production, these would be singletons or DI)
collector = MetricsCollector()
detector = DegradationDetector(collector)
alert_service = AlertService(detector)


@click.group()
def cli():
    """Model Performance Monitoring CLI"""
    pass


# ============================================================================
# METRICS COMMANDS
# ============================================================================

@cli.group()
def metrics():
    """Manage performance metrics"""
    pass


@metrics.command()
@click.argument('model_name')
@click.argument('model_version')
@click.argument('metric_type', type=click.Choice([m.value for m in MetricType]))
@click.argument('value', type=float)
@click.option('--dataset', help='Dataset name')
def record(model_name, model_version, metric_type, value, dataset):
    """
    Record a performance metric

    Example:
        python -m monitoring.cli metrics record my_model v1.0 accuracy 0.95
    """
    metric = collector.record_metric(
        model_name=model_name,
        model_version=model_version,
        metric_type=MetricType(metric_type),
        metric_value=value,
        dataset_name=dataset
    )

    click.echo(f"✅ Recorded {metric_type} = {value} for {model_name} v{model_version}")


@metrics.command()
@click.argument('model_name')
@click.argument('model_version')
@click.option('--metric', type=click.Choice([m.value for m in MetricType]), help='Filter by metric type')
@click.option('--hours', default=24, help='Hours to look back')
def history(model_name, model_version, metric, hours):
    """
    View metric history

    Example:
        python -m monitoring.cli metrics history my_model v1.0 --metric accuracy --hours 24
    """
    if metric:
        # Single metric history
        metrics_list = collector.get_metric_history(
            model_name=model_name,
            model_version=model_version,
            metric_type=MetricType(metric),
            hours=hours
        )

        click.echo(f"\n📊 {metric.upper()} History for {model_name} v{model_version}")
        click.echo(f"Last {hours} hours ({len(metrics_list)} data points)")
        click.echo("=" * 70)

        for m in metrics_list[:10]:  # Show last 10
            timestamp = m.timestamp.strftime("%Y-%m-%d %H:%M:%S")
            click.echo(f"  {timestamp}: {m.metric_value:.4f}")

        # Show summary
        summary = collector.get_metric_summary(
            model_name=model_name,
            model_version=model_version,
            metric_type=MetricType(metric),
            hours=hours
        )

        if summary:
            click.echo(f"\n📈 Summary:")
            click.echo(f"  Current: {summary.current_value:.4f}")
            click.echo(f"  Mean:    {summary.mean:.4f}")
            click.echo(f"  Median:  {summary.median:.4f}")
            click.echo(f"  Std:     {summary.std:.4f}")
            click.echo(f"  Min:     {summary.min:.4f}")
            click.echo(f"  Max:     {summary.max:.4f}")
            click.echo(f"  Trend:   {summary.trend}")

    else:
        # All metrics
        perf_history = collector.get_performance_history(
            model_name=model_name,
            model_version=model_version,
            hours=hours
        )

        click.echo(f"\n📊 Performance History: {model_name} v{model_version}")
        click.echo(f"Last {hours} hours | {perf_history.total_snapshots} snapshots")
        click.echo("=" * 70)
        click.echo(f"Overall Health: {perf_history.overall_health.upper()}")
        click.echo(f"Health Trend:   {perf_history.health_trend}")
        click.echo()

        for summary in perf_history.metric_summaries:
            trend_icon = "📈" if summary.trend == "improving" else "📉" if summary.trend == "degrading" else "➡️"
            click.echo(
                f"  {trend_icon} {summary.metric_type.value:15s} "
                f"Current: {summary.current_value:.4f}  "
                f"Mean: {summary.mean:.4f}  "
                f"Trend: {summary.trend}"
            )


# ============================================================================
# ALERT COMMANDS
# ============================================================================

@cli.group()
def alerts():
    """Manage alerts and alert rules"""
    pass


@alerts.command('create-rule')
@click.argument('model_name')
@click.argument('metric_type', type=click.Choice([m.value for m in MetricType]))
@click.option('--name', required=True, help='Rule name')
@click.option('--threshold', type=float, help='Threshold value')
@click.option('--operator', type=click.Choice(['gt', 'lt', 'gte', 'lte']), default='lt', help='Comparison operator')
@click.option('--degradation', type=float, help='Max degradation % (use instead of threshold)')
@click.option('--severity', type=click.Choice([s.value for s in AlertSeverity]), default='medium')
@click.option('--version', help='Specific model version (optional)')
def create_rule(model_name, metric_type, name, threshold, operator, degradation, severity, version):
    """
    Create an alert rule

    Example (threshold):
        python -m monitoring.cli alerts create-rule my_model accuracy --name "Low Accuracy" --threshold 0.90 --operator lt --severity high

    Example (degradation):
        python -m monitoring.cli alerts create-rule my_model accuracy --name "Accuracy Drop" --degradation 5 --severity high
    """
    if degradation:
        # Degradation-based rule
        rule = alert_service.create_degradation_rule(
            rule_name=name,
            model_name=model_name,
            metric_type=MetricType(metric_type),
            max_degradation_percentage=degradation,
            severity=AlertSeverity(severity),
            model_version=version
        )
        click.echo(f"✅ Created degradation rule '{name}' (ID: {rule.rule_id})")
        click.echo(f"   Alert when {metric_type} degrades > {degradation}%")

    elif threshold is not None:
        # Threshold-based rule
        rule = alert_service.create_rule(
            rule_name=name,
            model_name=model_name,
            metric_type=MetricType(metric_type),
            threshold_value=threshold,
            comparison_operator=operator,
            severity=AlertSeverity(severity),
            model_version=version
        )
        click.echo(f"✅ Created threshold rule '{name}' (ID: {rule.rule_id})")
        click.echo(f"   Alert when {metric_type} {operator} {threshold}")

    else:
        click.echo("❌ Must specify either --threshold or --degradation")


@alerts.command('list-rules')
@click.option('--model', help='Filter by model name')
def list_rules(model):
    """
    List alert rules

    Example:
        python -m monitoring.cli alerts list-rules --model my_model
    """
    rules = alert_service.list_rules(model_name=model)

    if not rules:
        click.echo("No alert rules found")
        return

    click.echo(f"\n🔔 Alert Rules ({len(rules)})")
    click.echo("=" * 70)

    for rule in rules:
        status = "✅" if rule.enabled else "❌"
        if rule.use_degradation:
            condition = f"degradation > {rule.max_degradation_percentage}%"
        else:
            condition = f"{rule.comparison_operator} {rule.threshold_value}"

        click.echo(f"\n{status} {rule.rule_name} (ID: {rule.rule_id})")
        click.echo(f"   Model: {rule.model_name} v{rule.model_version or 'all'}")
        click.echo(f"   Metric: {rule.metric_type.value}")
        click.echo(f"   Condition: {condition}")
        click.echo(f"   Severity: {rule.severity.value}")


@alerts.command('list')
@click.option('--model', help='Filter by model name')
@click.option('--status', type=click.Choice([s.value for s in AlertStatus]), help='Filter by status')
@click.option('--severity', type=click.Choice([s.value for s in AlertSeverity]), help='Filter by severity')
@click.option('--hours', default=24, help='Hours to look back')
def list_alerts(model, status, severity, hours):
    """
    List triggered alerts

    Example:
        python -m monitoring.cli alerts list --model my_model --status active
    """
    alerts_list = alert_service.list_alerts(
        model_name=model,
        status=AlertStatus(status) if status else None,
        severity=AlertSeverity(severity) if severity else None,
        hours=hours
    )

    if not alerts_list:
        click.echo(f"No alerts found in last {hours} hours")
        return

    click.echo(f"\n🚨 Alerts ({len(alerts_list)}) - Last {hours} hours")
    click.echo("=" * 70)

    for alert in alerts_list:
        severity_icon = {
            AlertSeverity.CRITICAL: "🔴",
            AlertSeverity.HIGH: "🟠",
            AlertSeverity.MEDIUM: "🟡",
            AlertSeverity.LOW: "🔵",
        }.get(alert.severity, "⚪")

        status_icon = {
            AlertStatus.ACTIVE: "🔥",
            AlertStatus.ACKNOWLEDGED: "👀",
            AlertStatus.RESOLVED: "✅",
        }.get(alert.status, "❓")

        timestamp = alert.triggered_at.strftime("%Y-%m-%d %H:%M:%S")

        click.echo(f"\n{severity_icon} {status_icon} {alert.rule_name}")
        click.echo(f"   ID: {alert.alert_id}")
        click.echo(f"   Model: {alert.model_name} v{alert.model_version}")
        click.echo(f"   Triggered: {timestamp}")
        click.echo(f"   {alert.message}")


@alerts.command()
@click.argument('alert_id')
@click.argument('user')
def acknowledge(alert_id, user):
    """
    Acknowledge an alert

    Example:
        python -m monitoring.cli alerts acknowledge alert_abc123 john@example.com
    """
    alert = alert_service.acknowledge_alert(alert_id, user)

    if alert:
        click.echo(f"✅ Acknowledged alert {alert_id}")
    else:
        click.echo(f"❌ Alert {alert_id} not found")


@alerts.command()
@click.argument('alert_id')
@click.argument('user')
@click.option('--notes', help='Resolution notes')
def resolve(alert_id, user, notes):
    """
    Resolve an alert

    Example:
        python -m monitoring.cli alerts resolve alert_abc123 john@example.com --notes "Fixed data pipeline"
    """
    alert = alert_service.resolve_alert(alert_id, user, notes)

    if alert:
        click.echo(f"✅ Resolved alert {alert_id}")
        if notes:
            click.echo(f"   Notes: {notes}")
    else:
        click.echo(f"❌ Alert {alert_id} not found")


# ============================================================================
# MONITORING COMMANDS
# ============================================================================

@cli.command()
@click.argument('model_name')
@click.argument('model_version')
@click.option('--hours', default=24, help='Hours to analyze')
def monitor(model_name, model_version, hours):
    """
    Monitor a model's performance and check for issues

    Example:
        python -m monitoring.cli monitor my_model v1.0
    """
    click.echo(f"\n🔍 Monitoring {model_name} v{model_version}")
    click.echo("=" * 70)

    # Get performance history
    history = collector.get_performance_history(
        model_name=model_name,
        model_version=model_version,
        hours=hours
    )

    click.echo(f"\n📊 Health Status: {history.overall_health.upper()}")
    click.echo(f"Trend: {history.health_trend}")
    click.echo(f"Snapshots: {history.total_snapshots} (last {hours}h)")

    # Check for degradation
    click.echo(f"\n🔍 Checking for Performance Degradation...")
    results = detector.check_all_metrics(
        model_name=model_name,
        model_version=model_version,
        baseline_window_hours=hours
    )

    degraded = [r for r in results if r.is_degraded]

    if degraded:
        click.echo(f"\n⚠️ Found {len(degraded)} degraded metrics:")
        for result in degraded:
            click.echo(f"\n  {result.metric_type.value}:")
            click.echo(f"    {result.severity.upper()}: {abs(result.percentage_change):.1f}% degradation")
            click.echo(f"    {result.baseline_value:.4f} → {result.current_value:.4f}")
    else:
        click.echo(f"\n✅ No degradation detected")

    # Evaluate alerts
    click.echo(f"\n🔔 Evaluating Alert Rules...")
    triggered_alerts = alert_service.evaluate_model(model_name, model_version)

    if triggered_alerts:
        click.echo(f"\n🚨 {len(triggered_alerts)} new alerts triggered:")
        for alert in triggered_alerts:
            click.echo(f"  - {alert.severity.value}: {alert.message}")
    else:
        click.echo(f"\n✅ No alerts triggered")

    # Alert summary
    summary = alert_service.get_alert_summary(model_name, model_version, hours=hours)

    if summary.active_count > 0 or summary.acknowledged_count > 0:
        click.echo(f"\n📋 Alert Summary:")
        click.echo(f"  Active: {summary.active_count}")
        click.echo(f"  Acknowledged: {summary.acknowledged_count}")
        click.echo(f"  Resolved: {summary.resolved_count}")

        if summary.critical_count > 0:
            click.echo(f"\n  🔴 Critical: {summary.critical_count}")
        if summary.high_count > 0:
            click.echo(f"  🟠 High: {summary.high_count}")


@cli.command()
@click.argument('model_name')
@click.argument('model_version')
@click.option('--metric', type=click.Choice([m.value for m in MetricType]), required=True)
def check(model_name, model_version, metric):
    """
    Check specific metric for degradation

    Example:
        python -m monitoring.cli check my_model v1.0 --metric accuracy
    """
    result = detector.check_degradation(
        model_name=model_name,
        model_version=model_version,
        metric_type=MetricType(metric)
    )

    click.echo(f"\n🔍 Degradation Check: {metric}")
    click.echo("=" * 70)
    click.echo(f"Model: {model_name} v{model_version}")
    click.echo(f"Current Value:  {result.current_value:.4f}")
    click.echo(f"Baseline Value: {result.baseline_value:.4f}")
    click.echo(f"Change:         {result.absolute_change:+.4f} ({result.percentage_change:+.1f}%)")
    click.echo()

    if result.is_degraded:
        click.echo(f"❌ DEGRADED ({result.severity.upper()})")
        click.echo(f"\n{result.recommendation}")
    else:
        click.echo(f"✅ No degradation detected")
        click.echo(f"\n{result.recommendation}")


if __name__ == '__main__':
    cli()
