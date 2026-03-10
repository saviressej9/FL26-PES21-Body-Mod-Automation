# Assign-GripSox-Brands.ps1
# Assigns players to Grip Sock-Brands subfolders.
# Excludes any player already found on disk in any other grip sox folder.

param(
  [Parameter(Mandatory=$true)][string]$CsvPath,
  [Parameter(Mandatory=$true)][string]$RootPath,
  [Parameter(Mandatory=$true)][string]$OtherGripSoxRootsPipe,
  [string]$RelativeRealPath   = "Asset\model\character\face\real",
  [string]$TemplateFolderName = "ID Players",
  [string[]]$Brands           = @("Adidas","Falke","Gravity","Metasox","Nike","SoxPro","Storelli","Tapedesign","TruSox"),
  [ValidateSet("Random","Balanced")][string]$Mode = "Balanced",
  [int]$Percent  = 100,
  [string[]]$ManualPlayerIds  = @(),
  [int]$Seed     = 26,
  [switch]$Overwrite,
  [switch]$DryRun
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Shuffle([object[]]$arr, [System.Random]$rng) {
  $a = [object[]]($arr)
  for ($i = $a.Count - 1; $i -gt 0; $i--) {
    $j = $rng.Next(0, $i + 1)
    $tmp = $a[$i]; $a[$i] = $a[$j]; $a[$j] = $tmp
  }
  return $a
}

# ── load player IDs ───────────────────────────────────────────────────────────
if (-not (Test-Path -LiteralPath $CsvPath -PathType Leaf)) { throw "CSV not found: $CsvPath" }
$rows = @(Import-Csv -LiteralPath $CsvPath -Delimiter ';')
if ($rows.Count -eq 0) { throw "CSV is empty: $CsvPath" }
$first = $rows | Select-Object -First 1
if (-not ($first.PSObject.Properties.Name -contains 'Id')) { throw "CSV missing 'Id' column: $CsvPath" }

$allIds = @(
  $rows | Select-Object -ExpandProperty Id |
    ForEach-Object { "$_".Trim() } |
    Where-Object   { $_ -match '^\d+$' } |
    Sort-Object -Unique
)
if ($allIds.Count -eq 0) { throw "No numeric Id values found in: $CsvPath" }

# ── build disk-based exclusion set from other grip sox folders ────────────────
$excludeSet = [System.Collections.Generic.HashSet[string]]::new()
foreach ($otherRoot in ($OtherGripSoxRootsPipe -split '\|' | ForEach-Object { $_.Trim() } | Where-Object { $_ -ne '' })) {
  $realPath = Join-Path $otherRoot $RelativeRealPath
  if (-not (Test-Path -LiteralPath $realPath -PathType Container)) { continue }
  foreach ($d in (Get-ChildItem -LiteralPath $realPath -Directory)) {
    if ($d.Name -match '^\d+$') { [void]$excludeSet.Add($d.Name) }
  }
}

# ── validate brand folders ────────────────────────────────────────────────────
$brandInfo = @()
foreach ($b in $Brands) {
  $brandPath    = Join-Path $RootPath $b
  $realPath     = Join-Path $brandPath $RelativeRealPath
  $templatePath = Join-Path $realPath $TemplateFolderName
  if (-not (Test-Path -LiteralPath $brandPath    -PathType Container)) { throw "Brand folder not found: $brandPath" }
  if (-not (Test-Path -LiteralPath $realPath     -PathType Container)) { throw "Real path not found: $realPath" }
  if (-not (Test-Path -LiteralPath $templatePath -PathType Container)) { throw "Template not found: $templatePath" }
  $brandInfo += [pscustomobject]@{ Brand=$b; RealPath=$realPath; TemplatePath=$templatePath }
}

# ── determine eligible players ────────────────────────────────────────────────
$rng = [System.Random]::new($Seed)

if ($ManualPlayerIds.Count -gt 0) {
  $eligible = @($ManualPlayerIds | Where-Object { $_ -match '^\d+$' } | Where-Object { -not $excludeSet.Contains($_) })
} else {
  $eligible = @($allIds | Where-Object { -not $excludeSet.Contains($_) })
  if ($Percent -lt 100) {
    $shuffled  = @($eligible | Sort-Object { $rng.Next() })
    $cnt       = [int][Math]::Round($shuffled.Count * ($Percent / 100.0))
    $cnt       = [Math]::Max(0, [Math]::Min($cnt, $shuffled.Count))
    $eligible  = @()
    if ($cnt -gt 0) { $eligible = @($shuffled[0..($cnt-1)]) }
  }
}

# ── assign brands ─────────────────────────────────────────────────────────────
$assignments = @()
if ($Mode -eq "Balanced") {
  $shuffledIds    = Shuffle $eligible $rng
  $shuffledBrands = Shuffle $brandInfo $rng
  $idx = 0
  foreach ($id in $shuffledIds) {
    $pick = $shuffledBrands[$idx % $shuffledBrands.Count]
    $assignments += [pscustomobject]@{ PlayerId=$id; Brand=$pick.Brand; RealPath=$pick.RealPath; TemplatePath=$pick.TemplatePath }
    $idx++
  }
} else {
  foreach ($id in $eligible) {
    $pick = $brandInfo[$rng.Next(0, $brandInfo.Count)]
    $assignments += [pscustomobject]@{ PlayerId=$id; Brand=$pick.Brand; RealPath=$pick.RealPath; TemplatePath=$pick.TemplatePath }
  }
}

# ── execute ───────────────────────────────────────────────────────────────────
Write-Host ""
Write-Host "===== GRIP SOX BRANDS ASSIGNMENT =====" -ForegroundColor Yellow
Write-Host ("Total players  : {0}" -f $allIds.Count)
Write-Host ("Excluded       : {0}" -f $excludeSet.Count)
Write-Host ("Eligible       : {0}" -f $eligible.Count)
Write-Host ("DryRun         : {0}" -f ([bool]$DryRun))
Write-Host ""

$created = 0; $skipped = 0
$results = @()

foreach ($a in $assignments) {
  $dest = Join-Path $a.RealPath $a.PlayerId
  if ($DryRun) {
    Write-Host ("Would create: {0}  (Brand: {1})" -f $dest, $a.Brand) -ForegroundColor Cyan
    $results += [pscustomobject]@{ PlayerId=$a.PlayerId; Brand=$a.Brand; DestPath=$dest; Action="DRYRUN" }
    continue
  }
  if (Test-Path -LiteralPath $dest -PathType Container) {
    if ($Overwrite) { Remove-Item -LiteralPath $dest -Recurse -Force }
    else {
      $skipped++
      $results += [pscustomobject]@{ PlayerId=$a.PlayerId; Brand=$a.Brand; DestPath=$dest; Action="SKIPPED_EXISTS" }
      continue
    }
  }
  Copy-Item -LiteralPath $a.TemplatePath -Destination $dest -Recurse -Force
  $created++
  $results += [pscustomobject]@{ PlayerId=$a.PlayerId; Brand=$a.Brand; DestPath=$dest; Action="CREATED" }
}

$logPath = Join-Path $PSScriptRoot "GripSox_Brands_Assignments.csv"
$results | Export-Csv -LiteralPath $logPath -NoTypeInformation -Encoding UTF8

if ($DryRun) {
  Write-Host "Dry run complete. No files copied." -ForegroundColor Yellow
} else {
  Write-Host ("Created : {0}" -f $created)
  Write-Host ("Skipped : {0}" -f $skipped)
  Write-Host ("Log     : {0}" -f $logPath)
}
