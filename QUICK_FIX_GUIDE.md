# Quick Fix Guide: Make Folders Endpoint Survive azd up

## TL;DR - The Problem

When you run `azd up`, it deploys pre-built container images from Azure Container Registry, NOT your local source code. If your code changes haven't been built into new images, they won't be deployed.

## The Fix (Choose ONE)

### Option A: Quick Manual Fix (5 minutes)

```bash
# 1. Login to container registry
az acr login --name crstg6fsvw

# 2. Build and push the API image with your fixes
docker build -t crstg6fsvw.azurecr.io/contentprocessorapi:latest \
  -f src/ContentProcessorAPI/Dockerfile \
  src/ContentProcessorAPI

docker push crstg6fsvw.azurecr.io/contentprocessorapi:latest

# 3. Update the running container (skip full azd up)
az containerapp update \
  --name ca-stg6fsvw-api \
  --resource-group msazaidocintstg \
  --image crstg6fsvw.azurecr.io/contentprocessorapi:latest

# 4. Verify it's working
curl https://ca-stg6fsvw-api.blackplant-3f8c2e39.eastus.azurecontainerapps.io/folders/
```

### Option B: Proper Git Workflow (10-15 minutes)

```bash
# 1. Commit your fixes
git add src/ContentProcessorAPI/app/routers/contentprocessor.py
git commit -m "Fix folders endpoint"
git push origin main

# 2. Wait for GitHub Actions to build (~5-10 minutes)
# Monitor: https://github.com/{your-org}/{your-repo}/actions

# 3. Verify new image is ready
az acr repository show-tags \
  --name crstg6fsvw \
  --repository contentprocessorapi \
  --orderby time_desc \
  --top 3

# 4. Now run azd up
azd up
```

### Option C: Automated Build (One-time setup)

Add a predeploy hook to azure.yaml so it always builds before deploying.

**Create a new file:** `/workspaces/content-processing-solution-accelerator/infra/scripts/build_images.sh`

```bash
#!/bin/bash
set -e

echo "=========================================="
echo "Building container images from source..."
echo "=========================================="

# Get environment variables
REGISTRY="${CONTAINER_REGISTRY_LOGIN_SERVER:-crstg6fsvw.azurecr.io}"

# Login to ACR
echo "Logging into Azure Container Registry..."
az acr login --name "${CONTAINER_REGISTRY_NAME:-crstg6fsvw}"

# Build and push ContentProcessorAPI
echo ""
echo "Building ContentProcessorAPI..."
docker build -t "${REGISTRY}/contentprocessorapi:latest" \
  -f src/ContentProcessorAPI/Dockerfile \
  src/ContentProcessorAPI
docker push "${REGISTRY}/contentprocessorapi:latest"
echo "✓ ContentProcessorAPI pushed"

# Build and push ContentProcessor
echo ""
echo "Building ContentProcessor..."
docker build -t "${REGISTRY}/contentprocessor:latest" \
  -f src/ContentProcessor/Dockerfile \
  src/ContentProcessor
docker push "${REGISTRY}/contentprocessor:latest"
echo "✓ ContentProcessor pushed"

# Build and push ContentProcessorWeb
echo ""
echo "Building ContentProcessorWeb..."
docker build -t "${REGISTRY}/contentprocessorweb:latest" \
  -f src/ContentProcessorWeb/Dockerfile \
  src/ContentProcessorWeb
docker push "${REGISTRY}/contentprocessorweb:latest"
echo "✓ ContentProcessorWeb pushed"

echo ""
echo "=========================================="
echo "All images built and pushed successfully!"
echo "=========================================="
```

**Update azure.yaml:**

