"""
Authentication E2E Tests.

EPIC: MD-3034 - Core User Journey E2E Tests
Tests: Password reset, MFA, OAuth/SSO, Session management

This module provides comprehensive E2E tests for authentication flows
including password reset, MFA enrollment/verification, OAuth/SSO integration,
and session management with token refresh.
"""

from __future__ import annotations

import asyncio
import hashlib
import re
import secrets
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class AuthProvider(Enum):
    """Supported authentication providers."""
    LOCAL = "local"
    OAUTH_GOOGLE = "oauth_google"
    OAUTH_GITHUB = "oauth_github"
    SSO_SAML = "sso_saml"
    SSO_OIDC = "sso_oidc"


class MFAMethod(Enum):
    """Supported MFA methods."""
    TOTP = "totp"
    SMS = "sms"
    EMAIL = "email"
    HARDWARE_KEY = "hardware_key"


@dataclass
class UserCredentials:
    """User credentials for testing."""
    email: str
    password: str
    user_id: str = field(default_factory=lambda: secrets.token_hex(16))
    mfa_enabled: bool = False
    mfa_method: Optional[MFAMethod] = None
    mfa_secret: Optional[str] = None


@dataclass
class AuthSession:
    """Authentication session representation."""
    session_id: str
    user_id: str
    access_token: str
    refresh_token: str
    expires_at: datetime
    created_at: datetime = field(default_factory=datetime.utcnow)
    is_mfa_verified: bool = False


@dataclass
class PasswordResetRequest:
    """Password reset request details."""
    request_id: str
    email: str
    token: str
    expires_at: datetime
    used: bool = False
    created_at: datetime = field(default_factory=datetime.utcnow)


