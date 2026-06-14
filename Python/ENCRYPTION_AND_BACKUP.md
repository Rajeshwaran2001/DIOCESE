# Database Encryption & Backup

How the records are encrypted at rest, and how to back them up to a USB /
external drive.

---

## 1. Encryption at rest

- The database is stored **encrypted** on disk as `diocese.db.enc`
  (**AES‑256‑GCM**, authenticated).
- While the app is running it decrypts to a **private working copy** in the
  local config folder; that copy is **re‑encrypted after every save** and
  **deleted when the app closes**.
- The plaintext database file is **never** left on the data folder / USB.

```
On disk (data folder):     diocese.db.enc        (encrypted, what you keep)
While the app runs:        <config>/diocese.working.db   (auto-deleted on close)
Encryption key:            <config>/dbkey.bin    (this PC only, never in backups)
```

**First run after this update:** if an old unencrypted `diocese.db` exists, it
is automatically encrypted on first open and the plaintext original is removed.

### Key management ("auto key on this PC")

- A random 256‑bit key is generated once and stored **only on this computer**
  (`dbkey.bin` in the config folder). It is **not** placed in the data folder or
  in any backup.
- Consequences:
  - A copied `diocese.db.enc` or a lost USB backup **cannot be read on another
    computer**.
  - Forgetting the **app password** does **not** lose data — the key is separate
    from the password.
  - Restoring on a **different / new** computer needs the key →
    **Settings → Backup → Save recovery key…** (see §4).

> **This protects confidentiality of copies.** Someone with access to *this*
> running PC (and the password) can read the data — that is expected.

---

## 2. Backups (Settings → Backup)

- **Backup to USB drive…** writes an encrypted backup to a **removable drive
  only**. Internal and network drives are intentionally **not** offered.
- If several USB drives are plugged in, you are asked **which one** to use.
- The file is named:

  ```
  diocese_backups_<YYYY-MM-DD>_<HHMM>.zip
  e.g.  diocese_backups_2026-06-12_2035.zip
  ```

  The date **and time** are included so a second backup the same day never
  overwrites the first.
- The zip contains the already‑encrypted `diocese.db.enc`, so the **backup
  itself is encrypted**. A lost USB stick is safe.

### If no drive is found

You'll see "No external drive found". Insert a USB / external drive and try
again. (Note: some USB **hard disks** report as fixed drives and may not be
listed; USB flash/pen drives work.)

---

## 3. Restoring a backup

**On the same computer** (the key is already here):

1. Close the app.
2. Unzip the backup and copy `diocese.db.enc` into your data folder
   (Settings shows the folder path), replacing the existing one.
3. Reopen the app.

**On a different / new computer** (needs the recovery key, see §4):

1. Install the app.
2. Put the recovery key in place as `dbkey.bin` in the config folder:
   - Windows: `%APPDATA%\DioceseCertManager\dbkey.bin`
   - Linux/macOS (dev): `~/.diocese_cert_manager/dbkey.bin`
3. Copy `diocese.db.enc` from the backup into the data folder.
4. Open the app.

> Without the matching key, an encrypted backup **cannot** be decrypted. This is
> by design.

---

## 4. Recovery key (disaster recovery)

Because the key lives only on this PC, a backup is useless on a new PC unless you
also keep the key. **Settings → Backup → Save recovery key…** writes
`diocese-recovery.key` (the 32‑byte key).

- Store it somewhere **safe and SEPARATE from the USB backups** (e.g. a
  different locked location / password manager).
- Anyone holding **both** a backup **and** this key can read the records — so
  never keep them together.

---

## 5. Where it's implemented (for developers)

| File | Responsibility |
|---|---|
| [`secure_store.py`](secure_store.py) | AES‑256‑GCM file encrypt/decrypt; local key (`dbkey.bin`); `SecureStore` (decrypt→working, `encrypt_back`, close); legacy migration; `export_recovery_key`. |
| [`db.py`](db.py) | `Database(db_file, on_commit=…)`; every write goes through `_commit()` which re‑encrypts via the hook. |
| [`main.py`](main.py) | Builds `SecureStore`, opens the working DB, re‑encrypts on close. |
| [`backup.py`](backup.py) | `list_external_drives()` (removable only), `default_backup_name()`, `make_backup()`. |
| [`ui_settings.py`](ui_settings.py) | **Backup** card — Backup to USB, Save recovery key. |

**Dependency:** `pycryptodome==3.20.0` (self‑contained AES, bundles with Nuitka
on Python 3.8 / Windows 7). Added to `requirements.txt` and `pyproject.toml`.

---

## 6. Limitations (be honest)

- While the app is open, a transient plaintext working copy exists locally
  (auto‑deleted on close; cleaned up on next start if a crash left one behind).
  Someone with live access to the running machine could read it.
- USB **hard disks** that report as fixed drives may not appear in the backup
  drive list (only removable/flash drives are listed).
- Key loss = data loss: if both `dbkey.bin` **and** every saved recovery key are
  lost, encrypted backups cannot be recovered.
