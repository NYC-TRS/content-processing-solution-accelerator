# Deployment Checklist: Ensure Folders Fix Survives

Use this checklist every time you deploy to ensure your code changes are included.

## Pre-Deployment Checks

### 1. Verify Code Changes Are Committed
```bash
# Check for uncommitted changes
git status

# If there are uncommitted changes to the folders endpoint:
git add src/ContentProcessorAPI/app/routers/contentprocessor.py
git commit -m "Fix folders endpoint"
```

### 2. Choose Your Deployment Method

Select ONE of the following methods:

---

## Method A: Automated Build (RECOMMENDED)

### Prerequisites
- [x] Docker is installed and running
- [x] Azure CLI is installed and logged in
- [x] Build scripts exist in `infra/scripts/`

### Steps
```bash
# 1. Backup current azure.yaml (first time only)
cp azure.yaml azure.yaml.backup

# 2. Replace azure.yaml with the version that has predeploy hook
cp azure.yaml.new azure.yaml

# 3. Verify build scripts are executable
chmod +x infra/scripts/build_images.sh

# 4. Run deployment (will automatically build images)
azd up

# Time estimate: 15-20 minutes (includes building 3 images)
```

### Verification
```bash
# Check deployed image
az containerapp show \
  --name ca-stg6fsvw-api \
  --resource-group msazaidocintstg \
  --query "properties.template.containers[0].image"

# Test folders endpoint
curl https://ca-stg6fsvw-api.blackplant-3f8c2e39.eastus.azurecontainerapps.io/folders/
```

---

## Method B: Wait for GitHub Actions

### Prerequisites
- [x] Code is pushed to main branch
- [x] GitHub Actions has write access to ACR

### Steps
```bash
# 1. Push your code
git push origin main

# 2. Monitor GitHub Actions workflow
gh run watch
# Or visit: https://github.com/{org}/{repo}/actions

# 3. Wait for "Build and Push Docker Images" to complete
# Time: ~5-10 minutes

# 4. Verify new images exist
az acr repository show-tags \
  --name crstg6fsvw \
  --repository contentprocessorapi \
  --orderby time_desc \
  --top 3

# 5. Deploy with azd
azd up

# Time estimate: 15-20 minutes total
```

### Verification
```bash
# Same as Method A
```

---

## Method C: Manual Build

### Prerequisites
- [x] Docker is installed and running
- [x] Logged into ACR

### Steps
```bash
# 1. Login to ACR
az acr login --name crstg6fsvw

# 2. Build API image
docker build \
  -t crstg6fsvw.azurecr.io/contentprocessorapi:latest \
  -f src/ContentProcessorAPI/Dockerfile \
  src/ContentProcessorAPI

# 3. Push API image
docker push crstg6fsvw.azurecr.io/contentprocessorapi:latest

# 4. Optional: Build other images if they changed
docker build -t crstg6fsvw.azurecr.io/contentprocessor:latest \
  -f src/ContentProcessor/Dockerfile src/ContentProcessor
docker push crstg6fsvw.azurecr.io/contentprocessor:latest

docker build -t crstg6fsvw.azurecr.io/contentprocessorweb:latest \
  -f src/ContentProcessorWeb/Dockerfile src/ContentProcessorWeb
docker push crstg6fsvw.azurecr.io/contentprocessorweb:latest

# 5. Deploy
azd up

# Time estimate: 10-15 minutes
```

### Verification
```bash
# Same as Method A
```

---

## Post-Deployment Verification

### 1. Check Container App Status
```bash
az containerapp show \
  --name ca-stg6fsvw-api \
  --resource-group msazaidocintstg \
  --query "properties.{provisioningState:provisioningState,runningStatus:runningStatus}"
```

Expected output:
```json
{
  "provisioningState": "Succeeded",
  "runningStatus": "Running"
}
```

### 2. Check Deployed Image Version
```bash
az containerapp show \
  --name ca-stg6fsvw-api \
  --resource-group msazaidocintstg \
  --query "properties.template.containers[0].image" \
  -o tsv
```

Expected output:
```
crstg6fsvw.azurecr.io/contentprocessorapi:latest
```

### 3. Check Image Creation Time
```bash
az acr repository show-manifests \
  --name crstg6fsvw \
  --repository contentprocessorapi \
  --orderby time_desc \
  --top 1 \
  --query "[0].{tag:tags[0],created:timestamp}"
```

Verify timestamp is recent (within last hour).

### 4. Test Folders Endpoint
```bash
# Without authentication (will return 401 if auth is required)
curl -I https://ca-stg6fsvw-api.blackplant-3f8c2e39.eastus.azurecontainerapps.io/folders/

# With authentication
curl -X GET \
  "https://ca-stg6fsvw-api.blackplant-3f8c2e39.eastus.azurecontainerapps.io/folders/" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

Expected: HTTP 200 OK with JSON response containing folders array

### 5. Check Application Logs
```bash
az containerapp logs show \
  --name ca-stg6fsvw-api \
  --resource-group msazaidocintstg \
  --follow \
  --tail 50
```

Look for:
- No error messages about missing imports
- No 500 errors when accessing /folders endpoint
- Successful database connections

### 6. Test with Frontend
```bash
# Open web app
echo "https://ca-stg6fsvw-web.blackplant-3f8c2e39.eastus.azurecontainerapps.io"

