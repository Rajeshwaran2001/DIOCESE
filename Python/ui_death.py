"""
ui_death.py
===========
Death Extract section: a modern entry form + a searchable history view,
switched by a segmented control at the top.
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


# The entry form follows the order of the actual pre-printed Death Extract sheet:
# NUMBER, DATE OF DEATH, DATE OF BURIAL, NAME OF DEAD PERSON, AGE, OCCUPATION,
# CAUSE OF DEATH, FAMILY RELATION, PLACE OF DEATH, PERSON WHO BURIED THE BODY,
# PLACE OF BURIAL, then the closing certificate paragraph + footer.
# ("S.No." is pre-printed, so it is omitted.)

# (field_key, label, required, is_date) in sheet order, shown as a label-left /
# value-right list to mirror the printed form.
_SHEET_FIELDS = [
    ("number",                 "Number",                    True,  False),
    ("date_of_death",          "Date of Death",             False, True),
    ("date_of_burial",         "Date of Burial",            False, True),
    ("name_of_dead_person",    "Name of Dead Person",       True,  False),
    ("age",                    "Age",                       False, False),
    ("occupation",             "Occupation",                False, False),
    ("cause_of_death",         "Cause of Death",            False, False),
    ("family_relation",        "Family Relation",           False, False),
    ("place_of_death",         "Place of Death",            False, False),
    ("person_who_buried_body", "Person Who Buried the Body", False, False),
    ("place_of_burial",        "Place of Burial",           False, False),
]

# Closing certificate paragraph + footer.
_FOOTER = [
    ("registrar_name", "Diocesan Registrar Name", False),
    ("witness_day", "Witness Date - Day", False),
    ("witness_month_year", "Witness Date - Month & Year", False),
]

_REQUIRED = [("number", "Number"), ("name_of_dead_person", "Name of Dead Person")]
_DATES = [("date_of_death", "Date of Death"), ("date_of_burial", "Date of Burial")]


class DeathSection(ctk.CTkFrame):
    form_type = "death"

    # Columns shown in the list/grid: (header, record_key, weight).
    _COLUMNS = [
        ("Name", "name_of_dead_person", 3),
        ("No.", "number", 1),
        ("Date of Death", "date_of_death", 2),
        ("Place of Death", "place_of_death", 2),
    ]

    def __init__(self, parent, app):
        super().__init__(parent, fg_color="transparent")
        self.app = app
        self.fields = {}
        self.editing_id = None

        # The entry form is large (~1s to build), so it is created lazily on the
        # first Add/Edit. Opening the section to view the list stays instant.
        self.entry_view = None
        self.current_view_name = "List"

        self._build_list_view()
        self._show("List")   # list/grid is the default screen

    def _ensure_entry_view(self):
        if self.entry_view is None:
            self._build_entry_view()

    # ------------------------------------------------------------------ #
    def _build_list_view(self):
        self.list_view = RecordTable(
            self,
            title="Death Extracts",
            add_label="＋  Add New",
            columns=self._COLUMNS,
            date_key="date_of_death",
            fetch=lambda q: self.app.db.search_death(q),
            on_add=self._add_new,
            on_edit=self._edit,
            on_reprint=lambda i: self._print(self.app.db.get_death(i)),
            on_delete=self._delete,
            search_placeholder="Search name / number / date...",
        )

    # ------------------------------------------------------------------ #
    def _build_entry_view(self):
        self.entry_view = ctk.CTkScrollableFrame(self, fg_color="transparent")
        # Entry header: a back link + title, so the user can return to the list.
        head = ctk.CTkFrame(self.entry_view, fg_color="transparent")
        head.pack(fill="x", padx=PAD, pady=(PAD, 0))
        secondary_button(head, "←  Back to list", command=self._cancel_entry,
                         font=SMALL_FONT, width=140, height=36).pack(side="left")
        self.entry_title = ctk.CTkLabel(head, text="New Death Extract", font=TITLE_FONT)
        self.entry_title.pack(side="left", padx=(12, 0))

        # A single card laid out like the real Death Extract sheet: a left LABEL
        # column and a right VALUE column, in the exact order of the printed form.
        sheet = Card(self.entry_view, title="Death Extract")
        sheet.pack(fill="x", padx=PAD, pady=(PAD, 0))
        grid = ctk.CTkFrame(sheet, fg_color="transparent")
        grid.pack(fill="x", padx=PAD, pady=(0, PAD))
        grid.grid_columnconfigure(0, weight=0, minsize=240)   # label column
        grid.grid_columnconfigure(1, weight=1)                # value column

        for r, (key, label, required, is_date) in enumerate(_SHEET_FIELDS):
            if key == "date_of_burial":
                continue

            if key == "date_of_death":
                ctk.CTkLabel(grid, text="Date of Death / Burial",
                             font=(FONT_FAMILY, 13, "bold"), anchor="w",
                             justify="left", wraplength=220).grid(
                    row=r, column=0, sticky="w", padx=(4, 12), pady=6)
                
                frame = ctk.CTkFrame(grid, fg_color="transparent")
                frame.grid(row=r, column=1, sticky="ew", pady=4)
                
                w_dod = DatePicker(frame, "")
                w_dod.label.pack_forget()
                w_dod.pack(side="left", fill="x", expand=True)
                self.fields["date_of_death"] = w_dod

                ctk.CTkLabel(frame, text="Burial", font=(FONT_FAMILY, 13, "bold"),
                             anchor="w").pack(side="left", padx=12)

                w_dob = DatePicker(frame, "")
                w_dob.label.pack_forget()
                w_dob.pack(side="left", fill="x", expand=True)
                self.fields["date_of_burial"] = w_dob
            else:
                ctk.CTkLabel(grid, text=label + ("  *" if required else ""),
                             font=(FONT_FAMILY, 13, "bold"), anchor="w",
                             justify="left", wraplength=220).grid(
                    row=r, column=0, sticky="w", padx=(4, 12), pady=6)
                cls = DatePicker if is_date else LabeledEntry
                widget = cls(grid, "")          # label sits in the left cell
                widget.label.pack_forget()
                widget.grid(row=r, column=1, sticky="ew", pady=4)
                self.fields[key] = widget

        # Closing certificate paragraph + footer.
        footer_card = Card(self.entry_view, title="Certificate paragraph & footer")
        footer_card.pack(fill="x", padx=PAD, pady=(PAD, 0))
        fgrid = ctk.CTkFrame(footer_card, fg_color="transparent")
        fgrid.pack(fill="x", padx=PAD, pady=(0, PAD))
        for i, (key, label, required) in enumerate(_FOOTER):
            col, r = i % 2, i // 2
            fgrid.grid_columnconfigure(col, weight=1)
            widget = LabeledEntry(fgrid, label, required=required)
            widget.grid(row=r, column=col, sticky="ew", padx=8, pady=8)
            self.fields[key] = widget

        actions = ctk.CTkFrame(self.entry_view, fg_color="transparent")
        actions.pack(fill="x", padx=PAD, pady=PAD)
        primary_button(actions, "Save", command=lambda: self._save(False)
                       ).pack(side="left", padx=(0, 8))
        primary_button(actions, "Save & Print", command=lambda: self._save(True)
                       ).pack(side="left", padx=8)
        secondary_button(actions, "Preview", command=self._preview
                         ).pack(side="left", padx=8)
        secondary_button(actions, "Cancel", command=self._cancel_entry
                         ).pack(side="left", padx=8)

    def _cancel_entry(self):
        if confirm(self, "Cancel", "Discard any unsaved changes and return to the list?"):
            self._clear()
            self._show("List")

    def can_navigate_away(self):
        if self.current_view_name == "Entry":
            show_warning(self, "Unsaved changes", "Please Save or Cancel before leaving this screen.")
            return False
        return True

    # ------------------------------------------------------------------ #
    def _show(self, which):
        self.current_view_name = which
        if self.entry_view is not None:
            self.entry_view.pack_forget()
        self.list_view.pack_forget()
        if which == "Entry":
            self.entry_view.pack(fill="both", expand=True)
        else:
            self.list_view.refresh()
            self.list_view.pack(fill="both", expand=True)

    def _add_new(self):
        """Open a blank entry form for a new record."""
        self._ensure_entry_view()
        self._clear()
        self.entry_title.configure(text="New Death Extract")
        self._show("Entry")

    # ------------------------------------------------------------------ #
    def _collect(self):
        data = {key: w.get() for key, w in self.fields.items()}
        data["pastorate_name"] = data.get("place_of_burial", "")
        return data

    def _load(self, record):
        for key, w in self.fields.items():
            w.set(record.get(key, ""))

    def _clear(self):
        for w in self.fields.values():
            w.clear()
        self.editing_id = None

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
        self._show("List")   # back to the grid after saving

    def _preview(self):
        PreviewWindow(self, self.form_type, self._collect(), self.app.config)

    def _print(self, record):
        from ui_common import ask_copies
        copies = ask_copies(self)
        if copies <= 0:
            return
        try:
            printing.print_record(self.form_type, record, self.app.config, copies=copies)
        except printing.PrinterError as exc:
            show_error(self, "Printing problem", str(exc))

    # ------------------------------------------------------------------ #
    def _edit(self, rec_id):
        rec = self.app.db.get_death(rec_id)
        if not rec:
            return
        self._ensure_entry_view()
        self._load(rec)
        self.editing_id = rec_id
        self.entry_title.configure(text="Edit Death Extract #{}".format(rec_id))
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
        self.list_view.refresh()
