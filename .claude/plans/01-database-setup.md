# Plan: Database Setup (Spec 01)

## Context

Spense Tracker ("Spendly") currently has only `app.py` — a Streamlit scaffold whose
data functions (`fetch_expenses`, `add_expense`, `fetch_summary`) return hard-coded
sample data. There is no persistence layer.

Spec `.claude/specs/01-database-setup.md` calls for a spec-driven, ORM-free SQLite
layer in a new `database/db.py` module: a connection helper, idempotent schema
creation, and one-time seed data (1 demo user + 8 expenses). This is the foundation
that later route/UI work will build on. This task delivers **only** the database layer
plus a startup hook — the `/health`, `/expenses` etc. routes in the spec are explicitly
"assumed" / out of scope.

**Decisions confirmed with user:**
- Startup init (`init_db()` + `seed_db()`) wires into `app.py`'s `main()`.
- Werkzeug will be installed and a `requirements.txt` created to pin deps.

**Verified environment facts:**
- Python 3.12.4, sqlite3 3.45.3 (CHECK + FK + `ON DELETE CASCADE` all supported).
- `database/` does not exist yet; no `requirements.txt` exists.
- Werkzeug is **not** installed.
- `.gitignore` already ignores `*.db`, so `spendly.db` won't be committed (good).

## Files to change

- **`database/__init__.py`** (new) — empty, makes `database` an importable package.
- **`database/db.py`** (new) — the core module (see below).
- **`app.py`** (modify) — call `init_db()` + `seed_db()` once on startup.
- **`requirements.txt`** (new) — pin `streamlit` and `werkzeug`.

## `database/db.py` design

Authoritative DDL, category list, and seed rows come verbatim from the spec
(§4.3 DDL, §8 categories, §5.3 seed set). Key constants/functions:

- `DB_PATH` — `spendly.db` resolved relative to the **project root**, not CWD.
  Use `pathlib.Path(__file__).resolve().parent.parent / "spendly.db"` so it works
  regardless of where the process is launched from.

- **`get_db()`** — opens `sqlite3.connect(DB_PATH)`, sets
  `conn.row_factory = sqlite3.Row`, executes `PRAGMA foreign_keys = ON;` on the
  connection, returns it. (FK pragma is per-connection in SQLite, so it must run
  here every time.)

- **`init_db()`** — obtains a connection via `get_db()`, runs both
  `CREATE TABLE IF NOT EXISTS` statements (exact DDL from spec §4.3) plus the two
  recommended indexes (`idx_expenses_user_id`, `idx_expenses_date`), commits, closes.
  Idempotent.

- **`seed_db()`** — obtains a connection via `get_db()`. Guard:
  `SELECT COUNT(*) FROM users` → if `> 0`, return early (prevents duplicate seeds).
  Otherwise:
  - Insert demo user (`name='Demo User'`, `email='demo@spendly.com'`,
    `password_hash=generate_password_hash('demo123')`,
    `created_at=datetime.now(timezone.utc).isoformat()`), capture
    `cursor.lastrowid` as `user_id`.
  - Insert the 8 sample expenses from spec §5.3 via `executemany` with parameterized
    rows, each linked to `user_id`. Dates are `YYYY-MM-DD`; `created_at` is an ISO
    timestamp. Note spec category spelling is intentionally `'Shoppping'` (triple-p) —
    must match the CHECK constraint exactly.
  - Commit, close.

Implementation rules (from spec §9): no ORM, **parameterized queries only** (`?`
placeholders — never f-strings/`.format`/`%`), `PRAGMA foreign_keys = ON` on every
connection, amounts as `REAL`, password via
`from werkzeug.security import generate_password_hash`. Let exceptions propagate
(don't swallow) per §11.

Optional convenience: an `if __name__ == "__main__":` block calling
`init_db(); seed_db()` so the module can be run standalone for verification.

## `app.py` change

At the start of `main()` (before `set_page_config`/rendering), import and call:

```python
from database.db import init_db, seed_db
init_db()
seed_db()
```

Both are idempotent/guarded, so calling on every Streamlit rerun is safe. (Leave the
existing placeholder `fetch_*`/`add_expense` stubs untouched — wiring the UI to the DB
is a later spec.)

## requirements.txt

Pin the two runtime deps actually used:

```
streamlit
werkzeug
```

(Versions can be left unpinned for now, or pinned to the installed versions after
install — installer's choice.)

## Implementation steps

1. `pip install werkzeug` (streamlit already installed).
2. Create `database/__init__.py` (empty).
3. Create `database/db.py` per the design above.
4. Create `requirements.txt`.
5. Modify `app.py` `main()` to call `init_db()` + `seed_db()`.

## Verification

1. **Standalone run:** `python -m database.db` — should create `spendly.db` with no
   error, and be safe to run twice (no duplicate seed).
2. **Schema check:**
   `python -c "import sqlite3,pprint; c=sqlite3.connect('spendly.db'); pprint.pprint(c.execute('SELECT name FROM sqlite_master WHERE type=\"table\"').fetchall())"`
   → expect `users` and `expenses`.
3. **Seed idempotency:** run `seed_db()` twice; `SELECT COUNT(*) FROM users` stays `1`
   and `SELECT COUNT(*) FROM expenses` stays `8`.
4. **FK enforcement:** with `PRAGMA foreign_keys=ON`, inserting an expense with a
   non-existent `user_id` raises `sqlite3.IntegrityError: FOREIGN KEY constraint failed`.
5. **Unique email:** inserting a second `demo@spendly.com` raises
   `UNIQUE constraint failed: users.email`.
6. **CHECK constraint:** inserting an expense with category `'Groceries'` (not in list)
   raises `CHECK constraint failed`.
7. **App startup:** `streamlit run app.py` launches without error and `spendly.db`
   exists in project root.

## Definition of Done (from spec §12)

- `spendly.db` created on startup; both tables exist with correct schema + constraints.
- Demo user exists with hashed password; 8 expenses across categories.
- No duplicate seed data on repeated runs.
- FK enforcement works; all queries parameterized; app starts without errors.
