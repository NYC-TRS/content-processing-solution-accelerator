# Comprehensive Strategy: Fix Folders Endpoint to Survive azd up

## Executive Summary

The folders endpoint fix keeps getting overwritten when running `azd up` because:
1. **azd up does NOT build container images from source code**
2. **azd up pulls pre-built images from Azure Container Registry (ACR)**
3. **The Bicep template uses the `latest` tag by default**
4. **GitHub Actions builds and pushes images on every push to main/dev branches**

**Root Cause:** Code changes committed to the repository do NOT automatically trigger new container image builds. When you run `azd up`, it deploys whatever image has the `latest` tag in ACR, which may be an older version without your fixes.

## Current Architecture Analysis

### How azd up Works

```
azd up workflow:
1. Read azure.yaml (no services defined - infrastructure only)
2. Read infra/main.parameters.json
3. Replace parameter placeholders with environment variables
4. Deploy Bicep template (infra/main.bicep)
5. Bicep pulls container images from ACR using:
   - publicContainerImageEndpoint = 'crstg6fsvw.azurecr.io'
   - imageTag = 'latest' (default)
6. Run postprovision hook (post_deployment.sh)
```

### Current Image Build Process

```
GitHub Actions (.github/workflows/build-docker-image.yml):
- Triggers: push to main, dev, demo, hotfix branches
- Builds Docker images from source code
- Pushes to ACR with tags:
  - latest (for main branch)
  - dev (for dev branch)
  - {branch}_{date}_{run_number}
```

### Why Fixes Don't Survive

```
Timeline:
1. You commit code fix to main branch ✓
2. GitHub Actions builds new image and pushes to ACR as 'latest' ✓
3. User runs 'azd up' BEFORE GitHub Actions completes ✗
   OR
3. User runs 'azd up' and Bicep uses cached/old 'latest' tag ✗
   OR
3. GitHub Actions hasn't run yet (manual local commit) ✗

Result: Container Apps get deployed with OLD image
```

## Comprehensive Solution Strategy

### Solution 1: Ensure Code is Committed and Built (RECOMMENDED)

This is the proper production approach that ensures version control and audit trail.

#### Step 1: Commit All Fixes to Git

```bash
# Ensure folders endpoint fix is committed
git add src/ContentProcessorAPI/app/routers/contentprocessor.py
git commit -m "Fix folders endpoint: Add CosmosMongDBHelper integration

- Import CosmosMongDBHelper for database access
- Add proper error handling and logging
- Filter out None values from folder results
- Support optional schema_id filtering"
```

#### Step 2: Push to Trigger GitHub Actions

```bash
# Push to main branch to trigger image build
git push origin main

# Wait for GitHub Actions to complete
# Monitor at: https://github.com/{org}/{repo}/actions
```

#### Step 3: Verify Image Build Completion

```bash
# Wait for GitHub Actions workflow to complete (typically 5-10 minutes)
# Check that new image is pushed to ACR

az acr repository show-tags \
  --name crstg6fsvw \
  --repository contentprocessorapi \
  --orderby time_desc \
  --top 5
```

#### Step 4: Run azd up

```bash
# Now deploy with the new image
azd up

# The Bicep template will pull the 'latest' tag which now contains your fix
```

#### Step 5: Verify Deployment

```bash
# Check the deployed container app revision
az containerapp revision list \
  --name ca-stg6fsvw-api \
  --resource-group msazaidocintstg \
  --query "[0].{name:name,created:properties.createdTime,image:properties.template.containers[0].image}"

# Test the folders endpoint
curl https://ca-stg6fsvw-api.blackplant-3f8c2e39.eastus.azurecontainerapps.io/folders/
```

### Solution 2: Use Specific Image Tags (PRODUCTION BEST PRACTICE)

Instead of using `latest`, use specific dated tags for predictable deployments.

#### Step 1: Set Environment Variable for Image Tag

```bash
# After GitHub Actions completes, use the dated tag
# Example: latest_2025-11-26_123

azd env set AZURE_ENV_CONTAINER_IMAGE_TAG "latest_2025-11-26_123"
```

