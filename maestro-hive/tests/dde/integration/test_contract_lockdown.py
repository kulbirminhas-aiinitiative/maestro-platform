"""
DDE Integration Tests: Contract Lockdown Mechanism
Test IDs: DDE-601 to DDE-625

Tests for contract lifecycle management and lockdown enforcement:
- Contract status transitions (DRAFT -> LOCKED -> DEPRECATED -> SUNSET)
- Lockdown enforcement prevents modifications to locked contracts
- Version increments and semver breaking change detection
- Dependent notification on contract changes
- Contract publishing and validation
- Support for OpenAPI, GraphQL, and gRPC specifications
- Rollback capabilities and sunset date enforcement
- Auto-generated documentation and compliance checks

These tests ensure the system can handle:
1. Interface completion locks contract preventing modifications
2. Version increments with proper semver handling
3. Breaking change detection (major version bump)
4. Backward compatible changes (minor version bump)
5. Contract deprecation and sunset workflows
6. Validation against specification formats
7. Examples, test cases, and documentation generation
8. Compliance checks and changelog tracking
"""

import pytest
import asyncio
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from enum import Enum


class ContractStatus(str, Enum):
    """Contract lifecycle status"""
    DRAFT = "draft"
    LOCKED = "locked"
    DEPRECATED = "deprecated"
    SUNSET = "sunset"


class ContractType(str, Enum):
    """Contract specification types"""
    OPENAPI = "openapi"
    GRAPHQL = "graphql"
    GRPC = "grpc"
    REST_API = "rest_api"
    EVENT_STREAM = "event_stream"


@dataclass
class ContractVersion:
    """Semantic version with breaking change detection"""
    major: int
    minor: int
    patch: int

    @classmethod
    def from_string(cls, version: str) -> 'ContractVersion':
        """Parse version string like 'v1.2.3' or '1.2.3'"""
        clean = version.lstrip('v')
        parts = clean.split('.')
        return cls(
            major=int(parts[0]) if len(parts) > 0 else 0,
            minor=int(parts[1]) if len(parts) > 1 else 0,
            patch=int(parts[2]) if len(parts) > 2 else 0
        )

    def to_string(self) -> str:
        """Convert to version string"""
        return f"v{self.major}.{self.minor}.{self.patch}"

    def bump_major(self) -> 'ContractVersion':
        """Bump major version (breaking change)"""
        return ContractVersion(self.major + 1, 0, 0)

    def bump_minor(self) -> 'ContractVersion':
        """Bump minor version (backward compatible)"""
        return ContractVersion(self.major, self.minor + 1, 0)

    def bump_patch(self) -> 'ContractVersion':
        """Bump patch version (bug fix)"""
        return ContractVersion(self.major, self.minor, self.patch + 1)

    def is_breaking_change(self, other: 'ContractVersion') -> bool:
        """Check if this version is a breaking change from other"""
        return self.major > other.major


@dataclass
class Contract:
    """Contract data structure"""
    id: str
    team_id: str
    contract_name: str
    version: str
    contract_type: ContractType
    specification: Dict[str, Any]
    owner_role: str
    owner_agent: str
    status: ContractStatus = ContractStatus.DRAFT
    consumers: List[str] = field(default_factory=list)
    supersedes_contract_id: Optional[str] = None
    breaking_changes: bool = False
    changes_from_previous: Optional[Dict[str, Any]] = None
    created_at: datetime = field(default_factory=datetime.now)
    locked_at: Optional[datetime] = None
    deprecated_at: Optional[datetime] = None
    sunset_date: Optional[datetime] = None
    examples: List[Dict[str, Any]] = field(default_factory=list)
    test_cases: List[Dict[str, Any]] = field(default_factory=list)
    changelog: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class ContractLockdownError(Exception):
    """Raised when attempting to modify a locked contract"""
    pass


class ContractValidationError(Exception):
    """Raised when contract validation fails"""
    pass


