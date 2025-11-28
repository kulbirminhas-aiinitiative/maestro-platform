#!/usr/bin/env python3
"""
Comprehensive Validation and Recovery Test for All 22 Workflows

This script:
1. Validates all 22 workflows using the complete validation system
2. Generates gap reports and recovery contexts for each
3. Produces a summary report with statistics
4. Saves individual recovery plans for each workflow
5. Identifies common issues across workflows
"""

import asyncio
import json
import logging
from pathlib import Path
from typing import Dict, List, Any
from datetime import datetime
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from workflow_validation import WorkflowValidator, ValidationSeverity
from workflow_gap_detector import WorkflowGapDetector, BatchGapDetector
from implementation_completeness_checker import ImplementationCompletenessChecker
from deployment_readiness_validator import DeploymentReadinessValidator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class WorkflowValidationSummary:
    """Summary of validation results for a single workflow"""
    def __init__(self, workflow_id: str, workflow_dir: Path):
        self.workflow_id = workflow_id
        self.workflow_dir = workflow_dir
        self.phase_reports = {}
        self.gap_report = None
        self.completeness_progress = None
        self.deployment_readiness = None
        self.recovery_context = None
        self.validation_time = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            'workflow_id': self.workflow_id,
            'workflow_dir': str(self.workflow_dir),
            'validation_time': self.validation_time,
            'phase_validation': {
                phase: {
                    'status': report.overall_status,
                    'checks_passed': report.checks_passed,
                    'checks_failed': report.checks_failed,
                    'critical_failures': report.critical_failures
                }
                for phase, report in self.phase_reports.items()
            } if self.phase_reports else {},
            'gaps': {
                'total_gaps': self.gap_report.total_gaps if self.gap_report else 0,
                'critical_gaps': self.gap_report.critical_gaps if self.gap_report else 0,
                'estimated_completion': self.gap_report.estimated_completion_percentage if self.gap_report else 0,
                'is_deployable': self.gap_report.is_deployable if self.gap_report else False,
                'recovery_priority': self.gap_report.recovery_priority if self.gap_report else 0
            } if self.gap_report else {},
            'completeness': {
                'overall_completion': self.completeness_progress.overall_completion if self.completeness_progress else 0,
                'backend_complete': self.completeness_progress.backend_complete if self.completeness_progress else False,
                'frontend_complete': self.completeness_progress.frontend_complete if self.completeness_progress else False,
                'is_deployable': self.completeness_progress.is_deployable if self.completeness_progress else False,
                'blockers': self.completeness_progress.blockers if self.completeness_progress else []
            } if self.completeness_progress else {},
            'deployment_readiness': {
                'is_deployable': self.deployment_readiness.is_deployable if self.deployment_readiness else False,
                'checks_passed': self.deployment_readiness.checks_passed if self.deployment_readiness else 0,
                'checks_failed': self.deployment_readiness.checks_failed if self.deployment_readiness else 0,
                'critical_failures': self.deployment_readiness.critical_failures if self.deployment_readiness else 0
            } if self.deployment_readiness else {},
            'has_recovery_context': self.recovery_context is not None
        }


