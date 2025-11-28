#!/usr/bin/env python3
"""
DAG Execution Test: Dog Marketplace Project

Comprehensive test of the DAG workflow system with a real-world requirement.
Executes all SDLC phases phase-by-phase with detailed monitoring and documentation.

Usage:
    python3 test_dog_marketplace.py
"""

import asyncio
import logging
import sys
import json
import os
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime
from dataclasses import dataclass, asdict

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

# Import workflow components
from team_execution_v2_split_mode import TeamExecutionEngineV2SplitMode
from team_execution_dual import TeamExecutionEngineDual, FeatureFlags, ExecutionMode
from team_execution_context import TeamExecutionContext


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class PhaseReview:
    """Review data for a single phase"""
    phase_name: str
    status: str  # 'success', 'warning', 'error'
    duration_seconds: float
    quality_score: float
    artifacts_count: int
    artifacts_list: List[str]
    issues: List[str]
    insights: List[str]
    context_received: Dict[str, Any]
    context_passed: Dict[str, Any]
    outputs_summary: str

    def to_dict(self):
        return asdict(self)


@dataclass
class TestExecution:
    """Overall test execution data"""
    test_id: str
    requirement: str
    start_time: datetime
    end_time: datetime
    execution_mode: str
    total_duration_seconds: float
    phases_completed: int
    phases_total: int
    overall_status: str  # 'success', 'partial', 'failed'
    phase_reviews: List[PhaseReview]
    issues_identified: List[Dict[str, Any]]

    def to_dict(self):
        data = asdict(self)
        data['start_time'] = self.start_time.isoformat()
        data['end_time'] = self.end_time.isoformat() if self.end_time else None
        return data


# =============================================================================
# TEST CONFIGURATION
# =============================================================================

# Test requirement
DOG_MARKETPLACE_REQUIREMENT = """
Build a comprehensive website for dog lovers - a marketplace platform where dog owners can buy and sell dog-related products.

## Core Features:
1. **Marketplace**
   - Product listings (food, toys, accessories, grooming products)
   - Search and filtering (by category, price, breed-specific)
   - Shopping cart and checkout
   - Payment processing (Stripe integration)
   - Order tracking

2. **User System**
   - Buyer accounts (wishlist, order history, reviews)
   - Seller accounts (store management, inventory, analytics)
   - User profiles with dog information
   - Rating and review system

3. **Social Features**
   - Product Q&A between buyers and sellers
   - Photo uploads (products and dogs)
   - Community recommendations
   - Share favorites on social media

4. **Technical Requirements**
   - Responsive design (mobile-first)
   - Fast performance (< 2s page load)
   - Secure authentication (JWT)
   - RESTful API
   - PostgreSQL database
   - React frontend
   - Node.js/Express backend
   - Docker deployment

5. **Additional Features**
   - Email notifications
   - Advanced analytics for sellers
   - Admin dashboard
   - Inventory management

Target: Production-ready MVP that can be deployed immediately.
"""

# Output configuration
OUTPUT_DIR = Path("./generated_dog_marketplace")
CHECKPOINT_DIR = Path("./checkpoints_dog_marketplace")
LOG_FILE = Path("./dog_marketplace_test.log")
REPORT_FILE = Path("./DOG_MARKETPLACE_TEST_REPORT.md")
ISSUES_FILE = Path("./issues_identified.md")


# =============================================================================
# LOGGING SETUP
# =============================================================================

def setup_logging():
    """Configure comprehensive logging"""
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - [%(levelname)s] - %(name)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # File handler
    file_handler = logging.FileHandler(LOG_FILE, mode='w')
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)

    # Root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)

    print(f"✅ Logging configured")
    print(f"   Log file: {LOG_FILE}")
    print()


# =============================================================================
# TEST RUNNER
# =============================================================================