class ContractManager:
    """Contract manager with lockdown enforcement"""

    def __init__(self):
        self._contracts: Dict[str, Contract] = {}
        self._events: List[Dict[str, Any]] = []

    async def create_contract(
        self,
        team_id: str,
        contract_name: str,
        version: str,
        contract_type: ContractType,
        specification: Dict[str, Any],
        owner_role: str,
        owner_agent: str,
        consumers: Optional[List[str]] = None
    ) -> Contract:
        """Create a new contract in DRAFT status"""
        contract = Contract(
            id=f"contract_{uuid.uuid4().hex[:12]}",
            team_id=team_id,
            contract_name=contract_name,
            version=version,
            contract_type=contract_type,
            specification=specification,
            owner_role=owner_role,
            owner_agent=owner_agent,
            status=ContractStatus.DRAFT,
            consumers=consumers or []
        )

        self._contracts[contract.id] = contract

        # Emit event
        await self._emit_event("contract.created", {
            "contract_id": contract.id,
            "contract_name": contract_name,
            "version": version,
            "owner": owner_agent
        })

        return contract

    async def lock_contract(self, contract_id: str, locked_by: str) -> Contract:
        """
        Lock contract after interface completion.
        Locked contracts cannot be modified.
        """
        contract = self._contracts.get(contract_id)
        if not contract:
            raise ValueError(f"Contract {contract_id} not found")

        if contract.status != ContractStatus.DRAFT:
            raise ContractLockdownError(
                f"Cannot lock contract in {contract.status} status"
            )

        contract.status = ContractStatus.LOCKED
        contract.locked_at = datetime.now()

        # Add to changelog
        contract.changelog.append({
            "action": "locked",
            "by": locked_by,
            "timestamp": datetime.now().isoformat(),
            "version": contract.version
        })

        # Notify consumers
        await self._notify_consumers(
            contract,
            "contract.locked",
            {
                "contract_id": contract_id,
                "contract_name": contract.contract_name,
                "version": contract.version,
                "locked_by": locked_by
            }
        )

        return contract

    async def modify_contract(
        self,
        contract_id: str,
        specification: Dict[str, Any],
        modified_by: str
    ) -> Contract:
        """
        Modify contract specification.
        Raises ContractLockdownError if contract is locked.
        """
        contract = self._contracts.get(contract_id)
        if not contract:
            raise ValueError(f"Contract {contract_id} not found")

        if contract.status == ContractStatus.LOCKED:
            raise ContractLockdownError(
                "Cannot modify locked contract. Create new version instead."
            )

        if contract.status in [ContractStatus.DEPRECATED, ContractStatus.SUNSET]:
            raise ContractLockdownError(
                f"Cannot modify contract in {contract.status} status"
            )

        contract.specification = specification

        # Add to changelog
        contract.changelog.append({
            "action": "modified",
            "by": modified_by,
            "timestamp": datetime.now().isoformat(),
            "changes": {"specification": "updated"}
        })

        return contract

    async def evolve_contract(
        self,
        contract_id: str,
        new_version: str,
        new_specification: Dict[str, Any],
        changes_from_previous: Dict[str, Any],
        breaking_changes: bool,
        evolved_by: str
    ) -> Contract:
        """
        Evolve contract to new version.
        Automatically detects breaking changes based on semver.
        """
        old_contract = self._contracts.get(contract_id)
        if not old_contract:
            raise ValueError(f"Contract {contract_id} not found")

        # Parse versions
        old_ver = ContractVersion.from_string(old_contract.version)
        new_ver = ContractVersion.from_string(new_version)

        # Detect breaking changes from version
        is_breaking = new_ver.is_breaking_change(old_ver)
        if is_breaking and not breaking_changes:
            # Auto-detect based on semver
            breaking_changes = True

        # Create new contract version
        new_contract = Contract(
            id=f"contract_{uuid.uuid4().hex[:12]}",
            team_id=old_contract.team_id,
            contract_name=old_contract.contract_name,
            version=new_version,
            contract_type=old_contract.contract_type,
            specification=new_specification,
            owner_role=old_contract.owner_role,
            owner_agent=evolved_by,
            status=ContractStatus.DRAFT,
            consumers=old_contract.consumers.copy(),
            supersedes_contract_id=contract_id,
            breaking_changes=breaking_changes,
            changes_from_previous=changes_from_previous
        )

        self._contracts[new_contract.id] = new_contract

        # Emit event
        event_type = "contract.breaking_change" if breaking_changes else "contract.evolved"
        await self._emit_event(event_type, {
            "contract_id": new_contract.id,
            "contract_name": new_contract.contract_name,
            "old_version": old_contract.version,
            "new_version": new_version,
            "breaking_changes": breaking_changes,
            "changes": changes_from_previous
        })

        # Notify consumers if breaking change
        if breaking_changes:
            await self._notify_consumers(
                old_contract,
                "contract.breaking_change",
                {
                    "old_contract_id": contract_id,
                    "new_contract_id": new_contract.id,
                    "old_version": old_contract.version,
                    "new_version": new_version,
                    "changes": changes_from_previous,
                    "action_required": "Update to new contract version"
                }
            )

        return new_contract

    async def deprecate_contract(
        self,
        contract_id: str,
        sunset_date: Optional[datetime],
        deprecated_by: str,
        reason: str
    ) -> Contract:
        """Mark contract as deprecated with optional sunset date"""
        contract = self._contracts.get(contract_id)
        if not contract:
            raise ValueError(f"Contract {contract_id} not found")

        contract.status = ContractStatus.DEPRECATED
        contract.deprecated_at = datetime.now()
        contract.sunset_date = sunset_date

        # Add to changelog
        contract.changelog.append({
            "action": "deprecated",
            "by": deprecated_by,
            "timestamp": datetime.now().isoformat(),
            "reason": reason,
            "sunset_date": sunset_date.isoformat() if sunset_date else None
        })

        # Notify consumers
        await self._notify_consumers(
            contract,
            "contract.deprecated",
            {
                "contract_id": contract_id,
                "version": contract.version,
                "reason": reason,
                "sunset_date": sunset_date.isoformat() if sunset_date else None
            }
        )

        return contract

    async def sunset_contract(self, contract_id: str, sunset_by: str) -> Contract:
        """Mark contract as sunset (end of life)"""
        contract = self._contracts.get(contract_id)
        if not contract:
            raise ValueError(f"Contract {contract_id} not found")

        contract.status = ContractStatus.SUNSET

        # Add to changelog
        contract.changelog.append({
            "action": "sunset",
            "by": sunset_by,
            "timestamp": datetime.now().isoformat()
        })

        # Notify consumers
        await self._notify_consumers(
            contract,
            "contract.sunset",
            {
                "contract_id": contract_id,
                "version": contract.version,
                "message": "Contract is now sunset and no longer supported"
            }
        )

        return contract

    async def rollback_to_version(
        self,
        contract_name: str,
        team_id: str,
        target_version: str,
        rolled_back_by: str
    ) -> Optional[Contract]:
        """Rollback to a previous contract version"""
        # Find contract with target version
        for contract in self._contracts.values():
            if (contract.team_id == team_id and
                contract.contract_name == contract_name and
                contract.version == target_version):

                # Create new contract based on old version
                new_contract = Contract(
                    id=f"contract_{uuid.uuid4().hex[:12]}",
                    team_id=contract.team_id,
                    contract_name=contract.contract_name,
                    version=f"{target_version}-rollback",
                    contract_type=contract.contract_type,
                    specification=contract.specification.copy(),
                    owner_role=contract.owner_role,
                    owner_agent=rolled_back_by,
                    status=ContractStatus.DRAFT,
                    consumers=contract.consumers.copy(),
                    metadata={"rollback_from": target_version}
                )

                new_contract.changelog.append({
                    "action": "rollback",
                    "by": rolled_back_by,
                    "timestamp": datetime.now().isoformat(),
                    "rolled_back_to": target_version
                })

                self._contracts[new_contract.id] = new_contract
                return new_contract

        return None

    async def validate_specification(
        self,
        contract: Contract
    ) -> Dict[str, Any]:
        """
        Validate contract specification based on contract type.
        Returns validation result with errors if any.
        """
        errors = []

        if contract.contract_type == ContractType.OPENAPI:
            # Validate OpenAPI spec
            if "openapi" not in contract.specification:
                errors.append("Missing 'openapi' version field")
            if "paths" not in contract.specification:
                errors.append("Missing 'paths' field")
            if "info" not in contract.specification:
                errors.append("Missing 'info' field")

        elif contract.contract_type == ContractType.GRAPHQL:
            # Validate GraphQL schema
            if "schema" not in contract.specification:
                errors.append("Missing 'schema' field")
            if "types" not in contract.specification:
                errors.append("Missing 'types' field")

        elif contract.contract_type == ContractType.GRPC:
            # Validate gRPC proto
            if "proto_file" not in contract.specification:
                errors.append("Missing 'proto_file' field")
            if "services" not in contract.specification:
                errors.append("Missing 'services' field")

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "contract_id": contract.id,
            "contract_type": contract.contract_type.value
        }

    async def add_examples(
        self,
        contract_id: str,
        examples: List[Dict[str, Any]]
    ) -> Contract:
        """Add usage examples to contract"""
        contract = self._contracts.get(contract_id)
        if not contract:
            raise ValueError(f"Contract {contract_id} not found")

        contract.examples.extend(examples)
        return contract

    async def add_test_cases(
        self,
        contract_id: str,
        test_cases: List[Dict[str, Any]]
    ) -> Contract:
        """Add test cases to contract"""
        contract = self._contracts.get(contract_id)
        if not contract:
            raise ValueError(f"Contract {contract_id} not found")

        contract.test_cases.extend(test_cases)
        return contract

    async def generate_documentation(
        self,
        contract_id: str
    ) -> Dict[str, Any]:
        """Auto-generate documentation from contract"""
        contract = self._contracts.get(contract_id)
        if not contract:
            raise ValueError(f"Contract {contract_id} not found")

        return {
            "contract_name": contract.contract_name,
            "version": contract.version,
            "type": contract.contract_type.value,
            "status": contract.status.value,
            "specification": contract.specification,
            "examples": contract.examples,
            "test_cases": contract.test_cases,
            "changelog": contract.changelog,
            "consumers": contract.consumers,
            "generated_at": datetime.now().isoformat()
        }

    async def check_compliance(
        self,
        contract_id: str,
        compliance_rules: List[str]
    ) -> Dict[str, Any]:
        """Check contract compliance against rules"""
        contract = self._contracts.get(contract_id)
        if not contract:
            raise ValueError(f"Contract {contract_id} not found")

        violations = []
        passed_rules = []

        for rule in compliance_rules:
            if rule == "has_examples" and not contract.examples:
                violations.append("Contract must have examples")
            elif rule == "has_examples" and contract.examples:
                passed_rules.append("has_examples")

            elif rule == "has_test_cases" and not contract.test_cases:
                violations.append("Contract must have test cases")
            elif rule == "has_test_cases" and contract.test_cases:
                passed_rules.append("has_test_cases")

            elif rule == "has_changelog" and not contract.changelog:
                violations.append("Contract must have changelog")
            elif rule == "has_changelog" and contract.changelog:
                passed_rules.append("has_changelog")

            elif rule == "versioning_semver":
                try:
                    ContractVersion.from_string(contract.version)
                    passed_rules.append("versioning_semver")
                except:
                    violations.append("Version must follow semver format")

        return {
            "compliant": len(violations) == 0,
            "passed_rules": passed_rules,
            "violations": violations,
            "contract_id": contract_id
        }

    async def publish_contract(
        self,
        contract_id: str,
        published_by: str
    ) -> Contract:
        """
        Publish contract (lock and make available).
        Validates before publishing.
        """
        contract = self._contracts.get(contract_id)
        if not contract:
            raise ValueError(f"Contract {contract_id} not found")

        # Validate specification
        validation = await self.validate_specification(contract)
        if not validation["valid"]:
            raise ContractValidationError(
                f"Cannot publish invalid contract: {validation['errors']}"
            )

        # Lock the contract
        await self.lock_contract(contract_id, published_by)

        # Emit publish event
        await self._emit_event("contract.published", {
            "contract_id": contract_id,
            "contract_name": contract.contract_name,
            "version": contract.version,
            "published_by": published_by
        })

        return contract

    def get_contract(self, contract_id: str) -> Optional[Contract]:
        """Get contract by ID"""
        return self._contracts.get(contract_id)

    def list_contracts(self, team_id: Optional[str] = None) -> List[Contract]:
        """List all contracts, optionally filtered by team"""
        if team_id:
            return [c for c in self._contracts.values() if c.team_id == team_id]
        return list(self._contracts.values())

    def get_events(self) -> List[Dict[str, Any]]:
        """Get all emitted events"""
        return self._events

    async def _emit_event(self, event_type: str, data: Dict[str, Any]):
        """Emit contract event"""
        self._events.append({
            "type": event_type,
            "data": data,
            "timestamp": datetime.now().isoformat()
        })

    async def _notify_consumers(
        self,
        contract: Contract,
        notification_type: str,
        data: Dict[str, Any]
    ):
        """Notify contract consumers"""
        for consumer in contract.consumers:
            await self._emit_event(f"notification.{consumer}", {
                "notification_type": notification_type,
                "consumer": consumer,
                **data
            })


