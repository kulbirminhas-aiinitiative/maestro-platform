#!/usr/bin/env python3
"""
Workflow Phase Validation Framework

Provides comprehensive validation for each SDLC phase to ensure
completeness before progressing to the next phase.

Addresses critical gaps found in workflow execution where phases
marked "complete" but delivered incomplete or non-functional artifacts.
"""

import os
import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import subprocess
import re


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ValidationSeverity(Enum):
    """Severity levels for validation failures"""
    CRITICAL = "critical"  # Blocks phase completion
    HIGH = "high"          # Should be fixed but phase can proceed with warnings
    MEDIUM = "medium"      # Advisory, doesn't block
    LOW = "low"            # Informational


@dataclass
class ValidationResult:
    """Result of a validation check"""
    check_name: str
    passed: bool
    severity: ValidationSeverity
    message: str
    details: Dict[str, Any] = field(default_factory=dict)
    fix_suggestion: Optional[str] = None


@dataclass
class PhaseValidationReport:
    """Complete validation report for a phase"""
    phase_name: str
    overall_status: str  # "passed", "failed", "warning"
    checks_passed: int
    checks_failed: int
    critical_failures: int
    results: List[ValidationResult] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "phase_name": self.phase_name,
            "overall_status": self.overall_status,
            "checks_passed": self.checks_passed,
            "checks_failed": self.checks_failed,
            "critical_failures": self.critical_failures,
            "results": [
                {
                    "check": r.check_name,
                    "passed": r.passed,
                    "severity": r.severity.value,
                    "message": r.message,
                    "details": r.details,
                    "fix_suggestion": r.fix_suggestion
                }
                for r in self.results
            ]
        }


class PhaseValidator:
    """Base class for phase validators"""

    def __init__(self, workflow_dir: Path):
        self.workflow_dir = Path(workflow_dir)
        self.results: List[ValidationResult] = []

    def add_result(self, result: ValidationResult):
        """Add a validation result"""
        self.results.append(result)

        if result.passed:
            logger.info(f"✓ {result.check_name}: PASSED")
        else:
            level = logging.CRITICAL if result.severity == ValidationSeverity.CRITICAL else logging.WARNING
            logger.log(level, f"✗ {result.check_name}: FAILED - {result.message}")

    def validate(self) -> PhaseValidationReport:
        """Run all validations for this phase"""
        raise NotImplementedError("Subclasses must implement validate()")

    def file_exists(self, path: str) -> bool:
        """Check if file exists relative to workflow dir"""
        return (self.workflow_dir / path).exists()

    def dir_exists(self, path: str) -> bool:
        """Check if directory exists relative to workflow dir"""
        return (self.workflow_dir / path).is_dir()

    def count_files(self, pattern: str, directory: str = ".") -> int:
        """Count files matching pattern in directory"""
        search_dir = self.workflow_dir / directory
        if not search_dir.exists():
            return 0
        return len(list(search_dir.rglob(pattern)))

    def find_files(self, pattern: str, directory: str = ".") -> List[Path]:
        """Find all files matching pattern"""
        search_dir = self.workflow_dir / directory
        if not search_dir.exists():
            return []
        return list(search_dir.rglob(pattern))


