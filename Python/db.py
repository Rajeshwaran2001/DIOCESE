"""
db.py
=====
SQLite persistence layer for the Diocese Certificate Manager.

* Opens / creates the database under the user-configured ``data_path``.
* Creates the schema on first run and keeps a ``schema_version`` for future
  migrations.
* Provides simple CRUD + search helpers for the three record types.

All access goes through the :class:`Database` class. Rows are returned as plain
``dict`` objects (``sqlite3.Row`` -> dict) so the UI never has to know column
indexes.

Only the Python standard library is used here, so it runs on a clean 3.8 install.
"""

import os
import sqlite3
from datetime import datetime


SCHEMA_VERSION = 1


# --------------------------------------------------------------------------- #
# Column lists (kept here so the UI and printing layers share one source of
# truth). 'id', 'created_at', 'updated_at' are managed automatically.
# --------------------------------------------------------------------------- #
DEATH_FIELDS = [
    "serial_no", "number", "date_of_death", "date_of_burial",
    "name_of_dead_person", "age", "occupation", "cause_of_death",
    "family_relation", "place_of_death", "person_who_buried_body",
    "place_of_burial", "registrar_name", "pastorate_name", "witness_date",
    "prepared_by", "checked_by",
]

MARRIAGE_FIELDS = [
    "serial_no", "number", "when_married", "place_solemnized", "witnesses",
    "signature_of_licensee", "witness_date", "prepared_by", "checked_by",
    "registrar_name",
]

MARRIAGE_PARTY_FIELDS = [
    "side", "name_of_party", "surname", "age", "condition",
    "rank_or_profession", "residence_at_marriage", "fathers_name",
    "signature_contracting_party",
]

BAPTISM_FIELDS = [
    "number", "when_baptized", "said_to_be_born", "christian_name",
    "surname_former_name", "sex", "father_name", "mother_name",
    "trade_or_profession", "names_of_godparents", "where_baptized",
    "signature_by_whom_baptized", "baptized_by_name", "witness_date",
    "prepared_by", "checked_by",
]


def _now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