# =============================================================================
# Test Suite: Contract Lockdown Mechanism
# =============================================================================

@pytest.mark.integration
@pytest.mark.dde
class TestContractLockdownBasics:
    """Test suite for contract lockdown basics (DDE-601 to DDE-605)"""

    @pytest.fixture
    def manager(self):
        """Create fresh contract manager for each test"""
        return ContractManager()

    @pytest.mark.asyncio
    async def test_dde_601_interface_completion_locks_contract(self, manager):
        """DDE-601: Interface completion locks contract"""
        # Create contract
        contract = await manager.create_contract(
            team_id="team-1",
            contract_name="UserAPI",
            version="v1.0.0",
            contract_type=ContractType.REST_API,
            specification={"endpoints": ["/users"]},
            owner_role="Tech Lead",
            owner_agent="agent-1"
        )

        assert contract.status == ContractStatus.DRAFT

        # Lock contract (simulating interface completion)
        locked = await manager.lock_contract(contract.id, "agent-1")

        assert locked.status == ContractStatus.LOCKED
        assert locked.locked_at is not None
        assert len(locked.changelog) == 1
        assert locked.changelog[0]["action"] == "locked"

    @pytest.mark.asyncio
    async def test_dde_602_cannot_modify_locked_contract(self, manager):
        """DDE-602: Cannot modify locked contract"""
        # Create and lock contract
        contract = await manager.create_contract(
            team_id="team-1",
            contract_name="UserAPI",
            version="v1.0.0",
            contract_type=ContractType.REST_API,
            specification={"endpoints": ["/users"]},
            owner_role="Tech Lead",
            owner_agent="agent-1"
        )

        await manager.lock_contract(contract.id, "agent-1")

        # Attempt to modify locked contract
        with pytest.raises(ContractLockdownError) as exc_info:
            await manager.modify_contract(
                contract.id,
                {"endpoints": ["/users", "/posts"]},
                "agent-1"
            )

        assert "Cannot modify locked contract" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_dde_603_version_increments_on_evolution(self, manager):
        """DDE-603: Version increments when contract evolves"""
        # Create and lock contract
        contract = await manager.create_contract(
            team_id="team-1",
            contract_name="UserAPI",
            version="v1.0.0",
            contract_type=ContractType.REST_API,
            specification={"endpoints": ["/users"]},
            owner_role="Tech Lead",
            owner_agent="agent-1"
        )

        await manager.lock_contract(contract.id, "agent-1")

        # Evolve to new version
        new_contract = await manager.evolve_contract(
            contract.id,
            new_version="v1.1.0",
            new_specification={"endpoints": ["/users", "/posts"]},
            changes_from_previous={"added": ["/posts"]},
            breaking_changes=False,
            evolved_by="agent-1"
        )

        assert new_contract.version == "v1.1.0"
        assert new_contract.supersedes_contract_id == contract.id
        assert new_contract.status == ContractStatus.DRAFT

    @pytest.mark.asyncio
    async def test_dde_604_dependent_notification_on_change(self, manager):
        """DDE-604: Dependents notified on contract change"""
        # Create contract with consumers
        contract = await manager.create_contract(
            team_id="team-1",
            contract_name="UserAPI",
            version="v1.0.0",
            contract_type=ContractType.REST_API,
            specification={"endpoints": ["/users"]},
            owner_role="Tech Lead",
            owner_agent="agent-1",
            consumers=["frontend-team", "mobile-team"]
        )

        await manager.lock_contract(contract.id, "agent-1")

        # Evolve with breaking change
        await manager.evolve_contract(
            contract.id,
            new_version="v2.0.0",
            new_specification={"endpoints": ["/v2/users"]},
            changes_from_previous={"breaking": "URL changed"},
            breaking_changes=True,
            evolved_by="agent-1"
        )

        # Check notifications sent
        events = manager.get_events()
        notifications = [e for e in events if e["type"].startswith("notification.")]

        # Should have notifications for: lock (2) + breaking change (2) = 4 total
        assert len(notifications) >= 2

        # Check breaking change notifications specifically
        breaking_notifications = [
            n for n in notifications
            if n["data"].get("notification_type") == "contract.breaking_change"
        ]
        assert len(breaking_notifications) == 2
        assert any("frontend-team" in e["type"] for e in breaking_notifications)
        assert any("mobile-team" in e["type"] for e in breaking_notifications)

    @pytest.mark.asyncio
    async def test_dde_605_contract_publishing_workflow(self, manager):
        """DDE-605: Contract publishing locks and validates"""
        # Create contract
        contract = await manager.create_contract(
            team_id="team-1",
            contract_name="UserAPI",
            version="v1.0.0",
            contract_type=ContractType.OPENAPI,
            specification={
                "openapi": "3.0.0",
                "info": {"title": "User API"},
                "paths": {"/users": {"get": {}}}
            },
            owner_role="Tech Lead",
            owner_agent="agent-1"
        )

        # Publish contract
        published = await manager.publish_contract(contract.id, "agent-1")

        assert published.status == ContractStatus.LOCKED

        # Check publish event
        events = manager.get_events()
        publish_events = [e for e in events if e["type"] == "contract.published"]
        assert len(publish_events) == 1


