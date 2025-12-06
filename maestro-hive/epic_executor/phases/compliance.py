"""
Phase 8: Compliance

Self-compliance check and score calculation.
This phase validates the overall execution meets 95% threshold.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from ..models import (
    ACEvidence,
    AcceptanceCriterion,
    ComplianceScore,
    DocumentInfo,
    ExecutionPhase,
    PhaseResult,
)


@dataclass
class ComplianceResult:
    """Result from the compliance phase."""
    compliance_score: ComplianceScore
    gaps: List[str]
    recommendations: List[str]
    iteration_needed: bool


class CompliancePhase:
    """
    Phase 8: Self-Compliance Check

    Responsibilities:
    1. Calculate compliance score using standard formula
    2. Identify gaps if score < 95%
    3. Generate recommendations for improvement
    4. Determine if iteration is needed
    """

    PASSING_THRESHOLD = 95.0

    def __init__(self):
        """Initialize the compliance phase."""
        pass

    async def execute(
        self,
        documents: List[DocumentInfo],
        acceptance_criteria: List[AcceptanceCriterion],
        evidence: List[ACEvidence],
        implementation_files: List[str],
        test_files: List[str],
        blocking_todos: int,
        build_passes: bool,
    ) -> Tuple[PhaseResult, Optional[ComplianceResult]]:
        """
        Execute the compliance phase.

        Args:
            documents: Created Confluence documents
            acceptance_criteria: List of ACs
            evidence: Collected evidence
            implementation_files: Implementation file paths
            test_files: Test file paths
            blocking_todos: Number of blocking TODOs
            build_passes: Whether build passed

        Returns:
            Tuple of (PhaseResult, ComplianceResult or None if failed)
        """
        started_at = datetime.now()
        errors: List[str] = []
        warnings: List[str] = []
        artifacts: List[str] = []

        try:
            # Build compliance score
            score = ComplianceScore(
                docs_complete=len(documents),
                docs_total=6,
                acs_implemented=sum(
                    1 for ac in acceptance_criteria
                    if ac.status.value in ["implemented", "tested", "verified"]
                ),
                acs_total=len(acceptance_criteria),
                test_files=len(test_files),
                impl_files=len(implementation_files),
                acs_with_evidence=len([e for e in evidence if e.implementation_file]),
                blocking_todos=blocking_todos,
                build_passes=build_passes,
            )

            # Calculate scores
            total_score = score.calculate()
            artifacts.append(f"Compliance Score: {total_score:.1f}/100")

            # Identify gaps
            gaps = self._identify_gaps(score)
            if gaps:
                for gap in gaps:
                    warnings.append(gap)

            # Generate recommendations
            recommendations = self._generate_recommendations(score)

            # Determine if iteration needed
            iteration_needed = total_score < self.PASSING_THRESHOLD

            if iteration_needed:
                warnings.append(
                    f"Score {total_score:.1f}% is below {self.PASSING_THRESHOLD}% threshold"
                )
            else:
                artifacts.append("PASS: Score meets compliance threshold")

            # Build result
            result = ComplianceResult(
                compliance_score=score,
                gaps=gaps,
                recommendations=recommendations,
                iteration_needed=iteration_needed,
            )

            completed_at = datetime.now()
            duration = (completed_at - started_at).total_seconds()

            phase_result = PhaseResult(
                phase=ExecutionPhase.COMPLIANCE,
                success=not iteration_needed,
                started_at=started_at,
                completed_at=completed_at,
                duration_seconds=duration,
                artifacts_created=artifacts,
                errors=errors,
                warnings=warnings,
                metrics={
                    "total_score": total_score,
                    "documentation_score": score.documentation_score,
                    "implementation_score": score.implementation_score,
                    "test_coverage_score": score.test_coverage_score,
                    "acceptance_criteria_score": score.acceptance_criteria_score,
                    "correctness_score": score.correctness_score,
                    "build_score": score.build_score,
                    "passing": score.passing,
                }
            )

            return phase_result, result

        except Exception as e:
            errors.append(str(e))
            completed_at = datetime.now()
            duration = (completed_at - started_at).total_seconds()

            phase_result = PhaseResult(
                phase=ExecutionPhase.COMPLIANCE,
                success=False,
                started_at=started_at,
                completed_at=completed_at,
                duration_seconds=duration,
                artifacts_created=artifacts,
                errors=errors,
                warnings=warnings,
            )

            return phase_result, None

    def _identify_gaps(self, score: ComplianceScore) -> List[str]:
        """Identify gaps in compliance."""
        gaps = []

        # Documentation gaps
        if score.docs_complete < score.docs_total:
            missing = score.docs_total - score.docs_complete
            gaps.append(f"GAP-DOC: Missing {missing} of {score.docs_total} required documents")

        # Implementation gaps
        if score.acs_implemented < score.acs_total:
            missing = score.acs_total - score.acs_implemented
            gaps.append(f"GAP-IMPL: {missing} of {score.acs_total} ACs not implemented")

        # Test coverage gaps
        if score.test_files < score.impl_files:
            ratio = score.test_files / score.impl_files if score.impl_files > 0 else 0
            gaps.append(f"GAP-TEST: Test coverage ratio is {ratio:.1%}, target is 100%")

        # Evidence gaps
        if score.acs_with_evidence < score.acs_total:
            missing = score.acs_total - score.acs_with_evidence
            gaps.append(f"GAP-EVID: {missing} of {score.acs_total} ACs lack evidence")

        # Correctness gaps
        if score.blocking_todos > 0:
            gaps.append(f"GAP-CORR: {score.blocking_todos} blocking TODOs found")

        # Build gaps
        if not score.build_passes:
            gaps.append("GAP-BUILD: Build or tests not passing")

        return gaps

    def _generate_recommendations(self, score: ComplianceScore) -> List[str]:
        """Generate recommendations for improving compliance."""
        recommendations = []

        # Prioritize by point value
        if score.implementation_score < 25:
            points_missing = 25 - score.implementation_score
            recommendations.append(
                f"HIGH: Implement remaining ACs (+{points_missing:.1f} potential points)"
            )

        if score.acceptance_criteria_score < 25:
            points_missing = 25 - score.acceptance_criteria_score
            recommendations.append(
                f"HIGH: Collect evidence for remaining ACs (+{points_missing:.1f} potential points)"
            )

        if score.test_coverage_score < 20:
            points_missing = 20 - score.test_coverage_score
            recommendations.append(
                f"MEDIUM: Increase test coverage (+{points_missing:.1f} potential points)"
            )

        if score.documentation_score < 15:
            points_missing = 15 - score.documentation_score
            recommendations.append(
                f"MEDIUM: Create missing documentation (+{points_missing:.1f} potential points)"
            )

        if score.correctness_score < 10:
            points_missing = 10 - score.correctness_score
            recommendations.append(
                f"MEDIUM: Resolve blocking TODOs (+{points_missing:.1f} potential points)"
            )

        if score.build_score < 5:
            recommendations.append(
                "LOW: Fix build/test failures (+5 potential points)"
            )

        return recommendations

    def generate_report(
        self,
        score: ComplianceScore,
        gaps: List[str],
        recommendations: List[str],
        epic_key: str,
    ) -> str:
        """
        Generate a markdown compliance report.

        Args:
            score: Compliance score
            gaps: Identified gaps
            recommendations: Improvement recommendations
            epic_key: EPIC key

        Returns:
            Markdown formatted report
        """
        status = "PASS" if score.passing else "FAIL"
        status_emoji = "[OK]" if score.passing else "[!!]"

        report = f"""# Compliance Report: {epic_key}

