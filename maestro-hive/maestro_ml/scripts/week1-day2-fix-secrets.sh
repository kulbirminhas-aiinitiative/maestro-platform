#!/bin/bash
# Week 1, Day 2-3: Fix Hardcoded Secrets
# Issue #2, #3 - CRITICAL SECURITY
# Estimated: 6 hours

set -e

echo "🔐 Maestro ML - Fix Hardcoded Secrets"
echo "======================================"
echo ""

# Step 1: Generate strong passwords
echo "📝 Step 1: Generating strong passwords..."
POSTGRES_PASSWORD=$(openssl rand -base64 32 | tr -d "=+/" | cut -c1-32)
MINIO_ROOT_PASSWORD=$(openssl rand -base64 32 | tr -d "=+/" | cut -c1-32)
GRAFANA_ADMIN_PASSWORD=$(openssl rand -base64 32 | tr -d "=+/" | cut -c1-32)
JWT_SECRET_KEY=$(openssl rand -base64 64 | tr -d "=+/" | cut -c1-64)
echo "✅ Passwords generated"

# Step 2: Create .env file
echo ""
echo "📝 Step 2: Creating .env file..."
cat > .env << EOF
# Maestro ML - Environment Variables
# Generated: $(date)
# DO NOT COMMIT THIS FILE!

# Database
POSTGRES_USER=maestro
POSTGRES_PASSWORD=$POSTGRES_PASSWORD
POSTGRES_DB=maestro_ml
DATABASE_URL=postgresql+asyncpg://maestro:$POSTGRES_PASSWORD@localhost:15432/maestro_ml

# Redis
REDIS_URL=redis://localhost:16379/0

# MinIO Object Storage
MINIO_ROOT_USER=minioadmin
MINIO_ROOT_PASSWORD=$MINIO_ROOT_PASSWORD
S3_ENDPOINT=http://localhost:9000
S3_BUCKET=maestro-artifacts
AWS_ACCESS_KEY_ID=minioadmin
AWS_SECRET_ACCESS_KEY=$MINIO_ROOT_PASSWORD

# Grafana
GRAFANA_ADMIN_USER=admin
GRAFANA_ADMIN_PASSWORD=$GRAFANA_ADMIN_PASSWORD

# JWT Authentication
JWT_SECRET_KEY=$JWT_SECRET_KEY
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=7

# Application
ENVIRONMENT=development
DEBUG=true
API_HOST=0.0.0.0
API_PORT=8000
EOF

echo "✅ .env file created"

# Step 3: Update .env.example
echo ""
echo "📝 Step 3: Updating .env.example..."
cat > .env.example << 'EOF'
# Maestro ML - Environment Configuration Template
# Copy this file to .env and fill in your values

# Database
POSTGRES_USER=maestro
POSTGRES_PASSWORD=<generate-strong-password>
POSTGRES_DB=maestro_ml
DATABASE_URL=postgresql+asyncpg://maestro:<password>@localhost:15432/maestro_ml

# Redis
REDIS_URL=redis://localhost:16379/0

# MinIO Object Storage
MINIO_ROOT_USER=minioadmin
MINIO_ROOT_PASSWORD=<generate-strong-password>
S3_ENDPOINT=http://localhost:9000
S3_BUCKET=maestro-artifacts
AWS_ACCESS_KEY_ID=minioadmin
AWS_SECRET_ACCESS_KEY=<same-as-minio-password>

# Grafana
GRAFANA_ADMIN_USER=admin
GRAFANA_ADMIN_PASSWORD=<generate-strong-password>

# JWT Authentication (CRITICAL - USE STRONG SECRET!)
JWT_SECRET_KEY=<generate-64-char-random-string>
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=7

# Application
ENVIRONMENT=development
DEBUG=true
API_HOST=0.0.0.0
API_PORT=8000

# Generate passwords with:
# openssl rand -base64 32 | tr -d "=+/" | cut -c1-32
EOF

