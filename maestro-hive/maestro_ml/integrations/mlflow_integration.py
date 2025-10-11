"""
Enhanced MLflow Integration for Maestro ML Platform

Features:
- Automatic experiment tracking
- Model versioning and registry
- Artifact management
- Metrics comparison
- Model deployment integration
"""

import os
from typing import Dict, Any, Optional, List
from datetime import datetime
import mlflow
from mlflow.tracking import MlflowClient
from mlflow.entities import ViewType
import logging

logger = logging.getLogger(__name__)


class MaestroMLflowIntegration:
    """
    Enhanced MLflow integration for Maestro ML Platform

    Usage:
        integration = MaestroMLflowIntegration(
            tracking_uri="http://mlflow:5000",
            registry_uri="http://mlflow:5000"
        )

        # Start experiment
        with integration.start_run(experiment_name="my_experiment") as run:
            integration.log_params({"lr": 0.01})
            integration.log_metrics({"accuracy": 0.95})
            integration.log_model(model, "sklearn_model")
    """

    def __init__(
        self,
        tracking_uri: Optional[str] = None,
        registry_uri: Optional[str] = None,
        experiment_name: Optional[str] = None,
        artifact_location: Optional[str] = None
    ):
        """
        Initialize MLflow integration

        Args:
            tracking_uri: MLflow tracking server URI
            registry_uri: MLflow model registry URI
            experiment_name: Default experiment name
            artifact_location: Default artifact storage location
        """
        self.tracking_uri = tracking_uri or os.getenv("MLFLOW_TRACKING_URI", "http://localhost:5000")
        self.registry_uri = registry_uri or tracking_uri or os.getenv("MLFLOW_REGISTRY_URI")
        self.experiment_name = experiment_name
        self.artifact_location = artifact_location

        # Set MLflow URIs
        mlflow.set_tracking_uri(self.tracking_uri)
        if self.registry_uri:
            mlflow.set_registry_uri(self.registry_uri)

        # Initialize client
        self.client = MlflowClient(
            tracking_uri=self.tracking_uri,
            registry_uri=self.registry_uri
        )

        logger.info(f"MLflow integration initialized: {self.tracking_uri}")

    def create_experiment(
        self,
        experiment_name: str,
        artifact_location: Optional[str] = None,
        tags: Optional[Dict[str, str]] = None
    ) -> str:
        """
        Create MLflow experiment

        Args:
            experiment_name: Name of experiment
            artifact_location: Storage location for artifacts
            tags: Experiment tags

        Returns:
            experiment_id: ID of created/existing experiment
        """
        try:
            experiment = self.client.get_experiment_by_name(experiment_name)
            if experiment:
                logger.info(f"Using existing experiment: {experiment_name}")
                return experiment.experiment_id
        except:
            pass

        experiment_id = self.client.create_experiment(
            name=experiment_name,
            artifact_location=artifact_location or self.artifact_location,
            tags=tags or {}
        )

        logger.info(f"Created experiment: {experiment_name} (ID: {experiment_id})")
        return experiment_id

    def start_run(
        self,
        experiment_name: Optional[str] = None,
        run_name: Optional[str] = None,
        tags: Optional[Dict[str, str]] = None,
        nested: bool = False
    ):
        """
        Start MLflow run

        Args:
            experiment_name: Experiment name
            run_name: Run name
            tags: Run tags
            nested: Whether this is a nested run

        Returns:
            ActiveRun context manager
        """
        exp_name = experiment_name or self.experiment_name

        if exp_name:
            mlflow.set_experiment(exp_name)

        return mlflow.start_run(
            run_name=run_name,
            tags=tags,
            nested=nested
        )

    def log_params(self, params: Dict[str, Any]):
        """Log parameters to current run"""
        mlflow.log_params(params)
        logger.debug(f"Logged {len(params)} parameters")

    def log_param(self, key: str, value: Any):
        """Log single parameter"""
        mlflow.log_param(key, value)

    def log_metrics(
        self,
        metrics: Dict[str, float],
        step: Optional[int] = None
    ):
        """
        Log metrics to current run

        Args:
            metrics: Dictionary of metric name -> value
            step: Optional step number for time series
        """
        mlflow.log_metrics(metrics, step=step)
        logger.debug(f"Logged {len(metrics)} metrics")

    def log_metric(
        self,
        key: str,
        value: float,
        step: Optional[int] = None
    ):
        """Log single metric"""
        mlflow.log_metric(key, value, step=step)

    def log_artifact(self, local_path: str, artifact_path: Optional[str] = None):
        """
        Log artifact file

        Args:
            local_path: Local file path
            artifact_path: Path within artifact store
        """
        mlflow.log_artifact(local_path, artifact_path)
        logger.debug(f"Logged artifact: {local_path}")

    def log_artifacts(self, local_dir: str, artifact_path: Optional[str] = None):
        """
        Log directory of artifacts

        Args:
            local_dir: Local directory path
            artifact_path: Path within artifact store
        """
        mlflow.log_artifacts(local_dir, artifact_path)
        logger.debug(f"Logged artifacts from: {local_dir}")

    def log_model(
        self,
        model: Any,
        artifact_path: str,
        registered_model_name: Optional[str] = None,
        **kwargs
    ):
        """
        Log ML model

        Args:
            model: Model object (sklearn, pytorch, tensorflow, etc.)
            artifact_path: Path to store model
            registered_model_name: Name for model registry
            **kwargs: Additional arguments for specific model flavor
        """
        # Auto-detect model type and use appropriate log function
        model_type = type(model).__module__

        if "sklearn" in model_type:
            mlflow.sklearn.log_model(
                model,
                artifact_path,
                registered_model_name=registered_model_name,
                **kwargs
            )
        elif "pytorch" in model_type or "torch" in model_type:
            mlflow.pytorch.log_model(
                model,
                artifact_path,
                registered_model_name=registered_model_name,
                **kwargs
            )
        elif "tensorflow" in model_type or "keras" in model_type:
            mlflow.tensorflow.log_model(
                model,
                artifact_path,
                registered_model_name=registered_model_name,
                **kwargs
            )
        elif "xgboost" in model_type:
            mlflow.xgboost.log_model(
                model,
                artifact_path,
                registered_model_name=registered_model_name,
                **kwargs
            )
        elif "lightgbm" in model_type:
            mlflow.lightgbm.log_model(
                model,
                artifact_path,
                registered_model_name=registered_model_name,
                **kwargs
            )
        else:
            # Generic Python model
            mlflow.pyfunc.log_model(
                artifact_path,
                python_model=model,
                registered_model_name=registered_model_name,
                **kwargs
            )

        logger.info(f"Logged model to: {artifact_path}")

    def load_model(self, model_uri: str) -> Any:
        """
        Load model from MLflow

        Args:
            model_uri: Model URI (runs:/run_id/path or models:/name/version)

        Returns:
            Loaded model object
        """
        model = mlflow.pyfunc.load_model(model_uri)
        logger.info(f"Loaded model from: {model_uri}")
        return model

    def register_model(
        self,
        model_uri: str,
        name: str,
        tags: Optional[Dict[str, str]] = None,
        description: Optional[str] = None
    ):
        """
        Register model in model registry

        Args:
            model_uri: URI of model to register
            name: Model name
            tags: Model tags
            description: Model description

        Returns:
            ModelVersion object
        """
        # Register model
        model_version = mlflow.register_model(model_uri, name)

        # Add tags if provided
        if tags:
            for key, value in tags.items():
                self.client.set_model_version_tag(
                    name,
                    model_version.version,
                    key,
                    value
                )

        # Add description if provided
        if description:
            self.client.update_model_version(
                name,
                model_version.version,
                description=description
            )

        logger.info(f"Registered model: {name} version {model_version.version}")
        return model_version

    def transition_model_stage(
        self,
        name: str,
        version: int,
        stage: str,
        archive_existing_versions: bool = False
    ):
        """
        Transition model to new stage

        Args:
            name: Model name
            version: Model version
            stage: Target stage (Staging, Production, Archived)
            archive_existing_versions: Archive current versions in target stage
        """
        self.client.transition_model_version_stage(
            name=name,
            version=version,
            stage=stage,
            archive_existing_versions=archive_existing_versions
        )

        logger.info(f"Transitioned {name} v{version} to {stage}")

    def get_experiment_runs(
        self,
        experiment_name: str,
        filter_string: Optional[str] = None,
        order_by: Optional[List[str]] = None,
        max_results: int = 100
    ) -> List[mlflow.entities.Run]:
        """
        Get runs for an experiment

        Args:
            experiment_name: Name of experiment
            filter_string: Filter string (e.g., "metrics.accuracy > 0.9")
            order_by: List of order by clauses
            max_results: Maximum number of results

        Returns:
            List of Run objects
        """
        experiment = self.client.get_experiment_by_name(experiment_name)

        if not experiment:
            raise ValueError(f"Experiment not found: {experiment_name}")

        runs = self.client.search_runs(
            experiment_ids=[experiment.experiment_id],
            filter_string=filter_string,
            order_by=order_by,
            max_results=max_results
        )

        return runs

    def get_best_run(
        self,
        experiment_name: str,
        metric_name: str,
        mode: str = "max"
    ) -> Optional[mlflow.entities.Run]:
        """
        Get best run based on metric

        Args:
            experiment_name: Name of experiment
            metric_name: Metric to optimize
            mode: "max" or "min"

        Returns:
            Best run or None
        """
        order = "DESC" if mode == "max" else "ASC"

        runs = self.get_experiment_runs(
            experiment_name,
            order_by=[f"metrics.{metric_name} {order}"],
            max_results=1
        )

        return runs[0] if runs else None

    def compare_runs(
        self,
        run_ids: List[str]
    ) -> Dict[str, Any]:
        """
        Compare multiple runs

        Args:
            run_ids: List of run IDs to compare

        Returns:
            Comparison data with params and metrics
        """
        comparison = {
            "runs": {},
            "params": {},
            "metrics": {}
        }

        for run_id in run_ids:
            run = self.client.get_run(run_id)

            comparison["runs"][run_id] = {
                "name": run.info.run_name,
                "start_time": run.info.start_time,
                "status": run.info.status
            }

            # Collect params
            for param, value in run.data.params.items():
                if param not in comparison["params"]:
                    comparison["params"][param] = {}
                comparison["params"][param][run_id] = value

            # Collect metrics
            for metric, value in run.data.metrics.items():
                if metric not in comparison["metrics"]:
                    comparison["metrics"][metric] = {}
                comparison["metrics"][metric][run_id] = value

        return comparison

    def get_model_versions(
        self,
        model_name: str,
        stages: Optional[List[str]] = None
    ) -> List[mlflow.entities.model_registry.ModelVersion]:
        """
        Get model versions

        Args:
            model_name: Name of model
            stages: Filter by stages (e.g., ["Production", "Staging"])

        Returns:
            List of ModelVersion objects
        """
        filter_string = f"name='{model_name}'"

        versions = self.client.search_model_versions(filter_string)

        if stages:
            versions = [v for v in versions if v.current_stage in stages]

        return versions

    def get_production_model(self, model_name: str) -> Optional[Any]:
        """
        Load production model

        Args:
            model_name: Name of model

        Returns:
            Loaded production model or None
        """
        versions = self.get_model_versions(model_name, stages=["Production"])

        if not versions:
            logger.warning(f"No production model found: {model_name}")
            return None

        # Get latest production version
        latest_version = max(versions, key=lambda v: int(v.version))

        model_uri = f"models:/{model_name}/{latest_version.version}"
        return self.load_model(model_uri)


# Convenience decorator for automatic experiment tracking
def track_with_mlflow(
    experiment_name: str,
    tracking_uri: Optional[str] = None
):
    """
    Decorator to automatically track function with MLflow

    Usage:
        @track_with_mlflow("my_experiment")
        def train_model(lr=0.01, epochs=10):
            # Training code
            return {"accuracy": 0.95}
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            integration = MaestroMLflowIntegration(
                tracking_uri=tracking_uri,
                experiment_name=experiment_name
            )

            with integration.start_run(run_name=func.__name__) as run:
                # Log function parameters
                integration.log_params(kwargs)

                # Execute function
                result = func(*args, **kwargs)

                # Log results as metrics if dict
                if isinstance(result, dict):
                    metrics = {k: v for k, v in result.items() if isinstance(v, (int, float))}
                    if metrics:
                        integration.log_metrics(metrics)

                return result

        return wrapper
    return decorator
