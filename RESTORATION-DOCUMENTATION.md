# Content Processing Solution Accelerator - Complete Restoration Documentation

This document provides a comprehensive record of all issues encountered and fixes applied to restore functionality to the Content Processing Solution Accelerator deployment.

---

## 1. INITIAL PROBLEMS

### What Was Broken

**Container Apps Failing to Start**
- All three container apps (web, api, processor) were failing to pull images
- Error: `Failed to pull image from registry`
- Root cause: Container apps were trying to pull from wrong Azure Container Registry (ACR)

**Image Pull Authentication Failures**
- Container apps lacked proper authentication to the correct ACR
- Managed identity not properly configured for registry access
- Missing role assignments for AcrPull permissions

**Web Application Broken Checkbox Behavior**
- Clicking checkboxes in the process queue grid was triggering row selection
- Checkbox clicks were not isolated from row click handlers
- Multi-select functionality was broken for bulk delete operations

### Root Cause Analysis

1. **Registry Misconfiguration**: The Bicep template had a hardcoded registry endpoint (`cpscontainerreg.azurecr.io`) that didn't match the actual deployed registry (`crstg6fsvw.azurecr.io`)

2. **Authentication Gap**: Container apps were configured without proper registry authentication blocks, even though a managed identity existed for ACR access

3. **Missing Role Assignments**: The managed identity created for ACR access wasn't assigned AcrPull role on the actual deployed registry

4. **Frontend Bug**: Event handlers in ProcessQueueGrid component weren't properly isolating checkbox clicks from row clicks

---

## 2. REGISTRY ISSUE

### The Problem

**Wrong Registry Reference**
- Line 61 of `/workspaces/content-processing-solution-accelerator/infra/main.bicep` had:
  ```bicep
  param publicContainerImageEndpoint string = 'cpscontainerreg.azurecr.io'
  ```
- This was a placeholder/example registry that didn't exist in the deployment
- The actual deployed registry was: `crstg6fsvw.azurecr.io`

### The Fix

**Step 1: Correct Registry Parameter (Line 61)**
```bicep
param publicContainerImageEndpoint string = 'crstg6fsvw.azurecr.io'
```

**Step 2: Add Registry Authentication - Container App Processor (Lines 712-717)**
```bicep
registries: [
  {
    server: publicContainerImageEndpoint
    identity: avmContainerRegistryReader.outputs.resourceId
  }
]
```

**Step 3: Add Registry Authentication - Container App API (Lines 766-771)**
```bicep
registries: [
  {
    server: publicContainerImageEndpoint
    identity: avmContainerRegistryReader.outputs.resourceId
  }
]
```

**Step 4: Add Registry Authentication - Container App Web (Lines 883-888)**
```bicep
registries: [
  {
    server: publicContainerImageEndpoint
    identity: avmContainerRegistryReader.outputs.resourceId
  }
]
```

### What This Fixed

- Container apps now authenticate to the correct registry using managed identity
- Image pulls succeed because the apps can access `crstg6fsvw.azurecr.io`
- All three container apps (processor, api, web) use consistent authentication

---

## 3. ACR PERMISSIONS

### Which Identities Needed AcrPull Role

**Managed Identity for Container Apps**
- Identity Name: `id-acr-stg6fsvw` (or similar based on solution suffix)
- Resource ID: Output from `avmContainerRegistryReader` module (lines 693-701)
- Principal ID: `avmContainerRegistryReader.outputs.principalId`

This identity is:
1. Created specifically for ACR access
2. Assigned to all three container apps as a user-assigned managed identity
3. Used in the `registries` configuration block for authentication

### How Permissions Were Granted

**Method 1: Through Bicep Template (Lines 402-408)**
```bicep
roleAssignments: [
  {
    principalId: avmContainerRegistryReader.outputs.principalId
    roleDefinitionIdOrName: 'AcrPull'
    principalType: 'ServicePrincipal'
  }
]
```

This assigns the AcrPull role at the ACR resource level when the registry is created/updated.

