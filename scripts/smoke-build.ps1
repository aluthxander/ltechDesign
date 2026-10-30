param(
    [ValidateSet('native', 'offscreen')][string]$SmokeMode = 'native',
    [switch]$SkipBuild,
    [string]$Executable = 'dist/windows/ltechDesign-Studio/ltechDesign-Studio.exe'
)

# Native mode intentionally displays the artifact window for this requested spike.
# Offscreen mode is process/event-loop evidence only, suitable for CI.
. (Join-Path $PSScriptRoot 'common.ps1')
$artifactRoot = Join-Path $projectRoot 'artifacts'
New-Item -ItemType Directory -Force -Path $artifactRoot | Out-Null
$reportPath = Join-Path $artifactRoot "segment01a-$SmokeMode.json"
$report = [ordered]@{
    status = 'failed'
    mode = $SmokeMode
    started_at_utc = [DateTime]::UtcNow.ToString('o')
    machine_scope = 'development-or-ci-host; not a clean Windows release test'
    manual_visual_inspection = $false
    expected_title = 'ltechDesign Studio'
    environment = 'Python/Qt paths cleared; PATH restricted to Windows directories'
}
$process = $null
$processStarted = $false
$transcribing = $false
$exitCode = 1
Push-Location $projectRoot
try {
    if ($env:OS -ne 'Windows_NT') { throw 'This spike requires Windows x64' }
    if (-not $SkipBuild) {
        $env:PYINSTALLER_CONFIG_DIR = Join-Path $projectRoot '.cache/pyinstaller'
        Start-Transcript -Path (Join-Path $artifactRoot 'segment01a-session.log') -Force | Out-Null
        $transcribing = $true
        Invoke-Uv sync --locked --group packaging
        $buildArguments = @('run', '--locked', '--group', 'packaging', 'python', '-m',
            'PyInstaller', '--noconfirm', '--clean', '--onedir', '--windowed', '--noupx',
            '--name', 'ltechDesign-Studio', '--distpath', 'dist/windows',
            '--workpath', 'build/pyinstaller', '--specpath', 'build/pyinstaller',
            'scripts/freeze_desktop.py')
        $report.build_command = 'uv ' + ($buildArguments -join ' ')
        # PS 5.1 treats redirected native stderr as ErrorRecords, including INFO.
        # Preserve those log lines while checking the native process exit explicitly.
        $oldPreference = $ErrorActionPreference
        try {
            $ErrorActionPreference = 'Continue'
            & uv @buildArguments 2>&1 | ForEach-Object { $_.ToString() } |
                Tee-Object -FilePath (Join-Path $artifactRoot 'segment01a-build.log')
            $buildExit = $LASTEXITCODE
        } finally { $ErrorActionPreference = $oldPreference }
        if ($buildExit -ne 0) { throw "PyInstaller failed: exit $buildExit" }
        Copy-Item -LiteralPath 'build/pyinstaller/ltechDesign-Studio/warn-ltechDesign-Studio.txt' -Destination (Join-Path $artifactRoot 'segment01a-build-warnings.txt')
    }
    $exePath = if ([IO.Path]::IsPathRooted($Executable)) {
        [IO.Path]::GetFullPath($Executable)
    } else { [IO.Path]::GetFullPath((Join-Path $projectRoot $Executable)) }
    if (-not (Test-Path -LiteralPath $exePath -PathType Leaf)) { throw "Missing artifact: $exePath" }
    $bundleRoot = Split-Path -Parent $exePath
    $required = @('_internal/python312.dll', '_internal/PySide6/Qt6Core.dll',
        '_internal/PySide6/Qt6Gui.dll', '_internal/PySide6/Qt6Widgets.dll',
        '_internal/PySide6/Qt6Svg.dll',
        '_internal/PySide6/plugins/imageformats/qjpeg.dll',
        '_internal/PySide6/plugins/imageformats/qwebp.dll',
        '_internal/PySide6/plugins/platforms/qwindows.dll')
    $report.executable = $exePath
    $report.lock_sha256 = (Get-FileHash -LiteralPath 'uv.lock' -Algorithm SHA256).Hash.ToLowerInvariant()
    $report.executable_sha256 = (Get-FileHash -LiteralPath $exePath -Algorithm SHA256).Hash.ToLowerInvariant()
    $report.required_bundled_files = @($required | ForEach-Object {
        $requiredPath = Join-Path $bundleRoot $_
        if (-not (Test-Path -LiteralPath $requiredPath -PathType Leaf)) { throw "Missing runtime/plugin: $_" }
        @{ path = $_; sha256 = (Get-FileHash -LiteralPath $requiredPath -Algorithm SHA256).Hash.ToLowerInvariant() }
    })
    $files = @(Get-ChildItem -LiteralPath $bundleRoot -Recurse -File)
    $report.bundle_file_count = $files.Count
    $report.bundle_bytes = ($files | Measure-Object -Property Length -Sum).Sum
    $workingDirectory = Join-Path $artifactRoot 'executable-smoke-cwd'
    New-Item -ItemType Directory -Force -Path $workingDirectory | Out-Null
    $start = New-Object System.Diagnostics.ProcessStartInfo
    $start.FileName = $exePath
    $start.UseShellExecute = $false
    # Suppresses a console; the native Qt GUI itself remains visible.
    $start.CreateNoWindow = $true
    $start.WorkingDirectory = $workingDirectory
    foreach ($key in @('PYTHONHOME', 'PYTHONPATH', 'VIRTUAL_ENV', 'QT_PLUGIN_PATH',
        'QT_QPA_PLATFORM_PLUGIN_PATH', 'QML2_IMPORT_PATH', 'QML_IMPORT_PATH')) {
        $start.EnvironmentVariables.Remove($key)
    }
    $start.EnvironmentVariables['PATH'] = "$env:SystemRoot\System32;$env:SystemRoot"
    $start.EnvironmentVariables['QT_QPA_PLATFORM'] = if ($SmokeMode -eq 'native') { 'windows' } else { 'offscreen' }
    if ($SmokeMode -eq 'offscreen') {
        $start.Arguments = '--smoke'
        $start.EnvironmentVariables['LTECHDESIGN_MEDIA_SMOKE_REPORT'] = Join-Path $artifactRoot 'segment12-executable-codecs.json'
        $start.EnvironmentVariables['LTECHDESIGN_PROJECT_SMOKE_REPORT'] = Join-Path $artifactRoot 'segment14-executable-thumbnail.json'
        $start.EnvironmentVariables['LTECHDESIGN_EXPORT_SMOKE_REPORT'] = Join-Path $artifactRoot 'segment15-executable-export.json'
        $start.EnvironmentVariables['LTECHDESIGN_EXPORT_SMOKE_SOURCE'] = Join-Path $projectRoot 'examples/proyek-contoh.ltechdesign'
    }
    $process = New-Object System.Diagnostics.Process
    $process.StartInfo = $start
    $watch = [Diagnostics.Stopwatch]::StartNew()
    if (-not $process.Start()) { throw 'Failed to start artifact' }
    $processStarted = $true
    $report.pid = $process.Id
    if ($SmokeMode -eq 'native') {
        # MainWindowHandle represents the process's visible, unowned main window.
        do {
            $process.Refresh()
            if ($process.HasExited) { throw "Artifact exited before window observation: $($process.ExitCode)" }
            if ($process.MainWindowHandle -ne [IntPtr]::Zero -and
                $process.MainWindowTitle -eq $report.expected_title) { break }
            Start-Sleep -Milliseconds 100
        } while ($watch.ElapsedMilliseconds -lt 15000)
        if ($process.MainWindowHandle -eq [IntPtr]::Zero -or
            $process.MainWindowTitle -ne $report.expected_title) { throw 'Expected native window not observed within 15s' }
        $report.observed_title = $process.MainWindowTitle
        $report.window_handle = $process.MainWindowHandle.ToInt64()
        $report.startup_observation_ms = $watch.ElapsedMilliseconds
        # Hold the real window open before requesting its normal close lifecycle.
        if ($process.WaitForExit(1000)) { throw 'Artifact exited without a close request' }
        $report.loaded_runtime_modules = @($process.Modules | Where-Object {
            $_.ModuleName -in @('python312.dll', 'Qt6Core.dll', 'Qt6Gui.dll', 'Qt6Widgets.dll', 'qwindows.dll')
        } | ForEach-Object { @{ name = $_.ModuleName; path = $_.FileName } })
        if (@($report.loaded_runtime_modules | Where-Object { $_.name -eq 'qwindows.dll' }).Count -ne 1) {
            throw 'Native qwindows plugin not observed in process modules'
        }
        foreach ($relative in $required) {
            $moduleName = [IO.Path]::GetFileName($relative)
            $expectedPath = [IO.Path]::GetFullPath((Join-Path $bundleRoot $relative))
            if (@($report.loaded_runtime_modules | Where-Object {
                $_.name -eq $moduleName -and $_.path -eq $expectedPath
            }).Count -ne 1) { throw "Runtime module not loaded from bundle: $moduleName" }
        }
        $report.close_method = 'Process.CloseMainWindow (normal WM_CLOSE request)'
        if (-not $process.CloseMainWindow()) { throw 'Normal window close request was rejected' }
        $report.close_requested = $true
    } else {
        $report.close_method = '--smoke: QTimer closes window through the Qt event loop'
        $report.native_window_observed = $false
    }
    if (-not $process.WaitForExit(15000)) { throw 'Artifact failed to exit within 15s after close' }
    $report.exit_code = $process.ExitCode
    $report.total_elapsed_ms = $watch.ElapsedMilliseconds
    if ($process.ExitCode -ne 0) { throw "Artifact exit code: $($process.ExitCode)" }
    if ($SmokeMode -eq 'offscreen') {
        $report.codec_smoke = Get-Content -Raw -LiteralPath (Join-Path $artifactRoot 'segment12-executable-codecs.json') | ConvertFrom-Json
    }
    $report.status = 'passed'
    $exitCode = 0
} catch {
    $report.error = $_.Exception.Message
    Write-Error $_ -ErrorAction Continue
} finally {
    if ($null -ne $process) {
        if ($processStarted -and -not $process.HasExited) {
            $process.Kill()
            $process.WaitForExit()
            $report.forced_termination = $true
        }
        $process.Dispose()
    }
    $report.finished_at_utc = [DateTime]::UtcNow.ToString('o')
    $report | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $reportPath -Encoding UTF8
    Write-Output "Executable smoke $($report.status): $reportPath"
    if ($transcribing) { Stop-Transcript | Out-Null }
    Pop-Location
}
exit $exitCode
