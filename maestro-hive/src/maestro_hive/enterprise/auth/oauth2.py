"""
OAuth2 Authentication Provider.

Implements OAuth2 authorization code flow with PKCE support.
Supports multiple providers (Google, GitHub, Azure AD).
"""

import secrets
import hashlib
import base64
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional, List, Dict, Any
from urllib.parse import urlencode
import aiohttp


class OAuth2ProviderType(Enum):
    """Supported OAuth2 providers."""
    GOOGLE = "google"
    GITHUB = "github"
    AZURE = "azure"
    CUSTOM = "custom"


@dataclass
class OAuth2Config:
    """OAuth2 configuration."""
    client_id: str
    client_secret: str
    redirect_uri: str
    provider: OAuth2ProviderType = OAuth2ProviderType.CUSTOM
    authorization_endpoint: str = ""
    token_endpoint: str = ""
    userinfo_endpoint: str = ""
    scopes: List[str] = field(default_factory=lambda: ["openid", "profile", "email"])
    use_pkce: bool = True

    def __post_init__(self):
        """Set provider-specific endpoints."""
        if self.provider == OAuth2ProviderType.GOOGLE:
            self.authorization_endpoint = "https://accounts.google.com/o/oauth2/v2/auth"
            self.token_endpoint = "https://oauth2.googleapis.com/token"
            self.userinfo_endpoint = "https://openidconnect.googleapis.com/v1/userinfo"
        elif self.provider == OAuth2ProviderType.GITHUB:
            self.authorization_endpoint = "https://github.com/login/oauth/authorize"
            self.token_endpoint = "https://github.com/login/oauth/access_token"
            self.userinfo_endpoint = "https://api.github.com/user"
        elif self.provider == OAuth2ProviderType.AZURE:
            self.authorization_endpoint = "https://login.microsoftonline.com/common/oauth2/v2.0/authorize"
            self.token_endpoint = "https://login.microsoftonline.com/common/oauth2/v2.0/token"
            self.userinfo_endpoint = "https://graph.microsoft.com/v1.0/me"


@dataclass
class TokenPair:
    """OAuth2 token pair."""
    access_token: str
    refresh_token: Optional[str]
    token_type: str = "Bearer"
    expires_in: int = 3600
    scope: List[str] = field(default_factory=list)
    id_token: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)

    @property
    def is_expired(self) -> bool:
        """Check if access token is expired."""
        expiry = self.created_at + timedelta(seconds=self.expires_in)
        return datetime.utcnow() >= expiry

    @property
    def expires_at(self) -> datetime:
        """Get token expiry time."""
        return self.created_at + timedelta(seconds=self.expires_in)


@dataclass
class PKCEChallenge:
    """PKCE challenge for secure OAuth2 flow."""
    verifier: str
    challenge: str
    method: str = "S256"


