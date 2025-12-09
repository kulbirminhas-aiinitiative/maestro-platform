/**
 * MD-2371: Mission Document Generation Service
 * Implements AC-2: Backend Document Generation Service (missionDocumentGeneration.service.ts)
 *
 * Orchestrates document generation when a mission completes.
 */

import {
  DocumentGenerationJob,
  DocumentGenerationOptions,
  DocumentGenerationResult,
  GeneratedDocument,
  MissionContext,
  DocumentType,
  JobStatus,
  TeamArtifactConfig,
} from './types';
import { personaDocumentConfigService } from './personaDocumentConfig.service';
import { documentTemplateService } from './documentTemplate.service';
import { webSocketNotificationService } from './webSocketNotification.service';
import { artifactRegistryService } from './artifactRegistry.service';

/**
 * Service for generating documents from completed missions
 */
export class MissionDocumentGenerationService {
  private jobs: Map<string, DocumentGenerationJob> = new Map();
  private processing: Set<string> = new Set();
  private readonly maxConcurrentJobs = 3;
  private readonly defaultMaxRetries = 3;

  /**
   * Generate documents for a completed mission
   * This is the main entry point called when a mission completes
   */
  async generateDocuments(
    missionContext: MissionContext,
    options: DocumentGenerationOptions = {}
  ): Promise<DocumentGenerationResult> {
    const startTime = Date.now();

    // Create job
    const job = await this.createJob(missionContext, options);

    try {
      // Update job status
      await this.updateJobStatus(job.id, 'processing');

      // Get team configurations
      const configs = await personaDocumentConfigService.getTeamConfigs(missionContext.teamId);

      if (configs.length === 0) {
        throw new Error(`No document configurations found for team ${missionContext.teamId}`);
      }

      // Determine which document types to generate
      const documentTypes = this.determineDocumentTypes(configs, options);
      job.documentTypes = documentTypes;

      // Generate each document
      const generatedDocs: GeneratedDocument[] = [];
      const errors: string[] = [];

      for (const docType of documentTypes) {
        try {
          // Find persona for this document type
          const config = configs.find((c) => c.documentTypes.includes(docType));
          if (!config) continue;

          // Notify start of generation
          webSocketNotificationService.emitDocumentGenerating(
            missionContext.missionId,
            job.id,
            docType,
            config.personaRole
          );

          // Generate the document
          const document = await this.generateSingleDocument(
            missionContext,
            docType,
            config,
            options
          );

          generatedDocs.push(document);

          // Register in artifact registry
          await artifactRegistryService.registerArtifact({
            teamId: missionContext.teamId,
            missionId: missionContext.missionId,
            documentId: document.id,
            documentType: docType,
            title: document.title,
            confluenceUrl: document.confluenceUrl,
          });

          // Notify completion
          webSocketNotificationService.emitDocumentComplete(
            missionContext.missionId,
            job.id,
            document.id,
            docType,
            document.confluenceUrl
          );
        } catch (error) {
          const errorMessage = error instanceof Error ? error.message : String(error);
          errors.push(`Failed to generate ${docType}: ${errorMessage}`);

          webSocketNotificationService.emitDocumentError(
            missionContext.missionId,
            job.id,
            docType,
            errorMessage,
            job.retryCount < job.maxRetries
          );
        }
      }

      // Update job with results
      job.generatedDocuments = generatedDocs;
      job.status = errors.length === 0 ? 'completed' : (generatedDocs.length > 0 ? 'completed' : 'failed');
      job.completedAt = new Date();

      const duration = Date.now() - startTime;

      return {
        success: errors.length === 0,
        jobId: job.id,
        documentsGenerated: generatedDocs.length,
        documentsFailed: errors.length,
        documents: generatedDocs,
        errors: errors.length > 0 ? errors : undefined,
        duration,
      };
    } catch (error) {
      await this.updateJobStatus(job.id, 'failed');
      throw error;
    } finally {
      this.processing.delete(job.id);
    }
  }

