Param(
    [switch]$Clean
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot

Set-Location $RepoRoot

if ($Clean) {
    if (Test-Path build) {
        Remove-Item -LiteralPath build -Recurse -Force
    }
    if (Test-Path dist) {
        Remove-Item -LiteralPath dist -Recurse -Force
    }
}

poetry install --with build --extras docx
poetry run pyinstaller --noconfirm --clean materialcard.spec

Write-Host ""
Write-Host "Built EXE:"
Write-Host "  $RepoRoot\dist\materialcard.exe"
