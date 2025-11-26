# Safe Deployment Strategy: Folders Endpoint Fix

## Executive Summary
**Objective**: Fix the folders endpoint in the API container without breaking the currently working web application.

**Risk Level**: MEDIUM
- API and Web are deployed independently (GOOD)
- Both have Makefile deployment tools (GOOD)
- Container Apps supports revision management with rollback (GOOD)
- Changes are uncommitted (RISK)
- Branch has diverged from upstream (AWARENESS)

## Current State Assessment

### Working Components
- Web application with fixed checkbox selection (revision: ca-stg6fsvw-web--0000026)
- API container with authentication and registry (revision: ca-stg6fsvw-api--0000025)
- Both deployed: 2025-11-26 04:54 UTC

### Pending Changes
```
Modified (staged for commit):
- src/ContentProcessorAPI/app/routers/contentprocessor.py (folders endpoint fix)
- src/ContentProcessorWeb/src/Pages/DefaultPage/Components/ProcessQueueGrid/ProcessQueueGrid.tsx (checkbox fix)

New files (need to add):
- src/ContentProcessorAPI/Makefile (deployment tool)
- src/ContentProcessorWeb/Makefile (deployment tool)
- src/ContentProcessorAPI/app/tests/routers/test_contentprocessor_confidence.py (new test)
```

### Key Infrastructure Details
- **ACR**: crstg6fsvw.azurecr.io
- **Resource Group**: msazaidocintstg
- **API App**: ca-stg6fsvw-api
- **Web App**: ca-stg6fsvw-web
- **Region**: eastus
- **Deployment Method**: Container Apps with revision-based deployment

## Deployment Strategy: The Safe Path Forward

### Phase 1: PRESERVE WORKING STATE (CRITICAL)

**Step 1.1: Create Safety Commit**
```bash
# Commit all working changes to preserve current state
git add src/ContentProcessorWeb/src/Pages/DefaultPage/Components/ProcessQueueGrid/ProcessQueueGrid.tsx
git add src/ContentProcessorWeb/Makefile
git add src/ContentProcessorWeb/README-DEPLOY.md
git commit -m "feat: Add working checkbox selection fix and deployment tooling

- Fix checkbox selection to work independently of row clicks
- Add Makefile for streamlined web deployment
- Add deployment documentation

This commit preserves the WORKING state before API changes."
```

**Why**: This creates a snapshot you can ALWAYS return to. If anything goes wrong, you have a clean commit to revert to.

**Step 1.2: Tag the Working State**
```bash
git tag -a working-web-v1 -m "Checkpoint: Working web app with checkbox fix"
```

**Why**: Tags are easier to reference than commit hashes. You can instantly return here with `git checkout working-web-v1`.

**Step 1.3: Create Safety Branch**
```bash
git checkout -b safe/api-folders-fix
```

**Why**: Work on a branch so main stays clean. If deployment fails, you can abandon this branch without affecting main.

**Verification Checkpoint 1**:
- [ ] Working changes committed
- [ ] Tag created
- [ ] New branch created
- [ ] Can see tag with: `git tag -l`

---

### Phase 2: PREPARE API CHANGES

**Step 2.1: Commit API Changes Separately**
```bash
# Add only API-related changes
git add src/ContentProcessorAPI/app/routers/contentprocessor.py
git add src/ContentProcessorAPI/Makefile
git add src/ContentProcessorAPI/app/tests/routers/test_contentprocessor_confidence.py
git commit -m "fix: Add missing CosmosMongDBHelper import for folders endpoint

- Import CosmosMongDBHelper in contentprocessor.py
- Add Makefile for API deployment
- Add confidence calculation tests

Separate commit to isolate API changes from working web changes."
```

**Why**: Separate commits make it easier to cherry-pick or revert specific changes.

**Step 2.2: Review Changes Before Building**
```bash
# Review what changed in the API
git show HEAD

# Double-check the specific import fix
grep -n "CosmosMongDBHelper" src/ContentProcessorAPI/app/routers/contentprocessor.py
```

**Verification Checkpoint 2**:
- [ ] API changes committed separately
- [ ] Import fix verified
- [ ] Makefile present
- [ ] Ready to build

---

### Phase 3: BUILD AND TEST LOCALLY

**Step 3.1: Test API Build (No Deployment)**
```bash
cd /workspaces/content-processing-solution-accelerator/src/ContentProcessorAPI

# Build the Docker image locally
make build-only

# Verify image was created
docker images | grep content-processor-api
```

