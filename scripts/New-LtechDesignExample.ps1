# Format fixture only. Application persistence lives in src/ltechdesign/persistence.
. (Join-Path $PSScriptRoot 'common.ps1')
Push-Location $projectRoot
try {
    Invoke-Uv run --locked python scripts/generate_native_fixture.py
} finally { Pop-Location }
