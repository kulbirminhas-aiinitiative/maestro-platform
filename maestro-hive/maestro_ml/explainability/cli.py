"""
Model Explainability CLI Tool
"""

import json
from pathlib import Path
from typing import Optional

import click
import joblib
import numpy as np
import pandas as pd

from .explainers.feature_importance import FeatureImportanceAnalyzer
from .explainers.lime_explainer import LIMEExplainer
from .explainers.shap_explainer import SHAPExplainer
from .models.explanation_models import ModelType


@click.group()
def cli():
    """Model Explainability CLI"""
    pass


@cli.command()
@click.option(
    "--model-path",
    required=True,
    type=click.Path(exists=True),
    help="Path to saved model",
)
@click.option(
    "--data-path",
    required=True,
    type=click.Path(exists=True),
    help="Path to data (CSV)",
)
@click.option(
    "--model-type", type=click.Choice([t.value for t in ModelType]), default="black_box"
)
@click.option("--output", type=click.Path(), help="Output path for explanation plot")
@click.option(
    "--method",
    type=click.Choice(["shap", "lime", "feature_importance"]),
    default="shap",
)
def explain_global(
    model_path: str, data_path: str, model_type: str, output: Optional[str], method: str
):
    """Generate global model explanation"""
    click.echo(f"Loading model from {model_path}...")
    model = joblib.load(model_path)

    click.echo(f"Loading data from {data_path}...")
    df = pd.read_csv(data_path)

    # Assume last column is target
    X = df.iloc[:, :-1]
    y = df.iloc[:, -1]

    feature_names = X.columns.tolist()

    if method == "shap":
        click.echo("Generating SHAP explanation...")
        explainer = SHAPExplainer(
            model=model, model_type=ModelType(model_type), feature_names=feature_names
        )
        explainer.fit(X.values)

        # Get global explanation
        global_exp = explainer.explain_global(X.values, num_samples=min(1000, len(X)))

        # Print top features
        click.echo("\n=== Top 10 Features (SHAP) ===")
        for fi in global_exp.feature_importances[:10]:
            click.echo(
                f"{fi.rank}. {fi.feature_name}: {fi.importance:.4f} (±{fi.std:.4f})"
            )

        # Save plot
        if output:
            explainer.plot_summary(X.values, save_path=output)
            click.echo(f"\nSaved SHAP summary plot to {output}")

    elif method == "lime":
        click.echo("LIME provides local explanations only. Use explain-local command.")

    elif method == "feature_importance":
        click.echo("Calculating feature importance...")
        analyzer = FeatureImportanceAnalyzer(
            model=model, model_type=ModelType(model_type), feature_names=feature_names
        )

        # Try intrinsic first
        global_exp = analyzer.get_intrinsic_importance()

        if global_exp is None:
            click.echo(
                "Model doesn't have intrinsic importance. Using permutation importance..."
            )
            global_exp = analyzer.get_permutation_importance(X.values, y.values)

        # Print top features
        click.echo("\n=== Top 10 Features ===")
        for fi in global_exp.feature_importances[:10]:
            click.echo(f"{fi.rank}. {fi.feature_name}: {fi.importance:.4f}")

        # Save plot
        if output:
            analyzer.plot_comparison(X.values, y.values, save_path=output)
            click.echo(f"\nSaved feature importance plot to {output}")


@cli.command()
@click.option(
    "--model-path",
    required=True,
    type=click.Path(exists=True),
    help="Path to saved model",
)
@click.option(
    "--train-data-path",
    required=True,
    type=click.Path(exists=True),
    help="Path to training data (CSV)",
)
@click.option(
    "--instance-path",
    required=True,
    type=click.Path(exists=True),
    help="Path to instance to explain (CSV)",
)
@click.option(
    "--model-type", type=click.Choice([t.value for t in ModelType]), default="black_box"
)
@click.option("--output", type=click.Path(), help="Output path for explanation plot")
@click.option("--method", type=click.Choice(["shap", "lime"]), default="shap")
@click.option("--top-k", type=int, default=5, help="Number of top features to show")
def explain_local(
    model_path: str,
    train_data_path: str,
    instance_path: str,
    model_type: str,
    output: Optional[str],
    method: str,
    top_k: int,
):
    """Generate local explanation for a single prediction"""
    click.echo(f"Loading model from {model_path}...")
    model = joblib.load(model_path)

    click.echo(f"Loading training data from {train_data_path}...")
    train_df = pd.read_csv(train_data_path)
    X_train = train_df.iloc[:, :-1]
    feature_names = X_train.columns.tolist()

    click.echo(f"Loading instance from {instance_path}...")
    instance_df = pd.read_csv(instance_path)
    instance = (
        instance_df.iloc[0, :-1]
        if instance_df.shape[1] == X_train.shape[1] + 1
        else instance_df.iloc[0]
    )

    if method == "shap":
        click.echo("Generating SHAP explanation...")
        explainer = SHAPExplainer(
            model=model, model_type=ModelType(model_type), feature_names=feature_names
        )
        explainer.fit(X_train.values)

        local_exp = explainer.explain_local(instance.values, top_k=top_k)

        # Print results
        click.echo("\n=== SHAP Local Explanation ===")
        click.echo(f"Prediction: {local_exp.prediction:.4f}")
        click.echo(f"Expected value (baseline): {local_exp.expected_value:.4f}")

        click.echo(f"\nTop {top_k} Positive Features:")
        for feature, contribution in local_exp.top_positive_features:
            value = local_exp.feature_values.get(feature, "N/A")
            click.echo(f"  {feature} = {value}: +{contribution:.4f}")

        click.echo(f"\nTop {top_k} Negative Features:")
        for feature, contribution in local_exp.top_negative_features:
            value = local_exp.feature_values.get(feature, "N/A")
            click.echo(f"  {feature} = {value}: {contribution:.4f}")

        # Save plot
        if output:
            explainer.plot_waterfall(instance.values, save_path=output)
            click.echo(f"\nSaved SHAP waterfall plot to {output}")

    elif method == "lime":
        click.echo("Generating LIME explanation...")
        explainer = LIMEExplainer(
            predict_fn=model.predict,
            training_data=X_train.values,
            feature_names=feature_names,
            mode="classification" if hasattr(model, "predict_proba") else "regression",
        )

        local_exp = explainer.explain_local(instance.values, top_k=top_k)

        # Print results
        click.echo("\n=== LIME Local Explanation ===")
        click.echo(f"Prediction: {local_exp.prediction:.4f}")
        click.echo(f"Intercept: {local_exp.expected_value:.4f}")

        click.echo(f"\nTop {top_k} Positive Features:")
        for feature, contribution in local_exp.top_positive_features:
            value = local_exp.feature_values.get(feature, "N/A")
            click.echo(f"  {feature} = {value}: +{contribution:.4f}")

        click.echo(f"\nTop {top_k} Negative Features:")
        for feature, contribution in local_exp.top_negative_features:
            value = local_exp.feature_values.get(feature, "N/A")
            click.echo(f"  {feature} = {value}: {contribution:.4f}")

        # Save plot
        if output:
            explainer.plot_explanation(
                instance.values, save_path=output, num_features=top_k * 2
            )
            click.echo(f"\nSaved LIME plot to {output}")