**Method 2: Manual Azure CLI (Used During Troubleshooting)**
```bash
# Get the principal ID of the managed identity
PRINCIPAL_ID=$(az identity show \
  --name id-acr-stg6fsvw \
  --resource-group msazaidocintstg \
  --query principalId -o tsv)

# Get the registry resource ID
ACR_ID=$(az acr show \
  --name crstg6fsvw \
  --resource-group msazaidocintstg \
  --query id -o tsv)

# Assign AcrPull role
az role assignment create \
  --assignee $PRINCIPAL_ID \
  --role "AcrPull" \
  --scope $ACR_ID
```

### Verification Command
```bash
# Verify role assignment
az role assignment list \
  --assignee $PRINCIPAL_ID \
  --scope $ACR_ID \
  -o table
```

---

## 4. CONTAINER APP UPDATES

### Configuration Changes

All three container apps required two key changes:

#### 1. Registry Authentication Configuration

**Processor App (lines 712-717, 1200-1205)**
```bicep
registries: [
  {
    server: publicContainerImageEndpoint  # crstg6fsvw.azurecr.io
    identity: avmContainerRegistryReader.outputs.resourceId
  }
]
```

**API App (lines 766-771, 1264-1269)**
```bicep
registries: [
  {
    server: publicContainerImageEndpoint  # crstg6fsvw.azurecr.io
    identity: avmContainerRegistryReader.outputs.resourceId
  }
]
```

**Web App (lines 883-888)**
```bicep
registries: [
  {
    server: publicContainerImageEndpoint  # crstg6fsvw.azurecr.io
    identity: avmContainerRegistryReader.outputs.resourceId
  }
]
```

#### 2. Managed Identity Assignment

Each container app was configured with both system-assigned and user-assigned identities:

```bicep
managedIdentities: {
  systemAssigned: true
  userAssignedResourceIds: [
    avmContainerRegistryReader.outputs.resourceId
  ]
}
```

- **System-assigned**: For accessing other Azure resources (Storage, Cosmos DB, etc.)
- **User-assigned**: Specifically for ACR authentication

#### 3. Image References Updated

**Processor App (line 728, 1216)**
```bicep
image: '${publicContainerImageEndpoint}/contentprocessor:${imageTag}'
# Becomes: crstg6fsvw.azurecr.io/contentprocessor:latest
```

**API App (line 782, 1281)**
```bicep
image: '${publicContainerImageEndpoint}/contentprocessorapi:${imageTag}'
# Becomes: crstg6fsvw.azurecr.io/contentprocessorapi:latest
```

**Web App (line 917)**
```bicep
image: '${publicContainerImageEndpoint}/contentprocessorweb:${imageTag}'
# Becomes: crstg6fsvw.azurecr.io/contentprocessorweb:latest
```

### Manual Update Commands (Used During Troubleshooting)

```bash
# Update Web App
az containerapp update \
  --name ca-stg6fsvw-web \
  --resource-group msazaidocintstg \
  --image crstg6fsvw.azurecr.io/contentprocessorweb:latest

# Update API App
az containerapp update \
  --name ca-stg6fsvw-api \
  --resource-group msazaidocintstg \
  --image crstg6fsvw.azurecr.io/contentprocessorapi:latest

# Update Processor App
az containerapp update \
  --name ca-stg6fsvw-app \
  --resource-group msazaidocintstg \
  --image crstg6fsvw.azurecr.io/contentprocessor:latest
```

---

## 5. WEB APP REBUILD

### The Checkbox Fix

**Problem**: In the ProcessQueueGrid component, clicking a checkbox would both toggle selection AND trigger the row click handler, showing the document in the center panel.

**File Modified**: `/workspaces/content-processing-solution-accelerator/src/ContentProcessorWeb/src/Pages/DefaultPage/Components/ProcessQueueGrid/ProcessQueueGrid.tsx`

**Changes Made**:

1. **Separated Click Handlers (Lines 252-273)**
   ```typescript
   onClick: (e: React.MouseEvent) => {
       const target = e.target as HTMLElement;
       const isCheckbox = target.closest('[role="checkbox"]');

       if (isCheckbox && !e.defaultPrevented) {
           // Checkbox click - toggle selection for bulk operations
           toggleRow(e, row.rowId);
       } else {
           // Row click - show document in center panel (not for deletion)
           const isInteractiveElement =
               target.closest('button') ||
               target.closest('[role="menuitem"]') ||
               target.closest('[role="menu"]');

           if (!isInteractiveElement && !e.defaultPrevented) {
               const item = row.item;
               const findItem = getSelectedItem(item.processId.label);
               dispatch(setSelectedGridRow({ processId: item.processId.label, item: findItem }));
           }
       }
   }
   ```

