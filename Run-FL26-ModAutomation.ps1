# Run-FL26-ModAutomation.ps1
# Master runner - reads config and calls all assignment scripts in correct order.

param(
  [ValidateSet("DryRun","Run")][string]$Mode = "DryRun",
  [string]$ConfigPath = ".\FL26_ModAutomation.config.json",
  [string]$SingleMod  = ""   # if set, only run this one mod key
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$dry  = ($Mode -eq "DryRun")
$solo = $SingleMod.Trim()   # empty = run all

# ── helpers ───────────────────────────────────────────────────────────────────

function Read-Json([string]$p) {
  if (-not (Test-Path -LiteralPath $p)) { throw "Config not found: $p" }
  return Get-Content -LiteralPath $p -Raw | ConvertFrom-Json
}

function Invoke-Mod([string]$script, [hashtable]$scriptArgs) {
  $scriptPath = Join-Path $here $script
  if (-not (Test-Path -LiteralPath $scriptPath)) { throw "Script missing: $scriptPath" }
  Write-Host ""
  Write-Host (">>> {0}" -f $scriptPath) -ForegroundColor Yellow
  & $scriptPath @scriptArgs
}

function Get-RealPath([string]$modRoot, [string]$relPath) {
  return Join-Path $modRoot $relPath
}

function Build-AllRealPathsPipe([string[]]$roots, [string]$relPath) {
  return ($roots | ForEach-Object { Join-Path $_ $relPath }) -join "|"
}

# ── load config ───────────────────────────────────────────────────────────────
$cfg     = Read-Json $ConfigPath
$modRoot = $cfg.modRootPath
$seed    = [int]$cfg.seed
$mods    = $cfg.mods
$csvMain = Join-Path $here $cfg.masterPlayerCsv
$relReal = "Asset\model\character\face\real"

if (-not (Test-Path -LiteralPath $modRoot -PathType Container)) {
  throw "Mod root folder not found: $modRoot"
}
if (-not (Test-Path -LiteralPath $csvMain -PathType Leaf)) {
  throw "Master player CSV not found: $csvMain"
}

Write-Host ""
Write-Host ("Mod root : {0}" -f $modRoot) -ForegroundColor Green
Write-Host ("Mode     : {0}" -f $Mode)    -ForegroundColor Green
if ($solo) {
  Write-Host ("SingleMod: {0}" -f $solo)  -ForegroundColor Cyan
}
Write-Host ""

# ── build real paths for disk-scan exclusions ─────────────────────────────────

# All grip sox real paths (for cross-exclusion)
$gripSoxRoots = @(
  (Join-Path $modRoot "Grip Sock-Brands"),
  (Join-Path $modRoot "Grip Sock-Dual Color All Teams"),
  (Join-Path $modRoot "Grip Sock-Long"),
  (Join-Path $modRoot "Grip Sock-Short")
) | Where-Object { Test-Path -LiteralPath $_ -PathType Container }

# All sock real paths (for cross-exclusion)
$sockHolesReal    = Join-Path (Join-Path $modRoot "Sock-Holes")       $relReal
$sockMidHighReal  = Join-Path (Join-Path $modRoot "Sock-Middle High") $relReal
$sockShortRoots   = @(
  (Join-Path $modRoot "Sock-Short"),
  (Join-Path $modRoot "Sock-Extreme Short"),
  (Join-Path $modRoot "Sock-Shinpads V1"),
  (Join-Path $modRoot "Sock-Shinpads V2")
) | Where-Object { Test-Path -LiteralPath $_ -PathType Container }
$allSockRealPaths = @(@($sockHolesReal, $sockMidHighReal) + ($sockShortRoots | ForEach-Object { Join-Path $_ $relReal })) | Where-Object { $_ -ne '' }

# All pants real paths (for cross-exclusion)
$pantsRoots = @(
  (Join-Path $modRoot "Pants-Baggy"),
  (Join-Path $modRoot "Pants-Extra Baggy"),
  (Join-Path $modRoot "Pants-Shorter")
) | Where-Object { Test-Path -LiteralPath $_ -PathType Container }
$allPantsRealPaths = @($pantsRoots | ForEach-Object { Join-Path $_ $relReal })

# ═════════════════════════════════════════════════════════════════════════════
# GRIP SOX — run Dual Color, Long, Short first; Brands last
# ═════════════════════════════════════════════════════════════════════════════

if (-not $solo -or $solo -in @("gripSoxDualColor","gripSoxLong","gripSoxShort")) {
foreach ($modKey in @("gripSoxDualColor","gripSoxLong","gripSoxShort")) {
  $mod = $mods.$modKey
  if (-not $mod -or -not $mod.enabled) { continue }

  $modFolder = Join-Path $modRoot $mod.folderName
  if (-not (Test-Path -LiteralPath $modFolder -PathType Container)) {
    Write-Host ("[WARN] Skipping {0} - folder not found." -f $mod.folderName) -ForegroundColor DarkYellow
    continue
  }

  # Other grip sox roots for exclusion (all except this one)
  $otherRoots = @($gripSoxRoots | Where-Object { $_ -ne $modFolder })

  $mArgs = @{
    CsvPath                = $csvMain
    RootPath               = $modFolder
    OtherGripSoxRootsPipe  = ($otherRoots -join "|")
    LogFileName            = ("{0}_Assignments.csv" -f $mod.logPrefix)
    Percent                = [int]$mod.percent
    Seed                   = $seed
  }
  if ($mod.manualPlayerIds -and $mod.manualPlayerIds.Count -gt 0) {
    $mArgs["ManualPlayerIds"] = @($mod.manualPlayerIds)
  }
  if ($dry) { $mArgs["DryRun"] = $true }

  Invoke-Mod "Assign-GripSox-Single.ps1" $mArgs
}
} # end SingleMod gripSox group

# Grip Sox Brands (runs last, excludes players in other grip sox folders)
if ((-not $solo -or $solo -eq "gripSoxBrands") -and $mods.gripSoxBrands -and $mods.gripSoxBrands.enabled) {
  $modFolder  = Join-Path $modRoot "Grip Sock-Brands"
  $otherRoots = @($gripSoxRoots | Where-Object { $_ -ne $modFolder })

  if (Test-Path -LiteralPath $modFolder -PathType Container) {
    $mArgs = @{
      CsvPath               = $csvMain
      RootPath              = $modFolder
      OtherGripSoxRootsPipe = ($otherRoots -join "|")
      Mode                  = [string]$mods.gripSoxBrands.mode
      Percent               = [int]$mods.gripSoxBrands.percent
      Seed                  = $seed
    }
    if ($mods.gripSoxBrands.manualPlayerIds -and $mods.gripSoxBrands.manualPlayerIds.Count -gt 0) {
      $mArgs["ManualPlayerIds"] = @($mods.gripSoxBrands.manualPlayerIds)
    }
    if ($dry) { $mArgs["DryRun"] = $true }
    Invoke-Mod "Assign-GripSox-Brands.ps1" $mArgs
  } else {
    Write-Host "[WARN] Skipping Grip Sock-Brands - folder not found." -ForegroundColor DarkYellow
  }
}

# ═════════════════════════════════════════════════════════════════════════════
# SOCKS — Holes first (priority), then Middle High, then Short group
# ═════════════════════════════════════════════════════════════════════════════

$allSockRealPipe = $allSockRealPaths -join "|"

if (-not $solo -or $solo -in @("sockHoles","sockMiddleHigh","sockShortGroup")) {
foreach ($modKey in @("sockHoles","sockMiddleHigh","sockShortGroup")) {
  $mod = $mods.$modKey
  if (-not $mod -or -not $mod.enabled) { continue }

  $modFolder = Join-Path $modRoot $mod.folderName
  if (-not (Test-Path -LiteralPath $modFolder -PathType Container)) {
    Write-Host ("[WARN] Skipping {0} - folder not found." -f $mod.folderName) -ForegroundColor DarkYellow
    continue
  }

  $mArgs = @{
    CsvPath              = $csvMain
    RootPath             = $modFolder
    AllSockRealPathsPipe = $allSockRealPipe
    ModName              = $mod.folderName
    LogFileName          = ("{0}_Assignments.csv" -f $mod.logPrefix)
    Percent              = [int]$mod.percent
    Seed                 = $seed
  }
  if ($mod.manualPlayerIds -and $mod.manualPlayerIds.Count -gt 0) {
    $mArgs["ManualPlayerIds"] = @($mod.manualPlayerIds)
  }
  if ($dry) { $mArgs["DryRun"] = $true }

  Invoke-Mod "Assign-Socks.ps1" $mArgs
}
} # end SingleMod socks group

# ═════════════════════════════════════════════════════════════════════════════
# PANTS — each mod scans all pants folders on disk before assigning
# ═════════════════════════════════════════════════════════════════════════════

$allPantsRealPipe = $allPantsRealPaths -join "|"

if (-not $solo -or $solo -in @("pantsBaggy","pantsExtraBaggy","pantsShorter")) {
foreach ($modKey in @("pantsBaggy","pantsExtraBaggy","pantsShorter")) {
  $mod = $mods.$modKey
  if (-not $mod -or -not $mod.enabled) { continue }

  $modFolder = Join-Path $modRoot $mod.folderName
  if (-not (Test-Path -LiteralPath $modFolder -PathType Container)) {
    Write-Host ("[WARN] Skipping {0} - folder not found." -f $mod.folderName) -ForegroundColor DarkYellow
    continue
  }

  $mArgs = @{
    CsvPath               = $csvMain
    RootPath              = $modFolder
    AllPantsRealPathsPipe = $allPantsRealPipe
    ModName               = $mod.folderName
    LogFileName           = ("{0}_Assignments.csv" -f $mod.logPrefix)
    Percent               = [int]$mod.percent
    Seed                  = $seed
  }
  if ($mod.manualPlayerIds -and $mod.manualPlayerIds.Count -gt 0) {
    $mArgs["ManualPlayerIds"] = @($mod.manualPlayerIds)
  }
  if ($dry) { $mArgs["DryRun"] = $true }

  Invoke-Mod "Assign-Pants.ps1" $mArgs
}
} # end SingleMod pants group

# ═════════════════════════════════════════════════════════════════════════════
# GLOVES
# ═════════════════════════════════════════════════════════════════════════════

if ((-not $solo -or $solo -eq "glovesBrands") -and $mods.glovesBrands -and $mods.glovesBrands.enabled) {
  $modFolder = Join-Path $modRoot "Gloves-Brands"
  if (Test-Path -LiteralPath $modFolder -PathType Container) {
    $mArgs = @{
      CsvPath   = $csvMain
      RootPath  = $modFolder
      Mode      = [string]$mods.glovesBrands.mode
      Percent   = [int]$mods.glovesBrands.percent
      Seed      = $seed
    }
    if ($mods.glovesBrands.excludeBrands) { $mArgs["ExcludeBrands"] = @($mods.glovesBrands.excludeBrands) }
    if ($mods.glovesBrands.manualPlayerIds -and $mods.glovesBrands.manualPlayerIds.Count -gt 0) {
      $mArgs["ManualPlayerIds"] = @($mods.glovesBrands.manualPlayerIds)
    }
    if ($dry) { $mArgs["DryRun"] = $true }
    Invoke-Mod "Assign-Gloves.ps1" $mArgs
  } else {
    Write-Host "[WARN] Skipping Gloves-Brands - folder not found." -ForegroundColor DarkYellow
  }
}

# ═════════════════════════════════════════════════════════════════════════════
# HANDTAPE — only runs if manually triggered (not part of batch run)
# ═════════════════════════════════════════════════════════════════════════════
# Handtape is always run individually from the UI, not in batch.

# ═════════════════════════════════════════════════════════════════════════════
# VALIDATE
# ═════════════════════════════════════════════════════════════════════════════

Write-Host ""
if (-not $solo) {
  & (Join-Path $here "Validate-Assignments.ps1") -Here $here
}

Write-Host ""
Write-Host ("All done. Mode={0}" -f $Mode) -ForegroundColor Green