@cli.command()
@click.option(
    "--model-path",
    required=True,
    type=click.Path(exists=True),
    help="Path to saved model",
)
@click.option(
    "--data-path",
    required=True,
    type=click.Path(exists=True),
    help="Path to data (CSV)",
)
@click.option(
    "--model-type", type=click.Choice([t.value for t in ModelType]), default="black_box"
)
@click.option(
    "--output", type=click.Path(), help="Output directory for comparison plots"
)
def compare_methods(
    model_path: str, data_path: str, model_type: str, output: Optional[str]
):
    """Compare feature importance across different methods"""
    click.echo(f"Loading model from {model_path}...")
    model = joblib.load(model_path)

    click.echo(f"Loading data from {data_path}...")
    df = pd.read_csv(data_path)
    X = df.iloc[:, :-1]
    y = df.iloc[:, -1]
    feature_names = X.columns.tolist()

    click.echo("Calculating feature importance using multiple methods...")

    analyzer = FeatureImportanceAnalyzer(
        model=model, model_type=ModelType(model_type), feature_names=feature_names
    )

    # Compare methods
    results = analyzer.compare_methods(
        X.values, y.values, methods=["intrinsic", "permutation"]
    )

    # Print comparison
    click.echo("\n=== Feature Importance Comparison ===\n")
    for method_name, explanation in results.items():
        click.echo(f"{method_name.upper()}:")
        for fi in explanation.feature_importances[:10]:
            click.echo(f"  {fi.rank}. {fi.feature_name}: {fi.importance:.4f}")
        click.echo()

    # Save plots
    if output:
        Path(output).mkdir(parents=True, exist_ok=True)
        plot_path = Path(output) / "importance_comparison.png"
        analyzer.plot_comparison(X.values, y.values, save_path=str(plot_path))
        click.echo(f"Saved comparison plot to {plot_path}")


@cli.command()
@click.option(
    "--model-path",
    required=True,
    type=click.Path(exists=True),
    help="Path to saved model",
)
@click.option(
    "--data-path",
    required=True,
    type=click.Path(exists=True),
    help="Path to data (CSV)",
)
@click.option("--output", required=True, type=click.Path(), help="Output JSON file")
@click.option(
    "--num-samples", type=int, default=100, help="Number of samples to explain"
)
def batch_explain(model_path: str, data_path: str, output: str, num_samples: int):
    """Generate explanations for multiple instances and save to JSON"""
    click.echo(f"Loading model from {model_path}...")
    model = joblib.load(model_path)

    click.echo(f"Loading data from {data_path}...")
    df = pd.read_csv(data_path)
    X = df.iloc[:, :-1]
    feature_names = X.columns.tolist()

    # Sample instances
    if len(X) > num_samples:
        indices = np.random.choice(len(X), num_samples, replace=False)
        X_sample = X.iloc[indices]
    else:
        X_sample = X

    click.echo(f"Generating SHAP explanations for {len(X_sample)} instances...")

    explainer = SHAPExplainer(
        model=model, model_type=ModelType.BLACK_BOX, feature_names=feature_names
    )
    explainer.fit(X.values)

    # Generate explanations
    explanations = []
    for idx, row in X_sample.iterrows():
        local_exp = explainer.explain_local(row.values, instance_id=str(idx))
        explanations.append(
            {
                "instance_id": local_exp.instance_id,
                "prediction": local_exp.prediction,
                "expected_value": local_exp.expected_value,
                "feature_contributions": local_exp.feature_contributions,
                "top_positive_features": local_exp.top_positive_features,
                "top_negative_features": local_exp.top_negative_features,
            }
        )

    # Save to JSON
    with open(output, "w") as f:
        json.dump(explanations, f, indent=2)

    click.echo(f"Saved {len(explanations)} explanations to {output}")


if __name__ == "__main__":
    cli()
