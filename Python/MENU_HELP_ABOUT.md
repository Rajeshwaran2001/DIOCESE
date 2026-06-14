# Menu Bar, Help & About

Where to edit the **company / contact details**, how to add **Help screenshots**,
and what the menu bar contains.

---

## 1. Edit the company / About details

Open [`ui_help.py`](ui_help.py). At the top is one clearly-marked block —
**this is the only place you need to change** to brand the About box:

```python
# =========================================================================== #
# APP / DEVELOPER INFO  — EDIT THESE VALUES
# =========================================================================== #
APP_NAME = "Diocese Certificate Manager"
APP_VERSION = "1.0.0"
ORG_NAME = "Diocese of Madurai Ramnad CSI"        # organisation using the app

# --- Developer / support details (replace the placeholders) ---------------- #
DEVELOPER_NAME = "<Developer company name>"        # TODO: your company
DEVELOPER_WEBSITE = "https://example.com"          # TODO: company website
SUPPORT_EMAIL = "support@example.com"              # TODO: support email
SUPPORT_PHONE = "+91 00000 00000"                  # TODO: support phone

COPYRIGHT = "© 2026 {}".format(ORG_NAME)
```

| Field | What it is | Shown in About as |
|---|---|---|
| `APP_NAME` | Product name | Big title |
| `APP_VERSION` | Version number | "Version 1.0.0" |
| `ORG_NAME` | The diocese / organisation using the app | "For: …" + copyright |
| `DEVELOPER_NAME` | **The company that developed it** | "Developed by: …" |
| `DEVELOPER_WEBSITE` | Company website URL | **Website** link (opens browser) |
| `SUPPORT_EMAIL` | Support email | **Email** link (opens mail app) |
| `SUPPORT_PHONE` | Support phone | **Phone** link (dials, where supported) |
| `COPYRIGHT` | Footer line | bottom of the window |

Notes:
- Website / Email / Phone are **clickable** in the About window
  (website → browser, email → `mailto:`, phone → `tel:`).
- Keep the quotes. Use a full `https://...` URL for the website.

### Optional: match the build metadata

The Windows build also embeds metadata in [`build.bat`](build.bat). If you want
the EXE properties to match, update these lines too (currently set to the
diocese, not the developer):

```bat
--company-name="Diocese of Madurai Ramnad CSI"
--product-name="Diocese Certificate Manager"
--file-version=1.0.0.0
--product-version=1.0.0.0
--copyright="Diocese of Madurai Ramnad CSI"
```

---

## 2. Add the Help screenshots

The Help window shows one screenshot per screen. They live in
[`assets/help/`](assets/help/). If a file is missing, a grey placeholder is shown
instead — so the app works with or without them.

Save PNGs with these exact names:

| File | Screen |
|---|---|
| `assets/help/overview.png` | Main window / sidebar |
| `assets/help/death.png` | Death Extract screen |
| `assets/help/marriage.png` | Marriage Returns screen |
| `assets/help/baptism.png` | Baptism Certificate screen |
| `assets/help/settings.png` | Settings screen |

- Take them at roughly **1100 px wide**; the window scales them down to fit.
- No code change is needed — just drop the files in and reopen Help.
- To change the **wording** of a Help page, edit the `HELP_TOPICS` list in
  [`ui_help.py`](ui_help.py) (each entry is `title`, `image filename`, and the
  bullet text).

---

## 3. What the menu bar contains

| Menu | Item | Action |
|---|---|---|
| **File** | Backup to USB drive… | Backup the encrypted database to a removable drive |
| | Save recovery key… | Export the encryption key (for restoring on another PC) |
| | Settings | Jump to the Settings screen |
| | Exit | Close the app |
| **Help** | Overview / User Guide | General how-to |
| | Death / Marriage / Baptism / Settings screen | Per-screen help + screenshot |
| **About** | (opens directly) | Version, organisation, developer, website, email, phone |

---

## 4. Where it's implemented (for developers)

| File | Responsibility |
|---|---|
| [`ui_help.py`](ui_help.py) | About info block, `HELP_TOPICS`, `HelpWindow`, `AboutWindow`, `open_help()`, `open_about()`. |
| [`main.py`](main.py) | `_build_menubar()` builds File / Help / About and wires the commands. |
| [`assets/help/`](assets/help/) | Screenshot PNGs (+ `README.txt` listing the filenames). |
