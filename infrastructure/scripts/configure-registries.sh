#!/bin/bash
# Maestro Platform - Registry Configuration Script
# Configures local environment to use Harbor, Nexus, and other artifact registries
#
# Usage:
#   ./configure-registries.sh [--docker] [--npm] [--pip] [--all]
#
# Options:
#   --docker     Configure Docker to use Harbor
#   --npm        Configure npm to use Nexus
#   --pip        Configure pip to use Nexus
#   --all        Configure all registries

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
HARBOR_URL="${HARBOR_URL:-localhost:28080}"
NEXUS_URL="${NEXUS_URL:-localhost:28081}"
NEXUS_DOCKER_URL="${NEXUS_DOCKER_URL:-localhost:28082}"
NEXUS_NPM_URL="${NEXUS_NPM_URL:-localhost:28084}"
NEXUS_PYPI_URL="${NEXUS_PYPI_URL:-localhost:28081}"

# Functions
print_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

configure_docker() {
    print_info "Configuring Docker to use Harbor registry..."

    # Check if Docker is installed
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed. Please install Docker first."
        return 1
    fi

    # Add Harbor as insecure registry (for development)
    DOCKER_CONFIG="/etc/docker/daemon.json"

    if [[ "$OSTYPE" == "darwin"* ]]; then
        print_info "macOS detected. Please manually add Harbor to Docker Desktop:"
        echo "  1. Open Docker Desktop → Preferences → Docker Engine"
        echo "  2. Add to the JSON config:"
        echo "     \"insecure-registries\": [\"${HARBOR_URL}\"]"
        return 0
    fi

    # Linux configuration
    if [ ! -f "$DOCKER_CONFIG" ]; then
        print_info "Creating Docker daemon config..."
        sudo mkdir -p /etc/docker
        echo '{}' | sudo tee "$DOCKER_CONFIG" > /dev/null
    fi

    # Check if already configured
    if grep -q "insecure-registries" "$DOCKER_CONFIG"; then
        print_warn "Docker already has insecure-registries configured."
        print_info "Current config:"
        sudo cat "$DOCKER_CONFIG" | grep -A 2 "insecure-registries"
    else
        print_info "Adding Harbor to insecure registries..."
        # Backup original config
        sudo cp "$DOCKER_CONFIG" "${DOCKER_CONFIG}.backup"

        # Add insecure registry using jq if available, otherwise manual
        if command -v jq &> /dev/null; then
            sudo jq ". + {\"insecure-registries\": [\"${HARBOR_URL}\"]}" "$DOCKER_CONFIG" | sudo tee "${DOCKER_CONFIG}.tmp" > /dev/null
            sudo mv "${DOCKER_CONFIG}.tmp" "$DOCKER_CONFIG"
        else
            print_warn "jq not found. Please manually add to $DOCKER_CONFIG:"
            echo "  \"insecure-registries\": [\"${HARBOR_URL}\"]"
            return 0
        fi

        # Restart Docker daemon
        print_info "Restarting Docker daemon..."
        sudo systemctl restart docker || print_warn "Could not restart Docker. Please restart manually."
    fi

    print_info "✓ Docker configuration complete"
    print_info "Test with: docker login ${HARBOR_URL}"
    print_info "  Username: admin"
    print_info "  Password: (from .env.infrastructure HARBOR_ADMIN_PASSWORD)"
}

configure_npm() {
    print_info "Configuring npm to use Nexus registry..."

    # Check if npm is installed
    if ! command -v npm &> /dev/null; then
        print_error "npm is not installed. Please install Node.js first."
        return 1
    fi

    # Configure npm registry
    print_info "Setting Nexus as npm registry..."
    npm config set registry http://${NEXUS_NPM_URL}/repository/npm-group/

    # Configure npm credentials (optional, for publishing)
    print_info "To publish packages, configure authentication:"
    echo "  npm login --registry=http://${NEXUS_NPM_URL}/repository/npm-hosted/"

    # Create/update .npmrc in project root
    if [ -f ".npmrc" ]; then
        print_warn ".npmrc already exists. Backing up to .npmrc.backup"
        cp .npmrc .npmrc.backup
    fi

    cat > .npmrc <<EOF
# Maestro Platform - Nexus npm Registry
registry=http://${NEXUS_NPM_URL}/repository/npm-group/

# For publishing (uncomment and add token after npm login)
# //${NEXUS_NPM_URL}/repository/npm-hosted/:_authToken=\${NPM_TOKEN}
EOF

    print_info "✓ npm configuration complete"
    print_info "  .npmrc created in current directory"
    print_info "  Global npm registry: $(npm config get registry)"
}

