#!/usr/bin/env python3
"""
SDLC Workflow Templates

Defines workflow templates for software development lifecycle using DAG-based workflows.
These workflows map SDLC phases to executable tasks with proper dependencies.

Integrates with: claude_team_sdk/workflow/workflow_engine.py
"""

import sys
from pathlib import Path
from typing import Dict, List, Any, Optional

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from workflow.dag import DAG, TaskNode, TaskType, WorkflowBuilder

# Import from current directory
import team_organization
SDLCPhase = team_organization.SDLCPhase


class SDLCWorkflowTemplates:
    """
    Pre-built workflow templates for SDLC processes

    Each template creates a complete DAG workflow with:
    - Phased task structure
    - Proper dependencies
    - Role assignments
    - Parallel execution where possible
    """

    @staticmethod
    def create_feature_development_workflow(
        feature_name: str,
        team_id: str,
        complexity: str = "medium",  # simple, medium, complex
        include_security_review: bool = True,
        include_performance_testing: bool = True
    ) -> DAG:
        """
        Standard feature development workflow

        Phases: Requirements → Design → Implementation → Testing → Deployment
        """
        builder = WorkflowBuilder(f"feature_{feature_name.lower().replace(' ', '_')}")

        # ============================================================================
        # PHASE 1: REQUIREMENTS
        # ============================================================================
        req_gathering = builder.add_task(
            task_id="requirements_gathering",
            title=f"Gather Requirements for {feature_name}",
            description=f"Collect and document all requirements for {feature_name}",
            task_type=TaskType.REQUIREMENTS,
            required_role="requirement_analyst",
            priority=10,
            estimated_hours=8 if complexity == "simple" else 16 if complexity == "medium" else 32
        )

        ux_research = builder.add_task(
            task_id="ux_research",
            title=f"UX Research for {feature_name}",
            description="Conduct user research, create wireframes and mockups",
            task_type=TaskType.DESIGN,
            required_role="ui_ux_designer",
            priority=10,
            estimated_hours=16
        )

        req_review = builder.add_task(
            task_id="requirements_review",
            title="Requirements Review",
            description="Review and validate all requirements with stakeholders",
            task_type=TaskType.REVIEW,
            required_role="requirement_analyst",
            priority=9,
            estimated_hours=4,
            depends_on=[req_gathering, ux_research]
        )

        # ============================================================================
        # PHASE 2: DESIGN
        # ============================================================================
        architecture_design = builder.add_task(
            task_id="architecture_design",
            title=f"Architecture Design for {feature_name}",
            description="Design solution architecture, API contracts, database schema",
            task_type=TaskType.DESIGN,
            required_role="solution_architect",
            priority=9,
            estimated_hours=16 if complexity == "simple" else 32 if complexity == "medium" else 48,
            depends_on=[req_review]
        )

        if include_security_review:
            security_design = builder.add_task(
                task_id="security_architecture_review",
                title="Security Architecture Review",
                description="Review architecture for security concerns, create threat model",
                task_type=TaskType.REVIEW,
                required_role="security_specialist",
                priority=9,
                estimated_hours=8,
                depends_on=[architecture_design]
            )

        infrastructure_design = builder.add_task(
            task_id="infrastructure_design",
            title="Infrastructure Design",
            description="Design infrastructure, deployment architecture, CI/CD pipeline",
            task_type=TaskType.DEPLOYMENT,
            required_role="devops_engineer",
            priority=8,
            estimated_hours=8,
            depends_on=[architecture_design]
        )

        design_review_deps = [architecture_design, infrastructure_design]
        if include_security_review:
            design_review_deps.append(security_design)

        design_review = builder.add_task(
            task_id="design_review",
            title="Design Review",
            description="Final design review with all stakeholders",
            task_type=TaskType.REVIEW,
            required_role="solution_architect",
            priority=8,
            estimated_hours=4,
            depends_on=design_review_deps
        )

        # ============================================================================
        # PHASE 3: IMPLEMENTATION
        # ============================================================================

        # Backend Implementation
        backend_setup = builder.add_task(
            task_id="backend_setup",
            title="Backend Project Setup",
            description="Initialize backend project, setup database, configure CI/CD",
            task_type=TaskType.CODE,
            required_role="backend_developer",
            priority=8,
            estimated_hours=4,
            depends_on=[design_review]
        )

        backend_api = builder.add_task(
            task_id="backend_api_implementation",
            title="Backend API Implementation",
            description="Implement REST/GraphQL APIs according to contracts",
            task_type=TaskType.CODE,
            required_role="backend_developer",
            priority=7,
            estimated_hours=24 if complexity == "simple" else 48 if complexity == "medium" else 80,
            depends_on=[backend_setup]
        )

        backend_tests = builder.add_task(
            task_id="backend_unit_tests",
            title="Backend Unit Tests",
            description="Write unit and integration tests for backend",
            task_type=TaskType.TEST,
            required_role="backend_developer",
            priority=7,
            estimated_hours=16,
            depends_on=[backend_api]
        )

        # Frontend Implementation
        frontend_setup = builder.add_task(
            task_id="frontend_setup",
            title="Frontend Project Setup",
            description="Initialize frontend project, setup tooling and CI/CD",
            task_type=TaskType.CODE,
            required_role="frontend_developer",
            priority=8,
            estimated_hours=4,
            depends_on=[design_review]
        )

        frontend_ui = builder.add_task(
            task_id="frontend_ui_implementation",
            title="Frontend UI Implementation",
            description="Implement UI components according to designs",
            task_type=TaskType.CODE,
            required_role="frontend_developer",
            priority=7,
            estimated_hours=24 if complexity == "simple" else 48 if complexity == "medium" else 80,
            depends_on=[frontend_setup, ux_research]
        )

        frontend_integration = builder.add_task(
            task_id="frontend_api_integration",
            title="Frontend API Integration",
            description="Integrate frontend with backend APIs",
            task_type=TaskType.CODE,
            required_role="frontend_developer",
            priority=7,
            estimated_hours=16,
            depends_on=[frontend_ui, backend_api]
        )

        frontend_tests = builder.add_task(
            task_id="frontend_unit_tests",
            title="Frontend Unit Tests",
            description="Write unit and component tests for frontend",
            task_type=TaskType.TEST,
            required_role="frontend_developer",
            priority=7,
            estimated_hours=16,
            depends_on=[frontend_integration]
        )

        # Code Review
        code_review = builder.add_task(
            task_id="code_review",
            title="Code Review",
            description="Peer code review for all implementation",
            task_type=TaskType.REVIEW,
            required_role="solution_architect",
            priority=7,
            estimated_hours=8,
            depends_on=[backend_tests, frontend_tests]
        )

        if include_security_review:
            security_code_review = builder.add_task(
                task_id="security_code_review",
                title="Security Code Review",
                description="Security review of implementation, SAST scanning",
                task_type=TaskType.REVIEW,
                required_role="security_specialist",
                priority=8,
                estimated_hours=8,
                depends_on=[code_review]
            )

        # ============================================================================
        # PHASE 4: TESTING
        # ============================================================================
        test_plan = builder.add_task(
            task_id="test_plan_creation",
            title="Test Plan Creation",
            description="Create comprehensive test plan and test cases",
            task_type=TaskType.TEST,
            required_role="qa_engineer",
            priority=7,
            estimated_hours=8,
            depends_on=[code_review]
        )

        functional_testing = builder.add_task(
            task_id="functional_testing",
            title="Functional Testing",
            description="Execute functional test cases",
            task_type=TaskType.TEST,
            required_role="qa_engineer",
            priority=6,
            estimated_hours=16,
            depends_on=[test_plan]
        )

        integration_testing = builder.add_task(
            task_id="integration_testing",
            title="Integration Testing",
            description="Test integration between components and APIs",
            task_type=TaskType.TEST,
            required_role="qa_engineer",
            priority=6,
            estimated_hours=16,
            depends_on=[test_plan]
        )

        e2e_testing = builder.add_task(
            task_id="e2e_testing",
            title="End-to-End Testing",
            description="Execute end-to-end user scenarios",
            task_type=TaskType.TEST,
            required_role="qa_engineer",
            priority=6,
            estimated_hours=16,
            depends_on=[functional_testing, integration_testing]
        )

        if include_performance_testing:
            performance_testing = builder.add_task(
                task_id="performance_testing",
                title="Performance Testing",
                description="Load testing, stress testing, performance benchmarking",
                task_type=TaskType.TEST,
                required_role="qa_engineer",
                priority=6,
                estimated_hours=16,
                depends_on=[integration_testing]
            )

        if include_security_review:
            security_testing = builder.add_task(
                task_id="security_testing",
                title="Security Testing",
                description="Penetration testing, DAST scanning, security validation",
                task_type=TaskType.TEST,
                required_role="security_specialist",
                priority=8,
                estimated_hours=16,
                depends_on=[security_code_review, integration_testing]
            )

        # Bug fixing iterations (placeholder)
        test_deps = [e2e_testing]
        if include_performance_testing:
            test_deps.append(performance_testing)
        if include_security_review:
            test_deps.append(security_testing)

        bug_fixes = builder.add_task(
            task_id="bug_fixes",
            title="Bug Fixes and Retesting",
            description="Fix identified bugs and retest",
            task_type=TaskType.CODE,
            required_role="backend_developer",
            priority=7,
            estimated_hours=24,
            depends_on=test_deps
        )

        uat = builder.add_task(
            task_id="user_acceptance_testing",
            title="User Acceptance Testing",
            description="Final UAT with stakeholders",
            task_type=TaskType.TEST,
            required_role="requirement_analyst",
            priority=6,
            estimated_hours=8,
            depends_on=[bug_fixes]
        )

        # ============================================================================
        # PHASE 5: DEPLOYMENT
        # ============================================================================
        deployment_plan = builder.add_task(
            task_id="deployment_planning",
            title="Deployment Planning",
            description="Create deployment plan, checklist, and rollback procedures",
            task_type=TaskType.DEPLOYMENT,
            required_role="deployment_specialist",
            priority=7,
            estimated_hours=8,
            depends_on=[uat]
        )

        infrastructure_setup = builder.add_task(
            task_id="production_infrastructure_setup",
            title="Production Infrastructure Setup",
            description="Setup production infrastructure, monitoring, alerting",
            task_type=TaskType.DEPLOYMENT,
            required_role="devops_engineer",
            priority=7,
            estimated_hours=16,
            depends_on=[deployment_plan]
        )

        deployment = builder.add_task(
            task_id="production_deployment",
            title="Production Deployment",
            description="Deploy to production environment",
            task_type=TaskType.DEPLOYMENT,
            required_role="deployment_specialist",
            priority=8,
            estimated_hours=4,
            depends_on=[infrastructure_setup]
        )

        smoke_tests = builder.add_task(
            task_id="smoke_testing",
            title="Production Smoke Tests",
            description="Execute smoke tests in production",
            task_type=TaskType.TEST,
            required_role="deployment_integration_tester",
            priority=8,
            estimated_hours=4,
            depends_on=[deployment]
        )

        integration_validation = builder.add_task(
            task_id="production_integration_validation",
            title="Production Integration Validation",
            description="Validate all integrations in production",
            task_type=TaskType.TEST,
            required_role="deployment_integration_tester",
            priority=8,
            estimated_hours=8,
            depends_on=[smoke_tests]
        )

        # ============================================================================
        # CROSS-CUTTING: DOCUMENTATION
        # ============================================================================
        api_docs = builder.add_task(
            task_id="api_documentation",
            title="API Documentation",
            description="Create OpenAPI/Swagger documentation",
            task_type=TaskType.DOCUMENTATION,
            required_role="technical_writer",
            priority=5,
            estimated_hours=16,
            depends_on=[backend_api]
        )

        user_guide = builder.add_task(
            task_id="user_guide",
            title="User Guide and Tutorials",
            description="Create end-user documentation and tutorials",
            task_type=TaskType.DOCUMENTATION,
            required_role="technical_writer",
            priority=5,
            estimated_hours=16,
            depends_on=[frontend_integration]
        )

        ops_runbook = builder.add_task(
            task_id="operations_runbook",
            title="Operations Runbook",
            description="Create operations and troubleshooting documentation",
            task_type=TaskType.DOCUMENTATION,
            required_role="technical_writer",
            priority=5,
            estimated_hours=8,
            depends_on=[infrastructure_setup]
        )

        release_notes = builder.add_task(
            task_id="release_notes",
            title="Release Notes",
            description="Compile release notes and changelog",
            task_type=TaskType.DOCUMENTATION,
            required_role="technical_writer",
            priority=6,
            estimated_hours=4,
            depends_on=[integration_validation]
        )

        # Final completion task
        final_deps = [integration_validation, release_notes]

        builder.add_task(
            task_id="feature_complete",
            title=f"{feature_name} - Complete",
            description=f"Feature {feature_name} successfully deployed to production",
            task_type=TaskType.MILESTONE,
            required_role="requirement_analyst",
            priority=10,
            estimated_hours=0,
            depends_on=final_deps
        )

        return builder.build()

    @staticmethod
    def create_bug_fix_workflow(
        bug_id: str,
        severity: str,  # critical, high, medium, low
        affected_component: str  # frontend, backend, infrastructure
    ) -> DAG:
        """
        Bug fix workflow with appropriate testing based on severity
        """
        builder = WorkflowBuilder(f"bugfix_{bug_id}")

        # Investigation
        investigation = builder.add_task(
            task_id="bug_investigation",
            title=f"Investigate Bug {bug_id}",
            description="Reproduce and identify root cause",
            task_type=TaskType.CODE,
            required_role="backend_developer" if affected_component == "backend" else "frontend_developer",
            priority=10 if severity in ["critical", "high"] else 5,
            estimated_hours=4
        )

        # Fix implementation
        fix_impl = builder.add_task(
            task_id="bug_fix_implementation",
            title=f"Fix Bug {bug_id}",
            description="Implement bug fix",
            task_type=TaskType.CODE,
            required_role="backend_developer" if affected_component == "backend" else "frontend_developer",
            priority=10 if severity in ["critical", "high"] else 5,
            estimated_hours=8,
            depends_on=[investigation]
        )

        # Unit tests
        unit_tests = builder.add_task(
            task_id="fix_unit_tests",
            title="Unit Tests for Fix",
            description="Add/update unit tests to cover the fix",
            task_type=TaskType.TEST,
            required_role="backend_developer" if affected_component == "backend" else "frontend_developer",
            priority=9,
            estimated_hours=4,
            depends_on=[fix_impl]
        )

        # Code review
        code_review = builder.add_task(
            task_id="fix_code_review",
            title="Code Review for Fix",
            description="Peer review of bug fix",
            task_type=TaskType.REVIEW,
            required_role="solution_architect",
            priority=9,
            estimated_hours=2,
            depends_on=[unit_tests]
        )

        # Testing based on severity
        if severity in ["critical", "high"]:
            # Full regression testing for critical/high bugs
            regression = builder.add_task(
                task_id="regression_testing",
                title="Regression Testing",
                description="Full regression test suite",
                task_type=TaskType.TEST,
                required_role="qa_engineer",
                priority=10,
                estimated_hours=16,
                depends_on=[code_review]
            )

            security_check = builder.add_task(
                task_id="security_validation",
                title="Security Validation",
                description="Ensure fix doesn't introduce security issues",
                task_type=TaskType.REVIEW,
                required_role="security_specialist",
                priority=10,
                estimated_hours=4,
                depends_on=[code_review]
            )

            final_test = regression
        else:
            # Smoke testing for medium/low bugs
            smoke_test = builder.add_task(
                task_id="smoke_testing",
                title="Smoke Testing",
                description="Quick smoke test of affected functionality",
                task_type=TaskType.TEST,
                required_role="qa_engineer",
                priority=7,
                estimated_hours=4,
                depends_on=[code_review]
            )
            final_test = smoke_test

        # Deployment
        deployment = builder.add_task(
            task_id="hotfix_deployment",
            title=f"Deploy Bug Fix {bug_id}",
            description="Deploy fix to production",
            task_type=TaskType.DEPLOYMENT,
            required_role="deployment_specialist",
            priority=10 if severity == "critical" else 7,
            estimated_hours=2,
            depends_on=[final_test]
        )

        # Post-deployment validation
        builder.add_task(
            task_id="post_deployment_validation",
            title="Post-Deployment Validation",
            description="Verify fix in production",
            task_type=TaskType.TEST,
            required_role="deployment_integration_tester",
            priority=10 if severity == "critical" else 7,
            estimated_hours=2,
            depends_on=[deployment]
        )

        return builder.build()

    @staticmethod
    def create_security_patch_workflow(
        vulnerability_id: str,
        cve_id: Optional[str] = None
    ) -> DAG:
        """
        Security vulnerability patch workflow
        """
        builder = WorkflowBuilder(f"security_patch_{vulnerability_id}")

        # Security assessment
        assessment = builder.add_task(
            task_id="security_assessment",
            title=f"Assess Vulnerability {vulnerability_id}",
            description=f"Analyze vulnerability {cve_id or vulnerability_id} and determine impact",
            task_type=TaskType.REVIEW,
            required_role="security_specialist",
            priority=10,
            estimated_hours=4
        )

        # Patch implementation
        patch_impl = builder.add_task(
            task_id="patch_implementation",
            title="Implement Security Patch",
            description="Implement fix for security vulnerability",
            task_type=TaskType.CODE,
            required_role="backend_developer",
            priority=10,
            estimated_hours=8,
            depends_on=[assessment]
        )

        # Security code review
        security_review = builder.add_task(
            task_id="security_code_review",
            title="Security Code Review",
            description="Security specialist reviews the patch",
            task_type=TaskType.REVIEW,
            required_role="security_specialist",
            priority=10,
            estimated_hours=4,
            depends_on=[patch_impl]
        )

        # Security testing
        security_test = builder.add_task(
            task_id="security_testing",
            title="Security Testing",
            description="Test that vulnerability is patched",
            task_type=TaskType.TEST,
            required_role="security_specialist",
            priority=10,
            estimated_hours=8,
            depends_on=[security_review]
        )

        # Regression testing
        regression = builder.add_task(
            task_id="regression_testing",
            title="Regression Testing",
            description="Ensure patch doesn't break functionality",
            task_type=TaskType.TEST,
            required_role="qa_engineer",
            priority=10,
            estimated_hours=16,
            depends_on=[security_test]
        )

        # Emergency deployment
        deployment = builder.add_task(
            task_id="emergency_deployment",
            title="Emergency Security Patch Deployment",
            description="Deploy security patch to production",
            task_type=TaskType.DEPLOYMENT,
            required_role="deployment_specialist",
            priority=10,
            estimated_hours=2,
            depends_on=[regression]
        )

        # Validation
        builder.add_task(
            task_id="security_validation",
            title="Post-Deployment Security Validation",
            description="Verify vulnerability is patched in production",
            task_type=TaskType.TEST,
            required_role="security_specialist",
            priority=10,
            estimated_hours=4,
            depends_on=[deployment]
        )

        return builder.build()

    @staticmethod
    def create_sprint_workflow(
        sprint_number: int,
        user_stories: List[Dict[str, Any]],
        sprint_duration_weeks: int = 2
    ) -> DAG:
        """
        Agile sprint workflow with multiple user stories

        Args:
            sprint_number: Sprint number
            user_stories: List of user stories, each with {id, title, points, priority}
            sprint_duration_weeks: Sprint duration in weeks
        """
        builder = WorkflowBuilder(f"sprint_{sprint_number}")

        # Sprint planning
        planning = builder.add_task(
            task_id="sprint_planning",
            title=f"Sprint {sprint_number} Planning",
            description="Plan sprint backlog and assign tasks",
            task_type=TaskType.REQUIREMENTS,
            required_role="requirement_analyst",
            priority=10,
            estimated_hours=8
        )

        # Design tasks for all stories
        design = builder.add_task(
            task_id="sprint_design",
            title=f"Sprint {sprint_number} Design",
            description="Design solutions for sprint user stories",
            task_type=TaskType.DESIGN,
            required_role="solution_architect",
            priority=9,
            estimated_hours=16,
            depends_on=[planning]
        )

        # Create tasks for each user story
        story_tasks = []
        for story in user_stories:
            story_id = story['id']
            story_points = story.get('points', 5)
            estimated_hours = story_points * 4  # Rough estimate: 1 point = 4 hours

            # Implementation
            impl = builder.add_task(
                task_id=f"story_{story_id}_implementation",
                title=f"Implement: {story['title']}",
                description=f"Implement user story {story_id}",
                task_type=TaskType.CODE,
                required_role="backend_developer",
                priority=story.get('priority', 5),
                estimated_hours=estimated_hours,
                depends_on=[design]
            )

            # Testing
            test = builder.add_task(
                task_id=f"story_{story_id}_testing",
                title=f"Test: {story['title']}",
                description=f"Test user story {story_id}",
                task_type=TaskType.TEST,
                required_role="qa_engineer",
                priority=story.get('priority', 5),
                estimated_hours=estimated_hours // 2,
                depends_on=[impl]
            )

            story_tasks.append(test)

        # Sprint review
        review = builder.add_task(
            task_id="sprint_review",
            title=f"Sprint {sprint_number} Review",
            description="Review sprint deliverables with stakeholders",
            task_type=TaskType.REVIEW,
            required_role="requirement_analyst",
            priority=8,
            estimated_hours=4,
            depends_on=story_tasks
        )

        # Sprint retrospective
        builder.add_task(
            task_id="sprint_retrospective",
            title=f"Sprint {sprint_number} Retrospective",
            description="Team retrospective and improvement planning",
            task_type=TaskType.MILESTONE,
            required_role="requirement_analyst",
            priority=7,
            estimated_hours=4,
            depends_on=[review]
        )

        return builder.build()


