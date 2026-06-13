$ErrorActionPreference = "Continue"

Write-Host ""
Write-Host "Digi4School PDF Helper - Public Release Preflight Check"
Write-Host "======================================================="
Write-Host ""

$badPatterns = @(
  "config.ini",
  ".env",
  "detected_books*.json",
  "books*.json",
  "manual_books*.json",
  "debug_ebooks*.html",
  "test_*.svg",
  "*.pdf"
)

$badDirs = @(
  "download",
  "output",
  "dlls",
  "__pycache__",
  ".venv",
  "venv",
  "env",
  ".pytest_cache"
)

$found = @()

foreach ($pattern in $badPatterns) {
  $items = Get-ChildItem -Recurse -Force -File -Filter $pattern -ErrorAction SilentlyContinue
  foreach ($item in $items) {
    if ($item.FullName -notmatch "\\.git\\") {
      $found += $item.FullName
    }
  }
}

foreach ($dir in $badDirs) {
  $items = Get-ChildItem -Recurse -Force -Directory -Filter $dir -ErrorAction SilentlyContinue
  foreach ($item in $items) {
    if ($item.FullName -notmatch "\\.git\\") {
      $found += $item.FullName
    }
  }
}

Write-Host "Checking for common sensitive/generated files..."
if ($found.Count -eq 0) {
  Write-Host "OK: No obvious sensitive/generated files found." -ForegroundColor Green
} else {
  Write-Host "WARNING: Found files/folders that should not be committed:" -ForegroundColor Yellow
  $found | Sort-Object | ForEach-Object { Write-Host " - $_" }
}

Write-Host ""
Write-Host "Searching for likely real credentials..."

$textFiles = Get-ChildItem -Recurse -Force -File -ErrorAction SilentlyContinue |
  Where-Object {
    $_.FullName -notmatch "\\.git\\" -and
    $_.Name -ne "config.example.ini" -and
    $_.Extension -in @(".py", ".md", ".txt", ".ini", ".json", ".ps1", ".toml", ".cfg", ".yml", ".yaml")
  }

$patterns = @(
  "[A-Za-z0-9._%+-]+@(gmail|outlook|icloud|hotmail|gmx|yahoo|protonmail)\.[A-Za-z]{2,}",
  "password\s*=\s*['""][^'""]{4,}['""]",
  "passwort\s*=\s*['""][^'""]{4,}['""]"
)

$secretHits = @()

foreach ($file in $textFiles) {
  try {
    $hits = Select-String -Path $file.FullName -ErrorAction SilentlyContinue -Pattern $patterns
    foreach ($hit in $hits) {
      $line = $hit.Line.Trim()

      if ($line -match "your-email@example.com") {
        continue
      }

      if ($line -match "author_email=''") {
        continue
      }

      $secretHits += $hit
    }
  } catch {
    # ignore unreadable files
  }
}

if ($secretHits.Count -gt 0) {
  Write-Host "WARNING: Possible real secrets/private data found:" -ForegroundColor Yellow
  $secretHits | ForEach-Object {
    Write-Host (" - {0}:{1}: {2}" -f $_.Path, $_.LineNumber, $_.Line.Trim())
  }
} else {
  Write-Host "OK: No obvious real credential strings found." -ForegroundColor Green
}

Write-Host ""

if (Test-Path ".git") {
  Write-Host "Git status:"
  git status --short
} else {
  Write-Host "Git status:"
  Write-Host "No Git repository initialized yet. This is OK before running git init." -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Preflight done."
