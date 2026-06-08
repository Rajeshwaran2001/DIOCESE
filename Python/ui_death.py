"""
ui_death.py
===========
Death Extract section: a modern entry form + a searchable history view,
switched by a segmented control at the top.
"""

import customtkinter as ctk

import printing
from ui_common import (
    LabeledEntry, Card, PreviewWindow,
    show_success, show_error, show_warning, confirm,
    validate_record, TITLE_FONT, HEADING_FONT, BUTTON_FONT, SMALL_FONT,
    LABEL_FONT, CORNER, PAD,
)


# (field_key, label, required) grouped into cards.
_GROUPS = [
    ("Reference", [
        ("serial_no", "S.No.", False),
        ("number", "Number", True),
    ]),
    ("Deceased details", [
        ("name_of_dead_person", "Name of Dead Person", True),
        ("age", "Age", False),
        ("occupation", "Occupation", False),
        ("family_relation", "Family Relation", False),
        ("cause_of_death", "Cause of Death", False),
    ]),
    ("Dates & places", [
        ("date_of_death", "Date of Death", False),
        ("date_of_burial", "Date of Burial", False),
        ("place_of_death", "Place of Death", False),
        ("place_of_burial", "Place of Burial", False),
        ("person_who_buried_body", "Person Who Buried the Body", False),
    ]),
    ("Certificate paragraph & footer", [
        ("registrar_name", "Diocesan Registrar Name", False),
        ("pastorate_name", "Pastorate Name", False),
        ("witness_date", "Witness Date (day of ___)", False),
        ("prepared_by", "Prepared By", False),
        ("checked_by", "Checked By", False),
    ]),
]

_REQUIRED = [("number", "Number"), ("name_of_dead_person", "Name of Dead Person")]
_DATES = [("date_of_death", "Date of Death"), ("date_of_burial", "Date of Burial")]


