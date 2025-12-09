"""
Pre-commit Hook Configuration Generator and Enforcement Module.

This module provides comprehensive pre-commit hook management for
standardized code quality enforcement across repositories.

Implements AC-4: Pre-commit Hook Enforcement for MD-2382
Quality Fabric & Evolutionary Templates (Conductor Integration)
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set
from pathlib import Path
import yaml
import json
import hashlib
from datetime import datetime


class HookType(Enum):
    """Types of pre-commit hooks."""
    LINTING = "linting"
    FORMATTING = "formatting"
    SECURITY = "security"
    TESTING = "testing"
    DOCUMENTATION = "documentation"
    COMMIT_MESSAGE = "commit_message"
    FILE_VALIDATION = "file_validation"
    SECRETS_DETECTION = "secrets_detection"
    TYPE_CHECKING = "type_checking"
    CUSTOM = "custom"


class HookStage(Enum):
    """Git hook stages for pre-commit."""
    PRE_COMMIT = "pre-commit"
    PRE_PUSH = "pre-push"
    COMMIT_MSG = "commit-msg"
    PRE_MERGE_COMMIT = "pre-merge-commit"
    POST_CHECKOUT = "post-checkout"
    POST_MERGE = "post-merge"


class Language(Enum):
    """Supported languages for hooks."""
    PYTHON = "python"
    NODE = "node"
    SYSTEM = "system"
    RUBY = "ruby"
    GOLANG = "golang"
    RUST = "rust"
    DOCKER = "docker"
    SCRIPT = "script"


@dataclass
class HookDefinition:
    """Definition of a single pre-commit hook."""
    id: str
    name: str
    description: str
    hook_type: HookType
    entry: str
    language: Language = Language.SYSTEM
    files: Optional[str] = None
    exclude: Optional[str] = None
    types: Optional[List[str]] = None
    types_or: Optional[List[str]] = None
    args: Optional[List[str]] = None
    additional_dependencies: Optional[List[str]] = None
    stages: List[HookStage] = field(default_factory=lambda: [HookStage.PRE_COMMIT])
    pass_filenames: bool = True
    require_serial: bool = False
    always_run: bool = False
    verbose: bool = False
    minimum_pre_commit_version: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert hook definition to pre-commit config format."""
        result = {
            "id": self.id,
            "name": self.name,
            "entry": self.entry,
            "language": self.language.value,
        }

        if self.files:
            result["files"] = self.files
        if self.exclude:
            result["exclude"] = self.exclude
        if self.types:
            result["types"] = self.types
        if self.types_or:
            result["types_or"] = self.types_or
        if self.args:
            result["args"] = self.args
        if self.additional_dependencies:
            result["additional_dependencies"] = self.additional_dependencies
        if self.stages != [HookStage.PRE_COMMIT]:
            result["stages"] = [s.value for s in self.stages]
        if not self.pass_filenames:
            result["pass_filenames"] = False
        if self.require_serial:
            result["require_serial"] = True
        if self.always_run:
            result["always_run"] = True
        if self.verbose:
            result["verbose"] = True
        if self.minimum_pre_commit_version:
            result["minimum_pre_commit_version"] = self.minimum_pre_commit_version

        return result


@dataclass
class Repository:
    """Pre-commit repository configuration."""
    repo: str
    rev: str
    hooks: List[Dict[str, Any]]

    def to_dict(self) -> Dict[str, Any]:
        """Convert repository to config format."""
        return {
            "repo": self.repo,
            "rev": self.rev,
            "hooks": self.hooks
        }


