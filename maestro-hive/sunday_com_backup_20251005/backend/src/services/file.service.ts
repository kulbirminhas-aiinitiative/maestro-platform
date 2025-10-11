import { S3Client, PutObjectCommand, GetObjectCommand, DeleteObjectCommand } from '@aws-sdk/client-s3';
import { getSignedUrl } from '@aws-sdk/s3-request-presigner';
import { prisma } from '@/config/database';
import { Logger } from '@/config/logger';
import { config } from '@/config';
import { FileUploadData, UploadedFile } from '@/types';
import { v4 as uuidv4 } from 'uuid';
import path from 'path';
import sharp from 'sharp';

interface S3Config {
  bucketName: string;
  region: string;
  accessKeyId: string;
  secretAccessKey: string;
  endpoint?: string;
}

export class FileService {
  private static s3Client: S3Client;
  private static s3Config: S3Config;

  /**
   * Initialize S3 client
   */
  static initialize() {
    this.s3Config = {
      bucketName: config.aws.s3Bucket,
      region: config.aws.region,
      accessKeyId: config.aws.accessKeyId!,
      secretAccessKey: config.aws.secretAccessKey!,
      endpoint: undefined, // Use default AWS endpoint
    };

    this.s3Client = new S3Client({
      region: this.s3Config.region,
      credentials: {
        accessKeyId: this.s3Config.accessKeyId,
        secretAccessKey: this.s3Config.secretAccessKey,
      },
      ...(this.s3Config.endpoint && { endpoint: this.s3Config.endpoint }),
    });

    Logger.api('File service initialized with S3 configuration');
  }

  /**
   * Upload file to S3 and save record to database
   */
  static async uploadFile(
    fileData: FileUploadData,
    uploadedBy: string,
    organizationId: string,
    itemId?: string,
    commentId?: string
  ): Promise<UploadedFile> {
    try {
      // Validate file
      this.validateFile(fileData);

      // Generate unique file key
      const fileExtension = path.extname(fileData.originalName);
      const fileKey = `${organizationId}/${uuidv4()}${fileExtension}`;

      // Upload to S3
      const uploadCommand = new PutObjectCommand({
        Bucket: this.s3Config.bucketName,
        Key: fileKey,
        Body: fileData.buffer,
        ContentType: fileData.mimeType,
        Metadata: {
          originalName: fileData.originalName,
          uploadedBy,
        },
      });

      await this.s3Client.send(uploadCommand);

      // Generate thumbnail for images
      let thumbnailKey: string | undefined;
      if (this.isImage(fileData.mimeType)) {
        thumbnailKey = await this.generateThumbnail(fileData.buffer, fileKey);
      }

      // Save file record to database
      const fileRecord = await prisma.file.create({
        data: {
          originalName: fileData.originalName,
          fileKey,
          fileSize: fileData.fileSize,
          mimeType: fileData.mimeType,
          thumbnailKey,
          uploadedBy,
          organizationId,
          itemId,
          commentId,
        },
      });

      const result: UploadedFile = {
        id: fileRecord.id,
        originalName: fileRecord.originalName,
        fileKey: fileRecord.fileKey,
        fileSize: fileRecord.fileSize,
        mimeType: fileRecord.mimeType,
        url: await this.getSignedUrl(fileRecord.fileKey),
        thumbnailUrl: thumbnailKey ? await this.getSignedUrl(thumbnailKey) : undefined,
      };

      Logger.business(`File uploaded: ${fileData.originalName}`, {
        fileId: fileRecord.id,
        fileSize: fileData.fileSize,
        uploadedBy,
      });

      return result;
    } catch (error) {
      Logger.error('File upload failed', error as Error);
      throw error;
    }
  }

  /**
   * Get file by ID with signed URL
   */
  static async getFile(
    fileId: string,
    userId: string
  ): Promise<UploadedFile | null> {
    try {
      const file = await prisma.file.findFirst({
        where: {
          id: fileId,
          deletedAt: null,
          OR: [
            { uploadedBy: userId },
            {
              item: {
                board: {
                  OR: [
                    { isPrivate: false },
                    {
                      members: {
                        some: { userId },
                      },
                    },
                    {
                      workspace: {
                        members: {
                          some: { userId },
                        },
                      },
                    },
                  ],
                },
              },
            },
          ],
        },
      });

      if (!file) {
        return null;
      }

      return {
        id: file.id,
        originalName: file.originalName,
        fileKey: file.fileKey,
        fileSize: file.fileSize,
        mimeType: file.mimeType,
        url: await this.getSignedUrl(file.fileKey),
        thumbnailUrl: file.thumbnailKey ? await this.getSignedUrl(file.thumbnailKey) : undefined,
      };
    } catch (error) {
      Logger.error('Get file failed', error as Error);
      throw error;
    }
  }

