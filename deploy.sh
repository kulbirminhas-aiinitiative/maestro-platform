#!/bin/bash
#
# Maestro Platform - Automated Deployment Script
# Usage: ./deploy.sh [environment] [options]
#
# Environments: development (default), demo, production
# Options: --skip-tests, --stop, --health
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEPLOY_SCRIPT="$SCRIPT_DIR/services/cicd/maestro_deploy.py"

# Default values
ENVIRONMENT="${1:-development}"
ACTION="deploy"

# Parse arguments
shift 2>/dev/null || true
EXTRA_ARGS=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --skip-tests)
            EXTRA_ARGS="$EXTRA_ARGS --skip-tests"
            shift
            ;;
        --stop)
            ACTION="stop"
            shift
            ;;
        --health)
            ACTION="health"
            shift
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Banner
echo "╔════════════════════════════════════════════════════════════╗"
echo "║     Maestro Platform - Automated Deployment Service       ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""
echo "Environment: $ENVIRONMENT"
echo "Action: $ACTION"
echo ""

# Check Python dependencies
if ! python3 -c "import yaml" 2>/dev/null; then
    echo "⚠️  Installing required Python packages..."
    pip3 install --quiet pyyaml requests
fi

# Run deployment
python3 "$DEPLOY_SCRIPT" $ACTION --environment "$ENVIRONMENT" $EXTRA_ARGS

EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then
    echo ""
    echo "╔════════════════════════════════════════════════════════════╗"
    echo "║                    ✅ SUCCESS                               ║"
    echo "╚════════════════════════════════════════════════════════════╝"

    if [ "$ACTION" == "deploy" ]; then
        echo ""
        echo "Services are now running in $ENVIRONMENT environment"
        echo ""
        echo "Next steps:"
        echo "  - Check health: ./deploy.sh $ENVIRONMENT --health"
        echo "  - View logs: cd ~/deployment && docker-compose logs -f"
        echo "  - Stop services: ./deploy.sh $ENVIRONMENT --stop"
    fi
else
    echo ""
    echo "╔════════════════════════════════════════════════════════════╗"
    echo "║                    ❌ FAILED                                ║"
    echo "╚════════════════════════════════════════════════════════════╝"
    echo ""
    echo "Check logs above for details"
fi

exit $EXIT_CODE
