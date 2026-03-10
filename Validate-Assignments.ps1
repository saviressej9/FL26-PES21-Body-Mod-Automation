# Validate-Assignments.ps1
# Scans all assignment log CSVs and checks for duplicate PlayerIds
# within each group (socks, pants, grip sox).
# Groups are independent - a player CAN appear in both socks and pants.

param(
  [Parameter(Mandatory=$true)][string]$Here
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Get-IdsFromCsv([string]$path) {
  if (-not (Test-Path -LiteralPath $path -PathType Leaf)) { return @() }
  $rows = @(Import-Csv -LiteralPath $path)
  if ($rows.Count -eq 0) { return @() }
  $f = $rows | Select-Object -First 1
  $col = if ($f.PSObject.Properties.Name -contains 'PlayerId') { 'PlayerId' }
         elseif ($f.PSObject.Properties.Name -contains 'Id')   { 'Id' }
         else { return @() }
  return @(
    $rows | Select-Object -ExpandProperty $col |
      ForEach-Object { "$_".Trim() } |
      Where-Object   { $_ -match '^\d+$' }
  )
}

function Check-Group([string]$groupName, [hashtable]$csvFiles) {
  $records = @()
  foreach ($label in $csvFiles.Keys) {
    $path = $csvFiles[$label]
    $ids  = @(Get-IdsFromCsv $path)
    if ($ids.Count -eq 0) { continue }
    foreach ($id in $ids) {
      $records += [pscustomobject]@{ PlayerId=$id; Source=$label }
    }
  }

  if ($records.Count -eq 0) {
    Write-Host ("[{0}] No assignment data found to validate." -f $groupName) -ForegroundColor DarkYellow
    return $true
  }

  $dupes = @($records | Group-Object PlayerId | Where-Object { $_.Count -gt 1 })
  if ($dupes.Count -eq 0) {
    Write-Host ("[OK] {0}: No duplicate PlayerIds found." -f $groupName) -ForegroundColor Green
    return $true
  }

  Write-Host ("[ERROR] {0}: Duplicate PlayerIds detected:" -f $groupName) -ForegroundColor Red
  foreach ($d in $dupes) {
    $srcs = ($d.Group | Select-Object -ExpandProperty Source | Sort-Object -Unique) -join ", "
    Write-Host ("  PlayerId {0} in: {1}" -f $d.Name, $srcs)
  }
  return $false
}

Write-Host ""
Write-Host "===== VALIDATING ASSIGNMENTS =====" -ForegroundColor Yellow

$sockGroup = @{
  "Sock-Holes"       = (Join-Path $Here "Socks_Holes_Assignments.csv")
  "Sock-MiddleHigh"  = (Join-Path $Here "Socks_MiddleHigh_Assignments.csv")
  "Sock-ShortGroup"  = (Join-Path $Here "Socks_ShortGroup_Assignments.csv")
}

$pantsGroup = @{
  "Pants-Baggy"      = (Join-Path $Here "Pants_Baggy_Assignments.csv")
  "Pants-ExtraBaggy" = (Join-Path $Here "Pants_ExtraBaggy_Assignments.csv")
  "Pants-Shorter"    = (Join-Path $Here "Pants_Shorter_Assignments.csv")
}

$gripSoxGroup = @{
  "GripSox-Brands"    = (Join-Path $Here "GripSox_Brands_Assignments.csv")
  "GripSox-DualColor" = (Join-Path $Here "GripSox_DualColor_Assignments.csv")
  "GripSox-Long"      = (Join-Path $Here "GripSox_Long_Assignments.csv")
  "GripSox-Short"     = (Join-Path $Here "GripSox_Short_Assignments.csv")
}

$ok1 = Check-Group "Socks"    $sockGroup
$ok2 = Check-Group "Pants"    $pantsGroup
$ok3 = Check-Group "Grip Sox" $gripSoxGroup

Write-Host ""
if ($ok1 -and $ok2 -and $ok3) {
  Write-Host "[OK] All groups passed validation." -ForegroundColor Green
  exit 0
} else {
  throw "Validation failed. Fix duplicates before enabling mods in-game."
}
