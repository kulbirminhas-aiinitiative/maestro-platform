"""
Pipeline Stage Definitions.

Defines build, test, security scan, and deploy stages.
"""

import asyncio
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Optional


class StageType(str, Enum):
    """Stage types."""
    BUILD = "build"
    TEST = "test"
    SECURITY_SCAN = "security_scan"
    DEPLOY = "deploy"
    VERIFY = "verify"
    CUSTOM = "custom"


class StageStatus(str, Enum):
    """Stage execution status."""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class StageOutput:
    """Output from stage execution."""
    stage_name: str
    status: StageStatus
    started_at: datetime
    completed_at: Optional[datetime] = None
    duration_ms: int = 0
    logs: list[str] = field(default_factory=list)
    artifacts: list[str] = field(default_factory=list)
    metrics: dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.stage_name,
            "status": self.status.value,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration_ms": self.duration_ms,
            "logs_count": len(self.logs),
            "artifacts": self.artifacts,
            "metrics": self.metrics,
            "error": self.error
        }


@dataclass
class StageConfig:
    """Stage configuration."""
    timeout_seconds: int = 600
    retry_count: int = 0
    parallel: bool = False
    continue_on_failure: bool = False
    environment: dict[str, str] = field(default_factory=dict)
    commands: list[str] = field(default_factory=list)


class PipelineStage:
    """Base class for pipeline stages."""

    def __init__(
        self,
        name: str,
        stage_type: StageType,
        config: Optional[StageConfig] = None,
        executor: Optional[Callable] = None
    ):
        self.name = name
        self.stage_type = stage_type
        self.config = config or StageConfig()
        self._executor = executor
        self._logs: list[str] = []

    def log(self, message: str) -> None:
        """Add log entry."""
        timestamp = datetime.utcnow().isoformat()
        self._logs.append(f"[{timestamp}] {message}")

    async def execute(self, context: dict[str, Any]) -> StageOutput:
        """Execute the stage."""
        started_at = datetime.utcnow()
        output = StageOutput(
            stage_name=self.name,
            status=StageStatus.RUNNING,
            started_at=started_at
        )

        try:
            self.log(f"Starting stage: {self.name}")

            if self._executor:
                result = await self._executor(context, self)
                output.metrics = result.get("metrics", {})
                output.artifacts = result.get("artifacts", [])
            else:
                result = await self._default_execute(context)
                output.metrics = result

            output.status = StageStatus.SUCCESS
            self.log(f"Stage completed successfully: {self.name}")

        except asyncio.TimeoutError:
            output.status = StageStatus.FAILED
            output.error = f"Stage timed out after {self.config.timeout_seconds}s"
            self.log(f"Stage timed out: {self.name}")
        except Exception as e:
            output.status = StageStatus.FAILED
            output.error = str(e)
            self.log(f"Stage failed: {self.name} - {e}")

        output.completed_at = datetime.utcnow()
        output.duration_ms = int(
            (output.completed_at - output.started_at).total_seconds() * 1000
        )
        output.logs = self._logs.copy()
        self._logs.clear()

        return output

    async def _default_execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """Default execution behavior by stage type."""
        if self.stage_type == StageType.BUILD:
            return await self._build(context)
        elif self.stage_type == StageType.TEST:
            return await self._test(context)
        elif self.stage_type == StageType.SECURITY_SCAN:
            return await self._security_scan(context)
        elif self.stage_type == StageType.DEPLOY:
            return await self._deploy(context)
        elif self.stage_type == StageType.VERIFY:
            return await self._verify(context)
        return {}

    async def _build(self, context: dict[str, Any]) -> dict[str, Any]:
        """Execute build stage."""
        self.log("Running build commands...")
        for cmd in self.config.commands:
            self.log(f"Executing: {cmd}")
        await asyncio.sleep(0.01)  # Simulate build
        return {"build_success": True, "artifact_size_bytes": 1024000}

    async def _test(self, context: dict[str, Any]) -> dict[str, Any]:
        """Execute test stage."""
        self.log("Running test suite...")
        await asyncio.sleep(0.01)  # Simulate testing
        return {
            "tests_total": 100,
            "tests_passed": 100,
            "tests_failed": 0,
            "coverage_percent": 85.5
        }

    async def _security_scan(self, context: dict[str, Any]) -> dict[str, Any]:
        """Execute security scan stage."""
        self.log("Running security scan...")
        await asyncio.sleep(0.01)  # Simulate scan
        return {
            "vulnerabilities_critical": 0,
            "vulnerabilities_high": 0,
            "vulnerabilities_medium": 2,
            "vulnerabilities_low": 5
        }

    async def _deploy(self, context: dict[str, Any]) -> dict[str, Any]:
        """Execute deploy stage."""
        env = context.get("env", {})
        target = env.get("DEPLOY_ENVIRONMENT", "staging")
        self.log(f"Deploying to {target}...")
        await asyncio.sleep(0.01)  # Simulate deployment
        return {"environment": target, "deployed": True}

    async def _verify(self, context: dict[str, Any]) -> dict[str, Any]:
        """Execute verification stage."""
        self.log("Running post-deployment verification...")
        await asyncio.sleep(0.01)  # Simulate verification
        return {"health_check_passed": True, "smoke_tests_passed": True}


class BuildStage(PipelineStage):
    """Build stage with Docker support."""

    def __init__(self, name: str = "build", config: Optional[StageConfig] = None):
        super().__init__(name, StageType.BUILD, config)
        self.docker_image: Optional[str] = None
        self.build_args: dict[str, str] = {}

    def set_docker_config(self, image: str, build_args: dict[str, str] = None) -> None:
        """Configure Docker build."""
        self.docker_image = image
        self.build_args = build_args or {}


class TestStage(PipelineStage):
    """Test stage with parallel execution support."""

    def __init__(self, name: str = "test", config: Optional[StageConfig] = None):
        config = config or StageConfig(parallel=True)
        super().__init__(name, StageType.TEST, config)
        self.test_suites: list[str] = []

    def add_test_suite(self, suite: str) -> None:
        """Add test suite to execute."""
        self.test_suites.append(suite)


class DeployStage(PipelineStage):
    """Deploy stage with environment targeting."""

    def __init__(
        self,
        name: str = "deploy",
        target_environment: str = "staging",
        config: Optional[StageConfig] = None
    ):
        super().__init__(name, StageType.DEPLOY, config)
        self.target_environment = target_environment
        self.deployment_strategy = "rolling"

    def set_strategy(self, strategy: str) -> None:
        """Set deployment strategy (rolling, blue-green, canary)."""
        valid = ["rolling", "blue-green", "canary"]
        if strategy not in valid:
            raise ValueError(f"Invalid strategy. Choose from: {valid}")
        self.deployment_strategy = strategy
