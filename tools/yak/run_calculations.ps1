$ErrorActionPreference='Stop'
$ownedRhino=New-Object -ComObject Rhino.Application.8
$ownedRhino.Visible=$true
$deadline=(Get-Date).AddSeconds(60)
while ($ownedRhino.IsInitialized -eq 0 -and (Get-Date) -lt $deadline) {Start-Sleep -Milliseconds 500}
if ($ownedRhino.IsInitialized -eq 0) {throw 'Dedicated Rhino did not initialize'}
$ownedRhino.RunScript('_Grasshopper',0)
$repoRoot=[System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../..'))
$scriptPath=Join-Path $PSScriptRoot 'native_calculations.py'
$ownedRhino.RunScript(('_-RunPythonScript "'+$scriptPath+'" _Enter'),0)
$reportPath=Join-Path $repoRoot 'tool/build/yak-calculations/results.json'
$deadline=(Get-Date).AddHours(3)
$previous=''
while ((Get-Date) -lt $deadline) {
 Start-Sleep -Seconds 2
 try {$r=Get-Content -LiteralPath $reportPath -Raw | ConvertFrom-Json} catch {continue}
 $progress=($r.current | ConvertTo-Json -Compress)
 if ($progress -ne $previous) {Write-Output $progress;$previous=$progress}
 if ($r.status -eq 'PASS') {Write-Output 'All example calculations PASS';exit 0}
 if ($r.status -eq 'FAIL') {Write-Output 'Example calculation failures recorded';exit 1}
}
throw 'Batch calculation timeout'
