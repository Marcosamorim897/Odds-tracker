"""Persistência das odds coletadas.

Usa Postgres (Neon) quando DATABASE_URL está definida — caso do deploy no
Render, onde o disco é efêmero. Localmente, sem essa variável, cai para
SQLite em data/odds.db.
"""
from sqlalchemy import create_engine, text

from src.config import DATABASE_URL, DATA_DIR, DB_PATH

IS_POSTGRES = bool(DATABASE_URL)

if IS_POSTGRES:
    ENGINE = create_engine(DATABASE_URL, pool_pre_ping=True)
else:
    DATA_DIR.mkdir(exist_ok=True)
    ENGINE = create_engine(f"sqlite:///{DB_PATH}")

_SCHEMA_POSTGRES = """
CREATE TABLE IF NOT EXISTS odds_snapshots (
    id SERIAL PRIMARY KEY,
    fetched_at TEXT NOT NULL,
    event_id TEXT NOT NULL,
    commence_time TEXT NOT NULL,
    home_team TEXT NOT NULL,
    away_team TEXT NOT NULL,
    bookmaker_key TEXT NOT NULL,
    bookmaker_title TEXT NOT NULL,
    outcome_name TEXT NOT NULL,
    price DOUBLE PRECISION NOT NULL
);
"""

_SCHEMA_SQLITE = """
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
"""

_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_snapshots_fetched ON odds_snapshots (fetched_at)",
    "CREATE INDEX IF NOT EXISTS idx_snapshots_event ON odds_snapshots (event_id)",
]


def _init_schema():
    with ENGINE.begin() as conn:
        conn.execute(text(_SCHEMA_POSTGRES if IS_POSTGRES else _SCHEMA_SQLITE))
        for stmt in _INDEXES:
            conn.execute(text(stmt))


_init_schema()


def save_rows(rows):
    """Grava um lote de linhas de odds (todas com o mesmo fetched_at)."""
    if not rows:
        return
    with ENGINE.begin() as conn:
        conn.execute(
            text(
                """INSERT INTO odds_snapshots
                   (fetched_at, event_id, commence_time, home_team, away_team,
                    bookmaker_key, bookmaker_title, outcome_name, price)
                   VALUES (:fetched_at, :event_id, :commence_time, :home_team,
                           :away_team, :bookmaker_key, :bookmaker_title,
                           :outcome_name, :price)"""
            ),
            rows,
        )


def load_latest_snapshot():
    """Retorna as linhas da coleta mais recente como lista de dicts."""
    with ENGINE.connect() as conn:
        result = conn.execute(
            text(
                """SELECT * FROM odds_snapshots
                   WHERE fetched_at = (SELECT MAX(fetched_at) FROM odds_snapshots)"""
            )
        )
        return [dict(row) for row in result.mappings().all()]