class RequirementsValidator(PhaseValidator):
    """Validates requirements phase outputs"""

    def validate(self) -> PhaseValidationReport:
        logger.info("=" * 80)
        logger.info("VALIDATING REQUIREMENTS PHASE")
        logger.info("=" * 80)

        self.results = []
        requirements_dir = self.workflow_dir / "requirements"

        # Check 1: Requirements directory exists
        if not requirements_dir.exists():
            self.add_result(ValidationResult(
                check_name="requirements_dir_exists",
                passed=False,
                severity=ValidationSeverity.CRITICAL,
                message="Requirements directory does not exist",
                fix_suggestion="Create requirements/ directory and add requirement documents"
            ))
        else:
            self.add_result(ValidationResult(
                check_name="requirements_dir_exists",
                passed=True,
                severity=ValidationSeverity.CRITICAL,
                message="Requirements directory found"
            ))

            # Check 2: Minimum number of requirement documents
            req_files = list(requirements_dir.glob("*.md"))
            min_required = 5

            self.add_result(ValidationResult(
                check_name="minimum_requirement_docs",
                passed=len(req_files) >= min_required,
                severity=ValidationSeverity.HIGH,
                message=f"Found {len(req_files)} requirement documents (minimum: {min_required})",
                details={"files": [f.name for f in req_files]},
                fix_suggestion=f"Add at least {min_required - len(req_files)} more requirement documents" if len(req_files) < min_required else None
            ))

            # Check 3: Key requirement documents exist
            key_docs = [
                "01_Product_Requirements_Document.md",
                "02_Functional_Requirements_Specification.md",
                "03_Non_Functional_Requirements.md",
                "04_User_Stories_and_Use_Cases.md"
            ]

            missing_docs = [doc for doc in key_docs if not (requirements_dir / doc).exists()]

            self.add_result(ValidationResult(
                check_name="key_requirement_documents",
                passed=len(missing_docs) == 0,
                severity=ValidationSeverity.HIGH,
                message=f"Key documents check: {len(key_docs) - len(missing_docs)}/{len(key_docs)} found",
                details={"missing": missing_docs},
                fix_suggestion=f"Create missing documents: {', '.join(missing_docs)}" if missing_docs else None
            ))

        # Generate report
        passed = sum(1 for r in self.results if r.passed)
        failed = sum(1 for r in self.results if not r.passed)
        critical = sum(1 for r in self.results if not r.passed and r.severity == ValidationSeverity.CRITICAL)

        overall_status = "passed" if critical == 0 and failed == 0 else ("failed" if critical > 0 else "warning")

        return PhaseValidationReport(
            phase_name="requirements",
            overall_status=overall_status,
            checks_passed=passed,
            checks_failed=failed,
            critical_failures=critical,
            results=self.results
        )


class DesignValidator(PhaseValidator):
    """Validates design phase outputs"""

    def validate(self) -> PhaseValidationReport:
        logger.info("=" * 80)
        logger.info("VALIDATING DESIGN PHASE")
        logger.info("=" * 80)

        self.results = []
        design_dir = self.workflow_dir / "design"

        # Check 1: Design directory exists
        if not design_dir.exists():
            self.add_result(ValidationResult(
                check_name="design_dir_exists",
                passed=False,
                severity=ValidationSeverity.CRITICAL,
                message="Design directory does not exist",
                fix_suggestion="Create design/ directory with architecture and API specifications"
            ))
        else:
            self.add_result(ValidationResult(
                check_name="design_dir_exists",
                passed=True,
                severity=ValidationSeverity.CRITICAL,
                message="Design directory found"
            ))

            # Check 2: Key design documents
            key_design_docs = [
                "01_SYSTEM_ARCHITECTURE.md",
                "02_DATABASE_SCHEMA_DESIGN.md",
                "03_API_DESIGN_SPECIFICATION.md",
                "04_UI_UX_DESIGN.md"
            ]

            found_docs = [doc for doc in key_design_docs if (design_dir / doc).exists()]

            self.add_result(ValidationResult(
                check_name="key_design_documents",
                passed=len(found_docs) >= 3,
                severity=ValidationSeverity.CRITICAL,
                message=f"Critical design documents: {len(found_docs)}/{len(key_design_docs)} found",
                details={"found": found_docs, "missing": [d for d in key_design_docs if d not in found_docs]},
                fix_suggestion="Create missing design documents before implementation"
            ))

            # Check 3: API specification completeness
            api_spec_path = design_dir / "03_API_DESIGN_SPECIFICATION.md"
            if api_spec_path.exists():
                content = api_spec_path.read_text()
                has_endpoints = "endpoint" in content.lower() or "route" in content.lower()
                has_methods = any(method in content for method in ["GET", "POST", "PUT", "DELETE"])

                self.add_result(ValidationResult(
                    check_name="api_specification_completeness",
                    passed=has_endpoints and has_methods,
                    severity=ValidationSeverity.HIGH,
                    message="API specification contains endpoints and HTTP methods" if (has_endpoints and has_methods) else "API specification incomplete",
                    fix_suggestion="Add detailed API endpoint specifications with HTTP methods" if not (has_endpoints and has_methods) else None
                ))

        # Generate report
        passed = sum(1 for r in self.results if r.passed)
        failed = sum(1 for r in self.results if not r.passed)
        critical = sum(1 for r in self.results if not r.passed and r.severity == ValidationSeverity.CRITICAL)

        overall_status = "passed" if critical == 0 and failed == 0 else ("failed" if critical > 0 else "warning")

        return PhaseValidationReport(
            phase_name="design",
            overall_status=overall_status,
            checks_passed=passed,
            checks_failed=failed,
            critical_failures=critical,
            results=self.results
        )


