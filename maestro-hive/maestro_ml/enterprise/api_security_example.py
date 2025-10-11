"""
Enterprise Security - Complete API Integration Example

Demonstrates how to integrate all security features:
- RBAC (Role-Based Access Control)
- Rate Limiting
- Security Headers
- Tenant Isolation
"""

from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

# Security imports
from enterprise.rbac.fastapi_integration import (
    get_current_user,
    require_permission,
    require_any_permission,
    RequirePermission
)
from enterprise.rbac.permissions import Permission, User
from enterprise.security import (
    add_rate_limiting,
    add_security_headers,
    RateLimitConfig
)
from enterprise.tenancy import (
    TenantIsolationMiddleware,
    tenant_context,
    enforce_tenant_on_create,
    verify_tenant_access,
    require_tenant_context
)

# Create FastAPI app
app = FastAPI(
    title="Maestro ML Platform - Secured",
    version="2.0.0",
    description="Enterprise ML platform with complete security"
)

# ============================================================================
# STEP 1: Add Security Middleware (order matters!)
# ============================================================================

# 1. Security Headers (outermost)
add_security_headers(
    app,
    enable_hsts=True,
    enable_csp=True,
    frame_options="DENY"
)

# 2. Rate Limiting
rate_limit_config = RateLimitConfig(
    per_user_limit=1000,    # 1000 requests per minute per user
    per_tenant_limit=5000,  # 5000 requests per minute per tenant
    per_ip_limit=100,       # 100 requests per minute per IP
    global_limit=10000,     # 10000 requests per minute globally
    window=60,              # 60 second window
    exempt_paths=["/health", "/metrics", "/docs"]
)
add_rate_limiting(app, rate_limit_config)

# 3. Tenant Isolation (innermost)
app.add_middleware(TenantIsolationMiddleware)

# ============================================================================
# STEP 2: Example Models (with tenant isolation)
# ============================================================================

from sqlalchemy import Column, String, DateTime, Integer
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()


class Model(Base):
    """ML Model with tenant isolation"""
    __tablename__ = "models"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    tenant_id = Column(String, nullable=False, index=True)  # Tenant isolation
    created_at = Column(DateTime, default=datetime.utcnow)
    created_by = Column(String)


class Experiment(Base):
    """Experiment with tenant isolation"""
    __tablename__ = "experiments"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    tenant_id = Column(String, nullable=False, index=True)  # Tenant isolation
    model_id = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)


# ============================================================================
# STEP 3: Secured Endpoints
# ============================================================================

# Example 1: Public endpoint (no authentication, but rate limited)
@app.get("/health")
async def health_check():
    """Public health check - no auth required, exempt from rate limiting"""
    return {"status": "healthy"}


# Example 2: Authenticated endpoint (requires login, no specific permission)
@app.get("/me")
async def get_current_user_info(user: User = Depends(get_current_user)):
    """Get current user info - requires authentication only"""
    return {
        "user_id": user.user_id,
        "email": user.email,
        "roles": user.roles,
        "tenant_id": user.tenant_id
    }


# Example 3: Permission-based endpoint (requires specific permission)
@app.get(
    "/models",
    dependencies=[require_permission(Permission.MODEL_VIEW)]
)
@require_tenant_context
async def list_models(
    db: Session = Depends(lambda: None),  # Placeholder
    user: User = Depends(get_current_user)
):
    """
    List models - requires MODEL_VIEW permission.
    Results are automatically filtered by tenant.
    """
    # Queries are automatically filtered by tenant from x-tenant-id header
    # models = db.query(Model).all()  # Auto-filtered!

    return {
        "models": [],
        "tenant_id": user.tenant_id,
        "user_id": user.user_id
    }


# Example 4: Create with tenant isolation
@app.post(
    "/models",
    dependencies=[require_permission(Permission.MODEL_CREATE)]
)
@require_tenant_context
async def create_model(
    model_data: dict,
    db: Session = Depends(lambda: None),
    user: User = Depends(get_current_user)
):
    """
    Create model - requires MODEL_CREATE permission.
    Tenant ID is automatically set from context.
    """
    # Create model
    model = Model(
        id=model_data["id"],
        name=model_data["name"],
        created_by=user.user_id
    )

    # Automatically set tenant from context
    enforce_tenant_on_create(model)

    # Save to database
    # db.add(model)
    # db.commit()

    return {
        "model_id": model.id,
        "tenant_id": model.tenant_id,
        "message": "Model created successfully"
    }


# Example 5: Multiple permission options (any of the listed)
@app.get(
    "/resources",
    dependencies=[require_any_permission(
        Permission.MODEL_VIEW,
        Permission.EXPERIMENT_VIEW,
        Permission.DATA_VIEW
    )]
)
async def list_resources(user: User = Depends(get_current_user)):
    """
    List resources - requires any of: MODEL_VIEW, EXPERIMENT_VIEW, or DATA_VIEW.
    """
    return {
        "resources": [],
        "user_permissions": "at least one of: model:view, experiment:view, data:view"
    }


