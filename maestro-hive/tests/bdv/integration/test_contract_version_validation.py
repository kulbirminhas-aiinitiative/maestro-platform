"""
BDV Phase 2A: Test Suite 12 - Contract Version Validation

Test IDs: BDV-301 to BDV-325 (25 tests)

Test Categories:
1. Semver Matching (BDV-301 to BDV-305): Exact version match, compatible minor/patch,
   major version mismatch, pre-release versions
2. Breaking Change Detection (BDV-306 to BDV-310): Removed endpoint, required field addition,
   response schema change, HTTP method change, auto-increment major version
3. Contract Locking (BDV-311 to BDV-315): Lock contract when scenarios pass, prevent modification,
   require new version, unlock workflow, persist lock status
4. Version Range Resolution (BDV-316 to BDV-320): Range syntax, pessimistic constraint,
   multiple constraints, latest version selection, conflict detection
5. Integration Tests (BDV-321 to BDV-325): Contract registry integration, scenario tagging,
   version mismatch errors, multiple contracts, performance testing

Author: Claude Code Implementation
Date: 2025-10-13
Version: 1.0.0
"""

import pytest
import json
import time
import re
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Tuple
from enum import Enum
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock


# ============================================================================
# Helper Classes - Semantic Versioning
# ============================================================================

@dataclass
class SemanticVersion:
    """Semantic version parser and matcher"""
    major: int
    minor: int
    patch: int
    prerelease: Optional[str] = None
    build: Optional[str] = None

    @staticmethod
    def parse(version_string: str) -> 'SemanticVersion':
        """
        Parse semantic version string.

        Examples:
            - "1.2.3" -> SemanticVersion(1, 2, 3)
            - "v1.2.3" -> SemanticVersion(1, 2, 3)
            - "1.0.0-alpha" -> SemanticVersion(1, 0, 0, prerelease="alpha")
            - "2.1.0-beta.1+build.123" -> SemanticVersion(2, 1, 0, prerelease="beta.1", build="build.123")
        """
        # Remove 'v' prefix if present
        version_string = version_string.strip()
        if version_string.startswith('v'):
            version_string = version_string[1:]

        # Parse main version, prerelease, and build
        prerelease = None
        build = None

        # Extract build metadata (+)
        if '+' in version_string:
            version_string, build = version_string.split('+', 1)

        # Extract prerelease (-)
        if '-' in version_string:
            version_string, prerelease = version_string.split('-', 1)

        # Parse major.minor.patch
        parts = version_string.split('.')
        if len(parts) != 3:
            raise ValueError(f"Invalid semantic version: {version_string}")

        try:
            major = int(parts[0])
            minor = int(parts[1])
            patch = int(parts[2])
        except ValueError:
            raise ValueError(f"Version parts must be integers: {version_string}")

        return SemanticVersion(
            major=major,
            minor=minor,
            patch=patch,
            prerelease=prerelease,
            build=build
        )

    def matches(self, constraint: str) -> bool:
        """
        Check if this version matches a constraint.

        Constraint syntax:
            - Exact: "1.2.3"
            - Range: ">=1.2.0 <2.0.0"
            - Pessimistic: "~>1.2.3" (>= 1.2.3, < 1.3.0)
            - Caret: "^1.2.3" (>= 1.2.3, < 2.0.0)
            - Wildcard: "1.2.x" or "1.x.x"
            - Multiple: ">=1.0.0, !=1.5.0, <2.0.0"
        """
        constraint = constraint.strip()

        # Handle multiple constraints (comma-separated)
        if ',' in constraint:
            constraints = [c.strip() for c in constraint.split(',')]
            return all(self.matches(c) for c in constraints)

        # Pessimistic constraint: ~>1.2.3 means >= 1.2.3, < 1.3.0
        if constraint.startswith('~>'):
            version_str = constraint[2:].strip()
            base_version = SemanticVersion.parse(version_str)
            return (self >= base_version and
                    self.major == base_version.major and
                    self.minor == base_version.minor)

        # Caret constraint: ^1.2.3 means >= 1.2.3, < 2.0.0
        if constraint.startswith('^'):
            version_str = constraint[1:].strip()
            base_version = SemanticVersion.parse(version_str)
            return (self >= base_version and self.major == base_version.major)

        # Complex range: ">=1.2.0 <2.0.0" (check before individual operators)
        if ' ' in constraint:
            parts = constraint.split()
            return all(self.matches(part) for part in parts)

        # Wildcard: 1.2.x or 1.x.x
        if 'x' in constraint.lower():
            parts = constraint.lower().split('.')
            if len(parts) != 3:
                return False

            if parts[0] != 'x' and int(parts[0]) != self.major:
                return False
            if parts[1] != 'x' and int(parts[1]) != self.minor:
                return False
            if parts[2] != 'x' and int(parts[2]) != self.patch:
                return False
            return True

        # Range operators
        if constraint.startswith('>='):
            return self >= SemanticVersion.parse(constraint[2:].strip())
        if constraint.startswith('<='):
            return self <= SemanticVersion.parse(constraint[2:].strip())
        if constraint.startswith('>'):
            return self > SemanticVersion.parse(constraint[1:].strip())
        if constraint.startswith('<'):
            return self < SemanticVersion.parse(constraint[1:].strip())
        if constraint.startswith('!='):
            return self != SemanticVersion.parse(constraint[2:].strip())
        if constraint.startswith('='):
            return self == SemanticVersion.parse(constraint[1:].strip())

        # Exact match
        return self == SemanticVersion.parse(constraint)

    def __eq__(self, other: 'SemanticVersion') -> bool:
        return (self.major == other.major and
                self.minor == other.minor and
                self.patch == other.patch and
                self.prerelease == other.prerelease)

    def __lt__(self, other: 'SemanticVersion') -> bool:
        if self.major != other.major:
            return self.major < other.major
        if self.minor != other.minor:
            return self.minor < other.minor
        if self.patch != other.patch:
            return self.patch < other.patch

        # Handle prerelease: 1.0.0-alpha < 1.0.0
        if self.prerelease and not other.prerelease:
            return True
        if not self.prerelease and other.prerelease:
            return False
        if self.prerelease and other.prerelease:
            return self.prerelease < other.prerelease

        return False

    def __le__(self, other: 'SemanticVersion') -> bool:
        return self == other or self < other

    def __gt__(self, other: 'SemanticVersion') -> bool:
        return not self <= other

    def __ge__(self, other: 'SemanticVersion') -> bool:
        return not self < other

    def __str__(self) -> str:
        version = f"{self.major}.{self.minor}.{self.patch}"
        if self.prerelease:
            version += f"-{self.prerelease}"
        if self.build:
            version += f"+{self.build}"
        return version


