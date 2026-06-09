"""
main.py
=======
Application bootstrap for the Diocese Certificate Manager.

* Creates the CustomTkinter root window.
* Builds a modern **web-dashboard style left sidebar** (logo + nav items with
  icons, an active-item highlight, a theme toggle pinned to the bottom).
* Swaps the main content frame between the Death / Marriage / Baptism / Settings
  sections.
* Owns the shared Config and Database objects and hands them to each section
  via ``app`` (so sections call ``self.app.db`` / ``self.app.config``).

Run with:  python main.py
Build with: build.bat  (Nuitka standalone)
"""

import os
import sys
import glob
import tkinter as tk


def _ensure_tcl_tk():
    """
    Some standalone CPython builds (e.g. the ones uv downloads, or
    python-build-standalone) bundle Tcl/Tk but don't set TCL_LIBRARY /
    TK_LIBRARY, so tkinter fails with "Can't find a usable init.tcl".

    Point those env vars at the bundled library *before* tkinter is imported.
    This is a no-op on a normal python.org / Windows install where Tk is
    already configured, and must run before ``import customtkinter``.
    """
    if os.environ.get("TCL_LIBRARY") and os.environ.get("TK_LIBRARY"):
        return
    for root in {sys.base_prefix, sys.prefix}:
        for sub in ("lib", "tcl", ""):
            base = os.path.join(root, sub) if sub else root
            tcl = sorted(glob.glob(os.path.join(base, "tcl8.*")))
            tk = sorted(glob.glob(os.path.join(base, "tk8.*")))
            # Keep real library dirs (they contain init.tcl / tk.tcl).
            tcl = [d for d in tcl if os.path.exists(os.path.join(d, "init.tcl"))]
            tk = [d for d in tk if os.path.exists(os.path.join(d, "tk.tcl"))]
            if tcl and tk:
                os.environ.setdefault("TCL_LIBRARY", tcl[-1])
                os.environ.setdefault("TK_LIBRARY", tk[-1])
                return


_ensure_tcl_tk()

import customtkinter as ctk

from config import Config
from db import Database
import ui_common
from ui_death import DeathSection
from ui_marriage import MarriageSection
from ui_baptism import BaptismSection
from ui_settings import SettingsSection


# Resolve the assets folder both when run from source and when frozen by Nuitka.
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ASSETS_DIR = os.path.join(BASE_DIR, "assets")

APP_TITLE = "Diocese Certificate Manager"
DIOCESE_NAME = "Diocese of Madurai Ramnad"
DIOCESE_SUB = "Church of South India"

# Sidebar palette (web-app look). Tuple = (light, dark).
SIDEBAR_BG = ("#1E293B", "#0F172A")        # slate
SIDEBAR_ITEM_HOVER = ("#334155", "#1E293B")
SIDEBAR_ACTIVE = ("#2563EB", "#3B82F6")    # accent highlight
SIDEBAR_TEXT = "#E2E8F0"
SIDEBAR_TEXT_DIM = "#94A3B8"

