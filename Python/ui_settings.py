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

import customtkinter as ctk

import printing
from ui_common import (
    Card, show_success, show_error, show_info, confirm,
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

        self._build_data_card(view)
        self._build_appearance_card(view)
        self._build_printer_card(view)
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
                       "A new diocese.db will be created here if one doesn't "
                       "exist.".format(folder)):
            return
        try:
            self.app.set_data_path(folder)
        except Exception as exc:
            show_error(self, "Could not change folder", str(exc))
            return
        self.path_label.configure(text=self.cfg.data_path)
        show_success(self, "Database folder updated",
                     "Now using:\n{}".format(self.cfg.db_file))

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

        # Paper size
        prow = ctk.CTkFrame(body, fg_color="transparent")
        prow.pack(fill="x", pady=6)
        ctk.CTkLabel(prow, text="Paper size", font=LABEL_FONT, width=140,
                     anchor="w").pack(side="left")
        self.paper_menu = ctk.CTkOptionMenu(
            prow, values=["A4", "Letter"], font=BUTTON_FONT,
            command=self._set_paper)
        self.paper_menu.set(self.cfg.paper_size)
        self.paper_menu.pack(side="left")

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

    def _set_paper(self, value):
        self.cfg.paper_size = value

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
            return

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

    def _set_printer(self, value):
        self.cfg.printer_name = "" if value == "(system default)" else value

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

        for form_key, form_title in _FORMS:
            x_mm, y_mm = self.cfg.calibration(form_key)
            row = ctk.CTkFrame(body, corner_radius=CORNER)
            row.pack(fill="x", pady=6)
            ctk.CTkLabel(row, text=form_title, font=HEADING_FONT, width=180,
                         anchor="w").pack(side="left", padx=PAD, pady=PAD)

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
                             ).pack(side="left", padx=4, pady=PAD)

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