class Database:
    def __init__(self, db_file):
        self.db_file = db_file
        os.makedirs(os.path.dirname(db_file), exist_ok=True)
        # check_same_thread False: CustomTkinter callbacks all run on the main
        # thread anyway, but this keeps us safe if a print runs in a worker.
        self.conn = sqlite3.connect(db_file, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        self._migrate()

    # ------------------------------------------------------------------ #
    # Schema creation / migration
    # ------------------------------------------------------------------ #
    def _migrate(self):
        cur = self.conn.cursor()

        cur.execute(
            """CREATE TABLE IF NOT EXISTS settings (
                   key TEXT PRIMARY KEY,
                   value TEXT
               )"""
        )

        cur.execute(
            """CREATE TABLE IF NOT EXISTS death_extract (
                   id INTEGER PRIMARY KEY AUTOINCREMENT,
                   serial_no TEXT, number TEXT,
                   date_of_death TEXT, date_of_burial TEXT,
                   name_of_dead_person TEXT, age TEXT, occupation TEXT,
                   cause_of_death TEXT, family_relation TEXT,
                   place_of_death TEXT, person_who_buried_body TEXT,
                   place_of_burial TEXT, registrar_name TEXT,
                   pastorate_name TEXT, witness_date TEXT,
                   prepared_by TEXT, checked_by TEXT,
                   created_at TEXT, updated_at TEXT
               )"""
        )

        cur.execute(
            """CREATE TABLE IF NOT EXISTS marriage_return (
                   id INTEGER PRIMARY KEY AUTOINCREMENT,
                   serial_no TEXT, number TEXT, when_married TEXT,
                   place_solemnized TEXT, witnesses TEXT,
                   signature_of_licensee TEXT, witness_date TEXT,
                   prepared_by TEXT, checked_by TEXT, registrar_name TEXT,
                   created_at TEXT, updated_at TEXT
               )"""
        )

        cur.execute(
            """CREATE TABLE IF NOT EXISTS marriage_party (
                   id INTEGER PRIMARY KEY AUTOINCREMENT,
                   marriage_id INTEGER NOT NULL,
                   side TEXT, name_of_party TEXT, surname TEXT, age TEXT,
                   condition TEXT, rank_or_profession TEXT,
                   residence_at_marriage TEXT, fathers_name TEXT,
                   signature_contracting_party TEXT,
                   FOREIGN KEY (marriage_id)
                       REFERENCES marriage_return (id) ON DELETE CASCADE
               )"""
        )

        cur.execute(
            """CREATE TABLE IF NOT EXISTS baptism (
                   id INTEGER PRIMARY KEY AUTOINCREMENT,
                   number TEXT, when_baptized TEXT, said_to_be_born TEXT,
                   christian_name TEXT, surname_former_name TEXT, sex TEXT,
                   father_name TEXT, mother_name TEXT,
                   trade_or_profession TEXT, names_of_godparents TEXT,
                   where_baptized TEXT, signature_by_whom_baptized TEXT,
                   baptized_by_name TEXT, witness_date TEXT,
                   prepared_by TEXT, checked_by TEXT,
                   created_at TEXT, updated_at TEXT
               )"""
        )

        # Record / bump the schema version.
        cur.execute(
            "INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)",
            ("schema_version", str(SCHEMA_VERSION)),
        )
        self.conn.commit()

    def close(self):
        try:
            self.conn.close()
        except sqlite3.Error:
            pass

    # ------------------------------------------------------------------ #
    # Generic helpers
    # ------------------------------------------------------------------ #
    @staticmethod
    def _row_to_dict(row):
        return dict(row) if row is not None else None

    def _rows_to_dicts(self, rows):
        return [self._row_to_dict(r) for r in rows]

    # ================================================================== #
    # DEATH EXTRACT
    # ================================================================== #
    def insert_death(self, data):
        cols = DEATH_FIELDS
        placeholders = ", ".join(["?"] * (len(cols) + 2))
        values = [data.get(c, "") for c in cols] + [_now(), _now()]
        sql = "INSERT INTO death_extract ({}, created_at, updated_at) VALUES ({})".format(
            ", ".join(cols), placeholders
        )
        cur = self.conn.execute(sql, values)
        self.conn.commit()
        return cur.lastrowid

    def update_death(self, rec_id, data):
        assignments = ", ".join("{}=?".format(c) for c in DEATH_FIELDS)
        values = [data.get(c, "") for c in DEATH_FIELDS] + [_now(), rec_id]
        self.conn.execute(
            "UPDATE death_extract SET {}, updated_at=? WHERE id=?".format(assignments),
            values,
        )
        self.conn.commit()

    def get_death(self, rec_id):
        row = self.conn.execute(
            "SELECT * FROM death_extract WHERE id=?", (rec_id,)
        ).fetchone()
        return self._row_to_dict(row)

    def delete_death(self, rec_id):
        self.conn.execute("DELETE FROM death_extract WHERE id=?", (rec_id,))
        self.conn.commit()

    def search_death(self, query=""):
        like = "%{}%".format(query.strip())
        rows = self.conn.execute(
            """SELECT * FROM death_extract
               WHERE name_of_dead_person LIKE ? OR number LIKE ?
                  OR serial_no LIKE ? OR date_of_death LIKE ?
               ORDER BY id DESC""",
            (like, like, like, like),
        ).fetchall()
        return self._rows_to_dicts(rows)

    # ================================================================== #
    # MARRIAGE (parent + two party children)
    # ================================================================== #
    def insert_marriage(self, data, party_a, party_b):
        cols = MARRIAGE_FIELDS
        placeholders = ", ".join(["?"] * (len(cols) + 2))
        values = [data.get(c, "") for c in cols] + [_now(), _now()]
        sql = "INSERT INTO marriage_return ({}, created_at, updated_at) VALUES ({})".format(
            ", ".join(cols), placeholders
        )
        cur = self.conn.execute(sql, values)
        marriage_id = cur.lastrowid
        self._insert_party(marriage_id, "A", party_a)
        self._insert_party(marriage_id, "B", party_b)
        self.conn.commit()
        return marriage_id

    def _insert_party(self, marriage_id, side, party):
        cols = ["marriage_id"] + MARRIAGE_PARTY_FIELDS
        data = dict(party)
        data["side"] = side
        data["marriage_id"] = marriage_id
        placeholders = ", ".join(["?"] * len(cols))
        values = [data.get(c, "") for c in cols]
        self.conn.execute(
            "INSERT INTO marriage_party ({}) VALUES ({})".format(
                ", ".join(cols), placeholders
            ),
            values,
        )

    def update_marriage(self, rec_id, data, party_a, party_b):
        assignments = ", ".join("{}=?".format(c) for c in MARRIAGE_FIELDS)
        values = [data.get(c, "") for c in MARRIAGE_FIELDS] + [_now(), rec_id]
        self.conn.execute(
            "UPDATE marriage_return SET {}, updated_at=? WHERE id=?".format(assignments),
            values,
        )
        # Simplest correct approach: replace the two child rows.
        self.conn.execute("DELETE FROM marriage_party WHERE marriage_id=?", (rec_id,))
        self._insert_party(rec_id, "A", party_a)
        self._insert_party(rec_id, "B", party_b)
        self.conn.commit()

    def get_marriage(self, rec_id):
        row = self.conn.execute(
            "SELECT * FROM marriage_return WHERE id=?", (rec_id,)
        ).fetchone()
        marriage = self._row_to_dict(row)
        if marriage is None:
            return None
        parties = self.conn.execute(
            "SELECT * FROM marriage_party WHERE marriage_id=? ORDER BY side", (rec_id,)
        ).fetchall()
        marriage["parties"] = {}
        for p in parties:
            p = dict(p)
            marriage["parties"][p["side"]] = p
        return marriage

    def delete_marriage(self, rec_id):
        # ON DELETE CASCADE removes the party rows.
        self.conn.execute("DELETE FROM marriage_return WHERE id=?", (rec_id,))
        self.conn.commit()

    def search_marriage(self, query=""):
        like = "%{}%".format(query.strip())
        rows = self.conn.execute(
            """SELECT mr.* FROM marriage_return mr
               LEFT JOIN marriage_party mp ON mp.marriage_id = mr.id
               WHERE mr.number LIKE ? OR mr.serial_no LIKE ?
                  OR mr.when_married LIKE ? OR mp.name_of_party LIKE ?
                  OR mp.surname LIKE ?
               GROUP BY mr.id
               ORDER BY mr.id DESC""",
            (like, like, like, like, like),
        ).fetchall()
        return self._rows_to_dicts(rows)

    # ================================================================== #
    # BAPTISM
    # ================================================================== #
    def insert_baptism(self, data):
        cols = BAPTISM_FIELDS
        placeholders = ", ".join(["?"] * (len(cols) + 2))
        values = [data.get(c, "") for c in cols] + [_now(), _now()]
        sql = "INSERT INTO baptism ({}, created_at, updated_at) VALUES ({})".format(
            ", ".join(cols), placeholders
        )
        cur = self.conn.execute(sql, values)
        self.conn.commit()
        return cur.lastrowid

    def update_baptism(self, rec_id, data):
        assignments = ", ".join("{}=?".format(c) for c in BAPTISM_FIELDS)
        values = [data.get(c, "") for c in BAPTISM_FIELDS] + [_now(), rec_id]
        self.conn.execute(
            "UPDATE baptism SET {}, updated_at=? WHERE id=?".format(assignments),
            values,
        )
        self.conn.commit()

    def get_baptism(self, rec_id):
        row = self.conn.execute(
            "SELECT * FROM baptism WHERE id=?", (rec_id,)
        ).fetchone()
        return self._row_to_dict(row)

    def delete_baptism(self, rec_id):
        self.conn.execute("DELETE FROM baptism WHERE id=?", (rec_id,))
        self.conn.commit()

    def search_baptism(self, query=""):
        like = "%{}%".format(query.strip())
        rows = self.conn.execute(
            """SELECT * FROM baptism
               WHERE christian_name LIKE ? OR surname_former_name LIKE ?
                  OR number LIKE ? OR when_baptized LIKE ?
               ORDER BY id DESC""",
            (like, like, like, like),
        ).fetchall()
        return self._rows_to_dicts(rows)
