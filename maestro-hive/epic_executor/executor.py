"""
EPIC Executor - Main Orchestrator

Executes EPIC work with compliance-ready output.
Inverse of epic-compliance: instead of auditing, this EXECUTES to achieve 95%+ score.

Usage:
    from epic_executor import EpicExecutor

    executor = EpicExecutor(jira_config, confluence_config)
    result = await executor.execute("MD-2385")
    print(f"Compliance Score: {result.compliance_score.total_score}%")
"""

import asyncio
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from .models import (
    ACEvidence,
    AcceptanceCriterion,
    ComplianceScore,
    ConvergenceMetrics,
    DocumentInfo,
    EpicInfo,
    ExecutionConfig,
    ExecutionPhase,
    ExecutionResult,
    Gap,
    GapSeverity,
    IterationRecord,
    PhaseResult,
)
from .jira.epic_updater import EpicUpdater, JiraConfig
from .confluence.publisher import ConfluencePublisher, ConfluenceConfig
from .phases.understanding import UnderstandingPhase
from .phases.documentation import DocumentationPhase
from .phases.implementation import ImplementationPhase
from .phases.testing import TestingPhase
from .phases.correctness import CorrectnessPhase
from .phases.build import BuildPhase
from .phases.evidence import EvidencePhase
from .phases.compliance import CompliancePhase


