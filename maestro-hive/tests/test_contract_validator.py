"""
Tests for ContractVersionValidator (MD-2095)

Validates:
- Semantic version parsing
- Version comparison
- Contract extraction from feature files
- Mismatch detection
- Breaking change blocking
"""

import pytest
import tempfile
from pathlib import Path
from datetime import datetime
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from bdv.contract_validator import (
    SemanticVersion,
    ContractVersion,
    ContractVersionValidator,
    VersionMismatch,
    ValidationResult,
    VersionSeverity,
    ContractRegistry,
    get_contract_registry
)


class TestSemanticVersion:
    """Tests for SemanticVersion class"""

    def test_parse_full_version(self):
        """Test parsing full semver"""
        v = SemanticVersion.parse("1.2.3")
        assert v.major == 1
        assert v.minor == 2
        assert v.patch == 3

    def test_parse_major_minor(self):
        """Test parsing major.minor only"""
        v = SemanticVersion.parse("2.5")
        assert v.major == 2
        assert v.minor == 5
        assert v.patch == 0

    def test_parse_major_only(self):
        """Test parsing major only"""
        v = SemanticVersion.parse("3")
        assert v.major == 3
        assert v.minor == 0
        assert v.patch == 0

    def test_parse_with_v_prefix(self):
        """Test parsing with 'v' prefix"""
        v = SemanticVersion.parse("v1.2.3")
        assert v.major == 1
        assert v.minor == 2
        assert v.patch == 3

    def test_parse_invalid(self):
        """Test parsing invalid version"""
        v = SemanticVersion.parse("invalid")
        assert v is None

    def test_str_representation(self):
        """Test string representation"""
        v = SemanticVersion(major=1, minor=2, patch=3)
        assert str(v) == "1.2.3"

    def test_equality(self):
        """Test version equality"""
        v1 = SemanticVersion(1, 2, 3)
        v2 = SemanticVersion(1, 2, 3)
        v3 = SemanticVersion(1, 2, 4)

        assert v1 == v2
        assert v1 != v3

    def test_less_than_major(self):
        """Test less than comparison (major)"""
        v1 = SemanticVersion(1, 0, 0)
        v2 = SemanticVersion(2, 0, 0)
        assert v1 < v2

    def test_less_than_minor(self):
        """Test less than comparison (minor)"""
        v1 = SemanticVersion(1, 1, 0)
        v2 = SemanticVersion(1, 2, 0)
        assert v1 < v2

    def test_less_than_patch(self):
        """Test less than comparison (patch)"""
        v1 = SemanticVersion(1, 1, 1)
        v2 = SemanticVersion(1, 1, 2)
        assert v1 < v2

    def test_compatible_same_version(self):
        """Test compatibility - same version"""
        v1 = SemanticVersion(1, 2, 3)
        v2 = SemanticVersion(1, 2, 3)

        is_compat, severity = v1.is_compatible_with(v2)
        assert is_compat is True
        assert severity == VersionSeverity.COMPATIBLE

    def test_compatible_minor_diff(self):
        """Test compatibility - minor version difference"""
        v1 = SemanticVersion(1, 2, 0)
        v2 = SemanticVersion(1, 3, 0)

        is_compat, severity = v1.is_compatible_with(v2)
        assert is_compat is True
        assert severity == VersionSeverity.WARNING

    def test_incompatible_major_diff(self):
        """Test incompatibility - major version difference"""
        v1 = SemanticVersion(1, 0, 0)
        v2 = SemanticVersion(2, 0, 0)

        is_compat, severity = v1.is_compatible_with(v2)
        assert is_compat is False
        assert severity == VersionSeverity.BREAKING


