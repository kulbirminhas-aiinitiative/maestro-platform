"""
SCIM 2.0 (System for Cross-domain Identity Management) endpoints.

Provides standard SCIM 2.0 API for:
- User provisioning/deprovisioning
- Group management
- Bulk operations

Reference: RFC 7644 (SCIM Protocol)
"""

from typing import Optional, Dict, Any, List
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends, Query, Header
from pydantic import BaseModel, Field, EmailStr
from sqlalchemy.ext.asyncio import AsyncSession
from maestro_core_logging import get_logger

logger = get_logger(__name__)


# SCIM 2.0 Schema URIs
SCIM_SCHEMAS = {
    "user": "urn:ietf:params:scim:schemas:core:2.0:User",
    "group": "urn:ietf:params:scim:schemas:core:2.0:Group",
    "enterprise_user": "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User",
    "list_response": "urn:ietf:params:scim:api:messages:2.0:ListResponse",
    "error": "urn:ietf:params:scim:api:messages:2.0:Error",
    "patch_op": "urn:ietf:params:scim:api:messages:2.0:PatchOp",
    "bulk_request": "urn:ietf:params:scim:api:messages:2.0:BulkRequest",
    "bulk_response": "urn:ietf:params:scim:api:messages:2.0:BulkResponse",
}


# SCIM Models
class SCIMName(BaseModel):
    """SCIM Name component."""
    formatted: Optional[str] = None
    familyName: Optional[str] = None
    givenName: Optional[str] = None
    middleName: Optional[str] = None
    honorificPrefix: Optional[str] = None
    honorificSuffix: Optional[str] = None


class SCIMEmail(BaseModel):
    """SCIM Email component."""
    value: str
    type: Optional[str] = "work"
    primary: Optional[bool] = True


class SCIMPhoneNumber(BaseModel):
    """SCIM Phone number component."""
    value: str
    type: Optional[str] = "work"


class SCIMPhoto(BaseModel):
    """SCIM Photo component."""
    value: str
    type: Optional[str] = "photo"


class SCIMGroup(BaseModel):
    """SCIM Group reference."""
    value: str
    display: Optional[str] = None
    ref: Optional[str] = Field(None, alias="$ref")


class SCIMMeta(BaseModel):
    """SCIM Resource metadata."""
    resourceType: str
    created: Optional[datetime] = None
    lastModified: Optional[datetime] = None
    location: Optional[str] = None
    version: Optional[str] = None


class SCIMEnterpriseUser(BaseModel):
    """SCIM Enterprise User extension."""
    employeeNumber: Optional[str] = None
    costCenter: Optional[str] = None
    organization: Optional[str] = None
    division: Optional[str] = None
    department: Optional[str] = None
    manager: Optional[Dict[str, str]] = None


class SCIMUser(BaseModel):
    """SCIM 2.0 User resource."""
    schemas: List[str] = [SCIM_SCHEMAS["user"]]
    id: Optional[str] = None
    externalId: Optional[str] = None
    userName: str
    name: Optional[SCIMName] = None
    displayName: Optional[str] = None
    nickName: Optional[str] = None
    profileUrl: Optional[str] = None
    title: Optional[str] = None
    userType: Optional[str] = None
    preferredLanguage: Optional[str] = None
    locale: Optional[str] = None
    timezone: Optional[str] = None
    active: bool = True
    password: Optional[str] = None
    emails: List[SCIMEmail] = []
    phoneNumbers: List[SCIMPhoneNumber] = []
    photos: List[SCIMPhoto] = []
    groups: List[SCIMGroup] = []
    meta: Optional[SCIMMeta] = None
    # Enterprise extension
    urn_ietf_params_scim_schemas_extension_enterprise_2_0_User: Optional[SCIMEnterpriseUser] = Field(
        None,
        alias="urn:ietf:params:scim:schemas:extension:enterprise:2.0:User"
    )

    class Config:
        populate_by_name = True


class SCIMGroupMember(BaseModel):
    """SCIM Group member."""
    value: str
    display: Optional[str] = None
    ref: Optional[str] = Field(None, alias="$ref")


class SCIMGroupResource(BaseModel):
    """SCIM 2.0 Group resource."""
    schemas: List[str] = [SCIM_SCHEMAS["group"]]
    id: Optional[str] = None
    externalId: Optional[str] = None
    displayName: str
    members: List[SCIMGroupMember] = []
    meta: Optional[SCIMMeta] = None


class SCIMListResponse(BaseModel):
    """SCIM List response."""
    schemas: List[str] = [SCIM_SCHEMAS["list_response"]]
    totalResults: int
    startIndex: int = 1
    itemsPerPage: int
    Resources: List[Any] = []


class SCIMError(BaseModel):
    """SCIM Error response."""
    schemas: List[str] = [SCIM_SCHEMAS["error"]]
    detail: str
    status: int
    scimType: Optional[str] = None


