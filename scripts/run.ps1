param([ValidateSet('desktop', 'cli')][string]$Mode = 'desktop', [switch]$Smoke,
    [string[]]$CliArgs = @('--help'))

. (Join-Path $PSScriptRoot 'common.ps1')
Push-Location $projectRoot
try {
    if ($Mode -eq 'desktop') {
        $desktopArgs = @()
        if ($Smoke) { $desktopArgs += '--smoke' }
        # python -c invokes the GUI target while retaining stderr in this console.
        Invoke-Uv run --locked python -c 'from ltechdesign.main import main; raise SystemExit(main())' @desktopArgs
    } else {
        Invoke-Uv run --locked ltechdesign-cli @CliArgs
    }
    exit 0
} catch {
    Write-Error $_ -ErrorAction Continue
    exit 1
} finally { Pop-Location }
