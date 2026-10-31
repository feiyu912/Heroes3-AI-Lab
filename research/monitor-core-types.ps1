param([int]$Seconds = 30)
$ErrorActionPreference = 'Stop'
Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;
public static class LabCpuSets {
    [DllImport("kernel32.dll", SetLastError=true)]
    [return: MarshalAs(UnmanagedType.Bool)]
    public static extern bool GetSystemCpuSetInformation(IntPtr info, uint length, out uint returnedLength, IntPtr process, uint flags);
}
'@
[uint32]$labSize = 0
[void][LabCpuSets]::GetSystemCpuSetInformation([IntPtr]::Zero,0,[ref]$labSize,[IntPtr]::Zero,0)
if ($labSize -eq 0) { throw 'CPU-set query returned no topology.' }
$labBuffer = [Runtime.InteropServices.Marshal]::AllocHGlobal([int]$labSize)
try {
    if (-not [LabCpuSets]::GetSystemCpuSetInformation($labBuffer,$labSize,[ref]$labSize,[IntPtr]::Zero,0)) {
        throw 'CPU-set query failed.'
    }
    $labBytes = [byte[]]::new($labSize)
    [Runtime.InteropServices.Marshal]::Copy($labBuffer,$labBytes,0,[int]$labSize)
} finally {
    [Runtime.InteropServices.Marshal]::FreeHGlobal($labBuffer)
}
$labCpus = @()
for ($labOffset=0; $labOffset -lt $labBytes.Length;) {
    $labEntrySize = [BitConverter]::ToUInt32($labBytes,$labOffset)
    $labType = [BitConverter]::ToUInt32($labBytes,$labOffset+4)
    if ($labEntrySize -lt 32 -or $labOffset+$labEntrySize -gt $labBytes.Length) { throw 'Unexpected CPU-set structure size.' }
    if ($labType -eq 0) {
        $labCpus += [pscustomobject]@{
            id = [BitConverter]::ToUInt32($labBytes,$labOffset+8)
            group = [BitConverter]::ToUInt16($labBytes,$labOffset+12)
            logicalProcessor = $labBytes[$labOffset+14]
            core = $labBytes[$labOffset+15]
            efficiencyClass = $labBytes[$labOffset+18]
            schedulingClass = $labBytes[$labOffset+20]
        }
    }
    $labOffset += $labEntrySize
}
$labSamples = @()
$labClock = [Diagnostics.Stopwatch]::StartNew()
while ($labClock.Elapsed.TotalSeconds -lt $Seconds) {
    $labCounters = Get-CimInstance Win32_PerfFormattedData_PerfOS_Processor
    $labMemory = Get-CimInstance Win32_OperatingSystem
    $labSamples += [pscustomobject]@{
        timeUtc = [DateTime]::UtcNow.ToString('o')
        availableMemoryMiB = $labMemory.FreePhysicalMemory/1024
        cpuLogical = @($labCounters | Select-Object Name,PercentProcessorTime)
    }
    [pscustomobject]@{
        topology = $labCpus
        samples = $labSamples
        scope = 'Windows whole-host logical utilization by CPU-set efficiency class, including desktop/background work; no guest-to-host vCPU identity or per-worker core affinity claim.'
        source = 'https://learn.microsoft.com/en-us/windows/win32/api/winnt/ns-winnt-system_cpu_set_information'
    } | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath 'G:\Heroes3-AI-Lab\research\core-type-telemetry.json' -Encoding utf8
    Start-Sleep -Seconds 2
}