2. **Simplified RenderRow (Lines 297-312)**
   - Removed `handleRowClick` function
   - Checkbox clicks now only affect multi-select state
   - Row clicks now only affect document preview
   - Both behaviors are independent

3. **Added role="checkbox" attribute (Lines 309-312)**
   ```typescript
   <TableSelectionCell
       role="checkbox"
       checked={selected}
       aria-label={`Select ${item.fileName.label}`}
   />
   ```

### Image Naming Convention

**Docker Image Names**:
- Built as: `content-processor-web` (with hyphens)
- Tagged as: `contentprocessorweb` (no hyphens, matches Bicep expectations)

**Why Two Names?**
- Local development uses readable hyphenated names
- Azure deployment expects no-hyphen format (legacy convention)
- Both tags are applied during build to support both use cases

**Build Commands**:
```bash
# Builds with both tags
docker build -t crstg6fsvw.azurecr.io/content-processor-web:TIMESTAMP \
             -t crstg6fsvw.azurecr.io/contentprocessorweb:TIMESTAMP \
             -t crstg6fsvw.azurecr.io/contentprocessorweb:latest .
```

### Deployment Process

**Automated via Makefile**:

1. **Create Makefile**: `/workspaces/content-processing-solution-accelerator/src/ContentProcessorWeb/Makefile`
   ```makefile
   ACR_NAME := crstg6fsvw
   RESOURCE_GROUP := msazaidocintstg
   APP_NAME := ca-stg6fsvw-web
   IMAGE_NAME := content-processor-web
   TIMESTAMP := $(shell date +%s)
   ```

2. **Single Command Deployment**:
   ```bash
   cd /workspaces/content-processing-solution-accelerator/src/ContentProcessorWeb
   make deploy
   ```

3. **What Happens**:
   - Logs into ACR: `az acr login --name crstg6fsvw`
   - Builds image: `docker build -t crstg6fsvw.azurecr.io/content-processor-web:TIMESTAMP .`
   - Pushes to registry: `docker push crstg6fsvw.azurecr.io/content-processor-web:TIMESTAMP`
   - Updates container app: `az containerapp update --name ca-stg6fsvw-web --image ...`

4. **Timestamp Strategy**:
   - Each build gets unique timestamp tag: `1732635521`
   - Plus `:latest` tag for convenience
   - Timestamped tags force Azure to pull new images (not cached)

### Manual Deployment Alternative

```bash
# Navigate to web app directory
cd /workspaces/content-processing-solution-accelerator/src/ContentProcessorWeb

# Login to ACR
az acr login --name crstg6fsvw

# Build with timestamp
TIMESTAMP=$(date +%s)
docker build -t crstg6fsvw.azurecr.io/content-processor-web:$TIMESTAMP \
             -t crstg6fsvw.azurecr.io/contentprocessorweb:$TIMESTAMP \
             -t crstg6fsvw.azurecr.io/contentprocessorweb:latest .

# Push both tags
docker push crstg6fsvw.azurecr.io/content-processor-web:$TIMESTAMP
docker push crstg6fsvw.azurecr.io/contentprocessorweb:$TIMESTAMP
docker push crstg6fsvw.azurecr.io/contentprocessorweb:latest

# Update container app
az containerapp update \
  --name ca-stg6fsvw-web \
  --resource-group msazaidocintstg \
  --image crstg6fsvw.azurecr.io/content-processor-web:$TIMESTAMP
```

### Post-Deployment Verification

```bash
# Check container app status
az containerapp show \
  --name ca-stg6fsvw-web \
  --resource-group msazaidocintstg \
  --query "properties.{Status:provisioningState,Image:template.containers[0].image}" \
  -o table

# Check revision status
az containerapp revision list \
  --name ca-stg6fsvw-web \
  --resource-group msazaidocintstg \
  --query "[].{Name:name,Active:properties.active,Created:properties.createdTime}" \
  -o table

# Test the endpoint
curl https://ca-stg6fsvw-web.blackplant-3f8c2e39.eastus.azurecontainerapps.io
```

