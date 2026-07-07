"""
SEC-EDGAR-Client (nur US-Filer). Kostenlos, kein API-Key – aber SEC verlangt
einen aussagekräftigen User-Agent. Setze EDGAR_UA (z. B. "Finvest research
you@example.com") als Umgebungsvariable.

Liefert eine Zeitreihe je US-GAAP-Konzept (jährliche 10-K-Werte). Da Filer
unterschiedliche Tags verwenden, probieren wir mehrere Aliase.
"""
from __future__ import annotations
import os
import time
import requests

UA = os.environ.get("EDGAR_UA", "Finvest Fundamental research contact@example.com")
HEADERS = {"User-Agent": UA, "Accept-Encoding": "gzip, deflate"}
_TICKER_MAP = None


def _get(url, tries=3):
    for i in range(tries):
        resp = requests.get(url, headers=HEADERS, timeout=30)
        if resp.status_code == 200:
            return resp.json()
        time.sleep(1.5 * (i + 1))          # SEC-Ratelimit respektieren
    resp.raise_for_status()


def ticker_to_cik(ticker: str):
    """SEC-Mapping Ticker -> zehnstellige CIK."""
    global _TICKER_MAP
    if _TICKER_MAP is None:
        data = _get("https://www.sec.gov/files/company_tickers.json")
        _TICKER_MAP = {row["ticker"].upper(): str(row["cik_str"]).zfill(10)
                       for row in data.values()}
    # BRK.B -> BRK-B -> BRK B: SEC nutzt meist die Stammaktie
    t = ticker.upper().replace(".", "-")
    return _TICKER_MAP.get(t) or _TICKER_MAP.get(ticker.upper().split(".")[0])


def company_facts(cik: str):
    return _get(f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json")


def _annual_series(facts, concept_aliases):
    """Gibt {fiscal_year: value} für das erste passende Konzept zurück (10-K, USD)."""
    gaap = facts.get("facts", {}).get("us-gaap", {})
    for c in concept_aliases:
        node = gaap.get(c)
        if not node:
            continue
        for unit, rows in node.get("units", {}).items():
            out = {}
            for row in rows:
                if row.get("form") in ("10-K", "10-K/A") and row.get("fp") == "FY" and "val" in row:
                    fy = row.get("fy")
                    if fy:
                        out[fy] = row["val"]
            if out:
                return out
    return {}


# Konzept-Aliase (Filer verwenden nicht immer dieselben Tags)
CONCEPTS = {
    "revenue": ["Revenues", "RevenueFromContractWithCustomerExcludingAssessedTax", "SalesRevenueNet"],
    "net_income": ["NetIncomeLoss", "ProfitLoss"],
    "operating_income": ["OperatingIncomeLoss"],
    "gross_profit": ["GrossProfit"],
    "assets": ["Assets"],
    "current_liabilities": ["LiabilitiesCurrent"],
    "cash": ["CashAndCashEquivalentsAtCarryingValue", "CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents"],
    "long_term_debt": ["LongTermDebtNoncurrent", "LongTermDebt"],
    "short_term_debt": ["ShortTermBorrowings", "DebtCurrent"],
    "equity": ["StockholdersEquity", "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest"],
    "op_cash_flow": ["NetCashProvidedByUsedInOperatingActivities"],
    "capex": ["PaymentsToAcquirePropertyPlantAndEquipment", "PaymentsForCapitalImprovements"],
    "shares": ["CommonStockSharesOutstanding", "WeightedAverageNumberOfDilutedSharesOutstanding"],
    "dep_amort": ["DepreciationDepletionAndAmortization", "DepreciationAmortizationAndAccretionNet"],
    # zusaetzlich fuer Piotroski / Beneish:
    "receivables": ["AccountsReceivableNetCurrent", "ReceivablesNetCurrent"],
    "cogs": ["CostOfGoodsAndServicesSold", "CostOfRevenue"],
    "sga": ["SellingGeneralAndAdministrativeExpense", "GeneralAndAdministrativeExpense"],
    "ppe": ["PropertyPlantAndEquipmentNet"],
    "current_assets": ["AssetsCurrent"],
}


def fetch_edgar_fundamentals(ticker: str) -> dict:
    """Roh-Zeitreihen je Kennzahl aus den 10-K-Filings. Leere Dicts bei Fehlen."""
    cik = ticker_to_cik(ticker)
    if not cik:
        return {}
    facts = company_facts(cik)
    return {key: _annual_series(facts, aliases) for key, aliases in CONCEPTS.items()}
