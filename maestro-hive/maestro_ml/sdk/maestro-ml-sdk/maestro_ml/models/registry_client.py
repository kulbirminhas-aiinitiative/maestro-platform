"""
Model Registry Client - wraps MLflow Model Registry
"""

from typing import List, Optional, Dict
from datetime import datetime
import mlflow
from mlflow.tracking import MlflowClient
from mlflow.entities.model_registry import RegisteredModel, ModelVersion as MlflowModelVersion

from ..config import Config
from ..exceptions import ModelNotFoundException, ModelVersionNotFoundException, MLflowException
from .model import Model, ModelVersion


class ModelRegistryClient:
    """
    Client for interacting with the MLflow Model Registry

    Provides a simplified, Pythonic interface for common model registry operations.

    Example:
        >>> from maestro_ml import MaestroClient
        >>> client = MaestroClient()
        >>> models = client.models.list()
        >>> model = client.models.get("my-model")
        >>> version = client.models.get_version("my-model", "1")
    """

    def __init__(self, config: Config):
        """
        Initialize the Model Registry Client

        Args:
            config: Maestro ML configuration
        """
        self.config = config
        mlflow.set_tracking_uri(config.mlflow_uri)
        if config.mlflow_registry_uri:
            mlflow.set_registry_uri(config.mlflow_registry_uri)
        self.client = MlflowClient()

    def list(
        self,
        max_results: int = 100,
        filter_string: Optional[str] = None
    ) -> List[Model]:
        """
        List all registered models

        Args:
            max_results: Maximum number of models to return
            filter_string: Optional filter string (MLflow syntax)

        Returns:
            List of Model objects

        Example:
            >>> models = client.models.list(max_results=10)
            >>> filtered = client.models.list(filter_string="name LIKE '%fraud%'")
        """
        try:
            mlflow_models = self.client.search_registered_models(
                max_results=max_results,
                filter_string=filter_string
            )
            return [self._to_model(m) for m in mlflow_models]
        except Exception as e:
            raise MLflowException(f"Failed to list models: {str(e)}") from e

    def get(self, name: str) -> Model:
        """
        Get a registered model by name

        Args:
            name: Model name

        Returns:
            Model object

        Raises:
            ModelNotFoundException: If model doesn't exist

        Example:
            >>> model = client.models.get("fraud-detector")
            >>> print(model.description)
        """
        try:
            mlflow_model = self.client.get_registered_model(name)
            return self._to_model(mlflow_model)
        except mlflow.exceptions.MlflowException as e:
            if "RESOURCE_DOES_NOT_EXIST" in str(e):
                raise ModelNotFoundException(f"Model '{name}' not found") from e
            raise MLflowException(f"Failed to get model: {str(e)}") from e

    def get_version(self, name: str, version: str) -> ModelVersion:
        """
        Get a specific model version

        Args:
            name: Model name
            version: Version number

        Returns:
            ModelVersion object

        Raises:
            ModelVersionNotFoundException: If version doesn't exist

        Example:
            >>> version = client.models.get_version("fraud-detector", "3")
            >>> print(version.current_stage)
        """
        try:
            mlflow_version = self.client.get_model_version(name, version)
            return self._to_model_version(mlflow_version)
        except mlflow.exceptions.MlflowException as e:
            if "RESOURCE_DOES_NOT_EXIST" in str(e):
                raise ModelVersionNotFoundException(
                    f"Model version '{name}' v{version} not found"
                ) from e
            raise MLflowException(f"Failed to get model version: {str(e)}") from e

    def get_latest_versions(
        self,
        name: str,
        stages: Optional[List[str]] = None
    ) -> List[ModelVersion]:
        """
        Get the latest versions of a model by stage

        Args:
            name: Model name
            stages: List of stages to filter by (e.g., ["Production", "Staging"])

        Returns:
            List of ModelVersion objects

        Example:
            >>> prod_versions = client.models.get_latest_versions(
            ...     "fraud-detector",
            ...     stages=["Production"]
            ... )
        """
        try:
            mlflow_versions = self.client.get_latest_versions(name, stages=stages)
            return [self._to_model_version(v) for v in mlflow_versions]
        except mlflow.exceptions.MlflowException as e:
            raise MLflowException(f"Failed to get latest versions: {str(e)}") from e

    def create(self, name: str, description: Optional[str] = None, tags: Optional[Dict[str, str]] = None) -> Model:
        """
        Create a new registered model

        Args:
            name: Model name (must be unique)
            description: Optional description
            tags: Optional tags

        Returns:
            Created Model object

        Example:
            >>> model = client.models.create(
            ...     name="new-model",
            ...     description="My new model",
            ...     tags={"team": "data-science"}
            ... )
        """
        try:
            mlflow_model = self.client.create_registered_model(
                name=name,
                description=description,
                tags=tags or {}
            )
            return self._to_model(mlflow_model)
        except mlflow.exceptions.MlflowException as e:
            raise MLflowException(f"Failed to create model: {str(e)}") from e

    def update(
        self,
        name: str,
        description: Optional[str] = None
    ) -> Model:
        """
        Update a registered model

        Args:
            name: Model name
            description: New description

        Returns:
            Updated Model object

        Example:
            >>> model = client.models.update(
            ...     name="my-model",
            ...     description="Updated description"
            ... )
        """
        try:
            mlflow_model = self.client.update_registered_model(
                name=name,
                description=description
            )
            return self._to_model(mlflow_model)
        except mlflow.exceptions.MlflowException as e:
            raise MLflowException(f"Failed to update model: {str(e)}") from e

    def delete(self, name: str) -> None:
        """
        Delete a registered model

        Args:
            name: Model name

        Example:
            >>> client.models.delete("old-model")
        """
        try:
            self.client.delete_registered_model(name)
        except mlflow.exceptions.MlflowException as e:
            raise MLflowException(f"Failed to delete model: {str(e)}") from e

    def transition_version_stage(
        self,
        name: str,
        version: str,
        stage: str,
        archive_existing_versions: bool = False
    ) -> ModelVersion:
        """
        Transition a model version to a different stage

        Args:
            name: Model name
            version: Version number
            stage: Target stage (None, Staging, Production, Archived)
            archive_existing_versions: Archive existing versions in the target stage

        Returns:
            Updated ModelVersion

        Example:
            >>> version = client.models.transition_version_stage(
            ...     name="fraud-detector",
            ...     version="5",
            ...     stage="Production",
            ...     archive_existing_versions=True
            ... )
        """
        try:
            mlflow_version = self.client.transition_model_version_stage(
                name=name,
                version=version,
                stage=stage,
                archive_existing_versions=archive_existing_versions
            )
            return self._to_model_version(mlflow_version)
        except mlflow.exceptions.MlflowException as e:
            raise MLflowException(f"Failed to transition stage: {str(e)}") from e

    def set_version_tag(self, name: str, version: str, key: str, value: str) -> None:
        """
        Set a tag on a model version

        Args:
            name: Model name
            version: Version number
            key: Tag key
            value: Tag value

        Example:
            >>> client.models.set_version_tag("my-model", "1", "validated", "true")
        """
        try:
            self.client.set_model_version_tag(name, version, key, value)
        except mlflow.exceptions.MlflowException as e:
            raise MLflowException(f"Failed to set tag: {str(e)}") from e

    def delete_version_tag(self, name: str, version: str, key: str) -> None:
        """
        Delete a tag from a model version

        Args:
            name: Model name
            version: Version number
            key: Tag key

        Example:
            >>> client.models.delete_version_tag("my-model", "1", "validated")
        """
        try:
            self.client.delete_model_version_tag(name, version, key)
        except mlflow.exceptions.MlflowException as e:
            raise MLflowException(f"Failed to delete tag: {str(e)}") from e

    def search(self, filter_string: str, max_results: int = 100) -> List[Model]:
        """
        Search for models using filter syntax

        Args:
            filter_string: Filter string (MLflow syntax)
            max_results: Maximum results to return

        Returns:
            List of matching models

        Example:
            >>> models = client.models.search(
            ...     "tags.team = 'fraud-detection'",
            ...     max_results=50
            ... )
        """
        return self.list(max_results=max_results, filter_string=filter_string)

    # Helper methods to convert MLflow objects to SDK objects

    def _to_model(self, mlflow_model: RegisteredModel) -> Model:
        """Convert MLflow RegisteredModel to SDK Model"""
        return Model(
            name=mlflow_model.name,
            creation_timestamp=datetime.fromtimestamp(mlflow_model.creation_timestamp / 1000)
            if mlflow_model.creation_timestamp
            else None,
            last_updated_timestamp=datetime.fromtimestamp(mlflow_model.last_updated_timestamp / 1000)
            if mlflow_model.last_updated_timestamp
            else None,
            description=mlflow_model.description,
            tags=mlflow_model.tags or {},
            latest_versions=[
                self._to_model_version(v) for v in (mlflow_model.latest_versions or [])
            ],
        )

    def _to_model_version(self, mlflow_version: MlflowModelVersion) -> ModelVersion:
        """Convert MLflow ModelVersion to SDK ModelVersion"""
        return ModelVersion(
            name=mlflow_version.name,
            version=mlflow_version.version,
            run_id=mlflow_version.run_id,
            creation_timestamp=datetime.fromtimestamp(mlflow_version.creation_timestamp / 1000)
            if mlflow_version.creation_timestamp
            else None,
            last_updated_timestamp=datetime.fromtimestamp(mlflow_version.last_updated_timestamp / 1000)
            if mlflow_version.last_updated_timestamp
            else None,
            current_stage=mlflow_version.current_stage,
            description=mlflow_version.description,
            tags=mlflow_version.tags or {},
            status=mlflow_version.status,
            source=mlflow_version.source,
            user_id=mlflow_version.user_id,
        )
