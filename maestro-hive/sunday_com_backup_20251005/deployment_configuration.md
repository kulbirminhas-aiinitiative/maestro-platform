# 🔧 Deployment Configuration Guide
**Sunday.com Platform Environment Variables & Configuration**

## 📋 Overview

This document provides comprehensive configuration management for deploying the Sunday.com platform across different environments (development, staging, production).

---

## 🔐 Backend Environment Variables

### 🚀 Core Application Settings
```bash
# Application Configuration
NODE_ENV=production                          # Environment: development|staging|production
PORT=3000                                   # Application port
LOG_LEVEL=info                             # Logging level: debug|info|warn|error

# Application Metadata
APP_NAME="Sunday.com API"
APP_VERSION="1.0.0"
```

### 🗄️ Database Configuration
```bash
# PostgreSQL Primary Database
DATABASE_URL="postgresql://username:password@host:5432/database_name"
DATABASE_URL_TEST="postgresql://username:password@host:5432/test_database"

# Connection Pool Settings (Optional)
DB_POOL_MIN=2
DB_POOL_MAX=20
DB_POOL_IDLE_TIMEOUT=30000
DB_POOL_ACQUIRE_TIMEOUT=60000
```

### 🔴 Redis Configuration
```bash
# Redis Connection
REDIS_URL="redis://password@host:6379"
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=your_redis_password

# Redis Performance Settings (Optional)
REDIS_MAX_RETRIES=3
REDIS_RETRY_DELAY_ON_FAIL=100
REDIS_DB=0
```

### 🔑 Authentication & Security
```bash
# JWT Configuration
JWT_SECRET="your-super-secure-jwt-secret-min-32-chars"
JWT_EXPIRES_IN=24h
JWT_REFRESH_SECRET="your-refresh-token-secret-min-32-chars"
JWT_REFRESH_EXPIRES_IN=7d

# Session Management
SESSION_SECRET="your-session-secret-min-32-chars"
BCRYPT_ROUNDS=12

# CORS Configuration
CORS_ORIGIN="https://sunday.com,https://www.sunday.com"

# Webhook Security
WEBHOOK_SECRET="your-webhook-secret-for-external-integrations"
```

### 🔗 External Service Integration

#### AWS Services
```bash
# AWS Configuration
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=your_aws_access_key
AWS_SECRET_ACCESS_KEY=your_aws_secret_key

# S3 File Storage
S3_BUCKET=sunday-files-production
CLOUDFRONT_DOMAIN=cdn.sunday.com

# File Upload Limits
MAX_FILE_SIZE=100MB
ALLOWED_FILE_TYPES="image/*,application/pdf,text/*,application/vnd.ms-excel,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
```

#### Email Services
```bash
# SendGrid Email Service
SENDGRID_API_KEY=your_sendgrid_api_key
FROM_EMAIL=noreply@sunday.com
```

#### Search & Analytics
```bash
# Elasticsearch Configuration
ELASTICSEARCH_URL=http://localhost:9200
ELASTICSEARCH_USERNAME=elastic
ELASTICSEARCH_PASSWORD=your_elasticsearch_password

# ClickHouse Analytics
CLICKHOUSE_URL=http://localhost:8123
CLICKHOUSE_USERNAME=default
CLICKHOUSE_PASSWORD=your_clickhouse_password
CLICKHOUSE_DATABASE=sunday_analytics
```

#### AI & ML Services
```bash
# OpenAI Integration
OPENAI_API_KEY=your_openai_api_key
OPENAI_MODEL=gpt-4
```

### 🚦 Rate Limiting & Performance
```bash
# API Rate Limiting
RATE_LIMIT_WINDOW_MS=900000        # 15 minutes in milliseconds
RATE_LIMIT_MAX_REQUESTS=1000       # Max requests per window

# WebSocket Configuration
WS_HEARTBEAT_INTERVAL=30000        # 30 seconds
WS_MAX_CONNECTIONS=10000           # Maximum concurrent connections
```