```yaml
name: content-processing

requiredVersions:
  azd: '>= 1.18.0'

metadata:
  template: content-processing@1.0
  name: content-processinge@1.0

hooks:
  predeploy:
    posix:
      shell: sh
      run: |
        chmod +x ./infra/scripts/build_images.sh
        ./infra/scripts/build_images.sh
      continueOnError: false
      interactive: false
    windows:
      shell: pwsh
      run: |
        Write-Host "Building and pushing container images..." -ForegroundColor Cyan
        $registry = if ($env:CONTAINER_REGISTRY_LOGIN_SERVER) { $env:CONTAINER_REGISTRY_LOGIN_SERVER } else { "crstg6fsvw.azurecr.io" }
        $registryName = if ($env:CONTAINER_REGISTRY_NAME) { $env:CONTAINER_REGISTRY_NAME } else { "crstg6fsvw" }

        az acr login --name $registryName

        docker build -t "$registry/contentprocessorapi:latest" -f src/ContentProcessorAPI/Dockerfile src/ContentProcessorAPI
        docker push "$registry/contentprocessorapi:latest"

        docker build -t "$registry/contentprocessor:latest" -f src/ContentProcessor/Dockerfile src/ContentProcessor
        docker push "$registry/contentprocessor:latest"

        docker build -t "$registry/contentprocessorweb:latest" -f src/ContentProcessorWeb/Dockerfile src/ContentProcessorWeb
        docker push "$registry/contentprocessorweb:latest"

        Write-Host "All images built and pushed successfully!" -ForegroundColor Green
      continueOnError: false
      interactive: false

  postprovision:
    posix:
      shell: sh
      run: sed -i 's/\r$//' ./infra/scripts/post_deployment.sh; bash ./infra/scripts/post_deployment.sh
      interactive: true
    windows:
      shell: pwsh
      run: ./infra/scripts/post_deployment.ps1
      interactive: true
```

**Then just run:**

```bash
azd up
# It will automatically build images from your current source code
```

## Verification

After deploying, verify the fix is working:

```bash
# Check the deployed image
az containerapp show \
  --name ca-stg6fsvw-api \
  --resource-group msazaidocintstg \
  --query "properties.template.containers[0].image" \
  -o tsv

# Test the endpoint
curl -X GET "https://ca-stg6fsvw-api.blackplant-3f8c2e39.eastus.azurecontainerapps.io/folders/" \
  -H "Authorization: Bearer YOUR_TOKEN"

# Check logs
az containerapp logs show \
  --name ca-stg6fsvw-api \
  --resource-group msazaidocintstg \
  --follow
```

## Why This Happens

```
Your Workflow:
1. Edit code ✓
2. Commit code ✓
3. Run azd up ✗ (deploys OLD image)

Correct Workflow:
1. Edit code ✓
2. Commit code ✓
3. Build new image ✓
4. Run azd up ✓ (deploys NEW image)
```

**Key Point:** `azd up` deploys container images, not source code. You must build new images when code changes.

## Recommendations

- **For rapid development:** Use Option A (manual build)
- **For team collaboration:** Use Option B (GitHub Actions)
- **For convenience:** Use Option C (automated predeploy hook)

## Common Issues

### Issue: "unauthorized: authentication required"
```bash
# Solution: Login to ACR
az acr login --name crstg6fsvw
```

### Issue: "Cannot connect to the Docker daemon"
```bash
# Solution: Start Docker
sudo systemctl start docker
# Or on Mac/Windows: Start Docker Desktop
```

### Issue: azd up still uses old image
```bash
# Solution: Force revision update
az containerapp revision list \
  --name ca-stg6fsvw-api \
  --resource-group msazaidocintstg \
  --output table

# Deactivate old revisions
az containerapp revision deactivate \
  --name ca-stg6fsvw-api \
  --resource-group msazaidocintstg \
  --revision OLD_REVISION_NAME
```

### Issue: Build is slow
```bash
# Solution: Use Docker BuildKit for faster builds
export DOCKER_BUILDKIT=1
docker build ...
```

## Need Help?

See the comprehensive guide: `FOLDERS_FIX_STRATEGY.md`
