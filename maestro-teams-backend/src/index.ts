/**
 * Maestro Teams Backend
 * Express server for Hybrid Team Foundation APIs
 * Part of MD-598: Epic 7
 */

import express from 'express';
import cors from 'cors';
import dotenv from 'dotenv';
import { teamRoutes } from './routes/teams';
import { blueprintRoutes } from './routes/blueprints';

dotenv.config();

const app = express();
const PORT = process.env.PORT || 3100;

// Middleware
app.use(cors());
app.use(express.json());

// Health check
app.get('/health', (req, res) => {
  res.json({ status: 'ok', service: 'maestro-teams-backend', timestamp: new Date().toISOString() });
});

// Routes
app.use('/api/teams', teamRoutes);
app.use('/api/teams/blueprints', blueprintRoutes);

// Error handler
app.use((err: any, req: express.Request, res: express.Response, next: express.NextFunction) => {
  console.error('Error:', err);
  res.status(err.status || 500).json({
    error: err.message || 'Internal server error',
    code: err.code || 'INTERNAL_ERROR'
  });
});

app.listen(PORT, () => {
  console.log(`🚀 Maestro Teams Backend running on port ${PORT}`);
});

export default app;
