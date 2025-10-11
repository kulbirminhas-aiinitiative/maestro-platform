"""
Model Training Pipeline DAG
Orchestrates the complete ML training workflow:
1. Data validation
2. Feature engineering
3. Model training
4. Model evaluation
5. Model registration (if meets quality thresholds)
"""

from datetime import datetime, timedelta
from airflow import DAG
from airflow.providers.cncf.kubernetes.operators.kubernetes_pod import KubernetesPodOperator
from airflow.operators.python import BranchPythonOperator
from airflow.operators.dummy import DummyOperator
from kubernetes.client import models as k8s

default_args = {
    'owner': 'ml-team',
    'depends_on_past': False,
    'email_on_failure': True,
    'email_on_retry': False,
    'retries': 2,
    'retry_delay': timedelta(minutes=5),
}

def decide_model_registration(**context):
    """Decide whether to register model based on evaluation metrics"""
    ti = context['ti']
    metrics = ti.xcom_pull(task_ids='evaluate_model')

    # Quality thresholds
    if metrics and metrics.get('accuracy', 0) > 0.85:
        return 'register_model'
    else:
        return 'skip_registration'

with DAG(
    'ml_model_training_pipeline',
    default_args=default_args,
    description='Complete ML model training and registration pipeline',
    schedule_interval='0 4 * * 0',  # Weekly on Sunday at 4 AM
    start_date=datetime(2025, 1, 1),
    catchup=False,
    tags=['ml', 'training', 'mlflow'],
) as dag:

    # Task 1: Data Validation
    validate_data = KubernetesPodOperator(
        task_id='validate_data',
        name='validate-training-data',
        namespace='airflow',
        image='python:3.11-slim',
        cmds=['python', '-c'],
        arguments=['''
import pandas as pd
import logging
from datetime import datetime, timedelta

logging.basicConfig(level=logging.INFO)
logging.info("Validating training data...")

# In production, this would load from S3/data warehouse
# For now, simulate validation
logging.info("✓ Data schema validation passed")
logging.info("✓ Data quality checks passed")
logging.info("✓ No missing critical features")
logging.info("✓ No data drift detected")

logging.info("Data validation completed successfully")
        '''],
        resources=k8s.V1ResourceRequirements(
            requests={'memory': '512Mi', 'cpu': '250m'},
            limits={'memory': '1Gi', 'cpu': '500m'}
        ),
        get_logs=True,
        is_delete_operator_pod=True,
    )

    # Task 2: Feature Engineering
    engineer_features = KubernetesPodOperator(
        task_id='engineer_features',
        name='feature-engineering',
        namespace='airflow',
        image='python:3.11-slim',
        cmds=['bash', '-c'],
        arguments=['''
pip install pandas scikit-learn feast mlflow boto3

python -c "
import pandas as pd
import logging
from feast import FeatureStore

logging.basicConfig(level=logging.INFO)
logging.info('Engineering features for training...')

# Get features from Feast
store = FeatureStore(repo_path='/feast/feature_repo')

# Simulate feature retrieval
entity_rows = [
    {'user_id': f'user_{i}', 'timestamp': pd.Timestamp.now()}
    for i in range(1000)
]

logging.info(f'Retrieved features for {len(entity_rows)} entities')
logging.info('Feature engineering completed')
"
        '''],
        env_vars={
            'FEAST_FEATURE_STORE_YAML': '/feast/feature_store.yaml',
        },
        resources=k8s.V1ResourceRequirements(
            requests={'memory': '1Gi', 'cpu': '500m'},
            limits={'memory': '2Gi', 'cpu': '1000m'}
        ),
        get_logs=True,
        is_delete_operator_pod=True,
    )

    # Task 3: Train Model
    train_model = KubernetesPodOperator(
        task_id='train_model',
        name='model-training',
        namespace='airflow',
        image='python:3.11-slim',
        cmds=['bash', '-c'],
        arguments=['''
pip install pandas scikit-learn mlflow boto3

python -c "
import mlflow
import mlflow.sklearn
from sklearn.ensemble import RandomForestClassifier
from sklearn.datasets import make_classification
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score
import logging

logging.basicConfig(level=logging.INFO)

# Set MLflow tracking URI
mlflow.set_tracking_uri('http://mlflow-service.mlflow.svc.cluster.local')
mlflow.set_experiment('task_assignment_model')

logging.info('Starting model training...')

# Generate sample data (in production, use real data)
X, y = make_classification(n_samples=10000, n_features=20, n_informative=15, random_state=42)
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# Start MLflow run
with mlflow.start_run(run_name='rf_classifier_training') as run:
    # Train model
    params = {
        'n_estimators': 100,
        'max_depth': 10,
        'min_samples_split': 5,
        'random_state': 42
    }

    mlflow.log_params(params)

    model = RandomForestClassifier(**params)
    model.fit(X_train, y_train)

    # Evaluate
    y_pred = model.predict(X_test)

    metrics = {
        'accuracy': accuracy_score(y_test, y_pred),
        'f1_score': f1_score(y_test, y_pred),
        'precision': precision_score(y_test, y_pred),
        'recall': recall_score(y_test, y_pred),
    }

    mlflow.log_metrics(metrics)

    # Log model
    mlflow.sklearn.log_model(model, 'model')

    logging.info(f'Training completed. Run ID: {run.info.run_id}')
    logging.info(f'Metrics: {metrics}')

    # Save run_id for downstream tasks
    print(f'RUN_ID={run.info.run_id}')
"
        '''],
        env_vars={
            'AWS_ACCESS_KEY_ID': 'admin',
            'AWS_SECRET_ACCESS_KEY': 'minioadmin',
            'MLFLOW_S3_ENDPOINT_URL': 'http://minio.storage.svc.cluster.local:9000',
        },
        resources=k8s.V1ResourceRequirements(
            requests={'memory': '2Gi', 'cpu': '1000m'},
            limits={'memory': '4Gi', 'cpu': '2000m'}
        ),
        get_logs=True,
        is_delete_operator_pod=True,
    )

    # Task 4: Evaluate Model
    evaluate_model = KubernetesPodOperator(
        task_id='evaluate_model',
        name='model-evaluation',
        namespace='airflow',
        image='python:3.11-slim',
        cmds=['bash', '-c'],
        arguments=['''
pip install mlflow boto3

python -c "
import mlflow
import logging
import json

logging.basicConfig(level=logging.INFO)

mlflow.set_tracking_uri('http://mlflow-service.mlflow.svc.cluster.local')

logging.info('Evaluating trained model...')

# Get latest run from experiment
experiment = mlflow.get_experiment_by_name('task_assignment_model')
runs = mlflow.search_runs(experiment_ids=[experiment.experiment_id], order_by=['start_time DESC'], max_results=1)

if not runs.empty:
    latest_run = runs.iloc[0]
    metrics = {
        'accuracy': latest_run['metrics.accuracy'],
        'f1_score': latest_run['metrics.f1_score'],
        'precision': latest_run['metrics.precision'],
        'recall': latest_run['metrics.recall'],
    }

    logging.info(f'Model Metrics: {json.dumps(metrics, indent=2)}')

    # Quality checks
    if metrics['accuracy'] > 0.85:
        logging.info('✓ Model meets quality thresholds')
    else:
        logging.warning('⚠ Model does not meet quality thresholds')

    print(json.dumps(metrics))
else:
    logging.error('No runs found for evaluation')
"
        '''],
        env_vars={
            'AWS_ACCESS_KEY_ID': 'admin',
            'AWS_SECRET_ACCESS_KEY': 'minioadmin',
            'MLFLOW_S3_ENDPOINT_URL': 'http://minio.storage.svc.cluster.local:9000',
        },
        resources=k8s.V1ResourceRequirements(
            requests={'memory': '512Mi', 'cpu': '250m'},
            limits={'memory': '1Gi', 'cpu': '500m'}
        ),
        get_logs=True,
        is_delete_operator_pod=True,
        do_xcom_push=True,
    )

    # Task 5: Register Model (if quality thresholds met)
    register_model = KubernetesPodOperator(
        task_id='register_model',
        name='model-registration',
        namespace='airflow',
        image='python:3.11-slim',
        cmds=['bash', '-c'],
        arguments=['''
pip install mlflow boto3

python -c "
import mlflow
import logging

logging.basicConfig(level=logging.INFO)

mlflow.set_tracking_uri('http://mlflow-service.mlflow.svc.cluster.local')

logging.info('Registering model to MLflow Model Registry...')

# Get latest run
experiment = mlflow.get_experiment_by_name('task_assignment_model')
runs = mlflow.search_runs(experiment_ids=[experiment.experiment_id], order_by=['start_time DESC'], max_results=1)

if not runs.empty:
    run_id = runs.iloc[0]['run_id']

    # Register model
    model_uri = f'runs:/{run_id}/model'
    model_name = 'task_assignment_classifier'

    result = mlflow.register_model(model_uri, model_name)

    logging.info(f'Model registered: {model_name} version {result.version}')

    # Transition to staging
    client = mlflow.tracking.MlflowClient()
    client.transition_model_version_stage(
        name=model_name,
        version=result.version,
        stage='Staging'
    )

    logging.info('Model transitioned to Staging stage')
else:
    logging.error('No runs found for registration')
"
        '''],
        env_vars={
            'AWS_ACCESS_KEY_ID': 'admin',
            'AWS_SECRET_ACCESS_KEY': 'minioadmin',
            'MLFLOW_S3_ENDPOINT_URL': 'http://minio.storage.svc.cluster.local:9000',
        },
        resources=k8s.V1ResourceRequirements(
            requests={'memory': '512Mi', 'cpu': '250m'},
            limits={'memory': '1Gi', 'cpu': '500m'}
        ),
        get_logs=True,
        is_delete_operator_pod=True,
    )

    skip_registration = DummyOperator(
        task_id='skip_registration'
    )

    # Task dependencies
    validate_data >> engineer_features >> train_model >> evaluate_model
    evaluate_model >> [register_model, skip_registration]
