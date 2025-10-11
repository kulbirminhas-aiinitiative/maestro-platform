#!/usr/bin/env python3
"""
Feature Discovery CLI Tool

Usage:
    python -m features.cli discover <data.csv> --target <column>
    python -m features.cli profile <data.csv>
    python -m features.cli correlate <data.csv>
"""

import click
import pandas as pd
from pathlib import Path
import json

from .discovery_engine import FeatureDiscoveryEngine
from .models.feature_schema import CorrelationMethod, ImportanceMethod


@click.group()
def cli():
    """Feature Discovery CLI - Analyze datasets and discover important features"""
    pass


@cli.command()
@click.argument('data_file', type=click.Path(exists=True))
@click.option('--target', '-t', help='Target variable name')
@click.option('--method', '-m',
              type=click.Choice(['random_forest', 'gradient_boosting', 'mutual_info']),
              default='random_forest',
              help='Feature importance method')
@click.option('--correlation', '-c',
              type=click.Choice(['pearson', 'spearman', 'kendall']),
              default='pearson',
              help='Correlation method')
@click.option('--output', '-o', type=click.Path(), help='Output JSON file')
@click.option('--classification/--regression', default=True, help='Task type')
def discover(data_file, target, method, correlation, output, classification):
    """
    Run complete feature discovery analysis

    Example:
        python -m features.cli discover data.csv --target price --classification
    """
    click.echo(f"🔍 Analyzing {data_file}...")

    # Load data
    df = pd.read_csv(data_file)
    click.echo(f"📊 Loaded {len(df)} rows, {len(df.columns)} columns")

    # Initialize engine
    engine = FeatureDiscoveryEngine()

    # Run discovery
    importance_method = ImportanceMethod(method)
    correlation_method = CorrelationMethod(correlation)

    report = engine.discover(
        df=df,
        target=target,
        dataset_name=Path(data_file).stem,
        importance_method=importance_method,
        correlation_method=correlation_method,
        is_classification=classification
    )

    # Display insights
    click.echo("\n" + "="*60)
    click.echo("📋 KEY INSIGHTS")
    click.echo("="*60)
    for insight in report.insights:
        click.echo(f"  {insight}")

    # Display top features
    if report.importance:
        click.echo("\n" + "="*60)
        click.echo(f"⭐ TOP 10 FEATURES ({report.importance.method.value})")
        click.echo("="*60)
        for imp in report.importance.importances[:10]:
            click.echo(f"  #{imp.rank:2d}. {imp.feature:30s} {imp.importance:.4f}")

    # Display recommendations
    if report.recommendations:
        click.echo("\n" + "="*60)
        click.echo("💡 TOP RECOMMENDATIONS")
        click.echo("="*60)
        for rec in report.recommendations[:10]:
            click.echo(f"  • {rec.feature:30s} (score: {rec.score:.3f})")
            click.echo(f"    {rec.reason}")

    # Save to file
    if output:
        output_path = Path(output)
        with open(output_path, 'w') as f:
            f.write(report.model_dump_json(indent=2))
        click.echo(f"\n✅ Report saved to {output_path}")


@cli.command()
@click.argument('data_file', type=click.Path(exists=True))
def profile(data_file):
    """
    Profile dataset statistics

    Example:
        python -m features.cli profile data.csv
    """
    click.echo(f"📊 Profiling {data_file}...")

    df = pd.read_csv(data_file)

    engine = FeatureDiscoveryEngine()
    profile_result = engine.profiler.profile(df, Path(data_file).stem)

    click.echo(f"\n📋 Dataset: {profile_result.dataset_name}")
    click.echo(f"Rows: {profile_result.num_rows:,}")
    click.echo(f"Features: {profile_result.num_features}")
    click.echo(f"Numerical: {len(profile_result.numerical_features)}")
    click.echo(f"Categorical: {len(profile_result.categorical_features)}")
    click.echo(f"Missing: {profile_result.null_percentage:.2f}%")

    click.echo("\n" + "="*80)
    click.echo("FEATURE STATISTICS")
    click.echo("="*80)

    for feat in profile_result.features:
        click.echo(f"\n{feat.name} ({feat.type.value})")
        click.echo(f"  Count: {feat.count:,} | Nulls: {feat.null_count} ({feat.null_percentage:.1f}%)")

        if feat.type.value == "numerical":
            click.echo(f"  Mean: {feat.mean:.2f} | Std: {feat.std:.2f}")
            click.echo(f"  Min: {feat.min:.2f} | Max: {feat.max:.2f}")
            click.echo(f"  Median: {feat.median:.2f} | Q25: {feat.q25:.2f} | Q75: {feat.q75:.2f}")
        elif feat.type.value == "categorical":
            click.echo(f"  Unique: {feat.unique_count}")
            click.echo(f"  Top: {feat.top_value} (n={feat.top_frequency})")


@cli.command()
@click.argument('data_file', type=click.Path(exists=True))
@click.option('--target', '-t', help='Target variable to focus on')
@click.option('--method', '-m',
              type=click.Choice(['pearson', 'spearman', 'kendall']),
              default='pearson')
@click.option('--threshold', default=0.5, help='Correlation threshold')
def correlate(data_file, target, method, threshold):
    """
    Analyze feature correlations

    Example:
        python -m features.cli correlate data.csv --target price
    """
    click.echo(f"🔗 Analyzing correlations in {data_file}...")

    df = pd.read_csv(data_file)

    engine = FeatureDiscoveryEngine(correlation_threshold=threshold)
    corr_matrix = engine.correlation_analyzer.analyze(
        df,
        dataset_name=Path(data_file).stem,
        target=target,
        method=CorrelationMethod(method)
    )

    click.echo(f"\n📊 Found {len(corr_matrix.high_correlations)} high correlations (>{threshold})")

    if target:
        target_corrs = engine.correlation_analyzer.get_target_correlations(
            corr_matrix, target, top_n=15
        )

        click.echo(f"\n⭐ TOP CORRELATIONS WITH '{target}'")
        click.echo("="*60)
        for pair in target_corrs:
            other = pair.feature2 if pair.feature1 == target else pair.feature1
            click.echo(f"  {other:30s} {pair.correlation:+.3f} ({pair.strength})")

    click.echo(f"\n🔗 HIGH CORRELATIONS (>{threshold})")
    click.echo("="*60)
    for pair in corr_matrix.high_correlations[:20]:
        click.echo(f"  {pair.feature1:20s} ↔ {pair.feature2:20s} {pair.correlation:+.3f}")


if __name__ == '__main__':
    cli()
