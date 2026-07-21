"""Registro e apuração das apostas do usuário (gestão de banca)."""
from datetime import datetime, timezone

from src.database import get_connection

BETS_SCHEMA = """
CREATE TABLE IF NOT EXISTS bets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL,
    event TEXT NOT NULL,
    market TEXT NOT NULL,
    bookmaker TEXT,
    odd REAL NOT NULL,
    units REAL NOT NULL,
    stake REAL NOT NULL,
    status TEXT NOT NULL DEFAULT 'Pendente',
    ev_pct REAL
);
"""

STATUSES = ["Pendente", "Ganha", "Perdida", "Anulada"]


def _conn():
    conn = get_connection()
    conn.executescript(BETS_SCHEMA)
    return conn


def add_bet(event, market, bookmaker, odd, units, stake, ev_pct=None):
    with _conn() as conn:
        conn.execute(
            """INSERT INTO bets
               (created_at, event, market, bookmaker, odd, units, stake, ev_pct)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                datetime.now(timezone.utc).isoformat(),
                event, market, bookmaker, float(odd), float(units),
                float(stake), ev_pct,
            ),
        )


def load_bets():
    with _conn() as conn:
        cur = conn.execute("SELECT * FROM bets ORDER BY created_at DESC")
        return [dict(row) for row in cur.fetchall()]


def update_status(bet_id, status):
    if status not in STATUSES:
        raise ValueError(f"Status inválido: {status}")
    with _conn() as conn:
        conn.execute("UPDATE bets SET status = ? WHERE id = ?", (status, bet_id))


def delete_bet(bet_id):
    with _conn() as conn:
        conn.execute("DELETE FROM bets WHERE id = ?", (bet_id,))


def profit(bet):
    """Lucro/prejuízo em R$ de uma aposta; None se ainda pendente."""
    if bet["status"] == "Ganha":
        return bet["stake"] * (bet["odd"] - 1.0)
    if bet["status"] == "Perdida":
        return -bet["stake"]
    if bet["status"] == "Anulada":
        return 0.0
    return None


def summary(bets):
    """Métricas agregadas das apostas já resolvidas."""
    settled = [b for b in bets if b["status"] in ("Ganha", "Perdida")]
    staked = sum(b["stake"] for b in settled)
    total_profit = sum(profit(b) for b in settled)
    wins = sum(1 for b in settled if b["status"] == "Ganha")
    return {
        "n_total": len(bets),
        "n_pending": sum(1 for b in bets if b["status"] == "Pendente"),
        "n_settled": len(settled),
        "staked": staked,
        "profit": total_profit,
        "roi": (total_profit / staked) if staked else 0.0,
        "hit_rate": (wins / len(settled)) if settled else 0.0,
    }