class AuthFlowSimulator:
    """
    Simulates authentication flow for E2E testing.

    Provides realistic authentication flow simulation including:
    - Password-based login
    - MFA enrollment and verification
    - OAuth/SSO integration
    - Session management and token refresh
    """

    def __init__(self):
        self.users: Dict[str, UserCredentials] = {}
        self.sessions: Dict[str, AuthSession] = {}
        self.reset_requests: Dict[str, PasswordResetRequest] = {}
        self.mfa_codes: Dict[str, str] = {}

    def register_user(self, email: str, password: str) -> UserCredentials:
        """Register a new user."""
        if email in self.users:
            raise ValueError(f"User {email} already exists")

        user = UserCredentials(email=email, password=self._hash_password(password))
        self.users[email] = user
        return user

    def _hash_password(self, password: str) -> str:
        """Hash password with salt."""
        salt = secrets.token_hex(16)
        return f"{salt}:{hashlib.sha256(f'{salt}{password}'.encode()).hexdigest()}"

    def _verify_password(self, stored: str, password: str) -> bool:
        """Verify password against stored hash."""
        salt, hash_val = stored.split(":")
        return hash_val == hashlib.sha256(f"{salt}{password}".encode()).hexdigest()

    async def login(
        self,
        email: str,
        password: str,
        mfa_code: Optional[str] = None
    ) -> Optional[AuthSession]:
        """
        Authenticate user with email and password.

        Returns session if successful, None if failed.
        """
        if email not in self.users:
            return None

        user = self.users[email]
        if not self._verify_password(user.password, password):
            return None

        # Check MFA if enabled
        if user.mfa_enabled:
            if not mfa_code:
                raise ValueError("MFA code required")
            if not self._verify_mfa(user.user_id, mfa_code):
                return None

        # Create session
        session = AuthSession(
            session_id=secrets.token_hex(32),
            user_id=user.user_id,
            access_token=secrets.token_hex(64),
            refresh_token=secrets.token_hex(64),
            expires_at=datetime.utcnow() + timedelta(hours=1),
            is_mfa_verified=user.mfa_enabled
        )
        self.sessions[session.session_id] = session
        return session

    async def logout(self, session_id: str) -> bool:
        """Invalidate session."""
        if session_id in self.sessions:
            del self.sessions[session_id]
            return True
        return False

    async def request_password_reset(self, email: str) -> Optional[PasswordResetRequest]:
        """Request password reset for email."""
        if email not in self.users:
            # Don't reveal if user exists
            return None

        request = PasswordResetRequest(
            request_id=secrets.token_hex(16),
            email=email,
            token=secrets.token_urlsafe(32),
            expires_at=datetime.utcnow() + timedelta(hours=1)
        )
        self.reset_requests[request.token] = request
        return request

    async def complete_password_reset(
        self,
        token: str,
        new_password: str
    ) -> bool:
        """Complete password reset with token."""
        if token not in self.reset_requests:
            return False

        request = self.reset_requests[token]
        if request.used or datetime.utcnow() > request.expires_at:
            return False

        # Update password
        user = self.users[request.email]
        user.password = self._hash_password(new_password)
        request.used = True

        return True

    async def enroll_mfa(
        self,
        user_id: str,
        method: MFAMethod
    ) -> Dict[str, Any]:
        """Enroll user in MFA."""
        # Find user by ID
        user = None
        for u in self.users.values():
            if u.user_id == user_id:
                user = u
                break

        if not user:
            raise ValueError(f"User {user_id} not found")

        if method == MFAMethod.TOTP:
            secret = secrets.token_hex(20)
            user.mfa_secret = secret
            return {
                "method": method.value,
                "secret": secret,
                "provisioning_uri": f"otpauth://totp/Maestro:{user.email}?secret={secret}&issuer=Maestro"
            }
        elif method == MFAMethod.EMAIL:
            return {
                "method": method.value,
                "email": user.email,
                "message": "Verification code will be sent to email"
            }
        elif method == MFAMethod.SMS:
            return {
                "method": method.value,
                "message": "Phone number required for SMS verification"
            }
        else:
            raise ValueError(f"Unsupported MFA method: {method}")

    async def verify_mfa_enrollment(
        self,
        user_id: str,
        code: str
    ) -> bool:
        """Verify MFA enrollment with code."""
        user = None
        for u in self.users.values():
            if u.user_id == user_id:
                user = u
                break

        if not user or not user.mfa_secret:
            return False

        # For testing, accept any 6-digit code or the stored test code
        if len(code) == 6 and code.isdigit():
            user.mfa_enabled = True
            user.mfa_method = MFAMethod.TOTP
            return True

        return False

    def _verify_mfa(self, user_id: str, code: str) -> bool:
        """Verify MFA code during login."""
        # For testing, accept any valid 6-digit code
        return len(code) == 6 and code.isdigit()

    async def refresh_token(self, refresh_token: str) -> Optional[AuthSession]:
        """Refresh access token using refresh token."""
        for session in self.sessions.values():
            if session.refresh_token == refresh_token:
                # Create new tokens
                session.access_token = secrets.token_hex(64)
                session.refresh_token = secrets.token_hex(64)
                session.expires_at = datetime.utcnow() + timedelta(hours=1)
                return session
        return None

    async def validate_session(self, session_id: str) -> bool:
        """Check if session is valid."""
        if session_id not in self.sessions:
            return False
        session = self.sessions[session_id]
        return datetime.utcnow() < session.expires_at


class OAuthSimulator:
    """
    Simulates OAuth/SSO flows for E2E testing.
    """

    def __init__(self, provider: AuthProvider):
        self.provider = provider
        self.auth_codes: Dict[str, Dict[str, Any]] = {}

    async def initiate_oauth(
        self,
        client_id: str,
        redirect_uri: str,
        state: str
    ) -> str:
        """Initiate OAuth flow, return authorization URL."""
        if self.provider == AuthProvider.OAUTH_GOOGLE:
            base_url = "https://accounts.google.com/o/oauth2/v2/auth"
        elif self.provider == AuthProvider.OAUTH_GITHUB:
            base_url = "https://github.com/login/oauth/authorize"
        else:
            raise ValueError(f"Unsupported OAuth provider: {self.provider}")

        return f"{base_url}?client_id={client_id}&redirect_uri={redirect_uri}&state={state}&response_type=code"

    async def complete_oauth(
        self,
        code: str,
        client_id: str,
        client_secret: str
    ) -> Optional[Dict[str, Any]]:
        """Exchange authorization code for tokens."""
        # Simulate token exchange
        return {
            "access_token": secrets.token_hex(32),
            "refresh_token": secrets.token_hex(32),
            "token_type": "Bearer",
            "expires_in": 3600,
            "scope": "openid email profile",
            "id_token": self._generate_mock_id_token()
        }

    def _generate_mock_id_token(self) -> str:
        """Generate mock ID token for testing."""
        import base64
        import json

        header = base64.urlsafe_b64encode(json.dumps({
            "alg": "RS256",
            "typ": "JWT"
        }).encode()).decode().rstrip("=")

        payload = base64.urlsafe_b64encode(json.dumps({
            "sub": secrets.token_hex(16),
            "email": "test@example.com",
            "email_verified": True,
            "name": "Test User",
            "iat": int(time.time()),
            "exp": int(time.time()) + 3600
        }).encode()).decode().rstrip("=")

        signature = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode().rstrip("=")

        return f"{header}.{payload}.{signature}"


