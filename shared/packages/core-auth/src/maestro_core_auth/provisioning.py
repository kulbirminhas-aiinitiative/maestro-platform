"""
Just-In-Time (JIT) user provisioning for SSO integrations.

Handles automatic user creation/update on first login from external IdPs.
"""

from typing import Optional, Dict, Any, List, Callable
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from maestro_core_logging import get_logger

from .oidc import OIDCUserInfo
from .ldap import LDAPUserInfo

logger = get_logger(__name__)


class ProvisioningAction(str, Enum):
    """Actions taken during provisioning."""
    CREATED = "created"
    UPDATED = "updated"
    ACTIVATED = "activated"
    DEACTIVATED = "deactivated"
    NO_CHANGE = "no_change"


class ProvisionedUser(BaseModel):
    """Result of a provisioning operation."""
    user_id: int
    username: str
    email: Optional[str]
    action: ProvisioningAction
    provider: str
    external_id: str
    groups_synced: List[str] = []
    roles_assigned: List[str] = []
    attributes_updated: List[str] = []


@dataclass
class ProvisioningConfig:
    """Configuration for JIT provisioning."""
    # Auto-create users on first SSO login
    auto_create_users: bool = True
    # Auto-update user attributes on each login
    auto_update_users: bool = True
    # Sync groups from IdP
    sync_groups: bool = True
    # Map IdP groups to application roles
    group_to_role_mapping: Dict[str, List[str]] = field(default_factory=dict)
    # Default roles for new users
    default_roles: List[str] = field(default_factory=lambda: ["user"])
    # Attribute mapping from IdP to user model
    attribute_mapping: Dict[str, str] = field(default_factory=lambda: {
        "email": "email",
        "given_name": "first_name",
        "family_name": "last_name",
        "name": "display_name",
        "preferred_username": "username"
    })
    # Domain restrictions (empty = allow all)
    allowed_domains: List[str] = field(default_factory=list)
    # Required group membership for access
    required_groups: List[str] = field(default_factory=list)


