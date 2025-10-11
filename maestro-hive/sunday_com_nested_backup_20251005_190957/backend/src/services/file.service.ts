import { prisma } from '@/config/database';
import { Logger } from '@/config/logger';
import { RedisService } from '@/config/redis';
import { FileUploadData, UploadedFile } from '@/types';
import { config } from '@/config';
import { v4 as uuidv4 } from 'uuid';
import crypto from 'crypto';
import path from 'path';

interface FileStorage {
  upload(buffer: Buffer, key: string, mimeType: string): Promise<string>;
  delete(key: string): Promise<void>;
  getUrl(key: string): string;
  getThumbnailUrl(key: string): string;
}

interface FileValidationRules {
  maxSize: number; // in bytes
  allowedTypes: string[];
  allowedExtensions: string[];
}

export class FileService {
  private static readonly DEFAULT_MAX_SIZE = 50 * 1024 * 1024; // 50MB
  private static readonly ALLOWED_TYPES = [
    'image/jpeg',
    'image/png',
    'image/gif',
    'image/webp',
    'application/pdf',
    'application/msword',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'application/vnd.ms-excel',
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    'text/plain',
    'text/csv',
    'application/zip',
    'application/x-zip-compressed',
  ];

  private static readonly ALLOWED_EXTENSIONS = [
    '.jpg', '.jpeg', '.png', '.gif', '.webp',
    '.pdf', '.doc', '.docx', '.xls', '.xlsx',
    '.txt', '.csv', '.zip',
  ];

  private static storage: FileStorage;

  /**
   * Initialize file storage
   */
  static initialize(): void {
    // In production, you'd configure AWS S3, Google Cloud Storage, etc.
    this.storage = new LocalFileStorage();
  }

  /**
   * Upload a file
   */
  static async uploadFile(
    organizationId: string,
    userId: string,
    fileData: FileUploadData,
    entityType?: 'item' | 'comment' | 'board',
    entityId?: string,
    validationRules?: Partial<FileValidationRules>
  ): Promise<UploadedFile> {
    try {
      // Verify user has permission to upload files
      const hasPermission = await this.verifyUploadPermission(organizationId, userId);
      if (!hasPermission) {
        throw new Error('Permission denied');
      }

      // Validate file
      await this.validateFile(fileData, validationRules);

      // Generate unique file key
      const fileExtension = path.extname(fileData.originalName);
      const fileKey = `${organizationId}/${userId}/${Date.now()}_${uuidv4()}${fileExtension}`;

      // Calculate checksum
      const checksum = crypto.createHash('sha256').update(fileData.buffer).digest('hex');

      // Check for duplicate files
      const existingFile = await prisma.file.findFirst({
        where: {
          organizationId,
          checksum,
          deletedAt: null,
        },
      });

      if (existingFile) {
        // Return existing file if it's the same
        const url = this.storage.getUrl(existingFile.fileKey);
        const thumbnailUrl = this.isImageFile(existingFile.mimeType || '')
          ? this.storage.getThumbnailUrl(existingFile.fileKey)
          : undefined;

        return {
          id: existingFile.id,
          originalName: existingFile.originalName,
          fileKey: existingFile.fileKey,
          fileSize: Number(existingFile.fileSize),
          mimeType: existingFile.mimeType,
          url,
          thumbnailUrl,
        };
      }

      // Upload to storage
      const uploadUrl = await this.storage.upload(fileData.buffer, fileKey, fileData.mimeType);

      // Generate thumbnail for images
      let thumbnailKey: string | undefined;
      if (this.isImageFile(fileData.mimeType)) {
        thumbnailKey = await this.generateThumbnail(fileData.buffer, fileKey);
      }

      // Save file record to database
      const file = await prisma.file.create({
        data: {
          id: uuidv4(),
          organizationId,
          originalName: fileData.originalName,
          fileKey,
          fileSize: fileData.fileSize,
          mimeType: fileData.mimeType,
          checksum,
          thumbnailKey,
          uploadedBy: userId,
        },
      });

      // Create attachment record if entity is specified
      if (entityType && entityId) {
        await this.attachFile(file.id, entityType, entityId, userId);
      }

      // Track file upload
      await this.trackFileEvent('file_uploaded', file.id, userId, organizationId, {
        fileSize: fileData.fileSize,
        mimeType: fileData.mimeType,
        entityType,
        entityId,
      });

      Logger.file(`File uploaded: ${fileData.originalName}`, {
        fileId: file.id,
        organizationId,
        userId,
        fileSize: fileData.fileSize,
      });

      const url = this.storage.getUrl(fileKey);
      const thumbnailUrl = thumbnailKey ? this.storage.getThumbnailUrl(thumbnailKey) : undefined;

      return {
        id: file.id,
        originalName: file.originalName,
        fileKey: file.fileKey,
        fileSize: Number(file.fileSize),
        mimeType: file.mimeType,
        url,
        thumbnailUrl,
      };
    } catch (error) {
      Logger.error('File upload failed', error as Error);
      throw error;
    }
  }

