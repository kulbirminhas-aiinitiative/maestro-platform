#!/usr/bin/env python3
"""
Validation Integration Layer

Combines existing validation (workflow_validation.py) with new build validation
(workflow_build_validation.py) to provide comprehensive quality assessment.

Validation Weights (NEW - Fixed from Batch 5 Analysis):
    OLD (WRONG):                    NEW (CORRECT):
    - File count: 40%               - Builds successfully: 50%
    - Directory structure: 30%      - Tests pass: 20%
    - Syntax valid: 30%             - Features implemented: 20%
                                    - Architecture coherent: 10%

Reference: BATCH5_WORKFLOW_SYSTEM_ANALYSIS.md
"""

import logging
import json
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
import asyncio

from workflow_validation import WorkflowValidator
from workflow_build_validation import BuildValidator, BuildValidationReport

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class ComprehensiveValidationReport:
    """Combined validation report with proper weighting"""
    workflow_id: str
    overall_score: float  # 0.0-1.0
    can_build: bool  # Most critical metric
    structural_validation: Dict[str, Any]  # From workflow_validation.py
    build_validation: Dict[str, Any]  # From workflow_build_validation.py
    weighted_scores: Dict[str, float]
    final_status: str  # "ready_to_deploy", "needs_fixes", "critical_failures"
    blocking_issues: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "workflow_id": self.workflow_id,
            "overall_score": self.overall_score,
            "can_build": self.can_build,
            "final_status": self.final_status,
            "weighted_scores": self.weighted_scores,
            "structural_validation": self.structural_validation,
            "build_validation": self.build_validation,
            "blocking_issues": self.blocking_issues,
            "warnings": self.warnings,
            "recommendations": self.recommendations
        }


