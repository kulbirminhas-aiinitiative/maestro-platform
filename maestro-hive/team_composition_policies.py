#!/usr/bin/env python3
"""
Team Composition Policies for Dynamic Team Management

Defines optimal team compositions for different:
- Project types (bug fix, feature, full SDLC, security patch, sprint)
- Project complexity levels (simple, medium, complex)
- SDLC phases (requirements, design, implementation, testing, deployment)
- Emergency scenarios

Provides:
- Minimum viable teams
- Optimal team sizes
- Scaling policies
- Phase-based team transitions
"""

import sys
from pathlib import Path
from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass
from enum import Enum

# Add parent directories to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
sys.path.insert(0, str(Path(__file__).parent))

import team_organization
SDLCPhase = team_organization.SDLCPhase


class ProjectType(str, Enum):
    """Types of projects with different team requirements"""
    BUG_FIX = "bug_fix"
    SIMPLE_FEATURE = "simple_feature"
    MEDIUM_FEATURE = "medium_feature"
    COMPLEX_FEATURE = "complex_feature"
    FULL_SDLC = "full_sdlc"
    SECURITY_PATCH = "security_patch"
    SPRINT = "sprint"
    EMERGENCY = "emergency"


class ComplexityLevel(str, Enum):
    """Project complexity levels"""
    SIMPLE = "simple"
    MEDIUM = "medium"
    COMPLEX = "complex"
    VERY_COMPLEX = "very_complex"


@dataclass
class TeamComposition:
    """
    Defines a team composition

    Contains:
    - Required personas (must have)
    - Optional personas (nice to have)
    - Minimum/maximum team size
    - Expected duration
    """
    project_type: str
    required_personas: List[str]
    optional_personas: List[str]
    min_team_size: int
    optimal_team_size: int
    max_team_size: int
    expected_duration_days: int
    description: str
    scaling_policy: str  # "fixed", "phase_based", "workload_based"


@dataclass
class PhaseTeamRequirements:
    """Team requirements for a specific SDLC phase"""
    phase: SDLCPhase
    primary_personas: List[str]  # Must be ACTIVE
    supporting_personas: List[str]  # Can be ON_STANDBY
    can_retire_from_previous_phase: List[str]  # Can retire these from previous phase
    description: str


