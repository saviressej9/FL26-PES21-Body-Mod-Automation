# Assign-Socks.ps1
# Generic script for all sock mods.
# Excludes players already found on disk in ANY sock folder before assigning.
# Sock-Holes has priority - if a player exists there they are blocked from all others.

param(
  [Parameter(Mandatory=$true)][string]$CsvPath,
  [Parameter(Mandatory=$true)][string]$RootPath,
  # Pipe-separated paths to ALL sock mod real folders (for disk scan exclusion)
  [Parameter(Mandatory=$true)][string]$AllSockRealPathsPipe,
  [Parameter(Mandatory=$true)][string]$ModName,
  [Parameter(Mandatory=$true)][string]$LogFileName,
  [string]$RelativeRealPath   = "Asset\model\character\face\real",
  [int]$Percent               = 15,
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

# ── disk-based exclusion: scan all sock folders ───────────────────────────────
$excludeSet = [System.Collections.Generic.HashSet[string]]::new()
foreach ($sockRealPath in ($AllSockRealPathsPipe -split '\|' | ForEach-Object { $_.Trim() } | Where-Object { $_ -ne '' })) {
  if (-not (Test-Path -LiteralPath $sockRealPath -PathType Container)) { continue }
  foreach ($d in (Get-ChildItem -LiteralPath $sockRealPath -Directory)) {
    if ($d.Name -match '^\d+$') { [void]$excludeSet.Add($d.Name) }
  }
}

# ── validate template(s) ──────────────────────────────────────────────────────
$realPath  = Join-Path $RootPath $RelativeRealPath
if (-not (Test-Path -LiteralPath $realPath -PathType Container)) { throw "Real path not found: $realPath" }

$templates = @(Get-ChildItem -LiteralPath $realPath -Directory | Where-Object { $_.Name -like "ID Players*" })
if ($templates.Count -eq 0) { throw "No 'ID Players*' template folders found in: $realPath" }

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
Write-Host ("===== SOCK ASSIGNMENT: {0} =====" -f $ModName) -ForegroundColor Yellow
Write-Host ("Total players : {0}" -f $allIds.Count)
Write-Host ("Excluded      : {0}" -f $excludeSet.Count)
Write-Host ("Eligible      : {0}" -f $eligible.Count)
Write-Host ("Templates     : {0}" -f $templates.Count)
Write-Host ("DryRun        : {0}" -f ([bool]$DryRun))
Write-Host ""

$created = 0; $skipped = 0; $idx = 0
$results = @()

foreach ($id in $eligible) {
  $tpl  = $templates[$idx % $templates.Count]
  $dest = Join-Path $realPath $id

  if ($DryRun) {
    Write-Host ("Would create: {0}  (From: {1})" -f $dest, $tpl.Name) -ForegroundColor Cyan
    $results += [pscustomobject]@{ PlayerId=$id; Template=$tpl.Name; DestPath=$dest; Action="DRYRUN" }
    $idx++; continue
  }

  if (Test-Path -LiteralPath $dest -PathType Container) {
    if ($Overwrite) { Remove-Item -LiteralPath $dest -Recurse -Force }
    else {
      $skipped++
      $results += [pscustomobject]@{ PlayerId=$id; Template=$tpl.Name; DestPath=$dest; Action="SKIPPED_EXISTS" }
      $idx++; continue
    }
  }

  Copy-Item -LiteralPath $tpl.FullName -Destination $dest -Recurse -Force
  $created++
  $results += [pscustomobject]@{ PlayerId=$id; Template=$tpl.Name; DestPath=$dest; Action="CREATED" }
  $idx++
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
