"""
ui_common.py
============
Shared CustomTkinter widgets, modern dialogs, validation and the print preview
window. Keeping these here avoids repeating the same code in every form file
and keeps the look consistent.
"""

import re
import tkinter as tk

import customtkinter as ctk

import layouts
import printing


# --------------------------------------------------------------------------- #
# Typography / spacing constants used across the app.
# --------------------------------------------------------------------------- #
FONT_FAMILY = "Segoe UI"          # falls back gracefully if unavailable
TITLE_FONT = (FONT_FAMILY, 22, "bold")
HEADING_FONT = (FONT_FAMILY, 16, "bold")
LABEL_FONT = (FONT_FAMILY, 13)
ENTRY_FONT = (FONT_FAMILY, 14)
BUTTON_FONT = (FONT_FAMILY, 14, "bold")
SMALL_FONT = (FONT_FAMILY, 12)

CORNER = 12        # rounded corner radius for cards/buttons
PAD = 12

# --------------------------------------------------------------------------- #
# Shared button colors. CTk's default button text is near-white (meant for a
# coloured fill), so a transparent "ghost" button renders invisible text in
# light mode. These tuples are (light, dark) so both appearance modes stay
# readable. Use primary_button() / secondary_button() instead of raw CTkButton.
# --------------------------------------------------------------------------- #
PRIMARY_COLOR = ("#2563EB", "#3B82F6")
PRIMARY_HOVER = ("#1D4ED8", "#2563EB")
GHOST_TEXT = ("#1E293B", "#E2E8F0")   # readable on a transparent/card surface
GHOST_BORDER = ("#CBD5E1", "#475569")
GHOST_HOVER = ("#E2E8F0", "#334155")


def primary_button(parent, text, command=None, **kw):
    """A filled accent button with guaranteed-white, centred text."""
    opts = dict(text=text, command=command, font=BUTTON_FONT, height=42,
                corner_radius=CORNER, fg_color=PRIMARY_COLOR,
                hover_color=PRIMARY_HOVER, text_color="#FFFFFF")
    opts.update(kw)
    return ctk.CTkButton(parent, **opts)


def secondary_button(parent, text, command=None, **kw):
    """An outlined ("ghost") button with readable text in light AND dark mode."""
    opts = dict(text=text, command=command, font=BUTTON_FONT, height=42,
                corner_radius=CORNER, fg_color="transparent", border_width=1,
                border_color=GHOST_BORDER, text_color=GHOST_TEXT,
                hover_color=GHOST_HOVER)
    opts.update(kw)
    return ctk.CTkButton(parent, **opts)


# --------------------------------------------------------------------------- #
# Validation helpers
# --------------------------------------------------------------------------- #
_DATE_RE = re.compile(r"^\s*\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\s*$")


def is_valid_date(text):
    """Accept blank, or dd/mm/yyyy / dd-mm-yyyy (clerical free-form friendly)."""
    if not text or not text.strip():
        return True  # dates are optional unless marked required
    return bool(_DATE_RE.match(text))


def validate_record(values, required=(), dates=()):
    """
    Return a list of human-readable error strings (empty list == valid).
    ``required`` and ``dates`` are iterables of (field_key, label) tuples.
    """
    errors = []
    for key, label in required:
        if not str(values.get(key, "")).strip():
            errors.append("• \"{}\" is required.".format(label))
    for key, label in dates:
        if not is_valid_date(values.get(key, "")):
            errors.append(
                "• \"{}\" must be a date like 31/12/2025.".format(label)
            )
    return errors


