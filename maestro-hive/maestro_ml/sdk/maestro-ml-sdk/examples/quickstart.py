"""
Maestro ML SDK - Quickstart Example

This example demonstrates the basic usage of the Maestro ML SDK
"""

from maestro_ml import MaestroClient

def main():
    # Initialize the client (loads config from environment)
    client = MaestroClient()

    print("=" * 60)
    print("Maestro ML SDK - Quickstart Example")
    print("=" * 60)
    print()

    # List all models
    print("📋 Listing all registered models...")
    models = client.models.list(max_results=10)
    print(f"Found {len(models)} models:")
    for model in models:
        print(f"  - {model.name} ({len(model.latest_versions)} versions)")
    print()

    # Get a specific model
    if models:
        model_name = models[0].name
        print(f"📦 Getting details for model: {model_name}")
        model = client.models.get(model_name)
        print(f"  Name: {model.name}")
        print(f"  Description: {model.description or 'No description'}")
        print(f"  Versions: {len(model.latest_versions)}")
        print(f"  Tags: {model.tags}")
        print()

        # Get latest production version
        if model.production_version:
            print(f"🚀 Production version:")
            prod = model.production_version
            print(f"  Version: {prod.version}")
            print(f"  Stage: {prod.current_stage}")
            print(f"  Status: {prod.status}")
            print(f"  Created: {prod.creation_timestamp}")
        else:
            print("  No production version yet")
        print()

    # Create a new model
    print("➕ Creating a new model...")
    try:
        new_model = client.models.create(
            name="quickstart-demo-model",
            description="Demo model created from quickstart example",
            tags={"demo": "true", "created_by": "sdk_example"}
        )
        print(f"✅ Created model: {new_model.name}")
        print()

        # Clean up: delete the demo model
        print("🗑️  Cleaning up demo model...")
        client.models.delete("quickstart-demo-model")
        print("✅ Demo model deleted")
    except Exception as e:
        print(f"ℹ️  Model might already exist or operation failed: {e}")
    print()

    # Search for models
    print("🔍 Searching for models with 'fraud' in name...")
    fraud_models = client.models.search("name LIKE '%fraud%'", max_results=5)
    print(f"Found {len(fraud_models)} fraud-related models")
    for model in fraud_models:
        print(f"  - {model.name}")
    print()

    print("=" * 60)
    print("✅ Quickstart example completed!")
    print("=" * 60)


if __name__ == "__main__":
    main()
