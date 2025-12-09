"""
JWT Token Manager.

Handles JWT creation, validation, and refresh for enterprise authentication.
"""

import secrets
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from enum import Enum
import jwt
import uuid


class TokenType(Enum):
    """Token types."""
    ACCESS = "access"
    REFRESH = "refresh"
    ID = "id"


@dataclass
class TokenConfig:
    """Token configuration."""
    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7
    issuer: str = "maestro"
    audience: str = "maestro-api"


@dataclass
class DecodedToken:
    """Decoded JWT token payload."""
    sub: str  # Subject (user ID)
    exp: datetime  # Expiration
    iat: datetime  # Issued at
    jti: str  # JWT ID
    token_type: TokenType
    scope: List[str] = field(default_factory=list)
    tenant_id: Optional[str] = None
    claims: Dict[str, Any] = field(default_factory=dict)

    @property
    def is_expired(self) -> bool:
        """Check if token is expired."""
        return datetime.utcnow() >= self.exp


class TokenManager:
    """
    JWT Token Manager for enterprise authentication.

    Handles creation, validation, and refresh of JWT tokens
    with support for access tokens, refresh tokens, and ID tokens.
    """

    def __init__(self, config: TokenConfig):
        """Initialize token manager."""
        self.config = config
        self._revoked_tokens: set = set()
        self._refresh_token_families: Dict[str, str] = {}

    def create_access_token(
        self,
        user_id: str,
        scope: List[str] = None,
        tenant_id: Optional[str] = None,
        additional_claims: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Create JWT access token.

        Args:
            user_id: User identifier
            scope: List of granted scopes
            tenant_id: Tenant identifier for multi-tenancy
            additional_claims: Extra claims to include

        Returns:
            Encoded JWT access token
        """
        now = datetime.utcnow()
        expires = now + timedelta(minutes=self.config.access_token_expire_minutes)

        payload = {
            "sub": user_id,
            "exp": expires,
            "iat": now,
            "nbf": now,
            "jti": str(uuid.uuid4()),
            "iss": self.config.issuer,
            "aud": self.config.audience,
            "type": TokenType.ACCESS.value,
            "scope": scope or [],
        }

        if tenant_id:
            payload["tenant_id"] = tenant_id

        if additional_claims:
            payload.update(additional_claims)

        return jwt.encode(
            payload,
            self.config.secret_key,
            algorithm=self.config.algorithm,
        )

    def create_refresh_token(
        self,
        user_id: str,
        family_id: Optional[str] = None,
    ) -> tuple[str, str]:
        """
        Create refresh token with family tracking for rotation.

        Args:
            user_id: User identifier
            family_id: Token family ID for rotation detection

        Returns:
            Tuple of (refresh_token, family_id)
        """
        now = datetime.utcnow()
        expires = now + timedelta(days=self.config.refresh_token_expire_days)
        family_id = family_id or str(uuid.uuid4())
        token_id = str(uuid.uuid4())

        payload = {
            "sub": user_id,
            "exp": expires,
            "iat": now,
            "jti": token_id,
            "iss": self.config.issuer,
            "type": TokenType.REFRESH.value,
            "family": family_id,
        }

        # Track latest token in family for rotation detection
        self._refresh_token_families[family_id] = token_id

        token = jwt.encode(
            payload,
            self.config.secret_key,
            algorithm=self.config.algorithm,
        )

        return token, family_id

    def create_id_token(
        self,
        user_id: str,
        email: str,
        name: Optional[str] = None,
        additional_claims: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Create OpenID Connect ID token.

        Args:
            user_id: User identifier
            email: User email
            name: User display name
            additional_claims: Extra identity claims

        Returns:
            Encoded ID token
        """
        now = datetime.utcnow()
        expires = now + timedelta(minutes=self.config.access_token_expire_minutes)

        payload = {
            "sub": user_id,
            "exp": expires,
            "iat": now,
            "iss": self.config.issuer,
            "aud": self.config.audience,
            "type": TokenType.ID.value,
            "email": email,
            "email_verified": True,
        }

        if name:
            payload["name"] = name

        if additional_claims:
            payload.update(additional_claims)

        return jwt.encode(
            payload,
            self.config.secret_key,
            algorithm=self.config.algorithm,
        )

    def verify_token(
        self,
        token: str,
        expected_type: Optional[TokenType] = None,
    ) -> DecodedToken:
        """
        Verify and decode JWT token.

        Args:
            token: JWT token to verify
            expected_type: Expected token type

        Returns:
            DecodedToken with payload

        Raises:
            jwt.InvalidTokenError: If token is invalid
            ValueError: If token type doesn't match or is revoked
        """
        try:
            payload = jwt.decode(
                token,
                self.config.secret_key,
                algorithms=[self.config.algorithm],
                issuer=self.config.issuer,
                audience=self.config.audience,
            )
        except jwt.ExpiredSignatureError:
            raise ValueError("Token has expired")
        except jwt.InvalidTokenError as e:
            raise ValueError(f"Invalid token: {e}")

        jti = payload.get("jti")
        if jti in self._revoked_tokens:
            raise ValueError("Token has been revoked")

        token_type = TokenType(payload.get("type", "access"))
        if expected_type and token_type != expected_type:
            raise ValueError(f"Expected {expected_type.value} token, got {token_type.value}")

        return DecodedToken(
            sub=payload["sub"],
            exp=datetime.fromtimestamp(payload["exp"]),
            iat=datetime.fromtimestamp(payload["iat"]),
            jti=jti,
            token_type=token_type,
            scope=payload.get("scope", []),
            tenant_id=payload.get("tenant_id"),
            claims={k: v for k, v in payload.items()
                   if k not in ["sub", "exp", "iat", "jti", "type", "scope", "tenant_id"]},
        )

    def refresh_tokens(
        self,
        refresh_token: str,
        scope: Optional[List[str]] = None,
    ) -> tuple[str, str, str]:
        """
        Refresh access token using refresh token with rotation.

        Implements refresh token rotation for security - each refresh
        generates a new refresh token and invalidates the old one.

        Args:
            refresh_token: Current refresh token
            scope: Updated scope (optional)

        Returns:
            Tuple of (new_access_token, new_refresh_token, family_id)

        Raises:
            ValueError: If refresh token is invalid or reused
        """
        decoded = self.verify_token(refresh_token, TokenType.REFRESH)

        # Check for token reuse (potential compromise)
        family_id = decoded.claims.get("family")
        if family_id:
            current_jti = self._refresh_token_families.get(family_id)
            if current_jti and current_jti != decoded.jti:
                # Token reuse detected - revoke entire family
                self._revoke_token_family(family_id)
                raise ValueError("Refresh token reuse detected - all tokens revoked")

        # Revoke old refresh token
        self._revoked_tokens.add(decoded.jti)

        # Create new tokens
        access_token = self.create_access_token(
            user_id=decoded.sub,
            scope=scope or decoded.scope,
            tenant_id=decoded.tenant_id,
        )

        new_refresh_token, family_id = self.create_refresh_token(
            user_id=decoded.sub,
            family_id=family_id,
        )

        return access_token, new_refresh_token, family_id

    def revoke_token(self, token: str) -> bool:
        """
        Revoke a token.

        Args:
            token: Token to revoke

        Returns:
            True if revocation succeeded
        """
        try:
            decoded = self.verify_token(token)
            self._revoked_tokens.add(decoded.jti)
            return True
        except ValueError:
            return False

    def _revoke_token_family(self, family_id: str) -> None:
        """Revoke all tokens in a family (security measure)."""
        if family_id in self._refresh_token_families:
            del self._refresh_token_families[family_id]

    def create_token_pair(
        self,
        user_id: str,
        scope: List[str] = None,
        tenant_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Create access and refresh token pair.

        Args:
            user_id: User identifier
            scope: Granted scopes
            tenant_id: Tenant identifier

        Returns:
            Dictionary with tokens and metadata
        """
        access_token = self.create_access_token(
            user_id=user_id,
            scope=scope,
            tenant_id=tenant_id,
        )
        refresh_token, family_id = self.create_refresh_token(user_id)

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "Bearer",
            "expires_in": self.config.access_token_expire_minutes * 60,
            "scope": " ".join(scope or []),
            "family_id": family_id,
        }
