"""
Stakeholder Analysis Template

Comprehensive stakeholder analysis document with:
- Stakeholder identification and classification
- Power/Interest matrix mapping
- Communication strategy
- Persona mapping (BA, PM, Sponsor)

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


class StakeholderAnalysisTemplate(DocumentTemplate):
    """
    Stakeholder Analysis template for comprehensive stakeholder management.

    Covers:
    - Stakeholder identification
    - Classification and prioritization
    - Power/Interest analysis
    - Engagement strategies
    - Communication planning
    """

    def __init__(self):
        super().__init__(
            template_id="tpl_stakeholder",
            name="Stakeholder Analysis",
            description="Comprehensive stakeholder analysis template for identifying and managing project stakeholders",
            phase="requirements",
            version="1.0.0",
            sections=self._create_sections(),
            variables=self._create_variables(),
            personas=self._create_personas(),
            quality_config=self._create_quality_config(),
            metadata={
                "category": "requirements",
                "audience": ["project_managers", "business_analysts", "sponsors"],
            },
        )

    def _create_sections(self) -> list:
        """Create stakeholder analysis sections."""
        return [
            TemplateSection(
                section_id="sh_intro",
                title="1. Introduction",
                description="Overview of the stakeholder analysis for {{project_name}}.",
                required=True,
                order=1,
                subsections=[
                    TemplateSection(
                        section_id="sh_purpose",
                        title="1.1 Purpose",
                        description="This document identifies and analyzes all stakeholders for {{project_name}} to ensure effective engagement and communication throughout the project lifecycle.",
                        required=True,
                        order=1,
                    ),
                    TemplateSection(
                        section_id="sh_scope",
                        title="1.2 Scope",
                        description="Scope of stakeholder identification and analysis efforts.",
                        required=True,
                        order=2,
                    ),
                ],
            ),
            TemplateSection(
                section_id="sh_identification",
                title="2. Stakeholder Identification",
                description="Complete list of identified stakeholders.",
                required=True,
                order=2,
                subsections=[
                    TemplateSection(
                        section_id="sh_internal",
                        title="2.1 Internal Stakeholders",
                        description="Stakeholders within the organization including executives, departments, and team members.",
                        required=True,
                        order=1,
                        prompts=[
                            TemplatePrompt(
                                prompt_id="internal_sh_prompt",
                                text="Identify internal stakeholders for {{project_name}} including their roles, departments, and initial assessment of their interest level.",
                                context_variables=["project_name"],
                            ),
                        ],
                    ),
                    TemplateSection(
                        section_id="sh_external",
                        title="2.2 External Stakeholders",
                        description="Stakeholders outside the organization including customers, vendors, regulators, and partners.",
                        required=True,
                        order=2,
                    ),
                ],
            ),
            TemplateSection(
                section_id="sh_classification",
                title="3. Stakeholder Classification",
                description="Categorization of stakeholders by type and role.",
                required=True,
                order=3,
                subsections=[
                    TemplateSection(
                        section_id="sh_primary",
                        title="3.1 Primary Stakeholders",
                        description="Stakeholders directly affected by project outcomes.",
                        required=True,
                        order=1,
                    ),
                    TemplateSection(
                        section_id="sh_secondary",
                        title="3.2 Secondary Stakeholders",
                        description="Stakeholders indirectly affected or with supporting roles.",
                        required=True,
                        order=2,
                    ),
                    TemplateSection(
                        section_id="sh_key",
                        title="3.3 Key Stakeholders",
                        description="Critical stakeholders with decision-making authority or significant influence.",
                        required=True,
                        order=3,
                    ),
                ],
            ),
            TemplateSection(
                section_id="sh_power_interest",
                title="4. Power/Interest Matrix",
                description="Analysis of stakeholder power and interest levels.",
                required=True,
                order=4,
                subsections=[
                    TemplateSection(
                        section_id="sh_high_power_high_interest",
                        title="4.1 Manage Closely (High Power, High Interest)",
                        description="Stakeholders requiring active engagement and frequent communication.",
                        required=True,
                        order=1,
                    ),
                    TemplateSection(
                        section_id="sh_high_power_low_interest",
                        title="4.2 Keep Satisfied (High Power, Low Interest)",
                        description="Stakeholders to keep informed and satisfied without overwhelming.",
                        required=True,
                        order=2,
                    ),
                    TemplateSection(
                        section_id="sh_low_power_high_interest",
                        title="4.3 Keep Informed (Low Power, High Interest)",
                        description="Stakeholders to keep adequately informed and use as advisors.",
                        required=True,
                        order=3,
                    ),
                    TemplateSection(
                        section_id="sh_low_power_low_interest",
                        title="4.4 Monitor (Low Power, Low Interest)",
                        description="Stakeholders requiring minimal effort with periodic monitoring.",
                        required=True,
                        order=4,
                    ),
                ],
            ),
            TemplateSection(
                section_id="sh_analysis",
                title="5. Detailed Stakeholder Analysis",
                description="In-depth analysis of each key stakeholder.",
                required=True,
                order=5,
                prompts=[
                    TemplatePrompt(
                        prompt_id="detailed_analysis_prompt",
                        text="For each key stakeholder in {{project_name}}, analyze: expectations, potential concerns, influence on project success, and recommended engagement approach.",
                        context_variables=["project_name"],
                    ),
                ],
            ),
            TemplateSection(
                section_id="sh_engagement",
                title="6. Engagement Strategy",
                description="Strategies for engaging different stakeholder groups.",
                required=True,
                order=6,
                subsections=[
                    TemplateSection(
                        section_id="sh_engagement_plan",
                        title="6.1 Engagement Plan",
                        description="Specific engagement activities for each stakeholder group.",
                        required=True,
                        order=1,
                    ),
                    TemplateSection(
                        section_id="sh_resistance",
                        title="6.2 Managing Resistance",
                        description="Strategies for addressing stakeholder resistance or concerns.",
                        required=True,
                        order=2,
                    ),
                ],
            ),
            TemplateSection(
                section_id="sh_communication",
                title="7. Communication Plan",
                description="Communication approach for each stakeholder group.",
                required=True,
                order=7,
                subsections=[
                    TemplateSection(
                        section_id="sh_comm_matrix",
                        title="7.1 Communication Matrix",
                        description="Stakeholder, information needs, frequency, method, and responsible party.",
                        required=True,
                        order=1,
                    ),
                    TemplateSection(
                        section_id="sh_comm_channels",
                        title="7.2 Communication Channels",
                        description="Available communication channels and when to use each.",
                        required=True,
                        order=2,
                    ),
                ],
            ),
            TemplateSection(
                section_id="sh_appendix",
                title="8. Appendices",
                description="Supporting materials including templates and tools.",
                required=False,
                order=8,
            ),
        ]

    def _create_variables(self) -> list:
        """Create template variables."""
        return [
            TemplateVariable(
                name="project_name",
                description="Name of the project",
                var_type="string",
                required=True,
            ),
            TemplateVariable(
                name="version",
                description="Document version",
                var_type="string",
                required=True,
                default_value="1.0",
            ),
            TemplateVariable(
                name="author",
                description="Document author",
                var_type="string",
                required=True,
            ),
            TemplateVariable(
                name="stakeholder_list",
                description="Initial list of known stakeholders",
                var_type="list",
                required=False,
                default_value=[],
            ),
            TemplateVariable(
                name="organization",
                description="Organization name",
                var_type="string",
                required=False,
            ),
        ]

    def _create_personas(self) -> dict:
        """Create persona mappings (AC-3)."""
        return {
            PersonaRole.CREATOR: PersonaMapping(
                role=PersonaRole.CREATOR,
                title="Business Analyst",
                responsibilities=[
                    "Identify all stakeholders",
                    "Conduct stakeholder interviews",
                    "Analyze power and interest levels",
                    "Document engagement strategies",
                ],
                required_skills=[
                    "Stakeholder analysis",
                    "Communication",
                    "Interview techniques",
                    "Documentation",
                ],
                approval_weight=0.4,
            ),
            PersonaRole.REVIEWER: PersonaMapping(
                role=PersonaRole.REVIEWER,
                title="Project Manager",
                responsibilities=[
                    "Validate stakeholder coverage",
                    "Review engagement strategies",
                    "Ensure alignment with project plan",
                    "Identify gaps in analysis",
                ],
                required_skills=[
                    "Project management",
                    "Stakeholder management",
                    "Risk assessment",
                ],
                approval_weight=0.3,
            ),
            PersonaRole.APPROVER: PersonaMapping(
                role=PersonaRole.APPROVER,
                title="Project Sponsor",
                responsibilities=[
                    "Approve stakeholder priorities",
                    "Validate key stakeholder identification",
                    "Authorize communication plan",
                ],
                required_skills=[
                    "Executive judgment",
                    "Organizational knowledge",
                    "Strategic alignment",
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
                "sh_intro",
                "sh_identification",
                "sh_classification",
                "sh_power_interest",
                "sh_engagement",
                "sh_communication",
            ],
            terminology_glossary={
                "stakeholder": "stakeholder",
                "engagement": "engagement",
            },
        )