class TestContractVersion:
    """Tests for ContractVersion class"""

    def test_creation(self):
        """Test ContractVersion creation"""
        version = SemanticVersion(1, 0, 0)
        contract = ContractVersion(
            contract_id="auth",
            contract_name="AuthAPI",
            version=version,
            schema_hash="abc123"
        )

        assert contract.contract_id == "auth"
        assert contract.version.major == 1
        assert contract.schema_hash == "abc123"

    def test_to_dict(self):
        """Test conversion to dictionary"""
        version = SemanticVersion(1, 2, 0)
        contract = ContractVersion(
            contract_id="auth",
            contract_name="AuthAPI",
            version=version,
            schema_hash="abc123",
            breaking_changes=["Removed endpoint X"]
        )

        d = contract.to_dict()
        assert d['contract_id'] == "auth"
        assert d['version'] == "1.2.0"
        assert d['breaking_changes'] == ["Removed endpoint X"]


class TestContractVersionValidator:
    """Tests for ContractVersionValidator class"""

    def test_initialization_empty(self):
        """Test validator initialization without expected versions"""
        validator = ContractVersionValidator()
        assert len(validator._expected_versions) == 0

    def test_initialization_with_versions(self):
        """Test validator initialization with expected versions"""
        validator = ContractVersionValidator(
            expected_versions={
                'auth': '1.0.0',
                'user': '2.1.0'
            }
        )
        assert len(validator._expected_versions) == 2
        assert validator._expected_versions['auth'].major == 1

    def test_register_expected_version(self):
        """Test registering expected versions"""
        validator = ContractVersionValidator()
        validator.register_expected_version('auth', '1.5.0')

        assert 'auth' in validator._expected_versions
        assert validator._expected_versions['auth'].minor == 5

    def test_extract_contract_versions(self):
        """Test extracting versions from feature file"""
        # Create temp feature file
        content = """
@contract:AuthAPI:v1.2.0
Feature: Authentication

  Scenario: Login
    Given I have credentials
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.feature', delete=False) as f:
            f.write(content)
            feature_path = Path(f.name)

        validator = ContractVersionValidator()
        contracts = validator.extract_contract_versions(feature_path)

        assert len(contracts) == 1
        assert contracts[0].contract_id == "authapi"
        assert contracts[0].version.major == 1
        assert contracts[0].version.minor == 2

        # Cleanup
        feature_path.unlink()

    def test_extract_multiple_contracts(self):
        """Test extracting multiple contracts from one file"""
        content = """
@contract:AuthAPI:v1.0.0
@contract:UserAPI:v2.5.1
Feature: User Management
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.feature', delete=False) as f:
            f.write(content)
            feature_path = Path(f.name)

        validator = ContractVersionValidator()
        contracts = validator.extract_contract_versions(feature_path)

        assert len(contracts) == 2
        feature_path.unlink()

    def test_validate_matching_version(self):
        """Test validation with matching version"""
        content = "@contract:AuthAPI:v1.0.0\nFeature: Test"

        with tempfile.NamedTemporaryFile(mode='w', suffix='.feature', delete=False) as f:
            f.write(content)
            feature_path = Path(f.name)

        validator = ContractVersionValidator(
            expected_versions={'authapi': '1.0.0'}
        )
        mismatches = validator.validate_feature_file(feature_path)

        assert len(mismatches) == 0
        feature_path.unlink()

    def test_validate_breaking_change(self):
        """Test validation detects breaking change"""
        content = "@contract:AuthAPI:v2.0.0\nFeature: Test"

        with tempfile.NamedTemporaryFile(mode='w', suffix='.feature', delete=False) as f:
            f.write(content)
            feature_path = Path(f.name)

        validator = ContractVersionValidator(
            expected_versions={'authapi': '1.0.0'}
        )
        mismatches = validator.validate_feature_file(feature_path)

        assert len(mismatches) == 1
        assert mismatches[0].severity == VersionSeverity.BREAKING
        feature_path.unlink()

    def test_validate_minor_warning(self):
        """Test validation warns on minor version diff"""
        content = "@contract:AuthAPI:v1.5.0\nFeature: Test"

        with tempfile.NamedTemporaryFile(mode='w', suffix='.feature', delete=False) as f:
            f.write(content)
            feature_path = Path(f.name)

        validator = ContractVersionValidator(
            expected_versions={'authapi': '1.2.0'},
            warn_on_minor=True
        )
        mismatches = validator.validate_feature_file(feature_path)

        assert len(mismatches) == 1
        assert mismatches[0].severity == VersionSeverity.WARNING
        feature_path.unlink()

    def test_validate_all(self):
        """Test validating all features in directory"""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)

            # Create feature files
            (tmppath / "auth.feature").write_text(
                "@contract:AuthAPI:v1.0.0\nFeature: Auth"
            )
            (tmppath / "user.feature").write_text(
                "@contract:UserAPI:v2.0.0\nFeature: User"
            )

            validator = ContractVersionValidator(
                expected_versions={
                    'authapi': '1.0.0',
                    'userapi': '1.0.0'  # Breaking change
                }
            )

            result = validator.validate_all(tmppath)

            assert result.total_contracts == 2
            assert result.valid_contracts == 1
            assert len(result.blocking_errors) == 1
            assert result.is_valid is False

    def test_should_block_execution(self):
        """Test blocking on breaking changes"""
        validator = ContractVersionValidator(
            expected_versions={'auth': '1.0.0'},
            block_on_breaking=True
        )

        result = ValidationResult(
            is_valid=False,
            total_contracts=1,
            valid_contracts=0,
            mismatches=[],
            blocking_errors=["Breaking change detected"],
            warnings=[]
        )

        assert validator.should_block_execution(result) is True

    def test_no_block_when_disabled(self):
        """Test no blocking when disabled"""
        validator = ContractVersionValidator(
            expected_versions={'auth': '1.0.0'},
            block_on_breaking=False
        )

        result = ValidationResult(
            is_valid=True,
            total_contracts=1,
            valid_contracts=0,
            mismatches=[],
            blocking_errors=["Breaking change detected"],
            warnings=[]
        )

        assert validator.should_block_execution(result) is False


