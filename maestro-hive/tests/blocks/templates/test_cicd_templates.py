"""
Tests for CI/CD Pipeline Templates

Reference: MD-2522 CI/CD Pipeline Templates

Tests cover all acceptance criteria:
- AC-1: Full pipeline suite for GitLab, Azure, Jenkins
- AC-2: Artifact management
- AC-3: Caching strategies
- AC-4: Matrix builds
- AC-5: Environment promotion
- AC-6: Rollback capability
"""

import pytest
import yaml
from typing import Dict, Any

from maestro_hive.blocks.templates.cicd import (
    # Enums
    PipelineType,
    Platform,
    # Models
    Step,
    Job,
    Stage,
    CacheConfig,
    ArtifactConfig,
    MatrixConfig,
    Environment,
    RollbackConfig,
    HealthCheck,
    PipelineTemplate,
    # GitLab
    GitLabPipeline,
    GitLabAdapter,
    # Azure
    AzurePipeline,
    AzureAdapter,
    # Jenkins
    JenkinsPipeline,
    JenkinsAdapter,
    # Registry
    PipelineRegistry,
    get_pipeline_registry,
)


# =============================================================================
# Test Fixtures
# =============================================================================

@pytest.fixture
def sample_steps():
    """Sample steps for testing."""
    return [
        Step(name="install", script="pip install -r requirements.txt"),
        Step(name="build", script="python setup.py build"),
        Step(name="test", script="pytest --cov"),
    ]


@pytest.fixture
def sample_cache():
    """Sample cache configuration (AC-3)."""
    return CacheConfig(
        key="${CI_COMMIT_REF_SLUG}",
        paths=[".cache/pip", "node_modules"],
        policy="pull-push",
        fallback_keys=["${CI_DEFAULT_BRANCH}"],
    )


@pytest.fixture
def sample_artifacts():
    """Sample artifact configuration (AC-2)."""
    return ArtifactConfig(
        paths=["dist/", "coverage/"],
        expire_in="1 week",
        reports={"junit": "report.xml"},
        upload_on_failure=True,
    )


@pytest.fixture
def sample_matrix():
    """Sample matrix configuration (AC-4)."""
    return MatrixConfig(
        dimensions={
            "python": ["3.9", "3.10", "3.11"],
            "os": ["ubuntu-latest", "windows-latest"],
        },
        fail_fast=True,
        max_parallel=4,
    )


@pytest.fixture
def sample_environment():
    """Sample environment configuration (AC-5)."""
    return Environment(
        name="production",
        url="https://app.example.com",
        requires_approval=True,
        approvers=["tech-lead", "devops"],
        protection_rules=["require_review"],
    )


@pytest.fixture
def sample_rollback():
    """Sample rollback configuration (AC-6)."""
    return RollbackConfig(
        enabled=True,
        strategy="previous_version",
        health_check=HealthCheck(
            endpoint="/health",
            expected_status=200,
            timeout="5m",
        ),
        max_attempts=3,
    )


# =============================================================================
# Model Tests
# =============================================================================

class TestPipelineEnums:
    """Test pipeline enums."""

    def test_pipeline_type_values(self):
        """Test PipelineType enum values."""
        assert PipelineType.BUILD.value == "build"
        assert PipelineType.TEST.value == "test"
        assert PipelineType.DEPLOY.value == "deploy"
        assert PipelineType.RELEASE.value == "release"

    def test_platform_values(self):
        """Test Platform enum values."""
        assert Platform.GITLAB.value == "gitlab"
        assert Platform.AZURE.value == "azure"
        assert Platform.JENKINS.value == "jenkins"
        assert Platform.GITHUB.value == "github"


class TestStep:
    """Test Step model."""

    def test_step_creation(self):
        """Test basic step creation."""
        step = Step(name="test", script="pytest")
        assert step.name == "test"
        assert step.script == "pytest"
        assert step.condition is None
        assert step.retry == 0

    def test_step_with_retry(self):
        """Test step with retry configuration."""
        step = Step(name="flaky-test", script="pytest", retry=3)
        assert step.retry == 3

    def test_step_to_dict(self):
        """Test step serialization."""
        step = Step(
            name="deploy",
            script="./deploy.sh",
            condition="$CI_COMMIT_BRANCH == 'main'",
            retry=2,
        )
        data = step.to_dict()
        assert data["name"] == "deploy"
        assert data["script"] == "./deploy.sh"
        assert data["condition"] == "$CI_COMMIT_BRANCH == 'main'"
        assert data["retry"] == 2


