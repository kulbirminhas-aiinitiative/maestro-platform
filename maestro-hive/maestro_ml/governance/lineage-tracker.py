#!/usr/bin/env python3
"""
Model Lineage Tracker
Tracks complete lineage: Dataset → Features → Model → Deployment
Integrates with MLflow, Feast, and Kubernetes
"""

import argparse
import json
from datetime import datetime
from typing import Dict, List, Optional
import mlflow
from mlflow.tracking import MlflowClient
import os


class ModelLineageTracker:
    """Track complete model lineage from data to deployment"""

    def __init__(self, tracking_uri: str = None):
        """
        Args:
            tracking_uri: MLflow tracking URI
        """
        self.tracking_uri = tracking_uri or os.environ.get(
            'MLFLOW_TRACKING_URI',
            'http://mlflow.ml-platform.svc.cluster.local:5000'
        )
        mlflow.set_tracking_uri(self.tracking_uri)
        self.client = MlflowClient()

    def track_data_lineage(
        self,
        run_id: str,
        dataset_name: str,
        dataset_version: str,
        data_source: str,
        data_schema: Dict,
        num_samples: int,
        validation_results: Optional[Dict] = None
    ):
        """
        Track dataset lineage

        Args:
            run_id: MLflow run ID
            dataset_name: Name of dataset
            dataset_version: Version of dataset
            data_source: Source location (S3, DB, etc.)
            data_schema: Data schema/structure
            num_samples: Number of samples
            validation_results: Data validation results
        """
        lineage = {
            'dataset_name': dataset_name,
            'dataset_version': dataset_version,
            'data_source': data_source,
            'data_schema': data_schema,
            'num_samples': num_samples,
            'validation_results': validation_results or {},
            'timestamp': datetime.now().isoformat()
        }

        # Log as tags and params
        self.client.set_tag(run_id, 'lineage.dataset_name', dataset_name)
        self.client.set_tag(run_id, 'lineage.dataset_version', dataset_version)
        self.client.set_tag(run_id, 'lineage.data_source', data_source)

        # Log as artifact
        with open(f'/tmp/data_lineage_{run_id}.json', 'w') as f:
            json.dump(lineage, f, indent=2)

        self.client.log_artifact(run_id, f'/tmp/data_lineage_{run_id}.json', 'lineage')

        print(f"✓ Data lineage tracked for dataset: {dataset_name} v{dataset_version}")

    def track_feature_lineage(
        self,
        run_id: str,
        feature_service: str,
        feature_view: str,
        features: List[str],
        feast_repo: str,
        feature_retrieval_stats: Optional[Dict] = None
    ):
        """
        Track feature engineering lineage

        Args:
            run_id: MLflow run ID
            feature_service: Feast feature service name
            feature_view: Feast feature view name
            features: List of feature names
            feast_repo: Feast repository path
            feature_retrieval_stats: Feature retrieval statistics
        """
        lineage = {
            'feature_service': feature_service,
            'feature_view': feature_view,
            'features': features,
            'feast_repo': feast_repo,
            'num_features': len(features),
            'feature_retrieval_stats': feature_retrieval_stats or {},
            'timestamp': datetime.now().isoformat()
        }

        # Log as tags
        self.client.set_tag(run_id, 'lineage.feature_service', feature_service)
        self.client.set_tag(run_id, 'lineage.feature_view', feature_view)
        self.client.set_tag(run_id, 'lineage.num_features', str(len(features)))

        # Log features list
        self.client.log_param(run_id, 'lineage.features', ','.join(features[:10]))  # First 10

        # Log as artifact
        with open(f'/tmp/feature_lineage_{run_id}.json', 'w') as f:
            json.dump(lineage, f, indent=2)

        self.client.log_artifact(run_id, f'/tmp/feature_lineage_{run_id}.json', 'lineage')

        print(f"✓ Feature lineage tracked: {len(features)} features from {feature_service}")

    def track_model_lineage(
        self,
        run_id: str,
        model_name: str,
        model_version: str,
        algorithm: str,
        hyperparameters: Dict,
        training_duration: float,
        code_version: str,
        dependencies: Dict
    ):
        """
        Track model training lineage

        Args:
            run_id: MLflow run ID
            model_name: Model name
            model_version: Model version
            algorithm: Algorithm used
            hyperparameters: Model hyperparameters
            training_duration: Training time in seconds
            code_version: Git commit hash or version
            dependencies: Python package dependencies
        """
        lineage = {
            'model_name': model_name,
            'model_version': model_version,
            'algorithm': algorithm,
            'hyperparameters': hyperparameters,
            'training_duration': training_duration,
            'code_version': code_version,
            'dependencies': dependencies,
            'timestamp': datetime.now().isoformat()
        }

        # Log as tags
        self.client.set_tag(run_id, 'lineage.model_name', model_name)
        self.client.set_tag(run_id, 'lineage.model_version', model_version)
        self.client.set_tag(run_id, 'lineage.algorithm', algorithm)
        self.client.set_tag(run_id, 'lineage.code_version', code_version)

        # Log hyperparameters
        for key, value in hyperparameters.items():
            self.client.log_param(run_id, f'hp.{key}', value)

        # Log as artifact
        with open(f'/tmp/model_lineage_{run_id}.json', 'w') as f:
            json.dump(lineage, f, indent=2)

        self.client.log_artifact(run_id, f'/tmp/model_lineage_{run_id}.json', 'lineage')

        print(f"✓ Model lineage tracked: {model_name} v{model_version} ({algorithm})")

    def track_deployment_lineage(
        self,
        run_id: str,
        deployment_name: str,
        deployment_env: str,
        deployment_time: str,
        deployment_config: Dict,
        endpoint_url: Optional[str] = None
    ):
        """
        Track model deployment lineage

        Args:
            run_id: MLflow run ID
            deployment_name: Deployment name (e.g., k8s deployment)
            deployment_env: Environment (staging, production)
            deployment_time: Deployment timestamp
            deployment_config: Deployment configuration
            endpoint_url: Inference endpoint URL
        """
        lineage = {
            'deployment_name': deployment_name,
            'deployment_env': deployment_env,
            'deployment_time': deployment_time,
            'deployment_config': deployment_config,
            'endpoint_url': endpoint_url,
            'timestamp': datetime.now().isoformat()
        }

        # Log as tags
        self.client.set_tag(run_id, 'lineage.deployment_name', deployment_name)
        self.client.set_tag(run_id, 'lineage.deployment_env', deployment_env)
        self.client.set_tag(run_id, 'lineage.deployment_time', deployment_time)

        if endpoint_url:
            self.client.set_tag(run_id, 'lineage.endpoint_url', endpoint_url)

        # Log as artifact
        with open(f'/tmp/deployment_lineage_{run_id}.json', 'w') as f:
            json.dump(lineage, f, indent=2)

        self.client.log_artifact(run_id, f'/tmp/deployment_lineage_{run_id}.json', 'lineage')

        print(f"✓ Deployment lineage tracked: {deployment_name} in {deployment_env}")

    def get_complete_lineage(self, run_id: str) -> Dict:
        """
        Get complete lineage for a model run

        Args:
            run_id: MLflow run ID

        Returns:
            Dict containing complete lineage
        """
        run = self.client.get_run(run_id)

        lineage = {
            'run_id': run_id,
            'experiment_id': run.info.experiment_id,
            'run_name': run.data.tags.get('mlflow.runName', 'unknown'),
            'status': run.info.status,
            'start_time': datetime.fromtimestamp(run.info.start_time / 1000).isoformat(),
            'end_time': datetime.fromtimestamp(run.info.end_time / 1000).isoformat() if run.info.end_time else None,
            'data': {},
            'features': {},
            'model': {},
            'deployment': {}
        }

        # Extract lineage from tags
        tags = run.data.tags

        # Data lineage
        if 'lineage.dataset_name' in tags:
            lineage['data'] = {
                'dataset_name': tags.get('lineage.dataset_name'),
                'dataset_version': tags.get('lineage.dataset_version'),
                'data_source': tags.get('lineage.data_source')
            }

        # Feature lineage
        if 'lineage.feature_service' in tags:
            lineage['features'] = {
                'feature_service': tags.get('lineage.feature_service'),
                'feature_view': tags.get('lineage.feature_view'),
                'num_features': tags.get('lineage.num_features')
            }

        # Model lineage
        if 'lineage.model_name' in tags:
            lineage['model'] = {
                'model_name': tags.get('lineage.model_name'),
                'model_version': tags.get('lineage.model_version'),
                'algorithm': tags.get('lineage.algorithm'),
                'code_version': tags.get('lineage.code_version')
            }

        # Deployment lineage
        if 'lineage.deployment_name' in tags:
            lineage['deployment'] = {
                'deployment_name': tags.get('lineage.deployment_name'),
                'deployment_env': tags.get('lineage.deployment_env'),
                'deployment_time': tags.get('lineage.deployment_time'),
                'endpoint_url': tags.get('lineage.endpoint_url')
            }

        # Metrics
        lineage['metrics'] = run.data.metrics

        # Parameters
        lineage['parameters'] = run.data.params

        return lineage

    def visualize_lineage(self, run_id: str):
        """
        Print visual representation of lineage

        Args:
            run_id: MLflow run ID
        """
        lineage = self.get_complete_lineage(run_id)

        print("\n" + "="*80)
        print(f"Model Lineage: {lineage['run_name']}")
        print("="*80)

        # Data lineage
        if lineage['data']:
            print("\n📊 Data:")
            print(f"  Dataset: {lineage['data']['dataset_name']} v{lineage['data']['dataset_version']}")
            print(f"  Source:  {lineage['data']['data_source']}")

        # Feature lineage
        if lineage['features']:
            print("\n🔧 Features:")
            print(f"  Service: {lineage['features']['feature_service']}")
            print(f"  View:    {lineage['features']['feature_view']}")
            print(f"  Count:   {lineage['features']['num_features']} features")

        # Model lineage
        if lineage['model']:
            print("\n🤖 Model:")
            print(f"  Name:      {lineage['model']['model_name']} v{lineage['model']['model_version']}")
            print(f"  Algorithm: {lineage['model']['algorithm']}")
            print(f"  Code:      {lineage['model']['code_version']}")

        # Deployment lineage
        if lineage['deployment']:
            print("\n🚀 Deployment:")
            print(f"  Name:     {lineage['deployment']['deployment_name']}")
            print(f"  Env:      {lineage['deployment']['deployment_env']}")
            print(f"  Time:     {lineage['deployment']['deployment_time']}")
            if lineage['deployment']['endpoint_url']:
                print(f"  Endpoint: {lineage['deployment']['endpoint_url']}")

        # Metrics
        if lineage['metrics']:
            print("\n📈 Metrics:")
            for key, value in list(lineage['metrics'].items())[:5]:  # Top 5
                print(f"  {key}: {value:.4f}")

        print("\n" + "="*80)


