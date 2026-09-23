$ErrorActionPreference = 'Stop'
$launchArguments = @($args)
$candidates = @()
$candidates += ,@((Join-Path $PSScriptRoot '.venv/Scripts/python.exe'))
if ($env:AYQYN_PYTHON) { $candidates += ,@($env:AYQYN_PYTHON) }
$candidates += ,@('py', '-3')
$candidates += ,@('python3')
$candidates += ,@('python')
if ($env:USERPROFILE) {
    $candidates += ,@((Join-Path $env:USERPROFILE '.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe'))
}
foreach ($candidate in $candidates) {
    $executable = $candidate[0]
    if (-not (Get-Command $executable -ErrorAction SilentlyContinue)) { continue }
    $prefix = @($candidate | Select-Object -Skip 1)
    try {
        & $executable @prefix -c 'import sys; sys.exit(sys.version_info < (3, 10))' 2>$null | Out-Null
        if ($LASTEXITCODE -ne 0) { continue }
    } catch {
        continue
    }
    & $executable @prefix (Join-Path $PSScriptRoot 'scripts/bootstrap.py') @launchArguments
    exit $LASTEXITCODE
}
Write-Error 'Python 3.10+ is required. Install it from https://www.python.org/downloads/windows/ and enable Add python.exe to PATH, then run this script again.'
exit 1
