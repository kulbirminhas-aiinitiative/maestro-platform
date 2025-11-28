import dotenv from 'dotenv';

// Load environment variables
dotenv.config();

export const config = {
  // Application
  app: {
    name: 'Sunday.com API',
    version: '1.0.0',
    port: parseInt(process.env.PORT || '3000'),
    env: process.env.NODE_ENV || 'development',
  },

  // Database
  database: {
    url: process.env.DATABASE_URL!,
    testUrl: process.env.DATABASE_URL_TEST,
  },

  // Redis
  redis: {
    url: process.env.REDIS_URL || 'redis://localhost:6379',
    host: process.env.REDIS_HOST || 'localhost',
    port: parseInt(process.env.REDIS_PORT || '6379'),
    password: process.env.REDIS_PASSWORD,
  },

  // JWT
  jwt: {
    secret: process.env.JWT_SECRET!,
    expiresIn: process.env.JWT_EXPIRES_IN || '24h',
    refreshSecret: process.env.JWT_REFRESH_SECRET!,
    refreshExpiresIn: process.env.JWT_REFRESH_EXPIRES_IN || '7d',
  },

  // Auth0
  auth0: {
    domain: process.env.AUTH0_DOMAIN,
    clientId: process.env.AUTH0_CLIENT_ID,
    clientSecret: process.env.AUTH0_CLIENT_SECRET,
    audience: process.env.AUTH0_AUDIENCE,
  },

  // Email
  email: {
    sendgridApiKey: process.env.SENDGRID_API_KEY,
    fromEmail: process.env.FROM_EMAIL || 'noreply@sunday.com',
  },

  // AWS
  aws: {
    region: process.env.AWS_REGION || 'us-east-1',
    accessKeyId: process.env.AWS_ACCESS_KEY_ID,
    secretAccessKey: process.env.AWS_SECRET_ACCESS_KEY,
    s3Bucket: process.env.S3_BUCKET || 'sunday-files-dev',
    cloudfrontDomain: process.env.CLOUDFRONT_DOMAIN,
  },

  // File Upload
  upload: {
    maxFileSize: process.env.MAX_FILE_SIZE || '100MB',
    allowedFileTypes: process.env.ALLOWED_FILE_TYPES?.split(',') || [
      'image/*',
      'application/pdf',
      'text/*',
      'application/vnd.ms-excel',
      'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    ],
  },

  // Rate Limiting
  rateLimit: {
    windowMs: parseInt(process.env.RATE_LIMIT_WINDOW_MS || '900000'),
    maxRequests: parseInt(process.env.RATE_LIMIT_MAX_REQUESTS || '100'),
  },

  // Logging
  logging: {
    level: process.env.LOG_LEVEL || 'info',
  },

  // Security
  security: {
    corsOrigin: process.env.CORS_ORIGIN || 'http://localhost:3001',
    bcryptRounds: parseInt(process.env.BCRYPT_ROUNDS || '12'),
    sessionSecret: process.env.SESSION_SECRET!,
    webhookSecret: process.env.WEBHOOK_SECRET!,
  },

  // External Services
  external: {
    sentryDsn: process.env.SENTRY_DSN,
    elasticsearchUrl: process.env.ELASTICSEARCH_URL || 'http://localhost:9200',
    elasticsearchUsername: process.env.ELASTICSEARCH_USERNAME,
    elasticsearchPassword: process.env.ELASTICSEARCH_PASSWORD,
    clickhouseUrl: process.env.CLICKHOUSE_URL || 'http://localhost:8123',
    clickhouseUsername: process.env.CLICKHOUSE_USERNAME || 'default',
    clickhousePassword: process.env.CLICKHOUSE_PASSWORD,
    clickhouseDatabase: process.env.CLICKHOUSE_DATABASE || 'sunday_analytics',
    openaiApiKey: process.env.OPENAI_API_KEY,
    openaiModel: process.env.OPENAI_MODEL || 'gpt-4',
  },

  // WebSocket
  websocket: {
    heartbeatInterval: parseInt(process.env.WS_HEARTBEAT_INTERVAL || '30000'),
    maxConnections: parseInt(process.env.WS_MAX_CONNECTIONS || '1000'),
  },

  // Feature Flags
  features: {
    enableAnalytics: process.env.ENABLE_ANALYTICS === 'true',
    enableAiFeatures: process.env.ENABLE_AI_FEATURES === 'true',
    enableWebhooks: process.env.ENABLE_WEBHOOKS === 'true',
    enableSearch: process.env.ENABLE_SEARCH === 'true',
  },
} as const;

// Validate required environment variables
const requiredEnvVars = [
  'DATABASE_URL',
  'JWT_SECRET',
  'JWT_REFRESH_SECRET',
  'SESSION_SECRET',
  'WEBHOOK_SECRET',
];

for (const envVar of requiredEnvVars) {
  if (!process.env[envVar]) {
    throw new Error(`Missing required environment variable: ${envVar}`);
  }
}

export default config;