class TestCacheConfig:
    """Test CacheConfig model (AC-3)."""

    def test_cache_defaults(self):
        """Test default cache configuration."""
        cache = CacheConfig()
        assert cache.key == "${CI_COMMIT_REF_SLUG}"
        assert cache.policy == "pull-push"
        assert cache.paths == []

    def test_cache_with_paths(self, sample_cache):
        """Test cache with custom paths."""
        assert ".cache/pip" in sample_cache.paths
        assert "node_modules" in sample_cache.paths

    def test_cache_to_gitlab(self, sample_cache):
        """Test GitLab cache format conversion."""
        gitlab_cache = sample_cache.to_gitlab()
        assert "paths" in gitlab_cache
        assert gitlab_cache["policy"] == "pull-push"

    def test_cache_to_azure(self, sample_cache):
        """Test Azure cache format conversion."""
        azure_cache = sample_cache.to_azure()
        assert "key" in azure_cache
        assert "path" in azure_cache

    def test_cache_to_jenkins(self, sample_cache):
        """Test Jenkins cache format conversion."""
        jenkins_cache = sample_cache.to_jenkins()
        assert "cache(" in jenkins_cache
        assert "ArbitraryFileCache" in jenkins_cache


class TestArtifactConfig:
    """Test ArtifactConfig model (AC-2)."""

    def test_artifact_defaults(self):
        """Test default artifact configuration."""
        artifacts = ArtifactConfig()
        assert artifacts.expire_in == "7 days"
        assert artifacts.upload_on_failure is False

    def test_artifact_with_reports(self, sample_artifacts):
        """Test artifacts with report configuration."""
        assert "junit" in sample_artifacts.reports
        assert sample_artifacts.upload_on_failure is True

    def test_artifact_to_gitlab(self, sample_artifacts):
        """Test GitLab artifact format conversion."""
        gitlab_artifacts = sample_artifacts.to_gitlab()
        assert gitlab_artifacts["expire_in"] == "1 week"
        assert "reports" in gitlab_artifacts
        assert gitlab_artifacts["when"] == "always"  # upload_on_failure=True

    def test_artifact_to_azure(self, sample_artifacts):
        """Test Azure artifact format conversion."""
        azure_artifacts = sample_artifacts.to_azure()
        assert azure_artifacts["task"] == "PublishBuildArtifacts@1"
        assert "inputs" in azure_artifacts

    def test_artifact_to_jenkins(self, sample_artifacts):
        """Test Jenkins artifact format conversion."""
        jenkins_artifacts = sample_artifacts.to_jenkins()
        assert "archiveArtifacts" in jenkins_artifacts


class TestMatrixConfig:
    """Test MatrixConfig model (AC-4)."""

    def test_matrix_defaults(self):
        """Test default matrix configuration."""
        matrix = MatrixConfig()
        assert matrix.fail_fast is True
        assert matrix.dimensions == {}

    def test_matrix_with_dimensions(self, sample_matrix):
        """Test matrix with dimension configuration."""
        assert "python" in sample_matrix.dimensions
        assert "3.11" in sample_matrix.dimensions["python"]
        assert sample_matrix.max_parallel == 4

    def test_matrix_to_gitlab(self, sample_matrix):
        """Test GitLab matrix format conversion."""
        gitlab_matrix = sample_matrix.to_gitlab()
        assert "parallel" in gitlab_matrix
        assert "matrix" in gitlab_matrix["parallel"]

    def test_matrix_to_azure(self, sample_matrix):
        """Test Azure matrix format conversion."""
        azure_matrix = sample_matrix.to_azure()
        assert "strategy" in azure_matrix
        assert "matrix" in azure_matrix["strategy"]

    def test_matrix_to_jenkins(self, sample_matrix):
        """Test Jenkins matrix format conversion."""
        jenkins_matrix = sample_matrix.to_jenkins()
        assert "matrix" in jenkins_matrix
        assert "axis" in jenkins_matrix