class TeamCompositionPolicy:
    """
    Defines team composition policies for different scenarios

    Provides methods to:
    - Get minimum viable team
    - Get optimal team
    - Get phase-specific requirements
    - Determine scaling needs
    """

    @staticmethod
    def get_composition_for_project(
        project_type: ProjectType,
        complexity: Optional[ComplexityLevel] = None
    ) -> TeamComposition:
        """
        Get team composition based on project type and complexity

        Returns minimum and optimal team compositions
        """
        compositions = {
            ProjectType.BUG_FIX: TeamComposition(
                project_type="bug_fix",
                required_personas=[
                    "backend_developer",  # or frontend_developer based on bug
                    "qa_engineer"
                ],
                optional_personas=[
                    "security_specialist",  # For security-related bugs
                    "devops_engineer"       # For deployment issues
                ],
                min_team_size=2,
                optimal_team_size=3,
                max_team_size=4,
                expected_duration_days=3,
                description="Quick bug fix with minimal team",
                scaling_policy="fixed"
            ),

            ProjectType.SIMPLE_FEATURE: TeamComposition(
                project_type="simple_feature",
                required_personas=[
                    "requirement_analyst",
                    "solution_architect",
                    "backend_developer",
                    "frontend_developer",
                    "qa_engineer"
                ],
                optional_personas=[
                    "ui_ux_designer",
                    "technical_writer",
                    "devops_engineer"
                ],
                min_team_size=5,
                optimal_team_size=6,
                max_team_size=8,
                expected_duration_days=14,
                description="Simple feature with core team",
                scaling_policy="phase_based"
            ),

            ProjectType.MEDIUM_FEATURE: TeamComposition(
                project_type="medium_feature",
                required_personas=[
                    "requirement_analyst",
                    "solution_architect",
                    "backend_developer",
                    "frontend_developer",
                    "qa_engineer",
                    "ui_ux_designer",
                    "devops_engineer"
                ],
                optional_personas=[
                    "security_specialist",
                    "technical_writer",
                    "deployment_specialist",
                    "deployment_integration_tester"
                ],
                min_team_size=7,
                optimal_team_size=9,
                max_team_size=11,
                expected_duration_days=30,
                description="Medium feature with expanded team",
                scaling_policy="phase_based"
            ),

            ProjectType.COMPLEX_FEATURE: TeamComposition(
                project_type="complex_feature",
                required_personas=[
                    "requirement_analyst",
                    "solution_architect",
                    "backend_developer",
                    "frontend_developer",
                    "qa_engineer",
                    "security_specialist",
                    "ui_ux_designer",
                    "technical_writer",
                    "devops_engineer",
                    "deployment_specialist",
                    "deployment_integration_tester"
                ],
                optional_personas=[],
                min_team_size=11,
                optimal_team_size=11,
                max_team_size=11,
                expected_duration_days=60,
                description="Complex feature with full team",
                scaling_policy="phase_based"
            ),

            ProjectType.FULL_SDLC: TeamComposition(
                project_type="full_sdlc",
                required_personas=[
                    "requirement_analyst",
                    "solution_architect",
                    "backend_developer",
                    "frontend_developer",
                    "qa_engineer",
                    "security_specialist",
                    "ui_ux_designer",
                    "technical_writer",
                    "devops_engineer",
                    "deployment_specialist",
                    "deployment_integration_tester"
                ],
                optional_personas=[],
                min_team_size=11,
                optimal_team_size=11,
                max_team_size=11,
                expected_duration_days=90,
                description="Full SDLC with all personas",
                scaling_policy="phase_based"
            ),

            ProjectType.SECURITY_PATCH: TeamComposition(
                project_type="security_patch",
                required_personas=[
                    "security_specialist",
                    "backend_developer",
                    "qa_engineer",
                    "deployment_specialist"
                ],
                optional_personas=[
                    "solution_architect",
                    "devops_engineer"
                ],
                min_team_size=4,
                optimal_team_size=5,
                max_team_size=6,
                expected_duration_days=2,
                description="Emergency security patch",
                scaling_policy="fixed"
            ),

            ProjectType.EMERGENCY: TeamComposition(
                project_type="emergency",
                required_personas=[
                    "backend_developer",
                    "devops_engineer",
                    "deployment_specialist"
                ],
                optional_personas=[
                    "security_specialist",
                    "qa_engineer"
                ],
                min_team_size=3,
                optimal_team_size=4,
                max_team_size=5,
                expected_duration_days=1,
                description="Emergency response team",
                scaling_policy="fixed"
            )
        }

        return compositions.get(project_type, compositions[ProjectType.MEDIUM_FEATURE])

    @staticmethod
    def get_phase_requirements(phase: SDLCPhase) -> PhaseTeamRequirements:
        """
        Get team requirements for a specific SDLC phase

        Defines:
        - Who must be ACTIVE
        - Who can be ON_STANDBY
        - Who can be RETIRED from previous phase
        """
        phase_requirements = {
            SDLCPhase.REQUIREMENTS: PhaseTeamRequirements(
                phase=SDLCPhase.REQUIREMENTS,
                primary_personas=[
                    "requirement_analyst",
                    "ui_ux_designer"
                ],
                supporting_personas=[
                    "solution_architect",  # For feasibility
                    "security_specialist"  # For security requirements
                ],
                can_retire_from_previous_phase=[],
                description="Requirements gathering phase needs analyst and UX designer"
            ),

            SDLCPhase.DESIGN: PhaseTeamRequirements(
                phase=SDLCPhase.DESIGN,
                primary_personas=[
                    "solution_architect",
                    "security_specialist"
                ],
                supporting_personas=[
                    "requirement_analyst",  # For clarifications
                    "devops_engineer",      # For infrastructure design
                    "backend_developer",    # For architecture input
                    "frontend_developer"    # For architecture input
                ],
                can_retire_from_previous_phase=[
                    # Keep requirement_analyst on standby
                ],
                description="Design phase needs architect and security specialist"
            ),

            SDLCPhase.IMPLEMENTATION: PhaseTeamRequirements(
                phase=SDLCPhase.IMPLEMENTATION,
                primary_personas=[
                    "backend_developer",
                    "frontend_developer",
                    "devops_engineer"
                ],
                supporting_personas=[
                    "solution_architect",   # For guidance
                    "ui_ux_designer",       # For design questions
                    "security_specialist",  # For code review
                    "qa_engineer"           # For test prep
                ],
                can_retire_from_previous_phase=[
                    "requirement_analyst"  # Can move to standby
                ],
                description="Implementation needs developers and DevOps"
            ),

            SDLCPhase.TESTING: PhaseTeamRequirements(
                phase=SDLCPhase.TESTING,
                primary_personas=[
                    "qa_engineer",
                    "deployment_integration_tester",
                    "security_specialist"
                ],
                supporting_personas=[
                    "backend_developer",    # For bug fixes
                    "frontend_developer",   # For bug fixes
                    "requirement_analyst"   # For acceptance criteria
                ],
                can_retire_from_previous_phase=[
                    "ui_ux_designer"  # Design is done
                ],
                description="Testing needs QA, integration tester, and security"
            ),

            SDLCPhase.DEPLOYMENT: PhaseTeamRequirements(
                phase=SDLCPhase.DEPLOYMENT,
                primary_personas=[
                    "deployment_specialist",
                    "devops_engineer",
                    "deployment_integration_tester"
                ],
                supporting_personas=[
                    "backend_developer",    # For production support
                    "security_specialist",  # For security validation
                    "qa_engineer"           # For smoke testing
                ],
                can_retire_from_previous_phase=[
                    "solution_architect",  # Architecture is finalized
                    "frontend_developer"   # If no frontend issues
                ],
                description="Deployment needs specialists, DevOps, and testers"
            )
        }

        return phase_requirements.get(phase, PhaseRequirements(
            phase=phase,
            primary_personas=[],
            supporting_personas=[],
            can_retire_from_previous_phase=[],
            description=f"No specific requirements for {phase.value}"
        ))

    @staticmethod
    def get_minimum_viable_team(
        project_type: ProjectType
    ) -> List[str]:
        """Get absolutely minimum team to start project"""
        composition = TeamCompositionPolicy.get_composition_for_project(project_type)
        return composition.required_personas[:composition.min_team_size]

    @staticmethod
    def get_optimal_team(
        project_type: ProjectType
    ) -> List[str]:
        """Get optimal team for best results"""
        composition = TeamCompositionPolicy.get_composition_for_project(project_type)
        return composition.required_personas + composition.optional_personas[:composition.optimal_team_size - len(composition.required_personas)]

    @staticmethod
    def should_scale_team_for_phase(
        current_phase: SDLCPhase,
        current_team_personas: Set[str]
    ) -> Dict[str, Any]:
        """
        Determine if team should be scaled for a phase

        Returns:
            {
                "should_add": [persona_ids to add],
                "should_retire": [persona_ids to retire],
                "should_activate": [persona_ids to move from standby to active],
                "should_standby": [persona_ids to move from active to standby]
            }
        """
        phase_req = TeamCompositionPolicy.get_phase_requirements(current_phase)

        current_personas_set = set(current_team_personas)

        # Personas to add (primary that we don't have)
        should_add = [
            p for p in phase_req.primary_personas
            if p not in current_personas_set
        ]

        # Personas to retire (from previous phase)
        should_retire = [
            p for p in phase_req.can_retire_from_previous_phase
            if p in current_personas_set
        ]

        # Personas to activate (primary that we have but might be on standby)
        should_activate = [
            p for p in phase_req.primary_personas
            if p in current_personas_set
        ]

        # Personas to move to standby (not primary or supporting)
        all_needed = set(phase_req.primary_personas + phase_req.supporting_personas)
        should_standby = [
            p for p in current_personas_set
            if p not in all_needed and p not in phase_req.can_retire_from_previous_phase
        ]

        return {
            "should_add": should_add,
            "should_retire": should_retire,
            "should_activate": should_activate,
            "should_standby": should_standby,
            "description": phase_req.description
        }

    @staticmethod
    def get_scaling_policy_for_project(
        project_type: ProjectType
    ) -> str:
        """Get scaling policy for a project type"""
        composition = TeamCompositionPolicy.get_composition_for_project(project_type)
        return composition.scaling_policy

    @staticmethod
    def get_progressive_scaling_plan(
        start_size: int,
        target_project_type: ProjectType
    ) -> List[Dict[str, Any]]:
        """
        Get a plan to progressively scale from small team to target

        Example: Start with 2, scale to 4, then to full team

        Returns:
            List of scaling steps with personas to add at each step
        """
        composition = TeamCompositionPolicy.get_composition_for_project(target_project_type)

        all_personas = composition.required_personas + composition.optional_personas
        target_size = composition.optimal_team_size

        if start_size >= target_size:
            return []

        # Create scaling steps
        steps = []
        current_size = start_size
        current_personas = all_personas[:start_size]

        # Scale in increments of 2-3
        while current_size < target_size:
            next_size = min(current_size + 2, target_size)
            new_personas = all_personas[current_size:next_size]

            steps.append({
                "from_size": current_size,
                "to_size": next_size,
                "add_personas": new_personas,
                "reason": f"Scaling up by {next_size - current_size}",
                "trigger": "workload_increase" if len(steps) > 0 else "initial_scale"
            })

            current_size = next_size

        return steps