configure_pip() {
    print_info "Configuring pip to use Nexus PyPI registry..."

    # Check if pip is installed
    if ! command -v pip &> /dev/null && ! command -v pip3 &> /dev/null; then
        print_error "pip is not installed. Please install Python first."
        return 1
    fi

    # Determine pip config location
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        PIP_CONFIG="$HOME/.config/pip/pip.conf"
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        PIP_CONFIG="$HOME/Library/Application Support/pip/pip.conf"
    else
        PIP_CONFIG="$HOME/.pip/pip.conf"
    fi

    # Create directory if it doesn't exist
    mkdir -p "$(dirname "$PIP_CONFIG")"

    # Backup existing config
    if [ -f "$PIP_CONFIG" ]; then
        print_warn "Backing up existing pip config to ${PIP_CONFIG}.backup"
        cp "$PIP_CONFIG" "${PIP_CONFIG}.backup"
    fi

    # Create pip configuration
    cat > "$PIP_CONFIG" <<EOF
# Maestro Platform - Nexus PyPI Registry
[global]
index-url = http://${NEXUS_PYPI_URL}/repository/pypi-group/simple
trusted-host = ${NEXUS_PYPI_URL}

[install]
trusted-host = ${NEXUS_PYPI_URL}

# For publishing (use twine with --repository-url)
# twine upload --repository-url http://${NEXUS_PYPI_URL}/repository/pypi-hosted/ dist/*
EOF

    print_info "✓ pip configuration complete"
    print_info "  Config file: $PIP_CONFIG"
    print_info "Test with: pip install requests"
}

show_help() {
    cat <<EOF
Maestro Platform - Registry Configuration Script

Usage: $0 [OPTIONS]

Options:
  --docker     Configure Docker to use Harbor registry
  --npm        Configure npm to use Nexus npm registry
  --pip        Configure pip to use Nexus PyPI registry
  --all        Configure all registries
  --help       Show this help message

Examples:
  $0 --all                  # Configure all registries
  $0 --docker --npm         # Configure only Docker and npm

After Configuration:
  1. Docker: docker login ${HARBOR_URL}
  2. npm: npm login --registry=http://${NEXUS_NPM_URL}/repository/npm-hosted/
  3. pip: pip install <package>  # Uses Nexus automatically

Registry URLs:
  Harbor:       http://${HARBOR_URL}
  Nexus Web UI: http://${NEXUS_URL}
  Nexus Docker: http://${NEXUS_DOCKER_URL}
  Nexus npm:    http://${NEXUS_NPM_URL}
  Nexus PyPI:   http://${NEXUS_PYPI_URL}

Credentials:
  Check infrastructure/.env.infrastructure for passwords
EOF
}

# Main script
main() {
    if [ $# -eq 0 ]; then
        show_help
        exit 0
    fi

    print_info "Maestro Platform - Registry Configuration"
    print_info "=========================================="

    while [ $# -gt 0 ]; do
        case "$1" in
            --docker)
                configure_docker
                shift
                ;;
            --npm)
                configure_npm
                shift
                ;;
            --pip)
                configure_pip
                shift
                ;;
            --all)
                configure_docker
                configure_npm
                configure_pip
                shift
                ;;
            --help|-h)
                show_help
                exit 0
                ;;
            *)
                print_error "Unknown option: $1"
                show_help
                exit 1
                ;;
        esac
    done

    print_info ""
    print_info "=========================================="
    print_info "✓ Configuration complete!"
    print_info ""
    print_info "Next steps:"
    print_info "  1. Start infrastructure: cd infrastructure && docker-compose -f docker-compose.infrastructure.yml up -d"
    print_info "  2. Access UIs:"
    print_info "     - Harbor:  http://${HARBOR_URL}"
    print_info "     - Nexus:   http://${NEXUS_URL}"
    print_info "     - MinIO:   http://localhost:29001"
    print_info "     - MLflow:  http://localhost:25000"
}

main "$@"