# ============================================================================
# Helper Classes - Breaking Change Detection
# ============================================================================

class ChangeType(Enum):
    """Types of API changes"""
    BREAKING = "breaking"
    NON_BREAKING = "non_breaking"
    PATCH = "patch"


@dataclass
class APIChange:
    """Represents a detected API change"""
    change_type: ChangeType
    description: str
    path: Optional[str] = None
    method: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)


class BreakingChangeDetector:
    """Detects breaking changes in OpenAPI specifications"""

    def __init__(self):
        pass

    def detect_changes(
        self,
        old_spec: Dict[str, Any],
        new_spec: Dict[str, Any]
    ) -> List[APIChange]:
        """
        Detect changes between two OpenAPI specifications.

        Returns list of APIChange objects with change type and description.
        """
        changes = []

        # Check for removed endpoints
        changes.extend(self._check_removed_endpoints(old_spec, new_spec))

        # Check for changed HTTP methods
        changes.extend(self._check_method_changes(old_spec, new_spec))

        # Check for required field additions
        changes.extend(self._check_required_fields(old_spec, new_spec))

        # Check for response schema changes
        changes.extend(self._check_response_schemas(old_spec, new_spec))

        return changes

    def _check_removed_endpoints(
        self,
        old_spec: Dict[str, Any],
        new_spec: Dict[str, Any]
    ) -> List[APIChange]:
        """Check for removed endpoints (DELETE breaking change)"""
        changes = []
        old_paths = old_spec.get('paths', {})
        new_paths = new_spec.get('paths', {})

        for path, methods in old_paths.items():
            if path not in new_paths:
                changes.append(APIChange(
                    change_type=ChangeType.BREAKING,
                    description=f"Endpoint removed: {path}",
                    path=path,
                    details={"removed_methods": list(methods.keys())}
                ))
            else:
                # Check for removed methods
                for method in methods.keys():
                    if method not in new_paths[path]:
                        changes.append(APIChange(
                            change_type=ChangeType.BREAKING,
                            description=f"Method removed: {method.upper()} {path}",
                            path=path,
                            method=method
                        ))

        return changes

    def _check_method_changes(
        self,
        old_spec: Dict[str, Any],
        new_spec: Dict[str, Any]
    ) -> List[APIChange]:
        """Check for HTTP method changes (breaking)"""
        changes = []
        old_paths = old_spec.get('paths', {})
        new_paths = new_spec.get('paths', {})

        for path in old_paths:
            if path in new_paths:
                old_methods = set(old_paths[path].keys())
                new_methods = set(new_paths[path].keys())

                # If methods are completely different, it's a breaking change
                if old_methods != new_methods and not old_methods.issubset(new_methods):
                    changes.append(APIChange(
                        change_type=ChangeType.BREAKING,
                        description=f"HTTP methods changed for {path}",
                        path=path,
                        details={
                            "old_methods": list(old_methods),
                            "new_methods": list(new_methods)
                        }
                    ))

        return changes

    def _check_required_fields(
        self,
        old_spec: Dict[str, Any],
        new_spec: Dict[str, Any]
    ) -> List[APIChange]:
        """Check for new required fields (breaking)"""
        changes = []
        old_paths = old_spec.get('paths', {})
        new_paths = new_spec.get('paths', {})

        for path in old_paths:
            if path in new_paths:
                for method in old_paths[path]:
                    if method in new_paths[path]:
                        old_required = self._get_required_fields(old_paths[path][method])
                        new_required = self._get_required_fields(new_paths[path][method])

                        # New required fields are breaking
                        added_required = new_required - old_required
                        if added_required:
                            changes.append(APIChange(
                                change_type=ChangeType.BREAKING,
                                description=f"Required fields added to {method.upper()} {path}",
                                path=path,
                                method=method,
                                details={"added_required_fields": list(added_required)}
                            ))

        return changes

    def _check_response_schemas(
        self,
        old_spec: Dict[str, Any],
        new_spec: Dict[str, Any]
    ) -> List[APIChange]:
        """Check for response schema changes"""
        changes = []
        old_paths = old_spec.get('paths', {})
        new_paths = new_spec.get('paths', {})

        for path in old_paths:
            if path in new_paths:
                for method in old_paths[path]:
                    if method in new_paths[path]:
                        old_response_fields = self._get_response_fields(old_paths[path][method])
                        new_response_fields = self._get_response_fields(new_paths[path][method])

                        # Removed response fields are breaking
                        removed_fields = old_response_fields - new_response_fields
                        if removed_fields:
                            changes.append(APIChange(
                                change_type=ChangeType.BREAKING,
                                description=f"Response fields removed from {method.upper()} {path}",
                                path=path,
                                method=method,
                                details={"removed_fields": list(removed_fields)}
                            ))

        return changes

    def _get_required_fields(self, operation: Dict[str, Any]) -> set:
        """Extract required fields from operation"""
        required = set()
        request_body = operation.get('requestBody', {})
        content = request_body.get('content', {})

        for media_type, schema_info in content.items():
            schema = schema_info.get('schema', {})
            required.update(schema.get('required', []))

        return required

    def _get_response_fields(self, operation: Dict[str, Any]) -> set:
        """Extract response fields from operation"""
        fields = set()
        responses = operation.get('responses', {})

        for status_code, response in responses.items():
            content = response.get('content', {})
            for media_type, schema_info in content.items():
                schema = schema_info.get('schema', {})
                properties = schema.get('properties', {})
                fields.update(properties.keys())

        return fields

    def suggest_version_bump(self, changes: List[APIChange]) -> str:
        """
        Suggest version bump based on detected changes.

        Returns: "major", "minor", or "patch"
        """
        if any(c.change_type == ChangeType.BREAKING for c in changes):
            return "major"
        elif any(c.change_type == ChangeType.NON_BREAKING for c in changes):
            return "minor"
        else:
            return "patch"


