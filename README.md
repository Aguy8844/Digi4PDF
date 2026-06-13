# Digi4School PDF Helper

> Personal backup helper for Digi4School e-books you can legally access with your own Digi4School account.

This tool logs into Digi4School with your own credentials, lists the e-books available to your account, and can create local PDF files from the reader pages.

## Important legal notice

Use this tool only for e-books that you personally own or are otherwise legally allowed to access through Digi4School.

Do not use it to download, share, upload, sell, redistribute, or publish copyrighted books. The project is intended for personal educational use and backup/accessibility workflows only.

If you are unsure whether a use case is allowed, do not use this tool for that use case.

## Features

- Digi4School login
- Multi-account support
- Number-based terminal menu
- Searchable book selection
- Download individual books
- Download all books for an account
- Download individual pages or page ranges
- Manual e-book URL entries
- Per-account book lists
- Chrome/Selenium fallback for newer Digi4School reader pages
- SVG + embedded image download
- PDF conversion via CairoSVG

## Installation

### 1. Clone the repository

```powershell
git clone https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git
cd YOUR_REPO_NAME
```

### 2. Create a virtual environment

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 3. Install requirements

```powershell
python -m pip install -r requirements.txt
```

### 4. Start

```powershell
python .\src\main.py
```

## First start

On the first start, the program asks for:

- account name
- Digi4School e-mail
- Digi4School password

The credentials are stored locally in `config.ini`.

Do not upload or share `config.ini`.

The public repository contains only `config.example.ini`.

## Usage

After starting the program, use the number menu:

```text
1  - Bücher anzeigen
2  - Buch auswählen und herunterladen
3  - Alle Bücher herunterladen
4  - Einzelne Seite / Seitenbereich herunterladen
5  - E-Book-Link hinzufügen
6  - Gespeicherten manuellen Link entfernen
7  - Bücherliste neu aus Digi4School scannen
8  - Buchtitel bearbeiten
9  - PDF-Ordner öffnen
10 - Account wechseln
11 - Account hinzufügen / aktualisieren
12 - Accounts anzeigen / verwalten
13 - Hilfe
0  - Beenden
```

Old command-style usage still works:

```text
list-books
download book 6410
download all
download book 6410 page 10 20
```

## Output

Generated PDFs are saved in:

```text
output/
```

Temporary page files are stored in:

```text
download/
```

Both folders are ignored by Git.

## Files that must never be committed

The `.gitignore` excludes:

```text
config.ini
detected_books*.json
books*.json
manual_books*.json
download/
output/
dlls/
debug_ebooks*.html
```

Before publishing, run:

```powershell
.\scripts\preflight_check.ps1
```

## Troubleshooting

### Chrome opens during download

That is normal for newer Digi4School reader pages. Some page files and images are only available in the authenticated browser context, so the tool uses Selenium/Chrome as a fallback.

### Some titles show as `Unknown title`

Use:

```text
7 - Bücherliste neu aus Digi4School scannen
```

If some titles remain unknown, use:

```text
8 - Buchtitel bearbeiten
```

### CairoSVG / Cairo DLL errors on Windows

Run the program from `src/main.py`. The project downloads/loads the required Cairo DLLs into `dlls/` on Windows.

## Security

This tool handles login credentials locally. Do not share logs, screenshots, or `config.ini` if they contain private data.

If credentials were accidentally committed, rotate the Digi4School password immediately and remove the secret from Git history before publishing.

## Disclaimer

This project is not affiliated with Digi4School or any publisher. It is provided for educational and personal backup purposes only.
