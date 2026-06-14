"""
ui_help.py
==========
Help and About windows, opened from the menu bar.

* :class:`HelpWindow` — a two-pane help browser: a list of screens on the left,
  and on the right a description of that screen plus a screenshot (loaded from
  ``assets/help/<key>.png`` if present; a placeholder is shown otherwise, so you
  can drop the images in later without code changes).
* :class:`AboutWindow` — app name, version, the organisation, the developer
  company, website, and contact details (email / phone).

Only the values in the "APP / DEVELOPER INFO" block below need editing to brand
the About box.
"""

import os
import webbrowser

import customtkinter as ctk

from ui_common import (
    FONT_FAMILY, TITLE_FONT, HEADING_FONT, BUTTON_FONT, LABEL_FONT, SMALL_FONT,
    CORNER, PAD, primary_button, secondary_button,
)

try:
    from PIL import Image
    _PIL_OK = True
except Exception:
    _PIL_OK = False


# =========================================================================== #
# APP / DEVELOPER INFO  — EDIT THESE VALUES
# =========================================================================== #
APP_NAME = "Diocese Certificate Manager"

# Read from version.txt so GitHub Actions can stamp the correct version at
# build time without touching this source file.
# Local dev: edit version.txt manually to match your current tag.
try:
    _ver_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "version.txt")
    APP_VERSION = open(_ver_file).read().strip()
except Exception:
    APP_VERSION = "dev"
ORG_NAME = "Diocese of Madurai Ramnad CSI"        # organisation using the app

# --- Developer / support details (replace the placeholders) ---------------- #
DEVELOPER_NAME = "SSS Solutions"        # TODO: your company
DEVELOPER_WEBSITE = "https://ssssolutions.net"          # TODO: company website
SUPPORT_EMAIL = "service.ssssolutions@gmail.com"              # TODO: support emai
SUPPORT_PHONE = "+91 99948 74045, +91 70920 43335"                  # TODO: support phone

COPYRIGHT = "© 2026 {}".format(ORG_NAME)


# --------------------------------------------------------------------------- #
# Help content. Each topic: a title, the screenshot filename, and body paras.
# Screenshots are optional — drop PNGs into assets/help/ to make them appear.
# --------------------------------------------------------------------------- #
ASSETS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")
HELP_IMG_DIR = os.path.join(ASSETS_DIR, "help")

HELP_TOPICS = [
    ("overview", "Overview / User Guide", "overview.png", [
        "This application stores Death, Marriage and Baptism records and prints "
        "the values onto your pre-printed certificate sheets.",
        "Use the left sidebar to switch between the Death, Marriage and Baptism "
        "registers, and the Settings button for printer, paper, security and "
        "backup options.",
        "The database is encrypted on disk. If a password is set, the app asks "
        "for it on opening and re-locks after a period of inactivity.",
        "Tip: each screen has its own Help page (this window) describing exactly "
        "what its buttons do.",
    ]),
    ("death", "Death Extract screen", "death.png", [
        "Lists all Death Extract records. Use the search box to filter by name, "
        "number, serial number or date.",
        "Add: opens a blank form. Fill the fields and Save to store the record.",
        "Edit (on a row): change an existing record. Delete: remove it (asks to "
        "confirm).",
        "Print / Reprint: sends the values to the printer to land on a "
        "pre-printed Death sheet. Use Preview first to check placement.",
    ]),
    ("marriage", "Marriage Returns screen", "marriage.png", [
        "Lists Marriage Returns. Each record has shared fields plus two parties "
        "(A and B) printed in two columns.",
        "Add / Edit opens the form with both party columns; Save stores parent "
        "and party rows together.",
        "Print / Reprint overlays the values onto a pre-printed Marriage sheet; "
        "Preview shows where each value will land.",
    ]),
    ("baptism", "Baptism Certificate screen", "baptism.png", [
        "Lists Baptism Certificates. Search by christian name, surname, number "
        "or date.",
        "Add / Edit / Delete manage records; Print / Reprint overlays the values "
        "onto a pre-printed Baptism sheet.",
        "Always Preview before printing on a real sheet to avoid wasting it.",
    ]),
    ("settings", "Settings screen", "settings.png", [
        "Database location: keep the database on this PC, a USB stick or a "
        "shared folder.",
        "Appearance: light/dark theme and accent colour.",
        "Printer: choose which printer to use.",
        "Print calibration: set each form's PAPER SIZE and a whole-sheet X/Y "
        "OFFSET, with an Alignment Test you can hold over a real form.",
        "Security: set/change/remove the app password and choose the auto-lock "
        "time.",
        "Backup: save an encrypted copy to a USB drive, and save a recovery key "
        "for restoring on another computer.",
    ]),
]

