"""Dashboard do odds-tracker: comparador de odds e oportunidades EV+."""
from datetime import datetime

import pandas as pd
import streamlit as st

from src import collector, database
from src.config import SHARP_BOOKMAKER

st.set_page_config(page_title="Odds Tracker", page_icon="⚽", layout="wide")

st.title("⚽ Odds Tracker — Brasileirão Série A")
st.caption(
    "Comparador de odds e detector de EV+ (referência de mercado: "
    f"{SHARP_BOOKMAKER}). Ferramenta analítica — a decisão de apostar é sempre sua."
)


def format_kickoff(iso_str):
    try:
        dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00")).astimezone()
        return dt.strftime("%d/%m %H:%M")
    except (ValueError, AttributeError):
        return iso_str


with st.sidebar:
    st.header("Coleta")
    if st.button("🔄 Atualizar odds agora", use_container_width=True):
        with st.spinner("Consultando a The Odds API..."):
            try:
                n_events, n_rows, credits = collector.collect()
                st.success(f"{n_events} jogos coletados ({n_rows} odds).")
                if credits is not None:
                    st.info(f"Créditos restantes no mês: {credits}")
            except collector.CollectorError as exc:
                st.error(str(exc))
            except Exception as exc:  # rede, timeout etc.
                st.error(f"Falha na coleta: {exc}")

    min_ev = st.slider(
        "EV mínimo (%)", min_value=0.0, max_value=10.0, value=1.0, step=0.5
    )

rows = database.load_latest_snapshot()

if not rows:
    st.info(
        "Nenhuma coleta no banco ainda. Configure sua chave no arquivo `.env` "
        "(use `.env.example` como modelo) e clique em **Atualizar odds agora** "
        "na barra lateral."
    )
    st.stop()

st.caption(f"Última coleta: {format_kickoff(rows[0]['fetched_at'])}")

tab_ev, tab_compare = st.tabs(["💰 Oportunidades EV+", "📊 Comparador de odds"])

with tab_ev:
    from src.ev_engine import find_value_bets

    opportunities = find_value_bets(rows, SHARP_BOOKMAKER, min_ev=min_ev / 100)
    if not opportunities:
        has_sharp = any(r["bookmaker_key"] == SHARP_BOOKMAKER for r in rows)
        if not has_sharp:
            st.warning(
                f"A coleta atual não trouxe odds da casa de referência "
                f"({SHARP_BOOKMAKER}), então não há como calcular EV. "
                "Isso pode acontecer quando a referência não cobre os jogos do momento."
            )
        else:
            st.info("Nenhuma oportunidade acima do EV mínimo configurado.")
    else:
        df = pd.DataFrame(opportunities)
        df["Jogo"] = df["home_team"] + " x " + df["away_team"]
        df["Início"] = df["commence_time"].map(format_kickoff)
        df["EV"] = (df["ev"] * 100).round(2).astype(str) + "%"
        df["Prob. justa"] = (df["fair_prob"] * 100).round(1).astype(str) + "%"
        df["Odd justa"] = df["fair_odd"].round(2)
        display = df[
            ["Jogo", "Início", "outcome", "bookmaker", "odd", "Odd justa",
             "Prob. justa", "EV"]
        ].rename(columns={"outcome": "Resultado", "bookmaker": "Casa", "odd": "Odd"})
        st.dataframe(display, use_container_width=True, hide_index=True)
        st.caption(
            "EV = probabilidade justa × odd − 1. Probabilidade justa estimada "
            "removendo o vig das odds da casa de referência (devig multiplicativo)."
        )

with tab_compare:
    df = pd.DataFrame(rows)
    df["Jogo"] = (
        df["home_team"] + " x " + df["away_team"]
        + " — " + df["commence_time"].map(format_kickoff)
    )
    game = st.selectbox("Escolha o jogo", sorted(df["Jogo"].unique()))
    game_df = df[df["Jogo"] == game]

    pivot = game_df.pivot_table(
        index="bookmaker_title", columns="outcome_name", values="price"
    )
    home = game_df["home_team"].iloc[0]
    away = game_df["away_team"].iloc[0]
    ordered = [c for c in [home, "Draw", away] if c in pivot.columns]
    pivot = pivot[ordered].rename(columns={"Draw": "Empate"})
    pivot.index.name = "Casa de aposta"

    st.dataframe(
        pivot.style.highlight_max(axis=0, props="background-color:#1b5e20;color:white")
        .format("{:.2f}"),
        use_container_width=True,
    )
    st.caption("Verde = melhor odd disponível para aquele resultado.")
