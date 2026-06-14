"""
printing.py
===========
GDI coordinate-overlay print engine (pywin32).

The blank certificates are already printed by a press. This module prints ONLY
the variable values at exact millimetre positions so they land on the
pre-printed lines.

Pipeline (per page):
    CreateDC -> StartDoc -> StartPage -> TextOut(...) -> EndPage -> EndDoc

Coordinate math:
    px = mm / 25.4 * dpi          (dpi from GetDeviceCaps(LOGPIXELSX/Y))
    final = layout_mm + calibration_offset_mm   (then converted to px)

pywin32 is Windows-only. To let the project import/run for development on other
platforms, the win32 imports are guarded; if they fail, ``PRINTING_AVAILABLE``
is False and :class:`PrinterError` is raised when a print is actually attempted.
"""

import layouts

try:  # pywin32 is only present on Windows
    import win32print
    import win32ui
    import win32con
    import win32gui
    PRINTING_AVAILABLE = True
except Exception:  # ImportError on non-Windows, or missing pywin32
    win32print = None
    win32ui = None
    win32con = None
    win32gui = None
    PRINTING_AVAILABLE = False

# DEVMODE constant for a user-defined (custom) paper size. Not always exposed
# by win32con, so we keep a literal fallback.
DMPAPER_USER = 256


MM_PER_INCH = 25.4


class PrinterError(Exception):
    """Raised for any printing problem so the UI can show a friendly dialog."""


# --------------------------------------------------------------------------- #
# Printer discovery
# --------------------------------------------------------------------------- #
def get_printers():
    """Return a list of installed printer names (empty if printing unavailable).

    Tolerant of a stopped/disabled Print Spooler service (EnumPrinters then
    raises RPC error 1722); we return an empty list instead of crashing the
    Settings screen, so the app still opens on machines with no spooler running.
    """
    if not PRINTING_AVAILABLE:
        return []
    flags = win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS
    try:
        printers = win32print.EnumPrinters(flags)
    except Exception:
        return []
    # Each entry: (flags, description, name, comment)
    return [p[2] for p in printers]


def get_default_printer():
    if not PRINTING_AVAILABLE:
        return ""
    try:
        return win32print.GetDefaultPrinter()
    except Exception:
        return ""


# --------------------------------------------------------------------------- #
# Build the list of (x_mm, y_mm, text) items for a record.
# Used by BOTH the real printer and the on-screen preview, so what you see is
# what prints.
# --------------------------------------------------------------------------- #
def collect_items(form_type, data):
    """
    Return a list of (x_mm, y_mm, text) tuples for the given record.

    ``data`` is a dict of the record's column values. For marriage it also
    carries a ``parties`` dict: {"A": {...}, "B": {...}}.
    """
    form = layouts.FORMS[form_type]
    layout = form["layout"]
    items = []

    def add_item(fld, cx, cy, val):
        if not val:
            items.append((cx, cy, "—"))
            return
        if fld == "witness_day":
            import re
            m = re.match(r"^(\d+)(ST|ND|RD|TH)$", val, re.IGNORECASE)
            if m:
                prefix, suffix = m.groups()
                items.append((cx, cy, prefix))
                items.append((cx + len(prefix) * 2.2, cy, suffix.upper(), True))
                return
        items.append((cx, cy, val))

    # Shared / single-value fields.
    for field, (x_mm, y_mm) in layout.items():
        value = data.get(field, "")
        value = "" if value is None else str(value).strip()
        add_item(field, x_mm, y_mm, value)

    # Marriage: two party columns.
    if form_type == "marriage":
        party_layout = form["party_layout"]
        party_x = form["party_x"]
        parties = data.get("parties", {}) or {}
        for side, x_mm in party_x.items():
            party = parties.get(side, {}) or {}
            for field, y_mm in party_layout.items():
                value = party.get(field, "")
                value = "" if value is None else str(value).strip()
                add_item(field, x_mm, y_mm, value)

    return items


def alignment_test_items(form_type):
    """
    Return marker items so staff can see where each field will land.

    For every coordinate in the layout we print a '+' marker plus the field
    name, so the test sheet can be overlaid on a real form against the light.
    """
    form = layouts.FORMS[form_type]
    items = []
    for field, (x_mm, y_mm) in form["layout"].items():
        items.append((x_mm, y_mm, "+ " + field))
    if form_type == "marriage":
        for side, x_mm in form["party_x"].items():
            for field, y_mm in form["party_layout"].items():
                items.append((x_mm, y_mm, "+ {}.{}".format(side, field)))
    return items


# --------------------------------------------------------------------------- #
# Real printing
# --------------------------------------------------------------------------- #
def _mm_to_px(mm, dpi):
    return int(round(mm / MM_PER_INCH * dpi))


