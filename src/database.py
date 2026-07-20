"""Persistência das odds coletadas em SQLite."""
import sqlite3
from src.config import DATA_DIR, DB_PATH

SCHEMA = """
CREATE TABLE IF NOT EXISTS odds_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fetched_at TEXT NOT NULL,
    event_id TEXT NOT NULL,
    commence_time TEXT NOT NULL,
    home_team TEXT NOT NULL,
    away_team TEXT NOT NULL,
    bookmaker_key TEXT NOT NULL,
    bookmaker_title TEXT NOT NULL,
    outcome_name TEXT NOT NULL,
    price REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_snapshots_fetched ON odds_snapshots (fetched_at);
CREATE INDEX IF NOT EXISTS idx_snapshots_event ON odds_snapshots (event_id);
"""


def get_connection():
    DATA_DIR.mkdir(exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    return conn


def save_rows(rows):
    """Grava um lote de linhas de odds (todas com o mesmo fetched_at)."""
    with get_connection() as conn:
        conn.executemany(
            """INSERT INTO odds_snapshots
               (fetched_at, event_id, commence_time, home_team, away_team,
                bookmaker_key, bookmaker_title, outcome_name, price)
               VALUES (:fetched_at, :event_id, :commence_time, :home_team,
                       :away_team, :bookmaker_key, :bookmaker_title,
                       :outcome_name, :price)""",
            rows,
        )


def load_latest_snapshot():
    """Retorna as linhas da coleta mais recente como lista de dicts."""
    with get_connection() as conn:
        cur = conn.execute(
            """SELECT * FROM odds_snapshots
               WHERE fetched_at = (SELECT MAX(fetched_at) FROM odds_snapshots)"""
        )
        return [dict(row) for row in cur.fetchall()]
