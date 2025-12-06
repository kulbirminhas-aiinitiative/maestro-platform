"""
Requirements Phase Document Templates

This module provides 9 document templates for Phase 1 (Requirements and Planning):
- 3 existing templates (BRD, User Stories, Acceptance Criteria)
- 6 new templates (SRS, Project Charter, Stakeholder Analysis, RTM, Feasibility, Risk)

Each template includes:
- Sections with prompts and variables (AC-2)
- Persona mapping for Creator/Reviewer/Approver (AC-3)
- Quality scoring metadata (AC-4)

Reference: MD-2515 Document Templates - Requirements Phase
"""

from .models import (
    TemplateSection,
    TemplatePrompt,
    TemplateVariable,
    PersonaRole,
    PersonaMapping,
    QualityScore,
    QualityScoringConfig,
    DocumentTemplate,
    RenderedDocument,
    ValidationResult,
)
from .srs_template import SoftwareRequirementsSpecTemplate
from .charter_template import ProjectCharterTemplate
from .stakeholder_template import StakeholderAnalysisTemplate
from .rtm_template import RequirementsTraceabilityMatrixTemplate
from .feasibility_template import FeasibilityStudyTemplate
from .risk_template import RiskAssessmentTemplate
from .registry import TemplateRegistry, get_requirements_templates

__all__ = [
    # Models
    "TemplateSection",
    "TemplatePrompt",
    "TemplateVariable",
    "PersonaRole",
    "PersonaMapping",
    "QualityScore",
    "QualityScoringConfig",
    "DocumentTemplate",
    "RenderedDocument",
    "ValidationResult",
    # Templates
    "SoftwareRequirementsSpecTemplate",
    "ProjectCharterTemplate",
    "StakeholderAnalysisTemplate",
    "RequirementsTraceabilityMatrixTemplate",
    "FeasibilityStudyTemplate",
    "RiskAssessmentTemplate",
    # Registry
    "TemplateRegistry",
    "get_requirements_templates",
]
