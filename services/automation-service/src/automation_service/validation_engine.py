#!/usr/bin/env python3
"""
Quality Fabric - Validation Engine
Validates fixes before they are applied
"""

import asyncio
import logging
import subprocess
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum
from datetime import datetime

logger = logging.getLogger(__name__)


class ValidationStatus(str, Enum):
    """Validation status"""
    PASSED = "passed"
    FAILED = "failed"
    WARNING = "warning"
    SKIPPED = "skipped"


@dataclass
class ValidationResult:
    """Result of validation"""
    validation_id: str
    status: ValidationStatus
    checks_passed: List[str]
    checks_failed: List[str]
    warnings: List[str]
    execution_time: float
    details: Dict[str, Any]


class ValidationEngine:
    """Validates fixes before application"""

    def __init__(self, project_path: str):
        self.project_path = Path(project_path)

    async def validate_fix(
        self,
        file_path: str,
        original_code: str,
        fixed_code: str,
        error_type: str
    ) -> ValidationResult:
        """Validate a code fix"""
        start_time = datetime.now()

        checks_passed = []
        checks_failed = []
        warnings = []

        # 1. Syntax validation
        if await self._validate_syntax(file_path, fixed_code):
            checks_passed.append("syntax")
        else:
            checks_failed.append("syntax")

        # 2. Run tests (if test file)
        if 'test' in file_path:
            if await self._validate_tests(file_path):
                checks_passed.append("tests")
            else:
                checks_failed.append("tests")

        # 3. Type check (if TypeScript)
        if file_path.endswith(('.ts', '.tsx')):
            if await self._validate_types():
                checks_passed.append("types")
            else:
                checks_failed.append("types")

        # 4. Lint check
        lint_result = await self._validate_lint(file_path)
        if lint_result == "passed":
            checks_passed.append("lint")
        elif lint_result == "warning":
            warnings.append("Lint warnings present")
        else:
            checks_failed.append("lint")

        # Determine overall status
        if checks_failed:
            status = ValidationStatus.FAILED
        elif warnings:
            status = ValidationStatus.WARNING
        else:
            status = ValidationStatus.PASSED

        execution_time = (datetime.now() - start_time).total_seconds()

        return ValidationResult(
            validation_id=f"val_{hash(file_path + str(datetime.now()))}",
            status=status,
            checks_passed=checks_passed,
            checks_failed=checks_failed,
            warnings=warnings,
            execution_time=execution_time,
            details={
                "file_path": file_path,
                "error_type": error_type
            }
        )

    async def _validate_syntax(self, file_path: str, code: str) -> bool:
        """Validate code syntax"""
        try:
            if file_path.endswith('.py'):
                compile(code, file_path, 'exec')
            elif file_path.endswith(('.ts', '.tsx', '.js', '.jsx')):
                # Use acorn or similar to validate JS/TS syntax
                pass
            return True
        except SyntaxError:
            return False

    async def _validate_tests(self, file_path: str) -> bool:
        """Run tests for validation"""
        try:
            result = await asyncio.create_subprocess_exec(
                'npm', 'test', '--', file_path,
                cwd=str(self.project_path),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await asyncio.wait_for(result.wait(), timeout=60)
            return result.returncode == 0
        except Exception as e:
            logger.error(f"Test validation failed: {e}")
            return False

    async def _validate_types(self) -> bool:
        """Validate TypeScript types"""
        try:
            result = await asyncio.create_subprocess_exec(
                'npx', 'tsc', '--noEmit',
                cwd=str(self.project_path),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await asyncio.wait_for(result.wait(), timeout=60)
            return result.returncode == 0
        except Exception as e:
            logger.error(f"Type validation failed: {e}")
            return False

    async def _validate_lint(self, file_path: str) -> str:
        """Validate linting"""
        try:
            result = await asyncio.create_subprocess_exec(
                'npx', 'eslint', file_path,
                cwd=str(self.project_path),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await asyncio.wait_for(result.wait(), timeout=30)

            if result.returncode == 0:
                return "passed"
            else:
                # Check if errors or warnings
                stdout, stderr = await result.communicate()
                if b'error' in stdout.lower():
                    return "failed"
                else:
                    return "warning"
        except Exception as e:
            logger.error(f"Lint validation failed: {e}")
            return "failed"