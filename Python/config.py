"""
config.py
=========
Loads and saves the application's configuration as a small JSON file.

The config file ALWAYS lives in a stable per-user folder so the app can find it
on every launch:

    Windows:  %APPDATA%\\DioceseCertManager\\config.json
    Other:    ~/.diocese_cert_manager/config.json   (dev / Linux / macOS)

The *database* on the other hand lives wherever the user wants it (USB stick,
shared network folder, ...). That location is stored inside the config as
``data_path`` and can be changed at runtime from the Settings screen.

Everything in here is plain stdlib so it works on a clean Python 3.8 install.
"""

import json
import os


# --------------------------------------------------------------------------- #
# Where the config file itself lives (NOT the database)
# --------------------------------------------------------------------------- #
def _app_config_dir():
    """Return a stable per-user directory for the config file, creating it."""
    if os.name == "nt":
        base = os.environ.get("APPDATA") or os.path.expanduser("~")
        folder = os.path.join(base, "DioceseCertManager")
    else:
        folder = os.path.join(os.path.expanduser("~"), ".diocese_cert_manager")
    os.makedirs(folder, exist_ok=True)
    return folder


CONFIG_DIR = _app_config_dir()
CONFIG_PATH = os.path.join(CONFIG_DIR, "config.json")


# Default database folder = same per-user folder. The user can move it later.
DEFAULT_DATA_PATH = CONFIG_DIR


# --------------------------------------------------------------------------- #
# Default configuration. Calibration offsets are PER FORM, in millimetres.
# These offsets are added to every coordinate when printing, so staff can
# nudge the whole printout to line up with the pre-printed sheet.
# --------------------------------------------------------------------------- #
DEFAULTS = {
    "schema_version": 1,
    "data_path": DEFAULT_DATA_PATH,
    # Per-form paper size (key from layouts.PAGE_SIZES_MM). The pre-printed
    # sheets are different sizes, so each form carries its own.
    "paper_size": {
        "death":    "Death sheet",
        "marriage": "Marriage sheet",
        "baptism":  "Baptism sheet",
    },
    "theme": "light",             # "light" or "dark"
    "accent_color": "blue",       # CustomTkinter built-in theme name
    "printer_name": "",           # empty => use the system default printer
    "font_name": "Arial",
    "font_size_pt": 11,
    # Per-form global calibration offsets (millimetres).
    "calibration": {
        "death":    {"x_mm": 0.0, "y_mm": 0.0},
        "marriage": {"x_mm": 0.0, "y_mm": 0.0},
        "baptism":  {"x_mm": 0.0, "y_mm": 0.0},
    },
}


class Config:
    """Thin wrapper around the config dict with load/save helpers."""

    def __init__(self):
        self._data = json.loads(json.dumps(DEFAULTS))  # deep copy of defaults
        self.load()

    # -- persistence ------------------------------------------------------- #
    def load(self):
        """Load config.json, merging onto defaults so new keys are filled in."""
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as fh:
                stored = json.load(fh)
            self._deep_merge(self._data, stored)
        except (FileNotFoundError, ValueError):
            # Missing or corrupt -> keep defaults and write a fresh file.
            self.save()
        self._migrate_paper_size()
        return self

    def _migrate_paper_size(self):
        """Old configs stored one global paper_size string; spread it per-form."""
        ps = self._data.get("paper_size")
        if isinstance(ps, str):
            self._data["paper_size"] = {
                "death": ps, "marriage": ps, "baptism": ps,
            }

    def save(self):
        """Write the current config back to disk (atomic-ish)."""
        tmp = CONFIG_PATH + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(self._data, fh, indent=2)
        os.replace(tmp, CONFIG_PATH)

    @staticmethod
    def _deep_merge(base, override):
        """Recursively copy override values onto base, in place."""
        for key, value in override.items():
            if (
                key in base
                and isinstance(base[key], dict)
                and isinstance(value, dict)
            ):
                Config._deep_merge(base[key], value)
            else:
                base[key] = value

    # -- generic access ---------------------------------------------------- #
    def get(self, key, default=None):
        return self._data.get(key, default)

    def set(self, key, value):
        self._data[key] = value
        self.save()

    # -- convenience accessors -------------------------------------------- #
    @property
    def data_path(self):
        path = self._data.get("data_path") or DEFAULT_DATA_PATH
        os.makedirs(path, exist_ok=True)
        return path

    @data_path.setter
    def data_path(self, value):
        self._data["data_path"] = value
        self.save()

    @property
    def db_file(self):
        """Full path to the SQLite database file."""
        return os.path.join(self.data_path, "diocese.db")

    def paper_size(self, form):
        """Return the paper-size key (e.g. 'Death sheet') for a form."""
        ps = self._data.get("paper_size", {})
        if isinstance(ps, str):  # not yet migrated
            return ps
        return ps.get(form, "A4")

    def set_paper_size(self, form, value):
        ps = self._data.get("paper_size")
        if not isinstance(ps, dict):
            ps = {}
        ps[form] = value
        self._data["paper_size"] = ps
        self.save()

    @property
    def theme(self):
        return self._data.get("theme", "light")

    @theme.setter
    def theme(self, value):
        self._data["theme"] = value
        self.save()

    @property
    def accent_color(self):
        return self._data.get("accent_color", "blue")

    @accent_color.setter
    def accent_color(self, value):
        self._data["accent_color"] = value
        self.save()

    @property
    def printer_name(self):
        return self._data.get("printer_name", "")

    @printer_name.setter
    def printer_name(self, value):
        self._data["printer_name"] = value
        self.save()

    @property
    def font_name(self):
        return self._data.get("font_name", "Arial")

    @property
    def font_size_pt(self):
        return int(self._data.get("font_size_pt", 11))

    # -- calibration ------------------------------------------------------- #
    def calibration(self, form):
        """Return (x_mm, y_mm) calibration offset tuple for a form key."""
        cal = self._data.get("calibration", {}).get(form, {})
        return float(cal.get("x_mm", 0.0)), float(cal.get("y_mm", 0.0))

    def set_calibration(self, form, x_mm, y_mm):
        self._data.setdefault("calibration", {})[form] = {
            "x_mm": float(x_mm),
            "y_mm": float(y_mm),
        }
        self.save()
