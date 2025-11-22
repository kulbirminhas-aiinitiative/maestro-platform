"""
MAESTRO Core Authentication & Authorization Library

Enterprise-grade authentication with JWT, OAuth2, RBAC, and multi-provider support.
Follows OAuth2/OpenID Connect standards and enterprise security best practices.

Usage:
    from maestro_core_auth import AuthManager, JWTAuth, RBACManager

    # Initialize authentication
    auth_manager = AuthManager(
        jwt_secret="your-secret-key",
        token_expire_minutes=30
    )

    # FastAPI integration
    from fastapi import Depends
    from maestro_core_auth import get_current_user, require_role

    @app.get("/protected")
    async def protected(user = Depends(get_current_user)):
        return {"user": user.username}

    @app.get("/admin")
    async def admin_only(user = Depends(require_role("admin"))):
        return {"message": "Admin access granted"}
"""

from .auth_manager import AuthManager
from .jwt_auth import JWTAuth, JWTPayload
from .oauth2 import OAuth2Provider, OAuth2Manager
from .rbac import RBACManager, Role, Permission
from .models import User, UserCreate, UserUpdate, TokenResponse
from .dependencies import (
    get_current_user,
    get_current_active_user,
    require_role,
    require_permission,
    require_auth
)
from .password import PasswordManager
from .session import SessionManager
from .exceptions import (
    AuthException,
    InvalidCredentialsException,
    TokenExpiredException,
    InsufficientPermissionsException
)

__version__ = "1.0.0"
__all__ = [
    # Core classes
    "AuthManager",
    "JWTAuth",
    "JWTPayload",
    "OAuth2Provider",
    "OAuth2Manager",
    "RBACManager",
    "Role",
    "Permission",

    # Models
    "User",
    "UserCreate",
    "UserUpdate",
    "TokenResponse",

    # Dependencies
    "get_current_user",
    "get_current_active_user",
    "require_role",
    "require_permission",
    "require_auth",

    # Utilities
    "PasswordManager",
    "SessionManager",

    # Exceptions
    "AuthException",
    "InvalidCredentialsException",
    "TokenExpiredException",
    "InsufficientPermissionsException",
]