async def validate_single_workflow(workflow_dir: Path) -> WorkflowValidationSummary:
    """
    Run complete validation on a single workflow

    Returns:
        WorkflowValidationSummary with all validation results
    """
    workflow_id = workflow_dir.name
    logger.info(f"\n{'='*80}")
    logger.info(f"Validating workflow: {workflow_id}")
    logger.info(f"{'='*80}")

    start_time = datetime.now()
    summary = WorkflowValidationSummary(workflow_id, workflow_dir)

    try:
        # 1. Phase Validation
        logger.info("Running phase validation...")
        validator = WorkflowValidator(workflow_dir)
        summary.phase_reports = validator.validate_all()

        phase_summary = []
        for phase, report in summary.phase_reports.items():
            status_icon = "✓" if report.overall_status == "passed" else ("⚠" if report.overall_status == "warning" else "✗")
            phase_summary.append(
                f"{status_icon} {phase}: {report.overall_status} "
                f"({report.checks_passed}✓/{report.checks_failed}✗)"
            )
        logger.info("  " + ", ".join(phase_summary))

        # 2. Gap Detection
        logger.info("Running gap detection...")
        detector = WorkflowGapDetector(workflow_dir)
        summary.gap_report = detector.detect_gaps()
        logger.info(f"  Total gaps: {summary.gap_report.total_gaps} "
                   f"(Critical: {summary.gap_report.critical_gaps})")
        logger.info(f"  Estimated completion: {summary.gap_report.estimated_completion_percentage*100:.1f}%")
        logger.info(f"  Deployable: {summary.gap_report.is_deployable}")

        # 3. Implementation Completeness
        logger.info("Checking implementation completeness...")
        checker = ImplementationCompletenessChecker(workflow_dir)
        summary.completeness_progress = checker.check_implementation_progress()
        logger.info(f"  Overall completion: {summary.completeness_progress.overall_completion*100:.1f}%")
        logger.info(f"  Backend complete: {summary.completeness_progress.backend_complete}")
        logger.info(f"  Frontend complete: {summary.completeness_progress.frontend_complete}")
        if summary.completeness_progress.blockers:
            logger.info(f"  Blockers: {len(summary.completeness_progress.blockers)}")

        # 4. Deployment Readiness
        logger.info("Checking deployment readiness...")
        deployment_validator = DeploymentReadinessValidator(workflow_dir, run_service_tests=False)
        summary.deployment_readiness = await deployment_validator.validate()
        logger.info(f"  Deployable: {summary.deployment_readiness.is_deployable}")
        logger.info(f"  Checks: {summary.deployment_readiness.checks_passed}✓/{summary.deployment_readiness.checks_failed}✗")
        logger.info(f"  Critical failures: {summary.deployment_readiness.critical_failures}")

        # 5. Generate Recovery Context if needed
        if not summary.gap_report.is_deployable or not summary.deployment_readiness.is_deployable:
            logger.info("Generating recovery context...")
            summary.recovery_context = detector.generate_recovery_context(summary.gap_report)
            logger.info(f"  Recovery instructions: {len(summary.recovery_context.get('recovery_instructions', []))}")
        else:
            logger.info("✓ Workflow is deployable - no recovery needed!")

        # Calculate validation time
        summary.validation_time = (datetime.now() - start_time).total_seconds()
        logger.info(f"Validation completed in {summary.validation_time:.2f}s")

    except Exception as e:
        logger.error(f"✗ Validation failed for {workflow_id}: {e}", exc_info=True)

    return summary