class JITProvisioner:
    """
    Just-In-Time user provisioning handler.

    Usage:
        config = ProvisioningConfig(
            auto_create_users=True,
            sync_groups=True,
            group_to_role_mapping={
                "Admins": ["admin"],
                "Developers": ["developer", "user"],
                "Users": ["user"]
            }
        )
        provisioner = JITProvisioner(config)

        # On OIDC login
        result = await provisioner.provision_oidc_user(
            user_info=oidc_user_info,
            provider_name="azure_ad",
            db_session=session
        )
    """

    def __init__(self, config: ProvisioningConfig):
        self.config = config
        self._user_created_callbacks: List[Callable] = []
        self._user_updated_callbacks: List[Callable] = []

    def on_user_created(self, callback: Callable) -> None:
        """Register callback for user creation events."""
        self._user_created_callbacks.append(callback)

    def on_user_updated(self, callback: Callable) -> None:
        """Register callback for user update events."""
        self._user_updated_callbacks.append(callback)

    async def provision_oidc_user(
        self,
        user_info: OIDCUserInfo,
        provider_name: str,
        db_session: AsyncSession
    ) -> ProvisionedUser:
        """
        Provision user from OIDC user info.

        Args:
            user_info: User info from OIDC provider
            provider_name: Name of the OIDC provider
            db_session: Database session

        Returns:
            Provisioned user result
        """
        # Validate domain if restricted
        if self.config.allowed_domains:
            if not user_info.email:
                raise ProvisioningError("Email required for domain validation")
            domain = user_info.email.split("@")[1]
            if domain not in self.config.allowed_domains:
                raise ProvisioningError(f"Domain {domain} not allowed")

        # Check required groups
        if self.config.required_groups:
            if not any(g in user_info.groups for g in self.config.required_groups):
                raise ProvisioningError("User not in required groups")

        # Look up existing user
        existing_user = await self._find_user_by_external_id(
            provider_name,
            user_info.sub,
            db_session
        )

        if existing_user:
            if self.config.auto_update_users:
                return await self._update_user(
                    existing_user,
                    user_info,
                    provider_name,
                    db_session
                )
            return ProvisionedUser(
                user_id=existing_user.id,
                username=existing_user.username,
                email=existing_user.email,
                action=ProvisioningAction.NO_CHANGE,
                provider=provider_name,
                external_id=user_info.sub
            )

        if not self.config.auto_create_users:
            raise ProvisioningError("User not found and auto-creation disabled")

        return await self._create_user_from_oidc(
            user_info,
            provider_name,
            db_session
        )

    async def provision_ldap_user(
        self,
        user_info: LDAPUserInfo,
        provider_name: str,
        db_session: AsyncSession
    ) -> ProvisionedUser:
        """
        Provision user from LDAP user info.

        Args:
            user_info: User info from LDAP
            provider_name: Name of the LDAP provider
            db_session: Database session

        Returns:
            Provisioned user result
        """
        # Validate domain if restricted
        if self.config.allowed_domains and user_info.email:
            domain = user_info.email.split("@")[1]
            if domain not in self.config.allowed_domains:
                raise ProvisioningError(f"Domain {domain} not allowed")

        # Check required groups
        if self.config.required_groups:
            if not any(g in user_info.groups for g in self.config.required_groups):
                raise ProvisioningError("User not in required groups")

        # Look up existing user
        existing_user = await self._find_user_by_external_id(
            provider_name,
            user_info.dn,
            db_session
        )

        if existing_user:
            if self.config.auto_update_users:
                return await self._update_user_from_ldap(
                    existing_user,
                    user_info,
                    provider_name,
                    db_session
                )
            return ProvisionedUser(
                user_id=existing_user.id,
                username=existing_user.username,
                email=existing_user.email,
                action=ProvisioningAction.NO_CHANGE,
                provider=provider_name,
                external_id=user_info.dn
            )

        if not self.config.auto_create_users:
            raise ProvisioningError("User not found and auto-creation disabled")

        return await self._create_user_from_ldap(
            user_info,
            provider_name,
            db_session
        )

    async def _create_user_from_oidc(
        self,
        user_info: OIDCUserInfo,
        provider_name: str,
        db_session: AsyncSession
    ) -> ProvisionedUser:
        """Create new user from OIDC info."""
        # Map attributes
        username = user_info.preferred_username or user_info.email
        if not username:
            raise ProvisioningError("Cannot determine username")

        # Determine roles from groups
        roles = list(self.config.default_roles)
        synced_groups = []
        if self.config.sync_groups:
            for group in user_info.groups:
                if group in self.config.group_to_role_mapping:
                    roles.extend(self.config.group_to_role_mapping[group])
                    synced_groups.append(group)

        roles = list(set(roles))  # Remove duplicates

        # Create user in database
        # This is a placeholder - implement based on your user model
        user_id = await self._create_user_in_db(
            username=username,
            email=user_info.email,
            first_name=user_info.given_name,
            last_name=user_info.family_name,
            display_name=user_info.name,
            external_id=user_info.sub,
            provider=provider_name,
            roles=roles,
            db_session=db_session
        )

        # Trigger callbacks
        for callback in self._user_created_callbacks:
            await callback(user_id, provider_name, user_info)

        logger.info(
            "User created via JIT provisioning",
            user_id=user_id,
            username=username,
            provider=provider_name
        )

        return ProvisionedUser(
            user_id=user_id,
            username=username,
            email=user_info.email,
            action=ProvisioningAction.CREATED,
            provider=provider_name,
            external_id=user_info.sub,
            groups_synced=synced_groups,
            roles_assigned=roles
        )

    async def _create_user_from_ldap(
        self,
        user_info: LDAPUserInfo,
        provider_name: str,
        db_session: AsyncSession
    ) -> ProvisionedUser:
        """Create new user from LDAP info."""
        # Determine roles from groups
        roles = list(self.config.default_roles)
        synced_groups = []
        if self.config.sync_groups:
            for group in user_info.groups:
                if group in self.config.group_to_role_mapping:
                    roles.extend(self.config.group_to_role_mapping[group])
                    synced_groups.append(group)

        roles = list(set(roles))

        # Create user
        user_id = await self._create_user_in_db(
            username=user_info.username,
            email=user_info.email,
            first_name=user_info.first_name,
            last_name=user_info.last_name,
            display_name=user_info.display_name,
            external_id=user_info.dn,
            provider=provider_name,
            roles=roles,
            db_session=db_session
        )

        for callback in self._user_created_callbacks:
            await callback(user_id, provider_name, user_info)

        logger.info(
            "User created via LDAP JIT provisioning",
            user_id=user_id,
            username=user_info.username,
            provider=provider_name
        )

        return ProvisionedUser(
            user_id=user_id,
            username=user_info.username,
            email=user_info.email,
            action=ProvisioningAction.CREATED,
            provider=provider_name,
            external_id=user_info.dn,
            groups_synced=synced_groups,
            roles_assigned=roles
        )

    async def _update_user(
        self,
        existing_user: Any,
        user_info: OIDCUserInfo,
        provider_name: str,
        db_session: AsyncSession
    ) -> ProvisionedUser:
        """Update existing user from OIDC info."""
        updated_attrs = []

        # Check and update attributes
        if user_info.email and user_info.email != existing_user.email:
            existing_user.email = user_info.email
            updated_attrs.append("email")

        if user_info.given_name and user_info.given_name != getattr(existing_user, 'first_name', None):
            existing_user.first_name = user_info.given_name
            updated_attrs.append("first_name")

        if user_info.family_name and user_info.family_name != getattr(existing_user, 'last_name', None):
            existing_user.last_name = user_info.family_name
            updated_attrs.append("last_name")

        # Sync groups/roles
        synced_groups = []
        roles = list(self.config.default_roles)
        if self.config.sync_groups:
            for group in user_info.groups:
                if group in self.config.group_to_role_mapping:
                    roles.extend(self.config.group_to_role_mapping[group])
                    synced_groups.append(group)

        roles = list(set(roles))

        # Commit updates
        # await db_session.commit()

        if updated_attrs:
            for callback in self._user_updated_callbacks:
                await callback(existing_user.id, provider_name, updated_attrs)

        action = ProvisioningAction.UPDATED if updated_attrs else ProvisioningAction.NO_CHANGE

        return ProvisionedUser(
            user_id=existing_user.id,
            username=existing_user.username,
            email=existing_user.email,
            action=action,
            provider=provider_name,
            external_id=user_info.sub,
            groups_synced=synced_groups,
            roles_assigned=roles,
            attributes_updated=updated_attrs
        )

    async def _update_user_from_ldap(
        self,
        existing_user: Any,
        user_info: LDAPUserInfo,
        provider_name: str,
        db_session: AsyncSession
    ) -> ProvisionedUser:
        """Update existing user from LDAP info."""
        updated_attrs = []

        # Check active status
        if not user_info.is_active and existing_user.is_active:
            existing_user.is_active = False
            updated_attrs.append("is_active")

        # Update attributes
        if user_info.email and user_info.email != existing_user.email:
            existing_user.email = user_info.email
            updated_attrs.append("email")

        # Sync groups/roles
        synced_groups = []
        roles = list(self.config.default_roles)
        if self.config.sync_groups:
            for group in user_info.groups:
                if group in self.config.group_to_role_mapping:
                    roles.extend(self.config.group_to_role_mapping[group])
                    synced_groups.append(group)

        action = ProvisioningAction.UPDATED if updated_attrs else ProvisioningAction.NO_CHANGE

        return ProvisionedUser(
            user_id=existing_user.id,
            username=existing_user.username,
            email=existing_user.email,
            action=action,
            provider=provider_name,
            external_id=user_info.dn,
            groups_synced=synced_groups,
            roles_assigned=list(set(roles)),
            attributes_updated=updated_attrs
        )

    async def _find_user_by_external_id(
        self,
        provider: str,
        external_id: str,
        db_session: AsyncSession
    ) -> Optional[Any]:
        """Find user by external ID. Override this."""
        # Implementation depends on your user model
        # Example:
        # return await db_session.execute(
        #     select(User).where(
        #         User.sso_provider == provider,
        #         User.external_id == external_id
        #     )
        # ).scalar_one_or_none()
        return None

    async def _create_user_in_db(
        self,
        username: str,
        email: Optional[str],
        first_name: Optional[str],
        last_name: Optional[str],
        display_name: Optional[str],
        external_id: str,
        provider: str,
        roles: List[str],
        db_session: AsyncSession
    ) -> int:
        """Create user in database. Override this."""
        # Implementation depends on your user model
        raise NotImplementedError("Implement _create_user_in_db")


class ProvisioningError(Exception):
    """Error during user provisioning."""
    pass
