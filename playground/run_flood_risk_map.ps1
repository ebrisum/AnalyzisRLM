<#
.SYNOPSIS
    Flood Risk Map of England – PowerShell launcher & environment setup.

.DESCRIPTION
    Sets up the Python environment, installs dependencies, and runs
    flood_risk_map_england.py to produce a static PNG map.

.EXAMPLE
    .\run_flood_risk_map.ps1
    .\run_flood_risk_map.ps1 -FloodGpkg "D:\Data\Flood_Zones.gpkg"
    .\run_flood_risk_map.ps1 -Dpi 150 -OutputName "flood_map_draft.png"
#>

param(
    [string]$FloodGpkg = "$env:USERPROFILE\Downloads\Flood\Flood_Map_for_Planning_Flood_Zones.gpkg",
    [string]$OutputDir  = $PSScriptRoot,
    [string]$OutputName = "flood_risk_map_england.png",
    [int]$Dpi           = 300,
    [string]$LadCache   = "",
    [switch]$SkipInstall
)

$ErrorActionPreference = "Stop"
$ScriptDir = $PSScriptRoot
$PythonScript = Join-Path $ScriptDir "flood_risk_map_england.py"

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  FLOOD RISK MAP OF ENGLAND – PowerShell Launcher"           -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

# ── 1. Locate Python ─────────────────────────────────────────────────
$python = $null
foreach ($cmd in @("python", "python3", "py")) {
    $found = Get-Command $cmd -ErrorAction SilentlyContinue
    if ($found) {
        $python = $found.Source
        break
    }
}
if (-not $python) {
    Write-Host "ERROR: Python not found. Install from https://www.python.org/downloads/" -ForegroundColor Red
    exit 1
}
$pyVersion = & $python --version 2>&1
Write-Host "`n  Python: $python ($pyVersion)" -ForegroundColor Green

# ── 2. Install dependencies ──────────────────────────────────────────
if (-not $SkipInstall) {
    Write-Host "`n[1/3] Installing Python dependencies..." -ForegroundColor Yellow
    $packages = @("geopandas", "matplotlib", "requests", "fiona")
    & $python -m pip install --quiet --upgrade $packages
    if ($LASTEXITCODE -ne 0) {
        Write-Host "  pip install failed. Trying with --user flag..." -ForegroundColor Yellow
        & $python -m pip install --quiet --upgrade --user $packages
    }
    Write-Host "  Dependencies installed." -ForegroundColor Green
} else {
    Write-Host "`n[1/3] Skipping dependency install (--SkipInstall)." -ForegroundColor DarkGray
}

# ── 3. Validate input file ───────────────────────────────────────────
Write-Host "`n[2/3] Validating input data..." -ForegroundColor Yellow

if (-not (Test-Path $FloodGpkg)) {
    Write-Host "  ERROR: Flood GeoPackage not found:" -ForegroundColor Red
    Write-Host "    $FloodGpkg" -ForegroundColor Red
    Write-Host "`n  Re-run with:  .\run_flood_risk_map.ps1 -FloodGpkg 'C:\path\to\file.gpkg'" -ForegroundColor Yellow
    exit 1
}

$sizeMB = [math]::Round((Get-Item $FloodGpkg).Length / 1MB, 1)
Write-Host "  Flood data: $FloodGpkg ($sizeMB MB)" -ForegroundColor Green

if (-not (Test-Path $PythonScript)) {
    Write-Host "  ERROR: Python script not found: $PythonScript" -ForegroundColor Red
    exit 1
}

# ── 4. Run the map generator ─────────────────────────────────────────
Write-Host "`n[3/3] Generating flood risk map..." -ForegroundColor Yellow

$args_list = @(
    $PythonScript,
    "--flood-gpkg", $FloodGpkg,
    "--output-dir", $OutputDir,
    "--output-name", $OutputName,
    "--dpi", $Dpi
)
if ($LadCache -and (Test-Path $LadCache)) {
    $args_list += @("--lad-cache", $LadCache)
}

& $python $args_list

if ($LASTEXITCODE -ne 0) {
    Write-Host "`n  Map generation failed (exit code $LASTEXITCODE)." -ForegroundColor Red
    exit $LASTEXITCODE
}

# ── 5. Open result ───────────────────────────────────────────────────
$outputFile = Join-Path $OutputDir $OutputName
if (Test-Path $outputFile) {
    $outSizeMB = [math]::Round((Get-Item $outputFile).Length / 1MB, 1)
    Write-Host "`n============================================================" -ForegroundColor Cyan
    Write-Host "  Map saved: $outputFile ($outSizeMB MB)"                        -ForegroundColor Green
    Write-Host "============================================================" -ForegroundColor Cyan

    $open = Read-Host "`n  Open the map now? (Y/n)"
    if ($open -ne "n") {
        Start-Process $outputFile
    }
} else {
    Write-Host "`n  WARNING: Output file not found at $outputFile" -ForegroundColor Yellow
}