async def validate_all_workflows(workflows_dir: Path, output_dir: Path):
    """
    Validate all workflows and generate comprehensive report

    Args:
        workflows_dir: Directory containing all workflow subdirectories
        output_dir: Directory to save validation results and recovery contexts
    """
    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)
    recovery_dir = output_dir / "recovery_contexts"
    recovery_dir.mkdir(exist_ok=True)
    reports_dir = output_dir / "validation_reports"
    reports_dir.mkdir(exist_ok=True)

    # Find all workflow directories
    workflow_dirs = sorted([d for d in workflows_dir.iterdir() if d.is_dir() and d.name.startswith('wf-')])

    logger.info("="*80)
    logger.info(f"COMPREHENSIVE WORKFLOW VALIDATION")
    logger.info(f"Found {len(workflow_dirs)} workflows to validate")
    logger.info("="*80 + "\n")

    # Validate each workflow
    all_summaries = []
    for workflow_dir in workflow_dirs:
        summary = await validate_single_workflow(workflow_dir)
        all_summaries.append(summary)

        # Save individual workflow report
        workflow_report_file = reports_dir / f"{summary.workflow_id}_validation_report.json"
        with open(workflow_report_file, 'w') as f:
            json.dump(summary.to_dict(), f, indent=2)

        # Save recovery context if generated
        if summary.recovery_context:
            recovery_file = recovery_dir / f"{summary.workflow_id}_recovery_plan.json"
            with open(recovery_file, 'w') as f:
                json.dump(summary.recovery_context, f, indent=2)

    # Generate aggregate statistics
    logger.info("\n" + "="*80)
    logger.info("AGGREGATE STATISTICS")
    logger.info("="*80)

    stats = {
        'total_workflows': len(all_summaries),
        'validation_timestamp': datetime.now().isoformat(),
        'total_validation_time': sum(s.validation_time for s in all_summaries),
        'deployable_count': sum(1 for s in all_summaries if s.gap_report and s.gap_report.is_deployable),
        'needs_recovery_count': sum(1 for s in all_summaries if s.recovery_context is not None),
        'average_completion': sum(s.gap_report.estimated_completion_percentage for s in all_summaries if s.gap_report) / len(all_summaries) if all_summaries else 0,
        'total_gaps': sum(s.gap_report.total_gaps for s in all_summaries if s.gap_report),
        'total_critical_gaps': sum(s.gap_report.critical_gaps for s in all_summaries if s.gap_report),
        'workflows': []
    }

    logger.info(f"Total workflows: {stats['total_workflows']}")
    logger.info(f"Deployable: {stats['deployable_count']} ({stats['deployable_count']/stats['total_workflows']*100:.1f}%)")
    logger.info(f"Need recovery: {stats['needs_recovery_count']} ({stats['needs_recovery_count']/stats['total_workflows']*100:.1f}%)")
    logger.info(f"Average completion: {stats['average_completion']*100:.1f}%")
    logger.info(f"Total gaps: {stats['total_gaps']} (Critical: {stats['total_critical_gaps']})")
    logger.info(f"Total validation time: {stats['total_validation_time']:.2f}s")

    # Breakdown by phase
    logger.info("\n" + "-"*80)
    logger.info("PHASE VALIDATION BREAKDOWN")
    logger.info("-"*80)

    phase_stats = {}
    for phase in ['requirements', 'design', 'implementation', 'testing', 'deployment']:
        passed = sum(1 for s in all_summaries if phase in s.phase_reports and s.phase_reports[phase].overall_status == 'passed')
        warning = sum(1 for s in all_summaries if phase in s.phase_reports and s.phase_reports[phase].overall_status == 'warning')
        failed = sum(1 for s in all_summaries if phase in s.phase_reports and s.phase_reports[phase].overall_status == 'failed')

        phase_stats[phase] = {
            'passed': passed,
            'warning': warning,
            'failed': failed,
            'pass_rate': passed / len(all_summaries) * 100 if all_summaries else 0
        }

        logger.info(f"{phase:20} - ✓{passed:2} ⚠{warning:2} ✗{failed:2} ({phase_stats[phase]['pass_rate']:.1f}% pass rate)")

    stats['phase_breakdown'] = phase_stats

    # Common issues
    logger.info("\n" + "-"*80)
    logger.info("COMMON ISSUES")
    logger.info("-"*80)

    issue_counts = {}
    for summary in all_summaries:
        if summary.gap_report:
            for phase, gaps in summary.gap_report.gaps_by_phase.items():
                for gap in gaps:
                    issue_key = f"{gap.phase}: {gap.description}"
                    issue_counts[issue_key] = issue_counts.get(issue_key, 0) + 1

    # Top 10 most common issues
    common_issues = sorted(issue_counts.items(), key=lambda x: x[1], reverse=True)[:10]
    for issue, count in common_issues:
        logger.info(f"  [{count:2}] {issue}")

    stats['common_issues'] = dict(common_issues)

    # Completeness breakdown
    logger.info("\n" + "-"*80)
    logger.info("IMPLEMENTATION COMPLETENESS")
    logger.info("-"*80)

    backend_complete = sum(1 for s in all_summaries if s.completeness_progress and s.completeness_progress.backend_complete)
    frontend_complete = sum(1 for s in all_summaries if s.completeness_progress and s.completeness_progress.frontend_complete)

    logger.info(f"Backend complete: {backend_complete}/{len(all_summaries)} ({backend_complete/len(all_summaries)*100:.1f}%)")
    logger.info(f"Frontend complete: {frontend_complete}/{len(all_summaries)} ({frontend_complete/len(all_summaries)*100:.1f}%)")

    # Deployment readiness
    logger.info("\n" + "-"*80)
    logger.info("DEPLOYMENT READINESS")
    logger.info("-"*80)

    deployment_ready = sum(1 for s in all_summaries if s.deployment_readiness and s.deployment_readiness.is_deployable)
    logger.info(f"Deployment ready: {deployment_ready}/{len(all_summaries)} ({deployment_ready/len(all_summaries)*100:.1f}%)")

    # Workflow details
    logger.info("\n" + "-"*80)
    logger.info("INDIVIDUAL WORKFLOW SUMMARY")
    logger.info("-"*80)

    for summary in all_summaries:
        workflow_data = {
            'workflow_id': summary.workflow_id,
            'estimated_completion': summary.gap_report.estimated_completion_percentage if summary.gap_report else 0,
            'gaps': summary.gap_report.total_gaps if summary.gap_report else 0,
            'critical_gaps': summary.gap_report.critical_gaps if summary.gap_report else 0,
            'is_deployable': summary.gap_report.is_deployable if summary.gap_report else False,
            'has_recovery_plan': summary.recovery_context is not None
        }
        stats['workflows'].append(workflow_data)

        deployable_icon = "✓" if workflow_data['is_deployable'] else "✗"
        recovery_icon = "📋" if workflow_data['has_recovery_plan'] else "  "

        logger.info(
            f"{deployable_icon} {summary.workflow_id:30} | "
            f"Completion: {workflow_data['estimated_completion']*100:5.1f}% | "
            f"Gaps: {workflow_data['gaps']:3} (Critical: {workflow_data['critical_gaps']:2}) | "
            f"{recovery_icon}"
        )

    # Save aggregate statistics
    stats_file = output_dir / "validation_statistics.json"
    with open(stats_file, 'w') as f:
        json.dump(stats, f, indent=2)

    logger.info("\n" + "="*80)
    logger.info("VALIDATION COMPLETE")
    logger.info("="*80)
    logger.info(f"Individual reports saved to: {reports_dir}")
    logger.info(f"Recovery plans saved to: {recovery_dir}")
    logger.info(f"Statistics saved to: {stats_file}")

    # Generate summary report
    summary_report_file = output_dir / "VALIDATION_SUMMARY_REPORT.md"
    generate_markdown_report(stats, all_summaries, summary_report_file)
    logger.info(f"Summary report saved to: {summary_report_file}")

    return stats, all_summaries


