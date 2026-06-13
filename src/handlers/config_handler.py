import os
from configparser import RawConfigParser


class ConfigHandler:
    """
    Multi-account config handler.

    Backwards compatible:
    - Old config.ini with DEFAULT email/password is migrated to [account:default].
    - AuthAndTokenHandler().get_data() can still call get_config()["email"] / ["password"].

    Note:
    - Passwords are stored locally in config.ini, like the original project did.
    - Do not upload or share config.ini.
    """

    def __init__(self, config_file="config.ini"):
        self.config_file = config_file

    # ------------------------------------------------------------------
    # Basic file handling
    # ------------------------------------------------------------------

    def _load(self):
        config = RawConfigParser()
        config.read(self.config_file, encoding="utf-8")
        return config

    def _save(self, config):
        with open(self.config_file, "w+", encoding="utf-8") as configfile:
            config.write(configfile)

    def _write_default(self):
        config = RawConfigParser()
        config["DEFAULT"] = {
            "active_account": "default",
        }
        config["account:default"] = {
            "email": "email",
            "password": "password",
        }
        self._save(config)

    def _account_section(self, account_name):
        account_name = str(account_name or "default").strip() or "default"
        return f"account:{account_name}"

    def _ensure_migrated(self, config):
        """
        Migrate old config.ini:
        [DEFAULT]
        email = ...
        password = ...

        to:
        [DEFAULT]
        active_account = default

        [account:default]
        email = ...
        password = ...
        """
        default_email = config["DEFAULT"].get("email", "").strip() if "DEFAULT" in config else ""
        default_password = config["DEFAULT"].get("password", "").strip() if "DEFAULT" in config else ""

        has_account_sections = any(section.startswith("account:") for section in config.sections())

        if not has_account_sections and default_email and default_email != "email":
            config["account:default"] = {
                "email": default_email,
                "password": default_password,
            }

        if "active_account" not in config["DEFAULT"]:
            config["DEFAULT"]["active_account"] = "default"

        return config

    # ------------------------------------------------------------------
    # Original compatible API
    # ------------------------------------------------------------------

    def check_config(self) -> bool:
        if not os.path.isfile(self.config_file):
            self._write_default()
            return False

        config = self._load()
        config = self._ensure_migrated(config)
        self._save(config)

        try:
            data = self.get_config()
            email = data.get("email", "").strip()
            password = data.get("password", "").strip()
        except Exception:
            return False

        return not (email == "email" or password == "password" or not email or not password)

    def get_config(self):
        config = self._load()
        config = self._ensure_migrated(config)
        self._save(config)

        active = self.get_active_account_name(config)
        section = self._account_section(active)

        if section not in config:
            raise KeyError(f"Account '{active}' does not exist.")

        return config[section]

    def write_config(self, email, password, account_name=None):
        config = self._load() if os.path.isfile(self.config_file) else RawConfigParser()
        config = self._ensure_migrated(config)

        if "DEFAULT" not in config:
            config["DEFAULT"] = {}

        account_name = str(account_name or self.get_active_account_name(config) or "default").strip() or "default"
        section = self._account_section(account_name)

        if section not in config:
            config.add_section(section)

        config[section]["email"] = str(email).strip()
        config[section]["password"] = str(password)

        config["DEFAULT"]["active_account"] = account_name
        self._save(config)

    # ------------------------------------------------------------------
    # Multi-account API
    # ------------------------------------------------------------------

    def list_accounts(self):
        config = self._load()
        config = self._ensure_migrated(config)
        self._save(config)

        names = []
        for section in config.sections():
            if section.startswith("account:"):
                names.append(section.split("account:", 1)[1])

        return names

    def get_active_account_name(self, config=None):
        if config is None:
            config = self._load()
            config = self._ensure_migrated(config)
            self._save(config)

        return config["DEFAULT"].get("active_account", "default").strip() or "default"

    def set_active_account(self, account_name):
        config = self._load()
        config = self._ensure_migrated(config)

        account_name = str(account_name).strip()
        section = self._account_section(account_name)

        if section not in config:
            raise KeyError(f"Account '{account_name}' does not exist.")

        config["DEFAULT"]["active_account"] = account_name
        self._save(config)

    def delete_account(self, account_name):
        config = self._load()
        config = self._ensure_migrated(config)

        account_name = str(account_name).strip()
        section = self._account_section(account_name)

        accounts = self.list_accounts()
        if len(accounts) <= 1:
            raise RuntimeError("Cannot delete the last account.")

        if section not in config:
            raise KeyError(f"Account '{account_name}' does not exist.")

        config.remove_section(section)

        if config["DEFAULT"].get("active_account") == account_name:
            remaining = [s.split("account:", 1)[1] for s in config.sections() if s.startswith("account:")]
            config["DEFAULT"]["active_account"] = remaining[0] if remaining else "default"

        self._save(config)

    def account_exists(self, account_name):
        config = self._load()
        config = self._ensure_migrated(config)
        return self._account_section(account_name) in config
