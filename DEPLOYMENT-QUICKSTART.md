# Quick Start: Deploy API Folders Fix

**Read this first**: This is the condensed execution guide. For full details, rationale, and troubleshooting, see `DEPLOYMENT-STRATEGY.md`.

## Pre-Flight Check
```bash
# Verify you're in the right place
pwd
# Should show: /workspaces/content-processing-solution-accelerator

# Verify Azure CLI is authenticated
az account show

# Verify you're on main branch
git branch
```

## Execution Steps (Copy-Paste Safe)

### Step 1: Preserve Working State (5 min)
```bash
# Commit working web changes
git add src/ContentProcessorWeb/src/Pages/DefaultPage/Components/ProcessQueueGrid/ProcessQueueGrid.tsx
git add src/ContentProcessorWeb/Makefile
git add src/ContentProcessorWeb/README-DEPLOY.md
git commit -m "feat: Add working checkbox selection fix and deployment tooling

- Fix checkbox selection to work independently of row clicks
- Add Makefile for streamlined web deployment
- Add deployment documentation

This commit preserves the WORKING state before API changes."

# Create safety tag
git tag -a working-web-v1 -m "Checkpoint: Working web app with checkbox fix"

# Create working branch
git checkout -b safe/api-folders-fix

# Verify tag exists
git tag -l
```
**Checkpoint**: You should see `working-web-v1` in the tag list.

---

### Step 2: Commit API Changes (3 min)
```bash
# Add API changes
git add src/ContentProcessorAPI/app/routers/contentprocessor.py
git add src/ContentProcessorAPI/Makefile
git add src/ContentProcessorAPI/app/tests/routers/test_contentprocessor_confidence.py
git commit -m "fix: Add missing CosmosMongDBHelper import for folders endpoint

- Import CosmosMongDBHelper in contentprocessor.py
- Add Makefile for API deployment
- Add confidence calculation tests

Separate commit to isolate API changes from working web changes."

# Verify the import is there
grep -n "CosmosMongDBHelper" src/ContentProcessorAPI/app/routers/contentprocessor.py
```
**Checkpoint**: You should see the import line in the grep output.

---

### Step 3: Test Build Locally (5-10 min)
```bash
# Change to API directory
cd src/ContentProcessorAPI

# Build Docker image (no deployment yet)
make build-only

# Verify image created
docker images | grep content-processor-api
```
**Checkpoint**: You should see the image with a timestamp tag.

---

### Step 4: Deploy API (8-12 min)
```bash
# Still in src/ContentProcessorAPI directory
# Full deployment
make deploy
```

**What to watch for**:
- "Logging into Azure Container Registry" - should succeed
- "Building Docker image" - should complete without errors
- "Pushing image to registry" - may take a few minutes
- "Updating container app" - will show new revision name

**Checkpoint**: Command completes and shows new revision name.

---

### Step 5: Verify Deployment (10-15 min)

#### 5A: Check Revision
```bash
cd /workspaces/content-processing-solution-accelerator

az containerapp revision list \
  --name ca-stg6fsvw-api \
  --resource-group msazaidocintstg \
  --query "[?properties.active==\`true\`].{Name:name,Traffic:properties.trafficWeight,Created:properties.createdTime}" \
  -o table
```
**Checkpoint**: Should show new revision (0000026 or higher) with 100% traffic.

#### 5B: Test Folders Endpoint
```bash
curl -X GET "https://ca-stg6fsvw-api.blackplant-3f8c2e39.eastus.azurecontainerapps.io/contentprocessor/folders" \
  -H "Content-Type: application/json"
```
**Checkpoint**: Should return JSON array of folders, not 500 error.

#### 5C: Check Logs (Optional)
```bash
az containerapp logs show \
  --name ca-stg6fsvw-api \
  --resource-group msazaidocintstg \
  --tail 50
```
**Checkpoint**: Should see no "ImportError" or "ModuleNotFoundError".

#### 5D: Test Web Application
1. Open browser: https://ca-stg6fsvw-web.blackplant-3f8c2e39.eastus.azurecontainerapps.io
2. Test checkbox selection - should still work
3. Test folder filtering - should now work
4. Open DevTools > Network > Look for `/contentprocessor/folders` call
5. Verify 200 status code

**Checkpoint**: All features work, no console errors.

---

### Step 6: Finalize (3 min)
```bash
cd /workspaces/content-processing-solution-accelerator

# Merge back to main
git checkout main
git merge safe/api-folders-fix

# Push to remote
git push origin main

# Clean up branch
git branch -d safe/api-folders-fix
```
**Checkpoint**: Changes merged, branch deleted.

---

## If Something Goes Wrong

### Build Failed (Step 3)?
**Impact**: None - nothing deployed
**Fix**: Check error message, fix code, recommit, retry

### Deployment Failed (Step 4)?
**Impact**: None - old revision still active
**Fix**: Check error message, may need to rollback code and retry

### Folders Endpoint Still Broken (Step 5)?
**Impact**: Medium - API broken but Web still works
**Rollback**:
```bash
az containerapp revision activate \
  --name ca-stg6fsvw-api \
  --resource-group msazaidocintstg \
  --revision ca-stg6fsvw-api--0000025
```

### Need to Reset Everything?
**Impact**: Return to pre-deployment state
**Rollback**:
```bash
# Rollback code
git checkout working-web-v1

# Rollback API deployment
az containerapp revision activate \
  --name ca-stg6fsvw-api \
  --resource-group msazaidocintstg \
  --revision ca-stg6fsvw-api--0000025

# Verify
az containerapp revision list \
  --name ca-stg6fsvw-api \
  --resource-group msazaidocintstg \
  --query "[?properties.active==\`true\`]"
```

---

## Success Checklist

- [ ] Step 1: Working state committed and tagged
- [ ] Step 2: API changes committed separately
- [ ] Step 3: Docker build succeeds locally
- [ ] Step 4: Deployment completes successfully
- [ ] Step 5A: New revision active with 100% traffic
- [ ] Step 5B: Folders endpoint returns 200
- [ ] Step 5C: No import errors in logs
- [ ] Step 5D: Web app works (checkbox + folders)
- [ ] Step 6: Changes merged to main

**All checked?** Deployment successful!

---

## Time Estimate
- Total: 34-48 minutes
- Actual deployment risk window: 8-12 minutes

---

## Quick Reference URLs
- **API**: https://ca-stg6fsvw-api.blackplant-3f8c2e39.eastus.azurecontainerapps.io
- **Web**: https://ca-stg6fsvw-web.blackplant-3f8c2e39.eastus.azurecontainerapps.io
- **Azure Portal**: https://portal.azure.com
- **Resource Group**: msazaidocintstg

---

## Notes
- Web app is NOT redeployed - stays on working revision
- API and Web are isolated - one can't break the other
- Multiple safety nets: git tag, branch, separate commits, container revisions
- Rollback is fast: <60 seconds
- Old revisions kept for 7 days for safety
