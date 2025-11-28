import { Router } from 'express';
import authRoutes from './auth.routes';
import organizationRoutes from './organization.routes';
// Import other routes as they are created
// import workspaceRoutes from './workspace.routes';
// import boardRoutes from './board.routes';
// import itemRoutes from './item.routes';

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
// Add other routes as they are implemented
// router.use('/workspaces', workspaceRoutes);
// router.use('/boards', boardRoutes);
// router.use('/items', itemRoutes);

export default router;