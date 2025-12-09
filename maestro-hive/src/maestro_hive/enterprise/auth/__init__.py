"""
Authentication module for enterprise features.

Provides:
- OAuth2 authentication flow
- JWT token management with refresh
- Multi-factor authentication (TOTP)
- API key management with rotation
- Secure password hashing (bcrypt)
"""

from .oauth2 import OAuth2Provider, OAuth2Config, TokenPair
from .token_manager import TokenManager, TokenConfig
from .mfa import MFAProvider, MFAConfig
from .api_keys import APIKeyManager, APIKey
from .password import PasswordHasher

__all__ = [
    "OAuth2Provider",
    "OAuth2Config",
    "TokenPair",
    "TokenManager",
    "TokenConfig",
    "MFAProvider",
    "MFAConfig",
    "APIKeyManager",
    "APIKey",
    "PasswordHasher",
]
