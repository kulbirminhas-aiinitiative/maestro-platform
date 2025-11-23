"""
OpenID Connect (OIDC) authentication provider for enterprise SSO.

Supports:
- Generic OIDC providers
- Azure AD / Entra ID
- Google Cloud Identity
- Okta
- Auth0
"""

from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from enum import Enum
import httpx
from authlib.integrations.httpx_client import AsyncOAuth2Client
from authlib.oidc.core import CodeIDToken
from pydantic import BaseModel
from maestro_core_logging import get_logger

logger = get_logger(__name__)


class OIDCProviderType(str, Enum):
    """Supported OIDC provider types."""
    GENERIC = "generic"
    AZURE_AD = "azure_ad"
    GOOGLE = "google"
    OKTA = "okta"
    AUTH0 = "auth0"


class OIDCUserInfo(BaseModel):
    """User information from OIDC provider."""
    sub: str  # Subject identifier
    email: Optional[str] = None
    email_verified: Optional[bool] = None
    name: Optional[str] = None
    given_name: Optional[str] = None
    family_name: Optional[str] = None
    preferred_username: Optional[str] = None
    picture: Optional[str] = None
    locale: Optional[str] = None
    groups: List[str] = field(default_factory=list)
    roles: List[str] = field(default_factory=list)
    tenant_id: Optional[str] = None

    class Config:
        extra = "allow"  # Allow additional claims


@dataclass
class OIDCProviderConfig:
    """Configuration for an OIDC provider."""
    name: str
    provider_type: OIDCProviderType
    client_id: str
    client_secret: str
    discovery_url: Optional[str] = None
    authorization_endpoint: Optional[str] = None
    token_endpoint: Optional[str] = None
    userinfo_endpoint: Optional[str] = None
    jwks_uri: Optional[str] = None
    issuer: Optional[str] = None
    scopes: List[str] = field(default_factory=lambda: ["openid", "email", "profile"])
    redirect_uri: str = ""
    # Azure AD specific
    tenant_id: Optional[str] = None
    # Additional configuration
    claim_mapping: Dict[str, str] = field(default_factory=dict)
    group_claim: str = "groups"
    role_claim: str = "roles"