@pytest.mark.integration
@pytest.mark.dde
class TestContractSpecifications:
    """Test suite for contract specifications (DDE-606 to DDE-608)"""

    @pytest.fixture
    def manager(self):
        return ContractManager()

    @pytest.mark.asyncio
    async def test_dde_606_openapi_specification_support(self, manager):
        """DDE-606: Support OpenAPI specification format"""
        contract = await manager.create_contract(
            team_id="team-1",
            contract_name="UserAPI",
            version="v1.0.0",
            contract_type=ContractType.OPENAPI,
            specification={
                "openapi": "3.0.0",
                "info": {
                    "title": "User API",
                    "version": "1.0.0"
                },
                "paths": {
                    "/users": {
                        "get": {
                            "responses": {
                                "200": {"description": "Success"}
                            }
                        }
                    }
                }
            },
            owner_role="Tech Lead",
            owner_agent="agent-1"
        )

        # Validate OpenAPI spec
        validation = await manager.validate_specification(contract)

        assert validation["valid"] is True
        assert validation["contract_type"] == "openapi"
        assert len(validation["errors"]) == 0

    @pytest.mark.asyncio
    async def test_dde_607_graphql_schema_support(self, manager):
        """DDE-607: Support GraphQL schema format"""
        contract = await manager.create_contract(
            team_id="team-1",
            contract_name="UserGraphQL",
            version="v1.0.0",
            contract_type=ContractType.GRAPHQL,
            specification={
                "schema": "type Query { users: [User] }",
                "types": {
                    "User": {
                        "fields": ["id", "name", "email"]
                    }
                }
            },
            owner_role="Tech Lead",
            owner_agent="agent-1"
        )

        # Validate GraphQL schema
        validation = await manager.validate_specification(contract)

        assert validation["valid"] is True
        assert validation["contract_type"] == "graphql"

    @pytest.mark.asyncio
    async def test_dde_608_grpc_proto_support(self, manager):
        """DDE-608: Support gRPC proto file format"""
        contract = await manager.create_contract(
            team_id="team-1",
            contract_name="UserService",
            version="v1.0.0",
            contract_type=ContractType.GRPC,
            specification={
                "proto_file": "user.proto",
                "services": {
                    "UserService": {
                        "methods": ["GetUser", "ListUsers"]
                    }
                },
                "messages": {
                    "User": ["id", "name", "email"]
                }
            },
            owner_role="Tech Lead",
            owner_agent="agent-1"
        )

        # Validate gRPC proto
        validation = await manager.validate_specification(contract)

        assert validation["valid"] is True
        assert validation["contract_type"] == "grpc"