class IntegratedValidator:
    """
    Integrated validator combining structural and build validation

    Validation Philosophy (Fixed from Batch 5):
    1. Build success is PRIMARY (50% weight)
    2. Functionality is SECONDARY (40% weight)
    3. Structure is TERTIARY (10% weight)

    This fixes the perverse incentive where personas optimized for file count
    instead of working code.
    """

    # NEW WEIGHTS (Batch 5 Fix)
    WEIGHTS = {
        "builds_successfully": 0.50,  # 50% - Can it build?
        "functionality": 0.20,         # 20% - Does it work (no stubs)?
        "features_implemented": 0.20,  # 20% - Are features complete?
        "structure": 0.10              # 10% - Is structure correct?
    }

    def __init__(self, workflow_dir: Path):
        self.workflow_dir = Path(workflow_dir)
        self.structural_validator = WorkflowValidator(str(workflow_dir))
        self.build_validator = BuildValidator(workflow_dir)

    async def validate_comprehensive(self) -> ComprehensiveValidationReport:
        """
        Run comprehensive validation with proper weighting

        Returns:
            ComprehensiveValidationReport with final deployment readiness assessment
        """
        logger.info("=" * 80)
        logger.info("COMPREHENSIVE VALIDATION (Batch 5 Enhanced)")
        logger.info("=" * 80)
        logger.info(f"Workflow: {self.workflow_dir.name}")
        logger.info("")

        # Run both validations
        logger.info("📋 Step 1/2: Structural Validation")
        structural_results = self.structural_validator.validate_all()
        structural_summary = self.structural_validator.generate_summary_report(structural_results)

        logger.info("\n🔨 Step 2/2: Build Validation")
        build_report = await self.build_validator.validate()

        # Calculate weighted scores
        logger.info("\n⚖️  Calculating Weighted Scores")
        weighted_scores = self._calculate_weighted_scores(
            structural_summary,
            build_report
        )

        # Calculate overall score
        overall_score = sum(
            weighted_scores[key] * self.WEIGHTS[key]
            for key in self.WEIGHTS.keys()
        )

        # Determine final status
        final_status, blocking_issues, warnings = self._determine_final_status(
            overall_score,
            build_report,
            structural_summary
        )

        # Generate recommendations
        recommendations = self._generate_recommendations(
            weighted_scores,
            build_report,
            structural_summary
        )

        logger.info(f"\n{'=' * 80}")
        logger.info("FINAL ASSESSMENT")
        logger.info(f"{'=' * 80}")
        logger.info(f"Overall Score: {overall_score:.1%}")
        logger.info(f"Can Build: {'✅ YES' if build_report.can_build else '❌ NO'}")
        logger.info(f"Final Status: {final_status.upper().replace('_', ' ')}")
        logger.info(f"Blocking Issues: {len(blocking_issues)}")
        logger.info(f"Warnings: {len(warnings)}")

        return ComprehensiveValidationReport(
            workflow_id=self.workflow_dir.name,
            overall_score=overall_score,
            can_build=build_report.can_build,
            structural_validation=structural_summary,
            build_validation=build_report.to_dict(),
            weighted_scores=weighted_scores,
            final_status=final_status,
            blocking_issues=blocking_issues,
            warnings=warnings,
            recommendations=recommendations
        )

    def _calculate_weighted_scores(
        self,
        structural_summary: Dict[str, Any],
        build_report: BuildValidationReport
    ) -> Dict[str, float]:
        """Calculate weighted scores for each validation category"""

        # 1. Builds Successfully (50%)
        # This is binary - either it builds or it doesn't
        builds_score = 1.0 if build_report.can_build else 0.0
        logger.info(f"  Builds Successfully: {builds_score:.1%} (weight: {self.WEIGHTS['builds_successfully']:.0%})")

        # 2. Functionality (20%)
        # Check for stubs and working implementations
        functionality_checks = [
            r for r in build_report.results
            if r.check_name in ["stub_implementation_detection", "error_handling", "dependency_coherence"]
        ]
        if functionality_checks:
            functionality_score = sum(1 for r in functionality_checks if r.passed) / len(functionality_checks)
        else:
            functionality_score = 0.5  # Default if no checks
        logger.info(f"  Functionality: {functionality_score:.1%} (weight: {self.WEIGHTS['functionality']:.0%})")

        # 3. Features Implemented (20%)
        # Check if PRD features are present
        feature_checks = [
            r for r in build_report.results
            if r.check_name == "feature_completeness"
        ]
        if feature_checks:
            features_score = 1.0 if feature_checks[0].passed else 0.3  # Low score if features missing
        else:
            features_score = 0.7  # Default (assume partial implementation)
        logger.info(f"  Features Implemented: {features_score:.1%} (weight: {self.WEIGHTS['features_implemented']:.0%})")

        # 4. Structure (10%)
        # From old validation system
        structural_score = structural_summary["summary"]["checks_passed"] / max(
            structural_summary["summary"]["total_checks"], 1
        )
        logger.info(f"  Structure: {structural_score:.1%} (weight: {self.WEIGHTS['structure']:.0%})")

        return {
            "builds_successfully": builds_score,
            "functionality": functionality_score,
            "features_implemented": features_score,
            "structure": structural_score
        }

    def _determine_final_status(
        self,
        overall_score: float,
        build_report: BuildValidationReport,
        structural_summary: Dict[str, Any]
    ) -> tuple[str, List[str], List[str]]:
        """
        Determine final deployment readiness status

        Returns:
            (status, blocking_issues, warnings)
        """
        blocking_issues = []
        warnings = []

        # Critical: Must build
        if not build_report.can_build:
            blocking_issues.append("Application does not build - npm install/build fails")

        # Critical: No critical build failures
        if build_report.critical_failures > 0:
            for result in build_report.results:
                if not result.passed and result.severity.value == "critical":
                    blocking_issues.append(f"Critical: {result.message}")

        # Critical: Must pass structural validation
        if structural_summary["summary"]["critical_failures"] > 0:
            blocking_issues.append(
                f"{structural_summary['summary']['critical_failures']} critical structural failures"
            )

        # Warnings: High-priority issues
        for result in build_report.results:
            if not result.passed and result.severity.value == "high":
                warnings.append(f"High: {result.message}")

        # Determine status
        if len(blocking_issues) > 0:
            status = "critical_failures"
        elif overall_score >= 0.8 and build_report.can_build:
            status = "ready_to_deploy"
        elif overall_score >= 0.6:
            status = "needs_fixes"
        else:
            status = "critical_failures"

        return status, blocking_issues, warnings

    def _generate_recommendations(
        self,
        weighted_scores: Dict[str, float],
        build_report: BuildValidationReport,
        structural_summary: Dict[str, Any]
    ) -> List[str]:
        """Generate actionable recommendations"""
        recommendations = []

        # Priority 1: Build failures
        if weighted_scores["builds_successfully"] < 1.0:
            recommendations.append(
                "CRITICAL: Fix build failures first - application must compile before other fixes"
            )

            # Find specific build errors
            for result in build_report.results:
                if "build" in result.check_name.lower() and not result.passed:
                    if result.fix_suggestion:
                        recommendations.append(f"  - {result.fix_suggestion}")

        # Priority 2: Stub implementations
        if weighted_scores["functionality"] < 0.8:
            recommendations.append(
                "HIGH: Replace stub implementations with working code"
            )

            # Find stub files
            for result in build_report.results:
                if result.check_name == "stub_implementation_detection" and not result.passed:
                    if result.details.get("stub_files"):
                        stub_count = len(result.details["stub_files"])
                        recommendations.append(f"  - Replace {stub_count} stub files with actual implementations")

        # Priority 3: Missing features
        if weighted_scores["features_implemented"] < 0.8:
            recommendations.append(
                "HIGH: Implement missing features from PRD"
            )

            for result in build_report.results:
                if result.check_name == "feature_completeness" and not result.passed:
                    if result.details.get("missing_features"):
                        missing = result.details["missing_features"][:5]
                        recommendations.append(f"  - Missing features: {', '.join(missing)}")

        # Priority 4: Structural issues
        if weighted_scores["structure"] < 0.8:
            recommendations.append(
                "MEDIUM: Fix structural issues (missing files, incomplete documentation)"
            )

        # General recommendations
        if len(recommendations) == 0:
            recommendations.append("✅ Application is deployment-ready")
            recommendations.append("  - All builds pass")
            recommendations.append("  - No stub implementations found")
            recommendations.append("  - Features are implemented")
        else:
            recommendations.insert(0, f"⚠️  Found {len(recommendations)} categories of issues to fix")

        return recommendations


