/**
 * MD-2371: Artifact Registry Service
 * Implements AC-8: Team Artifact Registry
 *
 * Tracks and manages generated artifacts per team.
 */

import {
  ArtifactRegistryEntry,
  DocumentType,
} from './types';

/**
 * Filter options for querying artifacts
 */
interface ArtifactFilter {
  teamId?: string;
  missionId?: string;
  documentType?: DocumentType;
  tags?: string[];
  startDate?: Date;
  endDate?: Date;
}

/**
 * Artifact statistics
 */
interface ArtifactStats {
  totalArtifacts: number;
  byDocumentType: Record<DocumentType, number>;
  byTeam: Record<string, number>;
  recentActivity: Array<{ date: string; count: number }>;
}

/**
 * Artifact update data
 */
interface ArtifactUpdate {
  title?: string;
  tags?: string[];
  confluenceUrl?: string;
}

/**
 * Service for managing the team artifact registry
 */
export class ArtifactRegistryService {
  private artifacts: Map<string, ArtifactRegistryEntry> = new Map();
  private teamIndex: Map<string, Set<string>> = new Map();
  private missionIndex: Map<string, Set<string>> = new Map();
  private typeIndex: Map<DocumentType, Set<string>> = new Map();

  /**
   * Register a new artifact in the registry
   */
  async registerArtifact(data: {
    teamId: string;
    missionId: string;
    documentId: string;
    documentType: DocumentType;
    title: string;
    confluenceUrl?: string;
    tags?: string[];
  }): Promise<ArtifactRegistryEntry> {
    const id = this.generateArtifactId();
    const now = new Date();

    // Check if this is an update to an existing artifact
    const existingArtifact = await this.findExistingArtifact(
      data.teamId,
      data.missionId,
      data.documentType
    );

    if (existingArtifact) {
      // Update existing artifact with new version
      existingArtifact.version++;
      existingArtifact.documentId = data.documentId;
      existingArtifact.title = data.title;
      existingArtifact.confluenceUrl = data.confluenceUrl;
      existingArtifact.updatedAt = now;

      return existingArtifact;
    }

    // Create new artifact entry
    const entry: ArtifactRegistryEntry = {
      id,
      teamId: data.teamId,
      missionId: data.missionId,
      documentId: data.documentId,
      documentType: data.documentType,
      title: data.title,
      confluenceUrl: data.confluenceUrl,
      version: 1,
      tags: data.tags || [],
      createdAt: now,
      updatedAt: now,
    };

    // Store and index
    this.artifacts.set(id, entry);
    this.indexArtifact(entry);

    return entry;
  }

  /**
   * Get artifact by ID
   */
  async getArtifact(id: string): Promise<ArtifactRegistryEntry | null> {
    return this.artifacts.get(id) || null;
  }

  /**
   * Get all artifacts for a team
   */
  async getTeamArtifacts(teamId: string): Promise<ArtifactRegistryEntry[]> {
    const artifactIds = this.teamIndex.get(teamId);
    if (!artifactIds) {
      return [];
    }

    return Array.from(artifactIds)
      .map((id) => this.artifacts.get(id))
      .filter((a): a is ArtifactRegistryEntry => a !== undefined);
  }

  /**
   * Get all artifacts for a mission
   */
  async getMissionArtifacts(missionId: string): Promise<ArtifactRegistryEntry[]> {
    const artifactIds = this.missionIndex.get(missionId);
    if (!artifactIds) {
      return [];
    }

    return Array.from(artifactIds)
      .map((id) => this.artifacts.get(id))
      .filter((a): a is ArtifactRegistryEntry => a !== undefined);
  }

  /**
   * Get artifacts by document type
   */
  async getArtifactsByType(documentType: DocumentType): Promise<ArtifactRegistryEntry[]> {
    const artifactIds = this.typeIndex.get(documentType);
    if (!artifactIds) {
      return [];
    }

    return Array.from(artifactIds)
      .map((id) => this.artifacts.get(id))
      .filter((a): a is ArtifactRegistryEntry => a !== undefined);
  }

  /**
   * Search artifacts with filters
   */
  async searchArtifacts(filter: ArtifactFilter): Promise<ArtifactRegistryEntry[]> {
    let results = Array.from(this.artifacts.values());

    if (filter.teamId) {
      results = results.filter((a) => a.teamId === filter.teamId);
    }

    if (filter.missionId) {
      results = results.filter((a) => a.missionId === filter.missionId);
    }

    if (filter.documentType) {
      results = results.filter((a) => a.documentType === filter.documentType);
    }

    if (filter.tags && filter.tags.length > 0) {
      results = results.filter((a) =>
        filter.tags!.some((tag) => a.tags.includes(tag))
      );
    }

    if (filter.startDate) {
      results = results.filter((a) => a.createdAt >= filter.startDate!);
    }

    if (filter.endDate) {
      results = results.filter((a) => a.createdAt <= filter.endDate!);
    }

    return results.sort((a, b) => b.updatedAt.getTime() - a.updatedAt.getTime());
  }