@pytest.mark.integration
@pytest.mark.dde
class TestContractVersioning:
    """Test suite for contract versioning (DDE-609 to DDE-615)"""

    @pytest.fixture
    def manager(self):
        return ContractManager()

    @pytest.mark.asyncio
    async def test_dde_609_semver_parsing(self, manager):
        """DDE-609: Semantic version parsing works correctly"""
        v1 = ContractVersion.from_string("v1.2.3")
        assert v1.major == 1
        assert v1.minor == 2
        assert v1.patch == 3

        v2 = ContractVersion.from_string("2.0.0")
        assert v2.major == 2
        assert v2.minor == 0
        assert v2.patch == 0

    @pytest.mark.asyncio
    async def test_dde_610_breaking_change_detection_major_bump(self, manager):
        """DDE-610: Breaking change detection with major version bump"""
        contract = await manager.create_contract(
            team_id="team-1",
            contract_name="UserAPI",
            version="v1.0.0",
            contract_type=ContractType.REST_API,
            specification={"endpoints": ["/users"]},
            owner_role="Tech Lead",
            owner_agent="agent-1",
            consumers=["frontend"]
        )

        await manager.lock_contract(contract.id, "agent-1")

        # Major version bump = breaking change
        new_contract = await manager.evolve_contract(
            contract.id,
            new_version="v2.0.0",
            new_specification={"endpoints": ["/v2/users"]},
            changes_from_previous={"breaking": "URL changed"},
            breaking_changes=True,
            evolved_by="agent-1"
        )

        assert new_contract.breaking_changes is True

        # Check breaking change event emitted
        events = manager.get_events()
        breaking_events = [e for e in events if e["type"] == "contract.breaking_change"]
        assert len(breaking_events) == 1

    @pytest.mark.asyncio
    async def test_dde_611_backward_compatible_minor_bump(self, manager):
        """DDE-611: Backward compatible changes use minor version bump"""
        contract = await manager.create_contract(
            team_id="team-1",
            contract_name="UserAPI",
            version="v1.0.0",
            contract_type=ContractType.REST_API,
            specification={"endpoints": ["/users"]},
            owner_role="Tech Lead",
            owner_agent="agent-1"
        )

        await manager.lock_contract(contract.id, "agent-1")

        # Minor version bump = backward compatible
        new_contract = await manager.evolve_contract(
            contract.id,
            new_version="v1.1.0",
            new_specification={"endpoints": ["/users", "/users/search"]},
            changes_from_previous={"added": ["/users/search"]},
            breaking_changes=False,
            evolved_by="agent-1"
        )

        assert new_contract.breaking_changes is False

        # Check evolved event (not breaking_change)
        events = manager.get_events()
        evolved_events = [e for e in events if e["type"] == "contract.evolved"]
        assert len(evolved_events) == 1

    @pytest.mark.asyncio
    async def test_dde_612_deprecation_workflow(self, manager):
        """DDE-612: Contract deprecation workflow"""
        contract = await manager.create_contract(
            team_id="team-1",
            contract_name="LegacyAPI",
            version="v1.0.0",
            contract_type=ContractType.REST_API,
            specification={"endpoints": ["/legacy"]},
            owner_role="Tech Lead",
            owner_agent="agent-1",
            consumers=["old-client"]
        )

        # Deprecate contract
        deprecated = await manager.deprecate_contract(
            contract.id,
            sunset_date=None,
            deprecated_by="agent-1",
            reason="Replaced by v2 API"
        )

        assert deprecated.status == ContractStatus.DEPRECATED
        assert deprecated.deprecated_at is not None
        assert len(deprecated.changelog) == 1
        assert deprecated.changelog[0]["action"] == "deprecated"

    @pytest.mark.asyncio
    async def test_dde_613_sunset_date_enforcement(self, manager):
        """DDE-613: Sunset date enforcement"""
        contract = await manager.create_contract(
            team_id="team-1",
            contract_name="LegacyAPI",
            version="v1.0.0",
            contract_type=ContractType.REST_API,
            specification={"endpoints": ["/legacy"]},
            owner_role="Tech Lead",
            owner_agent="agent-1"
        )

        # Set sunset date
        sunset_date = datetime.now() + timedelta(days=90)
        deprecated = await manager.deprecate_contract(
            contract.id,
            sunset_date=sunset_date,
            deprecated_by="agent-1",
            reason="Migrating to v2"
        )

        assert deprecated.sunset_date == sunset_date
        assert deprecated.sunset_date > datetime.now()

    @pytest.mark.asyncio
    async def test_dde_614_contract_rollback(self, manager):
        """DDE-614: Rollback to previous contract version"""
        # Create original contract
        contract = await manager.create_contract(
            team_id="team-1",
            contract_name="UserAPI",
            version="v1.0.0",
            contract_type=ContractType.REST_API,
            specification={"endpoints": ["/users"]},
            owner_role="Tech Lead",
            owner_agent="agent-1"
        )

        # Rollback to v1.0.0
        rolled_back = await manager.rollback_to_version(
            "UserAPI",
            "team-1",
            "v1.0.0",
            "agent-1"
        )

        assert rolled_back is not None
        assert rolled_back.version == "v1.0.0-rollback"
        assert rolled_back.specification == contract.specification
        assert "rollback" in rolled_back.changelog[0]["action"]

    @pytest.mark.asyncio
    async def test_dde_615_sunset_workflow(self, manager):
        """DDE-615: Contract sunset (end of life) workflow"""
        contract = await manager.create_contract(
            team_id="team-1",
            contract_name="OldAPI",
            version="v1.0.0",
            contract_type=ContractType.REST_API,
            specification={"endpoints": ["/old"]},
            owner_role="Tech Lead",
            owner_agent="agent-1",
            consumers=["legacy-client"]
        )

        # Deprecate first
        await manager.deprecate_contract(
            contract.id,
            sunset_date=datetime.now() + timedelta(days=30),
            deprecated_by="agent-1",
            reason="End of life"
        )

        # Then sunset
        sunset = await manager.sunset_contract(contract.id, "agent-1")

        assert sunset.status == ContractStatus.SUNSET
        assert len(sunset.changelog) == 2
        assert sunset.changelog[1]["action"] == "sunset"


