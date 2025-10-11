#!/usr/bin/env python3
"""
Test Runner - Automated Test Execution and Reporting

Orchestrates test suite execution and generates comprehensive test reports:
- Run all tests or specific test suite
- Collect and aggregate results
- Generate markdown test report
- Cleanup test artifacts
- Performance analysis
"""

import asyncio
import sys
import logging
import json
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime

# Add paths
sys.path.insert(0, str(Path(__file__).parent))

# Import test components
from team_execution_tests import TeamExecutionSplitModeTests, TestResult
from test_requirements import get_requirement_summary

logger = logging.getLogger(__name__)


# =============================================================================
# TEST RUNNER
# =============================================================================

class TestRunner:
    """
    Automated test runner.

    Features:
    - Run all tests or specific suite
    - Collect results
    - Generate reports (markdown, JSON)
    - Cleanup artifacts
    - Performance analysis
    """

    def __init__(
        self,
        output_dir: str = "./test_output",
        report_dir: str = "./test_reports"
    ):
        self.output_dir = Path(output_dir)
        self.report_dir = Path(report_dir)

        # Create directories
        self.report_dir.mkdir(parents=True, exist_ok=True)

        # Test suite
        self.test_suite = TeamExecutionSplitModeTests(
            output_dir=str(self.output_dir),
            checkpoint_dir=str(self.output_dir / "checkpoints")
        )

        # Results
        self.results: List[TestResult] = []
        self.start_time = None
        self.end_time = None

    async def run_all_tests(self) -> List[TestResult]:
        """Run all tests in the suite"""
        logger.info("\n" + "="*80)
        logger.info("TEST RUNNER: Starting All Tests")
        logger.info("="*80 + "\n")

        self.start_time = datetime.now()

        # Run tests
        self.results = await self.test_suite.run_all_tests()

        self.end_time = datetime.now()

        return self.results

    async def run_specific_tests(self, test_ids: List[str]) -> List[TestResult]:
        """Run specific tests by ID"""
        logger.info(f"\n Running specific tests: {', '.join(test_ids)}\n")

        self.start_time = datetime.now()

        test_map = {
            "TC1": self.test_suite.test_01_single_phase_execution,
            "TC2": self.test_suite.test_02_sequential_phase_execution,
            "TC3": self.test_suite.test_03_full_batch_execution,
            "TC4": self.test_suite.test_04_resume_from_checkpoint,
            "TC5": self.test_suite.test_05_phase_skipping,
            "TC6": self.test_suite.test_06_human_edits,
            "TC7": self.test_suite.test_07_quality_gate_failure,
            "TC8": self.test_suite.test_08_contract_validation_failure,
            "TC9": self.test_suite.test_09_multiple_checkpoints,
            "TC10": self.test_suite.test_10_concurrent_execution
        }

        results = []
        for test_id in test_ids:
            if test_id in test_map:
                result = await test_map[test_id]()
                results.append(result)
                self.results.append(result)

        self.end_time = datetime.now()

        return results

    def generate_test_report(self, output_file: str = "TEST_REPORT.md"):
        """Generate comprehensive test report in Markdown"""
        report_path = self.report_dir / output_file

        with open(report_path, 'w') as f:
            # Header
            f.write("# Team Execution V2 Split Mode - Test Report\n\n")
            f.write(f"**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

            # Summary
            f.write("## Test Summary\n\n")

            total = len(self.results)
            passed = sum(1 for r in self.results if r.passed)
            failed = sum(1 for r in self.results if not r.passed)
            total_duration = sum(r.duration_seconds for r in self.results)

            f.write(f"- **Total Tests**: {total}\n")
            f.write(f"- **Passed**: {passed} ✅\n")
            f.write(f"- **Failed**: {failed} {'❌' if failed > 0 else ''}\n")
            f.write(f"- **Total Duration**: {total_duration:.1f}s ({total_duration/60:.1f}m)\n")
            f.write(f"- **Success Rate**: {(passed/total*100):.0f}%\n\n")

            if self.start_time and self.end_time:
                duration = (self.end_time - self.start_time).total_seconds()
                f.write(f"- **Wall Clock Time**: {duration:.1f}s ({duration/60:.1f}m)\n\n")

            # Results Table
            f.write("## Test Results\n\n")
            f.write("| Test ID | Test Name | Status | Duration | Error |\n")
            f.write("|---------|-----------|--------|----------|-------|\n")

            for result in self.results:
                status = "✅ PASS" if result.passed else "❌ FAIL"
                error = result.error_message[:50] + "..." if result.error_message else ""
                f.write(f"| {result.test_id} | {result.test_name} | {status} | {result.duration_seconds:.1f}s | {error} |\n")

            f.write("\n")

            # Detailed Results
            f.write("## Detailed Results\n\n")

            for result in self.results:
                f.write(f"### {result.test_id}: {result.test_name}\n\n")
                f.write(f"- **Status**: {'✅ PASSED' if result.passed else '❌ FAILED'}\n")
                f.write(f"- **Duration**: {result.duration_seconds:.2f}s\n")

                if result.checkpoints_created:
                    f.write(f"- **Checkpoints Created**: {len(result.checkpoints_created)}\n")

                if result.context:
                    summary = result.context.get_summary()
                    f.write(f"- **Phases Completed**: {summary['completed_phases']}/{summary['total_phases']}\n")
                    f.write(f"- **Overall Quality**: {summary['overall_quality']:.0%}\n")

                if result.error_message:
                    f.write(f"\n**Error**:\n```\n{result.error_message}\n```\n")

                f.write("\n")

            # Performance Analysis
            f.write("## Performance Analysis\n\n")

            if self.results:
                avg_duration = sum(r.duration_seconds for r in self.results) / len(self.results)
                max_duration = max(r.duration_seconds for r in self.results)
                min_duration = min(r.duration_seconds for r in self.results)

                f.write(f"- **Average Test Duration**: {avg_duration:.1f}s\n")
                f.write(f"- **Max Test Duration**: {max_duration:.1f}s\n")
                f.write(f"- **Min Test Duration**: {min_duration:.1f}s\n\n")

            # Checkpoint Analysis
            f.write("## Checkpoint Analysis\n\n")

            total_checkpoints = sum(len(r.checkpoints_created) for r in self.results)
            f.write(f"- **Total Checkpoints Created**: {total_checkpoints}\n\n")

            # Context Flow Validation
            f.write("## Context Flow Validation\n\n")

            for result in self.results:
                if result.context and len(result.context.workflow.phase_results) > 1:
                    f.write(f"### {result.test_id}\n\n")
                    phases = result.context.workflow.phase_order
                    f.write(f"Phase Flow: {' → '.join(phases)}\n\n")

            # Test Requirements Used
            f.write("## Test Requirements\n\n")
            f.write(get_requirement_summary())

            # Conclusion
            f.write("\n## Conclusion\n\n")

            if failed == 0:
                f.write("✅ **All tests passed successfully!**\n\n")
                f.write("The split mode implementation is working correctly with:\n")
                f.write("- Independent phase execution\n")
                f.write("- Checkpoint save/load\n")
                f.write("- Phase skipping\n")
                f.write("- Human edits\n")
                f.write("- Context persistence\n\n")
            else:
                f.write(f"❌ **{failed} test(s) failed.**\n\n")
                f.write("Please review the detailed results above for error messages.\n\n")

            f.write(f"**Report Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

        logger.info(f"✅ Test report generated: {report_path}")
        return str(report_path)

    def generate_json_report(self, output_file: str = "test_results.json"):
        """Generate JSON test results"""
        report_path = self.report_dir / output_file

        results_data = {
            "generated_at": datetime.now().isoformat(),
            "summary": {
                "total": len(self.results),
                "passed": sum(1 for r in self.results if r.passed),
                "failed": sum(1 for r in self.results if not r.passed),
                "total_duration": sum(r.duration_seconds for r in self.results)
            },
            "results": [
                {
                    "test_id": r.test_id,
                    "test_name": r.test_name,
                    "passed": r.passed,
                    "duration_seconds": r.duration_seconds,
                    "error_message": r.error_message,
                    "checkpoints_created": r.checkpoints_created,
                    "context_summary": r.context.get_summary() if r.context else None
                }
                for r in self.results
            ]
        }

        with open(report_path, 'w') as f:
            json.dump(results_data, f, indent=2)

        logger.info(f"✅ JSON report generated: {report_path}")
        return str(report_path)

    def cleanup(self):
        """Clean up test artifacts"""
        self.test_suite.cleanup()
        logger.info("✅ Test artifacts cleaned up")

    def print_summary(self):
        """Print summary to console"""
        print("\n" + "="*80)
        print("TEST EXECUTION SUMMARY")
        print("="*80)

        total = len(self.results)
        passed = sum(1 for r in self.results if r.passed)
        failed = sum(1 for r in self.results if not r.passed)

        print(f"\nTotal Tests: {total}")
        print(f"Passed: {passed} ✅")
        print(f"Failed: {failed} {'❌' if failed > 0 else ''}")
        print(f"Success Rate: {(passed/total*100):.0f}%")

        total_duration = sum(r.duration_seconds for r in self.results)
        print(f"\nTotal Duration: {total_duration:.1f}s ({total_duration/60:.1f}m)")

        if self.start_time and self.end_time:
            wall_time = (self.end_time - self.start_time).total_seconds()
            print(f"Wall Clock Time: {wall_time:.1f}s ({wall_time/60:.1f}m)")

        print("\nPer-Test Results:")
        print("-" * 80)

        for result in self.results:
            status = "✅ PASS" if result.passed else "❌ FAIL"
            print(f"{result.test_id}: {status} ({result.duration_seconds:.1f}s)")
            if not result.passed:
                print(f"     Error: {result.error_message[:100]}")

        print("\n" + "="*80 + "\n")


# =============================================================================
# CLI AND MAIN
# =============================================================================

async def main():
    """CLI entry point"""
    import argparse

    parser = argparse.ArgumentParser(
        description="Team Execution V2 - Test Runner"
    )

    parser.add_argument(
        "--tests",
        nargs="+",
        help="Specific test IDs to run (e.g., TC1 TC2 TC3)"
    )

    parser.add_argument(
        "--report-format",
        choices=["markdown", "json", "both"],
        default="both",
        help="Report format"
    )

    parser.add_argument(
        "--no-cleanup",
        action="store_true",
        help="Don't cleanup test artifacts"
    )

    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Verbose logging"
    )

    args = parser.parse_args()

    # Configure logging
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s"
    )

    # Create runner
    runner = TestRunner()

    # Run tests
    if args.tests:
        await runner.run_specific_tests(args.tests)
    else:
        await runner.run_all_tests()

    # Print summary
    runner.print_summary()

    # Generate reports
    if args.report_format in ["markdown", "both"]:
        runner.generate_test_report()

    if args.report_format in ["json", "both"]:
        runner.generate_json_report()

    # Cleanup
    if not args.no_cleanup:
        runner.cleanup()

    # Exit with appropriate code
    failed = sum(1 for r in runner.results if not r.passed)
    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    asyncio.run(main())
