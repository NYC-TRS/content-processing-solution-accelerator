# Implementation Plan: Fix Folders Endpoint to Survive azd up

## Current Status Analysis

### What's Been Done
- Folders endpoint fix is committed (commit bfe5e2d, 2317b9d)
- Frontend fix for token timing is committed (commit 69ec67e)
- Code is in the repository

### Why It's Not Working
- azd up deploys pre-built container images from ACR
- No mechanism exists to build images before azd up runs
- GitHub Actions builds images on push, but user runs azd up immediately
- Default behavior pulls 'latest' tag which may be stale

## Root Cause Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                     THE PROBLEM                              │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Developer Flow:                                             │
│  1. Edit code ✓                                             │
│  2. git commit ✓                                            │
│  3. azd up ✗ <-- Deploys OLD image from ACR                │
│                                                              │
│  What SHOULD happen:                                         │
│  1. Edit code ✓                                             │
│  2. git commit ✓                                            │
│  3. Build new Docker image ✓                                │
│  4. Push image to ACR ✓                                     │
│  5. azd up ✓ <-- Deploys NEW image                         │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

## Solution Architecture

### Recommended Approach: Predeploy Hook

Add a `predeploy` hook to `azure.yaml` that automatically builds and pushes images before deployment.

**Benefits:**
- Fully automated
- Always uses latest source code
- No manual steps
- Integrated with azd workflow
- Works for all team members

**Drawbacks:**
- Slower azd up (adds ~5-10 minutes for builds)
- Requires Docker on deployment machine
- Uses local Docker resources

### Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                   azd up WORKFLOW                            │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  azd up                                                      │
│    │                                                         │
│    ├─▶ [NEW] predeploy hook                                │
│    │     ├─▶ Login to ACR                                  │
│    │     ├─▶ Build contentprocessorapi:latest              │
│    │     ├─▶ Build contentprocessor:latest                 │
│    │     ├─▶ Build contentprocessorweb:latest              │
│    │     └─▶ Push all images to ACR                        │
│    │                                                         │
│    ├─▶ azd provision (Bicep deployment)                    │
│    │     ├─▶ Read infra/main.bicep                         │
│    │     ├─▶ Pull images from ACR (now fresh!)             │
│    │     └─▶ Update Container Apps                         │
│    │                                                         │
│    └─▶ postprovision hook                                  │
│          └─▶ Run post_deployment.sh                        │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

## Step-by-Step Implementation

### Phase 1: Create Build Script (DONE)

File: `/workspaces/content-processing-solution-accelerator/infra/scripts/build_images.sh`

```bash
#!/bin/bash
set -e

# Script that builds and pushes all container images
# Called by azd predeploy hook
```

Status: ✓ Created and made executable

### Phase 2: Update azure.yaml

**Current azure.yaml:**
```yaml
hooks:
  postprovision:
    posix:
      shell: sh
      run: sed -i 's/\r$//' ./infra/scripts/post_deployment.sh; bash ./infra/scripts/post_deployment.sh
      interactive: true
```

**Updated azure.yaml:**
```yaml
hooks:
  predeploy:
    posix:
      shell: sh
      run: |
        echo "Building container images from source..."
        chmod +x ./infra/scripts/build_images.sh
        ./infra/scripts/build_images.sh
      continueOnError: false
      interactive: false
    windows:
      shell: pwsh
      run: ./infra/scripts/build_images.ps1
      continueOnError: false
      interactive: false

  postprovision:
    posix:
      shell: sh
      run: sed -i 's/\r$//' ./infra/scripts/post_deployment.sh; bash ./infra/scripts/post_deployment.sh
      interactive: true
```

### Phase 3: Create Windows Build Script (Optional)

File: `/workspaces/content-processing-solution-accelerator/infra/scripts/build_images.ps1`