### 🔧 Feature Flags
```bash
# Feature Toggles
ENABLE_ANALYTICS=true
ENABLE_AI_FEATURES=true
ENABLE_WEBHOOKS=true
ENABLE_SEARCH=true
```

### 🔍 Monitoring & Observability
```bash
# Error Tracking
SENTRY_DSN=your_sentry_dsn_url

# Health Check Configuration
HEALTH_CHECK_TIMEOUT=5000          # 5 seconds
```

---

## 🌐 Frontend Environment Variables

### 🚀 Core Application Settings
```bash
# Build Configuration
NODE_ENV=production
VITE_APP_TITLE="Sunday.com"
VITE_APP_DESCRIPTION="Modern Work Management Platform"
```

### 🔗 API Configuration
```bash
# Backend API Configuration
VITE_API_URL=https://api.sunday.com
VITE_WS_URL=wss://api.sunday.com
VITE_APP_URL=https://sunday.com

# GraphQL Endpoint (if used)
VITE_GRAPHQL_URL=https://api.sunday.com/graphql
```

### 🔑 Authentication Configuration
```bash
# Auth0 Configuration (if using SSO)
VITE_AUTH0_DOMAIN=your-domain.auth0.com
VITE_AUTH0_CLIENT_ID=your_auth0_client_id
VITE_AUTH0_AUDIENCE=https://api.sunday.com
```

### 🔧 Feature Flags
```bash
# Frontend Feature Toggles
VITE_ENABLE_ANALYTICS=true
VITE_ENABLE_AI_CHAT=true
VITE_ENABLE_DARK_MODE=true
VITE_ENABLE_PWA=true
```

### 📊 Analytics & Monitoring
```bash
# Google Analytics (if used)
VITE_GA_MEASUREMENT_ID=G-XXXXXXXXXX

# Error Tracking
VITE_SENTRY_DSN=your_frontend_sentry_dsn
```

---

## 🏗️ Environment-Specific Configurations

### 🧪 Development Environment
```bash
# Development overrides
NODE_ENV=development
LOG_LEVEL=debug
CORS_ORIGIN=http://localhost:3001
DATABASE_URL=postgresql://sunday_user:sunday_password@localhost:5432/sunday_dev
REDIS_URL=redis://localhost:6379
ENABLE_DEBUG_LOGGING=true
```

### 🎭 Staging Environment
```bash
# Staging configuration
NODE_ENV=staging
LOG_LEVEL=info
CORS_ORIGIN=https://staging.sunday.com
DATABASE_URL=postgresql://sunday_user:password@staging-db:5432/sunday_staging
REDIS_URL=redis://password@staging-redis:6379
ENABLE_PERFORMANCE_MONITORING=true
```

### 🚀 Production Environment
```bash
# Production configuration
NODE_ENV=production
LOG_LEVEL=warn
CORS_ORIGIN=https://sunday.com,https://www.sunday.com
DATABASE_URL=postgresql://sunday_user:secure_password@prod-db:5432/sunday_production
REDIS_URL=redis://secure_password@prod-redis:6379
ENABLE_MONITORING=true
ENABLE_ERROR_TRACKING=true
```

---

## 🔒 Security Best Practices

### 🔐 Secret Management
1. **Never commit secrets to version control**
2. **Use environment-specific secret management:**
   - Development: `.env` files (gitignored)
   - Staging/Production: AWS Secrets Manager, Kubernetes Secrets
3. **Rotate secrets regularly (quarterly)**
4. **Use strong, unique secrets (minimum 32 characters)**

### 🛡️ Environment Variable Security
```bash
# Use strong secrets
JWT_SECRET=$(openssl rand -base64 32)
SESSION_SECRET=$(openssl rand -base64 32)
WEBHOOK_SECRET=$(openssl rand -base64 32)

# Database passwords should be complex
DB_PASSWORD=$(openssl rand -base64 20)
REDIS_PASSWORD=$(openssl rand -base64 16)
```