# --------------------------------------------------------------------------- #
# Modern modal dialogs (never a raw traceback / Tk ugly popup)
# --------------------------------------------------------------------------- #
class _ModalDialog(ctk.CTkToplevel):
    def __init__(self, parent, title, message, kind="info", buttons=("OK",)):
        super().__init__(parent)
        self.result = None
        self.title(title)
        self.resizable(False, False)
        self.configure(padx=0, pady=0)

        accent = {
            "info": ("#2563EB", "ℹ"),
            "success": ("#16A34A", "✔"),
            "warning": ("#D97706", "⚠"),
            "error": ("#DC2626", "✖"),
            "confirm": ("#2563EB", "?"),
        }.get(kind, ("#2563EB", "ℹ"))

        container = ctk.CTkFrame(self, corner_radius=0)
        container.pack(fill="both", expand=True)

        header = ctk.CTkFrame(container, fg_color=accent[0], corner_radius=0, height=8)
        header.pack(fill="x")

        body = ctk.CTkFrame(container, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=24, pady=20)

        icon = ctk.CTkLabel(
            body, text=accent[1], font=(FONT_FAMILY, 32, "bold"),
            text_color=accent[0], width=48,
        )
        icon.grid(row=0, column=0, rowspan=2, sticky="n", padx=(0, 16))

        ctk.CTkLabel(
            body, text=title, font=HEADING_FONT, anchor="w", justify="left"
        ).grid(row=0, column=1, sticky="w")
        ctk.CTkLabel(
            body, text=message, font=LABEL_FONT, anchor="w", justify="left",
            wraplength=380,
        ).grid(row=1, column=1, sticky="w", pady=(6, 0))

        btn_row = ctk.CTkFrame(container, fg_color="transparent")
        btn_row.pack(fill="x", padx=24, pady=(0, 18))
        btn_row.grid_columnconfigure(0, weight=1)

        for i, label in enumerate(buttons):
            is_primary = (i == len(buttons) - 1)
            btn = ctk.CTkButton(
                btn_row, text=label, font=BUTTON_FONT, corner_radius=CORNER,
                width=110, height=36,
                fg_color=accent[0] if is_primary else "transparent",
                border_width=0 if is_primary else 1,
                border_color=GHOST_BORDER,
                text_color=("#FFFFFF" if is_primary else GHOST_TEXT),
                hover_color=(accent[0] if is_primary else GHOST_HOVER),
                command=lambda l=label: self._choose(l),
            )
            btn.grid(row=0, column=i + 1, padx=6)

        self._center(parent)
        self.transient(parent)
        self.grab_set()
        self.protocol("WM_DELETE_WINDOW", lambda: self._choose(buttons[0]))
        self.wait_window()

    def _choose(self, label):
        self.result = label
        self.grab_release()
        self.destroy()

    def _center(self, parent):
        self.update_idletasks()
        try:
            px, py = parent.winfo_rootx(), parent.winfo_rooty()
            pw, ph = parent.winfo_width(), parent.winfo_height()
            w, h = self.winfo_width(), self.winfo_height()
            x = px + (pw - w) // 2
            y = py + (ph - h) // 2
            self.geometry("+{}+{}".format(max(x, 0), max(y, 0)))
        except Exception:
            pass


def show_info(parent, title, message):
    _ModalDialog(parent, title, message, kind="info")


def show_success(parent, title, message):
    _ModalDialog(parent, title, message, kind="success")


def show_warning(parent, title, message):
    _ModalDialog(parent, title, message, kind="warning")


def show_error(parent, title, message):
    _ModalDialog(parent, title, message, kind="error")


def confirm(parent, title, message, ok="Yes", cancel="Cancel"):
    """Return True if the user picked the primary (ok) button."""
    dlg = _ModalDialog(parent, title, message, kind="confirm", buttons=(cancel, ok))
    return dlg.result == ok


# --------------------------------------------------------------------------- #
# Reusable form widgets
# --------------------------------------------------------------------------- #
class LabeledEntry(ctk.CTkFrame):
    """A label stacked above a rounded entry. ``get()`` / ``set()`` helpers."""

    def __init__(self, parent, label, required=False, width=240, **kw):
        super().__init__(parent, fg_color="transparent")
        text = label + ("  *" if required else "")
        self.label = ctk.CTkLabel(
            self, text=text, font=LABEL_FONT, anchor="w",
            text_color=("#DC2626" if required else None) if False else None,
        )
        self.label.pack(fill="x")
        self.entry = ctk.CTkEntry(
            self, font=ENTRY_FONT, corner_radius=CORNER, height=38, width=width
        )
        self.entry.pack(fill="x", pady=(3, 0))

    def get(self):
        return self.entry.get()

    def set(self, value):
        self.entry.delete(0, "end")
        if value:
            self.entry.insert(0, str(value))

    def clear(self):
        self.entry.delete(0, "end")