```powershell
Write-Host "Building container images from source..." -ForegroundColor Cyan

$registry = if ($env:CONTAINER_REGISTRY_LOGIN_SERVER) {
    $env:CONTAINER_REGISTRY_LOGIN_SERVER
} else {
    "crstg6fsvw.azurecr.io"
}
$registryName = if ($env:CONTAINER_REGISTRY_NAME) {
    $env:CONTAINER_REGISTRY_NAME
} else {
    "crstg6fsvw"
}

Write-Host "Registry: $registry" -ForegroundColor Yellow

# Login to ACR
Write-Host "Logging into Azure Container Registry..." -ForegroundColor Cyan
az acr login --name $registryName

# Get script directory and repo root
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = Split-Path -Parent (Split-Path -Parent $scriptDir)

# Build and push ContentProcessorAPI
Write-Host "`nBuilding ContentProcessorAPI..." -ForegroundColor Cyan
docker build `
  -t "$registry/contentprocessorapi:latest" `
  -f "$repoRoot/src/ContentProcessorAPI/Dockerfile" `
  "$repoRoot/src/ContentProcessorAPI"
docker push "$registry/contentprocessorapi:latest"
Write-Host "✓ ContentProcessorAPI built and pushed" -ForegroundColor Green

# Build and push ContentProcessor
Write-Host "`nBuilding ContentProcessor..." -ForegroundColor Cyan
docker build `
  -t "$registry/contentprocessor:latest" `
  -f "$repoRoot/src/ContentProcessor/Dockerfile" `
  "$repoRoot/src/ContentProcessor"
docker push "$registry/contentprocessor:latest"
Write-Host "✓ ContentProcessor built and pushed" -ForegroundColor Green

# Build and push ContentProcessorWeb
Write-Host "`nBuilding ContentProcessorWeb..." -ForegroundColor Cyan
docker build `
  -t "$registry/contentprocessorweb:latest" `
  -f "$repoRoot/src/ContentProcessorWeb/Dockerfile" `
  "$repoRoot/src/ContentProcessorWeb"
docker push "$registry/contentprocessorweb:latest"
Write-Host "✓ ContentProcessorWeb built and pushed" -ForegroundColor Green

Write-Host "`nAll images built and pushed successfully!" -ForegroundColor Green
```

### Phase 4: Test the Solution

```bash
# 1. Backup current azure.yaml
cp azure.yaml azure.yaml.backup

# 2. Update azure.yaml with predeploy hook
# (Edit file to add predeploy section)

# 3. Test the build script manually
./infra/scripts/build_images.sh

# 4. Verify images in ACR
az acr repository show-tags \
  --name crstg6fsvw \
  --repository contentprocessorapi \
  --orderby time_desc \
  --top 3

# 5. Test full azd up workflow
azd up

# 6. Verify deployment
az containerapp show \
  --name ca-stg6fsvw-api \
  --resource-group msazaidocintstg \
  --query "properties.template.containers[0].image"

# 7. Test folders endpoint
curl https://ca-stg6fsvw-api.blackplant-3f8c2e39.eastus.azurecontainerapps.io/folders/
```

## Alternative Solutions

### Alternative 1: Manual Build Before azd up

**Pros:**
- Simple
- No automation needed
- Fast when you don't need to rebuild

**Cons:**
- Manual process
- Easy to forget
- Not team-friendly

**Implementation:**
```bash
# Create a wrapper script: deploy.sh
#!/bin/bash
./infra/scripts/build_images.sh
azd up
```

### Alternative 2: Use Specific Image Tags

**Pros:**
- Predictable deployments
- Easy rollback
- Production best practice

**Cons:**
- Requires managing versions
- Still need to build images
- Extra complexity

**Implementation:**
```bash
# Build with timestamped tag
TAG="v$(date +%Y%m%d-%H%M%S)"
docker build -t crstg6fsvw.azurecr.io/contentprocessorapi:$TAG \
  -f src/ContentProcessorAPI/Dockerfile src/ContentProcessorAPI
docker push crstg6fsvw.azurecr.io/contentprocessorapi:$TAG

# Set environment variable
azd env set AZURE_ENV_CONTAINER_IMAGE_TAG "$TAG"

