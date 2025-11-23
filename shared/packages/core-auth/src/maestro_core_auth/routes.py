"""
FastAPI routes for enterprise authentication.

Provides:
- SSO login/callback endpoints
- LDAP authentication
- Token management
- User profile
"""

import secrets
from typing import Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Depends, Query, Request, Response
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from maestro_core_logging import get_logger

from .oidc import OIDCProvider, OIDCProviderRegistry, OIDCUserInfo
from .ldap import LDAPProvider, LDAPProviderRegistry
from .provisioning import JITProvisioner, ProvisioningConfig
from .auth_manager import AuthManager
from .models import TokenResponse

logger = get_logger(__name__)


class LoginRequest(BaseModel):
    """Username/password login request."""
    username: str
    password: str
    mfa_code: Optional[str] = None


class SSOLoginResponse(BaseModel):
    """SSO login initiation response."""
    auth_url: str
    state: str
    provider: str


class SSOCallbackRequest(BaseModel):
    """SSO callback parameters."""
    code: str
    state: str


def create_auth_router(
    auth_manager: AuthManager,
    oidc_registry: OIDCProviderRegistry,
    ldap_registry: LDAPProviderRegistry,
    provisioner: JITProvisioner,
    get_db_session,  # Dependency for database session
    state_store: Dict[str, Dict[str, Any]] = None  # Simple state storage
) -> APIRouter:
    """
    Create authentication router with all SSO endpoints.

    Args:
        auth_manager: Core authentication manager
        oidc_registry: Registry of OIDC providers
        ldap_registry: Registry of LDAP providers
        provisioner: JIT user provisioner
        get_db_session: FastAPI dependency for DB session
        state_store: State storage for CSRF protection (use Redis in production)

    Returns:
        Configured FastAPI router
    """
    router = APIRouter(prefix="/auth", tags=["Authentication"])

    # Use dict for simple state storage (replace with Redis in production)
    if state_store is None:
        state_store = {}

    # Username/Password Login
    @router.post("/login", response_model=TokenResponse)
    async def login(
        request: LoginRequest,
        db_session: AsyncSession = Depends(get_db_session)
    ):
        """Authenticate with username and password."""
        user = await auth_manager.authenticate_user(
            username=request.username,
            password=request.password,
            db_session=db_session,
            mfa_code=request.mfa_code
        )

        if not user:
            raise HTTPException(status_code=401, detail="Invalid credentials")

        return await auth_manager.create_tokens(user)

    # SSO Login Initiation
    @router.get("/sso/{provider}/login")
    async def sso_login(
        provider: str,
        redirect_uri: Optional[str] = Query(None),
        prompt: Optional[str] = Query(None)
    ) -> SSOLoginResponse:
        """
        Initiate SSO login with specified provider.

        Args:
            provider: OIDC provider name (azure_ad, google, okta)
            redirect_uri: Where to redirect after login
            prompt: Login prompt behavior
        """
        oidc_provider = oidc_registry.get_provider(provider)
        if not oidc_provider:
            raise HTTPException(status_code=404, detail=f"Provider {provider} not found")

        # Generate state for CSRF protection
        state = secrets.token_urlsafe(32)

        # Store state with metadata
        state_store[state] = {
            "provider": provider,
            "redirect_uri": redirect_uri,
            "nonce": secrets.token_urlsafe(16)
        }

        # Generate authorization URL
        auth_url = await oidc_provider.get_authorization_url(
            state=state,
            nonce=state_store[state]["nonce"],
            prompt=prompt
        )

        logger.info("SSO login initiated", provider=provider, state=state[:8])

        return SSOLoginResponse(
            auth_url=auth_url,
            state=state,
            provider=provider
        )

    # SSO Callback
    @router.get("/sso/{provider}/callback")
    async def sso_callback(
        provider: str,
        code: str = Query(...),
        state: str = Query(...),
        error: Optional[str] = Query(None),
        error_description: Optional[str] = Query(None),
        db_session: AsyncSession = Depends(get_db_session)
    ):
        """
        Handle SSO callback from identity provider.

        This endpoint receives the authorization code after successful IdP login.
        """
        # Check for IdP errors
        if error:
            logger.error("SSO callback error", provider=provider, error=error, desc=error_description)
            raise HTTPException(
                status_code=400,
                detail=f"SSO error: {error_description or error}"
            )

        # Validate state
        if state not in state_store:
            raise HTTPException(status_code=400, detail="Invalid state parameter")

        state_data = state_store.pop(state)
        if state_data["provider"] != provider:
            raise HTTPException(status_code=400, detail="Provider mismatch")

        # Get OIDC provider
        oidc_provider = oidc_registry.get_provider(provider)
        if not oidc_provider:
            raise HTTPException(status_code=404, detail=f"Provider {provider} not found")

        try:
            # Exchange code for tokens
            tokens = await oidc_provider.exchange_code(code)

            # Get user info
            user_info = await oidc_provider.get_user_info(tokens["access_token"])

            # Provision user (create or update)
            provisioned = await provisioner.provision_oidc_user(
                user_info=user_info,
                provider_name=provider,
                db_session=db_session
            )

            # Create internal tokens
            # Note: Need to get the actual user object here
            # This is a simplified example
            internal_tokens = {
                "access_token": tokens.get("access_token"),
                "token_type": "bearer",
                "user_id": provisioned.user_id,
                "username": provisioned.username
            }

            logger.info(
                "SSO login successful",
                provider=provider,
                user_id=provisioned.user_id,
                action=provisioned.action
            )

            # Redirect to frontend with tokens or return them
            if state_data.get("redirect_uri"):
                # In production, use a more secure method to pass tokens
                redirect_url = f"{state_data['redirect_uri']}?login=success"
                return RedirectResponse(url=redirect_url)

            return {
                "status": "success",
                "user_id": provisioned.user_id,
                "username": provisioned.username,
                "action": provisioned.action,
                "tokens": internal_tokens
            }

        except Exception as e:
            logger.error("SSO callback processing error", error=str(e))
            raise HTTPException(status_code=500, detail=str(e))

    # LDAP Login
    @router.post("/ldap/{provider}/login", response_model=TokenResponse)
    async def ldap_login(
        provider: str,
        request: LoginRequest,
        db_session: AsyncSession = Depends(get_db_session)
    ):
        """Authenticate with LDAP/Active Directory."""
        ldap_provider = ldap_registry.get_provider(provider)
        if not ldap_provider:
            raise HTTPException(status_code=404, detail=f"LDAP provider {provider} not found")

        # Authenticate against LDAP
        user_info = await ldap_provider.authenticate(request.username, request.password)
        if not user_info:
            raise HTTPException(status_code=401, detail="Invalid credentials")

        # Provision user
        provisioned = await provisioner.provision_ldap_user(
            user_info=user_info,
            provider_name=provider,
            db_session=db_session
        )

        # Create tokens
        # Note: Need to get the actual user object
        # This is simplified
        return TokenResponse(
            access_token="...",  # Generate actual token
            refresh_token="...",
            token_type="bearer",
            expires_in=1800
        )

    # Token Refresh
    @router.post("/refresh", response_model=TokenResponse)
    async def refresh_token(
        refresh_token: str,
        db_session: AsyncSession = Depends(get_db_session)
    ):
        """Refresh access token."""
        try:
            return await auth_manager.refresh_tokens(refresh_token, db_session)
        except Exception as e:
            raise HTTPException(status_code=401, detail=str(e))

    # Logout
    @router.post("/logout")
    async def logout(
        request: Request,
        provider: Optional[str] = Query(None)
    ):
        """
        Logout user.

        If provider is specified and supports single logout,
        returns the IdP logout URL.
        """
        # Get token from header
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header[7:]
            # Invalidate session
            # await auth_manager.logout(user_id, token)

        # Get IdP logout URL if provider specified
        if provider:
            oidc_provider = oidc_registry.get_provider(provider)
            if oidc_provider:
                logout_url = await oidc_provider.logout_url()
                if logout_url:
                    return {"logout_url": logout_url}

        return {"status": "logged_out"}

    # List Available Providers
    @router.get("/providers")
    async def list_providers():
        """List available authentication providers."""
        return {
            "oidc": oidc_registry.list_providers(),
            "ldap": ldap_registry.list_providers()
        }

    # User Profile (from SSO)
    @router.get("/me")
    async def get_current_user_profile(
        request: Request,
        db_session: AsyncSession = Depends(get_db_session)
    ):
        """Get current user profile."""
        # Extract and validate token
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Not authenticated")

        # Decode token and return user info
        # This is a placeholder
        return {"message": "Implement based on your user model"}

    return router


