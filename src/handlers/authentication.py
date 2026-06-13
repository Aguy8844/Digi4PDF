"""
Authentication and token handling for digi4school-2-pdf.

Restored toward the original project behavior:
- Use the original Digi4School LTI flow first.
- If Digi4School no longer returns an LTI form, fall back to the visible reader URL.
- Clean URLs such as ?page=59 so the downloader never builds broken URLs.
"""

import html
import os
import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from .config_handler import ConfigHandler


class AuthAndTokenHandler:
    LOGIN_URL = "https://digi4school.at/br/xhr/login"

    def get_data(self):
        if os.getenv("EMAIL"):
            return {
                "email": os.getenv("EMAIL"),
                "password": os.getenv("PASSWORD"),
            }

        config_data = ConfigHandler().get_config()
        return {
            "email": config_data["email"],
            "password": config_data["password"],
        }

    def login_user(self, session):
        login_payload = self.get_data()
        response = session.post(self.LOGIN_URL, data=login_payload, timeout=15)
        text = response.text.strip()

        if text == "OK":
            return True

        if text == "KO":
            return False

        print("Unexpected login response:")
        print(text[:500])
        return False

    def token_processing(self, data, session):
        """
        Original data format:
            (book_id, book_code, title, href)

        Some repaired lists may pass:
            (book_id, code, title, href, sub_id)
        """
        if not data or len(data) < 2:
            raise RuntimeError(f"Invalid book data: {data!r}")

        book_id = str(data[0]).strip()
        book_code = str(data[1]).strip()
        href = str(data[3]).strip() if len(data) > 3 and data[3] else ""
        sub_id = str(data[4]).strip() if len(data) > 4 and data[4] else ""

        if not sub_id and "-" in book_id:
            parts = book_id.split("-", 1)
            if parts[0].isdigit() and parts[1].isdigit():
                book_code = parts[0]
                sub_id = parts[1]

        # Original LTI flow first.
        book_code_url = "https://digi4school.at/ebook/" + book_code

        try:
            book_code_req = session.get(book_code_url, timeout=20)
            action_lti, data_payload = self.process_lti_response(book_code_req.text, base_url=book_code_req.url)

            first_lti_req = session.post(action_lti, data=data_payload, timeout=20)
            action_lti, data_payload = self.process_lti_response(first_lti_req.text, base_url=first_lti_req.url)

            second_lti_req = session.post(action_lti, data=data_payload, allow_redirects=False, timeout=20)
            redirect_url = second_lti_req.headers["Location"]
            redirect_url = urljoin(action_lti, redirect_url)

            # Load final HTML too because nested books can need an extra ID path.
            second_lti_req = session.post(action_lti, data=data_payload, allow_redirects=True, timeout=20)
            soup = BeautifulSoup(second_lti_req.text, "html.parser")

            if soup.select_one("#content"):
                id_element = soup.select_one('a[href*="index.html"]')
                if id_element:
                    id_value = id_element["href"].split("/")[-2]
                    url = redirect_url + id_value
                    return self.clean_reader_base(url)

            return self.clean_reader_base(redirect_url)

        except Exception as exc:
            fallback = self.make_reader_fallback(book_code, href, sub_id)
            print("LTI flow did not return an old-style URL.")
            print(f"Using reader URL fallback: {fallback}")
            return fallback

    def process_lti_response(self, response, base_url="https://digi4school.at/"):
        soup = BeautifulSoup(response, "html.parser")
        form = soup.find("form")

        if not form:
            text = soup.get_text(" ", strip=True)[:300]
            raise RuntimeError(f"No LTI form found. Page starts with: {text!r}")

        action = form.get("action")
        if not action:
            raise RuntimeError("LTI form has no action.")

        data_payload = {}
        for input_tag in form.find_all("input"):
            name = input_tag.get("name")
            if name:
                data_payload[name] = input_tag.get("value", "")

        if not data_payload:
            raise RuntimeError("LTI form has no payload.")

        return urljoin(base_url, html.unescape(action)), data_payload

    def make_reader_fallback(self, book_code, href="", sub_id=""):
        if href:
            return self.clean_reader_base(href)

        if sub_id:
            return f"https://a.digi4school.at/ebook/{book_code}/{sub_id}/"

        return f"https://a.digi4school.at/ebook/{book_code}/"

    def clean_reader_base(self, url):
        url = str(url).strip()
        url = url.split("#", 1)[0].split("?", 1)[0]
        url = re.sub(r"/index\.html$", "/", url)
        if not url.endswith("/"):
            url += "/"
        return url
