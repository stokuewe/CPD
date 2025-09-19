param(
    [string]$Root = (Get-Location).Path
)

$quickstartPath = Join-Path $Root 'specs/001-milestone-m1-basic/quickstart.md'
if (-not (Test-Path $quickstartPath)) {
    Write-Error "Quickstart file not found at $quickstartPath"
    exit 1
}

$content = Get-Content -Path $quickstartPath
$required = @(
    'Create SQLite project success',
    'Create MSSQL-backed project success',
    'Migration warning shown for outdated schema',
    'Read-only mode set when MSSQL offline',
    'Recent list trimming after >15 entries',
    'Clear list action works',
    'No secrets exposed in logs'
)

$missing = @()
foreach ($item in $required) {
    if (-not ($content -match [regex]::Escape($item))) {
        $missing += $item
    }
}

if ($missing.Count -gt 0) {
    Write-Error "Missing checklist entries:`n - {0}" -f ($missing -join "`n - ")
    exit 1
}

Write-Host "Quickstart validation checklist present." -ForegroundColor Green
