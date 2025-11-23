"""
Authentication and Authorization Module
Implements JWT-based authentication with OAuth2 password bearer flow
"""

import os
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

import structlog
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel, EmailStr

logger = structlog.get_logger(__name__)

# Configuration from environment variables
_DEFAULT_SECRET = "dev_secret_key_change_in_production"
SECRET_KEY = os.getenv("JWT_SECRET_KEY", _DEFAULT_SECRET)
ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
ADMIN_API_KEY = os.getenv("ADMIN_API_KEY", "")

# Validate secret key in production
_ENVIRONMENT = os.getenv("ENVIRONMENT", "development").lower()
if _ENVIRONMENT in ("production", "prod", "staging") and SECRET_KEY == _DEFAULT_SECRET:
    raise RuntimeError(
        "SECURITY ERROR: JWT_SECRET_KEY must be set in production! "
        "Generate a secure secret: python -c \"import secrets; print(secrets.token_urlsafe(32))\""
    )

# User passwords from environment (with safe dev defaults)
# In production, these MUST be set via environment variables
_DEFAULT_PASSWORDS = {"admin123", "dev123", "viewer123"}
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")
DEVELOPER_PASSWORD = os.getenv("DEVELOPER_PASSWORD", "dev123")
VIEWER_PASSWORD = os.getenv("VIEWER_PASSWORD", "viewer123")

if _ENVIRONMENT in ("production", "prod", "staging"):
    if {ADMIN_PASSWORD, DEVELOPER_PASSWORD, VIEWER_PASSWORD} & _DEFAULT_PASSWORDS:
        raise RuntimeError(
            "SECURITY ERROR: Default passwords detected in production! "
            "Set ADMIN_PASSWORD, DEVELOPER_PASSWORD, VIEWER_PASSWORD environment variables."
        )

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 schemes
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token")
http_bearer = HTTPBearer()

# ============================================================================
# Pydantic Models
# ============================================================================

class Token(BaseModel):
    """OAuth2 token response"""
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class TokenData(BaseModel):
    """Data encoded in JWT token"""
    username: Optional[str] = None
    email: Optional[EmailStr] = None
    scopes: list[str] = []
    exp: Optional[datetime] = None


class User(BaseModel):
    """User model"""
    username: str
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    disabled: bool = False
    is_admin: bool = False
    scopes: list[str] = []


class UserInDB(User):
    """User model with hashed password"""
    hashed_password: str


class LoginRequest(BaseModel):
    """Login request model"""
    username: str
    password: str


# ============================================================================
# Password Hashing
# ============================================================================

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a password against a hashed password

    Args:
        plain_password: Plain text password
        hashed_password: Bcrypt hashed password

    Returns:
        True if password matches, False otherwise
    """
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """
    Hash a password using bcrypt

    Args:
        password: Plain text password

    Returns:
        Bcrypt hashed password
    """
    return pwd_context.hash(password)


# ============================================================================
# JWT Token Operations
# ============================================================================

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a JWT access token

    Args:
        data: Data to encode in token (username, email, scopes)
        expires_delta: Optional expiration time delta

    Returns:
        Encoded JWT token
    """
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({
        "exp": expire,
        "iat": datetime.utcnow(),
        "type": "access"
    })

    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

    logger.info(
        "access_token_created",
        username=data.get("sub"),
        expires_at=expire.isoformat()
    )

    return encoded_jwt


def decode_access_token(token: str) -> TokenData:
    """
    Decode and validate a JWT access token

    Args:
        token: JWT token string

    Returns:
        TokenData with decoded information

    Raises:
        HTTPException: If token is invalid or expired
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")

        if username is None:
            logger.warning("token_missing_subject")
            raise credentials_exception

        token_data = TokenData(
            username=username,
            email=payload.get("email"),
            scopes=payload.get("scopes", []),
            exp=datetime.fromtimestamp(payload.get("exp"))
        )

        return token_data

    except JWTError as e:
        logger.error("jwt_decode_error", error=str(e))
        raise credentials_exception


# ============================================================================
# User Authentication (In-Memory for MVP)
# ============================================================================

# TODO: Replace with database-backed user store
# Users initialized from environment variables
USERS_DB: Dict[str, UserInDB] = {
    "admin": UserInDB(
        username="admin",
        email="admin@maestro-platform.com",
        full_name="Admin User",
        hashed_password=get_password_hash(ADMIN_PASSWORD),  # From environment
        disabled=False,
        is_admin=True,
        scopes=["admin", "templates:read", "templates:write", "templates:delete"]
    ),
    "developer": UserInDB(
        username="developer",
        email="dev@maestro-platform.com",
        full_name="Developer User",
        hashed_password=get_password_hash(DEVELOPER_PASSWORD),  # From environment
        disabled=False,
        is_admin=False,
        scopes=["templates:read", "templates:write"]
    ),
    "viewer": UserInDB(
        username="viewer",
        email="viewer@maestro-platform.com",
        full_name="Viewer User",
        hashed_password=get_password_hash(VIEWER_PASSWORD),  # From environment
        disabled=False,
        is_admin=False,
        scopes=["templates:read"]
    )
}


def get_user(username: str) -> Optional[UserInDB]:
    """
    Retrieve user from database

    Args:
        username: Username to retrieve

    Returns:
        UserInDB if found, None otherwise
    """
    if username in USERS_DB:
        return USERS_DB[username]
    return None


def authenticate_user(username: str, password: str) -> Optional[User]:
    """
    Authenticate a user with username and password

    Args:
        username: Username
        password: Plain text password

    Returns:
        User if authentication successful, None otherwise
    """
    user = get_user(username)
    if not user:
        logger.warning("authentication_failed_user_not_found", username=username)
        return None

    if not verify_password(password, user.hashed_password):
        logger.warning("authentication_failed_invalid_password", username=username)
        return None

    logger.info("user_authenticated", username=username)
    return User(**user.dict())


# ============================================================================
# Dependency Functions for FastAPI
# ============================================================================

async def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    """
    Dependency to get current authenticated user from JWT token

    Args:
        token: JWT token from Authorization header

    Returns:
        User object

    Raises:
        HTTPException: If token is invalid or user not found
    """
    token_data = decode_access_token(token)
    user = get_user(username=token_data.username)

    if user is None:
        logger.error("user_not_found_in_db", username=token_data.username)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if user.disabled:
        logger.warning("disabled_user_attempted_access", username=user.username)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled"
        )

    return User(**user.dict())


async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Dependency to get current active (non-disabled) user

    Args:
        current_user: User from get_current_user dependency

    Returns:
        User object

    Raises:
        HTTPException: If user is disabled
    """
    if current_user.disabled:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user"
        )
    return current_user


