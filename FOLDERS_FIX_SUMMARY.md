# Folders Fix Summary: Why It Doesn't Survive azd up

## The Problem in One Sentence

**azd up deploys pre-built container images from Azure Container Registry, NOT your local source code.**

## Root Cause Explained

```
What You Think Happens:
┌──────────────────────────────────────────────┐
│ 1. Edit code                                  │
│ 2. git commit                                 │
│ 3. azd up  ──▶  Deploys your code changes   │
└──────────────────────────────────────────────┘

What Actually Happens:
┌──────────────────────────────────────────────┐
│ 1. Edit code                                  │
│ 2. git commit                                 │
│ 3. azd up  ──▶  Pulls image from ACR         │
│              ──▶  Image is OLD (no changes)  │
│              ──▶  Deploys OLD code           │
└──────────────────────────────────────────────┘
```

## The Deployment Flow

```
azd up workflow:
┌─────────────────────────────────────────────────────────┐
│                                                         │
│  azd up                                                 │
│    │                                                    │
│    ├─▶ Read infra/main.bicep                          │
│    │                                                    │
│    ├─▶ Look for publicContainerImageEndpoint           │
│    │   = 'crstg6fsvw.azurecr.io'                      │
│    │                                                    │
│    ├─▶ Look for imageTag                              │
│    │   = 'latest'                                      │
│    │                                                    │
│    ├─▶ Pull images from ACR:                          │
│    │   - crstg6fsvw.azurecr.io/contentprocessorapi:latest │
│    │   - crstg6fsvw.azurecr.io/contentprocessor:latest    │
│    │   - crstg6fsvw.azurecr.io/contentprocessorweb:latest │
│    │                                                    │
│    └─▶ Update Container Apps with these images        │
│                                                         │
│  NO SOURCE CODE IS USED AT THIS STAGE                 │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

## When Images Get Built

Images are built by GitHub Actions:

```
GitHub Actions (.github/workflows/build-docker-image.yml):
┌─────────────────────────────────────────────────────────┐
│                                                         │
│  Triggers:                                              │
│  - Push to main branch                                  │
│  - Push to dev branch                                   │
│  - Pull request                                         │
│                                                         │
│  Actions:                                               │
│  1. Checkout source code                                │
│  2. Build Docker images from Dockerfiles                │
│  3. Push to ACR with tags:                             │
│     - latest (for main branch)                         │
│     - dev (for dev branch)                             │
│     - {branch}_{date}_{run_number}                     │
│                                                         │
│  Time: 5-10 minutes                                     │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

## Why Your Fixes Disappear

```
Timeline:

10:00 AM  │ You fix the code
10:01 AM  │ git commit -m "Fix folders endpoint"
10:02 AM  │ git push origin main
          │   ├─▶ GitHub Actions STARTS building image
          │
10:03 AM  │ You run: azd up
          │   ├─▶ Pulls 'latest' from ACR
          │   ├─▶ 'latest' is still THE OLD IMAGE
          │   └─▶ Deploys OLD code
          │
10:07 AM  │ GitHub Actions FINISHES building
          │   └─▶ Pushes NEW image as 'latest'
          │
Result: You deployed the OLD image!
```

## The Solution: 3 Options

### Option 1: Wait for GitHub Actions (Safest)

```bash
# 1. Push your code
git push origin main

# 2. Wait for GitHub Actions to complete (~5-10 min)
gh run watch

# 3. NOW run azd up
azd up
```

### Option 2: Manual Build (Fastest for dev)

```bash
# 1. Login to ACR
az acr login --name crstg6fsvw

# 2. Build and push
docker build -t crstg6fsvw.azurecr.io/contentprocessorapi:latest \
  -f src/ContentProcessorAPI/Dockerfile \
  src/ContentProcessorAPI
docker push crstg6fsvw.azurecr.io/contentprocessorapi:latest

# 3. Deploy
azd up
```

### Option 3: Add predeploy Hook (Best long-term)

Update `azure.yaml` to build images automatically:

