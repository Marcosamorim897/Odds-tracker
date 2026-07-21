# ⚽ Odds Tracker

Aplicação para análise de odds do Brasileirão Série A: coleta cotações de
várias casas de aposta via [The Odds API](https://the-odds-api.com), compara
lado a lado e identifica oportunidades de **EV+** (valor esperado positivo)
usando a Pinnacle como referência de mercado.

> Ferramenta analítica e educacional. Não é recomendação de aposta nem
> garantia de lucro. Aposte com responsabilidade.

## Como funciona o cálculo de EV

1. As odds da casa de referência (sharp) são convertidas em probabilidades
   implícitas e normalizadas para remover o vig (devig multiplicativo),
   gerando a **probabilidade justa** de cada resultado.
2. Para cada odd das demais casas: `EV = prob_justa × odd − 1`.
3. EV positivo indica que a odd paga mais do que o risco estimado pelo
   mercado — uma oportunidade teórica de valor.

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate        # Windows
pip install -r requirements.txt
copy .env.example .env        # e cole sua chave da The Odds API
```

## Uso

```bash
streamlit run app.py
```

Na barra lateral, clique em **Atualizar odds agora** para coletar. Cada
coleta consome 2 créditos da API (regiões `eu` + `uk`, mercado 1X2). O free
tier dá 500 créditos/mês (~8 coletas/dia).

Também dá para coletar via linha de comando (útil para agendar):

```bash
python -m src.collector
```

## Planilha de apostas (gestão de banca)

A aba **📒 Planilha de apostas** registra suas apostas com jogo, mercado,
casa, odd, unidades, valor em R$ e EV estimado. Conforme você marca cada
aposta como Ganha/Perdida/Anulada, o painel calcula lucro por aposta, ROI
por aposta, ROI geral, taxa de acerto e total apostado. A tabela tem
download em CSV embutido (ícone no topo do histórico).

## Estrutura

| Arquivo | Papel |
|---|---|
| `src/collector.py` | Busca odds na API e grava no SQLite |
| `src/ev_engine.py` | Devig + cálculo de EV |
| `src/bets.py` | Planilha de apostas: registro, status, lucro e ROI |
| `src/database.py` | Persistência (histórico de snapshots) |
| `src/config.py` | Liga, mercados, regiões, casa de referência |
| `app.py` | Dashboard Streamlit |