class DatePicker(ctk.CTkFrame):
    """A label above an entry + 📅 button that opens a small popup calendar.

    Self-contained (no external dependency such as tkcalendar) so the packaged
    Python 3.8 / Windows 7 build keeps working. Stores/returns the date as the
    same free-form ``dd/mm/yyyy`` string the rest of the app already validates,
    so it is a drop-in replacement for a :class:`LabeledEntry`.

    Time pickers are intentionally NOT shown — marriage returns record a date
    only. The hooks for an optional time field are kept commented below so they
    can be re-enabled later without redesigning the widget.
    """

    _MONTHS = ["January", "February", "March", "April", "May", "June",
               "July", "August", "September", "October", "November", "December"]

    def __init__(self, parent, label, required=False, width=240, **kw):
        super().__init__(parent, fg_color="transparent")
        text = label + ("  *" if required else "")
        self.label = ctk.CTkLabel(self, text=text, font=LABEL_FONT, anchor="w")
        self.label.pack(fill="x")

        row = ctk.CTkFrame(self, fg_color="transparent")
        row.pack(fill="x", pady=(3, 0))
        self.entry = ctk.CTkEntry(
            row, font=ENTRY_FONT, corner_radius=CORNER, height=38,
            placeholder_text="dd/mm/yyyy",
        )
        self.entry.pack(side="left", fill="x", expand=True)
        ctk.CTkButton(
            row, text="📅", width=42, height=38, corner_radius=CORNER,
            font=BUTTON_FONT, fg_color=PRIMARY_COLOR, hover_color=PRIMARY_HOVER,
            text_color="#FFFFFF", command=self._open_calendar,
        ).pack(side="left", padx=(6, 0))

        # --- Optional time picker (disabled by default) ----------------- #
        # To record a time alongside the date, uncomment the block below and
        # combine self.entry + self.time_entry in get()/set().
        # self.time_entry = ctk.CTkEntry(
        #     row, font=ENTRY_FONT, corner_radius=CORNER, height=38, width=90,
        #     placeholder_text="hh:mm",
        # )
        # self.time_entry.pack(side="left", padx=(6, 0))

        self._popup = None

    # ------------------------------------------------------------------ #
    def get(self):
        return self.entry.get()
        # With a time picker enabled:
        # date, time = self.entry.get().strip(), self.time_entry.get().strip()
        # return (date + " " + time).strip() if time else date

    def set(self, value):
        self.entry.delete(0, "end")
        if value:
            self.entry.insert(0, str(value))

    def clear(self):
        self.entry.delete(0, "end")
        # self.time_entry.delete(0, "end")

    # ------------------------------------------------------------------ #
    def _parse_current(self):
        """Return (year, month, day) from the entry, defaulting to today."""
        import datetime
        m = re.search(r"(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})", self.entry.get())
        if m:
            d, mo, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
            if y < 100:
                y += 2000
            try:
                datetime.date(y, mo, d)
                return y, mo, d
            except ValueError:
                pass
        t = datetime.date.today()
        return t.year, t.month, t.day

    def _open_calendar(self):
        if self._popup is not None and self._popup.winfo_exists():
            self._popup.focus()
            return
        year, month, _day = self._parse_current()
        self._popup = _CalendarPopup(self, year, month, self._on_pick)

    def _on_pick(self, day, month, year):
        self.set("{:02d}/{:02d}/{:04d}".format(day, month, year))


