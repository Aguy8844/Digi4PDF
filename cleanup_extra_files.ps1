cd C:\Users\phili\Documents\digi4school-2-pdf

Remove-Item -Force -ErrorAction SilentlyContinue `
  .\web_app.py, `
  .\requirements_web.txt, `
  .\WEBSITE_STARTEN.bat, `
  .\WEBSITE_INSTALLIEREN.bat, `
  .\ANLEITUNG_WEBSITE.txt, `
  .\STARTEN.bat, `
  .\INSTALLIEREN.bat, `
  .\ANLEITUNG_FUER_FREUNDIN.txt, `
  .\README_CAIRO_FIX.txt, `
  .\README_DOWNLOAD_FIX.txt, `
  .\README_HPTHEK_FIX.txt, `
  .\test_6410_3.svg, `
  .\debug_ebooks.html, `
  .\debug_ebooks_raw.html, `
  .\debug_ebooks_rendered.html, `
  .\debug_ebooks_rendered_books.html

Remove-Item -Recurse -Force -ErrorAction SilentlyContinue .\download