```yaml
hooks:
  predeploy:
    posix:
      shell: sh
      run: ./infra/scripts/build_images.sh
```

Then just run:
```bash
azd up  # Automatically builds images first
```

## Key Files

### Source Code
- `/workspaces/content-processing-solution-accelerator/src/ContentProcessorAPI/app/routers/contentprocessor.py`
  - Contains the folders endpoint fix

### Infrastructure
- `/workspaces/content-processing-solution-accelerator/infra/main.bicep`
  - Lines 60-64: Defines which registry and tag to use
  - Line 728: `image: '${publicContainerImageEndpoint}/contentprocessor:${imageTag}'`
  - Line 782: `image: '${publicContainerImageEndpoint}/contentprocessorapi:${imageTag}'`
  - Line 917: `image: '${publicContainerImageEndpoint}/contentprocessorweb:${imageTag}'`

### Configuration
- `/workspaces/content-processing-solution-accelerator/azure.yaml`
  - Controls azd up behavior
  - Can add predeploy hooks here

### CI/CD
- `/workspaces/content-processing-solution-accelerator/.github/workflows/build-docker-image.yml`
  - Builds images on git push

## Quick Commands

```bash
# Check what image is currently deployed
az containerapp show \
  --name ca-stg6fsvw-api \
  --resource-group msazaidocintstg \
  --query "properties.template.containers[0].image" \
  -o tsv

# Check available images in ACR
az acr repository show-tags \
  --name crstg6fsvw \
  --repository contentprocessorapi \
  --orderby time_desc \
  --top 5

# Test the folders endpoint
curl https://ca-stg6fsvw-api.blackplant-3f8c2e39.eastus.azurecontainerapps.io/folders/

# View container logs
az containerapp logs show \
  --name ca-stg6fsvw-api \
  --resource-group msazaidocintstg \
  --follow
```

## The Fix That Works

**RECOMMENDED APPROACH:**

1. Create `/workspaces/content-processing-solution-accelerator/infra/scripts/build_images.sh` (DONE)
2. Update `/workspaces/content-processing-solution-accelerator/azure.yaml` to add predeploy hook
3. Run `azd up` - it will now build images automatically

**Updated azure.yaml:**
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
      run: ./infra/scripts/build_images.ps1
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

## What to Commit

```bash
# Commit these files:
git add infra/scripts/build_images.sh
git add infra/scripts/build_images.ps1
git add azure.yaml

git commit -m "Add predeploy hook to build images before azd up

This ensures that azd up always deploys the latest source code
by building container images before deployment."

git push origin main
```

## Verification

After implementing and running `azd up`:

```bash
# 1. Check the deployed image timestamp
az containerapp revision list \
  --name ca-stg6fsvw-api \
  --resource-group msazaidocintstg \
  --query "[0].properties.createdTime"

# 2. Test folders endpoint
curl https://ca-stg6fsvw-api.blackplant-3f8c2e39.eastus.azurecontainerapps.io/folders/

# Expected: 200 OK with list of folders
```

## Why This Fixes the Problem

```
Before (broken):
azd up ──▶ Pull old image ──▶ Deploy old code

After (fixed):
azd up ──▶ Run predeploy hook
       ──▶ Build new images from source
       ──▶ Push to ACR
       ──▶ Pull fresh images
       ──▶ Deploy NEW code ✓
```

## Related Documents

- `FOLDERS_FIX_STRATEGY.md` - Comprehensive analysis and all solutions
- `QUICK_FIX_GUIDE.md` - Quick reference for immediate fixes
- `IMPLEMENTATION_PLAN.md` - Detailed implementation steps
- `infra/scripts/build_images.sh` - Build script for Linux/Mac
- `infra/scripts/build_images.ps1` - Build script for Windows

## Bottom Line

Your code fixes are fine. The problem is that `azd up` deploys container images, not source code. To fix it permanently, either:
1. Add a predeploy hook to build images automatically (RECOMMENDED)
2. Wait for GitHub Actions to build before running azd up
3. Manually build and push images before azd up

The predeploy hook makes it automatic and foolproof.