class OAuth2Provider:
    """
    OAuth2 authentication provider with PKCE support.

    Implements secure OAuth2 authorization code flow for
    enterprise authentication requirements.
    """

    def __init__(self, config: OAuth2Config):
        """Initialize OAuth2 provider."""
        self.config = config
        self._pending_states: Dict[str, PKCEChallenge] = {}
        self._session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create HTTP session."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    def _generate_pkce_challenge(self) -> PKCEChallenge:
        """Generate PKCE code verifier and challenge."""
        verifier = secrets.token_urlsafe(32)
        digest = hashlib.sha256(verifier.encode()).digest()
        challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode()
        return PKCEChallenge(verifier=verifier, challenge=challenge)

    def generate_authorization_url(
        self,
        scope: Optional[List[str]] = None,
        state: Optional[str] = None,
    ) -> tuple[str, str]:
        """
        Generate OAuth2 authorization URL.

        Args:
            scope: OAuth2 scopes (uses config default if not provided)
            state: Custom state parameter (generated if not provided)

        Returns:
            Tuple of (authorization_url, state)
        """
        state = state or secrets.token_urlsafe(16)
        scopes = scope or self.config.scopes

        params = {
            "client_id": self.config.client_id,
            "redirect_uri": self.config.redirect_uri,
            "response_type": "code",
            "scope": " ".join(scopes),
            "state": state,
        }

        if self.config.use_pkce:
            pkce = self._generate_pkce_challenge()
            self._pending_states[state] = pkce
            params["code_challenge"] = pkce.challenge
            params["code_challenge_method"] = pkce.method

        url = f"{self.config.authorization_endpoint}?{urlencode(params)}"
        return url, state

    async def exchange_code(
        self,
        code: str,
        state: str,
    ) -> TokenPair:
        """
        Exchange authorization code for tokens.

        Args:
            code: Authorization code from callback
            state: State parameter for PKCE verification

        Returns:
            TokenPair with access and refresh tokens

        Raises:
            ValueError: If state is invalid or code exchange fails
        """
        data = {
            "client_id": self.config.client_id,
            "client_secret": self.config.client_secret,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": self.config.redirect_uri,
        }

        if self.config.use_pkce:
            if state not in self._pending_states:
                raise ValueError("Invalid state parameter")
            pkce = self._pending_states.pop(state)
            data["code_verifier"] = pkce.verifier

        session = await self._get_session()
        headers = {"Accept": "application/json"}

        async with session.post(
            self.config.token_endpoint,
            data=data,
            headers=headers,
        ) as response:
            if response.status != 200:
                error = await response.text()
                raise ValueError(f"Token exchange failed: {error}")

            result = await response.json()

            return TokenPair(
                access_token=result["access_token"],
                refresh_token=result.get("refresh_token"),
                token_type=result.get("token_type", "Bearer"),
                expires_in=result.get("expires_in", 3600),
                scope=result.get("scope", "").split(),
                id_token=result.get("id_token"),
            )

    async def refresh_token(self, refresh_token: str) -> TokenPair:
        """
        Refresh expired access token.

        Args:
            refresh_token: Valid refresh token

        Returns:
            New TokenPair with fresh access token
        """
        data = {
            "client_id": self.config.client_id,
            "client_secret": self.config.client_secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        }

        session = await self._get_session()
        headers = {"Accept": "application/json"}

        async with session.post(
            self.config.token_endpoint,
            data=data,
            headers=headers,
        ) as response:
            if response.status != 200:
                error = await response.text()
                raise ValueError(f"Token refresh failed: {error}")

            result = await response.json()

            return TokenPair(
                access_token=result["access_token"],
                refresh_token=result.get("refresh_token", refresh_token),
                token_type=result.get("token_type", "Bearer"),
                expires_in=result.get("expires_in", 3600),
                scope=result.get("scope", "").split(),
            )

    async def get_user_info(self, access_token: str) -> Dict[str, Any]:
        """
        Fetch user information from provider.

        Args:
            access_token: Valid access token

        Returns:
            User information dictionary
        """
        session = await self._get_session()
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json",
        }

        async with session.get(
            self.config.userinfo_endpoint,
            headers=headers,
        ) as response:
            if response.status != 200:
                error = await response.text()
                raise ValueError(f"Failed to fetch user info: {error}")

            return await response.json()

    async def revoke_token(self, token: str) -> bool:
        """
        Revoke OAuth2 token.

        Args:
            token: Token to revoke

        Returns:
            True if revocation succeeded
        """
        # Provider-specific revocation endpoint
        revoke_endpoints = {
            OAuth2ProviderType.GOOGLE: "https://oauth2.googleapis.com/revoke",
            OAuth2ProviderType.GITHUB: None,  # GitHub doesn't support revocation
            OAuth2ProviderType.AZURE: "https://login.microsoftonline.com/common/oauth2/v2.0/logout",
        }

        endpoint = revoke_endpoints.get(self.config.provider)
        if not endpoint:
            return False

        session = await self._get_session()
        data = {"token": token}

        async with session.post(endpoint, data=data) as response:
            return response.status == 200

    async def close(self):
        """Close HTTP session."""
        if self._session and not self._session.closed:
            await self._session.close()

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
