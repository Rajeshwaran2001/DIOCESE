# Print Layout & Paper Guide

A complete reference for adjusting **where each value prints** and **what paper size
each form uses**. All measurements are in **millimetres (mm)**.

- To change paper size for a form → do it in the app: **Settings → Print calibration → (form) → Paper size**. No code needed.
- To shift a **whole** form on the page → **Settings → Print calibration → (form) → Offset X / Y**. No code needed.
- To move a **single field** → edit its `(x_mm, y_mm)` in [`layouts.py`](layouts.py). This guide lists every field and its line number.

---

## 1. How coordinates work

- Every value's position is `(x_mm, y_mm)` measured from the **top-left corner of the physical sheet** (portrait).
- `x_mm` grows to the **right**. `y_mm` grows **downward**.
- The **vertical gap** between two rows is just the difference between their `y_mm` values (e.g. `62 - 52 = 10 mm` apart).
- To move a field **right**, increase `x`. **Left**, decrease `x`.
- To move a field **down**, increase `y`. **Up**, decrease `y`.
- After editing `layouts.py`, save and use **Settings → Alignment Test** for that form to check on plain paper held over a real sheet.

> Tip: change **one** number at a time and re-test. Small steps (1–3 mm) are usually enough.

---

## 2. Paper sizes (width × height, mm)

Defined in [`layouts.py`](layouts.py) → `PAGE_SIZES_MM`.

| Key (shown in Settings) | Width | Height | Used by (default) |
|---|---|---|---|
| A4 | 210.0 | 297.0 | — |
| Letter | 215.9 | 279.4 | — |
| **Death sheet** | **188.0** | **245.0** | Death Extract |
| **Marriage sheet** | **207.0** | **275.0** | Marriage Returns |
| **Baptism sheet** | **207.0** | **279.0** | Baptism Certificate |

Source measurements you gave: Death 18.8 × 24.5 cm · Marriage 20.7 × 27.5 cm · Baptism 20.7 × 27.9 cm.

**To change a sheet size:** edit the tuple in `PAGE_SIZES_MM`, e.g. `"Death sheet": (188.0, 245.0)` → `(189.0, 246.0)`.
Each form's chosen size is stored per-form in the config (see §6).

---

## 3. Death Extract — fields

Paper: **Death sheet (188 × 245 mm)**. Edit in [`layouts.py`](layouts.py) → `DEATH_LAYOUT`.

| Field (code key) | x_mm | y_mm | Notes |
|---|---|---|---|
| number | 90.0 | 52.0 | top value row |
| date_of_death | 90.0 | 62.0 | |
| date_of_burial | 90.0 | 71.0 | |
| name_of_dead_person | 90.0 | 81.0 | |
| age | 90.0 | 90.0 | |
| occupation | 90.0 | 99.0 | |
| cause_of_death | 90.0 | 109.0 | |
| family_relation | 90.0 | 118.0 | |
| place_of_death | 90.0 | 128.0 | |
| person_who_buried_body | 90.0 | 137.0 | |
| place_of_burial | 90.0 | 147.0 | |
| registrar_name | 40.0 | 175.0 | certifying paragraph |
| pastorate_name | 103.0 | 195.0 | certifying paragraph |
| witness_date | 95.0 | 230.0 | |
| prepared_by | 37.0 | 256.0 | ⚠ see warning below |
| checked_by | 37.0 | 282.0 | ⚠ see warning below |

> ⚠ **Death footer falls off the page.** The Death sheet is only **245 mm** tall, but
> `prepared_by` (y=256) and `checked_by` (y=282) sit **below** the bottom edge. These
> coordinates were originally estimated for A4 (297 mm). Move them up so they fit, e.g.
> `prepared_by → ~225` and `checked_by → ~235`, then run the Alignment Test to fine-tune.
> All the value rows (52–147) are well within the sheet and only need normal nudging.

---

## 4. Marriage Returns — fields

Paper: **Marriage sheet (207 × 275 mm)**. Edit in [`layouts.py`](layouts.py).
This form has **two party columns** (A and B), so per-party fields use one Y value and two X values.

### 4a. Shared (single-value) fields — `MARRIAGE_LAYOUT`

| Field (code key) | x_mm | y_mm |
|---|---|---|
| number | 95.0 | 52.0 |
| when_married | 95.0 | 62.0 |
| signature_of_licensee | 95.0 | 156.0 |
| witnesses | 95.0 | 167.0 |
| place_solemnized | 95.0 | 178.0 |
| registrar_name | 40.0 | 200.0 |
| witness_date | 95.0 | 222.0 |
| prepared_by | 37.0 | 246.0 |
| checked_by | 37.0 | 258.0 |

