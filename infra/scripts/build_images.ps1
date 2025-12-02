# PowerShell script to build and push container images
# Used by azd predeploy hook on Windows

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "Building container images from source..." -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

# Get environment variables from azd
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

# Get script directory and repo root
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = Resolve-Path (Join-Path $scriptDir "../..")

Write-Host "Repository root: $repoRoot" -ForegroundColor Yellow
Write-Host "Registry: $registry" -ForegroundColor Yellow
Write-Host ""

# Login to ACR
Write-Host "Logging into Azure Container Registry..." -ForegroundColor Cyan
az acr login --name $registryName
if ($LASTEXITCODE -ne 0) {
    Write-Host "✗ Failed to login to ACR" -ForegroundColor Red
    exit 1
}
Write-Host "✓ Logged in successfully" -ForegroundColor Green
Write-Host ""

# Build and push ContentProcessorAPI
Write-Host "Building ContentProcessorAPI..." -ForegroundColor Cyan
docker build `
    -t "$registry/contentprocessorapi:latest" `
    -f "$repoRoot/src/ContentProcessorAPI/Dockerfile" `
    "$repoRoot/src/ContentProcessorAPI"
if ($LASTEXITCODE -ne 0) {
    Write-Host "✗ Failed to build ContentProcessorAPI" -ForegroundColor Red
    exit 1
}
Write-Host "Pushing ContentProcessorAPI..." -ForegroundColor Cyan
docker push "$registry/contentprocessorapi:latest"
if ($LASTEXITCODE -ne 0) {
    Write-Host "✗ Failed to push ContentProcessorAPI" -ForegroundColor Red
    exit 1
}
Write-Host "✓ ContentProcessorAPI built and pushed" -ForegroundColor Green
Write-Host ""

# Build and push ContentProcessor
Write-Host "Building ContentProcessor..." -ForegroundColor Cyan
docker build `
    -t "$registry/contentprocessor:latest" `
    -f "$repoRoot/src/ContentProcessor/Dockerfile" `
    "$repoRoot/src/ContentProcessor"
if ($LASTEXITCODE -ne 0) {
    Write-Host "✗ Failed to build ContentProcessor" -ForegroundColor Red
    exit 1
}
Write-Host "Pushing ContentProcessor..." -ForegroundColor Cyan
docker push "$registry/contentprocessor:latest"
if ($LASTEXITCODE -ne 0) {
    Write-Host "✗ Failed to push ContentProcessor" -ForegroundColor Red
    exit 1
}
Write-Host "✓ ContentProcessor built and pushed" -ForegroundColor Green
Write-Host ""

# Build and push ContentProcessorWeb
Write-Host "Building ContentProcessorWeb..." -ForegroundColor Cyan
docker build `
    -t "$registry/contentprocessorweb:latest" `
    -f "$repoRoot/src/ContentProcessorWeb/Dockerfile" `
    "$repoRoot/src/ContentProcessorWeb"
if ($LASTEXITCODE -ne 0) {
    Write-Host "✗ Failed to build ContentProcessorWeb" -ForegroundColor Red
    exit 1
}
Write-Host "Pushing ContentProcessorWeb..." -ForegroundColor Cyan
docker push "$registry/contentprocessorweb:latest"
if ($LASTEXITCODE -ne 0) {
    Write-Host "✗ Failed to push ContentProcessorWeb" -ForegroundColor Red
    exit 1
}
Write-Host "✓ ContentProcessorWeb built and pushed" -ForegroundColor Green
Write-Host ""

Write-Host "==========================================" -ForegroundColor Green
Write-Host "All images built and pushed successfully!" -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Images available:" -ForegroundColor Yellow
Write-Host "  - $registry/contentprocessorapi:latest" -ForegroundColor Yellow
Write-Host "  - $registry/contentprocessor:latest" -ForegroundColor Yellow
Write-Host "  - $registry/contentprocessorweb:latest" -ForegroundColor Yellow
Write-Host ""
