# Deployment Configuration Guide - Sunday.com

**Project**: Sunday.com Work Management Platform
**Environment**: Production Deployment Configuration
**Last Updated**: December 19, 2024

---

## Environment Variables Configuration

### Backend Environment Variables

#### Required Variables (Deployment Blockers if Missing)

```bash
# Database Configuration - CRITICAL
DATABASE_URL="postgresql://username:password@host:5432/database?schema=public"
DATABASE_URL_TEST="postgresql://username:password@host:5432/test_db?schema=public"

# Security Secrets - CRITICAL
JWT_SECRET="your-super-secret-jwt-key-minimum-32-characters"
JWT_REFRESH_SECRET="your-refresh-token-secret-minimum-32-characters"
SESSION_SECRET="your-session-secret-minimum-32-characters"
WEBHOOK_SECRET="your-webhook-secret-key-minimum-32-characters"
```

#### Application Configuration

```bash
# Application Settings
NODE_ENV=production
PORT=3000

# JWT Configuration
JWT_EXPIRES_IN=24h
JWT_REFRESH_EXPIRES_IN=7d

# CORS Configuration
CORS_ORIGIN=https://your-domain.com
BCRYPT_ROUNDS=12
```

#### External Services

```bash
# Redis Cache (Required for production)
REDIS_URL="redis://redis-host:6379"
REDIS_HOST=redis-host
REDIS_PORT=6379
REDIS_PASSWORD=your-redis-password

# Email Service (SendGrid)
SENDGRID_API_KEY=SG.your-sendgrid-api-key
FROM_EMAIL=noreply@yourdomain.com

# File Storage (AWS S3)
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=your-aws-access-key
AWS_SECRET_ACCESS_KEY=your-aws-secret-key
S3_BUCKET=your-production-bucket
CLOUDFRONT_DOMAIN=cdn.yourdomain.com

# Search & Analytics
ELASTICSEARCH_URL=http://elasticsearch:9200
ELASTICSEARCH_USERNAME=elastic_user
ELASTICSEARCH_PASSWORD=elastic_password
CLICKHOUSE_URL=http://clickhouse:8123
CLICKHOUSE_USERNAME=default
CLICKHOUSE_PASSWORD=clickhouse_password
CLICKHOUSE_DATABASE=sunday_analytics

# AI Features (OpenAI)
OPENAI_API_KEY=sk-your-openai-api-key
OPENAI_MODEL=gpt-4
```

#### Security & Monitoring

```bash
# Rate Limiting
RATE_LIMIT_WINDOW_MS=900000
RATE_LIMIT_MAX_REQUESTS=100

# File Upload Security
MAX_FILE_SIZE=100MB
ALLOWED_FILE_TYPES=image/*,application/pdf,text/*,application/vnd.ms-excel,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet

# Monitoring
LOG_LEVEL=info
SENTRY_DSN=https://your-sentry-dsn@sentry.io/project-id

# WebSocket Configuration
WS_HEARTBEAT_INTERVAL=30000
WS_MAX_CONNECTIONS=1000
```

#### Feature Flags

```bash
# Feature Controls
ENABLE_ANALYTICS=true
ENABLE_AI_FEATURES=true
ENABLE_WEBHOOKS=true
ENABLE_SEARCH=true
```

### Frontend Environment Variables

#### Production Frontend Configuration

Create `frontend/.env.production`:

```bash
# API Configuration
VITE_API_URL=https://api.yourdomain.com
VITE_WS_URL=wss://api.yourdomain.com

# Application URLs
VITE_APP_URL=https://yourdomain.com
VITE_APP_NAME=Sunday.com

# Feature Flags
VITE_ENABLE_ANALYTICS=true
VITE_ENABLE_DEBUG=false

# External Services
VITE_SENTRY_DSN=https://your-frontend-sentry-dsn@sentry.io/project-id

# Auth Configuration
VITE_AUTH0_DOMAIN=your-domain.auth0.com
VITE_AUTH0_CLIENT_ID=your-auth0-client-id
VITE_AUTH0_AUDIENCE=https://api.yourdomain.com
```