class ImplementationValidator(PhaseValidator):
    """Validates implementation phase outputs - MOST CRITICAL"""

    def validate(self) -> PhaseValidationReport:
        logger.info("=" * 80)
        logger.info("VALIDATING IMPLEMENTATION PHASE")
        logger.info("=" * 80)

        self.results = []
        impl_dir = self.workflow_dir / "implementation"

        if not impl_dir.exists():
            self.add_result(ValidationResult(
                check_name="implementation_dir_exists",
                passed=False,
                severity=ValidationSeverity.CRITICAL,
                message="Implementation directory does not exist",
                fix_suggestion="Create implementation/ directory with backend and frontend code"
            ))

            return PhaseValidationReport(
                phase_name="implementation",
                overall_status="failed",
                checks_passed=0,
                checks_failed=1,
                critical_failures=1,
                results=self.results
            )

        # Check 1: Backend implementation
        self._validate_backend(impl_dir)

        # Check 2: Frontend implementation
        self._validate_frontend(impl_dir)

        # Check 3: Package files and dependencies
        self._validate_dependencies(impl_dir)

        # Check 4: Configuration files
        self._validate_configuration(impl_dir)

        # Generate report
        passed = sum(1 for r in self.results if r.passed)
        failed = sum(1 for r in self.results if not r.passed)
        critical = sum(1 for r in self.results if not r.passed and r.severity == ValidationSeverity.CRITICAL)

        overall_status = "passed" if critical == 0 and failed == 0 else ("failed" if critical > 0 else "warning")

        return PhaseValidationReport(
            phase_name="implementation",
            overall_status=overall_status,
            checks_passed=passed,
            checks_failed=failed,
            critical_failures=critical,
            results=self.results
        )

    def _validate_backend(self, impl_dir: Path):
        """Validate backend implementation completeness"""
        backend_dir = impl_dir / "backend"

        if not backend_dir.exists():
            self.add_result(ValidationResult(
                check_name="backend_exists",
                passed=False,
                severity=ValidationSeverity.CRITICAL,
                message="Backend directory does not exist",
                fix_suggestion="Create backend/ directory with Node.js/Python API implementation"
            ))
            return

        self.add_result(ValidationResult(
            check_name="backend_exists",
            passed=True,
            severity=ValidationSeverity.CRITICAL,
            message="Backend directory found"
        ))

        src_dir = backend_dir / "src"
        if not src_dir.exists():
            self.add_result(ValidationResult(
                check_name="backend_src_exists",
                passed=False,
                severity=ValidationSeverity.CRITICAL,
                message="Backend src/ directory does not exist",
                fix_suggestion="Create backend/src/ with application code"
            ))
            return

        # Check for critical directories
        critical_dirs = ["routes", "services", "controllers"]
        found_dirs = [d for d in critical_dirs if (src_dir / d).exists()]

        self.add_result(ValidationResult(
            check_name="backend_structure",
            passed=len(found_dirs) >= 2,
            severity=ValidationSeverity.CRITICAL,
            message=f"Backend structure: {len(found_dirs)}/3 critical directories found ({', '.join(found_dirs) if found_dirs else 'none'})",
            details={"found": found_dirs, "missing": [d for d in critical_dirs if d not in found_dirs]},
            fix_suggestion=f"Create missing directories: {', '.join([d for d in critical_dirs if d not in found_dirs])}"
        ))

        # Check for TypeScript/JavaScript files
        ts_files = list(src_dir.rglob("*.ts")) + list(src_dir.rglob("*.js"))
        min_files = 20  # Reasonable minimum for a functional backend

        self.add_result(ValidationResult(
            check_name="backend_code_volume",
            passed=len(ts_files) >= min_files,
            severity=ValidationSeverity.CRITICAL,
            message=f"Backend code files: {len(ts_files)} found (minimum: {min_files})",
            details={"file_count": len(ts_files)},
            fix_suggestion=f"Backend only has {len(ts_files)} files, needs at least {min_files} for a functional API with routes, services, and middleware"
        ))

        # Check if server file exists and has imports
        server_files = list(src_dir.glob("server.*")) + list(src_dir.glob("app.*")) + list(src_dir.glob("index.*"))
        if server_files:
            server_file = server_files[0]
            content = server_file.read_text()

            # Check for route imports (critical)
            has_route_imports = "routes" in content.lower() or "router" in content.lower()

            self.add_result(ValidationResult(
                check_name="backend_has_routes",
                passed=has_route_imports,
                severity=ValidationSeverity.CRITICAL,
                message="Backend server imports route modules" if has_route_imports else "Backend server missing route imports",
                fix_suggestion="Implement route modules and import them in server file"
            ))

    def _validate_frontend(self, impl_dir: Path):
        """Validate frontend implementation completeness"""
        frontend_dir = impl_dir / "frontend"

        if not frontend_dir.exists():
            self.add_result(ValidationResult(
                check_name="frontend_exists",
                passed=False,
                severity=ValidationSeverity.CRITICAL,
                message="Frontend directory does not exist",
                fix_suggestion="Create frontend/ directory with React/Vue/Angular application"
            ))
            return

        self.add_result(ValidationResult(
            check_name="frontend_exists",
            passed=True,
            severity=ValidationSeverity.CRITICAL,
            message="Frontend directory found"
        ))

        src_dir = frontend_dir / "src"
        if not src_dir.exists():
            self.add_result(ValidationResult(
                check_name="frontend_src_exists",
                passed=False,
                severity=ValidationSeverity.CRITICAL,
                message="Frontend src/ directory does not exist",
                fix_suggestion="Create frontend/src/ with application code"
            ))
            return

        # Check for frontend files
        frontend_files = (
            list(src_dir.rglob("*.tsx")) +
            list(src_dir.rglob("*.jsx")) +
            list(src_dir.rglob("*.ts")) +
            list(src_dir.rglob("*.js")) +
            list(src_dir.rglob("*.vue"))
        )

        min_files = 10  # Minimum for a basic frontend

        self.add_result(ValidationResult(
            check_name="frontend_code_volume",
            passed=len(frontend_files) >= min_files,
            severity=ValidationSeverity.CRITICAL,
            message=f"Frontend code files: {len(frontend_files)} found (minimum: {min_files})",
            details={"file_count": len(frontend_files)},
            fix_suggestion=f"Frontend only has {len(frontend_files)} files, needs at least {min_files} for a functional UI"
        ))

        # Check for key frontend files
        key_files = ["App.tsx", "App.jsx", "App.vue", "main.tsx", "main.jsx", "index.tsx", "index.jsx"]
        has_app_file = any((src_dir / f).exists() or list(src_dir.rglob(f)) for f in key_files)

        self.add_result(ValidationResult(
            check_name="frontend_has_app_file",
            passed=has_app_file,
            severity=ValidationSeverity.CRITICAL,
            message="Frontend has main application file" if has_app_file else "Frontend missing main application file",
            fix_suggestion="Create App.tsx or equivalent main application component"
        ))

    def _validate_dependencies(self, impl_dir: Path):
        """Validate package files and dependencies"""
        backend_pkg = impl_dir / "backend" / "package.json"
        frontend_pkg = impl_dir / "frontend" / "package.json"

        # Check backend package.json
        if backend_pkg.exists():
            try:
                pkg_data = json.loads(backend_pkg.read_text())
                has_deps = "dependencies" in pkg_data and len(pkg_data["dependencies"]) > 0
                has_scripts = "scripts" in pkg_data and "start" in pkg_data["scripts"]

                self.add_result(ValidationResult(
                    check_name="backend_package_valid",
                    passed=has_deps and has_scripts,
                    severity=ValidationSeverity.HIGH,
                    message="Backend package.json is valid" if (has_deps and has_scripts) else "Backend package.json incomplete",
                    details={"has_dependencies": has_deps, "has_start_script": has_scripts},
                    fix_suggestion="Add dependencies and start script to backend/package.json"
                ))
            except json.JSONDecodeError:
                self.add_result(ValidationResult(
                    check_name="backend_package_valid",
                    passed=False,
                    severity=ValidationSeverity.HIGH,
                    message="Backend package.json is invalid JSON",
                    fix_suggestion="Fix JSON syntax in backend/package.json"
                ))

        # Check frontend package.json
        if frontend_pkg.exists():
            try:
                pkg_data = json.loads(frontend_pkg.read_text())
                has_deps = "dependencies" in pkg_data and len(pkg_data["dependencies"]) > 0
                has_build = "scripts" in pkg_data and "build" in pkg_data["scripts"]

                self.add_result(ValidationResult(
                    check_name="frontend_package_valid",
                    passed=has_deps and has_build,
                    severity=ValidationSeverity.HIGH,
                    message="Frontend package.json is valid" if (has_deps and has_build) else "Frontend package.json incomplete",
                    details={"has_dependencies": has_deps, "has_build_script": has_build},
                    fix_suggestion="Add dependencies and build script to frontend/package.json"
                ))
            except json.JSONDecodeError:
                self.add_result(ValidationResult(
                    check_name="frontend_package_valid",
                    passed=False,
                    severity=ValidationSeverity.HIGH,
                    message="Frontend package.json is invalid JSON",
                    fix_suggestion="Fix JSON syntax in frontend/package.json"
                ))

    def _validate_configuration(self, impl_dir: Path):
        """Validate configuration files"""
        env_example = impl_dir / ".env.example"

        if env_example.exists():
            content = env_example.read_text()
            key_vars = ["DATABASE", "PORT", "API"]
            found_vars = sum(1 for var in key_vars if var in content)

            self.add_result(ValidationResult(
                check_name="environment_config",
                passed=found_vars >= 2,
                severity=ValidationSeverity.MEDIUM,
                message=f"Environment configuration: {found_vars}/{len(key_vars)} key variables found",
                details={"variables_found": found_vars}
            ))