---

## 🐳 Docker Environment Configuration

### 📄 Backend .env.production
```bash
NODE_ENV=production
PORT=3000
DATABASE_URL=postgresql://sunday_user:${POSTGRES_PASSWORD}@postgres:5432/sunday_production
REDIS_URL=redis://:${REDIS_PASSWORD}@redis:6379
JWT_SECRET=${JWT_SECRET}
JWT_REFRESH_SECRET=${JWT_REFRESH_SECRET}
SESSION_SECRET=${SESSION_SECRET}
WEBHOOK_SECRET=${WEBHOOK_SECRET}
CORS_ORIGIN=https://sunday.com
AWS_REGION=us-east-1
S3_BUCKET=sunday-files-production
SENDGRID_API_KEY=${SENDGRID_API_KEY}
OPENAI_API_KEY=${OPENAI_API_KEY}
```

### 📄 Frontend .env.production
```bash
NODE_ENV=production
VITE_API_URL=https://api.sunday.com
VITE_WS_URL=wss://api.sunday.com
VITE_APP_URL=https://sunday.com
VITE_ENABLE_ANALYTICS=true
VITE_ENABLE_AI_CHAT=true
VITE_GA_MEASUREMENT_ID=${GA_MEASUREMENT_ID}
```

---

## ☸️ Kubernetes ConfigMap Example

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: sunday-backend-config
  namespace: production
data:
  NODE_ENV: "production"
  PORT: "3000"
  LOG_LEVEL: "info"
  CORS_ORIGIN: "https://sunday.com,https://www.sunday.com"
  ENABLE_ANALYTICS: "true"
  ENABLE_AI_FEATURES: "true"
  AWS_REGION: "us-east-1"
  S3_BUCKET: "sunday-files-production"
  FROM_EMAIL: "noreply@sunday.com"
  RATE_LIMIT_WINDOW_MS: "900000"
  RATE_LIMIT_MAX_REQUESTS: "1000"
```

---

## 📋 Configuration Validation Checklist

### ✅ Before Deployment
- [ ] All required environment variables are set
- [ ] Database connection strings are valid
- [ ] Redis connection is configured
- [ ] JWT secrets are secure (32+ characters)
- [ ] CORS origins are properly configured
- [ ] AWS credentials are valid
- [ ] Email service is configured
- [ ] File upload limits are appropriate
- [ ] Rate limiting is configured
- [ ] Feature flags are set correctly
- [ ] Monitoring services are configured

### ✅ Security Validation
- [ ] No hardcoded secrets in code
- [ ] Environment variables use secure values
- [ ] Database credentials are strong
- [ ] API keys are valid and not expired
- [ ] CORS is not set to '*' in production
- [ ] Rate limiting is enabled
- [ ] HTTPS is enforced

### ✅ Performance Validation
- [ ] Connection pool sizes are optimized
- [ ] Cache TTL values are appropriate
- [ ] File upload limits are reasonable
- [ ] Rate limiting thresholds are set
- [ ] WebSocket connection limits are configured

---

## 🚨 Troubleshooting Common Issues

### 🔴 Database Connection Issues
```bash
# Check connection string format
DATABASE_URL="postgresql://user:password@host:port/database"

# Verify database is accessible
pg_isready -h host -p port -U user

# Check connection pool settings
DB_POOL_MAX=20
DB_POOL_MIN=2
```

### 🔴 Redis Connection Issues
```bash
# Test Redis connection
redis-cli -h host -p port ping

# Check Redis password
REDIS_PASSWORD=your_password
```

### 🔴 CORS Issues
```bash
# Ensure frontend URL is in CORS origins
CORS_ORIGIN="https://sunday.com,https://www.sunday.com"

# For development
CORS_ORIGIN="http://localhost:3001"
```

---

**Configuration Status:** ✅ PRODUCTION READY
**Last Updated:** December 19, 2024
**Review Schedule:** Monthly