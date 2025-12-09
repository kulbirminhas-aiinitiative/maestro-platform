/**
 * MD-2371: Mission Command Service
 * Implements AC-6: Mission Command Integration
 *
 * Integrates document generation with /mission command workflow.
 */

import {
  DocumentGenerationOptions,
  DocumentGenerationResult,
  DocumentType,
} from './types';
import { teamInteractionPipelineService } from './teamInteractionPipeline.service';
import { personaDocumentConfigService } from './personaDocumentConfig.service';
import { missionDocumentGenerationService } from './missionDocumentGeneration.service';

/**
 * Mission command options
 */
interface MissionCommandOptions {
  teamId: string;
  objective: string;
  protocol?: 'round_robin' | 'free_form' | 'moderated' | 'consensus';
  generateDocuments?: boolean;
  documentTypes?: DocumentType[];
  publishToConfluence?: boolean;
  notifyOnComplete?: boolean;
}

/**
 * Mission command result
 */
interface MissionCommandResult {
  missionId: string;
  status: 'started' | 'completed' | 'failed';
  documentsGenerated?: DocumentGenerationResult;
  error?: string;
}

/**
 * Mission status for tracking
 */
interface MissionStatus {
  missionId: string;
  teamId: string;
  phase: 'collaboration' | 'generating_documents' | 'completed' | 'failed';
  progress: number;
  documentsQueued: number;
  documentsComplete: number;
  lastUpdate: Date;
}

/**
 * Service that provides the /mission command integration
 */
export class MissionCommandService {
  private activeMissions: Map<string, MissionStatus> = new Map();

  /**
   * Start a new mission with document generation configured
   * This is the main entry point for the /mission command
   */
  async startMission(options: MissionCommandOptions): Promise<MissionCommandResult> {
    const missionId = this.generateMissionId();

    try {
      // Validate team has document generation capabilities if requested
      if (options.generateDocuments !== false) {
        const validation = await this.validateTeamCapabilities(
          options.teamId,
          options.documentTypes
        );

        if (!validation.ready) {
          console.warn(`Team ${options.teamId} missing document capabilities: ${validation.missing.join(', ')}`);
        }
      }

      // Initialize mission status
      const status: MissionStatus = {
        missionId,
        teamId: options.teamId,
        phase: 'collaboration',
        progress: 0,
        documentsQueued: 0,
        documentsComplete: 0,
        lastUpdate: new Date(),
      };

      this.activeMissions.set(missionId, status);

      // Configure document generation callback
      if (options.generateDocuments !== false) {
        teamInteractionPipelineService.onDocumentGenerationComplete(
          missionId,
          (result) => this.handleDocumentGenerationComplete(missionId, result)
        );
      }

      // In a real implementation, this would start the actual mission
      // by calling into mission.service.ts
      await this.initiateMissionCollaboration(missionId, options);

      return {
        missionId,
        status: 'started',
      };
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : String(error);

      // Clean up on failure
      this.activeMissions.delete(missionId);

      return {
        missionId,
        status: 'failed',
        error: errorMessage,
      };
    }
  }

  /**
   * Get the current status of a mission
   */
  getMissionStatus(missionId: string): MissionStatus | null {
    return this.activeMissions.get(missionId) || null;
  }

  /**
   * Get all active missions for a team
   */
  getActiveMissionsForTeam(teamId: string): MissionStatus[] {
    const teamMissions: MissionStatus[] = [];
    for (const status of this.activeMissions.values()) {
      if (status.teamId === teamId && status.phase !== 'completed' && status.phase !== 'failed') {
        teamMissions.push(status);
      }
    }
    return teamMissions;
  }

  /**
   * Cancel an active mission
   */
  async cancelMission(missionId: string): Promise<boolean> {
    const status = this.activeMissions.get(missionId);

    if (!status) {
      return false;
    }

    if (status.phase === 'completed' || status.phase === 'failed') {
      return false; // Cannot cancel finished missions
    }

    // Cancel any pending document generation
    const jobs = await missionDocumentGenerationService.getJobsForMission(missionId);
    for (const job of jobs) {
      await missionDocumentGenerationService.cancelJob(job.id);
    }

    status.phase = 'failed';
    status.lastUpdate = new Date();

    return true;
  }