---

## 6. AUTHENTICATION CONFIGURATION

### Environment Variables

The web container app requires three critical authentication settings (lines 928-938 in main.bicep):

```bicep
env: [
  {
    name: 'APP_WEB_CLIENT_ID'
    value: 'd3b3c2ae-7f21-4d63-a046-3c14154f18a1'
  }
  {
    name: 'APP_WEB_AUTHORITY'
    value: '${environment().authentication.loginEndpoint}/${tenant().tenantId}'
  }
  {
    name: 'APP_WEB_SCOPE'
    value: 'api://445cde4d-2ab0-4d53-9a41-900716241a95/user_impersonation'
  }
  {
    name: 'APP_API_SCOPE'
    value: 'api://445cde4d-2ab0-4d53-9a41-900716241a95/user_impersonation'
  }
]
```

### Why They're Important

#### APP_WEB_CLIENT_ID
- **Value**: `d3b3c2ae-7f21-4d63-a046-3c14154f18a1`
- **Purpose**: The Azure AD application (client) ID for the web frontend
- **Usage**: Used by MSAL (Microsoft Authentication Library) to identify the web app during authentication
- **Impact if missing**: Users cannot log in; authentication will fail immediately

#### APP_WEB_AUTHORITY
- **Value**: `https://login.microsoftonline.com/{tenantId}`
- **Purpose**: The Azure AD tenant authority endpoint
- **Usage**: Tells MSAL which Azure AD tenant to authenticate against
- **Impact if missing**: Authentication requests go to wrong tenant or fail entirely

#### APP_WEB_SCOPE / APP_API_SCOPE
- **Value**: `api://445cde4d-2ab0-4d53-9a41-900716241a95/user_impersonation`
- **Purpose**: The OAuth2 scope for accessing the backend API
- **Usage**: Requests an access token with permissions to call the API
- **Impact if missing**:
  - User can log in but cannot call API endpoints
  - API returns 401 Unauthorized
  - Frontend shows "Failed to fetch" errors

### Authentication Flow

1. User visits web app
2. Web app redirects to `APP_WEB_AUTHORITY` (Azure AD)
3. User signs in with organizational credentials
4. Azure AD returns token with `APP_WEB_CLIENT_ID` as audience
5. Web app requests API access token with `APP_API_SCOPE`
6. Web app includes token in API calls
7. API validates token and processes request

### Verification

```bash
# Check if environment variables are set
az containerapp show \
  --name ca-stg6fsvw-web \
  --resource-group msazaidocintstg \
  --query "properties.template.containers[0].env" \
  -o table

# Expected output should include all four variables
```

---

## 7. KEY FILES MODIFIED

### Infrastructure Files

#### `/workspaces/content-processing-solution-accelerator/infra/main.bicep`

**Line 61: Registry Parameter**
```bicep
# Before:
param publicContainerImageEndpoint string = 'cpscontainerreg.azurecr.io'

# After:
param publicContainerImageEndpoint string = 'crstg6fsvw.azurecr.io'
```

**Lines 402-408: ACR Role Assignment**
```bicep
roleAssignments: [
  {
    principalId: avmContainerRegistryReader.outputs.principalId
    roleDefinitionIdOrName: 'AcrPull'
    principalType: 'ServicePrincipal'
  }
]
```

**Lines 693-701: Managed Identity for ACR**
```bicep
module avmContainerRegistryReader 'br/public:avm/res/managed-identity/user-assigned-identity:0.4.1' = {
  name: take('avm.res.managed-identity.user-assigned-identity.${solutionSuffix}', 64)
  params: {
    name: 'id-acr-${solutionSuffix}'
    location: resourceGroupLocation
    tags: tags
    enableTelemetry: enableTelemetry
  }
}
```

**Lines 712-717: Processor App Registry Config**
```bicep
registries: [
  {
    server: publicContainerImageEndpoint
    identity: avmContainerRegistryReader.outputs.resourceId
  }
]
```

**Lines 718-723: Processor App Managed Identities**
```bicep
managedIdentities: {
  systemAssigned: true
  userAssignedResourceIds: [
    avmContainerRegistryReader.outputs.resourceId
  ]
}
```

