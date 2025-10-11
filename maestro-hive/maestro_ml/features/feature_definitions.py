"""
Feature Definitions

Sample feature definitions for demonstration and testing.
Shows how to define features, entities, and data sources for Feast.
"""

from datetime import timedelta

# These imports will work when Feast is installed
# For now, they're here as examples and documentation

FEATURE_DEFINITIONS_CODE = """
# Example Feast feature definitions
# Save this to your feature repository (e.g., mlops/feast/feature_repo/features.py)

from datetime import timedelta
from feast import Entity, Feature, FeatureView, FileSource, ValueType

# ===========================
# Entities
# ===========================

user = Entity(
    name="user_id",
    value_type=ValueType.INT64,
    description="User identifier"
)

model = Entity(
    name="model_id",
    value_type=ValueType.STRING,
    description="Model identifier"
)

project = Entity(
    name="project_id",
    value_type=ValueType.STRING,
    description="ML project identifier"
)


# ===========================
# Data Sources
# ===========================

# User features source (from data warehouse or file)
user_features_source = FileSource(
    path="data/user_features.parquet",
    event_timestamp_column="event_timestamp",
    created_timestamp_column="created"
)

# Model performance metrics source
model_metrics_source = FileSource(
    path="data/model_metrics.parquet",
    event_timestamp_column="event_timestamp",
    created_timestamp_column="created"
)

# Project metadata source
project_features_source = FileSource(
    path="data/project_features.parquet",
    event_timestamp_column="event_timestamp",
    created_timestamp_column="created"
)


# ===========================
# Feature Views
# ===========================

user_features = FeatureView(
    name="user_features",
    entities=["user_id"],
    ttl=timedelta(days=7),
    features=[
        Feature(name="age", dtype=ValueType.INT64),
        Feature(name="country", dtype=ValueType.STRING),
        Feature(name="signup_date", dtype=ValueType.UNIX_TIMESTAMP),
        Feature(name="total_projects", dtype=ValueType.INT64),
        Feature(name="total_models", dtype=ValueType.INT64),
        Feature(name="avg_model_accuracy", dtype=ValueType.DOUBLE),
    ],
    online=True,
    batch_source=user_features_source,
    tags={"team": "ml-platform"}
)

model_performance_features = FeatureView(
    name="model_performance_features",
    entities=["model_id"],
    ttl=timedelta(days=30),
    features=[
        Feature(name="accuracy", dtype=ValueType.DOUBLE),
        Feature(name="precision", dtype=ValueType.DOUBLE),
        Feature(name="recall", dtype=ValueType.DOUBLE),
        Feature(name="f1_score", dtype=ValueType.DOUBLE),
        Feature(name="latency_p95_ms", dtype=ValueType.DOUBLE),
        Feature(name="training_time_minutes", dtype=ValueType.DOUBLE),
        Feature(name="prediction_count_24h", dtype=ValueType.INT64),
    ],
    online=True,
    batch_source=model_metrics_source,
    tags={"team": "ml-platform", "category": "model-monitoring"}
)

project_features = FeatureView(
    name="project_features",
    entities=["project_id"],
    ttl=timedelta(days=90),
    features=[
        Feature(name="team_size", dtype=ValueType.INT64),
        Feature(name="project_duration_days", dtype=ValueType.INT64),
        Feature(name="num_experiments", dtype=ValueType.INT64),
        Feature(name="num_models", dtype=ValueType.INT64),
        Feature(name="best_model_score", dtype=ValueType.DOUBLE),
        Feature(name="total_training_hours", dtype=ValueType.DOUBLE),
        Feature(name="budget_usd", dtype=ValueType.DOUBLE),
    ],
    online=True,
    batch_source=project_features_source,
    tags={"team": "ml-platform", "category": "project-analytics"}
)
"""


def generate_sample_data():
    """
    Generate sample feature data for testing

    Returns:
        Dictionary of DataFrames for each feature source
    """
    import pandas as pd
    from datetime import datetime, timedelta
    import random

    # Generate user features
    num_users = 100
    user_data = []

    for user_id in range(1, num_users + 1):
        user_data.append({
            "user_id": user_id,
            "event_timestamp": datetime.utcnow() - timedelta(hours=random.randint(0, 24)),
            "created": datetime.utcnow(),
            "age": random.randint(22, 65),
            "country": random.choice(["US", "UK", "CA", "DE", "FR", "JP", "AU"]),
            "signup_date": int((datetime.utcnow() - timedelta(days=random.randint(1, 365))).timestamp()),
            "total_projects": random.randint(0, 50),
            "total_models": random.randint(0, 200),
            "avg_model_accuracy": round(random.uniform(0.7, 0.99), 4)
        })

    user_df = pd.DataFrame(user_data)

    # Generate model performance features
    num_models = 200
    model_data = []

    for i in range(num_models):
        model_data.append({
            "model_id": f"model_{i}",
            "event_timestamp": datetime.utcnow() - timedelta(hours=random.randint(0, 24)),
            "created": datetime.utcnow(),
            "accuracy": round(random.uniform(0.7, 0.99), 4),
            "precision": round(random.uniform(0.7, 0.99), 4),
            "recall": round(random.uniform(0.7, 0.99), 4),
            "f1_score": round(random.uniform(0.7, 0.99), 4),
            "latency_p95_ms": round(random.uniform(10, 500), 2),
            "training_time_minutes": round(random.uniform(5, 180), 2),
            "prediction_count_24h": random.randint(100, 10000)
        })

    model_df = pd.DataFrame(model_data)

    # Generate project features
    num_projects = 50
    project_data = []

    for i in range(num_projects):
        project_data.append({
            "project_id": f"project_{i}",
            "event_timestamp": datetime.utcnow() - timedelta(hours=random.randint(0, 24)),
            "created": datetime.utcnow(),
            "team_size": random.randint(1, 15),
            "project_duration_days": random.randint(7, 365),
            "num_experiments": random.randint(5, 500),
            "num_models": random.randint(1, 50),
            "best_model_score": round(random.uniform(0.75, 0.99), 4),
            "total_training_hours": round(random.uniform(10, 1000), 2),
            "budget_usd": round(random.uniform(1000, 100000), 2)
        })

    project_df = pd.DataFrame(project_data)

    return {
        "user_features": user_df,
        "model_performance_features": model_df,
        "project_features": project_df
    }


def save_sample_data(output_dir: str = "data"):
    """
    Save sample data to Parquet files

    Args:
        output_dir: Directory to save data files
    """
    from pathlib import Path

    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True, parents=True)

    data = generate_sample_data()

    for name, df in data.items():
        filepath = output_path / f"{name}.parquet"
        df.to_parquet(filepath, index=False)
        print(f"Saved {len(df)} rows to {filepath}")

    print(f"\nSample data saved to {output_dir}/")
    print("\nTo use with Feast:")
    print("1. Create feature repository: feast init feature_repo")
    print("2. Copy feature definitions to feature_repo/features.py")
    print("3. Run: feast apply")
    print("4. Materialize features: feast materialize <start_date> <end_date>")


if __name__ == "__main__":
    save_sample_data()