def main(args):
    tracker = ModelLineageTracker()

    if args.command == 'track':
        # Example: Track complete lineage for a training run
        with mlflow.start_run(run_name="example-lineage-tracking") as run:
            run_id = run.info.run_id

            # Track data lineage
            tracker.track_data_lineage(
                run_id=run_id,
                dataset_name="customer_churn",
                dataset_version="2024-01-15",
                data_source="s3://ml-data/customer_churn_2024.parquet",
                data_schema={"features": 20, "target": "churn"},
                num_samples=10000,
                validation_results={"valid_rows": 9950, "null_rows": 50}
            )

            # Track feature lineage
            tracker.track_feature_lineage(
                run_id=run_id,
                feature_service="customer_features_v1",
                feature_view="customer_demographics",
                features=["age", "tenure", "monthly_charges", "contract_type"],
                feast_repo="/feast/feature_repo"
            )

            # Track model lineage
            tracker.track_model_lineage(
                run_id=run_id,
                model_name="churn_predictor",
                model_version="1.2.0",
                algorithm="RandomForest",
                hyperparameters={"n_estimators": 100, "max_depth": 10},
                training_duration=45.3,
                code_version="abc123def",
                dependencies={"scikit-learn": "1.3.0", "pandas": "2.0.0"}
            )

            # Track deployment lineage
            tracker.track_deployment_lineage(
                run_id=run_id,
                deployment_name="churn-predictor-prod",
                deployment_env="production",
                deployment_time=datetime.now().isoformat(),
                deployment_config={"replicas": 3, "cpu": "1", "memory": "2Gi"},
                endpoint_url="http://churn-predictor.ml-platform.svc.cluster.local:8080/predict"
            )

            print(f"\n✅ Complete lineage tracked for run: {run_id}")

    elif args.command == 'get':
        # Get lineage for specific run
        lineage = tracker.get_complete_lineage(args.run_id)
        print(json.dumps(lineage, indent=2))

    elif args.command == 'visualize':
        # Visualize lineage
        tracker.visualize_lineage(args.run_id)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Model lineage tracking')
    subparsers = parser.add_subparsers(dest='command', help='Command to run')

    # Track command
    track_parser = subparsers.add_parser('track', help='Track lineage (example)')

    # Get command
    get_parser = subparsers.add_parser('get', help='Get lineage for run')
    get_parser.add_argument('--run-id', required=True, help='MLflow run ID')

    # Visualize command
    viz_parser = subparsers.add_parser('visualize', help='Visualize lineage')
    viz_parser.add_argument('--run-id', required=True, help='MLflow run ID')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
    else:
        main(args)
