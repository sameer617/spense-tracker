<aside>
💸

**Goal:** Provide a spec-driven SQLite database layer for an expense tracker with a deterministic schema, safe initialization, and one-time seed data.

</aside>

## 1. Overview

Spendly stores:

- **Users** (authentication identity)
- **Expenses** (money spent by a user)

Implementation constraints:

- **SQLite** database file: `spendly.db` in project root
- **No ORM** (no SQLAlchemy)
- **Parameterized SQL only** (no string formatting)
- Enable **foreign key enforcement** on every connection: `PRAGMA foreign_keys = ON;`
- **Amounts stored as REAL**
- Passwords hashed with Werkzeug: `generate_password_hash`
- Dates use **YYYY-MM-DD** consistently

## 2. Depends

- Depends upon nothing.

## 3. Routes

These are the minimal routes assumed by this spec (exact UI/JSON responses can evolve):

- `GET /health`
    - Returns `{ "status": "ok" }` if app is running.
- `GET /expenses`
    - Lists expenses for the demo user (or future: authenticated user).
- `POST /expenses`
    - Creates a new expense (requires valid category; date format YYYY-MM-DD).
- `GET /users`
    - Debug/demo only: list users (do not return password hashes).
- `POST /users`
    - Creates a user with unique email and hashed password.

> Authentication is out of scope for this database spec, but the schema supports it via `password_hash`.
> 

## 4. Database schema

### 4.1 Table: `users`

Columns:

- `id` INTEGER PRIMARY KEY AUTOINCREMENT
- `name` TEXT NOT NULL
- `email` TEXT NOT NULL UNIQUE
- `password_hash` TEXT NOT NULL
- `created_at` TEXT NOT NULL (ISO timestamp string)

Constraints:

- Unique email enforced via `UNIQUE(email)`.

### 4.2 Table: `expenses`

Columns:

- `id` INTEGER PRIMARY KEY AUTOINCREMENT
- `user_id` INTEGER NOT NULL (FK → `users.id`)
- `amount` REAL NOT NULL
- `category` TEXT NOT NULL (fixed allowed list; enforced via CHECK)
- `location` TEXT
- `date` TEXT NOT NULL (YYYY-MM-DD)
- `description` TEXT
- `created_at` TEXT NOT NULL (ISO timestamp string)

Constraints:

- `FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE`
- Category allowed values (exact strings):
    - `Food`
    - `Transport`
    - `Bills`
    - `Health`
    - `Entertainment`
    - `Shoppping`
    - `Other`

Recommended SQLite DDL (authoritative):

```sql
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
```

Indexes (optional but recommended):

- `CREATE INDEX IF NOT EXISTS idx_expenses_user_id ON expenses(user_id);`
- `CREATE INDEX IF NOT EXISTS idx_expenses_date ON expenses(date);`

## 5. Functions to implement (`database/db.py`)

### 5.1 `get_db()`

Responsibilities:

- Opens connection to `spendly.db` in project root.
- Enables **dictionary-like row access**: `conn.row_factory = sqlite3.Row`.
- Enables FK enforcement **every time**: execute `PRAGMA foreign_keys = ON;`.
- Returns a working connection object.

### 5.2 `init_db()`

Responsibilities:

- Creates both tables with `CREATE TABLE IF NOT EXISTS`.
- Safe to call multiple times (idempotent).
- Ensures schema is ready before app routes are used.

Key requirements:

- Must use the same connection settings as `get_db()` (row_factory + FK pragma).
- Should commit DDL changes.

### 5.3 `seed_db()`

Responsibilities:

- Prevents duplicate inserts on repeated runs.
- Checks if `users` table already contains data; if yes, return early.
- Inserts one demo user:
    - name: `Demo User`
    - email: `demo@spendly.com`
    - password: `demo123` (hashed using `generate_password_hash`)
- Inserts **8 sample expenses** linked to the demo user.
    - Must cover multiple categories, dates spread across a month.
    - Include at least one expense per category (7 categories) + 1 extra in any category.

Seed data requirements:

- All inserts use parameterized queries.
- All dates are `YYYY-MM-DD`.

Suggested sample expenses (example set; can be used verbatim):

1. Food — 12.50 — “Lunch” — 2026-06-02 — location “Downtown”
2. Transport — 3.25 — “Bus fare” — 2026-06-03 — location “LA Metro”
3. Bills — 79.99 — “Internet bill” — 2026-06-05 — location “Online”
4. Health — 24.00 — “Pharmacy” — 2026-06-08 — location “CVS”
5. Entertainment — 15.00 — “Movie ticket” — 2026-06-12 — location “AMC”
6. Shoppping — 45.90 — “Household items” — 2026-06-15 — location “Target”
7. Other — 9.99 — “Cloud storage” — 2026-06-18 — location “Online”
8. Food — 28.75 — “Dinner” — 2026-06-22 — location “Koreatown”

## 6. Startup initialization contract

On app startup (before any route handlers run):

1. Call `init_db()`
2. Call `seed_db()`

This guarantees:

- database file exists
- schema exists
- demo data exists once

## 7. Files to change

- `database/db.py`
- `app.py`

## 8. Categories (Fixed List)

Use **exactly** these values:

- Food
- Transport
- Bills
- Health
- Entertainment
- Shoppping
- Other

## 9. Rules for implementation

- No ORMs (no SQLAlchemy)
- Parameterized queries only (no SQL string formatting)
- Always enable: `PRAGMA foreign_keys = ON`
- Amount stored as `REAL`
- Password hashing:
    - `from werkzeug.security import generate_password_hash`
- `seed_db()` must prevent duplicate inserts
- Dates must be `YYYY-MM-DD` consistently

## 10. Expected behavior

- `get_db()` returns a working connection with:
    - dictionary-like row access (`sqlite3.Row`)
    - FK enforcement enabled
- `init_db()`:
    - creates tables safely
    - does not fail on repeated runs
- `seed_db()`:
    - inserts demo data only once
    - does not duplicate records on multiple runs
- Database enforces:
    - unique email constraint
    - valid foreign key relationships

## 11. Error handling expectations

- Inserting duplicate email → fails with `UNIQUE constraint failed: users.email`
- Inserting expense with invalid `user_id` → fails with `FOREIGN KEY constraint failed`
- Invalid queries → raise clear Python exceptions (do not silently swallow)

## 12. Definition of Done

- `spendly.db` file is created on app startup
- Both tables exist with correct schema + constraints
- Demo user exists with hashed password
- 8 sample expenses exist across categories
- No duplicate seed data on repeated runs
- App starts without errors
- Foreign key enforcement works
- All queries use parameterized SQL