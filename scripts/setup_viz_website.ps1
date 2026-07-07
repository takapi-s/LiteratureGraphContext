# Sync CGC Playground UI sources into LGC website/ (literature-adapted fork).
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$CgcWeb = Join-Path $Root "external\CodeGraphContext\website"
$LgcWeb = Join-Path $Root "website"

if (-not (Test-Path $CgcWeb)) {
    Write-Error "CGC website not found at $CgcWeb"
}

$dirs = @(
    "src\components\ui",
    "src\lib",
    "public"
)
foreach ($d in $dirs) {
    $src = Join-Path $CgcWeb $d
    $dst = Join-Path $LgcWeb $d
    if (Test-Path $src) {
        New-Item -ItemType Directory -Force -Path $dst | Out-Null
        Copy-Item -Path (Join-Path $src "*") -Destination $dst -Recurse -Force
    }
}

$files = @(
    "package.json",
    "package-lock.json",
    "vite.config.ts",
    "tsconfig.json",
    "tsconfig.app.json",
    "tsconfig.node.json",
    "tailwind.config.ts",
    "postcss.config.js",
    "components.json",
    "eslint.config.js",
    "index.html",
    "src\index.css",
    "src\vite-env.d.ts",
    "src\components\FlowchartSVG.tsx",
    "src\components\ThemeProvider.tsx",
    "src\components\CodeGraphViewer.tsx"
)
foreach ($f in $files) {
    $src = Join-Path $CgcWeb $f
    if (Test-Path $src) {
        $dst = Join-Path $LgcWeb $f
        New-Item -ItemType Directory -Force -Path (Split-Path $dst) | Out-Null
        Copy-Item -Path $src -Destination $dst -Force
    }
}

Write-Host "Copied CGC website base into $LgcWeb"