# Example 6: Admin-only endpoint
@app.delete(
    "/models/{model_id}",
    dependencies=[require_permission(Permission.MODEL_DELETE)]
)
@require_tenant_context
async def delete_model(
    model_id: str,
    db: Session = Depends(lambda: None),
    user: User = Depends(get_current_user)
):
    """
    Delete model - requires MODEL_DELETE permission.
    Verifies tenant ownership before deletion.
    """
    # Fetch model (auto-filtered by tenant)
    # model = db.query(Model).filter(Model.id == model_id).first()

    # if not model:
    #     raise HTTPException(status_code=404, detail="Model not found")

    # Double-check tenant access (defense in depth)
    # verify_tenant_access(model, user.tenant_id)

    # Delete model
    # db.delete(model)
    # db.commit()

    return {"message": "Model deleted successfully"}


# Example 7: System admin endpoint (full access)
@app.post(
    "/admin/users",
    dependencies=[require_permission(Permission.SYSTEM_ADMIN)]
)
async def create_user_admin(
    user_data: dict,
    current_user: User = Depends(get_current_user)
):
    """
    Create user - requires SYSTEM_ADMIN permission.
    System admins can create users across tenants.
    """
    return {
        "user_id": user_data.get("user_id"),
        "message": "User created by system admin",
        "admin": current_user.user_id
    }


# Example 8: Tenant admin endpoint
@app.get(
    "/tenant/users",
    dependencies=[require_permission(Permission.TENANT_VIEW)]
)
@require_tenant_context
async def list_tenant_users(
    user: User = Depends(get_current_user)
):
    """
    List users in tenant - requires TENANT_VIEW permission.
    Results limited to current tenant.
    """
    return {
        "users": [],
        "tenant_id": user.tenant_id,
        "message": "Users in your tenant"
    }


# Example 9: Deployment endpoint (requires multiple permissions)
@app.post(
    "/models/{model_id}/deploy",
    dependencies=[Depends(RequirePermission(Permission.MODEL_DEPLOY))]
)
@require_tenant_context
async def deploy_model(
    model_id: str,
    deployment_config: dict,
    db: Session = Depends(lambda: None),
    user: User = Depends(get_current_user)
):
    """
    Deploy model - requires MODEL_DEPLOY permission.
    Verifies model belongs to user's tenant before deploying.
    """
    # Fetch model (auto-filtered by tenant)
    # model = db.query(Model).filter(Model.id == model_id).first()

    # if not model:
    #     raise HTTPException(status_code=404, detail="Model not found")

    # Deploy model
    return {
        "deployment_id": f"deploy-{model_id}",
        "model_id": model_id,
        "status": "deploying",
        "config": deployment_config
    }


# ============================================================================
# STEP 4: Rate Limit Information Endpoint
# ============================================================================

@app.get("/rate-limit-info")
async def rate_limit_info(user: User = Depends(get_current_user)):
    """
    Get rate limit information.
    Rate limit headers are automatically added to all responses.
    """
    return {
        "message": "Check response headers for rate limit information",
        "headers": {
            "X-RateLimit-Limit": "Maximum requests allowed",
            "X-RateLimit-Remaining": "Requests remaining",
            "X-RateLimit-Reset": "Timestamp when limit resets",
            "X-RateLimit-User-*": "User-specific limits",
            "X-RateLimit-Tenant-*": "Tenant-specific limits"
        }
    }


# ============================================================================
# STEP 5: Security Headers Information
# ============================================================================

@app.get("/security-headers")
async def security_headers_info():
    """
    Information about security headers.
    These headers are automatically added to all responses.
    """
    return {
        "message": "All responses include security headers",
        "headers": {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-XSS-Protection": "1; mode=block",
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
            "Content-Security-Policy": "Configured policy",
            "Referrer-Policy": "strict-origin-when-cross-origin",
            "Permissions-Policy": "Restricted features"
        }
    }


# ============================================================================
# STEP 6: Error Handlers
# ============================================================================

@app.exception_handler(PermissionError)
async def permission_error_handler(request, exc):
    """Handle permission errors"""
    return HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail=str(exc)
    )


# ============================================================================
# USAGE EXAMPLES
# ============================================================================

"""
1. Making Authenticated Requests:

   curl -X GET http://localhost:8000/models \\
     -H "Authorization: Bearer <token>" \\
     -H "x-user-id: user-123" \\
     -H "x-tenant-id: tenant-abc"

2. Rate Limit Headers in Response:

   X-RateLimit-Limit: 1000
   X-RateLimit-Remaining: 999
   X-RateLimit-Reset: 1633024800

3. Security Headers in Response:

   X-Content-Type-Options: nosniff
   X-Frame-Options: DENY
   Strict-Transport-Security: max-age=31536000

4. Tenant Isolation:

   # User in tenant-abc can only see/modify resources in tenant-abc
   # Queries are automatically filtered by tenant_id

5. Permission Checking:

   # User needs specific permission to access endpoint
   # Returns 403 Forbidden if permission missing

6. Rate Limiting:

   # Returns 429 Too Many Requests when limit exceeded
   # Retry-After header indicates when to retry
"""

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
