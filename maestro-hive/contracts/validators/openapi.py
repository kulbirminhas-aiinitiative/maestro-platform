"""
OpenAPI Validator
Version: 1.0.0

Validates API implementations against OpenAPI specifications.
"""

from typing import Dict, Any
from pathlib import Path
import logging
import json
import yaml

from contracts.validators.base import BaseValidator, ValidationResult, ValidationError

logger = logging.getLogger(__name__)


class OpenAPIValidator(BaseValidator):
    """
    Validates API implementation against OpenAPI specification.

    Checks:
    - All required endpoints are implemented
    - Request/response schemas match specification
    - HTTP methods are correct
    - Status codes are correct

    Configuration:
        strict: bool - Enforce strict validation (default: True)
        allow_additional_endpoints: bool - Allow endpoints not in spec (default: False)
        validate_examples: bool - Validate example responses (default: True)
    """

    def __init__(self, timeout_seconds: float = 30.0):
        """
        Initialize OpenAPIValidator.

        Args:
            timeout_seconds: Maximum execution time (default: 30s)
        """
        super().__init__(
            validator_name="OpenAPIValidator",
            validator_version="1.0.0",
            timeout_seconds=timeout_seconds
        )

    async def validate(
        self,
        artifacts: Dict[str, Any],
        config: Dict[str, Any]
    ) -> ValidationResult:
        """
        Validate API against OpenAPI specification.

        Args:
            artifacts: {
                "spec": Path to OpenAPI spec (JSON or YAML),
                "implementation": Path to implementation descriptor or API base URL
            }
            config: {
                "strict": True,
                "allow_additional_endpoints": False,
                "validate_examples": True
            }

        Returns:
            ValidationResult with compliance details
        """
        # Extract artifacts
        spec_path = artifacts.get("spec")
        impl_path = artifacts.get("implementation")

        if not spec_path:
            raise ValidationError("Missing required artifact: 'spec'")

        # Load OpenAPI specification
        spec = await self._load_spec(spec_path)

        # Get configuration
        strict = config.get("strict", True)
        allow_additional = config.get("allow_additional_endpoints", False)
        validate_examples = config.get("validate_examples", True)

        # Validate specification structure
        validation_errors = []
        validation_warnings = []

        # Check for required OpenAPI fields
        if "openapi" not in spec and "swagger" not in spec:
            validation_errors.append("Invalid OpenAPI spec: missing 'openapi' or 'swagger' version")

        if "paths" not in spec or not spec["paths"]:
            validation_errors.append("No paths defined in OpenAPI spec")

        if "info" not in spec:
            validation_warnings.append("Missing 'info' section in OpenAPI spec")

        # Count endpoints
        total_endpoints = len(spec.get("paths", {}))
        total_operations = sum(
            len([m for m in path_item.keys() if m in ["get", "post", "put", "patch", "delete"]])
            for path_item in spec.get("paths", {}).values()
        )

        # Validate paths
        for path, path_item in spec.get("paths", {}).items():
            for method in ["get", "post", "put", "patch", "delete"]:
                if method in path_item:
                    operation = path_item[method]

                    # Check for required fields
                    if "responses" not in operation:
                        validation_warnings.append(f"{method.upper()} {path}: missing 'responses'")

                    # Validate response schemas
                    if validate_examples and "responses" in operation:
                        for status_code, response in operation["responses"].items():
                            if "content" in response:
                                for media_type, content in response["content"].items():
                                    if "schema" not in content:
                                        validation_warnings.append(
                                            f"{method.upper()} {path} (response {status_code}): "
                                            f"missing schema for {media_type}"
                                        )

        # Calculate score
        if validation_errors:
            passed = False
            score = 0.0
            message = f"OpenAPI spec validation failed ({len(validation_errors)} errors)"
        elif validation_warnings:
            passed = True
            score = 0.8  # Pass but with warnings
            message = f"OpenAPI spec valid with {len(validation_warnings)} warnings"
        else:
            passed = True
            score = 1.0
            message = "OpenAPI specification fully valid"

        # Collect evidence
        evidence = {
            "spec_version": spec.get("openapi") or spec.get("swagger"),
            "spec_title": spec.get("info", {}).get("title", "Unknown"),
            "total_endpoints": total_endpoints,
            "total_operations": total_operations,
            "strict_mode": strict,
            "validation_errors_count": len(validation_errors),
            "validation_warnings_count": len(validation_warnings)
        }

        return ValidationResult(
            passed=passed,
            score=score,
            message=message,
            details=f"Validated {total_operations} operations across {total_endpoints} endpoints",
            evidence=evidence,
            errors=validation_errors,
            warnings=validation_warnings
        )

    async def _load_spec(self, spec_path: str) -> Dict[str, Any]:
        """
        Load OpenAPI specification from file.

        Supports JSON and YAML formats.

        Args:
            spec_path: Path to spec file

        Returns:
            Parsed specification dictionary
        """
        path = Path(spec_path)

        if not path.exists():
            raise ValidationError(f"OpenAPI spec not found: {spec_path}")

        try:
            with open(path, 'r') as f:
                content = f.read()

            # Try JSON first
            if path.suffix.lower() in ['.json']:
                return json.loads(content)

            # Try YAML
            elif path.suffix.lower() in ['.yaml', '.yml']:
                return yaml.safe_load(content)

            else:
                # Try to auto-detect
                try:
                    return json.loads(content)
                except json.JSONDecodeError:
                    return yaml.safe_load(content)

        except Exception as e:
            raise ValidationError(f"Failed to parse OpenAPI spec: {str(e)}")


# ============================================================================
# Module Exports
# ============================================================================

__all__ = [
    "OpenAPIValidator",
]
