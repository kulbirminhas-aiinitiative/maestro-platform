"""
Maestro Document Templates - Block Library Templates Module

This module provides comprehensive document templates for all SDLC phases,
starting with Requirements Phase templates (MD-2515).

Templates Available:
- Requirements Phase (9 templates): BRD, User Stories, Acceptance Criteria,
  SRS, Project Charter, Stakeholder Analysis, RTM, Feasibility Study, Risk Assessment

Reference: MD-2515 Document Templates - Requirements Phase
"""

from .requirements import (
    # Models
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
    # Templates
    SoftwareRequirementsSpecTemplate,
    ProjectCharterTemplate,
    StakeholderAnalysisTemplate,
    RequirementsTraceabilityMatrixTemplate,
    FeasibilityStudyTemplate,
    RiskAssessmentTemplate,
    # Registry
    TemplateRegistry,
    get_requirements_templates,
)

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
