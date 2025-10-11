"""
Screenshot Diff Validator
Version: 1.0.0

Validates visual consistency by comparing screenshots using perceptual diff.
"""

from typing import Dict, Any
from pathlib import Path
import logging

from contracts.validators.base import BaseValidator, ValidationResult, ValidationError

logger = logging.getLogger(__name__)


class ScreenshotDiffValidator(BaseValidator):
    """
    Validates visual consistency between expected and actual screenshots.

    Uses perceptual difference algorithms to detect visual regressions.

    Configuration:
        threshold: float (0.0-1.0) - Minimum similarity score to pass (default: 0.95)
        ignore_antialiasing: bool - Ignore antialiasing differences (default: True)
        ignore_colors: bool - Compare structure only, ignore colors (default: False)
        diff_output_path: str - Path to save diff image (optional)
    """

    def __init__(self, timeout_seconds: float = 60.0):
        """
        Initialize ScreenshotDiffValidator.

        Args:
            timeout_seconds: Maximum execution time (default: 60s for image processing)
        """
        super().__init__(
            validator_name="ScreenshotDiffValidator",
            validator_version="1.0.0",
            timeout_seconds=timeout_seconds
        )

    async def validate(
        self,
        artifacts: Dict[str, Any],
        config: Dict[str, Any]
    ) -> ValidationResult:
        """
        Validate screenshot similarity.

        Args:
            artifacts: {
                "actual": Path to actual screenshot,
                "expected": Path to expected screenshot,
                "diff_output": Optional path to save diff image
            }
            config: {
                "threshold": 0.95,  # Similarity threshold (0.0-1.0)
                "ignore_antialiasing": True,
                "ignore_colors": False,
                "diff_output_path": "/tmp/diff.png"  # Optional
            }

        Returns:
            ValidationResult with similarity score and diff evidence
        """
        # Extract paths
        actual_path = artifacts.get("actual")
        expected_path = artifacts.get("expected")

        if not actual_path or not expected_path:
            raise ValidationError("Missing required artifacts: 'actual' and 'expected' screenshots")

        # Ensure paths exist
        actual_file = Path(actual_path)
        expected_file = Path(expected_path)

        if not actual_file.exists():
            raise ValidationError(f"Actual screenshot not found: {actual_path}")

        if not expected_file.exists():
            raise ValidationError(f"Expected screenshot not found: {expected_path}")

        # Get configuration
        threshold = config.get("threshold", 0.95)
        ignore_antialiasing = config.get("ignore_antialiasing", True)
        ignore_colors = config.get("ignore_colors", False)
        diff_output_path = config.get("diff_output_path", artifacts.get("diff_output"))

        # Validate threshold
        if not 0.0 <= threshold <= 1.0:
            raise ValidationError(f"Invalid threshold: {threshold} (must be between 0.0 and 1.0)")

        # Perform image comparison
        try:
            similarity_score = await self._compare_images(
                actual_file,
                expected_file,
                ignore_antialiasing=ignore_antialiasing,
                ignore_colors=ignore_colors,
                diff_output_path=diff_output_path
            )

            passed = similarity_score >= threshold

            # Build result message
            if passed:
                message = f"Visual consistency verified (similarity: {similarity_score:.2%})"
            else:
                message = f"Visual regression detected (similarity: {similarity_score:.2%}, threshold: {threshold:.2%})"

            # Collect evidence
            evidence = {
                "similarity_score": similarity_score,
                "threshold": threshold,
                "actual_path": str(actual_path),
                "expected_path": str(expected_path),
                "ignore_antialiasing": ignore_antialiasing,
                "ignore_colors": ignore_colors
            }

            if diff_output_path:
                evidence["diff_image_path"] = str(diff_output_path)

            # Build warnings
            warnings = []
            if similarity_score < threshold:
                diff_percentage = (1.0 - similarity_score) * 100
                warnings.append(f"Visual difference: {diff_percentage:.2f}%")

            return ValidationResult(
                passed=passed,
                score=similarity_score,
                message=message,
                details=f"Compared {actual_file.name} with {expected_file.name}",
                evidence=evidence,
                warnings=warnings if not passed else []
            )

        except Exception as e:
            logger.exception("Screenshot comparison failed")
            raise ValidationError(f"Screenshot comparison failed: {str(e)}")

    async def _compare_images(
        self,
        actual_path: Path,
        expected_path: Path,
        ignore_antialiasing: bool = True,
        ignore_colors: bool = False,
        diff_output_path: str = None
    ) -> float:
        """
        Compare two images and return similarity score.

        Uses PIL (Pillow) for image processing.

        Args:
            actual_path: Path to actual image
            expected_path: Path to expected image
            ignore_antialiasing: Ignore antialiasing differences
            ignore_colors: Compare structure only
            diff_output_path: Path to save diff image

        Returns:
            Similarity score (0.0 = completely different, 1.0 = identical)
        """
        try:
            from PIL import Image, ImageChops
            import numpy as np
        except ImportError:
            raise ValidationError(
                "PIL (Pillow) is required for screenshot comparison. "
                "Install with: pip install Pillow"
            )

        # Load images
        actual_img = Image.open(actual_path)
        expected_img = Image.open(expected_path)

        # Ensure same size
        if actual_img.size != expected_img.size:
            logger.warning(
                f"Image size mismatch: actual={actual_img.size}, expected={expected_img.size}. "
                "Resizing actual to match expected."
            )
            actual_img = actual_img.resize(expected_img.size, Image.Resampling.LANCZOS)

        # Convert to RGB if needed
        if actual_img.mode != 'RGB':
            actual_img = actual_img.convert('RGB')
        if expected_img.mode != 'RGB':
            expected_img = expected_img.convert('RGB')

        # Convert to grayscale if ignoring colors
        if ignore_colors:
            actual_img = actual_img.convert('L')
            expected_img = expected_img.convert('L')

        # Calculate difference
        diff = ImageChops.difference(actual_img, expected_img)

        # Convert to numpy for analysis
        diff_array = np.array(diff)

        # Calculate similarity
        if ignore_antialiasing:
            # Use a threshold to ignore minor differences (antialiasing)
            threshold_value = 10  # Ignore differences < 10/255
            significant_diff = diff_array > threshold_value
            diff_ratio = np.mean(significant_diff)
        else:
            # Calculate exact pixel difference
            diff_ratio = np.mean(diff_array) / 255.0

        similarity_score = 1.0 - diff_ratio

        # Save diff image if requested
        if diff_output_path:
            # Enhance diff for visibility
            diff_enhanced = diff.point(lambda x: x * 10)  # Amplify differences
            diff_enhanced.save(diff_output_path)
            logger.info(f"Diff image saved to: {diff_output_path}")

        return similarity_score


# ============================================================================
# Module Exports
# ============================================================================

__all__ = [
    "ScreenshotDiffValidator",
]
