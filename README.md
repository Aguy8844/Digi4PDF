# Digi4PDF

Digi4PDF is a small terminal tool that helps you create personal PDF backups of Digi4School e-books that you can legally access with your own Digi4School account.

It logs into Digi4School, shows your available e-books in a simple menu, and lets you export selected books as PDF files for private use.

## Important notice

Only use this tool for e-books that you personally own or are allowed to access through your own Digi4School account.

Do not use Digi4PDF to download, share, upload, sell, redistribute, or publish copyrighted material. The generated PDFs are intended for private educational use only.

This project is not affiliated with Digi4School, the Austrian school book system, or any publisher.

## Features

* Login with your own Digi4School account
* Simple number-based terminal menu
* Multi-account support
* Searchable book selection
* Download one selected book
* Download all books from your account
* Download single pages or page ranges
* Manual e-book URL entries
* Edit unknown book titles
* Automatic PDF creation
* Chrome/Selenium fallback for newer Digi4School reader pages

## Requirements

You need:

* Windows, macOS, or Linux
* Python 3.10 or newer
* Google Chrome installed
* A valid Digi4School account
* Access to the e-books you want to export

On Windows, the tool automatically handles the required Cairo files for PDF conversion.

## Installation

Clone the repository:

```powershell
git clone https://github.com/Aguy8844/Digi4PDF.git
cd Digi4PDF
```

Create a virtual environment:

```powershell
python -m venv .venv
```

Activate it:

```powershell
.\.venv\Scripts\Activate.ps1
```

Install the required packages:

```powershell
python -m pip install -r requirements.txt
```

Start Digi4PDF:

```powershell
python .\src\main.py
```

## First start

On the first start, Digi4PDF will ask for your Digi4School login:

```text
Account name:
Digi4School e-mail:
Digi4School password:
```

The account name is only a local label. For example:

```text
school
private
my-account
```

Your login data is saved locally in a file called:

```text
config.ini
```

This file is ignored by Git and should never be uploaded or shared.

## How to use

After starting the program, you will see a menu like this:

```text
1  - Show books
2  - Select and download a book
3  - Download all books
4  - Download a single page / page range
5  - Add an e-book URL manually
6  - Remove a saved manual URL
7  - Rescan book list from Digi4School
8  - Edit a book title
9  - Open PDF output folder
10 - Switch account
11 - Add / update account
12 - Show / manage accounts
13 - Help
0  - Exit
```

For most users, the normal workflow is:

```text
1. Show books
2. Select and download a book
9. Open PDF output folder
```

## Downloading a book

Choose:

```text
2 - Select and download a book
```

You can then select a book by:

* entering its number
* entering its Digi4School ID
* typing a search term
* entering `/` to show all books again
* entering `q` to go back

Example:

```text
math
```

This filters the list to books containing “math” in the title or metadata.

## Output folder

Generated PDFs are saved in:

```text
output/
```

Temporary files are stored in:

```text
download/
```

Both folders are ignored by Git.

## Chrome fallback

Some newer Digi4School reader pages do not expose book pages through normal requests.

If that happens, Digi4PDF may open a visible Chrome window. This is expected. The tool uses the authenticated browser session to access the pages and embedded images.

If Chrome opens and the tool asks you to continue manually, log in or open the e-book in that Chrome window, then return to the terminal and press Enter.

## Unknown book titles

Sometimes Digi4School does not expose all book titles cleanly during the automatic scan. In that case, some entries may appear as:

```text
Unknown title
```

You can try:

```text
7 - Rescan book list from Digi4School
```

If the title is still unknown, use:

```text
8 - Edit a book title
```

The edited title is stored locally for that account.

## Multi-account support

Digi4PDF supports multiple local accounts.

Use:

```text
10 - Switch account
11 - Add / update account
12 - Show / manage accounts
```

Each account gets its own local book list.

Account data is stored locally only. Do not share your `config.ini`.

## Classic command mode

The old command-style interface still works:

```text
list-books
download book 6410
download all
download book 6410 page 10 20
```

## Files that are not included in the repository

For privacy and copyright reasons, the following files are ignored:

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

Before publishing changes, you can run:

```powershell
.\scripts\preflight_check.ps1
```

This checks for common private or generated files.

## Security warning

Do not share:

* your `config.ini`
* generated PDFs
* downloaded page files
* private book-list JSON files
* debug HTML files

If you accidentally commit credentials, change your Digi4School password immediately and remove the secret from Git history before making the repository public.

## Disclaimer

Digi4PDF is provided for personal educational use only.

The author does not encourage or support piracy, copyright infringement, or redistribution of copyrighted material.

Use this tool responsibly and only with e-books you are legally allowed to access.
