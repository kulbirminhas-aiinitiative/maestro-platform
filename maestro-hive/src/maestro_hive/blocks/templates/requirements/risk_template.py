"""
Risk Assessment Template

Comprehensive risk assessment document with:
- Risk identification and categorization
- Probability/Impact analysis
- Mitigation strategies
- Persona mapping (Risk Manager, PM, Sponsor)

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


class RiskAssessmentTemplate(DocumentTemplate):
    """
    Risk Assessment template for project risk management.

    Covers:
    - Risk identification
    - Risk categorization
    - Probability and impact analysis
    - Risk prioritization
    - Mitigation strategies
    - Contingency planning
    """

    def __init__(self):
        super().__init__(
            template_id="tpl_risk",
            name="Risk Assessment",
            description="Comprehensive risk assessment template for identifying, analyzing, and planning responses to project risks",
            phase="requirements",
            version="1.0.0",
            sections=self._create_sections(),
            variables=self._create_variables(),
            personas=self._create_personas(),
            quality_config=self._create_quality_config(),
            metadata={
                "category": "requirements",
                "audience": ["project_managers", "risk_managers", "stakeholders"],
            },
        )

    def _create_sections(self) -> list:
        """Create risk assessment sections."""
        return [
            TemplateSection(
                section_id="ra_intro",
                title="1. Introduction",
                description="Overview of the risk assessment for {{project_name}}.",
                required=True,
                order=1,
                subsections=[
                    TemplateSection(
                        section_id="ra_purpose",
                        title="1.1 Purpose",
                        description="This document identifies and assesses risks for {{project_name}} to enable proactive risk management throughout the project lifecycle.",
                        required=True,
                        order=1,
                    ),
                    TemplateSection(
                        section_id="ra_scope",
                        title="1.2 Scope",
                        description="Risk categories and project phases covered by this assessment.",
                        required=True,
                        order=2,
                    ),
                    TemplateSection(
                        section_id="ra_methodology",
                        title="1.3 Risk Assessment Methodology",
                        description="Approach used for risk identification, analysis, and prioritization.",
                        required=True,
                        order=3,
                    ),
                ],
            ),
            TemplateSection(
                section_id="ra_framework",
                title="2. Risk Management Framework",
                description="Framework for ongoing risk management.",
                required=True,
                order=2,
                subsections=[
                    TemplateSection(
                        section_id="ra_categories",
                        title="2.1 Risk Categories",
                        description="Categories used for risk classification: Technical, Schedule, Cost, Resource, External, Organizational.",
                        required=True,
                        order=1,
                    ),
                    TemplateSection(
                        section_id="ra_probability_scale",
                        title="2.2 Probability Scale",
                        description="1-5 scale: 1=Very Low (<10%), 2=Low (10-30%), 3=Medium (30-50%), 4=High (50-70%), 5=Very High (>70%).",
                        required=True,
                        order=2,
                    ),
                    TemplateSection(
                        section_id="ra_impact_scale",
                        title="2.3 Impact Scale",
                        description="1-5 scale: 1=Negligible, 2=Minor, 3=Moderate, 4=Major, 5=Severe.",
                        required=True,
                        order=3,
                    ),
                    TemplateSection(
                        section_id="ra_risk_matrix",
                        title="2.4 Risk Matrix",
                        description="Risk score = Probability x Impact. Low (1-6), Medium (7-12), High (13-19), Critical (20-25).",
                        required=True,
                        order=4,
                    ),
                ],
            ),
            TemplateSection(
                section_id="ra_identification",
                title="3. Risk Identification",
                description="Identified risks by category.",
                required=True,
                order=3,
                subsections=[
                    TemplateSection(
                        section_id="ra_technical_risks",
                        title="3.1 Technical Risks",
                        description="Technology, architecture, integration, and performance risks.",
                        required=True,
                        order=1,
                        prompts=[
                            TemplatePrompt(
                                prompt_id="tech_risks_prompt",
                                text="Identify technical risks for {{project_name}} considering: technology stack, integration complexity, performance requirements, and technical debt.",
                                context_variables=["project_name"],
                            ),
                        ],
                    ),
                    TemplateSection(
                        section_id="ra_schedule_risks",
                        title="3.2 Schedule Risks",
                        description="Timeline, dependencies, and delivery risks.",
                        required=True,
                        order=2,
                    ),
                    TemplateSection(
                        section_id="ra_cost_risks",
                        title="3.3 Cost Risks",
                        description="Budget, resource, and financial risks.",
                        required=True,
                        order=3,
                    ),
                    TemplateSection(
                        section_id="ra_resource_risks",
                        title="3.4 Resource Risks",
                        description="Staffing, skills, and capacity risks.",
                        required=True,
                        order=4,
                    ),
                    TemplateSection(
                        section_id="ra_external_risks",
                        title="3.5 External Risks",
                        description="Vendor, regulatory, market, and environmental risks.",
                        required=True,
                        order=5,
                    ),
                    TemplateSection(
                        section_id="ra_org_risks",
                        title="3.6 Organizational Risks",
                        description="Change management, stakeholder, and political risks.",
                        required=True,
                        order=6,
                    ),
                ],
            ),
            TemplateSection(
                section_id="ra_analysis",
                title="4. Risk Analysis",
                description="Detailed analysis and prioritization of identified risks.",
                required=True,
                order=4,
                subsections=[
                    TemplateSection(
                        section_id="ra_risk_register",
                        title="4.1 Risk Register",
                        description="Complete risk register with ID, description, category, probability, impact, score, owner, and status.",
                        required=True,
                        order=1,
                    ),
                    TemplateSection(
                        section_id="ra_top_risks",
                        title="4.2 Top 10 Risks",
                        description="Highest priority risks requiring immediate attention.",
                        required=True,
                        order=2,
                    ),
                ],
            ),
            TemplateSection(
                section_id="ra_response",
                title="5. Risk Response Planning",
                description="Strategies for addressing identified risks.",
                required=True,
                order=5,
                subsections=[
                    TemplateSection(
                        section_id="ra_strategies",
                        title="5.1 Response Strategies",
                        description="Response types: Avoid, Transfer, Mitigate, Accept.",
                        required=True,
                        order=1,
                    ),
                    TemplateSection(
                        section_id="ra_mitigation_plans",
                        title="5.2 Mitigation Plans",
                        description="Detailed mitigation plans for high-priority risks.",
                        required=True,
                        order=2,
                        prompts=[
                            TemplatePrompt(
                                prompt_id="mitigation_prompt",
                                text="Develop mitigation plans for the top risks in {{project_name}}. Include specific actions, responsible parties, and success criteria.",
                                context_variables=["project_name"],
                            ),
                        ],
                    ),
                    TemplateSection(
                        section_id="ra_contingency",
                        title="5.3 Contingency Plans",
                        description="Contingency plans for risks that cannot be fully mitigated.",
                        required=True,
                        order=3,
                    ),
                ],
            ),
            TemplateSection(
                section_id="ra_monitoring",
                title="6. Risk Monitoring",
                description="Ongoing risk monitoring and review process.",
                required=True,
                order=6,
                subsections=[
                    TemplateSection(
                        section_id="ra_triggers",
                        title="6.1 Risk Triggers",
                        description="Early warning indicators for identified risks.",
                        required=True,
                        order=1,
                    ),
                    TemplateSection(
                        section_id="ra_review_schedule",
                        title="6.2 Review Schedule",
                        description="Frequency and process for risk register reviews.",
                        required=True,
                        order=2,
                    ),
                    TemplateSection(
                        section_id="ra_escalation",
                        title="6.3 Escalation Process",
                        description="Process for escalating risks that exceed thresholds.",
                        required=True,
                        order=3,
                    ),
                ],
            ),
            TemplateSection(
                section_id="ra_budget",
                title="7. Risk Budget",
                description="Budget allocation for risk management activities.",
                required=True,
                order=7,
                subsections=[
                    TemplateSection(
                        section_id="ra_contingency_reserve",
                        title="7.1 Contingency Reserve",
                        description="Budget reserved for known risks (typically 10-15% of project budget).",
                        required=True,
                        order=1,
                    ),
                    TemplateSection(
                        section_id="ra_management_reserve",
                        title="7.2 Management Reserve",
                        description="Budget reserved for unknown risks (typically 5-10% of project budget).",
                        required=True,
                        order=2,
                    ),
                ],
            ),
            TemplateSection(
                section_id="ra_appendix",
                title="8. Appendices",
                description="Supporting materials and detailed risk data.",
                required=False,
                order=8,
            ),
        ]

    def _create_variables(self) -> list:
        """Create template variables."""
        return [
            TemplateVariable(
                name="project_name",
                description="Project name",
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
                name="risk_owner",
                description="Overall risk owner",
                var_type="string",
                required=False,
            ),
            TemplateVariable(
                name="project_budget",
                description="Total project budget for reserve calculations",
                var_type="number",
                required=False,
            ),
            TemplateVariable(
                name="risk_tolerance",
                description="Organization's risk tolerance level (Low/Medium/High)",
                var_type="string",
                required=False,
                default_value="Medium",
            ),
        ]

    def _create_personas(self) -> dict:
        """Create persona mappings (AC-3)."""
        return {
            PersonaRole.CREATOR: PersonaMapping(
                role=PersonaRole.CREATOR,
                title="Risk Manager / Project Manager",
                responsibilities=[
                    "Conduct risk identification sessions",
                    "Analyze and score risks",
                    "Develop mitigation plans",
                    "Maintain risk register",
                ],
                required_skills=[
                    "Risk management",
                    "Facilitation",
                    "Analysis",
                    "Documentation",
                ],
                approval_weight=0.4,
            ),
            PersonaRole.REVIEWER: PersonaMapping(
                role=PersonaRole.REVIEWER,
                title="Project Manager / Technical Lead",
                responsibilities=[
                    "Validate risk assessments",
                    "Review mitigation plans",
                    "Identify additional risks",
                    "Assign risk owners",
                ],
                required_skills=[
                    "Project management",
                    "Technical expertise",
                    "Risk assessment",
                ],
                approval_weight=0.3,
            ),
            PersonaRole.APPROVER: PersonaMapping(
                role=PersonaRole.APPROVER,
                title="Executive Sponsor / Steering Committee",
                responsibilities=[
                    "Approve risk response strategies",
                    "Authorize risk reserves",
                    "Accept residual risk levels",
                ],
                required_skills=[
                    "Executive judgment",
                    "Risk tolerance setting",
                    "Budget authority",
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
                "ra_intro",
                "ra_framework",
                "ra_identification",
                "ra_analysis",
                "ra_response",
                "ra_monitoring",
            ],
            terminology_glossary={
                "risk": "risk",
                "mitigation": "mitigation",
                "contingency": "contingency",
            },
        )
