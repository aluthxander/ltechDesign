param([string]$Subsystem = 'all')

. (Join-Path $PSScriptRoot 'common.ps1')
$supported = @('all', 'docs', 'core', 'desktop', 'lint', 'types', 'fixtures', 'package')
if ($Subsystem -notin $supported) {
    Write-Error "Unavailable subsystem '$Subsystem'. Available: $($supported -join ', ')" -ErrorAction Continue
    exit 2
}
Push-Location $projectRoot
try {
    if ($Subsystem -in @('all', 'docs')) {
        # Child process isolates existing audit scripts' exit statements.
        $psExe = (Get-Process -Id $PID).Path
        & $psExe -NoProfile -ExecutionPolicy Bypass -File scripts/check-segment00.ps1 -RequirePrerequisites
        if ($LASTEXITCODE -ne 0) { throw 'Documentation audit failed' }
    }
    if ($Subsystem -ne 'docs') {
        Invoke-Uv sync --locked
        if ($Subsystem -in @('all', 'lint')) {
            Invoke-Uv run --locked ruff check .
            Invoke-Uv run --locked ruff format --check .
        }
        if ($Subsystem -in @('all', 'types')) { Invoke-Uv run --locked mypy }
        if ($Subsystem -in @('all', 'fixtures')) {
            Invoke-Uv run --locked python scripts/generate_fixtures.py --check
        }
        if ($Subsystem -in @('all', 'core')) {
            Invoke-Uv run --locked pytest -m core --junitxml=artifacts/core.xml
        }
        if ($Subsystem -in @('all', 'desktop')) {
            $oldPlatform = $env:QT_QPA_PLATFORM
            try {
                $env:QT_QPA_PLATFORM = 'offscreen'
                Invoke-Uv run --locked pytest -m desktop --junitxml=artifacts/desktop.xml
            } finally { $env:QT_QPA_PLATFORM = $oldPlatform }
        }
        if ($Subsystem -in @('all', 'package')) {
            Invoke-Uv build --no-sources
            if ($LASTEXITCODE -ne 0) { throw 'Package build failed' }
            # Isolated non-editable wheel install; no development dependencies.
            Invoke-Uv venv --clear .cache/package-smoke
            $oldEnvironment = $env:UV_PROJECT_ENVIRONMENT
            try {
                $env:UV_PROJECT_ENVIRONMENT = Join-Path $projectRoot '.cache/package-smoke'
                Invoke-Uv sync --locked --offline --no-dev --no-install-project
            } finally { $env:UV_PROJECT_ENVIRONMENT = $oldEnvironment }
            Invoke-Uv pip install --offline --python .cache/package-smoke/Scripts/python.exe --no-deps dist/ltechdesign-0.1.0-py3-none-any.whl
            & .cache/package-smoke/Scripts/python.exe -I -m ltechdesign --version
            if ($LASTEXITCODE -ne 0) { throw 'Installed wheel smoke failed' }
            & .cache/package-smoke/Scripts/python.exe -I -c "import sys; from ltechdesign.domain import create_project, dump_project, load_project; p=create_project(); assert load_project(dump_project(p, {})).document == p.document; assert not any(k.startswith(('PySide', 'PyQt')) for k in sys.modules)"
            if ($LASTEXITCODE -ne 0) { throw 'Installed wheel domain/JSON smoke failed' }
            & .cache/package-smoke/Scripts/python.exe -I scripts/check_persistence.py examples/proyek-contoh.ltechdesign --scratch artifacts/persistence-wheel
            if ($LASTEXITCODE -ne 0) { throw 'Installed wheel native persistence smoke failed' }
            $oldPlatform = $env:QT_QPA_PLATFORM
            try {
                $env:QT_QPA_PLATFORM = 'offscreen'
                & .cache/package-smoke/Scripts/python.exe -I -m ltechdesign gui --smoke
                if ($LASTEXITCODE -ne 0) { throw 'Installed wheel desktop smoke failed' }
            } finally { $env:QT_QPA_PLATFORM = $oldPlatform }
        }
    }
    exit 0
} catch {
    Write-Error $_ -ErrorAction Continue
    exit 1
} finally { Pop-Location }