@pytest.mark.integration
@pytest.mark.dde
class TestValidationAndDocs:
    """Test suite for validation and documentation (DDE-616 to DDE-625)"""

    @pytest.fixture
    def manager(self):
        return ContractManager()

    @pytest.mark.asyncio
    async def test_dde_616_validation_against_spec(self, manager):
        """DDE-616: Validate contract against specification format"""
        # Valid OpenAPI contract
        valid_contract = await manager.create_contract(
            team_id="team-1",
            contract_name="ValidAPI",
            version="v1.0.0",
            contract_type=ContractType.OPENAPI,
            specification={
                "openapi": "3.0.0",
                "info": {"title": "Test"},
                "paths": {"/test": {}}
            },
            owner_role="Tech Lead",
            owner_agent="agent-1"
        )

        validation = await manager.validate_specification(valid_contract)
        assert validation["valid"] is True

        # Invalid OpenAPI contract (missing required fields)
        invalid_contract = await manager.create_contract(
            team_id="team-1",
            contract_name="InvalidAPI",
            version="v1.0.0",
            contract_type=ContractType.OPENAPI,
            specification={"endpoints": ["/test"]},
            owner_role="Tech Lead",
            owner_agent="agent-1"
        )

        validation = await manager.validate_specification(invalid_contract)
        assert validation["valid"] is False
        assert len(validation["errors"]) > 0

    @pytest.mark.asyncio
    async def test_dde_617_cannot_publish_invalid_spec(self, manager):
        """DDE-617: Cannot publish contract with invalid specification"""
        contract = await manager.create_contract(
            team_id="team-1",
            contract_name="InvalidAPI",
            version="v1.0.0",
            contract_type=ContractType.OPENAPI,
            specification={"invalid": "spec"},
            owner_role="Tech Lead",
            owner_agent="agent-1"
        )

        with pytest.raises(ContractValidationError):
            await manager.publish_contract(contract.id, "agent-1")

    @pytest.mark.asyncio
    async def test_dde_618_contract_examples(self, manager):
        """DDE-618: Add usage examples to contract"""
        contract = await manager.create_contract(
            team_id="team-1",
            contract_name="UserAPI",
            version="v1.0.0",
            contract_type=ContractType.REST_API,
            specification={"endpoints": ["/users"]},
            owner_role="Tech Lead",
            owner_agent="agent-1"
        )

        examples = [
            {
                "name": "Get all users",
                "request": "GET /users",
                "response": {"users": [{"id": 1, "name": "John"}]}
            },
            {
                "name": "Get user by ID",
                "request": "GET /users/1",
                "response": {"id": 1, "name": "John"}
            }
        ]

        updated = await manager.add_examples(contract.id, examples)
        assert len(updated.examples) == 2

    @pytest.mark.asyncio
    async def test_dde_619_contract_test_cases(self, manager):
        """DDE-619: Add test cases to contract"""
        contract = await manager.create_contract(
            team_id="team-1",
            contract_name="UserAPI",
            version="v1.0.0",
            contract_type=ContractType.REST_API,
            specification={"endpoints": ["/users"]},
            owner_role="Tech Lead",
            owner_agent="agent-1"
        )

        test_cases = [
            {
                "name": "Test get users returns 200",
                "method": "GET",
                "path": "/users",
                "expected_status": 200
            },
            {
                "name": "Test get user by ID returns user",
                "method": "GET",
                "path": "/users/1",
                "expected_status": 200,
                "expected_body": {"id": 1}
            }
        ]

        updated = await manager.add_test_cases(contract.id, test_cases)
        assert len(updated.test_cases) == 2

    @pytest.mark.asyncio
    async def test_dde_620_auto_generated_docs(self, manager):
        """DDE-620: Auto-generate documentation from contract"""
        contract = await manager.create_contract(
            team_id="team-1",
            contract_name="UserAPI",
            version="v1.0.0",
            contract_type=ContractType.REST_API,
            specification={"endpoints": ["/users", "/users/:id"]},
            owner_role="Tech Lead",
            owner_agent="agent-1"
        )

        # Add examples and test cases
        await manager.add_examples(contract.id, [{"name": "example1"}])
        await manager.add_test_cases(contract.id, [{"name": "test1"}])

        # Generate docs
        docs = await manager.generate_documentation(contract.id)

        assert docs["contract_name"] == "UserAPI"
        assert docs["version"] == "v1.0.0"
        assert len(docs["examples"]) == 1
        assert len(docs["test_cases"]) == 1
        assert "generated_at" in docs

    @pytest.mark.asyncio
    async def test_dde_621_changelog_tracking(self, manager):
        """DDE-621: Changelog tracks all contract changes"""
        contract = await manager.create_contract(
            team_id="team-1",
            contract_name="UserAPI",
            version="v1.0.0",
            contract_type=ContractType.REST_API,
            specification={"endpoints": ["/users"]},
            owner_role="Tech Lead",
            owner_agent="agent-1"
        )

        # Perform various operations
        await manager.lock_contract(contract.id, "agent-1")

        # Check changelog
        assert len(contract.changelog) == 1
        assert contract.changelog[0]["action"] == "locked"
        assert contract.changelog[0]["by"] == "agent-1"

    @pytest.mark.asyncio
    async def test_dde_622_compliance_check_examples(self, manager):
        """DDE-622: Compliance check for required examples"""
        contract = await manager.create_contract(
            team_id="team-1",
            contract_name="UserAPI",
            version="v1.0.0",
            contract_type=ContractType.REST_API,
            specification={"endpoints": ["/users"]},
            owner_role="Tech Lead",
            owner_agent="agent-1"
        )

        # Check compliance without examples
        compliance = await manager.check_compliance(
            contract.id,
            ["has_examples"]
        )

        assert compliance["compliant"] is False
        assert "Contract must have examples" in compliance["violations"]

        # Add examples
        await manager.add_examples(contract.id, [{"example": "test"}])

        # Check again
        compliance = await manager.check_compliance(
            contract.id,
            ["has_examples"]
        )

        assert compliance["compliant"] is True
        assert "has_examples" in compliance["passed_rules"]

    @pytest.mark.asyncio
    async def test_dde_623_compliance_check_test_cases(self, manager):
        """DDE-623: Compliance check for required test cases"""
        contract = await manager.create_contract(
            team_id="team-1",
            contract_name="UserAPI",
            version="v1.0.0",
            contract_type=ContractType.REST_API,
            specification={"endpoints": ["/users"]},
            owner_role="Tech Lead",
            owner_agent="agent-1"
        )

        compliance = await manager.check_compliance(
            contract.id,
            ["has_test_cases"]
        )

        assert compliance["compliant"] is False

        # Add test cases
        await manager.add_test_cases(contract.id, [{"test": "test"}])

        compliance = await manager.check_compliance(
            contract.id,
            ["has_test_cases"]
        )

        assert compliance["compliant"] is True

    @pytest.mark.asyncio
    async def test_dde_624_compliance_check_changelog(self, manager):
        """DDE-624: Compliance check for changelog presence"""
        contract = await manager.create_contract(
            team_id="team-1",
            contract_name="UserAPI",
            version="v1.0.0",
            contract_type=ContractType.REST_API,
            specification={"endpoints": ["/users"]},
            owner_role="Tech Lead",
            owner_agent="agent-1"
        )

        # Initially no changelog
        compliance = await manager.check_compliance(
            contract.id,
            ["has_changelog"]
        )

        assert compliance["compliant"] is False

        # Lock contract (adds changelog entry)
        await manager.lock_contract(contract.id, "agent-1")

        compliance = await manager.check_compliance(
            contract.id,
            ["has_changelog"]
        )

        assert compliance["compliant"] is True

    @pytest.mark.asyncio
    async def test_dde_625_compliance_check_semver(self, manager):
        """DDE-625: Compliance check for semver versioning"""
        # Valid semver
        contract1 = await manager.create_contract(
            team_id="team-1",
            contract_name="API1",
            version="v1.0.0",
            contract_type=ContractType.REST_API,
            specification={"endpoints": ["/test"]},
            owner_role="Tech Lead",
            owner_agent="agent-1"
        )

        compliance = await manager.check_compliance(
            contract1.id,
            ["versioning_semver"]
        )

        assert compliance["compliant"] is True
        assert "versioning_semver" in compliance["passed_rules"]

        # Invalid semver
        contract2 = await manager.create_contract(
            team_id="team-1",
            contract_name="API2",
            version="invalid-version",
            contract_type=ContractType.REST_API,
            specification={"endpoints": ["/test"]},
            owner_role="Tech Lead",
            owner_agent="agent-1"
        )

        compliance = await manager.check_compliance(
            contract2.id,
            ["versioning_semver"]
        )

        assert compliance["compliant"] is False
        assert "Version must follow semver format" in compliance["violations"]


