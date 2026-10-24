param()

# Segment 02: use the production typed boundary; do not maintain a second parser.
. (Join-Path $PSScriptRoot 'common.ps1')
Push-Location $projectRoot
try {
    Invoke-Uv run --locked python scripts/check_file_format.py
    exit 0
} catch {
    Write-Error $_ -ErrorAction Continue
    exit 1
} finally { Pop-Location }
