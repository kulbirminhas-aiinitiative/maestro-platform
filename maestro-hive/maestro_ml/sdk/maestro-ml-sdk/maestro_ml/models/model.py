"""
Model data classes for Maestro ML SDK
"""

from datetime import datetime
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field


class ModelVersion(BaseModel):
    """
    Represents a specific version of a model

    Attributes:
        name: Model name
        version: Version number/string
        run_id: MLflow run ID that created this version
        creation_timestamp: When the version was created
        current_stage: Current stage (None, Staging, Production, Archived)
        description: Optional description
        tags: User-defined tags
        status: Version status
        source: Source path of the model artifacts
    """

    name: str
    version: str
    run_id: Optional[str] = None
    creation_timestamp: Optional[datetime] = None
    last_updated_timestamp: Optional[datetime] = None
    current_stage: str = "None"
    description: Optional[str] = None
    tags: Dict[str, str] = Field(default_factory=dict)
    status: str = "READY"
    source: Optional[str] = None
    user_id: Optional[str] = None

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }

    def __str__(self) -> str:
        return f"ModelVersion(name={self.name}, version={self.version}, stage={self.current_stage})"

    def __repr__(self) -> str:
        return self.__str__()


class Model(BaseModel):
    """
    Represents a registered model in the model registry

    Attributes:
        name: Unique model name
        creation_timestamp: When the model was registered
        last_updated_timestamp: Last update time
        description: Optional description
        tags: User-defined tags
        latest_versions: List of latest model versions by stage
    """

    name: str
    creation_timestamp: Optional[datetime] = None
    last_updated_timestamp: Optional[datetime] = None
    description: Optional[str] = None
    tags: Dict[str, str] = Field(default_factory=dict)
    latest_versions: List[ModelVersion] = Field(default_factory=list)
    user_id: Optional[str] = None

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }

    @property
    def latest_version(self) -> Optional[ModelVersion]:
        """Get the latest version across all stages"""
        if not self.latest_versions:
            return None
        return max(self.latest_versions, key=lambda v: v.creation_timestamp or datetime.min)

    @property
    def production_version(self) -> Optional[ModelVersion]:
        """Get the current production version"""
        for version in self.latest_versions:
            if version.current_stage == "Production":
                return version
        return None

    @property
    def staging_version(self) -> Optional[ModelVersion]:
        """Get the current staging version"""
        for version in self.latest_versions:
            if version.current_stage == "Staging":
                return version
        return None

    def get_version(self, version: str) -> Optional[ModelVersion]:
        """Get a specific version by version number"""
        for v in self.latest_versions:
            if v.version == version:
                return v
        return None

    def __str__(self) -> str:
        return f"Model(name={self.name}, versions={len(self.latest_versions)})"

    def __repr__(self) -> str:
        return self.__str__()


class ModelSignature(BaseModel):
    """
    Model signature describing inputs and outputs

    Attributes:
        inputs: Input schema
        outputs: Output schema
        params: Optional parameter schema
    """

    inputs: Optional[Dict[str, Any]] = None
    outputs: Optional[Dict[str, Any]] = None
    params: Optional[Dict[str, Any]] = None


class ModelMetrics(BaseModel):
    """
    Model evaluation metrics

    Attributes:
        metrics: Dictionary of metric name to value
        timestamp: When metrics were computed
    """

    metrics: Dict[str, float] = Field(default_factory=dict)
    timestamp: Optional[datetime] = None

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }


class ModelArtifact(BaseModel):
    """
    Represents a model artifact (file/directory)

    Attributes:
        path: Relative path of the artifact
        is_dir: Whether the artifact is a directory
        file_size: Size in bytes (for files)
    """

    path: str
    is_dir: bool = False
    file_size: Optional[int] = None