NAV_ITEMS = [
    ("death", "Death", "🕮"),
    ("marriage", "Marriage", "💍"),
    ("baptism", "Baptism", "✝"),
]


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.config = Config()

        # Appearance must be set before widgets are created.
        ctk.set_appearance_mode(self.config.theme)
        try:
            ctk.set_default_color_theme(self.config.accent_color)
        except Exception:
            ctk.set_default_color_theme("blue")

        self.title(APP_TITLE)
        self.geometry("1180x760")
        self.minsize(960, 620)

        # Open the database (graceful failure dialog).
        self.db = None
        if not self._open_database(self.config.db_file):
            return

        self.sections = {}        # name -> frame instance (lazy)
        self.nav_buttons = {}     # name -> button
        self.current = None

        self._build_layout()
        self.show_section("death")

        # Pre-build the other sections once the window is on screen and idle, so
        # the first click on Marriage / Baptism / Settings is instant instead of
        # pausing to construct their (large) forms. Staggered so the UI stays
        # responsive while they build.
        self.after(120, self._prewarm_sections)

        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _prewarm_sections(self):
        """Build the remaining sections AND their (heavy) entry forms in the
        background, one step per idle tick, so the first click on any nav item
        or on Add/Edit is instant instead of pausing ~1s to construct widgets.
        """
        # Step 1: make sure every section object exists.
        pending = [n for n in ("marriage", "baptism", "settings")
                   if n not in self.sections]
        if pending:
            self._get_section(pending[0])
            self.after(60, self._prewarm_sections)
            return
        # Step 2: pre-build each record section's lazy entry form.
        for name in ("death", "marriage", "baptism"):
            section = self.sections.get(name)
            if section is not None and getattr(section, "entry_view", True) is None:
                section._ensure_entry_view()
                self.after(60, self._prewarm_sections)
                return

    # ------------------------------------------------------------------ #
    # Database lifecycle
    # ------------------------------------------------------------------ #
    def _open_database(self, db_file):
        try:
            if self.db is not None:
                self.db.close()
            self.db = Database(db_file)
            return True
        except Exception as exc:
            ui_common.show_error(
                self, "Cannot open database",
                "The database could not be opened at:\n{}\n\n{}".format(db_file, exc))
            return False

    def set_data_path(self, folder):
        """Point the app at a new database folder and rebuild the sections."""
        self.config.data_path = folder
        if not self._open_database(self.config.db_file):
            raise RuntimeError("Failed to open database in new folder.")
        # Drop cached sections so they re-read from the new DB.
        for name, frame in list(self.sections.items()):
            frame.destroy()
        self.sections.clear()
        self.show_section("settings")

    # ------------------------------------------------------------------ #
    # Theme
    # ------------------------------------------------------------------ #
    def set_theme(self, theme):
        self.config.theme = theme
        ctk.set_appearance_mode(theme)

    def _toggle_theme(self):
        new = "dark" if self.config.theme == "light" else "light"
        self.set_theme(new)
        self.theme_btn.configure(
            text=("🌙  Dark mode" if new == "light" else "☀  Light mode"))

    # ------------------------------------------------------------------ #
    # Layout: sidebar + content
    # ------------------------------------------------------------------ #
    def _build_layout(self):
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.sidebar = ctk.CTkFrame(
            self, width=240, corner_radius=0, fg_color=SIDEBAR_BG)
        self.sidebar.grid(row=0, column=0, sticky="nsw")
        self.sidebar.grid_propagate(False)
        self.sidebar.grid_rowconfigure(2, weight=1)  # spacer row pushes footer down

        self._build_brand()
        self._build_nav()
        self._build_sidebar_footer()

        self.content = ctk.CTkFrame(self, corner_radius=0, fg_color=("#F1F5F9", "#0B1120"))
        self.content.grid(row=0, column=1, sticky="nsew")
        self.content.grid_columnconfigure(0, weight=1)
        self.content.grid_rowconfigure(0, weight=1)

    def _build_brand(self):
        brand = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        brand.grid(row=0, column=0, sticky="ew", padx=18, pady=(22, 10))

        # Logo emblem: drawn with a Tk Canvas (a rounded accent square + white
        # cross) rather than loaded from a raster image. This keeps the runtime
        # free of any image-decoding dependency and avoids a Tk/Pillow X11
        # threading crash seen with PhotoImage on some standalone Tk builds.
        self._draw_logo(brand)

        ctk.CTkLabel(brand, text=DIOCESE_NAME, font=(ui_common.FONT_FAMILY, 16, "bold"),
                     text_color=SIDEBAR_TEXT, justify="left", anchor="w",
                     wraplength=200).pack(fill="x")
        ctk.CTkLabel(brand, text=DIOCESE_SUB, font=(ui_common.FONT_FAMILY, 12),
                     text_color=SIDEBAR_TEXT_DIM, anchor="w").pack(fill="x")

        ctk.CTkFrame(self.sidebar, height=1, fg_color="#334155"
                     ).grid(row=0, column=0, sticky="sew", padx=16)

    @staticmethod
    def _draw_logo(parent):
        """Vector-draw the cross emblem on a small Canvas (no image files)."""
        size = 52
        accent = "#2563EB"
        sidebar_bg = "#1E293B" if ctk.get_appearance_mode() == "Light" else "#0F172A"
        canvas = tk.Canvas(parent, width=size, height=size, highlightthickness=0,
                           bg=sidebar_bg, bd=0)
        canvas.pack(pady=(0, 10))
        # Rounded accent square (approximated with rectangles + corner ovals).
        r = 12
        canvas.create_rectangle(r, 2, size - r, size - 2, fill=accent, outline="")
        canvas.create_rectangle(2, r, size - 2, size - r, fill=accent, outline="")
        for cx, cy in ((2, 2), (size - 2 * r - 2, 2),
                       (2, size - 2 * r - 2), (size - 2 * r - 2, size - 2 * r - 2)):
            canvas.create_oval(cx, cy, cx + 2 * r, cy + 2 * r, fill=accent, outline="")
        # White cross.
        cx = size / 2
        canvas.create_rectangle(cx - 3, 12, cx + 3, size - 12, fill="white", outline="")
        canvas.create_rectangle(size * 0.30, size * 0.40, size * 0.70, size * 0.40 + 6,
                                fill="white", outline="")

    def _build_nav(self):
        nav = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        nav.grid(row=1, column=0, sticky="new", padx=12, pady=(12, 0))

        ctk.CTkLabel(nav, text="RECORDS", font=(ui_common.FONT_FAMILY, 11, "bold"),
                     text_color=SIDEBAR_TEXT_DIM, anchor="w"
                     ).pack(fill="x", padx=8, pady=(0, 6))

        for name, label, icon in NAV_ITEMS:
            self.nav_buttons[name] = self._nav_button(nav, name, label, icon)

    def _nav_button(self, parent, name, label, icon):
        btn = ctk.CTkButton(
            parent, text="  {}   {}".format(icon, label),
            anchor="w", font=(ui_common.FONT_FAMILY, 15),
            height=46, corner_radius=10,
            fg_color="transparent", hover_color=SIDEBAR_ITEM_HOVER,
            text_color=SIDEBAR_TEXT,
            command=lambda n=name: self.show_section(n),
        )
        btn.pack(fill="x", pady=3)
        return btn

    def _build_sidebar_footer(self):
        footer = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        footer.grid(row=3, column=0, sticky="sew", padx=12, pady=(0, 16))

        self.nav_buttons["settings"] = ctk.CTkButton(
            footer, text="  ⚙   Settings", anchor="w",
            font=(ui_common.FONT_FAMILY, 15), height=46, corner_radius=10,
            fg_color="transparent", hover_color=SIDEBAR_ITEM_HOVER,
            text_color=SIDEBAR_TEXT,
            command=lambda: self.show_section("settings"))
        self.nav_buttons["settings"].pack(fill="x", pady=3)

        self.theme_btn = ctk.CTkButton(
            footer,
            text=("🌙  Dark mode" if self.config.theme == "light" else "☀  Light mode"),
            anchor="w", font=(ui_common.FONT_FAMILY, 14), height=42, corner_radius=10,
            fg_color="transparent", hover_color=SIDEBAR_ITEM_HOVER,
            text_color=SIDEBAR_TEXT_DIM, command=self._toggle_theme)
        self.theme_btn.pack(fill="x", pady=(8, 0))

        ctk.CTkLabel(footer, text="v1.0.0", font=(ui_common.FONT_FAMILY, 11),
                     text_color=SIDEBAR_TEXT_DIM).pack(anchor="w", pady=(8, 0))

    # ------------------------------------------------------------------ #
    # Navigation
    # ------------------------------------------------------------------ #
    def show_section(self, name):
        section = self._get_section(name)
        if section is self.current:
            return
        # All sections share the SAME grid cell and stay gridded; switching is
        # just a Z-order change (tkraise). Nothing is un-gridded, so the content
        # frame never relayouts or blanks — this removes the switch flicker that
        # grid/grid_remove caused.
        section.tkraise()
        self.current = section
        self._highlight_nav(name)

    def _get_section(self, name):
        if name not in self.sections:
            factory = {
                "death": DeathSection,
                "marriage": MarriageSection,
                "baptism": BaptismSection,
                "settings": SettingsSection,
            }[name]
            section = factory(self.content, self)
            # Grid it once into the shared cell, then push it BELOW the current
            # section so building extra sections (e.g. during prewarm) never
            # covers the one the user is looking at.
            section.grid(row=0, column=0, sticky="nsew", padx=18, pady=18)
            if self.current is not None:
                section.lower(self.current)
            self.sections[name] = section
        return self.sections[name]

    def _highlight_nav(self, active):
        for name, btn in self.nav_buttons.items():
            if name == active:
                btn.configure(fg_color=SIDEBAR_ACTIVE, text_color="white")
            else:
                dim = name in ("settings",)
                btn.configure(fg_color="transparent",
                              text_color=SIDEBAR_TEXT_DIM if dim else SIDEBAR_TEXT)

    # ------------------------------------------------------------------ #
    def _on_close(self):
        try:
            if self.db is not None:
                self.db.close()
        except Exception:
            pass
        self.destroy()


def main():
    app = App()
    # If the DB failed to open, the window may already be torn down.
    if getattr(app, "db", None) is not None:
        app.mainloop()


if __name__ == "__main__":
    main()