# Deploy
azd up
```

### Alternative 3: Rely on GitHub Actions

**Pros:**
- Proper CI/CD
- Audit trail
- Team collaboration

**Cons:**
- Slow (5-10 minutes)
- Requires pushing to git
- Need to wait for build

**Implementation:**
```bash
# Commit and push
git add src/ContentProcessorAPI/app/routers/contentprocessor.py
git commit -m "Fix folders endpoint"
git push origin main

# Wait for GitHub Actions
gh run watch

# Deploy after build completes
azd up
```

## Comparison Matrix

| Solution | Speed | Automation | Reliability | Team-Friendly | Production-Ready |
|----------|-------|------------|-------------|---------------|------------------|
| Predeploy Hook | ⭐⭐⭐ (slower azd up) | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| Manual Build | ⭐⭐⭐⭐ | ⭐ | ⭐⭐ | ⭐⭐ | ⭐⭐ |
| Specific Tags | ⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| GitHub Actions | ⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |

## Recommended Implementation Strategy

### For Development Environment
Use **Predeploy Hook** (Solution above)
- One-time setup
- Always works
- No manual steps
- Perfect for rapid iteration

### For Staging/Production
Use **GitHub Actions + Specific Tags**
- Commit to feature branch
- PR review
- GitHub Actions builds
- Deploy with specific tag version
- Proper audit trail

## Migration Path

### Week 1: Immediate Fix
1. Implement predeploy hook in azure.yaml
2. Test with development environment
3. Verify folders endpoint works after azd up
4. Document for team

### Week 2: Process Improvement
1. Update team documentation
2. Train team on new workflow
3. Add build verification step
4. Create deployment checklist

### Week 3: Production Hardening
1. Implement specific image tagging
2. Add image scanning
3. Create rollback procedures
4. Set up monitoring/alerts

## Success Criteria

- [ ] Folders endpoint works after azd up
- [ ] No manual docker build commands needed
- [ ] All team members can deploy successfully
- [ ] Deployment is repeatable and reliable
- [ ] Clear rollback mechanism exists

## Rollback Plan

If the predeploy hook causes issues:

```bash
# 1. Restore original azure.yaml
cp azure.yaml.backup azure.yaml

# 2. Build images manually
./infra/scripts/build_images.sh

# 3. Deploy
azd up

# 4. Investigate and fix hook issues
```

## Next Steps

1. Review this implementation plan
2. Get approval for predeploy hook approach
3. Update azure.yaml
4. Test in development
5. Document in team wiki
6. Roll out to team

## Questions to Answer

1. Do we want predeploy builds for all environments?
2. Should we add build caching to speed up builds?
3. Do we need multi-architecture images (ARM64, AMD64)?
4. Should we implement image tagging strategy now or later?
5. Do we need to update CI/CD pipelines as well?

## Additional Enhancements

### Enhancement 1: Build Cache
Speed up builds by using Docker BuildKit cache:

```bash
export DOCKER_BUILDKIT=1
export BUILDKIT_PROGRESS=plain
docker build --cache-from ... --build-arg BUILDKIT_INLINE_CACHE=1 ...
```

### Enhancement 2: Parallel Builds
Build all images in parallel:

```bash
docker build ... contentprocessorapi:latest &
docker build ... contentprocessor:latest &
docker build ... contentprocessorweb:latest &
wait
```

### Enhancement 3: Build Verification
Add health checks after deployment:

```bash
# After azd up
./infra/scripts/verify_deployment.sh
```

### Enhancement 4: Conditional Builds
Only build images that have changed:

```bash
# Check if code changed since last build
if git diff --quiet HEAD^ HEAD -- src/ContentProcessorAPI/; then
  echo "No changes in API, skipping build"
else
  docker build ... contentprocessorapi:latest
fi
```

## Conclusion

The predeploy hook approach provides the best balance of automation, reliability, and ease of use. It solves the core problem (fixes not surviving azd up) while requiring minimal changes to the existing workflow.

**Estimated effort:**
- Setup: 1 hour
- Testing: 2 hours
- Documentation: 1 hour
- Total: 4 hours

**Impact:**
- Zero manual steps for deployments
- Fixes always survive azd up
- Team-friendly workflow
- Production-ready solution
