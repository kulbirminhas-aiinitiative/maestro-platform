"""Tests for ReleaseManagementConfig."""

import pytest
import tempfile
import os
import yaml

from maestro_hive.release_management.config import (
    ReleaseManagementConfig,
    EnvironmentDefaults,
    BranchDefaults,
    PipelineDefaults,
)


class TestEnvironmentDefaults:
    """Tests for EnvironmentDefaults dataclass."""

    def test_default_values(self):
        """Test default environment values."""
        defaults = EnvironmentDefaults()
        assert defaults.cpu == "1000m"
        assert defaults.memory == "1Gi"
        assert defaults.replicas == 1
        assert defaults.auto_deploy is False
        assert defaults.data_source == "synthetic"

    def test_custom_values(self):
        """Test custom environment values."""
        defaults = EnvironmentDefaults(
            cpu="2000m",
            memory="4Gi",
            replicas=3,
            auto_deploy=True,
            data_source="production_snapshot",
        )
        assert defaults.cpu == "2000m"
        assert defaults.replicas == 3


class TestBranchDefaults:
    """Tests for BranchDefaults dataclass."""

    def test_default_values(self):
        """Test default branch values."""
        defaults = BranchDefaults()
        assert defaults.require_reviews == 1
        assert defaults.require_ci is True
        assert defaults.require_signed is False
        assert defaults.prevent_force_push is True

    def test_custom_values(self):
        """Test custom branch values."""
        defaults = BranchDefaults(
            require_reviews=2,
            require_signed=True,
        )
        assert defaults.require_reviews == 2
        assert defaults.require_signed is True


class TestPipelineDefaults:
    """Tests for PipelineDefaults dataclass."""

    def test_default_values(self):
        """Test default pipeline values."""
        defaults = PipelineDefaults()
        assert defaults.default_timeout_minutes == 30
        assert defaults.max_concurrent_runs == 5
        assert defaults.artifact_retention_days == 30


