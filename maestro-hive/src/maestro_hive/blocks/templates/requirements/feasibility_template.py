"""
Feasibility Study Template

Comprehensive feasibility study document with:
- Technical, economic, operational feasibility analysis
- Risk assessment
- Persona mapping (Tech Lead, Finance Analyst, Sponsor)

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


class FeasibilityStudyTemplate(DocumentTemplate):
    """
    Feasibility Study template for project viability assessment.

    Covers:
    - Technical feasibility
    - Economic feasibility (cost-benefit analysis)
    - Operational feasibility
    - Schedule feasibility
    - Legal/Regulatory feasibility
    """

    def __init__(self):
        super().__init__(
            template_id="tpl_feasibility",
            name="Feasibility Study",
            description="Comprehensive feasibility study template for assessing project viability across multiple dimensions",
            phase="requirements",
            version="1.0.0",
            sections=self._create_sections(),
            variables=self._create_variables(),
            personas=self._create_personas(),
            quality_config=self._create_quality_config(),
            metadata={
                "category": "requirements",
                "audience": ["executives", "project_managers", "technical_leads"],
            },
        )

    def _create_sections(self) -> list:
        """Create feasibility study sections."""
        return [
            TemplateSection(
                section_id="fs_executive_summary",
                title="1. Executive Summary",
                description="High-level summary of feasibility findings and recommendation.",
                required=True,
                order=1,
                prompts=[
                    TemplatePrompt(
                        prompt_id="exec_summary_prompt",
                        text="Write an executive summary for the feasibility study of {{project_name}}, including key findings and go/no-go recommendation.",
                        context_variables=["project_name"],
                    ),
                ],
            ),
            TemplateSection(
                section_id="fs_introduction",
                title="2. Introduction",
                description="Background and context for the feasibility study.",
                required=True,
                order=2,
                subsections=[
                    TemplateSection(
                        section_id="fs_background",
                        title="2.1 Background",
                        description="Business context and need for {{project_name}}.",
                        required=True,
                        order=1,
                    ),
                    TemplateSection(
                        section_id="fs_objectives",
                        title="2.2 Study Objectives",
                        description="Goals and scope of this feasibility assessment.",
                        required=True,
                        order=2,
                    ),
                    TemplateSection(
                        section_id="fs_methodology",
                        title="2.3 Methodology",
                        description="Approach and methods used for feasibility analysis.",
                        required=True,
                        order=3,
                    ),
                ],
            ),
            TemplateSection(
                section_id="fs_technical",
                title="3. Technical Feasibility",
                description="Assessment of technical viability.",
                required=True,
                order=3,
                subsections=[
                    TemplateSection(
                        section_id="fs_tech_requirements",
                        title="3.1 Technical Requirements",
                        description="Technology stack, infrastructure, and technical capabilities required.",
                        required=True,
                        order=1,
                    ),
                    TemplateSection(
                        section_id="fs_tech_capabilities",
                        title="3.2 Current Capabilities",
                        description="Existing technical assets and skills available.",
                        required=True,
                        order=2,
                    ),
                    TemplateSection(
                        section_id="fs_tech_gaps",
                        title="3.3 Technical Gaps",
                        description="Gaps between required and available technical capabilities.",
                        required=True,
                        order=3,
                    ),
                    TemplateSection(
                        section_id="fs_tech_risks",
                        title="3.4 Technical Risks",
                        description="Technology-related risks and mitigation strategies.",
                        required=True,
                        order=4,
                    ),
                    TemplateSection(
                        section_id="fs_tech_verdict",
                        title="3.5 Technical Feasibility Verdict",
                        description="Overall technical feasibility assessment: Feasible / Feasible with conditions / Not feasible.",
                        required=True,
                        order=5,
                    ),
                ],
            ),
            TemplateSection(
                section_id="fs_economic",
                title="4. Economic Feasibility",
                description="Cost-benefit analysis and financial viability.",
                required=True,
                order=4,
                subsections=[
                    TemplateSection(
                        section_id="fs_costs",
                        title="4.1 Cost Analysis",
                        description="Development costs, operational costs, and total cost of ownership.",
                        required=True,
                        order=1,
                        prompts=[
                            TemplatePrompt(
                                prompt_id="cost_analysis_prompt",
                                text="Estimate costs for {{project_name}} including: development, infrastructure, licensing, training, and ongoing operations. Budget: {{budget}}",
                                context_variables=["project_name", "budget"],
                            ),
                        ],
                    ),
                    TemplateSection(
                        section_id="fs_benefits",
                        title="4.2 Benefits Analysis",
                        description="Quantifiable and intangible benefits expected.",
                        required=True,
                        order=2,
                    ),
                    TemplateSection(
                        section_id="fs_roi",
                        title="4.3 Return on Investment (ROI)",
                        description="ROI calculation and payback period analysis.",
                        required=True,
                        order=3,
                    ),
                    TemplateSection(
                        section_id="fs_financial_risks",
                        title="4.4 Financial Risks",
                        description="Budget overrun risks and financial contingencies.",
                        required=True,
                        order=4,
                    ),
                    TemplateSection(
                        section_id="fs_economic_verdict",
                        title="4.5 Economic Feasibility Verdict",
                        description="Overall economic feasibility assessment.",
                        required=True,
                        order=5,
                    ),
                ],
            ),
            TemplateSection(
                section_id="fs_operational",
                title="5. Operational Feasibility",
                description="Assessment of organizational readiness.",
                required=True,
                order=5,
                subsections=[
                    TemplateSection(
                        section_id="fs_org_impact",
                        title="5.1 Organizational Impact",
                        description="How the project affects existing processes and structures.",
                        required=True,
                        order=1,
                    ),
                    TemplateSection(
                        section_id="fs_user_acceptance",
                        title="5.2 User Acceptance",
                        description="Expected user adoption and change management needs.",
                        required=True,
                        order=2,
                    ),
                    TemplateSection(
                        section_id="fs_training",
                        title="5.3 Training Requirements",
                        description="Training and support needed for successful adoption.",
                        required=True,
                        order=3,
                    ),
                    TemplateSection(
                        section_id="fs_operational_verdict",
                        title="5.4 Operational Feasibility Verdict",
                        description="Overall operational feasibility assessment.",
                        required=True,
                        order=4,
                    ),
                ],
            ),
            TemplateSection(
                section_id="fs_schedule",
                title="6. Schedule Feasibility",
                description="Timeline analysis and schedule risk assessment.",
                required=True,
                order=6,
                subsections=[
                    TemplateSection(
                        section_id="fs_timeline",
                        title="6.1 Proposed Timeline",
                        description="High-level project schedule and milestones.",
                        required=True,
                        order=1,
                    ),
                    TemplateSection(
                        section_id="fs_constraints",
                        title="6.2 Schedule Constraints",
                        description="Fixed deadlines, dependencies, and constraints.",
                        required=True,
                        order=2,
                    ),
                    TemplateSection(
                        section_id="fs_schedule_verdict",
                        title="6.3 Schedule Feasibility Verdict",
                        description="Overall schedule feasibility assessment.",
                        required=True,
                        order=3,
                    ),
                ],
            ),
            TemplateSection(
                section_id="fs_legal",
                title="7. Legal and Regulatory Feasibility",
                description="Compliance and legal considerations.",
                required=True,
                order=7,
                subsections=[
                    TemplateSection(
                        section_id="fs_compliance",
                        title="7.1 Regulatory Compliance",
                        description="Applicable regulations and compliance requirements.",
                        required=True,
                        order=1,
                    ),
                    TemplateSection(
                        section_id="fs_legal_risks",
                        title="7.2 Legal Risks",
                        description="Legal risks and mitigation strategies.",
                        required=True,
                        order=2,
                    ),
                ],
            ),
            TemplateSection(
                section_id="fs_alternatives",
                title="8. Alternatives Analysis",
                description="Comparison of alternative solutions.",
                required=True,
                order=8,
                subsections=[
                    TemplateSection(
                        section_id="fs_alt_options",
                        title="8.1 Alternative Options",
                        description="Description of alternative approaches considered.",
                        required=True,
                        order=1,
                    ),
                    TemplateSection(
                        section_id="fs_alt_comparison",
                        title="8.2 Comparison Matrix",
                        description="Side-by-side comparison of alternatives.",
                        required=True,
                        order=2,
                    ),
                ],
            ),
            TemplateSection(
                section_id="fs_recommendation",
                title="9. Recommendation",
                description="Final recommendation and next steps.",
                required=True,
                order=9,
                subsections=[
                    TemplateSection(
                        section_id="fs_verdict",
                        title="9.1 Overall Feasibility Verdict",
                        description="Consolidated feasibility assessment across all dimensions.",
                        required=True,
                        order=1,
                    ),
                    TemplateSection(
                        section_id="fs_conditions",
                        title="9.2 Conditions for Success",
                        description="Prerequisites and conditions that must be met.",
                        required=True,
                        order=2,
                    ),
                    TemplateSection(
                        section_id="fs_next_steps",
                        title="9.3 Recommended Next Steps",
                        description="Immediate actions if project is approved.",
                        required=True,
                        order=3,
                    ),
                ],
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
                name="budget",
                description="Proposed budget amount",
                var_type="number",
                required=False,
            ),
            TemplateVariable(
                name="timeline_months",
                description="Proposed timeline in months",
                var_type="number",
                required=False,
            ),
            TemplateVariable(
                name="sponsor",
                description="Executive sponsor",
                var_type="string",
                required=False,
            ),
        ]

    def _create_personas(self) -> dict:
        """Create persona mappings (AC-3)."""
        return {
            PersonaRole.CREATOR: PersonaMapping(
                role=PersonaRole.CREATOR,
                title="Technical Lead / Business Analyst",
                responsibilities=[
                    "Conduct feasibility analysis",
                    "Gather technical and business data",
                    "Document findings and recommendations",
                    "Coordinate with subject matter experts",
                ],
                required_skills=[
                    "Technical analysis",
                    "Business analysis",
                    "Financial analysis",
                    "Documentation",
                ],
                approval_weight=0.3,
            ),
            PersonaRole.REVIEWER: PersonaMapping(
                role=PersonaRole.REVIEWER,
                title="Finance Analyst / Architecture Review Board",
                responsibilities=[
                    "Validate cost estimates",
                    "Review technical assessment",
                    "Challenge assumptions",
                    "Verify ROI calculations",
                ],
                required_skills=[
                    "Financial modeling",
                    "Technical review",
                    "Risk assessment",
                ],
                approval_weight=0.3,
            ),
            PersonaRole.APPROVER: PersonaMapping(
                role=PersonaRole.APPROVER,
                title="Executive Sponsor / Steering Committee",
                responsibilities=[
                    "Approve feasibility verdict",
                    "Authorize project initiation",
                    "Commit resources and budget",
                ],
                required_skills=[
                    "Executive decision-making",
                    "Strategic alignment",
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
                "fs_executive_summary",
                "fs_technical",
                "fs_economic",
                "fs_operational",
                "fs_recommendation",
            ],
            terminology_glossary={
                "feasible": "feasible",
                "viable": "viable",
                "ROI": "ROI",
            },
        )