class TestingValidator(PhaseValidator):
    """Validates testing phase outputs"""

    def validate(self) -> PhaseValidationReport:
        logger.info("=" * 80)
        logger.info("VALIDATING TESTING PHASE")
        logger.info("=" * 80)

        self.results = []
        testing_dir = self.workflow_dir / "testing"
        impl_dir = self.workflow_dir / "implementation"

        if not testing_dir.exists():
            self.add_result(ValidationResult(
                check_name="testing_dir_exists",
                passed=False,
                severity=ValidationSeverity.CRITICAL,
                message="Testing directory does not exist",
                fix_suggestion="Create testing/ directory with test files"
            ))
        else:
            # Check 1: Test files exist
            test_files = (
                list(testing_dir.rglob("*.test.*")) +
                list(testing_dir.rglob("*.spec.*"))
            )

            self.add_result(ValidationResult(
                check_name="test_files_exist",
                passed=len(test_files) >= 3,
                severity=ValidationSeverity.HIGH,
                message=f"Found {len(test_files)} test files (minimum: 3)",
                details={"test_count": len(test_files)},
                fix_suggestion="Create at least 3 test files covering unit, integration, and E2E tests"
            ))

            # Check 2: Test files can import implementation code
            if test_files and impl_dir.exists():
                broken_imports = self._check_test_imports(test_files, impl_dir)

                self.add_result(ValidationResult(
                    check_name="test_imports_valid",
                    passed=len(broken_imports) == 0,
                    severity=ValidationSeverity.CRITICAL,
                    message=f"Test import validation: {len(test_files) - len(broken_imports)}/{len(test_files)} test files have valid imports",
                    details={"broken_imports": broken_imports},
                    fix_suggestion=f"Fix imports in test files: {', '.join([str(t) for t in broken_imports])}" if broken_imports else None
                ))

        passed = sum(1 for r in self.results if r.passed)
        failed = sum(1 for r in self.results if not r.passed)
        critical = sum(1 for r in self.results if not r.passed and r.severity == ValidationSeverity.CRITICAL)

        overall_status = "passed" if critical == 0 and failed == 0 else ("failed" if critical > 0 else "warning")

        return PhaseValidationReport(
            phase_name="testing",
            overall_status=overall_status,
            checks_passed=passed,
            checks_failed=failed,
            critical_failures=critical,
            results=self.results
        )

    def _check_test_imports(self, test_files: List[Path], impl_dir: Path) -> List[Path]:
        """Check if test files have valid imports"""
        broken = []

        for test_file in test_files[:10]:  # Check first 10 to avoid too much processing
            try:
                content = test_file.read_text()

                # Extract import/require statements
                imports = re.findall(r'(?:import|require)\s*\(?[\'"]([^\'"]+)[\'"]', content)

                for imp in imports:
                    # Check if it's a relative import to implementation code
                    if imp.startswith('..') or imp.startswith('./'):
                        # This is a simplified check - in production would need more sophisticated resolution
                        if '/services/' in imp or '/models/' in imp or '/controllers/' in imp:
                            # These are likely imports to implementation code
                            # If we found earlier that these directories don't exist, this is broken
                            backend_src = impl_dir / "backend" / "src"
                            if not (backend_src / "services").exists() and "/services/" in imp:
                                broken.append(test_file)
                                break
            except Exception as e:
                logger.warning(f"Could not parse test file {test_file}: {e}")

        return broken


