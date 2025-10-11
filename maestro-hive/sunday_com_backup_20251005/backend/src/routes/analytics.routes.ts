import { Router } from 'express';
import { param, query, body } from 'express-validator';
import { AuthenticatedRequest } from '@/types';
import { AnalyticsService } from '@/services/analytics.service';
import { authenticateToken } from '@/middleware/auth';
import { validationMiddleware } from '@/middleware/express-validation';
import { Logger } from '@/config/logger';

const router = Router();

// Apply authentication to all routes
router.use(authenticateToken);

// ============================================================================
// ANALYTICS ROUTES
// ============================================================================

/**
 * GET /analytics/boards/:boardId
 * Get board analytics and metrics
 */
router.get(
  '/boards/:boardId',
  [
    param('boardId').isUUID().withMessage('Valid board ID required'),
    query('period').optional().isIn(['day', 'week', 'month', 'year']).withMessage('Period must be day, week, month, or year'),
    validationMiddleware,
  ],
  async (req: AuthenticatedRequest, res) => {
    try {
      const { boardId } = req.params;
      const { period = 'month' } = req.query;
      const userId = req.user!.id;

      const analytics = await AnalyticsService.getBoardAnalytics(
        boardId,
        userId,
        period as 'day' | 'week' | 'month' | 'year'
      );

      res.json({
        data: analytics,
      });
    } catch (error) {
      Logger.error('Get board analytics failed', error as Error);

      const errorMessage = (error as Error).message;
      if (errorMessage.includes('Access denied')) {
        res.status(403).json({
          error: {
            type: 'forbidden',
            message: errorMessage,
          },
        });
      } else {
        res.status(500).json({
          error: {
            type: 'internal_error',
            message: 'Failed to get board analytics',
          },
        });
      }
    }
  }
);

/**
 * GET /analytics/users/:userId
 * Get user activity report
 */
router.get(
  '/users/:userId',
  [
    param('userId').isUUID().withMessage('Valid user ID required'),
    query('period').optional().isIn(['day', 'week', 'month', 'year']).withMessage('Period must be day, week, month, or year'),
    validationMiddleware,
  ],
  async (req: AuthenticatedRequest, res) => {
    try {
      const { userId } = req.params;
      const { period = 'month' } = req.query;
      const requestingUserId = req.user!.id;

      const report = await AnalyticsService.getUserActivityReport(
        userId,
        requestingUserId,
        period as 'day' | 'week' | 'month' | 'year'
      );

      res.json({
        data: report,
      });
    } catch (error) {
      Logger.error('Get user activity report failed', error as Error);

      const errorMessage = (error as Error).message;
      if (errorMessage.includes('Access denied')) {
        res.status(403).json({
          error: {
            type: 'forbidden',
            message: errorMessage,
          },
        });
      } else {
        res.status(500).json({
          error: {
            type: 'internal_error',
            message: 'Failed to get user activity report',
          },
        });
      }
    }
  }
);

/**
 * GET /analytics/teams/workspaces/:workspaceId
 * Get team productivity report
 */
router.get(
  '/teams/workspaces/:workspaceId',
  [
    param('workspaceId').isUUID().withMessage('Valid workspace ID required'),
    query('period').optional().isIn(['day', 'week', 'month', 'year']).withMessage('Period must be day, week, month, or year'),
    validationMiddleware,
  ],
  async (req: AuthenticatedRequest, res) => {
    try {
      const { workspaceId } = req.params;
      const { period = 'month' } = req.query;
      const userId = req.user!.id;

      const report = await AnalyticsService.getTeamProductivityReport(
        workspaceId,
        userId,
        period as 'day' | 'week' | 'month' | 'year'
      );

      res.json({
        data: report,
      });
    } catch (error) {
      Logger.error('Get team productivity report failed', error as Error);

      const errorMessage = (error as Error).message;
      if (errorMessage.includes('Access denied')) {
        res.status(403).json({
          error: {
            type: 'forbidden',
            message: errorMessage,
          },
        });
      } else {
        res.status(500).json({
          error: {
            type: 'internal_error',
            message: 'Failed to get team productivity report',
          },
        });
      }
    }
  }
);