## Summary

**Score:** {score.total_score:.0f}/100 ({score.total_score:.0f}%)
**Status:** {status_emoji} {status}
**Threshold:** {self.PASSING_THRESHOLD}%

## Score Breakdown

| Category | Score | Max | Status |
|----------|-------|-----|--------|
| Documentation | {score.documentation_score:.1f} | 15 | {score.docs_complete}/{score.docs_total} docs |
| Implementation | {score.implementation_score:.1f} | 25 | {score.acs_implemented}/{score.acs_total} ACs |
| Test Coverage | {score.test_coverage_score:.1f} | 20 | {score.test_files}/{score.impl_files} ratio |
| Acceptance Criteria | {score.acceptance_criteria_score:.1f} | 25 | {score.acs_with_evidence}/{score.acs_total} with evidence |
| Correctness | {score.correctness_score:.1f} | 10 | {score.blocking_todos} blocking TODOs |
| Build | {score.build_score:.1f} | 5 | {'PASS' if score.build_passes else 'FAIL'} |
| **TOTAL** | **{score.total_score:.1f}** | **100** | **{status}** |

"""

        if gaps:
            report += "## Gaps Identified\n\n"
            for gap in gaps:
                report += f"- {gap}\n"
            report += "\n"

        if recommendations:
            report += "## Recommendations\n\n"
            for rec in recommendations:
                report += f"- {rec}\n"
            report += "\n"

        report += f"""---

*Generated by EPIC Executor v1.0*
*Date: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}*
"""

        return report
