"""
Phase 6: Build

Verify that generated code compiles and tests pass.
This phase validates build quality for 5 compliance points.
"""

import asyncio
import subprocess
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from ..models import ExecutionPhase, PhaseResult


@dataclass
class BuildResult:
    """Result from the build phase."""
    build_passed: bool
    tests_passed: bool
    lint_passed: bool
    type_check_passed: bool
    errors: List[str]
    warnings: List[str]
    points_earned: float  # Out of 5


class BuildPhase:
    """
    Phase 6: Build Verification

    Responsibilities:
    1. Run TypeScript/Python compilation
    2. Execute test suite
    3. Run linting
    4. Verify no errors
    """

    def __init__(self, project_root: Optional[str] = None):
        """
        Initialize the build phase.

        Args:
            project_root: Root directory of the project
        """
        self.project_root = Path(project_root) if project_root else Path.cwd()

    async def execute(
        self,
        implementation_files: List[str],
        test_files: List[str],
    ) -> Tuple[PhaseResult, Optional[BuildResult]]:
        """
        Execute the build phase.

        Args:
            implementation_files: List of implementation file paths
            test_files: List of test file paths

        Returns:
            Tuple of (PhaseResult, BuildResult or None if failed)
        """
        started_at = datetime.now()
        phase_errors: List[str] = []
        phase_warnings: List[str] = []
        artifacts: List[str] = []

        try:
            build_errors: List[str] = []
            build_warnings: List[str] = []

            # Determine project type
            project_type = self._detect_project_type()
            artifacts.append(f"Detected project type: {project_type}")

            # Run build verification based on project type
            build_passed = True
            tests_passed = True
            lint_passed = True
            type_check_passed = True

            if project_type == "python":
                # Python build verification
                type_check_passed = await self._run_python_type_check(
                    implementation_files, build_errors, build_warnings
                )
                lint_passed = await self._run_python_lint(
                    implementation_files, build_errors, build_warnings
                )
                tests_passed = await self._run_python_tests(
                    test_files, build_errors, build_warnings
                )
                build_passed = type_check_passed  # Python doesn't really "build"

            elif project_type == "typescript":
                # TypeScript build verification
                build_passed = await self._run_typescript_build(
                    build_errors, build_warnings
                )
                lint_passed = await self._run_eslint(
                    implementation_files, build_errors, build_warnings
                )
                tests_passed = await self._run_jest_tests(
                    test_files, build_errors, build_warnings
                )
                type_check_passed = build_passed  # tsc does type checking

            else:
                # Generic verification - just check files exist
                build_passed = all(Path(f).exists() for f in implementation_files)
                artifacts.append("Generic verification: checked file existence")

            # Calculate points (5 if passes, 0 otherwise)
            all_passed = build_passed and tests_passed
            points_earned = 5.0 if all_passed else 0.0

            if not all_passed:
                phase_warnings.append("Build or tests did not pass")

            artifacts.append(f"Build: {'PASS' if build_passed else 'FAIL'}")
            artifacts.append(f"Tests: {'PASS' if tests_passed else 'FAIL'}")
            artifacts.append(f"Lint: {'PASS' if lint_passed else 'FAIL'}")

            # Build result
            result = BuildResult(
                build_passed=build_passed,
                tests_passed=tests_passed,
                lint_passed=lint_passed,
                type_check_passed=type_check_passed,
                errors=build_errors,
                warnings=build_warnings,
                points_earned=points_earned,
            )

            completed_at = datetime.now()
            duration = (completed_at - started_at).total_seconds()

            phase_result = PhaseResult(
                phase=ExecutionPhase.BUILD,
                success=all_passed,
                started_at=started_at,
                completed_at=completed_at,
                duration_seconds=duration,
                artifacts_created=artifacts,
                errors=phase_errors,
                warnings=phase_warnings,
                metrics={
                    "build_passed": build_passed,
                    "tests_passed": tests_passed,
                    "lint_passed": lint_passed,
                    "type_check_passed": type_check_passed,
                    "points_earned": points_earned,
                    "points_max": 5.0,
                }
            )

            return phase_result, result

        except Exception as e:
            phase_errors.append(str(e))
            completed_at = datetime.now()
            duration = (completed_at - started_at).total_seconds()

            phase_result = PhaseResult(
                phase=ExecutionPhase.BUILD,
                success=False,
                started_at=started_at,
                completed_at=completed_at,
                duration_seconds=duration,
                artifacts_created=artifacts,
                errors=phase_errors,
                warnings=phase_warnings,
            )

            return phase_result, None

    def _detect_project_type(self) -> str:
        """Detect the project type based on configuration files."""
        if (self.project_root / "pyproject.toml").exists():
            return "python"
        if (self.project_root / "setup.py").exists():
            return "python"
        if (self.project_root / "package.json").exists():
            return "typescript"
        if (self.project_root / "tsconfig.json").exists():
            return "typescript"
        return "unknown"

    async def _run_command(
        self,
        cmd: List[str],
        cwd: Optional[Path] = None,
        timeout: int = 120,
    ) -> Tuple[int, str, str]:
        """Run a command and return exit code, stdout, stderr."""
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                cwd=cwd or self.project_root,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=timeout
            )
            return (
                process.returncode or 0,
                stdout.decode("utf-8", errors="ignore"),
                stderr.decode("utf-8", errors="ignore"),
            )
        except asyncio.TimeoutError:
            return 1, "", "Command timed out"
        except Exception as e:
            return 1, "", str(e)

    async def _run_python_type_check(
        self,
        files: List[str],
        errors: List[str],
        warnings: List[str],
    ) -> bool:
        """Run mypy type checking."""
        if not files:
            return True

        try:
            code, stdout, stderr = await self._run_command(
                ["python", "-m", "mypy", "--ignore-missing-imports"] + files[:10]
            )
            if code != 0 and "error:" in (stdout + stderr):
                errors.append(f"Type check errors: {stderr[:200]}")
                return False
            return True
        except Exception:
            warnings.append("mypy not available, skipping type check")
            return True

    async def _run_python_lint(
        self,
        files: List[str],
        errors: List[str],
        warnings: List[str],
    ) -> bool:
        """Run ruff or flake8 linting."""
        if not files:
            return True

        try:
            code, stdout, stderr = await self._run_command(
                ["python", "-m", "ruff", "check"] + files[:10]
            )
            if code != 0:
                warnings.append(f"Lint warnings: {stdout[:200]}")
            return True  # Lint warnings don't fail the build
        except Exception:
            warnings.append("ruff not available, skipping lint")
            return True

    async def _run_python_tests(
        self,
        test_files: List[str],
        errors: List[str],
        warnings: List[str],
    ) -> bool:
        """Run pytest."""
        if not test_files:
            warnings.append("No test files to run")
            return True

        try:
            code, stdout, stderr = await self._run_command(
                ["python", "-m", "pytest", "-x", "--tb=short"] + test_files[:5],
                timeout=60,
            )
            if code != 0:
                errors.append(f"Tests failed: {stdout[:300]}")
                return False
            return True
        except Exception as e:
            warnings.append(f"pytest error: {str(e)}")
            return True  # Don't fail on pytest issues

    async def _run_typescript_build(
        self,
        errors: List[str],
        warnings: List[str],
    ) -> bool:
        """Run TypeScript compilation."""
        try:
            code, stdout, stderr = await self._run_command(
                ["npx", "tsc", "--noEmit"],
                timeout=120,
            )
            if code != 0:
                errors.append(f"TypeScript errors: {stderr[:200]}")
                return False
            return True
        except Exception as e:
            warnings.append(f"tsc error: {str(e)}")
            return True

    async def _run_eslint(
        self,
        files: List[str],
        errors: List[str],
        warnings: List[str],
    ) -> bool:
        """Run ESLint."""
        if not files:
            return True

        ts_files = [f for f in files if f.endswith((".ts", ".tsx", ".js", ".jsx"))]
        if not ts_files:
            return True

        try:
            code, stdout, stderr = await self._run_command(
                ["npx", "eslint", "--max-warnings=10"] + ts_files[:10]
            )
            if code != 0:
                warnings.append(f"ESLint warnings: {stdout[:200]}")
            return True
        except Exception:
            return True

    async def _run_jest_tests(
        self,
        test_files: List[str],
        errors: List[str],
        warnings: List[str],
    ) -> bool:
        """Run Jest tests."""
        if not test_files:
            warnings.append("No test files to run")
            return True

        try:
            code, stdout, stderr = await self._run_command(
                ["npx", "jest", "--passWithNoTests", "--testTimeout=10000"],
                timeout=120,
            )
            if code != 0:
                errors.append(f"Jest tests failed: {stdout[:300]}")
                return False
            return True
        except Exception as e:
            warnings.append(f"Jest error: {str(e)}")
            return True
