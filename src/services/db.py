"""SQLite database connection and initialization (QSPARK 11-table schema)."""

import sqlite3
from contextlib import contextmanager
from pathlib import Path

SCHEMA_PATH = Path(__file__).resolve().parents[2] / "schema.sql"


def get_connection(db_path: str) -> sqlite3.Connection:
    """Create a SQLite connection with row factory and foreign keys enabled."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


@contextmanager
def transaction(db_path: str):
    """Context manager using BEGIN IMMEDIATE for concurrency-safe writes."""
    conn = get_connection(db_path)
    try:
        conn.execute("BEGIN IMMEDIATE")
        yield conn
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise
    finally:
        conn.close()


def init_db(db_path: str) -> None:
    """Initialize the database from schema.sql (single source of truth).

    If an incompatible legacy schema is detected, the old database file is
    preserved by renaming it aside (never deleted) and a fresh schema is created.
    """
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)

    p = Path(db_path)
    if p.exists() and p.stat().st_size > 0:
        try:
            probe = sqlite3.connect(db_path)
            try:
                cols = [r[1] for r in probe.execute("PRAGMA table_info(users)").fetchall()]
            finally:
                probe.close()
            if cols and "account_status" not in cols:
                legacy = p.with_name(
                    p.stem + ".legacy_"
                    + __import__("datetime").datetime.now().strftime("%Y%m%d_%H%M%S")
                    + p.suffix
                )
                p.rename(legacy)
                print(f"[migration] Legacy schema moved to {legacy.name}; creating fresh schema.")
        except sqlite3.DatabaseError:
            pass

    schema_sql = SCHEMA_PATH.read_text(encoding="utf-8")
    conn = get_connection(db_path)
    try:
        conn.executescript(schema_sql)
    finally:
        conn.close()