  /**
   * Get file by ID
   */
  static async getFile(fileId: string, userId: string): Promise<UploadedFile> {
    try {
      const file = await prisma.file.findFirst({
        where: {
          id: fileId,
          deletedAt: null,
        },
        include: {
          organization: true,
          uploadedByUser: {
            select: { id: true, firstName: true, lastName: true, email: true },
          },
        },
      });

      if (!file) {
        throw new Error('File not found');
      }

      // Verify access permission
      const hasAccess = await this.verifyFileAccess(file.organizationId, userId);
      if (!hasAccess) {
        throw new Error('Access denied');
      }

      const url = this.storage.getUrl(file.fileKey);
      const thumbnailUrl = file.thumbnailKey ? this.storage.getThumbnailUrl(file.thumbnailKey) : undefined;

      return {
        id: file.id,
        originalName: file.originalName,
        fileKey: file.fileKey,
        fileSize: Number(file.fileSize),
        mimeType: file.mimeType,
        url,
        thumbnailUrl,
      };
    } catch (error) {
      Logger.error('Get file failed', error as Error);
      throw error;
    }
  }

  /**
   * Delete file
   */
  static async deleteFile(fileId: string, userId: string): Promise<void> {
    try {
      const file = await prisma.file.findFirst({
        where: {
          id: fileId,
          deletedAt: null,
        },
      });

      if (!file) {
        throw new Error('File not found');
      }

      // Verify permission (file owner or organization admin)
      const hasPermission = await this.verifyDeletePermission(file.organizationId, file.uploadedBy, userId);
      if (!hasPermission) {
        throw new Error('Permission denied');
      }

      // Soft delete file record
      await prisma.file.update({
        where: { id: fileId },
        data: { deletedAt: new Date() },
      });

      // Remove from storage (in background)
      setImmediate(async () => {
        try {
          await this.storage.delete(file.fileKey);
          if (file.thumbnailKey) {
            await this.storage.delete(file.thumbnailKey);
          }
        } catch (error) {
          Logger.error('Failed to delete file from storage', error as Error);
        }
      });

      // Track file deletion
      await this.trackFileEvent('file_deleted', fileId, userId, file.organizationId);

      Logger.file(`File deleted: ${file.originalName}`, {
        fileId,
        organizationId: file.organizationId,
        userId,
      });
    } catch (error) {
      Logger.error('File deletion failed', error as Error);
      throw error;
    }
  }

  /**
   * Attach file to entity
   */
  static async attachFile(
    fileId: string,
    entityType: 'item' | 'comment' | 'board',
    entityId: string,
    userId: string
  ): Promise<void> {
    try {
      const file = await prisma.file.findFirst({
        where: {
          id: fileId,
          deletedAt: null,
        },
      });

      if (!file) {
        throw new Error('File not found');
      }

      // Verify access to entity
      const hasAccess = await this.verifyEntityAccess(entityType, entityId, userId);
      if (!hasAccess) {
        throw new Error('Access denied');
      }

      // Check if attachment already exists
      const existingAttachment = await prisma.fileAttachment.findFirst({
        where: {
          fileId,
          entityType,
          entityId,
        },
      });

      if (existingAttachment) {
        return; // Already attached
      }

      await prisma.fileAttachment.create({
        data: {
          id: uuidv4(),
          fileId,
          entityType,
          entityId,
          attachedBy: userId,
        },
      });

      Logger.file(`File attached to ${entityType}: ${entityId}`, {
        fileId,
        entityType,
        entityId,
        userId,
      });
    } catch (error) {
      Logger.error('Attach file failed', error as Error);
      throw error;
    }
  }

  /**
   * Detach file from entity
   */
  static async detachFile(
    fileId: string,
    entityType: 'item' | 'comment' | 'board',
    entityId: string,
    userId: string
  ): Promise<void> {
    try {
      // Verify access to entity
      const hasAccess = await this.verifyEntityAccess(entityType, entityId, userId);
      if (!hasAccess) {
        throw new Error('Access denied');
      }

      const attachment = await prisma.fileAttachment.findFirst({
        where: {
          fileId,
          entityType,
          entityId,
        },
      });

      if (!attachment) {
        throw new Error('Attachment not found');
      }

      await prisma.fileAttachment.delete({
        where: { id: attachment.id },
      });

      Logger.file(`File detached from ${entityType}: ${entityId}`, {
        fileId,
        entityType,
        entityId,
        userId,
      });
    } catch (error) {
      Logger.error('Detach file failed', error as Error);
      throw error;
    }
  }

