"""
AutoML CLI Tool

Command-line interface for running AutoML experiments.
"""

import sys
from pathlib import Path

import click
import pandas as pd

from .engines.automl_engine import AutoMLEngine
from .models.result_models import AutoMLConfig, TaskType


@click.group()
def cli():
    """AutoML CLI - Automated Machine Learning"""
    pass


@cli.command()
@click.option("--data", required=True, type=click.Path(exists=True), help="Path to training data CSV")
@click.option("--target", required=True, help="Target column name")
@click.option("--task", type=click.Choice(["classification", "regression"]), default="classification", help="ML task type")
@click.option("--metric", default="accuracy", help="Optimization metric")
@click.option("--time-budget", type=int, default=3600, help="Time budget in seconds")
@click.option("--max-trials", type=int, default=100, help="Maximum number of trials")
@click.option("--cv-folds", type=int, default=5, help="Number of CV folds")
@click.option("--ensemble/--no-ensemble", default=True, help="Build ensemble model")
@click.option("--output", type=click.Path(), help="Output path for best model")
@click.option("--experiment-name", help="MLflow experiment name")
def run(data, target, task, metric, time_budget, max_trials, cv_folds, ensemble, output, experiment_name):
    """
    Run AutoML on a dataset

    Example:
        automl run --data train.csv --target survived --task classification
    """
    click.echo(f"Loading data from {data}...")

    # Load data
    df = pd.read_csv(data)
    click.echo(f"Loaded {len(df)} rows, {len(df.columns)} columns")

    # Split features and target
    X = df.drop(columns=[target])
    y = df[target]

    click.echo(f"Target distribution:\n{y.value_counts()}\n")

    # Create config
    config = AutoMLConfig(
        task=TaskType(task),
        metric=metric,
        time_budget_seconds=time_budget,
        max_trials=max_trials,
        cv_folds=cv_folds,
        ensemble=ensemble,
        mlflow_tracking=True,
        mlflow_experiment=experiment_name or "automl-runs"
    )

    click.echo("Starting AutoML...")
    click.echo(f"Config: {config.dict()}\n")

    # Run AutoML
    engine = AutoMLEngine(config)

    try:
        result = engine.fit(X, y, experiment_name=experiment_name)

        # Print results
        click.echo("\n" + "=" * 80)
        click.echo("AutoML RESULTS")
        click.echo("=" * 80)

        click.echo(f"\nBest Model: {result.best_model_name}")
        click.echo(f"Best Score: {result.best_score:.4f}")
        click.echo(f"Best Params: {result.best_params}")

        click.echo(f"\nTotal Trials: {result.total_trials}")
        click.echo(f"Successful: {result.successful_trials}")
        click.echo(f"Failed: {result.failed_trials}")
        click.echo(f"Total Time: {result.total_time_seconds:.2f}s ({result.total_time_seconds / 60:.1f} min)")

        if result.ensemble_score:
            click.echo(f"\nEnsemble Score: {result.ensemble_score:.4f}")
            improvement = ((result.ensemble_score - result.best_score) / result.best_score) * 100
            click.echo(f"Improvement over best single model: {improvement:+.2f}%")

        # Leaderboard
        click.echo("\n" + "-" * 80)
        click.echo("LEADERBOARD (Top 10)")
        click.echo("-" * 80)
        leaderboard = result.get_leaderboard().head(10)
        click.echo(leaderboard.to_string(index=False))

        # Save model if requested
        if output:
            engine.save_model(output, use_ensemble=ensemble)
            click.echo(f"\nModel saved to: {output}")

        # MLflow info
        if result.mlflow_run_id:
            click.echo(f"\nMLflow Run ID: {result.mlflow_run_id}")
            click.echo(f"View at: http://localhost:5000/#/experiments/{result.mlflow_experiment_id}/runs/{result.mlflow_run_id}")

        click.echo("\n" + "=" * 80)

    except Exception as e:
        click.echo(f"\nError: {str(e)}", err=True)
        import traceback
        traceback.print_exc()
        sys.exit(1)


@cli.command()
@click.option("--data", required=True, type=click.Path(exists=True), help="Path to training data CSV")
@click.option("--target", required=True, help="Target column name")
@click.option("--model", required=True, help="Model type (e.g., random_forest, gradient_boosting)")
@click.option("--n-trials", type=int, default=50, help="Number of trials")
@click.option("--output", type=click.Path(), help="Output path for best model")
def tune(data, target, model, n_trials, output):
    """
    Hyperparameter tuning for a specific model

    Example:
        automl tune --data train.csv --target survived --model random_forest --n-trials 100
    """
    click.echo(f"Hyperparameter tuning for {model} not yet implemented")
    click.echo("This will be available in the Optuna integration")


@cli.command()
@click.option("--model", required=True, type=click.Path(exists=True), help="Path to saved model")
@click.option("--data", required=True, type=click.Path(exists=True), help="Path to test data CSV")
@click.option("--target", required=True, help="Target column name")
def evaluate(model, data, target):
    """
    Evaluate a saved model on test data

    Example:
        automl evaluate --model best_model.pkl --data test.csv --target survived
    """
    import joblib

    click.echo(f"Loading model from {model}...")
    loaded_model = joblib.load(model)

    click.echo(f"Loading test data from {data}...")
    df = pd.read_csv(data)

    X_test = df.drop(columns=[target])
    y_test = df[target]

    click.echo(f"Evaluating on {len(X_test)} samples...")

    score = loaded_model.score(X_test, y_test)
    predictions = loaded_model.predict(X_test)

    click.echo(f"\nTest Score: {score:.4f}")

    # Classification metrics
    try:
        from sklearn.metrics import classification_report
        click.echo("\nClassification Report:")
        click.echo(classification_report(y_test, predictions))
    except:
        pass


if __name__ == "__main__":
    cli()
