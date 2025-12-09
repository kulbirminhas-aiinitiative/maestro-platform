"""
Tests for Pre-commit Hook Configuration module (MD-2382 AC-4).

Verifies:
- Configuration generation
- Template usage
- Policy enforcement
- Validation functionality
"""

import pytest
from pathlib import Path
import tempfile
import yaml

from maestro_hive.blocks.templates.cicd.precommit import (
    PreCommitConfig,
    PreCommitManager,
    PreCommitTemplate,
    HookDefinition,
    HookType,
    HookStage,
    Language,
    Repository,
    EnforcementPolicy,
    ValidationResult,
    create_python_config,
    create_javascript_config,
    create_security_config,
    validate_project_config,
)


class TestHookDefinition:
    """Tests for HookDefinition dataclass."""

    def test_basic_hook(self):
        """Test creating a basic hook definition."""
        hook = HookDefinition(
            id="my-hook",
            name="My Custom Hook",
            description="Does something useful",
            hook_type=HookType.LINTING,
            entry="my-linter"
        )
        assert hook.id == "my-hook"
        assert hook.name == "My Custom Hook"
        assert hook.hook_type == HookType.LINTING
        assert hook.language == Language.SYSTEM  # default

    def test_hook_with_args(self):
        """Test hook with arguments."""
        hook = HookDefinition(
            id="ruff",
            name="Ruff Linter",
            description="Fast Python linter",
            hook_type=HookType.LINTING,
            entry="ruff check",
            language=Language.PYTHON,
            args=["--fix", "--select=E,F,W"],
            files=r"\.py$"
        )
        assert hook.args == ["--fix", "--select=E,F,W"]
        assert hook.files == r"\.py$"

    def test_hook_to_dict(self):
        """Test converting hook to dictionary."""
        hook = HookDefinition(
            id="test-hook",
            name="Test Hook",
            description="Test",
            hook_type=HookType.TESTING,
            entry="pytest",
            language=Language.PYTHON,
            args=["--verbose"]
        )
        result = hook.to_dict()
        assert result["id"] == "test-hook"
        assert result["name"] == "Test Hook"
        assert result["entry"] == "pytest"
        assert result["language"] == "python"
        assert result["args"] == ["--verbose"]

    def test_hook_with_stages(self):
        """Test hook with custom stages."""
        hook = HookDefinition(
            id="push-check",
            name="Push Check",
            description="Run before push",
            hook_type=HookType.TESTING,
            entry="./scripts/check.sh",
            stages=[HookStage.PRE_PUSH]
        )
        result = hook.to_dict()
        assert "stages" in result
        assert result["stages"] == ["pre-push"]


class TestRepository:
    """Tests for Repository dataclass."""

    def test_repository_creation(self):
        """Test creating a repository configuration."""
        repo = Repository(
            repo="https://github.com/pre-commit/pre-commit-hooks",
            rev="v4.5.0",
            hooks=[
                {"id": "trailing-whitespace"},
                {"id": "end-of-file-fixer"}
            ]
        )
        assert repo.repo == "https://github.com/pre-commit/pre-commit-hooks"
        assert repo.rev == "v4.5.0"
        assert len(repo.hooks) == 2

    def test_repository_to_dict(self):
        """Test converting repository to dictionary."""
        repo = Repository(
            repo="https://github.com/psf/black",
            rev="24.3.0",
            hooks=[{"id": "black"}]
        )
        result = repo.to_dict()
        assert result["repo"] == "https://github.com/psf/black"
        assert result["rev"] == "24.3.0"
        assert result["hooks"] == [{"id": "black"}]


class TestPreCommitConfig:
    """Tests for PreCommitConfig dataclass."""

    def test_basic_config(self):
        """Test creating a basic configuration."""
        config = PreCommitConfig(
            repos=[
                Repository(
                    repo="https://github.com/pre-commit/pre-commit-hooks",
                    rev="v4.5.0",
                    hooks=[{"id": "trailing-whitespace"}]
                )
            ]
        )
        assert len(config.repos) == 1
        assert config.fail_fast is False  # default

    def test_config_with_options(self):
        """Test configuration with all options."""
        config = PreCommitConfig(
            repos=[],
            default_language_version={"python": "python3.11"},
            default_stages=["pre-commit", "pre-push"],
            exclude="^vendor/",
            fail_fast=True,
            ci={"autofix_prs": True}
        )
        assert config.default_language_version == {"python": "python3.11"}
        assert config.fail_fast is True
        assert config.ci == {"autofix_prs": True}

    def test_config_to_dict(self):
        """Test converting configuration to dictionary."""
        config = PreCommitConfig(
            repos=[
                Repository(
                    repo="local",
                    rev="",
                    hooks=[{"id": "test"}]
                )
            ],
            fail_fast=True
        )
        result = config.to_dict()
        assert "repos" in result
        assert result["fail_fast"] is True

    def test_config_to_yaml(self):
        """Test generating YAML output."""
        config = PreCommitConfig(
            repos=[
                Repository(
                    repo="https://github.com/pre-commit/pre-commit-hooks",
                    rev="v4.5.0",
                    hooks=[{"id": "trailing-whitespace"}]
                )
            ]
        )
        yaml_output = config.to_yaml()
        assert "repos:" in yaml_output
        assert "pre-commit-hooks" in yaml_output
        assert "trailing-whitespace" in yaml_output


