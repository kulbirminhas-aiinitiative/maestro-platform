"""
Persona University Service (MD-3127)

Main orchestrator for curricula, exams, and credential issuance.
"The Foundry builds the agent (Birth). The University trains the agent (Life)."

AC-1: A curriculum can be defined in YAML and loaded by PersonaUniversityService
AC-2: A "Fresh" agent cannot be hired for a "Senior" role without credentials
AC-5: Upon passing (>80%), the agent receives a VC
"""

from __future__ import annotations

import logging
import yaml
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, TYPE_CHECKING

from maestro_hive.university.credential_store import CredentialStore, VerifiableCredential
from maestro_hive.university.user_simulator import ExamScenario, ScenarioStep
from maestro_hive.university.exam_simulator import ExamSimulator, ExamResult, ExamGrade

if TYPE_CHECKING:
    from maestro_hive.governance import Enforcer, ReputationEngine, IdentityManager, GovernancePersistence

logger = logging.getLogger(__name__)


@dataclass
class CurriculumModule:
    """A module within a curriculum."""
    module_id: str
    name: str
    skills: List[str]
    exam_type: str  # e.g., "code_completion", "bug_fix", "design_review"
    time_limit_minutes: int = 60
    pass_threshold: float = 0.8


@dataclass
class Curriculum:
    """
    A complete curriculum definition (AC-1).

    Loaded from YAML files with the following structure:
    - Core (mandatory for all agents)
    - Major (specialization)
    - Electives (optional)
    """
    curriculum_id: str
    name: str
    curriculum_type: str  # core, major, elective
    prerequisites: List[str]
    modules: List[CurriculumModule]
    certification_name: str
    validity_days: int = 365
    revocable: bool = True

    @classmethod
    def from_yaml(cls, yaml_path: str) -> "Curriculum":
        """Load curriculum from YAML file (AC-1)."""
        with open(yaml_path, 'r') as f:
            data = yaml.safe_load(f)

        curriculum_data = data.get('curriculum', data)
        return cls(
            curriculum_id=curriculum_data.get('id', Path(yaml_path).stem),
            name=curriculum_data.get('name', 'Unnamed Curriculum'),
            curriculum_type=curriculum_data.get('type', 'elective'),
            prerequisites=curriculum_data.get('prerequisites', []),
            modules=[
                CurriculumModule(
                    module_id=mod.get('id', f"mod_{i}"),
                    name=mod.get('name', f"Module {i}"),
                    skills=mod.get('skills', []),
                    exam_type=mod.get('exam', {}).get('type', 'code_completion'),
                    time_limit_minutes=mod.get('exam', {}).get('time_limit_minutes', 60),
                    pass_threshold=mod.get('exam', {}).get('pass_threshold', 0.8),
                )
                for i, mod in enumerate(curriculum_data.get('modules', []))
            ],
            certification_name=curriculum_data.get('certification', {}).get('name', 'Unknown_Certification'),
            validity_days=curriculum_data.get('certification', {}).get('validity_days', 365),
            revocable=curriculum_data.get('certification', {}).get('revocable', True),
        )

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            'id': self.curriculum_id,
            'name': self.name,
            'type': self.curriculum_type,
            'prerequisites': self.prerequisites,
            'modules': [
                {
                    'id': mod.module_id,
                    'name': mod.name,
                    'skills': mod.skills,
                    'exam': {
                        'type': mod.exam_type,
                        'time_limit_minutes': mod.time_limit_minutes,
                        'pass_threshold': mod.pass_threshold,
                    }
                }
                for mod in self.modules
            ],
            'certification': {
                'name': self.certification_name,
                'validity_days': self.validity_days,
                'revocable': self.revocable,
            }
        }


