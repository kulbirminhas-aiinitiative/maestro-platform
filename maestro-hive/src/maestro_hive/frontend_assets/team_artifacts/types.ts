/**
 * MD-2371: Mission-Document Workflow Types
 * Type definitions for the Mission-Document Workflow system
 */

// Document Types
export type DocumentType =
  | 'prd'
  | 'techDesign'
  | 'testPlan'
  | 'userStories'
  | 'adr'
  | 'runbook'
  | 'deploymentGuide';

// Job Status
export type JobStatus = 'queued' | 'processing' | 'completed' | 'failed' | 'cancelled';

// Persona Role Types
export type PersonaRole =
  | 'product_manager'
  | 'software_architect'
  | 'qa_engineer'
  | 'devops_engineer'
  | 'frontend_developer'
  | 'backend_developer'
  | 'ux_designer';

/**
 * Team Artifact Configuration
 * Maps personas to the document types they can generate
 * Implements AC-1: Persona Document Configuration
 */
export interface TeamArtifactConfig {
  id: string;
  teamId: string;
  personaId: string;
  personaRole: PersonaRole;
  documentTypes: DocumentType[];
  templateOverrides?: Record<string, unknown>;
  enabled: boolean;
  createdAt: Date;
  updatedAt: Date;
}

/**
 * Document Generation Job
 * Represents a job in the document generation queue
 */
export interface DocumentGenerationJob {
  id: string;
  missionId: string;
  teamId: string;
  status: JobStatus;
  documentTypes: DocumentType[];
  generatedDocuments: GeneratedDocument[];
  startedAt?: Date;
  completedAt?: Date;
  error?: string;
  retryCount: number;
  maxRetries: number;
}

/**
 * Generated Document
 * Represents a document that has been generated
 */
export interface GeneratedDocument {
  id: string;
  jobId: string;
  missionId: string;
  documentType: DocumentType;
  title: string;
  content: string;
  confluencePageId?: string;
  confluenceUrl?: string;
  personaId: string;
  personaRole: PersonaRole;
  aiSummary?: string;
  createdAt: Date;
}

/**
 * Mission Context
 * Context extracted from a completed mission for document generation
 */
export interface MissionContext {
  missionId: string;
  teamId: string;
  objective: string;
  outcome: string;
  participants: MissionParticipant[];
  messages: MissionMessage[];
  artifacts: MissionArtifact[];
  completedAt: Date;
}

/**
 * Mission Participant
 */
export interface MissionParticipant {
  id: string;
  personaId: string;
  personaRole: PersonaRole;
  personaName: string;
}

/**
 * Mission Message
 */
export interface MissionMessage {
  id: string;
  participantId: string;
  content: string;
  timestamp: Date;
  messageType: 'contribution' | 'question' | 'answer' | 'decision';
}

/**
 * Mission Artifact
 */
export interface MissionArtifact {
  id: string;
  type: string;
  content: string;
  generatedBy: string;
  createdAt: Date;
}

/**
 * Document Template
 * Template definition for document generation
 * Implements AC-3: Document Template System
 */
export interface DocumentTemplate {
  id: string;
  type: DocumentType;
  name: string;
  description: string;
  sections: TemplateSection[];
  requiredContext: string[];
  aiPromptTemplate: string;
  version: string;
}

/**
 * Template Section
 */
export interface TemplateSection {
  id: string;
  title: string;
  order: number;
  required: boolean;
  contentPrompt: string;
  maxTokens?: number;
}

/**
 * WebSocket Events
 * Implements AC-5: WebSocket Async Notification
 */
export interface DocumentGeneratingEvent {
  type: 'document:generating';
  payload: {
    missionId: string;
    jobId: string;
    documentType: DocumentType;
    persona: string;
    progress: number;
  };
}

export interface DocumentProgressEvent {
  type: 'document:progress';
  payload: {
    missionId: string;
    jobId: string;
    documentType: DocumentType;
    progress: number;
    message: string;
  };
}

export interface DocumentCompleteEvent {
  type: 'document:complete';
  payload: {
    missionId: string;
    jobId: string;
    documentId: string;
    documentType: DocumentType;
    confluenceUrl?: string;
  };
}

export interface DocumentErrorEvent {
  type: 'document:error';
  payload: {
    missionId: string;
    jobId: string;
    documentType: DocumentType;
    error: string;
    retryable: boolean;
  };
}

export type DocumentWebSocketEvent =
  | DocumentGeneratingEvent
  | DocumentProgressEvent
  | DocumentCompleteEvent
  | DocumentErrorEvent;

/**
 * Artifact Registry Entry
 * Implements AC-8: Team Artifact Registry
 */
export interface ArtifactRegistryEntry {
  id: string;
  teamId: string;
  missionId: string;
  documentId: string;
  documentType: DocumentType;
  title: string;
  confluenceUrl?: string;
  version: number;
  tags: string[];
  createdAt: Date;
  updatedAt: Date;
}

/**
 * Configuration options for document generation
 */
export interface DocumentGenerationOptions {
  templateOverrides?: Partial<Record<DocumentType, boolean>>;
  publishToConfluence?: boolean;
  generateAiSummary?: boolean;
  notifyOnComplete?: boolean;
  priority?: 'low' | 'normal' | 'high';
}

/**
 * Result of document generation
 */
export interface DocumentGenerationResult {
  success: boolean;
  jobId: string;
  documentsGenerated: number;
  documentsFailed: number;
  documents: GeneratedDocument[];
  errors?: string[];
  duration: number;
}
