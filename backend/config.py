"""
Zentrale Konfiguration des Finvest Fundamental-Systems (optimierte Version).

Neu ggü. v1:
- `sector` je Titel  -> Sektor-relative Perzentile
- FMP-Gratis-Anbindung (250 Calls/Tag) als bevorzugte US-Quelle
- neu gewichtetes Metrikset inkl. Piotroski, Accruals, Sektor-Relativwert
- Beneish-M-Score als zusätzliches Gate
"""

WACC = 0.085
BENCHMARK = {"US": "SPY", "CH": "^SSMI"}

# FMP: wird nur genutzt, wenn FMP_API_KEY gesetzt ist (Gratis-Tier reicht,
# 250 Calls/Tag; wöchentlicher Lauf ueber ~40 Titel bleibt darunter).
FMP_ENABLED = True

# --- Blockgewichte (Gesamt-Score) ---
BLOCK_WEIGHTS = {"quality": 0.45, "valuation": 0.40, "dislocation": 0.15}

# --- Qualitaet (Summe 100) ---
QUALITY_WEIGHTS = {
    "roic": 24,            # ROIC vs. Kapitalkosten (absolut)
    "roic_trend": 12,      # ROIC-Trend / inkrementell
    "piotroski": 16,       # NEU: 9-Punkte-Qualitaetscheck
    "earnings_quality": 18,# Cash Conversion + Accruals
    "margin_stability": 12,
    "balance": 12,         # Gate
    "dilution": 6,
}
# --- Bewertung (Summe 100) ---
VALUATION_WEIGHTS = {
    "pe_vs_hist": 26,      # KGV vs. eigene Historie (Z-Score)
    "pe_vs_sector": 12,    # NEU: KGV-Perzentil im Sektor
    "ev_vs_hist": 16,
    "pfcf_vs_hist": 12,
    "reverse_dcf": 20,
    "margin_of_safety": 14,
}

# --- Gates ---
GATE_MIN_BALANCE = 3
GATE_MIN_EARNINGS_QUALITY = 3
GATE_BENEISH_M = -1.78     # M darueber => Manipulationsverdacht => Deckel
GATE_CAP = 4.0

Q_HIGH = 6.5
V_CHEAP = 6.0

# Konfidenz-Gewicht je Datenquelle
SOURCE_QUALITY = {"fmp": 1.0, "edgar": 0.9, "yfinance": 0.7, "mock": 1.0}

def _u(t, y, d, n, e, s):
    return {"ticker": t, "yf": y, "domain": d, "name": n, "edgar": e, "sector": s}

UNIVERSE = {
    "US": [
        _u("AAPL","AAPL","apple.com","Apple",True,"Technology"),
        _u("MSFT","MSFT","microsoft.com","Microsoft",True,"Technology"),
        _u("NVDA","NVDA","nvidia.com","NVIDIA",True,"Semiconductors"),
        _u("AMZN","AMZN","amazon.com","Amazon",True,"Consumer Disc"),
        _u("GOOGL","GOOGL","google.com","Alphabet",True,"Communication"),
        _u("META","META","meta.com","Meta Platforms",True,"Communication"),
        _u("BRK.B","BRK-B","berkshirehathaway.com","Berkshire Hathaway",True,"Financials"),
        _u("LLY","LLY","lilly.com","Eli Lilly",True,"Healthcare"),
        _u("AVGO","AVGO","broadcom.com","Broadcom",True,"Semiconductors"),
        _u("JPM","JPM","jpmorganchase.com","JPMorgan Chase",True,"Financials"),
        _u("V","V","visa.com","Visa",True,"Financials"),
        _u("XOM","XOM","exxonmobil.com","Exxon Mobil",True,"Energy"),
        _u("UNH","UNH","unitedhealthgroup.com","UnitedHealth",True,"Healthcare"),
        _u("MA","MA","mastercard.com","Mastercard",True,"Financials"),
        _u("COST","COST","costco.com","Costco",True,"Staples"),
        _u("HD","HD","homedepot.com","Home Depot",True,"Consumer Disc"),
        _u("PG","PG","pg.com","Procter & Gamble",True,"Staples"),
        _u("JNJ","JNJ","jnj.com","Johnson & Johnson",True,"Healthcare"),
        _u("KO","KO","coca-colacompany.com","Coca-Cola",True,"Staples"),
        _u("UBER","UBER","uber.com","Uber",True,"Technology"),
        _u("BN","BN","brookfield.com","Brookfield",True,"Financials"),
        _u("QSR","QSR","rbi.com","Restaurant Brands",True,"Consumer Disc"),
    ],
    "CH": [
        _u("NESN","NESN.SW","nestle.com","Nestle",False,"Staples"),
        _u("ROG","ROG.SW","roche.com","Roche",False,"Healthcare"),
        _u("NOVN","NOVN.SW","novartis.com","Novartis",False,"Healthcare"),
        _u("UBSG","UBSG.SW","ubs.com","UBS Group",False,"Financials"),
        _u("CFR","CFR.SW","richemont.com","Richemont",False,"Consumer Disc"),
        _u("ZURN","ZURN.SW","zurich.com","Zurich Insurance",False,"Financials"),
        _u("ABBN","ABBN.SW","abb.com","ABB",False,"Industrials"),
        _u("LONN","LONN.SW","lonza.com","Lonza",False,"Healthcare"),
        _u("SIKA","SIKA.SW","sika.com","Sika",False,"Materials"),
        _u("HOLN","HOLN.SW","holcim.com","Holcim",False,"Materials"),
        _u("ALC","ALC.SW","alcon.com","Alcon",False,"Healthcare"),
        _u("GIVN","GIVN.SW","givaudan.com","Givaudan",False,"Materials"),
        _u("SREN","SREN.SW","swissre.com","Swiss Re",False,"Financials"),
        _u("PGHN","PGHN.SW","partnersgroup.com","Partners Group",False,"Financials"),
        _u("SCMN","SCMN.SW","swisscom.ch","Swisscom",False,"Telecom"),
        _u("SLHN","SLHN.SW","swisslife.ch","Swiss Life",False,"Financials"),
        _u("GEBN","GEBN.SW","geberit.com","Geberit",False,"Industrials"),
        _u("LOGN","LOGN.SW","logitech.com","Logitech",False,"Technology"),
    ],
}

FINANCIALS = {"UBSG", "ZURN", "SREN", "SLHN", "JPM"}
