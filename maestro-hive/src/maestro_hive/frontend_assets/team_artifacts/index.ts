/**
 * MD-2371: Mission-Document Workflow
 * Main entry point for all services
 */

// Types
export * from './types';

// Services - AC-1: Persona Document Configuration
export {
  PersonaDocumentConfigService,
  personaDocumentConfigService
} from './personaDocumentConfig.service';

// Services - AC-2: Document Generation Service
export {
  MissionDocumentGenerationService,
  missionDocumentGenerationService
} from './missionDocumentGeneration.service';

// Services - AC-3: Document Template System
export {
  DocumentTemplateService,
  documentTemplateService
} from './documentTemplate.service';

// Services - AC-4: Team Interaction Pipeline
export {
  TeamInteractionPipelineService,
  teamInteractionPipelineService,
  onMissionComplete
} from './teamInteractionPipeline.service';

// Services - AC-5: WebSocket Notification
export {
  WebSocketNotificationService,
  webSocketNotificationService,
  getMissionRoom,
  getTeamRoom
} from './webSocketNotification.service';

// Services - AC-6: Mission Command Integration
export {
  MissionCommandService,
  missionCommandService
} from './missionCommand.service';

// Services - AC-8: Artifact Registry
export {
  ArtifactRegistryService,
  artifactRegistryService
} from './artifactRegistry.service';

// React Components - AC-7: Frontend Real-time Reflection
export {
  MissionDocumentsPanel,
  styles as MissionDocumentsPanelStyles
} from './MissionDocumentsPanel';
