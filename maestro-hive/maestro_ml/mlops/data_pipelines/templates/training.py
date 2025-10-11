"""
Model Training Pipeline Template

Template for training ML models with validation and tracking.
"""

import logging
from pathlib import Path
from typing import Any, Optional

import joblib
import pandas as pd
from sklearn.model_selection import train_test_split

from ..pipeline_builder import PipelineBuilder

logger = logging.getLogger(__name__)


def load_training_data(data_path: str, **kwargs) -> dict[str, Any]:
    """
    Load training data

    Args:
        data_path: Path to training data

    Returns:
        Dictionary with data splits
    """
    logger.info(f"Loading training data from {data_path}")

    df = pd.read_parquet(data_path)

    logger.info(f"Loaded {len(df)} rows for training")

    return {"data": df}


def split_data(
    data: pd.DataFrame,
    target_column: str,
    test_size: float = 0.2,
    random_state: int = 42,
    **kwargs
) -> dict[str, Any]:
    """
    Split data into train/test sets

    Args:
        data: Input DataFrame
        target_column: Target column name
        test_size: Fraction of data for testing
        random_state: Random seed

    Returns:
        Dictionary with train/test splits
    """
    logger.info(f"Splitting data (test_size={test_size})")

    X = data.drop(columns=[target_column])
    y = data[target_column]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y,
        test_size=test_size,
        random_state=random_state,
        stratify=y if y.dtype == 'object' or y.nunique() < 20 else None
    )

    logger.info(f"Train set: {len(X_train)} samples")
    logger.info(f"Test set: {len(X_test)} samples")

    return {
        "X_train": X_train,
        "X_test": X_test,
        "y_train": y_train,
        "y_test": y_test
    }


def train_model(
    X_train: pd.DataFrame,
    y_train: pd.Series,
    model_type: str = "random_forest",
    **kwargs
) -> Any:
    """
    Train ML model

    Args:
        X_train: Training features
        y_train: Training target
        model_type: Type of model to train

    Returns:
        Trained model
    """
    logger.info(f"Training {model_type} model...")

    # Import model class
    if model_type == "random_forest":
        from sklearn.ensemble import RandomForestClassifier
        model = RandomForestClassifier(n_estimators=100, random_state=42)
    elif model_type == "gradient_boosting":
        from sklearn.ensemble import GradientBoostingClassifier
        model = GradientBoostingClassifier(n_estimators=100, random_state=42)
    elif model_type == "logistic_regression":
        from sklearn.linear_model import LogisticRegression
        model = LogisticRegression(max_iter=1000, random_state=42)
    else:
        raise ValueError(f"Unknown model type: {model_type}")

    # Train model
    model.fit(X_train, y_train)

    logger.info(f"Model training completed")

    return model


def evaluate_model(
    model: Any,
    X_test: pd.DataFrame,
    y_test: pd.Series,
    **kwargs
) -> dict[str, float]:
    """
    Evaluate model performance

    Args:
        model: Trained model
        X_test: Test features
        y_test: Test target

    Returns:
        Dictionary of evaluation metrics
    """
    logger.info("Evaluating model...")

    from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score

    # Make predictions
    y_pred = model.predict(X_test)

    # Calculate metrics
    metrics = {
        "accuracy": accuracy_score(y_test, y_pred),
        "precision": precision_score(y_test, y_pred, average='weighted', zero_division=0),
        "recall": recall_score(y_test, y_pred, average='weighted', zero_division=0),
        "f1_score": f1_score(y_test, y_pred, average='weighted', zero_division=0)
    }

    logger.info(f"Evaluation metrics:")
    for name, value in metrics.items():
        logger.info(f"  {name}: {value:.4f}")

    return metrics


def save_model(
    model: Any,
    model_path: str,
    metrics: Optional[dict[str, float]] = None,
    **kwargs
) -> dict[str, Any]:
    """
    Save trained model

    Args:
        model: Trained model to save
        model_path: Path to save model
        metrics: Model metrics to save alongside

    Returns:
        Save result
    """
    logger.info(f"Saving model to {model_path}")

    Path(model_path).parent.mkdir(parents=True, exist_ok=True)

    # Save model
    joblib.dump(model, model_path)

    # Save metrics if provided
    if metrics:
        metrics_path = str(Path(model_path).with_suffix('.metrics.json'))
        import json
        with open(metrics_path, 'w') as f:
            json.dump(metrics, f, indent=2)
        logger.info(f"Saved metrics to {metrics_path}")

    logger.info(f"Model saved successfully")

    return {
        "model_path": model_path,
        "metrics": metrics
    }


def log_to_mlflow(
    model: Any,
    metrics: dict[str, float],
    model_name: str = "model",
    **kwargs
) -> dict[str, str]:
    """
    Log model and metrics to MLflow

    Args:
        model: Trained model
        metrics: Model metrics
        model_name: Model name for MLflow

    Returns:
        MLflow run information
    """
    try:
        import mlflow

        logger.info("Logging to MLflow...")

        with mlflow.start_run(run_name=model_name):
            # Log metrics
            mlflow.log_metrics(metrics)

            # Log model
            mlflow.sklearn.log_model(model, "model")

            run_id = mlflow.active_run().info.run_id
            logger.info(f"Logged to MLflow run: {run_id}")

            return {"run_id": run_id, "model_name": model_name}

    except ImportError:
        logger.warning("MLflow not installed, skipping logging")
        return {}


def create_training_pipeline(
    pipeline_id: str = "model_training",
    name: str = "Model Training Pipeline"
) -> PipelineBuilder:
    """
    Create model training pipeline

    Returns:
        PipelineBuilder configured for model training
    """
    builder = PipelineBuilder(
        pipeline_id=pipeline_id,
        name=name,
        description="Load data, train model, evaluate, and save"
    )

    builder.add_task(
        task_id="load_data",
        function=load_training_data,
        name="Load Training Data",
        retry_count=2
    )

    builder.add_task(
        task_id="split_data",
        function=split_data,
        name="Split Train/Test Data",
        dependencies=["load_data"],
        retry_count=0
    )

    builder.add_task(
        task_id="train_model",
        function=train_model,
        name="Train ML Model",
        dependencies=["split_data"],
        retry_count=1
    )

    builder.add_task(
        task_id="evaluate_model",
        function=evaluate_model,
        name="Evaluate Model",
        dependencies=["train_model", "split_data"],
        retry_count=0
    )

    builder.add_task(
        task_id="save_model",
        function=save_model,
        name="Save Trained Model",
        dependencies=["train_model", "evaluate_model"],
        retry_count=2
    )

    builder.add_task(
        task_id="log_to_mlflow",
        function=log_to_mlflow,
        name="Log to MLflow",
        dependencies=["train_model", "evaluate_model"],
        retry_count=1
    )

    return builder


# Example usage
if __name__ == "__main__":
    pipeline = create_training_pipeline()

    results = pipeline.execute(
        data_path="data/processed/dataset.parquet",
        target_column="target",
        test_size=0.2,
        model_type="random_forest",
        model_path="models/model.pkl",
        model_name="my_model"
    )

    print("\nTraining Pipeline Results:")
    for task_id, result in results.items():
        print(f"  {task_id}: {result.status.value}")
        if result.duration_seconds:
            print(f"    Duration: {result.duration_seconds:.2f}s")
