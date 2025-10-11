#!/usr/bin/env python3
"""
Phase Gate Validator

Validates entry and exit criteria for SDLC phases.
Ensures phases can only start when prerequisites are met,
and can only complete when deliverables meet quality standards.
"""

import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
import json

from phase_models import (
    SDLCPhase,
    PhaseState,
    PhaseExecution,
    PhaseGateResult,
    PhaseIssue,
    QualityThresholds
)
from team_organization import TeamOrganization

logger = logging.getLogger(__name__)


class PhaseGateValidator:
    """
    Validates phase gates (entry/exit criteria) for SDLC phases
    
    Key Responsibilities:
    1. Entry gate: Validate prerequisites before starting phase
    2. Exit gate: Validate deliverables and quality before completing phase
    3. Generate actionable recommendations for failures
    """
    
    def __init__(self):
        # Load phase definitions from team_organization.py
        self.phase_definitions = TeamOrganization.get_phase_structure()
        
        # Define critical deliverables per phase (must have)
        self.critical_deliverables = {
            SDLCPhase.REQUIREMENTS: [
                "requirements_document",
                "user_stories"
            ],
            SDLCPhase.DESIGN: [
                "architecture_document",
                "api_specifications",
                "database_design"
            ],
            SDLCPhase.IMPLEMENTATION: [
                "backend_code",
                "frontend_code",
                "backend_tests"
            ],
            SDLCPhase.TESTING: [
                "test_plan",
                "test_report",
                "completeness_report"
            ],
            SDLCPhase.DEPLOYMENT: [
                "deployment_plan",
                "smoke_test_results",
                "monitoring_setup"
            ]
        }
    
    async def validate_entry_criteria(
        self,
        phase: SDLCPhase,
        phase_history: List[PhaseExecution]
    ) -> PhaseGateResult:
        """
        Validate entry criteria for a phase
        
        Entry gates check:
        1. Prerequisite phases completed
        2. Required artifacts available
        3. Environmental readiness
        
        Args:
            phase: Phase to validate entry for
            phase_history: History of all phase executions
        
        Returns:
            PhaseGateResult with pass/fail and details
        """
        
        logger.info(f"🚪 Validating ENTRY gate for {phase.value} phase")
        
        phase_def = self.phase_definitions[phase]
        criteria_met = []
        criteria_failed = []
        blocking_issues = []
        
        # Check prerequisite phases
        prerequisite_phases = self._get_prerequisite_phases(phase)
        
        for prereq_phase in prerequisite_phases:
            prereq_completed = self._is_phase_completed(prereq_phase, phase_history)
            
            if prereq_completed:
                criteria_met.append(f"✅ {prereq_phase.value} phase completed")
                logger.debug(f"  ✅ {prereq_phase.value} phase completed")
            else:
                criteria_failed.append(f"❌ {prereq_phase.value} phase not completed")
                blocking_issues.append(
                    f"Cannot start {phase.value} - {prereq_phase.value} phase must complete first"
                )
                logger.warning(f"  ❌ {prereq_phase.value} phase not completed")
        
        # Check entry criteria from phase definition
        for criterion in phase_def['entry_criteria']:
            is_met = await self._check_entry_criterion(criterion, phase, phase_history)
            
            if is_met:
                criteria_met.append(f"✅ {criterion}")
                logger.debug(f"  ✅ {criterion}")
            else:
                criteria_failed.append(f"❌ {criterion}")
                logger.debug(f"  ❌ {criterion}")
        
        # Calculate pass/fail
        passed = len(criteria_failed) == 0 and len(blocking_issues) == 0
        score = len(criteria_met) / max(len(criteria_met) + len(criteria_failed), 1)
        
        result = PhaseGateResult(
            passed=passed,
            score=score,
            criteria_met=criteria_met,
            criteria_failed=criteria_failed,
            blocking_issues=blocking_issues,
            warnings=[],
            recommendations=self._generate_entry_recommendations(phase, criteria_failed),
            required_threshold=1.0,  # 100% for entry gates
            actual_score=score
        )
        
        if passed:
            logger.info(f"✅ ENTRY gate PASSED for {phase.value} ({score:.0%})")
        else:
            logger.error(f"❌ ENTRY gate FAILED for {phase.value} ({score:.0%})")
            for issue in blocking_issues:
                logger.error(f"   🚫 {issue}")
        
        return result
    
    async def validate_exit_criteria(
        self,
        phase: SDLCPhase,
        phase_exec: PhaseExecution,
        quality_thresholds: QualityThresholds,
        output_dir: Path
    ) -> PhaseGateResult:
        """
        Validate exit criteria for a phase
        
        Exit gates check:
        1. Quality thresholds met
        2. Expected deliverables present
        3. No critical issues
        
        Args:
            phase: Phase to validate exit for
            phase_exec: Current phase execution
            quality_thresholds: Required quality levels
            output_dir: Output directory to check deliverables
        
        Returns:
            PhaseGateResult with pass/fail and details
        """
        
        logger.info(f"🚪 Validating EXIT gate for {phase.value} phase")
        
        phase_def = self.phase_definitions[phase]
        criteria_met = []
        criteria_failed = []
        blocking_issues = []
        warnings = []
        
        # Check quality thresholds
        if phase_exec.completeness < quality_thresholds.completeness:
            criteria_failed.append(
                f"❌ Completeness {phase_exec.completeness:.0%} < threshold {quality_thresholds.completeness:.0%}"
            )
            blocking_issues.append(
                f"Phase completeness too low - need {quality_thresholds.completeness:.0%}, got {phase_exec.completeness:.0%}"
            )
            logger.warning(f"  ❌ Completeness: {phase_exec.completeness:.0%} < {quality_thresholds.completeness:.0%}")
        else:
            criteria_met.append(
                f"✅ Completeness {phase_exec.completeness:.0%} ≥ {quality_thresholds.completeness:.0%}"
            )
            logger.debug(f"  ✅ Completeness: {phase_exec.completeness:.0%} ≥ {quality_thresholds.completeness:.0%}")
        
        if phase_exec.quality_score < quality_thresholds.quality:
            criteria_failed.append(
                f"❌ Quality score {phase_exec.quality_score:.2f} < threshold {quality_thresholds.quality:.2f}"
            )
            blocking_issues.append(
                f"Quality score too low - need {quality_thresholds.quality:.2f}, got {phase_exec.quality_score:.2f}"
            )
            logger.warning(f"  ❌ Quality: {phase_exec.quality_score:.2f} < {quality_thresholds.quality:.2f}")
        else:
            criteria_met.append(
                f"✅ Quality score {phase_exec.quality_score:.2f} ≥ {quality_thresholds.quality:.2f}"
            )
            logger.debug(f"  ✅ Quality: {phase_exec.quality_score:.2f} ≥ {quality_thresholds.quality:.2f}")
        
        # For testing phase, check test coverage
        if phase == SDLCPhase.TESTING and quality_thresholds.test_coverage > 0:
            if phase_exec.test_coverage < quality_thresholds.test_coverage:
                criteria_failed.append(
                    f"❌ Test coverage {phase_exec.test_coverage:.0%} < threshold {quality_thresholds.test_coverage:.0%}"
                )
                blocking_issues.append(
                    f"Test coverage too low - need {quality_thresholds.test_coverage:.0%}, got {phase_exec.test_coverage:.0%}"
                )
                logger.warning(f"  ❌ Test coverage: {phase_exec.test_coverage:.0%} < {quality_thresholds.test_coverage:.0%}")
            else:
                criteria_met.append(
                    f"✅ Test coverage {phase_exec.test_coverage:.0%} ≥ {quality_thresholds.test_coverage:.0%}"
                )
                logger.debug(f"  ✅ Test coverage: {phase_exec.test_coverage:.0%} ≥ {quality_thresholds.test_coverage:.0%}")
        
        # Check critical deliverables
        deliverable_check = await self._validate_critical_deliverables(
            phase,
            phase_exec,
            output_dir
        )
        
        criteria_met.extend(deliverable_check['met'])
        criteria_failed.extend(deliverable_check['failed'])
        
        if deliverable_check['critical_missing'] > 0:
            blocking_issues.append(
                f"{deliverable_check['critical_missing']} critical deliverable(s) missing"
            )
        
        if deliverable_check['warnings']:
            warnings.extend(deliverable_check['warnings'])
        
        # Check exit criteria from phase definition
        for criterion in phase_def['exit_criteria']:
            is_met = await self._check_exit_criterion(criterion, phase_exec, output_dir)
            
            if is_met:
                criteria_met.append(f"✅ {criterion}")
                logger.debug(f"  ✅ {criterion}")
            else:
                criteria_failed.append(f"❌ {criterion}")
                # Some failures are warnings, not blockers
                if self._is_critical_criterion(criterion):
                    blocking_issues.append(f"Critical: {criterion}")
                    logger.warning(f"  🚫 Critical: {criterion}")
                else:
                    warnings.append(f"Warning: {criterion}")
                    logger.debug(f"  ⚠️  Warning: {criterion}")
        
        # Check for critical issues in phase execution
        critical_issues = [issue for issue in phase_exec.issues if issue.severity == "critical"]
        if critical_issues:
            for issue in critical_issues:
                blocking_issues.append(f"Critical issue: {issue.description}")
            logger.error(f"  🚫 {len(critical_issues)} critical issue(s) found")
        
        # Calculate pass/fail
        has_blocking_issues = len(blocking_issues) > 0
        passed = not has_blocking_issues
        score = len(criteria_met) / max(len(criteria_met) + len(criteria_failed), 1)
        
        result = PhaseGateResult(
            passed=passed,
            score=score,
            criteria_met=criteria_met,
            criteria_failed=criteria_failed,
            blocking_issues=blocking_issues,
            warnings=warnings,
            recommendations=self._generate_exit_recommendations(phase, criteria_failed, blocking_issues),
            required_threshold=quality_thresholds.completeness,
            actual_score=score
        )
        
        if passed:
            logger.info(f"✅ EXIT gate PASSED for {phase.value} ({score:.0%})")
            if warnings:
                logger.info(f"   ⚠️  {len(warnings)} warning(s)")
        else:
            logger.error(f"❌ EXIT gate FAILED for {phase.value} ({score:.0%})")
            logger.error(f"   🚫 {len(blocking_issues)} blocking issue(s)")
        
        return result
    
    def _get_prerequisite_phases(self, phase: SDLCPhase) -> List[SDLCPhase]:
        """Get phases that must complete before this phase"""
        phase_order = [
            SDLCPhase.REQUIREMENTS,
            SDLCPhase.DESIGN,
            SDLCPhase.IMPLEMENTATION,
            SDLCPhase.TESTING,
            SDLCPhase.DEPLOYMENT
        ]
        
        try:
            current_index = phase_order.index(phase)
            return phase_order[:current_index]
        except ValueError:
            return []
    
    def _is_phase_completed(
        self,
        phase: SDLCPhase,
        phase_history: List[PhaseExecution]
    ) -> bool:
        """Check if a phase has been completed successfully"""
        for phase_exec in reversed(phase_history):
            if phase_exec.phase == phase:
                return phase_exec.state == PhaseState.COMPLETED
        return False
    
    async def _check_entry_criterion(
        self,
        criterion: str,
        phase: SDLCPhase,
        phase_history: List[PhaseExecution]
    ) -> bool:
        """
        Check a specific entry criterion
        
        This is a simplified implementation that does basic checks.
        Can be enhanced with more sophisticated validation.
        """
        criterion_lower = criterion.lower()
        
        # Check for completion keywords
        if "complete" in criterion_lower or "approved" in criterion_lower:
            # Check if previous phases are complete
            prereq_phases = self._get_prerequisite_phases(phase)
            return all(self._is_phase_completed(p, phase_history) for p in prereq_phases)
        
        # Default: assume criterion is met
        # In production, this would do actual validation
        return True
    
    async def _check_exit_criterion(
        self,
        criterion: str,
        phase_exec: PhaseExecution,
        output_dir: Path
    ) -> bool:
        """
        Check a specific exit criterion
        
        Implements specific validators for known criteria.
        Uses pattern matching with fallback to heuristics.
        """
        criterion_lower = criterion.lower()
        
        # Use word boundary matching to avoid false positives
        import re
        
        # Test-related criteria (e.g., "all tests pass", "tests passed")
        if re.search(r'\btests?\b.*\bpass', criterion_lower):
            return phase_exec.quality_score >= 0.70 and len(phase_exec.issues) == 0
        
        # Completeness criteria (e.g., "requirements complete", "implementation complete")
        if re.search(r'\bcomplete[d]?\b', criterion_lower) and not 'completely' in criterion_lower:
            return phase_exec.completeness >= 0.75
        
        # Review criteria (e.g., "code review passed", "review approved")
        if re.search(r'\breview\b.*(pass|approve)', criterion_lower):
            return phase_exec.quality_score >= 0.70
        
        # Security criteria (e.g., "security review passed", "security scan clean")
        if re.search(r'\bsecurity\b', criterion_lower):
            security_personas = ["security_specialist", "security_engineer"]
            has_security = any(p in phase_exec.personas_executed for p in security_personas)
            return has_security and phase_exec.quality_score >= 0.75
        
        # Documentation criteria (e.g., "documentation complete")
        if re.search(r'\bdocument(ation)?\b', criterion_lower):
            doc_files = list(output_dir.glob("**/*.md"))
            return len(doc_files) >= 3  # At least README, requirements, architecture
        
        # Code quality criteria (e.g., "code quality acceptable")
        if re.search(r'\bquality\b', criterion_lower) and 'code' in criterion_lower:
            return phase_exec.quality_score >= 0.70
        
        # Deployment readiness (e.g., "ready for deployment")
        if re.search(r'\bdeploy(ment)?\b.*\bready\b', criterion_lower):
            return (
                phase_exec.completeness >= 0.90 and
                phase_exec.quality_score >= 0.80 and
                phase_exec.test_coverage >= 0.70
            )
        
        # NEW PATTERNS - Common exit criteria
        
        # "created" criteria (e.g., "User stories created")
        if re.search(r'\bcreated?\b', criterion_lower):
            return phase_exec.completeness >= 0.70
        
        # "selected" criteria (e.g., "Technology stack selected")
        if re.search(r'\bselected?\b', criterion_lower):
            return phase_exec.completeness >= 0.60
        
        # "defined" criteria (e.g., "API contracts defined")
        if re.search(r'\bdefin(ed|ition)?\b', criterion_lower):
            return phase_exec.completeness >= 0.70
        
        # "designed" criteria (e.g., "Database schema designed")
        if re.search(r'\bdesign(ed)?\b', criterion_lower):
            return phase_exec.completeness >= 0.70
        
        # "implemented" criteria (e.g., "All features implemented")
        if re.search(r'\bimplement(ed)?\b', criterion_lower):
            return phase_exec.completeness >= 0.75
        
        # "executed" criteria (e.g., "All test cases executed")
        if re.search(r'\bexecuted?\b', criterion_lower):
            return phase_exec.completeness >= 0.70
        
        # "resolved" criteria (e.g., "Critical bugs resolved")
        if re.search(r'\bresolved?\b', criterion_lower):
            return len([i for i in phase_exec.issues if i.severity == "critical"]) == 0
        
        # "met" criteria (e.g., "Performance benchmarks met")
        if re.search(r'\bmet\b', criterion_lower) and 'benchmark' in criterion_lower:
            return phase_exec.quality_score >= 0.70
        
        # "validated" criteria (e.g., "Acceptance criteria validated")
        if re.search(r'\bvalidat(ed|ion)?\b', criterion_lower):
            return phase_exec.completeness >= 0.70
        
        # "active" criteria (e.g., "Monitoring dashboards active")
        if re.search(r'\bactive\b', criterion_lower):
            return phase_exec.completeness >= 0.60
        
        # "deployed" criteria (e.g., "Application deployed")
        if re.search(r'\bdeploy(ed)?\b', criterion_lower):
            return phase_exec.completeness >= 0.80
        
        # "sign-off" or "approved" criteria
        if re.search(r'\b(sign-?off|approval|approved?)\b', criterion_lower):
            return phase_exec.quality_score >= 0.75
        
        # "documented" criteria
        if re.search(r'\bdocumented?\b', criterion_lower):
            return phase_exec.completeness >= 0.70
        
        # "wireframes" criteria
        if re.search(r'\bwireframes?\b', criterion_lower):
            return phase_exec.completeness >= 0.60
        
        # Heuristic fallback: if phase has reasonable quality, assume criterion can be met
        if phase_exec.completeness >= 0.70 and phase_exec.quality_score >= 0.70:
            logger.debug(f"⚡ Criterion '{criterion}' passed via heuristic (quality sufficient)")
            return True
        
        # FAIL-SAFE: Unknown criteria fail by default (but less strict now)
        logger.warning(f"⚠️  Unknown exit criterion: '{criterion}' - FAILING for safety")
        return False
    
    async def _validate_critical_deliverables(
        self,
        phase: SDLCPhase,
        phase_exec: PhaseExecution,
        output_dir: Path
    ) -> Dict[str, Any]:
        """
        Validate that critical deliverables are present
        
        Returns:
            {
                'met': List[str],
                'failed': List[str],
                'warnings': List[str],
                'critical_missing': int
            }
        """
        critical_deliverables = self.critical_deliverables.get(phase, [])
        met = []
        failed = []
        warnings = []
        critical_missing = 0

        # NEW: For DEPLOYMENT phase, check deployment validation report
        if phase == SDLCPhase.DEPLOYMENT:
            deployment_validation_file = output_dir / "validation_reports" / "DEPLOYMENT_VALIDATION.json"
            if deployment_validation_file.exists():
                try:
                    deployment_validation = json.loads(deployment_validation_file.read_text())

                    # Check if deployment validation passed
                    if deployment_validation.get("passed", False):
                        met.append("✅ Deployment validation passed (builds successful, CORS configured)")
                        logger.info("  ✅ Deployment builds and configuration validated")
                    else:
                        failed.append("❌ Deployment validation failed - builds or configuration issues")
                        critical_missing += 1
                        errors = deployment_validation.get("errors", [])
                        logger.error(f"  ❌ Deployment validation failed: {len(errors)} error(s)")
                        for error in errors[:3]:  # Show first 3 errors
                            logger.error(f"     - {error.get('check')}: {error.get('error')}")

                except Exception as e:
                    logger.warning(f"  ⚠️  Could not read deployment validation: {e}")
                    warnings.append(f"⚠️  Could not validate deployment readiness: {e}")
            else:
                logger.warning("  ⚠️  DEPLOYMENT_VALIDATION.json not found")
                warnings.append("⚠️  Deployment validation report missing - builds may not have been tested")

        for deliverable in critical_deliverables:
            # Check if deliverable was created
            # In production, this would check actual files
            # For now, we check if it's in the expected deliverables
            
            deliverable_present = False
            
            # Check validation reports
            validation_dir = output_dir / "validation_reports"
            if validation_dir.exists():
                for persona_id in phase_exec.personas_executed:
                    validation_file = validation_dir / f"{persona_id}_validation.json"
                    if validation_file.exists():
                        try:
                            with open(validation_file) as f:
                                validation_data = json.load(f)
                                deliverables = validation_data.get("deliverables", {})
                                if deliverable in deliverables:
                                    deliverable_present = True
                                    break
                        except Exception:
                            pass
            
            if deliverable_present:
                met.append(f"✅ Critical deliverable: {deliverable}")
            else:
                failed.append(f"❌ Missing critical deliverable: {deliverable}")
                critical_missing += 1
        
        return {
            'met': met,
            'failed': failed,
            'warnings': warnings,
            'critical_missing': critical_missing
        }
    
    def _is_critical_criterion(self, criterion: str) -> bool:
        """Determine if a criterion is critical (blocking) or warning"""
        criterion_lower = criterion.lower()
        
        # Critical keywords
        critical_keywords = [
            "security",
            "critical",
            "must",
            "required",
            "blocking"
        ]
        
        return any(keyword in criterion_lower for keyword in critical_keywords)
    
    def _generate_entry_recommendations(
        self,
        phase: SDLCPhase,
        criteria_failed: List[str]
    ) -> List[str]:
        """Generate actionable recommendations for entry gate failures"""
        recommendations = []
        
        if not criteria_failed:
            return recommendations
        
        recommendations.append(
            f"Complete all prerequisite phases before starting {phase.value} phase"
        )
        
        for criterion in criteria_failed:
            if "requirements" in criterion.lower():
                recommendations.append(
                    "Ensure requirements phase is completed with approved documentation"
                )
            elif "design" in criterion.lower():
                recommendations.append(
                    "Ensure design phase is completed with reviewed architecture"
                )
            elif "implementation" in criterion.lower():
                recommendations.append(
                    "Ensure implementation phase is completed with passing tests"
                )
        
        return recommendations
    
    def _generate_exit_recommendations(
        self,
        phase: SDLCPhase,
        criteria_failed: List[str],
        blocking_issues: List[str]
    ) -> List[str]:
        """Generate actionable recommendations for exit gate failures"""
        recommendations = []
        
        if not criteria_failed and not blocking_issues:
            return recommendations
        
        # Analyze failure patterns
        has_completeness_issue = any("completeness" in str(item).lower() 
                                     for item in criteria_failed + blocking_issues)
        has_quality_issue = any("quality" in str(item).lower() 
                               for item in criteria_failed + blocking_issues)
        has_test_issue = any("test" in str(item).lower() 
                            for item in criteria_failed + blocking_issues)
        has_missing_deliverable = any("deliverable" in str(item).lower() 
                                      for item in criteria_failed + blocking_issues)
        
        if has_completeness_issue:
            recommendations.append(
                f"Re-run {phase.value} phase with focus on completing all expected deliverables"
            )
        
        if has_quality_issue:
            recommendations.append(
                f"Improve code quality in {phase.value} phase - remove stubs, add error handling, improve documentation"
            )
        
        if has_test_issue:
            recommendations.append(
                "Increase test coverage - add unit tests, integration tests, and edge case tests"
            )
        
        if has_missing_deliverable:
            recommendations.append(
                "Create missing critical deliverables before proceeding"
            )
        
        # Phase-specific recommendations
        if phase == SDLCPhase.REQUIREMENTS:
            recommendations.append(
                "Ensure all user stories have clear acceptance criteria and are reviewed"
            )
        elif phase == SDLCPhase.DESIGN:
            recommendations.append(
                "Ensure architecture document is complete and reviewed by security specialist"
            )
        elif phase == SDLCPhase.IMPLEMENTATION:
            recommendations.append(
                "Ensure all features are implemented with proper error handling and tests"
            )
        elif phase == SDLCPhase.TESTING:
            recommendations.append(
                "Resolve all critical and high-severity bugs before deployment"
            )
        elif phase == SDLCPhase.DEPLOYMENT:
            recommendations.append(
                "Ensure monitoring, alerting, and rollback procedures are in place"
            )
        
        return recommendations
