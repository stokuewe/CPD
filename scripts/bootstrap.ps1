param(
    [string]$Python = "python"
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path '.venv')) {
    Write-Host 'Creating virtual environment (.venv)...'
    & $Python -m venv .venv
}

$venvPython = Join-Path (Resolve-Path '.venv').Path 'Scripts/python.exe'
Write-Host 'Upgrading pip...'
& $venvPython -m pip install --upgrade pip
Write-Host 'Installing project requirements...'
& $venvPython -m pip install -r requirements.txt
Write-Host 'Bootstrap complete.'