class TestPreCommitTemplate:
    """Tests for PreCommitTemplate."""

    def test_python_standard(self):
        """Test Python standard template."""
        config = PreCommitTemplate.get_template(PreCommitTemplate.PYTHON_STANDARD)
        assert len(config.repos) >= 3  # At least hooks, black, ruff
        assert config.default_language_version is not None

    def test_python_strict(self):
        """Test Python strict template."""
        config = PreCommitTemplate.get_template(PreCommitTemplate.PYTHON_STRICT)
        assert config.fail_fast is True
        # Should have security hooks
        repo_urls = [r.repo for r in config.repos]
        assert any("bandit" in url or "detect-secrets" in url for url in repo_urls)

    def test_javascript_standard(self):
        """Test JavaScript standard template."""
        config = PreCommitTemplate.get_template(PreCommitTemplate.JAVASCRIPT_STANDARD)
        repo_urls = [r.repo for r in config.repos]
        assert any("eslint" in url or "prettier" in url for url in repo_urls)

    def test_typescript_strict(self):
        """Test TypeScript strict template."""
        config = PreCommitTemplate.get_template(PreCommitTemplate.TYPESCRIPT_STRICT)
        # Should include TypeScript checks
        assert len(config.repos) >= 2

    def test_multi_language(self):
        """Test multi-language template."""
        config = PreCommitTemplate.get_template(PreCommitTemplate.MULTI_LANGUAGE)
        assert "pre-commit" in config.default_stages
        assert "pre-push" in config.default_stages

    def test_security_focused(self):
        """Test security-focused template."""
        config = PreCommitTemplate.get_template(PreCommitTemplate.SECURITY_FOCUSED)
        assert config.fail_fast is True
        repo_urls = [r.repo for r in config.repos]
        # Should have multiple security tools
        security_repos = [u for u in repo_urls if any(
            s in u for s in ["detect-secrets", "gitleaks", "bandit", "safety"]
        )]
        assert len(security_repos) >= 2

    def test_minimal(self):
        """Test minimal template."""
        config = PreCommitTemplate.get_template(PreCommitTemplate.MINIMAL)
        assert len(config.repos) == 1  # Just pre-commit-hooks

    def test_invalid_template_raises(self):
        """Test that invalid template name raises ValueError."""
        with pytest.raises(ValueError):
            PreCommitTemplate.get_template("nonexistent")


class TestEnforcementPolicy:
    """Tests for EnforcementPolicy dataclass."""

    def test_default_policy(self):
        """Test default policy values."""
        policy = EnforcementPolicy()
        assert policy.minimum_hook_count == 4
        assert policy.require_security_hooks is True
        assert policy.require_secret_detection is True

    def test_custom_policy(self):
        """Test custom policy configuration."""
        policy = EnforcementPolicy(
            minimum_hook_count=10,
            require_security_hooks=True,
            require_formatting_hooks=True,
            require_linting_hooks=True,
            require_secret_detection=True,
            enforce_fail_fast=True
        )
        assert policy.minimum_hook_count == 10
        assert policy.enforce_fail_fast is True

    def test_required_repos(self):
        """Test required repositories in policy."""
        policy = EnforcementPolicy()
        assert "https://github.com/pre-commit/pre-commit-hooks" in policy.required_repos


