$ErrorActionPreference = 'Stop'
$taskRoot = 'G:\Heroes3-AI-Lab'
& wsl -d Ubuntu-22.04 -- python3 /mnt/g/Heroes3-AI-Lab/research/check-challenge-idle.py
if ($LASTEXITCODE -ne 0) { throw 'Lab work is already running.' }
Start-Process -FilePath 'powershell.exe' -ArgumentList @('-NoProfile','-ExecutionPolicy','Bypass','-File',"$taskRoot\research\finish-challenge-artifacts.ps1") -WindowStyle Hidden -RedirectStandardOutput "$taskRoot\research\challenge-finalization.log" -RedirectStandardError "$taskRoot\research\challenge-finalization-errors.log"
& wsl -d Ubuntu-22.04 -- python3 /mnt/g/Heroes3-AI-Lab/research/resume-paused-challenge.py
if ($LASTEXITCODE -ne 0) { throw 'Challenge continuation failed; preserved logs need review.' }