class TestReleaseManagementConfig:
    """Tests for ReleaseManagementConfig class."""

    def test_default_config(self):
        """Test default configuration."""
        config = ReleaseManagementConfig()

        assert config.enable_auto_promotion is False
        assert config.git_default_branch == "main"
        assert len(config.notification_channels) == 0
        assert len(config.environments) == 0

    def test_from_dict(self):
        """Test creating config from dictionary."""
        data = {
            "enable_auto_promotion": True,
            "git_default_branch": "develop",
            "notification_channels": ["#releases"],
            "environment_defaults": {
                "cpu": "2000m",
                "replicas": 2,
            },
            "environments": {
                "dev": {"tier": "development"},
                "test": {"tier": "test"},
            },
        }

        config = ReleaseManagementConfig.from_dict(data)

        assert config.enable_auto_promotion is True
        assert config.git_default_branch == "develop"
        assert config.notification_channels == ["#releases"]
        assert config.environment_defaults.cpu == "2000m"
        assert "dev" in config.environments

    def test_from_dict_with_branches(self):
        """Test creating config with branch settings."""
        data = {
            "branch_defaults": {
                "require_reviews": 2,
                "require_ci": True,
            },
            "branches": {
                "main": {"require_reviews": 3},
                "develop": {"require_reviews": 1},
            },
        }

        config = ReleaseManagementConfig.from_dict(data)

        assert config.branch_defaults.require_reviews == 2
        assert "main" in config.branches
        assert config.branches["main"]["require_reviews"] == 3

    def test_from_dict_with_pipelines(self):
        """Test creating config with pipeline settings."""
        data = {
            "pipeline_defaults": {
                "default_timeout_minutes": 60,
                "max_concurrent_runs": 10,
            },
            "pipelines": {
                "dev-pipeline": {"timeout": 30},
                "test-pipeline": {"timeout": 45},
            },
        }

        config = ReleaseManagementConfig.from_dict(data)

        assert config.pipeline_defaults.default_timeout_minutes == 60
        assert "dev-pipeline" in config.pipelines

    def test_from_file(self):
        """Test loading config from YAML file."""
        yaml_content = """
enable_auto_promotion: true
git_default_branch: main
notification_channels:
  - "#releases"
  - "#devops"
environment_defaults:
  cpu: "2000m"
  memory: "4Gi"
  replicas: 2
environments:
  dev:
    tier: development
    auto_deploy: true
  test:
    tier: test
"""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
            f.write(yaml_content)
            temp_path = f.name

        try:
            config = ReleaseManagementConfig.from_file(temp_path)

            assert config.enable_auto_promotion is True
            assert config.environment_defaults.cpu == "2000m"
            assert "dev" in config.environments
        finally:
            os.unlink(temp_path)

    def test_from_file_not_found(self):
        """Test loading config from non-existent file."""
        with pytest.raises(FileNotFoundError):
            ReleaseManagementConfig.from_file("/nonexistent/path.yaml")

    def test_from_env_with_config_path(self):
        """Test loading config from env with config path."""
        yaml_content = """
enable_auto_promotion: true
"""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
            f.write(yaml_content)
            temp_path = f.name

        try:
            os.environ["RELEASE_MGMT_CONFIG_PATH"] = temp_path
            config = ReleaseManagementConfig.from_env()

            assert config.enable_auto_promotion is True
        finally:
            del os.environ["RELEASE_MGMT_CONFIG_PATH"]
            os.unlink(temp_path)

    def test_from_env_with_individual_settings(self):
        """Test loading config from individual env vars."""
        os.environ["ENABLE_AUTO_PROMOTION"] = "true"
        os.environ["GIT_DEFAULT_BRANCH"] = "develop"
        os.environ["ENVIRONMENT_TIER"] = "test"

        try:
            config = ReleaseManagementConfig.from_env()

            assert config.enable_auto_promotion is True
            assert config.git_default_branch == "develop"
            assert config.environments.get("current", {}).get("tier") == "test"
        finally:
            del os.environ["ENABLE_AUTO_PROMOTION"]
            del os.environ["GIT_DEFAULT_BRANCH"]
            del os.environ["ENVIRONMENT_TIER"]

    def test_validate_valid_config(self):
        """Test validation passes for valid config."""
        config = ReleaseManagementConfig()
        assert config.validate() is True

    def test_validate_invalid_replicas(self):
        """Test validation fails for invalid replicas."""
        config = ReleaseManagementConfig()
        config.environment_defaults.replicas = 0

        with pytest.raises(ValueError, match="replicas"):
            config.validate()

    def test_validate_invalid_reviews(self):
        """Test validation fails for negative reviews."""
        config = ReleaseManagementConfig()
        config.branch_defaults.require_reviews = -1

        with pytest.raises(ValueError, match="reviews"):
            config.validate()

    def test_validate_invalid_timeout(self):
        """Test validation fails for invalid timeout."""
        config = ReleaseManagementConfig()
        config.pipeline_defaults.default_timeout_minutes = 0

        with pytest.raises(ValueError, match="timeout"):
            config.validate()

    def test_validate_invalid_concurrent_runs(self):
        """Test validation fails for invalid concurrent runs."""
        config = ReleaseManagementConfig()
        config.pipeline_defaults.max_concurrent_runs = 0

        with pytest.raises(ValueError, match="concurrent"):
            config.validate()

    def test_validate_invalid_tier(self):
        """Test validation fails for invalid environment tier."""
        config = ReleaseManagementConfig()
        config.environments["invalid"] = {"tier": "invalid_tier"}

        with pytest.raises(ValueError, match="Invalid tier"):
            config.validate()

    def test_to_dict(self):
        """Test converting config to dictionary."""
        config = ReleaseManagementConfig()
        config.enable_auto_promotion = True
        config.environments["dev"] = {"tier": "development"}

        result = config.to_dict()

        assert result["enable_auto_promotion"] is True
        assert "dev" in result["environments"]
        assert "environment_defaults" in result
        assert "branch_defaults" in result
        assert "pipeline_defaults" in result

    def test_save(self):
        """Test saving config to file."""
        config = ReleaseManagementConfig()
        config.enable_auto_promotion = True
        config.notification_channels = ["#test"]

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
            temp_path = f.name

        try:
            config.save(temp_path)

            # Verify file contents
            with open(temp_path, "r") as f:
                loaded = yaml.safe_load(f)

            assert loaded["enable_auto_promotion"] is True
            assert "#test" in loaded["notification_channels"]
        finally:
            os.unlink(temp_path)

    def test_get_environment_config(self):
        """Test getting environment config with defaults merged."""
        config = ReleaseManagementConfig()
        config.environment_defaults.cpu = "1000m"
        config.environments["dev"] = {"cpu": "500m", "tier": "development"}

        env_config = config.get_environment_config("dev")

        # Overridden value
        assert env_config["cpu"] == "500m"
        # Default value
        assert env_config["memory"] == "1Gi"
        # Custom value
        assert env_config["tier"] == "development"

    def test_get_environment_config_not_found(self):
        """Test getting config for non-existent environment uses defaults."""
        config = ReleaseManagementConfig()
        config.environment_defaults.cpu = "1000m"

        env_config = config.get_environment_config("nonexistent")

        assert env_config["cpu"] == "1000m"
        assert env_config["replicas"] == 1

    def test_get_branch_config(self):
        """Test getting branch config with defaults merged."""
        config = ReleaseManagementConfig()
        config.branch_defaults.require_reviews = 1
        config.branches["main"] = {
            "require_reviews": 2,
            "require_signed": True,
        }

        branch_config = config.get_branch_config("main")

        # Overridden value
        assert branch_config["require_reviews"] == 2
        # Overridden value
        assert branch_config["require_signed"] is True
        # Default value
        assert branch_config["require_ci"] is True

    def test_get_branch_config_not_found(self):
        """Test getting config for non-existent branch uses defaults."""
        config = ReleaseManagementConfig()
        config.branch_defaults.require_reviews = 1

        branch_config = config.get_branch_config("nonexistent")

        assert branch_config["require_reviews"] == 1
        assert branch_config["prevent_force_push"] is True

    def test_roundtrip_save_load(self):
        """Test saving and loading config preserves values."""
        original = ReleaseManagementConfig()
        original.enable_auto_promotion = True
        original.git_default_branch = "develop"
        original.environments["dev"] = {"tier": "development"}
        original.branches["main"] = {"require_reviews": 2}

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
            temp_path = f.name

        try:
            original.save(temp_path)
            loaded = ReleaseManagementConfig.from_file(temp_path)

            assert loaded.enable_auto_promotion == original.enable_auto_promotion
            assert loaded.git_default_branch == original.git_default_branch
            assert loaded.environments == original.environments
            assert loaded.branches == original.branches
        finally:
            os.unlink(temp_path)