#### Step 2: Update main.parameters.json (if needed)

The parameter file already supports this:
```json
"imageTag": {
  "value": "${AZURE_ENV_CONTAINER_IMAGE_TAG}"
}
```

#### Step 3: Deploy with Specific Tag

```bash
azd up
# This will deploy the exact image version you specified
```

### Solution 3: Build and Push Images Manually

For rapid development/testing when you need immediate feedback.

#### Step 1: Login to ACR

```bash
az acr login --name crstg6fsvw
```

#### Step 2: Build and Push API Image

```bash
# From repository root
cd /workspaces/content-processing-solution-accelerator

# Build the API image
docker build -t crstg6fsvw.azurecr.io/contentprocessorapi:latest \
  -f src/ContentProcessorAPI/Dockerfile \
  src/ContentProcessorAPI

# Push to ACR
docker push crstg6fsvw.azurecr.io/contentprocessorapi:latest
```

#### Step 3: Deploy with azd up

```bash
azd up
# Will now use the manually built image
```

### Solution 4: Add predeploy Hook to azure.yaml

Automate image building as part of azd up workflow.

#### Step 1: Update azure.yaml

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
        set -e
        echo "Building and pushing container images..."

        # Login to ACR
        az acr login --name ${CONTAINER_REGISTRY_NAME}

        # Build and push ContentProcessorAPI
        docker build -t ${CONTAINER_REGISTRY_LOGIN_SERVER}/contentprocessorapi:latest \
          -f src/ContentProcessorAPI/Dockerfile \
          src/ContentProcessorAPI
        docker push ${CONTAINER_REGISTRY_LOGIN_SERVER}/contentprocessorapi:latest

        # Build and push ContentProcessor
        docker build -t ${CONTAINER_REGISTRY_LOGIN_SERVER}/contentprocessor:latest \
          -f src/ContentProcessor/Dockerfile \
          src/ContentProcessor
        docker push ${CONTAINER_REGISTRY_LOGIN_SERVER}/contentprocessor:latest

        # Build and push ContentProcessorWeb
        docker build -t ${CONTAINER_REGISTRY_LOGIN_SERVER}/contentprocessorweb:latest \
          -f src/ContentProcessorWeb/Dockerfile \
          src/ContentProcessorWeb
        docker push ${CONTAINER_REGISTRY_LOGIN_SERVER}/contentprocessorweb:latest

        echo "✓ All images built and pushed successfully"
      continueOnError: false
    windows:
      shell: pwsh
      run: |
        Write-Host "Building and pushing container images..."

        # Login to ACR
        az acr login --name $env:CONTAINER_REGISTRY_NAME

        # Build and push images (similar to posix version)
        docker build -t "$env:CONTAINER_REGISTRY_LOGIN_SERVER/contentprocessorapi:latest" -f src/ContentProcessorAPI/Dockerfile src/ContentProcessorAPI
        docker push "$env:CONTAINER_REGISTRY_LOGIN_SERVER/contentprocessorapi:latest"

        docker build -t "$env:CONTAINER_REGISTRY_LOGIN_SERVER/contentprocessor:latest" -f src/ContentProcessor/Dockerfile src/ContentProcessor
        docker push "$env:CONTAINER_REGISTRY_LOGIN_SERVER/contentprocessor:latest"

        docker build -t "$env:CONTAINER_REGISTRY_LOGIN_SERVER/contentprocessorweb:latest" -f src/ContentProcessorWeb/Dockerfile src/ContentProcessorWeb
        docker push "$env:CONTAINER_REGISTRY_LOGIN_SERVER/contentprocessorweb:latest"

        Write-Host "✓ All images built and pushed successfully"
      continueOnError: false

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

#### Step 2: Deploy

```bash
azd up
# Will automatically build images before deploying
```

## Verification Steps

### After Any Deployment

