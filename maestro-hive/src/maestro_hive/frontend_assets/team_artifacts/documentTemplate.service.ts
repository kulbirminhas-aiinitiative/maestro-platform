/**
 * MD-2371: Document Template Service
 * Implements AC-3: Document Template System (PRD, Tech Design, Test Plan)
 *
 * Manages document templates for generating various document types.
 */

import {
  DocumentTemplate,
  DocumentType,
  TemplateSection,
  MissionContext,
} from './types';

/**
 * Built-in document templates
 */
const BUILT_IN_TEMPLATES: DocumentTemplate[] = [
  {
    id: 'template_prd_v1',
    type: 'prd',
    name: 'Product Requirements Document',
    description: 'Standard PRD template for product requirements',
    version: '1.0.0',
    requiredContext: ['objective', 'outcome', 'participants'],
    aiPromptTemplate: `Generate a comprehensive Product Requirements Document based on the following mission context:

Objective: {{objective}}
Outcome: {{outcome}}
Participants: {{participants}}
Key Discussion Points: {{discussionSummary}}

Create a well-structured PRD with clear requirements, user stories, and acceptance criteria.`,
    sections: [
      {
        id: 'prd_overview',
        title: 'Overview',
        order: 1,
        required: true,
        contentPrompt: 'Provide a high-level overview of the product/feature',
        maxTokens: 500,
      },
      {
        id: 'prd_objectives',
        title: 'Objectives',
        order: 2,
        required: true,
        contentPrompt: 'List the main objectives and goals',
        maxTokens: 300,
      },
      {
        id: 'prd_requirements',
        title: 'Functional Requirements',
        order: 3,
        required: true,
        contentPrompt: 'Detail the functional requirements',
        maxTokens: 1000,
      },
      {
        id: 'prd_nonfunctional',
        title: 'Non-Functional Requirements',
        order: 4,
        required: false,
        contentPrompt: 'List non-functional requirements (performance, security, etc.)',
        maxTokens: 500,
      },
      {
        id: 'prd_acceptance',
        title: 'Acceptance Criteria',
        order: 5,
        required: true,
        contentPrompt: 'Define acceptance criteria for each requirement',
        maxTokens: 800,
      },
    ],
  },
  {
    id: 'template_tech_design_v1',
    type: 'techDesign',
    name: 'Technical Design Document',
    description: 'Standard technical design document template',
    version: '1.0.0',
    requiredContext: ['objective', 'outcome', 'participants'],
    aiPromptTemplate: `Generate a Technical Design Document based on the following mission context:

Objective: {{objective}}
Outcome: {{outcome}}
Technical Contributors: {{technicalContributors}}
Architecture Decisions: {{architectureDecisions}}

Create a detailed technical design with architecture diagrams, component specifications, and implementation details.`,
    sections: [
      {
        id: 'tech_overview',
        title: 'Technical Overview',
        order: 1,
        required: true,
        contentPrompt: 'Provide technical overview and context',
        maxTokens: 500,
      },
      {
        id: 'tech_architecture',
        title: 'Architecture',
        order: 2,
        required: true,
        contentPrompt: 'Describe the system architecture',
        maxTokens: 800,
      },
      {
        id: 'tech_components',
        title: 'Component Design',
        order: 3,
        required: true,
        contentPrompt: 'Detail individual component designs',
        maxTokens: 1000,
      },
      {
        id: 'tech_data',
        title: 'Data Model',
        order: 4,
        required: false,
        contentPrompt: 'Describe data models and schemas',
        maxTokens: 600,
      },
      {
        id: 'tech_api',
        title: 'API Specifications',
        order: 5,
        required: false,
        contentPrompt: 'Define API endpoints and contracts',
        maxTokens: 800,
      },
      {
        id: 'tech_security',
        title: 'Security Considerations',
        order: 6,
        required: true,
        contentPrompt: 'Address security requirements and mitigations',
        maxTokens: 400,
      },
    ],
  },
  {
    id: 'template_test_plan_v1',
    type: 'testPlan',
    name: 'Test Plan Document',
    description: 'Standard test plan template for QA',
    version: '1.0.0',
    requiredContext: ['objective', 'outcome', 'participants'],
    aiPromptTemplate: `Generate a Test Plan based on the following mission context:

Objective: {{objective}}
Outcome: {{outcome}}
QA Contributors: {{qaContributors}}
Requirements Summary: {{requirementsSummary}}

Create a comprehensive test plan with test cases, coverage matrix, and testing strategy.`,
    sections: [
      {
        id: 'test_scope',
        title: 'Test Scope',
        order: 1,
        required: true,
        contentPrompt: 'Define what is in and out of scope for testing',
        maxTokens: 400,
      },
      {
        id: 'test_strategy',
        title: 'Testing Strategy',
        order: 2,
        required: true,
        contentPrompt: 'Describe the overall testing approach',
        maxTokens: 500,
      },
      {
        id: 'test_cases',
        title: 'Test Cases',
        order: 3,
        required: true,
        contentPrompt: 'List detailed test cases with steps and expected results',
        maxTokens: 1500,
      },
      {
        id: 'test_coverage',
        title: 'Coverage Matrix',
        order: 4,
        required: true,
        contentPrompt: 'Map test cases to requirements',
        maxTokens: 600,
      },
      {
        id: 'test_environment',
        title: 'Test Environment',
        order: 5,
        required: false,
        contentPrompt: 'Describe required test environment and data',
        maxTokens: 300,
      },
    ],
  },
  {
    id: 'template_adr_v1',
    type: 'adr',
    name: 'Architecture Decision Record',
    description: 'Standard ADR template',
    version: '1.0.0',
    requiredContext: ['objective', 'outcome'],
    aiPromptTemplate: `Generate an Architecture Decision Record based on the following mission context:

Context: {{objective}}
Decision Outcome: {{outcome}}
Participants: {{architectParticipants}}

Create a well-structured ADR documenting the decision, rationale, and consequences.`,
    sections: [
      {
        id: 'adr_status',
        title: 'Status',
        order: 1,
        required: true,
        contentPrompt: 'Current status of the decision',
        maxTokens: 50,
      },
      {
        id: 'adr_context',
        title: 'Context',
        order: 2,
        required: true,
        contentPrompt: 'Describe the context and problem',
        maxTokens: 400,
      },
      {
        id: 'adr_decision',
        title: 'Decision',
        order: 3,
        required: true,
        contentPrompt: 'State the decision that was made',
        maxTokens: 300,
      },
      {
        id: 'adr_rationale',
        title: 'Rationale',
        order: 4,
        required: true,
        contentPrompt: 'Explain why this decision was made',
        maxTokens: 500,
      },
      {
        id: 'adr_consequences',
        title: 'Consequences',
        order: 5,
        required: true,
        contentPrompt: 'List positive and negative consequences',
        maxTokens: 400,
      },
    ],
  },
  {
    id: 'template_runbook_v1',
    type: 'runbook',
    name: 'Operations Runbook',
    description: 'Standard runbook template for operations',
    version: '1.0.0',
    requiredContext: ['objective', 'outcome'],
    aiPromptTemplate: `Generate an Operations Runbook based on the following mission context:

System/Feature: {{objective}}
Operational Requirements: {{outcome}}
DevOps Contributors: {{devopsContributors}}

Create a practical runbook with procedures, troubleshooting steps, and recovery instructions.`,
    sections: [
      {
        id: 'runbook_prereqs',
        title: 'Prerequisites',
        order: 1,
        required: true,
        contentPrompt: 'List prerequisites and access requirements',
        maxTokens: 300,
      },
      {
        id: 'runbook_procedures',
        title: 'Standard Procedures',
        order: 2,
        required: true,
        contentPrompt: 'Document standard operating procedures',
        maxTokens: 800,
      },
      {
        id: 'runbook_troubleshoot',
        title: 'Troubleshooting',
        order: 3,
        required: true,
        contentPrompt: 'Common issues and resolution steps',
        maxTokens: 600,
      },
      {
        id: 'runbook_recovery',
        title: 'Recovery Procedures',
        order: 4,
        required: true,
        contentPrompt: 'Disaster recovery and rollback procedures',
        maxTokens: 500,
      },
    ],
  },
];

