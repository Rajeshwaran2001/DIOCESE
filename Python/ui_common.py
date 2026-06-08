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
                text_color=("white" if is_primary else None),
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


class Card(ctk.CTkFrame):
    """A rounded container with an optional heading, used to group fields."""

    def __init__(self, parent, title=None, **kw):
        super().__init__(parent, corner_radius=CORNER, **kw)
        if title:
            ctk.CTkLabel(
                self, text=title, font=HEADING_FONT, anchor="w"
            ).pack(fill="x", padx=PAD + 4, pady=(PAD, 2))


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

        page_w_mm, page_h_mm = layouts.PAGE_SIZES_MM.get(
            config.paper_size, layouts.PAGE_SIZES_MM["A4"]
        )
        scale = 2.6  # screen pixels per mm
        cal_x, cal_y = config.calibration(form_type)

        ctk.CTkLabel(
            self,
            text="Preview only – values shown where they will print on the "
                 "pre-printed {} sheet.".format(config.paper_size),
            font=SMALL_FONT, wraplength=580,
        ).pack(padx=12, pady=(12, 6))

        canvas = tk.Canvas(
            self, width=int(page_w_mm * scale), height=int(page_h_mm * scale),
            bg="white", highlightthickness=1, highlightbackground="#cccccc",
        )
        canvas.pack(padx=12, pady=12)

        # Page border.
        canvas.create_rectangle(
            1, 1, page_w_mm * scale, page_h_mm * scale, outline="#dddddd"
        )

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
