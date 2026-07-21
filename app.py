"""Dashboard do odds-tracker: comparador de odds, EV+ e planilha de apostas."""
from datetime import datetime

import pandas as pd
import streamlit as st

from src import bets, collector, database
from src.config import SHARP_BOOKMAKER
from src.ev_engine import find_value_bets

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

    st.header("Banca")
    unit_value = st.number_input(
        "Valor da unidade (R$)", min_value=1.0, value=10.0, step=1.0,
        help="Usado para sugerir o valor em R$ ao registrar apostas por unidade.",
    )

rows = database.load_latest_snapshot()
if rows:
    st.caption(f"Última coleta: {format_kickoff(rows[0]['fetched_at'])}")

NO_DATA_MSG = (
    "Nenhuma coleta no banco ainda. Configure sua chave no arquivo `.env` "
    "(use `.env.example` como modelo) e clique em **Atualizar odds agora** "
    "na barra lateral."
)

tab_ev, tab_compare, tab_sheet = st.tabs(
    ["💰 Oportunidades EV+", "📊 Comparador de odds", "📒 Planilha de apostas"]
)

with tab_ev:
    if not rows:
        st.info(NO_DATA_MSG)
    else:
        opportunities = find_value_bets(rows, SHARP_BOOKMAKER, min_ev=min_ev / 100)
        if not opportunities:
            has_sharp = any(r["bookmaker_key"] == SHARP_BOOKMAKER for r in rows)
            if not has_sharp:
                st.warning(
                    f"A coleta atual não trouxe odds da casa de referência "
                    f"({SHARP_BOOKMAKER}), então não há como calcular EV. "
                    "Isso pode acontecer quando a referência não cobre os "
                    "jogos do momento."
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
            ].rename(
                columns={"outcome": "Resultado", "bookmaker": "Casa", "odd": "Odd"}
            )
            st.dataframe(display, use_container_width=True, hide_index=True)
            st.caption(
                "EV = probabilidade justa × odd − 1. Probabilidade justa "
                "estimada removendo o vig das odds da casa de referência "
                "(devig multiplicativo)."
            )

with tab_compare:
    if not rows:
        st.info(NO_DATA_MSG)
    else:
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
            pivot.style.highlight_max(
                axis=0, props="background-color:#1b5e20;color:white"
            ).format("{:.2f}"),
            use_container_width=True,
        )
        st.caption("Verde = melhor odd disponível para aquele resultado.")

with tab_sheet:
    st.subheader("Registrar aposta")
    with st.form("add_bet", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            event = st.text_input("Jogo", placeholder="Flamengo x Palmeiras")
            market = st.text_input(
                "Mercado / Seleção", placeholder="1X2 — Flamengo"
            )
            bookmaker = st.text_input("Casa de aposta", placeholder="Bet365")
        with col2:
            odd = st.number_input("Odd", min_value=1.01, value=2.00, step=0.01)
            units = st.number_input(
                "Unidades", min_value=0.1, value=1.0, step=0.5
            )
            stake = st.number_input(
                "Valor (R$) — deixe 0 para usar unidades × valor da unidade",
                min_value=0.0, value=0.0, step=5.0,
            )
        ev_pct = st.number_input(
            "EV estimado no momento (%) — opcional",
            min_value=-50.0, max_value=100.0, value=0.0, step=0.5,
        )
        if st.form_submit_button("➕ Registrar"):
            if not event or not market:
                st.error("Preencha pelo menos o jogo e o mercado.")
            else:
                final_stake = stake if stake > 0 else units * unit_value
                bets.add_bet(
                    event, market, bookmaker, odd, units, final_stake,
                    ev_pct if ev_pct != 0 else None,
                )
                st.success(f"Aposta registrada: R$ {final_stake:.2f}.")
                st.rerun()

    all_bets = bets.load_bets()
    if not all_bets:
        st.info("Nenhuma aposta registrada ainda.")
    else:
        stats = bets.summary(all_bets)
        m1, m2, m3, m4, m5 = st.columns(5)
        m1.metric("Total apostado", f"R$ {stats['staked']:.2f}")
        m2.metric(
            "Lucro / Prejuízo", f"R$ {stats['profit']:.2f}",
            delta=f"{stats['roi'] * 100:.1f}% ROI",
        )
        m3.metric("ROI geral", f"{stats['roi'] * 100:.2f}%")
        m4.metric("Taxa de acerto", f"{stats['hit_rate'] * 100:.1f}%")
        m5.metric("Pendentes", stats["n_pending"])

        st.subheader("Histórico")
        df = pd.DataFrame(all_bets)
        df["Lucro (R$)"] = df.apply(lambda r: bets.profit(r), axis=1)
        df["ROI aposta (%)"] = df.apply(
            lambda r: round(bets.profit(r) / r["stake"] * 100, 1)
            if bets.profit(r) is not None and r["stake"]
            else None,
            axis=1,
        )
        df["Data"] = df["created_at"].map(format_kickoff)
        df["Excluir"] = False

        editable = df[
            ["id", "Data", "event", "market", "bookmaker", "odd", "units",
             "stake", "status", "Lucro (R$)", "ROI aposta (%)", "ev_pct",
             "Excluir"]
        ].rename(
            columns={
                "event": "Jogo", "market": "Mercado", "bookmaker": "Casa",
                "odd": "Odd", "units": "Unidades", "stake": "Valor (R$)",
                "status": "Status", "ev_pct": "EV est. (%)",
            }
        )

        edited = st.data_editor(
            editable,
            use_container_width=True,
            hide_index=True,
            disabled=[
                "id", "Data", "Jogo", "Mercado", "Casa", "Odd", "Unidades",
                "Valor (R$)", "Lucro (R$)", "ROI aposta (%)", "EV est. (%)",
            ],
            column_config={
                "id": None,
                "Status": st.column_config.SelectboxColumn(
                    "Status", options=bets.STATUSES, required=True
                ),
                "Excluir": st.column_config.CheckboxColumn("Excluir"),
            },
            key="bets_editor",
        )

        if st.button("💾 Salvar alterações"):
            changed = 0
            for _, row in edited.iterrows():
                bet_id = int(row["id"])
                if row["Excluir"]:
                    bets.delete_bet(bet_id)
                    changed += 1
                    continue
                original = next(b for b in all_bets if b["id"] == bet_id)
                if row["Status"] != original["status"]:
                    bets.update_status(bet_id, row["Status"])
                    changed += 1
            st.success(f"{changed} alteração(ões) salva(s).")
            st.rerun()

        st.caption(
            "Marque **Ganha/Perdida/Anulada** na coluna Status conforme os "
            "jogos terminam e clique em Salvar. ROI geral considera apenas "
            "apostas resolvidas."
        )
