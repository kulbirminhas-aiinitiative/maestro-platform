"""
Main Maestro ML Client - Unified interface for MLOps operations
"""

from typing import Optional
from pathlib import Path

from .config import Config
from .models.registry_client import ModelRegistryClient


class MaestroClient:
    """
    Main client for interacting with Maestro ML Platform

    This is the primary entry point for the SDK, providing access to:
    - Model Registry (models)
    - Experiments (experiments) - coming soon
    - Training Jobs (training) - coming soon
    - Deployments (deployment) - coming soon

    Example:
        >>> from maestro_ml import MaestroClient
        >>>
        >>> # Initialize with defaults (loads from environment)
        >>> client = MaestroClient()
        >>>
        >>> # Or with explicit configuration
        >>> client = MaestroClient(mlflow_uri="http://localhost:5000")
        >>>
        >>> # Use the model registry
        >>> models = client.models.list()
        >>> model = client.models.get("fraud-detector")
        >>> version = client.models.get_version("fraud-detector", "3")
        >>>
        >>> # Transition to production
        >>> client.models.transition_version_stage(
        ...     name="fraud-detector",
        ...     version="3",
        ...     stage="Production"
        ... )
    """

    def __init__(
        self,
        mlflow_uri: Optional[str] = None,
        mlflow_registry_uri: Optional[str] = None,
        namespace: Optional[str] = None,
        kube_context: Optional[str] = None,
        kube_config_path: Optional[Path] = None,
        api_url: Optional[str] = None,
        api_key: Optional[str] = None,
        config: Optional[Config] = None,
    ):
        """
        Initialize Maestro ML Client

        Args:
            mlflow_uri: MLflow tracking server URI
            mlflow_registry_uri: MLflow model registry URI (defaults to mlflow_uri)
            namespace: Kubernetes namespace
            kube_context: Kubernetes context name
            kube_config_path: Path to kubeconfig file
            api_url: Maestro ML Platform API URL
            api_key: API key for authentication
            config: Pre-configured Config object (takes precedence over individual params)

        Example:
            >>> # Load from environment
            >>> client = MaestroClient()
            >>>
            >>> # Explicit configuration
            >>> client = MaestroClient(
            ...     mlflow_uri="http://mlflow.example.com:5000",
            ...     namespace="production"
            ... )
            >>>
            >>> # Use existing config
            >>> config = Config.from_env()
            >>> client = MaestroClient(config=config)
        """
        # Load configuration
        if config:
            self.config = config
        else:
            # Try to load from environment first
            try:
                self.config = Config.from_env()
            except Exception:
                # Fall back to defaults
                self.config = Config()

            # Override with explicit parameters if provided
            if mlflow_uri:
                self.config.mlflow_uri = mlflow_uri
            if mlflow_registry_uri:
                self.config.mlflow_registry_uri = mlflow_registry_uri
            if namespace:
                self.config.namespace = namespace
            if kube_context:
                self.config.kube_context = kube_context
            if kube_config_path:
                self.config.kube_config_path = kube_config_path
            if api_url:
                self.config.api_url = api_url
            if api_key:
                self.config.api_key = api_key

        # Initialize sub-clients
        self._models: Optional[ModelRegistryClient] = None
        # TODO: Initialize other clients
        # self._experiments = None
        # self._training = None
        # self._deployment = None

    @property
    def models(self) -> ModelRegistryClient:
        """
        Access the Model Registry client

        Returns:
            ModelRegistryClient instance

        Example:
            >>> models = client.models.list()
            >>> model = client.models.get("my-model")
        """
        if self._models is None:
            self._models = ModelRegistryClient(self.config)
        return self._models

    # TODO: Add other client properties
    # @property
    # def experiments(self):
    #     """Access the Experiments client"""
    #     if self._experiments is None:
    #         self._experiments = ExperimentsClient(self.config)
    #     return self._experiments
    #
    # @property
    # def training(self):
    #     """Access the Training Jobs client"""
    #     if self._training is None:
    #         self._training = TrainingClient(self.config)
    #     return self._training
    #
    # @property
    # def deployment(self):
    #     """Access the Deployment client"""
    #     if self._deployment is None:
    #         self._deployment = DeploymentClient(self.config)
    #     return self._deployment

    def __repr__(self) -> str:
        """String representation of the client"""
        return f"MaestroClient(mlflow_uri={self.config.mlflow_uri}, namespace={self.config.namespace})"

    def __str__(self) -> str:
        """User-friendly string representation"""
        return self.__repr__()