class DeploymentValidator(PhaseValidator):
    """Validates deployment phase outputs"""

    def validate(self) -> PhaseValidationReport:
        logger.info("=" * 80)
        logger.info("VALIDATING DEPLOYMENT PHASE")
        logger.info("=" * 80)

        self.results = []
        deployment_dir = self.workflow_dir / "deployment"
        impl_dir = self.workflow_dir / "implementation"

        if not deployment_dir.exists():
            self.add_result(ValidationResult(
                check_name="deployment_dir_exists",
                passed=False,
                severity=ValidationSeverity.CRITICAL,
                message="Deployment directory does not exist",
                fix_suggestion="Create deployment/ directory with Docker and K8s configs"
            ))
        else:
            # Check 1: Dockerfile references
            self._validate_dockerfiles(deployment_dir, impl_dir)

            # Check 2: Docker Compose configuration
            self._validate_docker_compose(deployment_dir, impl_dir)

            # Check 3: Kubernetes manifests
            self._validate_kubernetes(deployment_dir)

        passed = sum(1 for r in self.results if r.passed)
        failed = sum(1 for r in self.results if not r.passed)
        critical = sum(1 for r in self.results if not r.passed and r.severity == ValidationSeverity.CRITICAL)

        overall_status = "passed" if critical == 0 and failed == 0 else ("failed" if critical > 0 else "warning")

        return PhaseValidationReport(
            phase_name="deployment",
            overall_status=overall_status,
            checks_passed=passed,
            checks_failed=failed,
            critical_failures=critical,
            results=self.results
        )

    def _validate_dockerfiles(self, deployment_dir: Path, impl_dir: Path):
        """Validate Dockerfile references to implementation code"""
        docker_dir = deployment_dir / "docker"
        if not docker_dir.exists():
            return

        dockerfiles = list(docker_dir.glob("Dockerfile.*"))

        for dockerfile in dockerfiles:
            service_name = dockerfile.name.replace("Dockerfile.", "")
            content = dockerfile.read_text()

            # Check if referenced service exists in implementation
            has_implementation = False

            if service_name == "backend":
                has_implementation = (impl_dir / "backend" / "src").exists()
            elif service_name == "frontend":
                has_implementation = (impl_dir / "frontend" / "src").exists()
            elif service_name in ["ai-service", "ml-service"]:
                has_implementation = (impl_dir / service_name).exists() or (impl_dir / "ml-services").exists()

            self.add_result(ValidationResult(
                check_name=f"dockerfile_{service_name}_valid",
                passed=has_implementation,
                severity=ValidationSeverity.CRITICAL if service_name in ["backend", "frontend"] else ValidationSeverity.HIGH,
                message=f"Dockerfile.{service_name} references {'existing' if has_implementation else 'non-existent'} implementation",
                details={"service": service_name, "dockerfile": str(dockerfile)},
                fix_suggestion=f"Implement {service_name} service in implementation/ directory" if not has_implementation else None
            ))

    def _validate_docker_compose(self, deployment_dir: Path, impl_dir: Path):
        """Validate Docker Compose service definitions"""
        compose_files = list(deployment_dir.rglob("docker-compose*.yml"))

        if not compose_files:
            return

        # Simple check - just verify services mentioned exist
        compose_file = compose_files[0]
        content = compose_file.read_text()

        services_defined = []
        if "frontend:" in content:
            services_defined.append("frontend")
        if "backend:" in content:
            services_defined.append("backend")
        if "ai-service:" in content or "ml-service:" in content:
            services_defined.append("ml-service")

        services_implemented = []
        if (impl_dir / "backend").exists():
            services_implemented.append("backend")
        if (impl_dir / "frontend").exists():
            services_implemented.append("frontend")

        missing_services = [s for s in services_defined if s not in services_implemented]

        self.add_result(ValidationResult(
            check_name="docker_compose_services",
            passed=len(missing_services) == 0,
            severity=ValidationSeverity.CRITICAL,
            message=f"Docker Compose: {len(services_implemented)}/{len(services_defined)} services implemented",
            details={"defined": services_defined, "implemented": services_implemented, "missing": missing_services},
            fix_suggestion=f"Implement missing services: {', '.join(missing_services)}" if missing_services else None
        ))

    def _validate_kubernetes(self, deployment_dir: Path):
        """Validate Kubernetes manifests exist"""
        k8s_dir = deployment_dir / "k8s"
        if not k8s_dir.exists():
            k8s_dir = deployment_dir / "kubernetes"

        if k8s_dir.exists():
            k8s_files = list(k8s_dir.glob("*.yaml")) + list(k8s_dir.glob("*.yml"))

            self.add_result(ValidationResult(
                check_name="kubernetes_manifests",
                passed=len(k8s_files) >= 3,
                severity=ValidationSeverity.MEDIUM,
                message=f"Kubernetes: {len(k8s_files)} manifest files found",
                details={"file_count": len(k8s_files)}
            ))


