/**
 * MD-2371: WebSocket Notification Service
 * Implements AC-5: WebSocket Async Notification
 *
 * Emits WebSocket events for document generation progress and completion.
 */

import {
  DocumentType,
  DocumentWebSocketEvent,
  DocumentGeneratingEvent,
  DocumentProgressEvent,
  DocumentCompleteEvent,
  DocumentErrorEvent,
} from './types';

/**
 * WebSocket event subscriber callback
 */
type EventSubscriber = (event: DocumentWebSocketEvent) => void;

/**
 * WebSocket connection interface
 * This would be implemented by the actual WebSocket library (e.g., Socket.IO)
 */
interface WebSocketConnection {
  emit(event: string, data: unknown): void;
  to(room: string): WebSocketConnection;
  broadcast: WebSocketConnection;
}

/**
 * Service for managing WebSocket notifications for document generation
 */
export class WebSocketNotificationService {
  private subscribers: Map<string, Set<EventSubscriber>> = new Map();
  private eventLog: DocumentWebSocketEvent[] = [];
  private readonly maxEventLogSize = 1000;
  private io: WebSocketConnection | null = null;

  /**
   * Initialize with a WebSocket server instance
   */
  initialize(io: WebSocketConnection): void {
    this.io = io;
  }

  /**
   * Emit a document:generating event
   */
  emitDocumentGenerating(
    missionId: string,
    jobId: string,
    documentType: DocumentType,
    persona: string
  ): void {
    const event: DocumentGeneratingEvent = {
      type: 'document:generating',
      payload: {
        missionId,
        jobId,
        documentType,
        persona,
        progress: 0,
      },
    };

    this.emit(event);
  }

  /**
   * Emit a document:progress event
   */
  emitDocumentProgress(
    missionId: string,
    jobId: string,
    documentType: DocumentType,
    progress: number,
    message: string
  ): void {
    const event: DocumentProgressEvent = {
      type: 'document:progress',
      payload: {
        missionId,
        jobId,
        documentType,
        progress: Math.min(100, Math.max(0, progress)),
        message,
      },
    };

    this.emit(event);
  }

  /**
   * Emit a document:complete event
   */
  emitDocumentComplete(
    missionId: string,
    jobId: string,
    documentId: string,
    documentType: DocumentType,
    confluenceUrl?: string
  ): void {
    const event: DocumentCompleteEvent = {
      type: 'document:complete',
      payload: {
        missionId,
        jobId,
        documentId,
        documentType,
        confluenceUrl,
      },
    };

    this.emit(event);
  }

  /**
   * Emit a document:error event
   */
  emitDocumentError(
    missionId: string,
    jobId: string,
    documentType: DocumentType,
    error: string,
    retryable: boolean
  ): void {
    const event: DocumentErrorEvent = {
      type: 'document:error',
      payload: {
        missionId,
        jobId,
        documentType,
        error,
        retryable,
      },
    };

    this.emit(event);
  }

  /**
   * Subscribe to document generation events for a specific mission
   */
  subscribe(missionId: string, callback: EventSubscriber): () => void {
    if (!this.subscribers.has(missionId)) {
      this.subscribers.set(missionId, new Set());
    }

    this.subscribers.get(missionId)!.add(callback);

    // Return unsubscribe function
    return () => {
      const missionSubscribers = this.subscribers.get(missionId);
      if (missionSubscribers) {
        missionSubscribers.delete(callback);
        if (missionSubscribers.size === 0) {
          this.subscribers.delete(missionId);
        }
      }
    };
  }

  /**
   * Subscribe to all document generation events
   */
  subscribeAll(callback: EventSubscriber): () => void {
    return this.subscribe('*', callback);
  }

  /**
   * Get recent events for a mission
   */
  getRecentEvents(missionId: string, limit = 50): DocumentWebSocketEvent[] {
    return this.eventLog
      .filter((event) => event.payload.missionId === missionId)
      .slice(-limit);
  }

  /**
   * Get recent events for a job
   */
  getJobEvents(jobId: string): DocumentWebSocketEvent[] {
    return this.eventLog.filter((event) => event.payload.jobId === jobId);
  }

  /**
   * Clear event log for a mission
   */
  clearEventLog(missionId: string): void {
    this.eventLog = this.eventLog.filter(
      (event) => event.payload.missionId !== missionId
    );
  }

  /**
   * Get all active subscriptions count
   */
  getActiveSubscriptionsCount(): number {
    let count = 0;
    for (const subscribers of this.subscribers.values()) {
      count += subscribers.size;
    }
    return count;
  }

  /**
   * Check if there are active subscribers for a mission
   */
  hasSubscribers(missionId: string): boolean {
    return (
      (this.subscribers.get(missionId)?.size || 0) > 0 ||
      (this.subscribers.get('*')?.size || 0) > 0
    );
  }

  private emit(event: DocumentWebSocketEvent): void {
    // Log event
    this.logEvent(event);

    // Emit via WebSocket if initialized
    if (this.io) {
      this.io.to(`mission:${event.payload.missionId}`).emit(event.type, event.payload);
    }

    // Notify mission-specific subscribers
    const missionSubscribers = this.subscribers.get(event.payload.missionId);
    if (missionSubscribers) {
      for (const subscriber of missionSubscribers) {
        try {
          subscriber(event);
        } catch (error) {
          console.error('Error in event subscriber:', error);
        }
      }
    }

    // Notify global subscribers
    const globalSubscribers = this.subscribers.get('*');
    if (globalSubscribers) {
      for (const subscriber of globalSubscribers) {
        try {
          subscriber(event);
        } catch (error) {
          console.error('Error in global event subscriber:', error);
        }
      }
    }
  }

  private logEvent(event: DocumentWebSocketEvent): void {
    this.eventLog.push(event);

    // Trim log if too large
    if (this.eventLog.length > this.maxEventLogSize) {
      this.eventLog = this.eventLog.slice(-this.maxEventLogSize / 2);
    }
  }
}

// Singleton instance
export const webSocketNotificationService = new WebSocketNotificationService();

/**
 * Utility function to create a WebSocket room name for a mission
 */
export function getMissionRoom(missionId: string): string {
  return `mission:${missionId}`;
}

/**
 * Utility function to create a WebSocket room name for a team
 */
export function getTeamRoom(teamId: string): string {
  return `team:${teamId}`;
}

/**
 * Example integration with Socket.IO:
 *
 * import { Server } from 'socket.io';
 * import { webSocketNotificationService } from './webSocketNotification.service';
 *
 * const io = new Server(httpServer);
 *
 * webSocketNotificationService.initialize(io);
 *
 * io.on('connection', (socket) => {
 *   socket.on('join:mission', (missionId) => {
 *     socket.join(`mission:${missionId}`);
 *   });
 *
 *   socket.on('leave:mission', (missionId) => {
 *     socket.leave(`mission:${missionId}`);
 *   });
 * });
 */
