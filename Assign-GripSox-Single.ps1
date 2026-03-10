# Assign-GripSox-Single.ps1
# Generic script for single-folder grip sox mods (Dual Color, Long, Short).
# Excludes players already found on disk in any other grip sox folder.

param(
  [Parameter(Mandatory=$true)][string]$CsvPath,
  [Parameter(Mandatory=$true)][string]$RootPath,
  [Parameter(Mandatory=$true)][string]$OtherGripSoxRootsPipe,
  [Parameter(Mandatory=$true)][string]$LogFileName,
  [string]$RelativeRealPath   = "Asset\model\character\face\real",
  [string]$TemplateFolderName = "ID Players",
  [int]$Percent               = 100,
  [string[]]$ManualPlayerIds  = @(),
  [int]$Seed                  = 26,
  [switch]$Overwrite,
  [switch]$DryRun
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

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

# ── disk-based exclusion from other grip sox folders ─────────────────────────
$excludeSet = [System.Collections.Generic.HashSet[string]]::new()
foreach ($otherRoot in ($OtherGripSoxRootsPipe -split '\|' | ForEach-Object { $_.Trim() } | Where-Object { $_ -ne '' })) {
  $rp = Join-Path $otherRoot $RelativeRealPath
  if (-not (Test-Path -LiteralPath $rp -PathType Container)) { continue }
  foreach ($d in (Get-ChildItem -LiteralPath $rp -Directory)) {
    if ($d.Name -match '^\d+$') { [void]$excludeSet.Add($d.Name) }
  }
}

# ── validate template ─────────────────────────────────────────────────────────
$realPath     = Join-Path $RootPath $RelativeRealPath
$templatePath = Join-Path $realPath $TemplateFolderName
if (-not (Test-Path -LiteralPath $realPath     -PathType Container)) { throw "Real path not found: $realPath" }
if (-not (Test-Path -LiteralPath $templatePath -PathType Container)) { throw "Template not found: $templatePath" }

# ── determine eligible players ────────────────────────────────────────────────
$rng = [System.Random]::new($Seed)

if ($ManualPlayerIds.Count -gt 0) {
  $eligible = @($ManualPlayerIds | Where-Object { $_ -match '^\d+$' } | Where-Object { -not $excludeSet.Contains($_) })
} else {
  $eligible = @($allIds | Where-Object { -not $excludeSet.Contains($_) })
  if ($Percent -lt 100) {
    $shuffled = @($eligible | Sort-Object { $rng.Next() })
    $cnt      = [int][Math]::Round($shuffled.Count * ($Percent / 100.0))
    $cnt      = [Math]::Max(0, [Math]::Min($cnt, $shuffled.Count))
    $eligible = @()
    if ($cnt -gt 0) { $eligible = @($shuffled[0..($cnt-1)]) }
  }
}

# ── execute ───────────────────────────────────────────────────────────────────
Write-Host ""
Write-Host ("===== GRIP SOX SINGLE: {0} =====" -f (Split-Path -Leaf $RootPath)) -ForegroundColor Yellow
Write-Host ("Total players : {0}" -f $allIds.Count)
Write-Host ("Excluded      : {0}" -f $excludeSet.Count)
Write-Host ("Eligible      : {0}" -f $eligible.Count)
Write-Host ("DryRun        : {0}" -f ([bool]$DryRun))
Write-Host ""

$created = 0; $skipped = 0
$results = @()

foreach ($id in $eligible) {
  $dest = Join-Path $realPath $id
  if ($DryRun) {
    Write-Host ("Would create: {0}" -f $dest) -ForegroundColor Cyan
    $results += [pscustomobject]@{ PlayerId=$id; DestPath=$dest; Action="DRYRUN" }
    continue
  }
  if (Test-Path -LiteralPath $dest -PathType Container) {
    if ($Overwrite) { Remove-Item -LiteralPath $dest -Recurse -Force }
    else {
      $skipped++
      $results += [pscustomobject]@{ PlayerId=$id; DestPath=$dest; Action="SKIPPED_EXISTS" }
      continue
    }
  }
  Copy-Item -LiteralPath $templatePath -Destination $dest -Recurse -Force
  $created++
  $results += [pscustomobject]@{ PlayerId=$id; DestPath=$dest; Action="CREATED" }
}

$logPath = Join-Path $PSScriptRoot $LogFileName
$results | Export-Csv -LiteralPath $logPath -NoTypeInformation -Encoding UTF8

if ($DryRun) {
  Write-Host "Dry run complete. No files copied." -ForegroundColor Yellow
} else {
  Write-Host ("Created : {0}" -f $created)
  Write-Host ("Skipped : {0}" -f $skipped)
  Write-Host ("Log     : {0}" -f $logPath)
}
