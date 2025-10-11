"""
Model Registry API Endpoints
"""

from fastapi import APIRouter, HTTPException, Query, Depends
from typing import List, Optional
from datetime import datetime
import mlflow
from mlflow.tracking import MlflowClient
from mlflow.exceptions import MlflowException

from ..config import settings
from ..schemas.models import (
    ModelResponse,
    ModelVersionResponse,
    ModelListResponse,
    ModelCreateRequest,
    ModelUpdateRequest,
    StageTransitionRequest,
    TagRequest,
)
from ..schemas.common import SuccessResponse, ErrorResponse
from ..dependencies.rbac import require_permissions
from ..dependencies.tenant import TenantAwareMLflowClient, get_tenant_aware_mlflow_client
from ...enterprise.rbac.permissions import Permission

router = APIRouter(prefix="/models", tags=["models"])


def convert_model_version(mv) -> ModelVersionResponse:
    """Convert MLflow ModelVersion to API response"""
    return ModelVersionResponse(
        name=mv.name,
        version=mv.version,
        creation_timestamp=datetime.fromtimestamp(mv.creation_timestamp / 1000) if mv.creation_timestamp else None,
        last_updated_timestamp=datetime.fromtimestamp(mv.last_updated_timestamp / 1000) if mv.last_updated_timestamp else None,
        current_stage=mv.current_stage,
        description=mv.description,
        user_id=mv.user_id,
        source=mv.source,
        run_id=mv.run_id,
        status=mv.status,
        tags=dict(mv.tags) if mv.tags else {}
    )


def convert_model(model) -> ModelResponse:
    """Convert MLflow RegisteredModel to API response"""
    from datetime import datetime

    return ModelResponse(
        name=model.name,
        creation_timestamp=datetime.fromtimestamp(model.creation_timestamp / 1000) if model.creation_timestamp else None,
        last_updated_timestamp=datetime.fromtimestamp(model.last_updated_timestamp / 1000) if model.last_updated_timestamp else None,
        description=model.description,
        tags=dict(model.tags) if model.tags else {},
        latest_versions=[convert_model_version(v) for v in (model.latest_versions or [])]
    )


@router.get("/", response_model=ModelListResponse, dependencies=[Depends(require_permissions(Permission.MODEL_VIEW))])
async def list_models(
    max_results: int = Query(100, ge=1, le=1000, description="Maximum number of models to return"),
    filter_string: Optional[str] = Query(None, description="MLflow filter string"),
    client: TenantAwareMLflowClient = Depends(get_tenant_aware_mlflow_client)
):
    """
    List all registered models

    - **max_results**: Maximum number of models to return (1-1000)
    - **filter_string**: Optional MLflow filter (e.g., "name LIKE '%fraud%'")
    """
    try:
        models = client.search_registered_models(
            max_results=max_results,
            filter_string=filter_string
        )

        return ModelListResponse(
            models=[convert_model(m) for m in models],
            total=len(models)
        )
    except MlflowException as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{name}", response_model=ModelResponse, dependencies=[Depends(require_permissions(Permission.MODEL_VIEW))])
async def get_model(
    name: str,
    client: TenantAwareMLflowClient = Depends(get_tenant_aware_mlflow_client)
):
    """
    Get model details by name

    - **name**: Registered model name
    """
    try:
        model = client.get_registered_model(name)
        return convert_model(model)
    except MlflowException as e:
        if "RESOURCE_DOES_NOT_EXIST" in str(e):
            raise HTTPException(status_code=404, detail=f"Model '{name}' not found")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/", response_model=ModelResponse, status_code=201, dependencies=[Depends(require_permissions(Permission.MODEL_CREATE))])
async def create_model(
    request: ModelCreateRequest,
    client: TenantAwareMLflowClient = Depends(get_tenant_aware_mlflow_client)
):
    """
    Create a new registered model

    - **name**: Unique model name
    - **description**: Optional model description
    - **tags**: Optional key-value tags
    """
    try:
        model = client.create_registered_model(
            name=request.name,
            tags=request.tags,
            description=request.description
        )
        return convert_model(model)
    except MlflowException as e:
        if "RESOURCE_ALREADY_EXISTS" in str(e):
            raise HTTPException(status_code=409, detail=f"Model '{request.name}' already exists")
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/{name}", response_model=ModelResponse, dependencies=[Depends(require_permissions(Permission.MODEL_UPDATE))])
async def update_model(
    name: str,
    request: ModelUpdateRequest,
    client: TenantAwareMLflowClient = Depends(get_tenant_aware_mlflow_client)
):
    """
    Update model metadata

    - **name**: Model name
    - **description**: Updated description
    """
    try:
        if request.description is not None:
            client.update_registered_model(
                name=name,
                description=request.description
            )

        model = client.get_registered_model(name)
        return convert_model(model)
    except MlflowException as e:
        if "RESOURCE_DOES_NOT_EXIST" in str(e):
            raise HTTPException(status_code=404, detail=f"Model '{name}' not found")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{name}", response_model=SuccessResponse, dependencies=[Depends(require_permissions(Permission.MODEL_DELETE))])
async def delete_model(
    name: str,
    client: TenantAwareMLflowClient = Depends(get_tenant_aware_mlflow_client)
):
    """
    Delete a registered model

    - **name**: Model name to delete
    """
    try:
        client.delete_registered_model(name)
        return SuccessResponse(
            success=True,
            message=f"Model '{name}' deleted successfully"
        )
    except MlflowException as e:
        if "RESOURCE_DOES_NOT_EXIST" in str(e):
            raise HTTPException(status_code=404, detail=f"Model '{name}' not found")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{name}/versions", response_model=List[ModelVersionResponse], dependencies=[Depends(require_permissions(Permission.MODEL_VIEW))])
