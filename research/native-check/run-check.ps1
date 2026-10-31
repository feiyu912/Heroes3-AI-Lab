$ErrorActionPreference = 'Stop'
$labRoot = 'G:\Heroes3-AI-Lab'
$labProbe = Join-Path $labRoot 'research\native-check'
$labVsRoot = 'D:\visual studio'
& (Join-Path $labVsRoot 'Common7\Tools\Launch-VsDevShell.ps1') -Arch amd64 -HostArch amd64 -SkipAutomaticLocation
$labCmake = Join-Path $labVsRoot 'Common7\IDE\CommonExtensions\Microsoft\CMake\CMake\bin\cmake.exe'
$labNinja = Join-Path $labVsRoot 'Common7\IDE\CommonExtensions\Microsoft\CMake\Ninja\ninja.exe'
$labResults = [ordered]@{}
& $labCmake --version 2>&1 | Tee-Object -FilePath (Join-Path $labProbe 'cmake-version.log')
& $labCmake -S $labProbe -B (Join-Path $labProbe 'build') -G Ninja "-DCMAKE_MAKE_PROGRAM=$labNinja" -DCMAKE_BUILD_TYPE=Release 2>&1 | Tee-Object -FilePath (Join-Path $labProbe 'smoke-configure.log')
$labResults.smokeConfigure = $LASTEXITCODE
if ($labResults.smokeConfigure -eq 0) {
    & $labCmake --build (Join-Path $labProbe 'build') --parallel 2 2>&1 | Tee-Object -FilePath (Join-Path $labProbe 'smoke-build.log')
    $labResults.smokeBuild = $LASTEXITCODE
    if ($labResults.smokeBuild -eq 0) {
        & (Join-Path $labProbe 'build\native_smoke.exe') 2>&1 | Tee-Object -FilePath (Join-Path $labProbe 'smoke-run.log')
        $labResults.smokeRun = $LASTEXITCODE
    }
}
& cl.exe /nologo /std:c++20 /c (Join-Path $labProbe 'probe_posix_headers.cpp') "/Fo$(Join-Path $labProbe 'posix-probe.obj')" 2>&1 | Tee-Object -FilePath (Join-Path $labProbe 'posix-headers.log')
$labResults.posixHeaders = $LASTEXITCODE
& cl.exe /nologo /std:c++20 /c (Join-Path $labProbe 'probe_os_gate.cpp') "/Fo$(Join-Path $labProbe 'os-gate-probe.obj')" 2>&1 | Tee-Object -FilePath (Join-Path $labProbe 'os-gate.log')
$labResults.trainingOsGate = $LASTEXITCODE
& $labCmake -S (Join-Path $labRoot 'vcmi') -B (Join-Path $labProbe 'upstream-build') -G Ninja "-DCMAKE_MAKE_PROGRAM=$labNinja" -DCMAKE_BUILD_TYPE=Release -DENABLE_LAUNCHER=OFF -DENABLE_EDITOR=OFF -DENABLE_TEST=OFF -DENABLE_MMAI=OFF 2>&1 | Tee-Object -FilePath (Join-Path $labProbe 'upstream-configure.log')
$labResults.upstreamConfigure = $LASTEXITCODE
$labResults | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $labProbe 'results.json') -Encoding utf8
