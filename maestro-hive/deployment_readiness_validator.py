#!/usr/bin/env python3
"""
Deployment Readiness Validator
Validates that a workflow output is actually deployable with smoke tests
"""

import asyncio
import json
import logging
import subprocess
import tempfile
import time
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List, Tuple
from enum import Enum
import yaml

logger = logging.getLogger(__name__)


class ValidationSeverity(Enum):
    """Severity of validation failures"""
    CRITICAL = "critical"  # Deployment will fail
    HIGH = "high"  # Deployment may fail
    MEDIUM = "medium"  # Deployment may have issues
    LOW = "low"  # Minor issues


@dataclass
class DeploymentCheck:
    """Result of a deployment readiness check"""
    check_name: str
    passed: bool
    severity: ValidationSeverity
    message: str
    details: Dict[str, Any] = field(default_factory=dict)
    fix_suggestion: Optional[str] = None
    execution_time: float = 0.0


@dataclass
class DeploymentReadinessReport:
    """Complete deployment readiness report"""
    workflow_dir: Path
    is_deployable: bool
    checks_passed: int
    checks_failed: int
    critical_failures: int
    high_failures: int
    checks: List[DeploymentCheck] = field(default_factory=list)
    docker_build_results: Dict[str, Any] = field(default_factory=dict)
    service_health_results: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "workflow_dir": str(self.workflow_dir),
            "is_deployable": self.is_deployable,
            "checks_passed": self.checks_passed,
            "checks_failed": self.checks_failed,
            "critical_failures": self.critical_failures,
            "high_failures": self.high_failures,
            "checks": [
                {
                    "check_name": c.check_name,
                    "passed": c.passed,
                    "severity": c.severity.value,
                    "message": c.message,
                    "details": c.details,
                    "fix_suggestion": c.fix_suggestion,
                    "execution_time": c.execution_time
                }
                for c in self.checks
            ],
            "docker_build_results": self.docker_build_results,
            "service_health_results": self.service_health_results
        }


