"""
Software Requirements Specification (SRS) Template

IEEE 830-1998 compliant SRS template with:
- Comprehensive sections for functional/non-functional requirements
- Persona mapping (Systems Analyst, Tech Lead, Architect)
- Quality scoring metadata

Reference: MD-2515 AC-1, AC-2, AC-3, AC-4
"""

from .models import (
    DocumentTemplate,
    TemplateSection,
    TemplatePrompt,
    TemplateVariable,
    PersonaRole,
    PersonaMapping,
    QualityScoringConfig,
)


class SoftwareRequirementsSpecTemplate(DocumentTemplate):
    """
    Software Requirements Specification template following IEEE 830-1998.

    Covers:
    - System overview and scope
    - Functional requirements
    - Non-functional requirements
    - External interfaces
    - System constraints
    """

    def __init__(self):
        super().__init__(
            template_id="tpl_srs",
            name="Software Requirements Specification",
            description="IEEE 830-1998 compliant SRS document template for capturing functional and non-functional requirements",
            phase="requirements",
            version="1.0.0",
            sections=self._create_sections(),
            variables=self._create_variables(),
            personas=self._create_personas(),
            quality_config=self._create_quality_config(),
            metadata={
                "standard": "IEEE 830-1998",
                "category": "requirements",
                "audience": ["developers", "architects", "qa"],
            },
        )

    def _create_sections(self) -> list:
        """Create SRS document sections."""
        return [
            TemplateSection(
                section_id="srs_intro",
                title="1. Introduction",
                description="Overview of the software requirements specification document.",
                required=True,
                order=1,
                subsections=[
                    TemplateSection(
                        section_id="srs_purpose",
                        title="1.1 Purpose",
                        description="Describe the purpose of this SRS and its intended audience. This document specifies requirements for {{project_name}}.",
                        required=True,
                        order=1,
                        prompts=[
                            TemplatePrompt(
                                prompt_id="purpose_prompt",
                                text="Write a clear purpose statement for an SRS document for {{project_name}}. Include intended audience and document scope.",
                                context_variables=["project_name"],
                            ),
                        ],
                    ),
                    TemplateSection(
                        section_id="srs_scope",
                        title="1.2 Scope",
                        description="Define the scope of the software system, including benefits and objectives.",
                        required=True,
                        order=2,
                    ),
                    TemplateSection(
                        section_id="srs_definitions",
                        title="1.3 Definitions, Acronyms, and Abbreviations",
                        description="Define all terms and acronyms used in this document.",
                        required=True,
                        order=3,
                    ),
                    TemplateSection(
                        section_id="srs_references",
                        title="1.4 References",
                        description="List all referenced documents including BRD, user stories, and standards.",
                        required=False,
                        order=4,
                    ),
                    TemplateSection(
                        section_id="srs_overview",
                        title="1.5 Overview",
                        description="Describe the organization and contents of the remainder of this document.",
                        required=True,
                        order=5,
                    ),
                ],
            ),
            TemplateSection(
                section_id="srs_overall_desc",
                title="2. Overall Description",
                description="High-level description of the software and its context.",
                required=True,
                order=2,
                subsections=[
                    TemplateSection(
                        section_id="srs_product_perspective",
                        title="2.1 Product Perspective",
                        description="Describe the product in context of larger systems. Include system interfaces, user interfaces, hardware interfaces, software interfaces, communication interfaces, and memory constraints.",
                        required=True,
                        order=1,
                    ),
                    TemplateSection(
                        section_id="srs_product_functions",
                        title="2.2 Product Functions",
                        description="Summarize the major functions the software will perform.",
                        required=True,
                        order=2,
                    ),
                    TemplateSection(
                        section_id="srs_user_characteristics",
                        title="2.3 User Characteristics",
                        description="Describe the general characteristics of the intended users including education level, experience, and technical expertise.",
                        required=True,
                        order=3,
                    ),
                    TemplateSection(
                        section_id="srs_constraints",
                        title="2.4 Constraints",
                        description="Describe any constraints that will affect the developers' options.",
                        required=True,
                        order=4,
                    ),
                    TemplateSection(
                        section_id="srs_assumptions",
                        title="2.5 Assumptions and Dependencies",
                        description="List any assumed factors and external dependencies.",
                        required=True,
                        order=5,
                    ),
                ],
            ),
            TemplateSection(
                section_id="srs_specific_req",
                title="3. Specific Requirements",
                description="Detailed software requirements organized by type.",
                required=True,
                order=3,
                subsections=[
                    TemplateSection(
                        section_id="srs_external_interfaces",
                        title="3.1 External Interfaces",
                        description="Detailed description of all inputs and outputs.",
                        required=True,
                        order=1,
                    ),
                    TemplateSection(
                        section_id="srs_functional_req",
                        title="3.2 Functional Requirements",
                        description="Detailed functional requirements with unique identifiers (FR-XXX). Each requirement should be testable and traceable.",
                        required=True,
                        order=2,
                        prompts=[
                            TemplatePrompt(
                                prompt_id="functional_req_prompt",
                                text="Generate functional requirements for {{project_name}} based on the following user stories: {{user_stories}}. Format each as FR-XXX: Description.",
                                context_variables=["project_name", "user_stories"],
                            ),
                        ],
                    ),
                    TemplateSection(
                        section_id="srs_nonfunctional_req",
                        title="3.3 Non-Functional Requirements",
                        description="Performance, security, reliability, and other quality requirements (NFR-XXX).",
                        required=True,
                        order=3,
                        subsections=[
                            TemplateSection(
                                section_id="srs_performance",
                                title="3.3.1 Performance Requirements",
                                description="Response times, throughput, capacity requirements.",
                                required=True,
                                order=1,
                            ),
                            TemplateSection(
                                section_id="srs_security",
                                title="3.3.2 Security Requirements",
                                description="Authentication, authorization, data protection requirements.",
                                required=True,
                                order=2,
                            ),
                            TemplateSection(
                                section_id="srs_reliability",
                                title="3.3.3 Reliability Requirements",
                                description="Availability, mean time between failures, recovery requirements.",
                                required=True,
                                order=3,
                            ),
                            TemplateSection(
                                section_id="srs_maintainability",
                                title="3.3.4 Maintainability Requirements",
                                description="Coding standards, documentation, modularity requirements.",
                                required=False,
                                order=4,
                            ),
                        ],
                    ),
                    TemplateSection(
                        section_id="srs_design_constraints",
                        title="3.4 Design Constraints",
                        description="Standards compliance, hardware limitations, and other design constraints.",
                        required=False,
                        order=4,
                    ),
                ],
            ),
            TemplateSection(
                section_id="srs_appendices",
                title="4. Appendices",
                description="Supporting information including models, analysis, and additional details.",
                required=False,
                order=4,
            ),
        ]

    def _create_variables(self) -> list:
        """Create template variables."""
        return [
            TemplateVariable(
                name="project_name",
                description="Name of the software project",
                var_type="string",
                required=True,
            ),
            TemplateVariable(
                name="version",
                description="Document version number",
                var_type="string",
                required=True,
                default_value="1.0",
            ),
            TemplateVariable(
                name="author",
                description="Document author name",
                var_type="string",
                required=True,
            ),
            TemplateVariable(
                name="stakeholders",
                description="List of project stakeholders",
                var_type="list",
                required=False,
                default_value=[],
            ),
            TemplateVariable(
                name="user_stories",
                description="List of user stories to derive requirements from",
                var_type="list",
                required=False,
                default_value=[],
            ),
            TemplateVariable(
                name="brd_reference",
                description="Reference to Business Requirements Document",
                var_type="string",
                required=False,
            ),
        ]

    def _create_personas(self) -> dict:
        """Create persona mappings (AC-3)."""
        return {
            PersonaRole.CREATOR: PersonaMapping(
                role=PersonaRole.CREATOR,
                title="Systems Analyst",
                responsibilities=[
                    "Gather and document requirements",
                    "Translate business needs to technical specifications",
                    "Maintain requirements traceability",
                    "Coordinate with stakeholders",
                ],
                required_skills=[
                    "Requirements engineering",
                    "Technical writing",
                    "System analysis",
                    "Stakeholder management",
                ],
                approval_weight=0.5,
            ),
            PersonaRole.REVIEWER: PersonaMapping(
                role=PersonaRole.REVIEWER,
                title="Technical Lead",
                responsibilities=[
                    "Review technical feasibility",
                    "Validate completeness",
                    "Identify gaps and ambiguities",
                    "Ensure alignment with architecture",
                ],
                required_skills=[
                    "Software architecture",
                    "Technical review",
                    "Risk assessment",
                ],
                approval_weight=0.3,
            ),
            PersonaRole.APPROVER: PersonaMapping(
                role=PersonaRole.APPROVER,
                title="Solution Architect",
                responsibilities=[
                    "Final approval of requirements",
                    "Ensure alignment with enterprise architecture",
                    "Sign-off for implementation",
                ],
                required_skills=[
                    "Enterprise architecture",
                    "Strategic planning",
                    "Technical governance",
                ],
                approval_weight=1.0,
            ),
        }

    def _create_quality_config(self) -> QualityScoringConfig:
        """Create quality scoring configuration (AC-4)."""
        return QualityScoringConfig(
            completeness_weight=25.0,
            consistency_weight=25.0,
            clarity_weight=25.0,
            traceability_weight=25.0,
            pass_threshold=70.0,
            required_sections=[
                "srs_intro",
                "srs_overall_desc",
                "srs_specific_req",
                "srs_functional_req",
                "srs_nonfunctional_req",
            ],
            terminology_glossary={
                "shall": "shall",  # Mandatory requirement
                "should": "should",  # Recommended
                "may": "may",  # Optional
            },
        )
