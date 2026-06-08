"""
ui_marriage.py
==============
Marriage Returns section. The entry form shows the two contracting parties in
side-by-side columns (Party A / Party B), plus the shared marriage fields.
Includes the searchable history view with edit / reprint / delete.
"""

import customtkinter as ctk

import printing
from ui_common import (
    LabeledEntry, Card, PreviewWindow,
    show_success, show_error, show_warning, confirm,
    validate_record, TITLE_FONT, HEADING_FONT, BUTTON_FONT, SMALL_FONT,
    LABEL_FONT, CORNER, PAD,
)


# Shared (single value) marriage fields, grouped into cards.
_SHARED_GROUPS = [
    ("Reference", [
        ("serial_no", "S.No.", False),
        ("number", "Number", True),
        ("when_married", "When Married", False),
    ]),
    ("Solemnisation", [
        ("place_solemnized", "Place Where Marriage Was Solemnized", False),
        ("signature_of_licensee", "Signature of the Licensee", False),
        ("witnesses", "Witnesses", False),
    ]),
    ("Certificate paragraph & footer", [
        ("registrar_name", "Diocesan Registrar Name", False),
        ("witness_date", "Witness Date (day of ___ two thousand and ___)", False),
        ("prepared_by", "Prepared By", False),
        ("checked_by", "Checked By", False),
    ]),
]

# Per-party fields (one entry per party column).
_PARTY_FIELDS = [
    ("name_of_party", "Name of Party"),
    ("surname", "Surname"),
    ("age", "Age"),
    ("condition", "Condition"),
    ("rank_or_profession", "Rank or Profession"),
    ("residence_at_marriage", "Residence at the Time of Marriage"),
    ("fathers_name", "Father's Name"),
    ("signature_contracting_party", "Signature of Contracting Party"),
]

_REQUIRED = [("number", "Number")]
_DATES = []