# Steps:
# 1. Login to the application
# 2. Navigate to page with folder filter
# 3. Verify folders dropdown populates
# 4. Select a folder and verify filtering works
```

---

## Troubleshooting

### Issue: Docker build fails with "Cannot connect to Docker daemon"
```bash
# Solution: Start Docker
sudo systemctl start docker  # Linux
# Or start Docker Desktop on Mac/Windows
```

### Issue: ACR login fails
```bash
# Solution: Ensure you're logged into Azure
az login
az account show

# Then retry
az acr login --name crstg6fsvw
```

### Issue: azd up uses old image
```bash
# Solution: Force Container App revision update
az containerapp revision list \
  --name ca-stg6fsvw-api \
  --resource-group msazaidocintstg \
  --output table

# Deactivate old revisions
az containerapp revision deactivate \
  --name ca-stg6fsvw-api \
  --resource-group msazaidocintstg \
  --revision REVISION_NAME

# Or restart the app
az containerapp revision restart \
  --name ca-stg6fsvw-api \
  --resource-group msazaidocintstg \
  --revision LATEST_REVISION_NAME
```

### Issue: Folders endpoint returns 500 error
```bash
# Check logs for details
az containerapp logs show \
  --name ca-stg6fsvw-api \
  --resource-group msazaidocintstg \
  --follow

# Common issues:
# - Missing CosmosMongDBHelper import
# - Database connection string not set
# - Missing APP_CONFIG_ENDPOINT environment variable
```

### Issue: Predeploy hook fails
```bash
# Check if scripts exist
ls -la infra/scripts/build_images.sh
ls -la infra/scripts/build_images.ps1

# Make scripts executable
chmod +x infra/scripts/build_images.sh

# Test script manually
./infra/scripts/build_images.sh

# If it works manually, azure.yaml may have syntax error
# Restore backup and try again
cp azure.yaml.backup azure.yaml
```

---

## Rollback Plan

If deployment fails or introduces issues:

### 1. Rollback to Previous Container App Revision
```bash
# List revisions
az containerapp revision list \
  --name ca-stg6fsvw-api \
  --resource-group msazaidocintstg \
  --output table

# Activate previous working revision
az containerapp revision activate \
  --name ca-stg6fsvw-api \
  --resource-group msazaidocintstg \
  --revision PREVIOUS_REVISION_NAME
```

### 2. Rollback to Previous Image Tag
```bash
# List available tags
az acr repository show-tags \
  --name crstg6fsvw \
  --repository contentprocessorapi \
  --orderby time_desc

# Update Container App with specific tag
az containerapp update \
  --name ca-stg6fsvw-api \
  --resource-group msazaidocintstg \
  --image crstg6fsvw.azurecr.io/contentprocessorapi:PREVIOUS_TAG
```

### 3. Restore Previous azure.yaml
```bash
# If you backed up azure.yaml
cp azure.yaml.backup azure.yaml

# Re-deploy
azd up
```

---

## Success Criteria

Deployment is successful when ALL of the following are true:

- [ ] Container Apps are in "Running" state
- [ ] Deployed image timestamp is recent (last hour)
- [ ] Folders endpoint returns 200 OK
- [ ] Folders endpoint returns valid JSON with folders array
- [ ] No errors in Container App logs
- [ ] Frontend can fetch and display folders
- [ ] Folder filtering works in the UI

---

## Best Practices

1. **Always test in dev first** before deploying to production
2. **Use specific image tags** for production deployments (not 'latest')
3. **Keep a log** of what image versions are deployed where
4. **Monitor logs** for 10 minutes after deployment
5. **Have a rollback plan** ready before deploying
6. **Commit before deploying** so you can track what was deployed
7. **Tag releases in git** that correspond to production deployments

---

## Quick Reference

```bash
# Environment variables
export ACR_NAME="crstg6fsvw"
export ACR_REGISTRY="crstg6fsvw.azurecr.io"
export API_APP_NAME="ca-stg6fsvw-api"
export RESOURCE_GROUP="msazaidocintstg"
export API_FQDN="ca-stg6fsvw-api.blackplant-3f8c2e39.eastus.azurecontainerapps.io"

# Common commands
alias check-image="az containerapp show --name $API_APP_NAME -g $RESOURCE_GROUP --query 'properties.template.containers[0].image'"
alias check-logs="az containerapp logs show --name $API_APP_NAME -g $RESOURCE_GROUP --follow"
alias list-images="az acr repository show-tags --name $ACR_NAME --repository contentprocessorapi --orderby time_desc"
alias test-folders="curl https://$API_FQDN/folders/"
```

---

## Contact / Escalation

If issues persist after following this checklist:

1. Check `FOLDERS_FIX_STRATEGY.md` for detailed analysis
2. Review Container App logs for specific error messages
3. Verify all environment variables are set correctly
4. Ensure database connection string is valid
5. Check Azure service health status
6. Contact Azure support if infrastructure issues suspected

---

## Maintenance

This checklist should be updated when:
- New services are added
- Deployment process changes
- New environments are created
- Issues are discovered and resolved
- Best practices evolve
