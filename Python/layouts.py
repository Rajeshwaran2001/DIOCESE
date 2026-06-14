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
    A4             = 210   x 297
    Letter         = 216   x 279
    Death sheet    = 188   x 245   (measured: 18.8 x 24.5 cm)
    Marriage sheet = 207   x 275   (measured: 20.7 x 27.5 cm)
    Baptism sheet  = 207   x 279   (measured: 20.7 x 27.9 cm)

The three "... sheet" entries are the real pre-printed forms (they are NOT A4).
Each form picks its own size in Settings -> Print calibration.
"""

PAGE_SIZES_MM = {
    "A4": (210.0, 297.0),
    "Letter": (215.9, 279.4),
    "Death sheet": (188.0, 245.0),
    "Marriage sheet": (207.0, 275.0),
    "Baptism sheet": (207.0, 279.0),
}

# Default font used for the printed values (overridable in config).
DEFAULT_FONT = "Arial"
DEFAULT_FONT_PT = 10


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
    # Note: "S.No." is pre-printed on the sheet, so it is NOT printed by us.
    "number":                (79.0,  38.0),
    "date_of_death":         (79.0,  48.0),
    "date_of_burial":        (79.0,  56.0),
    "name_of_dead_person":   (79.0,  64.0),
    "age":                   (79.0,  72.0),
    "occupation":            (79.0,  80.0),
    "cause_of_death":        (79.0,  89.0),
    "family_relation":       (79.0,  97.0),
    "place_of_death":        (79.0,  105.0),
    "person_who_buried_body":(79.0,  113.0),
    "place_of_burial":       (79.0,  121.0),
    # Certifying paragraph blanks:
    "registrar_name":        (26.0,  145.0),
    "pastorate_name":        (87.0,  158.0),
    "witness_day":           (56.0,  192.0),
    "witness_month_year":    (92.0,  192.0),
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
_M_VALUE_X = 91.0     # X for shared single-value fields
_M_PARTY_A_X = 91.0   # X for Party A column
_M_PARTY_B_X = 150.0  # X for Party B column

MARRIAGE_LAYOUT = {
    # --- shared (single value) fields ---
    # Note: "S.No." is pre-printed on the sheet, so it is NOT printed by us.
    "number":               (_M_VALUE_X, 52.0),
    "when_married":         (_M_VALUE_X, 62.0),
    "signature_of_licensee":(_M_VALUE_X, 156.0),
    "witnesses":            (_M_VALUE_X, 167.0),
    "place_solemnized":     (_M_VALUE_X, 178.0),
    # certifying paragraph + footer
    "registrar_name":       (140.0, 260.0),
    "witness_day":          (48.0, 220.5),
    "witness_month_year":   (98.0, 220.5),
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
_B_VALUE_X = 81.0

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
    "baptized_by_name":          (32.0, 183.5),   # "Mr / Rev. ____"
    "witness_day":               (48.0, 213.5),
    "witness_month_year":        (98.0, 213.5),
}


# =========================================================================== #
# PREVIEW TEMPLATES
# ---------------------------------------------------------------------------
# These describe the STATIC, pre-printed parts of each sheet (title block, the
# left-hand field labels, the certificate paragraph and footer labels) so the
# on-screen Print Preview can draw a mock-up of the real form in light grey and
# overlay the user's values in black on top. They are used by PreviewWindow
# ONLY — they are never sent to the printer (the press already printed them).
#
# Each template is a dict with:
#   "labels": list of (x_mm, y_mm, text)         -> left-column labels + headers
#   "lines":  list of (x1_mm, y_mm, x2_mm)       -> dotted "fill-in" guide lines
# Coordinates use the same top-left mm origin as the layouts above; label rows
# are aligned to the value rows so the preview reads like the printed sheet.
# =========================================================================== #
_DOTTED = "·" * 60  # visual stand-in for a pre-printed dotted line

DEATH_TEMPLATE = {
    "title": [
        (105.0, 12.0, "DIOCESE OF MADURAI RAMNAD"),
        (105.0, 18.0, "CHURCH OF SOUTH INDIA"),
        (105.0, 25.0, "DEATH EXTRACT"),
    ],
    "labels": [
        (12.0,  38.0, "NUMBER"),
        (12.0,  48.0, "DATE OF DEATH"),
        (12.0,  56.0, "DATE OF BURIAL"),
        (12.0,  64.0, "NAME OF DEAD PERSON"),
        (12.0,  72.0, "AGE"),
        (12.0,  80.0, "OCCUPATION"),
        (12.0,  89.0, "CAUSE OF DEATH"),
        (12.0,  97.0, "FAMILY RELATION"),
        (12.0,  105.0, "PLACE OF DEATH"),
        (12.0,  113.0, "PERSON WHO BURIED THE BODY"),
        (12.0,  121.0, "PLACE OF BURIAL"),
        (160.0, 33.0, "S.No."),
        (12.0,  148.5, "I, ................................................................ Diocesan Registrar, Diocese of"),
        (12.0,  154.5, "Madurai Ramnad, 162, East Veli St., Madurai-625 001. certify that this is the true extract of"),
        (12.0,  161.5, "the Register of death and burial of ................................................................"),
        (12.0,  167.5, "pastorate which is kept in this office of the Diocesan Registrar, Diocese of Madurai Ramnad,"),
        (12.0,  173.5, "162, East Veli St., Madurai-625 001."),
        (12.0,  195.5, "Witness my hand........................day of........................................"),
        (150.0, 252.0, "DIOCESAN REGISTRAR"),
    ],
    "colon_x": 75.0,   # where the ":" sits between label and value rows
    "colon_rows": [38.0, 48.0, 56.0, 64.0, 72.0, 80.0, 89.0, 97.0, 105.0, 113.0, 121.0],
}

MARRIAGE_TEMPLATE = {
    "title": [
        (105.0, 10.0, "DIOCESE OF MADURA AND RAMNAD - C.S.I."),
        (105.0, 16.0, "Copy of Marriage Returns sent to the Registrar -"),
        (105.0, 21.0, "General of Births, Deaths and Marriages"),
    ],
    "labels": [
        (12.0,  52.0, "NUMBER"),
        (12.0,  62.0, "WHEN MARRIED"),
        (12.0,  72.0, "NAME OF PARTIES"),
        (12.0,  82.0, "SURNAME"),
        (12.0,  92.0, "AGE"),
        (12.0,  102.0, "CONDITION"),
        (12.0,  112.0, "RANK OR PROFESSION"),
        (12.0,  124.0, "RESIDENCE AT THE TIME OF MARRIAGE"),
        (12.0,  134.0, "FATHER'S NAME"),
        (12.0,  145.0, "SIGNATURE OF CONTRACTING PARTIES"),
        (12.0,  156.0, "SIGNATURE OF THE LICENSEE"),
        (12.0,  167.0, "WITNESSES"),
        (12.0,  178.0, "PLACE WHERE MARRIAGE WAS SOLEMNIZED"),
        (160.0, 47.0, "S.No."),
        (12.0,  195.0, "Diocesan Registrar, Diocese of Madura and"),
        (12.0,  201.0, "Ramnad, certifies that this is true record in"),
        (12.0,  207.0, "the Register of Copy of Marriage Returns."),
        (12.0,  222.0, "Witness my hand........................day of........................................"),
        (150.0, 270.0, "Diocesan Registrar"),
    ],
    "colon_x": 88.0,
    "colon_rows": [52.0, 62.0],
}

BAPTISM_TEMPLATE = {
    "title": [
        (105.0, 12.0, "DIOCESE OF MADURA-RAMNAD - CSI"),
        (105.0, 20.0, "BAPTISM CERTIFICATE"),
    ],
    "labels": [
        (12.0,  50.0, "NUMBER"),
        (12.0,  60.0, "WHEN BAPTIZED"),
        (12.0,  70.0, "SAID TO BE BORN"),
        (12.0,  80.0, "CHRISTIAN NAME"),
        (12.0,  90.0, "SURNAME / FORMER NAME"),
        (12.0,  100.0, "SEX"),
        (12.0,  110.0, "FATHER'S NAME"),
        (12.0,  120.0, "MOTHER'S NAME"),
        (12.0,  130.0, "TRADE OR PROFESSION"),
        (12.0,  140.0, "NAMES OF GODPARENTS"),
        (12.0,  150.0, "WHERE BAPTIZED"),
        (12.0,  162.0, "SIGNATURE BY WHOM BAPTIZED"),
        (12.0,  185.0, "Mr / Rev. ......................"),
        (12.0,  215.0, "Witness my hand the ........................day of........................................"),
    ],
    "colon_x": 78.0,
    "colon_rows": [50.0, 60.0, 70.0, 80.0, 90.0, 100.0, 110.0, 120.0, 130.0, 140.0, 150.0, 162.0],
}


# --------------------------------------------------------------------------- #
# Registry so the printing engine can look a form up by key.
# --------------------------------------------------------------------------- #
FORMS = {
    "death": {
        "title": "Death Extract",
        "layout": DEATH_LAYOUT,
        "template": DEATH_TEMPLATE,
    },
    "marriage": {
        "title": "Marriage Returns",
        "layout": MARRIAGE_LAYOUT,
        "party_layout": MARRIAGE_PARTY_LAYOUT,
        "party_x": MARRIAGE_PARTY_X,
        "template": MARRIAGE_TEMPLATE,
    },
    "baptism": {
        "title": "Baptism Certificate",
        "layout": BAPTISM_LAYOUT,
        "template": BAPTISM_TEMPLATE,
    },
}
