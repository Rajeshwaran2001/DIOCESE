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
    LabeledEntry, DatePicker, Card, PreviewWindow, RecordTable,
    show_success, show_error, show_warning, confirm,
    validate_record, TITLE_FONT, HEADING_FONT, BUTTON_FONT, SMALL_FONT,
    LABEL_FONT, CORNER, PAD, FONT_FAMILY,
    primary_button, secondary_button,
)


# The entry form follows the order of the actual pre-printed register sheet:
# NUMBER, WHEN MARRIED, then the eight per-party rows, then SIGNATURE OF THE
# LICENSEE, WITNESSES and PLACE WHERE MARRIAGE WAS SOLEMNIZED, then the closing
# certificate paragraph + footer. ("S.No." is pre-printed, so it is omitted.)

# Shared single-value fields shown ABOVE the party columns.
_SHARED_TOP = [
    ("number", "Number", True),
]

# Per-party fields (one entry per party column), in sheet order.
_PARTY_FIELDS = [
    ("name_of_party", "Name of Parties"),
    ("surname", "Surname"),
    ("age", "Age"),
    ("condition", "Condition"),
    ("rank_or_profession", "Rank or Profession"),
    ("residence_at_marriage", "Residence at the Time of Marriage"),
    ("fathers_name", "Father's Name"),
    ("signature_contracting_party", "Signature of Contracting Parties"),
]

# Shared single-value fields shown BELOW the party columns, in sheet order.
_SHARED_BOTTOM = [
    ("signature_of_licensee", "Signature of the Licensee", False),
    ("witnesses", "Witnesses", False),
    ("place_solemnized", "Place Where Marriage Was Solemnized", False),
]

# Closing certificate paragraph + footer.
_FOOTER = [
    ("registrar_name", "Diocesan Registrar Name", False),
    ("witness_date", "Witness Date (day of ___ two thousand and ___)", False),
    ("prepared_by", "Prepared By", False),
    ("checked_by", "Checked By", False),
]

_REQUIRED = [("number", "Number")]
_DATES = [("when_married", "When Married")]