class TestValidationResult:
    """Tests for ValidationResult dataclass."""

    def test_passing_result(self):
        """Test a passing validation result."""
        result = ValidationResult(
            valid=True,
            score=95.0,
            issues=[],
            warnings=["Consider adding more hooks"],
            recommendations=["Add type checking"]
        )
        assert result.valid is True
        assert result.score == 95.0
        assert len(result.issues) == 0

    def test_failing_result(self):
        """Test a failing validation result."""
        result = ValidationResult(
            valid=False,
            score=45.0,
            issues=["Missing security hooks", "Missing linting"],
            hook_coverage={"security": False, "linting": False}
        )
        assert result.valid is False
        assert len(result.issues) == 2

    def test_result_to_dict(self):
        """Test converting result to dictionary."""
        result = ValidationResult(
            valid=True,
            score=100.0,
            hook_coverage={"security": True, "linting": True}
        )
        result_dict = result.to_dict()
        assert result_dict["valid"] is True
        assert result_dict["score"] == 100.0
        assert result_dict["hook_coverage"]["security"] is True


class TestPreCommitManager:
    """Tests for PreCommitManager."""

    @pytest.fixture
    def manager(self):
        """Create a manager instance."""
        return PreCommitManager()

    @pytest.fixture
    def strict_policy_manager(self):
        """Create a manager with strict policy."""
        policy = EnforcementPolicy(
            minimum_hook_count=8,
            require_security_hooks=True,
            require_secret_detection=True,
            require_linting_hooks=True,
            require_formatting_hooks=True,
            enforce_fail_fast=True
        )
        return PreCommitManager(policy=policy)

    def test_manager_initialization(self, manager):
        """Test manager initialization."""
        assert manager.policy is not None
        assert len(manager._audit_log) == 0

    def test_generate_config_from_template(self, manager):
        """Test generating config from template."""
        config = manager.generate_config(template=PreCommitTemplate.PYTHON_STANDARD)
        assert len(config.repos) >= 3

    def test_generate_config_with_custom_hooks(self, manager):
        """Test generating config with custom hooks."""
        custom_hook = HookDefinition(
            id="custom-check",
            name="Custom Check",
            description="My custom check",
            hook_type=HookType.CUSTOM,
            entry="./scripts/custom-check.sh"
        )
        config = manager.generate_config(
            template=PreCommitTemplate.MINIMAL,
            custom_hooks=[custom_hook]
        )
        # Should have minimal repos + local repo with custom hook
        assert len(config.repos) >= 2

    def test_generate_config_with_overrides(self, manager):
        """Test generating config with overrides."""
        config = manager.generate_config(
            template=PreCommitTemplate.MINIMAL,
            overrides={"fail_fast": True, "exclude": "^tests/"}
        )
        assert config.fail_fast is True
        assert config.exclude == "^tests/"

    def test_validate_good_config(self, manager):
        """Test validating a good configuration."""
        config = PreCommitTemplate.get_template(PreCommitTemplate.PYTHON_STRICT)
        result = manager.validate_config(config)
        assert result.valid is True
        assert result.score >= 80

    def test_validate_minimal_config(self, manager):
        """Test validating a minimal configuration."""
        config = PreCommitTemplate.get_template(PreCommitTemplate.MINIMAL)
        result = manager.validate_config(config)
        # Minimal config should have issues
        assert len(result.issues) > 0 or result.score < 100

    def test_validate_empty_config(self, manager):
        """Test validating an empty configuration."""
        config = PreCommitConfig(repos=[])
        result = manager.validate_config(config)
        assert result.valid is False
        assert result.score < 50

    def test_write_config(self, manager):
        """Test writing configuration to file."""
        config = PreCommitTemplate.get_template(PreCommitTemplate.MINIMAL)

        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir)
            config_path = manager.write_config(config, path)

            assert config_path.exists()
            assert config_path.name == ".pre-commit-config.yaml"

            # Verify content
            content = yaml.safe_load(config_path.read_text())
            assert "repos" in content

    def test_write_config_with_backup(self, manager):
        """Test writing config creates backup of existing."""
        config = PreCommitTemplate.get_template(PreCommitTemplate.MINIMAL)

        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir)

            # Write first config
            manager.write_config(config, path, backup=False)

            # Write second config (should create backup)
            manager.write_config(config, path, backup=True)

            # Check for backup file
            backup_files = list(path.glob(".pre-commit-config.yaml.backup.*"))
            assert len(backup_files) == 1

    def test_parse_config(self, manager):
        """Test parsing existing configuration file."""
        config = PreCommitTemplate.get_template(PreCommitTemplate.MINIMAL)

        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir)
            manager.write_config(config, path)

            # Parse it back
            parsed = manager.parse_config(path)
            assert len(parsed.repos) == len(config.repos)

    def test_parse_nonexistent_config(self, manager):
        """Test parsing non-existent configuration raises error."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir)
            with pytest.raises(FileNotFoundError):
                manager.parse_config(path)

    def test_generate_enforcement_report(self, manager):
        """Test generating enforcement report."""
        config = PreCommitTemplate.get_template(PreCommitTemplate.PYTHON_STRICT)
        validation = manager.validate_config(config)
        report = manager.generate_enforcement_report(config, validation)

        assert "timestamp" in report
        assert "validation" in report
        assert "policy" in report
        assert "configuration" in report
        assert "compliance_status" in report
        assert "integrity_hash" in report

    def test_audit_log(self, manager):
        """Test audit logging functionality."""
        manager.generate_config(template=PreCommitTemplate.MINIMAL)
        config = PreCommitTemplate.get_template(PreCommitTemplate.MINIMAL)
        manager.validate_config(config)

        audit_log = manager.get_audit_log()
        assert len(audit_log) >= 2
        assert all("timestamp" in entry for entry in audit_log)
        assert all("action" in entry for entry in audit_log)

    def test_hook_coverage_detection(self, manager):
        """Test that hook coverage is properly detected."""
        config = PreCommitTemplate.get_template(PreCommitTemplate.PYTHON_STRICT)
        result = manager.validate_config(config)

        assert result.hook_coverage["linting"] is True
        assert result.hook_coverage["formatting"] is True
        assert result.hook_coverage["security"] is True
        assert result.hook_coverage["secret_detection"] is True


class TestConvenienceFunctions:
    """Tests for convenience functions."""

    def test_create_python_config(self):
        """Test create_python_config function."""
        config = create_python_config()
        assert len(config.repos) >= 3

    def test_create_python_config_strict(self):
        """Test create_python_config with strict mode."""
        config = create_python_config(strict=True)
        assert config.fail_fast is True

    def test_create_javascript_config(self):
        """Test create_javascript_config function."""
        config = create_javascript_config()
        repo_urls = [r.repo for r in config.repos]
        assert any("prettier" in url or "eslint" in url for url in repo_urls)

    def test_create_javascript_config_typescript(self):
        """Test create_javascript_config with TypeScript."""
        config = create_javascript_config(typescript=True)
        # TypeScript config should have tsc check
        all_hooks = []
        for repo in config.repos:
            all_hooks.extend(repo.hooks)
        hook_ids = [h.get("id", h.get("name", "")) for h in all_hooks]
        assert any("tsc" in h.lower() or "typescript" in h.lower() for h in hook_ids)

    def test_create_security_config(self):
        """Test create_security_config function."""
        config = create_security_config()
        assert config.fail_fast is True

    def test_validate_project_config(self):
        """Test validate_project_config function."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir)

            # Create a config file
            config = create_python_config(strict=True)
            manager = PreCommitManager()
            manager.write_config(config, path)

            # Validate it
            result = validate_project_config(path)
            assert isinstance(result, ValidationResult)
            assert result.valid is True


