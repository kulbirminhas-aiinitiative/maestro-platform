#!/usr/bin/env python3
"""
Enhanced Workflow Build Validation

Addresses critical gap identified in Batch 5 analysis:
- Current validation checks file existence and count
- Enhanced validation checks BUILD SUCCESS and FUNCTIONALITY

Root Cause: Validation measured wrong metrics (77% validation, 0% can build)
Solution: Add build testing, stub detection, and feature completeness checks

Reference: BATCH5_WORKFLOW_SYSTEM_ANALYSIS.md
"""

import os
import json
import logging
import subprocess
import re
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import asyncio

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class BuildValidationSeverity(Enum):
    """Severity levels for build validation failures"""
    CRITICAL = "critical"  # Application won't build/run
    HIGH = "high"          # Major functionality missing
    MEDIUM = "medium"      # Minor issues
    LOW = "low"            # Informational


@dataclass
class BuildValidationResult:
    """Result of a build validation check"""
    check_name: str
    passed: bool
    severity: BuildValidationSeverity
    message: str
    details: Dict[str, Any] = field(default_factory=dict)
    fix_suggestion: Optional[str] = None
    evidence: List[str] = field(default_factory=list)


@dataclass
class BuildValidationReport:
    """Complete build validation report"""
    workflow_id: str
    overall_status: str  # "passed", "failed", "warning"
    can_build: bool  # Critical: Does it actually build?
    checks_passed: int
    checks_failed: int
    critical_failures: int
    results: List[BuildValidationResult] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "workflow_id": self.workflow_id,
            "overall_status": self.overall_status,
            "can_build": self.can_build,
            "checks_passed": self.checks_passed,
            "checks_failed": self.checks_failed,
            "critical_failures": self.critical_failures,
            "build_success_rate": self.checks_passed / max(self.checks_passed + self.checks_failed, 1),
            "results": [
                {
                    "check": r.check_name,
                    "passed": r.passed,
                    "severity": r.severity.value,
                    "message": r.message,
                    "details": r.details,
                    "fix_suggestion": r.fix_suggestion,
                    "evidence": r.evidence
                }
                for r in self.results
            ]
        }