class MarriageSection(ctk.CTkFrame):
    form_type = "marriage"

    _COLUMNS = [
        ("Party A", "party_a_name", 3),
        ("Party B", "party_b_name", 3),
        ("No.", "number", 1),
        ("When Married", "when_married", 2),
    ]

    def __init__(self, parent, app):
        super().__init__(parent, fg_color="transparent")
        self.app = app
        self.shared = {}
        self.party_a = {}
        self.party_b = {}
        self.editing_id = None

        # The entry form holds dozens of widgets and costs ~1s to build, so it
        # is created lazily on the first Add/Edit instead of up front. This keeps
        # opening the section (the common case — viewing the list) instant.
        self.entry_view = None

        self._build_list_view()
        self._show("List")

    def _ensure_entry_view(self):
        if self.entry_view is None:
            self._build_entry_view()

    def _fetch_records(self, query):
        """Search. The DB query already returns party A/B display names, so we
        only normalise blanks to a dash here (no per-row get_marriage() call)."""
        records = self.app.db.search_marriage(query) or []
        for rec in records:
            rec["party_a_name"] = (rec.get("party_a_name") or "").strip() or "—"
            rec["party_b_name"] = (rec.get("party_b_name") or "").strip() or "—"
        return records

    def _build_list_view(self):
        self.list_view = RecordTable(
            self,
            title="Marriage Returns",
            add_label="＋  Add New",
            columns=self._COLUMNS,
            date_key="when_married",
            fetch=self._fetch_records,
            on_add=self._add_new,
            on_edit=self._edit,
            on_reprint=lambda i: self._print(self.app.db.get_marriage(i)),
            on_delete=self._delete,
            search_placeholder="Search party / number / date...",
        )

    def _build_entry_view(self):
        self.entry_view = ctk.CTkScrollableFrame(self, fg_color="transparent")
        head = ctk.CTkFrame(self.entry_view, fg_color="transparent")
        head.pack(fill="x", padx=PAD, pady=(PAD, 0))
        secondary_button(head, "←  Back to list", command=lambda: self._show("List"),
                         font=SMALL_FONT, width=140, height=36).pack(side="left")
        self.entry_title = ctk.CTkLabel(head, text="New Marriage Return", font=TITLE_FONT)
        self.entry_title.pack(side="left", padx=(12, 0))

        # A single card laid out like the real register sheet: a left LABEL
        # column and a right VALUE area. Per-party rows split the value area into
        # two columns (Party A / Party B).
        sheet = Card(self.entry_view, title="Copy of Marriage Returns")
        sheet.pack(fill="x", padx=PAD, pady=(PAD, 0))
        grid = ctk.CTkFrame(sheet, fg_color="transparent")
        grid.pack(fill="x", padx=PAD, pady=(0, PAD))
        grid.grid_columnconfigure(0, weight=0, minsize=260)   # label column
        grid.grid_columnconfigure(1, weight=1, uniform="val")  # Party A / value
        grid.grid_columnconfigure(2, weight=1, uniform="val")  # Party B
        row = [0]  # mutable row counter shared by the helpers below

        def label_cell(text):
            ctk.CTkLabel(grid, text=text, font=(FONT_FAMILY, 13, "bold"),
                         anchor="w", justify="left", wraplength=240).grid(
                row=row[0], column=0, sticky="w", padx=(4, 12), pady=8)

        def shared_row(key, label, required=False, date=False):
            label_cell(label + ("  *" if required else ""))
            cls = DatePicker if date else LabeledEntry
            w = cls(grid, "")          # label sits in the left cell, not the widget
            w.label.pack_forget()
            w.grid(row=row[0], column=1, columnspan=2, sticky="ew", pady=4)
            self.shared[key] = w
            row[0] += 1

        # --- NUMBER, WHEN MARRIED (above the party split) --------------- #
        for key, label, required in _SHARED_TOP:
            shared_row(key, label, required=required)
        shared_row("when_married", "When Married", date=True)

        # Party A / Party B column headers, just above the per-party rows.
        ctk.CTkLabel(grid, text="Party A", font=HEADING_FONT, anchor="w").grid(
            row=row[0], column=1, sticky="w", padx=(0, 8), pady=(10, 0))
        ctk.CTkLabel(grid, text="Party B", font=HEADING_FONT, anchor="w").grid(
            row=row[0], column=2, sticky="w", padx=(8, 0), pady=(10, 0))
        row[0] += 1

        # --- Per-party rows (Party A | Party B) ------------------------- #
        for key, label in _PARTY_FIELDS:
            label_cell(label)
            wa = LabeledEntry(grid, "")
            wa.label.pack_forget()
            wa.grid(row=row[0], column=1, sticky="ew", padx=(0, 8), pady=4)
            self.party_a[key] = wa
            wb = LabeledEntry(grid, "")
            wb.label.pack_forget()
            wb.grid(row=row[0], column=2, sticky="ew", padx=(8, 0), pady=4)
            self.party_b[key] = wb
            row[0] += 1

        # --- SIGNATURE OF LICENSEE, WITNESSES, PLACE SOLEMNIZED --------- #
        for key, label, required in _SHARED_BOTTOM:
            shared_row(key, label, required=required)

        # --- Closing certificate paragraph + footer --------------------- #
        footer_card = Card(self.entry_view, title="Certificate paragraph & footer")
        footer_card.pack(fill="x", padx=PAD, pady=(PAD, 0))
        fgrid = ctk.CTkFrame(footer_card, fg_color="transparent")
        fgrid.pack(fill="x", padx=PAD, pady=(0, PAD))
        for i, (key, label, required) in enumerate(_FOOTER):
            col, r = i % 2, i // 2
            fgrid.grid_columnconfigure(col, weight=1)
            w = LabeledEntry(fgrid, label, required=required)
            w.grid(row=r, column=col, sticky="ew", padx=8, pady=8)
            self.shared[key] = w

        actions = ctk.CTkFrame(self.entry_view, fg_color="transparent")
        actions.pack(fill="x", padx=PAD, pady=PAD)
        primary_button(actions, "Save", command=lambda: self._save(False)
                       ).pack(side="left", padx=(0, 8))
        primary_button(actions, "Save & Print", command=lambda: self._save(True)
                       ).pack(side="left", padx=8)
        secondary_button(actions, "Preview", command=self._preview
                         ).pack(side="left", padx=8)
        secondary_button(actions, "Clear", command=self._clear
                         ).pack(side="left", padx=8)

    def _show(self, which):
        if self.entry_view is not None:
            self.entry_view.pack_forget()
        self.list_view.pack_forget()
        if which == "Entry":
            self.entry_view.pack(fill="both", expand=True)
        else:
            self.list_view.refresh()
            self.list_view.pack(fill="both", expand=True)

    def _add_new(self):
        self._ensure_entry_view()
        self._clear()
        self.entry_title.configure(text="New Marriage Return")
        self._show("Entry")

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
        self._show("List")

    def _preview(self):
        PreviewWindow(self, self.form_type, self._record_for_print(), self.app.config)

    def _print(self, record):
        try:
            printing.print_record(self.form_type, record, self.app.config)
        except printing.PrinterError as exc:
            show_error(self, "Printing problem", str(exc))

    # ------------------------------------------------------------------ #
    def _edit(self, rec_id):
        rec = self.app.db.get_marriage(rec_id)
        if not rec:
            return
        self._ensure_entry_view()
        for k, w in self.shared.items():
            w.set(rec.get(k, ""))
        a = rec.get("parties", {}).get("A", {})
        b = rec.get("parties", {}).get("B", {})
        for k, w in self.party_a.items():
            w.set(a.get(k, ""))
        for k, w in self.party_b.items():
            w.set(b.get(k, ""))
        self.editing_id = rec_id
        self.entry_title.configure(text="Edit Marriage Return #{}".format(rec_id))
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
        self.list_view.refresh()