class DogMarketplaceTest:
    """
    Comprehensive test runner for dog marketplace project.

    Executes all SDLC phases with detailed monitoring and documentation.
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.test_id = f"dog-marketplace-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        self.start_time = None
        self.end_time = None
        self.phase_reviews: List[PhaseReview] = []
        self.issues: List[Dict[str, Any]] = []
        self.engine = None
        self.dual_engine = None
        self.context = None

    def log_section(self, title: str):
        """Log a section separator"""
        separator = "=" * 80
        self.logger.info("")
        self.logger.info(separator)
        self.logger.info(f"  {title}")
        self.logger.info(separator)
        self.logger.info("")

    def log_phase_start(self, phase_name: str, phase_num: int, total_phases: int):
        """Log phase start"""
        self.logger.info("")
        self.logger.info("─" * 80)
        self.logger.info(f"🚀 PHASE {phase_num}/{total_phases}: {phase_name.upper()}")
        self.logger.info("─" * 80)
        self.logger.info("")

    def setup_environment(self):
        """Set up test environment and configuration"""
        self.log_section("STEP 1: ENVIRONMENT SETUP")

        # Set feature flags for DAG parallel mode
        os.environ['MAESTRO_ENABLE_DAG_EXECUTION'] = 'true'
        os.environ['MAESTRO_ENABLE_PARALLEL_EXECUTION'] = 'true'
        os.environ['MAESTRO_ENABLE_CONTEXT_PERSISTENCE'] = 'true'
        os.environ['MAESTRO_ENABLE_EXECUTION_EVENTS'] = 'true'
        os.environ['MAESTRO_ENABLE_RETRY_LOGIC'] = 'false'

        # Verify configuration
        flags = FeatureFlags()
        mode = flags.get_execution_mode()

        self.logger.info("Feature Flags Configuration:")
        self.logger.info(f"  Execution Mode: {mode.value}")
        self.logger.info(f"  DAG Execution: {flags.enable_dag_execution}")
        self.logger.info(f"  Parallel Execution: {flags.enable_parallel_execution}")
        self.logger.info(f"  Context Persistence: {flags.enable_context_persistence}")
        self.logger.info(f"  Execution Events: {flags.enable_execution_events}")
        self.logger.info("")

        if mode != ExecutionMode.DAG_PARALLEL:
            raise ValueError(f"Expected DAG_PARALLEL mode, got {mode.value}")

        # Create directories
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)

        self.logger.info("Output Directories:")
        self.logger.info(f"  Generated Project: {OUTPUT_DIR}")
        self.logger.info(f"  Checkpoints: {CHECKPOINT_DIR}")
        self.logger.info("")

        self.logger.info("✅ Environment setup complete")

    def initialize_engine(self):
        """Initialize execution engines"""
        self.log_section("STEP 2: ENGINE INITIALIZATION")

        # Create split mode engine (handles phase-by-phase execution)
        self.engine = TeamExecutionEngineV2SplitMode(
            output_dir=str(OUTPUT_DIR),
            checkpoint_dir=str(CHECKPOINT_DIR),
            quality_threshold=0.70,
            enable_contracts=False  # Disable for simpler test
        )

        self.logger.info("✅ TeamExecutionEngineV2SplitMode initialized")

        # Wrap with dual-mode engine (enables DAG execution)
        self.dual_engine = TeamExecutionEngineDual(
            linear_engine=self.engine,
            feature_flags=FeatureFlags()
        )

        self.logger.info("✅ TeamExecutionEngineDual initialized")
        self.logger.info("")

    async def execute_phase(self, phase_name: str, phase_num: int, total_phases: int) -> PhaseReview:
        """Execute a single phase with review"""
        self.log_phase_start(phase_name, phase_num, total_phases)

        phase_start = datetime.now()
        issues_found = []
        insights = []

        try:
            # Execute phase
            self.context = await self.engine.execute_phase(
                phase_name=phase_name,
                checkpoint=self.context,
                requirement=DOG_MARKETPLACE_REQUIREMENT if phase_name == "requirements" else None
            )

            phase_end = datetime.now()
            duration = (phase_end - phase_start).total_seconds()

            # Get phase result
            phase_result = self.context.workflow.get_phase_result(phase_name)

            # Extract metrics
            quality_metrics = self.context.team_state.quality_metrics.get(phase_name, {})
            quality_score = quality_metrics.get('overall_quality', 0.0)
            artifacts = phase_result.artifacts_created if phase_result else []

            # Review phase outputs
            self.logger.info("")
            self.logger.info("📊 PHASE REVIEW:")
            self.logger.info(f"   Status: {phase_result.status.value if phase_result else 'unknown'}")
            self.logger.info(f"   Duration: {duration:.2f} seconds")
            self.logger.info(f"   Quality Score: {quality_score:.0%}")
            self.logger.info(f"   Artifacts Created: {len(artifacts)}")

            # List artifacts
            if artifacts:
                self.logger.info("")
                self.logger.info("   Artifacts:")
                for artifact in artifacts[:10]:  # Show first 10
                    self.logger.info(f"      - {artifact}")
                if len(artifacts) > 10:
                    self.logger.info(f"      ... and {len(artifacts) - 10} more")

            # Check for issues
            if quality_score < 0.70:
                issue = f"Quality score ({quality_score:.0%}) below threshold (70%)"
                issues_found.append(issue)
                self.logger.warning(f"   ⚠️  {issue}")

            if not artifacts:
                issue = "No artifacts created"
                issues_found.append(issue)
                self.logger.warning(f"   ⚠️  {issue}")

            # Add insights
            if quality_score >= 0.85:
                insights.append(f"Excellent quality score: {quality_score:.0%}")

            if phase_name == "implementation" and duration < 60:
                insights.append("Fast implementation phase (completed in < 1 minute)")

            # Determine status
            if phase_result.status.value == "completed" and quality_score >= 0.70:
                status = "success"
            elif phase_result.status.value == "completed":
                status = "warning"
            else:
                status = "error"

            # Create summary
            outputs_summary = self._create_phase_summary(phase_name, phase_result)

            # Create review
            review = PhaseReview(
                phase_name=phase_name,
                status=status,
                duration_seconds=duration,
                quality_score=quality_score,
                artifacts_count=len(artifacts),
                artifacts_list=artifacts,
                issues=issues_found,
                insights=insights,
                context_received=phase_result.context_received if phase_result else {},
                context_passed=phase_result.context_passed if phase_result else {},
                outputs_summary=outputs_summary
            )

            self.logger.info("")
            if status == "success":
                self.logger.info("✅ Phase completed successfully")
            elif status == "warning":
                self.logger.warning("⚠️  Phase completed with warnings")
            else:
                self.logger.error("❌ Phase failed")

            # Log issues to global list
            for issue in issues_found:
                self.issues.append({
                    'phase': phase_name,
                    'severity': 'warning' if status == 'warning' else 'error',
                    'message': issue,
                    'timestamp': datetime.now().isoformat()
                })

            return review

        except Exception as e:
            phase_end = datetime.now()
            duration = (phase_end - phase_start).total_seconds()

            self.logger.error(f"❌ Phase failed with exception: {e}", exc_info=True)

            # Create error review
            review = PhaseReview(
                phase_name=phase_name,
                status="error",
                duration_seconds=duration,
                quality_score=0.0,
                artifacts_count=0,
                artifacts_list=[],
                issues=[str(e)],
                insights=[],
                context_received={},
                context_passed={},
                outputs_summary=f"Phase failed: {e}"
            )

            # Log to global issues
            self.issues.append({
                'phase': phase_name,
                'severity': 'critical',
                'message': str(e),
                'timestamp': datetime.now().isoformat()
            })

            return review

    def _create_phase_summary(self, phase_name: str, phase_result) -> str:
        """Create a summary of phase outputs"""
        if not phase_result:
            return "No results available"

        summary_parts = [
            f"Phase: {phase_name}",
            f"Status: {phase_result.status.value}",
            f"Duration: {phase_result.duration_seconds:.2f}s",
            f"Artifacts: {len(phase_result.artifacts_created)}",
        ]

        # Add key outputs (truncated)
        if phase_result.outputs:
            summary_parts.append("\nKey Outputs:")
            outputs_str = json.dumps(phase_result.outputs, indent=2)
            if len(outputs_str) > 500:
                summary_parts.append(outputs_str[:500] + "...(truncated)")
            else:
                summary_parts.append(outputs_str)

        return "\n".join(summary_parts)

    async def run_test(self):
        """Run the complete test"""
        self.start_time = datetime.now()

        try:
            # Setup
            self.setup_environment()
            self.initialize_engine()

            # Execute all SDLC phases
            self.log_section("STEP 3: SDLC PHASE EXECUTION")

            phases = ["requirements", "design", "implementation", "testing", "deployment"]

            for i, phase_name in enumerate(phases, 1):
                review = await self.execute_phase(phase_name, i, len(phases))
                self.phase_reviews.append(review)

                # Pause between phases for readability
                if i < len(phases):
                    await asyncio.sleep(1)

            self.end_time = datetime.now()

            # Generate reports
            self.log_section("STEP 4: REPORT GENERATION")
            self.generate_reports()

            self.log_section("TEST COMPLETE")
            self.print_summary()

        except Exception as e:
            self.logger.error(f"Test execution failed: {e}", exc_info=True)
            self.end_time = datetime.now()
            raise

    def generate_reports(self):
        """Generate comprehensive test reports"""
        # Generate main report
        report_content = self._generate_markdown_report()
        REPORT_FILE.write_text(report_content)
        self.logger.info(f"✅ Generated report: {REPORT_FILE}")

        # Generate issues log
        issues_content = self._generate_issues_log()
        ISSUES_FILE.write_text(issues_content)
        self.logger.info(f"✅ Generated issues log: {ISSUES_FILE}")

        # Generate JSON data
        json_file = Path("./dog_marketplace_test_data.json")
        test_execution = TestExecution(
            test_id=self.test_id,
            requirement=DOG_MARKETPLACE_REQUIREMENT,
            start_time=self.start_time,
            end_time=self.end_time,
            execution_mode="DAG_PARALLEL",
            total_duration_seconds=(self.end_time - self.start_time).total_seconds(),
            phases_completed=len([r for r in self.phase_reviews if r.status != 'error']),
            phases_total=len(self.phase_reviews),
            overall_status=self._determine_overall_status(),
            phase_reviews=self.phase_reviews,
            issues_identified=self.issues
        )

        json_file.write_text(json.dumps(test_execution.to_dict(), indent=2, default=str))
        self.logger.info(f"✅ Generated JSON data: {json_file}")

    def _determine_overall_status(self) -> str:
        """Determine overall test status"""
        if not self.phase_reviews:
            return "failed"

        statuses = [r.status for r in self.phase_reviews]

        if all(s == "success" for s in statuses):
            return "success"
        elif any(s == "error" for s in statuses):
            return "partial"
        else:
            return "warning"

    def _generate_markdown_report(self) -> str:
        """Generate markdown test report"""
        duration = (self.end_time - self.start_time).total_seconds()
        overall_status = self._determine_overall_status()

        # Status emoji
        status_emoji = {"success": "✅", "partial": "⚠️", "warning": "⚠️", "failed": "❌"}
        emoji = status_emoji.get(overall_status, "❓")

        lines = [
            "# Dog Marketplace DAG Execution Test Report",
            "",
            f"**Test ID:** `{self.test_id}`",
            f"**Execution Date:** {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}",
            f"**Duration:** {duration:.2f} seconds ({duration/60:.1f} minutes)",
            f"**Status:** {emoji} {overall_status.upper()}",
            "",
            "---",
            "",
            "## Executive Summary",
            "",
            f"This report documents the execution of a comprehensive DAG workflow test using the dog marketplace requirement.",
            f"The test ran through all {len(self.phase_reviews)} SDLC phases in **DAG_PARALLEL** mode, capturing detailed metrics, artifacts, and issues.",
            "",
            f"- **Phases Completed:** {len([r for r in self.phase_reviews if r.status != 'error'])}/{len(self.phase_reviews)}",
            f"- **Issues Identified:** {len(self.issues)}",
            f"- **Total Artifacts:** {sum(r.artifacts_count for r in self.phase_reviews)}",
            "",
        ]

        # Test Requirement
        lines.extend([
            "## Test Requirement",
            "",
            "```",
            DOG_MARKETPLACE_REQUIREMENT.strip(),
            "```",
            "",
        ])

        # Phase Breakdown
        lines.extend([
            "## Phase-by-Phase Execution",
            "",
        ])

        for i, review in enumerate(self.phase_reviews, 1):
            status_icon = {"success": "✅", "warning": "⚠️", "error": "❌"}[review.status]

            lines.extend([
                f"### Phase {i}: {review.phase_name.upper()}",
                "",
                f"**Status:** {status_icon} {review.status.upper()}",
                f"**Duration:** {review.duration_seconds:.2f}s",
                f"**Quality Score:** {review.quality_score:.0%}",
                f"**Artifacts:** {review.artifacts_count}",
                "",
            ])

            if review.artifacts_list:
                lines.append("**Artifacts Created:**")
                for artifact in review.artifacts_list[:10]:
                    lines.append(f"- `{artifact}`")
                if review.artifacts_count > 10:
                    lines.append(f"- *...and {review.artifacts_count - 10} more*")
                lines.append("")

            if review.issues:
                lines.append("**Issues:**")
                for issue in review.issues:
                    lines.append(f"- ⚠️ {issue}")
                lines.append("")

            if review.insights:
                lines.append("**Insights:**")
                for insight in review.insights:
                    lines.append(f"- 💡 {insight}")
                lines.append("")

            lines.append("---")
            lines.append("")

        # Issues Summary
        if self.issues:
            lines.extend([
                "## Issues Identified",
                "",
                f"Total issues: {len(self.issues)}",
                "",
            ])

            # Group by severity
            critical = [i for i in self.issues if i['severity'] == 'critical']
            errors = [i for i in self.issues if i['severity'] == 'error']
            warnings = [i for i in self.issues if i['severity'] == 'warning']

            if critical:
                lines.append(f"### 🔴 Critical ({len(critical)})")
                lines.append("")
                for issue in critical:
                    lines.append(f"- **[{issue['phase']}]** {issue['message']}")
                lines.append("")

            if errors:
                lines.append(f"### ❌ Errors ({len(errors)})")
                lines.append("")
                for issue in errors:
                    lines.append(f"- **[{issue['phase']}]** {issue['message']}")
                lines.append("")

            if warnings:
                lines.append(f"### ⚠️ Warnings ({len(warnings)})")
                lines.append("")
                for issue in warnings:
                    lines.append(f"- **[{issue['phase']}]** {issue['message']}")
                lines.append("")

        # Statistics
        lines.extend([
            "## Statistics",
            "",
            "| Metric | Value |",
            "|--------|-------|",
            f"| Total Duration | {duration:.2f}s ({duration/60:.1f}min) |",
            f"| Phases Completed | {len([r for r in self.phase_reviews if r.status != 'error'])}/{len(self.phase_reviews)} |",
            f"| Average Phase Duration | {duration/len(self.phase_reviews):.2f}s |",
            f"| Average Quality Score | {sum(r.quality_score for r in self.phase_reviews)/len(self.phase_reviews):.0%} |",
            f"| Total Artifacts | {sum(r.artifacts_count for r in self.phase_reviews)} |",
            f"| Issues Identified | {len(self.issues)} |",
            "",
        ])

        # Recommendations
        lines.extend([
            "## Recommendations",
            "",
        ])

        if overall_status == "success":
            lines.append("✅ All phases completed successfully! The system is working as expected.")
        else:
            lines.append("⚠️ Some issues were identified. Review the issues section above for details.")

        lines.extend([
            "",
            "### Next Steps",
            "",
            "1. Review all generated artifacts in `./generated_dog_marketplace/`",
            "2. Check detailed logs in `dog_marketplace_test.log`",
            "3. Address any identified issues",
            "4. Test the deployed application",
            "5. Verify all functionality works as expected",
            "",
            "---",
            "",
            f"*Report generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*",
        ])

        return "\n".join(lines)

    def _generate_issues_log(self) -> str:
        """Generate issues log markdown"""
        lines = [
            "# Issues Identified - Dog Marketplace Test",
            "",
            f"**Test ID:** `{self.test_id}`",
            f"**Date:** {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}",
            f"**Total Issues:** {len(self.issues)}",
            "",
            "---",
            "",
        ]

        if not self.issues:
            lines.append("✅ No issues identified! All phases completed successfully.")
            return "\n".join(lines)

        # Group by phase
        phases = list(set(i['phase'] for i in self.issues))

        for phase in phases:
            phase_issues = [i for i in self.issues if i['phase'] == phase]
            lines.extend([
                f"## {phase.upper()} Phase",
                "",
                f"Issues: {len(phase_issues)}",
                "",
            ])

            for issue in phase_issues:
                severity_icon = {"critical": "🔴", "error": "❌", "warning": "⚠️"}[issue['severity']]
                lines.extend([
                    f"### {severity_icon} {issue['severity'].upper()}",
                    "",
                    f"**Message:** {issue['message']}",
                    f"**Timestamp:** {issue['timestamp']}",
                    "",
                ])

        return "\n".join(lines)

    def print_summary(self):
        """Print test summary to console"""
        duration = (self.end_time - self.start_time).total_seconds()
        overall_status = self._determine_overall_status()

        status_emoji = {"success": "✅", "partial": "⚠️", "warning": "⚠️", "failed": "❌"}
        emoji = status_emoji.get(overall_status, "❓")

        self.logger.info(f"")
        self.logger.info(f"{emoji} TEST STATUS: {overall_status.upper()}")
        self.logger.info(f"")
        self.logger.info(f"Duration: {duration:.2f} seconds ({duration/60:.1f} minutes)")
        self.logger.info(f"Phases: {len([r for r in self.phase_reviews if r.status != 'error'])}/{len(self.phase_reviews)} completed")
        self.logger.info(f"Issues: {len(self.issues)} identified")
        self.logger.info(f"Artifacts: {sum(r.artifacts_count for r in self.phase_reviews)} created")
        self.logger.info(f"")
        self.logger.info(f"Reports:")
        self.logger.info(f"  - Main Report: {REPORT_FILE}")
        self.logger.info(f"  - Issues Log: {ISSUES_FILE}")
        self.logger.info(f"  - Detailed Log: {LOG_FILE}")
        self.logger.info(f"  - Generated Project: {OUTPUT_DIR}")
        self.logger.info(f"")


# =============================================================================
# MAIN
# =============================================================================

async def main():
    """Main entry point"""
    print()
    print("=" * 80)
    print("  DOG MARKETPLACE DAG EXECUTION TEST")
    print("=" * 80)
    print()
    print("This test will execute a comprehensive SDLC workflow for a dog marketplace")
    print("platform using the DAG workflow system in parallel mode.")
    print()
    print(f"Expected duration: 30-60 minutes")
    print()
    print("=" * 80)
    print()

    # Setup logging
    setup_logging()

    # Create and run test
    test = DogMarketplaceTest()

    try:
        await test.run_test()
        sys.exit(0)
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
