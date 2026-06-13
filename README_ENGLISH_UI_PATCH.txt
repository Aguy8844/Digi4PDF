# English UI patch

This patch switches the user-facing terminal interface to English while keeping the existing command names.

Replaced files:

```text
src/handlers/command_handler.py
src/handlers/book_downloader.py
src/handlers/book_fetcher.py
```

After applying:

```powershell
python .\src\main.py
.\scripts\preflight_check.ps1
git add .
git commit -m "Switch terminal UI to English"
git push
```