class BuildValidator:
    """
    Enhanced validator that checks if generated code actually builds and runs

    Validation Hierarchy (NEW):
    1. CRITICAL: Can it build? (npm install, npm build, docker build)
    2. HIGH: Is it functional? (No stubs, features implemented)
    3. MEDIUM: Is it complete? (Tests, docs, configuration)
    4. LOW: Is it optimized? (Performance, best practices)

    Old Hierarchy (WRONG):
    1. File count (40%) - WRONG METRIC
    2. Directory structure (30%) - WRONG METRIC
    3. Syntax valid (30%) - INSUFFICIENT
    """

    def __init__(self, workflow_dir: Path):
        self.workflow_dir = Path(workflow_dir)
        self.results: List[BuildValidationResult] = []

    def add_result(self, result: BuildValidationResult):
        """Add a validation result"""
        self.results.append(result)

        if result.passed:
            logger.info(f"✅ {result.check_name}: PASSED")
        else:
            level = logging.CRITICAL if result.severity == BuildValidationSeverity.CRITICAL else logging.WARNING
            logger.log(level, f"❌ {result.check_name}: FAILED - {result.message}")
            if result.evidence:
                for evidence in result.evidence[:3]:  # Show first 3 pieces of evidence
                    logger.log(level, f"   Evidence: {evidence}")

    async def validate(self) -> BuildValidationReport:
        """Run all build validations"""
        logger.info("=" * 80)
        logger.info("ENHANCED BUILD VALIDATION (Batch 5 Fixes)")
        logger.info("=" * 80)

        self.results = []
        impl_dir = self.workflow_dir / "implementation"

        if not impl_dir.exists():
            self.add_result(BuildValidationResult(
                check_name="implementation_dir_exists",
                passed=False,
                severity=BuildValidationSeverity.CRITICAL,
                message="Implementation directory does not exist",
                fix_suggestion="Run implementation phase to generate code"
            ))
            return self._generate_report()

        # ===== CRITICAL: BUILD SUCCESS CHECKS =====
        logger.info("\n🔨 CRITICAL: Build Success Checks")
        await self._validate_backend_builds(impl_dir)
        await self._validate_frontend_builds(impl_dir)
        await self._validate_docker_builds(impl_dir)

        # ===== HIGH: FUNCTIONALITY CHECKS =====
        logger.info("\n🎯 HIGH: Functionality Checks")
        await self._detect_stub_implementations(impl_dir)
        await self._validate_feature_completeness(impl_dir)
        await self._validate_dependency_coherence(impl_dir)

        # ===== MEDIUM: COMPLETENESS CHECKS =====
        logger.info("\n📋 MEDIUM: Completeness Checks")
        await self._validate_error_handling(impl_dir)
        await self._validate_configuration_completeness(impl_dir)

        return self._generate_report()

    async def _validate_backend_builds(self, impl_dir: Path):
        """CRITICAL: Validate backend can be built successfully"""
        backend_dir = impl_dir / "backend"

        if not backend_dir.exists():
            self.add_result(BuildValidationResult(
                check_name="backend_build_test",
                passed=False,
                severity=BuildValidationSeverity.CRITICAL,
                message="Backend directory does not exist",
                fix_suggestion="Create backend implementation"
            ))
            return

        package_json = backend_dir / "package.json"
        if not package_json.exists():
            self.add_result(BuildValidationResult(
                check_name="backend_build_test",
                passed=False,
                severity=BuildValidationSeverity.CRITICAL,
                message="Backend package.json missing",
                fix_suggestion="Create package.json with dependencies and build scripts"
            ))
            return

        # Test 1: Can we install dependencies?
        logger.info("  Testing: npm install (backend)...")
        install_result = await self._run_npm_command("install", backend_dir, timeout=120)

        if not install_result["success"]:
            self.add_result(BuildValidationResult(
                check_name="backend_npm_install",
                passed=False,
                severity=BuildValidationSeverity.CRITICAL,
                message="Backend npm install failed",
                details={"exit_code": install_result["exit_code"]},
                evidence=[install_result["error"]],
                fix_suggestion="Fix dependency errors in package.json"
            ))
            return
        else:
            self.add_result(BuildValidationResult(
                check_name="backend_npm_install",
                passed=True,
                severity=BuildValidationSeverity.CRITICAL,
                message="Backend dependencies install successfully"
            ))

        # Test 2: Can we build the project?
        logger.info("  Testing: npm run build (backend)...")
        build_result = await self._run_npm_command("run build", backend_dir, timeout=180)

        if not build_result["success"]:
            self.add_result(BuildValidationResult(
                check_name="backend_build_success",
                passed=False,
                severity=BuildValidationSeverity.CRITICAL,
                message="Backend build failed",
                details={"exit_code": build_result["exit_code"]},
                evidence=[build_result["error"]],
                fix_suggestion="Fix TypeScript/build errors in backend code"
            ))
        else:
            self.add_result(BuildValidationResult(
                check_name="backend_build_success",
                passed=True,
                severity=BuildValidationSeverity.CRITICAL,
                message="Backend builds successfully",
                details={"output": build_result["output"][:200]}
            ))

    async def _validate_frontend_builds(self, impl_dir: Path):
        """CRITICAL: Validate frontend can be built successfully"""
        frontend_dir = impl_dir / "frontend"

        if not frontend_dir.exists():
            self.add_result(BuildValidationResult(
                check_name="frontend_build_test",
                passed=False,
                severity=BuildValidationSeverity.CRITICAL,
                message="Frontend directory does not exist",
                fix_suggestion="Create frontend implementation"
            ))
            return

        package_json = frontend_dir / "package.json"
        if not package_json.exists():
            self.add_result(BuildValidationResult(
                check_name="frontend_build_test",
                passed=False,
                severity=BuildValidationSeverity.CRITICAL,
                message="Frontend package.json missing",
                fix_suggestion="Create package.json with dependencies and build scripts"
            ))
            return

        # Test 1: Can we install dependencies?
        logger.info("  Testing: npm install (frontend)...")
        install_result = await self._run_npm_command("install", frontend_dir, timeout=120)

        if not install_result["success"]:
            self.add_result(BuildValidationResult(
                check_name="frontend_npm_install",
                passed=False,
                severity=BuildValidationSeverity.CRITICAL,
                message="Frontend npm install failed",
                details={"exit_code": install_result["exit_code"]},
                evidence=[install_result["error"]],
                fix_suggestion="Fix dependency errors in package.json"
            ))
            return
        else:
            self.add_result(BuildValidationResult(
                check_name="frontend_npm_install",
                passed=True,
                severity=BuildValidationSeverity.CRITICAL,
                message="Frontend dependencies install successfully"
            ))

        # Test 2: Can we build the project?
        logger.info("  Testing: npm run build (frontend)...")
        build_result = await self._run_npm_command("run build", frontend_dir, timeout=180)

        if not build_result["success"]:
            self.add_result(BuildValidationResult(
                check_name="frontend_build_success",
                passed=False,
                severity=BuildValidationSeverity.CRITICAL,
                message="Frontend build failed",
                details={"exit_code": build_result["exit_code"]},
                evidence=[build_result["error"]],
                fix_suggestion="Fix TypeScript/Vite/build errors in frontend code"
            ))
        else:
            self.add_result(BuildValidationResult(
                check_name="frontend_build_success",
                passed=True,
                severity=BuildValidationSeverity.CRITICAL,
                message="Frontend builds successfully",
                details={"output": build_result["output"][:200]}
            ))

    async def _validate_docker_builds(self, impl_dir: Path):
        """CRITICAL: Validate Docker images can be built"""
        deployment_dir = self.workflow_dir / "deployment"

        if not deployment_dir.exists():
            logger.info("  ⚠️  No deployment directory - skipping Docker build tests")
            return

        docker_dir = deployment_dir / "docker"
        if not docker_dir.exists():
            logger.info("  ⚠️  No docker directory - skipping Docker build tests")
            return

        dockerfiles = list(docker_dir.glob("Dockerfile.*"))
        if not dockerfiles:
            logger.info("  ⚠️  No Dockerfiles found - skipping Docker build tests")
            return

        # Test backend Dockerfile
        backend_dockerfile = docker_dir / "Dockerfile.backend"
        if backend_dockerfile.exists():
            logger.info("  Testing: docker build (backend)...")
            docker_result = await self._run_docker_build(
                backend_dockerfile,
                "test-backend",
                impl_dir / "backend"
            )

            if docker_result["success"]:
                self.add_result(BuildValidationResult(
                    check_name="docker_build_backend",
                    passed=True,
                    severity=BuildValidationSeverity.CRITICAL,
                    message="Backend Docker image builds successfully"
                ))
            else:
                self.add_result(BuildValidationResult(
                    check_name="docker_build_backend",
                    passed=False,
                    severity=BuildValidationSeverity.HIGH,  # Not critical if npm build works
                    message="Backend Docker build failed",
                    evidence=[docker_result["error"]],
                    fix_suggestion="Fix Dockerfile.backend - check COPY paths and base image"
                ))

        # Test frontend Dockerfile
        frontend_dockerfile = docker_dir / "Dockerfile.frontend"
        if frontend_dockerfile.exists():
            logger.info("  Testing: docker build (frontend)...")
            docker_result = await self._run_docker_build(
                frontend_dockerfile,
                "test-frontend",
                impl_dir / "frontend"
            )

            if docker_result["success"]:
                self.add_result(BuildValidationResult(
                    check_name="docker_build_frontend",
                    passed=True,
                    severity=BuildValidationSeverity.CRITICAL,
                    message="Frontend Docker image builds successfully"
                ))
            else:
                self.add_result(BuildValidationResult(
                    check_name="docker_build_frontend",
                    passed=False,
                    severity=BuildValidationSeverity.HIGH,
                    message="Frontend Docker build failed",
                    evidence=[docker_result["error"]],
                    fix_suggestion="Fix Dockerfile.frontend - check COPY paths and nginx config"
                ))

    async def _detect_stub_implementations(self, impl_dir: Path):
        """HIGH: Detect stub/placeholder implementations that don't work"""

        # Pattern 1: 501 Not Implemented responses
        stub_patterns = [
            (r'res\.status\(501\)', "Express 501 response"),
            (r'return.*501', "501 status code"),
            (r'["\']Not implemented["\']', "Not implemented string"),
            (r'["\']TODO:', "TODO comment"),
            (r'throw new Error\(["\']Not implemented', "Not implemented error"),
            (r'# TODO:', "Python TODO"),
            (r'pass\s*#.*not.*implemented', "Python pass with not implemented"),
        ]

        stub_files = []
        total_files_checked = 0

        # Check backend files
        backend_src = impl_dir / "backend" / "src"
        if backend_src.exists():
            for file_path in backend_src.rglob("*.ts"):
                total_files_checked += 1
                content = file_path.read_text()

                for pattern, description in stub_patterns:
                    if re.search(pattern, content, re.IGNORECASE):
                        stub_files.append({
                            "file": str(file_path.relative_to(impl_dir)),
                            "pattern": description
                        })
                        break  # Only count once per file

        # Check frontend files
        frontend_src = impl_dir / "frontend" / "src"
        if frontend_src.exists():
            for file_path in frontend_src.rglob("*.tsx"):
                total_files_checked += 1
                content = file_path.read_text()

                for pattern, description in stub_patterns:
                    if re.search(pattern, content, re.IGNORECASE):
                        stub_files.append({
                            "file": str(file_path.relative_to(impl_dir)),
                            "pattern": description
                        })
                        break

        stub_percentage = len(stub_files) / max(total_files_checked, 1)

        if stub_percentage > 0.3:  # More than 30% stubs
            self.add_result(BuildValidationResult(
                check_name="stub_implementation_detection",
                passed=False,
                severity=BuildValidationSeverity.CRITICAL,
                message=f"High stub implementation rate: {len(stub_files)}/{total_files_checked} files ({stub_percentage:.0%})",
                details={"stub_files": stub_files[:10]},  # First 10
                evidence=[f"{s['file']}: {s['pattern']}" for s in stub_files[:5]],
                fix_suggestion="Replace stub implementations with actual working code"
            ))
        elif stub_percentage > 0.1:  # More than 10% stubs
            self.add_result(BuildValidationResult(
                check_name="stub_implementation_detection",
                passed=False,
                severity=BuildValidationSeverity.HIGH,
                message=f"Moderate stub implementation rate: {len(stub_files)}/{total_files_checked} files ({stub_percentage:.0%})",
                details={"stub_files": stub_files},
                evidence=[f"{s['file']}: {s['pattern']}" for s in stub_files[:3]],
                fix_suggestion="Complete implementation of stubbed features"
            ))
        else:
            self.add_result(BuildValidationResult(
                check_name="stub_implementation_detection",
                passed=True,
                severity=BuildValidationSeverity.HIGH,
                message=f"Low stub rate: {len(stub_files)}/{total_files_checked} files ({stub_percentage:.0%})",
                details={"stub_files": stub_files}
            ))

    async def _validate_feature_completeness(self, impl_dir: Path):
        """HIGH: Validate that features from PRD are implemented"""

        # Check if PRD exists
        requirements_dir = self.workflow_dir / "requirements"
        prd_file = requirements_dir / "01_Product_Requirements_Document.md"

        if not prd_file.exists():
            logger.info("  ⚠️  No PRD found - skipping feature completeness check")
            return

        prd_content = prd_file.read_text()

        # Extract feature keywords from PRD (simplified approach)
        # In production, would use AI to extract features
        feature_keywords = self._extract_feature_keywords(prd_content)

        # Check if features are implemented in code
        implemented_features = []
        missing_features = []

        backend_src = impl_dir / "backend" / "src"
        frontend_src = impl_dir / "frontend" / "src"

        all_code = ""
        if backend_src.exists():
            for file_path in backend_src.rglob("*.ts"):
                all_code += file_path.read_text().lower()
        if frontend_src.exists():
            for file_path in frontend_src.rglob("*.tsx"):
                all_code += file_path.read_text().lower()

        for feature in feature_keywords:
            # Simple check: is feature keyword in code?
            if feature.lower() in all_code:
                implemented_features.append(feature)
            else:
                missing_features.append(feature)

        if len(feature_keywords) == 0:
            logger.info("  ⚠️  No features extracted from PRD")
            return

        implementation_rate = len(implemented_features) / len(feature_keywords)

        if implementation_rate < 0.5:  # Less than 50% implemented
            self.add_result(BuildValidationResult(
                check_name="feature_completeness",
                passed=False,
                severity=BuildValidationSeverity.CRITICAL,
                message=f"Low feature implementation: {len(implemented_features)}/{len(feature_keywords)} features ({implementation_rate:.0%})",
                details={"missing_features": missing_features[:10]},
                evidence=[f"Missing: {f}" for f in missing_features[:5]],
                fix_suggestion="Implement missing features from PRD"
            ))
        elif implementation_rate < 0.8:  # Less than 80% implemented
            self.add_result(BuildValidationResult(
                check_name="feature_completeness",
                passed=False,
                severity=BuildValidationSeverity.HIGH,
                message=f"Moderate feature implementation: {len(implemented_features)}/{len(feature_keywords)} features ({implementation_rate:.0%})",
                details={"missing_features": missing_features},
                evidence=[f"Missing: {f}" for f in missing_features[:3]],
                fix_suggestion="Complete remaining features from PRD"
            ))
        else:
            self.add_result(BuildValidationResult(
                check_name="feature_completeness",
                passed=True,
                severity=BuildValidationSeverity.HIGH,
                message=f"Good feature implementation: {len(implemented_features)}/{len(feature_keywords)} features ({implementation_rate:.0%})",
                details={"implemented_features": implemented_features}
            ))

    async def _validate_dependency_coherence(self, impl_dir: Path):
        """HIGH: Validate that dependencies match what code actually uses"""

        backend_pkg = impl_dir / "backend" / "package.json"
        if not backend_pkg.exists():
            return

        try:
            pkg_data = json.loads(backend_pkg.read_text())
            declared_deps = set(pkg_data.get("dependencies", {}).keys())

            # Check what's actually imported in code
            backend_src = impl_dir / "backend" / "src"
            if not backend_src.exists():
                return

            used_imports = set()
            for file_path in backend_src.rglob("*.ts"):
                content = file_path.read_text()
                # Extract imports
                imports = re.findall(r'import\s+.*?\s+from\s+["\']([^"\']+)["\']', content)
                for imp in imports:
                    # Get package name (before first /)
                    if not imp.startswith('.'):  # External package
                        pkg_name = imp.split('/')[0]
                        if pkg_name.startswith('@'):  # Scoped package
                            pkg_name = imp.split('/')[0] + '/' + imp.split('/')[1]
                        used_imports.add(pkg_name)

            # Check for commonly used but missing dependencies
            common_deps = {
                'express': ['express', 'app.use', 'app.get'],
                'typeorm': ['typeorm', 'Entity', 'Repository'],
                'cors': ['cors'],
                'helmet': ['helmet'],
                'morgan': ['morgan'],
            }

            missing_deps = []
            for dep, indicators in common_deps.items():
                if dep not in declared_deps:
                    # Check if any indicator is in code
                    code_content = ""
                    for file_path in backend_src.rglob("*.ts"):
                        code_content += file_path.read_text()

                    if any(ind in code_content for ind in indicators):
                        missing_deps.append(dep)

            if missing_deps:
                self.add_result(BuildValidationResult(
                    check_name="dependency_coherence",
                    passed=False,
                    severity=BuildValidationSeverity.HIGH,
                    message=f"Missing {len(missing_deps)} dependencies that code uses",
                    details={"missing": missing_deps},
                    evidence=[f"Code uses {dep} but it's not in package.json" for dep in missing_deps],
                    fix_suggestion=f"Add to package.json: {', '.join(missing_deps)}"
                ))
            else:
                self.add_result(BuildValidationResult(
                    check_name="dependency_coherence",
                    passed=True,
                    severity=BuildValidationSeverity.HIGH,
                    message="Dependencies are coherent with code imports"
                ))

        except Exception as e:
            logger.warning(f"  ⚠️  Could not validate dependency coherence: {e}")

    async def _validate_error_handling(self, impl_dir: Path):
        """MEDIUM: Check for proper error handling"""
        backend_src = impl_dir / "backend" / "src"
        if not backend_src.exists():
            return

        files_with_try_catch = 0
        total_route_files = 0

        routes_dir = backend_src / "routes"
        if routes_dir.exists():
            for file_path in routes_dir.rglob("*.ts"):
                total_route_files += 1
                content = file_path.read_text()

                if "try" in content and "catch" in content:
                    files_with_try_catch += 1

        if total_route_files == 0:
            return

        error_handling_rate = files_with_try_catch / total_route_files

        if error_handling_rate < 0.5:
            self.add_result(BuildValidationResult(
                check_name="error_handling",
                passed=False,
                severity=BuildValidationSeverity.MEDIUM,
                message=f"Low error handling coverage: {files_with_try_catch}/{total_route_files} route files ({error_handling_rate:.0%})",
                fix_suggestion="Add try-catch blocks to route handlers"
            ))
        else:
            self.add_result(BuildValidationResult(
                check_name="error_handling",
                passed=True,
                severity=BuildValidationSeverity.MEDIUM,
                message=f"Good error handling coverage: {files_with_try_catch}/{total_route_files} route files ({error_handling_rate:.0%})"
            ))

    async def _validate_configuration_completeness(self, impl_dir: Path):
        """MEDIUM: Check for complete configuration files"""

        checks = [
            (impl_dir / "backend" / "tsconfig.json", "Backend TypeScript config"),
            (impl_dir / "frontend" / "tsconfig.json", "Frontend TypeScript config"),
            (impl_dir / "frontend" / "vite.config.ts", "Vite config"),
            (impl_dir / ".env.example", "Environment variables example"),
        ]

        missing_configs = []
        for file_path, description in checks:
            if not file_path.exists():
                missing_configs.append(description)

        if len(missing_configs) > 2:
            self.add_result(BuildValidationResult(
                check_name="configuration_completeness",
                passed=False,
                severity=BuildValidationSeverity.MEDIUM,
                message=f"Missing {len(missing_configs)} configuration files",
                details={"missing": missing_configs},
                fix_suggestion="Create missing configuration files"
            ))
        elif len(missing_configs) > 0:
            self.add_result(BuildValidationResult(
                check_name="configuration_completeness",
                passed=True,
                severity=BuildValidationSeverity.MEDIUM,
                message=f"Most configs present ({len(missing_configs)} missing)",
                details={"missing": missing_configs}
            ))
        else:
            self.add_result(BuildValidationResult(
                check_name="configuration_completeness",
                passed=True,
                severity=BuildValidationSeverity.MEDIUM,
                message="All configuration files present"
            ))

    # ===== HELPER METHODS =====

    async def _run_npm_command(self, command: str, cwd: Path, timeout: int = 60) -> Dict[str, Any]:
        """Run npm command and return result"""
        try:
            process = await asyncio.create_subprocess_exec(
                "npm", *command.split(),
                cwd=str(cwd),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=timeout
                )
            except asyncio.TimeoutError:
                process.kill()
                return {
                    "success": False,
                    "exit_code": -1,
                    "output": "",
                    "error": f"Command timed out after {timeout}s"
                }

            return {
                "success": process.returncode == 0,
                "exit_code": process.returncode,
                "output": stdout.decode('utf-8', errors='ignore'),
                "error": stderr.decode('utf-8', errors='ignore')
            }

        except Exception as e:
            return {
                "success": False,
                "exit_code": -1,
                "output": "",
                "error": str(e)
            }

    async def _run_docker_build(self, dockerfile: Path, tag: str, context: Path) -> Dict[str, Any]:
        """Run docker build and return result"""
        try:
            process = await asyncio.create_subprocess_exec(
                "docker", "build",
                "-f", str(dockerfile),
                "-t", tag,
                str(context),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=300  # 5 minutes for Docker builds
                )
            except asyncio.TimeoutError:
                process.kill()
                return {
                    "success": False,
                    "error": "Docker build timed out after 5 minutes"
                }

            return {
                "success": process.returncode == 0,
                "output": stdout.decode('utf-8', errors='ignore'),
                "error": stderr.decode('utf-8', errors='ignore')
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    def _extract_feature_keywords(self, prd_content: str) -> List[str]:
        """Extract feature keywords from PRD (simplified)"""
        # Look for feature sections
        features = []

        # Common feature section headers
        feature_patterns = [
            r'##\s+Features?\s*\n(.*?)(?=\n##|\Z)',
            r'##\s+Core Features?\s*\n(.*?)(?=\n##|\Z)',
            r'##\s+Key Features?\s*\n(.*?)(?=\n##|\Z)',
        ]

        for pattern in feature_patterns:
            matches = re.findall(pattern, prd_content, re.DOTALL | re.IGNORECASE)
            for match in matches:
                # Extract bullet points
                bullets = re.findall(r'[-*]\s+([^\n]+)', match)
                for bullet in bullets:
                    # Extract first 2-3 words as feature keyword
                    words = bullet.split()[:3]
                    if len(words) >= 2:
                        feature = ' '.join(words).strip('.,;:')
                        if len(feature) > 3:  # Skip very short features
                            features.append(feature)

        # Deduplicate
        return list(set(features))[:20]  # Max 20 features

    def _generate_report(self) -> BuildValidationReport:
        """Generate validation report"""
        passed = sum(1 for r in self.results if r.passed)
        failed = sum(1 for r in self.results if not r.passed)
        critical = sum(1 for r in self.results if not r.passed and r.severity == BuildValidationSeverity.CRITICAL)

        # Critical: Can it build?
        build_checks = [
            "backend_build_success",
            "frontend_build_success",
        ]
        can_build = all(
            any(r.check_name == check and r.passed for r in self.results)
            for check in build_checks
            if any(r.check_name == check for r in self.results)
        )

        overall_status = "passed" if critical == 0 and failed == 0 else ("failed" if critical > 0 or not can_build else "warning")

        return BuildValidationReport(
            workflow_id=self.workflow_dir.name,
            overall_status=overall_status,
            can_build=can_build,
            checks_passed=passed,
            checks_failed=failed,
            critical_failures=critical,
            results=self.results
        )


async def validate_workflow_builds(workflow_dir: str) -> BuildValidationReport:
    """
    Validate workflow with build testing

    Usage:
        report = await validate_workflow_builds("/tmp/maestro_workflow/wf-123456")
        if report.can_build:
            print("✅ Workflow builds successfully")
        else:
            print("❌ Workflow cannot build")
    """
    validator = BuildValidator(Path(workflow_dir))
    return await validator.validate()


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python workflow_build_validation.py <workflow_dir>")
        print("Example: python workflow_build_validation.py /tmp/maestro_workflow/wf-1760179880-5e4b549c")
        sys.exit(1)

    workflow_dir = sys.argv[1]

    async def main():
        print(f"\n🔍 Running Enhanced Build Validation on {workflow_dir}\n")
        report = await validate_workflow_builds(workflow_dir)

        print("\n" + "=" * 80)
        print("BUILD VALIDATION REPORT")
        print("=" * 80)
        print(json.dumps(report.to_dict(), indent=2))

        print("\n" + "=" * 80)
        print("SUMMARY")
        print("=" * 80)
        print(f"Overall Status: {report.overall_status.upper()}")
        print(f"Can Build: {'✅ YES' if report.can_build else '❌ NO'}")
        print(f"Checks Passed: {report.checks_passed}")
        print(f"Checks Failed: {report.checks_failed}")
        print(f"Critical Failures: {report.critical_failures}")
        print(f"Build Success Rate: {report.checks_passed / max(report.checks_passed + report.checks_failed, 1):.0%}")

        # Exit with error code if validation failed
        sys.exit(0 if report.can_build else 1)

    asyncio.run(main())
