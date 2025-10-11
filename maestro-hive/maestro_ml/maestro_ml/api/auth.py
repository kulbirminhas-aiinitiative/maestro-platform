#!/usr/bin/env python3
"""
Authentication Routes for Maestro ML Platform

Provides login, logout, registration, and token management endpoints.

Security Features:
- Rate limiting on authentication endpoints
- Input validation with Pydantic
- JWT token management
- Password hashing with bcrypt
- Token blacklisting for logout
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field
from typing import Optional
from slowapi import Limiter
from slowapi.util import get_remote_address
import logging

from enterprise.auth.jwt_manager import JWTManager, TokenPair
from enterprise.auth.password_hasher import PasswordHasher
from enterprise.auth.token_blacklist import TokenBlacklist
from maestro_ml.core.database import get_db

logger = logging.getLogger(__name__)

# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address)

router = APIRouter(prefix="/api/v1/auth", tags=["authentication"])
security = HTTPBearer()

# Initialize services
jwt_manager = JWTManager()
password_hasher = PasswordHasher()
token_blacklist = TokenBlacklist()


# ============================================================================
# Authentication Dependencies (for protecting routes)
# ============================================================================

async def get_current_user_dependency(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> dict:
    """
    Dependency function to get current authenticated user.
    
    Use this as a dependency in protected routes:
    
    @app.get("/api/v1/protected")
    async def protected_route(current_user = Depends(get_current_user_dependency)):
        # Only authenticated users can access this
        pass
    
    Returns:
        dict: User information (user_id, email, name, role)
    
    Raises:
        HTTPException: 401 if token is invalid or expired
    """
    token = credentials.credentials
    
    try:
        # Verify access token
        payload = jwt_manager.verify_access_token(token)
        
        # Check if token is blacklisted
        if await token_blacklist.is_revoked(token):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has been revoked"
            )
        
        # Get user info from token payload
        user_id = payload.get("sub")
        email = payload.get("email")
        
        # Find user in database
        user = await _get_user_by_id(db, user_id)
        
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or inactive"
            )
        
        # Return user info (exclude password_hash)
        return {
            "user_id": str(user.id),
            "email": user.email,
            "name": user.name,
            "role": user.role
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Authentication error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )


async def get_current_admin_user(
    current_user: dict = Depends(get_current_user_dependency)
) -> dict:
    """
    Dependency function to require admin role.
    
    Use this for admin-only routes.
    """
    if current_user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user


# Request/Response Models
class LoginRequest(BaseModel):
    """Login credentials with validation"""
    email: str = Field(..., pattern=r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', 
                       description="Valid email address")
    password: str = Field(..., min_length=8, max_length=128,
                         description="Password (8-128 characters)")


class RegisterRequest(BaseModel):
    """User registration with validation"""
    email: str = Field(..., pattern=r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$',
                       description="Valid email address")
    password: str = Field(..., min_length=8, max_length=128,
                         description="Strong password (min 8 chars, recommended: uppercase, lowercase, numbers, symbols)")
    name: str = Field(..., min_length=2, max_length=100,
                     description="User's full name")
    role: str = Field(default="viewer", pattern=r'^(admin|developer|viewer)$',
                     description="User role: admin, developer, or viewer")


class UserResponse(BaseModel):
    """User information"""
    user_id: str
    email: str
    name: str
    role: str


class TokenResponse(BaseModel):
    """Authentication token response"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserResponse


# Deprecated in-memory user storage (REMOVED - now using database only)
# This was replaced with PostgreSQL User model in Phase 4
_users_db_deprecated = {
    # Kept for reference only - DO NOT USE
    # All users now in PostgreSQL users table
}

# Default tenant ID (from database)
DEFAULT_TENANT_ID = "371191e4-9748-4b2a-9c7f-2d986463afa7"


