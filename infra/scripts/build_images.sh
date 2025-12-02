#!/bin/bash
set -e

echo "=========================================="
echo "Building container images from source..."
echo "=========================================="

# Get environment variables from azd
REGISTRY="${CONTAINER_REGISTRY_LOGIN_SERVER:-crstg6fsvw.azurecr.io}"
REGISTRY_NAME="${CONTAINER_REGISTRY_NAME:-crstg6fsvw}"

# Get the repository root (two levels up from this script)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

echo "Repository root: $REPO_ROOT"
echo "Registry: $REGISTRY"
echo ""

# Login to ACR
echo "Logging into Azure Container Registry..."
az acr login --name "$REGISTRY_NAME"
echo "✓ Logged in successfully"
echo ""

# Build and push ContentProcessorAPI
echo "Building ContentProcessorAPI..."
docker build \
  -t "${REGISTRY}/contentprocessorapi:latest" \
  -f "$REPO_ROOT/src/ContentProcessorAPI/Dockerfile" \
  "$REPO_ROOT/src/ContentProcessorAPI"
echo "Pushing ContentProcessorAPI..."
docker push "${REGISTRY}/contentprocessorapi:latest"
echo "✓ ContentProcessorAPI built and pushed"
echo ""

# Build and push ContentProcessor
echo "Building ContentProcessor..."
docker build \
  -t "${REGISTRY}/contentprocessor:latest" \
  -f "$REPO_ROOT/src/ContentProcessor/Dockerfile" \
  "$REPO_ROOT/src/ContentProcessor"
echo "Pushing ContentProcessor..."
docker push "${REGISTRY}/contentprocessor:latest"
echo "✓ ContentProcessor built and pushed"
echo ""

# Build and push ContentProcessorWeb
echo "Building ContentProcessorWeb..."
docker build \
  -t "${REGISTRY}/contentprocessorweb:latest" \
  -f "$REPO_ROOT/src/ContentProcessorWeb/Dockerfile" \
  "$REPO_ROOT/src/ContentProcessorWeb"
echo "Pushing ContentProcessorWeb..."
docker push "${REGISTRY}/contentprocessorweb:latest"
echo "✓ ContentProcessorWeb built and pushed"
echo ""

echo "=========================================="
echo "All images built and pushed successfully!"
echo "=========================================="
echo ""
echo "Images available:"
echo "  - ${REGISTRY}/contentprocessorapi:latest"
echo "  - ${REGISTRY}/contentprocessor:latest"
echo "  - ${REGISTRY}/contentprocessorweb:latest"
echo ""
