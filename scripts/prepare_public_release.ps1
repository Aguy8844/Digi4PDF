$ErrorActionPreference = "Continue"

Write-Host ""
Write-Host "Preparing clean public release folder..."
Write-Host "========================================"
Write-Host ""

Remove-Item -Force -ErrorAction SilentlyContinue `
  .\config.ini, `
  .\.env, `
  .\detected_books*.json, `
  .\books*.json, `
  .\manual_books*.json, `
  .\debug_ebooks*.html, `
  .\test_*.svg

Remove-Item -Recurse -Force -ErrorAction SilentlyContinue `
  .\download, `
  .\output, `
  .\dlls, `
  .\__pycache__, `
  .\.pytest_cache

Get-ChildItem -Recurse -Force -Directory -Filter "__pycache__" -ErrorAction SilentlyContinue | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
Get-ChildItem -Recurse -Force -File -Filter "*.pyc" -ErrorAction SilentlyContinue | Remove-Item -Force -ErrorAction SilentlyContinue

Write-Host "Done. Now run:"
Write-Host ".\scripts\preflight_check.ps1"
