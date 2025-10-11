"""
Maestro ML SDK - Python client for Maestro ML Platform

A unified interface for MLOps operations including:
- Model registry and versioning
- Experiment tracking
- Training job management
- Model deployment
- Feature store access

Example:
    >>> from maestro_ml import MaestroClient
    >>> client = MaestroClient()
    >>> model = client.models.get("my-model", version="v1.0.0")
    >>> client.models.deploy(model, replicas=3)
"""

__version__ = "0.1.0"
__author__ = "Maestro ML Team"
__email__ = "platform@maestro-ml.io"

from .client import MaestroClient
from .config import Config
from .models.model import Model, ModelVersion
from .exceptions import (
    MaestroMLException,
    ModelNotFoundException,
    DeploymentException,
    TrainingException,
)

__all__ = [
    "MaestroClient",
    "Config",
    "Model",
    "ModelVersion",
    "MaestroMLException",
    "ModelNotFoundException",
    "DeploymentException",
    "TrainingException",
]
