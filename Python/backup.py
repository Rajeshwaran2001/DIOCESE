"""
backup.py
=========
Backup the encrypted database to a **removable (external) drive only**.

* :func:`list_external_drives` returns the removable drives currently plugged in
  (USB sticks / pen drives). Internal and network drives are deliberately
  excluded so a backup can never be written "back to the same disk".
* :func:`make_backup` writes a ``diocese_backups_<date>_<time>.zip`` containing
  the already-encrypted database file onto the chosen drive.

The zip bundles both the encrypted database (``.enc``) and the local encryption
key (``diocese-recovery.key``) so a single ``.zip`` is enough to restore on any
PC — no separate key file is needed.

pywin32 (Windows) is required for drive detection; on other platforms
:func:`list_external_drives` returns an empty list.
"""

import os
import zipfile
from datetime import datetime

import secure_store

try:  # Windows-only drive enumeration
    import win32api
    import win32file
    _WIN = True
except Exception:
    win32api = None
    win32file = None
    _WIN = False


class BackupError(Exception):
    """Raised for any backup problem so the UI can show a friendly dialog."""


def list_external_drives():
    """Return ``[(root, label), ...]`` for removable drives that are present.

    ``root`` is like ``"E:\\"``; ``label`` is the volume name (may be empty).
    """
    if not _WIN:
        return []
    out = []
    try:
        roots = win32api.GetLogicalDriveStrings().split("\x00")
    except Exception:
        return []
    for root in roots:
        root = root.strip()
        if not root:
            continue
        try:
            if win32file.GetDriveType(root) != win32file.DRIVE_REMOVABLE:
                continue
            try:
                label = win32api.GetVolumeInformation(root)[0] or ""
            except Exception:
                label = ""
            out.append((root, label))
        except Exception:
            continue
    return out


def is_external_drive(path):
    """True if ``path`` lives on a removable drive (Windows)."""
    if not _WIN or not path:
        return False
    drive = os.path.splitdrive(os.path.abspath(path))[0]
    if not drive:
        return False
    root = drive + os.sep
    try:
        return win32file.GetDriveType(root) == win32file.DRIVE_REMOVABLE
    except Exception:
        return False


def default_backup_name(now=None):
    """e.g. ``diocese_backups_2026-06-12_1530.zip`` (date + time, never clashes)."""
    now = now or datetime.now()
    return now.strftime("diocese_backups_%Y-%m-%d_%H%M.zip")


# Name used inside the zip for the recovery key entry.
_KEY_ARCNAME = "diocese-recovery.key"


def make_backup(enc_path, dest_dir, filename=None):
    """Zip the encrypted database **and** the local encryption key into ``dest_dir``.

    The recovery key is bundled so that a single ``.zip`` file is sufficient to
    restore the database on any PC — no separate key file is needed.

    Returns the full path of the created zip. Raises :class:`BackupError`.
    """
    if not os.path.exists(enc_path):
        raise BackupError(
            "There is nothing to back up yet — the database is created after "
            "you add and save the first record.")
    if not dest_dir or not os.path.isdir(dest_dir):
        raise BackupError("The selected drive/folder is not available.")
    if _WIN and not is_external_drive(dest_dir):
        raise BackupError(
            "Backups can only be written to an external (USB) drive. "
            "Please insert a USB drive and select it.")

    key_path = secure_store.key_path()

    filename = filename or default_backup_name()
    dest = os.path.join(dest_dir, filename)
    tmp = dest + ".part"
    try:
        with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.write(enc_path, arcname=secure_store.ENC_NAME)
            if os.path.exists(key_path):
                zf.write(key_path, arcname=_KEY_ARCNAME)
        os.replace(tmp, dest)
    except Exception as exc:
        try:
            if os.path.exists(tmp):
                os.remove(tmp)
        except OSError:
            pass
        raise BackupError("Could not write the backup:\n{}".format(exc))
    return dest


def restore_backup(zip_path, data_dir):
    """Restore a backup zip created by :func:`make_backup`.

    Extracts ``diocese.db.enc`` into ``data_dir`` and, if the zip contains the
    recovery key (``diocese-recovery.key``), installs it as the local key so
    the database can be decrypted immediately — even on a different PC.

    Raises :class:`BackupError` on any problem.
    """
    if not zip_path or not os.path.isfile(zip_path):
        raise BackupError("Backup file not found:\n{}".format(zip_path))

    try:
        with zipfile.ZipFile(zip_path, "r") as zf:
            names = zf.namelist()

            if secure_store.ENC_NAME not in names:
                raise BackupError(
                    "This does not look like a Diocese backup — the file "
                    "'{}' is missing from the zip.".format(secure_store.ENC_NAME))

            os.makedirs(data_dir, exist_ok=True)

            # Restore the encryption key first so the DB can be opened.
            if _KEY_ARCNAME in names:
                key_dest = secure_store.key_path()
                os.makedirs(os.path.dirname(key_dest), exist_ok=True)
                key_data = zf.read(_KEY_ARCNAME)
                _atomic_write(key_dest, key_data)

            # Restore the encrypted database.
            enc_data = zf.read(secure_store.ENC_NAME)
            enc_dest = os.path.join(data_dir, secure_store.ENC_NAME)
            _atomic_write(enc_dest, enc_data)

    except BackupError:
        raise
    except zipfile.BadZipFile:
        raise BackupError("The file is not a valid zip archive:\n{}".format(zip_path))
    except Exception as exc:
        raise BackupError("Could not restore the backup:\n{}".format(exc))


def _atomic_write(path, data):
    """Write ``data`` bytes to ``path`` atomically (tmp + rename)."""
    tmp = path + ".tmp"
    with open(tmp, "wb") as fh:
        fh.write(data)
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(tmp, path)
