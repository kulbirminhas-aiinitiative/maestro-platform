#!/usr/bin/env python3
"""
Data Profiling CLI Tool

Usage:
    python -m profiling.cli profile <data.csv>
    python -m profiling.cli drift <baseline.csv> <current.csv>
    python -m profiling.cli quality <data.csv>
"""

import click
import pandas as pd
from pathlib import Path
import json

from .profiler_engine import DataProfiler
from .metrics.quality_metrics import QualityMetricsCalculator
from .drift.drift_detector import DriftDetector


@click.group()
def cli():
    """Data Profiling CLI - Quality metrics and drift detection"""
    pass


@cli.command()
@click.argument('data_file', type=click.Path(exists=True))
@click.option('--baseline', '-b', type=click.Path(exists=True), help='Baseline dataset for drift detection')
@click.option('--output', '-o', type=click.Path(), help='Output JSON file')
def profile(data_file, baseline, output):
    """
    Run complete data profiling (quality + drift)

    Example:
        python -m profiling.cli profile current.csv --baseline baseline.csv
    """
    click.echo(f"📊 Profiling {data_file}...")

    # Load data
    df = pd.read_csv(data_file)
    baseline_df = pd.read_csv(baseline) if baseline else None

    # Run profiling
    profiler = DataProfiler()
    report = profiler.profile(
        df,
        dataset_name=Path(data_file).stem,
        baseline_df=baseline_df
    )

    # Display results
    click.echo("\n" + "="*70)
    click.echo("📋 DATA QUALITY REPORT")
    click.echo("="*70)

    qr = report.quality_report
    click.echo(f"\nDataset: {qr.dataset_name}")
    click.echo(f"Overall Health: {report.overall_health.upper()}")
    click.echo(f"Overall Score: {qr.overall_score:.1f}%")
    click.echo(f"\nDimension Scores:")
    click.echo(f"  Completeness: {qr.completeness_score:.1f}%")
    click.echo(f"  Validity:     {qr.validity_score:.1f}%")
    click.echo(f"  Consistency:  {qr.consistency_score:.1f}%")
    click.echo(f"  Uniqueness:   {qr.uniqueness_score:.1f}%")

    click.echo(f"\nDataset Size:")
    click.echo(f"  Rows: {qr.total_rows:,}")
    click.echo(f"  Columns: {qr.total_columns}")
    click.echo(f"  Missing: {qr.missing_percentage:.2f}%")

    if qr.critical_issues:
        click.echo(f"\n🚨 CRITICAL ISSUES ({len(qr.critical_issues)})")
        for issue in qr.critical_issues[:5]:
            click.echo(f"  • {issue.column}: {issue.issue}")

    if qr.recommendations:
        click.echo(f"\n💡 RECOMMENDATIONS")
        for rec in qr.recommendations:
            click.echo(f"  {rec}")

    # Drift results
    if report.drift_report:
        click.echo("\n" + "="*70)
        click.echo("🔍 DRIFT DETECTION REPORT")
        click.echo("="*70)

        dr = report.drift_report
        click.echo(f"\nDrift Detected: {'YES' if dr.drift_detected else 'NO'}")
        click.echo(f"Drifted Features: {dr.drift_features_count}/{dr.total_features_analyzed} ({dr.drift_percentage:.1f}%)")
        click.echo(f"Retraining Recommended: {'YES' if dr.retraining_recommended else 'NO'}")

        if dr.severe_drift_features:
            click.echo(f"\n🚨 SEVERE DRIFT:")
            for feat in dr.severe_drift_features:
                click.echo(f"  • {feat}")

        if dr.high_drift_features:
            click.echo(f"\n⚠️ HIGH DRIFT:")
            for feat in dr.high_drift_features[:5]:
                click.echo(f"  • {feat}")

        if dr.recommendations:
            click.echo(f"\n💡 DRIFT RECOMMENDATIONS")
            for rec in dr.recommendations:
                click.echo(f"  {rec}")

    # Priority actions
    if report.action_required:
        click.echo("\n" + "="*70)
        click.echo("⚡ PRIORITY ACTIONS REQUIRED")
        click.echo("="*70)
        for action in report.priority_actions:
            click.echo(f"  {action}")

    # Save to file
    if output:
        output_path = Path(output)
        with open(output_path, 'w') as f:
            f.write(report.model_dump_json(indent=2))
        click.echo(f"\n✅ Report saved to {output_path}")


@cli.command()
@click.argument('data_file', type=click.Path(exists=True))
def quality(data_file):
    """
    Run data quality analysis only

    Example:
        python -m profiling.cli quality data.csv
    """
    click.echo(f"📊 Analyzing data quality for {data_file}...")

    df = pd.read_csv(data_file)

    calculator = QualityMetricsCalculator()
    report = calculator.calculate(df, Path(data_file).stem)

    click.echo(f"\n📋 Quality Score: {report.overall_score:.1f}%")
    click.echo(f"Completeness: {report.completeness_score:.1f}%")
    click.echo(f"Validity: {report.validity_score:.1f}%")
    click.echo(f"Consistency: {report.consistency_score:.1f}%")

    click.echo(f"\n📊 Per-Column Metrics:")
    for metrics in report.column_metrics:
        status = "✅" if metrics.completeness_score > 95 else "⚠️"
        click.echo(f"  {status} {metrics.column_name:30s} Complete: {metrics.completeness_score:.1f}%  Unique: {metrics.unique_count}")


@cli.command()
@click.argument('baseline_file', type=click.Path(exists=True))
@click.argument('current_file', type=click.Path(exists=True))
@click.option('--threshold', default=0.05, help='Significance threshold')
def drift(baseline_file, current_file, threshold):
    """
    Detect data drift between baseline and current datasets

    Example:
        python -m profiling.cli drift baseline.csv current.csv
    """
    click.echo(f"🔍 Detecting drift between {baseline_file} and {current_file}...")

    baseline_df = pd.read_csv(baseline_file)
    current_df = pd.read_csv(current_file)

    detector = DriftDetector(significance_level=threshold)
    report = detector.detect(
        baseline_df,
        current_df,
        dataset_name=Path(current_file).stem
    )

    click.echo(f"\n📊 Drift Detection Results")
    click.echo(f"Drift Detected: {report.drift_detected}")
    click.echo(f"Drifted Features: {report.drift_features_count}/{report.total_features_analyzed}")
    click.echo(f"Drift Percentage: {report.drift_percentage:.1f}%")

    click.echo(f"\n🔍 Feature-Level Drift:")
    for fd in report.feature_drifts:
        if fd.drift_detected:
            icon = "🚨" if fd.drift_severity.value in ["severe", "high"] else "⚠️"
            click.echo(f"  {icon} {fd.feature_name:30s} {fd.drift_severity.value:10s} (score: {fd.drift_score:.3f}, p={fd.p_value:.4f})")

    if report.retraining_recommended:
        click.echo(f"\n⚡ MODEL RETRAINING RECOMMENDED!")


if __name__ == '__main__':
    cli()