  /**
   * Get files for an item
   */
  static async getItemFiles(
    itemId: string,
    userId: string
  ): Promise<UploadedFile[]> {
    try {
      const files = await prisma.file.findMany({
        where: {
          itemId,
          deletedAt: null,
          item: {
            board: {
              OR: [
                { isPrivate: false },
                {
                  members: {
                    some: { userId },
                  },
                },
                {
                  workspace: {
                    members: {
                      some: { userId },
                    },
                  },
                },
              ],
            },
          },
        },
        orderBy: { createdAt: 'desc' },
      });

      const results: UploadedFile[] = [];

      for (const file of files) {
        results.push({
          id: file.id,
          originalName: file.originalName,
          fileKey: file.fileKey,
          fileSize: file.fileSize,
          mimeType: file.mimeType,
          url: await this.getSignedUrl(file.fileKey),
          thumbnailUrl: file.thumbnailKey ? await this.getSignedUrl(file.thumbnailKey) : undefined,
        });
      }

      return results;
    } catch (error) {
      Logger.error('Get item files failed', error as Error);
      throw error;
    }
  }

  /**
   * Delete file
   */
  static async deleteFile(
    fileId: string,
    userId: string
  ): Promise<void> {
    try {
      const file = await prisma.file.findFirst({
        where: {
          id: fileId,
          deletedAt: null,
          uploadedBy: userId, // Only allow uploader to delete
        },
      });

      if (!file) {
        throw new Error('File not found or access denied');
      }

      // Soft delete in database
      await prisma.file.update({
        where: { id: fileId },
        data: { deletedAt: new Date() },
      });

      // Delete from S3 (async, don't wait)
      this.deleteFromS3(file.fileKey, file.thumbnailKey).catch(error => {
        Logger.error('Failed to delete file from S3', error);
      });

      Logger.business(`File deleted: ${file.originalName}`, {
        fileId,
        userId,
      });
    } catch (error) {
      Logger.error('Delete file failed', error as Error);
      throw error;
    }
  }

  /**
   * Get signed URL for file access
   */
  static async getSignedUrl(
    fileKey: string,
    expiresIn = 3600 // 1 hour default
  ): Promise<string> {
    try {
      const command = new GetObjectCommand({
        Bucket: this.s3Config.bucketName,
        Key: fileKey,
      });

      return await getSignedUrl(this.s3Client, command, { expiresIn });
    } catch (error) {
      Logger.error('Get signed URL failed', error as Error);
      throw error;
    }
  }

  /**
   * Get presigned URL for direct upload
   */
  static async getPresignedUploadUrl(
    fileName: string,
    fileSize: number,
    mimeType: string,
    organizationId: string,
    userId: string
  ): Promise<{
    uploadUrl: string;
    fileKey: string;
    expiresIn: number;
  }> {
    try {
      // Validate file
      this.validateFileParams(fileName, fileSize, mimeType);

      // Generate unique file key
      const fileExtension = path.extname(fileName);
      const fileKey = `${organizationId}/${uuidv4()}${fileExtension}`;

      const command = new PutObjectCommand({
        Bucket: this.s3Config.bucketName,
        Key: fileKey,
        ContentType: mimeType,
        Metadata: {
          originalName: fileName,
          uploadedBy: userId,
        },
      });

      const expiresIn = 3600; // 1 hour
      const uploadUrl = await getSignedUrl(this.s3Client, command, { expiresIn });

      return {
        uploadUrl,
        fileKey,
        expiresIn,
      };
    } catch (error) {
      Logger.error('Get presigned upload URL failed', error as Error);
      throw error;
    }
  }

  /**
   * Confirm file upload and create database record
   */
  static async confirmUpload(
    fileKey: string,
    originalName: string,
    fileSize: number,
    mimeType: string,
    uploadedBy: string,
    organizationId: string,
    itemId?: string,
    commentId?: string
  ): Promise<UploadedFile> {
    try {
      // Generate thumbnail for images
      let thumbnailKey: string | undefined;
      if (this.isImage(mimeType)) {
        // Download the file from S3 to generate thumbnail
        const getCommand = new GetObjectCommand({
          Bucket: this.s3Config.bucketName,
          Key: fileKey,
        });

        const response = await this.s3Client.send(getCommand);
        if (response.Body) {
          const buffer = Buffer.from(await response.Body.transformToByteArray());
          thumbnailKey = await this.generateThumbnail(buffer, fileKey);
        }
      }

      // Save file record to database
      const fileRecord = await prisma.file.create({
        data: {
          originalName,
          fileKey,
          fileSize,
          mimeType,
          thumbnailKey,
          uploadedBy,
          organizationId,
          itemId,
          commentId,
        },
      });

      const result: UploadedFile = {
        id: fileRecord.id,
        originalName: fileRecord.originalName,
        fileKey: fileRecord.fileKey,
        fileSize: fileRecord.fileSize,
        mimeType: fileRecord.mimeType,
        url: await this.getSignedUrl(fileRecord.fileKey),
        thumbnailUrl: thumbnailKey ? await this.getSignedUrl(thumbnailKey) : undefined,
      };

      Logger.business(`File upload confirmed: ${originalName}`, {
        fileId: fileRecord.id,
        fileSize,
        uploadedBy,
      });

      return result;
    } catch (error) {
      Logger.error('Confirm upload failed', error as Error);
      throw error;
    }
  }

