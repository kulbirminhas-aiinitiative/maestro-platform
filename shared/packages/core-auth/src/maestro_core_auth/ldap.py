"""
LDAP/Active Directory authentication provider.

Supports:
- Simple bind authentication
- LDAP search for user attributes
- Group membership resolution
- Active Directory specific features
"""

from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from enum import Enum
import ldap
from ldap.ldapobject import LDAPObject
from pydantic import BaseModel
from maestro_core_logging import get_logger

logger = get_logger(__name__)


class LDAPAuthType(str, Enum):
    """LDAP authentication types."""
    SIMPLE = "simple"
    NTLM = "ntlm"
    GSSAPI = "gssapi"


class LDAPUserInfo(BaseModel):
    """User information from LDAP."""
    dn: str
    username: str
    email: Optional[str] = None
    display_name: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    employee_id: Optional[str] = None
    department: Optional[str] = None
    title: Optional[str] = None
    manager_dn: Optional[str] = None
    groups: List[str] = field(default_factory=list)
    is_active: bool = True
    attributes: Dict[str, Any] = field(default_factory=dict)


@dataclass
class LDAPConfig:
    """Configuration for LDAP connection."""
    name: str
    server_url: str  # ldap://server:389 or ldaps://server:636
    base_dn: str
    bind_dn: str
    bind_password: str
    user_search_base: Optional[str] = None
    user_search_filter: str = "(sAMAccountName={username})"  # AD default
    group_search_base: Optional[str] = None
    group_search_filter: str = "(member={user_dn})"
    # Attribute mapping
    username_attr: str = "sAMAccountName"
    email_attr: str = "mail"
    display_name_attr: str = "displayName"
    first_name_attr: str = "givenName"
    last_name_attr: str = "sn"
    member_of_attr: str = "memberOf"
    # Connection settings
    use_ssl: bool = False
    start_tls: bool = False
    timeout: int = 30
    # Active Directory specific
    is_active_directory: bool = True
    ad_disabled_flag: int = 2  # userAccountControl flag for disabled accounts


class LDAPProvider:
    """
    LDAP authentication provider.

    Usage:
        config = LDAPConfig(
            name="active_directory",
            server_url="ldaps://dc.company.com:636",
            base_dn="DC=company,DC=com",
            bind_dn="CN=Service Account,OU=Service Accounts,DC=company,DC=com",
            bind_password="password"
        )
        provider = LDAPProvider(config)

        # Authenticate user
        user = await provider.authenticate("john.doe", "password123")

        # Search for user
        user = await provider.find_user("john.doe")

        # Get user groups
        groups = await provider.get_user_groups(user.dn)
    """

    def __init__(self, config: LDAPConfig):
        self.config = config
        self._conn: Optional[LDAPObject] = None

    def _get_connection(self) -> LDAPObject:
        """Get or create LDAP connection."""
        if self._conn:
            return self._conn

        # Initialize connection
        self._conn = ldap.initialize(self.config.server_url)
        self._conn.set_option(ldap.OPT_REFERRALS, 0)
        self._conn.set_option(ldap.OPT_NETWORK_TIMEOUT, self.config.timeout)
        self._conn.set_option(ldap.OPT_PROTOCOL_VERSION, ldap.VERSION3)

        # Start TLS if configured
        if self.config.start_tls:
            self._conn.start_tls_s()

        # Bind with service account
        self._conn.simple_bind_s(self.config.bind_dn, self.config.bind_password)

        logger.info("LDAP connection established", server=self.config.server_url)
        return self._conn

    def _close_connection(self) -> None:
        """Close LDAP connection."""
        if self._conn:
            try:
                self._conn.unbind_s()
            except Exception:
                pass
            self._conn = None

    async def authenticate(
        self,
        username: str,
        password: str
    ) -> Optional[LDAPUserInfo]:
        """
        Authenticate user with username and password.

        Args:
            username: Username (sAMAccountName, userPrincipalName, etc.)
            password: User password

        Returns:
            User info if authentication successful, None otherwise
        """
        try:
            # First, find the user DN
            user_info = await self.find_user(username)
            if not user_info:
                logger.warning("LDAP auth failed: user not found", username=username)
                return None

            # Attempt to bind as the user
            test_conn = ldap.initialize(self.config.server_url)
            test_conn.set_option(ldap.OPT_REFERRALS, 0)
            test_conn.set_option(ldap.OPT_PROTOCOL_VERSION, ldap.VERSION3)

            if self.config.start_tls:
                test_conn.start_tls_s()

            test_conn.simple_bind_s(user_info.dn, password)
            test_conn.unbind_s()

            logger.info("LDAP authentication successful", username=username, dn=user_info.dn)
            return user_info

        except ldap.INVALID_CREDENTIALS:
            logger.warning("LDAP auth failed: invalid credentials", username=username)
            return None
        except ldap.LDAPError as e:
            logger.error("LDAP auth error", username=username, error=str(e))
            return None

    async def find_user(self, username: str) -> Optional[LDAPUserInfo]:
        """
        Find user by username.

        Args:
            username: Username to search for

        Returns:
            User info if found, None otherwise
        """
        try:
            conn = self._get_connection()

            # Build search filter
            search_filter = self.config.user_search_filter.format(username=username)
            search_base = self.config.user_search_base or self.config.base_dn

            # Search for user
            result = conn.search_s(
                search_base,
                ldap.SCOPE_SUBTREE,
                search_filter,
                [
                    self.config.username_attr,
                    self.config.email_attr,
                    self.config.display_name_attr,
                    self.config.first_name_attr,
                    self.config.last_name_attr,
                    self.config.member_of_attr,
                    "userAccountControl",
                    "employeeID",
                    "department",
                    "title",
                    "manager"
                ]
            )

            if not result:
                return None

            dn, attrs = result[0]
            if not dn:
                return None

            # Parse attributes
            def get_attr(key: str) -> Optional[str]:
                val = attrs.get(key, [])
                if val:
                    return val[0].decode("utf-8") if isinstance(val[0], bytes) else val[0]
                return None

            def get_attrs(key: str) -> List[str]:
                vals = attrs.get(key, [])
                return [v.decode("utf-8") if isinstance(v, bytes) else v for v in vals]

            # Check if account is disabled (AD specific)
            is_active = True
            if self.config.is_active_directory:
                uac = get_attr("userAccountControl")
                if uac:
                    is_active = not (int(uac) & self.config.ad_disabled_flag)

            # Get group memberships
            groups = get_attrs(self.config.member_of_attr)
            # Extract CN from group DNs
            group_names = []
            for group_dn in groups:
                if group_dn.startswith("CN="):
                    group_name = group_dn.split(",")[0].replace("CN=", "")
                    group_names.append(group_name)

            return LDAPUserInfo(
                dn=dn,
                username=get_attr(self.config.username_attr) or username,
                email=get_attr(self.config.email_attr),
                display_name=get_attr(self.config.display_name_attr),
                first_name=get_attr(self.config.first_name_attr),
                last_name=get_attr(self.config.last_name_attr),
                employee_id=get_attr("employeeID"),
                department=get_attr("department"),
                title=get_attr("title"),
                manager_dn=get_attr("manager"),
                groups=group_names,
                is_active=is_active,
                attributes=attrs
            )

        except ldap.LDAPError as e:
            logger.error("LDAP search error", username=username, error=str(e))
            return None

    async def get_user_groups(
        self,
        user_dn: str,
        recursive: bool = True
    ) -> List[str]:
        """
        Get all groups a user belongs to.

        Args:
            user_dn: User distinguished name
            recursive: Include nested group memberships

        Returns:
            List of group names
        """
        try:
            conn = self._get_connection()
            search_base = self.config.group_search_base or self.config.base_dn

            if self.config.is_active_directory and recursive:
                # Use AD's nested group membership filter
                search_filter = f"(member:1.2.840.113556.1.4.1941:={user_dn})"
            else:
                search_filter = self.config.group_search_filter.format(user_dn=user_dn)

            result = conn.search_s(
                search_base,
                ldap.SCOPE_SUBTREE,
                search_filter,
                ["cn"]
            )

            groups = []
            for dn, attrs in result:
                if dn and "cn" in attrs:
                    cn = attrs["cn"][0]
                    if isinstance(cn, bytes):
                        cn = cn.decode("utf-8")
                    groups.append(cn)

            return groups

        except ldap.LDAPError as e:
            logger.error("LDAP group search error", user_dn=user_dn, error=str(e))
            return []

    async def test_connection(self) -> bool:
        """Test LDAP connection."""
        try:
            conn = self._get_connection()
            # Simple search to verify connection
            conn.search_s(
                self.config.base_dn,
                ldap.SCOPE_BASE,
                "(objectClass=*)",
                ["1.1"]
            )
            return True
        except ldap.LDAPError as e:
            logger.error("LDAP connection test failed", error=str(e))
            return False

    def close(self) -> None:
        """Close the LDAP connection."""
        self._close_connection()


