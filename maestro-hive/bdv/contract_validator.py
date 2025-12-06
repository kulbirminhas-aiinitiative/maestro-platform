"""
Contract Version Validator (MD-2095)

Validates contract versions in BDV feature files against expected versions.
Detects breaking changes and version mismatches.

Features:
- Semantic version parsing and comparison
- Breaking change detection
- Version mismatch severity levels
- Blocking on major version conflicts
"""

import re
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
import hashlib

logger = logging.getLogger(__name__)


class VersionSeverity(str, Enum):
    """Severity levels for version mismatches"""
    COMPATIBLE = "compatible"  # Minor/patch differences
    WARNING = "warning"  # Minor version difference
    BREAKING = "breaking"  # Major version difference
    CRITICAL = "critical"  # Missing or invalid version


@dataclass
class SemanticVersion:
    """Represents a semantic version (major.minor.patch)"""
    major: int
    minor: int
    patch: int = 0

    @classmethod
    def parse(cls, version_str: str) -> Optional['SemanticVersion']:
        """
        Parse a version string into SemanticVersion.

        Args:
            version_str: Version string (e.g., "1.2.3", "v1.2", "1.0")

        Returns:
            SemanticVersion or None if parsing fails
        """
        # Remove 'v' prefix if present
        version_str = version_str.lstrip('v')

        # Match various version formats
        match = re.match(r'^(\d+)(?:\.(\d+))?(?:\.(\d+))?', version_str)
        if not match:
            return None

        major = int(match.group(1))
        minor = int(match.group(2)) if match.group(2) else 0
        patch = int(match.group(3)) if match.group(3) else 0

        return cls(major=major, minor=minor, patch=patch)

    def __str__(self) -> str:
        return f"{self.major}.{self.minor}.{self.patch}"

    def __eq__(self, other: 'SemanticVersion') -> bool:
        if not isinstance(other, SemanticVersion):
            return False
        return (self.major == other.major and
                self.minor == other.minor and
                self.patch == other.patch)

    def __lt__(self, other: 'SemanticVersion') -> bool:
        if self.major != other.major:
            return self.major < other.major
        if self.minor != other.minor:
            return self.minor < other.minor
        return self.patch < other.patch

    def is_compatible_with(self, other: 'SemanticVersion') -> Tuple[bool, VersionSeverity]:
        """
        Check compatibility with another version.

        Args:
            other: Version to compare against

        Returns:
            Tuple of (is_compatible, severity)
        """
        if self.major != other.major:
            return False, VersionSeverity.BREAKING
        if self.minor != other.minor:
            return True, VersionSeverity.WARNING
        return True, VersionSeverity.COMPATIBLE


@dataclass
class ContractVersion:
    """Represents a versioned contract"""
    contract_id: str
    contract_name: str
    version: SemanticVersion
    schema_hash: str
    created_at: datetime = field(default_factory=datetime.now)
    breaking_changes: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'contract_id': self.contract_id,
            'contract_name': self.contract_name,
            'version': str(self.version),
            'schema_hash': self.schema_hash,
            'created_at': self.created_at.isoformat(),
            'breaking_changes': self.breaking_changes,
            'metadata': self.metadata
        }


@dataclass
class VersionMismatch:
    """Represents a version mismatch"""
    contract_id: str
    expected_version: Optional[SemanticVersion]
    actual_version: Optional[SemanticVersion]
    severity: VersionSeverity
    message: str
    feature_file: str

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'contract_id': self.contract_id,
            'expected_version': str(self.expected_version) if self.expected_version else None,
            'actual_version': str(self.actual_version) if self.actual_version else None,
            'severity': self.severity.value,
            'message': self.message,
            'feature_file': self.feature_file
        }


@dataclass
class ValidationResult:
    """Result of contract version validation"""
    is_valid: bool
    total_contracts: int
    valid_contracts: int
    mismatches: List[VersionMismatch]
    blocking_errors: List[str]
    warnings: List[str]
    validated_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'is_valid': self.is_valid,
            'total_contracts': self.total_contracts,
            'valid_contracts': self.valid_contracts,
            'mismatches': [m.to_dict() for m in self.mismatches],
            'blocking_errors': self.blocking_errors,
            'warnings': self.warnings,
            'validated_at': self.validated_at.isoformat()
        }


