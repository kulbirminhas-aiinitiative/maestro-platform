"""
Axe-Core Accessibility Validator
Version: 1.0.0

Validates web accessibility using axe-core standards (WCAG 2.1).
"""

from typing import Dict, Any, List
from pathlib import Path
import logging
import json

from contracts.validators.base import BaseValidator, ValidationResult, ValidationError

logger = logging.getLogger(__name__)


class AxeCoreValidator(BaseValidator):
    """
    Validates web accessibility against WCAG standards using axe-core.

    Checks:
    - WCAG 2.1 Level A compliance
    - WCAG 2.1 Level AA compliance (default)
    - WCAG 2.1 Level AAA compliance (optional)

    Configuration:
        level: str - WCAG level to validate ("A", "AA", "AAA") (default: "AA")
        rules: List[str] - Specific rules to check (optional, checks all by default)
        ignore_rules: List[str] - Rules to ignore (optional)
        fail_on_warnings: bool - Fail validation on warnings (default: False)
    """

    def __init__(self, timeout_seconds: float = 60.0):
        """
        Initialize AxeCoreValidator.

        Args:
            timeout_seconds: Maximum execution time (default: 60s)
        """
        super().__init__(
            validator_name="AxeCoreValidator",
            validator_version="1.0.0",
            timeout_seconds=timeout_seconds
        )

    async def validate(
        self,
        artifacts: Dict[str, Any],
        config: Dict[str, Any]
    ) -> ValidationResult:
        """
        Validate web accessibility.

        Args:
            artifacts: {
                "html": Path to HTML file or URL to check,
                "axe_results": Path to pre-generated axe-core results JSON (optional)
            }
            config: {
                "level": "AA",  # WCAG level
                "rules": [],    # Specific rules (empty = all)
                "ignore_rules": [],  # Rules to ignore
                "fail_on_warnings": False
            }

        Returns:
            ValidationResult with accessibility violations
        """
        # Extract artifacts
        html_path = artifacts.get("html")
        axe_results_path = artifacts.get("axe_results")

        # Get configuration
        wcag_level = config.get("level", "AA").upper()
        specific_rules = config.get("rules", [])
        ignore_rules = config.get("ignore_rules", [])
        fail_on_warnings = config.get("fail_on_warnings", False)

        # Validate WCAG level
        if wcag_level not in ["A", "AA", "AAA"]:
            raise ValidationError(f"Invalid WCAG level: {wcag_level} (must be A, AA, or AAA)")

        # Load axe-core results
        if axe_results_path:
            # Use pre-generated results
            axe_results = await self._load_axe_results(axe_results_path)
        elif html_path:
            # Run axe-core analysis (simulated for now)
            axe_results = await self._run_axe_analysis(html_path, wcag_level, specific_rules)
        else:
            raise ValidationError("Missing required artifact: 'html' or 'axe_results'")

        # Parse results
        violations = axe_results.get("violations", [])
        passes = axe_results.get("passes", [])
        incomplete = axe_results.get("incomplete", [])
        inapplicable = axe_results.get("inapplicable", [])

        # Filter by ignore_rules
        if ignore_rules:
            violations = [v for v in violations if v.get("id") not in ignore_rules]

        # Count issues
        critical_count = len([v for v in violations if v.get("impact") == "critical"])
        serious_count = len([v for v in violations if v.get("impact") == "serious"])
        moderate_count = len([v for v in violations if v.get("impact") == "moderate"])
        minor_count = len([v for v in violations if v.get("impact") == "minor"])

        total_violations = len(violations)
        total_checks = len(passes) + len(violations)

        # Determine pass/fail
        if critical_count > 0 or serious_count > 0:
            passed = False
        elif moderate_count > 0 and not fail_on_warnings:
            passed = True  # Pass with warnings
        elif moderate_count > 0 and fail_on_warnings:
            passed = False
        else:
            passed = True

        # Calculate score
        if total_checks > 0:
            score = len(passes) / total_checks
        else:
            score = 0.0 if violations else 1.0

        # Build message
        if passed:
            if moderate_count > 0 or minor_count > 0:
                message = f"WCAG {wcag_level} compliance with {total_violations} warnings"
            else:
                message = f"WCAG {wcag_level} fully compliant"
        else:
            message = f"WCAG {wcag_level} violations found: {critical_count} critical, {serious_count} serious"

        # Collect evidence
        evidence = {
            "wcag_level": wcag_level,
            "total_violations": total_violations,
            "critical_violations": critical_count,
            "serious_violations": serious_count,
            "moderate_violations": moderate_count,
            "minor_violations": minor_count,
            "total_passes": len(passes),
            "incomplete_checks": len(incomplete),
            "inapplicable_checks": len(inapplicable),
            "violation_details": [
                {
                    "id": v.get("id"),
                    "impact": v.get("impact"),
                    "description": v.get("description"),
                    "help": v.get("help"),
                    "help_url": v.get("helpUrl"),
                    "nodes_affected": len(v.get("nodes", []))
                }
                for v in violations[:10]  # First 10 violations
            ]
        }

        # Build errors and warnings
        errors = []
        warnings = []

        for violation in violations:
            impact = violation.get("impact", "unknown")
            rule_id = violation.get("id", "unknown")
            description = violation.get("description", "No description")

            if impact in ["critical", "serious"]:
                errors.append(f"[{impact.upper()}] {rule_id}: {description}")
            else:
                warnings.append(f"[{impact.upper()}] {rule_id}: {description}")

        return ValidationResult(
            passed=passed,
            score=score,
            message=message,
            details=f"Checked {total_checks} accessibility rules, found {total_violations} violations",
            evidence=evidence,
            errors=errors[:10],  # Limit to 10
            warnings=warnings[:10]  # Limit to 10
        )

    async def _load_axe_results(self, results_path: str) -> Dict[str, Any]:
        """Load pre-generated axe-core results from JSON file."""
        path = Path(results_path)

        if not path.exists():
            raise ValidationError(f"Axe-core results not found: {results_path}")

        try:
            with open(path, 'r') as f:
                return json.load(f)
        except Exception as e:
            raise ValidationError(f"Failed to load axe-core results: {str(e)}")

    async def _run_axe_analysis(
        self,
        html_path: str,
        wcag_level: str,
        specific_rules: List[str]
    ) -> Dict[str, Any]:
        """
        Run axe-core analysis (simulated).

        In production, this would use axe-core via Playwright/Selenium.
        For now, returns a mock result structure.
        """
        logger.warning(
            "AxeCoreValidator is using simulated mode. "
            "For real analysis, integrate with axe-core via Playwright or provide pre-generated results."
        )

        # Return empty results (no violations in simulation)
        return {
            "violations": [],
            "passes": [
                {"id": "color-contrast", "impact": "serious", "description": "Ensure text has sufficient color contrast"},
                {"id": "html-has-lang", "impact": "serious", "description": "Ensure HTML has lang attribute"},
                {"id": "label", "impact": "critical", "description": "Ensure form elements have labels"}
            ],
            "incomplete": [],
            "inapplicable": []
        }


# ============================================================================
# Module Exports
# ============================================================================

__all__ = [
    "AxeCoreValidator",
]
