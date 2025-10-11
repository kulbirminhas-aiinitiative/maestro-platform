import { Router } from 'express';
import { body, param, query } from 'express-validator';
import multer from 'multer';
import { AuthenticatedRequest } from '@/types';
import { FileService } from '@/services/file.service';
import { authenticateToken } from '@/middleware/auth';
import { validationMiddleware } from '@/middleware/express-validation';
import { Logger } from '@/config/logger';

const router = Router();

// Configure multer for file uploads
const upload = multer({
  storage: multer.memoryStorage(),
  limits: {
    fileSize: 100 * 1024 * 1024, // 100MB
  },
  fileFilter: (req, file, cb) => {
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

    if (allowedMimeTypes.includes(file.mimetype)) {
      cb(null, true);
    } else {
      cb(new Error('File type not allowed'));
    }
  },
});

// Apply authentication to all routes
router.use(authenticateToken);

// ============================================================================
// FILE UPLOAD ROUTES
// ============================================================================

/**
 * POST /files/upload
 * Upload file directly
 */
router.post(
  '/upload',
  upload.single('file'),
  [
    body('organizationId').isUUID().withMessage('Valid organization ID required'),
    body('itemId').optional().isUUID().withMessage('Valid item ID required'),
    body('commentId').optional().isUUID().withMessage('Valid comment ID required'),
    validationMiddleware,
  ],
  async (req: AuthenticatedRequest, res) => {
    try {
      if (!req.file) {
        return res.status(400).json({
          error: {
            type: 'validation_error',
            message: 'No file uploaded',
          },
        });
      }

      const { organizationId, itemId, commentId } = req.body;
      const userId = req.user!.id;

      const fileData = {
        originalName: req.file.originalname,
        mimeType: req.file.mimetype,
        fileSize: req.file.size,
        buffer: req.file.buffer,
      };

      const uploadedFile = await FileService.uploadFile(
        fileData,
        userId,
        organizationId,
        itemId,
        commentId
      );

      res.status(201).json({
        data: uploadedFile,
      });
    } catch (error) {
      Logger.error('File upload failed', error as Error);

      const errorMessage = (error as Error).message;
      if (errorMessage.includes('size exceeds') || errorMessage.includes('type not allowed')) {
        res.status(400).json({
          error: {
            type: 'validation_error',
            message: errorMessage,
          },
        });
      } else {
        res.status(500).json({
          error: {
            type: 'internal_error',
            message: 'Failed to upload file',
          },
        });
      }
    }
  }
);

/**
 * POST /files/presigned-url
 * Get presigned URL for direct upload to S3
 */
router.post(
  '/presigned-url',
  [
    body('fileName').isString().trim().isLength({ min: 1, max: 255 }).withMessage('File name is required and must be between 1-255 characters'),
    body('fileSize').isInt({ min: 1 }).withMessage('File size must be a positive integer'),
    body('mimeType').isString().withMessage('MIME type is required'),
    body('organizationId').isUUID().withMessage('Valid organization ID required'),
    validationMiddleware,
  ],
  async (req: AuthenticatedRequest, res) => {
    try {
      const { fileName, fileSize, mimeType, organizationId } = req.body;
      const userId = req.user!.id;

      const presignedData = await FileService.getPresignedUploadUrl(
        fileName,
        fileSize,
        mimeType,
        organizationId,
        userId
      );

      res.json({
        data: presignedData,
      });
    } catch (error) {
      Logger.error('Get presigned URL failed', error as Error);

      const errorMessage = (error as Error).message;
      if (errorMessage.includes('size exceeds') || errorMessage.includes('type not allowed')) {
        res.status(400).json({
          error: {
            type: 'validation_error',
            message: errorMessage,
          },
        });
      } else {
        res.status(500).json({
          error: {
            type: 'internal_error',
            message: 'Failed to get presigned URL',
          },
        });
      }
    }
  }
);

/**
 * POST /files/confirm-upload
 * Confirm file upload and create database record
 */
router.post(
  '/confirm-upload',
  [
    body('fileKey').isString().withMessage('File key is required'),
    body('originalName').isString().trim().isLength({ min: 1, max: 255 }).withMessage('Original name is required and must be between 1-255 characters'),
    body('fileSize').isInt({ min: 1 }).withMessage('File size must be a positive integer'),
    body('mimeType').isString().withMessage('MIME type is required'),
    body('organizationId').isUUID().withMessage('Valid organization ID required'),
    body('itemId').optional().isUUID().withMessage('Valid item ID required'),
    body('commentId').optional().isUUID().withMessage('Valid comment ID required'),
    validationMiddleware,
  ],
  async (req: AuthenticatedRequest, res) => {
    try {
      const { fileKey, originalName, fileSize, mimeType, organizationId, itemId, commentId } = req.body;
      const userId = req.user!.id;

      const uploadedFile = await FileService.confirmUpload(
        fileKey,
        originalName,
        fileSize,
        mimeType,
        userId,
        organizationId,
        itemId,
        commentId
      );

      res.status(201).json({
        data: uploadedFile,
      });
    } catch (error) {
      Logger.error('Confirm upload failed', error as Error);
      res.status(500).json({
        error: {
          type: 'internal_error',
          message: 'Failed to confirm upload',
        },
      });
    }
  }
);

// ============================================================================
// FILE ACCESS ROUTES
// ============================================================================

/**
 * GET /files/:fileId
 * Get file by ID with signed URL
 */
router.get(
  '/:fileId',
  [
    param('fileId').isUUID().withMessage('Valid file ID required'),
    validationMiddleware,
  ],
  async (req: AuthenticatedRequest, res) => {
    try {
      const { fileId } = req.params;
      const userId = req.user!.id;

      const file = await FileService.getFile(fileId, userId);

      if (!file) {
        return res.status(404).json({
          error: {
            type: 'not_found',
            message: 'File not found',
          },
        });
      }

      res.json({
        data: file,
      });
    } catch (error) {
      Logger.error('Get file failed', error as Error);
      res.status(500).json({
        error: {
          type: 'internal_error',
          message: 'Failed to get file',
        },
      });
    }
  }
);

/**
 * GET /files/item/:itemId
 * Get all files for an item
 */
router.get(
  '/item/:itemId',
  [
    param('itemId').isUUID().withMessage('Valid item ID required'),
    validationMiddleware,
  ],
  async (req: AuthenticatedRequest, res) => {
    try {
      const { itemId } = req.params;
      const userId = req.user!.id;

      const files = await FileService.getItemFiles(itemId, userId);

      res.json({
        data: files,
      });
    } catch (error) {
      Logger.error('Get item files failed', error as Error);
      res.status(500).json({
        error: {
          type: 'internal_error',
          message: 'Failed to get item files',
        },
      });
    }
  }
);

/**
 * DELETE /files/:fileId
 * Delete file
 */
router.delete(
  '/:fileId',
  [
    param('fileId').isUUID().withMessage('Valid file ID required'),
    validationMiddleware,
  ],
  async (req: AuthenticatedRequest, res) => {
    try {
      const { fileId } = req.params;
      const userId = req.user!.id;

      await FileService.deleteFile(fileId, userId);

      res.status(204).send();
    } catch (error) {
      Logger.error('Delete file failed', error as Error);

      const errorMessage = (error as Error).message;
      if (errorMessage.includes('not found') || errorMessage.includes('access denied')) {
        res.status(404).json({
          error: {
            type: 'not_found',
            message: 'File not found or access denied',
          },
        });
      } else {
        res.status(500).json({
          error: {
            type: 'internal_error',
            message: 'Failed to delete file',
          },
        });
      }
    }
  }
);

export default router;