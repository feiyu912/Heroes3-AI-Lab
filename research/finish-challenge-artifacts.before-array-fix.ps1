$ErrorActionPreference = 'Stop'
$taskRoot = 'G:\Heroes3-AI-Lab'
$researchRoot = Join-Path $taskRoot 'research'
$progressFile = Join-Path $researchRoot 'challenge24-pipeline-progress.json'
$statusFile = Join-Path $researchRoot 'challenge-finalization-status.json'
$deadline = (Get-Date).AddHours(24)

function Save-Status([string]$state, [string]$detail) {
    @{state=$state; detail=$detail; updated_at=(Get-Date).ToString('o')} |
        ConvertTo-Json | Set-Content -LiteralPath $statusFile -Encoding UTF8
}

function Invoke-LabScript([string]$python, [string]$script) {
    & wsl -d Ubuntu-22.04 -- $python "/mnt/g/Heroes3-AI-Lab/research/$script"
    if ($LASTEXITCODE -ne 0) { throw "$script exited with code $LASTEXITCODE" }
}

try {
    Save-Status 'waiting' 'Existing 24-worker pipeline continues; no second trainer launched.'
    while ((Get-Date) -lt $deadline) {
        try { $progress = @(Get-Content -LiteralPath $progressFile -Raw | ConvertFrom-Json) }
        catch { Start-Sleep -Seconds 15; continue }
        if (@($progress | Where-Object { $_.returncode -ne 0 }).Count) {
            throw 'Training/evaluation pipeline failed; preserve logs and do not publish partial results.'
        }
        if ($progress.Count -eq 5 -and $progress[-1].script -eq 'run-fresh-challenge-evaluation.py') { break }
        Start-Sleep -Seconds 30
    }
    if ((Get-Date) -ge $deadline) { throw 'Timed out waiting for existing pipeline.' }
    Save-Status 'finalizing' 'All training and final held-out battles completed successfully.'
    Invoke-LabScript '/root/heroes3-ai-lab/venv/bin/python' 'summarize-challenge.py'
    Invoke-LabScript '/root/heroes3-ai-lab/venv/bin/python' 'save-challenge-model.py'
    Invoke-LabScript 'python3' 'write-challenge-report.py'
    & 'D:\anaconda3\python.exe' (Join-Path $researchRoot 'plot-challenge-results.py')
    if ($LASTEXITCODE -ne 0) { throw 'Plot generation failed.' }
    $results = Get-Content -LiteralPath (Join-Path $researchRoot 'CHALLENGE_RESULTS.json') -Raw | ConvertFrom-Json
    if (@($results.fresh_results).Count -ne 6) { throw 'Incomplete final matchup suite.' }
    foreach ($match in $results.fresh_results) {
        if ($match.summary[0].battles -ne 512 -or $match.summary[0].invalid_actions -ne 0) {
            throw "Final matchup verification failed: $($match.name)"
        }
    }
    Save-Status 'completed' 'Verified six 512-battle matchups; report, selected weights and figure saved.'
    Invoke-LabScript 'python3' 'snapshot-lab-v4.py'
} catch {
    Save-Status 'failed' $_.Exception.Message
    throw
}
