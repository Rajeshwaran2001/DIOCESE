# Diocese Certificate Manager

A small, fast **Windows desktop application** for the *Diocese of Madurai Ramnad,
Church of South India*. Office staff can enter, store, search, and **overlay-print**
three kinds of records onto **pre-printed blank forms**, and reprint any past entry:

1. **Death Extract**
2. **Marriage Returns Copy** (two parties — Party A / Party B)
3. **Baptism Certificate**

It is a single `.exe` (≈10 MB), needs **no .NET, no Python, no WebView2**, and runs
on **Windows 7 SP1, 8, 8.1, 10 and 11 (64-bit)**. The SQLite database can live on a
USB drive or a shared network folder, and its location is changeable in-app.

---

## How overlay printing works

The forms are **already printed** on paper. The program prints **only the values**
at the exact spots where they belong on the blank form. Each form has a map of
`field → (X mm, Y mm)` coordinates measured from the **top-left corner of the page**
(see [`layouts.go`](layouts.go), heavily commented). A per-form **calibration**
(X/Y nudge in millimetres) in **Settings** lets staff fine-tune so values land on
the pre-printed lines — see **Calibrating the printout** below.

---

## Project layout

Idiomatic Go layout: one entry point under `cmd/`, all logic split into focused
packages under `internal/`.

```
diocese-certs/
  cmd/diocesecerts/
    main.go            Entry point — just calls ui.Run()
  internal/
    model/
      model.go         Plain record structs (DeathExtract, MarriageReturn, …) — no deps
    config/
      config.go        config.json load/save, data-path handling
    store/
      store.go         SQLite open/migrate + CRUD for all three records
    printing/
      layouts.go       Per-form field coordinate maps (millimetres) — TUNE HERE
      print.go         GDI overlay printing engine (lxn/win, Windows-only)
    ui/
      app.go           Run(), main window, navigation, shared helpers + table model
      death.go         Death form + history
      marriage.go      Marriage form (two party columns) + history
      baptism.go       Baptism form + history
      settings.go      Settings: data path, paper, font, calibration, test print
  resource/
    app.ico            Application icon (multi-resolution)
    app.manifest       Win7+ compatibility, asInvoker (no admin prompt), DPI aware
    versioninfo.json   Company / product / version metadata (goversioninfo input)
  installer/
    setup.iss          Inno Setup installer script
  build.bat            One-click build (embeds resources, builds the exe)
  go.mod / go.sum
```

**Package dependencies** (no cycles): `model` depends on nothing; `config` and
`store` depend on `model`; `printing` depends on `model` + `config`; `ui` depends
on all of them; `cmd/diocesecerts` depends only on `ui`. The Windows-only code
(`ui`, `printing/print.go`, `cmd`) is tagged `//go:build windows`; `model`,
`config`, `store` and `printing/layouts.go` are platform-neutral pure Go.

---

## Prerequisites (build machine)

1. **Go 1.20.x** — the **last** Go release that supports Windows 7/8/8.1.
   Download the `go1.20.x.windows-amd64.msi` from <https://go.dev/dl/>.
   > Do **not** use a newer Go: the resulting exe would refuse to start on Win7/8.
2. **goversioninfo** (embeds the icon, manifest and version info):
   ```
   go install github.com/josephspurrier/goversioninfo/cmd/goversioninfo@v1.4.0
   ```
   Make sure `%USERPROFILE%\go\bin` is on your `PATH`.
3. (Optional, for the installer) **Inno Setup 6** — <https://jrsoftware.org/isdl.php>.

---

## Building

From the project folder, simply run:

```
build.bat
```

That does two things:

1. `goversioninfo -64 -o cmd\diocesecerts\resource.syso resource\versioninfo.json`
   — produces `resource.syso` **next to the main package**, which the Go linker
   automatically picks up to embed the **icon + manifest + version info** (bare,
   metadata-less binaries get flagged by antivirus more often).
2. The actual build:
   ```
   set CGO_ENABLED=0
   set GOARCH=amd64
   go build -ldflags "-s -w -H windowsgui" -o DioceseCerts.exe .\cmd\diocesecerts
   ```
   - `CGO_ENABLED=0` → a **pure-Go, statically linked** binary (the `modernc.org/sqlite`
     driver is pure Go, so there is **no C compiler and no DLL** dependency).
   - `-ldflags "-s -w"` strips debug info → smaller exe (~10 MB).
   - `-H windowsgui` selects the GUI subsystem so no console window appears.

**Do NOT run UPX or any other exe packer** — packers are the single biggest cause of
antivirus false-positives for small Go binaries.

---

## Packaging an installer (Inno Setup)

1. Build `DioceseCerts.exe` first (`build.bat`).
2. Open `installer\setup.iss` in the Inno Setup Compiler and press **Compile** (F9),
   or:
   ```
   "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" installer\setup.iss
   ```