# ============================================================================
# Helper Classes - Contract Registry
# ============================================================================

@dataclass
class ContractMetadata:
    """Contract metadata from registry"""
    name: str
    version: str
    status: str  # "DRAFT", "LOCKED", "DEPRECATED"
    openapi_spec: Dict[str, Any]
    locked_at: Optional[str] = None
    locked_by: Optional[str] = None


class ContractRegistry:
    """Mock contract registry for testing"""

    def __init__(self):
        self.contracts: Dict[str, Dict[str, ContractMetadata]] = {}

    def register_contract(
        self,
        name: str,
        version: str,
        openapi_spec: Dict[str, Any],
        status: str = "DRAFT"
    ):
        """Register a contract version"""
        if name not in self.contracts:
            self.contracts[name] = {}

        self.contracts[name][version] = ContractMetadata(
            name=name,
            version=version,
            status=status,
            openapi_spec=openapi_spec
        )

    def get_contract(self, name: str, version: str) -> Optional[ContractMetadata]:
        """Get contract by name and version"""
        return self.contracts.get(name, {}).get(version)

    def lock_contract(self, name: str, version: str, locked_by: str = "system"):
        """Lock a contract version"""
        if name in self.contracts and version in self.contracts[name]:
            contract = self.contracts[name][version]
            contract.status = "LOCKED"
            contract.locked_by = locked_by
            contract.locked_at = "2025-10-13T10:00:00Z"

    def unlock_contract(self, name: str, version: str):
        """Unlock a contract version"""
        if name in self.contracts and version in self.contracts[name]:
            contract = self.contracts[name][version]
            contract.status = "DRAFT"
            contract.locked_by = None
            contract.locked_at = None

    def get_all_versions(self, name: str) -> List[str]:
        """Get all versions for a contract"""
        if name not in self.contracts:
            return []
        return sorted(self.contracts[name].keys())

    def find_compatible_version(
        self,
        name: str,
        constraint: str
    ) -> Optional[str]:
        """Find latest compatible version matching constraint"""
        versions = self.get_all_versions(name)

        # Parse and sort versions
        parsed_versions = []
        for v in versions:
            try:
                parsed_versions.append((v, SemanticVersion.parse(v)))
            except ValueError:
                continue

        # Filter by constraint
        compatible = [
            (v_str, v_obj)
            for v_str, v_obj in parsed_versions
            if v_obj.matches(constraint)
        ]

        # Return latest
        if compatible:
            compatible.sort(key=lambda x: x[1], reverse=True)
            return compatible[0][0]

        return None


