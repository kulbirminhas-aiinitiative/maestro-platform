#!/usr/bin/env python3
"""
Comprehensive Test Suite Executor - Phase 2

Executes all 20 test cases and collects comprehensive statistics:
- Pass/fail rates by category
- Execution times
- Policy validation results
- Coverage metrics
- Detailed failure analysis

Generates JSON report for Phase 3 AI agent review.
"""

import asyncio
import sys
import logging
import json
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime
import time

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from test_suite_generator import TestSuiteGenerator, TestCase, TestResult
from dag_executor import DAGExecutor, WorkflowContextStore, ExecutionEvent
from dag_workflow import NodeStatus

logger = logging.getLogger(__name__)


# =============================================================================
# TEST EXECUTOR
# =============================================================================

class TestSuiteExecutor:
    """Executes comprehensive test suite and collects statistics"""

    def __init__(self):
        self.test_results: List[TestResult] = []
        self.start_time: datetime = None
        self.end_time: datetime = None

    async def execute_test_case(self, test_case: TestCase) -> TestResult:
        """Execute a single test case and collect results"""
        logger.info(f"\n{'='*80}")
        logger.info(f"EXECUTING: {test_case.test_id} - {test_case.name}")
        logger.info(f"{'='*80}")
        logger.info(f"Category: {test_case.category} | Complexity: {test_case.complexity_score}/10")
        logger.info(f"Description: {test_case.description}")
        logger.info(f"Expected: {test_case.expected_outcome}")

        start_time = time.time()
        nodes_executed = 0
        nodes_passed = 0
        nodes_failed = 0
        validation_results = {}
        error_message = ""
        passed = False

        try:
            # Create context store and executor
            context_store = WorkflowContextStore()

            # Event handler to track execution
            events = []
            async def event_handler(event: ExecutionEvent):
                events.append(event)

            executor = DAGExecutor(
                workflow=test_case.workflow,
                context_store=context_store,
                event_handler=event_handler,
                enable_contract_validation=True
            )

            # Execute workflow
            try:
                context = await executor.execute()

                # Count nodes
                for node_id, state in context.node_states.items():
                    nodes_executed += 1
                    if state.status == NodeStatus.COMPLETED:
                        nodes_passed += 1
                    elif state.status == NodeStatus.FAILED:
                        nodes_failed += 1

                    # Collect validation results
                    if state.output and 'validation_results' in state.output:
                        validation_results[node_id] = state.output['validation_results']

                # Determine if test passed based on expected outcome
                if test_case.expected_outcome == "pass":
                    # All nodes should succeed
                    passed = (nodes_failed == 0)
                    if not passed:
                        error_message = f"Expected pass but {nodes_failed} node(s) failed"
                elif test_case.expected_outcome == "fail":
                    # Expected nodes should fail
                    failed_nodes = [nid for nid, s in context.node_states.items()
                                  if s.status == NodeStatus.FAILED]
                    expected_failures_set = set(test_case.expected_failures)
                    actual_failures_set = set(failed_nodes)

                    passed = (expected_failures_set == actual_failures_set)
                    if not passed:
                        error_message = f"Expected failures: {expected_failures_set}, Got: {actual_failures_set}"
                else:
                    passed = True  # Partial or other outcomes

                if passed:
                    logger.info(f"✅ TEST PASSED: {test_case.test_id}")
                else:
                    logger.error(f"❌ TEST FAILED: {test_case.test_id} - {error_message}")

            except Exception as e:
                # Workflow failed with exception
                if test_case.expected_outcome == "fail":
                    # This might be expected
                    executions = await context_store.list_executions(test_case.workflow.workflow_id)
                    if executions:
                        context = await context_store.load_context(executions[-1])
                        failed_nodes = [nid for nid, s in context.node_states.items()
                                      if s.status == NodeStatus.FAILED]

                        expected_failures_set = set(test_case.expected_failures)
                        actual_failures_set = set(failed_nodes)

                        passed = (expected_failures_set.issubset(actual_failures_set))
                        if passed:
                            logger.info(f"✅ TEST PASSED: {test_case.test_id} (expected failure)")
                        else:
                            error_message = f"Expected failures: {expected_failures_set}, Got: {actual_failures_set}"
                            logger.error(f"❌ TEST FAILED: {test_case.test_id} - {error_message}")

                        # Still count nodes
                        for node_id, state in context.node_states.items():
                            nodes_executed += 1
                            if state.status == NodeStatus.COMPLETED:
                                nodes_passed += 1
                            elif state.status == NodeStatus.FAILED:
                                nodes_failed += 1

                            if state.output and 'validation_results' in state.output:
                                validation_results[node_id] = state.output['validation_results']
                    else:
                        passed = False
                        error_message = str(e)
                        logger.error(f"❌ TEST FAILED: {test_case.test_id} - {error_message}")
                else:
                    # Unexpected failure
                    passed = False
                    error_message = str(e)
                    logger.error(f"❌ TEST FAILED: {test_case.test_id} - Unexpected exception: {error_message}")

        except Exception as e:
            passed = False
            error_message = f"Test execution error: {str(e)}"
            logger.error(f"❌ TEST FAILED: {test_case.test_id} - {error_message}", exc_info=True)

        execution_time = time.time() - start_time

        result = TestResult(
            test_id=test_case.test_id,
            passed=passed,
            execution_time_seconds=execution_time,
            nodes_executed=nodes_executed,
            nodes_passed=nodes_passed,
            nodes_failed=nodes_failed,
            validation_results=validation_results,
            error_message=error_message
        )

        logger.info(f"Execution time: {execution_time:.2f}s")
        logger.info(f"Nodes: {nodes_executed} total, {nodes_passed} passed, {nodes_failed} failed")

        return result

    async def execute_all_tests(self, test_cases: List[TestCase]) -> None:
        """Execute all test cases"""
        self.start_time = datetime.now()
        logger.info("\n" + "="*80)
        logger.info("COMPREHENSIVE TEST SUITE EXECUTION")
        logger.info("="*80)
        logger.info(f"Total tests: {len(test_cases)}")
        logger.info(f"Start time: {self.start_time.isoformat()}")
        logger.info("="*80)

        for i, test_case in enumerate(test_cases, 1):
            logger.info(f"\n[{i}/{len(test_cases)}] Starting test: {test_case.test_id}")
            result = await self.execute_test_case(test_case)
            self.test_results.append(result)

            # Brief pause between tests
            await asyncio.sleep(0.5)

        self.end_time = datetime.now()

    def generate_statistics(self, test_cases: List[TestCase]) -> Dict[str, Any]:
        """Generate comprehensive statistics from test results"""
        total_tests = len(self.test_results)
        passed_tests = sum(1 for r in self.test_results if r.passed)
        failed_tests = total_tests - passed_tests

        # By category
        category_stats = {}
        for test_case in test_cases:
            category = test_case.category
            if category not in category_stats:
                category_stats[category] = {"total": 0, "passed": 0, "failed": 0}

            category_stats[category]["total"] += 1

        for result in self.test_results:
            test_case = next((t for t in test_cases if t.test_id == result.test_id), None)
            if test_case:
                category = test_case.category
                if result.passed:
                    category_stats[category]["passed"] += 1
                else:
                    category_stats[category]["failed"] += 1

        # Execution times
        total_execution_time = sum(r.execution_time_seconds for r in self.test_results)
        avg_execution_time = total_execution_time / total_tests if total_tests > 0 else 0
        slowest_test = max(self.test_results, key=lambda r: r.execution_time_seconds) if self.test_results else None
        fastest_test = min(self.test_results, key=lambda r: r.execution_time_seconds) if self.test_results else None

        # Node statistics
        total_nodes_executed = sum(r.nodes_executed for r in self.test_results)
        total_nodes_passed = sum(r.nodes_passed for r in self.test_results)
        total_nodes_failed = sum(r.nodes_failed for r in self.test_results)

        # Validation statistics
        total_validations = sum(len(r.validation_results) for r in self.test_results)

        # Complexity coverage
        complexity_scores = [t.complexity_score for t in test_cases]
        avg_complexity = sum(complexity_scores) / len(complexity_scores) if complexity_scores else 0

        # Feature validation coverage
        all_features_validated = set()
        for test_case in test_cases:
            all_features_validated.update(test_case.validates)

        stats = {
            "summary": {
                "total_tests": total_tests,
                "passed": passed_tests,
                "failed": failed_tests,
                "pass_rate": (passed_tests / total_tests * 100) if total_tests > 0 else 0
            },
            "by_category": category_stats,
            "execution_time": {
                "total_seconds": total_execution_time,
                "average_seconds": avg_execution_time,
                "slowest_test": {
                    "test_id": slowest_test.test_id if slowest_test else None,
                    "time_seconds": slowest_test.execution_time_seconds if slowest_test else 0
                },
                "fastest_test": {
                    "test_id": fastest_test.test_id if fastest_test else None,
                    "time_seconds": fastest_test.execution_time_seconds if fastest_test else 0
                }
            },
            "nodes": {
                "total_executed": total_nodes_executed,
                "total_passed": total_nodes_passed,
                "total_failed": total_nodes_failed,
                "pass_rate": (total_nodes_passed / total_nodes_executed * 100) if total_nodes_executed > 0 else 0
            },
            "validation": {
                "total_validations": total_validations,
                "validations_per_test": total_validations / total_tests if total_tests > 0 else 0
            },
            "coverage": {
                "complexity_range": {
                    "min": min(complexity_scores) if complexity_scores else 0,
                    "max": max(complexity_scores) if complexity_scores else 0,
                    "average": avg_complexity
                },
                "features_validated": sorted(list(all_features_validated)),
                "feature_count": len(all_features_validated)
            },
            "timeline": {
                "start_time": self.start_time.isoformat(),
                "end_time": self.end_time.isoformat(),
                "duration_seconds": (self.end_time - self.start_time).total_seconds()
            }
        }

        return stats

    def print_summary(self, test_cases: List[TestCase], stats: Dict[str, Any]) -> None:
        """Print comprehensive summary"""
        print("\n" + "="*80)
        print("COMPREHENSIVE TEST SUITE - FINAL SUMMARY")
        print("="*80)

        # Overall results
        print("\n📊 OVERALL RESULTS")
        print("-" * 80)
        summary = stats["summary"]
        print(f"Total Tests:     {summary['total_tests']}")
        print(f"Passed:          {summary['passed']} ({summary['pass_rate']:.1f}%)")
        print(f"Failed:          {summary['failed']}")

        # By category
        print("\n📂 RESULTS BY CATEGORY")
        print("-" * 80)
        for category, cat_stats in sorted(stats["by_category"].items()):
            pass_rate = (cat_stats['passed'] / cat_stats['total'] * 100) if cat_stats['total'] > 0 else 0
            status = "✅" if pass_rate == 100 else "⚠️" if pass_rate >= 50 else "❌"
            print(f"{status} {category.capitalize():12} {cat_stats['passed']}/{cat_stats['total']} ({pass_rate:.0f}%)")

        # Execution performance
        print("\n⏱️  EXECUTION PERFORMANCE")
        print("-" * 80)
        exec_stats = stats["execution_time"]
        print(f"Total Time:      {exec_stats['total_seconds']:.2f}s")
        print(f"Average/Test:    {exec_stats['average_seconds']:.2f}s")
        print(f"Slowest Test:    {exec_stats['slowest_test']['test_id']} ({exec_stats['slowest_test']['time_seconds']:.2f}s)")
        print(f"Fastest Test:    {exec_stats['fastest_test']['test_id']} ({exec_stats['fastest_test']['time_seconds']:.2f}s)")

        # Node statistics
        print("\n🔷 NODE STATISTICS")
        print("-" * 80)
        node_stats = stats["nodes"]
        print(f"Total Nodes:     {node_stats['total_executed']}")
        print(f"Passed:          {node_stats['total_passed']} ({node_stats['pass_rate']:.1f}%)")
        print(f"Failed:          {node_stats['total_failed']}")

        # Coverage
        print("\n🎯 COVERAGE METRICS")
        print("-" * 80)
        coverage = stats["coverage"]
        print(f"Complexity Range: {coverage['complexity_range']['min']}-{coverage['complexity_range']['max']} (avg: {coverage['complexity_range']['average']:.1f})")
        print(f"Features Tested:  {coverage['feature_count']} features")

        # Failed tests detail
        failed_results = [r for r in self.test_results if not r.passed]
        if failed_results:
            print("\n❌ FAILED TESTS DETAIL")
            print("-" * 80)
            for result in failed_results:
                test_case = next((t for t in test_cases if t.test_id == result.test_id), None)
                print(f"\n{result.test_id}: {test_case.name if test_case else 'Unknown'}")
                print(f"  Error: {result.error_message}")
                print(f"  Nodes: {result.nodes_executed} executed, {result.nodes_passed} passed, {result.nodes_failed} failed")

        # Success message
        print("\n" + "="*80)
        if summary['pass_rate'] == 100:
            print("🎉 ALL TESTS PASSED!")
            print("   Phase 0 integration is PRODUCTION READY")
        elif summary['pass_rate'] >= 80:
            print(f"✅ MOSTLY PASSING ({summary['pass_rate']:.0f}%)")
            print("   Phase 0 integration is functional with minor issues")
        else:
            print(f"⚠️  NEEDS ATTENTION ({summary['pass_rate']:.0f}% pass rate)")
            print("   Phase 0 integration requires fixes")
        print("="*80)

    def save_report(self, test_cases: List[TestCase], stats: Dict[str, Any], output_file: str) -> None:
        """Save comprehensive report as JSON"""
        # Build detailed test results
        detailed_results = []
        for result in self.test_results:
            test_case = next((t for t in test_cases if t.test_id == result.test_id), None)
            detailed_results.append({
                "test_id": result.test_id,
                "name": test_case.name if test_case else "Unknown",
                "category": test_case.category if test_case else "unknown",
                "complexity_score": test_case.complexity_score if test_case else 0,
                "passed": result.passed,
                "execution_time_seconds": result.execution_time_seconds,
                "nodes_executed": result.nodes_executed,
                "nodes_passed": result.nodes_passed,
                "nodes_failed": result.nodes_failed,
                "error_message": result.error_message,
                "validation_results": result.validation_results,
                "validates": test_case.validates if test_case else []
            })

        report = {
            "report_metadata": {
                "generated_at": datetime.now().isoformat(),
                "phase": "Phase 2: Comprehensive Validation",
                "version": "1.0.0"
            },
            "statistics": stats,
            "detailed_results": detailed_results
        }

        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'w') as f:
            json.dump(report, f, indent=2)

        logger.info(f"\n📄 Report saved to: {output_path}")


# =============================================================================
# MAIN EXECUTION
# =============================================================================

async def main():
    """Main execution function"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(name)s - %(message)s'
    )

    # Generate test suite
    generator = TestSuiteGenerator()
    test_cases = generator.generate_all_tests()

    # Execute test suite
    executor = TestSuiteExecutor()
    await executor.execute_all_tests(test_cases)

    # Generate statistics
    stats = executor.generate_statistics(test_cases)

    # Print summary
    executor.print_summary(test_cases, stats)

    # Save report
    executor.save_report(test_cases, stats, "reports/comprehensive_test_report.json")

    # Return exit code
    return 0 if stats["summary"]["pass_rate"] == 100 else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
