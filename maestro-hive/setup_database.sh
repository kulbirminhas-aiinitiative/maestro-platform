#!/bin/bash
#
# Database Setup Script for Maestro DAG Workflow System
#
# This script sets up PostgreSQL or SQLite database for workflow persistence.
#
# Usage:
#   ./setup_database.sh [postgres|sqlite]
#
# Examples:
#   ./setup_database.sh postgres    # Setup PostgreSQL (production)
#   ./setup_database.sh sqlite      # Setup SQLite (development)
#

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default to SQLite for development
DB_TYPE=${1:-sqlite}

echo "======================================================================"
echo "  Maestro DAG Workflow - Database Setup"
echo "======================================================================"
echo ""

# =============================================================================
# Function Definitions
# =============================================================================

install_dependencies() {
    echo -e "${BLUE}📦 Installing Python dependencies...${NC}"

    # Check if poetry is available
    if command -v poetry &> /dev/null; then
        echo "Using Poetry for dependency management..."
        poetry add sqlalchemy psycopg2-binary alembic
    else
        echo "Using pip for dependency management..."
        pip3 install sqlalchemy psycopg2-binary alembic
    fi

    echo -e "${GREEN}✅ Dependencies installed${NC}"
    echo ""
}

setup_postgresql() {
    echo -e "${BLUE}🐘 Setting up PostgreSQL...${NC}"
    echo ""

    # Check if PostgreSQL is installed
    if ! command -v psql &> /dev/null; then
        echo -e "${YELLOW}⚠️  PostgreSQL not found. Installing...${NC}"

        # Detect OS and install
        if [[ "$OSTYPE" == "linux-gnu"* ]]; then
            # Amazon Linux 2 / CentOS / RHEL
            if command -v yum &> /dev/null; then
                sudo yum install -y postgresql15 postgresql15-server
                sudo postgresql-setup --initdb
                sudo systemctl enable postgresql
                sudo systemctl start postgresql
            # Debian / Ubuntu
            elif command -v apt-get &> /dev/null; then
                sudo apt-get update
                sudo apt-get install -y postgresql postgresql-contrib
                sudo systemctl enable postgresql
                sudo systemctl start postgresql
            fi
        elif [[ "$OSTYPE" == "darwin"* ]]; then
            # macOS
            brew install postgresql@15
            brew services start postgresql@15
        fi
    fi

    # Check if PostgreSQL is running
    if ! sudo systemctl is-active --quiet postgresql 2>/dev/null; then
        echo -e "${YELLOW}⚠️  Starting PostgreSQL...${NC}"
        sudo systemctl start postgresql
    fi

    echo -e "${GREEN}✅ PostgreSQL is running${NC}"
    echo ""

    # Create database and user
    echo -e "${BLUE}🔧 Creating database and user...${NC}"

    sudo -u postgres psql << EOF
-- Create user if not exists
DO \$\$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_user WHERE usename = 'maestro') THEN
        CREATE USER maestro WITH PASSWORD 'maestro_dev';
    END IF;
END
\$\$;

-- Create database if not exists
SELECT 'CREATE DATABASE maestro_workflows OWNER maestro'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'maestro_workflows')\gexec

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE maestro_workflows TO maestro;
EOF

    echo -e "${GREEN}✅ Database 'maestro_workflows' created${NC}"
    echo ""

    # Set environment variables
    export POSTGRES_HOST=localhost
    export POSTGRES_PORT=5432
    export POSTGRES_DB=maestro_workflows
    export POSTGRES_USER=maestro
    export POSTGRES_PASSWORD=maestro_dev
    export USE_SQLITE=false

    echo -e "${BLUE}📝 Environment variables set:${NC}"
    echo "  POSTGRES_HOST=localhost"
    echo "  POSTGRES_PORT=5432"
    echo "  POSTGRES_DB=maestro_workflows"
    echo "  POSTGRES_USER=maestro"
    echo "  POSTGRES_PASSWORD=maestro_dev"
    echo ""

    # Create .env file
    cat > .env.database << EOF
# PostgreSQL Configuration
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=maestro_workflows
POSTGRES_USER=maestro
POSTGRES_PASSWORD=maestro_dev
USE_SQLITE=false

# Connection Pool Settings
DB_POOL_SIZE=10
DB_MAX_OVERFLOW=20
DB_POOL_TIMEOUT=30
DB_POOL_RECYCLE=3600
EOF

    echo -e "${GREEN}✅ Created .env.database file${NC}"
    echo ""
}

