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
import time
import tkinter as tk
from tkinter import filedialog


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
from secure_store import SecureStore, CryptoError
import backup
import secure_store
import ui_help
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

        # Password gate: if a password is configured, hide the main window and
        # require it before anything is built. Cancelling closes the app.
        # NOTE: we use window alpha instead of withdraw/deiconify because the
        # standalone Tk shipped by uv (python-build-standalone) does not
        # reliably restore the window after withdraw().
        self.aborted = False
        self.db = None
        self.store = None

        # First-launch bootstrap: if no password has ever been set, install the
        # default password now so the gate always runs and the user is forced to
        # change it immediately (see _check_default_password below).
        if not self.config.has_password():
            self.config.set_password("admin123")

        if self.config.has_password():
            self.attributes('-alpha', 0)          # invisible but exists
            if not self._password_gate():
                self.aborted = True
                self.destroy()
                return
            # Force a password change when the default password is still in use.
            if not self._check_default_password():
                self.aborted = True
                self.destroy()
                return
            self.attributes('-alpha', 1)          # reveal after unlock

        # Open the (encrypted) database (graceful failure dialog).
        if not self._open_database(self.config.data_path):
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

        # Re-lock the app after a period of inactivity (if a password is set).
        self._start_idle_lock()

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
    # Security: require the app password before showing the window
    # ------------------------------------------------------------------ #
    def _password_gate(self):
        """Return True to proceed, False to abort (cancelled/closed)."""
        if not self.config.has_password():
            return True
        return self._unlock_loop()

    def _unlock_loop(self):
        """Prompt for the password until correct (True) or cancelled (False).

        Wrong attempts are throttled with a growing delay (login throttling).
        """
        attempts = 0
        while True:
            pw = ui_common.prompt_password(
                self, "Unlock", "Enter the application password to continue.")
            if pw is None:
                return False  # cancelled / window closed
            if self.config.verify_password(pw):
                return True
            attempts += 1
            delay = min(attempts, 10)  # seconds: 1,2,3,... capped at 10
            ui_common.show_error(
                self, "Incorrect password",
                "That password is not correct.\n\n"
                "Please wait {} second(s) before trying again.".format(delay))
            time.sleep(delay)

    _DEFAULT_PASSWORD = "admin123"

    def _check_default_password(self):
        """Force the user to change the password if the default one is still set.

        Returns True to continue opening the app, False to abort (user cancelled).
        Uses a single dialog (warning embedded in the prompt) so the happy path
        is only ONE extra popup after the login prompt.
        """
        if not self.config.verify_password(self._DEFAULT_PASSWORD):
            return True   # not the default password — no action needed

        while True:
            new_pw = ui_common.prompt_password(
                self, "Change Required — Default Password Detected",
                "Your account is still using the default password.\n\n"
                "Please set a new password to secure the application. "
                "You cannot skip this step.",
                confirm_field=True)
            if new_pw is None:
                return False          # cancelled — abort the app
            if new_pw == self._DEFAULT_PASSWORD:
                ui_common.show_error(
                    self, "Choose a different password",
                    "That password is not allowed. Please pick a new one.")
                continue
            self.config.set_password(new_pw)
            return True               # app opens immediately — no success popup

    # ------------------------------------------------------------------ #
    # Idle auto-lock: re-require the password after inactivity
    # ------------------------------------------------------------------ #
    def _start_idle_lock(self):
        """Begin watching for inactivity (no-op if no password is set)."""
        self._locked = False
        self._last_activity = time.monotonic()
        self._idle_after_id = None
        # Any of these user actions counts as activity.
        for seq in ("<Key>", "<Button>", "<Motion>", "<MouseWheel>"):
            self.bind_all(seq, self._reset_activity, add="+")
        self._schedule_idle_check()

    def _reset_activity(self, _event=None):
        self._last_activity = time.monotonic()

    def _schedule_idle_check(self):
        if self._idle_after_id is not None:
            try:
                self.after_cancel(self._idle_after_id)
            except Exception:
                pass
        self._idle_after_id = self.after(15000, self._idle_check)  # every 15s

    def _idle_check(self):
        self._idle_after_id = None
        if self._locked:
            return  # a lock prompt is already up; it reschedules on unlock
        timeout_min = self.config.lock_timeout_min
        if self.config.has_password() and timeout_min > 0:
            idle = time.monotonic() - self._last_activity
            if idle >= timeout_min * 60:
                self._lock_screen()
                return
        self._schedule_idle_check()

    def _lock_screen(self):
        """Hide the window and require the password again."""
        if self._locked or not self.config.has_password():
            return
        self._locked = True
        self.attributes('-alpha', 0)
        if self._unlock_loop():
            self.attributes('-alpha', 1)
            self._locked = False
            self._reset_activity()
            self._schedule_idle_check()
        else:
            self._on_close()

    # ------------------------------------------------------------------ #
    # Backup / recovery (shared by the menu bar and the Settings screen)
    # ------------------------------------------------------------------ #
    def do_backup(self, parent):
        """Back up the encrypted database to a chosen external (USB) drive."""
        if self.store is None:
            ui_common.show_error(parent, "Not ready",
                                 "The database is not open yet.")
            return
        drives = backup.list_external_drives()
        if not drives:
            ui_common.show_error(
                parent, "No external drive found",
                "Insert a USB / external drive and try again.\n\n"
                "(Backups are only written to removable drives.)")
            return

        label_to_root, labels = {}, []
        for root, vol in drives:
            label = root if not vol else "{}  ({})".format(root, vol)
            labels.append(label)
            label_to_root[label] = root

        if len(labels) == 1:
            dest_root = label_to_root[labels[0]]
        else:
            picked = ui_common.choose(
                parent, "Choose drive",
                "Select the external drive to back up to:", labels)
            if picked is None:
                return
            dest_root = label_to_root[picked]

        try:
            dest = backup.make_backup(self.store.enc_path, dest_root)
        except backup.BackupError as exc:
            ui_common.show_error(parent, "Backup failed", str(exc))
            return
        ui_common.show_success(parent, "Backup complete",
                               "Encrypted backup saved to:\n{}".format(dest))

    def do_save_recovery_key(self, parent):
        """Export the encryption key so a backup can be restored on a new PC."""
        path = filedialog.asksaveasfilename(
            title="Save recovery key",
            defaultextension=".key",
            initialfile="diocese-recovery.key",
            filetypes=[("Recovery key", "*.key"), ("All files", "*.*")])
        if not path:
            return
        try:
            secure_store.export_recovery_key(path)
        except Exception as exc:
            ui_common.show_error(parent, "Could not save key", str(exc))
            return
        ui_common.show_info(
            parent, "Recovery key saved",
            "Keep this file safe and SEPARATE from your backups. Anyone with "
            "both the backup and this key can read the records.")

    def do_restore_backup(self, parent):
        """Restore the database from a backup zip chosen by the user."""
        zip_path = filedialog.askopenfilename(
            parent=parent,
            title="Choose a Diocese backup zip to restore",
            filetypes=[("Diocese backup", "*.zip"), ("All files", "*.*")])
        if not zip_path:
            return

        if not ui_common.confirm(
                parent, "Restore from backup",
                "This will REPLACE the current database with the contents of:\n"
                "{}\n\n"
                "All unsaved changes will be lost. Continue?".format(zip_path)):
            return

        # Close the current DB so we can safely overwrite the .enc file.
        try:
            if self.db is not None:
                self.db.close()
            if self.store is not None:
                self.store.close()
        except Exception:
            pass
        self.db = None
        self.store = None

        try:
            backup.restore_backup(zip_path, self.config.data_path)
        except backup.BackupError as exc:
            ui_common.show_error(parent, "Restore failed", str(exc))
            # Re-open the original database so the app keeps working.
            self._open_database(self.config.data_path)
            return

        # Reload the (now restored) database.
        if not self._open_database(self.config.data_path):
            return

        # Rebuild every section so they read from the restored DB.
        for _name, frame in list(self.sections.items()):
            frame.destroy()
        self.sections.clear()
        self.show_section("death")

        ui_common.show_success(
            parent, "Restore complete",
            "The database has been restored successfully. "
            "All records from the backup are now available.")

    # ------------------------------------------------------------------ #
    # Database lifecycle
    # ------------------------------------------------------------------ #
    def _open_database(self, data_dir):
        """Decrypt + open the database stored in ``data_dir``.

        The on-disk database is AES-encrypted; SecureStore decrypts it to a
        private working copy and re-encrypts after every write (and on close).
        """
        try:
            if self.db is not None:
                self.db.close()
            if self.store is not None:
                self.store.close()
            self.store = SecureStore(data_dir)
            working = self.store.open()
            self.db = Database(working, on_commit=self.store.encrypt_back)
            return True
        except CryptoError as exc:
            ui_common.show_error(
                self, "Cannot unlock database",
                "The encrypted database could not be opened:\n\n{}".format(exc))
            return False
        except Exception as exc:
            ui_common.show_error(
                self, "Cannot open database",
                "The database could not be opened in:\n{}\n\n{}".format(
                    data_dir, exc))
            return False

    def set_data_path(self, folder):
        """Point the app at a new database folder and rebuild the sections."""
        self.config.data_path = folder
        if not self._open_database(self.config.data_path):
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

        self._build_menubar()
        self._build_brand()
        self._build_nav()
        self._build_sidebar_footer()

        self.content = ctk.CTkFrame(self, corner_radius=0, fg_color=("#F1F5F9", "#0B1120"))
        self.content.grid(row=0, column=1, sticky="nsew")
        self.content.grid_columnconfigure(0, weight=1)
        self.content.grid_rowconfigure(0, weight=1)

    def _build_menubar(self):
        """Native menu bar: File / Help / About."""
        menubar = tk.Menu(self)

        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="Backup to USB drive…",
                              command=lambda: self.do_backup(self))
        file_menu.add_command(label="Save recovery key…",
                              command=lambda: self.do_save_recovery_key(self))
        file_menu.add_command(label="Restore from backup…",
                              command=lambda: self.do_restore_backup(self))
        file_menu.add_separator()
        file_menu.add_command(label="Settings",
                              command=lambda: self.show_section("settings"))
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self._on_close)
        menubar.add_cascade(label="File", menu=file_menu)

        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(
            label="Overview / User Guide",
            command=lambda: ui_help.open_help(self, "overview"))
        help_menu.add_separator()
        help_menu.add_command(
            label="Death Extract screen",
            command=lambda: ui_help.open_help(self, "death"))
        help_menu.add_command(
            label="Marriage Returns screen",
            command=lambda: ui_help.open_help(self, "marriage"))
        help_menu.add_command(
            label="Baptism Certificate screen",
            command=lambda: ui_help.open_help(self, "baptism"))
        help_menu.add_command(
            label="Settings screen",
            command=lambda: ui_help.open_help(self, "settings"))
        menubar.add_cascade(label="Help", menu=help_menu)

        menubar.add_command(label="About",
                            command=lambda: ui_help.open_about(self))

        # Attach to the window. self.config is shadowed by the Config object, so
        # set the native -menu option directly to stay robust.
        try:
            self.tk.call(self._w, "configure", "-menu", menubar)
        except Exception:
            try:
                self.configure(menu=menubar)
            except Exception:
                pass
        self._menubar = menubar  # keep a reference

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
        if self.current is not None and hasattr(self.current, "can_navigate_away"):
            if not self.current.can_navigate_away():
                return

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
        try:
            # Final re-encrypt + delete the plaintext working copy.
            if self.store is not None:
                self.store.close()
        except Exception:
            pass
        self.destroy()


def main():
    app = App()
    # If the password prompt was cancelled or the DB failed to open, the window
    # is already torn down — don't start the event loop.
    if getattr(app, "aborted", False):
        return
    if getattr(app, "db", None) is not None:
        # Schedule maximize for 10 ms after the event loop starts.
        # Calling state('zoomed') before mainloop() has no effect on the
        # python-build-standalone Tk that uv ships.
        def _maximize():
            try:
                app.state("zoomed")
            except Exception:
                pass
        app.after(10, _maximize)
        app.mainloop()


if __name__ == "__main__":
    main()