class TestPolicyEnforcement:
    """Tests for policy enforcement functionality."""

    def test_strict_policy_fails_minimal_config(self):
        """Test that strict policy fails minimal config."""
        strict_policy = EnforcementPolicy(
            minimum_hook_count=10,
            require_security_hooks=True,
            require_secret_detection=True
        )
        manager = PreCommitManager(policy=strict_policy)
        config = PreCommitTemplate.get_template(PreCommitTemplate.MINIMAL)
        result = manager.validate_config(config)

        assert result.valid is False

    def test_lenient_policy_passes_minimal_config(self):
        """Test that lenient policy passes minimal config."""
        lenient_policy = EnforcementPolicy(
            minimum_hook_count=1,
            require_security_hooks=False,
            require_secret_detection=False,
            require_linting_hooks=False,
            require_formatting_hooks=False
        )
        manager = PreCommitManager(policy=lenient_policy)
        config = PreCommitTemplate.get_template(PreCommitTemplate.MINIMAL)
        result = manager.validate_config(config)

        assert result.valid is True

    def test_required_repos_enforcement(self):
        """Test that required repositories are enforced."""
        policy = EnforcementPolicy(
            required_repos={"https://github.com/pre-commit/pre-commit-hooks"}
        )
        manager = PreCommitManager(policy=policy)

        # Config without required repo
        config = PreCommitConfig(
            repos=[
                Repository(
                    repo="https://github.com/psf/black",
                    rev="24.3.0",
                    hooks=[{"id": "black"}]
                )
            ]
        )
        result = manager.validate_config(config)
        assert "Missing required repositories" in str(result.issues)