/**
 * GET /analytics/organizations/:organizationId
 * Get organization-wide analytics
 */
router.get(
  '/organizations/:organizationId',
  [
    param('organizationId').isUUID().withMessage('Valid organization ID required'),
    query('period').optional().isIn(['day', 'week', 'month', 'year']).withMessage('Period must be day, week, month, or year'),
    validationMiddleware,
  ],
  async (req: AuthenticatedRequest, res) => {
    try {
      const { organizationId } = req.params;
      const { period = 'month' } = req.query;
      const userId = req.user!.id;

      const analytics = await AnalyticsService.getOrganizationAnalytics(
        organizationId,
        userId,
        period as 'day' | 'week' | 'month' | 'year'
      );

      res.json({
        data: analytics,
      });
    } catch (error) {
      Logger.error('Get organization analytics failed', error as Error);

      const errorMessage = (error as Error).message;
      if (errorMessage.includes('Access denied')) {
        res.status(403).json({
          error: {
            type: 'forbidden',
            message: errorMessage,
          },
        });
      } else {
        res.status(500).json({
          error: {
            type: 'internal_error',
            message: 'Failed to get organization analytics',
          },
        });
      }
    }
  }
);

/**
 * POST /analytics/custom
 * Generate custom analytics report
 */
router.post(
  '/custom',
  [
    body('organizationId').optional().isUUID().withMessage('Valid organization ID required'),
    body('workspaceId').optional().isUUID().withMessage('Valid workspace ID required'),
    body('boardId').optional().isUUID().withMessage('Valid board ID required'),
    body('userId').optional().isUUID().withMessage('Valid user ID required'),
    body('startDate').optional().isISO8601().withMessage('Valid start date required'),
    body('endDate').optional().isISO8601().withMessage('Valid end date required'),
    body('metrics').optional().isArray().withMessage('Metrics must be an array'),
    body('groupBy').optional().isString().withMessage('GroupBy must be a string'),
    body('filters').optional().isObject().withMessage('Filters must be an object'),
    validationMiddleware,
  ],
  async (req: AuthenticatedRequest, res) => {
    try {
      const userId = req.user!.id;
      const filter = {
        ...req.body,
        startDate: req.body.startDate ? new Date(req.body.startDate) : undefined,
        endDate: req.body.endDate ? new Date(req.body.endDate) : undefined,
      };

      const report = await AnalyticsService.generateCustomReport(filter, userId);

      res.json({
        data: report,
      });
    } catch (error) {
      Logger.error('Generate custom report failed', error as Error);

      const errorMessage = (error as Error).message;
      if (errorMessage.includes('Access denied')) {
        res.status(403).json({
          error: {
            type: 'forbidden',
            message: errorMessage,
          },
        });
      } else {
        res.status(500).json({
          error: {
            type: 'internal_error',
            message: 'Failed to generate custom report',
          },
        });
      }
    }
  }
);

/**
 * GET /analytics/dashboards/overview
 * Get dashboard overview data for current user
 */
router.get(
  '/dashboards/overview',
  [
    query('period').optional().isIn(['day', 'week', 'month', 'year']).withMessage('Period must be day, week, month, or year'),
    validationMiddleware,
  ],
  async (req: AuthenticatedRequest, res) => {
    try {
      const userId = req.user!.id;
      const { period = 'week' } = req.query;

      // Get user's personal analytics overview
      const userReport = await AnalyticsService.getUserActivityReport(
        userId,
        userId,
        period as 'day' | 'week' | 'month' | 'year'
      );

      // Get organization analytics if user is admin
      let organizationAnalytics = null;
      try {
        // Try to get organization analytics - will fail if user doesn't have access
        const userOrg = await req.prisma?.user.findUnique({
          where: { id: userId },
          select: { organizationId: true },
        });

        if (userOrg?.organizationId) {
          organizationAnalytics = await AnalyticsService.getOrganizationAnalytics(
            userOrg.organizationId,
            userId,
            period as 'day' | 'week' | 'month' | 'year'
          );
        }
      } catch (error) {
        // User doesn't have org admin access, which is fine
      }

      res.json({
        data: {
          userReport,
          organizationAnalytics,
          period,
          generatedAt: new Date(),
        },
      });
    } catch (error) {
      Logger.error('Get dashboard overview failed', error as Error);
      res.status(500).json({
        error: {
          type: 'internal_error',
          message: 'Failed to get dashboard overview',
        },
      });
    }
  }
);