class TestEnvironment:
    """Test Environment model (AC-5)."""

    def test_environment_defaults(self):
        """Test default environment configuration."""
        env = Environment(name="staging")
        assert env.requires_approval is False
        assert env.approvers == []

    def test_environment_with_approval(self, sample_environment):
        """Test environment with approval configuration."""
        assert sample_environment.requires_approval is True
        assert "tech-lead" in sample_environment.approvers
        assert sample_environment.url is not None

    def test_environment_to_gitlab(self, sample_environment):
        """Test GitLab environment format conversion."""
        gitlab_env = sample_environment.to_gitlab()
        assert gitlab_env["name"] == "production"
        assert gitlab_env["url"] == "https://app.example.com"


class TestRollbackConfig:
    """Test RollbackConfig model (AC-6)."""

    def test_rollback_defaults(self):
        """Test default rollback configuration."""
        rollback = RollbackConfig()
        assert rollback.enabled is True
        assert rollback.strategy == "previous_version"
        assert rollback.max_attempts == 3

    def test_rollback_with_health_check(self, sample_rollback):
        """Test rollback with health check configuration."""
        assert sample_rollback.health_check is not None
        assert sample_rollback.health_check.endpoint == "/health"
        assert sample_rollback.health_check.expected_status == 200

    def test_rollback_script_generation(self, sample_rollback):
        """Test rollback script generation."""
        script = sample_rollback.generate_rollback_script()
        assert "Rolling back" in script
        assert "PREVIOUS_VERSION" in script

    def test_blue_green_rollback_script(self):
        """Test blue-green rollback script generation."""
        rollback = RollbackConfig(strategy="blue_green")
        script = rollback.generate_rollback_script()
        assert "blue" in script.lower()
        assert "green" in script.lower()


class TestHealthCheck:
    """Test HealthCheck model."""

    def test_health_check_defaults(self):
        """Test default health check configuration."""
        hc = HealthCheck()
        assert hc.endpoint == "/health"
        assert hc.expected_status == 200
        assert hc.threshold == 3

    def test_health_check_to_dict(self):
        """Test health check serialization."""
        hc = HealthCheck(endpoint="/api/health", timeout="10m")
        data = hc.to_dict()
        assert data["endpoint"] == "/api/health"
        assert data["timeout"] == "10m"


class TestJob:
    """Test Job model."""

    def test_job_creation(self, sample_steps):
        """Test basic job creation."""
        job = Job(name="build", steps=sample_steps)
        assert job.name == "build"
        assert len(job.steps) == 3

    def test_job_with_cache_and_artifacts(self, sample_steps, sample_cache, sample_artifacts):
        """Test job with cache and artifact configuration."""
        job = Job(
            name="build",
            steps=sample_steps,
            cache=sample_cache,
            artifacts=sample_artifacts,
        )
        assert job.cache is not None
        assert job.artifacts is not None


class TestStage:
    """Test Stage model."""

    def test_stage_creation(self, sample_steps):
        """Test basic stage creation."""
        job = Job(name="build", steps=sample_steps)
        stage = Stage(name="build", jobs=[job])
        assert stage.name == "build"
        assert len(stage.jobs) == 1

    def test_stage_with_dependencies(self, sample_steps):
        """Test stage with dependencies."""
        job = Job(name="test", steps=sample_steps)
        stage = Stage(name="test", jobs=[job], dependencies=["build"])
        assert "build" in stage.dependencies


# =============================================================================
# GitLab Pipeline Tests (AC-1)
# =============================================================================

