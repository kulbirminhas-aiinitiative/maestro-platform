"""
Kubeflow Pipeline: ML Training with MLflow and Feast Integration
"""

from kfp import dsl, compiler
from kfp.dsl import component, Dataset, Model, Metrics, Output, Input
from typing import NamedTuple


@component(
    base_image='python:3.11',
    packages_to_install=['feast', 'pandas', 'pyarrow']
)
def extract_features(
    entity_ids: list,
    feature_view: str,
    feature_service: str,
    output_dataset: Output[Dataset]
):
    """Extract features from Feast feature store"""
    from feast import FeatureStore
    import pandas as pd
    from datetime import datetime

    # Connect to Feast
    store = FeatureStore(repo_path='/feast/feature_repo')

    # Create entity dataframe
    entity_df = pd.DataFrame({
        'entity_id': entity_ids,
        'event_timestamp': [datetime.now()] * len(entity_ids)
    })

    # Get historical features
    features = store.get_historical_features(
        entity_df=entity_df,
        features=[f"{feature_view}:*"]
    ).to_df()

    # Save to output
    features.to_parquet(output_dataset.path, index=False)

    print(f"✓ Extracted {len(features)} feature rows")
    print(f"✓ Features shape: {features.shape}")


@component(
    base_image='python:3.11',
    packages_to_install=['pandas', 'scikit-learn', 'great-expectations']
)
def validate_data(
    input_dataset: Input[Dataset],
    output_dataset: Output[Dataset]
) -> NamedTuple('ValidationOutput', [('passed', bool), ('report', str)]):
    """Validate data quality"""
    import pandas as pd
    import json
    from collections import namedtuple

    # Load data
    df = pd.read_parquet(input_dataset.path)

    # Run validations
    validations = {
        'total_rows': len(df),
        'missing_values': df.isnull().sum().to_dict(),
        'duplicates': df.duplicated().sum(),
        'numeric_ranges': {}
    }

    # Check numeric columns
    for col in df.select_dtypes(include=['float64', 'int64']).columns:
        validations['numeric_ranges'][col] = {
            'min': float(df[col].min()),
            'max': float(df[col].max()),
            'mean': float(df[col].mean())
        }

    # Quality gate: no more than 5% missing values
    missing_pct = (df.isnull().sum().sum() / (len(df) * len(df.columns))) * 100
    passed = missing_pct < 5.0

    # Save validated data
    df.to_parquet(output_dataset.path, index=False)

    report = json.dumps(validations, indent=2)
    print(f"✓ Validation passed: {passed}")
    print(f"✓ Missing values: {missing_pct:.2f}%")
    print(f"Report:\n{report}")

    OutputTuple = namedtuple('ValidationOutput', ['passed', 'report'])
    return OutputTuple(passed, report)


@component(
    base_image='python:3.11',
    packages_to_install=['mlflow', 'scikit-learn', 'pandas']
)
def train_model(
    input_dataset: Input[Dataset],
    experiment_name: str,
    model_type: str,
    n_estimators: int,
    max_depth: int,
    output_model: Output[Model],
    output_metrics: Output[Metrics]
) -> NamedTuple('TrainingOutput', [('accuracy', float), ('f1_score', float), ('model_uri', str)]):
    """Train ML model and log to MLflow"""
    import mlflow
    import pandas as pd
    from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import accuracy_score, f1_score, classification_report
    import json
    from collections import namedtuple

    # Load data
    df = pd.read_parquet(input_dataset.path)
    X = df.drop('target', axis=1)
    y = df['target']
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    # Configure MLflow
    mlflow.set_tracking_uri('http://mlflow.ml-platform.svc.cluster.local')
    mlflow.set_experiment(experiment_name)

    # Train model
    with mlflow.start_run():
        # Create model
        if model_type == 'random_forest':
            model = RandomForestClassifier(
                n_estimators=n_estimators,
                max_depth=max_depth,
                random_state=42
            )
        elif model_type == 'gradient_boosting':
            model = GradientBoostingClassifier(
                n_estimators=n_estimators,
                max_depth=max_depth,
                random_state=42
            )
        else:
            raise ValueError(f"Unknown model type: {model_type}")

        # Train
        model.fit(X_train, y_train)

        # Evaluate
        train_preds = model.predict(X_train)
        test_preds = model.predict(X_test)

        train_acc = accuracy_score(y_train, train_preds)
        test_acc = accuracy_score(y_test, test_preds)
        test_f1 = f1_score(y_test, test_preds, average='weighted')

        # Log to MLflow
        mlflow.log_params({
            'model_type': model_type,
            'n_estimators': n_estimators,
            'max_depth': max_depth,
            'train_size': len(X_train),
            'test_size': len(X_test)
        })

        mlflow.log_metrics({
            'train_accuracy': train_acc,
            'test_accuracy': test_acc,
            'f1_score': test_f1
        })

        # Log model
        mlflow.sklearn.log_model(model, 'model')
        model_uri = mlflow.get_artifact_uri('model')

        # Log classification report
        report = classification_report(y_test, test_preds, output_dict=True)
        mlflow.log_dict(report, 'classification_report.json')

        # Save metrics for Kubeflow
        output_metrics.log_metric('accuracy', test_acc)
        output_metrics.log_metric('f1_score', test_f1)

        print(f"✓ Model trained: {model_type}")
        print(f"✓ Train accuracy: {train_acc:.4f}")
        print(f"✓ Test accuracy: {test_acc:.4f}")
        print(f"✓ F1 score: {test_f1:.4f}")
        print(f"✓ Model URI: {model_uri}")

        # Save model path
        with open(output_model.path, 'w') as f:
            f.write(model_uri)

        OutputTuple = namedtuple('TrainingOutput', ['accuracy', 'f1_score', 'model_uri'])
        return OutputTuple(test_acc, test_f1, model_uri)