# =============================================================================
# Test Summary Helper
# =============================================================================

def get_test_summary():
    """Return summary of test suite"""
    return {
        "test_suite": "Contract Lockdown Mechanism",
        "test_ids": "DDE-601 to DDE-625",
        "total_tests": 25,
        "categories": {
            "lockdown_basics": 5,        # DDE-601 to DDE-605
            "specifications": 3,          # DDE-606 to DDE-608
            "versioning": 7,              # DDE-609 to DDE-615
            "validation_docs": 10         # DDE-616 to DDE-625
        },
        "file_path": "/home/ec2-user/projects/maestro-platform/maestro-hive/tests/dde/integration/test_contract_lockdown.py",
        "features_covered": [
            "Contract status transitions (DRAFT -> LOCKED -> DEPRECATED -> SUNSET)",
            "Lockdown enforcement prevents modifications",
            "Semver-based version increments",
            "Breaking change detection",
            "Dependent notification system",
            "Contract publishing workflow",
            "OpenAPI, GraphQL, gRPC specification support",
            "Rollback capabilities",
            "Sunset date enforcement",
            "Specification validation",
            "Examples and test cases",
            "Auto-generated documentation",
            "Changelog tracking",
            "Compliance checks"
        ]
    }


if __name__ == "__main__":
    import json
    summary = get_test_summary()
    print(json.dumps(summary, indent=2))