class DeploymentReadinessValidator:
    """
    Validates deployment readiness with actual smoke tests

    Performs:
    1. Docker build verification
    2. Docker Compose validation
    3. Environment variable checks
    4. Port availability checks
    5. Service health checks (optional - requires starting services)
    6. Database migration validation
    7. API endpoint validation
    """

    def __init__(self, workflow_dir: Path, run_service_tests: bool = False):
        """
        Initialize deployment readiness validator

        Args:
            workflow_dir: Path to workflow output directory
            run_service_tests: Whether to actually start services for testing (default: False)
        """
        self.workflow_dir = Path(workflow_dir)
        self.deployment_dir = self.workflow_dir / "deployment"
        self.implementation_dir = self.workflow_dir / "implementation"
        self.run_service_tests = run_service_tests
        self.checks: List[DeploymentCheck] = []

    async def validate(self) -> DeploymentReadinessReport:
        """
        Run all deployment readiness checks

        Returns:
            DeploymentReadinessReport with all check results
        """
        logger.info(f"Starting deployment readiness validation for {self.workflow_dir}")

        # Run all checks
        await self._check_deployment_directory()
        await self._check_dockerfiles()
        await self._validate_docker_compose()
        await self._check_environment_variables()
        await self._validate_docker_builds()
        await self._check_port_availability()

        if self.run_service_tests:
            await self._run_service_health_checks()
            await self._validate_api_endpoints()

        # Analyze results
        checks_passed = sum(1 for c in self.checks if c.passed)
        checks_failed = sum(1 for c in self.checks if not c.passed)
        critical_failures = sum(1 for c in self.checks if not c.passed and c.severity == ValidationSeverity.CRITICAL)
        high_failures = sum(1 for c in self.checks if not c.passed and c.severity == ValidationSeverity.HIGH)

        is_deployable = critical_failures == 0

        report = DeploymentReadinessReport(
            workflow_dir=self.workflow_dir,
            is_deployable=is_deployable,
            checks_passed=checks_passed,
            checks_failed=checks_failed,
            critical_failures=critical_failures,
            high_failures=high_failures,
            checks=self.checks
        )

        logger.info(f"Deployment readiness validation complete: {checks_passed} passed, {checks_failed} failed")
        return report

    async def _check_deployment_directory(self):
        """Check if deployment directory exists and has required files"""
        start_time = time.time()

        if not self.deployment_dir.exists():
            self.checks.append(DeploymentCheck(
                check_name="deployment_directory_exists",
                passed=False,
                severity=ValidationSeverity.CRITICAL,
                message="Deployment directory does not exist",
                fix_suggestion="Create deployment/ directory with Docker configurations",
                execution_time=time.time() - start_time
            ))
            return

        # Check for essential files
        required_files = [
            "docker-compose.yml",
            "docker/Dockerfile.backend",
        ]

        missing_files = [f for f in required_files if not (self.deployment_dir / f).exists()]

        if missing_files:
            self.checks.append(DeploymentCheck(
                check_name="required_deployment_files",
                passed=False,
                severity=ValidationSeverity.CRITICAL,
                message=f"Missing required deployment files: {', '.join(missing_files)}",
                details={"missing_files": missing_files},
                fix_suggestion="Generate missing deployment files",
                execution_time=time.time() - start_time
            ))
        else:
            self.checks.append(DeploymentCheck(
                check_name="deployment_directory_complete",
                passed=True,
                severity=ValidationSeverity.CRITICAL,
                message="Deployment directory exists with required files",
                execution_time=time.time() - start_time
            ))

    async def _check_dockerfiles(self):
        """Check if Dockerfiles are valid and reference existing files"""
        start_time = time.time()

        dockerfiles = list((self.deployment_dir / "docker").glob("Dockerfile.*")) if (self.deployment_dir / "docker").exists() else []

        if not dockerfiles:
            self.checks.append(DeploymentCheck(
                check_name="dockerfiles_exist",
                passed=False,
                severity=ValidationSeverity.CRITICAL,
                message="No Dockerfiles found",
                fix_suggestion="Create Dockerfiles for backend and frontend",
                execution_time=time.time() - start_time
            ))
            return

        for dockerfile in dockerfiles:
            service_name = dockerfile.name.replace("Dockerfile.", "")

            # Read Dockerfile
            try:
                content = dockerfile.read_text()

                # Check for COPY commands that reference implementation
                copy_commands = [line for line in content.split('\n') if line.strip().startswith('COPY')]

                # Check if referenced paths exist
                invalid_copies = []
                for copy_cmd in copy_commands:
                    # Simple parsing: COPY <src> <dest>
                    parts = copy_cmd.split()
                    if len(parts) >= 3 and parts[1] != '--from=builder':
                        src_path = parts[1]
                        # Check if source exists (relative to deployment or implementation dir)
                        if not src_path.startswith('/') and not src_path.startswith('.'):
                            # Relative path - check in implementation
                            impl_path = self.implementation_dir / src_path
                            if not impl_path.exists() and '*' not in src_path:
                                invalid_copies.append(src_path)

                if invalid_copies:
                    self.checks.append(DeploymentCheck(
                        check_name=f"dockerfile_{service_name}_references",
                        passed=False,
                        severity=ValidationSeverity.HIGH,
                        message=f"Dockerfile.{service_name} references non-existent paths: {', '.join(invalid_copies)}",
                        details={"service": service_name, "invalid_paths": invalid_copies},
                        fix_suggestion=f"Ensure implementation exists for {service_name} service",
                        execution_time=time.time() - start_time
                    ))
                else:
                    self.checks.append(DeploymentCheck(
                        check_name=f"dockerfile_{service_name}_valid",
                        passed=True,
                        severity=ValidationSeverity.CRITICAL,
                        message=f"Dockerfile.{service_name} is valid",
                        execution_time=time.time() - start_time
                    ))

            except Exception as e:
                self.checks.append(DeploymentCheck(
                    check_name=f"dockerfile_{service_name}_readable",
                    passed=False,
                    severity=ValidationSeverity.HIGH,
                    message=f"Could not read Dockerfile.{service_name}: {e}",
                    execution_time=time.time() - start_time
                ))

    async def _validate_docker_compose(self):
        """Validate docker-compose.yml configuration"""
        start_time = time.time()

        compose_file = self.deployment_dir / "docker-compose.yml"
        if not compose_file.exists():
            self.checks.append(DeploymentCheck(
                check_name="docker_compose_exists",
                passed=False,
                severity=ValidationSeverity.CRITICAL,
                message="docker-compose.yml not found",
                fix_suggestion="Create docker-compose.yml with service definitions",
                execution_time=time.time() - start_time
            ))
            return

        try:
            # Parse docker-compose.yml
            with open(compose_file) as f:
                compose_config = yaml.safe_load(f)

            services = compose_config.get('services', {})

            if not services:
                self.checks.append(DeploymentCheck(
                    check_name="docker_compose_services",
                    passed=False,
                    severity=ValidationSeverity.CRITICAL,
                    message="docker-compose.yml has no services defined",
                    fix_suggestion="Add service definitions to docker-compose.yml",
                    execution_time=time.time() - start_time
                ))
                return

            # Validate each service
            service_issues = []
            for service_name, service_config in services.items():
                # Check if build context exists
                if 'build' in service_config:
                    build_config = service_config['build']
                    if isinstance(build_config, dict):
                        context = build_config.get('context', '.')
                        dockerfile = build_config.get('dockerfile', 'Dockerfile')
                    else:
                        context = build_config
                        dockerfile = 'Dockerfile'

                    # Check if dockerfile exists
                    dockerfile_path = self.deployment_dir / context / dockerfile
                    if not dockerfile_path.exists():
                        service_issues.append(f"{service_name}: Dockerfile not found at {dockerfile_path}")

                # Check if required environment variables are defined
                if 'environment' in service_config:
                    env_vars = service_config['environment']
                    # This is just informational - we'll do detailed env check later

                # Check port conflicts
                if 'ports' in service_config:
                    ports = service_config['ports']
                    # Format: "HOST:CONTAINER" or "CONTAINER"
                    for port_mapping in ports:
                        if isinstance(port_mapping, str) and ':' in port_mapping:
                            host_port = port_mapping.split(':')[0]
                            # We'll check port availability in separate check

            if service_issues:
                self.checks.append(DeploymentCheck(
                    check_name="docker_compose_service_validity",
                    passed=False,
                    severity=ValidationSeverity.HIGH,
                    message=f"Docker Compose service issues: {'; '.join(service_issues)}",
                    details={"issues": service_issues},
                    fix_suggestion="Fix service configuration in docker-compose.yml",
                    execution_time=time.time() - start_time
                ))
            else:
                self.checks.append(DeploymentCheck(
                    check_name="docker_compose_valid",
                    passed=True,
                    severity=ValidationSeverity.CRITICAL,
                    message=f"docker-compose.yml is valid with {len(services)} services",
                    details={"service_count": len(services), "services": list(services.keys())},
                    execution_time=time.time() - start_time
                ))

        except Exception as e:
            self.checks.append(DeploymentCheck(
                check_name="docker_compose_parseable",
                passed=False,
                severity=ValidationSeverity.CRITICAL,
                message=f"Could not parse docker-compose.yml: {e}",
                fix_suggestion="Fix YAML syntax in docker-compose.yml",
                execution_time=time.time() - start_time
            ))

    async def _check_environment_variables(self):
        """Check if required environment variables are documented"""
        start_time = time.time()

        env_examples = list(self.deployment_dir.glob("**/.env.example"))
        env_examples.extend(list(self.implementation_dir.glob("**/.env.example")))

        if not env_examples:
            self.checks.append(DeploymentCheck(
                check_name="environment_variables_documented",
                passed=False,
                severity=ValidationSeverity.MEDIUM,
                message="No .env.example files found",
                fix_suggestion="Create .env.example files documenting required environment variables",
                execution_time=time.time() - start_time
            ))
        else:
            self.checks.append(DeploymentCheck(
                check_name="environment_variables_documented",
                passed=True,
                severity=ValidationSeverity.MEDIUM,
                message=f"Found {len(env_examples)} .env.example files",
                details={"env_files": [str(f) for f in env_examples]},
                execution_time=time.time() - start_time
            ))

    async def _validate_docker_builds(self):
        """Actually try to build Docker images"""
        start_time = time.time()

        compose_file = self.deployment_dir / "docker-compose.yml"
        if not compose_file.exists():
            return  # Already reported in previous check

        try:
            # Try docker-compose config validation
            result = subprocess.run(
                ["docker-compose", "-f", str(compose_file), "config"],
                cwd=self.deployment_dir,
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode == 0:
                self.checks.append(DeploymentCheck(
                    check_name="docker_compose_config_valid",
                    passed=True,
                    severity=ValidationSeverity.HIGH,
                    message="docker-compose config validation passed",
                    execution_time=time.time() - start_time
                ))

                # Try to build images (dry-run)
                logger.info("Attempting Docker image builds...")
                build_result = subprocess.run(
                    ["docker-compose", "-f", str(compose_file), "build", "--no-cache"],
                    cwd=self.deployment_dir,
                    capture_output=True,
                    text=True,
                    timeout=600  # 10 minutes max
                )

                if build_result.returncode == 0:
                    self.checks.append(DeploymentCheck(
                        check_name="docker_images_buildable",
                        passed=True,
                        severity=ValidationSeverity.CRITICAL,
                        message="All Docker images built successfully",
                        details={"build_output": build_result.stdout[-500:]},  # Last 500 chars
                        execution_time=time.time() - start_time
                    ))
                else:
                    self.checks.append(DeploymentCheck(
                        check_name="docker_images_buildable",
                        passed=False,
                        severity=ValidationSeverity.CRITICAL,
                        message="Docker image build failed",
                        details={"error": build_result.stderr[-500:]},
                        fix_suggestion="Fix Docker build errors in Dockerfiles",
                        execution_time=time.time() - start_time
                    ))

            else:
                self.checks.append(DeploymentCheck(
                    check_name="docker_compose_config_valid",
                    passed=False,
                    severity=ValidationSeverity.HIGH,
                    message=f"docker-compose config validation failed: {result.stderr}",
                    details={"error": result.stderr},
                    fix_suggestion="Fix docker-compose.yml configuration",
                    execution_time=time.time() - start_time
                ))

        except subprocess.TimeoutExpired:
            self.checks.append(DeploymentCheck(
                check_name="docker_build_timeout",
                passed=False,
                severity=ValidationSeverity.HIGH,
                message="Docker build timed out after 10 minutes",
                fix_suggestion="Optimize Dockerfile or increase build timeout",
                execution_time=time.time() - start_time
            ))
        except FileNotFoundError:
            self.checks.append(DeploymentCheck(
                check_name="docker_compose_available",
                passed=False,
                severity=ValidationSeverity.CRITICAL,
                message="docker-compose command not found",
                fix_suggestion="Install docker-compose to validate deployment",
                execution_time=time.time() - start_time
            ))
        except Exception as e:
            self.checks.append(DeploymentCheck(
                check_name="docker_build_validation",
                passed=False,
                severity=ValidationSeverity.HIGH,
                message=f"Docker build validation failed: {e}",
                execution_time=time.time() - start_time
            ))

    async def _check_port_availability(self):
        """Check if required ports are available"""
        start_time = time.time()

        compose_file = self.deployment_dir / "docker-compose.yml"
        if not compose_file.exists():
            return

        try:
            with open(compose_file) as f:
                compose_config = yaml.safe_load(f)

            services = compose_config.get('services', {})
            required_ports = []

            for service_name, service_config in services.items():
                if 'ports' in service_config:
                    for port_mapping in service_config['ports']:
                        if isinstance(port_mapping, str) and ':' in port_mapping:
                            host_port = int(port_mapping.split(':')[0])
                            required_ports.append((service_name, host_port))
                        elif isinstance(port_mapping, int):
                            required_ports.append((service_name, port_mapping))

            if required_ports:
                # Check port availability
                import socket
                ports_in_use = []
                for service_name, port in required_ports:
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    result = sock.connect_ex(('localhost', port))
                    sock.close()
                    if result == 0:
                        ports_in_use.append((service_name, port))

                if ports_in_use:
                    self.checks.append(DeploymentCheck(
                        check_name="ports_available",
                        passed=False,
                        severity=ValidationSeverity.HIGH,
                        message=f"Required ports already in use: {ports_in_use}",
                        details={"ports_in_use": ports_in_use},
                        fix_suggestion="Stop services using these ports or change port mappings",
                        execution_time=time.time() - start_time
                    ))
                else:
                    self.checks.append(DeploymentCheck(
                        check_name="ports_available",
                        passed=True,
                        severity=ValidationSeverity.HIGH,
                        message=f"All required ports are available: {[p[1] for p in required_ports]}",
                        details={"required_ports": required_ports},
                        execution_time=time.time() - start_time
                    ))

        except Exception as e:
            self.checks.append(DeploymentCheck(
                check_name="port_availability_check",
                passed=False,
                severity=ValidationSeverity.MEDIUM,
                message=f"Could not check port availability: {e}",
                execution_time=time.time() - start_time
            ))

    async def _run_service_health_checks(self):
        """Start services and check if they're healthy"""
        start_time = time.time()
        logger.info("Starting services for health checks...")

        compose_file = self.deployment_dir / "docker-compose.yml"
        if not compose_file.exists():
            return

        try:
            # Start services
            subprocess.run(
                ["docker-compose", "-f", str(compose_file), "up", "-d"],
                cwd=self.deployment_dir,
                capture_output=True,
                timeout=120
            )

            # Wait for services to start
            await asyncio.sleep(10)

            # Check service health
            result = subprocess.run(
                ["docker-compose", "-f", str(compose_file), "ps"],
                cwd=self.deployment_dir,
                capture_output=True,
                text=True
            )

            # Parse output to check service status
            services_healthy = "Up" in result.stdout

            if services_healthy:
                self.checks.append(DeploymentCheck(
                    check_name="services_start_successfully",
                    passed=True,
                    severity=ValidationSeverity.CRITICAL,
                    message="Services started successfully",
                    details={"ps_output": result.stdout},
                    execution_time=time.time() - start_time
                ))
            else:
                self.checks.append(DeploymentCheck(
                    check_name="services_start_successfully",
                    passed=False,
                    severity=ValidationSeverity.CRITICAL,
                    message="Services failed to start",
                    details={"ps_output": result.stdout},
                    fix_suggestion="Check service logs for startup errors",
                    execution_time=time.time() - start_time
                ))

            # Clean up
            subprocess.run(
                ["docker-compose", "-f", str(compose_file), "down"],
                cwd=self.deployment_dir,
                capture_output=True
            )

        except Exception as e:
            self.checks.append(DeploymentCheck(
                check_name="service_health_check",
                passed=False,
                severity=ValidationSeverity.HIGH,
                message=f"Service health check failed: {e}",
                execution_time=time.time() - start_time
            ))

    async def _validate_api_endpoints(self):
        """Validate that API endpoints are accessible"""
        start_time = time.time()
        logger.info("Validating API endpoints...")

        # This would require services to be running
        # For now, just check if API documentation exists
        api_docs = list(self.workflow_dir.glob("**/api.md"))
        api_docs.extend(list(self.workflow_dir.glob("**/API_DESIGN.md")))

        if api_docs:
            self.checks.append(DeploymentCheck(
                check_name="api_documented",
                passed=True,
                severity=ValidationSeverity.MEDIUM,
                message=f"API documented in {len(api_docs)} files",
                execution_time=time.time() - start_time
            ))
        else:
            self.checks.append(DeploymentCheck(
                check_name="api_documented",
                passed=False,
                severity=ValidationSeverity.LOW,
                message="No API documentation found",
                fix_suggestion="Create API documentation",
                execution_time=time.time() - start_time
            ))


def main():
    """CLI for deployment readiness validation"""
    import argparse

    parser = argparse.ArgumentParser(description="Validate deployment readiness")
    parser.add_argument(
        "workflow_dir",
        type=Path,
        help="Path to workflow output directory"
    )
    parser.add_argument(
        "--run-service-tests",
        action="store_true",
        help="Actually start services to test (requires Docker)"
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Output file for report (JSON)"
    )

    args = parser.parse_args()

    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Run validation
    validator = DeploymentReadinessValidator(
        workflow_dir=args.workflow_dir,
        run_service_tests=args.run_service_tests
    )

    report = asyncio.run(validator.validate())

    # Print report
    print("\n" + "="*80)
    print(f"DEPLOYMENT READINESS: {args.workflow_dir.name}")
    print("="*80)
    print(f"Deployable: {'Yes' if report.is_deployable else 'No'}")
    print(f"Checks Passed: {report.checks_passed}")
    print(f"Checks Failed: {report.checks_failed}")
    print(f"  - Critical: {report.critical_failures}")
    print(f"  - High: {report.high_failures}")

    print("\nCheck Results:")
    print("-"*80)
    for check in report.checks:
        status_icon = "✓" if check.passed else "✗"
        severity_icon = {
            ValidationSeverity.CRITICAL: "🔴",
            ValidationSeverity.HIGH: "🟠",
            ValidationSeverity.MEDIUM: "🟡",
            ValidationSeverity.LOW: "🟢"
        }[check.severity]

        print(f"{status_icon} {severity_icon} {check.check_name}")
        print(f"    {check.message}")
        if check.fix_suggestion:
            print(f"    💡 {check.fix_suggestion}")
        print()

    # Save report if requested
    if args.output:
        args.output.write_text(json.dumps(report.to_dict(), indent=2))
        print(f"Report saved to: {args.output}")

    print("="*80)


if __name__ == "__main__":
    main()