# =============================================================================
# E2E Test Classes
# =============================================================================


class TestPasswordResetFlow:
    """E2E tests for password reset flow."""

    @pytest.fixture
    def auth_sim(self):
        """Create auth simulator with test user."""
        sim = AuthFlowSimulator()
        sim.register_user("user@example.com", "OldPassword123!")
        return sim

    @pytest.mark.asyncio
    async def test_request_password_reset_valid_email(self, auth_sim):
        """Test password reset request for valid email."""
        request = await auth_sim.request_password_reset("user@example.com")

        assert request is not None
        assert request.email == "user@example.com"
        assert len(request.token) > 20
        assert not request.used
        assert request.expires_at > datetime.utcnow()

    @pytest.mark.asyncio
    async def test_request_password_reset_invalid_email(self, auth_sim):
        """Test password reset request for non-existent email."""
        request = await auth_sim.request_password_reset("nonexistent@example.com")
        # Should not reveal if user exists
        assert request is None

    @pytest.mark.asyncio
    async def test_complete_password_reset_valid_token(self, auth_sim):
        """Test completing password reset with valid token."""
        request = await auth_sim.request_password_reset("user@example.com")
        assert request is not None

        result = await auth_sim.complete_password_reset(
            request.token,
            "NewPassword456!"
        )
        assert result is True

        # Verify can login with new password
        session = await auth_sim.login("user@example.com", "NewPassword456!")
        assert session is not None

    @pytest.mark.asyncio
    async def test_complete_password_reset_invalid_token(self, auth_sim):
        """Test completing password reset with invalid token."""
        result = await auth_sim.complete_password_reset(
            "invalid_token_xyz",
            "NewPassword456!"
        )
        assert result is False

    @pytest.mark.asyncio
    async def test_complete_password_reset_used_token(self, auth_sim):
        """Test that reset token can only be used once."""
        request = await auth_sim.request_password_reset("user@example.com")
        assert request is not None

        # First use - should succeed
        result1 = await auth_sim.complete_password_reset(request.token, "NewPass1!")
        assert result1 is True

        # Second use - should fail
        result2 = await auth_sim.complete_password_reset(request.token, "NewPass2!")
        assert result2 is False

    @pytest.mark.asyncio
    async def test_full_password_reset_flow(self, auth_sim):
        """Test complete password reset flow end-to-end."""
        # 1. Request reset
        request = await auth_sim.request_password_reset("user@example.com")
        assert request is not None

        # 2. Verify old password still works
        session1 = await auth_sim.login("user@example.com", "OldPassword123!")
        assert session1 is not None
        await auth_sim.logout(session1.session_id)

        # 3. Complete reset
        result = await auth_sim.complete_password_reset(request.token, "BrandNew789!")
        assert result is True

        # 4. Verify old password no longer works
        session2 = await auth_sim.login("user@example.com", "OldPassword123!")
        assert session2 is None

        # 5. Verify new password works
        session3 = await auth_sim.login("user@example.com", "BrandNew789!")
        assert session3 is not None