echo "✅ .env.example updated"

# Step 4: Backup and update docker-compose.yml
echo ""
echo "📝 Step 4: Updating docker-compose.yml..."
cp docker-compose.yml docker-compose.yml.backup
cat > docker-compose.yml << 'EOF'
services:
  # PostgreSQL Database
  postgres:
    image: postgres:14-alpine
    container_name: maestro-postgres
    environment:
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DB: ${POSTGRES_DB}
    ports:
      - "15432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U maestro"]
      interval: 10s
      timeout: 5s
      retries: 5

  # Redis Cache
  redis:
    image: redis:7-alpine
    container_name: maestro-redis
    ports:
      - "16379:6379"
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 3s
      retries: 5

  # MinIO Object Storage
  minio:
    image: minio/minio:latest
    container_name: maestro-minio
    command: server /data --console-address ":9001"
    environment:
      MINIO_ROOT_USER: ${MINIO_ROOT_USER}
      MINIO_ROOT_PASSWORD: ${MINIO_ROOT_PASSWORD}
    ports:
      - "9000:9000"
      - "9001:9001"
    volumes:
      - minio_data:/data
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:9000/minio/health/live"]
      interval: 30s
      timeout: 20s
      retries: 3

  # Grafana
  grafana:
    image: grafana/grafana:latest
    container_name: maestro-grafana
    environment:
      GF_SECURITY_ADMIN_USER: ${GRAFANA_ADMIN_USER}
      GF_SECURITY_ADMIN_PASSWORD: ${GRAFANA_ADMIN_PASSWORD}
      GF_INSTALL_PLUGINS: ""
    ports:
      - "3003:3000"
    volumes:
      - grafana_data:/var/lib/grafana
      - ./infrastructure/monitoring/grafana/dashboards:/etc/grafana/provisioning/dashboards
      - ./infrastructure/monitoring/grafana/datasources:/etc/grafana/provisioning/datasources
    depends_on:
      - prometheus
    healthcheck:
      test: ["CMD-SHELL", "wget --no-verbose --tries=1 --spider http://localhost:3000/api/health || exit 1"]
      interval: 30s
      timeout: 10s
      retries: 3

volumes:
  postgres_data:
  redis_data:
  minio_data:
  grafana_data:
EOF

echo "✅ docker-compose.yml updated (backup saved as docker-compose.yml.backup)"

# Step 5: Ensure .gitignore excludes .env
echo ""
echo "📝 Step 5: Updating .gitignore..."
if ! grep -q "^\.env$" .gitignore 2>/dev/null; then
    echo ".env" >> .gitignore
    echo "✅ Added .env to .gitignore"
else
    echo "✅ .env already in .gitignore"
fi

# Step 6: Show credentials summary
echo ""
echo "🔐 Generated Credentials Summary"
echo "================================="
echo "⚠️  SAVE THESE SECURELY - They are now in .env"
echo ""
echo "PostgreSQL Password: $POSTGRES_PASSWORD"
echo "MinIO Root Password: $MINIO_ROOT_PASSWORD"
echo "Grafana Admin Password: $GRAFANA_ADMIN_PASSWORD"
echo "JWT Secret Key: ${JWT_SECRET_KEY:0:20}..."
echo ""
echo "📁 Credentials saved to: .env"
echo "⚠️  NEVER commit .env to git!"

# Step 7: Test docker-compose
echo ""
echo "🧪 Step 6: Testing docker-compose..."
if docker-compose config > /dev/null 2>&1; then
    echo "✅ docker-compose.yml is valid"
else
    echo "❌ docker-compose.yml has errors"
    exit 1
fi

echo ""
echo "🎉 COMPLETE: Secrets secured!"
echo ""
echo "📋 Next Steps:"
echo "  1. Review .env file"
echo "  2. Test: docker-compose up -d"
echo "  3. Verify services start with new passwords"
echo "  4. Proceed to Day 4: Build UIs"
