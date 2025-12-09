#!/usr/bin/env python3
"""
Style Checker: Automated code style checking for compliance.

Enforces coding standards using configurable rules.
"""

import json
import re
import subprocess
import logging
from dataclasses import dataclass, asdict, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class StyleViolation:
    """A style violation."""
    file: str
    line: int
    column: int
    rule: str
    message: str
    severity: str  # error, warning, info

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class StyleCheckResult:
    """Result of style check."""
    id: str
    project_path: str
    timestamp: str
    files_checked: int
    violations: List[StyleViolation]
    passed: bool
    summary: Dict[str, int]

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data['violations'] = [v.to_dict() for v in self.violations]
        return data


class StyleChecker:
    """Automated style checking."""

    def __init__(
        self,
        config_path: Optional[str] = None,
        output_dir: Optional[str] = None
    ):
        self.config_path = Path(config_path) if config_path else None
        self.output_dir = Path(output_dir) if output_dir else Path.cwd() / 'style_reports'
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self._result_counter = 0

        # Default rules
        self._rules = {
            'line_length': {'max': 120, 'severity': 'warning'},
            'trailing_whitespace': {'severity': 'error'},
            'file_newline': {'severity': 'error'},
            'indent_size': {'size': 4, 'severity': 'warning'}
        }

    def check(
        self,
        project_path: str,
        file_patterns: Optional[List[str]] = None
    ) -> StyleCheckResult:
        """
        Check project for style violations.

        Args:
            project_path: Path to project
            file_patterns: Glob patterns for files to check

        Returns:
            StyleCheckResult
        """
        project_path = Path(project_path)
        file_patterns = file_patterns or ['**/*.py', '**/*.ts', '**/*.tsx']

        violations = []
        files_checked = 0

        for pattern in file_patterns:
            for file_path in project_path.glob(pattern):
                if file_path.is_file():
                    files_checked += 1
                    file_violations = self._check_file(file_path)
                    violations.extend(file_violations)

        # Try to run external linters
        violations.extend(self._run_external_linters(project_path))

        self._result_counter += 1
        result_id = f"STYLE-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}-{self._result_counter:04d}"

        # Summary
        summary = {
            'errors': sum(1 for v in violations if v.severity == 'error'),
            'warnings': sum(1 for v in violations if v.severity == 'warning'),
            'info': sum(1 for v in violations if v.severity == 'info')
        }

        passed = summary['errors'] == 0

        result = StyleCheckResult(
            id=result_id,
            project_path=str(project_path),
            timestamp=datetime.utcnow().isoformat(),
            files_checked=files_checked,
            violations=violations,
            passed=passed,
            summary=summary
        )

        # Save report
        output_file = self.output_dir / f"{result_id}.json"
        with open(output_file, 'w') as f:
            json.dump(result.to_dict(), f, indent=2)

        logger.info(f"Style check complete: {files_checked} files, "
                   f"{len(violations)} violations, passed={passed}")

        return result

    def _check_file(self, file_path: Path) -> List[StyleViolation]:
        """Check a single file."""
        violations = []

        try:
            with open(file_path, 'r') as f:
                lines = f.readlines()

            for i, line in enumerate(lines, 1):
                # Line length
                if len(line.rstrip()) > self._rules['line_length']['max']:
                    violations.append(StyleViolation(
                        file=str(file_path),
                        line=i,
                        column=self._rules['line_length']['max'],
                        rule='line_length',
                        message=f"Line too long ({len(line.rstrip())} > {self._rules['line_length']['max']})",
                        severity=self._rules['line_length']['severity']
                    ))

                # Trailing whitespace
                if line.rstrip() != line.rstrip('\n\r'):
                    violations.append(StyleViolation(
                        file=str(file_path),
                        line=i,
                        column=len(line.rstrip()) + 1,
                        rule='trailing_whitespace',
                        message="Trailing whitespace",
                        severity=self._rules['trailing_whitespace']['severity']
                    ))

            # File should end with newline
            if lines and not lines[-1].endswith('\n'):
                violations.append(StyleViolation(
                    file=str(file_path),
                    line=len(lines),
                    column=1,
                    rule='file_newline',
                    message="File should end with a newline",
                    severity=self._rules['file_newline']['severity']
                ))

        except Exception as e:
            logger.debug(f"Error checking {file_path}: {e}")

        return violations

    def _run_external_linters(self, project_path: Path) -> List[StyleViolation]:
        """Run external linters if available."""
        violations = []

        # Try ruff for Python
        try:
            result = subprocess.run(
                ['ruff', 'check', '--format=json', '.'],
                capture_output=True,
                text=True,
                cwd=project_path,
                timeout=60
            )
            if result.stdout:
                ruff_violations = json.loads(result.stdout)
                for v in ruff_violations:
                    violations.append(StyleViolation(
                        file=v.get('filename', ''),
                        line=v.get('location', {}).get('row', 0),
                        column=v.get('location', {}).get('column', 0),
                        rule=v.get('code', 'ruff'),
                        message=v.get('message', ''),
                        severity='warning'
                    ))
        except (subprocess.SubprocessError, FileNotFoundError, json.JSONDecodeError):
            pass

        return violations


def get_style_checker(**kwargs) -> StyleChecker:
    """Get style checker instance."""
    return StyleChecker(**kwargs)
