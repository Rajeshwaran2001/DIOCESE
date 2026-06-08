# Diocese Certificate Manager

A modern Windows desktop app for the **Diocese of Madurai Ramnad, Church of South
India**. Office staff enter, store, search and **print three record types onto
the pre-printed blank forms** (overlay printing), and can reprint any past entry.

* **Death Extract**
* **Marriage Returns** (two contracting parties, A / B)
* **Baptism Certificate**

Built with Python 3.8 + CustomTkinter (modern themed UI, web-style sidebar,
light/dark mode), SQLite for storage, and pywin32 GDI for precise coordinate
printing. Packaged with **Nuitka standalone** (not PyInstaller, no UPX) to keep
antivirus false-positives low.

---

## 1. Requirements

* **Windows 7 SP1 / 8.1 / 10 / 11**, 64-bit (runtime).
* **Python 3.8.10 (64-bit)** for development/building — the last Python that
  supports Windows 7. Do **not** use a newer Python; newer ones drop Win7.

## 2. Run from source (development)

```bat
py -3.8 -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

> Printing uses pywin32 and only works on Windows. On other platforms the app
> still runs (enter/save/search/preview) but a print attempt shows a friendly
> "printing only available on Windows" message.

## 3. Project layout

```
main.py          app bootstrap, CTk root, web-style sidebar nav, theme
ui_death.py      death entry form + history
ui_marriage.py   marriage entry form (2 party columns) + history
ui_baptism.py    baptism entry form + history
ui_settings.py   settings, calibration, alignment test
ui_common.py     shared widgets, modern dialogs, validation, print preview
db.py            sqlite open/migrate + CRUD for all records
printing.py      pywin32 GDI overlay print engine
layouts.py       per-form field coordinate maps (millimetres)
config.py        config.json load/save, data-path handling
assets/          app.ico, logo.png
installer/        setup.iss (Inno Setup, wraps the Nuitka build)
build.bat        Nuitka standalone build command
requirements.txt pinned dependencies
```

## 4. Where data lives

* **config.json** is stored at `%APPDATA%\DioceseCertManager\config.json`.
* The **SQLite database** (`diocese.db`) defaults to that same folder, but you
  can move it from **Settings → Database location** to a **USB stick** or a
  **shared network folder**. The choice is remembered.

## 5. Building the standalone app (Nuitka)

One-time prerequisites:

* Python 3.8.10 (64-bit) with the venv from step 2.
* **Visual Studio 2019 Build Tools** with the *Desktop development with C++*
  workload. (Nuitka can otherwise fetch MinGW64, but **MSVC** is the
  recommended/most-tested path for Python 3.8 standalone.)

Then:

```bat
build.bat
```

Output: `dist\main.dist\` — the entire folder is the portable app. Run
`dist\main.dist\main.exe`.

Key Nuitka flags (already in `build.bat`) and **why they are required**:

| Flag | Why |
|------|-----|
| `--standalone` | Folder build; flagged far less by AV than onefile/PyInstaller. |
| `--enable-plugin=tk-inter` | **Required** — bundles Tcl/Tk correctly. |
| `--include-package-data=customtkinter` | **Required** — ships CustomTkinter's theme JSON/assets. |
| `--include-data-dir=assets=assets` | Ships our `logo.png` / `app.ico`. |
| `--windows-console-mode=disable` | No console window for a GUI app. |
| `--windows-icon-from-ico=assets\app.ico` | Taskbar / Explorer icon. |
| `--company/--product/--file-version/...` | Embed version metadata (lowers AV suspicion). |

**Do NOT run UPX or any packer on the output.**

### Windows 7 runtime gotcha (Universal CRT)

Windows 7 SP1 may lack the **Universal CRT** that the Nuitka build needs. Two
options (the installer does both safely):

1. **Bundle the Microsoft Visual C++ 2015–2022 Redistributable (x64)** and
   install it silently if missing (handled by `installer/setup.iss`). Download
   `vc_redist.x64.exe` from Microsoft and place it in
   `installer\redist\vc_redist.x64.exe` before compiling the installer.
2. Or verify the `api-ms-win-crt-*.dll` / `vcruntime140.dll` that Nuitka copies
   into `dist\main.dist\` are sufficient on a clean Win7 SP1 box.

**Always test on a real or VM clean Windows 7 SP1 x64 install** with no Python.

## 6. Building the installer (Inno Setup)

1. Run `build.bat` so `dist\main.dist` exists.
2. Download `vc_redist.x64.exe` and put it in `installer\redist\`.
3. Open `installer\setup.iss` in **Inno Setup** and click *Compile*
   (or `iscc installer\setup.iss`).

Result: `installer\Output\DioceseCertManager-Setup.exe`. It installs per-user to
`%LOCALAPPDATA%\DioceseCertManager` (no admin), creates Start Menu + optional
desktop shortcuts, requires Win7 SP1+ (`MinVersion=6.1sp1`), and installs the
VC++ redist when needed.

## 7. Avoiding antivirus false-positives

Compiled Python apps sometimes trip heuristic AV engines. In order of impact:

1. **Nuitka standalone** (what we use) is already much better than PyInstaller,
   and better than Nuitka onefile (no self-extracting stub).
2. **Code-sign with Authenticode — this is the real fix.** Buy a standard or
   **EV** code-signing certificate. *(Since June 2023, the private key must live
   on a hardware USB token or a cloud HSM.)* Sign **both** the main `.exe` inside
   the dist **and** the installer:

   ```bat
   signtool sign /fd sha256 /tr http://timestamp.digicert.com /td sha256 ^
     dist\main.dist\main.exe
   signtool sign /fd sha256 /tr http://timestamp.digicert.com /td sha256 ^
     installer\Output\DioceseCertManager-Setup.exe
   ```

3. **Never pack with UPX** — packers are the #1 false-positive trigger.
4. **Embed version metadata + icon** (done via the Nuitka flags above).
5. **Submit any false positives** to the AV vendor's portal for whitelisting.
6. **Reputation builds over time** for a standard cert; an **EV cert** gives
   instant SmartScreen/Defender reputation.

## 8. Calibrating the printout

The forms are pre-printed; the app prints **only the values** at exact mm
positions. To line them up:

1. Go to **Settings → Print calibration**.
2. Click **Alignment Test** for a form — it prints `+ markers` for every field
   on plain paper.
3. Hold that sheet over a real pre-printed form against the light.
4. Adjust the **X offset** (right = +) and **Y offset** (down = +) in millimetres,
   click **Save**, and test again. Repeat per form.
5. For fine-tuning a *single* field, edit its `(x_mm, y_mm)` tuple in
   `layouts.py`. The X/Y offsets in Settings shift the **whole** form.

Also in Settings: choose **paper size** (A4 default / Letter), **theme**
(light/dark), **accent colour**, and the target **printer** (or the system
default).

## 9. Data model (SQLite)

* `death_extract` — one row per death extract.
* `marriage_return` (parent) + `marriage_party` (two child rows, side `A`/`B`).
* `baptism` — one row per baptism certificate.
* `settings` — `schema_version` and future migration state.

The schema is created automatically on first run; `schema_version` is stored for
future migrations.

## 10. Troubleshooting

| Symptom | Fix |
|---------|-----|
| "No printer found" | Install/select a printer in Settings, or set a Windows default. |
| App won't start on Win7 | Install the VC++ 2015–2022 x64 redistributable. |
| Values land off the lines | Use the alignment test + X/Y offsets (section 8). |
| Database locked / bad path | Point Settings → Database location at a writable folder. |
| Defender/AV flags the exe | Code-sign it (section 7); submit a false-positive report. |