class DeathSection(ctk.CTkFrame):
    form_type = "death"

    def __init__(self, parent, app):
        super().__init__(parent, fg_color="transparent")
        self.app = app
        self.fields = {}
        self.editing_id = None

        self._build_header()
        self._build_entry_view()
        self._build_history_view()
        self._show("Entry")

    # ------------------------------------------------------------------ #
    def _build_header(self):
        bar = ctk.CTkFrame(self, fg_color="transparent")
        bar.pack(fill="x", padx=PAD, pady=(PAD, 0))
        ctk.CTkLabel(bar, text="Death Extract", font=TITLE_FONT).pack(side="left")
        self.switch = ctk.CTkSegmentedButton(
            bar, values=["Entry", "History"], font=BUTTON_FONT,
            command=self._show,
        )
        self.switch.set("Entry")
        self.switch.pack(side="right")

    # ------------------------------------------------------------------ #
    def _build_entry_view(self):
        self.entry_view = ctk.CTkScrollableFrame(self, fg_color="transparent")
        for title, fields in _GROUPS:
            card = Card(self.entry_view, title=title)
            card.pack(fill="x", padx=PAD, pady=(PAD, 0))
            grid = ctk.CTkFrame(card, fg_color="transparent")
            grid.pack(fill="x", padx=PAD, pady=(0, PAD))
            for i, (key, label, required) in enumerate(fields):
                col = i % 2
                row = i // 2
                grid.grid_columnconfigure(col, weight=1)
                widget = LabeledEntry(grid, label, required=required)
                widget.grid(row=row, column=col, sticky="ew", padx=8, pady=8)
                self.fields[key] = widget

        actions = ctk.CTkFrame(self.entry_view, fg_color="transparent")
        actions.pack(fill="x", padx=PAD, pady=PAD)
        ctk.CTkButton(actions, text="Save", font=BUTTON_FONT, height=42,
                      corner_radius=CORNER, command=lambda: self._save(False)
                      ).pack(side="left", padx=(0, 8))
        ctk.CTkButton(actions, text="Save & Print", font=BUTTON_FONT, height=42,
                      corner_radius=CORNER, command=lambda: self._save(True)
                      ).pack(side="left", padx=8)
        ctk.CTkButton(actions, text="Preview", font=BUTTON_FONT, height=42,
                      corner_radius=CORNER, fg_color="transparent", border_width=1,
                      command=self._preview).pack(side="left", padx=8)
        ctk.CTkButton(actions, text="Clear", font=BUTTON_FONT, height=42,
                      corner_radius=CORNER, fg_color="transparent", border_width=1,
                      command=self._clear).pack(side="left", padx=8)
        self.edit_banner = ctk.CTkLabel(actions, text="", font=SMALL_FONT,
                                        text_color="#D97706")
        self.edit_banner.pack(side="right")

    # ------------------------------------------------------------------ #
    def _build_history_view(self):
        self.history_view = ctk.CTkFrame(self, fg_color="transparent")
        top = ctk.CTkFrame(self.history_view, fg_color="transparent")
        top.pack(fill="x", padx=PAD, pady=PAD)
        self.search = ctk.CTkEntry(top, placeholder_text="Search name / number / date...",
                                   font=LABEL_FONT, height=40, corner_radius=CORNER)
        self.search.pack(side="left", fill="x", expand=True)
        self.search.bind("<KeyRelease>", lambda e: self._refresh_history())
        ctk.CTkButton(top, text="Refresh", font=BUTTON_FONT, width=100, height=40,
                      corner_radius=CORNER, command=self._refresh_history
                      ).pack(side="left", padx=(8, 0))

        self.rows = ctk.CTkScrollableFrame(self.history_view, fg_color="transparent")
        self.rows.pack(fill="both", expand=True, padx=PAD, pady=(0, PAD))

    # ------------------------------------------------------------------ #
    def _show(self, which):
        self.entry_view.pack_forget()
        self.history_view.pack_forget()
        if which == "Entry":
            self.entry_view.pack(fill="both", expand=True)
        else:
            self._refresh_history()
            self.history_view.pack(fill="both", expand=True)
        self.switch.set(which)

    # ------------------------------------------------------------------ #
    def _collect(self):
        return {key: w.get() for key, w in self.fields.items()}

    def _load(self, record):
        for key, w in self.fields.items():
            w.set(record.get(key, ""))

    def _clear(self):
        for w in self.fields.values():
            w.clear()
        self.editing_id = None
        self.edit_banner.configure(text="")

    # ------------------------------------------------------------------ #
    def _save(self, print_after):
        values = self._collect()
        errors = validate_record(values, required=_REQUIRED, dates=_DATES)
        if errors:
            show_warning(self, "Please check the form", "\n".join(errors))
            return
        try:
            if self.editing_id is None:
                rec_id = self.app.db.insert_death(values)
            else:
                rec_id = self.editing_id
                self.app.db.update_death(rec_id, values)
        except Exception as exc:
            show_error(self, "Database error", str(exc))
            return

        if print_after:
            record = self.app.db.get_death(rec_id)
            self._print(record)

        show_success(self, "Saved", "Death extract saved successfully.")
        self._clear()

    def _preview(self):
        PreviewWindow(self, self.form_type, self._collect(), self.app.config)

    def _print(self, record):
        try:
            printing.print_record(self.form_type, record, self.app.config)
        except printing.PrinterError as exc:
            show_error(self, "Printing problem", str(exc))

    # ------------------------------------------------------------------ #
    def _refresh_history(self):
        for child in self.rows.winfo_children():
            child.destroy()
        try:
            records = self.app.db.search_death(self.search.get())
        except Exception as exc:
            show_error(self, "Database error", str(exc))
            return
        if not records:
            ctk.CTkLabel(self.rows, text="No records found.", font=LABEL_FONT,
                         text_color="gray").pack(pady=20)
            return
        for rec in records:
            self._row_card(rec)

    def _row_card(self, rec):
        card = ctk.CTkFrame(self.rows, corner_radius=CORNER)
        card.pack(fill="x", pady=6)
        info = ctk.CTkFrame(card, fg_color="transparent")
        info.pack(side="left", fill="x", expand=True, padx=PAD, pady=PAD)
        title = "{}  (No. {})".format(rec.get("name_of_dead_person") or "—",
                                      rec.get("number") or "—")
        ctk.CTkLabel(info, text=title, font=HEADING_FONT, anchor="w").pack(fill="x")
        sub = "S.No {}  ·  Died {}  ·  Buried {}".format(
            rec.get("serial_no") or "—", rec.get("date_of_death") or "—",
            rec.get("date_of_burial") or "—")
        ctk.CTkLabel(info, text=sub, font=SMALL_FONT, anchor="w",
                     text_color="gray").pack(fill="x")

        btns = ctk.CTkFrame(card, fg_color="transparent")
        btns.pack(side="right", padx=PAD, pady=PAD)
        for label, cmd, primary in [
            ("Edit", lambda: self._edit(rec["id"]), True),
            ("Reprint", lambda: self._print(self.app.db.get_death(rec["id"])), False),
            ("Delete", lambda: self._delete(rec["id"]), False),
        ]:
            ctk.CTkButton(
                btns, text=label, font=SMALL_FONT, width=84, height=34,
                corner_radius=CORNER,
                fg_color=None if primary else "transparent",
                border_width=0 if primary else 1,
                command=cmd,
            ).pack(side="left", padx=4)

    def _edit(self, rec_id):
        rec = self.app.db.get_death(rec_id)
        if not rec:
            return
        self._load(rec)
        self.editing_id = rec_id
        self.edit_banner.configure(text="Editing record #{}".format(rec_id))
        self._show("Entry")

    def _delete(self, rec_id):
        if not confirm(self, "Delete record",
                       "Delete this death extract permanently? This cannot be undone."):
            return
        try:
            self.app.db.delete_death(rec_id)
        except Exception as exc:
            show_error(self, "Database error", str(exc))
            return
        self._refresh_history()