  /**
   * Get files attached to entity
   */
  static async getEntityFiles(
    entityType: 'item' | 'comment' | 'board',
    entityId: string,
    userId: string
  ): Promise<UploadedFile[]> {
    try {
      // Verify access to entity
      const hasAccess = await this.verifyEntityAccess(entityType, entityId, userId);
      if (!hasAccess) {
        throw new Error('Access denied');
      }

      const attachments = await prisma.fileAttachment.findMany({
        where: {
          entityType,
          entityId,
        },
        include: {
          file: {
            where: { deletedAt: null },
            include: {
              uploadedByUser: {
                select: { id: true, firstName: true, lastName: true },
              },
            },
          },
        },
        orderBy: { attachedAt: 'desc' },
      });

      const files: UploadedFile[] = attachments
        .filter(attachment => attachment.file)
        .map(attachment => {
          const file = attachment.file!;
          const url = this.storage.getUrl(file.fileKey);
          const thumbnailUrl = file.thumbnailKey ? this.storage.getThumbnailUrl(file.thumbnailKey) : undefined;

          return {
            id: file.id,
            originalName: file.originalName,
            fileKey: file.fileKey,
            fileSize: Number(file.fileSize),
            mimeType: file.mimeType,
            url,
            thumbnailUrl,
          };
        });

      return files;
    } catch (error) {
      Logger.error('Get entity files failed', error as Error);
      throw error;
    }
  }

  /**
   * Get organization files with pagination
   */
  static async getOrganizationFiles(
    organizationId: string,
    userId: string,
    page: number = 1,
    limit: number = 20,
    filter: {
      type?: 'image' | 'document' | 'archive' | 'other';
      search?: string;
      uploadedBy?: string;
    } = {}
  ): Promise<{
    files: UploadedFile[];
    total: number;
    page: number;
    totalPages: number;
  }> {
    try {
      // Verify access
      const hasAccess = await this.verifyFileAccess(organizationId, userId);
      if (!hasAccess) {
        throw new Error('Access denied');
      }

      const offset = (page - 1) * limit;

      // Build where clause
      const where: any = {
        organizationId,
        deletedAt: null,
      };

      if (filter.search) {
        where.originalName = {
          contains: filter.search,
          mode: 'insensitive',
        };
      }

      if (filter.uploadedBy) {
        where.uploadedBy = filter.uploadedBy;
      }

      if (filter.type) {
        switch (filter.type) {
          case 'image':
            where.mimeType = { startsWith: 'image/' };
            break;
          case 'document':
            where.mimeType = {
              in: [
                'application/pdf',
                'application/msword',
                'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                'application/vnd.ms-excel',
                'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                'text/plain',
                'text/csv',
              ],
            };
            break;
          case 'archive':
            where.mimeType = {
              in: ['application/zip', 'application/x-zip-compressed'],
            };
            break;
          case 'other':
            where.mimeType = {
              notIn: [
                ...this.ALLOWED_TYPES.filter(type =>
                  type.startsWith('image/') ||
                  ['application/pdf', 'application/msword', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                   'application/vnd.ms-excel', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                   'text/plain', 'text/csv', 'application/zip', 'application/x-zip-compressed'].includes(type)
                ),
              ],
            };
            break;
        }
      }

      const [files, total] = await Promise.all([
        prisma.file.findMany({
          where,
          include: {
            uploadedByUser: {
              select: { id: true, firstName: true, lastName: true, email: true },
            },
            attachments: {
              select: { entityType: true, entityId: true },
              take: 3, // Show first few attachments
            },
          },
          orderBy: { createdAt: 'desc' },
          skip: offset,
          take: limit,
        }),
        prisma.file.count({ where }),
      ]);

      const filesWithUrls: UploadedFile[] = files.map(file => {
        const url = this.storage.getUrl(file.fileKey);
        const thumbnailUrl = file.thumbnailKey ? this.storage.getThumbnailUrl(file.thumbnailKey) : undefined;

        return {
          id: file.id,
          originalName: file.originalName,
          fileKey: file.fileKey,
          fileSize: Number(file.fileSize),
          mimeType: file.mimeType,
          url,
          thumbnailUrl,
        };
      });

      return {
        files: filesWithUrls,
        total,
        page,
        totalPages: Math.ceil(total / limit),
      };
    } catch (error) {
      Logger.error('Get organization files failed', error as Error);
      throw error;
    }
  }