@dataclass
class PreCommitConfig:
    """Complete pre-commit configuration."""
    repos: List[Repository] = field(default_factory=list)
    default_language_version: Optional[Dict[str, str]] = None
    default_stages: Optional[List[str]] = None
    files: Optional[str] = None
    exclude: Optional[str] = None
    fail_fast: bool = False
    minimum_pre_commit_version: Optional[str] = None
    ci: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to YAML-serializable dict."""
        result: Dict[str, Any] = {}

        if self.default_language_version:
            result["default_language_version"] = self.default_language_version
        if self.default_stages:
            result["default_stages"] = self.default_stages
        if self.files:
            result["files"] = self.files
        if self.exclude:
            result["exclude"] = self.exclude
        if self.fail_fast:
            result["fail_fast"] = True
        if self.minimum_pre_commit_version:
            result["minimum_pre_commit_version"] = self.minimum_pre_commit_version
        if self.ci:
            result["ci"] = self.ci

        result["repos"] = [repo.to_dict() for repo in self.repos]

        return result

    def to_yaml(self) -> str:
        """Generate YAML configuration string."""
        return yaml.dump(
            self.to_dict(),
            default_flow_style=False,
            sort_keys=False,
            allow_unicode=True
        )


class PreCommitTemplate:
    """Pre-defined pre-commit configuration templates."""

    PYTHON_STANDARD = "python_standard"
    PYTHON_STRICT = "python_strict"
    JAVASCRIPT_STANDARD = "javascript_standard"
    TYPESCRIPT_STRICT = "typescript_strict"
    MULTI_LANGUAGE = "multi_language"
    SECURITY_FOCUSED = "security_focused"
    MINIMAL = "minimal"

    @classmethod
    def get_template(cls, name: str) -> PreCommitConfig:
        """Get a pre-defined template configuration."""
        templates = {
            cls.PYTHON_STANDARD: cls._python_standard(),
            cls.PYTHON_STRICT: cls._python_strict(),
            cls.JAVASCRIPT_STANDARD: cls._javascript_standard(),
            cls.TYPESCRIPT_STRICT: cls._typescript_strict(),
            cls.MULTI_LANGUAGE: cls._multi_language(),
            cls.SECURITY_FOCUSED: cls._security_focused(),
            cls.MINIMAL: cls._minimal(),
        }

        if name not in templates:
            raise ValueError(f"Unknown template: {name}. Available: {list(templates.keys())}")

        return templates[name]

    @classmethod
    def _python_standard(cls) -> PreCommitConfig:
        """Standard Python pre-commit configuration."""
        return PreCommitConfig(
            default_language_version={"python": "python3.11"},
            repos=[
                Repository(
                    repo="https://github.com/pre-commit/pre-commit-hooks",
                    rev="v4.5.0",
                    hooks=[
                        {"id": "trailing-whitespace"},
                        {"id": "end-of-file-fixer"},
                        {"id": "check-yaml"},
                        {"id": "check-json"},
                        {"id": "check-added-large-files", "args": ["--maxkb=500"]},
                        {"id": "check-merge-conflict"},
                        {"id": "debug-statements"},
                        {"id": "check-toml"},
                    ]
                ),
                Repository(
                    repo="https://github.com/psf/black",
                    rev="24.3.0",
                    hooks=[
                        {"id": "black", "language_version": "python3.11"}
                    ]
                ),
                Repository(
                    repo="https://github.com/astral-sh/ruff-pre-commit",
                    rev="v0.3.4",
                    hooks=[
                        {"id": "ruff", "args": ["--fix"]},
                        {"id": "ruff-format"}
                    ]
                ),
                Repository(
                    repo="https://github.com/pre-commit/mirrors-mypy",
                    rev="v1.9.0",
                    hooks=[
                        {
                            "id": "mypy",
                            "additional_dependencies": ["types-all"],
                            "args": ["--ignore-missing-imports"]
                        }
                    ]
                ),
            ]
        )

    @classmethod
    def _python_strict(cls) -> PreCommitConfig:
        """Strict Python pre-commit configuration with security checks."""
        config = cls._python_standard()

        # Add security scanning
        config.repos.append(
            Repository(
                repo="https://github.com/PyCQA/bandit",
                rev="1.7.8",
                hooks=[
                    {
                        "id": "bandit",
                        "args": ["-c", "pyproject.toml", "-r", "."],
                        "exclude": "tests/"
                    }
                ]
            )
        )

        # Add secret detection
        config.repos.append(
            Repository(
                repo="https://github.com/Yelp/detect-secrets",
                rev="v1.4.0",
                hooks=[
                    {"id": "detect-secrets", "args": ["--baseline", ".secrets.baseline"]}
                ]
            )
        )

        # Add commit message linting
        config.repos.append(
            Repository(
                repo="https://github.com/commitizen-tools/commitizen",
                rev="v3.21.3",
                hooks=[
                    {"id": "commitizen", "stages": ["commit-msg"]}
                ]
            )
        )

        config.fail_fast = True
        return config

    @classmethod
    def _javascript_standard(cls) -> PreCommitConfig:
        """Standard JavaScript/Node pre-commit configuration."""
        return PreCommitConfig(
            repos=[
                Repository(
                    repo="https://github.com/pre-commit/pre-commit-hooks",
                    rev="v4.5.0",
                    hooks=[
                        {"id": "trailing-whitespace"},
                        {"id": "end-of-file-fixer"},
                        {"id": "check-json"},
                        {"id": "check-added-large-files"},
                    ]
                ),
                Repository(
                    repo="https://github.com/pre-commit/mirrors-eslint",
                    rev="v8.57.0",
                    hooks=[
                        {
                            "id": "eslint",
                            "files": r"\.[jt]sx?$",
                            "types": ["file"],
                            "additional_dependencies": [
                                "eslint@8.57.0",
                                "eslint-config-prettier@9.1.0"
                            ]
                        }
                    ]
                ),
                Repository(
                    repo="https://github.com/pre-commit/mirrors-prettier",
                    rev="v4.0.0-alpha.8",
                    hooks=[
                        {"id": "prettier", "types_or": ["javascript", "typescript", "json", "yaml"]}
                    ]
                ),
            ]
        )

    @classmethod
    def _typescript_strict(cls) -> PreCommitConfig:
        """Strict TypeScript pre-commit configuration."""
        config = cls._javascript_standard()

        # Add TypeScript specific checks
        config.repos.append(
            Repository(
                repo="local",
                rev="",  # Local hooks don't need rev
                hooks=[
                    {
                        "id": "tsc",
                        "name": "TypeScript Compile Check",
                        "entry": "npx tsc --noEmit",
                        "language": "system",
                        "files": r"\.tsx?$",
                        "pass_filenames": False
                    }
                ]
            )
        )

        return config

    @classmethod
    def _multi_language(cls) -> PreCommitConfig:
        """Multi-language pre-commit configuration."""
        return PreCommitConfig(
            default_stages=["pre-commit", "pre-push"],
            repos=[
                Repository(
                    repo="https://github.com/pre-commit/pre-commit-hooks",
                    rev="v4.5.0",
                    hooks=[
                        {"id": "trailing-whitespace"},
                        {"id": "end-of-file-fixer"},
                        {"id": "check-yaml"},
                        {"id": "check-json"},
                        {"id": "check-toml"},
                        {"id": "check-xml"},
                        {"id": "check-added-large-files", "args": ["--maxkb=1000"]},
                        {"id": "check-merge-conflict"},
                        {"id": "check-case-conflict"},
                        {"id": "check-symlinks"},
                        {"id": "mixed-line-ending", "args": ["--fix=lf"]},
                    ]
                ),
                # Python
                Repository(
                    repo="https://github.com/astral-sh/ruff-pre-commit",
                    rev="v0.3.4",
                    hooks=[
                        {"id": "ruff", "types": ["python"]},
                        {"id": "ruff-format", "types": ["python"]}
                    ]
                ),
                # JavaScript/TypeScript
                Repository(
                    repo="https://github.com/pre-commit/mirrors-prettier",
                    rev="v4.0.0-alpha.8",
                    hooks=[
                        {"id": "prettier", "types_or": ["javascript", "typescript", "json", "yaml", "markdown"]}
                    ]
                ),
                # Shell scripts
                Repository(
                    repo="https://github.com/shellcheck-py/shellcheck-py",
                    rev="v0.10.0.1",
                    hooks=[
                        {"id": "shellcheck"}
                    ]
                ),
                # Dockerfile
                Repository(
                    repo="https://github.com/hadolint/hadolint",
                    rev="v2.12.0",
                    hooks=[
                        {"id": "hadolint-docker"}
                    ]
                ),
            ]
        )

    @classmethod
    def _security_focused(cls) -> PreCommitConfig:
        """Security-focused pre-commit configuration."""
        return PreCommitConfig(
            fail_fast=True,
            repos=[
                Repository(
                    repo="https://github.com/pre-commit/pre-commit-hooks",
                    rev="v4.5.0",
                    hooks=[
                        {"id": "check-added-large-files", "args": ["--maxkb=100"]},
                        {"id": "detect-private-key"},
                        {"id": "check-merge-conflict"},
                    ]
                ),
                # Secret detection
                Repository(
                    repo="https://github.com/Yelp/detect-secrets",
                    rev="v1.4.0",
                    hooks=[
                        {"id": "detect-secrets", "args": ["--baseline", ".secrets.baseline"]}
                    ]
                ),
                # Gitleaks for comprehensive secret scanning
                Repository(
                    repo="https://github.com/gitleaks/gitleaks",
                    rev="v8.18.2",
                    hooks=[
                        {"id": "gitleaks"}
                    ]
                ),
                # Python security
                Repository(
                    repo="https://github.com/PyCQA/bandit",
                    rev="1.7.8",
                    hooks=[
                        {"id": "bandit", "args": ["-ll", "-r", "."], "exclude": "tests/"}
                    ]
                ),
                # Dependency vulnerability scanning
                Repository(
                    repo="https://github.com/Lucas-C/pre-commit-hooks-safety",
                    rev="v1.3.3",
                    hooks=[
                        {"id": "python-safety-dependencies-check"}
                    ]
                ),
                # YAML security
                Repository(
                    repo="https://github.com/adrienverge/yamllint",
                    rev="v1.35.1",
                    hooks=[
                        {"id": "yamllint", "args": ["-d", "{extends: relaxed, rules: {line-length: disable}}"]}
                    ]
                ),
            ],
            ci={
                "autofix_commit_msg": "[pre-commit.ci] auto fixes",
                "autofix_prs": True,
                "autoupdate_commit_msg": "[pre-commit.ci] dependency update",
                "autoupdate_schedule": "weekly",
                "skip": ["gitleaks"],  # Skip in CI if needed
                "submodules": False
            }
        )

    @classmethod
    def _minimal(cls) -> PreCommitConfig:
        """Minimal pre-commit configuration for quick setup."""
        return PreCommitConfig(
            repos=[
                Repository(
                    repo="https://github.com/pre-commit/pre-commit-hooks",
                    rev="v4.5.0",
                    hooks=[
                        {"id": "trailing-whitespace"},
                        {"id": "end-of-file-fixer"},
                        {"id": "check-yaml"},
                        {"id": "check-added-large-files"},
                    ]
                ),
            ]
        )


@dataclass
class EnforcementPolicy:
    """Policy for pre-commit enforcement."""
    required_hooks: Set[str] = field(default_factory=set)
    minimum_hook_count: int = 4
    require_security_hooks: bool = True
    require_formatting_hooks: bool = True
    require_linting_hooks: bool = True
    require_secret_detection: bool = True
    allowed_custom_hooks: bool = True
    max_hook_timeout: int = 120  # seconds
    require_ci_integration: bool = False
    enforce_fail_fast: bool = False

    # Specific required repositories
    required_repos: Set[str] = field(default_factory=lambda: {
        "https://github.com/pre-commit/pre-commit-hooks"
    })

    # Banned patterns (security risk)
    banned_patterns: Set[str] = field(default_factory=lambda: {
        "curl.*|.*bash",  # Dangerous remote execution
        "wget.*|.*sh",
    })


@dataclass
class ValidationResult:
    """Result of pre-commit configuration validation."""
    valid: bool
    score: float
    issues: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    hook_coverage: Dict[str, bool] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "valid": self.valid,
            "score": self.score,
            "issues": self.issues,
            "warnings": self.warnings,
            "recommendations": self.recommendations,
            "hook_coverage": self.hook_coverage
        }


class PreCommitManager:
    """Manager for pre-commit hook configuration and enforcement."""

    def __init__(self, policy: Optional[EnforcementPolicy] = None):
        """Initialize manager with optional enforcement policy."""
        self.policy = policy or EnforcementPolicy()
        self._audit_log: List[Dict[str, Any]] = []

    def generate_config(
        self,
        template: str = PreCommitTemplate.PYTHON_STANDARD,
        custom_hooks: Optional[List[HookDefinition]] = None,
        overrides: Optional[Dict[str, Any]] = None
    ) -> PreCommitConfig:
        """Generate pre-commit configuration from template with customizations."""
        config = PreCommitTemplate.get_template(template)

        # Add custom hooks
        if custom_hooks:
            local_hooks = []
            for hook in custom_hooks:
                local_hooks.append(hook.to_dict())

            if local_hooks:
                config.repos.append(
                    Repository(
                        repo="local",
                        rev="",
                        hooks=local_hooks
                    )
                )

        # Apply overrides
        if overrides:
            if "fail_fast" in overrides:
                config.fail_fast = overrides["fail_fast"]
            if "exclude" in overrides:
                config.exclude = overrides["exclude"]
            if "default_stages" in overrides:
                config.default_stages = overrides["default_stages"]

        self._log_action("generate_config", {
            "template": template,
            "custom_hooks_count": len(custom_hooks) if custom_hooks else 0,
            "has_overrides": bool(overrides)
        })

        return config

    def validate_config(self, config: PreCommitConfig) -> ValidationResult:
        """Validate pre-commit configuration against enforcement policy."""
        issues = []
        warnings = []
        recommendations = []
        hook_coverage = {
            "linting": False,
            "formatting": False,
            "security": False,
            "secret_detection": False,
            "file_validation": False
        }

        # Count hooks and repos
        total_hooks = sum(len(repo.hooks) for repo in config.repos)
        repo_urls = {repo.repo for repo in config.repos}

        # Check minimum hook count
        if total_hooks < self.policy.minimum_hook_count:
            issues.append(
                f"Insufficient hooks: {total_hooks} < {self.policy.minimum_hook_count} required"
            )

        # Check required repos
        missing_repos = self.policy.required_repos - repo_urls
        if missing_repos:
            issues.append(f"Missing required repositories: {missing_repos}")

        # Analyze hooks for coverage
        all_hook_ids = set()
        for repo in config.repos:
            for hook in repo.hooks:
                hook_id = hook.get("id", "")
                all_hook_ids.add(hook_id)

                # Check for linting hooks
                if any(x in hook_id for x in ["ruff", "eslint", "pylint", "flake8"]):
                    hook_coverage["linting"] = True

                # Check for formatting hooks
                if any(x in hook_id for x in ["black", "prettier", "autopep8", "ruff-format"]):
                    hook_coverage["formatting"] = True

                # Check for security hooks
                if any(x in hook_id for x in ["bandit", "safety", "semgrep"]):
                    hook_coverage["security"] = True

                # Check for secret detection
                if any(x in hook_id for x in ["detect-secrets", "gitleaks", "trufflehog"]):
                    hook_coverage["secret_detection"] = True

                # Check for file validation
                if any(x in hook_id for x in ["check-yaml", "check-json", "check-toml"]):
                    hook_coverage["file_validation"] = True

        # Validate required hook types
        if self.policy.require_linting_hooks and not hook_coverage["linting"]:
            issues.append("Missing required linting hooks")

        if self.policy.require_formatting_hooks and not hook_coverage["formatting"]:
            issues.append("Missing required formatting hooks")

        if self.policy.require_security_hooks and not hook_coverage["security"]:
            issues.append("Missing required security hooks")

        if self.policy.require_secret_detection and not hook_coverage["secret_detection"]:
            issues.append("Missing required secret detection hooks")

        # Check fail_fast policy
        if self.policy.enforce_fail_fast and not config.fail_fast:
            warnings.append("fail_fast is recommended but not enabled")

        # Check CI integration
        if self.policy.require_ci_integration and not config.ci:
            warnings.append("CI integration is recommended")

        # Recommendations
        if not hook_coverage["file_validation"]:
            recommendations.append("Consider adding file validation hooks (check-yaml, check-json)")

        if "trailing-whitespace" not in all_hook_ids:
            recommendations.append("Consider adding trailing-whitespace hook")

        if "end-of-file-fixer" not in all_hook_ids:
            recommendations.append("Consider adding end-of-file-fixer hook")

        # Calculate score
        score = 100.0
        score -= len(issues) * 15
        score -= len(warnings) * 5
        score += sum(1 for v in hook_coverage.values() if v) * 5
        score = max(0, min(100, score))

        result = ValidationResult(
            valid=len(issues) == 0,
            score=score,
            issues=issues,
            warnings=warnings,
            recommendations=recommendations,
            hook_coverage=hook_coverage
        )

        self._log_action("validate_config", {
            "valid": result.valid,
            "score": result.score,
            "issues_count": len(issues)
        })

        return result

    def write_config(
        self,
        config: PreCommitConfig,
        path: Path,
        backup: bool = True
    ) -> Path:
        """Write pre-commit configuration to file."""
        config_path = path / ".pre-commit-config.yaml"

        # Backup existing config
        if backup and config_path.exists():
            backup_path = config_path.with_suffix(
                f".yaml.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            )
            backup_path.write_text(config_path.read_text())

        # Write new config
        config_path.write_text(config.to_yaml())

        self._log_action("write_config", {
            "path": str(config_path),
            "backup": backup
        })

        return config_path

    def parse_config(self, path: Path) -> PreCommitConfig:
        """Parse existing pre-commit configuration file."""
        config_path = path / ".pre-commit-config.yaml" if path.is_dir() else path

        if not config_path.exists():
            raise FileNotFoundError(f"Pre-commit config not found: {config_path}")

        with open(config_path) as f:
            data = yaml.safe_load(f)

        repos = []
        for repo_data in data.get("repos", []):
            repos.append(Repository(
                repo=repo_data["repo"],
                rev=repo_data.get("rev", ""),
                hooks=repo_data.get("hooks", [])
            ))

        return PreCommitConfig(
            repos=repos,
            default_language_version=data.get("default_language_version"),
            default_stages=data.get("default_stages"),
            files=data.get("files"),
            exclude=data.get("exclude"),
            fail_fast=data.get("fail_fast", False),
            minimum_pre_commit_version=data.get("minimum_pre_commit_version"),
            ci=data.get("ci")
        )

    def generate_enforcement_report(
        self,
        config: PreCommitConfig,
        validation: ValidationResult
    ) -> Dict[str, Any]:
        """Generate comprehensive enforcement report."""
        report = {
            "timestamp": datetime.now().isoformat(),
            "validation": validation.to_dict(),
            "policy": {
                "minimum_hook_count": self.policy.minimum_hook_count,
                "require_security_hooks": self.policy.require_security_hooks,
                "require_secret_detection": self.policy.require_secret_detection,
                "require_linting_hooks": self.policy.require_linting_hooks,
                "require_formatting_hooks": self.policy.require_formatting_hooks
            },
            "configuration": {
                "total_repos": len(config.repos),
                "total_hooks": sum(len(r.hooks) for r in config.repos),
                "fail_fast": config.fail_fast,
                "has_ci": bool(config.ci)
            },
            "compliance_status": "PASS" if validation.valid else "FAIL",
            "score": validation.score,
            "recommendations": validation.recommendations
        }

        # Generate hash for integrity
        report_json = json.dumps(report, sort_keys=True)
        report["integrity_hash"] = hashlib.sha256(report_json.encode()).hexdigest()

        return report

    def get_audit_log(self) -> List[Dict[str, Any]]:
        """Get audit log of manager actions."""
        return self._audit_log.copy()

    def _log_action(self, action: str, details: Dict[str, Any]) -> None:
        """Log an action to the audit log."""
        self._audit_log.append({
            "timestamp": datetime.now().isoformat(),
            "action": action,
            "details": details
        })


# Convenience functions for common operations
def create_python_config(strict: bool = False) -> PreCommitConfig:
    """Create a Python pre-commit configuration."""
    template = PreCommitTemplate.PYTHON_STRICT if strict else PreCommitTemplate.PYTHON_STANDARD
    return PreCommitTemplate.get_template(template)


def create_javascript_config(typescript: bool = False) -> PreCommitConfig:
    """Create a JavaScript/TypeScript pre-commit configuration."""
    template = PreCommitTemplate.TYPESCRIPT_STRICT if typescript else PreCommitTemplate.JAVASCRIPT_STANDARD
    return PreCommitTemplate.get_template(template)


def create_security_config() -> PreCommitConfig:
    """Create a security-focused pre-commit configuration."""
    return PreCommitTemplate.get_template(PreCommitTemplate.SECURITY_FOCUSED)


def validate_project_config(
    project_path: Path,
    policy: Optional[EnforcementPolicy] = None
) -> ValidationResult:
    """Validate a project's pre-commit configuration."""
    manager = PreCommitManager(policy)
    config = manager.parse_config(project_path)
    return manager.validate_config(config)
