"""
Configuration management for Maestro ML SDK
"""

import os
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv
from pydantic import BaseModel, Field, field_validator

from .exceptions import ConfigurationException


class Config(BaseModel):
    """
    Configuration for Maestro ML SDK

    Can be loaded from:
    1. Environment variables (MAESTRO_ML_*)
    2. .env file
    3. Explicit parameters

    Example:
        >>> config = Config()  # Load from environment
        >>> config = Config(mlflow_uri="http://localhost:5000")  # Explicit
    """

    # MLflow configuration
    mlflow_uri: str = Field(
        default="http://localhost:5000",
        description="MLflow tracking server URI"
    )
    mlflow_registry_uri: Optional[str] = Field(
        default=None,
        description="MLflow model registry URI (defaults to mlflow_uri)"
    )

    # Kubernetes configuration
    kube_context: Optional[str] = Field(
        default=None,
        description="Kubernetes context name"
    )
    kube_config_path: Optional[Path] = Field(
        default=None,
        description="Path to kubeconfig file"
    )
    namespace: str = Field(
        default="ml-platform",
        description="Kubernetes namespace for ML resources"
    )

    # API configuration
    api_url: Optional[str] = Field(
        default=None,
        description="Maestro ML Platform API URL"
    )
    api_key: Optional[str] = Field(
        default=None,
        description="API key for authentication"
    )

    # Timeouts
    request_timeout: int = Field(
        default=30,
        description="Request timeout in seconds",
        ge=1
    )
    training_job_timeout: int = Field(
        default=3600,
        description="Training job wait timeout in seconds",
        ge=1
    )

    # Feature flags
    verify_ssl: bool = Field(
        default=True,
        description="Verify SSL certificates"
    )
    verbose: bool = Field(
        default=False,
        description="Enable verbose logging"
    )

    class Config:
        env_prefix = "MAESTRO_ML_"
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False

    @classmethod
    def from_env(cls, env_file: Optional[Path] = None) -> "Config":
        """
        Load configuration from environment variables and .env file

        Args:
            env_file: Path to .env file (optional)

        Returns:
            Config instance

        Example:
            >>> config = Config.from_env()
            >>> config = Config.from_env(env_file=Path(".env.production"))
        """
        if env_file and env_file.exists():
            load_dotenv(env_file)
        else:
            load_dotenv()  # Load from .env in current directory

        return cls(
            mlflow_uri=os.getenv("MAESTRO_ML_MLFLOW_URI", "http://localhost:5000"),
            mlflow_registry_uri=os.getenv("MAESTRO_ML_MLFLOW_REGISTRY_URI"),
            kube_context=os.getenv("MAESTRO_ML_KUBE_CONTEXT"),
            kube_config_path=Path(os.getenv("MAESTRO_ML_KUBE_CONFIG_PATH", "~/.kube/config")).expanduser(),
            namespace=os.getenv("MAESTRO_ML_NAMESPACE", "ml-platform"),
            api_url=os.getenv("MAESTRO_ML_API_URL"),
            api_key=os.getenv("MAESTRO_ML_API_KEY"),
            request_timeout=int(os.getenv("MAESTRO_ML_REQUEST_TIMEOUT", "30")),
            training_job_timeout=int(os.getenv("MAESTRO_ML_TRAINING_JOB_TIMEOUT", "3600")),
            verify_ssl=os.getenv("MAESTRO_ML_VERIFY_SSL", "true").lower() == "true",
            verbose=os.getenv("MAESTRO_ML_VERBOSE", "false").lower() == "true",
        )

    @field_validator("mlflow_uri")
    @classmethod
    def validate_mlflow_uri(cls, v: str) -> str:
        """Validate MLflow URI format"""
        if not v:
            raise ConfigurationException("mlflow_uri cannot be empty")
        if not v.startswith(("http://", "https://", "file://")):
            raise ConfigurationException(
                f"Invalid mlflow_uri: {v}. Must start with http://, https://, or file://"
            )
        return v

    @field_validator("kube_config_path")
    @classmethod
    def validate_kube_config(cls, v: Optional[Path]) -> Optional[Path]:
        """Validate kubeconfig file exists"""
        if v:
            expanded = v.expanduser()
            if not expanded.exists():
                raise ConfigurationException(
                    f"Kubernetes config file not found: {expanded}"
                )
            return expanded
        return v

    def __str__(self) -> str:
        """String representation hiding sensitive data"""
        return (
            f"Config(\n"
            f"  mlflow_uri={self.mlflow_uri}\n"
            f"  namespace={self.namespace}\n"
            f"  api_url={self.api_url}\n"
            f"  api_key={'***' if self.api_key else None}\n"
            f")"
        )
