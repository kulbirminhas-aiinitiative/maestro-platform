import { Router } from 'express';
import authRoutes from './auth.routes';
import organizationRoutes from './organization.routes';
import workspaceRoutes from './workspace.routes';
import boardRoutes from './board.routes';
import itemRoutes from './item.routes';
import fileRoutes from './file.routes';
import commentRoutes from './comment.routes';
import aiRoutes from './ai.routes';
import automationRoutes from './automation.routes';
import timeRoutes from './time.routes';
import analyticsRoutes from './analytics.routes';
import webhookRoutes from './webhook.routes';
import collaborationRoutes from './collaboration.routes';

const router = Router();

// Health check endpoint
router.get('/health', (req, res) => {
  res.json({
    status: 'healthy',
    timestamp: new Date().toISOString(),
    version: '1.0.0',
    environment: process.env.NODE_ENV || 'development',
  });
});

// API routes
router.use('/auth', authRoutes);
router.use('/organizations', organizationRoutes);
router.use('/workspaces', workspaceRoutes);
router.use('/boards', boardRoutes);
router.use('/items', itemRoutes);
router.use('/files', fileRoutes);
router.use('/comments', commentRoutes);
router.use('/ai', aiRoutes);
router.use('/automation', automationRoutes);
router.use('/time', timeRoutes);
router.use('/analytics', analyticsRoutes);
router.use('/webhooks', webhookRoutes);
router.use('/collaboration', collaborationRoutes);

export default router;