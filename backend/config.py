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

# --- Qualitaet (Summe 100) -- abgeleitet aus Bill Ackmans 8 Investmentprinzipien ---
# Jede Kennzahl ist einem konkreten Ackman-Kriterium zugeordnet (siehe Kommentar).
QUALITY_WEIGHTS = {
    "roic": 18,             # Prinzip 4: High Returns on Capital
    "predictability": 10,   # Prinzip 1: Simple, Predictable (Umsatz-Volatilitaet)
    "fcf_generative": 12,   # Prinzip 2: Free-Cashflow-generativ (FCF-Marge)
    "moat": 14,             # Prinzip 3: Dominant, hohe Eintrittsbarrieren
    "extrinsic_risk": 8,    # Prinzip 5: Begrenzte, unkontrollierbare Fremdrisiken
    "balance": 14,          # Prinzip 6: Starke Bilanz, kein Kapitalzugang noetig (Gate)
    "management": 12,       # Prinzip 7: Exzellentes Management / Kapitalallokation
    "earnings_quality": 8,  # Cross-Check: Cash Conversion + Accruals
    "piotroski": 4,         # genereller 9-Punkte-Qualitaetscheck
}
# Prinzip 8 (Good Governance) wird BEWUSST NICHT in die Gewichtung eingerechnet --
# dafuer gibt es keine verlaessliche Gratis-Datenquelle. Stattdessen ein rein
# informativer Hinweis (siehe GOVERNANCE_WATCHLIST unten), der im Dashboard
# separat angezeigt werden kann, aber den Score nicht verzerrt.
GOVERNANCE_WATCHLIST = {
    # Bekannte Dual-Class-Strukturen (Gruenderstimmrechte ueberproportional) --
    # von Hand kuratiert, NICHT automatisch ermittelt. Nur ein Hinweis-Flag,
    # kein Score-Abzug, da die Angemessenheit von Dual-Class je nach Firma
    # unterschiedlich zu bewerten ist.
    "GOOGL": "Dual-Class-Aktienstruktur (Alphabet-Gruender halten ueberproportionale Stimmrechte)",
    "META": "Dual-Class-Aktienstruktur (Zuckerberg haelt ueberproportionale Stimmrechte)",
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

# Mindestschwelle fuer die abnormale (marktbereinigte) Tagesrendite, damit eine
# News ueberhaupt im Dashboard erscheint -- filtert reines Rauschen ohne
# spuerbare Kursreaktion heraus. In Prozentpunkten. Bewusst gleich der
# "Mittel"-Schwelle in news.strength_from(), damit nach dem Filter nie eine
# als "Tief" eingestufte News uebrig bleibt.
NEWS_MIN_ABS_MOVE = 2.0

# Konfidenz-Gewicht je Datenquelle
SOURCE_QUALITY = {"fmp": 1.0, "edgar": 0.9, "yfinance": 0.7, "mock": 1.0}

def _u(t, y, d, n, e, s):
    return {"ticker": t, "yf": y, "domain": d, "name": n, "edgar": e, "sector": s}

UNIVERSE = {
    # Top 50 US-Unternehmen nach Marktkapitalisierung (Stand Juli 2026, nur in
    # den USA domizilierte Firmen -- Cross-Listings wie TSM/ASML/HSBC/NVS/ARM
    # bewusst ausgeschlossen, da sie eigentlich anderen Maerkten zuzurechnen sind).
    "US": [
        _u("NVDA","NVDA","nvidia.com","NVIDIA",True,"Semiconductors"),
        _u("AAPL","AAPL","apple.com","Apple",True,"Technology"),
        _u("GOOGL","GOOGL","google.com","Alphabet",True,"Communication"),
        _u("MSFT","MSFT","microsoft.com","Microsoft",True,"Technology"),
        _u("AMZN","AMZN","amazon.com","Amazon",True,"Consumer Disc"),
        _u("AVGO","AVGO","broadcom.com","Broadcom",True,"Semiconductors"),
        _u("SPCX","SPCX","spacex.com","SpaceX",True,"Industrials"),
        _u("META","META","meta.com","Meta Platforms",True,"Communication"),
        _u("TSLA","TSLA","tesla.com","Tesla",True,"Consumer Disc"),
        _u("MU","MU","micron.com","Micron Technology",True,"Semiconductors"),
        _u("BRK.B","BRK-B","berkshirehathaway.com","Berkshire Hathaway",True,"Financials"),
        _u("LLY","LLY","lilly.com","Eli Lilly",True,"Healthcare"),
        _u("JPM","JPM","jpmorganchase.com","JPMorgan Chase",True,"Financials"),
        _u("AMD","AMD","amd.com","Advanced Micro Devices",True,"Semiconductors"),
        _u("WMT","WMT","walmart.com","Walmart",True,"Staples"),
        _u("V","V","visa.com","Visa",True,"Financials"),
        _u("XOM","XOM","exxonmobil.com","Exxon Mobil",True,"Energy"),
        _u("JNJ","JNJ","jnj.com","Johnson & Johnson",True,"Healthcare"),
        _u("INTC","INTC","intel.com","Intel",True,"Semiconductors"),
        _u("MA","MA","mastercard.com","Mastercard",True,"Financials"),
        _u("ABBV","ABBV","abbvie.com","AbbVie",True,"Healthcare"),
        _u("AMAT","AMAT","appliedmaterials.com","Applied Materials",True,"Semiconductors"),
        _u("CSCO","CSCO","cisco.com","Cisco Systems",True,"Technology"),
        _u("BAC","BAC","bankofamerica.com","Bank of America",True,"Financials"),
        _u("CAT","CAT","caterpillar.com","Caterpillar",True,"Industrials"),
        _u("COST","COST","costco.com","Costco",True,"Staples"),
        _u("LRCX","LRCX","lamresearch.com","Lam Research",True,"Semiconductors"),
        _u("CVX","CVX","chevron.com","Chevron",True,"Energy"),
        _u("UNH","UNH","unitedhealthgroup.com","UnitedHealth",True,"Healthcare"),
        _u("GE","GE","ge.com","GE Aerospace",True,"Industrials"),
        _u("KO","KO","coca-colacompany.com","Coca-Cola",True,"Staples"),
        _u("ORCL","ORCL","oracle.com","Oracle",True,"Technology"),
        _u("PG","PG","pg.com","Procter & Gamble",True,"Staples"),
        _u("MS","MS","morganstanley.com","Morgan Stanley",True,"Financials"),
        _u("HD","HD","homedepot.com","Home Depot",True,"Consumer Disc"),
        _u("MRK","MRK","merck.com","Merck & Co",True,"Healthcare"),
        _u("GS","GS","goldmansachs.com","Goldman Sachs",True,"Financials"),
        _u("PM","PM","pmi.com","Philip Morris International",True,"Staples"),
        _u("PLTR","PLTR","palantir.com","Palantir Technologies",True,"Technology"),
        _u("NFLX","NFLX","netflix.com","Netflix",True,"Communication"),
        _u("KLAC","KLAC","kla.com","KLA Corporation",True,"Semiconductors"),
        _u("DELL","DELL","dell.com","Dell Technologies",True,"Technology"),
        _u("RTX","RTX","rtx.com","RTX Corp",True,"Industrials"),
        _u("GEV","GEV","gevernova.com","GE Vernova",True,"Industrials"),
        _u("PANW","PANW","paloaltonetworks.com","Palo Alto Networks",True,"Technology"),
        _u("WFC","WFC","wellsfargo.com","Wells Fargo",True,"Financials"),
        _u("TXN","TXN","ti.com","Texas Instruments",True,"Semiconductors"),
        _u("SNDK","SNDK","sandisk.com","Sandisk",True,"Technology"),
        _u("AXP","AXP","americanexpress.com","American Express",True,"Financials"),
        _u("ANET","ANET","arista.com","Arista Networks",True,"Technology"),
    ],
    # Top 50 Schweizer Unternehmen nach Marktkapitalisierung (nur an der SIX
    # gehandelte Titel -- Cross-Listings wie Chubb/Glencore-OTC/TE Connectivity/
    # Garmin/STMicro/On Holding/Amcor bewusst ausgeschlossen, da deren
    # Haupthandelsplatz ausserhalb der SIX liegt).
    "CH": [
        _u("ROG","ROG.SW","roche.com","Roche",False,"Healthcare"),
        _u("NOVN","NOVN.SW","novartis.com","Novartis",False,"Healthcare"),
        _u("NESN","NESN.SW","nestle.com","Nestle",False,"Staples"),
        _u("ABBN","ABBN.SW","abb.com","ABB",False,"Industrials"),
        _u("UBSG","UBSG.SW","ubs.com","UBS Group",False,"Financials"),
        _u("CFR","CFR.SW","richemont.com","Richemont",False,"Consumer Disc"),
        _u("ZURN","ZURN.SW","zurich.com","Zurich Insurance",False,"Financials"),
        _u("GLEN","GLEN.SW","glencore.com","Glencore",False,"Materials"),
        _u("HOLN","HOLN.SW","holcim.com","Holcim",False,"Materials"),
        _u("GALD","GALD.SW","galderma.com","Galderma Group",False,"Healthcare"),
        _u("SREN","SREN.SW","swissre.com","Swiss Re",False,"Financials"),
        _u("LONN","LONN.SW","lonza.com","Lonza",False,"Healthcare"),
        _u("SCMN","SCMN.SW","swisscom.ch","Swisscom",False,"Telecom"),
        _u("SDZ","SDZ.SW","sandoz.com","Sandoz Group",False,"Healthcare"),
        _u("SCHP","SCHP.SW","schindler.com","Schindler Group",False,"Industrials"),
        _u("GIVN","GIVN.SW","givaudan.com","Givaudan",False,"Materials"),
        _u("ALC","ALC.SW","alcon.com","Alcon",False,"Healthcare"),
        _u("SIKA","SIKA.SW","sika.com","Sika",False,"Materials"),
        _u("SLHN","SLHN.SW","swisslife.ch","Swiss Life",False,"Financials"),
        _u("KNIN","KNIN.SW","kuehne-nagel.com","Kuehne+Nagel",False,"Industrials"),
        _u("LISN","LISN.SW","lindt-spruengli.com","Lindt & Spruengli",False,"Staples"),
        _u("HBAN","HBAN.SW","helvetiabaloise.com","Helvetia Baloise",False,"Financials"),
        _u("PGHN","PGHN.SW","partnersgroup.com","Partners Group",False,"Financials"),
        _u("VACN","VACN.SW","vatgroup.com","VAT Group",False,"Industrials"),
        _u("SGSN","SGSN.SW","sgs.com","SGS",False,"Industrials"),
        _u("GEBN","GEBN.SW","geberit.com","Geberit",False,"Industrials"),
        _u("EMSN","EMSN.SW","ems-group.com","Ems-Chemie",False,"Materials"),
        _u("STMN","STMN.SW","straumann.com","Straumann",False,"Healthcare"),
        _u("BAER","BAER.SW","juliusbaer.com","Julius Baer",False,"Financials"),
        _u("LOGN","LOGN.SW","logitech.com","Logitech",False,"Technology"),
        _u("SOON","SOON.SW","sonova.com","Sonova",False,"Healthcare"),
        _u("BEAN","BEAN.SW","belimo.com","Belimo Holding",False,"Industrials"),
        _u("UHR","UHR.SW","swatchgroup.com","Swatch Group",False,"Consumer Disc"),
        _u("SPSN","SPSN.SW","sps.swiss","Swiss Prime Site",False,"Real Estate"),
        _u("BCVN","BCVN.SW","bcv.ch","Banque Cantonale Vaudoise",False,"Financials"),
        _u("BKW","BKW.SW","bkw.ch","BKW",False,"Utilities"),
        _u("ACLN","ACLN.SW","accelleron.com","Accelleron Industries",False,"Industrials"),
        _u("FHZN","FHZN.SW","flughafen-zuerich.ch","Zurich Airport",False,"Industrials"),
        _u("AVOL","AVOL.SW","avolta.net","Avolta",False,"Consumer Disc"),
        _u("PSPN","PSPN.SW","psp.info","PSP Swiss Property",False,"Real Estate"),
        _u("BARN","BARN.SW","barry-callebaut.com","Barry Callebaut",False,"Staples"),
        _u("SQN","SQN.SW","swissquote.com","Swissquote",False,"Financials"),
        _u("VZN","VZN.SW","vzch.com","VZ Holding",False,"Financials"),
        _u("LUKN","LUKN.SW","lukb.ch","Luzerner Kantonalbank",False,"Financials"),
        _u("SUN","SUN.SW","sulzer.com","Sulzer",False,"Industrials"),
        _u("BANB","BANB.SW","bachem.com","Bachem",False,"Healthcare"),
        _u("EFGN","EFGN.SW","efginternational.com","EFG International",False,"Financials"),
        _u("SFSN","SFSN.SW","sfs.com","SFS Group",False,"Industrials"),
        _u("TEMN","TEMN.SW","temenos.com","Temenos",False,"Technology"),
        _u("HUBN","HUBN.SW","hubersuhner.com","Huber+Suhner",False,"Industrials"),
    ],
}

FINANCIALS = {
    "UBSG", "ZURN", "SREN", "SLHN", "JPM", "BRK.B", "MA", "V", "MS", "GS", "WFC",
    "AXP", "BAC", "HBAN", "PGHN", "BAER", "BCVN", "SQN", "VZN", "LUKN", "EFGN",
}