class _CalendarPopup(ctk.CTkToplevel):
    """Small month-grid calendar used by :class:`DatePicker`."""

    def __init__(self, picker, year, month, on_pick):
        super().__init__(picker)
        self._on_pick = on_pick
        self.year = year
        self.month = month
        self.title("Pick a date")
        self.resizable(False, False)
        self.attributes("-topmost", True)

        nav = ctk.CTkFrame(self, fg_color="transparent")
        nav.pack(fill="x", padx=10, pady=(10, 4))
        secondary_button(nav, "‹", command=lambda: self._shift(-1),
                         font=BUTTON_FONT, width=40, height=34).pack(side="left")
        self.title_label = ctk.CTkLabel(nav, text="", font=HEADING_FONT)
        self.title_label.pack(side="left", expand=True)
        secondary_button(nav, "›", command=lambda: self._shift(1),
                         font=BUTTON_FONT, width=40, height=34).pack(side="right")

        self.grid_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.grid_frame.pack(padx=10, pady=(0, 10))

        self._render()
        self._center(picker)
        self.transient(picker.winfo_toplevel())
        self.grab_set()

    def _shift(self, delta):
        self.month += delta
        if self.month < 1:
            self.month, self.year = 12, self.year - 1
        elif self.month > 12:
            self.month, self.year = 1, self.year + 1
        self._render()

    def _render(self):
        import calendar
        for child in self.grid_frame.winfo_children():
            child.destroy()
        self.title_label.configure(
            text="{} {}".format(DatePicker._MONTHS[self.month - 1], self.year))

        for c, name in enumerate(["Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"]):
            ctk.CTkLabel(self.grid_frame, text=name, font=(FONT_FAMILY, 11, "bold"),
                         width=38, text_color=GRID_TEXT_DIM).grid(row=0, column=c, padx=1, pady=1)

        for r, week in enumerate(calendar.Calendar().monthdayscalendar(self.year, self.month), start=1):
            for c, day in enumerate(week):
                if day == 0:
                    continue
                ctk.CTkButton(
                    self.grid_frame, text=str(day), width=38, height=32,
                    corner_radius=8, font=SMALL_FONT,
                    fg_color="transparent", text_color=GHOST_TEXT,
                    hover_color=GHOST_HOVER,
                    command=lambda d=day: self._pick(d),
                ).grid(row=r, column=c, padx=1, pady=1)

    def _pick(self, day):
        self._on_pick(day, self.month, self.year)
        self.grab_release()
        self.destroy()

    def _center(self, parent):
        self.update_idletasks()
        try:
            px, py = parent.winfo_rootx(), parent.winfo_rooty()
            self.geometry("+{}+{}".format(px, py + 44))
        except Exception:
            pass


class Card(ctk.CTkFrame):
    """A rounded container with an optional heading, used to group fields."""

    def __init__(self, parent, title=None, **kw):
        super().__init__(parent, corner_radius=CORNER, **kw)
        if title:
            ctk.CTkLabel(
                self, text=title, font=HEADING_FONT, anchor="w"
            ).pack(fill="x", padx=PAD + 4, pady=(PAD, 2))


# --------------------------------------------------------------------------- #
# RecordTable — the list/grid screen each record section opens to. Shows records
# in real columns with a search box, year + sort filters and an optional date
# range, plus a prominent "+ Add New" button. Text search hits the section's DB
# query; year / date-range / sort are applied client-side on the returned rows.
# --------------------------------------------------------------------------- #
HEADER_BG = ("#E2E8F0", "#1E293B")
ROW_BG = ("#FFFFFF", "#0F172A")
ROW_ALT_BG = ("#F8FAFC", "#131C2E")
GRID_TEXT_DIM = ("#64748B", "#94A3B8")


