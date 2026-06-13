# Security Policy

## Sensitive files

Never commit or share:

```text
config.ini
.env
detected_books*.json
books*.json
manual_books*.json
output/
download/
debug_ebooks*.html
```

`config.ini` can contain Digi4School login credentials.

The book-list JSON files can reveal which e-books are available to an account.

## If you accidentally commit credentials

1. Change the affected password immediately.
2. Remove the secret from the repository.
3. If the secret was pushed, remove it from Git history before making the repository public.

## Reporting security issues

Please open a private security advisory or contact the maintainer directly. Do not post credentials or private book links in public issues.
