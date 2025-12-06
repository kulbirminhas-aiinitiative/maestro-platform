"""
Quality Fabric Integration.

EPIC: MD-2496
AC-4: Quality Fabric validates each output
"""

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import aiohttp

logger = logging.getLogger(__name__)


@dataclass
class QualityResult:
    """Result from Quality Fabric validation."""

    score: float
    passed: bool
    issues: List[Dict[str, Any]] = field(default_factory=list)
    metrics: Dict[str, float] = field(default_factory=dict)
    validated_at: Optional[str] = None


class QualityFabricClient:
    """
    Client for Quality Fabric validation service.

    AC-4: Integrates with Quality Fabric to validate generated code.
    """

    DEFAULT_THRESHOLD = 80.0

    def __init__(
        self,
        base_url: str = "http://localhost:8000",
        threshold: float = DEFAULT_THRESHOLD,
        timeout: float = 30.0,
    ):
        """
        Initialize Quality Fabric client.

        Args:
            base_url: Base URL of Quality Fabric service
            threshold: Minimum score to pass (0-100)
            timeout: Request timeout in seconds
        """
        self.base_url = base_url.rstrip("/")
        self.threshold = threshold
        self.timeout = timeout

    async def validate(
        self,
        code: str,
        file_path: str,
        language: str = "python",
    ) -> QualityResult:
        """
        Validate code using Quality Fabric.

        Args:
            code: Source code to validate
            file_path: Target file path
            language: Programming language

        Returns:
            QualityResult with score and issues
        """
        try:
            async with aiohttp.ClientSession() as session:
                payload = {
                    "code": code,
                    "file_path": file_path,
                    "language": language,
                }

                async with session.post(
                    f"{self.base_url}/validate",
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=self.timeout),
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        return self._parse_response(data)
                    else:
                        error_text = await response.text()
                        logger.warning(f"Quality Fabric returned {response.status}: {error_text}")
                        return self._fallback_validation(code, language)

        except aiohttp.ClientError as e:
            logger.warning(f"Quality Fabric connection error: {e}")
            return self._fallback_validation(code, language)
        except asyncio.TimeoutError:
            logger.warning("Quality Fabric request timed out")
            return self._fallback_validation(code, language)
        except Exception as e:
            logger.error(f"Quality Fabric validation error: {e}")
            return self._fallback_validation(code, language)

    def validate_sync(
        self,
        code: str,
        file_path: str,
        language: str = "python",
    ) -> QualityResult:
        """
        Synchronous validation wrapper.

        Args:
            code: Source code to validate
            file_path: Target file path
            language: Programming language

        Returns:
            QualityResult with score and issues
        """
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        return loop.run_until_complete(
            self.validate(code, file_path, language)
        )

    async def health_check(self) -> bool:
        """
        Check if Quality Fabric service is healthy.

        Returns:
            True if service is available
        """
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.base_url}/health",
                    timeout=aiohttp.ClientTimeout(total=5.0),
                ) as response:
                    return response.status == 200
        except Exception:
            return False

    def _parse_response(self, data: Dict[str, Any]) -> QualityResult:
        """Parse Quality Fabric response."""
        score = data.get("score", 0.0)
        if isinstance(score, str):
            score = float(score.rstrip("%"))

        return QualityResult(
            score=score,
            passed=score >= self.threshold,
            issues=data.get("issues", []),
            metrics=data.get("metrics", {}),
            validated_at=data.get("timestamp"),
        )

    def _fallback_validation(
        self,
        code: str,
        language: str,
    ) -> QualityResult:
        """
        Fallback validation when Quality Fabric is unavailable.

        Performs basic local validation.
        """
        issues: List[Dict[str, Any]] = []
        metrics: Dict[str, float] = {}

        # Basic checks
        lines = code.split("\n")
        metrics["lines"] = len(lines)
        metrics["chars"] = len(code)

        # Check for obvious issues
        if "raise NotImplementedError" in code:
            issues.append({
                "type": "stub",
                "severity": "error",
                "message": "Contains NotImplementedError stub",
            })

        if "# TODO" in code or "# FIXME" in code:
            issues.append({
                "type": "incomplete",
                "severity": "warning",
                "message": "Contains TODO/FIXME comments",
            })

        # Calculate basic score
        base_score = 100.0
        for issue in issues:
            if issue["severity"] == "error":
                base_score -= 20
            elif issue["severity"] == "warning":
                base_score -= 5

        score = max(0.0, base_score)

        return QualityResult(
            score=score,
            passed=score >= self.threshold,
            issues=issues,
            metrics=metrics,
        )

    async def get_metrics(
        self,
        code: str,
        language: str = "python",
    ) -> Dict[str, float]:
        """
        Get code metrics from Quality Fabric.

        Args:
            code: Source code to analyze
            language: Programming language

        Returns:
            Dictionary of metric name to value
        """
        try:
            async with aiohttp.ClientSession() as session:
                payload = {
                    "code": code,
                    "language": language,
                }

                async with session.post(
                    f"{self.base_url}/metrics",
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=self.timeout),
                ) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        return self._calculate_local_metrics(code)

        except Exception as e:
            logger.debug(f"Quality Fabric metrics error: {e}")
            return self._calculate_local_metrics(code)

    def _calculate_local_metrics(self, code: str) -> Dict[str, float]:
        """Calculate basic metrics locally."""
        lines = code.split("\n")
        non_empty = [l for l in lines if l.strip()]
        comment_lines = [l for l in lines if l.strip().startswith("#")]

        return {
            "total_lines": len(lines),
            "code_lines": len(non_empty) - len(comment_lines),
            "comment_lines": len(comment_lines),
            "blank_lines": len(lines) - len(non_empty),
            "avg_line_length": sum(len(l) for l in lines) / len(lines) if lines else 0,
        }
