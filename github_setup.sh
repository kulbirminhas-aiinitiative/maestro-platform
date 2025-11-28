#!/bin/bash
# GitHub Packages Setup for maestro-shared

GITHUB_ORG="kulbirminhas-aiinitiative"
GITHUB_USERNAME="kulbirminhas-aiinitiative"
GITHUB_TOKEN=$(gh auth token)

echo "Configuring Poetry for GitHub Packages..."

# Configure Poetry repository
poetry config repositories.maestro-shared "https://github.com/$GITHUB_ORG/maestro-shared"

# Configure authentication
poetry config http-basic.maestro-shared $GITHUB_USERNAME $GITHUB_TOKEN

echo "✅ Poetry configured for GitHub Packages"
echo ""
echo "Repository: https://github.com/$GITHUB_ORG/maestro-shared"
echo "Username: $GITHUB_USERNAME"
echo "Token: ${GITHUB_TOKEN:0:10}..."

# Verify configuration
echo ""
echo "Configuration check:"
poetry config --list | grep maestro-shared