/**
 * Service for managing document templates
 */
export class DocumentTemplateService {
  private templates: Map<string, DocumentTemplate> = new Map();
  private customTemplates: Map<string, DocumentTemplate> = new Map();

  constructor() {
    // Initialize with built-in templates
    for (const template of BUILT_IN_TEMPLATES) {
      this.templates.set(template.id, template);
    }
  }

  /**
   * Get template by ID
   */
  getTemplateById(templateId: string): DocumentTemplate | null {
    return this.templates.get(templateId) || this.customTemplates.get(templateId) || null;
  }

  /**
   * Get template by document type
   */
  getTemplateByType(documentType: DocumentType): DocumentTemplate | null {
    for (const template of this.templates.values()) {
      if (template.type === documentType) {
        return template;
      }
    }
    for (const template of this.customTemplates.values()) {
      if (template.type === documentType) {
        return template;
      }
    }
    return null;
  }

  /**
   * Get all templates for a document type
   */
  getTemplatesForType(documentType: DocumentType): DocumentTemplate[] {
    const templates: DocumentTemplate[] = [];
    for (const template of this.templates.values()) {
      if (template.type === documentType) {
        templates.push(template);
      }
    }
    for (const template of this.customTemplates.values()) {
      if (template.type === documentType) {
        templates.push(template);
      }
    }
    return templates;
  }