  /**
   * Retry generation for a failed job
   */
  async retryGeneration(jobId: string): Promise<DocumentGenerationResult> {
    const job = this.jobs.get(jobId);

    if (!job) {
      throw new Error(`Job ${jobId} not found`);
    }

    if (job.retryCount >= job.maxRetries) {
      throw new Error(`Job ${jobId} has exceeded maximum retries`);
    }

    job.retryCount++;

    // Re-fetch mission context (would come from database in real implementation)
    const missionContext: MissionContext = {
      missionId: job.missionId,
      teamId: job.teamId,
      objective: 'Retry objective',
      outcome: 'Retry outcome',
      participants: [],
      messages: [],
      artifacts: [],
      completedAt: new Date(),
    };

    return this.generateDocuments(missionContext, {
      templateOverrides: job.documentTypes.reduce(
        (acc, type) => ({ ...acc, [type]: true }),
        {}
      ),
    });
  }

  /**
   * Get the status of a generation job
   */
  async getGenerationStatus(jobId: string): Promise<DocumentGenerationJob | null> {
    return this.jobs.get(jobId) || null;
  }

  /**
   * Get all jobs for a mission
   */
  async getJobsForMission(missionId: string): Promise<DocumentGenerationJob[]> {
    const missionJobs: DocumentGenerationJob[] = [];
    for (const job of this.jobs.values()) {
      if (job.missionId === missionId) {
        missionJobs.push(job);
      }
    }
    return missionJobs;
  }

  /**
   * Cancel a queued or processing job
   */
  async cancelJob(jobId: string): Promise<boolean> {
    const job = this.jobs.get(jobId);

    if (!job) {
      return false;
    }

    if (job.status === 'completed' || job.status === 'failed') {
      return false; // Cannot cancel finished jobs
    }

    job.status = 'cancelled';
    this.processing.delete(jobId);

    return true;
  }

  private async createJob(
    context: MissionContext,
    options: DocumentGenerationOptions
  ): Promise<DocumentGenerationJob> {
    const job: DocumentGenerationJob = {
      id: this.generateJobId(),
      missionId: context.missionId,
      teamId: context.teamId,
      status: 'queued',
      documentTypes: [],
      generatedDocuments: [],
      retryCount: 0,
      maxRetries: this.defaultMaxRetries,
    };

    this.jobs.set(job.id, job);
    return job;
  }

  private async updateJobStatus(jobId: string, status: JobStatus): Promise<void> {
    const job = this.jobs.get(jobId);
    if (job) {
      job.status = status;
      if (status === 'processing') {
        job.startedAt = new Date();
        this.processing.add(jobId);
      }
    }
  }

  private determineDocumentTypes(
    configs: TeamArtifactConfig[],
    options: DocumentGenerationOptions
  ): DocumentType[] {
    // Get all document types from configs
    const allTypes = new Set<DocumentType>();
    for (const config of configs) {
      for (const docType of config.documentTypes) {
        allTypes.add(docType);
      }
    }

    // Apply template overrides if specified
    if (options.templateOverrides) {
      const filteredTypes: DocumentType[] = [];
      for (const type of allTypes) {
        if (options.templateOverrides[type] !== false) {
          filteredTypes.push(type);
        }
      }
      return filteredTypes;
    }

    return Array.from(allTypes);
  }