# Helper functions
def get_minimal_bug_fix_team() -> List[str]:
    """Absolute minimum team for bug fix"""
    return ["backend_developer", "qa_engineer"]


def get_minimal_feature_team() -> List[str]:
    """Minimum team for feature development"""
    return [
        "requirement_analyst",
        "solution_architect",
        "backend_developer",
        "frontend_developer",
        "qa_engineer"
    ]


def get_full_sdlc_team() -> List[str]:
    """Full SDLC team (all 11 personas)"""
    return [
        "requirement_analyst",
        "solution_architect",
        "backend_developer",
        "frontend_developer",
        "devops_engineer",
        "qa_engineer",
        "security_specialist",
        "ui_ux_designer",
        "technical_writer",
        "deployment_specialist",
        "deployment_integration_tester"
    ]


def get_emergency_response_team() -> List[str]:
    """Emergency response team"""
    return [
        "backend_developer",
        "devops_engineer",
        "deployment_specialist",
        "security_specialist"
    ]


if __name__ == "__main__":
    print("=" * 80)
    print("TEAM COMPOSITION POLICIES")
    print("=" * 80)

    policy = TeamCompositionPolicy()

    # Show compositions for different project types
    for proj_type in ProjectType:
        comp = policy.get_composition_for_project(proj_type)
        print(f"\n📋 {proj_type.value.upper()}")
        print(f"   Description: {comp.description}")
        print(f"   Required: {', '.join(comp.required_personas)}")
        print(f"   Optional: {', '.join(comp.optional_personas)}")
        print(f"   Team size: {comp.min_team_size}-{comp.optimal_team_size} (max: {comp.max_team_size})")
        print(f"   Duration: {comp.expected_duration_days} days")
        print(f"   Scaling: {comp.scaling_policy}")

    # Show phase requirements
    print(f"\n{'=' * 80}")
    print("PHASE-BASED TEAM REQUIREMENTS")
    print("=" * 80)

    for phase in [SDLCPhase.REQUIREMENTS, SDLCPhase.DESIGN, SDLCPhase.IMPLEMENTATION,
                  SDLCPhase.TESTING, SDLCPhase.DEPLOYMENT]:
        req = policy.get_phase_requirements(phase)
        print(f"\n📌 {phase.value.upper()}")
        print(f"   {req.description}")
        print(f"   Primary (ACTIVE): {', '.join(req.primary_personas)}")
        print(f"   Supporting (STANDBY): {', '.join(req.supporting_personas)}")
        if req.can_retire_from_previous_phase:
            print(f"   Can retire: {', '.join(req.can_retire_from_previous_phase)}")

    # Progressive scaling example
    print(f"\n{'=' * 80}")
    print("PROGRESSIVE SCALING EXAMPLE: 2 → 8 members")
    print("=" * 80)

    plan = policy.get_progressive_scaling_plan(2, ProjectType.MEDIUM_FEATURE)
    for i, step in enumerate(plan, 1):
        print(f"\nStep {i}: {step['from_size']} → {step['to_size']} members")
        print(f"   Add: {', '.join(step['add_personas'])}")
        print(f"   Trigger: {step['trigger']}")