3. Output: `installer\Output\DioceseCerts-Setup.exe`.

The script installs to `%ProgramFiles%\DioceseCerts`, creates Start-Menu and
optional desktop shortcuts, and sets the minimum OS to **Windows 7 SP1**.

> **Avoiding admin prompts:** installing into Program Files needs administrator
> rights. To install **without any admin prompt**, edit `setup.iss`: set
> `DefaultDirName={localappdata}\{#MyAppShortName}`, comment out
> `PrivilegesRequired=admin`, and uncomment the `PrivilegesRequired=lowest` lines.
> The app itself never needs admin (`asInvoker` in the manifest).

---

## Avoiding antivirus false-positives

Small, unsigned Go executables are sometimes flagged by heuristic AV engines even
though they are completely clean. In order of effectiveness:

1. **Authenticode code-sign the exe and the installer.** This is by far the most
   effective measure. Buy a code-signing certificate:
   - A **standard (OV)** certificate works and builds reputation over a few weeks.
   - An **EV** certificate gives instant SmartScreen reputation (best for a public
     download), but costs more and requires a hardware token / cloud HSM.

   Sign with `signtool` (from the Windows SDK):
   ```
   signtool sign /fd SHA256 /a /tr http://timestamp.digicert.com /td SHA256 DioceseCerts.exe
   signtool sign /fd SHA256 /a /tr http://timestamp.digicert.com /td SHA256 installer\Output\DioceseCerts-Setup.exe
   ```
   Always include a timestamp (`/tr` … `/td SHA256`) so signatures stay valid after
   the certificate expires. To sign automatically from Inno Setup, configure a
   *Sign Tool* in the IDE and uncomment `SignTool=signtool` / `SignedUninstaller=yes`
   in `setup.iss`.

2. **Never pack the exe with UPX** (or any packer). We deliberately don't.

3. **Keep the embedded metadata** (icon, version info, manifest) — already done via
   `goversioninfo`. Don't strip it.

4. **If a specific vendor still flags it,** submit the file as a false-positive to
   that vendor's portal, e.g.:
   - Microsoft Defender: <https://www.microsoft.com/wdsi/filesubmission>
   - Most other vendors have a similar "submit a false positive / sample" page.

5. **Reputation builds over time.** Signed binaries from a consistent publisher
   accumulate trust; an EV certificate grants it immediately.

---

## Calibrating the printout

Because every printer has slightly different hardware margins, you tune each form
once:

1. Load a **plain sheet** (not a pre-printed form) into the printer.
2. Go to **Settings → Print calibration** and click **Print test** for the form you
   want to tune. This prints:
   - a **10 mm reference grid** of small crosshairs with `mm` labels, and
   - every field position marked with `[field_name]` sample text.
3. **Lay the plain test print over a real pre-printed form**, hold both up to a
   window/light, and see how far each value sits from where it should.
4. In Settings, adjust that form's **X offset** (positive = move right) and
   **Y offset** (positive = move down), in millimetres. Click **Print test** again.
5. Repeat until everything lines up, then click **Save Settings**.

If one single field is off on its own (rather than the whole sheet shifting), edit
that field's coordinate directly in [`layouts.go`](layouts.go) and rebuild — the
file is fully commented to explain the millimetre coordinate system.

> Tip: the global X/Y offset shifts the **whole** form. Use it first to get the sheet
> roughly aligned; only touch `layouts.go` for individual stragglers.

---

## Where the data and settings live

- **`config.json`** holds the database folder, paper size, printer, font, and the
  per-form calibration offsets. It is stored **next to the exe** when that folder is
  writable (good for portable/USB use), otherwise in `%APPDATA%\DioceseCerts\`
  (e.g. when installed under Program Files).
- **`diocese.db`** is a single SQLite file inside the configured **data folder**.
  Change the folder any time via **Settings → Data location → Change…**
  (point it at a USB drive or shared network folder). The choice is remembered.

  > Changing the folder points the app at a database **in that folder**; it does not
  > copy your existing data. To move existing records, copy `diocese.db` into the new
  > folder first (while the app is closed), then point the app at it.

---

## Usage at a glance

- **Death / Marriage / Baptism** tabs each have a **New / Edit Entry** sub-tab and a
  **History** sub-tab.
- Fill the form and click **Save**, or **Save & Print** to also overlay-print it.
- In **History**: search by name / number / date, then **View**, **Edit**,
  **Reprint**, or **Delete** (with confirmation). Double-click a row to load it.
- All errors (printer not found, bad data folder, locked DB) are shown as friendly
  dialog boxes; the program never crashes silently.

---

## License / copyright

© 2026 Diocese of Madurai Ramnad, Church of South India.
