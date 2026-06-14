"""
ui_settings.py
==============
Settings screen:
  * Database folder (folder picker) – move/point the DB to USB or a network share.
  * Paper size (A4 / Letter).
  * Theme (light / dark) + accent colour.
  * Printer selection.
  * Per-form print calibration (global X / Y offset in mm) with a
    "Print Alignment Test" button for each form.
"""

import os
from tkinter import filedialog

import backup as backup_mod

import customtkinter as ctk

import layouts
import printing
from ui_common import (
    Card, show_success, show_error, show_info, confirm, prompt_password,
    TITLE_FONT, HEADING_FONT, BUTTON_FONT, LABEL_FONT, SMALL_FONT,
    CORNER, PAD,
    primary_button, secondary_button,
)

_ACCENTS = ["blue", "green", "dark-blue"]
_FORMS = [("death", "Death Extract"), ("marriage", "Marriage Returns"),
          ("baptism", "Baptism Certificate")]


class SettingsSection(ctk.CTkFrame):
    def __init__(self, parent, app):
        super().__init__(parent, fg_color="transparent")
        self.app = app
        self.cfg = app.config
        self.cal_entries = {}

        view = ctk.CTkScrollableFrame(self, fg_color="transparent")
        view.pack(fill="both", expand=True)

        ctk.CTkLabel(view, text="Settings", font=TITLE_FONT, anchor="w"
                     ).pack(fill="x", padx=PAD, pady=(PAD, 0))

        self._build_backup_card(view)
        self._build_security_card(view)
        self._build_printer_card(view)
        self._build_data_card(view)
        self._build_appearance_card(view)
        self._build_calibration_card(view)

    # ------------------------------------------------------------------ #
    def _build_data_card(self, parent):
        card = Card(parent, title="Database location")
        card.pack(fill="x", padx=PAD, pady=(PAD, 0))
        body = ctk.CTkFrame(card, fg_color="transparent")
        body.pack(fill="x", padx=PAD, pady=(0, PAD))
        ctk.CTkLabel(body, text="The database can live on a USB stick or shared "
                     "network folder.", font=SMALL_FONT, text_color="gray",
                     anchor="w").pack(fill="x")
        row = ctk.CTkFrame(body, fg_color="transparent")
        row.pack(fill="x", pady=(8, 0))
        self.path_label = ctk.CTkLabel(row, text=self.cfg.data_path, font=LABEL_FONT,
                                       anchor="w")
        self.path_label.pack(side="left", fill="x", expand=True)
        ctk.CTkButton(row, text="Change folder...", font=BUTTON_FONT, height=38,
                      corner_radius=CORNER, command=self._change_data_path
                      ).pack(side="right")

    def _change_data_path(self):
        folder = filedialog.askdirectory(
            title="Choose folder for the database", initialdir=self.cfg.data_path)
        if not folder:
            return
        if not confirm(self, "Move database location",
                       "Use this folder for the database?\n\n{}\n\n"
                       "A new encrypted database will be created here if one "
                       "doesn't exist.".format(folder)):
            return
        try:
            self.app.set_data_path(folder)
        except Exception as exc:
            show_error(self, "Could not change folder", str(exc))
            return
        self.path_label.configure(text=self.cfg.data_path)
        show_success(self, "Database folder updated",
                     "Now using:\n{}".format(self.cfg.data_path))

    # ------------------------------------------------------------------ #
    def _build_appearance_card(self, parent):
        card = Card(parent, title="Appearance")
        card.pack(fill="x", padx=PAD, pady=(PAD, 0))
        body = ctk.CTkFrame(card, fg_color="transparent")
        body.pack(fill="x", padx=PAD, pady=(0, PAD))

        # Theme
        trow = ctk.CTkFrame(body, fg_color="transparent")
        trow.pack(fill="x", pady=6)
        ctk.CTkLabel(trow, text="Theme", font=LABEL_FONT, width=140, anchor="w"
                     ).pack(side="left")
        self.theme_switch = ctk.CTkSegmentedButton(
            trow, values=["light", "dark"], font=BUTTON_FONT,
            command=self._set_theme)
        self.theme_switch.set(self.cfg.theme)
        self.theme_switch.pack(side="left")

        # Accent colour
        arow = ctk.CTkFrame(body, fg_color="transparent")
        arow.pack(fill="x", pady=6)
        ctk.CTkLabel(arow, text="Accent colour", font=LABEL_FONT, width=140,
                     anchor="w").pack(side="left")
        self.accent_menu = ctk.CTkOptionMenu(
            arow, values=_ACCENTS, font=BUTTON_FONT, command=self._set_accent)
        self.accent_menu.set(self.cfg.accent_color)
        self.accent_menu.pack(side="left")
        ctk.CTkLabel(arow, text="(applies after restart)", font=SMALL_FONT,
                     text_color="gray").pack(side="left", padx=8)

    def _set_theme(self, value):
        self.app.set_theme(value)

    def _set_accent(self, value):
        self.cfg.accent_color = value
        show_info(self, "Accent colour saved",
                  "Restart the application to apply the new accent colour.")

    # ------------------------------------------------------------------ #
    def _build_printer_card(self, parent):
        card = Card(parent, title="Printer")
        card.pack(fill="x", padx=PAD, pady=(PAD, 0))
        body = ctk.CTkFrame(card, fg_color="transparent")
        body.pack(fill="x", padx=PAD, pady=(0, PAD))

        printers = printing.get_printers()
        if not printers:
            ctk.CTkLabel(body, text="No printers detected (or running off-Windows). "
                         "The system default printer will be used when available.",
                         font=SMALL_FONT, text_color="gray", anchor="w",
                         wraplength=520, justify="left").pack(fill="x")
        else:
            options = ["(system default)"] + printers
            row = ctk.CTkFrame(body, fg_color="transparent")
            row.pack(fill="x", pady=6)
            ctk.CTkLabel(row, text="Printer", font=LABEL_FONT, width=140, anchor="w"
                         ).pack(side="left")
            self.printer_menu = ctk.CTkOptionMenu(
                row, values=options, font=BUTTON_FONT, command=self._set_printer,
                width=320)
            current = self.cfg.printer_name or "(system default)"
            self.printer_menu.set(current if current in options else "(system default)")
            self.printer_menu.pack(side="left")

        # Print Font
        import tkinter.font as tkfont
        fonts = sorted(list(set(tkfont.families())))
        if not fonts:
            fonts = ["Courier", "Arial", "Times New Roman"]

        frow = ctk.CTkFrame(body, fg_color="transparent")
        frow.pack(fill="x", pady=6)
        ctk.CTkLabel(frow, text="Print Font", font=LABEL_FONT, width=140, anchor="w").pack(side="left")
        self.font_menu = ctk.CTkOptionMenu(
            frow, values=fonts, font=BUTTON_FONT, width=240)
        
        current_font = self.cfg.font_name
        if current_font not in fonts:
            fonts.append(current_font)
            fonts.sort()
            self.font_menu.configure(values=fonts)
        self.font_menu.set(current_font)
        self.font_menu.pack(side="left")

        # Print Font Size
        srow = ctk.CTkFrame(body, fg_color="transparent")
        srow.pack(fill="x", pady=6)
        ctk.CTkLabel(srow, text="Print Font Size", font=LABEL_FONT, width=140, anchor="w").pack(side="left")
        self.size_entry = ctk.CTkEntry(srow, font=LABEL_FONT, width=80, corner_radius=CORNER)
        self.size_entry.insert(0, str(self.cfg.font_size_pt))
        self.size_entry.pack(side="left")

        primary_button(srow, "Apply Font", font=BUTTON_FONT, width=90, height=32,
                       command=self._save_font).pack(side="left", padx=12)

    def _set_printer(self, value):
        self.cfg.printer_name = "" if value == "(system default)" else value

    def _save_font(self):
        font_name = self.font_menu.get().strip()
        if not font_name:
            font_name = "Courier"
            self.font_menu.set(font_name)
        self.cfg.font_name = font_name
        try:
            sz = int(self.size_entry.get())
            if sz < 6 or sz > 72:
                raise ValueError
            self.cfg.font_size_pt = sz
            show_success(self, "Font saved", "Print font updated to {} {}pt.".format(font_name, sz))
        except ValueError:
            show_error(self, "Invalid size", "Please enter a valid font size between 6 and 72.")

    # ------------------------------------------------------------------ #
    def _build_calibration_card(self, parent):
        card = Card(parent, title="Print calibration")
        card.pack(fill="x", padx=PAD, pady=(PAD, PAD))
        body = ctk.CTkFrame(card, fg_color="transparent")
        body.pack(fill="x", padx=PAD, pady=(0, PAD))
        ctk.CTkLabel(
            body,
            text="Nudge the whole printout to line up with the pre-printed sheet. "
                 "Positive X moves right, positive Y moves down (millimetres). "
                 "Print a test on plain paper, hold it over a real form against "
                 "the light, then adjust.",
            font=SMALL_FONT, text_color="gray", anchor="w", justify="left",
            wraplength=560).pack(fill="x", pady=(0, 8))

        paper_choices = list(layouts.PAGE_SIZES_MM.keys())

        for form_key, form_title in _FORMS:
            x_mm, y_mm = self.cfg.calibration(form_key)
            block = ctk.CTkFrame(body, corner_radius=CORNER)
            block.pack(fill="x", pady=6)
            ctk.CTkLabel(block, text=form_title, font=HEADING_FONT,
                         anchor="w").pack(fill="x", padx=PAD, pady=(PAD, 0))

            # Paper size for this form.
            paper_row = ctk.CTkFrame(block, fg_color="transparent")
            paper_row.pack(fill="x", padx=PAD, pady=(6, 0))
            ctk.CTkLabel(paper_row, text="Paper size", font=LABEL_FONT,
                         width=90, anchor="w").pack(side="left")
            paper_menu = ctk.CTkOptionMenu(
                paper_row, values=paper_choices, font=BUTTON_FONT, width=200,
                command=lambda v, f=form_key: self._set_paper(f, v))
            paper_menu.set(self.cfg.paper_size(form_key))
            paper_menu.pack(side="left")

            # Calibration offset for this form.
            row = ctk.CTkFrame(block, fg_color="transparent")
            row.pack(fill="x", padx=PAD, pady=(6, PAD))
            ctk.CTkLabel(row, text="Offset", font=LABEL_FONT, width=90,
                         anchor="w").pack(side="left")
            ctk.CTkLabel(row, text="X", font=LABEL_FONT).pack(side="left", padx=(8, 2))
            x_entry = ctk.CTkEntry(row, width=70, font=LABEL_FONT, corner_radius=CORNER)
            x_entry.insert(0, str(x_mm))
            x_entry.pack(side="left")
            ctk.CTkLabel(row, text="Y", font=LABEL_FONT).pack(side="left", padx=(8, 2))
            y_entry = ctk.CTkEntry(row, width=70, font=LABEL_FONT, corner_radius=CORNER)
            y_entry.insert(0, str(y_mm))
            y_entry.pack(side="left")
            self.cal_entries[form_key] = (x_entry, y_entry)

            primary_button(row, "Save", command=lambda f=form_key: self._save_cal(f),
                           font=SMALL_FONT, width=70, height=34
                           ).pack(side="left", padx=(10, 4))
            secondary_button(row, "Alignment Test",
                             command=lambda f=form_key: self._alignment_test(f),
                             font=SMALL_FONT, width=130, height=34
                             ).pack(side="left", padx=4)

    def _set_paper(self, form_key, value):
        self.cfg.set_paper_size(form_key, value)

    def _save_cal(self, form_key):
        x_entry, y_entry = self.cal_entries[form_key]
        try:
            x_mm = float(x_entry.get() or 0)
            y_mm = float(y_entry.get() or 0)
        except ValueError:
            show_error(self, "Invalid offset", "X and Y must be numbers (mm).")
            return
        self.cfg.set_calibration(form_key, x_mm, y_mm)
        show_success(self, "Calibration saved",
                     "Offset for this form saved: X={} mm, Y={} mm.".format(x_mm, y_mm))

    def _alignment_test(self, form_key):
        # Save the current offset first so the test reflects the entry boxes.
        x_entry, y_entry = self.cal_entries[form_key]
        try:
            self.cfg.set_calibration(form_key, float(x_entry.get() or 0),
                                     float(y_entry.get() or 0))
        except ValueError:
            show_error(self, "Invalid offset", "X and Y must be numbers (mm).")
            return
        try:
            printing.print_record(form_key, {}, self.cfg, alignment_test=True)
        except printing.PrinterError as exc:
            show_error(self, "Printing problem", str(exc))
            return
        show_info(self, "Alignment test sent",
                  "A marker sheet was sent to the printer. Overlay it on a real "
                  "form and adjust the X/Y offset until the markers sit on the lines.")

    # ------------------------------------------------------------------ #
    # Security: app-open password
    # ------------------------------------------------------------------ #
    def _build_security_card(self, parent):
        card = Card(parent, title="Security")
        card.pack(fill="x", padx=PAD, pady=(PAD, PAD))
        self.security_body = ctk.CTkFrame(card, fg_color="transparent")
        self.security_body.pack(fill="x", padx=PAD, pady=(0, PAD))
        self._refresh_security_body()

    def _refresh_security_body(self):
        body = self.security_body
        for child in body.winfo_children():
            child.destroy()

        has = self.cfg.has_password()
        status = ("A password is required each time the app opens."
                  if has else
                  "No password set. The app opens without asking.")
        ctk.CTkLabel(body, text=status, font=SMALL_FONT, text_color="gray",
                     anchor="w", justify="left", wraplength=560
                     ).pack(fill="x", pady=(0, 8))

        row = ctk.CTkFrame(body, fg_color="transparent")
        row.pack(fill="x")
        if has:
            primary_button(row, "Change password",
                           command=self._change_password,
                           font=SMALL_FONT, width=160, height=36
                           ).pack(side="left", padx=(0, 8))
            secondary_button(row, "Remove password",
                             command=self._remove_password,
                             font=SMALL_FONT, width=160, height=36
                             ).pack(side="left")
        else:
            primary_button(row, "Set password",
                           command=self._set_password,
                           font=SMALL_FONT, width=160, height=36
                           ).pack(side="left")

        # Auto-lock after inactivity (only meaningful when a password is set).
        lock_row = ctk.CTkFrame(body, fg_color="transparent")
        lock_row.pack(fill="x", pady=(10, 0))
        ctk.CTkLabel(lock_row, text="Auto-lock after", font=LABEL_FONT,
                     width=120, anchor="w").pack(side="left")
        self.lock_menu = ctk.CTkOptionMenu(
            lock_row, values=list(self._LOCK_CHOICES.keys()), font=BUTTON_FONT,
            width=150, command=self._set_lock_timeout)
        self.lock_menu.set(self._lock_label_for(self.cfg.lock_timeout_min))
        self.lock_menu.pack(side="left")
        if not has:
            ctk.CTkLabel(lock_row, text="(set a password to use this)",
                         font=SMALL_FONT, text_color="gray"
                         ).pack(side="left", padx=8)

    # label -> minutes (0 = never)
    _LOCK_CHOICES = {
        "Never": 0, "1 minute": 1, "5 minutes": 5,
        "10 minutes": 10, "15 minutes": 15, "30 minutes": 30,
    }

    def _lock_label_for(self, minutes):
        for label, mins in self._LOCK_CHOICES.items():
            if mins == minutes:
                return label
        return "5 minutes"

    def _set_lock_timeout(self, label):
        self.cfg.lock_timeout_min = self._LOCK_CHOICES.get(label, 5)

    def _ask_new_password(self):
        """Prompt for a new password (with confirmation). Returns str or None."""
        return prompt_password(
            self, "Set password",
            "Enter a password. You will be asked for it each time the app opens.",
            confirm_field=True)

    def _verify_current(self):
        """Ask for the current password; True if correct (or none set)."""
        if not self.cfg.has_password():
            return True
        current = prompt_password(self, "Confirm current password",
                                  "Enter your current password to continue.")
        if current is None:
            return False
        if not self.cfg.verify_password(current):
            show_error(self, "Incorrect password",
                       "The current password is not correct.")
            return False
        return True

    def _set_password(self):
        new = self._ask_new_password()
        if new is None:
            return
        self.cfg.set_password(new)
        self._refresh_security_body()
        show_success(self, "Password set",
                     "The app will now ask for this password on startup.")

    def _change_password(self):
        if not self._verify_current():
            return
        new = self._ask_new_password()
        if new is None:
            return
        self.cfg.set_password(new)
        self._refresh_security_body()
        show_success(self, "Password changed", "Your new password is saved.")

    def _remove_password(self):
        if not self._verify_current():
            return
        if not confirm(self, "Remove password",
                       "Remove the password? The app will open without asking."):
            return
        self.cfg.set_password("")
        self._refresh_security_body()
        show_success(self, "Password removed",
                     "The app will no longer ask for a password.")

    # ------------------------------------------------------------------ #
    # Backup & Restore
    # ------------------------------------------------------------------ #
    def _build_backup_card(self, parent):
        card = Card(parent, title="Backup & Restore")
        card.pack(fill="x", padx=PAD, pady=(PAD, PAD))
        body = ctk.CTkFrame(card, fg_color="transparent")
        body.pack(fill="x", padx=PAD, pady=(0, PAD))

        # -- Backup section --
        ctk.CTkLabel(
            body,
            text="Save an encrypted copy of the database to a USB / external "
                 "drive. The backup includes the recovery key so it can be "
                 "restored on any PC from a single zip file.",
            font=SMALL_FONT, text_color="gray", anchor="w", justify="left",
            wraplength=560).pack(fill="x", pady=(0, 8))

        backup_row = ctk.CTkFrame(body, fg_color="transparent")
        backup_row.pack(fill="x")
        primary_button(backup_row, "Backup to USB drive…",
                       command=self._backup_now,
                       font=SMALL_FONT, width=190, height=36
                       ).pack(side="left", padx=(0, 8))
        secondary_button(backup_row, "Save recovery key…",
                         command=self._save_recovery_key,
                         font=SMALL_FONT, width=190, height=36
                         ).pack(side="left")

        # -- Divider --
        ctk.CTkFrame(body, height=1, fg_color=("#CBD5E1", "#334155")
                     ).pack(fill="x", pady=(16, 8))

        # -- Restore section --
        ctk.CTkLabel(
            body, text="Restore from Backup",
            font=("Segoe UI", 14, "bold"), anchor="w"
        ).pack(fill="x", pady=(0, 4))
        ctk.CTkLabel(
            body,
            text="Pick a diocese backup zip to restore all records. "
                 "The current database will be replaced. "
                 "Use the same zip file from Settings → Backup to USB drive.",
            font=SMALL_FONT, text_color="gray", anchor="w", justify="left",
            wraplength=560).pack(fill="x", pady=(0, 8))

        restore_row = ctk.CTkFrame(body, fg_color="transparent")
        restore_row.pack(fill="x")
        secondary_button(restore_row, "Restore from backup…",
                         command=self._restore_backup,
                         font=SMALL_FONT, width=200, height=36
                         ).pack(side="left")

    def _backup_now(self):
        self.app.do_backup(self)

    def _save_recovery_key(self):
        self.app.do_save_recovery_key(self)

    def _restore_backup(self):
        self.app.do_restore_backup(self)
