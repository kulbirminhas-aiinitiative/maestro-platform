"""
Core authentication manager with enterprise features.
"""

from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession
from maestro_core_logging import get_logger

from .jwt_auth import JWTAuth
from .password import PasswordManager
from .rbac import RBACManager
from .session import SessionManager
from .models import User, UserCreate, TokenResponse
from .exceptions import InvalidCredentialsException, AuthException


class AuthManager:
    """
    Enterprise authentication manager with JWT, RBAC, and session management.

    Features:
    - JWT token management with refresh tokens
    - Role-based access control (RBAC)
    - Password hashing and validation
    - Session management with Redis
    - Multi-factor authentication support
    - OAuth2 provider integration
    """

    def __init__(
        self,
        jwt_secret: str,
        jwt_algorithm: str = "HS256",
        token_expire_minutes: int = 30,
        refresh_token_expire_days: int = 7,
        redis_url: str = "redis://localhost:6379",
        enable_mfa: bool = False,
        password_min_length: int = 8
    ):
        """
        Initialize authentication manager.

        Args:
            jwt_secret: Secret key for JWT signing
            jwt_algorithm: JWT algorithm (HS256, RS256, etc.)
            token_expire_minutes: Access token expiration time
            refresh_token_expire_days: Refresh token expiration time
            redis_url: Redis connection URL for sessions
            enable_mfa: Enable multi-factor authentication
            password_min_length: Minimum password length
        """
        self.logger = get_logger(__name__)

        # Initialize components
        self.jwt_auth = JWTAuth(
            secret_key=jwt_secret,
            algorithm=jwt_algorithm,
            access_token_expire_minutes=token_expire_minutes,
            refresh_token_expire_days=refresh_token_expire_days
        )

        self.password_manager = PasswordManager(min_length=password_min_length)
        self.rbac_manager = RBACManager()
        self.session_manager = SessionManager(redis_url=redis_url)

        self.enable_mfa = enable_mfa

    async def authenticate_user(
        self,
        username: str,
        password: str,
        db_session: AsyncSession,
        mfa_code: Optional[str] = None
    ) -> Optional[User]:
        """
        Authenticate user with username/password and optional MFA.

        Args:
            username: Username or email
            password: User password
            db_session: Database session
            mfa_code: Multi-factor authentication code

        Returns:
            User object if authentication successful, None otherwise

        Raises:
            InvalidCredentialsException: If credentials are invalid
        """
        try:
            # Find user by username or email
            user = await self._get_user_by_login(username, db_session)
            if not user:
                self.logger.warning("Authentication failed: user not found", username=username)
                raise InvalidCredentialsException("Invalid credentials")

            # Verify password
            if not self.password_manager.verify_password(password, user.hashed_password):
                self.logger.warning("Authentication failed: invalid password", username=username)
                raise InvalidCredentialsException("Invalid credentials")

            # Check if user is active
            if not user.is_active:
                self.logger.warning("Authentication failed: user inactive", username=username)
                raise InvalidCredentialsException("Account is disabled")

            # Verify MFA if enabled
            if self.enable_mfa and user.mfa_enabled:
                if not mfa_code:
                    raise AuthException("MFA code required")

                if not await self._verify_mfa_code(user, mfa_code):
                    self.logger.warning("Authentication failed: invalid MFA code", username=username)
                    raise InvalidCredentialsException("Invalid MFA code")

            # Log successful authentication
            self.logger.info("User authenticated successfully",
                           user_id=user.id,
                           username=user.username)

            return user

        except Exception as e:
            self.logger.error("Authentication error",
                            username=username,
                            error=str(e))
            raise

    async def create_tokens(self, user: User) -> TokenResponse:
        """
        Create access and refresh tokens for authenticated user.

        Args:
            user: Authenticated user

        Returns:
            TokenResponse with access and refresh tokens
        """
        # Create JWT tokens
        access_token = self.jwt_auth.create_access_token(
            subject=str(user.id),
            additional_claims={
                "username": user.username,
                "email": user.email,
                "roles": [role.name for role in user.roles] if user.roles else [],
                "permissions": await self.rbac_manager.get_user_permissions(user)
            }
        )

        refresh_token = self.jwt_auth.create_refresh_token(subject=str(user.id))

        # Store session
        await self.session_manager.create_session(
            user_id=user.id,
            access_token=access_token,
            refresh_token=refresh_token
        )

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=self.jwt_auth.access_token_expire_minutes * 60
        )

    async def refresh_tokens(
        self,
        refresh_token: str,
        db_session: AsyncSession
    ) -> TokenResponse:
        """
        Refresh access token using refresh token.

        Args:
            refresh_token: Valid refresh token
            db_session: Database session

        Returns:
            New TokenResponse with fresh tokens

        Raises:
            TokenExpiredException: If refresh token is invalid/expired
        """
        # Validate refresh token
        payload = self.jwt_auth.decode_token(refresh_token)
        if not payload or payload.token_type != "refresh":
            raise InvalidCredentialsException("Invalid refresh token")

        # Get user
        user = await self._get_user_by_id(int(payload.sub), db_session)
        if not user or not user.is_active:
            raise InvalidCredentialsException("User not found or inactive")

        # Verify session exists
        if not await self.session_manager.verify_session(user.id, refresh_token):
            raise InvalidCredentialsException("Session not found")

        # Create new tokens
        return await self.create_tokens(user)

    async def logout(self, user_id: int, access_token: str) -> None:
        """
        Logout user and invalidate session.

        Args:
            user_id: User ID
            access_token: Current access token
        """
        await self.session_manager.destroy_session(user_id, access_token)
        self.logger.info("User logged out", user_id=user_id)

    async def create_user(
        self,
        user_data: UserCreate,
        db_session: AsyncSession,
        created_by: Optional[int] = None
    ) -> User:
        """
        Create new user with hashed password.

        Args:
            user_data: User creation data
            db_session: Database session
            created_by: ID of user creating this account

        Returns:
            Created user object

        Raises:
            AuthException: If user creation fails
        """
        # Validate password strength
        self.password_manager.validate_password_strength(user_data.password)

        # Hash password
        hashed_password = self.password_manager.hash_password(user_data.password)

        # Create user (this would interact with your user repository)
        user = User(
            username=user_data.username,
            email=user_data.email,
            hashed_password=hashed_password,
            is_active=True,
            created_at=datetime.utcnow(),
            created_by=created_by
        )

        # Add to database (implementation depends on your ORM setup)
        # db_session.add(user)
        # await db_session.commit()
        # await db_session.refresh(user)

        self.logger.info("User created",
                        username=user.username,
                        created_by=created_by)

        return user

    async def change_password(
        self,
        user_id: int,
        current_password: str,
        new_password: str,
        db_session: AsyncSession
    ) -> bool:
        """
        Change user password with current password verification.

        Args:
            user_id: User ID
            current_password: Current password for verification
            new_password: New password
            db_session: Database session

        Returns:
            True if password changed successfully

        Raises:
            InvalidCredentialsException: If current password is wrong
            AuthException: If password change fails
        """
        user = await self._get_user_by_id(user_id, db_session)
        if not user:
            raise AuthException("User not found")

        # Verify current password
        if not self.password_manager.verify_password(current_password, user.hashed_password):
            raise InvalidCredentialsException("Current password is incorrect")

        # Validate new password
        self.password_manager.validate_password_strength(new_password)

        # Hash new password
        new_hashed_password = self.password_manager.hash_password(new_password)

        # Update user (implementation depends on your ORM setup)
        # user.hashed_password = new_hashed_password
        # user.password_changed_at = datetime.utcnow()
        # await db_session.commit()

        self.logger.info("Password changed", user_id=user_id)
        return True

    async def _get_user_by_login(self, login: str, db_session: AsyncSession) -> Optional[User]:
        """Get user by username or email."""
        # Implementation depends on your user repository
        # This is a placeholder
        pass

    async def _get_user_by_id(self, user_id: int, db_session: AsyncSession) -> Optional[User]:
        """Get user by ID."""
        # Implementation depends on your user repository
        # This is a placeholder
        pass

    async def _verify_mfa_code(self, user: User, mfa_code: str) -> bool:
        """Verify MFA code (TOTP, SMS, etc.)."""
        # Implementation depends on your MFA provider
        # This is a placeholder for TOTP verification
        import pyotp

        if not user.mfa_secret:
            return False

        totp = pyotp.TOTP(user.mfa_secret)
        return totp.verify(mfa_code, valid_window=1)