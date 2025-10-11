#!/bin/bash
#
# Generate Secure Secrets for Maestro ML Platform
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
ENV_FILE="$PROJECT_ROOT/.env"

echo "🔐 Generating Secure Secrets"
echo "=============================="
echo ""

# Check if .env already exists
if [ -f "$ENV_FILE" ]; then
    echo "⚠️  Warning: .env file already exists!"
    read -p "   Overwrite? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "❌ Aborted. Existing .env file preserved."
        exit 1
    fi
    # Backup existing file
    cp "$ENV_FILE" "$ENV_FILE.backup.$(date +%Y%m%d_%H%M%S)"
    echo "📦 Backup created: $ENV_FILE.backup.$(date +%Y%m%d_%H%M%S)"
fi

echo "🔑 Generating cryptographic secrets..."

# Generate strong random secrets
JWT_SECRET=$(openssl rand -base64 32)
JWT_REFRESH_SECRET=$(openssl rand -base64 32)
DB_PASSWORD=$(openssl rand -base64 24)
REDIS_PASSWORD=$(openssl rand -base64 24)
ENCRYPTION_KEY=$(openssl rand -base64 32)
API_SECRET_KEY=$(openssl rand -hex 32)

# Create .env file
cat > "$ENV_FILE" <<EOF
# Maestro ML Platform - Environment Configuration
# Generated: $(date)
# 
# ⚠️  SECURITY WARNING:
#   - Keep this file secure and never commit to git
#   - Rotate secrets regularly (every 90 days recommended)
#   - Use different secrets for dev/staging/production
#   - Store production secrets in a secrets manager (AWS Secrets Manager, Vault)

# Environment
ENVIRONMENT=development

# Database Configuration
POSTGRES_USER=maestro
POSTGRES_PASSWORD=$DB_PASSWORD
POSTGRES_DB=maestro_ml
DATABASE_URL=postgresql+asyncpg://maestro:$DB_PASSWORD@localhost:15432/maestro_ml

# Redis Configuration
REDIS_PASSWORD=$REDIS_PASSWORD
REDIS_URL=redis://:$REDIS_PASSWORD@localhost:16379/0

# JWT Authentication
JWT_SECRET_KEY=$JWT_SECRET
JWT_REFRESH_SECRET_KEY=$JWT_REFRESH_SECRET
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=7

# Encryption
ENCRYPTION_KEY=$ENCRYPTION_KEY

# API Configuration
API_SECRET_KEY=$API_SECRET_KEY
API_HOST=0.0.0.0
API_PORT=8000
API_HTTPS_PORT=8443

# CORS Origins (comma-separated)
CORS_ORIGINS=http://localhost:3000,http://localhost:8000,https://localhost:8443

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json

# Feature Flags
ENABLE_MULTI_TENANCY=true
ENABLE_AUDIT_LOGGING=true
ENABLE_RATE_LIMITING=true

# Rate Limiting
RATE_LIMIT_PER_MINUTE=60
RATE_LIMIT_BURST=10

# MinIO/S3 (if used)
# MINIO_ACCESS_KEY=$(openssl rand -hex 16)
# MINIO_SECRET_KEY=$(openssl rand -base64 24)
# MINIO_ENDPOINT=localhost:9000

# MLflow (if used)
# MLFLOW_TRACKING_URI=http://localhost:5000
EOF

# Set strict permissions
chmod 600 "$ENV_FILE"

echo ""
echo "✅ Secrets generated successfully!"
echo ""
echo "📁 Environment file: $ENV_FILE"
echo "🔒 Permissions: 600 (read/write owner only)"
echo ""
echo "🔑 Generated secrets:"
echo "   - JWT Access Token Secret (256-bit)"
echo "   - JWT Refresh Token Secret (256-bit)"
echo "   - Database Password (192-bit)"
echo "   - Redis Password (192-bit)"
echo "   - Encryption Key (256-bit)"
echo "   - API Secret Key (256-bit)"
echo ""
echo "⚠️  IMPORTANT SECURITY NOTES:"
echo "   1. Never commit .env to git (already in .gitignore)"
echo "   2. Use different secrets for each environment"
echo "   3. Rotate secrets every 90 days"
echo "   4. For production, use a secrets manager:"
echo "      - AWS Secrets Manager"
echo "      - HashiCorp Vault"
echo "      - Azure Key Vault"
echo ""
echo "📋 Next steps:"
echo "   1. Review and customize .env file"
echo "   2. Update docker-compose.yml to use env_file: .env"
echo "   3. Update application to load from environment"
echo "   4. Test configuration: poetry run python -c 'from maestro_ml.config.settings import get_settings; print(get_settings())'"
echo ""
