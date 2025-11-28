"""
Quality Fabric Test Generation Helper
Leverages /api/ai/generate-tests endpoint for base test coverage

This module provides automated test generation using Quality Fabric's AI capabilities.
It supports generating unit tests, integration tests, and comprehensive test suites
for the DDF Tri-Modal System.
"""

import httpx
import asyncio
from pathlib import Path
from typing import List, Dict, Any, Optional
import logging
import json

logger = logging.getLogger(__name__)


class QualityFabricTestGenerator:
    """
    Generate tests using Quality Fabric AI-powered test generation API

    This class interfaces with Quality Fabric's /api/ai/generate-tests endpoint
    to automatically generate comprehensive test suites with high coverage.

    Attributes:
        base_url: Quality Fabric API base URL
        api_key: Optional API key for authentication
        timeout: Request timeout in seconds
    """

    def __init__(
        self,
        base_url: str = "http://localhost:8000",
        api_key: Optional[str] = None,
        timeout: float = 60.0
    ):
        """
        Initialize Quality Fabric test generator

        Args:
            base_url: Quality Fabric API URL (default: http://localhost:8000)
            api_key: Optional API key for authentication
            timeout: Request timeout in seconds (default: 60.0)
        """
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.timeout = timeout
        logger.info(f"Initialized QualityFabricTestGenerator with base_url={base_url}")

    async def generate_tests_for_module(
        self,
        source_file: str,
        test_framework: str = "pytest",
        coverage_target: float = 0.90,
        output_dir: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate tests for a single module

        This method calls Quality Fabric's AI test generation endpoint to create
        comprehensive unit tests for a given source file.

        Args:
            source_file: Path to source file to generate tests for
            test_framework: Test framework (pytest, unittest, etc.)
            coverage_target: Target code coverage (0.0-1.0)
            output_dir: Optional output directory for generated tests

        Returns:
            Test generation response containing:
            - test_files: List of generated test files with content
            - summary: Generation summary with test count and coverage

        Example:
            >>> generator = QualityFabricTestGenerator()
            >>> result = await generator.generate_tests_for_module(
            ...     "dde/artifact_stamper.py",
            ...     coverage_target=0.90
            ... )
            >>> print(f"Generated {result['summary']['tests_generated']} tests")
        """
        logger.info(f"Generating tests for {source_file} (target: {coverage_target:.0%})")

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            headers = {}
            if self.api_key:
                headers["X-API-Key"] = self.api_key

            try:
                response = await client.post(
                    f"{self.base_url}/api/ai/generate-tests",
                    json={
                        "source_files": [source_file],
                        "test_framework": test_framework,
                        "coverage_target": coverage_target
                    },
                    headers=headers
                )
                response.raise_for_status()

                result = response.json()
                logger.info(
                    f"Generated {result.get('summary', {}).get('tests_generated', 0)} tests "
                    f"with {result.get('summary', {}).get('estimated_coverage', 0):.1%} coverage"
                )

                # Write tests to files if output_dir specified
                if output_dir:
                    await self._write_test_files(result.get('test_files', []), output_dir)

                return result

            except httpx.HTTPError as e:
                logger.error(f"Failed to generate tests for {source_file}: {e}")
                raise
            except Exception as e:
                logger.error(f"Unexpected error generating tests: {e}")
                raise

    async def generate_tests_for_stream(
        self,
        stream: str,  # "dde", "bdv", "acc"
        source_dir: str,
        output_dir: str,
        coverage_target: float = 0.85
    ) -> List[Dict[str, Any]]:
        """
        Generate tests for entire stream (DDE, BDV, or ACC)

        This method discovers all Python files in a stream directory and generates
        comprehensive test suites for each module.

        Args:
            stream: Stream name ("dde", "bdv", or "acc")
            source_dir: Source directory containing stream modules
            output_dir: Output directory for generated tests
            coverage_target: Target coverage for all modules

        Returns:
            List of test generation responses for each module

        Example:
            >>> generator = QualityFabricTestGenerator()
            >>> results = await generator.generate_tests_for_stream(
            ...     stream="dde",
            ...     source_dir="dde/",
            ...     output_dir="tests/dde/unit/"
            ... )
            >>> print(f"Generated tests for {len(results)} modules")
        """
        logger.info(f"Generating tests for {stream.upper()} stream from {source_dir}")

        source_path = Path(source_dir)
        if not source_path.exists():
            raise FileNotFoundError(f"Source directory not found: {source_dir}")

        # Discover all Python files
        source_files = list(source_path.rglob("*.py"))
        # Exclude __init__.py and test files
        source_files = [
            f for f in source_files
            if f.name != "__init__.py" and not f.name.startswith("test_")
        ]

        logger.info(f"Found {len(source_files)} source files to test")

        results = []
        for source_file in source_files:
            try:
                result = await self.generate_tests_for_module(
                    str(source_file),
                    coverage_target=coverage_target,
                    output_dir=output_dir
                )
                results.append({
                    "source_file": str(source_file),
                    "result": result
                })
            except Exception as e:
                logger.error(f"Failed to generate tests for {source_file}: {e}")
                results.append({
                    "source_file": str(source_file),
                    "error": str(e)
                })

        logger.info(
            f"Completed test generation for {stream.upper()} stream: "
            f"{len([r for r in results if 'result' in r])}/{len(results)} successful"
        )
        return results

    async def generate_integration_tests(
        self,
        source_files: List[str],
        output_file: str,
        coverage_target: float = 0.80,
        test_context: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate integration tests for multiple modules

        This method generates integration tests that verify the interaction
        between multiple modules or components.

        Args:
            source_files: List of source file paths to test together
            output_file: Output file path for integration tests
            coverage_target: Target integration coverage
            test_context: Optional context about integration points

        Returns:
            Test generation response

        Example:
            >>> generator = QualityFabricTestGenerator()
            >>> result = await generator.generate_integration_tests(
            ...     source_files=[
            ...         "dde/task_router.py",
            ...         "dde/capability_matcher.py"
            ...     ],
            ...     output_file="tests/dde/integration/test_task_routing.py"
            ... )
        """
        logger.info(
            f"Generating integration tests for {len(source_files)} modules "
            f"(target: {coverage_target:.0%})"
        )

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            headers = {}
            if self.api_key:
                headers["X-API-Key"] = self.api_key

            payload = {
                "source_files": source_files,
                "test_framework": "pytest",
                "coverage_target": coverage_target
            }

            if test_context:
                payload["context"] = test_context

            try:
                response = await client.post(
                    f"{self.base_url}/api/ai/generate-tests",
                    json=payload,
                    headers=headers
                )
                response.raise_for_status()

                result = response.json()
                logger.info(
                    f"Generated integration tests: "
                    f"{result.get('summary', {}).get('tests_generated', 0)} tests"
                )

                # Write integration test file
                if result.get('test_files'):
                    test_content = result['test_files'][0].get('content', '')
                    Path(output_file).parent.mkdir(parents=True, exist_ok=True)
                    with open(output_file, 'w') as f:
                        f.write(test_content)
                    logger.info(f"Wrote integration tests to {output_file}")

                return result

            except httpx.HTTPError as e:
                logger.error(f"Failed to generate integration tests: {e}")
                raise
            except Exception as e:
                logger.error(f"Unexpected error: {e}")
                raise

    async def generate_e2e_tests(
        self,
        workflow_spec: Dict[str, Any],
        output_file: str
    ) -> Dict[str, Any]:
        """
        Generate end-to-end workflow tests

        This method generates comprehensive E2E tests that validate complete
        workflows through all three streams (DDE, BDV, ACC).

        Args:
            workflow_spec: Workflow specification including:
                - name: Workflow name
                - description: Workflow description
                - components: List of components involved
                - scenarios: Test scenarios to cover
            output_file: Output file for E2E tests

        Returns:
            Test generation response

        Example:
            >>> generator = QualityFabricTestGenerator()
            >>> result = await generator.generate_e2e_tests(
            ...     workflow_spec={
            ...         "name": "User Profile Update",
            ...         "components": ["DDE", "BDV", "ACC"],
            ...         "scenarios": ["success", "validation_failure", "rollback"]
            ...     },
            ...     output_file="tests/e2e/test_user_profile_workflow.py"
            ... )
        """
        logger.info(f"Generating E2E tests for workflow: {workflow_spec.get('name')}")

        # For E2E tests, we'll use a specialized prompt
        # This is a placeholder - actual implementation would call Quality Fabric
        # with workflow-specific context

        logger.warning("E2E test generation not yet fully implemented via Quality Fabric API")
        return {
            "message": "E2E test generation requires manual implementation",
            "workflow": workflow_spec,
            "output_file": output_file
        }

    async def _write_test_files(
        self,
        test_files: List[Dict[str, Any]],
        output_dir: str
    ) -> None:
        """
        Write generated test files to disk

        Args:
            test_files: List of test file specs with file_path and content
            output_dir: Base output directory
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        for test_file in test_files:
            file_path = test_file.get('file_path', '')
            content = test_file.get('content', '')

            if not file_path or not content:
                logger.warning("Skipping test file with missing path or content")
                continue

            # Extract filename and write to output directory
            filename = Path(file_path).name
            full_path = output_path / filename

            with open(full_path, 'w') as f:
                f.write(content)

            logger.info(f"Wrote test file: {full_path}")

    async def health_check(self) -> bool:
        """
        Check if Quality Fabric API is available

        Returns:
            True if API is healthy, False otherwise
        """
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.base_url}/health")
                return response.status_code == 200
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False


# ============================================================================
# Convenience Functions
# ============================================================================

async def generate_dde_tests(
    coverage_target: float = 0.90,
    output_base: str = "tests/dde"
) -> Dict[str, Any]:
    """
    Generate comprehensive tests for DDE stream

    Args:
        coverage_target: Target coverage (default: 90%)
        output_base: Base output directory

    Returns:
        Summary of test generation
    """
    generator = QualityFabricTestGenerator()

    # Check health
    if not await generator.health_check():
        logger.error("Quality Fabric API not available")
        return {"error": "Quality Fabric API not available"}

    # Generate unit tests
    unit_results = await generator.generate_tests_for_stream(
        stream="dde",
        source_dir="dde/",
        output_dir=f"{output_base}/unit/",
        coverage_target=coverage_target
    )

    # Generate integration tests for key component pairs
    integration_pairs = [
        (["dde/task_router.py", "dde/capability_matcher.py"], "test_task_routing_integration.py"),
        (["dde/artifact_stamper.py", "dde/contract_lockdown.py"], "test_artifact_contract_integration.py"),
        (["dde/gate_executor.py", "dde/event_log.py"], "test_gate_execution_integration.py"),
    ]

    integration_results = []
    for source_files, output_name in integration_pairs:
        try:
            result = await generator.generate_integration_tests(
                source_files=source_files,
                output_file=f"{output_base}/integration/{output_name}",
                coverage_target=0.85
            )
            integration_results.append(result)
        except Exception as e:
            logger.error(f"Failed to generate integration tests for {output_name}: {e}")

    return {
        "unit_tests": unit_results,
        "integration_tests": integration_results,
        "summary": {
            "unit_modules": len(unit_results),
            "integration_tests": len(integration_results)
        }
    }


async def generate_bdv_tests(
    coverage_target: float = 0.85,
    output_base: str = "tests/bdv"
) -> Dict[str, Any]:
    """
    Generate comprehensive tests for BDV stream

    Args:
        coverage_target: Target coverage (default: 85%)
        output_base: Base output directory

    Returns:
        Summary of test generation
    """
    generator = QualityFabricTestGenerator()

    # Check health
    if not await generator.health_check():
        logger.error("Quality Fabric API not available")
        return {"error": "Quality Fabric API not available"}

    # Generate unit tests
    unit_results = await generator.generate_tests_for_stream(
        stream="bdv",
        source_dir="bdv/",
        output_dir=f"{output_base}/unit/",
        coverage_target=coverage_target
    )

    return {
        "unit_tests": unit_results,
        "summary": {
            "unit_modules": len(unit_results)
        }
    }


async def generate_acc_tests(
    coverage_target: float = 0.90,
    output_base: str = "tests/acc"
) -> Dict[str, Any]:
    """
    Generate comprehensive tests for ACC stream

    Args:
        coverage_target: Target coverage (default: 90%)
        output_base: Base output directory

    Returns:
        Summary of test generation
    """
    generator = QualityFabricTestGenerator()

    # Check health
    if not await generator.health_check():
        logger.error("Quality Fabric API not available")
        return {"error": "Quality Fabric API not available"}

    # Generate unit tests
    unit_results = await generator.generate_tests_for_stream(
        stream="acc",
        source_dir="acc/",
        output_dir=f"{output_base}/unit/",
        coverage_target=coverage_target
    )

    return {
        "unit_tests": unit_results,
        "summary": {
            "unit_modules": len(unit_results)
        }
    }


# ============================================================================
# CLI Interface
# ============================================================================

async def main():
    """CLI interface for test generation"""
    import sys
    import argparse

    parser = argparse.ArgumentParser(description="Generate tests using Quality Fabric")
    parser.add_argument("stream", choices=["dde", "bdv", "acc", "all"], help="Stream to generate tests for")
    parser.add_argument("--coverage", type=float, default=0.85, help="Target coverage (0.0-1.0)")
    parser.add_argument("--output", default="tests/", help="Output base directory")

    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)

    if args.stream == "dde":
        result = await generate_dde_tests(args.coverage, f"{args.output}/dde")
    elif args.stream == "bdv":
        result = await generate_bdv_tests(args.coverage, f"{args.output}/bdv")
    elif args.stream == "acc":
        result = await generate_acc_tests(args.coverage, f"{args.output}/acc")
    elif args.stream == "all":
        dde_result = await generate_dde_tests(args.coverage, f"{args.output}/dde")
        bdv_result = await generate_bdv_tests(args.coverage, f"{args.output}/bdv")
        acc_result = await generate_acc_tests(args.coverage, f"{args.output}/acc")
        result = {
            "dde": dde_result,
            "bdv": bdv_result,
            "acc": acc_result
        }

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
