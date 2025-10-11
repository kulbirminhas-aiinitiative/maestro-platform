#!/usr/bin/env python3
"""
CLI tool for generating ML Model Cards from MLflow

Usage:
    python cli.py generate <model_name> <version> [--format pdf|md|json]
    python cli.py list
    python cli.py validate <model_card.json>
"""

import click
import mlflow
from pathlib import Path
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from governance.model_cards.card_generator import ModelCardGenerator
from governance.model_cards.model_card_schema import ModelCard


@click.group()
@click.option('--mlflow-uri', envvar='MLFLOW_TRACKING_URI',
              default='http://localhost:5000',
              help='MLflow tracking URI')
@click.option('--pdf-service-url', envvar='PDF_SERVICE_URL',
              default='http://localhost:9550',
              help='PDF Generator Service URL')
@click.pass_context
def cli(ctx, mlflow_uri, pdf_service_url):
    """Model Card Generator CLI - Auto-generate ML model documentation"""
    ctx.ensure_object(dict)
    ctx.obj['mlflow_uri'] = mlflow_uri
    ctx.obj['pdf_service_url'] = pdf_service_url


@cli.command()
@click.argument('model_name')
@click.argument('version')
@click.option('--format', '-f', type=click.Choice(['pdf', 'md', 'json', 'all']),
              default='md', help='Output format')
@click.option('--output', '-o', type=click.Path(),
              help='Output directory (default: ./generated)')
@click.option('--override', '-r', type=click.Path(exists=True),
              help='JSON file with manual overrides')
@click.pass_context
def generate(ctx, model_name, version, format, output, override):
    """
    Generate model card from MLflow metadata

    Examples:
        \b
        # Generate Markdown card
        python cli.py generate fraud-detector 3

        \b
        # Generate PDF card
        python cli.py generate fraud-detector 3 --format pdf

        \b
        # Generate all formats with overrides
        python cli.py generate fraud-detector 3 --format all --override overrides.json
    """
    mlflow_uri = ctx.obj['mlflow_uri']
    pdf_service_url = ctx.obj['pdf_service_url']

    # Set output directory
    output_dir = Path(output) if output else Path(__file__).parent / "generated"
    output_dir.mkdir(exist_ok=True, parents=True)

    click.echo(f"🔄 Generating model card for {model_name} v{version}")
    click.echo(f"📡 MLflow URI: {mlflow_uri}")

    # Initialize generator
    generator = ModelCardGenerator(mlflow_uri=mlflow_uri)

    # Load overrides if provided
    overrides = None
    if override:
        import json
        with open(override) as f:
            overrides = json.load(f)
        click.echo(f"📝 Loaded overrides from {override}")

    try:
        # Generate model card
        card = generator.generate_from_mlflow(
            model_name=model_name,
            version=version,
            overrides=overrides
        )

        base_filename = f"{model_name}-v{version}"

        # Generate requested formats
        formats_to_generate = ['pdf', 'md', 'json'] if format == 'all' else [format]

        for fmt in formats_to_generate:
            if fmt == 'md':
                output_path = output_dir / f"{base_filename}.md"
                generator.save_markdown(card, output_path)
                click.echo(f"✅ Markdown saved to {output_path}")

            elif fmt == 'json':
                output_path = output_dir / f"{base_filename}.json"
                generator.save_json(card, output_path)
                click.echo(f"✅ JSON saved to {output_path}")

            elif fmt == 'pdf':
                output_path = output_dir / f"{base_filename}.pdf"
                try:
                    generator.save_pdf(card, output_path, pdf_service_url)
                    click.echo(f"✅ PDF saved to {output_path}")
                except Exception as e:
                    click.echo(f"⚠️  PDF generation failed: {e}", err=True)
                    click.echo(f"💡 Make sure PDF service is running at {pdf_service_url}")
                    if format != 'all':
                        raise

        click.echo(f"🎉 Model card generated successfully!")

    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        raise click.Abort()