**Lines 766-771: API App Registry Config**
```bicep
registries: [
  {
    server: publicContainerImageEndpoint
    identity: avmContainerRegistryReader.outputs.resourceId
  }
]
```

**Lines 773-778: API App Managed Identities**
```bicep
managedIdentities: {
  systemAssigned: true
  userAssignedResourceIds: [
    avmContainerRegistryReader.outputs.resourceId
  ]
}
```

**Lines 883-888: Web App Registry Config**
```bicep
registries: [
  {
    server: publicContainerImageEndpoint
    identity: avmContainerRegistryReader.outputs.resourceId
  }
]
```

**Lines 890-895: Web App Managed Identities**
```bicep
managedIdentities: {
  systemAssigned: true
  userAssignedResourceIds: [
    avmContainerRegistryReader.outputs.resourceId
  ]
}
```

**Lines 928-938: Web App Authentication Environment Variables**
```bicep
{
  name: 'APP_WEB_CLIENT_ID'
  value: 'd3b3c2ae-7f21-4d63-a046-3c14154f18a1'
}
{
  name: 'APP_WEB_AUTHORITY'
  value: '${environment().authentication.loginEndpoint}/${tenant().tenantId}'
}
{
  name: 'APP_WEB_SCOPE'
  value: 'api://445cde4d-2ab0-4d53-9a41-900716241a95/user_impersonation'
}
```

**Lines 1200-1211: Processor App Update Module (Duplicate Config)**
```bicep
# Same registry and identity configuration as initial deployment
# Ensures updates maintain correct authentication
```

**Lines 1264-1275: API App Update Module (Duplicate Config)**
```bicep
# Same registry and identity configuration as initial deployment
# Ensures updates maintain correct authentication
```

### Application Files

#### `/workspaces/content-processing-solution-accelerator/src/ContentProcessorWeb/src/Pages/DefaultPage/Components/ProcessQueueGrid/ProcessQueueGrid.tsx`

**Lines 252-273: Separated Click Handlers**
```typescript
onClick: (e: React.MouseEvent) => {
    const target = e.target as HTMLElement;
    const isCheckbox = target.closest('[role="checkbox"]');

    if (isCheckbox && !e.defaultPrevented) {
        // Checkbox click - toggle selection for bulk operations
        toggleRow(e, row.rowId);
    } else {
        // Row click - show document in center panel (not for deletion)
        const isInteractiveElement =
            target.closest('button') ||
            target.closest('[role="menuitem"]') ||
            target.closest('[role="menu"]');

        if (!isInteractiveElement && !e.defaultPrevented) {
            const item = row.item;
            const findItem = getSelectedItem(item.processId.label);
            dispatch(setSelectedGridRow({ processId: item.processId.label, item: findItem }));
        }
    }
}
```

**Lines 297-312: Simplified RenderRow Function**
```typescript
const RenderRow = ({ index, style, data }: ReactWindowRenderFnProps) => {
    const { item, selected, appearance, onClick } = data[index];
    const deleteBtnStatus = isDeleteDisabled(item.processId.label, item.status.label);

    return (
        <TableRow
            aria-rowindex={index + 2}
            style={style}
            key={item.processId.label}
            aria-selected={selected}
            onClick={onClick}  // Now uses the separated onClick handler
            appearance={appearance}
        >
            <TableSelectionCell
                role="checkbox"  // Added for proper click detection
                checked={selected}
                aria-label={`Select ${item.fileName.label}`}
            />
            {/* ... rest of the row cells ... */}
        </TableRow>
    );
};
```

**Key Changes**:
- Removed separate `handleRowClick` function
- Checkbox clicks isolated using `closest('[role="checkbox"]')` check
- Row clicks only trigger when NOT clicking checkbox, button, or menu
- Added explicit `role="checkbox"` attribute to TableSelectionCell

#### `/workspaces/content-processing-solution-accelerator/src/ContentProcessorAPI/app/routers/contentprocessor.py`

**Lines 3-4, 45-46: Added Logging**
```python
import logging

logger = logging.getLogger(__name__)
```

