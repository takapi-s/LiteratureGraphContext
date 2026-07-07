# Build Playground UI and sync into Python package bundle.
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Website = Join-Path $Root "website"
$Dist = Join-Path $Website "dist"
$Target = Join-Path $Root "src\litgraph\viz\dist"

Push-Location $Website
try {
    if (-not (Test-Path "node_modules")) {
        npm ci
    }
    npm run build
} finally {
    Pop-Location
}

if (-not (Test-Path (Join-Path $Dist "index.html"))) {
    Write-Error "Build failed: website/dist/index.html not found"
}

if (Test-Path $Target) {
    Remove-Item $Target -Recurse -Force
}
Copy-Item $Dist $Target -Recurse
Write-Host "Synced viz bundle to $Target"
