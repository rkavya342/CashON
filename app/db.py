"""
app/db.py — SQLite database helpers.

We use raw sqlite3 (no ORM) to keep things simple and educational.
Flask's 'g' object stores the per-request connection so we open it once
per request and close it cleanly at the end.
"""

import sqlite3
import os
from flask import g, current_app


def get_db():
    """
    Return a database connection for the current request.
    Creates a new connection if one doesn't already exist in 'g'.
    sqlite3.Row lets us access columns by name: row["email"].
    """
    if "db" not in g:
        g.db = sqlite3.connect(
            current_app.config["DATABASE"],
            detect_types=sqlite3.PARSE_DECLTYPES,
        )
        g.db.row_factory = sqlite3.Row      # named column access
        g.db.execute("PRAGMA foreign_keys = ON")  # enforce FK constraints
    return g.db


def init_db(app=None):
    """
    Read schema.sql and execute it against the database.
    Called by 'flask init-db' or seed.py.
    """
    if app:
        db_path = app.config["DATABASE"]
        schema_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "schema.sql")
    else:
        db_path = current_app.config["DATABASE"]
        schema_path = os.path.join(current_app.root_path, "..", "schema.sql")

    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    db = sqlite3.connect(db_path)
    db.execute("PRAGMA foreign_keys = ON")

    with open(schema_path, "r", encoding="utf-8") as f:
        db.executescript(f.read())

    db.commit()
    db.close()