```bash
# 1. Check Container App revision
az containerapp revision list \
  --name ca-stg6fsvw-api \
  --resource-group msazaidocintstg \
  --output table

# 2. Get the image being used
az containerapp show \
  --name ca-stg6fsvw-api \
  --resource-group msazaidocintstg \
  --query "properties.template.containers[0].image" \
  -o tsv

# 3. Test the folders endpoint
curl -X GET "https://ca-stg6fsvw-api.blackplant-3f8c2e39.eastus.azurecontainerapps.io/folders/" \
  -H "Authorization: Bearer YOUR_TOKEN"

# 4. Check logs for errors
az containerapp logs show \
  --name ca-stg6fsvw-api \
  --resource-group msazaidocintstg \
  --follow
```

### Verify Code is in Running Container

```bash
# Connect to container and verify code
az containerapp exec \
  --name ca-stg6fsvw-api \
  --resource-group msazaidocintstg \
  --command /bin/bash

# Inside container:
grep -A10 "async def get_folders" /app/app/routers/contentprocessor.py
```

## Recommended Workflow

### For Development (Rapid Iteration)

```bash
# 1. Make code changes
# 2. Build and push manually (Solution 3)
docker build -t crstg6fsvw.azurecr.io/contentprocessorapi:dev-$(date +%s) \
  -f src/ContentProcessorAPI/Dockerfile src/ContentProcessorAPI
docker push crstg6fsvw.azurecr.io/contentprocessorapi:dev-$(date +%s)

# 3. Update running container without full azd up
az containerapp update \
  --name ca-stg6fsvw-api \
  --resource-group msazaidocintstg \
  --image crstg6fsvw.azurecr.io/contentprocessorapi:dev-$(date +%s)
```

### For Production (Proper CI/CD)

```bash
# 1. Make code changes
# 2. Commit to feature branch
git checkout -b fix/folders-endpoint
git add src/ContentProcessorAPI/app/routers/contentprocessor.py
git commit -m "Fix folders endpoint"
git push origin fix/folders-endpoint

# 3. Create PR and merge to main after review
# 4. Wait for GitHub Actions to build images
# 5. Deploy with specific tag
azd env set AZURE_ENV_CONTAINER_IMAGE_TAG "latest_2025-11-26_123"
azd up
```

### For Emergency Hotfixes

```bash
# 1. Fix code locally
# 2. Build and push with hotfix tag
docker build -t crstg6fsvw.azurecr.io/contentprocessorapi:hotfix-folders \
  -f src/ContentProcessorAPI/Dockerfile src/ContentProcessorAPI
docker push crstg6fsvw.azurecr.io/contentprocessorapi:hotfix-folders

# 3. Update Container App directly
az containerapp update \
  --name ca-stg6fsvw-api \
  --resource-group msazaidocintstg \
  --image crstg6fsvw.azurecr.io/contentprocessorapi:hotfix-folders

# 4. Commit to git and create PR for proper fix
```

## Why Each Solution Works

### Solution 1 (Commit + GitHub Actions)
- ✅ Proper version control
- ✅ Audit trail
- ✅ Repeatable
- ✅ Production-ready
- ⚠️ Takes 5-10 minutes for build
- ⚠️ Requires waiting for CI/CD

### Solution 2 (Specific Tags)
- ✅ Predictable deployments
- ✅ Easy rollback
- ✅ No surprise updates
- ✅ Production best practice
- ⚠️ Requires managing tag versions

### Solution 3 (Manual Build)
- ✅ Immediate feedback
- ✅ Fast iteration
- ⚠️ Manual process
- ⚠️ No audit trail
- ⚠️ Only for development

### Solution 4 (predeploy Hook)
- ✅ Automated
- ✅ Always uses latest code
- ✅ Part of azd workflow
- ⚠️ Slower deployments
- ⚠️ Requires Docker on deployment machine

## Common Pitfalls to Avoid

### Pitfall 1: Assuming azd up Builds from Source
**Problem:** azd up does NOT build containers by default
**Solution:** Use Solution 4 (predeploy hook) or build manually

### Pitfall 2: Not Waiting for GitHub Actions
**Problem:** Running azd up before new image is pushed
**Solution:** Wait for GitHub Actions to complete, or use specific tags

