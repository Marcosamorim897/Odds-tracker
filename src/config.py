"""Configurações centrais do odds-tracker."""
import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

API_KEY = os.getenv("ODDS_API_KEY", "")
API_BASE_URL = "https://api.the-odds-api.com/v4"

# Em produção (Render), DATABASE_URL aponta para o Postgres do Neon.
# Localmente, fica vazio e o app usa SQLite em data/odds.db.
DATABASE_URL = os.getenv("DATABASE_URL", "").strip()
if DATABASE_URL.startswith("postgres://"):
    # SQLAlchemy exige o esquema "postgresql://"; alguns provedores ainda
    # entregam a connection string com o prefixo antigo "postgres://".
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# Brasileirão Série A
SPORT_KEY = "soccer_brazil_campeonato"

# Cada região consultada consome 1 crédito por mercado.
# "eu" inclui a Pinnacle (referência sharp); "uk" traz Bet365 e outras soft.
REGIONS = "eu,uk"
MARKETS = "h2h"  # 1X2
ODDS_FORMAT = "decimal"

# Casa usada como referência de mercado para estimar a probabilidade justa
SHARP_BOOKMAKER = "pinnacle"

DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "odds.db"