**Why**: Catch Docker build errors BEFORE pushing to production. If this fails, nothing is deployed.

**Step 3.2: Optional - Run API Container Locally**
```bash
# Get environment variables from Azure
az containerapp show --name ca-stg6fsvw-api --resource-group msazaidocintstg \
  --query "properties.template.containers[0].env" -o json

# Run container locally with environment (if you want to test)
# docker run -d -p 8000:8000 --env-file .env.local crstg6fsvw.azurecr.io/content-processor-api:latest
```

**Why**: Optionally test the container locally before deploying. SKIP if you're confident in the import fix.

**Verification Checkpoint 3**:
- [ ] Docker build succeeds
- [ ] Image exists locally
- [ ] No Python import errors
- [ ] (Optional) Local container runs

---

### Phase 4: STAGED DEPLOYMENT WITH VERIFICATION

**Step 4.1: Deploy API Only (Web Untouched)**
```bash
cd /workspaces/content-processing-solution-accelerator/src/ContentProcessorAPI

# Full deployment: build + push + update
make deploy
```

**What Happens**:
- Logs into Azure Container Registry
- Builds Docker image with timestamp tag
- Pushes to registry
- Creates NEW revision: ca-stg6fsvw-api--0000026
- Routes 100% traffic to new revision
- OLD revision (0000025) remains available for rollback

**Step 4.2: Immediate Verification**
```bash
# Check new revision is active
az containerapp revision list \
  --name ca-stg6fsvw-api \
  --resource-group msazaidocintstg \
  --query "[?properties.active==\`true\`].{Name:name,Traffic:properties.trafficWeight,Created:properties.createdTime}" \
  -o table

# Test the folders endpoint
API_URL="https://ca-stg6fsvw-api.blackplant-3f8c2e39.eastus.azurecontainerapps.io"
curl -X GET "$API_URL/contentprocessor/folders" -H "Content-Type: application/json"
```

**Expected Result**: Folders endpoint returns data without 500 error.

**Verification Checkpoint 4**:
- [ ] New API revision deployed
- [ ] Folders endpoint responds (not 500)
- [ ] API logs show no import errors
- [ ] Web app still loads (unchanged)

---

### Phase 5: END-TO-END VERIFICATION

**Step 5.1: Test Critical User Journeys**

Test these in the web application to ensure nothing broke:

1. **Checkbox Selection Test**:
   - Open: https://ca-stg6fsvw-web.blackplant-3f8c2e39.eastus.azurecontainerapps.io
   - Select multiple rows using checkboxes
   - Verify selection works independently of row clicks
   - **Expected**: Checkboxes work (already deployed)

2. **Folders Endpoint Test**:
   - Navigate to any feature that uses the folders filter
   - Open browser DevTools > Network tab
   - Look for call to `/contentprocessor/folders`
   - **Expected**: 200 response with folder list

3. **Process Queue Test**:
   - View the process queue grid
   - Filter by folder
   - Select and process items
   - **Expected**: All functionality works

**Step 5.2: Check Application Logs**
```bash
# Check API logs for errors
az containerapp logs show \
  --name ca-stg6fsvw-api \
  --resource-group msazaidocintstg \
  --follow \
  --tail 50

# Look for:
# - No "ModuleNotFoundError" or "ImportError"
# - Successful /folders endpoint calls
# - No 500 status codes
```

**Verification Checkpoint 5**:
- [ ] All user journeys work
- [ ] Folders endpoint functional
- [ ] Checkbox selection still works
- [ ] No errors in logs
- [ ] Web app unchanged and functional

---

### Phase 6: FINALIZE AND MERGE

**Step 6.1: Merge to Main (If Successful)**
```bash
# Switch back to main
git checkout main

# Merge the safe branch
git merge safe/api-folders-fix

# Push to your remote
git push origin main
```

**Step 6.2: Clean Up**
```bash
# Delete the safety branch (now merged)
git branch -d safe/api-folders-fix
```

**Verification Checkpoint 6**:
- [ ] Changes merged to main
- [ ] Both commits visible in history
- [ ] Working tag still accessible
- [ ] Deployment successful

---

## Rollback Procedures

### SCENARIO 1: Build Fails Locally (Phase 3)
**Impact**: NONE - Nothing deployed
**Action**: Fix the code error, recommit, retry build

