"""
Example usage of Model Card Generator

This demonstrates how to use the ModelCardGenerator programmatically.
For CLI usage, see cli.py
"""

from pathlib import Path
from card_generator import ModelCardGenerator

# Example 1: Generate from MLflow with auto-extraction
def example_basic_generation():
    """Basic model card generation from MLflow"""
    generator = ModelCardGenerator(mlflow_uri="http://localhost:5000")

    card = generator.generate_from_mlflow(
        model_name="fraud-detector",
        version="3"
    )

    # Save as Markdown
    generator.save_markdown(card, Path("./generated/fraud-detector-v3.md"))

    # Save as JSON
    generator.save_json(card, Path("./generated/fraud-detector-v3.json"))

    print("✅ Model card generated!")


# Example 2: Generate with manual overrides
def example_with_overrides():
    """Generate model card with manual annotations"""
    generator = ModelCardGenerator(mlflow_uri="http://localhost:5000")

    # Manual overrides for human-required sections
    overrides = {
        "intended_use": {
            "primary_uses": [
                "Real-time fraud detection in payment processing",
                "Risk assessment for transaction approval"
            ],
            "primary_users": [
                "Fraud analysts",
                "Risk management team",
                "Automated payment systems"
            ],
            "out_of_scope": [
                "Credit scoring decisions",
                "Customer profiling for marketing",
                "Employment decisions"
            ]
        },
        "ethical_considerations": {
            "risks_and_harms": [
                "May exhibit bias against certain transaction patterns common in specific demographics",
                "False positives could delay legitimate transactions",
                "Model drift may occur as fraud patterns evolve"
            ],
            "mitigations": [
                "Regular bias audits conducted monthly",
                "Human review required for high-value transactions",
                "Model retraining scheduled quarterly with diverse data",
                "Explanation provided to customers for flagged transactions"
            ]
        },
        "caveats_and_recommendations": {
            "caveats": [
                "Trained on 2023-2024 transaction data; may not capture emerging fraud patterns",
                "Performance may degrade for international transactions",
                "Requires minimum transaction history for accurate predictions"
            ],
            "recommendations": [
                "Monitor model performance weekly using fraud rate metrics",
                "Retrain model when F1 score drops below 0.85",
                "Combine with rule-based systems for comprehensive fraud prevention",
                "Provide clear communication to users about fraud detection process"
            ]
        }
    }

    card = generator.generate_from_mlflow(
        model_name="fraud-detector",
        version="3",
        overrides=overrides
    )

    # Save all formats
    generator.save_markdown(card, Path("./generated/fraud-detector-v3-full.md"))
    generator.save_json(card, Path("./generated/fraud-detector-v3-full.json"))

    # Save as PDF (requires PDF service running)
    try:
        generator.save_pdf(
            card,
            Path("./generated/fraud-detector-v3-full.pdf"),
            pdf_service_url="http://localhost:9550"
        )
        print("✅ PDF generated!")
    except Exception as e:
        print(f"⚠️  PDF generation skipped: {e}")
        print("💡 Start PDF service with: cd ~/projects/utilities/services/pdf_generator && python app.py")

    print("✅ Full model card generated with overrides!")


# Example 3: Batch generation for all production models
def example_batch_generation():
    """Generate model cards for all production models"""
    import mlflow
    from mlflow.tracking import MlflowClient

    mlflow.set_tracking_uri("http://localhost:5000")
    client = MlflowClient()
    generator = ModelCardGenerator(mlflow_uri="http://localhost:5000")

    # Get all models
    models = client.search_registered_models()

    output_dir = Path("./generated/batch")
    output_dir.mkdir(parents=True, exist_ok=True)

    for model in models:
        # Get production versions
        versions = client.get_latest_versions(model.name, stages=["Production"])

        for version in versions:
            print(f"🔄 Generating card for {model.name} v{version.version}...")

            try:
                card = generator.generate_from_mlflow(
                    model_name=model.name,
                    version=version.version
                )

                # Save as Markdown
                output_path = output_dir / f"{model.name}-v{version.version}.md"
                generator.save_markdown(card, output_path)

                print(f"✅ Generated {output_path}")

            except Exception as e:
                print(f"❌ Failed for {model.name} v{version.version}: {e}")

    print(f"🎉 Batch generation complete! Check {output_dir}/")


# Example 4: Programmatic model card creation
def example_manual_creation():
    """Create model card programmatically without MLflow"""
    from model_card_schema import (
        ModelCard, ModelDetails, IntendedUse, PerformanceMetrics,
        TrainingData, Metric, ModelType
    )
    from datetime import datetime

    card = ModelCard(
        model_details=ModelDetails(
            name="custom-classifier",
            version="1.0.0",
            model_type=ModelType.CLASSIFICATION,
            date=datetime.now(),
            owners=["ml-team@company.com"],
            framework="scikit-learn",
            algorithm="RandomForest",
            license="Apache 2.0"
        ),
        intended_use=IntendedUse(
            primary_uses=["Customer churn prediction"],
            primary_users=["Marketing team", "Customer success team"],
            out_of_scope=["Individual employee decisions"]
        ),
        metrics=PerformanceMetrics(
            model_performance=[
                Metric(name="accuracy", value=0.89),
                Metric(name="precision", value=0.87),
                Metric(name="recall", value=0.91),
                Metric(name="f1_score", value=0.89)
            ]
        ),
        training_data=TrainingData(
            dataset_name="customer_data_2024",
            num_samples=50000,
            preprocessing=["normalization", "one-hot encoding", "feature selection"]
        )
    )

    generator = ModelCardGenerator()
    generator.save_markdown(card, Path("./generated/custom-classifier.md"))
    generator.save_json(card, Path("./generated/custom-classifier.json"))

    print("✅ Manual model card created!")


if __name__ == "__main__":
    import sys

    # Create output directory
    Path("./generated").mkdir(exist_ok=True)

    if len(sys.argv) > 1:
        example_name = sys.argv[1]
        examples = {
            "basic": example_basic_generation,
            "overrides": example_with_overrides,
            "batch": example_batch_generation,
            "manual": example_manual_creation,
        }

        if example_name in examples:
            examples[example_name]()
        else:
            print(f"Unknown example: {example_name}")
            print(f"Available examples: {', '.join(examples.keys())}")
    else:
        print("Model Card Generator Examples")
        print("=" * 50)
        print("\nUsage: python example_usage.py <example_name>")
        print("\nAvailable examples:")
        print("  basic      - Basic generation from MLflow")
        print("  overrides  - Generation with manual overrides")
        print("  batch      - Batch generation for all production models")
        print("  manual     - Manual programmatic creation")
        print("\nExample:")
        print("  python example_usage.py overrides")
