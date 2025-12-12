"""Tests for EnvironmentManager."""

import pytest
from datetime import datetime

from maestro_hive.release_management.environments import EnvironmentManager
from maestro_hive.release_management.models import (
    EnvironmentConfig,
    EnvironmentTier,
    EnvironmentStatus,
)


class TestEnvironmentManager:
    """Tests for EnvironmentManager class."""

    @pytest.fixture
    def manager(self):
        """Create a fresh EnvironmentManager instance."""
        return EnvironmentManager()

    def test_init(self, manager):
        """Test manager initialization."""
        assert manager is not None
        assert len(manager._environments) == 0

    def test_create_environment(self, manager):
        """Test creating an environment."""
        env = manager.create_environment(
            name="dev-1",
            tier=EnvironmentTier.DEVELOPMENT,
        )
        assert env.name == "dev-1"
        assert env.tier == EnvironmentTier.DEVELOPMENT
        assert env.status == EnvironmentStatus.HEALTHY

    def test_create_environment_with_config(self, manager):
        """Test creating environment with custom config."""
        config = EnvironmentConfig(
            cpu="2000m",
            memory="4Gi",
            replicas=3,
        )
        env = manager.create_environment(
            name="test-1",
            tier=EnvironmentTier.TEST,
            config=config,
        )
        assert env.config.cpu == "2000m"
        assert env.config.replicas == 3

    def test_create_duplicate_environment_raises(self, manager):
        """Test creating duplicate environment raises error."""
        manager.create_environment("dev-1", EnvironmentTier.DEVELOPMENT)
        with pytest.raises(ValueError, match="already exists"):
            manager.create_environment("dev-1", EnvironmentTier.DEVELOPMENT)

    def test_create_environment_invalid_config_raises(self, manager):
        """Test creating environment with invalid config raises error."""
        config = EnvironmentConfig(replicas=0)  # Invalid
        with pytest.raises(ValueError, match="Invalid"):
            manager.create_environment(
                name="invalid",
                tier=EnvironmentTier.DEVELOPMENT,
                config=config,
            )

    def test_get_environment(self, manager):
        """Test getting an environment."""
        manager.create_environment("dev-1", EnvironmentTier.DEVELOPMENT)
        env = manager.get_environment("dev-1")
        assert env is not None
        assert env.name == "dev-1"

    def test_get_environment_not_found(self, manager):
        """Test getting non-existent environment."""
        env = manager.get_environment("nonexistent")
        assert env is None

    def test_list_environments(self, manager):
        """Test listing environments."""
        manager.create_environment("dev-1", EnvironmentTier.DEVELOPMENT)
        manager.create_environment("test-1", EnvironmentTier.TEST)

        envs = manager.list_environments()
        assert len(envs) == 2

    def test_list_environments_by_tier(self, manager):
        """Test listing environments filtered by tier."""
        manager.create_environment("dev-1", EnvironmentTier.DEVELOPMENT)
        manager.create_environment("dev-2", EnvironmentTier.DEVELOPMENT)
        manager.create_environment("test-1", EnvironmentTier.TEST)

        dev_envs = manager.list_environments(tier=EnvironmentTier.DEVELOPMENT)
        assert len(dev_envs) == 2

    def test_list_environments_by_status(self, manager):
        """Test listing environments filtered by status."""
        manager.create_environment("dev-1", EnvironmentTier.DEVELOPMENT)
        env = manager.create_environment("dev-2", EnvironmentTier.DEVELOPMENT)
        env.status = EnvironmentStatus.UNHEALTHY

        healthy = manager.list_environments(status=EnvironmentStatus.HEALTHY)
        assert len(healthy) == 1

    def test_update_environment_config(self, manager):
        """Test updating environment config."""
        manager.create_environment("dev-1", EnvironmentTier.DEVELOPMENT)

        new_config = EnvironmentConfig(cpu="3000m", replicas=2)
        env = manager.update_environment("dev-1", config=new_config)

        assert env is not None
        assert env.config.cpu == "3000m"
        assert env.config.replicas == 2

    def test_update_environment_status(self, manager):
        """Test updating environment status."""
        manager.create_environment("dev-1", EnvironmentTier.DEVELOPMENT)

        env = manager.update_environment("dev-1", status=EnvironmentStatus.DEGRADED)

        assert env is not None
        assert env.status == EnvironmentStatus.DEGRADED

    def test_update_nonexistent_environment(self, manager):
        """Test updating non-existent environment."""
        result = manager.update_environment("nonexistent", status=EnvironmentStatus.HEALTHY)
        assert result is None

    def test_delete_environment(self, manager):
        """Test deleting an environment."""
        manager.create_environment("dev-1", EnvironmentTier.DEVELOPMENT)

        result = manager.delete_environment("dev-1")
        assert result is True
        assert manager.get_environment("dev-1") is None

    def test_delete_nonexistent_environment(self, manager):
        """Test deleting non-existent environment."""
        result = manager.delete_environment("nonexistent")
        assert result is False

    def test_deploy_version(self, manager):
        """Test deploying a version."""
        manager.create_environment("dev-1", EnvironmentTier.DEVELOPMENT)

        result = manager.deploy("dev-1", "1.0.0")

        assert result is True
        env = manager.get_environment("dev-1")
        assert env.current_version == "1.0.0"

    def test_deploy_to_unhealthy_environment(self, manager):
        """Test deploying to unhealthy environment fails."""
        env = manager.create_environment("dev-1", EnvironmentTier.DEVELOPMENT)
        env.status = EnvironmentStatus.UNHEALTHY

        result = manager.deploy("dev-1", "1.0.0")
        assert result is False

    def test_deploy_force_to_unhealthy(self, manager):
        """Test force deploy to unhealthy environment."""
        env = manager.create_environment("dev-1", EnvironmentTier.DEVELOPMENT)
        env.status = EnvironmentStatus.UNHEALTHY

        result = manager.deploy("dev-1", "1.0.0", force=True)
        assert result is True
        assert env.current_version == "1.0.0"

    def test_deploy_tracks_version_history(self, manager):
        """Test that deploy tracks version history."""
        manager.create_environment("dev-1", EnvironmentTier.DEVELOPMENT)

        manager.deploy("dev-1", "1.0.0")
        manager.deploy("dev-1", "1.1.0")
        manager.deploy("dev-1", "1.2.0")

        history = manager.get_version_history("dev-1")
        assert "1.0.0" in history
        assert "1.1.0" in history

    def test_promote_valid_path(self, manager):
        """Test promoting between valid environments."""
        manager.create_environment("dev-1", EnvironmentTier.DEVELOPMENT)
        manager.create_environment("test-1", EnvironmentTier.TEST)
        manager.deploy("dev-1", "1.0.0")

        result = manager.promote("dev-1", "test-1")

        assert result.success is True
        assert result.version == "1.0.0"
        test_env = manager.get_environment("test-1")
        assert test_env.current_version == "1.0.0"

    def test_promote_invalid_path(self, manager):
        """Test promoting between invalid environments fails."""
        manager.create_environment("dev-1", EnvironmentTier.DEVELOPMENT)
        manager.create_environment("prod-1", EnvironmentTier.PRODUCTION)
        manager.deploy("dev-1", "1.0.0")

        result = manager.promote("dev-1", "prod-1")

        assert result.success is False
        assert "Cannot promote" in result.error

    def test_promote_source_not_found(self, manager):
        """Test promote with non-existent source."""
        manager.create_environment("test-1", EnvironmentTier.TEST)

        result = manager.promote("nonexistent", "test-1")

        assert result.success is False
        assert "not found" in result.error

    def test_promote_no_version(self, manager):
        """Test promote when no version deployed."""
        manager.create_environment("dev-1", EnvironmentTier.DEVELOPMENT)
        manager.create_environment("test-1", EnvironmentTier.TEST)

        result = manager.promote("dev-1", "test-1")

        assert result.success is False
        assert "No version" in result.error

    def test_promote_specific_version(self, manager):
        """Test promoting a specific version."""
        manager.create_environment("dev-1", EnvironmentTier.DEVELOPMENT)
        manager.create_environment("test-1", EnvironmentTier.TEST)
        manager.deploy("dev-1", "1.0.0")

        result = manager.promote("dev-1", "test-1", version="2.0.0")

        assert result.success is True
        assert result.version == "2.0.0"

    def test_rollback_to_previous(self, manager):
        """Test rolling back to previous version."""
        manager.create_environment("dev-1", EnvironmentTier.DEVELOPMENT)
        manager.deploy("dev-1", "1.0.0")
        manager.deploy("dev-1", "1.1.0")

        result = manager.rollback("dev-1")

        assert result.success is True
        assert result.from_version == "1.1.0"
        assert result.to_version == "1.0.0"
        env = manager.get_environment("dev-1")
        assert env.current_version == "1.0.0"

    def test_rollback_to_specific_version(self, manager):
        """Test rolling back to specific version."""
        manager.create_environment("dev-1", EnvironmentTier.DEVELOPMENT)
        manager.deploy("dev-1", "1.0.0")
        manager.deploy("dev-1", "1.1.0")
        manager.deploy("dev-1", "1.2.0")

        result = manager.rollback("dev-1", target_version="1.0.0")

        assert result.success is True
        assert result.to_version == "1.0.0"

    def test_rollback_version_not_in_history(self, manager):
        """Test rollback to version not in history fails."""
        manager.create_environment("dev-1", EnvironmentTier.DEVELOPMENT)
        manager.deploy("dev-1", "1.0.0")

        result = manager.rollback("dev-1", target_version="0.5.0")

        assert result.success is False
        assert "not in history" in result.error

    def test_rollback_no_history(self, manager):
        """Test rollback when no history available."""
        manager.create_environment("dev-1", EnvironmentTier.DEVELOPMENT)
        manager.deploy("dev-1", "1.0.0")

        result = manager.rollback("dev-1")

        assert result.success is False
        assert "No previous version" in result.error

    def test_rollback_with_reason(self, manager):
        """Test rollback with reason."""
        manager.create_environment("dev-1", EnvironmentTier.DEVELOPMENT)
        manager.deploy("dev-1", "1.0.0")
        manager.deploy("dev-1", "1.1.0")

        result = manager.rollback("dev-1", reason="Regression found")

        assert result.success is True
        assert result.reason == "Regression found"

    def test_get_health_status(self, manager):
        """Test getting health status."""
        manager.create_environment("dev-1", EnvironmentTier.DEVELOPMENT)
        manager.deploy("dev-1", "1.0.0")

        status = manager.get_health_status("dev-1")

        assert status["name"] == "dev-1"
        assert status["is_healthy"] is True
        assert status["current_version"] == "1.0.0"

    def test_get_health_status_not_found(self, manager):
        """Test health status for non-existent environment."""
        status = manager.get_health_status("nonexistent")
        assert "error" in status

    def test_get_version_history_empty(self, manager):
        """Test version history for new environment."""
        manager.create_environment("dev-1", EnvironmentTier.DEVELOPMENT)

        history = manager.get_version_history("dev-1")
        assert history == []

    def test_default_config_by_tier(self, manager):
        """Test that default config varies by tier."""
        dev = manager.create_environment("dev", EnvironmentTier.DEVELOPMENT)
        test = manager.create_environment("test", EnvironmentTier.TEST)
        preprod = manager.create_environment("preprod", EnvironmentTier.PRE_PROD)

        # Dev has auto_deploy
        assert dev.config.auto_deploy is True
        # Test has sanitized data
        assert test.config.data_source == "sanitized"
        # Pre-prod requires approval
        assert preprod.config.require_approval is True
