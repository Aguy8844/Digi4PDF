import concurrent.futures
import copy
import json
import os
import re
import shutil
import time
from pathlib import Path

import requests
from bs4 import BeautifulSoup
from tqdm import tqdm

from .authentication import AuthAndTokenHandler
from .book_downloader import BookContentDownloader
from .pdf_convert import SVGtoPDFConverter
from .javascript_executor import Executor
from .config_handler import ConfigHandler


class BookDataRetriever:
    def __init__(self):
        self.books_list_url = "https://digi4school.at/overview"
        self.conv = SVGtoPDFConverter()
        self._cached_books = None

        os.makedirs("download", exist_ok=True)
        os.makedirs("output", exist_ok=True)

    def clear_cache(self):
        self._cached_books = None

    def get_account_suffix(self):
        """
        Keep the old generic JSON files for the default account.
        Other accounts get their own files, e.g. detected_books_school2.json.
        """
        try:
            account_name = ConfigHandler().get_active_account_name()
        except Exception:
            account_name = "default"

        account_name = str(account_name or "default").strip()
        safe_name = self.safe_path_part(account_name)

        if not safe_name or safe_name == "default":
            return ""

        return "_" + safe_name

    def get_books_json_paths(self):
        suffix = self.get_account_suffix()

        if suffix:
            return (
                f"detected_books{suffix}.json",
                f"books{suffix}.json",
                f"manual_books{suffix}.json",
            )

        return (
            "detected_books.json",
            "books.json",
            "manual_books.json",
        )

    def get_detected_books_path(self):
        suffix = self.get_account_suffix()
        return f"detected_books{suffix}.json" if suffix else "detected_books.json"

    def get_manual_books_path(self):
        suffix = self.get_account_suffix()
        return f"manual_books{suffix}.json" if suffix else "manual_books.json"

    def book_from_url(self, title, href):
        href = self.clean_href(href)
        title = str(title or "").strip() or "Untitled e-book"

        code, sub_id = self.parse_ebook_url(href)
        if not code:
            raise ValueError("This does not look like a Digi4School e-book link.")

        book_id = f"{code}-{sub_id}" if sub_id else code
        return (book_id, code, title, href, sub_id)

    def add_manual_book(self, title, href):
        book = self.book_from_url(title, href)
        books = self.load_books_json(self.get_manual_books_path())

        books = [b for b in books if b[0] != book[0]]
        books.append(book)

        self.write_books_json(self.get_manual_books_path(), books)
        self.clear_cache()
        return book

    def remove_manual_book(self, selector):
        books = self.load_books_json(self.get_manual_books_path())
        if not books:
            return False

        selector = str(selector).strip()
        target_id = None

        if selector.isdigit():
            index = int(selector)
            if 1 <= index <= len(books):
                target_id = books[index - 1][0]
        else:
            target_id = selector

        if not target_id:
            return False

        new_books = [b for b in books if b[0] != target_id]
        if len(new_books) == len(books):
            return False

        self.write_books_json(self.get_manual_books_path(), new_books)
        self.clear_cache()
        return True

    def write_books_json(self, path, books):
        data = [
            {
                "id": book[0],
                "code": book[1],
                "sub_id": book[4] if len(book) > 4 else "",
                "title": book[2],
                "href": book[3] if len(book) > 3 else "",
            }
            for book in books
        ]

        Path(path).write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    def get_book_list(self, session: requests.Session):
        if self._cached_books is not None:
            return self._cached_books

        self._validate_session(session)

        books = []

        # Prefer account-specific detected/manual lists.
        # For the default account this keeps using the old filenames:
        # detected_books.json, books.json, manual_books.json.
        for path in self.get_books_json_paths():
            loaded = self.load_books_json(path)
            for book in loaded:
                if not any(existing[0] == book[0] for existing in books):
                    books.append(book)

        # Old static parser, if the old shelf page still exists.
        for book in self.get_book_list_static(session):
            if not any(existing[0] == book[0] for existing in books):
                books.append(book)

        if books:
            self._cached_books = books
            return books

        print("No saved/static list found for this account. Trying Selenium scan...")
        books = self.get_book_list_selenium(session)

        self._cached_books = books
        return books

    def load_books_json(self, path):
        p = Path(path)
        if not p.exists():
            return []

        try:
            raw = json.loads(p.read_text(encoding="utf-8"))
            books = []

            for item in raw:
                title = str(item.get("title") or item.get("name") or "Unknown title").strip()
                href = str(item.get("href") or item.get("url") or "").strip()
                code = str(item.get("code") or item.get("id") or "").strip()
                sub_id = str(item.get("sub_id") or "").strip()

                if href:
                    parsed_code, parsed_sub_id = self.parse_ebook_url(href)
                    if parsed_code:
                        code = parsed_code
                    if parsed_sub_id:
                        sub_id = parsed_sub_id

                if not code:
                    continue

                book_id = f"{code}-{sub_id}" if sub_id else code

                if not href:
                    href = f"https://a.digi4school.at/ebook/{code}/{sub_id}/" if sub_id else f"https://a.digi4school.at/ebook/{code}/"

                href = self.clean_href(href)
                books.append((book_id, code, title, href, sub_id))

            return books

        except Exception as exc:
            print(f"Could not read {path}: {exc}")
            return []

    def get_book_list_static(self, session: requests.Session):
        books = []

        try:
            response = session.get(self.books_list_url, timeout=15)
        except Exception:
            return []

        soup = BeautifulSoup(response.content, "html.parser")

        with open("debug_ebooks_raw.html", "wb") as f:
            f.write(response.content)

        shelf_div = soup.find(id="shelf")
        if shelf_div is None:
            return []

        for a_tag in shelf_div.find_all("a"):
            data_id = a_tag.get("data-id")
            data_code = a_tag.get("data-code")

            h1 = a_tag.find("h1")
            book_title = h1.text.strip() if h1 else "Unknown title"
            href = a_tag.get("href") or ""

            if data_id and data_code:
                books.append((str(data_id), str(data_code), book_title, href, ""))

        return books

    def force_rescan_current_account(self, session: requests.Session):
        """
        Ignore the saved detected list for the active account and scan Digi4School again.
        The old detected file is kept as .bak, just in case.
        """
        self.clear_cache()

        detected_path = Path(self.get_detected_books_path())
        if detected_path.exists():
            backup = detected_path.with_suffix(detected_path.suffix + ".bak")
            try:
                detected_path.replace(backup)
                print(f"Old scan file saved as: {backup.name}")
            except Exception:
                pass

        books = self.get_book_list_selenium(session)
        self._cached_books = books
        return books

    def update_book_title(self, selector, new_title):
        """
        Update the title in all known JSON lists for the active account.
        Works for detected_books*.json, books*.json and manual_books*.json.
        """
        selector = str(selector).strip()
        new_title = str(new_title or "").strip()

        if not selector or not new_title:
            return False

        changed = False

        for path in self.get_books_json_paths():
            books = self.load_books_json(path)
            if not books:
                continue

            # allow list index inside this file
            target_id = None
            if selector.isdigit():
                index = int(selector)
                if 1 <= index <= len(books):
                    target_id = books[index - 1][0]

            for i, book in enumerate(books):
                book_id = str(book[0])
                code = str(book[1])

                if book_id == selector or code == selector or (target_id and book_id == target_id):
                    book_list = list(book)
                    while len(book_list) < 5:
                        book_list.append("")
                    book_list[2] = new_title
                    books[i] = tuple(book_list)
                    changed = True

            if changed:
                self.write_books_json(path, books)

        if changed:
            self.clear_cache()

        return changed

    def title_is_unknown(self, title):
        title = str(title or "").strip().lower()
        return not title or title in ("unknown title", "unbekannt", "unbenanntes e-book", "untitled")

    def enrich_unknown_titles_from_overview(self, books, driver=None):
        """
        If some entries are still 'Unknown title', try a second pass over the current
        rendered overview page. This uses deep DOM text extraction and href/code mapping.
        """
        if not driver:
            return books

        try:
            entries = driver.find_elements("css selector", "app-book-list-entry")
        except Exception:
            return books

        code_to_title = {}

        for entry in entries:
            try:
                title = self.extract_title_from_entry(entry)
                href = self.extract_href_from_entry(entry)
                code, sub_id = self.parse_ebook_url(href)

                if code and title and not self.title_is_unknown(title):
                    code_to_title[code] = title
            except Exception:
                continue

        if not code_to_title:
            return books

        enriched = []
        for book in books:
            book_list = list(book)
            while len(book_list) < 5:
                book_list.append("")

            code = str(book_list[1])
            if self.title_is_unknown(book_list[2]) and code in code_to_title:
                book_list[2] = code_to_title[code]

            enriched.append(tuple(book_list))

        return enriched

    def get_book_list_selenium(self, session: requests.Session):
        books = []

        try:
            from selenium import webdriver
            from selenium.webdriver.chrome.options import Options
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support.ui import WebDriverWait
        except Exception as exc:
            print(f"Selenium is not available: {exc}")
            return []

        driver = None

        try:
            options = Options()
            options.add_argument("--start-maximized")

            driver = webdriver.Chrome(options=options)
            wait = WebDriverWait(driver, 20)

            driver.get("https://digi4school.at/")
            self.copy_requests_cookies_to_selenium(session, driver)

            driver.get(self.books_list_url)
            wait.until(lambda d: "digi4school" in d.title.lower() or d.find_elements(By.CSS_SELECTOR, "app-root"))
            time.sleep(4)

            with open("debug_ebooks_rendered.html", "w", encoding="utf-8") as f:
                f.write(driver.page_source)

            entries = driver.find_elements(By.CSS_SELECTOR, "app-book-list-entry")
            if not entries:
                print("No app-book-list-entry elements found.")
                return []

            count = len(entries)
            print(f"Found {count} book entries. Reading reader URLs...")

            for i in range(count):
                try:
                    driver.get(self.books_list_url)
                    time.sleep(2)
                    entries = driver.find_elements(By.CSS_SELECTOR, "app-book-list-entry")
                    if i >= len(entries):
                        break

                    entry = entries[i]
                    title = self.extract_title_from_entry(entry)
                    href = self.click_entry_and_get_url(driver, entry)

                    code, sub_id = self.parse_ebook_url(href)
                    if not code:
                        continue

                    book_id = f"{code}-{sub_id}" if sub_id else code
                    href = self.clean_href(href)

                    books.append((book_id, code, title, href, sub_id))
                    print(f"{len(books):>2}. {book_id} - {title}")

                except Exception as exc:
                    print(f"Skipping book #{i + 1}: {exc}")

            books = self.enrich_unknown_titles_from_overview(books, driver)
            self.write_detected_books(books)
            return books

        except Exception as exc:
            print(f"Selenium scan failed: {exc}")
            return []

        finally:
            if driver is not None:
                try:
                    driver.quit()
                except Exception:
                    pass

    def copy_requests_cookies_to_selenium(self, session, driver):
        for cookie in session.cookies:
            try:
                domain = cookie.domain or ".digi4school.at"
                if "digi4school.at" not in domain:
                    continue

                selenium_cookie = {
                    "name": cookie.name,
                    "value": cookie.value,
                    "domain": domain,
                    "path": cookie.path or "/",
                }

                if cookie.expires:
                    selenium_cookie["expiry"] = int(cookie.expires)

                driver.add_cookie(selenium_cookie)
            except Exception:
                pass

    def extract_title_from_entry(self, entry):
        """
        Robust title extraction for the newer Angular/Ionic Digi4School overview.
        Some titles are hidden inside web components, so Selenium .text alone can fail.
        """
        selectors = [
            "h1",
            "h2",
            "h3",
            "h2.entry-heading",
            ".entry-heading",
            ".book-title",
            ".title",
            "ion-label",
            "strong",
            "p",
            "span",
        ]

        for selector in selectors:
            try:
                elements = entry.find_elements("css selector", selector)
                for element in elements:
                    text = element.text.strip()
                    if self.looks_like_book_title(text):
                        return self.cleanup_title(text)

                    text = element.get_attribute("textContent") or ""
                    text = text.strip()
                    if self.looks_like_book_title(text):
                        return self.cleanup_title(text)
            except Exception:
                pass

        # Try useful attributes.
        for attr in ("aria-label", "title", "alt"):
            try:
                value = entry.get_attribute(attr) or ""
                if self.looks_like_book_title(value):
                    return self.cleanup_title(value)
            except Exception:
                pass

        # Deep DOM/shadow-root text extraction.
        try:
            driver = entry.parent
            text = driver.execute_script("""
                function collectText(node) {
                    if (!node) return "";
                    let out = "";

                    if (node.nodeType === Node.TEXT_NODE) {
                        return node.textContent || "";
                    }

                    if (node.nodeType === Node.ELEMENT_NODE) {
                        const tag = (node.tagName || "").toLowerCase();
                        if (["script", "style", "svg", "path"].includes(tag)) return "";

                        for (const attr of ["aria-label", "title", "alt"]) {
                            const v = node.getAttribute && node.getAttribute(attr);
                            if (v) out += "\\n" + v;
                        }

                        if (node.shadowRoot) {
                            out += "\\n" + collectText(node.shadowRoot);
                        }

                        for (const child of node.childNodes) {
                            out += "\\n" + collectText(child);
                        }
                    }

                    return out;
                }

                return collectText(arguments[0]);
            """, entry)

            for line in str(text).splitlines():
                line = line.strip()
                if self.looks_like_book_title(line):
                    return self.cleanup_title(line)

        except Exception:
            pass

        # Last resort: visible block text.
        text = entry.text.strip()
        for line in text.splitlines():
            line = line.strip()
            if self.looks_like_book_title(line):
                return self.cleanup_title(line)

        return "Unknown title"

    def looks_like_book_title(self, text):
        text = str(text or "").strip()

        if len(text) < 4:
            return False

        bad_fragments = [
            "öffnen",
            "open",
            "download",
            "e-book",
            "ebook",
            "zum buch",
            "buch öffnen",
            "aktivieren",
        ]

        lowered = text.lower()
        if lowered in bad_fragments:
            return False

        # Avoid huge chunks of the whole page.
        if len(text) > 220:
            return False

        # A useful title usually contains letters, not just numbers/icons.
        return any(ch.isalpha() for ch in text)

    def cleanup_title(self, title):
        title = re.sub(r"\s+", " ", str(title or "")).strip()
        title = re.sub(r"^(öffnen|open|buch öffnen)\s*[:\\-]?\s*", "", title, flags=re.I)
        title = re.sub(r"\s*(öffnen|open|buch öffnen)$", "", title, flags=re.I)
        return title.strip() or "Unknown title"

    def extract_href_from_entry(self, entry):
        try:
            links = entry.find_elements("css selector", "a[href]")
            for link in links:
                href = link.get_attribute("href") or ""
                if "/ebook/" in href:
                    return href
        except Exception:
            pass

        try:
            html = entry.get_attribute("outerHTML") or ""
            match = re.search(r"https://a\.[^\"']+/ebook/\d+(?:/\d+)?/(?:index\.html)?(?:\?[^\"']*)?", html)
            if match:
                return match.group(0)

            match = re.search(r"/ebook/\d+(?:/\d+)?/(?:index\.html)?(?:\?[^\"']*)?", html)
            if match:
                return "https://a.digi4school.at" + match.group(0)
        except Exception:
            pass

        return ""

    def click_entry_and_get_url(self, driver, entry):
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait

        wait = WebDriverWait(driver, 20)

        before_handles = set(driver.window_handles)
        before_url = driver.current_url

        try:
            clickable = entry.find_element(By.CSS_SELECTOR, "div[role='button']")
        except Exception:
            clickable = entry

        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", clickable)
        time.sleep(0.3)
        driver.execute_script("arguments[0].click();", clickable)

        wait.until(lambda d: set(d.window_handles) != before_handles or d.current_url != before_url)

        after_handles = set(driver.window_handles)
        new_handles = list(after_handles - before_handles)

        if new_handles:
            driver.switch_to.window(new_handles[0])

        time.sleep(2)
        current_url = driver.current_url

        if "/ebook/" not in current_url:
            html = driver.page_source
            match = re.search(r"https://a\.[^\"']+/ebook/\d+(?:/\d+)?/(?:index\.html)?(?:\?[^\"']*)?", html)
            if match:
                current_url = match.group(0)

        if new_handles:
            driver.close()
            driver.switch_to.window(list(before_handles)[0])

        if "/ebook/" not in current_url:
            raise RuntimeError("No ebook URL found after click.")

        return current_url

    def parse_ebook_url(self, href):
        match = re.search(r"/ebook/(\d+)(?:/(\d+))?", str(href))
        if not match:
            return "", ""

        return match.group(1), match.group(2) or ""

    def clean_href(self, href):
        href = str(href).strip()
        href = href.split("#", 1)[0].split("?", 1)[0]
        href = re.sub(r"/index\.html$", "/", href)
        if not href.endswith("/"):
            href += "/"
        return href

    def write_detected_books(self, books):
        data = [
            {
                "id": book[0],
                "code": book[1],
                "sub_id": book[4],
                "title": book[2],
                "href": book[3],
            }
            for book in books
        ]
        Path(self.get_detected_books_path()).write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    def download_page(self, data, session: requests.Session, start_page=None, end_page=None, disable_titlepage_check=False):
        self._validate_session(session)

        download = BookContentDownloader(session)
        starttime = time.perf_counter()
        down_dir = Path("download") / self.safe_path_part(data[0])
        os.makedirs(down_dir, exist_ok=True)

        if disable_titlepage_check:
            first_non_titlepage = 1
        else:
            print("Getting first non-titlepage" + " " * 50, end="\r")
            url = AuthAndTokenHandler().token_processing(data, session)
            executor = Executor()
            first_non_titlepage = executor.find_first_non_titlepage(url)

        print("Authenticating" + " " * 50, end="\r")
        url = AuthAndTokenHandler().token_processing(data, session)

        svg_success = download.download_pages(
            down_dir,
            url,
            start_page,
            end_page,
            first_non_titlepage,
            show_progress=True,
        )

        if not svg_success:
            print("Failed to download SVG files.\n")
            shutil.rmtree(down_dir, ignore_errors=True)
            return

        img_success = download.download_images(down_dir, url, show_progress=True)

        if not img_success:
            print("Failed to download images.\n")
            shutil.rmtree(down_dir, ignore_errors=True)
            return

        self.convert_and_cleanup(down_dir, data, starttime)

    def download_single_book(self, data, session: requests.Session):
        self._validate_session(session)

        download = BookContentDownloader(session)
        starttime = time.perf_counter()
        down_dir = Path("download") / self.safe_path_part(data[0])
        os.makedirs(down_dir, exist_ok=True)

        print("Authenticating" + " " * 50, end="\r")
        url = AuthAndTokenHandler().token_processing(data, session)
        print(f"Book base URL: {url}")

        svg_success = download.download_svgs(down_dir, url, show_progress=True)

        if not svg_success:
            print("Failed to download SVG files.\n")
            shutil.rmtree(down_dir, ignore_errors=True)
            return

        img_success = download.download_images(down_dir, url, show_progress=True)

        if not img_success:
            print("Failed to download images.\n")
            shutil.rmtree(down_dir, ignore_errors=True)
            return

        self.convert_and_cleanup(down_dir, data, starttime)

    def download_all_books(self, data, session: requests.Session):
        self._validate_session(session)

        if not data:
            print("No books found. Nothing to download.")
            return

        for book in data:
            print(f"\nDownloading: {book[2]}")
            self.download_single_book(book, session)

    def convert_and_cleanup(self, down_dir, data, starttime):
        svg_success, error_code = self.conv.convert_all_svgs_to_pdf(
            down_dir,
            data[2],
            show_progress=True,
        )

        if svg_success:
            if error_code == "missingsize":
                print("Warning: SVG size parameter missing. PDF scaling may be wrong.\n")

            time_taken = time.perf_counter() - starttime
            minutes, seconds = divmod(time_taken, 60)
            print(f"Downloaded '{data[2]}' in {int(minutes)} minutes and {seconds:.2f} seconds.\n")
        else:
            print(f"Error converting to PDF: {error_code}")
            shutil.rmtree(down_dir, ignore_errors=True)
            return

        shutil.rmtree(down_dir, ignore_errors=True)

    def safe_path_part(self, value):
        return re.sub(r"[^a-zA-Z0-9_-]", "_", str(value))

    def _validate_session(self, session):
        if session is None or ("ad_session_id" not in session.cookies and "digi4s" not in session.cookies):
            raise RuntimeError("Session is not initialized or user is not authenticated.")
