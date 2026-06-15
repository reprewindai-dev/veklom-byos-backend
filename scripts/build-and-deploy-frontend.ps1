# Veklom Frontend Build and Deploy Script
# Builds veklom-control-plane and deploys to production
# Usage: .\scripts\build-and-deploy-frontend.ps1

param(
    [switch]$SkipBuild = $false,
    [switch]$SkipDeploy = $false,
    [switch]$VerifyOnly = $false
)

$ErrorActionPreference = "Stop"

# Paths
$FrontendSource = "C:\Users\antho\OneDrive\Desktop\veklom-control-plane"
$BackendRepo = "C:\Users\antho\.windsurf\veklom-byos-backend-2"
$DeployTarget = "$BackendRepo\frontend\sovereign-control-node"
$ServerIP = "5.78.135.11"
$SSHKey = "$env:USERPROFILE\.ssh\veklom-deploy"

Write-Host "=== Veklom Frontend Build & Deploy ===" -ForegroundColor Cyan
Write-Host "Frontend Source: $FrontendSource"
Write-Host "Backend Target: $DeployTarget"
Write-Host "Server: $ServerIP"
Write-Host ""

# Step 1: Build Frontend
if (-not $SkipBuild -and -not $VerifyOnly) {
    Write-Host "Step 1: Building frontend..." -ForegroundColor Yellow
    
    Set-Location $FrontendSource
    
    # Install dependencies if needed
    if (-not (Test-Path "node_modules")) {
        Write-Host "Installing npm dependencies..."
        npm install
    }
    
    # Clean previous build
    if (Test-Path "out") {
        Write-Host "Cleaning previous build..."
        Remove-Item -Recurse -Force "out"
    }
    
    # Build
    Write-Host "Running npm run build..."
    $env:NEXT_PUBLIC_BASE_PATH = "/control-plane-next"
    npm run build
    
    if (-not (Test-Path "out")) {
        throw "Build failed - no out/ directory created"
    }
    
    Write-Host "Build successful!" -ForegroundColor Green
    Write-Host ""
}

# Step 2: Sync to Backend Repo
if (-not $SkipDeploy -and -not $VerifyOnly) {
    Write-Host "Step 2: Syncing build to backend repo..." -ForegroundColor Yellow
    
    # Ensure target exists
    if (-not (Test-Path $DeployTarget)) {
        New-Item -ItemType Directory -Path $DeployTarget -Force
    }
    
    # Use robocopy for reliable sync
    Write-Host "Syncing with robocopy..."
    robocopy "$FrontendSource\out" $DeployTarget /MIR /R:3 /W:5 /NDL /NFL /NJH /NJS
    
    if ($LASTEXITCODE -ge 8) {
        throw "Robocopy failed with exit code $LASTEXITCODE"
    }
    
    Write-Host "Sync complete!" -ForegroundColor Green
    Write-Host ""
}

# Step 3: Git Commit and Push (if changes detected)
if (-not $SkipDeploy -and -not $VerifyOnly) {
    Write-Host "Step 3: Committing changes..." -ForegroundColor Yellow
    
    Set-Location $BackendRepo
    
    # Check for changes
    $status = git status --porcelain
    if ($status) {
        Write-Host "Changes detected, committing..."
        git add frontend/sovereign-control-node/
        git commit -m "Update control-plane-next frontend build $(Get-Date -Format 'yyyy-MM-dd HH:mm')"
        git push origin main
        Write-Host "Pushed to GitHub! Coolify will auto-deploy." -ForegroundColor Green
    } else {
        Write-Host "No changes to commit (build matches current)" -ForegroundColor Yellow
    }
    Write-Host ""
}

# Step 4: Verify Deployment
Write-Host "Step 4: Verifying deployment..." -ForegroundColor Yellow

# Wait for deployment
Write-Host "Waiting 30s for deployment to propagate..."
Start-Sleep -Seconds 30

# Health check
$healthUrl = "https://veklom.com/health"
try {
    $response = Invoke-RestMethod -Uri $healthUrl -TimeoutSec 10
    Write-Host "Health check: $($response.status)" -ForegroundColor Green
} catch {
    Write-Host "Health check FAILED: $_" -ForegroundColor Red
}

# Check buildId in HTML
$controlPlaneUrl = "https://veklom.com/control-plane-next/"
try {
    $html = Invoke-RestMethod -Uri $controlPlaneUrl -TimeoutSec 10
    if ($html -match 'buildId["\']?\s*[:=]\s*["\']([^"\']+)') {
        $buildId = $matches[1]
        Write-Host "Current buildId: $buildId" -ForegroundColor Green
    } else {
        Write-Host "Could not extract buildId from HTML" -ForegroundColor Yellow
    }
} catch {
    Write-Host "Failed to fetch control-plane-next: $_" -ForegroundColor Red
}

Write-Host ""
Write-Host "=== Deploy Complete ===" -ForegroundColor Cyan
Write-Host "Verify at: https://veklom.com/control-plane-next/"
Write-Host "Health: https://veklom.com/health"