setup_sqlite() {
    echo -e "${BLUE}💾 Setting up SQLite...${NC}"
    echo ""

    # Set environment variables
    export USE_SQLITE=true
    export SQLITE_PATH=maestro_workflows.db

    echo -e "${BLUE}📝 Environment variables set:${NC}"
    echo "  USE_SQLITE=true"
    echo "  SQLITE_PATH=maestro_workflows.db"
    echo ""

    # Create .env file
    cat > .env.database << EOF
# SQLite Configuration (Development)
USE_SQLITE=true
SQLITE_PATH=maestro_workflows.db
EOF

    echo -e "${GREEN}✅ Created .env.database file${NC}"
    echo ""

    echo -e "${YELLOW}ℹ️  SQLite database will be created automatically on first run${NC}"
    echo ""
}

initialize_database() {
    echo -e "${BLUE}🔨 Initializing database schema...${NC}"
    echo ""

    # Source environment variables
    if [ -f .env.database ]; then
        export $(cat .env.database | xargs)
    fi

    # Initialize database using Python script
    python3 << EOF
from database.config import initialize_database

try:
    initialize_database(create_tables=True)
    print("✅ Database initialized successfully")
except Exception as e:
    print(f"❌ Database initialization failed: {e}")
    exit(1)
EOF

    echo ""
    echo -e "${GREEN}✅ Database schema created${NC}"
    echo ""
}

run_migrations() {
    echo -e "${BLUE}🔄 Running database migrations...${NC}"
    echo ""

    # Source environment variables
    if [ -f .env.database ]; then
        export $(cat .env.database | xargs)
    fi

    # Create initial migration if none exist
    if [ ! -d "alembic/versions" ] || [ -z "$(ls -A alembic/versions)" ]; then
        echo "Creating initial migration..."
        alembic revision --autogenerate -m "Initial schema"
    fi

    # Run migrations
    alembic upgrade head

    echo ""
    echo -e "${GREEN}✅ Migrations completed${NC}"
    echo ""
}

verify_setup() {
    echo -e "${BLUE}🔍 Verifying database setup...${NC}"
    echo ""

    # Source environment variables
    if [ -f .env.database ]; then
        export $(cat .env.database | xargs)
    fi

    # Test database connection
    python3 << EOF
from database.config import db_engine

try:
    db_engine.initialize()
    if db_engine.health_check():
        print("✅ Database connection: OK")
        print(f"✅ Database type: {'PostgreSQL' if not db_engine.config.use_sqlite else 'SQLite'}")
    else:
        print("❌ Database connection: FAILED")
        exit(1)
except Exception as e:
    print(f"❌ Database verification failed: {e}")
    exit(1)
EOF

    echo ""
}

print_next_steps() {
    echo "======================================================================"
    echo -e "${GREEN}🎉 Database setup complete!${NC}"
    echo "======================================================================"
    echo ""
    echo "Next steps:"
    echo ""
    echo "1. Source environment variables:"
    echo "   ${BLUE}source .env.database${NC}"
    echo ""
    echo "2. Start the API server:"
    if [ "$DB_TYPE" = "postgres" ]; then
        echo "   ${BLUE}python3 dag_api_server_postgres.py${NC}"
    else
        echo "   ${BLUE}USE_SQLITE=true python3 dag_api_server_postgres.py${NC}"
    fi
    echo ""
    echo "3. Test the API:"
    echo "   ${BLUE}curl http://localhost:8000/health${NC}"
    echo ""
    echo "4. View API documentation:"
    echo "   ${BLUE}http://localhost:8000/docs${NC}"
    echo ""
    echo "5. Test workflow execution:"
    echo "   ${BLUE}curl -X POST http://localhost:8000/api/workflows/sdlc_parallel/execute \\${NC}"
    echo "   ${BLUE}  -H 'Content-Type: application/json' \\${NC}"
    echo "   ${BLUE}  -d '{\"requirement\": \"Build a simple todo app\"}'${NC}"
    echo ""
    echo "======================================================================"
}

# =============================================================================
# Main Script
# =============================================================================

# Install dependencies
install_dependencies

# Setup database based on type
if [ "$DB_TYPE" = "postgres" ]; then
    setup_postgresql
elif [ "$DB_TYPE" = "sqlite" ]; then
    setup_sqlite
else
    echo -e "${RED}❌ Invalid database type: $DB_TYPE${NC}"
    echo "Usage: $0 [postgres|sqlite]"
    exit 1
fi

# Initialize database
initialize_database

# Run migrations (optional, can be skipped if using create_tables)
# run_migrations

# Verify setup
verify_setup

# Print next steps
print_next_steps