**Lines 521-548: Added Error Handling for Folders Endpoint**
```python
try:
    mongo_helper = CosmosMongDBHelper(
        connection_string=app_config.app_cosmos_connstr,
        db_name=app_config.app_cosmos_database,
        container_name=app_config.app_cosmos_container_process,
        indexes=[("process_id", 1)],
    )

    # Build query filter
    query = {}
    if schema_id:
        query["target_schema.Id"] = schema_id

    # Get distinct folder values
    folders = mongo_helper.get_distinct_values("folder", query=query)

    # Filter out None values and return
    folders = [f for f in folders if f is not None]

    return JSONResponse(
        status_code=200,
        content={"folders": folders},
    )
except Exception as e:
    logger.error(f"Error retrieving folders: {str(e)}")
    return JSONResponse(
        status_code=500,
        content={"error": "Failed to retrieve folders", "details": str(e)},
    )
```

**Purpose**: Added try-catch block and logging to prevent unhandled exceptions from crashing the API.

### Build and Deployment Files

#### `/workspaces/content-processing-solution-accelerator/src/ContentProcessorWeb/Makefile`
```makefile
# New file created for automated deployment
ACR_NAME := crstg6fsvw
RESOURCE_GROUP := msazaidocintstg
APP_NAME := ca-stg6fsvw-web
IMAGE_NAME := content-processor-web
TIMESTAMP := $(shell date +%s)
IMAGE_TAG := $(TIMESTAMP)
FULL_IMAGE := $(ACR_NAME).azurecr.io/$(IMAGE_NAME):$(IMAGE_TAG)
LATEST_IMAGE := $(ACR_NAME).azurecr.io/$(IMAGE_NAME):latest

.PHONY: deploy build push update-app login help clean

deploy: login build push update-app
```

#### `/workspaces/content-processing-solution-accelerator/src/ContentProcessorAPI/Makefile`
```makefile
# New file created for automated API deployment
ACR_NAME := crstg6fsvw
RESOURCE_GROUP := msazaidocintstg
APP_NAME := ca-stg6fsvw-api
IMAGE_NAME := content-processor-api
# ... similar structure to web Makefile
```

#### `/workspaces/content-processing-solution-accelerator/src/ContentProcessorWeb/README-DEPLOY.md`
```markdown
# New documentation file for deployment process
# Quick Deploy: make deploy
# Manual steps included as fallback
```

### Configuration Files

#### `/workspaces/content-processing-solution-accelerator/.gitignore`
```gitignore
# Added lines 17-19:
.claude
notes.md
updates.md
```

**Purpose**: Exclude development notes and Claude artifacts from git tracking.

---

## 8. DEPLOYMENT COMMANDS

### Order of Execution

The restoration followed this specific sequence to ensure dependencies were met:

#### Phase 1: Infrastructure Updates (Bicep)

```bash
# 1. Navigate to project root
cd /workspaces/content-processing-solution-accelerator

# 2. Update Bicep template (manual edit of main.bicep)
# - Changed publicContainerImageEndpoint parameter (line 61)
# - Added registries blocks (lines 712-717, 766-771, 883-888)
# - Added managedIdentities with user-assigned (lines 718-723, 773-778, 890-895)

# 3. Validate Bicep template
az bicep build --file infra/main.bicep

# 4. Deploy updated infrastructure (if needed)
az deployment group create \
  --resource-group msazaidocintstg \
  --template-file infra/main.bicep \
  --parameters solutionName=cps
```

#### Phase 2: ACR Role Assignment

```bash
# 5. Get managed identity principal ID
PRINCIPAL_ID=$(az identity show \
  --name id-acr-stg6fsvw \
  --resource-group msazaidocintstg \
  --query principalId -o tsv)

# 6. Get ACR resource ID
ACR_ID=$(az acr show \
  --name crstg6fsvw \
  --resource-group msazaidocintstg \
  --query id -o tsv)

# 7. Assign AcrPull role to managed identity
az role assignment create \
  --assignee $PRINCIPAL_ID \
  --role "AcrPull" \
  --scope $ACR_ID

# 8. Verify role assignment
az role assignment list \
  --assignee $PRINCIPAL_ID \
  --scope $ACR_ID \
  --query "[].{Role:roleDefinitionName,Scope:scope}" \
  -o table
```

#### Phase 3: Container App Updates