/**
 * GET /analytics/export
 * Export analytics data in various formats
 */
router.get(
  '/export',
  [
    query('type').isIn(['csv', 'json', 'xlsx']).withMessage('Export type must be csv, json, or xlsx'),
    query('scope').isIn(['board', 'workspace', 'organization', 'user']).withMessage('Scope must be board, workspace, organization, or user'),
    query('scopeId').isUUID().withMessage('Valid scope ID required'),
    query('period').optional().isIn(['day', 'week', 'month', 'year']).withMessage('Period must be day, week, month, or year'),
    query('metrics').optional().isString().withMessage('Metrics must be a comma-separated string'),
    validationMiddleware,
  ],
  async (req: AuthenticatedRequest, res) => {
    try {
      const userId = req.user!.id;
      const { type, scope, scopeId, period = 'month', metrics } = req.query;

      // Get analytics data based on scope
      let data;
      switch (scope) {
        case 'board':
          data = await AnalyticsService.getBoardAnalytics(
            scopeId as string,
            userId,
            period as 'day' | 'week' | 'month' | 'year'
          );
          break;
        case 'workspace':
          data = await AnalyticsService.getTeamProductivityReport(
            scopeId as string,
            userId,
            period as 'day' | 'week' | 'month' | 'year'
          );
          break;
        case 'organization':
          data = await AnalyticsService.getOrganizationAnalytics(
            scopeId as string,
            userId,
            period as 'day' | 'week' | 'month' | 'year'
          );
          break;
        case 'user':
          data = await AnalyticsService.getUserActivityReport(
            scopeId as string,
            userId,
            period as 'day' | 'week' | 'month' | 'year'
          );
          break;
        default:
          throw new Error('Invalid scope');
      }

      // Set appropriate headers for file download
      const filename = `${scope}-analytics-${scopeId}-${period}.${type}`;
      res.setHeader('Content-Disposition', `attachment; filename="${filename}"`);

      if (type === 'json') {
        res.setHeader('Content-Type', 'application/json');
        res.json(data);
      } else if (type === 'csv') {
        res.setHeader('Content-Type', 'text/csv');
        // Convert data to CSV format (simplified implementation)
        const csv = this.convertToCSV(data);
        res.send(csv);
      } else if (type === 'xlsx') {
        res.setHeader('Content-Type', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet');
        // In a real implementation, you'd use a library like xlsx to generate Excel files
        res.json({ message: 'XLSX export not implemented yet', data });
      }
    } catch (error) {
      Logger.error('Export analytics failed', error as Error);

      const errorMessage = (error as Error).message;
      if (errorMessage.includes('Access denied')) {
        res.status(403).json({
          error: {
            type: 'forbidden',
            message: errorMessage,
          },
        });
      } else {
        res.status(500).json({
          error: {
            type: 'internal_error',
            message: 'Failed to export analytics',
          },
        });
      }
    }
  }
);

// Helper function to convert data to CSV (simplified implementation)
function convertToCSV(data: any): string {
  if (!data || typeof data !== 'object') {
    return '';
  }

  // This is a simplified CSV conversion
  // In a real implementation, you'd want a more robust CSV generation library
  const headers = Object.keys(data);
  const values = Object.values(data).map(v =>
    typeof v === 'object' ? JSON.stringify(v) : String(v)
  );

  return [headers.join(','), values.join(',')].join('\n');
}

export default router;