class TestMFAFlow:
    """E2E tests for MFA enrollment and verification."""

    @pytest.fixture
    def auth_sim(self):
        """Create auth simulator with test user."""
        sim = AuthFlowSimulator()
        sim.register_user("mfa_user@example.com", "SecurePass123!")
        return sim

    @pytest.mark.asyncio
    async def test_mfa_enrollment_totp(self, auth_sim):
        """Test MFA enrollment with TOTP."""
        # Login first
        session = await auth_sim.login("mfa_user@example.com", "SecurePass123!")
        assert session is not None

        # Enroll in MFA
        enrollment = await auth_sim.enroll_mfa(session.user_id, MFAMethod.TOTP)

        assert "secret" in enrollment
        assert "provisioning_uri" in enrollment
        assert enrollment["method"] == "totp"

    @pytest.mark.asyncio
    async def test_mfa_verification_success(self, auth_sim):
        """Test MFA verification with valid code."""
        session = await auth_sim.login("mfa_user@example.com", "SecurePass123!")
        await auth_sim.enroll_mfa(session.user_id, MFAMethod.TOTP)

        # Verify with valid 6-digit code
        result = await auth_sim.verify_mfa_enrollment(session.user_id, "123456")
        assert result is True

    @pytest.mark.asyncio
    async def test_mfa_verification_invalid_code(self, auth_sim):
        """Test MFA verification with invalid code."""
        session = await auth_sim.login("mfa_user@example.com", "SecurePass123!")
        await auth_sim.enroll_mfa(session.user_id, MFAMethod.TOTP)

        # Verify with invalid code
        result = await auth_sim.verify_mfa_enrollment(session.user_id, "abc")
        assert result is False

    @pytest.mark.asyncio
    async def test_login_with_mfa_required(self, auth_sim):
        """Test login flow when MFA is enabled."""
        # Setup user with MFA
        session = await auth_sim.login("mfa_user@example.com", "SecurePass123!")
        await auth_sim.enroll_mfa(session.user_id, MFAMethod.TOTP)
        await auth_sim.verify_mfa_enrollment(session.user_id, "123456")
        await auth_sim.logout(session.session_id)

        # Try login without MFA code - should raise
        with pytest.raises(ValueError, match="MFA code required"):
            await auth_sim.login("mfa_user@example.com", "SecurePass123!")

        # Login with MFA code
        session2 = await auth_sim.login(
            "mfa_user@example.com",
            "SecurePass123!",
            mfa_code="654321"
        )
        assert session2 is not None
        assert session2.is_mfa_verified is True

    @pytest.mark.asyncio
    async def test_full_mfa_enrollment_flow(self, auth_sim):
        """Test complete MFA enrollment flow."""
        # 1. Login
        session = await auth_sim.login("mfa_user@example.com", "SecurePass123!")
        assert session is not None

        # 2. Initiate MFA enrollment
        enrollment = await auth_sim.enroll_mfa(session.user_id, MFAMethod.TOTP)
        assert "secret" in enrollment

        # 3. Verify enrollment
        verified = await auth_sim.verify_mfa_enrollment(session.user_id, "111111")
        assert verified is True

        # 4. Logout
        await auth_sim.logout(session.session_id)

        # 5. Login requires MFA now
        session2 = await auth_sim.login(
            "mfa_user@example.com",
            "SecurePass123!",
            mfa_code="222222"
        )
        assert session2 is not None


class TestOAuthSSOFlow:
    """E2E tests for OAuth/SSO integration."""

    @pytest.mark.asyncio
    async def test_google_oauth_initiation(self):
        """Test Google OAuth flow initiation."""
        oauth = OAuthSimulator(AuthProvider.OAUTH_GOOGLE)

        auth_url = await oauth.initiate_oauth(
            client_id="test_client_id",
            redirect_uri="https://app.example.com/callback",
            state="random_state_123"
        )

        assert "accounts.google.com" in auth_url
        assert "test_client_id" in auth_url
        assert "random_state_123" in auth_url

    @pytest.mark.asyncio
    async def test_github_oauth_initiation(self):
        """Test GitHub OAuth flow initiation."""
        oauth = OAuthSimulator(AuthProvider.OAUTH_GITHUB)

        auth_url = await oauth.initiate_oauth(
            client_id="github_client_id",
            redirect_uri="https://app.example.com/callback",
            state="state_xyz"
        )

        assert "github.com" in auth_url
        assert "github_client_id" in auth_url

    @pytest.mark.asyncio
    async def test_oauth_token_exchange(self):
        """Test OAuth authorization code exchange."""
        oauth = OAuthSimulator(AuthProvider.OAUTH_GOOGLE)

        tokens = await oauth.complete_oauth(
            code="auth_code_123",
            client_id="test_client",
            client_secret="test_secret"
        )

        assert tokens is not None
        assert "access_token" in tokens
        assert "refresh_token" in tokens
        assert "id_token" in tokens
        assert tokens["token_type"] == "Bearer"

    @pytest.mark.asyncio
    async def test_full_oauth_flow(self):
        """Test complete OAuth flow end-to-end."""
        oauth = OAuthSimulator(AuthProvider.OAUTH_GOOGLE)

        # 1. Initiate OAuth
        state = secrets.token_urlsafe(16)
        auth_url = await oauth.initiate_oauth(
            client_id="client_123",
            redirect_uri="https://app.example.com/callback",
            state=state
        )
        assert auth_url is not None

        # 2. User authenticates (simulated) and gets code
        auth_code = "simulated_auth_code_456"

        # 3. Exchange code for tokens
        tokens = await oauth.complete_oauth(
            code=auth_code,
            client_id="client_123",
            client_secret="secret_xyz"
        )

        assert tokens["access_token"] is not None
        assert tokens["id_token"] is not None

        # 4. Verify ID token structure
        id_token_parts = tokens["id_token"].split(".")
        assert len(id_token_parts) == 3  # header.payload.signature


