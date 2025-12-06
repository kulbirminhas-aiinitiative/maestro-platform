#!/usr/bin/env python3
"""
DAG Validation Nodes
Integrates validation framework into DAG workflow as executable nodes
"""

import logging
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

from dag_workflow import (
    WorkflowNode,
    NodeType,
    ExecutionMode,
    RetryPolicy,
)
from workflow_validation import (
    WorkflowValidator,
    ValidationSeverity,
    PhaseValidationReport
)
from workflow_gap_detector import WorkflowGapDetector, GapAnalysisReport
from implementation_completeness_checker import ImplementationCompletenessChecker, ImplementationProgress
from deployment_readiness_validator import DeploymentReadinessValidator, DeploymentReadinessReport

logger = logging.getLogger(__name__)


class ValidationNodeType:
    """Types of validation nodes"""
    PHASE_VALIDATOR = "phase_validator"  # Validates phase outputs
    GAP_DETECTOR = "gap_detector"  # Detects gaps in implementation
    COMPLETENESS_CHECKER = "completeness_checker"  # Checks implementation progress
    DEPLOYMENT_GATE = "deployment_gate"  # Pre-deployment validation
    DEPLOYMENT_READINESS = "deployment_readiness"  # Deployment readiness with smoke tests
    HANDOFF_VALIDATOR = "handoff_validator"  # Validates persona handoffs


@dataclass
class ValidationConfig:
    """Configuration for validation nodes"""
    validation_type: str  # ValidationNodeType
    phase_to_validate: Optional[str] = None
    severity_threshold: str = "critical"  # Block on this severity or higher
    fail_on_validation_error: bool = True
    generate_recovery_context: bool = False
    output_dir: Optional[str] = None  # Where workflow outputs are stored