#### Development Frontend Configuration

Create `frontend/.env.example`:

```bash
# Development API Configuration
VITE_API_URL=http://localhost:3000
VITE_WS_URL=ws://localhost:3000

# Development Application URLs
VITE_APP_URL=http://localhost:3001
VITE_APP_NAME=Sunday.com (Dev)

# Development Feature Flags
VITE_ENABLE_ANALYTICS=false
VITE_ENABLE_DEBUG=true

# Development External Services
VITE_SENTRY_DSN=

# Development Auth Configuration
VITE_AUTH0_DOMAIN=dev-domain.auth0.com
VITE_AUTH0_CLIENT_ID=dev-auth0-client-id
VITE_AUTH0_AUDIENCE=https://api.dev.yourdomain.com
```

---

## Docker Configuration

### Production Docker Compose

```yaml
# docker-compose.prod.yml
version: '3.8'

services:
  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
      target: runner
    environment:
      NODE_ENV: production
      PORT: 3000
      DATABASE_URL: ${DATABASE_URL}
      REDIS_URL: ${REDIS_URL}
      JWT_SECRET: ${JWT_SECRET}
      JWT_REFRESH_SECRET: ${JWT_REFRESH_SECRET}
      SESSION_SECRET: ${SESSION_SECRET}
      WEBHOOK_SECRET: ${WEBHOOK_SECRET}
      CORS_ORIGIN: ${CORS_ORIGIN}
      SENDGRID_API_KEY: ${SENDGRID_API_KEY}
      AWS_ACCESS_KEY_ID: ${AWS_ACCESS_KEY_ID}
      AWS_SECRET_ACCESS_KEY: ${AWS_SECRET_ACCESS_KEY}
      S3_BUCKET: ${S3_BUCKET}
      OPENAI_API_KEY: ${OPENAI_API_KEY}
    ports:
      - "3000:3000"
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "node", "docker-healthcheck.js"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 30s

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
      target: runner
    ports:
      - "80:80"
    restart: unless-stopped
    depends_on:
      - backend
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:80/"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 10s
```

### Environment File Structure

```
project-root/
├── .env.production              # Production secrets (NOT in git)
├── .env.example                 # Template for production (in git)
├── backend/
│   ├── .env                     # Local development (NOT in git)
│   ├── .env.example             # Development template (in git)
├── frontend/
│   ├── .env.production          # Frontend production (NOT in git)
│   ├── .env.local               # Frontend development (NOT in git)
│   └── .env.example             # Frontend template (in git)
```

---

## Deployment Checklist

### Pre-Deployment Validation

#### Environment Setup
- [ ] All required environment variables configured
- [ ] Database connection string valid and tested
- [ ] Redis connection configured and accessible
- [ ] AWS S3 bucket created and accessible
- [ ] SendGrid API key configured and tested
- [ ] OpenAI API key configured (if AI features enabled)

#### Security Configuration
- [ ] JWT secrets are cryptographically strong (32+ characters)
- [ ] CORS origin matches production domain
- [ ] Rate limiting configured appropriately
- [ ] File upload restrictions configured
- [ ] HTTPS certificates configured

#### Build Validation
- [ ] Backend build completes successfully
- [ ] Frontend build completes successfully
- [ ] Docker images build without errors
- [ ] Health checks respond correctly

#### Database Setup
- [ ] Production database created
- [ ] Database migrations executed
- [ ] Database user permissions configured
- [ ] Connection pooling configured

### Post-Deployment Validation

#### Service Health
- [ ] Backend health endpoint responds (GET /health)
- [ ] Frontend loads successfully
- [ ] Database connectivity confirmed
- [ ] Redis connectivity confirmed
- [ ] WebSocket connections working

#### Functional Testing
- [ ] User authentication works
- [ ] API endpoints respond correctly
- [ ] Real-time features functional
- [ ] File upload/download works
- [ ] Email notifications sent (if configured)

