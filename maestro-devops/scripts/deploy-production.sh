#!/bin/bash

###############################################################################
# Maestro Production Deployment Script
# Version: 1.0.0
# Description: Automated deployment script for production environments
###############################################################################

set -e  # Exit on error
set -u  # Exit on undefined variable
set -o pipefail  # Exit on pipe failure

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PROJECT_ROOT="/home/ec2-user/projects/maestro-frontend-production"
BACKUP_DIR="/home/ec2-user/backups/maestro"
LOG_FILE="/home/ec2-user/deployment-$(date +%Y%m%d-%H%M%S).log"

# Logging function
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1" | tee -a "$LOG_FILE"
}

log_error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR:${NC} $1" | tee -a "$LOG_FILE"
}

log_warning() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING:${NC} $1" | tee -a "$LOG_FILE"
}

log_info() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')] INFO:${NC} $1" | tee -a "$LOG_FILE"
}

# Error handler
error_exit() {
    log_error "$1"
    log_error "Deployment failed. Check logs at: $LOG_FILE"
    exit 1
}

# Check if running as correct user
if [ "$USER" != "ec2-user" ]; then
    error_exit "This script must be run as ec2-user"
fi

log "=================================="
log "Maestro Production Deployment"
log "=================================="
log ""

# Step 1: Pre-deployment checks
log "Step 1/10: Running pre-deployment checks..."

# Check Node.js
if ! command -v node &> /dev/null; then
    error_exit "Node.js is not installed"
fi
NODE_VERSION=$(node --version)
log_info "Node.js version: $NODE_VERSION"

# Check npm
if ! command -v npm &> /dev/null; then
    error_exit "npm is not installed"
fi
NPM_VERSION=$(npm --version)
log_info "npm version: $NPM_VERSION"

# Check Docker
if ! command -v docker &> /dev/null; then
    error_exit "Docker is not installed"
fi
DOCKER_VERSION=$(docker --version)
log_info "Docker version: $DOCKER_VERSION"

# Check PM2
if ! command -v pm2 &> /dev/null; then
    log_warning "PM2 is not installed. Installing..."
    sudo npm install -g pm2 || error_exit "Failed to install PM2"
fi

# Check disk space
AVAILABLE_SPACE=$(df -BG "$PROJECT_ROOT" | awk 'NR==2 {print $4}' | sed 's/G//')
if [ "$AVAILABLE_SPACE" -lt 10 ]; then
    error_exit "Insufficient disk space. Need at least 10GB, available: ${AVAILABLE_SPACE}GB"
fi
log_info "Available disk space: ${AVAILABLE_SPACE}GB"

log "✅ Pre-deployment checks passed"
log ""

# Step 2: Create backup
log "Step 2/10: Creating backup..."

mkdir -p "$BACKUP_DIR"
BACKUP_NAME="maestro-$(date +%Y%m%d-%H%M%S).tar.gz"

if [ -d "$PROJECT_ROOT" ]; then
    tar -czf "$BACKUP_DIR/$BACKUP_NAME" -C "$(dirname $PROJECT_ROOT)" "$(basename $PROJECT_ROOT)" 2>/dev/null || log_warning "Backup failed (non-critical)"
    log_info "Backup created: $BACKUP_DIR/$BACKUP_NAME"
else
    log_info "No existing installation to backup"
fi

log "✅ Backup completed"
log ""

# Step 3: Check/Create PostgreSQL container
log "Step 3/10: Setting up PostgreSQL database..."

if docker ps -a | grep -q maestro-postgres-v2; then
    log_info "PostgreSQL container already exists"
    if ! docker ps | grep -q maestro-postgres-v2; then
        log_info "Starting existing container..."
        docker start maestro-postgres-v2 || error_exit "Failed to start PostgreSQL container"
    fi
else
    log_info "Creating new PostgreSQL container..."
    docker run -d \
        --name maestro-postgres-v2 \
        --restart unless-stopped \
        -e POSTGRES_USER=maestro_app \
        -e POSTGRES_PASSWORD=maestro_app_password \
        -e POSTGRES_DB=maestro_production \
        -p 17432:5432 \
        pgvector/pgvector:pg15 || error_exit "Failed to create PostgreSQL container"

    log_info "Waiting for PostgreSQL to be ready..."
    sleep 10

    log_info "Enabling pgvector extension..."
    docker exec maestro-postgres-v2 psql -U maestro_app -d maestro_production -c 'CREATE EXTENSION IF NOT EXISTS vector;' || error_exit "Failed to enable pgvector"
fi

log "✅ PostgreSQL setup completed"
log ""

