"""
Authentication Dependencies
"""

from fastapi import Depends, HTTPException, status, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials, APIKeyHeader
from jose import JWTError, jwt
from datetime import datetime, timedelta
from typing import Optional

from ..config import settings


# Security schemes
bearer_scheme = HTTPBearer(auto_error=False)
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.access_token_expire_minutes)

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)
    return encoded_jwt


def verify_token(credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme)) -> Optional[dict]:
    """Verify JWT token"""
    if not credentials:
        return None

    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.secret_key,
            algorithms=[settings.algorithm]
        )
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


def verify_api_key(api_key: Optional[str] = Security(api_key_header)) -> Optional[str]:
    """Verify API key"""
    if not settings.api_key_enabled:
        return None

    if not api_key:
        return None

    if api_key in settings.api_keys:
        return api_key

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid API key"
    )


async def get_current_user(
    token_payload: Optional[dict] = Depends(verify_token),
    api_key: Optional[str] = Depends(verify_api_key)
) -> dict:
    """
    Get current user from JWT token or API key

    For now, authentication is optional. Returns None if no credentials provided.
    In production, remove the if statement to enforce authentication.
    """
    # Optional authentication - remove this in production
    if not token_payload and not api_key:
        return {"user_id": "anonymous", "authenticated": False}

    if token_payload:
        return {"user_id": token_payload.get("sub"), "authenticated": True}

    if api_key:
        return {"user_id": "api_key_user", "authenticated": True, "api_key": api_key}

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required"
    )