  /**
   * Retry document generation for a completed mission
   */
  async retryDocumentGeneration(
    missionId: string,
    options?: DocumentGenerationOptions
  ): Promise<DocumentGenerationResult | null> {
    const status = this.activeMissions.get(missionId);

    if (!status) {
      return null;
    }

    // Get the most recent job for this mission
    const jobs = await missionDocumentGenerationService.getJobsForMission(missionId);
    const lastJob = jobs[jobs.length - 1];

    if (!lastJob) {
      // No previous job, trigger new generation
      return teamInteractionPipelineService.triggerDocumentGeneration(
        missionId,
        status.teamId,
        options
      );
    }

    // Retry the last job
    return missionDocumentGenerationService.retryGeneration(lastJob.id);
  }

  /**
   * Get available document types for a team
   */
  async getAvailableDocumentTypes(teamId: string): Promise<DocumentType[]> {
    return personaDocumentConfigService.getTeamDocumentTypes(teamId);
  }

  /**
   * Configure document generation for future missions
   */
  async configureDocumentGeneration(
    teamId: string,
    config: {
      enabledDocumentTypes: DocumentType[];
      publishToConfluence: boolean;
      generateAiSummary: boolean;
    }
  ): Promise<void> {
    // Update team interaction pipeline config
    teamInteractionPipelineService.updateConfig({
      publishToConfluence: config.publishToConfluence,
      generateAiSummary: config.generateAiSummary,
      allowedDocumentTypes: config.enabledDocumentTypes,
    });
  }

  /**
   * Get mission history with document generation results
   */
  async getMissionHistory(
    teamId: string,
    limit = 20
  ): Promise<Array<MissionStatus & { documents?: DocumentGenerationResult }>> {
    const history: Array<MissionStatus & { documents?: DocumentGenerationResult }> = [];

    for (const status of this.activeMissions.values()) {
      if (status.teamId === teamId) {
        history.push(status);
      }
    }

    return history.slice(-limit);
  }

  private async validateTeamCapabilities(
    teamId: string,
    requestedTypes?: DocumentType[]
  ): Promise<{ ready: boolean; missing: string[] }> {
    if (!requestedTypes || requestedTypes.length === 0) {
      // If no specific types requested, just check if team has any capabilities
      const types = await personaDocumentConfigService.getTeamDocumentTypes(teamId);
      return {
        ready: types.length > 0,
        missing: types.length === 0 ? ['any document type'] : [],
      };
    }

    return personaDocumentConfigService.validateTeamCapabilities(teamId, requestedTypes);
  }

  private async initiateMissionCollaboration(
    missionId: string,
    options: MissionCommandOptions
  ): Promise<void> {
    // This would integrate with the existing mission.service.ts
    // to start the actual mission collaboration

    // Update status
    const status = this.activeMissions.get(missionId);
    if (status) {
      status.progress = 10;
      status.lastUpdate = new Date();
    }

    // In production, this would:
    // 1. Create mission record in database
    // 2. Load team and persona configurations
    // 3. Initialize collaboration protocol (round_robin, free_form, etc.)
    // 4. Start WebSocket communication with participants

    console.log(`Mission ${missionId} started with protocol: ${options.protocol || 'round_robin'}`);
  }

  private handleDocumentGenerationComplete(
    missionId: string,
    result: DocumentGenerationResult
  ): void {
    const status = this.activeMissions.get(missionId);

    if (status) {
      status.phase = 'completed';
      status.progress = 100;
      status.documentsComplete = result.documentsGenerated;
      status.lastUpdate = new Date();
    }

    console.log(
      `Mission ${missionId} document generation complete: ${result.documentsGenerated} documents generated`
    );
  }

  private generateMissionId(): string {
    return `mission_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }
}

// Singleton instance
export const missionCommandService = new MissionCommandService();

/**
 * Slash command handler for /mission
 *
 * Usage:
 * /mission --team=<teamId> --objective="<objective>" [--protocol=<protocol>] [--no-docs]
 *
 * Example integration:
 *
 * import { missionCommandService } from './missionCommand.service';
 *
 * app.post('/api/commands/mission', async (req, res) => {
 *   const { teamId, objective, protocol, generateDocuments } = req.body;
 *
 *   const result = await missionCommandService.startMission({
 *     teamId,
 *     objective,
 *     protocol,
 *     generateDocuments,
 *   });
 *
 *   res.json(result);
 * });
 */