  // ============================================================================
  // PRIVATE METHODS
  // ============================================================================

  /**
   * Validate file data
   */
  private static validateFile(fileData: FileUploadData): void {
    const maxFileSize = 100 * 1024 * 1024; // 100MB
    const allowedMimeTypes = [
      'image/jpeg',
      'image/png',
      'image/gif',
      'image/webp',
      'application/pdf',
      'text/plain',
      'text/csv',
      'application/vnd.ms-excel',
      'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
      'application/msword',
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
      'application/zip',
      'application/x-zip-compressed',
    ];

    if (fileData.fileSize > maxFileSize) {
      throw new Error('File size exceeds maximum allowed size (100MB)');
    }

    if (!allowedMimeTypes.includes(fileData.mimeType)) {
      throw new Error('File type not allowed');
    }

    if (!fileData.originalName || fileData.originalName.length > 255) {
      throw new Error('Invalid file name');
    }
  }

  /**
   * Validate file parameters
   */
  private static validateFileParams(
    fileName: string,
    fileSize: number,
    mimeType: string
  ): void {
    this.validateFile({
      originalName: fileName,
      fileSize,
      mimeType,
      buffer: Buffer.alloc(0), // Not used for validation
    });
  }

  /**
   * Check if file is an image
   */
  private static isImage(mimeType: string): boolean {
    return mimeType.startsWith('image/');
  }

  /**
   * Generate thumbnail for images
   */
  private static async generateThumbnail(
    buffer: Buffer,
    originalFileKey: string
  ): Promise<string> {
    try {
      const thumbnailBuffer = await sharp(buffer)
        .resize(300, 300, {
          fit: 'inside',
          withoutEnlargement: true,
        })
        .jpeg({ quality: 80 })
        .toBuffer();

      const thumbnailKey = originalFileKey.replace(/\.[^.]+$/, '_thumb.jpg');

      const uploadCommand = new PutObjectCommand({
        Bucket: this.s3Config.bucketName,
        Key: thumbnailKey,
        Body: thumbnailBuffer,
        ContentType: 'image/jpeg',
      });

      await this.s3Client.send(uploadCommand);

      return thumbnailKey;
    } catch (error) {
      Logger.error('Thumbnail generation failed', error as Error);
      throw error;
    }
  }

  /**
   * Delete file from S3
   */
  private static async deleteFromS3(
    fileKey: string,
    thumbnailKey?: string
  ): Promise<void> {
    try {
      // Delete main file
      await this.s3Client.send(new DeleteObjectCommand({
        Bucket: this.s3Config.bucketName,
        Key: fileKey,
      }));

      // Delete thumbnail if exists
      if (thumbnailKey) {
        await this.s3Client.send(new DeleteObjectCommand({
          Bucket: this.s3Config.bucketName,
          Key: thumbnailKey,
        }));
      }
    } catch (error) {
      Logger.error('Delete from S3 failed', error as Error);
      // Don't throw error for S3 deletion failures
    }
  }

  /**
   * Clean up orphaned files (files not associated with any item/comment)
   */
  static async cleanupOrphanedFiles(): Promise<void> {
    try {
      // Find files uploaded more than 24 hours ago with no associations
      const orphanedFiles = await prisma.file.findMany({
        where: {
          itemId: null,
          commentId: null,
          createdAt: {
            lt: new Date(Date.now() - 24 * 60 * 60 * 1000), // 24 hours ago
          },
          deletedAt: null,
        },
      });

      for (const file of orphanedFiles) {
        // Soft delete orphaned file
        await prisma.file.update({
          where: { id: file.id },
          data: { deletedAt: new Date() },
        });

        // Delete from S3
        this.deleteFromS3(file.fileKey, file.thumbnailKey).catch(error => {
          Logger.error('Failed to delete orphaned file from S3', error);
        });
      }

      Logger.business(`Cleaned up ${orphanedFiles.length} orphaned files`);
    } catch (error) {
      Logger.error('Cleanup orphaned files failed', error as Error);
    }
  }
}

// Initialize the service when the module is loaded
FileService.initialize();