#### Monitoring Setup
- [ ] Application logs being collected
- [ ] Error tracking configured (Sentry)
- [ ] Performance monitoring active
- [ ] Health check alerts configured

---

## Security Considerations

### Production Security Requirements

#### SSL/TLS Configuration
```nginx
# Frontend nginx configuration
server {
    listen 80;
    server_name yourdomain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name yourdomain.com;

    ssl_certificate /path/to/certificate.crt;
    ssl_certificate_key /path/to/private.key;

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
}
```

#### Environment Variable Security
- Use secrets management (AWS Secrets Manager, HashiCorp Vault)
- Never commit `.env` files to version control
- Rotate secrets regularly
- Use different secrets for each environment

#### Database Security
- Use dedicated database user with minimal permissions
- Enable SSL connections
- Regular backups with encryption
- Network isolation (VPC/private subnets)

---

## Scaling Configuration

### Horizontal Scaling

#### Load Balancer Configuration
```yaml
# Docker Compose with multiple backend instances
services:
  backend:
    deploy:
      replicas: 3
    environment:
      - NODE_ENV=production
      # ... other environment variables

  nginx-lb:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
    depends_on:
      - backend
```

#### Redis Session Store
```javascript
// Ensure session persistence across instances
const session = require('express-session');
const RedisStore = require('connect-redis')(session);

app.use(session({
  store: new RedisStore({ client: redisClient }),
  secret: process.env.SESSION_SECRET,
  resave: false,
  saveUninitialized: false,
  cookie: {
    secure: process.env.NODE_ENV === 'production',
    httpOnly: true,
    maxAge: 24 * 60 * 60 * 1000 // 24 hours
  }
}));
```

### Database Scaling
- Read replicas for query distribution
- Connection pooling configuration
- Query optimization and indexing
- Backup and disaster recovery procedures

---

## Monitoring & Logging

### Required Monitoring Endpoints

#### Health Checks
```bash
# Backend health
GET https://api.yourdomain.com/health

# Expected response
{
  "status": "healthy",
  "timestamp": "2024-12-19T10:00:00Z",
  "services": {
    "database": true,
    "redis": true
  },
  "version": "1.0.0",
  "uptime": 3600
}
```

#### Metrics Collection
- Application performance metrics
- Database query performance
- Error rates and types
- User activity metrics
- System resource utilization

### Log Management
```javascript
// Production logging configuration
const winston = require('winston');

const logger = winston.createLogger({
  level: 'info',
  format: winston.format.combine(
    winston.format.timestamp(),
    winston.format.errors({ stack: true }),
    winston.format.json()
  ),
  transports: [
    new winston.transports.File({ filename: 'error.log', level: 'error' }),
    new winston.transports.File({ filename: 'combined.log' })
  ]
});
```

---

## Troubleshooting Guide

### Common Deployment Issues

#### Environment Variable Issues
```bash
# Verify environment variables are loaded
docker exec -it sunday-backend env | grep NODE_ENV
docker exec -it sunday-backend env | grep DATABASE_URL
```

#### Database Connection Issues
```bash
# Test database connectivity
docker exec -it sunday-backend npm run migrate:status
docker exec -it sunday-backend npx prisma db pull
```

#### Redis Connection Issues
```bash
# Test Redis connectivity
docker exec -it sunday-redis redis-cli ping
docker exec -it sunday-backend node -e "console.log(require('./src/config/redis').checkRedisHealth())"
```

#### Build Issues
```bash
# Clean rebuild
docker system prune -a
docker-compose build --no-cache
docker-compose up -d
```

### Performance Issues
- Check database query performance
- Monitor Redis memory usage
- Verify file upload/download speeds
- Check WebSocket connection counts
- Monitor API response times

---

**Configuration Author**: Senior DevOps Engineer
**Last Review**: December 19, 2024
**Environment**: Production Ready
**Status**: Validated Configuration