class ContractVersionValidator:
    """
    Validates contract versions in BDV feature files.

    Supports:
    - Extracting contract versions from feature file tags
    - Comparing against expected versions
    - Detecting breaking changes
    - Blocking test execution on major version conflicts
    """

    # Regex pattern for contract tags: @contract:ContractName:v1.2.3
    CONTRACT_TAG_PATTERN = re.compile(
        r'@contract:(\w+):v?([\d]+(?:\.[\d]+)*)'
    )

    def __init__(
        self,
        expected_versions: Optional[Dict[str, str]] = None,
        block_on_breaking: bool = True,
        warn_on_minor: bool = True
    ):
        """
        Initialize validator.

        Args:
            expected_versions: Dict mapping contract_id to expected version string
            block_on_breaking: Whether to block on major version mismatches
            warn_on_minor: Whether to warn on minor version differences
        """
        self._expected_versions: Dict[str, SemanticVersion] = {}
        self.block_on_breaking = block_on_breaking
        self.warn_on_minor = warn_on_minor

        # Parse expected versions
        if expected_versions:
            for contract_id, version_str in expected_versions.items():
                version = SemanticVersion.parse(version_str)
                if version:
                    self._expected_versions[contract_id] = version

        logger.info(f"ContractVersionValidator initialized with {len(self._expected_versions)} expected versions")

    def register_expected_version(self, contract_id: str, version: str):
        """
        Register an expected version for a contract.

        Args:
            contract_id: Contract identifier
            version: Expected version string
        """
        parsed = SemanticVersion.parse(version)
        if parsed:
            self._expected_versions[contract_id] = parsed
            logger.debug(f"Registered expected version: {contract_id} -> {parsed}")

    def extract_contract_versions(self, feature_file: Path) -> List[ContractVersion]:
        """
        Extract contract versions from a feature file.

        Args:
            feature_file: Path to feature file

        Returns:
            List of ContractVersion objects found in the file
        """
        contracts = []

        try:
            content = feature_file.read_text()

            # Find all contract tags
            for match in self.CONTRACT_TAG_PATTERN.finditer(content):
                contract_name = match.group(1)
                version_str = match.group(2)
                version = SemanticVersion.parse(version_str)

                if version:
                    # Generate schema hash from contract name and surrounding content
                    schema_hash = self._compute_schema_hash(content, contract_name)

                    contract = ContractVersion(
                        contract_id=contract_name.lower(),
                        contract_name=contract_name,
                        version=version,
                        schema_hash=schema_hash,
                        metadata={'source_file': str(feature_file)}
                    )
                    contracts.append(contract)

        except Exception as e:
            logger.error(f"Error extracting versions from {feature_file}: {e}")

        return contracts

    def _compute_schema_hash(self, content: str, contract_name: str) -> str:
        """Compute a hash for the contract schema"""
        # Simple hash based on contract name and content
        hash_input = f"{contract_name}:{content[:1000]}"
        return hashlib.md5(hash_input.encode()).hexdigest()[:12]

    def validate_feature_file(self, feature_file: Path) -> List[VersionMismatch]:
        """
        Validate contract versions in a single feature file.

        Args:
            feature_file: Path to feature file

        Returns:
            List of VersionMismatch objects
        """
        mismatches = []
        contracts = self.extract_contract_versions(feature_file)

        for contract in contracts:
            expected = self._expected_versions.get(contract.contract_id)

            if expected is None:
                # No expected version registered - skip validation
                continue

            is_compatible, severity = contract.version.is_compatible_with(expected)

            if not is_compatible or (self.warn_on_minor and severity == VersionSeverity.WARNING):
                mismatch = VersionMismatch(
                    contract_id=contract.contract_id,
                    expected_version=expected,
                    actual_version=contract.version,
                    severity=severity,
                    message=self._generate_mismatch_message(
                        contract.contract_id,
                        expected,
                        contract.version,
                        severity
                    ),
                    feature_file=str(feature_file)
                )
                mismatches.append(mismatch)

        return mismatches

    def _generate_mismatch_message(
        self,
        contract_id: str,
        expected: SemanticVersion,
        actual: SemanticVersion,
        severity: VersionSeverity
    ) -> str:
        """Generate a human-readable mismatch message"""
        if severity == VersionSeverity.BREAKING:
            return (f"BREAKING: Contract '{contract_id}' has major version mismatch. "
                   f"Expected v{expected}, found v{actual}. "
                   f"This may indicate incompatible API changes.")
        elif severity == VersionSeverity.WARNING:
            return (f"WARNING: Contract '{contract_id}' has minor version difference. "
                   f"Expected v{expected}, found v{actual}. "
                   f"New features may be available.")
        else:
            return f"Contract '{contract_id}' version v{actual} (expected v{expected})"

    def validate_all(self, features_path: Path) -> ValidationResult:
        """
        Validate all feature files in a directory.

        Args:
            features_path: Path to features directory

        Returns:
            ValidationResult with all validation outcomes
        """
        all_mismatches = []
        blocking_errors = []
        warnings = []
        total_contracts = 0
        valid_contracts = 0

        # Find all feature files
        feature_files = list(features_path.rglob("*.feature"))

        for feature_file in feature_files:
            contracts = self.extract_contract_versions(feature_file)
            total_contracts += len(contracts)

            mismatches = self.validate_feature_file(feature_file)

            for mismatch in mismatches:
                all_mismatches.append(mismatch)

                if mismatch.severity == VersionSeverity.BREAKING:
                    blocking_errors.append(mismatch.message)
                elif mismatch.severity == VersionSeverity.WARNING:
                    warnings.append(mismatch.message)

            # Count valid contracts (those without mismatches)
            mismatch_ids = {m.contract_id for m in mismatches}
            valid_contracts += sum(
                1 for c in contracts if c.contract_id not in mismatch_ids
            )

        # Determine if validation passes
        is_valid = len(blocking_errors) == 0 or not self.block_on_breaking

        return ValidationResult(
            is_valid=is_valid,
            total_contracts=total_contracts,
            valid_contracts=valid_contracts,
            mismatches=all_mismatches,
            blocking_errors=blocking_errors,
            warnings=warnings
        )

    def should_block_execution(self, result: ValidationResult) -> bool:
        """
        Determine if test execution should be blocked.

        Args:
            result: ValidationResult from validate_all()

        Returns:
            True if execution should be blocked
        """
        if not self.block_on_breaking:
            return False

        return len(result.blocking_errors) > 0