async def require_admin(
    current_user: User = Depends(get_current_active_user)
) -> User:
    """
    Dependency to require admin privileges

    Args:
        current_user: User from get_current_active_user dependency

    Returns:
        User object

    Raises:
        HTTPException: If user is not admin
    """
    if not current_user.is_admin:
        logger.warning(
            "unauthorized_admin_access_attempt",
            username=current_user.username
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required"
        )
    return current_user


def require_scope(required_scope: str):
    """
    Dependency factory to require specific scope

    Args:
        required_scope: Required scope (e.g., "templates:write")

    Returns:
        Dependency function
    """
    async def check_scope(current_user: User = Depends(get_current_active_user)):
        if required_scope not in current_user.scopes:
            logger.warning(
                "insufficient_scope",
                username=current_user.username,
                required=required_scope,
                has=current_user.scopes
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required scope: {required_scope}"
            )
        return current_user

    return check_scope


# ============================================================================
# API Key Authentication (for service-to-service)
# ============================================================================

async def verify_api_key(
    credentials: HTTPAuthorizationCredentials = Depends(http_bearer)
) -> bool:
    """
    Verify API key from Authorization header

    Args:
        credentials: HTTP bearer credentials

    Returns:
        True if API key is valid

    Raises:
        HTTPException: If API key is invalid
    """
    api_key = credentials.credentials

    # Check against admin API key
    if api_key == ADMIN_API_KEY and ADMIN_API_KEY:
        logger.info("api_key_authenticated", key_type="admin")
        return True

    # TODO: Add support for service-specific API keys from database

    logger.warning("invalid_api_key_attempt", key_prefix=api_key[:8] if api_key else "none")
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid API key",
        headers={"WWW-Authenticate": "Bearer"},
    )


async def get_current_user_or_api_key(
    user: Optional[User] = Depends(get_current_user),
    api_key_valid: bool = Depends(verify_api_key)
) -> User:
    """
    Dependency that accepts either JWT token or API key

    Args:
        user: User from JWT token (optional)
        api_key_valid: API key validation result

    Returns:
        User object (service user if API key)
    """
    if user:
        return user

    if api_key_valid:
        # Return service user
        return User(
            username="service",
            email="service@maestro-platform.com",
            full_name="Service Account",
            is_admin=True,
            scopes=["admin"]
        )

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required"
    )


# ============================================================================
# Utility Functions
# ============================================================================

def create_user(
    username: str,
    password: str,
    email: Optional[EmailStr] = None,
    full_name: Optional[str] = None,
    is_admin: bool = False,
    scopes: list[str] = None
) -> User:
    """
    Create a new user (in-memory for MVP)

    Args:
        username: Username
        password: Plain text password (will be hashed)
        email: User email
        full_name: User full name
        is_admin: Admin flag
        scopes: List of permission scopes

    Returns:
        User object
    """
    if scopes is None:
        scopes = ["templates:read"]

    user_in_db = UserInDB(
        username=username,
        email=email,
        full_name=full_name,
        hashed_password=get_password_hash(password),
        disabled=False,
        is_admin=is_admin,
        scopes=scopes
    )

    USERS_DB[username] = user_in_db

    logger.info(
        "user_created",
        username=username,
        is_admin=is_admin,
        scopes=scopes
    )

    return User(**user_in_db.dict())


def check_permissions(user: User, required_permissions: list[str]) -> bool:
    """
    Check if user has all required permissions

    Args:
        user: User object
        required_permissions: List of required permission scopes

    Returns:
        True if user has all permissions
    """
    if user.is_admin:
        return True

    return all(perm in user.scopes for perm in required_permissions)