class EpicExecutor:
    """
    Main EPIC Executor class.

    Orchestrates the 9-phase execution process:
    1. Understanding - Parse EPIC, extract ACs
    2. Documentation - Generate Confluence docs
    3. Implementation - Execute via AI agents
    4. Testing - Generate tests
    5. Correctness - TODO audit
    6. Build - Build verification
    7. Evidence - AC evidence collection
    8. Compliance - Self-check
    9. Update - Update EPIC with results
    """

    def __init__(
        self,
        jira_config: JiraConfig,
        confluence_config: ConfluenceConfig,
        config: Optional[ExecutionConfig] = None,
    ):
        """
        Initialize the EPIC Executor.

        Args:
            jira_config: JIRA API configuration
            confluence_config: Confluence API configuration
            config: Optional execution configuration
        """
        self.jira_config = jira_config
        self.confluence_config = confluence_config
        self.config = config or self._default_config(jira_config, confluence_config)

        # Initialize phases
        self.understanding = UnderstandingPhase(jira_config)
        self.documentation = DocumentationPhase(confluence_config)
        self.implementation = ImplementationPhase(
            output_dir=self.config.output_dir,
            enable_ai_execution=self.config.enable_ai_execution,
        )
        self.testing = TestingPhase(output_dir=self.config.output_dir)
        self.correctness = CorrectnessPhase()
        self.build = BuildPhase()
        self.evidence = EvidencePhase()
        self.compliance = CompliancePhase()

        # JIRA updater for final phase
        self.epic_updater = EpicUpdater(jira_config)

        # Convergence tracking for gap-driven iteration
        self.convergence_metrics: Optional[ConvergenceMetrics] = None

    def _default_config(
        self,
        jira_config: JiraConfig,
        confluence_config: ConfluenceConfig,
    ) -> ExecutionConfig:
        """Create default execution config from JIRA/Confluence configs."""
        return ExecutionConfig(
            jira_base_url=jira_config.base_url,
            jira_email=jira_config.email,
            jira_api_token=jira_config.api_token,
            jira_project_key=jira_config.project_key,
            confluence_base_url=confluence_config.base_url,
            confluence_email=confluence_config.email,
            confluence_api_token=confluence_config.api_token,
            confluence_space_key=confluence_config.space_key,
            confluence_parent_page_id=confluence_config.parent_page_id,
        )

    async def execute(
        self,
        epic_key: str,
        max_iterations: int = 3,
    ) -> ExecutionResult:
        """
        Execute work for an EPIC.

        Args:
            epic_key: JIRA EPIC key (e.g., "MD-2385")
            max_iterations: Maximum retry iterations if < 95%

        Returns:
            ExecutionResult with full execution details
        """
        started_at = datetime.now()
        result = ExecutionResult(
            epic_key=epic_key,
            success=False,
            started_at=started_at,
        )

        # Initialize convergence tracking
        self.convergence_metrics = ConvergenceMetrics(
            target_score=self.config.min_compliance_score,
        )

        try:
            iteration = 0
            iteration_start = datetime.now()

            while iteration < max_iterations:
                iteration += 1
                result.iterations = iteration
                iteration_start = datetime.now()

                print(f"\n{'='*60}")
                print(f"EPIC Executor - {epic_key} - Iteration {iteration}/{max_iterations}")
                print(f"{'='*60}\n")

                # Execute all phases
                await self._execute_all_phases(result)

                # Get current score
                current_score = result.compliance_score.total_score if result.compliance_score else 0

                # Analyze gaps for this iteration
                gaps = await self._analyze_gaps(result)

                # Record iteration history
                iteration_record = IterationRecord(
                    iteration_number=iteration,
                    started_at=iteration_start,
                    completed_at=datetime.now(),
                    duration_seconds=(datetime.now() - iteration_start).total_seconds(),
                    compliance_score=current_score,
                    score_breakdown={
                        "documentation": result.compliance_score.documentation_score if result.compliance_score else 0,
                        "implementation": result.compliance_score.implementation_score if result.compliance_score else 0,
                        "testing": result.compliance_score.test_coverage_score if result.compliance_score else 0,
                        "evidence": result.compliance_score.acceptance_criteria_score if result.compliance_score else 0,
                        "correctness": result.compliance_score.correctness_score if result.compliance_score else 0,
                        "build": result.compliance_score.build_score if result.compliance_score else 0,
                    },
                    gaps_identified=gaps,
                    focus_areas=result.metadata.get("focus_areas", []) if result.metadata else [],
                    score_improvement=current_score - (
                        result.iteration_history[-1].compliance_score if result.iteration_history else 0
                    ),
                )
                result.iteration_history.append(iteration_record)

                # Check convergence
                converged = self.convergence_metrics.check_convergence(
                    new_score=current_score,
                    gaps_count=len(gaps),
                    max_iterations=max_iterations,
                )

                # Check if we passed
                if result.compliance_score and result.compliance_score.passing:
                    result.success = True
                    print(f"\n[PASS] Compliance score: {result.compliance_score.total_score:.0f}%")
                    print(f"[CONVERGENCE] {self.convergence_metrics.convergence_reason}")
                    break
                elif converged:
                    print(f"\n[CONVERGED] {self.convergence_metrics.convergence_reason}")
                    print(f"[FINAL SCORE] {current_score:.0f}%")
                    break
                else:
                    score = result.compliance_score.total_score if result.compliance_score else 0
                    print(f"\n[RETRY] Score: {score:.0f}% < 95% - iterating...")
                    print(f"[GAPS] {len(gaps)} gaps identified")

                    if iteration < max_iterations:
                        # Analyze gaps and prepare for next iteration
                        await self._prepare_next_iteration(result, gaps)

            # Phase 9: Update EPIC with results
            await self._update_epic(result)

        except Exception as e:
            result.errors.append(f"Execution failed: {str(e)}")
            result.success = False

        # Finalize result
        result.completed_at = datetime.now()
        result.duration_seconds = (result.completed_at - result.started_at).total_seconds()

        # Generate execution report
        report_path = await self._generate_report(result)
        result.execution_report_path = report_path

        return result

    async def _execute_all_phases(self, result: ExecutionResult) -> None:
        """Execute all 8 phases."""

        # Phase 1: Understanding
        print("\n[Phase 1/8] Understanding EPIC...")
        phase_result, understanding_result = await self.understanding.execute(
            epic_key=result.epic_key,
            create_child_tasks=True,
        )
        result.phase_results[ExecutionPhase.UNDERSTANDING] = phase_result

        if not understanding_result:
            result.errors.append("Understanding phase failed")
            return

        result.epic_info = understanding_result.epic_info
        result.acceptance_criteria = understanding_result.acceptance_criteria
        result.child_tasks_created = list(understanding_result.child_tasks_created.values())

        print(f"    - Extracted {len(result.acceptance_criteria)} ACs")
        print(f"    - Requirement type: {understanding_result.requirement_type}")
        print(f"    - Team: {', '.join(understanding_result.recommended_team_composition)}")

        # Phase 2: Documentation
        print("\n[Phase 2/8] Generating documentation...")
        phase_result, doc_result = await self.documentation.execute(
            epic_info=understanding_result.epic_info,
            implementation_context={
                "requirement_type": understanding_result.requirement_type,
                "team_composition": understanding_result.recommended_team_composition,
            },
        )
        result.phase_results[ExecutionPhase.DOCUMENTATION] = phase_result

        if doc_result:
            result.documents = doc_result.documents
            print(f"    - Created {len(doc_result.documents)} documents")
            print(f"    - Points: {doc_result.points_earned:.1f}/15")

        # Phase 3: Implementation
        print("\n[Phase 3/8] Implementing acceptance criteria...")
        phase_result, impl_result = await self.implementation.execute(
            epic_info=understanding_result.epic_info,
            team_composition=understanding_result.recommended_team_composition,
            requirement_type=understanding_result.requirement_type,
        )
        result.phase_results[ExecutionPhase.IMPLEMENTATION] = phase_result

        if impl_result:
            result.implementation_files = impl_result.implementation_files
            implemented_count = sum(
                1 for s in impl_result.acs_implemented.values()
                if s.value in ["implemented", "tested", "verified"]
            )
            print(f"    - Implemented {implemented_count}/{len(result.acceptance_criteria)} ACs")
            print(f"    - Created {len(impl_result.implementation_files)} files")
            print(f"    - Points: {impl_result.points_earned:.1f}/25")

        # Phase 4: Testing
        print("\n[Phase 4/8] Generating tests...")
        phase_result, test_result = await self.testing.execute(
            epic_info=understanding_result.epic_info,
            implementation_files=result.implementation_files,
        )
        result.phase_results[ExecutionPhase.TESTING] = phase_result

        if test_result:
            result.test_files = test_result.test_files
            print(f"    - Generated {len(test_result.test_files)} test files")
            print(f"    - Coverage ratio: {test_result.coverage_ratio:.1%}")
            print(f"    - Points: {test_result.points_earned:.1f}/20")

        # Phase 5: Correctness
        print("\n[Phase 5/8] Checking correctness...")
        phase_result, correct_result = await self.correctness.execute(
            implementation_files=result.implementation_files,
            test_files=result.test_files,
        )
        result.phase_results[ExecutionPhase.CORRECTNESS] = phase_result

        blocking_todos = 0
        if correct_result:
            blocking_todos = correct_result.blocking_count
            result.blocking_todos = blocking_todos
            print(f"    - Found {len(correct_result.todos_found)} TODOs")
            print(f"    - Blocking: {blocking_todos}")
            print(f"    - Points: {correct_result.points_earned:.1f}/10")

        # Phase 6: Build
        print("\n[Phase 6/8] Verifying build...")
        phase_result, build_result = await self.build.execute(
            implementation_files=result.implementation_files,
            test_files=result.test_files,
        )
        result.phase_results[ExecutionPhase.BUILD] = phase_result

        build_passed = False
        if build_result:
            build_passed = build_result.build_passed and build_result.tests_passed
            result.build_passed = build_passed
            print(f"    - Build: {'PASS' if build_result.build_passed else 'FAIL'}")
            print(f"    - Tests: {'PASS' if build_result.tests_passed else 'FAIL'}")
            print(f"    - Points: {build_result.points_earned:.1f}/5")

        # Phase 7: Evidence
        print("\n[Phase 7/8] Collecting evidence...")
        phase_result, evidence_result = await self.evidence.execute(
            epic_info=understanding_result.epic_info,
            implementation_files=result.implementation_files,
            test_files=result.test_files,
            documents=result.documents,
        )
        result.phase_results[ExecutionPhase.EVIDENCE] = phase_result

        if evidence_result:
            result.evidence = evidence_result.evidence_collected
            print(f"    - Collected evidence for {evidence_result.acs_with_evidence}/{len(result.acceptance_criteria)} ACs")
            print(f"    - Verified: {evidence_result.acs_verified}")
            print(f"    - Points: {evidence_result.points_earned:.1f}/25")

        # Phase 8: Compliance
        print("\n[Phase 8/8] Calculating compliance score...")
        phase_result, compliance_result = await self.compliance.execute(
            documents=result.documents,
            acceptance_criteria=result.acceptance_criteria,
            evidence=result.evidence,
            implementation_files=result.implementation_files,
            test_files=result.test_files,
            blocking_todos=blocking_todos,
            build_passes=build_passed,
        )
        result.phase_results[ExecutionPhase.COMPLIANCE] = phase_result

        if compliance_result:
            result.compliance_score = compliance_result.compliance_score
            score = compliance_result.compliance_score
            print(f"\n    {'='*40}")
            print(f"    COMPLIANCE SCORE: {score.total_score:.0f}/100")
            print(f"    {'='*40}")
            print(f"    Documentation:  {score.documentation_score:.1f}/15")
            print(f"    Implementation: {score.implementation_score:.1f}/25")
            print(f"    Test Coverage:  {score.test_coverage_score:.1f}/20")
            print(f"    AC Evidence:    {score.acceptance_criteria_score:.1f}/25")
            print(f"    Correctness:    {score.correctness_score:.1f}/10")
            print(f"    Build:          {score.build_score:.1f}/5")
            print(f"    {'='*40}")
            print(f"    Status: {'PASS' if score.passing else 'FAIL'}")

            if compliance_result.gaps:
                print("\n    Gaps:")
                for gap in compliance_result.gaps[:5]:
                    print(f"    - {gap}")

    async def _analyze_gaps(self, result: ExecutionResult) -> List[Gap]:
        """
        Analyze execution result to identify gaps.

        Returns:
            List of Gap objects with severity and impact scoring.
        """
        gaps: List[Gap] = []

        if not result.compliance_score:
            return gaps

        score = result.compliance_score

        # 1. Documentation gaps (15 points max)
        if score.documentation_score < 12:
            missing_docs = []
            required_doc_types = ["technical_design", "runbook", "api_documentation",
                                  "adr", "configuration_guide", "monitoring_guide"]
            existing_types = {doc.doc_type for doc in result.documents}
            missing_docs = [dt for dt in required_doc_types if dt not in existing_types]

            if missing_docs:
                impact = (12 - score.documentation_score)
                gaps.append(Gap(
                    category="documentation",
                    description=f"Missing documentation: {', '.join(missing_docs)}",
                    severity=GapSeverity.HIGH if len(missing_docs) > 2 else GapSeverity.MEDIUM,
                    impact_points=impact,
                    remediation=f"Create missing documents: {', '.join(missing_docs)}",
                    related_items=missing_docs,
                ))

        # 2. Implementation gaps (25 points max)
        if score.implementation_score < 20:
            unimplemented_acs = []
            for ac in result.acceptance_criteria:
                ac_has_impl = any(
                    ac.id.lower() in f.lower() or
                    any(word.lower() in f.lower() for word in ac.description.split()[:3])
                    for f in result.implementation_files
                )
                if not ac_has_impl:
                    unimplemented_acs.append(ac.id)

            if unimplemented_acs:
                impact = (20 - score.implementation_score)
                gaps.append(Gap(
                    category="implementation",
                    description=f"Unimplemented ACs: {len(unimplemented_acs)} remaining",
                    severity=GapSeverity.CRITICAL if len(unimplemented_acs) > 2 else GapSeverity.HIGH,
                    impact_points=impact,
                    remediation=f"Implement acceptance criteria: {', '.join(unimplemented_acs[:5])}",
                    related_items=unimplemented_acs,
                ))

        # 3. Test coverage gaps (20 points max)
        if score.test_coverage_score < 16:
            untested_files = []
            for impl_file in result.implementation_files:
                impl_name = Path(impl_file).stem
                has_test = any(
                    impl_name in test_file or f"test_{impl_name}" in test_file
                    for test_file in result.test_files
                )
                if not has_test:
                    untested_files.append(impl_file)

            if untested_files:
                impact = (16 - score.test_coverage_score)
                gaps.append(Gap(
                    category="testing",
                    description=f"Files without tests: {len(untested_files)}",
                    severity=GapSeverity.HIGH if len(untested_files) > 3 else GapSeverity.MEDIUM,
                    impact_points=impact,
                    remediation=f"Add tests for: {', '.join(untested_files[:5])}",
                    related_items=untested_files,
                ))

        # 4. Evidence gaps (25 points max)
        if score.acceptance_criteria_score < 20:
            acs_without_evidence = []
            ac_ids_with_evidence = {e.ac_id for e in (result.evidence or [])}
            for ac in result.acceptance_criteria:
                if ac.id not in ac_ids_with_evidence:
                    acs_without_evidence.append(ac.id)

            if acs_without_evidence:
                impact = (20 - score.acceptance_criteria_score)
                gaps.append(Gap(
                    category="evidence",
                    description=f"ACs without evidence: {len(acs_without_evidence)}",
                    severity=GapSeverity.HIGH if len(acs_without_evidence) > 2 else GapSeverity.MEDIUM,
                    impact_points=impact,
                    remediation=f"Collect evidence for: {', '.join(acs_without_evidence[:5])}",
                    related_items=acs_without_evidence,
                ))

        # 5. Correctness gaps (10 points max)
        if score.correctness_score < 8:
            if result.blocking_todos > 0:
                impact = (8 - score.correctness_score)
                gaps.append(Gap(
                    category="correctness",
                    description=f"Blocking TODOs: {result.blocking_todos}",
                    severity=GapSeverity.CRITICAL if result.blocking_todos > 2 else GapSeverity.HIGH,
                    impact_points=impact,
                    remediation="Resolve blocking TODOs before completion",
                    related_items=[f"TODO_{i}" for i in range(result.blocking_todos)],
                ))

        # 6. Build gaps (5 points max)
        if score.build_score < 5:
            gaps.append(Gap(
                category="build",
                description="Build or tests failing",
                severity=GapSeverity.CRITICAL,
                impact_points=5,
                remediation="Fix build errors and failing tests",
                related_items=[],
            ))

        # Sort by impact (highest first) for prioritization
        gaps.sort(key=lambda g: g.impact_points, reverse=True)

        return gaps

    async def _prepare_next_iteration(
        self,
        result: ExecutionResult,
        gaps: Optional[List[Gap]] = None,
    ) -> None:
        """
        Prepare for next iteration by analyzing gaps and adjusting focus.

        Analyzes the current execution result to identify:
        1. Which ACs failed or lack evidence
        2. Missing documentation
        3. Insufficient test coverage
        4. Blocking TODOs that need resolution

        Updates the execution state to focus on gaps in the next iteration.

        Args:
            result: Current execution result
            gaps: Pre-analyzed gaps (optional, will analyze if not provided)
        """
        print("\n[Iteration Prep] Analyzing gaps...")

        # Analyze gaps if not provided
        if gaps is None:
            gaps = await self._analyze_gaps(result)

        # Initialize metadata
        result.metadata = result.metadata or {}

        # Determine focus areas from gaps
        focus_areas = list(set(g.category for g in gaps))

        # Store gap details by category
        gap_details: Dict[str, List[str]] = {}
        for gap in gaps:
            if gap.category not in gap_details:
                gap_details[gap.category] = []
            gap_details[gap.category].extend(gap.related_items)

        # Log gaps by severity
        critical_gaps = [g for g in gaps if g.severity == GapSeverity.CRITICAL]
        high_gaps = [g for g in gaps if g.severity == GapSeverity.HIGH]
        medium_gaps = [g for g in gaps if g.severity == GapSeverity.MEDIUM]

        if critical_gaps:
            print(f"    [CRITICAL] {len(critical_gaps)} critical gaps:")
            for g in critical_gaps:
                print(f"        - {g.description} ({g.impact_points:.1f} pts)")

        if high_gaps:
            print(f"    [HIGH] {len(high_gaps)} high-priority gaps:")
            for g in high_gaps[:3]:  # Show top 3
                print(f"        - {g.description} ({g.impact_points:.1f} pts)")

        if medium_gaps:
            print(f"    [MEDIUM] {len(medium_gaps)} medium-priority gaps")

        # Store iteration feedback in metadata
        result.metadata["iteration_gaps"] = [g.description for g in gaps]
        result.metadata["focus_areas"] = focus_areas

        # Store specific items for focused iteration
        if "documentation" in focus_areas:
            result.metadata["missing_docs"] = gap_details.get("documentation", [])

        if "implementation" in focus_areas:
            result.metadata["focus_acs"] = gap_details.get("implementation", [])

        if "testing" in focus_areas:
            result.metadata["untested_files"] = gap_details.get("testing", [])[:10]

        if "evidence" in focus_areas:
            result.metadata["acs_need_evidence"] = gap_details.get("evidence", [])

        # Update phases with focus information for targeted iteration
        if "documentation" in focus_areas and hasattr(self.documentation, 'set_focus'):
            self.documentation.set_focus(result.metadata.get("missing_docs", []))

        if "implementation" in focus_areas and hasattr(self.implementation, 'set_focus_acs'):
            self.implementation.set_focus_acs(result.metadata.get("focus_acs", []))

        if "testing" in focus_areas and hasattr(self.testing, 'set_focus_files'):
            self.testing.set_focus_files(result.metadata.get("untested_files", []))

        # Print summary
        total_impact = sum(g.impact_points for g in gaps)
        print(f"\n    Gaps identified: {len(gaps)}")
        print(f"    Total impact: {total_impact:.1f} points")
        print(f"    Focus areas: {', '.join(focus_areas) or 'None'}")

        # Add convergence info if available
        if self.convergence_metrics:
            print(f"\n    [CONVERGENCE]")
            print(f"        Iterations: {self.convergence_metrics.iterations_completed}")
            print(f"        Current score: {self.convergence_metrics.current_score:.1f}%")
            print(f"        Target: {self.convergence_metrics.target_score}%")

        # Brief pause to allow any async cleanup
        await asyncio.sleep(0.1)

    async def _update_epic(self, result: ExecutionResult) -> None:
        """Phase 9: Update EPIC with execution results."""
        print("\n[Phase 9] Updating EPIC...")

        if not result.epic_info:
            print("    - Skipped: No EPIC info available")
            return

        try:
            # Get Confluence links
            confluence_links = [
                doc.confluence_url
                for doc in result.documents
                if doc.confluence_url
            ]

            # Build score breakdown for EPIC update
            breakdown = {}
            if result.compliance_score:
                score = result.compliance_score
                breakdown = {
                    "documentation": {"score": score.documentation_score, "max": 15, "status": f"{score.docs_complete}/{score.docs_total} docs"},
                    "implementation": {"score": score.implementation_score, "max": 25, "status": f"{score.acs_implemented}/{score.acs_total} ACs"},
                    "test_coverage": {"score": score.test_coverage_score, "max": 20, "status": f"{score.test_files}/{score.impl_files} ratio"},
                    "acceptance_criteria": {"score": score.acceptance_criteria_score, "max": 25, "status": f"{score.acs_with_evidence}/{score.acs_total} with evidence"},
                    "correctness": {"score": score.correctness_score, "max": 10, "status": f"{score.blocking_todos} blocking"},
                    "build": {"score": score.build_score, "max": 5, "status": "PASS" if score.build_passes else "FAIL"},
                }

            # Update EPIC description
            await self.epic_updater.update_epic_description(
                epic_key=result.epic_key,
                original_description=result.epic_info.description,
                compliance_score=result.compliance_score.total_score if result.compliance_score else 0,
                breakdown=breakdown,
                gaps=[],
                child_tasks=result.child_tasks_created,
                implementation_files=result.implementation_files[:10],
                confluence_links=confluence_links,
            )
            result.epic_updated = True
            print("    - Updated EPIC description")

            # Post execution comment
            await self.epic_updater.post_execution_comment(
                epic_key=result.epic_key,
                result=result,
                confluence_links=confluence_links,
            )
            print("    - Posted execution comment")

            # Link Confluence pages
            for doc in result.documents:
                if doc.confluence_url:
                    await self.epic_updater.link_confluence_page(
                        epic_key=result.epic_key,
                        page_url=doc.confluence_url,
                        title=doc.title,
                    )
            result.confluence_pages_linked = True
            print(f"    - Linked {len(confluence_links)} Confluence pages")

        except Exception as e:
            result.warnings.append(f"Failed to update EPIC: {str(e)}")
            print(f"    - Error: {str(e)}")

    async def _generate_report(self, result: ExecutionResult) -> str:
        """Generate execution report."""
        report_dir = Path(self.config.output_dir)
        report_path = report_dir / f"{result.epic_key}-execution-report.md"

        # Use compliance phase to generate report
        if result.compliance_score:
            compliance_result = await self.compliance.execute(
                documents=result.documents,
                acceptance_criteria=result.acceptance_criteria,
                evidence=result.evidence,
                implementation_files=result.implementation_files,
                test_files=result.test_files,
                blocking_todos=result.blocking_todos,
                build_passes=result.build_passed,
            )

            if compliance_result[1]:
                report_content = self.compliance.generate_report(
                    score=result.compliance_score,
                    gaps=compliance_result[1].gaps,
                    recommendations=compliance_result[1].recommendations,
                    epic_key=result.epic_key,
                )
            else:
                report_content = self._basic_report(result)
        else:
            report_content = self._basic_report(result)

        # Write report
        try:
            report_path.write_text(report_content)
            print(f"\n[Report] Saved to: {report_path}")
        except Exception as e:
            print(f"\n[Report] Failed to save: {str(e)}")

        return str(report_path)

    def _basic_report(self, result: ExecutionResult) -> str:
        """Generate a basic report when compliance check didn't run."""
        return f"""# Execution Report: {result.epic_key}

## Summary

- **Success:** {result.success}
- **Duration:** {result.duration_seconds:.1f}s
- **Iterations:** {result.iterations}

## Phases Completed

{chr(10).join(f"- {phase.value}: {'PASS' if pr.success else 'FAIL'}" for phase, pr in result.phase_results.items())}

## Artifacts

- Documents: {len(result.documents)}
- Implementation files: {len(result.implementation_files)}
- Test files: {len(result.test_files)}

## Errors

{chr(10).join(f"- {e}" for e in result.errors) if result.errors else "None"}

---
*Generated by EPIC Executor v1.0*
"""


async def execute_epic(
    epic_key: str,
    jira_base_url: str,
    jira_email: str,
    jira_api_token: str,
    confluence_base_url: str,
    confluence_email: str,
    confluence_api_token: str,
    confluence_space_key: str,
    project_key: str = "MD",
    max_iterations: int = 3,
) -> ExecutionResult:
    """
    Convenience function to execute an EPIC.

    Args:
        epic_key: JIRA EPIC key
        jira_base_url: JIRA base URL
        jira_email: JIRA email
        jira_api_token: JIRA API token
        confluence_base_url: Confluence base URL
        confluence_email: Confluence email
        confluence_api_token: Confluence API token
        confluence_space_key: Confluence space key
        project_key: JIRA project key
        max_iterations: Max retry iterations

    Returns:
        ExecutionResult
    """
    jira_config = JiraConfig(
        base_url=jira_base_url,
        email=jira_email,
        api_token=jira_api_token,
        project_key=project_key,
    )

    confluence_config = ConfluenceConfig(
        base_url=confluence_base_url,
        email=confluence_email,
        api_token=confluence_api_token,
        space_key=confluence_space_key,
    )

    executor = EpicExecutor(jira_config, confluence_config)
    return await executor.execute(epic_key, max_iterations)