class ContractRegistry:
    """
    Registry for managing contract versions across the system.

    Provides:
    - Central storage of expected contract versions
    - Version history tracking
    - Breaking change documentation
    """

    def __init__(self):
        self._contracts: Dict[str, ContractVersion] = {}
        self._history: Dict[str, List[ContractVersion]] = {}

    def register(self, contract: ContractVersion, breaking_changes: Optional[List[str]] = None):
        """
        Register a contract version.

        Args:
            contract: ContractVersion to register
            breaking_changes: List of breaking change descriptions
        """
        contract_id = contract.contract_id

        # Track history
        if contract_id in self._contracts:
            if contract_id not in self._history:
                self._history[contract_id] = []
            self._history[contract_id].append(self._contracts[contract_id])

        # Update breaking changes
        if breaking_changes:
            contract.breaking_changes = breaking_changes

        self._contracts[contract_id] = contract
        logger.info(f"Registered contract: {contract_id} v{contract.version}")

    def get(self, contract_id: str) -> Optional[ContractVersion]:
        """Get a contract by ID"""
        return self._contracts.get(contract_id)

    def get_expected_versions(self) -> Dict[str, str]:
        """Get all expected versions as dict"""
        return {
            contract_id: str(contract.version)
            for contract_id, contract in self._contracts.items()
        }

    def get_history(self, contract_id: str) -> List[ContractVersion]:
        """Get version history for a contract"""
        history = self._history.get(contract_id, []).copy()
        if contract_id in self._contracts:
            history.append(self._contracts[contract_id])
        return history

    def create_validator(self) -> ContractVersionValidator:
        """Create a validator with registered expected versions"""
        return ContractVersionValidator(
            expected_versions=self.get_expected_versions()
        )


# Global registry instance
_contract_registry: Optional[ContractRegistry] = None


def get_contract_registry() -> ContractRegistry:
    """Get or create global contract registry"""
    global _contract_registry
    if _contract_registry is None:
        _contract_registry = ContractRegistry()
    return _contract_registry


# Example usage
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    # Create validator with expected versions
    validator = ContractVersionValidator(
        expected_versions={
            'authapi': '2.0.0',
            'userapi': '1.5.0'
        },
        block_on_breaking=True
    )

    # Test version parsing
    print("=== Testing SemanticVersion ===")
    v1 = SemanticVersion.parse("1.2.3")
    v2 = SemanticVersion.parse("v2.0")
    v3 = SemanticVersion.parse("1.2.3")

    print(f"v1: {v1}")
    print(f"v2: {v2}")
    print(f"v1 == v3: {v1 == v3}")
    print(f"v1 < v2: {v1 < v2}")

    is_compat, severity = v1.is_compatible_with(v2)
    print(f"v1 compatible with v2: {is_compat}, severity: {severity}")

    # Test validation
    print("\n=== Testing Validation ===")
    features_path = Path("features/")
    if features_path.exists():
        result = validator.validate_all(features_path)
        print(f"Valid: {result.is_valid}")
        print(f"Total contracts: {result.total_contracts}")
        print(f"Blocking errors: {len(result.blocking_errors)}")
        print(f"Warnings: {len(result.warnings)}")
