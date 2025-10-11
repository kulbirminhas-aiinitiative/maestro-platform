"""
Password Hashing for Maestro ML Platform

Uses bcrypt for secure password hashing.
Part of Gap 1.1 (JWT Authentication Implementation).
"""

import logging
from passlib.context import CryptContext

logger = logging.getLogger(__name__)

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class PasswordHasher:
    """
    Secure password hashing using bcrypt

    Usage:
        hasher = PasswordHasher()

        # Hash password
        hashed = hasher.hash_password("my_secure_password123")

        # Verify password
        is_valid = hasher.verify_password("my_secure_password123", hashed)
    """

    def __init__(self, context: CryptContext = pwd_context):
        """
        Initialize password hasher

        Args:
            context: Passlib context (default: bcrypt)
        """
        self.context = context

    def hash_password(self, password: str) -> str:
        """
        Hash a password using bcrypt

        Args:
            password: Plain text password

        Returns:
            Hashed password string

        Example:
            hashed = hasher.hash_password("user_password123")
            # Store 'hashed' in database (NOT the plain password)
        """
        hashed = self.context.hash(password)
        logger.debug("Password hashed successfully")
        return hashed

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """
        Verify a password against its hash

        Args:
            plain_password: Plain text password (from login form)
            hashed_password: Hashed password (from database)

        Returns:
            True if password matches, False otherwise

        Example:
            # During login
            user = get_user_from_db(email)
            if not hasher.verify_password(login_password, user.hashed_password):
                raise HTTPException(status_code=401, detail="Invalid password")
        """
        try:
            is_valid = self.context.verify(plain_password, hashed_password)

            if is_valid:
                logger.debug("Password verification successful")
            else:
                logger.debug("Password verification failed")

            return is_valid

        except Exception as e:
            logger.error(f"Password verification error: {e}")
            return False

    def needs_rehash(self, hashed_password: str) -> bool:
        """
        Check if password hash needs to be updated

        This happens when:
        - bcrypt rounds have been increased
        - Algorithm has been upgraded

        Args:
            hashed_password: Current hashed password

        Returns:
            True if password should be rehashed

        Example:
            if hasher.needs_rehash(user.hashed_password):
                # User just logged in successfully, rehash their password
                new_hash = hasher.hash_password(plain_password)
                update_user_password_hash(user.id, new_hash)
        """
        return self.context.needs_update(hashed_password)


# Singleton instance
_password_hasher: PasswordHasher | None = None


def get_password_hasher() -> PasswordHasher:
    """
    Get singleton password hasher instance

    Usage in FastAPI:
        from fastapi import Depends
        from enterprise.auth import get_password_hasher, PasswordHasher

        async def login(
            hasher: PasswordHasher = Depends(get_password_hasher)
        ):
            if not hasher.verify_password(form.password, user.hashed_password):
                raise HTTPException(status_code=401)
    """
    global _password_hasher
    if _password_hasher is None:
        _password_hasher = PasswordHasher()
    return _password_hasher