class LDAPProviderRegistry:
    """Registry for managing multiple LDAP providers."""

    def __init__(self):
        self._providers: Dict[str, LDAPProvider] = {}

    def register_provider(self, config: LDAPConfig) -> LDAPProvider:
        """Register an LDAP provider."""
        provider = LDAPProvider(config)
        self._providers[config.name] = provider
        logger.info("LDAP provider registered", name=config.name)
        return provider

    def get_provider(self, name: str) -> Optional[LDAPProvider]:
        """Get provider by name."""
        return self._providers.get(name)

    def list_providers(self) -> List[str]:
        """List all registered provider names."""
        return list(self._providers.keys())

    def remove_provider(self, name: str) -> None:
        """Remove and close provider."""
        if name in self._providers:
            self._providers[name].close()
            del self._providers[name]
            logger.info("LDAP provider removed", name=name)

    def close_all(self) -> None:
        """Close all providers."""
        for provider in self._providers.values():
            provider.close()
        self._providers.clear()


# Factory function for Active Directory
def create_active_directory_provider(
    server_url: str,
    base_dn: str,
    bind_dn: str,
    bind_password: str,
    name: str = "active_directory"
) -> LDAPConfig:
    """Create Active Directory LDAP configuration."""
    return LDAPConfig(
        name=name,
        server_url=server_url,
        base_dn=base_dn,
        bind_dn=bind_dn,
        bind_password=bind_password,
        is_active_directory=True,
        user_search_filter="(sAMAccountName={username})",
        username_attr="sAMAccountName"
    )


# Factory for generic LDAP (OpenLDAP, etc.)
def create_openldap_provider(
    server_url: str,
    base_dn: str,
    bind_dn: str,
    bind_password: str,
    name: str = "openldap"
) -> LDAPConfig:
    """Create OpenLDAP configuration."""
    return LDAPConfig(
        name=name,
        server_url=server_url,
        base_dn=base_dn,
        bind_dn=bind_dn,
        bind_password=bind_password,
        is_active_directory=False,
        user_search_filter="(uid={username})",
        username_attr="uid",
        member_of_attr="memberOf"
    )