async def get_model_versions(
    name: str,
    stages: Optional[List[str]] = Query(None, description="Filter by stages"),
    client: TenantAwareMLflowClient = Depends(get_tenant_aware_mlflow_client)
):
    """
    Get all versions of a model

    - **name**: Model name
    - **stages**: Optional list of stages to filter (Production, Staging, etc.)
    """
    try:
        versions = client.get_latest_versions(name, stages=stages)
        return [convert_model_version(v) for v in versions]
    except MlflowException as e:
        if "RESOURCE_DOES_NOT_EXIST" in str(e):
            raise HTTPException(status_code=404, detail=f"Model '{name}' not found")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{name}/versions/{version}", response_model=ModelVersionResponse, dependencies=[Depends(require_permissions(Permission.MODEL_VIEW))])
async def get_model_version(
    name: str,
    version: str,
    client: TenantAwareMLflowClient = Depends(get_tenant_aware_mlflow_client)
):
    """
    Get specific model version

    - **name**: Model name
    - **version**: Model version
    """
    try:
        model_version = client.get_model_version(name, version)
        return convert_model_version(model_version)
    except MlflowException as e:
        if "RESOURCE_DOES_NOT_EXIST" in str(e):
            raise HTTPException(
                status_code=404,
                detail=f"Model version '{name}' v{version} not found"
            )
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{name}/versions/{version}/stage", response_model=ModelVersionResponse, dependencies=[Depends(require_permissions(Permission.MODEL_DEPLOY))])
async def transition_stage(
    name: str,
    version: str,
    request: StageTransitionRequest,
    client: TenantAwareMLflowClient = Depends(get_tenant_aware_mlflow_client)
):
    """
    Transition model version to a new stage

    - **name**: Model name
    - **version**: Model version
    - **stage**: Target stage (Staging, Production, Archived, None)
    - **archive_existing_versions**: Archive existing versions in target stage
    """
    try:
        model_version = client.transition_model_version_stage(
            name=name,
            version=version,
            stage=request.stage,
            archive_existing_versions=request.archive_existing_versions
        )
        return convert_model_version(model_version)
    except MlflowException as e:
        if "RESOURCE_DOES_NOT_EXIST" in str(e):
            raise HTTPException(
                status_code=404,
                detail=f"Model version '{name}' v{version} not found"
            )
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{name}/tags", response_model=SuccessResponse, dependencies=[Depends(require_permissions(Permission.MODEL_UPDATE))])
async def set_model_tag(
    name: str,
    request: TagRequest,
    client: TenantAwareMLflowClient = Depends(get_tenant_aware_mlflow_client)
):
    """
    Set a tag on a model

    - **name**: Model name
    - **key**: Tag key
    - **value**: Tag value
    """
    try:
        client.set_registered_model_tag(name, request.key, request.value)
        return SuccessResponse(
            success=True,
            message=f"Tag '{request.key}' set on model '{name}'"
        )
    except MlflowException as e:
        if "RESOURCE_DOES_NOT_EXIST" in str(e):
            raise HTTPException(status_code=404, detail=f"Model '{name}' not found")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{name}/tags/{key}", response_model=SuccessResponse, dependencies=[Depends(require_permissions(Permission.MODEL_UPDATE))])
async def delete_model_tag(
    name: str,
    key: str,
    client: TenantAwareMLflowClient = Depends(get_tenant_aware_mlflow_client)
):
    """
    Delete a tag from a model

    - **name**: Model name
    - **key**: Tag key to delete
    """
    try:
        client.delete_registered_model_tag(name, key)
        return SuccessResponse(
            success=True,
            message=f"Tag '{key}' deleted from model '{name}'"
        )
    except MlflowException as e:
        if "RESOURCE_DOES_NOT_EXIST" in str(e):
            raise HTTPException(status_code=404, detail=f"Model '{name}' not found")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{name}/versions/{version}/tags", response_model=SuccessResponse, dependencies=[Depends(require_permissions(Permission.MODEL_UPDATE))])
async def set_version_tag(
    name: str,
    version: str,
    request: TagRequest,
    client: TenantAwareMLflowClient = Depends(get_tenant_aware_mlflow_client)
):
    """
    Set a tag on a model version

    - **name**: Model name
    - **version**: Model version
    - **key**: Tag key
    - **value**: Tag value
    """
    try:
        client.set_model_version_tag(name, version, request.key, request.value)
        return SuccessResponse(
            success=True,
            message=f"Tag '{request.key}' set on model version '{name}' v{version}"
        )
    except MlflowException as e:
        if "RESOURCE_DOES_NOT_EXIST" in str(e):
            raise HTTPException(
                status_code=404,
                detail=f"Model version '{name}' v{version} not found"
            )
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{name}/versions/{version}/tags/{key}", response_model=SuccessResponse, dependencies=[Depends(require_permissions(Permission.MODEL_UPDATE))])
async def delete_version_tag(
    name: str,
    version: str,
    key: str,
    client: TenantAwareMLflowClient = Depends(get_tenant_aware_mlflow_client)
):
    """
    Delete a tag from a model version

    - **name**: Model name
    - **version**: Model version
    - **key**: Tag key to delete
    """
    try:
        client.delete_model_version_tag(name, version, key)
        return SuccessResponse(
            success=True,
            message=f"Tag '{key}' deleted from model version '{name}' v{version}"
        )
    except MlflowException as e:
        if "RESOURCE_DOES_NOT_EXIST" in str(e):
            raise HTTPException(
                status_code=404,
                detail=f"Model version '{name}' v{version} not found"
            )
        raise HTTPException(status_code=500, detail=str(e))
