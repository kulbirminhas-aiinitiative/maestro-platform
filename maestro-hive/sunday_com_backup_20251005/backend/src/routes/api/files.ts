import { Router } from 'express';
import { param, body, query } from 'express-validator';
import multer from 'multer';
import { FileService } from '@/services/file.service';
import { authenticate } from '@/middleware/auth';
import { rateLimit } from '@/middleware/rate-limit';
import { Logger } from '@/config/logger';
import { handleValidationErrors } from '@/middleware/validation';

const router = Router();

// Configure multer for file uploads
const upload = multer({
  storage: multer.memoryStorage(),
  limits: {
    fileSize: 50 * 1024 * 1024, // 50MB limit
    files: 10, // Maximum 10 files at once
  },
  fileFilter: (req, file, cb) => {
    // Basic file validation - more comprehensive validation in service
    const allowedTypes = [
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

    if (allowedTypes.includes(file.mimetype)) {
      cb(null, true);
    } else {
      cb(new Error(`File type ${file.mimetype} is not allowed`));
    }
  },
});

// Apply authentication to all file routes
router.use(authenticate);

// ============================================================================
// FILE UPLOAD
// ============================================================================

/**
 * @route   POST /api/files/upload
 * @desc    Upload files
 * @access  Private
 */
router.post(
  '/upload',
  rateLimit({ max: 20, windowMs: 60000 }), // 20 uploads per minute
  upload.array('files', 10), // Allow up to 10 files
  [
    body('organizationId')
      .isUUID()
      .withMessage('Valid organization ID is required'),
    body('entityType')
      .optional()
      .isIn(['item', 'comment', 'board'])
      .withMessage('Invalid entity type'),
    body('entityId')
      .optional()
      .isUUID()
      .withMessage('Entity ID must be a valid UUID'),
    handleValidationErrors,
  ],
  async (req, res) => {
    try {
      const userId = req.user!.id;
      const { organizationId, entityType, entityId } = req.body;
      const files = req.files as Express.Multer.File[];

      if (!files || files.length === 0) {
        return res.status(400).json({
          success: false,
          message: 'No files provided',
        });
      }

      const uploadPromises = files.map(async (file) => {
        const fileData = {
          originalName: file.originalname,
          buffer: file.buffer,
          fileSize: file.size,
          mimeType: file.mimetype,
        };

        return FileService.uploadFile(
          organizationId,
          userId,
          fileData,
          entityType,
          entityId
        );
      });

      const uploadedFiles = await Promise.all(uploadPromises);

      res.status(201).json({
        success: true,
        data: uploadedFiles,
        message: `${uploadedFiles.length} file(s) uploaded successfully`,
      });
    } catch (error) {
      Logger.error('File upload failed', error as Error);

      // Handle multer errors
      if (error instanceof multer.MulterError) {
        if (error.code === 'LIMIT_FILE_SIZE') {
          return res.status(400).json({
            success: false,
            message: 'File size exceeds the 50MB limit',
          });
        }
        if (error.code === 'LIMIT_FILE_COUNT') {
          return res.status(400).json({
            success: false,
            message: 'Too many files. Maximum 10 files allowed',
          });
        }
      }

      res.status(400).json({
        success: false,
        message: (error as Error).message,
      });
    }
  }
);

/**
 * @route   POST /api/files/upload/single
 * @desc    Upload single file
 * @access  Private
 */
router.post(
  '/upload/single',
  rateLimit({ max: 50, windowMs: 60000 }), // 50 uploads per minute
  upload.single('file'),
  [
    body('organizationId')
      .isUUID()
      .withMessage('Valid organization ID is required'),
    body('entityType')
      .optional()
      .isIn(['item', 'comment', 'board'])
      .withMessage('Invalid entity type'),
    body('entityId')
      .optional()
      .isUUID()
      .withMessage('Entity ID must be a valid UUID'),
    handleValidationErrors,
  ],
  async (req, res) => {
    try {
      const userId = req.user!.id;
      const { organizationId, entityType, entityId } = req.body;
      const file = req.file;

      if (!file) {
        return res.status(400).json({
          success: false,
          message: 'No file provided',
        });
      }

      const fileData = {
        originalName: file.originalname,
        buffer: file.buffer,
        fileSize: file.size,
        mimeType: file.mimetype,
      };

      const uploadedFile = await FileService.uploadFile(
        organizationId,
        userId,
        fileData,
        entityType,
        entityId
      );

      res.status(201).json({
        success: true,
        data: uploadedFile,
        message: 'File uploaded successfully',
      });
    } catch (error) {
      Logger.error('Single file upload failed', error as Error);

      // Handle multer errors
      if (error instanceof multer.MulterError) {
        if (error.code === 'LIMIT_FILE_SIZE') {
          return res.status(400).json({
            success: false,
            message: 'File size exceeds the 50MB limit',
          });
        }
      }

      res.status(400).json({
        success: false,
        message: (error as Error).message,
      });
    }
  }
);

// ============================================================================
// FILE MANAGEMENT
// ============================================================================

/**
 * @route   GET /api/files/:fileId
 * @desc    Get file by ID
 * @access  Private
 */
router.get(
  '/:fileId',
  [
    param('fileId')
      .isUUID()
      .withMessage('Valid file ID is required'),
    handleValidationErrors,
  ],
  async (req, res) => {
    try {
      const { fileId } = req.params;
      const userId = req.user!.id;

      const file = await FileService.getFile(fileId, userId);

      res.json({
        success: true,
        data: file,
      });
    } catch (error) {
      Logger.error('Get file failed', error as Error);
      const statusCode = (error as Error).message.includes('not found') ||
                        (error as Error).message.includes('Access denied') ? 404 : 500;
      res.status(statusCode).json({
        success: false,
        message: (error as Error).message,
      });
    }
  }
);

/**
 * @route   DELETE /api/files/:fileId
 * @desc    Delete file
 * @access  Private
 */
router.delete(
  '/:fileId',
  rateLimit({ max: 50, windowMs: 60000 }), // 50 deletions per minute
  [
    param('fileId')
      .isUUID()
      .withMessage('Valid file ID is required'),
    handleValidationErrors,
  ],
  async (req, res) => {
    try {
      const { fileId } = req.params;
      const userId = req.user!.id;

      await FileService.deleteFile(fileId, userId);

      res.json({
        success: true,
        message: 'File deleted successfully',
      });
    } catch (error) {
      Logger.error('Delete file failed', error as Error);
      const statusCode = (error as Error).message.includes('Permission denied') ? 403 : 400;
      res.status(statusCode).json({
        success: false,
        message: (error as Error).message,
      });
    }
  }
);

// ============================================================================
// FILE LISTING AND SEARCH
// ============================================================================

/**
 * @route   GET /api/files/organization/:organizationId
 * @desc    Get organization files
 * @access  Private
 */
router.get(
  '/organization/:organizationId',
  [
    param('organizationId')
      .isUUID()
      .withMessage('Valid organization ID is required'),
    query('page')
      .optional()
      .isInt({ min: 1 })
      .withMessage('Page must be a positive integer'),
    query('limit')
      .optional()
      .isInt({ min: 1, max: 100 })
      .withMessage('Limit must be between 1 and 100'),
    query('type')
      .optional()
      .isIn(['image', 'document', 'archive', 'other'])
      .withMessage('Invalid file type filter'),
    query('search')
      .optional()
      .trim()
      .isLength({ max: 100 })
      .withMessage('Search query must not exceed 100 characters'),
    query('uploadedBy')
      .optional()
      .isUUID()
      .withMessage('Uploaded by must be a valid UUID'),
    handleValidationErrors,
  ],
  async (req, res) => {
    try {
      const { organizationId } = req.params;
      const userId = req.user!.id;

      const page = parseInt(req.query.page as string) || 1;
      const limit = parseInt(req.query.limit as string) || 20;
      const { type, search, uploadedBy } = req.query;

      const filter = {
        type: type as 'image' | 'document' | 'archive' | 'other',
        search: search as string,
        uploadedBy: uploadedBy as string,
      };

      const result = await FileService.getOrganizationFiles(
        organizationId,
        userId,
        page,
        limit,
        filter
      );

      res.json({
        success: true,
        data: result.files,
        meta: {
          page: result.page,
          totalPages: result.totalPages,
          total: result.total,
          hasNext: result.page < result.totalPages,
          hasPrev: result.page > 1,
        },
      });
    } catch (error) {
      Logger.error('Get organization files failed', error as Error);
      res.status(400).json({
        success: false,
        message: (error as Error).message,
      });
    }
  }
);

/**
 * @route   GET /api/files/statistics/:organizationId
 * @desc    Get file statistics for organization
 * @access  Private
 */
router.get(
  '/statistics/:organizationId',
  [
    param('organizationId')
      .isUUID()
      .withMessage('Valid organization ID is required'),
    handleValidationErrors,
  ],
  async (req, res) => {
    try {
      const { organizationId } = req.params;
      const userId = req.user!.id;

      const statistics = await FileService.getFileStatistics(organizationId, userId);

      res.json({
        success: true,
        data: statistics,
      });
    } catch (error) {
      Logger.error('Get file statistics failed', error as Error);
      res.status(400).json({
        success: false,
        message: (error as Error).message,
      });
    }
  }
);

// ============================================================================
// FILE ATTACHMENTS
// ============================================================================

/**
 * @route   POST /api/files/:fileId/attach
 * @desc    Attach file to entity
 * @access  Private
 */
router.post(
  '/:fileId/attach',
  rateLimit({ max: 100, windowMs: 60000 }), // 100 requests per minute
  [
    param('fileId')
      .isUUID()
      .withMessage('Valid file ID is required'),
    body('entityType')
      .isIn(['item', 'comment', 'board'])
      .withMessage('Invalid entity type'),
    body('entityId')
      .isUUID()
      .withMessage('Valid entity ID is required'),
    handleValidationErrors,
  ],
  async (req, res) => {
    try {
      const { fileId } = req.params;
      const userId = req.user!.id;
      const { entityType, entityId } = req.body;

      await FileService.attachFile(fileId, entityType, entityId, userId);

      res.status(201).json({
        success: true,
        message: 'File attached successfully',
      });
    } catch (error) {
      Logger.error('Attach file failed', error as Error);
      res.status(400).json({
        success: false,
        message: (error as Error).message,
      });
    }
  }
);

/**
 * @route   DELETE /api/files/:fileId/detach
 * @desc    Detach file from entity
 * @access  Private
 */
router.delete(
  '/:fileId/detach',
  rateLimit({ max: 100, windowMs: 60000 }), // 100 requests per minute
  [
    param('fileId')
      .isUUID()
      .withMessage('Valid file ID is required'),
    body('entityType')
      .isIn(['item', 'comment', 'board'])
      .withMessage('Invalid entity type'),
    body('entityId')
      .isUUID()
      .withMessage('Valid entity ID is required'),
    handleValidationErrors,
  ],
  async (req, res) => {
    try {
      const { fileId } = req.params;
      const userId = req.user!.id;
      const { entityType, entityId } = req.body;

      await FileService.detachFile(fileId, entityType, entityId, userId);

      res.json({
        success: true,
        message: 'File detached successfully',
      });
    } catch (error) {
      Logger.error('Detach file failed', error as Error);
      res.status(400).json({
        success: false,
        message: (error as Error).message,
      });
    }
  }
);

/**
 * @route   GET /api/files/entity/:entityType/:entityId
 * @desc    Get files attached to entity
 * @access  Private
 */
router.get(
  '/entity/:entityType/:entityId',
  [
    param('entityType')
      .isIn(['item', 'comment', 'board'])
      .withMessage('Invalid entity type'),
    param('entityId')
      .isUUID()
      .withMessage('Valid entity ID is required'),
    handleValidationErrors,
  ],
  async (req, res) => {
    try {
      const { entityType, entityId } = req.params;
      const userId = req.user!.id;

      const files = await FileService.getEntityFiles(
        entityType as 'item' | 'comment' | 'board',
        entityId,
        userId
      );

      res.json({
        success: true,
        data: files,
      });
    } catch (error) {
      Logger.error('Get entity files failed', error as Error);
      res.status(400).json({
        success: false,
        message: (error as Error).message,
      });
    }
  }
);

// ============================================================================
// ERROR HANDLING
// ============================================================================

// Handle multer errors
router.use((error: any, req: any, res: any, next: any) => {
  if (error instanceof multer.MulterError) {
    if (error.code === 'LIMIT_FILE_SIZE') {
      return res.status(400).json({
        success: false,
        message: 'File size exceeds the 50MB limit',
      });
    }
    if (error.code === 'LIMIT_FILE_COUNT') {
      return res.status(400).json({
        success: false,
        message: 'Too many files. Maximum 10 files allowed',
      });
    }
    if (error.code === 'LIMIT_UNEXPECTED_FILE') {
      return res.status(400).json({
        success: false,
        message: 'Unexpected file field',
      });
    }
  }

  if (error.message && error.message.includes('File type')) {
    return res.status(400).json({
      success: false,
      message: error.message,
    });
  }

  next(error);
});

export default router;