### SCENARIO 2: API Deployment Succeeds but Folders Endpoint Still Broken (Phase 4)
**Impact**: MEDIUM - API broken but Web still works
**Action**:
```bash
# Rollback to previous revision
az containerapp revision activate \
  --name ca-stg6fsvw-api \
  --resource-group msazaidocintstg \
  --revision ca-stg6fsvw-api--0000025

# Verify rollback
az containerapp revision list \
  --name ca-stg6fsvw-api \
  --resource-group msazaidocintstg \
  --query "[?properties.active==\`true\`]"
```
**Recovery Time**: 30-60 seconds

### SCENARIO 3: API Breaks Other Endpoints (Phase 5)
**Impact**: HIGH - Multiple API features broken
**Action**: Same as Scenario 2 - immediate revision rollback

### SCENARIO 4: Need to Return to Pre-Deployment State (Any Phase)
**Impact**: Complete reset needed
**Action**:
```bash
# Return to working tag
git checkout working-web-v1

# Or reset branch to working state
git reset --hard working-web-v1

# Redeploy previous API revision if needed
az containerapp revision activate \
  --name ca-stg6fsvw-api \
  --resource-group msazaidocintstg \
  --revision ca-stg6fsvw-api--0000025
```

### SCENARIO 5: Complete Disaster Recovery
**Impact**: CRITICAL - Everything broken
**Action**:
```bash
# 1. Activate old API revision
az containerapp revision activate \
  --name ca-stg6fsvw-api \
  --resource-group msazaidocintstg \
  --revision ca-stg6fsvw-api--0000025

# 2. Return code to working tag
git reset --hard working-web-v1

# 3. Force push if needed (BE CAREFUL)
# git push --force-with-lease origin main

# 4. Verify both containers on old revisions
az containerapp show --name ca-stg6fsvw-api --resource-group msazaidocintstg \
  --query "properties.latestRevisionName"
```

---

## Risk Assessment Matrix

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Docker build fails | LOW | NONE | Local build-only test catches this |
| Import error persists | MEDIUM | MEDIUM | Revision rollback in 60 seconds |
| API breaks other endpoints | LOW | HIGH | Separate commit allows easy revert |
| Web app affected | VERY LOW | HIGH | Web not redeployed, isolated change |
| Git state lost | VERY LOW | CRITICAL | Tag + branch + separate commits protect state |
| Both containers break | VERY LOW | CRITICAL | Revision-based rollback for both |

**Overall Risk**: LOW-MEDIUM with strong mitigation at each stage

---

## Why This Strategy is Safe

### 1. **Isolation Layers**
- API and Web are separate containers - one can break without affecting the other
- Changes committed separately - can revert API without touching Web
- Branch-based work - main branch stays clean

### 2. **Multiple Recovery Points**
- **Git tag**: `working-web-v1` - instant code recovery
- **Git branch**: `safe/api-folders-fix` - isolated experimentation
- **Container revision**: `ca-stg6fsvw-api--0000025` - instant deployment rollback
- **Separate commits**: Can cherry-pick or revert individual changes

### 3. **Progressive Verification**
- Checkpoint after each phase
- Failures caught early before production impact
- Local testing catches build errors
- Revision system allows instant rollback

### 4. **No Simultaneous Changes**
- Only API is redeployed
- Web remains on working revision (0000026)
- If API fails, Web continues working

### 5. **Clear Success Criteria**
Each phase has explicit verification:
- Phase 1: Git state preserved
- Phase 2: Code changes isolated
- Phase 3: Build succeeds locally
- Phase 4: New revision active
- Phase 5: All features functional
- Phase 6: Changes merged cleanly

---

## Pre-Flight Checklist

Before starting deployment:

- [ ] Read this entire document
- [ ] Understand each rollback procedure
- [ ] Have Azure CLI authenticated: `az account show`
- [ ] Verify current directory: `/workspaces/content-processing-solution-accelerator`
- [ ] Backup: Create tag for current state
- [ ] Time: Allocate 30-45 minutes for careful execution
- [ ] Monitoring: Have Azure Portal open for visual confirmation
- [ ] Communication: Inform users of maintenance window (optional)

---

## Post-Deployment Actions

After successful deployment:

1. **Document the fix**:
   - Update notes.md with what was fixed
   - Record the revision numbers for audit trail

2. **Monitor for 24 hours**:
   - Check logs periodically
   - Watch for any unexpected errors
   - Validate folder filtering works for users