class OIDCProvider:
    """
    OIDC authentication provider with automatic discovery and token validation.

    Usage:
        config = OIDCProviderConfig(
            name="azure",
            provider_type=OIDCProviderType.AZURE_AD,
            client_id="your-client-id",
            client_secret="your-client-secret",
            tenant_id="your-tenant-id",
            redirect_uri="https://app.example.com/auth/callback"
        )
        provider = OIDCProvider(config)
        await provider.initialize()

        # Get authorization URL
        auth_url = await provider.get_authorization_url(state="random-state")

        # Exchange code for tokens
        tokens = await provider.exchange_code(code="auth-code")

        # Get user info
        user_info = await provider.get_user_info(tokens["access_token"])
    """

    def __init__(self, config: OIDCProviderConfig):
        self.config = config
        self._metadata: Optional[Dict[str, Any]] = None
        self._client: Optional[AsyncOAuth2Client] = None

    async def initialize(self) -> None:
        """
        Initialize provider by fetching OIDC discovery metadata.

        This should be called before using the provider.
        """
        if self.config.discovery_url:
            await self._fetch_discovery_metadata()
        else:
            self._set_default_endpoints()

        self._client = AsyncOAuth2Client(
            client_id=self.config.client_id,
            client_secret=self.config.client_secret,
            redirect_uri=self.config.redirect_uri,
            scope=" ".join(self.config.scopes)
        )

        logger.info(
            "OIDC provider initialized",
            provider=self.config.name,
            type=self.config.provider_type
        )

    async def _fetch_discovery_metadata(self) -> None:
        """Fetch OIDC discovery document."""
        async with httpx.AsyncClient() as client:
            response = await client.get(self.config.discovery_url)
            response.raise_for_status()
            self._metadata = response.json()

        # Set endpoints from metadata
        self.config.authorization_endpoint = self._metadata.get("authorization_endpoint")
        self.config.token_endpoint = self._metadata.get("token_endpoint")
        self.config.userinfo_endpoint = self._metadata.get("userinfo_endpoint")
        self.config.jwks_uri = self._metadata.get("jwks_uri")
        self.config.issuer = self._metadata.get("issuer")

        logger.debug("OIDC metadata fetched", issuer=self.config.issuer)

    def _set_default_endpoints(self) -> None:
        """Set default endpoints based on provider type."""
        if self.config.provider_type == OIDCProviderType.AZURE_AD:
            tenant = self.config.tenant_id or "common"
            base_url = f"https://login.microsoftonline.com/{tenant}/oauth2/v2.0"
            self.config.authorization_endpoint = f"{base_url}/authorize"
            self.config.token_endpoint = f"{base_url}/token"
            self.config.userinfo_endpoint = "https://graph.microsoft.com/oidc/userinfo"
            self.config.jwks_uri = f"https://login.microsoftonline.com/{tenant}/discovery/v2.0/keys"
            self.config.issuer = f"https://login.microsoftonline.com/{tenant}/v2.0"

        elif self.config.provider_type == OIDCProviderType.GOOGLE:
            self.config.authorization_endpoint = "https://accounts.google.com/o/oauth2/v2/auth"
            self.config.token_endpoint = "https://oauth2.googleapis.com/token"
            self.config.userinfo_endpoint = "https://openidconnect.googleapis.com/v1/userinfo"
            self.config.jwks_uri = "https://www.googleapis.com/oauth2/v3/certs"
            self.config.issuer = "https://accounts.google.com"

        elif self.config.provider_type == OIDCProviderType.OKTA:
            # Requires discovery_url to be set for Okta
            raise ValueError("Okta requires discovery_url to be set")

    async def get_authorization_url(
        self,
        state: str,
        nonce: Optional[str] = None,
        prompt: Optional[str] = None,
        login_hint: Optional[str] = None,
        additional_params: Optional[Dict[str, str]] = None
    ) -> str:
        """
        Generate authorization URL for redirecting user to IdP.

        Args:
            state: Random state for CSRF protection
            nonce: Nonce for replay protection
            prompt: Prompt behavior (none, login, consent, select_account)
            login_hint: Pre-fill username
            additional_params: Additional query parameters

        Returns:
            Authorization URL to redirect user to
        """
        params = {
            "response_type": "code",
            "client_id": self.config.client_id,
            "redirect_uri": self.config.redirect_uri,
            "scope": " ".join(self.config.scopes),
            "state": state,
        }

        if nonce:
            params["nonce"] = nonce
        if prompt:
            params["prompt"] = prompt
        if login_hint:
            params["login_hint"] = login_hint
        if additional_params:
            params.update(additional_params)

        # Build URL
        query = "&".join(f"{k}={v}" for k, v in params.items())
        return f"{self.config.authorization_endpoint}?{query}"

    async def exchange_code(
        self,
        code: str,
        code_verifier: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Exchange authorization code for tokens.

        Args:
            code: Authorization code from callback
            code_verifier: PKCE code verifier if used

        Returns:
            Token response containing access_token, id_token, refresh_token
        """
        data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": self.config.redirect_uri,
            "client_id": self.config.client_id,
            "client_secret": self.config.client_secret,
        }

        if code_verifier:
            data["code_verifier"] = code_verifier

        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.config.token_endpoint,
                data=data,
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            response.raise_for_status()
            tokens = response.json()

        logger.info("OIDC code exchanged for tokens", provider=self.config.name)
        return tokens

    async def refresh_access_token(self, refresh_token: str) -> Dict[str, Any]:
        """
        Refresh access token using refresh token.

        Args:
            refresh_token: Valid refresh token

        Returns:
            New token response
        """
        data = {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": self.config.client_id,
            "client_secret": self.config.client_secret,
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.config.token_endpoint,
                data=data,
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            response.raise_for_status()
            return response.json()

    async def get_user_info(self, access_token: str) -> OIDCUserInfo:
        """
        Get user information from OIDC provider.

        Args:
            access_token: Valid access token

        Returns:
            User information
        """
        async with httpx.AsyncClient() as client:
            response = await client.get(
                self.config.userinfo_endpoint,
                headers={"Authorization": f"Bearer {access_token}"}
            )
            response.raise_for_status()
            data = response.json()

        # Extract groups and roles from configured claims
        groups = data.get(self.config.group_claim, [])
        roles = data.get(self.config.role_claim, [])

        # Handle Azure AD specific tenant
        tenant_id = data.get("tid") if self.config.provider_type == OIDCProviderType.AZURE_AD else None

        user_info = OIDCUserInfo(
            sub=data["sub"],
            email=data.get("email"),
            email_verified=data.get("email_verified"),
            name=data.get("name"),
            given_name=data.get("given_name"),
            family_name=data.get("family_name"),
            preferred_username=data.get("preferred_username"),
            picture=data.get("picture"),
            locale=data.get("locale"),
            groups=groups if isinstance(groups, list) else [],
            roles=roles if isinstance(roles, list) else [],
            tenant_id=tenant_id
        )

        logger.info(
            "User info retrieved",
            provider=self.config.name,
            sub=user_info.sub,
            email=user_info.email
        )

        return user_info

    async def validate_id_token(self, id_token: str) -> Dict[str, Any]:
        """
        Validate ID token and return claims.

        Args:
            id_token: ID token from token response

        Returns:
            Validated token claims
        """
        # Fetch JWKS for validation
        async with httpx.AsyncClient() as client:
            response = await client.get(self.config.jwks_uri)
            response.raise_for_status()
            jwks = response.json()

        # Validate token using authlib
        from authlib.jose import jwt, JsonWebKey

        key_set = JsonWebKey.import_key_set(jwks)
        claims = jwt.decode(
            id_token,
            key_set,
            claims_options={
                "iss": {"essential": True, "value": self.config.issuer},
                "aud": {"essential": True, "value": self.config.client_id}
            }
        )
        claims.validate()

        return dict(claims)

    async def logout_url(
        self,
        id_token_hint: Optional[str] = None,
        post_logout_redirect_uri: Optional[str] = None
    ) -> Optional[str]:
        """
        Get logout URL for single logout.

        Args:
            id_token_hint: ID token for logout
            post_logout_redirect_uri: Where to redirect after logout

        Returns:
            Logout URL or None if not supported
        """
        if not self._metadata or "end_session_endpoint" not in self._metadata:
            return None

        params = []
        if id_token_hint:
            params.append(f"id_token_hint={id_token_hint}")
        if post_logout_redirect_uri:
            params.append(f"post_logout_redirect_uri={post_logout_redirect_uri}")

        endpoint = self._metadata["end_session_endpoint"]
        if params:
            return f"{endpoint}?{'&'.join(params)}"
        return endpoint


class OIDCProviderRegistry:
    """
    Registry for managing multiple OIDC providers.

    Usage:
        registry = OIDCProviderRegistry()
        await registry.register_provider(azure_config)
        await registry.register_provider(google_config)

        provider = registry.get_provider("azure")
        auth_url = await provider.get_authorization_url(state="...")
    """

    def __init__(self):
        self._providers: Dict[str, OIDCProvider] = {}

    async def register_provider(self, config: OIDCProviderConfig) -> None:
        """Register and initialize an OIDC provider."""
        provider = OIDCProvider(config)
        await provider.initialize()
        self._providers[config.name] = provider
        logger.info("OIDC provider registered", name=config.name)

    def get_provider(self, name: str) -> Optional[OIDCProvider]:
        """Get provider by name."""
        return self._providers.get(name)

    def list_providers(self) -> List[str]:
        """List all registered provider names."""
        return list(self._providers.keys())

    def remove_provider(self, name: str) -> None:
        """Remove provider from registry."""
        if name in self._providers:
            del self._providers[name]
            logger.info("OIDC provider removed", name=name)


# Pre-configured provider factories
def create_azure_ad_provider(
    client_id: str,
    client_secret: str,
    tenant_id: str,
    redirect_uri: str,
    name: str = "azure_ad"
) -> OIDCProviderConfig:
    """Create Azure AD OIDC provider configuration."""
    return OIDCProviderConfig(
        name=name,
        provider_type=OIDCProviderType.AZURE_AD,
        client_id=client_id,
        client_secret=client_secret,
        tenant_id=tenant_id,
        redirect_uri=redirect_uri,
        scopes=["openid", "email", "profile", "offline_access"],
        group_claim="groups",
        role_claim="roles"
    )


def create_google_provider(
    client_id: str,
    client_secret: str,
    redirect_uri: str,
    name: str = "google"
) -> OIDCProviderConfig:
    """Create Google OIDC provider configuration."""
    return OIDCProviderConfig(
        name=name,
        provider_type=OIDCProviderType.GOOGLE,
        client_id=client_id,
        client_secret=client_secret,
        redirect_uri=redirect_uri,
        scopes=["openid", "email", "profile"]
    )


def create_okta_provider(
    client_id: str,
    client_secret: str,
    okta_domain: str,
    redirect_uri: str,
    name: str = "okta"
) -> OIDCProviderConfig:
    """Create Okta OIDC provider configuration."""
    return OIDCProviderConfig(
        name=name,
        provider_type=OIDCProviderType.OKTA,
        client_id=client_id,
        client_secret=client_secret,
        discovery_url=f"https://{okta_domain}/.well-known/openid-configuration",
        redirect_uri=redirect_uri,
        scopes=["openid", "email", "profile", "groups"]
    )
