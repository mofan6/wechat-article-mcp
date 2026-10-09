$ErrorActionPreference = 'Stop'
$taskRoot = $PSScriptRoot
$taskPython = Get-Command python -ErrorAction SilentlyContinue
if ($taskPython) {
    & $taskPython.Source (Join-Path $taskRoot 'bootstrap.py') @args
} else {
    $taskPy = Get-Command py -ErrorAction SilentlyContinue
    if (-not $taskPy) { throw 'Install Python 3.11+ first, then run setup.ps1 again.' }
    & $taskPy.Source -3 (Join-Path $taskRoot 'bootstrap.py') @args
}
if ($LASTEXITCODE -ne 0) { throw 'Setup failed; inspect the error above.' }