_TOPIC_BY_KEY = {k: (k, t, img, body) for (k, t, img, body) in HELP_TOPICS}


# --------------------------------------------------------------------------- #
# Public entry points (reuse one window instead of stacking duplicates).
# --------------------------------------------------------------------------- #
def open_help(parent, topic="overview"):
    win = getattr(parent, "_help_window", None)
    if win is not None and win.winfo_exists():
        win.show_topic(topic)
        win.lift()
        win.focus_force()
        return win
    win = HelpWindow(parent, topic)
    parent._help_window = win
    return win


def open_about(parent):
    win = getattr(parent, "_about_window", None)
    if win is not None and win.winfo_exists():
        win.lift()
        win.focus_force()
        return win
    win = AboutWindow(parent)
    parent._about_window = win
    return win


# --------------------------------------------------------------------------- #
# Help window
# --------------------------------------------------------------------------- #
class HelpWindow(ctk.CTkToplevel):
    def __init__(self, parent, topic="overview"):
        super().__init__(parent)
        self.title("Help - {}".format(APP_NAME))
        self.geometry("860x640")
        self.minsize(720, 520)

        # Left: topic list.
        left = ctk.CTkFrame(self, width=220, corner_radius=0)
        left.pack(side="left", fill="y")
        left.pack_propagate(False)
        ctk.CTkLabel(left, text="Help topics", font=HEADING_FONT, anchor="w"
                     ).pack(fill="x", padx=PAD, pady=(PAD, 6))
        self._buttons = {}
        for key, title, _img, _body in HELP_TOPICS:
            btn = ctk.CTkButton(
                left, text=title, anchor="w", font=LABEL_FONT, height=40,
                corner_radius=CORNER, fg_color="transparent",
                command=lambda k=key: self.show_topic(k))
            btn.pack(fill="x", padx=8, pady=2)
            self._buttons[key] = btn

        # Right: scrollable content.
        self._content = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self._content.pack(side="left", fill="both", expand=True)

        self._image_ref = None  # keep a reference so Tk doesn't GC the image
        self.show_topic(topic)
        self._bring_to_front()

    @staticmethod
    def _bring_to_front_after(win):
        """Flash topmost on then off — reliable way to raise a CTkToplevel on
        Windows without permanently pinning it above every other application."""
        try:
            win.attributes("-topmost", True)
            win.lift()
            win.focus_force()
            win.after(200, lambda: win.attributes("-topmost", False))
        except Exception:
            pass

    def _bring_to_front(self):
        self.after(50, lambda: HelpWindow._bring_to_front_after(self))

    def show_topic(self, key):
        key, title, img_file, body = _TOPIC_BY_KEY.get(
            key, _TOPIC_BY_KEY["overview"])

        # Highlight the active topic button.
        for k, btn in self._buttons.items():
            btn.configure(fg_color=("#2563EB" if k == key else "transparent"),
                          text_color=("white" if k == key else ("#1E293B", "#E2E8F0")))

        for child in self._content.winfo_children():
            child.destroy()

        ctk.CTkLabel(self._content, text=title, font=TITLE_FONT, anchor="w",
                     justify="left").pack(fill="x", padx=PAD, pady=(PAD, 8))

        self._add_screenshot(img_file)

        for para in body:
            ctk.CTkLabel(self._content, text="•  " + para, font=LABEL_FONT,
                         anchor="w", justify="left", wraplength=560
                         ).pack(fill="x", padx=PAD, pady=4)

    def _add_screenshot(self, img_file):
        path = os.path.join(HELP_IMG_DIR, img_file)
        if _PIL_OK and os.path.exists(path):
            try:
                img = Image.open(path)
                w, h = img.size
                max_w = 560
                if w > max_w:
                    size = (max_w, max(1, int(h * max_w / w)))
                else:
                    size = (w, h)
                ctk_img = ctk.CTkImage(light_image=img, dark_image=img,
                                       size=size)
                label = ctk.CTkLabel(self._content, text="", image=ctk_img)
                label.pack(padx=PAD, pady=(0, 10), anchor="w")
                self._image_ref = ctk_img
                return
            except Exception:
                pass
        # Placeholder when no screenshot is available yet.
        ph = ctk.CTkFrame(self._content, height=120, corner_radius=CORNER,
                          fg_color=("#E2E8F0", "#1E293B"))
        ph.pack(fill="x", padx=PAD, pady=(0, 10))
        ctk.CTkLabel(
            ph,
            text="Screenshot placeholder\n(add  assets/help/{}  to show it here)"
                 .format(img_file),
            font=SMALL_FONT, text_color="gray").pack(expand=True, pady=20)


