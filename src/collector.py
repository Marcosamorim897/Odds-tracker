"""Coleta odds na The Odds API e grava no banco local."""
from datetime import datetime, timezone

import requests

from src import database
from src.config import API_BASE_URL, API_KEY, MARKETS, ODDS_FORMAT, REGIONS, SPORT_KEY


class CollectorError(Exception):
    pass


def fetch_odds():
    """Busca as odds atuais do campeonato configurado.

    Retorna (eventos, créditos_restantes).
    """
    if not API_KEY:
        raise CollectorError(
            "ODDS_API_KEY não configurada. Copie .env.example para .env "
            "e cole sua chave da The Odds API."
        )

    url = f"{API_BASE_URL}/sports/{SPORT_KEY}/odds"
    params = {
        "apiKey": API_KEY,
        "regions": REGIONS,
        "markets": MARKETS,
        "oddsFormat": ODDS_FORMAT,
    }
    resp = requests.get(url, params=params, timeout=30)
    if resp.status_code == 401:
        raise CollectorError("Chave da API inválida (401). Confira o valor no .env.")
    if resp.status_code == 429:
        raise CollectorError("Cota de créditos da API esgotada (429).")
    resp.raise_for_status()

    remaining = resp.headers.get("x-requests-remaining")
    return resp.json(), remaining


def flatten_events(events, fetched_at):
    rows = []
    for event in events:
        for bookmaker in event.get("bookmakers", []):
            for market in bookmaker.get("markets", []):
                if market.get("key") != "h2h":
                    continue
                for outcome in market.get("outcomes", []):
                    rows.append(
                        {
                            "fetched_at": fetched_at,
                            "event_id": event["id"],
                            "commence_time": event["commence_time"],
                            "home_team": event["home_team"],
                            "away_team": event["away_team"],
                            "bookmaker_key": bookmaker["key"],
                            "bookmaker_title": bookmaker["title"],
                            "outcome_name": outcome["name"],
                            "price": float(outcome["price"]),
                        }
                    )
    return rows


def collect():
    """Executa uma coleta completa. Retorna (n_jogos, n_linhas, créditos_restantes)."""
    events, remaining = fetch_odds()
    fetched_at = datetime.now(timezone.utc).isoformat()
    rows = flatten_events(events, fetched_at)
    if rows:
        database.save_rows(rows)
    return len(events), len(rows), remaining


if __name__ == "__main__":
    n_events, n_rows, credits = collect()
    print(f"Coleta ok: {n_events} jogos, {n_rows} linhas de odds gravadas.")
    print(f"Créditos restantes na The Odds API: {credits}")
