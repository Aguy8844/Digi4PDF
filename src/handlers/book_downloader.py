import base64
import os
import re
import time

import requests
import tqdm
from requests.exceptions import HTTPError, RequestException


class BookContentDownloader:
    def __init__(self, session) -> None:
        self.session: requests.Session = session

    def download_svgs(self, down_dir, url, show_progress=False):
        file_url, special_book_url = self.get_file_url(url)

        if file_url is None:
            print("Direct download did not receive real SVG files.")
            print("Starting visible Chrome fallback...")
            return self.download_svgs_with_browser(down_dir, url, show_progress=show_progress)

        total_pages = self.get_total_pages(file_url) if show_progress else None
        counter = 1
        downloaded = 0

        with tqdm.tqdm(total=total_pages, desc="Downloading svgs", unit="svg", disable=not show_progress) as pbar:
            while True:
                file_url_with_counter = file_url.format(counter, counter)

                try:
                    response = self.session.get(file_url_with_counter, timeout=10)

                    if response.status_code == 404:
                        if counter == 1:
                            return False
                        break

                    if not self.is_svg_response(response):
                        if counter == 1:
                            return False
                        break

                    if counter > 1500:
                        print("Stopped after 1500 pages as a safety limit.")
                        break

                    response.raise_for_status()

                except (RequestException, HTTPError):
                    if counter == 1:
                        print(f"Download error: {file_url_with_counter}")
                        return False
                    break

                svg_text = response.text

                if special_book_url:
                    svg_text = self.modify_svg_text(svg_text, counter)

                with open(f"{down_dir}/{counter}.svg", "w+", encoding="utf8") as svg_file:
                    svg_file.write(svg_text)

                counter += 1
                downloaded += 1
                pbar.update(1)

        return downloaded > 0

    def download_pages(self, down_dir, url, start_page, end_page, first_non_titlepage, show_progress=False):
        total_page_range = end_page - start_page + 1 if end_page else 1
        end_page = end_page if end_page else start_page

        file_url, special_book_url = self.get_file_url(url)

        if file_url is None:
            print("Direct download did not receive real SVG files.")
            print("Starting visible Chrome fallback...")
            return self.download_pages_with_browser(
                down_dir,
                url,
                start_page,
                end_page,
                first_non_titlepage,
                show_progress=show_progress,
            )

        counter = start_page + first_non_titlepage - 1
        downloaded = 0

        with tqdm.tqdm(total=total_page_range, desc="Downloading svgs", unit="svg", disable=not show_progress) as pbar:
            while counter <= end_page + first_non_titlepage - 1:
                file_url_with_counter = file_url.format(counter, counter)

                try:
                    response = self.session.get(file_url_with_counter, timeout=10)

                    if response.status_code == 404:
                        if downloaded == 0:
                            return False
                        break

                    if not self.is_svg_response(response):
                        if downloaded == 0:
                            return False
                        break

                    response.raise_for_status()

                except (RequestException, HTTPError):
                    if downloaded == 0:
                        print(f"Download error: {file_url_with_counter}")
                        return False
                    break

                svg_text = response.text

                if special_book_url:
                    svg_text = self.modify_svg_text(svg_text, counter)

                with open(f"{down_dir}/{counter}.svg", "w+", encoding="utf8") as svg_file:
                    svg_file.write(svg_text)

                counter += 1
                downloaded += 1
                pbar.update(1)

        return downloaded > 0

    def download_images(self, svg_dir, url, show_progress=False):
        svg_files = os.listdir(svg_dir)
        images_urls = []

        for file in svg_files:
            with open(f"{svg_dir}/{file}", "rb") as svg_file:
                svg_contents = svg_file.read().decode("utf-8")

            matches = re.findall(r'<image\s.*?xlink:href="([^"]*)".*?>', svg_contents)
            if matches:
                images_urls.extend(matches)

        # Remove duplicates but keep order.
        images_urls = list(dict.fromkeys(images_urls))

        total_image = len(images_urls) if show_progress else None
        base_url = self.clean_base_url(url)

        failed = []

        with tqdm.tqdm(total=total_image, desc="Downloading images", unit="image", disable=not show_progress) as pbar:
            for xlink_href in images_urls:
                image_url = self.join_url(base_url, xlink_href)
                dirname = f"{svg_dir}/{os.path.dirname(xlink_href)}"
                os.makedirs(dirname, exist_ok=True)
                target = os.path.join(dirname, os.path.basename(xlink_href))

                ok = False

                try:
                    response = self.session.get(image_url, timeout=10)
                    if self.is_binary_image_response(response):
                        with open(target, "wb") as img_file:
                            img_file.write(response.content)
                        ok = True
                except requests.RequestException:
                    ok = False

                if not ok:
                    failed.append((xlink_href, image_url, target))

                pbar.update(1)

        if failed:
            print("")
            print(f"{len(failed)} images could not be downloaded with requests.")
            print("Trying to download images through the Chrome context...")

            driver = self.make_logged_in_driver(base_url)
            if driver is None:
                print("Chrome image fallback is not available. PDF conversion will still be attempted.")
                return True

            try:
                with tqdm.tqdm(total=len(failed), desc="Downloading images via browser", unit="image", disable=not show_progress) as pbar:
                    still_failed = 0

                    for xlink_href, image_url, target in failed:
                        data = self.browser_fetch_binary(driver, image_url)
                        if data:
                            os.makedirs(os.path.dirname(target), exist_ok=True)
                            with open(target, "wb") as img_file:
                                img_file.write(data)
                        else:
                            still_failed += 1

                        pbar.update(1)

                if still_failed:
                    print(f"Warning: {still_failed} images could not be downloaded through Chrome either.")
                else:
                    print("All missing images were downloaded through Chrome.")

            finally:
                try:
                    driver.quit()
                except Exception:
                    pass

        return True

    def modify_svg_text(self, svg_text: str, counter):
        pattern = r'<image\s.*?xlink:href="([^"]*)".*?>'
        matches = re.findall(pattern, svg_text)

        if matches:
            for xlink_href in matches:
                new_url = f"{counter}/{xlink_href}"
                svg_text = svg_text.replace(xlink_href, new_url, 1)

        return svg_text

    def get_total_pages(self, url):
        try:
            response = self.session.get(url.format(1, 1), timeout=10)
            if not self.is_svg_response(response):
                return 0
        except requests.RequestException:
            return 0

        low = 1
        high = 2

        while high <= 2048:
            try:
                response = self.session.get(url.format(high, high), timeout=10)
            except requests.RequestException:
                break

            if not self.is_svg_response(response):
                break

            low = high
            high *= 2

        left = low
        right = high - 1

        while left <= right:
            mid = (left + right) // 2

            try:
                response = self.session.get(url.format(mid, mid), timeout=10)
            except requests.RequestException:
                right = mid - 1
                continue

            if self.is_svg_response(response):
                left = mid + 1
            else:
                right = mid - 1

        return right

    def get_file_url(self, url):
        url = self.clean_base_url(url)

        try:
            response = self.session.get(f"{url}1.svg", timeout=10)
            if self.is_svg_response(response):
                return f"{url}{{}}.svg", False
        except requests.RequestException:
            pass

        try:
            response = self.session.get(f"{url}1/1.svg", timeout=10)
            if self.is_svg_response(response):
                return f"{url}{{}}/{{}}.svg", True
        except requests.RequestException:
            pass

        return None, False

    def is_svg_response(self, response):
        if response.status_code != 200:
            return False

        content_type = response.headers.get("content-type", "").lower()
        start = response.text.lstrip()[:800].lower()

        return "svg" in content_type or start.startswith("<svg") or "<svg" in start

    def is_binary_image_response(self, response):
        if response.status_code != 200:
            return False

        content_type = response.headers.get("content-type", "").lower()

        # If the server returns the Ionic HTML app, it often says text/html.
        if "html" in content_type:
            return False

        if content_type.startswith("image/"):
            return True

        # Accept common binary image headers when content-type is missing/wrong.
        data = response.content[:12]
        return (
            data.startswith(b"\xff\xd8\xff")      # jpg
            or data.startswith(b"\x89PNG\r\n\x1a\n")  # png
            or data.startswith(b"GIF87a")
            or data.startswith(b"GIF89a")
            or data.startswith(b"RIFF")           # webp container
        )

    def clean_base_url(self, url):
        url = str(url).strip()
        url = url.split("#", 1)[0].split("?", 1)[0]
        url = re.sub(r"/index\.html$", "/", url)

        if not url.endswith("/"):
            url += "/"

        return url

    def join_url(self, base_url, path):
        return base_url.rstrip("/") + "/" + str(path).lstrip("/")

    # ------------------------------------------------------------------
    # Sichtbarer Chrome-Fallback
    # ------------------------------------------------------------------

    def download_svgs_with_browser(self, down_dir, url, show_progress=False):
        base_url = self.clean_base_url(url)
        driver = self.make_logged_in_driver(base_url)

        if driver is None:
            return False

        downloaded = 0

        try:
            with tqdm.tqdm(desc="Downloading svgs via browser", unit="svg", disable=not show_progress) as pbar:
                counter = 1

                while counter <= 1500:
                    svg_url = f"{base_url}{counter}.svg"
                    svg_text = self.browser_fetch_text(driver, svg_url)

                    if not self.text_is_svg(svg_text):
                        if counter == 1:
                            return self.download_special_svgs_with_browser(driver, down_dir, base_url, show_progress)
                        break

                    with open(f"{down_dir}/{counter}.svg", "w+", encoding="utf8") as svg_file:
                        svg_file.write(svg_text)

                    counter += 1
                    downloaded += 1
                    pbar.update(1)

            print(f"{downloaded} SVG pages downloaded through Chrome.")
            return downloaded > 0

        finally:
            try:
                driver.quit()
            except Exception:
                pass

    def download_special_svgs_with_browser(self, driver, down_dir, base_url, show_progress=False):
        downloaded = 0

        with tqdm.tqdm(desc="Downloading special svgs via browser", unit="svg", disable=not show_progress) as pbar:
            counter = 1

            while counter <= 1500:
                svg_url = f"{base_url}{counter}/{counter}.svg"
                svg_text = self.browser_fetch_text(driver, svg_url)

                if not self.text_is_svg(svg_text):
                    if counter == 1:
                        print("Chrome fallback could not read any SVG files.")
                        return False
                    break

                svg_text = self.modify_svg_text(svg_text, counter)

                with open(f"{down_dir}/{counter}.svg", "w+", encoding="utf8") as svg_file:
                    svg_file.write(svg_text)

                counter += 1
                downloaded += 1
                pbar.update(1)

        print(f"{downloaded} SVG pages downloaded through Chrome.")
        return downloaded > 0

    def download_pages_with_browser(self, down_dir, url, start_page, end_page, first_non_titlepage, show_progress=False):
        base_url = self.clean_base_url(url)
        driver = self.make_logged_in_driver(base_url)

        if driver is None:
            return False

        end_page = end_page if end_page else start_page
        counter = start_page + first_non_titlepage - 1
        last_counter = end_page + first_non_titlepage - 1
        downloaded = 0

        try:
            with tqdm.tqdm(total=(last_counter - counter + 1), desc="Downloading svgs via browser", unit="svg", disable=not show_progress) as pbar:
                while counter <= last_counter:
                    svg_url = f"{base_url}{counter}.svg"
                    svg_text = self.browser_fetch_text(driver, svg_url)

                    if not self.text_is_svg(svg_text):
                        print(f"Seite {counter} could not be read.")
                        return downloaded > 0

                    with open(f"{down_dir}/{counter}.svg", "w+", encoding="utf8") as svg_file:
                        svg_file.write(svg_text)

                    counter += 1
                    downloaded += 1
                    pbar.update(1)

            return downloaded > 0

        finally:
            try:
                driver.quit()
            except Exception:
                pass

    def make_logged_in_driver(self, base_url):
        try:
            from selenium import webdriver
            from selenium.webdriver.chrome.options import Options
        except Exception as exc:
            print(f"Selenium is not available: {exc}")
            return None

        options = Options()
        options.add_argument("--start-maximized")
        options.add_argument("--log-level=3")

        driver = webdriver.Chrome(options=options)

        try:
            driver.get("https://digi4school.at/")
            time.sleep(1)

            for cookie in self.session.cookies:
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

            driver.get(base_url + "?page=1")
            time.sleep(3)

            test_svg_url = base_url + "1.svg"

            for _ in range(5):
                svg_text = self.browser_fetch_text(driver, test_svg_url)
                if self.text_is_svg(svg_text):
                    print("Chrome fallback is logged in and can read files.")
                    return driver
                time.sleep(1)

            print("")
            print("=" * 72)
            print("Chrome has been opened, but the files are not available yet.")
            print("Please log in or open the book in the opened Chrome window.")
            print("When the book page is visible, return to PowerShell and press ENTER.")
            print("=" * 72)
            input("Continue with ENTER once the book is open in the Chrome window... ")

            driver.get(base_url + "?page=1")
            time.sleep(2)

            for _ in range(10):
                svg_text = self.browser_fetch_text(driver, test_svg_url)
                if self.text_is_svg(svg_text):
                    print("Chrome fallback is now logged in and can read files.")
                    return driver
                time.sleep(1)

            print("Chrome still could not read the files after manual login.")
            driver.quit()
            return None

        except Exception as exc:
            print(f"Chrome fallback could not be started: {exc}")

            try:
                driver.quit()
            except Exception:
                pass

            return None

    def browser_fetch_text(self, driver, url):
        script = """
            const url = arguments[0];
            const callback = arguments[1];

            fetch(url, { credentials: 'include', cache: 'no-store' })
                .then(async response => {
                    const text = await response.text();
                    callback({ ok: response.ok, status: response.status, text });
                })
                .catch(error => callback({ ok: false, status: 0, text: String(error) }));
        """

        try:
            result = driver.execute_async_script(script, url)
        except Exception:
            return ""

        if not result or not result.get("ok"):
            return ""

        return result.get("text", "")

    def browser_fetch_binary(self, driver, url):
        script = """
            const url = arguments[0];
            const callback = arguments[1];

            fetch(url, { credentials: 'include', cache: 'no-store' })
                .then(async response => {
                    if (!response.ok) {
                        callback({ ok: false, status: response.status, data: "" });
                        return;
                    }

                    const buffer = await response.arrayBuffer();
                    const bytes = new Uint8Array(buffer);
                    let binary = "";
                    const chunkSize = 0x8000;

                    for (let i = 0; i < bytes.length; i += chunkSize) {
                        const chunk = bytes.subarray(i, i + chunkSize);
                        binary += String.fromCharCode.apply(null, chunk);
                    }

                    callback({ ok: true, status: response.status, data: btoa(binary) });
                })
                .catch(error => callback({ ok: false, status: 0, data: "" }));
        """

        try:
            result = driver.execute_async_script(script, url)
        except Exception:
            return b""

        if not result or not result.get("ok") or not result.get("data"):
            return b""

        try:
            return base64.b64decode(result["data"])
        except Exception:
            return b""

    def text_is_svg(self, text):
        if not text:
            return False

        start = text.lstrip()[:800].lower()
        return start.startswith("<svg") or "<svg" in start