### 4b. Per-party fields — `MARRIAGE_PARTY_LAYOUT` (y only)

The same Y row is used for both parties; only the X differs (see 4c).

| Field (code key) | y_mm |
|---|---|
| name_of_party | 72.0 |
| surname | 82.0 |
| age | 92.0 |
| condition | 102.0 |
| rank_or_profession | 112.0 |
| residence_at_marriage | 124.0 |
| fathers_name | 134.0 |
| signature_contracting_party | 145.0 |

### 4c. Party column X positions — top of `MARRIAGE_LAYOUT` section

| Constant | Meaning | x_mm |
|---|---|---|
| `_M_VALUE_X` | shared single-value fields | 95.0 |
| `_M_PARTY_A_X` | Party **A** column | 95.0 |
| `_M_PARTY_B_X` | Party **B** column | 150.0 |

> To move the **whole** Party B column left/right, change `_M_PARTY_B_X` only (e.g. 150 → 145).
> To move **one** party field up/down for both columns, change its `y` in 4b.

---

## 5. Baptism Certificate — fields

Paper: **Baptism sheet (207 × 279 mm)**. Edit in [`layouts.py`](layouts.py) → `BAPTISM_LAYOUT`.
All value fields share one X (`_B_VALUE_X = 85.0`).

| Field (code key) | x_mm | y_mm |
|---|---|---|
| number | 85.0 | 50.0 |
| when_baptized | 85.0 | 60.0 |
| said_to_be_born | 85.0 | 70.0 |
| christian_name | 85.0 | 80.0 |
| surname_former_name | 85.0 | 90.0 |
| sex | 85.0 | 100.0 |
| father_name | 85.0 | 110.0 |
| mother_name | 85.0 | 120.0 |
| trade_or_profession | 85.0 | 130.0 |
| names_of_godparents | 85.0 | 140.0 |
| where_baptized | 85.0 | 150.0 |
| signature_by_whom_baptized | 85.0 | 162.0 |
| baptized_by_name | 45.0 | 185.0 |
| witness_date | 75.0 | 215.0 |
| prepared_by | 37.0 | 248.0 |
| checked_by | 37.0 | 262.0 |

> To move **all** baptism values left/right at once, change `_B_VALUE_X` (85.0).

---

## 6. Where settings are stored

Per-user config file (not the database):

- **Windows:** `%APPDATA%\DioceseCertManager\config.json`
- **Linux/macOS (dev):** `~/.diocese_cert_manager/config.json`

Relevant keys:

```json
{
  "paper_size": {
    "death":    "Death sheet",
    "marriage": "Marriage sheet",
    "baptism":  "Baptism sheet"
  },
  "calibration": {
    "death":    {"x_mm": 0.0, "y_mm": 0.0},
    "marriage": {"x_mm": 0.0, "y_mm": 0.0},
    "baptism":  {"x_mm": 0.0, "y_mm": 0.0}
  },
  "font_name": "Arial",
  "font_size_pt": 11
}
```

- `paper_size` and `calibration` are set from **Settings** (no need to edit JSON by hand).
- `font_name` / `font_size_pt` change the printed text size — currently only editable in this JSON.
  A bigger font also shifts text baselines slightly, so re-check alignment after changing it.

---

## 7. Quick decision guide

| I want to… | Where | Code? |
|---|---|---|
| Use a different paper size for a form | Settings → Print calibration → Paper size | No |
| Shift the whole form on the sheet | Settings → Print calibration → Offset X/Y | No |
| Move one field a little | `layouts.py` field tuple (§3–5) | Yes |
| Widen/narrow the gap between rows | `layouts.py` — change the `y` values | Yes |
| Move Party B column (marriage) | `layouts.py` → `_M_PARTY_B_X` | Yes |
| Move all baptism values sideways | `layouts.py` → `_B_VALUE_X` | Yes |
| Change a sheet's actual dimensions | `layouts.py` → `PAGE_SIZES_MM` | Yes |
| Change printed font/size | `config.json` → `font_name`, `font_size_pt` | JSON |

After **any** change, run **Settings → Alignment Test** for that form on plain paper, hold it
over a real pre-printed sheet against the light, then nudge the Offset X/Y until the values
sit on the lines.
