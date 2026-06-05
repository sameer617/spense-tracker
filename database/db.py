"""
Spendly — SQLite database layer (spec 01).

A small, ORM-free persistence layer for the expense tracker:

    get_db()   -> open a connection (row access + FK enforcement)
    init_db()  -> create the schema (idempotent)
    seed_db()  -> insert demo data exactly once

Implementation rules (spec §9):
    - No ORM (raw sqlite3 only).
    - Parameterized queries only — never string-format SQL.
    - `PRAGMA foreign_keys = ON` on every connection (it is per-connection).
    - Amounts stored as REAL; dates as YYYY-MM-DD.
    - Passwords hashed with werkzeug.security.generate_password_hash.
"""

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from werkzeug.security import generate_password_hash

# `spendly.db` lives in the project root, resolved relative to this file so it
# is stable regardless of the process's current working directory.
DB_PATH = Path(__file__).resolve().parent.parent / "spendly.db"

# Fixed, allowed expense categories (spec §8). Kept here for reference; the
# database enforces them via the CHECK constraint in the DDL below.
CATEGORIES = (
    "Food",
    "Transport",
    "Bills",
    "Health",
    "Entertainment",
    "Shoppping",  # NOTE: spelling is intentional and must match the CHECK constraint.
    "Other",
)

# Authoritative DDL (spec §4.3) plus the recommended indexes (spec §4.4).
_SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS expenses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    amount REAL NOT NULL,
    category TEXT NOT NULL CHECK (category IN (
        'Food',
        'Transport',
        'Bills',
        'Health',
        'Entertainment',
        'Shoppping',
        'Other'
    )),
    location TEXT,
    date TEXT NOT NULL,
    description TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_expenses_user_id ON expenses(user_id);
CREATE INDEX IF NOT EXISTS idx_expenses_date ON expenses(date);
"""

# Demo user (spec §5.3).
_DEMO_USER = {
    "name": "Demo User",
    "email": "demo@spendly.com",
    "password": "demo123",
}

# Sample expenses (spec §5.3): (amount, category, location, date, description).
# At least one row per category, dates spread across the month.
_SEED_EXPENSES = (
    (12.50, "Food", "Downtown", "2026-06-02", "Lunch"),
    (3.25, "Transport", "LA Metro", "2026-06-03", "Bus fare"),
    (79.99, "Bills", "Online", "2026-06-05", "Internet bill"),
    (24.00, "Health", "CVS", "2026-06-08", "Pharmacy"),
    (15.00, "Entertainment", "AMC", "2026-06-12", "Movie ticket"),
    (45.90, "Shoppping", "Target", "2026-06-15", "Household items"),
    (9.99, "Other", "Online", "2026-06-18", "Cloud storage"),
    (28.75, "Food", "Koreatown", "2026-06-22", "Dinner"),
)


def _now_iso() -> str:
    """Current UTC time as an ISO-8601 timestamp string for `created_at`."""
    return datetime.now(timezone.utc).isoformat()


def get_db() -> sqlite3.Connection:
    """Open a connection to spendly.db with dict-like rows and FK enforcement.

    The `PRAGMA foreign_keys = ON` is applied here because it is a per-connection
    setting in SQLite — it must be re-enabled every time a connection is opened.
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def init_db() -> None:
    """Create both tables (and indexes) if they don't exist. Idempotent."""
    conn = get_db()
    try:
        conn.executescript(_SCHEMA)
        conn.commit()
    finally:
        conn.close()


def seed_db() -> None:
    """Insert demo data once. No-op if the users table is already populated."""
    conn = get_db()
    try:
        existing = conn.execute("SELECT COUNT(*) FROM users;").fetchone()[0]
        if existing:
            return  # Already seeded — avoid duplicate inserts.

        password_hash = generate_password_hash(_DEMO_USER["password"])
        cursor = conn.execute(
            "INSERT INTO users (name, email, password_hash, created_at) "
            "VALUES (?, ?, ?, ?);",
            (_DEMO_USER["name"], _DEMO_USER["email"], password_hash, _now_iso()),
        )
        user_id = cursor.lastrowid

        created_at = _now_iso()
        rows = [
            (user_id, amount, category, location, date, description, created_at)
            for (amount, category, location, date, description) in _SEED_EXPENSES
        ]
        conn.executemany(
            "INSERT INTO expenses "
            "(user_id, amount, category, location, date, description, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?);",
            rows,
        )
        conn.commit()
    finally:
        conn.close()


if __name__ == "__main__":
    # Allow running the module standalone to create + seed the database.
    init_db()
    seed_db()
    print(f"Database ready at {DB_PATH}")