def generate_markdown_report(stats: Dict[str, Any], summaries: List[WorkflowValidationSummary], output_file: Path):
    """Generate a human-readable markdown report"""

    report = f"""# Workflow Validation Summary Report

**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**Total Workflows**: {stats['total_workflows']}
**Validation Time**: {stats['total_validation_time']:.2f}s

---

## Executive Summary

| Metric | Value | Percentage |
|--------|-------|------------|
| Deployable Workflows | {stats['deployable_count']} | {stats['deployable_count']/stats['total_workflows']*100:.1f}% |
| Need Recovery | {stats['needs_recovery_count']} | {stats['needs_recovery_count']/stats['total_workflows']*100:.1f}% |
| Average Completion | {stats['average_completion']*100:.1f}% | - |
| Total Gaps | {stats['total_gaps']} | - |
| Critical Gaps | {stats['total_critical_gaps']} | - |

---

## Phase Validation Results

| Phase | Passed | Warning | Failed | Pass Rate |
|-------|--------|---------|--------|-----------|
"""

    for phase, data in stats['phase_breakdown'].items():
        report += f"| {phase.title()} | {data['passed']} | {data['warning']} | {data['failed']} | {data['pass_rate']:.1f}% |\n"

    report += f"""
---

## Top 10 Common Issues

"""

    for i, (issue, count) in enumerate(list(stats['common_issues'].items())[:10], 1):
        report += f"{i}. **[{count} workflows]** {issue}\n"

    report += f"""
---

## Individual Workflow Details

| Workflow ID | Completion | Gaps | Critical | Deployable | Recovery Plan |
|-------------|------------|------|----------|------------|---------------|
"""

    for workflow in stats['workflows']:
        deployable_icon = "✅" if workflow['is_deployable'] else "❌"
        recovery_icon = "📋" if workflow['has_recovery_plan'] else "-"
        report += (
            f"| `{workflow['workflow_id']}` | "
            f"{workflow['estimated_completion']*100:.1f}% | "
            f"{workflow['gaps']} | "
            f"{workflow['critical_gaps']} | "
            f"{deployable_icon} | "
            f"{recovery_icon} |\n"
        )

    report += f"""
---

## Recovery Plans

Recovery plans have been generated for {stats['needs_recovery_count']} workflows that are not currently deployable.

Each recovery plan includes:
- **Priority-ordered fix instructions** - Specific actions to take
- **Component lists** - Missing files/modules to create
- **Recovery approach** - Recommended strategy (quick fix, incremental, or complete rework)
- **Estimated effort** - Based on completion percentage

**Location**: `recovery_contexts/[workflow_id]_recovery_plan.json`

---

## Recommendations

"""

    # Generate recommendations based on statistics
    if stats['deployable_count'] == 0:
        report += "⚠️ **CRITICAL**: No workflows are currently deployable. All workflows require fixes.\n\n"
    elif stats['deployable_count'] < stats['total_workflows'] * 0.25:
        report += "⚠️ **HIGH PRIORITY**: Less than 25% of workflows are deployable. Significant remediation required.\n\n"

    if stats['average_completion'] < 0.5:
        report += "⚠️ **Low Average Completion**: Workflows are only {:.1f}% complete on average. Consider:\n".format(stats['average_completion']*100)
        report += "   - Review workflow generation logic\n"
        report += "   - Implement validation gates during execution\n"
        report += "   - Use sub-phased implementation for better control\n\n"

    report += f"""
### Next Steps

1. **Review Recovery Plans**: Start with highest priority workflows (Priority 1)
2. **Address Common Issues**: Fix the top 3 most common issues first
3. **Implement Validation Gates**: Add validators to prevent future incomplete workflows
4. **Test Fixes**: Use the validation system to verify fixes

---

## Validation System Components Used

- ✅ **WorkflowValidator** - 5 phase validators (requirements, design, implementation, testing, deployment)
- ✅ **WorkflowGapDetector** - Gap detection and recovery context generation
- ✅ **ImplementationCompletenessChecker** - 8 sub-phase implementation tracking
- ✅ **DeploymentReadinessValidator** - Pre-deployment validation with Docker checks

---

**Report End**
"""

    with open(output_file, 'w') as f:
        f.write(report)


async def main():
    """Main entry point"""
    # Configuration
    workflows_dir = Path("/tmp/maestro_workflow")
    output_dir = Path("/tmp/maestro_workflow/validation_results")

    # Run validation
    stats, summaries = await validate_all_workflows(workflows_dir, output_dir)

    logger.info("\n" + "="*80)
    logger.info("🎉 VALIDATION TEST COMPLETE!")
    logger.info("="*80)
    logger.info(f"\nResults:")
    logger.info(f"  - {stats['deployable_count']}/{stats['total_workflows']} workflows are deployable")
    logger.info(f"  - {stats['needs_recovery_count']} recovery plans generated")
    logger.info(f"  - Average completion: {stats['average_completion']*100:.1f}%")
    logger.info(f"\nNext: Review recovery plans in {output_dir}/recovery_contexts/")


if __name__ == "__main__":
    asyncio.run(main())