class MarriageSection(ctk.CTkFrame):
    form_type = "marriage"

    def __init__(self, parent, app):
        super().__init__(parent, fg_color="transparent")
        self.app = app
        self.shared = {}
        self.party_a = {}
        self.party_b = {}
        self.editing_id = None

        self._build_header()
        self._build_entry_view()
        self._build_history_view()
        self._show("Entry")

    def _build_header(self):
        bar = ctk.CTkFrame(self, fg_color="transparent")
        bar.pack(fill="x", padx=PAD, pady=(PAD, 0))
        ctk.CTkLabel(bar, text="Marriage Returns", font=TITLE_FONT).pack(side="left")
        self.switch = ctk.CTkSegmentedButton(
            bar, values=["Entry", "History"], font=BUTTON_FONT, command=self._show)
        self.switch.set("Entry")
        self.switch.pack(side="right")

    def _build_entry_view(self):
        self.entry_view = ctk.CTkScrollableFrame(self, fg_color="transparent")

        for title, fields in _SHARED_GROUPS:
            card = Card(self.entry_view, title=title)
            card.pack(fill="x", padx=PAD, pady=(PAD, 0))
            grid = ctk.CTkFrame(card, fg_color="transparent")
            grid.pack(fill="x", padx=PAD, pady=(0, PAD))
            for i, (key, label, required) in enumerate(fields):
                col, row = i % 2, i // 2
                grid.grid_columnconfigure(col, weight=1)
                w = LabeledEntry(grid, label, required=required)
                w.grid(row=row, column=col, sticky="ew", padx=8, pady=8)
                self.shared[key] = w

        # Two-party card with side-by-side columns.
        party_card = Card(self.entry_view, title="Contracting Parties")
        party_card.pack(fill="x", padx=PAD, pady=(PAD, 0))
        cols = ctk.CTkFrame(party_card, fg_color="transparent")
        cols.pack(fill="x", padx=PAD, pady=(0, PAD))
        cols.grid_columnconfigure(0, weight=1)
        cols.grid_columnconfigure(1, weight=1)

        col_a = ctk.CTkFrame(cols, fg_color="transparent")
        col_a.grid(row=0, column=0, sticky="new", padx=(0, 8))
        col_b = ctk.CTkFrame(cols, fg_color="transparent")
        col_b.grid(row=0, column=1, sticky="new", padx=(8, 0))
        ctk.CTkLabel(col_a, text="Party A", font=HEADING_FONT,
                     anchor="w").pack(fill="x", pady=(0, 4))
        ctk.CTkLabel(col_b, text="Party B", font=HEADING_FONT,
                     anchor="w").pack(fill="x", pady=(0, 4))

        for key, label in _PARTY_FIELDS:
            wa = LabeledEntry(col_a, label)
            wa.pack(fill="x", pady=6)
            self.party_a[key] = wa
            wb = LabeledEntry(col_b, label)
            wb.pack(fill="x", pady=6)
            self.party_b[key] = wb

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

    def _build_history_view(self):
        self.history_view = ctk.CTkFrame(self, fg_color="transparent")
        top = ctk.CTkFrame(self.history_view, fg_color="transparent")
        top.pack(fill="x", padx=PAD, pady=PAD)
        self.search = ctk.CTkEntry(top, placeholder_text="Search party / number / date...",
                                   font=LABEL_FONT, height=40, corner_radius=CORNER)
        self.search.pack(side="left", fill="x", expand=True)
        self.search.bind("<KeyRelease>", lambda e: self._refresh_history())
        ctk.CTkButton(top, text="Refresh", font=BUTTON_FONT, width=100, height=40,
                      corner_radius=CORNER, command=self._refresh_history
                      ).pack(side="left", padx=(8, 0))
        self.rows = ctk.CTkScrollableFrame(self.history_view, fg_color="transparent")
        self.rows.pack(fill="both", expand=True, padx=PAD, pady=(0, PAD))

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
    def _collect_shared(self):
        return {k: w.get() for k, w in self.shared.items()}

    def _collect_party(self, widgets):
        return {k: w.get() for k, w in widgets.items()}

    def _record_for_print(self):
        """Build a dict shaped like a DB row (with a 'parties' sub-dict)."""
        data = self._collect_shared()
        data["parties"] = {
            "A": self._collect_party(self.party_a),
            "B": self._collect_party(self.party_b),
        }
        return data

    def _clear(self):
        for w in self.shared.values():
            w.clear()
        for w in self.party_a.values():
            w.clear()
        for w in self.party_b.values():
            w.clear()
        self.editing_id = None
        self.edit_banner.configure(text="")

    def _save(self, print_after):
        shared = self._collect_shared()
        errors = validate_record(shared, required=_REQUIRED, dates=_DATES)
        if errors:
            show_warning(self, "Please check the form", "\n".join(errors))
            return
        party_a = self._collect_party(self.party_a)
        party_b = self._collect_party(self.party_b)
        try:
            if self.editing_id is None:
                rec_id = self.app.db.insert_marriage(shared, party_a, party_b)
            else:
                rec_id = self.editing_id
                self.app.db.update_marriage(rec_id, shared, party_a, party_b)
        except Exception as exc:
            show_error(self, "Database error", str(exc))
            return

        if print_after:
            self._print(self.app.db.get_marriage(rec_id))

        show_success(self, "Saved", "Marriage return saved successfully.")
        self._clear()

    def _preview(self):
        PreviewWindow(self, self.form_type, self._record_for_print(), self.app.config)

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
            records = self.app.db.search_marriage(self.search.get())
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
        full = self.app.db.get_marriage(rec["id"])
        a = full.get("parties", {}).get("A", {})
        b = full.get("parties", {}).get("B", {})
        card = ctk.CTkFrame(self.rows, corner_radius=CORNER)
        card.pack(fill="x", pady=6)
        info = ctk.CTkFrame(card, fg_color="transparent")
        info.pack(side="left", fill="x", expand=True, padx=PAD, pady=PAD)
        couple = "{} & {}".format(
            (a.get("name_of_party") or "—"), (b.get("name_of_party") or "—"))
        ctk.CTkLabel(info, text="{}  (No. {})".format(couple, rec.get("number") or "—"),
                     font=HEADING_FONT, anchor="w").pack(fill="x")
        ctk.CTkLabel(info, text="S.No {}  ·  Married {}".format(
            rec.get("serial_no") or "—", rec.get("when_married") or "—"),
            font=SMALL_FONT, anchor="w", text_color="gray").pack(fill="x")

        btns = ctk.CTkFrame(card, fg_color="transparent")
        btns.pack(side="right", padx=PAD, pady=PAD)
        for label, cmd, primary in [
            ("Edit", lambda: self._edit(rec["id"]), True),
            ("Reprint", lambda: self._print(self.app.db.get_marriage(rec["id"])), False),
            ("Delete", lambda: self._delete(rec["id"]), False),
        ]:
            ctk.CTkButton(btns, text=label, font=SMALL_FONT, width=84, height=34,
                          corner_radius=CORNER,
                          fg_color=None if primary else "transparent",
                          border_width=0 if primary else 1,
                          command=cmd).pack(side="left", padx=4)

    def _edit(self, rec_id):
        rec = self.app.db.get_marriage(rec_id)
        if not rec:
            return
        for k, w in self.shared.items():
            w.set(rec.get(k, ""))
        a = rec.get("parties", {}).get("A", {})
        b = rec.get("parties", {}).get("B", {})
        for k, w in self.party_a.items():
            w.set(a.get(k, ""))
        for k, w in self.party_b.items():
            w.set(b.get(k, ""))
        self.editing_id = rec_id
        self.edit_banner.configure(text="Editing record #{}".format(rec_id))
        self._show("Entry")

    def _delete(self, rec_id):
        if not confirm(self, "Delete record",
                       "Delete this marriage return permanently? This cannot be undone."):
            return
        try:
            self.app.db.delete_marriage(rec_id)
        except Exception as exc:
            show_error(self, "Database error", str(exc))
            return
        self._refresh_history()