class PersonaUniversityService:
    """
    Main service for managing agent education and accreditation.

    Responsibilities:
    - Manage Curricula (YAML definitions) - AC-1
    - Check hiring eligibility (credentials required) - AC-2
    - Schedule and run exams - AC-3, AC-4
    - Issue credentials on passing - AC-5
    - Integrate with Governance systems - AC-6, AC-7, AC-8
    """

    def __init__(
        self,
        enforcer: Optional["Enforcer"] = None,
        reputation_engine: Optional["ReputationEngine"] = None,
        identity_manager: Optional["IdentityManager"] = None,
        persistence: Optional["GovernancePersistence"] = None,
        curriculum_dir: str = "config/curriculums",
        default_policy_path: Optional[str] = None,
    ):
        """
        Initialize the Persona University.

        Args:
            enforcer: For policy enforcement during exams
            reputation_engine: For reputation updates
            identity_manager: For credential signing
            persistence: For credential storage
            curriculum_dir: Directory containing curriculum YAML files
            default_policy_path: Default policy to restore after exams
        """
        self._enforcer = enforcer
        self._reputation_engine = reputation_engine
        self._curriculum_dir = Path(curriculum_dir)

        # Initialize credential store (AC-5, AC-6, AC-9)
        self._credential_store = CredentialStore(
            identity_manager=identity_manager,
            persistence=persistence,
        )

        # Initialize exam simulator (AC-3, AC-4, AC-8)
        self._exam_simulator = ExamSimulator(
            enforcer=enforcer,
            reputation_engine=reputation_engine,
            default_policy_path=default_policy_path,
        )

        # Cache for loaded curricula
        self._curricula: Dict[str, Curriculum] = {}

        # Load all curricula from directory
        self._load_curricula()

        logger.info(f"PersonaUniversityService initialized with {len(self._curricula)} curricula")

    def _load_curricula(self) -> None:
        """Load all curricula from the curriculum directory (AC-1)."""
        if not self._curriculum_dir.exists():
            logger.warning(f"Curriculum directory not found: {self._curriculum_dir}")
            return

        for yaml_path in self._curriculum_dir.glob("*.yaml"):
            try:
                curriculum = Curriculum.from_yaml(str(yaml_path))
                self._curricula[curriculum.curriculum_id] = curriculum
                logger.debug(f"Loaded curriculum: {curriculum.curriculum_id}")
            except Exception as e:
                logger.error(f"Failed to load curriculum {yaml_path}: {e}")

    def load_curriculum(self, yaml_path: str) -> Curriculum:
        """
        Load a single curriculum from YAML (AC-1).

        Args:
            yaml_path: Path to curriculum YAML file

        Returns:
            Loaded Curriculum object
        """
        curriculum = Curriculum.from_yaml(yaml_path)
        self._curricula[curriculum.curriculum_id] = curriculum
        logger.info(f"Loaded curriculum: {curriculum.name}")
        return curriculum

    def get_curriculum(self, curriculum_id: str) -> Optional[Curriculum]:
        """Get a curriculum by ID."""
        return self._curricula.get(curriculum_id)

    def list_curricula(self) -> List[Curriculum]:
        """List all available curricula."""
        return list(self._curricula.values())

    def check_hiring_eligibility(
        self,
        agent_id: str,
        required_role: str,
        required_credentials: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Check if an agent is eligible for a role (AC-2).

        A "Fresh" agent cannot be hired for a "Senior" role without credentials.

        Args:
            agent_id: Agent to check
            required_role: Role being considered
            required_credentials: List of required credential types

        Returns:
            Dict with 'eligible', 'missing_credentials', 'current_credentials'
        """
        current_credentials = self._credential_store.get_agent_credentials(agent_id, valid_only=True)
        current_types = {c.credential_type for c in current_credentials}

        required = required_credentials or []
        missing = [cred for cred in required if cred not in current_types]

        eligible = len(missing) == 0

        result = {
            'agent_id': agent_id,
            'role': required_role,
            'eligible': eligible,
            'current_credentials': [c.credential_type for c in current_credentials],
            'required_credentials': required,
            'missing_credentials': missing,
        }

        if not eligible:
            logger.info(f"Agent {agent_id} not eligible for {required_role}: missing {missing}")
        else:
            logger.debug(f"Agent {agent_id} eligible for {required_role}")

        return result

    def schedule_exam(
        self,
        agent_id: str,
        curriculum_id: str,
        module_id: Optional[str] = None,
        scenario_override: Optional[ExamScenario] = None,
    ) -> Optional[ExamScenario]:
        """
        Schedule an exam for an agent (AC-3).

        Args:
            agent_id: Agent taking the exam
            curriculum_id: Curriculum for the exam
            module_id: Specific module (or all modules if None)
            scenario_override: Custom scenario to use

        Returns:
            ExamScenario to be executed, or None if not found
        """
        if scenario_override:
            return scenario_override

        curriculum = self.get_curriculum(curriculum_id)
        if not curriculum:
            logger.error(f"Curriculum not found: {curriculum_id}")
            return None

        # Check prerequisites
        for prereq in curriculum.prerequisites:
            if not self._credential_store.has_credential(agent_id, prereq):
                logger.warning(f"Agent {agent_id} missing prerequisite: {prereq}")
                return None

        # Get module or use first module
        if module_id:
            module = next((m for m in curriculum.modules if m.module_id == module_id), None)
        else:
            module = curriculum.modules[0] if curriculum.modules else None

        if not module:
            logger.error(f"Module not found in curriculum: {module_id}")
            return None

        # Create exam scenario from module
        scenario = ExamScenario(
            scenario_id=f"{curriculum_id}_{module.module_id}",
            name=f"{curriculum.name}: {module.name}",
            description=f"Exam for {', '.join(module.skills)}",
            difficulty=self._infer_difficulty(curriculum),
            max_total_time_minutes=module.time_limit_minutes,
            passing_score=module.pass_threshold,
            steps=[
                ScenarioStep(
                    step_id=0,
                    user_input=self._generate_exam_prompt(module),
                    expected_behavior=f"Demonstrate {', '.join(module.skills)}",
                    success_criteria=[f"Correct use of {skill}" for skill in module.skills],
                    timeout_seconds=module.time_limit_minutes * 60,
                )
            ]
        )

        logger.info(f"Scheduled exam {scenario.scenario_id} for agent {agent_id}")
        return scenario

    def run_exam(
        self,
        agent_id: str,
        scenario: ExamScenario,
        agent_response_callback: Callable[[str], str],
    ) -> ExamResult:
        """
        Execute an exam for an agent (AC-3, AC-4).

        Args:
            agent_id: Agent taking the exam
            scenario: Exam scenario to run
            agent_response_callback: Function that produces agent responses

        Returns:
            ExamResult with full metrics
        """
        result = self._exam_simulator.run_exam(
            agent_id=agent_id,
            scenario=scenario,
            agent_response_callback=agent_response_callback,
        )

        # Issue credential if passed (AC-5)
        if result.passed and result.credential_type:
            self._issue_credential(
                agent_id=agent_id,
                credential_type=result.credential_type,
                exam_id=result.exam_id,
                exam_score=result.final_score,
            )

        return result

    def _issue_credential(
        self,
        agent_id: str,
        credential_type: str,
        exam_id: str,
        exam_score: float,
    ) -> VerifiableCredential:
        """Issue a credential to an agent (AC-5)."""
        credential = self._credential_store.issue_credential(
            agent_id=agent_id,
            credential_type=credential_type,
            exam_id=exam_id,
            exam_score=exam_score,
        )
        logger.info(f"Issued credential {credential.credential_id} ({credential_type}) to {agent_id}")
        return credential

    def get_agent_credentials(self, agent_id: str) -> List[VerifiableCredential]:
        """Get all valid credentials for an agent."""
        return self._credential_store.get_agent_credentials(agent_id, valid_only=True)

    def verify_credential(self, credential: VerifiableCredential) -> bool:
        """Verify a credential is valid."""
        return self._credential_store.verify_credential(credential)

    def revoke_credential(self, credential_id: str, reason: str = "") -> bool:
        """Revoke a credential."""
        return self._credential_store.revoke_credential(credential_id, reason)

    def _infer_difficulty(self, curriculum: Curriculum) -> str:
        """Infer difficulty from curriculum type."""
        difficulty_map = {
            'core': 'easy',
            'major': 'medium',
            'elective': 'medium',
        }
        return difficulty_map.get(curriculum.curriculum_type, 'medium')

    def _generate_exam_prompt(self, module: CurriculumModule) -> str:
        """Generate an exam prompt for a module."""
        prompt_templates = {
            'code_completion': f"Complete the following Python code to demonstrate {', '.join(module.skills)}:",
            'bug_fix': f"The following code has bugs related to {', '.join(module.skills)}. Fix them:",
            'design_review': f"Review the following design for {', '.join(module.skills)} and suggest improvements:",
            'code_review': f"Review this code for best practices in {', '.join(module.skills)}:",
        }
        return prompt_templates.get(
            module.exam_type,
            f"Demonstrate your knowledge of {', '.join(module.skills)}:"
        )

    def get_exam_history(self, agent_id: str) -> List[Dict[str, Any]]:
        """
        Get exam history for an agent (supports AC-10 frontend).

        Returns list of exam results with credentials earned.
        """
        credentials = self._credential_store.get_agent_credentials(agent_id, valid_only=False)
        return [
            {
                'credential_id': c.credential_id,
                'credential_type': c.credential_type,
                'exam_id': c.exam_id,
                'exam_score': c.exam_score,
                'issued_at': c.issued_at.isoformat(),
                'status': c.status.value,
                'is_valid': self._credential_store.verify_credential(c),
            }
            for c in credentials
        ]
