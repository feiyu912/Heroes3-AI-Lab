param([int]$Seconds = 45)
$samples = @()
$labTimer = [Diagnostics.Stopwatch]::StartNew()
while ($labTimer.Elapsed.TotalSeconds -lt $Seconds) {
    $labMemory = Get-CimInstance Win32_OperatingSystem
    $labCpu = Get-CimInstance Win32_PerfFormattedData_PerfOS_Processor -Filter "Name='_Total'"
    $samples += [pscustomobject]@{
        timeUtc = [DateTime]::UtcNow.ToString('o')
        totalMemoryMiB = $labMemory.TotalVisibleMemorySize / 1024
        availableMemoryMiB = $labMemory.FreePhysicalMemory / 1024
        cpuPercent = $labCpu.PercentProcessorTime
    }
    $samples | ConvertTo-Json | Set-Content -LiteralPath 'G:\Heroes3-AI-Lab\research\windows-training-telemetry.json' -Encoding utf8
    Start-Sleep -Seconds 2
}