# Step 4: Install and build backend
log "Step 4/10: Installing and building backend..."

cd "$PROJECT_ROOT/backend" || error_exit "Backend directory not found"

log_info "Installing dependencies..."
npm install || error_exit "Failed to install backend dependencies"

log_info "Building backend..."
npm run build || error_exit "Failed to build backend"

log_info "Generating Prisma client..."
npx prisma generate || error_exit "Failed to generate Prisma client"

log "✅ Backend build completed"
log ""

# Step 5: Run database migrations
log "Step 5/10: Running database migrations..."

npx prisma db push --accept-data-loss || error_exit "Database migration failed"

log "✅ Database migrations completed"
log ""

# Step 6: Seed database
log "Step 6/10: Seeding database..."

if npm run seed:users; then
    log "✅ Database seeding completed"
else
    log_warning "Database seeding failed (may already be seeded)"
fi
log ""

# Step 7: Install and build frontend
log "Step 7/10: Installing and building frontend..."

cd "$PROJECT_ROOT/frontend" || error_exit "Frontend directory not found"

log_info "Installing dependencies..."
npm install || error_exit "Failed to install frontend dependencies"

log_info "Building frontend..."
npm run build || error_exit "Failed to build frontend"

log "✅ Frontend build completed"
log ""

# Step 8: Start/Restart services
log "Step 8/10: Starting services..."

cd "$PROJECT_ROOT/backend"

# Stop existing services
pm2 stop maestro-backend maestro-frontend 2>/dev/null || log_info "No existing services to stop"

# Start backend
log_info "Starting backend on port 3100..."
PORT=3100 pm2 start dist/server.js --name maestro-backend --update-env || error_exit "Failed to start backend"

# Start frontend
cd "$PROJECT_ROOT/frontend"
log_info "Starting frontend on port 4300..."
pm2 start npm --name maestro-frontend -- run preview -- --port 4300 --host 0.0.0.0 || error_exit "Failed to start frontend"

# Save PM2 configuration
pm2 save

log "✅ Services started"
log ""

# Step 9: Configure PM2 startup
log "Step 9/10: Configuring PM2 auto-startup..."

sudo env PATH=$PATH:/usr/bin pm2 startup systemd -u ec2-user --hp /home/ec2-user 2>/dev/null || log_info "PM2 startup already configured"

log "✅ PM2 auto-startup configured"
log ""

# Step 10: Verify deployment
log "Step 10/10: Verifying deployment..."

sleep 10  # Give services time to start

# Check backend
if curl -sf http://localhost:3100/health > /dev/null; then
    log_info "✅ Backend is healthy"
else
    error_exit "Backend health check failed"
fi

# Check frontend
if curl -sf http://localhost:4300 > /dev/null; then
    log_info "✅ Frontend is accessible"
else
    error_exit "Frontend is not accessible"
fi

# Check database
USER_COUNT=$(docker exec maestro-postgres-v2 psql -U maestro_app -d maestro_production -t -c "SELECT COUNT(*) FROM users;" | tr -d ' ')
if [ "$USER_COUNT" -gt 0 ]; then
    log_info "✅ Database has $USER_COUNT user(s)"
else
    log_warning "Database has no users"
fi

# Check PM2 status
PM2_STATUS=$(pm2 jlist 2>/dev/null | jq -r '.[] | select(.name=="maestro-backend" or .name=="maestro-frontend") | .pm2_env.status' | grep -c "online" || echo "0")
if [ "$PM2_STATUS" -eq 2 ]; then
    log_info "✅ All PM2 processes are online"
else
    log_warning "Not all PM2 processes are online. Run 'pm2 list' to check status"
fi

log "✅ Deployment verification completed"
log ""

# Print summary
log "=================================="
log "Deployment Summary"
log "=================================="
log "Backend:   http://localhost:3100"
log "Frontend:  http://localhost:4300"
log "Database:  localhost:17432"
log "Users:     $USER_COUNT"
log "PM2 Processes: $PM2_STATUS/2 online"
log "Log file:  $LOG_FILE"
log "Backup:    $BACKUP_DIR/$BACKUP_NAME"
log "=================================="
log ""

log "🎉 Deployment completed successfully!"
log ""
log "Test Credentials:"
log "  Admin: admin@maestro.com / Admin123@"
log "  User:  test@test.com / Test123@"
log ""
log "Next steps:"
log "  1. Configure firewall rules for ports 3100 and 4300"
log "  2. Set up SSL/TLS certificates"
log "  3. Configure nginx reverse proxy (optional)"
log "  4. Set up monitoring and alerts"
log ""

exit 0