class SCIMPatchOperation(BaseModel):
    """SCIM Patch operation."""
    op: str  # add, remove, replace
    path: Optional[str] = None
    value: Optional[Any] = None


class SCIMPatchRequest(BaseModel):
    """SCIM Patch request."""
    schemas: List[str] = [SCIM_SCHEMAS["patch_op"]]
    Operations: List[SCIMPatchOperation]


# SCIM Service
class SCIMService:
    """
    SCIM 2.0 service for user and group management.

    This service handles SCIM operations and maps them to your user store.
    """

    def __init__(self, base_url: str = "/scim/v2"):
        self.base_url = base_url
        self.router = APIRouter(prefix=base_url, tags=["SCIM"])
        self._setup_routes()

    def _setup_routes(self) -> None:
        """Setup SCIM API routes."""

        # Service Provider Config
        @self.router.get("/ServiceProviderConfig")
        async def get_service_provider_config():
            """Return SCIM service provider configuration."""
            return {
                "schemas": ["urn:ietf:params:scim:schemas:core:2.0:ServiceProviderConfig"],
                "documentationUri": "https://docs.maestro.ai/scim",
                "patch": {"supported": True},
                "bulk": {
                    "supported": True,
                    "maxOperations": 1000,
                    "maxPayloadSize": 1048576
                },
                "filter": {
                    "supported": True,
                    "maxResults": 200
                },
                "changePassword": {"supported": True},
                "sort": {"supported": True},
                "etag": {"supported": False},
                "authenticationSchemes": [
                    {
                        "type": "oauthbearertoken",
                        "name": "OAuth Bearer Token",
                        "description": "Authentication using OAuth 2.0 Bearer Token"
                    }
                ]
            }

        # Resource Types
        @self.router.get("/ResourceTypes")
        async def get_resource_types():
            """Return supported SCIM resource types."""
            return {
                "schemas": [SCIM_SCHEMAS["list_response"]],
                "totalResults": 2,
                "Resources": [
                    {
                        "schemas": ["urn:ietf:params:scim:schemas:core:2.0:ResourceType"],
                        "id": "User",
                        "name": "User",
                        "endpoint": "/Users",
                        "schema": SCIM_SCHEMAS["user"],
                        "schemaExtensions": [
                            {
                                "schema": SCIM_SCHEMAS["enterprise_user"],
                                "required": False
                            }
                        ]
                    },
                    {
                        "schemas": ["urn:ietf:params:scim:schemas:core:2.0:ResourceType"],
                        "id": "Group",
                        "name": "Group",
                        "endpoint": "/Groups",
                        "schema": SCIM_SCHEMAS["group"]
                    }
                ]
            }

        # Schemas
        @self.router.get("/Schemas")
        async def get_schemas():
            """Return SCIM schemas."""
            return {
                "schemas": [SCIM_SCHEMAS["list_response"]],
                "totalResults": 3,
                "Resources": []  # Full schema definitions would go here
            }

        # Users endpoints
        @self.router.get("/Users")
        async def list_users(
            filter: Optional[str] = Query(None),
            startIndex: int = Query(1, ge=1),
            count: int = Query(100, ge=1, le=200),
            sortBy: Optional[str] = None,
            sortOrder: Optional[str] = "ascending"
        ):
            """List users with optional filtering."""
            # Parse SCIM filter
            users = await self._list_users(filter, startIndex, count, sortBy, sortOrder)
            return SCIMListResponse(
                totalResults=users["total"],
                startIndex=startIndex,
                itemsPerPage=count,
                Resources=users["items"]
            )

        @self.router.post("/Users", status_code=201)
        async def create_user(user: SCIMUser):
            """Create a new user."""
            created = await self._create_user(user)
            return created

        @self.router.get("/Users/{user_id}")
        async def get_user(user_id: str):
            """Get user by ID."""
            user = await self._get_user(user_id)
            if not user:
                raise HTTPException(
                    status_code=404,
                    detail=SCIMError(
                        detail=f"User {user_id} not found",
                        status=404
                    ).model_dump()
                )
            return user

        @self.router.put("/Users/{user_id}")
        async def replace_user(user_id: str, user: SCIMUser):
            """Replace user."""
            updated = await self._replace_user(user_id, user)
            if not updated:
                raise HTTPException(status_code=404, detail="User not found")
            return updated

        @self.router.patch("/Users/{user_id}")
        async def patch_user(user_id: str, patch: SCIMPatchRequest):
            """Patch user with operations."""
            updated = await self._patch_user(user_id, patch)
            if not updated:
                raise HTTPException(status_code=404, detail="User not found")
            return updated

        @self.router.delete("/Users/{user_id}", status_code=204)
        async def delete_user(user_id: str):
            """Delete user."""
            deleted = await self._delete_user(user_id)
            if not deleted:
                raise HTTPException(status_code=404, detail="User not found")

        # Groups endpoints
        @self.router.get("/Groups")
        async def list_groups(
            filter: Optional[str] = Query(None),
            startIndex: int = Query(1, ge=1),
            count: int = Query(100, ge=1, le=200)
        ):
            """List groups."""
            groups = await self._list_groups(filter, startIndex, count)
            return SCIMListResponse(
                totalResults=groups["total"],
                startIndex=startIndex,
                itemsPerPage=count,
                Resources=groups["items"]
            )

        @self.router.post("/Groups", status_code=201)
        async def create_group(group: SCIMGroupResource):
            """Create a new group."""
            return await self._create_group(group)

        @self.router.get("/Groups/{group_id}")
        async def get_group(group_id: str):
            """Get group by ID."""
            group = await self._get_group(group_id)
            if not group:
                raise HTTPException(status_code=404, detail="Group not found")
            return group

        @self.router.put("/Groups/{group_id}")
        async def replace_group(group_id: str, group: SCIMGroupResource):
            """Replace group."""
            return await self._replace_group(group_id, group)

        @self.router.patch("/Groups/{group_id}")
        async def patch_group(group_id: str, patch: SCIMPatchRequest):
            """Patch group."""
            return await self._patch_group(group_id, patch)

        @self.router.delete("/Groups/{group_id}", status_code=204)
        async def delete_group(group_id: str):
            """Delete group."""
            await self._delete_group(group_id)

    # Implementation methods - override these in your application
    async def _list_users(
        self,
        filter: Optional[str],
        start_index: int,
        count: int,
        sort_by: Optional[str],
        sort_order: str
    ) -> Dict[str, Any]:
        """List users. Override this method."""
        logger.warning("SCIM _list_users not implemented")
        return {"total": 0, "items": []}

    async def _create_user(self, user: SCIMUser) -> SCIMUser:
        """Create user. Override this method."""
        logger.info("SCIM create user", userName=user.userName)
        # Implementation would:
        # 1. Map SCIM user to internal user model
        # 2. Create user in database
        # 3. Return SCIM user with id and meta
        raise NotImplementedError("Implement _create_user")

    async def _get_user(self, user_id: str) -> Optional[SCIMUser]:
        """Get user by ID. Override this method."""
        logger.warning("SCIM _get_user not implemented")
        return None

    async def _replace_user(self, user_id: str, user: SCIMUser) -> Optional[SCIMUser]:
        """Replace user. Override this method."""
        raise NotImplementedError("Implement _replace_user")

    async def _patch_user(self, user_id: str, patch: SCIMPatchRequest) -> Optional[SCIMUser]:
        """Patch user. Override this method."""
        # Apply patch operations
        for op in patch.Operations:
            if op.op == "replace":
                pass  # Update field at op.path with op.value
            elif op.op == "add":
                pass  # Add value at op.path
            elif op.op == "remove":
                pass  # Remove value at op.path
        raise NotImplementedError("Implement _patch_user")

    async def _delete_user(self, user_id: str) -> bool:
        """Delete user. Override this method."""
        raise NotImplementedError("Implement _delete_user")

    async def _list_groups(
        self,
        filter: Optional[str],
        start_index: int,
        count: int
    ) -> Dict[str, Any]:
        """List groups. Override this method."""
        return {"total": 0, "items": []}

    async def _create_group(self, group: SCIMGroupResource) -> SCIMGroupResource:
        """Create group. Override this method."""
        raise NotImplementedError("Implement _create_group")

    async def _get_group(self, group_id: str) -> Optional[SCIMGroupResource]:
        """Get group. Override this method."""
        return None

    async def _replace_group(self, group_id: str, group: SCIMGroupResource) -> SCIMGroupResource:
        """Replace group. Override this method."""
        raise NotImplementedError("Implement _replace_group")

    async def _patch_group(self, group_id: str, patch: SCIMPatchRequest) -> SCIMGroupResource:
        """Patch group. Override this method."""
        raise NotImplementedError("Implement _patch_group")

    async def _delete_group(self, group_id: str) -> None:
        """Delete group. Override this method."""
        raise NotImplementedError("Implement _delete_group")


def parse_scim_filter(filter_str: str) -> Dict[str, Any]:
    """
    Parse SCIM filter string.

    Supports basic filters like:
    - userName eq "john"
    - email co "@company.com"
    - active eq true

    Returns parsed filter as dict.
    """
    if not filter_str:
        return {}

    # Simple parser for common filters
    parts = filter_str.split()
    if len(parts) >= 3:
        attribute = parts[0]
        operator = parts[1].lower()
        value = " ".join(parts[2:]).strip('"')

        return {
            "attribute": attribute,
            "operator": operator,
            "value": value
        }

    return {}
