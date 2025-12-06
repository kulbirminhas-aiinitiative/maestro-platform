"""
Project Charter Template

Formal project charter document template with:
- Standard PMI-aligned sections
- Persona mapping (PM, Stakeholders, Sponsor)
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


class ProjectCharterTemplate(DocumentTemplate):
    """
    Project Charter template following PMI best practices.

    Covers:
    - Project purpose and justification
    - Objectives and success criteria
    - High-level requirements
    - Project scope and boundaries
    - Stakeholder identification
    """

    def __init__(self):
        super().__init__(
            template_id="tpl_charter",
            name="Project Charter",
            description="PMI-aligned project charter template for formally authorizing projects",
            phase="requirements",
            version="1.0.0",
            sections=self._create_sections(),
            variables=self._create_variables(),
            personas=self._create_personas(),
            quality_config=self._create_quality_config(),
            metadata={
                "standard": "PMBOK",
                "category": "requirements",
                "audience": ["sponsors", "stakeholders", "project_team"],
            },
        )

    def _create_sections(self) -> list:
        """Create project charter sections."""
        return [
            TemplateSection(
                section_id="charter_header",
                title="1. Project Information",
                description="Basic project identification and authorization information.",
                required=True,
                order=1,
                subsections=[
                    TemplateSection(
                        section_id="charter_title",
                        title="1.1 Project Title",
                        description="{{project_name}}",
                        required=True,
                        order=1,
                    ),
                    TemplateSection(
                        section_id="charter_sponsor",
                        title="1.2 Project Sponsor",
                        description="{{sponsor_name}} - {{sponsor_title}}",
                        required=True,
                        order=2,
                    ),
                    TemplateSection(
                        section_id="charter_pm",
                        title="1.3 Project Manager",
                        description="{{project_manager}} - Authority level: {{authority_level}}",
                        required=True,
                        order=3,
                    ),
                ],
            ),
            TemplateSection(
                section_id="charter_purpose",
                title="2. Project Purpose and Justification",
                description="Why this project is being undertaken.",
                required=True,
                order=2,
                subsections=[
                    TemplateSection(
                        section_id="charter_business_need",
                        title="2.1 Business Need",
                        description="The business problem or opportunity this project addresses.",
                        required=True,
                        order=1,
                        prompts=[
                            TemplatePrompt(
                                prompt_id="business_need_prompt",
                                text="Describe the business need for {{project_name}}. Focus on the problem being solved or opportunity being captured.",
                                context_variables=["project_name"],
                            ),
                        ],
                    ),
                    TemplateSection(
                        section_id="charter_business_case",
                        title="2.2 Business Case Summary",
                        description="High-level ROI and strategic alignment justification.",
                        required=True,
                        order=2,
                    ),
                ],
            ),
            TemplateSection(
                section_id="charter_objectives",
                title="3. Project Objectives and Success Criteria",
                description="Measurable objectives and how success will be determined.",
                required=True,
                order=3,
                subsections=[
                    TemplateSection(
                        section_id="charter_goals",
                        title="3.1 Project Goals",
                        description="High-level goals the project aims to achieve.",
                        required=True,
                        order=1,
                    ),
                    TemplateSection(
                        section_id="charter_success_criteria",
                        title="3.2 Success Criteria",
                        description="Measurable criteria for determining project success.",
                        required=True,
                        order=2,
                    ),
                ],
            ),
            TemplateSection(
                section_id="charter_scope",
                title="4. Project Scope",
                description="What is included and excluded from the project.",
                required=True,
                order=4,
                subsections=[
                    TemplateSection(
                        section_id="charter_in_scope",
                        title="4.1 In Scope",
                        description="Major deliverables and work included in the project.",
                        required=True,
                        order=1,
                    ),
                    TemplateSection(
                        section_id="charter_out_scope",
                        title="4.2 Out of Scope",
                        description="Explicitly excluded items to prevent scope creep.",
                        required=True,
                        order=2,
                    ),
                ],
            ),
            TemplateSection(
                section_id="charter_requirements",
                title="5. High-Level Requirements",
                description="Summary of major requirements from stakeholders.",
                required=True,
                order=5,
                prompts=[
                    TemplatePrompt(
                        prompt_id="high_level_req_prompt",
                        text="Summarize high-level requirements for {{project_name}} from the following stakeholder input: {{stakeholder_requirements}}",
                        context_variables=["project_name", "stakeholder_requirements"],
                    ),
                ],
            ),
            TemplateSection(
                section_id="charter_milestones",
                title="6. Summary Milestones",
                description="High-level project milestones and target dates.",
                required=True,
                order=6,
            ),
            TemplateSection(
                section_id="charter_budget",
                title="7. Summary Budget",
                description="High-level budget allocation and funding source.",
                required=True,
                order=7,
            ),
            TemplateSection(
                section_id="charter_stakeholders",
                title="8. Key Stakeholders",
                description="Identification of key project stakeholders.",
                required=True,
                order=8,
            ),
            TemplateSection(
                section_id="charter_risks",
                title="9. High-Level Risks",
                description="Major risks identified at project initiation.",
                required=True,
                order=9,
            ),
            TemplateSection(
                section_id="charter_approval",
                title="10. Approval Signatures",
                description="Formal authorization signatures from sponsor and key stakeholders.",
                required=True,
                order=10,
            ),
        ]

    def _create_variables(self) -> list:
        """Create template variables."""
        return [
            TemplateVariable(
                name="project_name",
                description="Official project name",
                var_type="string",
                required=True,
            ),
            TemplateVariable(
                name="version",
                description="Charter version",
                var_type="string",
                required=True,
                default_value="1.0",
            ),
            TemplateVariable(
                name="sponsor_name",
                description="Executive sponsor name",
                var_type="string",
                required=True,
            ),
            TemplateVariable(
                name="sponsor_title",
                description="Executive sponsor title",
                var_type="string",
                required=True,
            ),
            TemplateVariable(
                name="project_manager",
                description="Assigned project manager",
                var_type="string",
                required=True,
            ),
            TemplateVariable(
                name="authority_level",
                description="PM authority level (Low/Medium/High)",
                var_type="string",
                required=False,
                default_value="Medium",
            ),
            TemplateVariable(
                name="stakeholder_requirements",
                description="Summary of stakeholder requirements",
                var_type="list",
                required=False,
                default_value=[],
            ),
            TemplateVariable(
                name="budget",
                description="Approved budget amount",
                var_type="number",
                required=False,
            ),
            TemplateVariable(
                name="target_completion",
                description="Target completion date",
                var_type="date",
                required=False,
            ),
        ]

    def _create_personas(self) -> dict:
        """Create persona mappings (AC-3)."""
        return {
            PersonaRole.CREATOR: PersonaMapping(
                role=PersonaRole.CREATOR,
                title="Project Manager",
                responsibilities=[
                    "Draft project charter",
                    "Gather stakeholder input",
                    "Define project scope and objectives",
                    "Identify high-level risks",
                ],
                required_skills=[
                    "Project management",
                    "Stakeholder communication",
                    "Business analysis",
                    "Documentation",
                ],
                approval_weight=0.3,
            ),
            PersonaRole.REVIEWER: PersonaMapping(
                role=PersonaRole.REVIEWER,
                title="Key Stakeholders",
                responsibilities=[
                    "Review project scope",
                    "Validate requirements coverage",
                    "Confirm resource availability",
                    "Identify additional risks",
                ],
                required_skills=[
                    "Domain expertise",
                    "Resource planning",
                    "Risk identification",
                ],
                approval_weight=0.3,
            ),
            PersonaRole.APPROVER: PersonaMapping(
                role=PersonaRole.APPROVER,
                title="Executive Sponsor",
                responsibilities=[
                    "Authorize project initiation",
                    "Approve budget and resources",
                    "Provide executive oversight",
                    "Remove organizational barriers",
                ],
                required_skills=[
                    "Executive leadership",
                    "Strategic decision-making",
                    "Budget authority",
                ],
                approval_weight=1.0,
            ),
        }

    def _create_quality_config(self) -> QualityScoringConfig:
        """Create quality scoring configuration (AC-4)."""
        return QualityScoringConfig(
            completeness_weight=30.0,
            consistency_weight=20.0,
            clarity_weight=25.0,
            traceability_weight=25.0,
            pass_threshold=70.0,
            required_sections=[
                "charter_header",
                "charter_purpose",
                "charter_objectives",
                "charter_scope",
                "charter_requirements",
                "charter_approval",
            ],
            terminology_glossary={
                "project": "project",
                "deliverable": "deliverable",
            },
        )