class TestGitLabPipeline:
    """Test GitLab pipeline generation."""

    def test_gitlab_pipeline_creation(self):
        """Test basic GitLab pipeline creation."""
        pipeline = GitLabPipeline()
        assert pipeline.platform == Platform.GITLAB
        assert pipeline.image == "python:3.11"

    def test_gitlab_build_pipeline(self):
        """Test GitLab build pipeline."""
        pipeline = GitLabAdapter.create_build_pipeline()
        assert pipeline.pipeline_type == PipelineType.BUILD
        assert len(pipeline.stages) >= 1

    def test_gitlab_test_pipeline(self):
        """Test GitLab test pipeline."""
        pipeline = GitLabAdapter.create_test_pipeline()
        assert pipeline.pipeline_type == PipelineType.TEST
        assert len(pipeline.stages) >= 2

    def test_gitlab_deploy_pipeline(self):
        """Test GitLab deploy pipeline."""
        pipeline = GitLabAdapter.create_deploy_pipeline()
        assert pipeline.pipeline_type == PipelineType.DEPLOY
        assert pipeline.rollback is not None

    def test_gitlab_release_pipeline(self):
        """Test GitLab release pipeline."""
        pipeline = GitLabAdapter.create_release_pipeline()
        assert pipeline.pipeline_type == PipelineType.RELEASE
        assert "RELEASE_VERSION" in pipeline.variables

    def test_gitlab_render_output(self):
        """Test GitLab pipeline YAML rendering."""
        pipeline = GitLabAdapter.create_build_pipeline()
        output = pipeline.render()
        assert "stages:" in output or "image:" in output
        # Should be valid YAML
        parsed = yaml.safe_load(output)
        assert parsed is not None

    def test_gitlab_with_matrix(self, sample_matrix):
        """Test GitLab pipeline with matrix builds (AC-4)."""
        pipeline = GitLabAdapter.create_test_pipeline(matrix=sample_matrix)
        assert pipeline.matrix is not None
        assert "python" in pipeline.matrix.dimensions

    def test_gitlab_validation(self):
        """Test GitLab pipeline validation."""
        pipeline = GitLabPipeline()
        errors = pipeline.validate()
        assert "Pipeline must have at least one stage" in errors

    def test_gitlab_add_stages(self):
        """Test adding stages to GitLab pipeline."""
        pipeline = GitLabPipeline()
        pipeline.add_build_stage()
        pipeline.add_test_stage()
        assert len(pipeline.stages) == 2
        assert pipeline.stages[0].name == "build"
        assert pipeline.stages[1].name == "test"


# =============================================================================
# Azure Pipeline Tests (AC-1)
# =============================================================================

class TestAzurePipeline:
    """Test Azure pipeline generation."""

    def test_azure_pipeline_creation(self):
        """Test basic Azure pipeline creation."""
        pipeline = AzurePipeline()
        assert pipeline.platform == Platform.AZURE
        assert pipeline.pool == "ubuntu-latest"

    def test_azure_build_pipeline(self):
        """Test Azure build pipeline."""
        pipeline = AzureAdapter.create_build_pipeline()
        assert pipeline.pipeline_type == PipelineType.BUILD
        assert len(pipeline.stages) >= 1

    def test_azure_test_pipeline(self):
        """Test Azure test pipeline."""
        pipeline = AzureAdapter.create_test_pipeline()
        assert pipeline.pipeline_type == PipelineType.TEST
        assert len(pipeline.stages) >= 2

    def test_azure_deploy_pipeline(self):
        """Test Azure deploy pipeline."""
        pipeline = AzureAdapter.create_deploy_pipeline()
        assert pipeline.pipeline_type == PipelineType.DEPLOY
        assert pipeline.rollback is not None

    def test_azure_release_pipeline(self):
        """Test Azure release pipeline."""
        pipeline = AzureAdapter.create_release_pipeline()
        assert pipeline.pipeline_type == PipelineType.RELEASE
        assert "releaseVersion" in pipeline.variables

    def test_azure_render_output(self):
        """Test Azure pipeline YAML rendering."""
        pipeline = AzureAdapter.create_build_pipeline()
        output = pipeline.render()
        assert "pool:" in output or "trigger:" in output
        # Should be valid YAML
        parsed = yaml.safe_load(output)
        assert parsed is not None

    def test_azure_with_matrix(self, sample_matrix):
        """Test Azure pipeline with matrix builds (AC-4)."""
        pipeline = AzureAdapter.create_test_pipeline(matrix=sample_matrix)
        assert pipeline.matrix is not None

    def test_azure_validation(self):
        """Test Azure pipeline validation."""
        pipeline = AzurePipeline()
        errors = pipeline.validate()
        assert "Pipeline must have at least one stage" in errors

    def test_azure_trigger_configuration(self):
        """Test Azure pipeline trigger configuration."""
        pipeline = AzurePipeline(trigger_branches=["main", "release/*"])
        assert "main" in pipeline.trigger_branches
        assert "release/*" in pipeline.trigger_branches


# =============================================================================
# Jenkins Pipeline Tests (AC-1)
# =============================================================================