  /**
   * Get file statistics for organization
   */
  static async getFileStatistics(
    organizationId: string,
    userId: string
  ): Promise<{
    totalFiles: number;
    totalSize: bigint;
    filesByType: Record<string, number>;
    storageQuota: {
      used: bigint;
      limit: bigint;
      percentage: number;
    };
  }> {
    try {
      // Verify access
      const hasAccess = await this.verifyFileAccess(organizationId, userId);
      if (!hasAccess) {
        throw new Error('Access denied');
      }

      const [stats, typeStats] = await Promise.all([
        prisma.file.aggregate({
          where: {
            organizationId,
            deletedAt: null,
          },
          _count: true,
          _sum: { fileSize: true },
        }),
        prisma.file.groupBy({
          by: ['mimeType'],
          where: {
            organizationId,
            deletedAt: null,
          },
          _count: true,
        }),
      ]);

      const filesByType: Record<string, number> = {};
      typeStats.forEach(stat => {
        if (stat.mimeType) {
          filesByType[stat.mimeType] = stat._count;
        }
      });

      // Get organization storage quota (would be configured per plan)
      const organization = await prisma.organization.findUnique({
        where: { id: organizationId },
        select: { subscriptionPlan: true },
      });

      // Define storage limits by plan
      const storageLimit = this.getStorageLimitByPlan(organization?.subscriptionPlan || 'free');
      const usedStorage = stats._sum.fileSize || BigInt(0);
      const percentage = Number(usedStorage) / Number(storageLimit) * 100;

      return {
        totalFiles: stats._count || 0,
        totalSize: usedStorage,
        filesByType,
        storageQuota: {
          used: usedStorage,
          limit: storageLimit,
          percentage: Math.round(percentage * 100) / 100,
        },
      };
    } catch (error) {
      Logger.error('Get file statistics failed', error as Error);
      throw error;
    }
  }

  // ============================================================================
  // PRIVATE HELPER METHODS
  // ============================================================================

  /**
   * Validate uploaded file
   */
  private static async validateFile(
    fileData: FileUploadData,
    customRules?: Partial<FileValidationRules>
  ): Promise<void> {
    const rules: FileValidationRules = {
      maxSize: customRules?.maxSize || this.DEFAULT_MAX_SIZE,
      allowedTypes: customRules?.allowedTypes || this.ALLOWED_TYPES,
      allowedExtensions: customRules?.allowedExtensions || this.ALLOWED_EXTENSIONS,
    };

    // Check file size
    if (fileData.fileSize > rules.maxSize) {
      throw new Error(`File size exceeds limit of ${Math.round(rules.maxSize / 1024 / 1024)}MB`);
    }

    // Check MIME type
    if (!rules.allowedTypes.includes(fileData.mimeType)) {
      throw new Error(`File type ${fileData.mimeType} is not allowed`);
    }

    // Check file extension
    const extension = path.extname(fileData.originalName).toLowerCase();
    if (!rules.allowedExtensions.includes(extension)) {
      throw new Error(`File extension ${extension} is not allowed`);
    }

    // Additional security checks
    if (await this.containsMaliciousContent(fileData.buffer)) {
      throw new Error('File contains potentially malicious content');
    }
  }

  /**
   * Check for malicious content (basic implementation)
   */
  private static async containsMaliciousContent(buffer: Buffer): Promise<boolean> {
    // Basic check for common malicious patterns
    const content = buffer.toString('utf8', 0, Math.min(buffer.length, 1024));
    const maliciousPatterns = [
      /<script/i,
      /javascript:/i,
      /vbscript:/i,
      /onload=/i,
      /onerror=/i,
    ];

    return maliciousPatterns.some(pattern => pattern.test(content));
  }

  /**
   * Check if file is an image
   */
  private static isImageFile(mimeType: string): boolean {
    return mimeType.startsWith('image/');
  }

  /**
   * Generate thumbnail for images
   */
  private static async generateThumbnail(buffer: Buffer, originalKey: string): Promise<string> {
    // In a real implementation, you'd use a library like sharp to generate thumbnails
    // For now, return a placeholder thumbnail key
    const thumbnailKey = originalKey.replace(/(\.[^.]+)$/, '_thumb$1');

    // Simulate thumbnail generation
    // await this.storage.upload(buffer, thumbnailKey, 'image/jpeg');

    return thumbnailKey;
  }