@cli.command()
@click.option('--filter', '-f', help='Filter models by name pattern')
@click.pass_context
def list(ctx, filter):
    """
    List available models in MLflow registry

    Examples:
        \b
        # List all models
        python cli.py list

        \b
        # Filter models
        python cli.py list --filter fraud
    """
    mlflow_uri = ctx.obj['mlflow_uri']
    mlflow.set_tracking_uri(mlflow_uri)

    from mlflow.tracking import MlflowClient
    client = MlflowClient()

    click.echo(f"📡 MLflow URI: {mlflow_uri}\n")

    try:
        models = client.search_registered_models()

        if filter:
            models = [m for m in models if filter.lower() in m.name.lower()]

        if not models:
            click.echo("No models found")
            return

        click.echo(f"Found {len(models)} model(s):\n")

        for model in models:
            click.echo(f"📦 {model.name}")

            # Get latest versions
            versions = client.get_latest_versions(model.name, stages=["Production", "Staging", "None"])

            for version in versions[:5]:  # Show max 5 versions
                stage = version.current_stage or "None"
                click.echo(f"   v{version.version} [{stage}]")

            if len(versions) > 5:
                click.echo(f"   ... and {len(versions) - 5} more versions")

            click.echo()

    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        raise click.Abort()


@cli.command()
@click.argument('card_file', type=click.Path(exists=True))
def validate(card_file):
    """
    Validate a model card JSON file

    Examples:
        \b
        # Validate a model card
        python cli.py validate fraud-detector-v3.json
    """
    import json
    from pydantic import ValidationError

    click.echo(f"🔍 Validating {card_file}...")

    try:
        with open(card_file) as f:
            card_data = json.load(f)

        # Validate using Pydantic model
        card = ModelCard(**card_data)

        click.echo(f"✅ Model card is valid!")
        click.echo(f"\nModel: {card.model_details.name} v{card.model_details.version}")
        click.echo(f"Type: {card.model_details.model_type.value}")

        if card.metrics.model_performance:
            click.echo(f"Metrics: {len(card.metrics.model_performance)} metrics")

        if card.training_data.dataset_name:
            click.echo(f"Dataset: {card.training_data.dataset_name}")

    except ValidationError as e:
        click.echo(f"❌ Validation failed:\n", err=True)
        for error in e.errors():
            field = '.'.join(str(x) for x in error['loc'])
            click.echo(f"  • {field}: {error['msg']}", err=True)
        raise click.Abort()

    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        raise click.Abort()


@cli.command()
@click.argument('model_name')
@click.argument('version')
@click.option('--key', '-k', required=True, help='Key to override (e.g., intended_use.primary_uses)')
@click.option('--value', '-v', required=True, help='JSON value to set')
@click.pass_context
def override(ctx, model_name, version, key, value):
    """
    Create an override file for manual annotations

    Examples:
        \b
        # Add intended use
        python cli.py override fraud-detector 3 \\
            --key intended_use.primary_uses \\
            --value '["Fraud detection", "Risk assessment"]'

        \b
        # Add ethical considerations
        python cli.py override fraud-detector 3 \\
            --key ethical_considerations.risks_and_harms \\
            --value '["May have bias against certain demographics"]'
    """
    import json

    override_file = Path(f"{model_name}-v{version}-overrides.json")

    # Load existing overrides if file exists
    if override_file.exists():
        with open(override_file) as f:
            overrides = json.load(f)
    else:
        overrides = {}

    # Parse the key path
    keys = key.split('.')
    current = overrides

    # Navigate/create nested structure
    for k in keys[:-1]:
        if k not in current:
            current[k] = {}
        current = current[k]

    # Set the value
    try:
        current[keys[-1]] = json.loads(value)
    except json.JSONDecodeError:
        # If not valid JSON, treat as string
        current[keys[-1]] = value

    # Save overrides
    with open(override_file, 'w') as f:
        json.dump(overrides, f, indent=2)

    click.echo(f"✅ Override saved to {override_file}")
    click.echo(f"\nCurrent overrides:")
    click.echo(json.dumps(overrides, indent=2))
    click.echo(f"\n💡 Use with: python cli.py generate {model_name} {version} --override {override_file}")


if __name__ == '__main__':
    cli()
