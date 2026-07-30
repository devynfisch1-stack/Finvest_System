"""
Financial-Modeling-Prep-Client (GRATIS-Tier, 250 Calls/Tag, US-Titel).

Wird nur genutzt, wenn FMP_API_KEY gesetzt ist. Liefert genau die Stuecke,
bei denen FMP dem yfinance-/EDGAR-Pfad ueberlegen ist:
- ECHTE historische KGV-/EV-EBITDA-Reihe (behebt die Naeherung)
- fertiger Piotroski-Score
- ROIC / Market Cap aus geprueften Kennzahlen

Alles best-effort: faellt etwas aus, gibt die Funktion nur zurueck, was da ist.
Budget: ~4 Calls/Titel x 22 US-Titel ~= 90 Calls pro Wochenlauf < 250/Tag.
"""
from __future__ import annotations
import os
import requests
from metrics_extra import valuation_history_stats

BASE = "https://financialmodelingprep.com/api"
KEY = os.environ.get("FMP_API_KEY")


def _get(path, **params):
    if not KEY:
        return None
    params["apikey"] = KEY
    try:
        r = requests.get(f"{BASE}/{path}", params=params, timeout=25)
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass
    return None


def fmp_block(symbol: str) -> dict:
    """Kompaktes Dict mit den FMP-Werten; leeres Dict wenn kein Key/US-Titel."""
    if not KEY:
        return {}
    out = {}

    quote = _get(f"v3/quote/{symbol}")
    if isinstance(quote, list) and quote:
        out["pe_now"] = quote[0].get("pe")
        out["market_cap"] = quote[0].get("marketCap")
        out["price"] = quote[0].get("price")

    # historische Verhaeltniszahlen (Jahresreihe, juengstes Jahr zuerst) ->
    # KGV/EV-EBITDA rezenz-gewichtet + 3/6/10-Jahres-Fenster (ersetzt das
    # vorherige stur flache 8-Jahres-Mittel, siehe valuation_history_stats()).
    ratios = _get(f"v3/ratios/{symbol}", limit=10)
    if isinstance(ratios, list) and len(ratios) >= 3:
        pes = [x.get("priceEarningsRatio") for x in ratios if x.get("priceEarningsRatio")]
        evs = [x.get("enterpriseValueMultiple") for x in ratios if x.get("enterpriseValueMultiple")]

        pe_stats = valuation_history_stats(pes)
        if pe_stats["mean"] is not None:
            out["pe_hist_mean"] = pe_stats["mean"]
            out["pe_hist_std"] = pe_stats["std"]
            out["pe_hist_3y"] = pe_stats["w3"]
            out["pe_hist_6y"] = pe_stats["w6"]
            out["pe_hist_10y"] = pe_stats["w10"]

        ev_stats = valuation_history_stats(evs)
        if ev_stats["mean"] is not None:
            out["ev_hist_mean"] = ev_stats["mean"]
            out["ev_hist_std"] = ev_stats["std"]
            out["ev_hist_3y"] = ev_stats["w3"]
            out["ev_hist_6y"] = ev_stats["w6"]
            out["ev_hist_10y"] = ev_stats["w10"]
            evs_valid = [e for e in evs if e and e > 0]
            if evs_valid:
                out["ev_now"] = evs_valid[0]

    km = _get(f"v3/key-metrics/{symbol}", limit=1)
    if isinstance(km, list) and km:
        out["roic"] = km[0].get("roic")

    score = _get("v4/score", symbol=symbol)
    if isinstance(score, list) and score:
        p = score[0].get("piotroskiScore")
        if p is not None:
            out["piotroski_raw"], out["piotroski_max"] = p, 9

    return out