class RecordTable(ctk.CTkFrame):
    """A configurable, filterable data grid for a record section.

    columns:   list of (header, record_key, weight) — what to show per row.
    date_key:  record key holding the row's main date (for year / range filters);
               dates are free-form dd/mm/yyyy or dd-mm-yyyy, parsed leniently.
    fetch:     fetch(query_str) -> list[dict] (the section's DB search method).
    on_add / on_edit / on_reprint / on_delete: callbacks (on_edit/reprint/delete
               receive the record id).
    """

    def __init__(self, parent, *, title, add_label, columns, date_key,
                 fetch, on_add, on_edit, on_reprint, on_delete,
                 search_placeholder="Search...", **kw):
        super().__init__(parent, fg_color="transparent", **kw)
        self.columns = columns
        self.date_key = date_key
        self._fetch = fetch
        self._on_edit = on_edit
        self._on_reprint = on_reprint
        self._on_delete = on_delete

        # --- Header: title + Add button ---------------------------------- #
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=PAD, pady=(PAD, 0))
        ctk.CTkLabel(header, text=title, font=TITLE_FONT).pack(side="left")
        primary_button(header, add_label, command=on_add, height=40,
                       width=140).pack(side="right")

        # --- Filter bar -------------------------------------------------- #
        bar = ctk.CTkFrame(self, fg_color="transparent")
        bar.pack(fill="x", padx=PAD, pady=(PAD, 0))

        self.search = ctk.CTkEntry(bar, placeholder_text=search_placeholder,
                                   font=LABEL_FONT, height=38, corner_radius=CORNER)
        self.search.pack(side="left", fill="x", expand=True)
        # Debounce typing: rebuild only after the user pauses, so each keystroke
        # doesn't trigger a full DB query + row re-render (which felt laggy).
        self.search.bind("<KeyRelease>", lambda e: self._debounce(self.refresh))

        self.year_var = ctk.StringVar(value="All years")
        self.year_menu = ctk.CTkOptionMenu(
            bar, variable=self.year_var, values=["All years"], width=120,
            height=38, font=LABEL_FONT, corner_radius=CORNER,
            command=lambda _=None: self._apply_filters())
        self.year_menu.pack(side="left", padx=(8, 0))

        self.sort_var = ctk.StringVar(value="Newest first")
        ctk.CTkOptionMenu(
            bar, variable=self.sort_var,
            values=["Newest first", "Oldest first", "Name (A–Z)"],
            width=150, height=38, font=LABEL_FONT, corner_radius=CORNER,
            command=lambda _=None: self._apply_filters()).pack(side="left", padx=(8, 0))

        secondary_button(bar, "Clear", command=self._clear_filters,
                         font=SMALL_FONT, width=80, height=38).pack(side="left", padx=(8, 0))

        # --- Optional date range ----------------------------------------- #
        range_row = ctk.CTkFrame(self, fg_color="transparent")
        range_row.pack(fill="x", padx=PAD, pady=(8, 0))
        ctk.CTkLabel(range_row, text="From", font=SMALL_FONT,
                     text_color=GRID_TEXT_DIM).pack(side="left")
        self.from_entry = ctk.CTkEntry(range_row, placeholder_text="dd/mm/yyyy",
                                       font=SMALL_FONT, width=120, height=34)
        self.from_entry.pack(side="left", padx=(4, 12))
        self.from_entry.bind("<KeyRelease>", lambda e: self._debounce(self._apply_filters))
        ctk.CTkLabel(range_row, text="To", font=SMALL_FONT,
                     text_color=GRID_TEXT_DIM).pack(side="left")
        self.to_entry = ctk.CTkEntry(range_row, placeholder_text="dd/mm/yyyy",
                                     font=SMALL_FONT, width=120, height=34)
        self.to_entry.pack(side="left", padx=(4, 0))
        self.to_entry.bind("<KeyRelease>", lambda e: self._debounce(self._apply_filters))
        self.count_label = ctk.CTkLabel(range_row, text="", font=SMALL_FONT,
                                        text_color=GRID_TEXT_DIM)
        self.count_label.pack(side="right")

        # --- Column headers ---------------------------------------------- #
        head = ctk.CTkFrame(self, fg_color=HEADER_BG, corner_radius=CORNER)
        head.pack(fill="x", padx=PAD, pady=(PAD, 0))
        for c, (label, _key, weight) in enumerate(self.columns):
            head.grid_columnconfigure(c, weight=weight, uniform="col")
            ctk.CTkLabel(head, text=label, font=(FONT_FAMILY, 12, "bold"),
                         anchor="w").grid(row=0, column=c, sticky="ew",
                                          padx=PAD, pady=8)
        # actions column header (no weight; fixed)
        actions_col = len(self.columns)
        head.grid_columnconfigure(actions_col, weight=0)
        ctk.CTkLabel(head, text="Actions", font=(FONT_FAMILY, 12, "bold"),
                     anchor="e").grid(row=0, column=actions_col, sticky="e",
                                      padx=PAD, pady=8)

        # --- Scrollable rows --------------------------------------------- #
        self.rows = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.rows.pack(fill="both", expand=True, padx=PAD, pady=(6, PAD))

        self._all = []  # last fetched (unfiltered-by-client) records
        self._debounce_id = None   # pending after() id for debounced rebuilds
        self._row_pool = []        # reusable row widgets (avoid rebuild churn)

    # ------------------------------------------------------------------ #
    def _debounce(self, fn, delay_ms=220):
        """Coalesce rapid events (typing) into a single deferred call to ``fn``."""
        if self._debounce_id is not None:
            try:
                self.after_cancel(self._debounce_id)
            except Exception:
                pass
        self._debounce_id = self.after(delay_ms, fn)

    # ------------------------------------------------------------------ #
    @staticmethod
    def _parse_year(value):
        """Pull a 4-digit year out of a free-form date string, else None."""
        if not value:
            return None
        m = re.search(r"(\d{4})", str(value))
        return int(m.group(1)) if m else None

    @staticmethod
    def _to_sortable(value):
        """Turn dd/mm/yyyy(-ish) into yyyymmdd int for comparing; 0 if unparseable."""
        if not value:
            return 0
        m = re.search(r"(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})", str(value))
        if not m:
            y = RecordTable._parse_year(value)
            return y * 10000 if y else 0
        d, mo, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
        if y < 100:
            y += 2000
        return y * 10000 + mo * 100 + d

    def refresh(self):
        """Re-run the DB search (text query) then apply client-side filters."""
        try:
            self._all = self._fetch(self.search.get()) or []
        except Exception as exc:
            show_error(self, "Database error", str(exc))
            self._all = []
        # Populate the year dropdown from the data.
        years = sorted({y for r in self._all
                        if (y := self._parse_year(r.get(self.date_key)))},
                       reverse=True)
        options = ["All years"] + [str(y) for y in years]
        self.year_menu.configure(values=options)
        if self.year_var.get() not in options:
            self.year_var.set("All years")
        self._apply_filters()

    def _apply_filters(self):
        rows = list(self._all)

        # Year filter.
        yr = self.year_var.get()
        if yr != "All years":
            rows = [r for r in rows if self._parse_year(r.get(self.date_key)) == int(yr)]

        # Date range.
        lo = self._to_sortable(self.from_entry.get()) if self.from_entry.get().strip() else None
        hi = self._to_sortable(self.to_entry.get()) if self.to_entry.get().strip() else None
        if lo:
            rows = [r for r in rows if self._to_sortable(r.get(self.date_key)) >= lo]
        if hi:
            rows = [r for r in rows if self._to_sortable(r.get(self.date_key)) <= hi]

        # Sort.
        s = self.sort_var.get()
        if s == "Newest first":
            rows.sort(key=lambda r: self._to_sortable(r.get(self.date_key)), reverse=True)
        elif s == "Oldest first":
            rows.sort(key=lambda r: self._to_sortable(r.get(self.date_key)))
        elif s == "Name (A–Z)":
            name_key = self.columns[0][1]
            rows.sort(key=lambda r: str(r.get(name_key) or "").lower())

        self._render(rows)

    def _clear_filters(self):
        self.search.delete(0, "end")
        self.from_entry.delete(0, "end")
        self.to_entry.delete(0, "end")
        self.year_var.set("All years")
        self.sort_var.set("Newest first")
        self.refresh()

    def _render(self, rows):
        """Render rows by REUSING pooled widgets instead of destroying and
        rebuilding them every time. Creating CTkButtons is expensive, so this
        keeps filtering/typing snappy: existing rows just get new text +
        rebound commands; new rows are built only when the list grows; surplus
        rows are hidden (and kept for next time)."""
        self.count_label.configure(text="{} record{}".format(
            len(rows), "" if len(rows) == 1 else "s"))

        # Empty-state label (created lazily, hidden when there are rows).
        if not hasattr(self, "_empty_label"):
            self._empty_label = ctk.CTkLabel(
                self.rows, text="No records found.", font=LABEL_FONT,
                text_color="gray")
        if not rows:
            for r in self._row_pool:
                r["frame"].pack_forget()
            self._empty_label.pack(pady=24)
            return
        self._empty_label.pack_forget()

        # Grow the pool if needed.
        while len(self._row_pool) < len(rows):
            self._row_pool.append(self._build_pooled_row())

        for i, rec in enumerate(rows):
            self._fill_pooled_row(self._row_pool[i], rec, i)
            self._row_pool[i]["frame"].pack(fill="x", pady=2)

        # Hide any leftover rows from a previous, longer result set.
        for r in self._row_pool[len(rows):]:
            r["frame"].pack_forget()

    def _build_pooled_row(self):
        """Create one reusable row widget (frame + cell labels + action buttons)."""
        frame = ctk.CTkFrame(self.rows, corner_radius=8)
        cells = []
        for c, (_label, _key, weight) in enumerate(self.columns):
            frame.grid_columnconfigure(c, weight=weight, uniform="col")
            lbl = ctk.CTkLabel(frame, text="", font=LABEL_FONT, anchor="w",
                               justify="left")
            lbl.grid(row=0, column=c, sticky="ew", padx=PAD, pady=10)
            cells.append(lbl)
        actions_col = len(self.columns)
        frame.grid_columnconfigure(actions_col, weight=0)
        btns = ctk.CTkFrame(frame, fg_color="transparent")
        btns.grid(row=0, column=actions_col, sticky="e", padx=(0, 8))
        edit = primary_button(btns, "Edit", font=SMALL_FONT, width=70, height=32)
        edit.pack(side="left", padx=3)
        reprint = secondary_button(btns, "Reprint", font=SMALL_FONT, width=80, height=32)
        reprint.pack(side="left", padx=3)
        delete = secondary_button(btns, "Delete", font=SMALL_FONT, width=72, height=32)
        delete.pack(side="left", padx=3)
        return {"frame": frame, "cells": cells,
                "edit": edit, "reprint": reprint, "delete": delete}

    def _fill_pooled_row(self, row, rec, index):
        """Update a pooled row's text, stripe colour and button commands."""
        row["frame"].configure(fg_color=ROW_BG if index % 2 == 0 else ROW_ALT_BG)
        for lbl, (_label, key, _weight) in zip(row["cells"], self.columns):
            lbl.configure(text=str(rec.get(key) or "—"))
        rec_id = rec["id"]
        row["edit"].configure(command=lambda i=rec_id: self._on_edit(i))
        row["reprint"].configure(command=lambda i=rec_id: self._on_reprint(i))
        row["delete"].configure(command=lambda i=rec_id: self._on_delete(i))