class TestContractRegistry:
    """Tests for ContractRegistry class"""

    def test_register_contract(self):
        """Test registering a contract"""
        registry = ContractRegistry()
        version = SemanticVersion(1, 0, 0)
        contract = ContractVersion(
            contract_id="auth",
            contract_name="AuthAPI",
            version=version,
            schema_hash="abc123"
        )

        registry.register(contract)

        assert registry.get("auth") == contract

    def test_version_history(self):
        """Test version history tracking"""
        registry = ContractRegistry()

        # Register v1
        v1 = ContractVersion(
            contract_id="auth",
            contract_name="AuthAPI",
            version=SemanticVersion(1, 0, 0),
            schema_hash="v1hash"
        )
        registry.register(v1)

        # Register v2
        v2 = ContractVersion(
            contract_id="auth",
            contract_name="AuthAPI",
            version=SemanticVersion(2, 0, 0),
            schema_hash="v2hash"
        )
        registry.register(v2, breaking_changes=["Removed endpoint X"])

        history = registry.get_history("auth")
        assert len(history) == 2
        assert history[0].version.major == 1
        assert history[1].version.major == 2

    def test_create_validator(self):
        """Test creating validator from registry"""
        registry = ContractRegistry()
        registry.register(ContractVersion(
            contract_id="auth",
            contract_name="AuthAPI",
            version=SemanticVersion(1, 0, 0),
            schema_hash="abc"
        ))

        validator = registry.create_validator()
        assert 'auth' in validator._expected_versions


class TestVersionMismatch:
    """Tests for VersionMismatch class"""

    def test_to_dict(self):
        """Test VersionMismatch to_dict"""
        mismatch = VersionMismatch(
            contract_id="auth",
            expected_version=SemanticVersion(1, 0, 0),
            actual_version=SemanticVersion(2, 0, 0),
            severity=VersionSeverity.BREAKING,
            message="Breaking change",
            feature_file="test.feature"
        )

        d = mismatch.to_dict()
        assert d['contract_id'] == "auth"
        assert d['expected_version'] == "1.0.0"
        assert d['actual_version'] == "2.0.0"
        assert d['severity'] == "breaking"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
