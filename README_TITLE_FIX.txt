Digi4School Titel-Verbesserungs-Patch

Dieser Patch ersetzt nur:
- src/handlers/book_fetcher.py
- src/handlers/command_handler.py

Der funktionierende Downloader bleibt unberührt.

Neu:
1. Bessere Titelerkennung beim automatischen Scan
   - liest mehr CSS-Selectoren
   - versucht auch Shadow-DOM/textContent/aria-label/title/alt
   - schreibt erkannte Titel in detected_books_<account>.json

2. Menüpunkt 7 erzwingt einen echten Neu-Scan der Bücherliste für den aktiven Account.
   Alte Scan-Datei wird als .bak gesichert.

3. Menüpunkt 8 erlaubt manuelles Umbenennen von Unknown-title-Einträgen.

Installation:
- Dateien aus der ZIP ersetzen.
- Danach starten:
  python .\src\main.py

Empfohlen:
- Im Menü 7 wählen und neu scannen.
- Falls einzelne Titel trotzdem Unknown bleiben, Menü 8 verwenden.