  /**
   * Register a custom template
   */
  registerCustomTemplate(template: DocumentTemplate): void {
    this.customTemplates.set(template.id, template);
  }

  /**
   * Render a template with mission context
   */
  renderTemplate(
    template: DocumentTemplate,
    context: MissionContext
  ): string {
    let rendered = template.aiPromptTemplate;

    // Replace context placeholders
    rendered = rendered.replace('{{objective}}', context.objective);
    rendered = rendered.replace('{{outcome}}', context.outcome);
    rendered = rendered.replace(
      '{{participants}}',
      context.participants.map((p) => `${p.personaName} (${p.personaRole})`).join(', ')
    );

    // Generate discussion summary from messages
    const discussionSummary = this.generateDiscussionSummary(context.messages);
    rendered = rendered.replace('{{discussionSummary}}', discussionSummary);

    // Filter participants by role for role-specific placeholders
    rendered = this.replaceRoleParticipants(rendered, context.participants);

    return rendered;
  }

  /**
   * Validate that context has all required fields for a template
   */
  validateContext(
    template: DocumentTemplate,
    context: MissionContext
  ): { valid: boolean; missing: string[] } {
    const missing: string[] = [];

    for (const required of template.requiredContext) {
      const value = context[required as keyof MissionContext];
      if (value === undefined || value === null || value === '') {
        missing.push(required);
      }
    }

    return {
      valid: missing.length === 0,
      missing,
    };
  }

  /**
   * Get all available templates
   */
  getAllTemplates(): DocumentTemplate[] {
    return [
      ...Array.from(this.templates.values()),
      ...Array.from(this.customTemplates.values()),
    ];
  }

  /**
   * Get template sections in order
   */
  getOrderedSections(template: DocumentTemplate): TemplateSection[] {
    return [...template.sections].sort((a, b) => a.order - b.order);
  }

  private generateDiscussionSummary(messages: MissionContext['messages']): string {
    if (messages.length === 0) {
      return 'No discussion recorded.';
    }

    // Group by message type
    const decisions = messages.filter((m) => m.messageType === 'decision');
    const contributions = messages.filter((m) => m.messageType === 'contribution');

    const parts: string[] = [];

    if (decisions.length > 0) {
      parts.push(`Key Decisions: ${decisions.map((d) => d.content).join('; ')}`);
    }

    if (contributions.length > 0) {
      const topContributions = contributions.slice(0, 5);
      parts.push(`Main Contributions: ${topContributions.map((c) => c.content.substring(0, 100)).join('; ')}`);
    }

    return parts.join('\n');
  }

  private replaceRoleParticipants(
    text: string,
    participants: MissionContext['participants']
  ): string {
    const roleMap: Record<string, string[]> = {};

    for (const participant of participants) {
      const roleKey = participant.personaRole.replace('_', ' ');
      if (!roleMap[roleKey]) {
        roleMap[roleKey] = [];
      }
      roleMap[roleKey].push(participant.personaName);
    }

    // Replace role-specific placeholders
    text = text.replace('{{technicalContributors}}',
      [...(roleMap['software architect'] || []), ...(roleMap['backend developer'] || []), ...(roleMap['frontend developer'] || [])].join(', ') || 'N/A'
    );
    text = text.replace('{{qaContributors}}',
      (roleMap['qa engineer'] || []).join(', ') || 'N/A'
    );
    text = text.replace('{{devopsContributors}}',
      (roleMap['devops engineer'] || []).join(', ') || 'N/A'
    );
    text = text.replace('{{architectParticipants}}',
      (roleMap['software architect'] || []).join(', ') || 'N/A'
    );
    text = text.replace('{{architectureDecisions}}', 'See discussion summary');
    text = text.replace('{{requirementsSummary}}', 'See discussion summary');

    return text;
  }
}

// Singleton instance
export const documentTemplateService = new DocumentTemplateService();