# --------------------------------------------------------------------------- #
# About window
# --------------------------------------------------------------------------- #
class AboutWindow(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("About {}".format(APP_NAME))
        self.geometry("460x460")
        self.resizable(False, False)

        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=24, pady=20)

        self._logo_ref = self._load_logo()
        if self._logo_ref is not None:
            ctk.CTkLabel(body, text="", image=self._logo_ref).pack(pady=(0, 8))

        ctk.CTkLabel(body, text=APP_NAME, font=TITLE_FONT).pack()
        ctk.CTkLabel(body, text="Version {}".format(APP_VERSION),
                     font=LABEL_FONT, text_color="gray").pack(pady=(0, 10))

        ctk.CTkLabel(body, text="For: {}".format(ORG_NAME), font=LABEL_FONT
                     ).pack(pady=(6, 0))
        ctk.CTkLabel(body, text="Developed by: {}".format(DEVELOPER_NAME),
                     font=LABEL_FONT).pack(pady=(2, 10))

        # Clickable website / email / phone.
        self._link_row(body, "Website", DEVELOPER_WEBSITE,
                       lambda: _open(DEVELOPER_WEBSITE))
        self._link_row(body, "Email", SUPPORT_EMAIL,
                       lambda: _open("mailto:" + SUPPORT_EMAIL))
        self._link_row(body, "Phone", SUPPORT_PHONE,
                       lambda: _open("tel:" + SUPPORT_PHONE.replace(" ", "")))

        ctk.CTkLabel(body, text=COPYRIGHT, font=SMALL_FONT, text_color="gray"
                     ).pack(side="bottom", pady=(10, 0))
        primary_button(body, "Close", command=self.destroy, width=120
                       ).pack(side="bottom", pady=(14, 0))

        self.transient(parent)
        self.after(50, lambda: HelpWindow._bring_to_front_after(self))

    def _link_row(self, parent, label, value, command):
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", pady=3)
        ctk.CTkLabel(row, text=label, font=LABEL_FONT, width=80, anchor="w"
                     ).pack(side="left")
        ctk.CTkButton(row, text=value, font=LABEL_FONT, anchor="w",
                      fg_color="transparent", text_color="#2563EB",
                      hover=False, command=command).pack(side="left")

    def _load_logo(self):
        if not _PIL_OK:
            return None
        path = os.path.join(ASSETS_DIR, "logo.png")
        if not os.path.exists(path):
            return None
        try:
            img = Image.open(path)
            return ctk.CTkImage(light_image=img, dark_image=img, size=(64, 64))
        except Exception:
            return None


def _open(url):
    try:
        webbrowser.open(url)
    except Exception:
        pass