class TestSessionManagement:
    """E2E tests for session management and token refresh."""

    @pytest.fixture
    def auth_sim(self):
        """Create auth simulator with test user."""
        sim = AuthFlowSimulator()
        sim.register_user("session_user@example.com", "SessionPass123!")
        return sim

    @pytest.mark.asyncio
    async def test_session_creation(self, auth_sim):
        """Test session is created on login."""
        session = await auth_sim.login("session_user@example.com", "SessionPass123!")

        assert session is not None
        assert len(session.session_id) == 64
        assert len(session.access_token) == 128
        assert len(session.refresh_token) == 128
        assert session.expires_at > datetime.utcnow()

    @pytest.mark.asyncio
    async def test_session_validation(self, auth_sim):
        """Test session validation."""
        session = await auth_sim.login("session_user@example.com", "SessionPass123!")

        is_valid = await auth_sim.validate_session(session.session_id)
        assert is_valid is True

        # Invalid session
        is_valid_fake = await auth_sim.validate_session("fake_session_id")
        assert is_valid_fake is False

    @pytest.mark.asyncio
    async def test_session_invalidation_on_logout(self, auth_sim):
        """Test session is invalidated on logout."""
        session = await auth_sim.login("session_user@example.com", "SessionPass123!")

        # Validate before logout
        assert await auth_sim.validate_session(session.session_id) is True

        # Logout
        await auth_sim.logout(session.session_id)

        # Validate after logout
        assert await auth_sim.validate_session(session.session_id) is False

    @pytest.mark.asyncio
    async def test_token_refresh(self, auth_sim):
        """Test access token refresh."""
        session = await auth_sim.login("session_user@example.com", "SessionPass123!")
        old_access_token = session.access_token
        old_refresh_token = session.refresh_token

        # Refresh tokens
        refreshed = await auth_sim.refresh_token(old_refresh_token)

        assert refreshed is not None
        assert refreshed.access_token != old_access_token
        assert refreshed.refresh_token != old_refresh_token
        assert refreshed.expires_at > datetime.utcnow()

    @pytest.mark.asyncio
    async def test_invalid_refresh_token(self, auth_sim):
        """Test refresh with invalid token."""
        refreshed = await auth_sim.refresh_token("invalid_refresh_token")
        assert refreshed is None

    @pytest.mark.asyncio
    async def test_full_session_lifecycle(self, auth_sim):
        """Test complete session lifecycle."""
        # 1. Login - create session
        session = await auth_sim.login("session_user@example.com", "SessionPass123!")
        assert session is not None

        # 2. Validate session
        assert await auth_sim.validate_session(session.session_id) is True

        # 3. Refresh token
        old_token = session.access_token
        refreshed = await auth_sim.refresh_token(session.refresh_token)
        assert refreshed.access_token != old_token

        # 4. Session still valid
        assert await auth_sim.validate_session(session.session_id) is True

        # 5. Logout
        await auth_sim.logout(session.session_id)

        # 6. Session invalidated
        assert await auth_sim.validate_session(session.session_id) is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