  /**
   * Track file events for analytics
   */
  private static async trackFileEvent(
    eventType: string,
    fileId: string,
    userId: string,
    organizationId: string,
    properties?: Record<string, any>
  ): Promise<void> {
    try {
      await prisma.activityLog.create({
        data: {
          id: uuidv4(),
          organizationId,
          userId,
          action: eventType,
          entityType: 'file',
          entityId: fileId,
          metadata: properties || {},
        },
      });
    } catch (error) {
      Logger.error('Failed to track file event', error as Error);
    }
  }

  /**
   * Verify upload permission
   */
  private static async verifyUploadPermission(organizationId: string, userId: string): Promise<boolean> {
    try {
      const membership = await prisma.organizationMember.findFirst({
        where: {
          organizationId,
          userId,
          status: 'active',
        },
      });

      return !!membership;
    } catch (error) {
      return false;
    }
  }

  /**
   * Verify file access permission
   */
  private static async verifyFileAccess(organizationId: string, userId: string): Promise<boolean> {
    return this.verifyUploadPermission(organizationId, userId);
  }

  /**
   * Verify delete permission
   */
  private static async verifyDeletePermission(
    organizationId: string,
    fileOwnerId: string,
    userId: string
  ): Promise<boolean> {
    // Allow file owner to delete their own files
    if (fileOwnerId === userId) {
      return true;
    }

    // Allow organization admins to delete any file
    try {
      const membership = await prisma.organizationMember.findFirst({
        where: {
          organizationId,
          userId,
          status: 'active',
          role: { in: ['owner', 'admin'] },
        },
      });

      return !!membership;
    } catch (error) {
      return false;
    }
  }

  /**
   * Verify entity access permission
   */
  private static async verifyEntityAccess(
    entityType: string,
    entityId: string,
    userId: string
  ): Promise<boolean> {
    try {
      switch (entityType) {
        case 'item':
          const item = await prisma.item.findFirst({
            where: {
              id: entityId,
              board: {
                OR: [
                  { isPrivate: false },
                  {
                    members: { some: { userId } },
                  },
                  {
                    workspace: {
                      members: { some: { userId } },
                    },
                  },
                ],
              },
            },
          });
          return !!item;

        case 'board':
          const board = await prisma.board.findFirst({
            where: {
              id: entityId,
              OR: [
                { isPrivate: false },
                {
                  members: { some: { userId } },
                },
                {
                  workspace: {
                    members: { some: { userId } },
                  },
                },
              ],
            },
          });
          return !!board;

        case 'comment':
          const comment = await prisma.comment.findFirst({
            where: {
              id: entityId,
              item: {
                board: {
                  OR: [
                    { isPrivate: false },
                    {
                      members: { some: { userId } },
                    },
                    {
                      workspace: {
                        members: { some: { userId } },
                      },
                    },
                  ],
                },
              },
            },
          });
          return !!comment;

        default:
          return false;
      }
    } catch (error) {
      return false;
    }
  }

  /**
   * Get storage limit by subscription plan
   */
  private static getStorageLimitByPlan(plan: string): bigint {
    switch (plan) {
      case 'free':
        return BigInt(1024 * 1024 * 1024); // 1GB
      case 'basic':
        return BigInt(5 * 1024 * 1024 * 1024); // 5GB
      case 'standard':
        return BigInt(25 * 1024 * 1024 * 1024); // 25GB
      case 'enterprise':
        return BigInt(100 * 1024 * 1024 * 1024); // 100GB
      default:
        return BigInt(1024 * 1024 * 1024); // 1GB default
    }
  }
}

/**
 * Local file storage implementation (for development)
 * In production, you'd use AWS S3, Google Cloud Storage, etc.
 */
class LocalFileStorage implements FileStorage {
  private readonly basePath: string;

  constructor() {
    this.basePath = config.storage?.localPath || './uploads';
  }

  async upload(buffer: Buffer, key: string, mimeType: string): Promise<string> {
    // In a real implementation, this would save to local filesystem
    // For now, simulate the upload
    return Promise.resolve(`${this.basePath}/${key}`);
  }

  async delete(key: string): Promise<void> {
    // In a real implementation, this would delete from local filesystem
    return Promise.resolve();
  }

  getUrl(key: string): string {
    // In production, this would return a proper URL
    return `/files/${key}`;
  }

  getThumbnailUrl(key: string): string {
    return `/files/thumbnails/${key}`;
  }
}

// Initialize file service
FileService.initialize();