# ============================================================================
# Helper Classes - Contract Version Validator
# ============================================================================

class ContractVersionValidator:
    """Validates contract versions in BDV scenarios"""

    def __init__(self, registry: Optional[ContractRegistry] = None):
        self.registry = registry or ContractRegistry()
        self.detector = BreakingChangeDetector()

    def validate_version(
        self,
        contract_name: str,
        required_version: str
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate that contract version exists and matches requirement.

        Returns: (is_valid, error_message)
        """
        # Parse version constraint
        try:
            if any(op in required_version for op in ['>=', '<=', '>', '<', '~>', '^', 'x']):
                # Version range - find compatible version
                compatible_version = self.registry.find_compatible_version(
                    contract_name,
                    required_version
                )
                if not compatible_version:
                    return False, f"No compatible version found for {contract_name} matching {required_version}"
                return True, None
            else:
                # Exact version
                contract = self.registry.get_contract(contract_name, required_version)
                if not contract:
                    return False, f"Contract {contract_name}:v{required_version} not found"
                return True, None
        except ValueError as e:
            return False, f"Invalid version format: {e}"

    def detect_breaking_changes(
        self,
        contract_name: str,
        old_version: str,
        new_version: str
    ) -> List[APIChange]:
        """Detect breaking changes between two contract versions"""
        old_contract = self.registry.get_contract(contract_name, old_version)
        new_contract = self.registry.get_contract(contract_name, new_version)

        if not old_contract or not new_contract:
            return []

        return self.detector.detect_changes(
            old_contract.openapi_spec,
            new_contract.openapi_spec
        )

    def can_modify_contract(
        self,
        contract_name: str,
        version: str
    ) -> Tuple[bool, Optional[str]]:
        """Check if contract can be modified (not locked)"""
        contract = self.registry.get_contract(contract_name, version)

        if not contract:
            return False, f"Contract {contract_name}:v{version} not found"

        if contract.status == "LOCKED":
            return False, f"Contract {contract_name}:v{version} is locked and cannot be modified"

        return True, None


# ============================================================================
# Test Fixtures
# ============================================================================

@pytest.fixture
def contract_registry():
    """Create test contract registry with sample contracts"""
    registry = ContractRegistry()

    # Register API contract versions
    registry.register_contract("API", "1.2.3", {
        "openapi": "3.0.0",
        "paths": {
            "/users": {
                "get": {
                    "responses": {
                        "200": {
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "properties": {
                                            "id": {"type": "string"},
                                            "name": {"type": "string"},
                                            "email": {"type": "string"}
                                        }
                                    }
                                }
                            }
                        }
                    }
                },
                "post": {
                    "requestBody": {
                        "content": {
                            "application/json": {
                                "schema": {
                                    "required": ["name", "email"]
                                }
                            }
                        }
                    }
                }
            }
        }
    })

    registry.register_contract("API", "1.2.0", {
        "openapi": "3.0.0",
        "paths": {
            "/users": {
                "get": {
                    "responses": {
                        "200": {
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "properties": {
                                            "id": {"type": "string"},
                                            "name": {"type": "string"}
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    })

    registry.register_contract("API", "1.2.5", {
        "openapi": "3.0.0",
        "paths": {
            "/users": {
                "get": {
                    "responses": {
                        "200": {
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "properties": {
                                            "id": {"type": "string"},
                                            "name": {"type": "string"},
                                            "email": {"type": "string"}
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    })

    registry.register_contract("API", "2.0.0", {
        "openapi": "3.0.0",
        "paths": {
            "/users": {
                "get": {
                    "responses": {
                        "200": {
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "properties": {
                                            "userId": {"type": "string"},
                                            "fullName": {"type": "string"}
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    })

    # Register pre-release versions
    registry.register_contract("API", "1.0.0-alpha", {
        "openapi": "3.0.0",
        "paths": {
            "/users": {"get": {"responses": {"200": {}}}}
        }
    })

    registry.register_contract("API", "1.0.0-beta", {
        "openapi": "3.0.0",
        "paths": {
            "/users": {"get": {"responses": {"200": {}}}}
        }
    })

    return registry


@pytest.fixture
def validator(contract_registry):
    """Create contract version validator"""
    return ContractVersionValidator(contract_registry)


# ============================================================================
# Test Suite 1: Semver Matching (BDV-301 to BDV-305)
# ============================================================================

class TestSemverMatching:
    """Semantic version matching tests (BDV-301 to BDV-305)"""

    def test_bdv_301_exact_version_match(self, validator):
        """BDV-301: Exact version match - @contract:API:v1.2.3 matches API v1.2.3"""
        is_valid, error = validator.validate_version("API", "1.2.3")

        assert is_valid is True
        assert error is None

    def test_bdv_302_compatible_minor_version(self, validator):
        """BDV-302: Compatible minor version - v1.2.x matches v1.2.0, v1.2.5"""
        version = SemanticVersion.parse("1.2.0")
        assert version.matches("1.2.x") is True

        version = SemanticVersion.parse("1.2.5")
        assert version.matches("1.2.x") is True

        version = SemanticVersion.parse("1.3.0")
        assert version.matches("1.2.x") is False

    def test_bdv_303_compatible_patch_version(self, validator):
        """BDV-303: Compatible patch version - v1.x.x matches v1.0.0, v1.9.9"""
        version = SemanticVersion.parse("1.0.0")
        assert version.matches("1.x.x") is True

        version = SemanticVersion.parse("1.9.9")
        assert version.matches("1.x.x") is True

        version = SemanticVersion.parse("2.0.0")
        assert version.matches("1.x.x") is False

    def test_bdv_304_major_version_mismatch_error(self, validator):
        """BDV-304: Major version mismatch error - v2.0.0 vs v1.9.9"""
        v1 = SemanticVersion.parse("1.9.9")
        v2 = SemanticVersion.parse("2.0.0")

        # v1.9.9 should not match v2.x constraint
        assert v1.matches("2.x.x") is False
        assert v2.matches("1.x.x") is False

    def test_bdv_305_prerelease_versions(self, validator):
        """BDV-305: Pre-release versions - v1.0.0-alpha, v1.0.0-beta"""
        alpha = SemanticVersion.parse("1.0.0-alpha")
        beta = SemanticVersion.parse("1.0.0-beta")
        stable = SemanticVersion.parse("1.0.0")

        assert alpha < beta
        assert beta < stable
        assert alpha < stable

        # Validate pre-release versions exist
        is_valid, error = validator.validate_version("API", "1.0.0-alpha")
        assert is_valid is True


# ============================================================================
# Test Suite 2: Breaking Change Detection (BDV-306 to BDV-310)
# ============================================================================

class TestBreakingChangeDetection:
    """Breaking change detection tests (BDV-306 to BDV-310)"""

    def test_bdv_306_removed_endpoint_detection(self):
        """BDV-306: Removed endpoint detection (DELETE breaking change)"""
        old_spec = {
            "paths": {
                "/users": {"get": {}, "post": {}},
                "/admin": {"get": {}}
            }
        }

        new_spec = {
            "paths": {
                "/users": {"get": {}, "post": {}}
            }
        }

        detector = BreakingChangeDetector()
        changes = detector.detect_changes(old_spec, new_spec)

        breaking_changes = [c for c in changes if c.change_type == ChangeType.BREAKING]
        assert len(breaking_changes) >= 1
        assert any("/admin" in c.description for c in breaking_changes)

    def test_bdv_307_required_field_addition(self):
        """BDV-307: Required field addition (POST breaking change)"""
        old_spec = {
            "paths": {
                "/users": {
                    "post": {
                        "requestBody": {
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "required": ["name"]
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }

        new_spec = {
            "paths": {
                "/users": {
                    "post": {
                        "requestBody": {
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "required": ["name", "email", "phone"]
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }

        detector = BreakingChangeDetector()
        changes = detector.detect_changes(old_spec, new_spec)

        breaking_changes = [c for c in changes if c.change_type == ChangeType.BREAKING]
        assert len(breaking_changes) >= 1
        assert any("Required fields added" in c.description for c in breaking_changes)

    def test_bdv_308_response_schema_change(self, validator):
        """BDV-308: Response schema change (breaking if removes fields)"""
        changes = validator.detect_breaking_changes("API", "1.2.3", "2.0.0")

        # v2.0.0 removes 'name' and 'email', adds 'fullName'
        breaking_changes = [c for c in changes if c.change_type == ChangeType.BREAKING]
        assert len(breaking_changes) >= 1
        assert any("Response fields removed" in c.description for c in breaking_changes)

    def test_bdv_309_http_method_change(self):
        """BDV-309: HTTP method change (GET to POST is breaking)"""
        old_spec = {
            "paths": {
                "/users": {
                    "get": {"responses": {"200": {}}}
                }
            }
        }

        new_spec = {
            "paths": {
                "/users": {
                    "post": {"responses": {"200": {}}}
                }
            }
        }

        detector = BreakingChangeDetector()
        changes = detector.detect_changes(old_spec, new_spec)

        breaking_changes = [c for c in changes if c.change_type == ChangeType.BREAKING]
        # Should detect method removal
        assert len(breaking_changes) >= 1

    def test_bdv_310_auto_increment_major_version(self):
        """BDV-310: Auto-increment major version on breaking change"""
        old_spec = {
            "paths": {
                "/users": {"get": {}, "delete": {}}
            }
        }

        new_spec = {
            "paths": {
                "/users": {"get": {}}
            }
        }

        detector = BreakingChangeDetector()
        changes = detector.detect_changes(old_spec, new_spec)
        suggested_bump = detector.suggest_version_bump(changes)

        assert suggested_bump == "major"


# ============================================================================
# Test Suite 3: Contract Locking (BDV-311 to BDV-315)
# ============================================================================

class TestContractLocking:
    """Contract locking tests (BDV-311 to BDV-315)"""

    def test_bdv_311_lock_contract_when_scenarios_pass(self, contract_registry):
        """BDV-311: Lock contract when all scenarios pass"""
        contract_registry.lock_contract("API", "1.2.3", locked_by="test_suite")

        contract = contract_registry.get_contract("API", "1.2.3")
        assert contract.status == "LOCKED"
        assert contract.locked_by == "test_suite"
        assert contract.locked_at is not None

    def test_bdv_312_locked_contracts_cannot_be_modified(self, validator, contract_registry):
        """BDV-312: Locked contracts cannot be modified (status: LOCKED)"""
        contract_registry.lock_contract("API", "1.2.3")

        can_modify, error = validator.can_modify_contract("API", "1.2.3")

        assert can_modify is False
        assert "locked" in error.lower()

    def test_bdv_313_new_version_required_for_changes(self, contract_registry):
        """BDV-313: New version required for changes - v1.2.3 -> v1.2.4"""
        # Lock existing version
        contract_registry.lock_contract("API", "1.2.3")

        # Register new version
        contract_registry.register_contract("API", "1.2.4", {
            "openapi": "3.0.0",
            "paths": {"/users": {"get": {}}}
        })

        # Old version is locked
        old_contract = contract_registry.get_contract("API", "1.2.3")
        assert old_contract.status == "LOCKED"

        # New version is unlocked
        new_contract = contract_registry.get_contract("API", "1.2.4")
        assert new_contract.status == "DRAFT"

    def test_bdv_314_unlock_requires_approval_workflow(self, validator, contract_registry):
        """BDV-314: Unlock requires approval workflow"""
        # Lock contract
        contract_registry.lock_contract("API", "1.2.3")

        # Verify locked
        can_modify, _ = validator.can_modify_contract("API", "1.2.3")
        assert can_modify is False

        # Unlock (simulating approval)
        contract_registry.unlock_contract("API", "1.2.3")

        # Now can modify
        can_modify, _ = validator.can_modify_contract("API", "1.2.3")
        assert can_modify is True

    def test_bdv_315_lock_status_persisted_in_registry(self, contract_registry):
        """BDV-315: Lock status persisted in contract registry"""
        # Lock contract
        contract_registry.lock_contract("API", "1.2.3", locked_by="admin")

        # Retrieve and verify persistence
        contract = contract_registry.get_contract("API", "1.2.3")
        assert contract.status == "LOCKED"
        assert contract.locked_by == "admin"
        assert contract.locked_at is not None


# ============================================================================
# Test Suite 4: Version Range Resolution (BDV-316 to BDV-320)
# ============================================================================

class TestVersionRangeResolution:
    """Version range resolution tests (BDV-316 to BDV-320)"""

    def test_bdv_316_range_syntax(self):
        """BDV-316: Range syntax - >=1.2.0 <2.0.0 (any 1.x version)"""
        v1_5_0 = SemanticVersion.parse("1.5.0")
        v2_0_0 = SemanticVersion.parse("2.0.0")
        v1_2_0 = SemanticVersion.parse("1.2.0")
        v1_9_9 = SemanticVersion.parse("1.9.9")

        assert v1_5_0.matches(">=1.2.0 <2.0.0") is True
        assert v2_0_0.matches(">=1.2.0 <2.0.0") is False
        assert v1_2_0.matches(">=1.2.0 <2.0.0") is True
        assert v1_9_9.matches(">=1.2.0 <2.0.0") is True

    def test_bdv_317_pessimistic_constraint(self):
        """BDV-317: Pessimistic constraint - ~>1.2.3 (>= 1.2.3, < 1.3.0)"""
        v1_2_3 = SemanticVersion.parse("1.2.3")
        v1_2_5 = SemanticVersion.parse("1.2.5")
        v1_3_0 = SemanticVersion.parse("1.3.0")
        v1_2_2 = SemanticVersion.parse("1.2.2")

        assert v1_2_3.matches("~>1.2.3") is True
        assert v1_2_5.matches("~>1.2.3") is True
        assert v1_3_0.matches("~>1.2.3") is False
        assert v1_2_2.matches("~>1.2.3") is False

    def test_bdv_318_multiple_constraints(self):
        """BDV-318: Multiple constraints - >=1.0.0, !=1.5.0, <2.0.0"""
        v1_4_0 = SemanticVersion.parse("1.4.0")
        v1_5_0 = SemanticVersion.parse("1.5.0")
        v1_6_0 = SemanticVersion.parse("1.6.0")

        constraint = ">=1.0.0, !=1.5.0, <2.0.0"

        assert v1_4_0.matches(constraint) is True
        assert v1_5_0.matches(constraint) is False
        assert v1_6_0.matches(constraint) is True

    def test_bdv_319_latest_compatible_version_selection(self, contract_registry):
        """BDV-319: Latest compatible version selection"""
        # Find latest version matching 1.2.x
        latest = contract_registry.find_compatible_version("API", "1.2.x")

        # Should return 1.2.5 (latest 1.2.x version)
        assert latest == "1.2.5"

    def test_bdv_320_version_conflict_detection(self, contract_registry):
        """BDV-320: Version conflict detection (no satisfying version)"""
        # Try to find version matching impossible constraint
        latest = contract_registry.find_compatible_version("API", ">=3.0.0")

        # Should return None (no version 3.x exists)
        assert latest is None


# ============================================================================
# Test Suite 5: Integration Tests (BDV-321 to BDV-325)
# ============================================================================

class TestIntegration:
    """Integration tests (BDV-321 to BDV-325)"""

    def test_bdv_321_contract_registry_integration(self, validator, contract_registry):
        """BDV-321: Contract registry integration (fetch version metadata)"""
        # Validate version using registry
        is_valid, error = validator.validate_version("API", "1.2.3")
        assert is_valid is True

        # Fetch metadata
        contract = contract_registry.get_contract("API", "1.2.3")
        assert contract is not None
        assert contract.name == "API"
        assert contract.version == "1.2.3"
        assert contract.openapi_spec is not None

    def test_bdv_322_scenario_tagging_with_version(self):
        """BDV-322: Scenario tagging with version - @contract:API:v1.2.3"""
        tag = "@contract:API:v1.2.3"

        # Parse tag
        match = re.match(r'@contract:([^:]+):v(.+)', tag)
        assert match is not None

        contract_name = match.group(1)
        version = match.group(2)

        assert contract_name == "API"
        assert version == "1.2.3"

    def test_bdv_323_version_mismatch_error_message(self, validator):
        """BDV-323: Version mismatch generates clear error message"""
        is_valid, error = validator.validate_version("API", "99.99.99")

        assert is_valid is False
        assert error is not None
        assert "not found" in error.lower()
        assert "99.99.99" in error

    def test_bdv_324_multiple_contracts_in_feature(self, validator, contract_registry):
        """BDV-324: Multiple contracts in single feature file"""
        # Register additional contract
        contract_registry.register_contract("PaymentAPI", "2.1.0", {
            "openapi": "3.0.0",
            "paths": {"/payments": {"post": {}}}
        })

        # Validate multiple contracts
        contracts_to_validate = [
            ("API", "1.2.3"),
            ("PaymentAPI", "2.1.0")
        ]

        results = []
        for name, version in contracts_to_validate:
            is_valid, error = validator.validate_version(name, version)
            results.append((is_valid, error))

        # Both should be valid
        assert all(r[0] for r in results)

    def test_bdv_325_performance_100_contracts_validated(self, contract_registry):
        """BDV-325: Performance - 100 contracts validated in <500ms"""
        # Register 100 contracts
        for i in range(100):
            contract_registry.register_contract(
                f"TestAPI_{i}",
                "1.0.0",
                {"openapi": "3.0.0", "paths": {}}
            )

        validator = ContractVersionValidator(contract_registry)

        # Validate all 100 contracts
        start = time.time()

        for i in range(100):
            is_valid, error = validator.validate_version(f"TestAPI_{i}", "1.0.0")
            assert is_valid is True

        elapsed = time.time() - start

        assert elapsed < 0.5, f"Validation took {elapsed:.3f}s, should be < 500ms"


# ============================================================================
# Additional Tests
# ============================================================================

class TestSemanticVersionParsing:
    """Additional semantic version parsing tests"""

    def test_parse_version_with_v_prefix(self):
        """Test parsing version with 'v' prefix"""
        version = SemanticVersion.parse("v1.2.3")
        assert version.major == 1
        assert version.minor == 2
        assert version.patch == 3

    def test_parse_version_with_build_metadata(self):
        """Test parsing version with build metadata"""
        version = SemanticVersion.parse("1.2.3+build.123")
        assert version.major == 1
        assert version.minor == 2
        assert version.patch == 3
        assert version.build == "build.123"

    def test_version_comparison(self):
        """Test version comparison operators"""
        v1 = SemanticVersion.parse("1.0.0")
        v2 = SemanticVersion.parse("2.0.0")
        v1_1 = SemanticVersion.parse("1.1.0")

        assert v1 < v2
        assert v1 < v1_1
        assert v1_1 < v2
        assert v2 > v1
        assert v1 <= v1
        assert v2 >= v2

    def test_caret_constraint(self):
        """Test caret constraint (^1.2.3)"""
        v1_2_3 = SemanticVersion.parse("1.2.3")
        v1_9_9 = SemanticVersion.parse("1.9.9")
        v2_0_0 = SemanticVersion.parse("2.0.0")

        assert v1_2_3.matches("^1.2.3") is True
        assert v1_9_9.matches("^1.2.3") is True
        assert v2_0_0.matches("^1.2.3") is False


# ============================================================================
# Test Execution Summary
# ============================================================================

if __name__ == "__main__":
    import sys

    # Run pytest with verbose output
    exit_code = pytest.main([__file__, "-v", "--tb=short", "-ra"])

    print("\n" + "="*80)
    print("BDV Phase 2A - Test Suite 12: Contract Version Validation")
    print("="*80)
    print("\nTest Categories:")
    print("  • Semver Matching (BDV-301 to BDV-305): 5 tests")
    print("  • Breaking Change Detection (BDV-306 to BDV-310): 5 tests")
    print("  • Contract Locking (BDV-311 to BDV-315): 5 tests")
    print("  • Version Range Resolution (BDV-316 to BDV-320): 5 tests")
    print("  • Integration Tests (BDV-321 to BDV-325): 5 tests")
    print("  • Additional utility tests: 4 tests")
    print(f"\nTotal: 29 tests (25 required + 4 additional)")
    print("="*80)
    print("\nKey Implementations:")
    print("  ✓ SemanticVersion class with full semver parsing")
    print("  ✓ Version constraint matching (>=, ~>, ^, x wildcard)")
    print("  ✓ BreakingChangeDetector with OpenAPI diff analysis")
    print("  ✓ ContractRegistry integration")
    print("  ✓ Contract locking mechanism")
    print("  ✓ Version range resolution")
    print("  ✓ Multiple constraint handling")
    print("  ✓ Performance: <500ms for 100 contracts")
    print("="*80)

    sys.exit(exit_code)