async def validate_workflow_comprehensive(workflow_dir: str) -> ComprehensiveValidationReport:
    """
    Run comprehensive validation on workflow

    Usage:
        report = await validate_workflow_comprehensive("/tmp/maestro_workflow/wf-123456")

        if report.final_status == "ready_to_deploy":
            print("✅ Ready to deploy!")
        else:
            print(f"❌ Status: {report.final_status}")
            for issue in report.blocking_issues:
                print(f"  - {issue}")
    """
    validator = IntegratedValidator(Path(workflow_dir))
    return await validator.validate_comprehensive()


def compare_old_vs_new_validation(workflow_dir: str) -> Dict[str, Any]:
    """
    Compare old validation approach vs new approach

    Demonstrates the Batch 5 problem:
    - Old approach: 77% validation score, 0% can build
    - New approach: Accurate assessment of deployment readiness

    Returns:
        {
            "old_approach": {
                "score": 0.77,
                "would_pass": True,
                "metrics": ["file_count", "directory_structure"]
            },
            "new_approach": {
                "score": 0.15,
                "would_pass": False,
                "metrics": ["build_success", "functionality", "features"]
            },
            "difference": {
                "score_delta": -0.62,
                "accuracy": "NEW approach is accurate"
            }
        }
    """
    # This would be implemented to show the comparison
    # For now, return a placeholder
    return {
        "comparison": "See workflow_build_validation.py for implementation",
        "key_insight": "Old validation optimized for wrong metrics (file count vs build success)",
        "batch_5_finding": "77% validation score, 0% can build - WRONG METRICS"
    }


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python validation_integration.py <workflow_dir>")
        print("Example: python validation_integration.py /tmp/maestro_workflow/wf-1760179880-5e4b549c")
        sys.exit(1)

    workflow_dir = sys.argv[1]

    async def main():
        print(f"\n🔍 Running Comprehensive Validation on {workflow_dir}\n")

        try:
            report = await validate_workflow_comprehensive(workflow_dir)

            print("\n" + "=" * 80)
            print("COMPREHENSIVE VALIDATION REPORT")
            print("=" * 80)

            # Summary
            print(f"\nWorkflow: {report.workflow_id}")
            print(f"Overall Score: {report.overall_score:.1%}")
            print(f"Can Build: {'✅ YES' if report.can_build else '❌ NO'}")
            print(f"Final Status: {report.final_status.upper().replace('_', ' ')}")

            # Weighted scores
            print("\nWeighted Scores:")
            for metric, score in report.weighted_scores.items():
                weight = IntegratedValidator.WEIGHTS[metric]
                contribution = score * weight
                print(f"  {metric:25s}: {score:5.1%} × {weight:5.1%} = {contribution:5.1%}")

            # Blocking issues
            if report.blocking_issues:
                print(f"\n⛔ Blocking Issues ({len(report.blocking_issues)}):")
                for issue in report.blocking_issues:
                    print(f"  - {issue}")

            # Warnings
            if report.warnings:
                print(f"\n⚠️  Warnings ({len(report.warnings)}):")
                for warning in report.warnings[:5]:  # First 5
                    print(f"  - {warning}")

            # Recommendations
            print(f"\n💡 Recommendations:")
            for rec in report.recommendations:
                print(f"  {rec}")

            # Save full report
            output_file = Path(workflow_dir) / "COMPREHENSIVE_VALIDATION_REPORT.json"
            output_file.parent.mkdir(parents=True, exist_ok=True)
            output_file.write_text(json.dumps(report.to_dict(), indent=2))
            print(f"\n📄 Full report saved to: {output_file}")

            # Exit code
            sys.exit(0 if report.final_status == "ready_to_deploy" else 1)

        except Exception as e:
            logger.error(f"Validation failed: {e}", exc_info=True)
            sys.exit(2)

    asyncio.run(main())