@component(
    base_image='python:3.11',
    packages_to_install=['mlflow']
)
def register_model(
    model_uri: str,
    model_name: str,
    accuracy: float,
    f1_score: float,
    min_accuracy: float = 0.85
) -> str:
    """Register model in MLflow if quality gate passes"""
    import mlflow

    mlflow.set_tracking_uri('http://mlflow.ml-platform.svc.cluster.local')

    if accuracy >= min_accuracy:
        result = mlflow.register_model(model_uri, model_name)

        # Transition to Staging
        client = mlflow.tracking.MlflowClient()
        client.transition_model_version_stage(
            name=model_name,
            version=result.version,
            stage="Staging"
        )

        print(f"✓ Model registered: {model_name} v{result.version}")
        print(f"✓ Stage: Staging")
        print(f"✓ Accuracy: {accuracy:.4f}")

        return f"Registered: {model_name} v{result.version} (Staging)"
    else:
        print(f"✗ Quality gate failed: accuracy {accuracy:.4f} < {min_accuracy}")
        return f"Failed: accuracy {accuracy:.4f} < {min_accuracy}"


@dsl.pipeline(
    name='ML Training Pipeline',
    description='End-to-end ML training with Feast features and MLflow tracking'
)
def ml_training_pipeline(
    entity_ids: list = [1, 2, 3, 4, 5],
    feature_view: str = 'user_features',
    feature_service: str = 'user_feature_service',
    experiment_name: str = 'ml-platform-training',
    model_type: str = 'random_forest',
    model_name: str = 'ml-platform-model',
    n_estimators: int = 100,
    max_depth: int = 10,
    min_accuracy: float = 0.85
):
    """
    ML Training Pipeline

    Steps:
    1. Extract features from Feast
    2. Validate data quality
    3. Train model
    4. Register model in MLflow if quality gate passes

    Args:
        entity_ids: List of entity IDs to get features for
        feature_view: Feast feature view name
        feature_service: Feast feature service name
        experiment_name: MLflow experiment name
        model_type: Type of model (random_forest, gradient_boosting)
        model_name: Model name in MLflow registry
        n_estimators: Number of trees
        max_depth: Maximum tree depth
        min_accuracy: Minimum accuracy for registration
    """

    # Step 1: Extract features from Feast
    extract_task = extract_features(
        entity_ids=entity_ids,
        feature_view=feature_view,
        feature_service=feature_service
    )

    # Step 2: Validate data
    validate_task = validate_data(
        input_dataset=extract_task.outputs['output_dataset']
    )

    # Step 3: Train model (only if validation passes)
    with dsl.Condition(validate_task.outputs['passed'] == True):
        train_task = train_model(
            input_dataset=validate_task.outputs['output_dataset'],
            experiment_name=experiment_name,
            model_type=model_type,
            n_estimators=n_estimators,
            max_depth=max_depth
        )

        # Step 4: Register model (only if quality gate passes)
        register_task = register_model(
            model_uri=train_task.outputs['model_uri'],
            model_name=model_name,
            accuracy=train_task.outputs['accuracy'],
            f1_score=train_task.outputs['f1_score'],
            min_accuracy=min_accuracy
        )


if __name__ == '__main__':
    # Compile pipeline
    compiler.Compiler().compile(
        pipeline_func=ml_training_pipeline,
        package_path='ml_training_pipeline.yaml'
    )
    print("✓ Pipeline compiled: ml_training_pipeline.yaml")
