"""
layouts.py
==========
Coordinate maps for printing variable values onto the THREE pre-printed forms.

How to read this file
---------------------
* Every coordinate is ``(x_mm, y_mm)`` measured from the **top-left corner of
  the physical page** (portrait), in **millimetres**.
* ``x_mm`` grows to the right, ``y_mm`` grows downward.
* The printing engine converts mm -> printer dots using the printer's real DPI,
  then adds the per-form calibration offset the user set in Settings.
* These numbers were estimated from photographs of the actual sheets, so they
  are a *good starting point*. Final alignment is done on real paper with the
  "Print Alignment Test" button and the X/Y offset fields in Settings.
  ==> To nudge a single field, change its tuple here.
  ==> To shift the WHOLE form, use the calibration offset in Settings instead.

Page sizes (portrait), width x height in mm:
    A4     = 210 x 297
    Letter = 216 x 279
"""

PAGE_SIZES_MM = {
    "A4": (210.0, 297.0),
    "Letter": (215.9, 279.4),
}

# Default font used for the printed values (overridable in config).
DEFAULT_FONT = "Arial"
DEFAULT_FONT_PT = 11


# =========================================================================== #
# FORM 1 — DEATH EXTRACT  (portrait)
# Pre-printed header "DIOCESE OF MADURAI RAMNAD / CHURCH OF SOUTH INDIA /
# DEATH EXTRACT" is NOT printed by us.
#
# Layout: a left column of labels each followed by a colon at ~x=85mm; values
# start just after the colon at ~x=90mm. "S.No." value sits at the top-right.
# Rows are ~9-10mm apart. The certifying paragraph blanks and the
# Prepared/Checked lines are near the bottom.
# =========================================================================== #
DEATH_LAYOUT = {
    # field name           : (x_mm, y_mm)
    "serial_no":             (185.0, 47.0),   # top-right, after "S.No."
    "number":                (90.0,  52.0),
    "date_of_death":         (90.0,  62.0),
    "date_of_burial":        (90.0,  71.0),
    "name_of_dead_person":   (90.0,  81.0),
    "age":                   (90.0,  90.0),
    "occupation":            (90.0,  99.0),
    "cause_of_death":        (90.0,  109.0),
    "family_relation":       (90.0,  118.0),
    "place_of_death":        (90.0,  128.0),
    "person_who_buried_body":(90.0,  137.0),
    "place_of_burial":       (90.0,  147.0),
    # Certifying paragraph blanks:
    "registrar_name":        (40.0,  175.0),  # "I, ____ Diocesan Registrar"
    "pastorate_name":        (103.0, 195.0),  # "...burial of ____ pastorate"
    "witness_date":          (95.0,  230.0),  # "Witness my hand ... day of ____"
    # Footer:
    "prepared_by":           (37.0,  256.0),
    "checked_by":            (37.0,  282.0),
}


# =========================================================================== #
# FORM 2 — MARRIAGE RETURNS COPY  (portrait, TWO party columns A / B)
# Pre-printed header "DIOCESE OF MADURA AND RAMNAD - C.S.I. / Copy of Marriage
# Returns ..." is NOT printed by us.
#
# The sheet has one label column on the left. The per-party fields are written
# in two columns: Party A and Party B. Shared fields use the single value X.
# =========================================================================== #
# X positions:
_M_VALUE_X = 95.0     # X for shared single-value fields
_M_PARTY_A_X = 95.0   # X for Party A column
_M_PARTY_B_X = 150.0  # X for Party B column

MARRIAGE_LAYOUT = {
    # --- shared (single value) fields ---
    "serial_no":            (185.0, 47.0),
    "number":               (_M_VALUE_X, 52.0),
    "when_married":         (_M_VALUE_X, 62.0),
    "place_solemnized":     (_M_VALUE_X, 178.0),
    "signature_of_licensee":(_M_VALUE_X, 156.0),
    "witnesses":            (_M_VALUE_X, 167.0),
    # certifying paragraph + footer
    "registrar_name":       (40.0, 200.0),
    "witness_date":         (95.0, 222.0),
    "prepared_by":          (37.0, 246.0),
    "checked_by":           (37.0, 258.0),
}

# Per-party fields: each maps to a y_mm; the engine uses PARTY_A_X / PARTY_B_X.
MARRIAGE_PARTY_LAYOUT = {
    # field                       : y_mm
    "name_of_party":               72.0,
    "surname":                     82.0,
    "age":                         92.0,
    "condition":                   102.0,
    "rank_or_profession":          112.0,
    "residence_at_marriage":       124.0,
    "fathers_name":                134.0,
    "signature_contracting_party": 145.0,
}
MARRIAGE_PARTY_X = {"A": _M_PARTY_A_X, "B": _M_PARTY_B_X}


# =========================================================================== #
# FORM 3 — BAPTISM CERTIFICATE  (portrait)
# Pre-printed header "DIOCESE OF MADURA-RAMNAD - CSI / BAPTISM CERTIFICATE"
# is NOT printed by us.
#
# Single label column; values start at ~x=85mm after each colon.
# =========================================================================== #
_B_VALUE_X = 85.0

BAPTISM_LAYOUT = {
    "number":                    (_B_VALUE_X, 50.0),
    "when_baptized":             (_B_VALUE_X, 60.0),
    "said_to_be_born":           (_B_VALUE_X, 70.0),
    "christian_name":            (_B_VALUE_X, 80.0),
    "surname_former_name":       (_B_VALUE_X, 90.0),
    "sex":                       (_B_VALUE_X, 100.0),
    "father_name":               (_B_VALUE_X, 110.0),
    "mother_name":               (_B_VALUE_X, 120.0),
    "trade_or_profession":       (_B_VALUE_X, 130.0),
    "names_of_godparents":       (_B_VALUE_X, 140.0),
    "where_baptized":            (_B_VALUE_X, 150.0),
    "signature_by_whom_baptized":(_B_VALUE_X, 162.0),
    # certifying paragraph + footer
    "baptized_by_name":          (45.0, 185.0),   # "Mr / Rev. ____"
    "witness_date":              (75.0, 215.0),   # "Witness my hand the ... day of ____"
    "prepared_by":               (37.0, 248.0),
    "checked_by":                (37.0, 262.0),
}


# --------------------------------------------------------------------------- #
# Registry so the printing engine can look a form up by key.
# --------------------------------------------------------------------------- #
FORMS = {
    "death": {
        "title": "Death Extract",
        "layout": DEATH_LAYOUT,
    },
    "marriage": {
        "title": "Marriage Returns",
        "layout": MARRIAGE_LAYOUT,
        "party_layout": MARRIAGE_PARTY_LAYOUT,
        "party_x": MARRIAGE_PARTY_X,
    },
    "baptism": {
        "title": "Baptism Certificate",
        "layout": BAPTISM_LAYOUT,
    },
}
