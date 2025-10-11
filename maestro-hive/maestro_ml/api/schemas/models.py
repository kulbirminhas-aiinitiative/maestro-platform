"""
Model Registry API Schemas
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class ModelVersionResponse(BaseModel):
    """Model version information"""
    name: str = Field(..., description="Model name")
    version: str = Field(..., description="Model version")
    creation_timestamp: Optional[datetime] = Field(None, description="Creation timestamp")
    last_updated_timestamp: Optional[datetime] = Field(None, description="Last updated timestamp")
    current_stage: str = Field(..., description="Current stage (Production, Staging, etc.)")
    description: Optional[str] = Field(None, description="Version description")
    user_id: Optional[str] = Field(None, description="User who created this version")
    source: Optional[str] = Field(None, description="Source path")
    run_id: Optional[str] = Field(None, description="MLflow run ID")
    status: str = Field(..., description="Version status")
    tags: Dict[str, str] = Field(default_factory=dict, description="Version tags")


class ModelResponse(BaseModel):
    """Model information"""
    name: str = Field(..., description="Model name")
    creation_timestamp: Optional[datetime] = Field(None, description="Creation timestamp")
    last_updated_timestamp: Optional[datetime] = Field(None, description="Last updated timestamp")
    description: Optional[str] = Field(None, description="Model description")
    tags: Dict[str, str] = Field(default_factory=dict, description="Model tags")
    latest_versions: List[ModelVersionResponse] = Field(
        default_factory=list,
        description="Latest versions of the model"
    )


class ModelListResponse(BaseModel):
    """List of models"""
    models: List[ModelResponse] = Field(..., description="List of models")
    total: int = Field(..., description="Total number of models")


class ModelCreateRequest(BaseModel):
    """Request to create a new model"""
    name: str = Field(..., description="Model name", min_length=1, max_length=255)
    description: Optional[str] = Field(None, description="Model description")
    tags: Optional[Dict[str, str]] = Field(None, description="Model tags")


class ModelUpdateRequest(BaseModel):
    """Request to update model metadata"""
    description: Optional[str] = Field(None, description="Updated description")


class StageTransitionRequest(BaseModel):
    """Request to transition model version stage"""
    stage: str = Field(
        ...,
        description="Target stage",
        pattern="^(Staging|Production|Archived|None)$"
    )
    archive_existing_versions: bool = Field(
        default=False,
        description="Archive existing versions in target stage"
    )


class TagRequest(BaseModel):
    """Request to set a tag"""
    key: str = Field(..., description="Tag key", min_length=1)
    value: str = Field(..., description="Tag value")
