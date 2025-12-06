"""
Requirements Traceability Matrix (RTM) Template

Comprehensive RTM document template with:
- Bidirectional traceability
- Coverage analysis
- Persona mapping (BA, QA Lead, PM)

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


class RequirementsTraceabilityMatrixTemplate(DocumentTemplate):
    """
    Requirements Traceability Matrix template for tracking requirement lifecycle.

    Covers:
    - Requirement identification and categorization
    - Forward traceability (requirements to implementation/tests)
    - Backward traceability (implementation to requirements)
    - Coverage analysis and gap identification
    """

    def __init__(self):
        super().__init__(
            template_id="tpl_rtm",
            name="Requirements Traceability Matrix",
            description="Bidirectional traceability matrix linking requirements to design, implementation, and test artifacts",
            phase="requirements",
            version="1.0.0",
            sections=self._create_sections(),
            variables=self._create_variables(),
            personas=self._create_personas(),
            quality_config=self._create_quality_config(),
            metadata={
                "category": "requirements",
                "audience": ["business_analysts", "qa_engineers", "project_managers"],
            },
        )

    def _create_sections(self) -> list:
        """Create RTM sections."""
        return [
            TemplateSection(
                section_id="rtm_intro",
                title="1. Introduction",
                description="Overview of the Requirements Traceability Matrix.",
                required=True,
                order=1,
                subsections=[
                    TemplateSection(
                        section_id="rtm_purpose",
                        title="1.1 Purpose",
                        description="This RTM tracks all requirements for {{project_name}} from origin through implementation and testing to ensure complete coverage and traceability.",
                        required=True,
                        order=1,
                    ),
                    TemplateSection(
                        section_id="rtm_scope",
                        title="1.2 Scope",
                        description="Requirements and artifacts covered by this traceability matrix.",
                        required=True,
                        order=2,
                    ),
                    TemplateSection(
                        section_id="rtm_definitions",
                        title="1.3 Definitions",
                        description="Requirement types, status definitions, and traceability terminology.",
                        required=True,
                        order=3,
                    ),
                ],
            ),
            TemplateSection(
                section_id="rtm_structure",
                title="2. Matrix Structure",
                description="Explanation of the RTM structure and columns.",
                required=True,
                order=2,
                subsections=[
                    TemplateSection(
                        section_id="rtm_columns",
                        title="2.1 Column Definitions",
                        description="Definition of each column in the traceability matrix: REQ-ID, Description, Source, Priority, Status, Design Reference, Code Reference, Test Reference, Verification Method.",
                        required=True,
                        order=1,
                    ),
                    TemplateSection(
                        section_id="rtm_status_codes",
                        title="2.2 Status Codes",
                        description="Status values: Draft, Approved, Implemented, Tested, Verified, Deferred, Cancelled.",
                        required=True,
                        order=2,
                    ),
                ],
            ),
            TemplateSection(
                section_id="rtm_functional",
                title="3. Functional Requirements Traceability",
                description="Traceability matrix for functional requirements (FR-XXX).",
                required=True,
                order=3,
                prompts=[
                    TemplatePrompt(
                        prompt_id="fr_trace_prompt",
                        text="Generate a traceability matrix for functional requirements of {{project_name}}. Include columns: REQ-ID, Description, Source, Priority, Status, Design Ref, Code Ref, Test Case.",
                        context_variables=["project_name"],
                    ),
                ],
            ),
            TemplateSection(
                section_id="rtm_nonfunctional",
                title="4. Non-Functional Requirements Traceability",
                description="Traceability matrix for non-functional requirements (NFR-XXX).",
                required=True,
                order=4,
                subsections=[
                    TemplateSection(
                        section_id="rtm_performance",
                        title="4.1 Performance Requirements",
                        description="Traceability for performance-related NFRs.",
                        required=True,
                        order=1,
                    ),
                    TemplateSection(
                        section_id="rtm_security",
                        title="4.2 Security Requirements",
                        description="Traceability for security-related NFRs.",
                        required=True,
                        order=2,
                    ),
                    TemplateSection(
                        section_id="rtm_reliability",
                        title="4.3 Reliability Requirements",
                        description="Traceability for reliability-related NFRs.",
                        required=True,
                        order=3,
                    ),
                ],
            ),
            TemplateSection(
                section_id="rtm_user_stories",
                title="5. User Story Traceability",
                description="Traceability matrix for user stories (US-XXX).",
                required=True,
                order=5,
            ),
            TemplateSection(
                section_id="rtm_coverage",
                title="6. Coverage Analysis",
                description="Analysis of requirement coverage across artifacts.",
                required=True,
                order=6,
                subsections=[
                    TemplateSection(
                        section_id="rtm_design_coverage",
                        title="6.1 Design Coverage",
                        description="Percentage of requirements traced to design artifacts.",
                        required=True,
                        order=1,
                    ),
                    TemplateSection(
                        section_id="rtm_impl_coverage",
                        title="6.2 Implementation Coverage",
                        description="Percentage of requirements traced to code modules.",
                        required=True,
                        order=2,
                    ),
                    TemplateSection(
                        section_id="rtm_test_coverage",
                        title="6.3 Test Coverage",
                        description="Percentage of requirements traced to test cases.",
                        required=True,
                        order=3,
                    ),
                ],
            ),
            TemplateSection(
                section_id="rtm_gaps",
                title="7. Gap Analysis",
                description="Identification of traceability gaps.",
                required=True,
                order=7,
                subsections=[
                    TemplateSection(
                        section_id="rtm_untested",
                        title="7.1 Untested Requirements",
                        description="Requirements without corresponding test cases.",
                        required=True,
                        order=1,
                    ),
                    TemplateSection(
                        section_id="rtm_unimplemented",
                        title="7.2 Unimplemented Requirements",
                        description="Requirements without code references.",
                        required=True,
                        order=2,
                    ),
                    TemplateSection(
                        section_id="rtm_orphan_tests",
                        title="7.3 Orphan Tests",
                        description="Test cases without requirement references.",
                        required=True,
                        order=3,
                    ),
                ],
            ),
            TemplateSection(
                section_id="rtm_change_log",
                title="8. Change Log",
                description="History of requirement changes and their impacts.",
                required=True,
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
                description="RTM version",
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
                name="requirements",
                description="List of requirements to trace",
                var_type="list",
                required=False,
                default_value=[],
            ),
            TemplateVariable(
                name="srs_reference",
                description="Reference to SRS document",
                var_type="string",
                required=False,
            ),
            TemplateVariable(
                name="test_plan_reference",
                description="Reference to test plan document",
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
                    "Create initial traceability matrix",
                    "Link requirements to sources",
                    "Maintain bidirectional traceability",
                    "Update coverage metrics",
                ],
                required_skills=[
                    "Requirements engineering",
                    "Traceability tools",
                    "Documentation",
                    "Attention to detail",
                ],
                approval_weight=0.4,
            ),
            PersonaRole.REVIEWER: PersonaMapping(
                role=PersonaRole.REVIEWER,
                title="QA Lead",
                responsibilities=[
                    "Validate test coverage",
                    "Review gap analysis",
                    "Verify test case linkage",
                    "Identify missing test scenarios",
                ],
                required_skills=[
                    "Test management",
                    "Requirements analysis",
                    "Coverage analysis",
                ],
                approval_weight=0.3,
            ),
            PersonaRole.APPROVER: PersonaMapping(
                role=PersonaRole.APPROVER,
                title="Project Manager",
                responsibilities=[
                    "Approve coverage thresholds",
                    "Accept gap remediation plans",
                    "Sign-off on traceability completeness",
                ],
                required_skills=[
                    "Project governance",
                    "Quality management",
                    "Risk assessment",
                ],
                approval_weight=1.0,
            ),
        }

    def _create_quality_config(self) -> QualityScoringConfig:
        """Create quality scoring configuration (AC-4)."""
        return QualityScoringConfig(
            completeness_weight=30.0,
            consistency_weight=20.0,
            clarity_weight=20.0,
            traceability_weight=30.0,
            pass_threshold=70.0,
            required_sections=[
                "rtm_intro",
                "rtm_structure",
                "rtm_functional",
                "rtm_nonfunctional",
                "rtm_coverage",
                "rtm_gaps",
            ],
            terminology_glossary={
                "requirement": "requirement",
                "trace": "trace",
                "coverage": "coverage",
            },
        )
