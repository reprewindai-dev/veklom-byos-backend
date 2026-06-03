# scripts/veklom-finalize-local.ps1

$UserRoot = $env:USERPROFILE

$OpenClawHome = $env:OPENCLAW_HOME
if (-not $OpenClawHome) { $OpenClawHome = Join-Path $UserRoot ".openclaw" }

$NpmGlobal = $env:NPM_CONFIG_PREFIX
if (-not $NpmGlobal) { $NpmGlobal = Join-Path $UserRoot ".npm-global" }

$ExpoHome = $env:EXPO_HOME
if (-not $ExpoHome) { $ExpoHome = Join-Path $UserRoot ".expo" }

$DockerConfig = $env:DOCKER_CONFIG
if (-not $DockerConfig) { $DockerConfig = Join-Path $UserRoot ".docker" }

$VeklomHome = Join-Path $UserRoot ".veklom"
$BackroomHome = Join-Path $VeklomHome "backroom"
$MarketplaceHome = Join-Path $VeklomHome "marketplace"
$TerminalHome = Join-Path $VeklomHome "terminal"

$dirs = @(
  $OpenClawHome,
  $NpmGlobal,
  $ExpoHome,
  $DockerConfig,
  $VeklomHome,
  $BackroomHome,
  $MarketplaceHome,
  $TerminalHome
)

foreach ($d in $dirs) {
  if (-not (Test-Path $d)) {
    New-Item -ItemType Directory -Force -Path $d | Out-Null
    Write-Host "Created directory: $d"
  } else {
    Write-Host "Directory already exists: $d"
  }
}

# Copy only safe artifacts if they exist
if (Test-Path ".\dist\terminal") {
  Copy-Item ".\dist\terminal\*" $TerminalHome -Recurse -Force -ErrorAction SilentlyContinue
  Write-Host "Copied terminal distribution artifacts to $TerminalHome"
}
if (Test-Path ".\marketplace\catalog.json") {
  Copy-Item ".\marketplace\catalog.json" $MarketplaceHome -Force -ErrorAction SilentlyContinue
  Write-Host "Copied marketplace catalog.json to $MarketplaceHome"
}
if (Test-Path ".\agents\skills") {
  Copy-Item ".\agents\skills\*" (Join-Path $OpenClawHome "skills") -Recurse -Force -ErrorAction SilentlyContinue
  Write-Host "Copied agents skills to $(Join-Path $OpenClawHome 'skills')"
}

Write-Host "Veklom local operator build finalized."
Write-Host "OpenClaw: $OpenClawHome"
Write-Host "NPM global: $NpmGlobal"
Write-Host "Expo: $ExpoHome"
Write-Host "Docker config: $DockerConfig"
Write-Host "Veklom home: $VeklomHome"