# Example usage:
"""
from fastapi import FastAPI
from maestro_core_auth import (
    AuthManager,
    OIDCProviderRegistry,
    LDAPProviderRegistry,
    JITProvisioner,
    ProvisioningConfig,
    create_azure_ad_provider,
    create_active_directory_provider
)
from maestro_core_auth.routes import create_auth_router

app = FastAPI()

# Initialize components
auth_manager = AuthManager(jwt_secret="your-secret")
oidc_registry = OIDCProviderRegistry()
ldap_registry = LDAPProviderRegistry()

# Configure OIDC providers
azure_config = create_azure_ad_provider(
    client_id="...",
    client_secret="...",
    tenant_id="...",
    redirect_uri="https://app.example.com/auth/sso/azure_ad/callback"
)
await oidc_registry.register_provider(azure_config)

# Configure LDAP
ad_config = create_active_directory_provider(
    server_url="ldaps://dc.company.com:636",
    base_dn="DC=company,DC=com",
    bind_dn="CN=Service,OU=Accounts,DC=company,DC=com",
    bind_password="..."
)
ldap_registry.register_provider(ad_config)

# Configure provisioning
provisioner = JITProvisioner(ProvisioningConfig(
    auto_create_users=True,
    sync_groups=True,
    group_to_role_mapping={
        "Admins": ["admin"],
        "Users": ["user"]
    }
))

# Create and include router
auth_router = create_auth_router(
    auth_manager=auth_manager,
    oidc_registry=oidc_registry,
    ldap_registry=ldap_registry,
    provisioner=provisioner,
    get_db_session=get_db  # Your DB session dependency
)
app.include_router(auth_router)
"""
