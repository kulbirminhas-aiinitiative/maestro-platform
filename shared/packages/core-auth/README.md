# MAESTRO Core Authentication Library

Enterprise-grade authentication and authorization for the MAESTRO platform.

## Features

- **JWT Authentication** - Secure token-based authentication
- **OIDC/OAuth2** - Azure AD, Google, Okta integration
- **LDAP/Active Directory** - Enterprise directory integration
- **SCIM 2.0** - Automated user provisioning
- **JIT Provisioning** - Just-in-time user creation
- **RBAC** - Role-based access control
- **MFA** - Multi-factor authentication support

## Installation

```bash
pip install maestro-core-auth
```

## Quick Start

### Basic JWT Authentication

```python
from maestro_core_auth import AuthManager

auth = AuthManager(
    jwt_secret="your-secret-key",
    token_expire_minutes=30
)

# Authenticate user
user = await auth.authenticate_user(username, password, db_session)
tokens = await auth.create_tokens(user)
```

### OIDC SSO (Azure AD Example)

```python
from maestro_core_auth import (
    OIDCProviderRegistry,
    create_azure_ad_provider
)

# Configure provider
config = create_azure_ad_provider(
    client_id="your-client-id",
    client_secret="your-client-secret",
    tenant_id="your-tenant-id",
    redirect_uri="https://app.example.com/auth/callback"
)

# Register and initialize
registry = OIDCProviderRegistry()
await registry.register_provider(config)

# Get authorization URL
provider = registry.get_provider("azure_ad")
auth_url = await provider.get_authorization_url(state="random-state")

# Exchange code for tokens
tokens = await provider.exchange_code(code="auth-code")
user_info = await provider.get_user_info(tokens["access_token"])
```

### LDAP/Active Directory

```python
from maestro_core_auth import (
    LDAPProviderRegistry,
    create_active_directory_provider
)

config = create_active_directory_provider(
    server_url="ldaps://dc.company.com:636",
    base_dn="DC=company,DC=com",
    bind_dn="CN=Service,OU=Accounts,DC=company,DC=com",
    bind_password="password"
)

registry = LDAPProviderRegistry()
provider = registry.register_provider(config)

# Authenticate
user = await provider.authenticate("john.doe", "password")
groups = await provider.get_user_groups(user.dn)
```

### SCIM 2.0 Provisioning

```python
from fastapi import FastAPI
from maestro_core_auth import SCIMService

app = FastAPI()
scim = SCIMService(base_url="/scim/v2")
app.include_router(scim.router)
```

### JIT Provisioning

```python
from maestro_core_auth import JITProvisioner, ProvisioningConfig

config = ProvisioningConfig(
    auto_create_users=True,
    sync_groups=True,
    group_to_role_mapping={
        "Admins": ["admin"],
        "Users": ["user"]
    }
)

provisioner = JITProvisioner(config)
result = await provisioner.provision_oidc_user(user_info, "azure_ad", session)
```

## Supported Providers

### OIDC
- Azure AD / Entra ID
- Google Cloud Identity
- Okta
- Auth0

### Directory Services
- Active Directory
- OpenLDAP

## License

MIT
