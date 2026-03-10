# Assign-Gloves.ps1
# Assigns players to Gloves-Brands subfolders.
# Excludes Real Madrid and Bayern Munich by default.

param(
  [Parameter(Mandatory=$true)][string]$CsvPath,
  [Parameter(Mandatory=$true)][string]$RootPath,
  [string]$RelativeRealPath   = "Asset\model\character\face\real",
  [string]$TemplateFolderName = "ID Players",
  [string[]]$ExcludeBrands    = @("Real Madrid","Bayern Munich"),
  [ValidateSet("Random","Balanced")][string]$Mode = "Balanced",
  [int]$Percent               = 50,
  [string[]]$ManualPlayerIds  = @(),
  [int]$Seed                  = 26,
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

# ── discover allowed brand folders ───────────────────────────────────────────
$brandInfos = @()
foreach ($d in (Get-ChildItem -LiteralPath $RootPath -Directory)) {
  if ($ExcludeBrands -contains $d.Name) { continue }
  $realPath     = Join-Path $d.FullName $RelativeRealPath
  $templatePath = Join-Path $realPath $TemplateFolderName
  if (-not (Test-Path -LiteralPath $realPath     -PathType Container)) { continue }
  if (-not (Test-Path -LiteralPath $templatePath -PathType Container)) { continue }
  $brandInfos += [pscustomobject]@{ Brand=$d.Name; RealPath=$realPath; TemplatePath=$templatePath }
}
if ($brandInfos.Count -eq 0) { throw "No valid glove brand folders found under: $RootPath" }

# ── determine eligible players ────────────────────────────────────────────────
$rng = [System.Random]::new($Seed)

if ($ManualPlayerIds.Count -gt 0) {
  $eligible = @($ManualPlayerIds | Where-Object { $_ -match '^\d+$' })
} else {
  $eligible = @($allIds)
  if ($Percent -lt 100) {
    $shuffled = @($eligible | Sort-Object { $rng.Next() })
    $cnt      = [int][Math]::Round($shuffled.Count * ($Percent / 100.0))
    $cnt      = [Math]::Max(0, [Math]::Min($cnt, $shuffled.Count))
    $eligible = @()
    if ($cnt -gt 0) { $eligible = @($shuffled[0..($cnt-1)]) }
  }
}

# ── assign brands ─────────────────────────────────────────────────────────────
$assignments = @()
if ($Mode -eq "Balanced") {
  $shuffledIds    = Shuffle $eligible $rng
  $shuffledBrands = Shuffle $brandInfos $rng
  $idx = 0
  foreach ($id in $shuffledIds) {
    $b = $shuffledBrands[$idx % $shuffledBrands.Count]
    $assignments += [pscustomobject]@{ PlayerId=$id; Brand=$b.Brand; RealPath=$b.RealPath; TemplatePath=$b.TemplatePath }
    $idx++
  }
} else {
  foreach ($id in $eligible) {
    $b = $brandInfos[$rng.Next(0, $brandInfos.Count)]
    $assignments += [pscustomobject]@{ PlayerId=$id; Brand=$b.Brand; RealPath=$b.RealPath; TemplatePath=$b.TemplatePath }
  }
}

# ── execute ───────────────────────────────────────────────────────────────────
Write-Host ""
Write-Host "===== GLOVES BRANDS ASSIGNMENT =====" -ForegroundColor Yellow
Write-Host ("Total players : {0}" -f $allIds.Count)
Write-Host ("Eligible      : {0}" -f $eligible.Count)
Write-Host ("Brands found  : {0}" -f $brandInfos.Count)
Write-Host ("DryRun        : {0}" -f ([bool]$DryRun))
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

$logPath = Join-Path $PSScriptRoot "Gloves_Assignments.csv"
$results | Export-Csv -LiteralPath $logPath -NoTypeInformation -Encoding UTF8

if ($DryRun) {
  Write-Host "Dry run complete. No files copied." -ForegroundColor Yellow
} else {
  Write-Host ("Created : {0}" -f $created)
  Write-Host ("Skipped : {0}" -f $skipped)
  Write-Host ("Log     : {0}" -f $logPath)
}