```bash
# 9. Update Container App - Processor
az containerapp update \
  --name ca-stg6fsvw-app \
  --resource-group msazaidocintstg \
  --image crstg6fsvw.azurecr.io/contentprocessor:latest \
  --query "properties.{Revision:latestRevisionName,Image:template.containers[0].image}" \
  -o table

# 10. Update Container App - API
az containerapp update \
  --name ca-stg6fsvw-api \
  --resource-group msazaidocintstg \
  --image crstg6fsvw.azurecr.io/contentprocessorapi:latest \
  --query "properties.{Revision:latestRevisionName,Image:template.containers[0].image}" \
  -o table

# 11. Update Container App - Web (initially, before rebuild)
az containerapp update \
  --name ca-stg6fsvw-web \
  --resource-group msazaidocintstg \
  --image crstg6fsvw.azurecr.io/contentprocessorweb:latest \
  --query "properties.{Revision:latestRevisionName,Image:template.containers[0].image}" \
  -o table
```

#### Phase 4: Web App Code Fix & Rebuild

```bash
# 12. Navigate to web app source
cd /workspaces/content-processing-solution-accelerator/src/ContentProcessorWeb

# 13. Edit ProcessQueueGrid.tsx (manual code changes)
# - Modified onClick handler (lines 252-273)
# - Simplified RenderRow function (lines 297-312)
# - Added role="checkbox" attribute (line 309)

# 14. Login to Azure Container Registry
az acr login --name crstg6fsvw

# 15. Build Docker image with timestamp tag
TIMESTAMP=$(date +%s)
docker build \
  -t crstg6fsvw.azurecr.io/content-processor-web:$TIMESTAMP \
  -t crstg6fsvw.azurecr.io/contentprocessorweb:$TIMESTAMP \
  -t crstg6fsvw.azurecr.io/contentprocessorweb:latest .

# 16. Push images to registry
docker push crstg6fsvw.azurecr.io/content-processor-web:$TIMESTAMP
docker push crstg6fsvw.azurecr.io/contentprocessorweb:$TIMESTAMP
docker push crstg6fsvw.azurecr.io/contentprocessorweb:latest

# 17. Update container app with new image
az containerapp update \
  --name ca-stg6fsvw-web \
  --resource-group msazaidocintstg \
  --image crstg6fsvw.azurecr.io/content-processor-web:$TIMESTAMP \
  --query "properties.{Revision:latestRevisionName,Image:template.containers[0].image}" \
  -o table
```

#### Phase 5: Verification

```bash
# 18. Check processor app status
az containerapp show \
  --name ca-stg6fsvw-app \
  --resource-group msazaidocintstg \
  --query "properties.{Status:provisioningState,Image:template.containers[0].image,Replicas:runningStatus}" \
  -o table

# 19. Check API app status and endpoint
az containerapp show \
  --name ca-stg6fsvw-api \
  --resource-group msazaidocintstg \
  --query "properties.{Status:provisioningState,FQDN:configuration.ingress.fqdn}" \
  -o table

# 20. Check web app status and endpoint
az containerapp show \
  --name ca-stg6fsvw-web \
  --resource-group msazaidocintstg \
  --query "properties.{Status:provisioningState,FQDN:configuration.ingress.fqdn}" \
  -o table

# 21. Test API endpoint
curl https://ca-stg6fsvw-api.blackplant-3f8c2e39.eastus.azurecontainerapps.io/startup

# 22. Test web endpoint (in browser)
# Open: https://ca-stg6fsvw-web.blackplant-3f8c2e39.eastus.azurecontainerapps.io

# 23. Check recent revisions
az containerapp revision list \
  --name ca-stg6fsvw-web \
  --resource-group msazaidocintstg \
  --query "[].{Name:name,Active:properties.active,Created:properties.createdTime,Traffic:properties.trafficWeight}" \
  -o table

# 24. Check container app logs (if issues)
az containerapp logs show \
  --name ca-stg6fsvw-web \
  --resource-group msazaidocintstg \
  --tail 50
```

### Automated Deployment (Using Makefile)

After initial setup, subsequent deployments can use the Makefile:

