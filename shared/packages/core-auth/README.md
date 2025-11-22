# MAESTRO Core Auth

Enterprise authentication and authorization for MAESTRO ecosystem.

## Features

- JWT/OAuth2 authentication
- Role-based access control (RBAC)
- Multi-factor authentication (MFA)
- Session management
- Token refresh
- Password hashing with bcrypt

## Installation

```bash
poetry add maestro-core-auth
```

## Usage

```python
from maestro_core_auth import AuthManager, JWTConfig

# Configure authentication
auth_config = JWTConfig(
    secret_key="your-secret-key",
    algorithm="HS256",
    access_token_expire_minutes=60
)

auth_manager = AuthManager(auth_config)

# Create tokens
token = auth_manager.create_access_token(user_id="123", roles=["admin"])

# Verify tokens
payload = auth_manager.verify_token(token)
```
