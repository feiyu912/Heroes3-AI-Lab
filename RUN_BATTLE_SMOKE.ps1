param(
    [ValidateSet('attacker', 'defender')]
    [string]$Role = 'attacker',
    [ValidateRange(1, 100)]
    [int]$Episodes = 5
)
$ErrorActionPreference = 'Stop'
$labOutput = '/mnt/g/Heroes3-AI-Lab/research/smoke-manual.json'
$labRunId = [guid]::NewGuid().ToString()
& wsl.exe -d Ubuntu-22.04 -- bash /mnt/g/Heroes3-AI-Lab/research/run-battle-smoke.sh --role $Role --episodes $Episodes --output $labOutput --run-id $labRunId
$labRunExit = $LASTEXITCODE
if ($labRunExit -ne 0) {
    throw "Battle worker exited with code $labRunExit"
}
$labResult = Get-Content -LiteralPath (Join-Path $PSScriptRoot 'research\smoke-manual.json') -Raw | ConvertFrom-Json
if (-not $labResult.completed -or $labResult.run_id -ne $labRunId) {
    throw 'Current invocation did not produce a complete result.'
}
Write-Host "Completed $($labResult.episodes.Count) battles; worker exited successfully."