### Pitfall 3: Using 'latest' Tag in Production
**Problem:** Unpredictable which version deploys
**Solution:** Use specific dated tags (Solution 2)

### Pitfall 4: Committing Without Pushing
**Problem:** Local commits don't trigger builds
**Solution:** Always push to trigger GitHub Actions

### Pitfall 5: Wrong Branch
**Problem:** Pushing to non-main branch doesn't build 'latest' tag
**Solution:** Ensure you push to main (or update workflow to build from your branch)

## File Checklist: What to Commit

```bash
# Essential files that must be committed for fix to persist:
✓ src/ContentProcessorAPI/app/routers/contentprocessor.py (folders endpoint)
✓ src/ContentProcessorAPI/Dockerfile (if modified)
✓ src/ContentProcessorAPI/pyproject.toml (if dependencies added)
✓ src/ContentProcessorAPI/uv.lock (if dependencies changed)

# Infrastructure files (optional, only if changing deployment):
○ azure.yaml (if adding predeploy hook)
○ infra/main.bicep (if changing container config)
○ infra/main.parameters.json (if adding new parameters)
```

## Testing the Full Workflow

```bash
# Test Script: Verify Fix Survives azd up
#!/bin/bash
set -e

echo "Step 1: Verify code is committed"
git diff --exit-code src/ContentProcessorAPI/app/routers/contentprocessor.py || {
  echo "ERROR: contentprocessor.py has uncommitted changes"
  exit 1
}

echo "Step 2: Push to trigger build"
git push origin main

echo "Step 3: Wait for GitHub Actions"
gh run watch

echo "Step 4: Verify new image exists"
az acr repository show-tags \
  --name crstg6fsvw \
  --repository contentprocessorapi \
  --orderby time_desc \
  --top 1

echo "Step 5: Deploy with azd"
azd up

echo "Step 6: Test folders endpoint"
RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" \
  https://ca-stg6fsvw-api.blackplant-3f8c2e39.eastus.azurecontainerapps.io/folders/)

if [ "$RESPONSE" = "200" ]; then
  echo "✓ SUCCESS: Folders endpoint is working!"
else
  echo "✗ FAILED: Folders endpoint returned $RESPONSE"
  exit 1
fi
```

## Quick Reference Commands

```bash
# Check current deployed image
az containerapp show -n ca-stg6fsvw-api -g msazaidocintstg \
  --query "properties.template.containers[0].image"

# List available images in ACR
az acr repository show-tags -n crstg6fsvw --repository contentprocessorapi

# Build and push manually
az acr login -n crstg6fsvw
docker build -t crstg6fsvw.azurecr.io/contentprocessorapi:latest \
  -f src/ContentProcessorAPI/Dockerfile src/ContentProcessorAPI
docker push crstg6fsvw.azurecr.io/contentprocessorapi:latest

# Update container app with specific image
az containerapp update -n ca-stg6fsvw-api -g msazaidocintstg \
  --image crstg6fsvw.azurecr.io/contentprocessorapi:SPECIFIC_TAG

# View container logs
az containerapp logs show -n ca-stg6fsvw-api -g msazaidocintstg --follow

# List container revisions
az containerapp revision list -n ca-stg6fsvw-api -g msazaidocintstg -o table
```

## Conclusion

**The fix will survive `azd up` if and only if:**

1. ✓ Code changes are committed to git
2. ✓ Changes are pushed to main branch
3. ✓ GitHub Actions successfully builds and pushes new image
4. ✓ You wait for GitHub Actions to complete before running `azd up`
5. ✓ OR you manually build and push the image
6. ✓ OR you add a predeploy hook to build automatically

**Recommended approach for your use case:**
- **Development:** Solution 3 (Manual build) for quick iteration
- **Production:** Solution 1 (GitHub Actions) + Solution 2 (Specific tags)
- **Automation:** Solution 4 (predeploy hook) to never worry about it

The root cause is simple: **azd up deploys container images, not source code.** Ensure your images contain your fixes before deploying.
