#!/bin/bash

# Sunday.com Local Development Setup Script
# This script sets up the local development environment

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if required tools are installed
check_prerequisites() {
    log_info "Checking prerequisites..."

    local missing_tools=()

    # Check Docker
    if ! command -v docker &> /dev/null; then
        missing_tools+=("docker")
    fi

    # Check Docker Compose
    if ! command -v docker-compose &> /dev/null; then
        missing_tools+=("docker-compose")
    fi

    # Check Node.js
    if ! command -v node &> /dev/null; then
        missing_tools+=("node")
    fi

    # Check npm
    if ! command -v npm &> /dev/null; then
        missing_tools+=("npm")
    fi

    # Check Git
    if ! command -v git &> /dev/null; then
        missing_tools+=("git")
    fi

    if [ ${#missing_tools[@]} -ne 0 ]; then
        log_error "Missing required tools: ${missing_tools[*]}"
        log_info "Please install the missing tools and run this script again."
        exit 1
    fi

    log_success "All prerequisites are installed"
}

# Setup environment files
setup_environment_files() {
    log_info "Setting up environment files..."

    # Backend environment
    if [ ! -f "backend/.env" ]; then
        log_info "Creating backend/.env from template..."
        cat > backend/.env << 'EOF'
# Database
DATABASE_URL=postgresql://sunday_user:sunday_password@localhost:5432/sunday_db

# Redis
REDIS_URL=redis://localhost:6379

# JWT
JWT_SECRET=your-development-jwt-secret-key
JWT_EXPIRES_IN=24h

# External Services
ELASTICSEARCH_URL=http://localhost:9200
CLICKHOUSE_URL=http://localhost:8123

# File Storage
S3_BUCKET_NAME=sunday-files-dev
AWS_ACCESS_KEY_ID=minioadmin
AWS_SECRET_ACCESS_KEY=minioadmin123
AWS_ENDPOINT=http://localhost:9002

# Email (Development - using Mailhog)
SMTP_HOST=localhost
SMTP_PORT=1025
SMTP_USER=
SMTP_PASS=

# Logging
LOG_LEVEL=debug
NODE_ENV=development

# API Keys (replace with actual keys)
OPENAI_API_KEY=your-openai-api-key
SENDGRID_API_KEY=your-sendgrid-api-key
EOF
        log_success "Created backend/.env"
    else
        log_info "backend/.env already exists"
    fi

    # Frontend environment
    if [ ! -f "frontend/.env" ]; then
        log_info "Creating frontend/.env from template..."
        cat > frontend/.env << 'EOF'
# API Configuration
VITE_API_URL=http://localhost:3000
VITE_WS_URL=ws://localhost:3000

# Environment
VITE_NODE_ENV=development

# Feature Flags
VITE_ENABLE_ANALYTICS=false
VITE_ENABLE_ERROR_REPORTING=false
EOF
        log_success "Created frontend/.env"
    else
        log_info "frontend/.env already exists"
    fi
}

# Install dependencies
install_dependencies() {
    log_info "Installing dependencies..."

    # Backend dependencies
    log_info "Installing backend dependencies..."
    cd backend
    npm ci
    cd ..

    # Frontend dependencies
    log_info "Installing frontend dependencies..."
    cd frontend
    npm ci
    cd ..

    log_success "Dependencies installed"
}

# Setup Docker containers
setup_docker_containers() {
    log_info "Setting up Docker containers..."

    # Stop any existing containers
    log_info "Stopping existing containers..."
    docker-compose down 2>/dev/null || true

    # Build and start containers
    log_info "Building and starting containers..."
    docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d postgres redis elasticsearch clickhouse minio prometheus grafana mailhog

    # Wait for databases to be ready
    log_info "Waiting for databases to be ready..."

    # Wait for PostgreSQL
    local postgres_ready=false
    local attempts=0
    while [ "$postgres_ready" = false ] && [ $attempts -lt 30 ]; do
        if docker-compose exec -T postgres pg_isready -U sunday_dev &>/dev/null; then
            postgres_ready=true
        else
            sleep 2
            ((attempts++))
        fi
    done

    if [ "$postgres_ready" = false ]; then
        log_error "PostgreSQL failed to start"
        exit 1
    fi

    # Wait for Redis
    local redis_ready=false
    attempts=0
    while [ "$redis_ready" = false ] && [ $attempts -lt 30 ]; do
        if docker-compose exec -T redis redis-cli ping &>/dev/null; then
            redis_ready=true
        else
            sleep 2
            ((attempts++))
        fi
    done

    if [ "$redis_ready" = false ]; then
        log_error "Redis failed to start"
        exit 1
    fi

    log_success "Docker containers are running"
}

# Setup database
setup_database() {
    log_info "Setting up database..."

    cd backend

    # Generate Prisma client
    log_info "Generating Prisma client..."
    npx prisma generate

    # Run database migrations
    log_info "Running database migrations..."
    npx prisma migrate dev --name init

    # Seed database (if seed script exists)
    if [ -f "prisma/seed.ts" ] || [ -f "prisma/seed.js" ]; then
        log_info "Seeding database..."
        npx prisma db seed
    fi

    cd ..

    log_success "Database setup complete"
}

# Create MinIO buckets
setup_minio() {
    log_info "Setting up MinIO buckets..."

    # Install mc (MinIO client) if not present
    if ! command -v mc &> /dev/null; then
        log_info "Installing MinIO client..."
        if [[ "$OSTYPE" == "darwin"* ]]; then
            brew install minio/stable/mc
        else
            wget https://dl.min.io/client/mc/release/linux-amd64/mc
            chmod +x mc
            sudo mv mc /usr/local/bin/
        fi
    fi

    # Configure MinIO client
    mc alias set local http://localhost:9002 minioadmin minioadmin123

    # Create buckets
    mc mb local/sunday-files-dev --ignore-existing
    mc policy set public local/sunday-files-dev

    log_success "MinIO setup complete"
}

# Display useful information
display_info() {
    log_success "🎉 Local development environment setup complete!"
    echo
    log_info "Services available at:"
    echo "  📱 Frontend:        http://localhost:5173"
    echo "  🔧 Backend API:     http://localhost:3000"
    echo "  🗄️  PostgreSQL:     localhost:5432"
    echo "  🚀 Redis:           localhost:6379"
    echo "  🔍 Elasticsearch:   http://localhost:9200"
    echo "  📊 ClickHouse:      http://localhost:8123"
    echo "  📦 MinIO:           http://localhost:9001"
    echo "  📈 Prometheus:      http://localhost:9090"
    echo "  📊 Grafana:         http://localhost:3001 (admin/admin123)"
    echo "  📧 Mailhog:         http://localhost:8025"
    echo
    log_info "To start the application:"
    echo "  Backend:  cd backend && npm run dev"
    echo "  Frontend: cd frontend && npm run dev"
    echo
    log_info "To stop services:"
    echo "  docker-compose down"
    echo
    log_info "For more information, see README.md"
}

# Main execution
main() {
    log_info "🚀 Setting up Sunday.com local development environment..."
    echo

    check_prerequisites
    setup_environment_files
    install_dependencies
    setup_docker_containers
    setup_database
    setup_minio
    display_info
}

# Run main function
main "$@"