class WorkflowValidator:
    """Main validator that orchestrates all phase validations"""

    def __init__(self, workflow_dir: str):
        self.workflow_dir = Path(workflow_dir)
        self.validators = {
            "requirements": RequirementsValidator(self.workflow_dir),
            "design": DesignValidator(self.workflow_dir),
            "implementation": ImplementationValidator(self.workflow_dir),
            "testing": TestingValidator(self.workflow_dir),
            "deployment": DeploymentValidator(self.workflow_dir)
        }

    def validate_phase(self, phase_name: str) -> PhaseValidationReport:
        """Validate a specific phase"""
        if phase_name not in self.validators:
            raise ValueError(f"Unknown phase: {phase_name}")

        return self.validators[phase_name].validate()

    def validate_all(self) -> Dict[str, PhaseValidationReport]:
        """Validate all phases"""
        reports = {}

        for phase_name, validator in self.validators.items():
            reports[phase_name] = validator.validate()

        return reports

    def generate_summary_report(self, reports: Dict[str, PhaseValidationReport]) -> Dict[str, Any]:
        """Generate overall summary of validation results"""
        total_checks = sum(r.checks_passed + r.checks_failed for r in reports.values())
        total_passed = sum(r.checks_passed for r in reports.values())
        total_failed = sum(r.checks_failed for r in reports.values())
        total_critical = sum(r.critical_failures for r in reports.values())

        phases_passed = sum(1 for r in reports.values() if r.overall_status == "passed")
        phases_failed = sum(1 for r in reports.values() if r.overall_status == "failed")
        phases_warning = sum(1 for r in reports.values() if r.overall_status == "warning")

        overall_status = "passed" if phases_failed == 0 else "failed"

        return {
            "overall_status": overall_status,
            "summary": {
                "total_checks": total_checks,
                "checks_passed": total_passed,
                "checks_failed": total_failed,
                "critical_failures": total_critical
            },
            "phases": {
                "total": len(reports),
                "passed": phases_passed,
                "failed": phases_failed,
                "warnings": phases_warning
            },
            "phase_reports": {name: report.to_dict() for name, report in reports.items()},
            "deployment_ready": total_critical == 0
        }


def validate_workflow(workflow_dir: str, phase: Optional[str] = None) -> Dict[str, Any]:
    """
    Validate workflow outputs

    Args:
        workflow_dir: Path to workflow directory
        phase: Specific phase to validate, or None for all phases

    Returns:
        Validation report dictionary
    """
    validator = WorkflowValidator(workflow_dir)

    if phase:
        report = validator.validate_phase(phase)
        return report.to_dict()
    else:
        reports = validator.validate_all()
        return validator.generate_summary_report(reports)


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python workflow_validation.py <workflow_dir> [phase]")
        print("Example: python workflow_validation.py /tmp/maestro_workflow/wf-123456")
        print("Example: python workflow_validation.py /tmp/maestro_workflow/wf-123456 implementation")
        sys.exit(1)

    workflow_dir = sys.argv[1]
    phase = sys.argv[2] if len(sys.argv) > 2 else None

    result = validate_workflow(workflow_dir, phase)

    print("\n" + "=" * 80)
    print("VALIDATION REPORT")
    print("=" * 80)
    print(json.dumps(result, indent=2))

    # Exit with error code if validation failed
    if phase:
        sys.exit(0 if result["passed"] else 1)
    else:
        sys.exit(0 if result["overall_status"] == "passed" else 1)