# --------------------------------------------------------------------------- #
# Print preview window — renders the items at screen scale on a canvas so staff
# can sanity-check positions before wasting a real pre-printed sheet.
# --------------------------------------------------------------------------- #
class PreviewWindow(ctk.CTkToplevel):
    def __init__(self, parent, form_type, data, config):
        super().__init__(parent)
        self.title("Print Preview - {}".format(layouts.FORMS[form_type]["title"]))
        self.geometry("620x820")
        self.config_obj = config

        paper_size = config.paper_size(form_type)
        page_w_mm, page_h_mm = layouts.PAGE_SIZES_MM.get(
            paper_size, layouts.PAGE_SIZES_MM["A4"]
        )
        scale = 2.6  # screen pixels per mm
        cal_x, cal_y = config.calibration(form_type)

        ctk.CTkLabel(
            self,
            text="Preview only – the grey form is the pre-printed {} sheet; "
                 "your entries are shown in black where they will land.".format(
                     paper_size),
            font=SMALL_FONT, wraplength=580,
        ).pack(padx=12, pady=(12, 6))

        # Scrollable canvas so the full page fits even on short screens.
        wrap = tk.Frame(self, bg="white")
        wrap.pack(fill="both", expand=True, padx=12, pady=(0, 6))
        canvas = tk.Canvas(
            wrap, width=int(page_w_mm * scale), height=int(page_h_mm * scale),
            bg="white", highlightthickness=1, highlightbackground="#cccccc",
        )
        vbar = tk.Scrollbar(wrap, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=vbar.set,
                         scrollregion=(0, 0, int(page_w_mm * scale),
                                       int(page_h_mm * scale)))
        vbar.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)

        # Page border.
        canvas.create_rectangle(
            1, 1, page_w_mm * scale, page_h_mm * scale, outline="#dddddd"
        )

        # --- 1) Draw the pre-printed FORM template in light grey --------- #
        self._draw_template(canvas, form_type, scale)

        # --- 2) Overlay the user's VALUES in black ----------------------- #
        items = printing.collect_items(form_type, data)
        for x_mm, y_mm, text in items:
            x = (x_mm + cal_x) * scale
            y = (y_mm + cal_y) * scale
            canvas.create_text(
                x, y, text=text, anchor="nw", fill="#111111",
                font=(config.font_name, 9),
            )

        ctk.CTkButton(
            self, text="Close", font=BUTTON_FONT, corner_radius=CORNER,
            command=self.destroy,
        ).pack(pady=(0, 12))

        self.transient(parent)

    # ------------------------------------------------------------------ #
    def _draw_template(self, canvas, form_type, scale):
        """Render the static pre-printed form (title, labels, colons, party
        headers) in light grey so the preview reads like the real sheet."""
        form = layouts.FORMS[form_type]
        tmpl = form.get("template")
        if not tmpl:
            return
        grey = "#9aa3af"

        # Centred title block.
        for x_mm, y_mm, text in tmpl.get("title", []):
            canvas.create_text(x_mm * scale, y_mm * scale, text=text,
                                anchor="n", fill="#555b66",
                                font=(FONT_FAMILY, 10, "bold"))

        # Left-column labels (and any inline paragraph/footer text).
        for x_mm, y_mm, text in tmpl.get("labels", []):
            canvas.create_text(x_mm * scale, y_mm * scale, text=text,
                                anchor="nw", fill=grey, font=(FONT_FAMILY, 8))

        # Colons + a dotted guide line after each value row.
        colon_x = tmpl.get("colon_x")
        if colon_x is not None:
            for y_mm in tmpl.get("colon_rows", []):
                cx, cy = colon_x * scale, y_mm * scale
                canvas.create_text(cx, cy, text=":", anchor="nw",
                                   fill=grey, font=(FONT_FAMILY, 8))
                canvas.create_line(cx + 6, cy + 11 * scale / 2.6,
                                   (colon_x + 110) * scale, cy + 11 * scale / 2.6,
                                   fill="#cdd3db", dash=(2, 3))

        # Marriage: label the two value columns so A / B are obvious.
        if form_type == "marriage":
            party_x = form.get("party_x", {})
            ax = party_x.get("A")
            bx = party_x.get("B")
            if ax is not None:
                canvas.create_text(ax * scale, 66.0 * scale, text="Party A",
                                   anchor="nw", fill="#555b66",
                                   font=(FONT_FAMILY, 8, "bold"))
            if bx is not None:
                canvas.create_text(bx * scale, 66.0 * scale, text="Party B",
                                   anchor="nw", fill="#555b66",
                                   font=(FONT_FAMILY, 8, "bold"))