```bash
# Web app deployment
cd /workspaces/content-processing-solution-accelerator/src/ContentProcessorWeb
make deploy

# API deployment
cd /workspaces/content-processing-solution-accelerator/src/ContentProcessorAPI
make deploy

# What the Makefile does automatically:
# 1. az acr login --name crstg6fsvw
# 2. docker build -t crstg6fsvw.azurecr.io/content-processor-web:$(date +%s) .
# 3. docker push crstg6fsvw.azurecr.io/content-processor-web:$(date +%s)
# 4. az containerapp update --name ca-stg6fsvw-web --image ...
```

### Critical Notes

1. **Order Matters**: Role assignments must be in place before container apps can pull images
2. **Wait for Propagation**: After role assignment, wait 2-3 minutes for Azure RBAC to propagate
3. **Timestamp Tags**: Always use timestamp tags (not just :latest) to force Azure to pull new images
4. **Browser Cache**: Use incognito/private browsing when testing web app changes
5. **Revision History**: Azure keeps old revisions; you can rollback if needed
6. **Environment Variables**: Ensure APP_WEB_CLIENT_ID and related variables are set correctly

---

## Summary of Fixes

| Issue | Root Cause | Solution | Files Changed |
|-------|------------|----------|---------------|
| Container apps failing to start | Wrong ACR endpoint in Bicep | Changed `publicContainerImageEndpoint` to `crstg6fsvw.azurecr.io` | `infra/main.bicep` (line 61) |
| Image pull authentication failed | Missing registry auth config | Added `registries` blocks with managed identity | `infra/main.bicep` (lines 712-717, 766-771, 883-888) |
| ACR access denied | No AcrPull role assigned | Added role assignment in Bicep and via Azure CLI | `infra/main.bicep` (lines 402-408) |
| Checkbox selection broken | Click handlers interfering | Separated checkbox and row click logic | `ProcessQueueGrid.tsx` (lines 252-273, 297-312) |
| Folders endpoint crashes | Missing error handling | Added try-catch and logging | `contentprocessor.py` (lines 521-548) |
| Manual deployment tedious | No automation | Created Makefiles for one-command deploy | `Makefile` (web & API) |

---

## Testing Checklist

After applying all fixes, verify the following:

- [ ] All three container apps show "Succeeded" provisioning state
- [ ] Container apps successfully pull images from crstg6fsvw.azurecr.io
- [ ] Web app loads without authentication errors
- [ ] Users can log in with organizational credentials
- [ ] API endpoints respond successfully (test /startup endpoint)
- [ ] Checkbox selection works independently of row clicks
- [ ] Bulk delete selects multiple items correctly
- [ ] Row clicks show document preview without selecting checkbox
- [ ] Folders endpoint returns data without errors
- [ ] No 401 or 403 errors in browser console

---

## Rollback Plan

If issues occur after deployment:

1. **Revert to previous revision**:
   ```bash
   # List revisions
   az containerapp revision list --name ca-stg6fsvw-web -g msazaidocintstg

   # Activate previous revision
   az containerapp revision activate \
     --name ca-stg6fsvw-web \
     --resource-group msazaidocintstg \
     --revision <previous-revision-name>
   ```

2. **Check logs for errors**:
   ```bash
   az containerapp logs show \
     --name ca-stg6fsvw-web \
     --resource-group msazaidocintstg \
     --tail 100 \
     --follow
   ```

3. **Verify role assignments**:
   ```bash
   az role assignment list \
     --assignee <principal-id> \
     --scope <acr-resource-id> \
     -o table
   ```

---

## Future Recommendations

1. **Parameterize Registry**: Move registry name to Bicep parameters file instead of hardcoding
2. **Automated Testing**: Add smoke tests to deployment pipeline
3. **Monitoring**: Enable Application Insights for better observability
4. **CI/CD Pipeline**: Automate builds and deployments via GitHub Actions or Azure DevOps
5. **Environment Separation**: Use separate registries/apps for dev/staging/production
6. **Documentation**: Keep this document updated as infrastructure evolves

---

## Contact and Support

For questions or issues with this deployment:
- Review container app logs: `az containerapp logs show`
- Check Azure Portal for resource status
- Verify role assignments: `az role assignment list`
- Review Bicep template: `/workspaces/content-processing-solution-accelerator/infra/main.bicep`

---

**Document Version**: 1.0
**Last Updated**: 2025-11-26
**Maintained By**: Development Team
