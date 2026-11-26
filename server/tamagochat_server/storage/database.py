import sqlite3

SCHEMA = """
CREATE TABLE IF NOT EXISTS cats(
    id TEXT PRIMARY KEY, secret_hash TEXT NOT NULL, name TEXT, version TEXT,
    stats TEXT, state TEXT, accept INTEGER DEFAULT 1, first_seen REAL, last_seen REAL);
CREATE TABLE IF NOT EXISTS messages(
    id INTEGER PRIMARY KEY AUTOINCREMENT, cat_id TEXT NOT NULL, kind TEXT NOT NULL,
    payload TEXT NOT NULL, created REAL NOT NULL, fetched REAL, delivered REAL);
CREATE INDEX IF NOT EXISTS msg_cat ON messages(cat_id, delivered);
CREATE TABLE IF NOT EXISTS replies(
    id INTEGER PRIMARY KEY AUTOINCREMENT, cat_id TEXT NOT NULL, text TEXT NOT NULL,
    created REAL NOT NULL, read INTEGER DEFAULT 0);
CREATE TABLE IF NOT EXISTS sessions(token_hash TEXT PRIMARY KEY, expires REAL NOT NULL);
"""

# colonnes ajoutées après coup : créées si la base est plus ancienne
LATER_COLUMNS = (("settings", "TEXT"), ("allow_settings", "INTEGER"), ("phrases", "TEXT"),
                 ("phrases_at", "REAL"))


def connect(path):
    con = sqlite3.connect(path)
    con.row_factory = sqlite3.Row
    con.executescript(SCHEMA)
    cols = {r["name"] for r in con.execute("PRAGMA table_info(cats)")}
    for col, typ in LATER_COLUMNS:
        if col not in cols:
            con.execute(f"ALTER TABLE cats ADD COLUMN {col} {typ}")
    con.execute("PRAGMA journal_mode=WAL")
    return con
