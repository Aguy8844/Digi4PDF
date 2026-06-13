import getpass
import os
import textwrap
import webbrowser

import requests

from .authentication import AuthAndTokenHandler
from .book_fetcher import BookDataRetriever
from .config_handler import ConfigHandler


class CommandHandler:
    def __init__(self) -> None:
        self.config_handler = ConfigHandler()
        self.session = self.create_session()
        self.auth = AuthAndTokenHandler()
        self.digi4school = BookDataRetriever()

        self.commands = {
            "list-books": self.list_books,
            "refresh-books": self.refresh_books,
            "force-rescan": self.force_rescan_books,
            "rename-book": self.rename_book_command,
            "add-url": self.add_url_command,
            "remove-book": self.remove_book_command,
            "download": self.download,
            "accounts": self.accounts_menu,
            "switch-account": self.switch_account_command,
            "add-account": self.add_account_command,
            "menu": self.menu,
            "help": self.help,
            "exit": self.exit_program,
            "quit": self.exit_program,
        }

    def create_session(self):
        session = requests.Session()
        session.headers.update({
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/149.0.0.0 Safari/537.36"
            )
        })
        return session

    def main(self):
        if not self.config_handler.check_config():
            print("Keine gültigen Zugangsdaten gefunden.")
            self.add_account_interactive(set_active=True)

        if self.login_current_account():
            self.menu()
        else:
            print("Login fehlgeschlagen. Bitte Accountdaten prüfen.")
            self.accounts_menu()

    def login_current_account(self):
        active = self.config_handler.get_active_account_name()
        print(f"Einloggen mit Account: {active}")

        self.session = self.create_session()
        self.auth = AuthAndTokenHandler()
        self.digi4school = BookDataRetriever()

        login_success = self.auth.login_user(self.session)

        if login_success:
            print("Login erfolgreich.\n")
            return True

        print("Login fehlgeschlagen.\n")
        return False

    # ------------------------------------------------------------------
    # Main menu
    # ------------------------------------------------------------------

    def menu(self, *args):
        print("Welcome to digi4school-2-pdf!!!")

        while True:
            active = self.config_handler.get_active_account_name()
            print("")
            print("=" * 72)
            print(f"Aktiver Account: {active}")
            print("=" * 72)
            print("1  - Bücher anzeigen")
            print("2  - Buch auswählen und herunterladen")
            print("3  - Alle Bücher herunterladen")
            print("4  - Einzelne Seite / Seitenbereich herunterladen")
            print("5  - E-Book-Link hinzufügen")
            print("6  - Gespeicherten manuellen Link entfernen")
            print("7  - Bücherliste neu aus Digi4School scannen")
            print("8  - Buchtitel bearbeiten")
            print("9  - PDF-Ordner öffnen")
            print("10 - Account wechseln")
            print("11 - Account hinzufügen / aktualisieren")
            print("12 - Accounts anzeigen / verwalten")
            print("13 - Hilfe")
            print("0  - Beenden")
            print("-" * 72)

            choice = input("Auswahl oder Befehl > ").strip()

            try:
                if choice == "1":
                    self.list_books_interactive()
                elif choice == "2":
                    self.download_interactive()
                elif choice == "3":
                    self.download_all_books()
                elif choice == "4":
                    self.download_page_interactive()
                elif choice == "5":
                    self.add_url_interactive()
                elif choice == "6":
                    self.remove_book_interactive()
                elif choice == "7":
                    self.force_rescan_books()
                elif choice == "8":
                    self.rename_book_interactive()
                elif choice == "9":
                    self.open_output_folder()
                elif choice == "10":
                    self.switch_account_interactive()
                elif choice == "11":
                    self.add_account_interactive(set_active=True)
                    self.login_current_account()
                elif choice == "12":
                    self.accounts_menu()
                elif choice == "13":
                    self.help()
                elif choice == "0":
                    self.exit_program()
                elif choice:
                    # Keep old command mode alive.
                    self.execute_command(choice)
            except SystemExit:
                raise
            except Exception as e:
                print(f"Fehler: {e}")

    def execute_command(self, command):
        if not command.strip():
            return

        command_name, *args = command.split()

        if command_name in self.commands:
            try:
                self.commands[command_name](*args)
            except SystemExit:
                raise
            except Exception as e:
                print(f"Fehler: {e}\n")
        else:
            print("Unbekannter Befehl. Tippe 'help'.\n")

    def help(self, *args):
        print("")
        print("Zahlenmenü:")
        print("1 Bücher anzeigen, 2 Buch herunterladen, 7 neu scannen, 8 Buchtitel bearbeiten, 10 Account wechseln, 11 Account hinzufügen.")
        print("")
        print("Buchauswahl:")
        print("- Nummer eingeben, z.B. 4")
        print("- ID eingeben, z.B. 6410")
        print("- Suchtext eingeben, z.B. mathe")
        print("- / zeigt wieder alle Bücher")
        print("- q bricht ab")
        print("")
        print("Alte Befehle funktionieren weiterhin:")
        print("- list-books")
        print("- download book <index_or_id>")
        print("- download all")
        print("- download book <index_or_id> page <start_page> [<end_page>] [--disable-check]")
        print("- add-url")
        print("- remove-book <index_or_id>")
        print("- refresh-books")
        print("- force-rescan")
        print("- rename-book <index_or_id> <new title>")
        print("- accounts")
        print("- switch-account <name>")
        print("- add-account")
        print("- exit\n")

    # ------------------------------------------------------------------
    # Book listing and interactive selection
    # ------------------------------------------------------------------

    def list_books(self, *args):
        data = self.digi4school.get_book_list(self.session)
        self.print_books(data)

    def list_books_interactive(self):
        books = self.digi4school.get_book_list(self.session)

        while True:
            print("")
            print("Bücher anzeigen")
            print("1 - Alle Bücher")
            print("2 - Nur Unknown-title-Einträge")
            print("3 - Suche/Filter")
            print("0 - Zurück")
            choice = input("> ").strip()

            if choice == "1":
                self.print_books(books)
            elif choice == "2":
                unknown = [b for b in books if "unknown" in str(b[2]).lower()]
                self.print_books(unknown)
            elif choice == "3":
                query = input("Suchtext: ").strip()
                self.print_books(self.filter_books(books, query))
            elif choice == "0":
                return
            else:
                print("Bitte 0 bis 3 eingeben.")

    def print_books(self, data):
        if len(data) > 0:
            print("")
            print("Index   ID          Book Name")
            print("-" * 100)

            for counter, book in enumerate(data, start=1):
                title = str(book[2]).strip()
                if len(title) > 78:
                    title = title[:75] + "..."
                print(f"{counter:>5}   {str(book[0]):<10}  {title}")

            print("-" * 100)
            print("")
        else:
            print("No data found!!\n")

    def choose_book(self, headline="Buch auswählen"):
        all_books = self.digi4school.get_book_list(self.session)
        filtered = all_books[:]
        query = ""

        while True:
            print("")
            print("=" * 72)
            print(headline)
            if query:
                print(f"Filter: {query}")
            print("=" * 72)
            self.print_books(filtered[:40])

            if len(filtered) > 40:
                print(f"... {len(filtered) - 40} weitere Treffer. Suchtext eingeben, um einzugrenzen.\n")

            print("Nummer/ID wählen | Suchtext eingeben | / = alle | q = zurück")
            choice = input("> ").strip()

            if choice.lower() in ("q", "quit", "zurück", "back"):
                return None

            if choice == "/":
                query = ""
                filtered = all_books[:]
                continue

            # Exact ID match in full list.
            for book in all_books:
                if str(book[0]) == choice or str(book[1]) == choice:
                    return book

            # Current filtered list number.
            if choice.isdigit():
                index = int(choice)
                if 1 <= index <= len(filtered):
                    return filtered[index - 1]

            # Otherwise treat input as search query.
            query = choice
            filtered = self.filter_books(all_books, query)

            if not filtered:
                print("Keine Treffer. '/' eingeben, um wieder alle Bücher zu sehen.")
                filtered = []

    def filter_books(self, books, query):
        query = str(query or "").strip().lower()
        if not query:
            return books[:]

        result = []
        for book in books:
            searchable = " ".join(str(part) for part in book).lower()
            if query in searchable:
                result.append(book)

        return result

    def refresh_books(self, *args):
        self.digi4school.clear_cache()
        print("Book cache cleared.\n")
        self.list_books()

    def force_rescan_books(self, *args):
        print("")
        print("Ich scanne die Bücherliste für diesen Account neu.")
        print("Das kann kurz ein Chrome-Fenster öffnen.")
        confirm = input("Wirklich neu scannen? [j/N] ").strip().lower()

        if confirm not in ("j", "ja", "y", "yes"):
            print("Abgebrochen.\n")
            return

        books = self.digi4school.force_rescan_current_account(self.session)

        if books:
            print("")
            print("Neue Bücherliste:")
            self.print_books(books)
        else:
            print("Beim Scan wurden keine Bücher gefunden.\n")

    # ------------------------------------------------------------------
    # Downloads
    # ------------------------------------------------------------------

    def download_interactive(self):
        data = self.choose_book("Buch herunterladen")
        if data is None:
            return

        self.digi4school.download_single_book(data, self.session)

    def download_page_interactive(self):
        data = self.choose_book("Einzelne Seite / Seitenbereich herunterladen")
        if data is None:
            return

        start_page = input("Startseite? ").strip()
        end_page = input("Endseite leer lassen für nur eine Seite: ").strip() or None
        disable = input("Titelblatt-Check deaktivieren? [j/N] ").strip().lower() in ("j", "ja", "y", "yes")

        self.download_page_by_data(data, start_page, end_page, disable)

    def download(self, *args):
        if not args:
            print("Invalid arguments. Type 'help'.\n")
            return

        if args[0] == "all":
            self.download_all_books()
            return

        if args[0] == "book" and len(args) == 2:
            self.download_book(args[1])
            return

        if args[0] == "book" and len(args) >= 4 and args[2] == "page":
            book_selector = args[1]
            start_page = args[3]
            end_page = None
            disable_titlepage_check = False

            if len(args) > 4:
                if args[4].isdigit():
                    end_page = args[4]
                elif args[4] == "--disable-check":
                    disable_titlepage_check = True

            if len(args) > 5 and args[5] == "--disable-check":
                disable_titlepage_check = True

            self.download_page(book_selector, start_page, end_page, disable_titlepage_check)
            return

        print("Invalid arguments. Type 'help'.\n")

    def download_book(self, selector):
        data = self.resolve_book(selector)
        if data is None:
            return

        self.digi4school.download_single_book(data, self.session)

    def download_all_books(self):
        confirm = input("Wirklich alle Bücher dieses Accounts herunterladen? [j/N] ").strip().lower()
        if confirm not in ("j", "ja", "y", "yes"):
            print("Abgebrochen.\n")
            return

        data = self.digi4school.get_book_list(self.session)
        self.digi4school.download_all_books(data, self.session)

    def download_page(self, selector, start_page, end_page=None, disable_titlepage_check=False):
        data = self.resolve_book(selector)
        if data is None:
            return

        self.download_page_by_data(data, start_page, end_page, disable_titlepage_check)

    def download_page_by_data(self, data, start_page, end_page=None, disable_titlepage_check=False):
        if not str(start_page).isdigit():
            print("Invalid start page.\n")
            return

        if end_page is not None and not str(end_page).isdigit():
            print("Invalid end page.\n")
            return

        self.digi4school.download_page(
            data,
            self.session,
            int(start_page),
            int(end_page) if end_page else None,
            disable_titlepage_check,
        )

    def resolve_book(self, selector):
        selector = str(selector).strip()
        data = self.digi4school.get_book_list(self.session)

        # Exact ID match, e.g. 6410 or 6525-1002.
        for book in data:
            if str(book[0]) == selector:
                return book

        # Code match, if unique.
        matches = [book for book in data if str(book[1]) == selector]
        if len(matches) == 1:
            return matches[0]

        if len(matches) > 1:
            print("This ID has multiple variants. Use the exact ID:")
            for book in matches:
                print(f"- {book[0]}: {book[2]}")
            return None

        # List index.
        if selector.isdigit():
            index = int(selector)
            if 1 <= index <= len(data):
                return data[index - 1]

        # Direct fallback if user knows a book ID.
        if "-" in selector:
            code, sub_id = selector.split("-", 1)
            return (selector, code, f"ebook-{selector}", f"https://a.digi4school.at/ebook/{code}/{sub_id}/", sub_id)

        if selector.isdigit():
            return (selector, selector, f"ebook-{selector}", f"https://a.digi4school.at/ebook/{selector}/", "")

        print("Book not found.\n")
        return None

    # ------------------------------------------------------------------
    # Manual URLs and title edits
    # ------------------------------------------------------------------

    def add_url_command(self, *args):
        self.add_url_interactive()

    def add_url_interactive(self):
        print("")
        title = input("Titel/Name für das Buch: ").strip()
        href = input("E-Book-Link: ").strip()

        if not href:
            print("Kein Link angegeben.\n")
            return

        book = self.digi4school.add_manual_book(title, href)
        print(f"Gespeichert für Account '{self.config_handler.get_active_account_name()}': {book[0]} - {book[2]}\n")

    def remove_book_command(self, *args):
        if not args:
            self.remove_book_interactive()
            return

        selector = args[0]
        if self.digi4school.remove_manual_book(selector):
            print("Manueller Link entfernt.\n")
        else:
            print("Manueller Link nicht gefunden.\n")

    def remove_book_interactive(self):
        selector = input("Welche manuelle Nummer oder ID entfernen? ").strip()
        if not selector:
            return

        if self.digi4school.remove_manual_book(selector):
            print("Manueller Link entfernt.\n")
        else:
            print("Manueller Link nicht gefunden.\n")

    def rename_book_command(self, *args):
        if len(args) >= 2:
            selector = args[0]
            new_title = " ".join(args[1:])
            if self.digi4school.update_book_title(selector, new_title):
                print("Titel geändert.\n")
            else:
                print("Buch nicht gefunden oder Titel leer.\n")
            return

        self.rename_book_interactive()

    def rename_book_interactive(self):
        data = self.choose_book("Buchtitel bearbeiten")
        if data is None:
            return

        print(f"Aktueller Titel: {data[2]}")
        new_title = input("Neuer Titel: ").strip()
        if not new_title:
            print("Kein Titel eingegeben.\n")
            return

        if self.digi4school.update_book_title(str(data[0]), new_title):
            print("Titel geändert.\n")
            self.list_books()
        else:
            print("Buch nicht gefunden.\n")

    def open_output_folder(self):
        output_dir = os.path.abspath("output")
        os.makedirs(output_dir, exist_ok=True)
        try:
            os.startfile(output_dir)
        except AttributeError:
            webbrowser.open(output_dir)

    # ------------------------------------------------------------------
    # Accounts
    # ------------------------------------------------------------------

    def accounts_menu(self, *args):
        while True:
            active = self.config_handler.get_active_account_name()
            accounts = self.config_handler.list_accounts()

            print("")
            print("Accounts:")
            print("-" * 64)
            for i, name in enumerate(accounts, start=1):
                marker = "*" if name == active else " "
                print(f"{i:>2}. {marker} {name}")
            print("-" * 64)
            print("1 - Account wechseln")
            print("2 - Account hinzufügen / aktualisieren")
            print("3 - Account löschen")
            print("0 - Zurück")
            choice = input("> ").strip()

            if choice == "1":
                self.switch_account_interactive()
            elif choice == "2":
                self.add_account_interactive(set_active=True)
                self.login_current_account()
            elif choice == "3":
                self.delete_account_interactive()
            elif choice == "0":
                return
            else:
                print("Bitte 0 bis 3 eingeben.")

    def add_account_command(self, *args):
        self.add_account_interactive(set_active=True)
        self.login_current_account()

    def add_account_interactive(self, set_active=True):
        print("")
        print("Neuen Account hinzufügen oder bestehenden aktualisieren.")
        account_name = input("Account-Name, z.B. schule, privat, freundin: ").strip()
        email = input("Digi4School E-Mail: ").strip()
        password = getpass.getpass("Digi4School Passwort: ")

        if not account_name:
            account_name = email.split("@", 1)[0] if "@" in email else "default"

        self.config_handler.write_config(email, password, account_name=account_name)

        if set_active:
            self.config_handler.set_active_account(account_name)

        print(f"Account gespeichert: {account_name}")
        print("Hinweis: Passwort liegt lokal in config.ini. Diese Datei nicht hochladen/teilen.\n")

    def switch_account_command(self, *args):
        if args:
            self.switch_to_account(args[0])
        else:
            self.switch_account_interactive()

    def switch_account_interactive(self):
        accounts = self.config_handler.list_accounts()
        active = self.config_handler.get_active_account_name()

        print("")
        print("Verfügbare Accounts:")
        for i, name in enumerate(accounts, start=1):
            marker = "*" if name == active else " "
            print(f"{i:>2}. {marker} {name}")

        selector = input("Welche Nummer oder welcher Name? ").strip()
        if not selector:
            return

        if selector.isdigit():
            index = int(selector)
            if 1 <= index <= len(accounts):
                account_name = accounts[index - 1]
            else:
                print("Ungültige Nummer.")
                return
        else:
            account_name = selector

        self.switch_to_account(account_name)

    def switch_to_account(self, account_name):
        try:
            self.config_handler.set_active_account(account_name)
        except Exception as exc:
            print(f"Account konnte nicht gewechselt werden: {exc}")
            return

        self.digi4school.clear_cache()

        if self.login_current_account():
            print(f"Aktiver Account: {account_name}\n")
        else:
            print("Wechsel gespeichert, aber Login ist fehlgeschlagen.\n")

    def delete_account_interactive(self):
        accounts = self.config_handler.list_accounts()
        active = self.config_handler.get_active_account_name()

        print("")
        print("Account löschen:")
        for i, name in enumerate(accounts, start=1):
            marker = "*" if name == active else " "
            print(f"{i:>2}. {marker} {name}")

        selector = input("Welche Nummer oder welcher Name soll gelöscht werden? ").strip()
        if not selector:
            return

        if selector.isdigit():
            index = int(selector)
            if 1 <= index <= len(accounts):
                account_name = accounts[index - 1]
            else:
                print("Ungültige Nummer.")
                return
        else:
            account_name = selector

        confirm = input(f"'{account_name}' wirklich löschen? [j/N] ").strip().lower()
        if confirm not in ("j", "ja", "y", "yes"):
            print("Abgebrochen.")
            return

        try:
            self.config_handler.delete_account(account_name)
            print("Account gelöscht.")
            self.login_current_account()
        except Exception as exc:
            print(f"Konnte Account nicht löschen: {exc}")

    def exit_program(self, *args):
        print("Bye!")
        raise SystemExit