async def _get_user_by_email(db: AsyncSession, email: str):
    """Helper function to get user by email from database"""
    from maestro_ml.models.database import User
    from sqlalchemy import select
    
    stmt = select(User).where(User.email == email)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def _get_user_by_id(db: AsyncSession, user_id: str):
    """Helper function to get user by ID from database"""
    from maestro_ml.models.database import User
    from sqlalchemy import select
    import uuid
    
    try:
        user_uuid = uuid.UUID(user_id) if isinstance(user_id, str) else user_id
        stmt = select(User).where(User.id == user_uuid)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()
    except (ValueError, AttributeError):
        return None


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("5/minute")  # Rate limit: 5 registrations per minute per IP
async def register(
    request: Request,  # Required for rate limiting
    register_request: RegisterRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Register a new user (Rate limited: 5/minute)
    
    Creates a new user account in the database and returns authentication tokens.
    
    Security:
    - Email validation
    - Password strength requirements (min 8 chars)
    - Rate limiting to prevent abuse
    """
    from maestro_ml.models.database import User
    import uuid
    
    # Check if user already exists
    existing_user = await _get_user_by_email(db, register_request.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this email already exists"
        )
    
    # Hash password
    password_hash = password_hasher.hash_password(register_request.password)
    
    # Create user in database
    new_user = User(
        id=uuid.uuid4(),
        tenant_id=uuid.UUID(DEFAULT_TENANT_ID),  # Use default tenant for now
        email=register_request.email,
        password_hash=password_hash,
        name=register_request.name,
        role=register_request.role,
        is_active=True,
        is_verified=False
    )
    
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    
    # Generate tokens
    tokens = jwt_manager.create_token_pair(
        user_id=str(new_user.id),
        email=new_user.email,
        roles=[new_user.role]
    )
    
    logger.info(f"User registered: {register_request.email} (ID: {new_user.id})")
    
    return TokenResponse(
        access_token=tokens.access_token,
        refresh_token=tokens.refresh_token,
        expires_in=tokens.expires_in,
        user=UserResponse(
            user_id=str(new_user.id),
            email=new_user.email,
            name=new_user.name,
            role=new_user.role
        )
    )


@router.post("/login", response_model=TokenResponse)
@limiter.limit("10/minute")  # Rate limit: 10 login attempts per minute per IP
async def login(
    request: Request,  # Required for rate limiting
    login_request: LoginRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Authenticate user and get tokens (Rate limited: 10/minute)
    
    Returns access and refresh tokens for valid credentials.
    
    Security:
    - Rate limiting to prevent brute force attacks
    - Passwords hashed with bcrypt
    - Invalid credentials logged
    """
    # Find user in database
    user = await _get_user_by_email(db, login_request.email)
    if not user or not user.is_active:
        # Use generic message to prevent user enumeration
        logger.warning(f"Failed login attempt for: {login_request.email}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
    # Verify password
    if not password_hasher.verify_password(login_request.password, user.password_hash):
        logger.warning(f"Failed login attempt (wrong password) for: {login_request.email}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
    # Update last login timestamp
    from datetime import datetime
    user.last_login_at = datetime.utcnow()
    await db.commit()
    
    # Generate tokens
    tokens = jwt_manager.create_token_pair(
        user_id=str(user.id),
        email=user.email,
        roles=[user.role]
    )
    
    logger.info(f"User logged in: {login_request.email} (ID: {user.id})")
    
    return TokenResponse(
        access_token=tokens.access_token,
        refresh_token=tokens.refresh_token,
        expires_in=tokens.expires_in,
        user=UserResponse(
            user_id=str(user.id),
            email=user.email,
            name=user.name,
            role=user.role
        )
    )

@router.post("/logout")
async def logout(
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """
    Logout user and invalidate token
    
    Adds the access token to the blacklist.
    """
    token = credentials.credentials
    
    # Add token to blacklist
    await token_blacklist.blacklist_token(token)
    
    logger.info("User logged out")
    
    return {"message": "Successfully logged out"}


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """
    Refresh access token
    
    Uses refresh token to get a new access token.
    """
    refresh_token = credentials.credentials
    
    try:
        # Verify refresh token
        payload = jwt_manager.verify_refresh_token(refresh_token)
        
        # Check if blacklisted
        if await token_blacklist.is_revoked(refresh_token):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has been revoked"
            )
        
        # Get user info from token
        user_id = payload.get("sub")
        email = payload.get("email")
        roles = payload.get("roles", [])
        
        # Find user in database
        user = await _get_user_by_id(db, user_id)
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or inactive"
            )
        
        # Generate new tokens
        tokens = jwt_manager.create_token_pair(
            user_id=str(user.id),
            email=user.email,
            roles=[user.role]
        )
        
        logger.info(f"Token refreshed for user: {user.email}")
        
        return TokenResponse(
            access_token=tokens.access_token,
            refresh_token=tokens.refresh_token,
            expires_in=tokens.expires_in,
            user=UserResponse(
                user_id=str(user.id),
                email=user["email"],
                name=user["name"],
                role=user["role"]
            )
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token"
        )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: dict = Depends(get_current_user_dependency)
):
    """
    Get current user information
    
    Returns the authenticated user's profile.
    """
    return UserResponse(
        user_id=current_user["user_id"],
        email=current_user["email"],
        name=current_user["name"],
        role=current_user["role"]
    )


@router.get("/health")
async def auth_health():
    """Authentication service health check"""
    return {
        "status": "healthy",
        "service": "authentication",
        "jwt_configured": jwt_manager.secret_key != "CHANGE_ME_IN_PRODUCTION"
    }
