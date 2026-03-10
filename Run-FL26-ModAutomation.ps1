# Run-FL26-ModAutomation.ps1
# Master runner - reads config and calls all assignment scripts in correct order.

param(
  [ValidateSet("DryRun","Run")][string]$Mode = "DryRun",
  [string]$ConfigPath = ".\FL26_ModAutomation.config.json",
  [string]$SingleMod  = ""
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$dry  = ($Mode -eq "DryRun")
$solo = $SingleMod.Trim()

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

function Get-ManualIds($mod) {
  if ($mod -and $mod.PSObject.Properties.Name -contains 'manualPlayerIds' -and $mod.manualPlayerIds) {
    [string[]]$ids = @($mod.manualPlayerIds | ForEach-Object { "$_" } | Where-Object { $_ -match '^\d+$' })
    return $ids
  }
  return [string[]]@()
}

$cfg     = Read-Json $ConfigPath
$modRoot = $cfg.modRootPath
$seed    = [int]$cfg.seed
$mods    = $cfg.mods
$grouped = if ($cfg.PSObject.Properties.Name -contains 'grouped') { $cfg.grouped } else { $null }
$csvMain = Join-Path $here $cfg.masterPlayerCsv
$relReal = "Asset\model\character\face\real"

if (-not (Test-Path -LiteralPath $modRoot -PathType Container)) { throw "Mod root not found: $modRoot" }
if (-not (Test-Path -LiteralPath $csvMain -PathType Leaf))      { throw "Master CSV not found: $csvMain" }

Write-Host ""
Write-Host ("Mod root : {0}" -f $modRoot) -ForegroundColor Green
Write-Host ("Mode     : {0}" -f $Mode)    -ForegroundColor Green
if ($solo) { Write-Host ("SingleMod: {0}" -f $solo) -ForegroundColor Cyan }
Write-Host ""

# ── exclusion path arrays ─────────────────────────────────────────────────────

$gripSoxRoots = @(
  (Join-Path $modRoot "Grip Sock-Brands"),
  (Join-Path $modRoot "Grip Sock-Dual Color All Teams"),
  (Join-Path $modRoot "Grip Sock-Extra Long"),
  (Join-Path $modRoot "Grip Sock-Long"),
  (Join-Path $modRoot "Grip Sock-Short")
) | Where-Object { Test-Path -LiteralPath $_ -PathType Container }

$sockShortRoots = @(
  (Join-Path $modRoot "Sock-Short"),
  (Join-Path $modRoot "Sock-Extreme Short"),
  (Join-Path $modRoot "Sock-Shinpads V1"),
  (Join-Path $modRoot "Sock-Shinpads V2")
) | Where-Object { Test-Path -LiteralPath $_ -PathType Container }

$allSockRealPaths = @(
  (Join-Path (Join-Path $modRoot "Sock-Holes")       $relReal),
  (Join-Path (Join-Path $modRoot "Sock-Middle High") $relReal)
) + @($sockShortRoots | ForEach-Object { Join-Path $_ $relReal }) | Where-Object { $_ -ne '' }

$pantsRoots = @(
  (Join-Path $modRoot "Pants-Baggy"),
  (Join-Path $modRoot "Pants-Extra Baggy"),
  (Join-Path $modRoot "Pants-Shorter")
) | Where-Object { Test-Path -LiteralPath $_ -PathType Container }
$allPantsRealPaths = @($pantsRoots | ForEach-Object { Join-Path $_ $relReal })

$allSockRealPipe  = $allSockRealPaths  -join "|"
$allPantsRealPipe = $allPantsRealPaths -join "|"

# ── Grip Sox Brands ───────────────────────────────────────────────────────────

if ((-not $solo -or $solo -eq "gripSoxBrands") -and $mods.gripSoxBrands -and $mods.gripSoxBrands.enabled) {
  $modFolder  = Join-Path $modRoot "Grip Sock-Brands"
  $otherRoots = @($gripSoxRoots | Where-Object { $_ -ne $modFolder })
  if (Test-Path -LiteralPath $modFolder -PathType Container) {
    $m     = $mods.gripSoxBrands
    $base  = @{
      CsvPath               = $csvMain
      RootPath              = $modFolder
      OtherGripSoxRootsPipe = ($otherRoots -join "|")
      Seed                  = $seed
    }
    $perVar = $m.PSObject.Properties.Name -contains 'perVariationMode' -and $m.perVariationMode
    if ($perVar -and $m.PSObject.Properties.Name -contains 'variationSettings') {
      foreach ($brand in $m.variationSettings.PSObject.Properties) {
        $vs = $brand.Value; $varArgs = $base.Clone()
        $varArgs["Brands"]  = @($brand.Name)
        $varArgs["Percent"] = [int]$vs.percent
        $varArgs["Mode"]    = "Balanced"
        if ($vs.PSObject.Properties.Name -contains 'manualIds' -and $vs.manualIds -and $vs.manualIds.Count -gt 0) {
          $varArgs["ManualPlayerIds"] = @($vs.manualIds)
        }
        if ($dry) { $varArgs["DryRun"] = $true }
        Invoke-Mod "Assign-GripSox-Brands.ps1" $varArgs
      }
    } else {
      $base["Mode"]    = [string]$m.mode
      $base["Percent"] = [int]$m.percent
      if ($m.PSObject.Properties.Name -contains 'brands' -and $m.brands -and $m.brands.Count -gt 0) {
        $base["Brands"] = @($m.brands)
      }
      $manIds = Get-ManualIds $m
      if ($manIds -and @($manIds).Count -gt 0) { $base["ManualPlayerIds"] = @($manIds) }
      if ($dry) { $base["DryRun"] = $true }
      Invoke-Mod "Assign-GripSox-Brands.ps1" $base
    }
  } else {
    Write-Host "[WARN] Skipping Grip Sock-Brands - folder not found." -ForegroundColor DarkYellow
  }
}

# ═════════════════════════════════════════════════════════════════════════════
# SOCKS
# ═════════════════════════════════════════════════════════════════════════════

$sockKeys = @("sockHoles","sockMiddleHigh","sockShortGroup")

if (-not $solo -or $solo -in $sockKeys) {
  foreach ($modKey in $sockKeys) {
    if ($solo -and $solo -ne $modKey) { continue }
    $mod = $mods.$modKey
    if (-not $mod -or -not $mod.enabled) { continue }
    $modFolder = Join-Path $modRoot $mod.folderName
    if (-not (Test-Path -LiteralPath $modFolder -PathType Container)) {
      Write-Host ("[WARN] Skipping {0} - folder not found." -f $mod.folderName) -ForegroundColor DarkYellow
      continue
    }
    $perVar = $mod.PSObject.Properties.Name -contains 'perVariationMode' -and $mod.perVariationMode
    if ($perVar -and $mod.PSObject.Properties.Name -contains 'variationSettings') {
      foreach ($tmpl in $mod.variationSettings.PSObject.Properties) {
        $vs = $tmpl.Value; $varFolderName = $tmpl.Name
        # For sockShortGroup, each variation name IS the folder name at mod root
        if ($modKey -eq "sockShortGroup") {
          $varFolder = Join-Path $modRoot $varFolderName
        } else {
          $varFolder = $modFolder
        }
        if (-not (Test-Path -LiteralPath $varFolder -PathType Container)) {
          Write-Host ("[WARN] Skipping variation {0} - folder not found." -f $varFolderName) -ForegroundColor DarkYellow
          continue
        }
        $mArgs = @{
          CsvPath              = $csvMain
          RootPath             = $varFolder
          AllSockRealPathsPipe = $allSockRealPipe
          ModName              = $varFolderName
          LogFileName          = ("{0}_{1}_Assignments.csv" -f $mod.logPrefix, ($varFolderName -replace '[^a-zA-Z0-9]','_'))
          Percent              = [int]$vs.percent
          Seed                 = $seed
        }
        if ($vs.PSObject.Properties.Name -contains 'manualIds' -and $vs.manualIds) {
          [string[]]$varManIds = @($vs.manualIds | ForEach-Object { "$_" } | Where-Object { $_ -match '^\d+$' })
          if ($varManIds -and @($varManIds).Count -gt 0) { $mArgs["ManualPlayerIds"] = $varManIds }
        }
        if ($dry) { $mArgs["DryRun"] = $true }
        Invoke-Mod "Assign-Socks.ps1" $mArgs
      }
    } else {
      $mArgs = @{
        CsvPath              = $csvMain
        RootPath             = $modFolder
        AllSockRealPathsPipe = $allSockRealPipe
        ModName              = $mod.folderName
        LogFileName          = ("{0}_Assignments.csv" -f $mod.logPrefix)
        Percent              = [int]$mod.percent
        Seed                 = $seed
      }
      $manIds = Get-ManualIds $mod
      if ($manIds -and @($manIds).Count -gt 0) { $mArgs["ManualPlayerIds"] = @($manIds) }
      if ($dry) { $mArgs["DryRun"] = $true }
      Invoke-Mod "Assign-Socks.ps1" $mArgs
    }
  }
}

# ═════════════════════════════════════════════════════════════════════════════
# PANTS
# ═════════════════════════════════════════════════════════════════════════════

$pantsKeys = @("pantsBaggy","pantsExtraBaggy","pantsShorter")

if (-not $solo -or $solo -in $pantsKeys) {
  foreach ($modKey in $pantsKeys) {
    if ($solo -and $solo -ne $modKey) { continue }
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
    $manIds = Get-ManualIds $mod
    if ($manIds -and @($manIds).Count -gt 0) { $mArgs["ManualPlayerIds"] = @($manIds) }
    if ($dry) { $mArgs["DryRun"] = $true }
    Invoke-Mod "Assign-Pants.ps1" $mArgs
  }
}

# ═════════════════════════════════════════════════════════════════════════════
# SHIRT (independent)
# ═════════════════════════════════════════════════════════════════════════════

if ((-not $solo -or $solo -eq "shirtBaggy") -and
    $mods.PSObject.Properties.Name -contains 'shirtBaggy' -and
    $mods.shirtBaggy -and $mods.shirtBaggy.enabled) {
  $mod       = $mods.shirtBaggy
  $modFolder = Join-Path $modRoot $mod.folderName
  if (Test-Path -LiteralPath $modFolder -PathType Container) {
    $mArgs = @{
      CsvPath     = $csvMain
      RootPath    = $modFolder
      LogFileName = ("{0}_Assignments.csv" -f $mod.logPrefix)
      Percent     = [int]$mod.percent
      Seed        = $seed
    }
    $manIds = Get-ManualIds $mod
    if ($manIds -and @($manIds).Count -gt 0) { $mArgs["ManualPlayerIds"] = @($manIds) }
    if ($dry) { $mArgs["DryRun"] = $true }
    Invoke-Mod "Assign-Shirt.ps1" $mArgs
  } else {
    Write-Host "[WARN] Skipping Shirt-Baggy - folder not found." -ForegroundColor DarkYellow
  }
}

# ═════════════════════════════════════════════════════════════════════════════
# GLOVES
# ═════════════════════════════════════════════════════════════════════════════

if ((-not $solo -or $solo -eq "glovesBrands") -and $mods.glovesBrands -and $mods.glovesBrands.enabled) {
  $modFolder = Join-Path $modRoot "Gloves-Brands"
  if (Test-Path -LiteralPath $modFolder -PathType Container) {
    $m    = $mods.glovesBrands
    $base = @{ CsvPath=$csvMain; RootPath=$modFolder; Seed=$seed }
    if ($m.PSObject.Properties.Name -contains 'excludeBrands' -and $m.excludeBrands) {
      $base["ExcludeBrands"] = @($m.excludeBrands)
    }
    $perVar = $m.PSObject.Properties.Name -contains 'perVariationMode' -and $m.perVariationMode
    if ($perVar -and $m.PSObject.Properties.Name -contains 'variationSettings') {
      foreach ($brand in $m.variationSettings.PSObject.Properties) {
        $vs = $brand.Value; $varArgs = $base.Clone()
        if ($varArgs.ContainsKey("ExcludeBrands")) { $varArgs.Remove("ExcludeBrands") }
        $varArgs["Brands"]  = @($brand.Name)
        $varArgs["Percent"] = [int]$vs.percent
        $varArgs["Mode"]    = "Balanced"
        if ($vs.PSObject.Properties.Name -contains 'manualIds' -and $vs.manualIds -and $vs.manualIds.Count -gt 0) {
          $varArgs["ManualPlayerIds"] = @($vs.manualIds)
        }
        if ($dry) { $varArgs["DryRun"] = $true }
        Invoke-Mod "Assign-Gloves.ps1" $varArgs
      }
    } else {
      $base["Mode"]    = [string]$m.mode
      $base["Percent"] = [int]$m.percent
      $manIds = Get-ManualIds $m
      if ($manIds -and @($manIds).Count -gt 0) { $base["ManualPlayerIds"] = @($manIds) }
      if ($dry) { $base["DryRun"] = $true }
      Invoke-Mod "Assign-Gloves.ps1" $base
    }
  } else {
    Write-Host "[WARN] Skipping Gloves-Brands - folder not found." -ForegroundColor DarkYellow
  }
}

# ═════════════════════════════════════════════════════════════════════════════
# GROUPED: Grip Sock Length
# Each variation is its own top-level folder (Grip Sock-Long, Grip Sock-Short, etc.)
# Mutually exclusive with each other and with Grip Sock-Brands.
# ═════════════════════════════════════════════════════════════════════════════

if (-not $solo -or $solo -eq "gripSoxLength") {
  if ($grouped -and ($grouped.PSObject.Properties.Name -contains 'gripSoxLength')) {
    $grp = $grouped.gripSoxLength
    if ($grp.enabled) {
      $varFolders = @(Get-ChildItem -LiteralPath $modRoot -Directory -ErrorAction SilentlyContinue |
        Where-Object { $_.Name.StartsWith("Grip Sock-") -and $_.Name -ne "Grip Sock-Brands" })

      if ($varFolders.Count -eq 0) {
        Write-Host "[WARN] No Grip Sock length folders found." -ForegroundColor DarkYellow
      } else {
        $perVar = $grp.PSObject.Properties.Name -contains 'perVariationMode' -and $grp.perVariationMode

        foreach ($vf in $varFolders) {
          $varLabel = $vf.Name.Substring("Grip Sock-".Length)
          $pct      = [int]$grp.percent
          $manIds   = Get-ManualIds $grp

          if ($perVar -and $grp.PSObject.Properties.Name -contains 'variationSettings') {
            $vs = $grp.variationSettings
            if ($vs.PSObject.Properties.Name -contains $varLabel) {
              $v      = $vs.$varLabel
              $pct    = [int]$v.percent
              $manIds = @()
              if ($v.PSObject.Properties.Name -contains 'manualIds' -and $v.manualIds) {
                [string[]]$manIds = @($v.manualIds | ForEach-Object { "$_" } | Where-Object { $_ -match '^\d+$' })
              }
            }
          }

          # Exclude all other grip sox folders (both length and brands)
          $otherRoots = @($gripSoxRoots | Where-Object { $_ -ne $vf.FullName })
          $logName    = ("GripSoxLength_{0}_Assignments.csv" -f ($varLabel -replace '[^a-zA-Z0-9]','_'))
          $mArgs = @{
            CsvPath               = $csvMain
            RootPath              = $vf.FullName
            OtherGripSoxRootsPipe = ($otherRoots -join "|")
            LogFileName           = $logName
            Percent               = $pct
            Seed                  = $seed
          }
          if ($manIds -and @($manIds).Count -gt 0) { $mArgs["ManualPlayerIds"] = @($manIds) }
          if ($dry) { $mArgs["DryRun"] = $true }
          Invoke-Mod "Assign-GripSox-Single.ps1" $mArgs
        }
      }
    }
  }
}

# ═════════════════════════════════════════════════════════════════════════════
# GROUPED: Sleeve Roll Up, Sleeve Inner, Wristtaping
# Each variation is an independent top-level folder.
# These groups are independent of each other and of all other mods.
# ═════════════════════════════════════════════════════════════════════════════

$groupedDefs = @(
  [pscustomobject]@{ Key="sleeveRollUp"; Prefix="Sleeve Roll Up-"; LogPrefix="SleeveRollUp"; Script="Assign-Sleeve.ps1"      },
  [pscustomobject]@{ Key="sleeveInner";  Prefix="Sleeve Inner-";   LogPrefix="SleeveInner";  Script="Assign-Sleeve.ps1"      },
  [pscustomobject]@{ Key="wristtaping";  Prefix="Wristtaping ";    LogPrefix="Wristtaping";  Script="Assign-Wristtaping.ps1" }
)

foreach ($gd in $groupedDefs) {
  if ($solo -and $solo -ne $gd.Key) { continue }
  if (-not $grouped) { continue }
  if (-not ($grouped.PSObject.Properties.Name -contains $gd.Key)) { continue }
  $grp = $grouped.($gd.Key)
  if (-not $grp.enabled) { continue }

  $varFolders = @(Get-ChildItem -LiteralPath $modRoot -Directory -ErrorAction SilentlyContinue |
    Where-Object { $_.Name.StartsWith($gd.Prefix) })

  if ($varFolders.Count -eq 0) {
    Write-Host ("[WARN] No folders found matching prefix '{0}'." -f $gd.Prefix) -ForegroundColor DarkYellow
    continue
  }

  $perVar = $grp.PSObject.Properties.Name -contains 'perVariationMode' -and $grp.perVariationMode

  foreach ($vf in $varFolders) {
    $varLabel = $vf.Name.Substring($gd.Prefix.Length)
    $pct      = [int]$grp.percent
    $manIds   = Get-ManualIds $grp

    if ($perVar -and $grp.PSObject.Properties.Name -contains 'variationSettings') {
      $vs = $grp.variationSettings
      if ($vs.PSObject.Properties.Name -contains $varLabel) {
        $v   = $vs.$varLabel
        $pct = [int]$v.percent
        $manIds = @()
        if ($v.PSObject.Properties.Name -contains 'manualIds' -and $v.manualIds -and $v.manualIds.Count -gt 0) {
          $manIds = @($v.manualIds)
        }
      }
    }

    $logName = ("{0}_{1}_Assignments.csv" -f $gd.LogPrefix, ($varLabel -replace '[^a-zA-Z0-9]','_'))
    $mArgs = @{
      CsvPath     = $csvMain
      RootPath    = $vf.FullName
      LogFileName = $logName
      Percent     = $pct
      Seed        = $seed
    }
    if ($manIds -and @($manIds).Count -gt 0) { $mArgs["ManualPlayerIds"] = @($manIds) }
    if ($dry) { $mArgs["DryRun"] = $true }

    Invoke-Mod $gd.Script $mArgs
  }
}

# ═════════════════════════════════════════════════════════════════════════════
# VALIDATE
# ═════════════════════════════════════════════════════════════════════════════

Write-Host ""
if (-not $solo) {
  & (Join-Path $here "Validate-Assignments.ps1") -Here $here
}

Write-Host ""
Write-Host ("All done. Mode={0}" -f $Mode) -ForegroundColor Green
