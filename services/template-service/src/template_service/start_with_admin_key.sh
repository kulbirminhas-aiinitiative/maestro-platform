#!/bin/bash
###############################################################################
# Central Registry Startup Script with Admin Key
###############################################################################

set -e

cd /home/ec2-user/projects/maestro-templates/services/central_registry

# Set admin key
export ADMIN_KEY="maestro-dev-admin-key-67890"

echo "Starting Central Registry with ADMIN_KEY configured..."
echo "Admin Key: ${ADMIN_KEY:0:15}..."

# Kill any existing registry on port 9600
lsof -ti:9600 | xargs kill -9 2>/dev/null || true
sleep 2

# Start registry
exec poetry run python app.py
