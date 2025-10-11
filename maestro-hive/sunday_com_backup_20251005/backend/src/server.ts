import express from 'express';
import cors from 'cors';
import helmet from 'helmet';
import compression from 'compression';
import morgan from 'morgan';
import { createServer } from 'http';
import { Server as SocketIOServer } from 'socket.io';

import { config } from '@/config';
import { logger, Logger } from '@/config/logger';
import { checkDatabaseHealth, disconnectDatabase } from '@/config/database';
import { checkRedisHealth, disconnectRedis } from '@/config/redis';
import { errorHandler, notFoundHandler } from '@/middleware/error';
import routes from '@/routes';

// Create Express app
const app = express();
const server = createServer(app);

// Initialize Socket.IO
const io = new SocketIOServer(server, {
  cors: {
    origin: config.security.corsOrigin,
    methods: ['GET', 'POST'],
    credentials: true,
  },
  transports: ['websocket', 'polling'],
});

// ============================================================================
// MIDDLEWARE SETUP
// ============================================================================

// Security middleware
app.use(helmet({
  contentSecurityPolicy: {
    directives: {
      defaultSrc: ["'self'"],
      styleSrc: ["'self'", "'unsafe-inline'"],
      scriptSrc: ["'self'"],
      imgSrc: ["'self'", "data:", "https:"],
      connectSrc: ["'self'", "ws:", "wss:"],
    },
  },
  crossOriginEmbedderPolicy: false,
}));

// CORS configuration
app.use(cors({
  origin: config.security.corsOrigin,
  credentials: true,
  methods: ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
  allowedHeaders: ['Content-Type', 'Authorization', 'X-Requested-With'],
}));

// Compression
app.use(compression());

// Body parsing
app.use(express.json({ limit: '10mb' }));
app.use(express.urlencoded({ extended: true, limit: '10mb' }));

// Logging
if (config.app.env === 'development') {
  app.use(morgan('dev'));
} else {
  app.use(morgan('combined', {
    stream: {
      write: (message) => logger.http(message.trim()),
    },
  }));
}

// Request ID middleware
app.use((req, res, next) => {
  const requestId = req.headers['x-request-id'] as string ||
    Math.random().toString(36).substring(2, 15);
  req.headers['x-request-id'] = requestId;
  res.setHeader('X-Request-ID', requestId);
  next();
});

// ============================================================================
// ROUTES
// ============================================================================

// API routes
app.use('/api/v1', routes);

// Root endpoint
app.get('/', (req, res) => {
  res.json({
    name: config.app.name,
    version: config.app.version,
    environment: config.app.env,
    status: 'running',
    timestamp: new Date().toISOString(),
  });
});

// Health check endpoint with detailed status
app.get('/health', async (req, res) => {
  try {
    const [dbHealth, redisHealth] = await Promise.all([
      checkDatabaseHealth(),
      checkRedisHealth(),
    ]);

    const status = dbHealth && redisHealth ? 'healthy' : 'unhealthy';

    res.status(status === 'healthy' ? 200 : 503).json({
      status,
      timestamp: new Date().toISOString(),
      services: {
        database: dbHealth,
        redis: redisHealth,
      },
      version: config.app.version,
      uptime: process.uptime(),
    });
  } catch (error) {
    Logger.error('Health check failed', error as Error);
    res.status(503).json({
      status: 'unhealthy',
      timestamp: new Date().toISOString(),
      error: 'Health check failed',
    });
  }
});

// ============================================================================
// WEBSOCKET SETUP
// ============================================================================

// Import WebSocket service
import { WebSocketService } from '@/services/websocket.service';

// Initialize WebSocket service
WebSocketService.initialize(io);

// Export io for use in other modules
export { io };

// ============================================================================
// ERROR HANDLING
// ============================================================================

// 404 handler
app.use(notFoundHandler);

// Global error handler
app.use(errorHandler);

// Unhandled promise rejections
process.on('unhandledRejection', (reason, promise) => {
  Logger.error('Unhandled Rejection at:', reason);
  // Don't crash the server, just log it
});

// Uncaught exceptions
process.on('uncaughtException', (error) => {
  Logger.error('Uncaught Exception:', error);
  // Graceful shutdown
  gracefulShutdown();
});

// ============================================================================
// GRACEFUL SHUTDOWN
// ============================================================================

const gracefulShutdown = async () => {
  Logger.api('Starting graceful shutdown...');

  // Close server
  server.close(() => {
    Logger.api('HTTP server closed');
  });

  // Close database connections
  await disconnectDatabase();
  await disconnectRedis();

  Logger.api('Graceful shutdown completed');
  process.exit(0);
};

// Handle shutdown signals
process.on('SIGTERM', gracefulShutdown);
process.on('SIGINT', gracefulShutdown);

// ============================================================================
// START SERVER
// ============================================================================

const startServer = async () => {
  try {
    // Check database connectivity
    const dbHealth = await checkDatabaseHealth();
    if (!dbHealth) {
      Logger.api('Database connection failed - continuing without database for demo');
      // throw new Error('Database connection failed');
    } else {
      Logger.api('Database connected successfully');
    }

    // Check Redis connectivity
    const redisHealth = await checkRedisHealth();
    if (!redisHealth) {
      Logger.api('Redis connection failed - continuing without Redis');
    } else {
      Logger.api('Redis connected successfully');
    }

    // Start server
    server.listen(config.app.port, () => {
      Logger.api(`🚀 ${config.app.name} server started`);
      Logger.api(`📍 Environment: ${config.app.env}`);
      Logger.api(`🌐 Server running on port ${config.app.port}`);
      Logger.api(`📋 Health check: http://localhost:${config.app.port}/health`);
      Logger.api(`📖 API docs: http://localhost:${config.app.port}/api/v1`);
    });
  } catch (error) {
    Logger.error('Failed to start server', error as Error);
    process.exit(1);
  }
};

// Start the server
startServer();

export default app;