"""
Zusätzliche, GRATIS berechenbare Profi-Kennzahlen:

- Piotroski F-Score (0–9): empirisch belegter 9-Punkte-Qualitätscheck.
- Beneish M-Score: Flag für mögliche Bilanzmanipulation (Gate).
- Sloan-Accruals: Ertragsqualität (Gewinn vs. Cashflow).
- Sektor-relative Perzentile: normalisiert Kennzahlen gegen echte Peers,
  statt gegen fixe Schwellen (behebt die Sektorblindheit).

Alle Funktionen sind rein (keine Netzwerkzugriffe) und damit offline testbar.
Fehlen Eingaben, wird None/Teilscore zurückgegeben – nie ein erzwungener Wert.
"""
from __future__ import annotations


def _safe_div(a, b):
    try:
        if a is None or b is None or b == 0:
            return None
        return a / b
    except Exception:
        return None


# --------------------------------------------------------------------------- #
#  PIOTROSKI F-SCORE  (braucht laufendes + Vorjahr)
# --------------------------------------------------------------------------- #
def piotroski(cur: dict, prev: dict):
    """
    cur/prev: dicts mit net_income, cfo, assets, ltd, current_assets,
    current_liabilities, shares, gross_profit, revenue.
    Rückgabe: (score, max_verfügbar). Nicht bewertbare Kriterien entfallen.
    """
    pts, mx = 0, 0

    def chk(cond):
        nonlocal pts, mx
        if cond is None:
            return
        mx += 1
        if cond:
            pts += 1

    roa = _safe_div(cur.get("net_income"), cur.get("assets"))
    roa_p = _safe_div(prev.get("net_income"), prev.get("assets"))
    chk(None if roa is None else roa > 0)                        # 1 ROA>0
    chk(None if cur.get("cfo") is None else cur["cfo"] > 0)      # 2 CFO>0
    chk(None if (roa is None or roa_p is None) else roa > roa_p) # 3 ROA steigt
    chk(None if (cur.get("cfo") is None or cur.get("net_income") is None)
        else cur["cfo"] > cur["net_income"])                     # 4 CFO>NI (Accrual)

    ltd_r = _safe_div(cur.get("ltd"), cur.get("assets"))
    ltd_r_p = _safe_div(prev.get("ltd"), prev.get("assets"))
    chk(None if (ltd_r is None or ltd_r_p is None) else ltd_r < ltd_r_p)   # 5 Verschuldung sinkt
    cr = _safe_div(cur.get("current_assets"), cur.get("current_liabilities"))
    cr_p = _safe_div(prev.get("current_assets"), prev.get("current_liabilities"))
    chk(None if (cr is None or cr_p is None) else cr > cr_p)               # 6 Liquidität steigt
    chk(None if (cur.get("shares") is None or prev.get("shares") is None)
        else cur["shares"] <= prev["shares"] * 1.001)                      # 7 keine Verwässerung

    gm = _safe_div(cur.get("gross_profit"), cur.get("revenue"))
    gm_p = _safe_div(prev.get("gross_profit"), prev.get("revenue"))
    chk(None if (gm is None or gm_p is None) else gm > gm_p)               # 8 Bruttomarge steigt
    at = _safe_div(cur.get("revenue"), cur.get("assets"))
    at_p = _safe_div(prev.get("revenue"), prev.get("assets"))
    chk(None if (at is None or at_p is None) else at > at_p)              # 9 Kapitalumschlag steigt

    if mx == 0:
        return None, 0
    return pts, mx


def piotroski_score(f_raw, mx):
    """0..9 -> 1..10 (auf verfügbare Kriterien skaliert)."""
    if f_raw is None or not mx:
        return None
    return 1 + (f_raw / mx) * 9


