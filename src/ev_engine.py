"""Motor de EV: remove o vig da casa de referência e calcula o valor esperado.

Método: devig multiplicativo. As probabilidades implícitas (1/odd) da casa
sharp são normalizadas para somar 1, o que remove a margem embutida e produz
a probabilidade "justa" de cada resultado. O EV de uma odd de casa soft é
então: EV = prob_justa * odd - 1.
"""
from collections import defaultdict


def devig_multiplicative(odds):
    """Recebe as odds decimais de todos os resultados de um mercado
    e devolve as probabilidades justas (sem a margem da casa)."""
    implied = [1.0 / o for o in odds]
    total = sum(implied)
    return [p / total for p in implied]


def overround(odds):
    """Margem embutida no conjunto de odds (ex.: 0.05 = 5% de vig)."""
    return sum(1.0 / o for o in odds) - 1.0


def _group_by_event(rows):
    events = defaultdict(list)
    for row in rows:
        events[row["event_id"]].append(row)
    return events


def find_value_bets(rows, sharp_key, min_ev=0.0):
    """Varre a coleta mais recente e retorna as oportunidades EV+.

    rows: linhas do banco (dicts) de um mesmo snapshot.
    Retorna lista de dicts ordenada por EV decrescente. Eventos sem odds
    da casa sharp são ignorados (sem referência não há como estimar EV).
    """
    opportunities = []
    for event_rows in _group_by_event(rows).values():
        sharp_rows = [r for r in event_rows if r["bookmaker_key"] == sharp_key]
        if len(sharp_rows) < 2:
            continue

        fair_probs = devig_multiplicative([r["price"] for r in sharp_rows])
        fair_by_outcome = {
            r["outcome_name"]: p for r, p in zip(sharp_rows, fair_probs)
        }
        vig = overround([r["price"] for r in sharp_rows])

        for row in event_rows:
            if row["bookmaker_key"] == sharp_key:
                continue
            fair_prob = fair_by_outcome.get(row["outcome_name"])
            if fair_prob is None:
                continue
            ev = fair_prob * row["price"] - 1.0
            if ev >= min_ev:
                opportunities.append(
                    {
                        "home_team": row["home_team"],
                        "away_team": row["away_team"],
                        "commence_time": row["commence_time"],
                        "outcome": row["outcome_name"],
                        "bookmaker": row["bookmaker_title"],
                        "odd": row["price"],
                        "fair_prob": fair_prob,
                        "fair_odd": 1.0 / fair_prob,
                        "ev": ev,
                        "sharp_vig": vig,
                    }
                )

    opportunities.sort(key=lambda o: o["ev"], reverse=True)
    return opportunities