class TestJenkinsPipeline:
    """Test Jenkins pipeline generation."""

    def test_jenkins_pipeline_creation(self):
        """Test basic Jenkins pipeline creation."""
        pipeline = JenkinsPipeline()
        assert pipeline.platform == Platform.JENKINS
        assert pipeline.agent == "any"

    def test_jenkins_build_pipeline(self):
        """Test Jenkins build pipeline."""
        pipeline = JenkinsAdapter.create_build_pipeline()
        assert pipeline.pipeline_type == PipelineType.BUILD
        assert len(pipeline.stages) >= 1

    def test_jenkins_test_pipeline(self):
        """Test Jenkins test pipeline."""
        pipeline = JenkinsAdapter.create_test_pipeline()
        assert pipeline.pipeline_type == PipelineType.TEST
        assert len(pipeline.stages) >= 2

    def test_jenkins_deploy_pipeline(self):
        """Test Jenkins deploy pipeline."""
        pipeline = JenkinsAdapter.create_deploy_pipeline()
        assert pipeline.pipeline_type == PipelineType.DEPLOY
        assert pipeline.rollback is not None

    def test_jenkins_release_pipeline(self):
        """Test Jenkins release pipeline."""
        pipeline = JenkinsAdapter.create_release_pipeline()
        assert pipeline.pipeline_type == PipelineType.RELEASE
        assert "RELEASE_VERSION" in pipeline.variables

    def test_jenkins_render_output(self):
        """Test Jenkins pipeline rendering."""
        pipeline = JenkinsAdapter.create_build_pipeline()
        output = pipeline.render()
        assert "pipeline {" in output
        assert "stages {" in output

    def test_jenkins_with_docker_agent(self):
        """Test Jenkins pipeline with Docker agent."""
        pipeline = JenkinsAdapter.create_build_pipeline(docker_image="python:3.11")
        output = pipeline.render()
        assert "docker" in output
        assert "python:3.11" in output

    def test_jenkins_validation(self):
        """Test Jenkins pipeline validation."""
        pipeline = JenkinsPipeline()
        errors = pipeline.validate()
        assert "Pipeline must have at least one stage" in errors

    def test_jenkins_with_matrix(self, sample_matrix):
        """Test Jenkins pipeline with matrix builds (AC-4)."""
        pipeline = JenkinsAdapter.create_test_pipeline(matrix=sample_matrix)
        assert pipeline.matrix is not None


# =============================================================================
# Pipeline Registry Tests
# =============================================================================

class TestPipelineRegistry:
    """Test PipelineRegistry functionality."""

    def test_registry_singleton(self):
        """Test registry singleton pattern."""
        reg1 = get_pipeline_registry()
        reg2 = get_pipeline_registry()
        assert reg1 is reg2

    def test_registry_initialization(self):
        """Test registry auto-initialization."""
        registry = PipelineRegistry()
        templates = registry.list_all()
        assert len(templates) == 12  # 3 platforms x 4 types

    def test_registry_get_by_id(self):
        """Test getting template by ID."""
        registry = PipelineRegistry()
        template = registry.get("gitlab_build")
        assert template is not None
        assert template.platform == Platform.GITLAB
        assert template.pipeline_type == PipelineType.BUILD

    def test_registry_get_by_platform_and_type(self):
        """Test getting template by platform and type."""
        registry = PipelineRegistry()
        template = registry.get_by_platform_and_type(Platform.AZURE, PipelineType.DEPLOY)
        assert template is not None
        assert template.platform == Platform.AZURE
        assert template.pipeline_type == PipelineType.DEPLOY

    def test_registry_list_by_platform(self):
        """Test listing templates by platform."""
        registry = PipelineRegistry()
        gitlab_templates = registry.list_by_platform(Platform.GITLAB)
        assert len(gitlab_templates) == 4

    def test_registry_list_by_type(self):
        """Test listing templates by type."""
        registry = PipelineRegistry()
        build_templates = registry.list_by_type(PipelineType.BUILD)
        assert len(build_templates) == 3

    def test_registry_get_adapter(self):
        """Test getting platform adapter."""
        registry = PipelineRegistry()
        adapter = registry.get_adapter(Platform.JENKINS)
        assert adapter == JenkinsAdapter

    def test_registry_create_pipeline(self):
        """Test creating pipeline through registry."""
        registry = PipelineRegistry()
        pipeline = registry.create_pipeline(Platform.GITLAB, PipelineType.BUILD)
        assert pipeline.platform == Platform.GITLAB
        assert pipeline.pipeline_type == PipelineType.BUILD

    def test_registry_get_template_ids(self):
        """Test getting all template IDs."""
        registry = PipelineRegistry()
        ids = registry.get_template_ids()
        assert "gitlab_build" in ids
        assert "azure_deploy" in ids
        assert "jenkins_release" in ids

    def test_registry_get_platforms(self):
        """Test getting supported platforms."""
        registry = PipelineRegistry()
        platforms = registry.get_platforms()
        assert Platform.GITLAB in platforms
        assert Platform.AZURE in platforms
        assert Platform.JENKINS in platforms

    def test_registry_count(self):
        """Test template count."""
        registry = PipelineRegistry()
        assert registry.count() == 12

    def test_registry_to_dict(self):
        """Test registry serialization."""
        registry = PipelineRegistry()
        data = registry.to_dict()
        assert data["template_count"] == 12
        assert "platforms" in data
        assert "templates" in data

    def test_registry_custom_template(self):
        """Test registering custom template."""
        registry = PipelineRegistry()
        custom = GitLabAdapter.create_build_pipeline()
        registry.register("custom_build", custom)
        retrieved = registry.get("custom_build")
        assert retrieved is custom


