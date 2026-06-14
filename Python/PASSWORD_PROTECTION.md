# App Password Protection

How the application's open-password works: how to set it, what happens on
launch, where it's stored, and how to recover if it's forgotten.

---

## 1. What it does

- When a password is set, the app shows an **Unlock** prompt **every time it is
  opened** (including after being closed and reopened).
- The main window stays hidden until the correct password is entered.
- A wrong password re-asks. **Cancel / closing the prompt exits the app.**
- If **no** password is set, the app opens normally with no prompt.

---

## 2. Setting / changing / removing the password

All done inside the app: **Settings → Security**.

| State | Buttons shown | Action |
|---|---|---|
| No password yet | **Set password** | Enter the new password twice (confirm). |
| Password is set | **Change password** | Asks for the current password, then the new one twice. |
| Password is set | **Remove password** | Asks for the current password, confirms, then disables the prompt. |

Notes:
- Setting or changing requires typing the password **twice** so a typo can't lock you out.
- Changing or removing first asks for the **current** password.
- After saving, the change takes effect the **next time the app opens**.

---

## 3. What happens on startup

```
App launches
   │
   ├─ No password set ─────────────► main window opens
   │
   └─ Password set
          │
          ▼
     "Unlock" prompt
          │
   ┌──────┴───────┐
   │ correct      │ wrong ──► error, ask again
   ▼              
 main window opens     Cancel / close ──► app exits
```

---

## 4. How it is stored (security)

- The password is **never stored as plaintext**.
- It is saved as a **PBKDF2-SHA256 hash with a random per-install salt**
  (200,000 iterations) in the config file, and compared in constant time.
- Config file location:
  - **Windows:** `%APPDATA%\DioceseCertManager\config.json`
  - **Linux / macOS (dev):** `~/.diocese_cert_manager/config.json`
- Relevant keys:

```json
{
  "password_hash": "<hex hash, or empty if no password>",
  "password_salt": "<hex salt>"
}
```

> **Important — this is access control, not data encryption.**
> The password keeps people out of the **app**. The database file
> (`diocese.db`) itself is **not encrypted**, so anyone with direct access to
> that file could still open it outside the app. This is the usual level of
> protection for a front-desk tool. If you need the **data** encrypted at rest,
> that is a separate, larger change — ask for it specifically.

---

## 5. Recovery — forgotten password

If the password is forgotten, you can reset it by editing the config file:

1. Close the app.
2. Open the config file (see paths in §4).
3. Set both values back to empty strings:

   ```json
   "password_hash": "",
   "password_salt": ""
   ```

   (Or delete those two lines.)
4. Save and reopen the app — it will open without a prompt. You can then set a
   new password from **Settings → Security**.

This is intentional: because the data isn't encrypted, the password can always
be cleared by someone with file access. Protect the machine/folder accordingly.

---

## 6. Where it's implemented (for developers)

| File | Responsibility |
|---|---|
| [`config.py`](config.py) | `has_password()`, `set_password()`, `verify_password()`; stores `password_hash` + `password_salt`. |
| [`ui_common.py`](ui_common.py) | `_PasswordDialog` / `prompt_password()` — the modal password box (with optional confirm field). |
| [`main.py`](main.py) | `_password_gate()` — hides the window and requires the password on startup; cancelling aborts. |
| [`ui_settings.py`](ui_settings.py) | **Security** card — Set / Change / Remove password. |
