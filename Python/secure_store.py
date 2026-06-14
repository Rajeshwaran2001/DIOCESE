"""
secure_store.py
===============
At-rest encryption for the SQLite database (file-level AES-256-GCM).

Design
------
SQLite needs a real file to work on, so we cannot encrypt every read/write in
place without a native engine (SQLCipher). Instead we keep the database
encrypted *on disk* and decrypt it to a private working copy only while the app
is running:

    on disk (data folder):   diocese.db.enc      <- AES-256-GCM ciphertext
    while running (local):   <config>/diocese.working.db   <- plaintext, transient

Flow:
    open()         decrypt .enc  -> working file   (or start a fresh working DB)
    encrypt_back() working file  -> .enc           (called after every DB write)
    close()        encrypt_back(), then delete the working file

Key management ("auto key on this PC")
--------------------------------------
A random 32-byte key is generated once and stored locally in the per-user
config folder (NOT in the data folder, so it never travels with the database or
its USB backups). Consequences:

* The .enc file and any USB backup are unreadable if copied to another computer.
* Forgetting the *app password* never loses data (the key is independent).
* Disaster recovery on a NEW PC requires the key: use "Save recovery key" in
  Settings and keep that file somewhere safe and separate from the backups.

Only :mod:`Crypto` (pycryptodome) is required; everything else is stdlib.
"""

import os

from Crypto.Cipher import AES

import config


MAGIC = b"DCMENC1\x00"          # 8-byte file marker / format version
KEY_BYTES = 32                  # AES-256
NONCE_BYTES = 12
TAG_BYTES = 16

ENC_NAME = "diocese.db.enc"     # encrypted DB, lives in the data folder
WORKING_NAME = "diocese.working.db"  # plaintext copy, lives in the config folder
KEY_NAME = "dbkey.bin"          # local key, lives in the config folder
LEGACY_PLAIN_NAME = "diocese.db"     # pre-encryption database to migrate


class CryptoError(Exception):
    """Raised when encryption / decryption / key handling fails."""


# --------------------------------------------------------------------------- #
# Key handling
# --------------------------------------------------------------------------- #
def key_path():
    return os.path.join(config.CONFIG_DIR, KEY_NAME)


def export_recovery_key(dest_path):
    """Copy the local key to ``dest_path`` so the DB can be restored on a new PC.

    Keep this file safe and SEPARATE from the backups — anyone with both the
    backup zip and this key file can read the records.
    """
    key = load_or_create_key()
    _atomic_write(dest_path, key)
    _harden_permissions(dest_path)
    return dest_path


def load_or_create_key():
    """Return the local 32-byte key, generating and persisting it on first use."""
    path = key_path()
    try:
        if os.path.exists(path):
            with open(path, "rb") as fh:
                key = fh.read()
            if len(key) == KEY_BYTES:
                return key
            # Wrong length -> treat as corrupt rather than silently re-keying.
            raise CryptoError("Encryption key file is corrupt: {}".format(path))
        key = os.urandom(KEY_BYTES)
        _atomic_write(path, key)
        _harden_permissions(path)
        return key
    except CryptoError:
        raise
    except Exception as exc:
        raise CryptoError("Cannot read/create encryption key:\n{}".format(exc))


# --------------------------------------------------------------------------- #
# Raw file encrypt / decrypt
# --------------------------------------------------------------------------- #
def encrypt_bytes(plain, key):
    nonce = os.urandom(NONCE_BYTES)
    cipher = AES.new(key, AES.MODE_GCM, nonce=nonce)
    ct, tag = cipher.encrypt_and_digest(plain)
    return MAGIC + nonce + tag + ct


def decrypt_bytes(blob, key):
    if blob[:len(MAGIC)] != MAGIC:
        raise CryptoError("Not a recognised encrypted database file.")
    off = len(MAGIC)
    nonce = blob[off:off + NONCE_BYTES]
    tag = blob[off + NONCE_BYTES:off + NONCE_BYTES + TAG_BYTES]
    ct = blob[off + NONCE_BYTES + TAG_BYTES:]
    cipher = AES.new(key, AES.MODE_GCM, nonce=nonce)
    try:
        return cipher.decrypt_and_verify(ct, tag)
    except ValueError:
        raise CryptoError(
            "Could not decrypt the database. The encryption key does not match "
            "this file (was it copied from another computer?), or the file is "
            "damaged.")


def encrypt_file(plain_path, enc_path, key):
    with open(plain_path, "rb") as fh:
        data = fh.read()
    _atomic_write(enc_path, encrypt_bytes(data, key))


def decrypt_file(enc_path, plain_path, key):
    with open(enc_path, "rb") as fh:
        blob = fh.read()
    _atomic_write(plain_path, decrypt_bytes(blob, key))
    _harden_permissions(plain_path)


# --------------------------------------------------------------------------- #
# SecureStore: ties the encrypted file <-> working file together
# --------------------------------------------------------------------------- #
class SecureStore:
    """Manages the encrypted DB for one data folder.

    ``data_dir`` is the user-chosen folder (may be a USB stick / network share);
    the ciphertext lives there. The transient plaintext working copy always
    lives in the local config folder so it never lands on removable media.
    """

    def __init__(self, data_dir, key=None):
        self.data_dir = data_dir
        self.enc_path = os.path.join(data_dir, ENC_NAME)
        self.legacy_plain = os.path.join(data_dir, LEGACY_PLAIN_NAME)
        self.working_path = os.path.join(config.CONFIG_DIR, WORKING_NAME)
        self.key = key or load_or_create_key()

    def open(self):
        """Prepare the plaintext working DB and return its path.

        * If an encrypted file exists -> decrypt it.
        * Else if a legacy plaintext DB exists -> adopt + encrypt it (one-time
          migration), then remove the plaintext original.
        * Else -> leave no working file; the DB layer will create a fresh one,
          which becomes encrypted on the first write.
        """
        os.makedirs(self.data_dir, exist_ok=True)
        self._remove_working()  # clear any leftover from a previous crash

        if os.path.exists(self.enc_path):
            decrypt_file(self.enc_path, self.working_path, self.key)
        elif os.path.exists(self.legacy_plain):
            # Migrate an old unencrypted database.
            decrypt_or_copy_legacy(self.legacy_plain, self.working_path)
            self.encrypt_back()
            try:
                os.remove(self.legacy_plain)
            except OSError:
                pass
        return self.working_path

    def encrypt_back(self):
        """Re-encrypt the working DB to the on-disk .enc file (atomic)."""
        if os.path.exists(self.working_path):
            encrypt_file(self.working_path, self.enc_path, self.key)

    def close(self):
        """Final encrypt + delete the plaintext working copy."""
        try:
            self.encrypt_back()
        finally:
            self._remove_working()

    def _remove_working(self):
        try:
            if os.path.exists(self.working_path):
                os.remove(self.working_path)
        except OSError:
            pass


def decrypt_or_copy_legacy(src_plain, working_path):
    """Copy a legacy plaintext DB to the working path (no decryption needed)."""
    with open(src_plain, "rb") as fh:
        data = fh.read()
    _atomic_write(working_path, data)
    _harden_permissions(working_path)


# --------------------------------------------------------------------------- #
# Small fs helpers
# --------------------------------------------------------------------------- #
def _atomic_write(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "wb") as fh:
        fh.write(data)
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(tmp, path)


def _harden_permissions(path):
    """Best-effort: restrict the file to the current user (POSIX)."""
    try:
        os.chmod(path, 0o600)
    except Exception:
        pass  # Windows ACLs differ; not critical