# =============================================================================
# Integration Tests
# =============================================================================

class TestPipelineIntegration:
    """Integration tests for complete pipeline workflows."""

    def test_complete_gitlab_workflow(self, sample_cache, sample_artifacts, sample_rollback):
        """Test complete GitLab pipeline workflow."""
        pipeline = GitLabPipeline(
            cache=sample_cache,
            artifacts=sample_artifacts,
            rollback=sample_rollback,
        )
        pipeline.add_build_stage()
        pipeline.add_test_stage()
        pipeline.add_deploy_stage("staging", requires_approval=False)
        pipeline.add_deploy_stage("production", requires_approval=True)

        # Validate
        errors = pipeline.validate()
        assert len(errors) == 0

        # Render
        output = pipeline.render()
        assert "build" in output
        assert "test" in output
        assert "deploy_staging" in output or "staging" in output

    def test_complete_azure_workflow(self, sample_cache, sample_rollback):
        """Test complete Azure pipeline workflow."""
        pipeline = AzurePipeline(
            cache=sample_cache,
            rollback=sample_rollback,
        )
        pipeline.add_build_stage()
        pipeline.add_test_stage()
        pipeline.add_deploy_stage("staging")
        pipeline.add_deploy_stage("production", requires_approval=True)

        # Validate
        errors = pipeline.validate()
        assert len(errors) == 0

        # Render and parse YAML
        output = pipeline.render()
        parsed = yaml.safe_load(output)
        assert parsed is not None

    def test_complete_jenkins_workflow(self, sample_cache, sample_rollback):
        """Test complete Jenkins pipeline workflow."""
        pipeline = JenkinsPipeline(
            cache=sample_cache,
            rollback=sample_rollback,
        )
        pipeline.add_build_stage()
        pipeline.add_test_stage()
        pipeline.add_deploy_stage("staging")
        pipeline.add_deploy_stage("production", requires_approval=True)

        # Validate
        errors = pipeline.validate()
        assert len(errors) == 0

        # Render
        output = pipeline.render()
        assert "pipeline {" in output
        assert "Build" in output

    def test_cross_platform_consistency(self):
        """Test consistency across all platforms."""
        registry = PipelineRegistry()

        for platform in [Platform.GITLAB, Platform.AZURE, Platform.JENKINS]:
            for ptype in PipelineType:
                template = registry.get_by_platform_and_type(platform, ptype)
                assert template is not None
                assert template.platform == platform
                assert template.pipeline_type == ptype
                assert len(template.stages) > 0

    def test_pipeline_serialization(self):
        """Test pipeline serialization to dict."""
        pipeline = GitLabAdapter.create_deploy_pipeline()
        data = pipeline.to_dict()

        assert data["pipeline_type"] == "deploy"
        assert data["platform"] == "gitlab"
        assert len(data["stages"]) > 0
        assert data["rollback"] is not None


# =============================================================================
# Acceptance Criteria Validation Tests
# =============================================================================