  private async generateSingleDocument(
    context: MissionContext,
    documentType: DocumentType,
    config: TeamArtifactConfig,
    options: DocumentGenerationOptions
  ): Promise<GeneratedDocument> {
    // Get template for document type
    const template = documentTemplateService.getTemplateByType(documentType);

    if (!template) {
      throw new Error(`No template found for document type: ${documentType}`);
    }

    // Render template with context
    const prompt = documentTemplateService.renderTemplate(template, context);

    // Generate content (simulated - would call AI service)
    const content = await this.generateContent(prompt, template, context);

    // Generate AI summary if requested
    let aiSummary: string | undefined;
    if (options.generateAiSummary !== false) {
      aiSummary = await this.generateSummary(content);
    }

    // Create document
    const document: GeneratedDocument = {
      id: this.generateDocumentId(),
      jobId: '', // Will be set by caller
      missionId: context.missionId,
      documentType,
      title: this.generateDocumentTitle(documentType, context),
      content,
      personaId: config.personaId,
      personaRole: config.personaRole,
      aiSummary,
      createdAt: new Date(),
    };

    // Publish to Confluence if requested
    if (options.publishToConfluence !== false) {
      const confluenceResult = await this.publishToConfluence(document);
      document.confluencePageId = confluenceResult.pageId;
      document.confluenceUrl = confluenceResult.url;
    }

    return document;
  }

  private async generateContent(
    prompt: string,
    template: ReturnType<typeof documentTemplateService.getTemplateByType>,
    context: MissionContext
  ): Promise<string> {
    // In production, this would call an AI service
    // For now, generate structured content based on template sections
    const sections = documentTemplateService.getOrderedSections(template!);

    const contentParts: string[] = [
      `# ${template!.name}`,
      '',
      `**Generated from Mission:** ${context.missionId}`,
      `**Team:** ${context.teamId}`,
      `**Date:** ${new Date().toISOString()}`,
      '',
    ];

    for (const section of sections) {
      contentParts.push(`## ${section.title}`);
      contentParts.push('');
      contentParts.push(this.generateSectionContent(section, context));
      contentParts.push('');
    }

    return contentParts.join('\n');
  }

  private generateSectionContent(
    section: ReturnType<typeof documentTemplateService.getOrderedSections>[0],
    context: MissionContext
  ): string {
    // Generate meaningful content based on section type and context
    const baseContent = `${section.contentPrompt}\n\n`;

    // Add context-specific content
    if (section.id.includes('overview') || section.id.includes('context')) {
      return baseContent + `Objective: ${context.objective}\n\nOutcome: ${context.outcome}`;
    }

    if (section.id.includes('requirements') || section.id.includes('scope')) {
      return baseContent + context.artifacts.map((a) => `- ${a.content}`).join('\n');
    }

    if (section.id.includes('decision')) {
      const decisions = context.messages.filter((m) => m.messageType === 'decision');
      return baseContent + decisions.map((d) => `- ${d.content}`).join('\n');
    }

    return baseContent + 'Content to be generated based on mission context.';
  }

  private async generateSummary(content: string): Promise<string> {
    // In production, this would call an AI service
    // For now, generate a basic summary
    const lines = content.split('\n').filter((l) => l.trim());
    const headings = lines.filter((l) => l.startsWith('#'));
    return `Document contains ${headings.length} sections covering: ${headings.slice(0, 3).map((h) => h.replace(/^#+\s*/, '')).join(', ')}...`;
  }

  private async publishToConfluence(
    document: GeneratedDocument
  ): Promise<{ pageId: string; url: string }> {
    // In production, this would call the Confluence API
    // For now, return simulated result
    const pageId = `page_${Date.now()}`;
    return {
      pageId,
      url: `https://confluence.example.com/wiki/spaces/MAESTRO/pages/${pageId}`,
    };
  }

  private generateDocumentTitle(documentType: DocumentType, context: MissionContext): string {
    const typeNames: Record<DocumentType, string> = {
      prd: 'Product Requirements Document',
      techDesign: 'Technical Design',
      testPlan: 'Test Plan',
      userStories: 'User Stories',
      adr: 'Architecture Decision Record',
      runbook: 'Operations Runbook',
      deploymentGuide: 'Deployment Guide',
    };

    const typeName = typeNames[documentType] || documentType;
    const shortObjective = context.objective.substring(0, 50);

    return `${typeName}: ${shortObjective}`;
  }

  private generateJobId(): string {
    return `job_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }

  private generateDocumentId(): string {
    return `doc_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }
}

// Singleton instance
export const missionDocumentGenerationService = new MissionDocumentGenerationService();