class PhaseValidationNodeExecutor:
    """
    Validates phase outputs using workflow_validation.py framework

    Can be inserted as a gate after any phase to ensure quality before proceeding
    """

    def __init__(self, config: ValidationConfig):
        self.config = config
        logger.info(f"Initialized PhaseValidationNodeExecutor for phase: {config.phase_to_validate}")

    async def execute(self, node_input: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute phase validation

        Args:
            node_input: Contains workflow_dir, phase_name, dependency_outputs

        Returns:
            Validation results with pass/fail status
        """
        logger.info(f"Validating phase: {self.config.phase_to_validate}")

        try:
            # Get workflow directory from context
            workflow_dir = self._get_workflow_dir(node_input)
            if not workflow_dir or not workflow_dir.exists():
                return self._validation_skipped("Workflow directory not found")

            # Create validator
            validator = WorkflowValidator(workflow_dir)

            # Validate specific phase or all phases
            if self.config.phase_to_validate:
                report = validator.validate_phase(self.config.phase_to_validate)
                reports = {self.config.phase_to_validate: report}
            else:
                reports = validator.validate_all()

            # Analyze results
            validation_result = self._analyze_validation_results(reports)

            # Determine if validation should block
            should_fail = (
                self.config.fail_on_validation_error and
                validation_result['has_critical_failures']
            )

            if should_fail:
                logger.error(f"Validation FAILED for phase {self.config.phase_to_validate}")
                return {
                    'status': 'failed',
                    'validation_passed': False,
                    'validation_result': validation_result,
                    'error': f"Validation failed: {validation_result['critical_count']} critical issues found",
                    'reports': {k: v.to_dict() for k, v in reports.items()}
                }
            else:
                logger.info(f"Validation PASSED for phase {self.config.phase_to_validate}")
                return {
                    'status': 'completed',
                    'validation_passed': True,
                    'validation_result': validation_result,
                    'reports': {k: v.to_dict() for k, v in reports.items()}
                }

        except Exception as e:
            logger.error(f"Validation node execution failed: {e}", exc_info=True)
            return {
                'status': 'failed',
                'validation_passed': False,
                'error': f"Validation execution error: {str(e)}"
            }

    def _get_workflow_dir(self, node_input: Dict[str, Any]) -> Optional[Path]:
        """Extract workflow directory from node input"""
        # Try from config
        if self.config.output_dir:
            return Path(self.config.output_dir)

        # Try from global context
        global_context = node_input.get('global_context', {})
        if 'workflow_dir' in global_context:
            return Path(global_context['workflow_dir'])

        if 'output_dir' in global_context:
            return Path(global_context['output_dir'])

        # Try from dependency outputs
        dependency_outputs = node_input.get('dependency_outputs', {})
        for dep_output in dependency_outputs.values():
            if 'output_dir' in dep_output:
                return Path(dep_output['output_dir'])
            if 'workflow_dir' in dep_output:
                return Path(dep_output['workflow_dir'])

        return None

    def _analyze_validation_results(
        self, reports: Dict[str, PhaseValidationReport]
    ) -> Dict[str, Any]:
        """Analyze validation reports and extract key metrics"""
        critical_count = 0
        high_count = 0
        medium_count = 0
        low_count = 0

        critical_failures = []

        for phase, report in reports.items():
            for result in report.results:
                if not result.passed:
                    if result.severity == ValidationSeverity.CRITICAL:
                        critical_count += 1
                        critical_failures.append({
                            'phase': phase,
                            'check': result.check_name,
                            'message': result.message,
                            'fix': result.fix_suggestion
                        })
                    elif result.severity == ValidationSeverity.HIGH:
                        high_count += 1
                    elif result.severity == ValidationSeverity.MEDIUM:
                        medium_count += 1
                    else:
                        low_count += 1

        return {
            'has_critical_failures': critical_count > 0,
            'critical_count': critical_count,
            'high_count': high_count,
            'medium_count': medium_count,
            'low_count': low_count,
            'total_failures': critical_count + high_count + medium_count + low_count,
            'critical_failures': critical_failures,
            'phases_validated': list(reports.keys())
        }

    def _validation_skipped(self, reason: str) -> Dict[str, Any]:
        """Return result when validation is skipped"""
        logger.warning(f"Validation skipped: {reason}")
        return {
            'status': 'completed',
            'validation_passed': True,
            'validation_skipped': True,
            'skip_reason': reason
        }


class GapDetectionNodeExecutor:
    """
    Detects gaps in workflow outputs using workflow_gap_detector.py

    Can be used to analyze incomplete implementations and generate recovery contexts
    """

    def __init__(self, config: ValidationConfig):
        self.config = config
        logger.info("Initialized GapDetectionNodeExecutor")

    async def execute(self, node_input: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute gap detection

        Returns:
            Gap analysis report with specific missing components
        """
        logger.info("Running gap detection")

        try:
            workflow_dir = self._get_workflow_dir(node_input)
            if not workflow_dir or not workflow_dir.exists():
                return {'status': 'completed', 'gaps': [], 'skipped': True}

            # Create gap detector
            detector = WorkflowGapDetector(workflow_dir)

            # Detect gaps
            report: GapAnalysisReport = detector.detect_gaps()

            # Generate recovery context if requested
            recovery_context = None
            if self.config.generate_recovery_context and not report.is_deployable:
                recovery_context = detector.generate_recovery_context(report)

            # Determine if gaps should block execution
            should_fail = (
                self.config.fail_on_validation_error and
                report.critical_gaps > 0
            )

            result = {
                'status': 'failed' if should_fail else 'completed',
                'gaps_detected': report.total_gaps,
                'critical_gaps': report.critical_gaps,
                'high_priority_gaps': report.high_priority_gaps,
                'estimated_completion': report.estimated_completion_percentage,
                'is_deployable': report.is_deployable,
                'recovery_priority': report.recovery_priority,
                'gap_report': report.to_dict(),
            }

            if recovery_context:
                result['recovery_context'] = recovery_context

            if should_fail:
                result['error'] = f"Critical gaps detected: {report.critical_gaps} deployment blockers"

            logger.info(f"Gap detection complete: {report.total_gaps} gaps, "
                       f"{report.estimated_completion_percentage*100:.1f}% complete")

            return result

        except Exception as e:
            logger.error(f"Gap detection failed: {e}", exc_info=True)
            return {
                'status': 'failed',
                'error': f"Gap detection error: {str(e)}"
            }

    def _get_workflow_dir(self, node_input: Dict[str, Any]) -> Optional[Path]:
        """Extract workflow directory from node input"""
        # Same logic as PhaseValidationNodeExecutor
        if self.config.output_dir:
            return Path(self.config.output_dir)

        global_context = node_input.get('global_context', {})
        if 'workflow_dir' in global_context:
            return Path(global_context['workflow_dir'])
        if 'output_dir' in global_context:
            return Path(global_context['output_dir'])

        dependency_outputs = node_input.get('dependency_outputs', {})
        for dep_output in dependency_outputs.values():
            if 'output_dir' in dep_output:
                return Path(dep_output['output_dir'])

        return None


class CompletenessCheckNodeExecutor:
    """
    Checks implementation completeness through sub-phases

    Uses implementation_completeness_checker.py to track detailed progress
    """

    def __init__(self, config: ValidationConfig):
        self.config = config
        logger.info("Initialized CompletenessCheckNodeExecutor")

    async def execute(self, node_input: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute implementation completeness check

        Returns:
            Detailed sub-phase progress report
        """
        logger.info("Checking implementation completeness")

        try:
            workflow_dir = self._get_workflow_dir(node_input)
            if not workflow_dir or not workflow_dir.exists():
                return {'status': 'completed', 'skipped': True}

            # Create completeness checker
            checker = ImplementationCompletenessChecker(workflow_dir)

            # Check progress
            progress: ImplementationProgress = checker.check_implementation_progress()

            # Determine if low completion should block
            should_fail = (
                self.config.fail_on_validation_error and
                progress.overall_completion < 0.7  # Less than 70% complete
            )

            result = {
                'status': 'failed' if should_fail else 'completed',
                'overall_completion': progress.overall_completion,
                'current_sub_phase': progress.current_sub_phase.value if progress.current_sub_phase else None,
                'backend_complete': progress.backend_complete,
                'frontend_complete': progress.frontend_complete,
                'integration_complete': progress.integration_complete,
                'is_deployable': progress.is_deployable,
                'blockers': progress.blockers,
                'progress_report': progress.to_dict()
            }

            if should_fail:
                result['error'] = f"Implementation incomplete: {progress.overall_completion*100:.1f}% complete"

            logger.info(f"Completeness check complete: {progress.overall_completion*100:.1f}% overall")

            return result

        except Exception as e:
            logger.error(f"Completeness check failed: {e}", exc_info=True)
            return {
                'status': 'failed',
                'error': f"Completeness check error: {str(e)}"
            }

    def _get_workflow_dir(self, node_input: Dict[str, Any]) -> Optional[Path]:
        """Extract workflow directory from node input"""
        if self.config.output_dir:
            return Path(self.config.output_dir)

        global_context = node_input.get('global_context', {})
        if 'workflow_dir' in global_context:
            return Path(global_context['workflow_dir'])
        if 'output_dir' in global_context:
            return Path(global_context['output_dir'])

        dependency_outputs = node_input.get('dependency_outputs', {})
        for dep_output in dependency_outputs.values():
            if 'output_dir' in dep_output:
                return Path(dep_output['output_dir'])

        return None


class DeploymentReadinessNodeExecutor:
    """
    Validates deployment readiness with actual smoke tests

    Uses deployment_readiness_validator.py for comprehensive pre-deployment validation
    """

    def __init__(self, config: ValidationConfig):
        self.config = config
        logger.info("Initialized DeploymentReadinessNodeExecutor")

    async def execute(self, node_input: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute deployment readiness validation

        Returns:
            Deployment readiness report with smoke test results
        """
        logger.info("Checking deployment readiness")

        try:
            workflow_dir = self._get_workflow_dir(node_input)
            if not workflow_dir or not workflow_dir.exists():
                return {'status': 'completed', 'skipped': True}

            # Create deployment readiness validator
            validator = DeploymentReadinessValidator(
                workflow_dir=workflow_dir,
                run_service_tests=False  # Don't actually start services by default
            )

            # Run validation
            report: DeploymentReadinessReport = await validator.validate()

            # Determine if failures should block
            should_fail = (
                self.config.fail_on_validation_error and
                not report.is_deployable
            )

            result = {
                'status': 'failed' if should_fail else 'completed',
                'is_deployable': report.is_deployable,
                'checks_passed': report.checks_passed,
                'checks_failed': report.checks_failed,
                'critical_failures': report.critical_failures,
                'high_failures': report.high_failures,
                'deployment_report': report.to_dict()
            }

            if should_fail:
                result['error'] = f"Deployment not ready: {report.critical_failures} critical issues"

            logger.info(f"Deployment readiness check complete: {report.checks_passed} passed, {report.checks_failed} failed")

            return result

        except Exception as e:
            logger.error(f"Deployment readiness check failed: {e}", exc_info=True)
            return {
                'status': 'failed',
                'error': f"Deployment readiness check error: {str(e)}"
            }

    def _get_workflow_dir(self, node_input: Dict[str, Any]) -> Optional[Path]:
        """Extract workflow directory from node input"""
        if self.config.output_dir:
            return Path(self.config.output_dir)

        global_context = node_input.get('global_context', {})
        if 'workflow_dir' in global_context:
            return Path(global_context['workflow_dir'])
        if 'output_dir' in global_context:
            return Path(global_context['output_dir'])

        dependency_outputs = node_input.get('dependency_outputs', {})
        for dep_output in dependency_outputs.values():
            if 'output_dir' in dep_output:
                return Path(dep_output['output_dir'])

        return None


class HandoffValidationNodeExecutor:
    """
    Validates persona handoffs between phases

    Ensures artifacts from one phase are valid before next phase begins
    """

    def __init__(self, from_phase: str, to_phase: str, config: ValidationConfig):
        self.from_phase = from_phase
        self.to_phase = to_phase
        self.config = config
        logger.info(f"Initialized HandoffValidationNodeExecutor: {from_phase} -> {to_phase}")

    async def execute(self, node_input: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute handoff validation

        Validates that:
        - Previous phase completed successfully
        - Required artifacts exist
        - Artifacts are valid and usable
        """
        logger.info(f"Validating handoff: {self.from_phase} -> {self.to_phase}")

        try:
            # Get outputs from previous phase
            dependency_outputs = node_input.get('dependency_outputs', {})
            from_phase_output = dependency_outputs.get(f"phase_{self.from_phase}", {})

            if not from_phase_output:
                return {
                    'status': 'failed',
                    'handoff_valid': False,
                    'error': f"No output found from {self.from_phase}"
                }

            # Check phase status
            if from_phase_output.get('status') != 'completed':
                return {
                    'status': 'failed',
                    'handoff_valid': False,
                    'error': f"{self.from_phase} did not complete successfully"
                }

            # Validate based on handoff type
            validation_result = self._validate_handoff_artifacts(from_phase_output)

            if not validation_result['valid']:
                return {
                    'status': 'failed',
                    'handoff_valid': False,
                    'error': validation_result['error'],
                    'validation_details': validation_result
                }

            logger.info(f"Handoff validation passed: {self.from_phase} -> {self.to_phase}")
            return {
                'status': 'completed',
                'handoff_valid': True,
                'from_phase': self.from_phase,
                'to_phase': self.to_phase,
                'validation_details': validation_result
            }

        except Exception as e:
            logger.error(f"Handoff validation failed: {e}", exc_info=True)
            return {
                'status': 'failed',
                'handoff_valid': False,
                'error': f"Handoff validation error: {str(e)}"
            }

    def _validate_handoff_artifacts(self, phase_output: Dict[str, Any]) -> Dict[str, Any]:
        """Validate artifacts for specific handoff types"""

        # Backend -> Frontend handoff
        if self.from_phase == "backend_development" and self.to_phase == "frontend_development":
            return self._validate_backend_to_frontend(phase_output)

        # Frontend -> Testing handoff
        elif self.from_phase == "frontend_development" and self.to_phase == "testing":
            return self._validate_frontend_to_testing(phase_output)

        # Testing -> Deployment handoff
        elif self.from_phase == "testing" and self.to_phase == "review":
            return self._validate_testing_to_deployment(phase_output)

        # Generic handoff - just check artifacts exist
        else:
            artifacts = phase_output.get('artifacts', [])
            return {
                'valid': len(artifacts) > 0,
                'error': None if len(artifacts) > 0 else "No artifacts produced by phase",
                'artifact_count': len(artifacts)
            }

    def _validate_backend_to_frontend(self, backend_output: Dict[str, Any]) -> Dict[str, Any]:
        """Validate backend artifacts before frontend development"""
        artifacts = backend_output.get('artifacts', [])

        # Check for required backend artifacts
        has_api_routes = any('routes' in str(a).lower() for a in artifacts)
        has_models = any('models' in str(a).lower() for a in artifacts)
        has_server = any('server' in str(a).lower() for a in artifacts)

        all_present = has_api_routes and has_models and has_server

        return {
            'valid': all_present,
            'error': None if all_present else "Backend missing required artifacts (routes, models, or server)",
            'has_api_routes': has_api_routes,
            'has_models': has_models,
            'has_server': has_server,
            'artifact_count': len(artifacts)
        }

    def _validate_frontend_to_testing(self, frontend_output: Dict[str, Any]) -> Dict[str, Any]:
        """Validate frontend artifacts before testing"""
        artifacts = frontend_output.get('artifacts', [])

        # Check for required frontend artifacts
        has_components = any('components' in str(a).lower() for a in artifacts)
        has_pages = any('pages' in str(a).lower() or 'views' in str(a).lower() for a in artifacts)

        all_present = has_components and has_pages

        return {
            'valid': all_present,
            'error': None if all_present else "Frontend missing required artifacts (components or pages)",
            'has_components': has_components,
            'has_pages': has_pages,
            'artifact_count': len(artifacts)
        }

    def _validate_testing_to_deployment(self, testing_output: Dict[str, Any]) -> Dict[str, Any]:
        """Validate testing artifacts before deployment"""
        artifacts = testing_output.get('artifacts', [])

        # Check for test artifacts
        has_tests = any('test' in str(a).lower() for a in artifacts)

        # Check if tests passed (if available)
        test_results = testing_output.get('test_results', {})
        tests_passed = test_results.get('passed', True)  # Default to True if not specified

        all_valid = has_tests and tests_passed

        return {
            'valid': all_valid,
            'error': None if all_valid else "Tests missing or failed",
            'has_tests': has_tests,
            'tests_passed': tests_passed,
            'artifact_count': len(artifacts)
        }


def create_validation_node(
    node_id: str,
    validation_type: str,
    phase_to_validate: Optional[str] = None,
    dependencies: List[str] = None,
    fail_on_error: bool = True,
    **kwargs
) -> WorkflowNode:
    """
    Factory function to create validation nodes

    Args:
        node_id: Unique node ID
        validation_type: Type from ValidationNodeType
        phase_to_validate: Phase to validate (for phase validators)
        dependencies: List of node IDs this validator depends on
        fail_on_error: Whether to fail workflow on validation error
        **kwargs: Additional config options

    Returns:
        WorkflowNode configured for validation
    """
    config = ValidationConfig(
        validation_type=validation_type,
        phase_to_validate=phase_to_validate,
        severity_threshold=kwargs.get('severity_threshold', 'critical'),
        fail_on_validation_error=fail_on_error,
        generate_recovery_context=kwargs.get('generate_recovery_context', False),
        output_dir=kwargs.get('output_dir')
    )

    # Select executor based on type
    if validation_type == ValidationNodeType.PHASE_VALIDATOR:
        executor = PhaseValidationNodeExecutor(config)
    elif validation_type == ValidationNodeType.GAP_DETECTOR:
        executor = GapDetectionNodeExecutor(config)
    elif validation_type == ValidationNodeType.COMPLETENESS_CHECKER:
        executor = CompletenessCheckNodeExecutor(config)
    elif validation_type == ValidationNodeType.DEPLOYMENT_READINESS:
        executor = DeploymentReadinessNodeExecutor(config)
    else:
        raise ValueError(f"Unknown validation type: {validation_type}")

    # Create node
    node = WorkflowNode(
        node_id=node_id,
        name=f"validate_{phase_to_validate}" if phase_to_validate else "validate",
        node_type=NodeType.CUSTOM,
        executor=executor.execute,
        dependencies=dependencies or [],
        execution_mode=ExecutionMode.SEQUENTIAL,
        retry_policy=RetryPolicy(
            max_attempts=1,
            retry_on_failure=False,
        ),
        config=config.__dict__,
        metadata={
            'validation_type': validation_type,
            'phase': phase_to_validate,
            'validator': True
        }
    )

    return node


def create_handoff_validation_node(
    node_id: str,
    from_phase: str,
    to_phase: str,
    dependencies: List[str],
    fail_on_error: bool = True
) -> WorkflowNode:
    """
    Factory function to create handoff validation nodes

    Args:
        node_id: Unique node ID
        from_phase: Source phase
        to_phase: Target phase
        dependencies: List of node IDs (should include from_phase node)
        fail_on_error: Whether to fail workflow on validation error

    Returns:
        WorkflowNode configured for handoff validation
    """
    config = ValidationConfig(
        validation_type=ValidationNodeType.HANDOFF_VALIDATOR,
        fail_on_validation_error=fail_on_error
    )

    executor = HandoffValidationNodeExecutor(from_phase, to_phase, config)

    node = WorkflowNode(
        node_id=node_id,
        name=f"handoff_{from_phase}_to_{to_phase}",
        node_type=NodeType.CUSTOM,
        executor=executor.execute,
        dependencies=dependencies,
        execution_mode=ExecutionMode.SEQUENTIAL,
        retry_policy=RetryPolicy(max_attempts=1, retry_on_failure=False),
        config=config.__dict__,
        metadata={
            'validation_type': ValidationNodeType.HANDOFF_VALIDATOR,
            'from_phase': from_phase,
            'to_phase': to_phase,
            'validator': True
        }
    )

    return node


# Export public API
__all__ = [
    'ValidationNodeType',
    'ValidationConfig',
    'PhaseValidationNodeExecutor',
    'GapDetectionNodeExecutor',
    'CompletenessCheckNodeExecutor',
    'DeploymentReadinessNodeExecutor',
    'HandoffValidationNodeExecutor',
    'create_validation_node',
    'create_handoff_validation_node',
]
