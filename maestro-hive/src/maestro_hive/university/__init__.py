"""
Persona University Module (MD-3127)

The Evolution & Accreditation System for AI agents.
"The Foundry builds the agent (Birth). The University trains the agent (Life)."

Components:
- PersonaUniversityService: Main orchestrator for curricula and exams
- CredentialStore: Manages Verifiable Credentials (VCs)
- UserSimulatorAgent: Simulates user behavior for exam scenarios
- ExamSimulator: Sandboxed exam execution environment
"""

from maestro_hive.university.credential_store import (
    CredentialStore,
    CredentialStatus,
    VerifiableCredential,
)
from maestro_hive.university.user_simulator import (
    UserSimulatorAgent,
    ExamScenario,
    ScenarioStep,
)
from maestro_hive.university.exam_simulator import (
    ExamSimulator,
    ExamResult,
    ExamGrade,
)
from maestro_hive.university.persona_university_service import (
    PersonaUniversityService,
    Curriculum,
    CurriculumModule,
)

__all__ = [
    # Main Service
    "PersonaUniversityService",
    "Curriculum",
    "CurriculumModule",
    # Credentials
    "CredentialStore",
    "CredentialStatus",
    "VerifiableCredential",
    # Simulator
    "UserSimulatorAgent",
    "ExamScenario",
    "ScenarioStep",
    # Exam
    "ExamSimulator",
    "ExamResult",
    "ExamGrade",
]