3. **Keep old revisions for 7 days**:
   - Don't delete old revisions immediately
   - Allows rollback if issues discovered later
   - Azure Container Apps auto-cleanup after retention period

4. **Update upstream (if applicable)**:
   ```bash
   # If you want to sync with upstream later
   git fetch upstream
   git merge upstream/main
   # Resolve conflicts carefully
   ```

---

## Quick Reference: Emergency Commands

```bash
# ROLLBACK API
az containerapp revision activate \
  --name ca-stg6fsvw-api \
  --resource-group msazaidocintstg \
  --revision ca-stg6fsvw-api--0000025

# RETURN CODE TO WORKING STATE
git checkout working-web-v1

# CHECK ACTIVE REVISIONS
az containerapp revision list \
  --name ca-stg6fsvw-api \
  --resource-group msazaidocintstg \
  --query "[?properties.active==\`true\`]"

# VIEW API LOGS
az containerapp logs show \
  --name ca-stg6fsvw-api \
  --resource-group msazaidocintstg \
  --follow --tail 100

# TEST FOLDERS ENDPOINT
curl https://ca-stg6fsvw-api.blackplant-3f8c2e39.eastus.azurecontainerapps.io/contentprocessor/folders
```

---

## Timeline Estimate

| Phase | Duration | Risk Window |
|-------|----------|-------------|
| Phase 1: Preserve State | 5 min | None - just git operations |
| Phase 2: Prepare API | 3 min | None - just commits |
| Phase 3: Build Locally | 5-10 min | None - local only |
| Phase 4: Deploy API | 8-12 min | Medium - new revision deploying |
| Phase 5: Verification | 10-15 min | Low - testing only |
| Phase 6: Finalize | 3 min | None - just git merge |
| **TOTAL** | **34-48 min** | **8-12 min actual deployment risk** |

**Key Insight**: Only 8-12 minutes of actual production risk during the container deployment. All other time is preparation and verification.

---

## Decision Log

### Should we create a Makefile for the API?
**DECISION**: YES - Already exists
**RATIONALE**: Provides consistent deployment interface, reduces human error, enables easy rollback

### Should we commit changes before deploying?
**DECISION**: YES - Required
**RATIONALE**:
- Creates audit trail
- Enables code-level rollback
- Separate commits isolate changes
- Tag provides safety checkpoint

### How to preserve the current working state?
**DECISION**: Multi-layered approach
**RATIONALE**:
1. Git tag: Instant code recovery
2. Git branch: Safe experimentation
3. Container revision: Instant deployment rollback
4. Separate commits: Granular control

### What verification should happen at each step?
**DECISION**: Progressive checkpoints with explicit criteria
**RATIONALE**:
- Catch failures early
- Validate assumptions
- Build confidence
- Document success
- Enable informed rollback decisions

---

## Contact Information (If Needed)

- **Azure Portal**: https://portal.azure.com
- **Resource Group**: msazaidocintstg
- **Container Apps**:
  - API: ca-stg6fsvw-api
  - Web: ca-stg6fsvw-web
- **Registry**: crstg6fsvw.azurecr.io

---

## Success Criteria

Deployment is considered successful when ALL of these are true:

1. [ ] API revision ca-stg6fsvw-api--0000026 (or higher) is active
2. [ ] Folders endpoint returns 200 status code
3. [ ] Web application checkbox selection still works
4. [ ] No import errors in API logs
5. [ ] Folder filtering works in UI
6. [ ] No increase in error rates
7. [ ] All user journeys functional
8. [ ] Changes committed and merged to main
9. [ ] Working state preserved in git tag

**If ANY criterion fails**: Execute appropriate rollback from the Rollback Procedures section.

---

## Conclusion

This strategy prioritizes safety through:
- **Isolation**: API and Web deployed independently
- **Preservation**: Multiple recovery points (git tag, branch, commits, revisions)
- **Verification**: Checkpoints at each phase
- **Rollback**: Fast recovery procedures (<60 seconds)
- **Progressive risk**: Failures caught early before production impact

The risk of breaking the working web application is VERY LOW because:
1. Web container is not redeployed
2. API changes are isolated to import fix
3. Multiple rollback mechanisms available
4. Clear success criteria at each stage

**Recommendation**: Proceed with deployment following this phased approach. The strategy balances safety with efficiency, ensuring the working state is preserved while fixing the folders endpoint.
