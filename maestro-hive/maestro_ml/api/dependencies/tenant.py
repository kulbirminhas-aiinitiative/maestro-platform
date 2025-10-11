"""
Tenant Isolation Dependencies

Ensures all database operations and MLflow artifacts are scoped to the user's tenant.
"""

from fastapi import Depends, HTTPException, status
from typing import Optional
import mlflow
from mlflow.tracking import MlflowClient

from .auth import get_current_user
from ...enterprise.rbac.permissions import _permission_checker as permission_checker
from ...enterprise.tenancy.tenant_manager import TenantManager


# Global tenant manager instance
_tenant_manager = TenantManager()


def get_tenant_manager() -> TenantManager:
    """Get tenant manager singleton"""
    return _tenant_manager


async def get_current_tenant_id(
    current_user: dict = Depends(get_current_user)
) -> str:
    """
    Extract tenant_id from current user

    Raises 403 if user has no tenant association.
    """
    # Anonymous users cannot have tenant_id
    if not current_user.get("authenticated", False):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required for tenant operations"
        )

    user_id = current_user.get("user_id")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user credentials"
        )

    # Get user from permission system to find tenant_id
    user = permission_checker.get_user(user_id)
    if not user or not user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is not associated with any tenant"
        )

    # Verify tenant is active
    tenant_manager = get_tenant_manager()
    tenant = tenant_manager.get_tenant(user.tenant_id)
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tenant not found"
        )

    if not tenant.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tenant is inactive. Please contact support."
        )

    return user.tenant_id


async def get_current_user_with_tenant(
    current_user: dict = Depends(get_current_user),
    tenant_id: str = Depends(get_current_tenant_id)
) -> dict:
    """
    Enhanced user dependency that includes tenant_id

    Returns user dict with added 'tenant_id' field.
    """
    current_user["tenant_id"] = tenant_id
    return current_user


class TenantAwareMLflowClient:
    """
    MLflow client wrapper that enforces tenant isolation

    Automatically adds tenant_id tag to all artifacts and filters queries by tenant.
    """

    def __init__(self, client: MlflowClient, tenant_id: str):
        self._client = client
        self._tenant_id = tenant_id

    @property
    def tenant_id(self) -> str:
        return self._tenant_id

    def _add_tenant_tag(self, tags: Optional[dict]) -> dict:
        """Add tenant_id to tags"""
        if tags is None:
            tags = {}
        tags["tenant_id"] = self._tenant_id
        return tags

    def _filter_by_tenant(self, filter_string: Optional[str]) -> str:
        """Add tenant filter to MLflow filter string"""
        tenant_filter = f"tags.tenant_id = '{self._tenant_id}'"

        if filter_string:
            return f"({filter_string}) AND {tenant_filter}"
        return tenant_filter

    def create_registered_model(self, name: str, tags: Optional[dict] = None, description: Optional[str] = None):
        """Create model with tenant tag"""
        tags = self._add_tenant_tag(tags)
        return self._client.create_registered_model(
            name=name,
            tags=tags,
            description=description
        )

    def search_registered_models(
        self,
        filter_string: Optional[str] = None,
        max_results: int = 100,
        order_by: Optional[list] = None,
        page_token: Optional[str] = None
    ):
        """Search models filtered by tenant"""
        filter_string = self._filter_by_tenant(filter_string)
        return self._client.search_registered_models(
            filter_string=filter_string,
            max_results=max_results,
            order_by=order_by,
            page_token=page_token
        )

    def get_registered_model(self, name: str):
        """
        Get model and verify it belongs to tenant

        Raises 404 if model doesn't exist or doesn't belong to tenant.
        """
        try:
            model = self._client.get_registered_model(name)

            # Verify tenant ownership
            model_tenant_id = model.tags.get("tenant_id")
            if model_tenant_id != self._tenant_id:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Model '{name}' not found"
                )

            return model
        except Exception as e:
            if "RESOURCE_DOES_NOT_EXIST" in str(e):
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Model '{name}' not found"
                )
            raise

    def update_registered_model(self, name: str, description: Optional[str] = None):
        """Update model (after tenant check)"""
        # Verify ownership first
        self.get_registered_model(name)
        return self._client.update_registered_model(name=name, description=description)

    def delete_registered_model(self, name: str):
        """Delete model (after tenant check)"""
        # Verify ownership first
        self.get_registered_model(name)
        return self._client.delete_registered_model(name)

    def get_latest_versions(self, name: str, stages: Optional[list] = None):
        """Get model versions (after tenant check)"""
        # Verify ownership first
        self.get_registered_model(name)
        return self._client.get_latest_versions(name, stages)

    def get_model_version(self, name: str, version: str):
        """Get specific model version (after tenant check)"""
        # Verify ownership first
        self.get_registered_model(name)
        return self._client.get_model_version(name, version)

    def transition_model_version_stage(
        self,
        name: str,
        version: str,
        stage: str,
        archive_existing_versions: bool = False
    ):
        """Transition model stage (after tenant check)"""
        # Verify ownership first
        self.get_registered_model(name)
        return self._client.transition_model_version_stage(
            name=name,
            version=version,
            stage=stage,
            archive_existing_versions=archive_existing_versions
        )

    def set_registered_model_tag(self, name: str, key: str, value: str):
        """Set model tag (after tenant check, prevent tenant_id modification)"""
        if key == "tenant_id":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot modify tenant_id tag"
            )

        # Verify ownership first
        self.get_registered_model(name)
        return self._client.set_registered_model_tag(name, key, value)

    def delete_registered_model_tag(self, name: str, key: str):
        """Delete model tag (after tenant check, prevent tenant_id deletion)"""
        if key == "tenant_id":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot delete tenant_id tag"
            )

        # Verify ownership first
        self.get_registered_model(name)
        return self._client.delete_registered_model_tag(name, key)

    def set_model_version_tag(self, name: str, version: str, key: str, value: str):
        """Set model version tag (after tenant check)"""
        if key == "tenant_id":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot modify tenant_id tag"
            )

        # Verify ownership first
        self.get_registered_model(name)
        return self._client.set_model_version_tag(name, version, key, value)

    def delete_model_version_tag(self, name: str, version: str, key: str):
        """Delete model version tag (after tenant check)"""
        if key == "tenant_id":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot delete tenant_id tag"
            )

        # Verify ownership first
        self.get_registered_model(name)
        return self._client.delete_model_version_tag(name, version, key)


def get_tenant_aware_mlflow_client(
    tenant_id: str = Depends(get_current_tenant_id)
) -> TenantAwareMLflowClient:
    """
    Get MLflow client that enforces tenant isolation

    Usage in endpoints:
        client: TenantAwareMLflowClient = Depends(get_tenant_aware_mlflow_client)
    """
    from ..config import settings

    mlflow.set_tracking_uri(settings.mlflow_tracking_uri)
    if settings.mlflow_registry_uri:
        mlflow.set_registry_uri(settings.mlflow_registry_uri)

    base_client = MlflowClient()
    return TenantAwareMLflowClient(base_client, tenant_id)