class TestAcceptanceCriteria:
    """Validate all acceptance criteria are met."""

    def test_ac1_full_pipeline_suite(self):
        """AC-1: Full pipeline suite for GitLab, Azure, Jenkins."""
        registry = PipelineRegistry()

        # Each platform should have 4 pipeline types
        for platform in [Platform.GITLAB, Platform.AZURE, Platform.JENKINS]:
            templates = registry.list_by_platform(platform)
            assert len(templates) == 4, f"{platform.value} should have 4 pipeline types"

            types = {t.pipeline_type for t in templates}
            assert PipelineType.BUILD in types
            assert PipelineType.TEST in types
            assert PipelineType.DEPLOY in types
            assert PipelineType.RELEASE in types

    def test_ac2_artifact_management(self):
        """AC-2: Artifact management with paths, expire_in, reports."""
        artifacts = ArtifactConfig(
            paths=["dist/", "coverage/"],
            expire_in="2 weeks",
            reports={"junit": "report.xml", "coverage": "coverage.xml"},
            upload_on_failure=True,
        )

        # Test all platform formats
        gitlab = artifacts.to_gitlab()
        assert "paths" in gitlab
        assert "expire_in" in gitlab
        assert "reports" in gitlab

        azure = artifacts.to_azure()
        assert "task" in azure
        assert "inputs" in azure

        jenkins = artifacts.to_jenkins()
        assert "archiveArtifacts" in jenkins

    def test_ac3_caching_strategies(self):
        """AC-3: Caching with key, paths, policy, fallback_keys."""
        cache = CacheConfig(
            key="${CI_COMMIT_REF_SLUG}",
            paths=[".cache/pip", "node_modules", ".m2"],
            policy="pull-push",
            fallback_keys=["${CI_DEFAULT_BRANCH}", "main"],
        )

        # Test all platform formats
        gitlab = cache.to_gitlab()
        assert "key" in gitlab
        assert "paths" in gitlab
        assert "policy" in gitlab

        azure = cache.to_azure()
        assert "key" in azure
        assert "restoreKeys" in azure

        jenkins = cache.to_jenkins()
        assert "cache(" in jenkins

    def test_ac4_matrix_builds(self):
        """AC-4: Matrix with dimensions, exclude, include, fail_fast."""
        matrix = MatrixConfig(
            dimensions={
                "python": ["3.9", "3.10", "3.11"],
                "os": ["ubuntu-latest", "windows-latest"],
            },
            exclude=[{"python": "3.9", "os": "windows-latest"}],
            fail_fast=True,
            max_parallel=4,
        )

        # Test all platform formats
        gitlab = matrix.to_gitlab()
        assert "parallel" in gitlab

        azure = matrix.to_azure()
        assert "strategy" in azure
        assert "maxParallel" in azure["strategy"]

        jenkins = matrix.to_jenkins()
        assert "matrix" in jenkins
        assert "failFast" in jenkins

    def test_ac5_environment_promotion(self):
        """AC-5: Environment with requires_approval, approvers, protection_rules."""
        env = Environment(
            name="production",
            url="https://prod.example.com",
            requires_approval=True,
            approvers=["tech-lead", "security-team"],
            protection_rules=["require_code_review", "require_security_scan"],
        )

        assert env.requires_approval is True
        assert len(env.approvers) == 2
        assert len(env.protection_rules) == 2

        # Test GitLab format
        gitlab = env.to_gitlab()
        assert gitlab["name"] == "production"
        assert gitlab["url"] == "https://prod.example.com"

    def test_ac6_rollback_capability(self):
        """AC-6: Rollback with strategy, health_check, max_attempts."""
        rollback = RollbackConfig(
            enabled=True,
            strategy="previous_version",
            health_check=HealthCheck(
                endpoint="/health",
                expected_status=200,
                timeout="5m",
                threshold=3,
            ),
            max_attempts=3,
            on_failure="rollback",
        )

        assert rollback.enabled is True
        assert rollback.strategy == "previous_version"
        assert rollback.health_check is not None
        assert rollback.max_attempts == 3

        # Test script generation
        script = rollback.generate_rollback_script()
        assert "PREVIOUS_VERSION" in script

        # Test serialization
        data = rollback.to_dict()
        assert data["enabled"] is True
        assert data["health_check"] is not None
