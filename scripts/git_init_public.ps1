$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "Initializing clean Git repository..."
Write-Host "===================================="
Write-Host ""

if (Test-Path ".git") {
  Write-Host "This folder already has a .git directory. Aborting."
  exit 1
}

.\scripts\preflight_check.ps1

git init
git add .
git status

Write-Host ""
Write-Host "If the status looks clean, commit with:"
Write-Host 'git commit -m "Initial clean public release"'