# --------------------------------------------------------------------------- #
#  BENEISH M-SCORE  (Manipulations-Flag, Gate)
# --------------------------------------------------------------------------- #
def beneish_m(cur: dict, prev: dict):
    """M > -1.78 deutet auf mögliche Bilanzmanipulation hin. None bei Datenlücken."""
    try:
        s, sp = cur["revenue"], prev["revenue"]
        rec, recp = cur["receivables"], prev["receivables"]
        cogs, cogsp = cur["cogs"], prev["cogs"]
        ca, cap = cur["current_assets"], prev["current_assets"]
        ppe, ppep = cur["ppe"], prev["ppe"]
        assets, assetsp = cur["assets"], prev["assets"]
        dep, depp = cur["dep"], prev["dep"]
        sga, sgap = cur["sga"], prev["sga"]
        ni = cur["net_income"]
        cfo = cur["cfo"]
        cl, clp = cur["current_liabilities"], prev["current_liabilities"]
        ltd, ltdp = cur.get("ltd", 0), prev.get("ltd", 0)

        DSRI = (rec / s) / (recp / sp)
        gm = (s - cogs) / s
        gmp = (sp - cogsp) / sp
        GMI = gmp / gm
        AQI = (1 - (ca + ppe) / assets) / (1 - (cap + ppep) / assetsp)
        SGI = s / sp
        DEPI = (depp / (depp + ppep)) / (dep / (dep + ppe))
        SGAI = (sga / s) / (sgap / sp)
        LVGI = ((ltd + cl) / assets) / ((ltdp + clp) / assetsp)
        TATA = (ni - cfo) / assets
        M = (-4.84 + 0.92 * DSRI + 0.528 * GMI + 0.404 * AQI + 0.892 * SGI
             + 0.115 * DEPI - 0.172 * SGAI + 4.679 * TATA - 0.327 * LVGI)
        return round(M, 2)
    except Exception:
        return None


# --------------------------------------------------------------------------- #
#  SLOAN-ACCRUALS  (Ertragsqualität)
# --------------------------------------------------------------------------- #
def accruals_ratio(net_income, cfo, assets):
    """(NI - CFO)/Assets. Hoch positiv = geringe Qualität. None bei Lücke."""
    if None in (net_income, cfo, assets) or not assets:
        return None
    return (net_income - cfo) / assets


def accruals_score(ar):
    """Niedrige Accruals -> hoher Score. -0.1..0.2 -> 10..1."""
    if ar is None:
        return None
    return max(1, min(10, 1 + (0.2 - ar) / 0.3 * 9))


# --------------------------------------------------------------------------- #
#  SEKTOR-RELATIVE PERZENTILE
# --------------------------------------------------------------------------- #
def percentile(value, peers, higher_is_better=True):
    """Rang von `value` innerhalb `peers` als 0..1."""
    vals = [p for p in peers if p is not None]
    if value is None or len(vals) < 3:
        return None
    below = sum(1 for p in vals if p < value)
    pct = below / len(vals)
    return pct if higher_is_better else 1 - pct


def pct_to_score(pct):
    return None if pct is None else max(1, min(10, 1 + pct * 9))


def inject_sector_percentiles(raws: list[dict]):
    """
    Ergänzt je Titel Sektor-Perzentil-Scores (KGV, ROIC, FCF-Rendite).
    Vergleich innerhalb Region+Sektor; zu kleine Gruppen -> regionsweit.
    """
    def group(r):
        return (r.get("region"), r.get("sector"))

    for r in raws:
        peers = [p for p in raws if group(p) == group(r)]
        if len(peers) < 3:
            peers = [p for p in raws if p.get("region") == r.get("region")]
        r["pe_sector_score"] = pct_to_score(
            percentile(r.get("pe_now"), [p.get("pe_now") for p in peers], higher_is_better=False))
        r["roic_sector_score"] = pct_to_score(
            percentile(r.get("roic"), [p.get("roic") for p in peers], higher_is_better=True))
        r["fcf_sector_score"] = pct_to_score(
            percentile(r.get("fcf_yield"), [p.get("fcf_yield") for p in peers], higher_is_better=True))
    return raws