# Helper function to visualize workflow
def print_workflow_summary(dag: DAG):
    """Print a summary of the workflow"""
    print(f"\n{'=' * 80}")
    print(f"Workflow: {dag.workflow_id}")
    print(f"{'=' * 80}\n")

    # Group tasks by phase
    from collections import defaultdict
    by_type = defaultdict(list)

    for task_id, node in dag.nodes.items():
        by_type[node.task_type].append(node)

    for task_type, tasks in sorted(by_type.items()):
        print(f"\n📋 {task_type.upper()}")
        print("-" * 80)
        for task in sorted(tasks, key=lambda t: t.priority, reverse=True):
            deps = f" (depends on: {', '.join(task.depends_on)})" if task.depends_on else ""
            print(f"  [{task.priority}] {task.title}{deps}")
            print(f"      Role: {task.required_role} | Estimate: {task.estimated_hours}h")

    print(f"\n{'=' * 80}")
    print(f"Total tasks: {len(dag.nodes)}")
    print(f"Total estimated hours: {sum(n.estimated_hours for n in dag.nodes.values())}")
    print(f"Critical path length: {len(dag.get_critical_path())}")
    print(f"{'=' * 80}\n")


if __name__ == "__main__":
    # Demo: Create and print workflows
    print("SDLC WORKFLOW TEMPLATES DEMO")
    print("=" * 80)

    # Feature development workflow
    feature_dag = SDLCWorkflowTemplates.create_feature_development_workflow(
        feature_name="User Authentication",
        team_id="demo_team",
        complexity="medium",
        include_security_review=True,
        include_performance_testing=True
    )
    print_workflow_summary(feature_dag)

    # Bug fix workflow
    bug_dag = SDLCWorkflowTemplates.create_bug_fix_workflow(
        bug_id="BUG-123",
        severity="high",
        affected_component="backend"
    )
    print_workflow_summary(bug_dag)

    # Security patch workflow
    security_dag = SDLCWorkflowTemplates.create_security_patch_workflow(
        vulnerability_id="VULN-456",
        cve_id="CVE-2024-12345"
    )
    print_workflow_summary(security_dag)

    # Sprint workflow
    sprint_dag = SDLCWorkflowTemplates.create_sprint_workflow(
        sprint_number=15,
        user_stories=[
            {"id": "US-101", "title": "User Login", "points": 5, "priority": 8},
            {"id": "US-102", "title": "Password Reset", "points": 3, "priority": 6},
            {"id": "US-103", "title": "Profile Management", "points": 8, "priority": 7}
        ],
        sprint_duration_weeks=2
    )
    print_workflow_summary(sprint_dag)
