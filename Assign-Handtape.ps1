# Assign-Handtape.ps1
# Assigns handtape folders for specific players based on skin color from PESEditor CSV.
# Template folder is named "ID" (not "ID Players").

param(
  [Parameter(Mandatory=$true)][string]$AppearanceCsvPath,
  [Parameter(Mandatory=$true)][string]$RootPath,
  # Pipe-separated player IDs to assign
  [Parameter(Mandatory=$true)][string]$PlayerIdsPipe,
  # Pipe-separated hands to assign: "left hand", "right hand", or both
  [Parameter(Mandatory=$true)][string]$HandsPipe,
  [string]$RelativeRealPath   = "Asset\model\character\face\real",
  [string]$TemplateFolderName = "ID",
  [switch]$Overwrite,
  [switch]$DryRun
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# ── load appearance CSV ───────────────────────────────────────────────────────
if (-not (Test-Path -LiteralPath $AppearanceCsvPath -PathType Leaf)) {
  throw "Appearance CSV not found: $AppearanceCsvPath"
}

$appRows = @(Import-Csv -LiteralPath $AppearanceCsvPath -Delimiter ';')
if ($appRows.Count -eq 0) { throw "Appearance CSV is empty." }

$appFirst = $appRows | Select-Object -First 1
if (-not ($appFirst.PSObject.Properties.Name -contains 'Id')) { throw "Appearance CSV missing 'Id' column." }
if (-not ($appFirst.PSObject.Properties.Name -contains 'SkinColour')) { throw "Appearance CSV missing 'SkinColour' column." }

# Build lookup: PlayerId -> SkinColour
$skinMap = @{}
foreach ($r in $appRows) {
  $playerId = "$($r.Id)".Trim()
  $skin     = "$($r.SkinColour)".Trim()
  if ($playerId -match '^\d+$' -and $skin -match '^\d+$') {
    $skinMap[$playerId] = [int]$skin
  }
}

# ── parse inputs ──────────────────────────────────────────────────────────────
$playerIds = @($PlayerIdsPipe -split '\|' | ForEach-Object { $_.Trim() } | Where-Object { $_ -match '^\d+$' } | Select-Object -Unique)
$hands     = @($HandsPipe     -split '\|' | ForEach-Object { $_.Trim().ToLower() } | Where-Object { $_ -ne '' } | Select-Object -Unique)

if ($playerIds.Count -eq 0) { throw "No valid player IDs provided." }
if ($hands.Count -eq 0)     { throw "No hands specified. Use 'left hand', 'right hand', or both." }

# Validate hand values
foreach ($h in $hands) {
  if ($h -notin @("left hand","right hand")) {
    throw "Invalid hand value '$h'. Must be 'left hand' or 'right hand'."
  }
}

# ── execute ───────────────────────────────────────────────────────────────────
Write-Host ""
Write-Host "===== HANDTAPE ASSIGNMENT =====" -ForegroundColor Yellow
Write-Host ("Players  : {0}" -f ($playerIds -join ', '))
Write-Host ("Hands    : {0}" -f ($hands -join ', '))
Write-Host ("DryRun   : {0}" -f ([bool]$DryRun))
Write-Host ""

$created = 0; $skipped = 0; $notFound = 0
$results = @()

foreach ($playerId in $playerIds) {
  # Look up skin color
  if (-not $skinMap.ContainsKey($playerId)) {
    Write-Host ("[WARN] Player {0} not found in appearance CSV - skipping." -f $playerId) -ForegroundColor DarkYellow
    $notFound++
    continue
  }

  $skinNum    = $skinMap[$playerId]
  $skinFolder = "skin{0}" -f $skinNum

  foreach ($hand in $hands) {
    $handFolderPath = Join-Path $RootPath (Join-Path $skinFolder $hand)
    $realPath       = Join-Path $handFolderPath $RelativeRealPath
    $templatePath   = Join-Path $realPath $TemplateFolderName

    if (-not (Test-Path -LiteralPath $realPath -PathType Container)) {
      Write-Host ("[WARN] Real path not found for skin={0}, hand={1}: {2}" -f $skinFolder, $hand, $realPath) -ForegroundColor DarkYellow
      continue
    }
    if (-not (Test-Path -LiteralPath $templatePath -PathType Container)) {
      Write-Host ("[WARN] Template 'ID' not found: {0}" -f $templatePath) -ForegroundColor DarkYellow
      continue
    }

    $dest = Join-Path $realPath $playerId

    if ($DryRun) {
      Write-Host ("Would create: {0}  (Skin: {1}, Hand: {2})" -f $dest, $skinFolder, $hand) -ForegroundColor Cyan
      $results += [pscustomobject]@{ PlayerId=$playerId; Skin=$skinFolder; Hand=$hand; DestPath=$dest; Action="DRYRUN" }
      continue
    }

    if (Test-Path -LiteralPath $dest -PathType Container) {
      if ($Overwrite) { Remove-Item -LiteralPath $dest -Recurse -Force }
      else {
        $skipped++
        $results += [pscustomobject]@{ PlayerId=$playerId; Skin=$skinFolder; Hand=$hand; DestPath=$dest; Action="SKIPPED_EXISTS" }
        continue
      }
    }

    Copy-Item -LiteralPath $templatePath -Destination $dest -Recurse -Force
    $created++
    $results += [pscustomobject]@{ PlayerId=$playerId; Skin=$skinFolder; Hand=$hand; DestPath=$dest; Action="CREATED" }
  }
}

$logPath = Join-Path $PSScriptRoot "Handtape_Assignments.csv"
$results | Export-Csv -LiteralPath $logPath -NoTypeInformation -Encoding UTF8

if ($DryRun) {
  Write-Host "Dry run complete. No files copied." -ForegroundColor Yellow
} else {
  Write-Host ("Created      : {0}" -f $created)
  Write-Host ("Skipped      : {0}" -f $skipped)
  Write-Host ("Not in DB    : {0}" -f $notFound)
  Write-Host ("Log          : {0}" -f $logPath)
}
