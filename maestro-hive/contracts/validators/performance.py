"""
Performance Validator
Version: 1.0.0

Validates performance metrics against thresholds.
"""

from typing import Dict, Any
from pathlib import Path
import logging
import json

from contracts.validators.base import BaseValidator, ValidationResult, ValidationError

logger = logging.getLogger(__name__)


class PerformanceValidator(BaseValidator):
    """
    Validates performance metrics against configured thresholds.

    Checks:
    - Page load time
    - Time to First Byte (TTFB)
    - First Contentful Paint (FCP)
    - Largest Contentful Paint (LCP)
    - Time to Interactive (TTI)
    - Cumulative Layout Shift (CLS)
    - API response times

    Configuration:
        max_load_time_ms: int - Maximum page load time in milliseconds
        max_ttfb_ms: int - Maximum Time to First Byte
        max_fcp_ms: int - Maximum First Contentful Paint
        max_lcp_ms: int - Maximum Largest Contentful Paint (2.5s for good)
        max_tti_ms: int - Maximum Time to Interactive
        max_cls: float - Maximum Cumulative Layout Shift (0.1 for good)
        max_api_response_ms: int - Maximum API response time
    """

    def __init__(self, timeout_seconds: float = 30.0):
        """
        Initialize PerformanceValidator.

        Args:
            timeout_seconds: Maximum execution time (default: 30s)
        """
        super().__init__(
            validator_name="PerformanceValidator",
            validator_version="1.0.0",
            timeout_seconds=timeout_seconds
        )

    async def validate(
        self,
        artifacts: Dict[str, Any],
        config: Dict[str, Any]
    ) -> ValidationResult:
        """
        Validate performance metrics.

        Args:
            artifacts: {
                "metrics": Path to performance metrics JSON or dict with metrics
            }
            config: {
                "max_load_time_ms": 3000,
                "max_ttfb_ms": 600,
                "max_fcp_ms": 1800,
                "max_lcp_ms": 2500,
                "max_tti_ms": 3800,
                "max_cls": 0.1,
                "max_api_response_ms": 500
            }

        Returns:
            ValidationResult with performance analysis
        """
        # Extract metrics
        metrics_artifact = artifacts.get("metrics")

        if not metrics_artifact:
            raise ValidationError("Missing required artifact: 'metrics'")

        # Load metrics
        if isinstance(metrics_artifact, dict):
            metrics = metrics_artifact
        else:
            metrics = await self._load_metrics(metrics_artifact)

        # Get thresholds from config (with defaults based on Web Vitals)
        thresholds = {
            "max_load_time_ms": config.get("max_load_time_ms", 3000),
            "max_ttfb_ms": config.get("max_ttfb_ms", 600),
            "max_fcp_ms": config.get("max_fcp_ms", 1800),
            "max_lcp_ms": config.get("max_lcp_ms", 2500),  # Web Vitals: good < 2.5s
            "max_tti_ms": config.get("max_tti_ms", 3800),
            "max_cls": config.get("max_cls", 0.1),  # Web Vitals: good < 0.1
            "max_api_response_ms": config.get("max_api_response_ms", 500)
        }

        # Validate metrics
        violations = []
        warnings = []
        passed_checks = []

        # Check each metric
        checks = [
            ("load_time_ms", "max_load_time_ms", "Page Load Time"),
            ("ttfb_ms", "max_ttfb_ms", "Time to First Byte"),
            ("fcp_ms", "max_fcp_ms", "First Contentful Paint"),
            ("lcp_ms", "max_lcp_ms", "Largest Contentful Paint"),
            ("tti_ms", "max_tti_ms", "Time to Interactive"),
            ("cls", "max_cls", "Cumulative Layout Shift"),
            ("api_response_ms", "max_api_response_ms", "API Response Time")
        ]

        for metric_key, threshold_key, metric_name in checks:
            if metric_key in metrics:
                actual_value = metrics[metric_key]
                threshold = thresholds[threshold_key]

                if actual_value > threshold:
                    violations.append(
                        f"{metric_name}: {actual_value} exceeds threshold {threshold}"
                    )
                elif actual_value > threshold * 0.8:  # Within 80% of threshold
                    warnings.append(
                        f"{metric_name}: {actual_value} approaching threshold {threshold}"
                    )
                else:
                    passed_checks.append(metric_name)

        # Calculate score
        total_checks = len(passed_checks) + len(violations) + len(warnings)
        if total_checks > 0:
            score = (len(passed_checks) + 0.5 * len(warnings)) / total_checks
        else:
            score = 0.0

        # Determine pass/fail
        passed = len(violations) == 0

        # Build message
        if passed:
            if warnings:
                message = f"Performance acceptable with {len(warnings)} warnings"
            else:
                message = "All performance metrics within thresholds"
        else:
            message = f"Performance violations: {len(violations)} metrics exceeded thresholds"

        # Collect evidence
        evidence = {
            "metrics": metrics,
            "thresholds": thresholds,
            "passed_checks": passed_checks,
            "violations_count": len(violations),
            "warnings_count": len(warnings)
        }

        # Add Web Vitals assessment if available
        if "lcp_ms" in metrics and "cls" in metrics:
            lcp_score = "good" if metrics["lcp_ms"] <= 2500 else "needs improvement" if metrics["lcp_ms"] <= 4000 else "poor"
            cls_score = "good" if metrics["cls"] <= 0.1 else "needs improvement" if metrics["cls"] <= 0.25 else "poor"

            evidence["web_vitals_assessment"] = {
                "lcp": lcp_score,
                "cls": cls_score
            }

        return ValidationResult(
            passed=passed,
            score=score,
            message=message,
            details=f"Validated {total_checks} performance metrics, {len(passed_checks)} passed",
            evidence=evidence,
            errors=violations,
            warnings=warnings
        )

    async def _load_metrics(self, metrics_path: str) -> Dict[str, Any]:
        """Load performance metrics from JSON file."""
        path = Path(metrics_path)

        if not path.exists():
            raise ValidationError(f"Performance metrics not found: {metrics_path}")

        try:
            with open(path, 'r') as f:
                return json.load(f)
        except Exception as e:
            raise ValidationError(f"Failed to load performance metrics: {str(e)}")


# ============================================================================
# Module Exports
# ============================================================================

__all__ = [
    "PerformanceValidator",
]
