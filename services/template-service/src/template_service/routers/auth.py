"""
Authentication Router
Endpoints for user authentication and token management
"""

from datetime import timedelta

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from ..auth import (
    Token,
    User,
    LoginRequest,
    authenticate_user,
    create_access_token,
    get_current_active_user,
    create_user,
    ACCESS_TOKEN_EXPIRE_MINUTES
)

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/v1/auth", tags=["authentication"])


@router.post("/token", response_model=Token)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends()
):
    """
    OAuth2 compatible token login endpoint

    Use this endpoint with OAuth2 password flow:
    - **username**: Your username
    - **password**: Your password

    Returns JWT access token for subsequent API calls
    """
    user = authenticate_user(form_data.username, form_data.password)

    if not user:
        logger.warning(
            "login_failed",
            username=form_data.username,
            client_ip="unknown"  # TODO: Extract from request
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={
            "sub": user.username,
            "email": user.email,
            "scopes": user.scopes
        },
        expires_delta=access_token_expires
    )

    logger.info(
        "user_logged_in",
        username=user.username,
        token_expires_minutes=ACCESS_TOKEN_EXPIRE_MINUTES
    )

    return Token(
        access_token=access_token,
        token_type="bearer",
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60  # Convert to seconds
    )


@router.post("/login", response_model=Token)
async def login(login_request: LoginRequest):
    """
    Alternative login endpoint with JSON body

    Use this endpoint if you prefer JSON over form data:
    ```json
    {
      "username": "developer",
      "password": "dev123"
    }
    ```

    Returns JWT access token
    """
    user = authenticate_user(login_request.username, login_request.password)

    if not user:
        logger.warning(
            "json_login_failed",
            username=login_request.username
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password"
        )

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={
            "sub": user.username,
            "email": user.email,
            "scopes": user.scopes
        },
        expires_delta=access_token_expires
    )

    logger.info(
        "user_logged_in_json",
        username=user.username
    )

    return Token(
        access_token=access_token,
        token_type="bearer",
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )


@router.get("/me", response_model=User)
async def read_users_me(current_user: User = Depends(get_current_active_user)):
    """
    Get current user information

    Returns the authenticated user's profile
    """
    return current_user


@router.post("/logout")
async def logout(current_user: User = Depends(get_current_active_user)):
    """
    Logout endpoint (client-side token invalidation)

    Since JWTs are stateless, actual logout happens client-side by discarding the token.
    This endpoint is provided for logging purposes.
    """
    logger.info("user_logged_out", username=current_user.username)

    return {
        "message": "Successfully logged out",
        "username": current_user.username
    }


@router.post("/refresh", response_model=Token)
async def refresh_token(current_user: User = Depends(get_current_active_user)):
    """
    Refresh access token

    Generates a new access token for the current user
    """
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={
            "sub": current_user.username,
            "email": current_user.email,
            "scopes": current_user.scopes
        },
        expires_delta=access_token_expires
    )

    logger.info("token_refreshed", username=current_user.username)

    return Token(
        access_token=access_token,
        token_type="bearer",
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )


# ============================================================================
# Development/Testing Endpoints (Remove in production)
# ============================================================================

@router.post("/dev/create-user", response_model=User, include_in_schema=False)
async def create_test_user(
    username: str,
    password: str,
    email: str = None,
    is_admin: bool = False
):
    """
    [DEV ONLY] Create a test user

    WARNING: This endpoint should be removed in production or protected with admin auth
    """
    try:
        user = create_user(
            username=username,
            password=password,
            email=email,
            is_admin=is_admin,
            scopes=["templates:read", "templates:write"] if not is_admin else ["admin"]
        )

        logger.info("dev_user_created", username=username)

        return user

    except Exception as e:
        logger.error("dev_user_creation_failed", username=username, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to create user: {str(e)}"
        )
