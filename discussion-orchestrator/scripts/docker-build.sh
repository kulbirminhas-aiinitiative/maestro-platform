#!/bin/bash
set -e

# Docker Build Script for Discussion Orchestrator
# This script builds and optionally pushes the Docker image

echo "========================================="
echo "Docker Build - Discussion Orchestrator"
echo "========================================="

# Navigate to the project directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# Default values
IMAGE_NAME="discussion-orchestrator"
TAG="${1:-latest}"
PUSH="${2:-false}"

echo "Image: $IMAGE_NAME:$TAG"
echo "Push to registry: $PUSH"
echo ""

# Build the image
echo "Building Docker image..."
cd "$PROJECT_DIR"
docker build -t "$IMAGE_NAME:$TAG" .

echo ""
echo "✓ Build completed successfully"
echo ""

# Tag with additional tags if specified
if [ "$TAG" != "latest" ]; then
    echo "Tagging as latest..."
    docker tag "$IMAGE_NAME:$TAG" "$IMAGE_NAME:latest"
fi

# Push to registry if requested
if [ "$PUSH" = "true" ] || [ "$PUSH" = "yes" ] || [ "$PUSH" = "1" ]; then
    echo "Pushing to registry..."
    docker push "$IMAGE_NAME:$TAG"

    if [ "$TAG" != "latest" ]; then
        docker push "$IMAGE_NAME:latest"
    fi

    echo "✓ Push completed successfully"
fi

echo ""
echo "========================================="
echo "Docker image ready: $IMAGE_NAME:$TAG"
echo ""
echo "To run the image:"
echo "  docker run -p 5000:5000 --env-file .env $IMAGE_NAME:$TAG"
echo ""
echo "To run with docker-compose:"
echo "  docker-compose up -d"
echo "========================================="