  /**
   * Update an artifact's metadata
   */
  async updateArtifact(id: string, update: ArtifactUpdate): Promise<ArtifactRegistryEntry | null> {
    const artifact = this.artifacts.get(id);

    if (!artifact) {
      return null;
    }

    if (update.title !== undefined) {
      artifact.title = update.title;
    }

    if (update.tags !== undefined) {
      artifact.tags = update.tags;
    }

    if (update.confluenceUrl !== undefined) {
      artifact.confluenceUrl = update.confluenceUrl;
    }

    artifact.updatedAt = new Date();

    return artifact;
  }

  /**
   * Add tags to an artifact
   */
  async addTags(id: string, tags: string[]): Promise<ArtifactRegistryEntry | null> {
    const artifact = this.artifacts.get(id);

    if (!artifact) {
      return null;
    }

    const uniqueTags = new Set([...artifact.tags, ...tags]);
    artifact.tags = Array.from(uniqueTags);
    artifact.updatedAt = new Date();

    return artifact;
  }

  /**
   * Remove tags from an artifact
   */
  async removeTags(id: string, tags: string[]): Promise<ArtifactRegistryEntry | null> {
    const artifact = this.artifacts.get(id);

    if (!artifact) {
      return null;
    }

    artifact.tags = artifact.tags.filter((t) => !tags.includes(t));
    artifact.updatedAt = new Date();

    return artifact;
  }

  /**
   * Delete an artifact from the registry
   */
  async deleteArtifact(id: string): Promise<boolean> {
    const artifact = this.artifacts.get(id);

    if (!artifact) {
      return false;
    }

    // Remove from indexes
    this.removeFromIndex(artifact);

    // Remove from storage
    this.artifacts.delete(id);

    return true;
  }

  /**
   * Get artifact statistics
   */
  async getStatistics(teamId?: string): Promise<ArtifactStats> {
    let artifacts = Array.from(this.artifacts.values());

    if (teamId) {
      artifacts = artifacts.filter((a) => a.teamId === teamId);
    }

    // Count by document type
    const byDocumentType: Record<string, number> = {};
    for (const artifact of artifacts) {
      byDocumentType[artifact.documentType] = (byDocumentType[artifact.documentType] || 0) + 1;
    }

    // Count by team
    const byTeam: Record<string, number> = {};
    for (const artifact of artifacts) {
      byTeam[artifact.teamId] = (byTeam[artifact.teamId] || 0) + 1;
    }

    // Recent activity (last 7 days)
    const now = new Date();
    const recentActivity: Array<{ date: string; count: number }> = [];

    for (let i = 6; i >= 0; i--) {
      const date = new Date(now);
      date.setDate(date.getDate() - i);
      const dateStr = date.toISOString().split('T')[0];

      const count = artifacts.filter((a) => {
        const artifactDate = a.createdAt.toISOString().split('T')[0];
        return artifactDate === dateStr;
      }).length;

      recentActivity.push({ date: dateStr, count });
    }

    return {
      totalArtifacts: artifacts.length,
      byDocumentType: byDocumentType as Record<DocumentType, number>,
      byTeam,
      recentActivity,
    };
  }

  /**
   * Get latest artifact of a specific type for a team
   */
  async getLatestArtifact(
    teamId: string,
    documentType: DocumentType
  ): Promise<ArtifactRegistryEntry | null> {
    const teamArtifacts = await this.getTeamArtifacts(teamId);

    const typeArtifacts = teamArtifacts
      .filter((a) => a.documentType === documentType)
      .sort((a, b) => b.updatedAt.getTime() - a.updatedAt.getTime());

    return typeArtifacts[0] || null;
  }

  /**
   * Get artifact version history
   */
  async getVersionHistory(
    teamId: string,
    missionId: string,
    documentType: DocumentType
  ): Promise<ArtifactRegistryEntry[]> {
    const artifacts = await this.searchArtifacts({
      teamId,
      missionId,
      documentType,
    });

    return artifacts.sort((a, b) => a.version - b.version);
  }

  private async findExistingArtifact(
    teamId: string,
    missionId: string,
    documentType: DocumentType
  ): Promise<ArtifactRegistryEntry | null> {
    const artifacts = await this.searchArtifacts({
      teamId,
      missionId,
      documentType,
    });

    return artifacts[0] || null;
  }

  private indexArtifact(artifact: ArtifactRegistryEntry): void {
    // Team index
    if (!this.teamIndex.has(artifact.teamId)) {
      this.teamIndex.set(artifact.teamId, new Set());
    }
    this.teamIndex.get(artifact.teamId)!.add(artifact.id);

    // Mission index
    if (!this.missionIndex.has(artifact.missionId)) {
      this.missionIndex.set(artifact.missionId, new Set());
    }
    this.missionIndex.get(artifact.missionId)!.add(artifact.id);

    // Type index
    if (!this.typeIndex.has(artifact.documentType)) {
      this.typeIndex.set(artifact.documentType, new Set());
    }
    this.typeIndex.get(artifact.documentType)!.add(artifact.id);
  }

  private removeFromIndex(artifact: ArtifactRegistryEntry): void {
    this.teamIndex.get(artifact.teamId)?.delete(artifact.id);
    this.missionIndex.get(artifact.missionId)?.delete(artifact.id);
    this.typeIndex.get(artifact.documentType)?.delete(artifact.id);
  }

  private generateArtifactId(): string {
    return `artifact_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }
}

// Singleton instance
export const artifactRegistryService = new ArtifactRegistryService();