def _make_printer_dc(printer_name, hprinter, page_mm):
    """Create a printer DC, asking the driver for the exact ``page_mm`` size.

    ``page_mm`` is (width_mm, height_mm). We set a custom (user-defined) paper
    size on the printer's DEVMODE so the driver feeds/treats the right sheet and
    never scales the output. If anything about the DEVMODE path fails we fall
    back to a plain printer DC (whatever paper the driver currently has).
    """
    try:
        devmode = win32print.GetPrinter(hprinter, 2)["pDevMode"]
        if devmode is not None and page_mm:
            w_mm, h_mm = page_mm
            devmode.PaperSize = DMPAPER_USER
            devmode.PaperWidth = int(round(w_mm * 10))   # tenths of a mm
            devmode.PaperLength = int(round(h_mm * 10))  # tenths of a mm
            fields = getattr(win32con, "DM_PAPERSIZE", 0x2)
            fields |= getattr(win32con, "DM_PAPERLENGTH", 0x4)
            fields |= getattr(win32con, "DM_PAPERWIDTH", 0x8)
            devmode.Fields = devmode.Fields | fields
            hdc = win32gui.CreateDC("WINSPOOL", printer_name, devmode)
            return win32ui.CreateDCFromHandle(hdc)
    except Exception:
        pass  # fall through to the default DC
    dc = win32ui.CreateDC()
    dc.CreatePrinterDC(printer_name)
    return dc


def print_record(form_type, data, config, alignment_test=False, copies=1):
    """
    Print a single record (or an alignment test) onto the selected printer.

    Raises :class:`PrinterError` on any failure (no printer, driver error, ...).
    """
    if not PRINTING_AVAILABLE:
        raise PrinterError(
            "Printing is only available on Windows (pywin32 not found).\n"
            "Install the packaged Windows build to print."
        )

    # Choose printer: configured name, else system default.
    printer_name = config.printer_name or get_default_printer()
    if not printer_name:
        raise PrinterError("No printer found. Please install/select a printer.")

    # Gather items + per-form calibration offset.
    if alignment_test:
        items = alignment_test_items(form_type)
    else:
        items = collect_items(form_type, data)
    cal_x, cal_y = config.calibration(form_type)

    # The pre-printed sheet for this form (custom size, usually not A4).
    page_mm = layouts.PAGE_SIZES_MM.get(config.paper_size(form_type))

    # Create the device context for the printer.
    try:
        hprinter = win32print.OpenPrinter(printer_name)
    except Exception as exc:
        raise PrinterError("Cannot open printer '{}':\n{}".format(printer_name, exc))

    dc = None
    try:
        dc = _make_printer_dc(printer_name, hprinter, page_mm)

        dpi_x = dc.GetDeviceCaps(win32con.LOGPIXELSX)
        dpi_y = dc.GetDeviceCaps(win32con.LOGPIXELSY)

        # The printable area starts a few mm inside the physical page edge.
        # Our coordinates are measured from the PHYSICAL top-left corner, so we
        # subtract this hardware margin to land where we expect. (Without this,
        # the margin was silently absorbed by the calibration offset.)
        phys_off_x = dc.GetDeviceCaps(win32con.PHYSICALOFFSETX)
        phys_off_y = dc.GetDeviceCaps(win32con.PHYSICALOFFSETY)

        # Build a clean font sized to the printer DPI.
        # Font height in device units = points / 72 * dpi.
        font_pt = config.font_size_pt
        font_height = int(round(font_pt / 72.0 * dpi_y))
        font = win32ui.CreateFont(
            {
                "name": config.font_name,
                "height": font_height,
                "weight": 400,  # normal
            }
        )
        sup_font_height = int(round((font_pt * 0.6) / 72.0 * dpi_y))
        sup_font = win32ui.CreateFont(
            {
                "name": config.font_name,
                "height": sup_font_height,
                "weight": 400,
            }
        )

        dc.StartDoc("Diocese Certificate - {}".format(form_type))
        
        for _ in range(copies):
            dc.StartPage()
            # Black text, transparent background so we don't blank out pre-printed lines.
            dc.SetTextColor(0x000000)
            dc.SetBkMode(win32con.TRANSPARENT)

            for item in items:
                x_mm, y_mm, text = item[0], item[1], item[2]
                is_sup = item[3] if len(item) > 3 else False

                px = _mm_to_px(x_mm + cal_x, dpi_x) - phys_off_x
                py = _mm_to_px(y_mm + cal_y, dpi_y) - phys_off_y

                if is_sup:
                    dc.SelectObject(sup_font)
                    py -= int(round(font_pt * 0.4 / 72.0 * dpi_y))
                else:
                    dc.SelectObject(font)

                dc.TextOut(px, py, text)

            dc.EndPage()
            
        dc.EndDoc()
    except PrinterError:
        raise
    except Exception as exc:
        try:
            if dc is not None:
                dc.AbortDoc()
        except Exception:
            pass
        raise PrinterError("Printing failed:\n{}".format(exc))
    finally:
        try:
            if dc is not None:
                dc.DeleteDC()
        except Exception:
            pass
        try:
            win32print.ClosePrinter(hprinter)
        except Exception:
            pass
