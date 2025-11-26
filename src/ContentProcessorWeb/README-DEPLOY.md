# Deployment Guide

## Quick Deploy (One Command)

To deploy your changes to Azure:

```bash
make deploy
```

This will:
1. Login to Azure Container Registry
2. Build Docker image with timestamp tag
3. Push to registry
4. Update container app with new image

## Other Commands

```bash
make build       # Build Docker image only
make push        # Push to registry
make update-app  # Update container app
make clean       # Remove old local images
make help        # Show all commands
```

## Manual Deployment (if needed)

If you prefer manual steps:

```bash
# 1. Login
az acr login --name crstg6fsvw

# 2. Build
docker build -t crstg6fsvw.azurecr.io/content-processor-web:$(date +%s) .

# 3. Push  
docker push crstg6fsvw.azurecr.io/content-processor-web:$(date +%s)

# 4. Update
az containerapp update --name ca-stg6fsvw-web \
  --resource-group msazaidocintstg \
  --image crstg6fsvw.azurecr.io/content-processor-web:TIMESTAMP
```

## Notes

- Always use timestamped tags (not just `:latest`) to force Azure to pull new images
- The Makefile automatically generates unique timestamps for each build
- Use incognito/private browsing to avoid browser caching
